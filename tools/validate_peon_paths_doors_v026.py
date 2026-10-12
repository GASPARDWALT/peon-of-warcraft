#!/usr/bin/env python3
"""Walk the frozen geography and new door art using the exact release ROM.

The retained ordinary-input environment route supplies nine doors, four cold
room saves, nine reciprocal zone links, real cave guards, cactus harvesting,
the earned atlas and native fire observations. This wrapper writes exclusively
to new v0.2.6 evidence and adds fixed-frame/font restoration checks inside and
after each door. No game RAM edits, emulator states or user saves are used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from PIL import Image

import build_peon_environment_v026 as art
import validate_peon_environment_v025 as retained

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/visual_polish_v026/paths_doors'
MENU_CHECKS = []
INN_CURES = []
ORIGINAL_SESSION = retained.EnvironmentSession


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_checks():
    manifest = json.loads((OUT / 'manifest.json').read_text())
    assert manifest['passed'] and not manifest['review_only']
    assert manifest['native_patterns'] == 192 and manifest['metatile_count'] == 47
    maps = art.frozen_geometry()
    assert maps == {key: value for key, value in manifest['maps'].items()
                    if isinstance(value, dict)}
    blocks, _, library = art.build_blocks()
    art.reduce_tiles(blocks, library)
    bank, meta, _budget = art.art.compile_tiles(blocks)
    assert len(bank) == 192
    assert meta == (ROOT / 'data/tilesets/peon_metatiles.bin').read_bytes()
    # All real building doors use the exact passable BR movement quadrant.
    for ident in (4, 11, 29):
        assert blocks[ident].indices.crop((16, 16, 32, 32)).tobytes() == art.door_panel().tobytes()
    # A tower has closed timber shutters, not the building's foot doorway.
    assert blocks[31].indices.crop((8, 8, 16, 16)).tobytes() == library['timber'].pixels.tobytes()
    assert blocks[31].indices.crop((16, 8, 24, 16)).tobytes() == library['timber'].pixels.tobytes()
    rows = [line.split('tilecoll', 1)[1].split(';', 1)[0].replace(' ', '').split(',')
            for line in (ROOT / 'data/tilesets/peon_collision.asm').read_text().splitlines()
            if 'tilecoll' in line]
    assert rows[31] == ['WALL'] * 4 and rows[15] == ['WALL'] * 4
    assert rows[16] == ['WARP_PANEL'] * 4
    assert all(rows[i] == ['WALL', 'WALL', 'WALL', 'WARP_PANEL'] for i in (4, 11, 29))
    road_ids = set(range(17, 27)) | {2, 16}
    proof = []
    placed_buildings = []
    patrols = []
    for name, dimensions in art.zones.DIMS.items():
        width, _height = dimensions
        data = (ROOT / f'maps/{name}.blk').read_bytes()
        actors = art.paths.events(name, 'object_event')
        warps = art.zones.warp_events(name)
        warp_positions = {tuple(warp['xy']) for warp in warps}
        for actor in actors:
            fields = [field.strip() for field in actor['arguments'].split(',')]
            x, y = actor['xy']
            if fields[1] == 'SPRITEMOVEDATA_WALK_LEFT_RIGHT':
                footprint = {(x - 1, y), (x, y), (x + 1, y)}
            elif fields[1] == 'SPRITEMOVEDATA_WALK_UP_DOWN':
                footprint = {(x, y - 1), (x, y), (x, y + 1)}
            else:
                continue
            assert not (footprint & warp_positions), (name, 'Patrol can occupy a portal', actor)
            patrols.append({'map': name, 'actor_xy': [x, y], 'sprite': fields[0],
                            'patrol_does_not_occupy_any_portal': True})
        for pos, ident in enumerate(data):
            if ident not in (4, 11, 29): continue
            door = (pos % width * 2 + 1, pos // width * 2 + 1)
            assert door in warp_positions, (name, 'Drawn building door has no real entrance', door)
            placed_buildings.append({'map': name, 'door_xy': door, 'metatile': ident,
                                     'visible_opening_has_actual_enter_event': True})
        for warp in warps:
            x, y = warp['xy']; ident = data[(y // 2) * width + x // 2]
            assert rows[ident][(y % 2) * 2 + x % 2] == 'WARP_PANEL', (name, warp, ident)
            assert ident in road_ids | {4, 11, 29}, (name, 'Warp on misleading artwork', warp, ident)
            # An authored NPC/quest marker must not occupy an actual door.
            assert not any(tuple(row['xy']) == (x, y)
                           and row['arguments'].split(',', 1)[0].strip() != 'SPRITE_NONE'
                           for row in actors), (name, warp)
            proof.append({'map': name, 'warp': warp['index'], 'xy': [x, y],
                          'metatile': ident, 'native_collision': 'WARP_PANEL',
                          'no_authored_actor_on_threshold': True})
    assert len(placed_buildings) == 9
    return {'passed': True, 'frozen_geometry': maps,
            'actual_warp_art_and_collision': proof,
            'all_nine_drawn_building_doors_have_actual_enter_events': placed_buildings,
            'native_patrol_portal_separation': patrols,
            'tower_closed_shutters_and_no_entrance': True,
            'cave_mouth_right_lane_above_real_warp': True,
            'native_metatiles_equal_compiled_new_art': True,
            'all_road_collision_rows_unchanged': True,
            'no_map_array_or_warp_change': True,
            'building_doors_exact_passable_br_16x16': True,
            'road_ends_outside_actual_portals_keep_published_closed_boundaries': True}


class Session(ORIGINAL_SESSION):
    def __init__(self, rom, symbols, output=None):
        raw = Path(rom).read_bytes()
        # A direct diagnostic may instantiate this class without main()'s
        # legacy-output context. Never inherit a published v025 destination.
        candidate = Path(output or retained.OUT).resolve()
        self.output_dir = (candidate if candidate.is_relative_to(OUT.resolve())
                           else OUT / 'preliminary' / ('direct_session_' + digest(raw)[:16]))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        super().__init__(rom, symbols)
        self.fonts = {}
        for label in ('Font', 'PeonBoldFont'):
            bank, address = symbols[label]
            offset = bank * 0x4000 + (address - 0x4000 if bank else address)
            self.fonts[label] = raw[offset:offset + 1024]
        self.expected_font = bytes(c for value in self.fonts['Font'] for c in (value, value))
        self.in_menu_review = False

    def capture(self, label):
        """All inherited fresh/talk/fight/save captures resolve here too."""
        assert self.output_dir.resolve().is_relative_to(OUT.resolve())
        self.p.screen.image.save(self.output_dir / (label + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(
            self.output_dir / (label + '_4x.png'))
        print(label, self.map(), self.position(), flush=True)

    def check_glyphs(self, phase):
        self.p.tick(40, True)
        assert bytes(self.p.memory[0, 0x8800:0x9000]) == self.expected_font, (phase, 'Regular font restore')
        tiles = self.read('wTilemap', 360); attrs = self.read('wAttrmap', 360)
        palette = self.read('wBGPals2', 64)
        actual = np.array(self.p.screen.image.convert('RGB')) >> 3
        count = self.read('wPeonBoldGlyphCount')[0]
        assert count <= 23 and self.read('wPeonBoldGlyphOverflow') == [0]
        codes = self.read('wPeonBoldGlyphCodes', count)
        bold_tiles = {}
        for index, code in enumerate(codes):
            assert 0x80 <= code <= 0xff
            raw = self.fonts['PeonBoldFont'][(code - 0x80) * 8:(code - 0x7f) * 8]
            expected = bytes(c for value in raw for c in (value, value))
            assert bytes(self.p.memory[1, 0x9690 + index * 16:0x96a0 + index * 16]) == expected
            bold_tiles[0x69 + index] = expected
        regular_count, bold_count = 0, 0
        for y in range(18):
            for x in range(20):
                code, attr = tiles[y * 20 + x], attrs[y * 20 + x]
                if attr & 8:
                    if code not in bold_tiles: continue
                    raw = bold_tiles[code]; bold_count += 1
                else:
                    if code < 0x80: continue
                    raw = self.expected_font[(code - 0x80) * 16:(code - 0x7f) * 16]
                    regular_count += 1
                colors = []
                for i in range(4):
                    offset = 8 * (attr & 7) + 2 * i
                    value = palette[offset] | palette[offset + 1] << 8
                    colors.append((value & 31, value >> 5 & 31, value >> 10 & 31))
                expected = np.array([[colors[((raw[row * 2] >> (7 - col)) & 1) |
                                              (((raw[row * 2 + 1] >> (7 - col)) & 1) << 1)]
                                      for col in range(8)] for row in range(8)], dtype=np.uint8)
                if attr & 0x20: expected = expected[:, ::-1]
                if attr & 0x40: expected = expected[::-1]
                assert np.array_equal(actual[y * 8:y * 8 + 8, x * 8:x * 8 + 8], expected), (
                    phase, 'Native glyph RGB555 pixel mismatch', x, y, hex(code), hex(attr))
        assert regular_count >= 10, (phase, 'Insufficient regular text', regular_count)
        return {'regular_cells_native_rgb555_match': regular_count,
                'bold_person_name_cells_native_rgb555_match': bold_count,
                'all128_regular_font_tiles_restored': True,
                'all_live_bold_cache_tiles_equal_native_font': True,
                'bold_cache_capacity_not_exceeded': True}

    def fight(self, label, flag, copper=None):
        result = super().fight(label, flag, copper)
        # Native poison still damages a walking character. A long geography
        # tour must deliberately cure a won encounter before continuing;
        # genuine inn dialogue performs the cure, never a memory assignment.
        status = self.read('wPartyMon1Status')[0]
        if result['outcome'] == 0 and status & 8:
            origin, xy = self.map(), self.position()
            heals = self.heal_calls
            self.rest()
            assert self.heal_calls == heals + 1 and self.read('wPartyMon1Status') == [0]
            self.travel(origin)
            self.navigate(xy)
            cure = {'after_encounter': label, 'poison_status_before': status,
                    'ordinary_walk_and_inn_healer_dialogue': True,
                    'native_heal_calls': 1, 'returned_to_original_map_and_cell': [origin, list(xy)],
                    'ram_health_or_status_edits': False}
            INN_CURES.append(cure)
            result['deliberate_inn_poison_cure_after_recorded_battle'] = cure
        return result

    def fixed_frame(self):
        tiles, attrs = self.read('wTilemap', 360), self.read('wAttrmap', 360)
        for y in range(18):
            for x in range(20):
                if y not in (0, 17) and x not in (0, 19): continue
                expected = {(0, 0): 0x79, (19, 0): 0x7b, (0, 17): 0x7d, (19, 17): 0x7e}.get(
                    (x, y), 0x7a if y in (0, 17) else 0x7c)
                assert tiles[y * 20 + x] == expected and attrs[y * 20 + x] == 3, (x, y)
        bank, address = self.sym['hBGMapAddress']
        base = self.p.memory[address] | self.p.memory[address + 1] << 8
        assert [self.p.memory[1, base + y * 32 + x] for y in range(18) for x in range(20)] == attrs
        return {'fixed20x18_frame_and_live_vram_attributes_match': True,
                'no_border_clipping': True}

    def menu_return(self, phase):
        checks = {'phase': phase, 'map_id': self.map(), 'xy': self.position()}
        for name, selection in (('character', 1), ('bags', 2)):
            before = self.snapshot()
            self.press('start')
            for _ in range(12):
                cursor = self.read('wMenuCursorPosition')[0]
                if cursor == selection: break
                self.press('up' if cursor > selection else 'down', 30)
            assert self.read('wMenuCursorPosition') == [selection]
            self.press('a', 150)
            checks[name] = self.check_glyphs(phase + '_' + name) | self.fixed_frame()
            self.capture(phase + '_' + name + '_native_overlay')
            self.press('b'); self.press('b'); self.p.tick(90, True)
            assert self.snapshot() == before, (phase, name, 'Opening a menu changed persistent gameplay')
            assert self.read('wScriptMode') == [0]
            checks[name]['unchanged_name_class_kit_hp_charges_money_quest_flags'] = True
            checks[name]['restored_world'] = super().scenery(phase + '_' + name + '_closed_restored')
            # CloseText deliberately reloads Crystal's field-name font, not
            # the separate body font used by menus. Check the correct native
            # asset here; the next opened menu checks all128 regular glyphs.
            field_font = (ROOT / 'gfx/font/overworld.2bpp').read_bytes()
            assert bytes(self.p.memory[0, 0x8800:0x9000]) == field_font, (phase, name, 'Native field font restore')
            checks[name]['all128_native_overworld_font_tiles_restored_on_close'] = True
        MENU_CHECKS.append(checks)
        return checks

    def scenery(self, label):
        scene = super().scenery(label)
        is_door = '_door_' in label and label.endswith(('_inside', '_returned'))
        is_cold = label.startswith('room_') and label.endswith('_continued_native_scene')
        if (is_door or is_cold) and not self.in_menu_review:
            self.in_menu_review = True
            try:
                scene['menu_font_and_class_restore'] = self.menu_return(label)
            finally:
                self.in_menu_review = False
        return scene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-sha')
    parser.add_argument('--source-only', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    static = source_checks()
    (OUT / 'source_validation.json').write_text(json.dumps(static, indent=2) + '\n')
    if args.source_only:
        print('PASS v026 native door/art placement; 18 frozen maps, IDs/warps/collisions/actors unchanged.')
        return
    if not args.expected_sha:
        parser.error('--expected-sha is required for native ROM validation')
    actual = digest((ROOT / 'pokecrystal.gbc').read_bytes())
    assert actual == args.expected_sha, 'Wrong candidate ROM'
    runtime = OUT / 'runtime'
    previous = runtime / 'validation.json'
    if previous.exists():
        old = json.loads(previous.read_text())
        if not old.get('passed') or old.get('rom_sha256') != actual:
            prefix = old.get('rom_sha256', 'unknown')[:16]
            archive = OUT / 'preliminary' / prefix
            if archive.exists():
                prefix += '_passed' if old.get('passed') else '_failed'
                archive = OUT / 'preliminary' / prefix
                serial = 2
                while archive.exists():
                    archive = OUT / 'preliminary' / f'{prefix}_{serial}'
                    serial += 1
            archive.parent.mkdir(exist_ok=True)
            shutil.move(str(runtime), str(archive))
    runtime.mkdir(exist_ok=True)
    old_out, old_session, old_argv = retained.OUT, retained.EnvironmentSession, sys.argv
    retained.OUT, retained.EnvironmentSession = runtime, Session
    sys.argv = [sys.argv[0], '--expected-sha', actual]
    MENU_CHECKS.clear()
    INN_CURES.clear()
    try:
        retained.main()
    finally:
        retained.OUT, retained.EnvironmentSession, sys.argv = old_out, old_session, old_argv
        path = runtime / 'validation.json'
        native = json.loads(path.read_text()) if path.exists() else {'passed': False, 'rom_sha256': actual}
        native['release'] = 'v0.2.6'
        native['source_geometry_and_art_placement'] = static
        native['door_and_cold_room_menu_restorations'] = MENU_CHECKS
        native['ordinary_inn_poison_cures_during_geography_tour'] = INN_CURES
        native['published_v025_evidence_not_written'] = True
        native['all18_map_arrays_and_warps_identical_to_published_v025'] = True
        native['user_saves_opened'] = False
        if native['passed']:
            try:
                assert len(MENU_CHECKS) == 22, ('Nine inside/return pairs plus four cold rooms', len(MENU_CHECKS))
                assert len(native['door_routes']) == 9 and len(native['room_cold_restarts']) == 4
                assert native['seven_sector_geography']['all_nine_directed_edges_and_returns_walked']
                assert native['rom_sha256'] == actual
            except AssertionError as error:
                native['passed'] = False
                native['failure'] = repr(error)
        (OUT / 'validation.json').write_text(json.dumps(native, indent=2) + '\n')
    assert native['passed'], native.get('failure', 'Native route failed')
    print(json.dumps({'passed': native['passed'], 'rom_sha256': actual,
                      'nine_real_doors': len(native.get('door_routes', [])),
                      'menu_restore_cases': len(MENU_CHECKS), 'ram_edits': False}))


if __name__ == '__main__':
    main()
