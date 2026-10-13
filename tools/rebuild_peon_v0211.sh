#!/bin/sh
# Convert the approved user PNG inputs; never redraw older artwork.
set -eu
if [ "${1:-}" != "--check" ] && [ "${1:-}" != "--help" ] && [ "${1:-}" != "-h" ]; then
  printf '%s\n' 'Legacy art regeneration is retired. Use python3 tools/build_peon_art_repair_v0212.py.' >&2
  exit 2
fi
cd "$(dirname "$0")/.."

case "${1:-}" in
  "") PEON_CHECK_ONLY=0 ;;
  --check) PEON_CHECK_ONLY=1 ;;
  -h|--help)
    printf '%s\n' 'Usage: tools/rebuild_peon_v0211.sh [--check]' \
      'Default: verify source art, import v0.2.11 native packets, build the ROM.' \
      '--check: verify prerequisites and preserved PNG inputs without generating or building.' \
      'Overrides: PEON_RGBDS (RGBDS directory), PEON_PYTHON (Python command), PEON_JOBS (default 4).'
    exit 0 ;;
  *) printf '%s\n' 'Unknown argument; use --help.' >&2; exit 2 ;;
esac
[ "$#" -le 1 ] || { printf '%s\n' 'Only one argument is accepted.' >&2; exit 2; }
PEON_PYTHON=${PEON_PYTHON:-python3}
PEON_JOBS=${PEON_JOBS:-4}
if [ -z "${PEON_RGBDS+x}" ]; then
  if [ -x /workspace/toolchains/rgbds-1.0.4/rgbasm ]; then
    PEON_RGBDS=/workspace/toolchains/rgbds-1.0.4/
  else
    PEON_RGBDS=
  fi
fi
if [ -n "$PEON_RGBDS" ]; then PEON_RGBDS=${PEON_RGBDS%/}/; fi
export PEON_RGBDS PEON_JOBS

# ZIP members, approved source PNGs and the environment baseline are required
# inputs. Do not reconstruct a missing baseline from already modified maps.
"$PEON_PYTHON" - "$PEON_CHECK_ONLY" <<'PY'
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import zipfile

root = Path.cwd()
def require(condition, message):
    if not condition:
        raise SystemExit(message)
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

for name in ('numpy', 'PIL'):
    importlib.import_module(name)
require(re.fullmatch(r'[1-9][0-9]*', os.environ['PEON_JOBS']), 'PEON_JOBS must be a positive integer.')
for name in ('rgbasm', 'rgblink', 'rgbfix', 'rgbgfx'):
    command = os.environ['PEON_RGBDS'] + name
    require(shutil.which(command), f'Missing {command}; install RGBDS 1.0.4 or set PEON_RGBDS.')
require(shutil.which('make'), 'GNU make is required.')

archives = {
    'peon_world_character_sheets_split': '0aac67d4de4e49e0f13882be203dc4acda51fafe542570f97d1b1ba5d794e27a',
    'durotar_asset_pack_v1': '2d9bbe4609ffc83c99955ec1065efbf5885bf902e417e5d99c6b31ad77edc7bc',
    'razor_hill_inn_gbc': '27276d86f2d71c77aca899ba73947d6ec12b6ae3042a3d6c747d35779bbbffcb',
}
for name, expected in archives.items():
    archive = root / 'references/characters' / (name + '.zip')
    require(archive.is_file() and digest(archive) == expected, f'Original ZIP missing or changed: {archive}')
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            if member.is_dir():
                continue
            path = root / 'references/characters' / name / member.filename
            require(path.is_file() and digest(path) == hashlib.sha256(source.read(member)).hexdigest(),
                    f'Extracted original differs from preserved ZIP: {path}')

players = root / 'references/generated/user_player_v0211'
player_manifest = json.loads((players / 'manifest.json').read_text())
for item in player_manifest['assets']:
    path = players / item['file']
    require(path.is_file() and digest(path) == item['sha256'], f'Approved player PNG missing or changed: {path}')
npcs = json.loads((root / 'references/generated/user_npc_completion_v0211/manifest.json').read_text())
for item in npcs['sprites']:
    path = root / item['path']
    require(path.is_file() and digest(path) == item['sha256'], f'Approved repaired NPC PNG missing or changed: {path}')
environment = root / 'references/generated/user_environment_v0211'
manifest = json.loads((environment / 'manifest.json').read_text())
for name, expected in manifest['baseline_sha256'].items():
    path = environment / 'baseline' / name
    require(path.is_file() and digest(path) == expected, f'Preserved environment baseline missing or changed: {path}')
print(f'Preserved inputs verified: {len(archives)} ZIPs, {len(player_manifest["assets"])} player PNGs, {len(npcs["sprites"])} repaired NPC PNGs.')
if sys.argv[1] == '1':
    print('Prerequisite check only; no generated files or ROM were changed.')
PY
[ "$PEON_CHECK_ONLY" -eq 0 ] || exit 0

# The battle importer uses this existing compression helper. This target only
# builds the C tools, not source art, gameplay or published releases.
make -C tools
"$PEON_PYTHON" tools/build_peon_user_world_v0211.py
"$PEON_PYTHON" tools/build_peon_user_battle_v0211.py
"$PEON_PYTHON" tools/import_peon_user_environment_v0211.py --apply

# Freeze the old generator outputs individually, including grouped targets.
# A missing legacy output is a concrete error, not permission to redraw it.
# A second guard rejects any Python/Node generator in the resulting make plan.
"$PEON_PYTHON" - <<'PY'
import hashlib
import os
from pathlib import Path
import re
import subprocess

text = Path('Makefile').read_text().replace('\\\n', ' ')
targets = []
frozen = set()
for line in text.splitlines():
    if line and not line[0].isspace() and ':' in line and not line.startswith('#'):
        targets = line.split(':', 1)[0].rstrip('& ').split()
    elif re.match(r'\t(?:python3?|node)\s+tools/', line):
        if 'v0211' not in line.split()[1]:
            frozen.update(targets)
missing = sorted(name for name in frozen if not Path(name).is_file())
if missing:
    raise SystemExit('Preserved legacy outputs are missing; refusing to redraw them:\n' + '\n'.join(missing))
command = ['make', 'pokecrystal.gbc', '-j' + os.environ['PEON_JOBS'], 'RGBDS=' + os.environ['PEON_RGBDS']]
command += ['--assume-old=' + name for name in sorted(frozen)]
plan = subprocess.run(command + ['-n'], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
if plan.returncode:
    raise SystemExit(plan.stdout)
if re.search(r'(?m)^\s*(?:python3?|node)\s+.*tools/', plan.stdout):
    raise SystemExit('Refusing an unexpected artwork generator in the make plan:\n' + plan.stdout)
print(f'Legacy artwork generators disabled ({len(frozen)} preserved outputs).', flush=True)
subprocess.run(command, check=True)
rom = Path('pokecrystal.gbc').read_bytes()
if len(rom) != 2097152 or rom[0x143] != 0xc0 or rom[0x147:0x14a] != bytes((0x10, 6, 3)):
    raise SystemExit('Unexpected GBC/MBC3+RTC/RAM+battery ROM header.')
print('Built ROM SHA-256:', hashlib.sha256(rom).hexdigest())
print('Build complete. Emulator QA on this exact ROM is required before publishing.')
PY
