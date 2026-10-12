#!/usr/bin/env python3
"""Draw an original readable fixed-cell Peon font without changing encoding.

The Crystal source sheet remains the immutable fallback for symbols, arrows,
UI glyphs and German diacritics. Only the explicitly listed Latin glyphs are
redrawn. This is deliberately not a variable-width text-engine migration.
"""
import hashlib
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/environment_v025/font'

# Six-pixel capitals: straight double-pixel stems keep headings legible on the
# native display. A clear outside margin remains inside every eight-pixel cell.
CAPS = {
    'A': ['011110','110011','110011','111111','110011','110011','110011'],
    'B': ['111110','110011','110011','111110','110011','110011','111110'],
    'C': ['011111','110000','110000','110000','110000','110000','011111'],
    'D': ['111110','110011','110011','110011','110011','110011','111110'],
    'E': ['111111','110000','110000','111110','110000','110000','111111'],
    'F': ['111111','110000','110000','111110','110000','110000','110000'],
    'G': ['011111','110000','110000','110111','110011','110011','011111'],
    'H': ['110011','110011','110011','111111','110011','110011','110011'],
    'I': ['11111','00100','00100','00100','00100','00100','11111'],
    'J': ['001111','000011','000011','000011','110011','110011','011110'],
    'K': ['110011','110110','111100','111000','111100','110110','110011'],
    'L': ['110000','110000','110000','110000','110000','110000','111111'],
    'M': ['110011','111111','111111','110011','110011','110011','110011'],
    'N': ['110011','111011','111011','110111','110111','110011','110011'],
    'O': ['011110','110011','110011','110011','110011','110011','011110'],
    'P': ['111110','110011','110011','111110','110000','110000','110000'],
    'Q': ['011110','110011','110011','110011','110111','110110','011101'],
    'R': ['111110','110011','110011','111110','110110','110011','110011'],
    'S': ['011111','110000','110000','011110','000011','000011','111110'],
    'T': ['111111','001100','001100','001100','001100','001100','001100'],
    'U': ['110011','110011','110011','110011','110011','110011','011110'],
    'V': ['110011','110011','110011','110011','110011','011110','001100'],
    'W': ['110011','110011','110011','110011','111111','111111','010010'],
    'X': ['110011','110011','011110','001100','011110','110011','110011'],
    'Y': ['110011','110011','011110','001100','001100','001100','001100'],
    'Z': ['111111','000011','000110','001100','011000','110000','111111'],
}

# Lowercase has a six-pixel x-height and explicit ascenders/descenders. Keeping
# real lowercase helps long English sentences scan without an all-caps wall.
LOWER = {
    'a': ['00000','01110','00001','01111','10001','10001','01111'],
    'b': ['10000','10000','11110','10001','10001','10001','11110'],
    'c': ['00000','01111','10000','10000','10000','10000','01111'],
    'd': ['00001','00001','01111','10001','10001','10001','01111'],
    'e': ['00000','01110','10001','11111','10000','10000','01111'],
    'f': ['00110','01001','01000','11100','01000','01000','01000'],
    'g': ['00000','01111','10001','10001','01111','00001','10001','01110'],
    'h': ['10000','10000','11110','10001','10001','10001','10001'],
    'i': ['00100','00000','01100','00100','00100','00100','01110'],
    'j': ['00010','00000','00110','00010','00010','00010','10010','01100'],
    'k': ['10000','10000','10010','10100','11000','10100','10010'],
    'l': ['01100','00100','00100','00100','00100','00100','00110'],
    'm': ['000000','110110','101001','101001','101001','101001','101001'],
    'n': ['00000','11110','10001','10001','10001','10001','10001'],
    'o': ['00000','01110','10001','10001','10001','10001','01110'],
    'p': ['00000','11110','10001','10001','10001','11110','10000','10000'],
    'q': ['00000','01111','10001','10001','10001','01111','00001','00001'],
    'r': ['00000','10110','11001','10000','10000','10000','10000'],
    's': ['00000','01111','10000','01110','00001','00001','11110'],
    't': ['01000','01000','11110','01000','01000','01001','00110'],
    'u': ['00000','10001','10001','10001','10001','10001','01111'],
    'v': ['00000','10001','10001','10001','10001','01010','00100'],
    'w': ['000000','100001','100001','100001','101101','101101','010010'],
    'x': ['00000','10001','01010','00100','00100','01010','10001'],
    'y': ['00000','10001','10001','10001','01111','00001','10001','01110'],
    'z': ['00000','11111','00001','00010','00100','01000','11111'],
}

NUMBERS = {
    '0': ['01110','10001','10011','10101','11001','10001','01110'],
    '1': ['00100','01100','00100','00100','00100','00100','01110'],
    '2': ['01110','10001','00001','00010','00100','01000','11111'],
    '3': ['11110','00001','00001','01110','00001','00001','11110'],
    '4': ['00010','00110','01010','10010','11111','00010','00010'],
    '5': ['11111','10000','10000','11110','00001','00001','11110'],
    '6': ['01110','10000','10000','11110','10001','10001','01110'],
    '7': ['11111','00001','00010','00100','01000','01000','01000'],
    '8': ['01110','10001','10001','01110','10001','10001','01110'],
    '9': ['01110','10001','10001','01111','00001','00001','01110'],
}

PUNCTUATION = {
    '(': ['00010','00100','01000','01000','01000','00100','00010'],
    ')': ['01000','00100','00010','00010','00010','00100','01000'],
    ':': ['00000','00110','00110','00000','00110','00110','00000'],
    ';': ['00000','00110','00110','00000','00110','00110','00100','01000'],
    '[': ['01110','01000','01000','01000','01000','01000','01110'],
    ']': ['01110','00010','00010','00010','00010','00010','01110'],
    "'": ['00110','00110','00100','00000','00000','00000','00000'],
    '-': ['00000','00000','00000','11111','00000','00000','00000'],
    '?': ['01110','10001','00001','00010','00100','00000','00100'],
    '!': ['00110','00110','00110','00110','00110','00000','00110'],
    '.': ['00000','00000','00000','00000','00000','00110','00110'],
    '&': ['01100','10010','10100','01000','10101','10010','01101'],
    'é': ['00010','00100','01110','10001','11111','10000','01111'],
    '×': ['00000','10001','01010','00100','01010','10001','00000'],
    '/': ['00001','00001','00010','00100','01000','10000','10000'],
    ',': ['00000','00000','00000','00000','00000','00110','00110','00100'],
}


def encoding():
    # Restrict this lookup to actual standard-font byte positions: Japanese
    # aliases later in the source must not replace the Latin names above.
    text = (ROOT / 'constants/charmap.asm').read_text()
    return {m[1]: int(m[2], 16) for m in re.finditer(
        r'charmap\s+"([^"\n]+)",\s+\$([0-9a-f]+)', text)
        if 0x80 <= int(m[2], 16) <= 0xff}


def tile_box(code):
    index = code - 0x80
    x, y = (index % 16) * 8, (index // 16) * 8
    return x, y, x + 8, y + 8


def draw_glyph(sheet, code, rows, offset=1):
    assert 1 <= len(rows) <= 8 and max(map(len, rows)) <= 6
    box = tile_box(code)
    sheet.paste(255, box)
    for y, row in enumerate(rows):
        for x, bit in enumerate(row):
            assert bit in '01'
            if bit == '1':
                sheet.putpixel((box[0] + offset + x, box[1] + y), 0)


def encode_1bpp(sheet):
    output = bytearray()
    for code in range(0x80, 0x100):
        tile = sheet.crop(tile_box(code))
        for y in range(8):
            output.append(sum((tile.getpixel((x, y)) == 0) << (7 - x)
                              for x in range(8)))
    return bytes(output)


def sample(sheet, text):
    codes = encoding()
    image = Image.new('L', (len(text) * 8, 8), 255)
    for i, ch in enumerate(text):
        if ch == ' ':
            continue
        image.paste(sheet.crop(tile_box(codes[ch])), (i * 8, 0))
    return image


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    original = Image.open(ROOT / 'gfx/font/font.png').convert('L')
    assert original.size == (128, 64)
    sheet = original.copy()
    codes, replaced = encoding(), []
    for ch, rows in (CAPS | LOWER | NUMBERS | PUNCTUATION).items():
        draw_glyph(sheet, codes[ch], rows)
        replaced.append(codes[ch])
    # Crystal stores common apostrophe+letter pairs as one cell. Keep those
    # encodings and the six-pixel footprint; use a visible top apostrophe.
    for ending in 'dlmrstv':
        code = codes["'" + ending]
        rows = LOWER[ending]
        if ending == 'm':
            rows = ['00000','11010','10101','10101','10101','10101','10101']
        # The compact contraction glyph has apostrophe in column zero and
        # a complete five-pixel lowercase outline in columns two through six.
        box = tile_box(code)
        sheet.paste(255, box)
        for y in (0, 1):
            sheet.putpixel((box[0], box[1] + y), 0)
        for y, row in enumerate(rows):
            for x, bit in enumerate(row):
                if bit == '1':
                    sheet.putpixel((box[0] + x + 2, box[1] + y), 0)
        replaced.append(code)
    # The decimal-point alias must remain visually identical to full stop.
    sheet.paste(sheet.crop(tile_box(codes['.'])), tile_box(codes['<DOT>'])[:2])
    replaced.append(codes['<DOT>'])
    target = ROOT / 'gfx/font/peon_readable.png'
    sheet.save(target)
    sheet.save(OUT / 'peon_readable_sheet_native.png')
    sheet.resize((1024, 512), Image.Resampling.NEAREST).save(OUT / 'peon_readable_sheet_8x.png')
    transparent = Image.new('RGBA', sheet.size)
    for y in range(sheet.height):
        for x in range(sheet.width):
            if sheet.getpixel((x, y)) == 0:
                transparent.putpixel((x, y), (247, 232, 185, 255))
    transparent.save(OUT / 'peon_readable_glyphs_transparent.png')
    samples = [
        'PEON OF WARCRAFT', 'Péon ABCDE', 'Ill 1I10O 36/36',
        'Your journey begins.', 'A small healing potion.',
        'Warlock: curses and fel.', 'MACE STRIKE --/--',
        'Quest complete! 25 XP.', "I'll teach you a spell.",
        'Agility, poison, injury.',
    ]
    # A wide comparison keeps every sentence untruncated at its native size.
    panel = Image.new('RGB', (512, 24 + 16 * len(samples) + 12), '#211a14')
    draw = ImageDraw.Draw(panel)
    draw.text((8, 6), 'Original fixed cells', fill='#f7e8b9')
    draw.text((264, 6), 'Readable fixed cells', fill='#f7e8b9')
    for row, text in enumerate(samples):
        for col, font in enumerate((original, sheet)):
            line = sample(font, text)
            tile = Image.new('RGB', line.size, '#f7e8b9')
            tile.paste('#211a14', (0, 0, line.width, line.height), line.point(lambda p: 255 - p))
            panel.paste(tile, (8 + 256 * col, 24 + row * 16))
    panel.save(OUT / 'peon_font_comparison_native.png')
    panel.resize((1536, panel.height * 3), Image.Resampling.NEAREST).save(OUT / 'peon_font_comparison_3x.png')
    untouched = sorted(set(range(0x80, 0x100)) - set(replaced))
    assert all(sheet.crop(tile_box(code)).tobytes() == original.crop(tile_box(code)).tobytes()
               for code in untouched)
    raw = encode_1bpp(sheet)
    assert len(raw) == 1024
    report = {
        'cell_size': [8, 8], 'sheet_size': list(sheet.size), 'tile_count': 128,
        'binary_pixels_only': set(sheet.tobytes()) == {0, 255},
        'original_source_unchanged': True, 'redrawn_codes': sorted(set(replaced)),
        'preserved_codes': untouched, 'arrows_icons_borders_charmap_unchanged': True,
        'font_1bpp_sha256': hashlib.sha256(raw).hexdigest(),
        'output': str(target.relative_to(ROOT)),
        'inspiration_references': [
            'https://github.com/gbdk-2020/gbdk-2020/blob/develop/gbdk-lib/include/gbdk/font.h',
            'https://github.com/pret/pokecrystal/blob/master/engine/gfx/load_font.asm',
        ],
        'external_glyph_art_copied': False,
    }
    (OUT / 'font_build.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'output': report['output'], 'redrawn_glyphs': len(set(replaced)),
                      'font_1bpp_sha256': report['font_1bpp_sha256']}))


if __name__ == '__main__':
    main()
