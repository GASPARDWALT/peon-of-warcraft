#!/usr/bin/env python3
"""Create original four-frame, 8px elemental particles for the native APU/OBJ engine.

These are executable sprite pixels, not a rendered approximation of the spell.
The transparent PNGs use precisely the ROM's three opaque RGB555 colours.
"""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/spell_animations'
PATTERNS = {
    'flame': [
        ['00000000','00010000','00012000','00212200','02111200','03212300','00333000','00000000'],
        ['00000000','00000100','00001200','00012200','00211200','03112300','00333000','00000000'],
        ['00000000','00100000','00210000','00221000','00211200','03112300','00333000','00000000'],
        ['00000000','00001000','00012100','00122100','00211200','00312300','00033000','00000000']],
    'leaf': [
        ['00000000','00000000','00001100','00012100','00122000','00320000','03000000','00000000'],
        ['00000000','00000000','00000000','00111100','01222300','03233000','03000000','00000000'],
        ['00000000','00000000','00110000','00121000','00022100','00023000','00003000','00000000'],
        ['00000000','00000000','00001300','00012200','00122000','00330000','03000000','00000000']],
    'arc': [
        ['00001000','00012000','00120000','01211000','00012000','00120000','01200000','03000000'],
        ['00010000','00120000','01211000','00012000','00001200','00012100','00120000','03000000'],
        ['00000100','00001200','00112100','00120000','01211000','00012000','00001200','00000300'],
        ['00100000','00121000','00001200','00112100','00120000','01211000','00012000','00003000']],
    'wind': [
        ['00000000','00111200','01000020','00000020','00112200','03000000','00000000','00000000'],
        ['00000000','00011120','00100002','00000002','00011220','00300000','00000000','00000000'],
        ['00000000','00001112','00010002','00000002','00001122','00030000','00000000','00000000'],
        ['00000000','00011120','00100020','00000200','00112200','03000000','00000000','00000000']],
}
PALETTES = {
    'flame': [(31,25,7),(31,9,2),(12,2,0)],
    'leaf': [(18,30,9),(5,17,8),(0,6,3)],
    'arc': [(31,30,12),(16,25,31),(3,7,14)],
    'wind': [(15,25,31),(5,13,26),(0,4,12)],
}


def expand(rgb):
    return tuple((v << 3) | (v >> 2) for v in rgb)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    native = Image.new('P', (8,128))
    native.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
    binary = bytearray()
    for index, (name, frames) in enumerate(PATTERNS.items()):
        sheet = Image.new('RGBA', (32,8))
        palette = PALETTES[name]
        for phase, rows in enumerate(frames):
            rgba = Image.new('RGBA', (8,8))
            for y, row in enumerate(rows):
                values = [int(v) for v in row]
                binary.extend((sum((v&1)<<(7-x) for x,v in enumerate(values)),
                               sum((v>>1)<<(7-x) for x,v in enumerate(values))))
                for x, value in enumerate(values):
                    native.putpixel((x,index*32+phase*8+y), value)
                    rgba.putpixel((x,y),(*expand(palette[value-1]),255) if value else (0,0,0,0))
            rgba.save(OUT / f'{name}_particle_frame_{phase:02d}_8x8.png')
            sheet.alpha_composite(rgba, (phase*8,0))
        sheet.save(OUT / f'{name}_particle_sheet_4frames.png')
        sheet.resize((256,64), Image.Resampling.NEAREST).save(OUT / f'{name}_particle_sheet_8x.png')
    path = ROOT / 'gfx/battle_anims/peon_nature'
    native.save(path.with_suffix('.png'))
    path.with_suffix('.2bpp').write_bytes(binary)
    (OUT / 'particles_manifest.json').write_text(json.dumps({
        'native_tile_count':16,'frame_size':[8,8],'frames_per_element':4,
        'binary_alpha':True,'source':'Original hand-drawn pixel patterns in build_peon_spell_particles.py',
        'warcraft_recordings_or_icons_imported':False,
        'palettes_rgb555':PALETTES,
        'timing':'Flame/leaf/wind 6 frames per phase; lightning/frost 4 frames per phase.',
        'integrated_scripts':['Rockbiter','Earth Shock','Flame Shock','Healing Wave',
                              'Lightning Shield','Strength of Earth','Purge','Frost Shock',
                              'Flame Shock II','Windfury','Chain Lightning'],
        'lightning_bolt':'Existing simple native arc, unchanged.'
    },indent=2)+'\n')
    print('16 native elemental tiles; 24 transparent PNG sprite exports')


if __name__ == '__main__':
    main()
