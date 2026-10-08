#!/usr/bin/env python3
"""Walk all nine authored doors and cold-restart each native room type.

Uses ordinary buttons and read-only memory/hook observers. The .ram battery
is isolated in a temporary directory; no savestate or gameplay RAM writes.
"""
import argparse
from pathlib import Path
import hashlib
import json
import logging
import re
import shutil
import tempfile

from PIL import Image
import validate_peon_villages as village

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'references/generated/deep_polish/world_runtime'


class WorldSession(village.Session):
    def snapshot(self):
        fields=[('wPlayerName',11),('wMapGroup',2),('wXCoord',1),('wYCoord',1),
                ('wBackupWarpNumber',1),('wBackupMapGroup',1),('wBackupMapNumber',1),
                ('wPartyMon1',48),('wPartyMon1Nickname',11),('wMoney',3),
                ('wEventFlags',256),('wNumItems',1),('wItems',self.read('wNumItems')[0]*2)]
        return {name:self.read(name,size) for name,size in fields}

    def terrain_upload(self):
        data=(ROOT/'gfx/tilesets/peon.2bpp').read_bytes()
        assert len(data)==192*16
        assert bytes(self.p.memory[0,0x9000:0x9600])==data[:96*16]
        assert bytes(self.p.memory[1,0x9000:0x9600])==data[96*16:]
        return {'native_tiles_matching_vram':192,'includes_native_deadthorn_tiles':True}

    def authored_blocks(self):
        name,width,height=village.MAPS[self.map()]
        bank,address=self.sym['wOverworldMapBlocks']
        actual=[]
        for y in range(height):
            start=address+(y+3)*(width+6)+3
            actual.extend(self.p.memory[bank,start:start+width])
        expected=(ROOT/f'maps/{name}.blk').read_bytes()
        assert bytes(actual)==expected,(name,'stale cached terrain survived')
        return {'current_authored_block_bytes_match':True,'count':len(expected)}

    def capture(self,label):
        self.p.screen.image.save(OUT/(label+'.png'))
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(OUT/(label+'_4x.png'))
        print(label,self.map(),self.position(),flush=True)

    def restart_room(self,label):
        origin=self.map();before=self.snapshot()
        observed={'saved':False,'menu_exited':False}
        self.p.hook_register(*self.sym['_SaveGameData'],lambda _:observed.__setitem__('saved',True),None)
        self.p.hook_register(*self.sym['StartMenu.Exit'],lambda _:observed.__setitem__('menu_exited',True),None)
        self.press('start')
        items=self.read('wMenuItemsList',self.read('wMenuItemsList')[0]+1)[1:]
        index=items.index(4)+1 # Stable STARTMENUITEM_SAVE, independent of menu text.
        for _ in range(12):
            current=self.read('wMenuCursorPosition')[0]
            if current==index: break
            self.press('up' if current>index else 'down',30)
        assert self.read('wMenuCursorPosition')==[index]
        self.press('a')
        for _ in range(16):
            if observed['saved'] and observed['menu_exited']: break
            self.press('a',180)
        assert all(observed.values()),(label,'save hooks did not complete',observed)
        self.p.tick(90,True);self.capture(label+'_saved')
        self.p.stop(save=True)
        battery=Path(str(self.rom)+'.ram')
        assert battery.stat().st_size==32768
        self.open();self.p.tick(240,True);self.press('start')
        for _ in range(16):
            if self.map()==origin and self.read('wScriptMode')==[0]: break
            self.press('a',180)
        self.p.tick(120,True)
        assert self.map()==origin and self.read('wScriptMode')==[0]
        after=self.snapshot()
        assert before==after,(label,'cold battery progress changed',
                              [name for name in before if before[name]!=after[name]])
        self.capture(label+'_continued')
        return {'room_id':origin,'native_battery_bytes':32768,'native_save_commit_observed':True,
                'name_location_home_kit_health_charges_money_event_flags_preserved':True,
                'before':before,'after':after,'terrain':self.authored_blocks(),
                'vram':self.terrain_upload()}


def visit_doors(s,name,report,visited):
    doors=[(int(m[1]),int(m[2]),m[3]) for m in re.finditer(
        r'^\s*warp_event\s+(\d+),\s*(\d+),\s*(PEON_(?:ORC|TROLL)_(?:INN|HUT)),',
        (ROOT/f'maps/{name}.asm').read_text(),re.M)]
    types={'PEON_TROLL_HUT':21,'PEON_ORC_HUT':22,'PEON_ORC_INN':23,'PEON_TROLL_INN':24}
    for i,(x,y,target) in enumerate(doors):
        origin=s.map();dest=types[target]
        s.navigate((x,y),expected_map=dest)
        s.capture(f'{name}_door_{i+1}_inside')
        entry={'origin_map':origin,'door':[x,y],'room_id':dest,
               'terrain':s.authored_blocks(),'vram':s.terrain_upload()}
        if dest not in visited:
            s.walk('up')
            report['room_cold_restarts'].append(s.restart_room(f'room_{dest}'))
            visited.add(dest)
        s.navigate((5,7),expected_map=origin)
        assert s.position()==(x,y),(name,'incorrect origin door return',(x,y),s.position())
        assert s.read('wScriptMode')==[0]
        entry['returns_to_exact_origin_door_after_restart']=True
        report['door_routes'].append(entry)
        s.capture(f'{name}_door_{i+1}_returned')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--expected-sha')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);logging.disable(logging.CRITICAL)
    village.OUT=OUT
    sha=hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest()
    assert not args.expected_sha or args.expected_sha==sha
    report={'rom_sha256':sha,'passed':False,'normal_buttons_only':True,
            'ram_edits':False,'emulator_states_loaded':False,'read_only_observers':True,
            'door_routes':[],'room_cold_restarts':[],'outdoor_regions':[],
            'scope':'Nine doors, four distinct room IDs, current terrain uploads, save/cold restart; physical Chromatic untested.'}
    s=None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-world-polish-') as directory:
            rom=Path(directory)/'test.gbc';shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
            s=WorldSession(rom,village.load_symbols())
            s.p.tick(1800,False);s.press('start');s.press('down');s.press('a')
            for _ in range(180):s.press('a')
            s.p.tick(120,True)
            assert s.read('wMapGroup',2)==[26,14] and s.read('wScriptMode')==[0]
            s.capture('fresh_character_the_den');visited=set()
            report['outdoor_regions'].append({'map':'TheDen','terrain':s.authored_blocks(),'vram':s.terrain_upload()})
            visit_doors(s,'TheDen',report,visited)
            s.navigate((20,10),expected_map=15);s.capture('valley_current_exit_road')
            report['outdoor_regions'].append({'map':'ValleyOfTrials','terrain':s.authored_blocks(),'vram':s.terrain_upload()})
            s.navigate((28,12),expected_map=16);s.capture('durotar_road_dry_trees')
            report['outdoor_regions'].append({'map':'DurotarRoad','terrain':s.authored_blocks(),'vram':s.terrain_upload()})
            s.navigate((12,24),expected_map=17);s.capture('senjin_coastal_arrival')
            report['outdoor_regions'].append({'map':'SenjinVillage','terrain':s.authored_blocks(),'vram':s.terrain_upload()})
            visit_doors(s,'SenjinVillage',report,visited)
            s.navigate((10,4),expected_map=16);s.navigate((12,4),expected_map=18)
            s.capture('razor_hill_arrival')
            report['outdoor_regions'].append({'map':'RazorHill','terrain':s.authored_blocks(),'vram':s.terrain_upload()})
            visit_doors(s,'RazorHill',report,visited)
            s.navigate((12,4),expected_map=19);s.capture('orgrimmar_gate_boundary')
            report['outdoor_regions'].append({'map':'OrgrimmarGate','terrain':s.authored_blocks(),'vram':s.terrain_upload()})
            assert len(report['door_routes'])==9 and visited=={21,22,23,24}
            assert hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest()==sha
            report['passed']=True;s.p.stop(save=False);s=None
    except Exception as exc:
        report['failure']=repr(exc)
        if s:
            s.capture('unexpected_state');s.p.stop(save=False)
        (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
        raise
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: nine native door routes, four complete room battery cold restarts and 192/192 actual terrain tiles.')


if __name__=='__main__':main()
