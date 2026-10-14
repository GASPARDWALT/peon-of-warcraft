#!/usr/bin/env python3
"""Native roster/PP and rock evolution checks using ordinary controls only.

The product run starts a real Warlock and uses his stored Imp. Optional evolution
runs use a separately compiled PEON_ROSTER_TEST_FIXTURE ROM, with native new-game
party records one XP below levels 8/12. Experience, replacement prompts, native
evolution, nicknames, menus and fights still execute normal ROM code. No emulator
RAM/ROM writes, CPU substitutions, state restore or user battery access is used.
"""
import argparse
import hashlib
import json
import logging
from pathlib import Path
import shutil
import tempfile

from PIL import Image
from validate_peon_earth_stone_v0212 import EarthSession
from validate_peon_warlock_pet import PetSession
from validate_peon_exit_title import symbols
from validate_peon_deep_ui import text_encoding

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RosterSession(EarthSession):
    def __init__(self, rom, sym, index, output, fixture=False):
        self.fixture = fixture
        self.evolutions = []
        self.evolution_recording = False
        self.evolution_frames = []
        self.learn_calls = 0
        self.native_pp = []
        self.observer_errors = []
        self.actual_moves = []
        self.latest_pp = None
        super().__init__(rom, sym, index, output)

    def open(self):
        # Reuse normal map routing and intro observers, but avoid old Earth
        # UI/capture expectations that predate START -> ROSTER directly.
        PetSession.open(self)
        for label, phase in (
            ('HandleMapTimeAndJoypad', 'world'),
            ('PeonTitleScreen.wait', 'title'),
            ('PeonCharacterSelect.input', 'select'),
            ('StartMenu.loop', 'start'),
            ('PeonTeamPickV029.input', 'roster'),
            ('PeonTeamMemberActionsV0213.details_input', 'rock_summary'),
            ('StatsScreen_GetJoypad', 'native_stats'),
            ('MoveScreenLoop.joy_loop', 'native_moves'),
            ('PeonCharacterSheet', 'hero_summary'),
        ):
            self.p.hook_register(*self.sym[label],
                lambda value: setattr(self, 'presentation', value), phase)
        self.p.hook_register(*self.sym['EvolutionAnimation'], self.evolving, None)
        self.p.hook_register(*self.sym['EvolveAfterBattle_MasterLoop.ReturnToMap'],
                             lambda _: setattr(self, 'evolution_recording', False), None)
        self.p.hook_register(*self.sym['BattleCommand_DoTurn.player'], self.observe_pp_paid, None)
        self.p.hook_register(*self.sym['LearnMove'],
            lambda _: setattr(self, 'learn_calls', self.learn_calls + 1), None)

    def evolving(self, _):
        self.evolution_recording = True
        self.evolutions.append({
            'frame': self.p.frame_count,
            'old_species': self.read('wEvolutionOldSpecies')[0],
            'new_species': self.read('wEvolutionNewSpecies')[0],
            'native_level': self.read('wCurPartyLevel')[0],
        })
        self.capture('native_evolution_begins')

    def observe_move(self, _):
        super().observe_move(_)
        if not self.read('hBattleTurn')[0] and self.read('wCurBattleMon') == [1]:
            self.actual_moves.append(self.read('wCurPlayerMove')[0])

    def observe_pp_paid(self, _):
        # Crystal prints UsedMoveText before DoTurn consumes PP. This native
        # player-record branch occurs after battle PP was actually decremented.
        if self.read('hBattleTurn')[0] or self.read('wCurBattleMon') != [1]:
            return
        move = self.read('wCurPlayerMove')[0]
        pp = self.read('wBattleMonPP', 4)
        if self.latest_pp is not None:
            slots = self.read('wBattleMonMoves', 4)
            index = slots.index(move)
            expected = list(self.latest_pp)
            expected[index] = (expected[index] & 0xc0) | ((expected[index] & 0x3f) - 1)
            if pp != expected:
                self.observer_errors.append({'move': move, 'before': self.latest_pp,
                                             'after': pp, 'expected': expected})
            self.native_pp.append({'move': move, 'before': self.latest_pp,
                                   'after': pp, 'exact_one_native_PP_spent': pp == expected})
        self.latest_pp = list(pp)

    def press(self, key, frames=90):
        # Native Start-menu input samples on an eight-frame text cadence.
        # A twelve-frame real held press reliably crosses that input window.
        held = 12 if key in ('a', 'b') and self.presentation == 'start' and not self.read('wBattleMode')[0] else 4
        self.p.button(key, delay=held)
        for offset in range(0, frames, 6):
            self.p.tick(min(6, frames - offset), True)
            if self.evolution_recording and len(self.evolution_frames) < 600:
                self.evolution_frames.append(self.p.screen.image.copy())
        if not self.read('wBattleMode')[0] and self.phase in ('battle', 'battle_drawing', 'using_item'):
            self.phase, self.context = 'overworld', None

    def capture(self, label):
        self.p.screen.image.save(self.folder / (label + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(
            self.folder / (label + '_4x.png'))
        print(label, self.map(), self.position(), self.presentation, flush=True)

    def fresh_class(self):
        # The fixture supplies a real second party record to both test classes.
        self.p.tick(240, True)
        self.press('start'); self.press('down'); self.press('a')
        chosen = False
        for _ in range(220):
            if self.map() == 14 and self.read('wScriptMode') == [0]:
                break
            if self.class_ready and not chosen:
                self.p.tick(60, True)
                for _ in range(self.class_index):
                    self.press('down', 40)
                assert self.read('wMenuCursorY') == [self.class_index]
                self.press('a', 90)
                chosen = True
            if self.naming and not self.naming_done:
                self.p.tick(120, True)
                for index in range(5):
                    self.press('a', 35)
                    if index < 4:
                        self.press('right', 35)
                self.press('start', 40); self.press('a')
                self.naming_done = True
            self.press('a')
        assert chosen and self.naming_done and self.map() == 14
        assert self.read('wScriptMode') == [0] and self.read('wPartyCount') == [2]
        assert self.read('wPartyMon1Species') == [66]
        if self.fixture:
            expected = (95, 7, 511) if self.class_index == 0 else (75, 11, 1727)
            actual = (self.read('wPartyMon2Species')[0], self.read('wPartyMon2Level')[0],
                      int.from_bytes(bytes(self.read('wPartyMon2Exp', 3)), 'big'))
            assert actual == expected, ('Native compiled fixture setup', actual, expected)
        else:
            assert self.read('wPartyMon2Species') == [74]
        assert self.item_quantity(0x94) == 0, 'Retired totem is still granted to new characters'

    def open_roster(self, member=0):
        self.press('start')
        self.wait_for(lambda: self.presentation == 'start')
        for _ in range(10):
            cursor = self.read('wMenuCursorPosition')[0]
            if cursor == 1:
                break
            self.press('up' if cursor > 1 else 'down', 30)
        self.press('a')
        self.wait_for(lambda: self.presentation == 'roster')
        for _ in range(4):
            cursor = self.read('wPeonTeamCursorV029')[0]
            if cursor == member:
                break
            self.press('up' if cursor > member else 'down', 30)
        assert self.read('wPeonTeamCursorV029') == [member]
        self.capture('roster_member_' + str(member))

    def member_action(self, choice):
        self.press('a', 60)
        for _ in range(7):
            cursor = self.read('wMenuCursorY')[0]
            if cursor == choice:
                break
            self.press('up' if cursor > choice else 'down', 30)
        assert self.read('wMenuCursorY') == [choice]
        self.press('a', 90)

    def close_roster(self):
        for _ in range(8):
            if self.presentation == 'world' and self.read('wScriptMode') == [0]:
                return
            self.press('b', 90)
        raise AssertionError(('Roster did not return to the actual world', self.presentation))

    def inspect_roster(self):
        party_before = self.read('wPartyMon1', 96)
        names_before = self.read('wPartyMonNicknames', 22)
        flags_before = self.read('wEventFlags', 256)
        self.open_roster(0)
        self.member_action(1)
        self.wait_for(lambda: self.presentation == 'hero_summary')
        self.capture('hero_class_and_gear_from_member_summary')
        self.press('b')
        self.wait_for(lambda: self.presentation == 'roster')
        self.press('down', 30)
        self.member_action(1)
        if self.fixture:
            self.wait_for(lambda: self.presentation == 'rock_summary')
            self.capture('rock_full_species_summary')
            self.press('a')
        self.wait_for(lambda: self.presentation == 'native_stats')
        self.capture('companion_native_stats')
        self.press('b')
        self.wait_for(lambda: self.presentation == 'roster')
        self.member_action(2)
        self.wait_for(lambda: self.presentation == 'native_moves')
        self.capture('companion_native_four_move_PP_management')
        self.press('b')
        self.wait_for(lambda: self.presentation == 'roster')
        assert self.read('wPartyMon1', 96) == party_before, 'Viewing menus changed native records'
        assert self.read('wPartyMonNicknames', 22) == names_before
        assert self.read('wEventFlags', 256) == flags_before
        self.member_action(3)
        self.wait_for(lambda: self.presentation == 'roster')
        assert self.read('wPeonTeamPreferredV029') == [1]
        self.capture('companion_selected_as_native_lead')
        self.close_roster()
        return {'start_opens_roster_directly': True, 'hero_class_and_gear_accessible': True,
                'native_companion_stats_and_moves_opened': True,
                'viewing_menus_preserves_native_records_and_nicknames': True,
                'one_native_preferred_lead_selected': True}

    def ordinary_battle(self):
        self.talk_at((10, 10), 'up', 'gornek_normal_first_quest')
        assert self.event('EVENT_PEON_QUEST_ACCEPTED')
        self.navigate((18, 13)); self.press('up', 30); self.press('a', 60)
        self.wait_for(lambda: self.phase == 'battle' and self.read('wBattleMode')[0], True)
        assert self.read('wCurBattleMon') == [1], 'Selected companion did not start alone'
        assert self.read('wPeonEarthTotemActive') == [0], 'A retired totem activated during battle'
        self.latest_pp = self.read('wBattleMonPP', 4)
        self.capture('one_native_active_companion')
        handled = self.move_menus
        for _ in range(300):
            if self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]:
                self.p.tick(60, True)
                break
            if self.move_menus > handled:
                handled = self.move_menus
                moves = self.read('wBattleMonMoves', 4)
                target = moves.index(9) if 9 in moves else moves.index(53) if 53 in moves else 0
                for _ in range(5):
                    current = self.read('wCurMoveNum')[0]
                    if current == target:
                        break
                    self.press('up' if current > target else 'down', 30)
                self.press('a', 120)
            elif self.phase == 'battle':
                for _ in range(5):
                    x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
                    if (x, y) == (1, 1):
                        break
                    self.press('left' if x > 1 else 'up', 30)
                self.press('a', 60)
            else:
                # Native EXP, stats, four-slot forgetting prompts and the
                # evolution animation are advanced using ordinary A buttons.
                self.press('a', 60)
        else:
            raise AssertionError(('Native fight/evolution exceeded bounded inputs', self.phase))
        assert self.read('wBattleResult') == [0] and self.event('EVENT_PEON_QUEST_DONE')
        assert self.actual_moves and self.native_pp and not self.observer_errors, self.observer_errors
        assert not self.pet_rounds and not self.pet_errors, 'An automatic second ally turn fired'
        self.capture('native_companion_victory')
        return {'normal_enemy_defeated': True, 'actual_companion_attack_ids': self.actual_moves,
                'normal_PP_records': self.native_pp, 'automatic_pet_actions': 0,
                'persistent_totem_objects': 0}


def run(rom_source, sym_source, index, output, fixture=False):
    with tempfile.TemporaryDirectory(prefix='peon-roster-v0213-') as folder:
        rom = Path(folder) / 'private.gbc'
        shutil.copyfile(rom_source, rom)
        s = RosterSession(rom, symbols(sym_source), index, output, fixture)
        try:
            s.fresh_class()
            before_name = s.read('wPartyMonNicknames', 22)[11:22]
            result = {'rom_sha256': sha(rom_source), 'compiled_evolution_fixture': fixture,
                      'ordinary_controls_only': True, 'emulator_memory_writes': False,
                      'state_restores': False, 'user_batteries_opened': False,
                      'menus': s.inspect_roster(), 'battle': s.ordinary_battle()}
            assert s.read('wPartyMonNicknames', 22)[11:22] == before_name
            if fixture:
                expected = (75, 8) if index == 0 else (76, 12)
                actual = (s.read('wPartyMon2Species')[0], s.read('wPartyMon2Level')[0])
                assert actual == expected, ('Native evolution result', actual, expected, s.evolutions)
                assert len(s.evolutions) == 1 and s.learn_calls >= 1
                assert s.read('wPartyMon1Species') == [66], 'Evolution changed the fixed hero'
                result['native_evolution'] = s.evolutions[0]
                assert s.evolution_frames, 'Native evolution had no observed framebuffer samples'
                s.evolution_frames[0].save(s.folder / 'native_evolution.gif', save_all=True,
                    append_images=s.evolution_frames[1:], duration=100, loop=0)
                result['native_evolution_framebuffer_samples'] = len(s.evolution_frames)
                result['native_four_move_learning_calls'] = s.learn_calls
                result['custom_DOUOLL_nickname_preserved'] = True
            result['nickname_preserved'] = True
            result['quest_flags_unchanged_by_menu_views'] = True
            result['status'] = 'PASS'
            return result
        finally:
            s.p.stop(save=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', type=Path, default=ROOT / 'pokecrystal.gbc')
    parser.add_argument('--sym', type=Path, default=ROOT / 'pokecrystal.sym')
    parser.add_argument('--fixture-rom', type=Path)
    parser.add_argument('--fixture-sym', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'references/generated/roster_v0213')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    args.output.mkdir(parents=True, exist_ok=True)
    assert 'PeonRosterTestSetupV0213' not in symbols(args.sym), 'Product ROM contains compiled QA fixture'
    report = {'product_ROM_fixture_free': True, 'normal': run(args.rom, args.sym, 2, args.output / 'normal'),
              'evolution': {}, 'status': 'PARTIAL'}
    if args.fixture_rom:
        assert args.fixture_sym and 'PeonRosterTestSetupV0213' in symbols(args.fixture_sym)
        for index, label in ((0, 'level7_to8'), (1, 'level11_to12')):
            report['evolution'][label] = run(args.fixture_rom, args.fixture_sym, index,
                                            args.output / label, fixture=True)
        report['status'] = 'PASS'
    else:
        report['unrun'] = ['native_7_to8_and_11_to12_evolution_requires_separate_compiled_fixture_ROM']
    (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
