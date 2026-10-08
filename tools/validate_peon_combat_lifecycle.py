#!/usr/bin/env python3
"""Native battle exit regression, with explicitly labelled diagnostic branches.

The first victory starts a fresh character and places the real inventory totem
using ordinary buttons. Flee/defeat/fallback branches rewind that battle menu
and use temporary, declared RAM fixtures; no user battery save is opened. Hooks
only observe execution, except the labelled non-Peon fallback tileset fixture.
"""
import argparse
import hashlib
import io
import json
import logging
import shutil
import tempfile
from pathlib import Path

from PIL import Image

from validate_peon_battle_totems import BagSession, TOTEM
from validate_peon_villages import load_symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/deep_polish/combat/lifecycle'
TRANSIENTS = ('wPeonRockbiterCharge', 'wPeonLightningShieldCharges',
              'wPeonEarthTotemActive', 'wPeonPlayerPoseActive')


def symbols_from(path):
    symbols = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) == 2 and ':' in fields[0]:
            symbols[fields[1]] = tuple(int(x, 16) for x in fields[0].split(':'))
    return symbols


class LifecycleSession(BagSession):
    def __init__(self, rom, symbols):
        self.calls = {'evolution': 0, 'pokerus_and_berries': 0, 'cleanup': 0}
        self.cleanup_entries = []
        self.cleanup_finished_states = []
        self.errors = []
        self.fallback = False
        self.fallback_tileset = None
        super().__init__(rom, symbols)

    def open(self):
        super().open()
        def safe(label, callback):
            def observe(_):
                try:
                    callback()
                except Exception as error:
                    self.errors.append({'hook': label, 'error': repr(error)})
            self.p.hook_register(*self.sym[label], observe, None)
        safe('EvolveAfterBattle', lambda: self.count('evolution'))
        safe('GivePokerusAndConvertBerries', lambda: self.count('pokerus_and_berries'))
        safe('CleanUpBattleRAM', self.cleanup)
        safe('ExitBattle.not_linked', self.set_fallback)
        bank, address = self.sym['CleanUpBattleRAM.loop']
        offset = bank * 0x4000 + address - 0x4000
        wait_address = self.sym['WaitSFX'][1]
        opcode = bytes((0xcd, wait_address & 255, wait_address >> 8))
        position = self.rom.read_bytes()[offset:offset + 40].index(opcode)
        cleanup_return = address + position + 3
        def finished():
            sp = self.p.register_file.SP
            caller = self.p.memory[sp] | self.p.memory[sp + 1] << 8
            if caller == cleanup_return:
                self.cleanup_finished_states.append(self.transients())
        safe('WaitSFX', finished)

    def count(self, label):
        self.calls[label] += 1

    def transients(self):
        return {label: self.read(label)[0] for label in TRANSIENTS}

    def cleanup(self):
        self.calls['cleanup'] += 1
        self.cleanup_entries.append(self.transients())
        if self.fallback_tileset is not None:
            self.write('wMapTileset', [self.fallback_tileset])
            self.fallback_tileset = None

    def set_fallback(self):
        if self.fallback:
            self.fallback_tileset = self.read('wMapTileset')[0]
            self.write('wMapTileset', [1])

    def capture(self, label):
        self.p.screen.image.save(OUT / (label + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(
            OUT / (label + '_4x.png'))

    def until_world(self, choose_bolt=True):
        entered = bool(self.read('wBattleMode')[0])
        menus = self.move_menus
        for _ in range(240):
            entered |= bool(self.read('wBattleMode')[0])
            if entered and self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]:
                self.p.tick(60, True)
                assert not self.errors, self.errors
                return
            if self.move_menus > menus:
                menus = self.move_menus
                moves = self.read('wBattleMonMoves', 4)
                target = moves.index(84) if choose_bolt and 84 in moves else 0
                for _ in range(5):
                    current = self.read('wCurMoveNum')[0]
                    if current == target:
                        break
                    self.press('up' if current > target else 'down', 30)
                self.press('a', 120)
            elif self.phase == 'battle':
                for _ in range(4):
                    x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
                    if (x, y) == (1, 1):
                        break
                    self.press('left' if x > 1 else 'up', 30)
                self.press('a', 60)
            else:
                self.press('a', 60)
        self.capture('unexpected_lifecycle_state')
        raise AssertionError(('Battle exit timed out', self.phase,
                              hex(self.p.register_file.PC), self.read('wBattleResult')))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', type=Path, default=ROOT / 'pokecrystal.gbc')
    parser.add_argument('--sym', type=Path, default=ROOT / 'pokecrystal.sym')
    parser.add_argument('--historical', action='store_true')
    args = parser.parse_args()
    global OUT
    OUT = OUT / ('historical_1435e70' if args.historical else 'candidate')
    OUT.mkdir(parents=True, exist_ok=True)
    logging.disable(logging.CRITICAL)
    report = {'rom_sha256': hashlib.sha256(args.rom.read_bytes()).hexdigest(),
              'historical_baseline': args.historical,
              'method': 'Fresh normal-button totem victory; independently labelled temporary flee/defeat/fallback fixtures.',
              'user_battery_saves_opened': False, 'cases': {}, 'all_checks_passed': False}
    session = None
    with tempfile.TemporaryDirectory(prefix='peon-combat-lifecycle-') as directory:
        rom = Path(directory) / 'lifecycle.gbc'
        shutil.copyfile(args.rom, rom)
        session = LifecycleSession(rom, symbols_from(args.sym))
        try:
            session.fresh()
            session.talk((10, 10), 'up', 'first_quest')
            session.navigate((18, 13)); session.press('up', 30); session.press('a', 60)
            session.wait(lambda: session.phase == 'battle', buttons=True)
            session.watch = True
            baseline = io.BytesIO(); session.p.save_state(baseline)

            def rewind():
                baseline.seek(0); session.p.load_state(baseline)
                session.phase, session.context = 'battle', 'battle'
                session.fallback = False; session.fallback_tileset = None
                session.calls = dict(evolution=0, pokerus_and_berries=0, cleanup=0)
                session.cleanup_entries = []; session.errors = []
                session.cleanup_finished_states = []
                for button in ('a', 'b', 'up', 'down', 'left', 'right', 'start', 'select'):
                    session.p.button_release(button)
                session.p.tick(20, True)

            def record(label, expected_result, diagnostic):
                assert session.read('wBattleResult')[0] & 0x3f == expected_result
                after = session.transients()
                result = {'battle_result': expected_result, 'calls': session.calls.copy(),
                          'cleanup_input_states': session.cleanup_entries.copy(),
                          'cleanup_finished_states': session.cleanup_finished_states.copy(),
                          'world_reused_union_bytes': after, 'map': session.map(),
                          'hp': session.word('wPartyMon1HP'), 'totem_quantity': session.item_quantity(TOTEM),
                          'diagnostic_fixtures': diagnostic}
                assert session.calls['cleanup'] == 1
                assert len(session.cleanup_finished_states) == 1
                assert session.item_quantity(TOTEM) == 1
                if not args.historical:
                    cleared = session.cleanup_finished_states[0]
                    assert all(value == 0 for value in cleared.values()), (label, cleared)
                    expected_legacy = int(label == 'non_peon_original_fallback')
                    assert session.calls['evolution'] == expected_legacy
                    assert session.calls['pokerus_and_berries'] == expected_legacy
                session.capture(label)
                report['cases'][label] = result

            rewind()
            placement = session.use_item(TOTEM, True)
            assert placement['after']['active'] == 1
            assert placement['enemy_move_count'] == 1
            session.until_world()
            assert session.event('EVENT_PEON_QUEST_DONE')
            record('normal_button_totem_victory', 0, [])

            rewind()
            for label, value in zip(TRANSIENTS, (1, 3, 1, 1)):
                session.write(label, [value])
            for _ in range(4):
                x, y = session.read('wMenuCursorX')[0], session.read('wMenuCursorY')[0]
                if (x, y) == (2, 2):
                    break
                session.press('right' if x < 2 else 'down', 30)
            assert (session.read('wMenuCursorX')[0], session.read('wMenuCursorY')[0]) == (2, 2)
            session.press('a', 90); session.until_world()
            assert not session.event('EVENT_PEON_QUEST_DONE')
            record('diagnostic_flee', 2, ['Four existing battle-only fields set 1/3/1/1 before native Run action.'])

            rewind()
            for label, value in zip(TRANSIENTS, (1, 3, 1, 1)):
                session.write(label, [value])
            session.write('wBattleMonHP', [0, 1]); session.write('wPartyMon1HP', [0, 1])
            session.write('wEnemyMonHP', [0, 240]); session.write('wEnemyMonMaxHP', [0, 240])
            session.write('wBattleMonSpeed', [0, 1]); session.write('wEnemyMonSpeed', [3, 231])
            session.write('wEnemyMonAttack', [3, 231]); session.write('wEnemyMonMoves', [33, 0, 0, 0])
            session.write('wEnemyMonPP', [35, 0, 0, 0]); session.until_world()
            assert session.map() == 23 and session.word('wPartyMon1HP') == 1
            assert not session.event('EVENT_PEON_QUEST_DONE')
            assert session.read('wPartyMon1Status') == [0]
            record('diagnostic_defeat_recovery', 1, ['Battle-only fields 1/3/1/1; player HP1; foe HP240/attack999/speed999/Tackle to reliably exercise native loss.'])

            rewind()
            session.fallback = True
            session.until_world()
            record('non_peon_original_fallback', 0, ['Only at post-battle entry, tileset temporarily1; restored at cleanup before returning to world.'])
            assert session.calls['evolution'] == session.calls['pokerus_and_berries'] == 1
            report['normal_victory_mob_disappears'] = True
            report['flee_and_defeat_do_not_retire_enemy'] = True
            report['native_non_peon_fallback_preserved'] = True
            report['all_checks_passed'] = True
        except Exception as error:
            report['failure'] = repr(error)
            if session is not None:
                session.capture('unexpected_state')
            raise
        finally:
            if session is not None:
                session.p.stop(save=False)
            (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
