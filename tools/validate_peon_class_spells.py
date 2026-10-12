#!/usr/bin/env python3
"""Native class move diagnostics; gameplay acquisition is checked separately.

Completes the ordinary Shaman intro, then uses documented temporary class
flags/loadouts to start three native battles and verify their affinity hook.
A rewound boar encounter tests all 24 class spells with real button casts,
interpreter, paired charge records, native status/stages, residual damage and
animation frames. No source ROM, user save or CPU path is substituted.
"""
from pathlib import Path
import argparse, hashlib, io, json, logging, shutil, tempfile
from PIL import Image
import validate_peon_spell_effects as retained
from validate_durotar_v022_quests import FLAGS, load_symbols

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'references/generated/environment_v025/classes/spells'
retained.OUT=OUT
MANIFEST=ROOT/'references/generated/environment_v025/classes/spell_manifest.json'
COMMANDS=['BattleCommand_ApplyDamage','BattleCommand_DrainTarget','BattleCommand_Poison',
          'BattleCommand_PoisonTarget','BattleCommand_BurnTarget','BattleCommand_StatUp',
          'BattleCommand_StatDown']
WARLOCK={'SHADOW_BALL','ABSORB','POISONPOWDER','SAND_ATTACK','FIRE_SPIN','KINESIS',
         'MEGA_DRAIN','NIGHT_SHADE','SMOG','FIRE_PUNCH','AMNESIA','TOXIC'}

class ClassSpellSession(retained.SpellSession):
    def open(self):
        super().open()
        for command in COMMANDS:
            if command not in retained.COMMANDS:
                self.p.hook_register(*self.sym[command],self.command,command)
        self.p.hook_register(*self.sym['ResidualDamage'],self.residual_enter,None)
        self.p.hook_register(*self.sym['ResidualDamage.did_psn_brn'],self.residual_done,None)
        self.p.hook_register(*self.sym['PeonApplyClassBattleAffinity'],self.affinity_enter,None)
        self.p.hook_register(*self.sym['PeonPrintClassPoisonText'],self.dot_text,None)
        self.residuals=[];self.residual_pending=None;self.affinity_entries=0;self.dot_texts=0
        self.name_pending=[];self.name_bc_returns=0;self.name_errors=[]
        self.p.hook_register(*self.sym['GetMoveName'],self.name_enter,None)
        self.p.hook_register(*self.sym['GetMoveName.named'],self.name_named,None)
    def name_enter(self,_):
        self.name_pending.append({'sp':self.p.register_file.SP,'bc':(self.p.register_file.B<<8)|self.p.register_file.C})
    def name_named(self,_):
        if not self.name_pending:
            self.name_errors.append({'kind':'name return without observed entry'})
            return
        entry=self.name_pending.pop()
        current_bc=(self.p.register_file.B<<8)|self.p.register_file.C
        if self.p.register_file.SP!=entry['sp']-2:
            self.name_errors.append({'kind':'move-name unbalanced stack','before':entry,'sp':self.p.register_file.SP})
        if current_bc!=entry['bc']:
            self.name_errors.append({'kind':'class move-name helper changed BC','before':entry,'bc':current_bc})
        self.name_bc_returns+=1
    def affinity_enter(self,_):self.affinity_entries+=1
    def dot_text(self,_):
        if self.case is not None:self.dot_texts+=1
    def residual_enter(self,_):
        if self.case is not None:
            self.residual_pending={'before':self.snapshot()}
    def residual_done(self,_):
        if self.residual_pending:
            self.residual_pending['after']=self.snapshot()
            self.residuals.append(self.residual_pending);self.residual_pending=None
    def flag(self,name,enabled):
        i=FLAGS[name];bank,address=self.sym['wEventFlags'];offset=i//8
        v=self.p.memory[bank,address+offset]
        self.p.memory[bank,address+offset]=v|(1<<(i%8)) if enabled else v&~(1<<(i%8))
    def class_flags(self,slug):
        self.flag('EVENT_PEON_WARRIOR',slug=='warrior')
        self.flag('EVENT_PEON_WARLOCK',slug=='warlock')
    def snapshot(self):
        data=super().snapshot()
        data.update({'party_pp':self.read('wPartyMon1PP',4),
                     'party_moves':self.read('wPartyMon1Moves',4),
                     'battle_moves':self.read('wBattleMonMoves',4),
                     'affinity':self.read('wBattleMonType',2),
                     'enemy_affinity':self.read('wEnemyMonType',2),
                     'enemy_toxic_count':self.read('wEnemyToxicCount')[0]})
        return data
    def press(self,key,frames=90):
        self.p.button(key,delay=4);self.tick(frames)
    def command(self,command):
        if self.case and not self.read('hBattleTurn')[0]:
            self.pending_command={'helper':command,'before':self.snapshot(),
                                  'entry_sp':self.p.register_file.SP}
    def capture(self,name):
        self.p.screen.image.save(OUT/f'{name}.png')
        self.p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(OUT/f'{name}_4x.png')
    def enter(self,helper):
        # Retained spell helpers are not mutated. Track their native returns
        # only for the shared elemental secondary-effect checks.
        if helper=='PeonGuaranteedSpellEffectChance' and self.case is not None:
            if not self.read('hBattleTurn')[0]:
                event={'helper':helper,'before':self.snapshot(),'entry_sp':self.p.register_file.SP}
                self.pending.append(event)
        elif helper in ('PeonConsumeRockbiterDamage','PeonLightningShieldRetaliation'):
            return
        else:
            super().enter(helper)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--expected-rom-sha256')
    args=parser.parse_args();logging.disable(logging.CRITICAL);OUT.mkdir(parents=True,exist_ok=True)
    rom_sha=hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest()
    if args.expected_rom_sha256:assert args.expected_rom_sha256==rom_sha
    spells=json.loads(MANIFEST.read_text());sym=load_symbols()
    result={'rom_sha256':rom_sha,'status':'RUNNING',
      'method':'Ordinary intro/navigation/battle start and real native menu casts; isolated documented temporary-RAM class/loadout/status fixtures.',
      'diagnostic_fixtures':['class flags on intro-completed temporary Shaman save (normal class acquisition checked by class_routes)',
        '24 individual learned move/paired PP fixtures in rewound native boar battle',
        'player HP120/max240; enemy HP240/max240 to observe effects before death',
        'enemy SPLASH to isolate drains and buffs',
        'enemy poison affinity [BUG,POISON] for native scorpid wound/curse immunity check',
        'neutral stages, no preexisting statuses/screens or transient totem/buffs'],
      'affinities':{},'cases':{}}
    with tempfile.TemporaryDirectory(prefix='peon-v025-class-spells-') as temporary:
        rom=Path(temporary)/'classes.gbc';shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
        s=ClassSpellSession(rom,sym)
        try:
            s.fresh();s.talk((10,10),'up','gornek_quest')
            world=io.BytesIO();s.p.save_state(world)
            baselines={}
            for slug,basic,typ in [('shaman',84,23),('warrior',2,0),('warlock',247,27)]:
                s.case=None;world.seek(0);s.p.load_state(world);s.class_flags(slug)
                s.write('wPartyMon1Moves',[1,basic,0,0]);s.write('wPartyMon1PP',[35,25,0,0])
                s.ready=False;s.navigate((18,13));s.press('up',30);s.press('a')
                s.until(lambda:s.ready)
                assert s.read('wBattleMonType',2)==[typ,typ],(slug,s.snapshot())
                result['affinities'][slug]={'types':s.read('wBattleMonType',2),
                    'native_InitBattleMon_hook_executed':s.affinity_entries>0,
                    'party_move_record':s.read('wPartyMon1Moves',4)}
                s.press('b',90);s.tick(30)
                state=io.BytesIO();s.p.save_state(state);baselines[slug]=state
                s.capture(slug+'_native_affinity_battle')
            for key,spec in spells.items():
                slug='warlock' if key in WARLOCK else 'warrior'
                s.case=None;state=baselines[slug];state.seek(0);s.p.load_state(state)
                s.case={'name':key,'move':spec['id']};s.events=[];s.pending=[];s.pending_command=None
                s.frames=[];s.residuals=[];s.residual_pending=None;s.dot_texts=0;s.secondary_rng=0;s.misses=0
                move=spec['id'];pp=spec['charges'];basic=247 if slug=='warlock' else 2
                # All four native slots and their paired party/battle charges.
                s.write('wPartyMon1Moves',[move,1,basic,0]);s.write('wBattleMonMoves',[move,1,basic,0])
                s.write('wPartyMon1PP',[pp,35,25,0]);s.write('wBattleMonPP',[pp,35,25,0]);s.write('wCurMoveNum',[0])
                for actor in ('wBattleMon','wPartyMon1'):
                    s.write(actor+'HP',[0,120]);s.write(actor+'MaxHP',[0,240]);s.write(actor+'Status',[0])
                s.write('wEnemyMonHP',[0,240]);s.write('wEnemyMonMaxHP',[0,240]);s.write('wEnemyMonStatus',[0])
                s.write('wEnemyMonType',[7,3]) # BUG/POISON = native scorpid affinity
                s.write('wEnemyMonMoves',[150,0,0,0]);s.write('wEnemyMonPP',[40,0,0,0])
                s.write('wPlayerStatLevels',[7]*7);s.write('wEnemyStatLevels',[7]*7)
                s.write('wPlayerScreens',[0]);s.write('wEnemyScreens',[0]);s.write('wEnemySubStatus5',[0])
                for field in ('wPeonRockbiterCharge','wPeonLightningShieldCharges','wPeonEarthTotemActive','wEnemyToxicCount'):
                    s.write(field,[0])
                before=s.snapshot();menus=s.menus
                s.until(lambda:s.menus>menus and bool(s.events),limit=80)
                after=s.snapshot()
                assert before['pp'][0]==pp and after['pp'][0]==pp-1,(key,'battle PP',before,after)
                assert after['party_pp'][0]==pp-1,(key,'party PP',before,after)
                assert after['affinity']==([27,27] if slug=='warlock' else [0,0])
                if spec['effect']=='EFFECT_NORMAL_HIT':
                    hits=s.helper_events('BattleCommand_ApplyDamage');assert hits and hits[0]['after']['enemy_hp']<hits[0]['before']['enemy_hp'],(key,s.events)
                elif spec['effect']=='EFFECT_LEECH_HIT':
                    drains=s.helper_events('BattleCommand_DrainTarget');assert drains and drains[0]['after']['player_hp']>drains[0]['before']['player_hp'],(key,s.events)
                elif spec['effect'] in ('EFFECT_POISON','EFFECT_TOXIC','EFFECT_POISON_HIT'):
                    assert after['enemy_status']&8,(key,'DOT not applied to poison-type scorpid',s.events)
                    assert s.dot_texts>0,(key,'custom curse/wound cast text absent')
                    dots=[v for v in s.residuals if v['before']['turn']==1 and v['before']['enemy_status']&8]
                    assert dots and any(v['after']['enemy_hp']<v['before']['enemy_hp'] for v in dots),(key,s.residuals)
                    if spec['effect']=='EFFECT_TOXIC':assert after['enemy_toxic_count']>=1,(key,after)
                elif spec['effect']=='EFFECT_BURN_HIT':assert after['enemy_status']&16,(key,s.events)
                elif spec['effect']=='EFFECT_DEFENSE_UP':assert after['player_stages'][1]==8,(key,after)
                elif spec['effect']=='EFFECT_DEFENSE_UP_2':assert after['player_stages'][1]==9,(key,after)
                elif spec['effect']=='EFFECT_SP_DEF_UP_2':assert after['player_stages'][4]==9,(key,after)
                elif spec['effect']=='EFFECT_ATTACK_UP':assert after['player_stages'][0]==8,(key,after)
                elif spec['effect']=='EFFECT_ATTACK_DOWN':assert after['enemy_stages'][0]==6,(key,after)
                elif spec['effect']=='EFFECT_ATTACK_DOWN_2':assert after['enemy_stages'][0]==5,(key,after)
                elif spec['effect']=='EFFECT_SPEED_DOWN':assert after['enemy_stages'][2]==6,(key,after)
                elif spec['effect']=='EFFECT_ACCURACY_DOWN':assert after['enemy_stages'][5]==6,(key,after)
                else:raise AssertionError((key,'unrecognized effect',spec))
                result['cases'][key]={'class':slug,'id':move,'name':spec['name'],'effect':spec['effect'],
                    'before':before,'after':after,'native_commands':s.events,'native_residuals':s.residuals,
                    'custom_DOT_text_calls':s.dot_texts,'captured_animation_frames':len(s.frames),
                    'paired_charge_spend':True}
                s.capture(key.lower()+'_after_cast')
                if s.frames:
                    s.frames[0].save(OUT/(key.lower()+'.gif'),save_all=True,append_images=s.frames[1:],duration=33,loop=0)
                print(slug,key,'PASS',flush=True)
            s.p.stop(save=False)
        except BaseException:
            s.capture('failure');s.p.stop(save=False);raise
    assert hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest()==rom_sha
    assert s.name_bc_returns > 0 and not s.name_pending and not s.name_errors, ('Native GetMoveName return checks failed', s.name_errors[:10], s.name_pending)
    result['move_name_native_bc_preserved_returns']=s.name_bc_returns
    result['status']='PASS';result['all_checks_passed']=True
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'rom_sha256':rom_sha,'status':'PASS','native_casts':len(result['cases'])},indent=2))

if __name__=='__main__':main()
