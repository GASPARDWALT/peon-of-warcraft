#!/usr/bin/env python3
"""Polish the retained world without changing map IDs, warps or collisions.

The published 1435e70 inputs are the immutable source, so running this tool
again cannot compound pixel reduction.  Only same-palette 8x8 tiles differing
by at most three pixels are merged.  Sixteen released slots hold a genuinely
native, full-resolution dry tree, adapted from our prepared deadthorn art.
Room fixtures rearrange existing tiles; the native budget remains 192.

The PNG maps are compiler reconstructions, not emulator screenshots.
"""
from collections import Counter, defaultdict, deque
from io import BytesIO
from pathlib import Path
import hashlib
import json
import re
import subprocess

from PIL import Image, ImageDraw

import build_durotar_world as world
from build_peon_durotar_trees import deadthorn

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/deep_polish/world'
BASELINE = '1435e70'
DIMS = dict(world.DIMS, PeonTrollHut=(6,5), PeonOrcHut=(6,5),
            PeonOrcInn=(6,5), PeonTrollInn=(6,5))
ROOM_ORIGIN = {'PeonTrollHut':'SenjinVillage', 'PeonTrollInn':'SenjinVillage',
               'PeonOrcHut':'RazorHill', 'PeonOrcInn':'RazorHill'}
TREE_PLACEMENTS = {
    'TheDen':[(1,3),(9,3)],
    'ValleyOfTrials':[(5,4),(8,8),(14,3)],
    'DurotarRoad':[(5,3),(8,5)],
    'RazorHill':[(9,5)], 'OrgrimmarGate':[(3,7)],
}


def original(path):
    return subprocess.check_output(['git','show',f'{BASELINE}:{path}'], cwd=ROOT)


def tile_id(index):
    return index if index < 96 else index + 32


def distance(a,b):
    return sum(x != y for x,y in zip(a,b))


def read_tiles(sheet, attributes):
    return [(sheet.crop((i%16*8,i//16*8,i%16*8+8,i//16*8+8)).tobytes(),
             (attributes[tile_id(i)//2] >> (tile_id(i)%2*4)) & 7)
            for i in range(192)]


def release_slots(tiles, count, usage):
    groups={i:[i] for i in range(len(tiles))}
    merges=[]
    for _ in range(count):
        candidates=[]
        for slave,members in groups.items():
            # Soil repeats across hundreds of cells: retain its complete grain
            # rather than exchanging background character for a sparse tree.
            # The primary road grain is likewise never retired.
            if tiles[slave][1]==1 or slave==7: continue
            for master,other in groups.items():
                if slave==master or tiles[slave][1]!=tiles[master][1]: continue
                errors=[distance(tiles[m][0],tiles[master][0]) for m in members]
                if max(errors)>3: continue
                # Prefer the smallest visible change, then the frequently used
                # representative.  No palette, transparency or shape resampling.
                weighted=sum(error*usage[tile_id(m)] for m,error in zip(members,errors))
                candidates.append((weighted,max(errors),sum(errors),
                                   -sum(usage[tile_id(m)] for m in other),slave,master))
        assert candidates, 'Could not free enough slots within the three-pixel bound'
        *_,slave,master=min(candidates)
        groups[master]+=groups.pop(slave)
        merges.append({'retired_index':slave,'representative_index':master})
    mapping={member:master for master,members in groups.items() for member in members}
    errors=[distance(tiles[i][0],tiles[mapping[i]][0]) for i in range(len(tiles))]
    assert max(errors)<=3
    assert all(tiles[i][1]==tiles[mapping[i]][1] for i in range(len(tiles)))
    return groups,mapping,merges,errors


def composed(meta, sources):
    return bytes(meta[block*16+tile] for block,tile in sources)


def fixtures(base_meta):
    # Full metatile collision semantics are assigned separately.  Every source
    # is an already allocated tile with its established palette.
    bed=[(40,i) for i in range(16)]
    for i in (0,1,2,3,4,7,8,11,12,15): bed[i]=(32,i)
    # The weaving uses the timber floor plus a narrow hide strip down the center.
    mat=[(32,i) for i in range(16)]
    for i in (5,9): mat[i]=(5,i)
    table=[(41,i) for i in range(16)]
    for i in (0,1,2,3,4,7,8,11,12,13,14,15): table[i]=(32,i)
    shrine=[(32,i) for i in range(16)]
    for i in (5,6,9,10): shrine[i]=(36,i)
    return [('darkspear_bedroll',bed,'WALL'),
            ('darkspear_table',table,'WALL'),
            ('woven_timber_floor',mat,'FLOOR'),
            ('darkspear_spirit_mask',shrine,'WALL')]


def edit_maps(block_ids):
    maps={name:list(original(f'maps/{name}.blk')) for name in DIMS}
    for name,places in TREE_PLACEMENTS.items():
        w,_=DIMS[name]
        for x,y in places:
            assert maps[name][y*w+x]==37,(name,x,y,'tree must replace an existing boulder')
            maps[name][y*w+x]=block_ids['deadthorn_tree']
    # Keep the existing east-west transition and its saved warp tile. Stone
    # jambs on the mountain boundary make the fortified Valley exit identifiable.
    for x,y in ((15,5),(15,6),(15,7)):
        assert maps['ValleyOfTrials'][y*16+x]==1
        maps['ValleyOfTrials'][y*16+x]=33
    # Readable branches lead to the vendor alcove and class camp, preserving
    # floor collision at every cell and every current quest actor position.
    name='TheDen';w,_=DIMS[name]
    added={(4,3),(4,4),(4,6),(4,7),(3,7),(3,8),(2,8)}
    roads={((i%w),(i//w)) for i,b in enumerate(maps[name]) if b in range(17,27) or b in (2,16)}
    roads|=added
    for x,y in added:
        assert maps[name][y*w+x] in (8,13,38)
    world.build_blocks()
    for x,y in roads:
        if maps[name][y*w+x]==16: continue
        neighbours={c for c,(dx,dy) in {'N':(0,-1),'S':(0,1),'E':(1,0),'W':(-1,0)}.items()
                    if (x+dx,y+dy) in roads}
        maps[name][y*w+x]=world.road_shape(neighbours)
    # The orc hearth has sandstone aisles and a short red central rug. The troll
    # rooms have woven timber and a Darkspear ritual mask. No obstacle is added,
    # moved or removed; the original bed/table event cells remain meaningful.
    name='PeonOrcHut';w,_=DIMS[name]
    for x,y in ((2,1),(3,1),(3,3)): maps[name][y*w+x]=7
    for name in ('PeonTrollHut','PeonTrollInn'):
        maps[name]=[block_ids['woven_timber_floor'] if b==5 else (32 if b==7 else b)
                    for b in maps[name]]
    maps['PeonTrollHut'][1*6+4]=block_ids['darkspear_spirit_mask']
    for pos,b in enumerate(maps['PeonTrollInn']):
        if b==40: maps['PeonTrollInn'][pos]=block_ids['darkspear_bedroll']
        elif b==41: maps['PeonTrollInn'][pos]=block_ids['darkspear_table']
    maps['PeonTrollInn'][1*6+4]=39 # Warm ground hearth instead of the tall brazier.
    maps['PeonOrcInn'][2*6+1]=32 # Serving aisle distinctly paved in timber.
    return maps


def collision_rows(source):
    return [tuple(line.split('tilecoll',1)[1].split(';',1)[0].replace(' ','').split(','))
            for line in source.splitlines() if 'tilecoll' in line]


def events(name, label, count):
    pattern=rf'^\s*{label}\s+(\d+),\s*(\d+),\s*(.+)'
    result=[]
    for match in re.finditer(pattern,(ROOT/f'maps/{name}.asm').read_text(),re.M):
        fields=[s.strip() for s in match[3].split(',')]
        result.append({'xy':tuple(map(int,match.groups()[:2])), 'fields':fields[:count]})
    return result


def validate(maps, collisions):
    baseline_coll=collision_rows(original('data/tilesets/peon_collision.asm').decode())
    results={}
    for name,data in maps.items():
        w,h=DIMS[name];old=original(f'maps/{name}.blk')
        assert len(data)==len(old)==w*h and 0 not in data
        # This stronger guarantee also preserves arbitrary old save positions.
        assert all(baseline_coll[a]==collisions[b] for a,b in zip(old,data)),name
        warps=events(name,'warp_event',2)
        actors=events(name,'object_event',12)
        bgs=events(name,'bg_event',2)
        def collision(p):
            x,y=p
            if not (0<=x<w*2 and 0<=y<h*2): return 'WALL'
            return collisions[data[y//2*w+x//2]][(y%2)*2+x%2]
        entrances=[p['xy'] for p in warps]
        start=entrances[0] if entrances else world.OBJECTIVES[name][0]
        reached={start};q=deque([start])
        while q:
            x,y=q.popleft()
            for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if p not in reached and collision(p)!='WALL': reached.add(p);q.append(p)
        assert all(p in reached for p in entrances),(name,'disconnected warp')
        for npc in actors:
            # Some opening objects are cinematic rather than playable. All
            # playable actor positions and their approach rings remain intact.
            if name in ('PeonOpening','GrommashHold'): continue
            x,y=npc['xy']
            assert collision((x,y))!='WALL',(name,'actor on wall',npc)
            assert any(p in reached for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))),(
                name,'unreachable actor',npc)
        for bg in bgs:
            x,y=bg['xy']
            assert any(p in reached for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))),(
                name,'unreachable background interaction',bg)
        results[name]={'all_saved_cells_preserve_collision':True,
            'connected_warps':len(entrances),'actors_approachable':len(actors),
            'background_events_approachable':len(bgs),'walkable_cells':len(reached),
            'changed_blocks':sum(a!=b for a,b in zip(old,data)),
            'sha256':hashlib.sha256(bytes(data)).hexdigest()}
    by_hash=defaultdict(list)
    for name,data in maps.items(): by_hash[hashlib.sha256(bytes(data)).hexdigest()].append(name)
    assert not any(len(names)>1 for names in by_hash.values()),'Duplicate playable map arrays'
    return results


def render(name,data,sheet,meta,attributes):
    width,height=DIMS[name]
    palettes=world.REGION_BGS.get(ROOM_ORIGIN.get(name,name),world.BG)
    canvas=Image.new('RGB',(width*32,height*32))
    for pos,block in enumerate(data):
        for j,tid in enumerate(meta[block*16:block*16+16]):
            i=tid if tid<96 else tid-32
            tile=sheet.crop((i%16*8,i//16*8,i%16*8+8,i//16*8+8))
            pal=(attributes[tid//2]>>(tid%2*4))&7
            colours=[tuple(((n>>3)<<3)|((n>>3)>>2) for n in c) for c in palettes[pal]]
            tile.putpalette([n for c in colours for n in c]+[0]*756)
            canvas.paste(tile.convert('RGB'),((pos%width)*32+(j%4)*8,(pos//width)*32+(j//4)*8))
    return canvas


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'maps').mkdir(exist_ok=True);(OUT/'before').mkdir(exist_ok=True)
    (OUT/'props').mkdir(exist_ok=True)
    old_sheet=Image.open(BytesIO(original('gfx/tilesets/peon.png')))
    old_meta=original('data/tilesets/peon_metatiles.bin')
    old_attributes=original('gfx/tilesets/peon_palette_map.bin')
    old_collision=original('data/tilesets/peon_collision.asm').decode()
    tiles=read_tiles(old_sheet,old_attributes)
    usage=Counter()
    for name in DIMS:
        for b in original(f'maps/{name}.blk'): usage.update(old_meta[b*16:b*16+16])
    tree=deadthorn().point([0,3,2,1,1]+[0]*251)
    tree_tiles=[(tree.crop((x*8,y*8,x*8+8,y*8+8)).tobytes(),5)
                for y in range(4) for x in range(4)]
    new_patterns=[key for key in dict.fromkeys(tree_tiles) if key not in tiles]
    groups,old_representative,merges,errors=release_slots(tiles,len(new_patterns),usage)
    compiled_tiles=[tiles[i] for i in sorted(groups)]+new_patterns
    lookup={key:i for i,key in enumerate(compiled_tiles)}
    assert len(compiled_tiles)==192 and len(lookup)==192
    native_remap={tile_id(i):tile_id(lookup[tiles[old_representative[i]]]) for i in range(192)}
    meta=bytearray(native_remap[tid] for tid in old_meta)
    base_meta=bytes(meta)
    rows=old_collision.splitlines();ids={}
    ids['deadthorn_tree']=len(meta)//16
    meta.extend(tile_id(lookup[key]) for key in tree_tiles)
    rows.append(f'\ttilecoll WALL, WALL, WALL, WALL ; {ids["deadthorn_tree"]:02x} deadthorn_tree')
    for name,refs,collision in fixtures(base_meta):
        ids[name]=len(meta)//16
        meta.extend(composed(base_meta,refs))
        rows.append(f'\ttilecoll {", ".join([collision]*4)} ; {ids[name]:02x} {name}')
    source='\n'.join(rows)+'\n'
    sheet=Image.new('P',(128,96));sheet.putpalette(old_sheet.getpalette())
    attributes=[7]*256
    for i,(pixels,pal) in enumerate(compiled_tiles):
        image=Image.frombytes('P',(8,8),pixels)
        sheet.paste(image,(i%16*8,i//16*8))
        attributes[tile_id(i)]=pal|(8 if i>=96 else 0)
    packed=bytes(attributes[i]|attributes[i+1]<<4 for i in range(0,256,2))
    maps=edit_maps(ids)
    checks=validate(maps,collision_rows(source))
    sheet.save(ROOT/'gfx/tilesets/peon.png')
    (ROOT/'data/tilesets/peon_metatiles.bin').write_bytes(meta)
    (ROOT/'gfx/tilesets/peon_palette_map.bin').write_bytes(packed)
    (ROOT/'data/tilesets/peon_collision.asm').write_text(source)
    for name,data in maps.items():
        (ROOT/f'maps/{name}.blk').write_bytes(bytes(data))
        image=render(name,data,sheet,meta,packed)
        image.save(OUT/'maps'/f'{name}.png')
        image.resize((image.width*2,image.height*2),Image.Resampling.NEAREST).save(
            OUT/'maps'/f'{name}_2x.png')
        render(name,original(f'maps/{name}.blk'),old_sheet,old_meta,old_attributes).save(
            OUT/'before'/f'{name}.png')
    # Transparent public tree uses the actual reduced native indices, with
    # index zero masked only where the original proposal had transparency.
    colors=world.BG[5]
    transparent=Image.new('RGBA',(32,32))
    transparent.putdata([colors[int(p)]+(255,) if src else (0,0,0,0)
                         for p,src in zip(tree.tobytes(),deadthorn().tobytes())])
    transparent.save(OUT/'props'/'deadthorn_tree_native.png')
    transparent.resize((256,256),Image.Resampling.NEAREST).save(
        OUT/'props'/'deadthorn_tree_native_8x.png')
    comparison=Image.new('RGB',(768,448),'#332a26');d=ImageDraw.Draw(comparison)
    for i,name in enumerate(('PeonOrcHut','PeonTrollHut','PeonOrcInn','PeonTrollInn')):
        image=Image.open(OUT/'maps'/f'{name}.png').resize((384,320),Image.Resampling.NEAREST)
        # 2x2 rooms use 2x in the individual files; the contact sheet displays
        # at native size to retain all four names and the honest renderer label.
        image=image.resize((192,160),Image.Resampling.NEAREST)
        x=(i%2)*384+16;y=(i//2)*200+32
        comparison.paste(image,(x,y));d.text((x+204,y+50),name,fill='#f7dea5')
    d.text((16,422),'Native terrain reconstruction / actors added by ROM at runtime',fill='#f7dea5')
    comparison.save(OUT/'interior_identity_contact_sheet.png')
    report={'passed':True,'baseline':BASELINE,'runtime_capture':False,
            'native_tiles':len(compiled_tiles),'tile_budget':192,
            'existing_block_ids_preserved':42,'appended_block_ids':ids,
            'map_ids_dimensions_warps_actors_unchanged':True,
            'retired_tile_count':len(merges),'max_pixel_changes_per_old_8x8_tile':max(errors),
            'changed_old_tile_patterns':sum(bool(n) for n in errors),
            'old_tile_pixel_changes':sum(errors),'same_palette_only':True,
            'all_soil_tile_patterns_protected':True,
            'merges':merges,'per_old_tile_pixel_errors':errors,
            'tree_placements':TREE_PLACEMENTS,'map_checks':checks,
            'byte_identical_playable_map_pairs':[],
            'limitations':['The Den and Razor Hill still share one Orc Inn room ID.',
                           'Residences remain shared within each race; the exit returns to its originating door.',
                           'Seven fixed screen zones await the requested final path drawing.',
                           'The native tree palette is reduced from four opaque colours to three.']}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('passed','native_tiles','retired_tile_count',
          'max_pixel_changes_per_old_8x8_tile','old_tile_pixel_changes','tree_placements')},indent=2))


if __name__=='__main__': main()
