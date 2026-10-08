#!/usr/bin/env python3
"""Native atlas restore/fog plus new finite-quest objectives, no old outputs."""
import ast
import hashlib
import inspect
import json
import logging
import shutil
import tempfile
import textwrap
from pathlib import Path

import run_peon_v023_validation as adapter
import validate_durotar_v022_quests as game
import validate_peon_atlas_player_objectives as retained
from validate_peon_villages import load_symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/deep_polish/atlas'


def redirect():
    for module in adapter.local_dependencies(retained):
        for key in ('OUT', 'OUTPUT'):
            if hasattr(module, key):
                setattr(module, key, OUT)
    # More real quest objectives need eleven OAM entries. Retain all actual
    # pixel, register, palette, CPU, fog and scanline assertions unchanged.
    tree = ast.parse(textwrap.dedent(inspect.getsource(retained.AtlasSession.check_atlas)))
    class Capacity(ast.NodeTransformer):
        def visit_Assert(self, node):
            if ast.unparse(node.test) == 'len(visible) <= 9':
                node.test.comparators[0] = ast.Constant(11)
            return node
    namespace = dict(retained.__dict__)
    exec(compile(ast.fix_missing_locations(Capacity().visit(tree)), __file__, 'exec'), namespace)
    retained.AtlasSession.check_atlas = namespace['check_atlas']


class Session(retained.AtlasSession):
    def expected(self, region):
        entries, points = super().expected(region)
        flag = lambda n: self.event('EVENT_PEON_' + n)
        if not flag('DISCOVERED_' + region):
            return entries, points
        active = flag('FAMILIARS_ACCEPTED') and not any(flag(n) for n in
                   ('FAMILIARS_DONE', 'MEDALLION_ACCEPTED', 'MEDALLION_DONE'))
        outside = [('CAVE_APPROACH_IMP_1_DEAD', (25, 6)),
                   ('CAVE_APPROACH_IMP_2_DEAD', (27, 9))]
        inside = [('CAVE_STRONG_IMP_DEAD', (12, 8)), ('CAVE_IMP_DEAD', (8, 10))]
        def objective(name, xy):
            entries.append([*retained.projected(region, xy), 0, 4])
            points.append({'type': 'objective', 'identity': name})
        if region == 'DEN' and flag('MAP_RECEIVED') and (not flag('GEAR_REWARDED') or (
                flag('SARKOTH_DONE') and not flag('SARKOTH_REPORT_DONE'))):
            i = 1 if points and points[0]['type'] == 'player' else 0
            entries.insert(i, [*retained.projected(region, (10, 9)), 1, 4])
            points.insert(i, {'type': 'questgiver', 'identity': 'GORNEK_REPORT', 'state': 'ready'})
        if region == 'VALLEY':
            if active:
                state = 'ready' if all(flag(n) for n, _ in outside + inside) else 'active'
                for i, point in enumerate(points):
                    if point.get('identity') == 'VALLEY_MEDALLION':
                        point['state'] = state
                        entries[i][2:] = [1, 4 if state == 'ready' else 7]
                if not all(flag(n) for n, _ in inside):
                    objective('CAVE_ENTRANCE', (24, 4))
                for n, xy in outside:
                    if not flag(n):
                        objective(n, xy)
        elif region == 'CAVERN' and active:
            for n, xy in inside:
                if not flag(n):
                    objective(n, xy)
        return entries, points


def main():
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    redirect()
    adapter.adapt_v023_gameplay(game)
    sha = hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest()
    report = {'rom_sha256': sha, 'normal_route': [], 'diagnostic_cases': [], 'all_checks_passed': False}
    s = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-deep-atlas-') as temp:
            rom = Path(temp) / 'game.gbc'
            shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = Session(rom, load_symbols())
            s.fresh()
            calls = len(s.atlas_calls)
            s.press('select', 180); s.press('b', 180)
            assert len(s.atlas_calls) == calls, 'Map appeared before reward'
            s.talk((10, 10), 'up', 'normal_accept_cutting_teeth')
            loads = s.encounter_loads
            s.navigate((18, 13)); s.press('up', 30); s.press('a', 120)
            s.fight('normal_boar', 'EVENT_PEON_QUEST_DONE', baseline=loads)
            s.talk((10, 10), 'up', 'normal_boar_reward'); s.rest()
            s.talk((10, 10), 'up', 'normal_accept_scorpid')
            loads = s.encounter_loads; s.navigate((17, 15))
            s.fight('normal_scorpid', 'EVENT_PEON_SCORPID_DEFEATED', baseline=loads)
            s.talk((10, 10), 'up', 'normal_earned_map'); s.rest()
            assert s.event('EVENT_PEON_MAP_RECEIVED')
            normal, diagnostic = report['normal_route'], report['diagnostic_cases']
            s.check_atlas('normal_den_fixed_map', normal)
            s.check_atlas('normal_valley_fog', normal, 'VALLEY')
            s.to_valley()
            s.talk((5, 11), 'right', 'normal_accept_familiars')
            assert s.event('EVENT_PEON_FAMILIARS_ACCEPTED')
            row = s.check_atlas('normal_familiars_two_live_targets_and_cave', normal)
            assert {'CAVE_ENTRANCE', 'CAVE_APPROACH_IMP_1_DEAD', 'CAVE_APPROACH_IMP_2_DEAD'} <= {
                p.get('identity') for p in row['points']}
            # From here event fixtures are explicitly diagnostic. The ordinary
            # quest validator independently wins all four actual encounters.
            s.set_flag('EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD')
            s.check_atlas('diagnostic_first_familiar_target_removed', diagnostic, diagnostic=True)
            s.set_flag('EVENT_PEON_CACTUS_ACCEPTED')
            s.set_flag('EVENT_PEON_SARKOTH_ACCEPTED')
            s.set_flag('EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD', False)
            row = s.check_atlas('diagnostic_eleven_points_hardware_capacity', diagnostic, diagnostic=True)
            assert len(row['hardware_oam']) == 11
            for flag in ('CAVE_APPROACH_IMP_1_DEAD', 'CAVE_APPROACH_IMP_2_DEAD',
                         'CAVE_STRONG_IMP_DEAD', 'CAVE_IMP_DEAD'):
                s.set_flag('EVENT_PEON_' + flag)
            row = s.check_atlas('diagnostic_familiars_ready_yellow_question', diagnostic, diagnostic=True)
            assert any(p.get('identity') == 'VALLEY_MEDALLION' and p['state'] == 'ready' for p in row['points'])
            s.set_flag('EVENT_PEON_FAMILIARS_DONE')
            s.check_atlas('diagnostic_next_quest_available', diagnostic, diagnostic=True)
            s.set_flag('EVENT_PEON_MEDALLION_ACCEPTED')
            s.check_atlas('diagnostic_legacy_medallion_remains_active', diagnostic, diagnostic=True)
            s.set_flag('EVENT_PEON_SARKOTH_DONE')
            s.check_atlas('diagnostic_gornek_report_ready_on_den_page', diagnostic, 'DEN', diagnostic=True)
            s.set_flag('EVENT_PEON_SARKOTH_REPORT_DONE')
            s.check_atlas('diagnostic_report_marker_removed_after_turn_in', diagnostic, 'DEN', diagnostic=True)
            assert hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest() == sha
            report['all_checks_passed'] = True
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        if s is not None:
            s.p.stop(save=False)
        (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS atlas', sha)


if __name__ == '__main__':
    main()
