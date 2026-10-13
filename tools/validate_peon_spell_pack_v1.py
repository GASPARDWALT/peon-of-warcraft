#!/usr/bin/env python3
"""Observe eight native Shaman sparring cases through ordinary controls.

The compiled fixture, rather than the emulator, prepares its party/opponent.
All hooks are read-only observers. Each case uses a fresh private ROM copy;
no RAM writes, save states, user batteries or CPU-call substitutions are used.
"""
import argparse
from collections import Counter
import hashlib
import json
import logging
from pathlib import Path
import shutil
import tempfile

import numpy as np
from PIL import Image
from pyboy import PyBoy

from validate_peon_environment_v2 import symbols, header, decode_tile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'references/generated/spell_tests/runtime'
CASES=[('lightning_bolt',0,1),('rockbiter',0,2),('earth_shock',0,3),('earth_totem',0,None),
       ('lightning_bolt',1,0),('rockbiter',1,0),('earth_shock',1,0),('earth_totem',1,None)]


def digest(data):return hashlib.sha256(data).hexdigest()


def rgb555(data):
    words=[int.from_bytes(data[n:n+2],'little') for n in range(0,len(data),2)]
    return np.array([[w&31,w>>5&31,w>>10&31] for w in words],dtype=np.uint8)


class SpellSession:
    def __init__(self,rom,sym,manifest,out,case):
        self.rom=Path(rom);self.data=self.rom.read_bytes();self.sym=sym;self.manifest=manifest
        self.out=Path(out);self.out.mkdir(parents=True,exist_ok=True);self.case=case
        self.phase='boot';self.ui='none';self.context=None;self.menus=0;self.frames=0
        self.moves=[];self.records=[];self.observations={};self.snapshots=[];self.errors=[]
        self.p=PyBoy(str(rom),window='null',sound_emulated=False,log_level='ERROR');self.p.set_emulation_speed(0)
        self.max_oam=0;self.max_scanline=0;self.observed_oam_frames=0;self.watch=False
        self.assets={};self.packets={p['ability']:p for p in manifest['packets']}
        for p in manifest['packets']:
            p['_raw']=(ROOT/p['2bpp']).read_bytes();p['_pal']=(ROOT/p['palette_file']).read_bytes()
            for a in p['assets']:
                a['_packet']=p;self.assets[sym[a['oam_label']][1]]=a
        self.register('PeonTitleScreen.wait',lambda _:setattr(self,'phase','title'))
        self.register('PeonCharacterSelect.input',lambda _:setattr(self,'phase','select'))
        self.register('HandleMapTimeAndJoypad',lambda _:setattr(self,'phase','world'))
        self.register('PeonSpellTestChooseScenario.Input',lambda _:setattr(self,'ui','cases'))
        self.register('LoadBattleMenu',self.menu)
        self.register('StaticMenuJoypad',self.static_menu)
        self.register('MoveSelectionScreen',lambda _:setattr(self,'ui','moves'))
        self.register('DoTurn',lambda _:setattr(self,'ui','action'))
        self.register('BattleCommand_UsedMoveText',self.used_move)
        self.register('PeonRenderSpellV1OAM',self.render)
        for label,phase in [('PeonBags','bags_drawing'),('PeonInventory.draw','inventory_drawing'),
                            ('PeonInventory.input','inventory'),('PeonInventory.used_battle_item','action')]:
            self.register(label,lambda _,phase=phase:setattr(self,'ui',phase))
        self.register('PeonInterfaceWait',lambda _:setattr(self,'ui','bags') if self.ui=='bags_drawing' else None)

    def register(self,label,callback):
        assert label in self.sym,('Missing native observer symbol',label)
        def safe(_):
            try:callback(None)
            except Exception as error:self.errors.append({'hook':label,'error':repr(error)})
        self.p.hook_register(*self.sym[label],safe,None)

    def read(self,label,length=1):
        if not length:return []
        bank,address=self.sym[label]
        return list(self.p.memory[address:address+length] if address>=0xe000 else self.p.memory[bank,address:address+length])

    def word(self,label):return int.from_bytes(bytes(self.read(label,2)),'big')

    def menu(self,_):self.ui='main_drawing';self.context='main';self.menus+=1
    def static_menu(self,_):
        if self.context=='main':self.ui='main';self.context=None
    def used_move(self,_):
        turn=self.read('hBattleTurn')[0]
        self.moves.append({'turn':turn,'move':self.read('wCurEnemyMove' if turn else 'wCurPlayerMove')[0]})

    def rom_bytes(self,label,length):
        bank,address=self.sym[label];offset=address if bank==0 else bank*0x4000+address-0x4000
        return self.data[offset:offset+length]

    def render(self,_):
        pointer=self.p.register_file.HL
        assert pointer in self.assets,('Unknown imported OAM orientation pointer',pointer)
        asset=self.assets[pointer];packet=asset['_packet'];base=49+self.read('wBattleAnimTempTileID')[0]
        rows=self.rom_bytes(asset['oam_label'],asset['oam_count']*4)
        x=(self.read('wBattleAnimTempXCoord')[0]+self.read('wBattleAnimTempXOffset')[0])&255
        y=(self.read('wBattleAnimTempYCoord')[0]+self.read('wBattleAnimTempYOffset')[0])&255
        flags=self.read('wBattleAnimTempOAMFlags')[0]&128
        if packet['ability']=='earth_totem' and asset['orientation']=='enemy_front':
            # All 32 source rows, including the initial eight-pixel rise,
            # stay above the retained player-name row beginning at y56.
            bottom=y-16+asset['canvas'][1]//2
            assert bottom<=56,('Enemy placement canvas overlaps retained player name',y,bottom)
        expected=[[(rows[n]+y)&255,(rows[n+1]+x)&255,(rows[n+2]+base)&255,(rows[n+3]&0x17)|flags]
                  for n in range(0,len(rows),4)]
        assert bytes(self.p.memory[0,0x8000+base*16:0x8000+base*16+len(packet['_raw'])])==packet['_raw'],('Imported spell VRAM differs',packet['ability'])
        assert bytes(self.read('wOBPals2',64)[32:56])==packet['_pal'],('Imported visible OBJ palette differs',packet['ability'])
        self.records.append({'frame':self.frames,'asset':asset,'expected':expected,'base':base,'xy':[x,y],
                             'turn':self.read('hBattleTurn')[0]})
        if len(self.records)>40:self.records=self.records[-40:]

    def step(self,frames):
        for _ in range(frames):
            self.p.tick(1,True);self.frames+=1
            if self.watch:self.observe()
        assert not self.errors,self.errors[-3:]

    def tap(self,key,settle=40,held=4):
        self.p.button_press(key);self.step(held);self.p.button_release(key);self.step(settle)

    def capture(self,label):
        self.p.screen.image.save(self.out/(label+'.png'))
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(self.out/(label+'_4x.png'))
        print(self.case,label,self.ui,flush=True)

    def wait(self,predicate,buttons=False,limit=6000):
        for n in range(limit):
            if predicate():
                for key in ('a','b','up','down','left','right'):self.p.button_release(key)
                self.step(12)
                if predicate():return
            if buttons and n%40==0:self.p.button('a',delay=4)
            self.step(1)
        raise AssertionError(('Native control wait timed out',self.ui,self.read('wBattleMode'),self.read('wMenuCursorX'),self.read('wMenuCursorY'),hex(self.p.register_file.PC)))

    def boot_case(self):
        self.step(300);assert self.phase=='title';self.tap('start',120)
        if self.phase=='select':
            for _ in range(4):
                if self.read('wMenuCursorY')==[1]:break
                self.tap('down',30)
            assert self.read('wMenuCursorY')==[1];self.tap('a',240)
        self.wait(lambda:self.read('wMapNumber')==[30] and self.read('wScriptMode')==[0])
        assert self.read('wXCoord')==[12] and self.read('wYCoord')==[17]
        assert self.read('wPartyMon1Level')==[8] and self.read('wPartyMon1Moves',4)==[1,84,14,9]
        for _ in range(3):
            self.tap('left',45)
            if self.read('wXCoord')==[11]:break
        assert self.read('wXCoord')==[11]
        self.tap('left',30);self.tap('a',90);self.wait(lambda:self.ui=='cases')
        for _ in range(self.case-1):self.tap('down',30)
        assert self.read('wMenuCursorY')==[self.case-1];self.capture('native_case_selected')
        self.watch=True;self.tap('a',60);self.wait(lambda:self.ui=='main',buttons=True)
        assert self.read('wDebugFlags')==[0x80|(self.case<<2)] and self.read('wBattleMode')[0]
        assert self.word('wEnemyMonHP')==200 and self.word('wEnemyMonMaxHP')==200
        assert self.read('wPeonRockbiterCharge')==[0] and self.read('wPeonLightningShieldCharges')==[0], 'Native battle began with phantom spell buffs'
        self.capture('native_battle_idle')

    def snapshot(self):
        return {'player_hp':self.word('wBattleMonHP'),'enemy_hp':self.word('wEnemyMonHP'),
                'mana':self.word('wPartyMon1CaughtData'),'rockbiter_charge':self.read('wPeonRockbiterCharge')[0],
                'lightning_shield_charges':self.read('wPeonLightningShieldCharges')[0],
                'earth_totem_active':self.read('wPeonEarthTotemActive')[0],
                'enemy_attack_stage':self.read('wEnemyStatLevels')[0],
                'totem_count':self.item_quantity(0x94),'native_used_move_count':len(self.moves)}

    def item_quantity(self,item):
        items=self.read('wItems',self.read('wNumItems')[0]*2)
        return sum(items[n+1] for n in range(0,len(items),2) if items[n]==item)

    def protected(self):
        return {name:digest(bytes(self.p.memory[bank,start:end])) for name,bank,start,end in [
            ('enemy_front',0,0x9000,0x9310),('player_back',0,0x9310,0x9550),
            ('bank0_font',0,0x8800,0x9000),('bank1_rank',1,0x8800,0x8860),('bank1_sidebar',1,0x8a90,0x8ad0)]}

    def palette_restore(self,baseline):
        actual=bytes(self.read('wBGPals2',64))
        for index in (0,1,4,5,6,7):
            assert actual[index*8:(index+1)*8]==baseline[index*8:(index+1)*8],('Spell leaked into native BG palette',index)
        for index,field in [(2,'wEnemyHPPal'),(3,'wPlayerHPPal')]:
            hpcolors=self.rom_bytes('HPBarPals',12);choice=self.read(field)[0];assert choice<3
            assert actual[index*8+2:index*8+6]==hpcolors[choice*4:choice*4+4],('Native HP palette no longer matches HP state',index,choice)
        return True

    def foreground(self):
        lcdc=self.p.memory[0xff40];base=0x9c00 if lcdc&8 else 0x9800
        assert self.p.memory[0xff42]==self.p.memory[0xff43]==0
        screen=np.array(self.p.screen.image.convert('RGB'))>>3
        palettes=np.array([rgb555(bytes(self.read('wBGPals2',64)[n*8:(n+1)*8])) for n in range(8)])
        regions=[(2,6,6,6),(12,0,7,7),(10,4,2,3)]+[(0,y,1,1) for y in (5,6,8,9)]
        pixels=0
        for x0,y0,width,height in regions:
            for ty in range(y0,y0+height):
                for tx in range(x0,x0+width):
                    position=base+ty*32+tx;tile,attr=self.p.memory[0,position],self.p.memory[1,position]
                    address=0x9000+(tile if tile<128 else tile-256)*16
                    indices=decode_tile(bytes(self.p.memory[attr>>3&1,address:address+16]))
                    if attr&32:indices=np.fliplr(indices)
                    if attr&64:indices=np.flipud(indices)
                    mask=indices>0;desired=palettes[attr&7][indices]
                    assert np.array_equal(screen[ty*8:ty*8+8,tx*8:tx*8+8][mask],desired[mask]),('Native actor/rank/sidebar foreground changed on LCD',tx,ty)
                    pixels+=int(mask.sum())
        return {'actor_rank_sidebar_LCD_foreground_pixels_exact':pixels,
                'transparent_BG_paper_can_show_priority_totem':True}

    def bold_font_proof(self):
        # Bags legitimately rebuilds the transient name cache. Validate its
        # current glyphs against the immutable font, rather than old cache IDs.
        count=self.read('wPeonBoldGlyphCount')[0];assert count<=23
        assert self.read('wPeonBoldGlyphOverflow')==[0]
        codes=self.read('wPeonBoldGlyphCodes',count);font=(ROOT/'gfx/font/peon_bold_v026.1bpp').read_bytes()
        for n,code in enumerate(codes):
            data=font[(code-0x80)*8:(code-0x80+1)*8]
            assert len(data)==8
            wanted=bytes(v for v in data for _ in range(2))
            assert bytes(self.p.memory[1,0x8920+n*16:0x8930+n*16])==wanted,('Current native bold glyph cache corrupted',n,code)
        return {'current_native_bold_cache_matches_font':True,'current_glyph_count':count,
                'cache_rebuilt_by_native_menus_is_not_treated_as_corruption':True}

    def fight(self,slot):
        self.wait(lambda:self.ui=='main');menus=self.menus
        for _ in range(5):
            x,y=self.read('wMenuCursorX')[0],self.read('wMenuCursorY')[0]
            if (x,y)==(1,1):break
            self.tap('left' if x>1 else 'up',30)
        self.tap('a',50);self.wait(lambda:self.ui=='moves')
        for _ in range(8):
            y=self.read('wMenuCursorY')[0]-1
            if y==slot:break
            self.tap('up' if y>slot else 'down',30)
        assert self.read('wMenuCursorY')==[slot+1]
        self.capture('fight_selected_'+str(slot));self.ui='action';self.tap('a',30)
        self.wait(lambda:self.read('wBattleMode')==[0] or self.ui=='main' and self.menus>menus,buttons=True)
        assert self.read('wBattleMode')[0] and self.word('wBattleMonHP')>0, 'Native sparring ended before the requested restoration check'

    def bags(self):
        self.wait(lambda:self.ui=='main')
        for _ in range(5):
            x,y=self.read('wMenuCursorX')[0],self.read('wMenuCursorY')[0]
            if (x,y)==(1,2):break
            self.tap('left' if x>1 else 'down',30)
        self.tap('a',40);self.wait(lambda:self.ui=='bags');self.tap('a',40);self.wait(lambda:self.ui=='inventory')
        items=self.read('wItems',self.read('wNumItems')[0]*2)[::2];assert 0x94 in items
        for _ in range(items.index(0x94)):self.tap('right',35)
        assert self.read('wNamedObjectIndex')==[0x94]
        icon=next(i for i in self.manifest['icons'] if i['ability']=='earth_totem')
        data=(ROOT/icon['2bpp']).read_bytes()
        assert bytes(self.p.memory[0,0x9280:0x92c0])==data
        assert bytes(self.read('wBGPals2',64)[40:48])==(ROOT/icon['palette_file']).read_bytes()
        self.capture('bags_supplied_totem_icon')

    def use_totem(self):
        self.bags();menus=self.menus;self.ui='action';self.tap('a',30)
        self.wait(lambda:self.ui=='main' and self.menus>menus,buttons=True)

    def observe(self):
        current=[list(self.p.memory[0xfe00+n:0xfe04+n]) for n in range(0,160,4)]
        if self.read('wBattleMode')[0]:
            active=[e for e in current if 0<e[0]<160]
            height=16 if self.p.memory[0xff40]&4 else 8
            maximum=max((sum(e[0]-16<=y<e[0]-16+height for e in active) for y in range(144)),default=0)
            self.max_oam=max(self.max_oam,len(active));self.max_scanline=max(self.max_scanline,maximum);self.observed_oam_frames+=1
            assert len(active)<=40 and maximum<=10,('Hardware OAM budget exceeded',len(active),maximum)
        snapshots=[(current,np.array([rgb555(bytes(self.read('wOBPals2',64)[n*8:(n+1)*8])) for n in range(8)]))]+self.snapshots[-1:]
        screen=np.array(self.p.screen.image.convert('RGB'))>>3
        for record in self.records:
            if self.frames-record['frame']>5:continue
            asset=record['asset'];label=asset['oam_label'];expected=record['expected']
            observation=self.observations.setdefault(label,{'VRAM_exact':True,'palette_exact':True,'OAM_frames':0,'LCD_frames':0,
                'matched_LCD_pixels':0,'positions':set(),'source_alpha_canvas_exact':False,'peak':None,'frames':[]})
            for oam,palettes in snapshots:
                starts=[n for n in range(41-len(expected)) if oam[n:n+len(expected)]==expected]
                if not starts:continue
                observation['OAM_frames']+=1;observation['positions'].add(tuple(record['xy']))
                count=0;matched=True
                for j,(y,x,tile,attr) in enumerate(expected):
                    y-=16;x-=8
                    if not(0<=x<=152 and 0<=y<=136):continue
                    indices=decode_tile(record['asset']['_packet']['_raw'][(tile-record['base'])*16:(tile-record['base']+1)*16])
                    mask=indices>0
                    # Earlier hardware objects own overlapping nonzero pixels.
                    for e in oam[:starts[0]+j]:
                        py,px,pt,pa=e;py-=16;px-=8
                        left,top,right,bottom=max(x,px),max(y,py),min(x+8,px+8),min(y+8,py+8)
                        if left>=right or top>=bottom:continue
                        earlier=decode_tile(bytes(self.p.memory[pa>>3&1,0x8000+pt*16:0x8010+pt*16]))
                        if pa&32:earlier=np.fliplr(earlier)
                        if pa&64:earlier=np.flipud(earlier)
                        mask[top-y:bottom-y,left-x:right-x]&=earlier[top-py:bottom-py,left-px:right-px]==0
                    wanted=palettes[attr&7][indices]
                    if not np.array_equal(screen[y:y+8,x:x+8][mask],wanted[mask]):matched=False;break
                    count+=int(mask.sum())
                if matched and count:
                    observation['LCD_frames']+=1;observation['matched_LCD_pixels']=max(observation['matched_LCD_pixels'],count)
                    if observation['peak'] is None:observation['peak']=self.p.screen.image.copy()
                    if len(observation['frames'])<70:observation['frames'].append(self.p.screen.image.copy())
        self.snapshots=snapshots[:1]

    def source_alpha(self,asset):
        width,height=asset['canvas'];indices=np.zeros((height,width),dtype=np.uint8)
        for tile in asset['tile_offset_records']:
            if tile.get('tile_index') is None:continue
            index=tile['tile_index'];x,y=tile['x'],tile['y']
            indices[y:y+8,x:x+8]=decode_tile(asset['_packet']['_raw'][index*16:(index+1)*16])
        source=np.array(Image.open(ROOT/asset['source']).convert('RGBA'))
        assert source.shape[:2]==(height,width) and np.array_equal(indices>0,source[:,:,3]>0)
        return True

    def finish_observations(self,ability,turn):
        expected=[a for a in self.packets[ability]['assets'] if a['orientation']==('enemy_front' if turn else 'player_back') or a['orientation']=='target']
        result=[]
        for asset in expected:
            label=asset['oam_label'];o=self.observations.get(label)
            assert o and o['OAM_frames'] and o['LCD_frames'],('Missing native imported OAM/LCD orientation',self.case,label,o)
            o['source_alpha_canvas_exact']=self.source_alpha(asset)
            image=o['peak'];image.save(self.out/(asset['orientation']+'_actual.png'))
            image.resize((640,576),Image.Resampling.NEAREST).save(self.out/(asset['orientation']+'_actual_4x.png'))
            frames=[im.resize((480,432),Image.Resampling.NEAREST) for im in o['frames']]
            if frames:frames[0].save(self.out/(asset['orientation']+'_native.gif'),save_all=True,append_images=frames[1:],duration=17,loop=0)
            metrics={k:v for k,v in o.items() if k not in ('peak','frames','positions')}
            # Each LCD frame can match several adjacent OAM snapshots/rows.
            # These are corroborating observations, not extra motion frames.
            metrics['matching_native_OAM_observations']=metrics.pop('OAM_frames')
            metrics['matching_source_LCD_observations']=metrics.pop('LCD_frames')
            result.append({'source':asset['source'],'source_sha256':asset['source_sha256'],'orientation':asset['orientation'],
                           'canvas':asset['canvas'],**metrics,
                           'distinct_actual_OAM_anchor_positions':len(o['positions'])})
        return result

    def persistent(self,label):
        m=self.manifest['persistent_earth_totem'];data=(ROOT/m['2bpp']).read_bytes()
        assert self.read('wPeonEarthTotemActive')==[1]
        assert bytes(self.p.memory[1,0x8ad0:0x8bd0])==data
        rows=self.rom_bytes(m['oam_label'],m['oam_count']*4)
        expected=[[(rows[n]+56)&255,(rows[n+1]+72)&255,rows[n+2]+0xad,rows[n+3]] for n in range(0,len(rows),4)]
        actual=[list(self.p.memory[0xfe60+n:0xfe64+n]) for n in range(0,len(rows),4)]
        assert actual==expected,('Persistent full source OAM layer differs',label,actual,expected)
        packet=self.packets['earth_totem'];assert bytes(self.read('wOBPals2',64)[32:56])==packet['_pal']
        # Behind-BG priority preserves foreground glyphs and actor silhouettes.
        # Compare source OBJ pixels only where hardware BG color index is zero.
        palettes=np.array([rgb555(bytes(self.read('wOBPals2',64)[n*8:(n+1)*8])) for n in range(8)])
        screen=np.array(self.p.screen.image.convert('RGB'))>>3;lcdc=self.p.memory[0xff40];bgbase=0x9c00 if lcdc&8 else 0x9800
        compared=0
        for y,x,tile,attr in expected:
            y-=16;x-=8;indices=decode_tile(data[(tile-0xad)*16:(tile-0xad+1)*16]);mask=indices>0
            for py in range(8):
                for px in range(8):
                    position=bgbase+((y+py)//8)*32+(x+px)//8
                    bgid,bga=self.p.memory[0,position],self.p.memory[1,position]
                    address=0x9000+(bgid if bgid<128 else bgid-256)*16
                    bg=decode_tile(bytes(self.p.memory[bga>>3&1,address:address+16]))
                    if bg[(y+py)%8,(x+px)%8]:mask[py,px]=False
            assert np.array_equal(screen[y:y+8,x:x+8][mask],palettes[attr&7][indices][mask]),('Persistent actual source LCD pixels differ',label)
            compared+=int(mask.sum())
        assert compared>0;foreground=self.foreground();self.capture(label)
        return {'bank1_16_tiles_exact':True,'13_sparse_source_OAM_entries_exact':True,
                'OBJ_palettes4_5_6_exact':True,'visible_source_LCD_pixels_exact':compared,
                'background_foreground_occludes_layer_by_native_priority':True,**foreground}

    def run(self):
        self.boot_case();ability,turn,slot=CASES[self.case-1]
        before=self.snapshot();protected=self.protected();bgpal=bytes(self.read('wBGPals2',64))
        if self.case==4:self.use_totem()
        elif self.case!=8:self.fight(slot)
        after=self.snapshot();assert self.protected()==protected,('Imported spell damaged actor/font VRAM',self.case,self.protected(),protected)
        self.palette_restore(bgpal)
        assert after['lightning_shield_charges']==0
        if self.case!=2:assert after['rockbiter_charge']==0
        if self.case in (1,2,3):
            cost={1:15,2:25,3:30}[self.case];assert after['mana']==before['mana']-cost
            assert {'turn':0,'move':{1:84,2:14,3:9}[self.case]} in self.moves
            if self.case!=2:assert after['enemy_hp']<before['enemy_hp']
        elif self.case in (5,6,7):
            assert after['mana']==before['mana']
            assert {'turn':1,'move':{5:84,6:14,7:9}[self.case]} in self.moves
            if self.case==6:assert after['enemy_attack_stage']==before['enemy_attack_stage']+2
            else:assert after['player_hp']<before['player_hp']
        extra={}
        if self.case==2:
            assert after['rockbiter_charge']==1
            self.fight(0);consumed=self.snapshot();assert consumed['rockbiter_charge']==0 and consumed['enemy_hp']<after['enemy_hp']
            assert consumed['mana']==after['mana'];extra['next_real_physical_strike_consumed_charge']=True
        if self.case==4:
            assert after['earth_totem_active']==1 and after['totem_count']==before['totem_count'] and after['mana']==before['mana']
            extra['persistent_after_placement']=self.persistent('persistent_after_placement')
            self.fight(1);extra['persistent_after_imported_lightning']=self.persistent('persistent_after_lightning')
            self.fight(0);extra['persistent_after_stock_physical']=self.persistent('persistent_after_stock_physical')
            self.bags();self.tap('b',40);self.tap('b',40);self.wait(lambda:self.ui=='main')
            extra['persistent_after_bags_return']=self.persistent('persistent_after_bags_return')
            assert self.protected()==protected,'Totem/menu restore damaged actor/font VRAM'
        self.palette_restore(bgpal);foreground=self.foreground()
        self.capture('native_restored_idle');font_proof=self.bold_font_proof()
        return {'case':self.case,'ability':ability,'caster':'enemy' if turn else 'player',
                'enemy_totem_visual_preview_only':self.case==8,'before':before,'after':after,
                'source_rendering':self.finish_observations(ability,turn),
                'actor_and_font_VRAM_restored':True,'native_BG_palettes_restored':True,
                'bold_font_cache':font_proof,
                **foreground,
                'OAM_frames_observed':self.observed_oam_frames,'max_active_OAM_entries':self.max_oam,
                'max_entries_per_scanline_including_X_hidden':self.max_scanline,
                'level_glow_observed':False,'level_glow_reason':'Native sparring grants no EXP; no level fixture injected.',**extra}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--rom',type=Path,required=True);parser.add_argument('--sym',type=Path,required=True)
    parser.add_argument('--expected-sha',required=True);parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--cases',default='1,2,3,4,5,6,7,8');args=parser.parse_args();logging.disable(logging.CRITICAL)
    original=args.rom.read_bytes();assert digest(original)==args.expected_sha
    manifest=json.loads((ROOT/'references/generated/spell_tests/import_manifest.json').read_text())
    report={'passed':False,'rom_sha256':digest(original),'symbols_sha256':digest(args.sym.read_bytes()),'header':header(original),
        'ordinary_inputs_only':True,'RAM_writes':False,'emulator_states_loaded':False,'user_batteries_opened':False,
        'fixture_prepared_by_native_ROM_not_emulator':True,'cases':[],
        'other_three_spell_icons':'Prepared converted assets; no live UI binding claimed.',
        'enemy_totem_item_mechanic':'Not implemented; case8 validates its explicitly labelled native visual preview.'}
    args.out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='peon-native-spell-pack-v1-') as temp:
        for case in [int(c) for c in args.cases.split(',')]:
            assert 1<=case<=8
            path=Path(temp)/('case_'+str(case)+'.gbc');shutil.copyfile(args.rom,path)
            s=SpellSession(path,symbols(args.sym),manifest,args.out/('case_'+str(case)),case)
            try:report['cases'].append(s.run())
            except BaseException as error:
                s.capture('first_failure');report['failure']=repr(error);report['failed_case']=case
                report['last_used_moves']=s.moves;raise
            finally:
                s.p.stop(save=False);(args.out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    report['passed']=True;(args.out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    assert args.rom.read_bytes()==original
    print(json.dumps({'passed':True,'rom_sha256':report['rom_sha256'],'cases':len(report['cases'])},indent=2))


if __name__=='__main__':main()
