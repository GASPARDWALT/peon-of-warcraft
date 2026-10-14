#!/usr/bin/env python3
"""Build the real game while refusing historical artwork regeneration."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main(report_directory='references/generated/art_repair_v0212', preserved_input_roots=()):
    os.chdir(ROOT)
    rgbds = os.environ.get('PEON_RGBDS', '/workspace/toolchains/rgbds-1.0.4/')
    if not Path(rgbds, 'rgbasm').is_file():
        executable = shutil.which('rgbasm')
        if not executable:
            raise SystemExit('RGBDS is missing; set PEON_RGBDS to its directory.')
        rgbds = str(Path(executable).parent)
    rgbds = rgbds.rstrip('/') + '/'
    subprocess.run(['make', '-C', 'tools'], check=True)
    frozen = set()
    targets = []
    for line in Path('Makefile').read_text().replace('\\\n', ' ').splitlines():
        if line and not line[0].isspace() and ':' in line and not line.startswith('#'):
            targets = line.split(':', 1)[0].rstrip('& ').split()
        elif re.match(r'\t(?:python3?|node)\s+tools/', line):
            frozen.update(targets)
    historical_count = len(frozen)
    for directory in preserved_input_roots:
        folder = Path(directory)
        if not folder.is_dir():
            raise SystemExit('Preserved native packet directory missing: ' + directory)
        frozen.update(str(path) for path in folder.rglob('*') if path.is_file()
                      and path.suffix in ('.2bpp', '.1bpp', '.bin', '.lz', '.gbcpal'))
    missing = sorted(name for name in frozen if not Path(name).is_file())
    if missing:
        raise SystemExit('Preserved inputs missing; refusing artwork regeneration:\n' + '\n'.join(missing))
    command = ['make', 'pokecrystal.gbc', '-j' + os.environ.get('PEON_JOBS', '4'), 'RGBDS=' + rgbds]
    command += ['--assume-old=' + name for name in sorted(frozen)]
    plan = subprocess.run(command + ['-n'], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if plan.returncode or re.search(r'(?m)^\s*(?:python3?|node)\s+.*tools/', plan.stdout):
        raise SystemExit('Unexpected build plan; no artwork generators were run:\n' + plan.stdout)
    subprocess.run(command, check=True)
    data = Path('pokecrystal.gbc').read_bytes()
    assert len(data) == 2097152 and data[0x143] == 0xc0
    assert data[0x147:0x14a] == bytes((0x10, 6, 3)), 'CGB/MBC3+RTC/32KiB RAM/battery header'
    assert ((-sum(data[0x134:0x14d]) - 25) & 0xff) == data[0x14d]
    assert (sum(data[:0x14e]) + sum(data[0x150:])) & 0xffff == int.from_bytes(data[0x14e:0x150], 'big')
    report = {'rom': 'pokecrystal.gbc', 'sha256': hashlib.sha256(data).hexdigest(),
              'bytes': len(data), 'build': 'passed', 'historical_generator_outputs_frozen': historical_count,
              'versioned_native_packets_frozen': len(frozen) - historical_count,
              'cgb_only': True, 'mbc3_rtc_ram_battery': True, 'ram_bytes': 32768,
              'physical_modretro_tested': False,
              'visual_quality_requires_emulator_review': True}
    output = ROOT / report_directory
    output.mkdir(parents=True, exist_ok=True)
    (output / 'build.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
