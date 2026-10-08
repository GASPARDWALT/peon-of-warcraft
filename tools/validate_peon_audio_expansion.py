#!/usr/bin/env python3
"""Validate the new native GBC audio without changing published evidence.

Isolated sound previews use a labelled temporary title CALL fixture. Independent
music evidence is tied to the exact ROM hash. The gameplay uses only normal
buttons and read-only observers, including for actual level gains. WAVs contain
the emulator APU, with pre-gain clipping measured separately. WoW recordings
were unavailable; these are original compositions, not imported samples.
"""
import argparse
import hashlib
import json
import logging
import shutil
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image
from pyboy import PyBoy

import run_peon_v023_validation as adapter
import validate_durotar_v022_quests as quests
from validate_peon_battle_totems import BagSession, TOTEM, POTION
from validate_peon_cave_approach import published_snapshot
from validate_peon_sfx import sfx_ids
from validate_peon_villages import load_symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/warcraft_audio_update/validation'
SFX_OUT = OUT.parent / 'sound_effects'
MUSIC_OUT = OUT.parent / 'music'
SFX_DESIGN = ROOT / 'references/generated/warcraft_audio_update/sound_effects/design.json'
MUSIC_IDS = {'Durotar': 0x67, 'Cave': 0x68, 'Inn': 0x6a}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(p, sym, name, count=1):
    if not count:
        return []
    bank, address = sym[name]
    return list(p.memory[address:address + count] if address >= 0xe000
                else p.memory[bank, address:address + count])


def safe_hook(p, sym, label, callback, errors):
    """PyBoy logs callback exceptions; retain and explicitly fail on them."""
    def guarded(_):
        try:
            callback()
        except Exception as error:
            errors.append({'hook': label, 'error': repr(error)})
    p.hook_register(*sym[label], guarded, None)


def write_audio(path, arrays, rate=48000):
    raw = np.concatenate(arrays).astype(np.int16)
    assert len(raw) and raw.max() > raw.min(), ('Silent native APU', path.name)
    peak = int(np.abs(raw).max())
    clipped = int(np.count_nonzero((raw == 127) | (raw == -128)))
    assert clipped == 0, ('Native APU saturated before preview gain', path.name, clipped)
    samples = raw.astype(float)
    samples -= samples.mean(axis=0, keepdims=True)
    gain = 28000 / max(1, float(np.abs(samples).max()))
    pcm = np.clip(samples * gain, -32768, 32767).astype('<i2')
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(2); output.setsampwidth(2); output.setframerate(rate)
        output.writeframes(pcm.tobytes())
    return {'wav': path.name, 'seconds': len(raw) / rate,
            'actual_native_apu_peak_before_gain': peak,
            'native_clipped_samples_before_gain': clipped,
            'preview_gain_only': gain, 'native_apu_capture': True}


def record_effect(rom, sym, effect, effect_id, mixed=False):
    """Exercise every new sound's real bytecode in an isolated ROM fixture."""
    production = rom.read_bytes()
    bank, address = sym['PeonTitleScreen.wait']
    offset = bank * 0x4000 + address - 0x4000
    original = production[offset:offset + 3]
    assert original[0] == 0xcd
    patched = bytearray(production)
    target = sym['PlaySFX'][1]
    patched[offset:offset + 3] = bytes((0xcd, target & 255, target >> 8))
    state = {'frame': 0, 'started': None, 'ended': None, 'voices': set()}
    errors, arrays = [], []
    with tempfile.TemporaryDirectory(prefix='peon-new-sfx-') as directory:
        path = Path(directory) / 'diagnostic.gbc'; path.write_bytes(patched)
        p = PyBoy(str(path), window='null', sound_emulated=True,
                  sound_sample_rate=48000, log_level='ERROR')
        p.set_emulation_speed(0)
        def trigger():
            if state['started'] is None:
                p.register_file.D, p.register_file.E = 0, effect_id
                state['started'] = state['frame']
                for i, value in enumerate(original):
                    p.memory[bank, address + i] = value
        def silence():
            if p.register_file.D == 0 and p.register_file.E == 1:
                p.register_file.D = p.register_file.E = 0
        def decode():
            voice = read(p, sym, 'wCurChannel')[0] + 1
            if voice not in effect['channels']:
                return
            pointer = read(p, sym, f'wChannel{voice}MusicAddress', 2)
            actual = (read(p, sym, f'wChannel{voice}MusicBank')[0],
                      pointer[0] | pointer[1] << 8)
            if actual == sym[f"{effect['header']}_Ch{voice}"]:
                state['voices'].add(voice)
        safe_hook(p, sym, 'PlaySFX', trigger, errors)
        safe_hook(p, sym, 'GetMusicByte', decode, errors)
        if not mixed:
            safe_hook(p, sym, 'PlayMusic', silence, errors)
        try:
            for frame in range(400):
                state['frame'] = frame; p.tick(1, True, True)
                if state['started'] is None:
                    continue
                arrays.append(p.sound.ndarray.copy())
                active = [read(p, sym, f'wChannel{i}Flags1')[0] & 1 for i in range(5, 9)]
                if not any(active) and frame > state['started']:
                    state['ended'] = frame
                    break
            assert not errors, errors
            assert state['ended'] is not None, (effect['name'], 'Never stopped')
            assert state['voices'] == set(effect['channels']), (effect['name'], state)
            elapsed = state['ended'] - state['started']
            assert 1 <= elapsed <= 42, (effect['name'], elapsed)
            for _ in range(6):
                p.tick(1, True, True); arrays.append(p.sound.ndarray.copy())
            result = write_audio(SFX_OUT / (effect['name'] + ('_mixed' if mixed else '') + '.wav'), arrays)
            audible = 0
            if mixed:
                for _ in range(120):
                    p.tick(1, True, True)
                    channels = all(read(p, sym, f'wChannel{i}Flags1')[0] & 1 for i in range(1, 5))
                    no_sfx = not any(read(p, sym, f'wChannel{i}Flags1')[0] & 1 for i in range(5, 9))
                    audible += bool(channels and no_sfx and np.ptp(p.sound.ndarray.astype('int16')))
                assert audible >= 6, ('Music flags alone are insufficient', effect['name'])
            assert not errors, errors
            return result | {'name': effect['name'], 'sfx_id': effect_id,
                             'native_voices_observed': sorted(state['voices']),
                             'terminated_frames': elapsed,
                             'music_restored_audible_frames': audible,
                             'diagnostic_temporary_title_CALL_fixture': True,
                             'production_rom_unmodified': True}
        finally:
            p.stop(save=False)


class AudioBoy:
    def __init__(self, raw, session):
        self.raw, self.session = raw, session
    def __getattr__(self, name):
        return getattr(self.raw, name)
    def tick(self, count=1, render=True, sound=True):
        result = None
        for _ in range(count):
            result = self.raw.tick(1, render, True)
            self.session.after_frame()
        return result


class AudioSession(BagSession):
    def __init__(self, rom, sym, effects, ids):
        self.effects = {ids[e['existing_sfx_id']]: e for e in effects}
        self.records, self.current, self.pending_audio = [], None, []
        self.frame, self.hook_errors = 0, []
        self.gold_events, self.gold_active = [], None
        self.music_decoded, self.music_selections = set(), []
        super().__init__(rom, sym)
    def open(self):
        # Retain BagSession's native menu observers, then replace the silent
        # emulator it constructs with a sound-emulated instance before boot.
        BagSession.open(self)
        self.p.stop(save=False)
        raw = PyBoy(str(self.rom), window='null', sound_emulated=True,
                    sound_sample_rate=48000, log_level='ERROR')
        raw.set_emulation_speed(0); self.p = AudioBoy(raw, self)
        for label, attr in [('MoveSelectionScreen', 'move_menus'),
                            ('LoadTrainerOrWildMonPic', 'encounter_loads'), ('HealParty', 'heal_calls')]:
            safe_hook(raw, self.sym, label, lambda a=attr: setattr(self, a, getattr(self, a) + 1), self.hook_errors)
        callbacks = {'LoadBattleMenu': lambda: self.battle_menu(None),
                     'StaticMenuJoypad': lambda: self.static_ready(None),
                     'PeonInterfaceWait': lambda: self.bags_ready(None),
                     'VerticalMenu': lambda: self.vertical_menu(None),
                     'ReturnFarCall': self.audio_returned,
                     'BattleCommand_UsedMoveText': lambda: self.used_move(None),
                     'PeonDrawBattleTotem.done': lambda: self.drawn(None),
                     'PlaySFX': self.sfx_started, 'PlayStereoSFX': self.sfx_started,
                     'GetMusicByte': self.native_decode,
                     'PlayMusic': self.music_select, '_PlayMusic': self.music_select}
        for label, phase in [('PeonBags', 'bags_drawing'), ('PeonInventory', 'inventory_drawing'),
                             ('PeonInventory.draw', 'inventory_drawing'), ('PeonInventory.input', 'inventory'),
                             ('PeonInventory.used_battle_item', 'using_item')]:
            callbacks[label] = lambda phase=phase: self.set_phase(phase)
        for label, callback in callbacks.items():
            safe_hook(raw, self.sym, label, callback, self.hook_errors)
        for label in ('PeonWorldLevelUpFeedback', 'PeonBattleLevelUpFeedback'):
            safe_hook(raw, self.sym, label, lambda label=label: self.gold_enter(label), self.hook_errors)
        safe_hook(raw, self.sym, 'PeonPlayLevelGlow.Restored', self.gold_restored, self.hook_errors)
        safe_hook(raw, self.sym, 'PeonPlayLevelGlow.Phase', self.gold_phase, self.hook_errors)
    def read(self, name, length=1):
        return read(self.p, self.sym, name, length)
    def capture(self, name):
        self.p.screen.image.save(OUT / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / (name + '_4x.png'))
        print(name, self.map(), self.position(), 'level', self.read('wPartyMon1Level'), flush=True)
    def music_select(self):
        value = self.p.register_file.D << 8 | self.p.register_file.E
        if value in MUSIC_IDS.values():
            self.music_selections.append({'id': value, 'map': self.map(), 'frame': self.frame})
    def sfx_started(self):
        if self.p.register_file.D:
            return
        effect = self.effects.get(self.p.register_file.E)
        if effect is None:
            return
        if self.current:
            self.finish_effect('retriggered_by_next_target')
        self.current = {'name': effect['name'], 'header': effect['header'],
                        'sfx_id': self.p.register_file.E, 'started_frame': self.frame,
                        'battle_mode': self.read('wBattleMode')[0],
                        'enemy_species': self.read('wEnemyMonSpecies')[0],
                        'player_level': self.read('wPartyMon1Level')[0],
                        'voices': set(), 'arrays': []}
    def native_decode(self):
        voice = self.read('wCurChannel')[0] + 1
        pointer = self.read(f'wChannel{voice}MusicAddress', 2)
        actual = (self.read(f'wChannel{voice}MusicBank')[0], pointer[0] | pointer[1] << 8)
        if voice <= 4:
            for name, music_id in MUSIC_IDS.items():
                if actual == self.sym[f'Music_Peon{name}_Ch{voice}.loop']:
                    self.music_decoded.add(music_id)
        elif self.current:
            effect = self.effects[self.current['sfx_id']]
            if voice in effect['channels'] and actual == self.sym[f"{effect['header']}_Ch{voice}"]:
                self.current['voices'].add(voice)
    def finish_effect(self, reason):
        record = self.current; self.current = None
        record['ended_frame'] = self.frame; record['termination_reason'] = reason
        record['native_voices_observed'] = sorted(record.pop('voices'))
        arrays = record.pop('arrays')
        if arrays:
            record.update(write_audio(OUT / f"normal_{len(self.records):02d}_{record['name']}.wav", arrays))
        record['music_restored_audible_frames'] = 0
        self.records.append(record); self.pending_audio.append(record)
    def gold_enter(self, label):
        level_variable = 'wBattleMonLevel' if label == 'PeonBattleLevelUpFeedback' else 'wPartyMon1Level'
        event = {'helper': label, 'frame': self.frame, 'level': self.read(level_variable)[0],
                 'entry_sp': self.p.register_file.SP, 'palette_before': self.read('wOBPals2', 64),
                 'oam_before': self.read('wShadowOAM', 160), 'gold_frames': [],
                 'phase_entries': [], 'pose_images': []}
        self.gold_events.append(event); self.gold_active = event
    def audio_returned(self):
        self.returned(None)
        if self.gold_active and self.p.register_file.SP == self.gold_active['entry_sp'] + 2:
            event = self.gold_active
            event['return_frame'] = self.frame
            event['palette_after'] = self.read('wOBPals2', 64)
            event['oam_after'] = self.read('wShadowOAM', 160)
            self.gold_active = None
    def gold_restored(self):
        if self.gold_active:
            self.gold_active['explicit_restored_phase_observed'] = True
            self.gold_active['palette_at_restored_phase'] = self.read('wOBPals2', 64)
            self.gold_active['oam_at_restored_phase'] = self.read('wShadowOAM', 160)
    def gold_phase(self):
        if self.gold_active:
            self.gold_active['phase_entries'].append(self.frame)
    def gold_pixels(self, objects):
        """Bind actual screen pixels to the current golden OBJ glyphs."""
        palette_bytes = self.read('wOBPals2', 64)[56:64]
        palette = np.array([((w := palette_bytes[i] | palette_bytes[i + 1] << 8) & 31,
                             w >> 5 & 31, w >> 10 & 31) for i in range(0, 8, 2)], dtype='uint8')
        actual = np.asarray(self.p.screen.image.convert('RGB')) >> 3
        matched = 0
        for y, x, tile, attr in objects:
            binary = list(self.p.memory[(attr >> 3) & 1, 0x8000 + tile * 16:0x8010 + tile * 16])
            indexes = np.zeros((8, 8), dtype='uint8')
            for row in range(8):
                for col in range(8):
                    indexes[row, col] = ((binary[row * 2] >> (7 - col)) & 1) | (((binary[row * 2 + 1] >> (7 - col)) & 1) << 1)
            if attr & 0x20:
                indexes = np.fliplr(indexes)
            if attr & 0x40:
                indexes = np.flipud(indexes)
            px, py = x - 8, y - 16
            if not (0 <= px <= 152 and 0 <= py <= 136):
                continue
            wanted = palette[indexes]
            gold = (indexes != 0) & (wanted[:, :, 0] >= 20) & (wanted[:, :, 1] >= 10) & (wanted[:, :, 2] <= 15)
            matched += int(np.count_nonzero(gold & np.all(actual[py:py + 8, px:px + 8] == wanted, axis=2)))
        return matched
    def after_frame(self):
        self.frame += 1
        assert not self.hook_errors, self.hook_errors
        sample = self.p.sound.ndarray.copy()
        active = any(self.read(f'wChannel{i}Flags1')[0] & 1 for i in range(5, 9))
        if self.current:
            self.current['arrays'].append(sample)
            if not active and self.frame > self.current['started_frame'] + 1:
                self.finish_effect('native_sfx_channels_stopped')
        audible = (not active and all(self.read(f'wChannel{i}Flags1')[0] & 1 for i in range(1, 5))
                   and bool(np.ptp(sample.astype('int16'))))
        for record in self.pending_audio:
            if self.frame > record['ended_frame'] + 6 and audible:
                record['music_restored_audible_frames'] += 1
        self.pending_audio = [r for r in self.pending_audio if r['music_restored_audible_frames'] < 6]
        if self.gold_active:
            event = self.gold_active
            hardware = list(self.p.memory[0xfe00:0xfea0])
            objects = [hardware[i:i + 4] for i in range(0, 160, 4)
                       if hardware[i + 2] in (0x6e, 0x6f) and hardware[i + 3] & 7 == 7 and hardware[i]]
            if objects:
                pixels = self.gold_pixels(objects)
                event['gold_frames'].append({'frame': self.frame, 'objects': objects,
                                            'actual_gold_rgb555_pixels_matching_native_glyphs': pixels})
                if (pixels and len(event['pose_images']) < len(event['phase_entries'])
                        and self.frame >= event['phase_entries'][-1] + 2):
                    event['pose_images'].append(self.p.screen.image.copy())
                if len(event['gold_frames']) == 9:
                    self.capture('normal_level_up_gold_' + str(len(self.gold_events)))
            assert self.frame < event['frame'] + 120, ('Gold helper did not return', event)
    def cue_count(self, name):
        return sum(r['name'] == name for r in self.records) + bool(self.current and self.current['name'] == name)
    def assert_cue_delta(self, name, before, expected=1):
        self.p.tick(180, True)
        assert self.cue_count(name) == before + expected, (name, before, self.cue_count(name), expected)
    def hearth(self):
        self.press('start')
        for _ in range(8):
            if self.read('wMenuCursorPosition') == [1]:
                break
            self.press('up', 30)
        assert self.read('wMenuCursorPosition') == [1]
        for _ in range(4):
            self.press('down', 30)
        self.press('a')
        self.wait(lambda: self.map() == 23 and self.read('wScriptMode') == [0], buttons=True)
        assert self.position() == (5, 6)


def normal_gameplay(rom, sym, effects, ids):
    # Only process-local compatibility of the retained Python helpers changes.
    # Native game state is never injected or restored in this route.
    adapter.adapt_v023_gameplay(quests)
    s = AudioSession(rom, sym, effects, ids)
    report = {'normal_buttons_only': True, 'ram_edits': False,
              'emulator_savestates_loaded': False, 'cases': {}}
    try:
        s.fresh(); report['initial_level'] = s.read('wPartyMon1Level')[0]
        s.merchant(potion=True)
        assert s.item_quantity(POTION) == 1
        s.watch = True
        before = s.cue_count('quest_accept')
        s.talk((10, 10), 'up', 'normal_first_quest_accept')
        s.assert_cue_delta('quest_accept', before)
        report['cases']['quest_accept'] = True
        level_before = s.read('wPartyMon1Level')[0]
        s.navigate((18, 13)); s.press('up', 30); s.press('a', 60)
        s.wait(lambda: s.phase == 'battle', buttons=True)
        before = s.cue_count('totem_place')
        placement = s.use_item(TOTEM, True)
        assert placement['after']['active'] == 1 and placement['after']['totems'] == 1
        s.assert_cue_delta('totem_place', before)
        report['cases']['totem_place'] = placement
        # Placement gives the boar one real attack, so healing has a real wound.
        assert s.word('wBattleMonHP') < s.word('wBattleMonMaxHP')
        before = s.cue_count('potion')
        potion = s.use_item(POTION, True)
        assert potion['after']['potions'] == 0
        s.assert_cue_delta('potion', before)
        report['cases']['successful_potion'] = potion
        s.press('up', 30)  # Return the native 2x2 menu from BAGS to FIGHT.
        s.fight('normal_audio_boar', 'EVENT_PEON_QUEST_DONE')
        assert s.read('wBattleResult') == [0]
        s.phase, s.context = 'overworld', None
        report['cases']['no_false_ding_on_boar_without_level_gain'] = {
            'before': level_before, 'after': s.read('wPartyMon1Level')[0],
            'ding_count': s.cue_count('level_up')}
        assert s.read('wPartyMon1Level')[0] == level_before and s.cue_count('level_up') == 0
        assert s.cue_count('quest_ready') >= 1
        before, ding_before, xp_before = s.cue_count('quest_reward'), s.cue_count('level_up'), s.experience()
        s.talk((10, 10), 'up', 'normal_first_quest_reward')
        # A real level gain intentionally replaces the lesser reward fanfare.
        s.assert_cue_delta('level_up', ding_before)
        s.assert_cue_delta('quest_reward', before, 0)
        assert s.experience() == xp_before + 15 and s.read('wPartyMon1Level')[0] > level_before
        report['cases']['quest_level_gain_uses_one_ding_instead_of_stacked_fanfare'] = True
        before = s.cue_count('healing')
        s.rest(); s.assert_cue_delta('healing', before)
        assert s.event('EVENT_PEON_HEARTH_GRANTED')
        report['cases']['inn_rest'] = True
        # Lazy Peons also supplies a real overworld XP reward to exercise the
        # quest cue even when this particular threshold does not gain a level.
        s.talk((8, 16), 'up', 'normal_lazy_accept')
        s.talk((5, 17), 'up', 'normal_lazy_wake')
        xp_before = s.experience(); before = s.cue_count('quest_reward')
        s.talk((8, 16), 'up', 'normal_lazy_reward')
        s.assert_cue_delta('quest_reward', before)
        assert s.experience() > xp_before
        before = s.cue_count('quest_reward'); xp_before = s.experience()
        dings_before, gold_before = s.cue_count('level_up'), len(s.gold_events)
        s.talk((8, 16), 'up', 'normal_no_repeat_quest_reward')
        s.assert_cue_delta('quest_reward', before, 0)
        assert s.experience() == xp_before
        assert s.cue_count('level_up') == dings_before and len(s.gold_events) == gold_before
        report['cases']['completed_quest_does_not_repeat_reward_audio_or_xp'] = True
        # Two stronger real road scorpids produce an actual battle level gain;
        # the opening level-one boar alone deliberately does not.
        s.talk((10, 10), 'up', 'normal_scorpid_quest_accept')
        s.navigate((17, 15)); s.fight('normal_audio_den_scorpid', 'EVENT_PEON_SCORPID_DEFEATED')
        assert s.read('wBattleResult') == [0]
        s.phase, s.context = 'overworld', None
        s.talk((10, 10), 'up', 'normal_scorpid_quest_reward'); s.rest()
        level_before = s.read('wPartyMon1Level')[0]
        s.to_valley(); s.navigate((28, 12), expected_map=16)
        s.navigate((16, 17)); s.fight('normal_audio_road_pair', 'EVENT_PEON_ROAD_SCORPID_PACK_DEAD')
        assert s.read('wBattleResult') == [0] and s.read('wPartyMon1Level')[0] > level_before
        s.phase, s.context = 'overworld', None
        report['cases']['actual_battle_level_gain'] = {'before': level_before, 'after': s.read('wPartyMon1Level')[0]}
        s.go_den()
        s.to_valley(); s.p.tick(180, True)
        assert MUSIC_IDS['Durotar'] in s.music_decoded
        before = s.cue_count('hearthstone')
        s.hearth(); s.assert_cue_delta('hearthstone', before)
        assert MUSIC_IDS['Inn'] in s.music_decoded
        report['cases']['hearthstone_native_return'] = True
        s.navigate((5, 7), expected_map=14)
        from validate_peon_ambient_music import warp_for
        s.to_valley()
        # The first hostile imp guards the only safe approach to the cave.
        # Fight it normally instead of bypassing either collisions or aggro.
        s.navigate((24, 6)); s.fight('normal_audio_cave_guard', 'EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD')
        assert s.read('wBattleResult') == [0]
        s.phase, s.context = 'overworld', None
        s.navigate(warp_for('ValleyOfTrials', 'BURNING_BLADE_CAVERN'), expected_map=20)
        s.p.tick(180, True)
        dings_before, gold_before = s.cue_count('level_up'), len(s.gold_events)
        report['normal_battery_restart'] = s.cold_restart()
        assert s.cue_count('level_up') == dings_before and len(s.gold_events) == gold_before
        report['continue_does_not_falsely_ding_or_glow'] = True
        s.p.tick(180, True)
        assert MUSIC_IDS['Cave'] in s.music_decoded
        report['cases']['three_ambiences_selected_and_native_decoder_observed'] = sorted(s.music_decoded)
        s.p.tick(180, True)
        assert not s.hook_errors and s.current is None
        for record in s.records:
            expected = s.effects[record['sfx_id']]['channels']
            assert record['native_voices_observed'] == expected, (record['name'], record)
            assert record['termination_reason'] == 'native_sfx_channels_stopped', record
            assert record['music_restored_audible_frames'] >= 6, record
        assert s.gold_events and any(e['helper'] == 'PeonBattleLevelUpFeedback' for e in s.gold_events)
        ding = [r for r in s.records if r['name'] == 'level_up']
        assert len(ding) == len(s.gold_events), (ding, s.gold_events)
        rendered = 0
        for event in s.gold_events:
            poses = event.pop('pose_images')
            if event['gold_frames']:
                rendered += 1
                assert len(event['phase_entries']) == 6, ('Expected six native poses', event)
                assert max(f['actual_gold_rgb555_pixels_matching_native_glyphs'] for f in event['gold_frames']) > 0, ('No actual golden screen pixels', event)
                assert event['explicit_restored_phase_observed']
                assert len(poses) == 6, ('Six visible native pose captures required', event)
                image = Image.new('RGB', (160 * 6, 144))
                for i, pose in enumerate(poses):
                    image.paste(pose, (i * 160, 0))
                filename = f"normal_{event['helper']}_level_{event['level']}_six_gold_poses.png"
                image.save(OUT / filename); event['six_native_pose_contact_sheet'] = filename
            assert event['palette_after'] == event['palette_before'], ('Palette not restored', event)
            assert event['oam_after'] == event['oam_before'], ('Native OAM not restored', event)
            assert sum(r['started_frame'] >= event['frame'] and r['started_frame'] <= event['frame'] + 2 for r in ding) == 1
        assert rendered > 0, 'No ordinary level gain rendered native gold pixels'
        report.update(sound_events=s.records, gold_level_up_events=s.gold_events,
                      actual_level_gains_each_play_one_ding=True,
                      native_gold_hardware_oam_observed=True,
                      native_gold_effects_rendered=rendered,
                      gold_visuals_skipped_in_crowded_world_or_scenes_off=len(s.gold_events) - rendered,
                      music_selections=s.music_selections, observer_errors=s.hook_errors)
        report['coverage_limit'] = 'Later spell/enemy cues have isolated native APU and source-routing checks; this button route covers the opening chapter only.'
        return report
    finally:
        s.p.stop(save=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--section', choices=('all', 'sfx', 'music', 'normal'), default='all')
    parser.add_argument('--expected-sha', required=True)
    parser.add_argument('--music-report', type=Path, default=MUSIC_OUT / 'validation.json')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    for folder in (OUT, SFX_OUT, MUSIC_OUT):
        folder.mkdir(parents=True, exist_ok=True)
    production = ROOT / 'pokecrystal.gbc'
    assert sha(production) == args.expected_sha, 'Expected a frozen root-approved candidate'
    before = published_snapshot(); effects = json.loads(SFX_DESIGN.read_text())['effects']
    ids, sym = sfx_ids(), load_symbols()
    assert len(effects) == 19 and all(ids[e['existing_sfx_id']] == e['sfx_id'] for e in effects)
    assert ids['SFX_PEON_BOAR_GRUNT'] == 0xcf and ids['SFX_PEON_LEVEL_UP'] == 0xd0
    report = {'rom_sha256': args.expected_sha, 'section': args.section, 'all_checks_passed': False,
              'source': 'Original GBC pulse/noise compositions; no external Warcraft samples auditioned or imported.',
              'physical_chromatic_audio_unverified': True}
    try:
        with tempfile.TemporaryDirectory(prefix='peon-audio-expansion-') as directory:
            frozen = Path(directory) / 'frozen.gbc'; shutil.copyfile(production, frozen)
            if args.section in ('all', 'sfx'):
                report['sound_effects'] = []
                for effect in effects:
                    isolated = record_effect(frozen, sym, effect, ids[effect['existing_sfx_id']])
                    mixed = record_effect(frozen, sym, effect, ids[effect['existing_sfx_id']], True)
                    report['sound_effects'].append({'isolated': isolated, 'mixed': mixed})
                    print('SFX passed:', effect['name'], flush=True)
            if args.section in ('all', 'music'):
                music = json.loads(args.music_report.read_text())
                assert music['rom_sha256'] == args.expected_sha and music['all_checks_passed']
                assert len(music['tracks']) == 7 and music['source_matches_refinement']
                for name, native_id in MUSIC_IDS.items():
                    track = music['tracks'][name]
                    assert track['native_music_id'] == native_id and track['native_four_channel_apu_capture']
                    assert track['phrase_entries_per_channel'] == [3] * 4
                    assert track['native_audio_metrics']['raw_mixer_limit_samples'] == 0
                report['music_validation'] = {
                    'independent_native_report': str(args.music_report.relative_to(ROOT)),
                    'report_sha256': sha(args.music_report),
                    'same_rom_sha256': music['rom_sha256'],
                    'all_checks_passed': True,
                    'no_duplicate_capture': True,
                }
            if args.section in ('all', 'normal'):
                report['ordinary_gameplay'] = normal_gameplay(frozen, sym, effects, ids)
        assert sha(production) == args.expected_sha, 'Production ROM changed during validation'
        assert published_snapshot() == before, 'Published evidence was modified'
        report.update(all_checks_passed=True, production_rom_unchanged=True, published_evidence_unchanged=True)
    except Exception as error:
        report['failure'] = repr(error)
        (OUT / (args.section + '_validation.json')).write_text(json.dumps(report, indent=2) + '\n')
        raise
    (OUT / (args.section + '_validation.json')).write_text(json.dumps(report, indent=2) + '\n')
    print('PASS', args.section, args.expected_sha, flush=True)


if __name__ == '__main__':
    main()
