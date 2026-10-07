#!/usr/bin/env python3
"""Compile imp sprites and bag icons from the repository concept atlas."""
from pathlib import Path
import sys,os
sys.path.insert(0,str(Path('tools').resolve()))
import build_durotar_assets as b
from PIL import Image
os.chdir(b.ROOT)
out=b.OUT
src=Image.open(out/'concept_imp_and_gear.png').convert('RGBA')
pal=[(255,255,255),(222,41,24),(255,206,57),(8,8,8)]
dirs=[b.indexed(b.cell(src,0,c,3,4,16),pal) for c in range(4)]
frames=[b.bob(f,d,p) for p in range(3) for d,f in zip(b.DIRS,dirs)]
b.export_animation('imp',[b.rgba(f) for f in frames],'overworld',[f'{d}_step_{p}' for p in range(3) for d in b.DIRS])
sheet=Image.new('P',(16,96));sheet.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
for i,j in enumerate([0,1,2,4,5,6]):sheet.paste(frames[j],(0,i*16))
sheet.save('gfx/sprites/peon_imp.png')
pal=[*pal[:3],(0,0,0)]
front=b.indexed(b.cell(src,1,0,3,4,56),pal,white=True);cast=b.indexed(b.cell(src,1,2,3,4,56),pal,white=True);back=b.indexed(b.cell(src,1,1,3,4,48),pal,white=True)
b.export_animation('imp',[b.rgba(f) for f in (front,cast,cast,front)],'battle',['idle','prepare','cast','return']);b.rgba(back).save(out/'battle/imp/back.png')
sheet=Image.new('P',(56,224));sheet.putpalette(front.getpalette())
for i,f in enumerate((front,cast,cast,front)):sheet.paste(f,(0,i*56))
sheet.save('gfx/pokemon/geodude/front.png');back.save('gfx/pokemon/geodude/back.png')
Path('gfx/pokemon/geodude/anim.asm').write_text('\tframe 0, 10\n\tframe 1, 08\n\tframe 2, 08\n\tframe 3, 10\n\tendanim\n')
Path('gfx/pokemon/geodude/anim_idle.asm').write_text('\tframe 0, 12\n\tframe 1, 08\n\tframe 0, 12\n\tendanim\n')
Path('gfx/pokemon/geodude/shiny.pal').write_text('\tRGB 27, 05, 03\n\tRGB 31, 25, 07\n')
for c,name in enumerate(('small_pouch','leather_bag','worn_mace','shaman_mace')):
 f=b.indexed(b.cell(src,2,c,3,4,16),b.OBJ[2]);b.rgba(f).save(out/'inventory'/f'{name}.png')
