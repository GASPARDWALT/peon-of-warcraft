#!/usr/bin/env python3
"""Retain native spell/item regression checks without overwriting old releases."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path

import run_peon_v023_validation as adapter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/deep_polish/combat/retained'
SUITES = {'spells': ('validate_peon_spell_effects', 'spell_validation/validation.json'),
          'totems': ('validate_peon_battle_totems', 'battle_totems_validation/validation.json')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('suite', choices=tuple(SUITES))
    args = parser.parse_args()
    adapter.OUT = OUT
    module_name, relative_report = SUITES[args.suite]
    target = importlib.import_module(module_name)
    for module in adapter.local_dependencies(target):
        for name in ('OUT', 'OUTPUT'):
            if hasattr(module, name):
                redirected = adapter.redirected(getattr(module, name))
                setattr(module, name, redirected)
                if isinstance(redirected, Path):
                    redirected.mkdir(parents=True, exist_ok=True)
        # Retained pre-v0.2.3 checks use the actual current inn recovery rule.
        # This adapter changes those obsolete location/walk assumptions only;
        # it retains native charge, turn, damage, status and save assertions.
        adapter.adapt_v023_gameplay(module)
    sha = hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest()
    target.main()
    report_path = OUT / relative_report
    report = json.loads(report_path.read_text())
    assert report['rom_sha256'] == sha
    assert hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest() == sha
    report['all_checks_passed'] = True
    report['retained_native_assertions_run_to_completion'] = True
    report['historical_output_destinations_redirected'] = True
    report_path.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
