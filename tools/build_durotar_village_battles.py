#!/usr/bin/env python3
"""Compile six distinct NPC battle/action sprites and native speaker portraits.

These are presentation assets. Friendly NPC actions do not add fights or loot.
The generated concept atlas is committed; all exports are reproducible offline.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v021/village_battles'
PORTRAITS = ROOT / 'gfx/peon_portraits'
SOURCE = OUT / 'concept_village_battles.png'
NAMES = ('troll_guard', 'troll_fisher', 'troll_caster',
         'orc_guard', 'orc_vendor', 'orc_questgiver')
TROLL = ((255, 255, 255), (239, 222, 181), (82, 165, 189), (16, 33, 57))
ORC = ((255, 255, 255), (148, 90, 49), (123, 181, 66), (8, 8, 8))
GRAY = [255, 255, 255, 170, 170, 170, 85, 85, 85, 0, 0, 0] + [0] * 756
HEAD_ROIS = ((.04, .00, .83, .72), (.03, .00, .82, .66),
             (.06, .00, .83, .70), (.03, .00, .76, .62),
             (.12, .00, .78, .58), (.07, .00, .81, .57))


def row_bounds(source):
    # Locate row divisions from the front column, avoiding attack/spell particles.
    foreground = np.array(source.getchannel('A'))[:, :source.width // 4] >= 180
    rows = np.any(foreground, axis=1)
    spans, start = [], None
    for y, full in enumerate(rows):
        if full and start is None:
            start = y
        elif not full and start is not None:
            spans.append((start, y)); start = None
    if start is not None:
        spans.append((start, source.height))
    assert len(spans) == 6, spans
    boundaries = [0] + [(spans[i][1] + spans[i + 1][0]) // 2 for i in range(5)]
    boundaries.append(source.height)
    return list(zip(boundaries, boundaries[1:]))


def extract(source, row, column):
    left = column * source.width // 4
    right = (column + 1) * source.width // 4
    cell = source.crop((left, row[0], right, row[1]))
    bbox = cell.getchannel('A').point(lambda n: 255 if n >= 180 else 0).getbbox()
    assert bbox, (row, column)
    return cell.crop(bbox), {'atlas_cell': [left, row[0], right, row[1]],
                             'opaque_bbox_in_cell': list(bbox)}


def fit(source, size, margin=2):
    source = source.copy()
    source.thumbnail((size - margin * 2, size - margin), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (size, size))
    canvas.paste(source, ((size - source.width) // 2, size - source.height))
    return canvas


def indexed(source, palette, white=True):
    pixels = np.array(source.convert('RGBA'))
    candidates = palette if white else palette[1:]
    distances = ((pixels[:, :, None, :3].astype(float) - np.array(candidates)) ** 2).sum(-1)
    values = (distances.argmin(-1) + (0 if white else 1)).astype('uint8')
    alpha = np.where(pixels[:, :, 3] >= 180, 255, 0).astype('uint8')
    values[alpha == 0] = 0
    im = Image.fromarray(values, 'P')
    im.putpalette([n for color in palette for n in color] + [0] * 756)
    return im, alpha


def rgba(frame, alpha):
    return Image.fromarray(np.dstack((np.array(frame.convert('RGB')), alpha)), 'RGBA')


def portrait_front(source, roi, palette):
    bounds = [round(roi[0] * source.width), round(roi[1] * source.height),
              round(roi[2] * source.width), round(roi[3] * source.height)]
    crop = source.crop(bounds)
    native, alpha = indexed(fit(crop, 24, 1), palette, white=False)
    return native, alpha, crop, bounds


def portrait_features(name, frame, alpha):
    """Keep two dark eyes and two bright tusks readable after native reduction."""
    pixels = np.array(frame)
    # The largest skin rows are the front-facing face, above hands/shoulders.
    skin = pixels == 2
    counts = skin.sum(1)
    eligible = [(int(counts[y]), y) for y in range(4, 19)]
    _, center_y = max(eligible)
    xs = np.where(skin[center_y])[0]
    if len(xs) < 4:
        return frame, alpha
    center_x = int(round((int(xs[0]) + int(xs[-1])) / 2))
    # Landmark positions adapt to each crop instead of imposing a shared head.
    eye_y = max(2, center_y - 1)
    mouth_y = min(22, center_y + 3)
    width = max(2, min(4, (int(xs[-1]) - int(xs[0])) // 3))
    dark = ((center_x - width, eye_y), (center_x + width, eye_y))
    ivory = ((center_x - width, mouth_y), (center_x + width, mouth_y))
    for x, y in dark:
        if 0 <= x < 24 and alpha[y, x] == 255:
            pixels[y, x] = 3
    # Orc portraits share brown/green/black; white tusks become index-zero white
    # while their alpha stays opaque, unlike the transparent surrounding pixels.
    tusk_color = 1 if name.startswith('troll') else 0
    for x, y in ivory:
        if 0 <= x < 24 and alpha[y, x] == 255:
            pixels[y, x] = tusk_color
    fixed = Image.fromarray(pixels, 'P')
    fixed.putpalette(frame.getpalette())
    return fixed, alpha


def two_bpp(frame):
    values = np.array(frame)
    out = bytearray()
    for tile_y in range(frame.height // 8):
        for tile_x in range(frame.width // 8):
            tile = values[tile_y * 8:(tile_y + 1) * 8,
                          tile_x * 8:(tile_x + 1) * 8]
            for row in tile:
                lo = hi = 0
                for value in row:
                    lo = (lo << 1) | (int(value) & 1)
                    hi = (hi << 1) | ((int(value) >> 1) & 1)
                out.extend((lo, hi))
    return bytes(out)


def animate(dest, frames):
    # The same front/prepare/action/return sequence applies to friendly gestures.
    frames[0].save(dest / 'animation.png', save_all=True,
                   append_images=frames[1:], duration=[420, 200, 260, 180],
                   loop=0, disposal=1, blend=0)
    sheet = Image.new('RGBA', (56 * 4, 56))
    preview = []
    for i, frame in enumerate(frames):
        sheet.paste(frame, (56 * i, 0))
        canvas = Image.new('RGBA', frame.size, (41, 33, 39, 255))
        canvas.alpha_composite(frame)
        preview.append(canvas.resize((280, 280), Image.Resampling.NEAREST).convert('RGB'))
    sheet.save(dest / 'sheet.png')
    preview[0].save(dest / 'preview.gif', save_all=True,
                    append_images=preview[1:], duration=[420, 200, 260, 180], loop=0)


def main():
    source = Image.open(SOURCE).convert('RGBA')
    rows = row_bounds(source)
    PORTRAITS.mkdir(parents=True, exist_ok=True)
    crops, assets = {}, []
    montage = Image.new('RGB', (880, len(NAMES) * 320), (41, 33, 39))
    draw = ImageDraw.Draw(montage)
    for row, name in enumerate(NAMES):
        palette = TROLL if row < 3 else ORC
        dest = OUT / name; dest.mkdir(parents=True, exist_ok=True)
        cells, infos = zip(*(extract(source, rows[row], col) for col in range(4)))
        crops[name] = {'cells': list(infos)}
        converted = [indexed(fit(cell, 48 if col == 1 else 56), palette)
                     for col, cell in enumerate(cells)]
        exported = [rgba(frame, alpha) for frame, alpha in converted]
        for label, frame in zip(('front', 'back', 'prepare', 'attack'), exported):
            frame.save(dest / f'{label}.png')
        frames = [exported[0], exported[2], exported[3], exported[0].copy()]
        for label, frame in zip(('idle', 'prepare', 'attack', 'return'), frames):
            frame.save(dest / f'{label}.png')
        animate(dest, frames)
        # Native BG battle inputs and source masks make white highlights explicit.
        battle_sheet = Image.new('P', (56, 56 * 4)); battle_sheet.putpalette(GRAY)
        for i, (frame, _) in enumerate([converted[0], converted[2],
                                       converted[3], converted[0]]):
            battle_sheet.paste(frame, (0, 56 * i))
        battle_sheet.save(dest / 'battle_engine_sheet.png')
        (dest / 'battle_engine_sheet.2bpp').write_bytes(two_bpp(battle_sheet))
        Image.fromarray(converted[0][1]).save(dest / 'front_alpha_mask.png')
        Image.fromarray(converted[1][1]).save(dest / 'back_alpha_mask.png')
        back = converted[1][0].copy(); back.putpalette(GRAY)
        back.save(dest / 'back_engine.png')
        (dest / 'back_engine.2bpp').write_bytes(two_bpp(back))
        (dest / 'battle_palette.pal').write_text(''.join(
            '\tRGB ' + ', '.join(f'{v >> 3:02d}' for v in color) + '\n'
            for color in palette))
        # Speaker portrait renderer expects white/primary/skin/black BG palette.
        portrait_palette = (palette[0], palette[1], palette[2], (0, 0, 0))
        portrait, alpha, head_crop, head_bounds = portrait_front(
            cells[0], HEAD_ROIS[row], portrait_palette)
        portrait, alpha = portrait_features(name, portrait, alpha)
        head_crop.save(dest / 'portrait_source_crop.png')
        rgba(portrait, alpha).save(dest / 'portrait.png')
        crops[name]['head_roi_in_front_crop'] = head_bounds
        portrait_gray = portrait.copy(); portrait_gray.putpalette(GRAY)
        portrait_gray.save(PORTRAITS / f'{name}.png')
        (PORTRAITS / f'{name}.2bpp').write_bytes(two_bpp(portrait_gray))
        (PORTRAITS / f'{name}.pal').write_text(''.join(
            '\tRGB ' + ', '.join(f'{v >> 3:02d}' for v in color) + '\n'
            for color in portrait_palette))
        draw.text((10, row * 320 + 5), name.replace('_', ' ').upper(), fill=(239, 222, 181))
        for col, frame in enumerate((exported[0], exported[1], exported[2], exported[3])):
            enlarged = frame.resize((168, 168), Image.Resampling.NEAREST)
            montage.paste(enlarged, (10 + 174 * col, row * 320 + 22), enlarged)
        face = rgba(portrait, alpha).resize((144, 144), Image.Resampling.NEAREST)
        montage.paste(face, (716, row * 320 + 28), face)
        assets.append({'name': name, 'front_size': [56, 56], 'back_size': [48, 48],
                       'animation_poses': ['idle', 'prepare', 'attack', 'return'],
                       'portrait_size': [24, 24], 'portrait_tiles': 9,
                       'portrait_2bpp': str((PORTRAITS / f'{name}.2bpp').relative_to(ROOT)),
                       'portrait_palette': str((PORTRAITS / f'{name}.pal').relative_to(ROOT)),
                       'presentation_only': True})
    montage.save(OUT / 'native_battle_portrait_preview.png')
    (OUT / 'cell_crop_manifest.json').write_text(json.dumps(crops, indent=2) + '\n')
    manifest = {'source': str(SOURCE.relative_to(ROOT)),
                'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                'native_opaque_colors_max': 4,
                'white_index': 0,
                'white_highlights_preserve_alpha': True,
                'friendly_npc_combat_paths_added': False,
                'assets': assets}
    (OUT / 'asset_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (OUT / 'README.md').write_text(
        '# Village battle silhouettes and speaker portraits\n\n'
        'Six distinct roles with native 56×56 front/action sprites, 48×48 backs, '
        'and 24×24 dialogue portraits. Public sprite and portrait PNGs are transparent. '
        'White highlights inside a sprite remain opaque through explicit alpha masks. '
        'The reference atlas is larger than the actual ROM graphics.\n\n'
        '![Native battle and portrait previews](native_battle_portrait_preview.png)\n\n'
        + '\n'.join(f'**{name.replace("_", " ")}** — ![{name}]({name}/preview.gif)\n'
                     for name in NAMES)
        + '\nThese are prepared assets: vendor and questgiver animations are friendly '
        'gestures. This asset pass adds no new NPC fights. Speaker portraits are '
        'supplied separately to the ROM dialogue renderer.\n\n'
        'Regenerate with `python3 tools/build_durotar_village_battles.py`.\n')
    print(json.dumps({'characters': len(NAMES), 'battle_front': [56, 56],
                      'battle_back': [48, 48], 'portrait': [24, 24],
                      'public_folder': str(OUT.relative_to(ROOT))}))


if __name__ == '__main__':
    main()
