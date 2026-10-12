#!/usr/bin/env python3
"""An intentionally hand-authored, symmetric Horde crest on a 16x16 grid.

The upper open diamond, lateral hooks and long central fang stay distinct at
native resolution. No antialiasing or palette expansion is used in the ROM.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/visual_polish_v026/horde'
ROWS = (
    '.......##.......',
    '......####......',
    '...##.####.##...',
    '...##########...',
    '..####....####..',
    '.####......####.',
    '..###..##..###..',
    '...###....###...',
    '..#####..#####..',
    '.###.######.###.',
    '..##..####..##..',
    '...##..##..##...',
    '....##.##.##....',
    '.....######.....',
    '.......##.......',
    '.......##.......',
)


def horde_emblem_indices():
    """Return cloth1 + dark3 indices for the shared four native banner tiles."""
    assert len(ROWS) == 16 and all(len(row) == 16 for row in ROWS)
    image = Image.new('L', (16, 16), 1)
    for y, row in enumerate(ROWS):
        for x, pixel in enumerate(row):
            if pixel == '#':
                image.putpixel((x, y), 3)
    return image


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    indices = horde_emblem_indices()
    for name, ink in (('horde_crest_red', (214, 66, 33)),
                      ('horde_crest_dark', (33, 25, 25))):
        image = Image.new('RGBA', indices.size)
        for y in range(16):
            for x in range(16):
                if indices.getpixel((x, y)) == 3:
                    image.putpixel((x, y), (*ink, 255))
        image.save(OUT / (name + '_native.png'))
        image.resize((256, 256), Image.Resampling.NEAREST).save(OUT / (name + '_16x.png'))
    panel = Image.new('RGB', (320, 160), (245, 222, 173))
    left = Image.open(OUT / 'horde_crest_red_native.png')
    right = Image.open(OUT / 'horde_crest_dark_native.png')
    panel.paste((214, 66, 33), (160, 0, 320, 160))
    for image, x in ((left, 16), (right, 176)):
        enlarged = image.resize((128, 128), Image.Resampling.NEAREST)
        panel.paste(enlarged, (x, 16), enlarged)
    panel.save(OUT / 'horde_crest_on_cloth_preview.png')
    (OUT / 'manifest.json').write_text(json.dumps({
        'native_dimensions': [16, 16], 'tiles': 4,
        'rows': ROWS, 'pixel_indices_sha256': hashlib.sha256(indices.tobytes()).hexdigest(),
        'native_cloth_index': 1, 'native_emblem_index': 3,
        'alpha': [0, 255], 'original_hand_authored_pixels': True,
        'reference': 'source/horde_symbol_reference.jpg',
        'native_integration': 'Shared by Horde standards and the hall carpet, preserving four-tile footprint.',
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
