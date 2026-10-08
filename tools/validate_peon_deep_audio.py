#!/usr/bin/env python3
"""Repeat real gameplay audio/level aura checks on the polished candidate."""
import argparse
import json
import sys
from pathlib import Path

import run_peon_v023_validation as adapter
import validate_peon_audio_expansion as audio

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/deep_polish/audio'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-sha', required=True)
    args = parser.parse_args()
    for module in adapter.local_dependencies(audio):
        for key in ('OUT', 'OUTPUT'):
            if hasattr(module, key):
                setattr(module, key, OUT)
    audio.OUT = OUT
    audio.SFX_OUT = OUT / 'sounds'
    audio.MUSIC_OUT = OUT / 'music'
    recoveries = []
    def go_den_with_actual_poison_recovery(self):
        gold, xp = self.money(), self.experience()
        home = {n: self.event('EVENT_PEON_' + n) for n in
                ('HEARTH_GRANTED', 'HOME_DEN', 'HOME_SENJIN', 'HOME_RAZOR')}
        try:
            return audio.quests.QuestSession.go_den(self)
        except AssertionError:
            # Ordinary walking after two scorpids can really kill a poisoned
            # peon. The original navigation helper cannot dismiss that text.
            # Accept only this native failure state; never bypass collision.
            if self.read('wScriptMode') == [0] or self.read('wPartyMon1HP', 2) != [0, 0]:
                raise
            self.capture('normal_poison_defeat_dialogue')
            self.close_dialogue()
            assert self.map() == 23 and self.read('wPartyMon1HP', 2) == [0, 1]
            assert self.read('wPartyMon1Status') == [0]
            assert self.money() == gold and self.experience() == xp
            assert home == {n: self.event('EVENT_PEON_' + n) for n in home}
            self.capture('normal_poison_defeat_returns_to_bound_inn')
            recoveries.append({'normal_buttons_only': True, 'native_poison_walk_defeat': True,
                               'bound_inn': self.map(), 'one_hp': True, 'status_cleared': True,
                               'gold_xp_home_binding_preserved': True})
            # Defeat and Hearthstone do not heal. Deliberately ask the real
            # innkeeper before continuing the audio route toward the cave.
            self.talk((6, 5), 'up', 'normal_deliberate_rest_after_poison_defeat')
            assert self.read('wPartyMon1HP', 2) == self.read('wPartyMon1MaxHP', 2)
            recoveries[-1]['deliberate_innkeeper_rest_after_recovery'] = True
            return audio.quests.QuestSession.go_den(self)
    audio.AudioSession.go_den = go_den_with_actual_poison_recovery
    original_walk = audio.AudioSession.walk
    def observed_walk(self, key):
        try:
            return original_walk(self, key)
        except AssertionError:
            self.capture('failure_navigation')
            x, y = self.position()
            state = {'map': self.map(), 'xy': [x, y], 'direction': key,
                     'player_direction': self.read('wPlayerDirection'),
                     'script_mode': self.read('wScriptMode'), 'battle': self.read('wBattleMode'),
                     'nearby_collisions': {str((a,b)): self.collision_at(a,b)
                         for a in range(x-2,x+3) for b in range(y-2,y+3)},
                     'object_structs': self.read('wObjectStructs', 13 * 40),
                     'map_blocks': self.read('wOverworldMapBlocks', 700)}
            (OUT / 'navigation_failure.json').write_text(json.dumps(state, indent=2) + '\n')
            raise
    audio.AudioSession.walk = observed_walk
    sys.argv = [__file__, '--section', 'normal', '--expected-sha', args.expected_sha]
    audio.main()
    report_path = OUT / 'normal_validation.json'
    report = json.loads(report_path.read_text())
    report['ordinary_native_poison_recoveries'] = recoveries
    report_path.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
