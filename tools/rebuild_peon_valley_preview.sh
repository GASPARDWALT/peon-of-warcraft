#!/bin/sh
# Rebuild only this preview's native inputs; preserve all published releases.
set -eu
cd "$(dirname "$0")/.."
PEON_VALLEY_MODE=${1:-build}
case "$PEON_VALLEY_MODE" in
    build|--build|--assets-only|--validate) ;;
    *) echo 'Usage: tools/rebuild_peon_valley_preview.sh [--build|--assets-only|--validate]' >&2; exit 2 ;;
esac
PEON_RGBDS=${PEON_RGBDS:-/workspace/toolchains/rgbds-1.0.4/}
PEON_PYBOY_DIR=${PEON_PYBOY_DIR:-/workspace/toolchains/pyboy-preview}

python3 tools/build_peon_food_icon.py
python3 tools/build_peon_environment_polish.py
python3 tools/build_peon_player_hud.py
python3 tools/build_peon_valley_sfx.py
python3 tools/build_peon_atlas_objectives.py
python3 tools/build_peon_wayfinding_preview.py
python3 tools/build_durotar_maps.py \
    --source references/generated/valley_layout_update/world \
    --output references/generated/valley_layout_update
if [ "$PEON_VALLEY_MODE" = '--assets-only' ]; then
    exit 0
fi
make pokecrystal.gbc -j4 RGBDS="$PEON_RGBDS"
python3 tools/lint_durotar_text.py
if [ "$PEON_VALLEY_MODE" != '--validate' ]; then
    exit 0
fi
export PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}"
python3 tools/validate_peon_cave_approach.py
python3 tools/validate_peon_atlas_player_objectives.py
python3 tools/validate_peon_camp_population.py
python3 tools/validate_peon_player_hud.py
python3 tools/validate_peon_valley_upgrade.py
python3 tools/validate_peon_valley_sfx.py
python3 tools/validate_peon_valley_source.py
# Build/source-contract evidence and packaging are separate final steps.
