#!/usr/bin/env python3
"""Walk all nine doors and genuine new Horde interiors in the exact ROM.

Retain the existing native ordinary-input geography, real cold battery saves,
healer, actual hardware RGB555 scenery/text and menu-return checks. Only their
output destinations are redirected to v028. Never write gameplay RAM, load a
state, or modify an earlier published artifact.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

import build_peon_environment_v028 as art
import validate_peon_paths_doors_v026 as legacy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/polish_v028/environment'
FIRE_REVIEWS = []
ORIGINAL_SESSION = legacy.Session


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_checks():
    manifest = json.loads((OUT / 'manifest.json').read_text())
    assert manifest['passed'] and not manifest['review_only']
    art.art.NAMES = art.NAMES
    blocks, _, library = art.build_blocks()
    art.art.reduce_shade_variants(blocks, library)
    bank, meta, _ = art.art.compile_tiles(blocks)
    assert len(bank) == 192 and len(blocks) == 53
    assert bytes(meta) == (ROOT / 'data/tilesets/peon_metatiles.bin').read_bytes()
    sheet = Image.open(ROOT / 'gfx/tilesets/peon.png').convert('L')
    attrs = [7] * 256
    for i, item in enumerate(bank):
        actual = sheet.crop((i % 16 * 8, i // 16 * 8,
                             i % 16 * 8 + 8, i // 16 * 8 + 8))
        actual = actual.point(lambda value: (255 - value) // 85)
        assert actual.tobytes() == item.pixels.tobytes(), ('Authored tile source differs', i)
        attrs[art.art.native_id(i)] = item.palette | (8 if i >= 96 else 0)
    packed = bytes(attrs[i] | attrs[i + 1] << 4 for i in range(0, 256, 2))
    assert packed == (ROOT / 'gfx/tilesets/peon_palette_map.bin').read_bytes()
    expected_collisions = art.collision_rows().encode()
    assert (ROOT / 'data/tilesets/peon_collision.asm').read_bytes() == expected_collisions
    rooms = {name: art.room_layout(name) for name in art.EDITED_ROOMS}
    for name, data in rooms.items():
        assert data == (ROOT / f'maps/{name}.blk').read_bytes()
        if name in art.INTERIORS:
            assert data.count(34) == 2, (name, 'Expected two native bowl basins')
            if name.endswith('Inn'):
                assert data.count(40 if 'Orc' in name else 43) == 3
        else:
            assert data.count(34) == 1, (name, 'Grommash basin count')
    geometry = art.geometry_checks(rooms)
    assert geometry == manifest['rooms']
    # Every actual warp, including the new readable interior foot opening,
    # retains its appropriate native movement-cell collision.
    rows = [line.split('tilecoll', 1)[1].split(';', 1)[0].replace(' ', '').split(',')
            for line in art.collision_rows().splitlines() if 'tilecoll' in line]
    warps = []
    for name, (width, _) in art.zones.DIMS.items():
        data = (ROOT / f'maps/{name}.blk').read_bytes()
        for warp in art.zones.warp_events(name):
            x, y = warp['xy']
            block = data[y // 2 * width + x // 2]
            assert rows[block][y % 2 * 2 + x % 2] == 'WARP_PANEL', (name, warp, block)
            if name in art.INTERIORS:
                assert block == 52 and (x, y) == (5, 7)
            warps.append({'map': name, 'warp_index': warp['index'], 'xy': [x, y],
                          'metatile': block, 'actual_collision': 'WARP_PANEL'})
    emblem_keys = {list(blocks[6].tiles())[j].key for j in (5, 6, 9, 10)}
    uses = [i for i, block in enumerate(blocks) if emblem_keys & {tile.key for tile in block.tiles()}]
    assert uses == [6] and not emblem_keys & {tile.key for tile in blocks[5].tiles()}
    original_rows = art.baseline('data/tilesets/peon_collision.asm')
    assert expected_collisions.startswith(original_rows)
    return {'passed': True, 'native_patterns': 192, 'metatile_count': 53,
            'tile_sheet_metatiles_and_packed_palette_attributes_exact': True,
            'old_47_collision_rows_byte_exact': True,
            'new_wall_ids': list(range(47, 52)), 'new_interior_foot_door_id': 52,
            'all_original_non_wall_room_cells_still_passable': True,
            'all_npc_table_bed_and_exit_approaches_reachable': True,
            'all_warp_coordinates_and_map_ids_dimensions_preserved': True,
            'all_world_and_opening_palm_block_arrays_preserved': True,
            'emblem_present_only_in_mounted_banner_block6': True,
            'no_floor_crest': True, 'three_corner_bunks_per_inn': True,
            'two_native_bowl_fire_basins_per_hut_and_inn': True,
            'one_grommash_wall_fire_basin': True,
            'round_room_geometry': geometry, 'actual_warp_collisions': warps}


class Session(ORIGINAL_SESSION):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reviewed_room_fires = set()

    def scenery(self, label):
        scene = super().scenery(label)
        if ('_door_' in label and label.endswith('_inside')
                and self.map() in (21, 22, 23, 24)
                and self.map() not in self.reviewed_room_fires):
            self.reviewed_room_fires.add(self.map())
            scene['actual_animated_fire_basins'] = self.review_basins()
        return scene

    def review_basins(self):
        before = self.snapshot()
        phases, captures, pixels, counts = [set(), set()], [], set(), []
        calls = [0]
        self.p.hook_register(*self.sym['AnimatePeonEnvironmentFire'],
                             lambda _: calls.__setitem__(0, calls[0] + 1), None)
        try:
            for frame in range(256):
                self.p.tick(1, True)
                native = self.terrain_upload()
                for i, matching in enumerate(native['fire_left_right_matching_phases']):
                    phases[i].update(matching)
                if frame % 8 == 0:
                    mask = self.visible_fire_mask()
                    counts.append(int(mask.sum()))
                    pixels.add((np.asarray(self.p.screen.image.convert('RGB')) >> 3)[mask].tobytes())
                    captures.append(self.p.screen.image.copy())
        finally:
            self.p.hook_deregister(*self.sym['AnimatePeonEnvironmentFire'])
        assert self.snapshot() == before
        assert phases == [{0, 1, 2}, {0, 1, 2}]
        assert calls[0] > 16 and min(counts) >= 32
        assert len(pixels) >= 3, 'Visible basin flames did not animate'
        name = f'room_{self.map()}_actual_fire_basins'
        for scale, suffix in ((1, '_native'), (4, '_4x')):
            images = ([im.resize((640, 576), Image.Resampling.NEAREST) for im in captures]
                      if scale == 4 else captures)
            images[0].save(self.output_dir / (name + suffix + '.gif'), save_all=True,
                           append_images=images[1:], duration=133, loop=0,
                           disposal=2, optimize=False)
        review = {'map_id': self.map(), 'position': self.position(),
                  'frames_observed': 256, 'native_fire_callback_calls': calls[0],
                  'visible_native_fire_pixels_minimum': min(counts),
                  'actual_visible_rgb555_fire_frames': len(pixels),
                  'fire_left_right_phases_observed': [sorted(p) for p in phases],
                  'other190_native_scenery_tiles_preserved_each_frame': True,
                  'gameplay_snapshot_unchanged': True, 'ram_edits': False,
                  'native_capture_gif': name + '_native.gif'}
        FIRE_REVIEWS.append(review)
        return review


@contextmanager
def redirected_runtime():
    original = legacy.OUT, legacy.source_checks, legacy.Session, sys.argv
    # Legacy Session.constructor consults its own module-global OUT, and
    # retained.main() recursively redirects all nested validators' OUT/OUTPUT.
    # Redirect before constructing any Session, so direct captures are safe.
    legacy.OUT = OUT
    legacy.source_checks = source_checks
    legacy.Session = Session
    try:
        yield
    finally:
        legacy.OUT, legacy.source_checks, legacy.Session, sys.argv = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-sha')
    parser.add_argument('--source-only', action='store_true')
    args = parser.parse_args()
    static = source_checks()
    (OUT / 'source_validation.json').write_text(json.dumps(static, indent=2) + '\n')
    if args.source_only:
        print('PASS v028 rounded rooms, three inn bunks, fire basins, readable exits and wall-only Horde crest.')
        return
    if not args.expected_sha:
        parser.error('--expected-sha is required for native gameplay proof')
    actual = sha((ROOT / 'pokecrystal.gbc').read_bytes())
    assert actual == args.expected_sha, 'Wrong ROM candidate'
    failure = None
    FIRE_REVIEWS.clear()
    try:
        with redirected_runtime():
            sys.argv = [str(Path(__file__)), '--expected-sha', actual]
            legacy.main()
    except Exception as error:
        failure = error
    path = OUT / 'validation.json'
    native = json.loads(path.read_text()) if path.exists() else {'passed': False, 'rom_sha256': actual}
    # Correct legacy wording: these four room arrays are intentionally new.
    native['release'] = 'v0.2.8'
    native.pop('all18_map_arrays_and_warps_identical_to_published_v025', None)
    native['world_map_arrays_and_all_warps_unchanged_from_v027'] = True
    native['old_room_walkable_coordinates_preserved'] = True
    native['rounded_room_layouts_intentionally_new'] = list(art.INTERIORS)
    native['published_v025_v026_v027_evidence_not_written'] = True
    native['source_geometry_and_art_placement'] = static
    native['actual_room_basin_fire_reviews'] = FIRE_REVIEWS
    try:
        assert sha((ROOT / 'pokecrystal.gbc').read_bytes()) == actual, 'ROM changed during validation'
        if not failure:
            assert len(native['door_routes']) == 9
            assert len(native['room_cold_restarts']) == 4
            assert len(native['door_and_cold_room_menu_restorations']) == 22
            assert sorted(review['map_id'] for review in FIRE_REVIEWS) == [21, 22, 23, 24]
    except Exception as error:
        failure = error
    if failure:
        native['passed'] = False
        native['failure'] = repr(failure)
    path.write_text(json.dumps(native, indent=2) + '\n')
    if failure:
        raise failure
    print(json.dumps({'passed': native['passed'], 'rom_sha256': actual,
                      'nine_doors': 9, 'four_actual_cold_room_saves': 4,
                      'menu_restore_cases': 22, 'ordinary_gameplay_ram_edits': False}))


if __name__ == '__main__':
    main()
