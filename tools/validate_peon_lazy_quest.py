#!/usr/bin/env python3
"""Exercise Lazy Peons, neutral wildlife and campfire through normal buttons.

Starts a fresh character in an isolated ROM copy. No RAM edits, diagnostic
calls or emulator states pass the quest or save flow. Inspection is read-only.
"""
import hashlib
import json
import logging
import shutil
import tempfile
from pathlib import Path

from PIL import Image

from validate_peon_villages import Session, load_symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/lazy_quest_validation'


def event_indices():
    result, index = {}, 0
    for line in (ROOT / 'constants/event_flags.asm').read_text().splitlines():
        parts = line.split(';')[0].split()
        if not parts:
            continue
        if parts[0] == 'const_def':
            index = int(parts[1]) if len(parts) > 1 else 0
        elif parts[0] == 'const_next':
            index = int(parts[1])
        elif parts[0] == 'const_skip':
            index += int(parts[1]) if len(parts) > 1 else 1
        elif parts[0] == 'const':
            result[parts[1]] = index
            index += 1
    return result


class LazySession(Session):
    def capture(self, name):
        self.p.screen.image.save(OUT / f'{name}.png')
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / f'{name}_4x.png')
        print(name, self.map(), self.position(), flush=True)

    def snapshot(self):
        return self.state() | {'wEventFlags': self.read('wEventFlags', 40),
                              'wNumKeyItems': self.read('wNumKeyItems')}

    def save_cold_restart(self):
        # Move away from the interactive fire before using menu confirmations.
        # Otherwise a surplus A after saving can start another rest dialogue.
        self.navigate((12, 9))
        self.press('down', 30)
        before = self.snapshot()
        self.press('start')
        for _ in range(10):
            if self.read('wMenuCursorPosition')[0] <= 1:
                break
            self.press('up', 30)
        for _ in range(3):
            self.press('down', 30)
        self.press('a')
        for _ in range(5):
            self.press('a', 180)
        self.capture('lazy_quest_saved')
        self.p.stop(save=True)
        assert Path(str(self.rom) + '.ram').stat().st_size == 32768
        self.open()
        self.p.tick(1800, True)
        self.press('start')
        for _ in range(12):
            if self.map() == 14 and self.read('wScriptMode') == [0]:
                break
            self.press('a', 180)
        self.p.tick(180, True)
        assert self.map() == 14 and self.read('wScriptMode') == [0]
        after = self.snapshot()
        assert before == after, ('lazy quest battery-save mismatch', before, after)
        self.capture('lazy_quest_cold_restart')
        return {'before': before, 'after': after, 'passed': True}


def main():
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    symbols, flags = load_symbols(), event_indices()
    results = {'rom_sha256': hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest(),
               'normal_buttons_only': True, 'ram_edits': False,
               'emulator_states_loaded': False}
    s = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-lazy-quest-') as directory:
            rom = Path(directory) / 'test.gbc'
            shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = LazySession(rom, symbols)
            observed = {'wake_impacts': 0, 'heal_calls': 0}

            def effect(context):
                if (s.map() == 14 and s.p.register_file.D == 0 and s.p.register_file.E == 0x31):
                    context['wake_impacts'] += 1

            s.p.hook_register(*symbols['PlaySFX'], effect, observed)
            s.p.hook_register(*symbols['HealParty'],
                              lambda state: state.__setitem__('heal_calls', state['heal_calls'] + 1), observed)

            def event(name):
                i = flags[name]
                return bool(s.read('wEventFlags', i // 8 + 1)[i // 8] & (1 << (i % 8)))

            def interact(position, direction, label, speaker=None):
                s.navigate(position)
                before = s.position()
                s.press(direction, 30)
                assert s.position() == before, ('Actor/prop did not block facing', label, before, s.position())
                s.press('a', 120)
                assert s.read('wScriptMode') != [0], (label, 'no dialogue')
                if speaker is not None:
                    last_talked = s.p.memory[symbols['hLastTalked'][1]]
                    assert last_talked == speaker, (label, 'wrong speaker', last_talked)
                s.capture(label)
                s.close_dialogue()
                assert s.read('wBattleMode') == [0], label + ' unexpectedly began combat'

            s.p.tick(1800, False)
            s.press('start')
            s.press('down')
            s.press('a')
            for _ in range(180):
                if s.map() == 14 and s.read('wScriptMode') == [0]:
                    break
                s.press('a')
            assert s.read('wMapGroup', 2) == [26, 14] and s.read('wScriptMode') == [0]
            s.capture('fresh_den_more_npcs')
            assert all(not event(name) for name in ('EVENT_PEON_LAZY_ACCEPTED',
                       'EVENT_PEON_LAZY_AWAKE', 'EVENT_PEON_LAZY_DONE'))
            initial_money = s.money()
            neutral = []
            for index, position, label in ((10, (6, 16), 'yellow_boar_west'),
                                            (11, (14, 16), 'yellow_boar_south')):
                s.navigate(position)
                s.p.tick(240, True)
                assert s.read('wBattleMode') == [0], label + ' aggroed by proximity'
                runtime_index = s.read(f'wMap{index}ObjectStructID')[0]
                assert runtime_index < 13, (label, 'NPC not allocated')
                assert s.read(f'wObject{runtime_index}Palette')[0] & 7 == 4, label + ' not yellow palette'
                interact(position, 'up', label, index)
                assert s.money() == initial_money
                neutral.append({'actor': index, 'position': list(position), 'yellow_palette': True,
                                'no_proximity_aggro': True, 'interaction_flavor_only': True})
            results['neutral_yellow_boars'] = neutral
            interact((5, 17), 'up', 'lazy_peon_before_quest', 8)
            assert not event('EVENT_PEON_LAZY_AWAKE') and observed['wake_impacts'] == 0
            # Click the marker above Foreman, testing the actual NPC portrait attribution.
            interact((8, 13), 'down', 'foreman_marker_offer', 7)
            assert event('EVENT_PEON_LAZY_ACCEPTED') and not event('EVENT_PEON_LAZY_AWAKE')
            assert s.money() == initial_money
            interact((8, 16), 'up', 'foreman_waiting_for_worker', 7)
            assert not event('EVENT_PEON_LAZY_DONE')
            interact((5, 17), 'up', 'lazy_peon_awakened', 8)
            assert event('EVENT_PEON_LAZY_AWAKE') and observed['wake_impacts'] == 1
            interact((5, 17), 'up', 'lazy_peon_working_repeat', 8)
            assert observed['wake_impacts'] == 1, 'Worker wake impact repeated'
            interact((8, 16), 'up', 'foreman_reward', 7)
            assert event('EVENT_PEON_LAZY_DONE') and s.money() == initial_money + 100
            assert s.read('wMap9ObjectStructID') == [255], 'Completed quest marker remains allocated'
            for _ in range(2):
                interact((8, 16), 'up', 'foreman_thanks_repeat', 7)
                assert s.money() == initial_money + 100, 'Quest reward repeated'
            results['lazy_peons'] = {'accepted': True, 'one_worker_awakened': True,
                                    'one_wake_impact': True, 'reward_copper': 100,
                                    'reward_only_once': True, 'marker_hidden_after_done': True,
                                    'marker_uses_foreman_speaker': True}
            heals = observed['heal_calls']
            interact((12, 8), 'up', 'campfire_rest', 0)
            assert observed['heal_calls'] == heals
            # The fire is scenery in v0.2.2; it must not invoke free restoration.
            results['campfire'] = {'ordinary_prop_interaction': True,
                                   'no_false_npc_speaker': True, 'no_free_restoration': True}
            results['save_cold_restart'] = s.save_cold_restart()
            assert all(event(name) for name in ('EVENT_PEON_LAZY_ACCEPTED',
                       'EVENT_PEON_LAZY_AWAKE', 'EVENT_PEON_LAZY_DONE'))
            assert s.money() == initial_money + 100
            assert s.read('wMap9ObjectStructID') == [255]
            results['all_checks_passed'] = True
            s.p.stop(save=False)
            s = None
    except Exception as exc:
        results['all_checks_passed'] = False
        results['failure'] = repr(exc)
        if s is not None:
            s.capture('unexpected_state')
            s.p.stop(save=False)
        (OUT / 'validation.json').write_text(json.dumps(results, indent=2) + '\n')
        raise
    results['limitations'] = ['One worker instead of Classic five; mace replaces quest blackjack.',
                             'The two added neutral boars are flavor NPCs, not combat/loot targets.',
                             'Physical Chromatic play remains untested.']
    (OUT / 'validation.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
