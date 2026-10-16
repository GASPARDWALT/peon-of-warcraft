"""Pure native32 palette-fit helpers, no files written on import.
Source: Shaman v20 ROOT-reviewed conversion. All geometry is supplied RGBA32.
fit() skin classification is ORC-GREEN only; adapt material masks for trolls
or purple robes, do not blindly interpret their colors as orc skin.
Palette layout is the unchanged v19 world RGB555 slots.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
from peon_world_readability_profile_v0219 import PALETTES

def encode(image):
 values=np.array(image);height,width=values.shape;out=bytearray()
 assert height==width==32
 for y in range(0,height,8):
  for x in range(0,width,8):
   for iy in range(8):
    lo=hi=0
    for ix in range(8):
     v=int(values[y+iy,x+ix]);lo|=(v&1)<<(7-ix);hi|=((v>>1)&1)<<(7-ix)
    out.extend((lo,hi))
 return bytes(out)

def fit(canvas,d,variant='body'):
 a=np.array(canvas);ids=np.zeros((32,32),dtype=np.uint8);attrs=[];scores=[]
 for tile in range(16):
  yy,xx=divmod(tile,4);ys=slice(yy*8,yy*8+8);xs=slice(xx*8,xx*8+8)
  rgb=a[ys,xs,:3].astype('int32')>>3;visible=a[ys,xs,3]>0
  skin=visible&(rgb[:,:,1]>rgb[:,:,0]*1.08)&(rgb[:,:,1]>rgb[:,:,2]*1.35)&(rgb[:,:,1]>9)
  pale=visible&(rgb[:,:,0]>=21)&(rgb[:,:,1]>=20)&(rgb[:,:,2]>=14)
  brown=visible&(rgb[:,:,0]>rgb[:,:,1]*1.10)&(rgb[:,:,0]>rgb[:,:,2]*1.2)&(rgb[:,:,0]>=4)&~pale
  dark=visible&(rgb.max(2)<7)&~brown
  gy,gx=np.mgrid[yy*8:yy*8+8,xx*8:xx*8+8]
  face=(gy>=9)&(gy<=15)&(gx>=8)&(gx<=24) if d!='back' else np.zeros((8,8),bool)
  protected=pale&face
  errors={};pixels={}
  for p in (2,3,5,6):
   pal=np.array(PALETTES[p][1:]);dist=((rgb[:,:,None,:]-pal)**2).sum(3).astype(float)
   cc=rgb*31/np.maximum(rgb.max(2,keepdims=True),1);pp=pal*31/np.maximum(pal.max(1,keepdims=True),1)
   hue=((cc[:,:,None,:]-pp)**2).sum(3);hue[:,:,2]=0
   dist+=hue*np.where(rgb.sum(2)>12,1.2,0)[:,:,None]
   if p in (2,6):
    dist[:,:,0][skin]+=2400;dist[:,:,2][skin]+=2400
   elif skin.any():dist+=skin[:,:,None]*5000
   if p==2:
    dist[:,:,1][brown]+=4000;dist[:,:,2][brown]+=4000
   elif p==3:
    dist[:,:,0][brown]+=4000;dist[:,:,2][brown]+=4000
   else:dist+=brown[:,:,None]*5500
   if p in (3,5,6):
    dist[:,:,1][protected]+=2400;dist[:,:,2][protected]+=2400
   else:dist+=protected[:,:,None]*3000
   dist[:,:,0][dark]+=2500;dist[:,:,1][dark]+=2500
   weight=np.where(protected,10,np.where(skin,3,np.where(brown,3,np.where(dark,2,1))))
   if variant=='ivory':weight=np.where(pale,5,weight)
   errors[p]=float((dist.min(2)*weight)[visible].sum());pixels[p]=(dist.argmin(2)+1).astype('uint8')
  chosen=6 if protected.any() and int(skin.sum())>=2 and yy==1 else min(errors,key=errors.get)
  attrs.append(chosen);pix=pixels[chosen];pix[~visible]=0;ids[ys,xs]=pix
  scores.append({'tile':tile,'palette':chosen,'source_skin':int(skin.sum()),'source_pale':int(pale.sum()),'source_brown':int(brown.sum()),'protected_face_pale':int(protected.sum()),'errors':errors})
 return ids,attrs,scores

def render(ids,attrs):
 out=np.zeros((32,32,4),dtype='uint8')
 for tile,p in enumerate(attrs):
  y,x=divmod(tile,4);local=ids[y*8:y*8+8,x*8:x*8+8];pal=np.array(PALETTES[p],dtype='uint8');pal=(pal<<3)|(pal>>2)
  out[y*8:y*8+8,x*8:x*8+8,:3]=pal[local];out[y*8:y*8+8,x*8:x*8+8,3]=np.where(local,255,0)
 return Image.fromarray(out)
