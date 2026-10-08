#!/usr/bin/env python3
"""Native fixed-panel and inventory edge checks in isolated emulator games.

The normal phase uses ordinary buttons through the real intro and Shaman kit.
Diagnostics restore that private state and explicitly substitute bags, levels,
legacy flags, and damage to exercise finite edge cases. No user saves are used.
"""
import argparse
import hashlib
import io
import json
import logging
from pathlib import Path
import re
import shutil
import tempfile

from PIL import Image
from pyboy import PyBoy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/deep_polish/ui'


def symbols():
    result = {}
    for row in (ROOT / 'pokecrystal.sym').read_text().splitlines():
        fields = row.split()
        if len(fields) == 2 and ':' in fields[0]:
            result[fields[1]] = tuple(int(n, 16) for n in fields[0].split(':'))
    return result


def text_encoding():
    return {m[1]: int(m[2], 16) for m in re.finditer(
        r'charmap\s+"([^"\n]+)",\s+\$([0-9a-f]+)',
        (ROOT / 'constants/charmap.asm').read_text())}


class Check:
    def __init__(self, rom, sym):
        self.sym = sym
        self.p = PyBoy(str(rom), window='null', sound_emulated=False, log_level='ERROR')
        self.p.set_emulation_speed(0)
        self.phase = None
        self.font_uploads = 0
        self.naming = False
        self.naming_done = False
        self.errors = []
        for label, phase in [('PeonBags', 'bags'), ('PeonInventory.input', 'inventory'),
                             ('PeonCharacterSheet', 'character'), ('StartMenu.GetInput', 'start')]:
            self.p.hook_register(*sym[label], lambda phase: setattr(self, 'phase', phase), phase)
        self.p.hook_register(*sym['PeonAskName'], lambda _: setattr(self, 'naming', True), None)
        self.p.hook_register(*sym['LoadStandardFont'], lambda _: setattr(self, 'font_uploads', self.font_uploads + 1), None)
        self.chars = text_encoding()

    def read(self, name, length=1):
        bank, address = self.sym[name]
        return list(self.p.memory[address:address + length] if address >= 0xe000
                    else self.p.memory[bank, address:address + length])

    def write(self, name, values):
        bank, address = self.sym[name]
        if address >= 0xe000:
            self.p.memory[address:address + len(values)] = values
        else:
            self.p.memory[bank, address:address + len(values)] = values

    def press(self, key, frames=100):
        self.p.button(key, delay=8)
        self.p.tick(frames, True)

    def encode(self, text):
        return [self.chars[c] for c in text]

    def row(self, y, x=0, width=20):
        return self.read('wTilemap', 360)[20 * y + x:20 * y + x + width]

    def has(self, text, y):
        encoded = self.encode(text)
        row = self.row(y)
        return any(row[x:x + len(encoded)] == encoded for x in range(21 - len(encoded)))

    def capture(self, slug):
        self.p.tick(40, True)
        self.p.screen.image.save(OUT / (slug + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / (slug + '_4x.png'))

    def chrome(self):
        tiles, attrs = self.read('wTilemap', 360), self.read('wAttrmap', 360)
        for y in range(18):
            for x in range(20):
                if y not in (0, 17) and x not in (0, 19):
                    continue
                expect = {(0, 0): 0x79, (19, 0): 0x7b, (0, 17): 0x7d, (19, 17): 0x7e}.get(
                    (x, y), 0x7a if y in (0, 17) else 0x7c)
                assert tiles[y * 20 + x] == expect, ('frame overwritten', x, y)
                assert attrs[y * 20 + x] == 3, ('frame palette changed', x, y)
        assert all(attrs[y * 20 + x] == 1 for y in (1, 2) for x in range(1, 19))
        bank, address = self.sym['hBGMapAddress']
        bg = self.p.memory[address] | (self.p.memory[address + 1] << 8)
        assert [self.p.memory[1, bg + y * 32 + x] for y in range(18) for x in range(20)] == attrs
        return {'frame': [0, 0, 19, 17], 'native_vram_attributes_match': True, 'no_border_clipping': True}

    def start(self, selection):
        self.press('start')
        for _ in range(15):
            cursor = self.read('wMenuCursorPosition')[0]
            if cursor == selection:
                break
            self.press('up' if cursor > selection else 'down', 35)
        assert self.read('wMenuCursorPosition') == [selection]
        assert self.read('wMenuItemsList', 8) == [7, 1, 2, 3, 4, 9, 5, 6]
        assert self.read('wMenuBorderTopCoord') == [0]
        assert self.read('wMenuBorderBottomCoord') == [15]
        assert self.read('wMenuBorderLeftCoord') == [6]
        assert self.read('wMenuBorderRightCoord') == [19]

    def bag(self):
        self.start(2)
        self.press('a')
        assert self.phase == 'bags'
        self.chrome()
        self.press('a')
        assert self.phase == 'inventory'
        self.chrome()

    def close(self):
        self.press('b')
        self.press('b')
        assert self.read('wMapGroup', 2) == [26, 14] and self.read('wScriptMode') == [0]

    def fresh(self):
        self.p.tick(240, True)
        self.press('start'); self.press('down'); self.press('a')
        for _ in range(160):
            if self.read('wMapGroup', 2) == [26, 14] and self.read('wScriptMode') == [0]:
                break
            if self.naming and not self.naming_done:
                self.p.tick(120, True)
                # Five actual letters reach the current persisted-name limit.
                for index in range(5):
                    self.press('a', 35)
                    if index < 4:
                        self.press('right', 35)
                self.press('start', 40); self.press('a')
                self.naming_done = True
            self.press('a')
        assert self.naming_done
        assert self.read('wMapGroup', 2) == [26, 14] and self.read('wScriptMode') == [0]
        self.p.tick(120, True)
        assert self.read('wPlayerName', 11)[:10] == self.encode('Péon ABCDE')

    def fixture_bag(self, entries):
        self.write('wNumItems', [len(entries)])
        values = [v for entry in entries for v in entry] + [0xff]
        self.write('wItems', values)

    def qty(self, item):
        values = self.read('wItems', self.read('wNumItems')[0] * 2)
        return sum(values[i + 1] for i in range(0, len(values), 2) if values[i] == item)


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-rom-sha')
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.out
    OUT.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest()
    if args.expected_rom_sha:
        assert digest == args.expected_rom_sha
    logging.disable(logging.CRITICAL)
    sym = symbols()
    report = {'rom_sha256': digest, 'normal_phase': {'ordinary_buttons_only': True,
              'ram_edits': False, 'savestates_loaded': False}, 'diagnostics': {
              'isolated_ram_edits_and_private_state_restore': True}}
    with tempfile.TemporaryDirectory(prefix='peon-deep-ui-') as folder:
        rom = Path(folder) / 'ui.gbc'
        shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
        s = Check(rom, sym)
        try:
            s.fresh()
            state = io.BytesIO(); s.p.save_state(state)
            def restore():
                state.seek(0); s.p.load_state(state); s.phase = 'overworld'
            s.start(1); s.capture('normal_fixed_start_menu')
            s.press('a'); s.capture('normal_character_maximum_name')
            report['normal_phase']['character'] = s.chrome()
            assert s.has('Péon ABCDE', 1)
            assert s.has('MACE STRIKE', 12) and s.has('LIGHTN.BOLT', 13)
            assert s.row(9, 13, 1) == s.encode('/')
            assert s.has('--', 14) and s.has('--', 15)
            s.close()
            s.bag(); s.capture('normal_starter_earth_totem')
            assert s.read('wNumItems') == [1] and s.qty(0x94) == 1
            assert s.has('COUNT', 8) and s.has('ACT BEFORE TARGET', 9)
            before = s.read('wPartyMon1Species', 48) + s.read('wNumItems', 42)
            s.press('a'); s.press('a')
            assert s.phase == 'inventory' and s.has('ONLY IN COMBAT', 14)
            assert before == s.read('wPartyMon1Species', 48) + s.read('wNumItems', 42)
            s.capture('normal_invalid_totem_use_feedback'); s.chrome(); s.close()
            report['normal_phase'].update(fixed_start_entries=7, fixed_start_bounds=[6, 0, 19, 15],
                maximum_name_fits=True, actual_starter_totem_preserved_on_invalid_use=True,
                actual_actions_and_health_maximum_shown=True, return_to_world=True)

            # Legacy flag and help-option diagnostics must not duplicate CHARACTER/MAP.
            restore()
            flags = s.read('wStatusFlags')[0] | 1
            s.write('wStatusFlags', [flags])
            s.write('wPokegearFlags', [s.read('wPokegearFlags')[0] | 128])
            s.write('wOptions2', [s.read('wOptions2')[0] | 1])
            s.start(7); s.capture('diagnostic_legacy_flags_fixed_start')
            report['diagnostics']['legacy_flags_keep_seven_entries_and_fixed_bounds'] = True
            s.press('b')

            # Distinct learned actions must appear instead of the old hardcoded pair.
            restore(); s.write('wPartyMon1Moves', [1, 0x54, 0x34, 0x69])
            s.start(1); s.press('a')
            assert s.has('FLAME SHOCK', 14) and s.has('HEAL.WAVE', 15)
            s.chrome(); s.capture('diagnostic_character_prepared_spells'); s.close()
            report['diagnostics']['character_displays_current_four_action_names'] = True

            # Inventory navigation keeps resident fonts and a stable rarity ribbon.
            restore(); s.fixture_bag([(0x94, 1), (0x12, 99), (0x2e, 5), (0x95, 2), (0x89, 1), (0x91, 1)])
            s.bag(); uploads = s.font_uploads
            for index, item in enumerate([0x94, 0x12, 0x2e, 0x95, 0x89, 0x91]):
                if index:
                    s.press('right', 70)
                assert s.read('wMenuCursorY') == [index] and s.read('wNamedObjectIndex') == [item]
                assert s.row(8, 8, 2) == s.encode(str(s.qty(item)).rjust(2))
                assert s.row(5, 7, 2) == s.encode(str(index + 1).rjust(2))
                s.chrome()
                if item == 0x89:
                    assert all(s.read('wAttrmap', 360)[180 + x] == 2 for x in range(1, 19))
                    s.press('a', 70)
                    assert s.read('wPartyMon1Item') == [0x89] and s.has('EQUIPPED', 8)
                    assert s.row(8, 10, 1) == s.encode(' '), 'Quantity/equipped labels need a spacer'
                    s.capture('diagnostic_equipped_weapon')
                if item == 0x91:
                    assert all(s.read('wAttrmap', 360)[180 + x] == 0 for x in range(1, 19))
                    assert s.has('QUEST PROOF', 9)
                    s.capture('diagnostic_quest_proof_ribbon_reset')
            assert s.font_uploads == uploads
            s.close()
            report['diagnostics']['six_items_scroll_without_font_reload'] = True
            report['diagnostics']['native_quantity_and_current_index_match_including_99_units'] = True
            report['diagnostics']['rarity_attribute_reset_and_equipped_indicator'] = True

            # Full-health potion, full-charge water and food are not wasted.
            restore(); s.fixture_bag([(0x94, 1), (0x12, 3), (0x2e, 5), (0x95, 2)])
            s.bag()
            before = s.read('wPartyMon1Species', 48) + s.read('wNumItems', 42)
            for item, text in [(0x12, 'CANNOT HEAL NOW'), (0x2e, 'CHARGES ARE FULL'), (0x95, 'CANNOT EAT NOW')]:
                s.press('right', 70); assert s.read('wNamedObjectIndex') == [item]
                s.press('a', 70)
                assert s.has(text, 14)
                assert before == s.read('wPartyMon1Species', 48) + s.read('wNumItems', 42)
                s.chrome()
            s.capture('diagnostic_full_health_food_feedback'); s.close()
            report['diagnostics']['full_health_and_charges_consume_nothing'] = True

            # Healing a real native HP field spends one unit, retains its index,
            # then clamps to the preceding stack when the final last unit is used.
            restore(); s.fixture_bag([(0x94, 1), (0x12, 2)])
            maximum = int.from_bytes(bytes(s.read('wPartyMon1MaxHP', 2)), 'big')
            s.write('wPartyMon1HP', (maximum - 10).to_bytes(2, 'big'))
            s.bag(); s.press('right', 70); s.press('a', 130)
            assert s.qty(0x12) == 1 and s.read('wMenuCursorY') == [1]
            assert s.read('wNamedObjectIndex') == [0x12]
            s.capture('diagnostic_consumed_stack_selection_retained')
            s.write('wPartyMon1HP', (maximum - 10).to_bytes(2, 'big'))
            s.press('a', 130)
            assert s.qty(0x12) == 0 and s.read('wMenuCursorY') == [0]
            assert s.read('wNamedObjectIndex') == [0x94]
            s.chrome(); s.capture('diagnostic_last_stack_cursor_clamped'); s.close()
            report['diagnostics']['successful_use_retains_stack_then_clamps_last_removed_stack'] = True

            restore(); s.fixture_bag([]); s.bag()
            s.press('a', 70); s.chrome()
            assert s.has('EMPTY', 7) and s.has('NO ITEMS TO USE', 13)
            assert s.read('wNumItems') == [0]
            s.capture('diagnostic_empty_inventory'); s.close()
            report['diagnostics']['empty_inventory_safe_and_same_frame'] = True
            assert not s.errors
        finally:
            s.p.stop(save=False)
    report['all_checks_passed'] = True
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
