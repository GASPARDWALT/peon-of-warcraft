#!/usr/bin/env python3
"""Actual class-relic recruitment, small team UX and progression.

Starts from the genuine old three-class batteries prepared by the save-upgrade
suite, then uses only ordinary inputs. Read-only hooks inspect the actual native
HP/catch-rate formula and party records. No memory writes or state restores.
"""
import argparse
import hashlib
import json
import logging
import math
import shutil
import tempfile
from pathlib import Path

from PIL import Image
from validate_peon_combat_v028 import PolishSession

import validate_peon_save_upgrade_v029 as migration
import validate_peon_warlock_pet as pets
import validate_peon_polish_v028 as visual
from validate_peon_battle_totems import BagSession
from validate_peon_class_routes import MASTER
from peon_event_flags_v029 import recruitment_flag_indices

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/recruitment_v029/team_runtime'
CLASSES = ('shaman', 'warrior', 'warlock')
RELICS = (5, 2, 4)
ROLES = (95, 68, 74)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_script_bank_gate(symbols):
    checked, sentinels, failures = 0, 0, []
    other_pointers = {}
    for path in sorted((ROOT / 'maps').glob('*.asm')):
        event = path.stem + '_MapEvents'
        if event not in symbols:
            continue
        event_bank = symbols[event][0]
        for number, row in enumerate(path.read_text().splitlines(), 1):
            words = row.strip().split(' ', 1)
            if len(words) == 2 and words[0] in ('callback', 'scene_script', 'coord_event', 'bg_event'):
                kind = words[0]
                args = [part.strip() for part in words[1].split(';', 1)[0].split(',')]
                target = args[0] if kind == 'scene_script' else args[-1]
                header = path.stem + ('_MapScripts' if kind in ('callback', 'scene_script') else '_MapEvents')
                if target in symbols and header in symbols:
                    other_pointers[kind] = other_pointers.get(kind, 0) + 1
                    if symbols[target][0] != symbols[header][0]:
                        failures.append({'map': path.stem, 'line': number, 'kind': kind,
                            'script': target, 'map_bank': symbols[header][0], 'script_bank': symbols[target][0]})
            if not row.lstrip().startswith('object_event '):
                continue
            fields = [part.strip() for part in row.strip().split(' ', 1)[1].split(',')]
            assert len(fields) == 13, ('Unrecognized object row', path, number)
            script = fields[11]
            assert script in symbols, ('Unresolved object script', path, number, script)
            checked += 1
            if script == 'ObjectEvent' and symbols[script][0] == 0 and symbols[script][1] < 0x4000:
                sentinels += 1
                continue
            if symbols[script][0] != event_bank:
                failures.append({'map': path.stem, 'line': number, 'script': script,
                                 'map_bank': event_bank, 'script_bank': symbols[script][0]})
    assert not failures, ('16-bit object script points into another ROM bank', failures)
    return {'resolved_object_script_pointers_compared': checked,
            'legal_fixed_ROM0_ObjectEvent_scripts': sentinels,
            'other_resolved_16bit_map_script_pointers': other_pointers,
            'cross_bank_object_scripts': 0,
            'map_local_farsjump_wrappers_required': True}


class TeamSession(pets.PetSession):
    def __init__(self, rom, symbols, index):
        self.slug = CLASSES[index]
        self.recruit_attempts = []
        self.recruit_pending = None
        self.ordinary_switches = 0
        self.enemy_opportunities = 0
        self.forbidden_calls = {'nickname_prompt': 0, 'dex_entry': 0, 'ball_effect': 0}
        self.hook_errors = []
        self.team_entries = 0
        self.native_save_calls = 0
        self.events = []
        self.folder = OUT / self.slug
        self.folder.mkdir(parents=True, exist_ok=True)
        self.bg_checks = []
        self.battle_chrome_checks = []
        self.pet_bg_changes = []
        self.harder_turn_observations = []
        super().__init__(rom, symbols, index, 'ordinary')
        self.flags.update(migration.named_constants(ROOT / 'constants/event_flags.asm'))

    def battle_menu(self, unused):
        self.events.append({'frame': self.p.frame_count, 'hook': 'LoadBattleMenu',
                            'phase_before': self.phase, 'battle_mode': self.read('wBattleMode')})
        super().battle_menu(unused)

    def static_ready(self, unused):
        if self.read('wBattleMode')[0]:
            self.events.append({'frame': self.p.frame_count, 'hook': 'StaticMenuJoypad',
                                'phase_before': self.phase, 'context': self.context})
        super().static_ready(unused)

    vertical_menu = BagSession.vertical_menu

    def open(self):
        super().open()
        def safe(label, callback):
            def observe(_):
                try:
                    callback()
                except Exception as error:
                    self.hook_errors.append({'hook': label, 'error': repr(error)})
            self.p.hook_register(*self.sym[label], observe, None)
        safe('PeonTeamPickV029.input', self.team_entered)
        safe('PeonTryRecruitV029.BaseBallRoll', self.roll_entered)
        safe('PeonTryRecruitV029.joined', lambda: self.roll_finished(True))
        safe('PeonTryRecruitV029.miss', lambda: self.roll_finished(False))
        safe('TryPlayerSwitch.try_switch', lambda: setattr(self, 'ordinary_switches', self.ordinary_switches + 1))
        safe('DoEnemyTurn', lambda: setattr(self, 'enemy_opportunities', self.enemy_opportunities + 1))
        safe('_SaveGameData', lambda: setattr(self, 'native_save_calls', self.native_save_calls + 1))
        self.p.hook_register(*self.sym['VerticalMenu'], self.vertical_menu, None)
        for label, role in (('GiveANickname_YesNo', 'nickname_prompt'),
                            ('NewPokedexEntry', 'dex_entry'),
                            ('PokeBallEffect', 'ball_effect')):
            if label in self.sym:
                safe(label, lambda role=role: self.forbidden_calls.__setitem__(role, self.forbidden_calls[role] + 1))

    def write(self, *_args, **_kwargs):
        raise AssertionError('Ordinary team/recruitment validation forbids emulator RAM writes')

    def press(self, key, frames=90):
        self.p.button(key, delay=4)
        self.p.tick(frames, True)
        # The retained trainer waiter predates nested TEAM panels. Only its
        # own drawing/confirmation phases require that extra input readiness.
        for _ in range(100):
            if self.phase not in ('drawing', 'selecting', 'confirm', 'message', 'slots_drawing'):
                return
            if self.phase in ('confirm', 'message') and self.wait_ready:
                return
            self.p.tick(10, True)
        raise AssertionError(('Native trainer readiness timeout', self.phase))

    def capture(self, label):
        folder = OUT / self.slug
        folder.mkdir(parents=True, exist_ok=True)
        self.p.screen.image.save(folder / (label + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(folder / (label + '_4x.png'))
        print(self.slug, label, self.map(), self.position(), self.phase, flush=True)

    def word(self, label):
        return int.from_bytes(bytes(self.read(label, 2)), 'big')

    palette = visual.Session.palette
    background = visual.Session.background
    object_mask = visual.Session.object_mask
    surface = visual.Session.surface

    def verify_battle_chrome(self, label):
        bank, address = self.sym['FontBattleExtra']
        wanted = bytes(self.p.memory[bank, address:address + 12 * 16])
        assert bytes(self.p.memory[0, 0x9600:0x96c0]) == wanted, (
            label, 'Native battle digits/Lv/HP $60..$6b were not restored')
        evidence = {'label': label, 'native_battle_font_packet_exact': True,
                    'bold_names': PolishSession.assert_current_bold_name_glyphs(self)}
        self.battle_chrome_checks.append(evidence)
        return evidence

    def pet_start(self, unused):
        super().pet_start(unused)
        self.pet_pending['actual_tiles'] = self.read('wTilemap', 360)
        self.pet_pending['actual_attrs'] = self.read('wAttrmap', 360)
        self.pet_pending['active_record'] = self.read('wCurBattleMon')[0]
        self.pet_pending['active_species'] = self.read('wBattleMonSpecies')[0]
        records = self.read('wPartyMon1', self.read('wPartyCount')[0] * 48)
        self.pet_pending['living_imps'] = [i for i in range(len(records) // 48)
            if records[i * 48] == 74 and any(records[i * 48 + 34:i * 48 + 36])]

    def pet_done(self, unused):
        try:
            before, after = self.pet_pending, self.round_snapshot()
            assert before and before['player_hp'] > 0 and before['enemy_hp'] > 0
            assert before['active_species'] != 74 and before['living_imps']
            assert after['enemy_hp'] == before['enemy_hp'] - 1
            ignored = {'enemy_hp', 'actual_tiles', 'actual_attrs', 'active_record', 'active_species', 'living_imps'}
            comparable = {k: v for k, v in before.items() if k not in ignored}
            assert comparable == {k: v for k, v in after.items() if k != 'enemy_hp'}, (
                'Pet changed protected state', {k: [v, after.get(k)] for k, v in comparable.items() if v != after.get(k)},
                {'tile_differences': [(i % 20, i // 20, a, b) for i, (a, b) in enumerate(zip(before['actual_tiles'], self.read('wTilemap', 360))) if a != b],
                 'attribute_differences': [(i % 20, i // 20, a, b) for i, (a, b) in enumerate(zip(before['actual_attrs'], self.read('wAttrmap', 360))) if a != b]})
            self.pet_rounds.append({'before': before, 'after': after})
            self.pet_pending = None
        except Exception as error:
            self.pet_errors.append(repr(error))

    def team_entered(self):
        self.team_entries += 1
        self.phase, self.context = 'team', None

    def canonical_base_stats(self, species):
        # Battle's wEnemyMonBaseStats is the old five-stat EXP record, followed
        # by catch rate. Read all six stats from the actual linked ROM table.
        bank, address = self.sym['BaseData']
        address += (species - 1) * 32
        assert self.p.memory[bank, address] == species
        return list(self.p.memory[bank, address + 1:address + 7])

    def roll_entered(self):
        assert self.recruit_pending is None
        hp, maximum = self.word('wEnemyMonHP'), self.word('wEnemyMonMaxHP')
        double, triple = hp * 2, maximum * 3
        if triple > 255:
            triple >>= 2
            double = max(1, double >> 2)
        base = self.read('wEnemyMonCatchRate')[0]
        threshold = max(1, base * (triple - double) // triple)
        status = self.read('wEnemyMonStatus')[0]
        if status & 0x27:  # Crystal SLP bits0..2 and FRZ bit5.
            threshold = min(255, threshold + 10)
        self.recruit_pending = {'species': self.read('wEnemyMonSpecies')[0],
            'level': self.read('wEnemyMonLevel')[0], 'hp': hp, 'max_hp': maximum,
            'base_catch_rate': base, 'status': status, 'expected_native_threshold': threshold,
            'quantity_before': self.item_quantity(RELICS[self.class_index]),
            'party_count_before': self.read('wPartyCount')[0],
            'canonical_base_stats': self.canonical_base_stats(self.read('wEnemyMonSpecies')[0]),
            'original_dvs': self.read('wEnemyMonDVs', 2),
            'original_held_item': self.read('wEnemyMonItem')[0]}

    def roll_finished(self, joined):
        pending = self.recruit_pending
        assert pending is not None
        assert self.read('wFinalCatchRate') == [pending['expected_native_threshold']], (
            'Relic diverged from native base-ball HP/status formula', pending, self.read('wFinalCatchRate'))
        assert self.item_quantity(RELICS[self.class_index]) == pending['quantity_before']
        if joined:
            count = self.read('wPartyCount')[0]
            assert count == pending['party_count_before'] + 1
            record = self.read('wPartyMon1', count * 48)[-48:]
            assert record[0] == pending['species'] and record[31] == pending['level']
            assert int.from_bytes(bytes(record[34:36]), 'big') == pending['hp']
            assert record[32] == pending['status']
            assert record[1] == pending['original_held_item']
            assert record[21:23] == pending['original_dvs']
            atk, defense, speed, special = record[21] >> 4, record[21] & 15, record[22] >> 4, record[22] & 15
            hp_dv = ((atk & 1) << 3) | ((defense & 1) << 2) | ((speed & 1) << 1) | (special & 1)
            dvs = [hp_dv, atk, defense, speed, special, special]
            expected = []
            for index, (base, dv) in enumerate(zip(pending['canonical_base_stats'], dvs)):
                ev_index = min(index, 4)
                ev = int.from_bytes(bytes(record[11 + ev_index * 2:13 + ev_index * 2]), 'big')
                sqrt_ev = math.isqrt(ev)
                if sqrt_ev * sqrt_ev < ev:
                    sqrt_ev += 1
                value = ((2 * (base + dv) + min(255, max(1, sqrt_ev)) // 4) * record[31]) // 100
                expected.append(value + record[31] + 10 if index == 0 else value + 5)
            actual = [int.from_bytes(bytes(record[36 + i * 2:38 + i * 2]), 'big') for i in range(6)]
            assert actual == expected, ('Recruit copied battle-modified stats instead of canonical raw stats', pending, actual, expected)
            pending['captured_hp_status_dvs_item_preserved_and_six_stats_recomputed'] = True
            pending['recruited_six_raw_stats'] = actual
        pending['joined'] = joined
        pending['original_native_roll_matches'] = True
        pending['reusable_relic_quantity_preserved'] = True
        self.recruit_attempts.append(pending)
        self.recruit_pending = None

    def continue_at_saved_location(self):
        expected = migration.previous.SAVE_LOCATIONS[self.class_index][0]
        self.p.tick(1800, True); self.press('start')
        for _ in range(25):
            if self.map() == expected and self.read('wScriptMode') == [0]:
                break
            self.press('a', 180)
        assert self.map() == expected and self.read('wScriptMode') == [0]
        assert self.read('wPartyCount') == [2 if self.class_index == 2 else 1]
        assert self.read('wPartyMon1Species') == [66]
        if expected in (22, 23):
            self.navigate((5, 7), expected_map=14)

    def heal_at_inn(self):
        self.navigate((17, 5), expected_map=23)
        self.talk_plain((6, 5), 'up')
        count = self.read('wPartyCount')[0]
        records = self.read('wPartyMon1', count * 48)
        assert all(records[i + 34:i + 36] == records[i + 36:i + 38]
                   for i in range(0, len(records), 48))
        self.capture('inn_heals_true_team')
        self.navigate((5, 7), expected_map=14)

    def class_relic_quest(self):
        self.enter_class_trainer()
        assert self.event('EVENT_PEON_RECRUIT_ACCEPTED_V029')
        assert self.item_quantity(RELICS[self.class_index]) == 1
        self.exit_trainer()
        before = self.item_quantity(RELICS[self.class_index])
        self.enter_class_trainer(); self.exit_trainer()
        assert self.item_quantity(RELICS[self.class_index]) == before
        self.capture('class_relic_quest_once')

    def field_team(self, index=None, expected_locked=True):
        # A native warp can publish its map number before fade-in/input has
        # finished. Wait normally before issuing the menu-opening key.
        self.p.tick(120, True)
        assert self.read('wScriptMode') == [0]
        before = self.read('wPartyMon1', 6 * 48)
        self.press('start')
        for _ in range(12):
            if self.read('wMenuCursorPosition') == [1]:
                break
            self.press('up', 30)
        self.press('a'); self.press('right'); self.ready('team')
        chars = migration.previous.classes.text_encoding()
        tiles = self.read('wTilemap', 360)
        encoded = [chars[c] for c in 'SARKOTH LOCKED']
        present = any(tiles[i:i + len(encoded)] == encoded for i in range(360 - len(encoded)))
        assert present == expected_locked, ('Progression capacity label', expected_locked, present)
        self.surface('actual_team_panel_' + str(self.team_entries))
        if index is None:
            self.press('b')
        else:
            for _ in range(6):
                current = self.read('wPeonTeamCursorV029')[0]
                if current == index:
                    break
                self.press('up' if current > index else 'down', 30)
            assert self.read('wPeonTeamCursorV029') == [index]
            self.press('a')
            assert self.read('wPeonTeamPreferredV029') == [index]
        self.surface('character_returns_after_team_' + str(self.team_entries))
        self.press('b'); self.press('b')
        assert self.read('wScriptMode') == [0]
        assert self.read('wPartyMon1', 6 * 48) == before
        self.phase, self.context = 'overworld', None

    def travel_crossroads(self):
        if self.map() == 14:
            self.navigate((20, 10), expected_map=15)
        if self.map() == 15:
            self.navigate((16, 0), expected_map=25)
        assert self.map() == 25

    def return_den(self):
        if self.map() == 26:
            self.navigate((9, 4), expected_map=25)
        if self.map() == 28:
            self.navigate((5, 9), expected_map=25)
        if self.map() == 25:
            self.navigate((5, 9), expected_map=15)
        if self.map() == 15:
            self.navigate((4, 12), expected_map=14)
        assert self.map() == 14

    def start_node(self):
        self.travel_crossroads()
        if self.class_index == 0:
            self.navigate((3, 6)); self.press('up', 30); self.press('a', 30)
        elif self.class_index == 1:
            self.navigate((0, 4), expected_map=26)
            self.navigate((3, 7)); self.press('up', 30); self.press('a', 30)
        else:
            self.navigate((5, 0), expected_map=28)
            self.navigate((6, 7)); self.press('right', 30); self.press('a', 30)
        self.wait(lambda: self.phase == 'battle', buttons=True)
        assert self.read('wEnemyMonSpecies') == [ROLES[self.class_index]]
        assert self.read('wBattleMode') == [1]

    def recruit_here(self):
        # The higher-level Warrior/Warlock can kill their level2/3 training
        # target in a single blow. Shaman can safely weaken this exact fixture;
        # the others use the unchanged full-HP roll and purchased potions.
        self.ready('battle')
        if self.class_index == 0:
            before_menus = self.menus
            for _ in range(5):
                x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
                if (x, y) == (1, 1):
                    break
                self.press('left' if x > 1 else 'up', 30)
            self.press('a', 60)
            for _ in range(5):
                if self.read('wMenuCursorY') == [1]:
                    break
                self.press('up', 30)
            self.press('a', 120)
            self.wait(lambda: self.menus > before_menus or not self.read('wBattleMode')[0], buttons=True)
            assert self.read('wBattleMode')[0], 'An ordinary critical knocked out the pact target; retry this node after reentry'
        quantity = self.item_quantity(RELICS[self.class_index])
        for _ in range(240):
            if self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]:
                break
            if self.phase == 'battle':
                if self.word('wBattleMonHP') <= self.word('wBattleMonMaxHP') // 2 and self.item_quantity(18):
                    self.open_bag_item(18)
                else:
                    self.open_bag_item(RELICS[self.class_index])
                self.press('a', 30)
            else:
                self.press('a', 40)
        assert self.read('wBattleMode') == [0]
        assert self.event('EVENT_PEON_RECRUIT_CAPTURED_V029')
        assert self.item_quantity(RELICS[self.class_index]) == quantity
        assert self.recruit_attempts and self.recruit_attempts[-1]['joined']
        assert not self.hook_errors, self.hook_errors
        # Script object operands are one-based NPC constants. A capture must
        # retire the target, preserve the player at actual struct0 and still
        # allow ordinary movement. The original wrong operand deleted hero0.
        assert self.read('wPlayerObject')[0] == 0
        assert self.read('wPlayerSprite')[0] != 0
        assert self.read('wMapObjects', 17)[16] == 255
        self.capture('actual_class_role_recruited')

    def relic_refusal(self, label):
        self.open_bag_item(RELICS[self.class_index])
        before = {name: self.read(name, count) for name, count in (
            ('wEnemyMonHP', 2), ('wBattleMonHP', 2), ('wPlayerTurnsTaken', 1),
            ('wEnemyTurnsTaken', 1), ('wPartyCount', 1), ('wPartyMon1', 6 * 48))}
        quantity = self.item_quantity(RELICS[self.class_index])
        attempts = len(self.recruit_attempts)
        self.press('a', 90); self.ready('inventory')
        after = {name: self.read(name, len(values)) for name, values in before.items()}
        assert before == after and self.item_quantity(RELICS[self.class_index]) == quantity
        assert len(self.recruit_attempts) == attempts
        self.capture(label + '_no_turn')
        self.surface(label + '_stable_inventory')
        self.press('b'); self.press('b'); self.ready('battle')
        self.p.tick(60, True)
        self.verify_battle_chrome(label + '_return')

    def wrong_target_refusal(self):
        assert self.class_index in (0, 1) and self.read('wPartyCount') == [1]
        self.travel_crossroads()
        if self.class_index == 0:
            self.navigate((0, 4), expected_map=26)
            self.navigate((3, 7)); self.press('up', 30); self.press('a', 30)
        else:
            self.navigate((3, 6)); self.press('up', 30); self.press('a', 30)
        self.wait(lambda: self.phase == 'battle', buttons=True)
        assert self.read('wEnemyMonSpecies')[0] != ROLES[self.class_index]
        self.relic_refusal('wrong_family_relic_refusal')
        self.flee_native(); self.return_den()
        assert not self.event('EVENT_PEON_RECRUIT_CAPTURED_V029')
        self.heal_at_inn()

    def finish_with_supplies(self, flag):
        harder_pack = flag in ('EVENT_PEON_KOLKAR_PACK_DEAD_V029', 'EVENT_PEON_ROAD_SCORPID_PACK_DEAD')
        entered = bool(self.read('wBattleMode')[0])
        menus = self.move_menus
        for _ in range(420):
            entered = entered or bool(self.read('wBattleMode')[0])
            if entered and self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]:
                break
            if self.phase == 'team':
                # A genuine faint requires a live replacement; no HP fixtures.
                count = self.read('wPartyCount')[0]
                records = self.read('wPartyMon1', count * 48)
                choices = [i for i in range(count)
                           if records[i * 48 + 34] or records[i * 48 + 35]]
                assert choices, 'Ordinary progression lost the entire team'
                target = choices[0]
                current = self.read('wPeonTeamCursorV029')[0]
                if current != target:
                    self.press('up' if current > target else 'down', 30)
                else:
                    self.press('a', 60)
            elif self.move_menus > menus:
                menus = self.move_menus
                actor = self.read('wCurBattleMon')[0]
                record = self.read('wPartyMon1', (actor + 1) * 48)[actor * 48:(actor + 1) * 48]
                pool = int.from_bytes(bytes(record[29:31]), 'big')
                cost = 25 if record[0] == 66 and self.class_index == 2 else 15
                desired = 1 if harder_pack and record[3] and pool >= cost else 0
                for _ in range(5):
                    cursor = self.read('wMenuCursorY')[0]
                    if cursor == desired + 1:
                        break
                    self.press('up' if cursor > desired + 1 else 'down', 30)
                previous_menu = self.menus
                self.phase, self.context = 'turn_pending', None
                self.press('a', 120)
                self.wait(lambda: self.menus > previous_menu and self.phase == 'battle'
                          or self.phase == 'team' or not self.read('wBattleMode')[0], buttons=True)
            elif self.phase == 'battle':
                actor = self.read('wCurBattleMon')[0]
                record = self.read('wPartyMon1', (actor + 1) * 48)[actor * 48:(actor + 1) * 48]
                pool = int.from_bytes(bytes(record[29:31]), 'big')
                minimum = 25 if record[0] == 66 and self.class_index == 2 else 15
                supply = None
                if harder_pack:
                    self.harder_turn_observations.append({'frame': self.p.frame_count, 'actor': actor, 'record': record, 'pool': pool, 'native_battle_moves': self.read('wBattleMonMoves', 4), 'battle_hp': self.read('wBattleMonHP', 2)})
                if self.word('wBattleMonHP') * 4 <= self.word('wBattleMonMaxHP') * 2 and self.item_quantity(18):
                    supply = 18
                elif harder_pack and pool < minimum and self.item_quantity(63):
                    supply = 63
                if supply is not None:
                    self.open_bag_item(supply)
                    previous_menu = self.menus
                    self.press('a', 30)
                    self.wait(lambda: self.menus > previous_menu and self.phase == 'battle'
                              or self.phase == 'team' or not self.read('wBattleMode')[0], buttons=True)
                else:
                    for _ in range(5):
                        x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
                        if (x, y) == (1, 1):
                            break
                        self.press('left' if x > 1 else 'up', 30)
                    self.press('a', 60)
            else:
                self.press('a', 60)
        assert entered and self.read('wBattleMode') == [0] and self.event(flag)
        assert self.read('wBattleResult') == [0]
        assert not self.hook_errors and not self.pet_errors, (self.hook_errors, self.pet_errors)
        self.capture('ordinary_' + flag.lower())

    def unlock_third_member(self):
        assert self.map() == 14
        if not self.event('EVENT_PEON_STING_ACCEPTED'):
            self.talk_plain((10, 10), 'up')
        if not self.event('EVENT_PEON_SCORPID_DEFEATED'):
            self.navigate((17, 15))
            self.wait(lambda: self.phase == 'battle', buttons=True)
            self.finish_with_supplies('EVENT_PEON_SCORPID_DEFEATED')
        self.talk_plain((10, 10), 'up')
        assert self.event('EVENT_PEON_MAP_RECEIVED')
        self.heal_at_inn()
        self.travel_crossroads(); self.navigate((0, 4), expected_map=26)
        self.talk_plain((4, 4), 'left')
        assert self.event('EVENT_PEON_SARKOTH_ACCEPTED')
        self.navigate((5, 9), expected_map=27)
        self.navigate((4, 3))
        self.wait(lambda: self.phase == 'battle', buttons=True)
        self.finish_with_supplies('EVENT_PEON_SARKOTH_DEAD')
        self.navigate((5, 0), expected_map=26)
        self.talk_plain((4, 4), 'left')
        assert self.event('EVENT_PEON_SARKOTH_DONE')
        self.return_den()
        assert not self.event('EVENT_PEON_SARKOTH_REPORT_DONE')
        self.field_team(expected_locked=True)
        self.talk_plain((10, 10), 'up')
        assert self.event('EVENT_PEON_SARKOTH_REPORT_DONE')
        self.field_team(expected_locked=False)
        self.capture('third_team_slot_unlocked_by_actual_report')

    def battle_team_cancel(self):
        self.ready('battle')
        fields = {'wPartyMon1': 6 * 48, 'wEnemyMonHP': 2, 'wBattleMonHP': 2,
                  'wPlayerTurnsTaken': 1, 'wEnemyTurnsTaken': 1, 'wCurBattleMon': 1}
        before = {name: self.read(name, width) for name, width in fields.items()}
        for _ in range(5):
            x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
            if (x, y) == (2, 1):
                break
            self.press('right' if x < 2 else 'up', 30)
        self.press('a', 30); self.ready('team')
        if self.read('wPartyCount') == [2]:
            # The third place is visibly locked until an actual Sarkoth report.
            for _ in range(4):
                if self.read('wPeonTeamCursorV029') == [2]:
                    break
                self.press('down', 30)
            self.press('a', 90)
            assert self.phase == 'team'
        self.press('b', 60)
        self.wait(lambda: self.phase == 'battle', buttons=False)
        self.p.tick(60, True)
        assert before == {name: self.read(name, width) for name, width in fields.items()}
        self.verify_battle_chrome('ordinary_team_locked_refusal_and_cancel' if self.read('wPartyCount') == [2]
                                  else 'ordinary_team_cancel')
        self.surface('native_battle_team_cancel_without_turn')

    def battle_switch(self, index):
        self.ready('battle')
        before = self.ordinary_switches
        before_enemy = self.enemy_opportunities
        for _ in range(5):
            x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
            if (x, y) == (2, 1):
                break
            self.press('right' if x < 2 else 'up', 30)
        self.press('a', 30); self.ready('team')
        for _ in range(6):
            current = self.read('wPeonTeamCursorV029')[0]
            if current == index:
                break
            self.press('up' if current > index else 'down', 30)
        self.press('a', 40)
        self.wait(lambda: self.phase == 'battle', buttons=True)
        assert self.ordinary_switches == before + 1
        assert self.enemy_opportunities == before_enemy + 1, 'A voluntary switch must spend one enemy opportunity'
        assert self.read('wCurBattleMon') == [index]
        assert self.read('wBattleMonSpecies') == [self.read('wPartySpecies', 7)[index]]
        self.surface('true_native_battle_switch_to_' + str(index))
        self.verify_battle_chrome('ordinary_voluntary_switch')

    def flee_native(self):
        for _ in range(12):
            if not self.read('wBattleMode')[0]:
                break
            self.ready('battle')
            for _ in range(5):
                x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
                if (x, y) == (2, 2):
                    break
                self.press('right' if x < 2 else 'down', 30)
            self.press('a', 120)
            self.wait(lambda: self.phase == 'battle' or not self.read('wBattleMode')[0], buttons=True)
        assert not self.read('wBattleMode')[0]
        self.close_dialogue()

    def companion_battle_switch(self):
        self.travel_crossroads()
        if self.class_index == 1:
            self.navigate((3, 6)); self.press('up', 30); self.press('a', 30)
        else:
            self.navigate((0, 4), expected_map=26)
            self.navigate((3, 7)); self.press('up', 30); self.press('a', 30)
        self.wait(lambda: self.phase == 'battle', buttons=True)
        assert self.read('wCurBattleMon') == [1]
        assert self.read('wBattleMonSpecies') == [ROLES[self.class_index]]
        self.surface('preferred_companion_is_actual_starting_combatant')
        self.battle_team_cancel()
        self.battle_switch(0)
        self.flee_native(); self.return_den()

    def turn_in_class_quest_once(self):
        before = self.experience(), self.money()
        self.enter_class_trainer(); self.exit_trainer()
        assert self.event('EVENT_PEON_RECRUIT_DONE_V029')
        assert (self.experience(), self.money()) == (before[0] + 50, before[1] + 100)
        self.enter_class_trainer(); self.exit_trainer()
        assert (self.experience(), self.money()) == (before[0] + 50, before[1] + 100)
        assert self.item_quantity(RELICS[self.class_index]) == 1
        self.capture('class_quest_reward_committed_once')

    def buy_vendor_supplies(self, count, item, choice):
        before = self.money(), self.item_quantity(item)
        for _ in range(count):
            self.phase, self.context = 'overworld', None
            self.navigate((14, 10)); self.press('up', 30); self.press('a', 60)
            self.wait(lambda: self.phase == 'merchant', buttons=True)
            assert self.read('wMenuCursorY') == [1]
            for _ in range(choice - 1):
                self.press('down', 30)
            self.press('a', 90)
            self.close_dialogue()
            self.phase, self.context = 'overworld', None
        assert self.money() == before[0] - 25 * count
        assert self.item_quantity(item) == before[1] + count
        self.capture('actual_vendor_supplies_' + str(item))

    def buy_healing_supplies(self, count=10):
        return self.buy_vendor_supplies(count, 18, 2)

    def buy_mana_supplies(self, count=4):
        return self.buy_vendor_supplies(count, 63, 4)

    def cold_recruited_party(self):
        assert self.map() == 14
        self.navigate((12, 9)); self.press('down', 30)
        fields = {'wPlayerName': 11, 'wPartyCount': 1, 'wPartySpecies': 7,
            'wPartyMon1': 6 * 48, 'wPartyMonOTs': 6 * 11, 'wPartyMonNicknames': 6 * 11,
            'wEventFlags': 256, 'wMoney': 3, 'wMapGroup': 2, 'wXCoord': 1, 'wYCoord': 1,
            'wPokedexCaught': 32, 'wPokedexSeen': 32,
            'wNumItems': 1, 'wNumKeyItems': 1, 'wNumBalls': 1}
        before = {name: self.read(name, count) for name, count in fields.items()}
        for name, counter, width in (('wItems', 'wNumItems', 2), ('wKeyItems', 'wNumKeyItems', 1), ('wBalls', 'wNumBalls', 2)):
            before[name] = self.read(name, before[counter][0] * width + 1)
        saves = self.native_save_calls
        self.press('start')
        for _ in range(12):
            if self.read('wMenuCursorPosition') == [1]:
                break
            self.press('up', 30)
        for _ in range(3):
            self.press('down', 30)
        self.press('a')
        for _ in range(5):
            self.press('a', 180)
        assert self.native_save_calls == saves + 1
        self.p.stop(save=True); self.p = None
        battery = Path(str(self.rom) + '.ram')
        assert battery.stat().st_size == 32768
        self.open(); self.p.tick(1800, True); self.press('start')
        for _ in range(25):
            if self.map() == 14 and self.read('wScriptMode') == [0]:
                break
            self.press('a', 180)
        assert self.map() == 14 and self.read('wScriptMode') == [0]
        after = {name: self.read(name, len(values)) for name, values in before.items()}
        assert before == after, 'Native cold save changed a recruited party or shared resources'
        self.phase, self.context = 'overworld', None
        checkpoint = Path('/tmp/peon_v029_progress_batteries')
        checkpoint.mkdir(exist_ok=True)
        checkpoint_file = checkpoint / (sha(self.rom)[:12] + '_' + self.slug + '.ram')
        shutil.copyfile(battery, checkpoint_file)
        self.surface('actual_recruited_party_cold_continue')
        return {'battery_bytes': 32768, 'battery_sha256': sha(battery),
                'native_save_and_separate_cold_continue': True,
                'all_recruit_records_names_resources_hp_moves_events_bags_preserved': True}

    def save_current_map(self, output_battery):
        before = {name: self.read(name, count) for name, count in (
            ('wPlayerName', 11), ('wPartyCount', 1), ('wPartySpecies', 7),
            ('wPartyMon1', 6 * 48), ('wEventFlags', 256), ('wMoney', 3),
            ('wMapGroup', 2), ('wXCoord', 1), ('wYCoord', 1))}
        saves = self.native_save_calls
        self.press('start')
        for _ in range(12):
            if self.read('wMenuCursorPosition') == [1]:
                break
            self.press('up', 30)
        for _ in range(3):
            self.press('down', 30)
        self.press('a')
        for _ in range(5):
            self.press('a', 180)
        assert self.native_save_calls == saves + 1
        assert all(self.read(name, len(values)) == values for name, values in before.items())
        self.capture('genuine_progressed_senjin_native_save')
        self.p.stop(save=True)
        self.p = None
        source = Path(str(self.rom) + '.ram')
        assert source.stat().st_size == 32768
        output_battery.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, output_battery)
        return {'battery_path': str(output_battery), 'battery_sha256': sha(output_battery),
                'battery_bytes': 32768, 'ordinary_buttons_only': True,
                'native_save_routine_observed': True,
                'ram_edits': False, 'emulator_states_loaded': False, 'snapshot': before}

    def flee_pack_for_travel(self, label):
        self.ready('battle')
        before_xp, before_copper = self.experience(), self.money()
        before_flags = self.read('wEventFlags', 256)
        for _ in range(24):
            if not self.read('wBattleMode')[0]:
                break
            self.ready('battle')
            if self.word('wBattleMonHP') * 2 <= self.word('wBattleMonMaxHP') and self.item_quantity(18):
                self.open_bag_item(18)
                menus = self.menus
                self.press('a', 30)
                self.wait(lambda: self.menus > menus and self.phase == 'battle'
                          or self.phase == 'team' or not self.read('wBattleMode')[0], buttons=True)
                continue
            for _ in range(5):
                x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
                if (x, y) == (2, 2):
                    break
                self.press('right' if x < 2 else 'down', 30)
            menus = self.menus
            self.phase, self.context = 'run_pending', None
            self.press('a', 30)
            self.wait(lambda: self.menus > menus and self.phase == 'battle'
                      or self.phase == 'team' or not self.read('wBattleMode')[0], buttons=True)
            assert self.phase != 'team', 'Ordinary travel flee unexpectedly required a fainted replacement'
        assert self.read('wBattleMode') == [0] and self.read('wBattleResult') == [2]
        self.close_dialogue()
        assert self.experience() == before_xp and self.money() == before_copper
        assert self.read('wEventFlags', 256) == before_flags
        assert not self.hook_errors and not self.pet_errors
        self.capture(label + '_actual_native_run_no_xp_loot_or_retirement')

    def reach_senjin(self, output_battery):
        assert self.class_index == 2 and self.event('EVENT_PEON_SARKOTH_REPORT_DONE')
        self.field_team(0, expected_locked=False)
        self.heal_at_inn()
        self.navigate((20, 10), expected_map=15)
        self.navigate((28, 12), expected_map=29)
        self.navigate((3, 4))
        self.wait(lambda: self.phase == 'battle', buttons=True)
        self.flee_pack_for_travel('kolkar_west')
        # Both visible aggressors control this same packet. Passing the east
        # raider's adjacent cell after a flee starts it again, as intended.
        self.navigate((7, 4))
        self.wait(lambda: self.phase == 'battle', buttons=True)
        self.flee_pack_for_travel('kolkar_east')
        self.navigate((9, 4), expected_map=16)
        self.navigate((12, 23))
        self.wait(lambda: self.phase == 'battle', buttons=True)
        self.flee_pack_for_travel('road_scorpids')
        self.navigate((12, 24), expected_map=17)
        self.navigate((15, 5), expected_map=24)
        self.talk_plain((6, 5), 'up')
        records = self.read('wPartyMon1', 3 * 48)
        assert all(records[i + 34:i + 36] == records[i + 36:i + 38] for i in range(0, len(records), 48))
        self.navigate((5, 7), expected_map=17)
        self.navigate((10, 8))
        self.surface('actual_populated_senjin_after_progression')
        result = self.save_current_map(output_battery)
        result['harder_packs_entered_and_fled_using_real_RUN'] = True
        result['pack_victory_not_claimed'] = True
        return result


def ordinary_class(rom, symbols, index, senjin_battery=None):
    s = TeamSession(rom, symbols, index)
    try:
        s.continue_at_saved_location()
        s.heal_at_inn()
        s.buy_healing_supplies(4)
        s.class_relic_quest()
        s.field_team(expected_locked=True)
        if index == 2:
            # The initial true imp already occupies member2. This ordinary
            # correct-role target verifies the initial cap without fixtures.
            s.start_node(); s.relic_refusal('full_roster_relic_refusal')
            # Leave through native RUN instead of killing the class target.
            s.flee_native(); s.return_den()
            s.unlock_third_member(); s.heal_at_inn()
            s.start_node(); s.recruit_here(); s.return_den()
            assert s.read('wPartyCount') == [3]
            assert s.read('wPartySpecies', 4) == [66, 74, 74, 255]
            s.field_team(1, expected_locked=False)
            s.companion_battle_switch()
            s.turn_in_class_quest_once()
            assert not any(s.forbidden_calls.values()), s.forbidden_calls
            cold = s.cold_recruited_party()
            progressed = s.reach_senjin(senjin_battery) if senjin_battery else None
            return {'passed': True, 'ordinary_initial_cap_two_refusal': True,
                'starting_imp_is_true_record_two': True, 'no_state_injection': True,
                'class_relic_given_once': True, 'team_from_character_returns_cleanly': True,
                'native_capacity_three_progression': True,
                'third_imp_recruited_after_actual_sarkoth_report': True,
                'preferred_real_imp_can_switch_to_hero_with_native_turn': True,
                'class_quest_xp_and_copper_reward_once': True,
                'genuine_recruited_party_cold_save': cold,
                'genuine_progressed_senjin_battery': progressed,
                'native_capture_probability_observations': s.recruit_attempts,
                'forbidden_original_pokemon_flows': s.forbidden_calls,
                'actual_ppu_background_checks': s.bg_checks,
                'battle_font_and_actual_bold_glyphs': s.battle_chrome_checks}
        s.wrong_target_refusal()
        s.start_node(); s.recruit_here(); s.return_den()
        s.heal_at_inn(); s.field_team(1, expected_locked=True)
        assert s.read('wPartyCount') == [2]
        assert s.read('wPartyMon1Species') == [66]
        assert s.read('wPartyMon1', 2 * 48)[48] == ROLES[index]
        s.companion_battle_switch()
        s.turn_in_class_quest_once()
        assert not any(s.forbidden_calls.values()), s.forbidden_calls
        cold = s.cold_recruited_party()
        return {'passed': True, 'ordinary_buttons_only': True, 'ram_writes': False,
            'emulator_states_loaded': False, 'class_relic_given_once': True,
            'ordinary_wrong_target_family_refusal_no_item_or_turn_cost': True,
            'native_capture_probability_observations': s.recruit_attempts,
            'class_eligible_role_is_real_second_record': True,
            'hero_record_kept_at_slot_zero': True, 'field_preferred_actor_one': True,
            'real_companion_starts_and_switches_with_one_native_enemy_turn': True,
            'class_quest_xp_and_copper_reward_once': True,
            'genuine_recruited_party_cold_save': cold,
            'forbidden_original_pokemon_flows': s.forbidden_calls,
            'actual_ppu_background_checks': s.bg_checks,
            'team_from_character_returns_cleanly': True,
            'battle_font_and_actual_bold_glyphs': s.battle_chrome_checks}
    except Exception as error:
        s.capture('first_failure')
        failure = {'rom_sha256': sha(rom), 'class': CLASSES[index], 'error': repr(error),
            'map': s.map(), 'xy': s.position(), 'phase': s.phase,
            'script_mode': s.read('wScriptMode'), 'battle_mode': s.read('wBattleMode'),
            'party_count': s.read('wPartyCount'), 'party_species': s.read('wPartySpecies', 7),
            'actual_pc': hex(s.p.register_file.PC), 'actual_sp': hex(s.p.register_file.SP),
            'actual_rom_bank': s.read('hROMBank')[0], 'hook_errors': s.hook_errors,
            'pet_errors': s.pet_errors, 'native_recruit_attempts': s.recruit_attempts}
        failure['recent_native_input_events'] = s.events[-40:]
        failure['harder_turn_observations'] = s.harder_turn_observations[-20:]
        failure['actual_party_records'] = s.read('wPartyMon1', 6 * 48)
        failure['actual_actor_index'] = s.read('wCurBattleMon')
        (s.folder / 'first_failure.json').write_text(json.dumps(failure, indent=2) + '\n')
        raise
    finally:
        if s.p:
            s.p.stop(save=False)


def main():
    global OUT
    logging.disable(logging.CRITICAL)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--symbols', type=Path, required=True)
    parser.add_argument('--expected-sha', required=True)
    parser.add_argument('--class', dest='selected_class', choices=CLASSES)
    parser.add_argument('--senjin-battery', type=Path,
                        help='Optional private output battery reached with actual Warlock progression')
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.output.resolve()
    assert ROOT / 'references/generated/recruitment_v029' in OUT.parents
    OUT.mkdir(parents=True, exist_ok=True)
    assert sha(args.rom) == args.expected_sha
    symbols = migration.previous.symbols(args.symbols)
    migration.configure(ROOT)
    fixed_flags = recruitment_flag_indices()
    report = {'passed': False, 'rom_sha256': args.expected_sha,
              'symbols_sha256': sha(args.symbols), 'ordinary_buttons_only': True,
              'ram_writes': False, 'emulator_states_loaded': False, 'classes': {},
              'fixed_reserved_recruitment_flags': fixed_flags,
              'requested_class_scope': args.selected_class or 'all_three',
              'full_three_class_gate_passed': False}
    try:
        report['native_object_script_bank_gate'] = object_script_bank_gate(symbols)
        with tempfile.TemporaryDirectory(prefix='peon-v029-team-') as directory:
            for index, name in enumerate(CLASSES):
                if args.selected_class and args.selected_class != name:
                    continue
                rom = Path(directory) / (name + '.gbc')
                shutil.copyfile(args.rom, rom)
                source = migration.PRIVATE / (name + '_v028.gbc.ram')
                shutil.copyfile(source, Path(str(rom) + '.ram'))
                source_rtc = migration.PRIVATE / (name + '_v028.gbc.rtc')
                if source_rtc.exists():
                    shutil.copyfile(source_rtc, Path(str(rom) + '.rtc'))
                report['classes'][name] = ordinary_class(rom, symbols, index, args.senjin_battery if index == 2 else None)
        report['passed'] = True
        report['full_three_class_gate_passed'] = set(report['classes']) == set(CLASSES)
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
