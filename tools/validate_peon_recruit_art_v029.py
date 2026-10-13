#!/usr/bin/env python3
"""Check authored v029 packets and actual native front/back rendering.

The linked-data checks read the requested frozen ROM, not a live build. Native
graphics diagnostics use private ROM copies and explicitly declared encounter,
HP and party fixtures; menus, animation and picture uploads execute normally.
They establish rendering, not ordinary recruitment or progression. The latter
belongs to the separate team/quest regression. No user battery is opened.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import logging
import shutil
import subprocess
import tempfile

import numpy as np
from PIL import Image
from validate_peon_resources_v029 import ResourceSession, symbols_from
from validate_peon_battle_totems import BagSession
from validate_peon_deep_ui import text_encoding
from validate_peon_villages import sprite_constants
from peon_event_flags_v029 import event_indices
from validate_peon_combat_v028 import PolishSession

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/recruitment_v029/runtime_art'
BINDINGS = {
    95: ('onix', 'earth_spirit', 'PokefanMSpriteGFX'),
    74: ('geodude', 'demon_imp', None),
    68: ('machamp', 'orc_grunt', 'PokefanFSpriteGFX'),
    88: ('grimer', 'orc_warlock', 'PeonCultistGFX'),
    77: ('ponyta', 'kolkar_archer', 'CooltrainerMSpriteGFX'),
    78: ('rapidash', 'kolkar_melee', 'CooltrainerFSpriteGFX'),
}
WORLD_NAMES = {'PokefanMSpriteGFX':'SPRITE_POKEFAN_M','PokefanFSpriteGFX':'SPRITE_POKEFAN_F',
    'PeonCultistGFX':'SPRITE_SUPER_NERD','CooltrainerMSpriteGFX':'SPRITE_COOLTRAINER_M',
    'CooltrainerFSpriteGFX':'SPRITE_COOLTRAINER_F'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def decode(data, width, height, column=False):
    result = np.zeros((height, width), dtype='uint8')
    rows, cols = height // 8, width // 8
    assert len(data) == rows * cols * 16
    for tile in range(rows * cols):
        tx, ty = divmod(tile, rows) if column else (tile % cols, tile // cols)
        for y in range(8):
            low, high = data[tile * 16 + y * 2:tile * 16 + y * 2 + 2]
            for x in range(8):
                result[ty * 8 + y, tx * 8 + x] = ((low >> (7-x)) & 1) | (((high >> (7-x)) & 1) << 1)
    return result


def rom_slice(rom, symbol, length):
    bank, address = symbol
    offset = address if bank == 0 else bank * 0x4000 + address - 0x4000
    assert 0 <= offset <= len(rom) - length
    return rom[offset:offset + length]


def linked_packets(path, sym):
    rom = Path(path).read_bytes()
    records = {}
    for species, (slug, art, world_label) in BINDINGS.items():
        folder = ROOT / 'gfx/peon_native_v029' / slug
        label = slug.capitalize()
        row = rom_slice(rom, sym['PokemonPicPointers'], species * 6)[(species-1)*6:species*6]
        packet_records = {}
        for index, (kind, filename) in enumerate((('Front', 'front.animated.2bpp.lz'), ('Back', 'back.2bpp.lz'))):
            stored_bank, lo, hi = row[index*3:index*3+3]
            bank, address = sym[label + kind + 'pic']
            assert (stored_bank + 0x36) & 0xff == bank, (slug, kind, 'raw bank pointer mismatch')
            assert lo | hi << 8 == address, (slug, kind, 'picture pointer address mismatch')
            expected = (folder / filename).read_bytes()
            actual = rom_slice(rom, (bank, address), len(expected))
            assert actual == expected, (slug, kind, 'ROM packet differs from source generator')
            with tempfile.TemporaryDirectory(prefix='peon-native-art-lz-') as temp:
                encoded, decoded = Path(temp)/'packet.lz', Path(temp)/'packet.bin'
                encoded.write_bytes(actual)
                subprocess.run([str(ROOT/'tools/lzcompress'), '-u', str(encoded), str(decoded)], check=True)
                raw = decoded.read_bytes()
            expected_raw = (folder / filename.removesuffix('.lz')).read_bytes()
            assert raw == expected_raw, (slug, kind, 'native compressed packet roundtrip')
            packet_records[kind.lower()] = {'linked_bank': bank, 'linked_address': address,
                'pointer_raw_bank_plus_0x36_exact': True, 'compressed_sha256': digest(actual),
                'decompressed_sha256': digest(raw), 'native_bytes': len(raw)}
        palette = (folder / 'normal.gbcpal').read_bytes()
        assert palette[:2] == b'\xff\x7f' and palette[-2:] == b'\x00\x00'
        # Table entry zero precedes the real species and each species has two
        # sets of the middle two RGB555 colors (normal and shiny).
        actual_palette = rom_slice(rom, sym['PokemonPalettes'], (species+1)*8)[species*8:(species+1)*8]
        assert actual_palette == palette[2:6] * 2, (slug, 'native palette table does not match authored colors')
        world = None
        if world_label:
            expected_world = (folder / 'world_npc.2bpp').read_bytes()
            actual_world = rom_slice(rom, sym[world_label], len(expected_world))
            assert actual_world == expected_world, (slug, 'native NPC packet differs')
            world = {'label': world_label, 'six_native_NPC_frames_exact': True,
                'bytes': len(actual_world), 'sha256': digest(actual_world),
                'source_frame_indices': [0, 1, 2, 4, 5, 6], 'right_facing': 'native mirrored Left'}
        dictionary = (folder / 'front.animated.2bpp').read_bytes()
        tilemap = (folder / 'front.animated.tilemap').read_bytes()
        original = (ROOT / 'gfx/peon_recruits_v029' / art / 'front_frames.bin').read_bytes()
        assert len(dictionary) // 16 <= 98 and len(tilemap) == 147
        assert tilemap[:49] == bytes(range(49)) and dictionary[:784] == original[:784], (
            slug, 'native frame zero must be the directly loaded first 49 tiles')
        for frame in range(3):
            rebuilt = b''.join(dictionary[t*16:(t+1)*16] for t in tilemap[frame*49:(frame+1)*49])
            assert rebuilt == original[frame*784:(frame+1)*784]
        for table,suffix in (('FramesPointers','Frames'),('BitmasksPointers','Bitmasks'),
                             ('AnimationPointers','Animation'),('AnimationIdlePointers','AnimationIdle')):
            entry=rom_slice(rom,sym[table],species*2)[(species-1)*2:species*2]
            bank,address=sym[label+suffix]
            assert int.from_bytes(entry,'little')==address,(slug,table,'native animation pointer')
            expected_bank=sym['KantoFrames'][0] if suffix=='Frames' else sym[table][0]
            assert bank==expected_bank,(slug,table,'animation data bank does not match native resolver')
        assert rom_slice(rom,sym[label+'Animation'],9)==bytes((0,10,1,8,2,8,0,10,255))
        assert rom_slice(rom,sym[label+'AnimationIdle'],7)==bytes((0,10,1,8,0,10,255))
        frame_bank,frame_address=sym[label+'Frames']
        frame_pointers=rom_slice(rom,(frame_bank,frame_address),4)
        for phase in (1,2):
            address=int.from_bytes(frame_pointers[(phase-1)*2:phase*2],'little')
            assert address==sym[label+f'Frames.frame{phase}'][1]
            bitmask_index=rom_slice(rom,(frame_bank,address),1)[0]
            bitmask_bank,bitmask_address=sym[label+'Bitmasks']
            mask=rom_slice(rom,(bitmask_bank,bitmask_address+bitmask_index*7),7)
            changed=[n for n in range(49) if mask[n//8]>>(n%8)&1]
            replacement=rom_slice(rom,(frame_bank,address+1),len(changed))
            native_tiles=list(range(49))
            for n,index in zip(changed,replacement):
                assert index<len(dictionary)//16,(slug,phase,'native animation references an unallocated tile',index)
                native_tiles[n]=index
            assert bytes(native_tiles)==tilemap[phase*49:(phase+1)*49],(slug,phase,'compiled frame/bitmask changed atlas references')
        records[slug] = {'species_id': species, 'source_art': art,
            'front_dictionary_tiles': len(dictionary)//16, 'no_overflow_needed': True,
            'all_three_front_frames_roundtrip_exact': True, 'packets': packet_records,
            'all_compiled_frame_bitmask_animation_pointers_and_tile_references_exact':True,
            'linked_normal_shiny_middle_RGB555_colors_exact': True, 'native_NPC_packet': world,
            'friendly_imp_world_note': 'Existing smaller follower packet is checked by companion QA.' if species == 74 else None}
    return records


class ArtSession(ResourceSession):
    def __init__(self, rom, sym, class_index, section):
        self.section = section
        self.context = None
        self.menus = 0
        self.watch = False
        self.fixture_species = None
        self.front_phases = {}
        self.back_phases = {}
        self.graphics_errors = []
        self.scanline_frames = 0
        self.scanline_peak = 0
        self.cast_frames = []
        self.atomic_pending = []
        self.atomic_records = []
        self.chrome_checks = []
        self.strict_back = False
        self.world_fixture = None
        self.world_watch = False
        self.world_frames = {}
        self.world_previous = None
        self.scene_watch = False
        self.scene_samples = []
        self.scene_frame_count = 0
        self.scene_oam_peak = 0
        self.sprite_ids = sprite_constants()
        self.world_ids = {self.sprite_ids[WORLD_NAMES[label]]:slug for slug,_,label in BINDINGS.values() if label}
        self.world_packets = {slug:(ROOT/'gfx/peon_native_v029'/slug/'world_npc.2bpp').read_bytes() for slug,_,_ in BINDINGS.values()}
        self.front_pixels = {}
        self.back_pixels = {}
        self.back_packets = {}
        self.enemy_animation_entries = []
        for species,(slug,art,_) in BINDINGS.items():
            folder=ROOT/'gfx/peon_recruits_v029'/art
            front=(folder/'front_frames.bin').read_bytes()
            back=(folder/'back_frames.bin').read_bytes()
            self.front_pixels[species]=[decode(front[n*784:(n+1)*784],56,56,True) for n in range(3)]
            self.back_packets[species]=[back[n*576:(n+1)*576] for n in range(3)]
            self.back_pixels[species]=[decode(data,48,48,True) for data in self.back_packets[species]]
        super().__init__(rom, sym, class_index, section)
        self.flags.update(event_indices())

    def open(self):
        super().open()
        for label in ('LoadBattleMenu','StaticMenuJoypad','LoadTrainerOrWildMonPic','PeonTeamPickV029.input'):
            self.p.hook_deregister(*self.sym[label])
        self.p.hook_register(*self.sym['LoadBattleMenu'], self.battle_menu, None)
        self.p.hook_register(*self.sym['StaticMenuJoypad'], self.menu_ready, None)
        self.p.hook_register(*self.sym['LoadTrainerOrWildMonPic'], self.set_enemy_fixture, None)
        self.p.hook_register(*self.sym['RefreshSprites'], self.set_world_fixture, None)
        if 'PeonTeamPickV029.input' in self.sym:
            self.p.hook_register(*self.sym['PeonTeamPickV029.input'], self.team_ready, None)
        self.p.hook_register(*self.sym['PeonCopyBattleBackPoseAtomic'], self.atomic_enter, None)
        self.p.hook_register(*self.sym['PeonAnimateEnemyAttack'],self.enemy_animation_started,None)
        bank, address = self.sym['PeonCopyBattleBackPoseAtomic.restore_registers']
        assert self.p.memory[bank,address+4] == 0xc9
        self.p.hook_register(bank,address+4,self.atomic_done,None)

    def battle_menu(self, _):
        self.resource_battle_menu(None)
        self.phase, self.context = 'battle_drawing', 'battle'
        self.menus += 1

    def menu_ready(self, _):
        self.resource_static_ready(None)
        if self.context:
            self.phase = self.context

    def team_ready(self, _):
        self.resource_phase('supply_target')
        self.phase='team'

    def enemy_animation_started(self, _):
        if self.watch:
            self.enemy_animation_entries.append({'frame':self.p.frame_count,
                'species':self.read('wEnemyMonSpecies')[0],'turn':self.read('hBattleTurn')[0],
                'move':self.read('wCurEnemyMove')[0],'options':self.read('wOptions')[0],
                'substitute':self.read('wEnemySubStatus4')[0],'minimized':self.read('wEnemyMinimized')[0]})

    def set_enemy_fixture(self, _):
        self.encounter_loads+=1
        if self.fixture_species is not None:
            self.write('wTempWildMonSpecies', [self.fixture_species])
            self.write('wCurPartyLevel', [7])

    def set_world_fixture(self, _):
        if self.world_fixture is None or self.map()!=14:
            return
        bank,address=self.sym['wMapObjects']
        # An isolated native graphics fixture retains player + one existing
        # Gornek object. It does not claim the final populated map layout.
        for index in range(2,16):
            self.p.memory[bank,address+index*16+1]=0
        self.p.memory[bank,address+17]=self.world_fixture
        self.p.memory[bank,address+20]=2  # native SPRITEMOVEDATA_WANDER
        self.p.memory[bank,address+21]=0x11

    def write(self, name, values):
        assert self.section.startswith('diagnostic'), 'RAM fixture writes are only allowed in the labelled diagnostic branch'
        BagSession.write(self, name, values)

    def press(self, key, frames=90):
        self.p.button(key, delay=4)
        self.tick(frames)
        if self.read('wBattleMode')[0]:
            return
        for _ in range(100):
            if self.phase in ('overworld', 'main', 'slots'):
                return
            if self.phase in ('confirm', 'message') and self.wait_ready:
                return
            self.tick(10)
        raise AssertionError(('native UI not ready', self.phase))

    def tick(self, frames):
        for _ in range(frames):
            self.p.tick(1, True)
            if self.watch:
                try:
                    self.observe_frame()
                except Exception as error:
                    self.graphics_errors.append({'frame': self.p.frame_count, 'error': repr(error)})
            if self.world_watch:
                try:
                    self.observe_world()
                except Exception as error:
                    self.graphics_errors.append({'frame':self.p.frame_count,'world_error':repr(error)})
            if self.scene_watch:
                try:
                    self.observe_scene()
                except Exception as error:
                    self.graphics_errors.append({'frame':self.p.frame_count,'scene_error':repr(error)})
        assert not self.graphics_errors, self.graphics_errors[-4:]

    def capture(self, label):
        folder = OUT / self.section / self.slug
        folder.mkdir(parents=True, exist_ok=True)
        self.p.screen.image.save(folder / (label + '.png'))
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(folder / (label + '_4x.png'))

    def palette(self, index):
        raw = bytes(self.read('wBGPals2', 64))[index*8:index*8+8]
        words = [int.from_bytes(raw[i:i+2], 'little') for i in range(0,8,2)]
        return np.array([[v&31, v>>5&31, v>>10&31] for v in words], dtype='uint8')

    def observe_world(self):
        if self.read('wBattleMode')[0] or self.read('wScriptMode')[0]:
            return
        actors=self.read('wObjectStructs',13*40)
        matches=[actors[n*40:(n+1)*40] for n in range(1,13)
                 if actors[n*40]==self.world_fixture and actors[n*40+1]==1]
        if not matches:
            return
        actor=matches[0]
        slug=self.world_ids[self.world_fixture]
        binary=self.world_packets[slug]
        tile=actor[2];bank=0 if tile&128 else 1;base=tile&127;address=0x8000+base*16
        assert bytes(self.p.memory[bank,address:address+192])==binary[:192],(slug,'native standing NPC VRAM')
        assert bytes(self.p.memory[bank,address+0x800:address+0x800+192])==binary[192:],(slug,'native walking NPC VRAM')
        current=(actor,list(self.p.memory[0xfe00:0xfea0]))
        snapshots=[current]+([self.world_previous] if self.world_previous is not None else [])
        self.world_previous=current
        actual=np.array(self.p.screen.image.convert('RGB'))>>3
        palettes=bytes(self.read('wOBPals2',64))
        for oldactor,oam in snapshots:
            facing=oldactor[13]
            if facing>=16:
                continue
            direction,phase=divmod(facing,4)
            column=min(direction,2)
            walking=bool(phase&1)
            mirror=direction==3 or (direction in (0,1) and phase==3)
            start=base+column*4+(0x80 if walking else 0)
            entries=[oam[n:n+4] for n in range(0,160,4)
                     if oam[n] and oam[n+1] and start<=oam[n+2]<start+4 and oam[n+3]>>3&1==bank]
            if sorted(row[2] for row in entries)!=list(range(start,start+4)):
                continue
            left,top=min(row[1] for row in entries),min(row[0] for row in entries)
            geometry={row[2]-start:(row[1]-left,row[0]-top) for row in entries}
            wanted={0:(8 if mirror else 0,0),1:(0 if mirror else 8,0),
                    2:(8 if mirror else 0,8),3:(0 if mirror else 8,8)}
            assert geometry==wanted,(slug,'native four-tile NPC geometry',facing,geometry,wanted)
            assert all(bool(row[3]&32)==mirror and not row[3]&64 for row in entries)
            source_index=column+(3 if walking else 0)
            source=binary[source_index*64:(source_index+1)*64]
            matched=True;visible=0
            for y,x,t,attribute in entries:
                px,py=x-8,y-16
                if not (0<=px<=152 and 0<=py<=136):
                    matched=False;break
                indices=decode(source[(t-start)*16:(t-start+1)*16],8,8)
                if mirror:indices=indices[:,::-1]
                mask=indices>0
                words=[int.from_bytes(palettes[(attribute&7)*8+i:(attribute&7)*8+i+2],'little') for i in range(0,8,2)]
                palette=np.array([[v&31,v>>5&31,v>>10&31] for v in words],dtype='uint8')
                visible+=int(mask.sum())
                if mask.any() and not np.array_equal(actual[py:py+8,px:px+8][mask],palette[indices][mask]):
                    matched=False;break
            if matched and visible>=16:
                key=(direction,int(walking),int(mirror))
                if key not in self.world_frames:self.world_frames[key]=self.p.screen.image.copy()
                return

    def world_cycle(self, species):
        _,_,label=BINDINGS[species]
        self.world_fixture=self.sprite_ids[WORLD_NAMES[label]]
        self.navigate((17,5),23);self.navigate((5,7),14)
        self.navigate((12,9))
        self.world_watch=True
        for _ in range(200):
            self.tick(20)
            facings={(d,w) for d,w,_ in self.world_frames}
            if {(d,w) for d in range(4) for w in range(2)}<=facings:
                break
        self.world_watch=False
        facings={(d,w) for d,w,_ in self.world_frames}
        assert {(d,w) for d in range(4) for w in range(2)}<=facings,(label,'native NPC facings/foot frames not all visible',sorted(facings))
        folder=OUT/self.section/self.slug;folder.mkdir(parents=True,exist_ok=True)
        for key,frame in self.world_frames.items():
            frame.save(folder/('world_facing_'+'_'.join(map(str,key))+'.png'))
        images=list(self.world_frames.values())
        images[0].save(folder/'world_actual_native.gif',save_all=True,append_images=images[1:],duration=150,loop=0)
        return {'private_map_object_fixture':True,'native_wander_function':True,
                'source_six_native_NPC_packets_exact_in_both_VRAM_banks':True,
                'all_four_directions_standing_and_walking_RGB555_pixels_exact':True,
                'actual_facings':sorted(self.world_frames),'native_Right_and_second_Down_Up_step_mirrors':True}

    def observe_scene(self):
        if self.read('wBattleMode')[0] or self.read('wScriptMode')[0] or self.map()!=17:
            return
        allocations=[]
        used=self.read('wUsedSprites',64)
        assert any(used[n]==0 for n in range(0,64,2)), 'native sprite queue has no terminator'
        for n in range(0,64,2):
            sprite,tile=used[n:n+2]
            if not sprite:
                break
            if sprite>=0xfd:
                reserve=4
            else:
                bank,address=self.sym['OverworldSprites']
                data=bytes(self.p.memory[bank,address+(sprite-1)*6:address+sprite*6])
                reserve=32 if data[4]==0 else 4 if data[4]==3 else 12
            native_bank=0 if tile&128 else 1
            start=tile&127
            assert start+reserve<=128, ('world sprite allocation overflows native bank',sprite,tile,reserve)
            for prev in allocations:
                assert prev['bank']!=native_bank or start>=prev['end'] or start+reserve<=prev['start'], (
                    'world native sprite intervals overlap',prev,{'sprite':sprite,'start':start,'end':start+reserve})
            allocations.append({'sprite':sprite,'bank':native_bank,'start':start,'end':start+reserve})
        assert len(allocations)>=8, ('populated scene was accidentally reduced',allocations)
        objects=list(self.p.memory[0xfe00:0xfea0])
        if self.p.memory[0xff40]&2:
            height=16 if self.p.memory[0xff40]&4 else 8
            counts=[0]*144
            for n in range(0,160,4):
                top=objects[n]-16
                for y in range(max(0,top),min(144,top+height)):
                    counts[y]+=1
            peak=max(counts);self.scene_oam_peak=max(self.scene_oam_peak,peak)
            assert peak<=10, ('populated Senjin OAM scanline overflow',peak,[y for y,count in enumerate(counts) if count>10])
        follower=self.read('wObjectFollow_Follower')[0]
        assert self.read('wObjectFollow_Leader')==[0] and 0<follower<13, 'living Warlock follower absent in populated Senjin'
        actors=self.read('wObjectStructs',13*40)
        sprite_ids={actors[n*40] for n in range(1,13) if actors[n*40]}
        assert 104 in sprite_ids, ('wrong friendly imp sprite in populated Senjin',sprite_ids)
        self.scene_frame_count+=1
        if self.scene_frame_count%20==0:
            self.scene_samples.append({'frame':self.p.frame_count,'position':self.position(),
                'allocations':allocations,'active_sprite_ids':sorted(sprite_ids),
                'physical_OAM_peak':self.scene_oam_peak})

    def populated_senjin(self):
        assert self.map()==17, 'The supplied private scene battery must continue in Senjin Village'
        assert self.event('EVENT_PEON_WARLOCK') and self.event('EVENT_PEON_SARKOTH_REPORT_DONE')
        assert self.read('wPartyCount')[0]>=2 and self.read('wPartyMon2Species')==[74]
        assert self.read('wPartyMon2HP',2)!=[0,0]
        self.navigate((10,14))
        self.scene_watch=True
        self.tick(120)
        for point in ((10,13),(11,13),(12,13),(13,13),(13,14),(13,15),(12,15),(11,15),(10,15),(10,14)):
            # Use individual native directional taps, observing every frame
            # while real guards, both nodes and the follower remain enabled.
            for key in self.path(point):
                before=self.position()
                for _ in range(8):
                    self.press(key,40)
                    if self.position()!=before:break
                assert sum(abs(a-b) for a,b in zip(before,self.position()))==1,(key,before,self.position())
            self.tick(40)
        self.tick(240);self.scene_watch=False
        sprite_ids={value for row in self.scene_samples for value in row['active_sprite_ids']}
        needed={104,self.sprite_ids['SPRITE_POKEFAN_M'],self.sprite_ids['SPRITE_POKEFAN_F']}
        assert needed<=sprite_ids, ('follower / post-report Earth and Grunt nodes not all actually loaded',needed,sprite_ids)
        assert self.scene_frame_count>=500 and self.scene_samples
        self.capture('populated_senjin_real_follower_and_post_report_nodes')
        return {'full_ROM_map_objects_preserved':True,'native_button_movement_only':True,
            'private_battery_continue':True,'RAM_writes':False,'living_real_imp_member_and_follower':True,
            'both_post_report_nodes_actually_loaded':True,'all_native_standing_walking_reservations_nonoverlapping':True,
            'physical_OAM_counts_include_X_hidden_objects':True,'frames':self.scene_frame_count,
            'physical_OAM_peak':self.scene_oam_peak,'samples':self.scene_samples}

    def protected(self):
        return {name:digest(bytes(self.p.memory[bank,start:end])) for name,bank,start,end in (
            ('font0',0,0x8800,0x9000),('enemy_front0',0,0x9000,0x9310),
            ('after_back0',0,0x9550,0x9800),('rank_totem_pet1',1,0x8800,0x8920),
            ('bold_font1',1,0x8920,0x8a90))}

    def atomic_enter(self, _):
        if not self.watch:
            return
        self.atomic_pending.append({'sp':self.p.register_file.SP,
            'vbk':self.p.memory[0xff4f], 'bgmode':self.read('hBGMapMode')[0],
            'source_bank':self.p.register_file.B, 'source_address':self.p.register_file.D<<8|self.p.register_file.E,
            'protected':self.protected(), 'flags':bytes(self.read('wEventFlags',256)),
            'tile_count':self.p.register_file.C})

    def atomic_done(self, _):
        if not self.atomic_pending:
            return
        try:
            row = self.atomic_pending.pop()
            assert row['sp'] == self.p.register_file.SP
            assert row['tile_count'] == 36
            assert row['vbk'] == self.p.memory[0xff4f] and row['bgmode'] == self.read('hBGMapMode')[0]
            assert row['protected'] == self.protected(), 'back pose upload damaged unrelated font/portrait regions'
            assert row['flags'] == bytes(self.read('wEventFlags',256)), 'back pose changed saved flags'
            source = bytes(self.p.memory[row['source_bank'], row['source_address']:row['source_address']+576])
            assert source == bytes(self.p.memory[0,0x9310:0x9550]), 'atomic destination differs from actual source packet'
            self.atomic_records.append({k:v for k,v in row.items() if k not in ('sp','protected','flags')})
        except Exception as error:
            self.graphics_errors.append({'atomic_upload':repr(error)})

    def observe_frame(self):
        if not self.read('wBattleMode')[0]:
            return
        actual = np.array(self.p.screen.image.convert('RGB')) >> 3
        enemy = self.read('wEnemyMonSpecies')[0]
        if enemy in BINDINGS:
            slug, art, _ = BINDINGS[enemy]
            for phase,pixels in enumerate(self.front_pixels[enemy]):
                if np.array_equal(actual[0:56,96:152],self.palette(1)[pixels]):
                    self.front_phases.setdefault(slug,{})[phase] = self.p.screen.image.copy()
        ally = self.read('wBattleMonSpecies')[0]
        if ally in BINDINGS:
            slug, art, _ = BINDINGS[ally]
            live = bytes(self.p.memory[0,0x9310:0x9550])
            if self.strict_back:
                assert live in self.back_packets[ally], (slug,'back VRAM is not a complete authored pose')
            for phase,(data,pixels) in enumerate(zip(self.back_packets[ally],self.back_pixels[ally])):
                if live == data and np.array_equal(actual[48:96,16:64],self.palette(0)[pixels]):
                    self.back_phases.setdefault(slug,{})[phase] = self.p.screen.image.copy()
        if self.p.memory[0xff40] & 2:
            height = 16 if self.p.memory[0xff40] & 4 else 8
            counts = [0]*144
            objects = list(self.p.memory[0xfe00:0xfea0])
            for n in range(0,160,4):
                top = objects[n]-16
                for y in range(max(0,top),min(144,top+height)):
                    counts[y] += 1
            peak = max(counts)
            self.scanline_frames += 1
            self.scanline_peak = max(self.scanline_peak,peak)
            assert peak <= 10, ('native physical OAM scanline overflow',peak,self.read('wFXAnimID',2))
        if len(self.cast_frames)<320:
            self.cast_frames.append(self.p.screen.image.copy())

    def enter_fixture_battle(self, species):
        self.fixture_species = species
        self.talk_plain((10,10),'up')
        self.navigate((18,13))
        self.press('up',30); self.press('a',60)
        self.wait(lambda:self.phase=='battle',buttons=True)
        self.fixture_species = None
        assert self.read('wEnemyMonSpecies') == [species]
        for prefix in ('wBattleMon','wPartyMon1','wEnemyMon'):
            self.write(prefix+'HP',[0,240]);self.write(prefix+'MaxHP',[0,240])
        self.write('wEnemyMonMoves',[33,0,0,0]);self.write('wEnemyMonPP',[35,0,0,0])
        self.write('wEnemyMonStatus',[0]);self.write('wBattleMonStatus',[0])
        self.tick(40)

    def cast_basic(self):
        self.wait(lambda:self.phase=='battle')
        menus, moves = self.menus, self.move_menus
        for _ in range(5):
            x,y=self.read('wMenuCursorX')[0],self.read('wMenuCursorY')[0]
            if (x,y)==(1,1):break
            self.press('left' if x>1 else 'up',30)
        self.press('a',60);self.wait(lambda:self.move_menus>moves)
        for _ in range(4):
            if self.read('wMenuCursorY')==[1]:break
            self.press('up',30)
        self.press('a',30)
        self.wait(lambda:self.menus>menus and self.phase=='battle',buttons=True)
        self.tick(60)
        return self.verify_battle_chrome()

    def verify_battle_chrome(self):
        """A correct creature pose must not hide a corrupt settled battle HUD."""
        bank,address=self.sym['FontBattleExtra']
        wanted=bytes(self.p.memory[bank,address:address+12*16])
        assert bytes(self.p.memory[0,0x9600:0x96c0])==wanted, (
            'custom menu return failed to reload native battle digits/Lv/HP graphics $60..$6b')
        record={'native_battle_digits_level_HP_glyph_packet_restored':True,
            'bold_header_glyphs_and_RGB555':PolishSession.assert_current_bold_name_glyphs(self)}
        self.chrome_checks.append(record)
        return record

    def prepare_ally_fixture(self, species):
        """Prepare one labelled party record; native Team does the real switch."""
        assert species in (95,74,68)
        record = bytes(self.read('wPartyMon1Species',48))
        ally = bytearray(record)
        ally[0] = species
        ally[2:6] = bytes((1,0,0,0))
        ally[23:27] = bytes((35,0,0,0))
        ally[28] = 0x80
        ally[29:31] = bytes((0,0))
        ally[34:38] = bytes((0,240,0,240))
        self.write('wPartyMon2Species',list(ally))
        self.write('wPartyCount',[2])
        self.write('wPartySpecies',[66,species,0xff])
        name = {95:'EARTHSPRT',74:'IMP',68:'ORC GRUNT'}[species]
        assert len(name)<=10
        chars=text_encoding()
        encoded=[chars[c] for c in name]+[0x50]*(11-len(name))
        assert len(encoded)==11 and encoded[-1]==0x50
        self.write('wPartyMon2Nickname',encoded)
        self.write('wPartyMon2OT',self.read('wPartyMon1OT',11))

    def switch_ally(self):
        """Use the native TEAM battle panel, never overwrite active battle data."""
        self.context=None
        for _ in range(6):
            x,y=self.read('wMenuCursorX')[0],self.read('wMenuCursorY')[0]
            if (x,y)==(2,1):break
            self.press('right' if x<2 else 'up',30)
        assert (self.read('wMenuCursorX')[0],self.read('wMenuCursorY')[0])==(2,1)
        self.press('a',60);self.wait(lambda:self.phase=='team')
        for _ in range(6):
            cursor=self.read('wPeonTeamCursorV029')[0]
            if cursor==1:break
            self.press('down' if cursor<1 else 'up',30)
        assert self.read('wPeonTeamCursorV029')==[1]
        self.capture('native_team_before_switch')
        before=self.menus
        self.press('a',60)
        self.wait(lambda:self.read('wCurBattleMon')==[1] and self.menus>before and self.phase=='battle',buttons=True)
        self.tick(60)
        self.strict_back=True
        self.verify_battle_chrome()
        self.capture('after_switch_settled_chrome_verified')

    wait = BagSession.wait


def save_phases(session, kind, slug, phases):
    folder=OUT/session.section/session.slug
    folder.mkdir(parents=True,exist_ok=True)
    for phase,frame in sorted(phases.items()):
        frame.save(folder/f'{slug}_{kind}_pose_{phase}.png')
        frame.resize((640,576),Image.Resampling.NEAREST).save(folder/f'{slug}_{kind}_pose_{phase}_4x.png')
    images=[frame.resize((480,432),Image.Resampling.NEAREST) for frame in session.cast_frames]
    if images:
        images[0].save(folder/f'{slug}_{kind}_actual_native.gif',save_all=True,append_images=images[1:],duration=17,loop=0)
    (folder/'native_observation.json').write_text(json.dumps({'phases':sorted(phases),
        'enemy_animation_entries':session.enemy_animation_entries,'used_moves':session.used_moves,
        'native_frames':len(session.cast_frames),'graphics_errors':session.graphics_errors},indent=2)+'\n')
    assert set(phases)=={0,1,2}, (kind,slug,'not all three actual RGB555 authored poses were seen',sorted(phases),session.enemy_animation_entries)
    return {'all_three_actual_RGB555_poses':True,'native_phases':sorted(phases),
        'native_frames_observed':len(images),'physical_OAM_peak':session.scanline_peak,
        'physical_OAM_frames_checked':session.scanline_frames,
        'settled_battle_chrome_checks':session.chrome_checks,
        'atomic_uploads_preserved_unrelated_VRAM_and_saved_flags':session.atomic_records}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--rom',type=Path,required=True)
    parser.add_argument('--symbols',type=Path,required=True)
    parser.add_argument('--expected-sha',required=True)
    parser.add_argument('--linked-only',action='store_true')
    parser.add_argument('--scene-battery',type=Path)
    parser.add_argument('--scene-only',action='store_true')
    args=parser.parse_args()
    logging.disable(logging.CRITICAL)
    assert digest(args.rom.read_bytes())==args.expected_sha
    sym=symbols_from(args.symbols)
    OUT.mkdir(parents=True,exist_ok=True)
    report={'passed':False,'rom_sha256':args.expected_sha,'symbols_sha256':digest(args.symbols.read_bytes()),
        'validator_sha256':digest(Path(__file__).read_bytes()),
        'method':'Frozen-ROM linked data plus actual native rendering in labelled private graphics fixtures.',
        'user_battery_files_opened':False,'ordinary_recruitment_claimed':False,'diagnostics':{}}
    try:
        report['linked_native_packets']=linked_packets(args.rom,sym)
        if args.scene_only:
            assert args.scene_battery is not None
            assert args.scene_battery.stat().st_size==32768
            report['private_scene_battery_sha256']=digest(args.scene_battery.read_bytes())
            with tempfile.TemporaryDirectory(prefix='peon-v029-populated-art-') as temp:
                path=Path(temp)/'scene.gbc';shutil.copyfile(args.rom,path)
                shutil.copyfile(args.scene_battery,Path(str(path)+'.ram'))
                s=ArtSession(path,sym,2,'populated_senjin')
                try:
                    s.tick(1800);s.press('start')
                    for _ in range(20):
                        if s.map()==17 and s.read('wScriptMode')==[0]:break
                        s.press('a',180)
                    report['populated_senjin']=s.populated_senjin()
                finally:
                    s.p.stop(save=False)
        elif not args.linked_only:
            with tempfile.TemporaryDirectory(prefix='peon-v029-art-runtime-') as temp:
                for species,(slug,art,_) in BINDINGS.items():
                    path=Path(temp)/(slug+'.gbc');shutil.copyfile(args.rom,path)
                    s=ArtSession(path,sym,0,'diagnostic_enemy/'+slug)
                    try:
                        s.fresh_resources_class()
                        s.enter_fixture_battle(species)
                        s.watch=True;s.tick(40)
                        for _ in range(4):
                            s.cast_basic()
                            if set(s.front_phases.get(slug,{}))=={0,1,2}:break
                        assert not s.hook_errors and not s.graphics_errors,(s.hook_errors,s.graphics_errors)
                        report['diagnostics'][slug]=save_phases(s,'front',slug,s.front_phases.get(slug,{}))
                    finally:
                        s.p.stop(save=False)
                for index,species in ((0,95),(2,74),(1,68)):
                    slug=BINDINGS[species][0]
                    path=Path(temp)/(slug+'_ally.gbc');shutil.copyfile(args.rom,path)
                    s=ArtSession(path,sym,index,'diagnostic_ally/'+slug)
                    try:
                        s.fresh_resources_class()
                        s.enter_fixture_battle(74)
                        s.prepare_ally_fixture(species)
                        s.watch=True;s.switch_ally();s.cast_basic()
                        assert s.read('wBattleMonSpecies')==[species]
                        assert s.read('wPartyMon1Species')==[66], 'Team switch reordered the native hero record'
                        assert not s.hook_errors and not s.graphics_errors,(s.hook_errors,s.graphics_errors)
                        report['diagnostics'][slug+'_active_ally']=save_phases(s,'back',slug,s.back_phases.get(slug,{}))
                    finally:
                        s.p.stop(save=False)
                for species,(slug,_,label) in BINDINGS.items():
                    if label is None:
                        continue
                    path=Path(temp)/(slug+'_world.gbc');shutil.copyfile(args.rom,path)
                    s=ArtSession(path,sym,0,'diagnostic_world/'+slug)
                    try:
                        s.fresh_resources_class()
                        report['diagnostics'][slug+'_world_NPC']=s.world_cycle(species)
                    finally:
                        s.p.stop(save=False)
        report['passed']=True
        report['runtime_rendering_executed']=not args.linked_only
    except Exception as error:
        report['failure']=repr(error)
        raise
    finally:
        filename='populated_senjin_validation.json' if args.scene_only else 'linked_packets_validation.json' if args.linked_only else 'validation.json'
        (OUT/filename).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'runtime':report['runtime_rendering_executed'],'rom_sha256':args.expected_sha}))


if __name__=='__main__':
    main()
