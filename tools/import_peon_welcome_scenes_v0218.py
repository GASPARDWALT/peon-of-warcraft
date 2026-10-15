#!/usr/bin/env python3
"""Fit approved generated welcome artwork into the native five-palette GBC BG.

This is an explicitly lossy nearest raster import, not native-grid recovery.
Sources stay byte-identical. No contours, silhouettes or details are invented.
"""
from __future__ import annotations
import hashlib
import json
from collections import deque
from pathlib import Path
import shutil
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import label, find_objects

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets/selection_v0218'
GFX=ROOT/'gfx/welcome_scenes_v0218'
REVIEW=ROOT/'references/generated/selection_v0218/welcome'
SOURCES={
 'base':('base_generated_source.png','/workspace/generated_images/exec-9ea8afc7-0317-4635-891f-1b339e840723.png'),
 'background':('durotar_background_generated_source.png','/workspace/generated_images/exec-00f064e1-aab7-4ca7-b50b-e948e114b064.png'),
 'classes':('classes_generated_source.png','/workspace/generated_images/exec-d35bd1c3-cbde-4224-9373-b5e5e3d08ba4.png'),
}
ROLES=('base','shaman','warrior','warlock')
PALETTE_IDS=(2,3,4,5,6)
MAX_TILES=312

def sha(data):return hashlib.sha256(data).hexdigest()
def rel(path):return Path(path).resolve().relative_to(ROOT).as_posix()
def expand(a):
 a=np.asarray(a,dtype=np.uint8);return(a<<3)|(a>>2)

def preserve_sources():
 ASSETS.mkdir(parents=True,exist_ok=True);out={}
 for role,(filename,generated)in SOURCES.items():
  target=ASSETS/filename
  if not target.exists():shutil.copyfile(generated,target)
  if Path(generated).exists():assert target.read_bytes()==Path(generated).read_bytes()
  out[role]=target
 return out

def isolate_base(path):
 rgb=np.array(Image.open(path).convert('RGB'));r,g,b=[rgb[:,:,k].astype(np.int16)for k in range(3)]
 # Only plum-colored pixels connected to an image border are background.
 # Achromatic black outline / grey hair are never eligible for removal.
 eligible=(r>g)&(b>g)&((r+b-2*g)>=4)&(g<45)&(r<85)&(b<85)
 labels,n=label(eligible)
 border=np.unique(np.concatenate((labels[0],labels[-1],labels[:,0],labels[:,-1])))
 border=border[border!=0];removed=np.isin(labels,border)
 rgba=np.dstack((rgb,(~removed).astype(np.uint8)*255))
 ys,xs=np.nonzero(~removed);box=(int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1)
 # RGB source corners must be removed; foreground hair/ink remains opaque.
 assert removed[0,0] and removed[-1,-1]
 assert np.count_nonzero((rgb.max(2)<=4)&(~removed))>100
 return Image.fromarray(rgba).crop(box),{'method':'only border-connected dark plum background flood-fill; achromatic black/grey protected','source_crop':list(box),'removed_border_background_pixels':int(removed.sum()),'retained_opaque_pixels':int((~removed).sum()),'retained_closed_plum_islands':True,'alpha_threshold':128}

def isolate_classes(path):
 a=np.array(Image.open(path).convert('RGBA'));mask=a[:,:,3]>=128;labels,n=label(mask)
 sizes=np.bincount(labels.ravel());components=[int(k)for k in np.argsort(sizes)[::-1]if k and sizes[k]>10000]
 assert len(components)==3,(n,components)
 components.sort(key=lambda k:np.nonzero(labels==k)[1].mean())
 result={}
 for panel,(role,k)in enumerate(zip(ROLES[1:],components)):
  visible=labels==k;ys,xs=np.nonzero(visible);box=(int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1)
  own=a.copy();own[:,:,3]=visible.astype(np.uint8)*255
  result[role]=(Image.fromarray(own).crop(box),{'source_crop':list(box),'nominal_equal_panel':[panel*a.shape[1]//3,0,(panel+1)*a.shape[1]//3,a.shape[0]],'method':'alpha>=128; whole connected figure selected by its nominal equal-third panel; preserve measured cross-panel equipment overhang','component_id':k,'component_opaque_pixels':int(visible.sum()),'alpha_threshold':128,'neighboring_component_pixels_imported':0})
 return result

def make_scenes(paths):
 bg=Image.open(paths['background']).convert('RGB').resize((160,144),Image.Resampling.NEAREST)
 figures={'base':isolate_base(paths['base']),**isolate_classes(paths['classes'])}
 scenes=[];masks=[];records={}
 for role in ROLES:
  figure,info=figures[role];w,h=figure.size;scale=min(64/w,84/h);size=(max(1,round(w*scale)),max(1,round(h*scale)))
  fit=figure.resize(size,Image.Resampling.NEAREST);arr=np.array(fit);arr[:,:,3]=(arr[:,:,3]>=128).astype(np.uint8)*255;fit=Image.fromarray(arr)
  xy=(18+(64-size[0])//2,125-size[1]);canvas=bg.convert('RGBA');canvas.alpha_composite(fit,xy)
  foreground=np.zeros((144,160),bool);foreground[xy[1]:xy[1]+size[1],xy[0]:xy[0]+size[0]]=arr[:,:,3]!=0
  scenes.append(np.array(canvas.convert('RGB')));masks.append(foreground)
  records[role]={**info,'source_bbox_size':[w,h],'fit_size':list(size),'fit_origin':list(xy),'fit_nearest_scale':scale,'feet_baseline_y':124,'figure_opaque_pixels_native':int(foreground.sum()),'source_geometry':'whole figure, no silhouette drawing, binary alpha and nearest sampling only'}
  fit.save(REVIEW/f'{role}_figure_fit_rgba.png');canvas.convert('RGB').save(REVIEW/f'{role}_composite_source.png')
 return np.asarray(scenes),np.asarray(masks),records,np.array(bg)

def material(color):
 r,g,b=map(int,color)
 if max(r,g,b)<=5:return 'ink'
 if g>=r+2 and g>=b+2:return 'green'
 if b>=r+2 and g>=r:return 'blue'
 if b>=g+2 and r>=g+1:return 'purple'
 if r>=24 and g>=21 and b>=14 and r>=g and g>=b+2:return 'ivory'
 if max(r,g,b)-min(r,g,b)<=4:return 'steel'
 return 'warm'

def weighted_medoids(colors,weights,count):
 delta=colors[:,None,:].astype(float)-colors[None,:,:]
 dist=(delta*delta*np.array([.95,1.15,.9])).sum(2)
 chosen=[int((weights[:,None]*dist).sum(0).argmin())]
 while len(chosen)<min(count,len(colors)):
  scores=weights*dist[:,chosen].min(1);scores[chosen]=-1;chosen.append(int(scores.argmax()))
 for _ in range(2):
  for k in range(len(chosen)):
   other=chosen[:k]+chosen[k+1:]
   best=dist[:,other].min(1)if other else np.full(len(colors),np.inf)
   scores=(weights[:,None]*np.minimum(best[:,None],dist)).sum(0);scores[other]=np.inf
   chosen[k]=int(scores.argmin())
 return colors[chosen]

def candidate_colors(colors,weights):
 kinds=np.array([material(c)for c in colors]);out=[]
 for kind,k in [('ink',4),('warm',14),('green',7),('blue',5),('purple',6),('ivory',4),('steel',5)]:
  selected=kinds==kind
  if selected.any():out.extend(weighted_medoids(colors[selected],weights[selected],k).tolist())
 return np.unique(np.asarray(out,dtype=np.uint8),axis=0)

def material_distances(colors,candidates):
 delta=colors[:,None,:].astype(float)-candidates[None,:,:]
 dist=(delta*delta*np.array([.95,1.2,.9])).sum(2)
 a=np.array([material(c)for c in colors]);b=np.array([material(c)for c in candidates])
 penalty={'ink':1100,'green':850,'blue':430,'purple':620,'ivory':1000,'steel':150,'warm':0}
 for kind,cost in penalty.items():dist+=(a[:,None]==kind)*(b[None,:]!=kind)*cost
 # Brown leather must never become green skin or purple cloth.
 dist+=(a[:,None]=='warm')*np.isin(b,['green','purple','blue','steel'])[None,:]*300
 return dist

def best_four(hist,dist):
 keep=hist>0;w=hist[keep];d=dist[keep];best=np.full(len(w),np.inf);chosen=[]
 for _ in range(4):
  scores=(w[:,None]*np.minimum(best[:,None],d)).sum(0);scores[chosen]=np.inf
  k=int(scores.argmin());chosen.append(k);best=np.minimum(best,d[:,k])
 for _ in range(2):
  for slot in range(4):
   others=chosen[:slot]+chosen[slot+1:];best=d[:,others].min(1)
   scores=(w[:,None]*np.minimum(best[:,None],d)).sum(0);scores[others]=np.inf;chosen[slot]=int(scores.argmin())
 return tuple(sorted(chosen))

def fit_shared_palettes(scenes,masks,occlusion):
 rgb=scenes>>3;colors,inverse=np.unique(rgb.reshape(-1,3),axis=0,return_inverse=True);indices=inverse.reshape(4,144,160)
 weights=np.ones((4,144,160),float);weights[masks]=3.5
 # Important face, tusk and hair contours outweigh large flat warm terrain.
 weights[:,41:76,30:74]*=np.where(masks[:,41:76,30:74],2.4,1.)
 weights[rgb.max(3)<=4]*=2.0
 weights[:,occlusion]=0
 globalhist=np.bincount(inverse,weights=weights.ravel(),minlength=len(colors))
 candidates=candidate_colors(colors,globalhist);dist=material_distances(colors,candidates)
 union=masks.any(0);groups=[];group_lookup=np.zeros((4,360),np.int16);shared_positions=[]
 for tile in range(360):
  ty,tx=divmod(tile,20);y,x=ty*8,tx*8
  # Any pixel outside the union is canonical shared background. Such a tile
  # uses the same palette across states, guaranteeing identical decoded sky.
  shared=not union[y:y+8,x:x+8].all()
  role_groups=[range(4)]if shared else [[r]for r in range(4)]
  if shared:shared_positions.append(tile)
  for roles in role_groups:
   hist=np.zeros(len(colors),float)
   for r in roles:
    hist+=np.bincount(indices[r,y:y+8,x:x+8].ravel(),weights=weights[r,y:y+8,x:x+8].ravel(),minlength=len(colors));group_lookup[r,tile]=len(groups)
   groups.append(hist)
 hist=np.asarray(groups)
 options=list(dict.fromkeys(best_four(h,dist)for h in hist if h.any()))
 costs=np.column_stack([dist[:,o].min(1)for o in options]);errors=hist@costs
 chosen=[int(errors.sum(0).argmin())]
 while len(chosen)<5:
  scores=np.minimum(errors,errors[:,chosen].min(1)[:,None]).sum(0);scores[chosen]=np.inf;chosen.append(int(scores.argmin()))
 palettes=[options[k]for k in chosen]
 for _ in range(8):
  costs=np.column_stack([dist[:,o].min(1)for o in palettes]);errors=hist@costs;assignment=errors.argmin(1)
  newer=[]
  for slot in range(5):
   grouped=hist[assignment==slot].sum(0)
   newer.append(best_four(grouped,dist)if grouped.any()else palettes[slot])
  if newer==palettes:break
  palettes=newer
 # Sort shades within each opaque palette by luminance, with index0 as an
 # ordinary opaque shade. No alpha/background reservation consumes a color.
 palettes=np.array([[*sorted(o,key=lambda k:float(candidates[k]@np.array([.299,.587,.114])))]for o in palettes])
 errors=hist@np.column_stack([dist[:,o].min(1)for o in palettes]);assignment=errors.argmin(1)
 indexed=np.zeros((4,144,160),np.uint8);decoded=np.zeros((4,144,160,3),np.uint8);attrs=np.zeros((4,360),np.uint8);tile_records=[]
 for r in range(4):
  records=[]
  for tile in range(360):
   ty,tx=divmod(tile,20);y,x=ty*8,tx*8;slot=int(assignment[group_lookup[r,tile]]);pal=palettes[slot]
   select=dist[indices[r,y:y+8,x:x+8]][:,:,pal].argmin(2);indexed[r,y:y+8,x:x+8]=select;decoded[r,y:y+8,x:x+8]=expand(candidates[pal][select]);attrs[r,tile]=slot+2
   records.append({'tile':tile,'xy':[x,y],'palette':slot+2,'shared_background_assignment':tile in shared_positions,'source_figure_pixels':int(masks[r,y:y+8,x:x+8].sum())})
  tile_records.append(records)
 outside=~union&~occlusion
 assert all(np.array_equal(decoded[0][outside],decoded[r][outside])for r in range(1,4))
 return indexed,decoded,candidates[palettes],attrs,tile_records,{'source_rgb555_colors':len(colors),'candidate_material_colors':len(candidates),'palette_fit_groups':len(groups),'shared_tile_positions':len(shared_positions),'outside_union_background_pixels':int(outside.sum()),'outside_union_and_ui_background_identical_all_four':True,'palette0_is_opaque':True,'shared_scene_palettes':True}

def encode_tile(tile):
 out=bytearray()
 for row in tile:
  out.extend((sum((int(v)&1)<<(7-k)for k,v in enumerate(row)),sum((int(v)>>1)<<(7-k)for k,v in enumerate(row))))
 return bytes(out)

def encode_scene(indexed,paletteattrs):
 bank1=bytearray(4096);bank0=bytearray(1536);tiles=[];known={};tilemap=bytearray();attrs=bytearray()
 for tile in range(360):
  y,x=divmod(tile,20);packet=encode_tile(indexed[y*8:y*8+8,x*8:x*8+8])
  if packet not in known:known[packet]=len(tiles);tiles.append(packet)
  unique=known[packet]
  if unique>=MAX_TILES:raise RuntimeError(f'{len(tiles)} unique tiles exceeds measured hardware limit{MAX_TILES}; no silhouette or scene simplification applied')
  if unique<240:
   physical=unique if unique<208 else unique+16;bank1[physical*16:physical*16+16]=packet;tid=(physical+0x80)&255;attr=int(paletteattrs[tile])|8
   assert not(0x50<=tid<=0x5f)
  else:
   physical=unique-240;assert physical<72;bank0[physical*16:physical*16+16]=packet;tid=physical;attr=int(paletteattrs[tile])
  tilemap.append(tid);attrs.append(attr)
 assert not any(bank1[208*16:224*16])
 assert not any(bank0[72*16:])
 return bytes(bank1),bytes(bank0),bytes(tilemap),bytes(attrs),len(tiles)

def decode_scene(bank1,bank0,tilemap,attributes,palettes):
 decoded=np.zeros((144,160,3),np.uint8)
 for tile,(tid,attr)in enumerate(zip(tilemap,attributes)):
  bank=1 if attr&8 else 0
  assert 2<=attr&7<=6 and not(attr&0xf0)
  if bank:
   assert not(0x50<=tid<=0x5f)
   offset=((tid-0x80)&255)*16;packet=bank1[offset:offset+16]
  else:
   assert tid<0x48;packet=bank0[tid*16:tid*16+16]
  yy,xx=divmod(tile,20)
  for y in range(8):
   lo,hi=packet[y*2:y*2+2]
   for x in range(8):
    value=((lo>>(7-x))&1)|(((hi>>(7-x))&1)<<1)
    decoded[yy*8+y,xx*8+x]=expand(palettes[(attr&7)-2][value])
 return decoded

def main():
 GFX.mkdir(parents=True,exist_ok=True);REVIEW.mkdir(parents=True,exist_ok=True)
 paths=preserve_sources();scenes,masks,records,bg=make_scenes(paths)
 # The engine always paints these source cells with opaque cards/name bars.
 # Normalize only hidden pixels, leaving the visible scenic composition and
 # the entire figure untouched. This avoids spending scarce VRAM on pixels
 # which can never reach the LCD.
 occlusion=np.zeros((144,160),bool)
 occlusion[3*8:13*8,13*8:19*8]=True
 occlusion[2*8:4*8,1*8:11*8]=True
 occlusion[16*8:17*8,1*8:19*8]=True
 assert not masks[:,occlusion].any()
 fitted=scenes.copy();fitted[:,occlusion]=bg[0,0]
 indexed,decoded,palettes,attrs,tiles,fit=fit_shared_palettes(fitted,masks,occlusion)
 hidden_cells=[[x,y]for y in range(18)for x in range(20)if occlusion[y*8:y*8+8,x*8:x*8+8].all()]
 paldata=b''.join(int(int(r)|(int(g)<<5)|(int(b)<<10)).to_bytes(2,'little')for p in palettes for r,g,b in p)
 assert len(paldata)==40
 manifest={'version':'v0.2.18','status':'PASS','import_kind':'explicitly lossy native BG raster import; no native grid recovery claimed','source_art_modified':False,'smoothing':False,'alpha':'binary; alpha>=128','scene_size':[160,144],'figure_fit_max':[64,84],'figure_fit_box':[18,41,82,125],'native_palette_slots':[2,3,4,5,6],'reserved_ui_palette_slots':[0,1,7],'shared_palette_rgb555':palettes.tolist(),'hardware_tile_limit':312,'reserved_bank0_ids':[0x48,0x5f],'occluded_source_cell_normalization':{'cells_xy_tiles':hidden_cells,'cells':len(hidden_cells),'normalization_rgb':bg[0,0].tolist(),'pixels_may_reach_lcd':False,'engine_opaque_panel_interior':[104,24,152,104],'engine_opaque_namebar':[8,16,88,32],'engine_opaque_footer':[8,128,152,136],'visible_source_pixels_modified':0},'reserved_bank1_ids':[0x50,0x5f],'background_source_sha256':sha(paths['background'].read_bytes()),'background_nearest_rgb_sha256':sha(bg.tobytes()),'fit':fit,'sources':{k:{'path':rel(v),'sha256':sha(v.read_bytes()),'size':list(Image.open(v).size)}for k,v in paths.items()},'states':{}}
 asm=['; Generated by tools/import_peon_welcome_scenes_v0218.py.','; Five shared opaque BG palettes2..6; UI palettes0/1/7 untouched.','; Bank1 IDs$50..$5f reserved for bronze frame; bank0 IDs$48..$5f for labels.','']
 for r,role in enumerate(ROLES):
  target=GFX/role;target.mkdir(exist_ok=True);b1,b0,tmap,at,unique=encode_scene(indexed[r],attrs[r]);roundtrip=decode_scene(b1,b0,tmap,at,palettes);assert np.array_equal(roundtrip,decoded[r]),role;hardware=Image.fromarray(roundtrip);hardware.save(target/'hardware.png');hardware.save(REVIEW/f'{role}_hardware.png');hardware.resize((640,576),Image.Resampling.NEAREST).save(REVIEW/f'{role}_hardware_4x.png')
  files={'tiles_bank1.2bpp':b1,'tiles_bank0.2bpp':b0,'tilemap.bin':tmap,'attrs.bin':at,'palettes.bin':paldata}
  for name,data in files.items():(target/name).write_bytes(data)
  prefix='PeonWelcome'+role.title()+'SceneV0218';asm.append(f'SECTION "Peon welcome {role} v0.2.18", ROMX')
  for suffix,name in [('Tiles1','tiles_bank1.2bpp'),('Tiles0','tiles_bank0.2bpp'),('Tilemap','tilemap.bin'),('Attrs','attrs.bin'),('Palettes','palettes.bin')]:asm.extend([f'{prefix}{suffix}::',f'\tINCBIN "{rel(target/name)}"'])
  asm.extend([f'{prefix}End::',f'assert {prefix}End - {prefix}Tiles1 == 6392',''])
  before=scenes[r]>>3;after=decoded[r]>>3;foreground=masks[r];a=np.array([material(c)for c in before[foreground]]);b=np.array([material(c)for c in after[foreground]])
  metrics={'figure_rgb555_rmse':round(float(np.sqrt(((before[foreground].astype(float)-after[foreground])**2).mean())),3),'figure_material_pixels':{k:{'source':int((a==k).sum()),'hardware':int((b==k).sum())}for k in ('green','ivory','steel','purple','blue','warm','ink')},'source_green_to_non_green':int(((a=='green')&(b!='green')).sum()),'source_warm_to_green':int(((a=='warm')&(b=='green')).sum())}
  manifest['states'][role]={**records[role],'unique_tiles':unique,'bank1_used':min(unique,240),'bank0_used':max(0,unique-240),'packet_decode_exact_pixel_roundtrip':True,'opaque_scene_pixels_using_color_index0':int((indexed[r]==0).sum()),'palette_sha256':sha(paldata),'hardware_rgb_sha256':sha(decoded[r].tobytes()),'files':{n:{'path':rel(target/n),'bytes':len(data),'sha256':sha(data)}for n,data in files.items()},'metrics':metrics,'tiles':tiles[r]}
 (GFX/'graphics.asm').write_text('\n'.join(asm)+'\n');(GFX/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(REVIEW/'import_report.json').write_text(json.dumps(manifest,indent=2)+'\n')
 contact=Image.new('RGB',(640,600),(23,8,17));draw=ImageDraw.Draw(contact)
 for n,role in enumerate(ROLES):
  xx=(n%2)*320;yy=(n//2)*(288+12);draw.text((xx+4,yy+2),role,fill=(255,231,189));contact.paste(Image.fromarray(decoded[n]).resize((320,288),Image.Resampling.NEAREST),(xx,yy+12))
 contact.save(REVIEW/'four_states_contact_2x.png')
 print(json.dumps({'status':'PASS','shared_palettes':palettes.tolist(),'fit':fit,'unique_tiles':{r:manifest['states'][r]['unique_tiles']for r in ROLES},'metrics':{r:manifest['states'][r]['metrics']for r in ROLES}},indent=2))
if __name__=='__main__':main()
