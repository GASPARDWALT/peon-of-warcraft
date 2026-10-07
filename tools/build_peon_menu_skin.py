#!/usr/bin/env python3
"""Compile a native six-tile Warcraft menu frame and RGB555 style previews.

Glyph indexes $79..$7e match Crystal's existing textbox characters. No new
font encoding, save fields or menu labels are required. Transparent exported
frame pieces are the same eight-pixel tiles used by the ROM.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"references/generated/durotar_v021/menu_skin"
GFX=ROOT/"gfx/pack/peon_menu_skin"
PALETTES=[
    [(255,239,189),(189,132,66),(107,66,33),(0,0,0)],
    [(66,24,16),(189,132,66),(99,49,33),(255,247,214)],
    [(49,33,24),(107,66,33),(189,132,66),(255,247,214)],
    [(255,239,189),(222,173,82),(148,57,33),(66,41,24)],
]
QUALITY_COLOURS=[(157,157,157),(255,255,255),(30,255,0),(0,112,221)]
NAMES=["top_left","horizontal","top_right","vertical","bottom_left","bottom_right"]

def glyphs():
    corner=Image.new("P",(8,8));draw=ImageDraw.Draw(corner)
    draw.line([(7,1),(3,1),(1,3),(1,7)],fill=3,width=3)
    draw.line([(7,2),(3,2),(2,3),(2,7)],fill=1,width=1)
    draw.line([(7,4),(4,4),(4,7)],fill=2,width=1)
    draw.point((3,2),fill=0)
    horizontal=Image.new("P",(8,8));draw=ImageDraw.Draw(horizontal)
    draw.rectangle((0,1,7,4),fill=3);draw.line((0,2,7,2),fill=1)
    draw.line((0,4,7,4),fill=2)
    vertical=Image.new("P",(8,8));draw=ImageDraw.Draw(vertical)
    draw.rectangle((1,0,4,7),fill=3);draw.line((2,0,2,7),fill=1)
    draw.line((4,0,4,7),fill=2)
    frames=[corner,horizontal,corner.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
            vertical,corner.transpose(Image.Transpose.FLIP_TOP_BOTTOM),
            corner.transpose(Image.Transpose.ROTATE_180)]
    for frame in frames:
        frame.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
    return frames

def pack(frames):
    data=bytearray()
    for image in frames:
        for row in np.array(image):
            data.append(sum((int(c)&1)<<(7-i) for i,c in enumerate(row)))
            data.append(sum(((int(c)>>1)&1)<<(7-i) for i,c in enumerate(row)))
    assert len(data)==16*len(frames)
    return bytes(data)

def percent_glyph():
    image=Image.new("P",(8,8));image.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
    rows=[" ##    #", "#  #  # ", "#  # #  ", " ## #   ",
          "   # ## ", "  # #  #", " #  #  #", "#    ## "]
    for y,row in enumerate(rows):
        for x,mark in enumerate(row):
            if mark=="#":image.putpixel((x,y),3)
    return image

def rgba(image,palette):
    pixels=np.array(image)
    alpha=np.where(pixels==0,0,255).astype("uint8")
    return Image.fromarray(np.dstack((np.array(palette,dtype="uint8")[pixels],alpha)),"RGBA")

def preview(frames,quality):
    palettes=[[tuple((c>>3)<<3 for c in colour) for colour in palette] for palette in PALETTES]
    palettes[2][3]=tuple((c>>3)<<3 for c in QUALITY_COLOURS[quality])
    indices=np.zeros((144,160),dtype="uint8")
    attrs=np.zeros((18,20),dtype="uint8")
    attrs[0,:]=attrs[-1,:]=3;attrs[:,0]=attrs[:,-1]=3
    attrs[1:3,1:19]=1;attrs[9,1:19]=2
    slots={(0,0):0,(19,0):2,(0,17):4,(19,17):5}
    for x in range(1,19):slots[x,0]=slots[x,17]=1
    for y in range(1,17):slots[0,y]=slots[19,y]=3
    for (x,y),number in slots.items():indices[y*8:(y+1)*8,x*8:(x+1)*8]=np.array(frames[number])
    font=Image.open(ROOT/"gfx/font/english.png").convert("L")
    def text(x,y,value):
        for i,char in enumerate(value):
            if char==" ":continue
            if "A"<=char<="Z":number=ord(char)-ord("A")
            elif "a"<=char<="z":number=ord(char)-ord("a")+0x20
            elif "0"<=char<="9":number=ord(char)-ord("0")+0x76
            else:continue
            tile=np.array(font.crop(((number%16)*8,(number//16)*8,(number%16+1)*8,(number//16+1)*8)))
            indices[y*8:(y+1)*8,(x+i)*8:(x+i+1)*8]=np.where(tile<128,3,0)
    text(2,1,"PEON OF WARCRAFT")
    text(2,4,"SHAMAN APPRENTICE")
    text(2,6,"CRUDE MACE")
    text(2,8,"ITEM QUALITY")
    text(2,9,["GRAY","WHITE","GREEN","BLUE"][quality])
    text(2,12,"BAGS AND EQUIPMENT")
    text(2,15,"A EQUIP   B BACK")
    colours=np.zeros((144,160,3),dtype="uint8")
    for y in range(18):
        for x in range(20):
            colours[y*8:(y+1)*8,x*8:(x+1)*8]=np.array(palettes[int(attrs[y,x])],dtype="uint8")[indices[y*8:(y+1)*8,x*8:(x+1)*8]]
    return Image.fromarray(colours,"RGB")

def main():
    OUT.mkdir(parents=True,exist_ok=True);GFX.parent.mkdir(parents=True,exist_ok=True)
    frames=glyphs();sheet=Image.new("P",(48,8));sheet.putpalette(frames[0].getpalette())
    transparent=Image.new("RGBA",(48,8))
    for i,(name,frame) in enumerate(zip(NAMES,frames)):
        sheet.paste(frame,(i*8,0));public=rgba(frame,PALETTES[3])
        public.save(OUT/f"frame_{name}.png");transparent.alpha_composite(public,(i*8,0))
    sheet.save(GFX.with_suffix(".png"));GFX.with_suffix(".2bpp").write_bytes(pack(frames))
    percent=percent_glyph();percent_path=GFX.with_name("peon_menu_percent")
    percent.save(percent_path.with_suffix(".png"))
    percent_path.with_suffix(".2bpp").write_bytes(pack([percent]))
    rgba(percent,PALETTES[1]).save(OUT/"percent_glyph.png")
    transparent.save(OUT/"frame_tiles_transparent.png")
    previews=[preview(frames,i) for i in range(4)]
    for name,image in zip(["gray","white","green","blue"],previews):
        image.save(OUT/f"menu_skin_{name}_native.png")
        image.resize((640,576),Image.Resampling.NEAREST).save(OUT/f"menu_skin_{name}_4x.png")
    enlarged=[im.resize((640,576),Image.Resampling.NEAREST) for im in previews]
    enlarged[0].save(OUT/"quality_colours_preview.gif",save_all=True,append_images=enlarged[1:],duration=650,loop=0)
    (OUT/"manifest.json").write_text(json.dumps({"frame_glyphs":["0x79","0x7a","0x7b","0x7c","0x7d","0x7e"],
        "2bpp_bytes":96,"frame_tile_size":[8,8],"percent_tile_id":"0x78","percent_2bpp_bytes":16,
        "total_skin_tiles":7,"palette_rgb555":[[[c>>3 for c in colour] for colour in palette] for palette in PALETTES],
        "quality_ink_rgb555":[[c>>3 for c in colour] for colour in QUALITY_COLOURS],
        "preview_kind":"Native style preview; actual menus retain their existing layouts and labels."},indent=2)+"\n")
    print(f"Six native menu-frame tiles and four quality previews compiled in {OUT.relative_to(ROOT)}")

if __name__=="__main__":main()
