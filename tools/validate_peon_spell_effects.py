#!/usr/bin/env python3
"""Real menu casts and isolated battle/poison diagnostics for apprentice spells.

Copies the ROM to a temporary directory, completes the normal intro/Gornek
conversation, then rewinds one ordinary boar battle. Only test moves, HP,
buff/status stages and (one guard case) accuracy are edited in temporary RAM.
The real battle interpreter, move selection, damage and faint handling run.
No ROM/source or user battery save is changed.
"""
from pathlib import Path
import hashlib
import io
import json
import logging
import shutil
import tempfile

from PIL import Image
from validate_durotar_v022_quests import QuestSession, load_symbols, FLAGS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'references/generated/durotar_v022/spell_validation'
SPELLS={'rockbiter':14,'lightning_shield':115,'purge':114}
HELPERS=['PeonTryRockbiterEffect','PeonTryLightningShieldEffect','PeonTryPurgeEffect',
         'PeonConsumeRockbiterDamage','PeonLightningShieldRetaliation',
         'PeonGuaranteedSpellEffectChance','DoPoisonStep','PeonRecoverFromDefeat']
COMMANDS=['BattleCommand_BurnTarget','BattleCommand_SpeedDown','BattleCommand_Heal',
          'BattleCommand_StartLoop','BattleCommand_EndLoop','BattleCommand_ApplyDamage']


class SpellSession(QuestSession):
    def __init__(self,rom,sym):
        self.case=None;self.events=[];self.pending=[];self.menus=0;self.ready=False
        self.frames=[];self.misses=0;self.faints=0;self.pending_command=None;self.secondary_rng=0
        super().__init__(rom,sym)

    def open(self):
        super().open()
        for helper in HELPERS:self.p.hook_register(*self.sym[helper],self.enter,helper)
        self.p.hook_register(*self.sym['ReturnFarCall'],self.returned,None)
        self.p.hook_register(*self.sym['BattleMenu'],self.menu,None)
        self.p.hook_register(*self.sym['BattleCommand_CheckHit'],self.check_hit,None)
        self.p.hook_register(*self.sym['BattleCommand_CheckHit.Miss'],self.miss,None)
        self.p.hook_register(*self.sym['BattleCommand_CheckFaint'],self.faint,None)
        for command in COMMANDS:self.p.hook_register(*self.sym[command],self.command,command)
        self.p.hook_register(*self.sym['DoMove.ReadMoveEffectCommand'],self.command_return,None)
        self.p.hook_register(*self.sym['BattleRandom'],self.random,None)

    def write(self,name,values):
        bank,address=self.sym[name]
        for i,value in enumerate(values):
            if address>=0xe000:self.p.memory[address+i]=value
            else:self.p.memory[bank,address+i]=value

    def word(self,name):return int.from_bytes(bytes(self.read(name,2)),'big')

    def snapshot(self):
        return {'move':self.read('wCurPlayerMove')[0],
                'animation':self.read('wPlayerMoveStruct')[0],
                'turn':self.read('hBattleTurn')[0],
                'damage':self.word('wCurDamage'),'enemy_hp':self.word('wEnemyMonHP'),
                'player_hp':self.word('wBattleMonHP'),'player_max_hp':self.word('wBattleMonMaxHP'),
                'party_hp':self.word('wPartyMon1HP'),'party_status':self.read('wPartyMon1Status')[0],
                'enemy_status':self.read('wEnemyMonStatus')[0],
                'pp':self.read('wBattleMonPP',4),
                'rock_charge':self.read('wPeonRockbiterCharge')[0],
                'shield_charges':self.read('wPeonLightningShieldCharges')[0],
                'player_stages':self.read('wPlayerStatLevels',7),
                'enemy_stages':self.read('wEnemyStatLevels',7),
                'player_screens':self.read('wPlayerScreens')[0],
                'enemy_screens':self.read('wEnemyScreens')[0],
                'enemy_reflect':self.read('wEnemyReflectCount')[0],
                'enemy_light_screen':self.read('wEnemyLightScreenCount')[0],
                'player_reflect':self.read('wPlayerReflectCount')[0],
                'missed':self.read('wAttackMissed')[0],
                'player_type':self.read('wPlayerMoveStructType')[0],
                'enemy_type':self.read('wEnemyMoveStructType')[0],
                'battle_mode':self.read('wBattleMode')[0]}

    def menu(self,_):
        self.menus+=1
        if not self.ready:
            self.ready=True;self.p.button_release('a')
            self.write('wBattleMonHP',[0,240]);self.write('wBattleMonMaxHP',[0,240])
            self.write('wEnemyMonHP',[0,240]);self.write('wEnemyMonMaxHP',[0,240])

    def enter(self,helper):
        if self.case is None:return
        turn=self.read('hBattleTurn')[0]
        if helper in ('DoPoisonStep','PeonRecoverFromDefeat'):
            if not self.case.get('poison'):return
        elif helper=='PeonGuaranteedSpellEffectChance':
            if turn or self.read('wCurPlayerMove')[0] not in (52,58,126):return
            if self.case.get('different_animation'):self.write('wPlayerMoveStruct',[1])
        elif helper.startswith('PeonTry'):
            expected={'PeonTryRockbiterEffect':14,'PeonTryLightningShieldEffect':115,'PeonTryPurgeEffect':114}[helper]
            if turn or self.read('wCurPlayerMove')[0]!=expected:return
            if self.case.get('different_animation'):self.write('wPlayerMoveStruct',[1])
        elif helper=='PeonConsumeRockbiterDamage' and turn:return
        elif helper=='PeonLightningShieldRetaliation' and not turn:return
        event={'helper':helper,'before':self.snapshot(),'entry_sp':self.p.register_file.SP}
        self.pending.append(event)

    def returned(self,_):
        # Nested farcalls inside Shield/Purge also pass here. Only the original
        # stack depth identifies the return from the helper being measured.
        if not self.pending:return
        for event in reversed(self.pending):
            if self.p.register_file.SP==event['entry_sp']+2:
                event['after']=self.snapshot();self.pending.remove(event);self.events.append(event)
                return

    def command(self,command):
        if not self.case or self.read('hBattleTurn')[0]:return
        self.pending_command={'helper':command,'before':self.snapshot(),
                              'entry_sp':self.p.register_file.SP}

    def command_return(self,_):
        event=self.pending_command
        if event and self.p.register_file.SP==event['entry_sp']+2:
            event['after']=self.snapshot();self.events.append(event);self.pending_command=None

    def random(self,_):
        if any(e['helper']=='PeonGuaranteedSpellEffectChance' for e in self.pending):
            self.secondary_rng+=1

    def check_hit(self,_):
        if self.case and self.case.get('force_low_accuracy') and not self.read('hBattleTurn')[0]:
            self.write('wPlayerMoveStructAccuracy',[1])

    def miss(self,_):
        if self.case and not self.read('hBattleTurn')[0]:self.misses+=1

    def faint(self,_):
        if self.case:self.faints+=1

    def press(self,key,frames=90):
        self.p.button(key,delay=8);self.tick(frames)

    def tick(self,frames):
        for _ in range((frames+1)//2):
            self.p.tick(2,True)
            if self.case and len(self.frames)<160:
                self.frames.append(self.p.screen.image.resize((640,576),Image.Resampling.NEAREST))

    def until(self,predicate,limit=200):
        for _ in range(limit):
            if predicate():return
            self.press('a',120)
        self.capture('unexpected_state')
        raise AssertionError({'case':self.case,'snapshot':self.snapshot(),'events':self.events[-6:],
                              'pc':hex(self.p.register_file.PC)})

    def capture(self,label):
        self.p.screen.image.save(OUT/f'{label}.png')
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(OUT/f'{label}_4x.png')

    def set_move(self,move):
        self.write('wBattleMonMoves',[move,1,84,115]);self.write('wBattleMonPP',[40,40,40,40])
        self.write('wCurMoveNum',[0])

    def helper_events(self,helper):return [e for e in self.events if e['helper']==helper]


def main():
    logging.disable(logging.CRITICAL);OUT.mkdir(parents=True,exist_ok=True)
    sym=load_symbols();result={'rom_sha256':hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest(),
        'method':'Normal intro and menu casts; isolated rewound boar battle with documented temporary RAM diagnostics.',
        'ram_diagnostics':['both combatants HP/maxHP240','test moves/PP on battle actor only',
                           'buff stage/screen test fixtures','one physical-miss case accuracy1/256',
                           'status spell MOVE_ANIM1 while actual wCurPlayerMove is14/115/114',
                           'shock MOVE_ANIM1 while actual wCurPlayerMove is52/58/126',
                           'shield lethal case enemy HP1; unchanged maxHP240',
                           'Fire immunity fixture enemy types20/20',
                           'Healing Wave battle actor level6 and HP1/maxHP240',
                           'Windfury sampling varies temporary RNG seed and waits; no CPU substitution',
                           'overworld poison party status8/HP3; bound-inn event fixture'],
        'cases':{}}
    with tempfile.TemporaryDirectory(prefix='peon-spell-test-') as temporary:
        rom=Path(temporary)/'spells.gbc';shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
        s=SpellSession(rom,sym)
        try:
            s.fresh();s.talk((10,10),'up','gornek_quest')
            world_baseline=io.BytesIO();s.p.save_state(world_baseline)
            s.navigate((18,13));s.press('up',30);s.press('a')
            s.until(lambda:s.ready);s.press('b',90);s.tick(30)
            baseline=io.BytesIO();s.p.save_state(baseline)
            def rewind(name,move,**options):
                s.case=None;baseline.seek(0);s.p.load_state(baseline)
                s.case={'name':name,'move':move,**options};s.events=[];s.pending=[];s.pending_command=None
                s.frames=[];s.misses=0;s.faints=0;s.secondary_rng=0
                s.set_move(move)
                s.write('wPeonRockbiterCharge',[0]);s.write('wPeonLightningShieldCharges',[0])
                s.write('wPlayerStatLevels',[7]*7);s.write('wEnemyStatLevels',[7]*7)
                s.write('wPlayerScreens',[0]);s.write('wEnemyScreens',[0])
                s.write('wEnemyMonMoves',[33,0,0,0]);s.write('wEnemyMonPP',[40,0,0,0])
                s.write('wEnemyMonStatus',[0])
            def cast(helper):
                s.until(lambda:bool(s.helper_events(helper)))
                return s.helper_events(helper)[0]
            def record(name,values):
                result['cases'][name]=values;s.capture(name)
                if s.frames:
                    s.frames[0].save(OUT/f'{name}.gif',save_all=True,append_images=s.frames[1:],duration=33,loop=0)
                print(name,'PASS',flush=True)

            rewind('rockbiter_cast',14,different_animation=True)
            e=cast('PeonTryRockbiterEffect')
            assert e['before']['move']==14 and e['before']['animation']==1
            assert e['after']['rock_charge']==1
            assert e['after']['player_stages']==[7]*7
            record('rockbiter_cast',e)
            s.events=[];s.frames=[];s.set_move(1)
            s.until(lambda:len(s.helper_events('PeonConsumeRockbiterDamage'))>=2)
            hits=s.helper_events('PeonConsumeRockbiterDamage')[:2]
            assert hits[0]['before']['rock_charge']==1 and hits[0]['after']['rock_charge']==0
            assert hits[0]['after']['damage']==hits[0]['before']['damage']*2
            assert hits[1]['before']['rock_charge']==0 and hits[1]['after']['damage']==hits[1]['before']['damage']
            record('rockbiter_one_physical_hit',{'hits':hits})

            rewind('rockbiter_nature_keeps_charge',84)
            s.write('wPeonRockbiterCharge',[1])
            s.until(lambda:bool(s.helper_events('PeonConsumeRockbiterDamage')))
            e=s.helper_events('PeonConsumeRockbiterDamage')[0]
            assert e['before']['player_type']>=20 and e['after']['rock_charge']==1
            assert e['after']['damage']==e['before']['damage']
            record('rockbiter_nature_keeps_charge',e)

            rewind('rockbiter_miss_keeps_charge',1,force_low_accuracy=True)
            s.write('wPeonRockbiterCharge',[1]);menus=s.menus
            s.until(lambda:s.misses>0 and s.menus>menus)
            assert s.read('wPeonRockbiterCharge')==[1]
            record('rockbiter_miss_keeps_charge',{'real_hit_check_misses':s.misses,'charge':1,
                                               'enemy_hp_after_miss':s.word('wEnemyMonHP')})

            rewind('lightning_shield_cast',115,different_animation=True)
            e=cast('PeonTryLightningShieldEffect')
            assert e['before']['move']==115 and e['before']['animation']==1
            assert e['after']['shield_charges']==3 and e['after']['player_screens']&16==0
            record('lightning_shield_cast',e)
            s.frames=[];s.set_move(14)
            s.until(lambda:len(s.helper_events('PeonLightningShieldRetaliation'))>=4)
            retaliations=s.helper_events('PeonLightningShieldRetaliation')[:4]
            for index,e in enumerate(retaliations[:3]):
                assert e['before']['shield_charges']==3-index and e['after']['shield_charges']==2-index
                assert e['before']['enemy_hp']-e['after']['enemy_hp']==30
                assert e['before']['damage']==e['after']['damage']
            assert retaliations[3]['before']['shield_charges']==0
            assert retaliations[3]['before']['enemy_hp']==retaliations[3]['after']['enemy_hp']
            record('lightning_shield_three_retaliations',{'retaliations':retaliations})

            rewind('lightning_shield_special_ignored',14)
            s.write('wPeonLightningShieldCharges',[3]);s.write('wEnemyMonMoves',[52,0,0,0]);s.write('wEnemyMonPP',[40,0,0,0])
            s.until(lambda:bool(s.helper_events('PeonLightningShieldRetaliation')))
            e=s.helper_events('PeonLightningShieldRetaliation')[0]
            assert e['before']['enemy_type']>=20 and e['after']['shield_charges']==3
            assert e['after']['enemy_hp']==e['before']['enemy_hp']
            record('lightning_shield_special_ignored',e)

            rewind('lightning_shield_lethal_retaliation',14)
            s.write('wPeonLightningShieldCharges',[3]);s.write('wEnemyMonHP',[0,1])
            s.until(lambda:bool(s.helper_events('PeonLightningShieldRetaliation')))
            e=s.helper_events('PeonLightningShieldRetaliation')[0]
            assert e['before']['enemy_hp']==1 and e['after']['enemy_hp']==0
            assert s.faints>0
            s.until(lambda:s.read('wBattleMode')==[0] and s.read('wScriptMode')==[0])
            record('lightning_shield_lethal_retaliation',{'retaliation':e,'faint_checks':s.faints,
                                                       'battle_returned_to_world':True})

            rewind('purge_enemy_positive_only',114,different_animation=True)
            player=[10,5,9,7,11,6,8];enemy=[9,5,8,6,12,7,10]
            s.write('wPlayerStatLevels',player);s.write('wEnemyStatLevels',enemy)
            s.write('wPlayerScreens',[16]);s.write('wPlayerReflectCount',[5])
            s.write('wEnemyScreens',[28]);s.write('wEnemyReflectCount',[5]);s.write('wEnemyLightScreenCount',[5])
            e=cast('PeonTryPurgeEffect')
            assert e['before']['move']==114 and e['before']['animation']==1
            assert e['after']['enemy_stages']==[7,5,7,6,7,7,7]
            assert e['after']['player_stages']==player
            assert e['after']['enemy_screens']==4 and e['after']['enemy_reflect']==0 and e['after']['enemy_light_screen']==0
            assert e['after']['player_screens']==16 and e['after']['player_reflect']==5
            record('purge_enemy_positive_only',e)

            for name,move in [('flame_shock',52),('flame_burst',126)]:
                rewind(name+'_guaranteed_burn',move,different_animation=True)
                e=cast('BattleCommand_BurnTarget')
                chance=s.helper_events('PeonGuaranteedSpellEffectChance')[0]
                assert chance['before']['move']==move and chance['before']['animation']==1
                assert e['before']['enemy_status']==0 and e['after']['enemy_status']&16
                assert s.secondary_rng==0, 'Guaranteed secondary effect consulted RNG'
                assert e['after']['pp'][0]==39
                record(name+'_guaranteed_burn',{'burn':e,'chance_guard':chance,
                                              'secondary_rng_calls':s.secondary_rng})

            rewind('flame_shock_fire_immunity',52)
            s.write('wEnemyMonType',[20,20])
            e=cast('BattleCommand_BurnTarget')
            assert e['after']['enemy_status']==0
            record('flame_shock_fire_immunity',e)

            rewind('frost_shock_guaranteed_slow',58,different_animation=True)
            e=cast('BattleCommand_SpeedDown')
            chance=s.helper_events('PeonGuaranteedSpellEffectChance')[0]
            assert chance['before']['move']==58 and chance['before']['animation']==1
            assert e['before']['enemy_stages'][2]==7 and e['after']['enemy_stages'][2]==6
            assert s.secondary_rng==0 and e['after']['pp'][0]==39
            record('frost_shock_guaranteed_slow',{'slow':e,'chance_guard':chance,
                                                'secondary_rng_calls':s.secondary_rng})

            rewind('healing_wave_level6',105)
            s.write('wBattleMonLevel',[6]);s.write('wBattleMonHP',[0,1])
            e=cast('BattleCommand_Heal')
            assert e['after']['player_hp']-e['before']['player_hp']==120
            assert e['after']['pp'][0]==39
            assert 'db 6, RECOVER, 10' in (ROOT/'engine/menus/peon_shaman_trainer.asm').read_text()
            record('healing_wave_level6',{'heal':e,'level6_trainer_entry':True,
                                         'trainer_acquisition_tested_separately':True})

            counts={}
            for seed in range(48):
                rewind('windfury_rng_sample',3)
                s.write('hRandomAdd',[(seed*7)&255]);s.write('hRandomSub',[(seed*11)&255])
                s.tick(seed*2);menus=s.menus
                s.until(lambda:s.menus>menus and bool(s.helper_events('BattleCommand_EndLoop')))
                hits=s.helper_events('BattleCommand_ApplyDamage')
                assert 2<=len(hits)<=5, ('Windfury hit count',len(hits))
                assert all(e['before']['enemy_hp']>e['after']['enemy_hp'] for e in hits)
                if len(hits) not in counts:
                    counts[len(hits)]=seed
                    record(f'windfury_{len(hits)}_hits',{'seed_sample':seed,'hits':hits,
                                                       'ordinary_button_cast':True})
                if set(counts)=={2,3,4,5}:break
            assert set(counts)=={2,3,4,5}, ('Windfury range not fully sampled',counts)

            rewind('chain_lightning_single_target',87)
            menus=s.menus
            s.until(lambda:s.menus>menus and bool(s.helper_events('BattleCommand_ApplyDamage')))
            hits=s.helper_events('BattleCommand_ApplyDamage')
            assert len(hits)==1 and hits[0]['before']['move']==87
            assert hits[0]['before']['player_type']>=20
            assert hits[0]['after']['enemy_hp']<hits[0]['before']['enemy_hp']
            record('chain_lightning_single_target',{'hits':hits,'current_one_enemy_limit':True})

            # Normal walking dispatches CountStep -> DoPoisonStep; only the
            # starting health/status and home flags are diagnostic fixtures.
            s.case=None;world_baseline.seek(0);s.p.load_state(world_baseline)
            s.case={'name':'overworld_poison_bound_inn','poison':True}
            s.events=[];s.pending=[];s.pending_command=None;s.frames=[]
            s.write('wPartyMon1HP',[0,3]);s.write('wPartyMon1Status',[8])
            s.write('wPoisonStepCount',[0])
            for flag in ('EVENT_PEON_HOME_DEN','EVENT_PEON_HOME_RAZOR','EVENT_PEON_HOME_SENJIN'):
                index=FLAGS[flag];bank,address=s.sym['wEventFlags'];offset=index//8
                value=s.read('wEventFlags',offset+1)[offset]
                s.p.memory[bank,address+offset]=(value|(1<<(index%8))) if flag.endswith('SENJIN') else (value&~(1<<(index%8)))
            before_money=s.money();before_pp=s.read('wPartyMon1PP',4);heal_calls=s.heal_calls
            s.navigate((11,11))
            # Discard setup navigation steps and begin a clear three-cycle path.
            s.write('wPoisonStepCount',[0]);s.write('wPartyMon1HP',[0,3]);s.events=[];s.pending=[]
            for expected_hp in (2,1):
                for direction in ('right','down','left','up'):s.walk(direction)
                assert s.word('wPartyMon1HP')==expected_hp
                assert s.read('wPartyMon1Status')==[8]
            for direction in ('right','down','left','up'):s.walk(direction)
            s.until(lambda:s.map()==24 and s.read('wScriptMode')==[0])
            assert s.word('wPartyMon1HP')==1 and s.read('wPartyMon1Status')==[0]
            assert s.money()==before_money and s.read('wPartyMon1PP',4)==before_pp
            assert s.heal_calls==heal_calls
            poison=s.helper_events('DoPoisonStep')
            assert len(poison)==3 and [e['before']['party_hp'] for e in poison]==[3,2,1]
            assert s.helper_events('PeonRecoverFromDefeat')
            record('overworld_poison_bound_inn',{'poison_steps':poison,'final_map':s.map(),
                'hp':1,'status_cleared':True,'heal_party_calls':0,'money_unchanged':True,'pp_unchanged':True,
                'ordinary_walking':True,'bound_inn_fixture':'Senjin'})
            s.p.stop(save=False)
        except BaseException:
            s.capture('unexpected_state');s.p.stop(save=False)
            raise
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'rom_sha256':result['rom_sha256'],'passed_cases':list(result['cases'])},indent=2))


if __name__=='__main__':main()
