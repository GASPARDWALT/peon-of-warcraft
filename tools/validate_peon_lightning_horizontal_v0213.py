#!/usr/bin/env python3
"""Observe horizontal Lightning Bolt on the actual ROM through normal buttons.

Fresh private shaman uses the normal quest rock battle. Native hooks inspect
VRAM, OAM and rendered source pixels; no RAM/ROM edits, CPU substitutions,
emulator states, or user batteries are used. Both cast directions are sought
through genuine enemy choices. The original caster pose dispatch is observed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import logging
import shutil
import tempfile

from PIL import Image

from validate_peon_earth_stone_v0212 import EarthSession
from validate_peon_exit_title import symbols
from validate_peon_spell_pack_v1 import SpellSession
from peon_ordinary_battle_readiness_v0213 import OrdinaryBattleReadiness

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "references/generated/spell_tests/lightning_horizontal_v0213"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def observer_manifest():
    data = json.loads((OUT / "import_manifest.json").read_text())
    folder = "gfx/peon_lightning_horizontal_v0213/"
    packet = {"ability": "lightning_bolt", "2bpp": data["packet"]["2bpp"],
              "palette_file": folder + "lightning_obj.gbcpal", "assets": []}
    for frame in data["frames"]:
        width, height = frame["native_canvas"]
        rows = []
        for x, y, tile, attrs in frame["OAM_rows"]:
            rows.append({"x": x * 8 + width // 2, "y": y * 8 + height // 2,
                         "tile_index": tile})
        packet["assets"].append({"oam_label": frame["oam_label"], "oam_count": frame["oam_count"],
                                 "canvas": [width, height], "tile_offset_records": rows,
                                 "source": folder + frame["role"] + "_source_rotated.png",
                                 "source_sha256": digest(ROOT / folder / (frame["role"] + "_source_rotated.png")),
                                 "orientation": {"player": "player_back", "enemy": "enemy_front",
                                                 "impact": "target"}[frame["role"]]})
    return {"packets": [packet]}, data


class FrameBoy:
    def __init__(self, raw, session):
        self.raw, self.session = raw, session

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def tick(self, count=1, render=True, sound=True):
        result = None
        for _ in range(count):
            result = self.raw.tick(1, render)
            self.session.after_frame()
        return result


class HorizontalSession(OrdinaryBattleReadiness, EarthSession):
    def __init__(self, rom, sym, folder):
        self.frames = 0
        self.records, self.observations, self.snapshots = [], {}, []
        self.turn_observations = {0: {}, 1: {}}
        self.watch = False
        self.max_oam = self.max_scanline = self.observed_oam_frames = 0
        self.moves, self.pose_uploads = [], []
        self.manifest, self.import_data = observer_manifest()
        self.packets, self.assets = {}, {}
        for packet in self.manifest["packets"]:
            packet["_raw"] = (ROOT / packet["2bpp"]).read_bytes()
            packet["_pal"] = (ROOT / packet["palette_file"]).read_bytes()
            self.packets[packet["ability"]] = packet
            for asset in packet["assets"]:
                asset["_packet"] = packet
                self.assets[sym[asset["oam_label"]][1]] = asset
        self.position_log = {0: [], 1: []}
        self.hook_errors = []
        self.data = Path(rom).read_bytes()
        super().__init__(rom, sym, 0, folder)
        # EarthSession keeps a ROM bytefield for warps; the spell observer's
        # same name is a lookup method. Our warp override uses self.data.
        del self.rom_bytes

    def open(self):
        super().open()
        self.p = FrameBoy(self.p, self)
        self.p.hook_register(*self.sym["PeonRenderSpellV1OAM"], self.render, None)
        self.p.hook_register(*self.sym["PeonLoadClassPlayerBackPose"], self.pose, None)
        self.p.hook_deregister(*self.sym["BattleCommand_UsedMoveText"])
        self.p.hook_register(*self.sym["BattleCommand_UsedMoveText"], self.used_move, None)

    rom_bytes = SpellSession.rom_bytes
    source_alpha = SpellSession.source_alpha
    observe = SpellSession.observe
    finish_observations = SpellSession.finish_observations

    def native_warps(self, name):
        bank, address = self.sym[name + "_MapEvents"]
        offset = bank * 0x4000 + address - 0x4000
        count = self.data[offset + 2]
        return {(self.data[offset + 4 + index * 5], self.data[offset + 3 + index * 5])
                for index in range(count)}

    def used_move(self, _):
        turn = self.read("hBattleTurn")[0]
        move = self.read("wCurEnemyMove" if turn else "wCurPlayerMove")[0]
        self.moves.append({"turn": turn, "move": move, "frame": self.frames})

    def pose(self, _):
        if self.watch and self.read("wFXAnimID", 2) == [84, 0] and self.read("hBattleTurn") == [0]:
            self.pose_uploads.append({"frame": self.frames, "index": self.p.register_file.C})

    def render(self, _):
        if self.p.register_file.HL not in self.assets:
            return
        try:
            SpellSession.render(self, None)
        except Exception as error:
            self.hook_errors.append(repr(error))
            return
        row = self.records[-1]
        if row["asset"]["orientation"] != "target":
            self.position_log[row["turn"]].append({"frame": self.frames, "xy": row["xy"]})

    def after_frame(self):
        self.frames += 1
        assert not self.hook_errors, self.hook_errors[:1]
        if self.watch and self.records:
            records = self.records
            for turn in (0, 1):
                self.observations = self.turn_observations[turn]
                self.records = [row for row in records if row["turn"] == turn]
                self.observe()
            self.records = records

    def cast(self, slot):
        self.wait_for(lambda: self.phase == "battle" or not self.read("wBattleMode")[0], True)
        if not self.read("wBattleMode")[0]:
            return
        menus, move_menus = self.menus, self.move_menus
        for _ in range(6):
            x, y = self.read("wMenuCursorX")[0], self.read("wMenuCursorY")[0]
            if (x, y) == (1, 1):
                break
            self.press("left" if x > 1 else "up", 30)
        self.press("a", 45)
        self.wait_for(lambda: self.move_menus > move_menus)
        for _ in range(6):
            current = self.read("wMenuCursorY")[0] - 1
            if current == slot:
                break
            self.press("up" if current > slot else "down", 30)
        self.phase, self.context = "move_pending", None
        self.press("a", 30)
        self.wait_for(lambda: self.menus > menus and self.phase == "battle"
                      or not self.read("wBattleMode")[0], True)

    def full_direction_seen(self, turn):
        name = "PeonSpellV1Lightning" + ("Enemy" if turn else "Player") + "OAM"
        row = self.turn_observations[turn].get(name)
        return bool(row and row["LCD_frames"] > 20 and len(row["positions"]) > 20)

    def route(self):
        self.fresh_class()
        # The normal boar accepts Lightning damage; the later native rock
        # correctly keeps its Ground immunity after the roster update.
        self.talk_at((10, 10), "up", "gornek_boar_quest_offer")
        self.navigate((18, 13))
        self.press("up", 30)
        self.press("a", 30)
        self.wait_for(lambda: self.phase == "battle" and self.read("wBattleMode")[0], True)
        self.watch = True
        self.cast(1)
        self.until_world(choose_bolt=True)
        self.travel(15)
        self.talk_at((11, 11), "right", "rock_quest_offer")
        self.begin_elemental()
        self.watch = True
        # POUND preserves the living quest rock while genuine wild AI gets
        # chances to choose its native THUNDERSHOCK. Potions are normal items.
        for _ in range(12):
            if not self.read("wBattleMode")[0] or self.full_direction_seen(1):
                break
            if self.word("wBattleMonHP") <= self.word("wBattleMonMaxHP") // 2 and self.item_quantity(18):
                self.open_bag_item(18)
                self.phase, self.context = "using_item", None
                self.press("a", 30)
                self.wait_for(lambda: self.phase == "battle" or not self.read("wBattleMode")[0], True)
            else:
                self.cast(0)
        self.capture("horizontal_bolt_native_battle_return")

    def finish(self, require_enemy):
        self.out = self.folder
        assert self.full_direction_seen(0), "No complete horizontal player cast observed on the actual ROM."
        assert any(move["move"] == 84 and move["turn"] == 0 for move in self.moves)
        directions = {}
        for turn in (0, 1):
            if not self.full_direction_seen(turn):
                assert not require_enemy or not turn, "Native route did not observe a complete enemy Lightning Bolt."
                continue
            label = "enemy" if turn else "player"
            direction_folder = self.folder / label
            direction_folder.mkdir(parents=True, exist_ok=True)
            self.out = direction_folder
            self.observations = self.turn_observations[turn]
            metrics = self.finish_observations("lightning_bolt", turn)
            positions = self.position_log[turn]
            first, last = positions[0]["xy"], positions[-1]["xy"]
            assert (last[0] < first[0]) if turn else (last[0] > first[0])
            assert (last[1] > first[1]) if turn else (last[1] < first[1])
            assert abs(last[0] - first[0]) >= 90 and abs(last[1] - first[1]) <= 25
            directions[label] = {"assets": metrics, "first_anchor": first, "last_anchor": last,
                                 "motion": "right to left/down" if turn else "left to right/up",
                                 "projectile_canvas": [32, 16], "actual_positions": positions}
        self.out = self.folder
        return {"directions": directions, "native_used_moves": self.moves,
                "native_caster_pose_uploads": self.pose_uploads,
                "native_pose_indices": sorted({row["index"] for row in self.pose_uploads}),
                "actual_hardware_OAM_peak": self.max_oam,
                "actual_OBJ_per_scanline_peak": self.max_scanline,
                "OAM_observer_checks": self.observed_oam_frames}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "pokecrystal.gbc")
    parser.add_argument("--sym", type=Path, default=ROOT / "pokecrystal.sym")
    parser.add_argument("--output", type=Path, default=OUT / "runtime")
    parser.add_argument("--expected-rom-sha256")
    parser.add_argument("--require-enemy", action="store_true")
    parser.add_argument("--require-cast-phases", default="")
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    args.output.mkdir(parents=True, exist_ok=True)
    sha = digest(args.rom)
    if args.expected_rom_sha256:
        assert sha == args.expected_rom_sha256
    report = {"status": "RUNNING", "rom_sha256": sha, "sym_sha256": digest(args.sym),
              "ordinary_controls_only": True, "RAM_writes": False, "ROM_patches": False,
              "CPU_substitutions": False, "emulator_states_loaded": False, "user_saves_opened": False,
              "limitations": ["Physical Chromatic hardware was not tested."]}
    session = None
    try:
        with tempfile.TemporaryDirectory(prefix="peon-horizontal-lightning-normal-") as directory:
            private_rom = Path(directory) / "shaman.gbc"
            shutil.copyfile(args.rom, private_rom)
            session = HorizontalSession(private_rom, symbols(args.sym), args.output)
            session.route()
            report.update(session.finish(args.require_enemy))
            if args.require_cast_phases:
                needed = {int(value) for value in args.require_cast_phases.split(",")}
                assert needed <= set(report["native_pose_indices"]), ("Caster phases missing", needed, report["native_pose_indices"])
            report.update(status="PASS", all_checks_passed=True)
    except BaseException as error:
        report.update(status="FAIL", error=repr(error))
        if session is not None:
            session.capture("horizontal_lightning_failure")
        raise
    finally:
        if session is not None:
            session.p.stop(save=False)
        (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
