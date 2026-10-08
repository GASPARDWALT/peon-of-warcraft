#!/usr/bin/env python3
"""Fresh normal-button quests, finite encounters and battery-save persistence.

No RAM edits, CPU substitutions or emulator states are used. Hooks only count
native menu/heal entries; all decisions are made with ordinary buttons.
"""
from collections import deque
from pathlib import Path
import hashlib
import json
import logging
import re
import shutil
import tempfile

from PIL import Image
from validate_peon_villages import Session, load_symbols, MAPS, DIRECTIONS, warp_tiles
from validate_peon_lazy_quest import event_indices

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/quest_validation'
MAPS.update({23: ('PeonOrcInn', 6, 5), 24: ('PeonTrollInn', 6, 5)})
FLAGS = event_indices()


def all_actors(name):
    result = []
    for line in (ROOT / 'maps' / (name + '.asm')).read_text().splitlines():
        if not re.match(r'\s*object_event\s+', line):
            continue
        fields = [s.strip() for s in line.strip().split(' ', 1)[1].split(',')]
        result.append({'xy': (int(fields[0]), int(fields[1])), 'sprite': fields[2],
                       'script': fields[-2], 'event': fields[-1], 'index': len(result) + 1})
    return result


def triggers(name):
    return {tuple(map(int, m.groups()[:2])): m[3] for m in re.finditer(
        r'^\s*coord_event\s+(\d+),\s*(\d+),\s*-1,\s*(\w+)',
        (ROOT / 'maps' / (name + '.asm')).read_text(), re.M)}


class QuestSession(Session):
    def __init__(self, rom, sym):
        self.move_menus = 0
        self.heal_calls = 0
        self.encounter_loads = 0
        super().__init__(rom, sym)

    def open(self):
        super().open()
        self.p.hook_register(*self.sym['MoveSelectionScreen'],
                             lambda _unused: setattr(self, 'move_menus', self.move_menus + 1), None)
        self.p.hook_register(*self.sym['LoadTrainerOrWildMonPic'],
                             lambda _unused: setattr(self, 'encounter_loads', self.encounter_loads + 1), None)
        self.p.hook_register(*self.sym['HealParty'],
                             lambda _unused: setattr(self, 'heal_calls', self.heal_calls + 1), None)

    def read(self, name, length=1):
        bank, address = self.sym[name]
        return list(self.p.memory[address:address + length] if address >= 0xe000
                    else self.p.memory[bank, address:address + length])

    def event(self, name):
        i = FLAGS[name]
        return bool(self.read('wEventFlags', i // 8 + 1)[i // 8] & (1 << (i % 8)))

    def experience(self):
        return int.from_bytes(bytes(self.read('wPartyMon1Exp', 3)), 'big')

    def live_actors(self, name):
        masks = self.read('wObjectMasks', 16)
        return [a for a in all_actors(name) if not masks[a['index']]
                and (a['event'] == '-1' or not self.event(a['event']))]

    def capture(self, name):
        self.p.screen.image.save(OUT / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / (name + '_4x.png'))
        print(name, self.map(), self.position(), 'level', self.read('wPartyMon1Level'), flush=True)

    def collision_at(self, x, y):
        _, w, h = MAPS[self.map()]
        if not (0 <= x < w * 2 and 0 <= y < h * 2):
            return 'WALL'
        # Live padded block data includes saved cactus changeblock callbacks,
        # unlike the immutable .blk source on disk.
        bank, address = self.sym['wOverworldMapBlocks']
        offset = (y // 2 + 3) * (w + 6) + x // 2 + 3
        block = self.p.memory[bank, address + offset]
        if not block:
            return 'WALL'
        return self.collisions[block][y % 2 * 2 + x % 2]

    def path(self, target):
        name, _, _ = MAPS[self.map()]
        live = self.live_actors(name)
        occupied = {a['xy'] for a in live}
        live_scripts = {a['script'] for a in live}
        danger = {xy for xy, script in triggers(name).items() if script in live_scripts}
        warps = warp_tiles(name)
        start = self.position()
        q, seen = deque([(start, [])]), {start}
        while q:
            (x, y), path = q.popleft()
            if (x, y) == target:
                return path
            for key, dx, dy in DIRECTIONS:
                pos = x + dx, y + dy
                if pos in seen or pos in occupied or self.collision_at(*pos) == 'WALL':
                    continue
                if pos in warps and pos != target:
                    continue
                if pos in danger and pos != target:
                    continue
                seen.add(pos)
                q.append((pos, path + [key]))
        raise AssertionError((name, 'no safe path', start, target))

    def talk(self, position, direction, label):
        self.navigate(position)
        before = self.position()
        self.press(direction, 30)
        assert self.position() == before, (label, 'facing moved into target')
        self.press('a', 120)
        assert self.read('wScriptMode') != [0], (label, 'no dialogue')
        self.capture(label)
        self.close_dialogue()

    def fresh(self):
        naming = {'entered': False, 'done': False}
        self.p.hook_register(*self.sym['PeonAskName'],
                             lambda value: value.__setitem__('entered', True), naming)
        self.p.tick(240, True)
        self.press('start'); self.press('down'); self.press('a')
        for _ in range(160):
            if self.read('wMapGroup', 2) == [26, 14] and self.read('wScriptMode') == [0]:
                break
            if naming['entered'] and not naming['done']:
                self.p.tick(120, True)
                for j in range(5):
                    self.press('a', 30)
                    if j < 4:
                        self.press('right', 30)
                self.press('start', 30); self.press('a'); naming['done'] = True
            self.press('a')
        assert naming['done'] and self.map() == 14 and self.read('wScriptMode') == [0]
        self.p.hook_deregister(*self.sym['PeonAskName'])
        self.capture('fresh_character')

    def fight(self, label, flag, copper=None):
        heal_before, money_before = self.heal_calls, self.money()
        loads_before = self.encounter_loads
        captured_loads = set()
        handled = self.move_menus
        entered = bool(self.read('wBattleMode')[0])
        for _ in range(160):
            if self.read('wBattleMode')[0]:
                entered = True
            if self.move_menus > handled:
                handled = self.move_menus
                self.p.tick(60, True)
                if self.encounter_loads not in captured_loads:
                    suffix = '_battle' if not captured_loads else '_battle_second'
                    self.capture(label + suffix)
                    captured_loads.add(self.encounter_loads)
                moves, pp = self.read('wBattleMonMoves', 4), self.read('wBattleMonPP', 4)
                wanted = 0 if getattr(self, 'prefer_physical', False) else next((i for i, move in enumerate(moves) if move == 84 and pp[i] & 63), 0)
                for _ in range(5):
                    current = self.read('wCurMoveNum')[0]
                    if current == wanted:
                        break
                    self.press('up' if current > wanted else 'down', 30)
                self.press('a', 180)
            else:
                self.press('a', 120)
            if entered and self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]:
                break
        assert entered and self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0], (label, 'battle did not finish')
        outcome = self.read('wBattleResult')[0]
        assert self.heal_calls == heal_before, (label, 'encounter silently called HealParty')
        if outcome == 0:
            assert self.event(flag), (label, 'victory not persistent')
            if copper is not None:
                assert self.money() == money_before + copper, (label, money_before, self.money())
        elif outcome == 1:
            assert not self.event(flag), (label, 'defeat deleted actor')
            assert self.map() == 14 and self.read('wPartyMon1HP', 2) == [0, 1]
            assert self.money() == money_before, (label, 'defeat granted loot')
        self.capture(label + '_after')
        return {'label': label, 'outcome': outcome, 'dead': self.event(flag),
                'no_auto_heal': True, 'encounter_loads_during_fight': self.encounter_loads - loads_before, 'level_after': self.read('wPartyMon1Level')[0],
                'hp_after': self.read('wPartyMon1HP', 2), 'money_after': self.money()}

    def go_den(self):
        if self.map() == 20:
            self.navigate((10, 16), expected_map=15)
        if self.map() == 16:
            self.navigate((4, 14), expected_map=15)
        if self.map() == 15:
            self.navigate((4, 12), expected_map=14)
        assert self.map() == 14

    def rest(self):
        self.go_den()
        self.navigate((17, 5), expected_map=23)
        heals = self.heal_calls
        self.talk((6, 5), 'up', 'deliberate_inn_rest')
        assert self.heal_calls == heals + 1
        assert self.read('wPartyMon1HP', 2) == self.read('wPartyMon1MaxHP', 2)
        self.navigate((5, 7), expected_map=14)

    def to_valley(self):
        if self.map() == 14:
            self.navigate((20, 10), expected_map=15)
        assert self.map() == 15

    def cold_restart(self):
        self.go_den(); self.navigate((12, 9)); self.press('down', 30)
        before = self.state() | {'events': self.read('wEventFlags', 42),
                                'hp': self.read('wPartyMon1HP', 2),
                                'keys': self.read('wKeyItems', self.read('wNumKeyItems')[0]),
                                'items': self.read('wItems', self.read('wNumItems')[0] * 2)}
        self.press('start')
        for _ in range(10):
            if self.read('wMenuCursorPosition')[0] <= 1:
                break
            self.press('up', 30)
        for _ in range(3):
            self.press('down', 30)
        self.press('a')
        for _ in range(5):
            self.press('a', 180)
        self.capture('quests_saved'); self.p.stop(save=True)
        assert Path(str(self.rom) + '.ram').stat().st_size == 32768
        self.open(); self.p.tick(1800, True); self.press('start')
        for _ in range(12):
            if self.map() == 14 and self.read('wScriptMode') == [0]:
                break
            self.press('a', 180)
        after = self.state() | {'events': self.read('wEventFlags', 42),
                               'hp': self.read('wPartyMon1HP', 2),
                               'keys': self.read('wKeyItems', self.read('wNumKeyItems')[0]),
                               'items': self.read('wItems', self.read('wNumItems')[0] * 2)}
        assert before == after, ('cold battery-save mismatch', before, after)
        self.capture('quests_cold_restart')
        return {'passed': True, 'battery_bytes': 32768, 'before': before, 'after': after}


def start_hostile(s, approach, label, flag, copper, records):
    s.navigate(approach)
    result = s.fight(label, flag, copper)
    records.append(result)
    assert result['outcome'] == 0, (label, 'natural progression failed', result)


def route_checks():
    """Native quadrants, actors and exits must agree before emulator navigation."""
    collisions = [r.split('tilecoll', 1)[1].split(';')[0].replace(' ', '').split(',')
                  for r in (ROOT / 'data/tilesets/peon_collision.asm').read_text().splitlines() if 'tilecoll' in r]
    results = {}
    for num in (14, 15, 16, 17, 18, 19, 20):
        name, w, h = MAPS[num]
        grid = (ROOT / 'maps' / (name + '.blk')).read_bytes()
        assert len(grid) == w * h and 0 not in grid, (name, 'invalid native ground')
        occupied = {a['xy'] for a in all_actors(name)}
        warps = warp_tiles(name)
        def free(p):
            x, y = p
            return 0 <= x < w * 2 and 0 <= y < h * 2 and collisions[grid[y // 2 * w + x // 2]][y % 2 * 2 + x % 2] != 'WALL' and p not in occupied
        origin = next(p for p in sorted(warps) if free(p))
        reached, q = {origin}, deque([origin])
        while q:
            x, y = q.popleft()
            for _, dx, dy in DIRECTIONS:
                pos = x + dx, y + dy
                if pos not in reached and free(pos):
                    reached.add(pos); q.append(pos)
        assert warps <= reached, (name, 'unreachable warp', warps - reached)
        for a in all_actors(name):
            x, y = a['xy']
            assert any((x + dx, y + dy) in reached for _, dx, dy in DIRECTIONS), (name, 'actor has no approach', a)
        results[name] = {'native_walkable_tiles_connected': len(reached), 'actors_approachable': len(occupied), 'doors_and_exits_connected': len(warps)}
    return results


def main():
    logging.disable(logging.CRITICAL); OUT.mkdir(parents=True, exist_ok=True)
    report = {'rom_sha256': hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest(),
              'normal_buttons_only': True, 'ram_edits': False, 'emulator_states_loaded': False,
              'native_route_checks': route_checks(), 'battles': [], 'quest_xp_rewards': {}}
    s = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-v022-quests-') as directory:
            rom = Path(directory) / 'test.gbc'; shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = QuestSession(rom, load_symbols()); s.fresh()
            # Complete the Den's ordinary chain first to establish natural level progression.
            s.talk((10, 10), 'up', 'gornek_first_quest')
            s.navigate((18, 13)); s.press('up', 30); s.press('a')
            record = s.fight('boar', 'EVENT_PEON_QUEST_DONE'); report['battles'].append(record)
            assert record['outcome'] == 0
            s.talk((10, 10), 'up', 'gornek_second_quest'); s.rest()
            start_hostile(s, (17, 15), 'den_scorpid', 'EVENT_PEON_SCORPID_DEFEATED', None, report['battles'])
            s.talk((10, 10), 'up', 'gornek_second_reward'); s.rest(); s.to_valley()
            s.talk((8, 11), 'up', 'galgar_offer')
            s.talk((10, 20), 'up', 'hanazua_offer')
            s.talk((5, 11), 'right', 'zureetha_offer')
            for position, face, number in (((8, 7), 'left', 1), ((24, 9), 'left', 2), ((10, 17), 'left', 3)):
                s.talk(position, face, f'cactus_{number}_harvest')
                assert s.event(f'EVENT_PEON_CACTUS_{number}')
            money, xp = s.money(), s.experience(); s.talk((8, 11), 'up', 'galgar_reward')
            assert s.event('EVENT_PEON_CACTUS_DONE') and s.money() == money + 50
            assert s.experience() == xp + 25
            s.talk((8, 11), 'up', 'galgar_repeat_no_reward')
            assert s.money() == money + 50 and s.experience() == xp + 25
            report['quest_xp_rewards']['cactus'] = {'normal_turn_in_xp': 25, 'repeat_xp_and_copper_unchanged': True}
            s.navigate((24, 4), expected_map=20)
            start_hostile(s, (8, 11), 'cave_imp', 'EVENT_PEON_CAVE_IMP_DEAD', 20, report['battles'])
            # Return and rest deliberately between finite encounters; no battle auto-heal.
            s.rest(); s.to_valley(); s.navigate((24, 4), expected_map=20)
            start_hostile(s, (12, 9), 'cave_strong_imp', 'EVENT_PEON_CAVE_STRONG_IMP_DEAD', 30, report['battles'])
            s.rest(); s.to_valley(); s.navigate((24, 4), expected_map=20)
            start_hostile(s, (5, 7), 'felstalker', 'EVENT_PEON_CAVE_FELSTALKER_DEAD', 25, report['battles'])
            s.rest(); s.to_valley()
            start_hostile(s, (16, 21), 'sarkoth', 'EVENT_PEON_SARKOTH_DEAD', 35, report['battles'])
            money, xp = s.money(), s.experience(); s.talk((10, 20), 'up', 'hanazua_reward')
            assert s.event('EVENT_PEON_SARKOTH_DONE') and s.money() == money + 100
            assert s.experience() == xp + 50
            s.talk((10, 20), 'up', 'hanazua_repeat_no_reward'); assert s.money() == money + 100
            assert s.experience() == xp + 50
            report['quest_xp_rewards']['sarkoth'] = {'normal_turn_in_xp': 50, 'repeat_xp_and_copper_unchanged': True}
            s.rest(); s.to_valley(); s.navigate((24, 4), expected_map=20)
            start_hostile(s, (5, 4), 'cultist', 'EVENT_PEON_CAVE_CULTIST_DEAD', 25, report['battles'])
            s.rest(); s.to_valley(); s.navigate((24, 4), expected_map=20)
            start_hostile(s, (14, 4), 'yarrog', 'EVENT_PEON_YARROG_DEAD', 35, report['battles'])
            s.navigate((10, 16), expected_map=15)
            money, xp = s.money(), s.experience(); s.talk((5, 11), 'right', 'zureetha_reward')
            assert s.event('EVENT_PEON_MEDALLION_DONE') and s.money() == money + 150
            assert s.experience() == xp + 100
            assert s.item_quantity(0x8e) == 1
            s.talk((5, 11), 'right', 'zureetha_repeat_no_reward'); assert s.money() == money + 150
            assert s.experience() == xp + 100
            report['quest_xp_rewards']['medallion'] = {'normal_turn_in_xp': 100, 'repeat_xp_and_copper_unchanged': True}
            s.rest(); s.to_valley(); s.navigate((28, 12), expected_map=16)
            for approach, label, flag, copper, face in (
                ((5, 6), 'tiger', 'EVENT_PEON_ROAD_TIGER_DEAD', 20, 'up'),
                ((18, 9), 'raptor', 'EVENT_PEON_ROAD_RAPTOR_DEAD', 25, None),
                ((5, 23), 'harpy', 'EVENT_PEON_ROAD_HARPY_DEAD', 25, None),
                ((18, 24), 'crawler', 'EVENT_PEON_COAST_CRAWLER_DEAD', 20, 'up')):
                s.navigate(approach)
                if face:
                    s.p.tick(240, True); assert s.read('wBattleMode') == [0], label + ' neutral aggroed'
                    s.press(face, 30); s.press('a')
                result = s.fight(label, flag, copper); report['battles'].append(result)
                assert result['outcome'] == 0
                s.rest(); s.to_valley(); s.navigate((28, 12), expected_map=16)
            assert s.read('wPartyMon1Level')[0] >= 4
            loads = s.encounter_loads
            start_hostile(s, (16, 17), 'scorpid_pack', 'EVENT_PEON_ROAD_SCORPID_PACK_DEAD', 40, report['battles'])
            assert s.encounter_loads == loads + 2, 'Scorpid pack was not two sequential native fights'
            assert s.event('EVENT_PEON_ROAD_SCORPID_PACK_FIRST')
            report['scorpid_pack_two_sequential_no_heal'] = True
            s.rest()  # Deliberately clear the pack's poison before the long revisit route.
            report['save_cold_restart'] = s.cold_restart()
            # Revisit every defeated actor tile and proximity trigger. No repeat battles or loot.
            before = s.money(); s.to_valley()
            for pos in ((16, 20), (16, 21)):
                s.navigate(pos); s.p.tick(120, True); assert s.read('wBattleMode') == [0]
            for pos in ((6, 6), (22, 8), (8, 16)):
                s.navigate(pos); assert s.collision_at(*pos) != 'WALL'
            assert all(s.event(flag) for flag in ('EVENT_PEON_CACTUS_DONE', 'EVENT_PEON_SARKOTH_DONE', 'EVENT_PEON_MEDALLION_DONE'))
            s.navigate((24, 4), expected_map=20)
            for pos in ((8, 10), (12, 8), (5, 6), (5, 3), (14, 3)):
                s.navigate(pos); s.press('a'); assert s.read('wBattleMode') == [0]
            s.navigate((10, 16), expected_map=15); s.navigate((28, 12), expected_map=16)
            for pos in ((5, 5), (18, 8), (5, 22), (18, 23), (16, 16)):
                s.navigate(pos); s.press('a'); assert s.read('wBattleMode') == [0]
            assert s.money() == before
            report['dead_actor_revisits_no_repeated_battle_or_loot'] = True
            report['cactus_terrain_disappearance_survives_cold_restart'] = True
            report['quests_reward_only_once'] = True
            report['all_checks_passed'] = True
            s.capture('road_all_encounters_remain_dead'); s.p.stop(save=False); s = None
    except Exception as exc:
        report['all_checks_passed'] = False; report['failure'] = repr(exc)
        if s:
            s.capture('unexpected_state'); s.p.stop(save=False)
        (OUT / 'validation_results.json').write_text(json.dumps(report, indent=2) + '\n')
        raise
    report['limitations'] = ['Physical Chromatic not exercised.', 'Full-pocket and escape/defeat fault cases are separate from this successful normal quest route.']
    (OUT / 'validation_results.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: finite encounters, three quests, deliberate inns and real battery-save persistence.')


if __name__ == '__main__':
    main()
