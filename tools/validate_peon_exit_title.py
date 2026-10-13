#!/usr/bin/env python3
"""Exercise native EXIT -> title -> START -> Continue using real input only.

Every run owns a temporary ROM/battery copy. Hooks observe control flow; there
are no emulator-state loads, RAM writes, or injected coordinates. Legacy saves
are explicitly upgraded with one ordinary native SAVE before EXIT checks;
EXIT itself never saves. Fixtures are genuine batteries from prior save tests.
"""
import argparse
import hashlib
import json
import logging
import shutil
import tempfile
from pathlib import Path

from pyboy import PyBoy

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "references/generated/exit_title_v0210"
CLASSES = ("shaman", "warrior", "warlock")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def symbols(path):
    result = {}
    for row in Path(path).read_text().splitlines():
        fields = row.split()
        if len(fields) == 2 and ":" in fields[0]:
            result[fields[1]] = tuple(int(part, 16) for part in fields[0].split(":"))
    return result


class ExitSession:
    def __init__(self, rom, sym, output):
        self.rom, self.sym, self.output = Path(rom), sym, Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.phase, self.trace = "boot", []
        self.counts = {"reset": 0, "exit": 0, "save": 0, "new_game": 0,
                       "title": 0, "continue": 0, "b_cancel": 0}
        self.p = PyBoy(str(rom), window="null", sound_emulated=True, log_level="ERROR")
        self.p.set_emulation_speed(0)
        phases = {"PeonTitleScreen.wait": "title",
                  "PeonCharacterSelect.input": "select",
                  "StartMenu.loop": "start_menu",
                  "HandleMapTimeAndJoypad": "world"}
        for label, phase in phases.items():
            self.p.hook_register(*sym[label], self.set_phase, phase)
        counters = {"Reset": "reset", "StartMenu_Exit": "exit",
                    "_SaveGameData": "save", "NewGame": "new_game",
                    "PeonTitleScreen": "title", "Continue": "continue",
                    "StartMenu.Exit": "b_cancel"}
        for label, counter in counters.items():
            self.p.hook_register(*sym[label], self.count, counter)

    def count(self, counter):
        if counter == "exit":
            # The release-loop label shares this entry address; repeated
            # read-only hook visits are one logical EXIT selection.
            if self.phase != "exit_release":
                self.counts[counter] += 1
                self.set_phase("exit_release")
            return
        self.counts[counter] += 1

    def set_phase(self, phase):
        if phase != self.phase:
            self.trace.append({"frame": self.p.frame_count, "phase": phase})
        self.phase = phase

    def read(self, name, length=1):
        bank, address = self.sym[name]
        return list(self.p.memory[address:address + length] if address >= 0xe000
                    else self.p.memory[bank, address:address + length])

    def step(self, frames):
        self.p.tick(frames, True)

    def tap(self, key, settle=90, held=8):
        self.p.button_press(key)
        self.step(held)
        self.p.button_release(key)
        self.step(settle)

    def wait(self, phase, budget=1800):
        for _ in range(budget // 10 + 1):
            if self.phase == phase:
                self.step(30)
                assert self.phase == phase, ("phase not settled", phase, self.phase)
                return
            self.step(10)
        raise AssertionError(("native screen did not become ready", phase, self.phase, self.counts))

    def capture(self, label):
        # Genuine 160x144 framebuffer, without source-art substitutions.
        self.p.screen.image.save(self.output / (label + ".png"))

    def full_sram(self):
        # PyBoy 2.7 rejects a slice ending at the exclusive bank boundary.
        return b"".join(bytes(self.p.memory[bank, 0xa000:0xbfff])
                        + bytes([self.p.memory[bank, 0xbfff]]) for bank in range(4))

    def compare_sram(self, before):
        after = self.full_sram()
        changed = [index for index, (old, new) in enumerate(zip(before, after)) if old != new]
        bank, address = self.sym["sScratch"]
        start = bank * 8192 + address - 0xa000
        # ram/sram.asm explicitly reserves 0x60 16-byte graphics tiles. This
        # is disposable scratch, not either native save record/checksum.
        assert all(start <= index < start + 0x60 * 16 for index in changed), (
            "EXIT/title changed persisted SRAM outside graphics scratch", changed)
        return {"all_32768_sram_bytes_equal": not changed,
                "saved_sram_outside_declared_graphics_scratch_equal": True,
                "graphics_scratch_region": {"bank": bank, "address": address, "bytes": 0x60 * 16},
                "graphics_scratch_changed_offsets": changed}

    def complete_record(self):
        lengths = {"wPlayerName": 11, "wPlayerID": 2, "wPartyCount": 1,
                   "wPartySpecies": 7, "wPartyMon1": 6 * 48,
                   "wPartyMonOTs": 6 * 11, "wPartyMonNicknames": 6 * 11,
                   "wEventFlags": 256, "wMoney": 3, "wMomsMoney": 3,
                   "wTMsHMs": 57, "wNumItems": 1, "wNumKeyItems": 1,
                   "wNumBalls": 1, "wNumPCItems": 1, "wMapGroup": 2,
                   "wXCoord": 1, "wYCoord": 1, "wBackupWarpNumber": 1,
                   "wBackupMapGroup": 1, "wBackupMapNumber": 1,
                   "wPokedexCaught": 32, "wPokedexSeen": 32}
        record = {name: self.read(name, length) for name, length in lengths.items()}
        for name, count, width in (("wItems", "wNumItems", 2),
                                   ("wKeyItems", "wNumKeyItems", 1),
                                   ("wBalls", "wNumBalls", 2),
                                   ("wPCItems", "wNumPCItems", 2)):
            record[name] = self.read(name, record[count][0] * width + 1)
        return record

    def continue_from_title(self):
        self.wait("title")
        self.tap("start")
        self.wait("select")
        assert self.read("wMenuCursorY") == [0], "Continue must be preselected"
        self.tap("a", 240)
        self.wait("world")
        self.step(120)
        assert self.read("wScriptMode") == [0] and self.read("wBattleMode") == [0]

    def open_menu(self):
        self.tap("start")
        self.wait("start_menu")
        assert self.read("wMenuItemsList", 8) == [7, 1, 2, 3, 4, 9, 5, 6]

    def select_exit(self):
        self.open_menu()
        for _ in range(8):
            if self.read("wMenuCursorPosition") == [7]:
                break
            self.tap("down", 30)
        assert self.read("wMenuCursorPosition") == [7]
        self.capture("exit_highlighted")

    def save_legacy_upgrade(self):
        # A v028 Warlock has no stored Imp yet. Explicitly saving its normal
        # v029 migration makes that new ally part of the last native save.
        before = self.counts["save"]
        self.open_menu()
        for _ in range(8):
            cursor = self.read("wMenuCursorPosition")[0]
            if cursor == 4:
                break
            self.tap("up" if cursor > 4 else "down", 30)
        assert self.read("wMenuCursorPosition") == [4]
        self.tap("a")
        for _ in range(15):
            if self.counts["save"] > before and self.phase == "world":
                break
            self.tap("a", 180)
        self.wait("world")
        assert self.counts["save"] == before + 1
        self.step(90)
        self.capture("explicit_native_legacy_upgrade_saved")

    def walk_unsaved(self):
        before = self.complete_record()
        for direction in ("right", "left", "down", "up"):
            # Crystal can use the first tap to turn. Releasing before the
            # 16-frame step finishes prevents a buffered second step.
            for _ in range(8):
                self.tap(direction, 40, 4)
                if self.read("wXCoord") != before["wXCoord"] or self.read("wYCoord") != before["wYCoord"]:
                    assert self.phase == "world" and self.read("wMapGroup", 2) == before["wMapGroup"]
                    return before, self.complete_record()
        raise AssertionError("Fixture cannot move in any adjacent direction")

    def verify(self, legacy=False):
        self.continue_from_title()
        if legacy:
            self.save_legacy_upgrade()
        baseline = self.complete_record()
        self.capture("original_saved_location")
        assert self.counts["continue"] == 1 and self.counts["new_game"] == 0
        rows = []
        for cycle, held_frames in enumerate((8, 240, 8), 1):
            self.open_menu()
            cancel_before, reset_before = self.counts["b_cancel"], self.counts["reset"]
            self.tap("b")
            self.wait("world")
            assert self.counts["b_cancel"] == cancel_before + 1
            assert self.counts["reset"] == reset_before and self.complete_record() == baseline
            _, moved = self.walk_unsaved()
            self.capture(f"cycle_{cycle}_unsaved_walk")
            assert (moved["wXCoord"], moved["wYCoord"]) != (baseline["wXCoord"], baseline["wYCoord"])
            before = self.counts.copy()
            self.select_exit()
            sram_before = self.full_sram()
            self.p.button_press("a")
            self.step(held_frames)
            if held_frames == 240:
                assert self.counts["exit"] == before["exit"] + 1
                assert self.counts["reset"] == before["reset"], "EXIT must await confirmation release"
                assert self.full_sram() == sram_before
            self.p.button_release("a")
            self.step(420)
            self.wait("title")
            assert self.counts["reset"] == before["reset"] + 1
            assert self.counts["exit"] == before["exit"] + 1
            assert self.counts["save"] == before["save"] == int(legacy)
            assert self.counts["new_game"] == 0 and self.read("hCGB") == [1]
            sram_comparison = self.compare_sram(sram_before)
            title_frame = hashlib.sha256(self.p.screen.ndarray.tobytes()).hexdigest()
            self.capture(f"cycle_{cycle}_returned_title")
            self.step(600)
            assert self.phase == "title" and self.counts["continue"] == before["continue"]
            assert hashlib.sha256(self.p.screen.ndarray.tobytes()).hexdigest() == title_frame
            assert self.compare_sram(sram_before) == sram_comparison
            self.continue_from_title()
            after = self.complete_record()
            assert after == baseline, ("Continue differs from last native save", cycle,
                                       [key for key in baseline if baseline[key] != after[key]])
            assert self.counts["save"] == int(legacy) and self.counts["new_game"] == 0
            self.capture(f"cycle_{cycle}_continued_saved_location")
            rows.append({"cycle": cycle, "exit_confirm_held_frames": held_frames,
                         "b_cancels_without_reset": True, "unsaved_walk_discarded": True,
                         "held_confirmation_waits_for_release": held_frames == 240,
                         "exit_enters_native_reset_once": True, "title_waits_for_fresh_start": True,
                         "idle_title_verified_frames": 600, "sram_comparison": sram_comparison,
                         "saved_identity_party_bags_events_money_location_equal": True,
                         "cgb_mode_retained": True})
        return {"cycles": rows, "native_counts": self.counts,
                "legacy_explicit_native_upgrade_save": legacy,
                "saved_record": baseline, "trace": self.trace}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--symbols", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--batteries", type=Path,
                        default=Path("/tmp/peon_v029_old_class_batteries"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    assert sha(args.rom) == args.expected_sha, "Wrong ROM candidate"
    sym = symbols(args.symbols)
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"rom_sha256": sha(args.rom), "symbols_sha256": sha(args.symbols),
              "ordinary_buttons_only": True, "ram_writes": False,
              "emulator_states_loaded": False, "physical_console_tested": False,
              "routes": {}, "legacy_v028_routes": {}, "passed": False}
    session = None
    try:
        with tempfile.TemporaryDirectory(prefix="peon-exit-title-") as directory:
            for suffix, report_key in (("upgraded_v029", "routes"), ("v028", "legacy_v028_routes")):
                for slug in CLASSES:
                    label = slug if suffix == "upgraded_v029" else f"{slug}_old_v028"
                    original = args.batteries / f"{slug}_{suffix}.gbc.ram"
                    assert original.stat().st_size == 32768
                    original_sha = sha(original)
                    rom = Path(directory) / f"{label}.gbc"
                    shutil.copyfile(args.rom, rom)
                    shutil.copyfile(original, Path(str(rom) + ".ram"))
                    session = ExitSession(rom, sym, args.output / label)
                    result = session.verify(legacy=suffix == "v028")
                    session.p.stop(save=True)
                    session = None
                    assert sha(original) == original_sha, "Original fixture changed"
                    result["original_battery_sha256"] = original_sha
                    result["original_battery_preserved"] = True
                    result["final_battery_bytes"] = Path(str(rom) + ".ram").stat().st_size
                    assert result["final_battery_bytes"] == 32768
                    report[report_key][slug] = result
                    print(f"PASS {label}: B cancels; three EXIT/title/Continue cycles preserve native save", flush=True)
        report["passed"] = True
    except Exception as error:
        report["error"] = repr(error)
        if session is not None:
            session.capture("first_failure")
            report["failure_phase"] = session.phase
            report["failure_counts"] = session.counts
            report["failure_trace"] = session.trace
        raise
    finally:
        if session is not None:
            session.p.stop(save=False)
        (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
