#!/usr/bin/env python3
"""Verify the two valley sound effects in diagnostic and ordinary play.

The isolated APU previews reuse the explicitly labelled temporary title CALL
fixture. The playable proof uses an unmodified ROM, ordinary buttons and
read-only observers: no RAM edits, CPU substitutions or emulator states.
"""
import hashlib
import json
import logging
import shutil
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from pyboy import PyBoy

import validate_peon_sfx as diagnostic
from validate_durotar_v022_quests import QuestSession
from validate_peon_villages import load_symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/valley_layout_update/sound_effects'


class AudioBoy:
    """Retain every actual APU frame during the existing button helpers."""
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


class AudioSession(QuestSession):
    def __init__(self, rom, sym, effects, ids):
        self.effects = {ids[e['existing_sfx_id']]: e for e in effects}
        self.records, self.current, self.pending = [], None, []
        self.frame = 0
        self.intros = []
        super().__init__(rom, sym)

    def open(self):
        raw = PyBoy(str(self.rom), window='null', sound_emulated=True,
                    sound_sample_rate=48000, log_level='ERROR')
        raw.set_emulation_speed(0)
        self.p = AudioBoy(raw, self)
        for label, attr in [('MoveSelectionScreen', 'move_menus'),
                            ('LoadTrainerOrWildMonPic', 'encounter_loads'),
                            ('HealParty', 'heal_calls')]:
            raw.hook_register(*self.sym[label],
                lambda name: setattr(self, name, getattr(self, name) + 1), attr)
        raw.hook_register(*self.sym['PlaySFX'], lambda _: self.sfx_started(), None)
        # Native anim_sound uses this ROMX entry directly, bypassing PlaySFX.
        raw.hook_register(*self.sym['PlayStereoSFX'], lambda _: self.sfx_started(), None)
        raw.hook_register(*self.sym['GetMusicByte'], lambda _: self.native_voice(), None)
        raw.hook_register(*self.sym['PeonEncounterStartMessage'],
            lambda _: self.intros.append({'species': self.read('wEnemyMonSpecies')[0],
                                         'frame': self.frame}), None)

    def capture(self, name):
        self.p.screen.image.save(OUT / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(
            OUT / (name + '_4x.png'))
        print(name, self.map(), self.position(), flush=True)

    def sfx_started(self):
        if self.p.register_file.D:
            return
        effect = self.effects.get(self.p.register_file.E)
        if effect is None:
            return
        if self.current is not None:
            self.current['retriggered_by_next_target_effect'] = True
            self.finish_effect('retriggered')
        self.current = {
            'name': effect['name'], 'header': effect['header'],
            'sfx_id': self.p.register_file.E, 'started_frame': self.frame,
            'enemy_species': self.read('wEnemyMonSpecies')[0],
            'player_move': self.read('wCurPlayerMove')[0],
            'battle_mode': self.read('wBattleMode')[0],
            'voices': set(), 'arrays': [],
        }

    def native_voice(self):
        if self.current is None:
            return
        voice = self.read('wCurChannel')[0] + 1
        if voice not in (5, 8):
            return
        bank, address = self.sym[f"{self.current['header']}_Ch{voice}"]
        pointer = self.read(f'wChannel{voice}MusicAddress', 2)
        if (self.read(f'wChannel{voice}MusicBank')[0] == bank
                and int.from_bytes(bytes(pointer), 'little') == address):
            self.current['voices'].add(voice)

    def finish_effect(self, reason):
        record = self.current
        record['ended_frame'] = self.frame
        record['observed_frames'] = self.frame - record['started_frame']
        record['end_reason'] = reason
        record['native_voices_observed'] = sorted(record.pop('voices'))
        arrays = record.pop('arrays')
        if arrays and record['native_voices_observed']:
            native = np.concatenate(arrays)
            record['native_apu_peak_before_preview_gain'] = int(np.abs(native.astype('int16')).max())
            record['native_apu_clipped_samples'] = int(np.sum((native == 127) | (native == -128)))
            index = sum(r['name'] == record['name'] for r in self.records) + 1
            filename = f"{record['name']}_ordinary_{index:02d}.wav"
            record['preview_gain'] = diagnostic.wav(OUT / filename, arrays)
            record['actual_apu_wav'] = filename
        self.records.append(record)
        self.pending.append(record)
        self.current = None

    def after_frame(self):
        self.frame += 1
        samples = self.p.sound.ndarray.copy()
        active = [self.read(f'wChannel{i}Flags1')[0] & 1 for i in range(5, 9)]
        if self.current is not None:
            self.current['arrays'].append(samples)
            if self.frame - self.current['started_frame'] == 12:
                name = self.current['name'] + '_native_effect_in_combat'
                if not (OUT / (name + '.png')).exists():
                    self.capture(name)
            if not any(active) and self.frame > self.current['started_frame'] + 1:
                self.finish_effect('native_sfx_channels_stopped')
        music = all(self.read(f'wChannel{i}Flags1')[0] & 1 for i in range(1, 5))
        audible = samples.size and np.max(samples) > np.min(samples)
        for record in self.pending:
            if record.get('music_resumes_after_effect'):
                continue
            # Set music flags alone cannot prove audible restoration: they stay
            # active under an SFX. Require six later APU frames with no SFX.
            if music and audible and not any(active) and self.frame > record['ended_frame']:
                record['pure_music_apu_frames_observed'] = record.get('pure_music_apu_frames_observed', 0) + 1
            if record.get('pure_music_apu_frames_observed', 0) >= 6:
                record['music_resumes_after_effect'] = True
                record['music_observed_frame'] = self.frame


def ordinary_combat(effects, ids):
    session = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-valley-sfx-buttons-') as directory:
            rom = Path(directory) / 'test.gbc'
            shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            session = AudioSession(rom, load_symbols(), effects, ids)
            session.fresh()
            session.talk((10, 10), 'up', 'gornek_before_audio')
            session.navigate((18, 13))
            session.press('up', 30)
            session.press('a')
            boar = session.fight('ordinary_boar_audio', 'EVENT_PEON_QUEST_DONE')
            assert boar['outcome'] == 0, ('ordinary boar was not defeated', boar)
            session.p.tick(180, True)
            grunts = [r for r in session.records if r['name'] == 'boar_grunt']
            bolts = [r for r in session.records if r['name'] == 'lightning_bolt']
            assert len(grunts) == 1, ('expected one ordinary boar grunt', grunts)
            assert grunts[0]['enemy_species'] == 19 and grunts[0]['battle_mode'] == 1
            assert bolts and all(r['player_move'] == 84 for r in bolts), bolts
            assert all(r['native_voices_observed'] == [5, 8] for r in grunts + bolts)
            assert all(r.get('music_resumes_after_effect') for r in grunts + bolts)
            assert all(1 <= r['observed_frames'] <= 42 for r in grunts + bolts)
            assert any(r['end_reason'] == 'native_sfx_channels_stopped' for r in bolts)
            session.talk((10, 10), 'up', 'gornek_before_scorpid_audio')
            session.rest()
            session.navigate((17, 15))
            scorpid = session.fight('ordinary_scorpid_audio', 'EVENT_PEON_SCORPID_DEFEATED')
            assert scorpid['outcome'] == 0, scorpid
            session.p.tick(180, True)
            assert len([r for r in session.records if r['name'] == 'boar_grunt']) == 1
            assert [r['species'] for r in session.intros] == [19, 27], session.intros
            assert session.current is None
            assert all(r['native_voices_observed'] == [5, 8] for r in session.records)
            assert all(r.get('music_resumes_after_effect') for r in session.records)
            assert all(1 <= r['observed_frames'] <= 42 for r in session.records)
            assert all(r['native_apu_clipped_samples'] == 0 for r in session.records)
            result = {
                'normal_buttons_only': True, 'ram_edits': False,
                'cpu_register_substitution': False, 'emulator_states_loaded': False,
                'production_rom_modified': False,
                'encounter_intros': session.intros,
                'boar_only_grunt_observed': True,
                'non_boar_intro_did_not_play_grunt': True,
                'actual_lightning_move_id': 84,
                'battle_results': [boar, scorpid], 'effects': session.records,
            }
            session.p.stop(save=False)
            return result
    except Exception:
        if session is not None:
            session.capture('unexpected_audio_state')
            (OUT / 'ordinary_failure_state.json').write_text(json.dumps({
                'frame': session.frame, 'effects': session.records,
                'intros': session.intros,
                'battle_mode': session.read('wBattleMode'),
                'map': session.map(), 'position': session.position()}, indent=2) + '\n')
            session.p.stop(save=False)
        raise


def main():
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'rom_sha256': hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest(),
              'all_checks_passed': False,
              'preview_source': 'Actual native emulator APU; no sampled WoW audio.',
              'source_limitation': 'Original pulse/noise authoring; Wowhead recordings unavailable and not auditioned.',
              'physical_console_audio_unverified': True}
    old_out = diagnostic.OUT
    try:
        diagnostic.OUT = OUT
        syms, ids = diagnostic.symbols(), diagnostic.sfx_ids()
        assert ids['SFX_PEON_BOAR_GRUNT'] == 0xcf and len(ids) == 208
        effects = json.loads((OUT / 'design.json').read_text())['effects']
        for effect in effects:
            (OUT / (effect['name'] + '_native_effect_in_combat.png')).unlink(missing_ok=True)
            (OUT / (effect['name'] + '_native_effect_in_combat_4x.png')).unlink(missing_ok=True)
        records = []
        for effect in effects:
            isolated = diagnostic.record_effect(effect, syms, ids)
            mixed = diagnostic.record_effect(effect, syms, ids, music=True)
            isolated.pop('music_resumes')
            isolated['music_resumes_after_effect'] = mixed['music_resumes']
            records.append(isolated)
            print(effect['name'], isolated['terminated_frames'], 'native frames', flush=True)
        report['diagnostic_effects'] = records
        report['ordinary_combat'] = ordinary_combat(effects, ids)
        report['all_checks_passed'] = True
        for name in ('unexpected_audio_state.png', 'unexpected_audio_state_4x.png', 'ordinary_failure_state.json'):
            (OUT / name).unlink(missing_ok=True)
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        diagnostic.OUT = old_out
        (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
