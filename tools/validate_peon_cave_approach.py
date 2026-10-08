#!/usr/bin/env python3
"""Exercise the two exterior cave imps using ordinary gameplay only.

Fresh character, the Den's two quests and deliberate inn rests precede the
Valley approach. Walking triggers each real level-three encounter. This tool
never edits game RAM/ROM, substitutes outcomes or loads emulator savestates.
Native memory/OAM/hooks are inspected only. All captures/reports go to the
fresh valley_layout_update folder; published validators and assets stay intact.
"""
import hashlib
import json
import logging
from pathlib import Path
import shutil
import tempfile

import numpy as np
from PIL import Image

import validate_durotar_v022_quests as game
import run_peon_v023_validation as adapter
from validate_peon_villages import warp_tiles

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/valley_layout_update'
IMPS = [
    {'index': 8, 'xy': (25, 6), 'approach': (24, 6),
     'script': 'ValleyCaveApproachImp1Script', 'flag': 'EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD'},
    {'index': 9, 'xy': (27, 9), 'approach': (26, 9),
     'script': 'ValleyCaveApproachImp2Script', 'flag': 'EVENT_PEON_CAVE_APPROACH_IMP_2_DEAD'},
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def published_snapshot():
    result = adapter.published_snapshot()
    for folder in (ROOT / 'references/generated/durotar_v023', ROOT / 'releases/v0.2.3'):
        result.update({str(p.relative_to(ROOT)): digest(p) for p in folder.rglob('*') if p.is_file()})
    return result


class ApproachSession(game.QuestSession):
    def capture(self, name):
        self.p.screen.image.save(OUT / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(OUT / (name + '_4x.png'))
        print(name, self.map(), self.position(), 'HP', self.read('wPartyMon1HP', 2), flush=True)

    def snapshot(self):
        return self.state() | {
            'player_id': self.read('wPlayerID', 2), 'level': self.read('wPartyMon1Level'),
            'experience': self.read('wPartyMon1Exp', 3), 'hp': self.read('wPartyMon1HP', 2),
            'max_hp': self.read('wPartyMon1MaxHP', 2), 'status': self.read('wPartyMon1Status'),
            'pp': self.read('wPartyMon1PP', 4), 'event_flags': self.read('wEventFlags', 256),
            'keys': self.read('wKeyItems', self.read('wNumKeyItems')[0] + 1),
            'items': self.read('wItems', self.read('wNumItems')[0] * 2 + 1),
        }

    def palette(self, number, variable='wOBPals2'):
        data = self.read(variable, 64)[number * 8:number * 8 + 8]
        return [((w := data[i] | data[i + 1] << 8) & 31, (w >> 5) & 31, (w >> 10) & 31)
                for i in range(0, 8, 2)]

    def palette_check(self, label):
        assert self.map() == 15
        self.p.tick(90, True)
        for variable in ('wOBPals1', 'wOBPals2'):
            assert self.palette(6, variable) == [(31, 31, 31), (27, 5, 3), (31, 25, 7), (1, 1, 1)], (label, variable, 'Red imp palette')
            assert self.palette(5, variable)[1] == (17, 17, 17), (label, variable, 'Active quest gray')
            assert self.palette(0, variable) == [(31, 31, 31), (22, 8, 4), (5, 2, 2), (31, 5, 3)], (label, variable, 'Sarkoth native red palette changed')
        return {'red_imp_obj_palette': 6, 'body_rgb555': [27, 5, 3],
                'gray_quest_obj_palette': 5, 'gray_rgb555': [17, 17, 17],
                'sarkoth_obj_palette_zero_preserved': True,
                'both_native_palette_buffers_match': True}

    def native_sprite(self, object_index, binary, indexed_png, palette_number):
        self.p.tick(90, True)
        runtime = self.read(f'wMap{object_index}ObjectStructID')[0]
        assert runtime < 13, ('Actor not visible', object_index, runtime, self.position())
        row = self.read('wObjectStructs', 13 * 40)[runtime * 40:(runtime + 1) * 40]
        assert row[1] == object_index and row[6] & 7 == palette_number
        tile = row[2] & 127; bank = 0 if row[2] & 128 else 1
        assert bytes(self.p.memory[bank, 0x8000 + tile * 16:0x8000 + tile * 16 + 64]) == binary[:64], ('Native standing sprite differs', object_index)
        wanted = np.asarray(self.palette(palette_number), dtype='uint8')[indexed_png]
        opaque = indexed_png != 0
        groups = {}
        # Read hardware OAM too: a shadow table alone is not rendering evidence.
        # A Python tick can end between the renderer's composition and DMA.
        # Wait for a complete publication, without changing the assertion or
        # replacing native OAM. The standing actor is stationary throughout.
        for settled_frames in range(61):
            oam = self.read('wShadowOAM', 160)
            hardware = list(self.p.memory[0xfe00:0xfea0])
            if hardware == oam:
                break
            self.p.tick(1, True)
        assert hardware == oam, ('Hardware OAM is not the current native shadow OAM',
                                [(i, actual, shadow) for i, (actual, shadow) in enumerate(zip(hardware, oam)) if actual != shadow][:40])
        actual = np.asarray(self.p.screen.image.convert('RGB')) >> 3
        for i in range(0, 160, 4):
            y, x, number, attributes = hardware[i:i + 4]
            if not (tile <= number < tile + 4) or attributes & 7 != palette_number or (attributes >> 3) & 1 != bank:
                continue
            assert not attributes & 0x60, 'Expected the unmirrored standing-down pose'
            part = number - tile; tx, ty = part % 2 * 8, part // 2 * 8
            px, py = x - 8, y - 16
            if not (0 <= px <= 152 and 0 <= py <= 136):
                continue
            mask = opaque[ty:ty + 8, tx:tx + 8]
            assert np.array_equal(actual[py:py + 8, px:px + 8][mask], wanted[ty:ty + 8, tx:tx + 8][mask]), ('Actual native sprite pixels differ', object_index, part)
            groups.setdefault((px - tx, py - ty), set()).add(part)
        complete = [list(origin) for origin, parts in groups.items() if parts == {0, 1, 2, 3}]
        assert complete, ('No complete four-tile sprite rendered', object_index, groups)
        # Both imps share native tile graphics. Tie the OAM group to this
        # particular actor, using the same offsets as .InitSprite; evidence
        # from the second imp must never stand in for the requested actor.
        origin = [((row[0x17] + row[0x19] + self.read('wPlayerBGMapOffsetX')[0] + 8) & 255) - 8,
                  ((row[0x18] + row[0x1a] + self.read('wPlayerBGMapOffsetY')[0] + 12) & 255) - 16]
        assert origin in complete, ('Requested actor has no complete native OAM group', object_index, origin, complete)
        return {'object_index': object_index, 'native_vram_standing_pose_matches': True,
                'actual_hardware_oam_matches': True, 'opaque_pixels_match_rgb555': True,
                'palette_number': palette_number, 'complete_oam_origins': complete,
                'requested_actor_native_origin': origin, 'rendering_evidence_bound_to_requested_actor': True,
                'frames_waited_for_complete_native_oam_publication': settled_frames}

    def check_marker(self, label):
        self.navigate((8, 11)); self.p.tick(90, True)
        assert self.event('EVENT_PEON_CACTUS_ACCEPTED') and not self.event('EVENT_PEON_CACTUS_DONE')
        assert self.read('wVariableSprites', 16)[13:16] == [54, 53, 53], 'Existing three quest marker aliases changed'
        # Public marker PNG is RGBA; use its retained native grayscale sprite
        # binary to reconstruct exact palette indexes without changing assets.
        binary = (ROOT / 'gfx/sprites/peon_quest_active_gray.2bpp').read_bytes()
        indexed = np.zeros((16, 16), dtype='uint8')
        for part in range(4):
            tx, ty = part % 2 * 8, part // 2 * 8
            for y in range(8):
                low, high = binary[part * 16 + y * 2:part * 16 + y * 2 + 2]
                for x in range(8):
                    indexed[ty + y, tx + x] = (low >> (7 - x) & 1) | (high >> (7 - x) & 1) << 1
        result = self.native_sprite(5, binary, indexed, 5)
        result.update(self.palette_check(label)); self.capture(label)
        return result

    def observe_imp(self, spec, label):
        assert self.map() == 15 and not self.event(spec['flag'])
        name, width, height = game.MAPS[15]
        live = self.live_actors(name)
        actors = {a['xy'] for a in live}
        triggers = set(game.triggers(name))
        warps = warp_tiles(name)
        options = []
        x, y = spec['xy']
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                point = x + dx, y + dy
                if not 2 <= abs(dx) + abs(dy) <= 3 or not (0 <= point[0] < width * 2 and 0 <= point[1] < height * 2):
                    continue
                if point in actors | triggers | warps or self.collision_at(*point) == 'WALL':
                    continue
                try:
                    path = self.path(point)
                except AssertionError:
                    continue
                options.append((len(path), point))
        assert options, ('No safe observation tile', spec)
        _, point = min(options)
        self.navigate(point)
        indexed = np.asarray(Image.open(ROOT / 'gfx/sprites/peon_imp.png'))[:16, :16]
        binary = (ROOT / 'gfx/sprites/peon_imp.2bpp').read_bytes()
        result = self.native_sprite(spec['index'], binary, indexed, 6)
        result.update(self.palette_check(label)); self.capture(label)
        return result | {'ordinary_observation_tile': list(point)}

    def fight(self, label, flag, copper=None, baseline=None):
        before = self.snapshot(); heals = self.heal_calls
        loads = self.encounter_loads if baseline is None else baseline
        handled = self.move_menus; entered = bool(self.read('wBattleMode')[0]); seen = set(); enemies = []
        for _ in range(180):
            entered |= bool(self.read('wBattleMode')[0])
            if self.move_menus > handled:
                handled = self.move_menus; self.p.tick(60, True)
                if self.encounter_loads not in seen:
                    seen.add(self.encounter_loads)
                    enemies.append({'species': self.read('wEnemyMonSpecies')[0], 'level': self.read('wEnemyMonLevel')[0]})
                    self.capture(label + '_battle')
                wanted = next((i for i, (move, pp) in enumerate(zip(self.read('wBattleMonMoves', 4), self.read('wBattleMonPP', 4))) if move == 84 and pp & 63), 0)
                for _ in range(5):
                    current = self.read('wCurMoveNum')[0]
                    if current == wanted:
                        break
                    self.press('up' if current > wanted else 'down', 30)
                self.press('a', 180)
            else:
                self.press('a', 120)
            if entered and self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]:
                break
        assert entered and self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]
        assert self.read('wBattleResult') == [0] and self.event(flag), (label, 'Ordinary encounter was not won')
        assert self.heal_calls == heals, (label, 'Encounter automatically healed')
        if copper is not None:
            assert self.money() == int.from_bytes(bytes(before['wMoney']), 'big') + copper
        self.capture(label + '_victory')
        return {'outcome': 'victory', 'observed_native_enemies': enemies,
                'native_encounter_loads': self.encounter_loads - loads, 'no_auto_heal': True,
                'death_flag_set': True, 'copper_reward': copper, 'before': before, 'after': self.snapshot()}

    def revisit_without_combat(self, label):
        loads = self.encounter_loads; money = self.money(); xp = self.experience()
        for spec in IMPS:
            assert self.event(spec['flag'])
            self.navigate(spec['approach']); self.p.tick(120, True)
            assert self.read('wBattleMode') == [0] and self.read('wScriptMode') == [0]
        assert self.encounter_loads == loads and self.money() == money and self.experience() == xp
        self.capture(label)
        return {'no_native_encounter_reloaded': True, 'no_repeat_copper_or_xp': True,
                'both_death_flags_still_set': True}

    def battery_restart(self):
        before = self.snapshot(); observed = {'saved': False, 'exited': False}
        self.p.hook_register(*self.sym['_SaveGameData'], lambda _: observed.__setitem__('saved', True), None)
        self.p.hook_register(*self.sym['StartMenu.Exit'], lambda _: observed.__setitem__('exited', True), None)
        self.press('start')
        for _ in range(10):
            if self.read('wMenuCursorPosition') == [1]:
                break
            self.press('up', 30)
        assert self.read('wMenuCursorPosition') == [1]
        for _ in range(3):
            self.press('down', 30)
        self.press('a')
        for _ in range(12):
            if observed['saved'] and observed['exited']:
                break
            self.press('a', 180)
        assert observed['saved'] and observed['exited']
        self.p.tick(90, True); self.capture('valley_native_save_complete'); self.p.stop(save=True)
        battery = Path(str(self.rom) + '.ram')
        assert battery.stat().st_size == 32768
        battery_sha = digest(battery)
        self.open(); self.p.tick(240, True); self.press('start')
        for _ in range(12):
            if self.map() == 15 and self.read('wScriptMode') == [0]:
                break
            self.press('a', 180)
        self.p.tick(90, True)
        assert self.snapshot() == before, 'Native battery restart changed progress, location, kit or wounds'
        self.capture('valley_after_cold_battery_restart')
        return {'native_battery_bytes': 32768, 'native_battery_sha256': battery_sha,
                'native_save_commit_observed': True, 'cold_restart_state_matches': True,
                'all_256_event_bytes_and_both_imp_death_flags_preserved': True,
                'player_location_health_status_pp_kit_copper_xp_preserved': True}


def main():
    logging.disable(logging.CRITICAL); OUT.mkdir(parents=True, exist_ok=True)
    preserved = published_snapshot()
    # Only Python objects in this process change. Capture destinations are fresh.
    for module in adapter.local_dependencies(game):
        for name in ('OUT', 'OUTPUT'):
            if hasattr(module, name):
                setattr(module, name, OUT)
        adapter.adapt_v023_gameplay(module)
    syms = game.load_symbols(); rom_sha = digest(ROOT / 'pokecrystal.gbc')
    actors = game.all_actors('ValleyOfTrials')
    assert [a['xy'] for a in actors[:7]] == [(8, 10), (10, 19), (6, 11), (16, 20), (8, 9), (10, 18), (6, 10)]
    assert len(actors) == 9
    for spec in IMPS:
        actor = actors[spec['index'] - 1]
        assert actor['xy'] == spec['xy'] and actor['script'] == spec['script'] and actor['event'] == spec['flag']
        assert game.triggers('ValleyOfTrials')[spec['approach']] == spec['script']
    report = {'rom_sha256': rom_sha, 'normal_buttons_only': True, 'ram_edits': False,
              'emulator_states_loaded': False, 'read_only_native_hooks': True,
              'original_seven_valley_object_indices_preserved': True, 'new_objects_appended_at_8_and_9': True,
              'exterior_encounters': [], 'palette_checkpoints': {}, 'all_checks_passed': False,
              'scope': 'Two exterior level-three imps, native cave doorway, map/quest markers and native battery persistence; Chromatic hardware not exercised.'}
    s = None
    try:
        with tempfile.TemporaryDirectory(prefix='peon-cave-approach-') as directory:
            rom = Path(directory) / 'test.gbc'; shutil.copyfile(ROOT / 'pokecrystal.gbc', rom)
            s = ApproachSession(rom, syms); s.fresh()
            s.talk((10, 10), 'up', 'gornek_cutting_teeth')
            loads = s.encounter_loads
            s.navigate((18, 13)); s.press('up', 30); s.press('a')
            report['boar'] = s.fight('ordinary_boar', 'EVENT_PEON_QUEST_DONE', baseline=loads)
            s.talk((10, 10), 'up', 'gornek_sting_quest'); s.rest()
            loads = s.encounter_loads; s.navigate((17, 15))
            report['den_scorpid'] = s.fight('ordinary_den_scorpid', 'EVENT_PEON_SCORPID_DEFEATED', baseline=loads)
            s.talk((10, 10), 'up', 'gornek_second_reward'); s.rest()
            assert s.event('EVENT_PEON_MAP_RECEIVED')
            s.to_valley(); s.talk((8, 11), 'up', 'galgar_accept_normally')
            report['palette_checkpoints']['existing_active_quest_marker'] = s.check_marker('existing_active_quest_marker')
            for number, spec in enumerate(IMPS, 1):
                label = 'exterior_imp_' + str(number)
                observer = s.observe_imp(spec, label + '_native_overworld')
                loads = s.encounter_loads
                # No A press: ordinary walking must start this hostile script.
                s.navigate(spec['approach'])
                for _ in range(20):
                    if s.read('wBattleMode')[0] or s.encounter_loads > loads:
                        break
                    s.p.tick(15, True)
                assert s.read('wBattleMode')[0] or s.encounter_loads > loads, (label, 'Walking did not auto-aggro')
                result = s.fight(label, spec['flag'], 30, baseline=loads)
                assert result['native_encounter_loads'] == 1 and result['observed_native_enemies'] == [{'species': 74, 'level': 3}]
                result.update(object_index=spec['index'], ordinary_walk_autoaggro=True, native_overworld=observer)
                report['exterior_encounters'].append(result)
                report['palette_checkpoints'][label + '_after_battle'] = s.palette_check(label)
                if number == 1:
                    # A deliberate, visible inn visit prepares the next test;
                    # the encounter itself must never refill HP or charges.
                    s.rest(); s.to_valley()
                    baseline = s.encounter_loads; s.navigate(spec['approach'])
                    assert s.encounter_loads == baseline and s.read('wBattleMode') == [0]
            s.navigate((24, 4), expected_map=20)
            assert s.position() == (10, 16)
            s.capture('inside_burning_blade_cavern')
            report['native_cave_entry'] = {'outside_xy': [24, 4], 'interior_map': 20, 'arrival_xy': [10, 16]}
            s.navigate((10, 15)); s.navigate((10, 16), expected_map=15)
            assert s.position() == (24, 4)
            s.capture('native_cave_return')
            report['palette_checkpoints']['after_cave_return'] = s.palette_check('after_cave_return')
            report['cave_return_does_not_respawn_imps'] = s.revisit_without_combat('no_repeat_after_cave_return')
            report['palette_checkpoints']['marker_after_cave_return'] = s.check_marker('marker_after_cave_return')
            s.press('select', 180); s.capture('ordinary_discovered_zone_map'); s.press('b', 180)
            assert s.map() == 15 and s.read('wScriptMode') == [0]
            report['palette_checkpoints']['after_zone_map_close'] = s.check_marker('marker_after_zone_map_close')
            report['battery_restart'] = s.battery_restart()
            report['palette_checkpoints']['after_cold_restart'] = s.check_marker('marker_after_cold_restart')
            report['cold_restart_does_not_respawn_imps'] = s.revisit_without_combat('no_repeat_after_cold_restart')
            assert published_snapshot() == preserved, 'Published assets/reports/releases changed'
            assert digest(ROOT / 'pokecrystal.gbc') == rom_sha, 'Root ROM changed during this test'
            report['published_assets_and_releases_preserved'] = True
            report['all_checks_passed'] = True; s.p.stop(save=False); s = None
            for filename in ('unexpected_state.png', 'unexpected_state_4x.png'):
                (OUT / filename).unlink(missing_ok=True)
    except Exception as error:
        report['failure'] = repr(error)
        if s is not None:
            s.capture('unexpected_state'); s.p.stop(save=False)
        (OUT / 'cave_approach_validation.json').write_text(json.dumps(report, indent=2) + '\n')
        raise
    (OUT / 'cave_approach_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
