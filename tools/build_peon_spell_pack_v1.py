#!/usr/bin/env python3
"""Build native Shaman effects without regenerating approved character/decor art.

The default target is the normal game. --fixture selects an isolated native
sparring menu with separately compiled objects; it never changes save layouts.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-import', action='store_true')
    parser.add_argument('--fixture', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    rgbds = os.environ.get('PEON_RGBDS', '/workspace/toolchains/rgbds-1.0.4/')
    if not Path(rgbds, 'rgbasm').is_file():
        executable = shutil.which('rgbasm')
        if not executable:
            raise SystemExit('RGBDS is missing; set PEON_RGBDS to its directory.')
        rgbds = str(Path(executable).parent) + '/'
    if not rgbds.endswith('/'):
        rgbds += '/'
    subprocess.run(['make', '-C', 'tools'], check=True)
    if not args.no_import:
        subprocess.run([sys.executable, 'tools/import_peon_spell_pack_v1.py'], check=True)

    # The only permitted artwork converter is the new, namespaced importer.
    # Freeze every historical generated target before asking Make to build.
    frozen = set()
    targets = []
    for line in Path('Makefile').read_text().replace('\\\n', ' ').splitlines():
        if line and not line[0].isspace() and ':' in line and not line.startswith('#'):
            targets = line.split(':', 1)[0].rstrip('& ').split()
        elif re.match(r'\t(?:python3?|node)\s+tools/', line):
            frozen.update(targets)
    missing = sorted(name for name in frozen if not Path(name).is_file())
    if missing:
        raise SystemExit('Preserved inputs missing; refusing artwork regeneration:\n' + '\n'.join(missing))
    target = 'pokecrystal_spell_test.gbc' if args.fixture else 'pokecrystal.gbc'
    command = ['make', target, '-j' + os.environ.get('PEON_JOBS', '4'), 'RGBDS=' + rgbds]
    command += ['--assume-old=' + name for name in sorted(frozen)]
    plan = subprocess.run(command + ['-n'], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if plan.returncode or re.search(r'(?m)^\s*(?:python3?|node)\s+.*tools/', plan.stdout):
        raise SystemExit('Unexpected build plan; no artwork generators were run:\n' + plan.stdout)
    subprocess.run(command, check=True)
    data = Path(target).read_bytes()
    if len(data) != 2097152 or data[0x143] != 0xc0 or data[0x147:0x14a] != bytes((0x10, 6, 3)):
        raise SystemExit('Unexpected CGB/MBC3+RTC/32KiB RAM/battery header.')
    if ((-sum(data[0x134:0x14d]) - 25) & 0xff) != data[0x14d]:
        raise SystemExit('Invalid ROM header checksum.')
    if (sum(data[:0x14e]) + sum(data[0x150:])) & 0xffff != int.from_bytes(data[0x14e:0x150], 'big'):
        raise SystemExit('Invalid ROM global checksum.')
    report = {'target': target, 'sha256': hashlib.sha256(data).hexdigest(),
              'bytes': len(data), 'cgb_only': True, 'mbc3_rtc_ram_battery': True,
              'ram_bytes': 32768, 'physical_modretro_tested': False,
              'historical_generator_outputs_frozen': len(frozen),
              'phase': 'shaman', 'fixture': args.fixture, 'build': 'passed'}
    output = ROOT / 'references/generated/spell_tests'
    output.mkdir(parents=True, exist_ok=True)
    (output / ('fixture_build.json' if args.fixture else 'normal_build.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
