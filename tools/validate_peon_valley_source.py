#!/usr/bin/env python3
"""Check preview save/data stability against the published v0.2.3 source."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/valley_layout_update'
BASE = 'aa2e27e'


def old(path):
    return subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)


def flags(text):
    result, value = {}, 0
    for line in text.splitlines():
        words = line.split(';')[0].split()
        if not words:
            continue
        if words[0] == 'const_def':
            value = int(words[1]) if len(words) > 1 else 0
        elif words[0] == 'const_next':
            value = int(words[1])
        elif words[0] == 'const_skip':
            value += int(words[1]) if len(words) > 1 else 1
        elif words[0] == 'const':
            result[words[1]] = value
            value += 1
    return result


def actors(text):
    return [line.split(';')[0].strip().removeprefix('object_event ')
            for line in text.splitlines() if line.strip().startswith('object_event ')]


def main():
    before = flags(old('constants/event_flags.asm').decode())
    after = flags((ROOT / 'constants/event_flags.asm').read_text())
    assert all(after[name] == value for name, value in before.items())
    new = {name: value for name, value in after.items() if name not in before}
    assert new == {'EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD': 312,
                   'EVENT_PEON_CAVE_APPROACH_IMP_2_DEAD': 313}
    unchanged = ['constants/map_constants.asm', 'ram/wram.asm', 'ram/sram.asm',
                 'data/tilesets/peon_collision.asm', 'data/tilesets/peon_metatiles.bin',
                 'gfx/tilesets/peon_palette_map.bin']
    for name in unchanged:
        assert (ROOT / name).read_bytes() == old(name), name
    changed = []
    for name in subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE, 'maps'], cwd=ROOT).decode().splitlines():
        if not name.endswith('.blk'):
            continue
        previous, current = old(name), (ROOT / name).read_bytes()
        assert len(previous) == len(current), name
        changed.extend({'map': name, 'offset': i, 'before': a, 'after': b}
                       for i, (a, b) in enumerate(zip(previous, current)) if a != b)
    assert changed == [{'map': 'maps/TheDen.blk', 'offset': 40, 'before': 37, 'after': 8}], changed
    for name, count in [('TheDen', 11), ('ValleyOfTrials', 7)]:
        previous = actors(old(f'maps/{name}.asm').decode())
        current = actors((ROOT / f'maps/{name}.asm').read_text())
        assert len(previous) == count
        for i, row in enumerate(previous):
            first, second = row.split(', '), current[i].split(', ')
            assert first[:2] == second[:2] and first[-2:] == second[-2:], (name, i + 1)
    old_sfx = flags(old('constants/sfx_constants.asm').decode())
    new_sfx = flags((ROOT / 'constants/sfx_constants.asm').read_text())
    assert all(new_sfx[name] == value for name, value in old_sfx.items())
    assert len(new_sfx) == len(old_sfx) + 1 and max(new_sfx.values()) < 256
    report = {'baseline_commit': BASE, 'existing_event_ids_unchanged': len(before),
              'new_reserved_event_ids': new, 'existing_den_actor_indices_and_coordinates_unchanged': 11,
              'new_den_actor_count': 15, 'existing_valley_actor_indices_and_coordinates_unchanged': 7,
              'new_valley_actor_count': 9, 'map_ids_and_save_layout_unchanged': True,
              'unchanged_inputs': unchanged, 'only_collision_block_change': changed,
              'existing_sound_effect_ids_unchanged': len(old_sfx),
              'new_sound_effect_ids': {name: value for name, value in new_sfx.items() if name not in old_sfx},
              'all_checks_passed': True}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'source_compatibility.json').write_text(json.dumps(report, indent=2) + '\n')
    rom = (ROOT / 'pokecrystal.gbc').read_bytes()
    header = {'cgb_flag': rom[0x143], 'cartridge_type': rom[0x147],
              'rom_size_code': rom[0x148], 'ram_size_code': rom[0x149]}
    assert len(rom) == 2 * 1024 * 1024
    assert header == {'cgb_flag': 192, 'cartridge_type': 16, 'rom_size_code': 6, 'ram_size_code': 3}
    assert (-sum(rom[0x134:0x14d]) - len(rom[0x134:0x14d])) & 255 == rom[0x14d]
    assert (sum(rom) - sum(rom[0x14e:0x150])) & 65535 == int.from_bytes(rom[0x14e:0x150], 'big')
    build = {'rom_sha256': hashlib.sha256(rom).hexdigest(), 'rom_bytes': len(rom),
             'native_header': header, 'header_checksum_valid': True, 'global_checksum_valid': True,
             'all_checks_passed': True, 'source_contract_report': 'source_compatibility.json',
             'build_command': 'sh tools/rebuild_peon_valley_preview.sh --build',
             'chromatic_hardware_tested': False}
    (OUT / 'build_validation.json').write_text(json.dumps(build, indent=2) + '\n')
    print(json.dumps(build, indent=2))


if __name__ == '__main__':
    main()
