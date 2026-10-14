#!/usr/bin/env python3
"""Import complete supplied masters as sparse, native 24x24 static sprites.

No drawing, smoothing, palette-zero material pixels or enlarged 16px sources.
The supplied class-master reference sheet contains three complete silhouettes.
"""
from pathlib import Path
from collections import deque
import hashlib
import json
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_peon_approved_players_v0212 import adaptive_palettes, palette_errors

ROOT = Path(__file__).resolve().parents[1]
GFX = ROOT / "gfx/large_masters_v0213"
OUT = ROOT / "references/generated/large_masters_v0213"
ROLES = (("Shaman", "shaman_master", (7,), (15, 330, 330, 668)),
         ("Warrior", "warrior_trainer", (3, 4), (530, 334, 865, 665)),
         ("Warlock", "enemy_warlock", (1, 5), (1066, 336, 1324, 666)))


def isolate_source(source, box):
    """Remove border-connected sheet paper, then disconnected label fragments.

    Paper trapped inside the character's outline remains opaque, preserving
    white horns, blade highlights and eyes. No anatomy pixels are authored.
    """
    a = np.asarray(source.crop(box)).copy()
    rgb = a[:, :, :3].astype(np.int32)
    paper = ((rgb[:, :, 0] > 160) & (rgb[:, :, 1] > 140) &
             (rgb[:, :, 2] > 110) & ((rgb.max(2) - rgb.min(2)) < 65))
    marked = np.zeros(paper.shape, bool)
    h, w = paper.shape
    q = deque((y, x) for y in range(h) for x in range(w)
              if (y in (0, h - 1) or x in (0, w - 1)) and paper[y, x])
    while q:
        y, x = q.popleft()
        if marked[y, x] or not paper[y, x]:
            continue
        marked[y, x] = True
        q.extend((yy, xx) for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1))
                 if 0 <= yy < h and 0 <= xx < w and not marked[yy, xx])
    visible = ~marked
    visited, components = np.zeros(paper.shape, bool), []
    for y, x in zip(*np.nonzero(visible)):
        if visited[y, x]:
            continue
        component, q = [], deque(((y, x),))
        while q:
            yy, xx = q.popleft()
            if visited[yy, xx] or not visible[yy, xx]:
                continue
            visited[yy, xx] = True
            component.append((yy, xx))
            q.extend((yyy, xxx) for yyy in range(max(0, yy - 1), min(h, yy + 2))
                     for xxx in range(max(0, xx - 1), min(w, xx + 2)) if not visited[yyy, xxx])
        components.append(component)
    body = max(components, key=len)
    a[:, :, 3] = 0
    yy, xx = np.asarray(body).T
    a[yy, xx, 3] = 255
    return Image.fromarray(a)


def encode_tile(values):
    data = bytearray()
    for row in values:
        data.append(sum((int(v) & 1) << (7 - x) for x, v in enumerate(row)))
        data.append(sum(((int(v) >> 1) & 1) << (7 - x) for x, v in enumerate(row)))
    return data


def main():
    GFX.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    graphics = ['SECTION "Peon large class master graphics v0213", ROMX']
    facings, palette_lines, report = [], [], []
    for title, role, slots, source_box in ROLES:
        source = ROOT / "references/characters/class_masters/class_masters_crystal_style_sheet_reference.png"
        original = Image.open(source).convert("RGBA")
        isolated = isolate_source(original, source_box)
        isolated.save(OUT / (role + "_source_isolated.png"))
        alpha = isolated.getchannel("A")
        crop = alpha.getbbox()
        sprite = isolated.crop(crop)
        sprite.thumbnail((24, 24), Image.Resampling.NEAREST)
        canvas = Image.new("RGBA", (24, 24))
        canvas.alpha_composite(sprite, ((24 - sprite.width) // 2, 24 - sprite.height))
        rgba = np.asarray(canvas)
        palettes, _ = adaptive_palettes(rgba, max(2, len(slots)))
        if len(slots) == 1:
            palettes = [palettes[int(palette_errors(rgba, palettes).sum(0).argmin())]]
        # Faces occupy very few pixels. Keep their actual source green as an
        # opaque material, rather than letting more numerous armor/robe pixels
        # consume every color in the medoid fit. These colors are source pixels.
        green = ((rgba[:, :, 1].astype(int) > rgba[:, :, 0].astype(int) + 12) &
                 (rgba[:, :, 1].astype(int) > rgba[:, :, 2].astype(int) + 12) &
                 (rgba[:, :, 3] > 0))
        if role in ("warrior_trainer", "enemy_warlock") and green.any():
            green_colors = rgba[:, :, :3][green] >> 3
            center = green_colors.mean(0)
            material = tuple(map(int, green_colors[((green_colors - center) ** 2).sum(1).argmin()]))
            chosen = 1 if role == "warrior_trainer" else 0
            palettes[chosen][2] = material
        if role == "enemy_warlock":
            # OBJ1 is also the Warlock player's supplied robe/skin family.
            # Share it unchanged instead of recoloring the player in the hut.
            palettes[0] = [(31, 31, 31), (12, 17, 5), (16, 11, 17), (1, 1, 1)]
        selection = palette_errors(rgba, palettes).argmin(1)
        rgb = rgba[:, :, :3].astype(np.int32) >> 3
        visible = rgba[:, :, 3] > 0
        indexed = np.zeros((24, 24), np.uint8)
        decoded = np.zeros((24, 24, 4), np.uint8)
        entries, packet = [], bytearray()
        for n, (y, x) in enumerate(( (y, x) for y in range(0, 24, 8) for x in range(0, 24, 8))):
            p = int(selection[n])
            mask = visible[y:y + 8, x:x + 8]
            colors = np.asarray(palettes[p][1:])
            v = ((rgb[y:y + 8, x:x + 8, None, :] - colors) ** 2).sum(3).argmin(2) + 1
            v[~mask] = 0
            indexed[y:y + 8, x:x + 8] = v
            actual = np.asarray(palettes[p], np.uint8)[v] * 8
            decoded[y:y + 8, x:x + 8, :3] = actual
            decoded[y:y + 8, x:x + 8, 3] = mask * 255
            packet.extend(encode_tile(v))
            if mask.any():
                entries.append((y - 8, x - 4, slots[p], n))
        assert len(packet) == 9 * 16
        (GFX / (role + ".bin")).write_bytes(packet)
        canvas.save(OUT / (role + "_native.png"))
        Image.fromarray(decoded).save(OUT / (role + "_hardware.png"))
        Image.fromarray(decoded).resize((240, 240), Image.Resampling.NEAREST).save(OUT / (role + "_hardware_10x.png"))
        graphics.extend([f"PeonLarge{title}WorldV0213::", f'\tINCBIN "gfx/large_masters_v0213/{role}.bin"', f"\tassert @ - PeonLarge{title}WorldV0213 == 9 * TILE_SIZE"])
        facings.extend([f"PeonLarge{title}FacingV0213:", f"\tdb {len(entries)}"])
        facings.extend(f"\tdb {y:2}, {x:2}, {p}, ${n:02x}" for y, x, p, n in entries)
        for palette, slot in zip(palettes, slots):
            palette_lines.extend([f"PeonLargeMasterPalette{slot}V0213:", "\tRGB " + ", ".join(str(v) for c in palette for v in c)])
        report.append({"role": role, "source": str(source.relative_to(ROOT)), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "source_dimensions": original.size, "source_crop": source_box, "alpha_crop_in_source_crop": crop, "background_isolation": "border-connected bright neutral sheet paper removed; largest eight-connected body retained; interior whites preserved", "import_kind": "lossy raster reference conversion, not recovery of a native pixel grid", "native_dimensions": [24, 24], "silhouette_dimensions": sprite.size, "resampling": "NEAREST", "oam_objects": len(entries), "palette_slots": slots, "rgb555_palettes": palettes, "alpha_preserved_after_native_resize": bool(np.array_equal(decoded[:, :, 3] > 0, visible))})
    (GFX / "graphics.asm").write_text("\n".join(graphics) + "\n")
    (GFX / "facings.asm").write_text("\n".join(facings) + "\n")
    (GFX / "palettes.asm").write_text("\n".join(palette_lines) + "\n")
    (OUT / "manifest.json").write_text(json.dumps({"actors": report, "source_pngs_untouched": True, "saved_record_layout_unchanged": True}, indent=2) + "\n")
    print(json.dumps({"oam_counts": [r["oam_objects"] for r in report], "total": sum(r["oam_objects"] for r in report)}))


if __name__ == "__main__":
    main()
