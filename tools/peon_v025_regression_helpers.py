#!/usr/bin/env python3
"""Current seven-zone contracts and read-only route adapters for retained tests.

These adapters change test navigation/source expectations, never game RAM,
ROM execution or success assertions. Historical source modules and published
reports remain untouched.
"""
from collections import deque
import ast
import hashlib
import inspect
import json
from pathlib import Path
import re
import subprocess
import textwrap

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/environment_v025'
BASE = '6d2a0be'


def map_ids(text):
    result, group, index = {}, 0, 0
    for line in text.splitlines():
        if re.match(r'^\s*newgroup\s+', line):
            group += 1; index = 0
        match = re.match(r'^\s*map_const\s+(\w+),\s*(\d+),\s*(\d+)', line)
        if match:
            index += 1
            result[match[1]] = (group, index, int(match[2]), int(match[3]))
    return result


def source_contract():
    import build_peon_valley_zones_v025 as zones
    import validate_peon_deep_source as saved
    old = lambda path: subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)
    preserved = ['ram/wram.asm', 'ram/sram.asm', 'constants/item_constants.asm',
                 'constants/music_constants.asm', 'constants/sfx_constants.asm', 'audio/sfx_pointers.asm']
    for path in preserved:
        assert (ROOT / path).read_bytes() == old(path), path
    old_ids = map_ids(old('constants/map_constants.asm').decode())
    new_ids = map_ids((ROOT / 'constants/map_constants.asm').read_text())
    assert all(new_ids.get(name) == value for name, value in old_ids.items()), 'Old map ID/group/dimension changed'
    new_maps = {name: values for name, values in new_ids.items() if name not in old_ids}
    assert {v[1] for v in new_maps.values()} == set(range(25, 30))
    assert all(v[0] == 26 and v[2:] == (5, 5) for v in new_maps.values())
    before, after = saved.flags(old('constants/event_flags.asm').decode()), saved.flags((ROOT / 'constants/event_flags.asm').read_text())
    assert all(after.get(name) == index for name, index in before.items()), 'Saved flag renumbered'
    additions = {name: value for name, value in after.items() if name not in before}
    assert all(318 <= value < 349 for value in additions.values()), additions
    assert len(after) == len(before) + len(additions)
    assert 'const_next 2048' in (ROOT / 'constants/event_flags.asm').read_text()
    assert (ROOT / 'data/tilesets/peon_collision.asm').read_bytes() == old('data/tilesets/peon_collision.asm')
    maps = {name: (ROOT / f'maps/{name}.blk').read_bytes() for name in zones.DIMS}
    graph = zones.validate(maps)
    assert maps == zones.build_maps(), 'Current authored seven-zone blocks differ from deterministic builder'
    # Keep all non-retired old interactions by index. Explicit changes are
    # documented rather than hidden behind blanket geometry equality.
    event_rows = lambda text, kind: re.findall(r'^\s*' + kind + r'\s+[^\n]+', text, re.M)
    objects = lambda text: re.findall(r'^\s*object_event\s+(\d+),\s*(\d+),\s*(\w+)', text, re.M)
    interaction_contract = {}
    for name in zones.paths.DIMS:
        previous, current = old(f'maps/{name}.asm').decode(), (ROOT / f'maps/{name}.asm').read_text()
        previous_actors, current_actors = objects(previous), objects(current)
        assert len(current_actors) >= len(previous_actors), (name, 'Saved actor slot removed')
        changes = []
        for i, original in enumerate(previous_actors, 1):
            actual = current_actors[i - 1]
            if name == 'ValleyOfTrials' and i in zones.RETIRED_OLD_VALLEY_ACTORS:
                assert actual[2] == 'SPRITE_NONE', (name, i, 'Duplicated old Valley actor still active')
                changes.append({'index': i, 'kind': 'retired duplicate; original saved slot retained'})
            elif name == 'TheDen' and i == 11:
                # User requested a mailbox; the optional second neutral boar
                # was explicitly replaced, leaving every quest actor intact.
                assert actual[:2] == ('16', '6') and actual[2] == 'SPRITE_PEON_MAILBOX', actual
                changes.append({'index': i, 'kind': 'optional neutral boar replaced by mailbox', 'xy': [16, 6]})
            else:
                assert actual == original, (name, i, 'Existing actor moved unexpectedly', original, actual)
        for kind in ('bg_event', 'coord_event'):
            old_rows, new_rows = event_rows(previous, kind), event_rows(current, kind)
            if name == 'ValleyOfTrials' and kind == 'coord_event':
                assert not new_rows, 'Retired exterior hostiles still have duplicate triggers'
            else:
                assert all(row in new_rows for row in old_rows), (name, kind, 'Existing interaction removed')
        old_warps, new_warps = event_rows(previous, 'warp_event'), event_rows(current, 'warp_event')
        if name in ('ValleyOfTrials', 'DurotarRoad', 'BurningBladeCavern'):
            # zones.validate checks exact reciprocal new targets and positions.
            assert len(new_warps) == len(old_warps)
        else:
            assert new_warps[:len(old_warps)] == old_warps, (name, 'Original door changed')
        interaction_contract[name] = {'original_slots_retained': len(previous_actors),
                                     'explicit_actor_changes': changes, 'appended_actors': len(current_actors) - len(previous_actors)}
    assert len((ROOT / 'data/tilesets/peon_metatiles.bin').read_bytes()) == 47 * 16
    frames = (ROOT / 'gfx/tilesets/peon_environment_fire.bin').read_bytes()
    graphics = (ROOT / 'gfx/tilesets/peon.2bpp').read_bytes()
    assert len(frames) == 96 and len(graphics) == 192 * 16 and graphics[:32] == frames[:32]
    assert (ROOT / 'gfx/tilesets/peon.png').read_bytes() != old('gfx/tilesets/peon.png')
    rom = (ROOT / 'pokecrystal.gbc').read_bytes()
    assert len(rom) == 2 * 1024 * 1024
    header = {'cgb_flag': rom[0x143], 'cartridge_type': rom[0x147], 'rom_size_code': rom[0x148], 'ram_size_code': rom[0x149]}
    assert header == {'cgb_flag': 192, 'cartridge_type': 16, 'rom_size_code': 6, 'ram_size_code': 3}
    assert (-sum(rom[0x134:0x14d]) - 25) & 255 == rom[0x14d]
    assert (sum(rom) - sum(rom[0x14e:0x150])) & 65535 == int.from_bytes(rom[0x14e:0x150], 'big')
    return {'rom_sha256': hashlib.sha256(rom).hexdigest(), 'baseline_commit': BASE,
            'all_checks_passed': True, 'preserved_inputs': preserved, 'all_existing_event_ids_preserved': True,
            'new_reserved_event_flags': additions, 'original_map_id_group_dimensions_preserved': True,
            'new_map_ids': new_maps, 'old_saved_walkable_cells_remain_walkable': True,
            'explicit_opened_old_wall_blocks': {name: sorted(cells) for name, cells in zones.OPENED_OLD_WALL_BLOCKS.items()},
            'movement_graph': graph, 'old_interaction_contract': interaction_contract,
            'native_metatiles': 47, 'native_tile_budget': 192, 'fire_phases': 3, 'animated_tiles': 2,
            'collision_table_byte_identical': True, 'native_header': header, 'physical_chromatic_tested': False}


def configure_routes(game):
    """Install current map metadata in this private Python validator process."""
    import build_peon_valley_zones_v025 as zones
    for name, number in zones.MAP_NUMBERS.items():
        if name in ('PeonOpening', 'GrommashHold'): continue
        game.MAPS[number] = (name, *zones.DIMS[name])
    return zones


def quest_session_class(retained):
    game = retained.game
    zones = configure_routes(game)
    base = retained.DeepQuestSession
    original_navigate = base.navigate
    original_talk_actor = base.talk_actor
    original_start_hostile = game.start_hostile

    class SevenZoneQuestSession(base):
        def live_actors(self, name):
            return [actor for actor in super().live_actors(name) if actor['sprite'] != 'SPRITE_NONE']

        def go_map(self, number):
            if self.map() == number: return
            rooms = {21, 22, 23, 24}
            if self.map() in rooms:
                current_name = game.MAPS[self.map()][0]
                event = next(event for event in zones.warp_events(current_name) if event['dynamic_room_return'])
                owner = self.read('wBackupMapNumber')[0]
                original_navigate(self, event['xy'], expected_map=owner)
                return self.go_map(number)
            graph = {}
            for name, current in zones.MAP_NUMBERS.items():
                if name in ('PeonOpening', 'GrommashHold'): continue
                graph[current] = []
                for event in zones.warp_events(name):
                    if event['dynamic_room_return']:
                        target = self.read('wBackupMapNumber')[0]
                    else:
                        target = zones.MAP_NUMBERS[event['target_name']]
                    # An unvisited shared room's future owner is not the
                    # current backup owner. Never invent an inn shortcut.
                    if current in rooms or target in rooms: continue
                    graph[current].append((target, event['xy']))
            queue, seen = deque([(self.map(), [])]), {self.map()}
            while queue:
                current, route = queue.popleft()
                if current == number:
                    for target, xy in route:
                        original_navigate(self, xy, expected_map=target)
                    assert self.map() == number
                    return
                for target, xy in graph.get(current, []):
                    if target not in seen:
                        seen.add(target); queue.append((target, route + [(target, xy)]))
            raise AssertionError(('No current native warp route', self.map(), number))

        def navigate(self, target, expected_map=None):
            target = tuple(target)
            if target == (24, 4) and expected_map == 20:
                return self.go_map(20)
            if target == (10, 16) and expected_map == 15 and self.map() == 20:
                # The old cave exit now returns through the real zone-six
                # corridor, preserving the old test's desired Valley endpoint.
                return self.go_map(15)
            if target == (5, 11) and expected_map is None:
                self.go_map(25)
                return original_navigate(self, (5, 5))
            return original_navigate(self, target, expected_map)

        def go_den(self):
            self.go_map(14)
            assert self.map() == 14

        def to_valley(self):
            self.go_map(15)
            assert self.map() == 15

        def cold_restart(self):
            self.go_den()
            before_flags = self.read('wEventFlags', 256)
            result = super().cold_restart()
            assert self.read('wEventFlags', 256) == before_flags, 'New sector/lesson flags changed at cold restart'
            result['all_256_event_bytes_and_new_sector_flags_preserved'] = True
            return result

        def talk_actor(self, script, label):
            matches = []
            for name, number in zones.MAP_NUMBERS.items():
                if name in ('PeonOpening', 'GrommashHold'): continue
                for actor in zones.object_events(name):
                    if actor['masked_placeholder'] or actor['sprite'].startswith('SPRITE_PEON_QUEST'): continue
                    owner = actor['script']
                    text = (ROOT / f'maps/{name}.asm').read_text()
                    wrapper = re.search(r'^' + re.escape(owner) + r':\s*\n\s*farsjump\s+' + re.escape(script) + r'\s*$', text, re.M)
                    if owner == script or wrapper:
                        matches.append((number, owner))
            assert len(matches) == 1, ('Missing or duplicate active quest speaker', script, matches)
            number, owner = matches[0]; self.go_map(number)
            return original_talk_actor(self, owner, label)

    def start_hostile(session, approach, label, flag, copper, battles):
        replacements = {'EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD': (28, (4, 6)),
                        'EVENT_PEON_CAVE_APPROACH_IMP_2_DEAD': (28, (7, 4)),
                        'EVENT_PEON_SARKOTH_DEAD': (27, (5, 4))}
        if flag in replacements:
            number, approach = replacements[flag]; session.go_map(number)
        return original_start_hostile(session, approach, label, flag, copper, battles)
    game.start_hostile = start_hostile
    retained.DeepQuestSession = SevenZoneQuestSession
    return SevenZoneQuestSession


def current_ui_main(retained):
    """Change only the obsolete one-stack starter assumption; keep assertions."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(retained.main)))
    class CurrentStarter(ast.NodeTransformer):
        changes = 0
        def visit_Assert(self, node):
            if ast.unparse(node.test) == "s.read('wNumItems') == [1] and s.qty(148) == 1":
                self.changes += 1
                node.test = ast.parse("s.read('wNumItems') == [3] and s.qty(148) == 1 and s.qty(63) == 1 and s.qty(18) == 2", mode='eval').body
            return self.generic_visit(node)
    transform = CurrentStarter(); tree = transform.visit(tree)
    assert transform.changes == 1, ('Retained UI starter contract changed', transform.changes)
    exec(compile(ast.fix_missing_locations(tree), str(retained.__file__), 'exec'), retained.__dict__)


def compare_upgrade_snapshot(before, after):
    """Only the seven new discovery bits may initialize during migration."""
    import validate_peon_deep_source as saved
    flags = saved.flags((ROOT / 'constants/event_flags.asm').read_text())
    sector_ids = [value for name, value in flags.items() if 342 <= value < 349]
    assert len(sector_ids) == 7, ('Exactly seven appended sector flags required', sector_ids)
    left, right = dict(before), dict(after)
    old_bits, new_bits = list(left.pop('event_flags')), list(right.pop('event_flags'))
    assert left == right, ('Old character/map/item/health/charge fields changed', left, right)
    assert len(old_bits) == len(new_bits) == 256
    masks = [0] * 256
    for i in sector_ids: masks[i // 8] |= 1 << (i % 8)
    for i, (old, new, mask) in enumerate(zip(old_bits, new_bits, masks)):
        assert (old ^ new) & (~mask & 255) == 0, ('Non-new-discovery saved bit changed', i, old, new, mask)
        assert old & mask & (~new & 255) == 0, ('Migration cleared prior discovery', i, old, new, mask)
    return True


def current_upgrade_main(retained):
    tree = ast.parse(textwrap.dedent(inspect.getsource(retained.main)))
    class CurrentMigration(ast.NodeTransformer):
        changes = 0
        def visit_Assert(self, node):
            if ast.unparse(node.test) == 's.snapshot() == before':
                self.changes += 1
                node.test = ast.parse('compare_upgrade_snapshot(before, s.snapshot())', mode='eval').body
            return self.generic_visit(node)
    transform = CurrentMigration(); tree = transform.visit(tree)
    assert transform.changes == 1, ('Retained upgrade snapshot contract changed', transform.changes)
    retained.compare_upgrade_snapshot = compare_upgrade_snapshot
    exec(compile(ast.fix_missing_locations(tree), str(retained.__file__), 'exec'), retained.__dict__)
