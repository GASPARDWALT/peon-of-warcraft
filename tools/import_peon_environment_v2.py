#!/usr/bin/env python3
"""Compile the supplied Durotar v2 art into isolated, playable test maps.

Only new test-map files are written. PNG source pixels and their alpha canvas
are never changed, resized, or redrawn. Seven fitted RGB555 palettes are a
documented hardware conversion, separate from the preserved originals.
"""
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'references/characters/peon_of_warcraft_environment_pack_v2_art_quality'
DUROTAR = SOURCE / 'durotar_valley'
SHARED = SOURCE / 'shared_interactables'
NATIVE = ROOT / 'gfx/tilesets/peon_environment_v2'
EVIDENCE = ROOT / 'references/generated/map_tests'
ARCHIVE_SHA = '5a9b27fe4a8c20934654388058f635726e2e3f477c131b27efff687fc2c1bdc0'
MAPS = [('PeonEnvironmentTest', 'Test', 30),
        ('PeonEnvironmentTestAnnex', 'Annex', 31),
        ('PeonEnvironmentTestCave', 'Cave', 32)]
WIDTH, HEIGHT = 12, 10
# Match gfx/lz.mk exactly. Optimal compression here would differ from a clean
# native Make rebuild when PNG/2bpp timestamps cause recompression.
LZ_FLAGS = ['--matching', '--align', '4']

# Pure encoding/conversion helpers only: importing this module never executes
# the previous importer, regenerates its maps, or changes its baseline.
spec = importlib.util.spec_from_file_location('peon_env_v0211_helpers', ROOT / 'tools/import_peon_user_environment_v0211.py')
helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)
Tile = helpers.Tile
encode = helpers.encode
sha = helpers.sha


def source_path(name):
    return (SHARED if name.startswith(('campfire_shared_', 'chest_shared_')) else DUROTAR) / name


def source_image(name):
    return Image.open(source_path(name)).convert('RGBA')


def fitted_palettes():
    """Source-derived, deterministic median-cut palettes on the RGB555 grid."""
    groups = [
        ('earth_paths', ('ground_durotar_dirt', 'path_', 'transition_'), None),
        ('red_earth_rock', ('ground_valley', 'ground_durotar_cracked', 'rock_', 'cave_'), None),
        ('wood_shadow', ('palisade', 'orc_hut', 'bones_', 'banner_'), None),
        ('desert_plants', ('cactus', 'grass_'), None),
        ('bone_stone', ('bones_', 'orc_hut', 'palisade'), 'bone'),
        ('horde_red', ('banner_', 'orc_hut', 'cave_'), 'red'),
        ('fire', ('campfire_shared_',), None),
    ]
    palettes, records = [], []
    for label, prefixes, filter_name in groups:
        counts = Counter()
        for path in sorted(list(DUROTAR.glob('*.png')) + list(SHARED.glob('campfire_shared_*.png'))):
            if not path.name.startswith(prefixes):
                continue
            for r, g, b, a in Image.open(path).convert('RGBA').get_flattened_data():
                if not a:
                    continue
                if filter_name == 'bone' and not (r + g + b > 180 and abs(r - g) < 48 and abs(g - b) < 40):
                    continue
                if filter_name == 'red' and not (r > g * 1.45 and r > b * 1.8):
                    continue
                weight = 4 if label == 'fire' and r > g * 1.65 and r > b * 2 else 1
                counts[(helpers.expand(r >> 3), helpers.expand(g >> 3), helpers.expand(b >> 3))] += weight
        colors = [color for color, count in sorted(counts.items()) for _ in range(count)]
        assert colors, label
        sample = Image.new('RGB', (len(colors), 1))
        sample.putdata(colors)
        indexed = sample.quantize(colors=4, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        raw = indexed.getpalette()
        palette = [tuple(helpers.expand(raw[i+k] >> 3) for k in range(3)) for i in range(0, 12, 3)]
        palette.sort(key=lambda c: sum(c), reverse=True)
        palettes.append(palette)
        records.append({'name': label, 'rgb555': [[v >> 3 for v in c] for c in palette],
                        'fit': 'median-cut of actual opaque source pixels on RGB555 grid',
                        'source_filter': filter_name})
    palettes.append(helpers.parse_palettes(ROOT / 'gfx/tilesets/peon_bg.pal')[7])
    return palettes, records


@dataclass
class MapBuilder:
    name: str
    short: str
    number: int
    floor: list
    wall: list
    palettes: list

    def __post_init__(self):
        self.blocks = [list(self.wall), list(self.wall), list(self.floor)]
        self.rows = [('WALL',) * 4, ('WALL',) * 4, ('FLOOR',) * 4]
        self.data = bytearray([2] * (WIDTH * HEIGHT))
        self.records = []
        for y in range(HEIGHT):
            for x in range(WIDTH):
                if x in (0, WIDTH-1) or y in (0, HEIGHT-1):
                    self.data[y*WIDTH+x] = 1

    def add(self, block, rows=('FLOOR',)*4):
        ident = len(self.blocks)
        assert ident < 128
        self.blocks.append(block)
        self.rows.append(tuple(rows))
        return ident

    def put(self, x, y, ident):
        assert 0 <= x < WIDTH and 0 <= y < HEIGHT
        self.data[y*WIDTH+x] = ident

    def cell(self, x, y, kind):
        bx, by, quadrant = x//2, y//2, (y%2)*2+x%2
        before = self.data[by*WIDTH+bx]
        rows = list(self.rows[before])
        rows[quadrant] = kind
        self.put(bx, by, self.add(list(self.blocks[before]), rows))

    def stamp(self, filename, bx, by, offset=(0, 0), collision='FLOOR'):
        asset = source_image(filename)
        width = (asset.width + offset[0] + 31)//32
        height = (asset.height + offset[1] + 31)//32
        ids = []
        for y in range(height):
            for x in range(width):
                block = helpers.composite(self.floor, asset, (offset[0]-x*32, offset[1]-y*32), self.palettes)
                ident = self.add(block, (collision,)*4)
                self.put(bx+x, by+y, ident)
                ids.append(ident)
        self.records.append({'source': str(source_path(filename).relative_to(ROOT)),
                             'sha256': sha(source_path(filename).read_bytes()),
                             'dimensions': list(asset.size), 'alpha_bbox': list(asset.getchannel('A').getbbox() or (0,0,0,0)),
                             'native_scale': 1, 'whole_canvas_preserved': True,
                             'placement_pixels': [bx*32+offset[0], by*32+offset[1]],
                             'metatile_ids': ids, 'color_conversion': '7 fitted map palettes, one palette per 8×8 tile'})
        return ids

    def floor_asset(self, name):
        image = source_image(name)
        assert image.size == (32,32)
        ident = self.add(helpers.opaque_block(image, self.palettes))
        self.records.append({'source': str(source_path(name).relative_to(ROOT)),
                             'sha256': sha(source_path(name).read_bytes()), 'dimensions': [32,32],
                             'native_scale': 1, 'whole_canvas_preserved': True,
                             'metatile_ids': [ident], 'color_conversion': '7 fitted map palettes, one palette per 8×8 tile'})
        return ident

    def collision_at(self, x, y):
        if not 0 <= x < WIDTH*2 or not 0 <= y < HEIGHT*2:
            return 'WALL'
        ident = self.data[y//2*WIDTH+x//2]
        return self.rows[ident][(y%2)*2+x%2]


def cave_native_block(ident, palette):
    """Copy original native CAVE patterns, without a procedural drawing pass."""
    sheet = Image.open(ROOT / 'gfx/tilesets/cave.png').convert('L')
    meta = (ROOT / 'data/tilesets/cave_metatiles.bin').read_bytes()
    block = []
    for tid in meta[ident*16:ident*16+16]:
        im = sheet.crop((tid%16*8, tid//16*8, tid%16*8+8, tid//16*8+8))
        block.append(Tile(bytes((255-v)//85 for v in im.get_flattened_data()), palette))
    return block


def fire_tiles(palettes):
    # A copied stone-floor patch distinguishes the source's dark orange flame
    # from orange dirt. No flame pixels are redrawn or recolored in the source.
    background = helpers.block_rgb(cave_native_block(2,2),palettes).crop((16,16,32,32)).convert('RGBA')
    frames = []
    for name in ['campfire_shared_frame_01_16x16.png', 'campfire_shared_frame_02_16x16.png', 'campfire_shared_frame_01_16x16.png']:
        source = source_image(name)
        rgb = Image.alpha_composite(background, source).convert('RGB')
        frames.append([helpers.convert_tile(rgb.crop((x,y,x+8,y+8)), palettes,
                       source.getchannel('A').crop((x,y,x+8,y+8)), forced_palette=6)
                       for y in (0,8) for x in (0,8)])
    assert len({tile.key for tile in frames[0]}) == 4
    return frames


def build_maps(palettes, frames):
    dirt = helpers.opaque_block(source_image('ground_durotar_dirt_01_32x32.png'), palettes)
    wall = cave_native_block(1, 2)
    maps = [MapBuilder(name, short, number, dirt, wall, palettes) for name,short,number in MAPS]
    a,b,c = maps
    dirt_name = 'ground_durotar_dirt_01_32x32.png'
    for m in maps:
        m.records.append({'source': str(source_path(dirt_name).relative_to(ROOT)), 'sha256': sha(source_path(dirt_name).read_bytes()),
                          'dimensions': [32,32], 'native_scale': 1, 'whole_canvas_preserved': True,
                          'metatile_ids': [2], 'role': 'source ground underneath alpha props'})
    # The supplied path names describe the opposite axis / vertical corner.
    # Match the visible openings, keeping all original pixels and filenames.
    path_names = {'NS':'straight_horizontal', 'EW':'straight_vertical',
                  'SE':'corner_ne', 'SW':'corner_nw', 'NE':'corner_se', 'NW':'corner_sw', 'NESW':'crossroad'}
    paths = {directions:a.floor_asset(f'path_durotar_{part}_32x32.png') for directions,part in path_names.items()}
    for x in range(4,8):
        a.put(x,3,paths['EW']); a.put(x,6,paths['EW'])
    for y in range(4,6):
        a.put(3,y,paths['NS']); a.put(8,y,paths['NS'])
    for x,y,key in [(3,3,'SE'),(8,3,'SW'),(3,6,'NE'),(8,6,'NW'),(6,6,'NESW'),(8,4,'NESW')]:
        a.put(x,y,paths[key])
    for y in (7,8): a.put(6,y,paths['NS'])
    for x in (9,10): a.put(x,4,paths['EW'])
    red = a.floor_asset('ground_valley_redsand_01_32x32.png')
    cracked = a.floor_asset('ground_durotar_cracked_01_32x32.png')
    for x in (1,2):
        for y in (1,2): a.put(x,y,red)
    for x in (9,10):
        for y in (1,2): a.put(x,y,cracked)
    a.stamp('cactus_durotar_round_01_32x32.png',4,1,collision='WALL')
    a.stamp('cactus_durotar_tall_01_16x32.png',6,1,(8,0))
    # The source's "tall" cactus is visibly only the lower 16 rows. Block its
    # actual base movement cell and preserve the empty upper source canvas.
    a.cell(12,3,'WALL')
    a.cell(21,9,'WARP_CARPET_RIGHT')

    # Complete native canvases, not a cropped cabin or partial cave mouth.
    b.stamp('orc_hut_durotar_01_64x64.png',4,2,collision='WALL')
    b.stamp('cave_entrance_durotar_01_64x64.png',8,2,collision='WALL')
    b.cell(10,7,'DOOR'); b.cell(18,7,'CAVE')
    # Palisade demonstration enclosure with an open central gate.
    pal_h = b.stamp('palisade_durotar_wall_horizontal_01_32x32.png',3,5,collision='WALL')[0]
    b.put(4,5,pal_h); b.put(6,5,pal_h); b.put(7,5,pal_h)
    gate = b.stamp('palisade_durotar_gate_01_32x32.png',5,5,collision='WALL')[0]
    b.cell(10,10,'FLOOR'); b.cell(11,10,'FLOOR'); b.cell(10,11,'FLOOR'); b.cell(11,11,'FLOOR')
    pal_v = b.stamp('palisade_durotar_wall_vertical_01_32x32.png',3,6,collision='WALL')[0]
    b.put(7,6,pal_v)
    b.stamp('banner_horde_durotar_01_16x48.png',1,2,(8,0))
    b.cell(2,6,'WALL')
    b.stamp('brazier_durotar_frame_01_16x16.png',2,6,(16,16))
    b.cell(5,13,'WALL')
    b.stamp('chest_shared_closed_16x16.png',6,6,(16,16))
    b.cell(13,13,'WALL')
    fire_block = cave_native_block(2,2)
    for at, tile in zip([10,11,14,15],frames[0]): fire_block[at]=tile
    b.put(5,6,b.add(fire_block,('FLOOR','FLOOR','FLOOR','WALL')))
    b.records.append({'source':str((SHARED/'campfire_shared_frame_01_16x16.png').relative_to(ROOT)),
                      'sha256':sha((SHARED/'campfire_shared_frame_01_16x16.png').read_bytes()),
                      'dimensions':[16,16], 'native_scale':1, 'whole_canvas_preserved':True,
                      'placement_pixels':[176,208], 'animated_physical_tile_ids':[0,1,2,3]})
    b.cell(2,9,'WARP_CARPET_LEFT')

    # One cave inspection room. Transition samples are kept as literal32×32
    # patches; the surrounding wall/floor are copied native CAVE modules.
    cave_floor = cave_native_block(2,2)
    cave_floor_id = c.add(cave_floor)
    for y in range(1,HEIGHT-1):
        for x in range(1,WIDTH-1): c.put(x,y,cave_floor_id)
    transitions = sorted(f.name for f in DUROTAR.glob('transition_*.png'))
    for i,name in enumerate(transitions): c.put(2+(i%4)*2,2+(i//4)*2,c.floor_asset(name))
    # A playable, joined three-block sample, rather than an isolated transition
    # patch: literal dirt -> literal transition -> literal red sand. Among the
    # four supplied variants, "left" has the lowest horizontal edge error for
    # this direction. Its canonical beige edge still differs from dirt01; do
    # not redraw it or silently claim the source textures are seamless.
    c.put(3,2,2)
    c.put(5,2,c.floor_asset('ground_valley_redsand_01_32x32.png'))
    c.stamp('rock_durotar_large_01_32x32.png',2,6,collision='WALL')
    c.stamp('rock_durotar_small_01_16x16.png',9,6,(16,16))
    c.cell(19,13,'WALL')
    c.stamp('bones_durotar_skull_pile_01_16x16.png',4,6,(16,16))
    c.cell(9,13,'WALL')
    c.stamp('grass_durotar_dry_01_16x16.png',7,6,(16,16))
    c.cell(6,17,'WARP_CARPET_DOWN'); c.cell(18,17,'WARP_CARPET_DOWN')
    return maps, path_names


def pack_map(m, frames, rgbgfx):
    # Animation keys are exclusively assigned0..3, never deduplicated into a
    # static tile even if static pixels happen to equal one animation phase.
    tiles = list(frames[0]); lookup = {}
    meta = bytearray()
    fire_keys = {tile.key:i for i,tile in enumerate(frames[0])}
    for block in m.blocks:
        for tile in block:
            if m.short == 'Annex' and tile in frames[0] and block[10:12] == frames[0][:2] and block[14:16] == frames[0][2:]:
                index = fire_keys[tile.key]
            else:
                if tile.key not in lookup:
                    lookup[tile.key] = len(tiles); tiles.append(tile)
                index = lookup[tile.key]
            meta.append(index if index < 96 else index+32)
    assert len(tiles) <= 192, f'{m.name}: {len(tiles)} >192 native patterns; no truncation allowed'
    native_patterns = len(tiles)
    while len(tiles) < 192: tiles.append(Tile(bytes(64),0))
    grayscale = Image.new('P',(128,96))
    grayscale.putpalette([v for v in (255,170,85,0) for _ in range(3)]+[0]*756)
    for index,tile in enumerate(tiles):
        im=Image.frombytes('P',(8,8),tile.pixels)
        grayscale.paste(im,(index%16*8,index//16*8))
    png=NATIVE/f'{m.short}.png'; grayscale.save(png)
    binary=NATIVE/f'{m.short}.2bpp'
    subprocess.run([rgbgfx,'--colors','dmg','-o',str(binary),str(png)],check=True)
    expected=b''.join(encode(tile) for tile in tiles)
    assert binary.read_bytes()==expected, 'rgbgfx changed grayscale index ordering'
    subprocess.run([str(ROOT/'tools/lzcompress'),*LZ_FLAGS,'--',str(binary),str(NATIVE/f'{m.short}.2bpp.lz')],check=True)
    (NATIVE/f'{m.short}_metatiles.bin').write_bytes(meta)
    attributes=[7]*256
    for index,tile in enumerate(tiles):
        physical=index if index<96 else index+32
        attributes[physical] = tile.pal | (8 if index>=96 else 0)
    palmap=bytes(attributes[i] | attributes[i+1]<<4 for i in range(0,256,2))
    assert palmap[48:64] == bytes([0x77]*16), 'Font slots must retain UI palette7'
    assert all(attributes[index+32]&8 for index in range(96,192)), 'Scenery second VRAM bank flag is required'
    (NATIVE/f'{m.short}_palette_map.bin').write_bytes(palmap)
    (NATIVE/f'{m.short}_priority.bin').write_bytes(bytes(32))
    collision='; Isolated source-art test collisions, no original map changed.\n'
    collision+=''.join('\tpeon_env_v2_tilecoll '+', '.join(row)+f' ; {i:02x}\n' for i,row in enumerate(m.rows))
    (NATIVE/f'{m.short}_collision.asm').write_text(collision)
    map_path=ROOT/f'maps/{m.name}.blk';map_path.write_bytes(m.data)
    assert len(meta)==len(m.blocks)*16 and max(meta)<224
    assert all(not 96<=tile<128 for tile in meta), 'Font slots cannot contain scenery'
    assert len(m.blocks)<128 and len(m.data)==WIDTH*HEIGHT
    preview=Image.new('RGB',(WIDTH*32,HEIGHT*32))
    for y in range(HEIGHT):
        for x in range(WIDTH):preview.paste(helpers.block_rgb(m.blocks[m.data[y*WIDTH+x]],m.palettes),(x*32,y*32))
    preview.save(EVIDENCE/f'{m.name}_native.png')
    preview.resize((preview.width*3,preview.height*3),Image.Resampling.NEAREST).save(EVIDENCE/f'{m.name}_native_3x.png')
    return {'name':m.name,'number':m.number,'width_blocks':WIDTH,'height_blocks':HEIGHT,'headerprefix':f'PeonEnvV2{m.short}',
            'native_patterns':native_patterns,'loaded_patterns':192,'metatile_count':len(m.blocks),
            'gfx':str(binary.relative_to(ROOT)), 'compressed_gfx':f'gfx/tilesets/peon_environment_v2/{m.short}.2bpp.lz',
            'metatiles':f'gfx/tilesets/peon_environment_v2/{m.short}_metatiles.bin',
            'collision':f'gfx/tilesets/peon_environment_v2/{m.short}_collision.asm',
            'palmap':f'gfx/tilesets/peon_environment_v2/{m.short}_palette_map.bin',
            'priority':f'gfx/tilesets/peon_environment_v2/{m.short}_priority.bin',
            'palettes':'gfx/tilesets/peon_environment_v2/background.pal',
            'map_blocks':str(map_path.relative_to(ROOT)), 'source_assets':m.records}


def reachable(m, start):
    seen={tuple(start)};todo=deque(seen)
    while todo:
        x,y=todo.popleft()
        for q in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
            if q not in seen and m.collision_at(*q) not in ('WALL',):seen.add(q);todo.append(q)
    return seen


def main():
    NATIVE.mkdir(parents=True,exist_ok=True);EVIDENCE.mkdir(parents=True,exist_ok=True)
    archive=ROOT/'references/characters/peon_of_warcraft_environment_pack_v2_art_quality.zip'
    assert sha(archive.read_bytes())==ARCHIVE_SHA, 'Preserved source archive changed'
    rgbgfx=os.environ.get('PEON_RGBGFX') or shutil.which('rgbgfx') or '/workspace/toolchains/rgbds-1.0.4/rgbgfx'
    assert Path(rgbgfx).is_file() and (ROOT/'tools/lzcompress').is_file()
    palettes,palette_fit=fitted_palettes()
    pal_text='; Seven fitted source RGB555 palettes; existing eighth UI palette retained.\n'
    pal_text+=''.join('\tRGB '+', '.join(f'{v>>3:02d}' for color in palette for v in color)+'\n' for palette in palettes)
    (NATIVE/'background.pal').write_text(pal_text)
    frames=fire_tiles(palettes)
    fire=b''.join(encode(tile) for frame in frames for tile in frame)
    assert len(fire)==192
    (NATIVE/'fire_frames.bin').write_bytes(fire)
    maps,orientations=build_maps(palettes,frames)
    results=[pack_map(m,frames,rgbgfx) for m in maps]
    gfx=['; Generated isolated environment-v2 data; all map-local tables share one bank.','MACRO peon_env_v2_tilecoll','\tdb COLL_\\1, COLL_\\2, COLL_\\3, COLL_\\4','ENDM','']
    for m in maps:
        prefix=f'PeonEnvV2{m.short}';base=f'gfx/tilesets/peon_environment_v2/{m.short}'
        gfx.extend([f'SECTION "Peon Environment v2 {m.short} Data", ROMX',f'{prefix}GFX::',f'INCBIN "{base}.2bpp.lz"',
                    f'{prefix}Meta::',f'INCBIN "{base}_metatiles.bin"',f'{prefix}Coll::',f'INCLUDE "{base}_collision.asm"',
                    f'{prefix}PalMap::',f'INCBIN "{base}_palette_map.bin"',f'{prefix}Priority::',f'INCBIN "{base}_priority.bin"',
                    f'assert BANK({prefix}Meta) == BANK({prefix}PalMap)',f'assert BANK({prefix}Meta) == BANK({prefix}Coll)',
                    f'assert BANK({prefix}Meta) == BANK({prefix}Priority)',''])
    (ROOT/'gfx/peon_environment_v2.asm').write_text('\n'.join(gfx))
    headers=['; 15-byte map-local headers selected by appended map IDs30..32.','PeonEnvironmentV2Headers::']
    for m in maps:
        p=f'PeonEnvV2{m.short}'
        headers.extend([f'\tdba {p}GFX',f'\tdba {p}Meta',f'\tdba {p}Coll','\tdw TilesetPeonEnvironmentV2Anim','\tdw 0',f'\tdw {p}PalMap'])
    headers.append('assert @ - PeonEnvironmentV2Headers == 3 * TILESET_LENGTH')
    (ROOT/'data/tilesets/peon_environment_v2_headers.asm').write_text('\n'.join(headers)+'\n')
    transitions=[{'map':maps[0].name,'doorxy':[21,9],'to':maps[1].name,'landingxy':[2,9]},
                 {'map':maps[1].name,'doorxy':[2,9],'to':maps[0].name,'landingxy':[21,9]},
                 {'map':maps[1].name,'doorxy':[10,7],'to':maps[2].name,'landingxy':[6,17],'kind':'hut'},
                 {'map':maps[1].name,'doorxy':[18,7],'to':maps[2].name,'landingxy':[18,17],'kind':'cave'},
                 {'map':maps[2].name,'doorxy':[6,17],'to':maps[1].name,'landingxy':[10,7]},
                 {'map':maps[2].name,'doorxy':[18,17],'to':maps[1].name,'landingxy':[18,7]}]
    obstacles=[{'map':maps[0].name,'fromxy':[8,4],'direction':'up','kind':'cactus'},
               {'map':maps[1].name,'fromxy':[8,8],'direction':'up','kind':'hut_wall'},
               {'map':maps[1].name,'fromxy':[8,12],'direction':'up','kind':'palisade_wall'},
               {'map':maps[1].name,'fromxy':[11,14],'direction':'up','kind':'campfire'},
               {'map':maps[2].name,'fromxy':[4,14],'direction':'up','kind':'rock'}]
    interactions=[{'map':maps[0].name,'npcxy':[10,17],'fromxy':[11,17],'direction':'left','kind':'inspection_npc'},
                  {'map':maps[1].name,'chestxy':[13,13],'fromxy':[13,14],'direction':'up','kind':'chest'}]
    starts=[[12,17],[2,9],[6,17]]
    static=[]
    for m,start in zip(maps,starts):
        cells=reachable(m,start)
        for item in transitions:
            if item['map']==m.name:assert tuple(item['doorxy']) in cells,(m.name,item,'door not reachable')
        for item in interactions:
            if item['map']==m.name:assert tuple(item['fromxy']) in cells,(m.name,item,'interaction not reachable')
        for item in obstacles:
            if item['map']!=m.name:continue
            x,y=item['fromxy'];dx,dy={'up':(0,-1),'down':(0,1),'left':(-1,0),'right':(1,0)}[item['direction']]
            assert (x,y) in cells and m.collision_at(x+dx,y+dy)=='WALL',(m.name,item,'invalid obstacle probe')
        static.append({'map':m.name,'reachable_cells':len(cells),'doors_reachable':True,'interactions_reachable':True})
    included={Path(item['source']).name for m in maps for item in m.records}
    excluded=[{'source':str(p.relative_to(ROOT)),'sha256':sha(p.read_bytes()),
               'reason':'Alternate ground texture variant excluded from this first-pass native tile budget; canonical original preserved.'}
              for p in sorted(DUROTAR.glob('*.png')) if p.name not in included]
    joined_transition={'map':maps[2].name,'blocks':[[3,2],[4,2],[5,2]],
                       'source_order':['ground_durotar_dirt_01_32x32.png','transition_durotar_dirt_redsand_left_32x32.png','ground_valley_redsand_01_32x32.png'],
                       'walk_start':[6,5],'walk_end':[11,5],'view_waypoint':[9,6],
                       'native_scale':1,'edge_continuity':'Source transition was selected by minimum RGB555 horizontal edge error. Canonical tile edges/colors are not pixel-seamless; all source geometry remains unchanged.'}
    assert all((x,5) in reachable(maps[2],[6,17]) for x in range(6,12)), 'Joined soil strip must be walkable'
    contract={'maps':results,'spawn':{'map':maps[0].name,'xy':[12,17]},'group':26,
              'route_waypoints':{maps[0].name:[[12,17],[11,17],[21,9]],maps[1].name:[[2,9],[10,8],[18,8],[13,14],[11,14]],maps[2].name:[[6,17],[4,14],[18,17]]},
              'obstacles':obstacles,'transitions':transitions,'interactions':interactions,'joined_transition':joined_transition,
              'fire':{'map':maps[1].name,'physical_tile_ids':[0,1,2,3],'vram_bank':0,'vram_address':'0x9000',
                      'framebytes':64,'frames':3,'period_engine_ticks':8,'path':str((NATIVE/'fire_frames.bin').relative_to(ROOT)),
                      'sha256':sha(fire),'palette':6,'alpha_background':'Copied native CAVE stone-floor module; no flame pixels redrawn.',
                      'sources':[{'source':str((SHARED/name).relative_to(ROOT)),'sha256':sha((SHARED/name).read_bytes())}
                                 for name in ['campfire_shared_frame_01_16x16.png','campfire_shared_frame_02_16x16.png','campfire_shared_frame_01_16x16.png']]}}
    (EVIDENCE/'test_contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    manifest={'source_archive':str(archive.relative_to(ROOT)),'source_archive_sha256':ARCHIVE_SHA,
              'scope':'Dedicated Durotar environment v2 test maps only; no real map, class or combat changes.',
              'source_geometry':'All supplied native pixel coordinates and complete source alpha canvases retained; no resampling.',
              'palettes':palette_fit,'existing_ui_palette_unchanged':True,'maps':results,'excluded':excluded,
              'compression_profile':{'tool':'tools/lzcompress','flags':LZ_FLAGS,'matches':'gfx/lz.mk: --matching + gfx/tilesets/%.lz --align4'},
              'path_visible_openings':orientations,'static_walkability':static,'fire':contract['fire'],'joined_transition':joined_transition,
              'native_output_sha256':{str(path.relative_to(ROOT)):sha(path.read_bytes()) for path in sorted(NATIVE.glob('*')) if path.is_file()},
              'native_cave_kit':{'png':'gfx/tilesets/cave.png','png_sha256':sha((ROOT/'gfx/tilesets/cave.png').read_bytes()),
                                 'metatile_source':'data/tilesets/cave_metatiles.bin','blocks':[1,2],'color_conversion':'native copied indexed patterns using fitted wood/stone palette2'},
              'limitations':['Cave and hut lead to a shared inspection room, not new quest or combat content.',
                             'The supplied banner/cactus keep their original transparent padding and visibly short opaque region.',
                             'Static previews show compiler output; actual ROM capture and walking are a separate required check.']}
    (EVIDENCE/'import_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'maps':[{k:r[k] for k in ('name','native_patterns','metatile_count')} for r in results],
                      'included_durotar_assets':len(included & {p.name for p in DUROTAR.glob('*.png')}),'excluded':len(excluded),'static_walkability':static},indent=2))


if __name__=='__main__':main()
