#!/usr/bin/env python3
"""Play the real rock quest, earth attacks and a private v0215 save upgrade.

Only controller inputs change the game. Observers read the native party,
animation VM, VRAM, LCD and hardware OAM. No RAM/ROM patches, save states,
CPU substitutions or personal batteries are used.
"""
import argparse
import copy
import hashlib
import json
import logging
from pathlib import Path
import shutil
import tempfile

from PIL import Image

from peon_ordinary_battle_readiness_v0213 import OrdinaryBattleReadiness
from validate_peon_exit_title import ExitSession, symbols
from validate_peon_resource_hud_v0213 import ResourceHUDSession
from validate_peon_roster_v0213 import RosterSession

ROOT = Path(__file__).resolve().parents[1]
ROCKS = (95, 75, 76)
STARTERS = (33, 189, 88)
ANIMATIONS = {33: 'BattleAnim_Tackle', 189: 'BattleAnim_MudSlap', 88: 'BattleAnim_RockThrow'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rom_bytes(rom, sym, label, count):
    bank, address = sym[label]
    offset = address if not bank else bank * 0x4000 + address - 0x4000
    return rom[offset:offset + count]


def static_contract(rom_path, sym):
    rom = Path(rom_path).read_bytes()
    curricula = {}
    for label, evolution in (('OnixEvosAttacks', (8, 75)),
                              ('GravelerEvosAttacks', (12, 76)),
                              ('GolemEvosAttacks', None)):
        data = rom_bytes(rom, sym, label, 64)
        if evolution:
            assert tuple(data[:4]) == (1, *evolution, 0), (label, list(data[:4]))
            position = 4
        else:
            assert data[0] == 0
            position = 1
        moves = []
        while data[position]:
            moves.append(list(data[position:position + 2]))
            position += 2
        assert moves[:3] == [[1, move] for move in STARTERS], (label, moves)
        assert all(move not in (1, 84, 9) for _, move in moves), (label, moves)
        curricula[label] = {'evolution_level_and_species': evolution, 'native_level_moves': moves}
    move_table = {}
    for move, name, power, kind, pp in ((33, 'STRIKE', 35, 0, 35),
                                       (189, 'MUD-SLAP', 20, 4, 10),
                                       (88, 'ROCK THROW', 50, 5, 15)):
        row = rom_bytes(rom, sym, 'Moves', 7 * move)[7 * (move - 1):7 * move]
        assert (row[2], row[3], row[5]) == (power, kind, pp), (name, list(row))
        move_table[name] = {'native_id': move, 'power': power, 'native_type': kind, 'PP': pp}
    costs = {}
    for role in ('shaman', 'warrior', 'warlock'):
        table = rom_bytes(rom, sym, 'PeonResourceMoveCostV029.' + role, 64)
        entries = {}
        for offset in range(0, len(table), 2):
            if table[offset] == 255:
                break
            entries[table[offset]] = table[offset + 1]
        else:
            raise AssertionError(('Unterminated cost table', role))
        assert all(move not in entries for move in (1, *STARTERS))
        costs[role] = {'MACE_STRIKE_mana_or_rage_cost': 0, 'STRIKE_mana_or_rage_cost': 0}
    return {'status': 'PASS', 'curricula': curricula, 'starting_moves': move_table,
            'basic_attack_resource_costs': costs,
            'companions_use_native_PP': True,
            'Lightning_Bolt_script_sha256': sha(ROOT / 'data/moves/peon_spell_animations.asm')}


class FrameBoy:
    def __init__(self, raw, session):
        self.raw, self.session = raw, session

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def tick(self, count=1, render=True, sound=True):
        result = None
        for _ in range(count):
            result = self.raw.tick(1, render, sound)
            self.session.observe_frame()
        return result


class RockSession(OrdinaryBattleReadiness, ResourceHUDSession):
    open_roster = RosterSession.open_roster
    member_action = RosterSession.member_action
    close_roster = RosterSession.close_roster

    def __init__(self, rom, sym, output):
        self.animations, self.animation_errors, self.native_PP = [], [], []
        self.active_animation = None
        self.record_animations = True
        self.current_PP = None
        self.particle_sources = {
            'rock': (ROOT / 'gfx/battle_anims/rocks.2bpp').read_bytes(),
            'sand': (ROOT / 'gfx/battle_anims/sand.2bpp').read_bytes(),
        }
        super().__init__(rom, sym, 0, output)

    def open(self):
        super().open()
        self.p = FrameBoy(self.p, self)
        for label, callback in (('GetBattleAnimByte', self.animation_byte),
                                ('RunBattleAnimScript.done', self.animation_done),
                                ('BattleCommand_DoTurn.player', self.player_PP_paid)):
            self.p.hook_register(*self.sym[label], callback, None)

    def animation_byte(self, _):
        if not self.record_animations or self.active_animation is not None:
            return
        move = int.from_bytes(bytes(self.read('wFXAnimID', 2)), 'little')
        if move not in ANIMATIONS:
            return
        pointer = int.from_bytes(bytes(self.read('wBattleAnimAddress', 2)), 'little')
        if pointer != self.sym[ANIMATIONS[move]][1]:
            return
        enemy = bool(self.read('hBattleTurn')[0])
        species = self.read('wEnemyMonSpecies' if enemy else 'wBattleMonSpecies')[0]
        if species not in ROCKS:
            return
        if sum(row['move'] == move and row['enemy_caster'] == enemy for row in self.animations) >= 2:
            return
        self.active_animation = {
            'move': move, 'enemy_caster': enemy, 'caster_species': species,
            'script': ANIMATIONS[move], 'start_frame': self.p.frame_count,
            'frames': [], 'projectile_positions': [], 'peak_hardware_scanline_objects': 0,
            'peak_hardware_OAM_objects': 0, 'native_rock_graphics_seen': False,
            'native_sand_graphics_seen': False,
        }

    def animation_done(self, _):
        if self.active_animation is None or not self.read('wBattleAnimFlags')[0] & 1:
            return
        row, self.active_animation = self.active_animation, None
        row['end_frame'] = self.p.frame_count
        row['duration_frames'] = row['end_frame'] - row['start_frame']
        frames = row.pop('frames')
        try:
            assert frames and row['duration_frames'] >= 12, row
            assert row['peak_hardware_scanline_objects'] <= 10, row
            assert row['peak_hardware_OAM_objects'] <= 40, row
            if row['move'] == 88:
                assert row['native_rock_graphics_seen'], 'Native ROCKS never reached animation VRAM'
                positions = row['projectile_positions']
                assert len({point[0] for point in positions}) >= 12, ('No visible rock travel', positions)
                assert min(point[0] for point in positions) < 80 < max(point[0] for point in positions)
                if row['enemy_caster']:
                    assert positions[-1][0] < positions[0][0], positions
                else:
                    assert positions[-1][0] > positions[0][0], positions
            if row['move'] in (88, 189):
                assert row['native_sand_graphics_seen'], 'Native SAND never reached animation VRAM'
            stem = ('enemy_' if row['enemy_caster'] else 'player_') + str(row['move'])
            stem += '_' + str(sum(old['move'] == row['move'] and old['enemy_caster'] == row['enemy_caster']
                                 for old in self.animations) + 1)
            directory = self.folder / 'animations'
            directory.mkdir(parents=True, exist_ok=True)
            frames[0].save(directory / (stem + '.gif'), save_all=True,
                           append_images=frames[1:], duration=17, loop=0, optimize=False)
            for phase, index in (('launch', min(6, len(frames) - 1)),
                                 ('travel', len(frames) // 2),
                                 ('impact', max(0, len(frames) - 12))):
                path = directory / (stem + '_' + phase + '.png')
                frames[index].save(path)
                frames[index].resize((640, 576), Image.Resampling.NEAREST).save(
                    path.with_stem(path.stem + '_4x'))
            row.update(status='PASS', evidence=str((directory / (stem + '.gif')).relative_to(ROOT)))
            self.animations.append(row)
        except Exception as error:
            self.animation_errors.append({'error': repr(error), 'animation': row})

    def observe_frame(self):
        row = self.active_animation
        if row is None:
            return
        row['frames'].append(self.p.screen.image.copy())
        raw = list(self.p.memory[0xfe00:0xfea0])
        height = 16 if self.p.memory[0xff40] & 4 else 8
        visible = [(raw[i] - 16, raw[i + 1] - 8) for i in range(0, 160, 4)
                   if 0 < raw[i] < 160 and 0 < raw[i + 1] < 168]
        row['peak_hardware_OAM_objects'] = max(row['peak_hardware_OAM_objects'], len(visible))
        peak = max((sum(y <= line < y + height for y, _ in visible) for line in range(144)), default=0)
        row['peak_hardware_scanline_objects'] = max(row['peak_hardware_scanline_objects'], peak)
        vram = bytes(self.p.memory[0, 0x8300:0x8900])
        for kind, source in self.particle_sources.items():
            if source in vram:
                row['native_' + kind + '_graphics_seen'] = True
        if row['move'] == 88:
            structs = self.read('wActiveAnimObjects', 24 * 10)
            for offset in range(0, len(structs), 24):
                obj = structs[offset:offset + 24]
                if obj[0] and obj[4] == 6:  # native arc-to-target-and-disappear callback
                    x = 180 - obj[7] if row['enemy_caster'] else obj[7]
                    y = 144 - obj[8] if row['enemy_caster'] else obj[8]
                    row['projectile_positions'].append([x, y])

    def player_PP_paid(self, _):
        if self.read('hBattleTurn')[0] or self.read('wBattleMonSpecies')[0] not in ROCKS:
            return
        after = self.read('wBattleMonPP', 4)
        move = self.read('wCurPlayerMove')[0]
        if self.current_PP is not None:
            slot = self.read('wBattleMonMoves', 4).index(move)
            expected = list(self.current_PP)
            expected[slot] = expected[slot] & 0xc0 | ((expected[slot] & 0x3f) - 1)
            assert after == expected, ('Native PP payment', move, self.current_PP, after, expected)
            self.native_PP.append({'move': move, 'before': self.current_PP, 'after': after,
                                   'exact_one_native_PP_spent': True})
        self.current_PP = after

    def safe_strike(self):
        """A native miss after enemy Mud-Slap is a valid turn, not test failure."""
        self.ready('battle')
        if not self.read('wBattleMode')[0]:
            return
        self.open_moves()
        for _ in range(6):
            if self.read('wMenuCursorY') == [1]:
                break
            self.press('up', 30)
        menus = self.menus
        self.phase, self.context = 'move_pending', None
        self.press('a', 30)
        self.wait_for(lambda: self.menus > menus and self.phase == 'battle'
                      or not self.read('wBattleMode')[0], True)

    def weaken_second(self):
        for _ in range(6):
            if not self.read('wBattleMode')[0]:
                return
            if 0 < self.word('wEnemyMonHP') < self.word('wEnemyMonMaxHP'):
                return
            self.safe_strike()
        assert 0 < self.word('wEnemyMonHP') < self.word('wEnemyMonMaxHP')

    def real_quest(self):
        self.fresh_class()
        self.begin_boar()
        self.until_world(choose_bolt=True)
        self.talk_at((10, 10), 'up', 'ordinary_gornek_boar_reward')
        self.travel(15)
        self.talk_at((11, 11), 'right', 'mysterious_shaman_offer')
        self.begin_elemental()
        for _ in range(50):
            if not self.read('wBattleMode')[0]:
                break
            self.ready('battle')
            if not self.read('wBattleMode')[0]:
                break
            if self.word('wBattleMonHP') <= self.word('wBattleMonMaxHP') // 2 and self.item_quantity(18):
                self.open_bag_item(18)
                self.phase, self.context = 'using_item', None
                self.press('a', 90)
            else:
                self.safe_strike()
        self.wait_for(lambda: not self.read('wBattleMode')[0] and not self.read('wScriptMode')[0], True)
        assert self.read('wBattleResult') == [0] and self.quest()['found']
        self.travel(15)
        self.talk_at((11, 11), 'right', 'return_telluric_stone_to_shaman')
        self.heal_at_inn()
        self.begin_elemental(second=True)
        self.capture_second()
        assert self.read('wPartyMon2Species') == [95] and self.read('wPartyMon2Level') == [3]
        self.capture('real_capture_TERRA_level_3')

    def rock_battle(self):
        self.heal_at_inn()
        self.open_roster(1)
        self.member_action(3)
        assert self.read('wPeonTeamPreferredV029') == [1]
        self.close_roster()
        # The scripted Den scorpid near Gornek remains undefeated. Enter
        # its actual authored coordinate trigger with a real walking step.
        self.navigate((19, 12))
        self.press('down', 30)
        self.press('a', 60)
        self.wait_for(lambda: self.phase == 'battle' and self.read('wBattleMode')[0], True)
        assert self.read('wCurBattleMon') == [1]
        self.current_PP = self.read('wBattleMonPP', 4)
        mana_before = self.word('wPartyMon1CaughtData')
        used = []
        # Use the weaker contact first. Rock Throw is super effective on
        # this actual scorpid and can otherwise end the fight immediately.
        for move in STARTERS:
            if not self.read('wBattleMode')[0]:
                break
            self.ready('battle')
            self.open_moves()
            moves = self.read('wBattleMonMoves', 4)
            slot = moves.index(move)
            for _ in range(7):
                cursor = self.read('wMenuCursorY')[0] - 1
                if cursor == slot:
                    break
                self.press('up' if cursor > slot else 'down', 30)
            self.capture('rock_selected_' + str(move))
            menus = self.menus
            self.phase, self.context = 'move_pending', None
            self.press('a', 60)
            self.wait_for(lambda: self.menus > menus and self.phase == 'battle'
                          or not self.read('wBattleMode')[0], True)
            used.append(move)
        if self.read('wBattleMode')[0]:
            self.until_world(choose_bolt=False)
        self.wait_for(lambda: not self.read('wBattleMode')[0] and not self.read('wScriptMode')[0], True)
        assert set(STARTERS) <= set(used), used
        assert set(STARTERS) <= {row['move'] for row in self.native_PP}, self.native_PP
        assert self.word('wPartyMon1CaughtData') == mana_before, 'Companion spent hero mana'
        assert not self.animation_errors, self.animation_errors
        assert {(False, move) for move in STARTERS} <= {(row['enemy_caster'], row['move']) for row in self.animations}
        assert any(row['enemy_caster'] and row['move'] in (189, 88) for row in self.animations)
        self.capture('rock_native_PP_earth_attacks_complete')
        return {'status': 'PASS', 'actual_companion_move_ids': used, 'native_PP': self.native_PP,
                'hero_mana_preserved': True, 'animations': self.animations}

    def save_real_battery(self):
        self.travel(14)
        self.navigate((12, 9))
        self.press('start')
        self.wait_for(lambda: self.presentation == 'start')
        for _ in range(16):
            cursor = self.read('wMenuCursorPosition')[0]
            if cursor == 4:
                break
            self.p.button('up' if cursor > 4 else 'down', delay=16)
            self.p.tick(48, True)
        assert self.read('wMenuCursorPosition') == [4]
        previous = self.saves
        for _ in range(80):
            if self.saves > previous:
                break
            self.p.button('a', delay=16)
            self.p.tick(120, True)
        assert self.saves == previous + 1
        self.p.tick(360, True)
        for _ in range(10):
            if self.presentation == 'world':
                break
            self.press('b', 90)
        before = ExitSession.complete_record(self)
        self.capture('native_SAVE_before_upgrade')
        self.p.stop(save=True)
        self.p = None
        battery = Path(str(self.rom) + '.ram')
        assert battery.stat().st_size == 32768
        return before, battery

    def cold_continue(self):
        self.open()
        self.p.tick(240, True)
        self.press('start', 90)
        for _ in range(160):
            if self.map() == 14 and self.presentation == 'world' and not self.read('wScriptMode')[0]:
                break
            self.press('a', 90)
        assert self.map() == 14 and self.presentation == 'world'
        self.p.tick(120, True)
        return ExitSession.complete_record(self)


def upgraded_record(before):
    expected = copy.deepcopy(before)
    data = expected['wPartyMon1']
    offset = 48
    assert data[offset + 2:offset + 6] == [1, 84, 0, 0]
    data[offset + 2:offset + 6] = [33, 189, 88, 0]
    old = data[offset + 24]
    data[offset + 24] = (old & 0xc0) | min(old & 0x3f, 10 + 2 * (old >> 6))
    data[offset + 25] = 15
    return expected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', required=True, type=Path)
    parser.add_argument('--sym', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--baseline-rom', type=Path, default=ROOT / 'releases/v0.2.15/peon_of_warcraft_v0_2_15.gbc')
    parser.add_argument('--baseline-sym', type=Path, default=ROOT / 'releases/v0.2.15/peon_of_warcraft_v0_2_15.sym')
    parser.add_argument('--skip-migration', action='store_true')
    parser.add_argument('--static-only', action='store_true')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    sym = symbols(args.sym)
    report = {'status': 'RUNNING', 'rom_sha256': sha(args.rom), 'sym_sha256': sha(args.sym),
              'method': 'Fresh private games; real quest capture, native turns, real SAVE and cold Continue; controller only.',
              'emulator_RAM_writes': False, 'ROM_patches': False, 'state_restores': False,
              'CPU_substitutions': False, 'user_saves_opened': False,
              'limitations': ['Physical Chromatic hardware not tested.',
                             'Higher-level move progression checked in linked ROM; no claim of ordinary level-15 play.']}
    current = None
    try:
        report['linked_ROM_contract'] = static_contract(args.rom, sym)
        if not args.static_only:
            with tempfile.TemporaryDirectory(prefix='peon-earth-v0216-') as directory:
                rom = Path(directory) / 'fresh.gbc'
                shutil.copyfile(args.rom, rom)
                current = RockSession(rom, sym, args.output / 'fresh_capture')
                current.real_quest()
                assert current.read('wPartyMon2Moves', 4) == [*STARTERS, 0]
                report['fresh_capture_native_moves'] = current.read('wPartyMon2Moves', 4)
                report['fresh_capture_native_PP'] = current.read('wPartyMon2PP', 4)
                report['fresh_quest_playability'] = {
                    'first_quest_rock_defeated': True, 'actual_capture_rolls': current.rolls,
                    'actual_native_defeat_retries': current.capture_retries,
                    'no_balance_stat_changes_or_injected_items': True,
                }
                report['earth_attacks'] = current.rock_battle()
                current.p.stop(save=False)
                current.p = None
                if not args.skip_migration:
                    legacy = Path(directory) / 'legacy.gbc'
                    shutil.copyfile(args.baseline_rom, legacy)
                    current = RockSession(legacy, symbols(args.baseline_sym), args.output / 'v0215_source')
                    current.record_animations = False
                    current.real_quest()
                    assert current.read('wPartyMon2Moves', 4) == [1, 84, 0, 0]
                    before, battery = current.save_real_battery()
                    target = Path(directory) / 'upgraded.gbc'
                    shutil.copyfile(args.rom, target)
                    shutil.copyfile(battery, Path(str(target) + '.ram'))
                    current = RockSession(target, sym, args.output / 'upgrade_continue')
                    after = current.cold_continue()
                    expected = upgraded_record(before)
                    assert after == expected, ('Upgrade changed fields outside known starter moves/PP', before, after, expected)
                    current.capture('cold_CONTINUE_rock_moves_corrected')
                    report['v0215_private_battery_upgrade'] = {
                        'status': 'PASS', 'baseline_rom_sha256': sha(args.baseline_rom),
                        'private_battery_bytes': 32768, 'before_moves': [1, 84, 0, 0],
                        'after_moves': current.read('wPartyMon2Moves', 4),
                        'all_other_party_stats_PP_names_levels_quests_items_money_unchanged': True,
                        'one_time_migration': True,
                    }
                    # Trigger map setup once more; converted starter guard must
                    # no longer match, and no native PP may be restored.
                    moves_before = current.read('wPartyMon2Moves', 4)
                    PP_before = current.read('wPartyMon2PP', 4)
                    current.travel(15)
                    assert current.read('wPartyMon2Moves', 4) == moves_before
                    assert current.read('wPartyMon2PP', 4) == PP_before
        report['status'] = 'PASS'
    except BaseException as error:
        report.update(status='FAIL', error=repr(error))
        if current is not None and current.p is not None:
            current.capture('failure')
            report['failure_state'] = {'phase': current.phase, 'presentation': current.presentation,
                                       'map': current.map(), 'position': current.position(),
                                       'battle': current.read('wBattleMode'), 'quest': current.quest(),
                                       'animation_errors': current.animation_errors,
                                       'PC': hex(current.p.register_file.PC)}
        raise
    finally:
        if current is not None and current.p is not None:
            current.p.stop(save=False)
        (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
