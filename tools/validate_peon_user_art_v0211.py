#!/usr/bin/env python3
"""Observe the actual v0.2.11 user-art routes with ordinary game controls.

An isolated ROM copy per class uses the ordinary intro, movement, menus, doors,
actual battles and a 32 KiB battery cold restart. Hooks inspect native uploads,
VRAM, OAM and RGB555 framebuffer pixels; callback failures explicitly fail QA.
"""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, logging, re, shutil, tempfile
from datetime import datetime, timezone
import numpy as np
from PIL import Image
import validate_peon_class_routes as routes
from validate_peon_warlock_pet import PetSession
from validate_peon_villages import MAPS, load_symbols, warp_tiles, sprite_constants
from validate_peon_exit_title import ExitSession, symbols as symbols_from_file
from validate_durotar_v022_quests import triggers
from validate_peon_deep_ui import text_encoding

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'references/generated/user_art_runtime_v0211'
OUT=BASE
routes.OUT=OUT
CLASSES=('shaman','warrior','warlock')
DIRECTIONS=('down','up','left','right')
MAPS.update({12:('PeonOpening',8,6),13:('GrommashHold',8,6)})


def digest(data):return hashlib.sha256(data).hexdigest()


def decode(data,width,height,column=False):
    out=np.zeros((height,width),dtype='uint8');cols,rows=width//8,height//8
    for n in range(cols*rows):
        tx,ty=divmod(n,rows) if column else (n%cols,n//cols)
        for y in range(8):
            lo,hi=data[n*16+y*2:n*16+y*2+2]
            for x in range(8):out[ty*8+y,tx*8+x]=(lo>>(7-x)&1)|(hi>>(7-x)&1)<<1
    return out


class GraphicsSession(PetSession):
    def __init__(self,rom,symbols,index):
        self.slug=CLASSES[index]
        folder=ROOT/'gfx/user_battle_v0211'/self.slug
        self.art={'overworld.bin':(folder/'overworld.bin').read_bytes(),
          'back_frames.bin':(folder/'back/frames.2bpp').read_bytes(),
          'portrait_frames.bin':(folder/'profile/frames.2bpp').read_bytes()}
        assert len({self.art['back_frames.bin'][i*576:(i+1)*576] for i in range(3)})==3,('Final class needs3 distinct compiled rear poses',self.slug)
        self.back_attrs=(folder/'back/attrs.bin').read_bytes()
        self.profile_attrs=(folder/'profile/attrs.bin').read_bytes()
        self.object_palette=1 if self.slug=='warlock' else 2
        self.upload_pending=[];self.uploads=[];self.hook_errors=[];self.world_watch=False
        self.world_frames={};self.world_facings=set();self.previous_facing=None;self.previous_world_oam=None
        self.cast=None;self.casts=[];self.last_world_vram=None
        self.full_player_region_checks=[]
        self.preview_checks=[]
        self.oam_report={'frames':0,'maximum_visible_entries':0,'maximum_entries_on_one_scanline':0,
                         'physical_scanline_counts_include_X_hidden_objects':True}
        self.native_counts={'save':0,'exit':0,'title':0,'continue':0,'new_game':0}
        self.presentation='boot'
        self.profile_inputs=0
        self.hold_import=None
        super().__init__(rom,symbols,index,section='normal')
        # Reserved v029 saved bits are numeric aliases, deliberately outside
        # the const stream used by older route observers.
        for match in re.finditer(r'^\s*DEF\s+(EVENT_\w+)\s+EQU\s+(\$[0-9a-fA-F]+|\d+)\b',
                                 (ROOT/'constants/event_flags.asm').read_text(),re.M):
            self.flags[match[1]]=int(match[2][1:],16) if match[2].startswith('$') else int(match[2])

    def write(self,*args,**kwargs):raise AssertionError('This graphics route permits no emulator RAM writes.')

    def collision_at(self,x,y):
        name,w,h=MAPS[self.map()]
        if not(0<=x<w*2 and 0<=y<h*2):return 'WALL'
        # v0211 adds native metatile IDs per map while preserving the original
        # geometry. The earlier route helper's one67-row table is obsolete.
        rows=[]
        path=ROOT/'gfx/tilesets/peon_user_environment_v0211'/(name+'_coll.asm')
        for row in path.read_text().splitlines():
            if 'peon_user_tilecoll' in row:
                rows.append(row.split('peon_user_tilecoll',1)[1].split(';',1)[0].replace(' ','').split(','))
        bank,address=self.sym['wOverworldMapBlocks']
        block=self.p.memory[bank,address+(y//2+3)*(w+6)+x//2+3]
        if not block:return 'WALL'
        assert block<len(rows),('map-local collision ID',name,block,len(rows))
        return rows[block][y%2*2+x%2]

    def open(self):
        super().open()
        for label,kind in [('PeonLoadClassPlayerBackPose','back'),('PeonLoadClassProfileFrame','profile'),
                           ('PeonLoadClassWorldPreview','preview')]:
            self.p.hook_register(*self.sym[label],lambda kind:self.safe(self.upload_enter,kind),kind)
        # Shared native Get2bpp adapter restores VBK immediately before RET.
        # v0211 preview saves BC before its direct helper call; back has one
        # direct helper call, and profile remains a tail call.
        # by observed stack depth; there is no inserted call or CPU substitution.
        for helper in ('PeonClassGet2bppBank0', 'PeonClassGetBackPoseBank0'):
            bank,address=self.sym[helper]
            offset=bank*0x4000+address-0x4000
            code=self.rom.read_bytes()[offset:offset+64]
            end=code.index(bytes((0xf1,0xe0,0x4f,0xf1,0xe0)))+6
            self.p.hook_register(bank,address+end,lambda _:self.safe(self.upload_done,None),None)
        self.p.hook_register(*self.sym['PeonAnimatePlayerAttack'],lambda _:self.safe(self.attack_start,None),None)
        self.p.hook_register(*self.sym['PeonCharacterTeamInputV029.input'],
                            lambda _:setattr(self,'profile_inputs',self.profile_inputs+1),None)
        bank,address=self.sym['PeonQuestMarker'];address-=1
        offset=bank*0x4000+address-0x4000
        assert self.rom.read_bytes()[offset]==0xc9,'Eye-opening end is not a native RET'
        self.p.hook_register(bank,address,lambda _:self.safe(self.observe_hold,None),None)
        for label,name in [('_SaveGameData','save'),('StartMenu_Exit','exit'),
                           ('PeonTitleScreen','title'),('Continue','continue'),('NewGame','new_game')]:
            self.p.hook_register(*self.sym[label],lambda name:self.native_count(name),name)
        for label,phase in [('PeonTitleScreen.wait','title'),('PeonCharacterSelect.input','select'),
                            ('StartMenu.loop','start_menu'),('HandleMapTimeAndJoypad','world')]:
            self.p.hook_register(*self.sym[label],lambda phase:setattr(self,'presentation',phase),phase)

    def native_count(self,name):
        # The native release guard aliases EXIT's entry and may re-enter.
        if name!='exit' or self.presentation!='exit_release':self.native_counts[name]+=1
        if name=='exit':self.presentation='exit_release'

    def observe_hold(self,_):
        assert self.map()==13
        self.hold_import=self.environment_import()
        self.capture('intro_GrommashHold_native_room')

    def safe(self,callback,value):
        try:callback(value)
        except Exception as error:self.hook_errors.append({'hook':callback.__name__,'error':repr(error)})

    def protected_back(self):
        return {'enemy_front':digest(bytes(self.p.memory[0,0x9000:0x9310])),
                'bank0_font':digest(bytes(self.p.memory[0,0x8800:0x9000])),
                'after_player':digest(bytes(self.p.memory[0,0x9550:0x9800])),
                'bank1_emblem_totem_pet':digest(bytes(self.p.memory[1,0x8800:0x8920])),
                'bank1_bold_font':digest(bytes(self.p.memory[1,0x8920:0x8a90])),
                'tilemap':digest(bytes(self.read('wTilemap',360))),
                'attrs_outside_player':digest(bytes(v for i,v in enumerate(self.read('wAttrmap',360))
                    if not (6<=i//20<12 and 2<=i%20<8)))}

    def upload_enter(self,kind):
        frame=self.p.register_file.C
        assert 0<=frame<=2,(kind,frame)
        if kind=='preview':
            expected=(ROOT/'gfx/user_battle_v0211'/CLASSES[frame]/'overworld.bin').read_bytes()[:64]
            target=0x9600
        else:
            size=576 if kind=='back' else 784
            expected=self.art['back_frames.bin' if kind=='back' else 'portrait_frames.bin'][frame*size:(frame+1)*size]
            target=0x9310 if kind=='back' else 0x9400
        self.upload_pending.append({'kind':kind,'frame':frame,'target':target,'expected':expected,
          'sp':self.p.register_file.SP,'vbk':self.p.memory[0xff4f], 'bgmode':self.read('hBGMapMode')[0],
          'events':digest(bytes(self.read('wEventFlags',256))),
          'font1_range':(0x8920,0x8a90) if self.read('wBattleMode')[0] else (0x9690,0x9800),
          'font1':digest(bytes(self.p.memory[1,0x8920:0x8a90])) if self.read('wBattleMode')[0]
                    else digest(bytes(self.p.memory[1,0x9690:0x9800])),
          'protected':self.protected_back() if kind=='back' and self.read('wBattleMode')[0] else None,
          'cursor_y':self.read('wMenuCursorY')[0],'cursor_x':self.read('wMenuCursorX')[0]})

    def upload_done(self,_):
        sp=self.p.register_file.SP
        for pending in reversed(self.upload_pending):
            wanted=pending['sp']-({'preview':4,'back':2,'profile':0}[pending['kind']])
            if sp!=wanted:continue
            actual=bytes(self.p.memory[0,pending['target']:pending['target']+len(pending['expected'])])
            assert actual==pending['expected'],(pending['kind'],self.slug,pending['frame'],'native VRAM differs',digest(actual),digest(pending['expected']))
            assert self.p.memory[0xff4f]==pending['vbk'],'class upload did not restore VBK'
            assert self.read('hBGMapMode')[0]==pending['bgmode'],'class upload did not restore native BG map mode'
            assert digest(bytes(self.read('wEventFlags',256)))==pending['events'],'graphics upload changed saved flags'
            start,end=pending['font1_range']
            assert digest(bytes(self.p.memory[1,start:end]))==pending['font1'],'class upload damaged bold font bank1'
            if pending['protected'] is not None:
                assert self.protected_back()==pending['protected'],'rear pose upload damaged enemy/font/emblem/totem/pet/HUD'
            row={k:v for k,v in pending.items() if k not in ('expected','protected','events','font1','sp','vbk','bgmode')}
            row.update({'bytes':len(actual),'native_sha256':digest(actual),'vram_bank':0,
                        'saved_flags_unchanged':True,'font_bank1_unchanged':True,
                        'protected_battle_regions_unchanged':pending['protected'] is not None})
            self.uploads.append(row);self.upload_pending.remove(pending);return

    def attack_start(self,_):
        if self.cast is not None and self.read('hBattleTurn')==[0]:
            self.cast['actual_moves'].add(self.read('wCurPlayerMove')[0])
            self.cast['started']=True

    def advance(self,frames):
        for _ in range(frames):
            self.p.tick(1,True)
            if self.world_watch:self.safe(self.observe_world,None)
            if self.world_watch:self.safe(self.observe_oam,None)
            if self.cast is not None:self.safe(self.observe_cast,None)
        assert not self.hook_errors,self.hook_errors[-4:]

    tick=advance

    def press(self,key,frames=90):
        if not self.read('wBattleMode')[0] and self.phase in ('battle','battle_drawing','using_item'):
            self.phase,self.context='overworld',None
        self.p.button(key,delay=4);self.advance(frames)
        if self.read('wBattleMode')[0]:return
        for _ in range(100):
            if self.phase in ('overworld','main','slots'):return
            if self.phase in ('confirm','message') and self.wait_ready:return
            self.advance(10)
        raise AssertionError(('trainer screen never ready',self.phase))

    def walk(self,key):
        before=self.position();oldmap=self.map()
        for _ in range(8):
            self.p.button(key,delay=4);self.advance(40)
            if self.position()!=before:break
        assert self.map()==oldmap,(key,'unexpected warp',oldmap,self.map())
        assert sum(abs(a-b) for a,b in zip(before,self.position()))==1,(key,before,self.position())

    def capture(self,name):
        folder=OUT/self.slug;folder.mkdir(parents=True,exist_ok=True)
        self.p.screen.image.save(folder/(name+'.png'))
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(folder/(name+'_4x.png'))
        print(self.slug,name,self.map(),self.position(),self.phase,flush=True)
        if name=='master_class_description':self.preview_pixels(self.class_index,10,12,name)
        if name=='cold_saved_character_preview_before_continue':self.preview_pixels(self.class_index,4,7,name)

    def saved_name_pixels(self):
        chars=text_encoding();wanted=[chars[c] for c in 'Péon ABCDE']
        assert self.read('wMenuScrollPosition')==[1],'saved identity did not pass native checksum metadata read'
        assert self.read('wPlayerName',11)==wanted+[0x50],'saved display lost/doubled the Peon prefix'
        tiles,attrs=self.read('wTilemap',360),self.read('wAttrmap',360)
        codes=self.read('wPeonBoldGlyphCodes',self.read('wPeonBoldGlyphCount')[0])
        bold=(ROOT/'gfx/font/peon_bold_v026.1bpp').read_bytes();actual=np.array(self.p.screen.image.convert('RGB'))>>3
        decoded=[]
        for n,code in enumerate(wanted):
            cell=4*20+2+n;tile,attr=tiles[cell],attrs[cell]
            encoded=codes[tile-0x69] if attr&8 and 0x69<=tile<0x69+len(codes) else tile
            decoded.append(encoded);assert encoded==code,('cold saved-name native cell',n,encoded,code)
            if code>=0x80:
                source=bytes(v for v in bold[(code-0x80)*8:(code-0x80+1)*8] for _ in range(2))
                assert attr&8 and bytes(self.p.memory[1,0x9000+tile*16:0x9000+tile*16+16])==source
            else:source=bytes(self.p.memory[attr>>3&1,0x9000+tile*16:0x9000+tile*16+16])
            indices=decode(source,8,8);expected=self.palette('wBGPals2',attr&7)[indices]
            x=(2+n)*8;assert np.array_equal(actual[32:40,x:x+8],expected),('cold saved-name actual glyph pixels',n)
        return {'name':'Péon ABCDE','native_bold_name_cells_correct':True,'exact_stored_prefix_once':True,
                'actual_RGB555_name_pixels_correct':True,'checksum_verified_identity':True}

    def preview_pixels(self,index,x,y,label):
        source=(ROOT/'gfx/user_battle_v0211'/CLASSES[index]/'overworld.bin').read_bytes()[:64]
        assert bytes(self.p.memory[0,0x9600:0x9640])==source,(label,'wrong native preview bytes')
        cells=[(y+dy)*20+x+dx for dy in range(2) for dx in range(2)]
        assert [self.read('wTilemap',360)[i] for i in cells]==[0x60,0x61,0x62,0x63]
        assert [self.read('wAttrmap',360)[i] for i in cells]==[5]*4
        palette=self.palette('wBGPals2',5)
        indices=decode(source,16,16)
        actual=np.array(self.p.screen.image.convert('RGB'))[y*8:y*8+16,x*8:x*8+16]>>3
        assert np.array_equal(actual,palette[indices]),(label,'preview actual RGB555 framebuffer differs')
        self.preview_checks.append({'label':label,'selected_class':CLASSES[index],
            'native_bank0_4_tiles':True,'actual_palette5':palette.tolist(),'actual_RGB555_framebuffer_exact':True})

    def world_vram(self):
        tile=self.read('wPlayerSpriteTile')[0];bank=0 if tile&128 else 1;address=0x8000+(tile&127)*16
        assert bytes(self.p.memory[bank,address:address+256])==self.art['overworld.bin'][:256],(self.slug,'standing VRAM')
        assert bytes(self.p.memory[bank,address+0x800:address+0x800+512])==self.art['overworld.bin'][256:],(self.slug,'walking VRAM')
        return {'bank':bank,'tile_base':tile&127,'standing_16_tiles':True,'walking_32_tiles':True}

    def palette(self,label,index):
        data=self.read(label,64)[index*8:index*8+8]
        words=[data[i]|data[i+1]<<8 for i in range(0,8,2)]
        return np.array([[w&31,w>>5&31,w>>10&31] for w in words],dtype='uint8')

    def observe_world(self,_):
        if self.read('wBattleMode')[0] or self.read('wScriptMode')[0]:return
        facing=self.read('wPlayerFacing')[0]
        if facing>=16:return
        tile=self.read('wPlayerSpriteTile')[0];base=tile&127;bank=0 if tile&128 else 1
        current_oam=list(self.p.memory[0xfe00:0xfea0]);candidates=(facing,self.previous_facing)
        snapshots=[current_oam]+([self.previous_world_oam] if self.previous_world_oam is not None else [])
        self.previous_facing=facing;self.previous_world_oam=current_oam
        actual=np.array(self.p.screen.image.convert('RGB'))>>3
        # Hardware DMA may already hold the next sprite positions while the
        # framebuffer is the previous completed LCD frame. Both adjacent
        # read-only snapshots are genuine native hardware, not forced poses.
        for oam in snapshots:
            for candidate in candidates:
                if candidate is None:continue
                direction,phase=divmod(candidate,4);pose=0 if phase%2==0 else 1 if phase==1 else 2
                start=base+direction*4+(0 if pose==0 else 0x80 if pose==1 else 0x90)
                entries=[oam[i:i+4] for i in range(0,160,4) if oam[i] and oam[i+1] and
                         start<=oam[i+2]<start+4 and (oam[i+3]>>3&1)==bank]
                if sorted(e[2] for e in entries)!=list(range(start,start+4)):continue
                anchor=next(e for e in entries if e[2]==start)
                geometry={e[2]-start:(e[1]-anchor[1],e[0]-anchor[0]) for e in entries}
                assert geometry=={0:(0,0),1:(8,0),2:(0,8),3:(8,8)},('world composite tile spacing/order',self.slug,candidate,geometry)
                assert all(not e[3]&0x40 for e in entries),'class player vertically mirrored by OAM'
                assert all(not e[3]&0x20 for e in entries),'left/right class accessories mirrored by OAM'
                assert all(e[3]&7==self.object_palette for e in entries),'class actor uses wrong source-family palette'
                matched=True;visible_pixels=0
                source=self.art['overworld.bin'][(pose*4+direction)*64:(pose*4+direction+1)*64]
                for y,x,t,attrs in entries:
                    x-=8;y-=16
                    if not(0<=x<=152 and 0<=y<=136):matched=False;break
                    indices=decode(source[(t-start)*16:(t-start+1)*16],8,8)
                    mask=indices>0;expected=self.palette('wOBPals2',attrs&7)[indices]
                    # The Warlock's follower has native high object priority and
                    # can partly cover a foot on a turn. Compare visible authored
                    # pixels, preserving genuine hardware overlap rather than
                    # pretending that an occluded pixel is a graphics mismatch.
                    current=next(n//4 for n in range(0,160,4)
                                 if oam[n:n+4]==[y+16,x+8,t,attrs])
                    for n in range(current):
                        py,px,pt,pa=oam[n*4:n*4+4];px-=8;py-=16
                        left,top,right,bottom=max(x,px),max(y,py),min(x+8,px+8),min(y+8,py+8)
                        if left>=right or top>=bottom:continue
                        earlier=decode(bytes(self.p.memory[(pa>>3)&1,0x8000+pt*16:0x8000+pt*16+16]),8,8)
                        if pa&32:earlier=earlier[:,::-1]
                        if pa&64:earlier=earlier[::-1,:]
                        mask[top-y:bottom-y,left-x:right-x]&=earlier[top-py:bottom-py,left-px:right-px]==0
                    visible_pixels+=int(mask.sum())
                    if mask.any() and not np.array_equal(actual[y:y+8,x:x+8][mask],expected[mask]):matched=False;break
                if matched and visible_pixels>=16:
                    label=DIRECTIONS[direction]+'_pose_'+str(pose)
                    self.world_facings.add((direction,pose))
                    if label not in self.world_frames:self.world_frames[label]=self.p.screen.image.copy()
                    return

    def observe_oam(self,_):
        """Count live hardware OBJ slots on every observed world frame."""
        entries=[list(self.p.memory[0xfe00+i:0xfe00+i+4]) for i in range(0,160,4)]
        height=16 if self.p.memory[0xff40]&4 else 8
        visible=[e for e in entries if e[0]-16<144 and e[0]-16+height>0]
        # Game Boy scans all Y-matching entries even when X is hidden.
        maximum=max((sum(e[0]-16<=y<e[0]-16+height for e in visible) for y in range(144)),default=0)
        self.oam_report['frames']+=1
        self.oam_report['maximum_visible_entries']=max(self.oam_report['maximum_visible_entries'],len(visible))
        self.oam_report['maximum_entries_on_one_scanline']=max(self.oam_report['maximum_entries_on_one_scanline'],maximum)
        assert len(visible)<=40,('hardware OAM overflow',len(visible))
        assert maximum<=10,('hardware scanline sprite limit exceeded',self.slug,self.map(),self.position(),maximum)

    def world_cycle(self):
        name,w,h=MAPS[self.map()];live=self.live_actors(name)
        occupied={a['xy'] for a in live};danger=set(triggers(name));warps=warp_tiles(name)
        folder=ROOT/'gfx/tilesets/peon_user_environment_v0211'
        meta=(folder/(name+'_meta.bin')).read_bytes()
        priority=(folder/(name+'_priority.bin')).read_bytes()
        blocks=(ROOT/'maps'/(name+'.blk')).read_bytes()
        def roof_at(x,y):
            block=blocks[(y//2)*w+x//2]
            ids=[meta[block*16+(y%2*2+dy)*4+x%2*2+dx] for dy in (0,1) for dx in (0,1)]
            return any(priority[t//8]&(0x80>>(t%8)) for t in ids)
        chosen=None
        for y in range(2,h*2-3):
            for x in range(2,w*2-3):
                cells={(x+a,y+b) for a in range(3) for b in range(3)}
                if cells&(occupied|danger|warps) or any(self.collision_at(*xy)=='WALL' or roof_at(*xy) for xy in cells):continue
                try:self.path((x,y))
                except AssertionError:continue
                chosen=(x,y);break
            if chosen:break
        assert chosen,'no safe walking square in Den'
        self.navigate(chosen);self.world_watch=True;self.advance(60)
        for _ in range(3):
            for key in ('right','down','left','up'):
                self.walk(key);self.walk(key)
        self.advance(60);self.world_watch=False
        needed={(d,p) for d in range(4) for p in range(3)}
        assert needed<=self.world_facings,(self.slug,'missing native world foot/facing pixels',sorted(self.world_facings))
        folder=OUT/self.slug;folder.mkdir(parents=True,exist_ok=True)
        for label,frame in self.world_frames.items():
            frame.save(folder/('world_'+label+'.png'))
            frame.resize((640,576),Image.Resampling.NEAREST).save(folder/('world_'+label+'_4x.png'))
        frames=list(self.world_frames.values())
        frames[0].save(folder/'world_native_facings.gif',save_all=True,append_images=frames[1:],duration=180,loop=0)
        return {'ordinary_directional_taps':True,'safe_square':chosen,'four_directions_three_native_poses_each':True,
                'actual_hardware_OAM_and_RGB555_pixels':True,'strict_16x16_four_tile_composite_geometry':True,'mirrored_accessories':False,'facings':sorted(self.world_facings)}

    def profile(self):
        self.press('start')
        for _ in range(12):
            if self.read('wMenuCursorPosition')==[1]:break
            self.press('up',30)
        before=self.profile_inputs
        self.press('a');self.wait(lambda:self.profile_inputs>before);self.advance(60)
        assert bytes(self.p.memory[0,0x9400:0x9710])==self.art['portrait_frames.bin'][:784]
        cells=[y*20+x for y in range(3,10) for x in range(1,8)]
        tiles=self.read('wTilemap',360);attrs=self.read('wAttrmap',360)
        assert [tiles[i] for i in cells]==list(range(0x40,0x71)),'profile tilemap is not native row-major'
        assert all(not attrs[i]&8 for i in cells),'profile uses wrong VRAM bank'
        assert bytes(attrs[i]&7 for i in cells)==self.profile_attrs,'profile tile palettes differ from imported payload'
        self.packet_pixels(self.art['portrait_frames.bin'][:784],56,56,False,1,3)
        self.capture('character_native_class_portrait');self.press('b');self.press('b');self.advance(120)
        return {'bank0_native_49_tiles':True,'row_major_tilemap':True,'actual_RGB555_pixels':True,'currently_displayed_frame':0}

    def observe_cast(self,_):
        if not self.cast['started'] or not self.read('wBattleMode')[0]:return
        data=bytes(self.p.memory[0,0x9310:0x9550])
        for frame in range(3):
            source=self.art['back_frames.bin'][frame*576:(frame+1)*576]
            if data!=source:continue
            self.cast['vram_poses'].add(frame)
            if self.packet_pixels(source,48,48,True,2,6,strict=False):
                self.cast['pixel_poses'].add(frame)
                if frame not in self.cast['screens']:self.cast['screens'][frame]=self.p.screen.image.copy()
            if len(self.cast['frames'])<180:self.cast['frames'].append(self.p.screen.image.copy())
            # Different authored phases can quantize to identical GBC packets
            # (e.g. a return-to-idle). Keep all matching phase indices; report
            # distinct packet count separately instead of inventing motion.

    def verify_idle(self,label=None):
        self.advance(40)
        assert bytes(self.p.memory[0,0x9310:0x9550])==self.art['back_frames.bin'][:576]
        assert self.read('wPeonPlayerPoseActive')==[0]
        tiles,attrs=self.read('wTilemap',360),self.read('wAttrmap',360)
        cells=[y*20+x for x in range(2,8) for y in range(6,12)]
        assert [tiles[i] for i in cells]==list(range(0x31,0x55))
        wanted=[self.back_attrs[y*6+x] for x in range(6) for y in range(6)]
        assert [attrs[i]&7 for i in cells]==wanted,'back picture regional palettes differ from compiled payload'
        self.packet_pixels(self.art['back_frames.bin'][:576],48,48,True,2,6)
        label=label or 'battle_class_idle_'+str(len(self.casts))
        self.capture(label)
        self.full_player_region_checks.append({'label':label,'all36_source_tiles_and_attributes_exact':True,
                                              'entire48x48_LCD_pixels_exact_no_HUD_mask':True})

    def packet_pixels(self,source,width,height,column,x,y,strict=True):
        """Compare actual RGB555 LCD pixels using every native tile attribute."""
        indices=decode(source,width,height,column)
        attrs=self.read('wAttrmap',360)
        expected=np.zeros((height,width,3),dtype='uint8')
        for dy in range(height//8):
            for dx in range(width//8):
                attr=attrs[(y+dy)*20+x+dx]
                expected[dy*8:dy*8+8,dx*8:dx*8+8]=self.palette('wBGPals2',attr&7)[indices[dy*8:dy*8+8,dx*8:dx*8+8]]
        actual=np.asarray(self.p.screen.image.convert('RGB'))[y*8:y*8+height,x*8:x*8+width]>>3
        passed=np.array_equal(actual,expected)
        if strict:assert passed,(self.slug,'actual RGB555 pixels differ from imported packet',width,height,x,y)
        return passed

    def enemy_import(self,species='rattata'):
        folder=ROOT/'gfx/user_battle_v0211/enemies'/species
        source=(folder/'frames.2bpp').read_bytes()
        assert bytes(self.p.memory[0,0x9000:0x9310])==source,'enemy front is not supplied source packet'
        cells=[y*20+x for y in range(7) for x in range(12,19)]
        attrs=(folder/'attrs.bin').read_bytes()
        assert bytes(self.read('wAttrmap',360)[i]&7 for i in cells)==attrs,'enemy regional palette attrs mismatch'
        self.packet_pixels(source,56,56,True,12,0)
        self.capture('supplied_'+species+'_battle_front')
        return {'species_packet':species,'source_tiles_exact':True,'two_regional_palette_attributes_exact':True,
                'actual_RGB555_pixels_exact':True}

    def imported_npcs(self):
        manifest=json.loads((ROOT/'gfx/user_world_v0211/manifest.json').read_text())
        constants=sprite_constants()
        bindings={constants[row['sprite']]:row['role'] for row in manifest['bindings']}
        records=[]
        actors=self.read('wObjectStructs',13*40)
        for i in range(1,13):
            actor=actors[i*40:(i+1)*40]
            role=bindings.get(actor[0])
            if not role:continue
            tile=actor[2];bank=0 if tile&128 else 1;address=0x8000+(tile&127)*16
            source=(ROOT/'gfx/user_world_v0211'/role/'overworld.bin').read_bytes()
            assert bytes(self.p.memory[bank,address:address+256])==source[:256],('NPC has stale world anatomy',role,i)
            wanted=manifest['roles'][role]['palette_index']
            oam=[list(self.p.memory[0xfe00+n:0xfe00+n+4]) for n in range(0,160,4)]
            current=[e for e in oam if e[0] and (e[3]>>3&1)==bank and (tile&127)<=e[2]<(tile&127)+16]
            assert all(e[3]&7==wanted for e in current),('Actual NPC OAM source-family palette',role,wanted,current)
            records.append({'object':i,'role':role,'four_direction_tiles_exact':True,
                            'actual_OAM_palette_index':wanted if current else None,'actual_OAM_entries_compared':len(current),
                            'raw_legacy_actor_palette':actor[6]&7,'vram_bank':bank})
        assert records,'No native imported NPC could be observed at The Den'
        return records

    def environment_import(self):
        name,_,_=MAPS[self.map()]
        folder=ROOT/'gfx/tilesets/peon_user_environment_v0211'
        source=(folder/(name+'.2bpp')).read_bytes()
        assert len(source)==192*16
        prefix='PeonUserEnv'+name
        pointers={}
        for field,label in [('wTilesetBank',prefix+'GFX'),('wTilesetBlocksBank',prefix+'Meta'),
                            ('wTilesetCollisionBank',prefix+'Coll')]:
            wanted=self.sym[label];actual=self.read(field,3)
            assert actual==[wanted[0],wanted[1]&255,wanted[1]>>8],('map native source pointer',name,field,actual,wanted)
            pointers[field]=actual
        assert self.read('wTilesetPalettes',2)==list(self.sym[prefix+'PalMap'][1].to_bytes(2,'little'))
        assert self.read('wTilesetAnim',4)[2:]==list(self.sym[prefix+'Priority'][1].to_bytes(2,'little'))
        priority=(folder/(name+'_priority.bin')).read_bytes()
        # Scrolling publishes wBGMapPalBuffer directly. wAttrmap is a stale
        # initial-screen buffer after movement; inspect the actual PPU map.
        lcdc=self.p.memory[0xff40]
        base=0x9c00 if lcdc&8 else 0x9800
        scx,scy=self.p.memory[0xff43],self.p.memory[0xff42]
        assert scx%8==0 and scy%8==0,('Map capture is mid-scroll',scx,scy)
        positions=[base+((scy//8+y)%32)*32+(scx//8+x)%32 for y in range(18) for x in range(20)]
        physical=[self.p.memory[0,p] for p in positions]
        attrs=[self.p.memory[1,p] for p in positions]
        tiles=[t|((a&8)<<4) for t,a in zip(physical,attrs)]
        expected=[bool(priority[t//8]&(0x80>>(t%8))) for t in tiles]
        actual=[bool(attr&0x80) for attr in attrs]
        assert actual==expected,('native PPU initial/scroll roof priority bits differ',name,
                                 [(i%20,i//20,tiles[i],attrs[i],expected[i]) for i in range(360) if actual[i]!=expected[i]][:15])
        # IDs0–3 are the expected native fire frames and change during play.
        assert bytes(self.p.memory[0,0x9040:0x9600])==source[64:1536],('map bank0 new decor differs',name)
        assert bytes(self.p.memory[1,0x9000:0x9600])==source[1536:],('map bank1 new decor differs',name)
        self.capture('supplied_environment_'+name)
        return {'map':name,'native_header_pointers_exact':pointers,'static_tiles_RGB555_indices_exact':True,
                'dynamic_fire_tiles_excluded':[0,1,2,3],'source_packet_sha256':digest(source),
                'bank0_static_tiles_compared':92,'bank1_static_tiles_compared':96,
                'all360_PPU_visible_roof_priority_bits_exact':True,'roof_priority_cells':sum(expected),
                'actual_hardware_bg_map_base':base,'scroll_xy':[scx,scy]}

    def save_exit_continue(self):
        self.navigate((12,9));self.press('down',30)
        before=ExitSession.complete_record(self)
        saves=self.native_counts['save'];self.press('start')
        for _ in range(12):
            cursor=self.read('wMenuCursorPosition')[0]
            if cursor==4:break
            self.press('up' if cursor>4 else 'down',30)
        assert self.read('wMenuCursorPosition')==[4]
        self.press('a')
        for _ in range(15):
            if self.native_counts['save']>saves and self.presentation=='world':break
            self.press('a',180)
        assert self.native_counts['save']==saves+1 and self.presentation=='world'
        assert ExitSession.complete_record(self)==before,'Native SAVE changed persistent game record'
        self.capture('native_real_save_after_battle')
        self.press('start')
        for _ in range(12):
            if self.read('wMenuCursorPosition')==[7]:break
            self.press('down',30)
        assert self.read('wMenuCursorPosition')==[7]
        self.capture('native_exit_highlighted')
        exits=self.native_counts['exit'];self.p.button_press('a');self.advance(240)
        assert self.native_counts['exit']==exits+1 and self.presentation=='exit_release','Held EXIT confirmation skipped title'
        self.p.button_release('a');self.advance(600)
        assert self.presentation=='title','EXIT did not return to native title'
        self.capture('native_exit_title_requires_fresh_start')
        self.press('start');self.advance(120)
        assert self.presentation=='select'
        self.capture('native_exit_saved_class_preview')
        self.press('a',240)
        for _ in range(30):
            if self.presentation=='world' and self.read('wScriptMode')==[0]:break
            self.advance(30)
        assert self.presentation=='world' and self.read('wBattleMode')==[0]
        self.advance(120)
        assert ExitSession.complete_record(self)==before,'EXIT/Continue changed the exact saved full party/bag/name/location record'
        assert self.native_counts['save']==saves+1,'EXIT unexpectedly saved'
        self.world_vram();self.capture('native_exit_continue_exact_saved_record')
        return {'native_save':True,'held_confirmation_release_guard':True,'exit_returns_to_title':True,
                'fresh_start_required':True,'continue_full_saved_record_equal':True,'exit_does_not_autosave':True,
                'last_saved_map':before['wMapGroup'],'last_saved_x':before['wXCoord'],'last_saved_y':before['wYCoord']}

    def real_door(self,door,inside,label):
        outside=self.map()
        self.navigate(door,inside);self.advance(120)
        assert self.read('wScriptMode')==[0] and self.read('wBattleMode')==[0]
        self.world_vram();packet=self.environment_import();self.capture(label+'_inside')
        self.navigate((5,7),outside);self.advance(120)
        self.world_vram();self.environment_import();self.capture(label+'_outside')
        return {'door':door,'exterior_map':outside,'interior_map':inside,
                'ordinary_controls_only':True,'returned_to_correct_exterior':True,'native_interior_packet':packet}

    def scene_route(self):
        self.advance(1800);self.press('start');self.advance(120)
        assert self.presentation=='select' and self.read('wMenuCursorX')==[2]
        self.capture('private_battery_saved_warlock_preview')
        self.press('a',240)
        for _ in range(30):
            if self.presentation=='world' and self.read('wScriptMode')==[0]:break
            self.advance(30)
        assert self.map()==17 and self.native_counts['new_game']==0 and self.native_counts['continue']==1
        assert self.event('EVENT_PEON_WARLOCK') and self.read('wPartyCount')[0]>=2
        self.world_vram();self.environment_import()
        # Deliberately crowded real Warlock scene, with guards, both recruit
        # nodes and its actual native follower retained.
        self.navigate((10,14));self.world_watch=True;self.advance(120)
        for point in ((10,13),(11,13),(12,13),(13,13),(13,14),(13,15),(12,15),(11,15),(10,15),(10,14)):
            self.navigate(point);self.advance(40)
        self.advance(240);self.world_watch=False
        self.capture('private_battery_populated_senjin_source_npcs')
        npcs=self.imported_npcs()
        doors=[]
        for n,(door,inside) in enumerate([((5,5),21),((15,5),24),((17,9),21)],1):
            doors.append(self.real_door(door,inside,'senjin_door_'+str(n)))
        # This genuine old save has already unlocked travel north. Routing
        # uses a genuine RUN from the road packet guarding Senjin's entrance,
        # then steers around its remaining living coordinate events.
        self.navigate((10,4),16);self.advance(120);self.environment_import()
        self.navigate((12,23));self.wait(lambda:self.phase=='battle',buttons=True)
        escape=self.flee_road_for_doors()
        self.navigate((12,4),18);self.advance(120);self.environment_import()
        for n,(door,inside) in enumerate([((5,5),22),((17,5),23),((17,13),22),((5,15),22)],1):
            doors.append(self.real_door(door,inside,'razor_hill_door_'+str(n)))
        return {'passed':True,'private_native_save_continue':True,'new_game_not_started':True,
                'ram_writes':False,'emulator_states_loaded':False,'crowded_senjin_oam':self.oam_report,
                'imported_senjin_npcs':npcs,'actual_road_run':escape,'seven_real_building_door_round_trips':doors}

    def flee_road_for_doors(self):
        before_flags=self.read('wEventFlags',256);before_xp=self.experience();before_money=self.money()
        for _ in range(24):
            if not self.read('wBattleMode')[0]:break
            self.ready('battle')
            hp=int.from_bytes(bytes(self.read('wBattleMonHP',2)),'big')
            maximum=int.from_bytes(bytes(self.read('wBattleMonMaxHP',2)),'big')
            if hp*2<=maximum and self.item_quantity(18):
                self.open_bag_item(18);menus=self.menus;self.press('a',30)
                self.wait(lambda:self.menus>menus and self.phase=='battle' or not self.read('wBattleMode')[0],buttons=True)
                continue
            for _ in range(5):
                x,y=self.read('wMenuCursorX')[0],self.read('wMenuCursorY')[0]
                if (x,y)==(2,2):break
                self.press('right' if x<2 else 'down',30)
            menus=self.menus;self.phase,self.context='run_pending',None;self.press('a',30)
            self.wait(lambda:self.menus>menus and self.phase=='battle' or not self.read('wBattleMode')[0],buttons=True)
        assert self.read('wBattleMode')==[0] and self.read('wBattleResult')==[2],'Travel did not exit by actual RUN'
        self.close_dialogue()
        assert self.read('wEventFlags',256)==before_flags,'Travel RUN retired a living enemy'
        assert self.experience()==before_xp and self.money()==before_money
        self.capture('actual_road_run_no_loot_or_retirement')
        return {'native_run':True,'no_experience_or_loot':True,'no_encounter_retirement':True,
                'ram_writes':False,'emulator_states_loaded':False}

    def cast_once(self,slot,label,required):
        self.ready('battle');self.verify_idle();menus=self.menus;move_menus=self.move_menus
        self.cast={'label':label,'started':False,'actual_moves':set(),'vram_poses':set(),
                   'pixel_poses':set(),'screens':{},'frames':[]}
        for _ in range(5):
            x,y=self.read('wMenuCursorX')[0],self.read('wMenuCursorY')[0]
            if (x,y)==(1,1):break
            self.press('left' if x>1 else 'up',30)
        self.press('a',60);self.wait(lambda:self.move_menus>move_menus)
        self.verify_idle('battle_fight_menu_default_'+str(len(self.casts)))
        for _ in range(6):
            cursor=self.read('wMenuCursorY')[0]-1
            if cursor==slot:break
            self.press('up' if cursor>slot else 'down',30)
        self.verify_idle('battle_fight_menu_selected_'+str(len(self.casts)))
        selected=self.read('wBattleMonMoves',4)[slot]
        self.press('a',30)
        for _ in range(200):
            if not self.read('wBattleMode')[0] or self.menus>menus and self.phase=='battle':break
            self.press('a',40)
        case=self.cast;self.cast=None
        assert case['actual_moves']=={selected},(label,'wrong actual move',case['actual_moves'],selected)
        assert set(required)<=case['vram_poses'] and set(required)<=case['pixel_poses'],(self.slug,label,required,case['vram_poses'],case['pixel_poses'])
        folder=OUT/self.slug
        for frame,image in case['screens'].items():
            image.save(folder/(label+'_pose_'+str(frame)+'.png'))
            image.resize((640,576),Image.Resampling.NEAREST).save(folder/(label+'_pose_'+str(frame)+'_4x.png'))
        if case['frames']:
            frames=[im.resize((480,432),Image.Resampling.NEAREST) for im in case['frames']]
            frames[0].save(folder/(label+'_native.gif'),save_all=True,append_images=frames[1:],duration=17,loop=0)
        result={'label':label,'actual_move':selected,'native_vram_poses':sorted(case['vram_poses']),
                'actual_RGB555_pixel_poses':sorted(case['pixel_poses']),'required_poses':list(required),
                'distinct_source_packets':len({self.art['back_frames.bin'][i*576:(i+1)*576] for i in range(3)}),
                'matching_identical_source_indices_are_not_claimed_as_distinct_motion':True,
                'ordinary_battle_inputs':True,'native_frames_retained':len(case['frames'])}
        self.casts.append(result);return result

    def finish_battle(self):
        self.until_world(choose_bolt=False);self.advance(90)
        assert self.read('wBattleMode')==[0] and self.read('wScriptMode')==[0]
        self.world_vram()

    def cold_graphics(self):
        self.navigate((12,9));self.press('down',30);before=self.persistent_snapshot()
        self.press('start')
        for _ in range(12):
            if self.read('wMenuCursorPosition')==[1]:break
            self.press('up',30)
        for _ in range(3):self.press('down',30)
        self.press('a')
        for _ in range(5):self.press('a',180)
        self.capture('native_class_saved');self.p.stop(save=True)
        battery=Path(str(self.rom)+'.ram');assert battery.stat().st_size==32768
        self.open();self.advance(1800);self.press('start');self.advance(120)
        assert bytes(self.p.memory[0,0x9600:0x9640])==self.art['overworld.bin'][:64],'cold saved class preview wrong before Continue'
        assert self.read('wMenuCursorX')==[self.class_index]
        self.capture('cold_saved_character_preview_before_continue')
        saved_name=self.saved_name_pixels()
        for _ in range(15):
            if self.map()==14 and self.read('wScriptMode')==[0]:break
            self.press('a',180)
        self.advance(90);after=self.persistent_snapshot()
        assert before==after,'cold restart changed saved record/class bits'
        self.world_vram();self.capture('cold_continue_correct_world_class')
        return {'battery_bytes':32768,'saved_preview_before_continue_correct':True,
                'saved_character_name':saved_name,
                'complete_record_and_all_256_event_bytes_preserved':True,'world_class_graphics_reloaded':True}


class MigrationSession(PetSession):
    """Ordinary controls on old/new private batteries; no art substitutions."""
    collision_at=GraphicsSession.collision_at

    def __init__(self,rom,sym,output):
        self.output=Path(output);self.output.mkdir(parents=True,exist_ok=True)
        self.presentation='boot';self.saves=0
        super().__init__(rom,sym,2)

    def write(self,*args,**kwargs):raise AssertionError('Legacy migration permits no RAM writes.')

    def open(self):
        super().open()
        for label,phase in [('PeonTitleScreen.wait','title'),('PeonCharacterSelect.input','select'),
                            ('HandleMapTimeAndJoypad','world')]:
            self.p.hook_register(*self.sym[label],lambda p:setattr(self,'presentation',p),phase)
        self.p.hook_register(*self.sym['_SaveGameData'],lambda _:setattr(self,'saves',self.saves+1),None)

    def capture(self,label):
        self.p.screen.image.save(self.output/(label+'.png'))
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(self.output/(label+'_4x.png'))

    def normal_continue(self):
        self.p.tick(1800,True);self.press('start');self.press('a',240)
        for _ in range(30):
            if self.presentation=='world' and self.read('wScriptMode')==[0]:break
            self.p.tick(30,True)
        assert self.presentation=='world' and self.map()==14 and self.read('wBattleMode')==[0]
        self.p.tick(120,True)

    def actual_save(self):
        before=self.saves;self.press('start')
        for _ in range(12):
            cursor=self.read('wMenuCursorPosition')[0]
            if cursor==4:break
            self.press('up' if cursor>4 else 'down',30)
        assert self.read('wMenuCursorPosition')==[4]
        self.press('a')
        for _ in range(15):
            if self.saves>before and self.presentation=='world':break
            self.press('a',180)
        assert self.saves==before+1 and self.presentation=='world'


def migration_check(rom,sym,output):
    """Link all17 mappings, then replay one genuine old SAVE→new Continue."""
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ROOT/'references/generated/user_environment_v0211/manifest.json').read_text())
    rows=[]
    map_ids={'THE_DEN':14,'SENJIN_VILLAGE':17,'RAZOR_HILL':18}
    current=None
    for line in (ROOT/'data/maps/peon_user_environment_relocations_v0211.asm').read_text().splitlines():
        if line.strip().startswith('map_id '):current=map_ids[line.split()[-1]]
        elif current and re.match(r'\s*db \d',line):
            x,y,tx,ty=map(int,line.strip().split('db ',1)[1].split(','))
            name,w,h=MAPS[current]
            blocks=(ROOT/'maps'/(name+'.blk')).read_bytes()
            collisions=[r.split('peon_user_tilecoll',1)[1].split(';',1)[0].replace(' ','').split(',')
                        for r in (ROOT/'gfx/tilesets/peon_user_environment_v0211'/(name+'_coll.asm')).read_text().splitlines()
                        if 'peon_user_tilecoll' in r]
            def at(a,b):return collisions[blocks[b//2*w+a//2]][b%2*2+a%2]
            assert at(x,y)=='WALL' and at(tx,ty)!='WALL',('Migration destination collision',name,x,y,tx,ty)
            rows.append([26,current,x,y,tx,ty])
    assert len(rows)==17
    bank,address=sym['PeonUserEnvironmentBlockedCellsV0211']
    offset=address if bank==0 else bank*0x4000+address-0x4000
    expected=bytes(v for row in rows for v in row)+b'\xff'
    assert Path(rom).read_bytes()[offset:offset+len(expected)]==expected,'Compiled17-row migration table differs'
    old=Path('/tmp/peon_exit_v0210_candidate_02')
    old_rom=old/'pokecrystal.gbc';old_sym=old/'pokecrystal.sym'
    fixture=Path('/tmp/peon_v029_progress_batteries/4530c718bf29_warlock.ram')
    assert digest(old_rom.read_bytes())=='0e2d747636788211b9a046df698ef9fecdafd1166e0514381815fd88ed22bb66'
    assert digest(old_sym.read_bytes())=='4db6b724020465cfa2d0695e0ffc77643a02d13fa7446a8f7eaa99639d09d0ce'
    source_sha=digest(fixture.read_bytes())
    assert source_sha=='176519b849b2f7cd1a3f9e0477d14e11d7ca5b29977d35255b89f5974bde2a16'
    with tempfile.TemporaryDirectory(prefix='peon-genuine-v0210-blocked-save-') as temp:
        path=Path(temp)/'old.gbc';shutil.copyfile(old_rom,path);shutil.copyfile(fixture,Path(str(path)+'.ram'))
        s=MigrationSession(path,symbols_from_file(old_sym),output/'old')
        try:
            s.normal_continue();s.navigate((15,4));s.p.tick(90,True)
            assert s.position()==(15,4)
            before=ExitSession.complete_record(s);s.actual_save();s.capture('old_native_save_at_new_facade_body')
            assert ExitSession.complete_record(s)==before
            s.p.stop(save=True);s.p=None
            new=Path(temp)/'new.gbc';shutil.copyfile(rom,new)
            shutil.copyfile(Path(str(path)+'.ram'),Path(str(new)+'.ram'))
        finally:
            if s.p:s.p.stop(save=False)
        s=MigrationSession(new,sym,output/'new')
        try:
            s.normal_continue();after=ExitSession.complete_record(s)
            assert s.position()==(15,3),'Blocked legacy save did not move to declared adjacent floor'
            allowed={'wXCoord','wYCoord'}
            assert {k:v for k,v in before.items() if k not in allowed}=={k:v for k,v in after.items() if k not in allowed},'Migration changed persistent record beyond coordinates'
            s.capture('new_continue_at_declared_safe_floor')
            origin=s.position()
            for direction in ('left','right','up','down'):
                for _ in range(6):
                    s.press(direction,40)
                    if s.position()!=origin:break
                if s.position()!=origin:break
            assert sum(abs(a-b) for a,b in zip(origin,s.position()))==1,'Migrated character cannot take an ordinary step'
            s.capture('new_continue_can_walk')
        finally:s.p.stop(save=False)
    assert digest(fixture.read_bytes())==source_sha,'Source genuine battery changed'
    return {'passed':True,'compiled17_rows_and_all_safe_destination_collisions_exact':True,'mappings':rows,
            'actual_old_v0210_native_save_position':[15,4],'actual_new_continue_position':[15,3],
            'complete_six_party_records_identity_bag_events_money_preserved':True,'ordinary_step_after_migration':True,
            'ordinary_controls_only':True,'ram_writes':False,'emulator_states_loaded':False,
            'source_private_battery_sha256':source_sha,'source_private_battery_preserved':True,
            'source_provenance':'recruitment_v029/team_runtime/final/validation.json genuine_recruited_party_cold_save'}


def main():
    global BASE,OUT
    parser=argparse.ArgumentParser();parser.add_argument('--expected-sha',required=True);parser.add_argument('--class',dest='class_name',choices=CLASSES)
    parser.add_argument('--rom',type=Path,default=ROOT/'pokecrystal.gbc');parser.add_argument('--sym',type=Path,default=ROOT/'pokecrystal.sym')
    parser.add_argument('--out',type=Path,default=BASE)
    parser.add_argument('--scene-battery',type=Path)
    parser.add_argument('--scene-only',action='store_true')
    parser.add_argument('--migration-only',action='store_true')
    args=parser.parse_args();BASE=OUT=args.out;routes.OUT=OUT
    logging.disable(logging.CRITICAL);OUT.mkdir(parents=True,exist_ok=True)
    sha=digest(args.rom.read_bytes());assert sha==args.expected_sha
    sym=symbols_from_file(args.sym);report={'rom_sha256':sha,'symbols_sha256':digest(args.sym.read_bytes()),'passed':False,
          'method':'Ordinary inputs only; read-only actual native VRAM/OAM/RGB555 and battery observation against supplied/derived v0211 packets.',
          'ram_writes':False,'emulator_states_loaded':False,'user_battery_files_opened':False,'classes':{}}
    with tempfile.TemporaryDirectory(prefix='peon-v0211-user-art-native-') as temp:
        for index,slug in enumerate(CLASSES):
            if args.scene_only or args.migration_only:break
            if args.class_name and slug!=args.class_name:continue
            rom=Path(temp)/(slug+'.gbc');shutil.copyfile(args.rom,rom)
            s=GraphicsSession(rom,sym,index)
            try:
                s.fresh_class();s.advance(90);fresh=s.world_vram();assert s.hold_import,'Opening never displayed the native Hold room'
                previews=[u for u in s.uploads if u['kind']=='preview' and u['frame']==index]
                assert previews,'highlighted class preview never loaded native tiles'
                s.capture('fresh_class_native_world');walking=s.world_cycle();npcs=s.imported_npcs();exterior=s.environment_import();profile=s.profile();s.world_vram()
                # Locked map menu and a real room door must reload the selected
                # actor rather than the original Shaman default.
                s.press('select');s.advance(60);s.capture('map_menu_before_unlock');s.press('b');s.advance(120);s.world_vram()
                s.navigate((17,5),23);s.advance(90);s.world_vram();interior=s.environment_import();s.capture('class_inside_inn')
                s.navigate((5,7),14);s.advance(90);s.world_vram();s.capture('class_after_door_reload');s.environment_import()
                hut=s.real_door((5,7),22,'den_hut')
                cold=s.cold_graphics()
                s.talk_plain((10,10),'up');s.navigate((18,13));s.press('up',30);s.press('a',60)
                s.wait(lambda:s.phase=='battle',buttons=True);s.advance(60)
                enemy=s.enemy_import()
                if index==0:
                    menus=s.menus;s.open_bag_item(148);s.press('a',30)
                    s.wait(lambda:s.menus>menus and s.phase=='battle',buttons=True)
                    assert s.read('wPeonEarthTotemActive')==[1]
                    spell=s.cast_once(1,'lightning_bolt',(0,1));s.finish_battle();s.rest()
                elif index==2:
                    spell=s.cast_once(1,'shadow_bolt',(0,1,2));s.finish_battle();s.rest()
                else:
                    physical=s.cast_once(0,'physical_strike',(0,1,2));s.finish_battle();s.rest()
                if index!=1:
                    s.navigate((18,14));s.wait(lambda:s.phase=='battle',buttons=True);s.advance(60)
                    physical=s.cast_once(0,'wand_strike' if index==2 else 'physical_strike',(0,1,2));s.finish_battle();s.rest()
                exit_result=s.save_exit_continue()
                assert not s.hook_errors,s.hook_errors
                back_checks=[u for u in s.uploads if u['kind']=='back' and u['protected_battle_regions_unchanged']]
                assert back_checks and {0,1,2}<={u['frame'] for u in back_checks},'missing protected native back uploads'
                report['classes'][slug]={'passed':True,'highlighted_class_preview':previews[-1],
                    'actual_preview_palette_and_framebuffer_checks':s.preview_checks,
                    'fresh_world_vram':fresh,'world_movement':walking,'character_profile':profile,
                    'map_menu_and_room_door_class_reload':True,'cold_save':cold,'actual_battle_casts':s.casts,
                    'imported_world_npcs':npcs,'first_enemy_source_art':enemy,'world_oam_budget':s.oam_report,
                    'native_user_environment_packets':[s.hold_import,exterior,interior],
                    'den_hut_round_trip':hut,
                    'save_exit_continue':exit_result,
                    'all_native_back_uploads_protect_enemy_font_emblem_totem_pet_and_hud':True,
                    'back_helper_observations':back_checks,'native_upload_count':len(s.uploads),
                    'read_only_hook_errors':s.hook_errors,'native_asset_sha256':{k:digest(v) for k,v in s.art.items()}}
                report['classes'][slug]['whole_back_visible_on_idle_and_FIGHT_selection']=s.full_player_region_checks
                print(slug,'GRAPHICS PASS',flush=True)
            except BaseException as error:
                s.capture('first_failure')
                failures=BASE/'failures';failures.mkdir(parents=True,exist_ok=True)
                stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
                label=slug+'_'+sha[:8]+'_'+stamp
                s.p.screen.image.save(failures/(label+'.png'))
                (failures/(label+'.json')).write_text(json.dumps({'rom_sha256':sha,'passed':False,
                    'class':slug,'error':repr(error),'read_only_hook_errors':s.hook_errors,
                    'map':s.map(),'xy':s.position(),'observed_preview_palette5':s.palette('wBGPals2',5).tolist(),
                    'rWBK':s.p.memory[0xff70],'hBGMapMode':s.read('hBGMapMode'),
                    'observed_profile_attrs':[s.read('wAttrmap',360)[y*20+x] for y in range(3,10) for x in range(1,8)],
                    'expected_profile_attrs':list(s.profile_attrs),
                    'observed_all_bg_palettes':[s.palette('wBGPals2',i).tolist() for i in range(8)],
                    'actual_world_facings_seen':sorted(s.world_facings)},indent=2)+'\n')
                raise
            finally:s.p.stop(save=False)
        if args.scene_battery:
            assert args.scene_battery.stat().st_size==32768
            battery_sha=digest(args.scene_battery.read_bytes())
            rom=Path(temp)/'warlock_scene.gbc';shutil.copyfile(args.rom,rom)
            shutil.copyfile(args.scene_battery,Path(str(rom)+'.ram'))
            previous_out=OUT;OUT=BASE/'scene'
            s=GraphicsSession(rom,sym,2)
            try:
                report['private_scene']=s.scene_route()
                report['private_scene']['source_battery_sha256']=battery_sha
                assert digest(args.scene_battery.read_bytes())==battery_sha,'Source private battery was changed'
            except BaseException as error:
                s.capture('first_failure')
                (BASE/'scene_failure.json').write_text(json.dumps({'rom_sha256':sha,'passed':False,
                    'failure':repr(error),'map':s.map(),'position':s.position(),'hook_errors':s.hook_errors},indent=2)+'\n')
                raise
            finally:s.p.stop(save=False);OUT=previous_out
        if args.migration_only:report['legacy_migration']=migration_check(args.rom,sym,BASE/'legacy_migration')
    assert digest(args.rom.read_bytes())==sha,'source ROM changed during graphics QA'
    report['passed']=True
    destination=BASE/('migration_validation.json' if args.migration_only else 'validation.json' if not args.class_name else 'validation_'+args.class_name+'.json')
    destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'rom_sha256':sha,'passed':True,'classes':list(report['classes'])},indent=2))

if __name__=='__main__':main()
