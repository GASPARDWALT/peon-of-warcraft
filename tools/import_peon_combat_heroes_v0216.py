#!/usr/bin/env python3
"""Fit complete approved hero bodies to native battle-picture envelopes.

This is an explicitly lossy raster import for Warrior/Warlock, and an indexed
native-packet normalization for the restored Base/Shaman. No new anatomy,
texture, replacement equipment, or interpolated pixels are generated. Source
files and their original palettes remain untouched.
"""
from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from build_peon_user_battle_v0211 import encode
from import_peon_approved_players_v0212 import (
    ALPHA_THRESHOLD, CROPS, SOURCE, SOURCES,
)
from import_peon_native_actors_v0213 import decode, HERO_PALETTE, palette_bytes

ROOT = Path(__file__).resolve().parents[1]
GFX = ROOT / "gfx/combat_heroes_v0216"
OUT = ROOT / "references/generated/combat_heroes_v0216"
PAPER = (31, 29, 23)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def json_out(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def fit_complete(image, envelope):
    """Nearest-sample a full source rectangle, with a shared bottom baseline."""
    scale = min(envelope / image.width, envelope / image.height)
    dims = tuple(min(envelope, max(1, round(x * scale))) for x in image.size)
    sampled = image.resize(dims, Image.Resampling.NEAREST)
    result = Image.new(image.mode, (envelope, envelope))
    offset = ((envelope - dims[0]) // 2, envelope - dims[1])
    result.paste(sampled, offset)
    return result, {"source_rect": [0, 0, image.width, image.height],
                    "sampled_dimensions": list(dims), "offset": list(offset),
                    "resampling": "nearest; complete source rectangle; no filtering"}


def rgba_indexed(indexed, colors):
    rgb = np.asarray(colors, dtype=np.uint8)
    rgb = (rgb << 3) | (rgb >> 2)
    indices = np.asarray(indexed)
    return Image.fromarray(np.dstack((rgb[indices], np.where(indices != 0, 255, 0))).astype("uint8"))


def native_frames(role, view, records):
    size = 48 if view == "back" else 56
    folder = ROOT / "gfx" / ("native_actor_restore_v0213/peon" if role == "base"
                              else "shaman_proportions_v0214")
    source = folder / f"{view}_frames.bin"
    packet = source.read_bytes()
    stride = size * size // 4
    assert len(packet) == 3 * stride
    originals = [decode(packet[p * stride:(p + 1) * stride], size, size) for p in range(3)]
    boxes = [frame.getbbox() for frame in originals]
    # One transform for the entire animation keeps the head/body ratio and
    # native inter-pose offsets. In particular, never enlarge the skull alone.
    union = (min(b[0] for b in boxes), min(b[1] for b in boxes),
             max(b[2] for b in boxes), max(b[3] for b in boxes))
    results, transforms = [], []
    for phase, original in enumerate(originals):
        result, transform = fit_complete(original.crop(union), size)
        assert set(result.get_flattened_data()) <= set(original.get_flattened_data())
        results.append(result)
        transforms.append(transform)
        records.append({"role": role, "view": view, "pose": phase,
                        "source": rel(source), "source_sha256": sha(packet),
                        "before_bbox": list(boxes[phase]), "after_bbox": list(result.getbbox()),
                        "shared_pose_crop": list(union), "transform": transform,
                        "head_body_ratio_preserved": True,
                        "new_drawing_detail": False})
    return originals, results, [rgba_indexed(frame, HERO_PALETTE) for frame in results]


def raster_frames(role, view, records):
    filename, expected = SOURCES[role]
    path = SOURCE / filename
    assert sha(path.read_bytes()) == expected, path
    image = Image.open(path).convert("RGBA")
    bounds = CROPS[role]["combat_" + view]
    crop = np.asarray(image.crop(bounds)).copy()
    crop[:, :, 3] = np.where(crop[:, :, 3] >= ALPHA_THRESHOLD, 255, 0)
    crop[crop[:, :, 3] == 0] = 0
    native, transform = fit_complete(Image.fromarray(crop), 48 if view == "back" else 56)
    before_path = ROOT / f"references/generated/approved_player_import_v0212/sprites/{role}/combat_{view}.png"
    before = Image.open(before_path).convert("RGBA")
    for phase in range(3):
        records.append({"role": role, "view": view, "pose": phase,
                        "source": rel(path), "source_sha256": expected,
                        "source_crop_bounds_exclusive": bounds,
                        "before_bbox": list(before.getbbox()), "after_bbox": list(native.getbbox()),
                        "transform": transform, "alpha_threshold": ALPHA_THRESHOLD,
                        "source_native_pixel_grid_recovered": False,
                        "source_color_detail_requantized": True,
                        "new_drawing_detail": False,
                        "unique_authored_source_poses": 1})
    return [before] * 3, [native] * 3


def material_family(rgb):
    """Protect recognizable skin, robe, leather and steel during quantization."""
    r, g, b = np.moveaxis(rgb, -1, 0)
    family = np.zeros(r.shape, dtype="uint8")
    family[(g > r + 1) & (g > b + 1)] = 1
    family[(r > g + 2) & (b > g + 1)] = 2
    family[(r > g + 2) & (g > b + 2)] = 3
    family[(rgb.max(-1) - rgb.min(-1) <= 3) & (rgb.sum(-1) > 24)] = 4
    return family


def quantize_region(rgb, palette, start):
    distance = ((rgb[:, :, None] - palette[None, None, start:]) ** 2).sum(3)
    source_family = material_family(rgb)
    target_family = material_family(palette[start:])
    # Dark outline is always legal. A purple pixel must not become green skin
    # merely because the two RGB vectors happen to be close.
    mismatch = ((source_family[:, :, None] != target_family[None, None])
                & (source_family[:, :, None] != 0)
                & (palette[start:].sum(1)[None, None] > 12))
    distance = distance + mismatch * 500
    # The source mohawk/ink is neutral: do not tint those near-black pixels
    # purple or leather merely to reduce numeric RGB error.
    neutral_dark = ((rgb.max(2) - rgb.min(2) <= 3) & (rgb.sum(2) <= 30))
    distance += neutral_dark[:, :, None] * (target_family[None, None] != 0) * 500
    return distance.argmin(2) + start


def source_palettes(rgba, count, role):
    rgb = rgba[:, :, :3].astype("int32") >> 3
    visible = rgba[:, :, 3] != 0
    colors, counts = np.unique(rgb[visible], axis=0, return_counts=True)
    dark = tuple(map(int, colors[colors.sum(1).argmin()]))
    selected = colors.sum(1) > max(10, sum(dark) + 6)
    values, weights = colors[selected].astype(float), counts[selected]
    centers = [values[weights.argmax()]]
    while len(centers) < min(12, len(values)):
        distance = ((values[:, None] - np.asarray(centers)[None]) ** 2).sum(2).min(1)
        centers.append(values[(distance * np.sqrt(weights)).argmax()])
    centers = np.asarray(centers)
    for _ in range(20):
        assignments = ((values[:, None] - centers[None]) ** 2).sum(2).argmin(1)
        for n in range(len(centers)):
            mask = assignments == n
            if mask.any():
                centers[n] = np.average(values[mask], weights=weights[mask], axis=0)
    medoids = list(dict.fromkeys(tuple(map(int, values[((values - center) ** 2).sum(1).argmin()]))
                                 for center in centers))
    def nearest(anchor):
        return tuple(map(int, colors[((colors - np.asarray(anchor)) ** 2).sum(1).argmin()]))
    # Keep the approved materials recognizable even when an area-weighted
    # fit could save average error by deleting the axe metal or green hands.
    # Every opaque entry is an actual RGB555 color of this source crop.
    if role == "warrior":
        primary = [(31, 31, 31), nearest((16, 21, 9)), nearest((15, 8, 2)), dark]
        secondary = [(31, 31, 31), nearest((8, 14, 6)), nearest((25, 24, 25)), dark]
    else:
        primary = [(31, 31, 31), nearest((19, 11, 17)), nearest((15, 20, 8)), dark]
        secondary = [(31, 31, 31), nearest((10, 5, 9)), nearest((16, 9, 3)), dark]
    options = [primary, secondary]
    if count > 2:
        options.extend([[(31, 31, 31), a, b, dark] for a, b in combinations(medoids, 2)])
    errors = []
    for y in range(0, len(rgba), 8):
        for x in range(0, len(rgba), 8):
            region, mask = rgb[y:y + 8, x:x + 8], visible[y:y + 8, x:x + 8]
            source_family = material_family(region)
            tile_errors = []
            for option in options:
                palette = np.asarray(option, dtype="int32")
                indices = quantize_region(region, palette, 1)
                hardware = palette[indices]
                error = ((region[mask] - hardware[mask]) ** 2).sum()
                hwfamily = material_family(hardware)
                error += 500 * np.count_nonzero(mask & (source_family != hwfamily)
                                                & (source_family != 0)
                                                & (hardware.sum(2) > 12))
                # Preserve source creases, straps, facial marks and bright
                # edges; minimizing mean color alone erases these details.
                for dy, dx in ((1, 0), (0, 1)):
                    sl = (slice(None, -dy or None), slice(None, -dx or None))
                    sr = (slice(dy, None), slice(dx, None))
                    both = mask[sl] & mask[sr]
                    gradient = ((region[sl] - region[sr]) ** 2).sum(2)
                    vanished = (indices[sl] == indices[sr]) & (gradient >= 36) & both
                    error += 8 * gradient[vanished].sum()
                tile_errors.append(float(error))
            errors.append(tile_errors)
    errors = np.asarray(errors)
    selected = [0, 1]
    while len(selected) < count:
        scores = np.minimum(errors, errors[:, selected].min(1)[:, None]).sum(0)
        scores[selected] = np.inf
        selected.append(int(scores.argmin()))
    palettes = [options[n] for n in selected]
    return palettes, errors[:, selected].argmin(1)


def emit(role, view, frames, native_indexed=None):
    size = frames[0].width
    slots = [2, 4, 6, 7] if view == "profile" else [1, 5] if view == "front" else [0, 6]
    source = np.asarray(frames[0])
    if native_indexed is not None:
        palettes = [[PAPER if view == "profile" else (31, 31, 31), *HERO_PALETTE[1:]]] * len(slots)
        indices = native_indexed
        choices = np.zeros((size // 8) ** 2, dtype="uint8")
        opaque_zero = [False] * len(slots)
    else:
        # BG6 used to be frozen to the retired simultaneous Imp. The native
        # roster now has one active fighter; HUD mana/type use BG3/BG4, not6.
        # Both existing actor palettes may retain colors from the source.
        palettes, choices = source_palettes(source, len(slots), role)
        opaque_zero = [tuple(p[0]) != (31, 31, 31) for p in palettes]
        palettes = [[p[0] if opaque_zero[n] else PAPER if view == "profile" else (31, 31, 31), *p[1:]]
                    for n, p in enumerate(palettes)]
        indices = []
        for frame in frames:
            rgba = np.asarray(frame)
            indexed = np.zeros((size, size), dtype="uint8")
            for number, choice in enumerate(choices):
                y, x = (number // (size // 8)) * 8, (number % (size // 8)) * 8
                region = rgba[y:y + 8, x:x + 8]
                visible = region[:, :, 3] != 0
                palette = np.asarray(palettes[int(choice)], dtype="int32")
                rgb = region[:, :, :3].astype("int32") >> 3
                start = 0 if opaque_zero[int(choice)] else 1
                if start == 0:
                    assert visible.all(), "Opaque material color0 must never paint an alpha hole"
                pixels = quantize_region(rgb, palette, start)
                pixels[~visible] = 0
                indexed[y:y + 8, x:x + 8] = pixels
            indices.append(Image.fromarray(indexed))
    packet = b"".join(encode(np.asarray(frame), column_major=view != "profile") for frame in indices)
    stride = size * size // 4
    assert len(packet) == 3 * stride
    attrs = bytes(slots[int(choice)] for choice in choices)
    palette_packet = b"".join(palette_bytes(p) for p in palettes)
    folder = GFX / role / view
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "frames.bin").write_bytes(packet)
    (folder / "attrs.bin").write_bytes(attrs)
    (folder / "palettes.bin").write_bytes(palette_packet)
    previews = []
    for phase, (indexed, frame) in enumerate(zip(indices, frames)):
        decoded = decode(packet[phase * stride:(phase + 1) * stride], size, size,
                         column_major=view != "profile")
        assert decoded.tobytes() == indexed.tobytes()
        pixels = np.zeros((size, size, 4), dtype="uint8")
        for number, choice in enumerate(choices):
            y, x = (number // (size // 8)) * 8, (number % (size // 8)) * 8
            palette = np.asarray(palettes[int(choice)], dtype="uint8")
            colors = (palette << 3) | (palette >> 2)
            pixels[y:y + 8, x:x + 8, :3] = colors[np.asarray(indexed)[y:y + 8, x:x + 8]]
        pixels[:, :, 3] = np.asarray(frame)[:, :, 3]
        preview = Image.fromarray(pixels)
        previews.append(preview)
        assert np.array_equal(pixels[:, :, 3], np.asarray(frame)[:, :, 3])
        target = OUT / role / view
        target.mkdir(parents=True, exist_ok=True)
        frame.save(target / f"source_native_{phase}.png")
        preview.save(target / f"hardware_{phase}.png")
        preview.save(folder / f"pose_{phase}.png")
        preview.resize((size * 6, size * 6), Image.Resampling.NEAREST).save(target / f"hardware_{phase}_6x.png")
    return previews, {"role": role, "view": view, "slots": slots,
                       "palettes_rgb555": palettes, "palette_zero_opaque": opaque_zero,
                       "native_size": [size, size], "frames": 3,
                       "tile_order": "row-major" if view == "profile" else "column-major",
                       "attr_order": "row-major; shared across all three poses",
                       "bytes_per_frame": stride, "alpha_preserved": True,
                       "hardware_opaque_colors": len(np.unique(np.concatenate([
                           np.asarray(im)[:, :, :3][np.asarray(im)[:, :, 3] != 0]
                           for im in previews]), axis=0)),
                       "outputs": {rel(folder / n): sha((folder / n).read_bytes())
                                   for n in ("frames.bin", "attrs.bin", "palettes.bin",
                                             "pose_0.png", "pose_1.png", "pose_2.png")}}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source_hashes, records, outputs, gallery = {}, [], [], {}
    for role in ("base", "shaman", "warrior", "warlock"):
        for view in ("back", "front"):
            if role in ("base", "shaman"):
                before, indexed, frames = native_frames(role, view, records)
                before = [rgba_indexed(frame, HERO_PALETTE) for frame in before]
            else:
                before, frames = raster_frames(role, view, records)
                before = [Image.open(ROOT / f"references/generated/approved_player_import_v0212/comparisons/{role}/{view}_hardware_rgba.png").convert("RGBA")] * 3
                indexed = None
            previews, report = emit(role, view, frames, indexed)
            for phase in range(3):
                record = next(record for record in records if record["role"] == role
                              and record["view"] == view and record["pose"] == phase)
                for label, im in (("before", before[phase]), ("after", previews[phase])):
                    pixels = np.asarray(im)
                    visible = pixels[:, :, 3] != 0
                    record[label + "_opaque_pixels"] = int(visible.sum())
                    families = material_family(pixels[:, :, :3].astype("int32") >> 3)
                    record[label + "_green_skin_pixels"] = int(np.count_nonzero(visible & (families == 1)))
            outputs.append(report)
            gallery[role, view] = (before, previews)
            if view == "front":
                _, report = emit(role, "profile", frames, indexed)
                outputs.append(report)
    for record in records:
        source_hashes[record["source"]] = record["source_sha256"]
    assert all(sha((ROOT / path).read_bytes()) == expected for path, expected in source_hashes.items())
    # Static packet comparison, deliberately separate from runtime captures.
    sheet = Image.new("RGB", (6 * 58, 4 * 126), "white")
    draw = ImageDraw.Draw(sheet)
    for row, role in enumerate(("base", "shaman", "warrior", "warlock")):
        draw.text((0, row * 126), role + " : before / after (three complete poses)", fill="black")
        for view, offset in (("back", 14), ("front", 68)):
            before, after = gallery[role, view]
            for phase in range(3):
                for delta, images in ((0, before), (3, after)):
                    image = images[phase]
                    sheet.paste(image, ((phase + delta) * 58, row * 126 + offset), image)
    sheet.save(OUT / "static_before_after.png")
    sheet.resize((sheet.width * 3, sheet.height * 3), Image.Resampling.NEAREST).save(OUT / "static_before_after_3x.png")
    manifest = {"version": "v0.2.16", "status": "PASS",
                "operation": "Complete-body native envelope normalization; approved raster detail reimport",
                "source_hashes": source_hashes, "original_sources_unchanged": True,
                "replacement_drawing_generated": False, "native_grid_recovery_claimed": False,
                "base_shaman": "All authored indexed native poses retained; one shared whole-body transform per view; original colors unchanged",
                "warrior_warlock": "Original high-resolution approved crops sampled again at maximum native coverage; both existing actor palettes fitted to source colors",
                "animations": "Base/Shaman retain three authored poses; Warrior/Warlock retain one supplied pose repeated in the three legacy slots",
                "hardware_contract": {"back": [48, 48], "front": [56, 56], "profile": [56, 56],
                                      "back_tiles": 36, "front_tiles": 49,
                                      "battle_hud_palettes_unchanged": [2, 3, 4, 7]},
                "poses": records, "packets": outputs,
                "runtime_tested": False, "static_gallery": rel(OUT / "static_before_after.png")}
    json_out(GFX / "manifest.json", manifest)
    json_out(OUT / "import_report.json", manifest)
    print(json.dumps({"status": "PASS", "pose_records": len(records), "packets": len(outputs),
                      "report": rel(OUT / "import_report.json")}))


if __name__ == "__main__":
    main()
