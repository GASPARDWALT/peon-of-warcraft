#!/bin/sh
# The v0.2.5 pipeline replaces native art without rerunning historical maps.
set -eu
cd "$(dirname "$0")/.."
PEON_ENV_MODE=${1:---build}
case "$PEON_ENV_MODE" in
    --build|--validate) ;;
    *) echo 'Usage: tools/rebuild_peon_v025.sh [--build|--validate]' >&2; exit 2 ;;
esac
PEON_RGBDS=${PEON_RGBDS:-/workspace/toolchains/rgbds-1.0.4/}
PEON_PYBOY_DIR=${PEON_PYBOY_DIR:-/workspace/toolchains/pyboy-preview}
python3 tools/build_peon_environment_palettes.py
python3 tools/build_peon_readable_font.py
python3 tools/build_peon_potion_assets.py
python3 tools/build_peon_pet_mail_assets.py
python3 tools/build_peon_environment_v025.py
python3 tools/build_peon_valley_zones_v025.py
python3 tools/build_durotar_maps.py --native-palettes --source references/generated/environment_v025/zone_layout --output references/generated/environment_v025
python3 tools/build_peon_valley_atlas_v025.py
make pokecrystal.gbc -j4 RGBDS="$PEON_RGBDS"
python3 tools/lint_durotar_text.py
python3 tools/validate_peon_environment_regressions.py --section source
if [ "$PEON_ENV_MODE" != '--validate' ]; then
    exit 0
fi
export PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}"
PEON_ENV_SHA=$(python3 -c 'import hashlib; print(hashlib.sha256(open("pokecrystal.gbc", "rb").read()).hexdigest())')
python3 tools/validate_peon_environment_v025.py --expected-sha "$PEON_ENV_SHA"
python3 tools/validate_peon_environment_regressions.py --section quests
python3 tools/validate_peon_environment_regressions.py --section atlas
python3 tools/validate_peon_environment_regressions.py --section ui
python3 tools/validate_peon_environment_regressions.py --section upgrade
python3 tools/validate_peon_class_routes.py --section normal --expected-sha "$PEON_ENV_SHA"
python3 tools/validate_peon_class_routes.py --section trainer --expected-sha "$PEON_ENV_SHA"
python3 tools/validate_peon_class_spells.py --expected-rom-sha256 "$PEON_ENV_SHA"
python3 tools/validate_peon_class_potions.py --section all --expected-rom-sha "$PEON_ENV_SHA"
python3 tools/validate_peon_rare_loot.py --expected-sha "$PEON_ENV_SHA"
python3 tools/validate_peon_warlock_pet.py --expected-sha "$PEON_ENV_SHA"
python3 tools/validate_peon_readable_font.py --expected-sha "$PEON_ENV_SHA"
