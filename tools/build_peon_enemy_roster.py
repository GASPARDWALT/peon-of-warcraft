#!/usr/bin/env python3
"""Compile the original Durotar v0.2.2 enemy atlas to native GBC assets.

Public images are the actual reduced pixels, with binary transparency. Each
enemy has six native 16x16 NPC frames, twelve public walking frames, a 56x56
front with four real attack poses and a 48x48 back. The compiler lowers the
common pose scale until Crystal's 128-tile animation budget is satisfied.
No shared ROM is built by this script. Use --validate after the normal build.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import io
import logging
import shutil
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageOps
from scipy.ndimage import label, find_objects

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/enemies'
RGBGFX = Path('/workspace/toolchains/rgbds-1.0.4/rgbgfx')
DIRS = ('down', 'up', 'left', 'right')
POSES = ('idle', 'prepare', 'attack', 'return')
GRAY = [255,255,255,170,170,170,85,85,85,0,0,0] + [0]*756
OBJ_RED = [(255,255,255),(181,66,33),(41,16,16),(255,41,24)]
OBJ_YELLOW = [(255,255,255),(181,123,57),(74,41,16),(255,214,24)]
OBJ_GREEN = [(255,255,255),(148,90,49),(123,181,66),(8,8,8)]
# Native slots are adapters only. MACHOP 66 remains the player's shaman.
ROSTER = [
    dict(name='tiger', display='TIGER', species='meowth', number=52,
         sprite='BugCatcher', label='PeonTigerGFX', obj=OBJ_YELLOW,
         palette=[(255,255,255),(222,140,57),(82,41,24),(0,0,0)],
         stats=[38,34,26,40,20,23], types=['NORMAL','NORMAL'],
         moves=['SCRATCH','BITE'], exp=55),
    dict(name='raptor', display='RAPTOR', species='totodile', number=158,
         sprite='Twin', label='PeonRaptorGFX', obj=OBJ_RED,
         palette=[(255,255,255),(222,189,115),(107,123,49),(0,0,0)],
         stats=[40,37,28,43,20,25], types=['NORMAL','NORMAL'],
         moves=['SCRATCH','BITE'], exp=62),
    dict(name='crawler', display='CRAWLER', species='krabby', number=98,
         sprite='Lass', label='PeonCrawlerGFX', obj=OBJ_YELLOW,
         palette=[(255,255,255),(222,165,90),(132,74,33),(0,0,0)],
         stats=[39,30,40,20,18,30], types=['NORMAL','NORMAL'],
         moves=['VICEGRIP','TACKLE'], exp=52),
    dict(name='harpy', display='HARPY', species='spearow', number=21,
         sprite='Teacher', label='PeonHarpyGFX', obj=OBJ_RED,
         palette=[(255,255,255),(173,123,206),(82,41,123),(0,0,0)],
         stats=[38,32,24,45,30,28], types=['FLYING','FLYING'],
         moves=['SCRATCH','WING_ATTACK'], exp=60),
    dict(name='felstalker', display='FELSTALKER', species='ekans', number=23,
         sprite='Beauty', label='PeonFelstalkerGFX', obj=OBJ_RED,
         palette=[(255,255,255),(148,107,173),(74,41,90),(0,0,0)],
         stats=[42,35,29,34,28,30], types=['DARK','DARK'],
         moves=['BITE','SCRATCH'], exp=65),
    dict(name='cultist', display='CULTIST', species='grimer', number=88,
         sprite='SuperNerd', label='PeonCultistGFX', obj=OBJ_RED,
         palette=[(255,255,255),(132,173,66),(99,57,123),(0,0,0)],
         stats=[38,24,24,28,40,34], types=['FIRE','FIRE'],
         moves=['FLAMETHROWER','TACKLE'], exp=67),
    dict(name='yarrog', display='YARROG', species='machoke', number=67,
         sprite='Rocker', label='PeonYarrogGFX', obj=OBJ_RED,
         palette=[(255,255,255),(148,173,74),(107,66,82),(0,0,0)],
         stats=[55,40,34,30,43,37], types=['DARK','DARK'],
         moves=['FLAMETHROWER','SLASH'], exp=90),
    dict(name='sarkoth', display='SARKOTH', species='kingler', number=99,
         sprite='Janine', label='PeonSarkothGFX', obj=OBJ_RED,
         palette=[(255,255,255),(222,115,49),(115,49,24),(0,0,0)],
         stats=[53,38,42,26,24,30], types=['POISON','POISON'],
         moves=['POISON_STING','VICEGRIP'], exp=85),
]


def occupied_rows(source):
    occupied = (np.array(source.getchannel('A')) >= 180).any(1)
    spans, start = [], None
    for y, full in enumerate(occupied):
        if full and start is None:
            start = y
        elif not full and start is not None:
            spans.append((start,y)); start = None
    if start is not None: spans.append((start,source.height))
    assert len(spans)==9, spans
    return spans


def battle_cells(source):
    """Recover isolated anatomy despite small unequal generator row margins.

    A connected foreground body is retained per row/column. This avoids the
    neighbouring row's claws leaking into the quantized sprite. The committed
    original atlas remains available, unchanged, alongside the native exports.
    """
    centres = np.array([80,235,392,561,742,897,1060,1223]) * source.height/1312
    columns=[]
    for column in range(4):
        cell=source.crop((round(column*source.width/4),0,
                          round((column+1)*source.width/4),source.height))
        pixels=np.array(cell)
        labels,_=label(pixels[:,:,3]>=180)
        components=[]
        for number,span in enumerate(find_objects(labels),1):
            if span is None: continue
            count=int((labels[span]==number).sum())
            if count>3000:
                components.append((number,span,count))
        crops=[]
        for row,centre in enumerate(centres):
            candidates=[c for c in components if abs((c[1][0].start+c[1][0].stop)/2-centre)<90]
            assert candidates,(row,column)
            number,span,count=max(candidates,key=lambda c:c[2])
            selected=pixels.copy()
            selected[:,:,3]=np.where(labels==number,selected[:,:,3],0)
            cropped=Image.fromarray(selected,'RGBA').crop((span[1].start,span[0].start,
                                                         span[1].stop,span[0].stop))
            crops.append(cropped)
        columns.append(crops)
    return [[columns[c][r] for c in range(4)] for r in range(8)]


def reduce(source, palette, size, scale=None, opaque_highlights=True):
    source=source.copy()
    if scale is None: source.thumbnail((size-2,size-1),Image.Resampling.LANCZOS)
    else: source=source.resize((max(1,round(source.width*scale)),
                               max(1,round(source.height*scale))),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(size,size))
    canvas.alpha_composite(source,((size-source.width)//2,size-source.height))
    pixels=np.array(canvas)
    colours=np.array(palette if opaque_highlights else palette[1:],dtype=float)
    distances=((pixels[:,:,None,:3].astype(float)-colours)**2).sum(-1)
    indices=(distances.argmin(-1)+(0 if opaque_highlights else 1)).astype('uint8')
    alpha=np.where(pixels[:,:,3]>=180,255,0).astype('uint8')
    indices[alpha==0]=0
    native=Image.fromarray(indices,'P')
    native.putpalette([v for colour in palette for v in colour]+[0]*756)
    public=Image.fromarray(np.dstack((np.array(palette,dtype='uint8')[indices],alpha)),'RGBA')
    return public,native


def count_tiles(frames):
    def tiles(frame):
        a=np.array(frame)
        return {a[y:y+8,x:x+8].tobytes() for y in range(0,56,8) for x in range(0,56,8)}
    base=tiles(frames[0]); all_tiles=set(base)
    for frame in frames[1:]:all_tiles.update(tiles(frame))
    return 49+len(all_tiles-base)


def gif(frames, path, scale=6, duration=130):
    preview=[]
    for frame in frames:
        canvas=Image.new('RGBA',frame.size,(31,26,34,255))
        canvas.alpha_composite(frame)
        preview.append(canvas.resize((frame.width*scale,frame.height*scale),Image.Resampling.NEAREST).convert('RGB'))
    preview[0].save(path,save_all=True,append_images=preview[1:],duration=duration,loop=0)


def export_battle(entry,crops):
    folder=OUT/entry['name'];folder.mkdir(parents=True,exist_ok=True)
    poses=[crops[0],crops[2],crops[3],crops[0]]
    maximum=max(max(p.size) for p in poses)
    for limit in range(54,31,-1):
        scale=limit/maximum
        pairs=[reduce(p,entry['palette'],56,scale) for p in poses]
        native=[p[1] for p in pairs]
        tile_count=count_tiles(native)
        if tile_count<=128:break
    else:raise AssertionError(f"Cannot fit {entry['name']} in 128 tiles")
    public=[p[0] for p in pairs]
    changed=int(np.count_nonzero((np.array(public[0].getchannel('A'))>0)!=(np.array(public[2].getchannel('A'))>0)))
    assert changed>=75,(entry['name'],changed)
    sheet=Image.new('RGBA',(224,56))
    for column,(frame,name) in enumerate(zip(public,POSES)):
        frame.save(folder/f'battle_{name}.png')
        sheet.alpha_composite(frame,(column*56,0))
    sheet.save(folder/'battle_sheet.png')
    public[0].save(folder/'battle_animation.png',save_all=True,append_images=public[1:],
                   duration=[200,120,160,200],loop=0,disposal=1,blend=0)
    gif(public,folder/'battle_preview.gif')
    back,back_native=reduce(crops[1],entry['palette'],48)
    back.save(folder/'battle_back.png')
    destination=ROOT/f"gfx/pokemon/{entry['species']}"
    sheet_native=Image.new('P',(56,224));sheet_native.putpalette(native[0].getpalette())
    for row,frame in enumerate(native):sheet_native.paste(frame,(0,row*56))
    sheet_native.save(destination/'front.png');back_native.save(destination/'back.png')
    (destination/'anim.asm').write_text('\tframe 0, 04\n\tframe 1, 06\n\tframe 2, 08\n\tframe 3, 06\n\tframe 0, 04\n\tendanim\n')
    (destination/'anim_idle.asm').write_text('\tframe 0, 16\n\tframe 0, 16\n\tendanim\n')
    (destination/'shiny.pal').write_text(''.join('\tRGB '+', '.join(f'{c>>3:02d}' for c in colour)+'\n' for colour in entry['palette'][1:3]))
    return dict(front_size=[56,56],back_size=[48,48],attack_frames=4,
                attack_silhouette_changed_pixels=changed,native_animation_tiles=tile_count,
                fitted_longest_dimension=limit,palette=entry['palette']),sheet


def export_overworld(entry,source,span,row):
    folder=OUT/entry['name'];folder.mkdir(parents=True,exist_ok=True)
    pairs=[]
    for col in range(6):
        cell=source.crop((round(col*source.width/6),span[0],round((col+1)*source.width/6),span[1]))
        bounds=cell.getchannel('A').point(lambda a:255 if a>=180 else 0).getbbox()
        assert bounds,(row,col)
        public,frame=reduce(cell.crop(bounds),entry['obj'],16,opaque_highlights=False)
        if row<8:
            # The shared three-color OBJ palette reserves index3 for the
            # yellow/red reaction outline. Keep body shades at indices1/2.
            pixels=np.array(public); mask=pixels[:,:,3]>0
            distance=((pixels[:,:,None,:3].astype(float)-np.array(entry['obj'][1:3]))**2).sum(-1)
            values=(distance.argmin(-1)+1).astype('uint8');values[~mask]=0
            padded=np.pad(mask,1)
            interior=mask & padded[:-2,1:-1] & padded[2:,1:-1] & padded[1:-1,:-2] & padded[1:-1,2:]
            values[mask & ~interior]=3
            frame=Image.fromarray(values,'P');frame.putpalette([v for c in entry['obj'] for v in c]+[0]*756)
            public=Image.fromarray(np.dstack((np.array(entry['obj'],dtype='uint8')[values],pixels[:,:,3])),'RGBA')
        pairs.append((public,frame))
    native=Image.new('P',(16,96));native.putpalette(GRAY)
    for index,(_,frame) in enumerate(pairs):native.paste(frame,(0,index*16))
    native.save(ROOT/f"gfx/sprites/peon_{entry['name']}.png")
    subprocess.run([str(RGBGFX),'-o',str(ROOT/f"gfx/sprites/peon_{entry['name']}.2bpp"),
                    str(ROOT/f"gfx/sprites/peon_{entry['name']}.png")],check=True)
    exported=[];sheet=Image.new('RGBA',(16*12,16))
    for direction,name in enumerate(DIRS):
        index=direction if direction<3 else 2
        frames=[pairs[index][0],pairs[index+3][0],pairs[index][0]]
        if direction==3:frames=[ImageOps.mirror(f) for f in frames]
        for phase,frame in enumerate(frames):
            frame.save(folder/f'overworld_{name}_{phase}.png')
            sheet.alpha_composite(frame,(len(exported)*16,0));exported.append(frame)
    sheet.save(folder/'overworld_sheet.png');native_public=Image.new('RGBA',(16,96))
    for index,(public,_) in enumerate(pairs):native_public.alpha_composite(public,(0,index*16))
    native_public.save(folder/'native_overworld_sheet.png')
    exported[0].save(folder/'overworld_animation.png',save_all=True,append_images=exported[1:],
                     duration=150,loop=0,disposal=1,blend=0)
    gif(exported,folder/'overworld_preview.gif',10)
    return dict(overworld_size=[16,16],native_frames=6,export_frames=12,
                obj_palette=entry['obj'],obj_palette_number=2 if row==8 else (4 if entry['obj']==OBJ_YELLOW else 0)),sheet


def portrait_innkeeper(source,span):
    cell=source.crop((0,span[0],round(source.width/6),span[1]))
    bounds=cell.getchannel('A').point(lambda a:255 if a>=180 else 0).getbbox()
    cell=cell.crop(bounds)
    # The full walking pose has wide arms/apron. A portrait needs the face,
    # brows and tusks rather than a miniature complete torso at its bottom.
    cell=cell.crop((round(cell.width*.20),0,round(cell.width*.78),round(cell.height*.53)))
    cell=cell.resize((22,22),Image.Resampling.LANCZOS)
    palette=[(255,255,255),(173,197,107),(99,132,33),(0,0,0)]
    public,native=reduce(cell,palette,24)
    # Restore facial landmarks lost at subpixel size in the source walking
    # portrait: brows/eyes and two modest tusks, using its existing four tones.
    values=np.array(native);alpha=np.array(public)[:,:,3]
    for x,y,color in ((7,8,3),(16,8,3),(8,15,0),(15,15,0)):
        if alpha[y,x]:values[y,x]=color
    native=Image.fromarray(values,'P');native.putpalette([v for c in palette for v in c]+[0]*756)
    public=Image.fromarray(np.dstack((np.array(palette,dtype='uint8')[values],alpha)),'RGBA')
    folder=ROOT/'gfx/peon_portraits';folder.mkdir(exist_ok=True)
    native.putpalette(GRAY);native.save(folder/'innkeeper.png')
    (folder/'innkeeper.pal').write_text(''.join('\tRGB '+', '.join(f'{c>>3:02d}' for c in colour)+'\n' for colour in palette))
    subprocess.run([str(RGBGFX),'-o',str(folder/'innkeeper.2bpp'),str(folder/'innkeeper.png')],check=True)
    public.save(OUT/'innkeeper/portrait.png')
    public.resize((192,192),Image.Resampling.NEAREST).save(OUT/'innkeeper/portrait_8x.png')


def export_decor():
    """Export small native-size decor proposals; world tiles remain unchanged."""
    source=Image.open(OUT/'concept_decor.png').convert('RGBA')
    entries=[('gray_rocks',(16,16),[(214,206,189),(115,115,115),(41,33,24)]),
             ('ochre_rocks',(16,16),[(247,189,99),(173,99,49),(41,33,24)]),
             ('desert_pebbles',(16,16),[(247,189,99),(173,99,49),(41,33,24)]),
             ('cactus_fruit',(16,16),[(140,173,66),(222,74,33),(41,57,24)]),
             ('cactus_empty',(16,16),[(140,173,66),(222,206,132),(41,57,24)]),
             ('valley_doorway',(32,32),[(222,173,99),(148,82,41),(41,33,24)]),
             ('campfire',(16,16),[(247,206,82),(222,99,33),(41,33,24)]),
             ('horde_banner',(16,32),[(222,74,33),(173,115,57),(41,33,24)])]
    folder=OUT/'decor';folder.mkdir(exist_ok=True)
    report={};gallery=Image.new('RGBA',(128,64))
    for i,(name,size,colors) in enumerate(entries):
        row,col=divmod(i,4)
        cell=source.crop((col*source.width//4,row*source.height//2,
                          (col+1)*source.width//4,(row+1)*source.height//2))
        bounds=cell.getchannel('A').point(lambda a:255 if a>=180 else 0).getbbox()
        assert bounds,name
        cell=cell.crop(bounds);cell.thumbnail((size[0]-2,size[1]-2),Image.Resampling.LANCZOS)
        canvas=Image.new('RGBA',size);canvas.alpha_composite(cell,((size[0]-cell.width)//2,size[1]-cell.height))
        pixels=np.array(canvas);alpha=np.where(pixels[:,:,3]>=180,255,0).astype('uint8')
        distance=((pixels[:,:,None,:3].astype(float)-np.array(colors))**2).sum(-1)
        rgb=np.array(colors,dtype='uint8')[distance.argmin(-1)]
        image=Image.fromarray(np.dstack((rgb,alpha)),'RGBA')
        image.save(folder/f'{name}.png')
        image.resize((size[0]*8,size[1]*8),Image.Resampling.NEAREST).save(folder/f'{name}_8x.png')
        gallery.alpha_composite(image,(col*32+(32-size[0])//2,row*32+32-size[1]))
        report[name]={'native_size':list(size),'opaque_colors':colors,'alpha_values':[0,255],
                      'integrated_in_world':False}
    gallery.save(folder/'decor_sheet.png')
    gallery.resize((1024,512),Image.Resampling.NEAREST).save(folder/'decor_sheet_8x.png')
    return report


def write_native_tables(manifest):
    sprite_lines=['; Six native 16x16 frames per Durotar creature; right is mirrored.',
                  'SECTION "Peon Durotar Enemy NPC Sprites", ROMX','']
    for entry in ROSTER+[dict(name='innkeeper',label='PeonInnkeeperGFX')]:
        sprite_lines.append(f"{entry['label']}:: INCBIN \"gfx/sprites/peon_{entry['name']}.2bpp\"")
    (ROOT/'gfx/peon_enemy_roster_sprites.asm').write_text('\n'.join(sprite_lines)+'\n')
    pic_lines=['; Flexible physical picture banks. FixPicBank uses raw banks for this roster.',
               'SECTION "Peon Durotar Enemy Frontpics", ROMX','']
    for entry in ROSTER:
        label=entry['species'].title().replace('_','')
        pic_lines.append(f'{label}Frontpic: INCBIN "gfx/pokemon/{entry["species"]}/front.animated.2bpp.lz"')
    pic_lines += ['','SECTION "Peon Durotar Enemy Backpics", ROMX','']
    for entry in ROSTER:
        label=entry['species'].title().replace('_','')
        pic_lines.append(f'{label}Backpic: INCBIN "gfx/pokemon/{entry["species"]}/back.2bpp.lz"')
    (ROOT/'gfx/peon_enemy_roster_pics.asm').write_text('\n'.join(pic_lines)+'\n')
    overflow=['; Extra bank-1 animation tiles, above the original 98-tile upload.',
              'SECTION "Peon Durotar Enemy Animation Overflow", ROMX','']
    for entry in ROSTER:
        name=entry['name'].title()
        path=f'gfx/pokemon/{entry["species"]}/front.animated.2bpp'
        overflow.append(f'Peon{name}OverflowTiles:')
        if manifest['characters'][entry['name']]['native_animation_tiles']>98:
            overflow.append(f'\tINCBIN "{path}", 98 * 16')
        overflow += [f'Peon{name}OverflowTilesEnd:',
                     f'\tassert Peon{name}OverflowTilesEnd - Peon{name}OverflowTiles <= 30 * 16']
    (ROOT/'gfx/peon_enemy_roster_overflow.asm').write_text('\n'.join(overflow)+'\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--validate',action='store_true')
    args=parser.parse_args()
    if args.validate:return validate()
    OUT.mkdir(parents=True,exist_ok=True)
    battle=Image.open(OUT/'concept_battle_roster.png').convert('RGBA')
    overworld=Image.open(OUT/'concept_overworld_roster.png').convert('RGBA')
    crops=battle_cells(battle);spans=occupied_rows(overworld)
    manifest=dict(source_battle='concept_battle_roster.png',source_overworld='concept_overworld_roster.png',
                  player_adapter_untouched='MACHOP 66',alpha_values=[0,255],characters={})
    gallery=Image.new('RGBA',(224,56*8));walk_gallery=Image.new('RGBA',(192,16*9))
    for row,entry in enumerate(ROSTER):
        battle_info,battle_sheet=export_battle(entry,crops[row])
        walk_info,walk_sheet=export_overworld(entry,overworld,spans[row],row)
        gallery.alpha_composite(battle_sheet,(0,row*56));walk_gallery.alpha_composite(walk_sheet,(0,row*16))
        manifest['characters'][entry['name']]={**battle_info,**walk_info,
            'native_species':entry['species'],'species_number':entry['number'],
            'overworld_slot':entry['sprite'],'move_kit':entry['moves'],
            'stats':entry['stats'],'types':entry['types']}
    entry=dict(name='innkeeper',obj=OBJ_GREEN)
    info,sheet=export_overworld(entry,overworld,spans[8],8)
    manifest['characters']['innkeeper']=info
    walk_gallery.alpha_composite(sheet,(0,128));portrait_innkeeper(overworld,spans[8])
    manifest['decor_proposals']=export_decor()
    gallery.save(OUT/'battle_roster_sheet.png')
    gallery.resize((896,1792),Image.Resampling.NEAREST).save(OUT/'battle_roster_sheet_4x.png')
    walk_gallery.save(OUT/'overworld_roster_sheet.png')
    walk_gallery.resize((1536,1152),Image.Resampling.NEAREST).save(OUT/'overworld_roster_sheet_8x.png')
    write_native_tables(manifest)
    for p in OUT.glob('*/*.png'):
        im=Image.open(p).convert('RGBA');assert set(np.unique(np.array(im)[:,:,3]))<={0,255},p
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'README.md').write_text(
        '# Durotar v0.2.2 native enemy roster\n\n'
        'The transparent native exports below are the reduced game pixels. '
        'Large original concept atlases are retained separately as source art. '
        'MACHOP66 remains the player; eight previously unused species slots adapt '
        'these Durotar enemies without changing the save layout.\n\n'
        '![Native combat roster, 4x nearest pixel enlargement](battle_roster_sheet_4x.png)\n\n'
        '![Native walking roster, 8x nearest pixel enlargement](overworld_roster_sheet_8x.png)\n\n'
        'Each enemy folder contains twelve transparent16×16 walking PNGs, '
        'the six-frame native NPC sheet, four56×56 battle pose PNGs, '
        'a48×48 back, transparent APNG loops and GIF previews. '
        'Right-facing NPCs use Crystal reflection, and the third public walking '
        'phase returns to idle. Four battle phases are idle → prepare → attack → '
        'return; the anticipation and strike are independently redrawn anatomy. '
        'The enemy helper preserves original impact effects and poison mechanics.\n\n'
        + '\n'.join(f'**{e["display"]}** — ![{e["name"]} attack]({e["name"]}/battle_preview.gif)\n'
                     for e in ROSTER)
        + '\n**Innkeeper portrait** — ![24×24 portrait, enlarged8x](innkeeper/portrait_8x.png)\n\n'
        '**Additional decor proposals** — transparent native-size PNGs, awaiting '
        'world-tile integration; the eight enemy assets above are integrated.\n\n'
        '![Decor proposals at8x](decor/decor_sheet_8x.png)\n\n'
        'Regenerate with `python tools/build_peon_enemy_roster.py`. '
        'After building the ROM, validate with '
        '`PYTHONPATH=/workspace/toolchains/pyboy-preview python tools/build_peon_enemy_roster.py --validate`. '
        'The validator copies the ROM to a temporary directory and never opens '
        'the user save. Its eight battle diagnostics substitute only temporary '
        'encounter RAM and raise HP to observe complete poses. '
        '`compiled_validation.json` records the tested ROM hash and32pixel-exact '
        'RGB555 pose checks. Ordinary map encounters are checked separately.\n')
    print(json.dumps({name:{k:v for k,v in values.items() if k in ('native_species','native_animation_tiles','attack_silhouette_changed_pixels','obj_palette_number')}
                      for name,values in manifest['characters'].items()},indent=2))


def validate():
    """Validate compiled picture bytes and table limits without altering saves."""
    manifest=json.loads((OUT/'manifest.json').read_text())
    report={'rom_sha256':hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest(),'characters':{}}
    for entry in ROSTER:
        folder=ROOT/f'gfx/pokemon/{entry["species"]}'
        count=(folder/'front.animated.2bpp').stat().st_size//16
        assert count<=128,(entry['name'],count)
        assert count==manifest['characters'][entry['name']]['native_animation_tiles']
        assert (folder/'front.dimensions').read_bytes()==bytes([0x77])
        assert (ROOT/f'gfx/sprites/peon_{entry["name"]}.2bpp').stat().st_size==6*4*16
        palette=(folder/'normal.gbcpal').read_bytes();colours=[]
        for index in range(4):
            word=int.from_bytes(palette[index*2:index*2+2],'little')
            colours.append((word&31,(word>>5)&31,(word>>10)&31))
        data=(folder/'back.2bpp').read_bytes();back=np.zeros((48,48),dtype='uint8');offset=0
        for x in range(0,48,8):
            for y in range(0,48,8):
                for dy in range(8):
                    lo,hi=data[offset+2*dy:offset+2*dy+2]
                    for dx in range(8):back[y+dy,x+dx]=((lo>>(7-dx))&1)|(((hi>>(7-dx))&1)<<1)
                offset+=16
        assert np.array_equal(np.array(colours,dtype='uint8')[back],
                              np.array(Image.open(folder/'back.png').convert('RGB'))>>3)
        report['characters'][entry['name']]={'compiled_animation_tiles':count,
            'pose_commands':[0,1,2,3,0],'overflow_tiles':max(0,count-98),'native_size_verified':True,
            'back_pixel_exact_rgb555':True}
    symbols={}
    for row in (ROOT/'pokecrystal.sym').read_text().splitlines():
        parts=row.split()
        if len(parts)==2 and ':' in parts[0]:
            try:symbols[parts[1]]=tuple(int(v,16) for v in parts[0].split(':'))
            except ValueError:pass
    rom=(ROOT/'pokecrystal.gbc').read_bytes()
    for entry in ROSTER:
        label=entry['species'].title().replace('_','')
        folder=ROOT/f'gfx/pokemon/{entry["species"]}'
        for suffix,path in [('Frontpic',folder/'front.animated.2bpp.lz'),('Backpic',folder/'back.2bpp.lz')]:
            bank,address=symbols[label+suffix]
            offset=bank*0x4000+address-0x4000;data=path.read_bytes()
            assert rom[offset:offset+len(data)]==data,(entry['name'],suffix,'ROM gfx differs from source')
        report['characters'][entry['name']]['compiled_pics_found_in_rom']=True
    report.update(validate_emulator(symbols))
    (OUT/'compiled_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


def validate_emulator(symbols):
    """Isolated ordinary intro plus eight real enemy pose/attack diagnostics.

    A world savestate is rewound between cases. Only the scripted boar encounter
    species is substituted in temporary RAM, and HP/maxHP increased to240 to
    observe the entire native attack. This tests real engine loading, animation
    pointers, palettes and move kits without changing any ROM or user save.
    """
    from pyboy import PyBoy
    logging.disable(logging.CRITICAL)
    destination=OUT/'in_game';destination.mkdir(exist_ok=True)
    result={'diagnostic_ram_changes':['temporary boar encounter species replaced by each new enemy',
                                    'both battle HP/maxHP increased to240; original move kits preserved'],
            'emulator_attacks':{},'original_player_species_66':True}
    expected={}
    for entry in ROSTER:
        source=Image.open(ROOT/f'gfx/pokemon/{entry["species"]}/front.png').convert('RGB')
        palette=(ROOT/f'gfx/pokemon/{entry["species"]}/normal.gbcpal').read_bytes()
        colours=[]
        for index in range(4):
            word=int.from_bytes(palette[index*2:index*2+2],'little')
            colours.append((word&31,(word>>5)&31,(word>>10)&31))
        colours=np.array(colours,dtype='uint8');expected[entry['number']]=[]
        for index in range(4):
            rgb=np.array(source.crop((0,index*56,56,(index+1)*56)))>>3
            closest=((rgb[:,:,None,:].astype('int16')-colours.astype('int16'))**2).sum(-1).argmin(-1)
            expected[entry['number']].append(colours[closest])
    with tempfile.TemporaryDirectory(prefix='peon-roster-test-') as temporary:
        rom=Path(temporary)/'roster.gbc';shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
        p=PyBoy(str(rom),window='null',sound_emulated=False,log_level='ERROR');p.set_emulation_speed(0)
        state={'entry':None,'menu':False,'pose_active':False,'frames':[],'matches':set(),'commands':set(),'hook_calls':0,'ticks':0}
        def read(name,length=1):
            bank,address=symbols[name]
            if address>=0xff00:return list(p.memory[address:address+length])
            return list(p.memory[bank,address:address+length])
        def write(name,values):
            bank,address=symbols[name]
            for i,value in enumerate(values):p.memory[bank,address+i]=value
        def loader(_):
            if state['entry'] is not None:write('wTempWildMonSpecies',[state['entry']['number']])
        def menu(_):
            if state['entry'] is None or state['menu']:return
            state['menu']=True;p.button_release('a')
            write('wBattleMonHP',[0,240]);write('wBattleMonMaxHP',[0,240])
            write('wEnemyMonHP',[0,240]);write('wEnemyMonMaxHP',[0,240])
        def attack(_):
            if state['entry'] is None:return
            assert read('wEnemyMonSpecies')[0]==state['entry']['number']
            state['hook_calls']+=1;state['pose_active']=True
        trace=[]
        def diagnostic_hook(name):
            if state['entry'] is None:return
            trace.append({'hook':name,'a':p.register_file.A,'bc':(p.register_file.B<<8)|p.register_file.C,
                          'de':(p.register_file.D<<8)|p.register_file.E,'hl':p.register_file.HL,
                          'sp':p.register_file.SP,'bank':read('hROMBank')[0],
                          'cur':read('wCurPartySpecies')[0],'enemy':read('wEnemyMonSpecies')[0]})
        for name in ('LoadEnemyMon','InitEnemyWildmon','GetEnemyMonFrontpic','GetFrontpicPointer',
                     'FixPicBank','GetAnimatedEnemyFrontpic','PeonLoadEnemyPoseOverflow',
                     'InitBattleDisplay','PeonEncounterStartMessage','PeonFixEnemyPicBankFromC.native'):
            p.hook_register(*symbols[name],diagnostic_hook,name)
        p.hook_register(*symbols['LoadTrainerOrWildMonPic'],loader,None)
        p.hook_register(*symbols['BattleMenu'],menu,None)
        p.hook_register(*symbols['PeonAnimateEnemyAttack.animate'],attack,None)
        def tick(frames):
            for _ in range((frames+1)//2):
                p.tick(2,True)
                if state['pose_active']:
                    entry=state['entry'];number=entry['number']
                    if len(state['frames'])<110:state['frames'].append(p.screen.image.resize((640,576),Image.Resampling.NEAREST))
                    if read('wPokeAnimSpecies')[0]==number:
                        command=read('wPokeAnimCommand')[0]
                        state['commands'].add(command)
                        if command<4:
                            actual=np.array(p.screen.image.convert('RGB').crop((96,0,152,56)))>>3
                            if np.array_equal(actual,expected[number][command]):
                                state['matches'].add(command)
                                if command==2:p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(destination/f'{entry["name"]}_actual_strike.png')
                    state['ticks']+=1
        def press(key,frames=90):p.button(key,delay=8);tick(frames)
        def pos():return tuple(read('wXCoord')+read('wYCoord'))
        def walk(key,steps):
            before=pos();p.button_press(key)
            for _ in range(steps*40+30):
                p.tick(1,True)
                if sum(abs(a-b) for a,b in zip(before,pos()))==steps:break
            p.button_release(key);tick(25)
            assert sum(abs(a-b) for a,b in zip(before,pos()))==steps,(key,before,pos())
        def until(predicate,limit=180):
            for _ in range(limit):
                if predicate():return
                press('a')
            p.screen.image.save(destination/'unexpected_state.png')
            (destination/'unexpected_trace.json').write_text(json.dumps(trace[-80:],indent=2)+'\n')
            raise AssertionError({'pos':pos(),'battle':read('wBattleMode'),'script':read('wScriptMode'),
                                  'species':read('wEnemyMonSpecies'),'pc':hex(p.register_file.PC),
                                  'state':{k:v for k,v in state.items() if k!='frames'}})
        tick(240);press('start');press('down');press('a')
        until(lambda:read('wMapGroup',2)==[26,14] and read('wScriptMode')[0]==0)
        print('intro position',pos(),flush=True)
        assert read('wPartySpecies')[0]==66,'Player adapter must remain MACHOP 66'
        walk('up',2);press('a');until(lambda:read('wScriptMode')[0]==0)
        walk('down',3);walk('right',8);press('up',20)
        print('boar approach',pos(),flush=True)
        baseline=io.BytesIO();p.save_state(baseline)
        for index,entry in enumerate(ROSTER):
            if index:
                baseline.seek(0);p.load_state(baseline)
            state.update(entry=entry,menu=False,pose_active=False,frames=[],matches=set(),commands=set(),hook_calls=0,ticks=0)
            press('a');until(lambda:state['menu'])
            until(lambda:state['matches']=={0,1,2,3})
            tick(160)
            assert state['hook_calls']>0
            assert read('wEnemyMonSpecies')[0]==entry['number']
            frames=state['frames'];frames[0].save(destination/f'{entry["name"]}_actual_attack.gif',save_all=True,
                                                   append_images=frames[1:],duration=33,loop=0)
            result['emulator_attacks'][entry['name']]={'species':entry['number'],'actual_pose_commands':sorted(state['commands']),
                'pixel_exact_rgb555_pose_matches':sorted(state['matches']),'attack_hook_calls':state['hook_calls'],
                'native_move_ids':read('wEnemyMonMoves',4)}
            print(entry['name'],'native poses',sorted(state['matches']),flush=True)
        p.stop(save=False)
    return result


if __name__=='__main__':main()
