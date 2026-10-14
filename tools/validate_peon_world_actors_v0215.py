#!/usr/bin/env python3
"""Ordinary-control validation of streamed world actors and native OAM limits.

Only private fresh ROM copies are used. Controller buttons change game state;
hooks and memory observations are read-only. No user battery or state is read.
"""
from pathlib import Path
import argparse
import hashlib
import json
import logging
import shutil
import tempfile

from PIL import Image

from validate_peon_earth_stone_v0212 import EarthSession, CLASSES
from validate_peon_exit_title import symbols

ROOT = Path(__file__).resolve().parents[1]


class WorldActorSession(EarthSession):
    def __init__(self, *args):
        self.world_loops = 0
        self.renderer_frames = []
        self.renderer_start = None
        self.base_intro = None
        self.body_checks = 0
        self.histogram_checks = 0
        super().__init__(*args)

    def open(self):
        super().open()
        self.p.hook_register(*self.sym['PeonInitLargeWorldSpritesV0215.active'],
                             self.renderer_enter, None)
        self.p.hook_register(*self.sym['_UpdateSprites.fill'], self.renderer_finish, None)
        # Existing presentation hook owns HandleMapTimeAndJoypad. A distinct
        # nearby native routine supplies the world-loop cadence observation.
        self.p.hook_register(*self.sym['HandleMapObjects'],
                             lambda _: setattr(self, 'world_loops', self.world_loops + 1), None)

    def renderer_enter(self, _):
        self.renderer_start = (self.read('hVBlankCounter')[0], self.read('hObjectStructIndex')[0])

    def renderer_finish(self, _):
        if self.renderer_start is None:
            return
        frame, original_index = self.renderer_start
        assert self.read('hObjectStructIndex') == [original_index], 'Renderer changed native current-object context'
        used = self.read('hUsedSpriteIndex')[0]
        assert used <= 160 and not used % 4
        shadow = self.read('wShadowOAM', used)
        world_cells = [tuple(shadow[i:i + 4]) for i in range(0, used, 4)
                       if not (not shadow[i + 3] & 8 and 0x60 <= shadow[i + 2] <= 0x76)]
        expected = [sum(y <= row + 16 < y + 8 for y, x, tile, flags in world_cells)
                    for row in range(144)]
        assert self.read('wPeonLargeWorldScanlinesV0215', 144) == expected, (
            'Committed world histogram differs from whole published bodies', used, world_cells)
        assert max(expected, default=0) <= 10
        self.histogram_checks += 1
        self.renderer_frames.append((self.read('hVBlankCounter')[0] - frame) & 255)
        self.renderer_start = None

    def capture(self, label):
        self.p.screen.image.save(self.folder / (label + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(
            self.folder / (label + '_4x.png'))
        print(CLASSES[self.class_index], label, self.map(), self.position(), flush=True)

    def rom_range(self, bank, address, length):
        offset = address if bank == 0 else bank * 0x4000 + address - 0x4000
        return self.rom_bytes[offset:offset + length]

    def descriptor(self, key):
        if key >= 0xe0:
            bank, address = self.sym['PeonLargeWorldHeroBindingsV0215']
            return self.rom_range(bank, address + (key - 0xe0) * 8, 8)
        bank, address = self.sym['PeonLargeWorldBindingsV0215']
        for offset in range(0, 256, 8):
            record = self.rom_range(bank, address + offset, 8)
            if record[0] == 255:
                break
            if record[0] == key:
                return record
        raise AssertionError(('Unbound visible cache key', key))

    def palette_rgb(self, palette, color):
        raw = bytes(self.read('wOBPals2', 64))
        rgb = int.from_bytes(raw[palette * 8 + color * 2:palette * 8 + color * 2 + 2], 'little')
        return tuple((rgb >> shift & 31) * 8 for shift in (0, 5, 10))

    @staticmethod
    def tile_indices(data):
        return [[((data[y * 2] >> (7 - x)) & 1) | (((data[y * 2 + 1] >> (7 - x)) & 1) << 1)
                 for x in range(8)] for y in range(8)]

    def scene(self, label=None, strict_lcd=False):
        raw = list(self.p.memory[0xfe00:0xfea0])
        oam = [tuple(raw[i:i + 4]) for i in range(0, 160, 4)
               if 8 < raw[i] < 160 and 0 < raw[i + 1] < 168]
        occupancy = [sum(y <= row + 16 < y + 8 for y, x, tile, flags in oam)
                     for row in range(144)]
        assert len(oam) <= 40 and max(occupancy, default=0) <= 10
        cache_keys = self.read('wPeonLargeWorldCacheIDsV0215', 13)
        cache_frames = self.read('wPeonLargeWorldCacheFramesV0215', 13)
        groups = {}
        for cell in oam:
            y, x, tile, flags = cell
            if flags & 8 and tile < 117:
                groups.setdefault(tile // 9, []).append(cell)
        assert 0 in groups, ('Hero disappeared', self.map(), self.position(), oam)
        reports = {}
        lcd = self.p.screen.image.convert('RGB')
        for index, cells in groups.items():
            key, frame = cache_keys[index], cache_frames[index]
            assert key != 255 and frame < 12
            desc = self.descriptor(key)
            frame_address = int.from_bytes(desc[3:5], 'little') + frame * 144
            source = self.rom_range(desc[2], frame_address, 144)
            actual = bytes(self.p.memory[1, 0x8000 + index * 144:0x8000 + (index + 1) * 144])
            assert actual == source, ('Atomic nine-tile source mismatch', index, key, frame)
            mask_address = int.from_bytes(desc[6:8], 'little')
            mask = int.from_bytes(self.rom_range(desc[5], mask_address + frame * 2, 2), 'little')
            attrs = self.rom_range(desc[5], mask_address + 24 + frame * 9, 9)
            relative_verified = False
            if 'wPeonLargeRelativeOAMV0215' in self.sym:
                assert self.read('wPeonLargeMetadataIDsV0215', 13)[index] == key
                assert self.read('wPeonLargeMetadataFramesV0215', 13)[index] == frame
                raw_masks = bytes(self.read('wPeonLargeMetadataMasksV0215', 26))
                assert int.from_bytes(raw_masks[index * 2:index * 2 + 2], 'little') == mask
                entries = [bytes(((tile // 3 * 8 - 8) & 255, (tile % 3 * 8 - 4) & 255,
                                  tile, attrs[tile] | (0x80 if tile >= 6 else 0)))
                           for tile in range(9) if mask & 1 << tile]
                count = self.read('wPeonLargeRelativeCountsV0215', 13)[index]
                assert count == len(entries)
                templates = bytes(self.read('wPeonLargeRelativeOAMV0215', 13 * 36))
                assert templates[index * 36:index * 36 + count * 4] == b''.join(entries), (
                    'Relative OAM cache differs from canonical source', index, key, frame)
                relative_verified = True
            bases = {(y - ((tile % 9) // 3 * 8 - 8), x - ((tile % 9) % 3 * 8 - 4))
                     for y, x, tile, flags in cells}
            assert len(bases) == 1, ('Actor OAM pieces split between origins', index, cells, bases)
            origin_y, origin_x = next(iter(bases))
            expected = {(origin_y + tile // 3 * 8 - 8,
                         origin_x + tile % 3 * 8 - 4, index * 9 + tile)
                        for tile in range(9) if mask & 1 << tile
                        and 8 < origin_y + tile // 3 * 8 - 8 < 160
                        and 0 < origin_x + tile % 3 * 8 - 4 < 168}
            assert {(y, x, tile) for y, x, tile, flags in cells} == expected, (
                'A visible actor was partially admitted', index, cells, expected)
            assert all(flags & 7 == attrs[tile % 9] and not flags & 0x60
                       for y, x, tile, flags in cells), ('Wrong palette/mirror', index, cells, attrs)
            checked = 0
            if strict_lcd:
                # Only assert unobscured source pixels: native BG priority and
                # previously admitted OBJ legitimately cover parts of actors.
                for y, x, tile, flags in cells:
                    indices = self.tile_indices(source[tile % 9 * 16:tile % 9 * 16 + 16])
                    for py in range(8):
                        for px in range(8):
                            color = indices[py][px]
                            sx, sy = x - 8 + px, y - 16 + py
                            if not color or not (0 <= sx < 160 and 0 <= sy < 144):
                                continue
                            # Avoid an intentionally higher-priority OAM cell.
                            pos = oam.index((y, x, tile, flags))
                            covered = False
                            for oy, ox, ot, of in oam[:pos]:
                                if ox - 8 <= sx < ox and oy - 16 <= sy < oy - 8:
                                    bank = 1 if of & 8 else 0
                                    pixels = self.tile_indices(bytes(self.p.memory[bank, 0x8000 + ot * 16:0x8000 + (ot + 1) * 16]))
                                    ux, uy = sx - ox + 8, sy - oy + 16
                                    if of & 0x20: ux = 7 - ux
                                    if of & 0x40: uy = 7 - uy
                                    if pixels[uy][ux]:
                                        covered = True
                                        break
                            if covered:
                                continue
                            # In these deliberately open path views there is
                            # no foreground wall. Strict probes are the hero.
                            if index != 0:
                                continue
                            assert lcd.getpixel((sx, sy)) == self.palette_rgb(flags & 7, color), (
                                'Actual LCD source pixel mismatch', index, frame, sx, sy,
                                lcd.getpixel((sx, sy)), self.palette_rgb(flags & 7, color))
                            checked += 1
            reports[str(index)] = {'key': key, 'frame': frame, 'complete_visible_tiles': len(cells),
                                   'source_VRAM_exact': True, 'source_palette_attrs_exact': True,
                                   'relative_OAM_template_source_exact': relative_verified,
                                   'actual_LCD_source_pixels': checked}
        self.body_checks += 1
        if label:
            self.capture(label)
        return {'objects': len(oam), 'maximum_scanline': max(occupancy, default=0), 'actors': reports}

    def fresh_class(self):
        # Preserve the existing native startup and collect the actual base
        # Peon during its forced LEFT-facing opening before class selection.
        self.p.tick(240, True)
        self.press('start'); self.press('down'); self.press('a')
        chosen = False
        for _ in range(200):
            if self.map() == 12 and self.base_intro is None:
                self.p.tick(60, True)
                try:
                    observed = self.scene('base_peon_actual_opening')
                    if observed['actors']['0']['key'] == 0xe0:
                        self.base_intro = observed
                except AssertionError:
                    pass  # The opening deliberately hides the hero at first.
            if self.map() == 14 and self.read('wScriptMode') == [0]:
                break
            if self.class_ready and not chosen:
                self.p.tick(60, True)
                for desired in range(1, self.class_index + 1):
                    self.p.button_press('down')
                    for _ in range(180):
                        self.p.tick(1, True)
                        if self.read('wMenuCursorY') == [desired]:
                            break
                    self.p.button_release('down')
                    self.p.tick(24, True)
                    assert self.read('wMenuCursorY') == [desired]
                assert self.read('wMenuCursorY') == [self.class_index]
                self.press('a', 90)
                chosen = True
            if self.naming and not self.naming_done:
                self.p.tick(120, True)
                for index in range(5):
                    self.press('a', 35)
                    if index < 4: self.press('right', 35)
                self.press('start', 40); self.press('a')
                self.naming_done = True
            self.press('a')
        assert chosen and self.naming_done and self.map() == 14 and self.read('wScriptMode') == [0], {
            'pc': hex(self.p.register_file.PC), 'sp': hex(self.p.register_file.SP),
            'rom': self.read('hROMBank'), 'wram': self.p.memory[0xff70],
            'presentation': self.presentation, 'phase': self.phase, 'chosen': chosen,
            'class_ready': self.class_ready, 'naming': self.naming,
            'input': self.read('wInputType'), 'map_event': self.read('wMapEventStatus'),
            'script': self.read('wScriptMode'), 'world_loops': self.world_loops,
            'sprite_context': self.read('hObjectStructIndex'),
            'renderer_frames': self.renderer_frames[-10:],
            'dma': self.read('hDMATransfer'), 'OAM_update': self.read('hOAMUpdate'),
        }

        assert self.event('EVENT_PEON_WARRIOR') == (self.class_index == 1)
        assert self.event('EVENT_PEON_WARLOCK') == (self.class_index == 2)

    def talk_at(self, point, facing, label, close=True):
        self.navigate(point)
        before = self.position()
        wanted = ('down', 'up', 'left', 'right').index(facing)
        self.p.button_press(facing)
        for _ in range(180):
            self.p.tick(1, True)
            if self.read('wObjectStructs', 40)[13] // 4 == wanted:
                break
        self.p.button_release(facing)
        self.p.tick(30, True)
        assert self.position() == before, (label, 'Moved into speaker')
        self.p.button_press('a')
        for _ in range(240):
            self.p.tick(1, True)
            if self.read('wScriptMode')[0]:
                break
        self.p.button_release('a')
        assert self.read('wScriptMode')[0], (label, 'No native dialogue')
        self.p.tick(120, True)
        self.capture(label)
        if close:
            self.close_dialogue()
            self.p.tick(120, True)

    def navigate(self, target, expected_map=None):
        if expected_map is not None:
            return super().navigate(target, expected_map)
        target = tuple(target)
        origin_map = self.map()
        for _ in range(240):
            if self.map() == origin_map and self.position() == target:
                self.p.tick(90, True)
                return
            route = self.path(target)
            assert route, ('Empty ordinary route', target)
            before = self.position()
            self.p.button_press(route[0])
            for _ in range(180):
                self.p.tick(1, True)
                if self.position() != before or self.map() != origin_map:
                    break
            self.p.button_release(route[0])
            self.p.tick(90, True)
            assert self.map() == origin_map, ('Unexpected ordinary warp', target)
            assert self.position() != before, ('Held movement did not complete', before, route[0])
        raise AssertionError(('Ordinary navigation budget', target, self.position()))

    def direction_checks(self):
        result = {}
        self.navigate((10, 12))
        for direction, expected in (('down', 0), ('up', 1), ('left', 2), ('right', 3)):
            self.p.button_press(direction)
            acknowledged = None
            for elapsed in range(180):
                self.p.tick(1, True)
                native_facing = self.read('wObjectStructs', 40)[13]
                if native_facing // 4 == expected:
                    acknowledged = elapsed + 1
                    break
            self.p.button_release(direction)
            assert acknowledged is not None, ('Native direction did not acknowledge held control', direction)
            self.p.tick(90, True)
            scene = self.scene('world_hero_' + direction, strict_lcd=True)
            assert scene['actors']['0']['frame'] // 3 == expected, (direction, scene)
            result[direction] = scene | {'direction_acknowledged_in_LCD_frames': acknowledged}
        # Ordinary held walking on the clear Den path samples actual gait.
        frames, renderer_before, loops_before = [], len(self.renderer_frames), self.world_loops
        self.p.button_press('left')
        for _ in range(90):
            self.p.tick(1, True)
            if self.read('hOAMUpdate') == [0]:
                frames.append(self.read('wPeonLargeWorldCacheFramesV0215')[0])
        self.p.button_release('left')
        self.p.tick(60, True)
        self.scene('world_hero_walk_completed', strict_lcd=True)
        assert {frame % 3 for frame in frames} >= {0, 1, 2}, ('Authored gait poses were not rendered', frames)
        durations = self.renderer_frames[renderer_before:]
        result['walking'] = {'observed_native_frames': sorted(set(frames)),
                             'all_three_authored_gait_poses': True,
                             'renderer_VBlank_intervals': durations,
                             'native_world_loops_during_150_LCD_frames': self.world_loops - loops_before}
        return result

    def gornek_marker(self, label):
        records = self.read('wObjectStructs', 13 * 40)
        marker = next(records[i:i + 40] for i in range(40, 13 * 40, 40)
                      if records[i] == 0xfd and records[i + 1] == 2)
        assert tuple(marker[16:18]) == (14, 12), 'Marker event coordinates changed'
        resolved = self.read('wVariableSprites', 16)[0xfd - 0xf0]
        source_label = {0x35: 'PeonQuestAvailableYellowGFX',
                        0x36: 'PeonQuestActiveGrayGFX',
                        0x3c: 'PeonQuestCompleteYellowGFX'}[resolved]
        tile = marker[2] & 0x7f
        assert marker[2] & 0x80, 'Marker overlaps streamed bank1 pool'
        source = self.rom_range(*self.sym[source_label], 64)
        assert bytes(self.p.memory[0, 0x8000 + tile * 16:0x8000 + (tile + 4) * 16]) == source
        origin_x = (marker[23] + marker[25] + 8 + self.read('wPlayerBGMapOffsetX')[0]) & 255
        origin_y = (marker[24] + marker[26] + 12 + self.read('wPlayerBGMapOffsetY')[0] - 8) & 255
        raw = list(self.p.memory[0xfe00:0xfea0])
        oam = [tuple(raw[i:i + 4]) for i in range(0, 160, 4)]
        expected = {(origin_y + i // 2 * 8, origin_x + i % 2 * 8, tile + i)
                    for i in range(4)}
        cells = [cell for cell in oam if cell[:3] in expected and not cell[3] & 8]
        assert {cell[:3] for cell in cells} == expected, ('Quest glyph partially missing', cells, expected)
        assert all(flags & 7 == marker[6] & 7 for y, x, t, flags in cells)
        checked = 0
        lcd = self.p.screen.image.convert('RGB')
        for y, x, t, flags in cells:
            for py, row in enumerate(self.tile_indices(source[(t - tile) * 16:(t - tile + 1) * 16])):
                for px, color in enumerate(row):
                    sx, sy = x - 8 + px, y - 16 + py
                    if color and 0 <= sx < 160 and 0 <= sy < 144:
                        assert lcd.getpixel((sx, sy)) == self.palette_rgb(flags & 7, color), (
                            'Actual LCD marker pixel mismatch', sx, sy)
                        checked += 1
        assert checked > 0
        self.capture(label)
        return {'source': source_label, 'source_VRAM_exact': True,
                'native_event_coordinates': [10, 8], 'visual_Y_shift_pixels': -8,
                'complete_visible_tiles': len(cells), 'actual_LCD_source_pixels': checked}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--sym', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-rom-sha256')
    parser.add_argument('--classes', default='shaman,warrior,warlock')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    digest = hashlib.sha256(args.rom.read_bytes()).hexdigest()
    if args.expected_rom_sha256:
        assert digest == args.expected_rom_sha256
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'rom_sha256': digest, 'ordinary_buttons_only': True, 'RAM_edits': False,
              'states_loaded': False, 'user_batteries_opened': False,
              'base_peon_runtime_scope': 'Scripted opening forced LEFT pose; source VRAM/OAM and actual LCD capture only, no free walking or four-direction coverage.',
              'classes': {}, 'status': 'RUNNING'}
    sym = symbols(args.sym)
    with tempfile.TemporaryDirectory(prefix='peon-world-actors-v0215-') as temp:
        for name in args.classes.split(','):
            index = CLASSES.index(name)
            rom = Path(temp) / (name + '.gbc')
            shutil.copyfile(args.rom, rom)
            session = WorldActorSession(rom, sym, index, args.output)
            try:
                session.fresh_class()
                directions = session.direction_checks()
                session.navigate((10, 10))
                session.p.tick(90, True)
                available_marker = session.gornek_marker('native_available_marker_above_actor')
                session.talk_at((10, 10), 'up', 'native_gornek_quest_with_larger_actor')
                assert session.event('EVENT_PEON_QUEST_ACCEPTED')
                session.p.tick(90, True)
                npc = session.scene('nearby_quest_NPC_after_dialogue')
                active_marker = session.gornek_marker('native_active_marker_above_actor')
                occupied = {actor['xy'] for actor in session.live_actors('TheDen')}
                crowded_point = next(point for point in ((10, 11), (11, 11), (10, 12))
                                     if point not in occupied and session.collision_at(*point) != 'WALL')
                session.navigate(crowded_point)
                session.p.tick(90, True)
                crowded = session.scene('den_crowded_priority', strict_lcd=True)
                samples = []
                for _ in range(3):
                    session.p.tick(90, True)
                    samples.append(session.scene())
                assert [sample['actors'] for sample in samples] == [samples[0]['actors']] * 3
                report['classes'][name] = {'directions': directions, 'base_opening': session.base_intro,
                                         'nearby_NPC_interaction': npc, 'crowded_scene': crowded,
                                         'crowded_native_position': list(session.position()),
                                         'quest_markers': {'available': available_marker, 'active': active_marker},
                                         'whole_actor_scene_checks': session.body_checks,
                                         'complete_renderer_histogram_checks': session.histogram_checks,
                                         'native_current_object_context_preserved': True}
            except Exception as exc:
                report['status'], report['failure'] = 'FAIL', repr(exc)
                session.capture('failure')
                (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
                raise
            finally:
                session.p.stop(save=False)
    report['status'] = 'PASS'
    (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'rom_sha256': digest, 'classes': list(report['classes'])}), flush=True)


if __name__ == '__main__':
    main()
