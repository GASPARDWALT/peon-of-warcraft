#!/usr/bin/env python3
"""Exact native elemental FX and binary-alpha, reusable PNG/APNG exports.

The two 12-tile projectile packets have identical layout. Only Warlock's
basic action substitutes a blue wand spark; Shadow Bolt and imp Firebolt
retain the tested four-phase trajectories. No old published art is written.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image
from build_peon_pet_spell_assets_v026 import FIRE, SHADOW, encode, indices

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/polish_v028/combat/assets'
GFX = ROOT / 'gfx/peon_combat_v028'
PALETTES = {
    'flame': [(31,25,7),(31,9,2),(12,2,0)],
    'nature': [(18,30,9),(5,17,8),(0,6,3)],
    'lightning': [(31,30,12),(16,25,31),(3,7,14)],
    'frost': [(15,25,31),(5,13,26),(0,4,12)],
    'shadow': [(26,13,31),(12,3,18),(3,1,5)],
    'wand': [(25,30,31),(11,18,27),(3,5,12)],
}
NATURE = {
    'flame': [
        ['00000000','00001000','00011200','00211100','02111220','02112230','00322300','00033000'],
        ['00000000','00010000','00211000','00111120','02111220','03122300','00323000','00033000'],
        ['00000000','00000100','00011200','00211120','02111220','03222300','00323000','00033000'],
        ['00000000','00001000','00012100','00211120','02111230','03222300','00323000','00033000']],
    'nature': [
        ['00000000','00001100','00012120','00122220','01222300','02223000','03330000','03000000'],
        ['00000000','00000000','00111100','01212220','02222320','00323300','03300000','00000000'],
        ['00000000','00110000','01212000','02222000','02320000','00330000','00030000','00000000'],
        ['00000000','00001000','00012120','00122220','01222300','02233000','03300000','03000000']],
    'lightning': [
        ['00001100','00012000','00120000','01111200','00012000','00120000','01200000','03000000'],
        ['00011000','00120000','01112000','00011200','00012000','00120000','01120000','03000000'],
        ['00000110','00001200','00111200','00120000','01111200','00012000','00001200','00000300'],
        ['00110000','00112000','00001200','00111200','00120000','01112000','00012000','00003000']],
    'frost': [
        ['00000000','00111200','01000020','00000020','00112200','03000000','00000000','00000000'],
        ['00000000','00011120','00100002','00000002','00011220','00300000','00000000','00000000'],
        ['00000000','00001112','00010002','00000002','00001122','00030000','00000000','00000000'],
        ['00000000','00011120','00100020','00000200','00112200','03000000','00000000','00000000']],
}
WAND = [
    ['0000000000000000','0003000000100000','0000233001212000','0000033221111200',
     '0000003221112300','0000000332123000','0000000000300000','0000000000000000'],
    ['0000000000000000','0000300000010000','0000023000121200','0000033221111200',
     '0000003221112300','0000000032123000','0000000000300000','0000000000000000'],
    ['0000000000000000','0003000000100000','0000023301212000','0000003221111200',
     '0000003221112300','0000000332123000','0000000000300000','0000000000000000'],
    ['0000000000000000','0000300000010000','0000233000121200','0000033221111200',
     '0000003221112300','0000000032123000','0000000000300000','0000000000000000'],
]


def rgba(frame, palette):
    im = Image.new('RGBA', (len(frame[0]),len(frame)), (0,0,0,0))
    for y,row in enumerate(frame):
        for x,value in enumerate(row):
            if value:
                im.putpixel((x,y),tuple((n<<3)|(n>>2) for n in palette[value-1])+(255,))
    return im


def export(name,frames,palette,integrated):
    images = [rgba(frame,palette) for frame in frames]
    w,h = images[0].size
    sheet = Image.new('RGBA',(w*len(images),h),(0,0,0,0))
    for i,im in enumerate(images):
        assert set(im.getchannel('A').getdata()) <= {0,255}
        im.save(OUT/f'{name}_frame_{i:02d}_{w}x{h}.png')
        im.resize((w*8,h*8),Image.Resampling.NEAREST).save(OUT/f'{name}_frame_{i:02d}_8x.png')
        sheet.alpha_composite(im,(i*w,0))
    sheet.save(OUT/f'{name}_sheet.png')
    images[0].save(OUT/f'{name}_native.apng',save_all=True,append_images=images[1:],duration=100,loop=0,
                   disposal=0,blend=0)
    preview = [im.resize((w*8,h*8),Image.Resampling.NEAREST) for im in images]
    preview[0].save(OUT/f'{name}_8x.apng',save_all=True,append_images=preview[1:],duration=100,loop=0,
                    disposal=0,blend=0)
    return {'name':name,'frame_size':[w,h],'frames':len(images),'binary_alpha':True,
            'opaque_colours':3,'palette_rgb555':palette,'integrated_in_rom':integrated}


def circle_frames(element):
    """Reusable 24x24 elemental cast halos; exports only, not fake runtime."""
    result=[]
    particle=[indices(x) for x in NATURE[element]]
    for phase in range(4):
        canvas=[[0]*24 for _ in range(24)]
        for ox,oy in ((0,8),(8,0),(16,8),(8,16)):
            p=particle[phase]
            for y,row in enumerate(p):
                for x,value in enumerate(row):
                    if value:canvas[oy+y][ox+x]=value
        result.append(canvas)
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True);GFX.mkdir(parents=True,exist_ok=True)
    records=[];nature=bytearray()
    for name,rows in NATURE.items():
        frames=[indices(x) for x in rows]
        nature.extend(b''.join(encode(frame) for frame in frames))
        records.append(export(name+'_particle',frames,PALETTES[name],True))
    fire=[indices(x) for x in FIRE];shadow=[indices(x) for x in SHADOW];wand=[indices(x) for x in WAND]
    records.append(export('imp_firebolt',fire,PALETTES['flame'],True))
    records.append(export('shadow_bolt',shadow,PALETTES['shadow'],True))
    records.append(export('wand_strike',wand,PALETTES['wand'],True))
    fire_bytes=b''.join(encode(x) for x in fire)
    projectiles=fire_bytes+b''.join(encode(x) for x in shadow)
    wand_packet=fire_bytes+b''.join(encode(x) for x in wand)
    assert len(nature)==16*16 and len(projectiles)==len(wand_packet)==12*16
    files={'nature':bytes(nature),'projectiles':projectiles,'wand_projectiles':wand_packet}
    for name,data in files.items():(GFX/f'{name}.2bpp').write_bytes(data)
    for name,element,pal in [('healing_wave_halo','nature','nature'),
                             ('lightning_shield_halo','lightning','lightning'),
                             ('frost_shock_halo','frost','frost'),
                             ('flame_shock_halo','flame','flame')]:
        records.append(export(name,circle_frames(element),PALETTES[pal],False))
    manifest={'source':'Original exact native pixel patterns; no proprietary game art copied.',
              'runtime_size':'8x8 particles; horizontal16x8 bolts; 24x24 halos are reusable source art only.',
              'rgb555_expansion':'(v << 3) | (v >> 2)','records':records,
              'native_tiles':{name:{'tiles':len(data)//16,'sha256':hashlib.sha256(data).hexdigest()}
                              for name,data in files.items()},
              'preserved_regions':['bank1 rank8800..885f','totem8860..88bf','imp88c0..891f',
                                   'bold8920..8a8f','enemy-front-overflow9620..97ff'],
              'new_saved_fields':0,'new_move_ids':0,'basic_wand_damage_or_turn_cost_changed':False}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('v028 combat assets: 3 same-budget native packets; 44 original alpha frames + sheets/APNGs.')


if __name__=='__main__':main()
