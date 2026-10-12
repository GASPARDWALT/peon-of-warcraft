#!/usr/bin/env python3
"""Native companion, turn cost, mailbox and battery checks.

Normal sections only use actual controls. The separate pet-kill branch rewinds
a private encounter and declares native HP fixtures, then uses a real potion.
No CPU substitution or user battery file is used.
"""
import argparse
import hashlib
import io
import json
import logging
import shutil
import tempfile
from pathlib import Path

from PIL import Image
from validate_peon_class_routes import ClassSession
from validate_peon_villages import load_symbols, MAPS
from validate_peon_battle_totems import BagSession
from validate_peon_combat_lifecycle import LifecycleSession

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/environment_v025/pet'
MAPS.update({25: ('PeonValleyCrossroads',5,5),26: ('PeonHanazuaCamp',5,5),
             27: ('PeonSarkothBasin',5,5),28: ('PeonCaveApproach',5,5),29: ('PeonValleyExit',5,5)})


class PetSession(ClassSession):
    def __init__(self, rom, symbols, class_index=2, section='normal'):
        self.pet_rounds = []; self.pet_pending = None; self.pet_errors = []
        self.pet_draws = 0; self.menus = 0; self.context = None
        super().__init__(rom, symbols, class_index, section)

    def open(self):
        super().open()
        self.p.hook_register(*self.sym['PeonHandleBetweenTurnEffects.PetTurn'], self.pet_start, None)
        self.p.hook_register(*self.sym['PeonHandleBetweenTurnEffects.PetTurnDone'], self.pet_done, None)
        self.p.hook_register(*self.sym['PeonDrawWarlockBattlePet.done'], self.pet_drawn, None)
        self.p.hook_register(*self.sym['LoadBattleMenu'], self.battle_menu, None)
        self.p.hook_register(*self.sym['StaticMenuJoypad'], self.static_ready, None)
        self.p.hook_register(*self.sym['ExitBattle'], lambda _: self.bag_phase('overworld'), None)
        for label, phase in [('PeonBags','bags_drawing'),('PeonInventory','inventory_drawing'),
                             ('PeonInventory.draw','inventory_drawing'),('PeonInventory.input','inventory'),
                             ('PeonInventory.used_battle_item','using_item')]:
            self.p.hook_register(*self.sym[label], self.bag_phase, phase)
        self.p.hook_register(*self.sym['PeonInterfaceWait'], self.bag_ready, None)

    def battle_menu(self, _):
        self.phase, self.context = 'battle_drawing', 'battle'; self.menus += 1

    def static_ready(self, _):
        if self.context: self.phase = self.context

    def bag_phase(self, phase): self.phase, self.context = phase, None
    def bag_ready(self, _):
        if self.phase == 'bags_drawing': self.phase = 'bags'

    def press(self, key, frames=90):
        if self.read('wBattleMode')[0]:
            self.p.button(key, delay=4); self.p.tick(frames, True)
        else:
            # A late native battle-menu restore may leave the observer's
            # context behind after ExitBattle; do not label inn Yes/No as it.
            if self.phase in ('battle','battle_drawing','using_item'):
                self.phase,self.context = 'overworld',None
            super().press(key, frames)

    def capture(self, name):
        folder = OUT / self.section; folder.mkdir(parents=True, exist_ok=True)
        if self.class_index != 2: name = ('shaman_' if self.class_index == 0 else 'warrior_') + name
        self.p.screen.image.save(folder / (name + '.png'))
        self.p.screen.image.resize((640,576), Image.Resampling.NEAREST).save(folder / (name + '_4x.png'))
        print(name, self.map(), self.position(), self.phase, flush=True)

    def round_snapshot(self):
        return {'enemy_hp': int.from_bytes(bytes(self.read('wEnemyMonHP',2)), 'big'),
                'player_hp': int.from_bytes(bytes(self.read('wBattleMonHP',2)), 'big'),
                'battle_pp': self.read('wBattleMonPP',4), 'party_pp': self.read('wPartyMon1PP',4),
                'player_turns': self.read('wPlayerTurnsTaken')[0],
                'enemy_turns': self.read('wEnemyTurnsTaken')[0], 'battle_turn': self.read('hBattleTurn')[0],
                'background_tile_and_attribute_sha256': hashlib.sha256(bytes(
                    self.read('wTilemap',360)+self.read('wAttrmap',360))).hexdigest()}

    def pet_start(self, _): self.pet_pending = self.round_snapshot()
    def pet_done(self, _):
        try:
            before, after = self.pet_pending, self.round_snapshot()
            assert before and before['player_hp'] > 0 and before['enemy_hp'] > 0
            assert after['enemy_hp'] == before['enemy_hp'] - 1
            assert {k:v for k,v in before.items() if k != 'enemy_hp'} == {
                k:v for k,v in after.items() if k != 'enemy_hp'}, 'pet changed turn/HP/charge state'
            self.pet_rounds.append({'before': before, 'after': after})
            self.pet_pending = None
        except Exception as error: self.pet_errors.append(repr(error))

    def pet_drawn(self, _):
        if self.read('wBattleMode')[0] and self.event('EVENT_PEON_WARLOCK'):
            self.pet_draws += 1

    wait = BagSession.wait
    ready = BagSession.ready
    open_bag_item = BagSession.open_bag_item
    until_world = LifecycleSession.until_world

    @property
    def errors(self): return self.pet_errors

    def companion(self):
        follower = self.read('wObjectFollow_Follower')[0]
        assert self.read('wObjectFollow_Leader') == [0] and 1 <= follower < 13
        actor = self.read('wObjectStructs',13 * 40)[follower * 40:(follower + 1) * 40]
        assert actor[0] == 0x4c and actor[1] == 15, ('wrong native pet actor', actor)
        assert actor[4] & 0x52 == 0x52 and not actor[4] & 0x80, 'pet clipping/deletion flags'
        assert actor[5] & 2, 'pet must have native high OAM priority'
        assert actor[6] & 7 == 0, 'pet must use actual red world palette'
        xy = (actor[16] - 4, actor[17] - 4)
        assert sum(abs(a-b) for a,b in zip(xy,self.position())) <= 2, ('pet fell behind',xy,self.position())
        return {'map': self.map(), 'player': self.position(), 'pet': xy, 'native_object': follower,
                'native_follow_queue_length': self.read('wFollowerMovementQueueLength')[0]}

    def battle_art(self):
        binary = (ROOT / 'gfx/pack/peon_warlock_pet_battle.2bpp').read_bytes()
        assert bytes(self.p.memory[1,0x8880:0x88d0]) == binary
        cells = (5*20+8,5*20+9,6*20+8,6*20+9)
        assert [self.read('wTilemap',360)[i] for i in cells] == [0x88,0x89,0x8a,0x8b]
        assert [self.read('wAttrmap',360)[i] for i in cells] == [0x0e]*4
        return {'native_bank1_vram_exact': True, 'native_backview_cells': [0x88,0x89,0x8a,0x8b]}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--expected-sha'); args = parser.parse_args()
    logging.disable(logging.CRITICAL); OUT.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256((ROOT / 'pokecrystal.gbc').read_bytes()).hexdigest()
    if args.expected_sha: assert digest == args.expected_sha
    report = {'rom_sha256': digest, 'status': 'RUNNING', 'normal_ram_edits': False,
              'user_battery_saves_opened': False, 'normal': {}, 'diagnostic': {}}
    with tempfile.TemporaryDirectory(prefix='peon-warlock-companion-') as temp:
        rom = Path(temp)/'warlock.gbc'; shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
        s = PetSession(rom, load_symbols())
        try:
            s.fresh_class(); s.p.tick(120,True)
            states = [s.companion()]
            for pos in [(12,9),(16,9),(16,7),(16,8),(12,10)]:
                s.navigate(pos); s.p.tick(60,True); states.append(s.companion())
            assert states[3]['pet'] == states[4]['player'], 'normal route must step back through pet tile'
            s.capture('ordinary_native_follow_trail')
            # Actual Horde post, inspecting does not alter items, cash, XP or flags.
            s.navigate((16,7)); s.press('up',30)
            before = s.persistent_snapshot(); s.press('a',120)
            s.capture('ordinary_den_horde_mailbox'); s.close_dialogue()
            assert before == s.persistent_snapshot()
            states.append(s.companion())
            s.navigate((17,5),23); s.p.tick(120,True); states.append(s.companion())
            s.capture('ordinary_imp_inside_inn')
            s.navigate((5,7),14); s.p.tick(120,True); states.append(s.companion())
            s.navigate((20,10),15); s.p.tick(120,True); states.append(s.companion())
            s.capture('ordinary_imp_zone2'); s.navigate((4,12),14); s.p.tick(120,True)
            states.append(s.companion())
            report['normal']['world_follow_and_four_door_zone_transitions'] = states
            report['normal']['mailbox_inspection_no_record_mutation'] = True
            report['normal']['ordinary_player_can_walk_back_through_pet_tile'] = True
            s.talk_plain((10,10),'up'); assert s.event('EVENT_PEON_QUEST_ACCEPTED')
            s.navigate((18,13)); s.press('up',30); s.press('a',60)
            s.wait(lambda:s.phase=='battle',buttons=True)
            s.p.tick(30,True); report['normal']['battle_backview'] = s.battle_art()
            s.capture('ordinary_battle_imp_backview')
            baseline = io.BytesIO(); s.p.save_state(baseline)
            pp = s.read('wPartyMon1PP',4)
            s.until_world(choose_bolt=False)
            assert s.event('EVENT_PEON_QUEST_DONE') and s.read('wBattleResult') == [0]
            assert s.read('wPartyMon1PP',4) == pp and not s.pet_errors
            s.capture('ordinary_imp_first_victory')
            s.rest(); s.navigate((18,14))
            s.wait(lambda:s.phase=='battle',buttons=True); s.until_world(choose_bolt=False)
            assert s.read('wBattleResult') == [0] and s.event('EVENT_PEON_SCORPID_DEFEATED')
            assert len(s.pet_rounds) >= 3 and not s.pet_errors
            report['normal']['native_full_round_firebolts'] = list(s.pet_rounds)
            report['normal']['pet_hits_fixed_1_no_extra_turn_no_charge_cost'] = True
            s.capture('ordinary_native_three_plus_rounds')
            report['normal']['cold_battery_continue'] = s.cold_save()
            report['normal']['cold_battery_companion'] = s.companion()
            # A separate branch is explicitly a temporary HP fixture. A real
            # potion consumes one enemy turn; HP1 opponent then dies to pet.
            baseline.seek(0); s.p.load_state(baseline)
            s.section, s.phase, s.context = 'diagnostic', 'battle', 'battle'
            for key in ('a','b','left','right','up','down'): s.p.button_release(key)
            s.pet_rounds = []; s.pet_errors = []; s.pet_pending = None
            s.write('wEnemyMonHP',[0,1])
            for prefix in ('wBattleMon','wPartyMon1'):
                maximum = int.from_bytes(bytes(s.read(prefix+'MaxHP',2)),'big')
                s.write(prefix+'HP',list((maximum-1).to_bytes(2,'big')))
            items, turns, experience = s.item_quantity(18),len(s.used_moves),s.experience()
            s.open_bag_item(18); s.capture('diagnostic_potion_pet_finisher')
            s.press('a',30)
            s.until_world(choose_bolt=False)
            assert s.item_quantity(18)==items-1 and s.event('EVENT_PEON_QUEST_DONE')
            assert s.experience()>experience and s.read('wBattleResult')==[0]
            assert len(s.pet_rounds)==1 and s.pet_rounds[0]['before']['enemy_hp']==1
            moves=s.used_moves[turns:]
            assert [m['turn'] for m in moves]==[1], ('potion must cost one enemy move only',moves)
            assert not s.pet_errors
            report['diagnostic']['hp1_potion_pet_kill']={'fixture':'Private battle rewind; opponent HP1; player HP max-1.',
                'native_potion_consumed':True,'one_enemy_turn':True,'native_victory_xp_and_quest_death_flag':True,
                'pet_round':s.pet_rounds[0]}
            s.capture('diagnostic_pet_finisher_native_victory')
            # New ordinary characters of the other two classes retain their
            # normal actors and do not accidentally inherit a native follower.
            absent = {}
            for index, name in ((0,'shaman'),(1,'warrior')):
                other_rom = Path(temp)/(name + '.gbc'); shutil.copyfile(ROOT/'pokecrystal.gbc',other_rom)
                other = PetSession(other_rom,load_symbols(),index,section='normal/no_pet')
                try:
                    other.fresh_class(); other.p.tick(120,True)
                    assert other.read('wObjectFollow_Leader',2) == [255,255]
                    actors = other.read('wObjectStructs',13*40)
                    assert not any(actors[i*40] == 0x4c and actors[i*40+1] == 15 for i in range(13))
                    assert other.pet_draws == 0 and not other.pet_rounds
                    other.capture('ordinary_class_has_no_imp')
                    absent[name]={'ordinary_buttons_only':True,'follower_absent':True,'pet_actor_absent':True}
                finally: other.p.stop(save=False)
            report['normal']['other_classes_do_not_inherit_companion'] = absent
            report['status']='PASS'
        except Exception as error:
            report['failure']=repr(error); s.capture('unexpected_state'); raise
        finally:
            if s.p: s.p.stop(save=False)
            (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
