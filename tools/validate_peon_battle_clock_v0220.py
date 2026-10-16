#!/usr/bin/env python3
"""Bounded ordinary-control battle smoke for v20's global CGB double speed.

Start a fresh private Shaman, walk at least 120 ordinary safe world tiles,
then execute actual MACE STRIKE and Lightning Bolt in
its normal Boar encounter, observe real resource payment, horizontal spell
OAM/VRAM/LCD pixels and completed victory-name glyphs. Hooks are read-only.
No ROM/RAM edits, CPU substitutions, save states or user batteries are used.
This does not claim physical cartridge testing or replace the audio/FPS test.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import logging
import re
import signal
import traceback
from pathlib import Path
import shutil
import tempfile

from validate_peon_lightning_horizontal_v0213 import HorizontalSession, digest
from validate_peon_resource_hud_v0213 import ResourceHUDSession
from validate_peon_battle_names_v0213 import BattleNamesSession
from validate_peon_exit_title import symbols
from validate_peon_earth_stone_v0212 import EarthSession
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def frozen_horizontal_observer():
    # Reconstruct only observer metadata from checked-in native inputs. The
    # retired v13 report JSON is not a build or validation dependency.
    folder = 'gfx/peon_lightning_horizontal_v0213/'
    source = (ROOT / 'gfx/peon_lightning_horizontal_v0213.asm').read_text()
    packet = {'ability': 'lightning_bolt', '2bpp': folder + 'lightning_tiles.2bpp',
              'palette_file': folder + 'lightning_obj.gbcpal', 'assets': []}
    for role, suffix, orientation in (('player', 'Player', 'player_back'),
                                      ('enemy', 'Enemy', 'enemy_front'),
                                      ('impact', 'Impact', 'target')):
        label = 'PeonSpellV1Lightning' + suffix + 'OAM'
        body = source.split(label + '::', 1)[1].split('assert @', 1)[0]
        width, height = Image.open(ROOT / (folder + role + '_source_rotated.png')).size
        tiles = []
        for line in body.splitlines():
            if not line.strip().startswith('dbsprite '):
                continue
            values = [int(value.strip()[1:], 16) if value.strip().startswith('$')
                      else int(value.strip()) for value in line.strip()[9:].split(',')]
            x, y, dx, dy, tile, attrs = values
            assert dx == dy == 0
            tiles.append({'x': x * 8 + width // 2, 'y': y * 8 + height // 2,
                          'tile_index': tile})
        count = int(re.search(r'DEF ' + label + r'Count EQU (\d+)', source)[1])
        assert count == len(tiles)
        packet['assets'].append({'oam_label': label, 'oam_count': count,
                                 'canvas': [width, height], 'tile_offset_records': tiles,
                                 'source': folder + role + '_source_rotated.png',
                                 'source_sha256': digest(ROOT / (folder + role + '_source_rotated.png')),
                                 'orientation': orientation})
    return {'packets': [packet]}, {'native_asm_sha256': digest(ROOT / 'gfx/peon_lightning_horizontal_v0213.asm')}


class BattleClockSession(HorizontalSession):
    # This existing driver observes native input acknowledgement before
    # releasing an actual button. It performs no emulator-memory writes.
    press = ResourceHUDSession.press
    metadata = ResourceHUDSession.metadata
    battle_bar = ResourceHUDSession.battle_bar
    ppu_snapshot = BattleNamesSession.ppu_snapshot
    check_victory = BattleNamesSession.check_victory

    def __init__(self, rom, sym, folder):
        self.class_selection_started = False
        self.forced_switches = []
        self.payments = []
        self.pending_payment = None
        self.victory_active = False
        self.pending = None
        self.pending_ppu = []
        self.victories = []
        self.frame = 0
        self.battle_clock_samples = {}
        self.result = {}
        self.cpu_checkpoint_serial = 0
        self.unexpected_boot_entries = []
        self.fresh_complete = False
        self.walk_watch = False
        self.walk_steps = []
        self.walk_last_position = None
        self.walk_script_modes = {}
        # Initialize the inherited spell observer using native source metadata
        # rather than its historical untracked import-report dependency.
        self.frames = 0
        self.records, self.observations, self.snapshots = [], {}, []
        self.turn_observations = {0: {}, 1: {}}
        self.watch = False
        self.max_oam = self.max_scanline = self.observed_oam_frames = 0
        self.moves, self.pose_uploads = [], []
        self.manifest, self.import_data = frozen_horizontal_observer()
        self.packets, self.assets = {}, {}
        for packet in self.manifest['packets']:
            packet['_raw'] = (ROOT / packet['2bpp']).read_bytes()
            packet['_pal'] = (ROOT / packet['palette_file']).read_bytes()
            self.packets[packet['ability']] = packet
            for asset in packet['assets']:
                asset['_packet'] = packet
                self.assets[sym[asset['oam_label']][1]] = asset
        self.position_log = {0: [], 1: []}
        self.hook_errors = []
        self.data = Path(rom).read_bytes()
        EarthSession.__init__(self, rom, sym, 0, folder)
        del self.rom_bytes

    def open(self):
        super().open()

        def guarded(label, callback):
            def observe(_):
                try:
                    callback()
                except Exception as error:
                    self.hook_errors.append({'hook': label, 'error': repr(error)})
            self.p.hook_register(*self.sym[label], observe, None)

        def class_release():
            self.class_selection_started = True
            self.class_ready = False
            for key in ('a', 'b', 'start'):
                self.p.button_release(key)

        guarded('PeonClassSelect.release', class_release)
        guarded('BattleTextbox', lambda: BattleNamesSession.begin_text(self))
        guarded('PromptButton', lambda: BattleNamesSession.text_finished(self))
        guarded('PeonSpendBattleResourceInternalV029', self.payment_enter)
        guarded('_Start', self.boot_enter)
        bank, address = self.sym['PeonSpendBattleResourceV029.body']
        target = self.sym['PeonSpendBattleResourceInternalV029'][1]
        offset = bank * 0x4000 + address - 0x4000
        # Observe the actual LD B,A after the existing CALL returns, never a
        # fabricated "payment done" point or a CPU/register substitution.
        assert self.data[offset:offset + 3] == bytes((0xcd, target & 255, target >> 8))
        self.p.hook_register(bank, address + 3, lambda _: self.payment_leave(), None)

    def boot_enter(self):
        if not self.fresh_complete:
            return
        state=self.cpu_state();sp=self.p.register_file.SP
        state['actual_stack_32_bytes']=list(self.p.memory[sp:min(0x10000,sp+32)])
        self.unexpected_boot_entries.append(state)
        (self.folder / 'unexpected_boot_entry.json').write_text(json.dumps(state,indent=2)+'\n')
        self.p.screen.image.save(self.folder/'unexpected_boot_actual_lcd.png')
        print('unexpected_native_boot_reentry',json.dumps(state),flush=True)

    def cpu_state(self):
        state = {'frames': self.frames, 'PC': hex(self.p.register_file.PC),
                 'SP': hex(self.p.register_file.SP), 'map': self.map(),
                 'position': self.position(), 'phase': self.phase,
                 'LCDC': int(self.p.memory[0xff40]), 'STAT': int(self.p.memory[0xff41]),
                 'KEY1': int(self.p.memory[0xff4d]), 'IE': int(self.p.memory[0xffff]),
                 'IF': int(self.p.memory[0xff0f])}
        for label in ('hROMBank', 'hDMATransfer', 'hOAMUpdate', 'hVBlank', 'hVBlankCounter', 'wScriptMode'):
            if label in self.sym:
                state[label] = self.read(label)[0]
        return state

    def cpu_checkpoint(self):
        self.cpu_checkpoint_serial += 1
        if self.cpu_checkpoint_serial % 120 == 0:
            (self.folder / 'latest_native_cpu_checkpoint.json').write_text(
                json.dumps(self.cpu_state(), indent=2) + '\n')

    def diagnose_signal(self, _signal, frame):
        # Host diagnostic signal only reads the private emulator. It never
        # changes emulated registers, memory, execution PC or game input.
        state = self.cpu_state()
        print('battle_smoke_signal_diagnostic', json.dumps(state), flush=True)
        traceback.print_stack(frame)
        (self.folder / 'signal_cpu_diagnostic.json').write_text(json.dumps(state, indent=2) + '\n')
        self.p.screen.image.save(self.folder / 'signal_actual_lcd.png')

    def payment_enter(self):
        if self.read('hBattleTurn')[0]:
            return
        move = self.read('wCurPlayerMove')[0]
        if move not in (1, 84):
            return
        self.pending_payment = {
            'move': move, 'frame': self.frames,
            'mana_before': self.metadata()['current'],
            'party_PP_before': self.read('wPartyMon1PP', 4),
            'battle_PP_before': self.read('wBattleMonPP', 4),
        }

    def payment_leave(self):
        if self.read('hBattleTurn')[0] or self.pending_payment is None:
            return
        row, self.pending_payment = self.pending_payment, None
        row.update(mana_after=self.metadata()['current'],
                   native_cost=self.read('wPeonResourceCostV029')[0],
                   party_PP_after=self.read('wPartyMon1PP', 4),
                   battle_PP_after=self.read('wBattleMonPP', 4),
                   after_frame=self.frames)
        expected = 0 if row['move'] == 1 else 15
        try:
            assert row['native_cost'] == expected, row
            assert row['mana_before'] - row['mana_after'] == expected, row
            assert row['party_PP_before'] == row['party_PP_after'], row
            assert row['battle_PP_before'] == row['battle_PP_after'], row
            row.update(status='PASS', actual_native_resource_payment_exact=True)
            self.payments.append(row)
        except Exception as error:
            self.hook_errors.append({'hook': 'resource payment return', 'error': repr(error)})

    def after_frame(self):
        super().after_frame()
        self.frame = self.frames
        assert not self.unexpected_boot_entries, ('Unexpected actual native Start after class selection',self.unexpected_boot_entries)
        self.cpu_checkpoint()
        if self.walk_watch:
            current = self.position()
            assert self.map() == 14 and not self.read('wBattleMode')[0]
            # Changing facing is itself a native script event. It can be
            # sampled in SCRIPT_READ/WAIT_MOVEMENT between ordinary steps;
            # absence of a script on every LCD frame is not a game invariant.
            mode = self.read('wScriptMode')[0]
            self.walk_script_modes[mode] = self.walk_script_modes.get(mode, 0) + 1
            assert not self.event('EVENT_PEON_QUEST_ACCEPTED')
            if current != self.walk_last_position:
                before = self.walk_last_position
                assert sum(abs(a-b) for a, b in zip(current, before)) == 1, (before, current)
                self.walk_steps.append({'from': before, 'to': current, 'frame': self.frames})
                self.walk_last_position = current
        if self.frames % 600 == 0:
            print('battle_smoke_progress', self.frames, self.map(), self.position(), self.phase, self.presentation, self.read('wBattleMode'), hex(self.p.register_file.PC), flush=True)
            self.p.screen.image.save(self.folder / 'latest_bounded_progress.png')
        assert self.frames < 30000, ('Long-walk/battle smoke exceeded500seconds of native frames', self.phase, self.map(), self.position(), hex(self.p.register_file.PC))
        if self.read('wBattleMode')[0]:
            value = int(self.p.memory[0xff4d])
            self.battle_clock_samples[value] = self.battle_clock_samples.get(value, 0) + 1
        if self.pending:
            self.pending_ppu.append(self.ppu_snapshot())
            if self.frame >= self.pending[0]:
                _, enemy = self.pending
                self.pending = None
                self.check_victory(enemy)

    def wait_for(self, predicate, buttons=False, limit=120):
        return super().wait_for(predicate, buttons, limit)

    def pose(self, _):
        # Idle restoration may run after wFXAnimID has been cleared. Read the
        # selected native move as well, rather than hiding that real upload.
        if (self.watch and self.read('wCurPlayerMove')[0] == 84
                and self.read('hBattleTurn') == [0]):
            self.pose_uploads.append({'frame': self.frames, 'index': self.p.register_file.C,
                                      'native_FXAnimID': self.read('wFXAnimID', 2)})

    def battle_background_diagnostic(self):
        snapshot = self.ppu_snapshot()
        snapshot['LCD_sha256'] = hashlib.sha256(self.p.screen.image.convert('RGB').tobytes()).hexdigest()
        examples = []
        # White-margin cells must not silently become stale world/actor art.
        for x, y in ((0, 0), (19, 0), (0, 6), (10, 12), (19, 17)):
            index = y*20+x
            tile_id, attrs = snapshot['tiles'][index], snapshot['attrs'][index]
            signed_id = tile_id if tile_id < 128 else tile_id-256
            address = 0x9000+signed_id*16
            examples.append({'cell': [x, y], 'tile': tile_id, 'attr': attrs,
                             'pattern_address': hex(address),
                             'bank0_pattern': bytes(self.p.memory[0, address:address+16]).hex(),
                             'bank1_pattern': bytes(self.p.memory[1, address:address+16]).hex()})
        snapshot['margin_cell_examples'] = examples
        (self.folder/'actual_battle_background_diagnostic.json').write_text(json.dumps(snapshot, indent=2)+'\n')
        frame_index = self.read('wTextboxFrame')[0] & 7
        bank, address = self.sym['Frames']
        offset = bank*0x4000+address-0x4000 if bank else address
        source = self.data[offset+frame_index*48:offset+(frame_index+1)*48]
        border = bytes(channel for byte in source for channel in (byte, byte))
        space = bytes(self.p.memory[0, 0x97f0:0x9800])
        actual_border = bytes(self.p.memory[0, 0x9790:0x97f0])
        assert space == bytes(16), ('Battle space glyph $7f overwritten', space.hex(), examples)
        assert actual_border == border, ('Battle six native textbox-border glyphs overwritten',
                                          actual_border.hex(), border.hex())
        return {'margin_cell_examples': examples,
                'native_bank0_space_glyph_16_zero_bytes_exact': True,
                'native_bank0_six_textbox_border_tiles_exact': True,
                'textbox_frame_index': frame_index}

    def shaman_rear_on_lcd(self):
        # Current class labels link the v16 enlarged complete back picture.
        # The v13 HUD observer hard-codes the retired v14 smaller packet.
        folder = ROOT / 'gfx/combat_heroes_v0216/shaman/back'
        expected = (folder / 'frames.bin').read_bytes()[:576]
        attrs = (folder / 'attrs.bin').read_bytes()
        palette = (folder / 'palettes.bin').read_bytes()
        assert len(expected) == 576 and len(attrs) == 36 and len(palette) == 16
        for _ in range(180):
            base = 0x9c00 if self.p.memory[0xff40] & 8 else 0x9800
            resident = (bytes(self.p.memory[0, 0x9310:0x9550]) == expected
                        and not self.p.memory[0xff42] and not self.p.memory[0xff43]
                        and all(self.p.memory[0, base+(y+6)*32+x+2] == 0x31+x*6+y
                                and self.p.memory[1, base+(y+6)*32+x+2] == attrs[y*6+x]
                                for y in range(6) for x in range(6)))
            if resident:
                live_palettes = bytes(self.read('wBGPals2', 64))
                assert live_palettes[:8] == palette[:8]
                assert live_palettes[48:56] == palette[8:16]
                lcd = self.p.screen.image.convert('RGB')
                match = True
                for tile_index in range(36):
                    tx, ty = divmod(tile_index, 6)
                    attr = attrs[ty*6+tx]
                    raw = live_palettes[(attr & 7)*8:(attr & 7)*8+8]
                    colors = [tuple(int.from_bytes(raw[n:n+2], 'little') >> shift & 31
                                    for shift in (0, 5, 10)) for n in range(0, 8, 2)]
                    for y in range(8):
                        lo, hi = expected[tile_index*16+y*2:tile_index*16+y*2+2]
                        for x in range(8):
                            ink = (lo >> (7-x) & 1) | (hi >> (7-x) & 1) << 1
                            actual = tuple(channel >> 3 for channel in lcd.getpixel((16+tx*8+x, 48+ty*8+y)))
                            if actual != colors[ink]:
                                match = False
                                break
                        if not match:
                            break
                    if not match:
                        break
                if match:
                    return {'source': 'gfx/combat_heroes_v0216/shaman/back/frames.bin',
                            'source_sha256': digest(folder / 'frames.bin'),
                            'native_bank0_576_bytes_exact': True,
                            'displayed_36_column_major_tiles_and_attrs_exact': True,
                            'native_player_palettes_0_and_6_exact': True,
                            'actual_48x48_RGB555_pixels_exact': 2304}
            self.p.tick(1, True)
        raise AssertionError('Complete current v16 Shaman rear did not reach the actual LCD')

    def fresh_class(self):
        self.p.tick(240, True)
        self.press('start')
        self.press('down')
        self.press('a')
        chosen = False
        for _ in range(220):
            if self.map() == 14 and self.read('wScriptMode') == [0]:
                break
            if self.class_ready and not chosen:
                # The hook observes the true class input loop after its
                # illustrated page is complete; no early confirm is sent.
                assert self.read('wMenuCursorY') == [0]
                self.capture('01_shaman_master_native_class_page')
                self.press('a', 90)
                chosen = True
            if self.naming and not self.naming_done:
                self.p.tick(120, True)
                for index in range(5):
                    self.press('a', 35)
                    if index < 4:
                        self.press('right', 35)
                self.press('start', 40)
                self.press('a')
                self.naming_done = True
            self.press('a')
        assert chosen and self.naming_done and self.map() == 14
        assert self.read('wScriptMode') == [0]
        assert self.event('EVENT_PEON_SHAMAN')
        assert self.read('wPartyMon1Species') == [66]
        assert self.read('wPartyMon1Moves', 2) == [1, 84]
        self.capture('02_fresh_shaman_native_world')
        self.fresh_complete = True

    def bounded_long_walk(self):
        # These waypoints remain inside The Den, away from entrances, battle
        # triggers and quest speakers. The inherited native-collision BFS may
        # route around an actual wandering actor; every successful grid step
        # is observed, never forced or teleported.
        self.navigate((12, 9))
        start = self.frames
        self.walk_last_position = self.position()
        self.walk_watch = True
        rounds = 0
        while len(self.walk_steps) < 120 and rounds < 12:
            for point in ((16, 9), (16, 11), (12, 11), (12, 9)):
                self.navigate(point)
            rounds += 1
        self.walk_watch = False
        assert len(self.walk_steps) >= 120, len(self.walk_steps)
        assert not self.unexpected_boot_entries
        assert not self.read('wScriptMode')[0]
        assert int(self.p.memory[0xff4d]) & 0x80
        deltas = {(row['to'][0]-row['from'][0], row['to'][1]-row['from'][1])
                  for row in self.walk_steps}
        assert deltas == {(-1, 0), (1, 0), (0, -1), (0, 1)}, deltas
        self.result['bounded_ordinary_long_walk'] = {
            'status': 'PASS', 'native_grid_steps': len(self.walk_steps),
            'native_LCD_frames': self.frames-start, 'waypoint_rounds': rounds,
            'map': 14, 'all_four_directions': True,
            'no_boot_reentries_battles_or_quest_acceptance': True,
            'native_script_mode_frame_histogram': self.walk_script_modes,
            'steps': self.walk_steps,
        }
        self.capture('03a_actual_120_tile_walk_complete')

    def route(self):
        self.fresh_class()
        self.result['initial_clock_KEY1'] = int(self.p.memory[0xff4d])
        self.result['initial_saved_resource'] = self.metadata()
        self.bounded_long_walk()
        self.talk_at((10, 10), 'up', '03_gornek_boar_offer')
        assert self.event('EVENT_PEON_QUEST_ACCEPTED')
        self.navigate((18, 13))
        self.press('up', 30)
        self.press('a', 60)
        self.wait_for(lambda: self.phase == 'battle' and self.read('wBattleMode')[0], True)
        assert self.read('wEnemyMonSpecies') == [19]
        self.result['initial_battle_HUD'] = self.battle_bar('04_battle_full_rear_and_mana')
        self.result['initial_battle_margin_patterns'] = self.battle_background_diagnostic()
        self.watch = True
        self.cast(0)
        assert any(row['move'] == 1 for row in self.payments), 'No real MACE STRIKE was executed'
        self.capture('05_after_free_mace_strike')
        # Ordinary first encounter normally survives one Mace. A naturally
        # fatal critical is reported honestly rather than replacing its HP.
        assert self.read('wBattleMode')[0], 'A natural first-turn critical ended the Boar before Lightning; no fixture used'
        self.cast(1)
        self.until_world(choose_bolt=True)
        assert self.read('wBattleResult') == [0]
        assert self.event('EVENT_PEON_QUEST_DONE')
        assert any(row['move'] == 84 for row in self.payments)
        assert self.full_direction_seen(0), 'No full visible native horizontal Lightning cast'
        assert self.victories and not any(row['errors'] for row in self.victories)
        assert self.read('wPartyMon1PP', 2) == [35, 30]
        assert self.battle_clock_samples and all(value & 0x80 for value in self.battle_clock_samples)
        assert self.result['initial_clock_KEY1'] & 0x80
        self.result.update(
            native_payments=self.payments,
            victory_name_glyphs=self.victories,
            battle_clock_KEY1_histogram={str(k): v for k, v in self.battle_clock_samples.items()},
            battle_frames_observed=sum(self.battle_clock_samples.values()),
            double_speed_bit_set_for_every_observed_battle_frame=True,
            native_managed_PP_after=self.read('wPartyMon1PP', 4),
            battle_result=self.read('wBattleResult')[0],
            final_party_resource=self.metadata(),
            final_world_clock_KEY1=int(self.p.memory[0xff4d]),
        )
        self.capture('06_actual_battle_complete_world_return')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', required=True, type=Path)
    parser.add_argument('--sym', required=True, type=Path)
    parser.add_argument('--expected-rom-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    args.output.mkdir(parents=True, exist_ok=True)
    assert digest(args.rom) == args.expected_rom_sha256
    report = {
        'status': 'RUNNING', 'version': 'v0.2.20',
        'rom_sha256': digest(args.rom), 'sym_sha256': digest(args.sym),
        'ordinary_controls_only': True, 'RAM_writes': False,
        'ROM_patches': False, 'CPU_substitutions': False,
        'emulator_states_loaded': False, 'user_saves_opened': False,
        'scope': 'Fresh Shaman, at least 120 ordinary safe Den world tiles, one normal Boar battle, free Mace and horizontal Lightning, exact native victory-name glyphs, battle CGB clock.',
        'limitations': ['No physical Chromatic test.', 'Audio and 60-VBlank cadence are checked by the separate performance validator.'],
    }
    session = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-v0220-battle-clock-') as directory:
            private = Path(directory) / 'battle.gbc'
            shutil.copyfile(args.rom, private)
            session = BattleClockSession(private, symbols(args.sym), args.output)
            signal.signal(signal.SIGUSR1, session.diagnose_signal)
            session.route()
            report.update(session.result)
            report.update(session.finish(require_enemy=False))
            assert not session.hook_errors
            assert {0, 1} <= set(report['native_pose_indices']), report['native_pose_indices']
            report.update(status='PASS', all_checks_passed=True)
    except BaseException as error:
        report.update(status='FAIL', error=repr(error))
        if session is not None:
            session.capture('battle_clock_failure')
        raise
    finally:
        if session is not None:
            report.update(session.result)
            report['unexpected_native_boot_reentries'] = session.unexpected_boot_entries
            session.p.stop(save=False)
        (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
