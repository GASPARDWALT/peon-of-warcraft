#!/usr/bin/env python3
"""Compile the seven real Valley sectors and exact player/quest projections."""
import hashlib
import json
import re
from pathlib import Path
from PIL import Image, ImageDraw
from build_durotar_maps import compile_map, text
from build_peon_environment_palettes import REGION_BGS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/environment_v025/atlas_overview'
# Grid-aligned rectangles retain the relative layout of the annotated plan.
# They fit the 160x144 display and leave the heading/footer unobstructed.
RECTS = {1: (5, 12, 4, 3), 2: (9, 12, 4, 3), 3: (7, 8, 4, 3),
         4: (2, 6, 4, 3), 5: (1, 10, 4, 3), 6: (8, 2, 4, 3),
         7: (15, 12, 4, 3)}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = json.loads((ROOT / 'references/generated/environment_v025/zone_layout/metadata.json').read_text())
    image = Image.new('RGB', (160, 144), (82, 49, 33))
    draw = ImageDraw.Draw(image)
    draw.rectangle((2, 15, 157, 120), fill=(123, 74, 41))
    projections = {}
    for zone in meta['zones']:
        z = zone['zone']; tx, ty, tw, th = RECTS[z]
        rect = tuple(v * 8 for v in (tx, ty, tw, th))
        x, y, w, h = rect; gw, gh = zone['movement_grid']
        projections[str(zone['map_id'])] = dict(map=zone['name'], zone=z,
            discovery_flag=f'EVENT_PEON_SECTOR_{z}', fog_tiles=[tx,ty,tw,th],
            thumbnail_offset=[x,y], thumbnail_size=[w,h], collision_size=[gw,gh],
            x_centers=[round(x+(n+.5)*w/gw) for n in range(gw)],
            y_centers=[round(y+(n+.5)*h/gh) for n in range(gh)])
    # The narrow connectors show the real graph, beneath terrain miniatures.
    for edge in meta['edges']:
        if edge['to_zone'] is None: continue
        a, b = projections[str(edge['from_map_id'])], projections[str(edge['to_map_id'])]
        ax, ay = edge['source_xy']; bx, by = edge['target_xy']
        start=(a['x_centers'][ax], a['y_centers'][ay]); end=(b['x_centers'][bx], b['y_centers'][by])
        bend=(end[0],start[1]) if edge['direction'] in ('RIGHT','LEFT') else (start[0],end[1])
        draw.line([start,bend,end],fill=(49,25,16),width=5)
        draw.line([start,bend,end],fill=(222,165,82),width=3)
    for zone in meta['zones']:
        row = projections[str(zone['map_id'])]; x,y=row['thumbnail_offset']; w,h=row['thumbnail_size']
        miniature=Image.open(ROOT/'references/generated/environment_v025/zone_layout/maps'/f"{zone['name']}.png").convert('RGB')
        image.paste(miniature.resize((w,h),Image.Resampling.NEAREST),(x,y))
    text(image,'VALLEY OF TRIALS',4,(255,247,214))
    text(image,'LEFT RIGHT CHANGE ZONE',124,(255,247,214))
    text(image,'A B SELECT BACK',136,(255,247,214))
    binary,native=compile_map(image,REGION_BGS['ValleyOfTrials'])
    # Two otherwise blank footer tiles become reusable fog patterns in bank1.
    patterns=bytearray()
    for rows in (['22222222']*8,
                 ['22222222','22111122','21222122','22221222','22212222','22222222','22212222','22222222']):
        for row in rows:
            vals=list(map(int,row)); patterns += bytes([sum((v&1)<<(7-i) for i,v in enumerate(vals)),sum((v>>1)<<(7-i) for i,v in enumerate(vals))])
    binary[358*16:360*16]=patterns
    binary[360*16+358:360*16+360]=bytes([101,101])
    binary[360*16+360+358:360*16+720]=bytes([binary[360*16+360+357]])*2
    (ROOT/'gfx/peon_maps/valley.bin').write_bytes(binary)
    (ROOT/'gfx/pack/peon_atlas_fog.2bpp').write_bytes(patterns)
    native.save(OUT/'valley_overview_compiler.png')
    native.resize((640,576),Image.Resampling.NEAREST).save(OUT/'valley_overview_compiler_4x.png')
    asm=['; Generated exact seven-sector projections. World cells are 16x16.', 'PeonOverviewProjectionTable:']
    for key,row in projections.items():
        ident=row['zone']; gw,gh=row['collision_size']
        asm += [f'\tdb {key}, {gw}, {gh}',f'\tdw PeonOverview{ident}X, PeonOverview{ident}Y']
    asm += ['\tdb 0']
    for row in projections.values():
        ident=row['zone']
        for axis in ('X','Y'):
            asm += [f'PeonOverview{ident}{axis}:','\tdb '+', '.join(map(str,row[f'{axis.lower()}_centers']))]
    (ROOT/'gfx/pack/peon_valley_overview_geometry.asm').write_text('\n'.join(asm)+'\n')
    asm = ['; Generated fog flags and rectangles, local to the fog helper bank.', 'PeonAtlasSectorFlagTable:']
    for key,row in projections.items():
        asm += [f'\tdb {key}',f"\tdw {row['discovery_flag']}"]
    asm += ['\tdb 0','PeonAtlasFogRectTable:']
    for row in projections.values():
        asm += [f"\tdw {row['discovery_flag']}",'\tdb '+', '.join(map(str,row['fog_tiles']))]
    asm += ['\tdw 0']
    (ROOT/'gfx/pack/peon_valley_fog_tables.asm').write_text('\n'.join(asm)+'\n')
    # Keep unrelated regional projections and room-door transforms unchanged.
    old=(ROOT/'gfx/pack/peon_atlas_geometry.asm').read_text()
    for name,x,y in (('SARKOTH',4,4),('CAVE_ENTRANCE',5,2)):
        for axis,value in (('X',x),('Y',y)):
            old=re.sub(rf'(DEF PEON_ATLAS_{name}_WORLD_{axis} EQU )\d+',rf'\g<1>{value}',old)
    (ROOT/'gfx/pack/peon_atlas_geometry.asm').write_text(old)
    points={
      'GORNEK_REPORT': {'map_id':14,'xy':[10,9]}, 'FOREMAN': {'map_id':14,'xy':[8,17]},
      'LAZY': {'map_id':14,'xy':[5,16]}, 'GAL GAR': {'map_id':15,'xy':[8,10]},
      'HANAZUA': {'map_id':26,'xy':[3,4]}, 'ZUREETHA': {'map_id':25,'xy':[6,4]},
      'SARKOTH': {'map_id':27,'xy':[4,4]}, 'CAVE_ENTRANCE': {'map_id':28,'xy':[5,2]},
      'OUTSIDE_IMP_1': {'map_id':28,'xy':[4,5]}, 'OUTSIDE_IMP_2': {'map_id':28,'xy':[6,4]},
      **{f'CACTUS{i}':{'map_id':15,'xy':xy} for i,xy in enumerate(([7,7],[23,9],[9,17]),1)}}
    # Resolve visible giver cells directly from actual actor rows.
    for identity,name,script in (('FOREMAN','TheDen','TheDenForemanScript'),('GAL GAR','ValleyOfTrials','ValleyOfTrialsGuideScript')):
        match=re.search(rf'object_event\s+(\d+),\s*(\d+),[^\n]+\b{script}\b',(ROOT/f'maps/{name}.asm').read_text())
        if match: points[identity]['xy']=list(map(int,match.groups()))
    manifest=dict(schema_version=1,page=1,default_in_maps=[14,15,25,26,27,28,29],
        projections=projections,points=points,binary='gfx/peon_maps/valley.bin',
        binary_sha256=hashlib.sha256(binary).hexdigest(),
        fog=dict(bank=1,tiles=[102,103],palette=7,pattern_file='gfx/pack/peon_atlas_fog.2bpp'),
        glyph_vram='bank0 $8000..$802f',oam_convention=dict(x_offset=4,y_offset=12),
        native_pixel_size=[160,144],runtime_capture=False,
        old_save_bridge='Legacy Den/Valley discovery enables sector1/2 only.',
        scope='Seven compact geographic sectors; first two maps retain their scrolling dimensions.')
    (OUT/'geometry_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Compiled full Valley overview, seven fog rectangles and exact native projections.')

if __name__=='__main__': main()
