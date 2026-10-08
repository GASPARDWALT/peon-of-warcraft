#!/usr/bin/env python3
"""Fixed native HUD: normal intro, crowds, scrolling, wounds and UI returns.

Only the separately labeled capacity/HP-bound diagnostics edit emulator RAM
and restore a private savestate. The normal playable route uses ordinary input.
Published outputs and personal batteries are never modified.
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
import validate_durotar_v022_quests as game
import run_peon_v023_validation as adapter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/deep_polish/hud'
BINARY = (ROOT / 'gfx/pack/peon_player_hud.2bpp').read_bytes()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode_tile(data):
    return np.array([[(data[y*2] >> (7-x) & 1) |
                      (data[y*2+1] >> (7-x) & 1) << 1 for x in range(8)]
                     for y in range(8)], dtype='uint8')


class HUDSession(ApproachSession):
    def __init__(self, rom, sym):
        self.helper_entries = []
        self.helper_returns = 0
        self.checked_loads = 0
        self.verify_helpers = False
        self.diagnostic = None
        self.hook_errors = []
        self.compaction_cases = set()
        self.active_hud_shapes = set()
        self.visibility_counts = {"rendered":0,"hidden_to_preserve_native_budget":0}
        self.omission_cases = {}
        super().__init__(rom, sym)
        self.p.hook_register(*sym['PeonDrawPlayerHUD'], lambda data:self.safe_hook(self.enter,data), None)
        bank, address = sym['PeonDrawPlayerHUD.done']
        self.p.hook_register(bank, address+4, lambda data:self.safe_hook(self.leave,data), None)
        bank, address = sym['PeonLoadPlayerHUDGFX.done']
        self.p.hook_register(bank, address+4, lambda data:self.safe_hook(self.loaded,data), None)

    def read(self, name, length=1):
        return super().read(name,length) if length else []

    def safe_hook(self, callback, data):
        # PyBoy prints and suppresses callback exceptions; retain them and
        # explicitly fail the validator so a callback failure cannot pass.
        try:
            callback(data)
        except Exception as error:
            self.hook_errors.append({'helper':callback.__name__,'error':repr(error)})

    def world_hud_active(self):
        return (self.read('wPartyCount')[0]!=0 and not self.read('wStateFlags')[0]&66
            and self.read('wBattleMode')==[0] and self.read('wScriptMode')==[0]
            and self.read('wMapTileset')==[37] and self.read('hCGB')!=[0])

    def write(self, name, values):
        bank, address = self.sym[name]
        for i, value in enumerate(values):
            if address >= 0xe000:
                self.p.memory[address+i] = value
            else:
                self.p.memory[bank,address+i] = value

    def registers(self):
        return {name:getattr(self.p.register_file,name) for name in ('A','F','B','C','D','E','HL','SP')}

    def protected(self):
        return {'tilemap':self.read('wTilemap',360), 'attrmap':self.read('wAttrmap',360),
            'event_flags':self.read('wEventFlags',256), 'party':self.read('wPartyMon1',256),
            'bg_pal1':self.read('wBGPals1',64), 'bg_pal2':self.read('wBGPals2',64),
            'obj_pal1':self.read('wOBPals1',64), 'obj_pal2':self.read('wOBPals2',64),
            'vbk':self.p.memory[0xff4f], 'wram_bank':self.p.memory[0xff70],
            'lcdc':self.p.memory[0xff40], 'scroll':[self.p.memory[0xff42],self.p.memory[0xff43]]}

    def enter(self, _):
        if self.diagnostic and not self.diagnostic.get('entered'):
            self.write('hUsedSpriteIndex',[self.diagnostic['slots']*4])
            self.write('wShadowOAM',self.diagnostic.get('world_oam', [80,80,1,8]*self.diagnostic['slots']))
            if 'hp' in self.diagnostic:
                self.write('wPartyMon1HP',list(self.diagnostic['hp'].to_bytes(2,'big')))
                self.write('wPartyMon1MaxHP',list(self.diagnostic['max_hp'].to_bytes(2,'big')))
            self.diagnostic['entered'] = True
        if self.verify_helpers:
            used = self.read('hUsedSpriteIndex')[0]
            self.helper_entries.append({'registers':self.registers(), 'protected':self.protected(),
                'used':used, 'actor_prefix':self.read('wShadowOAM',used)})

    def leave(self, _):
        if self.verify_helpers:
            entry = self.helper_entries.pop()
            assert self.registers() == entry['registers'], 'HUD changed CPU registers'
            assert self.protected() == entry['protected'], 'HUD changed game/UI/palette state'
            total = self.read('hUsedSpriteIndex')[0]
            before = [entry['actor_prefix'][i:i+4] for i in range(0,entry['used'],4)]
            active = self.world_hud_active()
            retained = [row for row in before if not active or
                (8<row[0]<160 and 0<row[1]<168)]
            prefix = [value for row in retained for value in row]
            added = total-len(prefix)
            if active:
                self.active_hud_shapes.add(added//4)
                if self.diagnostic is None:
                    self.visibility_counts['rendered' if added else 'hidden_to_preserve_native_budget'] += 1
                    if not added:
                        maximum_row = max(sum(row[0] <= scanline < row[0]+8 for row in retained)
                                          for scanline in range(19,27))
                        case = (self.map(),*self.position(),len(retained),maximum_row)
                        self.omission_cases[case] = self.omission_cases.get(case,0)+1
            assert added in (0,16), ('Unexpected HUD size',added)
            assert self.read('wShadowOAM',total)[added:] == prefix, 'HUD lost/reordered a visible world object'
            assert total <= 160, 'HUD exceeded40hardwareobjects'
            if len(prefix)<entry['used']:
                self.compaction_cases.add((self.map(),*self.position(),entry['used']//4,len(prefix)//4,added//4))
            self.helper_returns += 1
        if self.diagnostic and self.diagnostic.get('entered') and not self.diagnostic.get('done'):
            self.diagnostic['after_slots'] = self.read('hUsedSpriteIndex')[0]//4
            self.diagnostic['oam'] = self.read('wShadowOAM',160)
            self.diagnostic['done'] = True

    def loaded(self, _):
        if self.read('wMapTileset') != [37]:
            return
        assert bytes(self.p.memory[0,0x8600:0x86e0]) == BINARY, 'HUD graphics were not reloaded'
        used = self.read('wUsedSprites',64)
        for i in range(0,64,2):
            sprite, tile = used[i:i+2]
            if not sprite:
                break
            if tile & 128:
                length = 4 if sprite in (53,54,60,253,254,255) else 32 if sprite in (1,63) else 12
                assert (tile & 127)+length <= 96, ('Standing sprites overlap HUD VRAM',sprite,tile,length)
        self.checked_loads += 1

    def capture(self, name):
        self.p.screen.image.save(OUT/(name+'_in_rom.png'))
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(OUT/(name+'_in_rom_4x.png'))
        print(name,self.map(),self.position(),'HP',self.read('wPartyMon1HP',2),flush=True)

    def hud_objects(self):
        # A tick may stop halfway through native sprite composition. Observe
        # the completed OAM publication, not an in-progress shadow buffer.
        for _ in range(60):
            hardware = list(self.p.memory[0xfe00:0xfea0])
            if (hardware == self.read('wShadowOAM',160) and not self.helper_entries
                    and (self.read('hOAMUpdate')==[0] or not self.world_hud_active())):
                break
            self.p.tick(1,True)
        assert (hardware == self.read('wShadowOAM',160) and not self.helper_entries
                and (self.read('hOAMUpdate')==[0] or not self.world_hud_active())), 'No completed hardware OAM publication'
        return [hardware[i:i+4] for i in range(0,160,4)
                if hardware[i] < 160 and 96 <= hardware[i+2] < 110 and not hardware[i+3] & 8]

    def check(self, label, pixels=True, require=True):
        self.p.tick(90,True)
        assert not self.hook_errors, self.hook_errors
        assert self.read('wScriptMode') == [0]
        objects = self.hud_objects()
        if not objects:
            assert not require, ('HUD absent',label,self.read('hUsedSpriteIndex'),self.read('wStateFlags'))
            self.capture(label)
            return {'temporarily_hidden_to_preserve_crowded_world':True}
        assert len(objects) == 4, (label,len(objects))
        assert objects[0] == [19,10,100,2], ('HUD anchor changed',label,objects[0])
        width = 24
        hp = int.from_bytes(bytes(self.read('wPartyMon1HP',2)),'big')
        max_hp = int.from_bytes(bytes(self.read('wPartyMon1MaxHP',2)),'big')
        fill = max(1,min(width,width*hp//max_hp)) if hp and max_hp else 0
        remaining = fill
        actual_gauge = objects[1:]
        expected_gauge = []
        for n in range(width//8):
            amount = min(8,remaining); remaining -= amount
            expected_gauge.append([19,20+8*n,101+amount,0])
        assert actual_gauge == expected_gauge, (label,'HP gauge does not track actual HP',actual_gauge,expected_gauge)
        if pixels:
            colors = self.read('wOBPals2',64)
            screen = np.asarray(self.p.screen.image.convert('RGB')) >> 3
            for y,x,tile,attr in objects:
                decoded = decode_tile(BINARY[(tile-96)*16:(tile-95)*16])
                values = colors[(attr&7)*8:(attr&7)*8+8]
                palette = np.array([[(word&31),(word>>5&31),(word>>10&31)]
                    for i in range(0,8,2) for word in [values[i]|values[i+1]<<8]],dtype='uint8')
                mask = decoded != 0
                rendered = screen[y-16:y-8,x-8:x]
                assert np.array_equal(rendered[mask],palette[decoded][mask]), (label,'Actual HUD pixels differ',tile)
        self.capture(label)
        return {'oam_objects':len(objects),'hp':hp,'max_hp':max_hp,'gauge_width':width,'filled_pixels':fill,
                'native_vram_matches':bytes(self.p.memory[0,0x8600:0x86e0])==BINARY,
                'actual_hardware_oam_and_live_hp_match':True,'opaque_pixels_match_rgb555':pixels}


def main():
    logging.disable(logging.CRITICAL); OUT.mkdir(parents=True,exist_ok=True)
    preserved = published_snapshot()
    for module in adapter.local_dependencies(game):
        for name in ('OUT','OUTPUT'):
            if hasattr(module,name):setattr(module,name,OUT)
        adapter.adapt_v023_gameplay(module)
    syms = game.load_symbols(); rom_sha = sha(ROOT/'pokecrystal.gbc')
    report = {'rom_sha256':rom_sha,'ordinary_button_route':{},'diagnostics':{},'all_checks_passed':False,
        'save_layout_changed':False,'mana_system_added':False,
        'scope':'Fixed 34x8 native portrait/life HUD at (2,3); actual gameplay and explicit capacity/scanline/HP boundary diagnostics.',
        'fixed_panel_ink_bounds':[2,3,36,11], 'resize_with_crowd':False,
        'diagnostic_lifetimes':'Capacity/scanline/HP fixtures are isolated and restored before continuing normal gameplay.'}
    s = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-hud-') as folder:
            rom = Path(folder)/'test.gbc';shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
            s = HUDSession(rom,syms);s.verify_helpers = True;s.fresh()
            report['ordinary_button_route']['normal_spawn'] = s.check('hud_normal_spawn')
            # Paired native render: the only diagnostic is the usual text/UI
            # guard bit, which disables the HUD and its offscreen compaction.
            # Compare the whole actual screen outside the small HUD rectangle.
            spawn = io.BytesIO();s.p.save_state(spawn)
            s.verify_helpers = False
            s.p.tick(120,True);s.hud_objects()
            with_hud = np.asarray(s.p.screen.image.convert('RGB')).copy()
            native_progress = s.snapshot()
            spawn.seek(0);s.p.load_state(spawn)
            s.write('wStateFlags',[s.read('wStateFlags')[0]|64])
            s.p.tick(120,True);assert not s.hud_objects()
            without_hud = np.asarray(s.p.screen.image.convert('RGB')).copy()
            mask = np.ones((144,160),dtype=bool);mask[3:11,2:36] = False
            assert np.array_equal(with_hud[mask],without_hud[mask]), 'HUD changed visible native NPC/map pixels outside its rectangle'
            assert s.snapshot()==native_progress,'HUD guard fixture altered persistent player progress'
            report['diagnostics']['normal_spawn_native_world_pixels'] = {
                'explicit_emulator_guard_fixture':True,'all_actual_pixels_outside_hud_identical':True,
                'persistent_player_progress_identical':True,'hud_rectangle_excluded':[2,3,36,11]}
            spawn.seek(0);s.p.load_state(spawn);s.verify_helpers = True;s.p.tick(90,True)
            s.navigate((9,6));report['ordinary_button_route']['fresh_camp'] = s.check('hud_den_vendor_camp')
            for xy in ((10,12),(8,12),(4,16)):
                s.navigate(xy);report['ordinary_button_route'][str(xy)] = s.check(f'hud_den_x{xy[0]}_y{xy[1]}',pixels=True,require=False)
            s.navigate((10,10));s.press('up',30);s.press('a',90)
            assert s.read('wStateFlags')[0] & 64
            assert not s.hud_objects(), 'HUD leaked into speaker dialogue'
            s.capture('dialogue_without_player_hud');s.close_dialogue()
            assert s.event('EVENT_PEON_QUEST_ACCEPTED')
            s.navigate((18,13));s.press('up',30);s.press('a')
            s.fight('ordinary_boar','EVENT_PEON_QUEST_DONE')
            s.navigate((12,9));wounds = s.check('hud_after_normal_combat')
            assert 0 < wounds['hp'] < wounds['max_hp'];report['ordinary_button_route']['wounds'] = wounds
            s.rest();s.navigate((9,6));healed = s.check('hud_after_inn_healing')
            assert healed['hp'] == healed['max_hp'];report['ordinary_button_route']['inn_healed'] = healed
            s.press('start',120);assert not s.hud_objects(),'HUD leaked into main menu'
            s.capture('menu_without_player_hud');s.press('b',120)
            report['ordinary_button_route']['menu_return'] = s.check('hud_after_menu_return')
            s.press('select',120);assert not s.hud_objects(),'HUD leaked into map interface'
            s.capture('map_locked_without_player_hud');s.press('b',120)
            report['ordinary_button_route']['map_return'] = s.check('hud_after_map_return')
            baseline = io.BytesIO();s.p.save_state(baseline)
            for label,fixture in {
                'capacity32':{'slots':32}, 'capacity36':{'slots':36},
                'capacity_actor_priority38':{'slots':38},
                'scanline_six_safe':{'slots':24,'world_oam':[19,80,1,8]*6+[80,80,1,8]*18},
                'scanline_seven_preserve_actors':{'slots':24,'world_oam':[19,80,1,8]*7+[80,80,1,8]*17,'hide':True},
                'disjoint_rows_union_seven_safe':{'slots':24,'world_oam':[12,80,1,8]*3+[26,80,1,8]*4+[80,80,1,8]*17}, 'zero_hp':{'slots':24,'hp':0,'max_hp':31},
                'one_hp':{'slots':24,'hp':1,'max_hp':31}, 'half_hp':{'slots':24,'hp':16,'max_hp':32},
                'zero_maximum':{'slots':24,'hp':0,'max_hp':0}, 'clamped_hp':{'slots':24,'hp':40,'max_hp':32},
                'clamped_far_above_maximum':{'slots':24,'hp':1000,'max_hp':32},
                'full_16bit_hp':{'slots':24,'hp':65535,'max_hp':65535},
                'near_maximum_16bit_hp':{'slots':24,'hp':65534,'max_hp':65535},
                'half_16bit_hp':{'slots':24,'hp':32767,'max_hp':65535},
            }.items():
                baseline.seek(0);s.p.load_state(baseline);s.diagnostic = fixture
                for _ in range(20):
                    s.p.tick(1,True)
                    if fixture.get('done'):break
                assert fixture.get('done'),label
                assert not s.hook_errors,s.hook_errors
                expected = fixture['slots']+(4 if fixture['slots']<=36 and not fixture.get('hide') else 0)
                assert fixture['after_slots'] == expected,(label,fixture,expected)
                added = expected-fixture['slots']
                if added:
                    width = 24
                    hp = fixture.get('hp',15); maximum = fixture.get('max_hp',15)
                    fill = max(1,min(width,width*hp//maximum)) if hp and maximum else 0
                    start = 4
                    rows = [fixture['oam'][i:i+4] for i in range(start,added*4,4)]
                    desired = []
                    for part in range(width//8):
                        amount = min(8,fill);fill -= amount
                        desired.append([19,20+part*8,101+amount,0])
                    assert rows==desired,(label,'Diagnostic gauge fill differs',rows,desired)
                report['diagnostics'][label] = {key:value for key,value in fixture.items() if key not in ('oam','world_oam')}
                report['diagnostics'][label]['explicit_emulator_fixture'] = True
                s.diagnostic = None
                # Finish any subsequent native render before restoring a
                # private state; Python hook stacks are not savestate data.
                s.hud_objects()
            baseline.seek(0);s.p.load_state(baseline);s.p.tick(90,True)
            report['all_active_hud_shapes_including_walking'] = sorted(s.active_hud_shapes)
            assert s.active_hud_shapes <= {0,4}, 'HUD resized during walking'
            report['ordinary_world_visibility_counts'] = s.visibility_counts
            report['ordinary_safe_omission_cases'] = [dict(zip(
                ('map','x','y','retained_world_objects','most_world_objects_on_hud_row','refreshes'),(*case,count)))
                for case,count in sorted(s.omission_cases.items())]
            report['helper_register_and_palette_checks'] = s.helper_returns
            report['sprite_allocation_and_reload_checks'] = s.checked_loads
            report['offscreen_compaction_cases'] = [dict(zip(
                ('map','x','y','world_objects_before','visible_objects_retained','hud_objects'),case))
                for case in sorted(s.compaction_cases)]
            assert not s.hook_errors,s.hook_errors
            assert s.helper_returns > 100 and s.checked_loads > 2
            assert sha(ROOT/'pokecrystal.gbc') == rom_sha,'Root ROM changed while testing'
            assert preserved == published_snapshot(),'Published outputs changed'
            report['all_checks_passed'] = True;s.p.stop(save=False);s = None
    except Exception as error:
        report['failure'] = repr(error)
        if s is not None:s.capture('unexpected_state');s.p.stop(save=False)
        (OUT/'native_validation.json').write_text(json.dumps(report,indent=2)+'\n');raise
    (OUT/'native_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
