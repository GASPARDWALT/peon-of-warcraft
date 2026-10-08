#!/usr/bin/env python3
"""Package only a checked v0.2.3 ROM and matching independent validation reports."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'references/generated/durotar_v023'
OUT = ROOT / 'releases/v0.2.3'
NAME = 'peon_of_warcraft_v0_2_3'
REPORTS = (
    'in_game/validation_results.json', 'sprite_validation/validation_results.json',
    'save_upgrade_results.json', 'village_validation/validation_results.json',
    'speaker_portraits/emulator_validation.json', 'combat_assets/in_game/validation.json',
    'title_music/validation.json', 'sound_effects/validation.json',
    'lazy_quest_validation/validation.json', 'quest_markers/validation.json',
    'quest_markers/validation_results.json', 'menu_skin/validation.json',
    'enemies/compiled_validation.json', 'enemy_profiles/validation.json',
    'inn_validation/validation_results.json', 'trainer_validation/validation.json',
    'spell_validation/validation.json', 'quest_xp_validation/validation.json',
    'quest_validation/validation_results.json', 'quest_fault_validation/validation_results.json',
    'ambient_music/validation.json',
    'battle_totems_validation/validation.json', 'item_icon_validation/validation.json',
    'spell_animations/validation.json',
    'build_validation.json', 'player_combat/validation.json', 'combat_balance/validation.json',
    'combat_balance/normal_pack_validation.json',
)
DOCS = ('docs/V0_2_3_PLAYABLE.md', 'docs/V023_COMBAT_BALANCE.md', 'docs/V0_2_3_COMBAT_AND_BALANCE.md', 'docs/DUROTAR_V022_QUESTS.md', 'docs/PEON_V022_ATTACK_SLOTS.md',
        'docs/V0_2_2_INNS_HEARTHSTONE.md', 'docs/SHAMAN_TRAINER.md',
        'docs/QUEST_XP.md', 'docs/BATTLE_BAGS_AND_TOTEM.md')
SKIP = re.compile(r'(unexpected|failure|debug|trace|source_crop|\.pyc$)', re.I)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def true_keys(data, keys):
    for key in keys:
        require(data.get(key) is True, f'{key} did not pass')


def validate_player_combat(data):
    normal = data.get('normal_route', {})
    require(normal.get('ram_edits') is False and normal.get('emulator_states_loaded') is False,
            'Player movement lacks an ordinary-button route')
    restored = ('idle_36_tiles_restored', 'idle_actual_rgb555_and_palette',
                'back_tilemap_bank0_intact')
    for role, item in (('totem', 0x94), ('potion', 0x12)):
        action = normal.get(role, {})
        require(action.get('item_id') == item, f'{role}: wrong native item')
        true_keys(action, ('actual_button_use', 'other_battle_graphics_preserved') + restored)

    def pose_case(case, move, sequence, scenes=True, restore=True):
        require(case.get('move_id') == move and case.get('scenes_on') is scenes,
                'Player movement move/scenes mismatch')
        true_keys(case, ('actual_button_cast', 'native_animation_id_not_substituted'))
        require(case.get('native_sequence') == sequence and
                set(case.get('native_poses', [])) == set(sequence) and
                set(case.get('actual_rgb555_matched_poses', [])) == set(sequence),
                'Player pose sequence or actual pixel evidence incomplete')
        require(all(case.get('matched_native_frames', {}).get(pose, 0) > 0 for pose in sequence),
                'Player poses lack visible native frames')
        if restore:
            true_keys(case, restored)
        return case

    mace = pose_case(normal.get('mace', {}), 1, ['brace', 'swing', 'idle'])
    require(mace.get('protected_helper_returns', 0) >= 2, 'Battle helper return checks incomplete')
    bolt = pose_case(normal.get('lightning_bolt', {}), 84, ['brace', 'idle'], restore=False)
    true_keys(bolt, ('normal_battle_returned_to_world',))
    expected = {'diagnostic_mace': 1, 'diagnostic_lightning': 84,
                'diagnostic_flame_shock': 52, 'diagnostic_healing': 105,
                'diagnostic_rockbiter': 14, 'diagnostic_lightning_shield': 115,
                'diagnostic_scenes_off': 1}
    require(set(data.get('diagnostics', {})) == set(expected) and data.get('diagnostic_inputs'),
            'Declared player movement fixtures incomplete')
    for name, move in expected.items():
        off = name == 'diagnostic_scenes_off'
        sequence = ['idle'] if off else (['brace', 'swing', 'idle'] if move == 1 else ['brace', 'idle'])
        pose_case(data['diagnostics'][name], move, sequence, scenes=not off)


def validate_balance(data):
    require(data.get('stage') == 'final' and data.get('diagnostic_ram_changes') and
            data.get('enemy_level_policy') == 'match_current_native_player_level_each_fight',
            'Final balance fixtures/methods are not declared')
    require(data.get('levels') == [2, 4, 6] and len(set(data.get('seeds', []))) == 3,
            'Balance requires three levels and three RNG seeds')
    chains = data.get('chains', [])
    require(len(chains) == 99, 'The complete 99-series balance matrix is required')
    identities = {(c['enemy'], c['starting_level'], c['enemy_level'], c['attack'], c['seed'])
                  for c in chains}
    require(len(identities) == len(chains), 'Duplicate balance fixtures')
    expected = {(enemy, level, level, attack, seed)
                for enemy in ('boar', 'scorpid', 'imp') for level in data['levels']
                for attack in ('mace', 'bolt') for seed in data['seeds']}
    expected |= {(enemy, level, level + 2, 'bolt', seed)
                 for enemy in ('boar', 'scorpid', 'imp') for level in data['levels']
                 for seed in data['seeds']}
    expected |= {(enemy, level, level, 'flame_then_bolt', seed)
                 for enemy in ('boar', 'scorpid', 'imp') for level in (4, 6)
                 for seed in data['seeds']}
    require(identities == expected, 'Balance matrix is missing an enemy, level, seed or strategy')
    equal, higher, potion_cases = [], [], []
    for chain in chains:
        require(chain['enemy'] in {'boar', 'scorpid', 'imp'} and
                chain['starting_level'] in data['levels'] and chain['seed'] in data['seeds'],
                'Balance fixture outside the declared native matrix')
        battles = chain.get('battles', [])
        require(1 <= len(battles) <= 3, 'Balance fixture has no native battles')
        is_equal = chain['enemy_level'] == chain['starting_level']
        require(is_equal or chain['enemy_level'] == chain['starting_level'] + 2,
                'Unexpected enemy level comparison')
        (equal if is_equal else higher).append(chain)
        for i, battle in enumerate(battles):
            require(battle.get('outcome') in {'win', 'defeat'} and
                    battle.get('heal_party_calls') == 0 and battle.get('native_damage_events'),
                    'Balance lacks native damage evidence or healed automatically')
            if is_equal:
                require(battle['enemy']['level'] == battle['before']['level'],
                        'Equal foe did not follow the current native player level')
            else:
                require(battle['enemy']['level'] == battle['before']['level'] + 2,
                        'Higher foe was not two levels above the player')
            if i:
                require(battles[i-1]['outcome'] == 'win' and
                        battles[i-1]['after'] == battle['before'],
                        'Native HP/status/PP/XP/stats were not carried unchanged')
        if 'third_with_one_potion' in chain:
            require(is_equal and chain['attack'] == 'bolt' and len(battles) == 3,
                    'Potion comparison lacks its ordinary third encounter')
            treatment = chain['third_with_one_potion']
            potion, assisted = treatment['potion'], treatment['battle']
            true_keys(potion, ('ordinary_menu_buttons', 'stack_consumed'))
            require(potion.get('native_item_helper_calls') == 1 and potion.get('heal_party_calls') == 0,
                    'Potion was not used once through its native helper')
            before, after = potion['before'], potion['after']
            require(before == battles[1]['after'] and
                    after['hp'] == min(before['hp'] + 20, before['max_hp']) and
                    all(after.get(k) == v for k, v in before.items() if k != 'hp') and
                    assisted['before'] == after and assisted.get('heal_party_calls') == 0 and
                    assisted.get('native_damage_events') and
                    assisted['enemy']['level'] == assisted['before']['level'],
                    'Potion comparison changed native party fields or bypassed combat')
            potion_cases.append(chain)
    bolt = [c for c in equal if c['attack'] == 'bolt']
    mace = [c for c in equal if c['attack'] == 'mace']
    flame = [c for c in equal if c['attack'] == 'flame_then_bolt']
    require((len(bolt), len(mace), len(flame), len(higher), len(potion_cases)) == (27, 27, 18, 27, 27),
            'Balance attack/level/potion coverage incomplete')
    survived_two = sum(len(c['battles']) >= 2 and c['battles'][1]['outcome'] == 'win' for c in bolt)
    risky_third = sum(len(c['battles']) < 3 or c['battles'][2]['outcome'] == 'defeat' or
                     c['battles'][2]['after']['hp'] * 4 <= c['battles'][2]['after']['max_hp'] for c in bolt)
    improved = sum(c['third_with_one_potion']['battle']['outcome'] == 'win' and
                   (c['battles'][2]['outcome'] == 'defeat' or
                    c['third_with_one_potion']['battle']['after']['hp'] > c['battles'][2]['after']['hp'])
                   for c in potion_cases)
    hard = sum(c['battles'][0]['outcome'] == 'defeat' or
               c['battles'][0]['after']['hp'] * 2 <= c['battles'][0]['after']['max_hp'] for c in higher)
    require(survived_two * 4 >= len(bolt) * 3 and risky_third * 2 >= len(bolt) and
            improved * 2 > len(potion_cases) and hard * 2 > len(higher),
            'Measured native results do not meet the modest attrition thresholds')
    require(data['summary']['bolt']['survive_two'] == survived_two and
            data['summary']['bolt']['third_defeat_or_at_most_quarter_hp'] == risky_third and
            data['potion_summary']['meaningfully_improved'] == improved and
            data['higher_level_summary']['defeat_or_at_most_half_hp'] == hard,
            'Balance summaries disagree with the measured battles')
    true_keys(data.get('checks', {}), (
        'two_equal_bolt_fights_survived_at_least_75_percent',
        'third_equal_bolt_fight_defeat_or_at_most_quarter_hp_at_least_50_percent',
        'one_real_potion_improves_a_majority_of_eligible_third_fights',
        'plus_two_level_foes_cause_defeat_or_at_most_half_hp_in_majority',
        'no_free_heal_party_in_any_encounter', 'equal_enemy_matches_current_native_level_each_fight',
        'native_health_status_charges_and_xp_carry'))


def validate_normal_pack(data):
    true_keys(data, ('normal_buttons_only', 'two_equal_level_encounters_without_auto_heal',
                     'without_potion_won'))
    require(data.get('ram_edits') is False and data.get('emulator_states_loaded') is False,
            'Road pack proof used diagnostic injection')
    pack = data.get('pack', {})
    starts = pack.get('battle_starts', [])
    require(pack.get('outcome') == 0 and pack.get('victory_flag') is True and
            pack.get('native_enemy_loads') == 2 and pack.get('heal_party_calls') == 0 and
            len(starts) == 2 and all(s['player_level'] == s['enemy_level'] == 4 for s in starts),
            'Ordinary road pack lacks two victorious equal-level native encounters')
    before, after = pack['before'], pack['after']
    require(data.get('before_road') == before and before['level'] == 4 and
            starts[0]['hp'] == before['hp'] and starts[1]['hp'] <= starts[0]['hp'] and
            after['copper'] - before['copper'] == 40,
            'Road pack healed between members or lost its one-time reward evidence')
    gain = after['max_hp'] - before['max_hp']
    remaining = after['hp'] - gain
    require(data.get('max_hp_added_by_level_up') == gain and
            data.get('hp_after_removing_level_up_gain') == remaining and
            abs(data.get('fraction_of_starting_max_hp_remaining', -1) - remaining / before['max_hp']) < 1e-12,
            'Road pack HP measurement did not account for native level-up health')


def validate_report(name, data):
    require(not data.get('failure') and not data.get('error'), 'report records a failure')
    if 'all_checks_passed' in data:
        require(data['all_checks_passed'] is True, 'all_checks_passed is not true')
    elif name == 'in_game/validation_results.json':
        true_keys(data, ('new_game_reaches_den', 'master_asks_name',
                        'neutral_boar_does_not_aggro', 'scorpid_proximity_aggro_passed',
                        'second_quest_map_reward_passed', 'save_cold_restart_passed'))
    elif name == 'sprite_validation/validation_results.json':
        true_keys(data, ('vram_graphics_match', 'save_cold_restart_passed'))
        require(len(data['renderer_facings_verified']) == 16, '16 facings were not verified')
    elif name == 'title_music/validation.json':
        true_keys(data, ('native_four_channel_apu_capture',
                        'three_synchronized_phrase_entries_per_channel',
                        'start_reaches_character_select'))
    elif name == 'combat_assets/in_game/validation.json':
        true_keys(data, ('poison_damage_1_8_max_hp', 'native_encounter_no_trainer_or_creature_naming'))
        require(all(data['native_attack_pixel_matches'].values()), 'attack palette pixels differ')
        require(set(data['native_pose_pixel_matches']) == {'boar', 'scorpid', 'imp'},
                'base encounter roles incomplete')
        for role, poses in data['native_pose_pixel_matches'].items():
            require(set(poses) == {'idle', 'prepare', 'attack', 'return'} and all(poses.values()),
                    f'{role}: native pose pixels differ')
            attack = data['enemy_attacks'][role]
            require(attack['hook_calls'] > 0 and {0, 1, 2, 3}.issubset(attack['frames']),
                    f'{role}: real attack animation did not execute')
    elif name == 'enemies/compiled_validation.json':
        roles = {'tiger', 'raptor', 'crawler', 'harpy', 'felstalker', 'cultist', 'yarrog', 'sarkoth'}
        require(set(data['characters']) == roles and set(data['emulator_attacks']) == roles,
                'eight enemy roles incomplete')
        for role in roles:
            true_keys(data['characters'][role], ('native_size_verified', 'back_pixel_exact_rgb555',
                                                 'compiled_pics_found_in_rom'))
            attack = data['emulator_attacks'][role]
            require(attack['attack_hook_calls'] > 0 and
                    set(attack['pixel_exact_rgb555_pose_matches']) == {0, 1, 2, 3},
                    f'{role}: four real attack poses did not match')
    elif name == 'quest_markers/validation_results.json':
        true_keys(data, ('ordinary_new_game_reached_den',))
        require(len(data['cases']) >= 13, 'atlas state cases incomplete')
        for case in data['cases']:
            true_keys(case, ('rgb555_matches', 'background_vram_unchanged',
                             'registers_vbk_oam_guard_preserved', 'closed_to_world'))
    elif name == 'inn_validation/validation_results.json':
        true_keys(data, ('ordinary_new_game_reaches_den', 'unbound_hearth_does_not_travel',
                        'combat_wounds_persist_without_free_heal',
                        'declined_rest_does_not_heal_or_bind', 'rest_restores_spent_charges',
                        'cancelled_hearth_preserves_location',
                        'declined_new_binding_preserves_previous_home',
                        'inside_inn_battery_restart', 'saved_backup_exit_owner_preserved'))
        require(len(data['doors']) == 9 and all(d['round_trip'] for d in data['doors']),
                'nine door round trips incomplete')
        require(len(data['bindings']) == 3 and len(data['hearth_returns']) == 3,
                'three inn home bindings incomplete')
        for binding in data['bindings']:
            true_keys(binding, ('exclusive', 'restored_hp', 'status_zero_after_rest'))
    elif name == 'spell_validation/validation.json':
        cases = data['cases']
        required = ('rockbiter_cast', 'rockbiter_one_physical_hit', 'rockbiter_nature_keeps_charge',
                    'rockbiter_miss_keeps_charge', 'lightning_shield_cast',
                    'lightning_shield_three_retaliations', 'lightning_shield_special_ignored',
                    'lightning_shield_lethal_retaliation', 'purge_enemy_positive_only',
                    'flame_shock_guaranteed_burn', 'flame_burst_guaranteed_burn',
                    'flame_shock_fire_immunity', 'frost_shock_guaranteed_slow',
                    'healing_wave_level6', 'windfury_2_hits', 'windfury_3_hits',
                    'windfury_4_hits', 'windfury_5_hits', 'chain_lightning_single_target',
                    'overworld_poison_bound_inn')
        require(set(required).issubset(cases), 'spell effect cases incomplete')
        require(cases['rockbiter_cast']['after']['rock_charge'] == 1, 'Rockbiter was not primed')
        hits = cases['rockbiter_one_physical_hit']['hits']
        require(len(hits) == 2 and hits[0]['after']['damage'] == 2 * hits[0]['before']['damage']
                and hits[1]['after']['damage'] == hits[1]['before']['damage'],
                'Rockbiter one-hit effect failed')
        require(cases['lightning_shield_cast']['after']['shield_charges'] == 3,
                'Lightning Shield did not receive three charges')
        true_keys(cases['lightning_shield_lethal_retaliation'], ('battle_returned_to_world',))
        purge = cases['purge_enemy_positive_only']
        require(purge['after']['player_stages'] == purge['before']['player_stages'] and
                purge['after']['enemy_stages'] == [min(7, n) for n in purge['before']['enemy_stages']],
                'Purge affected player/debuff stages')
        for effect in ('flame_shock_guaranteed_burn', 'flame_burst_guaranteed_burn'):
            require(cases[effect]['burn']['after']['enemy_status'] & 16 and
                    cases[effect]['secondary_rng_calls'] == 0, 'Guaranteed burn case failed')
        slow = cases['frost_shock_guaranteed_slow']
        require(slow['slow']['after']['enemy_stages'][2] == 6 and
                slow['secondary_rng_calls'] == 0, 'Guaranteed Frost Shock slow failed')
        for count in (2, 3, 4, 5):
            require(len(cases[f'windfury_{count}_hits']['hits']) == count,
                    'Windfury actual hit count incomplete')
        poison = cases['overworld_poison_bound_inn']
        true_keys(poison, ('status_cleared', 'money_unchanged', 'pp_unchanged', 'ordinary_walking'))
        require(poison['hp'] == 1 and poison['heal_party_calls'] == 0,
                'Overworld poison silently healed on recovery')
    else:
        raise ValueError('Unknown runtime report schema; add explicit success checks')
    if name in {'save_upgrade_results.json', 'save_upgrade/validation.json'}:
        states = data.get('states', {})
        require(set(states) == {'v0.1.1', 'v0.2', 'v0.2.1', 'v0.2.2'},
                'Four genuine prior-version battery upgrades are required')
        preserved_fields = ('wPlayerName', 'wPlayerID', 'wMapGroup', 'wPartyMon1Level',
                            'wPartyMon1HP', 'wPartyMon1Moves', 'wPartyMon1PP',
                            'wPartyMon1Item', 'wMoney', 'wKeyItems')
        for version, state in states.items():
            true_keys(state, ('ordinary_buttons_only',))
            require(state.get('native_battery_size') == 32768,
                    f'{version}: source battery is not native 32 KiB SRAM')
            for field in ('source_rom_sha256', 'real_source_battery_sha256'):
                require(re.fullmatch(r'[0-9a-f]{64}', state.get(field, '')) is not None,
                        f'{version}: source ROM/battery evidence missing')
            handoff = state.get('legacy_kento_totem_handoff', {})
            true_keys(handoff, ('ordinary_buttons_only', 'continue_reloads_current_map_objects',
                                'repeat_no_duplicate', 'other_kit_cash_xp_health_charges_unchanged',
                                'battery_restart_preserves_totem'))
            preowned = version == 'v0.2.2'
            require(handoff.get('totem_preowned_on_source') is preowned and
                    handoff.get('handoff_required') is (not preowned) and
                    handoff.get('quantity_before_handoff') == int(preowned) and
                    handoff.get('quantity_after_handoff') == 1,
                    f'{version}: legacy/preowned Earth Totem flow changed its quantity')
            if not preowned:
                require(handoff.get('received_item_id') == 0x94,
                        f'{version}: Kento did not hand off the reusable Earth Totem')
            for field in ('source_saved_kento_script_pointer',
                          'current_kento_script_pointer_after_continue'):
                pointer = handoff.get(field, [])
                require(isinstance(pointer, list) and len(pointer) == 2 and
                        all(isinstance(n, int) and 0 <= n <= 255 for n in pointer),
                        f'{version}: saved/current NPC pointer evidence missing')
            require(re.fullmatch(r'[0-9a-f]{64}',
                                 handoff.get('native_second_battery_sha256', '')) is not None,
                    f'{version}: second native battery restart evidence missing')
            before = state.get('state_preserved', {})
            after = handoff.get('state_after_handoff_restart', {})
            require(all(field in before and before[field] == after.get(field)
                        for field in preserved_fields),
                    f'{version}: Kento/restart changed character kit, cash, wounds or charges')
        full_bag = states['v0.2.1'].get('separate_full_bag_diagnostic') or {}
        true_keys(full_bag, ('diagnostic_ram_edits', 'failed_without_item_or_kit_changes',
                            'original_inventory_restored_before_retry',
                            'ordinary_kento_retry_awards_one',
                            'repeat_after_retry_does_not_duplicate', 'no_user_save_changed'))
        require(full_bag.get('edited_fields') == ['wNumItems', 'wItems'],
                'Legacy full-bag diagnostic must label its inventory-only edits')
    if name == 'village_validation/validation_results.json':
        require(data['npc_count'] == 18 and data['building_count'] == 9, 'village coverage incomplete')
        true_keys(data['inside_troll_hut_save_cold_restart'], ('passed',))
        require(data['ram_edits'] is False, 'village traversal used RAM edits')
    if name == 'quest_validation/validation_results.json':
        require(data['normal_buttons_only'] is True and data['ram_edits'] is False and
                data['emulator_states_loaded'] is False, 'primary quests used diagnostic injection')
        rewards = data.get('quest_xp_rewards', {})
        for quest, amount in (('cactus', 25), ('sarkoth', 50), ('medallion', 100)):
            require(rewards.get(quest, {}).get('normal_turn_in_xp') == amount and
                    rewards[quest].get('repeat_xp_and_copper_unchanged') is True,
                    f'{quest}: normal quest XP/repeat coverage incomplete')
    if name == 'quest_fault_validation/validation_results.json':
        require(data['diagnostic_only'] is True and data['ram_edits'] is True,
                'full-pocket/loss fixtures are not explicitly diagnostic')
    if name == 'player_combat/validation.json':
        validate_player_combat(data)
    if name == 'combat_balance/validation.json':
        validate_balance(data)
    if name == 'combat_balance/normal_pack_validation.json':
        validate_normal_pack(data)
    if 'sound_effects_validation_rom_sha256' in data:
        require(data['sound_effects_validation_rom_sha256'] == data['rom_sha256'],
                'audio-quality report references stale effect captures')


def check():
    source = ROOT / 'pokecrystal.gbc'
    rom, sha = source.read_bytes(), digest(source)
    require(len(rom) == 2097152, 'ROM must be exactly 2 MiB')
    require((rom[0x143], rom[0x147], rom[0x149]) == (0xc0, 0x10, 3),
            'Unexpected CGB/MBC3/32 KiB SRAM header')
    checksum = 0
    for value in rom[0x134:0x14d]:
        checksum = (checksum - value - 1) & 255
    require(checksum == rom[0x14d], 'Header checksum invalid')
    require((sum(rom) - rom[0x14e] - rom[0x14f]) & 65535 ==
            int.from_bytes(rom[0x14e:0x150], 'big'), 'Global checksum invalid')
    names = set(REPORTS)
    for path in ASSETS.rglob('*.json'):
        data = json.loads(path.read_text())
        if isinstance(data, dict) and 'rom_sha256' in data:
            names.add(path.relative_to(ASSETS).as_posix())
    verified, errors = [], []
    for name in sorted(names):
        path = ASSETS / name
        try:
            data = json.loads(path.read_text())
            require(data.get('rom_sha256') == sha,
                    f"stale SHA {data.get('rom_sha256', 'missing')} (current {sha})")
            validate_report(name, data)
            verified.append(dict(path=name, sha256=digest(path), rom_sha256=sha))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f'{name}: {exc}')
    require(not errors, 'Release prerequisites failed:\n' + '\n'.join(errors))
    require((ASSETS / 'index.html').is_file() and (ASSETS / 'gallery_manifest.json').is_file(),
            'Generate the offline gallery first')
    gallery = json.loads((ASSETS / 'gallery_manifest.json').read_text())
    require(gallery['rom_sha256_at_generation'] == sha, 'Regenerate gallery against current ROM')
    browser = json.loads((ASSETS / 'gallery_browser_validation.json').read_text())
    require(browser.get('gallery_rom_sha256') == sha and browser.get('all_gallery_checks_passed') is True
            and browser.get('relative_image_links_verified') == len(gallery['images']),
            'Run the offline gallery browser/path validation against the current gallery')
    return rom, sha, verified


def add(z, path, name):
    info = zipfile.ZipInfo(str(name), (1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    z.writestr(info, path.read_bytes())


def asset_files(sha):
    for directory in ('durotar_v023', 'durotar_v022', 'durotar_v021', 'durotar_v02', 'title_portal_gbc'):
        folder = ROOT / 'references/generated' / directory
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or SKIP.search(path.name) or '__pycache__' in path.parts:
                continue
            if directory != 'durotar_v023' and path.name == 'index.html':
                continue  # Retained gallery reports describe a historical ROM, not this release.
            if path.suffix == '.json':
                data = json.loads(path.read_text())
                if isinstance(data, dict) and 'rom_sha256' in data:
                    if directory != 'durotar_v023' or data['rom_sha256'] != sha:
                        continue
            yield path, path.relative_to(folder.parent)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='verify prerequisites without creating archives')
    args = parser.parse_args()
    rom, sha, reports = check()
    if args.check:
        print(json.dumps(dict(rom_sha256=sha, verified_reports=len(reports), all_checks_passed=True)))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (NAME + '.gbc')).write_bytes(rom)
    manifest = dict(version='0.2.3', rom_sha256=sha, rom_bytes=len(rom), reports=reports,
                    cgb_flag='0xc0', mapper='0x10 MBC3+RTC+RAM+battery', sram_bytes=32768,
                    physical_chromatic_tested=False,
                    normal_and_diagnostic_methods='See each report; diagnostic injections are explicitly labeled.')
    (OUT / 'validation_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    with zipfile.ZipFile(OUT / (NAME + '.zip'), 'w') as z:
        for filename in (NAME + '.gbc', 'README.md', 'validation_manifest.json'):
            add(z, OUT / filename, filename)
        for document in DOCS:
            add(z, ROOT / document, document)
        for report in reports:
            add(z, ASSETS / report['path'], 'validation/' + report['path'])
    with zipfile.ZipFile(OUT / (NAME + '_assets.zip'), 'w') as z:
        for path, name in asset_files(sha):
            add(z, path, name)
        add(z, OUT / 'README.md', 'README.md')
        add(z, OUT / 'validation_manifest.json', 'validation_manifest.json')
    # Small transparent-only pack, retaining paths and all APNG animation frames.
    from PIL import Image
    transparent = 0
    with zipfile.ZipFile(OUT / (NAME + '_transparent_png.zip'), 'w') as z:
        for path, name in asset_files(sha):
            if path.suffix.lower() != '.png' or any(s in path.stem for s in ('engine', 'alpha_mask')):
                continue
            with Image.open(path) as im:
                alpha = im.convert('RGBA').getchannel('A')
                if alpha.getextrema()[0] == 255:
                    continue
            add(z, path, name)
            transparent += 1
        add(z, OUT / 'README.md', 'README.md')
    suffixes = ('.gbc', '.zip', '_assets.zip', '_transparent_png.zip')
    (OUT / 'SHA256SUMS.txt').write_text(''.join(digest(OUT / (NAME + suffix)) + '  ' +
                                             NAME + suffix + '\n' for suffix in suffixes))
    print(json.dumps(dict(release=str(OUT), rom_sha256=sha, verified_reports=len(reports),
                          transparent_png_files=transparent, all_checks_passed=True)))


if __name__ == '__main__':
    main()
