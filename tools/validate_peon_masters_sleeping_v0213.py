#!/usr/bin/env python3
"""Walk the training lodge and relocated lazy quest using ordinary buttons.

Only private fresh-ROM copies are opened; no emulator RAM writes, CPU
substitution, save states or user battery records are used.
"""
from pathlib import Path
import argparse
import hashlib
import json
import logging
import shutil
import tempfile
from PIL import Image

from validate_peon_earth_stone_v0212 import EarthSession, CLASSES

ROOT = Path(__file__).resolve().parents[1]
MASTER_IDS = (0x6a, 0x6b, 0x6c)
STANDS = (((6, 4), "up"), ((6, 5), "right"), ((3, 8), "up"))
SCRIPTS = ("PeonOrcHutShamanMasterScript", "PeonOrcHutWarriorMasterScript", "PeonOrcHutWarlockMasterScript")


class MasterSession(EarthSession):
    def live_actors(self, name):
        actors = super().live_actors(name)
        records = self.read("wObjectStructs", 13 * 40)
        follower_slots = {records[i * 40 + 1] for i in range(1, 13)
                          if records[i * 40] == 0x68}
        # Native IsNPCAtCoord explicitly ignores the friendly Imp. Its
        # transient slot15 replaces a map template; the static-source route
        # helper must not reinterpret that follower as a blocking cook.
        return [actor for actor in actors if actor["index"] not in follower_slots]

    def master_scene(self):
        assert self.map() == 22 and self.read("wBackupMapNumber") == [14]
        records = self.read("wObjectStructs", 13 * 40)
        masters = {}
        for i in range(13):
            actor = records[i * 40:(i + 1) * 40]
            if actor[0] not in MASTER_IDS:
                continue
            bank = 0 if actor[2] & 0x80 else 1
            tile = actor[2] & 0x7f
            role = ("shaman_master", "warrior_trainer", "enemy_warlock")[MASTER_IDS.index(actor[0])]
            expected = (ROOT / "gfx/large_masters_v0213" / (role + ".bin")).read_bytes()
            actual = bytes(self.p.memory[bank, 0x8000 + tile * 16:0x8000 + tile * 16 + len(expected)])
            assert actual == expected, ("Native master graphics mismatch", role, bank, tile)
            masters[role] = {"actor": actor[1], "sprite": actor[0], "world_xy": [actor[16] - 4, actor[17] - 4], "native_tile_bytes_exact": True}
        assert len(masters) == 3, ("All masters must have native object structs", masters)
        assert self.read("wMapObjects", 16 * 16)[16 + 1] == 0, "The attendant must be disabled before native actor allocation"
        assert not any(records[i * 40] and records[i * 40 + 1] == 1 for i in range(1, 13)), "No attendant live object in the lodge"
        oam = list(self.p.memory[0xfe00:0xfea0])
        visible = [(oam[i] - 16, oam[i + 1] - 8, oam[i + 2], oam[i + 3]) for i in range(0, 160, 4)
                   if 0 < oam[i + 1] < 168 and 8 < oam[i] < 160]
        rows = [sum(y <= row < y + 8 for y, x, tile, flags in visible) for row in range(144)]
        assert max(rows) <= 10, ("GBC scanline limit", max(rows))
        master_tiles = 0
        lcd = self.p.screen.image.convert("RGB")
        for actor in (records[i * 40:(i + 1) * 40] for i in range(13)):
            if actor[0] in MASTER_IDS:
                base = actor[2] & 0x7f
                bank_flag = 0 if actor[2] & 0x80 else 8
                master_tiles += sum(base <= tile < base + 9 and flags & 8 == bank_flag for y, x, tile, flags in visible)
                first = next((y, x) for y, x, tile, flags in visible if tile == base and flags & 8 == bank_flag)
                role = ("shaman_master", "warrior_trainer", "enemy_warlock")[MASTER_IDS.index(actor[0])]
                expected = Image.open(ROOT / "references/generated/large_masters_v0213" / (role + "_hardware.png")).convert("RGBA")
                checked = 0
                for py in range(24):
                    for px in range(24):
                        pixel = expected.getpixel((px, py))
                        if not pixel[3]:
                            continue
                        actual = lcd.getpixel((first[1] + px, first[0] + py))
                        assert actual == pixel[:3], ("Actual native LCD master pixel mismatch", role, px, py, actual, pixel)
                        checked += 1
                masters[role]["actual_native_lcd_opaque_pixels_exact"] = checked
        assert master_tiles == 27, ("Every complete master tile must reach native OAM", master_tiles)
        assert not any(records[i * 40] == 0x68 for i in range(13)), "Indoor follower should be hidden, not removed from party"
        return {"masters": masters, "native_visible_oam_objects": len(visible), "maximum_objects_on_one_scanline": max(rows), "complete_master_tiles_visible": master_tiles}

    def enter_lodge(self):
        self.navigate((5, 7), 22)
        self.navigate((5, 5))
        self.p.tick(90, True)

    def leave_lodge(self):
        # Crystal may use the first short D-pad tap only to turn in place.
        # The normal navigator repeats taps until the real downward warp.
        self.navigate((5, 9), 14)
        assert self.map() == 14

    def talk_master(self, index):
        stand, facing = STANDS[index]
        self.talk_at(stand, facing, "master_" + CLASSES[index] + "_dialogue", False)
        # Let the native character printer finish both full name lines.
        self.p.tick(120, True)
        self.capture("master_" + CLASSES[index] + "_dialogue")
        assert self.read("hLastTalked") == [index + 2], ("Speaker must stay the real lodge actor", index, self.read("hLastTalked"))
        if index != self.class_index:
            self.close_dialogue()
            assert not self.read("wScriptMode")[0]
            return {"other_class_refused": True, "real_portrait_actor": index + 2}
        for _ in range(60):
            if self.phase == "main":
                break
            self.press("a", 30)
        assert self.phase == "main", ("Class trainer menu did not open", index, self.phase)
        self.capture("master_" + CLASSES[index] + "_native_training_menu")
        self.press("b", 120)
        self.wait_for(lambda: not self.read("wScriptMode")[0], buttons=False)
        return {"matching_native_trainer_opened": True, "normal_B_exit": True, "real_portrait_actor": index + 2}

    def cold_continue_in_lodge(self):
        self.navigate((5, 5))
        self.press("left", 30)  # blocked table: face scenery, not a master
        assert self.position() == (5, 5)
        def record():
            count = self.read("wPartyCount")[0]
            stride = self.sym["wPartyMon2Species"][1] - self.sym["wPartyMon1Species"][1]
            return {"party_count": count, "party": self.read("wPartyMon1Species", stride * count),
                    "names": self.read("wPartyMonNicknames", 11 * count),
                    "events": self.read("wEventFlags", 256), "money": self.read("wMoney", 3),
                    "class_flags": [self.event("EVENT_PEON_WARRIOR"), self.event("EVENT_PEON_WARLOCK")],
                    "map": self.map(), "position": self.position()}
        before = record()
        self.press("start")
        def cursor_step(key):
            # Human-style hold until the actual menu acknowledges the D-pad.
            # Four-frame synthetic taps can end inside WaitBGMap before its
            # native input poll; keep the button held until one cursor move.
            old = self.read("wMenuCursorY")[0]
            self.p.button_press(key)
            for _ in range(180):
                self.p.tick(1, True)
                if self.read("wMenuCursorY")[0] != old:
                    break
            self.p.button_release(key)
            self.p.tick(24, True)
        for _ in range(12):
            if self.read("wMenuCursorPosition")[0] == 1:
                break
            cursor_step("up")
        # Select the actual native SAVE row, rather than assuming three
        # short taps all passed JoyTextDelay's input cadence.
        for _ in range(12):
            if self.read("wMenuCursorPosition")[0] == 4:
                break
            cursor_step("down")
        assert self.read("wMenuCursorPosition") == [4], {
            "save_cursor": self.read("wMenuCursorPosition"),
            "menu_cursor_y": self.read("wMenuCursorY"),
            "menu_joypad": self.read("wMenuJoypad"),
            "joy_down": self.read("hJoyDown"), "joy_pressed": self.read("hJoyPressed"),
            "menu_items": self.read("wMenuItemsList", 8), "pc": hex(self.p.register_file.PC),
            "rom_bank": self.read("hROMBank"), "window_stack": self.read("wWindowStackPointer", 2),
            "menu_joypad_filter": self.read("wMenuJoypadFilter"),
            "cursor_rows": self.read("w2DMenuNumRows"), "cursor_flags": self.read("w2DMenuFlags1"),
            "presentation": self.presentation,
        }
        saves = self.saves
        for _ in range(80):
            if self.saves > saves:
                break
            self.p.button("a", delay=16)
            self.p.tick(120, True)
        assert self.saves == saves + 1, ("The native save routine must actually run", {
            "saves": self.saves, "previous": saves, "cursor": self.read("wMenuCursorPosition"),
            "position": self.position(), "presentation": self.presentation, "input_type": self.read("wInputType"),
            "paused": self.read("wGameLogicPaused"), "joypad_disable": self.read("wJoypadDisable"),
        })
        self.p.tick(360, True)
        for _ in range(12):
            if self.presentation == "world" and not self.read("wScriptMode")[0]:
                break
            self.press("b", 90)
        self.capture("training_lodge_battery_saved")
        self.p.stop(save=True)
        battery = Path(str(self.rom) + ".ram")
        assert battery.stat().st_size == 32768
        self.open()
        self.p.tick(240, True)
        self.press("start", 90)
        for _ in range(120):
            if self.map() == 22 and not self.read("wScriptMode")[0] and self.presentation == "world":
                break
            self.press("a", 90)
        assert self.map() == 22 and self.presentation == "world"
        self.p.tick(120, True)
        after = record()
        assert before == after, ("Cold Continue changed the saved character/quest/party", before, after)
        scene = self.master_scene()
        self.capture("training_lodge_cold_continue_native_lcd")
        return {"private_battery_bytes": 32768, "party_names_moves_hp_and_flags_preserved": True,
                "current_three_master_scene": scene}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "pokecrystal.gbc")
    parser.add_argument("--sym", type=Path, default=ROOT / "pokecrystal.sym")
    parser.add_argument("--output", type=Path, default=ROOT / "references/generated/masters_sleeping_v0213")
    parser.add_argument("--expected-rom-sha256")
    parser.add_argument("--classes", default="shaman,warrior,warlock")
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    digest = hashlib.sha256(args.rom.read_bytes()).hexdigest()
    if args.expected_rom_sha256:
        assert digest == args.expected_rom_sha256
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"rom_sha256": digest, "ordinary_buttons_only": True, "ram_edits": False,
              "emulator_states_loaded": False, "user_battery_records_opened": False, "classes": {}, "status": "RUNNING"}
    symbols = {}
    for line in args.sym.read_text().splitlines():
        fields = line.split()
        if len(fields) == 2 and ":" in fields[0]:
            symbols[fields[1]] = tuple(int(n, 16) for n in fields[0].split(":"))
    with tempfile.TemporaryDirectory(prefix="peon-masters-sleeping-v0213-") as temp:
        for name in args.classes.split(","):
            index = CLASSES.index(name)
            rom = Path(temp) / (name + ".gbc")
            shutil.copyfile(args.rom, rom)
            session = MasterSession(rom, symbols, index, args.output)
            try:
                session.fresh_class()
                session.enter_lodge()
                scene = session.master_scene()
                session.capture("all_three_complete_large_masters_native_lcd")
                trainer = [session.talk_master(i) for i in range(3)]
                session.leave_lodge()
                assert session.read("wPartyCount") == [2 if index == 2 else 1]
                if index == 2:
                    assert session.read("wPartyMon2Species") == [74]
                    assert session.read("wObjectFollow_Follower")[0] not in (0, 255), "World imp returns outdoors"
                session.talk_at((8, 16), "up", "foreman_accept_relocated_lazy_quest")
                assert session.event("EVENT_PEON_LAZY_ACCEPTED")
                session.travel(15)
                session.talk_at((20, 14), "up", "zone_two_sleeping_peon_wakes")
                assert session.read("hLastTalked") == [12]
                assert session.event("EVENT_PEON_LAZY_AWAKE")
                assert not session.event("EVENT_PEON_LAZY_DONE")
                session.travel(14)
                money = session.money()
                session.talk_at((8, 16), "up", "foreman_lazy_quest_reward")
                assert session.event("EVENT_PEON_LAZY_DONE")
                assert session.money() == money + 100
                session.talk_at((8, 16), "up", "foreman_reward_cannot_duplicate")
                assert session.money() == money + 100
                session.enter_lodge()
                restart = session.cold_continue_in_lodge()
                if index == 2:
                    session.leave_lodge()
                    assert session.read("wPartyCount") == [2]
                    assert session.read("wPartyMon2Species") == [74]
                    assert session.read("wObjectFollow_Follower")[0] not in (0, 255)
                    records = session.read("wObjectStructs", 13 * 40)
                    assert any(records[i * 40] == 0x68 for i in range(1, 13))
                    session.capture("cold_continue_outdoor_imp_restored")
                    restart["walking_imp_restored_outdoors_after_cold_continue"] = True
                report["classes"][name] = {"scene": scene, "trainer_interactions": trainer,
                    "sleeping_worker_zone_two": [20, 13], "native_wake_flag": True,
                    "reward_once_only": 100, "native_party_preserved": True, "cold_continue_in_lodge": restart}
            except Exception:
                session.capture("failure")
                # Keep a disposable failure battery as local diagnostic
                # evidence outside the tracked repository; user saves remain
                # unopened. Successful private batteries are discarded.
                battery = Path(str(session.rom) + ".ram")
                if battery.is_file():
                    evidence = Path("/tmp/peon-masters-sleeping-failure-" + digest[:8])
                    evidence.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(battery, evidence / (name + ".ram"))
                report["status"] = "FAILED"
                (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
                raise
            finally:
                session.p.stop(save=False)
    report["status"] = "PASSED"
    (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
