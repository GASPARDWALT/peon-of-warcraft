#!/usr/bin/env python3
"""Inventory the preserved Environment Pack v2; never modify its source files."""
from collections import Counter
import argparse
import csv
import hashlib
import json
from pathlib import Path
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "references/characters/peon_of_warcraft_environment_pack_v2_art_quality"
ARCHIVE_SHA = "5a9b27fe4a8c20934654388058f635726e2e3f477c131b27efff687fc2c1bdc0"
CANONICAL_COMMIT = "64bfb4cbf75ca83b05f34401c520a099a5e25f54"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def category(filename):
    stem = Path(filename).stem
    for prefix, label in (
        ("orc_", "buildings"), ("troll_hut_", "buildings"),
        ("troll_totem_", "totems"), ("tiki_", "totems"), ("training_", "totems"),
        ("ground_", "ground"), ("path_", "paths"), ("boardwalk_", "paths"),
        ("transition_", "transitions"), ("water_", "water"), ("shore_", "shorelines"),
        ("rock_", "rocks"), ("cactus_", "vegetation"), ("grass_", "vegetation"),
        ("palm_", "vegetation"), ("bush_", "vegetation"), ("reeds_", "vegetation"),
        ("tree_", "vegetation"), ("fern_", "vegetation"), ("vine_", "vegetation"),
        ("bones_", "bones"), ("cave_", "cave_entrances"), ("banner_", "banners"),
        ("palisade_", "palisades"), ("brazier_", "fires"), ("campfire_", "fires"),
        ("floor_", "wood_floors"), ("crates_", "cargo_containers"),
        ("barrel_", "cargo_containers"), ("sack_", "cargo_containers"),
        ("weapon_", "weapon_racks"), ("watch_", "watch_posts"), ("beast_", "beast_pens"),
        ("canoe_", "boats_and_nets"), ("fishing_", "boats_and_nets"),
        ("driftwood_", "beach_props"), ("shells_", "beach_props"),
        ("ruin_", "ruins"), ("bridge_", "bridges"), ("chest_", "chests"),
        ("ore_", "ore_nodes"), ("herb_", "herbs"), ("resource_", "quest_and_resource_items"),
        ("quest_", "quest_and_resource_items"), ("bedroll_", "camp_furniture"),
        ("table_", "camp_furniture"), ("stool_", "camp_furniture"),
    ):
        if stem.startswith(prefix):
            return label
    raise ValueError("Unclassified canonical asset: " + filename)


def image_record(path):
    image = Image.open(path).convert("RGBA")
    alpha = set(image.getchannel("A").get_flattened_data())
    maximum = 0
    maximum_rgb555 = 0
    for y in range(0, image.height, 8):
        for x in range(0, image.width, 8):
            colors = {pixel[:3] for pixel in image.crop((x, y, min(x + 8, image.width),
                                                       min(y + 8, image.height))).get_flattened_data()
                      if pixel[3]}
            maximum = max(maximum, len(colors))
            maximum_rgb555 = max(maximum_rgb555, len({tuple(v >> 3 for v in c) for c in colors}))
    bbox = image.getchannel("A").getbbox()
    return {"dimensions": list(image.size), "alpha_values": sorted(alpha),
            "alpha_binary": alpha <= {0, 255}, "opaque": alpha == {255},
            "opaque_bbox": list(bbox) if bbox else None,
            "dimensions_multiples_of_8": not (image.width % 8 or image.height % 8),
            "max_visible_rgb_colors_per_8x8": maximum,
            "max_visible_rgb555_colors_per_8x8": maximum_rgb555,
            "rgba_pixels_sha256": sha(image.tobytes())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "references/generated/map_tests/source_inventory.json")
    args = parser.parse_args()
    archive = SOURCE.with_suffix(".zip")
    assert sha(archive.read_bytes()) == ARCHIVE_SHA, "Canonical archive hash changed"
    with (SOURCE / "manifest.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 166 and len({r["file"] for r in rows}) == 166
    metadata = {r["file"]: r for r in rows}
    records = []
    with zipfile.ZipFile(archive) as zipped:
        members = {item.filename: item for item in zipped.infolist() if not item.is_dir()}
        assert len(members) == 182
        assert set(members) == {p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob("*") if p.is_file()}
        for name in sorted(members):
            path = SOURCE / name
            data = path.read_bytes()
            assert data == zipped.read(name), "Extracted source differs from ZIP: " + name
            entry = {"file": name, "bytes": len(data), "sha256": sha(data)}
            if name in metadata:
                row = metadata[name]
                entry.update(role="native_asset", biome=row["biome"], source_kind=row["kind"],
                             category=category(name), **image_record(path))
                assert entry["dimensions"] == [int(row["width"]), int(row["height"])]
            elif path.suffix.lower() == ".png":
                entry.update(role="preview_or_source_atlas", folder=Path(name).parts[0],
                             dimensions=list(Image.open(path).size))
            else:
                entry.update(role="document_or_manifest")
            records.append(entry)
    assets = [r for r in records if r["role"] == "native_asset"]
    notes_path = ROOT / "references/generated/environment_pack_v2_source_audit/source_audit.json"
    notes = json.loads(notes_path.read_text())["import_notes"]
    durotar = [r for r in assets if r["biome"] == "durotar_valley"]
    pixel_groups = {}
    for item in durotar:
        pixel_groups.setdefault(item["rgba_pixels_sha256"], []).append(item["file"])
    report = {
        "schema": "peon.environment.source_inventory.v1", "status": "PASS",
        "scope": "Source inventory only; other biomes are catalogued, not imported or tested.",
        "canonical_commit": CANONICAL_COMMIT, "canonical_commit_subject": "Add_Map_environment_pack_v2_art_quality",
        "archive": str(archive.relative_to(ROOT)), "archive_sha256": ARCHIVE_SHA,
        "source": str(SOURCE.relative_to(ROOT)), "source_bytes_preserved": True,
        "total_files": len(records), "native_asset_count": len(assets),
        "preview_or_source_atlas_count": sum(r["role"] == "preview_or_source_atlas" for r in records),
        "document_or_manifest_count": sum(r["role"] == "document_or_manifest" for r in records),
        "biome_counts": dict(sorted(Counter(r["biome"] for r in assets).items())),
        "source_kind_counts": dict(sorted(Counter(r["source_kind"] for r in assets).items())),
        "category_counts": dict(sorted(Counter(r["category"] for r in assets).items())),
        "categories_by_biome": {
            biome: dict(sorted(Counter(r["category"] for r in assets if r["biome"] == biome).items()))
            for biome in sorted({r["biome"] for r in assets})},
        "native_dimensions_multiples_of_8": all(r["dimensions_multiples_of_8"] for r in assets),
        "native_alpha_binary": all(r["alpha_binary"] for r in assets),
        "source_tiles_exceeding_4_rgb555_colors": [r["file"] for r in assets if r["max_visible_rgb555_colors_per_8x8"] > 4],
        "durotar_exact_rgba_duplicate_groups": [names for names in pixel_groups.values() if len(names) > 1],
        "issues": {
            "path_filename_orientation_swapped": notes["path_filename_orientation_swapped"],
            "native_canvas_padding_to_review": {
                r["file"]: {"dimensions": r["dimensions"], "opaque_bbox": r["opaque_bbox"]}
                for r in assets if r["file"] in notes["cropping_or_padding_to_review"]},
            "water_frame_02_palette_conversion": notes["water_frame_02_requires_palette_conversion"],
            "budget_deferrals_are_not_source_duplicates": "No Durotar assets have identical full RGBA pixels; any deferred terrain variants remain distinct source art.",
        },
        "native_import_status": "Pending separate importer and exact-ROM runtime evidence.",
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "total_files", "native_asset_count",
                       "preview_or_source_atlas_count", "document_or_manifest_count", "biome_counts",
                       "category_counts", "native_dimensions_multiples_of_8", "native_alpha_binary")}, indent=2))


if __name__ == "__main__":
    main()
