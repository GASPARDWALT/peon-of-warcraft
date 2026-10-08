#!/usr/bin/env python3
"""Reach the road's two level-four scorpids with ordinary new-game buttons."""
import hashlib
import json
import logging
import shutil
import tempfile
from pathlib import Path

from PIL import Image

from validate_durotar_v022_quests import QuestSession, load_symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v023/combat_balance'


class PackSession(QuestSession):
    def capture(self, name):
        name = 'normal_pack_' + name
        self.p.screen.image.save(OUT / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / (name + '_4x.png'))
        print(name, self.map(), self.position(), self.snapshot(), flush=True)

    def word(self, name):
        return int.from_bytes(bytes(self.read(name, 2)), 'big')

    def snapshot(self):
        return dict(level=self.read('wPartyMon1Level')[0], experience=self.experience(),
                    hp=self.word('wPartyMon1HP'), max_hp=self.word('wPartyMon1MaxHP'),
                    pp=self.read('wPartyMon1PP', 4), status=self.read('wPartyMon1Status')[0],
                    copper=self.money())

    def fight(self, label, flag, copper=None, load_baseline=None):
        before = self.snapshot()
        heals = self.heal_calls
        loads = self.encounter_loads if load_baseline is None else load_baseline
        handled = self.move_menus
        battle_starts, sampled = [], set()
        entered = bool(self.read('wBattleMode')[0])
        for _ in range(180):
            entered |= bool(self.read('wBattleMode')[0])
            if self.move_menus > handled:
                handled = self.move_menus
                self.p.tick(60, True)
                if self.encounter_loads not in sampled:
                    sampled.add(self.encounter_loads)
                    battle_starts.append(dict(player_level=self.read('wBattleMonLevel')[0],
                                              enemy_level=self.read('wEnemyMonLevel')[0],
                                              hp=self.word('wBattleMonHP'),
                                              max_hp=self.word('wBattleMonMaxHP'),
                                              player_status=self.read('wBattleMonStatus')[0]))
                    self.capture(label + '_enemy_' + str(len(battle_starts)))
                moves, pp = self.read('wBattleMonMoves', 4), self.read('wBattleMonPP', 4)
                wanted = next((i for i, move in enumerate(moves) if move == 84 and pp[i] & 63), 0)
                for _ in range(5):
                    current = self.read('wCurMoveNum')[0]
                    if current == wanted:
                        break
                    self.press('up' if current > wanted else 'down', 30)
                self.press('a', 180)
            else:
                self.press('a', 120)
            if entered and self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]:
                break
        assert entered and self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]
        result = self.read('wBattleResult')[0]
        assert self.heal_calls == heals, 'Encounter called HealParty'
        if result == 0:
            assert self.event(flag), 'Victory did not persist'
            if copper is not None:
                assert self.money() == before['copper'] + copper
        elif result == 1:
            assert not self.event(flag), 'Defeat deleted undefeated enemy'
            assert self.word('wPartyMon1HP') == 1 and self.read('wPartyMon1Status') == [0]
            assert self.money() == before['copper'], 'Defeat granted loot'
        self.capture(label + '_after')
        return dict(outcome=result, before=before, after=self.snapshot(), battle_starts=battle_starts,
                    native_enemy_loads=self.encounter_loads - loads, heal_party_calls=0,
                    victory_flag=self.event(flag))


def main():
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(rom_sha256=hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest(),
                  normal_buttons_only=True, ram_edits=False, emulator_states_loaded=False,
                  method='Fresh character, Cutting Teeth, inn, Den scorpid, Gornek reward, inn, direct road pack. No farming, training, totem or potion.',
                  all_checks_passed=False)
    s = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-v023-normal-pack-') as directory:
            rom = Path(directory) / 'test.gbc'
            shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = PackSession(rom, load_symbols())
            s.fresh()
            s.talk((10, 10), 'up', 'gornek_first_quest')
            loads = s.encounter_loads
            s.navigate((18, 13)); s.press('up', 30); s.press('a')
            report['boar'] = s.fight('boar', 'EVENT_PEON_QUEST_DONE', load_baseline=loads)
            assert report['boar']['outcome'] == 0
            s.talk((10, 10), 'up', 'gornek_second_quest'); s.rest()
            loads = s.encounter_loads
            s.navigate((17, 15))
            report['den_scorpid'] = s.fight('den_scorpid', 'EVENT_PEON_SCORPID_DEFEATED', load_baseline=loads)
            assert report['den_scorpid']['outcome'] == 0
            s.talk((10, 10), 'up', 'gornek_second_reward'); s.rest()
            report['before_road'] = s.snapshot()
            assert report['before_road']['level'] == 4, report['before_road']
            s.to_valley(); s.navigate((28, 12), expected_map=16)
            loads = s.encounter_loads
            s.navigate((16, 17))
            report['pack'] = s.fight('two_equal_scorpids', 'EVENT_PEON_ROAD_SCORPID_PACK_DEAD', 40, load_baseline=loads)
            pair = report['pack']
            assert pair['native_enemy_loads'] == 2 and len(pair['battle_starts']) == 2
            assert all(b['player_level'] == b['enemy_level'] == 4 for b in pair['battle_starts'])
            report['two_equal_level_encounters_without_auto_heal'] = True
            report['without_potion_won'] = pair['outcome'] == 0
            if pair['outcome'] == 0:
                gain = pair['after']['max_hp'] - pair['before']['max_hp']
                report['max_hp_added_by_level_up'] = gain
                report['hp_after_removing_level_up_gain'] = pair['after']['hp'] - gain
                report['fraction_of_starting_max_hp_remaining'] = (pair['after']['hp'] - gain) / pair['before']['max_hp']
                assert s.event('EVENT_PEON_ROAD_SCORPID_PACK_FIRST')
            else:
                report['loss_recovery'] = dict(map=s.map(), hp=s.word('wPartyMon1HP'),
                                               first_member_remains_defeated=s.event('EVENT_PEON_ROAD_SCORPID_PACK_FIRST'))
            report['all_checks_passed'] = True
            s.p.stop(save=False); s = None
    except Exception as error:
        report['failure'] = repr(error)
        if s is not None:
            s.capture('unexpected_state'); s.p.stop(save=False)
        (OUT / 'normal_pack_validation.json').write_text(json.dumps(report, indent=2) + '\n')
        raise
    (OUT / 'normal_pack_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
