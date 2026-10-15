#!/usr/bin/env python3
"""Package v0.2.17 only after final, matching-ROM validation has passed.

Example:
  python3 tools/package_peon_v0217.py --rom /tmp/final/game.gbc \
    --sym /tmp/final/game.sym --map /tmp/final/game.map \
    --validation-root references/generated/v0217

Runtime images come only from validation.json's explicit native 160x144
screenshots/captures allowlist. Art exports are static import evidence, not
emulator captures. The ZIP is deterministic and every member is read back
with CRC and SHA256 verification. Its own SHA256 is stored externally.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

from PIL import Image, ImageSequence


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "releases/v0.2.17"
WORLD_ART = ROOT / "references/generated/world_redraw_v0217"
WORLD_GFX = ROOT / "gfx/world_redraw_v0217"
COMBAT_ART = ROOT / "references/generated/combat_heroes_v0216"
COMBAT_GFX = ROOT / "gfx/combat_heroes_v0216"
BASE_NAME = "peon_of_warcraft_v0_2_17"
HEROES = ("base", "shaman", "warrior", "warlock")
ANIMATED_WORLD_ROLES = HEROES + ("imp",)
DIRECTIONS = ("front", "back", "left", "right")
ART_SOURCES = tuple(ROOT / "assets/world_redraw_v0217" / (name + ".json")
                    for name in ("heroes", "orc_npcs", "trolls", "beasts", "monsters"))
ARCHIVED_REFERENCES = {
    "references/generated/peon_sprite_redesign_v030/originals/peon_base_design_reference.png",
    "references/generated/peon_sprite_redesign_v030/originals/peon_shaman_totemic_design_reference.png",
    "references/generated/peon_sprite_redesign_v030/originals/peon_warrior_design_reference.png",
    "references/generated/peon_sprite_redesign_v030/originals/peon_warlock_design_reference.png",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition, message: str):
    if not condition:
        raise SystemExit(message)


def json_bytes(value) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def source_path(value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else ROOT / path).resolve()


def passes(report) -> bool:
    if "status" in report:
        return report["status"] == "PASS"
    return report.get("passed") is True


def verify_manifest_sources(value):
    """Recheck declared source hashes, including approved larger raster masters.

    These are source-preservation checks, not a claim of recovered native
    pixel grids or runtime validation. Original PNGs stay outside the ZIP;
    new native authoring JSON files are included separately.
    """
    if isinstance(value, dict):
        for key in ("source_hashes", "source_files", "source_files_sha256", "source_json_sha256"):
            declared = value.get(key)
            if isinstance(declared, dict):
                for name, expected in declared.items():
                    if isinstance(expected, str):
                        require(digest(source_path(name).read_bytes()) == expected,
                                "Declared source changed: " + name)
        expected = value.get("source_sha256")
        if isinstance(expected, str):
            for key in ("source", "source_packet", "source_png"):
                name = value.get(key)
                if isinstance(name, str):
                    require(digest(source_path(name).read_bytes()) == expected,
                            "Declared source changed: " + name)
                    break
        for child in value.values():
            verify_manifest_sources(child)
    elif isinstance(value, list):
        for child in value:
            verify_manifest_sources(child)


def transparent_png(path: Path, dimensions: tuple[int, int]) -> bytes:
    data = path.read_bytes()
    image = Image.open(io.BytesIO(data))
    image.load()
    require(image.mode == "RGBA" and image.size == dimensions,
            "Invalid static native PNG: " + str(path))
    require(set(image.getchannel("A").get_flattened_data()) <= {0, 255},
            "Nonbinary static native PNG alpha: " + str(path))
    return data


def authored_world_sources(files: dict[str, bytes]) -> tuple[dict, list[dict]]:
    """Require actual native cells for all authored roles and archive their source."""
    roles, source_records = {}, []

    def validate_cells(rows, label):
        require(isinstance(rows, list) and len(rows) == 24,
                "Native authoring must contain 24 rows: " + label)
        require(all(isinstance(row, str) and len(row) == 24
                    and set(row) <= set(".123") for row in rows),
                "Native authoring is not a transparent 24x24 cell drawing: " + label)

    for path in ART_SOURCES:
        data = path.read_bytes()
        document = json.loads(data)
        require(document.get("version") == "v0.2.17",
                "Native authoring source has incorrect version: " + str(path))
        require(bool(document.get("authoring")),
                "Native authoring source has no method declaration: " + str(path))
        declared = document.get("roles", {})
        require(isinstance(declared, dict) and declared,
                "Native authoring source has no roles: " + str(path))
        for role, record in declared.items():
            require(isinstance(role, str) and Path(role).name == role and role not in roles,
                    "Unsafe or duplicate authored world role: " + str(role))
            require(isinstance(record, dict), "Invalid authored role record: " + role)
            views = record.get("views", {})
            require(isinstance(views, dict) and set(views) == set(DIRECTIONS),
                    "Authored role lacks four explicit directions: " + role)
            for direction in DIRECTIONS:
                validate_cells(views[direction], role + "/" + direction)
                walk = record.get("walk", {}).get(direction, [])
                if walk:
                    require(isinstance(walk, list) and len(walk) == 2,
                            "Authored walk needs two poses: " + role + "/" + direction)
                    for pose, rows in enumerate(walk, 1):
                        validate_cells(rows, f"{role}/{direction}/{pose}")
            references = record.get("references", [])
            require(isinstance(references, list) and bool(references),
                    "Authored role has no artwork references: " + role)
            for reference in references:
                require(isinstance(reference, str) and source_path(reference).is_file(),
                        "Missing authored artwork reference: " + str(reference))
            roles[role] = {"source": path.relative_to(ROOT).as_posix(),
                           "source_sha256": digest(data), "identity": record.get("identity", ""),
                           "references": references, "cells": record}
        target = "assets/world/native_sources/" + path.name
        files[target] = data
        source_records.append({"source": path.relative_to(ROOT).as_posix(), "path": target,
                               "sha256": digest(data), "roles": sorted(declared)})
    require(len(roles) == 35, "Expected all 35 newly authored world roles")
    require(set(ANIMATED_WORLD_ROLES) <= set(roles), "Missing an animated world family")
    return roles, source_records


def verify_world_export(data: bytes, packet: bytes, masks: bytes, attrs: bytes,
                        palettes: list, frame: int, cells, label: str):
    """Compare the selected static PNG and source cells with its actual 2bpp frame.

    This proves packet/export consistency only; emulator reports are required
    independently for runtime placement, palettes, OAM admission and interaction.
    """
    image = Image.open(io.BytesIO(data))
    pixels = image.load()
    actual_mask = 0
    for tile in range(9):
        palette_id = attrs[frame * 9 + tile]
        palette = palettes[palette_id]
        tile_y, tile_x = divmod(tile, 3)
        visible = False
        for row in range(8):
            offset = frame * 144 + tile * 16 + row * 2
            lo, hi = packet[offset:offset + 2]
            for column in range(8):
                shift = 7 - column
                index = ((lo >> shift) & 1) | (((hi >> shift) & 1) << 1)
                x, y = tile_x * 8 + column, tile_y * 8 + row
                expected = 0 if cells[y][x] == "." else int(cells[y][x])
                require(index == expected, "World 2bpp does not match authored source cells: " + label)
                pixel = pixels[x, y]
                require(pixel[3] == (255 if index else 0),
                        "World export alpha differs from native packet: " + label)
                if index:
                    visible = True
                    rgb = tuple((value << 3) | (value >> 2) for value in palette[index])
                    require(pixel[:3] == rgb,
                            "World export color differs from native packet/palette: " + label)
        if visible:
            actual_mask |= 1 << tile
    require(int.from_bytes(masks[frame * 2:frame * 2 + 2], "little") == actual_mask,
            "World native transparency mask differs from its frame: " + label)


def collect_art(files: dict[str, bytes]) -> dict:
    """Select explicit native exports; static drawings are never runtime proof."""
    world_path = WORLD_ART / "import_report.json"
    if not world_path.is_file():
        world_path = WORLD_GFX / "manifest.json"
    world = json.loads(world_path.read_text())
    combat_path = COMBAT_GFX / "manifest.json"
    combat = json.loads(combat_path.read_text())
    require(passes(world), "World native import manifest is not PASS")
    require(passes(combat), "Combat native import manifest is not PASS")
    verify_manifest_sources(world)
    verify_manifest_sources(combat)
    authored_roles, authoring_sources = authored_world_sources(files)
    require(set(world.get("authored_roles", [])) == set(authored_roles),
            "World manifest authored_roles differs from the five actual JSON sources")

    source_path_json = WORLD_ART / "source_png_hashes.json"
    require(source_path_json.is_file(), "Missing v17 source PNG preservation report")
    originals = json.loads(source_path_json.read_text())
    require(originals.get("all_source_sha256_identical_before_after_import") is True,
            "Original character source-preservation check is incomplete")
    original_files = originals.get("source_files", {})
    character_sources = [path for path in original_files
                         if path.startswith("references/characters/")]
    require(len(character_sources) == 495,
            "Expected the complete 495 original character PNG hashes")
    require(set(original_files) == set(character_sources) | ARCHIVED_REFERENCES,
            "Expected exactly the 495 original PNGs and four archived approved raster references")
    verify_manifest_sources(originals)

    static = {"version": "v0.2.17", "kind": "Static native exports; not emulator captures",
              "smoothing": False,
              "world": {"dimensions": [24, 24], "roles": {}, "files": [],
                        "authoring": "New native 24x24 pixel cells; not recovered or scaled source pixels",
                        "authoring_sources": authoring_sources,
                        "missing_named_exports": []},
              "combat": {"hardware_dimensions": {"back": [48, 48], "front": [56, 56],
              "profile": [56, 56]}, "unchanged_from_version": "v0.2.16",
              "files": [], "source_native_files": []}}
    for role, source in sorted(authored_roles.items()):
        record = world.get("roles", {}).get(role)
        require(isinstance(record, dict), "Missing authored world manifest role: " + role)
        require(record.get("source_kind") == "deliberate_native_24x24_cell_art",
                "World manifest mislabels native authoring: " + role)
        require(source_path(record.get("source_packet", "")) == source_path(source["source"])
                and record.get("source_sha256") == source["source_sha256"],
                "World manifest does not reference its exact native authoring JSON: " + role)
        packet_path = source_path(record["output_packet"])
        packet = packet_path.read_bytes()
        masks = packet_path.with_name("masks.bin").read_bytes()
        attrs = packet_path.with_name("attrs.bin").read_bytes()
        for payload, length, hash_key in ((packet, 1728, "output_sha256"),
                                          (masks, 24, "mask_sha256"),
                                          (attrs, 108, "attrs_sha256")):
            require(len(payload) == length and digest(payload) == record.get(hash_key),
                    "World native packet changed: " + role + "/" + hash_key)
        static["world"]["roles"][role] = record
        for direction in DIRECTIONS:
            for pose in (range(3) if role in ANIMATED_WORLD_ROLES else (0,)):
                name = f"world_{direction}_{pose}_24x24.png"
                path = WORLD_ART / role / name
                if not path.is_file():
                    path = WORLD_GFX / role / name
                if not path.is_file():
                    static["world"]["missing_named_exports"].append(f"{role}/{name}")
                    continue
                data = transparent_png(path, (24, 24))
                art = source["cells"]
                rows = (art.get("walk", {}).get(direction) or [art["views"][direction]] * 2)[pose - 1] if pose else art["views"][direction]
                frame = DIRECTIONS.index(direction) * 3 + pose
                verify_world_export(data, packet, masks, attrs,
                                    world["effective_world_palettes_rgb555"], frame, rows,
                                    role + "/" + name)
                target = f"assets/world/static_native_exports/{role}/{name}"
                files[target] = data
                static["world"]["files"].append({"path": target, "sha256": digest(data)})
    expected_exports = sum(12 if role in ANIMATED_WORLD_ROLES else 4 for role in authored_roles)
    require(expected_exports == 180 and len(static["world"]["files"]) == expected_exports,
            "Expected all 180 named v17 authored world PNG exports; missing: "
            + ", ".join(static["world"]["missing_named_exports"]))

    # Combat is the previously validated v16 import. Hardware exports are the
    # decoded packets in use; sampled pre-quantization sources stay distinct.
    packets = {(item["role"], item["view"]): item for item in combat.get("packets", [])}
    for role in HEROES:
        for view in ("back", "front", "profile"):
            require((role, view) in packets, "Missing combat packet manifest: " + role + "/" + view)
            record = packets[role, view]
            dimensions = (48, 48) if view == "back" else (56, 56)
            require(record.get("native_size") == list(dimensions), "Incorrect combat native dimensions")
            for path_string, expected in record.get("outputs", {}).items():
                require(digest(source_path(path_string).read_bytes()) == expected,
                        "Combat packet/export changed: " + path_string)
            for pose in range(3):
                path = COMBAT_GFX / role / view / f"pose_{pose}.png"
                data = transparent_png(path, dimensions)
                target = f"assets/combat/static_imports/{role}/{view}/hardware_{pose}.png"
                files[target] = data
                static["combat"]["files"].append({"path": target, "sha256": digest(data)})
                source = COMBAT_ART / role / view / f"source_native_{pose}.png"
                if source.is_file():
                    data = transparent_png(source, dimensions)
                    target = f"assets/combat/source_native/{role}/{view}/{source.name}"
                    files[target] = data
                    static["combat"]["source_native_files"].append({"path": target, "sha256": digest(data)})
    files["assets/manifest.json"] = json_bytes(static)
    files["assets/world/import_report.json"] = world_path.read_bytes()
    files["assets/world/source_png_hashes.json"] = json_bytes(originals)
    files["assets/combat/import_report.json"] = combat_path.read_bytes()
    return static


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("rom", "sym", "map", "validation-root"):
        parser.add_argument("--" + option, required=True, type=Path)
    args = parser.parse_args()
    validation_path = args.validation_root.resolve() / "validation.json"
    validation = json.loads(validation_path.read_text())
    require(passes(validation), "Packaging refused: validation is not PASS")
    rom_data = args.rom.read_bytes()
    rom_hash = digest(rom_data)
    require(validation.get("rom_sha256") == rom_hash,
            "Packaging refused: validation ROM SHA does not match supplied ROM")
    require(len(rom_data) >= 0x150 and rom_data[0x143] & 0x80,
            "Packaging refused: supplied ROM is not marked GBC-compatible")
    if (RELEASE / "manifest.json").is_file():
        previous = json.loads((RELEASE / "manifest.json").read_text())
        require(previous.get("rom_sha256") == rom_hash,
                "Packaging refused: v0.2.17 already contains a different ROM")

    files = {BASE_NAME + ".gbc": rom_data,
             BASE_NAME + ".sym": args.sym.read_bytes(),
             BASE_NAME + ".map": args.map.read_bytes(),
             "validation/validation.json": validation_path.read_bytes()}
    for extension in ("sym", "map"):
        if validation.get(extension + "_sha256"):
            require(validation[extension + "_sha256"] == digest(files[BASE_NAME + "." + extension]),
                    "Packaging refused: " + extension + " SHA mismatch")
    require(bool(validation.get("tests")), "Packaging refused: no final validation tests declared")
    for name, test in validation["tests"].items():
        require(passes(test), "Packaging refused: incomplete test " + name)
        if test.get("report"):
            report_path = source_path(test["report"])
            data = report_path.read_bytes()
            report = json.loads(data)
            require(passes(report), "Packaging refused: report is not PASS: " + name)
            if test.get("report_sha256"):
                require(digest(data) == test["report_sha256"], "Stale report: " + name)
            # Baseline comparisons may be referenced by the aggregate, but
            # their older-ROM reports cannot become final runtime evidence.
            if report.get("rom_sha256", rom_hash) == rom_hash:
                require(Path(name).name == name, "Unsafe test report name")
                files["validation/" + name + ".json"] = data

    screenshots = validation.get("screenshots", {})
    captures = validation.get("captures", [])
    require(bool(screenshots) or bool(captures), "No explicitly tested runtime captures declared")
    declared = list(screenshots.items())
    for number, item in enumerate(captures):
        item = {"path": item} if isinstance(item, str) else item
        declared.append((item.get("name", f"{number:02d}_" + Path(item["path"]).name), item))
    runtime_manifest = []
    for name, item in declared:
        item = {"path": item} if isinstance(item, str) else item
        path = source_path(item["path"])
        require(Path(name).name == name and name.endswith(".png"), "Unsafe runtime capture name")
        require(item.get("rom_sha256", rom_hash) == rom_hash, "Stale capture ROM SHA: " + name)
        data = path.read_bytes()
        if item.get("sha256"):
            require(item["sha256"] == digest(data), "Stale runtime capture: " + name)
        image = Image.open(io.BytesIO(data))
        image.load()
        require(image.size == (160, 144), "Runtime capture is not native LCD160x144: " + str(path))
        require(image.convert("RGBA").getchannel("A").getextrema() == (255, 255),
                "Runtime capture unexpectedly contains transparency: " + name)
        target = "runtime/" + name
        require(target not in files, "Duplicate runtime capture name: " + name)
        files[target] = data
        scaled_target = target[:-4] + "_4x.png"
        require(scaled_target not in files, "Duplicate scaled capture name: " + name)
        scaled = io.BytesIO()
        image.resize((640, 576), Image.Resampling.NEAREST).save(scaled, format="PNG")
        files[scaled_target] = scaled.getvalue()
        runtime_manifest.append({"source": str(path), "path": target, "sha256": digest(data),
                                 "rom_sha256": rom_hash, "nearest_4x": scaled_target})

    animation_manifest = []
    for item in validation.get("animations", []):
        require(isinstance(item, dict), "Runtime animation must be an explicit metadata entry")
        name = item.get("name", "")
        require(Path(name).name == name and name.endswith(".gif"), "Unsafe runtime animation name")
        require(item.get("rom_sha256") == rom_hash, "Stale animation ROM SHA: " + name)
        path = source_path(item["path"])
        data = path.read_bytes()
        require(item.get("sha256") == digest(data), "Stale runtime animation: " + name)
        animation = Image.open(io.BytesIO(data))
        require(animation.format == "GIF" and animation.size == (160, 144),
                "Runtime animation is not native LCD160x144 GIF: " + name)
        require(getattr(animation, "n_frames", 1) > 1, "Runtime animation has only one frame: " + name)
        frame_count = 0
        for frame in ImageSequence.Iterator(animation):
            require(frame.size == (160, 144), "Runtime animation frame dimensions changed: " + name)
            require(frame.convert("RGBA").getchannel("A").getextrema() == (255, 255),
                    "Runtime animation composed frame contains transparency: " + name)
            frame_count += 1
        target = "runtime/animations/" + name
        require(target not in files, "Duplicate runtime animation name: " + name)
        files[target] = data
        animation_manifest.append({"source": str(path), "path": target, "sha256": digest(data),
                                   "rom_sha256": rom_hash, "dimensions": [160, 144],
                                   "frames": frame_count, "composed_frames_opaque": True})

    static = collect_art(files)
    files["runtime/manifest.json"] = json_bytes({"rom_sha256": rom_hash, "captures": runtime_manifest,
                                               "animations": animation_manifest})
    if animation_manifest:
        files["runtime/animations/manifest.json"] = json_bytes({"rom_sha256": rom_hash,
                                                              "animations": animation_manifest})
    files["README.md"] = (
        "# Peon of Warcraft v0.2.17\n\n"
        "Ouvrir peon_of_warcraft_v0_2_17.gbc dans un émulateur Game Boy Color ou sur ModRetro.\n\n"
        "Les personnages du monde sont redessinés directement en pixels natifs 24×24 : "
        "visages, proportions et équipements disposent de nouveaux pixels. Les 35 rôles "
        "nouvellement dessinés possèdent leurs quatre directions ; les héros et le diablotin "
        "disposent de trois emplacements de pose par direction. Ces dessins sont de nouvelles "
        "interprétations natives des références fournies, pas une extraction exacte ou un "
        "agrandissement des anciens PNG 16×16. Les cinq JSON de cellules sources sont dans "
        "assets/world/native_sources/, avec leur provenance et leurs SHA256 dans le manifest.\n\n"
        "La grille de déplacement et de collision reste de 16 px. Les limites GBC restent "
        "40 objets et 10 par ligne ; les corps proches sont prioritaires, et le HUD optionnel "
        "peut disparaître lorsque les corps complets occupent les objets disponibles.\n\n"
        "Les imports de combat restent ceux de v0.2.16 : cadres natifs 48×48 de dos et 56×56 "
        "de face. Les conversions avec perte depuis les grandes références approuvées ne sont "
        "pas présentées comme des pixels natifs récupérés. Le caillou conserve STRIKE et ses "
        "attaques de terre ; MACE STRIKE conserve son coût nul de mana.\n\n"
        "runtime/ contient uniquement les captures natives 160×144 explicitement validées de "
        "cette ROM et leurs agrandissements 4× sans lissage. assets/world/static_native_exports/ "
        "et assets/combat/static_imports/ contiennent les PNG transparents des paquets natifs ; "
        "assets/combat/source_native/ contient les sources échantillonnées avant quantification. "
        "Ces galeries statiques sont distinctes des captures du jeu. Aucun lissage n'est appliqué.\n\n"
        "Les GIF de runtime/animations/, lorsqu'ils sont fournis, montrent cette même ROM en "
        "160×144 ; leurs images composées sont opaques et leurs SHA256 sont vérifiés.\n\n"
        "validation/ contient les preuves déclarées PASS. Les 495 PNG de personnages originaux "
        "et les quatre rasters approuvés, soit 499 sources conservées, ont été revérifiés par "
        "SHA256. Le matériel physique ModRetro n'a pas été testé.\n\n"
        "ZIP déterministe : noms triés, date fixe 2026-10-15 et compression fixe. Chaque membre "
        "est relu avec son CRC et son SHA256 après écriture. SHA256SUMS.txt vérifie les fichiers "
        "du ZIP ; le SHA256 du ZIP lui-même est fourni dans le manifest externe et le fichier "
        ".zip.sha256, sans hash autoréférentiel.\n"
    ).encode()
    manifest = {"version": "v0.2.17", "rom": BASE_NAME + ".gbc", "rom_sha256": rom_hash,
                "validation_sha256": digest(validation_path.read_bytes()),
                "physical_modretro_tested": False, "runtime": runtime_manifest,
                "runtime_animations": animation_manifest,
                "assets": {"world": "assets/world/static_native_exports/",
                           "world_authoring_sources": "assets/world/native_sources/",
                           "combat": "assets/combat/static_imports/",
                           "combat_sampled_sources": "assets/combat/source_native/"},
                "files": {name: {"sha256": digest(data), "bytes": len(data)}
                          for name, data in sorted(files.items())}}
    files["manifest.json"] = json_bytes(manifest)
    files["SHA256SUMS.txt"] = "".join(f"{digest(data)}  {name}\n"
                                      for name, data in sorted(files.items())
                                      if name != "manifest.json").encode()

    # All source, validation and image checks finish before any release output.
    RELEASE.mkdir(parents=True, exist_ok=True)
    archive = RELEASE / (BASE_NAME + ".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for name, data in sorted(files.items()):
            require(not Path(name).is_absolute() and ".." not in Path(name).parts, "Unsafe ZIP member")
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 15, 0, 0, 0))
            info.compress_type, info.create_system = zipfile.ZIP_DEFLATED, 3
            info.external_attr = 0o100644 << 16
            out.writestr(info, data, compresslevel=9)
    with zipfile.ZipFile(archive) as check:
        require(check.testzip() is None, "ZIP CRC verification failed")
        require(set(check.namelist()) == set(files), "ZIP file list changed")
        for name, data in files.items():
            require(digest(check.read(name)) == digest(data), "ZIP member SHA failed: " + name)
        require(digest(check.read(BASE_NAME + ".gbc")) == rom_hash, "Embedded ROM SHA failed")
    for name, data in files.items():
        if name == "manifest.json":
            continue
        target = RELEASE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    archive_hash = digest(archive.read_bytes())
    manifest.update({"zip_sha256": archive_hash, "zip_bytes": archive.stat().st_size,
                     "zip_crc_and_all_payload_sha256": "PASS"})
    (RELEASE / "manifest.json").write_bytes(json_bytes(manifest))
    (RELEASE / (archive.name + ".sha256")).write_text(f"{archive_hash}  {archive.name}\n")
    print(json.dumps({"status": "PASS", "rom_sha256": rom_hash, "zip_sha256": archive_hash,
                      "runtime_captures": len(runtime_manifest),
                      "runtime_animations": len(animation_manifest),
                      "world_pngs": len(static["world"]["files"]),
                      "combat_pngs": len(static["combat"]["files"]),
                      "combat_sampled_source_pngs": len(static["combat"]["source_native_files"]),
                      "release": str(RELEASE)}, indent=2))


if __name__ == "__main__":
    main()
