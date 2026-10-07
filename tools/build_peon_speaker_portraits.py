#!/usr/bin/env python3
"""Compile the seven original Warcraft speakers into native 24x24 portraits.

The public files retain alpha; engine PNGs use four ordered gray indexes.
Portraits occupy nine BG tiles and one four-colour palette, never OBJ tiles.
Village portraits are owned by build_peon_village_art.py and are not overwritten.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "references/generated/durotar_v021/speaker_portraits"
GFX = ROOT / "gfx/peon_portraits"
SOURCE = OUT / "concept_speaker_heads.png"
PALETTES = {
    "peon": [(255,255,255),(148,90,49),(123,181,66),(0,0,0)],
    "gornek": [(255,255,255),(165,66,41),(123,181,66),(0,0,0)],
    "hunter": [(255,255,255),(148,90,49),(123,181,66),(0,0,0)],
    "kento": [(255,255,255),(206,156,90),(99,57,33),(0,0,0)],
    "thrall": [(255,255,255),(173,132,66),(123,181,66),(0,0,0)],
    "warrior": [(255,255,255),(156,66,57),(123,181,66),(0,0,0)],
    "warlock": [(255,255,255),(115,165,66),(90,57,132),(0,0,0)],
}

def crop_cell(source, row, col, rows, cols, bounds):
    w, h = source.size
    box = (round(col*w/cols), round(row*h/rows),
           round((col+1)*w/cols), round((row+1)*h/rows))
    cell = source.crop(box)
    left, top, right, bottom = bounds
    return cell.crop((round(left*cell.width), round(top*cell.height),
                      round(right*cell.width), round(bottom*cell.height)))

def quantize(crop, colours):
    crop = crop.copy()
    # The source was drawn as enlarged pixels. Preserve dark eyes/tusks rather
    # than averaging those small features into the adjacent skin colour.
    crop.thumbnail((22,22), Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", (24,24))
    canvas.alpha_composite(crop, ((24-crop.width)//2, (24-crop.height)//2))
    pixels = np.array(canvas)
    values = (((pixels[:,:,:3,None].transpose(0,1,3,2).astype(float)
                - np.array(colours, dtype=float))**2).sum(axis=-1)).argmin(axis=-1)
    alpha = np.where(pixels[:,:,3] >= 180, 255, 0).astype("uint8")
    values[alpha == 0] = 0
    values = values.astype("uint8")
    public = Image.fromarray(np.dstack((np.array(colours,dtype="uint8")[values],alpha)), "RGBA")
    native = Image.fromarray(values, "P")
    native.putpalette([255,255,255,170,170,170,85,85,85,0,0,0] + [0]*756)
    return public, native, values

def pack_tiles(pixels):
    result = bytearray()
    for y in range(0,24,8):
        for x in range(0,24,8):
            for row in pixels[y:y+8,x:x+8]:
                result.append(sum((int(c)&1) << (7-i) for i,c in enumerate(row)))
                result.append(sum(((int(c)>>1)&1) << (7-i) for i,c in enumerate(row)))
    assert len(result) == 144
    return bytes(result)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    GFX.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert("RGBA")
    positions = {"peon":(0,0), "gornek":(0,1), "hunter":(0,2),
                 "kento":(0,3), "thrall":(1,0), "warrior":(1,1),
                 "warlock":(1,2)}
    crops = {}
    for name,(row,col) in positions.items():
        crop = crop_cell(source,row,col,2,4,(0,0,1,1))
        bounds = crop.getchannel("A").point(lambda v:255 if v>=180 else 0).getbbox()
        assert bounds, name
        crops[name] = crop.crop(bounds)
    gallery = Image.new("RGBA", (7*40,48), (35,29,31,255))
    draw = ImageDraw.Draw(gallery)
    manifest = {}
    for i, (name,colours) in enumerate(PALETTES.items()):
        public,native,pixels = quantize(crops[name],colours)
        public.save(OUT/f"{name}.png")
        public.resize((192,192),Image.Resampling.NEAREST).save(OUT/f"{name}_8x.png")
        native.save(GFX/f"{name}.png")
        (GFX/f"{name}.2bpp").write_bytes(pack_tiles(pixels))
        (GFX/f"{name}.pal").write_text("".join("\tRGB " + ", ".join(f"{c>>3:02d}" for c in colour) + "\n" for colour in colours))
        gallery.alpha_composite(public, (i*40+8,2))
        draw.text((i*40+1,30), name[:6], fill=(239,214,165))
        manifest[name] = {"size":[24,24], "tiles":9, "2bpp_bytes":144,
                          "palette_rgb555":[[c>>3 for c in colour] for colour in colours]}
    gallery.resize((1120,192),Image.Resampling.NEAREST).save(OUT/"speaker_portraits_gallery.png")
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(f"Generated {len(manifest)} native 24x24 speaker portraits in {OUT.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
