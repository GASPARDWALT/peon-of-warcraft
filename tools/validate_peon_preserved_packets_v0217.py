#!/usr/bin/env python3
"""Check protected v16 sources, compiled combat/master/lightning data and header."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'fb0b5c41'
PROTECTED = (
    'gfx/combat_heroes_v0216', 'gfx/large_masters_v0213',
    'gfx/canonical_decor_v0213', 'gfx/readable_interiors_v0212',
    'gfx/quieter_ground_v0214', 'gfx/zone_passages_v0213',
    'gfx/peon_lightning_horizontal_v0213', 'gfx/rock_roster_v0213',
    'maps', 'data/maps', 'data/moves', 'data/pokemon', 'engine/battle',
    'engine/menus/peon_class_graphics.asm', 'gfx/user_battle_v0211/data.asm',
)
ASSEMBLY = (
    'engine/menus/peon_class_graphics.asm', 'gfx/user_battle_v0211/data.asm',
    'gfx/large_masters_v0213/graphics.asm', 'gfx/peon_lightning_horizontal_v0213.asm',
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def symbols(path):
    result = {}
    for line in path.read_text().splitlines():
        match = re.fullmatch(r'([0-9A-Fa-f]+):([0-9A-Fa-f]+) (\S+)', line)
        if match:
            result[match[3]] = (int(match[1], 16), int(match[2], 16))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('rom', 'sym', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    # Native sources remain byte-identical to the actual delivered v16 commit.
    changed = subprocess.check_output(['git', 'diff', '--name-only', BASELINE, '--', *PROTECTED], cwd=ROOT, text=True)
    assert not changed, ('Protected gameplay/art source changed', changed)
    files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASELINE, '--', *PROTECTED], cwd=ROOT, text=True).splitlines()
    assert files
    source_hashes = {name: digest((ROOT / name).read_bytes()) for name in files}
    rom, sym = args.rom.read_bytes(), symbols(args.sym)
    compiled = []
    for name in ASSEMBLY:
        current = None
        for line in (ROOT / name).read_text().splitlines():
            label = re.fullmatch(r'\s*([A-Za-z_][A-Za-z0-9_]*)::?\s*(?:;.*)?', line)
            if label:
                current = label[1]
            include = re.fullmatch(r'\s*INCBIN\s+"([^"]+)"\s*(?:;.*)?', line)
            if not include or not include[1].startswith(('gfx/combat_heroes_v0216/', 'gfx/large_masters_v0213/', 'gfx/peon_lightning_horizontal_v0213/')):
                continue
            assert current in sym
            data = (ROOT / include[1]).read_bytes()
            bank, address = sym[current]
            offset = address if not bank else bank * 0x4000 + address - 0x4000
            assert rom[offset:offset + len(data)] == data, ('Compiled protected packet differs', current)
            compiled.append({'label': current, 'path': include[1], 'sha256': digest(data), 'bytes': len(data), 'ROM_exact': True})
    assert len(compiled) == 50, len(compiled)
    assert len(rom) == 2097152 and rom[0x143] == 0xc0 and rom[0x147] == 0x10 and rom[0x149] == 3
    header = 0
    for value in rom[0x134:0x14d]:
        header = (header - value - 1) & 255
    assert header == rom[0x14d]
    assert (sum(rom) - rom[0x14e] - rom[0x14f]) & 0xffff == int.from_bytes(rom[0x14e:0x150], 'big')
    report = {'version': 'v0.2.17', 'status': 'PASS', 'rom_sha256': digest(rom),
              'baseline_commit': BASELINE, 'protected_sources': source_hashes,
              'protected_source_count': len(files), 'compiled_protected_packets': compiled,
              'header_and_global_checksums_exact': True, 'CGB_only': True,
              'MBC3_timer_32KiB_RAM_battery': True, 'physical_console_tested': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'compiled_packets': len(compiled), 'protected_sources': len(files)}))


if __name__ == '__main__':
    main()
