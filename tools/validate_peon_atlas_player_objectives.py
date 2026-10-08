#!/usr/bin/env python3
"""Actual native atlas: current player, accepted objectives, fog and return.

The first route uses only normal buttons, including earning the map and
completing Lazy Peons/Cactus Surprise. Explicit diagnostic savestate branches
cover boss flags, undiscovered pages and projection bounds. Published outputs
are read-only; every new capture/report belongs to valley_layout_update/atlas.
"""
from pathlib import Path
import hashlib
import io
import json
import logging
import shutil
import tempfile

import numpy as np
from PIL import Image

from validate_peon_cave_approach import ApproachSession, published_snapshot
from validate_peon_villages import load_symbols, MAPS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/valley_layout_update/atlas'
GEOMETRY = json.loads((OUT / 'geometry_manifest.json').read_text())
QUESTS = json.loads((ROOT / 'references/generated/durotar_v022/quest_markers/manifest.json').read_text())
REGIONS = list(GEOMETRY['pages'])
GLYPHS = ((ROOT / 'gfx/pack/peon_quest_poi.2bpp').read_bytes()
          + (ROOT / 'gfx/pack/peon_atlas_avatar.2bpp').read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode_tile(binary):
    pixels = np.zeros((8, 8), dtype='uint8')
    for y in range(8):
        lo, hi = binary[2*y:2*y+2]
        for x in range(8):
            pixels[y, x] = ((lo >> (7-x)) & 1) | (((hi >> (7-x)) & 1) << 1)
    return pixels


def palette(data):
    return np.array([[(word & 31), (word >> 5) & 31, (word >> 10) & 31]
                     for i in range(0, len(data), 2)
                     for word in [data[i] | data[i+1] << 8]], dtype='uint8')


def background(binary):
    assert len(binary) == 6544
    result = np.zeros((144, 160, 3), dtype='uint8')
    colors = palette(binary[6480:6544]).reshape(8, 4, 3)
    for i in range(360):
        number, attr = binary[5760+i], binary[6120+i]
        # Signed addressing: bank0 lower 128, bank0 upper 128, then bank1.
        index = (256 + number) if attr & 8 else number
        pixels = decode_tile(binary[index*16:(index+1)*16])
        if attr & 0x20: pixels = pixels[:, ::-1]
        if attr & 0x40: pixels = pixels[::-1]
        y, x = divmod(i, 20)
        result[y*8:y*8+8, x*8:x*8+8] = colors[attr & 7][pixels]
    return result


def projected(region, xy):
    page = GEOMETRY['pages'][region]
    x, y = xy
    if not (0 <= x < page['collision_size'][0] and 0 <= y < page['collision_size'][1]):
        return None
    return [page['y_centers'][y]+12, page['x_centers'][x]+4]


class AtlasSession(ApproachSession):
    def __init__(self, rom, sym):
        self.atlas_calls = []
        super().__init__(rom, sym)
        self.p.hook_register(*self.sym['PeonDrawAtlasQuests'], self.entering, None)
        bank, addr = self.sym['PeonDrawAtlasQuests.done']
        self.p.hook_register(bank, addr+4, self.returning, None)

    def capture(self, name):
        self.p.screen.image.save(OUT / (name+'.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / (name+'_4x.png'))
        print(name, 'map', self.map(), 'position', self.position(), flush=True)

    def registers(self):
        return {name: getattr(self.p.register_file, name) for name in ('A','F','B','C','D','E','HL','SP')}

    def background_vram(self):
        return [bytes(self.p.memory[0, 0x8800:0x9800]), bytes(self.p.memory[1, 0x9000:0x9680])]

    def entering(self, _):
        self.atlas_calls.append({'registers': self.registers(), 'vbk': self.p.memory[0xff4f] & 1,
            'wram_bank': self.p.memory[0xff70] & 7, 'lcdc': self.p.memory[0xff40],
            'scroll': [self.p.memory[0xff42], self.p.memory[0xff43]],
            'oam_update': self.read('hOAMUpdate'), 'events': self.read('wEventFlags', 256),
            'background_vram': self.background_vram(),
            'bg_palettes': [self.read('wBGPals1',64), self.read('wBGPals2',64)],
            'obj_palettes_0_to_5': [self.read('wOBPals1',48), self.read('wOBPals2',48)]})

    def returning(self, _):
        state = self.atlas_calls[-1]
        assert state['registers'] == self.registers(), 'Atlas helper altered CPU registers'
        assert state['vbk'] == self.p.memory[0xff4f] & 1, 'VRAM bank leaked'
        assert state['wram_bank'] == self.p.memory[0xff70] & 7, 'WRAM bank leaked'
        assert state['lcdc'] == self.p.memory[0xff40], 'LCD mode altered'
        assert state['scroll'] == [self.p.memory[0xff42],self.p.memory[0xff43]], 'Scroll altered'
        assert state['oam_update'] == self.read('hOAMUpdate'), 'OAM update guard leaked'
        assert state['events'] == self.read('wEventFlags',256), 'Atlas wrote persistent event flags'
        assert state['background_vram'] == self.background_vram(), 'Atlas overlay corrupted native BG'
        assert state['bg_palettes'] == [self.read('wBGPals1',64),self.read('wBGPals2',64)]
        assert state['obj_palettes_0_to_5'] == [self.read('wOBPals1',48),self.read('wOBPals2',48)]
        state['verified'] = True

    def expected(self, region):
        entries, descriptions = [], []
        if not self.event('EVENT_PEON_DISCOVERED_'+region):
            return entries, descriptions
        page = GEOMETRY['pages'][region]['page']
        point = None
        if self.read('wMapGroup') == [26] and self.map() == page+14:
            point = projected(region, self.position())
            meaning = 'actual current map movement cell'
        elif self.read('wMapGroup') == [26] and 21 <= self.map() <= 24:
            owner, warp = self.read('wBackupMapNumber')[0], self.read('wBackupWarpNumber')[0]
            if self.read('wBackupMapGroup') == [26] and owner == page+14:
                doors = [door for door in GEOMETRY['doors'] if
                         (door['room'],door['map'],door['warp']) == (self.map(),owner,warp)]
                if doors:
                    assert len(doors) == 1
                    point = projected(region, doors[0]['xy'])
                    meaning = 'exact exterior return door while inside linked room'
        if point:
            entries.append([*point,2,6]); descriptions.append({'type':'player','meaning':meaning})
        # Original giver states retain original ordering and coordinates.
        for key, giver in QUESTS['points'].items():
            if giver['region'] != region or self.event(giver['complete_flag']):
                continue
            ready = all(self.event(flag) for flag in giver['ready_all_flags'])
            state = 'offered' if not self.event(giver['accepted_flag']) else 'ready' if ready else 'active'
            style = QUESTS['state_styles'][state]
            assert projected(region, giver['collision_coordinate']) == giver['oam_yx']
            entries.append([*giver['oam_yx'],style['tile'],style['palette']])
            descriptions.append({'type':'questgiver','identity':key,'state':state})
        def objective(key):
            point = projected(region, GEOMETRY['objectives'][key]['xy'])
            assert point is not None
            entries.append([*point,0,4]); descriptions.append({'type':'objective','identity':key})
        def active(accepted, done):
            return self.event('EVENT_PEON_'+accepted) and not self.event('EVENT_PEON_'+done)
        if region == 'DEN' and active('LAZY_ACCEPTED','LAZY_DONE') and not self.event('EVENT_PEON_LAZY_AWAKE'):
            objective('LAZY')
        if region == 'VALLEY':
            if active('CACTUS_ACCEPTED','CACTUS_DONE'):
                for number in (1,2,3):
                    if not self.event('EVENT_PEON_CACTUS_'+str(number)):
                        objective('CACTUS'+str(number))
            if active('SARKOTH_ACCEPTED','SARKOTH_DONE') and not self.event('EVENT_PEON_SARKOTH_DEAD'):
                objective('SARKOTH')
        if active('MEDALLION_ACCEPTED','MEDALLION_DONE') and not self.event('EVENT_PEON_YARROG_DEAD'):
            if region == 'VALLEY': objective('CAVE_ENTRANCE')
            if region == 'CAVERN': objective('YARROG')
        return entries, descriptions

    def check_atlas(self, label, records, region=None, diagnostic=False):
        self.p.tick(60, True)
        before = {'map':self.read('wMapGroup',2),'xy':self.position(),
                  'events':self.read('wEventFlags',256),
                  'palettes':[self.read('wOBPals1',64),self.read('wOBPals2',64)]}
        world_before = self.restored_world() if not diagnostic else None
        first = len(self.atlas_calls)
        self.press('select',180)
        if region is None:
            region = REGIONS[self.read('wMenuCursorY')[0]]
        wanted = GEOMETRY['pages'][region]['page']
        for _ in range(7):
            current = self.read('wMenuCursorY')[0]
            if current == wanted: break
            self.press('right',120)
        assert self.read('wMenuCursorY') == [wanted]
        self.p.tick(30,True)
        assert len(self.atlas_calls)>first and all(row.get('verified') for row in self.atlas_calls[first:])
        fog = not self.event('EVENT_PEON_DISCOVERED_'+region)
        native_name = 'fog' if fog else region.lower()
        binary = (ROOT/'gfx/peon_maps'/(native_name+'.bin')).read_bytes()
        assert bytes(self.p.memory[0,0x9000:0x9800]) == binary[:2048]
        assert bytes(self.p.memory[0,0x8800:0x9000]) == binary[2048:4096]
        assert bytes(self.p.memory[1,0x9000:0x9680]) == binary[4096:5760]
        hardware = list(self.p.memory[0xfe00:0xfea0])
        assert hardware == self.read('wShadowOAM',160), 'Shadow OAM was not submitted'
        visible = [hardware[i:i+4] for i in range(0,160,4)
                   if 0 < hardware[i] < 160 and 0 < hardware[i+1] < 168]
        expected, descriptions = self.expected(region)
        assert visible == expected, (label,'Actual hardware OAM differs',visible,expected)
        assert len(visible) <= 9, 'Overlay unexpectedly exceeds reserved sprite count'
        counts = [sum(e[0]-16 <= y < e[0]-8 for e in visible) for y in range(144)]
        assert max(counts,default=0) <= 10, 'More than ten OBJ tiles on one scanline'
        pixels = background(binary)
        if not fog:
            assert bytes(self.p.memory[0,0x8000:0x8030]) == GLYPHS
            assert self.p.memory[0xff40] & 2 and not self.p.memory[0xff40] & 4
            actual_pal = palette(self.read('wOBPals1',64)).reshape(8,4,3)
            assert actual_pal[4].tolist() == QUESTS['gold_palette_rgb555']
            assert actual_pal[7].tolist() == QUESTS['gray_palette_rgb555']
            assert actual_pal[6].tolist() == GEOMETRY['avatar']['rgb555']
            # In native CGB OAM priority the first sprite wins overlapping pixels.
            for y,x,tile,attr in reversed(expected):
                top, left = y-16, x-8
                assert 0 <= top <= 136 and 0 <= left <= 152, (label,'Clipped point',y,x)
                glyph = decode_tile(GLYPHS[tile*16:(tile+1)*16]); opaque = glyph != 0
                pixels[top:top+8,left:left+8][opaque] = actual_pal[attr&7][glyph][opaque]
        actual = np.asarray(self.p.screen.image.convert('RGB')) >> 3
        assert np.array_equal(actual,pixels), (label,'Rendered RGB555 differs',int(np.any(actual!=pixels,axis=-1).sum()))
        self.capture(label)
        self.press('b',180); self.p.tick(60,True)
        assert self.read('wMapGroup',2) == before['map'] and self.position() == before['xy']
        assert self.read('wScriptMode') == [0]
        assert self.read('wEventFlags',256) == before['events']
        assert [self.read('wOBPals1',64),self.read('wOBPals2',64)] == before['palettes'], (label,'Temporary atlas palette leaked into world')
        if world_before is not None:
            world_after = self.restored_world()
            for field in world_before:
                assert world_before[field] == world_after[field], (label,'Active world/font/sprite data not restored',field)
            expected_font = bytes(c for value in (ROOT/'gfx/font/font.1bpp').read_bytes() for c in (value,value))
            assert bytes(self.p.memory[0,0x8800:0x9000]) == expected_font, 'Standard font did not reload'
            assert bytes(self.p.memory[0,0x97f0:0x9800]) == bytes(16), 'Space glyph did not reload'
            if 'PeonDrawPlayerHUD' in self.sym:
                assert bytes(self.p.memory[0,0x8600:0x86e0]) == (ROOT/'gfx/pack/peon_player_hud.2bpp').read_bytes(), 'Native player HUD graphics not restored'
        record = {'name':label,'diagnostic_ram_edits_or_savestate':diagnostic,'region':region,
            'current_map':before['map'],'current_xy':list(before['xy']),'fog':fog,
            'hardware_oam':visible,'points':descriptions,'pixel_exact_rgb555':True,
            'background_vram_preserved':True,'cpu_banks_lcd_scroll_events_preserved':True,
            'world_palette_and_location_restored':True,'max_sprites_per_scanline':max(counts,default=0)}
        record['world_font_terrain_npc_graphics_bg_attributes_restored'] = world_before is not None
        records.append(record)
        return record

    def set_flag(self,name,value=True):
        index = self.flags[name]; bank,address = self.sym['wEventFlags']; address += index//8
        old = self.p.memory[bank,address]
        self.p.memory[bank,address] = old | (1 << (index%8)) if value else old & ~(1 << (index%8))

    def restored_world(self):
        # Only active world/font ranges: unused portrait/menu caches are not
        # claimed to be restored. Allocated standing and walking sprites are.
        graphics = []
        used = self.read('wUsedSprites',64)
        table_bank,table_address = self.sym['OverworldSprites']
        for i in range(0,len(used),2):
            identity,tile = used[i:i+2]
            if not identity: break
            resolved = identity
            seen = set()
            while resolved >= 0xf0:
                assert resolved not in seen, 'Cyclic variable sprite alias'
                seen.add(resolved)
                resolved = self.read('wVariableSprites',16)[resolved-0xf0]
            assert resolved, ('Unresolved variable sprite',identity)
            record = list(self.p.memory[table_bank,table_address+(resolved-1)*6:table_address+resolved*6])
            size = record[2] or 256 # Peon's special sixteen-tile standing pose.
            bank,address = (0 if tile & 128 else 1), 0x8000+(tile & 127)*16
            reserved = 512 if record[4] == 0 else size
            if bank == 0 and 'PeonDrawPlayerHUD' in self.sym:
                assert address + reserved <= 0x8600, ('World sprite allocation overlaps native HUD',identity,tile,reserved)
            walking = bytes(self.p.memory[bank,address+0x800:address+0x800+reserved]) if record[4] in (0,1) else None
            graphics.append((identity,tile,bytes(self.p.memory[bank,address:address+size]),walking))
        active_palettes = sorted({attr & 7 for attr in self.read('wAttrmap',360)})
        return {'terrain': [bytes(self.p.memory[0,0x9000:0x9600]),bytes(self.p.memory[1,0x9000:0x9600])],
                'tilemap':self.read('wTilemap',360),'attributes':self.read('wAttrmap',360),
                'active_bg_palettes':[[self.read(variable,64)[i*8:i*8+8] for i in active_palettes]
                                      for variable in ('wBGPals1','wBGPals2')],
                'player_hud_graphics':bytes(self.p.memory[0,0x8600:0x86e0]) if 'PeonDrawPlayerHUD' in self.sym else None,
                'allocated_sprite_graphics':graphics}


def main():
    logging.disable(logging.CRITICAL); OUT.mkdir(parents=True,exist_ok=True)
    published = published_snapshot()
    report = {'rom_sha256':digest(ROOT/'pokecrystal.gbc'),'all_checks_passed':False,
              'emulator':'PyBoy 2.7.0','normal_route_method':'Ordinary buttons only; real quest rewards, walking and warps; no RAM edits or emulator states loaded before the diagnostic section.',
              'diagnostic_method':'Explicit isolated event/coordinate fixtures and emulator states after the normal route.',
              'normal_route':[],'diagnostic_cases':[],'ordinary_map_reward_and_quests':{},
              'limitations':GEOMETRY['limitations']+['Physical Chromatic has not been tested.']}
    s = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-atlas-objectives-') as directory:
            rom = Path(directory)/'test.gbc'; shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
            s = AtlasSession(rom,load_symbols()); s.fresh()
            assert not s.event('EVENT_PEON_MAP_RECEIVED')
            calls = len(s.atlas_calls); s.press('select',180); s.capture('normal_map_locked_before_reward')
            s.press('a',120); s.press('b',120)
            assert len(s.atlas_calls) == calls, 'Unearned map revealed atlas points'
            s.talk((10,10),'up','normal_gornek_first_quest')
            loads = s.encounter_loads; s.navigate((18,13)); s.press('up',30); s.press('a')
            report['ordinary_map_reward_and_quests']['boar'] = s.fight('normal_boar','EVENT_PEON_QUEST_DONE',baseline=loads)
            s.talk((10,10),'up','normal_gornek_second_quest'); s.rest()
            loads = s.encounter_loads; s.navigate((17,15))
            report['ordinary_map_reward_and_quests']['scorpid'] = s.fight('normal_scorpid','EVENT_PEON_SCORPID_DEFEATED',baseline=loads)
            s.talk((10,10),'up','normal_gornek_map_reward'); s.rest()
            assert s.event('EVENT_PEON_MAP_RECEIVED')
            report['ordinary_map_reward_and_quests']['earned_map_with_normal_buttons'] = True
            normal = report['normal_route']; diag = report['diagnostic_cases']; map_states = {}
            def retain_map():
                state = io.BytesIO(); s.p.save_state(state); map_states[s.map()] = state
            s.check_atlas('normal_den_player',normal)
            s.navigate((12,9)); s.check_atlas('normal_den_player_walked',normal)
            retain_map()
            s.check_atlas('normal_valley_undiscovered',normal,'VALLEY')
            s.talk((8,13),'down','normal_lazy_accept')
            a = s.check_atlas('normal_lazy_sleeping_objective',normal)
            assert any(p.get('identity')=='LAZY' for p in a['points'])
            s.talk((5,17),'up','normal_lazy_wake')
            a = s.check_atlas('normal_lazy_ready_objective_removed',normal)
            assert not any(p.get('identity')=='LAZY' for p in a['points'])
            assert any(p.get('state')=='ready' for p in a['points'])
            s.talk((8,16),'up','normal_lazy_turn_in')
            s.check_atlas('normal_lazy_completed',normal)
            s.navigate((17,5),expected_map=23)
            a = s.check_atlas('normal_den_inn_exact_exterior_door',normal)
            inn = io.BytesIO(); s.p.save_state(inn)
            assert a['hardware_oam'][0] == [*projected('DEN',(17,5)),2,6]
            s.walk('left'); b = s.check_atlas('normal_den_inn_indoor_walk_same_door',normal)
            assert b['hardware_oam'][0] == a['hardware_oam'][0]
            s.navigate((5,7),expected_map=14)
            s.navigate((5,7),expected_map=22)
            a = s.check_atlas('normal_den_hut_exact_exterior_door',normal)
            assert a['hardware_oam'][0] == [*projected('DEN',(5,7)),2,6]
            s.navigate((5,7),expected_map=14); s.to_valley()
            s.talk((8,11),'up','normal_galgar_accept')
            a = s.check_atlas('normal_cactus_three_objectives',normal)
            assert sum(p.get('identity','').startswith('CACTUS') for p in a['points']) == 3
            s.check_atlas('normal_other_page_no_false_player',normal,'DEN')
            for pos,face,num in (((8,7),'left',1),((24,9),'left',2),((10,17),'left',3)):
                s.talk(pos,face,'normal_cactus_'+str(num)+'_harvest')
                assert s.event('EVENT_PEON_CACTUS_'+str(num))
                a = s.check_atlas('normal_cactus_'+str(num)+'_objective_removed',normal)
                assert sum(p.get('identity','').startswith('CACTUS') for p in a['points']) == 3-num
            s.talk((8,11),'up','normal_galgar_turn_in')
            s.check_atlas('normal_cactus_complete_giver_removed',normal)
            s.talk((10,20),'up','normal_hanazua_accept'); s.talk((5,11),'right','normal_zureetha_accept')
            a = s.check_atlas('normal_boss_and_cave_entrance_objectives',normal)
            assert {'SARKOTH','CAVE_ENTRANCE'} <= {p.get('identity') for p in a['points']}
            valley = io.BytesIO(); s.p.save_state(valley)
            retain_map()
            # The new narrow exterior corridor requires its two actual guards.
            # Win with ordinary controls, resting deliberately between fights.
            report['ordinary_map_reward_and_quests']['exterior_imps'] = []
            for number,(position,flag) in enumerate((((24,6),'EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD'),
                                                      ((26,9),'EVENT_PEON_CAVE_APPROACH_IMP_2_DEAD')),1):
                loads = s.encounter_loads; s.navigate(position)
                result = s.fight('normal_exterior_imp_'+str(number),flag,30,baseline=loads)
                report['ordinary_map_reward_and_quests']['exterior_imps'].append(result)
                s.rest(); s.to_valley()
            # The native cave doorway now remains open; interior actors avoided.
            s.navigate((24,4),expected_map=20)
            a = s.check_atlas('normal_cave_player_and_yarrog_objective',normal)
            assert a['hardware_oam'][0] == [*projected('CAVERN',s.position()),2,6]
            s.navigate((10,15)); s.check_atlas('normal_cave_player_walked',normal)
            cave = io.BytesIO(); s.p.save_state(cave)
            retain_map()
            s.navigate((10,16),expected_map=15); s.check_atlas('normal_cave_return_red_imp_palettes_restored',normal)
            assert s.palette(6) == [(31,31,31),(27,5,3),(31,25,7),(1,1,1)]
            # Real warps reach the remaining pages and every shared-room door.
            s.navigate((28,12),expected_map=16); s.check_atlas('normal_road_actual_player',normal); retain_map()
            s.navigate((12,24),expected_map=17); s.check_atlas('normal_senjin_actual_player',normal); retain_map()
            for number,(xy,room) in enumerate((((5,5),21),((15,5),24),((17,9),21)),1):
                s.navigate(xy,expected_map=room)
                a = s.check_atlas('normal_senjin_room_'+str(number)+'_exact_door',normal)
                assert a['hardware_oam'][0] == [*projected('SENJIN',xy),2,6]
                s.navigate((5,7),expected_map=17)
            s.navigate((10,4),expected_map=16); s.navigate((12,4),expected_map=18)
            s.check_atlas('normal_razor_actual_player',normal); retain_map()
            for number,(xy,room) in enumerate((((5,5),22),((17,5),23),((17,13),22),((5,15),22)),1):
                s.navigate(xy,expected_map=room)
                a = s.check_atlas('normal_razor_room_'+str(number)+'_exact_door',normal)
                assert a['hardware_oam'][0] == [*projected('RAZOR',xy),2,6]
                s.navigate((5,7),expected_map=18)
            s.navigate((12,4),expected_map=19); s.check_atlas('normal_orgrimmar_actual_player',normal); retain_map()
            # Explicit isolated diagnostic branches never masquerade as quest completion.
            valley.seek(0); s.p.load_state(valley)
            for flag in ('EVENT_PEON_CACTUS_1','EVENT_PEON_CACTUS_2','EVENT_PEON_CACTUS_3','EVENT_PEON_CACTUS_DONE'):
                s.set_flag(flag,False)
            a = s.check_atlas('diagnostic_maximum_nine_native_points',diag,diagnostic=True)
            assert len(a['hardware_oam']) == 9
            valley.seek(0); s.p.load_state(valley)
            for flag in ('EVENT_PEON_SARKOTH_DEAD','EVENT_PEON_YARROG_DEAD'): s.set_flag(flag)
            a = s.check_atlas('diagnostic_bosses_dead_ready_givers',diag,diagnostic=True)
            assert not any(p['type']=='objective' for p in a['points'])
            assert sum(p.get('state')=='ready' for p in a['points']) == 2
            for flag in ('EVENT_PEON_SARKOTH_DONE','EVENT_PEON_MEDALLION_DONE'): s.set_flag(flag)
            s.check_atlas('diagnostic_all_valley_quests_completed',diag,diagnostic=True)
            valley.seek(0); s.p.load_state(valley)
            s.set_flag('EVENT_PEON_DISCOVERED_VALLEY',False)
            a = s.check_atlas('diagnostic_fog_hides_player_and_active_objectives',diag,diagnostic=True)
            assert not a['hardware_oam']
            for region in REGIONS:
                state = map_states[GEOMETRY['pages'][region]['map_number']]
                state.seek(0); s.p.load_state(state)
                width,height = GEOMETRY['pages'][region]['collision_size']
                for name,value in [('wXCoord',width-1),('wYCoord',height-1)]:
                    bank,addr = s.sym[name]; s.p.memory[bank,addr] = value
                a = s.check_atlas('diagnostic_'+region.lower()+'_projection_boundary',diag,diagnostic=True)
                assert a['hardware_oam'][0] == [*projected(region,(width-1,height-1)),2,6]
                for name,value in [('wXCoord',width),('wYCoord',height)]:
                    state.seek(0); s.p.load_state(state)
                    bank,addr = s.sym[name]; s.p.memory[bank,addr] = value
                    a = s.check_atlas('diagnostic_'+region.lower()+'_'+name+'_out_of_bounds',diag,diagnostic=True)
                    assert not any(point['type']=='player' for point in a['points'])
            for name,value in [('wBackupWarpNumber',255),('wBackupMapGroup',0)]:
                inn.seek(0); s.p.load_state(inn)
                bank,addr = s.sym[name]; s.p.memory[bank,addr] = value
                a = s.check_atlas('diagnostic_inn_unmatched_'+name,diag,diagnostic=True)
                assert not any(point['type']=='player' for point in a['points'])
            cave.seek(0); s.p.load_state(cave); s.set_flag('EVENT_PEON_YARROG_DEAD')
            a = s.check_atlas('diagnostic_yarrog_dead_cave_objective_removed',diag,diagnostic=True)
            assert [p['type'] for p in a['points']] == ['player']
            # Render at overlap with Sarkoth: player's first OAM slot must win.
            valley.seek(0); s.p.load_state(valley)
            for name,value in zip(('wXCoord','wYCoord'),GEOMETRY['objectives']['SARKOTH']['xy']):
                bank,addr = s.sym[name]; s.p.memory[bank,addr] = value
            s.check_atlas('diagnostic_player_priority_over_objective',diag,diagnostic=True)
            report['helper_returns_verified'] = len(s.atlas_calls)
            s.p.stop(save=False); s = None
        assert published_snapshot() == published, 'Published v0.2.3 or older assets/reports changed'
        report['published_assets_untouched'] = True
        report['all_checks_passed'] = True
    except Exception as exc:
        report['failure'] = repr(exc)
        if s:
            s.capture('unexpected_atlas_state'); s.p.stop(save=False)
        (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
        raise
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: normal atlas reward, projected player, active objectives, exact native pixels and safe return.')


if __name__ == '__main__':
    main()
