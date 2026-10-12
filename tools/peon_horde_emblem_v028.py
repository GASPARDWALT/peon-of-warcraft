#!/usr/bin/env python3
"""A small, deliberately readable Horde crest, authored as whole pixels.

The upper horns, open ring, central diamond and two downward hooks follow the
official Orc tournament icon. The bitmap is new hand-placed pixel art; the
reference JPEG is not copied into the game or used as a ROM color source.
"""
from pathlib import Path
import hashlib
import json

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/polish_v028/environment'
ROWS = (
    '.......##.......',
    '...#..####..#...',
    '...##########...',
    '..####....####..',
    '.####......####.',
    '..###......###..',
    '..##...##...##..',
    '.###..####..###.',
    '####...##...####',
    '..###......###..',
    '...###....###...',
    '....##....##....',
    '...###....###...',
    '..####....####..',
    '....##....##....',
    '....##....##....',
)


def horde_emblem_indices():
    assert len(ROWS) == 16 and all(len(row) == 16 for row in ROWS)
    image = Image.new('L', (16, 16), 1)
    for y, row in enumerate(ROWS):
        for x, pixel in enumerate(row):
            if pixel == '#':
                image.putpixel((x, y), 3)
    return image


def emit():
    OUT.mkdir(parents=True, exist_ok=True)
    indices = horde_emblem_indices()
    for name, ink in (('horde_crest_red', (214, 66, 33)),
                      ('horde_crest_dark', (49, 33, 33))):
        image = Image.new('RGBA', indices.size)
        for y in range(16):
            for x in range(16):
                if indices.getpixel((x, y)) == 3:
                    image.putpixel((x, y), (*ink, 255))
        image.save(OUT / (name + '_native.png'))
        image.resize((256, 256), Image.Resampling.NEAREST).save(
            OUT / (name + '_16x.png'))
    (OUT / 'horde_emblem.json').write_text(json.dumps({
        'native_size': [16, 16], 'native_tiles': 4, 'rows': ROWS,
        'pixel_indices_sha256': hashlib.sha256(indices.tobytes()).hexdigest(),
        'alpha': [0, 255], 'hand_authored_native_pixels': True,
        'reference_url': 'https://wow.zamimg.com/images/wow/icons/large/inv_misc_tournaments_symbol_orc.jpg',
        'native_placement': 'Cloth center of metatile 6, mounted on timber walls only; floor 5 contains no emblem.',
    }, indent=2) + '\n')


if __name__ == '__main__':
    emit()
