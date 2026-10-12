#!/usr/bin/env python3
"""Native regular/name-weight typography and cache lifecycle validation."""
import argparse
import hashlib
import json
import logging
from pathlib import Path
import shutil
import tempfile
from contextlib import contextmanager
import sys
import numpy as np
from PIL import Image

from validate_peon_class_potions import PotionSession
from validate_peon_combat_lifecycle import symbols_from
from validate_peon_atlas_player_objectives import AtlasSession as OldAtlas
from validate_peon_deep_ui import text_encoding
import build_peon_readable_font as encoding
import run_peon_v023_validation as adapter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'references/generated/visual_polish_v026/font'
REGULAR=(ROOT/'gfx/font/peon_regular_v026.1bpp').read_bytes()
BOLD=(ROOT/'gfx/font/peon_bold_v026.1bpp').read_bytes()

@contextmanager
def redirected_retained_outputs():
    saved=[]
    for module in adapter.local_dependencies(sys.modules[__name__]):
        for name in ('OUT','OUTPUT'):
            if hasattr(module,name):
                saved.append((module,name,getattr(module,name)))
                setattr(module,name,OUT)
    try:yield
    finally:
        for module,name,value in reversed(saved):setattr(module,name,value)

def pair(raw): return bytes(value for byte in raw for value in (byte,byte))

def actual_world_graphics(session):
    snapshot=OldAtlas.restored_world(session)
    # Native GetUsedSprite skips walking uploads for bank0 allocations.
    # The historical helper treated their nonexistent steps as $8800 font
    # ownership; only actual bank1 walking ranges belong to these actors.
    snapshot['allocated_sprite_graphics']=[
        (identity,tile,standing,None if tile&128 else walking)
        for identity,tile,standing,walking in snapshot['allocated_sprite_graphics']]
    return snapshot

def assert_world_restored(before,after):
    for field in before:
        if field=='terrain':
            # Only the two legal native animated flame tiles may differ.
            assert before[field][0][32:]==after[field][0][32:] and before[field][1]==after[field][1]
        else:assert before[field]==after[field],('World graphics not restored after map',field)

def source_checks(symbols):
    baseline=symbols_from(Path('/tmp/peon_v026_baseline/pokecrystal.sym'))
    oldram={name:location for name,location in baseline.items() if location[1]>=0xa000}
    changed={name:(old,symbols.get(name)) for name,old in oldram.items() if symbols.get(name)!=old}
    assert not changed, ('Existing RAM symbol addresses changed',list(changed.items())[:20])
    assert symbols['wPeonTextStyle']==(0,0xcfd8)
    assert symbols['wPeonBoldGlyphOverflow']==(0,0xcff1)
    assert len(REGULAR)==len(BOLD)==1024 and BOLD==bytes(value|value>>1 for value in REGULAR)
    plain=Image.open(ROOT/'gfx/font/peon_regular_v026.png').convert('L')
    bold=Image.open(ROOT/'gfx/font/peon_bold_v026.png').convert('L')
    assert encoding.encode_1bpp(plain)==REGULAR and encoding.encode_1bpp(bold)==BOLD
    codes=encoding.encoding()
    for group in (('I','l','1','i'),('O','o','0')):
        assert len({plain.crop(encoding.tile_box(codes[ch])).tobytes() for ch in group})==len(group)
    return {'existing_ram_symbols_preserved':len(oldram),'regular_and_bold_128_fixed_cells':True,
            'bold_is_exact_one_pixel_horizontal_expansion':True,'ambiguous_glyphs_distinct':True,
            'fixed_runtime_wram_range':['$cfd8','$cff1'],
            'font_cache_vram_ranges':{'world':['bank1 $9690','bank1 $97ff'],
                                      'battle':['bank1 $8920','bank1 $8a8f']}}

class FontSession(PotionSession):
    def __init__(self,rom,symbols):
        self.glyph_checks=[];self.class_capture=None
        self.overflow_entries=[];self.overflows=[]
        self.scrolls=0;self.enemy_pose_font_checks=0
        self.enemy_animation_commands=set();self.enemy_animation_cache_checks=0
        self.paired_publications=0;self.publication_errors=[]
        self.typing_watch=False;self.partial_typing=None
        super().__init__(rom,symbols)

    def open(self):
        super().open()
        self.p.hook_register(*self.sym['PeonClassSelect.draw'],self.class_drawing,None)
        self.p.hook_register(*self.sym['PeonPlaceStyledGlyph.full'],self.cache_full,None)
        self.p.hook_register(*self.sym['TextScroll'],lambda _:setattr(self,'scrolls',self.scrolls+1),None)
        self.p.hook_register(*self.sym['PeonAnimateEnemyAttack.done'],self.enemy_pose_done,None)
        self.p.hook_register(*self.sym['PokeAnim_ConvertAndApplyBitmask'],self.enemy_animation_frame,None)
        self.p.hook_register(*self.sym['PeonCharacterSelect.input'],self.character_select_ready,None)
        self.p.hook_register(*self.sym['PeonPublishTextCellAttribute.done'],self.published_pair,None)
        self.cold_preview_pending=False
        self.cold_preview=None

    def published_pair(self,_):
        address=self.p.register_file.HL
        base=int.from_bytes(bytes(self.read('hBGMapAddress',2)),'little')
        y,x=divmod(address-base,32)
        if not(0<=x<20 and 0<=y<18):
            self.publication_errors.append(('Native publication outside current BG map',hex(address),hex(base)))
            return
        tile=self.read('wTilemap',360)[y*20+x]
        attr=self.read('wAttrmap',360)[y*20+x]
        actual=(self.p.memory[0,address],self.p.memory[1,address])
        if actual!=(tile,attr):
            self.publication_errors.append(('Hardware glyph/attribute pair differs immediately after publication',x,y,(tile,attr),actual))
        self.paired_publications+=1

    def character_select_ready(self,_):
        if self.read('wSaveFileExists')==[1] and not self.cold_preview:
            self.cold_preview_pending=True

    def class_ready(self,_):
        if self.class_capture:
            self.class_capture=False
            # Actual menu has completed WaitBGMap before reaching input.
            self.check_pixels('class_select_names_and_regular_description',range(4,15))
            self.capture(self.class_name+'_class_select_typography')

    def class_drawing(self,_):
        self.class_menu_drawn=True

    def press(self,key,frames=90):
        if self.typing_watch and not self.partial_typing:
            self.p.button(key,delay=8)
            for _ in range(frames):
                self.p.tick(1,True)
                base,_=self.cache_base(); count=self.read('wPeonBoldGlyphCount')[0]
                tiles=self.read('wTilemap',360);attrs=self.read('wAttrmap',360)
                visible=sum(bool(attrs[y*20+x]&8 and base<=tiles[y*20+x]<base+count)
                            for y in (14,16) for x in range(1,19))
                if not self.partial_typing and 5<=visible<10 and self.read('wScriptMode')[0] and not self.read('wBattleMode')[0]:
                    self.partial_typing=self.check_pixels('partial_name_during_actual_typing',[14,16])
                    self.capture(self.class_name+'_partial_name_during_actual_typing')
                    self.typing_watch=False
        else:super().press(key,frames)
        if getattr(self,'class_menu_drawn',False) and self.class_capture:
            self.p.tick(60,True)
            self.class_ready(None)
        if self.cold_preview_pending and not self.cold_preview:
            self.cold_preview_pending=False
            self.p.tick(60,True)
            self.cold_preview=self.check_pixels('cold_battery_character_name_preview',[4,5])
            assert self.cold_preview['cells']['bold']>=9
            self.capture(self.class_name+'_cold_saved_character_name_preview')
            self.cold_preview_pending=False

    def cache_full(self,_):
        _,address=self.cache_base()
        self.overflow_entries.append(bytes(self.p.memory[1,address:address+23*16]))

    def cache_base(self):
        return (0x92,0x8920) if self.read('wBattleMode')[0] else (0x69,0x9690)

    def enemy_pose_done(self,_):
        if self.read('wBattleMode')[0] and self.read('wPeonBoldGlyphCount')[0]:
            self.cache()
            self.enemy_pose_font_checks+=1

    def enemy_animation_frame(self,_):
        if self.read('wBattleMode')[0] and self.read('wPeonBoldGlyphCount')[0]:
            self.cache()
            self.enemy_animation_commands.add(self.read('wPokeAnimCommand')[0])
            self.enemy_animation_cache_checks+=1

    def queue_text_fixture(self,text,label):
        """Labeled private RAM text, interpreted by unmodified native scripts."""
        assert self.read('wScriptMode')==[0] and not self.read('wBattleMode')[0]
        assert len(text)<=76
        _,text_address=self.sym['wStringBuffer1']
        _,script_address=self.sym['wStringBuffer5']
        self.write('wStringBuffer1',text)
        self.write('wStringBuffer5',[0x47,0x4c,text_address&255,text_address>>8,0x54,0x49,0x91])
        self.write('wScriptBank',[self.sym['TheDen_MapScripts'][0]])
        self.write('wScriptPos',[script_address&255,script_address>>8])
        self.write('wScriptStackSize',[0]);self.write('wScriptRunning',[1]);self.write('wScriptMode',[1])
        for _ in range(400):
            self.p.tick(4,True)
            position=int.from_bytes(bytes(self.read('wScriptPos',2)),'little')
            if position==script_address+5 and self.read('wScriptMode')[0]:break
            if _%20==19:self.press('a',4)
        else:raise AssertionError(('Native private text fixture did not reach waitbutton',label))
        self.p.tick(12,True)
        row=self.check_pixels(label,[14,16],allow_overflow=True)
        self.capture(label)
        return row

    def finish_text_fixture(self):
        for _ in range(20):
            self.press('a',30)
            if self.read('wScriptMode')==[0]:return
        raise AssertionError('Private text fixture left input frozen')

    def capture(self,label):
        self.p.screen.image.save(OUT/(label+'.png'))
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(OUT/(label+'_4x.png'))
        print(label,self.phase,self.map(),self.position(),flush=True)

    def cache(self):
        count=self.read('wPeonBoldGlyphCount')[0]
        assert 0<=count<=23
        codes=self.read('wPeonBoldGlyphCodes',count) if count else []
        _,address=self.cache_base()
        assert len(set(codes))==len(codes)
        for index,code in enumerate(codes):
            actual=bytes(self.p.memory[1,address+index*16:address+(index+1)*16])
            assert actual==pair(BOLD[(code-128)*8:(code-127)*8]), ('Cached bold glyph bytes differ',index,code)
        return codes

    def decoded(self,y,x=0,length=20):
        codes=self.cache(); tiles=self.read('wTilemap',360);attrs=self.read('wAttrmap',360)
        base,_=self.cache_base()
        result=[]
        for i in range(y*20+x,y*20+x+length):
            tile=tiles[i]
            if attrs[i]&8 and base<=tile<base+len(codes):tile=codes[tile-base]
            result.append(tile)
        return result

    def check_pixels(self,label,rows=None,allow_overflow=False):
        assert not self.publication_errors, self.publication_errors[:3]
        assert bytes(self.p.memory[0,0x8800:0x9000])==pair(REGULAR), 'Regular font was not restored/uploaded'
        cache=self.cache(); tiles=self.read('wTilemap',360);attrs=self.read('wAttrmap',360)
        base,address=self.cache_base()
        map_address=int.from_bytes(bytes(self.read('hBGMapAddress',2)),'little')
        palettes=self.read('wBGPals2',64);screen=np.asarray(self.p.screen.image.convert('RGB'))>>3
        counts={'regular':0,'bold':0}
        for y in (range(18) if rows is None else rows):
            for x in range(20):
                tile,attr=tiles[y*20+x],attrs[y*20+x]
                if tile>=128 and not attr&8:
                    raw=pair(REGULAR[(tile-128)*8:(tile-127)*8]);style='regular'
                elif attr&8 and base<=tile<base+len(cache):
                    code=cache[tile-base]
                    raw=pair(BOLD[(code-128)*8:(code-127)*8]);style='bold'
                else:continue
                actual_attr=self.p.memory[1,map_address+y*32+x]
                assert actual_attr==attr, (label,'Font bank/palette attribute not published',x,y,attr,actual_attr)
                colors=[]
                for n in range(4):
                    offset=(attr&7)*8+n*2;value=palettes[offset]|palettes[offset+1]<<8
                    colors.append([value&31,(value>>5)&31,(value>>10)&31])
                expected=np.array([[colors[((raw[2*r]>>(7-c))&1)|(((raw[2*r+1]>>(7-c))&1)<<1)] for c in range(8)] for r in range(8)],dtype='uint8')
                if attr&0x20:expected=expected[:,::-1]
                if attr&0x40:expected=expected[::-1]
                assert np.array_equal(screen[y*8:y*8+8,x*8:x*8+8],expected), (label,'Glyph RGB555 pixel mismatch',x,y,tile,attr,style)
                counts[style]+=1
        assert sum(counts.values())>=5, (label,'Insufficient native text cells')
        if not allow_overflow:assert self.read('wPeonBoldGlyphOverflow')==[0], (label,'Ordinary name exceeded cache')
        row={'phase':label,'native_rgb555_glyph_pixels_exact':True,'cells':counts,
             'cached_source_codes':cache,'regular_font_full128_tiles_exact':True,
             'bold_cache_bytes_exact':True,'font_cache_address':hex(address),
             'hardware_font_bank_attributes_exact':True,
             'overflow':self.read('wPeonBoldGlyphOverflow')[0]}
        self.glyph_checks.append(row);return row

    def settled_check(self,label,rows=None):
        self.p.tick(60,True)
        result=self.check_pixels(label,rows)
        self.capture(self.class_name+'_'+label)
        return result

    def start_choice(self,number):
        self.press('start',100)
        for _ in range(14):
            current=self.read('wMenuCursorPosition')[0]
            if current==number:break
            self.press('up' if current>number else 'down',30)
        assert self.read('wMenuCursorPosition')==[number]
        self.press('a',90)

    def until_world(self):
        handled=self.move_menus;entered=bool(self.read('wBattleMode')[0])
        for _ in range(240):
            entered|=bool(self.read('wBattleMode')[0])
            if entered and self.read('wBattleMode')==[0] and self.read('wScriptMode')==[0]:return
            if self.move_menus>handled:
                handled=self.move_menus
                for _ in range(5):
                    if self.read('wCurMoveNum')==[0]:break
                    self.press('up',30)
                self.press('a',120)
            elif self.phase=='battle':
                for _ in range(4):
                    x,y=self.read('wMenuCursorX')[0],self.read('wMenuCursorY')[0]
                    if (x,y)==(1,1):break
                    self.press('left' if x>1 else 'up',30)
                self.press('a',60)
            else:self.press('a',60)
        raise AssertionError('Native battle did not finish')

def normal_route(s,index,report):
    s.class_name=('shaman','warrior','warlock')[index]
    s.class_capture=True
    s.fresh_class(index)
    assert not s.class_capture
    record_before=s.read('wPlayerName',11)
    chars=text_encoding();assert record_before==[chars[ch] for ch in 'Péon ABCDE']+[0x50]
    s.start_choice(1)
    row=s.settled_check('character_regular_body_bold_player')
    assert row['cells']['bold']>=9 and row['cells']['regular']>=10
    assert s.decoded(1,2,10)==[chars[ch] for ch in 'Péon ABCDE']
    s.press('b',90);s.press('b',90)
    s.start_choice(2)
    row=s.settled_check('bags_regular_body_bold_player')
    assert row['cells']['bold']>=9
    s.press('a',40);s.ready('inventory')
    s.settled_check('inventory_regular_item_description')
    s.press('right',40);s.ready('inventory');s.settled_check('inventory_after_item_change')
    s.press('b',90);s.press('b',90);s.press('b',90)
    assert s.read('wScriptMode')==[0]
    before=actual_world_graphics(s)
    s.press('select',150);s.settled_check('map_locked_regular_font')
    s.press('b',90);s.p.tick(60,True)
    after=actual_world_graphics(s)
    assert_world_restored(before,after)
    assert bytes(s.p.memory[0,0x8800:0x9000])==pair(REGULAR)
    s.navigate((7,12));s.press('left',30);s.typing_watch=True;s.press('a',120)
    for _ in range(8):
        if s.read('wScriptMode')==[0]:break
        s.settled_check('kento_dialogue_page_'+str(_),[14,16]);s.press('a',120)
    # For the Shaman this reaches the trainer; other classes finish the refusal.
    for _ in range(10):
        s.press('b',90)
        if s.read('wScriptMode')==[0]:break
    s.phase,s.context='overworld',None
    s.talk((10,10),'up',s.class_name+'_quest_accept')
    assert s.event('EVENT_PEON_QUEST_ACCEPTED')
    s.navigate((18,13));s.press('up',30);s.press('a',80)
    s.wait(lambda:s.phase=='battle',buttons=True)
    row=s.settled_check('battle_names_bold_actions_regular')
    assert row['cells']['bold']>=4 and row['cells']['regular']>=5
    s.press('right',30);s.press('a',120)
    row=s.settled_check('battle_self_regular_body_bold_player')
    assert row['cells']['bold']>=9
    s.press('b',90);s.ready('battle')
    row=s.settled_check('battle_names_restored_after_self')
    assert row['cells']['bold']>=4
    if index!=1:
        s.attack_slot(1)
        assert s.read('wBattleMode')[0], 'Ordinary first spell must leave the tutorial boar alive'
        row=s.settled_check('battle_font_after_native_spell_and_pet')
        assert row['cells']['bold']>=4
        if index==0:
            s.use_item(0x94,True)
            assert s.read('wPeonEarthTotemActive')==[1]
            row=s.settled_check('battle_font_after_bags_earth_totem')
            assert row['cells']['bold']>=4
    s.until_world();assert s.event('EVENT_PEON_QUEST_DONE')
    assert s.read('wPlayerName',11)==record_before
    assert s.read('wPeonBoldGlyphOverflow')==[0]
    if index==0:
        s.talk((10,10),'up','shaman_actual_second_quest_accept')
        assert s.event('EVENT_PEON_STING_ACCEPTED')
        s.rest();s.navigate((17,15));s.wait(lambda:s.phase=='battle',buttons=True)
        s.until_world();assert s.event('EVENT_PEON_SCORPID_DEFEATED')
        s.talk((10,10),'up','shaman_actual_map_quest_reward');assert s.event('EVENT_PEON_MAP_RECEIVED')
        s.rest();s.navigate((13,9))
        before=actual_world_graphics(s)
        s.press('select',180);assert s.read('wMenuCursorY')==[1]
        chart=(ROOT/'gfx/peon_maps/valley.bin').read_bytes()
        assert bytes(s.p.memory[0,0x9000:0x9800])==chart[:2048]
        assert bytes(s.p.memory[0,0x8800:0x9000])==chart[2048:4096]
        assert bytes(s.p.memory[1,0x9000:0x9660])==chart[4096:5728]
        s.capture('shaman_actual_earned_seven_sector_atlas')
        s.press('b',180);s.p.tick(60,True)
        assert_world_restored(before,actual_world_graphics(s))
        assert bytes(s.p.memory[0,0x8800:0x9000])==pair(REGULAR)
        s.start_choice(1);s.settled_check('character_names_after_actual_atlas_restore')
        s.press('b',90);s.press('b',90)
        report['earned_atlas_font_restore']={'ordinary_actual_second_quest':True,
            'real_atlas_graphics_loaded_in_both_banks':True,'native_font_full128_restored':True,
            'all_actual_allocated_sprite_graphics_restored':True,
            '190_static_terrain_tiles_and_both_banks_preserved':True,
            'names_rebuilt_correctly_after_native_atlas_cache_eviction':True}
    restart=s.cold_restart()
    assert s.read('wPlayerName',11)==record_before and s.cold_preview
    report['normal'][s.class_name]={'ordinary_buttons_only':True,'ram_edits':False,
        'emulator_states_loaded':False,'saved_name_record_unchanged':True,
        'normal_glyph_checks':s.glyph_checks,'native_victory':True,
        'native_text_scroll_calls':s.scrolls,
        'font_cache_checks_after_native_enemy_poses':s.enemy_pose_font_checks,
        'font_cache_checks_during_native_enemy_frames':s.enemy_animation_cache_checks,
        'actual_native_enemy_frame_commands':sorted(s.enemy_animation_commands),
        'atomic_hardware_glyph_attribute_pairs_observed':s.paired_publications,
        'actual_partial_name_typing':s.partial_typing,
        'actual_battery_restart':restart,
        'actual_cold_saved_name_preview':s.cold_preview}

def boundary_fixtures(s,report):
    chars=text_encoding()
    encode=lambda value:[chars[ch] for ch in value]
    s.class_name='diagnostic';s.class_capture=True;s.fresh_class(0)
    boundary=[0,0x26,*encode('ABCDEFGHIJKLMNOPQR'),0x4f,*encode('STUVW'),0x27,*encode(' regular'),0x57]
    row=s.queue_text_fixture(boundary,'diagnostic_23_unique_name_glyphs')
    assert s.read('wPeonBoldGlyphCount')==[23] and s.read('wPeonBoldGlyphOverflow')==[0]
    assert row['cells']['bold']==23 and row['cells']['regular']>=7
    report['diagnostic_23_glyph_boundary']=row
    s.finish_text_fixture()
    entries=len(s.overflow_entries)
    extra=[0,0x26,*encode('ABCDEFGHIJKLMNOPQR'),0x4f,*encode('STUVWXYZ'),0x27,*encode(' done'),0x57]
    row=s.queue_text_fixture(extra,'diagnostic_overflow_preserves_existing_name_pixels')
    assert s.read('wPeonBoldGlyphCount')==[23] and s.read('wPeonBoldGlyphOverflow')==[1]
    captures=s.overflow_entries[entries:]
    assert len(captures)==3 and len(set(captures))==1
    _,address=s.cache_base()
    assert captures[0]==bytes(s.p.memory[1,address:address+23*16])
    assert row['cells']['bold']==23
    report['diagnostic_overflow']={'fixture':'26 distinct bold letters in bounded private RAM text',
        'overflow_falls_back_regular':True,'existing_23_glyph_bytes_unchanged':True,
        'native_rgb555_pixels_exact':row}
    s.finish_text_fixture()
    row=s.queue_text_fixture([0,*encode('Regular text'),0x4f,*encode('clears old names.'),0x57],
                             'diagnostic_regular_clears_old_bold_cells')
    assert row['cells']['bold']==0 and s.read('wPeonBoldGlyphCount')==[0]
    assert all(not attr&8 for y in (14,16) for attr in s.read('wAttrmap',360)[y*20+1:y*20+19])
    report['diagnostic_regular_over_bold_clearing']=row
    s.finish_text_fixture()
    report['diagnostic_method']='Temporary private RAM text/script buffers only, interpreted by native code. No CPU calls substituted, no user save files read.'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--expected-sha',required=True)
    args=parser.parse_args();digest=hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest()
    assert digest==args.expected_sha
    OUT.mkdir(parents=True,exist_ok=True);logging.disable(logging.CRITICAL)
    symbols=symbols_from(ROOT/'pokecrystal.sym')
    report={'rom_sha256':digest,'passed':False,'user_battery_files_opened':False,
            'source':source_checks(symbols),'normal':{}}
    session=None
    try:
        with redirected_retained_outputs(), tempfile.TemporaryDirectory(prefix='peon-v026-typography-') as temporary:
            for index in range(3):
                rom=Path(temporary)/f'class_{index}.gbc';shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
                session=FontSession(rom,symbols)
                normal_route(session,index,report)
                session.p.stop(save=False);session=None
            rom=Path(temporary)/'boundary.gbc';shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
            session=FontSession(rom,symbols)
            boundary_fixtures(session,report)
            session.p.stop(save=False);session=None
        assert hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest()==digest
        report['passed']=True
    except Exception as error:
        report['failure']=repr(error)
        if session:session.capture('unexpected_font_state')
        raise
    finally:
        if session:session.p.stop(save=False)
        (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS native regular/name typography',digest,flush=True)

if __name__=='__main__':main()
