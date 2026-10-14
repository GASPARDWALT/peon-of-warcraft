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
OUT=Path(__file__).resolve().parent/'attempt_02'
assert not (OUT/'validation.json').exists(),'Preserve previous evidence; choose a new attempt folder'
OUT.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('read_only_allocator',ROOT/'references/generated/canonical_decor_v0213/verify_runtime_allocator.py')
allocator=importlib.util.module_from_spec(spec);spec.loader.exec_module(allocator)

class MiniSession(Zone2Session):
    def __init__(self,*args): self.inputs=[];self.route_checks=[];self.allocators=[];super().__init__(*args)
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
        name=MAPS[self.map()][0];record=allocator.check(self.p,self.sym,name)
        record.update(label=label,position=self.position(),frame=self.p.frame_count)
        self.allocators.append(record);state=self.capture(label);state['frame']=self.p.frame_count
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

logging.disable(logging.CRITICAL)
assert hashlib.sha256(FROZEN.read_bytes()).hexdigest()==SHA
report={'rom_sha256':SHA,'status':'RUNNING','ordinary_new_shaman_buttons_only':True,'ram_edits':False,'save_states_loaded':False,'cpu_substitution':False,'user_save_opened':False,'hooks':'Read-only observations of native menu/battle entries only','transitions':[]}
temp=tempfile.TemporaryDirectory(prefix='peon-v0213-mini-zones-');rom=Path(temp.name)/'private.gbc';shutil.copyfile(FROZEN,rom)
assert not Path(str(rom)+'.ram').exists()
s=MiniSession(rom,symbols(FROZEN.with_suffix('.sym')),OUT)
def save():
    report.update(transitions=s.route_checks,captures=s.captures,allocator_checks=s.allocators,inputs=s.inputs,last_state=s.info() if s.map() in MAPS else {'map':s.map(),'position':s.position()})
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
            elif command=='fight':result=s.fight(op['label'],op['flag'])
            elif command=='talk':s.talk_plain(tuple(op['xy']),op['direction']);result=s.info()
            elif command=='stop':report['status']=op.get('status','PASS');save();print(json.dumps({'stopped':True,'status':report['status']}),flush=True);break
            else:raise ValueError(command)
            save();print(json.dumps({'operation':op,'result':result}),flush=True)
        except Exception as e:
            report['status']='FAIL';report['failure']={'operation':op,'error':repr(e),'traceback':traceback.format_exc()};s.capture('first_failure_'+str(len(s.route_checks)));save();print(json.dumps({'operation':op,'failure':repr(e),'state':s.info()}),flush=True)
finally:
    save();s.p.stop(save=False);temp.cleanup()
