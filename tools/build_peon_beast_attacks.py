#!/usr/bin/env python3
"""Compile real boar/scorpid attack silhouettes into Crystal's native format.

The atlas contains two rows: boar and scorpid; columns idle/front, back,
anticipation, strike. Public PNGs retain binary alpha and the exact four-color
GBC pixels. Engine inputs are indexed PNGs because Crystal treats BG index
zero as its white battle background, rather than OBJ transparency.
"""
from pathlib import Path
import json
import shutil
import sys
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "references/generated/durotar_v021/combat_assets"
SOURCE = OUT / "concept_beast_attacks.png"
PALETTES = {
    "boar": [(255,255,255),(206,156,90),(115,66,33),(0,0,0)],
    "scorpid": [(255,255,255),(222,90,41),(123,41,24),(0,0,0)],
}
SPECIES = {"boar":"rattata", "scorpid":"sandshrew"}

def crop_atlas(atlas, row, column):
    w,h = atlas.size
    image = atlas.crop((round(column*w/4),round(row*h/2),
                        round((column+1)*w/4),round((row+1)*h/2)))
    alpha = image.getchannel("A").point(lambda a: 255 if a>=180 else 0)
    bounds = alpha.getbbox()
    assert bounds, (row,column)
    return image.crop(bounds)

def quantize(source, colours, size, scale=None):
    source = source.copy()
    if scale is None:
        source.thumbnail((size-2,size-2),Image.Resampling.LANCZOS)
    else:
        source = source.resize((max(1,round(source.width*scale)),
                                max(1,round(source.height*scale))),
                               Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA",(size,size))
    canvas.alpha_composite(source,((size-source.width)//2,size-1-source.height))
    pixels = np.array(canvas)
    alpha = np.where(pixels[:,:,3]>=180,255,0).astype("uint8")
    distance = ((pixels[:,:,:3,None].transpose(0,1,3,2).astype(float)
                 -np.array(colours,dtype=float))**2).sum(axis=-1)
    indices = distance.argmin(axis=-1).astype("uint8")
    indices[alpha==0] = 0
    public = Image.fromarray(np.dstack((np.array(colours,dtype="uint8")[indices],alpha)),"RGBA")
    native = Image.fromarray(indices,"P")
    native.putpalette([v for colour in colours for v in colour]+[0]*756)
    return public,native

def export(name, frames, back, native_frames, native_back):
    folder = OUT/name
    folder.mkdir(parents=True,exist_ok=True)
    labels = ["idle","prepare","attack","return"]
    sheet = Image.new("RGBA",(56*4,56))
    for index,(frame,label) in enumerate(zip(frames,labels)):
        frame.save(folder/f"{label}.png")
        frame.resize((336,336),Image.Resampling.NEAREST).save(folder/f"{label}_6x.png")
        sheet.alpha_composite(frame,(56*index,0))
    sheet.save(folder/"sheet.png")
    back.save(folder/"back.png")
    frames[0].save(folder/"animation.png",save_all=True,append_images=frames[1:],
                   duration=[200,120,160,220],loop=0,disposal=1,blend=0)
    preview=[]
    for frame in frames:
        canvas=Image.new("RGBA",(56,56),(35,29,31,255))
        canvas.alpha_composite(frame)
        preview.append(canvas.resize((336,336),Image.Resampling.NEAREST).convert("RGB"))
    preview[0].save(folder/"preview.gif",save_all=True,append_images=preview[1:],
                    duration=[200,120,160,220],loop=0)
    species = SPECIES[name]
    native_sheet = Image.new("P",(56,224))
    native_sheet.putpalette(native_frames[0].getpalette())
    for index,frame in enumerate(native_frames):
        native_sheet.paste(frame,(0,index*56))
    native_sheet.save(ROOT/f"gfx/pokemon/{species}/front.png")
    native_back.save(ROOT/f"gfx/pokemon/{species}/back.png")
    (ROOT/f"gfx/pokemon/{species}/anim.asm").write_text(
        "\tframe 0, 04\n\tframe 1, 06\n\tframe 2, 08\n"
        "\tframe 3, 06\n\tframe 0, 04\n\tendanim\n")
    # Idle previews do not trigger an attack silhouette.
    (ROOT/f"gfx/pokemon/{species}/anim_idle.asm").write_text(
        "\tframe 0, 16\n\tframe 0, 16\n\tendanim\n")
    (ROOT/f"gfx/pokemon/{species}/shiny.pal").write_text("".join(
        "\tRGB "+", ".join(f"{c>>3:02d}" for c in colour)+"\n"
        for colour in PALETTES[name][1:3]))
    return sheet

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if len(sys.argv)>1:
        shutil.copyfile(sys.argv[1],SOURCE)
    atlas = Image.open(SOURCE).convert("RGBA")
    manifest = {"source":str(SOURCE.relative_to(ROOT)),"characters":{}}
    gallery = Image.new("RGBA",(224,112))
    for row,(name,colours) in enumerate(PALETTES.items()):
        crops = [crop_atlas(atlas,row,col) for col in range(4)]
        front_crops = [crops[0],crops[2],crops[3]]
        scale = min(54/max(p.width for p in front_crops),
                    54/max(p.height for p in front_crops))
        public_native = [quantize(p,colours,56,scale) for p in front_crops]
        frames = [public_native[0][0],public_native[1][0],public_native[2][0],public_native[0][0].copy()]
        native_frames = [public_native[0][1],public_native[1][1],public_native[2][1],public_native[0][1].copy()]
        base_tiles=set()
        for y in range(0,56,8):
            for x in range(0,56,8):
                base_tiles.add(np.array(native_frames[0])[y:y+8,x:x+8].tobytes())
        all_tiles=set(base_tiles)
        for frame in native_frames[1:]:
            values=np.array(frame)
            for y in range(0,56,8):
                for x in range(0,56,8):all_tiles.add(values[y:y+8,x:x+8].tobytes())
        # The first49tiles retain their positions, including duplicates;
        # only additional poses are deduplicated by pokemon_animation_graphics.
        native_tile_count=49+len(all_tiles-base_tiles)
        assert native_tile_count<=128,(name,native_tile_count)
        back,native_back = quantize(crops[1],colours,48)
        masks=[np.array(f.getchannel("A"))>0 for f in frames]
        silhouette_change = int(np.count_nonzero(masks[0]!=masks[2]))
        assert silhouette_change>=100, f"{name}: attack must change the silhouette"
        for frame in [*frames,back]:
            pixels=np.array(frame)
            assert set(np.unique(pixels[:,:,3])) <= {0,255}
            assert len(set(map(tuple,pixels[pixels[:,:,3]>0,:3])))<=4
        sheet=export(name,frames,back,native_frames,native_back)
        gallery.alpha_composite(sheet,(0,56*row))
        manifest["characters"][name]={"adapter":SPECIES[name],"front_size":[56,56],
            "back_size":[48,48],"frames":4,"opaque_palette":colours,
            "attack_silhouette_changed_pixels":silhouette_change,
            "native_animation_tiles":native_tile_count,
            "animation_tiles_above_crystal_98_tile_upload":max(0,native_tile_count-98),
            "alpha_values":[0,255],"actual_attack_hook":"PeonAnimateEnemyAttack"}
    gallery.save(OUT/"beast_attack_sheet.png")
    gallery.resize((1344,672),Image.Resampling.NEAREST).save(OUT/"beast_attack_sheet_6x.png")
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(manifest["characters"],indent=2))


def validate_attacks():
    """Run isolated real-battle poses and a separate poison diagnostic.

    Requires a built ROM with PeonAnimateEnemyAttack integrated and PyBoy.
    The normal encounter flow uses buttons; only the poison endurance test
    adjusts HP and the enemy move in temporary emulator RAM, documented in JSON.
    """
    from pathlib import Path
    import tempfile, shutil, hashlib, json, logging, re, io
    from collections import deque
    from pyboy import PyBoy
    logging.disable(logging.CRITICAL)
    OUT=ROOT/'references/generated/durotar_v022/combat_assets/in_game'
    OUT.mkdir(parents=True,exist_ok=True)
    symbols={}
    for row in (ROOT/'pokecrystal.sym').read_text().splitlines():
        col=row.split()
        if len(col)==2 and ':' in col[0]:
            try:symbols[col[1]]=tuple(int(x,16) for x in col[0].split(':'))
            except ValueError:pass
    with tempfile.TemporaryDirectory(prefix='peon-beast-test-') as temporary:
        rom=Path(temporary)/'combat.gbc';shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
        p=PyBoy(str(rom),window='null',sound_emulated=False,log_level='ERROR');p.set_emulation_speed(0)
        results={'rom_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'enemy_attacks':{},'diagnostic_ram_changes':[]}
        legacy_intro_hooks=['GetTrainerBackpic','GetTrainerPic','CopyBackpic','BattleIntroSlidingPics',
                            'SendOutMonText','SendOutPlayerMon','InitEnemyTrainer',
                            'StartTrainerBattle_LoadPokeBallGraphics',
                            'GiveANickname_YesNo','InitNickname']
        native_intro_hooks=['PeonStartPlayerCombat','PeonStartEncounterTransition',
                            'PeonEncounterStartMessage','PeonAskName']
        results['intro_hooks']={name:0 for name in legacy_intro_hooks+native_intro_hooks}
        for name in results['intro_hooks']:
            p.hook_register(*symbols[name],lambda key:results['intro_hooks'].__setitem__(key,results['intro_hooks'][key]+1),name)
        results['legacy_ball_effect_calls']=0
        results['legacy_ball_sfx_calls']=0
        def battle_effect_hook(_):
            effect=(p.register_file.D<<8)|p.register_file.E
            if effect in (0x100,0x101,0x102):results['legacy_ball_effect_calls']+=1
        def sfx_hook(_):
            sound=(p.register_file.D<<8)|p.register_file.E
            if sound in (0x28,0x29):results['legacy_ball_sfx_calls']+=1
        p.hook_register(*symbols['Call_PlayBattleAnim'],battle_effect_hook,None)
        p.hook_register(*symbols['PlaySFX'],sfx_hook,None)
        encounter={'active':False,'frames':[],'menu_seen':False,'tail':0}
        results['native_encounter_legacy_cry_calls']=0
        def cry_hook(_):
            if encounter['active']:results['native_encounter_legacy_cry_calls']+=1
        p.hook_register(*symbols['PlayStereoCry'],cry_hook,None)
        p.hook_register(*symbols['PlayStereoCry2'],cry_hook,None)
        def battle_menu_hook(_):
            if encounter['active'] and not encounter['menu_seen']:
                # Stop the ordinary A press at the first menu so the proof
                # capture shows both combatants before the move overlay.
                p.button_release('a')
                encounter['menu_seen']=True;encounter['tail']=20
        p.hook_register(*symbols['BattleMenu'],battle_menu_hook,None)
        capture={'remaining':0,'species':0,'frames':[], 'commands':set()}
        expected_poses={}
        test_species={**SPECIES,'imp':'geodude'}
        pose_labels=['idle','prepare','attack','return']
        for name,species in test_species.items():
            source=Image.open(ROOT/f'gfx/pokemon/{species}/front.png')
            palette=(ROOT/f'gfx/pokemon/{species}/normal.gbcpal').read_bytes()
            colours=[]
            for index in range(4):
                word=int.from_bytes(palette[index*2:index*2+2],'little')
                colours.append((word&31,(word>>5)&31,(word>>10)&31))
            palette555=np.array(colours,dtype='uint8')
            expected_poses[name]=[]
            for index in range(4):
                # rgbgfx sorts/remaps colors; PNG palette indices need not
                # equal final GBC indices (the imp's yellow/red order differs).
                rgb555=np.array(source.crop((0,index*56,56,(index+1)*56)).convert('RGB'))>>3
                closest=((rgb555[:,:,None,:].astype('int16')-palette555.astype('int16'))**2).sum(axis=-1).argmin(axis=-1)
                expected_poses[name].append(palette555[closest])
        results['native_attack_pixel_matches']={name:False for name in SPECIES}
        results['native_pose_pixel_matches']={name:{label:False for label in pose_labels}
                                              for name in test_species}
        def read(name,length=1):
            bank,address=symbols[name]
            if address>=0xff00:return list(p.memory[address:address+length])
            return list(p.memory[bank,address:address+length])
        def write(name,values):
            bank,address=symbols[name]
            for i,value in enumerate(values):p.memory[bank,address+i]=value
        def pose_hook(_):
            species=read('wEnemyMonSpecies')[0]
            key={19:'boar',27:'scorpid',74:'imp'}.get(species,str(species))
            results['enemy_attacks'].setdefault(key,{'hook_calls':0,'frames':[]})['hook_calls']+=1
            if key not in results.get('recorded',[]) and not capture['remaining']:
                capture.update(remaining=90,species=species,frames=[],commands=set())
        p.hook_register(*symbols['PeonAnimateEnemyAttack.animate'],pose_hook,None)
        def tick(frames):
            for _ in range((frames+1)//2):
                p.tick(2,True)
                if encounter['active']:
                    encounter['frames'].append(p.screen.image.resize((640,576),resample=0))
                    if encounter['menu_seen']:
                        encounter['tail']-=1
                        if not encounter['tail']:
                            encounter['active']=False
                            encounter['frames'][0].save(OUT/'peon_native_encounter_from_world.gif',
                                save_all=True,append_images=encounter['frames'][1:],duration=33,loop=0)
                            p.screen.image.resize((640,576),resample=0).save(OUT/'peon_native_first_battle_menu.png')
                if capture['remaining']:
                    capture['frames'].append(p.screen.image.resize((640,576),resample=0))
                    if read('wPokeAnimSpecies')[0]==capture['species']:
                        command=read('wPokeAnimCommand')[0]
                        capture['commands'].add(command)
                        key={19:'boar',27:'scorpid',74:'imp'}[capture['species']]
                        if command<4:
                            actual=np.array(p.screen.image.convert('RGB').crop((96,0,152,56)))>>3
                            if np.array_equal(actual,expected_poses[key][command]):
                                results['native_pose_pixel_matches'][key][pose_labels[command]]=True
                        if command==2:
                            p.screen.image.resize((640,576),resample=0).save(OUT/f'{key}_actual_strike.png')
                            if key in SPECIES and results['native_pose_pixel_matches'][key]['attack']:
                                results['native_attack_pixel_matches'][key]=True
                    capture['remaining']-=1
                    if not capture['remaining']:
                        key={19:'boar',27:'scorpid',74:'imp'}[capture['species']]
                        capture['frames'][0].save(OUT/f'{key}_actual_attack.gif',save_all=True,
                            append_images=capture['frames'][1:],duration=33,loop=0)
                        results['enemy_attacks'][key]['frames']=sorted(capture['commands'])
                        results.setdefault('recorded',[]).append(key)
        def press(key,frames=90):p.button(key,delay=8);tick(frames)
        def pos():return tuple(read('wXCoord')+read('wYCoord'))
        def walk(key,steps):
            before=pos();p.button_press(key)
            for _ in range(steps*40+30):
                p.tick(1,True)
                if sum(abs(a-b) for a,b in zip(before,pos()))==steps:break
            p.button_release(key);tick(25)
            assert sum(abs(a-b) for a,b in zip(before,pos()))==steps,(key,steps,before,pos())
        def until(predicate):
            for _ in range(120):
                if predicate():return
                press('a')
            p.screen.image.save(OUT/'unexpected_state.png')
            raise AssertionError({name:read(name) for name in ['wMapNumber','wBattleMode','wScriptMode','wMenuCursorY']}|{'pos':pos(),'pc':hex(p.register_file.PC)})
        def navigate(target,avoid_aggro=False):
            name,w,h={14:('TheDen',12,10),15:('ValleyOfTrials',16,12),20:('BurningBladeCavern',10,10)}[read('wMapNumber')[0]]
            start=pos();grid=(ROOT/f'maps/{name}.blk').read_bytes()
            rows=[]
            for line in (ROOT/'data/tilesets/peon_collision.asm').read_text().splitlines():
                if 'tilecoll' in line:rows.append(line.split('tilecoll',1)[1].split(';')[0].replace(' ','').split(','))
            actors=set();warps=set()
            for line in (ROOT/f'maps/{name}.asm').read_text().splitlines():
                match=re.match(r'\s*object_event\s+(\d+),\s*(\d+),',line)
                if match:actors.add(tuple(int(x) for x in match.groups()))
                match=re.match(r'\s*warp_event\s+(\d+),\s*(\d+),',line)
                if match:warps.add(tuple(int(x) for x in match.groups()))
            queue=deque([(start,[])]);seen={start}
            while queue:
                (x,y),path=queue.popleft()
                if (x,y)==target:
                    for index,key in enumerate(path):
                        if target in warps and index==len(path)-1:
                            p.button(key,delay=30);tick(150)
                        else:walk(key,1)
                    return
                for key,dx,dy in [('left',-1,0),('right',1,0),('up',0,-1),('down',0,1)]:
                    xx,yy=x+dx,y+dy;point=(xx,yy)
                    if not(0<=xx<w*2 and 0<=yy<h*2) or point in actors or point in seen or (point in warps and point!=target):continue
                    if name=='TheDen' and avoid_aggro and abs(xx-19)+abs(yy-15)<=2:continue
                    if rows[grid[(yy//2)*w+xx//2]][(yy%2)*2+xx%2]=='WALL':continue
                    seen.add(point);queue.append((point,path+[key]))
            raise AssertionError(('no path',start,target))
        tick(240);press('start');press('down');press('a')
        until(lambda:read('wMapGroup',2)==[26,14] and read('wScriptMode')[0]==0)
        print('intro',pos(),flush=True)
        walk('up',2);press('a');until(lambda:read('wScriptMode')[0]==0)
        walk('down',2);walk('right',7)
        encounter['active']=True
        press('a');until(lambda:read('wBattleMode')[0]!=0)
        boar_baseline=io.BytesIO();p.save_state(boar_baseline)
        until(lambda:read('wBattleMode')[0]==0 and read('wScriptMode')[0]==0)
        assert results['enemy_attacks']['boar']['hook_calls']>0,results
        assert {0,1,2,3}.issubset(results['enemy_attacks']['boar']['frames']),results
        print('boar',results['enemy_attacks']['boar'],flush=True)
        navigate((10,10),True);press('up',20);press('a');until(lambda:read('wScriptMode')[0]==0)
        navigate((17,14),True);walk('down',1);tick(600);until(lambda:read('wBattleMode')[0]!=0)
        # Diagnostic only: preserve both actors long enough to observe the ORIGINAL
        # random Poison Sting proc and subsequent original residual poison damage.
        until(lambda:read('wMenuCursorY')[0]==1 and read('wEnemyMonHP',2)!=[0,0])
        write('wBattleMonHP',[0,240]);write('wBattleMonMaxHP',[0,240])
        write('wEnemyMonHP',[0,240]);write('wEnemyMonMaxHP',[0,240])
        write('wEnemyMonMoves',[40,0,0,0]);write('wEnemyMonPP',[35,0,0,0])
        results['diagnostic_ram_changes']=['both combatants HP/maxHP=240','enemy only move=Poison Sting (40), PP=35']
        poison={'hp_before_residual':None,'hp_after_residual':None,'applied':False}
        def applied(_):
            if read('hBattleTurn')[0]!=0:poison['applied']=True
        def residual_before(_):
            if read('hBattleTurn')[0]==0 and read('wBattleMonStatus')[0]&8:
                poison['hp_before_residual']=int.from_bytes(bytes(read('wBattleMonHP',2)),'big')
        def residual_after(_):
            if poison['hp_before_residual'] is not None and read('hBattleTurn')[0]==0:
                poison['hp_after_residual']=int.from_bytes(bytes(read('wBattleMonHP',2)),'big')
        p.hook_register(*symbols['PoisonOpponent'],applied,None)
        p.hook_register(*symbols['ResidualDamage.did_toxic'],residual_before,None)
        p.hook_register(*symbols['ResidualDamage.did_psn_brn'],residual_after,None)
        for _ in range(220):
            press('a',120)
            if poison['hp_after_residual'] is not None:break
            assert read('wBattleMode')[0]!=0,'Battle ended before diagnostic poison proc'
        tick(150)
        assert poison['applied'],poison
        assert read('wBattleMonStatus')[0]&8,read('wBattleMonStatus')
        assert poison['hp_before_residual']-poison['hp_after_residual']==30,poison
        assert results['enemy_attacks']['scorpid']['hook_calls']>0,results
        assert {0,1,2,3}.issubset(results['enemy_attacks']['scorpid']['frames']),results
        p.hook_deregister(*symbols['PoisonOpponent'])
        p.hook_deregister(*symbols['ResidualDamage.did_toxic'])
        p.hook_deregister(*symbols['ResidualDamage.did_psn_brn'])
        results['original_poison']=poison
        results['poison_damage_1_8_max_hp']=True
        p.screen.image.save(OUT/'original_poison_retained.png')
        write('wBattleMonStatus',[0]);write('wEnemyMonHP',[0,1])
        results['diagnostic_ram_changes'] += ['clear diagnostic poison before returning to normal flow','enemy HP=1 to end diagnostic fight']
        until(lambda:read('wBattleMode')[0]==0 and read('wScriptMode')[0]==0)
        navigate((10,10));press('up',20);press('a');until(lambda:read('wScriptMode')[0]==0)
        navigate((20,10));assert read('wMapNumber')[0]==15
        navigate((24,4));assert read('wMapNumber')[0]==20
        navigate((8,12));walk('up',1);tick(600)
        until(lambda:read('wBattleMode')[0]!=0)
        until(lambda:read('wBattleMode')[0]==0 and read('wScriptMode')[0]==0)
        assert results['enemy_attacks']['imp']['hook_calls']>0,results
        assert {0,1,2,3}.issubset(results['enemy_attacks']['imp']['frames']),results
        assert all(results['native_attack_pixel_matches'].values()),results
        assert all(all(poses.values()) for poses in results['native_pose_pixel_matches'].values()),results
        assert encounter['menu_seen'] and not encounter['active'],encounter
        assert all(results['intro_hooks'][name]==0 for name in legacy_intro_hooks),results['intro_hooks']
        assert results['legacy_ball_effect_calls']==0 and results['legacy_ball_sfx_calls']==0,results
        assert results['native_encounter_legacy_cry_calls']==0,results
        assert results['intro_hooks']['PeonAskName']==1,results['intro_hooks']
        results['native_encounter_no_trainer_or_creature_naming']=True
        # Exercise guards in separate rewound diagnostic fights. Each temporary
        # condition is injected only while entering the helper and restored on
        # its exit, before Crystal executes the ordinary move effect.
        guard={'active':False,'complete':False,'frame_calls':0}
        def guard_entry(_):
            if read('hBattleTurn')[0]==0 or guard['complete']:return
            guard['active']=True
            guard['old']=read(guard['field'])[0]
            write(guard['field'],[guard['old']|guard['value']])
        def guard_frame(_):
            if guard['active']:guard['frame_calls']+=1
        def guard_exit(_):
            if not guard['active']:return
            write(guard['field'],[guard['old']])
            guard['active']=False;guard['complete']=True
        p.hook_register(*symbols['PeonAnimateEnemyAttack'],guard_entry,None)
        p.hook_register(*symbols['PeonAnimateEnemyAttack.done'],guard_exit,None)
        p.hook_register(*symbols['PokeAnim_GetFrame'],guard_frame,None)
        results['guard_diagnostics']={}
        for name,field,value in [('substitute','wEnemySubStatus4',16),
                                 ('minimized','wEnemyMinimized',1),
                                 ('battle_scene_off','wOptions',128)]:
            boar_baseline.seek(0);p.load_state(boar_baseline)
            guard.update(active=False,complete=False,frame_calls=0,field=field,value=value)
            until(lambda:guard['complete'])
            assert guard['frame_calls']==0,(name,guard)
            assert read(field)[0]==guard['old'],(name,guard)
            results['guard_diagnostics'][name]={'native_frame_calls':0,'injected_field_restored':True}
        results['diagnostic_ram_changes'] += ['isolated helper guard tests temporarily set substitute/minimized/scenesOFF; fields restored on helper exit']
        p.stop(save=False)
        (OUT/'validation.json').write_text(json.dumps(results,indent=2)+'\n')
        print(json.dumps(results,indent=2),flush=True)

if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="--validate":
        validate_attacks()
    else:
        main()
