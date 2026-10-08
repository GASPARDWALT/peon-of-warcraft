#!/usr/bin/env python3
"""Play the expanded finite Valley quest chain; isolate explicit fault fixtures.

Normal progression uses only ordinary buttons, native menus, read-only hooks,
and a real battery save/cold restart. It never writes game RAM or ROM, changes
CPU outcomes or loads emulator states. Separately labelled diagnostic cases
inject old quest states/full bags only into a disposable fresh ROM instance.
"""
import argparse
import hashlib
import json
import logging
import shutil
import tempfile
from pathlib import Path

from PIL import Image
import numpy as np
import validate_durotar_v022_quests as game
from validate_durotar_v022_quest_faults import FaultSession, pocket_item_ids
from validate_peon_villages import load_symbols, DIRECTIONS
from validate_peon_lazy_quest import event_indices

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/deep_polish/quests'
FAMILIARS = ('EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD',
             'EVENT_PEON_CAVE_APPROACH_IMP_2_DEAD',
             'EVENT_PEON_CAVE_STRONG_IMP_DEAD', 'EVENT_PEON_CAVE_IMP_DEAD')


class DeepQuestSession(game.QuestSession):
    def capture(self, label):
        self.p.screen.image.save(OUT / f'{label}.png')
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / f'{label}_4x.png')
        print(label, self.map(), self.position(), 'level', self.read('wPartyMon1Level'), flush=True)

    def talk_actor(self, script, label):
        name = game.MAPS[self.map()][0]
        actor = next(a for a in game.all_actors(name) if a['script'] == script
                     and not a['sprite'].startswith('SPRITE_PEON_QUEST'))
        x, y = actor['xy']; options = []
        for facing, dx, dy in DIRECTIONS:
            # DIRECTIONS is the direction toward the actor; stand opposite it.
            stand = (x - dx, y - dy)
            try:
                path = self.path(stand)
            except AssertionError:
                continue
            options.append((len(path), stand, facing))
        assert options, ('No speaker approach', script, actor)
        _, position, facing = min(options)
        self.talk(position, facing, label)
        self.p.tick(90, True)

    def progress(self):
        return {'money': self.money(), 'xp': self.experience(),
                'hp': self.read('wPartyMon1HP', 2), 'max_hp': self.read('wPartyMon1MaxHP', 2),
                'pp': self.read('wPartyMon1PP', 4), 'status': self.read('wPartyMon1Status'),
                'moves': self.read('wPartyMon1Moves', 4)}

    def marker(self, slot, wanted, label):
        self.p.tick(90, True)
        actual = self.read('wVariableSprites', 16)[slot]
        assert actual == wanted, (label, actual, wanted)
        index = 2 if self.map() == 14 else 7
        runtime = self.read(f'wMap{index}ObjectStructID')[0]
        assert runtime < 13, (label, 'Marker not allocated', runtime)
        row = self.read('wObjectStructs', 13 * 40)[runtime * 40:(runtime + 1) * 40]
        bank, base = (0 if row[2] & 128 else 1), row[2] & 127
        state = {53: 'available_yellow', 54: 'active_gray', 60: 'complete_yellow'}[wanted]
        palette = 5 if wanted == 54 else 4
        assert row[6] & 7 == palette, (label, 'Wrong actual marker palette')
        binary = (ROOT / f'gfx/sprites/peon_quest_{state}.2bpp').read_bytes()
        assert bytes(self.p.memory[bank, 0x8000 + base * 16:0x8000 + base * 16 + 64]) == binary
        native = np.asarray(Image.open(ROOT / f'references/generated/durotar_v022/quest_markers/{state}.png'))
        expected, mask = native[:, :, :3] >> 3, native[:, :, 3] != 0
        for waited in range(61):
            hardware = list(self.p.memory[0xfe00:0xfea0])
            if hardware == self.read('wShadowOAM', 160):
                break
            self.p.tick(1, True)
        assert hardware == self.read('wShadowOAM', 160), (label, 'Incomplete hardware OAM publication')
        screen = np.asarray(self.p.screen.image.convert('RGB')) >> 3
        parts = set(); opaque_total = 0
        for i in range(0, 160, 4):
            y, x, number, attrs = hardware[i:i + 4]
            if not (base <= number < base + 4) or attrs & 7 != palette or (attrs >> 3) & 1 != bank:
                continue
            tx, ty = (number - base) % 2 * 8, (number - base) // 2 * 8
            px, py = x - 8, y - 16
            if not (0 <= px <= 152 and 0 <= py <= 136):
                continue
            assert not attrs & 0x60
            opaque = mask[ty:ty + 8, tx:tx + 8]
            assert np.array_equal(screen[py:py + 8, px:px + 8][opaque],
                                  expected[ty:ty + 8, tx:tx + 8][opaque]), (label, 'Rendered glyph pixels differ')
            parts.add(number - base); opaque_total += int(opaque.sum())
        assert parts == {0, 1, 2, 3} and opaque_total == int(mask.sum()), (label, 'Missing or clipped hardware glyph')
        self.capture(label)
        return {'resolved_native_sprite_id': actual, 'ordinary_progress': True,
                'native_vram_matches': True, 'actual_hardware_oam_four_tiles': True,
                'actual_opaque_rgb555_pixels_match': True, 'object_index': index,
                'hardware_publication_waited_frames': waited}


def reward(s, script, flag, xp, copper, label):
    before = s.progress()
    s.talk_actor(script, label)
    assert s.event(flag), (label, 'Reward flag not set')
    assert s.experience() == before['xp'] + xp, (label, 'Wrong XP delta', before, s.progress())
    assert s.money() == before['money'] + copper, (label, 'Wrong copper delta', before, s.progress())
    return {'xp_delta': xp, 'copper_delta': copper, 'one_time_saved_flag': flag}


def normal(symbols, report):
    s = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-deep-normal-') as directory:
            rom = Path(directory) / 'normal.gbc'; shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = DeepQuestSession(rom, symbols); s.fresh()
            s.talk_actor('TheDenQuestScript', 'normal_cutting_accept')
            s.navigate((18, 13)); s.press('up', 30); s.press('a')
            result = s.fight('normal_boar', 'EVENT_PEON_QUEST_DONE')
            assert result['outcome'] == 0; report['battles'].append(result)
            s.talk_actor('TheDenQuestScript', 'normal_cutting_reward_and_sting_accept')
            assert s.event('EVENT_PEON_STING_ACCEPTED')
            s.rest()
            game.start_hostile(s, (17, 15), 'normal_den_scorpid',
                               'EVENT_PEON_SCORPID_DEFEATED', None, report['battles'])
            s.talk_actor('TheDenQuestScript', 'normal_sting_reward')
            assert s.event('EVENT_PEON_MAP_RECEIVED') and s.event('EVENT_PEON_GEAR_REWARDED')
            assert s.event('EVENT_PEON_GEAR_CLUB_GRANTED') and s.item_quantity(0x89) == 1
            s.p.tick(90, True)
            assert s.read('wMap2ObjectStructID') == [255], 'Gornek idle marker not hidden'
            before = s.progress(); s.talk_actor('TheDenQuestScript', 'normal_no_repeat_den_reward')
            assert s.progress() == before
            report['initial_gear_once_and_idle_gornek_hidden'] = True
            s.rest(); s.to_valley()
            s.talk_actor('ValleyZureethaScript', 'normal_familiars_accept')
            assert s.event('EVENT_PEON_FAMILIARS_ACCEPTED')
            assert not s.event('EVENT_PEON_MEDALLION_ACCEPTED')
            report['markers']['familiars_active'] = s.marker(15, 54, 'normal_familiars_gray_question')
            for approach, label, flag, copper in (
                    ((24, 6), 'normal_approach_familiar_one', FAMILIARS[0], 30),
                    ((26, 9), 'normal_approach_familiar_two', FAMILIARS[1], 30)):
                game.start_hostile(s, approach, label, flag, copper, report['battles'])
                s.rest(); s.to_valley()
            s.talk_actor('ValleyZureethaScript', 'normal_familiars_two_of_four')
            assert not s.event('EVENT_PEON_FAMILIARS_DONE')
            assert s.read('wStringBuffer3') == [2], 'Native quest counter incorrect'
            s.navigate((24, 4), expected_map=20)
            game.start_hostile(s, (8, 11), 'normal_cave_familiar', FAMILIARS[3], 20, report['battles'])
            s.rest(); s.to_valley(); s.navigate((24, 4), expected_map=20)
            game.start_hostile(s, (12, 9), 'normal_cave_strong_familiar', FAMILIARS[2], 30, report['battles'])
            s.navigate((10, 16), expected_map=15)
            s.navigate((5, 11))
            report['markers']['familiars_ready'] = s.marker(15, 60, 'normal_familiars_yellow_question')
            report['rewards']['familiars'] = reward(s, 'ValleyZureethaScript', 'EVENT_PEON_FAMILIARS_DONE',
                                                    40, 50, 'normal_familiars_turn_in')
            assert not s.event('EVENT_PEON_MEDALLION_ACCEPTED'), 'Next quest silently accepted at turn-in'
            report['markers']['medallion_available'] = s.marker(15, 53, 'normal_medallion_yellow_exclamation')
            before = s.progress(); s.talk_actor('ValleyZureethaScript', 'normal_medallion_accept')
            assert s.event('EVENT_PEON_MEDALLION_ACCEPTED') and s.progress() == before
            report['markers']['medallion_active'] = s.marker(15, 54, 'normal_medallion_gray_question')
            # Sarkoth is another giver's single active quest. Its completed
            # report is delivered at Gornek instead of introducing a new item.
            s.rest(); s.to_valley()
            s.talk_actor('ValleyHanazuaScript', 'normal_sarkoth_accept')
            game.start_hostile(s, (16, 21), 'normal_sarkoth', 'EVENT_PEON_SARKOTH_DEAD', 35, report['battles'])
            report['rewards']['sarkoth'] = reward(s, 'ValleyHanazuaScript', 'EVENT_PEON_SARKOTH_DONE',
                                                 50, 100, 'normal_sarkoth_turn_in')
            before = s.progress(); s.talk_actor('ValleyHanazuaScript', 'normal_hanazua_report_reminder')
            assert s.progress() == before
            s.go_den(); s.navigate((10, 10))
            report['markers']['gornek_report_ready'] = s.marker(13, 60, 'normal_gornek_report_yellow_question')
            report['rewards']['gornek_report'] = reward(s, 'TheDenQuestScript', 'EVENT_PEON_SARKOTH_REPORT_DONE',
                                                        25, 50, 'normal_gornek_report_turn_in')
            assert s.read('wMap2ObjectStructID') == [255], 'Completed report marker remains'
            before = s.progress(); s.talk_actor('TheDenQuestScript', 'normal_gornek_no_repeat_report')
            assert s.progress() == before
            # Clear the cave's remaining finite native route. Healing happens
            # only through explicitly chosen inns, never between encounters.
            for approach, label, flag, copper in (
                    ((5, 7), 'normal_felstalker', 'EVENT_PEON_CAVE_FELSTALKER_DEAD', 25),
                    ((5, 4), 'normal_cultist', 'EVENT_PEON_CAVE_CULTIST_DEAD', 25),
                    ((14, 4), 'normal_yarrog', 'EVENT_PEON_YARROG_DEAD', 35)):
                s.rest(); s.to_valley(); s.navigate((24, 4), expected_map=20)
                game.start_hostile(s, approach, label, flag, copper, report['battles'])
            s.navigate((10, 16), expected_map=15)
            s.navigate((5, 11))
            report['markers']['medallion_ready'] = s.marker(15, 60, 'normal_medallion_yellow_question')
            report['rewards']['medallion'] = reward(s, 'ValleyZureethaScript', 'EVENT_PEON_MEDALLION_DONE',
                                                   100, 150, 'normal_medallion_turn_in')
            assert s.item_quantity(0x8e) == 1
            before = s.progress(); s.talk_actor('ValleyZureethaScript', 'normal_no_repeat_zureetha_reward')
            assert s.progress() == before
            report['save_cold_restart'] = s.cold_restart()
            assert all(s.event(flag) for flag in FAMILIARS)
            assert all(s.event(flag) for flag in ('EVENT_PEON_FAMILIARS_ACCEPTED', 'EVENT_PEON_FAMILIARS_DONE',
                                                  'EVENT_PEON_SARKOTH_REPORT_DONE', 'EVENT_PEON_GEAR_CLUB_GRANTED'))
            before, encounters = s.progress(), s.encounter_loads
            s.to_valley()
            for xy in ((25, 6), (24, 6), (27, 9), (26, 9)):
                s.navigate(xy); s.press('a'); assert s.read('wBattleMode') == [0]
            s.navigate((24, 4), expected_map=20)
            for xy in ((8, 10), (8, 11), (12, 8), (12, 9), (14, 3), (14, 4)):
                s.navigate(xy); s.press('a'); assert s.read('wBattleMode') == [0]
            assert s.encounter_loads == encounters and s.progress() == before
            report['retired_familiars_and_bosses_survive_cold_restart'] = True
            report['normal_ram_edits'] = False; report['normal_savestates_loaded'] = False
            report['normal_all_checks_passed'] = True
            s.p.stop(save=False); s = None
    finally:
        if s:
            s.capture('normal_unexpected_state'); s.p.stop(save=False)


class DeepFaultSession(FaultSession, DeepQuestSession):
    capture = DeepQuestSession.capture
    talk_actor = DeepQuestSession.talk_actor


def diagnostic(symbols, report):
    s = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-deep-diagnostic-') as directory:
            rom = Path(directory) / 'fixture.gbc'; shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = DeepFaultSession(rom, symbols); s.fresh(); s.to_valley()
            for flag in FAMILIARS:
                s.set_event(flag)
            s.talk_actor('ValleyZureethaScript', 'diagnostic_pre_kills_accept')
            assert s.event('EVENT_PEON_FAMILIARS_ACCEPTED') and not s.event('EVENT_PEON_MEDALLION_ACCEPTED')
            assert s.read('wVariableSprites', 16)[15] == 60
            before = s.progress(); s.talk_actor('ValleyZureethaScript', 'diagnostic_pre_kills_reward')
            assert s.event('EVENT_PEON_FAMILIARS_DONE')
            assert s.experience() == before['xp'] + 40 and s.money() == before['money'] + 50
            assert all(s.event(flag) for flag in FAMILIARS)
            report['diagnostic_cases']['pre_kills_count_without_respawn'] = True
            # A published save can have an accepted or completed medallion
            # while the new familiars bits are still zero. Neither gets gated.
            s.set_event('EVENT_PEON_FAMILIARS_ACCEPTED', False)
            s.set_event('EVENT_PEON_FAMILIARS_DONE', False)
            s.set_event('EVENT_PEON_MEDALLION_ACCEPTED')
            s.set_event('EVENT_PEON_YARROG_DEAD')
            before = s.progress(); s.talk_actor('ValleyZureethaScript', 'diagnostic_old_medallion_reward')
            assert s.event('EVENT_PEON_MEDALLION_DONE')
            assert not s.event('EVENT_PEON_FAMILIARS_ACCEPTED') and not s.event('EVENT_PEON_FAMILIARS_DONE')
            assert s.experience() == before['xp'] + 100 and s.money() == before['money'] + 150
            after = s.progress(); s.talk_actor('ValleyZureethaScript', 'diagnostic_old_medallion_already_done')
            assert s.progress() == after
            report['diagnostic_cases']['old_medallion_accepted_and_completed_bypass_gate'] = True
            s.go_den()
            for flag in ('EVENT_PEON_QUEST_ACCEPTED', 'EVENT_PEON_QUEST_DONE', 'EVENT_PEON_CUTTING_TURNED_IN',
                         'EVENT_PEON_STING_ACCEPTED', 'EVENT_PEON_SCORPID_DEFEATED', 'EVENT_PEON_MAP_RECEIVED'):
                s.set_event(flag)
            for flag in ('EVENT_PEON_SMALL_BAG', 'EVENT_PEON_GEAR_REWARDED', 'EVENT_PEON_GEAR_CLUB_GRANTED'):
                s.set_event(flag, False)
            s.set_event('EVENT_PEON_LARGE_BAG')
            # Nineteen ITEM stacks allow the club; an independently full
            # KEY_ITEM pouch blocks the small-pouch reward.
            ids = pocket_item_ids('ITEM', (0x89, 0x64))[:19]
            s.write('wNumItems', [19]); s.write('wItems', [v for item in ids for v in (item, 1)] + [255])
            saved_keys = s.full_keys((0x64,))
            before = s.progress(); s.talk_actor('TheDenQuestScript', 'diagnostic_partial_club_reward')
            assert s.event('EVENT_PEON_GEAR_CLUB_GRANTED') and s.item_quantity(0x89) == 1
            assert not s.event('EVENT_PEON_SMALL_BAG') and not s.event('EVENT_PEON_GEAR_REWARDED')
            assert s.read('wVariableSprites', 16)[13] == 60
            assert s.read('wMap2ObjectStructID')[0] < 13, 'Pending gear marker hidden'
            assert s.progress() == before, 'Retry gear gave repeated XP/copper or changed battle state'
            s.set_event('EVENT_PEON_SARKOTH_REPORT_DONE')
            s.talk_actor('TheDenQuestScript', 'diagnostic_partial_retry_still_full')
            assert s.item_quantity(0x89) == 1 and s.progress() == before
            assert s.read('wMap2ObjectStructID')[0] < 13, 'Report done hid pending gear marker'
            # A published partial handoff has the club but predates the new
            # per-component flag. Inventory must prevent a second club.
            s.set_event('EVENT_PEON_GEAR_CLUB_GRANTED', False)
            s.talk_actor('TheDenQuestScript', 'diagnostic_legacy_partial_club_no_duplicate')
            assert s.event('EVENT_PEON_GEAR_CLUB_GRANTED') and s.item_quantity(0x89) == 1
            assert not s.event('EVENT_PEON_SMALL_BAG') and s.progress() == before
            # Make key-pouch room without removing the already awarded club.
            s.restore_keys(saved_keys)
            s.talk_actor('TheDenQuestScript', 'diagnostic_pouch_retry_success')
            assert s.event('EVENT_PEON_SMALL_BAG') and s.event('EVENT_PEON_GEAR_REWARDED')
            assert s.item_quantity(0x89) == 1 and 0x64 in s.read('wKeyItems', s.read('wNumKeyItems')[0]) and s.progress() == before
            s.talk_actor('TheDenQuestScript', 'diagnostic_completed_gear_repeat')
            assert s.item_quantity(0x89) == 1 and 0x64 in s.read('wKeyItems', s.read('wNumKeyItems')[0]) and s.progress() == before
            report['diagnostic_cases']['partial_gear_reward_retry_without_duplicate_club'] = True
            report['diagnostic_cases']['pending_gear_marker_survives_completed_report'] = True
            report['diagnostic_ram_edits'] = True; report['diagnostic_savestates_loaded'] = False
            report['diagnostic_only_isolated_disposable_rom'] = True
            report['diagnostic_all_checks_passed'] = True
            s.p.stop(save=False); s = None
    finally:
        if s:
            s.capture('diagnostic_unexpected_state'); s.p.stop(save=False)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--section', choices=('normal', 'diagnostic', 'all'), default='all')
    parser.add_argument('--expected-sha'); args = parser.parse_args()
    logging.disable(logging.CRITICAL); OUT.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest()
    if args.expected_sha:
        assert digest == args.expected_sha, ('Candidate changed', digest, args.expected_sha)
    report = {'rom_sha256': digest, 'section': args.section, 'battles': [], 'markers': {}, 'rewards': {},
              'diagnostic_cases': {}, 'limitations': ['Physical Chromatic not tested.',
                'Four finite familiars replace the twelve-kill Classic objective; no respawn system added.',
                'Prepared earlier post-medallion quests and Call of Earth are not implemented here.']}
    filename = OUT / f'{args.section}_validation.json'
    try:
        symbols = load_symbols(); game.FLAGS = event_indices()
        if args.section in ('normal', 'all'):
            normal(symbols, report)
        if args.section in ('diagnostic', 'all'):
            diagnostic(symbols, report)
        assert hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest() == digest, 'Source ROM changed during validation'
        report['all_checks_passed'] = True
    except Exception as error:
        report['failure'] = repr(error); report['all_checks_passed'] = False
        filename.write_text(json.dumps(report, indent=2) + '\n'); raise
    filename.write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: deep quest', args.section, digest)


if __name__ == '__main__':
    main()
