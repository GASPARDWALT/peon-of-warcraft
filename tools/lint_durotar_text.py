#!/usr/bin/env python3
"""Catch overflow with a maximal ten-character peon name, before building."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
NAMES=['PeonOpening','GrommashHold','TheDen','ValleyOfTrials','DurotarRoad','SenjinVillage','RazorHill','OrgrimmarGate','BurningBladeCavern','PeonTrollHut','PeonOrcHut']
count=0
for name in NAMES:
    p=ROOT/'maps'/(name+'.asm')
    for n,line in enumerate(p.read_text().splitlines(),1):
        m=re.match(r'\s*(text|line|cont|para) "(.*)"$',line)
        if m:
            length=len(m[2].replace('<PLAYER>','Péon ABCDE'))
            assert length<=18,(str(p),n,length,m[2])
            count+=1
print(f'Passed: {count} dialogue rows fit 18 columns with the longest player name')
