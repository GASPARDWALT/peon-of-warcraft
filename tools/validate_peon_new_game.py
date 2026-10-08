#!/usr/bin/env python3
"""Check the published title and full opening via ordinary buttons only.

No game RAM, saved state or ROM edits; the master asks for ABCDE, both other
class routes stay locked, and the fresh apprentice arrives with one real save.
"""
import hashlib
import json
import logging
import shutil
import tempfile
from pathlib import Path

from PIL import Image
from pyboy import PyBoy
from validate_peon_title_music import symbols

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/in_game'
logging.disable(logging.CRITICAL)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sym = symbols()
    observed = {'class':0, 'name':0, 'nickname':0, 'initialize':0}
    report = {'rom_sha256':hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest(),
              'method':'Production ROM, ordinary new-game buttons; no RAM edits or save states.'}
    with tempfile.TemporaryDirectory(prefix='peon-v022-opening-') as temp:
        path = Path(temp)/'opening.gbc'
        shutil.copyfile(ROOT/'pokecrystal.gbc',path)
        p = PyBoy(str(path),window='null',sound_emulated=False,log_level='ERROR')
        p.set_emulation_speed(0)
        def hook(key):
            observed[key] += 1
        for label,key in [('PeonClassSelect','class'),('PeonAskName','name'),
                          ('InitNickname','nickname'),('PeonInitializeShaman','initialize')]:
            p.hook_register(*sym[label],hook,key)
        def read(name,n=1):
            bank,address=sym[name]
            return list(p.memory[bank,address:address+n])
        def press(key,frames=90):
            p.button(key,delay=8);p.tick(frames,True)
        def capture(name):
            p.screen.image.save(OUT/(name+'.png'))
            p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(OUT/(name+'_4x.png'))

        p.tick(240,True);capture('01_title')
        expected=Image.open(ROOT/'references/generated/title_portal_gbc/title_portal_native_160x144.png').convert('RGB')
        actual=p.screen.image.convert('RGB')
        assert [tuple(c>>3 for c in v) for v in actual.getdata()]==[tuple(c>>3 for c in v) for v in expected.getdata()]
        report['native_title_rgb555_matches']=True
        press('start');capture('02_character_select')
        press('a');assert read('wMapGroup')==[0], 'Empty Continue must keep character selection open'
        press('down');press('a');capture('03_sleeping')
        seen=[];classes_checked=False;named=False
        for _ in range(100):
            if read('wMapGroup',2)==[26,14] and read('wScriptMode')==[0]:break
            if observed['class'] and not classes_checked:
                capture('05_class_shaman')
                press('down');capture('06_class_warrior');press('a')
                assert read('wPartyCount')==[0]
                press('down');capture('07_class_warlock');press('a')
                assert read('wPartyCount')==[0]
                press('up');press('up');classes_checked=True
            if observed['name'] and not named:
                p.tick(120,True)
                capture('07b_master_asks_name')
                for i in range(5):
                    press('a',30)
                    if i<4:press('right',30)
                press('start',30);press('a');named=True
            if read('wMapNumber')[0] not in seen:
                seen.append(read('wMapNumber')[0]);capture('intro_map_'+str(seen[-1]))
            press('a')
        assert read('wMapGroup',2)==[26,14] and read('wScriptMode')==[0]
        assert classes_checked and named
        assert observed=={'class':1,'name':1,'nickname':0,'initialize':1},observed
        assert 12 in seen and 13 in seen,seen
        assert read('wPlayerName',11)==[143,234,174,173,127,128,129,130,131,132,80],read('wPlayerName',11)
        assert read('wPartyCount')==[1] and read('wPartyMon1Species')==[66]
        assert read('wPartyMon1Moves',4)==[1,84,0,0]
        assert read('wPartyMon1Level')==[2]
        assert read('wPartyMon1Exp',3)==[0,0,10]
        assert read('wNumKeyItems')==[3] and read('wKeyItems',3)==[25,45,50]
        assert read('wNumItems')==[1] and read('wItems',2)==[148,1]
        assert read('wMoney',3)==[0,0,50]
        capture('08_the_den')
        press('select');capture('08b_map_locked');press('b')
        assert read('wScriptMode')==[0] and read('wMapNumber')==[14]
        report.update(new_game_reaches_den=True,other_classes_locked=True,
                      master_asks_name=True,no_pokemon_nickname_screen=True,
                      peon_prefix_and_chosen_name_persist=True,
                      starting_kit=read('wKeyItems',3),starting_moves=read('wPartyMon1Moves',4),
                      reusable_earth_totem_received_once=True,starting_money_copper=50,
                      slow_curve_level2_exp=10,map_locked_before_second_quest=True,
                      intro_maps_seen=seen,native_hooks=observed,all_checks_passed=True)
        p.stop(save=False)
    (OUT/'validation_results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
