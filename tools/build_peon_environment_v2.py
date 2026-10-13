#!/usr/bin/env python3
"""Build the isolated native map fixture without regenerating previous artwork.

Test objects have their own suffix, so changing the compile-time spawn cannot
reuse normal-game objects with stale flags or overwrite published releases.
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
    parser.add_argument('--normal', action='store_true', help='Build the normal game entry instead of the test fixture.')
    args = parser.parse_args()
    os.chdir(ROOT)
    rgbds = os.environ.get('PEON_RGBDS', '/workspace/toolchains/rgbds-1.0.4/')
    if not Path(rgbds, 'rgbasm').is_file():
        executable = shutil.which('rgbasm')
        if not executable:
            raise SystemExit('RGBDS is missing; set PEON_RGBDS to its installed directory.')
        rgbds = str(Path(executable).parent) + '/'
    if not rgbds.endswith('/'):
        rgbds += '/'
    subprocess.run(['make', '-C', 'tools'], check=True)
    if not args.no_import:
        subprocess.run([sys.executable, 'tools/import_peon_environment_v2.py'], check=True)

    # Freeze all historical generators, including the existing approved v0211
    # outputs. The new importer writes only its own namespaced test files.
    frozen = set()
    targets = []
    for line in Path('Makefile').read_text().replace('\\\n', ' ').splitlines():
        if line and not line[0].isspace() and ':' in line and not line.startswith('#'):
            targets = line.split(':', 1)[0].rstrip('& ').split()
        elif re.match(r'\t(?:python3?|node)\s+tools/', line):
            frozen.update(targets)
    missing = sorted(name for name in frozen if not Path(name).is_file())
    if missing:
        raise SystemExit('Preserved inputs are missing; refusing artwork regeneration:\n' + '\n'.join(missing))
    target = 'pokecrystal.gbc' if args.normal else 'pokecrystal_environment_test.gbc'
    command = ['make', target, '-j' + os.environ.get('PEON_JOBS', '4'), 'RGBDS=' + rgbds]
    command += ['--assume-old=' + name for name in sorted(frozen)]
    plan = subprocess.run(command + ['-n'], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if plan.returncode or re.search(r'(?m)^\s*(?:python3?|node)\s+.*tools/', plan.stdout):
        raise SystemExit('Unexpected build plan; no artwork generators were run:\n' + plan.stdout)
    subprocess.run(command, check=True)
    data = Path(target).read_bytes()
    if len(data) != 2097152 or data[0x143] != 0xc0 or data[0x147:0x14a] != bytes((0x10, 6, 3)):
        raise SystemExit('Unexpected CGB/MBC3+RTC/32KiB RAM/battery header.')
    report = {'target': target, 'sha256': hashlib.sha256(data).hexdigest(),
              'bytes': len(data), 'cgb_only': True, 'mbc3_rtc_ram_battery': True,
              'ram_bytes': 32768, 'physical_modretro_tested': False,
              'historical_generator_outputs_frozen': len(frozen),
              'build': 'passed'}
    output = ROOT / 'references/generated/map_tests'
    output.mkdir(parents=True, exist_ok=True)
    (output / ('normal_build.json' if args.normal else 'build.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
