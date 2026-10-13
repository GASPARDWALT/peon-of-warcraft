#!/usr/bin/env python3
"""Import supplied native decor pixels without redrawing art or moving events.

The source assets remain byte-exact. Color conversion is separate and each 8x8
cell selects one existing GBC background palette. No image is resized or cropped
out of its native canvas. Original 67 block meanings and every movement-cell
collision remains preserved except documented source body walls with safe
Continue relocation; full 32x48 palms add visual-only block aliases above
the old trunk anchor. This importer never runs an historical art generator.
"""
from pathlib import Path
from collections import Counter, deque
from dataclasses import dataclass
import argparse
import hashlib
import json
import re
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'references/characters/durotar_asset_pack_v1'
INN_SOURCES = ROOT / 'references/characters/razor_hill_inn_gbc'
NATIVE = ROOT / 'gfx/tilesets/peon_user_environment_v0211'
OUT = ROOT / 'references/generated/user_environment_v0211'
BASE = OUT / 'baseline'
DIMS = {'PeonOpening': (8, 6), 'GrommashHold': (8, 6), 'TheDen': (12, 10),
        'ValleyOfTrials': (16, 12), 'DurotarRoad': (12, 14), 'SenjinVillage': (12, 10),
        'RazorHill': (12, 10), 'OrgrimmarGate': (12, 10), 'BurningBladeCavern': (10, 10),
        'PeonTrollHut': (6, 5), 'PeonOrcHut': (6, 5), 'PeonOrcInn': (6, 5),
        'PeonTrollInn': (6, 5), 'PeonValleyCrossroads': (5, 5), 'PeonHanazuaCamp': (5, 5),
        'PeonSarkothBasin': (5, 5), 'PeonCaveApproach': (5, 5), 'PeonValleyExit': (5, 5)}
FILES = ['gfx/tilesets/peon.png', 'gfx/tilesets/peon_palette_map.bin',
         'gfx/tilesets/peon_environment_fire.bin', 'data/tilesets/peon_metatiles.bin',
         'data/tilesets/peon_collision.asm', 'gfx/tilesets/peon_bg.pal',
         'gfx/tilesets/peon_regions.pal', 'gfx/tilesets/peon_interiors.pal']
FILES += [f'maps/{name}.blk' for name in DIMS]


def sha(data): return hashlib.sha256(data).hexdigest()
def expand(v): return (v << 3) | (v >> 2)
def source(name): return Image.open(SOURCES / f'{name}.png').convert('RGBA')

def init_baseline():
    for name in FILES:
        dest = BASE / name
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT / name).read_bytes())
    return {name: sha((BASE / name).read_bytes()) for name in FILES}


def parse_palettes(path):
    result = []
    for line in path.read_text().splitlines():
        if 'RGB' in line:
            values = [int(v) for v in re.findall(r'\d+', line.split('RGB')[1].split(';')[0])]
            result.append(tuple(tuple(expand(v) for v in values[i:i+3]) for i in range(0, 12, 3)))
    return result


@dataclass(frozen=True)
class Tile:
    pixels: bytes
    pal: int
    priority: bool = False
    @property
    def key(self): return (self.pixels, self.pal, self.priority)


def tile_rgb(tile, palettes):
    return Image.frombytes('RGB', (8, 8), b''.join(bytes(palettes[tile.pal][v]) for v in tile.pixels))


def block_rgb(block, palettes):
    im = Image.new('RGB', (32, 32))
    for j, tile in enumerate(block): im.paste(tile_rgb(tile, palettes), (j % 4 * 8, j // 4 * 8))
    return im


def original_blocks(palettes):
    sheet = Image.open(BASE / 'gfx/tilesets/peon.png').convert('L')
    attrs = (BASE / 'gfx/tilesets/peon_palette_map.bin').read_bytes()
    meta = (BASE / 'data/tilesets/peon_metatiles.bin').read_bytes()
    blocks = []
    for ident in range(67):
        block = []
        for tid in meta[ident*16:(ident+1)*16]:
            index = tid if tid < 96 else tid - 32
            image = sheet.crop((index % 16 * 8, index // 16 * 8,
                                index % 16 * 8 + 8, index // 16 * 8 + 8))
            block.append(Tile(bytes((255-v)//85 for v in image.get_flattened_data()),
                              (attrs[tid//2] >> (tid % 2 * 4)) & 7))
        blocks.append(block)
    return blocks


def distance(a, b):
    # Slight green weighting reduces hue shifts in plant outlines.
    return (a[0]-b[0])**2 * 2 + (a[1]-b[1])**2 * 3 + (a[2]-b[2])**2 * 2


def convert_tile(rgb, palettes, foreground=None, forced_palette=None):
    pixels = list(rgb.get_flattened_data())
    weights = list(foreground.get_flattened_data()) if foreground else [0]*64
    counts = Counter((color, 4 if weights[i] else 1) for i, color in enumerate(pixels))
    candidates = (forced_palette,) if forced_palette is not None else range(7)
    def score(pal):
        return sum(count * weight * min(distance(color, dst) for dst in palettes[pal])
                   for (color, weight), count in counts.items())
    pal = min(candidates, key=lambda p: (score(p), p))
    mapping = {color: min(range(4), key=lambda v: (distance(color, palettes[pal][v]), v))
               for color, _ in counts}
    return Tile(bytes(mapping[color] for color in pixels), pal)


def composite(block, asset, xy, palettes, roof=False):
    """Source alpha composition with unchanged native coordinates and scale."""
    rgb = block_rgb(block, palettes).convert('RGBA')
    overlay = Image.new('RGBA', (32, 32))
    overlay.alpha_composite(asset, xy)
    result = Image.alpha_composite(rgb, overlay).convert('RGB')
    alpha = overlay.getchannel('A')
    tiles = []
    for j in range(16):
        box = (j % 4*8, j // 4*8, j % 4*8+8, j // 4*8+8)
        mask = alpha.crop(box)
        tile=convert_tile(result.crop(box), palettes, mask) if mask.getbbox() else block[j]
        sy=box[1]-xy[1]
        if roof and mask.getbbox() and sy<48:
            tile=Tile(tile.pixels,tile.pal,True)
        tiles.append(tile)
    return tiles


def opaque_block(asset, palettes):
    return [convert_tile(asset.crop((x, y, x+8, y+8)).convert('RGB'), palettes)
            for y in range(0, 32, 8) for x in range(0, 32, 8)]


def read_rows():
    source_text = (BASE / 'data/tilesets/peon_collision.asm').read_text()
    rows = [tuple(v.strip() for v in line.split('tilecoll')[1].split(';')[0].strip().split(','))
            for line in source_text.splitlines() if 'tilecoll' in line]
    assert len(rows) == 67
    return source_text, rows


def map_palettes(name, base):
    regions = ('TheDen', 'ValleyOfTrials', 'DurotarRoad', 'SenjinVillage', 'RazorHill',
               'OrgrimmarGate', 'BurningBladeCavern')
    if name.startswith('Peon') and name in DIMS and name not in ('PeonOpening', 'PeonOrcHut', 'PeonOrcInn', 'PeonTrollHut', 'PeonTrollInn'):
        name = 'ValleyOfTrials'
    if name in regions:
        pals = parse_palettes(BASE/'gfx/tilesets/peon_regions.pal')
        return pals[regions.index(name)*8:(regions.index(name)+1)*8]
    if name in ('PeonOrcHut','PeonOrcInn','PeonTrollHut','PeonTrollInn'):
        pals = parse_palettes(BASE/'gfx/tilesets/peon_interiors.pal')
        return pals[8:16] if 'Orc' in name else pals[:8]
    return base


def compile_tiles(blocks, fire, active=None):
    bank = list(fire)
    lookup = {tile.key: i for i, tile in enumerate(bank)}
    assert len(lookup) == 4, 'Animated tiles must have four exclusive shapes'
    meta = []
    for ident, block in enumerate(blocks):
        if active is not None and ident not in active:
            # Inactive meanings never occur in this map or its declared script
            # changes. Reuse first scenery slot instead of wasting a blank tile.
            meta.extend([4] * 16)
            continue
        for tile in block:
            if tile.key not in lookup:
                lookup[tile.key] = len(bank); bank.append(tile)
            index = lookup[tile.key]
            if index < 4:
                assert ident in (34, 39), (ident, index, 'Fire tile reused outside exclusive fire props')
            meta.append(index if index < 96 else index + 32)
    return bank, meta


def encode(tile):
    data = bytearray()
    for y in range(8):
        row = tile.pixels[y*8:y*8+8]
        data += bytes((sum((p&1) << (7-x) for x,p in enumerate(row)),
                       sum(((p>>1)&1) << (7-x) for x,p in enumerate(row))))
    return bytes(data)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    baseline=init_baseline();palettes=parse_palettes(BASE/'gfx/tilesets/peon_bg.pal')
    old=original_blocks(palettes);blocks=[list(block) for block in old]
    collision_text,rows=read_rows();maps={n:bytearray((BASE/f'maps/{n}.blk').read_bytes()) for n in DIMS}
    records=[]
    def replace(ident,name,xy=(0,0),background=None):
        blocks[ident]=composite(background if background is not None else blocks[8],source(name),xy,palettes)
        records.append({'source':name+'.png','metatile_ids':[ident],'source_rect':[0,0,*source(name).size],
                        'native_position':list(xy),'full_native_source':True,'native_scale':1})
    # All uploaded source pixels remain untouched; this stage changes colors only.
    blocks[0]=opaque_block(source('cracked_earth_tile_32x32'),palettes)
    blocks[8]=opaque_block(source('sand_tile_32x32'),palettes)
    blocks[38]=list(blocks[8])
    records += [{'source':n+'.png','metatile_ids':ids,'source_rect':[0,0,32,32],
                 'native_position':[0,0],'full_native_source':True,'native_scale':1}
                for n,ids in [('cracked_earth_tile_32x32',[0]),('sand_tile_32x32',[8,38])]]
    replace(3,'cactus_round_01_32x32')
    replace(42,'cactus_round_01_32x32')
    replace(13,'cactus_tall_01_16x32',(8,0))
    replace(6,'horde_banner_01_16x32',(8,0),old[51])
    replace(30,'palisade_wall_01_32x32')
    replace(33,'palisade_post_01_32x32')
    replace(36,'skull_01_16x16',(8,8))
    replace(37,'large_rock_01_32x32')

    # Regenerate geography aliases from the exact same quadrant masks so new
    # sand does not alternate with the old bare-soil art at mountain corners.
    for mask in range(1,15):
        blocks[52+mask]=[blocks[1][j] if mask & (1<<((j//4//2)*2+j%4//2)) else blocks[38][j]
                        for j in range(16)]
    # Full 32x48 palm above existing base anchors, never crop its canopy.
    palms=source('palm_tree_01_32x48')
    def add_block(block,row):
        for i,current in enumerate(blocks):
            if current==block and rows[i]==row:return i
        blocks.append(block);rows.append(row);return len(blocks)-1
    for name,data in maps.items():
        width,height=DIMS[name]
        for pos,ident in enumerate(list(data)):
            if ident != 28:continue
            x,y=pos%width,pos//width
            assert y>0
            used=[]
            # Eliminate the old tree while retaining its coastal water strip.
            base=list(blocks[8])
            for j in (0,4,8,12):base[j]=old[28][j]
            lower=composite(base,palms,(0,-16),palettes)
            upperpos=pos-width;upperid=data[upperpos]
            upper=composite(blocks[upperid],palms,(0,16),palettes)
            lowid=add_block(lower,rows[28]);upid=add_block(upper,rows[upperid])
            data[pos]=lowid;data[upperpos]=upid;used += [upid,lowid]
            records.append({'source':'palm_tree_01_32x48.png','map':name,'metatile_ids':used,
                            'source_rect':[0,0,32,48],'world_origin_pixels':[x*32,y*32-16],
                            'full_native_source':True,'native_scale':1,
                            'original_anchor_block':[x,y],'upper_collision_preserved':list(rows[upperid])})
    # Native 16x16 flame needs four exclusive tiles, not a clipped 16x8 top.
    fire_frames=[]
    for phase in (1,2,3):
        flame=source(f'brazier_frame_0{phase}_16x16')
        # A fixed sand backdrop in all phases; no alpha checkerboard in ROM.
        converted=composite(blocks[8],flame,(8,8),palettes)
        fire_frames.append([converted[j] for j in (5,6,9,10)])
    fire=fire_frames[0]
    for phase in fire_frames:
        # All phases keep the same palette per animated tile.
        for j in range(4):
            if phase[j].pal != fire[j].pal:
                im=source(f'brazier_frame_0{fire_frames.index(phase)+1}_16x16')
                background=block_rgb(blocks[8],palettes).convert('RGBA')
                background.alpha_composite(im,(8,8))
                tileid=(5,6,9,10)[j];box=(tileid%4*8,tileid//4*8,tileid%4*8+8,tileid//4*8+8)
                phase[j]=convert_tile(background.crop(box).convert('RGB'),palettes,forced_palette=fire[j].pal)
    for ident in (34,39):
        blocks[ident]=list(blocks[8])
        for j,tile in zip((5,6,9,10),fire):blocks[ident][j]=tile
    records.append({'source':'brazier_frame_01_16x16.png / 02 / 03','metatile_ids':[34,39],
                    'source_rect':[0,0,16,16],'native_position':[8,8],'full_native_source':True,
                    'native_scale':1,'animated_tile_ids':[0,1,2,3]})
    # The third uploaded pack is authoritative for every enterable building.
    # Keep full 96x80 exterior pixels; its doorway center lands on each old warp.
    inn=Image.open(INN_SOURCES/'razor_hill_inn_exterior_96x80.png').convert('RGBA')
    old_house_ids={4,9,10,11,12,29,31,34,39}
    for name,data in maps.items():
        if name in ('PeonOrcHut','PeonOrcInn','PeonTrollHut','PeonTrollInn'):continue
        script=(ROOT/f'maps/{name}.asm').read_text()
        doors=[(int(x),int(y),dest) for x,y,dest in
               re.findall(r'warp_event\s+(\d+),\s*(\d+),\s*(PEON_(?:ORC|TROLL)_(?:HUT|INN)),',script)]
        if name=='OrgrimmarGate':
            # Standalone closed guard lodges share the supplied architecture.
            olddata=(BASE/f'maps/{name}.blk').read_bytes();width,_=DIMS[name]
            doors += [(i%width*2+1,i//width*2+1,'CLOSED_GUARD_LODGE') for i,v in enumerate(olddata) if v==31]
        if not doors:continue
        width,height=DIMS[name]
        for wx,wy,dest in doors:
            ox,oy=wx*16-40,wy*16-64
            assert ox>=0 and oy>=0 and ox+96<=width*32 and oy+80<=height*32,(name,wx,wy)
            used=[]
            for by in range(oy//32,(oy+79)//32+1):
                for bx in range(ox//32,(ox+95)//32+1):
                    pos=by*width+bx;currentid=data[pos]
                    originalid=(BASE/f'maps/{name}.blk').read_bytes()[pos]
                    background=blocks[8] if originalid in old_house_ids else blocks[currentid]
                    composed=composite(background,inn,(ox-bx*32,oy-by*32),palettes,roof=True)
                    bid=add_block(composed,rows[currentid]);data[pos]=bid;used.append(bid)
            records.append({'source':'razor_hill_inn_gbc/razor_hill_inn_exterior_96x80.png',
                            'map':name,'metatile_ids':used,'source_rect':[0,0,96,80],
                            'world_origin_pixels':[ox,oy],'full_native_source':True,'native_scale':1,
                            'door_warp_unchanged':[wx,wy] if dest!='CLOSED_GUARD_LODGE' else None,
                            'door_center':[wx,wy],'destination_unchanged':dest,
                            'closed_guard_lodge':dest=='CLOSED_GUARD_LODGE','native_roof_priority':True})
    # Interior adaptation is a documented native module assembly. Preserve the
    # 455-pattern original source and copy its furnishings/woodwork directly;
    # repeated floor/wall panels permit the established 192-pattern hardware
    # allocation, without downscaling the full image or generating replacements.
    interior=Image.open(INN_SOURCES/'razor_hill_inn_interior_192x160.png').convert('RGBA')
    modules={'northwest':(0,0,32,32),'northeast':(160,0,192,32),
             'southwest':(0,128,32,160),'southeast':(160,128,192,160),
             'north_wall':(80,0,112,32),'west_wall':(0,64,32,96),
             'east_wall':(160,64,192,96),'south_wall':(80,0,112,32),
             'bed':(80,8,112,40),'table':(128,96,160,128),
             'hearth':(80,72,112,104),'floor':(104,40,120,56),
             'doorway':(72,128,120,160)}
    floor=interior.crop(modules['floor'])
    repeated=Image.new('RGBA',(32,32))
    for py in (0,16):
        for px in (0,16):repeated.paste(floor,(px,py))
    floorblock=opaque_block(repeated,palettes)
    wallrow=('WALL',)*4
    roommods={}
    for label,box in modules.items():
        crop=interior.crop(box)
        if label in ('floor','doorway'):continue
        roommods[label]=add_block(opaque_block(crop,palettes),wallrow)
    for name in ('PeonOrcHut','PeonOrcInn','PeonTrollHut','PeonTrollInn'):
        data=maps[name]
        for y in range(5):
            for x in range(6):
                pos=y*6+x;oldid=data[pos];row=rows[oldid]
                if x==0 and y==0:label='northwest'
                elif x==5 and y==0:label='northeast'
                elif x==0 and y==4:label='southwest'
                elif x==5 and y==4:label='southeast'
                elif y==0:label='north_wall'
                elif y==4:label='south_wall'
                elif x==0:label='west_wall'
                elif x==5:label='east_wall'
                elif oldid in (40,43):label='bed'
                elif oldid in (41,44):label='table'
                elif oldid==34:label='hearth'
                else:label=None
                block=blocks[roommods[label]] if label else floorblock
                data[pos]=add_block(block,row)
        # Full 48x32 copied doorway across two panels, centered at old warp(5,7).
        doorway=interior.crop(modules['doorway'])
        for x in (2,3):
            pos=3*6+x;oldid=data[pos]
            door=composite(floorblock,doorway,((2-x)*32,0),palettes)
            data[pos]=add_block(door,rows[oldid])
        records.append({'source':'razor_hill_inn_gbc/razor_hill_inn_interior_192x160.png',
                        'map':name,'adaptation':'Source-derived modular room; full original is not a literal tilemap import.',
                        'module_crop_coordinates':{k:list(v) for k,v in modules.items()},
                        'native_scale':1,'full_native_source':False,'native_room_size':[192,160],
                        'door_warp_unchanged':[5,7],'floor_and_panels_reused':True})
    # The cinematic hall uses the same supplied structural panels and wood floor.
    name='GrommashHold';data=maps[name];width,height=DIMS[name]
    for y in range(height):
        for x in range(width):
            pos=y*width+x;oldid=data[pos];row=rows[oldid]
            if x==0 and y==0:label='northwest'
            elif x==width-1 and y==0:label='northeast'
            elif x==0 and y==height-1:label='southwest'
            elif x==width-1 and y==height-1:label='southeast'
            elif y==0:label='north_wall'
            elif y==height-1:label='south_wall'
            elif x==0:label='west_wall'
            elif x==width-1:label='east_wall'
            elif oldid==34:label='hearth'
            else:label=None
            block=blocks[roommods[label]] if label else (blocks[oldid] if oldid in (5,6) else floorblock)
            data[pos]=add_block(block,row)
    records.append({'source':'razor_hill_inn_gbc/razor_hill_inn_interior_192x160.png',
                    'map':'GrommashHold','adaptation':'Source-derived modular hall; copied structure/floor/hearth, original cinematic carpet and masters positions.',
                    'module_crop_coordinates':{k:list(v) for k,v in modules.items()},
                    'native_scale':1,'full_native_source':False,'native_room_size':[256,192]})
    # Physical body walls follow only the source's lower 24px. Roof/eaves stay
    # walkable and use GBC priority; door landings and service/patrol approaches
    # remain free. Replacing collision aliases does not move a map event.
    def event_info(name):
        script=(ROOT/f'maps/{name}.asm').read_text();warps=[];actors=[];events=[]
        for line in script.splitlines():
            if re.match(r'\s*warp_event ',line):
                fields=[f.strip() for f in line.split('warp_event',1)[1].split(';')[0].split(',')]
                warps.append((int(fields[0]),int(fields[1])))
            if re.match(r'\s*(?:bg_event|coord_event) ',line):
                match=re.search(r'(?:bg_event|coord_event)\s+(\d+),\s*(\d+)',line)
                if match:events.append(tuple(map(int,match.groups())))
            if re.match(r'\s*object_event ',line):
                fields=[f.strip() for f in line.split('object_event',1)[1].split(';')[0].split(',')]
                if fields[2]=='SPRITE_NONE' or fields[2].startswith('SPRITE_PEON_QUEST_'):continue
                x,y=int(fields[0]),int(fields[1]);foot={(x,y)}
                if fields[3]=='SPRITEMOVEDATA_WALK_LEFT_RIGHT':foot|={(x-1,y),(x+1,y)}
                if fields[3]=='SPRITEMOVEDATA_WALK_UP_DOWN':foot|={(x,y-1),(x,y+1)}
                actors.append({'xy':(x,y),'footprint':foot,'sprite':fields[2]})
        return warps,actors,events
    def cell_collision(data,name,xy):
        width,height=DIMS[name];x,y=xy
        if not (0<=x<width*2 and 0<=y<height*2):return 'WALL'
        return rows[data[y//2*width+x//2]][y%2*2+x%2]
    def neighbors(xy):
        x,y=xy;return ((x-1,y),(x+1,y),(x,y-1),(x,y+1))
    buildings=[r for r in records if r['source'].endswith('exterior_96x80.png')]
    body_changes={}
    alpha=inn.getchannel('A')
    for record in buildings:
        name=record['map'];data=maps[name];width,height=DIMS[name]
        ox,oy=record['world_origin_pixels'];wx,wy=record['door_center']
        warps,actors,events=event_info(name);protected=set(warps)|set(events)
        for warp in warps:protected.add((warp[0],warp[1]+1))
        for actor in actors:
            for foot in actor['footprint']:protected.add(foot);protected.update(neighbors(foot))
        changed=[]
        for cy in range((oy+48)//16,(oy+71)//16+1):
            for cx in range(ox//16,(ox+95)//16+1):
                xy=(cx,cy)
                if xy in protected or cell_collision(data,name,xy)=='WALL':continue
                count=sum(alpha.getpixel((px-ox,py-oy))>0
                          for py in range(cy*16,cy*16+16) for px in range(cx*16,cx*16+16)
                          if 0<=px-ox<96 and 48<=py-oy<72)
                if count<=128:continue
                pos=cy//2*width+cx//2;oldid=data[pos];row=list(rows[oldid])
                row[cy%2*2+cx%2]='WALL';data[pos]=add_block(blocks[oldid],tuple(row));changed.append(xy)
        body_changes.setdefault(name,[]).extend(changed)
        record['new_body_wall_cells']=[list(xy) for xy in changed]
    reachability={};relocations=[]
    for name,data in maps.items():
        width,height=DIMS[name];warps,actors,events=event_info(name)
        occupied=set().union(*(a['footprint'] for a in actors)) if actors else set()
        seed=warps[0] if warps else ((8,8) if name=='GrommashHold' else (8,8))
        if name=='PeonOpening':occupied.discard(seed) # sleeper and hidden hero share the cinematic anchor
        assert cell_collision(data,name,seed)!='WALL' and seed not in occupied,(name,'seed blocked',seed)
        reached={seed};queue=deque([seed])
        while queue:
            for xy in neighbors(queue.popleft()):
                if xy not in reached and xy not in occupied and cell_collision(data,name,xy)!='WALL':
                    reached.add(xy);queue.append(xy)
        assert all(w in reached for w in warps),(name,'unreachable warp',warps)
        assert all(any(xy in reached for xy in neighbors(a['xy'])) for a in actors),(name,'service/NPC isolated')
        reachability[name]={'seed':list(seed),'reachable_cells':len(reached),'all_warps_reachable':True,
                            'all_npc_approaches_reachable':True,'actor_count':len(actors)}
        original=(BASE/f'maps/{name}.blk').read_bytes()
        oldrows=read_rows()[1]
        for cy in range(height*2):
            for cx in range(width*2):
                oldcol=oldrows[original[cy//2*width+cx//2]][cy%2*2+cx%2]
                xy=(cx,cy)
                if oldcol!='WALL' and cell_collision(data,name,xy)=='WALL':
                    safe=[v for v in reached if v not in set(warps) and v not in set(events)]
                    landing=min(safe,key=lambda v:(abs(v[0]-cx)+abs(v[1]-cy),v[1],v[0]))
                    relocations.append({'map':name,'old':list(xy),'safe':list(landing)})
    allocations={}
    local_maps={};local_collisions={};local_block_counts={}
    for name,data in maps.items():
        border=51 if name in ('PeonOrcHut','PeonOrcInn','PeonTrollHut','PeonTrollInn') else 1
        aliases=sorted(set(data)-set(range(67)))
        remap={oldid:67+i for i,oldid in enumerate(aliases)}
        local=list(blocks[:67])+[blocks[i] for i in aliases]
        localrows=list(rows[:67])+[rows[i] for i in aliases]
        native_data=bytes(remap.get(v,v) for v in data)
        assert len(local)<128,(name,len(local))
        active=set(native_data)|{border,38}
        bank,meta=compile_tiles(local,fire,active)
        allocations[name]=(bank,meta,active)
        local_maps[name]=native_data;local_collisions[name]=localrows;local_block_counts[name]=len(local)
    bank,meta,_=allocations['PeonOpening']
    report={'source':'Actual user supplied PNG import; no source redraw or resizing.',
            'source_manifest':{p.name:sha(p.read_bytes()) for p in sorted(SOURCES.glob('*.png'))},
            'baseline_sha256':baseline,'native_patterns':max(len(v[0]) for v in allocations.values()),'native_pattern_budget':192,
            'source_composition_blocks':len(blocks),'original_metatile_count':67,
            'native_metatile_count_per_map':local_block_counts,
            'native_patterns_per_map':{n:len(v[0]) for n,v in allocations.items()},
            'source_architecture_pack_sha256':'27276d86f2d71c77aca899ba73947d6ec12b6ae3042a3d6c747d35779bbbffcb',
            'source_architecture_manifest':{p.name:sha(p.read_bytes()) for p in INN_SOURCES.glob('*.png')},'source_imports':records,
            'all_original_event_coordinates_unchanged':True,
            'body_wall_changes':body_changes,'reachability':reachability,'continue_relocations':relocations,
            'every_other_movement_cell_collision_preserved':True,'roof_priority_bitsets':True,
            'palettes_unchanged':True,'colors_per_background_tile':4,'fire_frames':3,
            'fire_patterns_per_frame':4,'runtime_capture':False,'applied':args.apply}
    OUT.joinpath('previews').mkdir(exist_ok=True)
    for ident,block in enumerate(blocks):block_rgb(block,palettes).save(OUT/'previews'/f'block_{ident:02d}.png')
    for name,data in maps.items():
        olddata=(BASE/f'maps/{name}.blk').read_bytes();width,height=DIMS[name]
        assert len(data)==len(olddata)==width*height
        # Changes are constrained to documented new source body-wall cells.
        for pos,(new,oldid) in enumerate(zip(data,olddata)):
            for q,(before,after) in enumerate(zip(read_rows()[1][oldid],rows[new])):
                xy=(pos%width*2+q%2,pos//width*2+q//2)
                assert before==after or (before!='WALL' and after=='WALL' and xy in body_changes.get(name,[])),(name,xy)
        im=Image.new('RGB',(width*32,height*32));pals=map_palettes(name,palettes)
        for pos,ident in enumerate(data):im.paste(block_rgb(blocks[ident],pals),(pos%width*32,pos//width*32))
        im.save(OUT/'previews'/f'{name}_compiler.png')
    usedsources={r['source'] for r in records}
    report['unused_sources']=[p.name for p in sorted(SOURCES.glob('*.png'))
                              if p.name not in usedsources and not p.name.startswith(('brazier_frame','preview'))]
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    assert max(len(v[0]) for v in allocations.values())<=192,report['native_patterns_per_map']
    outputs={}
    graphics_asm=[];palettes_asm=[]
    headers=['; Generated native headers, contiguous map numbers12..29.\nPeonUserEnvironmentHeaders::']
    NATIVE.mkdir(parents=True,exist_ok=True)
    for name,(bank,meta,active) in allocations.items():
        sheet=Image.new('P',(128,96))
        sheet.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
        attrs=[7]*256;priority=bytearray(32)
        for i,tile in enumerate(bank):
            sheet.paste(Image.frombytes('L',(8,8),tile.pixels),(i%16*8,i//16*8))
            tid=i if i<96 else i+32
            attrs[tid]=tile.pal | (8 if i>=96 else 0)
            if tile.priority:priority[tid//8]|=0x80>>(tid%8)
        folder=f'gfx/tilesets/peon_user_environment_v0211/{name}'
        outputs[folder+'.2bpp']=b''.join(encode(tile) for tile in bank)+bytes((192-len(bank))*16)
        outputs[folder+'_meta.bin']=bytes(meta)
        outputs[folder+'_priority.bin']=bytes(priority)
        outputs[folder+'_palmap.bin']=bytes(attrs[i]|attrs[i+1]<<4 for i in range(0,256,2))
        sheet.save(OUT/'previews'/f'{name}_native_tileset.png')
        if args.apply:sheet.save(ROOT/(folder+'.png'))
        gfxlabel=f'PeonUserEnv{name}GFX';metalabel=f'PeonUserEnv{name}Meta';pallabel=f'PeonUserEnv{name}PalMap';prilabel=f'PeonUserEnv{name}Priority'
        graphics_asm += [f'SECTION "User environment {name}", ROMX',gfxlabel+'::',
                         f'INCBIN "{folder}.2bpp.lz"',metalabel+'::',f'INCBIN "{folder}_meta.bin"','']
        palettes_asm += [pallabel+'::',f'INCBIN "{folder}_palmap.bin"',
                        f'assert BANK({pallabel}) == BANK(_LoadOverworldAttrmapPals)',
                        prilabel+'::',f'INCBIN "{folder}_priority.bin"',
                        f'assert BANK({prilabel}) == BANK(_LoadOverworldAttrmapPals)','']
        collabel=f'PeonUserEnv{name}Coll'
        outputs[folder+'_coll.asm']=(''.join('\tpeon_user_tilecoll '+', '.join(row)+f' ; {i:02x} native_collision_preserved\n' for i,row in enumerate(local_collisions[name]))).encode()
        graphics_asm += [collabel+'::',f'INCLUDE "{folder}_coll.asm"','']
        headers += [f'\tdba {gfxlabel}, {metalabel}, {collabel}',
                    '\tdw TilesetPeonAnim, '+prilabel+', '+pallabel]
    map_constants={'TheDen':'THE_DEN','SenjinVillage':'SENJIN_VILLAGE','RazorHill':'RAZOR_HILL','OrgrimmarGate':'ORGRIMMAR_GATE'}
    migration=['; Derived safe Continue landings for new facade body walls.','PeonUserEnvironmentBlockedCellsV0211:']
    for row in relocations:
        migration += ['\tmap_id '+map_constants[row['map']],
                      '\tdb '+', '.join(map(str,row['old']+row['safe']))]
    migration += ['\tdb $ff','']
    outputs['data/maps/peon_user_environment_relocations_v0211.asm']=('\n'.join(migration)).encode()
    outputs['gfx/tilesets/peon_environment_fire.bin']=b''.join(encode(tile) for phase in fire_frames for tile in phase)
    outputs['gfx/peon_user_environment_v0211.asm']=('\n'.join(graphics_asm).rstrip()+'\n').encode()
    outputs['gfx/peon_user_environment_palettes_v0211.asm']=('\n'.join(palettes_asm).rstrip()+'\n').encode()
    outputs['data/tilesets/peon_user_environment_headers_v0211.asm']=('\n'.join(headers)+'\n').encode()
    outputs.update({f'maps/{name}.blk':data for name,data in local_maps.items()
                    if data!=(BASE/f'maps/{name}.blk').read_bytes()})
    if args.apply:
        for name,data in outputs.items():
            (ROOT/name).parent.mkdir(parents=True,exist_ok=True)
            (ROOT/name).write_bytes(data)
    report['native_outputs']={name:sha(data) for name,data in outputs.items()}
    report['modified_maps']=list(name.removeprefix('maps/').removesuffix('.blk') for name in outputs if name.startswith('maps/'))
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'max_patterns':max(len(v[0]) for v in allocations.values()),'per_map':report['native_patterns_per_map'],'blocks':len(blocks),'applied':args.apply,'modified_maps':report['modified_maps']}))


if __name__=='__main__':main()
