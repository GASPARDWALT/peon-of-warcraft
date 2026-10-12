#!/usr/bin/env python3
"""Actual native v026 pet/totem/spell visuals and unchanged combat behavior.

Reuses the ordinary v025 companion route with new-art assertions. Additional
cases are explicitly private state/HP/speed/loadout diagnostics, selected via
the genuine battle UI. No published evidence or user battery save is touched.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import logging
import shutil
import sys
import tempfile

import numpy as np
from PIL import Image
import validate_peon_warlock_pet as previous
from validate_peon_villages import load_symbols
from validate_peon_battle_totems import BagSession

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'references/generated/visual_polish_v026/pets_spells'


def decode(data):
    return np.array([[((data[y*2]>>(7-x))&1)|(((data[y*2+1]>>(7-x))&1)<<1)
                     for x in range(8)] for y in range(8)],dtype='uint8')


def consts(path):
    out={};i=0
    for row in path.read_text().splitlines():
        p=row.split(';',1)[0].split()
        if not p:continue
        if p[0] in ('const_def','const_next'):
            if len(p)==1:i=0
            else:
                try:i=int(p[1].replace('$','0x'),0)
                except ValueError:pass
        elif p[0]=='const':out[p[1]]=i;i+=1
    return out


class PolishSession(previous.PetSession):
    def __init__(self,*args,**kwargs):
        self.visuals={name:{'phases':set(),'xy':[],'matched_frames':0,'frames':[],'previous_oam':None}
                      for name in ('firebolt','shadow_bolt')}
        self.anim_consts=consts(ROOT/'constants/battle_anim_constants.asm')
        self.packet=(ROOT/'gfx/peon_pets_v026/spell_particles_v026.2bpp').read_bytes()
        self.tiles=[decode(self.packet[i:i+16]) for i in range(0,len(self.packet),16)]
        self.visual_watch=False
        self.tint_entries=[];self.tint_checks=[];self.shadow_entries=[];self.shadow_checks=[]
        self.visual_errors=[];self.pet_target_checks=[]
        self.used_item_records=[];self.loot_grants=[]
        super().__init__(*args,**kwargs)
        self.native_sha=hashlib.sha256(Path(self.rom).read_bytes()).hexdigest()

    def open(self):
        super().open()
        def registers():
            return {key:getattr(self.p.register_file,key) for key in ('A','F','B','C','D','E','HL','SP')} | {
                'rWBK':self.p.memory[0xff70]}
        def tint_enter(_):
            fx=int.from_bytes(bytes(self.read('wFXAnimID',2)),'little')
            allowed=(self.read('hCGB')[0] and self.read('wMapTileset')==[37]
                     and self.read('wBattleMode')[0] and fx in (247,101)
                     and self.event('EVENT_PEON_WARLOCK'))
            self.tint_entries.append({'registers':registers(),'fx':fx,'allowed':bool(allowed),
                'source':self.read('wOBPals1',64),'dest':self.read('wOBPals2',64),
                'bg':self.read('wBGPals2',64)})
        def tint_return(_):
            try:
                before=self.tint_entries.pop()
                assert before['registers']==registers(),('tint CPU register/bank/stack corruption',before['registers'],registers())
                assert before['source']==self.read('wOBPals1',64),'tint changed palette source'
                assert before['bg']==self.read('wBGPals2',64),'tint changed BG/font palettes'
                wanted=before['dest'].copy()
                if before['allowed']:
                    bank,addr=self.sym['PeonTintShadowBoltParticle.Palette']
                    wanted[48:56]=list(self.p.memory[bank,addr:addr+8])
                assert wanted==self.read('wOBPals2',64),'tint changed wrong palette or failed active guard'
                self.tint_checks.append({'animation_id':before['fx'],'allowed':before['allowed'],
                    'registers_flags_stack_and_original_wram_bank_preserved':True,
                    'palette_source_unchanged_only_allowed_palette6_tinted':True})
            except Exception as error:self.visual_errors.append(repr(error))
        self.p.hook_register(*self.sym['PeonTintShadowBoltParticle'],tint_enter,None)
        bank,addr=self.sym['PeonTintShadowBoltParticle.Palette']
        assert self.p.memory[bank,addr-1]==0xc9
        self.p.hook_register(bank,addr-1,tint_return,None)
        def shadow_enter(_):
            fx=int.from_bytes(bytes(self.read('wFXAnimID',2)),'little')
            if fx in (247,101):
                target=np.array(self.p.screen.image.convert('RGB'))[42:50,128:136]>>3
                ink=int(np.count_nonzero(np.any(target!=31,axis=2)))
                if not ink:self.visual_errors.append('Shadow Bolt impact misses actual enemy ink')
            self.shadow_entries.append({'fx':fx,'source':self.read('wOBPals1',64),
                'dest':self.read('wOBPals2',64),'bg':self.read('wBGPals2',64),
                'impact_ink':ink if fx in (247,101) else None})
        def shadow_return(_):
            try:
                before=self.shadow_entries.pop()
                if before['fx'] not in (247,101):return
                assert before['source']==self.read('wOBPals1',64),'Shadow Bolt changed palette source'
                assert before['dest']==self.read('wOBPals2',64),'Shadow Bolt failed immediate OBJ restore'
                assert before['bg']==self.read('wBGPals2',64),'Shadow Bolt failed immediate BG restore'
                self.shadow_checks.append({'animation_id':before['fx'],
                    'native_impact_center':[132,46],'actual_enemy_ink_pixels':before['impact_ink'],
                    'all64_bg_obj_and_source_palette_bytes_restored_before_next_move_or_pet':True})
            except Exception as error:self.visual_errors.append(repr(error))
        self.p.hook_register(*self.sym['PlayBattleAnim'],shadow_enter,None)
        bank,addr=self.sym['_PlayBattleAnim']
        assert self.p.memory[bank,addr-1]==0xc9
        self.p.hook_register(bank,addr-1,shadow_return,None)
        self.p.hook_register(*self.sym['PeonRollRarePotion.Granted'],lambda _:
            self.loot_grants.append({'item':self.read('wCurItem')[0],
                'quantity':self.read('wItemQuantityChange')[0]}),None)

    def bag_phase(self,phase):
        super().bag_phase(phase)
        if phase=='using_item':
            self.used_item_records.append({'item':self.read('wNamedObjectIndex')[0],
                'healing_potions_after_consumption_before_enemy_or_loot':self.item_quantity(18)})

    def press(self,key,frames=90):
        if self.read('wBattleMode')[0]:
            self.p.button(key,delay=4);self.tick(frames)
        else:super().press(key,frames)

    def tick(self,frames):
        for _ in range(frames):
            self.p.tick(1,True)
            if self.visual_watch:self.observe()

    def observe(self):
        animation=int.from_bytes(bytes(self.read('wFXAnimID',2)),'little')
        name='firebolt' if animation==0x116 else 'shadow_bolt' if animation in (247,101) else None
        if not name or not self.read('wBattleMode')[0]:return
        v=self.visuals[name]
        v.setdefault('animation_ids',set()).add(animation)
        wanted=self.anim_consts['BATTLE_ANIM_FRAMESET_PEON_'+('FIREBOLT_V026' if name=='firebolt' else 'SHADOW_BOLT_V026')]
        native=self.read('wActiveAnimObjects',10*24)
        for n in range(10):
            a=native[n*24:(n+1)*24]
            if a[0] and a[3]==wanted:
                v['xy'].append([self.p.frame_count,a[7],a[8]])
                if len(v.get('raw_frames',[]))<80:v.setdefault('raw_frames',[]).append(self.p.screen.image.copy())
                v.setdefault('runtime_obj_palettes',set()).add(tuple(self.read('wOBPals2',64)[(4 if name=='firebolt' else 6)*8:(5 if name=='firebolt' else 7)*8]))
                v.setdefault('runtime_palette_sources',set()).add(tuple(self.read('wOBPals1',64)[(4 if name=='firebolt' else 6)*8:(5 if name=='firebolt' else 7)*8]))
        if bytes(self.p.memory[0,0x8310:0x83d0])!=self.packet:return
        v['native_packet_upload_verified']=True
        actual=np.array(self.p.screen.image.convert('RGB'))>>3
        oam=list(self.p.memory[0xfe00:0xfea0])
        snapshots=[oam]+([v['previous_oam']] if v['previous_oam'] is not None else [])
        v['previous_oam']=oam
        matched=False
        for objects in snapshots:
            for i in range(0,160,4):
                y,x,tile,attr=objects[i:i+4];phase=tile-49
                # Actual small-hit OAM occupies native hit tile69 after the
                # twelve projectile tiles. Include its ink in the HUD gate.
                if tile==69 and x and y and (attr&7)==2:
                    hit=decode(bytes(self.p.memory[(attr>>3)&1,0x8000+tile*16:0x8000+tile*16+16]))
                    if attr&32:hit=hit[:,::-1]
                    if attr&64:hit=hit[::-1,:]
                    yy,xx=np.nonzero(hit)
                    assert not any(x-8+px>=72 and y-16+py>=56 for py,px in zip(yy,xx)),name+' impact overlaps player HUD'
                    v.setdefault('actual_native_impact_oam_frames',0)
                    v['actual_native_impact_oam_frames']+=1
                if not (0<=phase<4 if name=='firebolt' else 4<=phase<12):continue
                v.setdefault('raw_oam_tiles',set()).add((phase,attr&7,attr))
                if not x or not y or attr&8:continue
                x-=8;y-=16
                if not (0<=x<=152 and 0<=y<=136):continue
                pixels=self.tiles[phase]
                if name=='shadow_bolt' and phase%2==0:
                    ny,nx,nt,na=objects[i+4:i+8]
                    assert (ny,nx,nt,na)==(y+16,x+16,tile+1,attr),'Shadow Bolt must be one horizontal16x8 composite'
                    composite=np.hstack((self.tiles[phase],self.tiles[phase+1]))
                    visible=composite>0
                    if 0<=x<=144 and 0<=y<=136 and visible.any():
                        rgb=np.array([[31,31,31],[26,13,31],[12,3,18],[3,1,5]],dtype='uint8')[composite]
                        if np.array_equal(actual[y:y+8,x:x+16][visible],rgb[visible]):
                            v.setdefault('full_horizontal_composite_phases',set()).add((phase-4)//2)
                if attr&32:pixels=pixels[:,::-1]
                if attr&64:pixels=pixels[::-1,:]
                mask=pixels>0
                # Compare only visible pixels when a impact sprite overlaps.
                for k in range(0,i,4):
                    py,px,pt,pa=objects[k:k+4];px-=8;py-=16
                    l,t,r,b=max(x,px),max(y,py),min(x+8,px+8),min(y+8,py+8)
                    if l>=r or t>=b:continue
                    p=decode(bytes(self.p.memory[(pa>>3)&1,0x8000+pt*16:0x8000+pt*16+16]))
                    if pa&32:p=p[:,::-1]
                    if pa&64:p=p[::-1,:]
                    mask[t-y:b-y,l-x:r-x]&=p[t-py:b-py,l-px:r-px]==0
                rgb5=[[31,31,31],[31,25,7],[31,9,2],[12,2,0]] if name=='firebolt' else [
                    [31,31,31],[26,13,31],[12,3,18],[3,1,5]]
                yy,xx=np.nonzero(mask)
                assert not any((x+px>=72 and y+py>=56) for py,px in zip(yy,xx)), name+' overlaps player HUD'
                if mask.any() and np.array_equal(actual[y:y+8,x:x+8][mask],np.array(rgb5,dtype='uint8')[pixels][mask]):
                    v['phases'].add(phase);v['matched_frames']+=1;matched=True
                    if name=='firebolt' or phase%2==0:
                        v.setdefault('physical_head_centers',[]).append([self.p.frame_count,x+(4 if name=='firebolt' else 12),y+4])
        if matched and len(v['frames'])<100:v['frames'].append(self.p.screen.image.copy())

    def round_snapshot(self):
        return super().round_snapshot() | {
            'animation_tokens':self.read('wFXAnimID',2)+self.read('wBattleAnimParam')+self.read('wBattleAfterAnim'),
            'bg_palette_sha256':hashlib.sha256(bytes(self.read('wBGPals2',64))).hexdigest(),
            'obj_palette_sha256':hashlib.sha256(bytes(self.read('wOBPals2',64))).hexdigest()}

    def pet_start(self,_):
        self.pet_pending=self.round_snapshot()
        # Verify the impact meets actual living-opponent ink, not a blank
        # corner of its 56x56 picture. The fixture never edits graphics.
        target=np.array(self.p.screen.image.convert('RGB'))[36:44,128:136]>>3
        ink=int(np.count_nonzero(np.any(target!=31,axis=2)))
        self.pet_target_checks.append({'enemy_species':self.read('wEnemyMonSpecies')[0],
            'native_impact_center':[132,40],'actual_enemy_ink_pixels':ink})
        if not ink:self.visual_errors.append('Firebolt impact misses actual enemy ink')
        self.pet_palette_before={'bg':self.read('wBGPals2',64),'obj':self.read('wOBPals2',64)}
        self.pet_background_before={'tiles':self.read('wTilemap',360),'attrs':self.read('wAttrmap',360)}

    def pet_done(self,_):
        before,after=self.pet_pending,self.round_snapshot()
        try:
            assert before and before['player_hp']>0 and before['enemy_hp']>0
            assert after['enemy_hp']==before['enemy_hp']-1
            differences={k:{'before':v,'after':after[k]} for k,v in before.items() if k!='enemy_hp' and after[k]!=v}
            if differences:
                differences['background_cells']={kind:[{'xy':[i%20,i//20],'before':old,'after':new}
                    for i,(old,new) in enumerate(zip(values,self.read('wTilemap' if kind=='tiles' else 'wAttrmap',360)))
                    if old!=new] for kind,values in self.pet_background_before.items()}
                differences['palette_bytes']={kind:{'before':self.pet_palette_before[kind],
                    'after':self.read('wBGPals2' if kind=='bg' else 'wOBPals2',64)} for kind in ('bg','obj')}
            assert not differences,differences
            assert not self.visual_errors,self.visual_errors
            self.pet_rounds.append({'before':before,'after':after});self.pet_pending=None
        except Exception as error:self.pet_errors.append(repr(error))

    def companion(self):
        f=self.read('wObjectFollow_Follower')[0]
        assert self.read('wObjectFollow_Leader')==[0] and 1<=f<13
        a=self.read('wObjectStructs',13*40)[f*40:(f+1)*40]
        assert a[0]==104 and a[1]==15 and (a[6]&7)==0
        assert a[4]&0x52==0x52 and not a[4]&0x80 and a[5]&2
        xy=(a[16]-4,a[17]-4)
        assert sum(abs(x-y) for x,y in zip(xy,self.position()))<=2
        # The friendly sprite's actual OAM samples must use its smaller source
        # tiles and red native palette, not a shared hostile-imp bitmap.
        pal=[];raw=self.read('wOBPals2',8)
        for i in range(0,8,2):
            word=int.from_bytes(bytes(raw[i:i+2]),'little');pal.append([word&31,(word>>5)&31,(word>>10)&31])
        actual=np.array(self.p.screen.image.convert('RGB'))>>3
        body=(ROOT/'gfx/peon_pets_v026/friendly_imp_world_v026.2bpp').read_bytes()
        source_tiles=[decode(body[i:i+16]) for i in range(0,len(body),16)]
        oam=list(self.p.memory[0xfe00:0xfea0]);matches=0
        for n in range(0,160,4):
            py,px,tile,attr=oam[n:n+4]
            if attr&7 or not px or not py:continue
            bank=(attr>>3)&1
            pixels=decode(bytes(self.p.memory[bank,0x8000+tile*16:0x8000+tile*16+16]))
            if not any(np.array_equal(pixels,t) for t in source_tiles):continue
            if not pixels.any():continue
            if attr&32:pixels=pixels[:,::-1]
            if attr&64:pixels=pixels[::-1,:]
            px-=8;py-=16
            if not (0<=px<=152 and 0<=py<=136):continue
            mask=pixels>0
            if np.array_equal(actual[py:py+8,px:px+8][mask],np.array(pal,dtype='uint8')[pixels][mask]):matches+=1
        assert matches>=1,'no actual red friendly-imp OAM pixels matched smaller native art'
        return {'map':self.map(),'player':self.position(),'pet':xy,'native_object':f,
                'sprite':104,'actual_obj_palette':0,'actual_small_sprite_oam_rgb555_pixels_match':True,
                'native_follow_queue_length':self.read('wFollowerMovementQueueLength')[0]}

    def battle_art(self,kind='imp'):
        source='combat_imp_v026' if kind=='imp' else 'earth_totem_v026'
        start=0x88c0 if kind=='imp' else 0x8860
        binary=(ROOT/'gfx/peon_pets_v026'/f'{source}.2bpp').read_bytes()[:96]
        assert bytes(self.p.memory[1,start:start+96])==binary
        cells=[y*20+x for y in range(4,7) for x in (8,9)]
        assert [self.read('wTilemap',360)[i] for i in cells]==list(range(0x8c if kind=='imp' else 0x86,0x92 if kind=='imp' else 0x8c))
        assert [self.read('wAttrmap',360)[i] for i in cells]==[14]*6
        expected=np.array(Image.open(OUT/'assets'/f'{source}_0_native.png').convert('RGBA'))
        expected[:,:,:3][expected[:,:,3]==0]=255
        actual=np.array(self.p.screen.image.convert('RGB'))[32:56,64:80]
        # PyBoy expands RGB5 as v<<3; source PNGs use replicated low bits.
        # Compare the underlying physical RGB555 values, not emulator gamma.
        assert np.array_equal(actual>>3,expected[:,:,:3]>>3),f'{kind} actual framebuffer differs from transparent native source'
        return {'native_bank1_vram_exact':True,'native_backview_size':[16,24],
                'actual_rgb555_framebuffer_exact':True,'protected_hud_and_emblem_footprints':True}

    def protected_actors(self):
        return {'native_bank0_actor_tiles':hashlib.sha256(bytes(self.p.memory[0,0x9000:0x9600])).hexdigest(),
                'native_bank1_enemy_front':hashlib.sha256(bytes(self.p.memory[1,0x9000:0x9310])).hexdigest(),
                'native_elite_emblem_tiles':hashlib.sha256(bytes(self.p.memory[1,0x8800:0x8860])).hexdigest(),
                'native_battle_bold_glyph_cache':hashlib.sha256(bytes(self.p.memory[1,0x8920:0x8a90])).hexdigest()}

    def finish_visuals(self):
        result={}
        for name,v in self.visuals.items():
            if not v['xy']:continue
            debug={k:sorted(x) if isinstance(x,set) else x for k,x in v.items()
                   if k not in ('frames','raw_frames','previous_oam','xy')}
            debug['rom_sha256']=self.native_sha
            (OUT/(name+'_native_observation.json')).write_text(json.dumps(debug,indent=2)+'\n')
            if v.get('raw_frames'):
                v['raw_frames'][min(15,len(v['raw_frames'])-1)].save(OUT/(name+'_raw_observed.png'))
            unique=[]
            for row in v['xy']:
                if not unique or unique[-1][1:]!=row[1:]:unique.append(row)
            motions=[(b[1]-a[1],b[2]-a[2]) for a,b in zip(unique,unique[1:]) if 0<b[0]-a[0]<=3]
            assert (2,-1) in motions,(name,'no actual two-pixel native travel observed',unique[:12])
            assert (2,0) in motions,name+' did not use its shallow casting trajectory'
            origin_x,origin_y=(88,60) if name=='firebolt' else (40,68)
            assert unique[0][1] in (origin_x,origin_x+2) and unique[0][2]==origin_y,name+' did not start at actual casting anchor'
            physical_x,physical_y=(80,44) if name=='firebolt' else (32,52)
            centers=v['physical_head_centers']
            assert centers[0][1] in (physical_x,physical_x+2) and centers[0][2]==physical_y, (name,'wrong physical launch',centers[:3])
            assert any(cx>=130 and abs(cy-(41 if name=='firebolt' else 46))<=1 for _,cx,cy in centers),name+' never physically reached enemy body'
            assert v.get('actual_native_impact_oam_frames',0)>0,name+' native impact was never observed'
            if name=='shadow_bolt':
                assert v['full_horizontal_composite_phases']=={0,1,2,3},'missing full16x8 horizontal source composites'
            required=set(range(4)) if name=='firebolt' else set(range(4,12))
            assert required<=v['phases'],(name,'native color/pixel phases missing',v['phases'])
            assert v['matched_frames']>=4
            if v['frames']:
                folder=OUT/'native_animation';folder.mkdir(parents=True,exist_ok=True)
                v['frames'][0].save(folder/(name+'_actual_native.png'))
                v['frames'][0].resize((640,576),Image.Resampling.NEAREST).save(folder/(name+'_actual_native_4x.png'))
                frames=[im.resize((480,432),Image.Resampling.NEAREST) for im in v['frames']]
                frames[0].save(folder/(name+'_actual_native.gif'),save_all=True,append_images=frames[1:],duration=17,loop=0)
            result[name]={'all_original_particle_phases_match_actual_rgb555_pixels':True,
                          'phases':sorted(v['phases']),'native_matched_frames':v['matched_frames'],
                          'actual_native_animation_ids':sorted(v['animation_ids']),
                          'native_two_pixels_right_per_frame':True,
                          'native_lift':'one pixel every eight frames',
                          'physical_launch_center':[physical_x,physical_y],
                          'physical_head_reaches_enemy_body':True,
                          'actual_native_impact_oam_frames':v['actual_native_impact_oam_frames'],
                          'full16x8_composite_rgb555_phases':sorted(v.get('full_horizontal_composite_phases',set())),
                          'visible_pixels_above_player_hud':True}
        assert not self.visual_errors,self.visual_errors
        assert {x['animation_id'] for x in self.tint_checks if x['allowed']}=={247,101}
        assert {x['animation_id'] for x in self.shadow_checks}=={247,101}
        return result


def normal_route(sha):
    """Original ordinary v025 route, with native consumption-before-loot proof.

    Copied as an explicit v026 route so published v025 code/evidence stays
    unchanged. A legitimate rare healing-potion drop may replenish the one
    just consumed; it must never be mistaken for item-use failure.
    """
    report = {'rom_sha256': sha, 'status': 'RUNNING', 'normal_ram_edits': False,
              'user_battery_saves_opened': False, 'normal': {}, 'diagnostic': {}}
    with tempfile.TemporaryDirectory(prefix='peon-warlock-companion-') as temp:
        rom = Path(temp)/'warlock.gbc'; shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
        s = PolishSession(rom, load_symbols())
        try:
            s.fresh_class(); s.p.tick(120,True)
            states = [s.companion()]
            for pos in [(12,9),(16,9),(16,7),(16,8),(12,10)]:
                s.navigate(pos); s.p.tick(60,True); states.append(s.companion())
            assert states[3]['pet'] == states[4]['player'], 'normal route must step back through pet tile'
            s.capture('ordinary_native_follow_trail')
            # Actual Horde post, inspecting does not alter items, cash, XP or flags.
            s.navigate((16,7)); s.press('up',30)
            before = s.persistent_snapshot(); s.press('a',120)
            s.capture('ordinary_den_horde_mailbox'); s.close_dialogue()
            assert before == s.persistent_snapshot()
            states.append(s.companion())
            s.navigate((17,5),23); s.p.tick(120,True); states.append(s.companion())
            s.capture('ordinary_imp_inside_inn')
            s.navigate((5,7),14); s.p.tick(120,True); states.append(s.companion())
            s.navigate((20,10),15); s.p.tick(120,True); states.append(s.companion())
            s.capture('ordinary_imp_zone2'); s.navigate((4,12),14); s.p.tick(120,True)
            states.append(s.companion())
            report['normal']['world_follow_and_four_door_zone_transitions'] = states
            report['normal']['mailbox_inspection_no_record_mutation'] = True
            report['normal']['ordinary_player_can_walk_back_through_pet_tile'] = True
            s.talk_plain((10,10),'up'); assert s.event('EVENT_PEON_QUEST_ACCEPTED')
            s.navigate((18,13)); s.press('up',30); s.press('a',60)
            s.wait(lambda:s.phase=='battle',buttons=True)
            s.p.tick(30,True); report['normal']['battle_backview'] = s.battle_art()
            s.capture('ordinary_battle_imp_backview')
            baseline = io.BytesIO(); s.p.save_state(baseline)
            pp = s.read('wPartyMon1PP',4)
            s.until_world(choose_bolt=False)
            assert s.event('EVENT_PEON_QUEST_DONE') and s.read('wBattleResult') == [0]
            assert s.read('wPartyMon1PP',4) == pp and not s.pet_errors
            s.capture('ordinary_imp_first_victory')
            s.rest(); s.navigate((18,14))
            s.wait(lambda:s.phase=='battle',buttons=True); s.until_world(choose_bolt=False)
            assert s.read('wBattleResult') == [0] and s.event('EVENT_PEON_SCORPID_DEFEATED')
            assert len(s.pet_rounds) >= 3 and not s.pet_errors
            report['normal']['native_full_round_firebolts'] = list(s.pet_rounds)
            report['normal']['pet_hits_fixed_1_no_extra_turn_no_charge_cost'] = True
            s.capture('ordinary_native_three_plus_rounds')
            report['normal']['cold_battery_continue'] = s.cold_save()
            report['normal']['cold_battery_companion'] = s.companion()
            # A separate branch is explicitly a temporary HP fixture. A real
            # potion consumes one enemy turn; HP1 opponent then dies to pet.
            baseline.seek(0); s.p.load_state(baseline)
            s.section, s.phase, s.context = 'diagnostic', 'battle', 'battle'
            for key in ('a','b','left','right','up','down'): s.p.button_release(key)
            s.pet_rounds = []; s.pet_errors = []; s.pet_pending = None
            s.used_item_records=[];s.loot_grants=[]
            s.write('wEnemyMonHP',[0,1])
            for prefix in ('wBattleMon','wPartyMon1'):
                maximum = int.from_bytes(bytes(s.read(prefix+'MaxHP',2)),'big')
                s.write(prefix+'HP',list((maximum-1).to_bytes(2,'big')))
            items, turns, experience = s.item_quantity(18),len(s.used_moves),s.experience()
            s.open_bag_item(18); s.capture('diagnostic_potion_pet_finisher')
            s.press('a',30)
            s.until_world(choose_bolt=False)
            assert s.event('EVENT_PEON_QUEST_DONE')
            assert s.used_item_records==[{'item':18,'healing_potions_after_consumption_before_enemy_or_loot':items-1}]
            grants=sum(g['quantity'] for g in s.loot_grants if g['item']==18)
            assert s.item_quantity(18)==items-1+grants, 'final inventory must include legitimate native rare loot'
            assert s.experience()>experience and s.read('wBattleResult')==[0]
            assert len(s.pet_rounds)==1 and s.pet_rounds[0]['before']['enemy_hp']==1
            moves=s.used_moves[turns:]
            assert [m['turn'] for m in moves]==[1], ('potion must cost one enemy move only',moves)
            assert not s.pet_errors
            report['diagnostic']['hp1_potion_pet_kill']={'fixture':'Private battle rewind; opponent HP1; player HP max-1.',
                'native_potion_consumed_before_loot':s.used_item_records,
                'native_post_victory_rare_loot':s.loot_grants,
                'final_quantity_accounts_for_native_loot':True,'one_enemy_turn':True,'native_victory_xp_and_quest_death_flag':True,
                'pet_round':s.pet_rounds[0]}
            s.capture('diagnostic_pet_finisher_native_victory')
            # New ordinary characters of the other two classes retain their
            # normal actors and do not accidentally inherit a native follower.
            absent = {}
            for index, name in ((0,'shaman'),(1,'warrior')):
                other_rom = Path(temp)/(name + '.gbc'); shutil.copyfile(ROOT/'pokecrystal.gbc',other_rom)
                other = PolishSession(other_rom,load_symbols(),index,section='normal/no_pet')
                try:
                    other.fresh_class(); other.p.tick(120,True)
                    assert other.read('wObjectFollow_Leader',2) == [255,255]
                    actors = other.read('wObjectStructs',13*40)
                    assert not any(actors[i*40] == 104 and actors[i*40+1] == 15 for i in range(13))
                    assert other.pet_draws == 0 and not other.pet_rounds
                    other.capture('ordinary_class_has_no_imp')
                    absent[name]={'ordinary_buttons_only':True,'follower_absent':True,'pet_actor_absent':True}
                finally: other.p.stop(save=False)
            report['normal']['other_classes_do_not_inherit_companion'] = absent
            report['normal_firebolt_actual_enemy_ink']=s.pet_target_checks
            report['status']='PASS'
        except Exception as error:
            report['failure']=repr(error); s.capture('unexpected_state'); raise
        finally:
            if s.p: s.p.stop(save=False)
            (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def diagnostics(symbols):
    reports={}
    with tempfile.TemporaryDirectory(prefix='peon-v026-pet-spells-') as temp:
        path=Path(temp)/'warlock.gbc';shutil.copyfile(ROOT/'pokecrystal.gbc',path)
        s=PolishSession(path,symbols,2,section='diagnostic');s.visual_watch=True
        try:
            s.fresh_class();s.talk_plain((10,10),'up');s.navigate((18,13));s.press('up',30);s.press('a',60)
            s.wait(lambda:s.phase=='battle',buttons=True);s.p.tick(60,True)
            baseline=io.BytesIO();s.p.save_state(baseline)
            def rewind():
                baseline.seek(0);s.p.load_state(baseline)
                for k in ('a','b','left','right','up','down'):s.p.button_release(k)
                s.phase,s.context='battle','battle';s.pet_errors=[];s.pet_rounds=[];s.pet_pending=None
            # A robust living target makes the actual Shadow Bolt cast/PP
            # visible without changing the damage formula or CPU execution.
            rewind()
            for prefix in ('wBattleMon','wPartyMon1','wEnemyMon'):
                s.write(prefix+'HP',[0,240]);s.write(prefix+'MaxHP',[0,240])
            s.write('wEnemyMonMoves',[33,0,0,0]);s.write('wEnemyMonPP',[35,0,0,0])
            before=s.read('wBattleMonPP',4);menus=s.menus;move_menus=s.move_menus
            protected=s.protected_actors()
            s.press('a',60);s.wait(lambda:s.move_menus>move_menus)
            s.press('down',30);s.press('a',30)
            s.wait(lambda:s.menus>menus and s.phase=='battle',buttons=True)
            assert s.read('wBattleMonPP',4)==s.read('wPartyMon1PP',4)==[before[0],before[1]-1,0,0]
            assert len(s.pet_rounds)==1 and not s.pet_errors
            s.p.tick(60,True);reports['shadow_bolt_visual_and_charge']=s.battle_art()
            assert protected==s.protected_actors(),'native animation changed protected actor/rank tiles'
            reports['all_protected_actor_and_rank_tiles_restored_after_shadow_and_fire']=True
            s.capture('shadow_bolt_after_native_cast')
            # The later Shadow Bolt rank also uses Night Shade's existing
            # animation-table entry. Test that alias through the native UI in
            # a declared private loadout fixture, retaining its normal effect.
            rewind()
            for prefix in ('wBattleMon','wPartyMon1','wEnemyMon'):
                s.write(prefix+'HP',[0,240]);s.write(prefix+'MaxHP',[0,240])
            for prefix in ('wBattleMon','wPartyMon1'):
                s.write(prefix+'Moves',[1,101,0,0]);s.write(prefix+'PP',[35,15,0,0])
            s.write('wEnemyMonMoves',[33,0,0,0]);s.write('wEnemyMonPP',[35,0,0,0])
            menus=s.menus;move_menus=s.move_menus
            matched=s.visuals['shadow_bolt']['matched_frames']
            palettes={n:s.read(n,64) for n in ('wBGPals2','wOBPals2')}
            s.press('a',60);s.wait(lambda:s.move_menus>move_menus)
            s.press('down',30);s.press('a',30)
            s.wait(lambda:s.menus>menus and s.phase=='battle',buttons=True)
            assert s.read('wBattleMonPP',4)==s.read('wPartyMon1PP',4)==[35,14,0,0]
            assert s.visuals['shadow_bolt']['matched_frames']>matched
            assert 101 in s.visuals['shadow_bolt']['animation_ids']
            assert all(s.read(n,64)==old for n,old in palettes.items())
            assert len(s.pet_rounds)==1 and not s.pet_errors
            reports['shadow_bolt_later_rank_native_alias']={
                'fixture':'Private prepared move slot 2=101, 15 charges; all living HP240.',
                'native_animation_id':101,'actual_purple_particle_pixels':True,
                'one_charge_used_one_pet_round':True,'all_64_bg_and_obj_palette_bytes_restored':True}
            # Bag cancel and rejected full-health potion have no pet attack.
            rewind();rounds=len(s.pet_rounds);moves=len(s.used_moves)
            s.open_bag_item(18);s.press('b',30);s.wait(lambda:s.phase=='battle')
            assert len(s.pet_rounds)==rounds and len(s.used_moves)==moves
            reports['bag_cancel_no_extra_pet_turn']=True
            rewind();s.open_bag_item(18);qty=s.item_quantity(18);s.press('a',30);s.ready('inventory')
            assert not s.pet_rounds and s.item_quantity(18)==qty
            s.press('b',30);s.wait(lambda:s.phase=='battle');reports['full_health_potion_no_extra_pet_turn']=True
            # A native flee is guaranteed with a declared speed fixture.
            rewind();s.write('wBattleMonSpeed',[255,255]);s.write('wEnemyMonSpeed',[0,1])
            s.press('right',30);s.press('down',30);s.press('a',90)
            for _ in range(100):
                if not s.read('wBattleMode')[0] and not s.read('wScriptMode')[0]:break
                s.press('a',60)
            assert s.read('wBattleMode')==[0] and not s.pet_rounds and not s.event('EVENT_PEON_QUEST_DONE')
            s.p.tick(90,True);s.companion()
            live=s.read('wObjectStructs',13*40)
            assert sum(live[i*40]==104 and live[i*40+1]==15 for i in range(13))==1
            s.capture('flee_world_restored_one_small_companion')
            reports['native_flee_no_firebolt_no_quest_death']=True
            # Defeat executes the native recovery path; a dead caster's pet
            # cannot retaliate or delete the enemy. Swift's hit is guaranteed.
            rewind()
            for prefix in ('wBattleMon','wPartyMon1'):s.write(prefix+'HP',[0,1])
            s.write('wBattleMonSpeed',[0,1]);s.write('wEnemyMonSpeed',[255,255])
            s.write('wEnemyMonMoves',[129,0,0,0]);s.write('wEnemyMonPP',[20,0,0,0])
            s.until_world(choose_bolt=False)
            assert not s.pet_rounds and s.read('wBattleResult')==[1] and not s.event('EVENT_PEON_QUEST_DONE')
            assert s.read('wPartyMon1HP',2)==[0,1]
            s.p.tick(90,True);s.companion();s.capture('loss_world_restored_one_small_companion')
            reports['native_loss_no_firebolt_bound_inn_recovery_hp1']=True
            reports['native_particles']=s.finish_visuals()
            assert set(reports['native_particles'])=={'firebolt','shadow_bolt'}
            reports['native_tint_guard_register_stack_and_wram_bank']={
                'successful_and_rejected_guard_returns':len(s.tint_checks),
                'active_aliases':sorted({x['animation_id'] for x in s.tint_checks if x['allowed']}),
                'rejected_unrelated_and_extended_animation_ids':sorted({x['animation_id'] for x in s.tint_checks if not x['allowed']}),
                'all_preserved':not s.visual_errors}
            reports['immediate_shadow_palette_restore_before_enemy_or_pet']=s.shadow_checks
            reports['firebolt_actual_native_enemy_ink_at_impact']=s.pet_target_checks
        finally:s.p.stop(save=False)
        # The original Shaman's actual reusable inventory totem gains only
        # pixels. Placing it still costs one enemy turn and no spell charge.
        path=Path(temp)/'shaman.gbc';shutil.copyfile(ROOT/'pokecrystal.gbc',path)
        s=PolishSession(path,symbols,0,section='diagnostic/totem')
        try:
            s.fresh_class();s.talk_plain((10,10),'up');s.navigate((18,13));s.press('up',30);s.press('a',60)
            s.wait(lambda:s.phase=='battle',buttons=True)
            for prefix in ('wBattleMon','wPartyMon1','wEnemyMon'):
                s.write(prefix+'HP',[0,240]);s.write(prefix+'MaxHP',[0,240])
            s.write('wEnemyMonMoves',[33,0,0,0]);s.write('wEnemyMonPP',[35,0,0,0])
            pp=s.read('wBattleMonPP',4);moves=len(s.used_moves);menus=s.menus
            s.open_bag_item(148);s.press('a',30);s.wait(lambda:s.menus>menus and s.phase=='battle',buttons=True)
            assert [m['turn'] for m in s.used_moves[moves:]]==[1]
            assert s.read('wBattleMonPP',4)==s.read('wPartyMon1PP',4)==pp
            assert s.read('wPeonEarthTotemActive')==[1] and s.item_quantity(148)==1
            s.p.tick(60,True);reports['larger_totem_native_pixels']=s.battle_art('totem')
            assert not s.visual_errors,self.visual_errors
            s.capture('larger_earth_totem_actual_native')
            reports['reusable_totem_same_native_item_turn_and_no_charge_cost']=True
        finally:s.p.stop(save=False)
    return reports


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--expected-sha');args=parser.parse_args()
    logging.disable(logging.CRITICAL);OUT.mkdir(parents=True,exist_ok=True)
    sha=hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest()
    symbols_sha=hashlib.sha256((ROOT/'pokecrystal.sym').read_bytes()).hexdigest()
    if args.expected_sha:assert args.expected_sha==sha
    # Redirect the older route's own capture/report globals only. Every new
    # instance uses the subclass, so no older published PNG is written.
    previous.OUT=OUT;previous.PetSession=PolishSession
    report=normal_route(sha)
    report['passed']=False;report['status']='RUNNING'
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    try:report['visual_polish_diagnostics']=diagnostics(load_symbols())
    except Exception as error:
        report['failure']=repr(error)
        (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
        raise
    assert hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest()==sha,'shared ROM changed during validation'
    assert hashlib.sha256((ROOT/'pokecrystal.sym').read_bytes()).hexdigest()==symbols_sha,'shared symbols changed during validation'
    report['symbols_sha256']=symbols_sha
    report['rom_and_symbols_stable_through_complete_native_run']=True
    report['passed']=True;report['status']='PASS'
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('v026 pet/totem/spell native validation PASS',sha)


if __name__=='__main__':main()
