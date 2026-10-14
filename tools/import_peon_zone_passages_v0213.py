#!/usr/bin/env python3
"""Import supplied inn posts at world thresholds, retaining every other native tile.

This is a final layer over a map-local native packet, never a scenery generator.
--input-dir/--map-dir allow a canonical decor import to precede this stage.
Original animated patterns0..3, font gap96..127 and NPC VRAM remain protected.
Preview records actual over-budget results; --apply refuses any overflow.
"""
from collections import deque
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
from PIL import Image
import import_peon_user_environment_v0211 as native

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/zone_passages_v0213'
GFX = ROOT / 'gfx/zone_passages_v0213'
SOURCE = ROOT / 'references/characters/razor_hill_inn_gbc/razor_hill_inn_interior_192x160.png'
CAVE = ROOT / 'references/characters/peon_of_warcraft_environment_pack_v2_art_quality/durotar_valley/cave_entrance_durotar_01_64x64.png'
# Complete native horn+wood shaft+dark outline; neighboring red door frame
# is a separate object. Native8px crops retain the whole visible pillar.
CROPS = {'left': (74,128,82,160), 'right': (110,128,118,160)}
NAMES = ('TheDen','ValleyOfTrials','PeonValleyCrossroads','PeonHanazuaCamp',
         'PeonSarkothBasin','PeonCaveApproach','PeonValleyExit','DurotarRoad',
         'SenjinVillage','RazorHill','OrgrimmarGate')
CONSTANTS = {'TheDen':'THE_DEN','ValleyOfTrials':'VALLEY_OF_TRIALS',
 'PeonValleyCrossroads':'PEON_VALLEY_CROSSROADS','PeonHanazuaCamp':'PEON_HANAZUA_CAMP',
 'PeonSarkothBasin':'PEON_SARKOTH_BASIN','PeonCaveApproach':'PEON_CAVE_APPROACH',
 'PeonValleyExit':'PEON_VALLEY_EXIT','DurotarRoad':'DUROTAR_ROAD',
 'SenjinVillage':'SENJIN_VILLAGE','RazorHill':'RAZOR_HILL','OrgrimmarGate':'ORGRIMMAR_GATE',
 'BurningBladeCavern':'BURNING_BLADE_CAVERN'}
WORLD = set(CONSTANTS.values())
# Passage orientation retains published world IDs/coordinates and both corridors.
ORIENTATION = {'TheDen': {1:'horizontal',4:'horizontal'},
 'ValleyOfTrials': {1:'horizontal',2:'horizontal',3:'vertical'},
 'PeonValleyCrossroads': {1:'vertical',2:'vertical',3:'horizontal'},
 'PeonHanazuaCamp': {1:'horizontal',2:'vertical'},
 'PeonSarkothBasin': {1:'vertical',2:'horizontal'},
 'PeonCaveApproach': {1:'vertical'}, 'PeonValleyExit': {1:'horizontal',2:'horizontal'},
 'DurotarRoad': {1:'horizontal',2:'vertical',3:'vertical'},
 'SenjinVillage': {1:'vertical'}, 'RazorHill': {1:'vertical',2:'vertical'},
 'OrgrimmarGate': {1:'vertical'}}


def sha(data): return hashlib.sha256(data).hexdigest()


def parse_events(text):
    return [(int(x),int(y),dest,int(index)) for x,y,dest,index in
            re.findall(r'warp_event\s+(\d+),\s*(\d+),\s*(\w+),\s*(\d+)',text)]


def original_text(name):
    # Discard only this layer's append-only duplicates on a repeat run.
    text=(ROOT/f'maps/{name}.asm').read_text()
    return re.sub(r'\t; BEGIN WORLD THRESHOLDS V0213.*?\t; END WORLD THRESHOLDS V0213\n', '', text, flags=re.S)


def actor_cells(text):
    result=set()
    for x,y,sprite,motion in re.findall(r'object_event\s+(\d+),\s*(\d+),\s*(\w+),\s*(\w+)',text):
        if sprite=='SPRITE_NONE': continue
        x,y=int(x),int(y);result.add((x,y))
        if motion=='SPRITEMOVEDATA_WALK_LEFT_RIGHT': result.update(((x-1,y),(x+1,y)))
        if motion=='SPRITEMOVEDATA_WALK_UP_DOWN': result.update(((x,y-1),(x,y+1)))
    return result


def rows(path):
    return [tuple(v.strip() for v in line.split('tilecoll')[1].split(';')[0].split(','))
            for line in path.read_text().splitlines() if 'tilecoll' in line]


def read_packet(name, folder):
    source=(folder/f'{name}.2bpp').read_bytes()
    assert len(source)%16==0 and 192<=len(source)//16<=224, (name,'expected native packet or bounded diagnostic extension')
    attrs=(folder/f'{name}_palmap.bin').read_bytes()
    priority=(folder/f'{name}_priority.bin').read_bytes()
    bank=[]
    for i in range(len(source)//16):
        pixels=bytes(((source[i*16+y*2]>>(7-x))&1)|(((source[i*16+y*2+1]>>(7-x))&1)<<1)
                     for y in range(8) for x in range(8))
        tid=i if i<96 else i+32
        bank.append(native.Tile(pixels,(attrs[tid//2]>>(tid%2*4))&7,
                                bool(priority[tid//8]&(0x80>>(tid%8)))))
    meta=(folder/f'{name}_meta.bin').read_bytes()
    assert not any(96<=t<128 for t in meta),(name,'background packet uses reserved font logical ID')
    blocks=[[bank[t if t<96 else t-32] for t in meta[i:i+16]] for i in range(0,len(meta),16)]
    return bank,blocks,rows(folder/f'{name}_coll.asm')


def render(grid,pals):
    image=Image.new('RGB',(len(grid[0])*8,len(grid)*8))
    for y,row in enumerate(grid):
        for x,t in enumerate(row):image.paste(native.tile_rgb(t,pals),(x*8,y*8))
    return image


def around(x,y): return ((x-1,y),(x+1,y),(x,y-1),(x,y+1))


def reachable(cells,seed,occupied=(),absorbing=()):
    h,w=len(cells),len(cells[0]);occupied=set(occupied);absorbing=set(absorbing)
    seen={seed};todo=deque([seed])
    while todo:
        p=todo.popleft()
        if p in absorbing and p!=seed:continue
        for q in around(*p):
            x,y=q
            if 0<=x<w and 0<=y<h and q not in seen and q not in occupied and cells[y][x]!='WALL':
                seen.add(q);todo.append(q)
    return seen


def prepare(name,folder,mapfolder,source,cave,capacity=192):
    w,h=native.DIMS[name];bank,blocks,collision=read_packet(name,folder)
    data=(mapfolder/f'{name}.blk').read_bytes()
    assert len(data)==w*h
    grid=[[None]*(w*4) for _ in range(h*4)]
    cells=[[None]*(w*2) for _ in range(h*2)]
    for pos,b in enumerate(data):
        for j,t in enumerate(blocks[b]):grid[pos//w*4+j//4][pos%w*4+j%4]=t
        for q,c in enumerate(collision[b]):cells[pos//w*2+q//2][pos%w*2+q%2]=c
    before=[list(row) for row in grid];oldcells=[list(row) for row in cells]
    pals=native.map_palettes(name,native.parse_palettes(ROOT/'gfx/tilesets/peon_bg.pal'))
    original=render(grid,pals);composition=original.copy();mask=Image.new('1',original.size)
    text=original_text(name);warps=parse_events(text);actors=actor_cells(text)
    triggers={(int(x),int(y)) for x,y in re.findall(r'coord_event\s+(\d+),\s*(\d+)',text)}
    reverse_names={v:k for k,v in CONSTANTS.items()}
    for index,(x,y,dest,dest_index) in enumerate(warps,1):
        if dest not in WORLD:continue
        destination=parse_events(original_text(reverse_names[dest]))
        assert 1<=dest_index<=len(destination),(name,index,'missing destination warp')
        back=destination[dest_index-1]
        assert back[2:]==(CONSTANTS[name],index),(name,index,'non-reciprocal published link',back)
    imports=[];thresholds=[];allworld=[]
    def overlay(image,xy,description):
        x,y=xy;ww,hh=image.size
        assert x>=0 and y>=0 and x+ww<=w*32 and y+hh<=h*32,(name,description,xy)
        assert x%8==y%8==ww%8==hh%8==0
        rgba=Image.new('RGBA',(ww,hh));rgba.alpha_composite(image.convert('RGBA'))
        composed=composition.crop((x,y,x+ww,y+hh)).convert('RGBA')
        composed.alpha_composite(rgba);composition.paste(composed.convert('RGB'),xy)
        for ty in range(hh//8):
            for tx in range(ww//8):
                box=(tx*8,ty*8,tx*8+8,ty*8+8)
                alpha=rgba.getchannel('A').crop(box)
                if alpha.getbbox():
                    grid[y//8+ty][x//8+tx]=native.convert_tile(composed.crop(box).convert('RGB'),pals,alpha)
                    mask.paste(1,(x+tx*8,y+ty*8,x+tx*8+8,y+ty*8+8))
        imports.append(description|{'world_rect':[x,y,x+ww,y+hh],'native_scale':1})
    for index,(x,y,dest,dest_index) in enumerate(warps,1):
        if dest not in WORLD:continue
        xb,yb=x//2*2,y//2*2
        corridor={(xb+dx,yb+dy) for dy in range(2) for dx in range(2)}
        orientation='vertical' if name=='PeonCaveApproach' and dest=='BURNING_BLADE_CAVERN' else ORIENTATION[name][index]
        threshold={p for p in corridor if (p[1]==y if orientation=='vertical' else p[0]==x)}
        allworld.extend(sorted(threshold))
        assert not threshold & actors,(name,'warp threshold actor overlap',threshold & actors)
        # The old primitive banner/arch on a world portal is replaced by its
        # existing unobstructed road/sand tile. This never touches a building.
        ground_ident=38 if name.startswith('Peon') else 8
        # Use a nearby native road block only when it is floor-only and shared.
        floorblocks=[i for i in set(data) if collision[i]==('FLOOR',)*4]
        assert ground_ident in set(data) or floorblocks
        if ground_ident not in set(data):ground_ident=min(floorblocks)
        ground=blocks[ground_ident]
        for ty in range(4):
            for tx in range(4):grid[yb*2+ty][xb*2+tx]=ground[ty*4+tx]
        cleared=render([[ground[ty*4+tx] for tx in range(4)] for ty in range(4)],pals)
        composition.paste(cleared,(xb*16,yb*16));mask.paste(1,(xb*16,yb*16,xb*16+32,yb*16+32))
        for cx,cy in corridor:cells[cy][cx]='WARP_PANEL' if (cx,cy) in threshold else 'FLOOR'
        if name=='PeonCaveApproach' and dest=='BURNING_BLADE_CAVERN':
            # Full provided64x64 arch, with the existing mouth/landing retained.
            overlay(cave,(48,0),{'asset':str(CAVE.relative_to(ROOT)),'source_rect':[0,0,64,64],
                    'type':'cave entrance','source_pixels_changed':False,'spike_posts':False})
        else:
            if orientation=='vertical':positions=[(xb-1,yb),(xb+2,yb)]
            else:positions=[(x,yb-2),(x,yb+2)]
            # Historical banners/stumps immediately beside a gateway were
            # threshold markers. Remove their complete obsolete32px native
            # metatile when the supplied post replaces it; a half banner is
            # not preserved scenery. Buildings are never these IDs.
            marker_positions=set()
            for cx,cy in positions:
                for py in (cy,cy+1):
                    if data[py//2*w+cx//2] in (6,33):marker_positions.add((cx//2,py//2))
            for bx,by in sorted(marker_positions):
                marker_backdrop=blocks[1]
                for ty in range(4):
                    for tx in range(4):grid[by*4+ty][bx*4+tx]=marker_backdrop[ty*4+tx]
                cliff=render([[marker_backdrop[ty*4+tx] for tx in range(4)] for ty in range(4)],pals)
                composition.paste(cliff,(bx*32,by*32));mask.paste(1,(bx*32,by*32,bx*32+32,by*32+32))
                imports.append({'type':'obsolete gateway marker removed','old_metatile':data[by*w+bx],
                                'world_rect':[bx*32,by*32,bx*32+32,by*32+32],
                                'replacement':'unchanged existing native cliff tile','portal_index':index})
            for label,(cx,cy) in zip(('left','right'),positions):
                body={(cx,cy),(cx,cy+1)}
                assert not body & actors,(name,index,'post on actor footprint',body & actors)
                assert not body & set((a,b) for a,b,_,_ in warps),(name,index,'post on published event')
                for a,b in body:
                    assert 0<=a<w*2 and 0<=b<h*2,(name,index,'post body outside map',a,b)
                    cells[b][a]='WALL'
                # Keep narrow supplied pillars at the inner edges of the two
                # existing16px wall cells. Their central32px corridor stays clear.
                offset=8 if orientation=='vertical' and label=='left' else 0
                overlay(source.crop(CROPS[label]),(cx*16+offset,cy*16),
                        {'asset':str(SOURCE.relative_to(ROOT)),'source_rect':list(CROPS[label]),
                         'type':'complete spiked horned post','side':label,'portal_index':index,
                         'source_pixels_changed':False,'body_cells':[list(p) for p in sorted(body)]})
        thresholds.append({'original_index':index,'original_xy':[x,y],'destination':dest,
                           'destination_index':dest_index,'cells':[list(p) for p in sorted(threshold)],
                           'corridor_cells':[list(p) for p in sorted(corridor)]})
    if name=='RazorHill':cells[16][5]='FLOOR' # documented front approach to published hut door6
    # Every pixel and palette/priority key outside documented overlay cells stays exact.
    preserved=0
    for y,row in enumerate(grid):
        for x,t in enumerate(row):
            if not mask.getpixel((x*8,y*8)):
                assert t==before[y][x],(name,'outside-art pixel changed',x,y);preserved+=1
    # NPCs, all published warp landings, and each two-way route remain usable.
    for x,y,_,_ in warps:assert cells[y][x]!='WALL',(name,'landing blocked',x,y)
    for x,y in actors:assert cells[y][x]==oldcells[y][x],(name,'actor collision changed',x,y)
    # Nearby routes may enter different cells of the same threshold. Treat a
    # whole threshold as absorbing, and test all destinations from each landing.
    reach_reports=[]
    for threshold in thresholds:
        seed=tuple(threshold['original_xy']);seen=reachable(cells,seed,actors,set(allworld))
        exits=[p for p in around(*seed) if 0<=p[0]<w*2 and 0<=p[1]<h*2 and p not in actors and cells[p[1]][p[0]]=='FLOOR']
        assert exits,(name,'arrival cannot leave without immediately re-warping',seed)
        # A neighboring activation lane is absorbing, so every route must
        # genuinely leave its arrival and approach the destination threshold.
        for other in thresholds:
            assert any(tuple(p) in seen for p in other['cells']),(name,'two-way route blocked',seed,other)
        old_seen=reachable(oldcells,seed,actors)
        for actor in actors:
            if any(p in old_seen for p in around(*actor)):
                assert any(p in seen for p in around(*actor)),(name,'NPC approach disconnected',actor)
        reach_reports.append({'arrival':list(seed),'reachable_cells':len(seen),'existing_npc_approaches_preserved':True,'safe_arrival_steps':[list(p) for p in exits]})
    # Append changed blocks; retain historical collision IDs for changeblock.
    result_blocks=[list(b) for b in blocks];result_rows=list(collision);newdata=bytearray(data)
    for by in range(h):
        for bx in range(w):
            block=[grid[by*4+dy][bx*4+dx] for dy in range(4) for dx in range(4)]
            row=tuple(cells[by*2+q//2][bx*2+q%2] for q in range(4))
            old=data[by*w+bx]
            if block==blocks[old] and row==collision[old]:continue
            matches=[i for i in range(len(result_blocks)) if result_blocks[i]==block and result_rows[i]==row]
            ident=matches[0] if matches else len(result_blocks)
            if not matches:result_blocks.append(block);result_rows.append(row)
            assert ident<128,(name,'metatile overflow',ident)
            newdata[by*w+bx]=ident
    active=set(newdata)|{1}
    active.update(int(v) for v in re.findall(r'changeblock\s+\d+,\s*\d+,\s*(\d+)',text))
    patterns=list(bank[:4]);lookup={t.key:i for i,t in enumerate(patterns)};meta=[]
    for ident,block in enumerate(result_blocks):
        if ident not in active:meta.extend([4]*16);continue
        for tile in block:
            if tile.key not in lookup:lookup[tile.key]=len(patterns);patterns.append(tile)
            i=lookup[tile.key];meta.append(i if i<96 else i+32)
    count=len(patterns)
    assert not any(96<=t<128 for t in meta),(name,'output reserved-font ID')
    if count<=capacity:assert max(meta)<(224 if capacity==192 else 248),(name,'output exceeds scoped native IDs')
    changed=[];relocations=[]
    safe=reachable(cells,tuple(thresholds[0]['original_xy']),actors) if thresholds else set()
    for y in range(h*2):
        for x in range(w*2):
            if cells[y][x]!=oldcells[y][x]:
                changed.append({'xy':[x,y],'before':oldcells[y][x],'after':cells[y][x]})
                if oldcells[y][x]!='WALL' and cells[y][x]=='WALL':
                    target=min((p for p in safe if p not in set(allworld) and p not in triggers),key=lambda p:(abs(p[0]-x)+abs(p[1]-y),p[1],p[0]))
                    relocations.append({'old':[x,y],'safe':list(target)})
    native_image=render(grid,pals)
    original.save(OUT/f'{name}_before_native.png');composition.save(OUT/f'{name}_source_composition.png')
    native_image.save(OUT/f'{name}_native.png')
    native_image.resize((native_image.width*3,native_image.height*3),Image.Resampling.NEAREST).save(OUT/f'{name}_native_3x.png')
    mask.save(OUT/f'{name}_changed_art_mask.png')
    report={'map':name,'base_packet_pattern_capacity':len(bank),'patterns':count,'pattern_budget':capacity,'fits':count<=capacity,
            'metatiles':len(result_blocks),'active_metatiles':len(active),'imports':imports,
            'thresholds':thresholds,'collision_changes':changed,'continue_relocations':relocations,
            'unaffected_native_tiles_exact':preserved,'native_grid_tiles':w*h*16,
            'two_way_actor_aware_bfs':reach_reports,'native_sha256':sha(native_image.tobytes()),
            'original_animated_tiles_0_to_3_preserved':True,'font_ids_96_to_127_reserved':True,
            'legacy_font_logical_ids_96_to_127_reserved':True,
            'font_portrait_bank1_9600_to_97ff_reserved':True,
            'extended_background_ids':[] if capacity==192 else [224,247],
            'extended_background_requires_scoped_allocator':capacity>192}
    outputs={}
    if count<=capacity:
        attrs=[7]*256;priority=bytearray(32)
        sheet=Image.new('P',(128,((capacity+15)//16)*8));sheet.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
        for i,t in enumerate(patterns):
            tid=i if i<96 else i+32;attrs[tid]=t.pal|(8 if i>=96 else 0)
            if t.priority:priority[tid//8]|=0x80>>(tid%8)
            sheet.paste(Image.frombytes('L',(8,8),t.pixels),(i%16*8,i//16*8))
        outputs={f'{name}.2bpp':b''.join(native.encode(t) for t in patterns)+bytes((capacity-count)*16),
                 f'{name}_meta.bin':bytes(meta),f'{name}_palmap.bin':bytes(attrs[i]|attrs[i+1]<<4 for i in range(0,256,2)),
                 f'{name}_priority.bin':bytes(priority),f'{name}_coll.asm':''.join('\tpeon_user_tilecoll '+', '.join(row)+f' ; {i:02x} preserved_or_post_body\n' for i,row in enumerate(result_rows)).encode()}
        sheet.save(GFX/f'{name}.png')
    (OUT/f'{name}.blk').write_bytes(newdata)
    duplicates=[];existing={(x,y) for x,y,_,_ in warps}
    for threshold in thresholds:
        for x,y in threshold['cells']:
            if (x,y) in existing:continue
            duplicates.append(f'\twarp_event {x}, {y}, {threshold["destination"]}, {threshold["destination_index"]} ; full clear threshold')
    if duplicates:
        insertion='\t; BEGIN WORLD THRESHOLDS V0213\n'+'\n'.join(duplicates)+'\n\t; END WORLD THRESHOLDS V0213\n'
        text=text.replace('\tdef_coord_events',insertion+'\tdef_coord_events',1)
    (OUT/f'{name}.asm').write_text(text)
    return outputs,bytes(newdata),text,report



def cave_return_threshold():
    """Cave exception keeps every native pixel; make its exit fully active."""
    text=original_text('BurningBladeCavern');warps=parse_events(text)
    existing={(x,y) for x,y,_,_ in warps};duplicates=[]
    for x,y,dest,index in warps:
        if dest!='PEON_CAVE_APPROACH':continue
        xb,yb=x//2*2,y//2*2
        for cy in (y,):
            for cx in range(xb,xb+2):
                if (cx,cy) not in existing:
                    duplicates.append(f'\twarp_event {cx}, {cy}, {dest}, {index} ; full cave return threshold')
    if duplicates:
        insertion='\t; BEGIN WORLD THRESHOLDS V0213\n'+'\n'.join(duplicates)+'\n\t; END WORLD THRESHOLDS V0213\n'
        text=text.replace('\tdef_coord_events',insertion+'\tdef_coord_events',1)
    return text,len(duplicates)



def verify_native(rom_path,sym_path):
    """Check exact cartridge bindings through the retained PeonUserEnv ABI."""
    cartridge=rom_path.read_bytes();syms={}
    for line in sym_path.read_text().splitlines():
        match=re.match(r'([0-9a-fA-F]+):([0-9a-fA-F]{4})\s+(\S+)',line)
        if match:syms[match[3]]=(int(match[1],16),int(match[2],16))
    def bound(label,content):
        assert label in syms,('missing native ABI symbol',label)
        bank,address=syms[label];offset=bank*0x4000+(address if bank==0 else address-0x4000)
        assert cartridge[offset:offset+len(content)]==content,('native bytes differ',label)
    def ptr(label,far=False):
        bank,address=syms[label]
        return (bytes([bank]) if far else b'')+address.to_bytes(2,'little')
    manifest=json.loads((OUT/'manifest.json').read_text());proof=[]
    assert len(manifest['maps'])==len(NAMES) and not manifest['partial_preview']
    codes={'FLOOR':0x00,'WALL':0x07,'WARP_PANEL':0x7c}
    header_bytes=bytearray();header_source=(ROOT/'data/tilesets/peon_user_environment_headers_v0211.asm').read_text()
    for line in header_source.splitlines():
        if line.strip().startswith('dba '):
            for label in line.split('dba',1)[1].split(','):header_bytes.extend(ptr(label.strip(),True))
        elif line.strip().startswith('dw '):
            for label in line.split('dw',1)[1].split(','):header_bytes.extend(ptr(label.strip()))
    bound('PeonUserEnvironmentHeaders',bytes(header_bytes))
    by_constant={v:k for k,v in CONSTANTS.items()}|{'PEON_TROLL_HUT':'PeonTrollHut',
        'PEON_ORC_HUT':'PeonOrcHut','PEON_ORC_INN':'PeonOrcInn','PEON_TROLL_INN':'PeonTrollInn'}
    map_numbers={name:i+12 for i,name in enumerate(native.DIMS)}
    for report in manifest['maps']:
        name=report['map'];label='PeonUserEnv'+name
        packets={'GFX':'.2bpp.lz','Meta':'_meta.bin','PalMap':'_palmap.bin','Priority':'_priority.bin'}
        for suffix,file_suffix in packets.items():bound(label+suffix,(GFX/(name+file_suffix)).read_bytes())
        raw=(GFX/(name+'.2bpp')).read_bytes()
        assert len(raw)==manifest['native_pattern_capacity']*16,(name,'wrong native packet capacity')
        collision=rows(GFX/f'{name}_coll.asm')
        bound(label+'Coll',bytes(codes[value] for row in collision for value in row))
        source_blocks=(ROOT/f'maps/{name}.blk').read_bytes()
        assert source_blocks==(OUT/f'{name}.blk').read_bytes(),(name,'passage block map not applied')
        bound(name+'_Blocks',source_blocks)
        assert syms[label+'PalMap'][0]==syms['_LoadOverworldAttrmapPals'][0]
        assert syms[label+'Priority'][0]==syms['_LoadOverworldAttrmapPals'][0]
        proof.append({'map':name,'unique_patterns':report['patterns'],'capacity':report['pattern_budget'],
                      'retained_native_abi_labels_bound':True,'native_artwork_collision_and_blocks_exact':True})
    for name in (*NAMES,'BurningBladeCavern'):
        events=parse_events((ROOT/f'maps/{name}.asm').read_text())
        event_bytes=bytearray([0,0,len(events)])
        for x,y,dest,index in events:
            assert dest in by_constant,(name,'unknown Peon destination',dest)
            event_bytes.extend((y,x,index,26,map_numbers[by_constant[dest]]))
        bound(name+'_MapEvents',bytes(event_bytes))
        if name!='BurningBladeCavern':
            expected=next(r for r in manifest['maps'] if r['map']==name)
            for threshold in expected['thresholds']:
                for x,y in threshold['cells']:
                    assert (x,y,threshold['destination'],threshold['destination_index']) in events,(name,'activation lane missing',x,y)
    report={'rom_path':str(rom_path),'rom_sha256':sha(cartridge),'native_headers_match_retained_abi':True,
            'world_activation_lines_match_compiled_event_bytes':True,'ordinary_runtime_playtest':False,'maps':proof}
    (OUT/'native_binding_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'native_bindings_verified':len(proof),'world_warp_maps_verified':len(NAMES)+1,'rom_sha256':report['rom_sha256']}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--verify-rom',type=Path,help='Verify frozen ROM packet/event bindings without regenerating anything.')
    parser.add_argument('--symbols',type=Path,help='Same-build RGBDS .sym file for --verify-rom.')
    parser.add_argument('--input-dir',type=Path,default=ROOT/'gfx/tilesets/peon_user_environment_v0211')
    parser.add_argument('--map-dir',type=Path)
    parser.add_argument('--pattern-capacity',type=int,choices=(192,216),default=192,
                        help='216 requires the scoped outdoor bank1 extension; fonts and portraits retain their original slots.')
    parser.add_argument('--maps',nargs='+',choices=NAMES,help='Preview a staged subset; final apply normally uses all eleven maps.')
    args=parser.parse_args()
    if args.verify_rom:
        assert args.symbols,'--verify-rom requires --symbols'
        verify_native(args.verify_rom,args.symbols);return
    OUT.mkdir(parents=True,exist_ok=True);GFX.mkdir(parents=True,exist_ok=True)
    names=args.maps or NAMES
    baseline=OUT/'baseline';baseline.mkdir(exist_ok=True)
    for name in names:
        target=baseline/f'{name}.blk'
        if not target.exists():target.write_bytes((ROOT/f'maps/{name}.blk').read_bytes())
    mapfolder=args.map_dir or baseline
    source=Image.open(SOURCE).convert('RGB');cave=Image.open(CAVE).convert('RGBA')
    results=[];prepared=[]
    for name in names:
        outputs,data,text,report=prepare(name,args.input_dir,mapfolder,source,cave,args.pattern_capacity)
        results.append(report);prepared.append((name,outputs,data,text))
    cave_text,cave_duplicates=cave_return_threshold()
    (OUT/'BurningBladeCavern.asm').write_text(cave_text)
    manifest={'native_pattern_capacity':args.pattern_capacity,'partial_preview':set(names)!=set(NAMES),'cave_return_append_only_warps':cave_duplicates,'cave_interior_pixels_changed':False,
              'source_posts':str(SOURCE.relative_to(ROOT)),'source_posts_sha256':sha(SOURCE.read_bytes()),
              'source_cave':str(CAVE.relative_to(ROOT)),'source_cave_sha256':sha(CAVE.read_bytes()),
              'base_packet':str(args.input_dir),'base_maps':str(mapfolder),'source_redrawn':False,
              'source_scale':1,'conversion':'One existing regional GBC palette per8x8 overlay tile; nearest-color quantization is separate from unchanged supplied source pixels. Unaffected native tiles are never re-quantized.',
              'interiors_changed':False,'building_facades_changed':False,
              'preservation':'Every native tile outside recorded source-post/cave/cleared-old-world-threshold rectangles is identical, including palette and priority.',
              'warp_indices_preserved':True,'append_only_threshold_cells':True,'activation_line_width_cells':2,'arrival_inward_step_is_clear_floor':True,'applied':False,'maps':results}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({r['map']:{'patterns':r['patterns'],'fits':r['fits'],'metatiles':r['metatiles']} for r in results}))
    if not all(r['fits'] for r in results):
        if args.apply:raise SystemExit('Refusing native apply: actual tile budget overflow; source previews retained.')
        return
    graphics=[];attributes=[];headers=[];relocations=[]
    for name,outputs,data,text in prepared:
        for path,content in outputs.items():(GFX/path).write_bytes(content)
        subprocess.run([str(ROOT/'tools/lzcompress'),'--',str(GFX/f'{name}.2bpp'),str(GFX/f'{name}.2bpp.lz')],check=True)
        label=f'PeonPassage{name}';folder=f'gfx/zone_passages_v0213/{name}'
        graphics += [f'SECTION "World passage {name} v0213", ROMX',label+'GFXV0213::',f'INCBIN "{folder}.2bpp.lz"',
                     label+'MetaV0213::',f'INCBIN "{folder}_meta.bin"',label+'CollV0213::',f'INCLUDE "{folder}_coll.asm"','']
        attributes += [label+'PalMapV0213::',f'INCBIN "{folder}_palmap.bin"',f'assert BANK({label}PalMapV0213) == BANK(_LoadOverworldAttrmapPals)',
                       label+'PriorityV0213::',f'INCBIN "{folder}_priority.bin"',f'assert BANK({label}PriorityV0213) == BANK(_LoadOverworldAttrmapPals)','']
        headers += [f'; {name}',f'\tdba {label}GFXV0213, {label}MetaV0213, {label}CollV0213',f'\tdw TilesetPeonAnim, {label}PriorityV0213, {label}PalMapV0213']
        report=next(r for r in results if r['map']==name)
        for move in report['continue_relocations']:relocations += ['\tmap_id '+CONSTANTS[name],'\tdb '+', '.join(map(str,move['old']+move['safe']))]
        if args.apply:
            (ROOT/f'maps/{name}.blk').write_bytes(data);(ROOT/f'maps/{name}.asm').write_text(text)
    (GFX/'graphics.asm').write_text('\n'.join(graphics)+'\n');(GFX/'palettes.asm').write_text('\n'.join(attributes)+'\n')
    (GFX/'headers.asm').write_text('\n'.join(headers)+'\n')
    (GFX/'continue_relocations.asm').write_text('; Append before the existing migration terminator.\n'+'\n'.join(relocations)+'\n')
    if args.apply:(ROOT/'maps/BurningBladeCavern.asm').write_text(cave_text)
    manifest['applied']=args.apply;(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
