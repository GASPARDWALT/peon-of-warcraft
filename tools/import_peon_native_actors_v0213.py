#!/usr/bin/env python3
"""Restore archived native actor packets without drawing or regenerating art.

Only byte copies, palette metadata and decoded verification previews are emitted.
The original four-frame enemy dictionaries and their frame maps remain intact.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "gfx/native_actor_restore_v0213"
PREVIEW = ROOT / "references/generated/native_actor_restore_v0213"
HERO_PALETTE = ((31, 31, 31), (15, 22, 8), (18, 11, 6), (0, 0, 0))
WORLD_PALETTE = ((31, 31, 31), (18, 11, 6), (15, 22, 8), (1, 1, 1))
PAPER = (31, 29, 23)
SOURCES = {
    "shaman/overworld.bin": "8815123a338e95a28a38ed86e235be9838366e9102457d8557544a4c2b11e25b",
    "shaman/front_frames.bin": "e3a144c2f8288a8dcb2c1d0b4cb283e8936b374a1978f34752efdec22d6b1ae7",
    "shaman/portrait_frames.bin": "d3b7e70f58e10d2dce9649d169110ce946be7e59ed055aaa81a6ea3097c05c06",
    "shaman/back_frames.bin": "f63530fec765b2cdf54d7fb3d0c86073cc6c1c4d9154385826214f8c942beb7b",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def palette_bytes(colors) -> bytes:
    return b"".join((r | (g << 5) | (b << 10)).to_bytes(2, "little") for r, g, b in colors)


def unpack_palette(data: bytes):
    return [tuple((int.from_bytes(data[i:i + 2], "little") >> s) & 31 for s in (0, 5, 10))
            for i in range(0, len(data), 2)]


def decode(data: bytes, width: int, height: int, *, column_major=True, tilemap=None):
    """Decode existing indexed tile bytes; never resample or invent a pixel."""
    out = Image.new("P", (width, height))
    tiles_w, tiles_h = width // 8, height // 8
    for y in range(tiles_h):
        for x in range(tiles_w):
            position = x * tiles_h + y if column_major else y * tiles_w + x
            tile = position if tilemap is None else tilemap[position]
            source = data[tile * 16:tile * 16 + 16]
            assert len(source) == 16
            for iy in range(8):
                for ix in range(8):
                    shift = 7 - ix
                    value = ((source[2 * iy] >> shift) & 1) | (((source[2 * iy + 1] >> shift) & 1) << 1)
                    out.putpixel((8 * x + ix, 8 * y + iy), value)
    return out


def preview(indexed, colors, target: Path):
    colors8 = [tuple(round(channel * 255 / 31) for channel in color) for color in colors]
    image = Image.new("RGBA", indexed.size)
    image.putdata([(*colors8[index], 0 if index == 0 else 255) for index in indexed.get_flattened_data()])
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    image.resize((image.width * 4, image.height * 4), Image.Resampling.NEAREST).save(
        target.with_name(target.stem + "_4x.png"))


def main():
    records = []

    def put(path: str, data: bytes, *, source=None, note=None):
        target = OUTPUT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        records.append({"output": target.relative_to(ROOT).as_posix(), "bytes": len(data),
                        "sha256": sha(data), "source": source, "note": note})

    def copy(source: Path, output: str):
        data = source.read_bytes()
        put(output, data, source=source.relative_to(ROOT).as_posix(), note="Byte-for-byte archived packet copy")
        return data

    # The approved v0.2.6 Shaman body includes the original v0.2.1 rear actor.
    # Base Peon and Shaman deliberately share this archived body. Other classes
    # retain their current bindings rather than reviving procedural substitutes.
    for leaf in ("overworld.bin", "front_frames.bin", "portrait_frames.bin", "back_frames.bin"):
        source = ROOT / "gfx/peon_classes/shaman" / leaf
        assert sha(source.read_bytes()) == SOURCES[f"shaman/{leaf}"], source
        copy(source, "peon/" + leaf)
    hero = palette_bytes(HERO_PALETTE)
    put("peon/back_palettes.bin", hero * 2, note="Original uniform BG0 and BG6 colors")
    put("peon/back_attrs.bin", bytes(36), note="Native 6x6 rear tiles all use BG0")
    put("peon/front_palettes.bin", hero * 2, note="Original uniform BG1 and BG5 colors")
    put("peon/front_attrs.bin", bytes([1]) * 49, note="Native 7x7 front tiles all use BG1")
    put("peon/profile_palettes.bin", palette_bytes((PAPER, *HERO_PALETTE[1:])) * 4,
        note="Native profile paper plus original colors for BG2/4/6/7")
    put("peon/profile_attrs.bin", bytes([2]) * 49)
    world_text = "\n".join("\tRGB " + ", ".join(map(str, color)) for color in WORLD_PALETTE) + "\n"
    put("peon/world_preview.pal", world_text.encode(), note="Original native hero color order")
    put("peon/world_obj.pal", world_text.encode(), note="Hero OBJ2 only; root applies scoped palette hook")
    back = (OUTPUT / "peon/back_frames.bin").read_bytes()
    front = (OUTPUT / "peon/front_frames.bin").read_bytes()
    portrait = (OUTPUT / "peon/portrait_frames.bin").read_bytes()
    for frame in range(3):
        preview(decode(back[frame * 576:(frame + 1) * 576], 48, 48), HERO_PALETTE,
                PREVIEW / f"peon_back_{frame}.png")
        # Row-major profile packets must reconstruct the same authored front.
        face = decode(front[frame * 784:(frame + 1) * 784], 56, 56)
        stats = decode(portrait[frame * 784:(frame + 1) * 784], 56, 56, column_major=False)
        assert face.tobytes() == stats.tobytes(), ("profile/front order mismatch", frame)
        preview(face, HERO_PALETTE, PREVIEW / f"peon_front_{frame}.png")

    for species, role, opaque in (("rattata", "boar", ((25, 19, 11), (14, 8, 4), (0, 0, 0))),
                                  ("geodude", "imp", ((31, 25, 7), (27, 5, 3), (0, 0, 0)))):
        folder = ROOT / "gfx/pokemon" / species
        for leaf in ("front.animated.2bpp", "front.animated.2bpp.lz", "front.animated.tilemap",
                     "anim.asm", "anim_idle.asm", "frames.asm", "bitmask.asm", "back.2bpp", "back.2bpp.lz"):
            copy(folder / leaf, role + "/" + leaf)
        colors = ((31, 31, 31), *opaque)
        assert unpack_palette((folder / "normal.gbcpal").read_bytes()) == list(colors)
        pal = palette_bytes(colors)
        put(role + "/enemy_palettes.bin", pal * 2)
        put(role + "/enemy_attrs.bin", bytes([1]) * 49)
        original = Image.open(folder / "front.png").convert("RGB")
        assert original.size == (56, 224)
        source_colors = sorted(set(original.get_flattened_data()), key=sum, reverse=True)
        assert len(source_colors) == 4
        indices = {color: index for index, color in enumerate(source_colors)}
        dictionary = (OUTPUT / role / "front.animated.2bpp").read_bytes()
        maps = (OUTPUT / role / "front.animated.tilemap").read_bytes()
        assert len(maps) == 196
        assert len(dictionary) // 16 == (109 if role == "boar" else 89)
        for frame in range(4):
            native = decode(dictionary, 56, 56, tilemap=maps[frame * 49:(frame + 1) * 49])
            reference = original.crop((0, frame * 56, 56, (frame + 1) * 56))
            assert native.tobytes() == bytes(indices[color] for color in reference.get_flattened_data()), (
                role, frame, "native packet no longer matches complete archived PNG")
            preview(native, colors, PREVIEW / f"{role}_front_{frame}.png")
        if role == "imp":
            raw = (folder / "back.2bpp").read_bytes()
            assert len(raw) == 576
            put("imp/back_frames.bin", raw * 3, source="gfx/pokemon/geodude/back.2bpp",
                note="Original complete 48x48 rear frame reused unchanged by three native pose requests")
            put("imp/back_palettes.bin", pal * 2)
            put("imp/back_attrs.bin", bytes(36))
            preview(decode(raw, 48, 48), colors, PREVIEW / "imp_back.png")

    manifest = {"version": "v0.2.13", "operation": "Archived native asset restoration; no redrawing",
                "historical_sources": {"peon_class_packets": "2755365 (v0.2.6)",
                                       "boar_and_imp_pngs": "f73b2ec (v0.2.1)"},
                "restored_roles": ["base Peon", "Shaman", "Boar", "Imp"],
                "unchanged_classes": ["Warrior", "Warlock"],
                "dimensions": {"world": [16, 16], "front": [56, 56], "back": [48, 48]},
                "enemy_frames": 4, "hero_frames": 3, "records": records,
                "native_verification": "All four enemy frames exactly match all pixels in archived PNGs; profile row/column order matches; source packet hashes pinned",
                "runtime_verification": "Root must validate the exact assembled ROM; these are decoded native packets, not emulator screenshots"}
    PREVIEW.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (PREVIEW / "import_report.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"outputs": len(records), "enemy_frames_pixel_verified": 8,
                      "hero_front_profile_frames_verified": 3, "manifest": str(OUTPUT / "manifest.json")}))


if __name__ == "__main__":
    main()
