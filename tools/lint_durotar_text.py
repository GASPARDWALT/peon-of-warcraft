#!/usr/bin/env python3
"""Catch overflow with a maximal ten-character peon name, before building."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
NAMES=['PeonOpening','GrommashHold','TheDen','ValleyOfTrials','DurotarRoad','SenjinVillage','RazorHill','OrgrimmarGate','BurningBladeCavern','PeonTrollHut','PeonOrcHut','PeonOrcInn','PeonTrollInn']
PATHS=[ROOT/'maps'/(name+'.asm') for name in NAMES]
PATHS += [ROOT/p for p in ('engine/events/peon_quest_xp.asm',
    'engine/menus/peon_hearthstone.asm','engine/menus/peon_shaman_trainer.asm',
    'engine/battle/peon_spell_effects.asm','engine/battle/peon_encounter_intro.asm',
    'engine/events/poisonstep.asm')]
count=0
for p in PATHS:
    for n,line in enumerate(p.read_text().splitlines(),1):
        m=re.match(r'\s*(text|line|cont|para) "(.*)"$',line)
        if m:
            length=len(m[2].replace('<PLAYER>','Péon ABCDE'))
            assert length<=18,(str(p),n,length,m[2])
            count+=1
print(f'Passed: {count} dialogue rows fit 18 columns with the longest player name')
