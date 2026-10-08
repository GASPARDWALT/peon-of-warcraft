#!/usr/bin/env python3
"""Compile the original bread concept to one native four-tile GBC item icon."""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/valley_layout_update/items'
GFX = ROOT / 'gfx/pack/peon_food'
SOURCE = OUT / 'tough_bread_concept.png'
PALETTE = ((255, 255, 255), (239, 222, 181), (148, 90, 49), (0, 0, 0))
GRAY = [255, 255, 255, 170, 170, 170, 85, 85, 85, 0, 0, 0] + [0] * 756


def two_bpp(pixels):
    data = bytearray()
    for tile_y in range(2):
        for tile_x in range(2):
            tile = pixels[tile_y * 8:(tile_y + 1) * 8,
                          tile_x * 8:(tile_x + 1) * 8]
            for row in tile:
                low = high = 0
                for value in row:
                    low = (low << 1) | (int(value) & 1)
                    high = (high << 1) | ((int(value) >> 1) & 1)
                data.extend((low, high))
    return bytes(data)


def main():
    OUT.mkdir(parents=True, exist_ok=True); GFX.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert('RGBA')
    bbox = source.getchannel('A').point(lambda value: 255 if value >= 180 else 0).getbbox()
    assert bbox, 'Bread source has no opaque foreground'
    crop = source.crop(bbox)
    crop.thumbnail((14, 14), Image.Resampling.LANCZOS)
    fitted = Image.new('RGBA', (16, 16))
    fitted.paste(crop, ((16 - crop.width) // 2, (16 - crop.height) // 2))
    pixels = np.array(fitted)
    alpha = np.where(pixels[:, :, 3] >= 180, 255, 0).astype('uint8')
    colors = np.array(PALETTE[1:], dtype=float)
    distances = ((pixels[:, :, None, :3].astype(float) - colors) ** 2).sum(-1)
    values = (distances.argmin(-1) + 1).astype('uint8')
    values[alpha == 0] = 0
    # Native silhouettes need a full-pixel outline after large-to-small reduction.
    opaque = alpha == 255
    padded = np.pad(opaque, 1)
    enclosed = (padded[:-2, 1:-1] & padded[2:, 1:-1]
                & padded[1:-1, :-2] & padded[1:-1, 2:])
    values[opaque & ~enclosed] = 3
    # Rescue the concept's three scoring cuts at the native logical pixel grid.
    # Sub-pixel scoring otherwise collapses into isolated cream dots.
    for x, y in ((9, 4), (10, 5), (7, 6), (8, 7), (5, 8), (6, 9)):
        if values[y, x] == 2:
            values[y, x] = 1
    indexed = Image.fromarray(values, 'P')
    indexed.putpalette([value for color in PALETTE for value in color] + [0] * 756)
    rgba = Image.fromarray(np.dstack((np.array(indexed.convert('RGB')), alpha)), 'RGBA')
    rgba.save(OUT / 'tough_bread.png')
    rgba.resize((32, 32), Image.Resampling.NEAREST).save(OUT / 'tough_bread_2x.png')
    rgba.resize((128, 128), Image.Resampling.NEAREST).save(OUT / 'tough_bread_8x.png')
    indexed.putpalette(GRAY)
    indexed.save(GFX / 'bread.png')
    binary = two_bpp(values)
    assert len(binary) == 64
    (GFX / 'bread.2bpp').write_bytes(binary)
    palette_text = ''.join('\tRGB ' + ', '.join(f'{value >> 3:02d}' for value in color)
                           + '\n' for color in PALETTE)
    (GFX / 'bread.pal').write_text(palette_text)
    bounds = rgba.getchannel('A').getbbox()
    manifest = {
        'source': str(SOURCE.relative_to(ROOT)),
        'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'source_origin': 'Original generated bread concept; no commercial icon copied.',
        'native_png': str((OUT / 'tough_bread.png').relative_to(ROOT)),
        'native_size': [16, 16], 'opaque_bbox': list(bounds),
        'opaque_colors': len(np.unique(values[opaque])), 'alpha_values': [0, 255],
        'engine_png': str((GFX / 'bread.png').relative_to(ROOT)),
        'engine_2bpp': str((GFX / 'bread.2bpp').relative_to(ROOT)),
        'engine_palette': str((GFX / 'bread.pal').relative_to(ROOT)),
        'tile_count': 4, 'binary_bytes': len(binary),
        'palette_rgb555': [[value >> 3 for value in color] for color in PALETTE],
        'proposed_label': 'PeonBreadIconGFX', 'item_alias': 'PEON_CAMP_BREAD',
        'item_id_alias': 'ITEM_95',
        'integration': 'Ready icon only; item registry, inventory and healing handled separately.',
    }
    (OUT / 'tough_bread_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'native_icon': str((OUT / 'tough_bread.png').relative_to(ROOT)),
                      'size': [16, 16], 'colors': manifest['opaque_colors'],
                      'alpha': [0, 255], 'bytes': len(binary)}))


if __name__ == '__main__':
    main()
