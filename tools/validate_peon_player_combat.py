#!/usr/bin/env python3
"""Record actual rear combat poses and protect native battle graphics.

The first route buys a potion and uses the intro kit, Totem, potion, Mace and
Lightning Bolt through real controls. Separate labelled diagnostic encounters
rewind the pre-battle state and change only species, HP, moves/PP and the
native battle-scenes option. No animation ID, CPU call or graphics bytes are
substituted. Outputs belong exclusively to v0.2.3.
"""
from pathlib import Path
import hashlib
import io
import json
import logging
import shutil
import tempfile

import numpy as np
from PIL import Image

from validate_peon_spell_animations import AnimationSession, decode_tile, load_symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "references/generated/durotar_v023/player_combat"
POSES = ("idle", "brace", "swing")
TOTEM, POTION = 0x94, 0x12


def palette_rgb555():
    encoded = (ROOT / "gfx/peon_player_battle/back_frames.gbcpal").read_bytes()
    return np.array([[word & 31, word >> 5 & 31, word >> 10 & 31]
                     for word in (int.from_bytes(encoded[i:i + 2], "little")
                                  for i in range(0, 8, 2))], dtype="uint8")


def decode_back(binary):
    result = np.zeros((48, 48), dtype="uint8")
    for tx in range(6):
        for ty in range(6):
            offset = (tx * 6 + ty) * 16
            result[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8] = decode_tile(binary[offset:offset + 16])
    return result


class PlayerSession(AnimationSession):
    def __init__(self, rom, sym):
        packed = (ROOT / "gfx/peon_player_battle/back_frames.2bpp").read_bytes()
        assert len(packed) == 1728
        self.pose_data = [packed[i * 576:(i + 1) * 576] for i in range(3)]
        self.pose_pixels = [decode_back(frame) for frame in self.pose_data]
        self.pose_palette = palette_rgb555()
        self.recording = None
        self.pose_returns = []
        self.diagnostic_species = None
        self.merchant_context = False
        self.merchant_ready = 0
        self.item_ready = 0
        self.frame_number = 0
        super().__init__(rom, sym)

    def open(self):
        super().open()
        self.p.hook_register(*self.sym["PeonAnimatePlayerAttack"], self.pose_helper, "attack")
        self.p.hook_register(*self.sym["PeonRestorePlayerIdlePose"], self.pose_helper, "restore")
        self.p.hook_register(*self.sym["VerticalMenu"], self.merchant_enter, None)
        self.p.hook_register(*self.sym["PeonInventory.input"], self.inventory_ready, None)
        self.p.hook_register(*self.sym["PeonInventory.used_battle_item"], self.inventory_used, None)

    def menu(self, _):
        # Retain the inherited observations without its HP240 fixture. The
        # normal route must use the real starting actor and ordinary enemy.
        self.menus += 1
        self.ready = True

    def fixture_enemy(self, _):
        if self.diagnostic_species is not None:
            self.write("wTempWildMonSpecies", [self.diagnostic_species])
        self.encounter_loads += 1

    def merchant_enter(self, _):
        if self.map() == 14 and not self.read("wBattleMode")[0]:
            self.merchant_context = True

    def input_ready(self, _):
        super().input_ready(_)
        if self.merchant_context and not self.read("wBattleMode")[0]:
            self.merchant_ready += 1

    def inventory_ready(self, _):
        self.ui_state = "inventory"
        self.item_ready += 1

    def inventory_used(self, _):
        self.ui_state = "using_item"

    def protected(self):
        # The player back occupies bank0 $9310..$954f. The newly placed
        # Totem is a legitimate independent upload into bank1 $8860..$887f.
        return {"enemy_front_bank0": bytes(self.p.memory[0, 0x9000:0x9310]),
                "bank0_after_player": bytes(self.p.memory[0, 0x9550:0x9800]),
                "font_bank0": bytes(self.p.memory[0, 0x8800:0x9000]),
                "rank_bank1": bytes(self.p.memory[1, 0x8800:0x8860]),
                "enemy_and_other_bank1": bytes(self.p.memory[1, 0x8880:0x9800])}

    def check_protected_after_turn(self, baseline, label):
        current = self.protected()
        changed = {key: {"count": sum(a != b for a, b in zip(current[key], value)),
                         "first_offsets": [i for i, (a, b) in enumerate(zip(current[key], value)) if a != b][:20]}
                   for key, value in baseline.items() if current[key] != value}
        # Enemy poses initialize tiles98+ on their first actual attack. This
        # is a legitimate cache fill, not rear-pose corruption; prove the new
        # bytes exactly match the native packed enemy animation and protect
        # every byte outside that allocation. Helper-entry guards remain exact.
        if "enemy_and_other_bank1" in changed:
            species = self.read("wEnemyMonSpecies")[0]
            role = {19: "rattata", 67: "machoke"}[species]
            packed = (ROOT / f"gfx/pokemon/{role}/front.animated.2bpp").read_bytes()
            tail = packed[98 * 16:]
            offset = 0x9620 - 0x8880
            before = baseline["enemy_and_other_bank1"]
            after = current["enemy_and_other_bank1"]
            assert after[:offset] == before[:offset] and after[offset + len(tail):] == before[offset + len(tail):], (label, "Changed outside enemy tail allocation")
            assert after[offset:offset + len(tail)] == tail, (label, "Enemy pose tail does not match native art")
            del changed["enemy_and_other_bank1"]
        assert not changed, (label, "Changed enemy/font/rank graphics", changed)

    def pose_helper(self, kind):
        if self.recording is None:
            return
        record = self.recording
        if kind == "attack" and not self.read("hBattleTurn")[0]:
            record["attack_helper_entries"] += 1
            record["started"] = True
            record["actual_moves"].add(self.read("wCurPlayerMove")[0])
        if kind == "restore":
            record["restore_helper_entries"] += 1
        self.pose_returns.append({"kind": kind, "entry_sp": self.p.register_file.SP,
                                  "protected": self.protected(),
                                  "totem_tiles": bytes(self.p.memory[1, 0x8860:0x8880]),
                                  "vbk": self.p.memory[0xff4f], "wbk": self.p.memory[0xff70]})

    def returned(self, _):
        super().returned(_)
        for entry in reversed(self.pose_returns):
            if self.p.register_file.SP == entry["entry_sp"] + 2:
                assert self.protected() == entry["protected"], ("Player pose helper corrupted other graphics", entry["kind"])
                assert bytes(self.p.memory[1, 0x8860:0x8880]) == entry["totem_tiles"], "Rear pose helper changed Totem tiles"
                assert self.p.memory[0xff4f] == entry["vbk"] and self.p.memory[0xff70] == entry["wbk"], "Rear pose helper changed VRAM/WRAM bank"
                self.pose_returns.remove(entry)
                if self.recording:
                    self.recording["protected_helper_returns"] += 1
                break

    def tick(self, frames):
        for _ in range(frames):
            self.p.tick(1, True)
            self.frame_number += 1
            if self.recording is not None:
                self.observe_player()

    def observe_player(self):
        record = self.recording
        if not record["started"]:
            return
        if len(record["frames"]) < 1600:
            record["frames"].append(self.p.screen.image.copy())
        actual_binary = bytes(self.p.memory[0, 0x9310:0x9550])
        for index, expected_binary in enumerate(self.pose_data):
            if actual_binary != expected_binary:
                continue
            name = POSES[index]
            record["native_poses"].add(name)
            if not record["native_sequence"] or record["native_sequence"][-1] != name:
                record["native_sequence"].append(name)
            expected = self.pose_palette[self.pose_pixels[index]]
            actual = np.array(self.p.screen.image.convert("RGB").crop((16, 48, 64, 96))) >> 3
            if np.array_equal(actual, expected):
                record["pixel_poses"].add(name)
                record["matched_frames"][name] += 1
                if name not in record["screens"]:
                    record["screens"][name] = self.p.screen.image.copy()
            break

    def capture(self, label):
        self.p.screen.image.save(OUT / f"{label}_in_rom.png")
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / f"{label}_in_rom_4x.png")

    def verify_idle(self):
        self.release_all(); self.tick(60)
        assert bytes(self.p.memory[0, 0x9310:0x9550]) == self.pose_data[0], "Idle rear tiles not restored"
        assert self.read("wPeonPlayerPoseActive") == [0], "Rear-pose transient flag stayed active"
        expected = self.pose_palette[self.pose_pixels[0]]
        actual = np.array(self.p.screen.image.convert("RGB").crop((16, 48, 64, 96))) >> 3
        assert np.array_equal(actual, expected), "Idle rear palette/pixels not restored"
        tilemap, attrs = self.read("wTilemap", 360), self.read("wAttrmap", 360)
        assert [tilemap[y * 20 + x] for x in range(2, 8) for y in range(6, 12)] == list(range(0x31, 0x55))
        assert [attrs[y * 20 + x] for x in range(2, 8) for y in range(6, 12)] == [0] * 36
        return {"idle_36_tiles_restored": True, "idle_actual_rgb555_and_palette": True,
                "back_tilemap_bank0_intact": True}

    def buy_potion(self):
        self.navigate((14, 10)); self.press("up", 30); self.press("a", 60)
        for _ in range(80):
            if self.merchant_ready:
                break
            self.press("a", 40)
        assert self.merchant_ready and self.read("wMenuCursorY") == [1]
        self.press("down", 30)
        assert self.read("wMenuCursorY") == [2]
        self.press("a", 90); self.close_dialogue()
        self.merchant_context = False
        assert self.item_quantity(POTION) == 1 and self.money() == 25

    def use_bag_item(self, item):
        self.wait_main()
        protected = self.protected()
        self.press("up", 30); self.press("left", 30); self.press("down", 30)
        entered = self.bags_entered
        self.p.button("a", delay=4)
        for _ in range(240):
            self.tick(1)
            if self.bags_entered > entered:
                break
        assert self.bags_entered == entered + 1
        self.release_all(); self.tick(120)
        self.p.button("a", delay=4)
        for _ in range(240):
            self.tick(1)
            if self.ui_state == "inventory":
                break
        assert self.ui_state == "inventory"
        self.release_all(); self.tick(30)
        items = self.read("wItems", self.read("wNumItems")[0] * 2)[::2]
        assert item in items
        for _ in range(len(items) + 1):
            if self.read("wNamedObjectIndex") == [item]:
                break
            self.press("right", 30)
        assert self.read("wNamedObjectIndex") == [item]
        before_quantity = self.item_quantity(item)
        before_hp = self.word("wBattleMonHP")
        menus = self.main_ready
        self.p.button("a", delay=4)
        self.ui_state = "submitted_item"
        self.wait_main(after=menus)
        self.check_protected_after_turn(protected, "Bag item")
        if item == TOTEM:
            assert self.read("wPeonEarthTotemActive") == [1] and self.item_quantity(item) == before_quantity
            assert bytes(self.p.memory[1, 0x8860:0x8880]) == (ROOT / "gfx/pack/peon_earth_totem_battle.2bpp").read_bytes()
        else:
            # This consumes an enemy turn. The counterattack may remove all
            # HP just restored; final HP need not exceed pre-potion HP.
            assert self.item_quantity(item) == before_quantity - 1, (item, before_quantity, self.item_quantity(item))
        self.capture("normal_totem_return" if item == TOTEM else "normal_potion_return")
        return {"item_id": item, "actual_button_use": True, "other_battle_graphics_preserved": True,
                "hp_before_item": before_hp, "hp_after_enemy_turn": self.word("wBattleMonHP"),
                **self.verify_idle()}

    def cast(self, name, move, slot=0, scenes=True):
        self.wait_main()
        self.press("up", 30); self.press("left", 30)
        protected = self.protected()
        record = {"name": name, "started": False, "attack_helper_entries": 0,
                  "restore_helper_entries": 0, "protected_helper_returns": 0,
                  "native_poses": set(), "pixel_poses": set(), "native_sequence": [],
                  "actual_moves": set(),
                  "matched_frames": {pose: 0 for pose in POSES}, "screens": {}, "frames": []}
        self.recording = record
        menus = self.main_ready
        self.p.button("a", delay=4)
        for _ in range(240):
            self.tick(1)
            if self.ui_state == "moves":
                break
        assert self.ui_state == "moves", (name, "Move selector not ready")
        self.release_all(); self.tick(60)
        for _ in range(4):
            cursor = self.read("wMenuCursorY")[0] - 1
            if cursor == slot:
                break
            self.press("up" if cursor > slot else "down", 30)
        assert self.read("wMenuCursorY") == [slot + 1]
        assert self.read("wBattleMonMoves", 4)[slot] == move
        self.p.button("a", delay=4); self.ui_state = "submitted"
        # The final normal Lightning may defeat the ordinary boar. Diagnostics
        # have HP240 and must return to the actual battle main menu.
        for frame in range(24000):
            if self.ui_state == "main" and self.main_ready > menus:
                self.release_all(); self.tick(60)
                if self.ui_state == "main":
                    break
            if self.read("wBattleMode") == [0] and self.read("wScriptMode") == [0]:
                break
            if frame % 24 == 0:
                self.p.button("b" if self.ui_state in ("moves", "bags") else "a", delay=4)
            self.tick(1)
        else:
            raise AssertionError((name, "Action did not finish", self.ui_state, hex(self.p.register_file.PC)))
        assert record["attack_helper_entries"] >= 1, (name, "Player pose helper was never reached")
        assert record["actual_moves"] == {move}, (name, "Wrong move actually executed", record["actual_moves"])
        if scenes:
            assert {"idle", "brace"} <= record["native_poses"], (name, record["native_poses"])
            assert {"idle", "brace"} <= record["pixel_poses"], (name, "Actual pose pixels/palette mismatch", record["pixel_poses"])
            if move == 1:
                assert "swing" in record["native_poses"] and "swing" in record["pixel_poses"], (name, "Mace follow-through missing")
        else:
            assert not {"brace", "swing"} & record["native_poses"], (name, "Scenes OFF still changes the rear pose")
        self.release_all()
        in_battle = self.read("wBattleMode")[0] != 0
        if in_battle:
            self.check_protected_after_turn(protected, name)
            static = self.verify_idle()
        else:
            assert name.startswith("normal_"), (name, "Diagnostic enemy unexpectedly defeated")
            static = {"normal_battle_returned_to_world": True}
        for pose, screen in record["screens"].items():
            screen.save(OUT / f"{name}_{pose}_actual_rom.png")
            screen.resize((640, 576), Image.Resampling.NEAREST).save(OUT / f"{name}_{pose}_actual_rom_4x.png")
            index = POSES.index(pose)
            rgba = np.array(screen.convert("RGBA").crop((16, 48, 64, 96)))
            rgba[self.pose_pixels[index] == 0] = 0
            rgba[self.pose_pixels[index] != 0, 3] = 255
            assert set(np.unique(rgba[:, :, 3])) == {0, 255}
            Image.fromarray(rgba, "RGBA").save(OUT / f"{name}_{pose}_actual_native_transparent.png")
        if record["frames"]:
            gif = [frame.resize((320, 288), Image.Resampling.NEAREST) for frame in record["frames"]]
            # GIF duration is quantized to 10 ms; 20/20/10 retains 60 fps on
            # average instead of silently rounding every 17-ms frame to 10.
            durations = [10 if i % 3 == 2 else 20 for i in range(len(gif))]
            gif[0].save(OUT / f"{name}_actual_rom.gif", save_all=True, append_images=gif[1:], duration=durations, loop=0)
        self.recording = None
        return {"move_id": move, "scenes_on": scenes, "actual_button_cast": True,
                "native_animation_id_not_substituted": True,
                "native_poses": sorted(record["native_poses"]), "native_sequence": record["native_sequence"],
                "actual_rgb555_matched_poses": sorted(record["pixel_poses"]),
                "matched_native_frames": record["matched_frames"],
                "protected_helper_returns": record["protected_helper_returns"], **static}


def main():
    logging.disable(logging.CRITICAL); OUT.mkdir(parents=True, exist_ok=True)
    sym = load_symbols()
    assert "PeonAnimatePlayerAttack" in sym and "PeonRestorePlayerIdlePose" in sym, "Build the player-pose integration first"
    report = {"rom_sha256": hashlib.sha256((ROOT / "pokecrystal.gbc").read_bytes()).hexdigest(),
              "normal_route": {"ram_edits": False, "emulator_states_loaded": False}, "diagnostics": {}}
    with tempfile.TemporaryDirectory(prefix="peon-player-poses-") as temporary:
        rom = Path(temporary) / "player.gbc"; shutil.copyfile(ROOT / "pokecrystal.gbc", rom)
        s = PlayerSession(rom, sym)
        try:
            s.fresh(); s.buy_potion(); s.talk((10, 10), "up", "gornek_before_player_test")
            s.navigate((18, 13)); s.press("up", 30)
            world = io.BytesIO(); s.p.save_state(world)
            s.press("a"); s.wait_main()
            report["normal_route"]["totem"] = s.use_bag_item(TOTEM)
            report["normal_route"]["potion"] = s.use_bag_item(POTION)
            report["normal_route"]["mace"] = s.cast("normal_mace", 1, slot=0)
            report["normal_route"]["lightning_bolt"] = s.cast("normal_lightning_bolt", 84, slot=1)
            s.recording = None; world.seek(0); s.p.load_state(world)
            s.diagnostic_species = 67; s.ui_state = "none"; s.release_all()
            s.press("a"); s.wait_main()
            s.write("wBattleMonHP", [0, 240]); s.write("wBattleMonMaxHP", [0, 240])
            s.write("wEnemyMonHP", [0, 240]); s.write("wEnemyMonMaxHP", [0, 240])
            s.write("wPeonEarthTotemActive", [1]); s.bag_return(); s.check_static()
            baseline = io.BytesIO(); s.p.save_state(baseline)
            for name, move, scenes in [("diagnostic_mace", 1, True), ("diagnostic_lightning", 84, True),
                                       ("diagnostic_flame_shock", 52, True), ("diagnostic_healing", 105, True),
                                       ("diagnostic_rockbiter", 14, True), ("diagnostic_lightning_shield", 115, True),
                                       ("diagnostic_scenes_off", 1, False)]:
                s.recording = None; baseline.seek(0); s.p.load_state(baseline)
                s.ui_state = "main"; s.pose_returns.clear(); s.release_all()
                s.set_move(move); s.write("wPlayerStatLevels", [7] * 7); s.write("wEnemyStatLevels", [7] * 7)
                s.write("wEnemyMonMoves", [33, 0, 0, 0]); s.write("wEnemyMonPP", [40, 0, 0, 0])
                if move == 105:
                    s.write("wBattleMonHP", [0, 60])
                # Bit 7 is Crystal's existing battle scenes option.
                options = s.read("wOptions")[0]
                s.write("wOptions", [options & 0x7f if scenes else options | 0x80])
                report["diagnostics"][name] = s.cast(name, move, scenes=scenes)
                s.bag_return(); s.check_static()
            s.p.stop(save=False)
        except BaseException:
            s.capture("unexpected_player_pose"); s.p.stop(save=False); raise
    report["diagnostic_inputs"] = ["gold enemy species67 at the normal encounter loader", "HP/maxHP240",
                                  "temporary move/PP selection", "Healing Wave HP60", "Earth Totem active1",
                                  "existing battle-scenes option bit7", "rewound isolated encounter state"]
    report["all_checks_passed"] = True
    (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Native player combat poses passed:", report["rom_sha256"])


if __name__ == "__main__":
    main()
