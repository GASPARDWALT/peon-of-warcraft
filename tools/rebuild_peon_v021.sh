#!/bin/sh
# Rebuild from retained concept PNGs and source music, then validate/package.
set -eu
cd "$(dirname "$0")/.."
PEON_RGBDS=${PEON_RGBDS:-/workspace/toolchains/rgbds-1.0.4/}
PEON_PYBOY_DIR=${PEON_PYBOY_DIR:-/workspace/toolchains/pyboy-preview}
python3 tools/build_durotar_assets.py
python3 tools/build_durotar_extra_assets.py
python3 tools/build_durotar_village_assets.py
python3 tools/build_durotar_village_battles.py
python3 tools/build_peon_speaker_portraits.py
python3 tools/build_peon_menu_skin.py
python3 tools/build_peon_atlas_quests.py
python3 tools/build_durotar_world.py
python3 tools/build_peon_interiors.py
python3 tools/build_peon_beast_attacks.py
python3 tools/build_peon_title_music.py
python3 tools/build_peon_sfx.py
python3 tools/build_durotar_maps.py --source references/generated/durotar_v021/world --output references/generated/durotar_v021
make -j4 RGBDS="$PEON_RGBDS"
python3 tools/lint_durotar_text.py
PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 tools/validate_peon_intro.py
PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 tools/validate_peon_sprite.py
PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 tools/validate_peon_save_upgrade.py
PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 tools/validate_peon_villages.py
PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 tools/validate_peon_speaker_portraits.py
PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 tools/build_peon_beast_attacks.py --validate
PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 tools/validate_peon_title_music.py
PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 tools/validate_peon_sfx.py
PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 tools/validate_peon_lazy_quest.py
PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 tools/validate_peon_atlas_quests.py
PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 tools/validate_peon_menu_skin.py
python3 tools/build_peon_v021_gallery.py
python3 tools/package_peon_v021.py
