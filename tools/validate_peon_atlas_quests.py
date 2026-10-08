#!/usr/bin/env python3
"""Check native atlas glyphs, quest states, fog and palette isolation.

Ordinary buttons reach The Den. The isolated ROM's discovery/quest flags are
then changed for explicitly labelled diagnostic branch coverage. Actual quest
walkthroughs belong to their separate normal-play validators.
"""
import hashlib
import io
import json
import logging
import shutil
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from pyboy import PyBoy

logging.disable(logging.CRITICAL)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/quest_markers'
ATLAS = ROOT / 'references/generated/durotar_v022/zone_maps'


def symbols():
    result = {}
    for line in (ROOT/'pokecrystal.sym').read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and ':' in parts[0]:
            try: result[parts[1]] = tuple(int(c, 16) for c in parts[0].split(':'))
            except ValueError: pass
    return result


def flag_ids():
    result = {}; index = 0
    for line in (ROOT/'constants/event_flags.asm').read_text().splitlines():
        parts = line.split(';')[0].split()
        if not parts: continue
        if parts[0] == 'const_def': index = int(parts[1]) if len(parts)>1 else 0
        elif parts[0] == 'const_next': index = int(parts[1])
        elif parts[0] == 'const_skip': index += int(parts[1]) if len(parts)>1 else 1
        elif parts[0] == 'const': result[parts[1]] = index; index += 1
    return result


def main():
    sym = symbols(); flags = flag_ids()
    assert 'PeonDrawAtlasQuests' in sym, 'Include the helper and rebuild first'
    manifest = json.loads((OUT/'manifest.json').read_text())
    results = {'rom_sha256': hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest(),
               'emulator': 'PyBoy 2.7.0',
               'test_method': 'Ordinary new-game buttons, then diagnostic quest/discovery flag injection',
               'cases': []}
    with tempfile.TemporaryDirectory(prefix='peon-atlas-') as directory:
        rom = Path(directory)/'test.gbc'; shutil.copyfile(ROOT/'pokecrystal.gbc', rom)
        p = PyBoy(str(rom), window='null', sound_emulated=False, log_level='ERROR')
        p.set_emulation_speed(0)
        def read(name, length=1):
            bank, address = sym[name]
            if address >= 0xff00: return list(p.memory[address:address+length])
            return list(p.memory[bank, address:address+length])
        def press(key, frames=90):
            p.button(key, delay=8); p.tick(frames, True)
        def set_flag(name, value=True):
            index = flags[name]; bank, address = sym['wEventFlags']; address += index//8
            old = p.memory[bank, address]
            p.memory[bank, address] = (old | (1 << (index % 8))) if value else (old & ~(1 << (index % 8)))
        def get_flag(name):
            index = flags[name]; bank, address = sym['wEventFlags']
            return bool(p.memory[bank, address+index//8] & (1 << (index % 8)))
        def gray_palette():
            return read('wOBPals1', 64)[56:64], read('wOBPals2', 64)[56:64]
        named = {'entered': False, 'filled': False}
        p.hook_register(*sym['PeonAskName'], lambda s:s.__setitem__('entered', True), named)
        p.tick(240, True); press('start'); press('down'); press('a')
        for _ in range(120):
            if read('wMapGroup', 2) == [26, 14] and read('wScriptMode')[0] == 0: break
            if named['entered'] and not named['filled']:
                p.tick(120, True)
                for i in range(5):
                    press('a', 30)
                    if i<4: press('right', 30)
                press('start', 30); press('a'); named['filled'] = True
            press('a')
        assert read('wMapGroup', 2) == [26, 14] and read('wScriptMode')[0] == 0
        results['ordinary_new_game_reached_den'] = True
        p.hook_deregister(*sym['PeonAskName'])
        baseline = io.BytesIO(); p.save_state(baseline)
        snapshots = []
        def registers():
            return {name:getattr(p.register_file, name) for name in ('A', 'F', 'B', 'C', 'D', 'E', 'HL', 'SP')}
        def entering(_):
            snapshots.append({'entry':registers(), 'vbk':p.memory[0xff4f]&1,
                              'oam_update':read('hOAMUpdate')[0], 'flags_before':read('wEventFlags', 256)})
        def returning(_):
            state = snapshots[-1]
            assert state['entry'] == registers(), ('register corruption', state['entry'], registers())
            assert state['vbk'] == p.memory[0xff4f]&1, 'VBK was not restored'
            assert state['oam_update'] == read('hOAMUpdate')[0], 'OAM guard was not restored'
            assert state['flags_before'] == read('wEventFlags', 256), 'Helper changed quest flags'
            state['verified'] = True
        p.hook_register(*sym['PeonDrawAtlasQuests'], entering, None)
        done_bank, done_address = sym['PeonDrawAtlasQuests.done']
        # Four one-byte POPs precede RET; inspect fully restored registers.
        p.hook_register(done_bank, done_address+4, returning, None)
        points = manifest['points']; styles = manifest['state_styles']
        all_quest_flags = set()
        for point in points.values():
            all_quest_flags.update([point['accepted_flag'], point['complete_flag'], *point['ready_all_flags']])
        lazy = points['DEN']; cactus = points['VALLEY']; sarkoth = points['VALLEY_SARKOTH']; medallion = points['VALLEY_MEDALLION']
        def accepted(point): return [point['accepted_flag']]
        def ready(point): return [point['accepted_flag'], *point['ready_all_flags']]
        cases = [
            ('den_offer', 'DEN', [], False),
            ('den_active_gray', 'DEN', accepted(lazy), False),
            ('den_ready_yellow', 'DEN', ready(lazy), False),
            ('den_done', 'DEN', [lazy['complete_flag']], False),
            ('den_fog', 'DEN', ready(lazy), True),
            ('valley_fog', 'VALLEY', [], True),
            ('valley_all_offered', 'VALLEY', [], False),
            ('valley_all_active_gray', 'VALLEY', accepted(cactus)+accepted(sarkoth)+accepted(medallion), False),
            ('valley_partial_cactus_gray', 'VALLEY', accepted(cactus)+cactus['ready_all_flags'][:2], False),
            ('valley_all_ready_yellow', 'VALLEY', ready(cactus)+ready(sarkoth)+ready(medallion), False),
            ('valley_mixed_states', 'VALLEY', ready(cactus)+accepted(sarkoth), False),
            ('valley_one_done_two_ready', 'VALLEY', [cactus['complete_flag']]+ready(sarkoth)+ready(medallion), False),
            ('valley_all_done', 'VALLEY', [cactus['complete_flag'], sarkoth['complete_flag'], medallion['complete_flag']], False),
        ]
        for label, region, enabled, fog in cases:
            baseline.seek(0); p.load_state(baseline)
            set_flag('EVENT_PEON_MAP_RECEIVED')
            for flag in all_quest_flags: set_flag(flag, False)
            for flag in enabled: set_flag(flag)
            set_flag('EVENT_PEON_DISCOVERED_'+region, not fog)
            palette_before = gray_palette()
            first_snapshot = len(snapshots)
            press('select', 120)
            if region == 'VALLEY': press('right', 120)
            p.tick(12, True)
            assert len(snapshots)>first_snapshot and all(s['verified'] for s in snapshots[first_snapshot:])
            expected_id = 'fog' if fog else region.lower()
            binary = (ROOT/'gfx/peon_maps'/(expected_id+'.bin')).read_bytes()
            assert bytes(p.memory[0, 0x9000:0x9800]) == binary[:2048], 'BG tile bank 0 lower half corrupted'
            assert bytes(p.memory[0, 0x8800:0x9000]) == binary[2048:4096], 'BG tile bank 0 upper half corrupted'
            assert bytes(p.memory[1, 0x9000:0x9680]) == binary[4096:5760], 'BG tile bank 1 corrupted'
            entries = [list(p.memory[0xfe00+i:0xfe04+i]) for i in range(0, 160, 4)]
            visible = [entry for entry in entries if 0<entry[0]<160 and 0<entry[1]<168]
            expected = Image.open(ATLAS/(expected_id+'.png')).convert('RGBA')
            expected_oam = []; point_states = {}
            if not fog:
                for identity, point in points.items():
                    if point['region'] != region: continue
                    if get_flag(point['complete_flag']): state = 'completed'
                    elif not get_flag(point['accepted_flag']): state = 'offered'
                    elif all(get_flag(f) for f in point['ready_all_flags']): state = 'ready'
                    else: state = 'active'
                    point_states[identity] = state
                    if state == 'completed': continue
                    style = styles[state]; oy, ox = point['oam_yx']
                    expected_oam.append([oy, ox, style['tile'], style['palette']])
                    glyph = Image.open(OUT/(style['glyph']+'.png')).convert('RGBA')
                    expected.alpha_composite(glyph, tuple(point['glyph_top_left']))
            assert visible == expected_oam, (label, visible, expected_oam)
            if expected_oam:
                assert p.memory[0xff40]&2, 'OBJ rendering is disabled'
                assert not p.memory[0xff40]&4, 'Glyph requires 8-pixel OBJ mode'
                assert bytes(p.memory[0, 0x8000:0x8020]) == (ROOT/'gfx/pack/peon_quest_poi.2bpp').read_bytes()
            if not fog:
                packed = []
                for red, green, blue in manifest['gray_palette_rgb555']:
                    value = red | green<<5 | blue<<10; packed += [value&255, value>>8]
                assert gray_palette() == (packed, packed), 'Temporary gray palette does not match native RGB555'
            actual = p.screen.image.convert('RGB')
            same = np.array_equal(np.asarray(actual)>>3, np.asarray(expected.convert('RGB'))>>3)
            actual.save(OUT/(label+'_in_rom.png'))
            actual.resize((640, 576), Image.Resampling.NEAREST).save(OUT/(label+'_in_rom_4x.png'))
            assert same, (label, 'Rendered RGB555 pixels differ from the atlas+glyph reconstruction')
            press('b', 120)
            assert read('wMapGroup', 2) == [26, 14] and read('wScriptMode')[0] == 0
            assert gray_palette() == palette_before, (label, 'Atlas gray palette leaked back into the world', palette_before, gray_palette())
            results['cases'].append({'name':label, 'diagnostic_flag_injection':True, 'quest_states':point_states,
                                     'visible_oam':visible, 'rgb555_matches':same, 'background_vram_unchanged':True,
                                     'registers_vbk_oam_guard_preserved':True, 'world_obj_palette_restored':True,
                                     'closed_to_world':True})
        p.hook_deregister(*sym['PeonDrawAtlasQuests'])
        p.hook_deregister(done_bank, done_address+4)
        p.stop(save=False)
    results['limitations'] = ['Availability/fog branches use diagnostic flag injection',
                              'Chromatic hardware is untested', 'Only four current prototype atlas quests have POIs']
    (OUT/'validation_results.json').write_text(json.dumps(results, indent=2)+'\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__': main()
