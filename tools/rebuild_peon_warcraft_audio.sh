#!/bin/sh
# Rebuild the new audio/glow inputs without rewriting released evidence.
set -eu
cd "$(dirname "$0")/.."
PEON_AUDIO_MODE=${1:-build}
case "$PEON_AUDIO_MODE" in
    build|--build|--validate) ;;
    *) echo 'Usage: tools/rebuild_peon_warcraft_audio.sh [--build|--validate]' >&2; exit 2 ;;
esac
PEON_RGBDS=${PEON_RGBDS:-/workspace/toolchains/rgbds-1.0.4/}
PEON_PYBOY_DIR=${PEON_PYBOY_DIR:-/workspace/toolchains/pyboy-preview}

python3 tools/build_peon_audio_expansion.py
python3 tools/build_peon_ambient_refinement.py
python3 tools/build_peon_level_glow.py
python3 tools/build_peon_durotar_trees.py
make pokecrystal.gbc -j4 RGBDS="$PEON_RGBDS"
python3 tools/lint_durotar_text.py
python3 tools/validate_peon_warcraft_source.py
if [ "$PEON_AUDIO_MODE" != '--validate' ]; then
    exit 0
fi
export PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}"
python3 tools/build_peon_ambient_refinement.py --validate
PEON_AUDIO_SHA=$(python3 -c 'import hashlib; print(hashlib.sha256(open("pokecrystal.gbc", "rb").read()).hexdigest())')
python3 tools/validate_peon_audio_expansion.py --section sfx --expected-sha "$PEON_AUDIO_SHA"
python3 tools/validate_peon_audio_expansion.py --section normal --expected-sha "$PEON_AUDIO_SHA"
python3 tools/validate_peon_audio_expansion.py --section music --expected-sha "$PEON_AUDIO_SHA"
