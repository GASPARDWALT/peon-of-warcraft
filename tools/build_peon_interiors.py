#!/usr/bin/env python3
"""Open native hut door quadrants and build two save-compatible shared rooms."""
from pathlib import Path
import json,re
from PIL import Image
import build_durotar_world as world
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'references/generated/durotar_v021'
def main():
    world.BLOCKS.clear();world.build_blocks()
    collision=ROOT/'data/tilesets/peon_collision.asm'
    rows=collision.read_text().splitlines()
    # Door graphic is centered across bottomquadrants; use one actual entrance.
    for index in (4,29):
        comment=rows[index].split(';',1)[1]
        rows[index]='\ttilecoll WALL, WALL, WALL, WARP_PANEL ;'+comment
    # The Den's large building also has a front entrance at its bottom quarter.
    comment=rows[11].split(';',1)[1]
    rows[11]='\ttilecoll WALL, WALL, WALL, WARP_PANEL ;'+comment
    collision.write_text('\n'.join(rows)+'\n')
    entries={}
    manifest=json.loads((world.OUT/'manifest.json').read_text())
    for mapname,doors in manifest['hut_entrances'].items():
        if not doors:continue
        p=ROOT/'maps'/f'{mapname}.asm';s=p.read_text()
        # Make reruns idempotent: only generated door warps are replaced.
        s=re.sub(r'\n\twarp_event[^\n]+ ; PEON_HUT_DOOR','',s)
        additions=[]
        for door in doors:
            x,y=door['door_tile'];target='PEON_TROLL_HUT' if door['block']==29 else 'PEON_ORC_HUT'
            additions.append(f'\twarp_event {x}, {y}, {target}, 1 ; PEON_HUT_DOOR')
            entries.setdefault(mapname,[]).append({'xy':[x,y],'target':target})
        if mapname=='TheDen':
            additions.append('\twarp_event 5, 7, PEON_ORC_HUT, 1 ; PEON_HUT_DOOR')
            entries[mapname].append({'xy':[5,7],'target':'PEON_ORC_HUT'})
        s=s.replace('\tdef_coord_events','\n'.join(additions)+'\n\tdef_coord_events',1)
        p.write_text(s)
    for name,origin in [('PeonTrollHut','SenjinVillage'),('PeonOrcHut','RazorHill')]:
        w,h=6,5;data=[1 if x in (0,5) or y in (0,4) else (5 if x in (2,3) else 7) for y in range(h) for x in range(w)]
        data[3*w+2]=16;data[1*w+4]=6
        (ROOT/'maps'/f'{name}.blk').write_bytes(bytes(data))
        pals=world.REGION_BGS[origin]
        canvas=Image.new('RGB',(w*32,h*32))
        for i,value in enumerate(data):
            b=world.BLOCKS[value];im=b['im'].copy();im.putpalette([v for c in pals[b['pal']] for v in c]+[0]*756)
            canvas.paste(im.convert('RGB'),((i%w)*32,(i//w)*32))
        canvas.save(world.OUT/'maps'/f'{name}.png')
    (ROOT/'gfx/tilesets/peon_interiors.pal').write_text(''.join(world.palfile(world.REGION_BGS[name]) for name in ('SenjinVillage','RazorHill')))
    manifest['enterable_buildings']=entries
    manifest['limitations']=['Map geography compressed to v0.2 dimensions.','Huts share two reusable interior layouts.','Echo Isles and Orgrimmar city remain outside these maps.']
    (world.OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'building_entries.json').write_text(json.dumps(entries,indent=2)+'\n')
    print('Linked',sum(len(v) for v in entries.values()),'building doors to two shared interiors.')
if __name__=='__main__':main()
