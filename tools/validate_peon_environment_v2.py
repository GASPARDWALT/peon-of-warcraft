#!/usr/bin/env python3
"""Bounded native environment-v2 checks through actual buttons only.

The dedicated compile-guard ROM runs from an isolated copy. No user battery,
memory write, CPU-call substitution, emulator state or gameplay migration is
used. A JSON layout contract supplies the test maps and deliberate probes.
"""
import argparse
from collections import deque
import hashlib
import json
import logging
from pathlib import Path
import shutil
import tempfile

import numpy as np
from PIL import Image
from pyboy import PyBoy

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_OUT=ROOT/'references/generated/map_tests/runtime'
DIRECTIONS={'left':(-1,0),'right':(1,0),'up':(0,-1),'down':(0,1)}


def digest(data):return hashlib.sha256(data).hexdigest()


def decode_tile(data):
    result=np.zeros((8,8),dtype=np.uint8)
    for y in range(8):
        low,high=data[y*2:y*2+2]
        for x in range(8):
            bit=7-x;result[y,x]=((low>>bit)&1)|(((high>>bit)&1)<<1)
    return result


def palette_source(path):
    path=ROOT/path
    if path.suffix=='.pal':
        import re
        words=[]
        for line in path.read_text().splitlines():
            match=re.search(r'\bRGB\s+([^;]+)',line)
            if not match:continue
            numbers=[int(v.strip()) for v in match[1].split(',')]
            assert len(numbers)%3==0
            for n in range(0,len(numbers),3):
                r,g,b=numbers[n:n+3];assert max(r,g,b)<=31
                words.append(r|(g<<5)|(b<<10))
        data=b''.join(w.to_bytes(2,'little') for w in words)
    else:data=path.read_bytes()
    assert len(data)==64,('Expected eight native RGB555 palettes',path,len(data))
    return data


def prepare_contract(source):
    """Keep the importer contract separate from this reproducible play route."""
    contract=json.loads(json.dumps(source));names={m['name']:m['number'] for m in contract['maps']}
    for m in contract['maps']:
        m['header_prefix']=m.get('header_prefix',m.get('headerprefix'))
        m['warp_cells']=[t['doorxy'] for t in contract.get('transitions',[]) if t['map']==m['name']]
    contract['spawn']['map']=names.get(contract['spawn']['map'],contract['spawn']['map'])
    if 'actions' in contract:return contract
    actions=[]
    def walk(xy,label):actions.append({'type':'walk','xy':xy,'label':label})
    def interact(name):
        for p in contract['interactions']:
            if p['map']!=name:continue
            action={'type':'interact','map':names[name],'from':p['fromxy'],'direction':p['direction'],'label':p['kind']}
            if p['kind']=='chest':
                action|={'item':18,'quantity_delta':1};actions.append(action)
                actions.append(action|{'label':'chest_second_inspection','quantity_delta':0})
            else:actions.append(action)
    def blocked(name):
        for p in contract['obstacles']:
            if p['map']==name:actions.append({'type':'blocked','map':names[name],'from':p['fromxy'],'direction':p['direction'],'label':p['kind']})
    def warp(origin,destination,xy,label,direction):
        t=next(t for t in contract['transitions'] if t['map']==origin and t['to']==destination and t['doorxy']==xy)
        actions.append({'type':'warp','xy':xy,'to_map':names[destination],'landing':t['landingxy'],
                        'label':label,'direction':direction})
    test,annex,cave='PeonEnvironmentTest','PeonEnvironmentTestAnnex','PeonEnvironmentTestCave'
    interact(test);blocked(test)
    walk([10,6],'native_ground_paths_north');walk([12,12],'native_crossroad')
    warp(test,annex,[21,9],'native_annex_entry','right')
    blocked(annex);interact(annex)
    fire=contract['fire']
    actions.append({'type':'fire','map':names[fire['map']],'from':[11,14],
                    'bank':fire['vram_bank'],'address':int(fire['vram_address'],0),
                    'source':fire['path'],'frame_bytes':fire['framebytes'],'observe_frames':240})
    walk([12,6],'native_hut_whole_facade');walk([10,8],'native_hut_front')
    warp(annex,cave,[10,7],'native_hut_inside','up')
    blocked(cave);walk([12,10],'native_ground_transitions')
    joined=contract.get('joined_transition')
    if joined:
        assert joined['map']==cave
        walk(joined['walk_start'],'native_joined_soil_start')
        actions.append({'type':'joined_transition','from':joined['walk_start'],'to':joined['walk_end'],
                        'source_blocks':joined['blocks'],'source_order':joined['source_order'],
                        'label':'native_joined_soil_walk'})
        walk(joined['view_waypoint'],'native_joined_soil_whole_strip')
    warp(cave,annex,[6,17],'native_hut_return','down')
    walk([20,6],'native_cave_whole_facade');walk([18,8],'native_cave_front')
    warp(annex,cave,[18,7],'native_cave_inside','up')
    warp(cave,annex,[18,17],'native_cave_return','down')
    warp(annex,test,[2,9],'native_test_return','left')
    contract['actions']=actions
    return contract


def symbols(path):
    out={}
    for row in Path(path).read_text().splitlines():
        f=row.split()
        if len(f)==2 and ':' in f[0]:
            try:out[f[1]]=tuple(int(n,16) for n in f[0].split(':'))
            except ValueError:pass
    return out


def header(data):
    assert len(data)==2*1024*1024,'Unexpected ROM size'
    assert data[0x143]&0x80 and data[0x147]==0x10 and data[0x148]==6 and data[0x149]==3
    checksum=0
    for b in data[0x134:0x14d]:checksum=(checksum-b-1)&255
    assert checksum==data[0x14d],'Header checksum invalid'
    assert (sum(data)-data[0x14e]-data[0x14f])&65535==int.from_bytes(data[0x14e:0x150],'big'),'Global checksum invalid'
    return {'rom_bytes':len(data),'cgb_flag':data[0x143],'mbc3_rtc_ram_battery_header':True,
            'declared_ram_bytes':32768,'checksums_valid':True,'physical_cartridge_tested':False,
            'rtc_clock_and_battery_persistence_tested':False}


class EnvironmentSession:
    def __init__(self,rom,sym,contract,out):
        self.rom=Path(rom);self.rom_bytes=self.rom.read_bytes();self.sym=sym;self.contract=contract
        self.out=Path(out);self.out.mkdir(parents=True,exist_ok=True)
        self.maps={int(m['number']):m for m in contract['maps']}
        self.phase='boot';self.trace=[];self.new_games=0;self.frames=0;self.warp_landings=[]
        self.p=PyBoy(str(rom),window='null',sound_emulated=False,log_level='ERROR')
        self.p.set_emulation_speed(0)
        for label,phase in [('PeonTitleScreen.wait','title'),('PeonCharacterSelect.input','select'),
                            ('HandleMapTimeAndJoypad','world')]:
            if label in sym:self.p.hook_register(*sym[label],self.set_phase,phase)
        self.p.hook_register(*sym['NewGame'],lambda _:setattr(self,'new_games',self.new_games+1),None)
        if 'HandleNewMap' in sym:
            self.p.hook_register(*sym['HandleNewMap'],lambda _:self.warp_landings.append(
                {'frame':self.p.frame_count,'map':self.map(),'xy':list(self.xy())}),None)

    def set_phase(self,phase):
        if phase!=self.phase:self.trace.append({'frame':self.p.frame_count,'phase':phase})
        self.phase=phase

    def read(self,name,length=1):
        if not length:return []
        bank,address=self.sym[name]
        return list(self.p.memory[address:address+length] if address>=0xe000
                    else self.p.memory[bank,address:address+length])

    def map(self):return self.read('wMapNumber')[0]
    def xy(self):return tuple(self.read('wXCoord')+self.read('wYCoord'))
    def step(self,frames):self.p.tick(frames,True);self.frames+=frames

    def tap(self,key,settle=90,held=4):
        self.p.button_press(key);self.step(held);self.p.button_release(key);self.step(settle)

    def capture(self,label):
        self.p.screen.image.save(self.out/(label+'.png'))
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(self.out/(label+'_4x.png'))
        print(label,self.map(),self.xy(),self.read('wScriptMode'),flush=True)

    def boot(self):
        self.step(300);assert self.phase=='title';self.capture('native_title')
        self.tap('start',120)
        if self.phase=='select':
            for _ in range(4):
                if self.read('wMenuCursorY')==[1]:break
                self.tap('down',30)
            assert self.read('wMenuCursorY')==[1]
            self.tap('a',240)
        start=self.contract['spawn']
        for _ in range(120):
            if self.map()==start['map'] and self.read('wScriptMode')==[0]:break
            self.step(10)
        assert self.map()==start['map'] and self.xy()==tuple(start['xy'])
        assert self.new_games==1 and self.read('wBattleMode')==[0]
        self.step(120);self.capture('test_map_start')

    def rom_slice(self,bank,address,length):
        offset=address if bank==0 else bank*0x4000+address-0x4000
        return self.rom_bytes[offset:offset+length]

    def collision(self,x,y):
        m=self.maps[self.map()];w,h=m['width_blocks'],m['height_blocks']
        if not(0<=x<2*w and 0<=y<2*h):return 7
        bank,address=self.sym['wOverworldMapBlocks']
        block=self.p.memory[bank,address+(y//2+3)*(w+6)+x//2+3]
        if block==0:return 7
        b,a=self.read('wTilesetCollisionBank')[0],int.from_bytes(bytes(self.read('wTilesetCollisionAddress',2)),'little')
        return self.rom_slice(b,a+block*4+y%2*2+x%2,1)[0]

    def occupied(self):
        # Actual live actors, rather than immutable source coordinates.
        actors=self.read('wObjectStructs',13*40)
        return {(a[16]-4,a[17]-4) for n in range(1,13)
                for a in [actors[n*40:(n+1)*40]] if a[0] and not a[4]&1}

    def warps(self):
        m=self.maps[self.map()]
        return {tuple(p) for p in m.get('warp_cells',[])}

    def path(self,target):
        target=tuple(target);start=self.xy();occupied=self.occupied();warps=self.warps()
        queue=deque([(start,[])]);seen={start}
        while queue:
            (x,y),steps=queue.popleft()
            if (x,y)==target:return steps
            for key,(dx,dy) in DIRECTIONS.items():
                p=(x+dx,y+dy)
                if p in seen or p in occupied or self.collision(*p)==7 or p in warps and p!=target:continue
                seen.add(p);queue.append((p,steps+[key]))
        raise AssertionError(('No native walkable path',self.map(),start,target))

    def walk(self,key):
        before=self.xy();oldmap=self.map()
        for _ in range(8):
            self.tap(key,40)
            if self.xy()!=before:break
        assert self.map()==oldmap and sum(abs(a-b) for a,b in zip(before,self.xy()))==1,('Ordinary walk failed',key,before,self.xy(),oldmap,self.map())

    def navigate(self,target,expected_map=None,direction=None):
        target=tuple(target)
        # Native warps trigger by entering the square. A reciprocal arrival
        # already stands on that square, so walk off before returning.
        if expected_map is not None and self.xy()==target:
            for key,(dx,dy) in DIRECTIONS.items():
                adjacent=(target[0]+dx,target[1]+dy)
                if self.collision(*adjacent)!=7 and adjacent not in self.occupied() and adjacent not in self.warps():
                    self.walk(key);break
            else:raise AssertionError(('No ordinary step off arrival warp',self.map(),target))
        if expected_map is not None and direction is not None:
            dx,dy=DIRECTIONS[direction]
            self.navigate((target[0]-dx,target[1]-dy));steps=[direction]
        else:steps=self.path(target)
        for n,key in enumerate(steps):
            if expected_map is not None and n==len(steps)-1:self.tap(key,180,held=16)
            else:self.walk(key)
        if expected_map is None:assert self.xy()==target
        else:
            # Crystal's directional carpet warps act on another outward
            # press while standing on the carpet. DOOR/CAVE warp on entry.
            if self.map()!=expected_map and self.xy()==target and direction:
                for _ in range(3):
                    self.tap(direction,180,held=8)
                    if self.map()==expected_map:break
            assert self.map()==expected_map,('Warp target mismatch',target,expected_map,self.map(),self.xy())
        assert self.read('wBattleMode')==[0]

    def palette(self,label,index):
        data=self.read(label,64)[index*8:index*8+8]
        words=[data[i]|data[i+1]<<8 for i in range(0,8,2)]
        return [[w&31,w>>5&31,w>>10&31] for w in words]

    def source_proof(self,label):
        m=self.maps[self.map()];gfx=(ROOT/m['gfx']).read_bytes();assert len(gfx)==192*16
        dynamic=set(m.get('dynamic_tiles',[0,1,2,3]))
        for n in range(192):
            if n in dynamic:continue
            bank,tile=(0,n) if n<96 else (1,n-96)
            assert bytes(self.p.memory[bank,0x9000+tile*16:0x9000+(tile+1)*16])==gfx[n*16:(n+1)*16],('Loaded tile differs from source',m['name'],n)
        if m.get('header_prefix'):
            prefix=m['header_prefix']
            for field,suffix in [('wTilesetBank','GFX'),('wTilesetBlocksBank','Meta'),('wTilesetCollisionBank','Coll')]:
                b,a=self.sym[prefix+suffix];assert self.read(field,3)==[b,a&255,a>>8]
            assert self.read('wTilesetPalettes',2)==list(self.sym[prefix+'PalMap'][1].to_bytes(2,'little'))
            for source,suffix in [('metatiles','Meta'),('palmap','PalMap')]:
                data=(ROOT/m[source]).read_bytes();b,a=self.sym[prefix+suffix]
                assert self.rom_slice(b,a,len(data))==data,('Compiled map table differs from supplied conversion',m['name'],source)
        blocks=(ROOT/m['map_blocks']).read_bytes();w,h=m['width_blocks'],m['height_blocks']
        assert len(blocks)==w*h
        bank,address=self.sym['wOverworldMapBlocks']
        loaded=bytes(self.p.memory[bank,address+(y+3)*(w+6)+x+3] for y in range(h) for x in range(w))
        assert loaded==blocks,('Native loaded map layout differs from importer',m['name'])
        if m.get('palettes'):
            raw=palette_source(m['palettes'])
            # Slot 7 belongs to the existing native interface. Opening and
            # closing dialogue deliberately changes its paper/accent theme.
            assert bytes(self.read('wBGPals2',56))==raw[:56],('Native environment RGB555 palette table differs',m['name'])
        ppu=self.ppu_proof(m)
        self.capture(label)
        return {'map':m['name'],'source_gfx_sha256':digest(gfx),'static_native_tiles_exact':192-len(dynamic),
                'source_rgb555_palettes_exact':bool(m.get('palettes')),'native_loaded_map_blocks_exact':len(blocks),
                'source_environment_palette_indices_compared':list(range(7)),
                'interface_palette7_current_RGB555':self.palette('wBGPals2',7),
                'source_metatile_and_palmap_ROM_tables_exact':bool(m.get('header_prefix')),**ppu}

    def visible_bg(self):
        lcdc=self.p.memory[0xff40];base=0x9c00 if lcdc&8 else 0x9800
        scx,scy=self.p.memory[0xff43],self.p.memory[0xff42]
        assert scx%8==scy%8==0,('Map capture is mid-scroll',scx,scy)
        positions=[base+((scy//8+y)%32)*32+(scx//8+x)%32 for y in range(18) for x in range(20)]
        return [(self.p.memory[0,p],self.p.memory[1,p]) for p in positions],base,(scx,scy),lcdc

    def object_window_mask(self,lcdc):
        mask=np.zeros((144,160),dtype=bool)
        if lcdc&2:
            height=16 if lcdc&4 else 8
            for n in range(40):
                y,x,_,_=self.p.memory[0xfe00+n*4:0xfe04+n*4]
                left,top=x-8,y-16
                if left<160 and top<144 and left+8>0 and top+height>0:
                    mask[max(0,top):min(144,top+height),max(0,left):min(160,left+8)]=True
        if lcdc&0x20:
            x,y=self.p.memory[0xff4b]-7,self.p.memory[0xff4a]
            if x<160 and y<144:mask[max(0,y):,max(0,x):]=True
        return mask

    def ppu_proof(self,m):
        palmap=(ROOT/m['palmap']).read_bytes();assert len(palmap)==128
        priority=(ROOT/m['priority']).read_bytes() if m.get('priority') else bytes(32)
        cells,base,scroll,lcdc=self.visible_bg();dynamic=set(m.get('dynamic_tiles',[0,1,2,3]))
        mask=self.object_window_mask(lcdc);actual=np.array(self.p.screen.image.convert('RGB'))>>3
        palettes=np.array([self.palette('wBGPals2',n) for n in range(8)],dtype=np.uint8)
        compared=pixels=0;errors=[]
        for i,(physical,attr) in enumerate(cells):
            logical=physical|((attr&8)<<4)
            if not (logical<96 or 128<=logical<224):continue
            expected=(palmap[logical//2]>>(4*(logical%2)))&15
            if priority[logical//8]&(0x80>>(logical%8)):expected|=0x80
            if attr!=expected:errors.append((i%20,i//20,logical,attr,expected))
            compared+=1
            if logical in dynamic:continue
            bank=attr>>3&1
            address=0x8000+physical*16 if lcdc&0x10 else 0x9000+(physical if physical<128 else physical-256)*16
            indices=decode_tile(bytes(self.p.memory[bank,address:address+16]))
            if attr&0x20:indices=np.fliplr(indices)
            if attr&0x40:indices=np.flipud(indices)
            y,x=divmod(i,20);y*=8;x*=8
            wanted=palettes[attr&7][indices];valid=~mask[y:y+8,x:x+8]
            assert np.array_equal(actual[y:y+8,x:x+8][valid],wanted[valid]),('Native LCD RGB555 background differs',m['name'],x,y,physical,attr)
            pixels+=int(valid.sum())
        assert not errors,('Actual CGB BG palette/bank attributes differ from source',m['name'],errors[:20])
        assert compared>0 and pixels>0
        return {'actual_hardware_bg_map_base':base,'scroll_xy':list(scroll),
                'visible_native_tile_attributes_exact':compared,'static_LCD_RGB555_pixels_exact':pixels,
                'object_and_window_overlay_pixels_excluded':int(mask.sum()),
                'source_packed_palmap_sha256':digest(palmap)}

    def blocked_probe(self,p):
        assert self.map()==p['map'];self.navigate(p['from']);before=self.xy()
        dx,dy=DIRECTIONS[p['direction']];assert self.collision(before[0]+dx,before[1]+dy)==7
        self.p.button_press(p['direction']);self.step(60);self.p.button_release(p['direction']);self.step(40)
        assert self.xy()==before and self.map()==p['map'],('Solid obstacle crossed',p,before,self.xy())
        self.capture('blocked_'+p['label'])
        return {'kind':p['label'],'from':list(before),'direction':p['direction'],'coordinate_unchanged':True}

    def item_quantity(self,item):
        values=self.read('wItems',self.read('wNumItems')[0]*2)
        return sum(values[i+1] for i in range(0,len(values),2) if values[i]==item)

    def interact(self,p):
        assert self.map()==p['map'];self.navigate(p['from']);before=self.xy()
        self.tap(p['direction'],30);assert self.xy()==before
        item=p.get('item');before_items=self.item_quantity(item) if item else None
        self.tap('a',120);assert self.read('wScriptMode')!=[0]
        self.capture('interaction_'+p['label'])
        for _ in range(40):
            if self.read('wScriptMode')==[0]:break
            self.tap('a',60)
        assert self.read('wScriptMode')==[0]
        if item:assert self.item_quantity(item)==before_items+p.get('quantity_delta',1)
        return {'label':p['label'],'native_dialogue_opened_and_closed':True,'item':item,
                'quantity_before':before_items,'quantity_after':self.item_quantity(item) if item else None}

    def fire_probe(self,p):
        assert self.map()==p['map'];self.navigate(p['from']);self.step(60)
        source=(ROOT/p['source']).read_bytes();size=p['frame_bytes'];frames=[source[n:n+size] for n in range(0,len(source),size)]
        assert len(frames)==3 and len(set(frames))>=2
        seen={};lcd_seen={};bank,address=p['bank'],p['address'];firecells=[];incremental_upload_frames=0
        visible,_,_,lcdc=self.visible_bg()
        firecells=[(i,physical,attr) for i,(physical,attr) in enumerate(visible) if physical<4 and not attr&8]
        assert {physical for _,physical,_ in firecells}=={0,1,2,3},('Complete campfire is not visible',firecells)
        mask=self.object_window_mask(lcdc);palettes=np.array([self.palette('wBGPals2',n) for n in range(8)])
        for _ in range(p.get('observe_frames',240)):
            self.step(1);actual=bytes(self.p.memory[bank,address:address+size])
            # Crystal uploads one 8x8 tile per animation command. Between
            # commands the four-tile packet can contain two source phases.
            for tile in range(size//16):
                chunk=actual[tile*16:(tile+1)*16]
                assert any(chunk==f[tile*16:(tile+1)*16] for f in frames),('Fire uses unrelated tile graphics',tile,digest(chunk))
            if actual in frames:
                index=frames.index(actual)
                if actual not in seen:
                    seen[actual]=self.p.screen.image.copy();self.capture('fire_phase_'+str(index))
            else:incremental_upload_frames+=1
            # The LCD can show the preceding VBlank upload; compare it with
            # source states independently instead of assuming CPU/PPU timing.
            screen=np.array(self.p.screen.image.convert('RGB'))>>3
            for frame in set(frames):
                matched=True;pixels=0
                for i,physical,attr in firecells:
                    y,x=divmod(i,20);y*=8;x*=8
                    valid=~mask[y:y+8,x:x+8]
                    wanted=palettes[attr&7][decode_tile(frame[physical*16:(physical+1)*16])]
                    if not np.array_equal(screen[y:y+8,x:x+8][valid],wanted[valid]):matched=False;break
                    pixels+=int(valid.sum())
                if matched and pixels and frame not in lcd_seen:
                    lcd_seen[frame]=pixels;self.capture('fire_LCD_source_state_'+str(frames.index(frame)))
        assert set(seen)==set(frames),('Missing actual animated fire states',len(seen),len(set(frames)))
        assert set(lcd_seen)==set(frames),('Missing actual LCD campfire states',len(lcd_seen),len(set(frames)))
        return {'source_phase_slots':len(frames),'distinct_native_vram_states_observed':len(seen),
                'distinct_actual_LCD_source_states_observed':len(lcd_seen),'source_exact_LCD_fire_pixels':list(lcd_seen.values()),
                'incremental_native_tile_upload_frames':incremental_upload_frames,
                'source_phase_equivalence_groups':[[i for i,f in enumerate(frames) if f==frame] for frame in seen],
                'source_fire_packet_sha256':digest(source),
                'observed_frames':p.get('observe_frames',240),'native_bank':bank,'native_address':address}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--rom',type=Path,required=True)
    parser.add_argument('--sym',type=Path,required=True);parser.add_argument('--expected-sha',required=True)
    parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--out',type=Path,default=DEFAULT_OUT)
    args=parser.parse_args();logging.disable(logging.CRITICAL)
    original=args.rom.read_bytes();assert digest(original)==args.expected_sha
    contract=prepare_contract(json.loads(args.contract.read_text()));args.out.mkdir(parents=True,exist_ok=True)
    report={'passed':False,'rom_sha256':digest(original),'symbols_sha256':digest(args.sym.read_bytes()),
            'contract_sha256':digest(args.contract.read_bytes()),'header':header(original),
            'ordinary_buttons_only':True,'ram_writes':False,'emulator_states_loaded':False,
            'user_battery_files_opened':False,'scope':'Dedicated environment prototype only; no classes/combat/full-save suite.'}
    with tempfile.TemporaryDirectory(prefix='peon-environment-v2-native-') as temp:
        path=Path(temp)/'test.gbc';shutil.copyfile(args.rom,path)
        s=EnvironmentSession(path,symbols(args.sym),contract,args.out)
        try:
            s.boot();report['start']=s.source_proof('native_environment_start')
            report['actions']=[]
            for action in contract['actions']:
                kind=action['type']
                if kind=='walk':
                    s.navigate(action['xy']);s.step(60);result=s.source_proof(action['label'])
                elif kind=='joined_transition':
                    start,end=tuple(action['from']),tuple(action['to'])
                    assert s.xy()==start and start[1]==end[1] and end[0]>start[0]
                    route=[list(start)]
                    for x in range(start[0]+1,end[0]+1):
                        assert s.collision(x,start[1])!=7
                        s.walk('right');assert s.xy()==(x,start[1]);route.append(list(s.xy()))
                    s.step(60);result=s.source_proof(action['label'])|{
                        'actual_button_walk_coordinates':route,'source_block_boundaries_crossed':[
                            list(p) for p in route[1:] if p[0]%2==0],
                        'source_blocks':action['source_blocks'],'source_order':action['source_order']}
                elif kind=='blocked':result=s.blocked_probe(action)
                elif kind=='warp':
                    before=s.map();old_landings=len(s.warp_landings)
                    s.navigate(action['xy'],action['to_map'],action.get('direction'));s.step(120)
                    if action.get('landing'):
                        raw=tuple(action['landing'])
                        observed=s.warp_landings[old_landings:]
                        assert any(e['map']==action['to_map'] and tuple(e['xy'])==raw for e in observed),('Native warp event landing differs',action,observed)
                        # An outward key at a carpet can also advance one
                        # native step out of a destination door after loading.
                        allowed={raw}
                        if s.collision(*raw) in (0x71,0x7b):allowed.add((raw[0],raw[1]+1))
                        assert s.xy() in allowed,('Unexpected settled warp position',raw,s.xy(),allowed)
                    result=s.source_proof(action['label'])|{'from_map':before,'to_map':s.map(),'ordinary_warp':True,
                        'native_event_landing_xy':action.get('landing'),'settled_xy':list(s.xy())}
                elif kind=='interact':result=s.interact(action)
                elif kind=='fire':result=s.fire_probe(action)
                else:raise ValueError('Unknown QA action: '+kind)
                report['actions'].append({'type':kind,**result})
            report['frames']=s.frames;report['native_new_game_calls']=s.new_games
            report['trace']=s.trace;report['passed']=True
        except BaseException as error:
            s.capture('first_failure');report['failure']=repr(error);report['map']=s.map();report['xy']=s.xy()
            raise
        finally:
            s.p.stop(save=False)
            (args.out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    assert args.rom.read_bytes()==original,'Source ROM changed during environment QA'
    print(json.dumps({'passed':True,'rom_sha256':report['rom_sha256'],'actions':len(report['actions'])},indent=2))


if __name__=='__main__':main()
