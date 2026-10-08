#!/usr/bin/env python3
"""Prepared Durotar tree cutouts; does not alter native maps or tilesets.

Pixel geometry is authored at native resolution with binary transparency and
four opaque colours. These files are art proposals, not in-ROM captures.
"""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/warcraft_audio_update/trees'
PALETTES = {
    'deadthorn_tree': ['#342831', '#815238', '#b37b49', '#d1a36b'],
    'crooked_acacia': ['#30292c', '#875a3e', '#737a3d', '#b3a667'],
    'coastal_palm': ['#292d2c', '#996b42', '#657c3d', '#b3a667'],
}


def blank(size):
    return Image.new('L', size, 0)


def branch(draw, points, outer=3, inner=1):
    draw.line(points, fill=1, width=outer)
    draw.line(points, fill=2, width=inner)


def deadthorn():
    im = blank((32, 32))
    d = ImageDraw.Draw(im)
    # Forks keep open sky between them rather than forming a dense antler blob.
    branch(d, [(16,26),(15,20),(12,16),(11,12),(7,10),(5,6),(3,5)], 4, 2)
    branch(d, [(11,13),(11,8),(8,5),(8,2)], 3, 1)
    branch(d, [(15,20),(17,14),(16,9),(18,5),(18,2)], 4, 2)
    branch(d, [(16,10),(13,7),(14,3)], 3, 1)
    branch(d, [(17,17),(22,13),(24,8),(27,6),(28,3)], 4, 2)
    branch(d, [(23,11),(22,7),(24,3)], 3, 1)
    branch(d, [(21,16),(27,14),(29,11),(30,11)], 3, 1)
    branch(d, [(13,18),(8,17),(5,14),(2,14)], 3, 1)
    branch(d, [(9,17),(7,20),(4,21)], 3, 1)
    # A broad crooked root makes the one-cell collision footprint readable.
    d.polygon([(14,18),(18,17),(19,23),(18,27),(23,29),(25,30),
               (17,30),(15,29),(10,31),(7,31),(13,27),(14,23)], fill=1)
    d.polygon([(15,19),(17,18),(17,24),(16,28),(20,29),(16,29),
               (14,28),(10,30),(14,26)], fill=2)
    d.line([(15,20),(15,24),(14,27),(11,29)], fill=3)
    d.line([(16,10),(17,14),(16,18)], fill=3)
    d.line([(12,15),(10,12),(7,11)], fill=3)
    d.line([(22,13),(24,9),(26,7)], fill=3)
    d.point((15,22), fill=4); d.point((14,26), fill=4)
    d.line((12,28,10,30), fill=4)
    # Bark checks are one-pixel cuts, never soft shade bands.
    d.line((17,21,16,22), fill=1)
    d.point((16,26), fill=1); d.point((11,13), fill=4)
    return im


def acacia():
    im = blank((32, 32)); d = ImageDraw.Draw(im)
    branch(d, [(19,27),(18,22),(16,18),(15,12),(10,8)], 5, 3)
    branch(d, [(16,18),(21,14),(24,10),(27,9)], 4, 2)
    branch(d, [(15,14),(18,8),(17,6)], 3, 1)
    branch(d, [(14,16),(8,13),(6,10)], 3, 1)
    clusters = [
        ([(1,10),(3,7),(6,7),(6,5),(10,4),(12,6),(13,9),(11,12),
          (8,12),(7,14),(3,13),(3,11)],
         [(2,10),(4,8),(7,8),(7,6),(10,5),(11,7),(12,9),(10,11),
          (7,11),(6,13),(4,12),(4,10)],
         [(5,8,8,8),(7,6,9,6),(4,10,5,10)]),
        ([(10,5),(13,2),(17,2),(19,4),(22,4),(23,7),(20,10),
          (16,10),(14,11),(11,9)],
         [(11,5),(14,3),(17,3),(18,5),(21,5),(22,7),(19,9),
          (16,9),(14,10),(12,8)],
         [(14,4,17,4),(12,6,15,6),(18,6,20,6)]),
        ([(20,9),(23,6),(27,5),(29,7),(30,7),(31,11),(29,13),
          (26,13),(25,15),(21,14),(19,12)],
         [(21,9),(24,7),(27,6),(29,8),(30,11),(28,12),(25,12),
          (24,14),(22,13),(20,11)],
         [(24,8,28,8),(23,10,25,10),(27,10,29,10)]),
    ]
    for outline, fill, accents in clusters:
        d.polygon(outline, fill=1); d.polygon(fill, fill=3)
        for line in accents: d.line(line, fill=4)
    d.polygon([(17,23),(21,23),(21,27),(24,29),(25,30),(19,30),
               (16,29),(12,31),(10,31),(16,27)], fill=1)
    d.polygon([(18,23),(20,24),(19,27),(22,29),(18,29),(16,28),
               (13,30),(17,27)], fill=2)
    d.line([(16,15),(17,20),(19,23),(18,27),(15,29)], fill=4)
    d.line((20,25,20,27), fill=1); d.point((18,21), fill=1)
    return im


def palm():
    im = blank((32, 40)); d = ImageDraw.Draw(im)
    # The leaning trunk leaves a large open gap below the coastal crown.
    d.polygon([(14,10),(18,10),(18,17),(17,24),(19,32),(19,36),
               (23,38),(23,39),(17,39),(13,38),(10,39),(8,39),
               (14,35),(14,31),(12,25),(13,18)], fill=1)
    d.polygon([(15,11),(17,11),(16,19),(15,25),(17,32),(17,36),
               (20,38),(17,38),(15,36),(15,31),(14,25)], fill=2)
    d.line([(15,13),(14,21),(14,26),(16,33),(16,36)], fill=4)
    for y, x in [(17,14),(22,13),(27,14),(32,16),(35,16)]:
        d.line((x,y,x+2,y+1), fill=1)
        d.point((x,y-1), fill=4)
    leaves = [
        ([(16,10),(12,7),(7,7),(3,10),(1,14),(0,17),(2,16),
          (5,12),(8,10),(13,10)],
         [(13,8),(8,8),(4,11),(2,15),(6,11),(9,9),(14,10)]),
        ([(16,9),(13,5),(9,3),(4,3),(2,5),(6,5),(10,7),(13,10)],
         [(13,7),(10,5),(5,4),(7,5),(11,8),(14,9)]),
        ([(16,10),(15,6),(16,2),(19,0),(22,1),(20,3),(18,6),(18,10)],
         [(16,7),(17,3),(19,1),(20,1),(18,4),(17,8)]),
        ([(17,9),(22,4),(27,3),(30,5),(31,8),(28,7),(25,6),
          (21,9),(18,11)],
         [(19,9),(23,5),(27,4),(29,5),(26,5),(23,7),(20,10)]),
        ([(17,10),(23,9),(27,11),(30,15),(31,19),(28,17),(25,13),
          (21,12),(18,12)],
         [(19,10),(23,10),(26,12),(29,16),(26,13),(22,11),(19,12)]),
        ([(16,10),(19,13),(20,17),(18,21),(17,18),(17,15),(14,12)],
         [(16,11),(18,14),(19,17),(18,19),(18,16),(16,13)]),
    ]
    for outline, fill in leaves:
        d.polygon(outline, fill=1); d.polygon(fill, fill=3)
    d.line([(4,11),(8,8),(12,8)], fill=4)
    d.line([(7,4),(10,5),(12,6)], fill=4)
    d.line([(17,5),(18,3),(19,2)], fill=4)
    d.line([(22,7),(25,5),(27,5)], fill=4)
    d.line([(23,11),(26,13),(28,15)], fill=4)
    d.point((17,13), fill=4)
    # Two small coconuts tie the crown to the warm brown bark.
    d.rectangle((14,10,16,12), fill=1); d.point((15,11), fill=2)
    d.rectangle((17,10,19,12), fill=1); d.point((18,11), fill=4)
    return im


def rgba(indexed, colors):
    pixels = [(0,0,0,0)] + [tuple(bytes.fromhex(c.lstrip('#'))) + (255,) for c in colors]
    result = Image.new('RGBA', indexed.size)
    result.putdata([pixels[i] for i in indexed.tobytes()])
    return result


def checker(size):
    im = Image.new('RGB', size, '#e0c49a'); d = ImageDraw.Draw(im)
    for y in range(0, size[1], 16):
        for x in range(0, size[0], 16):
            if (x//16+y//16)%2: d.rectangle((x,y,x+15,y+15),fill='#d3b58a')
    return im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assets = [('deadthorn_tree', deadthorn(), 'Valley cliffs and dry canyon shoulders'),
              ('crooked_acacia', acacia(), 'Sparse Den/canyon trees, away from the main road'),
              ('coastal_palm', palm(), 'Senjin coastal edge and beach-side buildings')]
    manifest = {'status':'Prepared art; NOT integrated into the ROM.',
                'runtime_capture':False, 'native_maps_modified':False,
                'native_tileset_slots_current_budget':192, 'assets':[]}
    sheet = checker((864,456)); d = ImageDraw.Draw(sheet)
    d.rectangle((0,0,863,55),fill='#30292c')
    d.text((20,14),'DUROTAR TREES - PREPARED PIXEL ART',fill='#efd9ad')
    d.text((20,34),'Native sprites enlarged 8x / not ROM captures',fill='#efd9ad')
    for n,(name,indexed,placement) in enumerate(assets):
        im = rgba(indexed, PALETTES[name]); path = OUT/(name+'.png')
        im.save(path)
        im.resize((im.width*8,im.height*8),Image.Resampling.NEAREST).save(OUT/(name+'_8x.png'))
        raw = im.tobytes()
        values = {tuple(raw[i:i+4]) for i in range(0,len(raw),4)}
        alpha = {p[3] for p in values}
        colors = {p[:3] for p in values if p[3]}
        assert alpha=={0,255} and len(colors)<=4
        assert im.size in ((32,32),(32,40))
        occupied = sum(any(indexed.getpixel((x,y)) for y in range(by,by+8) for x in range(bx,bx+8))
                       for by in range(0,im.height,8) for bx in range(0,im.width,8))
        enlarged = im.resize((im.width*8,im.height*8),Image.Resampling.NEAREST)
        sheet.paste(enlarged,(n*288+16,76),enlarged)
        d.text((n*288+16,408),name,fill='#30292c')
        d.text((n*288+16,426),f'{im.width}x{im.height} / {len(colors)} opaque colors / binary alpha',fill='#30292c')
        manifest['assets'].append({'name':name,'file':str(path.relative_to(ROOT)),
            'native_size':list(im.size),'opaque_colors':len(colors),'alpha_values':sorted(alpha),
            'palette':PALETTES[name],'occupied_8x8_cells':occupied,
            'suggested_zone_placement':placement,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'rom_integrated':False})
    sheet.save(OUT/'durotar_trees_contact_sheet.png')
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    main()
