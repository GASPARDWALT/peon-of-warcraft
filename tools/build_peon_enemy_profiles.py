#!/usr/bin/env python3
"""Compile original dragon rank concepts into six native CGB BG tiles.

Gold Yarrog / silver Sarkoth are prototype presentation choices, not claims
about their exact WoW Classic creature classification. Normal creatures have
no rank emblem. Exported native PNGs have strictly binary transparency.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "references/generated/durotar_v022/enemy_profiles"
GFX = ROOT / "gfx/peon_enemy_profiles"
SOURCE = OUT / "concept_gold_silver_dragons.png"
PALETTES = {
    "gold": [(31,31,31), (31,25,8), (20,11,1), (0,0,0)],
    "silver": [(31,31,31), (26,28,31), (13,16,20), (0,0,0)],
}
CROPS = {"gold": (168,26,704,990), "silver": (868,18,1405,990)}

def pack(image):
    pixels = np.asarray(image)
    data = bytearray()
    for ty in range(0,24,8):
        for tx in range(0,16,8):
            for row in pixels[ty:ty+8,tx:tx+8]:
                data.append(sum((int(c)&1) << (7-i) for i,c in enumerate(row)))
                data.append(sum(((int(c)>>1)&1) << (7-i) for i,c in enumerate(row)))
    assert len(data) == 96
    return bytes(data)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    GFX.mkdir(parents=True,exist_ok=True)
    if not SOURCE.exists():
        raise SystemExit(f"Missing original concept: {SOURCE}")
    concept = Image.open(SOURCE).convert("RGBA")
    manifest = {"source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                "native_dimensions":[16,24], "native_tiles":6,
                "native_tile_ids":"$80..$85", "native_vram":"bank 1 $8800..$885f",
                "native_screen_tiles":{"x":10,"y":4,"width":2,"height":3},
                "bg_palette":5, "emblems":{}}
    preview = Image.new("RGBA",(128,96),(0,0,0,0))
    for i,(rank,palette) in enumerate(PALETTES.items()):
        # Hard alpha and nearest-neighbour reduction keep the final engine
        # image exact: no antialiasing, no implicit fifth colour, no glow.
        crop = concept.crop(CROPS[rank])
        native = np.asarray(crop.resize((16,24),Image.Resampling.NEAREST))
        colours = np.asarray(palette,dtype=np.int32) * 8
        differences = ((native[:,:,:3,None].transpose(0,1,3,2).astype(np.int32)
                        - colours[None,None,1:,:]) ** 2).sum(axis=-1)
        indices = (differences.argmin(axis=-1)+1).astype("uint8")
        indices[native[:,:,3] < 180] = 0
        engine = Image.fromarray(indices,"P")
        engine.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
        engine.save(GFX/f"{rank}_dragon.png")
        binary = pack(engine)
        (GFX/f"{rank}_dragon.2bpp").write_bytes(binary)
        (GFX/f"{rank}_dragon.pal").write_text("".join(f"\tRGB {r:02d}, {g:02d}, {b:02d}\n" for r,g,b in palette))
        rgb = np.asarray(palette,dtype="uint8")[indices] * 8
        alpha = np.where(indices==0,0,255).astype("uint8")
        exported = Image.fromarray(np.dstack((rgb,alpha)),"RGBA")
        assert set(np.unique(alpha)) == {0,255}
        assert len(exported.getcolors()) <= 4
        exported.save(OUT/f"{rank}_dragon.png")
        exported.resize((128,192),Image.Resampling.NEAREST).save(OUT/f"{rank}_dragon_8x.png")
        preview.alpha_composite(exported.resize((64,96),Image.Resampling.NEAREST),(i*64,0))
        manifest["emblems"][rank] = {
            "native_palette_rgb555":palette, "binary_sha256":hashlib.sha256(binary).hexdigest(),
            "species_alias":"PEON_MOB_YARROG" if rank=="gold" else "PEON_MOB_SARKOTH",
            "rank_basis":"Explicit prototype boss/rank adaptation; not a verified Classic rank classification.",
            "transparent_pixels":int((alpha==0).sum()),"opaque_pixels":int((alpha==255).sum()),
        }
    preview.save(OUT/"native_dragon_emblems_4x.png")
    (OUT/"asset_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (OUT/"README.md").write_text(
        "# Native enemy rank emblems\n\n"
        "Original dragon concepts are compiled into 16×24 pixel, six-tile CGB emblems. "
        "The native transparent PNGs are the actual ROM pixels, limited to three opaque colours "
        "and transparency. On the Game Boy background layer, transparent pixels use the white "
        "battle background. The full concept is an art reference, not a promise of higher ROM resolution.\n\n"
        "Gold for Yarrog and silver for Sarkoth are explicit prototype boss/rank adaptations. "
        "No unverified claim about their original WoW Classic rank is implied. Ordinary enemies "
        "have no dragon. The emblem is placed below the enemy name/HP panel, left of the 56×56 "
        "animated front portrait, and above the player HUD. It uses bank-1 signed BG tiles "
        "$80..$85 at $8800..$885f and palette 5. Both idle and animated enemy-front "
        "copies, player backpic, bank-0 font and battle OAM are untouched. Normal overworld "
        "sprite-cache loading restores this area when combat ends.\n")
    print("Compiled two original 16×24 dragon emblems: six tiles each, binary alpha, RGB555.")

if __name__ == "__main__":
    main()
