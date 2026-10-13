#!/usr/bin/env python3
"""Play the earth-stone chain with ordinary buttons in private ROM copies.

RAM/ROM writes, CPU substitutions, emulator states and user saves are forbidden.
Read-only hooks count native capture rolls, naming, team screens and real saves.
"""
from collections import deque
from pathlib import Path
import argparse
import hashlib
import json
import logging
import re
import shutil
import tempfile

from PIL import Image
from validate_peon_warlock_pet import PetSession
from validate_peon_villages import MAPS, DIRECTIONS, warp_tiles
from validate_durotar_v022_quests import all_actors, triggers
from validate_peon_exit_title import symbols, ExitSession
from validate_peon_deep_ui import text_encoding
from peon_event_flags_v029 import event_indices

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "references/generated/earth_stone_quest_v0212"
CLASSES = ("shaman", "warrior", "warlock")
QUEST_FLAGS = tuple("EVENT_PEON_EARTH_STONE_" + suffix
                    for suffix in ("ACCEPTED", "FOUND", "REPORTED", "DONE"))
MAPS.update({12: ("PeonOpening", 8, 6), 13: ("GrommashHold", 8, 6)})


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class EarthSession(PetSession):
    def __init__(self, rom, sym, index, folder):
        self.folder = folder / CLASSES[index]
        self.folder.mkdir(parents=True, exist_ok=True)
        self.events = []
        self.rolls = []
        self.pending_roll = None
        self.naming_entries = 0
        self.saves = 0
        self.team_entries = 0
        self.capture_retries = []
        self.team_icon_checks = []
        self.presentation = "boot"
        self.rom_bytes = Path(rom).read_bytes()
        super().__init__(rom, sym, index)
        self.flags = event_indices()

    def write(self, *args, **kwargs):
        raise AssertionError("Ordinary-control validation forbids emulator writes.")

    def open(self):
        super().open()
        for label, phase in (("HandleMapTimeAndJoypad", "world"),
                             ("PeonTitleScreen.wait", "title"),
                             ("PeonCharacterSelect.input", "select"),
                             ("StartMenu.loop", "start")):
            self.p.hook_register(*self.sym[label],
                                 lambda value: setattr(self, "presentation", value), phase)
        self.p.hook_register(*self.sym["_SaveGameData"],
                             lambda _: setattr(self, "saves", self.saves + 1), None)
        self.p.hook_register(*self.sym["_NamingScreen"],
                             lambda _: setattr(self, "naming_entries", self.naming_entries + 1), None)
        self.p.hook_register(*self.sym["PeonTeamPickV029.input"],
                             lambda _: setattr(self, "team_entries", self.team_entries + 1), None)
        self.p.hook_register(*self.sym["PeonTryRecruitV029.BaseBallRoll"], self.roll_enter, None)
        self.p.hook_register(*self.sym["PeonTryRecruitV029.success"], self.roll_success, None)
        self.p.hook_register(*self.sym["PeonTryRecruitV029.joined"], self.roll_finish, True)
        self.p.hook_register(*self.sym["PeonTryRecruitV029.miss"], self.roll_finish, False)

    def press(self, key, frames=90):
        self.p.button(key, delay=4)
        self.p.tick(frames, True)
        if not self.read("wBattleMode")[0] and self.phase in (
                "battle", "battle_drawing", "using_item"):
            self.phase, self.context = "overworld", None

    def capture(self, label):
        self.p.screen.image.save(self.folder / (label + ".png"))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(
            self.folder / (label + "_4x.png"))
        print(CLASSES[self.class_index], label, self.map(), self.position(),
              self.phase, self.quest(), flush=True)

    def wait_for(self, predicate, buttons=False, limit=600):
        for _ in range(limit):
            if predicate():
                return
            if buttons:
                self.press("a", 40)
            else:
                self.p.tick(12, True)
        self.capture("failure_timeout")
        raise AssertionError(("Native input wait expired", self.phase, self.presentation,
                              self.map(), self.position(), self.quest(),
                              hex(self.p.register_file.PC)))

    def quest(self):
        return {name.rsplit("_", 1)[1].lower(): self.event(name) for name in QUEST_FLAGS}

    def keys(self):
        return self.read("wKeyItems", self.read("wNumKeyItems")[0])

    def word(self, name):
        return int.from_bytes(bytes(self.read(name, 2)), "big")

    def collision_at(self, x, y):
        _, width, height = MAPS[self.map()]
        if not (0 <= x < width * 2 and 0 <= y < height * 2):
            return "WALL"
        bank, address = self.sym["wOverworldMapBlocks"]
        block = self.p.memory[bank, address + (y // 2 + 3) * (width + 6) + x // 2 + 3]
        if not block:
            return "WALL"
        coll_bank = self.read("wTilesetCollisionBank")[0]
        pointer = self.read("wTilesetCollisionAddress", 2)
        coll_address = pointer[0] | pointer[1] << 8
        value = self.p.memory[coll_bank, coll_address + block * 4 + y % 2 * 2 + x % 2]
        return "WALL" if value == 7 else "FLOOR"

    def live_actors(self, name):
        masks = self.read("wObjectMasks", 16)
        structs = self.read("wObjectStructs", 13 * 40)
        result = []
        for actor in all_actors(name):
            index = actor["index"]
            if masks[index] or actor["sprite"] == "SPRITE_NONE":
                continue
            if actor["sprite"].startswith("SPRITE_PEON_QUEST"):
                continue  # Native decorative glyphs do not block walking/talking.
            if actor["event"] != "-1" and self.event(actor["event"]):
                continue
            for offset in range(40, 13 * 40, 40):
                record = structs[offset:offset + 40]
                if record[0] and record[1] == index:
                    actor = dict(actor, xy=(record[16] - 4, record[17] - 4))
                    break
            result.append(actor)
        return result

    def path(self, target):
        name = MAPS[self.map()][0]
        occupied = {actor["xy"] for actor in self.live_actors(name)}
        danger = set(triggers(name))
        warps = self.native_warps(name)
        queue, seen = deque([(self.position(), [])]), {self.position()}
        while queue:
            (x, y), route = queue.popleft()
            if (x, y) == target:
                return route
            for key, dx, dy in DIRECTIONS:
                point = (x + dx, y + dy)
                if point in seen or point in occupied or self.collision_at(*point) == "WALL":
                    continue
                if point in warps | danger and point != target:
                    continue
                seen.add(point)
                queue.append((point, route + [key]))
        raise AssertionError(("No ordinary route", name, self.position(), target, occupied))

    def native_warps(self, name):
        bank, address = self.sym[name + "_MapEvents"]
        offset = bank * 0x4000 + address - 0x4000
        count = self.rom_bytes[offset + 2]
        return {(self.rom_bytes[offset + 4 + i * 5],
                 self.rom_bytes[offset + 3 + i * 5]) for i in range(count)}

    def navigate(self, target, expected_map=None):
        target = tuple(target)
        origin = self.map()
        for _ in range(240):
            if expected_map is not None and self.map() == expected_map:
                self.p.tick(180, True)
                return
            if self.map() == origin and self.position() == target:
                if expected_map is None:
                    self.p.tick(40, True)
                    return
                # Coordinates update before the native door/fade commits its
                # map number. Let that pending transition finish normally.
                self.p.tick(180, True)
                if self.map() == expected_map:
                    return
                # A saved/arrival portal requires stepping away before reentry.
                for key, dx, dy in DIRECTIONS:
                    point = (target[0] + dx, target[1] + dy)
                    if self.collision_at(*point) != "WALL" and point not in self.native_warps(MAPS[origin][0]):
                        self.press(key, 40)
                        break
                continue
            route = self.path(target)
            assert route, ("Empty route to portal", origin, target)
            self.press(route[0], 40)
        raise AssertionError(("Navigation budget", origin, target, expected_map,
                              self.map(), self.position()))

    def travel(self, destination):
        if self.map() == 23:
            portal = next(iter(self.native_warps("PeonOrcInn")))
            self.navigate((portal[0], portal[1] - 1))
            self.press("down", 40)
            self.p.tick(180, True)
            assert self.map() == 14
        if self.map() == 14 and destination in (15, 25):
            self.navigate((20, 10), 15)
        if self.map() == 25 and destination in (15, 14):
            self.navigate((5, 9), 15)
        if self.map() == 15 and destination == 25:
            self.navigate((16, 0), 25)
        if self.map() == 15 and destination == 14:
            self.navigate((4, 12), 14)
        assert self.map() == destination, ("Travel route", self.map(), destination)

    def talk_at(self, point, facing, label, close=True):
        self.navigate(point)
        before = self.position()
        self.press(facing, 30)
        assert self.position() == before, (label, "Moved into speaker")
        self.press("a", 120)
        self.capture(label)
        assert self.read("wScriptMode")[0], (label, "No native dialogue")
        if close:
            self.close_dialogue()
            self.p.tick(120, True)

    def begin_elemental(self, second=False):
        self.travel(25)
        stand, facing = ((2, 5), "down") if second else ((3, 6), "up")
        self.talk_at(stand, facing, "second_elemental_offer" if second else "first_elemental_offer", False)
        self.wait_for(lambda: self.phase == "battle" and self.read("wBattleMode")[0], buttons=True)
        self.p.tick(60, True)
        assert self.read("wEnemyMonSpecies") == [95]
        assert self.read("wPeonRecruitNodeObjectV029") == ([10] if second else [0])
        self.capture("second_elemental_battle" if second else "first_elemental_battle")

    def run_battle(self):
        for _ in range(30):
            if not self.read("wBattleMode")[0]:
                break
            self.wait_for(lambda: self.phase == "battle" or not self.read("wBattleMode")[0], True)
            if not self.read("wBattleMode")[0]:
                break
            for _ in range(6):
                x, y = self.read("wMenuCursorX")[0], self.read("wMenuCursorY")[0]
                if (x, y) == (2, 2):
                    break
                self.press("right" if x < 2 else "down", 30)
            menus = self.menus
            self.phase, self.context = "run_pending", None
            self.press("a", 30)
            self.wait_for(lambda: self.menus > menus and self.phase == "battle"
                          or not self.read("wBattleMode")[0], True)
        self.wait_for(lambda: not self.read("wBattleMode")[0] and not self.read("wScriptMode")[0], True)
        assert self.read("wBattleResult") == [2], "Expected native RUN"

    def fight_first(self):
        self.until_world(choose_bolt=True)
        assert self.read("wBattleResult") == [0] and self.quest()["found"]
        assert 153 in self.keys() and not self.quest()["reported"]
        self.capture("first_win_telluric_stone_received")

    def heal_at_inn(self):
        self.travel(14)
        self.navigate((17, 5), 23)
        self.talk_at((6, 5), "up", "ordinary_inn_recovery")
        assert self.word("wPartyMon1HP") == self.word("wPartyMon1MaxHP")
        # Native COLL_DOOR fires on a downward step; a lateral approach to
        # the same event cell does not activate it.
        portal = next(iter(self.native_warps("PeonOrcInn")))
        self.navigate((portal[0], portal[1] - 1))
        self.press("down", 40)
        self.p.tick(180, True)
        assert self.map() == 14, ("Inn downward door exit", portal, self.map(), self.position())

    def weaken_second(self):
        self.ready("battle")
        menus, move_menus = self.menus, self.move_menus
        for _ in range(6):
            x, y = self.read("wMenuCursorX")[0], self.read("wMenuCursorY")[0]
            if (x, y) == (1, 1):
                break
            self.press("left" if x > 1 else "up", 30)
        self.press("a", 60)
        self.wait_for(lambda: self.move_menus > move_menus)
        for _ in range(6):
            if self.read("wMenuCursorY") == [1]:
                break
            self.press("up", 30)
        self.phase, self.context = "move_pending", None
        self.press("a", 30)
        self.wait_for(lambda: self.menus > menus and self.phase == "battle"
                      or not self.read("wBattleMode")[0], True)
        if self.read("wBattleMode")[0]:
            assert 0 < self.word("wEnemyMonHP") < self.word("wEnemyMonMaxHP")
            self.capture("second_elemental_weakened_by_native_strike")

    def roll_enter(self, _):
        self.pending_roll = {
            "enemy_hp": self.word("wEnemyMonHP"),
            "enemy_max_hp": self.word("wEnemyMonMaxHP"),
            "status": self.read("wEnemyMonStatus")[0],
            "catch_rate": self.read("wEnemyMonCatchRate")[0],
            "control_quantity": self.item_quantity(5),
            "party_before": self.read("wPartyCount")[0],
        }

    def roll_success(self, _):
        assert self.pending_roll is not None
        self.pending_roll["random_byte"] = self.p.register_file.A

    def roll_finish(self, joined):
        row = self.pending_roll
        assert row is not None
        if not joined:
            row["random_byte"] = self.p.register_file.A
        maximum, hp = row["enemy_max_hp"], row["enemy_hp"]
        assert maximum < 85, "This bounded route expects the native low-HP division branch."
        expected = max(1, row["catch_rate"] * (3 * maximum - 2 * hp) // (3 * maximum))
        expected = min(255, expected + (10 if row["status"] & 0x27 else 0))
        row["threshold"] = self.read("wFinalCatchRate")[0]
        assert row["threshold"] == expected, ("Native capture formula", row, expected)
        assert (row["random_byte"] <= expected) == joined, ("Native RNG outcome", row, joined)
        row["joined"] = joined
        row["party_after"] = self.read("wPartyCount")[0]
        assert row["party_after"] == row["party_before"] + int(joined)
        assert self.item_quantity(5) == row["control_quantity"]
        self.rolls.append(row)
        self.pending_roll = None

    def capture_second(self):
        before_hero_name = self.read("wPartyMonNicknames", 11)
        original_control = self.item_quantity(5)
        naming_before = self.naming_entries
        attempts = 0
        self.weaken_second()
        while not self.quest()["done"] and attempts < 40:
            if not self.read("wBattleMode")[0]:
                self.wait_for(lambda: not self.read("wScriptMode")[0], True)
                result = self.read("wBattleResult")[0]
                assert result in (0, 1, 2)
                assert self.quest() == dict(accepted=True, found=True, reported=True, done=False)
                assert self.item_quantity(5) == original_control and self.read("wPartyCount") == [1]
                self.capture_retries.append({"battle_result": result, "quest_unchanged": True,
                                             "control_stone_preserved": True})
                self.capture("second_encounter_retry_" + str(len(self.capture_retries)))
                assert len(self.capture_retries) <= 4, "Bounded native encounter retry budget."
                self.heal_at_inn()
                self.begin_elemental(second=True)
                self.weaken_second()
            self.wait_for(lambda: self.phase == "battle" or not self.read("wBattleMode")[0], True)
            if not self.read("wBattleMode")[0]:
                continue
            if self.word("wBattleMonHP") <= self.word("wBattleMonMaxHP") // 2 and self.item_quantity(18):
                self.open_bag_item(18)
            else:
                self.open_bag_item(5)
                attempts += 1
                self.capture("control_stone_attempt_" + str(attempts))
            self.phase, self.context = "using_item", None
            self.press("a", 30)
        assert self.quest()["done"] and self.read("wPartyCount") == [2], ("Capture failed", self.rolls)
        self.wait_for(lambda: self.naming_entries > naming_before, buttons=True)
        self.p.tick(180, True)
        self.capture("native_elemental_rename_screen")
        # Native NAME_MON starts on A at column0,row0. Type T E R R A.
        for keys in (("down", "down", "right"),
                     ("up", "up", "right", "right", "right"),
                     ("down", "right", "right", "right", "right"),
                     (), ("up",) + ("left",) * 8):
            for key in keys:
                self.press(key, 35)
            self.press("a", 35)
        self.press("start", 40)
        self.press("a", 120)
        self.wait_for(lambda: not self.read("wScriptMode")[0] and not self.read("wBattleMode")[0], True)
        wanted = [text_encoding()[c] for c in "TERRA"] + [0x50]
        assert self.read("wPartyMonNicknames", 11) == before_hero_name
        assert self.read("wPartyMonNicknames", 22)[11:17] == wanted
        assert self.item_quantity(5) == original_control
        assert self.read("wPartyMon2Species") == [95]
        assert self.event("EVENT_PEON_RECRUIT_EARTH1_DONE_V029")
        self.capture("elemental_recruited_named_TERRA")

    def show_team(self, expect_terra=True):
        self.press("start")
        for _ in range(12):
            if self.read("wMenuCursorPosition") == [1]:
                break
            self.press("up", 30)
        self.press("a")
        self.capture("native_character_stats")
        old = self.team_entries
        self.press("right")
        self.wait_for(lambda: self.team_entries > old)
        self.p.tick(30, True)
        if expect_terra:
            assert self.visible_text("TERRA"), "TEAM did not display the actual companion nickname."
        self.verify_team_icons()
        self.capture("native_TEAM_TERRA" if expect_terra else "native_TEAM_class_icon_palette")
        self.press("b")
        self.press("b")
        self.press("b")
        self.p.tick(120, True)

    def verify_team_icons(self):
        families = []
        for row in (ROOT / "gfx/user_world_v0211/world_obj.pal").read_text().splitlines():
            if "RGB" not in row:
                continue
            values = [int(value) for value in re.findall(r"\d+", row)]
            words = [values[i] | values[i + 1] << 5 | values[i + 2] << 10
                     for i in range(0, 12, 3)]
            families.append(b"".join(word.to_bytes(2, "little") for word in words))
        paper = bytes(self.read("wBGPals2", 2))
        assert int.from_bytes(paper, "little") == 31 | 29 << 5 | 23 << 10
        for index in range(self.read("wPartyCount")[0]):
            species = self.read("wPartySpecies", 7)[index]
            if index == 0:
                source = ROOT / "gfx/approved_player_v0212" / CLASSES[self.class_index] / "overworld.bin"
                family = 1 if self.class_index == 2 else 2
            elif species == 95:
                source = ROOT / "gfx/earth_elemental_v0212/overworld.bin"
                family = 2
            elif species == 74:
                source = ROOT / "gfx/user_world_v0211/imp/overworld.bin"
                family = 7
            elif species == 68:
                source = ROOT / "gfx/user_world_v0211/orc_guard/overworld.bin"
                family = 2
            else:
                raise AssertionError(("Unexpected native TEAM icon role", species))
            wanted = source.read_bytes()[:64]
            start = 0x9400 + index * 64
            actual = bytes(self.p.memory[0, start:start + 64])
            assert actual == wanted, ("TEAM four-tile icon differs from canonical world source", index, source)
            palette = bytes(self.read("wBGPals2", 64)[(4 + index) * 8:(5 + index) * 8])
            expected_palette = paper + families[family][2:]
            assert palette == expected_palette, ("TEAM icon palette differs from world family/paper", index,
                                                  palette.hex(), expected_palette.hex())
            self.team_icon_checks.append({"row": index, "species": species,
                                          "source": str(source.relative_to(ROOT)),
                                          "four_native_VRAM_tiles_exact": True,
                                          "tile_sha256": hashlib.sha256(actual).hexdigest(),
                                          "world_palette_family": family,
                                          "native_palette_hex": palette.hex(),
                                          "opaque_world_colors_and_paper0_exact": True})

    def visible_text(self, value):
        tiles, attrs = self.read("wTilemap", 360), self.read("wAttrmap", 360)
        codes = self.read("wPeonBoldGlyphCodes", self.read("wPeonBoldGlyphCount")[0])
        glyph_base = 0x92 if self.read("wBattleMode")[0] else 0x69
        wanted = [text_encoding()[c] for c in value]
        # A battle HUD may publish directly to native VRAM while wTilemap
        # contains the open TEAM/menu surface. Inspect the displayed hardware
        # BG map too, using its real LCDC base and 32-tile stride.
        base = 0x9c00 if self.p.memory[0xff40] & 8 else 0x9800
        sx, sy = self.p.memory[0xff43] // 8, self.p.memory[0xff42] // 8
        actual_tiles = [self.p.memory[0, base + ((y + sy) % 32) * 32 + (x + sx) % 32]
                        for y in range(18) for x in range(20)]
        actual_attrs = [self.p.memory[1, base + ((y + sy) % 32) * 32 + (x + sx) % 32]
                        for y in range(18) for x in range(20)]
        for row_tiles, row_attrs in ((tiles, attrs), (actual_tiles, actual_attrs)):
            decoded = [codes[tile - glyph_base] if attr & 8 and glyph_base <= tile < glyph_base + len(codes)
                       else tile for tile, attr in zip(row_tiles, row_attrs)]
            for values in (row_tiles, decoded):
                if any(values[i:i + len(wanted)] == wanted for i in range(361 - len(wanted))):
                    return True
        return False

    def check_named_battle_HUD(self):
        self.travel(14)
        self.talk_at((10, 10), "up", "normal_gornek_quest_for_companion_HUD")
        assert self.event("EVENT_PEON_QUEST_ACCEPTED")
        self.navigate((18, 13))
        self.press("up", 30)
        self.press("a", 30)
        self.wait_for(lambda: self.phase == "battle" and self.read("wBattleMode")[0], True)
        for _ in range(6):
            x, y = self.read("wMenuCursorX")[0], self.read("wMenuCursorY")[0]
            if (x, y) == (2, 1):
                break
            self.press("right" if x < 2 else "up", 30)
        old = self.team_entries
        self.press("a", 30)
        self.wait_for(lambda: self.team_entries > old)
        for _ in range(6):
            cursor = self.read("wPeonTeamCursorV029")[0]
            if cursor == 1:
                break
            self.press("down" if cursor < 1 else "up", 30)
        self.phase, self.context = "switch_pending", None
        self.press("a", 30)
        self.wait_for(lambda: self.phase == "battle" and self.read("wCurBattleMon") == [1], True)
        self.p.tick(60, True)
        wanted = [text_encoding()[c] for c in "TERRA"] + [0x50]
        assert self.read("wBattleMonNickname", 6) == wanted
        self.events.append({"HUD_scroll": [self.p.memory[0xff43], self.p.memory[0xff42]],
                            "LCDC": self.p.memory[0xff40],
                            "tilemap_name_row": self.read("wTilemap", 360)[150:155],
                            "bold_codes": self.read("wPeonBoldGlyphCodes", self.read("wPeonBoldGlyphCount")[0])})
        assert self.visible_text("TERRA"), "Native battle HUD concealed the chosen nickname."
        self.capture("native_battle_HUD_TERRA")
        self.run_battle()
        assert not self.event("EVENT_PEON_QUEST_DONE"), "HUD check accidentally killed the ordinary boar."

    def save_continue(self):
        self.travel(14)
        self.navigate((12, 9))
        before = ExitSession.complete_record(self)
        saves = self.saves
        self.press("start")
        for _ in range(12):
            cursor = self.read("wMenuCursorPosition")[0]
            if cursor == 4:
                break
            self.press("up" if cursor > 4 else "down", 30)
        self.press("a")
        self.wait_for(lambda: self.saves == saves + 1 and self.presentation == "world", True)
        assert ExitSession.complete_record(self) == before
        self.capture("native_SAVE_named_party")
        self.p.stop(save=True)
        self.p = None
        battery = Path(str(self.rom) + ".ram")
        assert battery.stat().st_size == 32768
        self.open()
        self.p.tick(1800, True)
        self.press("start")
        self.press("a", 240)
        self.wait_for(lambda: self.map() == 14 and self.presentation == "world"
                      and not self.read("wScriptMode")[0], True)
        assert ExitSession.complete_record(self) == before, "Cold Continue changed party/name/quest/inventory."
        self.capture("cold_CONTINUE_TERRA_persisted")
        return {"native_save_calls": self.saves, "battery_bytes": battery.stat().st_size,
                "full_persistent_record_equal": True, "battery_sha256": sha(battery)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "pokecrystal.gbc")
    parser.add_argument("--sym", type=Path, default=ROOT / "pokecrystal.sym")
    parser.add_argument("--output", type=Path, default=OUT / "runtime")
    parser.add_argument("--classes", nargs="+", choices=CLASSES, default=list(CLASSES))
    parser.add_argument("--preliminary", action="store_true")
    parser.add_argument("--expected-rom-sha256")
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    args.output.mkdir(parents=True, exist_ok=True)
    digest = sha(args.rom)
    if args.expected_rom_sha256:
        assert digest == args.expected_rom_sha256
    report = {"rom_sha256": digest, "sym_sha256": sha(args.sym), "status": "RUNNING",
              "preliminary_logic_evidence": args.preliminary,
              "method": "Genuine fresh classes; native buttons, battles, capture RNG, naming and battery Continue.",
              "RAM_writes": False, "ROM_patches": False, "CPU_substitutions": False,
              "emulator_state_loads": False, "user_saves_opened": False, "classes": {},
              "limitations": ["Full-bag recovery reviewed in source; no artificial full inventory.",
                              "First-battle native loss not forced by fixtures.",
                              "First-elemental capture guard checked through native node0 and exact pact source; no preowned-stone inventory fixture."]}
    current = None
    try:
        with tempfile.TemporaryDirectory(prefix="peon-earth-quest-ordinary-") as directory:
            for name in args.classes:
                private_rom = Path(directory) / (name + ".gbc")
                shutil.copyfile(args.rom, private_rom)
                current = EarthSession(private_rom, symbols(args.sym), CLASSES.index(name), args.output)
                current.fresh_class()
                assert not any(current.quest().values())
                current.travel(15)
                current.talk_at((11, 11), "right", "mysterious_shaman_offer")
                if name != "shaman":
                    assert not any(current.quest().values())
                    assert 153 not in current.keys() and current.item_quantity(5) == 0
                    current.travel(25)
                    assert current.read("wObjectMasks", 16)[1] and current.read("wObjectMasks", 16)[10]
                    current.capture("other_class_elementals_masked")
                    current.show_team(expect_terra=False)
                    report["classes"][name] = {"refused_without_progress_or_items": True,
                                              "quest_elementals_hidden": True,
                                              "canonical_TEAM_icons": current.team_icon_checks}
                else:
                    assert current.quest() == dict(accepted=True, found=False, reported=False, done=False)
                    current.begin_elemental()
                    flags = current.quest()
                    current.run_battle()
                    assert current.quest() == flags and 153 not in current.keys()
                    current.capture("first_native_RUN_no_stone_or_credit")
                    current.begin_elemental()
                    current.fight_first()
                    current.travel(15)
                    current.talk_at((11, 11), "right", "return_telluric_stone_to_shaman")
                    assert current.quest() == dict(accepted=True, found=True, reported=True, done=False)
                    assert 153 not in current.keys() and current.item_quantity(5) == 1
                    quantity = current.item_quantity(5)
                    current.talk_at((11, 11), "right", "control_stone_reminder_no_duplicate")
                    assert current.item_quantity(5) == quantity
                    current.heal_at_inn()
                    current.begin_elemental(second=True)
                    current.capture_second()
                    current.show_team()
                    current.check_named_battle_HUD()
                    saved = current.save_continue()
                    report["classes"][name] = {"complete_chain": True, "first_RUN_no_credit": True,
                                              "native_capture_rolls": current.rolls,
                                              "native_second_encounter_retries": current.capture_retries,
                                              "control_stone_reusable": True, "renamed_to": "TERRA",
                                              "TEAM_and_native_battle_HUD_show_chosen_name": True,
                                              "canonical_TEAM_icons": current.team_icon_checks,
                                              "cold_continue": saved}
                current.p.stop(save=False)
                current.p = None
        report["status"] = "PASS"
        report["all_checks_passed"] = True
    except BaseException as error:
        report["status"] = "FAIL"
        report["error"] = repr(error)
        if current is not None and current.p is not None:
            current.capture("failure")
            report["failure_state"] = {"map": current.map(), "position": current.position(),
                                       "quest": current.quest(), "phase": current.phase,
                                       "rolls": current.rolls, "observer_events": current.events}
            current.p.stop(save=False)
            current.p = None
        raise
    finally:
        (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"status": report["status"], "rom_sha256": digest,
                          "classes": list(report["classes"])}, indent=2), flush=True)


if __name__ == "__main__":
    main()
