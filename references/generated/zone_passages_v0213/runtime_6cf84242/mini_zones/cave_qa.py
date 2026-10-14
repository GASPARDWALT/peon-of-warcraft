#!/usr/bin/env python3
"""Ordinary button-only private-ROM mini-zone passage QA. No RAM writes/states."""
from pathlib import Path
from collections import deque
import hashlib, importlib.util, json, logging, shutil, sys, tempfile, traceback
ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'tools'))
from validate_peon_zone2_tracker_v0213 import Zone2Session, symbols
from validate_peon_villages import MAPS,DIRECTIONS
from validate_durotar_v022_quests import all_actors,triggers
MAPS.update({25:('PeonValleyCrossroads',5,5),26:('PeonHanazuaCamp',5,5),27:('PeonSarkothBasin',5,5),28:('PeonCaveApproach',5,5),29:('PeonValleyExit',5,5)})
FROZEN=Path('/tmp/peon-v0213-frozen/peon_v0213.gbc')
SHA='6cf84242e9a518af635fe9e2138f7f60228de2d0da7b4ee12ba7511f814f88e8'
OUT=Path(__file__).resolve().parent/'cave_pair_attempt_03'
assert not (OUT/'validation.json').exists(),'Preserve previous evidence; choose a new attempt folder'
OUT.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('read_only_allocator',ROOT/'references/generated/canonical_decor_v0213/verify_runtime_allocator.py')
allocator=importlib.util.module_from_spec(spec);spec.loader.exec_module(allocator)

class MiniSession(Zone2Session):
    def __init__(self,*args): self.inputs=[];self.route_checks=[];self.allocators=[];self.battles=[];self.battle_phase='world';self.battle_context=None;self.menus=0;super().__init__(*args);self.register_battle_observers()
    def write(self,*a,**kw): raise AssertionError('No RAM writes permitted')
    def press(self,key,frames=90):
        self.inputs.append({'frame':self.p.frame_count,'button':key,'hold':8,'advance':frames,'kind':'press'})
        return super().press(key,frames)
    def raw_collision(self,x,y):
        _,w,h=MAPS[self.map()]
        if not(0<=x<2*w and 0<=y<2*h):return 7
        bank,address=self.sym['wOverworldMapBlocks']
        block=self.p.memory[bank,address+(y//2+3)*(w+6)+x//2+3]
        if not block:return 7
        bank=self.read('wTilesetCollisionBank')[0];v=self.read('wTilesetCollisionAddress',2);address=v[0]|v[1]<<8
        return self.p.memory[bank,address+block*4+y%2*2+x%2]
    def native_warps(self):
        v=self.read('wCurMapWarpEventsPointer',2);address=v[0]|v[1]<<8;bank=self.read('wMapScriptsBank')[0]
        rows=[]
        for i in range(self.read('wCurMapWarpEventCount')[0]):
            y,x,idx,grp,mnum=list(self.p.memory[bank,address+i*5:address+i*5+5])

            if idx==255:idx=self.read('wBackupWarpNumber')[0];grp=self.read('wBackupMapGroup')[0];mnum=self.read('wBackupMapNumber')[0]
            rows.append({'index':i+1,'xy':(x,y),'destination_map':mnum,'destination_group':grp,'destination_index':idx})
        return rows
    def live_actors(self,name):
        masks=self.read('wObjectMasks',16);structs=self.read('wObjectStructs',13*40);result=[]
        for a in all_actors(name):
            idx=a['index']
            if a['sprite']=='SPRITE_NONE' or a['sprite'].startswith('SPRITE_PEON_QUEST') or masks[idx]:continue
            if a['event']!='-1' and self.event(a['event']):continue
            for off in range(40,13*40,40):
                row=structs[off:off+40]
                if row[0] and row[1]==idx:a=dict(a,xy=(row[16]-4,row[17]-4));break
            result.append(a)
        return result
    def path(self,target,allowdanger=False):
        name,_,_=MAPS[self.map()];live=self.live_actors(name);occupied={a['xy'] for a in live}
        danger={p for p,script in triggers(name).items() if script in {a['script'] for a in live}}
        warps={r['xy'] for r in self.native_warps()};target=tuple(target);start=self.position();q=deque([(start,[])]);seen={start}
        while q:
            (x,y),route=q.popleft()
            if (x,y)==target:return route
            for key,dx,dy in DIRECTIONS:
                p=x+dx,y+dy
                if p in seen or p in occupied or self.raw_collision(*p)==7:continue
                if p in warps and p!=target:continue
                if p in danger and not allowdanger and p!=target:continue
                seen.add(p);q.append((p,route+[key]))
        raise AssertionError((name,'no safe path',start,target))
    def walk(self,key):
        before=self.position();oldmap=self.map()
        for _ in range(8):
            self.inputs.append({'frame':self.p.frame_count,'button':key,'hold':4,'advance':40,'kind':'walk','before_map':self.map(),'before_xy':self.position()})
            self.p.button(key,delay=4);self.p.tick(40,True)
            if self.position()!=before:break
        assert self.map()==oldmap,(key,'unexpected warp',oldmap,self.map(),before,self.position())
        assert sum(abs(a-b) for a,b in zip(before,self.position()))==1,(key,before,self.position(),self.read('wBattleMode'),self.read('wScriptMode'))
    def navigate(self,target,expected_map=None):
        target=tuple(target)
        assert expected_map is None,'Use portal operation for observed transition and safe-egress checks'
        oldmap=self.map()
        for key in self.path(target):self.walk(key)
        assert self.map()==oldmap and self.position()==target
    def capture_checked(self,label):
        assert self.read('wBattleMode')==[0] and self.read('wScriptMode')==[0],('not stationary world',label)
        self.p.tick(60,True)
        name=MAPS[self.map()][0]
        if name in allocator.PASSAGES or name=='BurningBladeCavern':
            record=allocator.check(self.p,self.sym,name);record.update(label=label,position=self.position(),frame=self.p.frame_count);self.allocators.append(record)
        state=self.capture(label);state['frame']=self.p.frame_count
        return state
    def info(self):
        name,w,h=MAPS.get(self.map(),('unknown',0,0));live=self.live_actors(name) if w else[]
        return {'frame':self.p.frame_count,'map':self.map(),'name':name,'xy':self.position(),'script':self.read('wScriptMode'),'battle':self.read('wBattleMode'),'hp':self.read('wPartyMon1HP',2),'level':self.read('wPartyMon1Level'),'warps':self.native_warps() if w else[],'actors':live,
                'collision_rows':[''.join('#' if self.raw_collision(x,y)==7 else 'W' if self.raw_collision(x,y)&0xf0==0x70 else '.' for x in range(w*2)) for y in range(h*2)]}
    def egress(self,label):
        oldmap=self.map();start=self.position();name,_,_=MAPS[oldmap];live=self.live_actors(name);occupied={a['xy'] for a in live}
        danger={p for p,script in triggers(name).items() if script in {a['script'] for a in live}}
        choices=[(key,(start[0]+dx,start[1]+dy)) for key,dx,dy in DIRECTIONS if self.raw_collision(start[0]+dx,start[1]+dy)==0 and (start[0]+dx,start[1]+dy) not in occupied|danger]
        assert choices,('arrival has no safe native FLOOR escape',oldmap,start)
        key,target=choices[0];self.walk(key);self.p.tick(120,True)
        assert self.map()==oldmap and self.position()==target and self.read('wScriptMode')==[0],('arrival egress failed',oldmap,start,key,self.info())
        self.capture_checked(label+'_safe_egress')
        return {'from':start,'button':key,'to':target,'native_collision':self.raw_collision(*target),'map_unchanged':True}
    def portal(self,lane,expected,label):
        lane=tuple(lane);oldmap=self.map();entry=next(r for r in self.native_warps() if r['xy']==lane)
        assert entry['destination_map']==expected,(entry,expected)
        route=self.path(lane);assert route,('step off arrival first',lane)
        for key in route[:-1]:self.walk(key)
        before=self.position();self.capture_checked(label+'_approach')
        self.inputs.append({'frame':self.p.frame_count,'button':route[-1],'hold':30,'advance':150,'kind':'portal','source_map':oldmap,'source_lane':lane})
        self.p.button(route[-1],delay=30);self.p.tick(150,True)
        assert self.map()==expected,(label,'warp failed',oldmap,lane,expected,self.info())
        destination=self.native_warps()[entry['destination_index']-1]['xy']
        assert self.position()==destination,(label,'wrong published destination',destination,self.position())
        assert self.read('wScriptMode')==[0] and self.read('wBattleMode')==[0],(label,'entry still scripted')
        self.capture_checked(label+'_arrival')
        escape=self.egress(label)
        record={'label':label,'source_map':oldmap,'source_lane':lane,'source_index':entry['index'],'approach':before,'entry_button':route[-1],'destination_map':expected,'destination_xy':destination,'destination_index':entry['destination_index'],'safe_egress':escape,'passed':True}
        self.route_checks.append(record);return record


    def register_battle_observers(self):
        self.p.hook_register(*self.sym['LoadBattleMenu'],self.observe_battle_menu,None)
        self.p.hook_register(*self.sym['StaticMenuJoypad'],self.observe_static_ready,None)
        for label,phase in [('PeonBags','bags_drawing'),('PeonInventory','inventory_drawing'),('PeonInventory.draw','inventory_drawing'),('PeonInventory.input','inventory'),('PeonInventory.used_battle_item','acting')]:
            self.p.hook_register(*self.sym[label],self.observe_battle_phase,phase)
        self.p.hook_register(*self.sym['PeonInterfaceWait'],self.observe_bags_ready,None)
    def observe_battle_menu(self,_):
        self.menus+=1;self.battle_phase='battle_drawing';self.battle_context='battle'
    def observe_static_ready(self,_):
        if self.read('wBattleMode')[0] and self.battle_context=='battle':self.battle_phase='battle'
    def observe_battle_phase(self,phase):self.battle_phase=phase;self.battle_context=None
    def observe_bags_ready(self,_):
        if self.battle_phase=='bags_drawing':self.battle_phase='bags'
    def word(self,name):return int.from_bytes(bytes(self.read(name,2)),'big')
    def battle_snapshot(self):
        return {'frame':self.p.frame_count,'phase':self.battle_phase,'mode':self.read('wBattleMode')[0],'party_level':self.read('wPartyMon1Level')[0],'party_hp':self.word('wPartyMon1HP'),'party_maxhp':self.word('wPartyMon1MaxHP'),'battle_hp':self.word('wBattleMonHP') if self.read('wBattleMode')[0] else None,'enemy_hp':self.word('wEnemyMonHP') if self.read('wBattleMode')[0] else None,'enemy_species':self.read('wEnemyMonSpecies')[0] if self.read('wBattleMode')[0] else None,'enemy_level':self.read('wEnemyMonLevel')[0] if self.read('wBattleMode')[0] else None,'mana':self.word('wPartyMon1CaughtData'),'healing_potions':self.item_quantity(18),'moves':self.read('wPartyMon1Moves',4),'cursor':self.read('wMenuCursorX')+self.read('wMenuCursorY'),'move_menus':self.move_menus,'battle_menus':self.menus}
    def wait_battle(self,predicate,limit=6000,prompts=False):
        for i in range(limit):
            if predicate():return
            if prompts and i%30==0 and self.battle_phase not in ('battle_drawing','battle','inventory','bags'):
                self.inputs.append({'frame':self.p.frame_count,'button':'a','hold':1,'advance':1,'kind':'battle_prompt'})
                self.p.button('a',delay=1)
            self.p.tick(1,True)
        raise AssertionError(('native battle wait expired',self.battle_snapshot()))
    def action_return(self,oldmenus):
        self.wait_battle(lambda:(self.menus>oldmenus and self.battle_phase=='battle') or not self.read('wBattleMode')[0],prompts=True)
        if not self.read('wBattleMode')[0]:self.close_dialogue();self.battle_phase='world'
    def attack_slot(self,slot):
        self.p.tick(80,True)
        assert self.battle_phase=='battle',self.battle_snapshot()
        for _ in range(4):
            x,y=self.read('wMenuCursorX')[0],self.read('wMenuCursorY')[0]
            if(x,y)==(1,1):break
            self.press('left' if x>1 else 'up',30)
        oldmoves=self.move_menus;oldmenus=self.menus;self.press('a',60)
        self.wait_battle(lambda:self.move_menus>oldmoves);self.p.tick(80,True)
        for _ in range(5):
            cur=self.read('wMenuCursorY')[0]-1
            if cur==slot:break
            self.press('up' if cur>slot else 'down',30)
        assert self.read('wMenuCursorY')==[slot+1],('move selection',slot,self.battle_snapshot())
        self.battle_phase='acting';self.battle_context=None;self.press('a',30);self.action_return(oldmenus)
    def use_healing(self):
        self.p.tick(80,True)
        oldmenus=self.menus
        for _ in range(4):
            x,y=self.read('wMenuCursorX')[0],self.read('wMenuCursorY')[0]
            if(x,y)==(1,2):break
            self.press('left' if x>1 else 'down',30)
        self.press('a',30);self.wait_battle(lambda:self.battle_phase=='bags')
        self.press('a',30);self.wait_battle(lambda:self.battle_phase=='inventory')
        items=self.read('wItems',self.read('wNumItems')[0]*2)[::2];assert 18 in items
        for _ in range(items.index(18)):self.press('right',30);self.wait_battle(lambda:self.battle_phase=='inventory')
        assert self.read('wNamedObjectIndex')==[18]
        self.battle_phase='acting';self.battle_context=None;self.press('a',30);self.action_return(oldmenus)
    def battle(self,label,flag):
        before=self.battle_snapshot();heals=self.heal_calls;used=len(self.used_moves);actions=[]
        self.wait_battle(lambda:self.read('wBattleMode')[0],prompts=True)
        self.wait_battle(lambda:self.battle_phase=='battle',prompts=True)
        self.capture(label+'_battle_start')
        for turn in range(40):
            if not self.read('wBattleMode')[0]:break
            state=self.battle_snapshot()
            if state['battle_hp']<=6 and state['healing_potions']:
                action='healing_potion';self.use_healing()
            else:
                slot=1 if state['mana']>=15 and 84 in self.read('wBattleMonMoves',4) else 0
                action='move_slot_'+str(slot);self.attack_slot(slot)
            actions.append({'turn':turn,'action':action,'before':state,'after':self.battle_snapshot()})
            self.capture(label+'_action_'+str(turn))
        assert self.read('wBattleMode')==[0] and self.read('wScriptMode')==[0],('battle incomplete',label,self.battle_snapshot())
        record={'label':label,'flag':flag,'before':before,'after':self.battle_snapshot(),'actions':actions,'used_moves':self.used_moves[used:],'outcome':self.read('wBattleResult')[0],'death_flag':self.event(flag),'no_silent_heal':heals==self.heal_calls}
        self.battles.append(record)
        assert record['outcome']==0 and record['death_flag'],('ordinary battle not won',record)
        self.capture_checked(label+'_victory_world')
        return record
    def engage(self,xy,direction=None):
        self.navigate(tuple(xy))
        if direction:self.press(direction,30);self.press('a',60)
        return self.battle_snapshot()
    def train(self,row):
        assert self.map()==22
        self.navigate((6,4));self.press('up',30);self.press('a',120)
        for _ in range(60):
            if self.phase=='main':break
            self.press('a',30)
        assert self.phase=='main',('trainer not ready',self.phase)
        self.select(row);self.capture('kento_selected_lesson_'+str(row));oldmoney=self.money();self.press('a',90)
        assert self.phase=='confirm',('lesson not available',row,self.phase,self.read('wPartyMon1Level'),oldmoney)
        self.press('a',90);assert self.phase=='message';self.capture('kento_lesson_'+str(row)+'_bought');self.dismiss();self.exit_trainer()
        return {'row':row,'money_before':oldmoney,'money_after':self.money(),'moves':self.read('wPartyMon1Moves',4),'ordinary_buttons':True}

logging.disable(logging.CRITICAL)
assert hashlib.sha256(FROZEN.read_bytes()).hexdigest()==SHA
report={'rom_sha256':SHA,'status':'RUNNING','ordinary_new_shaman_buttons_only':True,'ram_edits':False,'save_states_loaded':False,'cpu_substitution':False,'user_save_opened':False,'hooks':'Read-only observations of native menu/battle entries only','transitions':[]}
temp=tempfile.TemporaryDirectory(prefix='peon-v0213-mini-zones-');rom=Path(temp.name)/'private.gbc';shutil.copyfile(FROZEN,rom)
assert not Path(str(rom)+'.ram').exists()
s=MiniSession(rom,symbols(FROZEN.with_suffix('.sym')),OUT)
def save():
    report.update(battles=s.battles,transitions=s.route_checks,captures=s.captures,allocator_checks=s.allocators,inputs=s.inputs,last_state=s.info() if s.map() in MAPS else {'map':s.map(),'position':s.position()})
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'ready':True,'folder':str(OUT),'private_rom':str(rom)}),flush=True)
try:
    for line in sys.stdin:
        try:
            op=json.loads(line);command=op['op']
            if command=='fresh':s.fresh_class();result=s.info()
            elif command=='info':result=s.info()
            elif command=='nav':s.navigate(op['xy']);result=s.info()
            elif command=='path':result=s.path(op['xy'],op.get('allowdanger',False))
            elif command=='portal':result=s.portal(op['xy'],op['map'],op['label'])
            elif command=='egress':result=s.egress(op['label'])
            elif command=='capture':result=s.capture_checked(op['label'])
            elif command=='fight':result=s.battle(op['label'],op['flag'])
            elif command=='engage':result=s.engage(op['xy'],op.get('direction'))
            elif command=='train':result=s.train(op['row'])
            elif command=='battle_info':result=s.battle_snapshot()
            elif command=='press':s.press(op['key'],op.get('frames',90));result=s.battle_snapshot()
            elif command=='raw_walk':s.walk(op['key']);result=s.info()
            elif command=='talk':s.talk_plain(tuple(op['xy']),op['direction']);result=s.info()
            elif command=='stop':report['status']=op.get('status','PASS');save();print(json.dumps({'stopped':True,'status':report['status']}),flush=True);break
            else:raise ValueError(command)
            save();print(json.dumps({'operation':op,'result':result}),flush=True)
        except Exception as e:
            report['status']='FAIL';report['failure']={'operation':op,'error':repr(e),'traceback':traceback.format_exc()};s.capture('first_failure_'+str(len(s.route_checks)));save();print(json.dumps({'operation':op,'failure':repr(e),'state':s.info()}),flush=True)
finally:
    save();s.p.stop(save=False);temp.cleanup()
