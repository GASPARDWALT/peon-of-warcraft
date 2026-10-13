#!/usr/bin/env python3
"""Compile supplied native pixels without rescaling or changing alpha.

Battle portraits use two regional palettes, respecting rank/pet palettes.
The Character page has four free portrait palettes. Originals are never edited.
"""
from pathlib import Path
from itertools import combinations
import hashlib
import json
import subprocess
import numpy as np
from PIL import Image
from build_peon_user_world_v0211 import WORLD_PALETTES, ROLE_PALETTE, index_world_rgba, encode_world_frame

ROOT = Path(__file__).resolve().parents[1]
GFX = ROOT / 'gfx/user_battle_v0211'
OUT = ROOT / 'references/generated/user_battle_v0211'
PLAYER = ROOT / 'references/generated/user_player_v0211'
SOURCE = ROOT / 'references/characters/peon_world_character_sheets_split'
REPAIR = ROOT / 'references/generated/user_npc_completion_v0211'
ROSTER = [('rattata','RATTATA','boar','Rattata'), ('sandshrew','SANDSHREW','scorpid','Sandshrew'),
 ('geodude','GEODUDE','imp','Geodude'), ('ekans','EKANS','felhunter','Ekans'),
 ('meowth','MEOWTH','tiger','Meowth'), ('totodile','TOTODILE','raptor','Totodile'),
 ('spearow','SPEAROW','harpy','Spearow'), ('kingler','KINGLER','sarkoth','Kingler'),
 ('grimer','GRIMER','enemy_warlock','Grimer'), ('machoke','MACHOKE','enemy_warlock','Machoke'),
 ('machamp','MACHAMP','orc_guard','Machamp')]
FIXED = {'shaman': [(31,31,31),(22,15,7),(8,17,6),(3,2,2)],
 'warlock': [(31,31,31),(31,20,5),(26,5,4),(4,2,3)],
 'sarkoth': [(31,31,31),(26,28,31),(13,16,20),(0,0,0)],
 'yarrog': [(31,31,31),(31,25,8),(20,11,1),(0,0,0)]}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def rgba(path):
    a = np.asarray(Image.open(path).convert('RGBA'))
    assert set(np.unique(a[:,:,3])) <= {0,255}, path
    return a

def candidates(frames):
    pixels = np.concatenate([a[:,:,:3][a[:,:,3] != 0] >> 3 for a in frames])
    colors, counts = np.unique(pixels, axis=0, return_counts=True)
    colors = colors.astype(float)
    dark = colors[np.argmin(colors.sum(1))].astype(int)
    # Exact source medoids, six material/skin shade groups. Never introduce
    # dithering, move a pixel or replace a supplied silhouette.
    keep = colors.sum(1) > max(10, dark.sum()+6)
    c, w = colors[keep], counts[keep]
    seeds = [c[np.argmax(w)]]
    while len(seeds) < min(6,len(c)):
        distance = ((c[:,None,:]-np.array(seeds)[None,:,:])**2).sum(2).min(1)
        seeds.append(c[np.argmax(distance * np.sqrt(w))])
    centers = np.array(seeds)
    for _ in range(16):
        assignment = ((c[:,None,:]-centers[None,:,:])**2).sum(2).argmin(1)
        for i in range(len(centers)):
            mask = assignment == i
            if mask.any(): centers[i] = np.average(c[mask],weights=w[mask],axis=0)
    medoids = []
    for center in centers:
        v = tuple(c[((c-center)**2).sum(1).argmin()].astype(int))
        if v not in medoids: medoids.append(v)
    return [[(31,31,31), x, y, tuple(dark)] for x,y in combinations(medoids,2)]

def tile_errors(frames, palettes):
    h,w = frames[0].shape[:2]
    result = []
    for y in range(0,h,8):
        for x in range(0,w,8):
            errors=[]
            for palette in palettes:
                error=0
                for a in frames:
                    visible=a[y:y+8,x:x+8,3] != 0
                    rgb=(a[y:y+8,x:x+8,:3].astype(int)>>3)[visible]
                    error+=((rgb[:,None,:]-np.array(palette[1:])[None,:,:])**2).sum(2).min(1).sum() if len(rgb) else 0
                errors.append(error)
            result.append(errors)
    return np.array(result)

def choose_palettes(frames, count, fixed=None):
    options=candidates(frames)
    errors=tile_errors(frames,options)
    if fixed:
        fixed_error=tile_errors(frames,[fixed])[:,0]
        first=np.minimum(errors,fixed_error[:,None]).sum(0).argmin()
        return [options[first],fixed]
    selected=[int(errors.sum(0).argmin())]
    while len(selected)<count:
        current=errors[:,selected].min(1)
        improvement=np.minimum(errors,current[:,None]).sum(0)
        for i in selected: improvement[i]=np.iinfo(np.int64).max
        selected.append(int(improvement.argmin()))
    return [options[i] for i in selected]

def material_palettes(frames, role):
    """Protect the player's green skin and class material against a purely
    numeric fit that could mistake green head shading for brown leather."""
    visible=np.concatenate([a[:,:,:3][a[:,:,3] != 0] >> 3 for a in frames])
    colors=np.unique(visible,axis=0).astype(int)
    def nearest(anchor):return tuple(map(int,colors[((colors-np.array(anchor))**2).sum(1).argmin()]))
    dark=nearest((2,2,2));green=nearest((12,17,5));light=nearest((20,26,9))
    leather=nearest((18,12,6));hide=nearest((24,17,9));steel=nearest((19,20,20))
    if role=='enemy_warlock':
        return [[(31,31,31),green,nearest((14,7,18)),dark],
                [(31,31,31),nearest((25,18,9)),nearest((8,3,12)),dark]]
    if role=='enemy_yarrog':
        return [[(31,31,31),green,nearest((14,7,18)),dark],FIXED['yarrog']]
    if role=='enemy_sarkoth':
        return [[(31,31,31),nearest((13,6,14)),nearest((25,13,4)),dark],FIXED['sarkoth']]
    if role=='enemy_felhunter':
        return [[(31,31,31),nearest((14,7,18)),nearest((8,4,11)),dark],
                [(31,31,31),nearest((13,22,5)),nearest((6,12,4)),dark]]
    if role=='enemy_raptor':
        return [[(31,31,31),light,green,dark],
                [(31,31,31),nearest((25,8,4)),nearest((25,18,9)),dark]]
    if role=='warlock': return [[(31,31,31),green,nearest((16,11,17)),dark],FIXED['warlock']]
    if role=='shaman': return [[(31,31,31),light,steel,dark],FIXED['shaman']]
    if role=='warrior': return [[(31,31,31),light,green,dark],[(31,31,31),steel,leather,dark]]
    return [[(31,31,31),light,green,dark],[(31,31,31),hide,leather,dark]]

def encode(indexed, column_major=False):
    h,w=indexed.shape
    coords=[(y,x) for y in range(0,h,8) for x in range(0,w,8)]
    if column_major: coords=[(y,x) for x in range(0,w,8) for y in range(0,h,8)]
    out=bytearray()
    for y,x in coords:
        for row in indexed[y:y+8,x:x+8]:
            low=high=0
            for n in row: low=(low<<1)|(int(n)&1);high=(high<<1)|((int(n)>>1)&1)
            out.extend((low,high))
    return bytes(out)

def emit(name, paths, slots, column=False, fixed=None, materials=None, paper=(31,31,31)):
    folder=GFX/name;folder.mkdir(parents=True,exist_ok=True)
    previews=OUT/name;previews.mkdir(parents=True,exist_ok=True)
    frames=[rgba(p) for p in paths]
    pals=material_palettes(frames,materials) if materials else choose_palettes(frames,len(slots),fixed)
    # BG pixels cannot be transparent in hardware. Source-alpha-zero pixels
    # are index0, so match the actual Character paper instead of introducing
    # an opaque white portrait rectangle. Opaque indices1..3 stay unchanged.
    pals=[[tuple(paper),*p[1:]] for p in pals]
    fitpals=[list(p) for p in pals]
    if materials=='warlock': fitpals[1][2]=fitpals[1][3] # pet red never becomes purple robe material
    choices=tile_errors(frames,fitpals).argmin(1)
    h,w=frames[0].shape[:2]
    attrs=bytes(slots[int(i)] for i in choices)
    packet=b''
    for phase,a in enumerate(frames):
        indexed=np.zeros((h,w),dtype=np.uint8);preview=np.zeros_like(a)
        for n,choice in enumerate(choices):
            y=(n//(w//8))*8;x=(n%(w//8))*8
            region=a[y:y+8,x:x+8];visible=region[:,:,3]!=0
            palette=np.array(pals[int(choice)])
            fitpalette=np.array(fitpals[int(choice)])
            rgb=region[:,:,:3].astype(int)>>3
            indices=((rgb[:,:,None,:]-fitpalette[None,None,1:,:])**2).sum(3).argmin(2)+1
            if materials=='warlock' and int(choice)==1:indices[indices==2]=3
            indices[~visible]=0
            indexed[y:y+8,x:x+8]=indices
            expanded=(palette[indices]<<3)|(palette[indices]>>2)
            preview[y:y+8,x:x+8,:3]=expanded
            preview[y:y+8,x:x+8,3]=region[:,:,3]
        assert np.array_equal(preview[:,:,3],a[:,:,3])
        packet+=encode(indexed,column)
        Image.fromarray(preview).save(previews/f'phase_{phase}_hardware_rgba.png')
        Image.fromarray(preview).resize((w*4,h*4),Image.Resampling.NEAREST).save(previews/f'phase_{phase}_4x.png')
    (folder/'frames.2bpp').write_bytes(packet)
    (folder/'attrs.bin').write_bytes(attrs)
    palraw=b''.join(int(r|(g<<5)|(b<<10)).to_bytes(2,'little') for p in pals for r,g,b in p)
    (folder/'palettes.bin').write_bytes(palraw)
    (folder/'palettes.pal').write_text(''.join('\tRGB '+', '.join(map(str,c))+'\n' for p in pals for c in p))
    return {'name':name,'sources':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in paths],
      'dimensions':[w,h],'frames':len(paths),'slots':slots,'palette_rgb555':pals,
      'pixel_geometry_and_alpha_unchanged':True,'tile_family_map_stable_across_frames':True,
      'packet_sha256':sha(folder/'frames.2bpp'),'opaque_colors':len(set(tuple(c) for p in pals for c in p[1:])),
      'transparent_bg_paper_rgb555':list(paper)}

def player_paths(role,view):
    return [PLAYER/f'sprites/{role}/combat_{view}.png']+[PLAYER/f'animations/{role}/combat_{view}_idle_{phase}.png' for phase in (1,2)]

def main():
    GFX.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    report=[];assembly=[]
    for role in ('base','shaman','warrior','warlock'):
        for view,slots,column in [('back',[0,6],True),('front',[0,6],True),('profile',[2,4,6,7],False)]:
            sourceview='front' if view=='profile' else view
            report.append(emit(f'{role}/{view}',player_paths(role,sourceview),slots,column,FIXED.get(role) if view!='profile' else None,role if view!='profile' else None,
                               paper=(31,29,23) if view=='profile' else (31,31,31)))
        packet=b''
        for phase in (0,1,2):
            for direction in ('front','back','left','right'):
                p=PLAYER/f'sprites/{role}/world_{direction}.png' if phase==0 else PLAYER/f'animations/{role}/world_{direction}_step_{phase}.png'
                packet+=encode_world_frame(index_world_rgba(Image.open(p),ROLE_PALETTE[role]))
        (GFX/role/'overworld.bin').write_bytes(packet)
        palette=WORLD_PALETTES[ROLE_PALETTE[role]]
        (GFX/role/'world_preview.pal').write_text('\tRGB '+', '.join(map(str,(v for c in palette for v in c)))+'\n')
    hero=GFX/'hero_animation';hero.mkdir(exist_ok=True)
    (hero/'anim.asm').write_text('\tframe 0, 10\n\tframe 0, 08\n\tframe 0, 10\n\tendanim\n')
    (hero/'anim_idle.asm').write_text('\tframe 0, 16\n\tendanim\n')
    (hero/'frames.asm').write_text('\tdw .frame1\n.frame1\n\tdb $00\n')
    (hero/'bitmask.asm').write_text('\tdb 0, 0, 0, 0, 0, 0, 0\n')
    for species,const,role,label in ROSTER:
        source=SOURCE/role/f'{role}_combat_front.png'
        if role=='enemy_warlock':
            # Use the repaired full-height source56 robe/staff with the actual
            # face/knife source48 transplanted as native pixels. Manifest of
            # the repair records both unchanged original parents.
            source=REPAIR/role/f'{role}_combat_front.png'
        fixed=FIXED.get('yarrog' if species=='machoke' else role)
        semantic={'grimer':'enemy_warlock','machoke':'enemy_yarrog','kingler':'enemy_sarkoth',
                  'ekans':'enemy_felhunter','totodile':'enemy_raptor'}.get(species)
        record=emit(f'enemies/{species}',[source],[1,5],True,fixed,semantic)
        report.append(record)
        folder=GFX/'enemies'/species
        # Native loader copies a second49-tile packet when initializing
        # animation. Frame0 stays canonical; no old anatomy is referenced.
        front=(folder/'frames.2bpp').read_bytes()+bytes(49*16)
        (folder/'front.2bpp').write_bytes(front)
        subprocess.run([str(ROOT/'tools/lzcompress'),str(folder/'front.2bpp'),str(folder/'front.2bpp.lz')],check=True)
        (folder/'anim.asm').write_text('\tframe 0, 10\n\tframe 0, 08\n\tframe 0, 10\n\tendanim\n')
        (folder/'anim_idle.asm').write_text('\tframe 0, 16\n\tendanim\n')
        (folder/'frames.asm').write_text('\tdw .frame1\n.frame1\n\tdb $00 ; empty changes; supplied canonical anatomy\n')
        (folder/'bitmask.asm').write_text('\tdb 0, 0, 0, 0, 0, 0, 0\n')
        assembly.append((const,label,species))
    # True rear ally supplied via source-repair route; grunt uses the actual
    # rear Peon body, not a mislabeled source face.
    imp=REPAIR/'imp/imp_combat_back.png'
    if not imp.is_file(): raise FileNotFoundError('True imp rear repair not yet supplied')
    report.append(emit('allies/imp',[imp,REPAIR/'imp/imp_combat_back_idle.png',REPAIR/'imp/imp_combat_back_cast.png'],[0,6],True))
    report.append(emit('allies/grunt',player_paths('base','back'),[0,6],True))
    # Native tables live in separate floating banks, keeping each actor under
    # 16KiB; all IDs and save records remain untouched.
    text=[]
    for role in ('base','shaman','warrior','warlock'):
        cap=role.title();text.append(f'SECTION "User {cap} Battle v0211", ROMX\n')
        for view in ('back','front','profile'):
            for suffix,file in [('Tiles','frames.2bpp'),('Pals','palettes.bin'),('Attrs','attrs.bin')]:
                text.append(f'PeonUser{cap}{view.title()}{suffix}V0211:\n\tINCBIN "gfx/user_battle_v0211/{role}/{view}/{file}"\n')
    for const,label,species in assembly:
        text.append(f'SECTION "User {species} Colors v0211", ROMX\nPeonUser{label}EnemyMetaV0211:\n\tINCBIN "gfx/user_battle_v0211/enemies/{species}/palettes.bin"\n\tINCBIN "gfx/user_battle_v0211/enemies/{species}/attrs.bin"\n')
    for role in ('imp','grunt'):
        for suffix,file in [('Tiles','frames.2bpp'),('Pals','palettes.bin'),('Attrs','attrs.bin')]:
            text.append(f'PeonUser{role.title()}Ally{suffix}V0211:\n\tINCBIN "gfx/user_battle_v0211/allies/{role}/{file}"\n')
    (GFX/'data.asm').write_text(''.join(text))
    manifest={'version':'v0.2.11','source_pngs_preserved':True,'resized':False,
       'scope':'Hardware conversion only; geometry/alpha intact, source materials fitted to regional RGB555 palettes.',
       'battle_palette_reservations':{'player':[0,6],'enemy':[1,5],'hp':[2,3],'exp':4,'rank':5,'pet_totem':6,'font':7},
       'enemy_static_canonical_note':'No invented enemy motion; native timing and spell/impact animations retained.',
       'records':report,'passed':True}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2,default=lambda x:int(x))+'\n')
    print(f'Imported {len(report)} native battle packets; original alpha/geometry intact.')

if __name__=='__main__':
    raise SystemExit('Legacy procedural hero import is retired. Use tools/import_peon_approved_players_v0212.py and tools/build_peon_art_repair_v0212.py instead. Encoder helpers remain importable.')
