#!/usr/bin/env python3
"""Original native 16x16 healing/mana flasks, with three colors + alpha.

No downloaded Blizzard pixels. PNG alpha becomes the current native menu
parchment color at 2bpp index zero; physical GBC backgrounds have no alpha.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GFX = ROOT / 'gfx/pack/peon_item_icons'
OUT = ROOT / 'references/generated/environment_v025/potions/assets'
ROWS = [
    '      3333      ',
    '      3113      ',
    '      3333      ',
    '      3113      ',
    '     311113     ',
    '    31111113    ',
    '   3111111113   ',
    '   3111222113   ',
    '  311222222113  ',
    '  312222222213  ',
    '  312222222213  ',
    '  311222222213  ',
    '   3122222213   ',
    '   3312221333   ',
    '     333333     ',
    '                ',
]


def encode(indices):
    binary = bytearray()
    for ty in range(2):
        for tx in range(2):
            for y in range(8):
                low = high = 0
                for x in range(8):
                    value = int(indices[ty * 8 + y, tx * 8 + x])
                    low = (low << 1) | (value & 1)
                    high = (high << 1) | ((value >> 1) & 1)
                binary.extend((low, high))
    return bytes(binary)


def main():
    assert len(ROWS) == 16 and all(len(row) == 16 for row in ROWS)
    OUT.mkdir(parents=True, exist_ok=True)
    GFX.mkdir(parents=True, exist_ok=True)
    indices = np.array([[int(c) if c != ' ' else 0 for c in row] for row in ROWS], dtype='uint8')
    records = []
    for slug, name, liquid, item, effect in [
        ('minor_healing_potion', 'Minor Healing Potion', (224, 48, 56), 0x12, '20 HP; all classes'),
        ('minor_mana_potion', 'Minor Mana Potion', (48, 136, 232), 0x3f, '5 charges each spell; caster classes'),
    ]:
        palette = [(248, 232, 184), (248, 240, 208), liquid, (24, 16, 16)]
        rgba = np.array(palette, dtype='uint8')[indices]
        rgba = np.dstack((rgba, np.where(indices == 0, 0, 255).astype('uint8')))
        rgba[indices == 0, :3] = 0
        png = Image.fromarray(rgba)
        png.save(GFX / (slug + '.png'))
        png.save(OUT / (slug + '_native.png'))
        png.resize((128, 128), Image.Resampling.NEAREST).save(OUT / (slug + '_8x.png'))
        binary = encode(indices)
        assert len(binary) == 64
        (GFX / (slug + '.2bpp')).write_bytes(binary)
        palette_source = '; Original potion icon, three opaque RGB555 colors.\n\tRGB ' + ', '.join(
            ','.join(str(c // 8) for c in rgb) for rgb in palette) + '\n'
        (GFX / (slug + '.pal')).write_text(palette_source)
        records.append({'name': name, 'slug': slug, 'item_id': item, 'effect': effect,
                        'native_size': [16, 16], 'opaque_colors': 3, 'alpha': 'binary',
                        '2bpp_sha256': hashlib.sha256(binary).hexdigest(),
                        'native_png': str((OUT / (slug + '_native.png')).relative_to(ROOT))})
    (OUT / 'manifest.json').write_text(json.dumps({'original_art': True, 'items': records}, indent=2) + '\n')
    print('Original native potion PNGs, palettes and 2bpp tiles emitted.')


if __name__ == '__main__':
    main()
