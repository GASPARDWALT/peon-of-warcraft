#!/usr/bin/env python3
"""Validate new cliffs and Continue using real, normally obtained v028 saves.

Preparation plays the immutable v028 ROM, walks every reachable old cell that
will become WALL, and uses the actual Save menu. Validation cold-boots each
32 KiB battery with the candidate ROM; no RAM/SRAM edits or emulator states.
The 24 pre-existing isolated floor cells are reported separately rather than
represented as ordinarily obtainable saves.
"""
import argparse
from collections import deque
from contextlib import contextmanager
import hashlib
import json
import logging
from pathlib import Path
import re
import shutil

from PIL import Image

import build_peon_geography_v029 as geography
import run_peon_v023_validation as adapter
import validate_peon_environment_v025 as environment
import validate_peon_lazy_quest as lazy
import validate_peon_villages as villages
import validate_peon_class_potions as potions

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/geography_v029'
PRIVATE = Path('/tmp/peon_geography_v029_old_batteries')
OLD = Path('/tmp/peon_v028_candidate_06')
OLD_SHA = '943d460f6f76e15dff5b0fc2b8b11b90ba4c2ae79d5e190ea9dd3870b4d68620'
OLD_SYM_SHA = 'a39b3bb28f5634fa9f1ba93323de698287503033d78462c6cad8847afdad82ab'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def symbols(path):
    result = {}
    for row in Path(path).read_text().splitlines():
        fields = row.split()
        if len(fields) == 2 and ':' in fields[0]:
            try:
                result[fields[1]] = tuple(int(n, 16) for n in fields[0].split(':'))
            except ValueError:
                pass
    return result


@contextmanager
def metadata_context(source, output):
    """Only observer metadata/destinations change, never the running ROM."""
    saved = []
    for module in adapter.local_dependencies(environment):
        for name, value in (('ROOT', source), ('OUT', output), ('OUTPUT', output)):
            if hasattr(module, name):
                saved.append((module, name, getattr(module, name)))
                setattr(module, name, value)
    old_flags = environment.game.FLAGS
    environment.game.FLAGS = lazy.event_indices()
    # Numeric aliases in explicitly reserved bits intentionally do not alter
    # the const stream. The old observer parser only knows const entries.
    for match in re.finditer(r'^\s*DEF\s+(EVENT_\w+)\s+EQU\s+(\$[0-9a-fA-F]+|\d+)\b',
                             (source / 'constants/event_flags.asm').read_text(), re.M):
        value = match[2]
        environment.game.FLAGS[match[1]] = int(value[1:], 16) if value.startswith('$') else int(value)
    old_maps = dict(villages.MAPS)
    for name in geography.TARGETS:
        villages.MAPS[geography.zones.MAP_NUMBERS[name]] = (name, *geography.zones.DIMS[name])
    output.mkdir(parents=True, exist_ok=True)
    try:
        yield
    finally:
        villages.MAPS.clear(); villages.MAPS.update(old_maps)
        environment.game.FLAGS = old_flags
        for module, name, value in reversed(saved):
            setattr(module, name, value)


class GeographySession(environment.EnvironmentSession):
    def __init__(self, rom, syms, output):
        self.output = output
        self.save_calls = self.menu_exits = self.relocations = 0
        super().__init__(rom, syms)

    def open(self):
        super().open()
        for label, counter in (('_SaveGameData', 'save_calls'),
                               ('StartMenu.Exit', 'menu_exits'),
                               ('PeonRelocateBlockedContinueV029.Relocate', 'relocations')):
            if label in self.sym:
                self.p.hook_register(*self.sym[label],
                    lambda _, name=counter: setattr(self, name, getattr(self, name) + 1), None)

    def capture(self, label):
        self.output.mkdir(parents=True, exist_ok=True)
        self.p.screen.image.save(self.output / (label + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(
            self.output / (label + '_4x.png'))
        print(label, self.map(), self.position(), flush=True)

    def record(self):
        fields = {'wPlayerName': 11, 'wPlayerID': 2,
                  'wPartyCount': 1, 'wPartySpecies': 7,
                  'wPartyMons': 6 * 48, 'wPartyMonOTs': 6 * 11,
                  'wPartyMonNicknames': 6 * 11, 'wEventFlags': 256,
                  'wMoney': 3, 'wMomsMoney': 3, 'wTMsHMs': 57,
                  'wMapGroup': 2, 'wXCoord': 1, 'wYCoord': 1,
                  'wBackupWarpNumber': 1, 'wBackupMapGroup': 1, 'wBackupMapNumber': 1,
                  'wNumItems': 1, 'wNumKeyItems': 1, 'wNumBalls': 1, 'wNumPCItems': 1}
        record = {field: self.read(field, size) for field, size in fields.items()}
        for field, count, width in [('wItems', 'wNumItems', 2), ('wKeyItems', 'wNumKeyItems', 1),
                                    ('wBalls', 'wNumBalls', 2), ('wPCItems', 'wNumPCItems', 2)]:
            record[field] = self.read(field, record[count][0] * width + 1)
        return record

    def travel(self, destination, target_cell=None):
        """Choose entrances reachable without pulling a living blocker.

        Sarkoth separates two ordinary basin approaches. A graph of map IDs
        alone can choose an unreachable exit; consider each entry cell too.
        """
        names = {re.sub(r'(?<!^)(?=[A-Z])', '_', item[0]).upper(): number
                 for number, item in villages.MAPS.items()}

        def warps(name):
            return [{'xy': (int(m[1]), int(m[2])), 'target': m[3], 'index': int(m[4])}
                    for m in re.finditer(r'^\s*warp_event\s+(\d+),\s*(\d+),\s*(\w+),\s*(-?\d+)',
                        (environment.ROOT / f'maps/{name}.asm').read_text(), re.M)]

        def accessible(number, entry):
            name, width, height = villages.MAPS[number]
            blocks = (environment.ROOT / f'maps/{name}.blk').read_bytes()
            live = [a for a in environment.game.all_actors(name)
                    if a['sprite'] != 'SPRITE_NONE'
                    and (a['event'] == '-1' or not self.event(a['event']))]
            occupied = {a['xy'] for a in live}
            danger = {p for p, script in environment.game.triggers(name).items()
                      if script in {a['script'] for a in live}}
            portals = villages.warp_tiles(name)
            seen, queue = {entry}, deque([entry])
            while queue:
                x, y = queue.popleft()
                if (x, y) in portals and (x, y) != entry:
                    continue
                for _, dx, dy in villages.DIRECTIONS:
                    p = x + dx, y + dy
                    if (p in seen or p in occupied or p in danger or not
                            (0 <= p[0] < 2 * width and 0 <= p[1] < 2 * height)):
                        continue
                    block = blocks[p[1] // 2 * width + p[0] // 2]
                    if not block or self.collisions[block][p[1] % 2 * 2 + p[0] % 2] == 'WALL':
                        continue
                    seen.add(p); queue.append(p)
            return seen

        graph = {}
        for number, (name, _, _) in villages.MAPS.items():
            rows = warps(name)
            graph[number] = []
            for row in rows:
                target_name, target_index = row['target'], row['index']
                if target_name not in names:
                    continue
                target = names[target_name]
                if target in (21, 22, 23, 24):
                    continue
                target_map = villages.MAPS[target][0]
                target_row = warps(target_map)[target_index - 1]
                graph[number].append((target, tuple(row['xy']), tuple(target_row['xy'])))
        start = self.map(), self.position()
        seen, queue = {start}, deque([(start, [])])
        while queue:
            (number, entry), route = queue.popleft()
            walk = accessible(number, entry)
            if number == destination and (target_cell is None or tuple(target_cell) in walk):
                for target, source_xy in route:
                    self.navigate(source_xy, expected_map=target)
                return
            for target, source_xy, target_xy in graph[number]:
                state = target, target_xy
                if source_xy not in walk or state in seen:
                    continue
                seen.add(state)
                queue.append((state, route + [(target, source_xy)]))
        raise AssertionError(('No safe ordinary portal route', start, destination))

    def go_den(self):
        self.travel(14)

    def to_valley(self):
        self.travel(15)

    def palette_location(self):
        # The frozen preparation metadata intentionally has no references
        # tree. These five appended compact regions use the actual Valley
        # palette row, independently of an optional old gallery JSON.
        if 25 <= self.map() <= 29:
            return 'PeonRegionBGPalettes', 64
        return super().palette_location()

    def save_ordinary(self):
        before = self.record()
        saves, exits = self.save_calls, self.menu_exits
        self.press('start')
        choices = self.read('wMenuItemsList', self.read('wMenuItemsList')[0] + 1)[1:]
        index = choices.index(4) + 1  # Native STARTMENUITEM_SAVE; order may change.
        for _ in range(16):
            cursor = self.read('wMenuCursorPosition')[0]
            if cursor == index:
                break
            self.press('up' if cursor > index else 'down', 30)
        assert self.read('wMenuCursorPosition') == [index]
        self.press('a')
        for _ in range(20):
            if self.save_calls == saves + 1 and self.menu_exits > exits:
                break
            self.press('a', 180)
        self.p.tick(90, True)
        assert self.save_calls == saves + 1 and self.menu_exits > exits
        assert self.read('wScriptMode') == [0] and self.record() == before
        self.p.stop(save=True)
        self.p = None
        battery = Path(str(self.rom) + '.ram')
        assert battery.stat().st_size == 32768
        return before, battery

    def continue_ordinary(self, map_id):
        self.p.tick(1800, True)
        self.press('start')
        for _ in range(24):
            if self.read('wMapGroup', 2) == [26, map_id] and self.read('wScriptMode') == [0]:
                break
            self.press('a', 180)
        self.p.tick(120, True)
        assert self.read('wMapGroup', 2) == [26, map_id]
        assert self.read('wScriptMode') == [0] and self.read('wBattleMode') == [0]


def old_case_plan():
    changes = json.loads((OUT / 'changed_collision_cells.json').read_text())
    _, _, rows = geography.build_tables()
    cases, isolated = [], []
    for name, entries in changes.items():
        old = geography.original(f'maps/{name}.blk')
        walk = geography.reached(old, name, rows)
        for entry in entries:
            row = entry | {'map': name, 'map_id': geography.zones.MAP_NUMBERS[name]}
            (cases if tuple(entry['xy']) in walk else isolated).append(row)
        safe = next(entry['safeLandingSuggested'] for entry in entries
                    if tuple(entry['safeLandingSuggested']) in walk)
        cases.append({'map': name, 'map_id': geography.zones.MAP_NUMBERS[name],
                      'xy': safe, 'safeLandingSuggested': safe, 'unchanged_floor_control': True})
    assert len(isolated) == 24 and sum(not c.get('unchanged_floor_control') for c in cases) == 44
    return cases, isolated


def freeze_old_metadata():
    source = PRIVATE / 'source_metadata'
    assert sha(OLD / 'pokecrystal.gbc') == OLD_SHA
    assert sha(OLD / 'pokecrystal.sym') == OLD_SYM_SHA
    # A resumed preparation must use the original observer metadata even if
    # the live checkout has since integrated the geography proposal.
    if source.exists():
        return source
    assert len((ROOT / 'data/tilesets/peon_metatiles.bin').read_bytes()) == 53 * 16
    for name in geography.TARGETS:
        assert (ROOT / f'maps/{name}.blk').read_bytes() == geography.original(f'maps/{name}.blk')
    source.mkdir(parents=True)
    for folder in ('constants', 'maps', 'gfx', 'data'):
        shutil.copytree(ROOT / folder, source / folder)
    shutil.copyfile(OLD / 'pokecrystal.sym', source / 'pokecrystal.sym')
    return source


class GeographyPreparationSession(GeographySession, potions.PotionSession):
    def write(self, *_args, **_kwargs):
        raise AssertionError('Geography preparation forbids gameplay memory edits')

    def unlock_sarkoth_side_passage(self):
        """Reach the basin's western floor through an actual native victory.

        The live level-four boss blocks that ledge until killed. The ordinary
        level-two starter, Lightning Bolt, and two starting healing potions
        are sufficient. This is gameplay, not a collision-only assumption.
        """
        assert self.map() == 27 and not self.event('EVENT_PEON_SARKOTH_DEAD')
        return self.ordinary_passage_battle((5, 4), 'EVENT_PEON_SARKOTH_DEAD',
            'ordinary_sarkoth_victory_opens_western_ledge')

    def unlock_cave_western_ledge(self):
        # The first level-three familiar guards the old western pocket. Rest
        # through the real innkeeper before returning to that live fight.
        # Sarkoth's poison also ticks while walking. Use his actual potion
        # drop, if needed, rather than editing status or walking through the
        # genuine poison-faint dialogue on the way to the inn.
        if self.word('wPartyMon1HP') < 10 and self.item_quantity(potions.HEAL):
            self.use_world_item(potions.HEAL, True)
        self.rest()
        self.travel(28)
        assert not self.event('EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD')
        return self.ordinary_passage_battle((4, 6), 'EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD',
            'ordinary_familiar_victory_opens_western_ledge')

    def ordinary_passage_battle(self, trigger, retired_flag, label):
        self.watch = True
        previous_menu = self.menus
        self.navigate(trigger)
        self.wait_action_return(previous_menu)
        actions = []
        for _ in range(25):
            if not self.read('wBattleMode')[0]:
                break
            hp, enemy = self.word('wBattleMonHP'), self.word('wEnemyMonHP')
            if hp <= 9 and self.item_quantity(potions.HEAL):
                actions.append({'action': 'starting healing potion', 'hp_before': hp,
                                'enemy_hp_before': enemy})
                self.use_item(potions.HEAL, True)
            else:
                actions.append({'action': 'Lightning Bolt', 'hp_before': hp,
                                'enemy_hp_before': enemy})
                self.attack_slot(1)
        assert self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]
        assert self.read('wBattleResult') == [0] and self.event(retired_flag)
        self.capture(label)
        return {'ordinary_boss_victory': True, 'ram_or_sram_edits': False,
                'retired_flag': retired_flag, 'label': label,
                'starting_healing_potions_used': sum(a['action'].startswith('starting') for a in actions),
                'actions': actions, 'record_after_battle': self.record()}


def prepare():
    PRIVATE.mkdir(parents=True, exist_ok=True)
    source = freeze_old_metadata()
    cases, isolated = old_case_plan()
    evidence = OUT / 'old_save_preparation'
    report = {'passed': False, 'source_rom_sha256': OLD_SHA,
              'source_sym_sha256': OLD_SYM_SHA, 'ordinary_buttons_only': True,
              'ram_or_sram_edits': False, 'emulator_states_loaded': False,
              'user_saves_opened': False, 'reachable_changed_cells': 44,
              'isolated_old_floor_cells_unobtainable_by_ordinary_play': isolated,
              'unchanged_floor_control_count': 7, 'cases': []}
    saved_report = OUT / 'old_save_preparation.json'
    if saved_report.exists():
        previous = json.loads(saved_report.read_text())
        assert previous['source_rom_sha256'] == OLD_SHA
        assert previous['source_sym_sha256'] == OLD_SYM_SHA
        for index, prepared in enumerate(previous['cases']):
            assert all(prepared.get(k) == value for k, value in cases[index].items())
            assert prepared.get('old_rom_cold_continue_preserves_complete_record')
            battery = Path(prepared['battery_path'])
            assert battery.stat().st_size == 32768 and sha(battery) == prepared['battery_sha256']
        report['cases'] = previous['cases']
        report['ordinary_passage_unlocks'] = previous.get('ordinary_passage_unlocks', [])
    session = None
    try:
        with metadata_context(source, evidence):
            rom = PRIVATE / 'old_walk.gbc'
            shutil.copyfile(OLD / 'pokecrystal.gbc', rom)
            if report['cases']:
                last = report['cases'][-1]
                shutil.copyfile(last['battery_path'], Path(str(rom) + '.ram'))
            else:
                Path(str(rom) + '.ram').unlink(missing_ok=True)
            session = GeographyPreparationSession(rom, symbols(OLD / 'pokecrystal.sym'), evidence)
            if report['cases']:
                session.continue_ordinary(last['map_id'])
                assert session.record() == last['record_before_upgrade']
            else:
                session.fresh()
            for index in range(len(report['cases']), len(cases)):
                case = cases[index]
                try:
                    session.travel(case['map_id'], case['xy'])
                except AssertionError:
                    if (session.map() == 27 and case['map_id'] == 27
                            and case['xy'] == [2, 5] and not session.event('EVENT_PEON_SARKOTH_DEAD')):
                        unlock = session.unlock_sarkoth_side_passage()
                    elif (case['map_id'] == 28 and case['xy'] == [2, 4]
                            and not session.event('EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD')):
                        unlock = session.unlock_cave_western_ledge()
                    else:
                        raise
                    report.setdefault('ordinary_passage_unlocks', []).append(unlock)
                    session.travel(case['map_id'], case['xy'])
                session.navigate(case['xy'])
                assert session.collision_at(*case['xy']) == 'FLOOR'
                label = f"{index:02d}_{case['map']}_{case['xy'][0]}_{case['xy'][1]}"
                session.capture(label + '_ordinary_old_position')
                record, battery = session.save_ordinary()
                dest = PRIVATE / (label + '.ram')
                shutil.copyfile(battery, dest)
                report['cases'].append(case | {'battery_path': str(dest),
                    'battery_sha256': sha(dest), 'battery_bytes': 32768,
                    'record_before_upgrade': record, 'ordinary_save_commit_observed': True,
                    'label': label})
                session.open()
                session.continue_ordinary(case['map_id'])
                assert session.record() == record
                report['cases'][-1]['old_rom_cold_continue_preserves_complete_record'] = True
                saved_report.write_text(json.dumps(report, indent=2) + '\n')
            assert len(report['cases']) == 51
            session.p.stop(save=False); session = None
            assert sha(OLD / 'pokecrystal.gbc') == OLD_SHA
            report['passed'] = True
    except Exception as error:
        report['failure'] = repr(error)
        if session and session.p:
            session.capture('old_save_preparation_failure')
            session.p.stop(save=False)
        raise
    finally:
        (OUT / 'old_save_preparation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': True, 'ordinary_batteries': 51, 'reachable_changed_cells': 44,
                      'isolated_not_fabricated': 24, 'source_rom_sha256': OLD_SHA}))


def compare_upgrade(before, after, level):
    assert before.keys() == after.keys()
    allowed = {'wXCoord', 'wYCoord'}
    changes = []
    for key in before:
        if before[key] == after[key]:
            continue
        changes.append(key)
        if key == 'wPartyMons':
            # Resource storage owns only native MON_POKERUS/MON_CAUGHTDATA.
            expected = list(before[key])
            maximum = min(999, 48 + 12 * max(1, min(100, level)))
            assert expected[28] != 0x80, 'Unexpected already-tagged v028 baseline'
            expected[28:31] = [0x80, maximum >> 8, maximum & 255]
            assert after[key] == expected, ('Unexpected party progression change', key)
        else:
            assert key in allowed, ('Unexpected persistent change at Continue', key)
    return changes


def prepare_road_saves():
    """Save normally on the moved pack anchor and its new gate triggers."""
    prepared = json.loads((OUT / 'old_save_preparation.json').read_text())
    assert prepared['passed'] and len(prepared['cases']) == 51
    source = freeze_old_metadata()
    evidence = OUT / 'old_road_preparation'
    evidence.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'source_rom_sha256': OLD_SHA,
              'source_sym_sha256': OLD_SYM_SHA, 'ordinary_buttons_only': True,
              'ram_or_sram_edits': False, 'emulator_states_loaded': False,
              'user_saves_opened': False, 'cases': []}
    session = None
    try:
        with metadata_context(source, evidence):
            rom = PRIVATE / 'old_road_walk.gbc'
            shutil.copyfile(OLD / 'pokecrystal.gbc', rom)
            shutil.copyfile(prepared['cases'][-1]['battery_path'], Path(str(rom) + '.ram'))
            session = GeographySession(rom, symbols(OLD / 'pokecrystal.sym'), evidence)
            session.continue_ordinary(prepared['cases'][-1]['map_id'])
            assert session.read('wPartyMon1Level')[0] >= 4
            session.travel(16)
            for index, position in enumerate([(12, 22), (12, 23), (11, 24), (13, 24), (12, 25)]):
                session.navigate(position)
                collision = session.collision_at(*position)
                assert collision == ('WARP_PANEL' if position in ((13, 24), (12, 25)) else 'FLOOR')
                label = f'road_{index}_{position[0]}_{position[1]}'
                session.capture(label + '_ordinary_old_position')
                record, battery = session.save_ordinary()
                dest = PRIVATE / (label + '.ram')
                shutil.copyfile(battery, dest)
                report['cases'].append({'map': 'DurotarRoad', 'map_id': 16,
                    'xy': list(position), 'safeLandingSuggested': list(position),
                    'unchanged_floor_control': True, 'moved_pack_anchor_overlap': index == 0,
                    'future_gate_trigger_cell': index != 0,
                    'expected_landing_collision': collision,
                    'battery_path': str(dest), 'battery_sha256': sha(dest),
                    'battery_bytes': 32768, 'record_before_upgrade': record,
                    'ordinary_save_commit_observed': True, 'label': label})
                session.open()
                session.continue_ordinary(16)
                assert session.record() == record
                report['cases'][-1]['old_rom_cold_continue_preserves_complete_record'] = True
            assert not session.event('EVENT_PEON_ROAD_SCORPID_PACK_DEAD')
            session.p.stop(save=False); session = None
            report['passed'] = True
    except Exception as error:
        report['failure'] = repr(error)
        if session and session.p:
            session.capture('old_road_preparation_failure')
            session.p.stop(save=False)
        raise
    finally:
        (OUT / 'old_road_preparation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': True, 'ordinary_road_batteries': 5,
                      'hero_level_at_least_four': True, 'existing_pack_dead_flag_clear': True}))


def prepare_actor_saves():
    """Take short normal walks from the existing same-map battery fixtures."""
    prepared = json.loads((OUT / 'old_save_preparation.json').read_text())
    assert prepared['passed'] and len(prepared['cases']) == 51
    source = freeze_old_metadata()
    landings = json.loads((OUT / 'new_actor_continue_landings.json').read_text())
    entries = [e for e in landings['entries'] if e['map'] != 'DurotarRoad']
    evidence = OUT / 'old_actor_preparation'
    evidence.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'source_rom_sha256': OLD_SHA,
              'source_sym_sha256': OLD_SYM_SHA, 'ordinary_buttons_only': True,
              'ram_or_sram_edits': False, 'emulator_states_loaded': False,
              'user_saves_opened': False, 'cases': []}
    session = None
    try:
        with metadata_context(source, evidence):
            for index, entry in enumerate(entries):
                base = next((c for c in prepared['cases'] if c['map_id'] == entry['map_id']),
                            prepared['cases'][-1])
                rom = PRIVATE / 'old_actor_walk.gbc'
                shutil.copyfile(OLD / 'pokecrystal.gbc', rom)
                shutil.copyfile(base['battery_path'], Path(str(rom) + '.ram'))
                session = GeographySession(rom, symbols(OLD / 'pokecrystal.sym'), evidence)
                session.continue_ordinary(base['map_id'])
                session.travel(entry['map_id'], entry['xy'])
                session.navigate(entry['xy'])
                assert session.collision_at(*entry['xy']) == 'FLOOR'
                label = f"actor_{index}_{entry['map']}_{entry['xy'][0]}_{entry['xy'][1]}"
                session.capture(label + '_ordinary_old_position')
                record, battery = session.save_ordinary()
                dest = PRIVATE / (label + '.ram')
                shutil.copyfile(battery, dest)
                report['cases'].append(entry | {'new_body_save': True,
                    'battery_path': str(dest), 'battery_sha256': sha(dest),
                    'battery_bytes': 32768, 'record_before_upgrade': record,
                    'ordinary_save_commit_observed': True, 'label': label})
                session.open()
                session.continue_ordinary(entry['map_id'])
                assert session.record() == record
                report['cases'][-1]['old_rom_cold_continue_preserves_complete_record'] = True
                session.p.stop(save=False); session = None
            assert len(report['cases']) == len(entries)
            report['passed'] = True
    except Exception as error:
        report['failure'] = repr(error)
        if session and session.p:
            session.capture('old_actor_preparation_failure')
            session.p.stop(save=False)
        raise
    finally:
        (OUT / 'old_actor_preparation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': True, 'ordinary_new_body_batteries': len(entries)}))


def native_layout(rom_path, symbol_path):
    """Verify source-shaped cliffs and reciprocal routes in actual ROM bytes."""
    rom, sym = Path(rom_path).read_bytes(), symbols(symbol_path)

    def native(label, size):
        bank, address = sym[label]
        offset = bank * 0x4000 + address - (0x4000 if bank else 0)
        return rom[offset:offset + size]

    meta, collision, rows = geography.build_tables()
    assert native('TilesetPeonMeta', len(meta)) == meta
    codes = {'FLOOR': 0x00, 'WALL': 0x07, 'WARP_PANEL': 0x7c}
    assert native('TilesetPeonColl', len(rows) * 4) == bytes(
        codes[value] for row in rows for value in row)
    old_sym = symbols(OLD / 'pokecrystal.sym')
    old_rom = (OLD / 'pokecrystal.gbc').read_bytes()
    bank, address = old_sym['TilesetPeonMeta']
    offset = bank * 0x4000 + address - 0x4000
    assert meta[:53 * 16] == old_rom[offset:offset + 53 * 16]
    table = bytearray()
    changes = json.loads((OUT / 'changed_collision_cells.json').read_text())
    overrides_path = OUT / 'continue_landing_overrides.json'
    overrides = json.loads(overrides_path.read_text())['entries'] if overrides_path.exists() else []
    by_override = {(e['map_id'], tuple(e['xy'])): e for e in overrides}
    for name, entries in changes.items():
        for entry in entries:
            map_id = geography.zones.MAP_NUMBERS[name]
            override = by_override.get((map_id, tuple(entry['xy'])))
            landing = override['safeLandingSuggested'] if override else entry['safeLandingSuggested']
            table.extend([26, map_id, *entry['xy'], *landing])
    actor_landings = json.loads((OUT / 'new_actor_continue_landings.json').read_text())
    for entry in actor_landings['entries']:
        table.extend([26, entry['map_id'], *entry['xy'], *entry['safeLandingSuggested']])
    table.append(0xff)
    assert native('PeonBlockedContinueCellsV029', len(table)) == table
    maps, warps = {}, {}
    expected = json.loads((OUT / 'proposed_geometry.json').read_text())
    route_names = set(geography.TARGETS) | {'DurotarRoad', 'BurningBladeCavern', 'SenjinVillage'}
    for name in route_names:
        blocks = (ROOT / f'maps/{name}.blk').read_bytes()
        assert native(name + '_Blocks', len(blocks)) == blocks
        if name in expected['maps']:
            assert hashlib.sha256(blocks).hexdigest() == expected['maps'][name]['proposed_blocks_sha256']
        events = geography.event_rows(name, 'warp_event')
        raw = native(name + '_MapEvents', 3 + len(events) * 5)
        assert raw[:3] == bytes([0, 0, len(events)])
        warps[name] = []
        for index, event in enumerate(events):
            fields = [part.strip() for part in event['arguments'].split(';', 1)[0].split(',')]
            target, target_index = geography.zones.MAP_CONSTANTS[fields[0]], int(fields[1])
            row = bytes([event['xy'][1], event['xy'][0], target_index,
                         26, geography.zones.MAP_NUMBERS[target]])
            assert raw[3 + index * 5:8 + index * 5] == row
            warps[name].append({'xy': event['xy'], 'target': target, 'target_index': target_index})
        maps[name] = {'compiled_blocks_match_source': True, 'bytes': len(blocks),
                      'sha256': hashlib.sha256(blocks).hexdigest(),
                      'compiled_warp_coordinates_and_ids_match': True}
    edges = []
    for source, source_index, target, target_index, direction, source_zone, target_zone in geography.zones.REQUIRED_ROUTE:
        a, b = warps[source][source_index - 1], warps[target][target_index - 1]
        assert (a['target'], a['target_index']) == (target, target_index)
        assert (b['target'], b['target_index']) == (source, source_index)
        edges.append({'source': source, 'target': target, 'direction': direction,
                      'source_zone': source_zone, 'target_zone': target_zone,
                      'source_xy': a['xy'], 'target_xy': b['xy'],
                      'actual_rom_reciprocal_warps': True})
    gate = (ROOT / 'maps/PeonValleyExit.blk').read_bytes()
    assert {i % 5 for i, block in enumerate(gate) if block == 33} == {4}
    return {'metatiles': 67, 'old_first_53_metatile_bytes_preserved': True,
            'actual_compiled_collision_rows_match_all_four_quadrants': True,
            'compiled_migration_entries': 68 + len(actor_landings['entries']),
            'compiled_mountain_migration_entries': 68,
            'compiled_new_body_migration_entries': len(actor_landings['entries']),
            'compiled_migration_table_matches_safe_cells': True,
            'documented_landing_overrides': overrides,
            'maps': maps, 'reciprocal_routes': edges,
            'ivory_fortification_only_on_eastern_zone_7_wall': True,
            'literal_fixed_camera_screens_implemented': False,
            'the_den_native_pixels': [384, 320], 'valley_of_trials_native_pixels': [512, 384],
            'other_five_valley_regions_native_pixels': [160, 160]}


def validate(expected_sha, rom_path, symbol_path, include_road, include_actors):
    assert sha(rom_path) == expected_sha
    prepared = json.loads((OUT / 'old_save_preparation.json').read_text())
    assert prepared['passed'] and prepared['source_rom_sha256'] == OLD_SHA
    cases = list(prepared['cases'])
    if include_road:
        road = json.loads((OUT / 'old_road_preparation.json').read_text())
        assert road['passed'] and road['source_rom_sha256'] == OLD_SHA
        cases.extend(road['cases'])
    if include_actors:
        actors = json.loads((OUT / 'old_actor_preparation.json').read_text())
        assert actors['passed'] and actors['source_rom_sha256'] == OLD_SHA
        cases.extend(actors['cases'])
    landings = json.loads((OUT / 'new_actor_continue_landings.json').read_text())
    by_anchor = {(e['map_id'], tuple(e['xy'])): e for e in landings['entries']}
    overrides_path = OUT / 'continue_landing_overrides.json'
    overrides = json.loads(overrides_path.read_text())['entries'] if overrides_path.exists() else []
    by_override = {(e['map_id'], tuple(e['xy'])): e for e in overrides}
    runtime = OUT / 'continue_runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'rom_sha256': expected_sha, 'source_rom_sha256': OLD_SHA,
              'symbols_sha256': sha(symbol_path),
              'normal_buttons_only': True, 'ram_or_sram_edits': False,
              'emulator_states_loaded': False, 'user_saves_opened': False,
              'physical_chromatic_tested': False, 'cases': []}
    session = None
    try:
        report['native_compiled_layout'] = native_layout(rom_path, symbol_path)
        with metadata_context(ROOT, runtime):
            for case in cases:
                battery = Path(case['battery_path'])
                assert battery.stat().st_size == 32768 and sha(battery) == case['battery_sha256']
                rom = PRIVATE / 'upgrade_test.gbc'
                shutil.copyfile(rom_path, rom)
                shutil.copyfile(battery, Path(str(rom) + '.ram'))
                session = GeographySession(rom, symbols(symbol_path), runtime)
                session.continue_ordinary(case['map_id'])
                body = by_anchor.get((case['map_id'], tuple(case['xy'])))
                override = by_override.get((case['map_id'], tuple(case['xy'])))
                landing = (override or body or case)['safeLandingSuggested']
                relocated = bool(body) or not case.get('unchanged_floor_control')
                assert session.relocations == int(relocated), (
                    'Continue relocation hook count', case, session.relocations)
                assert session.position() == tuple(landing), (case, session.position())
                assert session.read('wPlayerMapX') + session.read('wPlayerMapY') == [
                    session.position()[0] + 4, session.position()[1] + 4], (
                    'Saved player object coordinates did not follow Continue relocation',
                    case, session.position(), session.read('wPlayerMapX') + session.read('wPlayerMapY'))
                assert session.collision_at(*session.position()) == case.get('expected_landing_collision', 'FLOOR')
                changes = compare_upgrade(case['record_before_upgrade'], session.record(),
                                          session.read('wPartyMon1Level')[0])
                native = session.scenery(case['label'] + '_upgraded_native_position')
                # Stand on real floor and prove one ordinary step can leave it.
                before_xy = session.position()
                name = villages.MAPS[case['map_id']][0]
                live_actors = session.live_actors(name)
                occupied = {a['xy'] for a in live_actors}
                occupied |= {tuple(e['xy']) for e in landings['entries'] if e['map_id'] == case['map_id']}
                live_scripts = {a['script'] for a in live_actors}
                danger = {xy for xy, script in environment.game.triggers(name).items()
                          if script in live_scripts}
                portals = villages.warp_tiles(name)
                for key, dx, dy in villages.DIRECTIONS:
                    pos = before_xy[0] + dx, before_xy[1] + dy
                    if (session.collision_at(*pos) != 'WALL' and pos not in occupied
                            and pos not in danger and pos not in portals):
                        session.walk(key)
                        assert session.read('wPlayerMapX') + session.read('wPlayerMapY') == [
                            session.position()[0] + 4, session.position()[1] + 4]
                        step = {'key': key, 'to': list(session.position())}
                        break
                else:
                    # A safe floor can be the one-cell approach to a real
                    # geographic portal. Prove that route by ordinary input,
                    # rather than misclassifying a valid exit as a dead end.
                    source_warps = geography.event_rows(name, 'warp_event')
                    for key, dx, dy in villages.DIRECTIONS:
                        pos = before_xy[0] + dx, before_xy[1] + dy
                        if (pos not in portals or pos in occupied or pos in danger
                                or session.collision_at(*pos) == 'WALL'):
                            continue
                        warp = next(w for w in source_warps if tuple(w['xy']) == pos)
                        target_constant = warp['arguments'].split(',')[0].strip()
                        target_name = geography.zones.MAP_CONSTANTS[target_constant]
                        target_map = geography.zones.MAP_NUMBERS[target_name]
                        session.navigate(pos, expected_map=target_map)
                        assert session.read('wPlayerMapX') + session.read('wPlayerMapY') == [
                            session.position()[0] + 4, session.position()[1] + 4]
                        assert session.read('wScriptMode') == [0] and session.read('wBattleMode') == [0]
                        step = {'key': key, 'to': list(session.position()), 'map_id': session.map(),
                                'source_portal_xy': list(pos), 'via_real_reciprocal_portal': True}
                        break
                    else:
                        raise AssertionError(('No ordinary step or portal from migration landing', case))
                report['cases'].append({'map': case['map'], 'old_xy': case['xy'],
                    'new_xy': list(before_xy), 'unchanged_floor_control': bool(case.get('unchanged_floor_control')),
                    'moved_pack_anchor_overlap': bool(case.get('moved_pack_anchor_overlap')),
                    'future_gate_trigger_cell': bool(case.get('future_gate_trigger_cell')),
                    'new_body_save': bool(case.get('new_body_save')),
                    'documented_landing_override': bool(override),
                    'source_battery_sha256': case['battery_sha256'],
                    'persistent_changed_fields': changes,
                    'only_geography_xy_and_documented_mana_tag_current_changed': True,
                    'ordinary_walk_after_continue': step, 'native_world_pixels': native,
                    'live_script_and_battle_modes_clear': True})
                session.p.stop(save=False); session = None
            assert len(report['cases']) == 51 + 5 * include_road + (len(actors['cases']) if include_actors else 0)
            assert sha(rom_path) == expected_sha
            report['passed'] = True
    except Exception as error:
        report['failure'] = repr(error)
        if session and session.p:
            session.capture('continue_geography_failure')
            session.p.stop(save=False)
        raise
    finally:
        (OUT / 'continue_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': True, 'rom_sha256': expected_sha,
                      'changed_cell_cold_upgrades': 44, 'unchanged_floor_controls': 7,
                      'road_overlap_and_trigger_upgrades': 5 * include_road,
                      'extra_body_anchor_upgrades': len(actors['cases']) if include_actors else 0,
                      'ram_or_sram_edits': False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-old-saves', action='store_true')
    parser.add_argument('--prepare-road-saves', action='store_true')
    parser.add_argument('--include-road-saves', action='store_true')
    parser.add_argument('--prepare-actor-saves', action='store_true')
    parser.add_argument('--include-actor-saves', action='store_true')
    parser.add_argument('--expected-sha')
    parser.add_argument('--rom', type=Path, default=ROOT / 'pokecrystal.gbc')
    parser.add_argument('--symbols', type=Path, default=ROOT / 'pokecrystal.sym')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.prepare_old_saves:
        prepare()
    elif args.prepare_road_saves:
        prepare_road_saves()
    elif args.prepare_actor_saves:
        prepare_actor_saves()
    elif args.expected_sha:
        validate(args.expected_sha, args.rom, args.symbols, args.include_road_saves, args.include_actor_saves)
    else:
        parser.error('Choose --prepare-old-saves or --expected-sha for Continue validation.')


if __name__ == '__main__':
    main()
