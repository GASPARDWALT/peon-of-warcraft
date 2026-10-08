#!/usr/bin/env python3
"""Measure native apprentice combat attrition in isolated, declared fixtures.

The ordinary intro, fight menus, damage, poison, PP, XP, levels and recovery
execute in the ROM. A temporary starter level and encounter species/level are
set before the native generators run. Rewinding only the encounter's world
state lets another foe spawn while retaining the complete native party record:
HP/status/PP/XP/stats/held weapon are copied unchanged between fights. No user
save, ROM byte, CPU register, damage result or RNG return is substituted.
"""
import argparse
import hashlib
import io
import json
import logging
from pathlib import Path
import shutil
import tempfile

from PIL import Image

from validate_durotar_v022_quests import QuestSession, load_symbols

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'references/generated/durotar_v023/combat_balance'
ENEMIES={'boar':19,'scorpid':27,'imp':74}
ATTACKS={'mace':1,'bolt':84}


def summarize(chains):
    result={}
    for attack in ('mace','bolt','flame_then_bolt'):
        cases=[c for c in chains if c['attack']==attack and c['enemy_level']==c['starting_level']]
        if not cases:continue
        two=[c for c in cases if len(c['battles'])>=2 and c['battles'][1]['outcome']=='win']
        three=[c for c in cases if len(c['battles'])>=3 and c['battles'][2]['outcome']=='win']
        needs=[c for c in cases if len(c['battles'])<3 or c['battles'][2]['outcome']=='defeat' or
               c['battles'][2]['after']['hp']*4<=c['battles'][2]['after']['max_hp']]
        result[attack]={'chains':len(cases),'survive_two':len(two),'survive_three':len(three),
            'third_defeat_or_at_most_quarter_hp':len(needs),
            'hp_after_second_wins':[c['battles'][1]['after']['hp'] for c in two],
            'max_hp_after_second_wins':[c['battles'][1]['after']['max_hp'] for c in two]}
    return result


def finish_final(report):
    assert report['enemy_level_policy']=='match_current_native_player_level_each_fight'
    assert sorted(report['levels'])==[2,4,6] and len(report['seeds'])>=3,'Final balance requires levels2/4/6 and at least three seeds'
    report['summary']=summarize(report['chains']);bolt=report['summary']['bolt']
    potions=[c for c in report['chains'] if 'third_with_one_potion' in c]
    improved=[]
    for case in potions:
        original=case['battles'][2];assisted=case['third_with_one_potion']['battle']
        if assisted['outcome']=='win' and (original['outcome']=='defeat' or assisted['after']['hp']>original['after']['hp']):
            improved.append(case)
    higher=[c for c in report['chains'] if c['enemy_level']==c['starting_level']+2]
    hard=[c for c in higher if c['battles'][0]['outcome']=='defeat' or
          c['battles'][0]['after']['hp']*2<=c['battles'][0]['after']['max_hp']]
    report['potion_summary']={'eligible_third_fights':len(potions),'meaningfully_improved':len(improved),
        'assisted_third_victories':sum(c['third_with_one_potion']['battle']['outcome']=='win' for c in potions)}
    report['higher_level_summary']={'chains':len(higher),'defeat_or_at_most_half_hp':len(hard),
        'victories':sum(c['battles'][0]['outcome']=='win' for c in higher)}
    report['checks']={
        'two_equal_bolt_fights_survived_at_least_75_percent':bolt['survive_two']*4>=bolt['chains']*3,
        'third_equal_bolt_fight_defeat_or_at_most_quarter_hp_at_least_50_percent':
            bolt['third_defeat_or_at_most_quarter_hp']*2>=bolt['chains'],
        'one_real_potion_improves_a_majority_of_eligible_third_fights':bool(potions) and len(improved)*2>len(potions),
        'plus_two_level_foes_cause_defeat_or_at_most_half_hp_in_majority':bool(higher) and len(hard)*2>len(higher),
        'no_free_heal_party_in_any_encounter':all(b['heal_party_calls']==0 for c in report['chains'] for b in c['battles']),
        'equal_enemy_matches_current_native_level_each_fight':all(b['enemy']['level']==b['before']['level']
            for c in report['chains'] if c['enemy_level']==c['starting_level'] for b in c['battles']),
        'native_health_status_charges_and_xp_carry':all(c['battles'][i]['before']==c['battles'][i-1]['after']
            for c in report['chains'] for i in range(1,len(c['battles'])))}
    assert all(report['checks'].values()),{'checks':report['checks'],'summary':report['summary'],
                                          'potions':report['potion_summary'],'higher':report['higher_level_summary']}
    report['cases']={f"lv{c['starting_level']}_{c['enemy']}_{c['attack']}_enemy{c['enemy_level']}_seed{c['seed']}":c
                     for c in report['chains']}
    report['all_checks_passed']=True
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')


class BalanceSession(QuestSession):
    def __init__(self,rom,sym,level):
        self.level=level;self.case=None;self.ui='none';self.main_count=0
        self.moves_ready=0;self.creating=False;self.turns=[];self.defeated=False
        self.captured=False;self.potion_calls=0
        super().__init__(rom,sym)

    def open(self):
        super().open()
        self.p.hook_register(*self.sym['GeneratePartyMonStats'],self.starter,None)
        self.p.hook_register(*self.sym['PeonInitializeShaman'],self.finish_starter,None)
        self.p.hook_deregister(*self.sym['LoadTrainerOrWildMonPic'])
        self.p.hook_register(*self.sym['LoadTrainerOrWildMonPic'],self.encounter,None)
        self.p.hook_register(*self.sym['_StaticMenuJoypad'],self.menu_ready,None)
        self.p.hook_register(*self.sym['MoveSelectionScreen.interpret_joypad'],self.move_ready,None)
        self.p.hook_register(*self.sym['DoTurn'],lambda _:setattr(self,'ui','action'),None)
        self.p.hook_register(*self.sym['BattleCommand_ApplyDamage'],self.damage,None)
        self.p.hook_register(*self.sym['BattleCommand_CheckFaint'],self.faint,None)
        self.p.hook_register(*self.sym['PeonRecoverFromDefeat'],self.recovery,None)
        self.p.hook_register(*self.sym['StartMenu.GetInput'],lambda _:setattr(self,'ui','start_menu'),None)
        self.p.hook_register(*self.sym['PeonInterfaceWait'],lambda _:setattr(self,'ui','bags_ready'),None)
        self.p.hook_register(*self.sym['PeonInventory.input'],lambda _:setattr(self,'ui','inventory'),None)
        self.p.hook_register(*self.sym['PeonTryUseMinorPotion'],lambda _:setattr(self,'potion_calls',self.potion_calls+1),None)

    def write(self,name,values):
        bank,address=self.sym[name]
        for i,value in enumerate(values):
            if address>=0xe000:self.p.memory[address+i]=value
            else:self.p.memory[bank,address+i]=value

    def word(self,name):return int.from_bytes(bytes(self.read(name,2)),'big')

    def starter(self,_):
        if self.read('wCurPartySpecies')==[66] and self.read('wBattleMode')==[0]:
            self.write('wCurPartyLevel',[self.level]);self.creating=True
            self.write('hRandomAdd',[73]);self.write('hRandomSub',[151])

    def finish_starter(self,_):
        self.creating=False
        assert self.read('wPartyMon1Level')==[self.level],('Native starter level',self.level,self.read('wPartyMon1Level'))

    def encounter(self,_):
        self.encounter_loads+=1
        if self.case:
            self.write('wTempWildMonSpecies',[self.case['species']])
            self.write('wCurPartyLevel',[self.case['enemy_level']])
            self.write('hRandomAdd',[self.case['seed']])
            self.write('hRandomSub',[self.case['seed']^0xa5])

    def menu_ready(self,_):
        pointer=int.from_bytes(bytes(self.read('wMenuData_2DMenuItemStringsAddr',2)),'little')
        if self.read('wBattleMode')[0] and pointer==self.sym['BattleMenuHeader.Text'][1]:
            self.ui='main';self.main_count+=1;self.p.button_release('a')

    def move_ready(self,_):self.ui='moves';self.moves_ready+=1

    def damage(self,_):
        if not self.case:return
        turn=self.read('hBattleTurn')[0]
        self.turns.append({'who':'enemy' if turn else 'player',
            'move':self.read('wCurEnemyMove' if turn else 'wCurPlayerMove')[0],
            'rolled_damage':self.word('wCurDamage'),
            'player_hp':self.word('wBattleMonHP'),'enemy_hp':self.word('wEnemyMonHP'),
            'player_status':self.read('wBattleMonStatus')[0],
            'enemy_status':self.read('wEnemyMonStatus')[0]})

    def faint(self,_):
        if self.case and self.word('wBattleMonHP')==0:self.defeated=True

    def recovery(self,_):
        # Poison residual damage can enter LostBattle without a move-script
        # CheckFaint command. Verify the native zero-HP recovery input too.
        if self.case and self.word('wPartyMon1HP')==0:self.defeated=True

    def capture(self,label):
        directory=OUT/'in_game';directory.mkdir(exist_ok=True,parents=True)
        self.p.screen.image.save(directory/f'{label}.png')
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(directory/f'{label}_4x.png')

    def tick(self,frames):self.p.tick(frames,True)
    def press(self,key,frames=40):self.p.button(key,delay=4);self.tick(frames)
    def release(self):
        for key in ('a','b','up','down','left','right','start','select'):self.p.button_release(key)

    def party(self):
        return self.read('wPartyMon1Species',self.sym['wPartyMon2Species'][1]-self.sym['wPartyMon1Species'][1])

    def actor(self,enemy=False):
        prefix='wEnemyMon' if enemy else 'wPartyMon1'
        return {'species':self.read(prefix+'Species')[0],'level':self.read(prefix+'Level')[0],
                'hp':self.word(prefix+'HP'),'max_hp':self.word(prefix+'MaxHP'),
                'status':self.read(prefix+'Status')[0],'dvs':self.read(prefix+'DVs',2),
                'stats':[self.word(prefix+x) for x in ('Attack','Defense','Speed','SpclAtk','SpclDef')],
                'moves':self.read(prefix+'Moves',4),'pp':self.read(prefix+'PP',4),
                **({} if enemy else {'xp':int.from_bytes(bytes(self.read('wPartyMon1Exp',3)),'big'),
                                    'held_item':self.read('wPartyMon1Item')[0]})}

    def use_potion(self,label):
        before=self.actor();heals=self.heal_calls;calls=self.potion_calls
        # One declared diagnostic stack, then entirely ordinary menu use.
        self.write('wNumItems',[1]);self.write('wItems',[18,1,255])
        self.ui='world';self.press('start',120)
        assert self.ui=='start_menu',('Start menu not ready',self.ui)
        items=self.read('wMenuItemsList',16);target=items[1:1+items[0]].index(2)+1
        for _ in range(12):
            cursor=self.read('wMenuCursorY')[0]
            if cursor==target:break
            self.press('up' if cursor>target else 'down',30)
        assert self.read('wMenuCursorY')==[target],('Start Bags cursor',target,self.read('wMenuCursorY'))
        self.press('a',150);assert self.ui=='bags_ready',('Bags not ready',self.ui)
        self.press('a',150);assert self.ui=='inventory',('Inventory not ready',self.ui)
        self.capture(label+'_potion_selected');self.press('a',150)
        assert self.potion_calls==calls+1,'Potion helper was not called through inventory'
        after=self.actor()
        assert after['hp']==min(before['max_hp'],before['hp']+20),('Potion native heal',before,after)
        assert self.read('wNumItems')==[0] and self.heal_calls==heals,'Potion not consumed/free full heal'
        assert after['status']==before['status'] and after['pp']==before['pp'],'Potion unexpectedly cleared poison/refilled spells'
        self.capture(label+'_potion_used')
        self.press('b',150);self.press('b',150);self.release();self.tick(80)
        assert self.read('wScriptMode')==[0] and self.read('wBattleMode')==[0]
        return {'before':before,'after':after,'native_item_helper_calls':1,
                'ordinary_menu_buttons':True,'stack_consumed':True,'heal_party_calls':0}

    def fight(self,label,move):
        before=self.actor();heal_before=self.heal_calls
        self.turns=[];self.defeated=False;self.ui='entering';entered=False
        enemies=None;captured=False;chosen=0
        self.press('a',4)
        for frame in range(30000):
            mode=self.read('wBattleMode')[0]
            if mode:entered=True
            if entered and not mode and self.read('wScriptMode')==[0]:break
            if self.ui=='main':
                self.release();self.tick(30)
                if enemies is None:
                    enemies=self.actor(True)
                    assert enemies['species']==self.case['species'] and enemies['level']==self.case['enemy_level']
                if not captured:
                    self.capture(label+'_start');captured=True
                self.ui='opening_moves';self.press('a',4)
            elif self.ui=='moves':
                self.release();self.tick(20)
                moves=self.read('wBattleMonMoves',4)
                selected=52 if self.case.get('flame_strategy') and chosen==0 and self.case['species']!=74 else move
                assert selected in moves,(label,'Missing diagnostic move',selected,moves)
                target=moves.index(selected)+1
                for _ in range(6):
                    cursor=self.read('wMenuCursorY')[0]
                    if cursor==target:break
                    self.press('up' if cursor>target else 'down',20)
                assert self.read('wMenuCursorY')==[target],('Move cursor',target,self.read('wMenuCursorY'))
                chosen+=1;self.ui='submitted';self.press('a',4)
            elif frame%24==0:self.press('a',4)
            else:self.tick(1)
        else:
            self.capture(label+'_unexpected')
            raise AssertionError((label,'Battle timed out',self.ui,self.actor(),self.turns[-8:]))
        self.release();self.tick(60)
        assert entered and self.heal_calls==heal_before,(label,'No battle/free heal',entered,self.heal_calls,heal_before)
        assert enemies is not None
        after=self.actor();outcome=self.read('wBattleResult')[0]&0x3f
        assert outcome in (0,1),(label,'Unexpected result',outcome)
        if outcome==1:
            assert self.defeated and after['hp']==1 and after['status']==0,(label,'Native defeat recovery',after)
        self.capture(label+'_end')
        return {'before':before,'enemy':enemies,'after':after,'outcome':'defeat' if outcome else 'win',
                'player_chosen_turns':chosen,'native_damage_events':self.turns,'heal_party_calls':0,
                'native_defeat_recovery':bool(outcome)}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',default='final')
    parser.add_argument('--seeds',default='17,143,221');parser.add_argument('--levels',default='2,4,6')
    parser.add_argument('--higher',action='store_true');parser.add_argument('--fixed-enemies',action='store_true')
    parser.add_argument('--potion-third',action='store_true');parser.add_argument('--flame',action='store_true')
    parser.add_argument('--combine',help='Combine three current-SHA per-level measurement reports with this prefix')
    args=parser.parse_args()
    seeds=list(map(int,args.seeds.split(',')));levels=list(map(int,args.levels.split(',')))
    logging.disable(logging.CRITICAL);OUT.mkdir(parents=True,exist_ok=True)
    if args.stage=='final':args.higher=args.potion_third=args.flame=True
    if args.combine:
        parts=[json.loads((OUT/f'{args.combine}_lv{level}_native_balance.json').read_text()) for level in (2,4,6)]
        sha=hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest()
        assert all(p['rom_sha256']==sha and p['all_checks_passed'] for p in parts),'Measurements do not match current frozen ROM'
        report={**parts[0],'stage':'final','levels':[2,4,6],
                'chains':[c for p in parts for c in p['chains']],
                'native_measurement_reports':[f'{args.combine}_lv{level}_native_balance.json' for level in (2,4,6)]}
        finish_final(report);print(json.dumps({k:report[k] for k in ('rom_sha256','summary','potion_summary','higher_level_summary','checks')},indent=2));return
    report={'rom_sha256':hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest(),
        'stage':args.stage,'method':'Real ROM combat and menus; diagnostic encounter/level/RNG-seed fixtures, complete native party carried between world rewinds.',
        'diagnostic_ram_changes':['starter level before native stats/XP generator; initial RNG state73/151',
            'scripted boar encounter replaced by requested creature/level before native enemy generator',
            'hRandomAdd/Sub seeded at each encounter; native hardware RNG and crit/status chances remain',
            'world savestate rewound between fights while native party record is restored byte-for-byte'],
        'excluded_from_comparison':['Walking poison attrition between distant encounters; no map travel in fixture',
            'Gear upgrades, Earth Totem and Healing Wave; main unassisted comparisons use starter mace/bolt only'],
        'enemy_level_policy':'fixed_initial_level' if args.fixed_enemies else 'match_current_native_player_level_each_fight',
        'levels':levels,'seeds':seeds,'chains':[]}
    if args.potion_third:
        report['diagnostic_ram_changes'].append('one temporary potion stack before native inventory use; +20 HP is produced only by item code')
    if args.flame:
        report['diagnostic_ram_changes'].append('level4+ Flame Shock/15 charges in diagnostic party slot3; acquisition is tested separately')
    sym=load_symbols()
    with tempfile.TemporaryDirectory(prefix='peon-balance-') as temp:
        rom=Path(temp)/'balance.gbc';shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
        for level in levels:
            s=BalanceSession(rom,sym,level)
            try:
                s.fresh();s.talk((10,10),'up','gornek_balance')
                s.navigate((18,13));s.press('up',30)
                base=io.BytesIO();s.p.save_state(base);initial=s.party()
                for name,species in ENEMIES.items():
                    attacks=dict(ATTACKS)
                    if args.flame and level>=4:attacks['flame_then_bolt']=84
                    for attack,move in attacks.items():
                        for seed in seeds:
                            carry=initial;chain={'enemy':name,'starting_level':level,'enemy_level':level,
                                'attack':attack,'seed':seed,'level_policy':report['enemy_level_policy'],'battles':[]}
                            if attack=='flame_then_bolt':
                                base.seek(0);s.p.load_state(base);s.write('wPartyMon1Species',initial)
                                s.write('wPartyMon1Moves',[1,84,52,0]);s.write('wPartyMon1PP',[35,30,15,0]);carry=s.party()
                            third_party=None;third_level=None
                            for battle in range(3):
                                base.seek(0);s.p.load_state(base);s.release()
                                s.write('wPartyMon1Species',carry)
                                assert s.party()==carry,'Native party carry was altered'
                                enemy_level=level if args.fixed_enemies else s.read('wPartyMon1Level')[0]
                                s.case={'species':species,'enemy_level':enemy_level,'seed':(seed+battle*41)&255,
                                        'flame_strategy':attack=='flame_then_bolt'}
                                if battle==2:third_party=carry;third_level=enemy_level
                                result=s.fight(f'{args.stage}_lv{level}_{name}_{attack}_seed{seed}_{battle+1}',move)
                                assert args.fixed_enemies or result['enemy']['level']==result['before']['level'],'Equal-level fixture mismatch'
                                chain['battles'].append(result);carry=s.party()
                                if result['outcome']=='defeat':break
                            if args.potion_third and attack=='bolt' and third_party is not None:
                                base.seek(0);s.p.load_state(base);s.release();s.write('wPartyMon1Species',third_party)
                                potion=s.use_potion(f'{args.stage}_lv{level}_{name}_seed{seed}')
                                s.case={'species':species,'enemy_level':third_level,'seed':(seed+82)&255}
                                assisted=s.fight(f'{args.stage}_lv{level}_{name}_seed{seed}_potion_third',84)
                                chain['third_with_one_potion']={'potion':potion,'battle':assisted}
                            report['chains'].append(chain)
                            print(level,name,attack,seed,[(b['outcome'],b['after']['hp'],b['after']['level']) for b in chain['battles']],flush=True)
                    if args.higher:
                        for seed in seeds:
                            base.seek(0);s.p.load_state(base);s.release();s.write('wPartyMon1Species',initial)
                            s.case={'species':species,'enemy_level':level+2,'seed':seed}
                            result=s.fight(f'{args.stage}_lv{level}_{name}_higher_seed{seed}',84)
                            report['chains'].append({'enemy':name,'starting_level':level,'enemy_level':level+2,
                                'attack':'bolt','seed':seed,'battles':[result]})
            finally:s.p.stop(save=False)
    report['all_checks_passed']=True
    (OUT/f'{args.stage}_native_balance.json').write_text(json.dumps(report,indent=2)+'\n')
    if args.stage=='final':finish_final(report)
    print('Native balance report:',len(report['chains']),'chains',report['rom_sha256'],flush=True)


if __name__=='__main__':main()
