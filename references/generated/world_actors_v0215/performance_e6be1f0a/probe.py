from pathlib import Path
import sys, json, logging, shutil, tempfile, hashlib, statistics, traceback
sys.path.insert(0, '/workspace/peon-of-warcraft/tools')
from validate_peon_earth_stone_v0212 import EarthSession
from validate_peon_exit_title import symbols
from validate_peon_masters_sleeping_v0213 import MasterSession
ROOT=Path('/workspace/peon-of-warcraft')
OUT=Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'references/generated/world_actors_v0215/performance_11cdb90b'
OUT.mkdir(parents=True,exist_ok=True)
logging.disable(logging.CRITICAL)
class Perf(MasterSession):
 def __init__(self,*a):
  self.profile_on=False;self.durations=[];self.entries=[];self.pending=None;self.state_mismatches=[];self.dma_uploads=0;self.dma_wait_records=[];self.dma_wait_pending=None;self.profile_counts={}
  super().__init__(*a)
 def open(self):
  super().open()
  self.p.hook_register(*self.sym['_UpdateSprites'],self.begin,None)
  if 'PeonInitLargeWorldSpritesV0215' in self.sym:self.p.hook_deregister(*self.sym['_UpdateSprites.fill'])
  self.p.hook_register(*self.sym['_UpdateSprites.fill'],self.finish,None)
  if 'PeonUploadLargeWorldFrameGDMAHomeV0215' in self.sym:
   self.p.hook_register(*self.sym['PeonUploadLargeWorldFrameGDMAHomeV0215'],self.upload_begin,None)
   self.p.hook_register(*self.sym['PeonUploadLargeWorldFrameGDMAHomeV0215.done'],self.upload_end,None)
   for label in ['PeonBuildLargeWorldCandidateV0215','PeonReadLargeWorldMaskV0215','PeonAdmitWorldCandidateV0215','PeonAdmitWorldCandidateV0215.commit_rows','PeonCommitStreamedCandidateRowsV0215']:
    if label in self.sym:self.p.hook_register(*self.sym[label],self.count_function,label)
 def count_function(self,label):
  if not self.profile_on:return
  index=self.read('wPeonLargeObjectIndexV0215')[0]
  if label=='PeonReadLargeWorldMaskV0215':
   key=self.read('wPeonLargeCacheKeyV0215')[0];frame=self.read('wPeonLargeFrameV0215')[0]
   warm=(self.read('wPeonLargeMetadataIDsV0215',13)[index]==key and self.read('wPeonLargeMetadataFramesV0215',13)[index]==frame)
   label='metadata_warm' if warm else 'metadata_cold'
  elif label=='PeonAdmitWorldCandidateV0215':
   label='admit_nonzero' if self.read('wPeonLargeCandidateBytesV0215')[0] else 'admit_zero'
  elif label=='PeonCommitStreamedCandidateRowsV0215':
   label='admitted'
  elif label.endswith('.commit_rows'):
   span=self.read('wPeonLargeCandidateMaxYV0215')[0]-self.read('wPeonLargeCandidateMinYV0215')[0]
   if self.p.register_file.B!=span:return
   label='admitted'
  group=self.profile_counts.setdefault(label,{})
  group[index]=group.get(index,0)+1
 def upload_begin(self,_):
  self.dma_uploads+=1
  if self.profile_on:self.dma_wait_pending=(self.p._cycles(),self.p.frame_count,self.read('wPeonLargeObjectIndexV0215')[0],self.read('wPeonLargeFrameV0215')[0])
 def upload_end(self,_):
  if self.profile_on and self.dma_wait_pending:
   cycles,frame,index,pose=self.dma_wait_pending
   self.dma_wait_records.append({'object':index,'frame':pose,'elapsed_tcycles':self.p._cycles()-cycles,'elapsed_lcd_frames':self.p.frame_count-frame})
   self.dma_wait_pending=None
 def begin(self,_):
  if self.profile_on:
   self.pending=(self.p._cycles(),self.p.frame_count,self.read('hObjectStructIndex')[0],self.p.memory[0xff70])
   self.entries.append(self.p._cycles())
 def finish(self,_):
  if 'PeonInitLargeWorldSpritesV0215' in self.sym and self.map()==22 and self.read('wBackupMapNumber')==[14]:
   self.lodge_oam_generation+=1
   shadow=self.read('wShadowOAM',160)
   for offset in range(self.read('hUsedSpriteIndex')[0],160,4):shadow[offset]=160
   self.lodge_completed_oam=shadow
  if self.profile_on and self.pending:
   cycles,frame,index,wbk=self.pending
   self.durations.append(self.p._cycles()-cycles)
   actual=(self.read('hObjectStructIndex')[0],self.p.memory[0xff70])
   if actual!=(index,wbk):self.state_mismatches.append([index,wbk,*actual])
   self.pending=None
 def press(self,key,frames=90):
  if (key not in ('up','down','left','right') or self.presentation!='world' or self.read('wScriptMode')!=[0] or self.map() not in (14,22)):
   return super().press(key,frames)
  self.p.button(key,delay=12);self.p.tick(frames,True)
 def capture(self,label):
  self.p.screen.image.save(self.folder/(label+'.png'))
 def sample(self,label,frames=240,key=None):
  self.p.tick(30,True);self.durations=[];self.entries=[];self.state_mismatches=[];self.pending=None
  before_uploads=self.dma_uploads;start_cycles=self.p._cycles();start=self.position();changes=[];oam=[]
  self.profile_on=True
  if key:self.p.button_press(key)
  for n in range(frames):
   self.p.tick(1,True)
   pos=self.position()
   if not changes or changes[-1][1]!=pos:changes.append((n,pos,self.p._cycles()))
   raw=list(self.p.memory[0xfe00:0xfea0]);vis=[(raw[i]-16,raw[i+1]-8,raw[i+2],raw[i+3]) for i in range(0,160,4) if 0<raw[i+1]<168 and 8<raw[i]<160]
   line=max(sum(y<=r<y+8 for y,x,t,f in vis) for r in range(144)) if vis else 0
   oam.append((len(vis),line))
   assert line<=10,('scanline violation',label,n,line)
   if self.read('wBattleMode')[0] or self.read('wScriptMode')[0]:raise AssertionError(('Unwanted dialogue/battle',label,self.position()))
  if key:self.p.button_release(key)
  self.profile_on=False;self.capture(label)
  diffs=[b-a for a,b in zip(self.entries,self.entries[1:])]
  def stats(v):return {'samples':len(v),'median':statistics.median(v) if v else None,'mean':statistics.mean(v) if v else None,'min':min(v) if v else None,'max':max(v) if v else None}
  return {'frames':frames,'cpu_speed_register':self.p.memory[0xff4d], 'position_before':start,'position_after':self.position(),'position_changes':changes,'sprite_update_duration_tcycles':stats(self.durations),'sprite_update_interval_tcycles':stats(diffs),'sprite_updates':len(self.entries),'gdma_frame_uploads':self.dma_uploads-before_uploads,'maximum_visible_oam':max(x[0] for x in oam),'maximum_objects_per_scanline':max(x[1] for x in oam),'register_state_mismatches':self.state_mismatches}
 def short_steps(self):
  result=[]
  for key in ['left','right','up','down','left','right','up','down'][:4 if len(sys.argv)>5 else 8]:
   self.p.tick(30,True);before=self.position();cycles=self.p._cycles();changes=[];ends=[];self.durations=[];self.entries=[];self.pending=None;self.state_mismatches=[];self.profile_on=True
   before_uploads=self.dma_uploads;self.dma_wait_records=[];self.dma_wait_pending=None;self.profile_counts={}
   self.p.button_press(key)
   for n in range(500):
    self.p.tick(1,True)
    if self.position()!=before:
     self.p.button_release(key);changes.append(n+1);break
   else:raise AssertionError(('Step did not move',key,before))
   for n in range(120):
    self.p.tick(1,True)
    if self.read('wPlayerStepFlags')[0] == 0:ends.append(n+1);break
   self.profile_on=False
   result.append({'key':key,'before':before,'after':self.position(),'lcd_frames_until_map_coord_changed':changes[0],'duration_tcycles_to_change':self.p._cycles()-cycles,'update_duration_tcycles':self.durations,'gdma_frame_uploads':self.dma_uploads-before_uploads,'gdma_wait_records':self.dma_wait_records,'function_counts':self.profile_counts,'register_state_mismatches':self.state_mismatches})
  return result
for version,path in [('v0215',Path(sys.argv[1]) if len(sys.argv)>1 else Path('/tmp/peon-v0215-candidate2/peon_v0215.gbc')),('v0214',Path('/tmp/peon-v0214-candidate1/peon_v0214.gbc'))]:
 if len(sys.argv)>3 and version != sys.argv[3]:continue
 for index,name in [(0,'shaman'),(2,'warlock')]:
  if len(sys.argv)>4 and name!=sys.argv[4]:continue
  with tempfile.TemporaryDirectory(prefix='peon-world-perf-') as td:
   rom=Path(td)/'private.gbc';shutil.copyfile(path,rom)
   folder=OUT/version;folder.mkdir(exist_ok=True)
   s=Perf(rom,symbols(path.with_suffix('.sym')),index,folder)
   report={'rom_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'ordinary_buttons_only':True,'ram_edits':False,'user_battery_opened':False,'emulator_states_loaded':False,'class':name,'samples':{},'status':'RUNNING'}
   try:
    s.fresh_class();s.p.tick(120,True);print(version,name,'fresh',s.position(),flush=True)
    report['samples']['den_spawn_idle']=s.sample('den_spawn_idle')
    report['samples']['short_steps']=s.short_steps();print(version,name,'steps_done',s.position(),report['samples']['den_spawn_idle']['sprite_update_duration_tcycles'],[x['lcd_frames_until_map_coord_changed'] for x in report['samples']['short_steps']],flush=True)
    if len(sys.argv)>5 and sys.argv[5]=='quick':
     report['status']='PASS';continue
    if len(sys.argv)<=5:
     s.navigate((10,11));report['samples']['den_dense_idle']=s.sample('den_dense_idle');print(version,name,'dense_done',flush=True)
    s.navigate((5,7),22);s.navigate((5,5));report['samples']['three_masters_idle']=s.sample('three_masters_idle');print(version,name,'lodge_done',flush=True)
    # Blocked table forces turn in place: compare facing changes, no movement or script.
    s.press('left',30);s.p.tick(60,True);report['samples']['lodge_after_turn']=s.sample('lodge_after_turn',frames=120)
    if 'PeonInitLargeWorldSpritesV0215' in s.sym:
     report['samples']['lodge_whole_body_scene']=s.master_scene();s.capture('lodge_whole_body_scene')
    report['status']='PASS'
   except Exception as e:
    report['status']='FAILED';report['error']=repr(e);report['traceback']=traceback.format_exc();report['final_state']={'map':s.map(),'position':s.position(),'presentation':s.presentation,'phase':s.phase,'pc':s.p.register_file.PC,'rombank':s.p.memory[0xff9d] if False else s.read('hROMBank'),'wram_bank':s.p.memory[0xff70]};s.capture('failure');print(version,name,'FAIL',traceback.format_exc(),flush=True)
   finally:
    s.p.stop(save=False);(folder/(name+'_validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print('ALL_FINISHED',flush=True)
