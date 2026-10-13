#!/usr/bin/env python3
"""Native pack edge cases using clearly declared disposable save fixtures.

The fixtures start from genuine v028 class batteries. Map/level/HP/stats are
edited only in private emulator RAM, then saved with the real game menu and
cold-loaded. Actual map scripts, enemies, menus, turns, XP, retirement flags
and reward routines execute normally. This proves battle state transitions,
not ordinary leveling or the claimed difficulty curve; that belongs to the
team/progression route. No published or user battery is opened for writing.
"""
from pathlib import Path
import argparse
import hashlib
import json
import logging
import shutil
import tempfile

import numpy as np
from PIL import Image

import validate_peon_save_upgrade_v029 as migration
from validate_peon_recruit_art_v029 import ArtSession, decode, rom_slice
from validate_peon_resources_v029 import symbols_from, maximum
from validate_peon_battle_totems import BagSession
from validate_peon_combat_v028 import PolishSession

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/recruitment_v029/pack_runtime'
FLAGS = ('EVENT_PEON_KOLKAR_ARCHER_DEAD_V029', 'EVENT_PEON_KOLKAR_PACK_DEAD_V029',
         'EVENT_PEON_CAVE_CULTIST_FIRST_V029', 'EVENT_PEON_CAVE_CULTIST_DEAD',
         'EVENT_PEON_ROAD_SCORPID_PACK_FIRST', 'EVENT_PEON_ROAD_SCORPID_SECOND_V029',
         'EVENT_PEON_ROAD_SCORPID_PACK_DEAD')
PACKS = {
    'kolkar': {'map': 29, 'start': (1, 4), 'trigger': (2, 4), 'direction': 'right',
               'members': [(77, 7), (78, 8)], 'first': FLAGS[0], 'final': FLAGS[1], 'copper': 60},
    'cave': {'map': 20, 'start': (7, 3), 'trigger': (7, 3), 'direction': 'left',
             'members': [(88, 4), (74, 4)], 'first': FLAGS[2], 'final': FLAGS[3], 'copper': 25},
    'road': {'map': 16, 'start': (12, 20), 'trigger': (13, 23), 'direction': 'down',
             'members': [(27, 6), (27, 7), (158, 7)], 'first': FLAGS[4], 'final': FLAGS[6], 'copper': 75},
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class PackSession(ArtSession):
    def __init__(self, rom, symbols, index, case):
        self.case = case
        self.enemy_entries, self.faints, self.experience_calls = [], [], 0
        self.mutual_events = []
        self.reward_rolls, self.forbidden = 0, {}
        self.load_pending = None
        self.pack_errors = []
        self.sidebar_checks = []
        self.pack_scanline_frames, self.pack_scanline_peak = 0, 0
        self.pack_watch = False
        self.native_saves = 0
        self.cleanups = []
        self.pack_images = []
        super().__init__(rom, symbols, index, 'diagnostic/' + case)

    def open(self):
        super().open()
        def safe(label, callback):
            def observe(_):
                try:
                    callback()
                except Exception as error:
                    self.pack_errors.append({'hook': label, 'error': repr(error)})
            self.p.hook_register(*self.sym[label], observe, None)
        if 'mutual_faint' in self.case:
            def snapshot(label):
                self.mutual_events.append({'label': label, 'frame': self.p.frame_count,
                    'active': self.read('wCurBattleMon'), 'current_party': self.read('wCurPartyMon'),
                    'live_hp': self.read('wBattleMonHP', 2), 'party': self.state_of_party(),
                    'move': self.read('wCurPlayerMove'), 'enemy': self.read('wEnemyMonSpecies'),
                    'enemy_hp': self.read('wEnemyMonHP', 2), 'result': self.read('wBattleResult'),
                    'cursor': self.read('wMenuCursorX', 2)})
                (OUT / 'mutual_native_boundaries.json').write_text(json.dumps(self.mutual_events, indent=2) + '\n')
            for label in ('BattleCommand_Selfdestruct', 'UpdateFaintedPlayerMon',
                          'UpdateBattleMonInParty', 'PeonAdvanceWildPackV029',
                          'ForcePickPartyMonInBattle', 'PeonTeamForcedBattleV029.body',
                          'InitBattleMon'):
                safe(label, lambda label=label: snapshot(label))
        safe('LoadEnemyMon', self.enemy_loading)
        safe('PeonEncounterStartMessage', self.enemy_loaded)
        safe('PeonRecordPackFaintV029.body', self.enemy_fainted)
        safe('GiveExperiencePoints', lambda: setattr(self, 'experience_calls', self.experience_calls + 1))
        safe('PeonRollRarePotion', lambda: setattr(self, 'reward_rolls', self.reward_rolls + 1))
        safe('_SaveGameData', lambda: setattr(self, 'native_saves', self.native_saves + 1))
        bank, address = self.sym['CheckPayDay']
        assert self.p.memory[bank, address - 1] == 0xc9
        def cleanup_finished(_):
            state = self.read('wBattleMode') + self.read('wPeonRockbiterCharge') + self.read('wPeonLightningShieldCharges') + self.read('wPeonEarthTotemActive') + self.read('wPeonPlayerPoseActive')
            self.cleanups.append(state)
            assert state == [0] * 5, ('Actual cleanup returned with active field state', state)
        self.p.hook_register(bank, address - 1, cleanup_finished, None)
        for label in ('InitEnemyTrainer', 'WinTrainerBattle', 'EnemySwitch',
                      'EnemySwitch_SetMode', 'ShowBattleTextEnemySentOut', 'PokeBallEffect'):
            self.forbidden.setdefault(label, 0)
            safe(label, lambda label=label: self.forbidden.__setitem__(label, self.forbidden[label] + 1))

    def write(self, name, values):
        assert self.section.startswith('diagnostic/')
        BagSession.write(self, name, values)

    def press(self, key, frames=90):
        self.p.button(key, delay=4)
        self.tick(frames)
        # A pack's final KO can finish the battle during this bounded step.
        # Its map script still needs A to finish reward text; do not wait for
        # the now-inapplicable battle input phase in the older art harness.
        if self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]:
            self.phase, self.context = 'overworld', None

    def wait(self, predicate, buttons=False, limit=240):
        for _ in range(limit):
            if predicate():
                return
            if buttons:
                self.press('a', 40)
            else:
                self.tick(8)
        self.capture('unexpected_state')
        raise AssertionError(('native pack UI timed out', self.phase,
                              self.map(), self.position(), hex(self.p.register_file.PC),
                              self.enemy_entries[-3:], self.read('wBattleMode'),
                              self.read('wScriptMode')))

    def walk(self, direction):
        before, oldmap = self.position(), self.map()
        for _ in range(8):
            self.press(direction, 40)
            if self.position() != before:
                break
        assert self.map() == oldmap, (direction, 'unexpected warp', oldmap, self.map())
        assert sum(abs(a-b) for a,b in zip(before, self.position())) == 1, (direction, before, self.position())

    def capture(self, label):
        folder = OUT / self.case
        folder.mkdir(parents=True, exist_ok=True)
        self.p.screen.image.save(folder / (label + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(folder / (label + '_4x.png'))
        print(self.case, label, self.map(), self.position(), self.phase, flush=True)

    def state_of_party(self):
        data = self.read('wPartyMon1Species', self.read('wPartyCount')[0] * 48)
        return [{'species': data[i], 'hp': data[i + 34:i + 36],
                 'max_hp': data[i + 36:i + 38], 'status': data[i + 32],
                 'resource': data[i + 29:i + 31]} for i in range(0, len(data), 48)]

    def enemy_loading(self):
        if self.map() not in (16, 20, 29):
            return
        self.load_pending = {'party': self.state_of_party(),
                             'field_totem': self.read('wPeonEarthTotemActive')[0]}

    def enemy_loaded(self):
        if self.map() not in (16, 20, 29):
            return
        assert self.read('wBattleMode') == [1], 'pack changed into trainer mode'
        party = {'party': self.state_of_party(), 'field_totem': self.read('wPeonEarthTotemActive')[0]}
        assert self.load_pending == party, ('enemy replacement changed party HP/resources/status', self.load_pending, party)
        entry = {'species': self.read('wEnemyMonSpecies')[0], 'level': self.read('wEnemyMonLevel')[0],
                 'party_before_enemy_init': self.load_pending, 'party_after_enemy_init': party,
                 'native_wild_mode': True, 'no_intermediate_heal_or_refill': True}
        self.enemy_entries.append(entry)
        self.load_pending = None
        self.capture('enemy_' + str(len(self.enemy_entries)) + '_native_entrance')

    def enemy_fainted(self):
        self.faints.append({'species': self.read('wEnemyMonSpecies')[0],
                            'level': self.read('wEnemyMonLevel')[0], 'party': self.state_of_party()})

    def tick(self, frames):
        for _ in range(frames):
            self.p.tick(1, True)
            if self.pack_watch and self.read('wBattleMode')[0] and self.p.memory[0xff40] & 2:
                height = 16 if self.p.memory[0xff40] & 4 else 8
                counts = [0] * 144
                for top in list(self.p.memory[0xfe00:0xfea0])[::4]:
                    for y in range(max(0, top - 16), min(144, top - 16 + height)):
                        counts[y] += 1
                peak = max(counts)
                self.pack_scanline_peak = max(self.pack_scanline_peak, peak)
                self.pack_scanline_frames += 1
                assert peak <= 10, ('pack OAM scanline overflow', peak, self.read('wFXAnimID', 2))
                if len(self.pack_images) < 240 and self.read('wPeonPlayerPoseActive')[0]:
                    self.pack_images.append(self.p.screen.image.copy())
        assert not self.pack_errors, self.pack_errors[-5:]

    def continue_at(self, number):
        self.p.tick(1800, True)
        self.press('start')
        for _ in range(30):
            if self.map() == number and self.read('wScriptMode') == [0]:
                break
            self.press('a', 180)
        assert self.map() == number and self.read('wScriptMode') == [0]
        self.tick(120)

    def native_save_and_restart(self, number):
        assert self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]
        before = self.native_saves
        self.press('start')
        for _ in range(12):
            if self.read('wMenuCursorPosition') == [1]:
                break
            self.press('up', 30)
        for _ in range(3):
            self.press('down', 30)
        self.press('a')
        for _ in range(16):
            if self.native_saves > before:
                break
            self.press('a', 180)
        assert self.native_saves == before + 1
        for _ in range(10):
            self.press('a', 90)
            if self.read('wScriptMode') == [0] and self.phase == 'overworld':
                break
        self.p.stop(save=True)
        self.p = None
        assert Path(str(self.rom) + '.ram').stat().st_size == 32768
        self.open()
        self.continue_at(number)

    def create_saved_fixture(self, pack, add_ally=False):
        for flag in FLAGS:
            index = self.flags[flag]
            bank, address = self.sym['wEventFlags']
            self.p.memory[bank, address + index // 8] &= ~(1 << (index % 8))
        self.write('wPartyMon1Level', [8])
        self.write('wPartyMon1Exp', list((640).to_bytes(3, 'big')))
        for field, value in (('HP', 80), ('MaxHP', 80), ('Attack', 50), ('Defense', 40),
                              ('Speed', 70), ('SpclAtk', 50), ('SpclDef', 40)):
            self.write('wPartyMon1' + field, list(value.to_bytes(2, 'big')))
        self.write('wPartyMon1Status', [0])
        self.write('wPartyMon1Moves', [1, (84, 2, 247)[self.class_index], 150, 0])
        self.write('wPartyMon1PP', [35, 30, 40, 0])
        self.write('wPartyMon1PokerusStatus', [0x80])
        self.write('wPartyMon1CaughtData', list((20 if self.class_index == 1 else 100).to_bytes(2, 'big')))
        if add_ally:
            self.prepare_ally_fixture(95 if self.class_index == 0 else 68 if self.class_index == 1 else 74)
        self.set_private_map_fixture(pack)
        self.write('wBackupMapGroup', [26])
        self.write('wBackupMapNumber', [14])
        self.native_save_and_restart(pack['map'])
        self.capture('private_native_saved_fixture_cold_loaded')

    def prepare_private_third_earth_fixture(self):
        # Render both sidebar entries after the declared private fixture's
        # Sarkoth-report flag; ordinary cap/recruitment is tested separately.
        assert self.class_index == 0 and self.read('wPartyCount') == [2]
        record = bytearray(self.read('wPartyMon2Species', 48))
        record[34:36] = bytes((0, 120))
        self.write('wPartyMon3Species', list(record))
        self.write('wPartyMon3Nickname', self.read('wPartyMon2Nickname', 11))
        self.write('wPartyMon3OT', self.read('wPartyMon2OT', 11))
        self.write('wPartyCount', [3])
        self.write('wPartySpecies', [66, 95, 95, 0xff])
        index = self.flags['EVENT_PEON_SARKOTH_REPORT_DONE']
        bank, address = self.sym['wEventFlags']
        self.p.memory[bank, address + index // 8] |= 1 << (index % 8)
        self.native_save_and_restart(16)

    def enter_pack(self, pack):
        self.navigate(pack['trigger'])
        self.walk(pack['direction'])
        self.wait(lambda: self.phase == 'battle', buttons=True)
        self.tick(60)
        self.pack_watch = True
        self.check_sidebar()
        self.capture('native_pack_menu')

    def select_action(self, move_index):
        self.wait(lambda: self.phase == 'battle')
        start, menus = self.move_menus, self.menus
        for _ in range(5):
            x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
            if (x, y) == (1, 1):
                break
            self.press('left' if x > 1 else 'up', 30)
        self.press('a', 60)
        self.wait(lambda: self.move_menus > start)
        for _ in range(8):
            cursor = self.read('wMenuCursorY')[0]
            if cursor == move_index + 1:
                break
            self.press('down' if cursor < move_index + 1 else 'up', 30)
        self.tick(60)
        self.assert_move_resource_ui()
        self.press('a', 30)
        for _ in range(100):
            if self.read('wBattleMode') == [0] or self.menus > menus and self.phase == 'battle':
                break
            self.press('a', 90)
        if self.read('wBattleMode')[0]:
            assert self.phase == 'battle'
        self.tick(60)
        if self.read('wBattleMode')[0] and self.phase == 'battle':
            self.check_sidebar()

    def switch_to(self, index):
        self.context = None
        for _ in range(6):
            x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
            if (x, y) == (2, 1):
                break
            self.press('right' if x < 2 else 'up', 30)
        self.press('a', 60); self.wait(lambda: self.phase == 'team')
        for _ in range(6):
            cursor = self.read('wPeonTeamCursorV029')[0]
            if cursor == index:
                break
            self.press('down' if cursor < index else 'up', 30)
        before = self.menus
        self.press('a', 60)
        self.wait(lambda: self.read('wCurBattleMon') == [index] and self.menus > before and self.phase == 'battle', buttons=True)
        self.tick(60)
        self.check_sidebar()

    def check_sidebar(self):
        assert self.read('wBattleMode') == [1]
        active = self.read('wCurBattleMon')[0]
        records = self.state_of_party()
        displayed = [i for i in range(min(3, len(records))) if i != active][:2]
        tiles, attrs = self.read('wTilemap', 360), self.read('wAttrmap', 360)
        actual = np.array(self.p.screen.image.convert('RGB')) >> 3
        bars = rom_slice(self.rom.read_bytes(), self.sym['PeonAllyHPBarsV029'], 5 * 16)
        heads = {66: 'machamp', 95: 'onix', 74: 'geodude', 68: 'machamp'}
        observations = []
        for slot, index in enumerate(displayed):
            record = records[index]
            head = (ROOT / 'gfx/peon_native_v029' / heads[record['species']] / 'head_8x8.2bpp').read_bytes()
            hp, maxhp = int.from_bytes(bytes(record['hp']), 'big'), int.from_bytes(bytes(record['max_hp']), 'big')
            level = min(4, max(1, hp * 4 // maxhp)) if hp and maxhp else 0
            bar = bars[level * 16:level * 16 + 16]
            row = (5, 8)[slot]
            address = 0x8a90 + slot * 32
            assert bytes(self.p.memory[1, address:address+32]) == head + bar, ('sidebar native bank1 packet', slot, index)
            for offset, picture in enumerate((head, bar)):
                cell = (row + offset) * 20
                assert (tiles[cell], attrs[cell]) == (0xa9 + slot * 2 + offset, 8), ('sidebar live tile/attribute', slot, index, tiles[cell], attrs[cell])
                pixels = decode(picture, 8, 8)
                y = (row + offset) * 8
                assert np.array_equal(actual[y:y+8, :8], self.palette(0)[pixels]), ('sidebar actual RGB555 raster', slot, index, offset)
            observations.append({'party_index': index, 'species': record['species'], 'hp': hp,
                                 'max_hp': maxhp, 'four_segment_bar': level})
        for slot in range(len(displayed), 2):
            for row in ((5, 6) if slot == 0 else (8, 9)):
                if tiles[row*20] != 0x7f or attrs[row*20] != 0:
                    self.capture('sidebar_stale_unused_cell_failure')
                assert tiles[row*20] == 0x7f and attrs[row*20] == 0, ('stale unused sidebar cell', slot, row, tiles[row*20], attrs[row*20])
        font = rom_slice(self.rom.read_bytes(), self.sym['FontBattleExtra'], 12*16)
        assert bytes(self.p.memory[0, 0x9600:0x96c0]) == font, 'Native battle HP/level chrome differs from frozen source'
        bold = PolishSession.assert_current_bold_name_glyphs(self)
        self.sidebar_checks.append({'active_index': active, 'native_battle_font_packet_exact': True, 'live_bold_name_glyphs': bold, 'displayed': observations,
                                    'real_bank1_packet_and_RGB555_pixels_exact': True,
                                    'additional_OAM_objects': 0})

    def place_and_keep_field_totem(self):
        before = self.menus
        quantity = self.item_quantity(148)
        self.open_inventory(148, battle=True)
        self.press('a', 30)
        self.wait(lambda: self.menus > before and self.phase == 'battle', buttons=True)
        assert self.read('wPeonEarthTotemActive') == [1]
        assert self.item_quantity(148) == quantity, 'Totem must remain reusable'
        source = (ROOT / 'gfx/peon_pets_v026/earth_totem_v026.2bpp').read_bytes()
        assert bytes(self.p.memory[1, 0x8860:0x88c0]) == source
        self.switch_to(1)
        assert self.read('wPeonEarthTotemActive') == [1], 'Ally switch incorrectly despawned the field totem'
        assert bytes(self.p.memory[1, 0x8860:0x88c0]) == source
        self.capture('native_earth_ally_and_persistent_field_totem')
        self.switch_to(0)
        assert self.read('wPeonEarthTotemActive') == [1]

    def win_pack(self, final_flag):
        for _ in range(35):
            if self.read('wBattleMode')[0]:
                use_spell = self.read('wBattleMonSpecies') == [66] and self.class_index != 1
                self.select_action(1 if use_spell else 0)
            else:
                self.press('a', 90)
            if self.event(final_flag) and self.read('wScriptMode') == [0]:
                break
        assert self.event(final_flag) and self.read('wBattleResult') == [0]
        assert self.read('wBattleMode') == [0]
        assert not any(self.forbidden.values()), self.forbidden
        self.capture('full_native_pack_victory')

    def flee(self):
        before = self.read('wBattleResult')[0]
        for _ in range(12):
            for _ in range(4):
                x, y = self.read('wMenuCursorX')[0], self.read('wMenuCursorY')[0]
                if (x, y) == (2, 2):
                    break
                self.press('right' if x < 2 else 'down', 30)
            self.press('a', 60)
            if self.read('wBattleMode') == [0]:
                break
            self.wait(lambda: self.phase == 'battle', buttons=True)
        self.close_dialogue()
        assert self.read('wBattleMode') == [0] and self.read('wBattleResult') != [0], before

    def defeat_first_member(self):
        for _ in range(12):
            if len(self.enemy_entries) >= 2:
                return
            self.select_action(1)
        raise AssertionError('First native pack member did not retire')

    def settle_world(self):
        for _ in range(100):
            if self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]:
                return
            self.press('a', 90)
        raise AssertionError(('Native battle/recovery did not settle', self.map(), self.phase))

    def place_saved_map(self, pack):
        self.set_private_map_fixture(pack)
        self.native_save_and_restart(pack['map'])

    def set_private_map_fixture(self, pack):
        self.write('wMapGroup', [26, pack['map']])
        x, y = pack['start']
        self.write('wXCoord', [x]); self.write('wYCoord', [y])
        # Native Continue retains the saved player object. A private map
        # fixture must synchronize its four native object coordinates too;
        # changing only wXCoord/wYCoord creates an artificial blocked walk.
        self.write('wPlayerMapX', [x + 4]); self.write('wPlayerMapY', [y + 4])
        self.write('wPlayerLastMapX', [x + 4]); self.write('wPlayerLastMapY', [y + 4])
        bank, address = self.sym['wMapObjects']
        self.p.memory[bank, address + 2] = y + 4
        self.p.memory[bank, address + 3] = x + 4


def open_case(rom, sym, index, case, temp):
    target = Path(temp) / (case + '.gbc')
    shutil.copyfile(rom, target)
    source = migration.PRIVATE / (('shaman', 'warrior', 'warlock')[index] + '_v028.gbc.ram')
    shutil.copyfile(source, Path(str(target) + '.ram'))
    s = PackSession(target, sym, index, case)
    s.continue_at((14, 23, 22)[index])
    return s


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--symbols', type=Path, required=True)
    parser.add_argument('--expected-sha', required=True)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    assert sha(args.rom) == args.expected_sha
    syms = symbols_from(args.symbols)
    migration.configure(ROOT)
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'rom_sha256': args.expected_sha, 'symbols_sha256': sha(args.symbols),
              'passed': False, 'status': 'RUNNING', 'user_battery_files_opened': False,
              'fixture': 'Private native-saved level8/80HP custom-stat records and map placement; actual game scripts/menus thereafter.',
              'ordinary_progression_claimed': False, 'cases': {}}
    try:
        with tempfile.TemporaryDirectory(prefix='peon-v029-packs-') as temp:
            for name, pack in PACKS.items():
                s = open_case(args.rom, syms, 0, name + '_full', temp)
                try:
                    s.create_saved_fixture(pack, add_ally=True)
                    if name == 'road':
                        s.prepare_private_third_earth_fixture()
                    money, xp = s.money(), s.experience()
                    s.enter_pack(pack)
                    s.select_action(2)  # real harmless action lets the actual enemy attack/animate
                    if name == 'kolkar':
                        s.place_and_keep_field_totem()
                    s.win_pack(pack['final'])
                    actual = [(entry['species'], entry['level']) for entry in s.enemy_entries]
                    assert actual == pack['members'], (name, actual, pack['members'])
                    assert s.experience_calls == len(pack['members'])
                    assert s.money() == money + pack['copper'] and s.experience() > xp
                    assert s.reward_rolls == 1
                    # Battle padding shares the Miscellaneous union with
                    # wSurroundingTiles. After map reload those bytes are terrain,
                    # not a live totem flag. Check the real cleanup boundary.
                    assert s.cleanups and s.cleanups[-1] == [0] * 5
                    saved_flags = bytes(s.read('wEventFlags', 256))
                    s.native_save_and_restart(pack['map'])
                    assert saved_flags == bytes(s.read('wEventFlags', 256))
                    money_after, xp_after = s.money(), s.experience()
                    s.navigate(pack['trigger'])
                    s.press(pack['direction'], 90)
                    s.close_dialogue()
                    assert s.read('wBattleMode') == [0]
                    assert (s.money(), s.experience()) == (money_after, xp_after)
                    report['cases'][name + '_full'] = {
                        'native_members': actual, 'player_state_unchanged_during_each_replacement': s.enemy_entries,
                        'xp_once_per_member': len(pack['members']), 'copper_once': pack['copper'],
                        'one_rare_loot_roll_only_after_complete_win': True,
                        'native_item_field_totem_persists_through_ally_switches_and_next_enemy': name == 'kolkar',
                        'native_save_cold_continue_and_no_repeat_encounter_or_rewards': True,
                        'forbidden_trainer_or_ball_calls': s.forbidden,
                        'consecutive_OAM_frames': s.pack_scanline_frames, 'peak_OBJ_per_scanline': s.pack_scanline_peak,
                        'native_group_heads_and_HP_bars': s.sidebar_checks,
                        'private_report_unlocked_three_member_sidebar_fixture': name == 'road'}
                finally:
                    if s.p:
                        s.p.stop(save=False)

            s = open_case(args.rom, syms, 0, 'road_lowlevel_visibility', temp)
            try:
                s.create_saved_fixture(PACKS['road'])
                s.write('wPartyMon1Level', [2])
                s.write('wPartyMon1Exp', [0, 0, 10])
                s.native_save_and_restart(16)
                actors = s.read('wObjectStructs', 13 * 40)
                assert not any(actors[n*40] and actors[n*40+1] == 8 for n in range(1,13)), 'Low-level road pack remained visible after native hide callback'
                assert not s.event(FLAGS[6]), 'Transient hide permanently retired the road pack'
                s.write('wPartyMon1Level', [8])
                s.write('wPartyMon1Exp', [0, 2, 128])
                s.native_save_and_restart(16)
                actors = s.read('wObjectStructs', 13 * 40)
                assert any(actors[n*40] and actors[n*40+1] == 8 for n in range(1,13)), 'Eligible road pack failed to reappear'
                assert not s.event(FLAGS[6])
                s.capture('native_eligible_road_pack_reappears_without_retirement')
                report['cases']['road_lowlevel_visibility'] = {
                    'private_native_saved_level2_then_level8': True,
                    'level2_native_callback_hides_internal_map_object8': True,
                    'level8_native_callback_restores_pack': True,
                    'transient_hide_preserves_saved_retirement_flags': True}
            finally:
                if s.p:
                    s.p.stop(save=False)

            pack = PACKS['kolkar']
            s = open_case(args.rom, syms, 0, 'kolkar_partial_flee', temp)
            try:
                s.create_saved_fixture(pack)
                copper = s.money()
                s.enter_pack(pack)
                s.defeat_first_member()
                xp = s.experience()
                assert s.event(pack['first']) and not s.event(pack['final'])
                s.flee(); s.settle_world()
                assert s.reward_rolls == 0 and s.money() == copper and s.experience() == xp
                assert s.event(pack['first']) and not s.event(pack['final'])
                s.native_save_and_restart(pack['map'])
                assert s.event(pack['first']) and not s.event(pack['final'])
                s.enter_pack(pack)
                assert [(e['species'], e['level']) for e in s.enemy_entries] == [(77, 7), (78, 8), (78, 8)]
                assert s.experience() == xp, 'Cold return granted replay XP'
                s.win_pack(pack['final'])
                assert s.experience_calls == 2 and s.reward_rolls == 1
                assert s.money() == copper + 60
                report['cases']['kolkar_partial_flee'] = {
                    'native_enemy_entries': [(e['species'], e['level']) for e in s.enemy_entries],
                    'first_member_retired_before_flee_and_cold_continue': True,
                    'cold_return_starts_only_surviving_member': True,
                    'xp_calls_total_two_not_three': s.experience_calls,
                    'no_loot_or_copper_on_flee_one_reward_after_final_win': True,
                    'forbidden_trainer_or_ball_calls': s.forbidden}
            finally:
                if s.p:
                    s.p.stop(save=False)

            s = open_case(args.rom, syms, 0, 'kolkar_partial_loss', temp)
            try:
                s.create_saved_fixture(pack)
                copper = s.money()
                s.enter_pack(pack)
                s.defeat_first_member()
                xp = s.experience()
                for prefix in ('wBattleMon', 'wPartyMon1'):
                    s.write(prefix + 'HP', [0, 1])
                    s.write(prefix + 'Moves', [150, 0, 0, 0])
                    s.write(prefix + 'PP', [40, 0, 0, 0])
                # Deleting later private fixture slots must also reset the
                # remembered native selection; index1 would highlight move0.
                s.write('wCurMoveNum', [0])
                s.select_action(0)
                s.settle_world()
                assert s.read('wBattleResult') == [1]
                assert s.event(pack['first']) and not s.event(pack['final'])
                assert s.reward_rolls == 0 and s.money() <= copper and s.experience() == xp
                s.place_saved_map(pack)
                s.enter_pack(pack)
                assert [(e['species'], e['level']) for e in s.enemy_entries] == [(77, 7), (78, 8), (78, 8)]
                assert s.experience() == xp
                report['cases']['kolkar_partial_loss'] = {
                    'fixture': 'After the first real KO, only private caster HP=1 and harmless move replaced to force loss.',
                    'real_native_loss_and_hearth_recovery': True,
                    'first_member_retirement_survives_loss_native_save_cold_continue': True,
                    'remaining_enemy_only_no_repeated_xp_or_reward': True,
                    'forbidden_trainer_or_ball_calls': s.forbidden}
            finally:
                if s.p:
                    s.p.stop(save=False)

            s = open_case(args.rom, syms, 0, 'kolkar_mutual_faint', temp)
            try:
                s.create_saved_fixture(pack, add_ally=True)
                s.enter_pack(pack)
                for prefix in ('wBattleMon', 'wPartyMon1'):
                    s.write(prefix + 'HP', [0, 1])
                    s.write(prefix + 'Moves', [120, 0, 0, 0])
                    s.write(prefix + 'PP', [5, 0, 0, 0])
                s.write('wEnemyMonHP', [0, 1])
                s.write('wCurMoveNum', [0])
                # A real self-destruct action drives the original mutual-faint
                # branch; selecting the next real ally uses the new TEAM UI.
                menus, moves = s.menus, s.move_menus
                s.press('a', 60); s.wait(lambda: s.move_menus > moves)
                s.press('a', 30)
                s.wait(lambda: s.phase == 'team', buttons=True)
                assert s.read('wEnemyMonSpecies') == [78] and s.read('wEnemyMonHP', 2) != [0, 0]
                assert s.event(pack['first']) and not s.event(pack['final'])
                for _ in range(4):
                    if s.read('wPeonTeamCursorV029') == [1]:
                        break
                    s.press('down', 30)
                s.press('a', 60)
                s.wait(lambda: s.read('wCurBattleMon') == [1] and s.menus > menus and s.phase == 'battle', buttons=True)
                s.tick(60)
                assert s.read('wBattleMonSpecies') == [95]
                assert s.read('wEnemyMonSpecies') == [78]
                assert s.read('wPartyMon1HP', 2) == [0, 0], ('mutual hero record after native forced switch', s.state_of_party(), s.mutual_events)
                s.check_sidebar()
                assert not any(s.forbidden.values()), s.forbidden
                s.capture('native_mutual_faint_forced_earth_ally_against_live_raider')
                copper_before_final = s.money()
                s.win_pack(pack['final'])
                assert s.money() == copper_before_final + 60
                assert s.experience_calls == 2 and s.reward_rolls == 1
                report['cases']['kolkar_mutual_faint'] = {
                    'fixture': 'Private hero/first-target HP1 plus Selfdestruct120; native action and forced-switch controls.',
                    'next_live_enemy_loaded_before_forced_ally_choice': True,
                    'native_team_ally_switch_hero_slot_not_reordered': True,
                    'active_earth_spirit_species': 95, 'remaining_raider_species': 78,
                    'earth_ally_completes_native_WIN_without_trainer_transition': True,
                    'xp_calls_total_two_copper60_and_one_loot_roll_only_on_final_win': True,
                    'forbidden_empty_enemy_trainer_party_switch_calls': s.forbidden,
                    'consecutive_OAM_frames': s.pack_scanline_frames,
                    'peak_OBJ_per_scanline': s.pack_scanline_peak,
                        'native_group_heads_and_HP_bars': s.sidebar_checks,
                        'private_report_unlocked_three_member_sidebar_fixture': name == 'road'}
            finally:
                if s.p:
                    s.p.stop(save=False)
    except Exception as error:
        report['failure'] = repr(error)
        (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
        raise
    assert sha(args.rom) == args.expected_sha
    report['passed'], report['status'] = True, 'PASS'
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Native v029 pack validation PASS', args.expected_sha)


if __name__ == '__main__':
    main()
