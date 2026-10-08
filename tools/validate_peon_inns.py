#!/usr/bin/env python3
"""Exercise inns/Hearthstone through normal buttons and battery-save restart.

An isolated ROM copy is used. No RAM edits, savestate shortcuts or quest-flag
injection are used to pass gameplay, binding, rest, travel or save checks.
"""
import hashlib
import json
import logging
import re
import shutil
import tempfile
from collections import deque
from pathlib import Path
from PIL import Image
from pyboy import PyBoy

logging.disable(logging.CRITICAL)
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'references/generated/durotar_v022/inn_validation'
MAPS={14:('TheDen',12,10),15:('ValleyOfTrials',16,12),16:('DurotarRoad',12,14),
      17:('SenjinVillage',12,10),18:('RazorHill',12,10),19:('OrgrimmarGate',12,10),
      20:('BurningBladeCavern',10,10),21:('PeonTrollHut',6,5),22:('PeonOrcHut',6,5),
      23:('PeonOrcInn',6,5),24:('PeonTrollInn',6,5)}


def symbols():
    result={}
    for row in (ROOT/'pokecrystal.sym').read_text().splitlines():
        parts=row.split()
        if len(parts)==2 and ':' in parts[0]:
            try:result[parts[1]]=tuple(int(n,16) for n in parts[0].split(':'))
            except ValueError:pass
    return result


def flag_ids():
    result={};index=0
    for row in (ROOT/'constants/event_flags.asm').read_text().splitlines():
        parts=row.split(';')[0].split()
        if not parts:continue
        if parts[0]=='const_def':index=int(parts[1]) if len(parts)>1 else 0
        elif parts[0]=='const_next':index=int(parts[1])
        elif parts[0]=='const_skip':index+=int(parts[1]) if len(parts)>1 else 1
        elif parts[0]=='const':result[parts[1]]=index;index+=1
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    sym=symbols();flags=flag_ids()
    assert 'PeonHearthstoneMenu' in sym, 'Include hearthstone helper and rebuild first'
    results={'rom_sha256':hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest(),
             'emulator':'PyBoy 2.7.0','test_method':'Ordinary buttons only; no RAM edits or savestate shortcuts',
             'doors':[],'bindings':[],'hearth_returns':[]}
    collision=[]
    for row in (ROOT/'data/tilesets/peon_collision.asm').read_text().splitlines():
        if 'tilecoll' in row:collision.append(row.split('tilecoll',1)[1].split(';')[0].replace(' ','').split(','))
    with tempfile.TemporaryDirectory(prefix='peon-inns-') as directory:
        rom=Path(directory)/'test.gbc';shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
        p=PyBoy(str(rom),window='null',sound_emulated=True,log_level='ERROR')
        p.set_emulation_speed(0)
        observed={'naming':False,'named':False,'moves':0,'hearth_menus':0,'yes_no':0}
        p.hook_register(*sym['PeonAskName'],lambda s:s.__setitem__('naming',True),observed)
        p.hook_register(*sym['MoveSelectionScreen'],lambda s:s.__setitem__('moves',s['moves']+1),observed)
        p.hook_register(*sym['PeonHearthstoneMenu'],lambda s:s.__setitem__('hearth_menus',s['hearth_menus']+1),observed)
        p.hook_register(*sym['YesNoBox'],lambda s:s.__setitem__('yes_no',s['yes_no']+1),observed)
        def read(name,length=1):
            bank,address=sym[name]
            return list(p.memory[address:address+length]) if address>=0xff00 else list(p.memory[bank,address:address+length])
        def press(key,frames=90):
            p.button(key,delay=8);p.tick(frames,True)
        def event(name):
            index=flags[name];bank,address=sym['wEventFlags']
            return bool(p.memory[bank,address+index//8]&(1<<(index%8)))
        def position():return tuple(read('wXCoord')+read('wYCoord'))
        def mapnum():return read('wMapNumber')[0]
        def healthy():return read('wPartyMon1HP',2)==read('wPartyMon1MaxHP',2)
        def capture(name):
            p.screen.image.save(OUT/(name+'.png'))
            p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(OUT/(name+'_4x.png'))
            print(name,'map',mapnum(),'xy',position(),'script',read('wScriptMode')[0],flush=True)
        def advance(predicate,limit=100):
            for _ in range(limit):
                if predicate():return
                press('a')
            capture('failure')
            raise AssertionError({'map':mapnum(),'xy':position(),'script':read('wScriptMode'),
                                  'battle':read('wBattleMode'),'pc':hex(p.register_file.PC)})
        def walk(key):
            before=position();p.button_press(key)
            for _ in range(80):
                p.tick(1,False)
                if position()!=before:break
            p.button_release(key);p.tick(25,True)
            assert sum(abs(a-b) for a,b in zip(before,position()))==1,(key,before,position())
        def navigate(target):
            num=mapnum();name,width,height=MAPS[num]
            data=(ROOT/'maps'/(name+'.blk')).read_bytes()
            rows=(ROOT/'maps'/(name+'.asm')).read_text().splitlines()
            actors=set();danger=[];warps=set()
            for row in rows:
                match=re.match(r'\s*warp_event\s+(\d+),\s*(\d+),',row)
                if match:warps.add(tuple(int(v) for v in match.groups()))
                match=re.match(r'\s*object_event\s+(\d+),\s*(\d+),',row)
                if match:
                    last=row.split(',')[-1].strip()
                    if last in flags and event(last):continue
                    actor=tuple(int(v) for v in match.groups());actors.add(actor)
                    if 'PAL_NPC_RED' in row:danger.append(actor)
            def blocked(x,y):
                return collision[data[y//2*width+x//2]][y%2*2+x%2]=='WALL'
            start=position()
            if start==target:
                # Door arrival stands on the outdoor entrance. Step away before
                # approaching it again, rather than editing the warp state.
                choices=[('down',0,1),('left',-1,0),('right',1,0),('up',0,-1)]
                for key,dx,dy in choices:
                    x,y=start[0]+dx,start[1]+dy
                    if 0<=x<width*2 and 0<=y<height*2 and not blocked(x,y) and (x,y) not in actors:
                        walk(key);break
                start=position()
            queue=deque([(start,[])]);seen={start};found=None
            while queue:
                (x,y),path=queue.popleft()
                if (x,y)==target:found=path;break
                for key,dx,dy in [('left',-1,0),('right',1,0),('up',0,-1),('down',0,1)]:
                    point=(x+dx,y+dy);xx,yy=point
                    if not(0<=xx<width*2 and 0<=yy<height*2) or point in seen or point in actors:continue
                    if blocked(xx,yy) or (point in warps and point!=target):continue
                    if any(abs(xx-ax)+abs(yy-ay)<=2 for ax,ay in danger):continue
                    seen.add(point);queue.append((point,path+[key]))
            assert found is not None,(name,start,target)
            for index,key in enumerate(found):
                if target in warps and index==len(found)-1:
                    p.button(key,delay=30);p.tick(180,True)
                else:walk(key)
            return num
        def finish_talk():advance(lambda:read('wScriptMode')[0]==0 and read('wBattleMode')[0]==0)
        def talk(x,y):
            navigate((x,y+1));press('up',30);press('a')
        def first_menu_item():
            press('start')
            for _ in range(8):
                if read('wMenuCursorPosition')[0]==1:break
                press('up',30)
            assert read('wMenuCursorPosition')[0]==1
            assert read('wMenuItemsList',8)==[7,1,2,3,4,9,5,6],read('wMenuItemsList',8)
        def hearth(cancel=False):
            before=(mapnum(),position())
            yes_no=observed['yes_no']
            first_menu_item()
            for _ in range(4):press('down',30)
            capture('hearthstone_menu')
            count=observed['hearth_menus'];press('a')
            assert observed['hearth_menus']==count+1
            if cancel:
                advance(lambda:observed['yes_no']>yes_no)
                press('b');press('b')
                assert (mapnum(),position())==before
                return
            # Confirm the native Yes/No; the script then casts and warps.
            advance(lambda:mapnum() in (23,24) and read('wScriptMode')[0]==0)
            assert position()==(5,6),position()
        def binding(flag):
            before=read('wPartyMon1HP',2);status=read('wPartyMon1Status')[0]
            money=read('wMoney',3);talk(6,4)
            finish_talk()
            assert event('EVENT_PEON_HEARTH_GRANTED') and event(flag)
            homes=['EVENT_PEON_HOME_DEN','EVENT_PEON_HOME_SENJIN','EVENT_PEON_HOME_RAZOR']
            assert sum(event(f) for f in homes)==1
            assert healthy() and read('wPartyMon1Status')[0]==0
            assert read('wMoney',3)==money, 'Prototype rest/binding unexpectedly charged money'
            results['bindings'].append({'home':flag,'exclusive':True,'restored_hp':True,
                                        'status_before':status,'status_zero_after_rest':True,'hp_before':before,
                                        'hp_after':read('wPartyMon1HP',2),
                                        'prototype_rest_cost_copper':0,'money_unchanged':True})
        def enter_door(origin,xy,expected,kind):
            assert mapnum()==origin
            navigate(tuple(xy));assert mapnum()==expected,(origin,xy,mapnum())
            capture(kind+'_'+str(origin)+'_'+str(xy[0])+'_'+str(xy[1]))
            return {'origin_map':origin,'door':xy,'interior_map':expected}
        def exit_room(origin):
            navigate((5,7));assert mapnum()==origin,(origin,mapnum())

        p.tick(240,True);press('start');press('down');press('a')
        for _ in range(120):
            if mapnum()==14 and read('wScriptMode')[0]==0:break
            if observed['naming'] and not observed['named']:
                p.tick(120,True)
                for i in range(5):
                    press('a',30)
                    if i<4:press('right',30)
                press('start',30);press('a');observed['named']=True
            press('a')
        assert read('wMapGroup',2)==[26,14]
        results['ordinary_new_game_reaches_den']=True
        first_menu_item()
        for _ in range(4):press('down',30)
        press('a');capture('hearthstone_unbound')
        # Native text has several pages before StartMenu returns. Dismiss all
        # text/menu layers with ordinary B presses before trying to walk.
        for _ in range(6):press('b')
        assert read('wScriptMode')[0]==0
        assert not event('EVENT_PEON_HEARTH_GRANTED') and mapnum()==14, {'granted':event('EVENT_PEON_HEARTH_GRANTED'),'map':mapnum(),'xy':position(),'script':read('wScriptMode')}
        results['unbound_hearth_does_not_travel']=True
        # Obtain actual wounds and spent move charges through ordinary combat.
        talk(10,9);finish_talk();assert event('EVENT_PEON_QUEST_ACCEPTED')
        talk(18,12)
        advance(lambda:read('wBattleMode')[0]!=0)
        handled=0
        for _ in range(150):
            if read('wBattleMode')[0]==0 and read('wScriptMode')[0]==0:break
            if observed['moves']>handled:
                handled=observed['moves'];press('a')
            press('a')
        assert read('wBattleMode')[0]==0 and read('wScriptMode')[0]==0
        assert read('wBattleResult')[0]==0,'Boar sparring must be won'
        money_before_reward=int.from_bytes(bytes(read('wMoney',3)),'big')
        talk(10,9);finish_talk()
        assert event('EVENT_PEON_CUTTING_TURNED_IN')
        money_after_reward=int.from_bytes(bytes(read('wMoney',3)),'big')
        assert money_after_reward==money_before_reward+100,(money_before_reward,money_after_reward)
        results['normal_quest_reward_copper']=100
        results['actual_copper_available_for_rest_check']=money_after_reward
        wounded_hp=read('wPartyMon1HP',2);spent_pp=read('wPartyMon1PP',4)
        assert not healthy(),'Boar fight must provide real wounds for the rest check'
        capture('wounded_before_inn')
        results['combat_wounds_persist_without_free_heal']=True
        # All residence NPCs provide flavour; none is a free-rest shortcut.
        entries=json.loads((ROOT/'references/generated/durotar_v022/building_entries.json').read_text())
        for door in entries['TheDen']:
            if door['service']!='residence':continue
            record=enter_door(14,door['xy'],22,'residence')
            hp=read('wPartyMon1HP',2);pp=read('wPartyMon1PP',4)
            talk(6,4);finish_talk()
            assert read('wPartyMon1HP',2)==hp and read('wPartyMon1PP',4)==pp
            exit_room(14);record['round_trip']=True;record['no_free_heal']=True;results['doors'].append(record)
        record=enter_door(14,[17,5],23,'inn')
        yes_no=observed['yes_no'];talk(6,4)
        advance(lambda:observed['yes_no']>yes_no)
        press('b');finish_talk()
        assert not event('EVENT_PEON_HEARTH_GRANTED') and read('wPartyMon1HP',2)==wounded_hp
        results['declined_rest_does_not_heal_or_bind']=True
        binding('EVENT_PEON_HOME_DEN')
        assert read('wPartyMon1PP',4)!=spent_pp,'Rest must replenish actual spent charges'
        results['rest_restores_spent_charges']=True
        capture('den_inn_bound');exit_room(14);record['round_trip']=True;results['doors'].append(record)
        navigate((20,10));assert mapnum()==15
        hearth(cancel=True);results['cancelled_hearth_preserves_location']=True
        hearth();assert mapnum()==23 and read('wBackupMapNumber')[0]==14
        results['hearth_returns'].append({'home':'DEN','interior':23,'backup_owner':14})
        exit_room(14);navigate((20,10));navigate((28,12));assert mapnum()==16
        navigate((12,24));assert mapnum()==17
        for door in entries['SenjinVillage']:
            if door['service']!='residence':continue
            record=enter_door(17,door['xy'],21,'residence')
            hp=read('wPartyMon1HP',2);pp=read('wPartyMon1PP',4)
            talk(6,4);finish_talk()
            assert read('wPartyMon1HP',2)==hp and read('wPartyMon1PP',4)==pp
            exit_room(17);record['round_trip']=True;record['no_free_heal']=True;results['doors'].append(record)
        record=enter_door(17,[15,5],24,'inn')
        yes_no=observed['yes_no'];talk(6,4)
        advance(lambda:observed['yes_no']>yes_no);press('a')
        advance(lambda:observed['yes_no']>yes_no+1);press('b');finish_talk()
        assert event('EVENT_PEON_HOME_DEN') and not event('EVENT_PEON_HOME_SENJIN')
        results['declined_new_binding_preserves_previous_home']=True
        binding('EVENT_PEON_HOME_SENJIN')
        capture('senjin_inn_bound');exit_room(17);record['round_trip']=True;results['doors'].append(record)
        navigate((10,4));navigate((12,4));assert mapnum()==18
        hearth();assert mapnum()==24 and read('wBackupMapNumber')[0]==17
        results['hearth_returns'].append({'home':'SENJIN','interior':24,'backup_owner':17})
        exit_room(17);navigate((10,4));navigate((12,4));assert mapnum()==18
        for door in entries['RazorHill']:
            if door['service']!='residence':continue
            record=enter_door(18,door['xy'],22,'residence')
            hp=read('wPartyMon1HP',2);pp=read('wPartyMon1PP',4)
            talk(6,4);finish_talk()
            assert read('wPartyMon1HP',2)==hp and read('wPartyMon1PP',4)==pp
            exit_room(18);record['round_trip']=True;record['no_free_heal']=True;results['doors'].append(record)
        record=enter_door(18,[17,5],23,'inn');binding('EVENT_PEON_HOME_RAZOR')
        capture('razor_inn_bound');exit_room(18);record['round_trip']=True;results['doors'].append(record)
        navigate((12,4));assert mapnum()==19
        hearth();assert mapnum()==23 and read('wBackupMapNumber')[0]==18
        results['hearth_returns'].append({'home':'RAZOR','interior':23,'backup_owner':18})
        capture('hearth_arrival_razor_inn')
        assert len(results['doors'])==9
        before={name:read(name,length) for name,length in [('wPlayerName',11),('wMapGroup',2),('wXCoord',1),('wYCoord',1),('wBackupWarpNumber',3)]}
        first_menu_item()
        for _ in range(3):press('down',30)
        assert read('wMenuCursorPosition')[0]==4
        press('a');capture('original_save_position')
        for _ in range(8):press('a')
        p.tick(240,True);p.stop(save=True)
        assert Path(str(rom)+'.ram').stat().st_size==32768
        p=PyBoy(str(rom),window='null',sound_emulated=True,log_level='ERROR');p.set_emulation_speed(0)
        p.tick(240,True);press('start')
        for _ in range(8):press('a')
        p.tick(180,True)
        after={name:read(name,length) for name,length in [('wPlayerName',11),('wMapGroup',2),('wXCoord',1),('wYCoord',1),('wBackupWarpNumber',3)]}
        assert before==after,(before,after)
        assert event('EVENT_PEON_HOME_RAZOR') and event('EVENT_PEON_HEARTH_GRANTED')
        assert not event('EVENT_PEON_HOME_DEN') and not event('EVENT_PEON_HOME_SENJIN')
        capture('inside_inn_after_battery_restart')
        exit_room(18);capture('correct_razor_exit_after_restart')
        results['save_position_still_three_down']=True
        results['inside_inn_battery_restart']=True
        results['saved_backup_exit_owner_preserved']=True
        results['state_before_save']=before;results['state_after_restart']=after
        p.stop(save=False)
    results['limitations']=['Inn rest is an instant prototype adaptation, not Classic regeneration timing',
                            'Hearthstone has no cooldown in this demo',
                            'Three homes share two native inn layouts',
                            'Chromatic hardware is untested']
    (OUT/'validation_results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
