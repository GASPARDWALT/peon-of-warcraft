#!/usr/bin/env python3
"""Observe three native class graphics routes without editing RAM or loading states.

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
from validate_peon_villages import MAPS, load_symbols, warp_tiles
from validate_durotar_v022_quests import triggers
from validate_peon_deep_ui import text_encoding

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'references/generated/visual_polish_v026/classes'
OUT=BASE/'runtime'
routes.OUT=OUT
CLASSES=('shaman','warrior','warlock')
DIRECTIONS=('down','up','left','right')


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
        self.slug=CLASSES[index];self.art={name:(ROOT/'gfx/peon_classes'/self.slug/name).read_bytes()
                                          for name in ('overworld.bin','back_frames.bin','portrait_frames.bin')}
        self.upload_pending=[];self.uploads=[];self.hook_errors=[];self.world_watch=False
        self.world_frames={};self.world_facings=set();self.previous_facing=None;self.previous_world_oam=None
        self.cast=None;self.casts=[];self.last_world_vram=None
        self.preview_checks=[]
        super().__init__(rom,symbols,index,section='normal')

    def write(self,*args,**kwargs):raise AssertionError('This graphics route permits no emulator RAM writes.')

    def open(self):
        super().open()
        for label,kind in [('PeonLoadClassPlayerBackPose','back'),('PeonLoadClassProfileFrame','profile'),
                           ('PeonLoadClassWorldPreview','preview')]:
            self.p.hook_register(*self.sym[label],lambda kind:self.safe(self.upload_enter,kind),kind)
        # Shared native Get2bpp adapter restores VBK immediately before RET.
        # Tail calls (back/profile) and direct preview calls are distinguished
        # by observed stack depth; there is no inserted call or CPU substitution.
        bank,address=self.sym['PeonClassGet2bppBank0']
        offset=bank*0x4000+address-0x4000
        code=self.rom.read_bytes()[offset:offset+32]
        end=code.index(bytes((0xf1,0xe0,0x4f,0xc9)))+3
        self.p.hook_register(bank,address+end,lambda _:self.safe(self.upload_done,None),None)
        self.p.hook_register(*self.sym['PeonAnimatePlayerAttack'],lambda _:self.safe(self.attack_start,None),None)

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
                'attrmap':digest(bytes(self.read('wAttrmap',360)))}

    def upload_enter(self,kind):
        frame=self.p.register_file.C
        assert 0<=frame<=2,(kind,frame)
        if kind=='preview':
            expected=(ROOT/'gfx/peon_classes'/CLASSES[frame]/'overworld.bin').read_bytes()[:64]
            target=0x9600
        else:
            size=576 if kind=='back' else 784
            expected=self.art['back_frames.bin' if kind=='back' else 'portrait_frames.bin'][frame*size:(frame+1)*size]
            target=0x9310 if kind=='back' else 0x9400
        self.upload_pending.append({'kind':kind,'frame':frame,'target':target,'expected':expected,
          'sp':self.p.register_file.SP,'vbk':self.p.memory[0xff4f],
          'events':digest(bytes(self.read('wEventFlags',256))),
          'font1_range':(0x8920,0x8a90) if self.read('wBattleMode')[0] else (0x9690,0x9800),
          'font1':digest(bytes(self.p.memory[1,0x8920:0x8a90])) if self.read('wBattleMode')[0]
                    else digest(bytes(self.p.memory[1,0x9690:0x9800])),
          'protected':self.protected_back() if kind=='back' and self.read('wBattleMode')[0] else None,
          'cursor_y':self.read('wMenuCursorY')[0],'cursor_x':self.read('wMenuCursorX')[0]})

    def upload_done(self,_):
        sp=self.p.register_file.SP
        for pending in reversed(self.upload_pending):
            wanted=pending['sp']-2 if pending['kind']=='preview' else pending['sp']
            if sp!=wanted:continue
            actual=bytes(self.p.memory[0,pending['target']:pending['target']+len(pending['expected'])])
            assert actual==pending['expected'],(pending['kind'],self.slug,pending['frame'],'native VRAM differs',digest(actual),digest(pending['expected']))
            assert self.p.memory[0xff4f]==pending['vbk'],'class upload did not restore VBK'
            assert digest(bytes(self.read('wEventFlags',256)))==pending['events'],'graphics upload changed saved flags'
            start,end=pending['font1_range']
            assert digest(bytes(self.p.memory[1,start:end]))==pending['font1'],'class upload damaged bold font bank1'
            if pending['protected'] is not None:
                assert self.protected_back()==pending['protected'],'rear pose upload damaged enemy/font/emblem/totem/pet/HUD'
            row={k:v for k,v in pending.items() if k not in ('expected','protected','events','font1','sp','vbk')}
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
        source=(ROOT/'gfx/peon_classes'/CLASSES[index]/'overworld.bin').read_bytes()[:64]
        assert bytes(self.p.memory[0,0x9600:0x9640])==source,(label,'wrong native preview bytes')
        cells=[(y+dy)*20+x+dx for dy in range(2) for dx in range(2)]
        assert [self.read('wTilemap',360)[i] for i in cells]==[0x60,0x61,0x62,0x63]
        assert [self.read('wAttrmap',360)[i] for i in cells]==[5]*4
        palette=self.palette('wBGPals2',5)
        wanted=np.array([[31,29,23],[18,11,6],[15,22,8],[1,1,1]],dtype='uint8')
        assert np.array_equal(palette,wanted),(label,'class preview palette5 is not paper/brown/green/outline',palette.tolist())
        indices=decode(source,16,16)
        actual=np.array(self.p.screen.image.convert('RGB'))[y*8:y*8+16,x*8:x*8+16]>>3
        assert np.array_equal(actual,wanted[indices]),(label,'preview actual RGB555 framebuffer differs')
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
                assert all(not e[3]&0x20 for e in entries),'left/right class accessories mirrored by OAM'
                assert all(e[3]&7==2 for e in entries),'class player changed green NPC palette'
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

    def world_cycle(self):
        name,w,h=MAPS[self.map()];live=self.live_actors(name)
        occupied={a['xy'] for a in live};danger=set(triggers(name));warps=warp_tiles(name)
        chosen=None
        for y in range(2,h*2-3):
            for x in range(2,w*2-3):
                cells={(x+a,y+b) for a in range(3) for b in range(3)}
                if cells&(occupied|danger|warps) or any(self.collision_at(*xy)=='WALL' for xy in cells):continue
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
                'actual_hardware_OAM_and_RGB555_pixels':True,'mirrored_accessories':False,'facings':sorted(self.world_facings)}

    def profile(self):
        self.press('start')
        for _ in range(12):
            if self.read('wMenuCursorPosition')==[1]:break
            self.press('up',30)
        self.press('a');self.advance(60)
        assert bytes(self.p.memory[0,0x9400:0x9710])==self.art['portrait_frames.bin'][:784]
        cells=[y*20+x for y in range(3,10) for x in range(1,8)]
        tiles=self.read('wTilemap',360);attrs=self.read('wAttrmap',360)
        assert [tiles[i] for i in cells]==list(range(0x40,0x71)),'profile tilemap is not native row-major'
        assert all(not attrs[i]&8 for i in cells),'profile uses wrong VRAM bank'
        indices=decode(self.art['portrait_frames.bin'][:784],56,56)
        expected=self.palette('wBGPals2',attrs[cells[0]]&7)[indices]
        actual=np.array(self.p.screen.image.convert('RGB'))[24:80,8:64]>>3
        assert np.array_equal(actual,expected),'native character portrait RGB555 pixels differ'
        self.capture('character_native_class_portrait');self.press('b');self.press('b');self.advance(120)
        return {'bank0_native_49_tiles':True,'row_major_tilemap':True,'actual_RGB555_pixels':True,'currently_displayed_frame':0}

    def observe_cast(self,_):
        if not self.cast['started'] or not self.read('wBattleMode')[0]:return
        data=bytes(self.p.memory[0,0x9310:0x9550])
        for frame in range(3):
            source=self.art['back_frames.bin'][frame*576:(frame+1)*576]
            if data!=source:continue
            self.cast['vram_poses'].add(frame)
            indices=decode(source,48,48,True);expected=self.palette('wBGPals2',0)[indices]
            actual=np.array(self.p.screen.image.convert('RGB'))[48:96,16:64]>>3
            if np.array_equal(actual,expected):
                self.cast['pixel_poses'].add(frame)
                if frame not in self.cast['screens']:self.cast['screens'][frame]=self.p.screen.image.copy()
            if len(self.cast['frames'])<180:self.cast['frames'].append(self.p.screen.image.copy())
            break

    def verify_idle(self):
        self.advance(40)
        assert bytes(self.p.memory[0,0x9310:0x9550])==self.art['back_frames.bin'][:576]
        assert self.read('wPeonPlayerPoseActive')==[0]
        tiles,attrs=self.read('wTilemap',360),self.read('wAttrmap',360)
        cells=[y*20+x for x in range(2,8) for y in range(6,12)]
        assert [tiles[i] for i in cells]==list(range(0x31,0x55))
        assert [attrs[i] for i in cells]==[0]*36
        self.capture('battle_class_idle_'+str(len(self.casts)))

    def cast_once(self,slot,label,required):
        self.ready('battle');self.verify_idle();menus=self.menus;move_menus=self.move_menus
        self.cast={'label':label,'started':False,'actual_moves':set(),'vram_poses':set(),
                   'pixel_poses':set(),'screens':{},'frames':[]}
        for _ in range(5):
            x,y=self.read('wMenuCursorX')[0],self.read('wMenuCursorY')[0]
            if (x,y)==(1,1):break
            self.press('left' if x>1 else 'up',30)
        self.press('a',60);self.wait(lambda:self.move_menus>move_menus)
        for _ in range(6):
            cursor=self.read('wMenuCursorY')[0]-1
            if cursor==slot:break
            self.press('up' if cursor>slot else 'down',30)
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


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--expected-sha',required=True);parser.add_argument('--class',dest='class_name',choices=CLASSES)
    args=parser.parse_args();logging.disable(logging.CRITICAL);OUT.mkdir(parents=True,exist_ok=True)
    sha=digest((ROOT/'pokecrystal.gbc').read_bytes());assert sha==args.expected_sha
    sym=load_symbols();report={'rom_sha256':sha,'passed':False,'method':'Ordinary inputs only; read-only native VRAM/OAM/RGB555 and battery observation.',
          'ram_writes':False,'emulator_states_loaded':False,'user_battery_files_opened':False,'classes':{}}
    with tempfile.TemporaryDirectory(prefix='peon-v026-three-class-graphics-') as temp:
        for index,slug in enumerate(CLASSES):
            if args.class_name and slug!=args.class_name:continue
            rom=Path(temp)/(slug+'.gbc');shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
            s=GraphicsSession(rom,sym,index)
            try:
                s.fresh_class();s.advance(90);fresh=s.world_vram()
                previews=[u for u in s.uploads if u['kind']=='preview' and u['frame']==index]
                assert previews,'highlighted class preview never loaded native tiles'
                s.capture('fresh_class_native_world');walking=s.world_cycle();profile=s.profile();s.world_vram()
                # Locked map menu and a real room door must reload the selected
                # actor rather than the original Shaman default.
                s.press('select');s.advance(60);s.capture('map_menu_before_unlock');s.press('b');s.advance(120);s.world_vram()
                s.navigate((17,5),23);s.advance(90);s.world_vram();s.capture('class_inside_inn')
                s.navigate((5,7),14);s.advance(90);s.world_vram();s.capture('class_after_door_reload')
                cold=s.cold_graphics()
                s.talk_plain((10,10),'up');s.navigate((18,13));s.press('up',30);s.press('a',60)
                s.wait(lambda:s.phase=='battle',buttons=True);s.advance(60)
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
                    physical=s.cast_once(0,'physical_strike',(0,1,2));s.finish_battle();s.rest()
                assert not s.hook_errors,s.hook_errors
                back_checks=[u for u in s.uploads if u['kind']=='back' and u['protected_battle_regions_unchanged']]
                assert back_checks and {0,1,2}<={u['frame'] for u in back_checks},'missing protected native back uploads'
                report['classes'][slug]={'passed':True,'highlighted_class_preview':previews[-1],
                    'actual_preview_palette_and_framebuffer_checks':s.preview_checks,
                    'fresh_world_vram':fresh,'world_movement':walking,'character_profile':profile,
                    'map_menu_and_room_door_class_reload':True,'cold_save':cold,'actual_battle_casts':s.casts,
                    'all_native_back_uploads_protect_enemy_font_emblem_totem_pet_and_hud':True,
                    'back_helper_observations':back_checks,'native_upload_count':len(s.uploads),
                    'read_only_hook_errors':s.hook_errors,'native_asset_sha256':{k:digest(v) for k,v in s.art.items()}}
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
                    'actual_world_facings_seen':sorted(s.world_facings)},indent=2)+'\n')
                raise
            finally:s.p.stop(save=False)
    assert digest((ROOT/'pokecrystal.gbc').read_bytes())==sha,'source ROM changed during graphics QA'
    report['passed']=True
    destination=BASE/('validation.json' if not args.class_name else 'validation_'+args.class_name+'.json')
    destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'rom_sha256':sha,'passed':True,'classes':list(report['classes'])},indent=2))

if __name__=='__main__':main()
