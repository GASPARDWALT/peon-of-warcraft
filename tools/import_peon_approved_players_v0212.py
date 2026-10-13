#!/usr/bin/env python3
"""Convert approved design rasters into separate native hero assets.

This is a lossy raster import, not recovery of an enlarged native pixel grid.
Original PNGs are only read. No replacement anatomy or equipment is authored.
"""
from pathlib import Path
import hashlib
import json
import sys
from itertools import combinations

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_peon_user_battle_v0211 import encode
from build_peon_user_world_v0211 import (
    WORLD_PALETTES, ROLE_PALETTE, encode_world_frame, index_world_rgba,
    hardware_rgba,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'references/generated/peon_sprite_redesign_v030/originals'
OUT = ROOT / 'references/generated/approved_player_import_v0212'
GFX = ROOT / 'gfx/approved_player_v0212'
ALPHA_THRESHOLD = 128
BORDER = 1
ROLES = ('shaman', 'base', 'warrior', 'warlock')
DIRECTIONS = ('front', 'back', 'left', 'right')
PAPER = (31, 29, 23)
# Palette 6 is also used by the legacy Warlock Imp. Keep its exact RGB555
# colors until the runtime allocates that pet independently.
WARLOCK_PET_PALETTE = [(31, 31, 31), (31, 20, 5), (26, 5, 4), (4, 2, 3)]
SOURCES = {
    'base': ('peon_base_design_reference.png',
             'ab2dde71d2a12778be265e55169eb9a1692a627a8771abcc7c7aa4b2da475ab1'),
    'shaman': ('peon_shaman_totemic_design_reference.png',
               '740053366b7da897d7daef3744616e7eb060937f2f6ded06003ff31702fa6c27'),
    'warrior': ('peon_warrior_design_reference.png',
                'bf8c362a5acfb51390378c2256dc3e58285a54ca02286112ddc9164406c32ffc'),
    'warlock': ('peon_warlock_design_reference.png',
                'af0513b60380c38540d4fb95b398f60d4fcd2becf087bd4c8ab3d41da63f3622'),
}
# Bounds are half-open original-source coordinates, measured from each
# complete source silhouette at alpha >=128. Four top-row directions follow
# the approved sheet's front/back/left/right order; bottom row is front/rear.
CROPS = {
    'base': {
        'world_front': [128, 60, 383, 356],
        'world_back': [467, 60, 721, 355],
        'world_left': [866, 60, 1020, 362],
        'world_right': [1237, 60, 1391, 362],
        'combat_front': [149, 373, 719, 974],
        'combat_back': [846, 392, 1374, 982],
    },
    'shaman': {
        'world_front': [35, 44, 374, 368],
        'world_back': [426, 43, 765, 368],
        'world_left': [830, 48, 1111, 370],
        'world_right': [1175, 48, 1458, 375],
        'combat_front': [56, 369, 773, 973],
        'combat_back': [831, 388, 1492, 981],
    },
    'warrior': {
        'world_front': [57, 61, 380, 351],
        'world_back': [472, 62, 794, 351],
        'world_left': [868, 63, 1118, 357],
        'world_right': [1184, 63, 1404, 357],
        'combat_front': [45, 376, 735, 956],
        'combat_back': [845, 396, 1493, 956],
    },
    'warlock': {
        'world_front': [121, 68, 375, 349],
        'world_back': [474, 68, 718, 349],
        'world_left': [875, 69, 1053, 358],
        'world_right': [1196, 68, 1389, 359],
        'combat_front': [157, 379, 746, 969],
        'combat_back': [875, 400, 1413, 969],
    },
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def relative(path):
    return str(path.relative_to(ROOT))


def palette_errors(rgba, palettes, color_zero_is_opaque=False):
    """Fit colors while giving existing high-contrast source marks more weight.

    Weights change palette selection only. They never draw or move pixels.
    """
    rgb = rgba[:, :, :3].astype(np.int32) >> 3
    visible = rgba[:, :, 3] > 0
    importance = np.ones(visible.shape, dtype=float)
    for dy, dx in ((0, 1), (1, 0)):
        left = rgb[:rgb.shape[0] - dy or None, :rgb.shape[1] - dx or None]
        right = rgb[dy:, dx:]
        both = visible[:visible.shape[0] - dy or None, :visible.shape[1] - dx or None] & visible[dy:, dx:]
        gradient = np.sqrt(((left - right) ** 2).sum(2))
        weight = np.minimum(3.0, gradient / 10.0) * both
        importance[:importance.shape[0] - dy or None, :importance.shape[1] - dx or None] += weight
        importance[dy:, dx:] += weight
    result = []
    for y in range(0, rgba.shape[0], 8):
        for x in range(0, rgba.shape[1], 8):
            mask = visible[y:y + 8, x:x + 8]
            colors = rgb[y:y + 8, x:x + 8][mask]
            weights = importance[y:y + 8, x:x + 8][mask]
            if color_zero_is_opaque and not mask.all():
                # BG index0 is a material color only in completely filled
                # tiles. Alpha holes must retain the battle-field paper.
                result.append([float('inf')] * len(palettes))
                continue
            result.append([float((((colors[:, None, :] - np.asarray(p if color_zero_is_opaque else p[1:])) ** 2)
                                   .sum(2).min(1) * weights).sum())
                           if len(colors) else 0.0 for p in palettes])
    return np.asarray(result)


def adaptive_palettes(rgba, count, fixed=None, allow_opaque_secondary=False):
    colors, counts = np.unique(rgba[:, :, :3][rgba[:, :, 3] > 0] >> 3,
                               axis=0, return_counts=True)
    dark = tuple(map(int, colors[colors.sum(1).argmin()]))
    useful = colors.sum(1) > max(10, sum(dark) + 6)
    values, weights = colors[useful].astype(float), counts[useful]
    centers = [values[weights.argmax()]]
    while len(centers) < min(12, len(values)):
        distances = ((values[:, None, :] - np.asarray(centers)[None, :, :]) ** 2).sum(2).min(1)
        centers.append(values[(distances * np.sqrt(weights)).argmax()])
    centers = np.asarray(centers)
    for _ in range(20):
        groups = ((values[:, None, :] - centers[None, :, :]) ** 2).sum(2).argmin(1)
        for i in range(len(centers)):
            mask = groups == i
            if mask.any():
                centers[i] = np.average(values[mask], weights=weights[mask], axis=0)
    medoids = list(dict.fromkeys(tuple(map(int, values[((values - center) ** 2).sum(1).argmin()]))
                                for center in centers))
    options = [[(31, 31, 31), a, b, dark] for a, b in combinations(medoids, 2)]
    errors = palette_errors(rgba, options)
    if fixed:
        fixed_errors = palette_errors(rgba, [fixed])[:, 0]
        first = int(np.minimum(errors, fixed_errors[:, None]).sum(0).argmin())
        return [options[first], fixed], palette_errors(rgba, [options[first], fixed]).argmin(1)
    if count == 2:
        # Select both palettes together, rather than freezing a first greedy
        # palette that can prevent the second from retaining source detail.
        pair = min(combinations(range(len(options)), 2),
                   key=lambda p: float(np.minimum(errors[:, p[0]], errors[:, p[1]]).sum()))
        selected = list(pair)
    else:
        selected = [int(errors.sum(0).argmin())]
        while len(selected) < count:
            scores = np.minimum(errors, errors[:, selected].min(1)[:, None]).sum(0)
            scores[selected] = np.inf
            selected.append(int(scores.argmin()))
        for _ in range(4):
            for slot in range(count):
                other = selected[:slot] + selected[slot + 1:]
                scores = np.minimum(errors, errors[:, other].min(1)[:, None]).sum(0)
                scores[other] = np.inf
                selected[slot] = int(scores.argmin())
    palettes = [options[i] for i in selected]
    choices = errors[:, selected].argmin(1)
    if allow_opaque_secondary and count == 2:
        # Keep the two paper palettes unless replacing only the secondary
        # improves the complete actor. Primary0 also colors blank field cells.
        opaque_options = [[dark, a, b, c] for a, b, c in combinations(medoids, 3)]
        if opaque_options:
            opaque_errors = palette_errors(rgba, opaque_options, color_zero_is_opaque=True)
            primary, secondary = min(((a, b) for a in range(len(options))
                                     for b in range(len(opaque_options))),
                                    key=lambda pair: float(np.minimum(errors[:, pair[0]],
                                                                     opaque_errors[:, pair[1]]).sum()))
            candidate_errors = np.column_stack((errors[:, primary], opaque_errors[:, secondary]))
            if candidate_errors.min(1).sum() < errors[:, selected].min(1).sum():
                return [options[primary], opaque_options[secondary]], candidate_errors.argmin(1)
    return palettes, choices


def import_pose(role, pose, original, source_path):
    bounds = CROPS[role][pose]
    crop = np.asarray(original.crop(bounds)).copy()
    alpha = crop[:, :, 3].copy()
    visible = alpha >= ALPHA_THRESHOLD
    crop[:, :, 3] = np.where(visible, 255, 0)
    crop[~visible] = 0
    size = 16 if pose.startswith('world_') else 56 if pose.endswith('front') else 48
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    scale = min((size - 2 * BORDER) / width, (size - 2 * BORDER) / height)
    fitted = (max(1, min(size - 2 * BORDER, round(width * scale))),
              max(1, min(size - 2 * BORDER, round(height * scale))))
    offset = ((size - fitted[0]) // 2, (size - fitted[1]) // 2)
    reduced = Image.fromarray(crop).resize(fitted, Image.Resampling.NEAREST)
    native = Image.new('RGBA', (size, size))
    native.paste(reduced, offset)
    target = OUT / 'sprites' / role / f'{pose}.png'
    target.parent.mkdir(parents=True, exist_ok=True)
    native.save(target)
    comparisons = OUT / 'comparisons' / role
    comparisons.mkdir(parents=True, exist_ok=True)
    # These are crop/nearest-neighbor previews, never alternative artwork.
    original.crop(bounds).save(comparisons / f'{pose}_source_crop.png')
    native.resize((size * 8, size * 8), Image.Resampling.NEAREST).save(
        comparisons / f'{pose}_native_8x.png')
    rgba = np.asarray(native)
    mask = rgba[:, :, 3] != 0
    return native, {
        'role': role, 'pose': pose, 'source': relative(source_path),
        'source_sha256': sha(source_path), 'source_canvas': list(original.size),
        'crop_bounds_exclusive': bounds, 'crop_dimensions': [width, height],
        'crop_visible_pixels_at_threshold': int(np.count_nonzero(visible)),
        'crop_intermediate_alpha_pixels': int(np.count_nonzero((alpha > 0) & (alpha < 255))),
        'alpha_conversion': {'threshold': ALPHA_THRESHOLD, 'comparison': '>=',
                             'visible_alpha': 255, 'background_alpha': 0,
                             'transparent_rgb': [0, 0, 0]},
        'resampling': 'Pillow nearest-neighbor; no pixel drawing, filtering, or dithering',
        'aspect_fit': {'nominal_scale': scale, 'fitted_dimensions': list(fitted),
                       'offset': list(offset), 'transparent_border_minimum': BORDER,
                       'integer_rounding': 'Nearest integer dimensions; whole source crop retained'},
        'native_dimensions': [size, size], 'native_path': relative(target),
        'native_sha256': sha(target), 'native_visible_pixels': int(np.count_nonzero(mask)),
        'native_opaque_rgb_colors': len(np.unique(rgba[:, :, :3][mask], axis=0)),
        'native_binary_alpha': bool(set(np.unique(rgba[:, :, 3])) <= {0, 255}),
        'source_geometry_unchanged': False, 'source_color_quantized_in_native_png': False,
        'exact_native_grid_recovery': False, 'replacement_anatomy_authored': False,
    }


def emit_battle(role, view, native):
    rgba = np.asarray(native)
    slots = [2, 4, 6, 7] if view == 'profile' else [0, 6]
    fixed = WARLOCK_PET_PALETTE if role == 'warlock' and view != 'profile' else None
    palettes, choices = adaptive_palettes(rgba, len(slots), fixed=fixed,
                                         allow_opaque_secondary=view != 'profile' and fixed is None)
    opaque_zero = [tuple(palette[0]) != (31, 31, 31) for palette in palettes]
    paper = PAPER if view == 'profile' else (31, 31, 31)
    palettes = [[tuple(palette[0]) if opaque_zero[number] else tuple(paper),
                 *(tuple(int(channel) for channel in color)
                                for color in palette[1:])] for number, palette in enumerate(palettes)]
    height, width = rgba.shape[:2]
    indexed = np.zeros((height, width), dtype=np.uint8)
    preview = np.zeros_like(rgba)
    for number, choice in enumerate(choices):
        y, x = (number // (width // 8)) * 8, (number % (width // 8)) * 8
        region = rgba[y:y + 8, x:x + 8]
        palette = np.asarray(palettes[int(choice)], dtype=np.int32)
        source = region[:, :, :3].astype(np.int32) >> 3
        if opaque_zero[int(choice)]:
            assert np.all(region[:, :, 3] == 255), 'Opaque BG index0 palette assigned to an alpha-edge tile'
            indices = ((source[:, :, None, :] - palette[None, None, :, :]) ** 2).sum(3).argmin(2)
        else:
            indices = ((source[:, :, None, :] - palette[None, None, 1:, :]) ** 2).sum(3).argmin(2) + 1
        indices[region[:, :, 3] == 0] = 0
        indexed[y:y + 8, x:x + 8] = indices
        expanded = (palette[indices] << 3) | (palette[indices] >> 2)
        preview[y:y + 8, x:x + 8, :3] = expanded
        preview[y:y + 8, x:x + 8, 3] = region[:, :, 3]
    column_major = view != 'profile'
    frame = encode(indexed, column_major)
    folder = GFX / role / view
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'frames.2bpp').write_bytes(frame * 3)
    (folder / 'attrs.bin').write_bytes(bytes(slots[int(choice)] for choice in choices))
    palraw = b''.join(int(r | (g << 5) | (b << 10)).to_bytes(2, 'little')
                      for palette in palettes for r, g, b in palette)
    (folder / 'palettes.bin').write_bytes(palraw)
    (folder / 'palettes.pal').write_text(''.join('\tRGB ' + ', '.join(map(str, color)) + '\n'
                                               for palette in palettes for color in palette))
    preview_path = OUT / 'comparisons' / role / f'{view}_hardware_rgba.png'
    Image.fromarray(preview).save(preview_path)
    Image.fromarray(preview).resize((width * 8, height * 8), Image.Resampling.NEAREST).save(
        OUT / 'comparisons' / role / f'{view}_hardware_8x.png')
    assert np.array_equal(preview[:, :, 3], rgba[:, :, 3])
    assert len(frame) == (width // 8) * (height // 8) * 16
    visible = rgba[:, :, 3] > 0
    source_rgb555 = rgba[:, :, :3].astype(np.int32) >> 3
    native_rgb555 = preview[:, :, :3].astype(np.int32) >> 3
    selected_errors = np.column_stack([palette_errors(rgba, [palette], color_zero_is_opaque=opaque_zero[number])[:, 0]
                                       for number, palette in enumerate(palettes)])
    return {
        'role': role, 'view': view, 'dimensions': [width, height], 'slots': slots,
        'palettes_rgb555': palettes, 'tile_order': 'column-major' if column_major else 'row-major',
        'attribute_order': 'row-major', 'frames': 3, 'unique_source_poses': 1,
        'frame_slots_identical': True, 'bytes_per_frame': len(frame),
        'frames_path': relative(folder / 'frames.2bpp'), 'frames_sha256': sha(folder / 'frames.2bpp'),
        'native_alpha_preserved': True,
        'palette_color_zero_is_opaque': opaque_zero,
        'opaque_color_zero_tile_indices': [number for number, choice in enumerate(choices) if opaque_zero[int(choice)]],
        'alpha_validation_uses_source_mask': True,
        'rgb555_rmse': round(float(np.sqrt(((source_rgb555[visible] - native_rgb555[visible]) ** 2).mean())), 6),
        'weighted_palette_error': float(selected_errors[np.arange(len(choices)), choices].sum()),
        'hardware_opaque_colors': len(np.unique(preview[:, :, :3][preview[:, :, 3] > 0], axis=0)),
        'warlock_legacy_pet_palette_preserved': bool(fixed),
        'method': '12 adaptive source RGB555 medoids; joint palette selection with existing source-contrast weights; one palette per8x8 tile; profile and Warlock retain paper palettes, other battle views permit opaque BG6 index0 only in completely filled tiles when total fit improves',
    }


def emit_contact_sheets(native_by_role):
    width, height = 208, 236
    sheets = {kind: Image.new('RGBA', (width, height)) for kind in ('native', 'hardware')}
    poses = [(f'world_{d}', 20 * i, 20) for i, d in enumerate(DIRECTIONS)]
    poses += [('combat_front', 92, 0), ('combat_back', 160, 4)]
    for row, role in enumerate(('base', 'shaman', 'warrior', 'warlock')):
        for pose, x, y in poses:
            sheets['native'].paste(native_by_role[role][pose], (x, 60 * row + y))
            preview_name = (pose if pose.startswith('world_') else pose.removeprefix('combat_')) + '_hardware_rgba.png'
            hardware = Image.open(OUT / 'comparisons' / role / preview_name).convert('RGBA')
            sheets['hardware'].paste(hardware, (x, 60 * row + y))
    paths = {}
    for kind, sheet in sheets.items():
        path = OUT / 'comparisons' / f'{kind}_contact_sheet.png'
        sheet.save(path)
        sheet.resize((width * 4, height * 4), Image.Resampling.NEAREST).save(
            OUT / 'comparisons' / f'{kind}_contact_sheet_4x.png')
        paths[kind] = relative(path)
    return {'dimensions': [width, height], 'rows': ['base', 'shaman', 'warrior', 'warlock'],
            'poses': [{'pose': pose, 'x': x, 'row_y_offset': y} for pose, x, y in poses],
            'paths': paths}


def main():
    records, hardware_records, world_records = [], [], []
    native_by_role = {}
    original_hashes = {}
    for role in ROLES:
        filename, expected = SOURCES[role]
        source_path = SOURCE / filename
        if sha(source_path) != expected:
            raise ValueError(f'Approved master hash changed: {source_path}')
        original_hashes[relative(source_path)] = expected
        original = Image.open(source_path).convert('RGBA')
        native_by_role[role] = {}
        # Save and inspect the critical Shaman rear first.
        for pose in ('combat_back', 'combat_front', *('world_' + d for d in DIRECTIONS)):
            native, record = import_pose(role, pose, original, source_path)
            native_by_role[role][pose] = native
            records.append(record)
        for view in ('back', 'front', 'profile'):
            pose = 'combat_front' if view == 'profile' else 'combat_' + view
            hardware_records.append(emit_battle(role, view, native_by_role[role][pose]))
        folder = GFX / role
        packet = b''
        for direction in DIRECTIONS:
            native = native_by_role[role]['world_' + direction]
            indexed = index_world_rgba(native, ROLE_PALETTE[role])
            packet += encode_world_frame(indexed)
            preview = hardware_rgba(indexed, ROLE_PALETTE[role])
            preview.save(OUT / 'comparisons' / role / f'world_{direction}_hardware_rgba.png')
            preview.resize((128, 128), Image.Resampling.NEAREST).save(
                OUT / 'comparisons' / role / f'world_{direction}_hardware_8x.png')
        (folder / 'overworld.bin').write_bytes(packet * 3)
        world_palette = WORLD_PALETTES[ROLE_PALETTE[role]]
        (folder / 'world_preview.pal').write_text(
            '\tRGB ' + ', '.join(str(channel) for color in world_palette for channel in color) + '\n')
        world_records.append({'role': role, 'directions': list(DIRECTIONS),
                              'palette_index': ROLE_PALETTE[role],
                              'palette_rgb555': WORLD_PALETTES[ROLE_PALETTE[role]],
                              'path': relative(folder / 'overworld.bin'),
                              'sha256': sha(folder / 'overworld.bin'),
                              'palette_path': relative(folder / 'world_preview.pal'),
                              'bytes': len(packet) * 3, 'unique_source_phases': 1,
                              'phase_slots_identical': True,
                              'global_obj_palette_changed': False})
    assert all(sha(ROOT / path) == expected for path, expected in original_hashes.items())
    contact_sheets = emit_contact_sheets(native_by_role)
    manifest = {
        'schema': 'approved-hero-raster-import-v0212',
        'source_of_truth': 'Four approved v030 original design rasters; native incoming atlas bytes still unavailable',
        'source_originals_changed': False, 'source_hashes': original_hashes,
        'lossless_native_extraction': False, 'native_grid_recovered': False,
        'direct_raster_conversion': True, 'replacement_art_generated': False,
        'resizing_and_alpha_conversion_explicit': True, 'rom_integrated': False,
        'static_animation_policy': 'One supplied pose per direction/front/rear; three identical binary slots, no invented gait/attack anatomy',
        'future_source_priority': 'If the user native PNG atlas becomes available, import its native cells directly in preference to this lossy conversion',
        'sprites': records, 'battle': hardware_records, 'world': world_records,
        'contact_sheets': contact_sheets,
    }
    write_json(OUT / 'manifest.json', manifest)
    (OUT / 'README.md').write_text(
        '# Approved hero raster import — v0.2.12\n\n'
        'These 24 native PNGs are direct conversions of the four approved design '
        'masters in `references/generated/peon_sprite_redesign_v030/originals/`. '
        'The original source PNGs remain unchanged. The source rasters are not '
        'exact enlarged native pixel grids: every crop, original SHA256, alpha '
        'threshold, nearest-neighbor size and centering offset is recorded in '
        '`manifest.json`. Alpha >=128 becomes 255; lower alpha becomes 0. '
        'Whole source poses and equipment fit inside a one-pixel transparent border.\n\n'
        'No replacement anatomy, ASCII sprite rows, polygons, new equipment or '
        'attack poses are authored. Three engine frame slots repeat the single '
        'source pose. World directions are imported independently. The source '
        'native PNGs retain their sampled RGB colors. Separate GBC files reduce '
        'colors to the allocated per-tile palettes, so hardware previews show '
        'the actual remaining color loss. Warlock palette6 remains compatible '
        'with the legacy Imp. Other battle views may use all four BG6 colors '
        'only inside completely opaque 8×8 tiles when the complete actor fit '
        'improves; BG0 and every alpha-edge tile retain the white battlefield. '
        'Source alpha, rather than color index0, defines these previews and '
        'validation masks. Global world palettes are not modified here.\n\n'
        'Reproduce with `python tools/import_peon_approved_players_v0212.py`. '
        'This importer does not modify engine bindings or build a ROM. A future '
        'available user native atlas takes priority over this lossy raster conversion.\n')
    print(json.dumps({'native_sprites': len(records), 'source_originals_unchanged': True,
                      'shaman_rear': records[0], 'output': relative(OUT)}, indent=2))


if __name__ == '__main__':
    main()
