#!/usr/bin/env python3
"""Compile native region maps/fog to a CGB display without changing SRAM."""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from build_durotar_assets import ROOT, OUT, BG, REGION_BGS
from compile_peon_title import FONT

FONT.update({
 'D':['11110','10001','10001','10001','10001','10001','11110'],
 'G':['01111','10000','10000','10111','10001','10001','01110'],
 'J':['00111','00010','00010','00010','10010','10010','01100'],
 'U':['10001','10001','10001','10001','10001','10001','01110'],
 'V':['10001','10001','10001','10001','10001','01010','00100'],
 'Y':['10001','10001','01010','00100','00100','00100','00100'],
 'Z':['11111','00001','00010','00100','01000','10000','11111'],
 'X':['10001','10001','01010','00100','01010','10001','10001'],
})
SPECS=[('DEN','TheDen','THE DEN'),('VALLEY','ValleyOfTrials','VALLEY OF TRIALS'),
 ('ROAD','DurotarRoad','DUROTAR ROAD'),('SENJIN','SenjinVillage','SENJIN VILLAGE'),
 ('RAZOR','RazorHill','RAZOR HILL'),('ORGRIMMAR','OrgrimmarGate','ORGRIMMAR GATE'),
 ('CAVERN','BurningBladeCavern','BURNING BLADE CAVERN'),('FOG',None,'DUROTAR MAP')]

def text(im,s,y,colour):
    x=(160-len(s)*6+1)//2
    for c in s:
        for dy,row in enumerate(FONT[c]):
            for dx,v in enumerate(row):
                if v=='1':im.putpixel((x+dx,y+dy),colour)
        x+=6

def compile_map(im,pals):
    arr=np.array(im,dtype=float)/8
    tiles=arr.reshape(18,8,20,8,3).transpose(0,2,1,3,4).reshape(360,64,3)
    pals=np.array(pals,dtype='uint8')>>3
    delta=((tiles[:,None,:,None,:]-pals[None,:,None,:,:].astype(float))**2).sum(axis=-1)
    assignment=delta.min(axis=-1).sum(axis=-1).argmin(axis=1)
    chosen=pals[assignment]
    indices=((tiles[:,:,None,:]-chosen[:,None,:,:].astype(float))**2).sum(axis=-1).argmin(axis=-1)
    pixels=chosen[np.arange(360)[:,None],indices]
    rendered=((pixels.astype('uint16')<<3)|(pixels.astype('uint16')>>2)).astype('uint8')
    out=bytearray()
    for tile in indices.reshape(360,8,8):
        for row in tile:
            out.extend([sum((int(v)&1)<<(7-x) for x,v in enumerate(row)),sum(((int(v)>>1)&1)<<(7-x) for x,v in enumerate(row))])
    out.extend(bytes(i%256 for i in range(360)))
    out.extend(bytes(int(assignment[i])|(8 if i>=256 else 0) for i in range(360)))
    for palette in pals:
        for r,g,b in palette:out.extend((int(r)|(int(g)<<5)|(int(b)<<10)).to_bytes(2,'little'))
    reconstruction=Image.fromarray(rendered.reshape(18,20,8,8,3).transpose(0,2,1,3,4).reshape(144,160,3))
    return out,reconstruction

def main():
    global BG, REGION_BGS
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=OUT)
    parser.add_argument('--output',type=Path,default=OUT)
    args=parser.parse_args()
    if args.source.name=='world':
        import build_durotar_world as world
        BG, REGION_BGS=world.BG,world.REGION_BGS
    dest=ROOT/'gfx/peon_maps';dest.mkdir(parents=True,exist_ok=True)
    preview=args.output/'zone_maps';preview.mkdir(parents=True,exist_ok=True)
    asm=[]
    for ident,name,title in SPECS:
        im=Image.new('RGB',(160,144),(123,74,41))
        if name:
            miniature=ImageOps.contain(Image.open(args.source/'maps'/(name+'.png')).convert('RGB'),(156,100),Image.Resampling.NEAREST)
            im.paste(miniature,((160-miniature.width)//2,16+(104-miniature.height)//2))
            pals=REGION_BGS[name]
        else:
            im.paste((8,8,8),(2,16,158,120));pals=BG
            text(im,'UNDISCOVERED',60,(255,247,214));text(im,'EXPLORE TO REVEAL',72,(255,247,214))
        text(im,title,4,(255,247,214))
        text(im,'LEFT RIGHT CHANGE ZONE',124,(255,247,214))
        text(im,'A B SELECT BACK',136,(255,247,214))
        binary,native=compile_map(im,pals)
        (dest/(ident.lower()+'.bin')).write_bytes(binary)
        native.save(preview/(ident.lower()+'.png'))
        native.resize((640,576),Image.Resampling.NEAREST).save(preview/(ident.lower()+'_4x.png'))
        asm.extend([f'SECTION "Peon Zone Map {ident}", ROMX',f'PeonMap_{ident}:',f'INCBIN "gfx/peon_maps/{ident.lower()}.bin"',''])
    (ROOT/'gfx/peon_zone_maps.asm').write_text('\n'.join(asm).rstrip()+'\n')
    print('Compiled eight native map/fog screens')

if __name__=='__main__':main()
