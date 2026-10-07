#!/usr/bin/env python3
"""Compile the approved title artwork to native CGB tiles and eight palettes.

This is an asset compiler: the input remains unchanged. Every 8x8 output tile
uses one four-colour RGB555 palette, with both CGB VRAM banks supplying 360 tiles.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'references/generated/title_portal_redrawn_v2.png'
OUT=ROOT/'gfx/title/peon_portal'
PREVIEW=ROOT/'references/generated/title_portal_gbc'
FONT={
 'A':['01110','10001','10001','11111','10001','10001','10001'],
 'B':['11110','10001','10001','11110','10001','10001','11110'],
 'C':['01111','10000','10000','10000','10000','10000','01111'],
 'E':['11111','10000','10000','11110','10000','10000','11111'],
 'F':['11111','10000','10000','11110','10000','10000','10000'],
 'H':['10001','10001','10001','11111','10001','10001','10001'],
 'I':['11111','00100','00100','00100','00100','00100','11111'],
 'K':['10001','10010','10100','11000','10100','10010','10001'],
 'L':['10000','10000','10000','10000','10000','10000','11111'],
 'M':['10001','11011','10101','10101','10001','10001','10001'],
 'N':['10001','11001','11001','10101','10011','10011','10001'],
 'O':['01110','10001','10001','10001','10001','10001','01110'],
 'P':['11110','10001','10001','11110','10000','10000','10000'],
 'R':['11110','10001','10001','11110','10100','10010','10001'],
 'S':['01111','10000','10000','01110','00001','00001','11110'],
 'T':['11111','00100','00100','00100','00100','00100','00100'],
 'W':['10001','10001','10001','10101','10101','11011','10001'],
 ' ':['00000']*7,
}

def text(image,string,y):
    x=(160-(len(string)*6-1))//2
    for c in string:
        for dy,row in enumerate(FONT[c]):
            for dx,v in enumerate(row):
                if v=='1': image.putpixel((x+dx,y+dy),(255,247,206))
        x+=6

def main():
    OUT.mkdir(parents=True,exist_ok=True); PREVIEW.mkdir(parents=True,exist_ok=True)
    native=Image.open(SOURCE).convert('RGB').resize((160,144),Image.Resampling.LANCZOS)
    draw=ImageDraw.Draw(native)
    draw.rectangle((30,5,129,14),fill=(17,13,18))
    text(native,'PEON OF WARCRAFT',7)
    draw.rectangle((44,113,116,137),fill=(17,13,18))
    for label,y in [('CLICK START',114),('TO BECOME',122),('WARCHIEF',130)]: text(native,label,y)
    pixels=np.asarray(native,dtype=np.float64)/255*31
    tiles=pixels.reshape(18,8,20,8,3).transpose(0,2,1,3,4).reshape(360,64,3)
    # Semantic initial palettes keep rare flames, grass and violet sky represented.
    palettes=np.array([
        [[2,1,4],[10,2,10],[19,2,9],[29,7,5]],
        [[3,2,3],[9,8,10],[16,13,13],[27,14,6]],
        [[3,2,3],[12,10,12],[21,18,16],[29,19,9]],
        [[8,2,2],[25,6,2],[31,17,2],[31,29,15]],
        [[11,5,12],[21,12,18],[30,18,9],[31,29,18]],
        [[2,5,3],[8,12,4],[17,17,6],[28,18,6]],
        [[2,2,3],[10,8,9],[19,14,9],[30,20,7]],
        [[2,2,2],[29,18,4],[31,30,25],[27,2,4]],
    ],dtype=np.float64)
    weights=np.array([0.9,1.25,0.85])
    ui=np.array([i//20<2 or i//20>=14 for i in range(360)])
    for iteration in range(18):
        distances=((tiles[:,None,:,None,:]-palettes[None,:,None,:,:])**2*weights).sum(axis=-1)
        error=distances.min(axis=-1).sum(axis=-1)
        assignment=error.argmin(axis=1)
        assignment[ui]=7
        for pal in range(7):
            group=tiles[assignment==pal].reshape(-1,3)
            if len(group)==0: continue
            indices=((group[:,None,:]-palettes[pal][None,:,:])**2*weights).sum(axis=-1).argmin(axis=1)
            for colour in range(4):
                points=group[indices==colour]
                if len(points): palettes[pal,colour]=np.rint(points.mean(axis=0))
    palettes=np.clip(np.rint(palettes),0,31).astype(np.uint8)
    distances=((tiles[:,None,:,None,:]-palettes[None,:,None,:,:].astype(float))**2*weights).sum(axis=-1)
    assignment=distances.min(axis=-1).sum(axis=-1).argmin(axis=1)
    assignment[ui]=7
    chosen=palettes[assignment]
    indices=((tiles[:,:,None,:]-chosen[:,None,:,:].astype(float))**2*weights).sum(axis=-1).argmin(axis=2)
    data=bytearray(); tilemap=bytearray(); attrmap=bytearray()
    rendered=np.empty((360,64,3),dtype=np.uint8)
    for i,tile in enumerate(indices.reshape(360,8,8)):
        for row in tile:
            data.extend([sum((int(v)&1)<<(7-x) for x,v in enumerate(row)),
                         sum(((int(v)>>1)&1)<<(7-x) for x,v in enumerate(row))])
        # Signed BG addressing: first 128 tiles at $9000, next 128 at $8800.
        local=i%256
        tilemap.append(local)
        attrmap.append(int(assignment[i]) | (8 if i>=256 else 0))
        rgb=chosen[i,indices[i]].astype(np.uint16)
        rendered[i]=((rgb<<3)|(rgb>>2)).astype(np.uint8)
    palette_data=bytearray()
    for palette in palettes:
        for r,g,b in palette:
            colour=int(r)|(int(g)<<5)|(int(b)<<10)
            palette_data.extend(colour.to_bytes(2,'little'))
    for filename,content in [('tiles.2bpp',data),('screen.tilemap',tilemap),('screen.attrmap',attrmap),('palettes.bin',palette_data)]:
        (OUT/filename).write_bytes(content)
    image=Image.fromarray(rendered.reshape(18,20,8,8,3).transpose(0,2,1,3,4).reshape(144,160,3))
    image.save(PREVIEW/'title_portal_native_160x144.png')
    image.resize((960,864),Image.Resampling.NEAREST).save(PREVIEW/'title_portal_native_preview_6x.png')
    report={'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'width':160,'height':144,'tiles':360,'bank_0_tiles':256,'bank_1_tiles':104,
            'background_palettes':8,'colours_per_tile':4,'palette_format':'RGB555',
            'caption':'Compiler reconstruction; emulator capture is validated separately'}
    (PREVIEW/'conversion_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__': main()
