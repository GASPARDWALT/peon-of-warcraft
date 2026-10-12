#!/usr/bin/env python3
"""Observe new environment graphics through ordinary gameplay and real saves.

The primary route never writes RAM, patches the ROM, loads emulator states or
substitutes CPU outcomes. All temporary batteries are outside the checkout;
retained validators' output destinations alone are redirected for this run.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import logging
from pathlib import Path
import re
import shutil
import tempfile

import numpy as np
from PIL import Image

import run_peon_v023_validation as adapter
import validate_durotar_v022_quests as game
import validate_peon_villages as village
import validate_peon_world_polish as retained

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/environment_v025/runtime'
ZONE_LAYOUT = None


def configure_zone_layout():
    global ZONE_LAYOUT
    path = ROOT / 'references/generated/environment_v025/zone_layout/metadata.json'
    if not path.exists():
        ZONE_LAYOUT = None
        return
    ZONE_LAYOUT = json.loads(path.read_text())
    assert len(ZONE_LAYOUT['zones']) == 7
    for zone in ZONE_LAYOUT['zones']:
        width, height = zone['blocks']
        village.MAPS[zone['map_id']] = (zone['name'], width, height)


@contextmanager
def output_redirect():
    saved = []
    for entry in (game, retained):
        for module in adapter.local_dependencies(entry):
            for name in ('OUT', 'OUTPUT'):
                if hasattr(module, name):
                    saved.append((module, name, getattr(module, name)))
                    setattr(module, name, OUT)
    try:
        yield
    finally:
        for module, name, value in reversed(saved):
            setattr(module, name, value)


class EnvironmentSession(retained.WorldSession, game.QuestSession):
    def capture(self, label):
        self.p.screen.image.save(OUT / (label + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(
            OUT / (label + '_4x.png'))
        print(label, self.map(), self.position(), flush=True)

    def authored_blocks(self):
        name, width, height = village.MAPS[self.map()]
        expected = bytearray((ROOT / f'maps/{name}.blk').read_bytes())
        if self.map() == 15:
            for i, x, y in ((1, 6, 6), (2, 22, 8), (3, 8, 16)):
                if self.event('EVENT_PEON_CACTUS_' + str(i)):
                    expected[(y // 2) * width + x // 2] = 38
        bank, address = self.sym['wOverworldMapBlocks']
        actual = bytearray()
        for y in range(height):
            start = address + (y + 3) * (width + 6) + 3
            actual.extend(self.p.memory[bank, start:start + width])
        assert actual == expected, (name, 'Cached or incorrect authored block data')
        return {'map': name, 'current_authored_blocks_loaded': True,
                'harvested_cactus_callbacks_reapplied': True, 'bytes': len(actual)}

    def live_actors(self, name):
        return [actor for actor in super().live_actors(name) if actor['sprite'] != 'SPRITE_NONE']

    def path(self, target):
        from collections import deque
        name = village.MAPS[self.map()][0]
        live = self.live_actors(name)
        occupied = {actor['xy'] for actor in live}
        # A friendly guard can occupy either side of its authored anchor by
        # the time a D-pad step completes. Reserve that actual patrol radius;
        # enemy approach/quest interaction cells keep their original behavior.
        for row in (ROOT / f'maps/{name}.asm').read_text().splitlines():
            if not re.match(r'\s*object_event\s+', row): continue
            fields = [part.strip() for part in row.strip().split(' ', 1)[1].split(',')]
            if fields[2] not in ('SPRITE_OFFICER', 'SPRITE_LINK_RECEPTIONIST'): continue
            x, y = int(fields[0]), int(fields[1])
            if (x, y) not in occupied: continue
            if fields[3] == 'SPRITEMOVEDATA_WALK_LEFT_RIGHT':
                occupied.update((x+delta, y) for delta in (-1, 0, 1))
            elif fields[3] == 'SPRITEMOVEDATA_WALK_UP_DOWN':
                occupied.update((x, y+delta) for delta in (-1, 0, 1))
        scripts = {actor['script'] for actor in live}
        danger = {xy for xy, script in game.triggers(name).items() if script in scripts}
        warps = village.warp_tiles(name)
        start = self.position(); queue = deque([(start, [])]); seen = {start}
        while queue:
            (x, y), route = queue.popleft()
            if (x, y) == target: return route
            for key, dx, dy in village.DIRECTIONS:
                pos = (x+dx, y+dy)
                if pos in seen or pos in occupied or self.collision_at(*pos) == 'WALL': continue
                if pos in warps and pos != target: continue
                if pos in danger and pos != target: continue
                seen.add(pos); queue.append((pos, route+[key]))
        raise AssertionError((name, 'No safe ordinary path', start, target))

    def navigate(self, target, expected_map=None):
        target = tuple(target)
        name = village.MAPS[self.map()][0]
        warps = village.warp_tiles(name)
        if self.position() == target and target in warps:
            occupied = {actor['xy'] for actor in self.live_actors(name)}
            for key, dx, dy in village.DIRECTIONS:
                stand = (target[0]+dx, target[1]+dy)
                if self.collision_at(*stand) != 'WALL' and stand not in warps and stand not in occupied:
                    self.walk(key); break
            else:
                raise AssertionError(('No ordinary step away from current warp', name, target))
        path, origin = self.path(target), self.map()
        for i, key in enumerate(path):
            if target in warps and i == len(path)-1:
                before = self.position()
                for _ in range(8):
                    self.p.button(key, delay=4); self.p.tick(40, True)
                    if self.map() != origin or self.position() != before:
                        break
                self.p.tick(150, True)
            else:
                self.walk(key)
        if expected_map is None:
            assert self.map() == origin and self.position() == target, (
                origin, target, self.map(), self.position())
        else:
            assert self.map() == expected_map, (origin, target, expected_map, self.map(), self.position())

    def travel(self, destination):
        from collections import deque
        if self.map() in (21, 22, 23, 24):
            owner = self.read('wBackupMapNumber')[0]
            self.navigate((5, 7), expected_map=owner)
        names = {re.sub(r'(?<!^)(?=[A-Z])', '_', entry[0]).upper(): number
                 for number, entry in village.MAPS.items()}
        graph = {}
        for number, (name, _, _) in village.MAPS.items():
            graph[number] = [(names[match[3]], (int(match[1]), int(match[2]))) for match in re.finditer(
                r'^\s*warp_event\s+(\d+),\s*(\d+),\s*([A-Z_]+),',
                (ROOT / f'maps/{name}.asm').read_text(), re.M) if match[3] in names]
        start = self.map(); queue = deque([(start, [])]); seen = {start}
        while queue:
            node, route = queue.popleft()
            if node == destination:
                for next_map, xy in route:
                    self.navigate(xy, expected_map=next_map)
                return
            for next_map, xy in graph[node]:
                if next_map not in seen and next_map not in (21, 22, 23, 24):
                    seen.add(next_map); queue.append((next_map, route + [(next_map, xy)]))
        raise AssertionError(('No authored map graph route', start, destination))

    def go_den(self):
        if ZONE_LAYOUT is None:
            return super().go_den()
        self.travel(14)

    def to_valley(self):
        if ZONE_LAYOUT is None:
            return super().to_valley()
        self.travel(15)

    def talk_actor(self, script, label):
        name = village.MAPS[self.map()][0]
        actor = next(a for a in self.live_actors(name) if a['script'] == script
                     and not a['sprite'].startswith('SPRITE_PEON_QUEST'))
        options = []
        x, y = actor['xy']
        for direction, dx, dy in village.DIRECTIONS:
            stand = (x-dx, y-dy)
            try: path = self.path(stand)
            except AssertionError: continue
            options.append((len(path), stand, direction))
        assert options, ('No ordinary speaker approach', actor)
        _, stand, direction = min(options)
        self.talk(stand, direction, label)

    def terrain_upload(self):
        data = (ROOT / 'gfx/tilesets/peon.2bpp').read_bytes()
        assert len(data) == 192 * 16
        actual = [bytes(self.p.memory[bank, 0x9000:0x9600]) for bank in (0, 1)]
        phasefile = ROOT / 'gfx/tilesets/peon_environment_fire.bin'
        if not phasefile.exists():
            # Historical v0.2.4 only: its fire graphics were static.
            assert actual == [data[:96*16], data[96*16:]]
            return {'native_tiles_matching_vram': 192, 'historical_static_fire': True}
        phases = phasefile.read_bytes()
        assert len(phases) == 96
        bank, address = self.sym['PeonEnvironmentFireFrames']
        assert bytes(self.p.memory[bank, address:address+96]) == phases
        assert actual[0][32:] == data[32:96*16], 'Unrelated bank-zero scenery tile changed'
        assert actual[1] == data[96*16:], 'Bank-one scenery tile changed'
        state = []
        for part in (0, 1):
            tile = actual[0][part*16:(part+1)*16]
            matching = [i for i in range(3) if tile == phases[i*32+part*16:i*32+(part+1)*16]]
            assert matching, ('Invalid native fire tile phase', part, tile.hex())
            state.append(matching)
        return {'fixed_native_tiles_matching_both_vram_banks': 190,
                'animated_native_tiles_matching_allowed_phases': 2,
                'fire_left_right_matching_phases': state,
                'staggered_native_phase_updates_allowed': True}

    def continued_fire_cycle(self):
        if 'AnimatePeonEnvironmentFire' not in self.sym:
            return {'historical_static_fire': True}
        calls = [0]; seen = [set(), set()]
        self.p.hook_register(*self.sym['AnimatePeonEnvironmentFire'],
                             lambda _: calls.__setitem__(0, calls[0]+1), None)
        try:
            for _ in range(128):
                self.p.tick(1, True)
                native = self.terrain_upload()
                for part, matching in enumerate(native['fire_left_right_matching_phases']):
                    seen[part].update(matching)
        finally:
            self.p.hook_deregister(*self.sym['AnimatePeonEnvironmentFire'])
        assert calls[0] > 10 and seen == [{0, 1, 2}, {0, 1, 2}], (
            'Native fire animation pointer stale or inactive after cold Continue', calls, seen)
        return {'cold_continue_native_animation_callback_calls': calls[0],
                'every_left_and_right_fire_phase_observed': True,
                'other_190_native_tiles_preserved_every_frame': True,
                'frames_observed': 128}

    def palette_location(self):
        # Exact grouping in native LoadMapPals; no preview colors substituted.
        number = self.map()
        if 14 <= number <= 20:
            return 'PeonRegionBGPalettes', (number - 14) * 64
        if 21 <= number <= 24:
            return 'PeonInteriorBGPalettes', (1 if number in (22, 23) else 0) * 64
        if ZONE_LAYOUT is not None and 25 <= number <= 29:
            return 'PeonRegionBGPalettes', 64
        return 'PeonMapBGPalettes', 0

    def rendered_background(self, encoded):
        """Compare actual RGB555 pixels with live native tile/attribute data.

        Hardware OAM rectangles and any active window are excluded. Native
        sprites are tested elsewhere; this checks the scene's actual colors.
        """
        assert len(encoded) == 64
        colors = np.array([[(v & 31), (v >> 5) & 31, (v >> 10) & 31]
                           for v in (int.from_bytes(encoded[i:i+2], 'little')
                                     for i in range(0, 64, 2))], dtype=np.uint8)
        screen = np.asarray(self.p.screen.image.convert('RGB')) >> 3
        lcdc = self.p.memory[0xff40]
        tilemap_base = 0x9c00 if lcdc & 8 else 0x9800
        tilemap = np.array(list(self.p.memory[0, tilemap_base:tilemap_base+1024]), dtype=np.int16)
        attrs = np.array(list(self.p.memory[1, tilemap_base:tilemap_base+1024]), dtype=np.uint8)
        vram = [bytes(self.p.memory[b, 0x8000:0x9800]) for b in (0, 1)]
        mask = np.ones((144, 160), dtype=bool)
        sprite_height = 16 if lcdc & 4 else 8
        for i in range(0, 160, 4):
            y, x, _, _ = self.p.memory[0xfe00+i:0xfe00+i+4]
            px, py = x-8, y-16
            if px < 160 and px+8 > 0 and py < 144 and py+sprite_height > 0:
                mask[max(0, py):min(144, py+sprite_height), max(0, px):min(160, px+8)] = False
        expected = np.zeros_like(screen)
        palettes = Counter()
        scanlines = self.p.screen.tilemap_position_list
        for y in range(144):
            sx, sy, wx, wy = scanlines[y]
            if lcdc & 0x20 and y >= wy and wx < 160:
                mask[y, max(0, wx):] = False
            for x in range(160):
                xx, yy = (x+sx) & 255, (y+sy) & 255
                pos = (yy//8)*32 + xx//8
                number, attr = int(tilemap[pos]), int(attrs[pos])
                tx, ty = xx % 8, yy % 8
                if attr & 0x20: tx = 7-tx
                if attr & 0x40: ty = 7-ty
                offset = number*16 if lcdc & 0x10 else 0x1000 + (number if number < 128 else number-256)*16
                raw = vram[(attr >> 3) & 1]
                low, high = raw[offset+ty*2:offset+ty*2+2]
                index = ((low >> (7-tx)) & 1) | (((high >> (7-tx)) & 1) << 1)
                expected[y, x] = colors[(attr & 7)*4+index]
                if mask[y, x]: palettes[attr & 7] += 1
        mismatch = np.any(expected != screen, axis=-1) & mask
        assert int(mask.sum()) > 12000, ('Insufficient visible scenery pixels', int(mask.sum()))
        assert not np.any(mismatch), ('Native background RGB555 differs from live tiles/palettes',
                                      int(mismatch.sum()), np.argwhere(mismatch)[:10].tolist(),
                                      not np.any(mismatch & ~self.visible_fire_mask()))
        return {'actual_visible_native_bg_pixels_match_rgb555': True,
                'pixels_checked': int(mask.sum()), 'visible_palette_pixel_counts': dict(palettes),
                'sprite_rectangles_and_window_excluded': True}

    def scenery(self, label):
        self.p.tick(90, True)
        assert self.read('wScriptMode') == [0] and self.read('wBattleMode') == [0]
        terrain, vram = self.authored_blocks(), self.terrain_upload()
        palette, offset = self.palette_location()
        bank, address = self.sym[palette]
        expected = bytes(self.p.memory[bank, address+offset:address+offset+64])
        base = bytes(self.read('wBGPals1', 64))
        assert base[:56] == expected[:56], (label, palette, 'Base scenery RGB555 palette differs')
        actual = bytes(self.read('wBGPals2', 64))
        assert actual[:56] == expected[:56], (label, palette, 'Active scenery RGB555 palette differs')
        assert actual == base, (label, 'Active and base palette publication differs')
        # A tick may finish after a VBlank fire write but expose the preceding
        # raster image. Wait for one complete matching frame only when every
        # differing pixel is an independently verified native fire tile.
        for waited in range(9):
            try:
                pixels = self.rendered_background(actual)
                break
            except AssertionError as error:
                detail = error.args[0]
                if not (isinstance(detail, tuple) and len(detail) == 4 and detail[0] ==
                        'Native background RGB555 differs from live tiles/palettes' and detail[3]):
                    raise
                if waited == 8: raise
                self.p.tick(1, True)
                self.terrain_upload()
        pixels['native_raster_alignment_waited_frames'] = waited
        self.capture(label)
        return {'map_id': self.map(), 'position': self.position(), 'terrain': terrain,
                'vram': vram, 'palette_rom_label': palette, 'palette_table_byte_offset': offset,
                'palette_rgb555_bytes': list(expected),
                'seven_scenery_palettes_match_native_table': True,
                'reserved_font_portrait_palette_7': 'Read live; intentionally may retain last portrait colors.',
                'screen': pixels}

    def visible_fire_mask(self):
        lcdc = self.p.memory[0xff40]
        base = 0x9c00 if lcdc & 8 else 0x9800
        tilemap = np.array(list(self.p.memory[0, base:base+1024]))
        attrs = np.array(list(self.p.memory[1, base:base+1024]))
        mask = np.zeros((144, 160), dtype=bool)
        columns = np.arange(160)
        for y, (sx, sy, wx, wy) in enumerate(self.p.screen.tilemap_position_list):
            pos = ((y+sy) & 255)//8*32 + ((columns+sx) & 255)//8
            mask[y] = (tilemap[pos] < 2) & ((attrs[pos] & 8) == 0)
            if lcdc & 0x20 and y >= wy and wx < 160:
                mask[y, max(0, wx):] = False
        sprite_height = 16 if lcdc & 4 else 8
        for i in range(0, 160, 4):
            y, x, _, _ = self.p.memory[0xfe00+i:0xfe00+i+4]
            px, py = x-8, y-16
            if px < 160 and px+8 > 0 and py < 144 and py+sprite_height > 0:
                mask[max(0, py):min(144, py+sprite_height), max(0, px):min(160, px+8)] = False
        return mask


def visit_doors(s, name, report, visited):
    doors = [(int(m[1]), int(m[2]), m[3]) for m in re.finditer(
        r'^\s*warp_event\s+(\d+),\s*(\d+),\s*(PEON_(?:ORC|TROLL)_(?:INN|HUT)),',
        (ROOT / f'maps/{name}.asm').read_text(), re.M)]
    types = {'PEON_TROLL_HUT': 21, 'PEON_ORC_HUT': 22, 'PEON_ORC_INN': 23, 'PEON_TROLL_INN': 24}
    for i, (x, y, target) in enumerate(doors):
        origin, dest = s.map(), types[target]
        options = []
        for dx, dy in ((0, 1), (-1, 0), (1, 0), (0, -1)):
            stand = (x+dx, y+dy)
            try: path = s.path(stand)
            except AssertionError: continue
            options.append((0 if dy == 1 else 1, len(path), stand))
        assert options, ('Door has no ordinary exterior threshold', name, x, y)
        _, _, stand = min(options)
        s.navigate(stand)
        entry = {'origin_map': origin, 'door': [x, y], 'room_id': dest,
                 'outside_threshold': s.scenery(f'{name}_door_{i+1}_outside')}
        s.navigate((x, y), expected_map=dest)
        entry['inside_threshold'] = s.scenery(f'{name}_door_{i+1}_inside')
        if dest not in visited:
            s.walk('up')
            result = s.restart_room(f'room_{dest}')
            result['continued_fire_cycle'] = s.continued_fire_cycle()
            result['continued_native_scene'] = s.scenery(f'room_{dest}_continued_native_scene')
            report['room_cold_restarts'].append(result)
            visited.add(dest)
        s.navigate((5, 7), expected_map=origin)
        assert s.position() == (x, y), (name, 'Door returns to incorrect origin', s.position(), (x, y))
        entry['outside_return'] = s.scenery(f'{name}_door_{i+1}_returned')
        entry['returns_to_exact_origin_door_after_cold_restart'] = True
        report['door_routes'].append(entry)


def check_mailbox(s, name, report):
    script = name + 'MailboxScript'
    actor = next((a for a in s.live_actors(name) if a['script'] == script), None)
    if actor is None:
        return
    x, y = actor['xy']; options = []
    for direction, dx, dy in village.DIRECTIONS:
        stand = (x-dx, y-dy)
        try: path = s.path(stand)
        except AssertionError: continue
        options.append((len(path), stand, direction))
    assert options
    _, stand, direction = min(options)
    s.navigate(stand)
    def state():
        return s.snapshot() | {'key_items': s.read('wKeyItems', s.read('wNumKeyItems')[0])}
    before = state()
    s.talk(stand, direction, name + '_mailbox_actual_native_dialogue')
    after = state()
    assert after == before, ('Decorative mailbox changed inventory, copper, quests or character', name,
                             {key: [before[key], after[key]] for key in before if before[key] != after[key]})
    report.setdefault('mailboxes', []).append({
        'map': name, 'ordinary_walk_and_dialogue': True,
        'inventory_copper_full_saved_event_flags_and_character_unchanged': True,
        'scene_after_close': s.scenery(name + '_mailbox_closed_environment_restored'),
        'network_or_real_mail_backend': False})


def cave_and_cacti(s, report):
    s.to_valley()
    s.talk((8, 11), 'up', 'cactus_quest_accept_native_dialogue')
    assert s.event('EVENT_PEON_CACTUS_ACCEPTED')
    for position, facing, number, former_cell in (
            ((8, 7), 'left', 1, (7, 7)), ((24, 9), 'left', 2, (23, 9)),
            ((10, 17), 'left', 3, (9, 17))):
        s.navigate(position)
        entry = {'number': number, 'before': s.scenery(f'cactus_{number}_before_harvest')}
        s.talk(position, facing, f'cactus_{number}_native_harvest_dialogue')
        assert s.event('EVENT_PEON_CACTUS_' + str(number))
        assert s.collision_at(*former_cell) == 'FLOOR'
        s.navigate(former_cell)
        entry['after'] = s.scenery(f'cactus_{number}_harvested_walkable')
        report['cactus_harvests'].append(entry)
    report['cactus_cold_restart'] = s.restart_room('valley_three_harvests')
    report['cactus_cold_restart']['continued_fire_cycle'] = s.continued_fire_cycle()
    report['cactus_cold_restart']['scene'] = s.scenery('valley_three_harvests_cold_continued')
    for number, cell in ((1, (7, 7)), (2, (23, 9)), (3, (9, 17))):
        assert s.event('EVENT_PEON_CACTUS_' + str(number)) and s.collision_at(*cell) == 'FLOOR'
    if ZONE_LAYOUT is not None:
        s.navigate((24, 4))
        assert s.map() == 15, 'Retired Valley cave threshold still loads an old map'
        report['retired_valley_cave_threshold_is_walkable_and_has_no_warp'] = s.scenery(
            'retired_old_valley_cave_threshold_no_warp')
        s.go_den()
        return
    options = []
    for stand in ((24, 5), (23, 4), (25, 4), (24, 3)):
        try: path = s.path(stand)
        except AssertionError: continue
        options.append((len(path), stand))
    report['cave']['initial_safe_exterior_thresholds'] = [list(stand) for _, stand in options]
    if not options:
        # The original guard spans both cells of the narrow cave corridor.
        # Establish access by winning its actual encounter, never by hiding it.
        s.rest(); s.to_valley(); s.navigate((24, 6))
        result = s.fight('native_blocking_cave_approach_imp', 'EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD', 30)
        assert result['outcome'] == 0
        report['cave']['ordinary_blocking_guard_victory'] = result
        s.rest(); s.to_valley()
        for stand in ((24, 5), (23, 4), (25, 4), (24, 3)):
            try: path = s.path(stand)
            except AssertionError: continue
            options.append((len(path), stand))
    assert options, 'Native cave threshold inaccessible even after clearing the blocking guard'
    _, threshold = min(options)
    s.navigate(threshold)
    report['cave']['outside'] = s.scenery('burning_blade_cave_outside_threshold')
    loads = s.encounter_loads
    s.navigate((24, 4), expected_map=20)
    report['cave']['inside'] = s.scenery('burning_blade_cave_inside_threshold')
    s.navigate((10, 16), expected_map=15)
    assert s.position() == (24, 4)
    assert s.encounter_loads == loads, 'Safe cave threshold unexpectedly triggered a hostile encounter'
    report['cave']['returned'] = s.scenery('burning_blade_cave_exact_outside_return')
    report['cave'].update(ordinary_buttons_only=True, native_enter_and_return=True,
                          exact_exterior_return=True, no_guard_ram_edits=True)
    s.go_den()


def earn_map_and_check_overlays(s, report):
    """The new scenery survives genuine combat, dialogue and native menus."""
    battles = []
    s.talk((10, 10), 'up', 'native_gornek_cutting_teeth_accept')
    s.navigate((18, 13)); s.press('up', 30); s.press('a')
    result = s.fight('native_boar_map_progression', 'EVENT_PEON_QUEST_DONE')
    assert result['outcome'] == 0
    battles.append(result)
    s.talk((10, 10), 'up', 'native_gornek_sting_accept')
    assert s.event('EVENT_PEON_STING_ACCEPTED')
    s.rest()
    s.navigate((17, 15))
    result = s.fight('native_scorpid_map_progression', 'EVENT_PEON_SCORPID_DEFEATED')
    assert result['outcome'] == 0
    battles.append(result)
    s.talk((10, 10), 'up', 'native_gornek_earned_map_reward')
    assert s.event('EVENT_PEON_MAP_RECEIVED')
    s.rest()
    report['map_earned_with_ordinary_quest_battles'] = battles
    s.navigate((13, 9))
    checks = {}
    for item, downs in (('character', 0), ('bags', 1)):
        before = s.snapshot()
        s.press('start')
        for _ in range(10):
            if s.read('wMenuCursorPosition') == [1]: break
            s.press('up', 30)
        assert s.read('wMenuCursorPosition') == [1]
        for _ in range(downs): s.press('down', 30)
        s.press('a'); s.capture(item + '_overlay_on_new_environment')
        s.press('b'); s.press('b'); s.p.tick(90, True)
        assert s.snapshot() == before
        checks[item] = s.scenery(item + '_closed_new_environment_restored')
    before = s.snapshot()
    observed = []
    s.p.hook_register(*s.sym['PeonDrawAtlasQuests'], lambda _: observed.append(s.map()), None)
    try:
        s.press('select', 180)
        page = s.read('wMenuCursorY')[0]
        assert observed and page in (0, 1), 'Earned atlas did not load a native Valley/Den page'
        assert page == 0 if ZONE_LAYOUT is None else page == 1, 'New seven-sector overview must open on Valley'
        native = (ROOT / f'gfx/peon_maps/{"den" if page == 0 else "valley"}.bin').read_bytes()
        assert bytes(s.p.memory[0, 0x9000:0x9800]) == native[:2048]
        assert bytes(s.p.memory[0, 0x8800:0x9000]) == native[2048:4096]
        assert bytes(s.p.memory[1, 0x9000:0x9680]) == native[4096:5760]
        s.capture('earned_atlas_over_new_environment')
        s.press('b', 180)
    finally:
        s.p.hook_deregister(*s.sym['PeonDrawAtlasQuests'])
    assert s.snapshot() == before
    assert s.read('wScriptMode') == [0]
    bank, address = s.sym['Font']
    font = bytes(s.p.memory[bank, address:address+1024])
    expected = bytes(c for value in font for c in (value, value))
    assert bytes(s.p.memory[0, 0x8800:0x9000]) == expected, 'Actual native Font was not restored after atlas'
    checks['earned_atlas'] = s.scenery('earned_atlas_closed_new_environment_restored')
    checks['earned_atlas']['actual_native_chart_uploaded_in_both_banks'] = True
    checks['earned_atlas']['native_atlas_page'] = page
    report['native_overlay_returns'] = checks


def fire_animation(s, report):
    phases = (ROOT / 'gfx/tilesets/peon_environment_fire.bin').read_bytes()
    assert len(phases) == 96
    s.navigate((13, 9)); s.scenery('native_den_campfire_before_animation_capture')
    seen = [set(), set()]; sample = []; frame_images = []; native_calls = [0]
    fire_pixels = set(); visible_counts = []
    def observed(_unused):
        native_calls[0] += 1
    s.p.hook_register(*s.sym['AnimatePeonEnvironmentFire'], observed, None)
    try:
        for frame in range(512):
            s.p.tick(1, True)
            native = s.terrain_upload()
            for part, matching in enumerate(native['fire_left_right_matching_phases']):
                seen[part].update(matching)
            if frame % 8 == 0:
                sample.append({'frame': frame, 'left_right_phases': native['fire_left_right_matching_phases']})
                frame_images.append(s.p.screen.image.copy())
                mask = s.visible_fire_mask()
                visible_counts.append(int(mask.sum()))
                fire_pixels.add((np.asarray(s.p.screen.image.convert('RGB')) >> 3)[mask].tobytes())
    finally:
        s.p.hook_deregister(*s.sym['AnimatePeonEnvironmentFire'])
    assert native_calls[0] > 80, ('Native tile animation callback did not execute repeatedly', native_calls)
    assert seen == [{0, 1, 2}, {0, 1, 2}], ('Native fire did not show every left/right phase', seen)
    assert min(visible_counts) >= 64, 'No actual native fire tiles visible in animation capture'
    assert len(fire_pixels) >= 3, 'Visible fire RGB555 pixels did not animate'
    path = OUT / 'native_den_campfire_animation.gif'
    frame_images[0].save(path, save_all=True, append_images=frame_images[1:], duration=133,
                         loop=0, disposal=2, optimize=False)
    enlarged = [im.resize((640, 576), Image.Resampling.NEAREST) for im in frame_images]
    enlarged[0].save(OUT / 'native_den_campfire_animation_4x.gif', save_all=True,
                     append_images=enlarged[1:], duration=133, loop=0, disposal=2, optimize=False)
    report['native_fire_animation'] = {
        'ordinary_buttons_only': True, 'frames_observed': 512,
        'native_animation_callback_calls': native_calls[0],
        'left_right_phases_observed': [sorted(x) for x in seen],
        'other_190_native_tiles_unchanged_every_observed_frame': True,
        'visible_fire_tile_pixels_per_frame_minimum': min(visible_counts),
        'distinct_actual_visible_fire_rgb555_frames': len(fire_pixels),
        'no_palette_oam_or_save_state_substitution': True,
        'actual_native_frames_gif': path.name, 'samples': sample,
        'final_scene': s.scenery('native_den_campfire_after_animation_capture')}


def seven_sector_graph(s, report):
    """Traverse the authored directed layout and every reciprocal return."""
    assert ZONE_LAYOUT is not None
    records = []
    by_number = {zone['zone']: zone for zone in ZONE_LAYOUT['zones']}
    edges = ZONE_LAYOUT['edges']
    # Visit the user-requested northwestern loop, northern approach, then the
    # fortified eastern exit. Each link is proved in both directions.
    order = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 1), (3, 6), (2, 7), (7, None)]
    for from_zone, to_zone in order:
        edge = next(e for e in edges if (e['from_zone'], e['to_zone']) == (from_zone, to_zone)
                        and e['to_map_id'] != 20)
        s.travel(edge['from_map_id'])
        if from_zone == 4 and to_zone == 5:
            s.talk_actor('PeonCampHanazuaScript', 'zone_4_hanazua_actual_sarkoth_quest')
            assert s.event('EVENT_PEON_SARKOTH_ACCEPTED')
        if from_zone == 5 and not s.event('EVENT_PEON_SARKOTH_DEAD'):
            s.navigate((5, 4))
            result = s.fight('zone_5_actual_sarkoth_blocking_passage', 'EVENT_PEON_SARKOTH_DEAD', 35)
            assert result['outcome'] == 0
            report['zone_5_ordinary_sarkoth_victory'] = result
        source_position, target_position = tuple(edge['source_xy']), tuple(edge['target_xy'])
        s.navigate(source_position, expected_map=edge['to_map_id'])
        assert s.position() == target_position, ('Wrong sector arrival', edge, s.position())
        record = {'from_zone': from_zone, 'to_zone': to_zone, 'direction': edge['direction'],
                  'source_map': edge['from_map_id'], 'destination_map': edge['to_map_id'],
                  'source_xy': source_position, 'target_xy': target_position,
                  'forward': s.scenery(f'zone_{from_zone}_to_{to_zone or "road"}_{edge["direction"].lower()}')}
        s.navigate(target_position, expected_map=edge['from_map_id'])
        assert s.position() == source_position, ('Wrong reciprocal sector return', edge, s.position())
        record['reverse'] = s.scenery(f'zone_{to_zone or "road"}_back_to_{from_zone}_exact_return')
        record['ordinary_bidirectional_travel_verified'] = True
        records.append(record)
    s.travel(28)
    # Both level-three guards are genuine native encounters. Rest is an
    # explicitly chosen inn interaction rather than an artificial HP reset.
    battles = []
    for position, flag, label in (
            ((4, 6), 'EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD', 'new_zone_6_first_familiar'),
            ((5, 4), 'EVENT_PEON_CAVE_APPROACH_IMP_2_DEAD', 'new_zone_6_second_familiar')):
        s.rest(); s.travel(28)
        encoded = s.read('wOBPals2', 64)[50:52]
        red = int.from_bytes(bytes(encoded), 'little')
        assert (red & 31, (red >> 5) & 31, (red >> 10) & 31) == (27, 5, 3), 'New cave-approach imps lost actual red OBJ6'
        if not s.event(flag):
            s.navigate(position)
            result = s.fight(label, flag, 30)
            assert result['outcome'] == 0
            battles.append(result)
    s.rest(); s.travel(28)
    edge = next(e for e in edges if e['from_map_id'] == 28 and e['to_map_id'] == 20)
    s.navigate((5, 3))
    report['cave']['outside'] = s.scenery('zone_6_sole_cave_outside_threshold')
    s.navigate(tuple(edge['source_xy']), expected_map=20)
    assert s.position() == tuple(edge['target_xy'])
    report['cave']['inside'] = s.scenery('zone_6_cave_inside_threshold')
    s.navigate(tuple(edge['target_xy']), expected_map=28)
    assert s.position() == tuple(edge['source_xy'])
    report['cave']['returned'] = s.scenery('zone_6_cave_exact_exterior_return')
    report['cave'].update(ordinary_buttons_only=True, native_enter_and_return=True,
                          exact_exterior_return=True, cave_owner_map=28,
                          retired_valley_cave_unloaded=True, approach_battles=battles)
    report['cave']['native_sector_battery_restart'] = s.restart_room('zone_6_cave_entrance_saved')
    report['cave']['native_sector_battery_restart']['continued_fire_cycle'] = s.continued_fire_cycle()
    for flag in ('EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD', 'EVENT_PEON_CAVE_APPROACH_IMP_2_DEAD'):
        assert s.event(flag), 'Retired cave guard reappeared after native battery restart'
    s.travel(20)
    s.navigate(tuple(edge['target_xy']), expected_map=28)
    assert s.position() == tuple(edge['source_xy'])
    report['cave']['cold_battery_return_keeps_new_zone_6_owner'] = True
    records.append({'from_zone': 6, 'to_zone': None, 'destination_map': 20,
                    'direction': 'UP', 'ordinary_bidirectional_travel_verified': True})
    report['seven_sector_geography'] = {
        'zone_metadata_sha256': hashlib.sha256((ROOT / 'references/generated/environment_v025/zone_layout/metadata.json').read_bytes()).hexdigest(),
        'seven_distinct_sector_maps': [by_number[i]['map_id'] for i in range(1, 8)],
        'all_nine_directed_edges_and_returns_walked': len(records) == 9,
        'reference_direction_order': ['1 RIGHT 2', '2 UP 3', '3 LEFT 4', '4 DOWN 5',
                                     '5 RIGHT 1', '3 UP 6', '2 RIGHT 7', '7 RIGHT ROAD', '6 UP CAVE'],
        'edge_records': records}
    assert len(records) == 9
    s.travel(16)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-sha', required=True)
    args = parser.parse_args()
    sha = hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest()
    assert sha == args.expected_sha
    OUT.mkdir(parents=True, exist_ok=True)
    logging.disable(logging.CRITICAL)
    configure_zone_layout()
    report = {'rom_sha256': sha, 'passed': False, 'normal_buttons_only': True,
              'ram_edits': False, 'emulator_states_loaded': False, 'read_only_observers': True,
              'door_routes': [], 'room_cold_restarts': [], 'cactus_harvests': [], 'cave': {},
              'outdoor_regions': [], 'physical_chromatic_tested': False}
    s = None
    try:
        with output_redirect(), tempfile.TemporaryDirectory(prefix='peon-environment-v025-') as directory:
            rom = Path(directory) / 'test.gbc'
            shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = EnvironmentSession(rom, village.load_symbols())
            s.fresh()
            report['outdoor_regions'].append(s.scenery('fresh_character_the_den_environment'))
            earn_map_and_check_overlays(s, report)
            fire_animation(s, report)
            visited = set()
            visit_doors(s, 'TheDen', report, visited)
            check_mailbox(s, 'TheDen', report)
            cave_and_cacti(s, report)
            if ZONE_LAYOUT is None:
                s.navigate((20, 10), expected_map=15)
                report['outdoor_regions'].append(s.scenery('valley_native_exit_road'))
                s.navigate((28, 12), expected_map=16)
            else:
                seven_sector_graph(s, report)
            report['outdoor_regions'].append(s.scenery('durotar_road_native_trees_and_paths'))
            s.navigate((12, 24), expected_map=17)
            report['outdoor_regions'].append(s.scenery('senjin_native_coastal_arrival'))
            visit_doors(s, 'SenjinVillage', report, visited)
            check_mailbox(s, 'SenjinVillage', report)
            s.navigate((10, 4), expected_map=16)
            s.navigate((12, 4), expected_map=18)
            report['outdoor_regions'].append(s.scenery('razor_hill_native_horde_arrival'))
            visit_doors(s, 'RazorHill', report, visited)
            check_mailbox(s, 'RazorHill', report)
            s.navigate((12, 4), expected_map=19)
            report['outdoor_regions'].append(s.scenery('orgrimmar_gate_native_boundary'))
            assert len(report['door_routes']) == 9 and visited == {21, 22, 23, 24}
            assert len(report['cactus_harvests']) == 3
            assert hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest() == sha
            s.p.stop(save=False); s = None
            report['passed'] = True
    except Exception as error:
        report['failure'] = repr(error)
        if s:
            s.capture('unexpected_native_state'); s.p.stop(save=False); s = None
        raise
    finally:
        (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS actual scenery pixels, native palettes, nine doors, cave and three harvested cactus batteries', sha)


if __name__ == '__main__':
    main()
