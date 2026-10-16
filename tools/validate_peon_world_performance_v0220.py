#!/usr/bin/env python3
"""Measure native world cadence with ordinary controls and read-only hooks.

Reports emulated CPU T-cycles and LCD frames, never host throughput. A fresh
private ROM copy is booted normally; no game RAM/register writes, fixtures,
save states or user batteries are used. Function timings include interrupts,
HALT/DelayFrame waits and nested callees; they must not be added together.
"""
from __future__ import annotations
import argparse, hashlib, json, logging, shutil, statistics, tempfile, traceback
from pathlib import Path
from validate_peon_masters_sleeping_v0213 import MasterSession
from validate_peon_exit_title import symbols

ROOT=Path(__file__).resolve().parents[1]
LABELS=(
 'HandleMapObjects','_UpdateSprites','InitSprites','PeonDrawPlayerHUD',
 'PeonInitLargeWorldSpritesV0215','PeonSnapshotWorldObjectsV0215',
 'PeonScoreWorldObjectsV0215','PeonChooseWorldObjectV0215',
 'PeonFindLargeWorldBindingV0215','PeonBuildLargeWorldCandidateV0215',
 'PeonBuildNativeWorldCandidateV0215','PeonReadLargeWorldMaskV0215',
 'PeonCopyCachedWorldMetadataV0215','PeonTranslateWorldRelativeOAMV0215',
 'PeonAdmitWorldCandidateV0215','PeonGroupStreamedCandidateRowsV0215',
 'PeonCheckStreamedCandidateRowsV0215','PeonCommitStreamedCandidateRowsV0215',
 'PeonEnsureLargeWorldFrameV0215','PeonUploadLargeWorldFrameGDMAHomeV0215',
 'PeonWorldHUDHasScanlineBudgetV0215','PeonUserWorldPaletteV0211',
 'PeonHUDGetHPFill','PeonGetHeroResourceBarFillV0213',
 'PeonDrawPlayerHUD.RaiseHUDPriority','HandleMapBackground',
 'HandleNPCStep','_HandlePlayerStep','DelayFrame','VBlank',
 '_UpdateSound','GameTimer','MobileTimer',
)

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def stats(values):
 return {'samples':len(values),'sum':sum(values),'min':min(values) if values else None,
         'median':statistics.median(values) if values else None,
         'mean':statistics.mean(values) if values else None,'max':max(values) if values else None}

def compiled_tables(rom,sym):
 def packet(label,size):
  bank,address=sym[label];offset=address if not bank else bank*0x4000+address-0x4000
  return rom[offset:offset+size]
 label='PeonLargeWorldDescriptorPointersV0220'
 if label not in sym:return {'present':False,'baseline_linear_lookup':True}
 bank,address=sym['PeonLargeWorldBindingsV0215'];expected=[0]*256;entries=0
 while True:
  offset=bank*0x4000+address-0x4000;key=rom[offset]
  if key==255:break
  assert not expected[key],('Duplicate ordinary descriptor sprite',key)
  expected[key]=address;entries+=1;address+=8
 assert sym[label][0]==bank==sym['PeonFindLargeWorldBindingV0215'][0]
 actual=packet(label,512)
 assert actual==b''.join(pointer.to_bytes(2,'little') for pointer in expected),'Compiled direct-descriptor table differs from canonical binding order'
 flags=packet('PeonLargeWorldWalkFlagsV0220',256)
 assert len(flags)==256 and set(flags)<={0,1},'Compiled gait flags are not256booleans'
 assert all(flags[key] for key in (0x23,0x24,0x28,0x2c)),'Existing Kolkar/crawler/Yarrog gait was disabled'
 return {'present':True,'ordinary_descriptor_entries':entries,'all_256_pointers_exact':True,
  'same_renderer_rom_bank':True,'walk_flags_boolean':True,
  'enabled_sprite_ids':[i for i,enabled in enumerate(flags) if enabled],
  'retained_legacy_npc_gaits':True}

class PerformanceSession(MasterSession):
 def __init__(self,*args,detailed=False):
  self.detailed=detailed
  self.profile=False;self.hook_errors=[];self.dispatch={};self.pending=[];self.records=[]
  self.entry_times={};self.sample_frames=[];self.generation=0
  super().__init__(*args)
 def open(self):
  super().open()
  # This inherited observer is only for old source-art checks, unused here.
  if 'PeonInitLargeWorldSpritesV0215' in self.sym:
   self.p.hook_deregister(*self.sym['_UpdateSprites.fill'])
  self.dispatch={};self.pending=[]
  if self.detailed:
   for label in LABELS:
    if label in self.sym:self.add_hook(self.sym[label],lambda label=label:self.enter(label))
  else:
   self.fixed_region('_UpdateSprites','_UpdateSprites.fill')
   self.fixed_region('PeonDrawPlayerHUD','PeonDrawPlayerHUD.done')
   if 'PeonInitLargeWorldSpritesV0215' in self.sym:
    bank,address=self.sym['InitSprites']
    self.fixed_region('InitSprites',(bank,address+3))
    self.fixed_region('PeonInitLargeWorldSpritesV0215','PeonInitLargeWorldSpritesV0215.done')
    self.fixed_region('PeonUploadLargeWorldFrameGDMAHomeV0215','PeonUploadLargeWorldFrameGDMAHomeV0215.done')
   else:
    bank,address=self.sym['InitSprites.DeterminePriorities']
    self.fixed_region('InitSprites',(bank,address-1),16)
   bank,address=self.sym['DelayFrames']
   self.fixed_region('DelayFrame',(bank,address-1),16)
   bank,address=self.sym['VBlankHandlers']
   self.fixed_region('VBlank',(bank,address-1),16)
   bank,address=self.sym['GameTimer.Function']
   self.fixed_region('GameTimer',(bank,address-1),16)
   for label in ('_UpdateSound','MobileTimer','HandleMapObjects','HandleMapBackground'):
    if label in self.sym:self.add_hook(self.sym[label],lambda label=label:self.entry_times.setdefault(label,[]).append(self.p._cycles()))
 def fixed_region(self,label,end,end_cost=0):
  target=self.sym[end] if isinstance(end,str) else end
  self.add_hook(target)
  def begin():
   self.pending.append({'label':label,'cycles':self.p._cycles(),'frame':self.p.frame_count,
                        'return_address':target,'return_sp':None,'end_instruction_tcycles':end_cost})
   self.entry_times.setdefault(label,[]).append(self.p._cycles())
  self.add_hook(self.sym[label],begin)
 def add_hook(self,address,callback=None):
  if address not in self.dispatch:
   self.dispatch[address]=[]
   try:self.p.hook_register(*address,self.observe,address)
   except Exception:
    self.dispatch.pop(address);raise
  if callback is not None:self.dispatch[address].append(callback)
 def observe(self,address):
  try:
   if not self.profile:return
   sp=self.p.register_file.SP;cycles=self.p._cycles()
   closed=[]
   for record in self.pending:
    if record['return_address']==address and record['return_sp'] in (None,sp):
     record['tcycles']=cycles-record['cycles']+record.get('end_instruction_tcycles',0);record['lcd_frames']=self.p.frame_count-record['frame']
     if record['label']=='GameTimer':record['game_time_frames_after']=self.game_time_frames()
     self.records.append(record);closed.append(record)
   for record in closed:self.pending.remove(record)
   for callback in self.dispatch[address]:callback()
  except Exception as error:self.hook_errors.append({'address':address,'error':repr(error)})
 def enter(self,label):
  cycles=self.p._cycles();sp=self.p.register_file.SP
  if label=='MobileTimer':
   # Count the hardware timer IRQ without return-PC instrumentation.
   self.entry_times.setdefault(label,[]).append(cycles)
   return
  if label=='VBlank':
   # A fixed RETI observer avoids installing return-PC breakpoints at
   # arbitrary interrupted instructions. Include the native RETI's16T.
   bank,address=self.sym['VBlankHandlers'];ret=(bank,address-1)
   offset=address-1 if not bank else bank*0x4000+address-1-0x4000
   assert self.rom_bytes[offset]==0xd9,'Expected VBlank RETI immediately before handlers'
   self.add_hook(ret)
   self.pending.append({'label':label,'cycles':cycles,'frame':self.p.frame_count,
                        'return_address':ret,'return_sp':sp,'end_instruction_tcycles':16})
   self.entry_times.setdefault(label,[]).append(cycles)
   return
  pc=self.p.memory[sp] | self.p.memory[(sp+1)&65535]<<8
  bank=0 if pc<0x4000 else self.read('hROMBank')[0]
  ret=(bank,pc)
  assert pc<0x8000,('Return outside ROM',label,sp,ret)
  self.add_hook(ret)
  self.pending.append({'label':label,'cycles':cycles,'frame':self.p.frame_count,
                       'return_address':ret,'return_sp':(sp+2)&65535})
  self.entry_times.setdefault(label,[]).append(cycles)
 def capture(self,label):
  self.p.screen.image.save(self.folder/(label+'.png'))
 def tick(self,frames=1):
  self.p.tick(frames,True)
  assert not self.hook_errors,('Read-only profile hooks failed',self.hook_errors)
 def begin_sample(self):
  self.profile=False;self.tick(30);self.pending=[];self.records=[];self.entry_times={};self.profile=True
  return self.p._cycles()
 def finish_sample(self,start):
  elapsed=self.p._cycles()-start;self.profile=False
  expected_speed=getattr(self,'expected_cpu_speed',None)
  if expected_speed:
   assert bool(self.p.memory[0xff4d]&128)==(expected_speed=='double'),('Unexpected hardware CPU speed',expected_speed,self.p.memory[0xff4d])
  blockers=[r for r in self.records if r['label'] in ('DelayFrame','VBlank')]
  def blocked_time(record, labels):
   lo,hi=record['cycles'],record['cycles']+record['tcycles'];spans=[]
   for blocker in blockers:
    if blocker['label'] not in labels:continue
    a,b=max(lo,blocker['cycles']),min(hi,blocker['cycles']+blocker['tcycles'])
    if a<b:spans.append((a,b))
   total=0;end=lo
   for a,b in sorted(spans):
    if b>end:total+=b-max(a,end);end=b
   return total
  groups={}
  for label in LABELS:
   entries=self.entry_times.get(label,[]);records=[r for r in self.records if r['label']==label]
   if entries:
    groups[label]={'calls':len(entries),'completed_calls':len(records),
       'inclusive_tcycles':stats([r['tcycles'] for r in records]),
       'inclusive_lcd_frames':stats([r['lcd_frames'] for r in records]),
       'VBlank_interrupt_tcycles':stats([blocked_time(r,('VBlank',)) for r in records]),
       'outside_DelayFrame_and_VBlank_tcycles':stats([r['tcycles']-blocked_time(r,('DelayFrame','VBlank')) for r in records]),
       'entry_interval_tcycles':stats([b-a for a,b in zip(entries,entries[1:])]),
       'inclusive_share_of_sample':sum(r['tcycles'] for r in records)/elapsed}
  return {'elapsed_tcycles':elapsed,'cpu_speed_KEY1':self.p.memory[0xff4d],
          'cpu_double_speed':bool(self.p.memory[0xff4d]&128),'functions':groups,
          'inflight_calls_excluded':len(self.pending),'hook_errors':self.hook_errors}
 def visible_oam(self):
  raw=list(self.p.memory[0xfe00:0xfea0]);cells=[tuple(raw[i:i+4]) for i in range(0,160,4) if 8<raw[i]<160 and 0<raw[i+1]<168]
  scanlines=[sum(y<=row+16<y+8 for y,x,tile,attr in cells) for row in range(144)]
  assert len(cells)<=40 and max(scanlines,default=0)<=10,('Native OAM limit',cells,scanlines)
  return {'cells':len(cells),'maximum_scanline':max(scanlines,default=0)}
 def motion(self):
  obj=self.read('wObjectStructs',40)
  return {'xy':list(self.position()),'step_flags':self.read('wPlayerStepFlags')[0],
    'native_player_event':self.read('wScriptRunning')[0],
    'native_script_mode':self.read('wScriptMode')[0],
    'camera_SCX_SCY':[self.p.memory[0xff43],self.p.memory[0xff42]],
    'object_pixels_offsets':obj[23:27],'facing':obj[13],
    'object_step_duration':obj[12]}
 def game_time_frames(self):
  hours=int.from_bytes(bytes(self.read('wGameTimeHours',2)),'big')
  return (((hours*60+self.read('wGameTimeMinutes')[0])*60+self.read('wGameTimeSeconds')[0])*60+self.read('wGameTimeFrames')[0])
 def idle(self,label,frames=240):
  start=self.begin_sample();before=self.position();occupancy=[];game_time_before=self.game_time_frames()
  assert self.read('hMobile')==[0],'Mobile serial mode is outside world timing scope'
  for _ in range(frames):
   self.tick();occupancy.append(self.visible_oam())
   assert not self.read('wScriptMode')[0] and not self.read('wBattleMode')[0]
  report=self.finish_sample(start)
  sound_calls=report['functions']['_UpdateSound']['calls']
  clock_delta=self.game_time_frames()-game_time_before
  clocks=[r['game_time_frames_after'] for r in self.records if r['label']=='GameTimer' and 'game_time_frames_after' in r]
  assert sound_calls==frames,('Native sound update cadence differs from LCD frames',label,sound_calls,frames)
  # A tick returns at the LCD boundary, possibly before the current VBlank
  # reaches GameTimer (which follows audio). Prove every complete IRQ clock
  # increment, and account for at most one boundary IRQ rather than calling
  # that phase offset a tempo change.
  assert len(clocks)>=frames-1,('GameTimer missed LCD interrupts',label,len(clocks),frames)
  assert all(b-a==1 for a,b in zip(clocks,clocks[1:])),('GameTimer did not increment exactly one native frame',label,clocks)
  assert abs(clock_delta-frames)<=1,('GameTimer frame cadence changed',label,clock_delta,frames)
  report.update({'label':label,'lcd_frames':frames,'before':before,'after':self.position(),
   'sound_updates_per_lcd_frame':sound_calls/frames,'game_time_frame_delta':clock_delta,
   'complete_GameTimer_calls':len(clocks),'each_GameTimer_increment_exactly_one_frame':True,
   'LCD_boundary_may_precede_final_GameTimer_by_one_IRQ':clock_delta!=frames,
   'mobile_mode_inactive':True,'hardware_RTC_or_serial_link_not_tested':True,
   'maximum_visible_oam':max(r['cells'] for r in occupancy),
   'maximum_objects_per_scanline':max(r['maximum_scanline'] for r in occupancy)})
  self.capture(label)
  return report
 def single_step(self,key):
  start=self.begin_sample();before=self.position();origin=self.motion();changes=[]
  first_motion=first_camera=first_facing=coord_change=settled=None;released=False;turn_script_frames=0
  self.p.button_press(key)
  for frame in range(1,501):
   self.tick();current=self.motion()
   if not changes or changes[-1]['state']!=current:
    changes.append({'lcd_frame':frame,'elapsed_tcycles':self.p._cycles()-start,'state':current})
   if first_motion is None and (current['object_pixels_offsets']!=origin['object_pixels_offsets'] or current['step_flags']):
    first_motion=frame
   if first_camera is None and current['camera_SCX_SCY']!=origin['camera_SCX_SCY']:first_camera=frame
   if first_facing is None and current['facing']!=origin['facing']:first_facing=frame
   # Stop after the native walking code acknowledges one move. This avoids
   # queued second steps while respecting the game's actual input sampling.
   if not released and (current['step_flags']&0xe0 or self.position()!=before):
    self.p.button_release(key);released=True
   if coord_change is None and self.position()!=before:coord_change=frame
   if coord_change is not None and not current['step_flags']:
    settled=frame;break
   # A native direction change is itself player event9 and deliberately
   # executes ChangeDirectionScript/deactivatefacing3. Count that latency;
   # reject every other event or battle rather than treating it as movement.
   if current['native_script_mode']:
    assert current['native_player_event']==9,('Unexpected native script during step',key,current)
    turn_script_frames+=1
   assert not self.read('wBattleMode')[0],('Step triggered battle',key,current)
  self.p.button_release(key)
  report=self.finish_sample(start)
  assert coord_change is not None and settled is not None,('Native step did not finish',key,before,self.motion())
  after=self.position();assert sum(abs(a-b) for a,b in zip(before,after))==1,('Expected one16px native step',key,before,after)
  camera=[origin['camera_SCX_SCY']];camera_changes=[]
  for change in changes:
   value=change['state']['camera_SCX_SCY']
   if value!=camera[-1]:
    delta=[((b-a+128)%256)-128 for a,b in zip(camera[-1],value)]
    assert sum(abs(v) for v in delta)==2,('Camera is not moving at native2px per update',key,delta)
    camera.append(value);camera_changes.append({'lcd_frame':change['lcd_frame'],'delta':delta})
  assert len(camera_changes)==8,('One16px tile must use8native2px camera updates',key,camera_changes)
  report.update({'key':key,'before':before,'after':after,'lcd_frames_to_first_motion':first_motion,
   'lcd_frames_to_first_facing_change':first_facing,'native_direction_change_script_frames':turn_script_frames,
   'lcd_frames_to_first_camera_motion':first_camera,'lcd_frames_to_tile_coord_change':coord_change,
   'lcd_frames_to_step_flags_clear':settled,'motion_changes':changes,
   'native_camera_updates':camera_changes,'eight_native_2px_updates_per_16px_step':True})
  return report

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--rom',type=Path,required=True);parser.add_argument('--sym',type=Path,required=True)
 parser.add_argument('--expected-rom-sha256',required=True);parser.add_argument('--output',type=Path,required=True)
 parser.add_argument('--frames',type=int,default=240);parser.add_argument('--include-lodge',action='store_true')
 parser.add_argument('--expected-cpu-speed',choices=('normal','double'))
 parser.add_argument('--detailed-profile',action='store_true',help='Dynamic return hooks for initial hotspot investigation; fixed boundaries are the default')
 args=parser.parse_args();logging.disable(logging.CRITICAL)
 assert digest(args.rom)==args.expected_rom_sha256,'Unexpected ROM candidate'
 args.output.mkdir(parents=True,exist_ok=True)
 report={'status':'RUNNING','rom_sha256':digest(args.rom),'sym_sha256':digest(args.sym),
  'method':'Emulated CPU T-cycles and actual LCD frames; inclusive profile timings overlap and include interrupts/waits',
  'profile_boundaries':'dynamic_function_returns' if args.detailed_profile else 'fixed_native_labels',
  'host_fps_measured':False,'ordinary_buttons_only':True,'game_RAM_or_register_edits':False,
  'fixtures_or_emulator_states':False,'user_battery_opened':False,'samples':{}}
 session=None
 try:
  report['compiled_tables']=compiled_tables(args.rom.read_bytes(),symbols(args.sym))
  with tempfile.TemporaryDirectory(prefix='peon-world-perf-v0220-') as td:
   private=Path(td)/'private.gbc';shutil.copyfile(args.rom,private)
   session=PerformanceSession(private,symbols(args.sym),0,args.output,detailed=args.detailed_profile)
   session.expected_cpu_speed=args.expected_cpu_speed
   session.fresh_class();session.tick(120)
   print('fresh',session.map(),session.position(),flush=True)
   report['samples']['den_spawn_idle']=session.idle('den_spawn_idle',args.frames)
   print('idle',report['samples']['den_spawn_idle']['functions'].get('_UpdateSprites'),flush=True)
   report['samples']['steps']=[session.single_step(key) for key in ('left','right','up','down')]
   print('steps',[(x['key'],x['lcd_frames_to_first_motion'],x['lcd_frames_to_tile_coord_change'],x['lcd_frames_to_step_flags_clear']) for x in report['samples']['steps']],flush=True)
   session.navigate((10,11));report['samples']['den_dense_idle']=session.idle('den_dense_idle',args.frames)
   print('dense',session.map(),session.position(),flush=True)
   if args.include_lodge:
    session.navigate((5,7),22);print('lodge_entry',session.map(),session.position(),flush=True)
    session.navigate((5,5));report['samples']['three_masters_idle']=session.idle('three_masters_idle',args.frames)
   report['status']='PASS'
 except Exception as error:
  report['status']='FAIL';report['error']=repr(error);report['traceback']=traceback.format_exc()
  if session is not None:
   report['last_state']={'map':session.map(),'motion':session.motion(),'pc':session.p.register_file.PC,'hook_errors':session.hook_errors}
   session.capture('failure')
  raise
 finally:
  if session is not None:session.p.stop(save=False)
  assert digest(args.rom)==args.expected_rom_sha256,'Source ROM changed during measurement'
  (args.output/'performance.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'status':report['status'],'rom_sha256':report['rom_sha256'],'output':str(args.output/'performance.json')},indent=2))
if __name__=='__main__':main()
