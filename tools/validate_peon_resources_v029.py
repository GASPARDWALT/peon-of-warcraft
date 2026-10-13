#!/usr/bin/env python3
"""Native mana/rage regression against an immutable v029 candidate.

Normal sections use real buttons, private batteries and read-only hooks.
Optional diagnostics explicitly replace disposable resource/status/PP fixtures
to cover refusal and prevented/immune execution; they are not normal play.
Pass reports include the exact frozen ROM hash and actual native display proof.
"""
import argparse
import hashlib
import json
import logging
import re
import shutil
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from validate_peon_class_routes import ClassSession
from validate_peon_deep_ui import text_encoding

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "references/generated/resources_v029/runtime"
CLASSES = ("shaman", "warrior", "warlock")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def symbols_from(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        fields = line.split()
        if len(fields) == 2 and ":" in fields[0]:
            result[fields[1]] = tuple(int(part, 16) for part in fields[0].split(":"))
    return result


def maximum(class_index, level):
    level = min(100, max(1, level))
    return 100 if class_index == 1 else min(999, (48 + 12 * level) if class_index == 0 else (60 + 15 * level))


class ResourceSession(ClassSession):
    def __init__(self, rom, sym, class_index, section="normal"):
        self.slug = CLASSES[class_index]
        self.payment_pending = None
        self.payments, self.refusals, self.hook_errors = [], [], []
        self.walking_pending, self.walking_ticks = None, []
        self.resource_ui, self.resource_context = "overworld", None
        self.battle_menus = 0
        self.supply_pending, self.supply_events = [], []
        self.trainer_entries = []
        self.resource_draw_pending, self.resource_draws, self.readout_checks = [], [], []
        super().__init__(rom, sym, class_index, section)

    def open(self):
        super().open()
        for label, callback in [("PeonSpendBattleResourceInternalV029.pay", self.payment),
                                ("PeonWriteCurrentResourceV029", self.write_resource),
                                ("PeonPrintNoResourceV029", self.refusal),
                                ("PeonResourceWalkingStepV029", self.walking_start),
                                ("PeonResourceWalkingStepV029.done", self.walking_done)]:
            def safe(_, callback=callback, label=label):
                try:
                    callback()
                except Exception as error:
                    self.hook_errors.append({"hook": label, "error": repr(error)})
            self.p.hook_register(*self.sym[label], safe, None)
        for label, phase in [("PeonBags", "bags_drawing"),
                             ("PeonInventory.draw", "inventory_drawing"),
                             ("PeonInventory.input", "inventory"),
                             ("PeonInventory.used_battle_item", "using_item"),
                             ("PeonTeamPickV029.input", "supply_target")]:
            self.p.hook_register(*self.sym[label], self.resource_phase, phase)
        self.p.hook_deregister(*self.sym["MoveSelectionScreen"])
        self.p.hook_register(*self.sym["MoveSelectionScreen"], self.resource_moves_menu, None)
        self.p.hook_register(*self.sym["LoadBattleMenu"], self.resource_battle_menu, None)
        self.p.hook_register(*self.sym["PeonInterfaceWait"], self.resource_bags_ready, None)
        self.p.hook_register(*self.sym["StaticMenuJoypad"], self.resource_static_ready, None)
        self.p.hook_register(*self.sym["VerticalMenu"], self.resource_merchant_ready, None)
        self.p.hook_register(*self.sym["ReturnFarCall"], self.supply_returned, None)
        self.p.hook_register(*self.sym["PeonPrintResourceForIndexV029.body"], self.resource_draw_entered, None)
        for label in ("PeonClassTrainer", "PeonShamanTrainer"):
            self.p.hook_register(*self.sym[label],
                                 lambda _: self.trainer_entries.append(
                                     [self.metadata(i) for i in range(self.read("wPartyCount")[0])]), None)
        for label in ("PeonTryUseMinorManaV029", "PeonTryUseMinorHealingV029",
                      "PeonTryDrinkWaterV029", "PeonTryEatMeatV029"):
            self.p.hook_register(*self.sym[label], self.supply_entered, label)

    def write(self, *args, **kwargs):
        raise AssertionError("Normal resources route permits no emulator RAM writes")

    def metadata(self, index=0):
        bank, address = self.sym["wPartyMon1Species"]
        record = bytes(self.p.memory[bank, address + index * 48:address + (index + 1) * 48])
        return {"species": record[0], "tag": record[28], "current": int.from_bytes(record[29:31], "big"),
                "level": record[31], "hp": int.from_bytes(record[34:36], "big"),
                "max_hp": int.from_bytes(record[36:38], "big"),
                "pp": list(record[23:27]), "record_hex": record.hex()}

    def walking_start(self):
        assert self.walking_pending is None
        self.walking_pending = {"frame": self.p.frame_count,
                                "step": self.read("wStepCount")[0],
                                "before": [self.metadata(i) for i in range(self.read("wPartyCount")[0])],
                                "battle": self.read("wBattleMode")[0]}

    def walking_done(self):
        pending = self.walking_pending
        assert pending is not None
        pending["after"] = [self.metadata(i) for i in range(self.read("wPartyCount")[0])]
        assert len(pending["before"]) == len(pending["after"])
        eligible = (not pending["battle"] and pending["step"] % 4 == 0
                    and self.event("EVENT_PEON_SHAMAN"))
        for index, (before, after) in enumerate(zip(pending["before"], pending["after"])):
            expected = before["current"]
            if eligible and index < 3 and before["tag"] == 0x80 and before["hp"]:
                actor_class = self.class_index if index == 0 else {95: 0, 74: 2, 68: 1}.get(before["species"])
                if actor_class is not None:
                    expected = (max(0, expected - 5) if actor_class == 1
                                else min(maximum(actor_class, before["level"]), expected + 2))
            assert after["current"] == expected, (pending, index, expected)
            # A recovery tick can only change the existing resource bytes.
            old, new = bytes.fromhex(before["record_hex"]), bytes.fromhex(after["record_hex"])
            assert all(old[i] == new[i] for i in range(48) if i not in (29, 30))
        self.walking_ticks.append(pending)
        self.walking_pending = None

    def resource_phase(self, phase):
        self.resource_ui, self.resource_context = phase, None

    def resource_battle_menu(self, _):
        self.resource_ui, self.resource_context = "battle_drawing", "battle"
        self.battle_menus += 1

    def resource_moves_menu(self, _):
        self.move_menus += 1
        self.resource_ui, self.resource_context = "moves", None

    def resource_bags_ready(self, _):
        if self.resource_ui == "bags_drawing":
            self.resource_ui = "bags"

    def resource_static_ready(self, _):
        if self.resource_context:
            self.resource_ui = self.resource_context

    def resource_merchant_ready(self, _):
        if self.map() == 14 and not self.read("wBattleMode")[0]:
            self.resource_context = "merchant"

    def supply_snapshot(self):
        return {"records": [self.metadata(i) for i in range(self.read("wPartyCount")[0])],
                "battle_hp": self.read("wBattleMonHP", 2),
                "battle_pp": self.read("wBattleMonPP", 4),
                "items": self.read("wItems", self.read("wNumItems")[0] * 2),
                "turns": self.read("wPlayerTurnsTaken") + self.read("wEnemyTurnsTaken")}

    def supply_entered(self, label):
        self.supply_pending.append({"helper": label, "before": self.supply_snapshot(),
                                    "entry_sp": self.p.register_file.SP})

    def supply_returned(self, _):
        for event in reversed(self.resource_draw_pending):
            if self.p.register_file.SP != event["entry_sp"] + 6:
                continue
            try:
                after = self.read("wTilemap", 360)
                start = event["destination"]
                assert all(event["tiles"][i] == after[i] for i in range(360)
                           if not start <= i < start + 9), "Resource readout damaged adjacent fields"
                assert event["attrs"] == self.read("wAttrmap", 360), "Resource readout changed palettes/VRAM banks"
                assert event["graphics"] == self.resource_protected_graphics(), "Resource print changed fonts/portraits"
                assert event["palettes"] == self.read("wBGPals2", 64), "Resource print changed native colors"
                self.resource_draws.append({"frame": event["frame"], "destination": start,
                    "only_nine_destination_cells_changed": True,
                    "neighbor_fields_attributes_fonts_portraits_and_palettes_preserved": True})
            except Exception as error:
                self.hook_errors.append({"hook": "resource_draw_returned", "error": repr(error)})
            self.resource_draw_pending.remove(event)
            break
        for event in reversed(self.supply_pending):
            if self.p.register_file.SP != event["entry_sp"] + 2:
                continue
            event["after"] = self.supply_snapshot()
            event["carry"] = bool(self.p.register_file.F & 0x10)
            self.supply_pending.remove(event)
            self.supply_events.append(event)
            break

    def resource_protected_graphics(self):
        # Printing the resource is text-only; neither regular font/portraits
        # nor the bank-one pet/portrait/bold-name graphics may be uploaded.
        return [hashlib.sha256(bytes(self.p.memory[bank, 0x8800:0x9800])).hexdigest()
                for bank in (0, 1)]

    def resource_draw_entered(self, _):
        destination = (self.p.register_file.D << 8 | self.p.register_file.E) - self.sym["wTilemap"][1]
        assert 0 <= destination <= 351
        self.resource_draw_pending.append({"entry_sp": self.p.register_file.SP,
            "destination": destination, "frame": self.p.frame_count,
            "tiles": self.read("wTilemap", 360), "attrs": self.read("wAttrmap", 360),
            "graphics": self.resource_protected_graphics(), "palettes": self.read("wBGPals2", 64)})

    def assert_native_regular_text(self, text, x, y, native_palette=0):
        """Check authored glyphs, settled VRAM cells and actual LCD pixels.

        This is not a screenshot reconstructed from the same wTilemap: the
        expected bits come from the frozen ROM's regular Font source packet.
        """
        chars = text_encoding()
        expected_codes = [chars[c] for c in text]
        start = y * 20 + x
        assert self.read("wTilemap", 360)[start:start + len(text)] == expected_codes, (text, x, y)
        assert self.read("wAttrmap", 360)[start:start + len(text)] == [7] * len(text), (text, "regular bank0 palette7")
        lcdc = self.p.memory[0xff40]
        assert lcdc & 0x80 and not lcdc & 0x10, "Expected signed-tile native text scene"
        raw = np.asarray(self.read("wBGPals2", 64), dtype=np.uint16).reshape(8, 4, 2)
        words = raw[:, :, 0] | raw[:, :, 1] << 8
        colors = np.stack((words & 31, words >> 5 & 31, words >> 10 & 31), axis=-1).astype(np.uint8)[native_palette]
        actual = np.asarray(self.p.screen.image.convert("RGB")) >> 3
        checked_pixels = 0
        for n, code in enumerate(expected_codes):
            source_label, offset = ("Font", (code - 128) * 8) if code >= 128 else ("TextboxSpaceGFX", 0)
            assert code >= 128 or code == 127, (text, code, "not a regular font glyph")
            source_bank, source_address = self.sym[source_label]
            glyph = bytes(self.p.memory[source_bank, source_address + offset:source_address + offset + 8])
            pattern = 0x9000 + (code if code < 128 else code - 256) * 16
            assert bytes(self.p.memory[0, pattern:pattern + 16]) == bytes(v for byte in glyph for v in (byte, byte)), (
                text, code, "native regular glyph differs from frozen source")
            yy, xx = (y * 8, (x + n) * 8)
            win_x, win_y = self.p.memory[0xff4b] - 7, self.p.memory[0xff4a]
            window = bool(lcdc & 0x20) and yy >= win_y and xx >= win_x and win_x <= 159
            bx = xx - win_x if window else (xx + self.p.memory[0xff43]) & 255
            by = yy - win_y if window else (yy + self.p.memory[0xff42]) & 255
            assert bx % 8 == by % 8 == 0, "Expected settled text-aligned native scroll"
            tilemap = (0x9c00 if lcdc & 0x40 else 0x9800) if window else (0x9c00 if lcdc & 0x08 else 0x9800)
            cell = tilemap + by // 8 * 32 + bx // 8
            # Battle CGB colors publish palette0 directly to native VRAM;
            # wAttrmap retains the menu builder's regular palette7 staging.
            # Keep both ownership checks explicit instead of treating this
            # legacy direct-publication path as a damaged font.
            assert self.p.memory[0, cell] == code and self.p.memory[1, cell] == native_palette, (
                text, "VRAM publication differs", {"cell": hex(cell), "expected": code,
                "tile": self.p.memory[0, cell], "attr": self.p.memory[1, cell],
                "lcdc": lcdc, "scroll": [self.p.memory[0xff43], self.p.memory[0xff42]],
                "window": [win_x, win_y], "window_used": window})
            bits = np.asarray([[3 if byte & (1 << (7 - bit)) else 0 for bit in range(8)] for byte in glyph])
            assert np.array_equal(actual[yy:yy + 8, xx:xx + 8], colors[bits]), (
                text, code, "actual PPU pixels differ from canonical regular glyph")
            checked_pixels += 64
        return {"text": text, "cell": [x, y], "tile_codes": expected_codes,
                "staging_palette": 7, "published_native_palette": native_palette,
                "canonical_rom_glyph_and_vram_attributes_exact": True,
                "actual_ppu_rgb555_pixels_checked": checked_pixels}

    def assert_move_resource_ui(self):
        index = self.read("wCurBattleMon")[0]
        record = self.metadata(index)
        actor_class = self.class_index if index == 0 else {95: 0, 74: 2, 68: 1}[record["species"]]
        unit = "RG" if actor_class == 1 else "MP"
        resource = self.assert_native_regular_text(
            f"{unit}{record['current']:>3}/{maximum(actor_class, record['level']):>3}", 1, 9)
        cost = self.read("wPeonResourceCostV029")[0]
        cost_text = f"{cost:>2}/{unit}" if cost else "--/--"
        price = self.assert_native_regular_text(cost_text, 5, 11)
        moves = self.read("wBattleMonMoves", 4)
        native_names = bytes(self.p.memory[self.sym["MoveNames"][0], self.sym["MoveNames"][1]:self.sym["MoveNames"][1] + 13 * 251]).split(b"\x50")
        rows = []
        for slot, move in enumerate(moves):
            if not move:
                name = "-"
            elif move == 1 and index == 0:
                name = ("MACE STRIKE", "MELEE STRIKE", "WAND STRIKE")[actor_class]
            elif move in (1, 10) and record["species"] == 74:
                name = "CLAW STRIKE"
            elif move == 1 and record["species"] in (95, 68):
                name = "STONE FIST" if record["species"] == 95 else "AXE STRIKE"
            else:
                packet = native_names[move - 1]
                english = {value: key for key, value in text_encoding().items() if len(key) == 1 and (key.isascii() or key == "é")}
                name = "".join(english[value] for value in packet)
            expected = [text_encoding()[c] for c in name]
            row = self.read("wTilemap", 360)[(13 + slot) * 20 + 6:(13 + slot) * 20 + 18]
            assert row == expected + [127] * (12 - len(expected)), (actor_class, index, slot, move, name, row)
            rows.append({"slot": slot, "move": move, "exact_text": name})
        result = {"frame": self.p.frame_count, "index": index, "species": record["species"],
                  "resource": resource, "cost": price, "four_actual_move_rows": rows}
        self.readout_checks.append(result)
        return result

    def wait_resource_ui(self, expected, buttons=False):
        for _ in range(240):
            if self.resource_ui == expected:
                self.p.tick(12, True)
                return
            if buttons:
                self.press("a", 30)
            else:
                self.p.tick(8, True)
        self.capture("unexpected_resource_ui")
        raise AssertionError((expected, self.resource_ui, self.phase, hex(self.p.register_file.PC)))

    def payment(self):
        assert self.payment_pending is None, "A prior payment was not written"
        index = self.read("wCurBattleMon")[0]
        self.payment_pending = {"index": index, "move": self.read("wCurPlayerMove")[0],
                                "cost": self.read("wPeonResourceCostV029")[0],
                                "before": self.metadata(index)["current"],
                                "frame": self.p.frame_count}

    def write_resource(self):
        if self.payment_pending is None:
            return  # Native rage gain, water, inn or potion writes.
        pending = self.payment_pending
        actual = self.p.register_file.B << 8 | self.p.register_file.C
        assert actual == pending["before"] - pending["cost"], (pending, actual)
        assert self.read("wPeonResourceIndexV029")[0] == pending["index"]
        pending["after"] = actual
        self.payments.append(pending)
        self.payment_pending = None

    def refusal(self):
        self.refusals.append({"frame": self.p.frame_count, "resources": self.metadata(),
                              "hp": self.read("wBattleMonHP", 2),
                              "player_turns": self.read("wPlayerTurnsTaken")[0],
                              "enemy_turns": self.read("wEnemyTurnsTaken")[0]})

    def capture(self, label):
        folder = OUT / self.section / self.slug
        folder.mkdir(parents=True, exist_ok=True)
        self.p.screen.image.save(folder / f"{label}.png")
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(folder / f"{label}_4x.png")

    def persistent_snapshot(self):
        return {"party_count": self.read("wPartyCount")[0],
                "records": [self.metadata(index)["record_hex"] for index in range(self.read("wPartyCount")[0])],
                "events": self.read("wEventFlags", 256), "name": self.read("wPlayerName", 11),
                "items": self.read("wItems", self.read("wNumItems")[0] * 2),
                "keys": self.read("wKeyItems", self.read("wNumKeyItems")[0]),
                "money": self.read("wMoney", 3), "map": self.map(), "position": self.position()}

    def fresh_resources_class(self):
        self.p.tick(240, True)
        self.press("start"); self.press("down"); self.press("a")
        chosen = False
        for _ in range(220):
            if self.map() == 14 and self.read("wScriptMode") == [0]:
                break
            if self.class_ready and not chosen:
                self.p.tick(60, True)
                for _ in range(self.class_index):
                    self.press("down", 40)
                self.press("a", 90)
                chosen = True
            if self.naming and not self.naming_done:
                self.p.tick(120, True)
                for index in range(5):
                    self.press("a", 35)
                    if index < 4:
                        self.press("right", 35)
                self.press("start", 40); self.press("a")
                self.naming_done = True
            self.press("a")
        assert chosen and self.naming_done and self.map() == 14 and self.read("wScriptMode") == [0]
        assert self.event("EVENT_PEON_SHAMAN")
        assert self.event("EVENT_PEON_WARRIOR") == (self.class_index == 1)
        assert self.event("EVENT_PEON_WARLOCK") == (self.class_index == 2)
        hero = self.metadata()
        assert hero["species"] == 66 and hero["tag"] == 0x80
        assert hero["current"] == (0 if self.class_index == 1 else maximum(self.class_index, hero["level"]))
        assert self.read("wPartyCount")[0] == (2 if self.class_index == 2 else 1)
        if self.class_index == 2:
            imp = self.metadata(1)
            assert imp["species"] == 74 and imp["tag"] == 0x80
            assert imp["current"] == maximum(2, imp["level"])
        self.capture("fresh_saved_resource")

    def select_move(self, slot):
        self.p.tick(60, True)
        for _ in range(6):
            actual = self.read("wMenuCursorY")[0] - 1
            if actual == slot:
                break
            self.press("up" if actual > slot else "down", 30)
        assert self.read("wMenuCursorY")[0] - 1 == slot
        self.assert_move_resource_ui()
        self.capture("selected_move_resource_info")
        self.press("a", 180)

    def buy_supply(self, choice, item):
        self.resource_ui, self.resource_context = "overworld", None
        self.navigate((14, 10)); self.press("up", 30)
        self.p.button("a", delay=1); self.p.tick(1, True)
        # Stop advancing dialogue as soon as VerticalMenu starts painting,
        # before its actual joypad loop. A held through that transition can
        # select the default stock item before the intended D-pad choice.
        for _ in range(600):
            if self.resource_ui == "merchant":
                break
            if self.resource_context == "merchant":
                self.p.tick(2, True)
            else:
                self.p.button("a", delay=1); self.p.tick(4, True)
        self.wait_resource_ui("merchant")
        assert self.read("wMenuCursorY") == [1]
        for _ in range(choice - 1):
            self.press("down", 30)
        if self.read("wMenuCursorY") != [choice]:
            self.capture("unexpected_merchant_cursor")
        assert self.read("wMenuCursorY") == [choice], (choice, self.read("wMenuCursorY"),
                                                       self.resource_ui, self.read("wScriptMode"))
        money, quantity = self.money(), self.item_quantity(item)
        self.press("a", 90); self.close_dialogue()
        assert self.money() == money - 25
        assert self.item_quantity(item) == quantity + 5
        self.resource_ui, self.resource_context = "overworld", None
        return {"item": item, "price_copper": 25, "bundle": 5}

    def buy_heroic_strike(self):
        self.enter_class_trainer(); self.select(0)
        before = self.money(); self.press("a"); assert self.phase == "confirm"
        self.press("a"); assert self.phase == "message"
        assert self.money() == before - 10
        assert self.read("wPartyMon1Moves", 3) == [1, 2, 5]
        self.dismiss(); self.exit_trainer()

    def open_inventory(self, item, battle=False):
        if battle:
            if self.resource_ui != "battle":
                self.press("b", 90)
            self.wait_resource_ui("battle")
            for _ in range(6):
                x, y = self.read("wMenuCursorX")[0], self.read("wMenuCursorY")[0]
                if (x, y) == (1, 2):
                    break
                self.press("left" if x > 1 else "down", 30)
            assert (self.read("wMenuCursorX")[0], self.read("wMenuCursorY")[0]) == (1, 2)
            self.press("a", 30)
        else:
            self.press("start")
            for _ in range(12):
                if self.read("wMenuCursorPosition") == [1]:
                    break
                self.press("up", 30)
            self.press("down", 30); self.press("a", 30)
        self.wait_resource_ui("bags")
        self.press("a", 30); self.wait_resource_ui("inventory")
        items = self.read("wItems", self.read("wNumItems")[0] * 2)[::2]
        assert item in items, (item, items)
        for _ in range(items.index(item)):
            self.press("right", 30); self.wait_resource_ui("inventory")
        assert self.read("wNamedObjectIndex") == [item]

    def use_supply(self, item, *, battle=False, target=0, cancel=False, expected_used=False):
        self.open_inventory(item, battle=battle)
        before = self.supply_snapshot()
        quantity, moves, menus = self.item_quantity(item), len(self.used_moves), self.battle_menus
        old_events = len(self.supply_events)
        self.press("a", 30)
        # In field mode the native TEAM panel is the actual target picker.
        # Combat supplies use the active actor and never open TEAM.
        if not battle:
            self.wait_resource_ui("supply_target")
            if cancel:
                self.press("b", 30)
            else:
                for _ in range(6):
                    cursor = self.read("wPeonTeamCursorV029")[0]
                    if cursor == target:
                        break
                    self.press("up" if cursor > target else "down", 30)
                assert self.read("wPeonTeamCursorV029") == [target]
                self.press("a", 30)
        if expected_used and battle:
            for _ in range(240):
                if self.battle_menus > menus and self.resource_ui == "battle":
                    break
                self.press("a", 30)
            assert self.battle_menus > menus and self.resource_ui == "battle"
            enemy_actions = self.used_moves[moves:]
            assert len(enemy_actions) == 1 and enemy_actions[0]["turn"] == 1, enemy_actions
        else:
            self.wait_resource_ui("inventory")
            assert len(self.used_moves) == moves and self.battle_menus == menus
        if battle and item == 46:
            # Inventory rejects drinking before entering the restoration
            # helper; no synthetic resource callback is expected here.
            assert len(self.supply_events) == old_events
            event = {"helper": "PeonInventory.drink combat guard", "before": before,
                     "after": self.supply_snapshot(), "carry": False}
        else:
            assert len(self.supply_events) == old_events + 1, (old_events, self.supply_events[-3:])
            event = self.supply_events[-1]
        assert event["carry"] == expected_used, event
        assert self.item_quantity(item) == quantity - int(expected_used)
        if not expected_used:
            assert event["before"] == event["after"], event
            assert self.supply_snapshot() == before, "Refusal/cancellation changed a record, turn or item"
        else:
            old, new = event["before"]["records"][target], event["after"]["records"][target]
            if item in (46, 63):
                actor_class = self.class_index if target == 0 else {95: 0, 74: 2, 68: 1}[old["species"]]
                assert new["current"] == min(maximum(actor_class, old["level"]), old["current"] + (60 if item == 46 else 40))
                assert new["hp"] == old["hp"] and new["pp"] == old["pp"]
            else:
                assert new["hp"] == min(old["max_hp"], old["hp"] + (20 if item == 18 else 10))
                assert new["current"] == old["current"] and new["pp"] == old["pp"]
        self.capture(f"supply_{item}_{'battle' if battle else 'field'}_{'used' if expected_used else 'refused'}")
        if not (expected_used and battle):
            self.press("b", 120)
            if battle:
                self.wait_resource_ui("battle")
            else:
                self.press("b", 180)
                self.resource_ui = "overworld"
        return {"item": item, "battle": battle, "target": target, "cancelled": cancel,
                "used": expected_used, "event": event,
                "quantity_before": quantity, "quantity_after": self.item_quantity(item),
                "enemy_actions": len(self.used_moves) - moves}

    def begin_selected_attack(self, slot):
        if self.resource_ui == "battle":
            for _ in range(6):
                x, y = self.read("wMenuCursorX")[0], self.read("wMenuCursorY")[0]
                if (x, y) == (1, 1):
                    break
                self.press("left" if x > 1 else "up", 30)
            before = self.move_menus
            self.press("a", 60)
            assert self.move_menus > before
        self.select_move(slot)

    def ordinary_warrior_shortage(self):
        assert self.class_index == 1 and self.metadata()["current"] == 0
        before, old_refusals, old_menus = self.supply_snapshot(), len(self.refusals), self.move_menus
        self.select_move(2)
        for _ in range(20):
            if self.move_menus > old_menus:
                break
            self.press("a", 90)
        self.p.tick(60, True)
        assert len(self.refusals) > old_refusals and self.move_menus > old_menus
        assert self.supply_snapshot() == before
        self.capture("ordinary_zero_rage_strike_refused")
        return {"ordinary_buttons_only": True, "zero_rage": True,
                "rejected_move": 5, "no_turn_item_hp_or_pp_spent": True}

    def enter_boar(self):
        self.navigate((10, 10)); self.press("up", 30); self.press("a"); self.close_dialogue()
        self.navigate((18, 13)); self.press("up", 30)
        before = self.move_menus
        self.press("a")
        for _ in range(40):
            if self.move_menus > before:
                break
            self.press("a")
        assert self.read("wBattleMode")[0] and self.move_menus > before
        self.p.tick(60, True)
        self.assert_move_resource_ui()
        return self.move_menus

    def finish_resource_battle(self, flag="EVENT_PEON_QUEST_DONE"):
        handled = self.move_menus - 1
        for _ in range(240):
            if self.resource_ui == "battle" or self.move_menus > handled:
                handled = self.move_menus
                # Caster starting slot two is paid; Warrior uses the basic
                # until enough rage exists for its paid rank-one strike.
                current = self.metadata()["current"]
                required = (15, 15, 25)[self.class_index]
                wanted = (2 if self.class_index == 1 else 1) if current >= required else 0
                self.begin_selected_attack(wanted)
                handled = self.move_menus
            else:
                self.press("a", 90)
            if self.read("wBattleMode") == [0] and self.read("wScriptMode") == [0]:
                break
        assert self.read("wBattleMode") == [0] and self.event(flag)
        assert self.read("wBattleResult") == [0]
        assert not self.hook_errors and self.payment_pending is None, self.hook_errors
        assert self.payments, "No resource-controlled action was executed"
        if self.class_index != 1:
            cost = (15, 0, 25)[self.class_index]
            assert any(payment["cost"] == cost for payment in self.payments)
        else:
            assert any(payment["cost"] == 0 for payment in self.payments)
            assert 0 < self.metadata()["current"] <= 100
        self.capture("ordinary_battle_resource_result")


def normal_route(rom, sym, index):
    s = ResourceSession(rom, sym, index)
    try:
        s.fresh_resources_class()
        initial = s.persistent_snapshot()
        if index == 1:
            s.buy_heroic_strike()
        purchases = [s.buy_supply(1, 46)]
        if index != 1:
            purchases.append(s.buy_supply(3, 149))
        supplies = [s.use_supply(46, expected_used=False),
                    s.use_supply(18, cancel=True, expected_used=False)]
        if index != 1:
            supplies.append(s.use_supply(149, expected_used=False))
        if index != 1:
            supplies.append(s.use_supply(63, expected_used=False))
        if index == 2:
            supplies.append(s.use_supply(46, target=1, expected_used=False))
        s.enter_boar()
        rage_refusal = s.ordinary_warrior_shortage() if index == 1 else None
        before_pp = s.metadata()["pp"]
        s.begin_selected_attack(0 if index == 1 else 1)
        # After the first ordinary cast/hit, the real enemy reply injures
        # the apprentice. Supplies are exercised through the actual Bags UI.
        s.wait_resource_ui("battle", buttons=True)
        supplies.append(s.use_supply(46, battle=True, expected_used=False))
        if index != 1:
            supplies.append(s.use_supply(149, battle=True, expected_used=False))
        hero = s.metadata()
        assert 0 < hero["hp"] < hero["max_hp"], "The ordinary enemy reply did not injure the hero"
        supplies.append(s.use_supply(18, battle=True, expected_used=True))
        if index != 1:
            supplies.append(s.use_supply(63, battle=True, expected_used=True))
        s.finish_resource_battle()
        if index == 1 and not any(p["move"] == 5 and p["cost"] == 15 for p in s.payments):
            # The level-one boar can fall before enough rage accumulates.
            # Fight the real adjacent scorpid, rather than injecting rage
            # or changing the first enemy's HP to force a paid strike.
            before_menus = s.move_menus
            s.navigate((18, 14))
            for _ in range(80):
                if s.read("wBattleMode")[0] and s.move_menus > before_menus:
                    break
                s.press("a", 60)
            assert s.read("wBattleMode")[0] and s.move_menus > before_menus
            s.finish_resource_battle("EVENT_PEON_SCORPID_DEFEATED")
        if index == 1:
            assert any(p["move"] == 5 and p["cost"] == 15 for p in s.payments), s.payments
        assert s.metadata()["pp"] == before_pp, "Managed battle changed the old per-move PP bytes"
        depleted = s.metadata()
        # Initial copper is finite: Warrior buys its ten-copper lesson and
        # water first. The first quest's actual reward funds its meat bundle.
        s.talk_plain((10, 10), "up")
        assert s.event("EVENT_PEON_CUTTING_TURNED_IN")
        if index == 1:
            purchases.append(s.buy_supply(3, 149))
        # The first post-turn-in master visit legitimately grants the one
        # new recruitment relic. Subsequent visits must duplicate nothing.
        s.enter_class_trainer(); s.exit_trainer()
        before_trainer = s.persistent_snapshot()
        for _ in range(2):
            s.enter_class_trainer()
            entered_records = s.trainer_entries[-1]
            s.p.tick(600, True)
            assert [s.metadata(i) for i in range(s.read("wPartyCount")[0])] == entered_records
            s.exit_trainer()
            assert [s.metadata(i) for i in range(s.read("wPartyCount")[0])] == entered_records
        # Traversing the world legitimately performs recovery ticks. Each
        # exact tick is checked by the read-only walking hooks above.
        assert s.persistent_snapshot()["items"] == before_trainer["items"]
        cold = s.cold_save()
        assert not s.hook_errors
        after_cold = s.metadata()
        actor_max = maximum(index, after_cold["level"])
        supplies.append(s.use_supply(46, expected_used=index != 1 and after_cold["current"] < actor_max))
        supplies.append(s.use_supply(46, expected_used=False))
        hero = s.metadata()
        supplies.append(s.use_supply(149, expected_used=0 < hero["hp"] < hero["max_hp"]))
        s.rest()
        for actor in range(s.read("wPartyCount")[0]):
            record = s.metadata(actor)
            actor_class = index if not actor else {95: 0, 74: 2, 68: 1}[record["species"]]
            assert record["hp"] == record["max_hp"]
            assert record["current"] == (0 if actor_class == 1 else maximum(actor_class, record["level"]))
        assert not s.hook_errors and s.walking_pending is None and not s.supply_pending
        return {"normal_buttons_only": True, "ram_writes": False, "state_loads": False,
                "initial": initial, "after_battle": depleted, "payments": s.payments,
                "supplies": supplies, "merchant_purchases": purchases,
                "ordinary_zero_rage_refusal": rage_refusal,
                "managed_legacy_pp_unchanged_through_battle": True,
                "walking_ticks": s.walking_ticks,
                "resource_text_only_draws": s.resource_draws,
                "actual_resource_cost_pixels_and_four_move_rows": s.readout_checks,
                "living_resource_ticks_only_each_fourth_completed_walk": True,
                "inn_restores_party_health_mana_and_clears_rage": True,
                "no_refill_on_repeated_master_visits": True,
                "cold_battery": cold, "tagged_current_preserved_on_Continue": True,
                "starting_imp_is_real_second_record": index == 2}
    finally:
        s.p.stop(save=False)


def diagnostic_zero_mana_refusal(rom, sym):
    s = ResourceSession(rom, sym, 0, section="diagnostics")
    try:
        s.fresh_resources_class(); s.enter_boar()
        # Explicit isolated fixture: a tagged living Shaman with zero mana.
        bank, address = sym["wPartyMon1CaughtData"]
        s.p.memory[bank, address:address + 2] = [0, 0]
        before = {"hp": s.read("wBattleMonHP", 2), "enemy_hp": s.read("wEnemyMonHP", 2),
                  "turns": s.read("wPlayerTurnsTaken") + s.read("wEnemyTurnsTaken"),
                  "pp": s.read("wPartyMon1PP", 4), "items": s.read("wItems", s.read("wNumItems")[0] * 2)}
        count = len(s.refusals)
        s.select_move(1)
        for _ in range(12):
            if len(s.refusals) > count:
                break
            s.p.tick(20, True)
        assert len(s.refusals) > count
        assert s.metadata()["current"] == 0
        after = {"hp": s.read("wBattleMonHP", 2), "enemy_hp": s.read("wEnemyMonHP", 2),
                 "turns": s.read("wPlayerTurnsTaken") + s.read("wEnemyTurnsTaken"),
                 "pp": s.read("wPartyMon1PP", 4), "items": s.read("wItems", s.read("wNumItems")[0] * 2)}
        assert before == after, "Rejected spell spent a turn, HP, item or legacy charge"
        s.capture("zero_mana_refusal_no_turn")
        return {"diagnostic_resource_fixture": True, "only_two_current_resource_bytes_written": True,
                "normal_ui_spell_selection": True, "before": before, "after": after,
                "zero_current_preserved": True, "no_paid_cast_executed": not s.payments}
    finally:
        s.p.stop(save=False)


def diagnostic_zero_pp_status_and_immunity(rom, sym):
    """Private, explicit metadata/PP/status/type fixtures; real UI/CPU flow.

    These do not replace the ordinary routes. No CPU jump substitution,
    emulator state load, user battery or published source ROM is touched.
    """
    s = ResourceSession(rom, sym, 0, section="diagnostics")
    writes = []

    def fixture(label, data):
        bank, address = sym[label]
        before = list(s.p.memory[bank, address:address + len(data)])
        s.p.memory[bank, address:address + len(data)] = data
        writes.append({"label": label, "before": before, "after": list(data)})

    def advance_to_battle():
        for _ in range(120):
            if s.resource_ui == "battle":
                s.p.tick(30, True)
                return
            s.press("a", 30)
        raise AssertionError(("battle UI failed to return", s.resource_ui))

    try:
        s.fresh_resources_class(); s.enter_boar()
        # PP stays genuinely zero; shared mana controls availability.
        fixture("wPartyMon1PP", [0, 0, 0, 0])
        fixture("wBattleMonPP", [0, 0, 0, 0])
        fixture("wPartyMon1CaughtData", [0, 45])
        # Two turns asleep deterministically prevents the selected cast.
        fixture("wPartyMon1Status", [2])
        fixture("wBattleMonStatus", [2])
        before_payments, current = len(s.payments), s.metadata()["current"]
        s.begin_selected_attack(1); advance_to_battle()
        assert len(s.payments) == before_payments
        assert s.metadata()["current"] == current
        assert s.metadata()["pp"] == [0, 0, 0, 0]
        asleep = {"prevented_cast_not_charged": True, "mana": current, "zero_legacy_pp_preserved": True}
        s.capture("diagnostic_sleep_prevents_mana_spend")
        fixture("wPartyMon1Status", [0]); fixture("wBattleMonStatus", [0])
        # Ground immunity guarantees a resisted lightning action. Native
        # resource debit occurs once even though this cast deals zero HP.
        fixture("wEnemyMonType1", [4]); fixture("wEnemyMonType2", [4])
        enemy_hp = s.read("wEnemyMonHP", 2)
        current = s.metadata()["current"]; count = len(s.payments)
        s.begin_selected_attack(1); advance_to_battle()
        assert len(s.payments) == count + 1
        assert s.payments[-1]["cost"] == 15
        assert s.metadata()["current"] == current - 15
        assert s.read("wEnemyMonHP", 2) == enemy_hp
        assert s.metadata()["pp"] == [0, 0, 0, 0]
        immunity = {"executed_immune_cast_charged_once": True, "cost": 15,
                    "enemy_hp_unchanged": True, "zero_legacy_pp_preserved": True}
        s.capture("diagnostic_immune_cast_spends_real_mana")
        # At zero mana and zero legacy PP the native weapon still executes;
        # no hidden charge refill is allowed.
        fixture("wPartyMon1CaughtData", [0, 0])
        count = len(s.payments)
        s.begin_selected_attack(0)
        for _ in range(120):
            if len(s.payments) > count:
                break
            s.press("a", 30)
        assert len(s.payments) == count + 1 and s.payments[-1]["cost"] == 0
        assert s.metadata()["current"] == 0 and s.metadata()["pp"] == [0, 0, 0, 0]
        assert not s.hook_errors and s.payment_pending is None
        s.capture("diagnostic_free_mace_zero_mana_zero_pp")
        return {"private_diagnostic": True, "fixture_writes": writes,
                "sleep": asleep, "immunity": immunity,
                "free_weapon_with_zero_pool_and_zero_pp": True,
                "actual_button_selection_and_native_action_execution": True}
    finally:
        s.p.stop(save=False)


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "pokecrystal.gbc")
    parser.add_argument("--symbols", type=Path, default=ROOT / "pokecrystal.sym")
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--diagnostics", action="store_true")
    args = parser.parse_args()
    assert sha(args.rom) == args.expected_sha256
    sym = symbols_from(args.symbols)
    for label in ("PeonSpendBattleResourceInternalV029.pay", "PeonWriteCurrentResourceV029",
                  "PeonDrawCharacterResourceV029", "PeonDrawBattleResourceV029",
                  "PeonResourceTagIsMetadataV029", "PeonCheckResourceMovesUsableV029",
                  "PeonResourceWalkingStepV029.done", "wPeonResourceClassV029"):
        assert label in sym, f"Future v029 helper is not integrated: {label}"
    assert sym["wPeonResourceIndexV029"] == (0, 0xcffb)
    assert sym["wPeonResourceClassV029"] == (0, 0xcfff)
    OUT = args.output
    OUT.mkdir(parents=True, exist_ok=True)
    logging.disable(logging.CRITICAL)
    report = {"rom_sha256": args.expected_sha256, "symbols_sha256": sha(args.symbols),
              "normal": {}, "diagnostics": {}}
    report["passed"] = False
    (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    try:
        with tempfile.TemporaryDirectory(prefix="peon-v029-resources-") as directory:
            for index, name in enumerate(CLASSES):
                rom = Path(directory) / f"{name}.gbc"
                shutil.copyfile(args.rom, rom)
                report["normal"][name] = normal_route(rom, sym, index)
            if args.diagnostics:
                rom = Path(directory) / "zero_mana.gbc"
                shutil.copyfile(args.rom, rom)
                report["diagnostics"]["zero_mana_refusal"] = diagnostic_zero_mana_refusal(rom, sym)
                rom = Path(directory) / "zero_pp_status.gbc"
                shutil.copyfile(args.rom, rom)
                report["diagnostics"]["zero_pp_status_and_immunity"] = diagnostic_zero_pp_status_and_immunity(rom, sym)
    except Exception as error:
        report["error"] = repr(error)
        (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
        raise
    assert sha(args.rom) == args.expected_sha256
    report["passed"] = True
    (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "rom_sha256": args.expected_sha256}))


if __name__ == "__main__":
    main()
