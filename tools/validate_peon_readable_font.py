#!/usr/bin/env python3
"""Check original fixed-cell typography in the actual ROM with normal input.

The font check boots a private fresh game, enters a maximum five-letter name,
opens Character/Bags and talks to Gornek. It never edits game RAM, injects text,
loads savestates, or opens a user battery save. Optional --baseline records the
same route in a pre-font ROM for genuine before/after captures.
"""
import argparse
import hashlib
import json
import logging
from pathlib import Path
import shutil
import tempfile

import numpy as np
from PIL import Image

import build_peon_readable_font as font

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/environment_v025/font'


def load_symbols(path):
    result = {}
    for row in path.read_text().splitlines():
        parts = row.split()
        if len(parts) == 2 and ':' in parts[0]:
            result[parts[1]] = tuple(int(n, 16) for n in parts[0].split(':'))
    return result


def source_checks():
    sheet = Image.open(ROOT / 'gfx/font/peon_readable.png').convert('L')
    original = Image.open(ROOT / 'gfx/font/font.png').convert('L')
    report = json.loads((OUT / 'font_build.json').read_text())
    assert sheet.size == (128, 64) and set(sheet.tobytes()) == {0, 255}
    assert len(font.encode_1bpp(sheet)) == 1024
    assert hashlib.sha256(font.encode_1bpp(sheet)).hexdigest() == report['font_1bpp_sha256']
    assert all(sheet.crop(font.tile_box(code)).tobytes() == original.crop(font.tile_box(code)).tobytes()
               for code in report['preserved_codes'])
    codes = font.encoding()
    for group in [('I', 'l', '1', 'i'), ('O', 'o', '0')]:
        assert len({sheet.crop(font.tile_box(codes[ch])).tobytes() for ch in group}) == len(group)
    assert sheet.crop(font.tile_box(codes['.'])).tobytes() == sheet.crop(font.tile_box(codes['<DOT>'])).tobytes()
    glyphs = Image.open(OUT / 'peon_readable_glyphs_transparent.png')
    assert glyphs.mode == 'RGBA' and set(glyphs.getchannel('A').tobytes()) == {0, 255}
    assert 'INCBIN "gfx/font/peon_readable.1bpp"' in (ROOT / 'gfx/font.asm').read_text()
    return report | {'status': 'PASS', 'ambiguous_glyph_groups_distinct': True,
                     'transparent_preview_binary_alpha': True}


class FontCheck:
    def __init__(self, rom, sym, expected, output):
        super().__init__(rom, sym)
        self.expected = bytes(c for value in expected for c in (value, value))
        self.out = output
        self.reports = []

    def capture(self, slug):
        self.p.tick(40, True)
        self.p.screen.image.save(self.out / (slug + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(self.out / (slug + '_4x.png'))

    def font_in_vram(self):
        assert bytes(self.p.memory[0, 0x8800:0x9000]) == self.expected, 'Actual standard Font upload differs'

    def verify_rendered_glyphs(self, phase, rows=None):
        self.p.tick(40, True)
        self.font_in_vram()
        tiles, attrs = self.read('wTilemap', 360), self.read('wAttrmap', 360)
        palette = self.read('wBGPals2', 64)
        actual = np.array(self.p.screen.image.convert('RGB')) >> 3
        checked, distinct = 0, set()
        selected_rows = range(18) if rows is None else rows
        for y in selected_rows:
            for x in range(20):
                code, attr = tiles[y * 20 + x], attrs[y * 20 + x]
                if code < 0x80 or attr & 8:
                    continue
                # The signed-font range is always $8800..$8fff. Decode the
                # actual live CGB palette, not a mocked black/white screenshot.
                raw = self.expected[(code - 0x80) * 16:(code - 0x80 + 1) * 16]
                colors = []
                for i in range(4):
                    index = 8 * (attr & 7) + 2 * i
                    value = palette[index] | palette[index + 1] << 8
                    colors.append((value & 31, (value >> 5) & 31, (value >> 10) & 31))
                expected = np.array([[colors[((raw[2 * row] >> (7 - col)) & 1) |
                                                   (((raw[2 * row + 1] >> (7 - col)) & 1) << 1)]
                                      for col in range(8)] for row in range(8)], dtype='uint8')
                if attr & 0x20:
                    expected = expected[:, ::-1]
                if attr & 0x40:
                    expected = expected[::-1]
                pixels = actual[y * 8:y * 8 + 8, x * 8:x * 8 + 8]
                assert np.array_equal(pixels, expected), (phase, 'native RGB555 glyph mismatch', x, y, hex(code), hex(attr))
                checked += 1
                distinct.add(code)
        assert checked >= 10, (phase, 'not enough ordinary rendered text cells', checked)
        result = {'phase': phase, 'native_glyph_cells_compared': checked,
                  'distinct_codes': sorted(distinct), 'all_128_font_tiles_in_vram_match': True,
                  'actual_cgb_rgb555_pixels_match': True}
        self.reports.append(result)
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', type=Path, default=ROOT / 'pokecrystal.gbc')
    parser.add_argument('--symbols', type=Path, default=ROOT / 'pokecrystal.sym')
    parser.add_argument('--expected-sha')
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--source-only', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    static = source_checks()
    (OUT / 'font_source_validation.json').write_text(json.dumps(static, indent=2) + '\n')
    if args.source_only:
        print('Original readable font source checks PASS; 128 fixed cells, original UI glyphs preserved.')
        return
    # Static font inspection should not depend on an emulator installation.
    from validate_peon_deep_ui import Check
    NativeFontCheck = type('NativeFontCheck', (FontCheck, Check), {})
    logging.disable(logging.CRITICAL)
    romdata = args.rom.read_bytes()
    digest = hashlib.sha256(romdata).hexdigest()
    if args.expected_sha:
        assert digest == args.expected_sha
    sym = load_symbols(args.symbols)
    bank, address = sym['Font']
    offset = bank * 0x4000 + (address - 0x4000 if bank else address)
    expected = romdata[offset:offset + 1024]
    sheet = Image.open(ROOT / ('gfx/font/font.png' if args.baseline else 'gfx/font/peon_readable.png')).convert('L')
    assert expected == font.encode_1bpp(sheet), 'Font ROM bytes do not match the declared source drawing'
    output = OUT / ('baseline_v024' if args.baseline else 'native_validation')
    output.mkdir(exist_ok=True)
    report = {'rom_sha256': digest, 'status': 'RUNNING', 'ordinary_buttons_only': True,
              'ram_edits': False, 'savestates_loaded': False, 'user_saves_opened': False,
              'original_pre_font_baseline': args.baseline, 'font_1bpp_sha256': hashlib.sha256(expected).hexdigest(),
              'source': static}
    with tempfile.TemporaryDirectory(prefix='peon-readable-font-') as folder:
        rom = Path(folder) / 'font.gbc'
        shutil.copyfile(args.rom, rom)
        s = NativeFontCheck(rom, sym, expected, output)
        try:
            s.fresh()
            assert s.read('wPlayerName', 11)[:10] == s.encode('Péon ABCDE')
            s.start(1); s.press('a')
            s.chrome()
            assert s.has('Péon ABCDE', 1)
            s.verify_rendered_glyphs('character_maximum_name')
            s.capture('character_maximum_name_in_rom')
            s.close()
            s.start(2); s.press('a')
            s.chrome(); s.verify_rendered_glyphs('bags_fixed_frame')
            s.capture('bags_in_rom')
            s.press('a'); s.chrome()
            s.verify_rendered_glyphs('inventory_quantity_description')
            s.capture('inventory_in_rom')
            s.close()
            # Fresh characters spawn directly below Gornek at x=10. These
            # short actual D-pad taps approach his unchanged (10,9) location.
            for _ in range(12):
                if s.read('wYCoord') == [10]:
                    break
                s.press('up', 30)
            assert s.read('wXCoord') == [10] and s.read('wYCoord') == [10]
            s.press('up', 30); s.press('a', 240)
            assert s.read('wScriptMode') != [0]
            s.verify_rendered_glyphs('gornek_dialogue_with_portrait', rows=[14, 16])
            s.capture('gornek_dialogue_in_rom')
            for _ in range(40):
                if s.read('wScriptMode') == [0]:
                    break
                s.press('a', 90)
            assert s.read('wScriptMode') == [0]
            report['normal_native_checks'] = s.reports
            report['maximum_saved_name_has_native_accented_prefix'] = True
            report['fixed_frame_geometry_preserved'] = True
            report['font_reload_calls'] = s.font_uploads
            report['status'] = 'PASS'
            report['all_checks_passed'] = True
        except Exception:
            s.capture('validation_failure')
            report['normal_native_checks'] = s.reports
            report['status'] = 'FAIL'
            raise
        finally:
            s.p.stop(save=False)
            (output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'rom_sha256': digest, 'status': report['status'],
                      'native_glyph_cells_compared': sum(x['native_glyph_cells_compared'] for x in s.reports),
                      'ordinary_buttons_only': True}))


if __name__ == '__main__':
    main()
