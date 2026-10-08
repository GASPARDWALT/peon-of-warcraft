#!/usr/bin/env python3
"""Check the audio update against the released Valley preview save contract."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

from validate_peon_valley_source import flags

ROOT = Path(__file__).resolve().parents[1]
BASE = 'd48390d'
OUT = ROOT / 'references/generated/warcraft_audio_update'


def previous(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


def main():
    preserved = ['constants/event_flags.asm', 'constants/map_constants.asm',
                 'constants/music_constants.asm', 'ram/wram.asm', 'ram/sram.asm',
                 'data/tilesets/peon_collision.asm', 'data/tilesets/peon_metatiles.bin',
                 'gfx/tilesets/peon_palette_map.bin']
    maps = subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', BASE, 'maps'], cwd=ROOT).decode().splitlines()
    preserved += [name for name in maps if name.endswith('.blk')]
    for name in preserved:
        assert (ROOT / name).read_bytes() == previous(name), name
    before = flags(previous('constants/sfx_constants.asm').decode())
    after = flags((ROOT / 'constants/sfx_constants.asm').read_text())
    assert all(after[name] == value for name, value in before.items())
    assert len(before) == 208 and len(after) == 227 and max(after.values()) < 256
    prefix = lambda text: re.findall(r'^\s*dba\s+(\w+)', text, re.M)
    old_ptr = prefix(previous('audio/sfx_pointers.asm').decode())
    new_ptr = prefix((ROOT / 'audio/sfx_pointers.asm').read_text())
    assert new_ptr[:len(old_ptr)] == old_ptr and len(new_ptr) == len(after)
    old_sounds = previous('audio/peon_sfx.asm').decode().rstrip()
    assert (ROOT / 'audio/peon_sfx.asm').read_text().startswith(old_sounds)
    for name in ('TheDen', 'ValleyOfTrials', 'BurningBladeCavern',
                 'PeonOrcInn', 'PeonTrollInn'):
        event_lines = lambda text: [line.strip() for line in text.splitlines()
                                   if line.strip().startswith(('object_event ', 'warp_event ',
                                                              'coord_event ', 'bg_event '))]
        path = f'maps/{name}.asm'
        assert event_lines((ROOT / path).read_text()) == event_lines(previous(path).decode()), path
    rom = (ROOT / 'pokecrystal.gbc').read_bytes()
    header = {'cgb_flag': rom[0x143], 'cartridge_type': rom[0x147],
              'rom_size_code': rom[0x148], 'ram_size_code': rom[0x149]}
    assert len(rom) == 2 * 1024 * 1024
    assert header == {'cgb_flag': 192, 'cartridge_type': 16, 'rom_size_code': 6, 'ram_size_code': 3}
    assert (-sum(rom[0x134:0x14d]) - 25) & 255 == rom[0x14d]
    assert (sum(rom) - sum(rom[0x14e:0x150])) & 65535 == int.from_bytes(rom[0x14e:0x150], 'big')
    report = {'baseline_commit': BASE, 'rom_sha256': hashlib.sha256(rom).hexdigest(),
              'rom_bytes': len(rom), 'native_header': header,
              'preserved_inputs': preserved, 'existing_sound_ids_and_pointers_preserved': len(before),
              'new_sound_ids': {name: value for name, value in after.items() if name not in before},
              'existing_sfx_note_data_preserved': True, 'actor_and_warp_tables_unchanged': True,
              'save_layout_unchanged': True, 'chromatic_hardware_tested': False,
              'header_checksum_valid': True, 'global_checksum_valid': True,
              'all_checks_passed': True}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'source_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('rom_sha256', 'all_checks_passed', 'save_layout_unchanged')}))


if __name__ == '__main__':
    main()
