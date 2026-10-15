#!/usr/bin/env python3
"""Import three approved illustrated master busts into five native GBC palettes.

Whole-alpha-component crops, nearest fitting and material/face weighted palette
reduction are explicitly lossy. Original atlas files remain byte-identical.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import label
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets/class_portraits_v0219'
GFX=ROOT/'gfx/class_portraits_v0219'
REVIEW=ROOT/'references/generated/class_selection_v0219'
INK=(3,2,3)
SOURCES={
 'kento':('kento_corrected_horns_source.png','/workspace/generated_images/exec-185ed939-e788-401a-b1e9-5cf599a111b1.png',0),
 'zogzog':('zogzog_garrosh_brown_source.png','/workspace/generated_images/exec-3ed724b1-b980-478a-b3fb-ac29b53ad4dd.png',1),
 'bismillah':('bismillah_original_source.png','/workspace/generated_images/exec-f3471475-09cf-4e61-901f-cb4e1bd847ea.png',2),
}
SOURCE_DIGESTS={'kento':'ce0a6f5c36712fb9c270c2b7ca8b3be931a29de07b257279dea6db91a91c283b','zogzog':'e6600052e5773d6715702949fc66d93ddf965437c95a9693865e42b418ac7811','bismillah':'c3a60b4e6b3088b3dd64f935dbbb6f128b690219d7c2124161c3c3854421beed'}
NAMES={'kento':'Kento Brandenhoof','zogzog':'MoCMoc Zogzog','bismillah':'Bismillah LesTenebres'}
FOCUS={'kento':[(30,23,68,59,3.0),(43,30,56,39,7.0)],'zogzog':[(25,15,60,51,3.2),(37,27,55,36,7.5)],'bismillah':[(24,21,51,60,3.6),(29,27,46,34,12.0)]}
def sha(b):return hashlib.sha256(b).hexdigest()
def rel(p):return Path(p).resolve().relative_to(ROOT).as_posix()
def expand(a):
 a=np.asarray(a,np.uint8);return(a<<3)|(a>>2)
def material(c,role):
 r,g,b=map(int,c)
 if max(c)<=(3 if role in ('kento','zogzog') else 5):return'ink'
 if g>=r+2 and g>=b+2:return'green'
 if b>=r+2 and g>=r:return'blue'
 if b>=g+2 and r>=g+1:return'purple'
 if r>=23 and g>=20 and b>=13 and r>=g and g>=b+2:return'bone'
 if max(c)-min(c)<=4:return'steel'
 if r>=20 and g>=14 and b<=g*.65:return'gold'
 if r>=9 and r>g*2.1 and g<=11:return'red'
 return'warm'
def preserve_sources():
 ASSETS.mkdir(parents=True,exist_ok=True);paths={}
 for role,(filename,original,panel)in SOURCES.items():
  p=ASSETS/filename
  if not p.exists():shutil.copyfile(original,p)
  if Path(original).exists():assert p.read_bytes()==Path(original).read_bytes()
  assert sha(p.read_bytes())==SOURCE_DIGESTS[role],(role,'Approved source atlas changed')
  paths[role]=p
 return paths
def extract(path,role,panel):
 source=np.array(Image.open(path).convert('RGBA'));visible=source[:,:,3]>=128;labs,n=label(visible);sizes=np.bincount(labs.ravel());large=[int(k)for k in np.argsort(sizes)[::-1]if k and sizes[k]>10000]
 assert len(large)==3,(role,n,large)
 large.sort(key=lambda k:np.where(labs==k)[1].mean());chosen=large[panel];mask=labs==chosen;ys,xs=np.nonzero(mask);box=[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
 owned=source.copy();owned[:,:,3]=mask.astype(np.uint8)*255;crop=Image.fromarray(owned).crop(box)
 scale=min(80/crop.width,88/crop.height);size=(round(crop.width*scale),round(crop.height*scale));fit=crop.resize(size,Image.Resampling.NEAREST);a=np.array(fit);a[:,:,3]=(a[:,:,3]>=128).astype(np.uint8)*255
 canvas=np.zeros((88,80,4),np.uint8);x,y=(80-size[0])//2,88-size[1];canvas[y:y+size[1],x:x+size[0]]=a
 return canvas,{'source':rel(path),'source_sha256':sha(path.read_bytes()),'source_atlas_dimensions':[source.shape[1],source.shape[0]],'source_component_id':chosen,'source_component_count':n,'selected_panel_identity':panel,'source_crop':box,'source_component_opaque_pixels':int(mask.sum()),'unapproved_neighbor_pixels_imported':0,'source_crop_policy':'whole approved alpha>=128 connected bust selected by panel identity, not an equal-third clipping rectangle','native_canvas':[80,88],'fit_dimensions':list(size),'fit_origin':[x,y],'fit_nearest_scale':scale,'native_opaque_pixels':int((canvas[:,:,3]!=0).sum()),'crop_complete':True,'resampling':'nearest; explicitly lossy raster fit, no native-grid recovery claimed','new_silhouette_or_anatomy_drawing':False,'smoothing':False,'dithering':False}
def medoids(colors,weights,k):
 d=((colors[:,None].astype(float)-colors[None].astype(float))**2*np.array([.95,1.1,.95])).sum(2)
 selected=[int((weights[:,None]*d).sum(0).argmin())]
 while len(selected)<min(k,len(colors)):
  scores=weights*d[:,selected].min(1);scores[selected]=-1;selected.append(int(scores.argmax()))
 for _ in range(2):
  for i in range(len(selected)):
   others=selected[:i]+selected[i+1:];best=d[:,others].min(1)if others else np.full(len(colors),np.inf)
   scores=(weights[:,None]*np.minimum(best[:,None],d)).sum(0);scores[others]=np.inf;selected[i]=int(scores.argmin())
 return colors[selected]
def distance(colors,candidates,role):
 d=((colors[:,None].astype(float)-candidates[None].astype(float))**2*np.array([.95,1.1,.95])).sum(2);a=np.array([material(c,role)for c in colors]);b=np.array([material(c,role)for c in candidates])
 penalties={'ink':1000,'green':700,'blue':250,'purple':500,'bone':170,'steel':100,'gold':100,'red':200,'warm':45}
 if role in ('kento','zogzog'):penalties.update(bone=100,steel=90,gold=35,red=35,warm=35)
 for kind,cost in penalties.items():d+=(a[:,None]==kind)*(b[None]!=kind)*cost
 d+=(a[:,None]=='warm')*np.isin(b,['green','blue','purple'])[None]*1000
 return d
def best_three(h,d,ink):
 keep=h>0;w=h[keep];cost=d[keep];baseline=ink[keep];selected=[]
 for _ in range(3):
  scores=(w[:,None]*np.minimum(baseline[:,None],cost)).sum(0);scores[selected]=np.inf;k=int(scores.argmin());selected.append(k);baseline=np.minimum(baseline,cost[:,k])
 for _ in range(2):
  for i in range(3):
   others=selected[:i]+selected[i+1:];best=np.minimum(ink[keep],cost[:,others].min(1));scores=(w[:,None]*np.minimum(best[:,None],cost)).sum(0);scores[others]=np.inf;selected[i]=int(scores.argmin())
 return tuple(sorted(selected))
def fit_palettes(rgba,role):
 rgb=rgba[:,:,:3]>>3;visible=rgba[:,:,3]!=0;colors,inverse=np.unique(rgb[visible],axis=0,return_inverse=True);indices=np.zeros(visible.shape,np.int16);indices[visible]=inverse
 weight=visible.astype(float)
 for y in range(87):
  edge=np.minimum(2,np.sqrt(((rgb[y].astype(float)-rgb[y+1])**2).sum(1))/8)*(visible[y]&visible[y+1]);weight[y]+=edge;weight[y+1]+=edge
 for x0,y0,x1,y1,v in FOCUS[role]:weight[y0:y1,x0:x1]*=v
 # Rare glowing eyes, tusks and source highlights must not be averaged away.
 if role=='bismillah':
  purple=(rgb[:,:,2]>rgb[:,:,1]+5)&(rgb[:,:,0]>rgb[:,:,1]+5);weight[24:38,24:50]*=np.where(purple[24:38,24:50],5,1)
 hist=np.bincount(indices[visible],weights=weight[visible],minlength=len(colors));kinds=np.array([material(c,role)for c in colors]);pool=[]
 for kind,k in [('ink',3),('warm',12),('gold',5),('red',5),('green',6),('blue',6),('purple',7),('bone',5),('steel',6)]:
  m=kinds==kind
  if m.any():pool.extend(medoids(colors[m],hist[m],k).tolist())
 candidates=np.unique(np.array(pool,np.uint8),axis=0);d=distance(colors,candidates,role);ink=distance(colors,np.array([INK]),role)[:,0]
 tilehist=[]
 for y in range(0,88,8):
  for x in range(0,80,8):
   mask=visible[y:y+8,x:x+8];tilehist.append(np.bincount(indices[y:y+8,x:x+8][mask],weights=weight[y:y+8,x:x+8][mask],minlength=len(colors)))
 h=np.array(tilehist);options=list(dict.fromkeys(best_three(q,d,ink)for q in h if q.any()));cost=np.column_stack([np.minimum(ink,d[:,o].min(1))for o in options]);errors=h@cost
 selected=[int(errors.sum(0).argmin())]
 while len(selected)<5:
  scores=np.minimum(errors,errors[:,selected].min(1)[:,None]).sum(0);scores[selected]=np.inf;selected.append(int(scores.argmin()))
 palettes=[options[k]for k in selected]
 for _ in range(7):
  errors=h@np.column_stack([np.minimum(ink,d[:,p].min(1))for p in palettes]);assignment=errors.argmin(1);new=[]
  for k in range(5):
   group=h[assignment==k].sum(0);new.append(best_three(group,d,ink)if group.any()else palettes[k])
  if palettes==new:break
  palettes=new
 palette=np.array([[INK,*candidates[list(p)].tolist()]for p in palettes],np.uint8);errors=h@np.column_stack([np.minimum(ink,d[:,p].min(1))for p in palettes]);assignment=errors.argmin(1)
 indexed=np.zeros((88,80),np.uint8);decoded=np.zeros((88,80,4),np.uint8);decoded[:,:,:3]=expand(INK);decoded[:,:,3]=rgba[:,:,3];records=[]
 for tile,slot in enumerate(assignment):
  yy,xx=divmod(tile,10);y,x=yy*8,xx*8;ids=indices[y:y+8,x:x+8];cost=np.concatenate((ink[:,None],d[:,palettes[slot]]),axis=1);select=cost[ids].argmin(2);mask=visible[y:y+8,x:x+8];select[~mask]=0;indexed[y:y+8,x:x+8]=select;decoded[y:y+8,x:x+8,:3]=expand(palette[slot][select]);records.append({'tile':tile,'xy':[x,y],'palette_id':int(slot)+3,'opaque_pixels':int(mask.sum()),'source_colors':len(np.unique(rgb[y:y+8,x:x+8][mask],axis=0))})
 return indexed,decoded,palette,assignment.astype(np.uint8)+3,records

def encode(a):
 b=bytearray()
 for y in range(0,88,8):
  for x in range(0,80,8):
   for row in a[y:y+8,x:x+8]:b.extend((sum((int(v)&1)<<(7-i)for i,v in enumerate(row)),sum((int(v)>>1)<<(7-i)for i,v in enumerate(row))))
 return bytes(b)
def decode(packet):
 a=np.zeros((88,80),np.uint8)
 for tile in range(110):
  y,x=divmod(tile,10)
  for row in range(8):
   lo,hi=packet[tile*16+row*2:tile*16+row*2+2]
   for xx in range(8):a[y*8+row,x*8+xx]=((lo>>(7-xx))&1)|(((hi>>(7-xx))&1)<<1)
 return a
def metric(before,after,box,role):
 x0,y0,x1,y1=box;a=before[y0:y1,x0:x1];b=after[y0:y1,x0:x1];visible=a[:,:,3]!=0;aa=a[:,:,:3][visible]>>3;bb=b[:,:,:3][visible]>>3;sa=np.array([material(c,role)for c in aa]);sb=np.array([material(c,role)for c in bb]);return{'box':list(box),'opaque_pixels':int(visible.sum()),'exact_rgb555_pixels':int((aa==bb).all(1).sum()),'rgb555_rmse':round(float(np.sqrt(((aa.astype(float)-bb)**2).mean())),3),'source_materials':{k:int((sa==k).sum())for k in sorted(set(sa))},'native_materials':{k:int((sb==k).sum())for k in sorted(set(sb))},'source_warm_to_green':int(((sa=='warm')&(sb=='green')).sum())}
def main():
 GFX.mkdir(parents=True,exist_ok=True);REVIEW.mkdir(parents=True,exist_ok=True);sources=preserve_sources();manifest={'version':'v0.2.19','status':'PASS','scope':'Static illustrated master conversion, not ROM screenshots','source_art_modified':False,'source_geometry':'complete approved alpha component, nearest lossy fit; no redrawing','native_size':[80,88],'native_tiles':110,'native_palette_ids':[3,4,5,6,7],'shared_opaque_background_rgb555':list(INK),'roles':{}};lines=[]
 for role,path in sources.items():
  rgba,info=extract(path,role,SOURCES[role][2]);indexed,decoded,palettes,attrs,tiles=fit_palettes(rgba,role);packet=encode(indexed);assert len(packet)==1760 and np.array_equal(decode(packet),indexed);assert np.array_equal(rgba[:,:,3],decoded[:,:,3]);assert len(attrs)==110
  paldata=b''.join(int(int(r)|(int(g)<<5)|(int(b)<<10)).to_bytes(2,'little')for p in palettes for r,g,b in p);assert len(paldata)==40
  out=GFX/role;out.mkdir(exist_ok=True);review=REVIEW/role;review.mkdir(exist_ok=True)
  (out/'portrait.2bpp').write_bytes(packet);(out/'attrs.bin').write_bytes(attrs.tobytes());(out/'palettes.bin').write_bytes(paldata);Image.fromarray(decoded).save(out/'hardware.png');Image.fromarray(rgba).save(review/'source_fit.png');Image.fromarray(decoded).save(review/'hardware.png')
  bg=Image.new('RGBA',(80,88),(*map(int,expand(INK)),255));sourcebg=bg.copy();sourcebg.alpha_composite(Image.fromarray(rgba));bg.alpha_composite(Image.fromarray(decoded));bg.convert('RGB').save(review/'hardware_bg.png');bg.resize((320,352),Image.Resampling.NEAREST).save(review/'hardware_4x.png');sourcebg.resize((320,352),Image.Resampling.NEAREST).save(review/'source_fit_4x.png')
  cmp=Image.new('RGB',(640,368),tuple(map(int,expand(INK))));cmp.paste(sourcebg.resize((320,352),Image.Resampling.NEAREST),(0,16));cmp.paste(bg.resize((320,352),Image.Resampling.NEAREST),(320,16));draw=ImageDraw.Draw(cmp);draw.text((4,2),role+' source nearest',fill=(247,231,181));draw.text((324,2),'actual native 5 palettes',fill=(247,231,181));cmp.save(review/'comparison_4x.png')
  report={**info,'name':NAMES[role],'native_palettes_rgb555':palettes.tolist(),'palette_policy':'Dark warm fur/skin shadows remain separate from common background ink; per-tile material/face weighting' if role in ('kento','zogzog') else 'Grey undead face and violet glowing eyes receive material/face weighted palettes','attrs_bank_flag_included':False,'packet_decode_exact':True,'alpha_geometry_exact_after_fit':True,'source_ink_may_use_opaque_bg_index0':True,'whole_metrics':metric(rgba,decoded,(0,0,80,88),role),'focus_metrics':{f'focus_{i}':metric(rgba,decoded,b[:4],role)for i,b in enumerate(FOCUS[role])},'tiles':tiles,'outputs':{rel(out/n):{'bytes':(out/n).stat().st_size,'sha256':sha((out/n).read_bytes())}for n in('portrait.2bpp','attrs.bin','palettes.bin','hardware.png')}}
  manifest['roles'][role]=report;(review/'import_report.json').write_text(json.dumps(report,indent=2)+'\n');title=role.title();prefix=f'PeonMaster{title}PortraitV0219';lines +=[f'SECTION "Peon illustrated master {role} v0219", ROMX',prefix+'::',f'\tINCBIN "gfx/class_portraits_v0219/{role}/portrait.2bpp"',f'\tassert @ - {prefix} == 110 * TILE_SIZE',prefix+'Attrs::',f'\tINCBIN "gfx/class_portraits_v0219/{role}/attrs.bin"',f'\tassert @ - {prefix}Attrs == 110',prefix+'Palettes::',f'\tINCBIN "gfx/class_portraits_v0219/{role}/palettes.bin"',f'\tassert @ - {prefix}Palettes == 40','']
 (GFX/'graphics.asm').write_text('\n'.join(lines));(GFX/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(REVIEW/'import_report.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'status':'PASS','roles':{r:{'crop':v['source_crop'],'fit':v['fit_dimensions'],'whole':v['whole_metrics'],'focus':v['focus_metrics']}for r,v in manifest['roles'].items()}},indent=2))
if __name__=='__main__':main()
