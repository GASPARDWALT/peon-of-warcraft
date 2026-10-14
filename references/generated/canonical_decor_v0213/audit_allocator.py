from pathlib import Path
import re,json
R=Path(__file__).resolve().parents[3]
types={'PEON_SPRITE':0,'WALKING_SPRITE':1,'STANDING_SPRITE':2,'STILL_SPRITE':3,'USER_WORLD_4DIR_SPRITE':4,'STATIC_MASTER_SPRITE':5};slot={0:32,1:12,2:12,3:4,4:16,5:9}
lines=[re.search(r'overworld_sprite\s+(\w+),\s*(\d+),\s*(\w+)',x).groups() for x in (R/'data/sprites/sprites.asm').read_text().splitlines() if re.search(r'^\s*overworld_sprite ',x)]
ids={};i=0
for x in (R/'constants/sprite_constants.asm').read_text().splitlines():
 x=x.split(';')[0].split()
 if not x:continue
 if x[0] in ('const_def','const_next'):i=int(x[1].replace('$','0x'),0) if len(x)>1 else 0
 elif x[0]=='const':ids[x[1]]=i;i+=1
for alias,real in re.findall(r'DEF (PEON_SPRITE_\w+) EQU (SPRITE_\w+)',(R/'constants/peon_constants.asm').read_text()):ids[alias]=ids[real]
names=('PeonOpening','TheDen','ValleyOfTrials','DurotarRoad','SenjinVillage','RazorHill','OrgrimmarGate','BurningBladeCavern','PeonValleyCrossroads','PeonHanazuaCamp','PeonSarkothBasin','PeonCaveApproach','PeonValleyExit')
reports=[]
for name in names:
 raw=re.findall(r'object_event\s+\d+,\s*\d+,\s*(\w+)',(R/f'maps/{name}.asm').read_text())
 records=[]
 for actor in dict.fromkeys(['SPRITE_CHRIS']+raw+['SPRITE_PEON_FRIENDLY_IMP']):
  if actor=='SPRITE_NONE':continue
  if actor.startswith('SPRITE_PEON_QUEST_'):typ=3;length=4;source='runtime quest-marker4tile'
  else:
   sprite=ids[actor];source,lengthstr,t=lines[sprite-1];typ=types[t];length=16 if typ in (0,4) else 9 if typ==5 else int(lengthstr)
  records.append({'actor':actor,'type':typ,'standing_length':length,'source':source})
 records.sort(key=lambda r:r['type']);offset=0;bank=1;walk=[]
 for rec in records:
  end=offset+slot[rec['type']]
  if bank==1 and end>128:bank=0;offset=0;end=slot[rec['type']]
  if end>128:break
  rec.update({'bank':bank,'standing_range':[hex(0x8000+offset*16),hex(0x8000+(offset+rec['standing_length'])*16-1)]})
  if bank==1 and rec['type'] in (0,1,2):
   length=32 if rec['type']==0 else rec['standing_length'];a,b=0x8800+offset*16,0x8800+(offset+length)*16-1
   assert b<0x8e00 or a>=0x8f80,(name,rec,a,b)
   rec['walking_range']=[hex(a),hex(b)];walk.append(b)
  offset=end
 reports.append({'map':name,'bank1_walking_highest_byte':hex(max(walk)),'allocated_sprites_including_optional_follower':records,'extra_background_range_unwritten_by_actors':True})
result={'allocation':'Read-only simulation of current native ArrangeUsedSprites and GetUsedSprite; includes all map-object sprite IDs regardless of visibility and optional Warlock follower. USER_WORLD_4DIR has no walking upload; bank0 never receives walking uploads. Quest marker variable IDs conservatively reserve their4tile objects.','extra_bank':1,'extra_physical_range':['$8e00','$8f7f'],'emote_physical_range':['$8f80','$8fff'],'portrait_cache':['bank1 $9600','$968f'],'font_cache':['bank1 $9690','$97ff'],'decompress_available_bytes':4096,'required216_bytes':3456,'maps':reports}
(R/'references/generated/canonical_decor_v0213/allocator_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print({r['map']:r['bank1_walking_highest_byte'] for r in reports})
