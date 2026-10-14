#!/usr/bin/env python3
"""Observe resized Shaman cards/poses in a real ROM using normal controls.

Fresh private ROM; read-only hooks inspect uploads and complete LCD actor
rectangles. No RAM/ROM writes, CPU substitutions, state loads or user saves.
"""
import argparse
import hashlib
import json
import logging
from pathlib import Path
import shutil
import tempfile

import numpy as np
from PIL import Image

from validate_peon_roster_v0213 import RosterSession
from validate_peon_battle_names_v0213 import BattleNamesSession
from validate_peon_exit_title import symbols

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'gfx/shaman_proportions_v0214'


def sha(data): return hashlib.sha256(data).hexdigest()


def decode(raw, width, height, column=False):
    result = np.zeros((height, width), dtype='uint8')
    cols, rows = width // 8, height // 8
    for i in range(cols * rows):
        tx, ty = divmod(i, rows) if column else (i % cols, i // cols)
        for y in range(8):
            lo, hi = raw[i * 16 + y * 2:i * 16 + y * 2 + 2]
            for x in range(8):
                result[ty * 8 + y, tx * 8 + x] = (lo >> (7 - x) & 1) | (hi >> (7 - x) & 1) << 1
    return result


class FrameBoy:
    def __init__(self, raw, owner): self.raw, self.owner = raw, owner
    def __getattr__(self, name): return getattr(self.raw, name)
    def tick(self, count=1, render=True, sound=True):
        for _ in range(count):
            result = self.raw.tick(1, render, sound)
            self.owner.after_frame()
        return result


class ShamanSession(RosterSession):
    def __init__(self, rom, sym, output):
        self.frames = 0; self.uploads = []; self.pending = []; self.pose_errors = []
        self.actor_checks = []; self.seen = set(); self.current_pose_move = 0
        self.pose_frames = {1: [], 84: []}
        self.native_attacks = []; self.card_check = None
        self.back = (PACK / 'back_frames.bin').read_bytes()
        self.front = (PACK / 'front_frames.bin').read_bytes()
        self.profile = (PACK / 'portrait_frames.bin').read_bytes()
        assert len(self.back) == 1728 and len(self.front) == len(self.profile) == 2352
        self.back_indices = [decode(self.back[n * 576:(n + 1) * 576], 48, 48, True) for n in range(3)]
        self.profile_indices = decode(self.profile[:784], 56, 56)
        assert np.array_equal(self.profile_indices, decode(self.front[:784], 56, 56, True))
        super().__init__(rom, sym, 0, output)

    def open(self):
        super().open()
        self.p = FrameBoy(self.p, self)
        for label, observer in [('PeonLoadClassPlayerBackPose', self.back_enter),
                                ('PeonAnimatePlayerAttack', self.attack_enter)]:
            self.p.hook_register(*self.sym[label], lambda _, observer=observer: self.safe(observer), None)
        helper = 'PeonClassGetBackPoseBank0'
        bank, address = self.sym[helper]
        data = Path(self.rom).read_bytes()
        offset = bank * 0x4000 + address - 0x4000
        code = data[offset:offset + 96]
        end = code.index(bytes((0xf1, 0xe0, 0x4f, 0xf1, 0xe0))) + 6
        assert code[end] == 0xc9, 'Native backpose helper RET not found'
        self.p.hook_register(bank, address + end, lambda _: self.safe(self.back_uploaded), None)

    def safe(self, observer):
        try: observer()
        except Exception as error: self.pose_errors.append(repr(error))

    def fresh_class(self): BattleNamesSession.fresh_class(self)

    def attack_enter(self):
        if self.read('wBattleMode')[0] and self.read('hBattleTurn') == [0] and self.read('wFXAnimID', 2)[1] == 0:
            move = self.read('wCurPlayerMove')[0]
            if self.read('wFXAnimID')[0] == move and move in (1, 84):
                self.current_pose_move = move
                self.native_attacks.append({'frame': self.frames, 'move': move})

    def back_enter(self):
        frame = self.p.register_file.C
        assert frame in (0, 1, 2), frame
        self.pending.append({'frame': frame, 'move': self.current_pose_move,
                             'battle': bool(self.read('wBattleMode')[0])})

    def back_uploaded(self):
        if not self.pending: return
        row = self.pending.pop(0)
        raw = bytes(self.p.memory[0, 0x9310:0x9550])
        expected = self.back[row['frame'] * 576:(row['frame'] + 1) * 576]
        assert raw == expected, ('Native uploaded Shaman pose differs', row, sha(raw), sha(expected))
        row.update({'observed_frame': self.frames, 'bytes': 576, 'vram_bank': 0,
                    'address': '$9310', 'source_packet_exact': True, 'sha256': sha(raw)})
        self.uploads.append(row)

    def palette(self, index):
        raw = bytes(self.read('wBGPals2', 64))[index * 8:(index + 1) * 8]
        values = [int.from_bytes(raw[n:n + 2], 'little') for n in range(0, 8, 2)]
        return np.array([(v & 31, v >> 5 & 31, v >> 10 & 31) for v in values], dtype='uint8')

    def after_frame(self):
        self.frames += 1
        assert not self.pose_errors, self.pose_errors
        if self.read('wBattleMode') != [1] or self.read('wBattleMonSpecies') != [66]: return
        if self.p.memory[0xff42] or self.p.memory[0xff43]: return
        raw = bytes(self.p.memory[0, 0x9310:0x9550])
        matches = [n for n in range(3) if raw == self.back[n * 576:(n + 1) * 576]]
        if not matches: return
        phase = matches[0]
        actual = np.asarray(self.p.screen.image.convert('RGB'))[48:96, 16:64] >> 3
        expected = self.palette(0)[self.back_indices[phase]]
        if not np.array_equal(actual, expected): return
        base = 0x9c00 if self.p.memory[0xff40] & 8 else 0x9800
        for y in range(6):
            for x in range(6):
                address = base + (y + 6) * 32 + x + 2
                tile, attr = self.p.memory[0, address], self.p.memory[1, address]
                # The next VBlank may already prepare a blank/fade while
                # PyBoy still holds the completed actor frame. Record only
                # frames whose displayed actor map is also fully resident.
                if tile != 0x31 + x * 6 + y or attr & 0x0f != 0: return
        move = self.current_pose_move
        key = (move, phase)
        if key not in self.seen:
            self.seen.add(key)
            row = {'move': move, 'pose': phase, 'frame': self.frames,
                   'source_packet_exact': True, 'complete_48x48_rgb555_pixels_exact': True,
                   'all_36_hardware_tiles_column_major_bank0_palette0': True}
            self.actor_checks.append(row)
            self.capture(f'back_move_{move}_pose_{phase}_actual_lcd')
        if move in self.pose_frames and len(self.pose_frames[move]) < 120 and self.frames % 3 == 0:
            self.pose_frames[move].append(self.p.screen.image.copy())

    def check_card(self):
        self.open_roster(0); self.member_action(1)
        self.wait_for(lambda: self.presentation == 'hero_summary')
        self.p.tick(90, True)
        raw = bytes(self.p.memory[0, 0x9400:0x9710])
        assert raw == self.profile[:784], 'Native SUMMARY portrait is not the new row-major Shaman'
        actual = np.asarray(self.p.screen.image.convert('RGB'))[24:80, 8:64] >> 3
        expected = self.palette(2)[self.profile_indices]
        assert np.array_equal(actual, expected), 'Complete 56x56 SUMMARY actor differs on LCD'
        base = 0x9c00 if self.p.memory[0xff40] & 8 else 0x9800
        for y in range(7):
            for x in range(7):
                address = base + (y + 3) * 32 + x + 1
                assert self.p.memory[0, address] == 0x40 + y * 7 + x
                assert self.p.memory[1, address] & 0x0f == 2
        self.card_check = {'ordinary_START_ROSTER_SUMMARY': True, 'source_row_major_49_tiles_exact': True,
                           'complete_56x56_rgb555_pixels_exact': True, 'native_bank0_palette2': True}
        self.capture('roster_SUMMARY_new_shaman_front_actual_lcd')
        self.press('b'); self.wait_for(lambda: self.presentation == 'roster'); self.close_roster()

    def cast(self, slot):
        self.wait_for(lambda: self.phase == 'battle' or not self.read('wBattleMode')[0], True)
        assert self.read('wBattleMode') == [1], 'Encounter ended before requested native move'
        old = self.move_menus
        for _ in range(6):
            x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
            if (x, y) == (1, 1): break
            self.press('left' if x > 1 else 'up', 30)
        self.press('a', 60); self.wait_for(lambda: self.move_menus > old)
        for _ in range(5):
            current = self.read('wCurMoveNum')[0]
            if current == slot: break
            self.press('up' if current > slot else 'down', 30)
        self.press('a', 180)
        move = (1, 84)[slot]
        wanted = {(move, 0), (move, 1)} | ({(move, 2)} if move == 1 else set())
        self.wait_for(lambda: wanted <= self.seen or not self.read('wBattleMode')[0], True)
        assert wanted <= self.seen, ('Native selected move poses not observed', move, self.seen)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', type=Path, required=True); parser.add_argument('--sym', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--expected-sha256')
    args = parser.parse_args(); logging.disable(logging.CRITICAL)
    digest = sha(args.rom.read_bytes())
    if args.expected_sha256: assert digest == args.expected_sha256
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'status': 'RUNNING', 'rom_sha256': digest, 'ordinary_controls_only': True,
              'RAM_or_ROM_writes': False, 'CPU_substitutions': False, 'state_loads': False, 'user_saves_opened': False}
    runs = {}
    with tempfile.TemporaryDirectory(prefix='peon-shaman-proportions-') as temp:
        for label, slot in (('mace', 0), ('lightning', 1)):
            rom = Path(temp) / (label + '.gbc'); shutil.copyfile(args.rom, rom)
            s = ShamanSession(rom, symbols(args.sym), args.output / label)
            try:
                s.fresh_class()
                if label == 'mace': s.check_card()
                s.talk_at((10, 10), 'up', 'ordinary_gornek_quest')
                s.navigate((18, 13)); s.press('up', 30); s.press('a', 60)
                s.wait_for(lambda: s.phase == 'battle' and s.read('wBattleMode')[0], True)
                s.p.tick(30, True); s.cast(slot)
                assert not s.pose_errors
                if label == 'mace':
                    assert {row['frame'] for row in s.uploads} >= {0, 1, 2}
                    assert s.card_check
                images = s.pose_frames[(1, 84)[slot]]
                if images:
                    images[0].save(s.folder / 'native_cast.gif', save_all=True,
                                   append_images=images[1:], duration=50, loop=0, optimize=False)
                runs[label] = {'status': 'PASS', 'native_pose_uploads': s.uploads,
                               'actual_actor_checks': s.actor_checks,
                               'native_player_animations': s.native_attacks,
                               'roster_summary': s.card_check,
                               'ordinary_fresh_shaman_first_boar_encounter': True}
            except Exception as error:
                report['failure'] = repr(error); s.capture('failure'); raise
            finally:
                report['runs'] = runs
                (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
                s.p.stop(save=False)
    report['status'] = 'PASS'
    (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
