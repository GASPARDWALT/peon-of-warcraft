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
from pathlib import Path
from pyboy import PyBoy

logging.disable(logging.CRITICAL)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/v0_1_playable'

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    symbols={}
    for line in (ROOT/'pokecrystal.sym').read_text().splitlines():
        a=line.split()
        if len(a)==2 and ':' in a[0]:
            try: symbols[a[1]]=tuple(int(n,16) for n in a[0].split(':'))
            except ValueError: pass
    results={'rom_sha256':hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest()}
    with tempfile.TemporaryDirectory(prefix='peon-intro-') as directory:
        rom=Path(directory)/'test.gbc'
        shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
        p=PyBoy(str(rom),window='null',sound_emulated=True,log_level='ERROR')
        p.set_emulation_speed(0)
        observed={'class_entered':False,'move_menus':0}
        p.hook_register(*symbols['PeonClassSelect'],lambda state:state.__setitem__('class_entered',True),observed)
        p.hook_register(*symbols['MoveSelectionScreen'],lambda state:state.__setitem__('move_menus',state['move_menus']+1),observed)
        def read(name,length=1):
            bank,address=symbols[name]
            return list(p.memory[bank,address:address+length])
        def press(key,frames=90):
            p.button(key,delay=8); p.tick(frames,True)
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
            press('a')
            if read('wMapNumber')[0] not in seen:
                seen.append(read('wMapNumber')[0]); capture('intro_map_'+str(read('wMapNumber')[0]))
        assert read('wMapGroup',2)==[26,14]
        assert read('wPartyCount')[0]==1
        assert read('wPartyMon1Species')[0]==66
        assert read('wPartyMon1Moves',4)==[1,84,0,0]
        assert read('wNumKeyItems')[0]==3
        assert read('wKeyItems',3)==[25,45,50]
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
        walk('up',2); press('a'); capture('09_quest_offer')
        advance_until(lambda:read('wScriptMode')[0]==0)
        capture('10_quest_accepted')
        results['event_bytes_after_acceptance']=read('wEventFlags',18)
        walk('down',2); walk('right',7)
        sparring_state=io.BytesIO()
        p.save_state(sparring_state)
        press('a')
        for _ in range(6): press('a')
        capture('11_battle')
        # Choose the second move, Lightning Bolt, once the move menu appears.
        handled=0
        spells=[]
        for _ in range(80):
            if observed['move_menus']>handled:
                handled=observed['move_menus']
                p.tick(60,True)
                if read('wCurMoveNum')[0]==0: press('down',60)
                capture('11_spell_selection')
                press('a',180)
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
        # Save via the regular Start menu (SHAMAN, PACK, player, SAVE).
        before={name:read(name,length) for name,length in [('wPlayerName',11),('wPlayerID',2),('wMapGroup',2),('wXCoord',1),('wYCoord',1),('wNumKeyItems',1),('wKeyItems',3),('wPartyMon1Moves',4),('wEventFlags',18)]}
        press('start'); capture('13_start_menu')
        for _ in range(3): press('down',30)
        press('a')
        for _ in range(5): press('a',180)
        capture('14_saved')
        p.stop(save=True)
        assert Path(str(rom)+'.ram').stat().st_size==32768
        p=PyBoy(str(rom),window='null',sound_emulated=True,log_level='ERROR')
        p.set_emulation_speed(0)
        p.tick(240,True); press('start'); capture('15_continue_selection')
        for _ in range(5): press('a',180)
        after={name:read(name,length) for name,length in [('wPlayerName',11),('wPlayerID',2),('wMapGroup',2),('wXCoord',1),('wYCoord',1),('wNumKeyItems',1),('wKeyItems',3),('wPartyMon1Moves',4),('wEventFlags',18)]}
        assert before==after,(before,after)
        capture('16_after_cold_restart')
        results['save_cold_restart_passed']=True
        results['saved_state']=after
        assert read('wScriptMode')[0]==0
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
