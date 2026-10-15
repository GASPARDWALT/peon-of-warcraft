#!/usr/bin/env python3
"""Import existing native master portraits without resizing or drawing pixels.

The historical 64x68 authored PNGs are source artwork, not recovered user
pixels. Five BG palettes are fitted per portrait; index0 is the shared panel
background and may also represent opaque ink. Source alpha is retained in
review PNGs separately, because the actual BG is opaque. The caller adds the
VRAM-bank1 attribute bit to the emitted palette IDs3..7.
"""
from __future__ import annotations

import argparse
import hashlib
from itertools import combinations
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "references/generated/peon_sprite_redesign_v030/selection"
GFX = ROOT / "gfx/class_portraits_v0218"
REVIEW = ROOT / "references/generated/class_selection_v0218"
BACKGROUND = (3, 2, 3)
PALETTE_IDS = (3, 4, 5, 6, 7)
SOURCES = {
    "kento": SOURCE / "master_kento_portrait_64x68.png",
    "zogzog": SOURCE / "master_zogzog_portrait_64x68.png",
    "bismillah": SOURCE / "master_xasthur_portrait_64x68.png",
}
SOURCE_DIGESTS = {
    "kento": "3cda83e0b4bb98272ee1f3ed274d8b092e791166b9e93e3a3205fc23babf5d3f",
    "zogzog": "360ac75d785407a2a7befd2e4e92f6b7bde6057b3db0ff71b5d14cd9e2d4e1bb",
    "bismillah": "99fdca7ee482fa323e11e0bb8700d48fcbbb292e031fb4ca46f63216082c5c26",
}
NAMES = {"kento": "Kento Brandenhoof", "zogzog": "MoCMoc Zogzog",
         "bismillah": "Bismillah LesTenèbres"}
FOCUS = {
    "kento": ((18, 21, 46, 42, 3.0), (22, 24, 43, 28, 7.0),
              (0, 0, 24, 23, 2.5), (40, 0, 64, 23, 2.5)),
    "zogzog": ((18, 13, 46, 39, 3.0), (22, 22, 43, 26, 8.0),
               (22, 28, 43, 37, 5.0)),
    "bismillah": ((22, 22, 41, 42, 3.5), (24, 27, 40, 31, 8.0)),
}
PROTECTED_PALETTES = {
    # Source material families keep rare profession/face colors from being
    # discarded by a global mean-error fit dominated by large flat regions.
    # Every entry is an actual source color; these alter no source geometry.
    "kento": (
        ((11, 7, 4), (23, 8, 8), (30, 28, 22)),  # eyes, brows, eye glints
        ((6, 4, 3), (11, 7, 4), (17, 12, 7)),  # layered brown fur
        ((17, 12, 7), (26, 22, 15), (30, 28, 22)),  # ivory horns/muzzle
        ((4, 6, 9), (7, 11, 15), (13, 19, 20)),  # blue woven cloth
        ((9, 4, 5), (16, 5, 7), (22, 15, 7)),  # braids/gold bindings
    ),
    "zogzog": (
        ((9, 14, 7), (16, 20, 9), (23, 8, 8)),  # skin and red irises
        ((9, 14, 7), (16, 20, 9), (30, 28, 22)),  # skin and ivory tusks
        ((8, 9, 10), (9, 4, 5), (16, 5, 7)),  # red shoulder armor
        ((5, 5, 6), (8, 9, 10), (15, 15, 17)),  # beard/iron shading
        ((8, 9, 10), (22, 15, 7), (23, 24, 25)),  # metal highlights/buckle
    ),
    "bismillah": (
        ((7, 9, 9), (12, 16, 14), (20, 22, 19)),  # undead face/hands
        ((6, 4, 8), (11, 7, 13), (17, 11, 19)),  # purple robe folds
        ((11, 7, 13), (22, 15, 7), (30, 28, 22)),  # hood rim/shoulders
        ((11, 7, 4), (26, 22, 15), (30, 28, 22)),  # staff/bone skull
        ((16, 20, 9), (17, 11, 19), (22, 15, 7)),  # green charm/cloth
    ),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def expand(colors):
    values = np.asarray(colors, dtype=np.uint8)
    return (values << 3) | (values >> 2)


def material(color):
    r, g, b = map(int, color)
    if max(r, g, b) <= 3:
        return "ink"
    if r >= 23 and g >= 20 and b >= 13 and r >= g and g > b + 1:
        return "bone"
    if g > r + 1 and g > b + 1 and r + g + b >= 14:
        return "green"
    if b > g + 1 and r > g + 1:
        return "purple"
    if b > r + 2 and g > r + 1:
        return "blue"
    if r > g * 1.5 and r > b * 1.3 and r >= 7 and b >= g:
        return "red"
    if max(r, g, b) - min(r, g, b) <= 5:
        return "steel"
    if r > g and g > b:
        return "leather"
    return "neutral"


def distance_table(colors):
    """Prefer source material hues over numerically close unrelated materials."""
    delta = colors[:, None, :].astype(float) - colors[None, :, :]
    errors = (delta * delta * np.array([0.95, 1.15, 0.9])).sum(2)
    kinds = [material(color) for color in colors]
    for source, kind in enumerate(kinds):
        for target, other in enumerate(kinds):
            if kind != other and kind in ("ink", "bone", "green", "purple", "blue", "red", "steel", "leather"):
                errors[source, target] += {"ink": 600, "bone": 130,
                                          "green": 180, "purple": 95,
                                          "blue": 80, "red": 85,
                                          "steel": 160, "leather": 180}[kind]
    return errors


def fit_palettes(rgba, role):
    rgb = rgba[:, :, :3] >> 3
    visible = rgba[:, :, 3] != 0
    colors, inverse = np.unique(rgb[visible], axis=0, return_inverse=True)
    assert len(colors) >= 3, (role, "At least three opaque source colors expected")
    assert len(colors) <= 40, (role, "Review a source with more than40 native colors before palette fitting")
    indices = np.zeros(visible.shape, dtype=np.uint8)
    indices[visible] = inverse
    weight = np.ones(visible.shape, dtype=float)
    # Source boundaries and contrasting one-pixel marks outweigh flat shading.
    for dy, dx in ((0, 1), (1, 0)):
        a, b = rgb[:rgb.shape[0] - dy or None, :rgb.shape[1] - dx or None], rgb[dy:, dx:]
        both = visible[:visible.shape[0] - dy or None, :visible.shape[1] - dx or None] & visible[dy:, dx:]
        edge = np.minimum(2, np.sqrt(((a.astype(float) - b) ** 2).sum(2)) / 9) * both
        weight[:weight.shape[0] - dy or None, :weight.shape[1] - dx or None] += edge
        weight[dy:, dx:] += edge
    for x0, y0, x1, y1, emphasis in FOCUS.get(role, ()):
        weight[y0:y1, x0:x1] *= emphasis
    weight[visible & (rgb.sum(2) <= 15)] *= 2.0
    tiles, histograms = [], []
    for y in range(0, rgba.shape[0], 8):
        for x in range(0, rgba.shape[1], 8):
            mask = visible[y:y + 8, x:x + 8]
            values = indices[y:y + 8, x:x + 8]
            histograms.append(np.bincount(values[mask], weights=weight[y:y + 8, x:x + 8][mask],
                                          minlength=len(colors)))
            tiles.append((y, x))
    # BG index0 is opaque, so its dark panel shade can also serve as ink.
    # Keep the source alpha independently rather than wasting a fourth color
    # on an almost identical dark source outline in every hardware palette.
    options = np.asarray(list(combinations(
        [index for index, color in enumerate(colors) if material(color) != "ink"], 3)), dtype=np.int16)
    all_colors = np.concatenate((colors, np.asarray([BACKGROUND], dtype=np.uint8)))
    distances = distance_table(all_colors)[:len(colors)]
    costs = np.minimum(distances[:, options].min(2), distances[:, -1, None])
    errors = np.asarray(histograms) @ costs
    fixed = []
    for required in PROTECTED_PALETTES.get(role, ()):
        required_ids = sorted(next(index for index, color in enumerate(colors)
                                   if tuple(map(int, color)) == wanted) for wanted in required)
        fixed.append(next(index for index, option in enumerate(options)
                          if list(option) == required_ids))
    chosen = list(fixed) or [int(errors.sum(0).argmin())]
    while len(chosen) < min(5, len(options)):
        candidate_scores = np.minimum(errors, errors[:, chosen].min(1)[:, None]).sum(0)
        candidate_scores[chosen] = np.inf
        chosen.append(int(candidate_scores.argmin()))
    for _ in range(5):
        changed = False
        for slot in range(len(fixed), len(chosen)):
            others = chosen[:slot] + chosen[slot + 1:]
            if not others:
                continue
            scores = np.minimum(errors, errors[:, others].min(1)[:, None]).sum(0)
            scores[others] = np.inf
            candidate = int(scores.argmin())
            if candidate != chosen[slot]:
                chosen[slot] = candidate
                changed = True
        if not changed:
            break
    while len(chosen) < 5:
        chosen.append(chosen[-1])
    palettes = np.asarray([[BACKGROUND, *colors[options[option]].tolist()]
                           for option in chosen], dtype=np.uint8)
    assignment = errors[:, chosen].argmin(1)
    if role == "kento":
        eye_mask = np.zeros(visible.shape, dtype=bool)
        eye_mask[24:28, 22:43] = True
        eye_mask &= (rgb == (23, 8, 8)).all(2) & visible
        for number, (y, x) in enumerate(tiles):
            if eye_mask[y:y + 8, x:x + 8].any():
                assignment[number] = 0
            # The small cool-gray carved shoulder stones share a tile with
            # braid bindings. Prefer the cool cloth/stone family over tinting
            # their larger surface brown to fit those few gold bindings.
            if y == 40 and x in (8, 48):
                assignment[number] = 3
    indexed = np.zeros(visible.shape, dtype=np.uint8)
    decoded = np.zeros((*visible.shape, 4), dtype=np.uint8)
    decoded[:, :, :3] = expand(BACKGROUND)
    decoded[:, :, 3] = rgba[:, :, 3]
    tile_records = []
    for number, ((y, x), palette) in enumerate(zip(tiles, assignment)):
        mask = visible[y:y + 8, x:x + 8]
        source_ids = indices[y:y + 8, x:x + 8]
        palette_indices = np.asarray([len(colors), *options[chosen[palette]]])
        selection = distances[source_ids[..., None], palette_indices].argmin(2)
        selection[~mask] = 0
        indexed[y:y + 8, x:x + 8] = selection
        decoded[y:y + 8, x:x + 8, :3] = expand(palettes[palette][selection])
        before = rgb[y:y + 8, x:x + 8][mask]
        after = palettes[palette][selection][mask]
        exact = int(np.count_nonzero((before == after).all(1)))
        tile_records.append({"tile": number, "xy": [x, y], "palette_id": int(palette) + 3,
                             "source_opaque_colors": len(np.unique(before, axis=0)),
                             "native_opaque_colors": len(np.unique(after, axis=0)),
                             "opaque_pixels": int(mask.sum()), "exact_rgb555_pixels": exact,
                             "opaque_source_pixels_using_background_ink": int(np.count_nonzero(mask & (selection == 0)))})
    assert np.array_equal(decoded[:, :, 3], rgba[:, :, 3]), (role, "Source alpha geometry changed")
    return indexed, decoded, palettes, assignment.astype(np.uint8) + 3, tile_records


def encode(indexed):
    packet = bytearray()
    for y in range(0, indexed.shape[0], 8):
        for x in range(0, indexed.shape[1], 8):
            for row in indexed[y:y + 8, x:x + 8]:
                packet.extend((sum((int(value) & 1) << (7 - bit) for bit, value in enumerate(row)),
                               sum((int(value) >> 1) << (7 - bit) for bit, value in enumerate(row))))
    return bytes(packet)


def decode(packet, dimensions):
    width, height = dimensions
    values = np.zeros((height, width), dtype=np.uint8)
    for tile in range(width // 8 * (height // 8)):
        y, x = divmod(tile, width // 8)
        for row in range(8):
            lo, hi = packet[tile * 16 + row * 2:tile * 16 + row * 2 + 2]
            for column in range(8):
                values[y * 8 + row, x * 8 + column] = ((lo >> (7 - column)) & 1) | (((hi >> (7 - column)) & 1) << 1)
    return values


def region_metrics(source, decoded, box):
    x0, y0, x1, y1 = box
    before, after = source[y0:y1, x0:x1], decoded[y0:y1, x0:x1]
    visible = before[:, :, 3] != 0
    a, b = before[:, :, :3][visible] >> 3, after[:, :, :3][visible] >> 3
    source_materials, native_materials = {}, {}
    for colors, result in ((a, source_materials), (b, native_materials)):
        for color in colors:
            name = material(color)
            result[name] = result.get(name, 0) + 1
    return {"box": list(box), "opaque_pixels": int(visible.sum()),
            "exact_rgb555_pixels": int((a == b).all(1).sum()),
            "rgb555_rmse": round(float(np.sqrt(((a.astype(float) - b) ** 2).mean())), 3),
            "source_material_pixels": source_materials, "native_material_pixels": native_materials}


def convert_source(path: Path, role: str, padded_size=(64, 72)):
    """Import a native cel at origin0,0; padded_size is (width,height), no scaling.

    Returns metadata and ASM lines. This entry point also accepts a future
    native Peon portrait that fits the same72-tile canvas.
    """
    path = Path(path).resolve()
    payload = path.read_bytes()
    if role in SOURCE_DIGESTS:
        assert sha(payload) == SOURCE_DIGESTS[role], (role, "Historical portrait source changed")
    original = Image.open(path).convert("RGBA")
    assert original.width <= padded_size[0] and original.height <= padded_size[1]
    assert padded_size == (64, 72), "Runtime portrait ABI requires64x72"
    assert set(original.getchannel("A").get_flattened_data()) <= {0, 255}
    source = Image.new("RGBA", padded_size)
    source.paste(original, (0, 0))
    rgba = np.asarray(source)
    indexed, decoded, palettes, attrs, tile_records = fit_palettes(rgba, role)
    packet = encode(indexed)
    assert len(packet) == 1152 and np.array_equal(decode(packet, padded_size), indexed)
    assert len(attrs) == 72 and set(map(int, attrs)) <= set(PALETTE_IDS)
    palette_data = b"".join(int(r | (g << 5) | (b << 10)).to_bytes(2, "little")
                            for r, g, b in palettes.reshape((-1, 3)).tolist())
    assert len(palette_data) == 40
    folder, review = GFX / role, REVIEW / role
    folder.mkdir(parents=True, exist_ok=True)
    review.mkdir(parents=True, exist_ok=True)
    (folder / "portrait.2bpp").write_bytes(packet)
    (folder / "attrs.bin").write_bytes(attrs.tobytes())
    (folder / "palettes.bin").write_bytes(palette_data)
    source.save(review / "source_padded.png")
    hardware = Image.fromarray(decoded)
    hardware.save(folder / "hardware.png")
    hardware.save(review / "hardware.png")
    background = Image.new("RGBA", padded_size, (*map(int, expand(BACKGROUND)), 255))
    background.alpha_composite(hardware)
    background.convert("RGB").save(review / "hardware_bg.png")
    background.resize((384, 432), Image.Resampling.NEAREST).save(review / "hardware_6x.png")
    comparison = Image.new("RGB", (800, 478), tuple(map(int, expand(BACKGROUND))))
    draw = ImageDraw.Draw(comparison)
    draw.text((8, 4), NAMES.get(role, role) + " — static source / native conversion", fill=(247, 231, 189))
    source_bg = Image.new("RGBA", padded_size, (*map(int, expand(BACKGROUND)), 255))
    source_bg.alpha_composite(source)
    comparison.paste(source_bg.resize((384, 432), Image.Resampling.NEAREST), (8, 38))
    comparison.paste(background.resize((384, 432), Image.Resampling.NEAREST), (408, 38))
    comparison.save(review / "comparison_6x.png")
    regions = {f"focus_{n}": region_metrics(rgba, decoded, box[:4])
               for n, box in enumerate(FOCUS.get(role, ())) }
    warnings = []
    for name, metric in regions.items():
        for kind in ("green", "bone", "red"):
            before = metric["source_material_pixels"].get(kind, 0)
            after = metric["native_material_pixels"].get(kind, 0)
            if before >= 3 and after < max(1, before // 3):
                warnings.append(f"{name}: source {kind} pixels reduced from{before} to{after}; visually review")
    outputs = {rel(file): sha(file.read_bytes()) for file in
               (folder / "portrait.2bpp", folder / "attrs.bin", folder / "palettes.bin", folder / "hardware.png")}
    report = {"role": role, "name": NAMES.get(role, role), "source": rel(path), "source_sha256": sha(payload),
              "source_provenance": "Historical authored native pixel portrait from selection/build_selection.js; not user PNG extraction",
              "source_dimensions": list(original.size), "source_crop": [0, 0, original.width, original.height],
              "native_dimensions": list(padded_size), "padding": [0, 0, padded_size[0] - original.width, padded_size[1] - original.height],
              "source_alpha_geometry_exact": True, "source_pixel_positions_exact": True,
              "resampling": None, "smoothing": False, "dithering": False, "new_anatomy_authored": False,
              "exact_source_rgb555_colors_preserved": False,
              "palette_conversion": "Lossy material-protected source palettes; per8x8 weighted assignment; source ink maps to shared dark BG0",
              "source_opaque_colors": len(np.unique(rgba[:, :, :3][rgba[:, :, 3] != 0] >> 3, axis=0)),
              "native_palette_ids": list(PALETTE_IDS), "palettes_rgb555": palettes.tolist(),
              "protected_source_material_palettes_rgb555": PROTECTED_PALETTES.get(role, ()),
              "protected_eye_tile_policy": "Kento tiles containing source red iris pixels use palette3; source iris color is present exactly" if role == "kento" else "Material/face-weighted palette assignment",
              "shared_background_rgb555": list(BACKGROUND),
              "palette_zero_used_for_source_transparency_and_opaque_ink": True,
              "source_alpha_retained_separately_from_opaque_bg_indices": True,
              "attrs_encoding": "72 palette IDs3..7 in row-major order; caller adds$08 VRAM-bank1 flag",
              "native_tile_order": "8 columns x9 rows, row-major, 2bpp; 72tiles/1152bytes",
              "packet_decode_exact": True, "tiles": tile_records, "focus_regions": regions,
              "visual_review_warnings": warnings, "outputs": outputs,
              "runtime_verification": "Static conversion only; exact-ROM rendering is tested separately"}
    (review / "import_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    title = "".join(word.title() for word in role.split("_"))
    label = f"PeonMaster{title}PortraitV0218"
    lines = [f'SECTION "Peon master{title} portrait v0218", ROMX', f"{label}::",
             f'\tINCBIN "gfx/class_portraits_v0218/{role}/portrait.2bpp"',
             f"\tassert @ - {label} == 72 * TILE_SIZE", f"{label}Attrs::",
             f'\tINCBIN "gfx/class_portraits_v0218/{role}/attrs.bin"',
             f"\tassert @ - {label}Attrs == 72", f"{label}Palettes::",
             f'\tINCBIN "gfx/class_portraits_v0218/{role}/palettes.bin"',
             f"\tassert @ - {label}Palettes == 5 * 4 * 2",
             f"\tassert BANK({label}) == BANK({label}Attrs)",
             f"\tassert BANK({label}) == BANK({label}Palettes)"]
    assert path.read_bytes() == payload, "Source portrait was changed"
    return report, lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", default=[], metavar="ROLE=PNG",
                        help="Add an optional native portrait, e.g.peon=/path/portrait.png")
    args = parser.parse_args()
    sources = dict(SOURCES)
    for override in args.source:
        role, path = override.split("=", 1)
        assert role.isidentifier() and role not in sources, "Use an additional unique role"
        sources[role] = Path(path)
    reports, graphics = [], []
    for role, path in sources.items():
        report, lines = convert_source(path, role)
        reports.append(report)
        graphics += lines + [""]
    (GFX / "graphics.asm").write_text("\n".join(graphics))
    report = {"version": "v0.2.18", "status": "PASS", "scope": "Static native portrait conversion; not ROM screenshots",
              "roles": {entry["role"]: entry for entry in reports},
              "sources_unchanged": True, "runtime_verification": "Not run by asset importer"}
    for path in (GFX / "manifest.json", REVIEW / "import_report.json"):
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (REVIEW / "README.md").write_text(
        "# Class master portraits v0.2.18\n\n"
        "Static native conversion evidence, not emulator screenshots. The three complete "
        "64x68 historical authored portraits under peon_sprite_redesign_v030/selection "
        "are read-only sources. Their character identities follow the supplied class-master "
        "references; these files are not user PNG extractions or recovered source grids. "
        "The historical build_selection.js generator is never run by this importer.\n\n"
        "No scaling, smoothing, dithering, silhouette editing or anatomy drawing occurs. "
        "Four transparent rows pad the bottom to64x72. Each portrait uses72 row-major8x8 "
        "tiles (1152 bytes),72 palette IDs3..7, and five4-color RGB555 palettes (40 bytes). "
        "attrs.bin deliberately omits the VRAM-bank1 bit; the caller must OR$08. Each "
        "portrait/attrs/palettes group is in one ROMX section in graphics.asm. Labels use "
        "PeonMaster{Kento,Zogzog,Bismillah}PortraitV0218 with Attrs/Palettes suffixes.\n\n"
        "BG index0 is opaque dark panel/ink RGB555(3,2,3), shared by every palette. It may "
        "represent source-opaque ink as well as background. Source alpha is preserved "
        "separately in hardware.png and source_padded.png; hardware_bg.png shows the actual "
        "opaque BG colors. Never infer a sprite transparency mask from these BG indices.\n\n"
        "Palettes use only existing source material colors besides the fixed background. "
        "Fine gradients are reduced by the per-tile four-color limit. Face/eye, horn/tusk, "
        "fur/beard, armor and robe materials guide palette assignment; Kento's tiny red "
        "iris tiles keep a dedicated source-color palette. The import reports retain "
        "per-tile before/after color counts and weighted face-region error information.\n\n"
        "hardware_bg.png is the1x review, hardware_6x.png is nearest-neighbor only, and "
        "comparison_6x.png shows source left/native right. Native1x and6x outputs were "
        "visually inspected; final engine rendering remains separate ROM validation.\n",
        encoding="utf-8")
    print(json.dumps({"status": "PASS", "roles": list(sources),
                      "warnings": {entry["role"]: entry["visual_review_warnings"] for entry in reports}}, indent=2))


if __name__ == "__main__":
    main()
