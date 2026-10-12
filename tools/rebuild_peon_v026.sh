#!/bin/sh
# Regenerate only v0.2.6 art; preserve previously published references/releases.
set -eu
cd "$(dirname "$0")/.."
PEON_RGBDS=${PEON_RGBDS:-/workspace/toolchains/rgbds-1.0.4/}
python3 tools/peon_horde_emblem_v026.py
python3 tools/build_peon_text_font_v026.py
make gfx/sprites/peon.2bpp gfx/peon_player_battle/back_frames.2bpp RGBDS="$PEON_RGBDS"
python3 tools/build_peon_player_classes_v026.py
python3 tools/build_peon_pet_spell_assets_v026.py
python3 tools/build_peon_environment_v026.py
make pokecrystal.gbc -j4 RGBDS="$PEON_RGBDS"
python3 tools/lint_durotar_text.py
python3 -c 'import hashlib; print("Built ROM SHA-256:", hashlib.sha256(open("pokecrystal.gbc", "rb").read()).hexdigest())'
