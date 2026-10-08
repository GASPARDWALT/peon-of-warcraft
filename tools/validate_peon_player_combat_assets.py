#!/usr/bin/env python3
"""Audit authored v0.2.3 player combat assets without building or editing the ROM.

Decode actual column-major tiles, compile the indexed native PNGs independently
with rgbgfx in a temporary directory, and inspect public PNG/APNG/GIF pixels.
The separate generated concept reference is deliberately outside this audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "gfx/peon_player_battle"
PUBLIC = ROOT / "references/generated/durotar_v023/player_combat"
NAMES = ("idle", "brace", "swing")
LEGACY_HASHES = {
    "gfx/pokemon/machop/back.png": "876ba18a36e539c0c82cfc8393c531cb71a844567875f903ebe69881afae4377",
    "gfx/pokemon/machop/back.2bpp": "2bb88d79fcae635f4673ed6fe115ee78bebdc532ef556bfecf8b0020aadc9024",
    "gfx/pokemon/machop/normal.gbcpal": "7abf96acd03f905a34b086a54ab11a015f75425f03e5b8a2c435148891971791",
    "gfx/pokemon/machop/back.gbcpal": "7abf96acd03f905a34b086a54ab11a015f75425f03e5b8a2c435148891971791",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode_column_major(binary: bytes) -> np.ndarray:
    """Decode 36 tiles: native GetMonBackpic expects tx outer, ty inner."""
    if len(binary) != 576:
        raise ValueError(f"48x48 frame requires 576 bytes, got {len(binary)}")
    indices = np.zeros((48, 48), dtype=np.uint8)
    for tile_number in range(36):
        tx, ty = divmod(tile_number, 6)
        for y in range(8):
            lo, hi = binary[tile_number * 16 + y * 2:tile_number * 16 + y * 2 + 2]
            for x in range(8):
                bit = 7 - x
                indices[ty * 8 + y, tx * 8 + x] = ((lo >> bit) & 1) | (((hi >> bit) & 1) << 1)
    return indices


def read_palette(binary: bytes) -> list[list[int]]:
    if len(binary) != 8:
        raise ValueError("A four-colour RGB555 palette must contain 8 bytes")
    words = [int.from_bytes(binary[i:i + 2], "little") for i in range(0, 8, 2)]
    if any(word & 0x8000 for word in words):
        raise ValueError("RGB555 palette contains a set reserved high bit")
    return [[word & 31, (word >> 5) & 31, (word >> 10) & 31] for word in words]


def public_pixels(indices: np.ndarray, palette: list[list[int]]) -> np.ndarray:
    pixels = np.zeros((*indices.shape, 4), dtype=np.uint8)
    for colour in (1, 2, 3):
        pixels[indices == colour, :3] = np.asarray(palette[colour]) * 8
        pixels[indices == colour, 3] = 255
    return pixels


def enlarged(pixels: np.ndarray, scale: int = 8) -> np.ndarray:
    return pixels.repeat(scale, axis=0).repeat(scale, axis=1)


def on_canvas(pixels: np.ndarray) -> np.ndarray:
    result = np.full(pixels.shape, 255, dtype=np.uint8)
    result[:, :, :3] = (245, 237, 213)
    opaque = pixels[:, :, 3] != 0
    result[opaque, :3] = pixels[opaque, :3]
    return result


def opaque_component_sizes(indices: np.ndarray) -> list[int]:
    """Measure the rendered silhouette, including isolated one-pixel fragments."""
    remaining = set(zip(*np.nonzero(indices != 0)))
    sizes = []
    while remaining:
        stack = [remaining.pop()]
        size = 0
        while stack:
            y, x = stack.pop()
            size += 1
            for neighbour in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    stack.append(neighbour)
        sizes.append(size)
    return sorted(sizes, reverse=True)


class Audit:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def require(self, name: str, passed: bool, **details) -> None:
        self.checks.append({"check": name, "passed": bool(passed), **details})

    def image(self, path: Path, expected: np.ndarray, rgba: bool = True) -> None:
        with Image.open(path) as image:
            self.require(f"{path.name}: dimensions", image.size == (expected.shape[1], expected.shape[0]),
                         actual_size=list(image.size))
            if rgba:
                self.require(f"{path.name}: RGBA", image.mode == "RGBA", actual_mode=image.mode)
            actual = np.asarray(image.convert("RGBA"))
            same_size = actual.shape == expected.shape
            self.require(f"{path.name}: actual pixels", same_size and np.array_equal(actual, expected),
                         differing_pixels=int(np.count_nonzero(np.any(actual != expected, axis=2))) if same_size else None)

    def animation(self, path: Path, expected: list[np.ndarray], durations: list[int], alpha: bool) -> None:
        with Image.open(path) as animation:
            self.require(f"{path.name}: five-frame loop", animation.n_frames == len(expected) and animation.info.get("loop") == 0,
                         actual_frames=animation.n_frames, loop=animation.info.get("loop"))
            for number in range(min(animation.n_frames, len(expected))):
                animation.seek(number)
                actual = np.asarray(animation.convert("RGBA"))
                wanted = expected[number]
                same_size = actual.shape == wanted.shape
                self.require(f"{path.name}: frame {number} pixels", same_size and np.array_equal(actual, wanted),
                             differing_pixels=int(np.count_nonzero(np.any(actual != wanted, axis=2))) if same_size else None)
                self.require(f"{path.name}: frame {number} timing", animation.info.get("duration") == durations[number],
                             duration_ms=animation.info.get("duration"))
                if alpha:
                    values = sorted(int(n) for n in np.unique(actual[:, :, 3]))
                    self.require(f"{path.name}: frame {number} binary alpha", values == [0, 255], actual_values=values)


def run(rgbgfx: Path, report: dict, audit: Audit) -> None:
    manifest = json.loads((PUBLIC / "asset_manifest.json").read_text())
    palette_binary = (NATIVE / "back_frames.gbcpal").read_bytes()
    palette = read_palette(palette_binary)
    report["rgb555_palette"] = palette
    audit.require("runtime palette retained exactly", palette_binary == (ROOT / "gfx/pokemon/machop/normal.gbcpal").read_bytes()
                  == (ROOT / "gfx/pokemon/machop/back.gbcpal").read_bytes())
    audit.require("manifest palette", manifest["rgb555_palette"] == palette)
    audit.require("manifest source", manifest["source"] == "gfx/pokemon/machop/back.png"
                  and manifest["source_sha256"] == sha256(ROOT / manifest["source"]))
    audit.require("manifest native binary", manifest["native_binary"] == "gfx/peon_player_battle/back_frames.2bpp")
    audit.require("manifest native layout", manifest["size"] == [48, 48] and manifest["bytes_per_frame"] == 576
                  and manifest["total_bytes"] == 1728 and manifest["tile_order"] == "column-major, tx outer then ty")
    packed = (NATIVE / "back_frames.2bpp").read_bytes()
    audit.require("packed three-frame length", len(packed) == 1728, actual_bytes=len(packed))
    old_binary = (ROOT / "gfx/pokemon/machop/back.2bpp").read_bytes()
    old_indices = decode_column_major(old_binary)
    with Image.open(ROOT / "gfx/pokemon/machop/back.png") as image:
        source_rgb555 = np.asarray(image.convert("RGB")) >> 3
        source_indices = np.asarray(image)
    palette_values = np.asarray(palette)
    matches = np.all(source_rgb555[:, :, None, :] == palette_values, axis=3)
    audit.require("legacy PNG has exact runtime RGB555 colours", np.all(matches.sum(axis=2) == 1))
    canonical_legacy = matches.argmax(axis=2).astype(np.uint8)
    audit.require("legacy PNG colours decode to old column-major tiles", np.array_equal(canonical_legacy, old_indices))
    report["legacy_png_index_to_runtime_index"] = {
        str(int(index)): sorted(int(n) for n in np.unique(canonical_legacy[source_indices == index]))
        for index in np.unique(source_indices)
    }
    frames, public, binaries = [], [], []
    report["frames"] = []
    report["rgbgfx"] = {"executable": str(rgbgfx), "temporary_compilations_only": True}
    with tempfile.TemporaryDirectory(prefix="peon-combat-assets-") as temporary:
        for number, name in enumerate(NAMES):
            png = NATIVE / f"back_{name}.png"
            binary_path = NATIVE / f"back_{name}.2bpp"
            binary = binary_path.read_bytes()
            binaries.append(binary)
            indices = decode_column_major(binary)
            with Image.open(png) as image:
                audit.require(f"{name}: native indexed PNG", image.mode == "P" and image.size == (48, 48)
                              and "transparency" not in image.info, actual_mode=image.mode, actual_size=list(image.size))
                audit.require(f"{name}: DMG palette", image.getpalette()[:12] == [255, 255, 255, 170, 170, 170, 85, 85, 85, 0, 0, 0])
                png_indices = np.asarray(image)
            audit.require(f"{name}: native PNG indices 0..3", sorted(int(n) for n in np.unique(png_indices)) == [0, 1, 2, 3])
            audit.require(f"{name}: actual column-major decode", np.array_equal(indices, png_indices))
            compiled_path = Path(temporary) / f"{name}.2bpp"
            command = [str(rgbgfx), "--columns", "--colors", "dmg", "-Weverything", "-o", str(compiled_path), str(png)]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            compiled_equal = result.returncode == 0 and compiled_path.is_file() and compiled_path.read_bytes() == binary
            audit.require(f"{name}: independent rgbgfx byte equality", compiled_equal, returncode=result.returncode,
                          stderr=result.stderr.strip(), flags=["--columns", "--colors", "dmg", "-Weverything"])
            audit.require(f"{name}: packed frame offset", packed[number * 576:(number + 1) * 576] == binary)
            expected = public_pixels(indices, palette)
            public.append(expected)
            public_path = PUBLIC / f"peon_back_{name}_48x48.png"
            audit.image(public_path, expected)
            with Image.open(public_path) as image:
                pixels = np.asarray(image.convert("RGBA"))
            colours = sorted(set(tuple(int(n) for n in rgb) for rgb in pixels[pixels[:, :, 3] == 255, :3]))
            alpha = sorted(int(n) for n in np.unique(pixels[:, :, 3]))
            audit.require(f"{name}: binary transparency", alpha == [0, 255], actual_values=alpha)
            audit.require(f"{name}: three opaque RGB555 colours", len(colours) == 3 and all(all(n % 8 == 0 for n in rgb) for rgb in colours),
                          opaque_rgb888_colours=colours)
            audit.image(PUBLIC / f"peon_back_{name}_8x.png", enlarged(expected))
            changed = indices != old_indices
            silhouette = (indices != 0) != (old_indices != 0)
            changed_tiles = sum(bool(np.any(changed[y:y + 8, x:x + 8])) for x in range(0, 48, 8) for y in range(0, 48, 8))
            ys, xs = np.nonzero(indices != 0)
            component_sizes = opaque_component_sizes(indices)
            metrics = {
                "name": name, "tile_bytes": len(binary), "frame_offset": number * 576,
                "png_sha256": sha256(png), "binary_sha256": sha256(binary_path),
                "public_png_sha256": sha256(public_path),
                "changed_pixels_from_idle": int(changed.sum()),
                "changed_silhouette_pixels": int(silhouette.sum()),
                "changed_tiles_from_idle": changed_tiles,
                "changed_left_arm_pixels": int(changed[8:36, 0:24].sum()),
                "changed_torso_pixels": int(changed[14:32, 12:40].sum()),
                "changed_pixels_row_41": int(changed[41].sum()),
                "changed_foot_pixels_rows_42_through_47": int(changed[42:].sum()),
                "opaque_bbox_exclusive": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
                "foot_baseline_y": int(ys.max()),
                "connected_component_count": len(component_sizes),
                "connected_component_sizes_4_neighbours": component_sizes,
            }
            report["frames"].append(metrics)
            audit.require(f"{name}: feet retain position and pixels", not changed[42:].any() and int(ys.max()) == 47)
            audit.require(f"{name}: no detached opaque fragments", len(component_sizes) == 1,
                          connected_component_sizes_4_neighbours=component_sizes)
            if name == "idle":
                audit.require("idle byte-identical to existing player backpic", binary == old_binary)
            else:
                audit.require(f"{name}: meaningful arm and torso pose", metrics["changed_pixels_from_idle"] >= 128
                              and metrics["changed_silhouette_pixels"] >= 16 and changed_tiles >= 8
                              and metrics["changed_left_arm_pixels"] >= 64 and metrics["changed_torso_pixels"] >= 16,
                              thresholds={"changed_pixels": 128, "silhouette": 16, "tiles": 8, "left_arm": 64, "torso": 16})
            declared = manifest["frames"][number]
            audit.require(f"{name}: manifest metrics match actual pixels", all(declared[key] == metrics[key] for key in
                          ("name", "changed_pixels_from_idle", "changed_silhouette_pixels", "tile_bytes", "frame_offset")))
            frames.append(indices)
    audit.require("combined bytes equal separate binaries", packed == b"".join(binaries))
    audit.require("manifest idle preservation", manifest["idle_matches_current_backpic"] is True and binaries[0] == old_binary)
    audit.require("brace and swing are different poses", int(np.count_nonzero(frames[1] != frames[2])) >= 128
                  and int(np.count_nonzero((frames[1] != 0) != (frames[2] != 0))) >= 16)
    sheet = np.concatenate(public, axis=1)
    audit.image(PUBLIC / "peon_back_three_pose_sheet_144x48.png", sheet)
    audit.image(PUBLIC / "peon_back_three_pose_sheet_8x.png", enlarged(sheet))
    audit.image(PUBLIC / "peon_back_three_pose_sheet_display_8x.png", on_canvas(enlarged(sheet)), rgba=False)
    sequence = [public[i] for i in (0, 1, 2, 1, 0)]
    large_sequence = [enlarged(frame) for frame in sequence]
    durations = [320, 160, 160, 120, 320]
    audit.animation(PUBLIC / "peon_back_three_pose_preview.apng", sequence, durations, alpha=True)
    audit.animation(PUBLIC / "peon_back_three_pose_preview_8x.apng", large_sequence, durations, alpha=True)
    audit.animation(PUBLIC / "peon_back_three_pose_preview_8x.gif", [on_canvas(frame) for frame in large_sequence], durations, alpha=False)
    report["assets"] = {
        "source_png_sha256": sha256(ROOT / "gfx/pokemon/machop/back.png"),
        "source_2bpp_sha256": sha256(ROOT / "gfx/pokemon/machop/back.2bpp"),
        "combined_2bpp_sha256": sha256(NATIVE / "back_frames.2bpp"),
        "combined_palette_sha256": sha256(NATIVE / "back_frames.gbcpal"),
        "manifest_sha256": sha256(PUBLIC / "asset_manifest.json"),
    }
    report["foot_baseline_note"] = "Rows 42–47 and baseline y=47 are identical. Swing changes 9 pixels on row 41 where the shield lowers; these are outside the protected feet."


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rgbgfx", type=Path, default=Path(shutil.which("rgbgfx") or "/workspace/toolchains/rgbds-1.0.4/rgbgfx"))
    args = parser.parse_args()
    audit = Audit()
    report = {
        "scope": "v0.2.3 native player combat assets; no ROM build or engine integration test",
        "rom_build_performed": False,
        "runtime_animation_verified": False,
        "excluded_non_native_concept": "peon_back_pose_concept_original.png",
        "limitations": ["This report verifies prepared assets, not installation or playback inside the ROM.",
                        "GIF and display sheet use an opaque presentation canvas; native PNG and APNG have binary transparency."],
    }
    protected_before = {path: sha256(ROOT / path) for path in LEGACY_HASHES}
    rom = ROOT / "pokecrystal.gbc"
    rom_before = sha256(rom) if rom.exists() else None
    report["rom_sha256_at_audit_start"] = rom_before
    try:
        for path, expected in LEGACY_HASHES.items():
            audit.require(f"v0.2.2 legacy input preserved: {path}", protected_before[path] == expected,
                          expected_sha256=expected, actual_sha256=protected_before[path])
        run(args.rgbgfx, report, audit)
    except Exception as error:
        audit.require("audit completed without exception", False, error_type=type(error).__name__, error=str(error))
    protected_after = {path: sha256(ROOT / path) for path in LEGACY_HASHES}
    audit.require("legacy player files unchanged during audit", protected_before == protected_after)
    rom_after = sha256(rom) if rom.exists() else None
    report["rom_sha256_at_audit_end"] = rom_after
    report["rom_file_unchanged_during_audit"] = rom_before == rom_after
    # ROM compilation may happen concurrently in another agent; record this,
    # while checking immutable art inputs independently of integration work.
    report["checks"] = audit.checks
    report["all_checks_passed"] = all(check["passed"] for check in audit.checks)
    report_path = PUBLIC / "asset_validation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    failures = [check for check in audit.checks if not check["passed"]]
    print(json.dumps({"all_checks_passed": report["all_checks_passed"], "checks": len(audit.checks),
                      "failed_checks": failures, "report": str(report_path.relative_to(ROOT)),
                      "combined_2bpp_sha256": report.get("assets", {}).get("combined_2bpp_sha256")}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
