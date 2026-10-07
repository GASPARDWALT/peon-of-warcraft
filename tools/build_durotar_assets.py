#!/usr/bin/env python3
"""Compile approved sprite concepts into native GBC assets and transparent PNGs.

The public RGBA exports are the actual indexed sprites used by the game.
Opaque indexed PNGs under gfx are build inputs (OBJ index zero is transparent).
No alpha blending, interpolation or palette overflow occurs in the ROM.
"""
from pathlib import Path
import json
import random
import numpy as np
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v02'
NAMES = ['peon', 'hunter', 'gornek', 'kento', 'thrall', 'warrior', 'warlock', 'boar', 'scorpid']
DIRS = ['down', 'up', 'left', 'right']
OBJ = [
    [(255,255,255),(181,66,33),(41,16,16),(255,41,24)],
    [(255,255,255),(189,140,57),(90,57,132),(8,8,8)],
    [(255,255,255),(148,90,49),(123,181,66),(8,8,8)],
    [(255,255,255),(206,156,90),(99,57,33),(8,8,8)],
    [(255,255,255),(181,123,57),(74,41,16),(255,214,24)],
    [(255,255,255),(222,41,24),(255,206,57),(8,8,8)],
    [(255,255,255),(239,222,181),(82,165,189),(16,33,57)],
    [(255,255,255),(181,156,115),(107,82,57),(41,33,24)],
]
BG = [
    [(239,181,115),(206,123,66),(140,66,41),(49,24,24)],
    [(239,181,115),(214,140,74),(173,90,49),(82,49,33)],
    [(239,181,115),(140,165,74),(82,115,49),(33,57,33)],
    [(181,222,222),(82,165,181),(49,115,140),(33,66,90)],
    [(255,214,132),(222,165,82),(181,115,57),(99,57,33)],
    [(239,181,115),(173,107,66),(107,66,49),(49,33,24)],
    [(239,181,115),(189,74,49),(115,49,41),(41,24,24)],
    [(255,247,214),(255,247,214),(123,74,41),(8,8,8)],
]
REGION_BGS={}
for name,light,mid,shade in [('TheDen',(239,181,115),(214,140,74),(173,90,49)),
 ('ValleyOfTrials',(239,165,99),(206,123,66),(165,82,49)),
 ('DurotarRoad',(239,197,132),(214,165,90),(165,115,57)),
 ('SenjinVillage',(247,222,165),(214,189,115),(173,140,82)),
 ('RazorHill',(231,165,107),(198,115,66),(148,74,41)),
 ('OrgrimmarGate',(222,148,90),(181,99,57),(132,57,33)),
 ('BurningBladeCavern',(140,132,148),(107,99,115),(66,57,74))]:
    pals=[p.copy() for p in BG]
    pals[1]=[light,mid,shade,pals[1][3]]
    if name=='BurningBladeCavern':pals[0]=[(148,140,156),(115,107,123),(74,66,82),(33,24,41)]
    REGION_BGS[name]=pals

def indexed(image, palette, white=False):
    a=np.array(image.convert('RGBA'))
    colours=np.array(palette if white else palette[1:],dtype=float)
    dist=((a[:,:,:3,None].transpose(0,1,3,2).astype(float)-colours)**2).sum(axis=-1)
    values=(dist.argmin(axis=-1)+(0 if white else 1)).astype('uint8')
    values[a[:,:,3]<180]=0
    im=Image.fromarray(values,'P')
    im.putpalette([v for c in palette for v in c]+[0]*756)
    if white:im.info['native_alpha']=Image.fromarray(np.where(a[:,:,3]<180,0,255).astype('uint8'))
    return im

def rgba(im):
    data=np.array(im.convert('RGB'))
    alpha=np.array(im.info['native_alpha']) if 'native_alpha' in im.info else np.where(np.array(im)==0,0,255).astype('uint8')
    return Image.fromarray(np.dstack((data,alpha)),'RGBA')

def cell(source, row, col, rows, cols, size):
    w,h=source.size
    im=source.crop((round(col*w/cols),round(row*h/rows),round((col+1)*w/cols),round((row+1)*h/rows)))
    alpha=im.getchannel('A').point(lambda a:255 if a>=180 else 0)
    bounds=alpha.getbbox()
    assert bounds, (row,col)
    im=im.crop(bounds)
    # Resample once into the native logical grid, then strictly quantize.
    im.thumbnail((size-2,size-1),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(size,size))
    canvas.paste(im,((size-im.width)//2,size-im.height))
    return canvas

def humanoid_cell(source, row, col):
    """Keep all humanoid facings at a consistent native standing height.

    The old width-first fit flattened front/back figures holding wide gear.
    A 15x15 target reserves the top row for a one-pixel walking bob; the complete
    image, including each independently drawn mace/shield orientation, stays
    inside the existing 16x16 OBJ footprint.
    """
    w,h=source.size
    im=source.crop((round(col*w/4),round(row*h/9),round((col+1)*w/4),round((row+1)*h/9)))
    bounds=im.getchannel('A').point(lambda a:255 if a>=180 else 0).getbbox()
    assert bounds, (row,col)
    im=im.crop(bounds).resize((15,15),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(16,16))
    canvas.paste(im,(0,1))
    return canvas

def humanoid_face(frame, name, direction):
    """Preserve the small orc eye landmarks after the final three-color reduction."""
    if name in ('kento','warlock') or direction=='up':return frame
    pixels=np.array(frame)
    candidates=[]
    for y in range(2,8):
        xs=np.flatnonzero(pixels[y,2:14]==2)+2
        if len(xs)>=3:candidates.append((len(xs),-y,xs))
    if not candidates:return frame
    count,negative_y,xs=max(candidates,key=lambda v:(v[0],v[1]))
    y=-negative_y;center=(int(xs[0])+int(xs[-1]))//2
    if direction=='down':eye_x=(center-2,center+2)
    elif direction=='left':eye_x=(int(xs[0])+1,)
    else:eye_x=(int(xs[-1])-1,)
    for x in eye_x:
        if 0<=x<16 and pixels[y,x]==2:pixels[y,x]=3
    out=Image.fromarray(pixels,'P');out.putpalette(frame.getpalette())
    return out

def humanoid_bob(frame, direction, phase):
    if phase==0:return frame.copy()
    out=Image.new('P',(16,16));out.putpalette(frame.getpalette())
    assert not np.any(np.array(frame)[0]),'Idle humanoid needs one top row for bob'
    # Head and torso rise together, with no dropped top pixels or sideways flip.
    out.paste(frame.crop((0,1,16,12)),(0,0))
    left=frame.crop((0,12,8,16));right=frame.crop((8,12,16,16))
    out.paste(left,(0,11 if phase==1 else 12))
    out.paste(right,(8,12 if phase==1 else 11))
    # Stretch the planted upper leg by one row so the raised torso stays joined.
    if phase==1:out.paste(right.crop((0,0,8,1)),(8,11))
    else:out.paste(left.crop((0,0,8,1)),(0,11))
    return out

def bob(frame, direction, phase):
    if phase==0: return frame.copy()
    out=frame.copy()
    # Alternate weight-bearing feet without mirroring equipment or face.
    pixels=np.array(frame)
    out.paste(0,(0,13,16,16))
    legs=frame.crop((0,13,16,16))
    left=legs.crop((0,0,8,3)); right=legs.crop((8,0,16,3))
    out.paste(left,(0,12 if phase==1 else 13))
    out.paste(right,(8,13 if phase==1 else 12))
    return out

def export_animation(name,frames,folder,labels):
    dest=OUT/folder/name; dest.mkdir(parents=True,exist_ok=True)
    sheet=Image.new('RGBA',(frames[0].width*len(frames),frames[0].height))
    for i,(frame,label) in enumerate(zip(frames,labels)):
        frame.save(dest/(label+'.png')); sheet.paste(frame,(i*frame.width,0))
    sheet.save(dest/'sheet.png')
    frames[0].save(dest/'animation.png',save_all=True,append_images=frames[1:],duration=150,loop=0,disposal=1,blend=0)
    # GitHub displays GIF reliably; PNG/APNG files above retain transparency.
    preview=[]
    for frame in frames:
        canvas=Image.new('RGBA',frame.size,(36,31,35,255)); canvas.alpha_composite(frame)
        preview.append(canvas.resize((frame.width*6,frame.height*6),Image.Resampling.NEAREST).convert('RGB'))
    preview[0].save(dest/'preview.gif',save_all=True,append_images=preview[1:],duration=150,loop=0)

def export_humanoid_polish(name, frames):
    """Write true four-phase walking loops and a native before/after record."""
    polish=ROOT/'references/generated/durotar_v021/size_polish'
    dest=OUT/'overworld'/name
    for i,direction in enumerate(DIRS):
        walk=[rgba(frames[j]) for j in (i,i+4,i,i+8)]
        walk[0].save(dest/f'walk_{direction}.png',save_all=True,
                     append_images=walk[1:],duration=120,loop=0,disposal=1,blend=0)
        preview=[]
        for image in walk:
            canvas=Image.new('RGBA',(16,16),(36,31,35,255));canvas.alpha_composite(image)
            preview.append(canvas.resize((128,128),Image.Resampling.NEAREST).convert('RGB'))
        preview[0].save(dest/f'walk_{direction}.gif',save_all=True,
                        append_images=preview[1:],duration=120,loop=0)
    if not (polish/'before'/name).exists():return
    after=polish/'after'/name;after.mkdir(parents=True,exist_ok=True)
    for phase in range(3):
        for i,direction in enumerate(DIRS):
            rgba(frames[phase*4+i]).save(after/f'{direction}_step_{phase}.png')

def humanoid_polish_report():
    polish=ROOT/'references/generated/durotar_v021/size_polish'
    names=[n for n in NAMES[:7] if (polish/'before'/n).exists() and (polish/'after'/n).exists()]
    if not names:return
    comparison=Image.new('RGB',(1040,66+len(names)*146),(36,31,35))
    draw=ImageDraw.Draw(comparison)
    draw.text((12,10),'NATIVE 16x16 - BEFORE / AFTER  |  independent player gear orientations',(239,222,181))
    for i,direction in enumerate(DIRS):
        draw.text((143+i*220,33),direction.upper()+'     BEFORE / AFTER',(239,222,181))
    result={'native_canvas':[16,16],'standing_target':[15,15],
            'upper_body_walking_bob_pixels':1,'player_gear_independent_left_right':True,
            'player_source_frames':12,'npc_source_frames':6,
            'walking_order':['idle','step_a','idle','step_b'],
            'npc_front_back_step_b':'Standard Crystal mirrored step A.',
            'characters':{}}
    for row,name in enumerate(names):
        draw.text((12,85+row*146),name.upper(),(239,222,181))
        result['characters'][name]={}
        for phase in range(3):
            for i,direction in enumerate(DIRS):
                label=f'{direction}_step_{phase}.png'
                before=Image.open(polish/'before'/name/label).convert('RGBA')
                after=Image.open(polish/'after'/name/label).convert('RGBA')
                bb=before.getchannel('A').getbbox();ab=after.getchannel('A').getbbox()
                assert bb and ab and after.size==(16,16)
                result['characters'][name][label]={
                    'before_bbox':list(bb),'after_bbox':list(ab),
                    'before_size':[bb[2]-bb[0],bb[3]-bb[1]],
                    'after_size':[ab[2]-ab[0],ab[3]-ab[1]]}
                if phase==0:
                    for j,image in enumerate((before,after)):
                        checker=Image.new('RGBA',(16,16),(58,51,43,255));d=ImageDraw.Draw(checker)
                        for y in range(0,16,4):
                            for x in range(0,16,4):
                                if (x+y)//4%2:d.rectangle((x,y,x+3,y+3),fill=(75,66,55,255))
                        checker.alpha_composite(image)
                        enlarged=checker.resize((96,96),Image.Resampling.NEAREST)
                        comparison.paste(enlarged,(140+i*220+j*106,65+row*146))
                        box=bb if j==0 else ab
                        draw.text((140+i*220+j*106,164+row*146),
                                  f'{box[2]-box[0]}x{box[3]-box[1]}',(201,183,151))
    comparison.save(polish/'native_before_after.png')
    (polish/'bounding_boxes.json').write_text(json.dumps(result,indent=2)+'\n')
    (polish/'README.md').write_text(
        '# Native humanoid size and walking polish\n\n'
        'The existing 16×16 sprite footprint is unchanged. The peon and six '
        'original humanoid roles use more of that space, with a target of 15×15 '
        'at rest and a one-pixel upper-body walking bob. Every exact opaque '
        'bounding box is recorded in `bounding_boxes.json`; irregular silhouettes '
        'can occupy less than the target.\n\n'
        '![Before and after at native pixel scale](native_before_after.png)\n\n'
        'The player retains twelve independent source frames and separately drawn '
        'left/right equipment. NPCs retain the standard six-frame format and '
        'Crystal’s existing reflection of right-facing and alternate front/back '
        'walking poses. No new OAM size, palette, save field or collision was added.\n\n'
        '**Actual four-phase player source loops:** idle → step A → idle → step B.\n\n'
        + '\n'.join(f'**{direction}** — ![{direction}](../../durotar_v02/overworld/peon/walk_{direction}.gif)\n'
                    for direction in DIRS)
        + '\nEach humanoid folder in `durotar_v02/overworld/` also contains '
        '`walk_down.png`, `walk_up.png`, `walk_left.png`, `walk_right.png` '
        '(transparent APNG) and their GIF previews.\n\n'
        'Regenerate only these assets with:\n\n'
        '```python\nimport runpy\na = runpy.run_path("tools/build_durotar_assets.py")\n'
        'a["characters"](only=a["NAMES"][:7], auxiliary=False)\n```\n')

def characters(only=None, auxiliary=True):
    """Build selected overworld roles without touching battle or terrain assets.

    `characters(only=NAMES[:7], auxiliary=False)` refreshes the humanoid sprite
    sheets, naming sprite and transparent overworld exports only.
    """
    source=Image.open(OUT/'concept_overworld.png').convert('RGBA')
    frames_by_name={}
    pal_indices=[2,2,2,3,2,2,1,4,0]
    selected=set(NAMES if only is None else only)
    assert selected.issubset(NAMES),selected
    for row,name in enumerate(NAMES):
        if name not in selected:continue
        humanoid=name in NAMES[:7]
        dirs=[indexed(humanoid_cell(source,row,col) if humanoid else cell(source,row,col,9,4,16),OBJ[pal_indices[row]]) for col in range(4)]
        if humanoid:dirs=[humanoid_face(frame,name,direction) for direction,frame in zip(DIRS,dirs)]
        animate=humanoid_bob if humanoid else bob
        frames=[animate(frame,direction,phase) for phase in range(3) for direction,frame in zip(DIRS,dirs)]
        if humanoid and name!='peon':
            # Export the standard six-frame NPC renderer's real reflected poses.
            frames[3]=ImageOps.mirror(frames[2]);frames[7]=ImageOps.mirror(frames[6])
            frames[8]=ImageOps.mirror(frames[4]);frames[9]=ImageOps.mirror(frames[5])
            frames[10]=frames[6].copy();frames[11]=frames[7].copy()
        frames_by_name[name]=frames
        labels=[f'{direction}_step_{phase}' for phase in range(3) for direction in DIRS]
        export_animation(name,[rgba(f) for f in frames],'overworld',labels)
        if humanoid:export_humanoid_polish(name,frames)
        # Crystal NPC layout: idle down/up/left, then step down/up/left.
        order=list(range(12)) if name=='peon' else [0,1,2,4,5,6]
        sheet=Image.new('P',(16,16*len(order))); sheet.putpalette(frames[0].getpalette())
        for i,j in enumerate(order): sheet.paste(frames[j],(0,16*i))
        file='peon' if name=='peon' else 'peon_'+name
        sheet.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
        sheet.save(ROOT/f'gfx/sprites/{file}.png')
        if name=='peon':
            naming=Image.new('P',(16,96));naming.putpalette(sheet.getpalette())
            for i,j in enumerate([0,1,2,4,5,6]):
                values=np.array(frames[j]);values=np.where(values==1,2,np.where(values==2,1,values)).astype('uint8')
                naming.paste(Image.fromarray(values,'P'),(0,i*16))
            naming.save(ROOT/'gfx/sprites/peon_naming.png')
    humanoid_polish_report()
    if not auxiliary:return
    # Marker and sleeping pose have a single standard OBJ frame.
    mark=Image.new('P',(16,16));mark.putpalette([v for c in OBJ[4] for v in c]+[0]*756)
    d=ImageDraw.Draw(mark);d.rectangle((6,1,9,9),fill=3);d.rectangle((6,12,9,14),fill=3)
    rgba(mark).save(OUT/'quest_marker.png')
    mark.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
    mark.save(ROOT/'gfx/sprites/peon_quest_marker.png')
    sleep=frames_by_name['peon'][0].rotate(90)
    rgba(sleep).save(OUT/'peon_sleeping.png')
    sleep.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
    sleep.save(ROOT/'gfx/sprites/peon_sleeping.png')
    for filename,name in [('fighter','peon'),('fox','boar'),('monster','scorpid')]:
        frames=frames_by_name[name]
        icon=Image.new('P',(16,32));icon.putpalette(frames[0].getpalette())
        icon.paste(frames[0],(0,0));icon.paste(frames[4],(0,16))
        icon.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
        icon.save(ROOT/f'gfx/icons/{filename}.png')

def battles():
    source=Image.open(OUT/'concept_battle.png').convert('RGBA')
    mapping={'peon':(0,0,0,1),'kento':(1,0,1,1),'thrall':(1,2,1,3),'warrior':(2,0,2,1),'warlock':(2,2,2,3),'boar':(3,0,3,1),'scorpid':(3,2,3,3)}
    pals={'peon':OBJ[2],'kento':OBJ[3],'thrall':OBJ[2],'warrior':OBJ[2],'warlock':OBJ[1],
          'boar':[(255,255,255),(206,156,90),(115,66,33),(0,0,0)],
          'scorpid':[(255,255,255),(222,90,41),(123,41,24),(0,0,0)]}
    pals={name:[*pal[:3],(0,0,0)] for name,pal in pals.items()}
    game_species={'peon':'machop','boar':'rattata','scorpid':'sandshrew'}
    for name,(r,c,br,bc) in mapping.items():
        front=indexed(cell(source,r,c,4,4,56),pals[name],white=True)
        back=indexed(cell(source,br,bc,4,4,48),pals[name],white=True)
        shifted=Image.new('RGBA',(56,56));shifted.paste(rgba(front),(0,-1))
        prepare=indexed(shifted,pals[name],white=True)
        cast=indexed(cell(source,0,2,4,4,56),pals[name],white=True) if name=='peon' else prepare.copy()
        frames=[front,prepare,cast,front.copy()]
        export_animation(name,[rgba(f) for f in frames],'battle',['idle','prepare','cast','return'])
        rgba(back).save(OUT/'battle'/name/'back.png')
        if name not in game_species: continue
        species=game_species[name]
        sheet=Image.new('P',(56,56*4));sheet.putpalette(front.getpalette())
        for i,f in enumerate(frames):sheet.paste(f,(0,56*i))
        sheet.save(ROOT/f'gfx/pokemon/{species}/front.png')
        back.save(ROOT/f'gfx/pokemon/{species}/back.png')
        (ROOT/f'gfx/pokemon/{species}/anim.asm').write_text('\tframe 0, 10\n\tframe 1, 06\n\tframe 2, 08\n\tframe 3, 06\n\tframe 0, 10\n\tendanim\n')
        (ROOT/f'gfx/pokemon/{species}/anim_idle.asm').write_text('\tframe 0, 12\n\tframe 1, 12\n\tframe 0, 12\n\tendanim\n')
        # Avoid inherited alternate shiny creature colours.
        c1,c2=pals[name][1:3]
        rgb=lambda c:', '.join(f'{n>>3:02d}' for n in c)
        (ROOT/f'gfx/pokemon/{species}/shiny.pal').write_text(f'\tRGB {rgb(c1)}\n\tRGB {rgb(c2)}\n')
        if name=='peon':
            trainer=Image.new('P',(56,56));trainer.putpalette(back.getpalette());trainer.paste(back,(4,8))
            indices=np.array(trainer)
            indices=np.where(indices==1,2,np.where(indices==2,1,indices)).astype('uint8')
            trainer=Image.fromarray(indices,'P')
            trainer.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
            trainer.save(ROOT/'gfx/player/chris_back.png')
            indices=np.array(front)
            indices=np.where(indices==1,2,np.where(indices==2,1,indices)).astype('uint8')
            portrait=Image.fromarray(indices,'P')
            portrait.putpalette(trainer.getpalette());portrait.save(ROOT/'gfx/pack/peon_portrait.png')
            front.save(ROOT/'gfx/trainers/chris.png')

def inventory():
    frames=[]
    for kind in range(4):
        im=Image.new('P',(16,16),0);im.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
        d=ImageDraw.Draw(im)
        if kind==0:
            d.line((4,14,10,5),fill=3,width=3);d.line((5,13,10,6),fill=2)
            d.polygon([(8,2),(13,2),(15,5),(12,8),(7,6)],fill=3);d.rectangle((9,3,12,5),fill=1)
        elif kind==1:
            d.ellipse((2,1,14,14),fill=3);d.ellipse((3,2,13,13),fill=1)
            for x in (5,8,11):d.line((x,3,x,12),fill=2)
            d.ellipse((7,6,10,9),fill=3);d.point((8,7),1)
        elif kind==2:
            d.rectangle((5,1,11,13),fill=3);d.rectangle((6,2,10,12),fill=1)
            d.line((3,5,13,5),fill=3);d.point((7,7),3);d.point((9,7),3)
            d.rectangle((7,10,9,11),fill=2)
        else:
            d.polygon([(2,3),(12,1),(14,12),(4,14)],fill=3)
            d.polygon([(3,4),(11,2),(13,11),(5,13)],fill=1)
            d.line((5,5,9,7,7,9,11,10),fill=2);d.rectangle((4,1,6,2),fill=2)
        frames.append(im)
    sheet=Image.new('P',(16,64));sheet.putpalette(frames[0].getpalette())
    for i,frame in enumerate(frames):
        sheet.paste(frame,(0,i*16));palette=[(255,247,214),(189,132,74),(107,66,33),(0,0,0)]
        frame.putpalette([v for c in palette for v in c]+[0]*756)
        rgba(frame).save(OUT/'inventory'/(['crude_mace','wooden_shield','apprentice_totem','durotar_map'][i]+'.png'))
    sheet.save(ROOT/'gfx/pack/peon_icons.png')

def terrain_block(kind):
    if kind==16:return terrain_block(2)
    im=Image.new('P',(32,32),0); d=ImageDraw.Draw(im); rng=random.Random(400+kind)
    for _ in range(16):
        x,y=rng.randrange(32),rng.randrange(32);d.line((x,y,min(31,x+1),y),fill=1)
    if kind==1: # layered cliff, shaded horizontal rock faces
        d.rectangle((0,0,31,31),fill=2)
        for x,y,w in [(0,0,18),(18,1,13),(2,9,19),(23,10,8),(0,20,13),(15,21,16)]:
            d.rectangle((x,y,min(31,x+w),min(31,y+8)),fill=1)
            d.line((x,y,min(31,x+w-1),y),fill=0)
            d.line((x,y+7,min(31,x+w),y+7),fill=3)
        d.line((0,31,31,31),fill=3)
    elif kind==2: # road
        d.rectangle((0,7,31,25),fill=1)
        for x,y in [(2,11),(11,20),(24,15),(29,22)]:d.line((x,y,x+2,y),fill=0)
        d.line((0,6,31,6),fill=2);d.line((0,26,31,26),fill=2)
    elif kind==3: # cactus
        d.ellipse((7,26,25,30),fill=2)
        d.rectangle((14,4,19,27),fill=3);d.rectangle((15,3,18,26),fill=1)
        d.line((16,5,16,24),fill=0)
        d.rectangle((6,11,14,16),fill=3);d.rectangle((6,5,10,14),fill=3)
        d.rectangle((7,6,9,13),fill=1);d.rectangle((10,12,14,14),fill=1)
        d.rectangle((19,16,27,21),fill=3);d.rectangle((23,8,27,20),fill=3)
        d.rectangle((24,9,26,19),fill=1);d.rectangle((19,17,23,19),fill=1)
    elif kind==4: # small hide hut, bone supports and detailed reed roof
        d.polygon([(0,21),(5,13),(16,4),(27,13),(31,21)],fill=3)
        d.polygon([(2,18),(16,6),(29,18)],fill=2)
        for y in (11,14,17):d.line((16-(y-5),y,16+(y-5),y),fill=1)
        d.rectangle((3,20,28,30),fill=2)
        d.rectangle((12,21,20,31),fill=3);d.line((13,22,13,29),fill=1)
        for x in (2,28):d.line((x,13,x,30),fill=0,width=2)
        d.rectangle((5,22,8,25),fill=3);d.point((6,22),0)
    elif kind==5: # hold rug
        d.rectangle((0,0,31,31),fill=2);d.rectangle((2,0,29,31),fill=1)
        d.line((3,0,3,31),fill=0);d.line((28,0,28,31),fill=0)
        d.polygon([(16,7),(23,16),(16,25),(9,16)],outline=3)
        d.line((16,10,16,22),fill=0);d.line((12,16,20,16),fill=0)
    elif kind==6: # Horde banner
        d.line((7,2,7,29),fill=3,width=2);d.polygon([(8,3),(27,3),(27,21),(17,25),(8,21)],fill=3)
        d.polygon([(9,4),(26,4),(26,20),(17,23),(9,20)],fill=1)
        d.polygon([(17,7),(22,11),(20,17),(17,19),(14,17),(12,11)],fill=3)
        d.line((17,9,17,19),fill=0)
    elif kind==7: # hold sandstone tiles
        for y in (0,16):
            for x in (0,16):
                d.rectangle((x,y,x+15,y+15),fill=2);d.rectangle((x+1,y+1,x+14,y+14),fill=1)
                d.line((x+2,y+2,x+13,y+2),fill=0)
    elif kind in (9,10,11,12): # four large Den roof/wall quarters
        full=Image.new('P',(64,64),0); q=ImageDraw.Draw(full)
        q.polygon([(1,30),(8,18),(32,3),(55,18),(62,30)],fill=3)
        q.polygon([(5,28),(32,6),(58,28)],fill=1)
        for y in (13,18,23,27):q.line((32-(y-5),y,32+(y-5),y),fill=2)
        q.rectangle((7,30,56,59),fill=2);q.rectangle((10,32,53,55),fill=1)
        q.rectangle((25,35,39,63),fill=3);q.arc((24,32,40,49),180,360,fill=0,width=2)
        for x in (4,57):
            q.polygon([(x,60),(x,18),(x+2,8),(x+4,18),(x+4,60)],fill=0)
            q.line((x+4,20,x+4,57),fill=3)
        for x in (13,45):q.rectangle((x,35,x+6,40),fill=3);q.line((x,35,x+5,35),fill=0)
        n=kind-9; im=full.crop(((n%2)*32,(n//2)*32,(n%2+1)*32,(n//2+1)*32))
    elif kind==13: # scrub, passable
        for x,y in [(4,9),(19,21),(24,6)]:
            d.line((x,y+5,x,y),fill=2);d.line((x,y+4,x-3,y+1),fill=1);d.line((x,y+4,x+3,y+1),fill=1)
    elif kind==14: # water
        d.rectangle((0,0,31,31),fill=1)
        for x,y in [(1,4),(17,12),(5,22),(23,28)]:d.line((x,y,min(31,x+6),y),fill=0);d.point((x+3,y+1),2)
    elif kind==15: # cave mouth
        d.polygon([(1,31),(2,13),(10,4),(22,3),(30,14),(31,31)],fill=2)
        d.line((4,13,11,7,22,6,28,15),fill=0,width=2)
        d.ellipse((8,13,25,37),fill=3);d.rectangle((8,25,25,31),fill=3)
    return im

def terrain():
    tiles=[]; meta=[]; palette_ids=[]
    block_pals=[1,0,4,2,5,6,6,5,1,6,6,5,5,2,3,0,4]
    blocks=[]
    for kind,pal in enumerate(block_pals):
        im=terrain_block(kind);im.putpalette([v for c in BG[pal] for v in c]+[0]*756);blocks.append(im)
        im.convert('RGBA').save(OUT/'terrain'/f'block_{kind:02d}.png')
        for y in range(4):
            for x in range(4):
                pixels=tuple(im.crop((x*8,y*8,x*8+8,y*8+8)).getdata()); key=(pixels,pal)
                if key not in tiles:tiles.append(key);palette_ids.append(pal)
                i=tiles.index(key)
                meta.append(i if i<96 else 128+i-96)
    assert len(tiles)<=192,len(tiles)
    sheet=Image.new('P',(128,((len(tiles)+15)//16)*8));sheet.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
    for i,(tile,_) in enumerate(tiles):
        for j,v in enumerate(tile):sheet.putpixel(((i%16)*8+j%8,(i//16)*8+j//8),v)
    sheet.save(ROOT/'gfx/tilesets/peon.png')
    (ROOT/'data/tilesets/peon_metatiles.bin').write_bytes(bytes(meta))
    walls={1,3,4,6,9,10,11,12,14,15}
    (ROOT/'data/tilesets/peon_collision.asm').write_text(''.join('\ttilecoll '+', '.join(['WARP_PANEL' if i==16 else 'WALL' if i in walls else 'FLOOR']*4)+'\n' for i in range(17)))
    mapped=[7]*256
    for i,pal in enumerate(palette_ids):mapped[i if i<96 else 128+i-96]=pal|(8 if i>=96 else 0)
    (ROOT/'gfx/tilesets/peon_palette_map.bin').write_bytes(bytes(mapped[i]|mapped[i+1]<<4 for i in range(0,256,2)))
    def palfile(pals):
        return ''.join('\tRGB '+', '.join(f'{v>>3:02d}' for c in pal for v in c)+'\n' for pal in pals)
    (ROOT/'gfx/tilesets/peon_bg.pal').write_text(palfile(BG))
    (ROOT/'gfx/tilesets/peon_regions.pal').write_text(''.join(palfile(pals) for pals in REGION_BGS.values()))
    (ROOT/'gfx/overworld/peon_obj.pal').write_text(palfile(OBJ))
    for name,w,h in [('PeonOpening',8,6),('GrommashHold',8,6),('TheDen',12,10),('ValleyOfTrials',16,12),('DurotarRoad',12,14),('SenjinVillage',12,10),('RazorHill',12,10),('OrgrimmarGate',12,10),('BurningBladeCavern',10,10)]:
        data=[8]*(w*h)
        for y in range(h):
            for x in range(w):
                if x in (0,w-1) or y in (0,h-1):data[y*w+x]=1
                elif name=='GrommashHold':data[y*w+x]=5 if x in (3,4) else 7
                elif y==h//2 or x==w//2:data[y*w+x]=2
                elif (x*7+y*11)%13==0:data[y*w+x]=13
        if name=='TheDen':
            for x,y,i in [(2,2,9),(3,2,10),(2,3,11),(3,3,12),(8,2,4),(1,4,3),(9,7,3),(5,2,6)]:data[y*w+x]=i
            # Keep every NPC, approach and aggro ring on walkable ground.
            for x,y in [(5,4),(5,5),(5,6),(9,6),(9,7),(9,8),(8,7),(10,7),(10,8),(3,6)]:data[y*w+x]=8
        elif name=='PeonOpening':data[2*w+2]=3;data[1*w+6]=3
        elif name=='ValleyOfTrials':
            for x,y in [(3,3),(11,4),(4,8),(13,8)]:data[y*w+x]=3
            for x in range(4,10):data[2*w+x]=1
            data[1*w+12]=15
        elif name=='SenjinVillage':
            for y in range(1,h-1):data[y*w+w-2]=14
            for x,y in [(2,2),(7,2),(3,7)]:data[y*w+x]=4
        elif name=='RazorHill':
            for x,y in [(2,2),(8,2),(2,6),(8,6)]:data[y*w+x]=4
            data[2*w+5]=6
        elif name=='OrgrimmarGate':
            for x in range(2,10):data[2*w+x]=1
            for x in (4,7):data[3*w+x]=6
        elif name=='BurningBladeCavern':
            for x,y in [(3,3),(4,3),(5,3),(6,6),(7,6)]:data[y*w+x]=1
        warps={'TheDen':[(20,10)],'ValleyOfTrials':[(4,12),(28,12),(24,4)],'DurotarRoad':[(4,14),(12,24),(12,4)],
               'SenjinVillage':[(10,4)],'RazorHill':[(12,16),(12,4)],'OrgrimmarGate':[(12,16)],'BurningBladeCavern':[(10,16)]}
        for x,y in warps.get(name,[]):data[(y//2)*w+x//2]=16
        (ROOT/f'maps/{name}.blk').write_bytes(bytes(data))
        canvas=Image.new('RGB',(w*32,h*32))
        for i,value in enumerate(data):
            block=blocks[value].copy();pals=REGION_BGS.get(name,BG)
            block.putpalette([v for c in pals[block_pals[value]] for v in c]+[0]*756)
            canvas.paste(block.convert('RGB'),((i%w)*32,(i//w)*32))
        canvas.save(OUT/'maps'/(name+'.png'))
    print('Compiled',len(tiles),'native terrain tiles')

def main():
    for folder in ('terrain','maps','inventory'): (OUT/folder).mkdir(parents=True,exist_ok=True)
    characters();battles();inventory();terrain()
    manifest={'characters':NAMES,'overworld_frame_size':[16,16],'walking_frames_per_character':12,
              'battle_front_size':[56,56],'battle_back_size':[48,48],
              'alpha':'PNG exports contain only alpha 0 or 255; game uses transparent OBJ colour zero',
              'palette':'3 opaque colours per overworld sprite; four colours including background per battle sprite',
              'animation_note':'All NPCs export four directions; standard Crystal NPC renderer mirrors side direction. Peon equipment uses independent left/right frames.',
              'battle_note':'Peon has a distinct casting pose; other characters have idle/breathing cycles, not full bespoke attacks.'}
    (OUT/'asset_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':main()
