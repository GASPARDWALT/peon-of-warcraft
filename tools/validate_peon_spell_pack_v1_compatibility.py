#!/usr/bin/env python3
"""Bounded normal-game checks of classes affected by shared FX wrappers.

Reuse the existing read-only native artwork observer for the intro, four world
directions and one ordinary physical/wand turn per class. No battery migration,
full quest replay, RAM writes or emulator states are needed for this change.
"""
import argparse
import hashlib
import json
import logging
from pathlib import Path
import shutil
import tempfile

import validate_peon_user_art_v0211 as artwork

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, default=ROOT / 'pokecrystal.gbc')
    parser.add_argument('--sym', type=Path, default=ROOT / 'pokecrystal.sym')
    parser.add_argument('--out', type=Path, default=ROOT / 'references/generated/spell_tests/compatibility')
    parser.add_argument('--expected-sha', required=True)
    args = parser.parse_args()
    sha = hashlib.sha256(args.rom.read_bytes()).hexdigest()
    assert sha == args.expected_sha, 'Normal ROM differs from requested build'
    logging.disable(logging.CRITICAL)
    args.out.mkdir(parents=True, exist_ok=True)
    artwork.OUT = artwork.BASE = args.out
    artwork.routes.OUT = args.out
    sym = artwork.symbols_from_file(args.sym)
    report = {'rom_sha256': sha, 'passed': False, 'classes': {},
              'ordinary_controls_only': True, 'ram_writes': False,
              'emulator_states_loaded': False, 'user_batteries_opened': False,
              'scope': 'Normal intro, imported class movement and one native basic attack turn per class.'}
    with tempfile.TemporaryDirectory(prefix='peon-spell-v1-normal-art-') as temp:
        for index, name in enumerate(artwork.CLASSES):
            rom = Path(temp) / (name + '.gbc')
            shutil.copyfile(args.rom, rom)
            session = artwork.GraphicsSession(rom, sym, index)
            try:
                session.fresh_class()
                session.advance(90)
                world = session.world_vram()
                assert session.hold_import, 'Native opening did not display Grommash Hold'
                walking = session.world_cycle()
                # The existing first quest encounter is sufficient to exercise
                # the shared wrappers and all three imported rear poses.
                session.talk_plain((10, 10), 'up')
                session.navigate((18, 13))
                session.press('up', 30)
                session.press('a', 60)
                session.wait(lambda: session.phase == 'battle', buttons=True)
                session.advance(60)
                enemy = session.enemy_import()
                strike = session.cast_once(0, 'basic_strike_after_spell_import', (0, 1, 2))
                assert not session.hook_errors, session.hook_errors
                report['classes'][name] = {'passed': True, 'native_world_packet': world,
                    'four_world_directions': walking, 'native_basic_attack': strike,
                    'enemy_front_packet': enemy, 'protected_battle_uploads': session.uploads,
                    'read_only_hook_errors': session.hook_errors,
                    'world_oam_limits': session.oam_report}
                print(name + ': normal class artwork and attack PASS', flush=True)
            except BaseException as error:
                session.capture('compatibility_failure')
                report['failure'] = {'class': name, 'error': repr(error),
                                     'read_only_hook_errors': session.hook_errors}
                (args.out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
                raise
            finally:
                session.p.stop(save=False)
    assert hashlib.sha256(args.rom.read_bytes()).hexdigest() == sha
    report['passed'] = True
    (args.out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'rom_sha256': sha, 'passed': True, 'classes': list(report['classes'])}, indent=2))


if __name__ == '__main__':
    main()
