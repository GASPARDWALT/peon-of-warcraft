#!/usr/bin/env python3
"""Exact RGB555 environment palettes, independent of historical generators."""
from pathlib import Path
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/environment_v025'
BASE = '6d2a0be'
REGIONS = ('TheDen', 'ValleyOfTrials', 'DurotarRoad', 'SenjinVillage',
           'RazorHill', 'OrgrimmarGate', 'BurningBladeCavern')
ROOMS = {'PeonTrollHut': 'SenjinVillage', 'PeonTrollInn': 'SenjinVillage',
         'PeonOrcHut': 'RazorHill', 'PeonOrcInn': 'RazorHill'}


def expand(value):
    return (value << 3) | (value >> 2)


def original_palettes(path):
    text = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT).decode()
    result = []
    for line in text.splitlines():
        if 'RGB' not in line:
            continue
        values = [int(v) for v in re.findall(r'\d+', line.split('RGB', 1)[1].split(';')[0])]
        assert len(values) == 12 and all(0 <= v < 32 for v in values)
        result.append([tuple(expand(x) for x in values[i:i+3]) for i in range(0, 12, 3)])
    return result


def updated(palettes, cave=False):
    palettes = [[tuple(c) for c in p] for p in palettes]
    palettes[5][1] = tuple(map(expand, (31, 27, 19)))  # Visible ivory tusks and leather highlights.
    palettes[6][1] = tuple(map(expand, (26, 8, 4)))  # Horde red hide.
    palettes[6][2] = tuple(map(expand, (14, 4, 3)))
    if cave:
        # Amber trails/fire guide the player against the unchanged purple rock.
        palettes[4][1:] = [tuple(map(expand, c)) for c in ((31, 27, 18), (28, 20, 12), (12, 8, 4))]
    return palettes


BG = updated(original_palettes('gfx/tilesets/peon_bg.pal'))
_regions = original_palettes('gfx/tilesets/peon_regions.pal')
assert len(_regions) == 56
REGION_BGS = {name: updated(_regions[i*8:(i+1)*8], name == 'BurningBladeCavern')
              for i, name in enumerate(REGIONS)}


def palettes_for(name):
    return REGION_BGS.get(ROOMS.get(name, name), BG)


def palfile(palettes):
    return ''.join('\tRGB ' + ', '.join(f'{component >> 3:02d}' for colour in palette
                                     for component in colour) + '\n' for palette in palettes)


def main():
    (ROOT / 'gfx/tilesets/peon_bg.pal').write_text(palfile(BG))
    (ROOT / 'gfx/tilesets/peon_regions.pal').write_text(''.join(palfile(REGION_BGS[name]) for name in REGIONS))
    (ROOT / 'gfx/tilesets/peon_interiors.pal').write_text(''.join(palfile(REGION_BGS[name])
                                                             for name in ('SenjinVillage', 'RazorHill')))
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'source': 'Original RGB555 palette refinements based on v0.2.4.',
              'palettes_per_map': 8, 'colours_per_tile': 4, 'font_palette_7_preserved': True,
              'base': BG, 'regions': REGION_BGS, 'room_origins': ROOMS,
              'cave_path_and_fire': 'Amber highlights against purple stone; collision unchanged.'}
    (OUT / 'palettes.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Compiled exact RGB555 environment palettes; font and object palettes unchanged.')


if __name__ == '__main__':
    main()
