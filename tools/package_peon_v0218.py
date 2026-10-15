#!/usr/bin/env python3
"""Package the validated v0.2.18 selection screens, without regenerating art.

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
from pathlib import Path
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
VERSION = "v0.2.18"
BASE = "peon_of_warcraft_v0_2_18"
RELEASE = ROOT / "releases" / VERSION
SCENES = ROOT / "gfx/welcome_scenes_v0218"
PORTRAITS = ROOT / "gfx/class_portraits_v0218"
LABELS = ROOT / "gfx/selection_labels_v0218"


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
                  "native_packet_files": [], "world_and_combat": "Unchanged from v0.2.17; not rebundled"}

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
    require(passed(scene_manifest), "Welcome scene import is not PASS")
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
    require(passed(portrait_manifest), "Master portrait import is not PASS")
    require(set(portrait_manifest["roles"]) == {"kento", "zogzog", "bismillah"}, "Expected three master portraits")
    add(PORTRAITS / "manifest.json")
    for role, record in portrait_manifest["roles"].items():
        old = original({"path": record["source"], "sha256": record["source_sha256"]}, (64, 68)).convert("RGBA")
        folder = PORTRAITS / role
        outputs = record["outputs"]
        expected = {str((folder / name).relative_to(ROOT)): length for name, length in (
            ("portrait.2bpp", 1152), ("attrs.bin", 72), ("palettes.bin", 40), ("hardware.png", None))}
        require(set(outputs) == set(expected), "Portrait outputs differ from native ABI")
        payloads = {Path(path).name: checked_file(path, outputs[path], length)
                    for path, length in expected.items()}
        for name in ("portrait.2bpp", "attrs.bin", "palettes.bin"):
            provenance["native_packet_files"].append(add(folder / name, payloads[name]))
        require(set(payloads["attrs.bin"]) <= set(range(3, 8)), "Portrait uses an unallocated palette")
        palette = colors(payloads["palettes.bin"])
        decoded = Image.new("RGB", (64, 72))
        for tile, attr in enumerate(payloads["attrs.bin"]):
            index = (attr - 3) * 4
            paint_tile(decoded, payloads["portrait.2bpp"][tile * 16:(tile + 1) * 16],
                       tile % 8 * 8, tile // 8 * 8, palette[index:index + 4])
        hardware = png(payloads["hardware.png"], (64, 72), rgba=True)
        require(hardware.convert("RGB").tobytes() == decoded.tobytes(), "Portrait PNG differs from packet decode")
        padded = Image.new("RGBA", (64, 72))
        padded.paste(old, (0, 0))
        require(padded.getchannel("A").tobytes() == hardware.getchannel("A").tobytes(),
                "Portrait changed original silhouette/alpha coordinates")
        provenance["primary_static_PNGs"].append(add(folder / "hardware.png", payloads["hardware.png"]))
        preview = io.BytesIO()
        decoded.save(preview, format="PNG")
        provenance["opaque_portrait_previews"].append(add(folder / "hardware_bg.png", preview.getvalue()))

    label_manifest = json.loads((LABELS / "manifest.json").read_bytes())
    require(passed(label_manifest) and label_manifest["tiles"] == 24
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
        require(previous.get("rom_sha256") == rom_hash, "v0.2.18 already contains a different ROM")
    if (RELEASE / (BASE + ".gbc")).is_file():
        require(sha((RELEASE / (BASE + ".gbc")).read_bytes()) == rom_hash, "Existing v18 loose ROM differs")
    if (RELEASE / (BASE + ".zip")).is_file():
        with zipfile.ZipFile(RELEASE / (BASE + ".zip")) as old:
            require(sha(old.read(BASE + ".gbc")) == rom_hash, "Existing v18 ZIP contains a different ROM")
    files = {BASE + ".gbc": rom, BASE + ".sym": sym, BASE + ".map": map_data}
    validation_path = args.validation_root.resolve() / "validation.json"
    validation, reports, captures = collect_validation(validation_path, rom, sym, map_data, files)
    provenance = collect_assets(files)
    files["README.md"] = (
        "# Peon of Warcraft v0.2.18\n\n"
        "Ouvrir peon_of_warcraft_v0_2_18.gbc dans un émulateur Game Boy Color ou sur ModRetro.\n\n"
        "Cette version ajoute un accueil illustré dans Durotar, quatre images de classe et les "
        "portraits des trois maîtres. Les personnages du monde et de combat restent ceux de v0.2.17.\n\n"
        "runtime/ contient uniquement les captures 160×144 de cette ROM déclarées par les tests, "
        "avec leurs copies 4× sans lissage. assets/native_selection/ contient sept PNG natifs "
        "statiques (quatre scènes et trois portraits), les trois aperçus opaques hardware_bg.png, "
        "les tuiles 2bpp, cartes, attributs, palettes et manifests. Ces images statiques ne sont "
        "pas des captures du jeu. Les libellés utilisent 24 tuiles de texte compact.\n\n"
        "Les trois grandes illustrations et les trois portraits originaux 64×68 restent intacts "
        "dans le dépôt et sont revérifiés par SHA256. Leurs chemins et leur provenance figurent "
        "dans assets/source_provenance.json ; les grands PNG ne sont pas dupliqués dans le ZIP. "
        "Les scènes sont des conversions natives avec perte de couleurs et réduction sans "
        "lissage ; les portraits conservent leur géométrie avec quatre lignes transparentes "
        "de marge inférieure. Aucune récupération de grille native des grandes illustrations "
        "n'est revendiquée.\n\n"
        "validation/ contient les rapports PASS portant sur le SHA256 exact de la ROM. "
        "Le matériel physique ModRetro n'a pas été testé.\n\n"
        "ZIP déterministe : noms triés, date fixe 2026-10-15, compression fixe ; tous les membres "
        "sont relus avec CRC et SHA256, et la ROM embarquée est identique au fichier fourni. "
        "SHA256SUMS.txt couvre les contenus hors manifest ; le manifest externe et le fichier "
        ".zip.sha256 fournissent le SHA256 du ZIP sans hash autoréférentiel.\n"
    ).encode()
    manifest = {"version": VERSION, "rom": BASE + ".gbc", "rom_sha256": rom_hash,
        "sym_sha256": sha(sym), "map_sha256": sha(map_data),
        "validation_sha256": sha(validation_path.read_bytes()), "tests": reports,
        "physical_modretro_tested": False, "runtime": captures,
        "static_primary_native_PNGs": provenance["primary_static_PNGs"],
        "opaque_portrait_previews": provenance["opaque_portrait_previews"],
        "source_provenance": "assets/source_provenance.json",
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
