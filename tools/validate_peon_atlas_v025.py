#!/usr/bin/env python3
"""Native seven-sector atlas QA, without writing game code or old evidence.

Ordinary new-game controls earn the map, explore every sector, move the actual
avatar, accept quests, pick cacti, clear the two entrance guards and use linked
room doors. An explicitly separate diagnostic section changes only temporary
quest/discovery/coordinate RAM. Hooks inspect native execution and rendering;
they never replace CPU results, save data, OAM, palettes, fonts or tile uploads.
"""
import argparse
import copy
import hashlib
import io
import json
import logging
from pathlib import Path
import re
import shutil
import tempfile

import numpy as np
from PIL import Image

import validate_durotar_v022_quests as game
import validate_peon_environment_v025 as environment
import validate_peon_villages as village
from validate_peon_atlas_player_objectives import (
    AtlasSession as PreviousAtlas, background, decode_tile, palette)
from validate_peon_combat_lifecycle import symbols_from

ROOT = Path(__file__).resolve().parents[1]
BASE_OUT = ROOT / 'references/generated/environment_v025/atlas_overview'
OUT = BASE_OUT / 'runtime'
GEOMETRY = None
GLYPHS = None
STYLES = None
SECTORS = None


def load_geometry():
    global GEOMETRY, GLYPHS, STYLES, SECTORS
    overview = json.loads((BASE_OUT / 'geometry_manifest.json').read_text())
    GEOMETRY = json.loads((ROOT / 'references/generated/valley_layout_update/atlas/geometry_manifest.json').read_text())
    GEOMETRY['overview'] = overview
    GLYPHS = ((ROOT / 'gfx/pack/peon_quest_poi.2bpp').read_bytes()
              + (ROOT / 'gfx/pack/peon_atlas_avatar.2bpp').read_bytes())
    STYLES = json.loads((ROOT / 'references/generated/durotar_v022/quest_markers/manifest.json').read_text())
    SECTORS = [dict(row, map_number=int(key), fog_tile_rect=row['fog_tiles'])
               for key, row in overview['projections'].items()]
    assert len(SECTORS) == 7
    assert {entry['zone'] for entry in SECTORS} == set(range(1, 8))


def project(region, map_number, xy):
    x, y = xy
    if region == 'VALLEY':
        matches = [sector for sector in SECTORS if sector['map_number'] == map_number]
        if len(matches) != 1:
            return None
        geometry = matches[0]
    else:
        geometry = GEOMETRY['pages'][region]
        if geometry['map_number'] != map_number:
            return None
    width, height = geometry['collision_size']
    if not (0 <= x < width and 0 <= y < height):
        return None
    return [geometry['y_centers'][y] + 12, geometry['x_centers'][x] + 4]


class AtlasSession(environment.EnvironmentSession):
    def __init__(self, rom, symbols):
        self.atlas_calls = []
        self.observer_errors = []
        self.fire_calls = 0
        self.map_entries = []
        super().__init__(rom, symbols)
        self.p.hook_register(*self.sym['PeonDrawAtlasQuests'], self.entering, None)
        bank, address = self.sym['PeonDrawAtlasQuests.done']
        self.p.hook_register(bank, address + 4, self.returning, None)
        self.p.hook_register(*self.sym['AnimatePeonEnvironmentFire'],
                             lambda _: setattr(self, 'fire_calls', self.fire_calls + 1), None)
        self.p.hook_register(*self.sym['PeonZoneMap.input'],
                             lambda _: self.map_entries.append(self.read('wMenuCursorY')[0]), None)

    def live_actors(self, name):
        actors = super().live_actors(name)
        # A friendly patrol can move into the precomputed next cell while
        # menus consume frames. Reserve its authored movement footprint;
        # read-only route planning must not treat its anchor as its only cell.
        rows = [line for line in (ROOT / 'maps' / (name + '.asm')).read_text().splitlines()
                if re.match(r'\s*object_event\s+', line)]
        result = list(actors)
        for actor in actors:
            fields = [part.strip() for part in rows[actor['index'] - 1].strip().split(' ', 1)[1].split(',')]
            if fields[2] != 'SPRITE_OFFICER' or not any(word in fields[3] for word in ('WALK_', 'WANDER')):
                continue
            rx, ry = int(fields[4]), int(fields[5])
            x, y = actor['xy']
            for dy in range(-ry, ry + 1):
                for dx in range(-rx, rx + 1):
                    if dx or dy:
                        result.append(dict(actor, xy=(x + dx, y + dy), patrol_footprint=True))
        return result

    def registers(self):
        return {name: getattr(self.p.register_file, name)
                for name in ('A', 'F', 'B', 'C', 'D', 'E', 'HL', 'SP')}

    def background_vram(self):
        return [bytes(self.p.memory[0, 0x8800:0x9800]),
                bytes(self.p.memory[1, 0x9000:0x9680])]

    def entering(self, _):
        self.atlas_calls.append({'registers': self.registers(),
            'vbk': self.p.memory[0xff4f] & 1, 'wram_bank': self.p.memory[0xff70] & 7,
            'lcdc': self.p.memory[0xff40],
            'scroll': [self.p.memory[0xff42], self.p.memory[0xff43]],
            'oam_update': self.read('hOAMUpdate'), 'events': self.read('wEventFlags', 256),
            'background_vram': self.background_vram(),
            'bg_palettes': [self.read('wBGPals1', 64), self.read('wBGPals2', 64)],
            'obj_palettes_0_to_5': [self.read('wOBPals1', 48), self.read('wOBPals2', 48)]})

    def returning(self, _):
        try:
            state = self.atlas_calls[-1]
            for field, actual in (
                    ('registers', self.registers()),
                    ('vbk', self.p.memory[0xff4f] & 1),
                    ('wram_bank', self.p.memory[0xff70] & 7),
                    ('lcdc', self.p.memory[0xff40]),
                    ('scroll', [self.p.memory[0xff42], self.p.memory[0xff43]]),
                    ('oam_update', self.read('hOAMUpdate')),
                    ('events', self.read('wEventFlags', 256)),
                    ('background_vram', self.background_vram()),
                    ('bg_palettes', [self.read('wBGPals1', 64), self.read('wBGPals2', 64)]),
                    ('obj_palettes_0_to_5', [self.read('wOBPals1', 48), self.read('wOBPals2', 48)])):
                assert state[field] == actual, ('Atlas overlay corrupted', field)
            state['verified'] = True
        except Exception as error:
            self.observer_errors.append(repr(error))

    def capture(self, name):
        self.p.screen.image.save(OUT / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(
            OUT / (name + '_4x.png'))
        print(name, 'map', self.map(), 'xy', self.position(), flush=True)

    def flag(self, short):
        return self.event('EVENT_PEON_' + short)

    def sector_known(self, map_number):
        matches = [sector for sector in SECTORS if sector['map_number'] == map_number]
        return len(matches) == 1 and self.event(matches[0]['discovery_flag'])

    def on_page(self, region, map_number):
        if region == 'VALLEY':
            return self.sector_known(map_number)
        page = GEOMETRY['pages'][region]
        return page['map_number'] == map_number and self.flag('DISCOVERED_' + region)

    def expected_points(self, region):
        entries, points = [], []

        def append(kind, identity, map_number, xy, tile=0, pal=4, **details):
            if not self.on_page(region, map_number):
                return
            coordinate = project(region, map_number, xy)
            if coordinate is None and kind == 'player':
                return
            assert coordinate is not None, ('Out-of-range authored atlas landmark', identity, map_number, xy)
            entries.append([*coordinate, tile, pal])
            points.append({'type': kind, 'identity': identity, 'map_number': map_number,
                           'xy': list(xy), **details})

        map_number, xy = self.map(), self.position()
        if 21 <= map_number <= 24:
            owner, warp = self.read('wBackupMapNumber')[0], self.read('wBackupWarpNumber')[0]
            doors = [door for door in GEOMETRY['doors'] if
                     (door['room'], door['map'], door['warp']) == (map_number, owner, warp)]
            if self.read('wBackupMapGroup') == [26] and len(doors) == 1:
                append('player', 'ACTUAL_EXTERIOR_DOOR', owner, doors[0]['xy'], 2, 6,
                       meaning='Exact exterior return door while inside linked room')
        elif self.read('wMapGroup') == [26]:
            append('player', 'ACTUAL_MOVEMENT_CELL', map_number, xy, 2, 6,
                   meaning='Actual saved current map and movement cell')

        def giver(identity, map_number, xy, state):
            if state == 'completed':
                return
            tile, pal = (0, 4) if state == 'offered' else (1, 4 if state == 'ready' else 7)
            append('questgiver', identity, map_number, xy, tile, pal, state=state)

        def state(accepted, complete, ready):
            if self.flag(complete):
                return 'completed'
            if not self.flag(accepted):
                return 'offered'
            return 'ready' if all(self.flag(f) for f in ready) else 'active'

        familiars_active = self.flag('FAMILIARS_ACCEPTED') and not any(self.flag(f) for f in
                            ('FAMILIARS_DONE', 'MEDALLION_ACCEPTED', 'MEDALLION_DONE'))
        familiars_ready = all(self.flag(f) for f in ('CAVE_APPROACH_IMP_1_DEAD',
            'CAVE_APPROACH_IMP_2_DEAD', 'CAVE_STRONG_IMP_DEAD', 'CAVE_IMP_DEAD'))
        if region in ('DEN', 'VALLEY'):
            if self.flag('MAP_RECEIVED') and (not self.flag('GEAR_REWARDED') or (
                    self.flag('SARKOTH_DONE') and not self.flag('SARKOTH_REPORT_DONE'))):
                giver('GORNEK_REPORT', 14, (10, 9), 'ready')
            giver('LAZY_PEONS', 14, (8, 15), state('LAZY_ACCEPTED', 'LAZY_DONE', ('LAZY_AWAKE',)))
            if region == 'DEN' and self.flag('LAZY_ACCEPTED') and not self.flag('LAZY_DONE') and not self.flag('LAZY_AWAKE'):
                append('objective', 'LAZY', 14, (5, 16))
        if region == 'VALLEY':
            giver('CACTUS', 15, (8, 10), state('CACTUS_ACCEPTED', 'CACTUS_DONE',
                  ('CACTUS_1', 'CACTUS_2', 'CACTUS_3')))
            giver('SARKOTH', 26, (3, 4), state('SARKOTH_ACCEPTED', 'SARKOTH_DONE', ('SARKOTH_DEAD',)))
            if familiars_active:
                med_state = 'ready' if familiars_ready else 'active'
            elif self.flag('FAMILIARS_DONE') and not self.flag('MEDALLION_ACCEPTED') and not self.flag('MEDALLION_DONE'):
                med_state = 'offered'
            else:
                med_state = state('MEDALLION_ACCEPTED', 'MEDALLION_DONE', ('YARROG_DEAD',))
            giver('FAMILIARS_MEDALLION', 25, (6, 4), med_state)
            if self.flag('LAZY_ACCEPTED') and not self.flag('LAZY_DONE') and not self.flag('LAZY_AWAKE'):
                append('objective', 'LAZY', 14, (5, 16))
            if self.flag('CACTUS_ACCEPTED') and not self.flag('CACTUS_DONE'):
                for number, xy in ((1, (7, 7)), (2, (23, 9)), (3, (9, 17))):
                    if not self.flag('CACTUS_' + str(number)):
                        append('objective', 'CACTUS' + str(number), 15, xy)
            if self.flag('SARKOTH_ACCEPTED') and not self.flag('SARKOTH_DONE') and not self.flag('SARKOTH_DEAD'):
                append('objective', 'SARKOTH', 27, (4, 4))
            medallion_active = self.flag('MEDALLION_ACCEPTED') and not self.flag('MEDALLION_DONE') and not self.flag('YARROG_DEAD')
            if medallion_active or (familiars_active and not all(self.flag(f) for f in ('CAVE_STRONG_IMP_DEAD', 'CAVE_IMP_DEAD'))):
                append('objective', 'CAVE_ENTRANCE', 28, (5, 2))
            if familiars_active:
                for flag, xy in (('CAVE_APPROACH_IMP_1_DEAD', (4, 5)), ('CAVE_APPROACH_IMP_2_DEAD', (6, 4))):
                    if not self.flag(flag):
                        append('objective', flag, 28, xy)
        if region == 'CAVERN':
            if self.flag('MEDALLION_ACCEPTED') and not self.flag('MEDALLION_DONE') and not self.flag('YARROG_DEAD'):
                append('objective', 'YARROG', 20, (14, 3))
            if familiars_active:
                for flag, xy in (('CAVE_STRONG_IMP_DEAD', (12, 8)), ('CAVE_IMP_DEAD', (8, 10))):
                    if not self.flag(flag):
                        append('objective', flag, 20, xy)
        return entries, points

    def expected_background(self, region):
        fog = region != 'VALLEY' and not self.flag('DISCOVERED_' + region)
        filename = 'fog' if fog else region.lower()
        binary = bytearray((ROOT / 'gfx/peon_maps' / (filename + '.bin')).read_bytes())
        if region == 'VALLEY':
            overview = GEOMETRY['overview']
            for sector in SECTORS:
                if self.event(sector['discovery_flag']):
                    continue
                x, y, width, height = sector['fog_tile_rect']
                for yy in range(y, y + height):
                    for xx in range(x, x + width):
                        binary[5760 + yy * 20 + xx] = overview['fog']['tiles'][0]
                        binary[6120 + yy * 20 + xx] = 8 + overview['fog']['palette']
                binary[5760 + (y + height // 2) * 20 + x + width // 2] = overview['fog']['tiles'][1]
        return bytes(binary), fog

    def expected_bridge(self, original):
        result = list(original)
        def enabled(name):
            index = self.flags[name]
            return bool(original[index // 8] & (1 << (index % 8)))
        if not any(enabled(sector['discovery_flag']) for sector in SECTORS):
            for legacy, current in (('EVENT_PEON_DISCOVERED_DEN', 'EVENT_PEON_SECTOR_1'),
                                    ('EVENT_PEON_DISCOVERED_VALLEY', 'EVENT_PEON_SECTOR_2')):
                if enabled(legacy):
                    index = self.flags[current]
                    result[index // 8] |= 1 << (index % 8)
        return result

    def world_graphics(self):
        result = PreviousAtlas.restored_world(self)
        self.terrain_upload()
        # The two flame patterns change independently in their legal native
        # phases. All 190 other patterns must restore byte for byte.
        result['terrain'][0] = result['terrain'][0][32:]
        return result

    def fire_after_close(self):
        before = self.fire_calls
        seen = [set(), set()]
        for _ in range(128):
            self.p.tick(1, True)
            native = self.terrain_upload()
            for part, phases in enumerate(native['fire_left_right_matching_phases']):
                seen[part].update(phases)
        assert self.fire_calls > before + 10, 'Atlas left native terrain animation stalled'
        assert seen == [{0, 1, 2}, {0, 1, 2}], ('Atlas starved later fire phases', seen)
        return {'world_frames_observed': 128, 'native_fire_callback_calls': self.fire_calls - before,
                'both_native_tiles_show_all_three_phases': True,
                'other_190_patterns_preserved_every_frame': True}

    def check_atlas(self, label, records, region=None, diagnostic=False):
        self.p.tick(60, True)
        before = {'map': self.read('wMapGroup', 2), 'xy': self.position(),
                  'events': self.read('wEventFlags', 256),
                  'palettes': [self.read('wOBPals1', 64), self.read('wOBPals2', 64)]}
        world_before = self.world_graphics() if not diagnostic else None
        first = len(self.atlas_calls)
        self.press('select', 180)
        default = self.read('wMenuCursorY')[0]
        if region is None:
            region = next(name for name, page in GEOMETRY['pages'].items() if page['page'] == default)
        wanted = GEOMETRY['pages'][region]['page']
        for _ in range(7):
            current = self.read('wMenuCursorY')[0]
            if current == wanted:
                break
            self.press('right', 120)
        assert self.read('wMenuCursorY') == [wanted]
        self.p.tick(30, True)
        assert not self.observer_errors, self.observer_errors
        assert len(self.atlas_calls) > first and all(row.get('verified') for row in self.atlas_calls[first:])
        binary, fog = self.expected_background(region)
        assert bytes(self.p.memory[0, 0x9000:0x9800]) == binary[:2048]
        assert bytes(self.p.memory[0, 0x8800:0x9000]) == binary[2048:4096]
        assert bytes(self.p.memory[1, 0x9000:0x9680]) == binary[4096:5760]
        assert self.read('wTilemap', 360) == list(binary[5760:6120]), (label, 'Sector fog tile grid differs')
        assert self.read('wAttrmap', 360) == list(binary[6120:6480]), (label, 'Sector fog attributes differ')
        hardware = list(self.p.memory[0xfe00:0xfea0])
        assert hardware == self.read('wShadowOAM', 160)
        visible = [hardware[i:i + 4] for i in range(0, 160, 4)
                   if 0 < hardware[i] < 160 and 0 < hardware[i + 1] < 168]
        expected, descriptions = self.expected_points(region)
        assert visible == expected, (label, 'Actual hardware OAM differs', visible, expected, descriptions)
        assert len(visible) <= 16
        counts = [sum(sprite[0] - 16 <= y < sprite[0] - 8 for sprite in visible) for y in range(144)]
        assert max(counts, default=0) <= 10
        pixels = background(binary)
        if not fog:
            assert bytes(self.p.memory[0, 0x8000:0x8030]) == GLYPHS
            assert self.p.memory[0xff40] & 2 and not self.p.memory[0xff40] & 4
            actual_pal = palette(self.read('wOBPals1', 64)).reshape(8, 4, 3)
            assert actual_pal[4].tolist() == STYLES['gold_palette_rgb555']
            assert actual_pal[7].tolist() == STYLES['gray_palette_rgb555']
            assert actual_pal[6].tolist() == GEOMETRY['avatar']['rgb555']
            for y, x, tile, attr in reversed(expected):
                top, left = y - 16, x - 8
                assert 0 <= top <= 136 and 0 <= left <= 152
                glyph = decode_tile(GLYPHS[tile * 16:(tile + 1) * 16])
                opaque = glyph != 0
                pixels[top:top + 8, left:left + 8][opaque] = actual_pal[attr & 7][glyph][opaque]
        actual = np.asarray(self.p.screen.image.convert('RGB')) >> 3
        assert np.array_equal(actual, pixels), (label, 'RGB555 screen differs',
                int(np.any(actual != pixels, axis=-1).sum()))
        # While the atlas is idle, VBlank must not upload flame patterns into
        # its reused native BG storage or overwrite the submitted atlas OAM.
        for _ in range(32):
            self.p.tick(1, True)
            assert bytes(self.p.memory[0, 0x9000:0x9800]) == binary[:2048]
            assert bytes(self.p.memory[0, 0x8800:0x9000]) == binary[2048:4096]
            assert list(self.p.memory[0xfe00:0xfea0]) == hardware
        self.capture(label)
        self.press('b', 180); self.p.tick(60, True)
        assert self.read('wMapGroup', 2) == before['map'] and self.position() == before['xy']
        assert self.read('wScriptMode') == [0]
        expected_events = self.expected_bridge(before['events']) if region == 'VALLEY' else before['events']
        assert self.read('wEventFlags', 256) == expected_events, (label, 'Unexpected saved flag mutation')
        assert [self.read('wOBPals1', 64), self.read('wOBPals2', 64)] == before['palettes']
        fire = None
        if world_before is not None:
            world_after = self.world_graphics()
            assert world_before == world_after, ('World graphics failed to restore', label,
                    [field for field in world_before if world_before[field] != world_after[field]])
            font = (ROOT / 'gfx/font/peon_readable.1bpp').read_bytes()
            expected_font = bytes(value for byte in font for value in (byte, byte))
            assert bytes(self.p.memory[0, 0x8800:0x9000]) == expected_font
            assert bytes(self.p.memory[0, 0x97f0:0x9800]) == bytes(16)
            assert bytes(self.p.memory[0, 0x8600:0x86e0]) == (ROOT / 'gfx/pack/peon_player_hud.2bpp').read_bytes()
            fire = self.fire_after_close()
        row = {'name': label, 'diagnostic_ram_or_emulator_state': diagnostic,
            'region': region, 'initial_page': default, 'current_map': before['map'],
            'current_xy': list(before['xy']), 'whole_region_fog': fog,
            'sector_discovery': {str(sector['zone']): self.event(sector['discovery_flag']) for sector in SECTORS},
            'hardware_oam': visible, 'points': descriptions,
            'native_rgb555_pixels_exact': True, 'cpu_banks_lcd_scroll_events_preserved': True,
            'tilemap_attributes_and_background_patterns_exact': True,
            'atlas_not_overwritten_during_32_idle_vblanks': True,
            'world_palette_location_restored': True,
            'native_font_hud_actor_graphics_190_static_tiles_restored': world_before is not None,
            'legacy_sector_bridge_applied': expected_events != before['events'],
            'max_obj_tiles_per_scanline': max(counts, default=0),
            'fire_after_close': fire}
        records.append(row)
        return row

    def set_flag(self, name, value=True):
        index = self.flags[name]
        bank, address = self.sym['wEventFlags']; address += index // 8
        old = self.p.memory[bank, address]
        self.p.memory[bank, address] = old | (1 << (index % 8)) if value else old & ~(1 << (index % 8))

    def write(self, name, values):
        bank, address = self.sym[name]
        if address >= 0xe000:
            self.p.memory[address:address + len(values)] = values
        else:
            self.p.memory[bank, address:address + len(values)] = values


def ordinary_routes(s, report):
    normal = report['normal_route']
    s.fresh()
    assert not s.event('EVENT_PEON_MAP_RECEIVED')
    calls = len(s.atlas_calls)
    s.press('select', 180); s.capture('normal_map_locked_before_reward')
    s.press('a', 120); s.press('b', 120)
    assert len(s.atlas_calls) == calls
    s.talk((10, 10), 'up', 'normal_gornek_cutting_teeth_accept')
    s.navigate((18, 13)); s.press('up', 30); s.press('a', 120)
    report['ordinary_battles'].append(s.fight('normal_boar', 'EVENT_PEON_QUEST_DONE'))
    s.talk((10, 10), 'up', 'normal_gornek_scorpid_quest'); s.rest()
    s.navigate((17, 15))
    report['ordinary_battles'].append(s.fight('normal_scorpid', 'EVENT_PEON_SCORPID_DEFEATED'))
    s.talk((10, 10), 'up', 'normal_gornek_earned_map'); s.rest()
    assert s.event('EVENT_PEON_MAP_RECEIVED')
    report['map_earned_after_actual_second_quest'] = True
    row = s.check_atlas('normal_earned_overview_only_den_revealed', normal)
    assert row['initial_page'] == 1 and sum(row['sector_discovery'].values()) == 1
    s.check_atlas('normal_den_zoom_page_still_available', normal, 'DEN')
    s.check_atlas('normal_unknown_road_page_fog', normal, 'ROAD')
    s.navigate((12, 9)); row = s.check_atlas('normal_den_player_walked', normal)
    assert row['hardware_oam'][0] == [*project('VALLEY', 14, s.position()), 2, 6]

    s.talk_actor('TheDenForemanScript', 'normal_lazy_quest_accepted')
    row = s.check_atlas('normal_lazy_gray_giver_and_sleeping_objective', normal)
    assert any(point['identity'] == 'LAZY' for point in row['points'])
    s.talk((5, 17), 'up', 'normal_sleeping_peon_woken')
    row = s.check_atlas('normal_lazy_objective_removed_ready_giver', normal)
    assert not any(point['identity'] == 'LAZY' for point in row['points'])
    assert any(point['identity'] == 'LAZY_PEONS' and point['state'] == 'ready' for point in row['points'])
    s.talk_actor('TheDenForemanScript', 'normal_lazy_quest_reward')
    s.check_atlas('normal_lazy_giver_removed_after_turn_in', normal)

    def doors(owner):
        s.travel(owner)
        for index, door in enumerate([door for door in GEOMETRY['doors'] if door['map'] == owner]):
            s.navigate(tuple(door['xy']), expected_map=door['room'])
            row = s.check_atlas(f'normal_owner_{owner}_door_{index + 1}_interior_projection', normal)
            region = row['region']
            assert row['hardware_oam'][0] == [*project(region, owner, door['xy']), 2, 6]
            s.walk('up')
            moved = s.check_atlas(f'normal_owner_{owner}_door_{index + 1}_indoor_walk_same_projection', normal)
            assert moved['hardware_oam'][0] == row['hardware_oam'][0]
            s.navigate((5, 7), expected_map=owner)
            assert s.position() == tuple(door['xy'])
            report['room_door_projections'].append({'owner': owner, 'room': door['room'],
                'warp': door['warp'], 'xy': door['xy'], 'native_exact_return': True})

    doors(14)
    s.travel(15)
    row = s.check_atlas('normal_zone_2_revealed_by_rightward_travel', normal)
    assert row['initial_page'] == 1 and s.flag('SECTOR_2')
    s.talk_actor('ValleyOfTrialsGuideScript', 'normal_galgar_cactus_quest_accept')
    row = s.check_atlas('normal_three_real_cactus_targets', normal)
    assert sum(point['type'] == 'objective' and point['identity'].startswith('CACTUS') for point in row['points']) == 3
    for position, face, number in (((8, 7), 'left', 1), ((24, 9), 'left', 2), ((10, 17), 'left', 3)):
        s.talk(position, face, f'normal_cactus_{number}_picked')
        assert s.flag('CACTUS_' + str(number))
        row = s.check_atlas(f'normal_cactus_{number}_map_target_removed', normal)
        assert sum(point['type'] == 'objective' and point['identity'].startswith('CACTUS') for point in row['points']) == 3 - number
    s.talk_actor('ValleyOfTrialsGuideScript', 'normal_galgar_reward')
    s.check_atlas('normal_cactus_completed_marker_removed', normal)
    s.travel(25)
    s.check_atlas('normal_zone_3_revealed_by_northward_travel', normal)
    s.talk_actor('PeonCrossroadsZureethaScript', 'normal_moved_zureetha_familiars_accepted')
    assert s.flag('FAMILIARS_ACCEPTED')
    row = s.check_atlas('normal_familiar_targets_hidden_before_zone_6_discovery', normal)
    assert not any(point['identity'] in ('CAVE_ENTRANCE', 'CAVE_APPROACH_IMP_1_DEAD', 'CAVE_APPROACH_IMP_2_DEAD') for point in row['points'])
    s.travel(26)
    s.talk_actor('PeonCampHanazuaScript', 'normal_moved_hanazua_sarkoth_accepted')
    row = s.check_atlas('normal_zone_4_gray_hanazua_and_hidden_sarkoth_basin', normal)
    assert not any(point['type'] == 'objective' and point['identity'] == 'SARKOTH' for point in row['points'])
    s.travel(27)
    row = s.check_atlas('normal_zone_5_revealed_sarkoth_target', normal)
    assert any(point['type'] == 'objective' and point['identity'] == 'SARKOTH' for point in row['points'])
    s.navigate((5, 4))
    result = s.fight('normal_sarkoth_zone_5', 'EVENT_PEON_SARKOTH_DEAD', 35)
    assert result['outcome'] == 0
    report['ordinary_battles'].append(result)
    s.check_atlas('normal_sarkoth_dead_target_removed_ready_hanazua', normal)
    s.rest()
    s.travel(26)
    s.talk_actor('PeonCampHanazuaScript', 'normal_hanazua_sarkoth_reward')
    assert s.flag('SARKOTH_DONE')
    row = s.check_atlas('normal_gornek_report_yellow_question_at_actual_den', normal)
    assert any(point['identity'] == 'GORNEK_REPORT' for point in row['points'])
    s.travel(14); s.talk((10, 10), 'up', 'normal_gornek_sarkoth_report_reward')
    row = s.check_atlas('normal_gornek_report_marker_removed_after_turn_in', normal)
    assert not any(point['identity'] == 'GORNEK_REPORT' for point in row['points'])
    s.travel(28)
    row = s.check_atlas('normal_zone_6_two_familiar_targets_and_cave_revealed', normal)
    assert {'CAVE_ENTRANCE', 'CAVE_APPROACH_IMP_1_DEAD', 'CAVE_APPROACH_IMP_2_DEAD'} <= {point['identity'] for point in row['points']}
    for position, flag, number in (((4, 6), 'CAVE_APPROACH_IMP_1_DEAD', 1), ((5, 4), 'CAVE_APPROACH_IMP_2_DEAD', 2)):
        s.navigate(position)
        report['ordinary_battles'].append(s.fight(f'normal_zone_6_guard_{number}', 'EVENT_PEON_' + flag, 30))
        row = s.check_atlas(f'normal_defeated_guard_{number}_map_target_removed', normal)
        assert not any(point['identity'] == flag for point in row['points'])
        s.rest(); s.travel(28)
    s.navigate((5, 2), expected_map=20)
    row = s.check_atlas('normal_cave_player_projection_and_two_inside_familiars', normal)
    assert row['region'] == 'CAVERN'
    assert {'CAVE_STRONG_IMP_DEAD', 'CAVE_IMP_DEAD'} <= {point['identity'] for point in row['points']}
    s.navigate((10, 15)); s.check_atlas('normal_cave_actual_player_walked', normal)
    s.navigate((10, 16), expected_map=28)
    s.check_atlas('normal_cave_return_to_real_zone_6_overview', normal)
    s.travel(29)
    row = s.check_atlas('normal_zone_7_all_seven_sectors_discovered', normal)
    assert all(row['sector_discovery'].values())
    s.travel(16); s.check_atlas('normal_road_actual_player_regional_page', normal)
    s.travel(17); s.check_atlas('normal_senjin_actual_player_regional_page', normal); doors(17)
    s.travel(18); s.check_atlas('normal_razor_actual_player_regional_page', normal); doors(18)
    s.travel(19); s.check_atlas('normal_orgrimmar_actual_player_regional_page', normal)
    assert len(report['room_door_projections']) == 9
    s.travel(14)
    return s.snapshot()


def diagnostic_routes(s, report):
    records = report['diagnostic_cases']
    state = io.BytesIO(); s.p.save_state(state); state = state.getvalue()
    def rewind():
        s.p.load_state(io.BytesIO(state))
        for button in ('a', 'b', 'up', 'down', 'left', 'right', 'start', 'select'):
            s.p.button_release(button)
    for sector in SECTORS:
        rewind()
        s.set_flag(sector['discovery_flag'], False)
        s.check_atlas(f"diagnostic_sector_{sector['zone']}_fog_hides_points", records, 'VALLEY', diagnostic=True)
    rewind()
    for sector in SECTORS:
        s.set_flag(sector['discovery_flag'], False)
    s.set_flag('EVENT_PEON_DISCOVERED_DEN', False)
    s.set_flag('EVENT_PEON_DISCOVERED_VALLEY', False)
    row = s.check_atlas('diagnostic_all_seven_sectors_hidden_no_false_player', records, 'VALLEY', diagnostic=True)
    assert not row['hardware_oam']
    rewind()
    for sector in SECTORS:
        s.set_flag(sector['discovery_flag'], False)
    row = s.check_atlas('diagnostic_legacy_save_bridge_only_den_and_valley', records, 'VALLEY', diagnostic=True)
    assert row['sector_discovery'] == {'1': True, '2': True, '3': False, '4': False, '5': False, '6': False, '7': False}
    assert row['legacy_sector_bridge_applied']
    s.check_atlas('diagnostic_legacy_bridge_second_open_idempotent', records, 'VALLEY', diagnostic=True)

    rewind()
    # All objectives and independent questgiver states, including the maximum
    # practical overview OAM case, are native branches with declared fixtures.
    for name in ('LAZY_DONE', 'LAZY_AWAKE', 'CACTUS_DONE', 'CACTUS_1', 'CACTUS_2', 'CACTUS_3',
                 'SARKOTH_DONE', 'SARKOTH_DEAD', 'SARKOTH_REPORT_DONE', 'MEDALLION_ACCEPTED', 'MEDALLION_DONE',
                 'FAMILIARS_DONE', 'CAVE_APPROACH_IMP_1_DEAD', 'CAVE_APPROACH_IMP_2_DEAD',
                 'CAVE_STRONG_IMP_DEAD', 'CAVE_IMP_DEAD'):
        s.set_flag('EVENT_PEON_' + name, False)
    for name in ('LAZY_ACCEPTED', 'CACTUS_ACCEPTED', 'SARKOTH_ACCEPTED', 'FAMILIARS_ACCEPTED'):
        s.set_flag('EVENT_PEON_' + name)
    s.set_flag('EVENT_PEON_GEAR_REWARDED', False)
    row = s.check_atlas('diagnostic_fourteen_visible_markers_native_scanline_budget', records, 'VALLEY', diagnostic=True)
    assert len(row['hardware_oam']) == 14
    for name in ('CAVE_APPROACH_IMP_1_DEAD', 'CAVE_APPROACH_IMP_2_DEAD', 'CAVE_STRONG_IMP_DEAD', 'CAVE_IMP_DEAD'):
        s.set_flag('EVENT_PEON_' + name)
    row = s.check_atlas('diagnostic_familiars_ready_yellow_question', records, 'VALLEY', diagnostic=True)
    assert any(point['identity'] == 'FAMILIARS_MEDALLION' and point['state'] == 'ready' for point in row['points'])
    s.set_flag('EVENT_PEON_FAMILIARS_DONE')
    row = s.check_atlas('diagnostic_next_medallion_offer_after_familiars', records, 'VALLEY', diagnostic=True)
    assert any(point['identity'] == 'FAMILIARS_MEDALLION' and point['state'] == 'offered' for point in row['points'])
    s.set_flag('EVENT_PEON_MEDALLION_ACCEPTED')
    s.set_flag('EVENT_PEON_YARROG_DEAD', False)
    s.check_atlas('diagnostic_legacy_medallion_active_entrance_objective', records, 'VALLEY', diagnostic=True)
    s.set_flag('EVENT_PEON_YARROG_DEAD')
    s.check_atlas('diagnostic_medallion_ready_marker', records, 'VALLEY', diagnostic=True)
    s.set_flag('EVENT_PEON_MEDALLION_DONE')
    s.check_atlas('diagnostic_medallion_giver_removed', records, 'VALLEY', diagnostic=True)
    rewind()
    s.write('wXCoord', [255]); s.write('wYCoord', [255])
    row = s.check_atlas('diagnostic_out_of_bounds_player_not_drawn', records, 'VALLEY', diagnostic=True)
    assert not any(point['type'] == 'player' for point in row['points'])
    rewind()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-sha', required=True)
    args = parser.parse_args()
    digest = hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest()
    assert digest == args.expected_sha
    OUT.mkdir(parents=True, exist_ok=True)
    logging.disable(logging.CRITICAL)
    load_geometry(); environment.configure_zone_layout()
    report = {'rom_sha256': digest, 'all_checks_passed': False,
              'normal_method': 'Ordinary buttons only, real quests, movement, combat and door warps; no normal RAM edits or emulator states loaded.',
              'diagnostic_method': 'Explicit temporary event/coordinate fixtures and private emulator states, with unchanged native execution.',
              'user_battery_saves_opened': False, 'normal_route': [], 'diagnostic_cases': [],
              'ordinary_battles': [], 'room_door_projections': []}
    s = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-seven-sector-atlas-') as temporary:
            rom = Path(temporary) / 'game.gbc'; shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = AtlasSession(rom, symbols_from(ROOT / 'pokecrystal.sym'))
            report['ordinary_route_saved_fields'] = ordinary_routes(s, report)
            diagnostic_routes(s, report)
            assert not s.observer_errors, s.observer_errors
            report['native_overlay_return_checks'] = len(s.atlas_calls)
            report['no_animation_starvation_after_any_normal_atlas_close'] = True
            assert hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest() == digest
            report['all_checks_passed'] = True
    except Exception as error:
        report['failure'] = repr(error)
        if s is not None:
            s.capture('unexpected_atlas_state')
        raise
    finally:
        if s is not None:
            s.p.stop(save=False)
        (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS seven-sector native atlas', digest, flush=True)


if __name__ == '__main__':
    main()
