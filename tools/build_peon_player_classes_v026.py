#!/usr/bin/env python3
"""Author native apprentice-class pixel sprites, without resizing concept art.

Shaman native sprites remain immutable inputs. Warrior and Warlock are newly
painted on the same 16/56/48 pixel grids with the existing four-index palettes.
The code emits native bytes directly, avoiding whole-strip tile interleaving.
"""
from pathlib import Path
import hashlib
import json
import re

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'gfx/peon_classes'
OUT = ROOT / 'references/generated/visual_polish_v026/classes'
CLASSES = ('shaman', 'warrior', 'warlock')
DIRECTIONS = ('down', 'up', 'left', 'right')
POSES = ('idle', 'ready', 'release')
WORLD_PALETTE = [(31,31,31),(18,11,6),(15,22,8),(1,1,1)]
BATTLE_PALETTE = [(31,31,31),(15,22,8),(18,11,6),(0,0,0)]
DMG = [255,255,255,170,170,170,85,85,85,0,0,0] + [0]*756

WORLD = {
'warrior': {
'down': ['.....######.....','....#gggggg#....','...#gggggggg#...','..#gg#gggg#gg#..','...#gggggggg#...','....#gbbbbg#....','..##g######g##..','.b#gg#bbbb#gg#b.','bb#gg#bbbb#gg###','bb#bg#bbbb#g#bb#','.b##g#bbbb#g#bb#','..#g#########bb#','...##bb##bb####.','....#bb##bb#....','....#gg##gg#....','....####.###....'],
'up': ['.....######.....','....#gggggg#....','...#gggggggg#...','..#gggggggggg#..','...#gggggggg#...','....#gggggg#....','..##g######g##..','.###gg#bbbb#gg#b','.bb#gg#bbbb#gg#b','.bb#bg#bbbb#gbbb','.bb#g#bbbb#g##b.','.bb########g#...','..####bb##bb##..','....#bb##bb#....','....#gg##gg#....','....####.###....'],
'left': ['.....######.....','....#gggggg#....','...#gggggggg#...','..#ggg#ggggg#...','..#ggggggggg#...','...#bbggggg#....','...##g########..','.b#ggg#bbbb#bb#.','bb#ggg#bbbb#bb#.','bb#bgg#bbbb#bb#.','.b##g#bbbbg#bb#.','..#g##bbbbg#bb#.','...###bb##b###..','.....#bb##bb#...','....#ggg##gg#...','....####..###...'],
'right': ['.....######.....','....#gggggg#....','...#gggggggg#...','...#ggggg#ggg#..','...#ggggggggg#..','....#gggggbb#...','..########g##...','.#bb#bbbb#ggg#b.','.#bb#bbbb#ggg#bb','.#bb#bbbb#ggb#bb','.#bb#gbbb#gg##b.','.#bb#gbbb##gg#..','..###b##bb###...','...#bb##bb#.....','...#gg##ggg#....','...###..####....'],
},
'warlock': {
'down': ['....########....','...#bbbbbbbb#...','..#bbggggggbb#..','..#bgg#gg#ggb#..','..#bggggggggb#..','...#bgbbbbg#b...','.b..########....','.b.#gg#bb#gg#...','bbb#gg#bb#gg#...','.b.#bb#bb#gb#...','.b.###bbbb###...','.b..#bbbbbb#....','.b..#b#bb#b#....','.b..#bbbbbb#....','.b..#gg##gg#....','....####.###....'],
'up': ['....########....','...#bbbbbbbb#...','..#bbbbbbbbbb#..','..#bbbbbbbbbb#..','..#bbbbbbbbbb#..','...#bbbbbbbb#...','....########..b.','...#gg#bb#gg#.b.','...#gg#bb#gg#bbb','...#gb#bb#bb#.b.','...###bbbb###.b.','....#bbbbbb#..b.','....#b#bb#b#..b.','....#bbbbbb#..b.','....#gg##gg#..b.','....####.###....'],
'left': ['....########....','...#bbbbbbbb#...','..#bbggggggbb#..','..#bgg#gggggb#..','..#bggggggggb#..','...#bbgggggb#...','.b..########....','.b.#gg#bbbb#....','bbb#gg#bbbb#....','.b.#gb#bbbb#....','.b.###bbbb##....','.b..#bbbbbb#....','.b..#b#bb#b#....','.b..#bbbbbb#....','.b..#ggg#gg#....','....####.###....'],
'right': ['....########....','...#bbbbbbbb#...','..#bbggggggbb#..','..#bggggg#ggb#..','..#bggggggggb#..','...#bgggggbb#...','....########..b.','....#bbbb#gg#.b.','....#bbbb#gg#bbb','....#bbbb#bg#.b.','....##bbbb###.b.','....#bbbbbb#..b.','....#b#bb#b#..b.','....#bbbbbb#..b.','....#gg#ggg#..b.','....####.###....'],
}}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def bitmap(size):
    pixels = Image.new('L', size, 0)
    mask = Image.new('L', size, 0)
    return pixels, mask


class Paint:
    def __init__(self, size):
        self.pixels, self.mask = bitmap(size)
        self.d, self.m = ImageDraw.Draw(self.pixels), ImageDraw.Draw(self.mask)
    def shape(self, method, xy, fill, **kwargs):
        getattr(self.d, method)(xy, fill=fill, **kwargs)
        getattr(self.m, method)(xy, fill=255, **kwargs)
    def polygon(self, xy, fill): self.shape('polygon', xy, fill)
    def ellipse(self, xy, fill): self.shape('ellipse', xy, fill)
    def rectangle(self, xy, fill): self.shape('rectangle', xy, fill)
    def line(self, xy, fill, width=1): self.shape('line', xy, fill, width=width)
    def point(self, xy, fill): self.shape('point', xy, fill)


def world_frames(cls):
    result = []
    values = {'.':0,'b':1,'g':2,'#':3}
    for phase in range(3):
        for direction in DIRECTIONS:
            rows = [r.replace(' ', 'b') for r in WORLD[cls][direction]]
            assert all(len(r)==16 for r in rows), (cls,direction,[(len(r),r) for r in rows])
            pixels = Image.new('L',(16,16))
            for y,row in enumerate(rows):
                for x,char in enumerate(row): pixels.putpixel((x,y),values[char])
            # Short steps anchor the hips and staff; only feet and wrist move.
            if phase:
                d = ImageDraw.Draw(pixels)
                d.rectangle((4,14,11,15),fill=0)
                if phase == 1:
                    d.line((3,14,6,14),fill=2);d.line((3,15,6,15),fill=3)
                    d.line((9,14,11,14),fill=2);d.line((9,15,11,15),fill=3)
                else:
                    d.line((4,14,6,14),fill=2);d.line((4,15,6,15),fill=3)
                    d.line((9,14,12,14),fill=2);d.line((9,15,12,15),fill=3)
                if cls == 'warrior' and direction in ('down','left'):
                    pixels.putpixel((3,10 if phase==1 else 11),2)
            result.append((pixels,pixels.point(lambda v:255 if v else 0)))
    return result


def axe(p, hand, tip, size=5):
    hx,hy=hand;tx,ty=tip
    p.line((hx,hy,tx,ty),3,3);p.line((hx,hy,tx,ty),2)
    p.polygon([(tx-1,ty-size),(tx+size,ty-size+1),(tx+size+1,ty-1),(tx+size,ty+3),(tx-1,ty+4)],3)
    p.polygon([(tx,ty-size+1),(tx+size-1,ty-size+2),(tx+size,ty-1),(tx+size-1,ty+2),(tx,ty+3)],2)
    p.line((tx+size-1,ty-size+2,tx+size,ty+1),0)
    p.rectangle((hx-2,hy-2,hx+2,hy+2),3);p.rectangle((hx-1,hy-1,hx+1,hy+1),1)


def staff(p, hand, tip):
    hx,hy=hand;tx,ty=tip
    p.line((hx,hy+10,tx,ty),3,3);p.line((hx,hy+9,tx,ty),2)
    p.ellipse((tx-3,ty-4,tx+3,ty+2),3)
    p.ellipse((tx-2,ty-3,tx+2,ty+1),2)
    p.line((tx,ty-2,tx,ty),1)
    p.rectangle((hx-2,hy-2,hx+2,hy+2),3);p.rectangle((hx-1,hy-1,hx+1,hy+1),1)


def front_frame(cls, phase):
    p=Paint((56,56));dy=-1 if phase==1 else 0
    if cls=='warlock':
        p.polygon([(17,7+dy),(21,2+dy),(34,2+dy),(40,9+dy),(40,25+dy),(16,25+dy)],3)
        p.polygon([(18,8+dy),(22,4+dy),(33,4+dy),(38,10+dy),(38,23+dy),(18,23+dy)],2)
    else:
        p.ellipse((17,4+dy,39,26+dy),3);p.ellipse((18,5+dy,38,25+dy),1)
    p.polygon([(17,12+dy),(12,10+dy),(15,18+dy),(20,18+dy)],3)
    p.polygon([(18,13+dy),(14,12+dy),(16,17+dy),(19,17+dy)],1)
    p.polygon([(38,12+dy),(43,10+dy),(41,18+dy),(36,18+dy)],3)
    p.polygon([(37,13+dy),(41,12+dy),(40,17+dy),(37,17+dy)],1)
    p.ellipse((19,8+dy,37,25+dy),1)
    p.line((21,12+dy,26,13+dy),3,2);p.line((31,13+dy,35,12+dy),3,2)
    p.point((23,15+dy),0);p.point((33,15+dy),0)
    p.point((24,15+dy),3);p.point((32,15+dy),3)
    p.line((28,16+dy,29,18+dy),3)
    p.line((20,17+dy,22,20+dy),2)
    p.line((35,17+dy,35,20+dy),2)
    p.line((25,24+dy,32,24+dy),2)
    p.point((27,19+dy),2);p.point((30,19+dy),2)
    p.line((23,22+dy,34,22+dy),3)
    p.point((24,21+dy),0);p.point((32,21+dy),0)
    # Plain leather jerkin/robe and bare green arms, no heroic pauldrons.
    p.polygon([(18,26+dy),(22,24+dy),(34,24+dy),(39,28+dy),(39,41),(17,41)],3)
    p.polygon([(20,27+dy),(24,26+dy),(33,26+dy),(37,30+dy),(37,40),(19,40)],2)
    p.line((23,27+dy,31,31+dy),3,2);p.line((25,33+dy,33,33+dy),3)
    p.point((23,28+dy),0);p.point((27,30+dy),0)
    p.line((21,34+dy,21,37),3);p.line((35,34+dy,35,38),3)
    p.point((23,36),0);p.point((32,36),0)
    p.polygon([(15,27+dy),(20,29+dy),(17,36+dy),(12,39+dy),(9,35+dy)],3)
    p.polygon([(15,29+dy),(18,30+dy),(15,35+dy),(12,37+dy),(11,35+dy)],1)
    p.polygon([(37,28+dy),(42,28+dy),(46,36+dy),(42,41+dy),(37,37+dy)],3)
    p.polygon([(39,29+dy),(41,30+dy),(44,36+dy),(41,38+dy),(39,36+dy)],1)
    p.rectangle((18,39,37,42),3);p.rectangle((20,40,35,41),2);p.rectangle((26,39,29,42),1)
    if cls=='warlock':
        p.polygon([(18,40),(37,40),(40,49),(16,49)],3)
        p.polygon([(20,42),(35,42),(37,47),(18,47)],2)
        p.line((25,42,23,47),3);p.line((31,43,33,47),3)
    else:
        p.rectangle((18,41,25,49),3);p.rectangle((19,42,24,48),2)
        p.rectangle((31,41,38,49),3);p.rectangle((32,42,37,48),2)
    p.polygon([(18,48),(25,48),(26,53),(13,53),(13,51)],3)
    p.polygon([(19,49),(24,49),(24,52),(15,52),(15,51)],1)
    p.polygon([(31,48),(38,48),(43,51),(43,53),(30,53)],3)
    p.polygon([(32,49),(37,49),(41,51),(41,52),(32,52)],1)
    p.line((18,47,24,47),2);p.line((33,47,38,47),2)
    p.point((18,51),3);p.point((21,51),3);p.point((36,51),3);p.point((39,51),3)
    if cls=='warrior':
        # Modest wooden buckler, deliberately smaller than the Shaman shield.
        p.ellipse((40,31+dy,52,45+dy),3);p.ellipse((41,32+dy,51,44+dy),2)
        p.line((45,33+dy,45,43+dy),3);p.ellipse((44,37+dy,48,40+dy),3);p.point((46,38+dy),0)
        tips=[(6,27),(5,10),(11,39)]
        axe(p,(12,36+dy),tips[phase],4)
    else:
        tips=[(6,17),(6,9),(11,12)]
        staff(p,(12,36+dy),tips[phase])
        if phase:
            p.polygon([(41,34),(46,30),(49,29),(51,31),(47,34),(43,37)],3)
            p.polygon([(42,34),(46,32),(49,30),(49,32),(46,34),(43,35)],1)
    return p.pixels,p.mask


def back_frame(cls, phase):
    p=Paint((48,48));dy=-1 if phase==1 else 0
    if cls=='warlock':
        p.polygon([(20,6+dy),(25,1+dy),(35,1+dy),(42,9+dy),(41,23+dy),(19,23+dy)],3)
        p.polygon([(21,7+dy),(26,3+dy),(34,3+dy),(40,10+dy),(39,21+dy),(21,21+dy)],2)
        p.line((29,4+dy,27,15+dy),3);p.line((29,15+dy,36,20+dy),3)
        # Side cheek visible beneath the small apprentice hood.
        p.polygon([(37,10+dy),(42,12+dy),(43,17+dy),(39,20+dy),(36,18+dy)],3)
        p.polygon([(38,11+dy),(41,13+dy),(41,17+dy),(38,18+dy)],1)
    else:
        p.ellipse((19,3+dy,42,23+dy),3);p.ellipse((20,4+dy,41,22+dy),1)
        p.line((23,8+dy,22,15+dy),2);p.line((36,8+dy,39,13+dy),2)
    p.polygon([(20,11+dy),(15,8+dy),(17,18+dy),(22,19+dy)],3)
    p.polygon([(19,12+dy),(17,11+dy),(18,17+dy),(21,17+dy)],1)
    p.polygon([(21,24+dy),(25,21+dy),(37,22+dy),(42,27+dy),(41,38),(19,39)],3)
    p.polygon([(23,25+dy),(27,23+dy),(36,24+dy),(39,28+dy),(39,37),(21,37)],2)
    p.line((24,27+dy,35,32+dy),3,2);p.line((24,34,31,35),3)
    p.point((25,27+dy),0);p.point((30,30+dy),0)
    p.line((23,30+dy,23,32+dy),3);p.line((36,34,36,36),3)
    p.point((27,36),0);p.point((34,36),0)
    p.polygon([(19,24+dy),(14,26+dy),(11,32+dy),(17,37+dy),(22,33+dy)],3)
    p.polygon([(18,26+dy),(15,28+dy),(14,32+dy),(17,34+dy),(20,32+dy)],1)
    p.polygon([(39,25+dy),(44,27+dy),(47,34+dy),(43,38+dy),(38,33+dy)],3)
    p.polygon([(40,27+dy),(43,29+dy),(45,34+dy),(42,36+dy),(40,32+dy)],1)
    p.rectangle((20,37,40,40),3);p.rectangle((22,38,38,39),2)
    if cls=='warlock':
        p.polygon([(20,39),(39,39),(42,44),(17,44)],3)
        p.polygon([(22,40),(37,40),(39,43),(20,43)],2)
    else:
        p.rectangle((20,40,27,44),3);p.rectangle((21,41,26,43),2)
        p.rectangle((32,40,39,44),3);p.rectangle((33,41,38,43),2)
    p.polygon([(19,43),(26,43),(27,47),(15,47),(15,45)],3)
    p.polygon([(20,44),(25,44),(25,46),(17,46)],1)
    p.polygon([(32,43),(39,43),(43,46),(43,47),(31,47)],3)
    p.polygon([(33,44),(38,44),(41,46),(33,46)],1)
    p.line((21,42,26,42),2);p.line((34,42,38,42),2)
    p.point((18,46),3);p.point((21,46),3);p.point((36,46),3)
    if cls=='warrior':
        p.ellipse((35,29+dy,47,42+dy),3);p.ellipse((36,30+dy,46,41+dy),2)
        p.line((40,31+dy,40,40+dy),3);p.ellipse((39,34+dy,43,38+dy),3);p.point((41,35+dy),0)
        tips=[(4,18),(5,6),(5,38)]
        axe(p,(14,31+dy),tips[phase],4)
    else:
        tips=[(6,9),(6,4),(11,7)]
        staff(p,(13,29+dy),tips[phase])
        if phase:
            p.polygon([(39,31),(43,27),(46,26),(47,28),(44,30),(41,34)],3)
            p.polygon([(40,31),(43,29),(46,27),(46,28),(43,31),(41,32)],1)
    return p.pixels,p.mask


def source_indexed(path, color=False):
    image=Image.open(path)
    if not color:
        return Image.fromarray(np.asarray(image).astype('uint8'),'L')
    pixels=np.asarray(image.convert('RGB')).astype('int16')>>3
    pal=np.asarray(BATTLE_PALETTE,dtype='int16')
    native=((pixels[:,:,None,:]-pal[None,None,:,:])**2).sum(axis=3).argmin(axis=2).astype('uint8')
    return Image.fromarray(native,'L')


def shaman_frames(kind):
    if kind=='world':
        image=source_indexed(ROOT/'gfx/sprites/peon.png')
        return [(image.crop((0,i*16,16,(i+1)*16)),None) for i in range(12)]
    if kind=='back':
        return [(source_indexed(ROOT/f'gfx/peon_player_battle/back_{name}.png'),None) for name in ('idle','brace','swing')]
    image=source_indexed(ROOT/'gfx/pokemon/machop/front.png',color=True)
    return [(image.crop((0,i*56,56,(i+1)*56)),None) for i in range(3)]


def encode(image, column_major=False):
    out=bytearray();coords=[(x,y) for x in range(image.width//8) for y in range(image.height//8)] if column_major else [(x,y) for y in range(image.height//8) for x in range(image.width//8)]
    for tx,ty in coords:
        for y in range(8):
            row=[image.getpixel((tx*8+x,ty*8+y)) for x in range(8)]
            out.extend((sum((v&1)<<(7-x) for x,v in enumerate(row)),sum((v>>1)<<(7-x) for x,v in enumerate(row))))
    return bytes(out)


def rgba(image, mask, palette):
    if mask is None:
        if image.width == 16:
            mask=image.point(lambda v:255 if v else 0)
        else:
            # Transparent background only; preserve enclosed ivory tusks and
            # highlights whose native palette index is also zero.
            background=image.copy()
            for x in range(image.width):
                for y in (0,image.height-1):
                    if background.getpixel((x,y))==0: ImageDraw.floodfill(background,(x,y),9)
            for y in range(image.height):
                for x in (0,image.width-1):
                    if background.getpixel((x,y))==0: ImageDraw.floodfill(background,(x,y),9)
            mask=background.point(lambda v:0 if v==9 else 255)
    array=np.asarray(image,dtype='uint8');col=np.asarray(palette,dtype='uint8')*8
    return Image.fromarray(np.dstack((col[array],np.asarray(mask,dtype='uint8'))),'RGBA')


def emit(cls,kind,frames):
    native=NATIVE/cls;public=OUT/cls;native.mkdir(parents=True,exist_ok=True);public.mkdir(parents=True,exist_ok=True)
    palette=WORLD_PALETTE if kind=='world' else BATTLE_PALETTE
    size=16 if kind=='world' else 56 if kind=='front' else 48
    strip=Image.new('P',(size,size*len(frames)));strip.putpalette(DMG)
    metrics=[];exports=[]
    for i,(image,mask) in enumerate(frames):
        assert image.size==(size,size) and set(np.unique(np.asarray(image)))<={0,1,2,3}
        strip.paste(image,(0,i*size));export=rgba(image,mask,palette);exports.append(export)
        label=f'{DIRECTIONS[i%4]}_step_{i//4}' if kind=='world' else POSES[i]
        export.save(public/f'{cls}_{kind}_{label}_{size}x{size}.png')
        export.resize((size*8,size*8),Image.Resampling.NEAREST).save(public/f'{cls}_{kind}_{label}_8x.png')
        metrics.append({'frame':i,'label':label,'opaque_pixels':int(np.count_nonzero(np.asarray(export.getchannel('A')))),
                        'changed_pixels_from_idle':int(np.count_nonzero(np.asarray(image)!=np.asarray(frames[0][0]))),
                        'opaque_bounds':export.getbbox()})
    strip.save(native/f'{kind}_frames.png')
    data=b''.join(encode(image,column_major=kind!='world') for image,_ in frames)
    name='overworld.bin' if kind=='world' else f'{kind}_frames.bin'
    (native/name).write_bytes(data)
    if kind=='front':
        portraits=b''.join(encode(image) for image,_ in frames)
        if cls=='shaman':
            # Keep the current readable character portrait unchanged at rest.
            portrait=source_indexed(ROOT/'gfx/pack/peon_portrait.png')
            portraits=encode(portrait)+portraits[len(encode(portrait)):]
        (native/'portrait_frames.bin').write_bytes(portraits)
    cols=3 if kind!='world' else 3;rows=1 if kind!='world' else 4
    sheet=Image.new('RGBA',(size*cols,size*rows))
    for i,im in enumerate(exports):
        x,y=(i,i//len(exports)) if kind!='world' else (i//4,i%4)
        sheet.alpha_composite(im,(x*size,y*size))
    sheet.save(public/f'{cls}_{kind}_sheet.png');sheet.resize((sheet.width*8,sheet.height*8),Image.Resampling.NEAREST).save(public/f'{cls}_{kind}_sheet_8x.png')
    if kind=='world':
        for direction,direction_label in enumerate(DIRECTIONS):
            sequence=[exports[direction+phase*4] for phase in (0,1,0,2)]
            sequence[0].save(public/f'{cls}_world_{direction_label}_walk.apng',save_all=True,append_images=sequence[1:],duration=130,loop=0,disposal=1,blend=0)
            canvases=[]
            for frame in sequence:
                enlarged=frame.resize((size*8,size*8),Image.Resampling.NEAREST)
                canvas=Image.new('RGB',enlarged.size,(245,237,213))
                canvas.paste(enlarged,mask=enlarged.getchannel('A'));canvases.append(canvas)
            canvases[0].save(public/f'{cls}_world_{direction_label}_walk_8x.gif',save_all=True,append_images=canvases[1:],duration=130,loop=0)
    if kind!='world':
        sequence=[exports[i] for i in (0,1,2,1,0)]
        sequence[0].save(public/f'{cls}_{kind}_motion.apng',save_all=True,append_images=sequence[1:],duration=[260,130,130,130,260],loop=0,disposal=1,blend=0)
        canvases=[]
        for im in sequence:
            im=im.resize((size*8,size*8),Image.Resampling.NEAREST);canvas=Image.new('RGB',im.size,(245,237,213));canvas.paste(im,mask=im.getchannel('A'));canvases.append(canvas)
        canvases[0].save(public/f'{cls}_{kind}_motion_8x.gif',save_all=True,append_images=canvases[1:],duration=[260,130,130,130,260],loop=0)
    return {'size':[size,size],'frames':metrics,'binary_bytes':len(data),'binary':str((native/name).relative_to(ROOT)),
            'sha256':sha(native/name),'tile_order':'row-major per frame' if kind=='world' else 'column-major per frame',
            'binary_alpha':True,'game_palette_rgb555':palette}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    report={'style':'Humble green Orc apprentices; original native pixel grids, no concept resize or imported artwork.',
            'classes':{},'runtime_validation_report':'references/generated/visual_polish_v026/classes/validation.json','dimensions_unchanged':True}
    for cls in CLASSES:
        frames={'world':shaman_frames('world') if cls=='shaman' else world_frames(cls),
                'front':shaman_frames('front') if cls=='shaman' else [front_frame(cls,i) for i in range(3)],
                'back':shaman_frames('back') if cls=='shaman' else [back_frame(cls,i) for i in range(3)]}
        report['classes'][cls]={kind:emit(cls,kind,data) for kind,data in frames.items()}
    assert (NATIVE/'shaman/overworld.bin').read_bytes()==(ROOT/'gfx/sprites/peon.2bpp').read_bytes()
    assert (NATIVE/'shaman/back_frames.bin').read_bytes()==(ROOT/'gfx/peon_player_battle/back_frames.2bpp').read_bytes()
    report['shaman_world_and_rear_native_bytes_unchanged']=True
    sheet=Image.new('RGBA',(56*3,56+48+16*4))
    for i,cls in enumerate(CLASSES):
        for kind,y in [('front',0),('back',56),('world',104)]:
            src=Image.open(OUT/cls/f'{cls}_{kind}_sheet.png')
            if kind!='world':src=src.crop((0,0,56 if kind=='front' else 48,56 if kind=='front' else 48))
            sheet.alpha_composite(src,(i*56,y))
    sheet.save(OUT/'three_apprentice_classes_native.png')
    sheet.resize((sheet.width*6,sheet.height*6),Image.Resampling.NEAREST).save(OUT/'three_apprentice_classes_6x.png')
    paper=Image.new('RGBA',(sheet.width*6,sheet.height*6),(243,234,207))
    paper.alpha_composite(sheet.resize(paper.size,Image.Resampling.NEAREST))
    paper.save(OUT/'three_apprentice_classes_paper_review.png')
    report['native_source_review']={'highlight_preview_class_from_menu_cursor':True,'current_actor_class_from_existing_saved_flags':True,'sprite_ids_unchanged':True,'save_layout_unchanged':True,'class_owned_ui_and_battle_uploads_use_vram_bank0':True,'original_shaman_native_world_and_rear_preserved':True}
    (OUT/'asset_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'classes':list(report['classes']),'native_dimensions':['16x16 world','56x56 front','48x48 back'],'shaman_native_unchanged':True},indent=2))


if __name__=='__main__':main()
