#!/usr/bin/env python3
"""Restored world actors and both map graphics banks after the v19 gallery.

Only actual controller input changes state. ROM, decompression scratch,
VRAM, OAM and native loader hooks are observed read-only in fresh private
copies. The v17 world assertions remain unchanged. A readiness epoch keeps
the next D-pad press out of the new portrait's native upload interval.
"""
from pathlib import Path
import hashlib
import json
import sys

import validate_peon_world_actors_v0216 as checks
from validate_peon_world_actors_v0217 import WorldActorSessionV0217

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MAPS = {
    13: ('GrommashHold', 'gfx/readable_interiors_v0212/GrommashHold.2bpp',
         'PeonReadableGrommashHoldGFXV0212'),
    14: ('TheDen', 'gfx/quieter_ground_v0214/TheDen.2bpp', 'PeonUserEnvTheDenGFX'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


class RestoredWorldSession(WorldActorSessionV0217):
    def __init__(self, *args):
        self.class_input_serial = 0
        self.accepted_master = False
        self.accepted_capture = False
        self.background_loads = []
        self.background_errors = []
        self.borrowed_bank1_before_accept = None
        super().__init__(*args)

    def open(self):
        super().open()
        self.p.hook_deregister(*self.sym['PeonClassSelect.input'])
        self.p.hook_register(*self.sym['PeonClassSelect.input'], self.input_ready, None)
        self.p.hook_register(*self.sym['PeonClassSelect.draw'], self.drawing_class, None)
        self.p.hook_register(*self.sym['PeonClassSelect.accepted'], self.accepted, None)
        self.p.hook_register(*self.sym['PeonLoadNativeTilesetGFXV0213.native_gfx_done'],
                             self.map_graphics_loaded, None)

    def input_ready(self, _):
        self.class_ready = True
        self.class_input_serial += 1

    def drawing_class(self, _):
        self.class_ready = False

    def accepted(self, _):
        self.accepted_master = True
        expected = (ROOT / SOURCE_MAPS[13][1]).read_bytes()[1536:3072]
        actual = bytes(self.p.memory[1, 0x9000:0x9600])
        self.borrowed_bank1_before_accept = {
            'bank': 1, 'address': 0x9000, 'bytes': 1536,
            'gallery_sha256': sha(actual), 'original_map_sha256': sha(expected),
            'gallery_really_borrowed_map_graphics': actual != expected,
        }

    def map_graphics_loaded(self, _):
        if not self.accepted_master or self.map() not in SOURCE_MAPS:
            return
        try:
            name, path, label = SOURCE_MAPS[self.map()]
            expected = (ROOT / path).read_bytes()
            assert len(expected) == (3072 if self.map() == 13 else 3456)
            source_pointer = (self.read('wTilesetBank')[0],
                              int.from_bytes(bytes(self.read('wTilesetAddress', 2)), 'little'))
            assert source_pointer == self.sym[label], ('Unexpected native tileset source', name, source_pointer)
            compressed = (ROOT / (path + '.lz')).read_bytes()
            assert self.rom_range(*source_pointer, len(compressed)) == compressed
            scratch = bytes(self.read('wDecompressScratch', len(expected)))
            assert scratch == expected, ('Native decompression differs from preserved map packet', name)
            ranges = []
            spans = [(0, 0x9000, 0, 1536), (1, 0x9000, 1536, 1536)]
            if self.map() == 14:
                spans.append((1, 0x8e00, 3072, 384))
            for bank, address, offset, length in spans:
                actual = bytes(self.p.memory[bank, address:address + length])
                source = expected[offset:offset + length]
                assert actual == source, ('Native map graphics were not restored', name, bank, hex(address))
                ranges.append({'VRAM_bank': bank, 'address': address, 'bytes': length,
                               'source_offset': offset, 'source_sha256': sha(source),
                               'actual_VRAM_sha256': sha(actual), 'byte_exact': True})
            self.background_loads.append({'map': name, 'source': path,
                                          'ROM_compressed_source_exact': True,
                                          'native_decompression_scratch_exact': True,
                                          'ranges': ranges})
        except Exception as error:
            # PyBoy suppresses callback exceptions; surface them in normal
            # Python after the controller route reaches its next observation.
            self.background_errors.append(repr(error))

    def wait_class_input(self, after=-1):
        for _ in range(600):
            if self.class_ready and self.class_input_serial > after:
                return
            self.p.tick(1, True)
        raise AssertionError(('Native class portrait never reached its input loop',
                              self.class_input_serial, self.read('wMenuCursorY')))

    def fresh_class(self):
        self.p.tick(240, True)
        self.press('start'); self.press('down'); self.press('a')
        chosen = False
        for _ in range(200):
            if self.map() == 12 and self.base_intro is None:
                self.p.tick(60, True)
                try:
                    observed = self.scene('base_peon_actual_opening')
                    if observed['actors']['0']['key'] == 0xe0:
                        self.base_intro = observed
                except AssertionError:
                    pass  # The existing scripted opening initially hides it.
            if self.map() == 14 and self.read('wScriptMode') == [0]:
                break
            if self.accepted_master and self.map() == 13 and not self.accepted_capture:
                self.capture('accepted_master_restored_hall_and_dialogue')
                self.accepted_capture = True
            if self.class_ready and not chosen:
                self.wait_class_input()
                for desired in range(1, self.class_index + 1):
                    self.p.button_press('down')
                    for _ in range(180):
                        self.p.tick(1, True)
                        if self.read('wMenuCursorY') == [desired]:
                            break
                    self.p.button_release('down')
                    assert self.read('wMenuCursorY') == [desired]
                    # Wait for this portrait's actual ready loop, not an
                    # assumed fixed24-frame interval from the older picker.
                    serial = self.class_input_serial
                    self.wait_class_input(after=serial)
                    self.p.tick(2, True)
                assert self.read('wMenuCursorY') == [self.class_index]
                self.press('a', 90)
                chosen = True
            if self.naming and not self.naming_done:
                self.p.tick(120, True)
                for index in range(5):
                    self.press('a', 35)
                    if index < 4:
                        self.press('right', 35)
                self.press('start', 40); self.press('a')
                self.naming_done = True
            self.press('a')
        assert chosen and self.naming_done and self.map() == 14 and self.read('wScriptMode') == [0]
        assert self.event('EVENT_PEON_WARRIOR') == (self.class_index == 1)
        assert self.event('EVENT_PEON_WARLOCK') == (self.class_index == 2)
        assert not self.background_errors, self.background_errors
        assert self.borrowed_bank1_before_accept['gallery_really_borrowed_map_graphics']
        assert {entry['map'] for entry in self.background_loads} == {'GrommashHold', 'TheDen'}
        self.capture('accepted_master_den_both_BG_banks_and_extension_restored')
        report = {'status': 'PASS', 'rom_sha256': sha(self.rom_bytes),
                  'ordinary_buttons_only': True, 'emulator_memory_edits': False,
                  'states_loaded': False, 'user_batteries_opened': False,
                  'gallery_before_accept': self.borrowed_bank1_before_accept,
                  'native_map_graphics_loads_after_accept': self.background_loads,
                  'native_map_loader_hook_errors': self.background_errors}
        (self.folder / 'background_restore_validation.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    checks.ART_ROOT = ROOT / 'references/generated/world_readability_v0219'
    checks.ASSET_MANIFEST = ROOT / 'gfx/world_readability_v0219/manifest.json'
    checks.GRAPHICS = ROOT / 'gfx/world_readability_v0219/graphics.asm'
    checks.WorldActorSession = RestoredWorldSession
    if '--report-version' not in sys.argv:
        sys.argv.extend(('--report-version', 'v0.2.19'))
    checks.main()
    output = Path(sys.argv[sys.argv.index('--output') + 1])
    path = output / 'validation.json'
    report = json.loads(path.read_text())
    for name, record in report['classes'].items():
        detail = json.loads((output / name / 'background_restore_validation.json').read_text())
        assert detail['status'] == 'PASS' and detail['rom_sha256'] == report['rom_sha256']
        record['native_background_restoration'] = detail
        record['directions']['walking']['animation_note'] = (
            'Idle and restored historical gait poses at the existing gait addresses; '
            'the controller walk observed all three addresses, with complete source/OAM checks.')
    report['world_animation_scope'] = {
        'restored_humanoids': 'Four historical directions and native gait transformations, restored through nearest16-to24.',
        'source_world_creatures': 'Source directional illustrations repeated at the existing three gait addresses; see per-role provenance.',
        'native_address_coverage_is_not_distinct_art_pose_coverage': True,
    }
    path.write_text(json.dumps(report, indent=2) + '\n')
