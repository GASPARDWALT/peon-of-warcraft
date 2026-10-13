#!/usr/bin/env python3
"""Import a separately generated, previously missing Earth Elemental design.

The original source master is never modified. This is a documented lossy raster
conversion, not a native-grid extraction and not supplied user artwork. No
anatomy, walking frames, circles or polygon substitutes are drawn here.
"""
from pathlib import Path
import hashlib
import json
import subprocess

import numpy as np
from PIL import Image

from build_peon_user_battle_v0211 import encode
from build_peon_user_world_v0211 import encode_world_frame, WORLD_PALETTES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/earth_elemental_v0212'
GFX = ROOT / 'gfx/earth_elemental_v0212'
MASTER = OUT / 'originals/earth_elemental_generated_master.png'
ALPHA_THRESHOLD = 128
DIRECTIONS = ('front', 'back', 'left', 'right')
CROPS = {
    'world_front': (21, 166, 312, 458),
    'world_back': (344, 166, 638, 458),
    'world_left': (687, 166, 883, 468),
    'world_right': (987, 166, 1185, 468),
    'combat_front': (21, 552, 729, 1201),
    'combat_back': (738, 574, 1232, 1206),
}
REFERENCES = (
    'references/characters/peon_world_character_sheets_split/boar/boar_sheet.png',
    'references/characters/peon_world_character_sheets_split/scorpid/scorpid_sheet.png',
    'references/characters/peon_world_character_sheets_split/imp/imp_sheet.png',
    'references/generated/peon_sprite_redesign_v030/originals/peon_shaman_totemic_design_reference.png',
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return str(path.relative_to(ROOT))


def save_preview(name, rgba):
    rgba = rgba.astype('uint8').copy()
    rgba[rgba[:, :, 3] == 0] = 0
    im = Image.fromarray(rgba, 'RGBA')
    path = OUT / 'comparisons' / (name + '.png')
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    im.resize((im.width * 8, im.height * 8), Image.Resampling.NEAREST).save(
        path.with_name(name + '_8x.png'))


def import_pose(name, original):
    bounds = CROPS[name]
    crop = np.asarray(original.crop(bounds)).copy()
    source_alpha = crop[:, :, 3].copy()
    crop[:, :, 3] = np.where(source_alpha >= ALPHA_THRESHOLD, 255, 0)
    crop[crop[:, :, 3] == 0] = 0
    size = 16 if name.startswith('world') else 56 if name.endswith('front') else 48
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    scale = min((size - 2) / width, (size - 2) / height)
    fitted = (round(width * scale), round(height * scale))
    offset = ((size - fitted[0]) // 2, (size - fitted[1]) // 2)
    reduced = Image.fromarray(crop).resize(fitted, Image.Resampling.NEAREST)
    native = Image.new('RGBA', (size, size))
    native.paste(reduced, offset)
    path = OUT / 'sprites' / (name + '.png')
    path.parent.mkdir(parents=True, exist_ok=True)
    native.save(path)
    original.crop(bounds).save(OUT / 'comparisons' / (name + '_source_crop.png'))
    save_preview(name + '_native', np.asarray(native))
    a = np.asarray(native)
    return a, {
        'pose': name, 'source': relative(MASTER), 'source_sha256': sha(MASTER),
        'source_canvas': list(original.size), 'crop_bounds_exclusive': list(bounds),
        'crop_dimensions': [width, height], 'native_dimensions': [size, size],
        'fitted_dimensions': list(fitted), 'centering_offset': list(offset),
        'minimum_transparent_border': 1,
        'source_intermediate_alpha_pixels': int(((source_alpha > 0) & (source_alpha < 255)).sum()),
        'alpha_conversion': 'alpha >=128 becomes255; alpha <128 becomes0; transparent RGB0',
        'resampling': 'Pillow nearest-neighbor, no pixel drawing or dithering',
        'native_grid_recovered': False, 'source_geometry_unchanged': False,
        'native_path': relative(path), 'native_sha256': sha(path),
        'native_binary_alpha': bool(set(np.unique(a[:, :, 3])) <= {0, 255}),
        'native_visible_pixels': int((a[:, :, 3] != 0).sum()),
    }


def source_palettes(frames):
    """Use source RGB555 medoids for stone, ink and distinctive green energy."""
    pixels = np.concatenate([a[:, :, :3][a[:, :, 3] > 0] >> 3 for a in frames])
    colors, counts = np.unique(pixels, axis=0, return_counts=True)
    colors = colors.astype('int32')
    green_mask = (colors[:, 1] > colors[:, 0] + 4) & (colors[:, 1] > colors[:, 2] + 4)
    greens, stones = colors[green_mask], colors[~green_mask]
    assert len(greens), 'Green earthen-energy source pixels missing'
    def closest(group, anchor):
        return tuple(map(int, group[((group - np.array(anchor)) ** 2).sum(1).argmin()]))
    ink = closest(stones, (3, 2, 3))
    light = closest(stones, (27, 21, 14))
    mid = closest(stones, (15, 10, 6))
    green = closest(greens, (22, 29, 2))
    return [[(31, 31, 31), light, mid, ink],
            [(31, 31, 31), green, light, ink]]


def pack_palette(palettes):
    return b''.join(int(r | g << 5 | b << 10).to_bytes(2, 'little')
                    for p in palettes for r, g, b in p)


def hardware_reduce(a, palettes):
    h, w = a.shape[:2]
    indices = np.zeros((h, w), dtype='uint8')
    preview = np.zeros_like(a)
    choices = []
    for y in range(0, h, 8):
        for x in range(0, w, 8):
            region = a[y:y + 8, x:x + 8]
            visible = region[:, :, 3] > 0
            rgb = region[:, :, :3].astype('int32') >> 3
            greens = (rgb[:, :, 1] > rgb[:, :, 0] + 4) & (rgb[:, :, 1] > rgb[:, :, 2] + 4) & visible
            errors = []
            for palette in palettes:
                error = ((rgb[:, :, None] - np.array(palette[1:])) ** 2).sum(3).min(2)
                # Source green marks carry identity; give their loss extra weight.
                errors.append(float((error * visible * np.where(greens, 5, 1)).sum()))
            choice = int(np.argmin(errors))
            choices.append(choice)
            palette = np.array(palettes[choice])
            fit = ((rgb[:, :, None] - palette[None, None, 1:]) ** 2).sum(3).argmin(2) + 1
            fit[~visible] = 0
            indices[y:y + 8, x:x + 8] = fit
            preview[y:y + 8, x:x + 8, :3] = (palette[fit] << 3) | (palette[fit] >> 2)
            preview[y:y + 8, x:x + 8, 3] = region[:, :, 3]
    assert np.array_equal(preview[:, :, 3], a[:, :, 3])
    return indices, preview, choices


def emit_battle(name, a, slots, palettes):
    folder = GFX / name
    folder.mkdir(parents=True, exist_ok=True)
    indices, preview, choices = hardware_reduce(a, palettes)
    frame = encode(indices, True)
    (folder / 'frames.2bpp').write_bytes(frame * 3)
    (folder / 'attrs.bin').write_bytes(bytes(slots[c] for c in choices))
    (folder / 'palettes.bin').write_bytes(pack_palette(palettes))
    (folder / 'palettes.pal').write_text(''.join('\tRGB ' + ', '.join(map(str, c)) + '\n'
                                               for p in palettes for c in p))
    rawfile = 'front.2bpp' if a.shape[0] == 56 else 'back.2bpp'
    # Front has the native loader's second 49-tile packet; all changes empty.
    native_packet = frame + bytes(49 * 16) if rawfile.startswith('front') else frame
    (folder / rawfile).write_bytes(native_packet)
    subprocess.run([str(ROOT / 'tools/lzcompress'), str(folder / rawfile),
                    str(folder / (rawfile + '.lz'))], check=True)
    if rawfile.startswith('front'):
        (folder / 'anim.asm').write_text('\tframe 0, 10\n\tframe 0, 08\n\tframe 0, 10\n\tendanim\n')
        (folder / 'anim_idle.asm').write_text('\tframe 0, 16\n\tendanim\n')
        (folder / 'frames.asm').write_text('\tdw .frame1\n.frame1\n\tdb $00 ; static generated canonical pose\n')
        (folder / 'bitmask.asm').write_text('\tdb 0, 0, 0, 0, 0, 0, 0\n')
    save_preview(name + '_hardware', preview)
    return {'name': name, 'native_dimensions': [a.shape[1], a.shape[0]],
            'slots': slots, 'palettes_rgb555': palettes, 'tile_order': 'column-major',
            'attribute_order': 'row-major', 'static_pose_slots': 3,
            'bytes_per_frame': len(frame), 'frames_path': relative(folder / 'frames.2bpp'),
            'native_packet_path': relative(folder / (rawfile + '.lz')),
            'hardware_alpha_unchanged_from_native_png': True,
            'opaque_colors_per_tile_maximum': 3, 'tile_count': len(choices),
            'green_energy_tile_family_count': choices.count(1),
            'frames_sha256': sha(folder / 'frames.2bpp')}


def emit_world(poses, palettes):
    # One OBJ palette: highlight stone, green energy, deep stone outline.
    palette = WORLD_PALETTES[2] # Existing brown/green family; no global OBJ slot replaced.
    packet = b''
    records = []
    for direction in DIRECTIONS:
        a = poses['world_' + direction]
        rgb = a[:, :, :3].astype('int32') >> 3
        indices = (((rgb[:, :, None] - np.array(palette[1:])) ** 2).sum(3).argmin(2) + 1).astype('uint8')
        indices[a[:, :, 3] == 0] = 0
        packet += encode_world_frame(indices)
        colors = np.array(palette)
        preview = np.dstack(((colors[indices] << 3) | (colors[indices] >> 2), a[:, :, 3])).astype('uint8')
        save_preview('world_' + direction + '_hardware', preview)
        records.append({'direction': direction, 'native_alpha_preserved': True})
    (GFX / 'overworld.bin').write_bytes(packet * 3)
    (GFX / 'world.pal').write_text(''.join('\tRGB ' + ', '.join(map(str, c)) + '\n' for c in palette))
    (GFX / 'world_palette.bin').write_bytes(pack_palette([palette]))
    return {'palette_rgb555': palette, 'opaque_OBJ_colors': 3,
            'directions': list(DIRECTIONS), 'phases': 3, 'phases_identical': True,
            'bytes': 768, 'path': relative(GFX / 'overworld.bin'),
            'global_OBJ_palette_index': 2,
            'records': records}


def contact_sheet(poses):
    # A source/hardware preview only; never represents emulator evidence.
    for kind in ('native', 'hardware'):
        sheet = Image.new('RGBA', (200, 60))
        for i, direction in enumerate(DIRECTIONS):
            p = OUT / 'comparisons' / f'world_{direction}_{kind}.png'
            sheet.paste(Image.open(p), (i * 20, 22))
        front_name = 'combat_front_native' if kind == 'native' else 'enemy_front_hardware'
        back_name = 'combat_back_native' if kind == 'native' else 'ally_back_hardware'
        sheet.paste(Image.open(OUT / 'comparisons' / (front_name + '.png')), (88, 2))
        sheet.paste(Image.open(OUT / 'comparisons' / (back_name + '.png')), (150, 6))
        sheet.save(OUT / 'comparisons' / (kind + '_contact_sheet.png'))
        sheet.resize((1600, 480), Image.Resampling.NEAREST).save(
            OUT / 'comparisons' / (kind + '_contact_sheet_8x.png'))


def main():
    if not MASTER.is_file():
        raise FileNotFoundError(f'Preserve Image Generation output first: {MASTER}')
    original = Image.open(MASTER).convert('RGBA')
    source_hash = sha(MASTER)
    reference_hashes = {p: sha(ROOT / p) for p in REFERENCES}
    (OUT / 'comparisons').mkdir(parents=True, exist_ok=True)
    GFX.mkdir(parents=True, exist_ok=True)
    poses, records = {}, []
    for name in CROPS:
        poses[name], record = import_pose(name, original)
        records.append(record)
    palettes = source_palettes([poses['combat_front'], poses['combat_back']])
    battle = [emit_battle('enemy_front', poses['combat_front'], [1, 5], palettes),
              emit_battle('ally_front', poses['combat_front'], [0, 6], palettes),
              emit_battle('ally_back', poses['combat_back'], [0, 6], palettes)]
    world = emit_world(poses, palettes)
    # Sidebar is an ordinary source crop, using the current shared OBJ colors.
    head = Image.fromarray(poses['combat_front']).crop((16, 4, 40, 28)).resize((8, 8), Image.Resampling.NEAREST)
    head_rgba = np.asarray(head)
    head_rgb = head_rgba[:, :, :3].astype('int32') >> 3
    head_index = (((head_rgb[:, :, None] - np.asarray(WORLD_PALETTES[2][1:])) ** 2).sum(3).argmin(2) + 1).astype('uint8')
    head_index[head_rgba[:, :, 3] == 0] = 0
    (GFX / 'head_8x8.2bpp').write_bytes(encode(head_index, False))
    head.save(OUT / 'sprites/sidebar_head_source.png')
    contact_sheet(poses)
    asm = ['SECTION "Missing Earth Elemental v0212", ROMX\n']
    for name, label in [('enemy_front', 'Enemy'), ('ally_front', 'AllyFront'), ('ally_back', 'AllyBack')]:
        for suffix, filename in [('Tiles', 'frames.2bpp'), ('Pals', 'palettes.bin'), ('Attrs', 'attrs.bin')]:
            asm.append(f'PeonEarthElemental{label}{suffix}V0212:\n\tINCBIN "gfx/earth_elemental_v0212/{name}/{filename}"\n')
    asm.extend(['PeonEarthElementalEnemyMetaV0212:\n',
                '\tINCBIN "gfx/earth_elemental_v0212/enemy_front/palettes.bin"\n',
                '\tINCBIN "gfx/earth_elemental_v0212/enemy_front/attrs.bin"\n',
                'PeonEarthElementalWorldV0212:\n\tINCBIN "gfx/earth_elemental_v0212/overworld.bin"\n',
                'PeonEarthElementalWorldPalV0212:\n\tINCBIN "gfx/earth_elemental_v0212/world_palette.bin"\n'])
    (GFX / 'data.asm').write_text(''.join(asm))
    report = {'schema': 'missing-earth-elemental-generated-raster-import-v0212',
              'source_of_truth': 'New missing-monster Image Generation master; supplied user character artwork retained',
              'generated_missing_art': True, 'provided_by_user': False,
              'source_master': relative(MASTER), 'source_sha256': source_hash,
              'style_reference_hashes': reference_hashes,
              'source_originals_changed': False, 'native_grid_recovered': False,
              'lossless_native_extraction': False, 'lossy_nearest_neighbor_conversion': True,
              'manual_pixel_redraw': False, 'new_animation_anatomy': False,
              'ROM_integration_verified': False, 'sprites': records,
              'battle': battle, 'world': world}
    (OUT / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    (OUT / 'README.md').write_text(
        '# Missing Earth Elemental — v0.2.12\n\n'
        'This monster is newly generated under the user’s authorization to complete missing PNGs. '
        'It was absent from the supplied character packs. Original boar, scorpid, imp and approved '
        'Shaman artwork supplied style references; none were changed. The generation master and '
        'prompt are preserved in `originals/`. This is a lossy raster conversion, not recovery of '
        'an exact generated native grid or an extraction of user-provided elemental pixels.\n\n'
        'The six complete source silhouettes are cropped at the coordinates in `manifest.json`. '
        'Alpha >=128 becomes255; lower alpha becomes0. Nearest-neighbor aspect fitting centers '
        'each pose inside a one-pixel transparent border: four16×16 world directions,56×56 '
        'combat front and48×48 true combat rear. Separate hardware packets use RGB555 source '
        'medoids, three opaque colors per8×8 BG tile and two palette families. World OBJ uses '
        'exactly three opaque colors. Three frame slots repeat each canonical pose; there are '
        'no manually drawn circles, polygons, extra silhouettes or invented attack poses.\n\n'
        'Hardware previews are authored-asset projections, not running-ROM evidence. Engine '
        'bindings and build integration are separate. Reproduce with '
        '`python3 tools/import_peon_earth_elemental_v0212.py`.\n')
    assert sha(MASTER) == source_hash
    assert all(sha(ROOT / path) == value for path, value in reference_hashes.items())
    print(json.dumps({'native_sprites': len(records), 'battle_packets': len(battle),
                      'output': relative(OUT), 'gfx': relative(GFX)}, indent=2))


if __name__ == '__main__':
    main()
