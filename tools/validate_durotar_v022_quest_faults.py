#!/usr/bin/env python3
"""Explicit diagnostic fixtures for full-pocket reward retries.

This is separate from the successful no-RAM-edit quest route. Synthetic
inventory and ready/dead flags are injected in a fresh isolated ROM solely to
exercise failure branches; subsequent giver interactions use normal buttons.
No user's battery save is opened or modified.
"""
from pathlib import Path
import hashlib
import json
import logging
import shutil
import tempfile

from PIL import Image
from validate_durotar_v022_quests import QuestSession, FLAGS, load_symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/quest_fault_validation'


def pocket_item_ids(pocket, exclude=()):
    ids = []
    index = 1
    for line in (ROOT / 'data/items/attributes.asm').read_text().splitlines():
        if not line.strip().startswith('item_attribute '):
            continue
        fields = [s.strip() for s in line.strip().split(' ', 1)[1].split(',')]
        if fields[4] == pocket and index not in exclude:
            ids.append(index)
        index += 1
    return ids


class FaultSession(QuestSession):
    def capture(self, name):
        self.p.screen.image.save(OUT / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / (name + '_4x.png'))
        print(name, self.map(), self.position(), flush=True)

    def write(self, name, values):
        bank, address = self.sym[name]
        if address >= 0xe000:
            self.p.memory[address:address + len(values)] = values
        else:
            self.p.memory[bank, address:address + len(values)] = values

    def set_event(self, name, value=True):
        i = FLAGS[name]
        bank, address = self.sym['wEventFlags']
        old = self.p.memory[bank, address + i // 8]
        self.p.memory[bank, address + i // 8] = old | (1 << (i % 8)) if value else old & ~(1 << (i % 8))

    def experience(self):
        return int.from_bytes(bytes(self.read('wPartyMon1Exp', 3)), 'big')

    def progress(self):
        return {'money': self.money(), 'xp': self.experience(),
                'hp': self.read('wPartyMon1HP', 2), 'max_hp': self.read('wPartyMon1MaxHP', 2),
                'pp': self.read('wPartyMon1PP', 4), 'status': self.read('wPartyMon1Status'),
                'moves': self.read('wPartyMon1Moves', 4)}

    def full_items(self, exclude):
        before = self.read('wNumItems'), self.read('wItems', 41), self.event('EVENT_PEON_LARGE_BAG')
        ids = pocket_item_ids('ITEM', exclude)[:20]
        assert len(ids) == 20 and len(set(ids)) == 20
        self.set_event('EVENT_PEON_LARGE_BAG')
        self.write('wNumItems', [20])
        self.write('wItems', [v for item in ids for v in (item, 99)] + [255])
        return before

    def restore_items(self, before):
        number, items, large = before
        self.write('wNumItems', number); self.write('wItems', items)
        self.set_event('EVENT_PEON_LARGE_BAG', large)

    def full_keys(self, exclude):
        before = self.read('wNumKeyItems'), self.read('wKeyItems', 26)
        ids = pocket_item_ids('KEY_ITEM', exclude)[:25]
        assert len(ids) == 25 and len(set(ids)) == 25
        self.write('wNumKeyItems', [25]); self.write('wKeyItems', ids + [255])
        return before

    def restore_keys(self, before):
        number, keys = before
        self.write('wNumKeyItems', number); self.write('wKeyItems', keys)


def main():
    logging.disable(logging.CRITICAL); OUT.mkdir(parents=True, exist_ok=True)
    report = {'rom_sha256': hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest(),
              'method': 'Explicit full-pocket/dead-flag fixtures. Second-pack-member loss uses temporary HP=1, enemy native Swift, enemy Speed65535/player Speed1 and no active totem. Traversal, menus and retry battles use normal buttons in an isolated ROM; no result/CPU substitution.',
              'ram_edits': True, 'diagnostic_only': True, 'emulator_states_loaded': False, 'cases': {}}
    s = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-quest-faults-') as directory:
            rom = Path(directory) / 'diagnostic.gbc'; shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = FaultSession(rom, load_symbols()); s.fresh(); s.to_valley()
            s.talk((5, 11), 'right', 'medallion_accept_normally')
            s.set_event('EVENT_PEON_YARROG_DEAD')
            saved = s.full_items((0x8e,))
            before = s.progress(); s.talk((5, 11), 'right', 'spirit_mace_full_bag')
            assert not s.event('EVENT_PEON_MEDALLION_DONE')
            assert s.progress() == before, 'Failed equipment reward granted copper/XP/heal/PP'
            assert 0x93 in s.read('wKeyItems', s.read('wNumKeyItems')[0]), 'Missing proof was not recovered safely'
            s.restore_items(saved)
            s.talk((5, 11), 'right', 'spirit_mace_retry_success')
            assert s.event('EVENT_PEON_MEDALLION_DONE') and s.item_quantity(0x8e) == 1
            assert s.money() == before['money'] + 150 and s.experience() == before['xp'] + 100
            assert 0x93 not in s.read('wKeyItems', s.read('wNumKeyItems')[0])
            after = s.progress(); s.talk((5, 11), 'right', 'spirit_mace_repeat_no_reward')
            assert s.progress() == after
            report['cases']['equipment_full_bag_retry'] = {'failed_without_reward': True, 'proof_recovered_then_consumed': True,
                                                          'successful_retry_copper': 150, 'successful_retry_xp': 100,
                                                          'reward_only_once': True}

            s.talk((10, 20), 'up', 'sarkoth_accept_normally'); s.set_event('EVENT_PEON_SARKOTH_DEAD')
            saved = s.full_items((18,))
            before = s.progress(); s.talk((10, 20), 'up', 'potions_full_bag')
            assert not s.event('EVENT_PEON_SARKOTH_DONE') and s.progress() == before
            s.restore_items(saved)
            quantity = s.item_quantity(18); s.talk((10, 20), 'up', 'potions_retry_success')
            assert s.event('EVENT_PEON_SARKOTH_DONE') and s.item_quantity(18) == quantity + 2
            assert s.money() == before['money'] + 100 and s.experience() == before['xp'] + 50
            after = s.progress(); s.talk((10, 20), 'up', 'potions_repeat_no_reward'); assert s.progress() == after
            report['cases']['consumable_full_bag_retry'] = {'failed_without_reward': True, 'successful_retry_potions': 2,
                                                           'successful_retry_copper': 100, 'successful_retry_xp': 50,
                                                           'reward_only_once': True}

            s.talk((8, 11), 'up', 'galgar_accept_normally')
            for n in (1, 2, 3):
                s.set_event(f'EVENT_PEON_CACTUS_{n}')
            saved = s.full_keys((0x78,))
            before = s.progress(); s.talk((8, 11), 'up', 'leather_bag_full_quest_pouch')
            assert not s.event('EVENT_PEON_CACTUS_DONE') and s.progress() == before
            s.restore_keys(saved); s.talk((8, 11), 'up', 'leather_bag_retry_success')
            assert s.event('EVENT_PEON_CACTUS_DONE') and s.event('EVENT_PEON_LARGE_BAG')
            assert s.money() == before['money'] + 50 and s.experience() == before['xp'] + 25
            after = s.progress(); s.talk((8, 11), 'up', 'leather_bag_repeat_no_reward'); assert s.progress() == after
            report['cases']['key_pocket_full_reward_retry'] = {'failed_without_reward': True, 'successful_retry_copper': 50,
                                                              'successful_retry_xp': 25, 'bag_capacity_unlocked': True,
                                                              'reward_only_once': True}
            # Fault boundary only: the first pack member is defeated normally;
            # one HP is injected at the second native encounter picture load.
            # At its actual move-selection screen, native Swift and a high
            # enemy speed guarantee an ordinary damaging turn; HP alone does
            # not force loss when a scorpid misses or chooses a status move.
            s.rest(); s.to_valley(); s.navigate((28, 12), expected_map=16)
            s.p.hook_deregister(*s.sym['LoadTrainerOrWildMonPic'])
            fixture = {'loads': 0, 'second_hp_injected': False, 'native_swift_speed_fixture': False}
            def force_second_loss(_unused):
                s.encounter_loads += 1
                fixture['loads'] += 1
                if fixture['loads'] == 2:
                    s.write('wPartyMon1HP', [0, 1]); s.write('wBattleMonHP', [0, 1])
                    fixture['second_hp_injected'] = True
            s.p.hook_register(*s.sym['LoadTrainerOrWildMonPic'], force_second_loss, None)
            s.p.hook_deregister(*s.sym['MoveSelectionScreen'])
            def force_native_damaging_turn(_unused):
                s.move_menus += 1
                if fixture['loads'] == 2:
                    s.write('wEnemyMonMoves', [129, 0, 0, 0])  # SWIFT: native always-hit damage.
                    s.write('wEnemyMonPP', [20, 0, 0, 0])
                    s.write('wEnemyMonSpeed', [255, 255]); s.write('wBattleMonSpeed', [0, 1])
                    s.write('wPeonEarthTotemActive', [0])
                    fixture['native_swift_speed_fixture'] = True
            s.p.hook_register(*s.sym['MoveSelectionScreen'], force_native_damaging_turn, None)
            s.prefer_physical = True
            money = s.money(); s.navigate((16, 17))
            result = s.fight('pack_second_member_forced_loss', 'EVENT_PEON_ROAD_SCORPID_PACK_DEAD')
            report['forced_pack_result'] = result | {'fixture': dict(fixture)}
            assert result['outcome'] == 1 and fixture['loads'] == 2 and fixture['second_hp_injected'], (result, fixture)
            assert s.event('EVENT_PEON_ROAD_SCORPID_PACK_FIRST') and not s.event('EVENT_PEON_ROAD_SCORPID_PACK_DEAD')
            assert s.money() == money and s.read('wPartyMon1HP', 2) == [0, 1] and s.read('wPartyMon1Status') == [0]
            first_state = s.cold_restart()
            assert s.event('EVENT_PEON_ROAD_SCORPID_PACK_FIRST') and not s.event('EVENT_PEON_ROAD_SCORPID_PACK_DEAD')
            s.p.hook_deregister(*s.sym['MoveSelectionScreen'])
            s.p.hook_register(*s.sym['MoveSelectionScreen'],
                             lambda _unused: setattr(s, 'move_menus', s.move_menus + 1), None)
            s.prefer_physical = False; s.rest(); s.to_valley(); s.navigate((28, 12), expected_map=16)
            loads = s.encounter_loads; s.navigate((16, 17))
            result = s.fight('pack_retry_only_surviving_member', 'EVENT_PEON_ROAD_SCORPID_PACK_DEAD', 40)
            assert result['outcome'] == 0 and s.encounter_loads == loads + 1
            report['cases']['pack_partial_defeat_persistence'] = {
                'first_member_killed_by_normal_buttons': True, 'second_member_hp_fault_injected': True,
                'second_member_native_swift_speed_fixture': fixture['native_swift_speed_fixture'],
                'second_loss_grants_no_copper': True, 'first_flag_survives_cold_battery_restart': True,
                'retry_starts_only_one_surviving_member': True, 'final_copper_reward': 40,
                'save_restart': first_state}
            report['all_checks_passed'] = True; s.p.stop(save=False); s = None
    except Exception as exc:
        report['all_checks_passed'] = False; report['failure'] = repr(exc)
        if s:
            s.capture('unexpected_state'); s.p.stop(save=False)
        (OUT / 'validation_results.json').write_text(json.dumps(report, indent=2) + '\n')
        raise
    (OUT / 'validation_results.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS diagnostics: full item/key pockets grant no rewards until retry succeeds exactly once.')


if __name__ == '__main__':
    main()
