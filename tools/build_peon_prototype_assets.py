#!/usr/bin/env python3
"""Build original, deliberately small v0.1 tile and NPC pixel assets."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]

def indexed(path, image):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    image.putpalette([255,255,255,170,170,170,85,85,85,0,0,0] + [0]*756)
    image.save(path)

def block(kind):
    im = Image.new('P', (32,32), 1)
    d = ImageDraw.Draw(im)
    if kind in (0,2):
        for x,y in [(3,5),(19,9),(10,24),(27,28)]: d.point((x,y),2)
        if kind == 2:
            d.rectangle((0,10,31,21),fill=0)
            d.line((0,9,31,9),fill=2); d.line((0,22,31,22),fill=2)
    elif kind == 1:
        d.rectangle((0,0,31,31),fill=3)
        for x,y in [(0,0),(16,0),(0,16),(16,16)]:
            d.rectangle((x+1,y+1,x+14,y+14),fill=2)
            d.line((x+2,y+2,x+13,y+2),fill=1)
    elif kind == 3:
        d.rectangle((14,2,18,29),fill=3)
        d.rectangle((15,3,17,28),fill=2)
        d.rectangle((6,10,14,14),fill=3); d.rectangle((6,6,9,13),fill=2)
        d.rectangle((18,15,25,19),fill=3); d.rectangle((23,9,25,18),fill=2)
    elif kind == 4:
        d.polygon([(1,29),(1,17),(16,1),(30,17),(30,29)],fill=3)
        d.polygon([(3,16),(16,3),(28,16)],fill=2)
        for y in (9,13): d.line((8,y,24,y),fill=1)
        d.rectangle((3,18,28,28),fill=1)
        d.rectangle((13,18,19,30),fill=3)
        d.rectangle((5,19,9,23),fill=2); d.rectangle((23,19,26,23),fill=2)
    elif kind == 5:
        d.rectangle((0,0,31,31),fill=1)
        d.line((0,0,31,0),fill=2); d.line((0,0,0,31),fill=2)
        d.rectangle((6,0,25,31),fill=2)
        d.line((8,0,8,31),fill=0); d.line((23,0,23,31),fill=0)
    elif kind == 6:
        d.rectangle((7,1,10,30),fill=3)
        d.rectangle((11,2,26,20),fill=2)
        d.line((12,3,25,3),fill=0)
        d.polygon([(17,6),(22,9),(20,15),(16,15),(14,9)],fill=3)
        d.line((18,7,18,18),fill=0)
    elif kind == 7:
        d.rectangle((0,0,31,31),fill=0)
        for x in (0,16): d.line((x,0,x,31),fill=2)
        for y in (0,16): d.line((0,y,31,y),fill=2)
    return im

def main():
    # Original native-resolution gate vignette, 60 tiles, below the title text.
    gate=Image.new('P',(80,48),0); g=ImageDraw.Draw(gate)
    g.rectangle((12,1,67,10),fill=3); g.rectangle((14,3,65,8),fill=2)
    for x in (12,58):
        g.rectangle((x,9,x+9,47),fill=3); g.rectangle((x+2,10,x+7,45),fill=2)
        for y in (16,24,32,40): g.line((x+2,y,x+7,y),fill=1)
    g.polygon([(31,45),(36,29),(39,19),(43,29),(49,45)],fill=2)
    g.ellipse((33,13,45,25),fill=1)
    for x in (3,70):
        g.rectangle((x,37,x+7,47),fill=3)
        g.polygon([(x,37),(x+2,26),(x+4,31),(x+6,23),(x+7,37)],fill=2)
        g.rectangle((x+2,33,x+5,36),fill=1)
    indexed('gfx/title/peon_gate.png',gate)
    tiles=[]; palettes=[]; meta=[]
    for kind in range(9):
        im=block(kind if kind<8 else 0)
        pal=[1,5,4,2,5,1,1,5,1][kind]
        for y in range(4):
            for x in range(4):
                tile=tuple(im.crop((x*8,y*8,x*8+8,y*8+8)).get_flattened_data())
                key=(tile,pal)
                if key not in tiles: tiles.append(key); palettes.append(pal)
                meta.append(tiles.index(key))
    assert len(tiles)<=96, len(tiles)
    sheet=Image.new('P',(128,96),0)
    for i,(tile,_) in enumerate(tiles):
        for j,v in enumerate(tile): sheet.putpixel(((i%16)*8+j%8,(i//16)*8+j//8),v)
    indexed('gfx/tilesets/peon.png',sheet)
    (ROOT/'data/tilesets/peon_metatiles.bin').write_bytes(bytes(meta))
    collisions=['FLOOR','WALL','FLOOR','WALL','WALL','FLOOR','WALL','FLOOR','FLOOR']
    (ROOT/'data/tilesets/peon_collision.asm').write_text(''.join('\ttilecoll '+', '.join([c]*4)+'\n' for c in collisions))
    palbytes=bytearray()
    palettes+= [7]*(256-len(palettes))
    for i in range(0,256,2): palbytes.append(palettes[i] | palettes[i+1]<<4)
    (ROOT/'gfx/tilesets/peon_palette_map.bin').write_bytes(palbytes)
    for name,w,h in [('PeonOpening',8,6),('GrommashHold',8,6),('TheDen',12,10)]:
        # Block zero is reserved as the engine's border sentinel.
        data=[8]*(w*h)
        for y in range(h):
            for x in range(w):
                if x in (0,w-1) or y in (0,h-1): data[y*w+x]=1
                elif name=='GrommashHold': data[y*w+x]=5 if x in (3,4) else 7
                elif y==h//2: data[y*w+x]=2
        if name=='PeonOpening':
            for x,y in [(2,2),(5,3),(6,1)]: data[y*w+x]=3
        if name=='TheDen':
            for x,y in [(2,2),(8,2)]: data[y*w+x]=4
            for x,y in [(1,4),(10,6),(9,7)]: data[y*w+x]=3
            data[2*w+5]=6
        (ROOT/f'maps/{name}.blk').write_bytes(bytes(data))
    # Three directional idle frames plus three step frames; standard Crystal NPCs.
    for name in ['peon_kento','peon_thrall','peon_warrior','peon_warlock','peon_hunter','peon_boar','peon_quest_marker','peon_sleeping']:
        frame=Image.new('P',(16,16),0); d=ImageDraw.Draw(frame)
        if name=='peon_sleeping':
            d.rectangle((2,8,13,13),fill=3); d.rectangle((7,9,12,12),fill=1)
            d.rectangle((1,7,6,11),fill=2); d.line((2,9,4,9),fill=3)
            d.rectangle((11,12,14,14),fill=3)
        elif name=='peon_quest_marker':
            d.rectangle((6,1,9,9),fill=3); d.rectangle((7,2,8,8),fill=1)
            d.rectangle((6,12,9,14),fill=3); d.rectangle((7,12,8,13),fill=1)
        elif name=='peon_boar':
            d.rectangle((2,5,13,12),fill=3); d.rectangle((3,6,12,11),fill=1)
            d.rectangle((0,8,4,11),fill=2); d.point((2,7),3)
            d.rectangle((3,12,5,14),fill=3); d.rectangle((10,12,12,14),fill=3)
        else:
            d.rectangle((4,2,11,7),fill=3); d.rectangle((5,3,10,6),fill=2)
            d.point((6,4),3); d.point((9,4),3)
            d.rectangle((3,8,12,13),fill=3); d.rectangle((4,9,11,12),fill=1)
            d.rectangle((4,14,6,15),fill=3); d.rectangle((9,14,11,15),fill=3)
            d.rectangle((1,9,2,12),fill=2); d.rectangle((13,9,14,12),fill=2)
            if name=='peon_kento':
                d.line((2,4,0,0),fill=3,width=2); d.line((13,4,15,0),fill=3,width=2)
                d.point((0,0),1); d.point((15,0),1); d.rectangle((6,6,9,8),fill=1)
            elif name=='peon_warlock':
                d.polygon([(8,0),(2,7),(3,14),(13,14),(14,7)],fill=3)
                d.rectangle((5,4,10,7),fill=2); d.point((6,5),0); d.point((9,5),0)
                d.line((14,4,14,15),fill=1); d.point((14,3),2)
            elif name=='peon_warrior':
                d.rectangle((0,7,4,10),fill=3); d.rectangle((11,7,15,10),fill=3)
                d.line((1,0,1,6),fill=1,width=2)
            elif name=='peon_thrall':
                d.rectangle((4,0,11,2),fill=3); d.rectangle((5,9,10,11),fill=2)
            else: d.rectangle((0,2,2,8),fill=1); d.line((1,6,1,13),fill=3)
        frames=Image.new('P',(16,96),0)
        for i in range(6):
            f=frame.copy()
            if i%3==1 and name!='peon_quest_marker':
                dd=ImageDraw.Draw(f); dd.rectangle((5,3,10,6),fill=2)
            if i>=3 and name not in ('peon_quest_marker','peon_boar'):
                dd=ImageDraw.Draw(f); dd.point((4,15),0); dd.point((10,15),0)
            frames.paste(f,(0,i*16))
        if name in ('peon_quest_marker','peon_sleeping'): frames=frames.crop((0,0,16,16))
        indexed(f'gfx/sprites/{name}.png',frames)
    # Battle art is drawn from the technical ASCII source, never the AI mockup.
    from build_peon_sprite import IDLE, PIXELS
    for species,directions,count in [('machop',('down','up'),4),('rattata',None,5)]:
        for view in ('front','back'):
            canvas=Image.new('P',(40,40*count),0) if view=='front' else Image.new('P',(48,48),0)
            if species=='machop':
                f=Image.new('P',(16,16),0)
                for y,row in enumerate(IDLE[directions[view=='back']]):
                    for x,c in enumerate(row): f.putpixel((x,y),PIXELS[c])
            else:
                f=Image.new('P',(16,16),0); dd=ImageDraw.Draw(f)
                dd.rectangle((2,5,13,12),fill=3); dd.rectangle((3,6,12,11),fill=1)
                dd.rectangle((0,8,4,11),fill=2); dd.point((2,7),3)
                dd.rectangle((3,12,5,14),fill=3); dd.rectangle((10,12,12,14),fill=3)
            scale=2 if view=='front' else 3
            f=f.resize((16*scale,16*scale),Image.Resampling.NEAREST)
            for i in range(count if view=='front' else 1):
                canvas.paste(f,(4 if view=='front' else 0,i*40+6 if view=='front' else 0))
            colors=[255,255,255,214,160,96,88,160,40,0,0,0]
            canvas.putpalette(colors+[0]*756)
            canvas.save(ROOT/f'gfx/pokemon/{species}/{view}.png')

if __name__=='__main__': main()
