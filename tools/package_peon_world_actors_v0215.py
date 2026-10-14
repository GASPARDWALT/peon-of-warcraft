#!/usr/bin/env python3
"""Package v0.2.15 only from an explicitly passing, matching-ROM validation.

Example:
  python3 tools/package_peon_world_actors_v0215.py --rom /tmp/final/game.gbc \
    --sym /tmp/final/game.sym --map /tmp/final/game.map \
    --validation-root references/generated/v0215

validation.json must contain status=PASS, the actual rom_sha256, and an
explicit screenshots{name:path} or captures[{path,sha256?}] allowlist of
native160x144 LCD images. No runtime directory is globbed. A deterministic
ZIP carries payload checksums; its own SHA lives outside the ZIP to avoid a
circular self-hash. Every ZIP member is read back and CRC/hash-checked.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "releases/v0.2.15"
ART = ROOT / "references/generated/world_actors_v0215"
BASE_NAME = "peon_of_warcraft_v0_2_15"
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
                "Packaging refused: v0.2.15 already contains a different ROM")

    files = {BASE_NAME + ".gbc": rom_data,
             BASE_NAME + ".sym": args.sym.read_bytes(),
             BASE_NAME + ".map": args.map.read_bytes(),
             "validation/validation.json": validation_path.read_bytes()}
    for extension in ("sym", "map"):
        if validation.get(extension + "_sha256"):
            require(validation[extension + "_sha256"] == digest(files[BASE_NAME + "." + extension]),
                    "Packaging refused: " + extension + " SHA mismatch")
    # Reports are explicitly declared by the aggregate, never directory scans.
    for name, test in validation.get("tests", {}).items():
        require(passes(test), "Packaging refused: incomplete test " + name)
        if test.get("report"):
            report_path = source_path(test["report"])
            data = report_path.read_bytes()
            report = json.loads(data)
            require(passes(report), "Packaging refused: report is not PASS: " + name)
            if test.get("report_sha256"):
                require(digest(data) == test["report_sha256"], "Stale report: " + name)
            # Older comparison evidence can remain referenced by the aggregate;
            # only the final-ROM reports are included as current runtime proof.
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
        require(image.size == (160, 144), "Runtime capture is not native LCD160x144: " + str(path))
        require(image.convert("RGBA").getchannel("A").getextrema() == (255, 255),
                "Runtime capture unexpectedly contains transparency: " + name)
        target = "runtime/" + name
        require(target not in files, "Duplicate runtime capture name: " + name)
        files[target] = data
        scaled_target = target[:-4] + "_4x.png"
        scaled = io.BytesIO()
        image.resize((640, 576), Image.Resampling.NEAREST).save(scaled, format="PNG")
        files[scaled_target] = scaled.getvalue()
        runtime_manifest.append({"source": str(path), "path": target, "sha256": digest(data),
                                 "rom_sha256": rom_hash, "nearest_4x": scaled_target})

    art_manifest = json.loads((ART / "import_report.json").read_text())
    source_hashes = json.loads((ART / "source_png_hashes.json").read_text())
    require(source_hashes.get("all_source_sha256_identical_before_after_import") is True,
            "Source-original preservation check is incomplete")
    for path, expected in source_hashes["source_files"].items():
        require(digest(source_path(path).read_bytes()) == expected, "Original source PNG changed: " + path)
    static_manifest = {"version": "v0.2.15", "kind": "Static native import PNGs; not emulator captures",
                       "dimensions": [24, 24], "smoothing": False,
                       "new_art_detail_drawn": False, "roles": {}, "files": []}
    for role in HEROES + COMMON_NPCS:
        static_manifest["roles"][role] = art_manifest["roles"][role]
        for direction in DIRECTIONS:
            for pose in (range(3) if role in HEROES else (0,)):
                path = ART / role / f"world_{direction}_{pose}_24x24.png"
                data = path.read_bytes()
                image = Image.open(io.BytesIO(data))
                require(image.mode == "RGBA" and image.size == (24, 24), "Invalid native import PNG: " + str(path))
                require(set(image.getchannel("A").get_flattened_data()) <= {0, 255}, "Nonbinary source alpha")
                target = f"assets/static_imports/{role}/{path.name}"
                files[target] = data
                static_manifest["files"].append({"path": target, "sha256": digest(data)})
    files["assets/manifest.json"] = json_bytes(static_manifest)
    files["assets/source_png_hashes.json"] = json_bytes(source_hashes)
    files["runtime/manifest.json"] = json_bytes({"rom_sha256": rom_hash, "captures": runtime_manifest})
    files["README.md"] = (
        "# Peon of Warcraft v0.2.15\n\n"
        "Ouvrir peon_of_warcraft_v0_2_15.gbc dans un émulateur Game Boy Color ou sur ModRetro.\n\n"
        "`runtime/` contient des captures natives160×144 de cette ROM testée et leurs agrandissements4×nearest. "
        "`assets/static_imports/` contient des PNG24×24 transparents réutilisables, issus de l'import natif ; "
        "cette galerie d'assets est distincte des captures du jeu. Les sprites sont agrandis sans lissage. "
        "Les Kolkar historiques sont seulement agrandis ; aucun nouveau dessin de Kolkar n'est revendiqué.\n\n"
        "`validation/` contient les preuves déclarées PASS. Le matériel physique ModRetro n'a pas été testé.\n\n"
        "ZIP déterministe : noms triés, date fixe et compression fixe. Chaque membre est relu avec son CRC "
        "et son SHA256 après écriture. `SHA256SUMS.txt` vérifie les fichiers du ZIP ; "
        "le SHA256 du ZIP lui-même est fourni dans le manifest externe et le fichier .zip.sha256, "
        "car un fichier ne peut pas contenir son propre hash sans circularité.\n"
    ).encode()
    manifest = {"version": "v0.2.15", "rom": BASE_NAME + ".gbc", "rom_sha256": rom_hash,
                "validation_sha256": digest(validation_path.read_bytes()),
                "physical_modretro_tested": False,
                "runtime": runtime_manifest, "assets": "assets/static_imports/",
                "files": {name: {"sha256": digest(data), "bytes": len(data)} for name, data in sorted(files.items())}}
    files["manifest.json"] = json_bytes(manifest)
    # The external manifest additionally contains the final ZIP hash. Exclude
    # that name from the portable checksum list so it also verifies the loose
    # release directory without an embedded/external-manifest mismatch.
    files["SHA256SUMS.txt"] = "".join(f"{digest(data)}  {name}\n"
                                      for name, data in sorted(files.items())
                                      if name != "manifest.json").encode()

    # All checks above finish before any release files or ROM bytes are copied.
    RELEASE.mkdir(parents=True, exist_ok=True)
    archive = RELEASE / (BASE_NAME + ".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for name, data in sorted(files.items()):
            require(not Path(name).is_absolute() and ".." not in Path(name).parts, "Unsafe ZIP member")
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 14, 0, 0, 0))
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
                      "runtime_captures": len(runtime_manifest), "transparent_pngs": len(static_manifest["files"]),
                      "release": str(RELEASE)}, indent=2))


if __name__ == "__main__":
    main()
