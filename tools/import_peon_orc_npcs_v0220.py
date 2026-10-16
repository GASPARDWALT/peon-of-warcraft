#!/usr/bin/env python3
"""Derive complete native32 NPC artwork and authored walk cels from source art.

Original/user PNGs and v19 packets remain read-only. This is a lossy nearest
source-art conversion, not recovery of a native source grid. Walk edits move
actual source limb clusters and explicitly author alternating feet at 32px;
they are not source animation and are never claimed to be so.
"""
from __future__ import annotations
import copy, hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from peon_native32_material_fit_v0220 import encode, render
from peon_world_readability_profile_v0219 import PALETTES
from import_peon_world_actors_v0215 import decode
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/world_native_v0220'
OUT=ROOT/'references/generated/world_native_v0220/orc_npcs'
DIRS=('front','back','left','right')
TOWNS='assets/world_native_v0220/originals/orc_townsfolk_generated_source.png'
SPECIAL='assets/world_native_v0220/originals/orc_specialists_generated_source.png'
# Source-component bounds measured using the actual source alpha>=128.
SPECS={
 'orc_merchant':(TOWNS,[(62,26,336,381),(441,25,708,381),(818,25,1026,382),(1188,25,1397,382)],'merchant'),
 'peon_worker':(TOWNS,[(53,396,321,726),(442,396,703,727),(842,402,1016,727),(1205,402,1381,727)],'worker'),
 'orc_guard':(TOWNS,[(22,739,337,1064),(451,743,746,1064),(778,737,1025,1064),(1193,737,1439,1064)],'guard'),
 'beast_handler':(SPECIAL,[(59,11,332,379),(450,14,706,379),(795,17,1050,379),(1164,16,1420,379)],'hunter'),
 'shaman_apprentice':(SPECIAL,[(41,392,317,725),(457,395,696,725),(787,396,1052,726),(1191,396,1436,726)],'apprentice'),
 'veteran_questgiver':(SPECIAL,[(52,730,332,1074),(441,731,710,1074),(837,735,1032,1074),(1195,734,1391,1074)],'veteran'),
}
IDENTITIES={
 'orc_merchant':'Whole broad merchant WORLD design: tied brown hair, focused ivory eyes and tusks, green face and curved forearms, crossed leather vest, ivory apron, waist buckle, complete leather pouches and separate boots.',
 'peon_worker':'Whole compact worker WORLD design: short dark crest, broad green face and focused eyes/tusks, ivory work shirt, brown suspender straps, waist pouch, bent strong forearms and full work boots.',
 'beast_handler':'Complete hunter WORLD design: tied brown hair, focused orc eyes and tusks, curved held bow, shoulder quiver with pale arrow feathers, crossed brown leather, ivory fur trim, belt and separate boots.',
 'shaman_apprentice':'Complete apprentice WORLD design: green stitched hood and robe, green face with pale eyes and tusks, whole hooked staff with an attached green crystal, leather satchel and separate boots.',
 'veteran_questgiver':'Complete veteran WORLD design: tied gray hair and beard, readable green face with focused pale eyes and tusks, substantial leather pauldrons and crossed straps, ivory fur trim, belt pouch and complete boots.',
 'orc_guard':'Whole guard WORLD design: short crest, focused green orc face with pale eyes/tusks, steel/red pauldrons, brown crossed leather, complete axe and separate armored boots.',
}
def sha(data):return hashlib.sha256(data).hexdigest()
def rel(path):return path.relative_to(ROOT).as_posix()
def rows(ids):return [''.join('.123'[int(v)]for v in row)for row in ids]
def mask_of(ids):return sum(1<<t for t in range(16)if ids[t//4*8:t//4*8+8,t%4*8:t%4*8+8].any())

def fit_materials(canvas,d,kind,forced_attrs=None):
 """Keep real materials, expression and alpha within existing OBJ palettes."""
 a=np.asarray(canvas);ids=np.zeros((32,32),dtype='uint8');attrs=[];scores=[]
 for t in range(16):
  yy,xx=divmod(t,4);ys=slice(yy*8,yy*8+8);xs=slice(xx*8,xx*8+8)
  rgb=a[ys,xs,:3].astype('int32')>>3;visible=a[ys,xs,3]>0
  skin=visible&(rgb[:,:,1]>rgb[:,:,0]*1.08)&(rgb[:,:,1]>rgb[:,:,2]*1.35)&(rgb[:,:,1]>9)
  pale=visible&(rgb[:,:,0]>=21)&(rgb[:,:,1]>=20)&(rgb[:,:,2]>=14)
  red=visible&(rgb[:,:,0]>rgb[:,:,1]*1.8)&(rgb[:,:,0]>rgb[:,:,2]*1.3)&(rgb[:,:,0]>10)
  brown=visible&(rgb[:,:,0]>rgb[:,:,1]*1.10)&(rgb[:,:,0]>rgb[:,:,2]*1.2)&(rgb[:,:,0]>=4)&~pale&~red
  dark=visible&(rgb.max(2)<7)&~brown
  steel=visible&(rgb.max(2)-rgb.min(2)<6)&(rgb.max(2)>=7)&~pale
  gy,gx=np.mgrid[yy*8:yy*8+8,xx*8:xx*8+8]
  face_low,face_high=(9,15)if kind=='merchant' else (6,14)
  face=(gy>=face_low)&(gy<=face_high)&(gx>=8)&(gx<=24)if d!='back' else np.zeros((8,8),bool)
  protected=pale&face;choices=(2,3,5,6,7)if kind=='guard'else(2,3,5,6)
  errors={};pixels={}
  for p in choices:
   pal=np.array(PALETTES[p][1:]);dist=((rgb[:,:,None,:]-pal)**2).sum(3).astype(float)
   cc=rgb*31/np.maximum(rgb.max(2,keepdims=True),1);pp=pal*31/np.maximum(pal.max(1,keepdims=True),1)
   hue=((cc[:,:,None,:]-pp)**2).sum(3);hue[:,:,2]=0;dist+=hue*np.where(rgb.sum(2)>12,1.2,0)[:,:,None]
   if p in(2,6):dist[:,:,0][skin]+=2400;dist[:,:,2][skin]+=2400
   elif skin.any():dist+=skin[:,:,None]*5000
   if p==2:dist[:,:,1][brown]+=4000;dist[:,:,2][brown]+=4000
   elif p==3:dist[:,:,0][brown]+=4000;dist[:,:,2][brown]+=4000
   else:dist+=brown[:,:,None]*5500
   if p in(3,5,6):dist[:,:,1][protected]+=2400;dist[:,:,2][protected]+=2400
   else:dist+=protected[:,:,None]*3000
   if p==5:dist[:,:,0][steel]+=200;dist[:,:,2][steel]+=1000
   elif kind=='guard':dist+=steel[:,:,None]*2500
   if p==7:dist[:,:,0][red]+=2000;dist[:,:,2][red]+=2000
   elif kind=='guard':dist+=red[:,:,None]*2000
   dist[:,:,0][dark]+=2500;dist[:,:,1][dark]+=2500
   weight=np.where(protected,10,np.where(skin,3,np.where(brown,3,np.where(dark,2,np.where(pale,5,1)))))
   errors[p]=float((dist.min(2)*weight)[visible].sum());pixels[p]=(dist.argmin(2)+1).astype('uint8')
  reason='weighted native material fit'
  if protected.any() and skin.sum()>=2 and yy==1:chosen=6;reason='source ivory eyes/tusks and green face'
  elif kind in('merchant','worker','hunter','apprentice','veteran')and pale.sum()>=4 and skin.sum()>=3 and brown.sum()<=4:chosen=6;reason='source ivory wraps and green hands/forearms'
  elif kind in('merchant','worker','hunter','veteran')and yy==2 and xx in(1,2)and pale.sum()>=6 and brown.sum()>=12 and skin.sum()<=8:chosen=3;reason='source ivory cloth/fur and brown leather; tiny green neck shadow reduces to warm tone'
  elif kind=='veteran' and yy==0 and steel.sum()>=3:chosen=5;reason='Actual gray veteran hair stays gray/ivory/ink rather than becoming green or brown'
  elif kind=='guard' and yy in(2,3) and xx in(1,2) and brown.sum()>=12:chosen=3;reason='Keep source brown leather/pants and ivory plates, rather than recoloring whole clothing blue for small steel patch'
  elif kind=='guard' and yy==1 and xx in(0,3) and steel.sum()>=2 and skin.sum()<4:chosen=5;reason='Actual source steel pauldrons; tiny red trim reduces to cool shadow'
  elif kind=='guard'and steel.sum()>=3 and red.sum()<=steel.sum()*2 and skin.sum()<4:chosen=5;reason='actual source steel pauldrons/axe/boot plates'
  elif kind=='guard'and red.sum()>=6 and skin.sum()<4 and steel.sum()<3:chosen=7;reason='actual source red cloth'
  else:chosen=min(errors,key=errors.get)
  if forced_attrs is not None:
   chosen=forced_attrs[t];reason='Stable per-direction palette across all gait keys; source material re-fit to idle allocation'
  local=pixels[chosen];local[~visible]=0;ids[ys,xs]=local;attrs.append(chosen)
  scores.append({'tile':t,'palette':chosen,'reason':reason,'skin_pixels':int(skin.sum()),'pale_pixels':int(pale.sum()),'brown_pixels':int(brown.sum()),'steel_pixels':int(steel.sum()),'red_pixels':int(red.sum()),'errors':errors})
 return ids,attrs,scores

def native_source(path,box):
 source=np.asarray(Image.open(ROOT/path).convert('RGBA'));a=source[box[1]:box[3],box[0]:box[2]].copy();a[:,:,3]=np.where(a[:,:,3]>=128,255,0)
 whole=Image.fromarray(a);small=whole.copy();small.thumbnail((32,32),Image.Resampling.NEAREST);offset=((32-small.width)//2,32-small.height);canvas=Image.new('RGBA',(32,32));canvas.paste(small,offset)
 return canvas,{'source_path':path,'source_sha256':sha((ROOT/path).read_bytes()),'source_canvas':[source.shape[1],source.shape[0]],'source_crop':list(box),'source_alpha_threshold':128,'whole_source_dimensions':list(whole.size),'native_body_dimensions':list(small.size),'native_offset':list(offset),'native_canvas':[32,32],'native_sampling':'NEAREST; original complete figure directly reduced once, no16px intermediary','source_alpha_preserved_at_native_sampling':True,'source_anatomy_erased_for_tile_budget':False}

def move_patch(a,box,dx,dy,attach=False):
 """Authored native part-key transform of existing source pixels only."""
 x0,y0,x1,y1=box;patch=a[y0:y1,x0:x1].copy();out=a.copy();out[y0:y1,x0:x1]=0
 # A copied first elbow row keeps a downswung forearm attached to its upperarm.
 if attach and dy>0:out[y0:y0+dy,x0:x1]=patch[:dy]
 for py in range(patch.shape[0]):
  for px in range(patch.shape[1]):
   yy,xx=y0+py+dy,x0+px+dx
   if patch[py,px,3]and 0<=xx<32 and 0<=yy<32:out[yy,xx]=patch[py,px]
 return out

def make_walks(canvas,d,kind):
 """Two visibly different footfall/forearm keys; face remains source exact."""
 a=np.asarray(canvas);result=[];edits=[]
 # Coordinates are native anatomy anchors for these complete source drawings.
 if d in('front','back'):
  opaque=a[:,:,3]>0;foot=a[27:,:,3].any(0);xs=np.flatnonzero(foot);mid=int((xs.min()+xs.max()+1)//2)
  left=(max(0,int(xs.min())-1),27,mid,32);right=(mid,27,min(32,int(xs.max())+2),32)
  if kind=='apprentice' and d=='front':
   # The real staff reaches row29 beside the boots: never move its lower shaft.
   left=(9,30,16,32);right=(18,30,25,32)
  body=np.flatnonzero(a[20:26,:,3].any(0));x0,x1=int(body.min()),int(body.max())+1
  arms=[(x0,21,min(x0+5,mid-1),27),(max(x1-5,mid+1),21,x1,27)]
  for phase in(0,1):
   b=a.copy();chosen=left if phase==0 else right;dx=-1 if phase==0 else 1
   dy=-1
   if kind=='apprentice' and d=='front' and phase==0:dx,dy=1,0
   b=move_patch(b,chosen,dx,dy)
   # Counter-swing forearms retains hands/wraps from actual source; weapon-bearing
   # guard hands stay fixed so no axe can detach from the wrist.
   if kind not in('guard','hunter','apprentice'):
    b=move_patch(b,arms[1-phase],0,-1)
    b=move_patch(b,arms[phase],0,1,attach=True)
   result.append(Image.fromarray(b));edits.append({'leg_box':list(chosen),'leg_shift':[dx,dy],'counter_forearm_boxes':[list(x)for x in arms]if kind not in('guard','hunter','apprentice')else[],'held_equipment_fixed':kind in('guard','hunter','apprentice')})
 else:
  # Complete side foot cluster shifts fore/aft one pixel with a raised heel.
  # The other lower-leg contour stays planted; no whole-body horizontal slide.
  xs=np.flatnonzero(a[28:,:,3].any(0));x0,x1=int(xs.min()),int(xs.max())+1
  # Bow/staff tips beside the side-view boots are equipment, not a second leg.
  protected_foot_bounds={('hunter','left'):(13,21),('hunter','right'):(10,17),('apprentice','left'):(14,24),('apprentice','right'):(8,18)}
  if (kind,d) in protected_foot_bounds:x0,x1=protected_foot_bounds[kind,d]
  mid=(x0+x1)//2
  front=(x0,28,max(mid+1,x0+2),32)if d=='left'else(max(mid-1,x0),28,x1,32)
  rear=(max(mid-1,x0),28,x1,32)if d=='left'else(x0,28,min(mid+1,x1),32)
  for phase in(0,1):
   chosen=front if phase==0 else rear;dx=(-1 if d=='left' else 1)*(1 if phase==0 else -1)
   b=move_patch(a,chosen,dx,-1 if phase==0 else 0)
   result.append(Image.fromarray(b));edits.append({'leg_box':list(chosen),'leg_shift':[dx,-1 if phase==0 else 0],'held_equipment_fixed':True})
 for image in result:
  frame=np.asarray(image);assert np.array_equal(frame[:18],a[:18]),(kind,d,'Face/head changed by native gait')
  if kind in('hunter','apprentice') and d in('left','right'):
   limit={('hunter','left'):(0,12),('hunter','right'):(19,32),('apprentice','left'):(0,12),('apprentice','right'):(20,32)}[(kind,d)]
   assert np.array_equal(frame[:,limit[0]:limit[1]],a[:,limit[0]:limit[1]]),(kind,d,'Held bow/staff detached')
  if kind=='apprentice' and d=='front':assert np.array_equal(frame[:30,:10],a[:30,:10]),'Staff shaft altered by footfall'
 assert not np.array_equal(np.asarray(result[0]),a)and not np.array_equal(np.asarray(result[1]),a)
 assert not np.array_equal(np.asarray(result[0]),np.asarray(result[1]))
 return result,edits

def import_role(role,spec,previous,identity=None,material_variant=None):
 source,boxes,kind=spec;record={'references':[source]+previous['references'],'identity':identity or IDENTITIES[role],'palette':2,'frame_size':32,'dimensions':[32,32],'views':{},'attributes':{},'walk':{},'walk_attributes':{},'source_kind':'whole_generated_world_source_reduced_directly_to_native32_with_authored_gaits','new_anatomy_authored':False,'new_detail_generated':True,'resampling':'NEAREST once from whole WORLD source to native32, no16px intermediary and no smoothing','source_note':'User-authorized redraw referencing the supplied world silhouettes, converted from a complete new WORLD design. Conversion is explicitly lossy; not exact source-grid recovery. Native gait edits are authored separately.','animation_note':'Actual distinct alternating leg keys in allfour directions; front/back counter-forearm swing where equipment permits. Face/head/source equipment stays attached. Not original-source animation.','provenance':{'source_sha256':sha((ROOT/source).read_bytes()),'supplied_reference_hashes':{r:sha((ROOT/r).read_bytes())for r in previous['references']},'original_pngs_modified':False,'directions':{}}};previews={};role_out=OUT/role;role_out.mkdir(parents=True,exist_ok=True)
 for d,box in zip(DIRS,boxes):
  canvas,prov=native_source(source,box)
  if material_variant=='leather_worker_shirt':
   cells=np.asarray(canvas).copy();rgb=cells[:,:,:3].astype('int32');gy,gx=np.mgrid[:32,:32]
   shirt=(cells[:,:,3]>0)&(gy>=17)&(gy<=23)&(gx>=8)&(gx<=23)&(rgb[:,:,0]>=168)&(rgb[:,:,1]>=160)&(rgb[:,:,2]>=112)
   # Material recolor only on actual existing ivory shirt pixels. Face,
   # outline, equipment, all source alpha and shape coordinates remain exact.
   cells[shirt,:3]=[132,88,49];canvas=Image.fromarray(cells);prov['derived_material_variant']={'kind':material_variant,'native_existing_shirt_pixels_recolored':int(shirt.sum()),'region':[8,17,24,24],'old_source_material':'ivory work shirt','derived_material_rgb':[132,88,49],'alpha_and_geometry_unchanged':True}
  walks,keys=make_walks(canvas,d,kind);prov['authored_native_gait_keys']=keys;records=[];imgs=[];idle_attrs=None;idle_native=None
  for pose,cel in enumerate([canvas]+walks):
   ids,attrs,scores=fit_materials(cel,d,kind,idle_attrs);encoded=encode(Image.fromarray(ids));assert np.array_equal(np.asarray(decode(encoded,32)),ids)
   if pose==0:idle_attrs=attrs
   native=render(ids,attrs);assert np.array_equal(np.asarray(native)[:,:,3],np.asarray(cel)[:,:,3])
   if pose==0:idle_native=np.asarray(native).copy()
   else:assert np.array_equal(np.asarray(native)[:18],idle_native[:18]),(role,d,pose,'Native face flicker')
   native.save(role_out/f'{d}_{pose}_native32.png');imgs.append(native)
   records.append({'pose':pose,'nonblank_mask':mask_of(ids),'occupied_tiles':mask_of(ids).bit_count(),'native_2bpp_sha256':sha(encoded),'decode_exact':True,'per_tile_palette_ids':attrs,'material_scores':scores})
   if pose==0:record['views'][d]=rows(ids);record['attributes'][d]=attrs
   else:record['walk'].setdefault(d,[]).append(rows(ids));record['walk_attributes'].setdefault(d,[]).append(attrs)
  prov['frames']=records;record['provenance']['directions'][d]=prov;previews[d]=imgs
 contact=Image.new('RGB',(4*180,3*180),(230,195,139));draw=ImageDraw.Draw(contact)
 for j,d in enumerate(DIRS):
  for p,im in enumerate(previews[d]):
   x,y=j*180,p*180;draw.text((x+4,y+3),f'{role} {d} {p}',fill=(0,0,0));contact.paste(im,(x+4,y+38),im);big=im.resize((128,128),Image.Resampling.NEAREST);contact.paste(big,(x+47,y+30),big)
 contact.save(role_out/'four_views_three_poses_1x4x.png')
 gif=[]
 for p in(0,1,0,2):
  frame=Image.new('RGB',(128,32),(230,195,139))
  for i,d in enumerate(DIRS):frame.paste(previews[d][p],(i*32,0),previews[d][p])
  gif.append(frame.resize((512,128),Image.Resampling.NEAREST))
 gif[0].save(role_out/'authored_gait_preview.gif',save_all=True,append_images=gif[1:],duration=120,loop=0)
 return record

def main():
 OUT.mkdir(parents=True,exist_ok=True);previous=json.loads((ROOT/'assets/world_readability_v0219/orc_npcs.json').read_text());roles=copy.deepcopy(previous['roles'])
 for name,record in roles.items():record['frame_size']=24;record['dimensions']=[24,24]
 for role,spec in SPECS.items():roles[role]=import_role(role,spec,previous['roles'][role])
 roles['quest_peon']=import_role('quest_peon',SPECS['peon_worker'],previous['roles']['quest_peon'],identity='Gornek/quest Peon uses the complete new worker WORLD anatomy with an explicitly derived darker leather work-shirt material, retaining its focused green face, pale eyes/tusks, belt pouch and boots. This is an honest family variant, not a separately recovered source.',material_variant='leather_worker_shirt')
 roles['camp_guard']=copy.deepcopy(roles['orc_guard']);roles['camp_guard']['identity']='Camp guard reuses the complete new guard WORLD archetype and true gait frames, with the same armor/axe silhouette. This unbound roster family is explicitly shared, not a separate recovered drawing.';roles['camp_guard']['references']=list(dict.fromkeys(roles['camp_guard']['references']+previous['roles']['camp_guard']['references']));roles['camp_guard']['provenance']['shared_world_art_family']='orc_guard'
 payload={'version':'v0.2.20','authoring':'Six complete new WORLD design families reduced directly to32, plus two explicitly documented source-family variants; authored native gaits. Garrosh24 alone remains exactly approved and unchanged.','roles':roles}
 staged=SOURCE/'orc_npcs.json.tmp';staged.write_text(json.dumps(payload,indent=2)+'\n');staged.replace(SOURCE/'orc_npcs.json')
 # This is a static native-art comparison, never labelled an emulator capture.
 from import_peon_world_readability_v0219 import render as render24, indexed as indexed24
 comparison=Image.new('RGB',(4*240,9*168),(230,195,139));draw=ImageDraw.Draw(comparison)
 for row,(name,art) in enumerate(roles.items()):
  for col,d in enumerate(DIRS):
   x,y=col*240,row*168;draw.text((x+3,y+3),name+' '+d,fill=(0,0,0))
   old=previous['roles'][name];old_ids=indexed24(old['views'][d],name,d,0);before=render24(old_ids,old['attributes'][d]);comparison.paste(before,(x+5,y+29),before)
   b=before.resize((72,72),Image.Resampling.NEAREST);comparison.paste(b,(x+3,y+66),b);draw.text((x+3,y+147),'old24 / 3x',fill=(0,0,0))
   if art['frame_size']==32:
    ids=np.array([[0 if c=='.'else int(c)for c in r]for r in art['views'][d]],dtype='uint8');after=render(ids,art['attributes'][d])
   else:after=before
   comparison.paste(after,(x+94,y+23),after);b=after.resize((after.width*4,after.height*4),Image.Resampling.NEAREST);comparison.paste(b,(x+104,y+28),b);draw.text((x+94,y+154),'native'+str(art['frame_size'])+' / 4x',fill=(0,0,0))
 comparison.save(OUT/'all_npc_world_before_after_1x.png')
 report={'version':'v0.2.20','status':'SOURCE_REVIEW','source_json':rel(SOURCE/'orc_npcs.json'),'source_json_sha256':sha((SOURCE/'orc_npcs.json').read_bytes()),'converted_roles':list(SPECS)+['quest_peon','camp_guard'],'retained_v19_roles':['warrior_trainer'],'protected_garrosh':{'role':'warrior_trainer','frame_size':24,'views_and_walks_unchanged':roles['warrior_trainer']['views']==previous['roles']['warrior_trainer']['views']and roles['warrior_trainer'].get('walk')==previous['roles']['warrior_trainer'].get('walk')},'native_material_palette_contract':{str(k):PALETTES[k]for k in(2,3,5,6,7)},'originals_changed':False,'built_or_runtime_verified':False}
 (OUT/'source_import_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in('converted_roles','retained_v19_roles','source_json_sha256')},indent=2))
if __name__=='__main__':main()
