#!/usr/bin/env python3
"""Check native inventory icons, with explicitly isolated prepared-art fixtures.

Normal starter-bag checks never edit RAM or load emulator states. The separate
32-art diagnostic phase edits an isolated bag and, for unassigned artwork only,
overrides one temporary icon-lookup entry. It does not unlock classes or grant
loot. All icon drawing still runs the native inventory and renderer.
"""
import hashlib
import io
import json
import logging
import re
import shutil
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from validate_peon_villages import Session, load_symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/item_icon_validation'
CELLS = [3 * 20 + 16, 3 * 20 + 17, 4 * 20 + 16, 4 * 20 + 17]


def icon_label(slug):
    return 'PeonItemIcon' + ''.join(part.capitalize() for part in slug.split('_'))


def item_ids():
    result, index = {}, 0
    for line in (ROOT / 'constants/item_constants.asm').read_text().splitlines():
        fields = line.split(';')[0].split()
        if not fields:
            continue
        if fields[0] == 'const_def':
            index = int(fields[1].replace('$', '0x'), 0) if len(fields) > 1 else 0
        elif fields[0] == 'const':
            result[fields[1]] = index
            index += 1
    return result


class IconSession(Session):
    def __init__(self, rom, symbols):
        self.phase = 'overworld'
        self.entries = []
        self.checked_returns = 0
        super().__init__(rom, symbols)
        self.p.hook_register(*symbols['PeonBags'], lambda _context: setattr(self, 'phase', 'landing'), None)
        self.p.hook_register(*symbols['PeonInventory.input'], lambda _context: setattr(self, 'phase', 'inventory'), None)
        self.p.hook_register(*symbols['PeonDrawInventoryItemIconFromC'], self.renderer_entry, None)
        bank, address = symbols['PeonDrawInventoryItemIconFromC.Done']
        assert self.p.memory[bank, address + 7] == 0xc9, 'Renderer return offset changed'
        self.p.hook_register(bank, address + 7, self.renderer_return, None)

    def write(self, name, values):
        bank, address = self.sym[name]
        self.p.memory[bank, address:address + len(values)] = values

    def capture(self, name):
        self.p.screen.image.save(OUT / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / (name + '_4x.png'))

    def registers(self):
        return {name: getattr(self.p.register_file, name) for name in ('A', 'F', 'B', 'C', 'D', 'E', 'HL', 'SP')}

    def protected(self):
        tiles, attrs = self.read('wTilemap', 360), self.read('wAttrmap', 360)
        pals = self.read('wBGPals1', 64)
        return {'party': self.read('wPartyMon1Species', 48),
                'items': self.read('wNumItems', 42), 'money': self.read('wMoney', 3),
                'events': self.read('wEventFlags', 44), 'cursor': self.read('wMenuCursorY'),
                'font': list(self.p.memory[0, 0x8800:0x9000]),
                'oam': self.read('wShadowOAM', 160), 'other_palettes': pals[:40] + pals[48:],
                'other_tiles': [value for i, value in enumerate(tiles) if i not in CELLS],
                'other_attrs': [value for i, value in enumerate(attrs) if i not in CELLS]}

    def renderer_entry(self, _context):
        self.entries.append((self.registers(), self.p.memory[0xff4f], self.protected()))

    def renderer_return(self, _context):
        registers, vbk, protected = self.entries.pop()
        assert registers == self.registers(), ('Icon register corruption', registers, self.registers())
        assert vbk == self.p.memory[0xff4f], 'Icon changed VBK'
        assert protected == self.protected(), 'Icon altered inventory, stats, flags, font, OAM or unrelated UI'
        self.checked_returns += 1

    def enter_bags(self):
        self.phase = 'overworld'
        self.press('start', 120)
        for _ in range(12):
            cursor = self.read('wMenuCursorPosition')[0]
            if cursor == 2:
                break
            self.press('up' if cursor > 2 else 'down', 30)
        self.press('a', 120)
        assert self.phase == 'landing', ('No bag landing page', self.phase)
        self.p.tick(120, True)

    def enter_inventory(self):
        assert self.phase == 'landing'
        self.press('a', 120)
        assert self.phase == 'inventory', ('No inventory', self.phase)
        self.p.tick(120, True)

    def check_icon(self, entry, label):
        self.p.tick(120, True)
        slug = entry['slug']
        binary = (ROOT / entry['rom_gfx']).read_bytes()
        assert len(binary) == 64
        internal_png = Image.open((ROOT / entry['rom_gfx']).with_suffix('.png'))
        assert internal_png.mode == 'P' and 'transparency' not in internal_png.info
        assert internal_png.size == (16, 16) and set(np.unique(np.asarray(internal_png))) <= {0, 1, 2, 3}
        assert bytes(self.p.memory[0, 0x9280:0x92c0]) == binary, (label, 'Native icon VRAM differs')
        tiles, attrs = self.read('wTilemap', 360), self.read('wAttrmap', 360)
        assert [tiles[i] for i in CELLS] == [0x28, 0x29, 0x2a, 0x2b], (label, 'Icon tile cells differ')
        assert [attrs[i] for i in CELLS] == [5] * 4, (label, 'Icon palette attributes differ')
        address = self.p.memory[self.sym['hBGMapAddress'][1]] | (self.p.memory[self.sym['hBGMapAddress'][1] + 1] << 8)
        for row, col, tile in ((3, 16, 0x28), (3, 17, 0x29), (4, 16, 0x2a), (4, 17, 0x2b)):
            assert self.p.memory[0, address + row * 32 + col] == tile
            assert self.p.memory[1, address + row * 32 + col] == 5
        palette = entry['rom_palette_rgb555']
        expected_palette = b''.join((r | (g << 5) | (b << 10)).to_bytes(2, 'little') for r, g, b in palette)
        assert bytes(self.read('wBGPals1', 48)[40:48]) == expected_palette, (label, 'Icon palette differs')
        rgba = np.asarray(Image.open(ROOT / 'references/generated/durotar_v022/items' / entry['native_png']).convert('RGBA'))
        assert rgba.shape == (16, 16, 4) and set(np.unique(rgba[:, :, 3])) == {0, 255}
        assert np.all(rgba[rgba[:, :, 3] == 0, :3] == 0)
        assert len(np.unique(rgba[rgba[:, :, 3] == 255, :3], axis=0)) <= 3
        detail = np.asarray(Image.open(ROOT / 'references/generated/durotar_v022/items' / entry['detail_png']).convert('RGBA'))
        assert detail.shape == (32, 32, 4) and set(np.unique(detail[:, :, 3])) == {0, 255}
        assert np.all(detail[detail[:, :, 3] == 0, :3] == 0)
        assert len(np.unique(detail[detail[:, :, 3] == 255, :3], axis=0)) <= 16
        assert np.all(detail[:, :, :3] % 8 == 0)
        expected = rgba[:, :, :3] >> 3
        expected[rgba[:, :, 3] == 0] = palette[0]
        actual = np.asarray(self.p.screen.image.convert('RGB').crop((128, 24, 144, 40))) >> 3
        assert np.array_equal(actual, expected), (label, 'Actual native RGB555 icon pixels differ')
        self.capture(label)
        return {'slug': slug, 'native_vram_tiles_match': True, 'actual_bg_attributes_match': True,
                'actual_rgb555_pixels_match': True, 'binary_png_alpha': True,
                'detail_reference_png_binary_alpha_and_rgb555': True,
                'internal_png_is_rebuildable_indexed_grayscale_without_alpha': True,
                'transparent_png_background_is_native_parchment': True}


def main():
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    symbols, constants = load_symbols(), item_ids()
    manifest = json.loads((ROOT / 'references/generated/durotar_v022/items/asset_manifest.json').read_text())
    catalog = manifest['items']
    assert len(catalog) == 32
    by_slug = {entry['slug']: entry for entry in catalog}
    assert by_slug['earth_totem']['item'] == 'ITEM_94'
    assert by_slug['earth_totem']['status'] == 'integrated_battle_totem'
    by_id = {constants[entry['item']]: entry for entry in catalog
             if entry['item'] is not None and not entry['item'].startswith('$')}
    report = {'rom_sha256': hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest(),
              'normal_starter_bag_ram_edits': False, 'normal_starter_bag_states_loaded': False,
              'normal_starter_icons': [], 'native_catalog_diagnostics': []}
    s = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-item-icons-') as directory:
            rom = Path(directory) / 'normal.gbc'
            shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = IconSession(rom, symbols)
            s.p.tick(1800, False)
            s.press('start')
            s.press('down')
            s.press('a')
            for _ in range(180):
                if s.map() == 14 and s.read('wScriptMode') == [0]:
                    break
                s.press('a')
            assert s.read('wMapGroup', 2) == [26, 14]
            normal_before = (s.read('wPartyMon1Species', 48), s.read('wNumItems', 42), s.read('wMoney', 3))
            key_items = s.read('wKeyItems', s.read('wNumKeyItems')[0])
            kit = [constants[name] for name in ('ITEM_19', 'ITEM_2D', 'ITEM_32')]
            assert all(item in key_items for item in kit), 'Protected starter equipment kit missing'
            report['normal_protected_kit_key_item_ids'] = kit
            count = s.read('wNumItems')[0]
            owned = s.read('wItems', count * 2)[::2]
            assert constants['ITEM_94'] in owned, 'Starter Earth Totem missing'
            s.enter_bags()
            s.enter_inventory()
            for index, item in enumerate(owned):
                if index:
                    s.press('right', 120)
                assert s.read('wMenuCursorY') == [index] and s.read('wNamedObjectIndex') == [item]
                report['normal_starter_icons'].append(s.check_icon(by_id[item], 'normal_' + by_id[item]['slug']))
            assert normal_before == (s.read('wPartyMon1Species', 48), s.read('wNumItems', 42), s.read('wMoney', 3))
            s.press('b', 120)
            s.press('b', 120) # close the parent Start menu too
            # Hearthstone is acquired by binding at an actual inn, not in the
            # starter kit. Rest and bind through the production NPC script.
            s.navigate((17, 5), expected_map=23)
            s.navigate((6, 5))
            s.press('up', 30)
            s.press('a', 120)
            s.close_dialogue()
            s.navigate((5, 7), expected_map=14)
            s.enter_bags()
            report['normal_hearthstone_menu_asset'] = s.check_icon(by_slug['hearthstone'], 'normal_hearthstone_after_inn_bind')
            report['normal_renderer_preservation_checks'] = s.checked_returns
            s.p.stop(save=False)
            s = None

            # Separate diagnostic game. It starts normally, then deliberately
            # replaces its bag/lookup to render prepared and later-loot icons.
            diagrom = Path(directory) / 'diagnostic.gbc'
            shutil.copyfile(ROOT / 'pokecrystal.gbc', diagrom)
            s = IconSession(diagrom, symbols)
            s.p.tick(1800, False)
            s.press('start')
            s.press('down')
            s.press('a')
            for _ in range(180):
                if s.map() == 14 and s.read('wScriptMode') == [0]:
                    break
                s.press('a')
            assert s.map() == 14
            baseline = io.BytesIO()
            s.p.save_state(baseline)
            bank, lookup = symbols['PeonInventoryItemIconLookup']
            records, cursor = {}, lookup
            while s.p.memory[bank, cursor] != 255:
                records[s.p.memory[bank, cursor]] = cursor
                cursor += 5
            original_lookup = bytes(s.p.memory[bank, lookup:cursor + 1])
            contact = Image.new('RGB', (8 * 64, 4 * 64))
            for index, entry in enumerate(catalog):
                baseline.seek(0)
                s.p.load_state(baseline)
                s.p.memory[bank, lookup:cursor + 1] = original_lookup
                item = constants.get(entry['item'])
                prepared = item is None
                if prepared:
                    item = constants['ITEM_64']
                    gfx_bank, gfx = symbols[icon_label(entry['slug']) + 'GFX']
                    palette_bank, palette = symbols[icon_label(entry['slug']) + 'Palette']
                    assert gfx_bank == palette_bank == bank
                    pointer = records[item] + 1
                    s.p.memory[bank, pointer:pointer + 4] = [gfx & 255, gfx >> 8, palette & 255, palette >> 8]
                else:
                    assert item in records, (entry['slug'], 'Real item absent from native lookup')
                s.write('wNumItems', [1])
                s.write('wItems', [item, 1, 255])
                s.enter_bags()
                s.enter_inventory()
                case = s.check_icon(entry, 'diagnostic_' + entry['slug'])
                case.update({'item_id': item, 'isolated_inventory_ram_edit': True,
                             'temporary_lookup_override_for_prepared_art': prepared,
                             'catalog_status': entry['status']})
                report['native_catalog_diagnostics'].append(case)
                contact.paste(s.p.screen.image.convert('RGB').crop((128, 24, 144, 40)).resize(
                    (64, 64), Image.Resampling.NEAREST), ((index % 8) * 64, (index // 8) * 64))
            baseline.seek(0)
            s.p.load_state(baseline)
            s.p.memory[bank, lookup:cursor + 1] = original_lookup
            s.write('wNumItems', [1])
            s.write('wItems', [constants['ITEM_5A'], 1, 255])
            s.enter_bags()
            s.enter_inventory()
            report['unmapped_id_fallback'] = s.check_icon(by_slug['small_pouch'], 'diagnostic_unmapped_fallback')
            report['register_vbk_inventory_stats_flags_font_oam_preservation_checks'] = s.checked_returns + report['normal_renderer_preservation_checks']
            contact.save(OUT / 'actual_native_item_icons_contact_sheet_4x.png')
            s.p.stop(save=False)
            s = None
            report['all_checks_passed'] = True
    except Exception as exc:
        report['all_checks_passed'] = False
        report['failure'] = repr(exc)
        if s is not None:
            s.capture('unexpected_state')
            s.p.stop(save=False)
        (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
        raise
    report['limitations'] = ['Prepared Mage/Warrior/spell artwork is diagnosed through temporary UI lookup overrides; those items/classes are not unlocked.',
                             'Later gear is injected only in diagnostic bags, not claimed as earned loot.',
                             'PNG transparency is native BG parchment in the ROM, not an alpha channel.',
                             'Physical Chromatic testing remains outstanding.']
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
