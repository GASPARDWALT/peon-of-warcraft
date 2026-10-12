#!/usr/bin/env python3
"""Author original native-size v026 companions and spell particles.

Only new v026 targets/public previews are written. Published v025 art is never
rebuilt. Each alpha PNG uses exactly the native RGB555 palette and pixel grid.
"""
from pathlib import Path
import hashlib
import json
import re
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/visual_polish_v026/pets_spells/assets'
GFX = ROOT / 'gfx/peon_pets_v026'

IMP = [
 '  3          3  ', ' 313        313 ', ' 3213      3123 ', ' 32213333331223 ',
 '  322222222223  ', ' 33222222222233 ', '3222222222222223', ' 32222222222223 ',
 '  332222222233  ', '    32222223    ', '   3322222233   ', '  322322223223  ',
 ' 32132222223123 ', ' 32332222223323 ', '  3 32222223 3  ', '    32222223 3  ',
 '    32222223 3  ', '    33222233 3  ', '     323323  3  ', '    32133123 3  ',
 '    32133123 3  ', '   3313 3133 3  ', '   3333 3333333 ', '                ',
]
TOTEM = [
 '    33333333    ', '   3111111113   ', ' 33113311331133 ', '312213113122213 ',
 '311213113121113 ', ' 3113333331113  ', '  31231132113   ', '   313113113    ',
 '   311333113    ', '   333111333    ', '    311113      ', '   33122133     ',
 '  3111221113    ', ' 312311113213   ', ' 311333333113   ', '  3122112213    ',
 '   31111113     ', '   33311333     ', '    311113      ', '   33111133     ',
 '  3111111113    ', ' 311111111113   ', ' 333333333333   ', '                ',
]
FIRE = [
 ['        ','    2   ','   21   ','  2112  ',' 211122 ','  22223 ','   223  ','        '],
 ['        ','   2    ','  212   ',' 21112  ','2111223 ',' 222233 ','   23   ','        '],
 ['        ','    2   ','  2122  ',' 211123 ','2111223 ','  2223  ','   23   ','        '],
 ['        ','   2    ','  2122  ',' 211123 ','2111223 ',' 22223  ','   23   ','        '],
]
SHADOW = [
 ['                ','  3       33    ','   33   32223   ','    2333221123  ','   332332211123 ','  33    322223  ','          333   ','                '],
 ['                ','   33     33    ','  3233  32223   ','    3233221123  ','   323332211123 ','  33    322223  ','          333   ','                '],
 ['                ','  33      33    ','   3233 32223   ','    2333221123  ','  3332332211123 ','   3    322223  ','          333   ','                '],
 ['                ','   3      33    ','  3323  32223   ','    2333221123  ','   332332211123 ','  323   322223  ','          333   ','                '],
]


def palette(row):
    vals = list(map(int,re.findall(r'\d+',row.split(';',1)[0])))
    assert len(vals)==12
    return [tuple((v<<3)|(v>>2) for v in vals[i:i+3]) for i in range(0,12,3)]


def indices(rows):
    assert all(len(r)==len(rows[0]) for r in rows)
    return [[int(c) if c!=' ' else 0 for c in row] for row in rows]


def encode(frame):
    result=bytearray()
    for ty in range(len(frame)//8):
        for tx in range(len(frame[0])//8):
            for y in range(8):
                low=high=0
                for x in range(8):
                    v=frame[ty*8+y][tx*8+x]
                    low=(low<<1)|(v&1);high=(high<<1)|((v>>1)&1)
                result.extend((low,high))
    return bytes(result)


def image_of(frame,pal):
    image=Image.new('RGBA',(len(frame[0]),len(frame)),(0,0,0,0))
    for y,row in enumerate(frame):
        for x,v in enumerate(row):
            if v:image.putpixel((x,y),pal[v]+(255,))
    return image


def emit(name,frames,pal):
    images=[image_of(f,pal) for f in frames]
    for i,im in enumerate(images):
        im.save(OUT/(name+f'_{i}_native.png'))
        im.resize((im.width*8,im.height*8),Image.Resampling.NEAREST).save(OUT/(name+f'_{i}_8x.png'))
    sheet=Image.new('RGBA',(images[0].width*len(images),images[0].height),(0,0,0,0))
    for i,im in enumerate(images):sheet.paste(im,(i*im.width,0))
    sheet.save(OUT/(name+'_native_sheet.png'))
    binary=b''.join(encode(f) for f in frames)
    (GFX/(name+'.2bpp')).write_bytes(binary)
    return {'name':name,'frame_size':[images[0].width,images[0].height],
            'frames':len(frames),'tile_bytes':len(binary),'sha256':hashlib.sha256(binary).hexdigest()}


def world_frames():
    # A real small companion rather than shrinking the hostile actor sheet.
    # Foot alignment is retained; right-facing is Crystal's native mirror.
    down=['                ']*16
    down[3]='     2    2     '
    down[4]='    232  232    '
    down[5]='    23333332    '
    down[6]='    23133132    '
    down[7]='     233332     '
    down[8]='    22333322    '
    down[9]='   2323333232   '
    down[10]='    22333322    '
    down[11]='     233332 2   '
    down[12]='     232232 2   '
    down[13]='     21221222   '
    up=down.copy();up[6]='    23333332    ';up[7]='     233332     '
    left=down.copy();left[4]='     232        ';left[5]='    2333332     '
    left[6]='    2133332     ';left[7]='    233332      '
    left[9]='    23333232    ';left[11]='     23332 22   '
    left[12]='     23222 2    '
    idle=[indices(f) for f in (down,up,left)]
    walking=[]
    for f in idle:
        p=[row.copy() for row in f]
        # Opposite foot/arm offset is one native pixel, never fractional blur.
        p[13]=[0]*16;p[13][5:8]=[2,1,2];p[14][9:12]=[2,1,2]
        p[9][3],p[10][3]=0,2
        walking.append(p)
    return idle+walking


def main():
    OUT.mkdir(parents=True,exist_ok=True);GFX.mkdir(parents=True,exist_ok=True)
    pet_source=(ROOT/'engine/battle/peon_warlock_pet.asm').read_text()
    red=palette(pet_source.split('PeonPetBattlePalette:',1)[1].strip().splitlines()[0])
    totem_source=(ROOT/'engine/battle/peon_battle_totems.asm').read_text()
    earth=palette(totem_source.split('.palette:',1)[1].strip().splitlines()[0])
    world_rows=[r for r in (ROOT/'gfx/overworld/peon_obj.pal').read_text().splitlines() if r.strip().startswith('RGB')]
    flame=palette('RGB 31,31,31, 31,25,7, 31,9,2, 12,2,0')
    shadow=palette('RGB 31,31,31, 26,13,31, 12,3,18, 3,1,5')
    imp=indices(IMP);cast=[r.copy() for r in imp]
    # A raised casting forearm and lit hand, with body/foot anchors unchanged.
    for y in range(10,16):
        for x in range(12,16):cast[y][x]=0
    for y,x,v in [(9,12,3),(9,13,1),(9,14,3),(10,12,3),(10,13,2),(10,14,3),(11,12,3),(11,13,2),(12,11,3),(12,12,2),(13,10,3),(13,11,2)]:cast[y][x]=v
    records=[emit('combat_imp_v026',[imp,cast],red),
             emit('earth_totem_v026',[indices(TOTEM)],earth),
             emit('friendly_imp_world_v026',world_frames(),palette(world_rows[0]))]
    # Four single-tile fire frames, then four two-tile shadow frames.
    records.append(emit('firebolt_v026',[indices(f) for f in FIRE],flame))
    records.append(emit('shadow_bolt_v026',[indices(f) for f in SHADOW],shadow))
    packet=(GFX/'firebolt_v026.2bpp').read_bytes()+(GFX/'shadow_bolt_v026.2bpp').read_bytes()
    (GFX/'spell_particles_v026.2bpp').write_bytes(packet)
    assert len(packet)==12*16
    (OUT/'manifest.json').write_text(json.dumps({'original_native_art':True,'alpha':'binary',
        'rgb555_expansion':'(v << 3) | (v >> 2)','records':records,
        'battle_visible_footprint':{'columns':[8,9],'rows':[4,5,6]},
        'bank1_bg_tiles':{'totem':['86','87','88','89','8a','8b'],'imp':['8c','8d','8e','8f','90','91']},
        'friendly_world_sprite_id':104,'hostile_world_imp_unchanged':True,
        'new_animation_id':'116','particle_movement':'native 2 pixels/frame',
        'protected':'player HUD begins column9 row7; elite emblem columns10/11 rows4..6'},indent=2)+'\n')
    print('Original v026 companion/totem/spell PNGs and native tiles emitted; prior releases untouched.')


if __name__=='__main__':main()
