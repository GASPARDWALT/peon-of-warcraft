#!/usr/bin/env python3
"""Read-only native checks reached through cold Continue and ordinary walking."""
from pathlib import Path
import hashlib, importlib.util, json, logging, shutil, tempfile

ROOT = Path('/workspace/peon-of-warcraft')
OUT = Path(__file__).resolve().parent / 'cold_razor_attempt_06'
ROM = Path('/tmp/peon-v0213-candidate2/peon_v0213.gbc')
EXPECTED = 'bd99f73e3397940b67eee82f974a84eb859aa030a14ed6a4d6abcbfe6e7575a7'
EAST = ROOT / 'references/generated/zone_passages_v0213/runtime_6cf84242/east'
spec = importlib.util.spec_from_file_location('ordinary_east', EAST / 'validate.py')
east = importlib.util.module_from_spec(spec)
spec.loader.exec_module(east)
east.OUT = OUT
import verify_visible_metatiles
_original_world = east.PortalSession.world
def exact_world(self, label):
    record = _original_world(self, label)
    record['native_visible_metatiles'] = verify_visible_metatiles.check(self)
    return record
east.PortalSession.world = exact_world


def main():
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256(ROM.read_bytes()).hexdigest() == EXPECTED
    previous = json.loads((EAST / 'attempt_05/validation.json').read_text())
    assert previous['status'] == 'PASS'
    save = previous['generated_private_native_save']
    battery = Path(save['path'])
    assert save['native_save_calls'] == 1 and not save['state_edits']
    assert hashlib.sha256(battery.read_bytes()).hexdigest() == save['sha256']
    report = {'status': 'RUNNING', 'rom_sha256': EXPECTED,
              'ordinary_controls_only': True, 'ram_writes': False,
              'save_states': False, 'cpu_substitution': False,
              'user_saves_opened': False,
              'private_native_battery_provenance': save}
    with tempfile.TemporaryDirectory(prefix='peon-v0213-candidate2-cold-') as directory:
        private_rom = Path(directory) / 'candidate2.gbc'
        shutil.copyfile(ROM, private_rom)
        shutil.copyfile(battery, Path(str(private_rom) + '.ram'))
        session = east.PortalSession(private_rom, east.symbols(ROM.with_suffix('.sym')))
        try:
            session.cold(17)
            session.navigate((4, 8))
            session.world('senjin_canonical_supplied_full_palm')
            session.cross(17, 1, 0, 'ordinary_senjin_road', False)
            session.navigate((8, 7))
            session.world('road_canonical_supplied_full_cactus')
            session.cross(16, 3, 0, 'ordinary_road_razor', False)
            for point, label in [((12, 15), 'razor_south_hornposts_extended_tiles'),
                                 ((11, 10), 'razor_central_terrain_and_facades'),
                                 ((12, 8), 'razor_canonical_rock_and_facades'),
                                 ((12, 5), 'razor_north_hornposts_extended_tiles')]:
                session.navigate(point)
                session.world(label)
            visible = [check for check in session.checks
                       if check['map'] == 18
                       and check['allocator']['visible_extra_signed_cells']]
            assert len(visible) >= 2
            full_razor = [check for check in session.checks if check['map'] == 18
                          and check['native_visible_metatiles']['all360_visible_cells_exact']]
            assert len(full_razor) >= 5
            report['razor_206_patterns_proven'] = True
            report['razor_all360_native_tile_palette_bank_priority_cells_exact'] = True
            report['razor_full360_cell_comparison_views'] = len(full_razor)
            report['razor_visible_extension_checks'] = len(visible)
            report['status'] = 'PASS'
        except Exception as error:
            report['failure'] = repr(error)
            session.capture('first_failure')
            raise
        finally:
            report.update(crossings=session.crossings, allocator_checks=session.checks,
                          captures=session.captures, inputs=session.inputs,
                          final_map=session.map(), final_xy=list(session.position()))
            (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
            session.p.stop(save=False)
    print(json.dumps({'status': report['status'],
                      'allocator_checks': len(report['allocator_checks']),
                      'razor_visible_extension_checks': report['razor_visible_extension_checks']}))


if __name__ == '__main__':
    main()
