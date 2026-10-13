#!/usr/bin/env python3
"""Package the exact tested EXIT-to-title fix without changing prior releases."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.2.10"
BASE_SHA = "4530c718bf299ec9e1c8de8c52895906a81024345bd60717cd5c99dbd30b8a93"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    assert digest(rom) == args.expected_sha
    assert len(rom) == 2097152 and rom[0x143] == 0xC0
    assert rom[0x147:0x14A] == bytes((0x10, 6, 3))
    check = 0
    for value in rom[0x134:0x14D]:
        check = (check - value - 1) & 255
    assert check == rom[0x14D]
    assert (sum(rom) - rom[0x14E] - rom[0x14F]) & 65535 == int.from_bytes(rom[0x14E:0x150], "big")
    evidence = ROOT / "references/generated"
    reports = ["exit_title_v0210/validation.json",
               "browser_player_v0210/validation.json",
               "browser_player_v0210/warrior/validation.json",
               "browser_player_v0210/warlock/validation.json",
               "browser_player_v0210/core/validation.json",
               "browser_player_v0210/core/reset_lifecycle_validation.json"]
    proofs = []
    for name in reports:
        data = (evidence / name).read_bytes()
        report = json.loads(data)
        assert report.get("passed") is True and report["rom_sha256"] == args.expected_sha, name
        if "/core/" not in name and name.startswith("browser_"):
            exit_proof = report["native_exit_return_to_title"]
            assert exit_proof["passed"] and exit_proof["held_exit_confirmation_does_not_skip_title"], name
            assert exit_proof["continue_restores_saved_character_record"], name
        proofs.append({"file": name, "sha256": digest(data)})
    browser_dir = ROOT / "releases/browser-player-v0.2.10"
    browser = json.loads((browser_dir / "manifest.json").read_text())
    assert browser["browser_qa_passed"] and browser["rom_sha256"] == args.expected_sha
    assert digest((browser_dir / "peon_of_warcraft_v0_2_10_player.html").read_bytes()) == browser["player_sha256"]
    output = ROOT / "releases/v0.2.10"
    output.mkdir(parents=True, exist_ok=True)
    filename = "peon_of_warcraft_v0_2_10.gbc"
    (output / filename).write_bytes(rom)
    shutil.copy2(ROOT / "docs/V0_2_10_EXIT_TO_TITLE.md", output / "README.md")
    manifest = {
        "version": VERSION, "base_rom_sha256": BASE_SHA,
        "rom_sha256": args.expected_sha, "rom_bytes": len(rom),
        "cgb_only": True, "mapper": "MBC3+RTC+RAM+battery", "save_ram_bytes": 32768,
        "exit_returns_to_title": True, "requires_confirmation_release": True,
        "b_closes_menu": True, "exit_autosaves": False,
        "new_sprite_art_integrated": False, "save_layout_changed": False,
        "physical_chromatic_tested": False, "devday_flash_tested": False,
        "native_source_changed": ["engine/menus/start_menu.asm"],
        "passed_reports": proofs, "browser_player_sha256": browser["player_sha256"],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    archive = output / "peon_of_warcraft_v0_2_10.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as packed:
        files = [(output / filename, filename), (output / "README.md", "README.md"),
                 (output / "manifest.json", "manifest.json")]
        files += [(evidence / name, "validation/" + name) for name in reports]
        for source, target in files:
            info = zipfile.ZipInfo(target, date_time=(2026, 10, 13, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            packed.writestr(info, source.read_bytes())
    with zipfile.ZipFile(archive) as packed:
        assert packed.testzip() is None
        assert digest(packed.read(filename)) == args.expected_sha
    (output / "SHA256SUMS.txt").write_text("".join(
        digest(path.read_bytes()) + "  " + path.name + "\n" for path in [output / filename, archive]))
    print(json.dumps({"rom_sha256": args.expected_sha, "zip": str(archive),
                      "zip_sha256": digest(archive.read_bytes()), "native_and_browser_exit_passed": True}, indent=2))


if __name__ == "__main__":
    main()
