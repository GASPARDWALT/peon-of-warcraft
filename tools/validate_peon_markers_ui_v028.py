#!/usr/bin/env python3
"""Ordinary class themes, decorative markers, real quests and warm UI checks.

The ROM and battery are private copies. No RAM writes, emulator states, CPU
substitution, flag fixtures or artificial quest progress are used.
"""
from collections import deque
from pathlib import Path
import argparse, hashlib, json, logging, shutil, tempfile

import numpy as np
from PIL import Image
from validate_peon_class_routes import ClassSession
from validate_peon_villages import MAPS, DIRECTIONS, load_symbols, warp_tiles
from validate_durotar_v022_quests import triggers

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/polish_v028/ui_markers'
THEMES = ((20,25,31), (31,20,18), (26,20,31))
CLASSES = ('shaman', 'warrior', 'warlock')
MAPS.update({25:('PeonValleyCrossroads',5,5),26:('PeonHanazuaCamp',5,5),
             27:('PeonSarkothBasin',5,5),28:('PeonCaveApproach',5,5),29:('PeonValleyExit',5,5)})


def digest(data): return hashlib.sha256(data).hexdigest()


def load_frozen_symbols(path):
    result = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and ':' in parts[0]:
            try:
                result[parts[1]] = tuple(int(n, 16) for n in parts[0].split(':'))
            except ValueError:
                pass
    return result


def decode(data):
    pixels = np.zeros((16,16), dtype=np.uint8)
    for n in range(4):
        for y in range(8):
            lo,hi = data[n*16+y*2:n*16+y*2+2]
            for x in range(8):
                pixels[n//2*8+y,n%2*8+x] = (lo>>(7-x)&1) | (hi>>(7-x)&1)<<1
    return pixels


class UISession(ClassSession):
    def __init__(self, rom, symbols):
        self.themes=[]; self.transitions=[]; self.marker_checks=[]; self.talks=[]
        self.hook_errors=[]; self.upload_stack=[]; self.uploads=[]
        self.monitor_transition=False; self.theme_cycle_done=False
        self.native_talks=[]
        super().__init__(rom,symbols,0)

    def write(self,*args,**kwargs):
        raise AssertionError('This validator permits no emulator RAM writes.')

    def safe(self,callback,value):
        try: callback(value)
        except Exception as error: self.hook_errors.append((callback.__name__,repr(error)))

    def open(self):
        super().open()
        self.p.hook_register(*self.sym['CheckFacingObject.standing'],
                             lambda _:self.safe(self.talk_found,None),None)
        for label in ('PeonLoadPlayerHUDGFX','PeonApplyMenuSkin'):
            self.p.hook_register(*self.sym[label],lambda label:self.safe(self.upload_start,label),label)
            bank,address=self.sym[label+'.done']
            self.p.hook_register(bank,address+4,lambda label:self.safe(self.upload_end,label),label)

    def regs(self):
        return {name:getattr(self.p.register_file,name) for name in ('A','F','B','C','D','E','HL','SP')}

    def upload_start(self,label):
        self.upload_stack.append({'label':label,'regs':self.regs(),
                                 'mode':self.read('hBGMapMode')[0],
                                 'vbk':self.p.memory[0xff4f]})

    def upload_end(self,label):
        before=self.upload_stack.pop()
        assert before['label']==label
        assert before['regs']==self.regs(),(label,'register/stack preservation')
        assert before['vbk']==self.p.memory[0xff4f],(label,'VBK changed')
        # Menu skin subsequently publishes attributes and intentionally leaves
        # mapmode1. Its upload-only mask restores before native publication.
        if label=='PeonLoadPlayerHUDGFX':
            assert before['mode']==self.read('hBGMapMode')[0],(label,'mapmode changed')
            if self.read('wMapTileset')==[37] and self.read('hCGB')!=[0]:
                assert bytes(self.p.memory[0,0x8600:0x86e0]) == (ROOT/'gfx/pack/peon_player_hud.2bpp').read_bytes()
        self.uploads.append({'label':label,'registers_and_stack_preserved':True,
                             'vram_bank_restored':True,'entry_mapmode':before['mode']})

    def talk_found(self,_):
        address=self.p.register_file.B*256+self.p.register_file.C
        self.native_talks.append({'sprite':self.p.memory[address],
                                 'map_object':self.p.memory[address+1]})

    def capture(self,name):
        if name=='master_class_description' and not self.theme_cycle_done:
            self.theme_cycle_done=True
            self.check_theme(0)
            for n in range(9):
                self.monitor_transition=True
                self.press('down',45)
                self.monitor_transition=False
                self.check_theme((n+1)%3)
            assert self.read('wMenuCursorY')==[0]
        folder=OUT/'runtime';folder.mkdir(parents=True,exist_ok=True)
        self.p.screen.image.save(folder/(name+'.png'))
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(folder/(name+'_4x.png'))
        print(name,self.map(),self.position(),flush=True)

    def press(self,key,frames=90):
        if not self.monitor_transition:
            super().press(key,frames)
        else:
            self.p.button(key,delay=4)
            for _ in range(frames):
                self.p.tick(1,True)
                bg=int.from_bytes(bytes(self.read('hBGMapAddress',2)),'little')
                visible=[self.p.memory[0,bg+y*32+x] for y in range(18) for x in range(20)]
                nonblank=sum(tile!=0x7f for tile in visible)
                assert nonblank>=100,('class transition published a blank panel',nonblank)
                self.transitions.append(nonblank)
        assert not self.hook_errors,self.hook_errors[-4:]

    def check_theme(self,index):
        self.p.tick(60,True)
        assert self.read('wMenuCursorY')==[index]
        attrs=self.read('wAttrmap',360)
        bg=int.from_bytes(bytes(self.read('hBGMapAddress',2)),'little')
        hardware=[self.p.memory[1,bg+y*32+x] for y in range(18) for x in range(20)]
        assert hardware==attrs,'class attributes were not published to VRAM'
        for y in range(18):
            for x in range(20):
                wanted=1 if y in (0,17) or x in (0,19) else 5 if y in (12,13) and x in (10,11) else 0
                assert attrs[y*20+x]&7==wanted,(index,x,y,attrs[y*20+x],wanted)
        assert any(value&8 for value in attrs),'name-only bank1 glyphs were lost'
        colours=[]
        body=[]
        encoded_body=self.read('wBGPals2',8)
        for j in range(0,8,2):
            value=encoded_body[j]|encoded_body[j+1]<<8
            body.append((value&31,value>>5&31,value>>10&31))
        assert body[:2]==[THEMES[index],THEMES[index]],(index,'space/glyph paper not uniformly tinted',body)
        encoded=self.read('wBGPals2',64)[40:48]
        for j in range(0,8,2):
            value=encoded[j]|encoded[j+1]<<8
            colours.append((value&31,value>>5&31,value>>10&31))
        assert colours==[THEMES[index],(18,11,6),(15,22,8),(1,1,1)],colours
        art=(ROOT/'gfx/peon_classes_v028'/CLASSES[index]/'overworld.bin').read_bytes()[:64]
        assert bytes(self.p.memory[0,0x9600:0x9640])==art
        actual=np.asarray(self.p.screen.image.convert('RGB'))>>3
        expected=np.asarray(colours,dtype=np.uint8)[decode(art)]
        assert np.array_equal(actual[96:112,80:96],expected),(index,'real preview pixels differ')
        assert tuple(actual[116,148])==THEMES[index],(index,'real backdrop pixel differs')
        self.themes.append({'class':CLASSES[index],'body_rgb555':THEMES[index],
                            'space_and_regular_glyph_paper_match':True,
                            'hardware_attributes_match':True,'preview_vram_and_rgb555_match':True,
                            'green_skin_and_leather_preserved':True,'name_bank1_preserved':True})
        self.capture('class_theme_'+CLASSES[index])

    def path(self,target):
        name,_,_=MAPS[self.map()]
        live=self.live_actors(name)
        occupied={a['xy'] for a in live if not a['sprite'].startswith('SPRITE_PEON_QUEST_')}
        live_scripts={a['script'] for a in live}
        danger={xy for xy,script in triggers(name).items() if script in live_scripts}
        warps=warp_tiles(name);start=self.position()
        queue=deque([(start,[])]);seen={start}
        while queue:
            (x,y),path=queue.popleft()
            if (x,y)==tuple(target):return path
            for key,dx,dy in DIRECTIONS:
                pos=(x+dx,y+dy)
                if pos in seen or pos in occupied or self.collision_at(*pos)=='WALL':continue
                if pos in warps and pos!=tuple(target):continue
                if pos in danger and pos!=tuple(target):continue
                seen.add(pos);queue.append((pos,path+[key]))
        raise AssertionError((name,'no safe path',start,target))

    def marker(self,index,slot,state,label):
        self.p.tick(90,True)
        wanted={'available_yellow':53,'active_gray':54,'complete_yellow':60}[state]
        assert self.read('wVariableSprites',16)[slot]==wanted
        runtime=self.read(f'wMap{index}ObjectStructID')[0]
        assert runtime<13,(label,'marker not allocated')
        row=self.read('wObjectStructs',13*40)[runtime*40:(runtime+1)*40]
        bank,base=(0 if row[2]&128 else 1),row[2]&127
        palette=5 if state=='active_gray' else 4
        assert row[6]&7==palette
        binary=(ROOT/f'gfx/sprites/peon_quest_{state}.2bpp').read_bytes()
        assert bytes(self.p.memory[bank,0x8000+base*16:0x8000+base*16+64])==binary
        native=np.asarray(Image.open(ROOT/f'references/generated/durotar_v022/quest_markers/{state}.png'))
        wanted_pixels=native[:,:,:3]>>3;mask=native[:,:,3]!=0
        for _ in range(60):
            hardware=list(self.p.memory[0xfe00:0xfea0])
            if hardware==self.read('wShadowOAM',160):break
            self.p.tick(1,True)
        assert hardware==self.read('wShadowOAM',160),'unfinished native OAM publication'
        actual=np.asarray(self.p.screen.image.convert('RGB'))>>3;parts=set()
        for j in range(0,160,4):
            y,x,tile,attr=hardware[j:j+4]
            if not base<=tile<base+4 or attr&7!=palette or attr>>3&1!=bank:continue
            px,py=x-8,y-16;tx,ty=(tile-base)%2*8,(tile-base)//2*8
            if not 0<=px<=152 or not 0<=py<=136:continue
            opaque=mask[ty:ty+8,tx:tx+8]
            assert np.array_equal(actual[py:py+8,px:px+8][opaque],wanted_pixels[ty:ty+8,tx:tx+8][opaque]),(label,'marker RGB555 differs')
            parts.add(tile-base)
        assert parts=={0,1,2,3},(label,'marker clipped')
        self.marker_checks.append({'label':label,'state':state,'vram_and_oam_rgb555_match':True})
        self.capture(label)

    def talk_real(self,npc,stand,face,label):
        self.navigate(stand)
        before=self.position();self.press(face,30)
        assert self.position()==before,(label,'real NPC stopped blocking')
        offset=len(self.native_talks);self.press('a',120)
        assert self.read('wScriptMode')!=[0],(label,'no dialogue')
        matches=self.native_talks[offset:]
        assert matches and matches[-1]['map_object']==npc,(label,'talk intercepted by marker',matches)
        assert matches[-1]['sprite']<253
        self.capture(label);self.close_dialogue();self.p.tick(90,True)
        self.talks.append({'label':label,'stand':stand,'real_map_object':npc,'native_facing_object':matches[-1],
                           'npc_collision_preserved':True})

    def cross_marker(self,xy,label):
        x,y=xy;entered=[]
        # The real giver occupies the south cell and must stay solid. The
        # floating icon cell is reachable from north, east and west.
        for stand,key,back in (((x,y-1),'down','up'),((x-1,y),'right','left'),((x+1,y),'left','right')):
            self.navigate(stand);self.walk(key)
            assert self.position()==xy,(label,'marker still blocks',stand,key)
            self.capture(label+'_from_'+key);self.walk(back);entered.append(key)
        return {'label':label,'entered_from':entered,'real_npc_south_cell_still_solid':True}


def main():
    global OUT
    parser=argparse.ArgumentParser()
    parser.add_argument('--expected-rom-sha256',required=True)
    parser.add_argument('--rom',type=Path,default=ROOT/'pokecrystal.gbc')
    parser.add_argument('--symbols',type=Path,default=ROOT/'pokecrystal.sym')
    parser.add_argument('--output',type=Path,default=OUT)
    args=parser.parse_args();OUT=args.output.resolve();OUT.mkdir(parents=True,exist_ok=True)
    assert ROOT/'references/generated/polish_v028' in OUT.parents or OUT==ROOT/'references/generated/polish_v028'
    logging.disable(logging.CRITICAL)
    assert digest(args.rom.read_bytes())==args.expected_rom_sha256
    report={'rom_sha256':args.expected_rom_sha256,'symbols_sha256':digest(args.symbols.read_bytes()),
            'passed':False,'normal_buttons_only':True,
            'ram_edits':False,'emulator_states_loaded':False,'marker_crossings':[]}
    with tempfile.TemporaryDirectory(prefix='peon-v028-ui-markers-') as temp:
        rom=Path(temp)/'normal.gbc';shutil.copyfile(args.rom,rom)
        s=UISession(rom,load_frozen_symbols(args.symbols))
        try:
            s.fresh_class();s.navigate((10,10))
            s.marker(2,13,'available_yellow','gornek_available')
            report['marker_crossings'].append(s.cross_marker((10,8),'gornek_available_pass_through'))
            s.talk_real(1,(10,8),'down','gornek_accept_from_marker_cell')
            assert s.event('EVENT_PEON_QUEST_ACCEPTED')
            s.navigate((10,10));s.marker(2,13,'active_gray','gornek_active_gray')
            for stand,face in (((10,8),'down'),((9,9),'right'),((11,9),'left'),((10,10),'up')):
                s.talk_real(1,stand,face,'gornek_active_talk_'+face)
            report['marker_crossings'].append(s.cross_marker((10,8),'gornek_gray_pass_through'))
            s.navigate((10,10));s.press('start');s.press('a');s.press('b');s.press('b');s.p.tick(90,True)
            s.marker(2,13,'active_gray','gornek_gray_after_character_menu')
            s.navigate((18,13));s.press('up',30);s.press('a')
            fight=s.fight('ordinary_boar','EVENT_PEON_QUEST_DONE');assert fight['outcome']==0
            report['ordinary_boar_victory']=fight
            s.navigate((10,10));s.marker(2,13,'complete_yellow','gornek_turn_in_yellow')
            report['marker_crossings'].append(s.cross_marker((10,8),'gornek_ready_pass_through'))
            before=s.money();s.talk_real(1,(10,8),'down','gornek_reward_from_marker_cell')
            assert s.event('EVENT_PEON_CUTTING_TURNED_IN') and s.money()==before+100
            s.navigate((8,16));s.marker(9,14,'available_yellow','lazy_available')
            report['marker_crossings'].append(s.cross_marker((8,14),'lazy_available_pass_through'))
            s.talk_real(7,(8,14),'down','foreman_accept_from_marker_cell')
            assert s.event('EVENT_PEON_LAZY_ACCEPTED')
            s.navigate((8,16));s.marker(9,14,'active_gray','lazy_active_gray')
            s.talk_real(8,(5,17),'up','wake_actual_sleeping_peon')
            assert s.event('EVENT_PEON_LAZY_AWAKE')
            s.navigate((8,16));s.marker(9,14,'complete_yellow','lazy_turn_in_yellow')
            before=s.money();s.talk_real(7,(8,14),'down','foreman_reward_from_marker_cell')
            assert s.event('EVENT_PEON_LAZY_DONE') and s.money()==before+100
            assert s.read('wMap9ObjectStructID')==[255]
            paid=s.money();s.talk_real(7,(8,14),'down','foreman_no_second_reward')
            assert s.money()==paid and s.read('wMap9ObjectStructID')==[255]
            s.navigate((20,10),expected_map=15);s.navigate((8,11))
            s.marker(5,13,'available_yellow','galgar_available')
            report['marker_crossings'].append(s.cross_marker((8,9),'galgar_available_pass_through'))
            s.talk_real(1,(8,9),'down','galgar_accept_from_marker_cell')
            assert s.event('EVENT_PEON_CACTUS_ACCEPTED')
            s.navigate((8,11));s.marker(5,13,'active_gray','galgar_active_gray')
            for x,y,name in ((7,7,'EVENT_PEON_CACTUS_1'),(23,9,'EVENT_PEON_CACTUS_2'),(9,17,'EVENT_PEON_CACTUS_3')):
                choices=[]
                for face,dx,dy in DIRECTIONS:
                    stand=(x-dx,y-dy)
                    try:path=s.path(stand)
                    except AssertionError:continue
                    choices.append((len(path),stand,face))
                _,stand,face=min(choices);s.navigate(stand);s.press(face,30);s.press('a',120);s.close_dialogue()
                assert s.event(name),name
                s.capture('actual_harvest_'+name.lower())
            s.navigate((8,11));s.marker(5,13,'complete_yellow','galgar_turn_in_yellow')
            report['marker_crossings'].append(s.cross_marker((8,9),'galgar_ready_pass_through'))
            before=s.money();s.talk_real(1,(8,9),'down','galgar_reward_from_marker_cell')
            assert s.event('EVENT_PEON_CACTUS_DONE') and s.money()==before+50
            assert s.read('wMap5ObjectStructID')==[255]
            assert not s.hook_errors,s.hook_errors
            report.update({'passed':True,'themes':s.themes,'native_transition_frames_without_blank_panel':len(s.transitions),
                           'marker_checks':s.marker_checks,'native_talk_checks':s.talks,'upload_preservation_checks':s.uploads,
                           'single_lazy_reward_and_hidden_marker':True,'real_three_cactus_pickups':True})
        finally:s.p.stop(save=False)
    assert digest(args.rom.read_bytes())==args.expected_rom_sha256,'ROM changed during validation'
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('themes','native_talk_checks','upload_preservation_checks')},indent=2))


if __name__=='__main__':main()
