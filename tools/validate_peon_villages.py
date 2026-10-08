#!/usr/bin/env python3
"""Normal-button village, NPC, house-entry and inside-house save validation.

An isolated fresh ROM copy is used.  The playable route never edits RAM,
substitutes speakers, loads emulator states, or touches a user's save file.
Read-only VRAM/RAM inspection verifies rendered portraits, palettes and saves.
"""
from collections import deque
from pathlib import Path
import hashlib
import json
import logging
import re
import shutil
import tempfile

import numpy as np
from PIL import Image
from pyboy import PyBoy

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'references/generated/durotar_v022/village_validation'
MAPS={14:('TheDen',12,10),15:('ValleyOfTrials',16,12),16:('DurotarRoad',12,14),
      17:('SenjinVillage',12,10),18:('RazorHill',12,10),19:('OrgrimmarGate',12,10),
      20:('BurningBladeCavern',10,10),21:('PeonTrollHut',6,5),22:('PeonOrcHut',6,5),23:('PeonOrcInn',6,5),24:('PeonTrollInn',6,5)}
ROLES={'SPRITE_SAGE':'troll_caster','SPRITE_CLERK':'troll_fisher',
       'SPRITE_LINK_RECEPTIONIST':'troll_guard','SPRITE_OFFICER':'orc_guard',
       'SPRITE_GENTLEMAN':'orc_vendor','SPRITE_BLACK_BELT':'orc_questgiver'}
DIRECTIONS=[('left',-1,0),('right',1,0),('up',0,-1),('down',0,1)]


def load_symbols():
    out={}
    for line in (ROOT/'pokecrystal.sym').read_text().splitlines():
        parts=line.split()
        if len(parts)==2 and ':' in parts[0]:
            try:out[parts[1]]=tuple(int(n,16) for n in parts[0].split(':'))
            except ValueError:pass
    return out


def sprite_constants():
    out={};idx=0
    for line in (ROOT/'constants/sprite_constants.asm').read_text().splitlines():
        parts=line.split(';',1)[0].split()
        if not parts:continue
        if parts[0] in ('const_def','const_next'):
            idx=int(parts[1].replace('$','0x'),0) if len(parts)>1 else 0
        elif parts[0]=='const':out[parts[1]]=idx;idx+=1
    return out


def actors(name):
    out=[]
    for line in (ROOT/'maps'/f'{name}.asm').read_text().splitlines():
        match=re.match(r'\s*object_event\s+(\d+),\s*(\d+),\s*((?:SPRITE_|PEON_SPRITE_)\w+),(.+)',line)
        if not match:continue
        fields=[s.strip() for s in line.strip().split(' ',1)[1].split(',')]
        out.append({'xy':(int(match[1]),int(match[2])),'sprite':match[3],
                    'script':fields[-2],'palette':fields[8],'event':fields[-1],'map_object_index':len(out)+1})
    return out


def warp_tiles(name):
    return {tuple(map(int,m.groups())) for m in re.finditer(
        r'^\s*warp_event\s+(\d+),\s*(\d+),',(ROOT/'maps'/f'{name}.asm').read_text(),re.M)}


class Session:
    def __init__(self,rom,sym):
        self.rom=rom;self.sym=sym;self.open()
        self.flags={};index=0
        for row in (ROOT/'constants/event_flags.asm').read_text().splitlines():
            parts=row.split(';')[0].split()
            if not parts:continue
            if parts[0] in ('const_def','const_next'):index=int(parts[1]) if len(parts)>1 else 0
            elif parts[0]=='const_skip':index+=int(parts[1]) if len(parts)>1 else 1
            elif parts[0]=='const':self.flags[parts[1]]=index;index+=1
        self.collisions=[row.split('tilecoll',1)[1].split(';',1)[0].replace(' ','').split(',')
                         for row in (ROOT/'data/tilesets/peon_collision.asm').read_text().splitlines() if 'tilecoll' in row]
    def open(self):
        self.p=PyBoy(str(self.rom),window='null',sound_emulated=False,log_level='ERROR')
        self.p.set_emulation_speed(0)
    def read(self,name,length=1):
        if not length:return []
        bank,address=self.sym[name]
        return list(self.p.memory[address:address+length] if address>=0xe000
                    else self.p.memory[bank,address:address+length])
    def position(self):return tuple(self.read('wXCoord')+self.read('wYCoord'))
    def map(self):return self.read('wMapNumber')[0]
    def press(self,key,frames=90):self.p.button(key,delay=8);self.p.tick(frames,True)
    def capture(self,name):
        self.p.screen.image.save(OUT/f'{name}.png')
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(OUT/f'{name}_4x.png')
        print(name,MAPS.get(self.map(),self.map()),self.position(),flush=True)
    def walk(self,key):
        before=self.position();oldmap=self.map()
        # Release before the 16-frame step completes. Holding until wXCoord
        # changes can buffer a second step when many map objects are active.
        # Short ordinary D-pad taps also handle Crystal's turn-before-walking.
        for _ in range(8):
            self.p.button(key,delay=4);self.p.tick(40,True)
            if self.position()!=before:break
        assert self.map()==oldmap,(key,'unexpected warp',oldmap,self.map(),before,self.position())
        assert sum(abs(a-b) for a,b in zip(before,self.position()))==1,(key,before,self.position())
    def collision_at(self,x,y):
        name,w,h=MAPS[self.map()]
        if not (0<=x<w*2 and 0<=y<h*2):return 'WALL'
        grid=(ROOT/'maps'/f'{name}.blk').read_bytes();block=grid[(y//2)*w+x//2]
        if block==0:return 'WALL' # Crystal bypasses collision row for ID zero.
        return self.collisions[block][(y%2)*2+x%2]
    def path(self,target):
        num=self.map();name,w,h=MAPS[num]
        live=[]
        for npc in actors(name):
            if self.read('wObjectMasks',16)[npc['map_object_index']]:continue
            flag=npc['event']
            if flag!='-1':
                i=self.flags[flag]
                if self.read('wEventFlags',i//8+1)[i//8]&(1<<(i%8)):continue
            live.append(npc)
        occupied={npc['xy'] for npc in live};warps=warp_tiles(name)
        live_scripts={npc['script'] for npc in live}
        dangerous={tuple(map(int,m.groups()[:2])) for m in re.finditer(
            r'^\s*coord_event\s+(\d+),\s*(\d+),\s*-1,\s*(\w+)',
            (ROOT/'maps'/f'{name}.asm').read_text(),re.M) if m[3] in live_scripts}
        start=self.position();q=deque([(start,[])]);seen={start}
        while q:
            (x,y),path=q.popleft()
            if (x,y)==target:return path
            for key,dx,dy in DIRECTIONS:
                pos=(x+dx,y+dy)
                if pos in seen or pos in occupied or self.collision_at(*pos)=='WALL':continue
                if pos in warps and pos!=target:continue
                if pos in dangerous and pos!=target:continue
                seen.add(pos);q.append((pos,path+[key]))
        raise AssertionError((name,'no path',start,target))
    def navigate(self,target,expected_map=None):
        target=tuple(target);name,_,_=MAPS[self.map()];warps=warp_tiles(name)
        if self.position()==target and target in warps:
            occupied={npc['xy'] for npc in actors(name)}
            for key,dx,dy in DIRECTIONS:
                pos=(target[0]+dx,target[1]+dy)
                if self.collision_at(*pos)!='WALL' and pos not in warps and pos not in occupied:
                    self.walk(key);break
            else:raise AssertionError(('cannot step off warp',name,target))
        path=self.path(target);oldmap=self.map()
        for i,key in enumerate(path):
            if target in warps and i==len(path)-1:
                self.p.button(key,delay=30);self.p.tick(150,True)
            else:self.walk(key)
        if expected_map is None:
            assert self.map()==oldmap and self.position()==target,(oldmap,target,self.map(),self.position())
        else:assert self.map()==expected_map,(oldmap,target,expected_map,self.map(),self.position())
    def close_dialogue(self):
        for _ in range(80):
            if self.read('wScriptMode')==[0]:return
            self.press('a')
        raise AssertionError(('conversation failed to close',self.map(),self.position(),self.read('wScriptMode')))
    def money(self):return int.from_bytes(bytes(self.read('wMoney',3)),'big')
    def item_quantity(self,item):
        values=self.read('wItems',self.read('wNumItems')[0]*2)
        return sum(values[i+1] for i in range(0,len(values),2) if values[i]==item)
    def state(self):
        return {name:self.read(name,size) for name,size in [('wPlayerName',11),('wMapGroup',2),
                ('wXCoord',1),('wYCoord',1),('wBackupWarpNumber',1),('wBackupMapGroup',1),
                ('wBackupMapNumber',1),('wPartyMon1Moves',4),('wPartyMon1Item',1),('wMoney',3)]}
    def save_restart(self):
        before=self.state();self.press('start')
        for _ in range(10):
            if self.read('wMenuCursorPosition')[0]<=1:break
            self.press('up',30)
        for _ in range(3):self.press('down',30)
        self.press('a')
        for _ in range(5):self.press('a',180)
        self.capture('troll_hut_saved');self.p.stop(save=True)
        assert Path(str(self.rom)+'.ram').stat().st_size==32768
        self.open();self.p.tick(1800,True);self.press('start')
        for _ in range(5):self.press('a',180)
        self.p.tick(180,True)
        after=self.state();assert before==after,('inside-house save mismatch',before,after)
        assert self.map()==21 and self.read('wScriptMode')==[0]
        self.capture('troll_hut_cold_restart');return {'before':before,'after':after,'passed':True}


def portrait_check(s,role):
    expected_binary=(ROOT/'gfx/peon_portraits'/f'{role}.2bpp').read_bytes()
    assert len(expected_binary)==144
    assert bytes(s.p.memory[1,0x9600:0x9690])==expected_binary,role+' portrait VRAM mismatch'
    tilemap=s.read('wTilemap',360);attrs=s.read('wAttrmap',360)
    assert [tilemap[y*20+x] for y in range(8,11) for x in range(1,4)]==list(range(0x60,0x69))
    assert [attrs[y*20+x] for y in range(8,11) for x in range(1,4)]==[15]*9
    palette=[]
    for line in (ROOT/'gfx/peon_portraits'/f'{role}.pal').read_text().splitlines():
        if 'RGB' in line:palette.append(tuple(map(int,re.findall(r'\d+',line))))
    native=np.array(Image.open(ROOT/'gfx/peon_portraits'/f'{role}.png'))
    expected=np.array(palette,dtype='uint8')[native]
    actual=np.array(s.p.screen.image.convert('RGB').crop((8,64,32,88)))>>3
    assert np.array_equal(actual,expected),(role,'portrait rendered RGB555 mismatch',int(np.any(actual!=expected,axis=-1).sum()))
    return {'role':role,'rgb555_matches':True,'vram_matches':True,'tile_attributes_match':True}


def sprite_palette_check(s,npc,sprites):
    sprite=sprites[npc['sprite']];role=ROLES[npc['sprite']]
    table=s.read('wUsedSprites',64);tile=None
    for i in range(0,64,2):
        if table[i]==sprite:tile=table[i+1];break
    assert tile is not None,(role,'sprite not allocated',table)
    bank=0 if tile&128 else 1;address=0x8000+(tile&127)*16
    expected=(ROOT/'gfx/sprites'/f'peon_{role}.2bpp').read_bytes()
    assert bytes(s.p.memory[bank,address:address+192])==expected[:192],role+' idle VRAM mismatch'
    assert bytes(s.p.memory[bank,address+0x800:address+0x800+192])==expected[192:],role+' walking VRAM mismatch'
    objs=s.read('wObjectStructs',13*40);runtime=None
    for i in range(13):
        row=objs[i*40:(i+1)*40]
        if row[0]==sprite and row[1]==npc['map_object_index']:runtime=row;break
    assert runtime is not None,(role,'nearby NPC runtime not found')
    expected_index=6 if npc['palette']=='PAL_NPC_TREE' else 2
    assert runtime[6]&7==expected_index,(role,'incorrect object palette',runtime[6],expected_index)
    encoded=s.read('wOBPals1',64)[expected_index*8:(expected_index+1)*8]
    bank,address=s.sym['PeonMapOBJPalettes']
    assert encoded==list(s.p.memory[bank,address+expected_index*8:address+(expected_index+1)*8])
    if expected_index==6:
        colour=int.from_bytes(bytes(encoded[4:6]),'little');r=colour&31;g=(colour>>5)&31;b=(colour>>10)&31
        assert g>r and b>r,(role,'Darkspear skin is not cyan',(r,g,b))
    return {'graphics_match':True,'palette_index':expected_index,'cyan_skin':expected_index==6}


def talk_npc(s,npc,sprites):
    x,y=npc['xy'];options=[]
    for face,dx,dy in [('up',0,1),('down',0,-1),('right',-1,0),('left',1,0)]:
        target=(x+dx,y+dy)
        try:path=s.path(target)
        except AssertionError:continue
        options.append((len(path),target,face))
    assert options,('NPC inaccessible',npc)
    _,target,face=min(options);s.navigate(target);s.press(face,30)
    palette=sprite_palette_check(s,npc,sprites)
    terrain_before=[bytes(s.p.memory[bank,0x9000:0x9600]) for bank in (0,1)]
    money=s.money();quantity=s.item_quantity(46)
    s.press('a',120);assert s.read('wScriptMode')!=[0],('NPC not responding',npc)
    portrait=portrait_check(s,ROLES[npc['sprite']])
    label=npc['script'].replace('Script','')
    s.capture(label+'_dialogue');s.close_dialogue()
    assert terrain_before==[bytes(s.p.memory[bank,0x9000:0x9600]) for bank in (0,1)],'Conversation changed terrain VRAM'
    result={'npc':label,'xy':list(npc['xy']),'map':MAPS[s.map()][0],
            'ordinary_buttons':True,'portrait':portrait,'sprite':palette,'closed_cleanly':True}
    if 'Kwaii' in npc['script'] or 'Jark' in npc['script']:
        if money>=25:
            assert s.money()==money-25,(label,'vendor price',money,s.money())
            assert s.item_quantity(46)==quantity+5,(label,'water bundle not received')
            result['purchase']={'cost_copper':25,'spring_water_quantity':5,'passed':True}
        else:result['purchase']={'skipped':'Fresh character lacks 25 copper; no funds injected.'}
    return result


def test_houses(s,name,entries,results):
    for i,entry in enumerate(entries[name]):
        origin=s.map();target=tuple(entry['xy']);destination={'PEON_TROLL_HUT':21,'PEON_ORC_HUT':22,'PEON_ORC_INN':23,'PEON_TROLL_INN':24}[entry['target']]
        s.navigate(target,expected_map=destination);s.capture(name+f'_house_{i+1}_inside')
        record={'origin_map':origin,'door':list(target),'interior_map':destination,'ordinary_buttons':True}
        if destination==21 and 'inside_troll_hut_save_cold_restart' not in results:
            s.walk('up');results['inside_troll_hut_save_cold_restart']=s.save_restart()
        s.navigate((5,7),expected_map=origin)
        assert s.position()==target,('house returned to wrong origin',name,target,s.position())
        assert s.read('wScriptMode')==[0]
        record['returned_to_exact_origin']=True;results['building_entries'].append(record)
        s.capture(name+f'_house_{i+1}_returned')


def main():
    logging.disable(logging.CRITICAL);OUT.mkdir(parents=True,exist_ok=True)
    sym=load_symbols();sprites=sprite_constants()
    results={'rom_sha256':hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest(),
             'emulator':'PyBoy 2.7','playable_method':'Fresh normal-button new game, walking, conversations, purchases, house warps and battery-save cold restart.',
             'ram_edits':False,'emulator_states_loaded':False,'building_entries':[],'npcs':[]}
    entries=json.loads((ROOT/'references/generated/durotar_v022/building_entries.json').read_text())
    s=None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-villages-') as directory:
            rom=Path(directory)/'test.gbc';shutil.copyfile(ROOT/'pokecrystal.gbc',rom);s=Session(rom,sym)
            s.p.tick(1800,False);s.press('start');s.press('down');s.press('a')
            for _ in range(180):s.press('a')
            s.p.tick(120,True)
            assert s.read('wMapGroup',2)==[26,14] and s.read('wScriptMode')==[0]
            s.capture('fresh_character_the_den');results['new_game_reaches_den']=True
            test_houses(s,'TheDen',entries,results)
            s.navigate((20,10),expected_map=15);s.navigate((28,12),expected_map=16)
            for npc in actors('DurotarRoad'):
                if npc['sprite'] in ROLES:results['npcs'].append(talk_npc(s,npc,sprites))
            s.navigate((12,24),expected_map=17);s.capture('senjin_arrival')
            for npc in actors('SenjinVillage'):results['npcs'].append(talk_npc(s,npc,sprites))
            test_houses(s,'SenjinVillage',entries,results)
            s.navigate((10,4),expected_map=16);s.navigate((12,4),expected_map=18);s.capture('razor_arrival')
            for npc in actors('RazorHill'):results['npcs'].append(talk_npc(s,npc,sprites))
            test_houses(s,'RazorHill',entries,results)
            s.navigate((12,4),expected_map=19);s.capture('orgrimmar_gate_arrival')
            for npc in actors('OrgrimmarGate'):results['npcs'].append(talk_npc(s,npc,sprites))
            assert len(results['npcs'])==18,len(results['npcs'])
            assert len(results['building_entries'])==9,len(results['building_entries'])
            assert results['inside_troll_hut_save_cold_restart']['passed']
            results['npc_count']=18;results['building_count']=9;results['all_checks_passed']=True
            s.p.stop(save=False);s=None
    except Exception as exc:
        results['all_checks_passed']=False;results['failure']=repr(exc)
        if s is not None:
            s.capture('unexpected_state');s.p.stop(save=False)
        (OUT/'validation_results.json').write_text(json.dumps(results,indent=2)+'\n')
        raise
    results['limitations']=['Chromatic physical hardware not exercised.','These maps contain the current 18 village/road/gate NPCs, not every WoW Classic NPC.']
    (OUT/'validation_results.json').write_text(json.dumps(results,indent=2)+'\n')
    print('PASS: 18 NPCs with correct portraits and palettes, 9 enterable buildings, and inside-troll-hut battery-save cold restart.')


if __name__=='__main__':main()
