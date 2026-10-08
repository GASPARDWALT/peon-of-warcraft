#!/usr/bin/env python3
"""Compile the retained original Earth Totem icon into a tiny battle prop."""
from pathlib import Path
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/battle_totems'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'references/generated/durotar_v022/items/earth_totem_16.png'
    original = Image.open(source).convert('RGBA').resize((8,16), Image.Resampling.NEAREST)
    image = Image.new('P', original.size)
    image.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
    source_colours = [(176,120,56),(64,136,48),(24,16,16)]
    for y in range(16):
        for x in range(8):
            r,g,b,a=original.getpixel((x,y))
            value=0 if a<128 else 1+min(range(3), key=lambda i: sum(
                (v-w)**2 for v,w in zip((r,g,b),source_colours[i])))
            image.putpixel((x,y),value)
    native = bytearray()
    for ty in range(2):
        for y in range(8):
            values = [image.getpixel((x, ty * 8 + y)) for x in range(8)]
            assert all(0 <= v < 4 for v in values)
            native.extend((sum((v & 1) << (7-x) for x,v in enumerate(values)),
                           sum((v >> 1) << (7-x) for x,v in enumerate(values))))
    image.save(ROOT / 'gfx/pack/peon_earth_totem_battle.png')
    (ROOT / 'gfx/pack/peon_earth_totem_battle.2bpp').write_bytes(native)
    colours = [(255,255,255),(181,123,57),(66,140,49),(24,16,16)]
    rgba = Image.new('RGBA', image.size)
    for y in range(16):
        for x in range(8):
            v=image.getpixel((x,y))
            rgba.putpixel((x,y), (*colours[v],255) if v else (0,0,0,0))
    rgba.save(OUT / 'earth_totem_battle_native_8x16.png')
    rgba.resize((64,128), Image.Resampling.NEAREST).save(OUT / 'earth_totem_battle_8x.png')
    (OUT / 'manifest.json').write_text(json.dumps({
        'item_id':148,'size':[8,16],'binary_alpha':True,
        'screen_tiles':[[8,6],[8,7]],'vram_tiles':[134,135],
        'vram_bank':1,'vram_start':34816+96,'bg_palette':6,
        'effect':'Player acts first while placed; placing costs one battle turn.',
        'save_state':'Reusable inventory item; placed state is battle-only.'
    },indent=2)+'\n')
    print('Earth Totem: 8x16, two native tiles, transparent PNG exports')


if __name__ == '__main__':
    main()
