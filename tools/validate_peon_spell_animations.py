#!/usr/bin/env python3
"""Record real native spell casts and verify particle pixels/restoration.

Normal intro, menus and casts use buttons. An isolated boar encounter is
rewound with declared temporary HP/spellset/rank/totem fixtures. MOVE_ANIM,
CPU execution and animation pointers are never substituted. User saves are
never opened; each run copies the ROM into a temporary directory.
"""
from pathlib import Path
import hashlib
import io
import json
import logging
import re
import shutil
import tempfile

import numpy as np
from PIL import Image

from validate_peon_spell_effects import SpellSession, load_symbols

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'references/generated/durotar_v022/spell_animations'
SPELLS=[('rockbiter',14,'PeonRockbiter'),('earth_shock',9,'PeonEarthShock'),
        ('flame_shock',52,'PeonFlameShock'),('healing_wave',105,'PeonHealingWave'),
        ('lightning_shield',115,'PeonLightningShield'),
        ('strength_of_earth',96,'PeonStrengthOfEarth'),('purge',114,'PeonPurge'),
        ('frost_shock',58,'PeonFrostShock'),('flame_shock_ii',126,'PeonFlameShockII'),
        ('windfury',3,'PeonWindfury'),('chain_lightning',87,'PeonChainLightning'),
        ('lightning_bolt',84,'Thundershock')]
EXPECTED_GROUPS={'rockbiter':{1},'earth_shock':{2},'flame_shock':{0},
    'healing_wave':{1},'lightning_shield':{2},'strength_of_earth':{1},
    'purge':{1,3},'frost_shock':{2},'flame_shock_ii':{0},'windfury':{3},
    'chain_lightning':{2},'lightning_bolt':set()}
PALETTES={3:[[31,30,12],[16,25,31],[3,7,14]],
          4:[[31,25,7],[31,9,2],[12,2,0]],
          5:[[18,30,9],[5,17,8],[0,6,3]],
          6:[[15,25,31],[5,13,26],[0,4,12]]}


def decode_tile(data):
    image=np.zeros((8,8),dtype='uint8')
    for y in range(8):
        lo,hi=data[y*2:y*2+2]
        for x in range(8):image[y,x]=((lo>>(7-x))&1)|(((hi>>(7-x))&1)<<1)
    return image


class AnimationSession(SpellSession):
    def __init__(self,rom,sym):
        self.visual=None
        self.ui_state='none';self.main_ready=0;self.bags_entered=0;self.bags_returned=0
        self.native=(ROOT/'gfx/battle_anims/peon_nature.2bpp').read_bytes()
        self.tiles=[decode_tile(self.native[i:i+16]) for i in range(0,256,16)]
        super().__init__(rom,sym)

    def open(self):
        super().open()
        self.p.hook_register(*self.sym['GetBattleAnimByte'],self.byte,None)
        self.p.hook_register(*self.sym['RunBattleAnimScript.done'],self.script_done,None)
        self.p.hook_deregister(*self.sym['LoadTrainerOrWildMonPic'])
        self.p.hook_register(*self.sym['LoadTrainerOrWildMonPic'],self.fixture_enemy,None)
        self.p.hook_deregister(*self.sym['MoveSelectionScreen'])
        self.p.hook_register(*self.sym['MoveSelectionScreen'],self.move_menu,None)
        self.p.hook_register(*self.sym['_StaticMenuJoypad'],self.input_ready,None)
        self.p.hook_register(*self.sym['DoTurn'],lambda _:setattr(self,'ui_state','action'),None)
        self.p.hook_register(*self.sym['PeonBags'],self.bags_open,None)
        self.p.hook_register(*self.sym['BattleMenu_Pack.didnt_use_item'],self.bags_close,None)

    def move_menu(self,_):
        self.move_menus+=1;self.ui_state='moves'

    def input_ready(self,_):
        strings=int.from_bytes(bytes(self.read('wMenuData_2DMenuItemStringsAddr',2)),'little')
        if self.read('wBattleMode')[0] and strings==self.sym['BattleMenuHeader.Text'][1]:
            # Unlike BattleMenu entry, this point follows drawing/ApplyTilemap
            # and awaits player input. Never advance another action accidentally.
            self.main_ready+=1;self.ui_state='main'
            self.p.button_release('a');self.p.button_release('b')

    def bags_open(self,_):
        self.ui_state='bags';self.bags_entered+=1

    def bags_close(self,_):
        self.ui_state='restoring';self.bags_returned+=1

    def release_all(self):
        for key in ('a','b','up','down','left','right','start','select'):
            self.p.button_release(key)

    def wait_main(self,after=None,limit=24000):
        self.release_all()
        for frame in range(limit):
            if self.ui_state=='main' and (after is None or self.main_ready>after):
                self.release_all();self.tick(60)
                if self.ui_state=='main':return
            if frame%24==0:
                self.p.button('b' if self.ui_state in ('moves','bags') else 'a',delay=4)
            self.tick(1)
        raise AssertionError(('Main battle menu not ready',self.ui_state,self.main_ready,
                              self.menus,self.read('wBattleMenuCursorPosition'),hex(self.p.register_file.PC)))

    def fixture_enemy(self,_):
        # A gold-rank species tests the same spell engine plus protected badge
        # reserve; this is an explicit diagnostic, not a normal Yarrog quest.
        self.write('wTempWildMonSpecies',[67])
        self.encounter_loads+=1

    def byte(self,_):
        if not self.visual or self.read('hBattleTurn')[0]:return
        pointer=int.from_bytes(bytes(self.read('wBattleAnimAddress',2)),'little')
        if pointer==self.sym['BattleAnim_'+self.visual['label']][1]:
            self.visual['entries']+=1;self.visual['active']=True
            self.visual['actual_animation_ids'].add(int.from_bytes(bytes(self.read('wFXAnimID',2)),'little'))
            self.visual['actual_moves'].add(self.read('wCurPlayerMove')[0])

    def script_done(self,_):
        if self.visual and self.visual['active'] and self.read('wBattleAnimFlags')[0]&1:
            self.visual['terminations']+=1;self.visual['active']=False;self.visual['tail']=45

    def tick(self,frames):
        for _ in range(frames):
            self.p.tick(1,True)
            if self.visual:
                self.observe()
                if (self.visual['active'] or self.visual['tail']) and len(self.visual['frames'])<400:
                    self.visual['frames'].append(self.p.screen.image.copy())
                    if self.visual['tail'] and not self.visual['active']:self.visual['tail']-=1

    def observe(self):
        v=self.visual
        if not (v['active'] or v['tail']) or self.read('hBattleTurn')[0]:return
        dictionary=self.read('wBattleAnimTileDict',10);base=None
        for i in range(0,10,2):
            candidate=49+dictionary[i+1]
            if dictionary[i] and bytes(self.p.memory[0,0x8000+candidate*16:0x8000+candidate*16+256])==self.native:
                base=candidate;v['native_upload_verified']=True;break
        if base is None:return
        actual=np.array(self.p.screen.image.convert('RGB'))>>3
        current_oam=list(self.p.memory[0xfe00:0xfea0])
        # The framebuffer is the last completed LCD frame; DMA can already
        # contain the next one. Try both adjacent hardware OAM snapshots.
        snapshots=[current_oam]
        if v.get('previous_oam') is not None:snapshots.append(v['previous_oam'])
        v['previous_oam']=current_oam
        for oam in snapshots:
            for i in range(0,160,4):
                y,x,tile,attributes=oam[i:i+4];phase=tile-base
                if not 0<=phase<16 or not y or not x or attributes&8:continue
                v['raw_phases'].add(phase)
                x-=8;y-=16
                if not (0<=x<=152 and 0<=y<=136):continue
                palette=attributes&7
                if palette not in PALETTES:continue
                indices=self.tiles[phase]
                if attributes&32:indices=indices[:,::-1]
                if attributes&64:indices=indices[::-1,:]
                mask=indices>0
                # Lower OAM indices have hardware priority. Rocks and elemental
                # particles deliberately overlap in Earth effects; compare the
                # visible native points rather than pixels covered by a rock.
                for earlier in range(0,i,4):
                    py,px,pt,pa=oam[earlier:earlier+4]
                    px-=8;py-=16
                    if not (-7<=px<160 and -7<=py<144):continue
                    left=max(x,px);top=max(y,py);right=min(x+8,px+8);bottom=min(y+8,py+8)
                    if left>=right or top>=bottom:continue
                    previous=decode_tile(bytes(self.p.memory[(pa>>3)&1,0x8000+pt*16:0x8000+pt*16+16]))
                    if pa&32:previous=previous[:,::-1]
                    if pa&64:previous=previous[::-1,:]
                    mask[top-y:bottom-y,left-x:right-x]&=previous[top-py:bottom-py,left-px:right-px]==0
                colours=np.array([[31,31,31]]+PALETTES[palette],dtype='uint8')
                desired=colours[indices]
                seen=actual[y:y+8,x:x+8]
                if v['name']=='strength_of_earth' and phase==7 and len(v['debug'])<12:
                    v['debug'].append({'xy':[x,y],'attributes':attributes,'palette':palette,
                        'visible_points':int(mask.sum()),'expected':desired[mask].tolist(),
                        'actual':seen[mask].tolist(),'flags':self.read('wBattleAnimFlags')[0]})
                    self.p.screen.image.save(OUT/'strength_of_earth_phase7_debug.png')
                if mask.any() and np.array_equal(seen[mask],desired[mask]):
                    encoded=self.read('wOBPals1',64)[palette*8:(palette+1)*8]
                    rgb=[]
                    for p in range(1,4):
                        word=int.from_bytes(bytes(encoded[p*2:p*2+2]),'little')
                        rgb.append([word&31,(word>>5)&31,(word>>10)&31])
                    assert rgb==PALETTES[palette],('Native particle palette mismatch',palette,rgb)
                    v['phases'].add(phase);v['palettes'].add(palette)
                    v['matched_particle_frames']+=1
                    if v['peak'] is None:v['peak']=self.p.screen.image.copy()

    def capture(self,label):
        self.p.screen.image.save(OUT/f'{label}_in_rom.png')
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(OUT/f'{label}_in_rom_4x.png')

    def protected(self):
        return {'front_back_hp_tiles':bytes(self.p.memory[0,0x9000:0x9800]),
                'battle_font':bytes(self.p.memory[0,0x8800:0x9000]),
                'enemy_animation_and_rank_totem':bytes(self.p.memory[1,0x8800:0x9800])}

    def check_static(self):
        assert self.ui_state=='main',('Static capture outside main battle menu',self.ui_state)
        self.tick(45)
        image=np.array(self.p.screen.image.convert('RGB'))>>3
        front=np.array(Image.open(ROOT/'references/generated/durotar_v022/enemies/yarrog/battle_idle.png').convert('RGBA'))
        desired=front[:,:,:3]>>3;desired[front[:,:,3]==0]=[31,31,31]
        assert np.array_equal(image[0:56,96:152],desired),'Enemy idle front changed'
        binary=(ROOT/'gfx/pokemon/machop/back.2bpp').read_bytes()
        back=np.zeros((48,48),dtype='uint8');offset=0
        for x in range(0,48,8):
            for y in range(0,48,8):
                back[y:y+8,x:x+8]=decode_tile(binary[offset:offset+16]);offset+=16
        encoded=(ROOT/'gfx/pokemon/machop/normal.gbcpal').read_bytes();colours=[]
        for offset in range(0,8,2):
            word=int.from_bytes(encoded[offset:offset+2],'little')
            colours.append([word&31,(word>>5)&31,(word>>10)&31])
        colours=np.array(colours,dtype='uint8')
        assert np.array_equal(image[48:96,16:64],colours[back]),('Player native back changed',
            [[self.read('wTilemap',360)[y*20+x] for x in range(2,8)] for y in range(6,12)],
            [[self.read('wAttrmap',360)[y*20+x] for x in range(2,8)] for y in range(6,12)],
            self.read('wBGPals1',8),self.read('wBGPals1',64)[56:64])
        # The gold badge and native placed totem retain their safe bank1 IDs.
        tilemap=self.read('wTilemap',360);attrs=self.read('wAttrmap',360)
        assert [tilemap[y*20+x] for y in range(4,7) for x in (10,11)]==list(range(0x80,0x86))
        assert [attrs[y*20+x] for y in range(4,7) for x in (10,11)]==[13]*6
        assert [tilemap[y*20+8] for y in (6,7)]==[0x86,0x87]
        assert [attrs[y*20+8] for y in (6,7)]==[14,14]
        assert bytes(self.p.memory[1,0x8800:0x8860])==(ROOT/'gfx/peon_enemy_profiles/gold_dragon.2bpp').read_bytes()
        assert bytes(self.p.memory[1,0x8860:0x8880])==(ROOT/'gfx/pack/peon_earth_totem_battle.2bpp').read_bytes()
        dragon=np.array(Image.open(ROOT/'gfx/peon_enemy_profiles/gold_dragon.png'))
        palette=np.array([list(map(int,re.findall(r'\d+',line))) for line in
                          (ROOT/'gfx/peon_enemy_profiles/gold_dragon.pal').read_text().splitlines() if 'RGB' in line],dtype='uint8')
        assert np.array_equal(image[32:56,80:96],palette[dragon]),'Gold rank pixels/palette changed'
        binary=(ROOT/'gfx/pack/peon_earth_totem_battle.2bpp').read_bytes()
        totem=np.vstack([decode_tile(binary[:16]),decode_tile(binary[16:])])
        palette=np.array([[31,31,31],[22,15,7],[8,17,6],[3,2,2]],dtype='uint8')
        assert np.array_equal(image[48:64,64:72],palette[totem]),'Totem pixels/palette changed'
        return {'entire_enemy_front_rgb555':True,'player_back_rgb555':True,
                'gold_rank_and_totem_rgb555':True,'gold_rank_and_totem_restored':True}

    def bag_return(self):
        self.wait_main()
        # The cursor can stay on BAGS from a preceding round-trip. Establish
        # FIGHT explicitly, then move down exactly once to BAGS.
        self.press('up',30);self.press('left',30);self.press('down',30)
        assert self.read('wMenuCursorY')==[2] and self.read('wMenuCursorX')==[1],('Not on Bags',self.read('wMenuCursorY',2))
        entered=self.bags_entered;returned=self.bags_returned
        self.p.button('a',delay=4)
        for _ in range(240):
            self.tick(1)
            if self.bags_entered>entered:break
        assert self.bags_entered==entered+1,('Bags not opened',self.ui_state)
        self.release_all();self.tick(120)
        self.capture('bags_during_spell_checks')
        menu=self.main_ready;self.p.button('b',delay=4)
        self.wait_main(after=menu)
        assert self.bags_returned==returned+1,('Bags did not return without item',self.bags_returned,returned)
        self.press('up',30);self.press('left',30)


def main():
    logging.disable(logging.CRITICAL);OUT.mkdir(parents=True,exist_ok=True)
    sym=load_symbols();report={'rom_sha256':hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest(),
        'method':'Real button casts and native ROM video; no MOVE_ANIM or CPU substitution.',
        'ram_diagnostics':['boar encounter species67 to protect gold-rank reserve',
                           'combatants HP/maxHP240; test spellset/PP in temporary battle RAM',
                           'Healing Wave HP1; enemy positive-stat fixture for Purge',
                           'Earth Totem active fixture to protect its bank1 reserve'],
        'cases':{}}
    failures=[]
    with tempfile.TemporaryDirectory(prefix='peon-native-spells-') as temp:
        rom=Path(temp)/'spells.gbc';shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
        s=AnimationSession(rom,sym)
        try:
            s.fresh();s.talk((10,10),'up','gornek')
            s.navigate((18,13));s.press('up',30);s.press('a')
            s.wait_main()
            s.write('wPeonEarthTotemActive',[1]);s.write('wBattleMonHP',[0,240])
            s.bag_return()
            s.check_static();baseline=io.BytesIO();s.p.save_state(baseline)
            for name,move,label in SPELLS:
                s.visual=None;s.case=None;baseline.seek(0);s.p.load_state(baseline)
                s.ui_state='main';s.release_all()
                s.set_move(move);s.write('wPlayerStatLevels',[7]*7)
                # Positive stages are needed only for Purge. Raising evasion
                # for every other spell can legitimately suppress its script.
                s.write('wEnemyStatLevels',[9]*7 if move==114 else [7]*7)
                s.write('wEnemyMonMoves',[33,0,0,0]);s.write('wEnemyMonPP',[40,0,0,0])
                s.write('wPeonRockbiterCharge',[0]);s.write('wPeonLightningShieldCharges',[0])
                if move==105:s.write('wBattleMonHP',[0,1])
                protected=s.protected();menus=s.main_ready
                v={'name':name,'label':label,'entries':0,'terminations':0,'active':False,'tail':0,
                   'frames':[],'phases':set(),'raw_phases':set(),'palettes':set(),'peak':None,'actual_animation_ids':set(),
                   'actual_moves':set(),'native_upload_verified':False,'matched_particle_frames':0,'debug':[]}
                s.visual=v;s.case={'name':name,'move':move}
                # First open the actual move selector, then choose slot one.
                s.p.button('a',delay=4)
                for _ in range(240):
                    s.tick(1)
                    if s.ui_state=='moves':break
                assert s.ui_state=='moves',(name,'Move selector not opened',s.ui_state)
                s.release_all();s.tick(60)
                s.p.button('a',delay=4);s.ui_state='submitted'
                s.wait_main(after=menus)
                assert v['entries']>=1 and v['entries']==v['terminations'],(name,'unterminated script',v['entries'],v['terminations'],s.snapshot(),s.read('wCurMoveNum'),s.read('wMenuCursorY',2))
                assert v['actual_moves']=={move} and v['actual_animation_ids']=={move},(name,'wrong native script/animation',v['actual_moves'],v['actual_animation_ids'])
                expected={group*4+p for group in EXPECTED_GROUPS[name] for p in range(4)}
                if not expected<=v['phases']:
                    failures.append({'spell':name,'expected':sorted(expected),'visible':sorted(v['phases']),
                                     'raw_oam':sorted(v['raw_phases']),'diagnostic':v['debug']})
                    print(name,'MISSING_VISIBLE_PHASE',flush=True)
                if expected:assert v['native_upload_verified'] and v['matched_particle_frames']>0
                static=s.check_static()
                assert s.protected()==protected,(name,'Front/back/fonts/animation or rank/totem tiles changed')
                s.capture(name+'_after_cast')
                # A real Bags round-trip restores the ordinary battle display.
                s.bag_return();s.check_static()
                assert s.protected()==protected,(name,'Bags return damaged battle graphics')
                if v['peak'] is not None:
                    v['peak'].save(OUT/f'{name}_actual_particle_frame.png')
                    v['peak'].resize((640,576),Image.Resampling.NEAREST).save(OUT/f'{name}_actual_particle_frame_4x.png')
                frames=v['frames']
                assert frames,(name,'No native recording')
                enlarged=[im.resize((640,576),Image.Resampling.NEAREST) for im in frames]
                enlarged[0].save(OUT/f'{name}_actual_rom_cast.gif',save_all=True,append_images=enlarged[1:],duration=17,loop=0)
                report['cases'][name]={'move_id':move,'script':label,'script_entries':v['entries'],
                    'clean_terminations':v['terminations'],'native_phase_indices':sorted(v['phases']),
                    'rgb555_pixel_matched_particle_frames':v['matched_particle_frames'],
                    'visible_palette_indices':sorted(v['palettes']),'native_tile_upload_verified':v['native_upload_verified'],
                    'real_button_cast':True,'move_animation_not_substituted':True,
                    'no_graphics_corruption_after_cast_and_bags':True,**static}
                print(name,'DONE',flush=True)
            s.p.stop(save=False)
        except BaseException:
            s.capture('unexpected_animation');s.p.stop(save=False);raise
    if failures:
        (OUT/'diagnostic_animation_details.json').write_text(json.dumps(failures,indent=2)+'\n')
    assert not failures,failures
    for name in ('diagnostic_animation_details.json','strength_of_earth_phase7_debug.png',
                 'unexpected_animation_in_rom.png','unexpected_animation_in_rom_4x.png'):
        (OUT/name).unlink(missing_ok=True)
    report['all_checks_passed']=True
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'native_rom_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
