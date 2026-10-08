#!/bin/sh
# Deterministic rebuild from retained native PNGs, concept atlases and scores.
# No image service, downloads, make clean or changes to published v0.2.1 art.
set -eu
cd "$(dirname "$0")/.."
PEON_REBUILD_MODE=${1:-build}
case "$PEON_REBUILD_MODE" in
    build|--build|--assets-only|--validate) ;;
    *) echo 'Usage: tools/rebuild_peon_v022.sh [--build|--assets-only|--validate]' >&2; exit 2 ;;
esac
PEON_RGBDS=${PEON_RGBDS:-/workspace/toolchains/rgbds-1.0.4/}
PEON_PYBOY_DIR=${PEON_PYBOY_DIR:-/workspace/toolchains/pyboy-preview}

# Re-export unchanged legacy concepts into v022. Their original SOURCE paths
# stay read-only; only OUT changes. Base player/master/imp native PNGs remain
# committed Makefile inputs, so their old published galleries are not rebuilt.
python3 - <<'PY'
import hashlib
import importlib
import sys
from pathlib import Path

root=Path.cwd();sys.path.insert(0,str(root/'tools'))
published=root/'references/generated/durotar_v021'
def snapshot():
    return {str(p.relative_to(published)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in published.rglob('*') if p.is_file()}
before=snapshot()
for name,folder in [('build_durotar_village_assets','village_assets'),
                    ('build_durotar_village_battles','village_battles'),
                    ('build_peon_speaker_portraits','speaker_portraits'),
                    ('build_peon_menu_skin','menu_skin'),
                    ('build_peon_beast_attacks','combat_assets')]:
    module=importlib.import_module(name)
    module.OUT=root/'references/generated/durotar_v022'/folder
    module.main()
assert snapshot()==before,'A generator changed the published v0.2.1 assets'
PY
python3 tools/build_peon_enemy_roster.py
python3 tools/build_peon_enemy_profiles.py
python3 tools/build_peon_item_catalog.py
python3 tools/build_peon_battle_totems.py
python3 tools/build_peon_spell_particles.py
python3 tools/build_peon_quest_markers.py
python3 tools/build_peon_ambient_music.py
python3 tools/build_peon_title_music.py
python3 tools/build_peon_sfx.py
# Map-dependent order: geometry first, opened doors/furniture second, native
# region thumbnails third, quest coordinates/atlas previews last.
python3 tools/build_durotar_world.py
python3 tools/build_peon_interiors.py
python3 tools/build_durotar_maps.py --source references/generated/durotar_v022/world --output references/generated/durotar_v022
python3 tools/build_peon_atlas_quests.py

if [ "$PEON_REBUILD_MODE" = '--assets-only' ]; then
    exit 0
fi
make -j4 RGBDS="$PEON_RGBDS"
python3 tools/lint_durotar_text.py
if [ "$PEON_REBUILD_MODE" != '--validate' ]; then
    exit 0
fi
export PYTHONPATH="$PEON_PYBOY_DIR${PYTHONPATH:+:$PYTHONPATH}"
python3 tools/validate_peon_new_game.py
python3 tools/validate_durotar_v022_quests.py
python3 tools/validate_durotar_v022_quest_faults.py
python3 tools/validate_peon_quest_xp.py
python3 tools/validate_peon_trainer.py
python3 tools/validate_peon_inns.py
python3 tools/validate_peon_save_upgrade.py
python3 tools/validate_peon_villages.py
python3 tools/validate_peon_lazy_quest.py
python3 tools/validate_peon_atlas_quests.py
python3 tools/validate_peon_quest_markers.py
python3 tools/validate_peon_menu_skin.py
python3 tools/validate_peon_sprite.py
python3 tools/validate_peon_speaker_portraits.py
python3 tools/validate_peon_enemy_profiles.py
python3 tools/build_peon_enemy_roster.py --validate
python3 tools/build_peon_beast_attacks.py --validate
python3 tools/validate_peon_spell_effects.py
python3 tools/validate_peon_spell_animations.py
python3 tools/validate_peon_battle_totems.py
python3 tools/validate_peon_item_icons.py
python3 tools/validate_peon_title_music.py
python3 tools/validate_peon_ambient_music.py
python3 tools/validate_peon_sfx.py
python3 tools/build_peon_v022_gallery.py
# Packaging remains an explicit final command after reviewing the reports:
# python3 tools/package_peon_v022.py
