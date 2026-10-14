#!/usr/bin/env python3
"""Ordinary exact-ROM portal walking; private proven native battery, no writes."""
from pathlib import Path
from collections import deque
import hashlib,importlib.util,json,logging,re,shutil,sys,tempfile
from PIL import Image
ROOT=Path('/workspace/peon-of-warcraft');sys.path.insert(0,str(ROOT/'tools'))
from validate_peon_class_potions import PotionSession
from validate_peon_zone2_tracker_v0213 import Zone2Session,symbols
from validate_peon_villages import MAPS,DIRECTIONS,warp_tiles,Session
import import_peon_zone_passages_v0213 as art
FROZEN=Path('/tmp/peon-v0213-frozen/peon_v0213.gbc');SYM=FROZEN.with_suffix('.sym')
EXPECTED='6cf84242e9a518af635fe9e2138f7f60228de2d0da7b4ee12ba7511f814f88e8'
OUT=Path(__file__).resolve().parent/'attempt_05'
for n in ('PeonValleyCrossroads','PeonHanazuaCamp','PeonSarkothBasin','PeonCaveApproach','PeonValleyExit'):
 MAPS[list(art.native.DIMS).index(n)+12]=(n,*art.native.DIMS[n])
spec=importlib.util.spec_from_file_location('allocator',ROOT/'references/generated/canonical_decor_v0213/verify_runtime_allocator.py');allocator=importlib.util.module_from_spec(spec);spec.loader.exec_module(allocator)
manifest=json.loads((art.OUT/'manifest.json').read_text());BY_MAP={r['map']:r for r in manifest['maps']}
EGRESS={(14,1):'left',(14,4):'right',(15,1):'right',(15,2):'left',(15,3):'down',
 (16,1):'right',(16,2):'up',(16,3):'down',(17,1):'down',(18,1):'up',(18,2):'down',
 (19,1):'up',(20,1):'up',(25,1):'up',(25,2):'down',(25,3):'right',
 (26,1):'left',(26,2):'up',(27,1):'down',(27,2):'left',(28,1):'up',(28,2):'down',
 (29,1):'right',(29,2):'left'}

def threshold(number,index):
 name=MAPS[number][0]
 if number==20:return {'original_index':1,'original_xy':[10,16],'destination':'PEON_CAVE_APPROACH','destination_index':2,'cells':[[10,16],[11,16]]}
 return next(t for t in BY_MAP[name]['thresholds'] if t['original_index']==index)

class PortalSession(PotionSession):
 def open(self):
  # Register only the actual menu/encounter observers used in this route.
  # The older BagSession has an unrelated removed totem-drawing hook.
  Session.open(self)
  for label,callback in [('LoadBattleMenu',self.battle_menu),('StaticMenuJoypad',self.static_ready),
                         ('PeonInterfaceWait',self.bags_ready),('VerticalMenu',self.vertical_menu),
                         ('ReturnFarCall',self.returned),('BattleCommand_UsedMoveText',self.used_move),
                         ('MoveSelectionScreen',self.move_screen)]:self.p.hook_register(*self.sym[label],callback,None)
  for label,phase in [('PeonBags','bags_drawing'),('PeonInventory','inventory_drawing'),
                      ('PeonInventory.draw','inventory_drawing'),('PeonInventory.input','inventory'),
                      ('PeonInventory.used_battle_item','using_item')]:self.p.hook_register(*self.sym[label],self.set_phase,phase)
  self.enemy_turns=0
  self.p.hook_register(*self.sym['DoEnemyTurn'],lambda _:setattr(self,'enemy_turns',self.enemy_turns+1),None)
  self.p.hook_register(*self.sym['LoadTrainerOrWildMonPic'],lambda _:setattr(self,'encounter_loads',self.encounter_loads+1),None)
  self.p.hook_register(*self.sym['HealParty'],lambda _:setattr(self,'heal_calls',self.heal_calls+1),None)
 def __init__(self,rom,sym):
  self.folder=OUT;self.captures=[];self.checks=[];self.crossings=[];self.inputs=[];self.flees=[]
  super().__init__(rom,sym)
  for m in re.finditer(r'^\s*DEF\s+(EVENT_\w+)\s+EQU\s+(\$[0-9a-fA-F]+|\d+)\b',(ROOT/'constants/event_flags.asm').read_text(),re.M):self.flags[m[1]]=int(m[2][1:],16) if m[2].startswith('$') else int(m[2])
 def write(self,*a,**k):raise AssertionError('No emulator RAM writes permitted')
 def event(self,name):
  i=self.flags[name];return bool(self.read('wEventFlags',i//8+1)[i//8]&(1<<(i%8)))
 collision_at=Zone2Session.collision_at
 def live_actors(self,name):return [a for a in super().live_actors(name) if a['sprite']!='SPRITE_NONE']
 def press(self,key,frames=90):
  self.inputs.append({'frame':self.p.frame_count,'key':key,'frames':frames,'map':self.map(),'xy':self.position()})
  super().press(key,frames)
 def capture(self,label):
  self.folder.mkdir(parents=True,exist_ok=True)
  self.p.screen.image.save(self.folder/(label+'.png'));self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(self.folder/(label+'_4x.png'))
  r={'name':label,'frame':self.p.frame_count,'map':self.map(),'xy':list(self.position()),'level':self.read('wPartyMon1Level')[0],
     'hp':self.read('wPartyMon1HP',2),'script_mode':self.read('wScriptMode'),'battle_mode':self.read('wBattleMode')}
  self.captures.append(r);print(label,r,flush=True)
  return r
 def world(self,label):
  assert self.read('wBattleMode')==[0] and self.read('wScriptMode')==[0],('not world',label,self.phase,self.map(),self.position())
  self.p.tick(90,True);r=self.capture(label);r['allocator']=allocator.check(self.p,self.sym,MAPS[self.map()][0]);self.checks.append(r)
  return r
 def settle(self,label):
  for _ in range(40):
   if self.read('wBattleMode')[0]:self.flee(label);break
   if self.read('wScriptMode')==[0]:break
   self.press('a',90)
  assert self.read('wBattleMode')==[0] and self.read('wScriptMode')==[0],('failed world settle',label)
  self.phase,self.context='overworld',None
 def flee(self,label):
  before={'flags':self.read('wEventFlags',256),'xp':self.experience(),'money':self.money(),'map':self.map()}
  self.wait(lambda:self.phase=='battle',buttons=True)
  self.capture(label+'_native_encounter')
  for _ in range(24):
   if not self.read('wBattleMode')[0]:break
   self.ready('battle')
   if self.word('wBattleMonHP')*2<=self.word('wBattleMonMaxHP') and self.item_quantity(18):
    self.use_item(18,True);continue
   for _ in range(8):
    x,y=self.read('wMenuCursorX')[0],self.read('wMenuCursorY')[0]
    if (x,y)==(2,2):break
    self.press('right' if x<2 else 'down',30)
   old=self.menus;self.phase,self.context='run_pending',None;self.press('a',30)
   self.wait(lambda:self.menus>old and self.phase=='battle' or not self.read('wBattleMode')[0],buttons=True)
  assert self.read('wBattleMode')==[0] and self.read('wBattleResult')==[2],('ordinary RUN failed',label,self.read('wBattleResult'))
  self.close_dialogue();assert self.read('wEventFlags',256)==before['flags'] and self.experience()==before['xp'] and self.money()==before['money']
  assert self.map()==before['map'];self.phase,self.context='overworld',None
  self.capture(label+'_native_run_no_retirement');self.flees.append({'label':label,'ordinary_run':True,'flags_xp_money_unchanged':True})
 def move_egress(self,number,index,label):
  old=self.position();key=EGRESS[(number,index)];dx,dy=next((dx,dy) for k,dx,dy in DIRECTIONS if k==key)
  target=(old[0]+dx,old[1]+dy);assert self.collision_at(*target)=='FLOOR'
  self.walk(key);assert self.map()==number and self.position()==target,('arrival rewarp trap',number,index,old,target,self.map(),self.position())
  self.settle(label+'_egress_guard');return self.world(label+'_egress')
 def normal_portal(self,target,destnum,label):
  try:self.navigate(target,destnum)
  except AssertionError as error:
   if 'no safe path' not in str(error):raise
   # A living aggressor can guard the approach to a valid warp lane.
   # Enter the real adjacent guard coordinate, use native RUN, then walk on.
   name=MAPS[self.map()][0];warps=warp_tiles(name);occupied={a['xy'] for a in self.live_actors(name)}
   options=[]
   for _,dx,dy in DIRECTIONS:
    stand=(target[0]+dx,target[1]+dy)
    if stand in warps or stand in occupied or self.collision_at(*stand)=='WALL':continue
    try:route=self.path(stand)
    except AssertionError:continue
    options.append((len(route),stand))
   assert options,('no guarded ordinary approach',name,target)
   stand=min(options)[1];self.navigate(stand);self.settle(label+'_approach_guard')
   diagnostic={'map':name,'target':list(target),'stand':list(stand),'collision':self.collision_at(*target),'live_actors':self.live_actors(name),'first_path_refusal':str(error)}
   self.capture(label+'_adjacent_ordinary_entry');self.inputs.append({'native_lane_diagnostic':diagnostic})
   delta=(target[0]-stand[0],target[1]-stand[1]);key=next(k for k,dx,dy in DIRECTIONS if (dx,dy)==delta)
   self.inputs.append({'frame':self.p.frame_count,'key':key,'button_delay':30,'tick_frames':150,'native_adjacent_lane_entry':True})
   self.p.button(key,delay=30);self.p.tick(150,True)
   assert self.map()==destnum,('ordinary adjacent lane entry failed',diagnostic,destnum,self.map(),self.position())
 def cross(self,number,index,lane,label,required=True):
  t=threshold(number,index);target=tuple(t['cells'][lane]);dest={v:k for k,v in art.CONSTANTS.items()}[t['destination']]
  destnum=list(art.native.DIMS).index(dest)+12;expected=tuple(threshold(destnum,t['destination_index'])['original_xy'])
  assert self.map()==number
  self.world(label+'_approach');self.normal_portal(target,destnum,label);self.settle(label+'_arrival_guard')
  assert self.position()==expected,(label,'wrong landing',expected,self.position())
  arrival=self.world(label+'_arrival');egress=self.move_egress(destnum,t['destination_index'],label)
  record={'required_lane_case':required,'source_map':number,'source_index':index,'lane':lane,'activation_xy':list(target),'target_map':destnum,'expected_landing':list(expected),'actual_landing':arrival['xy'],'ordinary_egress_xy':egress['xy']}
  self.crossings.append(record);(self.folder/'partial.json').write_text(json.dumps({'crossings':self.crossings,'checks':self.checks,'flees':self.flees},indent=2)+'\n')
 def pair(self,number,index,label):
  t=threshold(number,index);dest={v:k for k,v in art.CONSTANTS.items()}[t['destination']];destnum=list(art.native.DIMS).index(dest)+12
  for lane in (0,1):
   self.cross(number,index,lane,label+'_A_'+str(lane));self.cross(destnum,t['destination_index'],lane,label+'_B_'+str(lane))
 def cold(self,number):
  self.p.tick(1800,True);self.press('start')
  for _ in range(30):
   if self.map()==number and self.read('wScriptMode')==[0]:break
   self.press('a',180)
  assert self.map()==number and self.read('wScriptMode')==[0];self.phase,self.context='overworld',None;self.world('private_native_cold_continue')

def main():
 logging.disable(logging.CRITICAL);assert hashlib.sha256(FROZEN.read_bytes()).hexdigest()==EXPECTED
 provenance=json.loads((ROOT/'references/generated/recruitment_v029/team_runtime/validation.json').read_text())
 # The retained report records this as actual native-saved, ordinary progression.
 def find(v):
  if isinstance(v,dict):
   if v.get('battery_path')=='/tmp/peon_v029_senjin_warlock.ram':return v
   for x in v.values():
    r=find(x)
    if r:return r
  if isinstance(v,list):
   for x in v:
    r=find(x)
    if r:return r
 source=find(provenance);assert source and source['ordinary_buttons_only'] and not source['ram_edits'] and not source['emulator_states_loaded']
 battery=Path(source['battery_path']);assert hashlib.sha256(battery.read_bytes()).hexdigest()==source['battery_sha256']
 report={'rom_sha256':EXPECTED,'ordinary_controls_only':True,'ram_writes':False,'save_states':False,'cpu_substitution':False,'user_saves_opened':False,'private_native_battery_provenance':source,'status':'RUNNING'}
 with tempfile.TemporaryDirectory(prefix='peon-v0213-east-ordinary-') as temp:
  rom=Path(temp)/'east.gbc';shutil.copyfile(FROZEN,rom);shutil.copyfile(battery,Path(str(rom)+'.ram'))
  s=PortalSession(rom,symbols(SYM))
  try:
   s.cold(17);s.pair(17,1,'senjin_road')
   s.navigate((10,4),16);s.move_egress(16,2,'route_road');s.navigate((12,4),18);s.move_egress(18,1,'route_razor')
   s.pair(18,1,'razor_road');s.pair(18,2,'razor_gate')
   # Return from the northern town, then cross the guarded road canyon normally.
   s.navigate((12,16),16);s.move_egress(16,3,'route_road_west')
   s.navigate((4,14),29);s.move_egress(29,2,'route_exit_east')
   s.pair(29,2,'exit_road')
   # The Kolkar pack remains alive; traverse each actual guarded coordinate
   # with ordinary RUN, retaining its retirement flags and all rewards.
   for point in ((7,4),(6,4),(5,4),(4,4),(3,4),(2,4),(1,4)):
    s.navigate(point);s.settle('kolkar_travel_'+str(point[0]))
   s.cross(29,1,0,'route_valley',False);s.pair(15,2,'valley_exit')
   s.cross(15,1,0,'route_den',False);s.pair(14,1,'den_valley')
   # Generate a new private battery with the exact current cartridge and
   # actual SAVE menu, then use it for candidate2's independent cold proof.
   s.cross(14,1,0,'route_save_valley',False);s.cross(15,2,0,'route_save_exit',False)
   for point in ((3,4),(4,4),(5,4),(6,4),(7,4),(8,4)):
    s.navigate(point);s.settle('kolkar_return_'+str(point[0]))
   s.cross(29,2,0,'route_save_road',False);s.cross(16,2,0,'route_save_senjin',False)
   s.navigate((7,9));s.world('complete_canonical_palm_senjin')
   saved={'count':0};s.p.hook_register(*s.sym['_SaveGameData'],lambda _:saved.__setitem__('count',saved['count']+1),None)
   s.press('start')
   choices=s.read('wMenuItemsList',s.read('wMenuItemsList')[0]+1)[1:];index=choices.index(4)+1
   for _ in range(16):
    cursor=s.read('wMenuCursorPosition')[0]
    if cursor==index:break
    s.press('up' if cursor>index else 'down',30)
   s.press('a')
   for _ in range(12):
    s.press('a',180)
    if saved['count'] and s.read('wScriptMode')==[0]:break
   assert saved['count']==1;s.p.stop(save=True);s.p=None
   generated=OUT/'ordinary_6cf_senjin.ram';shutil.copyfile(Path(str(rom)+'.ram'),generated)
   report['generated_private_native_save']={'path':str(generated),'sha256':hashlib.sha256(generated.read_bytes()).hexdigest(),'native_save_calls':1,'state_edits':False}
   report['status']='PASS'
  except Exception as e:
   report['failure']=repr(e);s.capture('first_failure');raise
  finally:
   report.update(crossings=s.crossings,allocator_checks=s.checks,captures=s.captures,normal_runs=s.flees,inputs=s.inputs,final_map=s.map() if s.p else 17,final_xy=list(s.position()) if s.p else [7,9])
   (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
   if s.p:s.p.stop(save=False)
 print(json.dumps({'status':report['status'],'required_crossings':len(report['crossings']),'allocator_checks':len(report['allocator_checks'])}))
if __name__=='__main__':main()
