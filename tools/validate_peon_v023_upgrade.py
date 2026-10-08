#!/usr/bin/env python3
"""Create native batteries on four published ROMs and continue them on v0.2.3.

The four real migration/handoff/save routes use no RAM edits or savestates.
A separate full-pocket diagnostic boots a real v0.2.1 battery copy and edits
only its isolated item pocket to check refusal/retry. The genuine v0.2.2 source
route wins two ordinary battles before saving, so nonzero death/quest flags,
spent charges and persistent wounds must survive the upgrade. Source ROMs and
all published reports remain intact.
"""
import hashlib
import json
import logging
import shutil
import tempfile
import zipfile
from pathlib import Path
from pyboy import PyBoy
import validate_peon_trainer as training
from validate_peon_lazy_quest import event_indices
from validate_durotar_v022_quest_faults import pocket_item_ids
from validate_peon_villages import Session

logging.disable(logging.CRITICAL)
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'references/generated/durotar_v023/save_upgrade'
V022_PUBLISHED_SHA='bbda42f538d2704a601fc05ef5b44c8ca332538a9422dd237e45f74b24c4dc96'
# Read-only MoveSelectionScreen observer from the frozen/published v0.2.2
# RGBDS symbols. Never use current ROM addresses as hooks in an older source.
V022_SOURCE_MOVE_SCREEN=(0x0f,0x6575)


def symbols():
    result={}
    for row in (ROOT/'pokecrystal.sym').read_text().splitlines():
        parts=row.split()
        if len(parts)==2 and ':' in parts[0]:
            try:result[parts[1]]=tuple(int(n,16) for n in parts[0].split(':'))
            except ValueError:pass
    return result


def release_rom(version,stem):
    source=ROOT/'releases'/version/(stem+'.gbc')
    if source.exists():return source.read_bytes()
    with zipfile.ZipFile(source.with_suffix('.zip')) as archive:
        return archive.read(stem+'.gbc')


def validate_release(version,stem,syms,current):
    source=release_rom(version,stem)
    with tempfile.TemporaryDirectory(prefix='peon-save-upgrade-') as directory:
        rom=Path(directory)/'upgrade.gbc';rom.write_bytes(source)
        source_session=Session(rom,syms);p=source_session.p
        def read(name,length=1):
            if not length:return []
            bank,address=syms[name]
            return list(p.memory[address:address+length]) if address>=0xff00 else list(p.memory[bank,address:address+length])
        def press(key,frames=120):p.button(key,delay=8);p.tick(frames,True)
        def capture(suffix):p.screen.image.save(OUT/(version.replace('.','_')+'_'+suffix+'.png'))
        def state():
            result={name:read(name,length) for name,length in [
                ('wPlayerName',11),('wPlayerID',2),('wMapGroup',2),('wXCoord',1),('wYCoord',1),
                ('wPartyMon1Level',1),('wPartyMon1HP',2),('wPartyMon1Moves',4),('wPartyMon1PP',4),
                ('wPartyMon1Item',1),('wMoney',3),('wKeyItems',3),('wNumItems',1),
                ('wPartyMon1Status',1),('wEventFlags',256)]}
            result['wItems']=read('wItems',2*result['wNumItems'][0]+1)
            return result
        def progress():
            result=state()
            for field in ('wMapGroup','wXCoord','wYCoord','wNumItems','wItems'):
                del result[field]
            result['experience']=read('wPartyMon1Exp',3)
            result['key_count']=read('wNumKeyItems')
            result['all_keys']=read('wKeyItems',result['key_count'][0]+1)
            return result
        def totem_quantity():
            items=read('wItems',2*read('wNumItems')[0])
            return sum(items[i+1] for i in range(0,len(items),2) if items[i]==0x94)
        def death_flags():
            values=read('wEventFlags',256)
            return {name:bool(values[index//8]&(1<<(index%8)))
                    for name,index in training.FLAGS.items()
                    if name.startswith('EVENT_PEON_') and
                    (name.endswith('_DEAD') or name in ('EVENT_PEON_QUEST_DONE','EVENT_PEON_SCORPID_DEFEATED'))}
        def source_v022_progress():
            assert hashlib.sha256(source).hexdigest()==V022_PUBLISHED_SHA
            observed={'move_menus':0}
            p.hook_register(*V022_SOURCE_MOVE_SCREEN,
                lambda _unused:observed.__setitem__('move_menus',observed['move_menus']+1),None)
            def is_set(name):
                i=training.FLAGS[name]
                return bool(read('wEventFlags',i//8+1)[i//8]&(1<<(i%8)))
            def talk(pos,direction):
                source_session.navigate(pos);source_session.press(direction,30)
                source_session.press('a',120);source_session.close_dialogue()
            def battle(flag):
                handled=observed['move_menus'];entered=bool(read('wBattleMode')[0])
                for _ in range(160):
                    if read('wBattleMode')[0]:entered=True
                    if observed['move_menus']>handled:
                        handled=observed['move_menus'];p.tick(60,True)
                        for _ in range(5):
                            cursor=read('wCurMoveNum')[0]
                            if cursor==1:break
                            press('up' if cursor>1 else 'down',30)
                        press('a',180)
                    else:press('a',120)
                    if entered and read('wBattleMode')==[0] and read('wScriptMode')==[0]:break
                assert entered and read('wBattleMode')==[0] and read('wScriptMode')==[0]
                assert read('wBattleResult')==[0] and is_set(flag),('Source v0.2.2 encounter failed',flag)
            talk((10,10),'up');assert is_set('EVENT_PEON_QUEST_ACCEPTED')
            source_session.navigate((18,13));source_session.press('up',30);source_session.press('a',120)
            battle('EVENT_PEON_QUEST_DONE');capture('source_actual_boar_victory')
            talk((10,10),'up');assert is_set('EVENT_PEON_STING_ACCEPTED')
            source_session.navigate((17,15));battle('EVENT_PEON_SCORPID_DEFEATED')
            capture('source_actual_scorpid_victory')
            p.hook_deregister(*V022_SOURCE_MOVE_SCREEN)
            assert totem_quantity()==1,'v0.2.2 source already owns exactly one Earth Totem'
            assert read('wPartyMon1PP',4)[1]<35,'Source must exercise genuinely spent spell charges'
            return {'ordinary_buttons_only':True,'source_move_menu_observer':list(V022_SOURCE_MOVE_SCREEN),
                    'source_rom_verified_before_observer':V022_PUBLISHED_SHA,
                    'two_actual_source_victories':True,'no_source_ram_edits':True,
                    'death_flags':death_flags(),'spell_charges_after_source_combats':read('wPartyMon1PP',4)}
        def save_current(session):
            observed={'saved':False,'exited':False}
            session.p.hook_register(*syms['_SaveGameData'],
                lambda _unused:observed.__setitem__('saved',True),None)
            session.p.hook_register(*syms['StartMenu.Exit'],
                lambda _unused:observed.__setitem__('exited',True),None)
            session.press('start')
            for _ in range(10):
                if session.read('wMenuCursorPosition')[0]==1:break
                session.press('up',30)
            assert session.read('wMenuCursorPosition')[0]==1
            for _ in range(3):session.press('down',30)
            session.press('a')
            for _ in range(12):
                if observed['saved'] and observed['exited']:break
                session.press('a',180)
            assert observed['saved'] and observed['exited'],'Native SAVE did not commit and return'
            session.p.tick(60,True)
            assert session.read('wScriptMode')[0]==0
            session.p.stop(save=True)
        p.tick(1800,True);press('start');press('down');press('a')
        named=False
        for _ in range(180):
            if read('wMapGroup',2)==[26,14] and read('wScriptMode')[0]==0:break
            # v0.2.1 introduced the native player naming page. Observe its
            # unchanged WRAM destination/type, then enter ABCDE by buttons.
            pointer=int.from_bytes(bytes(read('wNamingScreenDestinationPointer',2)),'little')
            if (version in ('v0.2.1','v0.2.2') and not named and read('wMapGroup',2)==[26,13]
                    and read('wNamingScreenType')[0]==1 and pointer==syms['wPlayerName'][1]):
                p.tick(120,True)
                for index in range(5):
                    press('a',30)
                    if index<4:press('right',30)
                press('start',30);press('a');named=True
            press('a')
        assert read('wMapGroup',2)==[26,14] and read('wScriptMode')[0]==0,(version,'Old new-game did not reach The Den')
        assert version not in ('v0.2.1','v0.2.2') or named,'Source must exercise its real naming screen'
        source_combat=source_v022_progress() if version=='v0.2.2' else None
        before=state();source_experience=read('wPartyMon1Exp',3)
        source_deaths=death_flags();source_totem_count=totem_quantity()
        legacy_kento_pointer=read('wMap4ObjectScript',2);capture('before_save')
        press('start')
        for _ in range(10):
            if read('wMenuCursorPosition')[0]==1:break
            press('up',30)
        assert read('wMenuCursorPosition')[0]==1
        for _ in range(3):press('down',30)
        press('a')
        for _ in range(8):press('a',180)
        p.stop(save=True)
        battery=Path(str(rom)+'.ram');assert battery.stat().st_size==32768
        legacy_battery=battery.read_bytes()
        battery_hash=hashlib.sha256(legacy_battery).hexdigest()
        rom.write_bytes(current)
        session=training.TrainerSession(rom,syms);p=session.p
        session.load_continue()
        after=state();capture('after_upgrade')
        assert before==after,(version,before,after)
        assert death_flags()==source_deaths,'Continue changed persistent defeated-enemy flags'
        assert read('wScriptMode')[0]==0 and read('wMapGroup',2)==[26,14]
        current_kento_pointer=list(syms['TheDenKentoScript'][1].to_bytes(2,'little'))
        assert read('wMap4ObjectScript',2)==current_kento_pointer,(
            version,'Continue retained a legacy map-object script pointer',
            read('wMap4ObjectScript',2),current_kento_pointer)
        # Reaching Kento is ordinary gameplay: if the source character carries
        # poison, walking may legitimately deal damage. Compare the handoff
        # itself against the actual state after walking, never erase poison.
        source_health_after_continue=read('wPartyMon1HP',2)
        source_status_after_continue=read('wPartyMon1Status')
        session.navigate((7,12))
        kit_before=progress()
        preowned=version=='v0.2.2'
        assert totem_quantity()==int(preowned),'Source Earth Totem ownership must match its published version'
        session.enter_trainer();capture('legacy_kento_handoff');session.exit_trainer()
        assert totem_quantity()==1 and read('wNumItems')==[1]
        assert read('wItems',3)==[0x94,1,0xff]
        assert progress()==kit_before,'Totem handoff modified kit, cash, XP, charges or health'
        once=state()
        session.enter_trainer();session.exit_trainer()
        assert once==state() and progress()==kit_before,'Repeat Kento visit duplicated or changed the kit'
        capture('legacy_kento_repeat_no_duplicate')
        before_restart=state();save_current(session)
        upgraded_battery_hash=hashlib.sha256(battery.read_bytes()).hexdigest()
        session=training.TrainerSession(rom,syms);p=session.p;session.load_continue()
        assert state()==before_restart and totem_quantity()==1 and progress()==kit_before
        capture('totem_after_native_battery_restart');session.p.stop(save=False)
        handoff={'ordinary_buttons_only':True,'received_item_id':148,'quantity_after_handoff':1,
                 'source_saved_kento_script_pointer':legacy_kento_pointer,
                 'current_kento_script_pointer_after_continue':current_kento_pointer,
                 'continue_reloads_current_map_objects':True,
                 'totem_preowned_on_source':preowned,'quantity_before_handoff':source_totem_count,
                 'handoff_required':not preowned,'preowned_totem_not_duplicated':preowned,
                 'repeat_no_duplicate':True,'other_kit_cash_xp_health_charges_unchanged':True,
                 'source_experience':source_experience,'normalized_experience_before_handoff':kit_before['experience'],
                 'health_after_continue':source_health_after_continue,'status_after_continue':source_status_after_continue,
                 'health_after_ordinary_walk_to_kento':kit_before['wPartyMon1HP'],
                 'native_second_battery_sha256':upgraded_battery_hash,'battery_restart_preserves_totem':True,
                 'state_after_handoff_restart':before_restart}
        diagnostic=None
        if version=='v0.2.1':
            # Distinct emulator/file: ordinary old-save evidence above is never
            # rewound or edited to pass the real handoff/persistence route.
            diagrom=Path(directory)/'full_bag_diagnostic.gbc';diagrom.write_bytes(current)
            Path(str(diagrom)+'.ram').write_bytes(legacy_battery)
            session=training.TrainerSession(diagrom,syms);p=session.p;session.load_continue()
            kit=progress();original_number=read('wNumItems');original_items=read('wItems',41)
            capacity=20 if session.event('EVENT_PEON_LARGE_BAG') else 12 if session.event('EVENT_PEON_SMALL_BAG') else 6
            ids=pocket_item_ids('ITEM',exclude=(0x94,))[:capacity]
            assert len(ids)==capacity and len(set(ids))==capacity
            synthetic=[v for item in ids for v in (item,99)]+[255]
            session.write('wNumItems',[capacity]);session.write('wItems',synthetic)
            session.enter_trainer();capture('diagnostic_full_bag_refused');session.exit_trainer()
            assert totem_quantity()==0 and read('wNumItems')==[capacity]
            assert read('wItems',len(synthetic))==synthetic and progress()==kit
            session.write('wNumItems',original_number);session.write('wItems',original_items)
            session.enter_trainer();capture('diagnostic_full_bag_retry_succeeds');session.exit_trainer()
            assert totem_quantity()==1 and progress()==kit
            session.enter_trainer();session.exit_trainer()
            assert totem_quantity()==1 and progress()==kit
            session.p.stop(save=False)
            diagnostic={'diagnostic_ram_edits':True,'source_real_battery_sha256':battery_hash,
                        'edited_fields':['wNumItems','wItems'],'native_capacity':capacity,
                        'synthetic_normal_pocket_item_ids':ids,'failed_without_item_or_kit_changes':True,
                        'original_inventory_restored_before_retry':True,'ordinary_kento_retry_awards_one':True,
                        'repeat_after_retry_does_not_duplicate':True,'no_user_save_changed':True}
    return {'source_rom_sha256':hashlib.sha256(source).hexdigest(),'real_source_battery_sha256':battery_hash,
            'native_battery_size':32768,'ordinary_buttons_only':True,'state_preserved':after,
            'player_name_entered_on_source_rom':named,'legacy_kento_totem_handoff':handoff,
            'source_ordinary_combats':source_combat,'source_persistent_death_flags':source_deaths,
            'persistent_death_flags_preserved':True,'all_256_event_flag_bytes_preserved':True,
            'separate_full_bag_diagnostic':diagnostic}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    syms=symbols();current=(ROOT/'pokecrystal.gbc').read_bytes();states={}
    training.FLAGS=event_indices()
    for version,stem in [('v0.1.1','peon_of_warcraft_v0_1_1'),('v0.2','peon_of_warcraft_v0_2'),
                         ('v0.2.1','peon_of_warcraft_v0_2_1'),('v0.2.2','peon_of_warcraft_v0_2_2')]:
        states[version]=validate_release(version,stem,syms,current)
        print(version,'real battery upgrade passed',flush=True)
    report={'rom_sha256':hashlib.sha256(current).hexdigest(),'emulator':'PyBoy 2.7.0',
            'test_method':'Four ordinary source-ROM/native-battery upgrades, current NPC reload, Kento issue-or-skip/repeat and second battery restart; v0.2.2 genuine combat progress; separate labelled full-pocket diagnostic',
            'all_checks_passed':True,'states':states,
            'scope':'Published v0.1.1, v0.2, v0.2.1 and v0.2.2 characters at The Den; older XP values normalize to the existing level curve; other source locations and Chromatic hardware not tested.'}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT.parent/'save_upgrade_results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
