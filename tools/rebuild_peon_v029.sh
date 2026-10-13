#!/bin/sh
# Regenerate only v029 art; isolate Make so old visual releases stay untouched.
set -eu
PEON_REPOSITORY=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PEON_RGBDS=${PEON_RGBDS:-}
PEON_MAKE_JOBS=${PEON_MAKE_JOBS:-4}
if [ -z "$PEON_RGBDS" ] && [ -x /workspace/toolchains/rgbds-1.0.4/rgbasm ]; then
    PEON_RGBDS=/workspace/toolchains/rgbds-1.0.4/
fi
case "$PEON_RGBDS" in
    ""|*/) ;;
    *) PEON_RGBDS="$PEON_RGBDS/" ;;
esac
python3 - "$PEON_REPOSITORY" "$PEON_RGBDS" "$PEON_MAKE_JOBS" <<'PY'
from pathlib import Path
import hashlib
import shutil
import subprocess
import sys
import tempfile

source = Path(sys.argv[1])
rgbds, jobs = sys.argv[2], int(sys.argv[3])
if jobs < 1:
    raise SystemExit("PEON_MAKE_JOBS must be a positive integer")

def run(arguments, directory):
    subprocess.run(arguments, cwd=directory, check=True)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

art_directories = (
    "gfx/peon_recruits_v029",
    "gfx/peon_native_v029",
    "gfx/peon_combat_v029",
)
# Build inputs, never arbitrary untracked uploads, old proof files or releases.
tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=source)
inputs = {Path(name.decode()) for name in tracked.split(b"\0") if name}
# These inputs are authored without equivalent PNG sources. The shared
# Unown dictionaries are canonical ASM rather than generated species files.
# Keep an explicit list even when these currently happen to be tracked.
canonical_inputs = (
    "gfx/pack/peon_atlas_fog.2bpp",
    "gfx/title/peon_portal/tiles.2bpp",
    "gfx/pokemon/unown/bitmask.asm",
    "gfx/pokemon/unown/frames.asm",
)
missing_canonical = [name for name in canonical_inputs
                     if not (source / name).is_file()]
if missing_canonical:
    raise SystemExit("Missing canonical authored inputs: "
                     + ", ".join(missing_canonical))
inputs.update(map(Path, canonical_inputs))
new_sources = (
    "engine/overworld/peon_geography_migration_v029.asm",
    "engine/battle/peon_resources_v029.asm",
    "engine/menus/peon_team_v029.asm",
    "engine/items/peon_recruitment_v029.asm",
    "engine/events/peon_rest_loot_v029.asm",
    "engine/battle/peon_move_info_v029.asm",
    "engine/battle/peon_pack_transition_v029.asm",
    "engine/battle/peon_packs_v029.asm",
    "engine/battle/peon_ally_visuals_v029.asm",
    "gfx/peon_recruits_pics_v029.asm",
    "tools/build_peon_combat_assets_v029.py",
    "tools/build_peon_native_recruits_v029.py",
    "tools/build_peon_recruit_assets_v029.py",
)
inputs.update(map(Path, new_sources))
for folder in art_directories:
    inputs.update(path.relative_to(source) for path in (source / folder).rglob("*")
                  if path.is_file())

excluded_prefixes = ("releases/", "references/generated/", ".git/")
inputs = {path for path in inputs if not path.as_posix().startswith(excluded_prefixes)
          and "__pycache__" not in path.parts
          and path.suffix not in (".o", ".gbc", ".gb", ".sym", ".map", ".ram")}
expected_art = {path.relative_to(source): digest(path)
                for folder in art_directories
                for path in (source / folder).rglob("*") if path.is_file()}
if not expected_art:
    raise SystemExit("Missing reviewed gfx/peon_*_v029 inputs")

with tempfile.TemporaryDirectory(prefix="peon-v029-rebuild-") as scratch:
    work = Path(scratch) / "source"
    work.mkdir()
    for relative in sorted(inputs):
        original, target = source / relative, work / relative
        if not original.is_file():
            continue  # Respect a locally deleted tracked file.
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)

    # Recreate every v029 output from the three authoring generators.
    # A leftover compressed packet must not conceal a missing source rule.
    for folder in art_directories:
        shutil.rmtree(work / folder)

    run(["make", "-C", "tools", f"-j{jobs}"], work)
    # Arrow packets retain the reviewed Firebolt prefix. Its ignored 2bpp
    # dependency may be absent in a fresh clone: encode it from the existing
    # pure pattern library without invoking the old visual-output generator.
    run([sys.executable, "-c", (
        "import sys; from pathlib import Path; sys.path.insert(0, 'tools'); "
        "from build_peon_combat_assets_v028 import FIRE, SHADOW, indices, encode; "
        "p = Path('gfx/peon_combat_v028/projectiles.2bpp'); "
        "p.parent.mkdir(parents=True, exist_ok=True); "
        "p.write_bytes(b''.join(encode(indices(f)) for f in FIRE + SHADOW))"
    )], work)
    for generator in ("build_peon_recruit_assets_v029.py",
                      "build_peon_native_recruits_v029.py",
                      "build_peon_combat_assets_v029.py"):
        run([sys.executable, "tools/" + generator], work)
    run(["make", "pokecrystal.gbc", f"-j{jobs}", "RGBDS=" + rgbds], work)
    # Make materializes compressed .lz packets after the raw generators.
    mismatch = [str(relative) for relative, expected in expected_art.items()
                if not (work / relative).is_file()
                or digest(work / relative) != expected]
    if mismatch:
        raise SystemExit("Regenerated art differs from reviewed inputs: "
                         + ", ".join(mismatch[:20]))

    run([sys.executable, "tools/lint_durotar_text.py"], work)
    # Only the native build is returned; no art/proof/gallery is overwritten.
    for name in ("pokecrystal.gbc", "pokecrystal.sym", "pokecrystal.map"):
        result = work / name
        if not result.is_file() or not result.stat().st_size:
            raise SystemExit("Missing build result: " + name)
        shutil.copy2(result, source / name)
    print("Built ROM SHA-256:", digest(source / "pokecrystal.gbc"))
PY
