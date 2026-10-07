#!/usr/bin/env python3
"""Check the integrated atlas OBJ overlay with an isolated PyBoy ROM.

The opening reaches The Den through ordinary buttons. Availability, completion
and fog branches are then checked with explicitly labelled diagnostic event-flag
injection; this is not a substitute for the normal quest walkthrough tests.
No personal save or original ROM is written.
"""
import hashlib
import io
import json
import logging
import shutil
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from pyboy import PyBoy

logging.disable(logging.CRITICAL)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v021/quest_markers'


def symbols():
    result={}
    for line in (ROOT/'pokecrystal.sym').read_text().splitlines():
        parts=line.split()
        if len(parts)==2 and ':' in parts[0]:
            try:result[parts[1]]=tuple(int(c,16) for c in parts[0].split(':'))
            except ValueError:pass
    return result


def flag_ids():
    result={}; index=0
    for line in (ROOT/'constants/event_flags.asm').read_text().splitlines():
        parts=line.split(';')[0].split()
        if not parts:continue
        if parts[0]=='const_def':index=int(parts[1]) if len(parts)>1 else 0
        elif parts[0]=='const_next':index=int(parts[1])
        elif parts[0]=='const_skip':index+=int(parts[1]) if len(parts)>1 else 1
        elif parts[0]=='const':result[parts[1]]=index;index+=1
    return result


def main():
    sym=symbols();flags=flag_ids()
    assert 'PeonDrawAtlasQuests' in sym, 'Include the helper and rebuild first'
    manifest=json.loads((OUT/'manifest.json').read_text())
    results={'rom_sha256':hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest(),
             'emulator':'PyBoy 2.7.0',
             'test_method':'Ordinary new-game buttons, then diagnostic quest/discovery flag injection',
             'cases':[]}
    with tempfile.TemporaryDirectory(prefix='peon-atlas-') as directory:
        rom=Path(directory)/'test.gbc'
        shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
        p=PyBoy(str(rom),window='null',sound_emulated=False,log_level='ERROR')
        p.set_emulation_speed(0)
        def read(name,length=1):
            bank,address=sym[name]
            if address>=0xff00:
                return list(p.memory[address:address+length])
            return list(p.memory[bank,address:address+length])
        def press(key,frames=90):
            p.button(key,delay=8);p.tick(frames,True)
        def set_flag(name,value=True):
            index=flags[name];bank,address=sym['wEventFlags'];address+=index//8
            old=p.memory[bank,address]
            p.memory[bank,address]=(old|(1<<(index%8))) if value else (old&~(1<<(index%8)))
        named={'entered':False,'filled':False}
        p.hook_register(*sym['PeonAskName'],lambda s:s.__setitem__('entered',True),named)
        p.tick(240,True);press('start');press('down');press('a')
        for _ in range(120):
            if read('wMapGroup',2)==[26,14] and read('wScriptMode')[0]==0:break
            if named['entered'] and not named['filled']:
                p.tick(120,True)
                for i in range(5):
                    press('a',30)
                    if i<4:press('right',30)
                press('start',30);press('a');named['filled']=True
            press('a')
        assert read('wMapGroup',2)==[26,14] and read('wScriptMode')[0]==0
        results['ordinary_new_game_reached_den']=True
        p.hook_deregister(*sym['PeonAskName'])
        baseline=io.BytesIO();p.save_state(baseline)
        snapshots=[]
        def registers():
            return {name:getattr(p.register_file,name) for name in ('A','F','B','C','D','E','HL','SP')}
        def entering(_):
            snapshots.append({'entry':registers(),'vbk':p.memory[0xff4f]&1,
                              'oam_update':read('hOAMUpdate')[0],
                              'flags_before':read('wEventFlags',256)})
        def returning(_):
            state=snapshots[-1]
            assert state['entry']==registers(), ('register corruption',state['entry'],registers())
            assert state['vbk']==(p.memory[0xff4f]&1), 'VBK was not restored'
            assert state['oam_update']==read('hOAMUpdate')[0], 'OAM guard was not restored'
            assert state['flags_before']==read('wEventFlags',256), 'Helper changed quest flags'
            state['verified']=True
        p.hook_register(*sym['PeonDrawAtlasQuests'],entering,None)
        done_bank,done_address=sym['PeonDrawAtlasQuests.done']
        # .done has four one-byte POPs followed by RET. Check just before RET.
        p.hook_register(done_bank,done_address+4,returning,None)
        cases=[
            ('den_offer','DEN',[],[],0,False),
            ('den_active','DEN',['EVENT_PEON_LAZY_ACCEPTED'],[],0,False),
            ('den_ready','DEN',['EVENT_PEON_LAZY_ACCEPTED','EVENT_PEON_LAZY_AWAKE'],[],1,False),
            ('den_done','DEN',['EVENT_PEON_LAZY_DONE'],[],None,False),
            ('valley_fog','VALLEY',[],['EVENT_PEON_DISCOVERED_VALLEY'],None,True),
            ('valley_offer','VALLEY',['EVENT_PEON_DISCOVERED_VALLEY'],[],0,False),
            ('valley_active','VALLEY',['EVENT_PEON_DISCOVERED_VALLEY','EVENT_PEON_CACTUS_ACCEPTED','EVENT_PEON_CACTUS_1'],[],0,False),
            ('valley_ready','VALLEY',['EVENT_PEON_DISCOVERED_VALLEY','EVENT_PEON_CACTUS_ACCEPTED','EVENT_PEON_CACTUS_1','EVENT_PEON_CACTUS_2','EVENT_PEON_CACTUS_3'],[],1,False),
            ('valley_done','VALLEY',['EVENT_PEON_DISCOVERED_VALLEY','EVENT_PEON_CACTUS_DONE'],[],None,False),
        ]
        for label,region,enabled,disabled,tile,fog in cases:
            baseline.seek(0);p.load_state(baseline)
            set_flag('EVENT_PEON_MAP_RECEIVED')
            for flag in enabled:set_flag(flag)
            for flag in disabled:set_flag(flag,False)
            first_snapshot=len(snapshots)
            press('select',120)
            if region=='VALLEY':press('right',120)
            p.tick(12,True)
            assert len(snapshots)>first_snapshot and all(s['verified'] for s in snapshots[first_snapshot:])
            expected_id='fog' if fog else region.lower()
            binary=(ROOT/'gfx/peon_maps'/(expected_id+'.bin')).read_bytes()
            assert bytes(p.memory[0,0x9000:0x9800])==binary[:2048], 'BG tile bank 0 lower half corrupted'
            assert bytes(p.memory[0,0x8800:0x9000])==binary[2048:4096], 'BG tile bank 0 upper half corrupted'
            assert bytes(p.memory[1,0x9000:0x9680])==binary[4096:5760], 'BG tile bank 1 corrupted'
            entries=[list(p.memory[0xfe00+i:0xfe04+i]) for i in range(0,160,4)]
            visible=[entry for entry in entries if 0<entry[0]<160 and 0<entry[1]<168]
            if tile is None:
                assert not visible, (label,visible)
                expected=Image.open(ROOT/'references/generated/durotar_v021/zone_maps'/(expected_id+'.png')).convert('RGB')
            else:
                oy,ox=manifest['points'][region]['oam_yx']
                assert visible==[[oy,ox,tile,4]], (label,visible)
                assert p.memory[0xff40]&2, 'OBJ rendering is disabled'
                assert not (p.memory[0xff40]&4), 'Glyph requires 8-pixel OBJ mode'
                assert bytes(p.memory[0,0x8000:0x8020])==(ROOT/'gfx/pack/peon_quest_poi.2bpp').read_bytes()
                suffix='quest_available' if tile==0 else 'quest_complete'
                expected=Image.open(OUT/(region.lower()+'_'+suffix+'.png')).convert('RGB')
            actual=p.screen.image.convert('RGB')
            same=np.array_equal(np.asarray(actual)>>3,np.asarray(expected)>>3)
            actual.save(OUT/(label+'_in_rom.png'))
            actual.resize((640,576),Image.Resampling.NEAREST).save(OUT/(label+'_in_rom_4x.png'))
            assert same, (label,'Rendered RGB555 pixels differ from the atlas+glyph reconstruction')
            press('b',120)
            assert read('wMapGroup',2)==[26,14] and read('wScriptMode')[0]==0
            results['cases'].append({'name':label,'diagnostic_flag_injection':True,
                                     'visible_oam':visible,'rgb555_matches':same,
                                     'background_vram_unchanged':True,
                                     'registers_vbk_oam_guard_preserved':True,
                                     'closed_to_world':True})
        p.hook_deregister(*sym['PeonDrawAtlasQuests'])
        p.hook_deregister(done_bank,done_address+4)
        p.stop(save=False)
    results['limitations']=['Availability/fog branches use diagnostic flag injection',
                            'Chromatic hardware is untested',
                            'Only the current two prototype atlas quests have POIs']
    (OUT/'validation_results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
