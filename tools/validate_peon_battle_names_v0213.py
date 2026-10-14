#!/usr/bin/env python3
"""Verify actual battle-name glyphs after native spell and victory text.

Fresh private ROM, ordinary controls and read-only hooks only. No RAM/ROM
writes, CPU substitutions, emulator states or user batteries are used.
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

from validate_peon_zone2_tracker_v0213 import Zone2Session, symbols
from validate_peon_deep_ui import text_encoding

ROOT = Path(__file__).resolve().parents[1]
REGULAR = (ROOT / 'gfx/font/peon_regular_v026.1bpp').read_bytes()
BOLD = (ROOT / 'gfx/font/peon_bold_v026.1bpp').read_bytes()


def tile(source, code):
    raw = source[(code - 128) * 8:(code - 127) * 8]
    return bytes(v for row in raw for v in (row, row))


class BattleNamesSession(Zone2Session):
    def __init__(self, rom, sym, folder):
        self.frame = 0
        self.victory_active = False
        self.pending = None
        self.pending_ppu = []
        self.victories = []
        self.moves = []
        self.hook_errors = []
        super().__init__(rom, sym, folder)

    def open(self):
        super().open()
        for label, observer in [('BattleTextbox', self.begin_text),
                                ('PromptButton', self.text_finished),
                                ('BattleCommand_UsedMoveText', self.used_move)]:
            def guarded(_, observer=observer, label=label):
                try: observer()
                except Exception as error:
                    self.hook_errors.append({'hook': label, 'error': repr(error)})
            # ClassSession already observes UsedMoveText; replace that observer
            # with another read-only observer instead of registering twice.
            if label == 'BattleCommand_UsedMoveText':
                self.p.hook_deregister(*self.sym[label])
            self.p.hook_register(*self.sym[label], guarded, None)

    def begin_text(self):
        self.victory_active = self.p.register_file.HL == self.sym['BattleText_EnemyMonFainted'][1]

    def text_finished(self):
        if self.victory_active and self.pending is None:
            enemy = self.read('wEnemyMonSpecies')[0]
            if not any(row['enemy_species'] == enemy for row in self.victories):
                # Release ordinary A/B input at the completed victory prompt
                # so a lucky one-hit battle cannot advance to EXP before the
                # framebuffer observation. This never writes game memory.
                self.p.button_release('a'); self.p.button_release('b')
                self.pending = (self.frame + 2, enemy)
                self.pending_ppu = []

    def used_move(self):
        turn = self.read('hBattleTurn')[0]
        self.moves.append({'turn': turn, 'move': self.read('wCurEnemyMove' if turn else 'wCurPlayerMove')[0]})

    def press(self, key, frames=90):
        self.p.button(key, delay=4)
        for _ in range(frames):
            if self.pending:
                self.pending_ppu.append(self.ppu_snapshot())
            self.p.tick(1, True)
            self.frame += 1
            if self.pending and self.frame >= self.pending[0]:
                _, enemy = self.pending
                self.pending = None
                self.check_victory(enemy)
        assert not self.hook_errors, self.hook_errors

    def fresh_class(self):
        # Ordinary intro/class/name entry, deliberately independent of retired
        # totem kit counts and the changed companion/ROSTER mechanics.
        self.p.tick(240, True)
        self.press('start'); self.press('down'); self.press('a')
        chosen = False
        for _ in range(200):
            if self.map() == 14 and self.read('wScriptMode') == [0]: break
            if self.class_ready and not chosen:
                self.p.tick(60, True)
                assert self.read('wMenuCursorY') == [0]
                self.press('a', 90); chosen = True
            if self.naming and not self.naming_done:
                self.p.tick(120, True)
                for i in range(5):
                    self.press('a', 35)
                    if i < 4: self.press('right', 35)
                self.press('start', 40); self.press('a')
                self.naming_done = True
            self.press('a')
        assert chosen and self.naming_done and self.map() == 14 and self.read('wScriptMode') == [0]
        assert self.event('EVENT_PEON_SHAMAN') and self.read('wPartyMon1Species') == [66]
        assert self.read('wPartyMon1Moves', 2) == [1, 84]
        self.capture('fresh_shaman')

    def ppu_snapshot(self):
        base = 0x9c00 if self.p.memory[0xff40] & 8 else 0x9800
        positions = [base + y * 32 + x for y in range(18) for x in range(20)]
        return {'tiles': [self.p.memory[0, address] for address in positions],
                'attrs': [self.p.memory[1, address] for address in positions],
                'sample_frame': self.frame}

    def check_victory(self, enemy):
        count = self.read('wPeonBoldGlyphCount')[0]
        codes = self.read('wPeonBoldGlyphCodes', count) if count else []
        assert count <= 23 and len(set(codes)) == count
        base = 0x9c00 if self.p.memory[0xff40] & 8 else 0x9800
        # Observe the PPU map actually being displayed. A prompt can finish
        # and clear the next RAM text buffer while its complete victory text
        # is still visible; that legitimate preparation is not a blank LCD.
        assert self.p.memory[0xff42] == self.p.memory[0xff43] == 0
        screen = np.asarray(self.p.screen.image.convert('RGB')) >> 3
        palette_data = bytes(self.read('wBGPals2', 64))
        checked = {'regular': 0, 'bold': 0}
        errors = []
        expected_text = {}
        chars = text_encoding()
        for y, text in ((14, 'Enemy '), (16, 'was defeated!')):
            expected_text.update({y * 20 + x: chars[ch] for x, ch in enumerate(text, 1)})
        nickname = self.read('wEnemyMonNickname', 11)
        for x, code in enumerate(nickname, 7):
            if code == 0x50: break
            expected_text[14 * 20 + x] = code
        def decoded(sample, n):
            value, attr = sample['tiles'][n], sample['attrs'][n]
            return codes[value - 0x92] if attr & 8 and 0x92 <= value < 0x92 + count else value
        # PyBoy finishes the LCD frame and then runs the following VBlank.
        # A fast prompt can clear the hardware map in that VBlank. Retain
        # the map from immediately before tick, which the captured frame
        # actually consumed, and still require every literal message code.
        candidates = [self.ppu_snapshot(), *reversed(self.pending_ppu)]
        displayed = next((sample for sample in candidates
                          if all(decoded(sample, n) == value for n, value in expected_text.items())), None)
        assert displayed is not None, 'No complete native victory text PPU sample was observed'
        tiles, attrs = displayed['tiles'], displayed['attrs']
        for y in (0, 7, 14, 16):
            for x in range(20):
                n = y * 20 + x; code, attr = tiles[n], attrs[n]
                if attr & 8 and 0x92 <= code < 0x92 + count:
                    decoded = codes[code - 0x92]
                    source = tile(BOLD, decoded); style = 'bold'
                elif code >= 128:
                    decoded = code
                    source = tile(REGULAR, code); style = 'regular'
                else: continue
                if n in expected_text and decoded != expected_text[n]:
                    errors.append({'cell': [x, y], 'expected_text_code': expected_text[n],
                                   'actual_text_code': decoded})
                pattern = 0x9000 + (code if code < 128 else code - 256) * 16
                if bytes(self.p.memory[attr >> 3 & 1, pattern:pattern + 16]) != source:
                    errors.append({'cell': [x, y], 'glyph': 'VRAM bytes differ', 'style': style})
                    continue
                palette = []
                for color in range(4):
                    offset = (attr & 7) * 8 + color * 2
                    word = int.from_bytes(palette_data[offset:offset + 2], 'little')
                    palette.append((word & 31, word >> 5 & 31, word >> 10 & 31))
                expected = np.array([[palette[(source[r * 2] >> (7 - c) & 1) |
                                             (source[r * 2 + 1] >> (7 - c) & 1) << 1]
                                      for c in range(8)] for r in range(8)], dtype='uint8')
                if attr & 32: expected = np.fliplr(expected)
                if attr & 64: expected = np.flipud(expected)
                if not np.array_equal(screen[y * 8:y * 8 + 8, x * 8:x * 8 + 8], expected):
                    errors.append({'cell': [x, y], 'glyph': 'actual RGB555 pixels differ', 'style': style})
                checked[style] += 1
        row = {'enemy_species': enemy, 'frame': self.frame, 'checked_glyphs': checked,
               'displayed_ppu_sample_frame': displayed['sample_frame'],
               'errors': errors, 'cached_source_codes': codes,
               'actual_lcd_pixels_and_hardware_attributes_exact': not errors}
        self.victories.append(row)
        self.capture('victory_' + str(enemy) + '_actual_lcd')
        print('victory_glyph_check', json.dumps(row), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', type=Path, default=ROOT / 'pokecrystal.gbc')
    parser.add_argument('--sym', type=Path, default=ROOT / 'pokecrystal.sym')
    parser.add_argument('--output', type=Path, default=ROOT / 'references/generated/battle_names_v0213/final')
    parser.add_argument('--expect-broken', action='store_true')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'rom_sha256': hashlib.sha256(args.rom.read_bytes()).hexdigest(),
              'ordinary_buttons_only': True, 'ram_edits': False, 'emulator_states_loaded': False,
              'user_batteries_opened': False, 'status': 'RUNNING'}
    with tempfile.TemporaryDirectory(prefix='peon-battle-names-') as temp:
        rom = Path(temp) / 'names.gbc'; shutil.copyfile(args.rom, rom)
        s = BattleNamesSession(rom, symbols(args.sym), args.output)
        try:
            s.fresh_class(); original_name = s.read('wPlayerName', 11)
            s.talk_plain((10, 10), 'up'); s.navigate((18, 13))
            s.press('up', 30); s.press('a', 120)
            assert s.fight('boar', 'EVENT_PEON_QUEST_DONE')['outcome'] == 0
            s.talk_plain((10, 10), 'up'); s.rest()
            route = s.path((17, 15))
            for key in route[:-1]: s.walk(key)
            s.press(route[-1], 60)
            assert s.fight('scorpid', 'EVENT_PEON_SCORPID_DEFEATED')['outcome'] == 0
            assert s.read('wPlayerName', 11) == original_name
            assert {row['enemy_species'] for row in s.victories} == {19, 27}, s.victories
            assert any(row['turn'] == 0 and row['move'] == 84 for row in s.moves)
            errors = [error for row in s.victories for error in row['errors']]
            if args.expect_broken:
                assert errors, 'Baseline did not reproduce the name glyph regression'
                report['status'] = 'EXPECTED_REGRESSION_REPRODUCED'
            else:
                assert not errors, errors
                assert all(row['checked_glyphs']['regular'] >= 10 and row['checked_glyphs']['bold'] >= 4
                           for row in s.victories), s.victories
                report['status'] = 'PASS'
            report['player_name_record_unchanged'] = True
        except Exception as error:
            report['failure'] = repr(error); s.capture('failure'); raise
        finally:
            report['victory_glyph_checks'] = s.victories
            report['observed_moves'] = s.moves
            (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
            s.p.stop(save=False)
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
