#!/usr/bin/env python3
"""Package validated v0.2.19 portraits and world restoration without regenerating art.

Requires --rom, --sym, --map and --validation-root. The latter contains the
final matching-ROM validation.json, declared PASS reports and an explicit
native-screen capture allowlist. All checks, including ZIP readback, finish
in memory before any release output is written. Large original PNGs are
rehashed but remain outside the archive; their provenance is included.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from pathlib import Path
import zipfile

from PIL import Image
import numpy as np
from scipy.ndimage import label

ROOT = Path(__file__).resolve().parents[1]
VERSION = "v0.2.19"
BASE = "peon_of_warcraft_v0_2_19"
RELEASE = ROOT / "releases" / VERSION
SCENES = ROOT / "gfx/welcome_scenes_v0218"
PORTRAITS = ROOT / "gfx/class_portraits_v0219"
LABELS = ROOT / "gfx/selection_labels_v0218"
WORLD = ROOT / "gfx/world_readability_v0219"
LARGE_MASTERS = ROOT / "gfx/large_masters_v0219"
WORLD_SOURCES = ROOT / "assets/world_readability_v0219"


def require(value, message):
    if not value:
        raise SystemExit(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def source_path(value):
    path = Path(value)
    return (path if path.is_absolute() else ROOT / path).resolve()


def passed(value):
    return isinstance(value, dict) and (value.get("status") == "PASS"
        if "status" in value else value.get("passed") is True)


def checked_file(path, expected, size=None):
    path = source_path(path)
    data = path.read_bytes()
    require(sha(data) == expected, "SHA256 mismatch: " + str(path))
    require(size is None or len(data) == size, "Byte count mismatch: " + str(path))
    return data


def png(data, size, opaque=False, rgba=False):
    image = Image.open(io.BytesIO(data))
    image.load()
    require(image.format == "PNG" and image.size == size, "Invalid native PNG dimensions/format")
    require(not rgba or image.mode == "RGBA", "Native portrait must retain RGBA")
    alpha = image.convert("RGBA").getchannel("A")
    require(set(alpha.get_flattened_data()) <= {0, 255}, "PNG contains nonbinary alpha")
    require(not opaque or alpha.getextrema() == (255, 255), "Native LCD/scene must be opaque")
    return image


def colors(data):
    require(len(data) == 40, "Expected five native four-color palettes")
    return [tuple(((value >> shift) & 31) * 8 + (((value >> shift) & 31) >> 2)
                  for shift in (0, 5, 10))
            for value in (int.from_bytes(data[i:i + 2], "little")
                          for i in range(0, len(data), 2))]


def paint_tile(image, packet, x, y, palette):
    require(len(packet) == 16, "Native tile packet is incomplete")
    for row in range(8):
        lo, hi = packet[row * 2:row * 2 + 2]
        for column in range(8):
            index = ((lo >> (7 - column)) & 1) | (((hi >> (7 - column)) & 1) << 1)
            image.putpixel((x + column, y + row), palette[index])


def collect_assets(files):
    provenance = {"version": VERSION, "kind": "Static native conversion evidence; not ROM captures",
                  "large_original_PNGs_in_archive": False, "original_sources": [],
                  "primary_static_PNGs": [], "opaque_portrait_previews": [],
                  "native_packet_files": [], "world_and_combat": "World restoration is included separately; battle graphics are preserved"}

    def add(path, data=None):
        path = source_path(path)
        target = "assets/native_selection/" + path.relative_to(ROOT / "gfx").as_posix()
        require(target not in files, "Duplicate native asset: " + target)
        files[target] = path.read_bytes() if data is None else data
        return target

    def original(record, expected_size=None):
        path = source_path(record["path"])
        payload = checked_file(path, record["sha256"])
        image = Image.open(io.BytesIO(payload))
        image.load()
        require(image.format == "PNG", "Original illustration must be PNG: " + str(path))
        dimensions = tuple(record.get("size", expected_size or image.size))
        require(image.size == dimensions and (expected_size is None or image.size == expected_size),
                "Original source dimensions changed: " + str(path))
        provenance["original_sources"].append({"source": path.relative_to(ROOT).as_posix(),
            "sha256": sha(payload), "bytes": len(payload), "dimensions": list(image.size),
            "original_read_only": True, "included_in_archive": False})
        return image

    scene_manifest = json.loads((SCENES / "manifest.json").read_bytes())
    require(passed(scene_manifest) and scene_manifest.get("version") == "v0.2.18", "Welcome scene import must remain the approved v0.2.18")
    require(set(scene_manifest["states"]) == {"base", "shaman", "warrior", "warlock"},
            "Expected four complete welcome scenes")
    require(set(scene_manifest["sources"]) == {"base", "background", "classes"},
            "Expected all three original welcome illustration sources")
    for record in scene_manifest["sources"].values():
        original(record)
    add(SCENES / "manifest.json")
    expected_lengths = {"tiles_bank1.2bpp": 4096, "tiles_bank0.2bpp": 1536,
                        "tilemap.bin": 360, "attrs.bin": 360, "palettes.bin": 40}
    for role, record in scene_manifest["states"].items():
        require(set(record["files"]) == set(expected_lengths), "Incomplete welcome scene packets")
        packets = {}
        for name, length in expected_lengths.items():
            entry = record["files"][name]
            require(source_path(entry["path"]) == SCENES / role / name,
                    "Welcome manifest packet path differs from role/name")
            require(entry["bytes"] == length, "Welcome manifest packet size differs")
            packets[name] = checked_file(entry["path"], entry["sha256"], length)
            provenance["native_packet_files"].append(add(entry["path"], packets[name]))
        palette = colors(packets["palettes.bin"])
        decoded = Image.new("RGB", (160, 144))
        for tile, (tile_id, attr) in enumerate(zip(packets["tilemap.bin"], packets["attrs.bin"])):
            require(2 <= attr & 7 <= 6 and not attr & 0xf0, "Invalid scene native attribute")
            if attr & 8:
                require(not 0x50 <= tile_id <= 0x5f, "Welcome scene overwrites reserved bank1 slots")
                offset = ((tile_id - 0x80) & 255) * 16
                packet = packets["tiles_bank1.2bpp"][offset:offset + 16]
            else:
                require(tile_id < 0x48, "Welcome scene overwrites reserved font/label bank0 slots")
                packet = packets["tiles_bank0.2bpp"][tile_id * 16:(tile_id + 1) * 16]
            index = ((attr & 7) - 2) * 4
            paint_tile(decoded, packet, tile % 20 * 8, tile // 20 * 8, palette[index:index + 4])
        hardware = SCENES / role / "hardware.png"
        data = hardware.read_bytes()
        image = png(data, (160, 144), opaque=True)
        require(image.convert("RGB").tobytes() == decoded.tobytes(), "Scene PNG differs from native packet decode")
        require(sha(decoded.tobytes()) == record["hardware_rgb_sha256"], "Scene decoded RGB hash differs")
        provenance["primary_static_PNGs"].append(add(hardware, data))

    portrait_manifest = json.loads((PORTRAITS / "manifest.json").read_bytes())
    require(passed(portrait_manifest) and portrait_manifest.get("version") == VERSION, "Master portrait import is not v0.2.19 PASS")
    require(set(portrait_manifest["roles"]) == {"kento", "zogzog", "bismillah"}, "Expected three master portraits")
    add(PORTRAITS / "manifest.json")
    for role, record in portrait_manifest["roles"].items():
        atlas = original({"path": record["source"], "sha256": record["source_sha256"]}, (2078, 757)).convert("RGBA")
        require(record["native_canvas"] == [80, 88] and record.get("crop_complete") is True,
                "Portrait must retain its whole approved bust on80x88")
        require(record.get("unapproved_neighbor_pixels_imported") == 0,
                "Portrait imported unapproved neighboring artwork")
        source_rgba = np.asarray(atlas)
        labels, component_count = label(source_rgba[:, :, 3] >= 128)
        sizes = np.bincount(labels.ravel())
        components = [int(k) for k in np.argsort(sizes)[::-1] if k and sizes[k] > 10000]
        require(len(components) == 3, "Expected three large source bust components")
        components.sort(key=lambda k: np.nonzero(labels == k)[1].mean())
        approved_panel = {"kento": 0, "zogzog": 1, "bismillah": 2}[role]
        component = components[approved_panel]
        mask = labels == component
        ys, xs = np.nonzero(mask)
        bounds = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
        require(record["source_crop"] == bounds and record["selected_panel_identity"] == approved_panel,
                "Portrait crop/approved panel changed")
        require(record["source_component_id"] == component
                and record["source_component_count"] == component_count
                and record["source_component_opaque_pixels"] == int(mask.sum()),
                "Portrait source component metadata differs")
        x0, y0, x1, y1 = bounds
        fit_scale = min(80 / (x1 - x0), 88 / (y1 - y0))
        fit_size = (round((x1 - x0) * fit_scale), round((y1 - y0) * fit_scale))
        fit_origin = ((80 - fit_size[0]) // 2, 88 - fit_size[1])
        require(record["fit_dimensions"] == list(fit_size)
                and record["fit_origin"] == list(fit_origin), "Portrait whole-bust nearest fit changed")
        isolated_alpha = Image.fromarray(mask.astype(np.uint8) * 255).crop(tuple(bounds))
        fit_alpha = isolated_alpha.resize(fit_size, Image.Resampling.NEAREST)
        expected_alpha = Image.new("L", (80, 88), 0)
        expected_alpha.paste(fit_alpha, fit_origin)
        folder = PORTRAITS / role
        outputs = record["outputs"]
        expected = {str((folder / name).relative_to(ROOT)): length for name, length in (
            ("portrait.2bpp", 1760), ("attrs.bin", 110), ("palettes.bin", 40), ("hardware.png", None))}
        require(set(outputs) == set(expected), "Portrait outputs differ from native80x88 ABI")
        payloads = {}
        for path, length in expected.items():
            entry = outputs[path]
            require(isinstance(entry, dict) and entry.get("bytes") is not None,
                    "Portrait output must declare SHA and byte count")
            data = checked_file(path, entry["sha256"], length)
            require(entry["bytes"] == len(data), "Portrait manifest byte count mismatch")
            payloads[Path(path).name] = data
        for name in ("portrait.2bpp", "attrs.bin", "palettes.bin"):
            provenance["native_packet_files"].append(add(folder / name, payloads[name]))
        require(set(payloads["attrs.bin"]) <= set(range(3, 8)), "Portrait uses an unallocated palette")
        palette = colors(payloads["palettes.bin"])
        decoded = Image.new("RGB", (80, 88))
        for tile, attr in enumerate(payloads["attrs.bin"]):
            index = (attr - 3) * 4
            require(palette[index] == (24, 16, 24), "Portrait lost its shared opaque panel ink")
            paint_tile(decoded, payloads["portrait.2bpp"][tile * 16:(tile + 1) * 16],
                       tile % 10 * 8, tile // 10 * 8, palette[index:index + 4])
        hardware = png(payloads["hardware.png"], (80, 88), rgba=True)
        require(hardware.convert("RGB").tobytes() == decoded.tobytes(), "Portrait PNG differs from packet decode")
        require(expected_alpha.tobytes() == hardware.getchannel("A").tobytes(),
                "Portrait changed complete source component/nearest alpha geometry")
        require(record.get("native_opaque_pixels") == int(np.count_nonzero(np.asarray(expected_alpha))),
                "Portrait opaque-pixel metadata differs")
        provenance["primary_static_PNGs"].append(add(folder / "hardware.png", payloads["hardware.png"]))
        preview = io.BytesIO()
        decoded.save(preview, format="PNG")
        provenance["opaque_portrait_previews"].append(add(folder / "hardware_bg.png", preview.getvalue()))

    label_manifest = json.loads((LABELS / "manifest.json").read_bytes())
    require(passed(label_manifest) and label_manifest.get("version") == "v0.2.18" and label_manifest["tiles"] == 24
            and label_manifest["tile_ids"] == [0x48, 0x5f], "Invalid native label allocation")
    label_source = checked_file(label_manifest["source"], label_manifest["source_sha256"])
    label_packet = checked_file(LABELS / "labels.2bpp", label_manifest["packet_sha256"], 384)
    files["assets/native_selection/welcome_labels.json"] = label_source
    add(LABELS / "manifest.json")
    provenance["native_packet_files"].append(add(LABELS / "labels.2bpp", label_packet))
    require(len(provenance["primary_static_PNGs"]) == 7, "Expected seven primary native PNGs")
    require(len(provenance["original_sources"]) == 6, "Expected three illustrations and three preserved masters")
    files["assets/source_provenance.json"] = json_bytes(provenance)
    return provenance


def collect_world_assets(files, validation):
    """Verify all39 emitted families, including the exact30/90 engine binding."""
    manifest_path = WORLD / "manifest.json"
    manifest_data = manifest_path.read_bytes()
    manifest = json.loads(manifest_data)
    require(passed(manifest) and manifest.get("version") == VERSION,
            "World restoration manifest is not v0.2.19 PASS")
    roles = manifest.get("roles", {})
    require(len(roles) == 39, "Expected39 world actor families")
    bound = {name for name, role in roles.items() if role.get("exported_in_rom") is True}
    require(len(bound) == 30 and manifest.get("exported_actor_families") == 30,
            "Expected30 world families bound in the engine")
    contract = {"manifest_sha256": sha(manifest_data), "role_families": 39,
                "bound_families": 30, "bound_packets": 90}
    require(validation.get("world_asset_contract") == contract,
            "Final validation world_asset_contract differs from the packaged39/30/90 assets")
    provenance = {"version": VERSION, "scope": "Static native world restoration, not ROM screenshots",
                  "contract": contract, "original_sources_in_archive": False,
                  "source_files_rehashed": {}, "source_JSONs": [],
                  "world_packet_files": [], "bound_packet_files": [], "world_static_PNGs": [],
                  "large_master_files": [], "roles": {}}

    def add(path, data=None):
        path = source_path(path)
        require(path.is_relative_to(ROOT), "World asset escapes repository")
        target = "assets/native_world/" + path.relative_to(ROOT).as_posix()
        require(target not in files, "Duplicate world asset: " + target)
        files[target] = path.read_bytes() if data is None else data
        return target

    checked_sources = {}

    def source_check(path, expected):
        require(isinstance(path, str) and isinstance(expected, str) and len(expected) == 64,
                "Malformed world source SHA declaration")
        key = source_path(path)
        require(key.is_relative_to(ROOT), "World source escapes repository")
        if key in checked_sources:
            require(checked_sources[key] == expected, "Conflicting world source hash")
            return
        payload = checked_file(key, expected)
        checked_sources[key] = expected
        provenance["source_files_rehashed"][key.relative_to(ROOT).as_posix()] = {
            "sha256": expected, "bytes": len(payload), "declared_source_SHA_rechecked": True}

    def visit_sources(value):
        if isinstance(value, dict):
            for map_name in ("source_files_sha256", "source_json_sha256", "source_hashes",
                             "source_files", "all_v13_master_source_files_untouched"):
                declared = value.get(map_name)
                if isinstance(declared, dict):
                    for name, digest in declared.items():
                        if isinstance(digest, str) and len(digest) == 64:
                            source_check(name, digest)
            if isinstance(value.get("source_sha256"), str):
                for name in ("source_packet", "source", "source_png"):
                    if isinstance(value.get(name), str):
                        source_check(value[name], value["source_sha256"])
                        break
            for path_key, digest_key in (("source_original_copy", "source_original_png_sha256"),
                                         ("path", "sha256")):
                if isinstance(value.get(path_key), str) and isinstance(value.get(digest_key), str):
                    source_check(value[path_key], value[digest_key])
            for child in value.values():
                visit_sources(child)
        elif isinstance(value, list):
            for child in value:
                visit_sources(child)

    visit_sources(manifest)
    add(manifest_path, manifest_data)
    graphics_data = (WORLD / "graphics.asm").read_bytes()
    declarations = re.findall(r'\bINCBIN\s+"([^"]+)"', graphics_data.decode())
    expected_bound = {str((WORLD / role / name).relative_to(ROOT)) for role in bound
                      for name in ("overworld.bin", "masks.bin", "attrs.bin")}
    require(len(declarations) == 90 and len(set(declarations)) == 90
            and set(declarations) == expected_bound, "Engine does not bind exactly the declared90 world packets")
    add(WORLD / "graphics.asm", graphics_data)
    add(WORLD / "bindings.asm")
    palettes = manifest["effective_world_palettes_rgb555"]
    require(len(palettes) == 8 and all(len(p) == 4 for p in palettes), "Invalid world palette profile")
    expanded = [[tuple((int(v) << 3) | (int(v) >> 2) for v in color) for color in p]
                for p in palettes]
    for role, record in sorted(roles.items()):
        folder = WORLD / role
        require(source_path(record["output_packet"]) == folder / "overworld.bin",
                "World packet points outside its declared role")
        packet = checked_file(folder / "overworld.bin", record["output_sha256"], 1728)
        masks = checked_file(folder / "masks.bin", record["mask_sha256"], 24)
        attrs = checked_file(folder / "attrs.bin", record["attrs_sha256"], 108)
        require(all(value < 8 for value in attrs), "World body uses a non-GBC palette")
        if role in bound:
            require(not set(attrs) & {0, 4}, "Bound world body borrows a quest/HUD palette")
        strip = Image.new("RGBA", (96, 72))
        for frame in range(12):
            base = frame * 144
            active = 0
            for tile in range(9):
                raw = packet[base + tile * 16:base + (tile + 1) * 16]
                if any(raw):
                    active |= 1 << tile
                pal = expanded[attrs[frame * 9 + tile]]
                rgba = [(*rgb, 0 if index == 0 else 255) for index, rgb in enumerate(pal)]
                x = frame // 3 * 24 + tile % 3 * 8
                y = frame % 3 * 24 + tile // 3 * 8
                paint_tile(strip, raw, x, y, rgba)
            require(active == int.from_bytes(masks[frame * 2:frame * 2 + 2], "little"),
                    "World transparent-tile mask differs from its complete body: " + role)
        native_data = (folder / "overworld.png").read_bytes()
        native = png(native_data, (96, 72), rgba=True)
        require(native.tobytes() == strip.tobytes(), "World PNG differs from its complete native packet decode: " + role)
        paths = []
        for name, data in (("overworld.bin", packet), ("masks.bin", masks), ("attrs.bin", attrs)):
            target = add(folder / name, data)
            provenance["world_packet_files"].append(target)
            paths.append(target)
            if role in bound:
                provenance["bound_packet_files"].append(target)
        target = add(folder / "overworld.png", native_data)
        provenance["world_static_PNGs"].append(target)
        provenance["roles"][role] = {"exported_in_rom": role in bound, "packet_paths": paths,
            "native_RGBA_strip": target, "native_decode_and_masks_exact": True,
            "source_kind": record.get("source_kind"), "source_note": record.get("source_note")}
    require(len(provenance["world_packet_files"]) == 117
            and len(provenance["bound_packet_files"]) == 90
            and len(provenance["world_static_PNGs"]) == 39,
            "World release asset counts differ from the39/30/90 contract")
    # Include source/provenance JSONs, never the large original illustrations.
    for path in sorted(WORLD_SOURCES.glob("*.json")):
        payload = path.read_bytes()
        json.loads(payload)
        target = add(path, payload)
        provenance["source_JSONs"].append({"path": target, "source": path.relative_to(ROOT).as_posix(),
            "sha256": sha(payload), "bytes": len(payload)})
    require(provenance["source_JSONs"], "No world source/provenance JSONs were declared")
    master_path = LARGE_MASTERS / "manifest.json"
    master_data = master_path.read_bytes()
    master = json.loads(master_data)
    require(passed(master)
            and master.get("all_source_alpha128_pixels_inside_four_whole_component_crops") is True
            and master.get("all9_oam_positions_and_tileids_preserved") is True,
            "Garrosh master source is not a complete-body PASS")
    visit_sources(master)
    for name, digest in master["v13_master_sources_untouched"].items():
        source_check(name, digest)
    asset_records = master["asset_files"]
    require({"warrior_trainer.bin", "facings.asm", "palettes.asm", "graphics.asm",
             "garrosh_master_native24.png"} <= set(asset_records),
            "Garrosh static source manifest is incomplete")
    asset_data = {}
    for name, entry in sorted(asset_records.items()):
        require(Path(name).name == name, "Unsafe Garrosh static asset filename")
        asset_data[name] = checked_file(LARGE_MASTERS / name, entry["sha256"], entry["bytes"])
        if name.endswith("native24.png"):
            png(asset_data[name], (24, 24), rgba=True)
    source_record = master["source_original_png_unmodified"]
    source_check(source_record["path"], source_record["sha256"])
    source_art = Image.open(io.BytesIO(checked_file(source_record["path"], source_record["sha256"]))).convert("RGBA")
    require(list(source_art.size) == source_record["size"], "Garrosh source sheet dimensions changed")
    source_values = np.asarray(source_art)
    component_labels, component_count = label(source_values[:, :, 3] >= 64)
    require(component_count == 4, "Garrosh source must contain four complete alpha-connected directions")
    require(int(np.count_nonzero(source_values[:, :, 3] >= 128)) == master["source_alpha128_pixels"],
            "Garrosh source opaque-pixel count changed")
    source_json_path = roles["warrior_trainer"]["source_packet"]
    source_json_data = checked_file(source_json_path, master["source_json_sha256"])
    source_role = json.loads(source_json_data)["roles"]["warrior_trainer"]
    binding = master["generated_source_provenance"]["lodge_static_binding"]
    require(source_role["provenance"]["lodge_static_binding"] == binding,
            "Garrosh lodge source JSON and static manifest disagree")
    require(source_role["provenance"]["view_records"] == master["generated_source_provenance"]["view_records"],
            "Garrosh source view geometry differs between manifests")
    world_data = checked_file(WORLD / "warrior_trainer/overworld.bin",
                              roles["warrior_trainer"]["output_sha256"], 1728)
    world_attrs = checked_file(WORLD / "warrior_trainer/attrs.bin",
                               roles["warrior_trainer"]["attrs_sha256"], 108)
    static = master["lodge_static_front"]
    require(source_path(static["packet"]) == LARGE_MASTERS / "warrior_trainer.bin",
            "Garrosh lodge packet changed path")
    static_data = checked_file(static["packet"], static["sha256"], 144)
    require(static["bytes"] == 144 and static_data == asset_data["warrior_trainer.bin"],
            "Garrosh lodge packet manifest SHA disagrees")

    def indices24(packet):
        require(len(packet) == 144, "Whole24x24 body requires nine tiles")
        result = np.zeros((24, 24), np.uint8)
        for tile in range(9):
            yy, xx = divmod(tile, 3)
            for row in range(8):
                lo, hi = packet[tile * 16 + row * 2:tile * 16 + row * 2 + 2]
                for column in range(8):
                    result[yy * 8 + row, xx * 8 + column] = ((lo >> (7 - column)) & 1) | (((hi >> (7 - column)) & 1) << 1)
        return result

    def row_indices(rows):
        require(len(rows) == 24 and all(len(row) == 24 and set(row) <= set(".123") for row in rows),
                "Garrosh source JSON must describe a whole24x24 cel")
        return np.asarray([[0 if cell == "." else int(cell) for cell in row] for row in rows], np.uint8)

    def native24(packet, attrs24, native_palettes):
        image = Image.new("RGBA", (24, 24))
        require(len(attrs24) == 9, "Garrosh complete native body needs nine palette attributes")
        for tile, palette_id in enumerate(attrs24):
            values = native_palettes[palette_id]
            # The dedicated Garrosh preview author uses rounded RGB555->RGB8
            # and transparent RGBA zero. The39-family strip importer instead
            # replicates high bits and retains white RGB under alpha0. Both
            # representations recover exactly the same native five-bit color;
            # match each format's documented renderer byte-for-byte.
            pal = [(0, 0, 0, 0) if index == 0 else
                   (*tuple(round(int(v) * 255 / 31) for v in rgb), 255)
                   for index, rgb in enumerate(values)]
            paint_tile(image, packet[tile * 16:(tile + 1) * 16], tile % 3 * 8, tile // 3 * 8, pal)
        return image

    require([crop["view"] for crop in master["crops"]] == ["front", "back", "left", "right"],
            "Garrosh must retain all four actual source views")
    covered = np.zeros(source_values.shape[:2], bool)
    source_alpha = {}
    for direction_index, crop in enumerate(master["crops"]):
        direction = crop["view"]
        component = crop["component_label"]
        ys, xs = np.nonzero(component_labels == component)
        measured = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
        require(measured == crop["source_bbox"] and int(len(xs)) == crop["alpha64_component_pixels"],
                "Garrosh crop is not the complete measured source component: " + direction)
        x0, y0, x1, y1 = measured
        covered[y0:y1, x0:x1] = True
        nearest = source_art.crop(tuple(measured))
        nearest.thumbnail((24, 24), Image.Resampling.NEAREST)
        offset = ((24 - nearest.width) // 2, 24 - nearest.height)
        require(list(nearest.size) == crop["body_dimensions"] and list(offset) == crop["target_offset"],
                "Garrosh native fitting changed or clips the full body")
        fitted = Image.new("RGBA", (24, 24))
        fitted.paste(nearest, offset)
        fitted_values = np.asarray(fitted).copy()
        fitted_values[:, :, 3] = np.where(fitted_values[:, :, 3] >= 128, 255, 0)
        source_alpha[direction] = fitted_values[:, :, 3] != 0
        preview = png(asset_data[f"garrosh_{direction}_source_nearest24.png"], (24, 24), rgba=True)
        require(np.array_equal(fitted_values, np.asarray(preview)),
                "Garrosh source preview differs from the full nearest source crop")
        view = next(entry for entry in master["generated_source_provenance"]["view_records"] if entry["view"] == direction)
        require(sha(fitted_values.tobytes()) == view["nearest24_rgba_sha256"],
                "Garrosh nearest-source RGBA hash differs")
        for pose in range(3):
            frame = direction_index * 3 + pose
            packet = world_data[frame * 144:(frame + 1) * 144]
            decoded_indices = indices24(packet)
            expected_rows = source_role["views"][direction] if pose == 0 else source_role.get("walk", {}).get(direction, [source_role["views"][direction]] * 2)[pose - 1]
            require(np.array_equal(decoded_indices, row_indices(expected_rows)),
                    "Garrosh world packet differs from its approved indexed source JSON")
            require(np.array_equal(decoded_indices != 0, source_alpha[direction]),
                    "Garrosh world packet dropped or added source body alpha")
            require(sha(decoded_indices.tobytes()) == view["native_indices_sha256"],
                    "Garrosh world index SHA differs from its own source conversion")
            frame_attrs = world_attrs[frame * 9:(frame + 1) * 9]
            require(list(frame_attrs) == source_role["attributes"][direction] == view["palette_attributes"],
                    "Garrosh world palette assignment differs from its own source conversion")
            if pose == 0:
                native = native24(packet, frame_attrs, palettes)
                declared = png(asset_data[f"garrosh_{direction}_world_native24.png"], (24, 24), rgba=True)
                require(native.tobytes() == declared.tobytes(),
                        "Garrosh world preview differs from its own packet/palette decode")
    require(not np.any((source_values[:, :, 3] >= 128) & ~covered),
            "Garrosh approved opaque source pixels fall outside the four complete crops")
    lodge_indices = indices24(static_data)
    world_front_indices = indices24(world_data[:144])
    require(np.array_equal(lodge_indices != 0, world_front_indices != 0)
            and np.array_equal(lodge_indices != 0, source_alpha["front"]),
            "Garrosh lodge/world front no longer preserve the complete approved source silhouette")
    require(np.array_equal(lodge_indices, row_indices(binding["lodge_front_rows"])),
            "Garrosh lodge palette-fit indices differ from their own approved source JSON")
    static_attrs = static["attributes"]
    require(static_attrs == binding["lodge_attrs"] and len(static_attrs) == 9
            and all(value in (3, 4) for value in static_attrs), "Garrosh lodge palette attributes differ")
    lodge_palettes = list(palettes)
    palette_asm = asset_data["palettes.asm"].decode()
    for palette_id in (3, 4):
        declared = binding[f"lodge_palette{palette_id}_rgb555"]
        match = re.search(r"PeonLargeMasterPalette" + str(palette_id) + r"V0213:\s*\n\s*RGB\s+([^\n]+)", palette_asm)
        require(match is not None, "Garrosh lodge palette is absent from compiled ASM")
        values = [int(value.strip()) for value in match.group(1).split(",")]
        require(values == [int(channel) for rgb in declared for channel in rgb],
                "Garrosh lodge palette ASM differs from its own manifest")
        lodge_palettes[palette_id] = declared
    lodge_native = native24(static_data, static_attrs, lodge_palettes)
    lodge_preview = png(asset_data["garrosh_master_native24.png"], (24, 24), rgba=True)
    require(lodge_native.tobytes() == lodge_preview.tobytes(),
            "Garrosh lodge preview differs from its independent packet/palette decode")
    rows = static["oam_rows"]
    require(len(rows) == 9 and [row[3] for row in rows] == list(range(9))
            and [(row[0], row[1]) for row in rows] == [(y, x) for y in (-8, 0, 8) for x in (-4, 4, 12)]
            and [row[2] & 7 for row in rows] == static_attrs,
            "Garrosh lodge facing is not the complete declared3x3 body")
    facing = asset_data["facings.asm"].decode()
    match = re.search(r"PeonLargeWarriorFacingV0213:(.*?)(?:\n[A-Za-z_][A-Za-z_0-9]*:|\Z)", facing, re.S)
    require(match is not None, "Garrosh lodge facing is absent from compiled ASM")
    declarations = re.findall(r"\bdb\s+([^\n]+)", match.group(1))
    parsed = [[int(token.strip()[1:], 16) if token.strip().startswith("$") else int(token.strip())
               for token in declaration.split(",")] for declaration in declarations]
    require(parsed == [[9], *rows], "Garrosh actual facing ASM differs from the nine-cell manifest")
    provenance["garrosh_lodge_world_verification"] = {
        "whole_source_alpha_preserved_in_all12_world_frames": True,
        "lodge_front_alpha_identical_to_world_and_complete_source": True,
        "independent_packet_SHA_JSON_indices_and_palette_RGBA_decodes_exact": True,
        "dedicated_Garrosh_PNG_RGB_renderer": "round(rgb555*255/31); transparent RGBA zero",
        "world_strip_PNG_RGB_renderer": "replicated high bits; palette RGB retained under alpha0",
        "all9_OAM_cells_and_actual_facing_ASM_exact": True,
        "lodge_and_world_indices_identical": np.array_equal(lodge_indices, world_front_indices),
        "different_indices_are_declared_palette_pool_conversion": True,
        "lodge_packet_sha256": sha(static_data), "world_front_packet_sha256": sha(world_data[:144])}
    provenance["large_master_files"].append(add(master_path, master_data))
    for name, data in sorted(asset_data.items()):
        provenance["large_master_files"].append(add(LARGE_MASTERS / name, data))
    provenance["source_files_rehashed_count"] = len(checked_sources)
    files["assets/world_source_provenance.json"] = json_bytes(provenance)
    return provenance


def collect_validation(validation_path, rom, sym, map_data, files):
    data = validation_path.read_bytes()
    validation = json.loads(data)
    require(passed(validation), "Packaging refused: final validation is not PASS")
    rom_hash = sha(rom)
    for name, payload in (("rom", rom), ("sym", sym), ("map", map_data)):
        require(validation.get(name + "_sha256") == sha(payload), "Final validation " + name + " SHA mismatch")
    require(validation.get("tests"), "No final tests declared")
    reports = []
    for name, test in validation["tests"].items():
        require(isinstance(name, str) and Path(name).name == name, "Unsafe report name")
        require(passed(test) and test.get("report"), "Incomplete test/report: " + name)
        report_data = source_path(test["report"]).read_bytes()
        report = json.loads(report_data)
        require(passed(report) and report.get("rom_sha256") == rom_hash, "Report is not PASS for this ROM: " + name)
        require(test.get("report_sha256", sha(report_data)) == sha(report_data), "Stale report hash: " + name)
        require(test.get("rom_sha256", rom_hash) == rom_hash, "Stale declared test ROM hash: " + name)
        target = "validation/" + name + ".json"
        require(target not in files, "Duplicate validation report")
        files[target] = report_data
        reports.append({"name": name, "path": target, "sha256": sha(report_data), "rom_sha256": rom_hash})
    files["validation/validation.json"] = data
    declared = list(validation.get("screenshots", {}).items())
    for number, item in enumerate(validation.get("captures", [])):
        entry = {"path": item} if isinstance(item, str) else item
        declared.append((entry.get("name", f"{number:02d}_" + Path(entry["path"]).name), entry))
    require(declared, "No explicit native runtime capture allowlist")
    captures = []
    for name, item in declared:
        entry = {"path": item} if isinstance(item, str) else item
        require(Path(name).name == name and name.endswith(".png"), "Unsafe runtime capture name")
        require(entry.get("rom_sha256", rom_hash) == rom_hash, "Stale capture ROM hash: " + name)
        path = source_path(entry["path"])
        payload = path.read_bytes()
        require(entry.get("sha256", sha(payload)) == sha(payload), "Stale capture hash: " + name)
        image = png(payload, (160, 144), opaque=True)
        target, enlarged = "runtime/" + name, "runtime/" + name[:-4] + "_4x.png"
        require(target not in files and enlarged not in files, "Duplicate runtime capture name")
        scaled = io.BytesIO()
        image.resize((640, 576), Image.Resampling.NEAREST).save(scaled, format="PNG")
        files[target], files[enlarged] = payload, scaled.getvalue()
        captures.append({"source": str(path), "path": target, "sha256": sha(payload),
            "rom_sha256": rom_hash, "dimensions": [160, 144], "opaque": True,
            "nearest_4x": enlarged, "nearest_4x_sha256": sha(scaled.getvalue())})
    files["runtime/manifest.json"] = json_bytes({"rom_sha256": rom_hash, "captures": captures})
    return validation, reports, captures


def verified_archive(files, rom_hash):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in sorted(files.items()):
            require(not Path(name).is_absolute() and ".." not in Path(name).parts, "Unsafe ZIP member")
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 15, 0, 0, 0))
            info.compress_type, info.create_system = zipfile.ZIP_DEFLATED, 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload, compresslevel=9)
    payload = buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        require(archive.testzip() is None, "ZIP CRC verification failed")
        require(len(archive.namelist()) == len(files) and set(archive.namelist()) == set(files), "ZIP members changed")
        for name, data in files.items():
            require(sha(archive.read(name)) == sha(data), "ZIP member SHA mismatch: " + name)
        require(sha(archive.read(BASE + ".gbc")) == rom_hash, "Embedded ROM SHA mismatch")
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("rom", "sym", "map", "validation-root"):
        parser.add_argument("--" + option, required=True, type=Path)
    args = parser.parse_args()
    rom, sym, map_data = args.rom.read_bytes(), args.sym.read_bytes(), args.map.read_bytes()
    rom_hash = sha(rom)
    require(len(rom) >= 0x150 and rom[0x143] & 0x80, "ROM is not marked Game Boy Color compatible")
    if (RELEASE / "manifest.json").is_file():
        previous = json.loads((RELEASE / "manifest.json").read_bytes())
        require(previous.get("rom_sha256") == rom_hash, "v0.2.19 already contains a different ROM")
    if (RELEASE / (BASE + ".gbc")).is_file():
        require(sha((RELEASE / (BASE + ".gbc")).read_bytes()) == rom_hash, "Existing v19 loose ROM differs")
    if (RELEASE / (BASE + ".zip")).is_file():
        with zipfile.ZipFile(RELEASE / (BASE + ".zip")) as old:
            require(sha(old.read(BASE + ".gbc")) == rom_hash, "Existing v19 ZIP contains a different ROM")
    files = {BASE + ".gbc": rom, BASE + ".sym": sym, BASE + ".map": map_data}
    validation_path = args.validation_root.resolve() / "validation.json"
    validation, reports, captures = collect_validation(validation_path, rom, sym, map_data, files)
    provenance = collect_assets(files)
    world_provenance = collect_world_assets(files, validation)
    files["README.md"] = (
        "# Peon of Warcraft v0.2.19\n\n"
        "Ouvrir peon_of_warcraft_v0_2_19.gbc dans un émulateur Game Boy Color ou sur ModRetro.\n\n"
        "Les trois maîtres ont des bustes illustrés de 80 × 88 pixels : Kento Tauren Shaman aux cornes "
        "corrigées, MoCMoc Zogzog inspiré de Garrosh (brun, chauve, armure et hache), "
        "Bismillah mort-vivant Démoniste. Ce sont des illustrations générées approuvées, "
        "converties avec perte par réduction au plus proche et palettes natives ; aucun "
        "lissage ni récupération d'une grille source n'est revendiqué. Les trois atlas "
        "de 2078 × 757 pixels restent intacts dans le dépôt ; chaque buste seul est importé entier.\n\n"
        "L'accueil illustré, ses quatre états de classe et ses libellés compacts restent "
        "les assets approuvés de v0.2.18. assets/native_selection/ contient sept PNG natifs "
        "statiques (quatre scènes et trois portraits), trois aperçus opaques et tous leurs "
        "paquets 2bpp, cartes, attributs et palettes. Ces images sont des revues d'import, "
        "pas des captures du jeu. Les grands PNG sources sont revérifiés par SHA256 mais "
        "ne sont pas dupliqués dans le ZIP ; assets/source_provenance.json les documente.\n\n"
        "Les personnages du monde restaurent les silhouettes natives historiques et "
        "les vues sources disponibles. Le passage de 16 à 24 pixels au plus proche rend ces dessins "
        "plus grands sans inventer du détail. Le maître Guerrier du monde suit l'aspect "
        "Garrosh brun/chauve ; le Guerrier du joueur reste distinct. Les conversions, "
        "retouches locales déclarées et cas sans source dédiée sont documentés dans les "
        "manifestes et JSON de provenance. assets/native_world/ contient les 39 familles "
        "et leurs 117 paquets, dont 30 familles et 90 paquets liés au moteur, plus leurs strips "
        "statiques de 96 × 72 pixels. Les palettes et facings du maître Garrosh sont fournis séparément. "
        "Les graphismes de combat et le gameplay existant sont préservés.\n\n"
        "runtime/ contient uniquement les captures de 160 × 144 pixels de cette ROM figurant dans "
        "l'allowlist des tests, et leurs copies 4× sans lissage. validation/ conserve les "
        "rapports PASS liés au SHA256 exact de la ROM, du SYM et du MAP. Le matériel "
        "physique ModRetro n'a pas été testé.\n\n"
        "ZIP déterministe : noms triés, date 2026-10-15 et compression fixes. Tous les membres "
        "sont relus avec CRC/SHA256 ; la ROM embarquée est identique au fichier fourni. "
        "SHA256SUMS.txt couvre les contenus hors manifest. Le manifest externe et .zip.sha256 "
        "fournissent le hash du ZIP sans hash autoréférentiel.\n"
    ).encode()

    manifest = {"version": VERSION, "rom": BASE + ".gbc", "rom_sha256": rom_hash,
        "sym_sha256": sha(sym), "map_sha256": sha(map_data),
        "validation_sha256": sha(validation_path.read_bytes()), "tests": reports,
        "physical_modretro_tested": False, "runtime": captures,
        "static_primary_native_PNGs": provenance["primary_static_PNGs"],
        "opaque_portrait_previews": provenance["opaque_portrait_previews"],
        "source_provenance": "assets/source_provenance.json",
        "world_source_provenance": "assets/world_source_provenance.json",
        "world_asset_contract": world_provenance["contract"],
        "world_native_packet_files": world_provenance["world_packet_files"],
        "world_static_PNGs": world_provenance["world_static_PNGs"],
        "files": {name: {"sha256": sha(data), "bytes": len(data)} for name, data in sorted(files.items())}}
    files["manifest.json"] = json_bytes(manifest)
    files["SHA256SUMS.txt"] = "".join(f"{sha(data)}  {name}\n" for name, data in sorted(files.items())
                                      if name != "manifest.json").encode()
    archive = verified_archive(files, rom_hash)
    archive_hash = sha(archive)
    # No output path is created before every source, proof and archive check.
    RELEASE.mkdir(parents=True, exist_ok=True)
    for name, payload in files.items():
        if name == "manifest.json":
            continue
        target = RELEASE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    (RELEASE / (BASE + ".zip")).write_bytes(archive)
    manifest.update({"zip_sha256": archive_hash, "zip_bytes": len(archive),
                     "zip_crc_and_all_payload_sha256": "PASS"})
    (RELEASE / "manifest.json").write_bytes(json_bytes(manifest))
    (RELEASE / (BASE + ".zip.sha256")).write_text(f"{archive_hash}  {BASE}.zip\n")
    print(json.dumps({"status": "PASS", "rom_sha256": rom_hash, "zip_sha256": archive_hash,
        "runtime_captures": len(captures), "primary_static_PNGs": 7, "opaque_portrait_previews": 3,
        "native_packet_files": len(provenance["native_packet_files"]), "release": str(RELEASE)}, indent=2))


if __name__ == "__main__":
    main()
