#!/usr/bin/env python3
"""Exercise v0.1 through normal buttons and real battery-save restart.

No RAM edits or save states are used to pass the new-game, quest or save flow.
All emulation uses a temporary ROM copy, never a user's save file.
"""
import hashlib
import io
import json
import logging
import shutil
import tempfile
import re
from pathlib import Path
from pyboy import PyBoy
from PIL import Image
from collections import deque

logging.disable(logging.CRITICAL)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v021/in_game'

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    symbols={}
    for line in (ROOT/'pokecrystal.sym').read_text().splitlines():
        a=line.split()
        if len(a)==2 and ':' in a[0]:
            try: symbols[a[1]]=tuple(int(n,16) for n in a[0].split(':'))
            except ValueError: pass
    results={'rom_sha256':hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest()}
    flags={}; flag_index=0
    for line in (ROOT/'constants/event_flags.asm').read_text().splitlines():
        parts=line.split(';')[0].split()
        if not parts:continue
        if parts[0]=='const_def':flag_index=int(parts[1]) if len(parts)>1 else 0
        elif parts[0]=='const_next':flag_index=int(parts[1])
        elif parts[0]=='const_skip':flag_index+=int(parts[1]) if len(parts)>1 else 1
        elif parts[0]=='const':flags[parts[1]]=flag_index;flag_index+=1
    with tempfile.TemporaryDirectory(prefix='peon-intro-') as directory:
        rom=Path(directory)/'test.gbc'
        shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
        p=PyBoy(str(rom),window='null',sound_emulated=True,log_level='ERROR')
        p.set_emulation_speed(0)
        observed={'class_entered':False,'move_menus':0,'naming_entered':False,'character_sheets':0}
        p.hook_register(*symbols['PeonClassSelect'],lambda state:state.__setitem__('class_entered',True),observed)
        p.hook_register(*symbols['MoveSelectionScreen'],lambda state:state.__setitem__('move_menus',state['move_menus']+1),observed)
        p.hook_register(*symbols['PeonAskName'],lambda state:state.__setitem__('naming_entered',True),observed)
        p.hook_register(*symbols['PeonCharacterSheet'],lambda state:state.__setitem__('character_sheets',state['character_sheets']+1),observed)
        def read(name,length=1):
            bank,address=symbols[name]
            return list(p.memory[bank,address:address+length])
        def press(key,frames=90):
            p.button(key,delay=8); p.tick(frames,True)
        def event(name):
            index=flags[name]
            return bool(read('wEventFlags',index//8+1)[index//8]&(1<<(index%8)))
        map_specs={14:('TheDen',12,10),15:('ValleyOfTrials',16,12),16:('DurotarRoad',12,14),17:('SenjinVillage',12,10),18:('RazorHill',12,10),19:('OrgrimmarGate',12,10),20:('BurningBladeCavern',10,10),21:('PeonTrollHut',6,5),22:('PeonOrcHut',6,5)}
        def navigate(target,avoid_aggro=True):
            num=read('wMapNumber')[0];name,w,h=map_specs[num]
            grid=(ROOT/f'maps/{name}.blk').read_bytes()
            if tuple(read('wXCoord')+read('wYCoord'))==target:
                walk('up',1)
            start=tuple(read('wXCoord')+read('wYCoord'))
            collision_rows=[]
            for row in (ROOT/'data/tilesets/peon_collision.asm').read_text().splitlines():
                if 'tilecoll' in row:collision_rows.append(row.split('tilecoll',1)[1].split(';')[0].replace(' ','').split(','))
            actors=set()
            for row in (ROOT/'maps'/f'{name}.asm').read_text().splitlines():
                match=re.match(r'\s*object_event\s+(\d+),\s*(\d+),',row)
                if match:actors.add((int(match[1]),int(match[2])))
            def blocked_at(x,y):
                block=grid[(y//2)*w+x//2]
                return collision_rows[block][(y%2)*2+x%2]=='WALL'
            warps=set()
            for row in (ROOT/'maps'/f'{name}.asm').read_text().splitlines():
                match=re.match(r'\s*warp_event\s+(\d+),\s*(\d+),',row)
                if match:warps.add((int(match[1]),int(match[2])))
            queue=deque([(start,[])]);seen={start};found=None
            while queue:
                (x,y),path=queue.popleft()
                if (x,y)==target:found=path;break
                for key,dx,dy in [('left',-1,0),('right',1,0),('up',0,-1),('down',0,1)]:
                    pos=(x+dx,y+dy);xx,yy=pos
                    if not (0<=xx<w*2 and 0<=yy<h*2) or pos in seen or pos in actors:continue
                    if blocked_at(xx,yy):continue
                    if pos in warps and pos!=target:continue
                    if num==14 and avoid_aggro and not event('EVENT_PEON_SCORPID_DEFEATED') and abs(xx-19)+abs(yy-15)<=2:continue
                    seen.add(pos);queue.append((pos,path+[key]))
            assert found is not None,(name,start,target)
            for i,key in enumerate(found):
                if tuple(read('wXCoord')+read('wYCoord'))==target:break
                if target in warps and i==len(found)-1:
                    p.button(key,delay=30);p.tick(150,True)
                else:walk(key,1)
            return num
        def walk(key,steps):
            before=read('wXCoord')+read('wYCoord')
            p.button_press(key)
            for _ in range(steps*40+30):
                p.tick(1,False)
                position=read('wXCoord')+read('wYCoord')
                if sum(abs(a-b) for a,b in zip(before,position))==steps: break
            p.button_release(key); p.tick(25,True)
            assert sum(abs(a-b) for a,b in zip(before,read('wXCoord')+read('wYCoord')))==steps, (key,steps,before,read('wXCoord')+read('wYCoord'))
        def capture(name):
            p.screen.image.save(OUT/(name+'.png'))
            p.screen.image.resize((640,576),resample=0).save(OUT/(name+'_4x.png'))
            print(name,read('wMapGroup',2),read('wXCoord',2),read('wScriptMode'),flush=True)
        def advance_until(predicate,limit=100):
            for _ in range(limit):
                if predicate(): return
                press('a')
            capture('unexpected_state')
            raise AssertionError({name:read(name,2 if name in ('wEnemyMonHP','wBattleMonHP') else 1) for name in ('wBattleMode','wEnemyMonHP','wBattleMonHP','wBattleResult','wCurPlayerMove','wCurMoveNum','wMenuCursorY','wScriptMode')} | {'pc':hex(p.register_file.PC)})

        p.tick(240,True); capture('01_title')
        expected=Image.open(ROOT/'references/generated/title_portal_gbc/title_portal_native_160x144.png').convert('RGB')
        actual=p.screen.image.convert('RGB')
        assert [tuple(c >> 3 for c in pixel) for pixel in actual.getdata()] == [tuple(c >> 3 for c in pixel) for pixel in expected.getdata()], 'Native title differs from compiled tile/palette reconstruction'
        results['native_title_rgb555_matches']=True
        title_out=ROOT/'references/generated/title_portal_gbc'
        actual.save(title_out/'title_portal_in_rom_160x144.png')
        actual.resize((960,864),resample=0).save(title_out/'title_portal_in_rom_6x.png')
        press('start'); capture('02_character_select')
        # Empty Continue must keep the selection screen visible.
        press('a'); assert read('wMapGroup')[0]==0
        press('down'); press('a'); capture('03_sleeping')
        seen=[]
        for i in range(80):
            if read('wMapGroup',2)==[26,14] and read('wScriptMode')[0]==0: break
            # Class selection is distinguishable from text through its custom loop.
            bank,address=symbols['PeonClassSelect.input']
            if observed['class_entered'] and 'other_classes_locked' not in results:
                capture('05_class_shaman')
                press('down'); capture('06_class_warrior')
                press('a'); assert read('wPartyCount')[0]==0
                press('down'); capture('07_class_warlock')
                press('a'); assert read('wPartyCount')[0]==0
                press('up'); press('up')
                results['other_classes_locked']=True
            if observed['naming_entered'] and 'master_asks_name' not in results:
                # Enter "ABCDE" with actual buttons, then jump to END and confirm.
                p.tick(120,True);capture('07b_master_naming')
                for j in range(5):
                    press('a',30)
                    if j<4:press('right',30)
                press('start',30);press('a',90)
                results['master_asks_name']=True
            press('a')
            if read('wMapNumber')[0] not in seen:
                seen.append(read('wMapNumber')[0]); capture('intro_map_'+str(read('wMapNumber')[0]))
        assert read('wMapGroup',2)==[26,14]
        assert read('wPartyCount')[0]==1
        assert read('wPartyMon1Species')[0]==66
        assert read('wPartyMon1Moves',4)==[1,84,0,0]
        assert read('wNumKeyItems')[0]==3
        assert read('wKeyItems',3)==[25,45,50]
        assert read('wPlayerName',11)==[143,234,174,173,127,128,129,130,131,132,80], read('wPlayerName',11)
        capture('08_the_den')
        results['new_game_reaches_den']=True
        results['starting_kit']=read('wKeyItems',3)
        results['starting_moves']=read('wPartyMon1Moves',4)
        # Exercise the actual player graphic load, including distinct walking frames.
        tile=read('wPlayerSpriteTile')[0]
        bank=0 if tile&128 else 1
        address=0x8000+(tile&127)*16
        graphic=(ROOT/'gfx/sprites/peon.2bpp').read_bytes()
        assert bytes(p.memory[bank,address:address+256])==graphic[:256]
        assert bytes(p.memory[bank,address+0x800:address+0x800+512])==graphic[256:]
        results['player_vram_matches']=True
        press('select');capture('08b_map_locked');press('b')
        assert read('wMapGroup',2)==[26,14] and read('wScriptMode')[0]==0
        walk('up',2); press('a'); capture('09_quest_offer')
        advance_until(lambda:read('wScriptMode')[0]==0)
        capture('10_quest_accepted')
        results['event_bytes_after_acceptance']=read('wEventFlags',18)
        walk('down',2); walk('right',7)
        p.tick(240,True)
        assert read('wBattleMode')[0]==0
        results['neutral_boar_does_not_aggro']=True
        sparring_state=io.BytesIO()
        p.save_state(sparring_state)
        press('a')
        advance_until(lambda:read('wBattleMode')[0]!=0)
        # Choose the second move, Lightning Bolt, once the move menu appears.
        handled=0
        spells=[]
        for _ in range(80):
            if observed['move_menus']>handled:
                handled=observed['move_menus']
                p.tick(60,True)
                if 'battle_self_returns_cleanly' not in results:
                    sheets=observed['character_sheets']
                    press('b',60);capture('11_battle')
                    press('right',30);press('a',90)
                    assert observed['character_sheets']==sheets+1, 'SELF did not open custom character sheet'
                    capture('11a_battle_self')
                    press('b',90);press('left',30);press('a',90)
                    assert read('wBattleMode')[0]!=0 and read('wPartyCount')[0]==1
                    results['battle_self_returns_cleanly']=True
                    handled=observed['move_menus']
                if read('wCurMoveNum')[0]==0: press('down',60)
                capture('11_spell_selection')
                if 'spell_animation_recorded' not in results:
                    p.button('a',delay=8);frames=[]
                    for frame in range(50):
                        p.tick(4,True);frames.append(p.screen.image.resize((640,576),resample=0))
                    frames[0].save(OUT/'lightning_bolt_in_rom.gif',save_all=True,append_images=frames[1:],duration=67,loop=0)
                    results['spell_animation_recorded']=True
                else:press('a',180)
            else: press('a',120)
            spells.append(read('wCurPlayerMove')[0])
            if read('wBattleMode')[0]==0 and read('wScriptMode')[0]==0: break
        advance_until(lambda:read('wBattleMode')[0]==0 and read('wScriptMode')[0]==0)
        capture('12_after_battle')
        assert read('wMapGroup',2)==[26,14], 'Battle failed to return to The Den'
        results['battle_result']=read('wBattleResult')[0]
        results['moves_observed_in_battle']=sorted(set(spells))
        assert 84 in spells, 'Lightning Bolt was not exercised in combat'
        assert read('wBattleResult')[0]==0, 'First quest encounter did not succeed'
        # Quest two, proximity-only aggro and earned map, with no RAM changes.
        navigate((10,10));press('up',20);press('a')
        advance_until(lambda:event('EVENT_PEON_STING_ACCEPTED') and read('wScriptMode')[0]==0)
        capture('18_scorpid_quest_accepted')
        navigate((17,14));assert read('wBattleMode')[0]==0
        walk('down',1);p.tick(600,True)
        capture('18b_aggro_state')
        assert read('wBattleMode')[0]!=0, 'Red scorpid failed to aggro without A'
        results['scorpid_proximity_aggro_passed']=True
        capture('19_scorpid_battle')
        handled=observed['move_menus']
        for _ in range(100):
            if observed['move_menus']>handled:
                handled=observed['move_menus'];p.tick(40,True)
                if read('wCurMoveNum')[0]==0:press('down',30)
                press('a',180)
            else:press('a',90)
            if read('wBattleMode')[0]==0 and read('wScriptMode')[0]==0:break
        assert event('EVENT_PEON_SCORPID_DEFEATED'), 'Scorpid quest failed'
        assert not event('EVENT_PEON_MAP_RECEIVED'), 'Map awarded before quest turn-in'
        navigate((10,10));press('up',20);press('a')
        advance_until(lambda:event('EVENT_PEON_MAP_RECEIVED') and read('wScriptMode')[0]==0)
        assert read('wNumKeyItems')[0]==5 and 90 in read('wKeyItems',5)
        results['second_quest_map_reward_passed']=True
        press('select');capture('20_zone_map_den')
        expected=Image.open(ROOT/'references/generated/durotar_v021/zone_maps/den.png').convert('RGB')
        # The independent atlas validator verifies the quest OBJ glyph. Compare
        # every remaining native background pixel here, including the frame.
        actual=p.screen.image.convert('RGB')
        for y in range(144):
            for x in range(160):
                if 58 <= x < 66 and 92 <= y < 100:continue
                assert tuple(c>>3 for c in actual.getpixel((x,y)))==tuple(c>>3 for c in expected.getpixel((x,y))), (x,y)
        press('right');capture('21_zone_map_fog')
        expected=Image.open(ROOT/'references/generated/durotar_v021/zone_maps/fog.png').convert('RGB')
        assert [tuple(c>>3 for c in v) for v in p.screen.image.convert('RGB').getdata()]==[tuple(c>>3 for c in v) for v in expected.getdata()]
        press('b');results['zone_map_and_fog_render_passed']=True
        # Native menus must close cleanly and reload overworld graphics.
        press('start');press('a');capture('22_shaman_sheet');press('b');press('b')
        press('start');press('down',30);press('a');capture('23_bags');press('b');press('b')
        assert read('wScriptMode')[0]==0 and read('wMapGroup',2)==[26,14]
        results['custom_menus_return_to_world']=True
        press('start')
        while read('wMenuCursorPosition')[0]>1:press('up',30)
        press('down',30);press('a');press('a');capture('23b_inventory');press('a')
        assert read('wPartyMon1Item')[0]==137, 'Green club was not equipped'
        capture('23c_equipped_green_club');press('b');press('b')
        results['equipment_persists_in_existing_held_item_field']=True
        navigate((14,10));press('up',30);money_before=int.from_bytes(bytes(read('wMoney',3)),'big');press('a')
        advance_until(lambda:int.from_bytes(bytes(read('wMoney',3)),'big')==money_before-25 and read('wScriptMode')[0]==0)
        assert int.from_bytes(bytes(read('wMoney',3)),'big')==money_before-25
        assert read('wItems',4)==[137,1,46,5], read('wItems',4)
        capture('23d_duokna_purchase');results['classic_vendor_bundle_price_passed']=True
        # Walk to all new maps via normal warp tiles, including return routes.
        routes=[((20,10),15),((24,4),20),((10,16),15),((28,12),16),((12,24),17),((10,4),16),((12,4),18),((12,4),19)]
        reached=[]
        for target,next_map in routes:
            navigate(target);p.tick(120,True)
            assert read('wMapNumber')[0]==next_map,(target,next_map,read('wMapNumber'))
            reached.append(next_map);capture('24_zone_'+str(next_map))
            if next_map==20:
                navigate((8,12));walk('up',1);p.tick(600,True)
                assert read('wBattleMode')[0]!=0
                capture('24c_red_imp_battle')
                cave_state=io.BytesIO();p.save_state(cave_state)
                handled=observed['move_menus']
                for _ in range(120):
                    if observed['move_menus']>handled:
                        handled=observed['move_menus'];p.tick(40,True)
                        if read('wCurMoveNum')[0]==0:press('down',30)
                        press('a',180)
                    else:press('a',90)
                    if read('wBattleMode')[0]==0 and read('wScriptMode')[0]==0:break
                assert read('wBattleResult')[0]==0
                assert any(v in read('wItems',read('wNumItems')[0]*2)[::2] for v in (135,141))
                capture('24d_cave_loot');results['red_imp_combat_and_loot_passed']=True
            if next_map==15 and not event('EVENT_PEON_CACTUS_DONE'):
                navigate((8,11));press('up',30);press('a')
                advance_until(lambda:event('EVENT_PEON_CACTUS_ACCEPTED') and read('wScriptMode')[0]==0)
                for n,target in enumerate([(7,8),(23,10),(9,18)],1):
                    navigate(target);press('up',30);press('a')
                    advance_until(lambda:event('EVENT_PEON_CACTUS_'+str(n)) and read('wScriptMode')[0]==0)
                navigate((8,11));press('up',30);press('a')
                advance_until(lambda:event('EVENT_PEON_CACTUS_DONE') and read('wScriptMode')[0]==0)
                assert event('EVENT_PEON_LARGE_BAG')
                capture('24b_cactus_reward');results['cactus_quest_and_bag_upgrade_passed']=True
        results['zones_reached_by_walking']=reached
        for flag in ['DEN','VALLEY','ROAD','SENJIN','RAZOR','ORGRIMMAR','CAVERN']:
            assert event('EVENT_PEON_DISCOVERED_'+flag),flag
        press('select');capture('25_orgrimmar_map');press('b')
        results['zone_discovery_flags_passed']=True
        # Save via the regular Start menu (SHAMAN, PACK, player, SAVE).
        before={name:read(name,length) for name,length in [('wPlayerName',11),('wPlayerID',2),('wMapGroup',2),('wXCoord',1),('wYCoord',1),('wNumKeyItems',1),('wKeyItems',4),('wPartyMon1Moves',4),('wPartyMon1Item',1),('wEventFlags',40)]}
        press('start'); capture('13_start_menu')
        while read('wMenuCursorPosition')[0]>1: press('up',30)
        for _ in range(3): press('down',30)
        press('a')
        for _ in range(5): press('a',180)
        capture('14_saved')
        p.stop(save=True)
        assert Path(str(rom)+'.ram').stat().st_size==32768
        p=PyBoy(str(rom),window='null',sound_emulated=True,log_level='ERROR')
        p.set_emulation_speed(0)
        p.tick(1800,True); press('start'); capture('15_continue_selection')
        for _ in range(5): press('a',180)
        after={name:read(name,length) for name,length in [('wPlayerName',11),('wPlayerID',2),('wMapGroup',2),('wXCoord',1),('wYCoord',1),('wNumKeyItems',1),('wKeyItems',4),('wPartyMon1Moves',4),('wPartyMon1Item',1),('wEventFlags',40)]}
        assert before==after,(before,after)
        capture('16_after_cold_restart')
        results['save_cold_restart_passed']=True
        results['saved_state']=after
        assert read('wScriptMode')[0]==0
        # Independent active-combat inventory diagnostic, after all normal tests.
        # Seed empty charges/item only in an isolated emulator state; then use
        # actual BAGS buttons to prove active and saved fields stay synchronized.
        p.hook_register(*symbols['MoveSelectionScreen'],lambda state:state.__setitem__('move_menus',state['move_menus']+1),observed)
        cave_state.seek(0);p.load_state(cave_state)
        menus=observed['move_menus']
        advance_until(lambda:observed['move_menus']>menus)
        for field,value in [('wBattleMonPP',1),('wPartyMon1PP',1)]:
            bank,address=symbols[field];p.memory[bank,address+1]=value
        bank,address=symbols['wBattleMonItem'];p.memory[bank,address]=0
        press('b',60);press('down',30);press('a',180);press('a',180)
        press('a',180)
        assert read('wBattleMonItem')[0]==137 and read('wPartyMon1Item')[0]==137
        press('right',180);press('a',180)
        capture('26_battle_bag_water')
        assert read('wBattleMonPP',2)[1]==11 and read('wPartyMon1PP',2)[1]==11, {'battle_pp':read('wBattleMonPP',2),'party_pp':read('wPartyMon1PP',2),'cursor':read('wMenuCursorY'),'items':read('wItems',4),'pc':hex(p.register_file.PC)}
        assert read('wItems',4)==[137,1,46,4],read('wItems',4)
        press('b',90)
        assert read('wBattleMode')[0]!=0
        results['active_battle_bags_diagnostic_passed']=True
        results['active_battle_bags_diagnostic_injections']=['active weapon cleared','Lightning charges set to one in battle and party fields']
        # Separate fault-injection check: lower HP to guarantee a friendly loss.
        # This is not used to pass the ordinary intro, quest, win or save tests.
        sparring_state.seek(0); p.load_state(sparring_state)
        bank,address=symbols['wPartyMon1HP']
        p.memory[bank,address]=0; p.memory[bank,address+1]=1
        press('a')
        advance_until(lambda:read('wBattleMode')[0]!=0)
        advance_until(lambda:read('wBattleMode')[0]==0 and read('wScriptMode')[0]==0,200)
        assert read('wMapGroup',2)==[26,14]
        assert read('wBattleResult')[0]==1
        assert read('wPartyMon1HP',2)==read('wPartyMon1MaxHP',2)
        capture('17_friendly_defeat_recovery')
        results['friendly_defeat_fault_injection_passed']=True
        p.stop(save=False)
    (OUT/'validation_results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__=='__main__': main()
