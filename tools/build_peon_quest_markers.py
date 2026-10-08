#!/usr/bin/env python3
"""Compile three original, high-contrast Classic quest symbols at 16×16."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"references/generated/durotar_v022/quest_markers"
GFX=ROOT/"gfx/sprites"

def pack(image):
    pixels=np.asarray(image);data=bytearray()
    for y in (0,8):
        for x in (0,8):
            for row in pixels[y:y+8,x:x+8]:
                data.extend([sum((int(v)&1)<<(7-i) for i,v in enumerate(row)),
                             sum(((int(v)>>1)&1)<<(7-i) for i,v in enumerate(row))])
    assert len(data)==64
    return bytes(data)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest={"dimensions":[16,16],"sprite_type":"STILL_SPRITE","tiles_per_sprite":4,"states":{}}
    preview=Image.new("RGBA",(384,128))
    for number,(name,question,gray) in enumerate((
            ("available_yellow",False,False),("active_gray",True,True),("complete_yellow",True,False))):
        mask=Image.new("L",(16,16));draw=ImageDraw.Draw(mask)
        if question:
            draw.line([(4,3),(5,2),(9,2),(10,3),(10,5),(8,7),(7,7),(7,9)],fill=255,width=2)
            draw.rectangle((6,12,8,13),fill=255)
        else:
            draw.rectangle((6,2,8,8),fill=255)
            draw.rectangle((6,11,8,13),fill=255)
        outline=np.asarray(mask.filter(ImageFilter.MaxFilter(3)))>0
        fill=np.asarray(mask)>0
        pixels=np.zeros((16,16),dtype="uint8")
        pixels[outline]=3 if gray else 2
        pixels[fill]=1 if gray else 3
        engine=Image.fromarray(pixels,"P")
        engine.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
        stem=f"peon_quest_{name}"
        engine.save(GFX/f"{stem}.png")
        (GFX/f"{stem}.2bpp").write_bytes(pack(engine))
        palette=[(31,31,31),(17,17,17),(31,25,7),(1,1,1)] if gray else [
            (31,31,31),(22,15,7),(9,5,2),(31,26,3)]
        rgba=Image.fromarray(np.dstack((np.asarray(palette,dtype="uint8")[pixels]*8,
                                    np.where(pixels==0,0,255).astype("uint8"))),"RGBA")
        assert len(rgba.getcolors())<=4
        rgba.save(OUT/f"{name}.png")
        expanded=rgba.resize((128,128),Image.Resampling.NEAREST)
        expanded.save(OUT/f"{name}_8x.png");preview.alpha_composite(expanded,(number*128,0))
        manifest["states"][name]={"native_path":f"gfx/sprites/{stem}.png", "binary_bytes":64,
            "sprite_id":54 if gray else 53 if not question else 60,
            "object_palette":5 if gray else 4,
            "palette_override":"BG-independent OBJ palette5 colour1 becomes neutral gray; restore red in imp cave." if gray else "Existing gold/brown OBJ palette4, unchanged."}
    preview.save(OUT/"three_native_states_8x.png")
    (OUT/"asset_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (OUT/"README.md").write_text(
        "# Native quest markers\n\n"
        "The three PNGs are the exact 16×16 overworld glyphs: available yellow !, "
        "accepted/incomplete gray ?, and ready-to-turn-in yellow ?. Each glyph has "
        "four native tiles and strictly binary alpha. Expanded previews use nearest-neighbour "
        "scaling. They are UI markers above quest givers, not replacement character sprites.\n\n"
        "The ROM uses otherwise unused sprite IDs 53, 54 and 60. Yellow keeps the existing "
        "gold/brown OBJ palette 4. Gray uses OBJ palette 5 with only its first opaque "
        "colour replaced by neutral RGB555 (17,17,17) in quest-marker maps. The cave "
        "retains the red imp palette. Root map scripts control quest state, disappearance, "
        "and map-load restoration without adding save slots or changing SRAM layout.\n")
    print("Compiled ! yellow, ? gray, ? yellow: four native tiles each, binary transparency.")

if __name__=="__main__":main()
