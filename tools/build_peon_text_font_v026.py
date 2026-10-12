#!/usr/bin/env python3
"""Generate thin fixed-cell text and a separate bold face for person names."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw
import build_peon_readable_font as old

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/visual_polish_v026/font'
CAPS = {
    'A': ['01110','10001','10001','11111','10001','10001','10001'],
    'B': ['11110','10001','10001','11110','10001','10001','11110'],
    'C': ['01111','10000','10000','10000','10000','10000','01111'],
    'D': ['11110','10001','10001','10001','10001','10001','11110'],
    'E': ['11111','10000','10000','11110','10000','10000','11111'],
    'F': ['11111','10000','10000','11110','10000','10000','10000'],
    'G': ['01111','10000','10000','10111','10001','10001','01111'],
    'H': ['10001','10001','10001','11111','10001','10001','10001'],
    'I': ['01110','00100','00100','00100','00100','00100','01110'],
    'J': ['00111','00001','00001','00001','10001','10001','01110'],
    'K': ['10001','10010','10100','11000','10100','10010','10001'],
    'L': ['10000','10000','10000','10000','10000','10000','11111'],
    'M': ['10001','11011','10101','10101','10001','10001','10001'],
    'N': ['10001','11001','10101','10011','10001','10001','10001'],
    'O': ['01110','10001','10001','10001','10001','10001','01110'],
    'P': ['11110','10001','10001','11110','10000','10000','10000'],
    'Q': ['01110','10001','10001','10001','10101','10010','01101'],
    'R': ['11110','10001','10001','11110','10100','10010','10001'],
    'S': ['01111','10000','10000','01110','00001','00001','11110'],
    'T': ['11111','00100','00100','00100','00100','00100','00100'],
    'U': ['10001','10001','10001','10001','10001','10001','01110'],
    'V': ['10001','10001','10001','10001','10001','01010','00100'],
    'W': ['10001','10001','10001','10101','10101','10101','01010'],
    'X': ['10001','10001','01010','00100','01010','10001','10001'],
    'Y': ['10001','10001','01010','00100','00100','00100','00100'],
    'Z': ['11111','00001','00010','00100','01000','10000','11111'],
}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    regular = Image.open(ROOT / 'gfx/font/font.png').convert('L')
    codes = old.encoding()
    lower = dict(old.LOWER)
    lower['m'] = ['00000','11010','10101','10101','10101','10101','10101']
    lower['w'] = ['00000','10001','10001','10101','10101','10101','01010']
    punctuation = dict(old.PUNCTUATION)
    punctuation.update({'!': ['00100']*5+['00000','00100'],
                        ':': ['00000','00100','00000','00000','00100','00000','00000'],
                        '.': ['00000']*6+['00100'],
                        "'": ['00100','00100','00000','00000','00000','00000','00000']})
    replaced = []
    for ch, rows in (CAPS | lower | old.NUMBERS | punctuation).items():
        old.draw_glyph(regular, codes[ch], rows)
        replaced.append(codes[ch])
    for ending in 'dlmrstv':
        box = old.tile_box(codes["'"+ending]); regular.paste(255, box)
        for y in (0, 1): regular.putpixel((box[0],box[1]+y),0)
        for y,row in enumerate(lower[ending]):
            for x,bit in enumerate(row):
                if bit == '1': regular.putpixel((box[0]+x+2,box[1]+y),0)
        replaced.append(codes["'"+ending])
    regular.paste(regular.crop(old.tile_box(codes['.'])),old.tile_box(codes['<DOT>'])[:2])
    replaced.append(codes['<DOT>'])
    raw = old.encode_1bpp(regular)
    boldraw = bytes(value | value >> 1 for value in raw)
    bold = Image.new('L',regular.size,255)
    for code in range(0x80,0x100):
        box=old.tile_box(code)
        for y,row in enumerate(boldraw[(code-0x80)*8:(code-0x7f)*8]):
            for x in range(8):
                if row & 1 << (7-x): bold.putpixel((box[0]+x,box[1]+y),0)
    for slug,sheet,binary in (('peon_regular_v026',regular,raw),('peon_bold_v026',bold,boldraw)):
        sheet.save(ROOT / 'gfx/font' / (slug+'.png'))
        (ROOT / 'gfx/font' / (slug+'.1bpp')).write_bytes(binary)
        sheet.save(OUT / (slug+'_native.png'))
        sheet.resize((1024,512),Image.Resampling.NEAREST).save(OUT / (slug+'_8x.png'))
        alpha=Image.new('RGBA',sheet.size)
        for y in range(sheet.height):
            for x in range(sheet.width):
                if sheet.getpixel((x,y))==0: alpha.putpixel((x,y),(247,232,185,255))
        alpha.save(OUT / (slug+'_transparent.png'))
    lines = ['GORNEK','Péon ABCDE','Kento Brandenhoof','Your journey begins.',
             'Healing potion: 20 HP.','Ill 1I10O 36/36','Shaman: Nature and fire.']
    panel=Image.new('RGB',(512,24+len(lines)*16),'#f7e8b9'); draw=ImageDraw.Draw(panel)
    draw.text((8,5),'Regular body text',fill='#211a14'); draw.text((264,5),'Names bold, body regular',fill='#211a14')
    for i,line in enumerate(lines):
        for column,sheet in enumerate((regular,bold if i<3 else regular)):
            sample=old.sample(sheet,line); ink=Image.new('RGB',sample.size,'#211a14')
            panel.paste(ink,(8+column*256,24+i*16),sample.point(lambda p:255-p))
    panel.save(OUT/'regular_and_name_weight_native.png')
    panel.resize((1536,panel.height*3),Image.Resampling.NEAREST).save(OUT/'regular_and_name_weight_3x.png')
    original=Image.open(ROOT/'gfx/font/font.png').convert('L')
    preserved=sorted(set(range(128,256))-set(replaced))
    assert all(regular.crop(old.tile_box(code)).tobytes()==original.crop(old.tile_box(code)).tobytes() for code in preserved)
    report=dict(cell_size=[8,8],native_regular_width=5,bold_expands_right_by_one_pixel=True,
        glyph_count=128,regular_sha256=hashlib.sha256(raw).hexdigest(),
        bold_sha256=hashlib.sha256(boldraw).hexdigest(),preserved_codes=preserved,
        encoding_and_box_dimensions_unchanged=True,previous_published_font_assets_unchanged=True,
        bold_bg_bank=1,bold_bg_address_ranges={'world':['$9690','$97ff'],
                                            'battle':['$8920','$8a8f']},
        bold_cache_capacity=23,
        actual_native_rom_capture=False)
    (OUT/'font_build.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Generated regular and name-only bold fonts: 128 unchanged 8x8 cells.')

if __name__=='__main__': main()
