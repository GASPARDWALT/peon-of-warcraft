#!/bin/sh
# Rebuild polished native art and validate without rewriting earlier releases.
set -eu
cd "$(dirname "$0")/.."
PEON_POLISH_MODE=${1:---build}
case "$PEON_POLISH_MODE" in
    --build|--validate) ;;
    *) echo 'Usage: tools/rebuild_peon_v024.sh [--build|--validate]' >&2; exit 2 ;;
esac
PEON_RGBDS=${PEON_RGBDS:-/workspace/toolchains/rgbds-1.0.4/}
PEON_PYBOY_DIR=${PEON_PYBOY_DIR:-/workspace/toolchains/pyboy-preview}

python3 tools/build_peon_world_polish.py
python3 tools/build_durotar_maps.py --source references/generated/deep_polish/world --output references/generated/deep_polish/world
python3 tools/build_peon_player_hud.py
make pokecrystal.gbc -j4 RGBDS="$PEON_RGBDS"
python3 tools/lint_durotar_text.py
python3 tools/validate_peon_deep_source.py
if [ "$PEON_POLISH_MODE" != '--validate' ]; then
    exit 0
fi
export PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}"
PEON_POLISH_SHA=$(python3 -c 'import hashlib; print(hashlib.sha256(open("pokecrystal.gbc", "rb").read()).hexdigest())')
python3 tools/validate_peon_fixed_hud.py
python3 tools/validate_peon_world_polish.py --expected-sha "$PEON_POLISH_SHA"
python3 tools/validate_peon_deep_ui.py --expected-rom-sha "$PEON_POLISH_SHA"
python3 tools/validate_peon_deep_quests.py --section normal --expected-sha "$PEON_POLISH_SHA"
python3 tools/validate_peon_deep_quests.py --section diagnostic --expected-sha "$PEON_POLISH_SHA"
python3 tools/validate_peon_services_polish.py --section all --expected-rom-sha256 "$PEON_POLISH_SHA"
python3 tools/validate_peon_combat_lifecycle.py
python3 tools/validate_peon_unlimited_mace.py
python3 tools/validate_peon_deep_combat_retained.py spells
python3 tools/validate_peon_deep_combat_retained.py totems
python3 tools/validate_peon_deep_atlas.py
python3 tools/validate_peon_deep_audio.py --expected-sha "$PEON_POLISH_SHA"
python3 tools/validate_peon_deep_upgrade.py
