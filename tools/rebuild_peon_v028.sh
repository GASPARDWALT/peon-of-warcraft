#!/bin/sh
# Only new v028 generators; preserve previously published art and evidence.
set -eu
cd "$(dirname "$0")/.."
PEON_RGBDS=${PEON_RGBDS:-/workspace/toolchains/rgbds-1.0.4/}
python3 tools/build_peon_player_classes_v028.py
python3 tools/build_peon_combat_assets_v028.py
python3 tools/build_peon_environment_v028.py
make pokecrystal.gbc -j4 RGBDS="$PEON_RGBDS"
python3 tools/lint_durotar_text.py
python3 -c 'import hashlib; print("Built ROM SHA-256:", hashlib.sha256(open("pokecrystal.gbc", "rb").read()).hexdigest())'
