#!/usr/bin/env python3
"""Original, tile-aware Durotar plants for the native v0.25 environment.

Each public plant function returns (indices, palette_grid, alpha_mask).
Indices are 32x32 L pixels in 0..3; zero is transparent. The 4x4 L grid
chooses one existing GBC palette for each 8x8 tile. No native asset, map,
or ROM is changed by this module. Running it writes inspectable PNGs only.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw
from build_peon_environment_palettes import BG


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "references/generated/environment_v025/plants"
def _canvas(palette=2):
    return Image.new("L", (32, 32), 0), Image.new("L", (4, 4), palette)


def _finish(im, grid):
    # Empty tiles use the same neutral palette across all four plants.
    for ty in range(4):
        for tx in range(4):
            if not im.crop((tx*8, ty*8, tx*8+8, ty*8+8)).getbbox():
                grid.putpixel((tx, ty), 1)
    alpha = im.point(lambda p: 255 if p else 0)
    assert set(im.tobytes()) <= {0, 1, 2, 3}
    assert set(alpha.tobytes()) <= {0, 255}
    return im, grid, alpha


def cactus():
    """Upright saguaro, two raised arms, two red flowers; tile-safe bloom caps."""
    im, grid = _canvas()
    d = ImageDraw.Draw(im)
    # Main body is seven pixels wide: ridges remain readable at 1x.
    d.polygon([(13,8),(16,8),(18,10),(18,28),(17,30),(12,30),
               (11,28),(11,11)], fill=3)
    d.polygon([(13,9),(15,9),(17,11),(17,28),(16,29),(13,29),
               (12,27),(12,11)], fill=2)
    d.line([(13,11),(13,27)], fill=1)
    d.line([(16,12),(16,28)], fill=3)
    d.point((14,9), fill=1)
    # Left arm curves up, right arm is taller; neither grows into a bloom tile.
    d.polygon([(4,18),(5,16),(7,16),(8,18),(8,20),(12,20),
               (12,23),(6,23),(4,22)], fill=3)
    d.polygon([(5,18),(6,17),(7,19),(7,21),(11,21),
               (11,23),(6,23),(5,21)], fill=2)
    d.line((5,18,5,20), fill=1)
    d.point((7,22), fill=1)
    d.polygon([(24,10),(25,8),(27,8),(28,10),(28,20),
               (26,23),(18,23),(18,19),(24,19)], fill=3)
    d.polygon([(25,10),(26,9),(27,11),(27,19),(25,22),
               (19,22),(19,20),(25,20)], fill=2)
    d.line((25,11,25,18), fill=1)
    d.point((22,21), fill=1)
    # Flower caps use only palette 6 in row 0; no green pixel shares their tiles.
    for x in (13, 28):
        d.polygon([(x,2),(x+1,3),(x+2,4),(x+1,6),
                   (x-1,7),(x-3,5),(x-2,3)], fill=3)
        d.polygon([(x,3),(x+1,4),(x,5),(x-1,6),(x-2,5),
                   (x-1,3)], fill=2)
        d.point((x-1,4), fill=1)
        d.point((x,4), fill=1)
    grid.putpixel((1,0), 6)
    grid.putpixel((3,0), 6)
    return _finish(im, grid)


def scrub():
    """Low desert agave cluster, long sharp leaves and a separate small shoot."""
    im, grid = _canvas()
    d = ImageDraw.Draw(im)
    leaves = [
        ([(11,29),(6,27),(3,25),(2,24),(6,24),(9,26),(12,28)],
         [(10,28),(6,26),(4,25),(7,25),(10,27)]),
        ([(11,29),(8,22),(8,17),(10,16),(12,23),(13,28)],
         [(11,27),(9,21),(9,18),(10,20),(12,27)]),
        ([(12,29),(12,21),(15,16),(16,16),(15,23),(14,29)],
         [(13,28),(13,22),(15,18),(14,24)]),
        ([(12,29),(16,22),(20,19),(22,19),(19,23),(15,29)],
         [(14,28),(17,23),(20,21),(17,25)]),
        ([(12,29),(17,26),(22,25),(23,27),(18,29),(13,30)],
         [(15,28),(19,26),(21,26),(18,28)]),
    ]
    for edge, body in leaves:
        d.polygon(edge, fill=3)
        d.polygon(body, fill=2)
    d.line([(4,25),(6,25),(8,26)], fill=1)
    d.line([(9,18),(10,23),(11,26)], fill=1)
    d.line([(15,18),(14,22),(13,25)], fill=1)
    d.line([(20,20),(17,23),(16,25)], fill=1)
    # The small shoot shares the same green palette and does not fill open sky.
    d.polygon([(25,29),(23,25),(23,24),(25,25),(26,27),
               (28,25),(30,24),(29,27),(27,29)], fill=3)
    d.line([(25,28),(24,26),(24,25)], fill=2)
    d.line([(26,28),(28,26),(29,25)], fill=1)
    d.rectangle((10,29,15,30), fill=3)
    d.line((11,29,14,29), fill=2)
    d.point((12,28), fill=1)
    return _finish(im, grid)


def palm():
    """Coastal palm: airy green crown, bent warm trunk and two coconuts."""
    im, grid = _canvas()
    d = ImageDraw.Draw(im)
    leaves = [
        ([(18,11),(13,8),(8,8),(3,11),(1,15),(4,13),
           (9,10),(14,10),(18,13)],
         [(17,11),(13,9),(8,9),(4,12),(9,10),(14,10)]),
        ([(18,10),(15,7),(11,4),(8,4),(8,6),(11,6),
           (13,8),(16,11)],
         [(16,9),(13,6),(9,5),(10,5),(12,6),(14,8)]),
        ([(18,11),(18,5),(21,1),(23,0),(23,2),(22,4),
           (21,8),(21,12)],
         [(19,10),(19,5),(22,2),(23,1),(21,5),(20,10)]),
        ([(19,10),(23,7),(26,9),(30,9),(31,12),(28,11),
           (25,10),(22,11),(20,13)],
         [(20,10),(23,8),(26,9),(29,10),(25,9),(22,10)]),
        ([(19,11),(24,10),(28,12),(30,15),(27,15),(25,13),
           (22,13),(20,14)],
         [(21,11),(25,11),(28,14),(25,12),(22,12)]),
        ([(18,11),(15,12),(12,15),(16,15),(19,13),(21,15),
           (23,15),(21,12)],
         [(17,12),(15,14),(18,13),(20,13),(21,14)]),
    ]
    for edge, body in leaves:
        d.polygon(edge, fill=3)
        d.polygon(body, fill=2)
    d.line([(5,11),(9,9),(13,9)], fill=1)
    d.line([(9,5),(11,5),(13,7)], fill=1)
    d.line([(19,7),(20,4),(22,2)], fill=1)
    d.line([(23,8),(25,9),(27,9)], fill=1)
    d.point((24,11), fill=1)
    # Brown starts exactly at y16 so the lower eight tiles own palette 5.
    for ty in (2,3):
        for tx in range(4):
            grid.putpixel((tx,ty),5)
    d.polygon([(18,16),(22,16),(22,20),(23,24),(25,28),
               (28,29),(30,30),(24,31),(20,30),(22,27),
               (20,23),(18,20)], fill=3)
    d.polygon([(19,16),(21,16),(21,20),(22,25),(24,28),
               (26,30),(23,30),(23,28),(21,24),(19,20)], fill=2)
    d.line([(19,17),(20,21),(21,25),(23,28),(24,29)], fill=1)
    d.line((20,19,22,19), fill=3)
    d.line((21,23,23,23), fill=3)
    d.line((23,27,24,27), fill=3)
    # Nuts hang at the crown/trunk boundary, each with a tiny ivory glint.
    d.rectangle((15,16,17,18),fill=3)
    d.point((16,17),fill=2)
    d.rectangle((22,16,24,18),fill=3)
    d.point((23,17),fill=2)
    return _finish(im, grid)


def deadthorn():
    """Crooked dead tree with asymmetric forks, open gaps and visible roots."""
    im, grid = _canvas(5)
    d = ImageDraw.Draw(im)

    def branch(points, width=3):
        d.line(points, fill=3, width=width)
        d.line(points, fill=2, width=max(1,width-2))

    branch([(15,28),(14,22),(16,16),(15,11),(16,6),(20,3),(22,3)],4)
    branch([(16,16),(10,13),(9,8),(10,4)],3)
    branch([(10,13),(5,11),(3,9),(2,9)],3)
    branch([(9,9),(6,9),(5,9)],3)
    branch([(15,11),(20,10),(22,7),(22,3)],3)
    branch([(20,10),(23,13),(28,11),(30,9)],3)
    branch([(14,22),(9,19),(6,16),(2,16)],3)
    branch([(9,19),(5,22),(3,22)],3)
    branch([(16,18),(21,17),(24,19),(29,17)],3)
    # Root footprint and broken bark produce depth without a ground ellipse.
    d.polygon([(13,22),(17,21),(18,26),(18,28),(23,30),
               (23,31),(18,31),(15,29),(11,31),(8,31),
               (12,28)],fill=3)
    d.polygon([(14,23),(16,22),(16,27),(17,29),(21,30),
               (18,30),(15,28),(11,30),(9,30),(13,27)],fill=2)
    d.line([(14,23),(14,27),(12,29),(10,30)],fill=1)
    d.line([(16,7),(16,10),(17,12)],fill=1)
    d.line([(11,13),(10,10),(10,7)],fill=1)
    d.line([(20,9),(22,7),(22,5)],fill=1)
    d.point((15,20),fill=1)
    d.point((17,26),fill=3)
    d.point((16,24),fill=3)
    return _finish(im, grid)


PLANTS = {"cactus": cactus, "scrub": scrub, "palm": palm, "deadthorn": deadthorn}


def rgba(plant):
    im, grid, mask = plant
    result = Image.new("RGBA",im.size,(0,0,0,0))
    for y in range(32):
        for x in range(32):
            if mask.getpixel((x,y)):
                pal = BG[grid.getpixel((x//8,y//8))]
                rgb = pal[im.getpixel((x,y))]
                result.putpixel((x,y),rgb+(255,))
    return result


def tile_patterns(plant):
    im, grid, _ = plant
    result = []
    for ty in range(4):
        for tx in range(4):
            tile = im.crop((tx*8,ty*8,tx*8+8,ty*8+8))
            if tile.getbbox():
                result.append((grid.getpixel((tx,ty)),tile.tobytes()))
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    plants = {name:fn() for name,fn in PLANTS.items()}
    patterns = set()
    manifest = {"native_size":[32,32],"transparent_index":0,
                "alpha_values":[0,255],"rom_modified":False,"assets":{}}
    sheet = Image.new("RGB",(1024,400),"#c49960")
    d = ImageDraw.Draw(sheet)
    d.rectangle((0,0,1023,43),fill="#382a20")
    d.text((18,14),"DUROTAR / NATIVE 32x32 PLANTS / PREPARED TILE-PALETTE ART",fill="#ffdfab")
    for n,(name,plant) in enumerate(plants.items()):
        indices,grid,alpha = plant
        image = rgba(plant)
        image.save(OUT/(name+".png"))
        indices.save(OUT/(name+"_indices.png"))
        grid.save(OUT/(name+"_palettes.png"))
        alpha.save(OUT/(name+"_alpha.png"))
        enlarged = image.resize((256,256),Image.Resampling.NEAREST)
        enlarged.save(OUT/(name+"_8x.png"))
        sheet.paste(enlarged,(n*256,72),enlarged)
        cells=tile_patterns(plant)
        patterns.update(cells)
        manifest["assets"][name]={"occupied_tiles":len(cells),
            "unique_palette_patterns":len(set(cells)),
            "palettes":sorted({p for p,_ in cells})}
        d.text((n*256+16,352),name.upper(),fill="#382a20")
        d.text((n*256+16,371),str(len(cells))+" occupied 8x8 cells",fill="#382a20")
    manifest["unique_nonblank_palette_patterns_total"] = len(patterns)
    manifest["unique_nonblank_pixel_patterns_total"] = len({p for _,p in patterns})
    assert len(patterns) <= 40, "Keep the shared native plant tile budget bounded."
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    sheet.save(OUT/"plants_contact_sheet.png")
    print(json.dumps(manifest,indent=2))


if __name__=="__main__":
    main()
