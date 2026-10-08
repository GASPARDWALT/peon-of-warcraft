#!/usr/bin/env python3
"""Link nine hut/inn doors and compile shared rooms without expanding VRAM.

Run after build_durotar_world.py. Bedroll/table metatiles rearrange existing
8x8 tiles, preserving the 192-tile allocation and all previous block indexes.
"""
import json
import re
from pathlib import Path
from PIL import Image, ImageDraw
import build_durotar_world as world

ROOT = Path(__file__).resolve().parents[1]
OUT = world.OUT.parent
INN_DOORS = {'TheDen':(17,5),'SenjinVillage':(15,5),'RazorHill':(17,5)}


def furnishings():
    # A tile reference is (existing block, existing 8x8 tile within the block).
    # Both pieces retain the existing floor around their central silhouette.
    bed=[(7,i) for i in range(16)]
    for dest,source in {5:(7,0),6:(7,1),9:(5,5),10:(5,6),
                        13:(32,12),14:(32,13)}.items():bed[dest]=source
    table=[(7,i) for i in range(16)]
    for dest,source in {5:(32,0),6:(32,1),9:(32,12),10:(32,13)}.items():table[dest]=source
    return {'inn_bedroll':bed,'inn_table':table}


def draw_block(block,pals,custom):
    if block not in custom:
        source=world.BLOCKS[block]
        image=source['im'].copy()
        image.putpalette([v for colour in pals[source['pal']] for v in colour]+[0]*756)
        return image.convert('RGB')
    image=Image.new('RGB',(32,32))
    for position,(source_block,source_tile) in enumerate(custom[block]):
        source=world.BLOCKS[source_block]
        tile=source['im'].crop((source_tile%4*8,source_tile//4*8,
                                source_tile%4*8+8,source_tile//4*8+8))
        tile.putpalette([v for colour in pals[source['pal']] for v in colour]+[0]*756)
        image.paste(tile.convert('RGB'),(position%4*8,position//4*8))
    return image


def main():
    world.build_blocks()
    base_blocks=len(world.BLOCKS)
    manifest=json.loads((world.OUT/'manifest.json').read_text())
    collision=ROOT/'data/tilesets/peon_collision.asm'
    rows=collision.read_text().splitlines()[:base_blocks]
    for index in (4,11,29):
        comment=rows[index].split(';',1)[1]
        rows[index]='\ttilecoll WALL, WALL, WALL, WARP_PANEL ;'+comment
    native_meta=ROOT/'data/tilesets/peon_metatiles.bin'
    original=native_meta.read_bytes()[:base_blocks*16]
    assert len(original)==base_blocks*16
    compiled=bytearray(original)
    custom={};ids={}
    for offset,(name,refs) in enumerate(furnishings().items()):
        index=base_blocks+offset;ids[name]=index;custom[index]=refs
        compiled.extend(original[block*16+tile] for block,tile in refs)
        rows.append('\ttilecoll WALL, WALL, WALL, WALL ; '+f'{index:02x} {name}')
    native_meta.write_bytes(compiled)
    collision.write_text('\n'.join(rows)+'\n')

    entries={}
    for mapname,doors in manifest['hut_entrances'].items():
        if not doors:continue
        path=ROOT/'maps'/f'{mapname}.asm';source=path.read_text()
        source=re.sub(r'\n\twarp_event[^\n]+ ; PEON_HUT_DOOR','',source)
        additions=[]
        for door in doors:
            x,y=door['door_tile']
            is_inn=(x,y)==INN_DOORS.get(mapname)
            target=('PEON_TROLL_' if door['block']==29 else 'PEON_ORC_')+('INN' if is_inn else 'HUT')
            additions.append(f'\twarp_event {x}, {y}, {target}, 1 ; PEON_HUT_DOOR')
            entries.setdefault(mapname,[]).append({'xy':[x,y],'target':target,'service':'inn' if is_inn else 'residence'})
        if mapname=='TheDen':
            additions.append('\twarp_event 5, 7, PEON_ORC_HUT, 1 ; PEON_HUT_DOOR')
            entries[mapname].append({'xy':[5,7],'target':'PEON_ORC_HUT','service':'residence'})
        source=source.replace('\tdef_coord_events','\n'.join(additions)+'\n\tdef_coord_events',1)
        path.write_text(source)
    assert sum(len(doors) for doors in entries.values())==9
    for mapname,expected in [('TheDen',2),('SenjinVillage',3),('RazorHill',4)]:
        warps=re.findall(r'\bwarp_event\s+(\d+),\s*(\d+),\s*([^,]+),',
                         (ROOT/'maps'/f'{mapname}.asm').read_text())
        assert tuple(int(v) for v in warps[expected-1][:2])==INN_DOORS[mapname], 'Hearthstone backup warp changed'
        assert warps[expected-1][2].endswith('_INN')

    specs=[('PeonTrollHut','SenjinVillage',False),('PeonOrcHut','RazorHill',False),
           ('PeonOrcInn','RazorHill',True),('PeonTrollInn','SenjinVillage',True)]
    for name,origin,is_inn in specs:
        width,height=6,5
        data=[1 if x in (0,5) or y in (0,4) else (5 if x in (2,3) else 7)
              for y in range(height) for x in range(width)]
        data[3*width+2]=16
        if is_inn:
            data[1*width+1]=ids['inn_bedroll'];data[3*width+1]=ids['inn_bedroll']
            data[1*width+4]=34
            data[2*width+4]=ids['inn_table'];data[3*width+4]=ids['inn_table']
        else:data[1*width+4]=6
        (ROOT/'maps'/f'{name}.blk').write_bytes(bytes(data))
        pals=world.REGION_BGS[origin]
        canvas=Image.new('RGB',(width*32,height*32))
        for position,block in enumerate(data):
            canvas.paste(draw_block(block,pals,custom),(position%width*32,position//width*32))
        canvas.save(world.OUT/'maps'/f'{name}.png')
        canvas.resize((384,320),Image.Resampling.NEAREST).save(world.OUT/'maps'/f'{name}_2x.png')
    props=world.OUT/'props';props.mkdir(parents=True,exist_ok=True)
    for name,index in ids.items():
        image=draw_block(index,world.REGION_BGS['RazorHill'],custom).convert('RGBA')
        mask=Image.new('L',(32,32),0);draw=ImageDraw.Draw(mask)
        draw.rectangle((8,8,23,31 if name=='inn_bedroll' else 23),fill=255)
        image.putalpha(mask);image.save(props/(name+'.png'))
    (ROOT/'gfx/tilesets/peon_interiors.pal').write_text(''.join(
        world.palfile(world.REGION_BGS[name]) for name in ('SenjinVillage','RazorHill')))
    manifest['enterable_buildings']=entries
    manifest['inns']={name:{'door':list(xy),'home_flag':'EVENT_PEON_HOME_'+suffix}
                      for (name,xy),suffix in zip(INN_DOORS.items(),('DEN','SENJIN','RAZOR'))}
    manifest['interior_furnishings']={'new_metatile_indexes':ids,'new_native_tiles':0,
                                     'source_blocks':[5,7,32]}
    manifest['limitations']=['Map geography compressed to prototype dimensions.',
                             'Residences share two rooms; three inns share two layouts.',
                             'Inn rest restores health and charges instantly as a prototype adaptation.',
                             'Echo Isles and Orgrimmar city remain outside these maps.']
    (world.OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'building_entries.json').write_text(json.dumps(entries,indent=2)+'\n')
    print('Linked nine doors: six residences and three inns; two new furniture blocks, zero new VRAM tiles.')


if __name__=='__main__':main()
