#!/usr/bin/env python3
"""Import richer WORLD views directly at24px; never use combat views.

The original artwork remains read-only. This is a lossy nearest-sampled raster
import, not newly authored pixel art and not recovery of a native pixel grid.
NPC source colors receive a material/outline-aware fit to existing palettes.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import import_peon_world_actors_v0215 as old
from import_peon_approved_players_v0212 import SOURCES, CROPS, ALPHA_THRESHOLD

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "gfx/world_actors_v0216"
REVIEW = ROOT / "references/generated/world_detail_v0216"
RASTERS = ROOT / "references/generated/peon_sprite_redesign_v030/originals"
DIRECTIONS = ("front", "back", "left", "right")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def world_crop(role, direction):
    path = RASTERS / SOURCES[role][0]
    assert sha(path.read_bytes()) == SOURCES[role][1]
    original = Image.open(path).convert("RGBA")
    bounds = CROPS[role]["world_" + direction]
    crop = np.array(original.crop(bounds))
    visible = crop[..., 3] >= ALPHA_THRESHOLD
    crop[..., 3] = np.where(visible, 255, 0)
    crop[~visible] = 0
    source = Image.fromarray(crop, "RGBA")
    scale = min(22 / source.width, 22 / source.height)
    fitted = (max(1, round(source.width * scale)), max(1, round(source.height * scale)))
    offset = ((24 - fitted[0]) // 2, 24 - fitted[1] - 1)
    frame = Image.new("RGBA", (24, 24))
    frame.paste(source.resize(fitted, Image.Resampling.NEAREST), offset)
    return source, frame, {
        "source": rel(path), "source_sha256": sha(path.read_bytes()),
        "source_canvas": list(original.size), "source_pose": "world_" + direction,
        "crop_bounds_exclusive": bounds, "crop_dimensions": list(source.size),
        "alpha_threshold": ALPHA_THRESHOLD, "native_dimensions": [24, 24],
        "fitted_dimensions": list(fitted), "offset": list(offset),
        "resampling": "nearest", "combat_pose_used": False,
        "exact_native_grid_recovery": False, "new_anatomy_authored": False,
    }


def fit_materials(source, role, candidates, default, hero=False):
    """Keep only actual darkest source marks as ink, rather than dark fills.

    Each sprite uses existing three-opaque-color OBJ palettes. Source material
    hue and its relative luminance choose those colors; alpha/geometry are exact.
    A dark green source pixel remains skin instead of becoming black solely
    because the hardware green is brighter than its dim raster counterpart.
    """
    pixels = np.array(source)
    rgb = pixels[..., :3].astype(np.float64) / 255
    opaque = pixels[..., 3] != 0
    luma = rgb @ np.array([0.2126, 0.7152, 0.0722])
    unique_luma = np.unique(luma[opaque])
    # Supplied NPCs have an eight-color indexed-like raster. Preserve their
    # darkest outline plus an existing deep-shadow color when it is also dark;
    # these source marks retain faces/equipment instead of flattening all fills.
    if hero:
        # Source-black outlines and the original charcoal crest remain ink.
        # Unlike a fixed pixel percentage, these actual source-color tests do
        # not force a bright eye/tusk/equipment pixel into an outline cluster.
        chroma = rgb.max(2) - rgb.min(2)
        source_black = (rgb.max(2) <= 0.08)
        source_charcoal = (chroma <= 0.08) & (luma <= 0.28)
        ink = opaque & (source_black | source_charcoal)
    else:
        darkest = unique_luma[0]
        if len(unique_luma) > 1 and unique_luma[1] <= 0.18:
            darkest = unique_luma[1]
        ink = opaque & (luma <= darkest + 1e-8)
    values = np.zeros((24, 24), dtype=np.uint8)
    attrs = []
    for y in range(0, 24, 8):
        for x in range(0, 24, 8):
            colors = rgb[y:y + 8, x:x + 8]
            visible = opaque[y:y + 8, x:x + 8]
            local_ink = ink[y:y + 8, x:x + 8]
            nonink = visible & ~local_ink
            options = {}
            # Use source hue independent of its very dim atlas exposure.
            unit = colors / np.maximum(colors.max(2, keepdims=True), 1 / 255)
            for number in candidates:
                palette = np.array(old.PALETTES[number][1:3], dtype=np.float64) / 31
                pal_unit = palette / np.maximum(palette.max(1, keepdims=True), 1 / 31)
                distances = ((unit[..., None, :] - pal_unit[None, None, :, :]) ** 2).sum(3)
                distances += 0.12 * ((colors[..., None, :] - palette[None, None, :, :]) ** 2).sum(3)
                selected = distances.argmin(2).astype(np.uint8) + 1
                options[number] = (float(distances.min(2)[nonink].sum()), selected)
            r, g, b = colors[..., 0], colors[..., 1], colors[..., 2]
            source_skin = (g >= r) & (g > b * 1.10) & (g >= 0.10) & nonink
            if 2 in candidates and source_skin.any():
                # Orc atlas exposure is dim and olive. Brightness must not
                # cause its real green source material to choose brown/metal.
                selected_palette = 2
            else:
                selected_palette = min(candidates, key=lambda p: (options[p][0], p != default, p))
            indices = options[selected_palette][1].copy()
            # Existing palette2 explicitly distinguishes Orc skin and leather.
            if selected_palette == 2:
                r, g, b = colors[..., 0], colors[..., 1], colors[..., 2]
                skin = (g >= r) & (g > b * 1.10)
                indices[skin & nonink] = 2
                indices[(r > g * 1.13) & nonink] = 1
            indices[local_ink] = 3
            indices[~visible] = 0
            values[y:y + 8, x:x + 8] = indices
            attrs.append(selected_palette)
    image = Image.fromarray(values, "L")
    rendered = old.rgba_from_attrs(image, bytes(attrs))
    assert np.array_equal(np.asarray(rendered.getchannel("A")), pixels[..., 3])
    return image, rendered, bytes(attrs), {
        "source_outline_pixels": int(ink.sum()),
        "native_ink_pixels": int(np.count_nonzero(values == 3)),
        "native_opaque_pixels": int(opaque.sum()),
        "outline_fraction": round(float(ink.sum() / max(opaque.sum(), 1)), 5),
    }


def comparison(role, source_frames, prior_frames, new_frames):
    # Explicitly static artwork review: not a screenshot or gameplay proof.
    sheet = Image.new("RGB", (4 * 192, 168), (30, 29, 27))
    draw = ImageDraw.Draw(sheet)
    draw.text((4, 3), role + " WORLD: source / v15 / v16 (static packet decode)", fill="white")
    for d, direction in enumerate(DIRECTIONS):
        x = d * 192
        draw.text((x + 4, 20), direction, fill="white")
        for j, frame in enumerate((source_frames[d], prior_frames[d * 3], new_frames[d * 3])):
            factor = min(56 / frame.width, 112 / frame.height)
            thumb = frame.resize((max(1, round(frame.width * factor)), max(1, round(frame.height * factor))), Image.Resampling.NEAREST)
            sheet.paste(thumb, (x + j * 64 + (64 - thumb.width) // 2, 43 + (112 - thumb.height) // 2), thumb)
            draw.text((x + j * 64 + 4, 151), ("source", "v15", "v16")[j], fill="white")
    sheet.save(REVIEW / role / "comparison.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    prior = json.loads((ROOT / "gfx/world_actors_v0215/manifest.json").read_text())
    preserved = {rel(p): sha(p.read_bytes()) for p in (ROOT / "references/characters").rglob("*.png")}
    preserved.update({rel(RASTERS / filename): digest for filename, digest in SOURCES.values()})
    roles = copy.deepcopy(prior["roles"])
    for role, entry in roles.items():
        folder = OUT / role
        review = REVIEW / role
        folder.mkdir(exist_ok=True)
        review.mkdir(exist_ok=True)
        old_packet = (ROOT / entry["output_packet"]).read_bytes()
        prior_attrs = (ROOT / "gfx/world_actors_v0215" / role / "attrs.bin").read_bytes()
        prior_indexed = [old.decode(old_packet[i * 144:(i + 1) * 144], 24) for i in range(12)]
        prior_frames = [old.rgba_from_attrs(frame, prior_attrs[i * 9:(i + 1) * 9]) for i, frame in enumerate(prior_indexed)]
        source_crops = []
        provenance = []
        frames = []
        rendered = []
        attrs = []
        metrics = []
        if role in SOURCES:
            for direction in DIRECTIONS:
                crop, native, record = world_crop(role, direction)
                source_crops.append(crop)
                provenance.append(record)
                crop.save(review / f"world_{direction}_source_crop.png")
                native.save(review / f"world_{direction}_sampled_24.png")
                for pose in range(3):
                    moving = native
                    # The approved artwork supplies four stills, no walk limbs.
                    # A1px full-body bob preserves those exact source pixels.
                    if role in ("base", "shaman") and pose == 1:
                        moving = Image.new("RGBA", (24, 24))
                        moving.paste(native, (0, -1))
                        assert moving.getchannel("A").getbbox()[1] >= 0
                        assert np.count_nonzero(np.asarray(moving.getchannel("A"))) == np.count_nonzero(np.asarray(native.getchannel("A")))
                    palette = 1 if role == "warlock" else 2
                    frame, shown, attr, metric = fit_materials(moving, role, (palette,), palette, hero=True)
                    frames.append(frame); rendered.append(shown); attrs.append(attr); metrics.append(metric)
            entry.update({
                "baseline_source_packet": entry["source_packet"],
                "baseline_source_sha256": entry["source_sha256"],
                "source_packet": provenance[0]["source"],
                "source_note": "Approved four WORLD raster views reimported directly at24px; combat poses never used; no16px intermediate",
                "source_kind": "approved_world_raster_direct24",
                "source_world_crops": provenance,
                "source_png": provenance[0]["source"],
                "source_sha256": provenance[0]["source_sha256"],
                "source_artwork_manifest": "references/generated/approved_player_import_v0212/manifest.json",
                "native_input_layout": "four_world_stills_direction_major",
                "animation_note": "Base/Shaman full-body1px bob on pose1 only; no new anatomy or walk limbs" if role in ("base", "shaman") else "Four approved stills repeated for three gait addresses, same policy asv15",
                "detail_source": "Higher-resolution dedicated WORLD silhouettes, not enlarging the prior16px packet",
            })
        elif entry.get("source_color_recovery_from_png"):
            if entry.get("source_png"):
                source_crops = [Image.open(ROOT / entry["source_png"]).convert("RGBA") for _ in DIRECTIONS]
            else:
                source_crops = [Image.open(ROOT / f["source"]).convert("RGBA") for f in entry["source_png_frames"]]
            for source in source_crops:
                assert source.size == (16, 16)
                native = source.resize((24, 24), Image.Resampling.NEAREST)
                candidates = old.family_palettes(role)
                for _ in range(3):
                    frame, shown, attr, metric = fit_materials(native, role, candidates, entry["palette_index"])
                    frames.append(frame); rendered.append(shown); attrs.append(attr); metrics.append(metric)
            entry.update({"source_note_v0216": "Exact supplied WORLD silhouette and existing explicit whole-body fallback; source-darkest outline separated from dim material fills", "detail_source": "Source16px materials recovered; no invented finer anatomy"})
        else:
            # Missing supplied art and unbound roster packets retain their exact
            # v15bytes. Never redraw Crawler/Kolkar/sleeper as schematic substitutes.
            frames = prior_indexed
            rendered = prior_frames
            attrs = [prior_attrs[i * 9:(i + 1) * 9] for i in range(12)]
            source_crops = [prior_frames[i * 3] for i in range(4)]
            metrics = [{"retained_v15_bytes": True} for _ in range(12)]
            entry["retained_v15_bytes"] = True
            entry["historical_origin"] = {
                "path": entry["source_packet"],
                "sha256": entry["source_sha256"],
                "available": (ROOT / entry["source_packet"]).is_file(),
                "verified_for_this_import": False,
            }
            entry["source_packet"] = f"gfx/world_actors_v0215/{role}/overworld.bin"
            entry["source_sha256"] = sha(old_packet)
            entry["native_input_layout"] = "retained_direction_major_24px"
        packet = b"".join(old.encode(frame) for frame in frames)
        masks = [old.active_mask(frame) for frame in frames]
        mask_data = b"".join(mask.to_bytes(2, "little") for mask in masks)
        attr_data = b"".join(attrs)
        assert len(packet) == 1728 and len(mask_data) == 24 and len(attr_data) == 108
        (folder / "overworld.bin").write_bytes(packet)
        (folder / "masks.bin").write_bytes(mask_data)
        (folder / "attrs.bin").write_bytes(attr_data)
        strip = Image.new("RGBA", (24 * 4, 24 * 3))
        for i, shown in enumerate(rendered):
            strip.paste(shown, ((i // 3) * 24, (i % 3) * 24))
            shown.save(review / f"world_{DIRECTIONS[i // 3]}_pose{i % 3}_native.png")
            shown.save(review / f"world_{DIRECTIONS[i // 3]}_{i % 3}_24x24.png")
        strip.save(folder / "overworld.png")
        comparison(role, source_crops, prior_frames, rendered)
        entry.update({
            "output_packet": rel(folder / "overworld.bin"), "output_sha256": sha(packet),
            "mask_sha256": sha(mask_data), "attrs_sha256": sha(attr_data),
            "uses_palette_indices": sorted(set(attr_data)),
            "adds_new_pixel_detail": role in SOURCES,
            "detail_is_recovered_from_approved_world_source": role in SOURCES,
            "source_pixels_invented": False,
            "combat_pose_used": False,
            "frame_records": [dict(entry["frame_records"][i],
                opaque_pixels_after=int(np.count_nonzero(np.asarray(frame))),
                opaque_bounds_after=list(rendered[i].getbbox()), mask=masks[i],
                oam_entries=masks[i].bit_count(),
                oam_per8px_row=[sum(bool(masks[i] & (1 << cell)) for cell in range(row * 3, row * 3 + 3)) for row in range(3)],
                native_decode_exact=True, indexed_pixels_are_nearest_source=False,
                per_tile_palette_ids=list(attrs[i]), color_fit_metrics=metrics[i],
                source_byte_offset=(i * 144 if entry.get("retained_v15_bytes") else
                    None if role in SOURCES else entry["frame_records"][i].get("source_byte_offset")),
                rgb555_error_after=None,
                alpha_is_nearest_source=True)
                for i, frame in enumerate(frames)],
        })
    # Keep the established binding ABI and exported symbol names. Only native
    # packet paths change; all rendering, movement/collision and palettes stay.
    (OUT / "graphics.asm").write_text((ROOT / "gfx/world_actors_v0215/graphics.asm").read_text().replace("gfx/world_actors_v0215/", "gfx/world_actors_v0216/").replace("World-only24px source-derived packets.", "World-only24px detail imports from dedicated WORLD views."))
    (OUT / "bindings.asm").write_text((ROOT / "gfx/world_actors_v0215/bindings.asm").read_text())
    report = dict(prior, version="v0.2.16", roles=roles,
        method="Dedicated approved WORLD rasters imported directly at24px for4heroes; outline/material-aware existing-palette fitting for suppliedNPC WORLD PNGs",
        new_detail_generated=False, new_anatomy_authored=False,
        source_hero_detail_recovered=True, combat_poses_used=False,
        palettes_changed=False, battle_sprites_unchanged=True,
        runtime_verification="Static decoded native packets only; root must verify exact compiled ROM",
        source_files_sha256=preserved)
    for p in (OUT / "manifest.json", REVIEW / "import_report.json"):
        p.write_text(json.dumps(report, indent=2) + "\n")
    assert all(sha((ROOT / path).read_bytes()) == digest for path, digest in preserved.items())
    (REVIEW / "source_png_hashes.json").write_text(json.dumps({"source_files": preserved, "source_files_count": len(preserved), "all_source_sha256_identical_before_after_import": True}, indent=2) + "\n")
    # Fourhero static overview at native4x for visual review.
    overview = Image.new("RGB", (768, 168 * 4), (30, 29, 27))
    for row, role in enumerate(("base", "shaman", "warrior", "warlock")):
        overview.paste(Image.open(REVIEW / role / "comparison.png"), (0, row * 168))
    overview.save(REVIEW / "hero_world_comparison.png")
    print(json.dumps({"roles": len(roles), "frames": len(roles) * 12, "source_files_unchanged": len(preserved), "hero_review": rel(REVIEW / "hero_world_comparison.png")}, indent=2))


if __name__ == "__main__":
    main()
