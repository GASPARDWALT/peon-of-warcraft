#!/usr/bin/env python3
"""Derive larger world-only actor packets from their current native pixels.

This importer does not draw anatomy or equipment and does not alter a source.
Heroes retain their native indices; supplied NPC PNGs recover their source
colors through per8px tile palette fitting. Both use nearest sampling to24px.
It encodes12 direction-major frames for a streamed nine-tile renderer, while
explicitly retaining existing damaged-crop fallbacks and historical actors.
Battle packets, map props, palettes, master bodies and gameplay are untouched.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from build_peon_user_world_v0211 import BINDINGS, DIRECTIONS, WORLD_PALETTES


ROOT = Path(__file__).resolve().parents[1]
GFX = ROOT / "gfx/world_actors_v0215"
REVIEW = ROOT / "references/generated/world_actors_v0215"
OLD_NPC_MANIFEST = ROOT / "gfx/user_world_v0211/manifest.json"
FRAME_SIZE = 24
FRAME_BYTES = 9 * 16
PALETTES = [list(palette) for palette in WORLD_PALETTES]
# Exact ordinary-world palette2 after the established restored-hero hook.
PALETTES[2] = [(31, 31, 31), (18, 11, 6), (15, 22, 8), (1, 1, 1)]
OLD_PALETTES = [list(palette) for palette in PALETTES]
# The integration owns this source-derived replacement of the brown Imp family.
PALETTES[7] = [(31, 31, 31), (31, 25, 7), (27, 5, 3), (2, 1, 1)]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def decode(data: bytes, width: int) -> Image.Image:
    assert len(data) == (width // 8) ** 2 * 16
    values = np.zeros((width, width), dtype="uint8")
    for tile in range((width // 8) ** 2):
        y, x = divmod(tile, width // 8)
        source = data[tile * 16:(tile + 1) * 16]
        for row in range(8):
            for column in range(8):
                shift = 7 - column
                values[y * 8 + row, x * 8 + column] = (
                    ((source[row * 2] >> shift) & 1)
                    | (((source[row * 2 + 1] >> shift) & 1) << 1)
                )
    return Image.fromarray(values, "L")


def encode(image: Image.Image) -> bytes:
    values = np.asarray(image)
    assert values.shape == (FRAME_SIZE, FRAME_SIZE)
    assert set(np.unique(values)) <= {0, 1, 2, 3}
    packet = bytearray()
    for y in range(0, FRAME_SIZE, 8):
        for x in range(0, FRAME_SIZE, 8):
            for row in values[y:y + 8, x:x + 8]:
                packet.extend((
                    sum((int(value) & 1) << (7 - i) for i, value in enumerate(row)),
                    sum((int(value) >> 1) << (7 - i) for i, value in enumerate(row)),
                ))
    assert len(packet) == FRAME_BYTES
    return bytes(packet)


def rgba(image: Image.Image, palette) -> Image.Image:
    values = np.asarray(image)
    colors = np.asarray(palette, dtype="uint8")
    colors = (colors << 3) | (colors >> 2)
    alpha = np.where(values != 0, 255, 0).astype("uint8")
    return Image.fromarray(np.dstack((colors[values], alpha)), "RGBA")


def family_palettes(role: str) -> tuple[int, ...]:
    """Existing color families only; quest4 is never borrowed or recolored."""
    if role.startswith("troll_") or role.startswith("senjin_"):
        return (6, 7, 3, 5)
    if role == "imp":
        return (7,)
    if role in ("scorpid", "sarkoth"):
        return (1, 3, 5)
    if role in ("boar", "tiger"):
        return (3, 5)
    if role in ("felhunter", "panther"):
        return (1, 5)
    if role == "harpy":
        return (1, 3, 5, 7)
    if role in ("enemy_warlock", "yarrog"):
        return (1, 5)
    if role == "raptor":
        return (2, 3, 7)
    if role == "rock_one_npc":
        return (3, 5)
    return (2, 3, 5)


def tile_material_palettes(role: str, colors, opaque, candidates: tuple[int, ...]) -> tuple[int, ...]:
    """Preserve supplied material hues so dim skin is not fitted as leather."""
    r, g, b = colors[..., 0], colors[..., 1], colors[..., 2]
    visible_green = np.any(opaque & (g >= r) & (g > b + 2) & (g > 8))
    blue_pixels = np.count_nonzero(opaque & (b > r) & (g >= r) & (colors.sum(2) > 12))
    visible_blue = blue_pixels > 0
    visible_purple = np.any(opaque & (b > g) & (r >= g) & (colors.sum(2) > 12))
    red_pixels = np.count_nonzero(opaque & (r * 10 > g * 16) & (r * 10 > b * 16) & (r > 8))
    visible_red = red_pixels > 0
    if role.startswith("troll_") or role.startswith("senjin_"):
        if red_pixels > blue_pixels * 1.2:
            return (7,)
        if visible_blue:
            return (6,)
        if visible_red:
            return (7,)
    elif role in ("enemy_warlock", "yarrog", "felhunter", "panther", "harpy", "scorpid", "sarkoth"):
        if visible_purple:
            return (1,)
    elif 2 in candidates:
        if visible_green:
            return (2,)
        if role == "raptor" and visible_red:
            return (7,)
    return candidates


def fit_rgba(source: Image.Image, candidates: tuple[int, ...], default: int, role: str):
    """Select one stable three-opaque-color palette per8x8 OBJ, preserving alpha."""
    pixels = np.asarray(source)
    rgb = pixels[..., :3].astype("int32") >> 3
    opaque = pixels[..., 3] != 0
    assert source.size == (24, 24) and set(np.unique(pixels[..., 3])) <= {0, 255}
    values = np.zeros((24, 24), dtype="uint8")
    rendered = np.zeros((24, 24, 4), dtype="uint8")
    attrs = []
    for y in range(0, 24, 8):
        for x in range(0, 24, 8):
            colors = rgb[y:y + 8, x:x + 8]
            mask = opaque[y:y + 8, x:x + 8]
            # Source outlines carry the shape. Fitting weights their existing
            # dark marks; the mask and every pixel position remain untouched.
            weights = np.where(colors.sum(2) < 20, 2, 1)
            options = {}
            local_candidates = tile_material_palettes(role, colors, mask, candidates)
            # Compare source and palette hue as well as brightness. Otherwise
            # a dim purple source would become brown/green or solid outline.
            chroma = colors * 31 / np.maximum(colors.max(2, keepdims=True), 1)
            chroma_weight = np.where(colors.sum(2) > 10, 1.0, 0.0)
            for candidate in local_candidates:
                palette = np.asarray(PALETTES[candidate][1:], dtype="int32")
                distances = ((colors[..., None, :] - palette[None, None, :, :]) ** 2).sum(3)
                palette_chroma = palette * 31 / np.maximum(palette.max(1, keepdims=True), 1)
                hue_distances = ((chroma[..., None, :] - palette_chroma[None, None, :, :]) ** 2).sum(3)
                # The last opaque color is source outline/shadow ink. Hue
                # matching must never lift all of those dim marks into fill.
                hue_distances[..., 2] = 0
                distances = distances + hue_distances * chroma_weight[..., None]
                options[candidate] = (float((distances.min(2) * weights)[mask].sum()), distances)
            selected = min(local_candidates, key=lambda p: (options[p][0], p != default, p))
            indices = (options[selected][1].argmin(2) + 1).astype("uint8")
            indices[~mask] = 0
            values[y:y + 8, x:x + 8] = indices
            palette = np.asarray(PALETTES[selected], dtype="uint8")
            palette = (palette << 3) | (palette >> 2)
            rendered[y:y + 8, x:x + 8, :3] = palette[indices]
            rendered[y:y + 8, x:x + 8, 3] = pixels[y:y + 8, x:x + 8, 3]
            attrs.append(selected)
    assert np.array_equal(rendered[..., 3], pixels[..., 3])
    return Image.fromarray(values, "L"), Image.fromarray(rendered, "RGBA"), bytes(attrs)


def rgba_from_attrs(image: Image.Image, attrs: bytes) -> Image.Image:
    assert len(attrs) == 9
    result = Image.new("RGBA", (24, 24))
    for tile, palette in enumerate(attrs):
        y, x = divmod(tile, 3)
        result.paste(rgba(image.crop((x * 8, y * 8, x * 8 + 8, y * 8 + 8)), PALETTES[palette]), (x * 8, y * 8))
    return result


def active_mask(image: Image.Image) -> int:
    values = np.asarray(image)
    return sum(
        int(np.any(values[y:y + 8, x:x + 8] != 0)) << tile
        for tile, (y, x) in enumerate((
            (y, x) for y in range(0, FRAME_SIZE, 8)
            for x in range(0, FRAME_SIZE, 8)
        ))
    )


def label(role: str) -> str:
    return "PeonWorld" + "".join(word.capitalize() for word in role.split("_")) + "V0215"


def twelve_frames(data: bytes, native_layout="pose_major") -> list[Image.Image]:
    if native_layout == "pose_major":
        assert len(data) == 12 * 64
        # Existing PeonFacings addresses0..15 idle, 16..31A, 32..47B.
        return [decode(data[(pose * 4 + direction) * 64:
                                 (pose * 4 + direction + 1) * 64], 16)
                for direction in range(4) for pose in range(3)]
    if native_layout == "one_pose":
        assert len(data) == 64
        return [decode(data, 16) for _ in range(12)]
    if native_layout == "native_three_directions":
        assert len(data) == 6 * 64
        # Crystal's native down/up/left idle then down/up/left step;
        # down/up stepB is mirroredstepA, side A/B share their native art.
        source = [decode(data[i * 64:(i + 1) * 64], 16) for i in range(6)]
        result = []
        for direction in range(4):
            base = min(direction, 2)
            views = [source[base], source[base + 3],
                     source[base + 3].transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                     if direction < 2 else source[base + 3]]
            if direction == 3:
                views = [view.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for view in views]
            result.extend(views)
        return result
    raise ValueError(native_layout)


def main():
    GFX.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    old_manifest = json.loads(OLD_NPC_MANIFEST.read_text())
    original_png_hashes = {relative(path): sha(path.read_bytes())
                           for path in (ROOT / "references/characters").rglob("*.png")}
    specs = {}
    for role in ("base", "shaman", "warrior", "warlock"):
        path = (ROOT / "gfx/native_actor_restore_v0213/peon/overworld.bin"
                if role in ("base", "shaman") else
                ROOT / f"gfx/approved_player_v0212/{role}/overworld.bin")
        specs[role] = {"path": path, "palette": 1 if role == "warlock" else 2,
                       "kind": "hero", "layout": "pose_major",
                       "source_note": ("Archived original native Peon/Shaman world pixels"
                                       if role in ("base", "shaman") else
                                       "Existing approved lossy raster import; not recovered native PNG detail"),
                       "source_artwork_manifest": ("gfx/native_actor_restore_v0213/manifest.json"
                                                   if role in ("base", "shaman") else
                                                   "references/generated/approved_player_import_v0212/manifest.json")}
    for role, entry in old_manifest["roles"].items():
        specs[role] = {"path": ROOT / f"gfx/user_world_v0211/{role}/overworld.bin",
                       "palette": entry["palette_index"], "kind": "supplied_npc",
                       "layout": "pose_major", "source_png_frames": entry["frames"],
                       "fit_source_pngs": True,
                       "source_note": "Supplied16px PNGs enlarged bynearest; existing explicit whole-PNG fallbacks retained; per8px color fit"}
    specs["rock_one_npc"] = {"path": ROOT / "gfx/rock_roster_v0213/one/overworld_npc.bin",
                             "palette": 3, "kind": "supplied_rock_npc", "layout": "pose_major",
                             "fit_source_pngs": True,
                             "source_note": "Supplied small-rock native PNG enlarged bynearest; per8pxcolor fit",
                             "source_png": "references/characters/peon_of_warcraft_environment_pack_v2_art_quality/durotar_valley/rock_durotar_small_01_16x16.png"}
    for stage in ("one", "vein", "element"):
        raw_palette = (ROOT / f"gfx/rock_roster_v0213/{stage}/world_palette.bin").read_bytes()
        custom_palette = [tuple((int.from_bytes(raw_palette[i:i + 2], "little") >> shift) & 31
                                for shift in (0, 5, 10)) for i in range(0, 8, 2)]
        specs[f"rock_{stage}"] = {"path": ROOT / f"gfx/rock_roster_v0213/{stage}/overworld.bin",
                                  "palette": 3, "custom_palette": custom_palette,
                                  "kind": "roster_only_derived_rock", "layout": "pose_major",
                                  "source_note": "Derived larger rock packet exported separately; native16px roster menu icon remains bound to original"}
    # These two sources lack intact equivalent supplied directions. They are
    # archived whole bodies, not a newly authored stand-in for a supplied PNG.
    specs["sleeping"] = {"path": ROOT / "gfx/sprites/peon_sleeping.2bpp",
                         "palette": 2, "kind": "approved_archived_native", "layout": "one_pose",
                         "source_note": "Archived original sleeping pose; procedural v0211sleeping packet excluded"}
    specs["crawler"] = {"path": ROOT / "gfx/sprites/peon_crawler.2bpp", "palette": 4,
                        "kind": "historical_noncanonical", "layout": "native_three_directions",
                        "source_note": "Existing historical crawler frames, enlarged only; no supplied crawler PNG exists"}
    specs["yarrog"] = {"path": ROOT / "gfx/user_world_v0211/enemy_warlock/overworld.bin", "palette": 1,
                       "kind": "supplied_warlock_family", "layout": "pose_major",
                       "source_png_frames": old_manifest["roles"]["enemy_warlock"]["frames"],
                       "fit_source_pngs": True,
                       "source_note": "Complete supplied enemyWarlock fourdirection PNGs; historical procedural Yarrog excluded"}
    for role, species in (("kolkar_archer", "ponyta"), ("kolkar_raider", "rapidash")):
        specs[role] = {"path": ROOT / f"gfx/peon_native_v029/{species}/world_npc.2bpp",
                       "palette": 3, "baseline_palette": OLD_PALETTES[0], "palette_index_before": 0,
                       "kind": "historical_noncanonical", "layout": "native_three_directions",
                       "source_note": "Current active historical nativeKolkar frames enlarged only; no suppliedKolkar PNG exists; exact indices retain sourceleather/ink family3 insteadofHUDredoutline family0"}
    records = {}
    graphics = ["; World-only24px source-derived packets. Native16px UI icons stay unchanged."]
    bound_roles = {role for _, _, role in BINDINGS} | {"base", "shaman", "warrior", "warlock", "sleeping", "crawler", "yarrog", "rock_one_npc", "kolkar_archer", "kolkar_raider"}
    for role, spec in specs.items():
        folder = GFX / role
        folder.mkdir(exist_ok=True)
        review = REVIEW / role
        review.mkdir(exist_ok=True)
        data = spec["path"].read_bytes()
        old_frames = twelve_frames(data, spec["layout"])
        baseline_palette = spec.get("baseline_palette", spec.get("custom_palette", OLD_PALETTES[spec["palette"]]))
        old_rgba_frames = [rgba(frame, baseline_palette) for frame in old_frames]
        source_frames = []
        if spec.get("fit_source_pngs"):
            if spec.get("source_png"):
                source_frames = [Image.open(ROOT / spec["source_png"]).convert("RGBA") for _ in range(12)]
            else:
                source_frames = [Image.open(ROOT / frame["source"]).convert("RGBA")
                                 for frame in spec["source_png_frames"] for _ in range(3)]
            assert len(source_frames) == 12
            assert all(image.size == (16, 16) for image in source_frames)
            assert all(np.array_equal(np.asarray(source.getchannel("A")), np.asarray(old.getchannel("A")))
                       for source, old in zip(source_frames, old_rgba_frames))
            candidates = family_palettes(role)
            converted = [fit_rgba(source.resize((24, 24), Image.Resampling.NEAREST), candidates, spec["palette"], role)
                         for source in source_frames]
            new_frames = [result[0] for result in converted]
            new_rgba_frames = [result[1] for result in converted]
            frame_attrs = [result[2] for result in converted]
        else:
            candidates = (spec["palette"],)
            source_frames = old_rgba_frames
            new_frames = [frame.resize((24, 24), Image.Resampling.NEAREST) for frame in old_frames]
            frame_attrs = [bytes([spec["palette"]] * 9) for _ in range(12)]
            palette = spec.get("custom_palette", PALETTES[spec["palette"]])
            new_rgba_frames = [rgba(frame, palette) for frame in new_frames]
        packets = [encode(frame) for frame in new_frames]
        masks = [active_mask(frame) for frame in new_frames]
        packet = b"".join(packets)
        mask_data = b"".join(mask.to_bytes(2, "little") for mask in masks)
        assert len(packet) == 12 * FRAME_BYTES and len(mask_data) == 24
        assert all(np.array_equal(np.asarray(decode(encoded, 24)), np.asarray(frame))
                   for frame, encoded in zip(new_frames, packets))
        # Every original coordinate contributes to the nearest enlarged grid.
        coverage = Image.fromarray(np.arange(256, dtype="uint8").reshape(16, 16), "L").resize((24, 24), Image.Resampling.NEAREST)
        assert set(np.asarray(coverage).flatten()) == set(range(256))
        (folder / "overworld.bin").write_bytes(packet)
        (folder / "masks.bin").write_bytes(mask_data)
        attrs_data = b"".join(frame_attrs)
        assert len(attrs_data) == 108
        (folder / "attrs.bin").write_bytes(attrs_data)
        palette = spec.get("custom_palette", PALETTES[spec["palette"]])
        grayscale = [255, 170, 85, 0]
        indexed_strip = Image.new("P", (24, 24 * 12))
        indexed_strip.putpalette([value for gray in grayscale for value in (gray, gray, gray)] + [0] * 756)
        comparison = Image.new("RGBA", (520, 132), (28, 27, 25, 255))
        draw = ImageDraw.Draw(comparison)
        draw.text((4, 2), f"{role}: original16 / derived24 | static native decode", fill="white")
        frame_records = []
        for i, (old, enlarged, encoded, mask) in enumerate(zip(old_frames, new_frames, packets, masks)):
            direction, pose = divmod(i, 3)
            key = f"{DIRECTIONS[direction]}_{pose}"
            old_rgba, new_rgba = old_rgba_frames[i], new_rgba_frames[i]
            if spec.get("fit_source_pngs"):
                source_frames[i].save(review / f"source_{key}_16x16.png")
                decoded_rgba = rgba_from_attrs(decode(encoded, 24), frame_attrs[i])
                assert np.array_equal(np.asarray(decoded_rgba), np.asarray(new_rgba))
            old_rgba.save(review / f"baseline_{key}_16x16.png")
            new_rgba.save(review / f"world_{key}_24x24.png")
            indexed_strip.paste(enlarged, (0, i * 24))
            values = np.asarray(enlarged)
            source_rgb = np.asarray(source_frames[i].resize((24, 24), Image.Resampling.NEAREST))[:, :, :3].astype("int32") >> 3
            rendered_rgb = np.asarray(new_rgba)[:, :, :3].astype("int32") >> 3
            opaque = np.asarray(new_rgba)[:, :, 3] > 0
            color_rmse = round(float(np.sqrt(((source_rgb - rendered_rgb) ** 2)[opaque].mean())), 4)
            frame_records.append({"direction": DIRECTIONS[direction], "pose": pose,
                                  "frame_index": i, "byte_offset": i * FRAME_BYTES,
                                  "source_byte_offset": ((pose * 4 + direction) * 64
                                                         if spec["layout"] == "pose_major" else None),
                                  "opaque_pixels_before": int(np.count_nonzero(np.asarray(old))),
                                  "opaque_pixels_after": int(np.count_nonzero(values)),
                                  "opaque_bounds_before": list(old_rgba.getbbox()),
                                  "opaque_bounds_after": list(new_rgba.getbbox()),
                                  "mask": mask, "oam_entries": mask.bit_count(),
                                  "oam_per8px_row": [sum(bool(mask & 1 << tile)
                                                        for tile in range(row * 3, row * 3 + 3))
                                                      for row in range(3)],
                                  "native_decode_exact": True,
                                  "indexed_pixels_are_nearest_source": not bool(spec.get("fit_source_pngs")),
                                  "per_tile_palette_ids": list(frame_attrs[i]),
                                  "rgb555_error_after": color_rmse,
                                  "alpha_is_nearest_source": True})
            if pose == 0:
                x = direction * 130
                draw.text((x + 4, 20), DIRECTIONS[direction], fill="white")
                # Native-sized comparison plus the same3x display-cell enlargement.
                comparison.alpha_composite(old_rgba, (x + 4, 40))
                comparison.alpha_composite(new_rgba, (x + 32, 32))
                comparison.alpha_composite(old_rgba.resize((48, 48), Image.Resampling.NEAREST), (x + 4, 75))
                comparison.alpha_composite(new_rgba.resize((72, 72), Image.Resampling.NEAREST), (x + 56, 58))
        indexed_strip.save(folder / "overworld.png")
        comparison.convert("RGB").save(review / "comparison.png")
        export = label(role)
        if role in bound_roles:
            graphics += [f'SECTION "Peon24 World {role} v0215", ROMX, ALIGN[4]',
                         f"{export}::", f'\tINCBIN "gfx/world_actors_v0215/{role}/overworld.bin"',
                         f"\tassert @ - {export} == 12 * 9 * TILE_SIZE",
                         f"{export}Masks::", f'\tINCBIN "gfx/world_actors_v0215/{role}/masks.bin"',
                         f"\tassert @ - {export}Masks == 12 * 2",
                         f"{export}Attrs::", f'\tINCBIN "gfx/world_actors_v0215/{role}/attrs.bin"',
                         f"\tassert @ - {export}Attrs == 12 * 9",
                         f"\tassert {export}Attrs - {export}Masks == 12 * 2",
                         f"\tassert BANK({export}) == BANK({export}Masks)", ""]
        records[role] = {"source_packet": relative(spec["path"]), "source_sha256": sha(data),
                         "source_note": spec["source_note"], "source_kind": spec["kind"],
                         "native_input_layout": spec["layout"],
                         "source_png_frames": spec.get("source_png_frames", []),
                         "source_png": spec.get("source_png"),
                         "source_artwork_manifest": spec.get("source_artwork_manifest"),
                         "output_packet": relative(folder / "overworld.bin"),
                         "output_sha256": sha(packet), "mask_sha256": sha(mask_data), "attrs_sha256": sha(attrs_data),
                         "label": export, "masks_label": export + "Masks", "attrs_label": export + "Attrs",
                         "palette_index": spec["palette"], "palette_rgb555": palette,
                         "palette_index_before": spec.get("palette_index_before", spec["palette"]),
                         "candidate_palette_indices": list(candidates),
                         "source_color_recovery_from_png": bool(spec.get("fit_source_pngs")),
                         "uses_palette_indices": sorted(set(attrs_data)),
                         "frame_records": frame_records, "exported_in_rom": role in bound_roles,
                         "adds_new_pixel_detail": False, "source_pixels_invented": False}
    (GFX / "graphics.asm").write_text("\n".join(graphics).rstrip() + "\n")
    bindings = ["; Included inside the floating world-renderer ROM section.",
                "; Records: sprite, palette, bankframes, dwframes, bankmasks, dwmasks.",
                "PeonLargeWorldBindingsV0215::"]
    runtime_bindings = [(sprite, role, records[role]["palette_index"]) for sprite, _, role in BINDINGS]
    runtime_bindings += [("SPRITE_RED", "sleeping", 2), ("SPRITE_LASS", "crawler", 4),
                         ("SPRITE_ROCKER", "yarrog", 1), ("SPRITE_POKEFAN_M", "rock_one_npc", 3)]
    runtime_bindings += [("SPRITE_POKEFAN_F", "orc_guard", 2),
                         ("SPRITE_COOLTRAINER_M", "kolkar_archer", 3),
                         ("SPRITE_COOLTRAINER_F", "kolkar_raider", 3)]
    for sprite, role, palette in runtime_bindings:
        export = label(role)
        bindings += [f"\tdb {sprite}, {palette}, BANK({export})", f"\tdw {export}",
                     f"\tdb BANK({export}Masks)", f"\tdw {export}Masks"]
    bindings += ["\tdb $ff", "", "PeonLargeWorldHeroBindingsV0215::"]
    for role in ("base", "shaman", "warrior", "warlock"):
        export = label(role)
        bindings += [f"\tdb SPRITE_CHRIS, {records[role]['palette_index']}, BANK({export})",
                     f"\tdw {export}", f"\tdb BANK({export}Masks)", f"\tdw {export}Masks"]
    bindings += ["\tassert @ - PeonLargeWorldHeroBindingsV0215 == 4 * 8"]
    (GFX / "bindings.asm").write_text("\n".join(bindings) + "\n")
    assert all(sha((ROOT / path).read_bytes()) == digest for path, digest in original_png_hashes.items())
    (REVIEW / "source_png_hashes.json").write_text(json.dumps({
        "source_files": dict(sorted(original_png_hashes.items())),
        "source_files_count": len(original_png_hashes),
        "all_source_sha256_identical_before_after_import": True,
    }, indent=2) + "\n")
    report = {"version": "v0.2.15", "method": "Hero native indices enlarged to24px; suppliedNPC PNG colors recovered per8pxusing existingOBJpalettes; nearestsampling only",
              "dimensions_before": [16, 16], "dimensions_after": [24, 24],
              "linear_size_ratio": 1.5, "canvas_area_ratio": 2.25,
              "native_tile_order": "row-major", "native_frame_order": "direction*3+pose (front/back/left/right)",
              "native_walk_cycle": [0, 1, 0, 2], "bytes_per_frame": 144,
              "mask_encoding": "12 little-endian9-bit masks; bit0=upperleft, bit8=lowerright",
              "attributes_encoding": "108 paletteIDbytes12x9; immediately after24maskbytes, sameROMbank",
              "graphics_alignment": 16, "palette_files_written_by_importer": False,
              "effective_world_palettes_rgb555": PALETTES,
              "palette_integration_required": "Root applies restoredfamily2forallclasses and archivedred/gold/inkImp7; masterroom3/4/5/7overridepreserved",
              "quest_palette4_excluded_from_fits": True,
              "color_fit_policy": "ThreeopaqueRGB555colors per8pxOBJ; source-materialhueguards retain Orcgreen/Trollblue/Warlockpurple/Impred; outlinepositions unchanged",
              "new_detail_generated": False, "resampling_is_smoothing": False,
              "source_original_pngs_changed": False, "source_pngs_hashed": len(original_png_hashes),
              "masters_24px_unchanged": True, "map_props_unchanged": True,
              "battle_sprites_unchanged": True, "native16px_menu_icons_unchanged": True,
              "runtime_verification": "Root must verify the compiled ROM; comparisons here are decoded static native packets",
              "runtime_bindings": [{"sprite": sprite, "role": role, "palette_index": palette}
                                   for sprite, role, palette in runtime_bindings],
              "exported_actor_families": len(bound_roles), "roles": records}
    for path in (GFX / "manifest.json", REVIEW / "import_report.json"):
        path.write_text(json.dumps(report, indent=2) + "\n")
    (REVIEW / "README.md").write_text(
        "# Larger world actors v0.2.15\n\n"
        "World actors are enlarged from 16×16 to 24×24 with nearest sampling. "
        "This increases their screen size by 50% and draws no new artistic detail. "
        "NPC colors are recovered from their supplied PNGs using one existing three-opaque-color palette per8px tile. "
        "The hero retains its existing native indexed colors and walk frames so the classmasterroom stays compatible. "
        "Transparent index0 remains transparent; no smoothing is used.\n\n"
        "`import_report.json` records source hashes, source PNG provenance, existing damaged-crop fallbacks, "
        "frame ordering and sparse OAM masks. The original archived sleeping body is restored. "
        "Crawler has no supplied PNG and keeps its whole historical native body. "
        "Yarrog uses the complete supplied enemyWarlock family, retaining the documented front-as-left fallback. "
        "Recruitable Grunts use the complete supplied OrcGuard family. Both Kolkar roles have no supplied PNG: "
        "their existing native bodies are only enlarged, using the sourceleather/ink family3 in placeofHUDred0, "
        "with no claim of new art.\n\n"
        "Comparisons are static packet decodes, not game screenshots. Original source PNGs, battle sprites, "
        "24px class masters, buildings, decor, collisions and warps are unchanged. Native 16px menu icons remain intact.\n")
    print(json.dumps({"actor_families": len(records), "exported_actor_families": len(bound_roles),
                      "runtime_npc_ids": len(runtime_bindings), "frames_verified": len(records) * 12,
                      "source_pngs_unchanged": len(original_png_hashes),
                      "report": relative(REVIEW / "import_report.json")}, indent=2))


if __name__ == "__main__":
    main()
