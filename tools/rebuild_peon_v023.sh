#!/bin/sh
# Rebuild committed native inputs without replacing tuned stats or old releases.
set -eu
cd "$(dirname "$0")/.."
PEON_REBUILD_MODE=${1:-build}
case "$PEON_REBUILD_MODE" in
    build|--build|--assets-only|--validate) ;;
    *) echo 'Usage: tools/rebuild_peon_v023.sh [--build|--assets-only|--validate]' >&2; exit 2 ;;
esac
PEON_RGBDS=${PEON_RGBDS:-/workspace/toolchains/rgbds-1.0.4/}
PEON_PYBOY_DIR=${PEON_PYBOY_DIR:-/workspace/toolchains/pyboy-preview}

# Retained art is copied to the new output directory. Native PNG/ASM inputs
# are already committed; older generators must not reset calibrated stats.
python3 tools/stage_peon_v023_assets.py
if [ "$PEON_REBUILD_MODE" = '--assets-only' ]; then
    exit 0
fi
make pokecrystal.gbc -j4 RGBDS="$PEON_RGBDS"
python3 tools/lint_durotar_text.py
if [ "$PEON_REBUILD_MODE" != '--validate' ]; then
    exit 0
fi
export PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}"
python3 tools/run_peon_v023_validation.py --jobs 4
python3 tools/build_peon_v023_gallery.py
python3 tools/validate_peon_v023_gallery.py
# Packaging is an explicit final step once all reports match the current ROM:
# python3 tools/package_peon_v023.py
