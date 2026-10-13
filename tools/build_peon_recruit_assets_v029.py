#!/usr/bin/env python3
"""Original native recruitment artwork; no ROM IDs, maps or game state edits.

Uses shared pixel/tile primitives from v028 without invoking its generator or
writing any v028 output. All assets here belong to the independent v029 set.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw
import build_peon_player_classes_v028 as art

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT/'gfx/peon_recruits_v029'
OUT = ROOT/'references/generated/recruitment_v029/assets'
RECRUITS = ('earth_spirit', 'demon_imp', 'orc_grunt')
ENEMIES = ('orc_warlock', 'kolkar_archer', 'kolkar_melee')
ASSET_SETS = RECRUITS+ENEMIES
DIRECTIONS = ('down', 'up', 'left', 'right')
POSES = ('idle', 'ready', 'release')
PALETTES = {
    'earth_spirit': {'world': [(31,31,31),(18,12,6),(13,23,6),(1,1,1)],
                     'battle': [(31,31,31),(13,23,6),(18,12,6),(0,0,0)]},
    'demon_imp': {'world': [(31,31,31),(26,7,3),(31,26,14),(1,1,1)],
                  'battle': [(31,31,31),(26,7,3),(13,3,2),(0,0,0)]},
    'orc_grunt': {'world': [(31,31,31),(16,10,5),(12,21,6),(1,1,1)],
                  'battle': [(31,31,31),(12,21,6),(16,10,5),(0,0,0)]},
    'orc_warlock': {'world': [(31,31,31),(9,6,13),(13,22,8),(1,1,1)],
                    'battle': [(31,31,31),(13,22,8),(9,6,13),(0,0,0)]},
    'kolkar_archer': {'world': [(31,31,31),(22,15,8),(11,7,4),(1,1,1)],
                      'battle': [(31,31,31),(22,15,8),(11,7,4),(0,0,0)]},
    'kolkar_melee': {'world': [(31,31,31),(22,15,8),(11,7,4),(1,1,1)],
                     'battle': [(31,31,31),(22,15,8),(11,7,4),(0,0,0)]},
}

EARTH_WORLD = {
    'down': ['.....#######....','....#rrrrrrr#...','...#rrrrrrrrr#..',
             '..##r#grrgr#r##.','...#rrrrrrrrr#..','....##rrr###....',
             '.##...####...##.','#rr#.##rr##.#rr#','#rr##rrrrrr##rr#',
             '.##.#rrrrrr#.##.','....#rr##rr#....','...##rrrrrr##...',
             '..#rr##rr##rr#..','..#rr#....#rr#..','...##......##...','................'],
    'up': ['.....#######....','....#rrrrrrr#...','...#rr#rrrrrr#..',
           '..##rrrr#rrrr##.','...#rrr#rrrrr#..','....##rrr###....',
           '.##...####...##.','#rr#.##rr##.#rr#','#rr##rr#rrr##rr#',
           '.##.#rrrrrr#.##.','....#rr##rr#....','...##rrrrrr##...',
           '..#rr##rr##rr#..','..#rr#....#rr#..','...##......##...','................'],
    'left': ['.....#######....','....#rrrrrrr#...','...#rrrrrrrrr#..',
             '..#gr#rrrr#rr#..','..#rrrrrrrrrr#..','...##rrr#####...',
             '...##rrrr###....','..#rr##rrr#.....','..#rr#rrrr##....',
             '...###rrr#rr#...','....#rrrr#rr#...','...##rrr####....',
             '..#rr##rr#......','..#rr#..#rr#....','...##....##.....','................'],
    'right': ['.....#######....','....#rrrrrrr#...','...#rrrrrrrrr#..',
              '...#rr#rrrr#rg#.','...#rrrrrrrrrr#.','....#####rrr##..',
              '.....###rrrr##..','......#rrr##rr#.','.....##rrrr#rr#.',
              '....#rr#rrr###..','....#rr#rrrr#...','.....####rrr##..',
              '.......#rr##rr#.','.....#rr#..#rr#.','......##....##..','................'],
}
IMP_WORLD = {
    'down': ['..#........#....','...#......#.....','...########.....',
             '..#rrgrrgrr#....','..#rrrrrrrr#....','...#rr##rr#.....',
             '....######......','..##r#rr#r##....','.#rrr#rr#rrr#...',
             '..##r#rr#r##..#.','...#rrrrrr#..#..','....#rrrr#..#...',
             '.....#rr#..#....','....#r##r##.....','....##..##......','................'],
    'up': ['..#........#....','...#......#.....','...########.....',
           '..#rrrrrrrr#....','..#rrr#rrrr#....','...#rrrrrr#.....',
           '....######......','..##r#rr#r##....','.#rrr#rr#rrr#...',
           '..##r#rr#r##..#.','...#rr#rrr#..#..','....#rrrr#..#...',
           '.....#rr#..#....','....#r##r##.....','....##..##......','................'],
    'left': ['....#...#.......','.....#.#........','....######......',
             '...#grrrrr#.....','..#rrrrrrr#.....','...#grrrrr#.....',
             '....######......','...#r#rrr#......','..#rr#rrr##.....',
             '...###rrr#r#..#.','....#rrrr#r#.#..','.....#rr###.#...',
             '.....#rr#..#....','....#r##r##.....','....##..##......','................'],
    'right': ['.......#...#....','........#.#.....','......######....',
              '.....#rrrrrg#...','.....#rrrrrrr#..','.....#rrrrrg#...',
              '......######....','......#rrr#r#...','.....##rrr#rr#..',
              '.#..#r#rrr###...','..#.#r#rrrr#....','...#.###rr#.....',
              '....#..#rr#.....','.....##r##r#....','......##..##....','................'],
}


def world_frames(recruit):
    if recruit.startswith('kolkar_'):return kolkar_world(recruit)
    if recruit=='orc_warlock':return art.world_frames('warlock')
    if recruit == 'orc_grunt':
        frames = art.world_frames('warrior')
        for pixels, mask in frames:
            # A crewcut silhouette instead of the playable apprentice knot.
            for x in range(6,10): pixels.putpixel((x,0),0); mask.putpixel((x,0),0)
        return frames
    rows = EARTH_WORLD if recruit == 'earth_spirit' else IMP_WORLD
    result=[]; values={'.':0,'r':1,'g':2,'#':3}
    for phase in range(3):
        for direction in DIRECTIONS:
            assert len(rows[direction])==16 and all(len(row)==16 for row in rows[direction]),(recruit,direction)
            pixels=Image.new('L',(16,16))
            for y,row in enumerate(rows[direction]):
                for x,value in enumerate(row):pixels.putpixel((x,y),values[value])
            if phase:
                d=ImageDraw.Draw(pixels)
                d.rectangle((2,13,13,15),fill=0)
                if recruit=='earth_spirit':
                    for x,y in ((3,13),(10,14)) if phase==1 else ((4,14),(11,13)):
                        d.rectangle((x,y,x+2,min(y+1,15)),fill=3); d.point((x+1,y),fill=1)
                else:
                    for x,y in ((3,13),(8,14)) if phase==1 else ((5,14),(9,13)):
                        d.line((x,y,x+2,y),fill=1);d.line((x,min(y+1,15),x+2,min(y+1,15)),fill=3)
                    # Tail tip curls gently rather than moving the torso.
                    d.point((13 if direction!='right' else 2,10 if phase==1 else 11),fill=1)
            result.append((pixels,pixels.point(lambda v:255 if v else 0)))
    return result


def rock(p,x,y,w,h):
    if h<8:
        # Low foot fragments must not reuse a tall boulder's coordinates:
        # those would run outside the shard and create stray bright streaks.
        p.polygon([(x+2,y),(x+w-2,y),(x+w,y+2),(x+w-2,y+h),
                   (x+1,y+h),(x,y+2)],3)
        p.polygon([(x+3,y+1),(x+w-3,y+1),(x+w-2,y+2),
                   (x+w-3,y+h-1),(x+2,y+h-1)],2)
        p.point((x+3,y+1),0)
        return
    p.polygon([(x+3,y),(x+w-4,y),(x+w,y+4),(x+w-1,y+h-3),
               (x+w-5,y+h),(x+2,y+h-1),(x,y+h-4),(x,y+3)],3)
    p.polygon([(x+4,y+2),(x+w-5,y+2),(x+w-2,y+5),(x+w-3,y+h-4),
               (x+w-5,y+h-2),(x+3,y+h-3),(x+2,y+4)],2)
    p.line((x+4,y+2,x+5,y+2),0)
    p.point((x+2,y+5),0)
    p.line((x+4,y+h-3,x+w-5,y+h-2),3)
    p.polygon([(x+w-3,y+5),(x+w-3,y+h-4),(x+w-6,y+h-3),
               (x+w-5,y+h-5)],3)
    if w>12:
        p.line((x+w//2,y+4,x+w//2+1,y+7,x+w//2-1,y+9),3)
        p.point((x+w//2,y+8),2)


def earth_front(phase):
    p=art.Paint((56,56));dy=-1 if phase==1 else 0
    rock(p,16,25+dy,24,16)
    rock(p,20,39,8,12); rock(p,31,39,9,12)
    rock(p,14,48,13,5);rock(p,32,48,14,5)
    left=[(5,22),(7,11),(2,29)][phase]; right=[(41,24),(42,23),(40,18)][phase]
    rock(p,*left,10,14);rock(p,*right,10,14)
    rock(p,18,4+dy,21,18)
    p.line((22,11+dy,26,12+dy),3,2);p.line((32,12+dy,36,11+dy),3,2)
    p.rectangle((23,13+dy,25,14+dy),1);p.rectangle((32,13+dy,34,14+dy),1)
    p.line((25,18+dy,33,18+dy),3)
    p.line((26,29+dy,31,29+dy),1);p.point((28,31+dy),1)
    for x,y in ((9,45),(46,45),(8,50),(48,50)):p.point((x,y),2)
    return p.pixels,p.mask


def earth_back(phase):
    p=art.Paint((48,48));dy=-1 if phase==1 else 0
    rock(p,19,24+dy,22,16)
    rock(p,19,39,9,7);rock(p,32,39,10,7)
    rock(p,15,44,14,3);rock(p,33,44,12,3)
    left=[(6,23),(8,11),(3,29)][phase];right=[(39,24),(38,23),(36,17)][phase]
    rock(p,*left,9,13);rock(p,*right,8,13)
    rock(p,21,4+dy,22,18)
    p.line((38,11+dy,42,12+dy),3,2);p.rectangle((39,13+dy,41,14+dy),1)
    p.line((24,10+dy,25,15+dy),3)
    p.line((25,28+dy,34,31+dy),3)
    p.point((29,36),1)
    return p.pixels,p.mask


def imp_head(p,x,y,back=False):
    # Backwards-curved bone horns, angular muzzle and pointed ears.
    p.polygon([(x+1,y+5),(x-4,y+1),(x-2,y-4),(x+1,y-6),(x-1,y-1),(x+4,y+4)],3)
    p.polygon([(x+1,y+3),(x-2,y),(x-1,y-3),(x,y-3),(x,y),(x+3,y+4)],0)
    p.polygon([(x+14,y+5),(x+20,y+1),(x+19,y-4),(x+16,y-6),(x+17,y-1),(x+12,y+4)],3)
    p.polygon([(x+15,y+3),(x+18,y),(x+17,y-3),(x+17,y-2),(x+16,y+1),(x+13,y+4)],0)
    p.polygon([(x+2,y+2),(x+12,y+1),(x+16,y+7),(x+14,y+15),
               (x+10,y+18),(x+4,y+17),(x,y+13),(x-1,y+7)],3)
    p.polygon([(x+3,y+4),(x+11,y+3),(x+14,y+8),(x+12,y+14),
               (x+9,y+16),(x+4,y+15),(x+1,y+11),(x+1,y+7)],1)
    p.line((x+2,y+8,x+3,y+13),2,2);p.line((x+5,y+15,x+9,y+16),2)
    p.polygon([(x,y+8),(x-5,y+5),(x-3,y+11),(x+2,y+12)],3)
    p.line((x-3,y+7,x,y+10),1,2)
    p.polygon([(x+15,y+8),(x+21,y+5),(x+18,y+11),(x+13,y+12)],3)
    p.line((x+18,y+7,x+15,y+10),1,2)
    if back:
        p.line((x+5,y+5,x+4,y+10),2)
        p.line((x+12,y+8,x+15,y+9),3,2);p.point((x+14,y+10),0)
        p.point((x+14,y+13),0)
    else:
        p.line((x+3,y+7,x+6,y+8),3,2);p.line((x+9,y+8,x+12,y+7),3,2)
        p.point((x+5,y+9),0);p.point((x+10,y+9),0)
        p.line((x+6,y+12,x+8,y+12),2)
        p.line((x+4,y+14,x+11,y+14),3)
        p.point((x+5,y+13),0);p.point((x+10,y+13),0)


def imp_picture(phase,back=False):
    size=48 if back else 56;p=art.Paint((size,size));x=26 if back else 25;y=7 if back else 8
    dy=-1 if phase==1 else 0
    # A thin mischievous demon: long forearms, bent knees and a curling tail.
    tailx=45 if back else 50
    p.line((x+8,35,tailx-3,39,tailx,32,tailx-2,28),3,3)
    p.line((x+8,35,tailx-3,38,tailx-1,32,tailx-2,29),1)
    p.polygon([(tailx-3,28),(tailx,27),(tailx-1,31)],3);p.point((tailx-1,28),1)
    p.polygon([(x+1,25+dy),(x+10,24+dy),(x+14,31),(x+11,39),(x+2,39),(x-1,31)],3)
    p.polygon([(x+2,27+dy),(x+9,26+dy),(x+11,31),(x+9,37),(x+3,37),(x+1,31)],1)
    p.line((x+4,29+dy,x+5,35),2,2);p.line((x+9,28+dy,x+9,31),0)
    p.line((x+2,38,x-1,43,x+1,size-3),3,5)
    p.line((x+2,38,x,43,x+1,size-4),1,2)
    p.line((x+10,38,x+13,42,x+11,size-3),3,5)
    p.line((x+10,38,x+12,42,x+11,size-4),1,2)
    p.line((x-3,size-2,x+3,size-2),3,2);p.line((x+9,size-2,x+16,size-2),3,2)
    for fx in (x-2,x,x+10,x+12,x+14):p.point((fx,size-3),0)
    left=[(x-8,35),(x-11,21),(x-9,35)][phase]
    right=[(x+19,35),(x+20,31),(x+20,19)][phase]
    for start,hand in (((x+1,27+dy),left),((x+11,26+dy),right)):
        hx,hy=hand;p.line((*start,hx,hy),3,4);p.line((*start,hx,hy),1,2)
        p.line((hx-2,hy,hx+2,hy),3,3)
        for fx in (hx-2,hx,hx+2):p.line((fx,hy,fx,hy+3),1);p.point((fx,hy+4),0)
    imp_head(p,x-1,y+dy,back)
    if back:p.line((x+3,31,x+8,34),2)
    return p.pixels,p.mask


def grunt_picture(phase,back=False):
    pixels,mask=(art.back_frame if back else art.front_frame)('warrior',phase)
    d,m=ImageDraw.Draw(pixels),ImageDraw.Draw(mask)
    dy=-1 if phase==1 else 0
    if not back:
        # Close-cropped novice hair, different from the main Peon's top knot.
        d.rectangle((21,2+dy,35,7+dy),fill=0);m.rectangle((21,2+dy,35,7+dy),fill=0)
        d.line((23,8+dy,33,8+dy),fill=3);m.line((23,8+dy,33,8+dy),fill=255)
        d.line((24,9+dy,31,9+dy),fill=2);m.line((24,9+dy,31,9+dy),fill=255)
    else:
        d.rectangle((28,0,33,2),fill=0);m.rectangle((28,0,33,2),fill=0)
    d.point((24,35),fill=3);d.point((25,35),fill=0)
    return pixels,mask


def picture(recruit,kind,phase):
    if recruit.startswith('kolkar_'):return kolkar_picture(recruit,phase,kind=='back')
    if recruit=='orc_warlock':
        pixels,mask=(art.back_frame if kind=='back' else art.front_frame)('warlock',phase)
        d=ImageDraw.Draw(pixels)
        if kind=='front':
            dy=-1 if phase==1 else 0
            d.line((20,14+dy,24,16+dy),fill=3);d.line((32,16+dy,35,14+dy),fill=3)
            d.line((24,23+dy,32,23+dy),fill=3)
        return pixels,mask
    if recruit=='earth_spirit':return (earth_back if kind=='back' else earth_front)(phase)
    if recruit=='demon_imp':return imp_picture(phase,kind=='back')
    return grunt_picture(phase,kind=='back')


def kolkar_world(recruit):
    frames=[]
    for phase in range(3):
        for direction in DIRECTIONS:
            p=art.Paint((16,16));right=direction=='right'
            # Four actual legs under a horizontal horse body. A 16px sprite
            # must not become a humanoid with a decorative tail.
            p.polygon([(3,8),(11,7),(14,9),(14,12),(4,12),(2,10)],3)
            p.polygon([(4,9),(11,8),(13,10),(12,11),(4,11)],2)
            for n,x in enumerate((4,7,10,13)):
                shift=0 if phase==0 else (1 if (n+phase)%2 else -1)
                p.line((x,12,x+shift,14),3)
                p.point((x,12),2);p.line((x+shift-1,15,x+shift,15),3)
            p.line((13,9,15,8,15,11),3)
            x=7 if right else 5
            p.rectangle((x-1,4,x+3,9),3);p.rectangle((x,5,x+2,8),1)
            p.rectangle((x-1,0,x+3,4),3);p.rectangle((x,1,x+2,3),1)
            p.line((x,0,x+2,0),2)
            if direction!='up':p.point((x+2 if right else x,2),3)
            else:p.rectangle((x,1,x+2,2),2)
            if recruit=='kolkar_archer':
                bx=12 if right else 1
                p.line((bx,4,bx+1,6,bx,9),3);p.line((bx,5,bx,8),2)
                p.line((x,6,bx,6),1)
            else:
                bx=12 if right else 1
                p.line((bx,3,bx+1,10),3);p.point((bx,3),1)
                p.line((x,6,bx,6),1)
            # No visible index0 pigments are used by world hardware objects.
            pixels=p.pixels;frames.append((pixels,pixels.point(lambda v:255 if v else 0)))
    return frames


def kolkar_picture(recruit,phase,back=False):
    size=48 if back else 56;p=art.Paint((size,size));dy=-1 if phase==1 else 0
    hx=17 if back else 21;hy=3 if back else 4
    left=13 if back else 17;right=43 if back else 50
    bodyy=29 if back else 32;bottom=size-3
    # Horse barrel, haunch and four separately visible hocks/hooves.
    p.polygon([(left,bodyy+1),(left+7,bodyy-2),(right-6,bodyy-2),(right,bodyy+3),
               (right-1,bodyy+10),(right-8,bodyy+12),(left+3,bodyy+10)],3)
    p.polygon([(left+3,bodyy+2),(left+8,bodyy),(right-7,bodyy),(right-3,bodyy+4),
               (right-4,bodyy+8),(right-9,bodyy+10),(left+5,bodyy+8)],2)
    p.line((left+7,bodyy+1,right-8,bodyy+1),1)
    p.line((right-8,bodyy+3,right-6,bodyy+7),3)
    for n,x in enumerate((left+5,left+11,right-9,right-2)):
        shift=0 if phase!=2 else (-2 if n%2==0 else 1)
        endx=x+shift-1 if n%2==0 else x+shift+1
        p.line((x,bodyy+8,endx,bottom-2),3,3)
        p.line((x,bodyy+8,endx,bottom-3),2)
        p.line((endx-2,bottom,endx+1,bottom),3,2)
        if n%2==0:p.point((endx-1,bottom-1),0)
    tailx=size-2
    p.line((right-1,bodyy+2,tailx,bodyy+1,tailx,bodyy+8),3,2)
    p.line((tailx-1,bodyy+7,tailx-1,bodyy+10),2)
    # Humanoid upper body rises from the front horse shoulder, with a plain
    # leather harness rather than Orc armor or a generic bipedal pose.
    p.polygon([(hx-5,hy+14+dy),(hx,hy+11+dy),(hx+9,hy+12+dy),
               (hx+14,hy+18+dy),(hx+10,bodyy+5),(hx-1,bodyy+4)],3)
    p.polygon([(hx-3,hy+16+dy),(hx+1,hy+13+dy),(hx+8,hy+14+dy),
               (hx+11,hy+19+dy),(hx+8,bodyy+2),(hx+1,bodyy+1)],1)
    p.line((hx,hy+16+dy,hx+7,hy+21+dy),2,3)
    p.line((hx+7,hy+21+dy,hx+5,bodyy+2),2,2)
    p.rectangle((hx-1,bodyy,hx+9,bodyy+2),3);p.point((hx+4,bodyy+1),0)
    p.polygon([(hx-1,hy+1+dy),(hx+7,hy+dy),(hx+11,hy+5+dy),
               (hx+9,hy+12+dy),(hx+2,hy+14+dy),(hx-3,hy+9+dy)],3)
    p.polygon([(hx,hy+3+dy),(hx+6,hy+2+dy),(hx+8,hy+6+dy),
               (hx+7,hy+11+dy),(hx+2,hy+12+dy),(hx-1,hy+8+dy)],1)
    p.polygon([(hx-1,hy+2+dy),(hx+1,hy+dy),(hx+7,hy+dy),
               (hx+9,hy+3+dy),(hx+5,hy+4+dy),(hx+1,hy+3+dy)],2)
    p.line((hx-2,hy+5+dy,hx-3,hy+10+dy),2,2)
    p.line((hx+1,hy+6+dy,hx+5,hy+7+dy),3)
    p.point((hx+2,hy+8+dy),0)
    if not back:p.point((hx+7,hy+8+dy),0)
    p.line((hx+2,hy+11+dy,hx+6,hy+11+dy),3)
    # Longbow vs polearm is obvious in both silhouettes and their releases.
    toolx=5 if back else 7;handy=hy+22
    if recruit=='kolkar_archer':
        p.line((toolx+2,hy+8,toolx-2,hy+13,toolx-3,hy+22,
                toolx,hy+29,toolx+3,hy+32),3,3)
        p.line((toolx+2,hy+9,toolx,hy+14,toolx-1,hy+22,
                toolx+1,hy+28,toolx+3,hy+31),2)
        pull=toolx+9 if phase==1 else toolx+3
        p.line((toolx+2,hy+9,pull,hy+21,toolx+3,hy+31),0)
        p.line((hx-3,hy+17+dy,toolx+1,handy),3,4)
        p.line((hx-3,hy+17+dy,toolx+1,handy),1,2)
        p.line((hx+10,hy+17+dy,pull,hy+21),3,4)
        p.line((hx+10,hy+17+dy,pull,hy+21),1,2)
        if phase!=2:
            p.line((toolx,hy+21,hx+6,hy+21),3)
            p.polygon([(toolx-2,hy+21),(toolx+1,hy+19),(toolx+1,hy+23)],3)
            p.point((toolx-1,hy+21),0)
    else:
        tip=(toolx,hy+5) if phase==0 else (toolx+2,1) if phase==1 else (3,hy+22)
        grip=(hx-4,hy+22)
        p.line((grip[0]+5,grip[1]+10,*tip),3,3)
        p.line((grip[0]+5,grip[1]+9,*tip),2)
        tx,ty=tip
        p.polygon([(tx,ty-1),(tx-2,ty+3),(tx,ty+7),(tx+3,ty+3)],3)
        p.line((tx,ty+1,tx,ty+5),0)
        p.line((hx-3,hy+17+dy,*grip),3,4);p.line((hx-3,hy+17+dy,*grip),1,2)
        p.line((hx+10,hy+17+dy,grip[0]+4,grip[1]+6),3,4)
        p.line((hx+10,hy+17+dy,grip[0]+4,grip[1]+6),1,2)
    if back:
        # Rear profile faces the opponent at upper-right, opposite the enemy
        # front's attack direction. No scaling or lost horse limb is involved.
        p.point((hx+4,bodyy+1),2)
        p.line((hx+4,hy+3+dy,hx+7,hy+4+dy),2,2)
        return (p.pixels.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
                p.mask.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
    return p.pixels,p.mask


def heads(recruit):
    """Deliberately drawn 8px/16px faces, not resized battle illustrations."""
    result={}
    for size in (8,16):
        p=art.Paint((size,size))
        if size==8:
            if recruit=='earth_spirit':rows=['.KKKKKK.','KBBBBBBK','KBGKKGBK','KBBBBBBK','KBBKKBBK','.KKKKKK.','........','........']
            elif recruit=='demon_imp':rows=['K......K','.KKKKKK.','KGGGGGGK','KGWKKWGK','KGGGGGGK','.GKKKKG.','..KKKK..','........']
            elif recruit=='orc_warlock':rows=['.KKKKKK.','KBBGGBBK','KGGKKGGK','KGGGGGGK','.GWKKWG.','.KGGGGK.','..KKKK..','........']
            else:rows=['..KKKK..','.KBBBBK.','KGGKKGGK','KGGGGGGK','.GWKKWG.','.KGGGGK.','..KKKK..','........']
            p.stamp(rows,0,0)
        elif recruit=='earth_spirit':
            rock(p,2,1,11,12);p.rectangle((4,6,6,7),1);p.rectangle((9,6,11,7),1);p.line((6,10,10,10),3)
        elif recruit=='demon_imp':
            p.stamp(['K............K..','.K..........K...','..KKKKKKKKKK....',
                     '.KGGGGGGGGGGK...','KGGGBGGGGGBGGK..','KGGKKKGGKKKGGK..',
                     '.KGWGKGGKGWGK...','.KGGGGGGGGGGK...','..KGBGGGGBGK....',
                     '..KGGWKKWGGK....','...KGGGGGGK.....','....KKKKKK......'],0,1)
        else:
            if recruit=='orc_warlock':
                p.polygon([(3,2),(6,0),(11,1),(14,5),(13,12),(4,13),(1,7)],3)
                p.polygon([(4,3),(7,2),(11,3),(12,6),(11,11),(5,11),(3,7)],2)
            p.stamp(['....KKKKKK....','...KGGGGGGK...','K.KGGGGGGGGK.K',
                     'KGGGKKGGKKGGGK','.KGGWKGGKWGGK.','.KGGGGGGGGGGK.',
                     '..KGBGGGGBGK..','..KGGWKKWGGK..','...KGGGGGGK...','....KKKKKK....'],1,3)
            if recruit.startswith('kolkar_'):
                p.line((5,3,10,3),2,2)
                p.line((4,4,3,7),2)
        pixels,mask=p.pixels,p.mask;data=art.encode(pixels)
        native=NATIVE/recruit;public=OUT/recruit
        (native/f'head_{size}x{size}.2bpp').write_bytes(data)
        export=art.rgba(pixels,mask,PALETTES[recruit]['battle'])
        export.save(public/f'{recruit}_head_{size}x{size}.png')
        export.resize((size*8,size*8),Image.Resampling.NEAREST).save(public/f'{recruit}_head_{size}x{size}_8x.png')
        result[str(size)]={'size':[size,size],'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                          'tile_order':'row-major','palette_rgb555':PALETTES[recruit]['battle']}
    return result


def palette_file(palette):return '\tRGB '+', '.join(str(v) for rgb in palette for v in rgb)+'\n'


def emit(recruit,kind,frames):
    native,public=NATIVE/recruit,OUT/recruit
    native.mkdir(parents=True,exist_ok=True);public.mkdir(parents=True,exist_ok=True)
    size=16 if kind=='world' else 56 if kind=='front' else 48
    palette=PALETTES[recruit]['world' if kind=='world' else 'battle']
    strip=Image.new('P',(size,size*len(frames)));strip.putpalette(art.DMG)
    exports=[];metrics=[]
    for n,(pixels,mask) in enumerate(frames):
        assert pixels.size==(size,size) and set(np.unique(np.array(pixels)))<={0,1,2,3}
        assert set(np.unique(np.array(mask)))<={0,255}
        strip.paste(pixels,(0,n*size));im=art.rgba(pixels,mask,palette);exports.append(im)
        label=f'{DIRECTIONS[n%4]}_step_{n//4}' if kind=='world' else POSES[n]
        im.save(public/f'{recruit}_{kind}_{label}_{size}x{size}.png')
        im.resize((size*8,size*8),Image.Resampling.NEAREST).save(public/f'{recruit}_{kind}_{label}_8x.png')
        metrics.append({'frame':n,'label':label,'opaque_bounds':im.getbbox(),'opaque_pixels':int(np.count_nonzero(np.array(mask)))})
    strip.save(native/f'{kind}_frames.png')
    name='overworld.bin' if kind=='world' else f'{kind}_frames.bin'
    data=b''.join(art.encode(pixels,column_major=kind!='world') for pixels,_ in frames)
    assert len(data)==(768 if kind=='world' else 2352 if kind=='front' else 1728)
    (native/name).write_bytes(data)
    if kind=='front':(native/'portrait_frames.bin').write_bytes(b''.join(art.encode(pixels) for pixels,_ in frames))
    (native/f'{kind}.pal').write_text(palette_file(palette))
    sheet=Image.new('RGBA',(size*3,size*(4 if kind=='world' else 1)))
    for n,im in enumerate(exports):
        x,y=(n//4,n%4) if kind=='world' else (n,0);sheet.alpha_composite(im,(x*size,y*size))
    sheet.save(public/f'{recruit}_{kind}_sheet.png')
    sheet.resize((sheet.width*6,sheet.height*6),Image.Resampling.NEAREST).save(public/f'{recruit}_{kind}_sheet_6x.png')
    motions=[(direction,[exports[d+phase*4] for phase in (0,1,0,2)],[140]*4) for d,direction in enumerate(DIRECTIONS)] if kind=='world' else [
        ('motion',[exports[p] for p in (0,1,2,1,0)],[280,140,140,140,280])]
    for direction,frames,timing in motions:
        label=f'{recruit}_{kind}_{direction}'
        frames[0].save(public/f'{label}.apng',save_all=True,append_images=frames[1:],duration=timing,loop=0,disposal=1,blend=0)
        paper=[]
        for frame in frames:
            frame=frame.resize((size*6,size*6),Image.Resampling.NEAREST)
            bg=Image.new('RGB',frame.size,(243,234,207));bg.paste(frame,mask=frame.getchannel('A'));paper.append(bg)
        paper[0].save(public/f'{label}_6x.gif',save_all=True,append_images=paper[1:],duration=timing,loop=0)
    return {'size':[size,size],'frames':metrics,'binary':str((native/name).relative_to(ROOT)),
            'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
            'palette_rgb555':palette,'tile_order':'row-major' if kind=='world' else 'column-major per frame'}


def icons():
    native,public=NATIVE/'item_icons',OUT/'item_icons'
    native.mkdir(parents=True,exist_ok=True);public.mkdir(parents=True,exist_ok=True)
    result={};sheet=Image.new('RGBA',(48,16))
    for n,name in enumerate(('domination_skull','rally_horn','elemental_relic')):
        p=art.Paint((16,16))
        if name=='domination_skull':
            palette=[(31,31,31),(24,22,15),(24,5,3),(0,0,0)]
            p.polygon([(4,2),(11,2),(14,5),(13,10),(11,11),(11,14),(4,14),(4,11),(2,9),(2,5)],3)
            p.polygon([(5,3),(10,3),(12,5),(12,9),(10,10),(10,13),(5,13),(5,10),(3,8),(3,5)],1)
            p.line((5,4,9,4),0);p.rectangle((4,6,6,8),3);p.rectangle((9,6,11,8),3)
            p.point((5,7),2);p.point((10,7),2);p.line((7,9,8,9),3)
            p.line((5,11,10,11),3);p.point((6,12),0);p.point((9,12),0)
        elif name=='rally_horn':
            palette=[(31,31,31),(25,23,16),(17,10,4),(0,0,0)]
            p.polygon([(2,11),(4,7),(7,5),(10,3),(12,1),(14,3),(13,7),(10,10),(7,11),(5,14),(3,14)],3)
            p.polygon([(4,10),(6,7),(9,6),(11,4),(12,3),(12,6),(9,8),(6,10),(4,12)],1)
            p.line((5,9,9,7),0);p.line((7,6,9,9),2,2)
            p.rectangle((2,11,4,13),2);p.point((3,11),0)
        else:
            palette=[(31,31,31),(15,22,8),(18,11,6),(0,0,0)]
            p.polygon([(5,1),(10,1),(12,4),(11,7),(12,10),(11,14),(4,14),(3,10),(4,7),(3,4)],3)
            p.polygon([(5,3),(10,3),(10,6),(9,8),(10,11),(9,13),(5,13),(5,10),(6,7),(5,5)],2)
            p.rectangle((6,5,9,8),3);p.rectangle((7,5,8,7),1);p.point((7,5),0)
            p.line((5,10,9,10),3);p.line((6,12,8,12),0)
        data=art.encode(p.pixels);assert len(data)==64
        (native/f'{name}.2bpp').write_bytes(data);(native/f'{name}.pal').write_text(palette_file(palette))
        indexed=p.pixels.convert('P');indexed.putpalette(art.DMG);indexed.save(native/f'{name}.png')
        im=art.rgba(p.pixels,p.mask,palette);im.save(public/f'{name}_16x16.png')
        im.resize((128,128),Image.Resampling.NEAREST).save(public/f'{name}_8x.png');sheet.alpha_composite(im,(n*16,0))
        result[name]={'binary':str((native/f'{name}.2bpp').relative_to(ROOT)),'bytes':64,'palette_rgb555':palette,
                      'sha256':hashlib.sha256(data).hexdigest(),'tile_order':'row-major'}
    sheet.save(public/'recruitment_items_sheet.png')
    sheet.resize((384,128),Image.Resampling.NEAREST).save(public/'recruitment_items_sheet_8x.png')
    return result


def jerky_item():
    """A small meat wrap, three opaque pigments and true index0 alpha."""
    native,public=NATIVE/'items',OUT/'items'
    native.mkdir(parents=True,exist_ok=True);public.mkdir(parents=True,exist_ok=True)
    p=art.Paint((16,16));palette=[(31,31,31),(25,17,9),(14,5,3),(2,1,1)]
    p.polygon([(3,3),(6,2),(7,5),(6,10),(3,9)],3)
    p.polygon([(4,4),(5,3),(6,5),(5,8),(4,8)],2)
    p.point((5,4),1);p.line((4,6,5,7),1)
    p.polygon([(8,1),(11,2),(12,5),(10,10),(7,9),(7,4)],3)
    p.polygon([(9,2),(10,3),(11,5),(9,8),(8,8),(8,4)],2)
    p.line((9,4,10,5),1);p.point((9,7),1)
    p.polygon([(11,6),(14,6),(15,8),(13,11),(10,10)],3)
    p.polygon([(12,7),(13,7),(14,8),(12,10),(11,9)],2)
    p.point((13,8),1)
    p.polygon([(2,8),(7,10),(11,8),(13,10),(11,14),(5,15),(2,12)],3)
    p.polygon([(3,10),(7,12),(11,10),(11,12),(10,13),(5,14),(3,12)],1)
    p.line((4,11,9,12),3);p.line((8,12,8,14),2)
    pixels,mask=p.pixels,p.mask
    assert all((pixels.getpixel((x,y))!=0)==(mask.getpixel((x,y))!=0) for y in range(16) for x in range(16))
    data=art.encode(pixels);assert len(data)==64
    (native/'tough_jerky.2bpp').write_bytes(data);(native/'tough_jerky.pal').write_text(palette_file(palette))
    indexed=pixels.convert('P');indexed.putpalette(art.DMG);indexed.save(native/'tough_jerky.png')
    im=art.rgba(pixels,mask,palette);im.save(public/'tough_jerky_native.png')
    im.resize((128,128),Image.Resampling.NEAREST).save(public/'tough_jerky_8x.png')
    return {'tough_jerky':{'binary':str((native/'tough_jerky.2bpp').relative_to(ROOT)),
                         'bytes':64,'tile_order':'row-major','palette_rgb555':palette,
                         'three_opaque_indices_plus_transparent_zero':True,'sha256':hashlib.sha256(data).hexdigest()}}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    report={'source_art_only':True,'native_runtime_integration_verified':False,
            'sprite_species_item_move_ids_assigned':False,'saved_fields_modified':False,
            'style':'Original humble Warcraft-inspired recruits, explicit native pixels and fixed RGB555 palettes.',
            'recruits':{},'enemies':{},'item_icons':icons(),'items':jerky_item()}
    for recruit in ASSET_SETS:
        frames={'world':world_frames(recruit),'front':[picture(recruit,'front',p) for p in range(3)],
                'back':[picture(recruit,'back',p) for p in range(3)]}
        entry={kind:emit(recruit,kind,values) for kind,values in frames.items()}
        entry['heads']=heads(recruit)
        report['recruits' if recruit in RECRUITS else 'enemies'][recruit]=entry
    sheet=Image.new('RGBA',(56*6,168))
    for n,recruit in enumerate(ASSET_SETS):
        for kind,y,size in (('front',0,56),('back',56,48),('world',104,16)):
            im=Image.open(OUT/recruit/f'{recruit}_{kind}_sheet.png')
            if kind!='world':im=im.crop((0,0,size,size))
            sheet.alpha_composite(im,(n*56,y))
    sheet.save(OUT/'six_recruit_enemy_sets_native.png')
    large=sheet.resize((sheet.width*6,sheet.height*6),Image.Resampling.NEAREST);large.save(OUT/'six_recruit_enemy_sets_6x.png')
    review=Image.new('RGBA',large.size,(243,234,207));review.alpha_composite(large);review.save(OUT/'six_recruit_enemy_sets_paper_review.png')
    (OUT/'asset_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'recruits':RECRUITS,'enemies':ENEMIES,'native_frames':108,'group_heads':12,'recruitment_icons':3,
                      'formats':['16x16 world','56x56 front','48x48 back'],'runtime_integrated':False},indent=2))


if __name__=='__main__':main()
