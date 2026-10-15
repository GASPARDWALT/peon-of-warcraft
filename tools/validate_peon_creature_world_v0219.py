#!/usr/bin/env python3
"""Observe the actual boar and Kolkar world bodies with ordinary controls.

Starts one fresh private Shaman game, approaches the Den boar, then walks
through Valley of Trials to its gate's two visible Kolkar. No emulator memory
writes, state loads, source mutations or existing batteries are permitted.
The gate's actual collision corridor requires passing both Kolkar encounter
cells. The west encounter's native RUN command is used; no party or encounter
state is edited. Testing the eastern Road exit is outside this art probe.
"""
from pathlib import Path
import argparse
import hashlib
import json
import logging
import shutil
import tempfile

from PIL import Image

import validate_peon_world_actors_v0216 as checks
from validate_peon_world_restore_v0219 import RestoredWorldSession
from validate_peon_earth_stone_v0212 import MAPS
from validate_peon_exit_title import symbols
from validate_peon_villages import sprite_constants

ROOT = Path(__file__).resolve().parents[1]
GFX = ROOT / "gfx/world_readability_v0219"
ROLES = {"boar": "SPRITE_POKE_BALL", "kolkar_archer": "SPRITE_COOLTRAINER_M",
         "kolkar_raider": "SPRITE_COOLTRAINER_F"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


class CreatureSession(RestoredWorldSession):
    def __init__(self, *args):
        self.completed_world_oam = []
        self.creature_manifest = json.loads((GFX / "manifest.json").read_text())
        self.creature_sprite_ids = sprite_constants()
        super().__init__(*args)

    def renderer_finish(self, context):
        super().renderer_finish(context)
        used = self.read("hUsedSpriteIndex")[0]
        if not used or self.read("wBattleMode")[0]:
            return
        assert used <= 160 and not used % 4
        shadow = self.read("wShadowOAM", 160)
        for offset in range(used, 160, 4):
            shadow[offset] = 160  # native hidden-tail fill, predicted read-only
        self.completed_world_oam.append(bytes(shadow))
        self.completed_world_oam = self.completed_world_oam[-8:]

    def creature_observation(self, role):
        """Require the whole unclipped native body and every opaque LCD pixel."""
        key = self.creature_sprite_ids[ROLES[role]]
        raw = list(self.p.memory[0xfe00:0xfea0])
        assert bytes(raw) in self.completed_world_oam, "No complete native OAM publication"
        cells = [tuple(raw[i:i + 4]) for i in range(0, 160, 4)
                 if 8 < raw[i] < 160 and 0 < raw[i + 1] < 168]
        occupancy = [sum(y <= line + 16 < y + 8 for y, x, tile, flags in cells)
                     for line in range(144)]
        assert len(cells) <= 40 and max(occupancy, default=0) <= 10
        cache_ids = self.read("wPeonLargeWorldCacheIDsV0215", 13)
        cache_frames = self.read("wPeonLargeWorldCacheFramesV0215", 13)
        structs = self.read("wObjectStructs", 13 * 40)
        candidates = [i for i in range(1, 13) if cache_ids[i] == key and structs[i * 40]
                      and (role != "boar" or structs[i * 40 + 1] == 3)]
        assert len(candidates) == 1, ("Creature native slot unavailable", role, candidates)
        slot = candidates[0]
        frame = cache_frames[slot]
        assert frame < 12
        folder = GFX / role
        packet = (folder / "overworld.bin").read_bytes()[frame * 144:(frame + 1) * 144]
        masks = (folder / "masks.bin").read_bytes()
        mask = int.from_bytes(masks[frame * 2:frame * 2 + 2], "little")
        attrs = (folder / "attrs.bin").read_bytes()[frame * 9:(frame + 1) * 9]
        desc = self.descriptor(key)
        address = int.from_bytes(desc[3:5], "little") + frame * 144
        assert self.rom_range(desc[2], address, 144) == packet, (role, "ROM/source packet differs")
        assert bytes(self.p.memory[1, 0x8000 + slot * 144:0x8000 + (slot + 1) * 144]) == packet
        mask_address = int.from_bytes(desc[6:8], "little")
        assert self.rom_range(desc[5], mask_address + frame * 2, 2) == mask.to_bytes(2, "little")
        assert self.rom_range(desc[5], mask_address + 24 + frame * 9, 9) == attrs
        body = [cell for cell in cells if cell[3] & 8 and cell[2] // 9 == slot]
        active = {i for i in range(9) if mask & 1 << i}
        assert {tile % 9 for y, x, tile, flags in body} == active, (role, "Body partly culled", body, active)
        origins = {(x - 8 - tile % 9 % 3 * 8, y - 16 - tile % 9 // 3 * 8)
                   for y, x, tile, flags in body}
        assert len(origins) == 1, (role, "Body cells split between origins")
        origin_x, origin_y = next(iter(origins))
        assert all(0 <= x - 8 and x <= 160 and 0 <= y - 16 and y - 8 <= 144
                   for y, x, tile, flags in body), (role, "Body viewport-clipped")
        assert all(flags & 7 == attrs[tile % 9] and not flags & 0x60
                   for y, x, tile, flags in body), (role, "Palette or mirror differs")
        palette_data = bytes(self.read("wOBPals2", 64))
        expected_palettes = self.creature_manifest["effective_world_palettes_rgb555"]
        for palette in set(attrs):
            for color in range(4):
                value = int.from_bytes(palette_data[palette * 8 + color * 2:palette * 8 + color * 2 + 2], "little")
                assert tuple(value >> shift & 31 for shift in (0, 5, 10)) == tuple(expected_palettes[palette][color]), (
                    role, "Actual world OBJ palette differs", palette, color)
        lcd = self.p.screen.image.convert("RGB")
        checked = 0
        for y, x, tile, flags in body:
            indices = self.tile_indices(packet[tile % 9 * 16:(tile % 9 + 1) * 16])
            for py, row in enumerate(indices):
                for px, color in enumerate(row):
                    if not color:
                        continue
                    sx, sy = x - 8 + px, y - 16 + py
                    assert lcd.getpixel((sx, sy)) == self.palette_rgb(flags & 7, color), (
                        role, "Actual creature LCD pixel differs", frame, sx, sy,
                        lcd.getpixel((sx, sy)), self.palette_rgb(flags & 7, color))
                    checked += 1
        assert checked > 100, (role, "Insufficient complete-body actual pixels")
        return {"role": role, "native_slot": slot, "native_sprite": key, "frame": frame,
                "direction": ("front", "back", "left", "right")[frame // 3],
                "world_xy": [structs[slot * 40 + 16] - 4, structs[slot * 40 + 17] - 4],
                "whole_ROM_and_VRAM_144_bytes_exact": True, "frame_sha256": sha(packet),
                "source_mask_exact": mask, "complete_unclipped_OAM_cells": len(body),
                "all_source_palette_attributes_exact": True,
                "actual_LCD_all_opaque_source_pixels_exact": checked,
                "native_canvas_origin": [origin_x, origin_y],
                "native_OAM_objects": len(cells), "maximum_objects_per_scanline": max(occupancy),
                "complete_native_OAM_publication": True}

    def capture_creatures(self, roles, label):
        last_error = None
        for _ in range(240):
            self.p.tick(1, True)
            if self.read("hOAMUpdate") != [0] or self.read("wBattleMode") != [0] or self.read("wScriptMode") != [0]:
                continue
            try:
                records = {role: self.creature_observation(role) for role in roles}
                self.capture(label)
                return {"map": self.map(), "player_position": list(self.position()), "actors": records,
                        "all_actual_creature_pixels_required_no_occlusion_skips": True}
            except AssertionError as error:
                last_error = error
        raise AssertionError(("No complete native creature LCD observation", roles, repr(last_error)))

    def flee_gate_pack(self, label):
        self.wait_for(lambda: self.phase == "battle", buttons=True)
        flags_before = self.read("wEventFlags", 256)
        experience_before = self.read("wPartyMon1Exp", 3)
        copper_before = self.money()
        actions = []
        healed_last = False
        for _ in range(24):
            if self.read("wBattleMode") == [0]:
                break
            self.ready("battle")
            hp, maximum = self.word("wBattleMonHP"), self.word("wBattleMonMaxHP")
            # This is the ordinary starter Potion in the native inventory.
            # One heal may precede another RUN attempt; do not spend several
            # consecutive Potions while the same enemy keeps taking turns.
            if hp * 3 <= maximum * 2 and self.item_quantity(18) and not healed_last:
                self.open_bag_item(18)
                previous = self.menus
                self.press("a", 30)
                self.wait_for(lambda: self.menus > previous and self.phase == "battle"
                              or not self.read("wBattleMode")[0], buttons=True)
                actions.append({"native_action": "POTION", "HP_before": hp})
                healed_last = True
                continue
            for _ in range(6):
                x, y = self.read("wMenuCursorX")[0], self.read("wMenuCursorY")[0]
                if (x, y) == (2, 2):
                    break
                self.press("right" if x < 2 else "down", 30)
            assert (self.read("wMenuCursorX")[0], self.read("wMenuCursorY")[0]) == (2, 2)
            previous = self.menus
            self.phase, self.context = "run_pending", None
            self.press("a", 30)
            self.wait_for(lambda: self.menus > previous and self.phase == "battle"
                          or not self.read("wBattleMode")[0], buttons=True)
            actions.append({"native_action": "RUN", "HP_before": hp,
                            "battle_still_active": bool(self.read("wBattleMode")[0])})
            healed_last = False
        assert self.read("wBattleMode") == [0] and self.read("wBattleResult") == [2], (
            "Ordinary RUN did not escape", label, actions, self.map(), self.position())
        self.close_dialogue()
        self.p.tick(90, True)
        assert self.map() == 29, ("Gate flee did not remain in the gate", self.map())
        assert self.read("wEventFlags", 256) == flags_before
        assert self.read("wPartyMon1Exp", 3) == experience_before and self.money() == copper_before
        self.capture(label)
        return {"ordinary_native_actions": actions, "native_RUN_result": 2,
                "no_experience_or_copper_reward": True, "all_event_flags_unchanged": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--sym", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-rom-sha256")
    args = parser.parse_args()
    args.output = args.output.resolve()
    logging.disable(logging.CRITICAL)
    args.output.mkdir(parents=True, exist_ok=True)
    digest = sha(args.rom.read_bytes())
    if args.expected_rom_sha256:
        assert digest == args.expected_rom_sha256
    checks.ART_ROOT = ROOT / "references/generated/world_readability_v0219"
    checks.ASSET_MANIFEST = GFX / "manifest.json"
    checks.GRAPHICS = GFX / "graphics.asm"
    MAPS[29] = ("PeonValleyExit", 5, 5)
    report = {"version": "v0.2.19", "status": "RUNNING", "rom_sha256": digest,
              "sym_sha256": sha(args.sym.read_bytes()), "ordinary_buttons_only": True,
              "emulator_memory_edits": False, "state_restores": False,
              "user_batteries_opened": False, "captures": [], "observations": {}}
    session = None
    try:
        with tempfile.TemporaryDirectory(prefix="peon-creature-world-v0219-") as temporary:
            rom = Path(temporary) / "private.gbc"
            shutil.copyfile(args.rom, rom)
            session = CreatureSession(rom, symbols(args.sym), 0, args.output)
            session.fresh_class()
            # Two grid squares west of the quest boar, away from the nearby
            # Scorpid's adjacent trigger cells. No talk or combat is needed.
            session.navigate((16, 12))
            report["observations"]["boar"] = session.capture_creatures(["boar"], "native_boar_world_complete")
            session.navigate((20, 10), expected_map=15)
            session.navigate((28, 12), expected_map=29)
            # The real row3 is a wall. Cross the existing west encounter,
            # escape normally, then stand centrally without contacting either
            # body. Both actual source rear views are unobscured at this spot.
            session.navigate((3, 4))
            first_flee = session.flee_gate_pack("ordinary_west_Kolkar_RUN")
            session.navigate((5, 4))
            report["observations"]["kolkar_pair"] = session.capture_creatures(
                ["kolkar_archer", "kolkar_raider"], "native_kolkar_pair_world_complete")
            assert not session.renderer_hook_errors, session.renderer_hook_errors
            assert not session.background_errors, session.background_errors
            report["route"] = {"maps": [14, 15, 29], "mandatory_native_encounters": 1,
                               "ordinary_RUN_observations": [first_flee],
                               "no_Kolkar_retirement": not session.event("EVENT_PEON_KOLKAR_PACK_DEAD_V029"),
                               "final_native_map": session.map(), "final_position": list(session.position()),
                               "scope": "Complete native boar and two Kolkar world bodies; eastern Durotar Road exit not tested"}
            for label in ("native_boar_world_complete", "native_kolkar_pair_world_complete", "ordinary_west_Kolkar_RUN"):
                path = session.folder / (label + ".png")
                image = Image.open(path)
                assert image.size == (160, 144) and image.convert("RGBA").getchannel("A").getextrema() == (255, 255)
                capture_path = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
                report["captures"].append({"name": label + ".png", "path": capture_path,
                                            "sha256": sha(path.read_bytes()), "rom_sha256": digest})
            report["status"] = "PASS"
    except Exception as error:
        report["status"], report["failure"] = "FAIL", repr(error)
        if session is not None:
            session.capture("failure")
            report["failure_state"] = {"map": session.map(), "position": list(session.position()),
                                        "battle": session.read("wBattleMode"), "script": session.read("wScriptMode")}
        raise
    finally:
        if session is not None:
            session.p.stop(save=False)
        (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "rom_sha256": digest,
                      "observations": report["observations"]}, indent=2))


if __name__ == "__main__":
    main()
