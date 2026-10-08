#!/usr/bin/env python3
"""Services regression checks on isolated ROM copies and native button input.

Historical validators are imported with new output roots, never run against
published artifacts. Later trainer levels remain explicitly RAM diagnostics.
"""
import argparse
import ast
import hashlib
import json
import logging
import re
import shutil
import tempfile
from pathlib import Path

from PIL import Image
import validate_peon_inns as inns
import validate_peon_trainer as trainer
from validate_peon_villages import Session, load_symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/deep_polish/services'


def source_checks():
    report = {'status': 'PASS', 'checks': []}
    for name, prefix in [('SenjinVillage', 'SenjinVillageKwaii'), ('RazorHill', 'RazorHillJark')]:
        source = (ROOT / 'maps' / (name + '.asm')).read_text()
        script = source.split(prefix + 'Script:', 1)[1].split('.MenuHeader:', 1)[0]
        for label, item, quantity in [('Water', 'FRESH_WATER', 5), ('Potion', 'POTION', 1), ('Bread', 'PEON_CAMP_BREAD', 5)]:
            branch = script.split('.' + label + ':', 1)[1].split('\n.', 1)[0]
            tokens = ['yesorno', 'iffalse .Close', 'checkmoney YOUR_MONEY, 25',
                      'ifequal HAVE_LESS, .Poor', 'giveitem ' + item + (', 5' if quantity == 5 else ''),
                      'iffalse .Full', 'takemoney YOUR_MONEY, 25', 'playsound SFX_TRANSACTION']
            positions = [branch.index(token) for token in tokens]
            assert positions == sorted(positions), (name, label, 'unsafe transaction ordering')
            report['checks'].append({'vendor': prefix, 'stock': item, 'quantity': quantity, 'price_copper': 25,
                                     'confirmation_money_capacity_before_charge': True})
        for number, row in enumerate(source.splitlines(), 1):
            text = re.match(r'\s*(?:text|line|para|cont) "(.*)"', row)
            if text:
                assert len(text[1].replace('<PLAYER>', 'Peon ABCDEFG')) <= 18, (name, number, text[1])
    report['reachable_dialogues_fit_18_columns'] = True
    menu = (ROOT / 'engine/menus/peon_shaman_trainer.asm').read_text()
    assert '\thlcoord 1, 5 ; eighteen-column messages' in menu
    assert '\thlcoord 1, 11 ; the longest spell descriptions' in menu
    report['trainer_content_stays_inside_fixed_frame'] = True
    return report


class ServicesSession(Session):
    def capture(self, name):
        self.p.screen.image.save(OUT / 'vendors' / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / 'vendors' / (name + '_4x.png'))
        print(name, 'map', self.map(), 'position', self.position(), flush=True)

    def advance(self, predicate, maximum=100):
        for _ in range(maximum):
            if predicate():
                self.p.tick(60, True)
                return
            self.press('a')
        self.capture('unexpected_state')
        raise AssertionError((self.map(), self.position(), self.read('wScriptMode'), hex(self.p.register_file.PC)))

    def event(self, name):
        i = self.flags[name]
        return bool(self.read('wEventFlags', i // 8 + 1)[i // 8] & (1 << (i % 8)))

    def talk(self, target, direction='up'):
        self.navigate(target)
        before = self.position()
        self.press(direction, 30)
        assert before == self.position(), (target, direction, self.position())
        self.press('a', 120)

    def vendor(self, target, slot=1, cancel_menu=False, cancel_confirmation=False):
        before = self.money(), self.read('wNumItems'), self.read('wItems', 41)
        menus_before, questions_before = self.observed['menus'], self.observed['questions']
        self.talk(target)
        self.advance(lambda: self.observed['menus'] > menus_before)
        if cancel_menu:
            self.press('b')
        else:
            for _ in range(slot - 1):
                self.press('down', 30)
            self.press('a')
            self.advance(lambda: self.observed['questions'] > questions_before)
            self.press('b' if cancel_confirmation else 'a')
        self.close_dialogue()
        return before, (self.money(), self.read('wNumItems'), self.read('wItems', 41))


def vendor_checks(symbols):
    (OUT / 'vendors').mkdir(parents=True, exist_ok=True)
    report = {'ordinary_buttons_primary_routes': True, 'primary_routes_ram_edits': False, 'emulator_states_loaded': False,
              'stock_prices': {'water_5': 25, 'minor_potion_1': 25, 'bread_5': 25},
              'potions_and_village_bread_stock_are_prototype_adaptations': True}
    with tempfile.TemporaryDirectory(prefix='peon-services-vendors-') as directory:
        rom = Path(directory) / 'test.gbc'
        shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
        s = ServicesSession(rom, symbols)
        try:
            s.observed = {'menus': 0, 'questions': 0, 'initializations': 0, 'trainer': 0}
            s.p.hook_register(*symbols['VerticalMenu'], lambda x: x.__setitem__('menus', x['menus'] + 1), s.observed)
            s.p.hook_register(*symbols['YesNoBox'], lambda x: x.__setitem__('questions', x['questions'] + 1), s.observed)
            s.p.hook_register(*symbols['PeonInitializeShaman'], lambda x: x.__setitem__('initializations', x['initializations'] + 1), s.observed)
            s.p.hook_register(*symbols['PeonShamanTrainer.Input'], lambda x: x.__setitem__('trainer', x['trainer'] + 1), s.observed)
            s.p.tick(1800, True)
            s.press('start'); s.press('down'); s.press('a')
            s.advance(lambda: s.map() == 14 and s.read('wScriptMode') == [0], 200)
            assert s.money() == 50 and s.read('wNumItems') == [1]
            key_kit = s.read('wKeyItems', 4)
            # Earn the existing Lazy Peons reward without diagnostic funding.
            s.talk((8, 16)); s.close_dialogue()
            s.talk((5, 17)); s.close_dialogue()
            s.talk((8, 16)); s.close_dialogue()
            assert s.event('EVENT_PEON_LAZY_DONE') and s.money() == 150
            # Visiting the master again must never reinitialize or duplicate kit.
            items_before, money_before = s.read('wItems', 41), s.money()
            s.talk((7, 12), 'left')
            s.advance(lambda: s.observed['trainer'] > 0, 30)
            for _ in range(12):
                s.press('b', 120)
                if s.read('wScriptMode') == [0]: break
            assert s.read('wItems', 41) == items_before and s.money() == money_before
            assert s.observed['initializations'] == 1
            report['revisiting_master_never_duplicates_kit'] = True
            s.navigate((20, 10), 15); s.navigate((28, 12), 16); s.navigate((12, 24), 17)
            target = (16, 14)
            for kwargs in [{'cancel_menu': True}, {'cancel_confirmation': True}]:
                before, after = s.vendor(target, **kwargs)
                assert before == after, ('cancel mutated inventory/money', kwargs, before, after)
            report['shop_and_confirmation_cancellation_are_noops'] = True
            before, after = s.vendor(target, 1)
            assert after[0] == before[0] - 25 and s.item_quantity(46) == 5 and s.read('wNumItems') == [2]
            before, after = s.vendor(target, 2)
            assert after[0] == before[0] - 25 and s.item_quantity(18) == 1 and s.read('wNumItems') == [3]
            s.capture('kwaii_potion_purchased')
            before, after = s.vendor(target, 3)
            assert after[0] == before[0] - 25 and s.item_quantity(149) == 5 and s.read('wNumItems') == [4]
            report['kwaii_three_stock_success_ordinary_reward_money'] = True
            for _ in range(3):
                before, after = s.vendor(target, 1)
                assert after[0] == before[0] - 25 and s.read('wNumItems') == [4]
            assert s.item_quantity(46) == 20 and s.money() == 0
            report['existing_stack_purchase_preserves_stack_count'] = True
            before, after = s.vendor(target, 2)
            assert before == after, ('insufficient funds charged player', before, after)
            report['insufficient_funds_refusal_changes_nothing'] = True
            s.navigate((10, 4), 16); s.navigate((12, 4), 18)
            before, after = s.vendor((16, 11), 2)
            assert before == after and s.money() == 0
            s.capture('jark_road_stock_no_money')
            report['jark_same_native_stock_and_safe_refusal'] = True
            assert s.read('wKeyItems', 4) == key_kit and s.item_quantity(148) == 1, 'starter kit changed during commerce'
            report['starter_items_preserved'] = True
            report['status'] = 'PASS'
        finally:
            s.p.stop(save=False)
        # A second fresh character can afford bread before filling the pouch;
        # this covers Jark's successful food branch without invented funding.
        bread_rom = Path(directory) / 'bread.gbc'
        shutil.copyfile(ROOT / 'pokecrystal.gbc', bread_rom)
        s = ServicesSession(bread_rom, symbols)
        try:
            s.observed = {'menus': 0, 'questions': 0}
            s.p.hook_register(*symbols['VerticalMenu'], lambda x: x.__setitem__('menus', x['menus'] + 1), s.observed)
            s.p.hook_register(*symbols['YesNoBox'], lambda x: x.__setitem__('questions', x['questions'] + 1), s.observed)
            s.p.tick(1800, True)
            s.press('start'); s.press('down'); s.press('a')
            s.advance(lambda: s.map() == 14 and s.read('wScriptMode') == [0], 200)
            assert s.money() == 50 and s.read('wNumItems') == [1]
            s.navigate((20, 10), 15); s.navigate((28, 12), 16); s.navigate((12, 4), 18)
            before, after = s.vendor((16, 11), 3)
            assert after[0] == before[0] - 25 and s.item_quantity(149) == 5
            assert s.read('wNumItems') == [2]
            before, after = s.vendor((16, 11), 1)
            assert after[0] == before[0] - 25 and s.item_quantity(46) == 5 and s.read('wNumItems') == [3]
            s.capture('jark_bread_and_water_native_purchase')
            report['jark_bread_and_water_success_ordinary_starting_money'] = True
        finally:
            s.p.stop(save=False)
        # Capacity is a separate, explicitly labelled temporary fixture. Story
        # gear occupies key-item storage; the ordinary route above never edits
        # RAM and cannot fill six unique stacks with these three vendor items.
        fixture_rom = Path(directory) / 'capacity_fixture.gbc'
        shutil.copyfile(ROOT / 'pokecrystal.gbc', fixture_rom)
        s = ServicesSession(fixture_rom, symbols)
        try:
            s.observed = {'menus': 0, 'questions': 0}
            s.p.hook_register(*symbols['VerticalMenu'], lambda x: x.__setitem__('menus', x['menus'] + 1), s.observed)
            s.p.hook_register(*symbols['YesNoBox'], lambda x: x.__setitem__('questions', x['questions'] + 1), s.observed)
            s.p.tick(1800, True)
            s.press('start'); s.press('down'); s.press('a')
            s.advance(lambda: s.map() == 14 and s.read('wScriptMode') == [0], 200)
            s.navigate((20, 10), 15); s.navigate((28, 12), 16); s.navigate((12, 24), 17)
            for label, values in [('wNumItems', [6]), ('wItems', [148, 1, 46, 5, 18, 1, 135, 1, 136, 1, 137, 1, 255])]:
                bank, address = symbols[label]
                s.p.memory[bank, address:address + len(values)] = values
            before, after = s.vendor((16, 14), 3)
            assert before == after, ('full-capacity purchase mutated player state', before, after)
            before, after = s.vendor((16, 14), 1)
            assert after[0] == before[0] - 25 and s.item_quantity(46) == 10 and s.read('wNumItems') == [6]
            s.capture('diagnostic_full_pouch_new_stack_refused_existing_stack_allowed')
            report['isolated_capacity_diagnostic'] = {
                'ram_edits': ['wNumItems', 'wItems'], 'user_save_opened': False,
                'full_stack_capacity_refusal_changes_nothing': True,
                'existing_stack_can_be_bought_in_full_pouch': True,
                'money_from_ordinary_new_game': True}
        finally:
            s.p.stop(save=False)
    return report


def trainer_checks():
    trainer.OUT = OUT / 'trainer'
    base = trainer.TrainerSession
    border_observations = []
    class FramedTrainerSession(base):
        def record_phase(self, value):
            before = self.phase
            super().record_phase(value)
            if value == 'main' and before != 'main':
                border_observations.append(('main', self.frame_edges()))
        def frame_edges(self):
            tilemap = self.read('wTilemap', 360)
            return [tilemap[y * 20 + x] for y in range(1, 17) for x in (0, 19)]
        def open(self):
            super().open()
            self.p.hook_deregister(*self.sym['PeonShamanTrainer.WaitAB'])
            def prompt(_):
                self.wait_ready = True
                border_observations.append(('prompt', self.frame_edges()))
            self.p.hook_register(*self.sym['PeonShamanTrainer.WaitAB'], prompt, None)
    trainer.TrainerSession = FramedTrainerSession
    try:
        trainer.main()
    finally:
        trainer.TrainerSession = base
    assert border_observations, 'No native trainer frame observed'
    expected = border_observations[0][1]
    assert all(edges == expected for _, edges in border_observations), 'Trainer frame changed across prompts'
    report = json.loads((trainer.OUT / 'validation.json').read_text())
    report['fixed_native_frame_edges_observations'] = len(border_observations)
    report['frame_edges_preserved_across_all_lesson_prompts'] = True
    report['legacy_import_diagnostics'] = legacy_trainer_checks()
    (trainer.OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def legacy_trainer_checks():
    """Explicitly edited temporary loadouts, followed by native Kento input."""
    folder = OUT / 'trainer_imports'
    folder.mkdir(parents=True, exist_ok=True)
    original_output = trainer.OUT
    trainer.OUT = folder
    report = {'diagnostic_ram_edits': ['wPartyMon1Moves', 'wPartyMon1PP'],
              'user_save_opened': False, 'emulator_states_loaded': False,
              'rom_sha256': hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest()}
    try:
        with tempfile.TemporaryDirectory(prefix='peon-trainer-import-') as directory:
            rom = Path(directory) / 'test.gbc'
            shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = trainer.TrainerSession(rom, load_symbols())
            try:
                s.p.tick(1800, True)
                s.press('start'); s.press('down'); s.press('a')
                for _ in range(180):
                    if s.map() == 14 and s.read('wScriptMode') == [0]: break
                    s.press('a')
                assert s.map() == 14 and s.read('wScriptMode') == [0]
                # Unique charge pools include PP-Up bits. Reordering must move
                # the entire pair, with no refill, masking or lost other spell.
                moves, charges = [105, 52, 84, 1], [0x82, 0x45, 0x43, 0x87]
                s.write('wPartyMon1Moves', moves); s.write('wPartyMon1PP', charges)
                money, hp = s.money(), s.read('wPartyMon1HP', 2)
                s.enter_trainer()
                assert s.read('wPartyMon1Moves', 4) == [1, 84, 52, 105], s.read('wPartyMon1Moves', 4)
                assert s.read('wPartyMon1PP', 4) == [0x87, 0x43, 0x45, 0x82], s.read('wPartyMon1PP', 4)
                assert sorted(zip(moves, charges)) == sorted(zip(s.read('wPartyMon1Moves', 4), s.read('wPartyMon1PP', 4)))
                assert s.money() == money and s.read('wPartyMon1HP', 2) == hp
                s.capture('diagnostic_reordered_import_pair_preserved')
                report['reordered_pairs_exactly_preserved_with_pp_up_bits'] = True
                s.select(0); s.press('a'); s.press('a')
                assert s.phase == 'slots'
                s.press('a')
                assert s.phase == 'message'
                assert s.read('wPartyMon1Moves', 4) == [1, 84, 14, 105]
                assert s.read('wPartyMon1PP', 4) == [0x87, 0x43, 10, 0x82]
                assert s.money() == money - 10
                report['normal_training_replaces_only_third_slot_after_import'] = True
                s.dismiss(); s.exit_trainer()
                prepared = s.read('wPartyMon1Moves', 4), s.read('wPartyMon1PP', 4), s.money()
                s.enter_trainer()
                assert prepared == (s.read('wPartyMon1Moves', 4), s.read('wPartyMon1PP', 4), s.money())
                s.exit_trainer()
                report['already_canonical_records_are_unchanged'] = True
                # Missing Bolt: there is a Mace outside its usual slot, but
                # preflight must refuse before performing even that first swap.
                s.write('wPartyMon1Moves', [14, 52, 105, 1])
                s.write('wPartyMon1PP', [0x82, 0x45, 0x43, 0x87])
                before = s.snapshot()
                s.dialogue((7, 12), 'left')
                assert before == s.snapshot(), 'Incomplete loadout was partially rewritten'
                assert s.phase == 'overworld' and s.read('wScriptMode') == [0]
                report['missing_basic_refuses_without_any_saved_state_mutation'] = True
                report['status'] = 'PASS'
            finally:
                s.p.stop(save=False)
    finally:
        trainer.OUT = original_output
    (folder / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def inn_checks():
    """Retain historical checks with the current ordinary short-tap navigator.

    Holding until the coordinate update buffers a second movement when the Den
    has many actors. This changes only button duration; every rest/bind/warp/
    battery assertion is retained and the player never receives state edits.
    """
    inns.OUT = OUT / 'inns'
    tree = ast.parse((ROOT / 'tools/validate_peon_inns.py').read_text())
    replacement = ast.parse('''
def walk(key):
    before = position()
    oldmap = mapnum()
    for _ in range(8):
        p.button(key, delay=4)
        p.tick(40, True)
        if position() != before:
            break
    assert mapnum() == oldmap, (key, 'unexpected warp', oldmap, mapnum())
    assert sum(abs(a-b) for a,b in zip(before,position())) == 1, (key,before,position())
''').body[0]
    replacements = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'walk':
            node.body = replacement.body
            replacements += 1
    assert replacements == 1, 'Historical inn walker shape changed'
    reserve_patrols = ast.parse('''
if 'SPRITEMOVEDATA_WALK_LEFT_RIGHT' in row:
    actors.update((actor[0]+dx, actor[1]) for dx in (-1, 0, 1))
if 'SPRITEMOVEDATA_WALK_UP_DOWN' in row:
    actors.update((actor[0], actor[1]+dy) for dy in (-1, 0, 1))
''').body
    class PatrolPaths(ast.NodeTransformer):
        count = 0
        def visit_Expr(self, node):
            if ast.unparse(node) == 'actors.add(actor)':
                self.count += 1
                return [node] + reserve_patrols
            return node
    patrols = PatrolPaths()
    tree = patrols.visit(tree)
    assert patrols.count == 1, 'Historical inn actor navigation shape changed'
    # Spend the real Earth Totem's turn before attacking. A quick ordinary
    # critical hit can otherwise kill this first boar without any damage, making
    # the historical wounded-rest precondition depend on combat RNG.
    setup = ast.parse('''
phase = {'value': 'intro', 'menus': 0}
def battle_menu_ready(_):
    phase['value'] = 'battle_drawing'
    phase['menus'] += 1
def battle_input_ready(_):
    if phase['value'] == 'battle_drawing':
        phase['value'] = 'battle'
def bag_input_ready(_):
    if phase['value'] == 'bags_drawing':
        phase['value'] = 'bags'
p.hook_register(*sym['LoadBattleMenu'], battle_menu_ready, None)
p.hook_register(*sym['StaticMenuJoypad'], battle_input_ready, None)
p.hook_register(*sym['PeonBags'], lambda _: phase.__setitem__('value', 'bags_drawing'), None)
p.hook_register(*sym['PeonInterfaceWait'], bag_input_ready, None)
p.hook_register(*sym['PeonInventory.input'], lambda _: phase.__setitem__('value', 'inventory'), None)
''').body
    action = ast.parse('''
advance(lambda: phase['value'] == 'battle')
press('down', 30)
assert read('wMenuCursorX') == [1] and read('wMenuCursorY') == [2]
press('a', 30)
for _ in range(120):
    if phase['value'] == 'bags': break
    p.tick(8, True)
assert phase['value'] == 'bags'
press('a', 30)
for _ in range(120):
    if phase['value'] == 'inventory': break
    p.tick(8, True)
assert phase['value'] == 'inventory' and read('wNamedObjectIndex') == [148]
menus = phase['menus']
press('a', 30)
advance(lambda: phase['menus'] > menus and phase['value'] == 'battle')
assert read('wBattleMonHP', 2) != read('wBattleMonMaxHP', 2), 'Totem turn must produce actual wounds'
if observed['moves'] == 0:
    press('up', 30)
results['real_totem_turn_obtains_wounds_before_rest'] = True
''').body
    class TotemTurn(ast.NodeTransformer):
        count = 0
        spell_choices = 0
        def visit_Expr(self, node):
            if ast.unparse(node) == "advance(lambda: read('wBattleMode')[0] != 0)":
                self.count += 1
                return setup + [node] + action
            return node
        def visit_If(self, node):
            self.generic_visit(node)
            if ast.unparse(node.test) == "observed['moves'] > handled":
                # Mace Strike is now free. Spend the actual Lightning Bolt
                # resource so the retained inn charge-restoration assertion
                # exercises a depleted spell instead of an already-full pool.
                node.body = ast.parse('''
handled = observed['moves']
for _ in range(4):
    if read('wMenuCursorY') == [2]: break
    press('down' if read('wMenuCursorY')[0] < 2 else 'up', 30)
assert read('wMenuCursorY') == [2], ('Lightning cursor', read('wMenuCursorY'), hex(p.register_file.PC))
press('a')
''').body
                self.spell_choices += 1
            return node
    totem = TotemTurn()
    tree = totem.visit(tree)
    assert totem.count == 1, 'Historical first-battle entry changed'
    assert totem.spell_choices == 1, 'Historical combat spell-selection loop changed'
    namespace = dict(inns.__dict__)
    namespace['__name__'] = 'services_inn_validation'
    exec(compile(ast.fix_missing_locations(tree), str(ROOT / 'tools/validate_peon_inns.py'), 'exec'), namespace)
    namespace['OUT'] = inns.OUT
    namespace['main']()
    result = json.loads((inns.OUT / 'validation_results.json').read_text())
    result['ordinary_navigation_uses_short_4_frame_dpad_taps'] = True
    (inns.OUT / 'validation_results.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--section', choices=['source', 'vendors', 'trainer', 'inns', 'all'], default='all')
    parser.add_argument('--expected-rom-sha256')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest()
    if args.expected_rom_sha256:
        assert digest == args.expected_rom_sha256, 'ROM differs from frozen candidate'
    symbols = load_symbols()
    sections = ['source', 'vendors', 'trainer', 'inns'] if args.section == 'all' else [args.section]
    report = {'rom_sha256': digest, 'status': 'PASS', 'sections': {}}
    for section in sections:
        if section == 'source': result = source_checks()
        elif section == 'vendors': result = vendor_checks(symbols)
        elif section == 'trainer': result = trainer_checks()
        else: result = inn_checks()
        report['sections'][section] = result
    assert hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest() == digest, 'ROM changed during validation'
    (OUT / (args.section + '_validation.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'rom_sha256': digest, 'status': 'PASS', 'sections': list(report['sections'])}))


if __name__ == '__main__':
    main()
