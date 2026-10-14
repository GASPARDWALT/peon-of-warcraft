#!/usr/bin/env python3
"""Add native è and repair solid bold m using existing glyph art only."""
import hashlib
import json
from pathlib import Path
import re
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/battle_names_v0213/grave_glyph'
CODE = 0xd7
SOURCE = 0xea
LOWER_M = 0xac


def sha(data): return hashlib.sha256(data).hexdigest()

def box(code):
    i = code - 128; x, y = i % 16 * 8, i // 16 * 8
    return x, y, x + 8, y + 8


def patch():
    OUT.mkdir(parents=True, exist_ok=True)
    charmap = (ROOT / 'constants/charmap.asm').read_text()
    latin = charmap.split('; Japanese control characters', 1)[0]
    aliases = re.findall(r'charmap\s+"([^"\n]+)",\s+\$d7\b', latin, re.I)
    assert aliases == ['è'], ('Reserved cell unexpectedly has another active Latin alias', aliases)
    regular_path = ROOT / 'gfx/font/peon_regular_v026.1bpp'
    bold_path = ROOT / 'gfx/font/peon_bold_v026.1bpp'
    previous = regular_path.read_bytes(); previous_bold = bold_path.read_bytes()
    assert len(previous) == len(previous_bold) == 1024
    acute = previous[(SOURCE - 128) * 8:(SOURCE - 127) * 8]
    assert acute[:2] == bytes((0x08, 0x10)), ('Expected existing native acute accent', acute.hex())
    # Mirror only the existing accent rows; the original complete é body is
    # copied byte for byte, retaining its baseline and six-pixel footprint.
    reverse = lambda byte: int(f'{byte:08b}'[::-1], 2)
    grave = bytes(reverse(row) for row in acute[:2]) + acute[2:]
    start = (CODE - 128) * 8
    assert previous[start:start + 8] in (bytes(8), grave)
    native = bytearray(previous); native[start:start + 8] = grave
    bold_native = bytearray(previous_bold)
    bold_native[start:start + 8] = bytes(row | row >> 1 for row in grave)
    m_start = (LOWER_M - 128) * 8
    regular_m = bytes(native[m_start:m_start + 8])
    # Horizontal thickening joins all three narrow stems into a rectangle.
    # Retain the exact existing regular m outline in the bold cache instead.
    bold_native[m_start:m_start + 8] = regular_m
    assert native[:start] == previous[:start] and native[start + 8:] == previous[start + 8:]
    assert all(bold_native[index * 8:index * 8 + 8] == previous_bold[index * 8:index * 8 + 8]
               for index in range(128) if index + 128 not in (CODE, LOWER_M))
    for slug, data in (('peon_regular_v026', native), ('peon_bold_v026', bold_native)):
        path = ROOT / 'gfx/font' / slug
        path.with_suffix('.1bpp').write_bytes(data)
        sheet = Image.open(path.with_suffix('.png')).convert('L')
        assert sheet.size == (128, 64)
        for code in ((CODE, LOWER_M) if slug == 'peon_bold_v026' else (CODE,)):
            cell_start = (code - 128) * 8
            x, y, _, _ = box(code)
            for row, byte in enumerate(data[cell_start:cell_start + 8]):
                for col in range(8): sheet.putpixel((x + col, y + row), 0 if byte & (128 >> col) else 255)
        sheet.save(path.with_suffix('.png'))
        single = Image.new('RGBA', (8, 8), (0, 0, 0, 0))
        for row, byte in enumerate(data[start:start + 8]):
            for col in range(8):
                if byte & (128 >> col): single.putpixel((col, row), (0, 0, 0, 255))
        single.save(OUT / (slug + '_grave_native.png'))
        single.resize((64, 64), Image.Resampling.NEAREST).save(OUT / (slug + '_grave_8x.png'))
    single_m = Image.new('RGBA', (8, 8), (0, 0, 0, 0))
    for row, byte in enumerate(regular_m):
        for col in range(8):
            if byte & (128 >> col): single_m.putpixel((col, row), (0, 0, 0, 255))
    single_m.save(OUT / 'peon_bold_v026_m_native.png')
    single_m.resize((64, 64), Image.Resampling.NEAREST).save(OUT / 'peon_bold_v026_m_8x.png')
    (OUT / 'import.json').write_text(json.dumps({
        'character': 'è', 'code': '$d7', 'canvas': [8, 8], 'font_tiles': 128,
        'source': 'gfx/font/peon_regular_v026.1bpp', 'source_character': 'é',
        'source_code': '$ea', 'source_acute_bytes': acute.hex(), 'derived_grave_bytes': grave.hex(),
        'changed_cells': {'regular': ['$d7'], 'bold': ['$ac (m)', '$d7 (è)']},
        'bold_m_exact_existing_regular_outline': True,
        'regular_m_bytes': regular_m.hex(),
        'old_solid_expanded_m_bytes': bytes(row | row >> 1 for row in regular_m).hex(),
        'all_other_regular_and_bold_cells_identical': True,
        'original_crystal_font_png_unchanged': True,
        'english_slot_previously_blank': True,
        'retained_japanese_alias': 'ら (legacy Japanese/mobile text; already blank in active English font)',
        'regular_sha256': sha(native), 'bold_sha256': sha(bold_native)
    }, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'character': 'è', 'code': '$d7', 'bytes_per_font': len(native)}, ensure_ascii=False))


if __name__ == '__main__': patch()
