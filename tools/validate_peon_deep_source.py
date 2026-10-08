#!/usr/bin/env python3
"""Verify the polished preview's actual save/header/navigation contract."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/deep_polish'
BASE = '1435e70'


def old(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


def flags(text):
    result, i = {}, 0
    for row in text.splitlines():
        parts = row.split(';')[0].split()
        if not parts:
            continue
        if parts[0] in ('const_def', 'const_next'):
            i = int(parts[1], 0) if len(parts) > 1 else 0
        elif parts[0] == 'const_skip':
            i += int(parts[1], 0) if len(parts) > 1 else 1
        elif parts[0] == 'const':
            result[parts[1]] = i
            i += 1
    return result


def collision_rows(text):
    return [tuple(p.strip() for p in m[1].split(',')) for m in
            re.finditer(r'^\s*tilecoll\s+([^;\n]+)', text, re.M)]


def main():
    preserved = ['ram/wram.asm', 'ram/sram.asm', 'constants/map_constants.asm',
                 'constants/item_constants.asm', 'constants/music_constants.asm',
                 'constants/sfx_constants.asm', 'audio/sfx_pointers.asm']
    for path in preserved:
        assert (ROOT / path).read_bytes() == old(path), path
    before = flags(old('constants/event_flags.asm').decode())
    after = flags((ROOT / 'constants/event_flags.asm').read_text())
    assert all(after.get(name) == index for name, index in before.items()), 'Saved flag renumbered'
    old_cols = collision_rows(old('data/tilesets/peon_collision.asm').decode())
    new_cols = collision_rows((ROOT / 'data/tilesets/peon_collision.asm').read_text())
    maps = {}
    names = ('PeonOpening', 'GrommashHold', 'TheDen', 'ValleyOfTrials', 'DurotarRoad',
             'SenjinVillage', 'RazorHill', 'OrgrimmarGate', 'BurningBladeCavern',
             'PeonTrollHut', 'PeonOrcHut', 'PeonOrcInn', 'PeonTrollInn')
    coords = lambda s: re.findall(r'^\s*(?:warp_event|coord_event|bg_event)\s+[^\n]+', s, re.M)
    actors = lambda s: re.findall(r'^\s*object_event\s+(\d+),\s*(\d+),\s*(\w+)', s, re.M)
    for name in names:
        path = f'maps/{name}.blk'
        previous, current = old(path), (ROOT / path).read_bytes()
        assert len(previous) == len(current), (name, 'Saved geometry changed')
        # Keep all existing FLOOR/WALL/WARP movement cells exactly equivalent;
        # block artwork may change without moving a saved player into rock.
        for i, (a, b) in enumerate(zip(previous, current)):
            assert old_cols[a] == new_cols[b], (name, i, a, b, 'Collision changed')
        script_path = f'maps/{name}.asm'
        original, updated = old(script_path).decode(), (ROOT / script_path).read_text()
        assert coords(original) == coords(updated), (name, 'Interaction/warp coordinates changed')
        assert actors(original) == actors(updated), (name, 'Actor order/position changed')
        maps[name] = {'changed_blocks': sum(a != b for a, b in zip(previous, current)),
                      'bytes': len(current), 'movement_collision_preserved': True,
                      'sha256': hashlib.sha256(current).hexdigest()}
    huts = [maps[n]['sha256'] for n in ('PeonOrcHut', 'PeonTrollHut')]
    inns = [maps[n]['sha256'] for n in ('PeonOrcInn', 'PeonTrollInn')]
    assert len(set(huts)) == 2 and len(set(inns)) == 2, 'Tribal rooms still duplicate'
    rom = (ROOT / 'pokecrystal.gbc').read_bytes()
    assert len(rom) == 2 * 1024 * 1024
    header = {'cgb_flag': rom[0x143], 'cartridge_type': rom[0x147],
              'rom_size_code': rom[0x148], 'ram_size_code': rom[0x149]}
    assert header == dict(cgb_flag=192, cartridge_type=16, rom_size_code=6, ram_size_code=3)
    assert (-sum(rom[0x134:0x14d]) - 25) & 255 == rom[0x14d]
    assert (sum(rom) - sum(rom[0x14e:0x150])) & 65535 == int.from_bytes(rom[0x14e:0x150], 'big')
    report = {'rom_sha256': hashlib.sha256(rom).hexdigest(), 'baseline_commit': BASE,
              'all_checks_passed': True, 'preserved_inputs': preserved,
              'all_existing_event_ids_preserved': True,
              'new_reserved_event_flags': {n: i for n, i in after.items() if n not in before},
              'maps': maps, 'hut_and_inn_duplicates_removed': True,
              'map_ids_dimensions_coordinates_and_save_layout_preserved': True,
              'native_header': header, 'physical_chromatic_tested': False}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'source_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
