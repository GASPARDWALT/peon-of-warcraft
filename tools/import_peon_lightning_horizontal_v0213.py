#!/usr/bin/env python3
"""Rotate supplied Lightning Bolt art exactly into a horizontal native cast.

All original PNGs stay untouched. The entire 16x32 source canvas rotates 90
degrees clockwise into 32x16 with a pixel permutation, including transparency.
The existing source-derived native palettes and icon remain unchanged. This
tool imports only Lightning Bolt; it does not run historical art generators.
"""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import struct

from PIL import Image, ImageDraw

from import_peon_spell_pack_v1 import convert, encode, compile_png, palette_bytes

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "references/characters/peon_of_warcraft_spell_effects_pack_v1"
NATIVE = ROOT / "gfx/peon_lightning_horizontal_v0213"
ASM = ROOT / "gfx/peon_lightning_horizontal_v0213.asm"
PACK_ASM = ROOT / "gfx/peon_spell_pack_v1.asm"
OUT = ROOT / "references/generated/spell_tests/lightning_horizontal_v0213"
FRAMES = (
    ("player", "player_back/lightning_bolt_player_back_16x32.png", "Player"),
    ("enemy", "enemy_front/lightning_bolt_enemy_front_16x32.png", "Enemy"),
    ("impact", "impacts/lightning_bolt_explosion_32x32.png", "Impact"),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rel(path):
    return str(path.relative_to(ROOT))


def palettes_from_native(path):
    data = path.read_bytes()
    assert len(data) == 3 * 8
    words = struct.unpack("<12H", data)
    colors = [(word & 31, word >> 5 & 31, word >> 10 & 31) for word in words]
    return [colors[index:index + 4] for index in range(0, 12, 4)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rgbgfx", default="/workspace/toolchains/rgbds-1.0.4/rgbgfx")
    args = parser.parse_args()
    NATIVE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    source_hashes = {rel(SOURCE / file): sha((SOURCE / file).read_bytes()) for _, file, _ in FRAMES}
    palette_source = ROOT / "gfx/peon_spell_pack_v1/lightning_bolt_obj.gbcpal"
    palette_data = palette_source.read_bytes()
    palettes = palettes_from_native(palette_source)
    assert palette_bytes(palettes) == palette_data
    palette_target = NATIVE / "lightning_obj.gbcpal"
    palette_target.write_bytes(palette_data)
    unique, lookup, records, oam_blocks = [], {}, [], []
    contact = Image.new("RGBA", (3 * 420, 330), (30, 30, 40, 255))
    draw = ImageDraw.Draw(contact)
    for index, (role, file, label) in enumerate(FRAMES):
        original = Image.open(SOURCE / file).convert("RGBA")
        assert original.size == ((32, 32) if role == "impact" else (16, 32))
        assert set(original.getchannel("A").get_flattened_data()) <= {0, 255}
        rotated = original.transpose(Image.Transpose.ROTATE_270)
        assert rotated.size == ((32, 32) if role == "impact" else (32, 16))
        assert rotated.transpose(Image.Transpose.ROTATE_90).tobytes() == original.tobytes()
        derived_source = NATIVE / (role + "_source_rotated.png")
        rotated.save(derived_source)
        indexes, rendered, cells, metrics = convert(rotated, palettes)
        indexes.save(NATIVE / (role + "_indexes.png"))
        rendered.save(NATIVE / (role + "_native.png"))
        assert rendered.getchannel("A").tobytes() == rotated.getchannel("A").tobytes()
        oam = []
        for cell in cells:
            if not cell["nonempty"]:
                continue
            tile = encode(cell["pixels"])
            if tile not in lookup:
                lookup[tile] = len(unique)
                unique.append(cell["pixels"])
            oam.append((cell["x"] // 8 - rotated.width // 16,
                        cell["y"] // 8 - rotated.height // 16,
                        lookup[tile], 4 + cell["palette"]))
        prefix = "PeonSpellV1Lightning" + label
        oam_blocks.extend([f"DEF {prefix}OAMCount EQU {len(oam)}", f"{prefix}OAM::",
                           f"; Entire {file}, rotated 90 clockwise; source SHA256 {source_hashes[rel(SOURCE / file)]}"])
        oam_blocks.extend(f"\tdbsprite {x}, {y}, 0, 0, ${tile:02x}, ${attrs:02x}"
                          for x, y, tile, attrs in oam)
        oam_blocks.append(f"\tassert @ - {prefix}OAM == {prefix}OAMCount * 4")
        native_bbox = list(rendered.getchannel("A").getbbox())
        assert native_bbox[2] - native_bbox[0] > native_bbox[3] - native_bbox[1]
        records.append({"role": role, "source": rel(SOURCE / file),
                        "source_sha256": source_hashes[rel(SOURCE / file)],
                        "original_canvas": list(original.size), "native_canvas": list(rotated.size),
                        "entire_canvas_rotation": "90 degrees clockwise; dst_x=height-1-src_y, dst_y=src_x",
                        "exact_RGBA_rotation_roundtrip": True, "source_crop": [0, 0, *original.size],
                        "native_alpha_bbox": native_bbox,
                        "source_opaque_pixels": sum(bool(value) for value in original.getchannel("A").get_flattened_data()),
                        "native_opaque_pixels": sum(bool(value) for value in rendered.getchannel("A").get_flattened_data()),
                        "alpha_exact_after_rotation": True, "oam_label": prefix + "OAM",
                        "oam_count": len(oam), "OAM_rows": oam,
                        "peak_OBJ_per_source_scanline": max(Counter(y for _, y, _, _ in oam).values()),
                        "conversion": metrics, "native_preview": rel(NATIVE / (role + "_native.png"))})
        draw.text((index * 420 + 8, 8), role + " / exact source rotation", fill="white")
        zoom = original.resize((original.width * 6, original.height * 6), Image.Resampling.NEAREST)
        contact.alpha_composite(zoom, (index * 420 + 8, 32))
        zoom = rendered.resize((rendered.width * 6, rendered.height * 6), Image.Resampling.NEAREST)
        contact.alpha_composite(zoom, (index * 420 + 218, 118 if role != "impact" else 32))
    assert len(unique) <= 79
    packet = Image.new("P", (8, 8 * len(unique)))
    packet.putpalette(Image.open(NATIVE / "player_indexes.png").getpalette())
    for number, pixels in enumerate(unique):
        for y in range(8):
            for x in range(8):
                packet.putpixel((x, number * 8 + y), pixels[y * 8 + x])
    packet_path = NATIVE / "lightning_tiles.png"
    packet.save(packet_path)
    binary = compile_png(packet_path, args.rgbgfx, b"".join(encode(pixels) for pixels in unique), compress=True)
    asm = ["; Generated by tools/import_peon_lightning_horizontal_v0213.py.",
           "; Exact whole-canvas rotation of the user's individual Lightning Bolt PNGs.",
           "; Include within Peon Spell Effects v1; source-derived palettes4/5/6 unchanged.",
           f"DEF PeonSpellV1LightningGFXTileCount EQU {len(unique)}",
           "PeonSpellV1LightningGFX::", f'\tINCBIN "{binary["lz"]}"',
           "PeonSpellV1LightningOBPalettes::", f'\tINCBIN "{rel(palette_target)}"',
           "\tassert @ - PeonSpellV1LightningOBPalettes == 3 palettes", *oam_blocks]
    ASM.write_text("\n".join(asm) + "\n")
    current = PACK_ASM.read_text()
    start = current.find("DEF PeonSpellV1LightningGFXTileCount")
    end = current.find("PeonSpellV1LightningIconGFX::")
    include = 'INCLUDE "gfx/peon_lightning_horizontal_v0213.asm"\n'
    if start >= 0:
        assert end > start
        PACK_ASM.write_text(current[:start] + include + current[end:])
    else:
        assert include in current, "Missing Lightning-only graphics overlay."
    assert {rel(SOURCE / file): sha((SOURCE / file).read_bytes()) for _, file, _ in FRAMES} == source_hashes
    contact.convert("RGB").save(OUT / "source_rotation_native.png")
    manifest = {"source_pack": rel(SOURCE), "canonical_source_sha256": source_hashes,
                "source_files_unchanged": True, "generated_by": rel(Path(__file__).resolve()),
                "rotation_only_before_GBC_palette_fit": True, "smoothing": False,
                "new_drawn_pixels": False, "palette_source": rel(palette_source),
                "palette_sha256": sha(palette_data), "palette_bytes_unchanged": True,
                "projectile_canvas": [32, 16], "impact_canvas": [32, 32],
                "objects_per_scanline_limit": 10, "OBJ_count_limit": 40,
                "static_peak_lightning_OBJ_count": max(row["oam_count"] for row in records),
                "static_peak_lightning_OBJ_per_scanline": max(row["peak_OBJ_per_source_scanline"] for row in records),
                "frames": records, "packet": binary,
                "asm_include": rel(ASM), "runtime_validation": "Pending central ROM build."}
    (OUT / "import_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Horizontal supplied Lightning Bolt: {len(unique)} native tiles; "
          f"OAM {[row['oam_count'] for row in records]}; original PNGs and palettes unchanged.")


if __name__ == "__main__":
    main()
