#!/usr/bin/env python3
"""Redraw existing native décor tiles without altering layouts or tile IDs.

Four indexed colours, the same 192 VRAM slots, and retained metatile/collision
tables are deliberate constraints. Compiler exports are not emulator captures.
"""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import build_durotar_world as world

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/valley_layout_update/decor'
TARGETS = {1: 'durotar_escarpment', 6: 'horde_banner', 30: 'spiked_palisade',
           31: 'watchtower', 34: 'fire_brazier', 37: 'ochre_boulder', 39: 'campfire'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blank(size):
    return Image.new('P', size, 0)


def cliff_module():
    im = Image.new('P', (16, 16), 2); d = ImageDraw.Draw(im)
    # An irregular sandstone shelf with a lit upper face and recessed cracks.
    d.polygon([(0, 2), (3, 0), (11, 0), (15, 3), (15, 10),
               (12, 14), (4, 15), (0, 12)], fill=3)
    d.polygon([(0, 3), (3, 1), (11, 1), (14, 4), (14, 9),
               (10, 12), (3, 12), (0, 10)], fill=1)
    d.polygon([(1, 4), (4, 2), (10, 2), (12, 4), (10, 6), (3, 6)], fill=0)
    d.polygon([(0, 8), (5, 9), (9, 8), (14, 5), (14, 10),
               (10, 13), (4, 14), (0, 11)], fill=2)
    d.line([(0, 11), (4, 13), (10, 13), (14, 10)], fill=3)
    d.line([(3, 8), (6, 8), (7, 10)], fill=3)
    d.line([(10, 3), (11, 5), (10, 7)], fill=2)
    d.line([(1, 3), (4, 1), (9, 1)], fill=0)
    d.point((2, 10), fill=1); d.point((12, 11), fill=1)
    return im


def boulder_module():
    im = blank((16, 16)); mask = Image.new('L', im.size); d = ImageDraw.Draw(im)
    outline = [(0, 8), (2, 4), (6, 1), (11, 0), (15, 5),
               (15, 12), (11, 15), (4, 15), (0, 12)]
    ImageDraw.Draw(mask).polygon(outline, fill=255)
    d.polygon(outline, fill=3)
    d.polygon([(1, 8), (3, 4), (7, 2), (11, 1), (13, 5),
               (9, 8), (3, 9)], fill=1)
    d.polygon([(2, 10), (8, 10), (13, 7), (14, 11),
               (10, 14), (4, 13)], fill=2)
    d.line([(3, 5), (7, 2), (10, 2)], fill=0)
    d.line([(7, 4), (8, 6), (6, 8)], fill=2)
    d.line([(9, 9), (8, 11), (9, 13)], fill=3)
    d.line([(2, 11), (4, 12), (6, 12)], fill=1)
    d.point((12, 5), fill=0); d.point((12, 12), fill=1)
    return im, mask


def banner():
    im = blank((32, 32)); mask = Image.new('L', im.size)
    d = ImageDraw.Draw(im); m = ImageDraw.Draw(mask)
    # Keep blank quadrants intact: all artwork occupies the existing seven tiles.
    m.rectangle((8, 2, 9, 29), fill=255)
    cloth = [(10, 4), (22, 4), (22, 18), (18, 22), (15, 20), (10, 20)]
    m.polygon(cloth, fill=255)
    d.rectangle((8, 2, 9, 29), fill=3); d.line((8, 3, 8, 28), fill=1)
    d.point((8, 2), fill=0); d.line((8, 5, 9, 5), fill=0)
    d.polygon(cloth, fill=3)
    d.polygon([(11, 5), (21, 5), (21, 17), (18, 20), (15, 18), (11, 19)], fill=1)
    d.line((21, 6, 21, 16), fill=2); d.line((11, 18, 15, 17), fill=2)
    # Small pale Horde crest: horns, open ring and a pointed lower blade.
    d.line([(12, 9), (14, 7), (14, 9)], fill=0)
    d.line([(20, 9), (18, 7), (18, 9)], fill=0)
    d.polygon([(16, 9), (19, 11), (18, 15), (16, 18), (14, 15), (13, 11)], fill=3)
    d.line([(16, 9), (18, 11), (17, 14), (16, 16), (15, 14), (14, 11), (16, 9)], fill=0)
    d.line((16, 12, 16, 18), fill=0)
    d.line((11, 6, 14, 6), fill=0); d.point((20, 6), fill=0)
    return im, mask


def palisade():
    unit = blank((8, 32)); mask = Image.new('L', unit.size)
    d = ImageDraw.Draw(unit); m = ImageDraw.Draw(mask)
    stake = [(0, 12), (3, 2), (6, 12), (6, 29), (0, 29)]
    m.polygon(stake, fill=255); m.rectangle((0, 16, 7, 19), fill=255)
    d.polygon(stake, fill=3)
    d.polygon([(1, 12), (3, 4), (5, 12), (5, 28), (1, 28)], fill=1)
    d.line((2, 10, 2, 27), fill=0); d.line((4, 13, 4, 28), fill=2)
    d.line((3, 7, 3, 11), fill=0); d.line((1, 24, 3, 22), fill=2)
    d.rectangle((0, 16, 7, 19), fill=3)
    d.line((0, 17, 7, 17), fill=1); d.line((0, 18, 7, 18), fill=2)
    d.line((1, 15, 5, 15), fill=0); d.line((1, 20, 5, 20), fill=0)
    m.line((1, 15, 5, 15), fill=255); m.line((1, 20, 5, 20), fill=255)
    im = blank((32, 32)); full = Image.new('L', im.size)
    for x in range(0, 32, 8): im.paste(unit, (x, 0)); full.paste(mask, (x, 0))
    return im, full


def flames():
    im = blank((16, 16)); mask = Image.new('L', im.size)
    d = ImageDraw.Draw(im); m = ImageDraw.Draw(mask)
    shape = [(1, 15), (0, 10), (3, 5), (3, 1), (6, 4), (7, 8),
             (10, 3), (10, 0), (13, 5), (13, 9), (15, 6), (15, 12), (12, 15)]
    m.polygon(shape, fill=255); d.polygon(shape, fill=2)
    d.polygon([(2, 14), (1, 10), (4, 6), (4, 3), (7, 9),
               (10, 6), (11, 3), (12, 10), (14, 9), (14, 12), (11, 14)], fill=1)
    d.polygon([(5, 14), (4, 11), (7, 8), (7, 5), (9, 11),
               (11, 9), (11, 13), (9, 14)], fill=0)
    d.point((3, 4), fill=0); d.point((11, 5), fill=0)
    return im, mask


def braces():
    # Reused lower tower braces also form the campfire's crossed-log base.
    im = blank((32, 32)); mask = Image.new('L', im.size)
    d = ImageDraw.Draw(im); m = ImageDraw.Draw(mask)
    lines = [((5, 19, 3, 31), 3), ((26, 19, 28, 31), 3),
             ((3, 31, 26, 20), 3), ((6, 20, 28, 31), 3)]
    for points, width in lines:
        d.line(points, fill=3, width=width); m.line(points, fill=255, width=width)
    d.line((5, 19, 3, 31), fill=1); d.line((26, 19, 28, 31), fill=1)
    d.line((3, 30, 26, 19), fill=1, width=2)
    d.line((6, 19, 28, 30), fill=1, width=2)
    d.line((4, 31, 27, 20), fill=2); d.line((5, 21, 28, 32), fill=2)
    for points, width in [((5,19,3,31),1), ((26,19,28,31),1),
                          ((3,30,26,19),2), ((6,19,28,30),2),
                          ((4,31,27,20),1), ((5,21,28,32),1)]:
        m.line(points, fill=255, width=width)
    for x, y in ((4, 29), (11, 27), (19, 27), (27, 29)):
        d.point((x, y), fill=0); m.point((x, y), fill=255)
    return im, mask


def native_index(tile_id):
    assert tile_id < 96 or 128 <= tile_id < 224, tile_id
    return tile_id if tile_id < 96 else tile_id - 32


def tile_xy(tile_id):
    index = native_index(tile_id)
    return (index % 16) * 8, (index // 16) * 8


def block_image(sheet, meta, block):
    out = blank((32, 32))
    for offset, tile_id in enumerate(meta[block*16:block*16+16]):
        x, y = tile_xy(tile_id)
        out.paste(sheet.crop((x, y, x+8, y+8)), (offset % 4*8, offset // 4*8))
    return out


def colour(im, palette):
    im = im.copy()
    colours = [tuple(((v >> 3) << 3) | ((v >> 3) >> 2) for v in c) for c in palette]
    im.putpalette([v for c in colours for v in c] + [0]*756)
    return im.convert('RGBA')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    preserved = [*ROOT.glob('maps/*.blk'), ROOT/'data/tilesets/peon_metatiles.bin',
                 ROOT/'data/tilesets/peon_collision.asm', ROOT/'gfx/tilesets/peon_palette_map.bin']
    original_hashes = {str(p.relative_to(ROOT)): sha(p) for p in preserved}
    sheet = Image.open(ROOT/'gfx/tilesets/peon.png').copy()
    assert sheet.mode == 'P' and sheet.size == (128, 96) and set(sheet.tobytes()) <= {0, 1, 2, 3}
    previous_sheet = sheet.copy()
    meta = (ROOT/'data/tilesets/peon_metatiles.bin').read_bytes()
    world.build_blocks()  # Draws baseline indexed modules in memory, never main().
    baseline = {b: world.BLOCKS[b]['im'].copy() for b in TARGETS}
    patches = {}

    def put_tile(tile_id, pixels):
        assert tile_id not in (1, 44), 'Shared ground/blank tiles must stay intact'
        assert set(pixels.tobytes()) <= {0, 1, 2, 3}
        if tile_id in patches: assert patches[tile_id].tobytes() == pixels.tobytes()
        patches[tile_id] = pixels

    def put_region(block, im, x0=0, y0=0, x1=32, y1=32):
        for y in range(y0, y1, 8):
            for x in range(x0, x1, 8):
                tile_id = meta[block*16+y//8*4+x//8]
                if tile_id in (1, 44):
                    assert not any(im.crop((x, y, x+8, y+8)).tobytes())
                    continue
                put_tile(tile_id, im.crop((x, y, x+8, y+8)))

    cliff = blank((32, 32)); unit = cliff_module()
    for x in (0, 16):
        for y in (0, 16): cliff.paste(unit, (x, y))
    put_region(1, cliff)
    rock, rock_mask = boulder_module(); rock32 = blank((32, 32)); rock32.paste(rock, (8, 8))
    put_region(37, rock32)
    flag, flag_mask = banner(); put_region(6, flag)
    stakes, stakes_mask = palisade(); put_region(30, stakes)
    flame, flame_mask = flames(); torch = blank((32, 32)); torch.paste(flame, (8, 0))
    put_region(34, torch, 8, 0, 24, 16)
    logs, logs_mask = braces(); put_region(31, logs, 0, 24, 32, 32)
    for tile_id, tile in patches.items(): sheet.paste(tile, tile_xy(tile_id))
    assert len(set(meta)) == 192 and len(patches) == 27
    for tile_id in set(meta) - set(patches):
        x,y = tile_xy(tile_id)
        assert sheet.crop((x,y,x+8,y+8)).tobytes() == previous_sheet.crop((x,y,x+8,y+8)).tobytes()
    sheet.save(ROOT/'gfx/tilesets/peon.png')
    rendered = {b: block_image(sheet, meta, b) for b in TARGETS}
    masks = {1: Image.new('L', (32, 32), 255), 6: flag_mask, 30: stakes_mask,
             37: Image.new('L', (32, 32))}
    masks[37].paste(rock_mask, (8, 8))
    fire_mask = Image.new('L', (32, 32)); fire_mask.paste(flame_mask, (8, 8))
    fire_mask.paste(logs_mask.crop((0, 24, 32, 32)), (0, 24)); masks[39] = fire_mask
    torch_mask = Image.new('L', (32, 32)); torch_mask.paste(flame_mask, (8, 0))
    ImageDraw.Draw(torch_mask).rectangle((12, 13, 19, 18), fill=255)
    ImageDraw.Draw(torch_mask).rectangle((14, 15, 17, 29), fill=255); masks[34] = torch_mask
    # Tower exports use its actual baseline hut/brace silhouette plus new braces.
    tower = Image.new('L', (32, 32)); d = ImageDraw.Draw(tower)
    d.polygon([(1,18),(6,11),(15,4),(23,11),(30,18)], fill=255)
    d.rectangle((4,19,27,29), fill=255); d.rectangle((12,21,20,31), fill=255)
    d.line((5,19,3,31), fill=255, width=2); d.line((26,19,28,31), fill=255, width=2)
    tower.paste(logs_mask.crop((0,24,32,32)), (0,24)); masks[31] = tower
    font = ImageFont.load_default(); comparison = Image.new('RGB', (528, len(TARGETS)*208), (24,21,20))
    report = {'runtime_capture': False, 'source': 'Native indexed décor compilation.',
              'native_8x8_tile_slots': 192, 'patched_tile_ids': sorted(patches),
              'geometry_changed': False, 'collision_changed': False,
              'shared_updates': {'cliff': ['fortified_gate_wall'], 'flame': ['brazier','campfire'],
                                 'wood': ['watchtower_braces','campfire_logs']},
              'assets': {}, 'preserved_native_inputs': original_hashes}
    for row, (block, name) in enumerate(TARGETS.items()):
        palette_id = world.BLOCKS[block]['pal']; rgba = colour(rendered[block], world.BG[palette_id])
        rgba.putalpha(masks[block])
        assert set(rgba.getchannel('A').tobytes()) <= {0, 255}
        rgba.save(OUT/(name+'.png'))
        rgba.resize((256,256), Image.Resampling.NEAREST).save(OUT/(name+'_8x.png'))
        native = colour(rendered[block], world.BG[palette_id])
        native.save(OUT/(name+'_native_background.png'))
        before = colour(baseline[block], world.BG[palette_id])
        y = row*208; ImageDraw.Draw(comparison).text((8,y+5), name+' — original pixels / new pixels', font=font, fill=(255,232,187))
        comparison.paste(before.resize((192,192), Image.Resampling.NEAREST).convert('RGB'), (64,y+16))
        comparison.paste(native.resize((192,192), Image.Resampling.NEAREST).convert('RGB'), (296,y+16))
        report['assets'][name] = {'file': name+'.png', 'native_size': [32,32],
                                  'block_id': block, 'palette_id': palette_id,
                                  'binary_alpha': True, 'background_tile': block == 1,
                                  'changed_pixels': sum(a!=b for a,b in zip(baseline[block].tobytes(), rendered[block].tobytes()))}
    # A separately masked shelf export preserves pale colour-zero highlights.
    shelf_mask = Image.new('L',(16,16)); ImageDraw.Draw(shelf_mask).polygon(
        [(0,2),(3,0),(11,0),(15,3),(15,10),(12,14),(4,15),(0,12)], fill=255)
    shelf = colour(unit, world.BG[0]); shelf.putalpha(shelf_mask)
    shelf.save(OUT/'durotar_rock_shelf_16x16.png')
    shelf.resize((128,128),Image.Resampling.NEAREST).save(OUT/'durotar_rock_shelf_8x.png')
    report['assets']['durotar_rock_shelf'] = {'file':'durotar_rock_shelf_16x16.png',
        'native_size':[16,16], 'block_id':1, 'palette_id':0, 'binary_alpha':True,
        'source':'Semantic silhouette of one repeated native sandstone shelf.'}
    comparison.save(OUT/'environment_before_after.png')
    for name, expected in original_hashes.items(): assert sha(ROOT/name) == expected, name
    assert Image.open(ROOT/'gfx/tilesets/peon.png').tobytes() == sheet.tobytes()
    report['tileset_sha256'] = sha(ROOT/'gfx/tilesets/peon.png')
    (OUT/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'native_tiles':192, 'patched_tiles':len(patches), 'geometry_changed':False,
                      'assets':len(report['assets']), 'out':str(OUT.relative_to(ROOT))}))


if __name__ == '__main__':
    main()
