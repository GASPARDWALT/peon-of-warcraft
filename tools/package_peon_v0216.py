#!/usr/bin/env python3
"""Package v0.2.16 only after final, matching-ROM validation has passed.

Example:
  python3 tools/package_peon_v0216.py --rom /tmp/final/game.gbc \
    --sym /tmp/final/game.sym --map /tmp/final/game.map \
    --validation-root references/generated/v0216

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
RELEASE = ROOT / "releases/v0.2.16"
WORLD_ART = ROOT / "references/generated/world_detail_v0216"
WORLD_GFX = ROOT / "gfx/world_actors_v0216"
COMBAT_ART = ROOT / "references/generated/combat_heroes_v0216"
COMBAT_GFX = ROOT / "gfx/combat_heroes_v0216"
BASE_NAME = "peon_of_warcraft_v0_2_16"
HEROES = ("base", "shaman", "warrior", "warlock")
COMMON_NPCS = ("quest_peon", "peon_worker", "orc_guard", "orc_merchant",
               "boar", "scorpid", "imp", "troll_shaman", "enemy_warlock",
               "rock_one_npc", "sleeping", "kolkar_archer", "kolkar_raider")
DIRECTIONS = ("front", "back", "left", "right")


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
    pixel grids or runtime validation. Source files stay outside the ZIP.
    """
    if isinstance(value, dict):
        for key in ("source_hashes", "source_files"):
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


def collect_art(files: dict[str, bytes]) -> dict:
    """Select named native exports only; never glob preview/diagnostic trees."""
    world_path = WORLD_ART / "import_report.json"
    if not world_path.is_file():
        world_path = WORLD_GFX / "manifest.json"
    world = json.loads(world_path.read_text())
    combat_path = COMBAT_GFX / "manifest.json"
    combat = json.loads(combat_path.read_text())
    require(passes(combat), "Combat native import manifest is not PASS")
    verify_manifest_sources(world)
    verify_manifest_sources(combat)

    source_path_json = WORLD_ART / "source_png_hashes.json"
    if not source_path_json.is_file():
        # The v15 baseline hashes still protect the same 495 originals. This
        # fallback does not use v15 artwork as a v16 rendered export.
        source_path_json = ROOT / "references/generated/world_actors_v0215/source_png_hashes.json"
    originals = json.loads(source_path_json.read_text())
    require(originals.get("all_source_sha256_identical_before_after_import") is True,
            "Original character source-preservation check is incomplete")
    original_files = originals.get("source_files", {})
    character_sources = [path for path in original_files
                         if path.startswith("references/characters/")]
    require(len(character_sources) == 495,
            "Expected the complete 495 original character PNG hashes")
    # The v16 manifest also records four approved raster references: 499
    # sources in total. Verify every entry, not only the 495 character PNGs.
    verify_manifest_sources(originals)

    static = {"version": "v0.2.16", "kind": "Static native imports; not emulator captures",
              "smoothing": False, "world": {"dimensions": [24, 24], "roles": {},
              "files": [], "missing_named_exports": []},
              "combat": {"hardware_dimensions": {"back": [48, 48], "front": [56, 56],
              "profile": [56, 56]}, "files": [], "source_native_files": []}}
    for role in HEROES + COMMON_NPCS:
        static["world"]["roles"][role] = world.get("roles", {}).get(role, {})
        for direction in DIRECTIONS:
            for pose in (range(3) if role in HEROES else (0,)):
                name = f"world_{direction}_{pose}_24x24.png"
                path = WORLD_ART / role / name
                if not path.is_file():
                    path = WORLD_GFX / role / name
                if not path.is_file():
                    static["world"]["missing_named_exports"].append(f"{role}/{name}")
                    continue
                data = transparent_png(path, (24, 24))
                target = f"assets/world/static_imports/{role}/{name}"
                files[target] = data
                static["world"]["files"].append({"path": target, "sha256": digest(data)})
    require(len(static["world"]["files"]) == 100,
            "Expected all 100 named v16 native world PNG exports; missing: "
            + ", ".join(static["world"]["missing_named_exports"]))

    # Hardware exports are the decoded packets in use; source_native exports
    # are their sampled, pre-quantization source, clearly labelled separately.
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
                "Packaging refused: v0.2.16 already contains a different ROM")

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
        "# Peon of Warcraft v0.2.16\n\n"
        "Ouvrir peon_of_warcraft_v0_2_16.gbc dans un émulateur Game Boy Color ou sur ModRetro.\n\n"
        "Les personnages du monde conservent leurs corps 24×24 sur la grille de déplacement de 16 px. "
        "Les détails proviennent de leurs sources de personnage dans le monde, pas d'une réduction "
        "des illustrations de combat. Les silhouettes et équipements fournis restent les références. "
        "Les limites GBC restent 40 objets et 10 par ligne ; les personnages proches sont prioritaires.\n\n"
        "Les trois héros de classe occupent mieux leurs cadres natifs de combat 48×48 de dos et 56×56 "
        "de face ; le Peon de base est également fourni. Les PNG natifs et leurs provenances sont "
        "dans assets/combat/. Les imports Warrior/Warlock depuis les grandes références approuvées "
        "restent des conversions avec perte ; ils ne sont pas présentés comme des pixels natifs récupérés.\n\n"
        "Le Peon de base et le Shaman conservent trois poses dessinées. Warrior/Warlock conservent "
        "l'unique pose fournie, répétée dans les trois emplacements natifs.\n\n"
        "Le petit caillou utilise STRIKE et des attaques de terre adaptées, avec leurs animations. "
        "Il ne possède pas de masse. MACE STRIKE est une attaque physique sans coût de mana.\n\n"
        "runtime/ contient uniquement les captures natives 160×144 explicitement validées de cette ROM "
        "et leurs agrandissements 4× sans lissage. assets/world/static_imports/ et "
        "assets/combat/static_imports/ contiennent des PNG transparents décodés depuis les imports "
        "natifs. assets/combat/source_native/ contient les sources échantillonnées avant quantification. "
        "Ces galeries statiques sont distinctes des captures du jeu. Aucun lissage n'est appliqué.\n\n"
        "Les GIF de runtime/animations/, lorsqu'ils sont fournis, montrent les animations de cette "
        "même ROM en 160×144 ; leurs images composées sont opaques et leurs SHA256 sont vérifiés.\n\n"
        "validation/ contient les preuves déclarées PASS. Les 495 PNG de personnages originaux "
        "et les quatre rasters approuvés, soit 499 sources, ont été revérifiés par SHA256. "
        "Le matériel physique ModRetro n'a pas été testé.\n\n"
        "ZIP déterministe : noms triés, date fixe 2026-10-15 et compression fixe. Chaque membre est "
        "relu avec son CRC et son SHA256 après écriture. SHA256SUMS.txt vérifie les fichiers du ZIP ; "
        "le SHA256 du ZIP lui-même est fourni dans le manifest externe et le fichier .zip.sha256, "
        "car un fichier ne peut pas contenir son propre hash sans circularité.\n"
    ).encode()
    manifest = {"version": "v0.2.16", "rom": BASE_NAME + ".gbc", "rom_sha256": rom_hash,
                "validation_sha256": digest(validation_path.read_bytes()),
                "physical_modretro_tested": False, "runtime": runtime_manifest,
                "runtime_animations": animation_manifest,
                "assets": {"world": "assets/world/static_imports/",
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
