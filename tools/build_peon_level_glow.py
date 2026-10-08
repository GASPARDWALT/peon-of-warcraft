#!/usr/bin/env python3
"""Original two-tile, four-color GBC level aura and six native trajectories."""
from pathlib import Path
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/warcraft_audio_update/level_up'
PALETTE = [(31,31,31),(31,28,12),(31,21,3),(16,9,0)]
GLYPHS = [
    ['00000000','00030000','00313000','03111300','00323000','00030000','00000000','00000000'],
    ['00000000','00000000','00001133','00012200','00122000','01220000','13200000','33000000'],
]


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    native = Image.new('P',(16,8)); native.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
    public = Image.new('RGBA',(16,8)); binary = bytearray()
    for tile,rows in enumerate(GLYPHS):
        for y,row in enumerate(rows):
            values = list(map(int,row))
            binary += bytes([sum((v&1)<<(7-x) for x,v in enumerate(values)),
                             sum((v>>1)<<(7-x) for x,v in enumerate(values))])
            for x,value in enumerate(values):
                native.putpixel((tile*8+x,y),value)
                if value: public.putpixel((tile*8+x,y),(*(v<<3 for v in PALETTE[value]),255))
    native.save(ROOT/'gfx/pack/peon_level_glow.png')
    (ROOT/'gfx/pack/peon_level_glow.2bpp').write_bytes(binary)
    public.save(OUT/'peon_level_glow.png')
    public.resize((256,128),Image.Resampling.NEAREST).save(OUT/'peon_level_glow_16x.png')
    lines = ['; Six poses, six frames each. Relative OAM dy/dx, tile, attributes.',
             'PeonLevelGlowPalette:'] + ['\tRGB '+', '.join(map(str,p)) for p in PALETTE]
    trajectories = {}
    for label,specs in [('Battle',[(0,22,8),(-4,24,10),(-8,23,12),(-12,20,10),(-16,17,8),(-20,12,6)]),
                        ('World',[(4,12,7),(2,14,9),(0,15,10),(-2,13,9),(-4,11,7),(-6,9,5)])]:
        lines += ['PeonLevelGlow'+label+'Frames:']
        phases = []
        for rise,rx,ry in specs:
            phase = [(rise,-rx,0x6e,7),(rise,rx,0x6e,7),(rise-ry,0,0x6e,7),(rise+ry,0,0x6e,7),
                     (rise-ry//2,-rx//2,0x6f,7),(rise-ry//2,rx//2,0x6f,7|0x20),
                     (rise+ry//2,-rx//2,0x6f,7|0x40),(rise+ry//2,rx//2,0x6f,7|0x60)]
            phases.append(phase)
            lines += ['\tdb '+', '.join(map(str,point)) for point in phase]
        trajectories[label.lower()] = phases
    (ROOT/'gfx/pack/peon_level_glow_frames.asm').write_text('\n'.join(lines)+'\n')
    manifest = {'tiles':2,'tile_ids':[110,111],'obj_vram':'bank0 $86e0..$86ff',
        'temporary_obj_palette':7,'rgb555':PALETTE,'frames':36,'keyframes':6,'phase_frames':6,
        'trajectories':trajectories,'binary_sha256':hashlib.sha256(binary).hexdigest(),
        'limitations':['Effect skips visual when the last eight OAM slots contain visible world actors; sound still plays.',
                       'Scenes OFF keeps the native ding and skips the visual.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Native two-tile gold aura and six trajectories generated.')


if __name__=='__main__': main()
