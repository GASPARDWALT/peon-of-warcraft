#!/usr/bin/env python3
"""Original RGB555 native pixel art for the friendly imp and Horde mailbox."""
from pathlib import Path
import json
import re
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/environment_v025/pet/assets'
GFX = ROOT / 'gfx/pack'
IMP = [
 '   3        3   ', '  313      313  ', '  321333333123  ', '   3222222223   ',
 '  332222222233  ', ' 32222222222223 ', '  322222222223  ', '   3332222333   ',
 '     322223     ', '   3332222333   ', '  322322223223  ', '  323322223323  ',
 '   3 322223 3   ', '     33 33  3   ', '    313 313 3   ', '    333 33333   ',
]
MAIL = [
 '   333333333    ', '  31111111133   ', ' 3122222222133  ', ' 3122333222113  ',
 ' 3122323222113  ', ' 3122333222113  ', ' 3122222222113  ', ' 3111111111113  ',
 '  33333333333   ', '      313       ', '      313       ', '      313       ',
 '      313       ', '      313       ', '     33333      ', '                ',
]
FIRE = ['        ', '   2    ', '  212   ', ' 21212  ', '2121122 ', ' 22122  ', '  222   ', '        ']


def encode(rows):
    out = bytearray()
    for ty in range(len(rows) // 8):
        for tx in range(len(rows[0]) // 8):
            for y in range(8):
                low = high = 0
                for x in range(8):
                    char = rows[ty * 8 + y][tx * 8 + x]
                    i = int(char) if char != ' ' else 0
                    low = (low << 1) | (i & 1)
                    high = (high << 1) | ((i >> 1) & 1)
                out.extend((low, high))
    return bytes(out)


def write_png(rows, palette, path):
    image = Image.new('RGBA', (len(rows[0]), len(rows)), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char != ' ': image.putpixel((x, y), palette[int(char)] + (255,))
    image.save(path)
    image.resize((image.width * 8, image.height * 8), Image.Resampling.NEAREST).save(
        path.with_name(path.stem.replace('_native', '_8x') + '.png'))


def expand_palette(row):
    """Match the actual RGB555 framebuffer, including replicated low bits."""
    values = [int(v) for v in re.findall(r'\d+', row.split(';',1)[0])]
    assert len(values) == 12 and all(0 <= v <= 31 for v in values)
    return [tuple((v << 3) | (v >> 2) for v in values[i:i+3]) for i in range(0,12,3)]


def main():
    OUT.mkdir(parents=True, exist_ok=True); GFX.mkdir(parents=True, exist_ok=True)
    for rows in (IMP, MAIL, FIRE):
        assert len(rows) % 8 == 0 and len(rows[0]) % 8 == 0
        assert all(len(r) == len(rows[0]) for r in rows)
    source_text = (ROOT / 'engine/battle/peon_warlock_pet.asm').read_text()
    native_pet_row = source_text.split('PeonPetBattlePalette:',1)[1].strip().splitlines()[0]
    native_world_rows = [r for r in (ROOT / 'gfx/overworld/peon_obj.pal').read_text().splitlines() if r.strip().startswith('RGB')]
    red = expand_palette(native_pet_row)
    brown = expand_palette(native_world_rows[3])
    write_png(IMP, red, OUT / 'warlock_imp_back_native.png')
    write_png(FIRE, red, OUT / 'imp_firebolt_native.png')
    write_png(MAIL, brown, OUT / 'horde_mailbox_native.png')
    # Export the native source walking sheet with binary alpha. This remains
    # the ROM's existing imp pixel pattern, tinted to the world red palette.
    source = Image.open(ROOT / 'gfx/sprites/peon_imp.png')
    world_palette = expand_palette(native_world_rows[0])
    world = Image.new('RGBA', source.size, (0,0,0,0))
    for y in range(source.height):
        for x in range(source.width):
            index = source.getpixel((x,y))
            if index: world.putpixel((x,y),world_palette[index]+(255,))
    world.save(OUT / 'friendly_imp_world_native_sheet.png')
    world.resize((source.width*4,source.height*4),Image.Resampling.NEAREST).save(
        OUT / 'friendly_imp_world_sheet_4x.png')
    (GFX / 'peon_warlock_pet_battle.2bpp').write_bytes(encode(IMP) + encode(FIRE))
    (GFX / 'peon_mailbox.2bpp').write_bytes(encode(MAIL))
    assert (GFX / 'peon_warlock_pet_battle.2bpp').stat().st_size == 80
    assert (GFX / 'peon_mailbox.2bpp').stat().st_size == 64
    (OUT / 'manifest.json').write_text(json.dumps({
        'original_art': True,
        'new_original_art': ['imp backview', 'Horde mailbox', 'small Firebolt'],
        'existing_world_sheet_export': 'gfx/sprites/peon_imp.png; unchanged native pixel indices',
        'public_png_palette_expansion': '(RGB5 << 3) | (RGB5 >> 2); native palette values',
        'palette_sources': {'imp_back': 'PeonPetBattlePalette', 'world_imp': 'PeonMapOBJPalettes slot0', 'mailbox': 'PeonMapOBJPalettes slot3'},
        'native_dimensions': {'imp_back': [16,16], 'mailbox': [16,16], 'firebolt': [8,8]},
        'alpha': 'binary; GBC background tile index 0 is white, world OBJ index 0 is transparent',
        'bank_1_battle_tiles': ['88','89','8a','8b','8c'],
        'battle_top_left_cell': [8,5],
        'player_hud_clear_region_avoided': {'top_left': [9,7], 'size': [11,5]},
        'native_world_imp': 'existing three-direction PeonImpGFX walking sheet, red OBJ palette 0',
        'mailbox_sprite_id': 103,
    }, indent=2) + '\n')
    print('Native imp backview, small firebolt and Horde mailbox PNGs/2bpp emitted.')


if __name__ == '__main__': main()
