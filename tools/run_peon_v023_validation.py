#!/usr/bin/env python3
"""Run retained native checks into v0.2.3 without altering published assets.

Each validator runs in a separate Python process. Its local tools dependencies
are discovered recursively, and only OUT/OUTPUT destinations are redirected.
ROOT, SOURCE and native input paths retain their original meanings. The one
function-local OUT in the beast validator is adapted in memory, without editing
that validator. No asset generator, ROM build or hardware flash is performed.
"""
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
from types import ModuleType
import wave

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
OUT = ROOT / 'references/generated/durotar_v023'
OLD = ROOT / 'references/generated/durotar_v022'

# key: module, callable, expected report(s). Build evidence remains root-owned.
JOBS = {
    'new_game': ('validate_peon_new_game', 'main', ['in_game/validation_results.json']),
    'sprite': ('validate_peon_sprite', 'main', ['sprite_validation/validation_results.json']),
    'upgrade': ('validate_peon_v023_upgrade', 'main', ['save_upgrade/validation.json', 'save_upgrade_results.json']),
    'villages': ('validate_peon_villages', 'main', ['village_validation/validation_results.json']),
    'portraits': ('validate_peon_speaker_portraits', 'main', ['speaker_portraits/emulator_validation.json']),
    'beast_attacks': ('build_peon_beast_attacks', 'validate_attacks', ['combat_assets/in_game/validation.json']),
    'title_music': ('validate_peon_title_music', 'main', ['title_music/validation.json']),
    'sfx': ('validate_peon_sfx', 'main', ['sound_effects/validation.json']),
    'lazy_quest': ('validate_peon_lazy_quest', 'main', ['lazy_quest_validation/validation.json']),
    'quest_markers': ('validate_peon_quest_markers', 'main', ['quest_markers/validation.json']),
    'atlas': ('validate_peon_atlas_quests', 'main', ['quest_markers/validation_results.json']),
    'menu': ('validate_peon_menu_skin', 'main', ['menu_skin/validation.json']),
    'enemy_roster': ('build_peon_enemy_roster', 'validate', ['enemies/compiled_validation.json']),
    'enemy_profiles': ('validate_peon_enemy_profiles', 'main', ['enemy_profiles/validation.json']),
    'inns': ('validate_peon_inns', 'main', ['inn_validation/validation_results.json']),
    'trainer': ('validate_peon_trainer', 'main', ['trainer_validation/validation.json']),
    'spell_effects': ('validate_peon_spell_effects', 'main', ['spell_validation/validation.json']),
    'quest_xp': ('validate_peon_quest_xp', 'main', ['quest_xp_validation/validation.json']),
    'quests': ('validate_durotar_v022_quests', 'main', ['quest_validation/validation_results.json']),
    'quest_faults': ('validate_durotar_v022_quest_faults', 'main', ['quest_fault_validation/validation_results.json']),
    'ambient_music': ('validate_peon_ambient_music', 'main', ['ambient_music/validation.json']),
    'battle_totems': ('validate_peon_battle_totems', 'main', ['battle_totems_validation/validation.json']),
    'item_icons': ('validate_peon_item_icons', 'main', ['item_icon_validation/validation.json']),
    'spell_animations': ('validate_peon_spell_animations', 'main', ['spell_animations/validation.json', 'spell_animations/native_rom_validation.json']),
    'audio_quality': (None, 'audio_quality', ['ambient_music/audio_quality.json']),
    'player_combat': ('validate_peon_player_combat', 'main', ['player_combat/validation.json']),
    'combat_balance': ('validate_peon_balance', 'main', ['combat_balance/validation.json']),
    'normal_pack': ('validate_peon_v023_normal_pack', 'main', ['combat_balance/normal_pack_validation.json']),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def published_snapshot():
    folders = [ROOT / 'references/generated' / version
               for version in ('durotar_v02', 'durotar_v021', 'durotar_v022', 'title_portal_gbc')]
    folders += [ROOT / 'releases' / version for version in ('v0.1.1', 'v0.2', 'v0.2.1', 'v0.2.2')]
    return {str(p.relative_to(ROOT)): sha(p) for folder in folders
            for p in sorted(folder.rglob('*')) if p.is_file()}


def redirected(path):
    if not isinstance(path, Path):
        return path
    for version in ('durotar_v022', 'durotar_v021'):
        source = ROOT / 'references/generated' / version
        try:
            return OUT / path.relative_to(source)
        except ValueError:
            pass
    return path


def local_dependencies(module):
    """Find modules behind both module imports and imported helper classes."""
    found, pending = {}, [module]
    while pending:
        item = pending.pop()
        if item.__name__ in found:
            continue
        filename = getattr(item, '__file__', None)
        if filename is None or not Path(filename).resolve().is_relative_to(TOOLS):
            continue
        found[item.__name__] = item
        for value in list(vars(item).values()):
            if isinstance(value, ModuleType):
                pending.append(value)
            elif inspect.isclass(value) or inspect.isfunction(value):
                owner = sys.modules.get(getattr(value, '__module__', ''))
                if owner is not None:
                    pending.append(owner)
    return list(found.values())


class LocalOutputRedirect(ast.NodeTransformer):
    def visit_Assign(self, node):
        if any(isinstance(target, ast.Name) and target.id in ('OUT', 'OUTPUT') for target in node.targets):
            # Assignment-local destinations only; preserve other source strings.
            class ReplaceVersion(ast.NodeTransformer):
                def visit_Constant(self, value):
                    if isinstance(value.value, str):
                        value.value = value.value.replace('durotar_v022', 'durotar_v023').replace('durotar_v021', 'durotar_v023')
                    return value
            node.value = ReplaceVersion().visit(node.value)
        return self.generic_visit(node)


def adapt_local_outputs(module):
    for name, function in list(vars(module).items()):
        if not inspect.isfunction(function) or function.__module__ != module.__name__:
            continue
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
        assignments = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id in ('OUT', 'OUTPUT') for t in n.targets)]
        if not assignments:
            continue
        tree = ast.fix_missing_locations(LocalOutputRedirect().visit(tree))
        exec(compile(tree, str(module.__file__), 'exec'), module.__dict__)


def adapt_v023_gameplay(module):
    """Update two obsolete harness assumptions while retaining their checks.

    Defeat now reaches the saved home inn (or the Den inn by default) at one
    HP, without granting/binding a Hearthstone or restoring charges. Normal
    inn walking uses short released taps rather than a held-key polling loop.
    All adaptations exist only in this worker's imported Python objects.
    """
    if module.__name__ == 'validate_durotar_v022_quests':
        cls = module.QuestSession
        def home_flags(self):
            return {name: self.event(name) for name in
                    ('EVENT_PEON_HEARTH_GRANTED', 'EVENT_PEON_HOME_DEN',
                     'EVENT_PEON_HOME_SENJIN', 'EVENT_PEON_HOME_RAZOR')}
        def assert_recovery(self, before):
            after = home_flags(self)
            assert before == after, ('Defeat granted or changed home binding', before, after)
            assert sum(after[name] for name in after if name != 'EVENT_PEON_HEARTH_GRANTED') <= 1
            owner = 17 if after['EVENT_PEON_HOME_SENJIN'] else 18 if after['EVENT_PEON_HOME_RAZOR'] else 14
            inn = 24 if owner == 17 else 23
            warp = {14: 2, 17: 3, 18: 4}[owner]
            assert self.read('wMapGroup', 2) == [26, inn] and self.position() == (5, 6), (
                'Defeat did not reach exact native inn entrance', owner, self.map(), self.position())
            assert self.read('wBackupWarpNumber', 3) == [warp, 26, owner], 'Recovery inn exit owner changed'
            assert self.read('wPartyMon1HP', 2) == [0, 1] and self.read('wPartyMon1Status') == [0]
            self.last_recovery_validation = {
                'native_inn_map': inn, 'arrival_xy': [5, 6], 'saved_home_or_default_owner': owner,
                'backup_warp_owner_correct': True, 'one_hp': True, 'status_cleared': True,
                'home_flags_before': before, 'home_flags_after': after,
                'defeat_did_not_grant_or_rebind_hearthstone': True,
            }
        cls._v023_home_flags, cls._v023_assert_recovery = home_flags, assert_recovery
        tree = ast.parse(textwrap.dedent(inspect.getsource(cls.fight)))
        class FightAdapter(ast.NodeTransformer):
            replacements = 0
            def visit_Assert(self, node):
                if ast.unparse(node.test) == "self.map() == 14 and self.read('wPartyMon1HP', 2) == [0, 1]":
                    self.replacements += 1
                    return ast.parse('self._v023_assert_recovery(recovery_home_before)').body[0]
                return self.generic_visit(node)
            def visit_Return(self, node):
                if isinstance(node.value, ast.Dict):
                    node.value.keys.append(ast.Constant('native_inn_recovery'))
                    node.value.values.append(ast.parse('self.last_recovery_validation if outcome == 1 else None', mode='eval').body)
                return self.generic_visit(node)
        transformer = FightAdapter(); tree = transformer.visit(tree)
        assert transformer.replacements == 1, 'Original defeat assertion changed; review adapter'
        tree.body[0].body.insert(0, ast.parse('recovery_home_before = self._v023_home_flags()').body[0])
        namespace = dict(module.__dict__)
        exec(compile(ast.fix_missing_locations(tree), str(module.__file__), 'exec'), namespace)
        cls.fight = namespace['fight']
        original_go_den = cls.go_den
        def go_den(self):
            if self.map() in (23, 24):
                owner = self.read('wBackupMapNumber')[0]
                assert owner in (14, 17, 18), ('Inn exit must have a valid saved owner', owner)
                self.navigate((5, 7), expected_map=owner)
            if self.map() == 19:
                self.navigate((12, 16), expected_map=18)
            if self.map() == 18:
                self.navigate((12, 16), expected_map=16)
            if self.map() == 17:
                self.navigate((10, 4), expected_map=16)
            return original_go_den(self)
        cls.go_den = go_den
    elif module.__name__ == 'validate_peon_inns':
        tree = ast.parse(textwrap.dedent(inspect.getsource(module.main)))
        short_walk = ast.parse('''
def walk(key):
    before=position();oldmap=mapnum()
    for _ in range(8):
        p.button(key,delay=4);p.tick(40,True)
        if position()!=before:break
    assert mapnum()==oldmap,(key,'unexpected warp during one-tile tap',oldmap,mapnum())
    assert sum(abs(a-b) for a,b in zip(before,position()))==1,(key,before,position())
''').body[0]
        class WalkAdapter(ast.NodeTransformer):
            replacements = 0
            def visit_FunctionDef(self, node):
                if node.name == 'walk':
                    self.replacements += 1
                    return short_walk
                return self.generic_visit(node)
        transformer = WalkAdapter(); tree = transformer.visit(tree)
        assert transformer.replacements == 1, 'Original inn walk helper changed; review adapter'
        exec(compile(ast.fix_missing_locations(tree), str(module.__file__), 'exec'), module.__dict__)


def stage_static_inputs():
    """These validators also read manifests through OUT; never copy old reports."""
    inputs = {
        'ambient_music': ['score_manifest.json'],
        'sound_effects': ['design.json'],
        'quest_markers': ['manifest.json'],
        'enemies': ['manifest.json'],
    }
    for folder, files in inputs.items():
        for filename in files:
            source, destination = OLD / folder / filename, OUT / folder / filename
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
    # Enemy validation reads its retained pixel-perfect public pose PNGs via OUT.
    for source in (OLD / 'enemies').glob('*/battle_*.png'):
        destination = OUT / source.relative_to(OLD)
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)


def audio_quality():
    """Analyze fresh native APU previews; this is not a listening verdict."""
    import numpy as np
    rom_sha = sha(ROOT / 'pokecrystal.gbc')
    music = json.loads((OUT / 'ambient_music/validation.json').read_text())
    effects = json.loads((OUT / 'sound_effects/validation.json').read_text())
    assert music['rom_sha256'] == effects['rom_sha256'] == rom_sha
    assert music['all_checks_passed'] and effects['all_checks_passed']
    report = {'rom_sha256': rom_sha, 'method': 'Objective analysis of fresh native APU preview WAVs; no subjective listening verdict.',
              'tracks': {}, 'sound_effects': {}, 'sound_effects_validation_rom_sha256': rom_sha}
    def analyze(path):
        with wave.open(str(path), 'rb') as f:
            assert f.getsampwidth() == 2 and f.getnchannels() == 2
            rate = f.getframerate()
            samples = np.frombuffer(f.readframes(f.getnframes()), dtype='<i2').reshape(-1, 2).astype('int32')
        assert len(samples) and np.any(samples), (path, 'silent preview')
        peak = np.max(np.abs(samples), axis=0)
        clipped = int(np.count_nonzero((samples <= -32768) | (samples >= 32767)))
        assert clipped == 0, (path, 'digital clipping')
        rms = np.sqrt(np.mean(samples.astype('float64') ** 2, axis=0))
        assert all(n > 100 for n in rms), (path, 'near-silent channel')
        return {'duration_seconds': round(len(samples) / rate, 6),
                'peak_pcm_per_channel': peak.tolist(), 'rms_pcm_per_channel': np.round(rms, 2).tolist(),
                'mean_dc_pcm_per_channel': np.round(samples.mean(axis=0), 4).tolist(),
                'digital_clipped_samples': clipped, 'wav_sha256': sha(path)}
    for name, track in music['tracks'].items():
        report['tracks'][name] = analyze(OUT / 'ambient_music' / track['wav'])
    assert len(report['tracks']) == 7
    for path in sorted((OUT / 'sound_effects').glob('*.wav')):
        report['sound_effects'][path.name] = analyze(path)
    assert len(report['sound_effects']) >= 9
    report['all_checks_passed'] = True
    (OUT / 'ambient_music/audio_quality.json').write_text(json.dumps(report, indent=2) + '\n')


def worker(key):
    stage_static_inputs()
    module_name, callable_name, reports = JOBS[key]
    if module_name is None:
        audio_quality()
    else:
        module = importlib.import_module(module_name)
        for dependency in local_dependencies(module):
            for name in ('OUT', 'OUTPUT'):
                if hasattr(dependency, name):
                    value = redirected(getattr(dependency, name))
                    setattr(dependency, name, value)
                    if isinstance(value, Path):
                        value.mkdir(parents=True, exist_ok=True)
            adapt_local_outputs(dependency)
            adapt_v023_gameplay(dependency)
        original_argv = sys.argv
        try:
            sys.argv = [str(module.__file__)]
            getattr(module, callable_name)()
        finally:
            sys.argv = original_argv
    current = sha(ROOT / 'pokecrystal.gbc')
    for filename in reports:
        data = json.loads((OUT / filename).read_text())
        assert data['rom_sha256'] == current, (key, filename, 'stale ROM report')
        assert not data.get('failure') and not data.get('error'), (key, filename)
        if 'all_checks_passed' in data:
            assert data['all_checks_passed'] is True, (key, filename)


def chosen_keys(values):
    return {part for value in (values or []) for part in value.split(',') if part}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', action='append', help='Comma-separated job names; repeatable.')
    parser.add_argument('--skip', action='append', help='Comma-separated jobs to omit; repeatable.')
    parser.add_argument('--jobs', type=int, default=1, help='Independent validator processes (default 1).')
    parser.add_argument('--list', action='store_true', help='Print jobs/reports without running validators.')
    parser.add_argument('--worker', choices=JOBS, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.list:
        print(json.dumps({key: value[2] for key, value in JOBS.items()}, indent=2))
        return
    if args.worker:
        worker(args.worker)
        return
    only, skip = chosen_keys(args.only), chosen_keys(args.skip)
    assert (only | skip) <= set(JOBS), ('Unknown jobs', sorted((only | skip) - set(JOBS)))
    assert args.jobs > 0
    selected = [key for key in JOBS if (not only or key in only) and key not in skip]
    assert selected, 'No validation jobs selected'
    before, rom_sha = published_snapshot(), sha(ROOT / 'pokecrystal.gbc')
    OUT.mkdir(parents=True, exist_ok=True)
    stage_static_inputs()
    log_folder = OUT / 'validation_logs'; log_folder.mkdir(exist_ok=True)
    results = {}
    def run(key):
        with (log_folder / (key + '.log')).open('w') as log:
            proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker', key],
                                  cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=os.environ.copy())
        return key, proc.returncode
    # WAV analysis requires fresh music/effect captures. Other jobs share only
    # immutable native inputs; each process owns its own report destinations.
    ordinary = [key for key in selected if key != 'audio_quality']
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        for future in as_completed([executor.submit(run, key) for key in ordinary]):
            key, code = future.result(); results[key] = code
            print(key + ': ' + ('PASS' if code == 0 else 'FAIL; see ' + str(log_folder / (key + '.log'))), flush=True)
    if 'audio_quality' in selected:
        key, code = run('audio_quality'); results[key] = code
        print(key + ': ' + ('PASS' if code == 0 else 'FAIL'), flush=True)
    assert published_snapshot() == before, 'A validator modified published art or release artifacts'
    assert sha(ROOT / 'pokecrystal.gbc') == rom_sha, 'ROM changed during the validation batch'
    assert all(code == 0 for code in results.values()), ('Validation failures', results)
    print(json.dumps({'validated_rom_sha256': rom_sha, 'selected_jobs': selected,
                      'published_artifacts_preserved': True, 'all_selected_checks_passed': True}, indent=2))


if __name__ == '__main__':
    main()
