#!/usr/bin/env python3
"""Package v0.2.1 only when independent emulator reports match the ROM."""
import hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPORTS=['in_game/validation_results.json','sprite_validation/validation_results.json','save_upgrade_results.json','village_validation/validation_results.json','speaker_portraits/emulator_validation.json','combat_assets/in_game/validation.json','title_music/validation.json','sound_effects/validation.json','lazy_quest_validation/validation.json','quest_markers/validation_results.json','menu_skin/validation.json']
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def add(z,path,name):
    info=zipfile.ZipInfo(str(name),(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
    z.writestr(info,path.read_bytes())
def main():
    source=ROOT/'pokecrystal.gbc';rom=source.read_bytes();sha=digest(source)
    assets=ROOT/'references/generated/durotar_v021'
    reports=[json.loads((assets/p).read_text()) for p in REPORTS]
    assert all(r['rom_sha256']==sha for r in reports),'Validation reports are stale'
    intro,sprites,upgrade,villages,portraits,combat,music,sfx,lazy,atlas,menus=reports
    for key in ['new_game_reaches_den','master_asks_name','neutral_boar_does_not_aggro','scorpid_proximity_aggro_passed','second_quest_map_reward_passed','zone_map_and_fog_render_passed','equipment_persists_in_existing_held_item_field','classic_vendor_bundle_price_passed','cactus_quest_and_bag_upgrade_passed','red_imp_combat_and_loot_passed','zone_discovery_flags_passed','save_cold_restart_passed','battle_self_returns_cleanly','active_battle_bags_diagnostic_passed']:
        assert intro[key],key
    assert len(sprites['renderer_facings_verified'])==16 and sprites['save_cold_restart_passed']
    assert upgrade['v0_1_1_save_upgrade_passed'] and upgrade['v0_2_save_upgrade_passed']
    assert villages['all_checks_passed'] and villages['npc_count']==18 and villages['building_count']==9
    assert villages['inside_troll_hut_save_cold_restart']['passed']
    assert len(portraits['portrait_variants'])==13
    normal=portraits['ordinary_button_gornek_dialogue']
    assert normal['native_rgb555_matches'] and normal['close_text_restores_map_and_palette'] and not normal['speaker_metadata_substituted']
    for role in portraits['portrait_variants'].values():assert role['native_rgb555_matches'] and role['close_text_restores_map_and_palette']
    assert combat['poison_damage_1_8_max_hp']
    assert combat['native_encounter_no_trainer_or_creature_naming']
    assert all(combat['native_attack_pixel_matches'].values())
    poses=combat['native_pose_pixel_matches']
    assert set(poses)=={'boar','scorpid','imp'}
    for role in poses.values():assert set(role)=={'idle','prepare','attack','return'} and all(role.values())
    assert music['native_four_channel_apu_capture'] and music['three_synchronized_phrase_entries_per_channel'] and music['start_reaches_character_select']
    assert sfx['all_checks_passed']
    assert lazy['all_checks_passed'] and lazy['save_cold_restart']['passed']
    assert lazy['campfire']['native_heal_invoked'] and lazy['lazy_peons']['reward_only_once']
    assert len(lazy['neutral_yellow_boars'])==2
    assert atlas['ordinary_new_game_reached_den'] and len(atlas['cases'])==9
    for case in atlas['cases']:
        assert case['rgb555_matches'] and case['background_vram_unchanged'] and case['closed_to_world']
        assert case['registers_vbk_oam_guard_preserved']
    assert menus['all_checks_passed']
    assert menus['bags']['three_card_frames_and_labels_do_not_overlap']
    assert set(menus['diagnostic_rarity_cases'])=={'gray','white','green','blue'}
    for case in menus['diagnostic_rarity_cases'].values():
        assert case['native_percent_glyph_rgb555_matches'] and case['outer_frame_not_overwritten_by_text']
        assert case['world_graphics_palettes_restored']
    for role in ('boar','scorpid','imp'):
        assert combat['enemy_attacks'][role]['hook_calls']>0 and {0,1,2,3}.issubset(combat['enemy_attacks'][role]['frames'])
    assert len(rom)==2097152 and rom[0x143]==0xc0 and rom[0x147]==0x10 and rom[0x149]==3
    header=0
    for value in rom[0x134:0x14d]:header=(header-value-1)&255
    assert header==rom[0x14d]
    assert (sum(rom)-rom[0x14e]-rom[0x14f])&65535==int.from_bytes(rom[0x14e:0x150],'big')
    out=ROOT/'releases/v0.2.1';out.mkdir(parents=True,exist_ok=True);name='peon_of_warcraft_v0_2_1'
    (out/(name+'.gbc')).write_bytes(rom)
    shutil.copyfile(ROOT/'docs/V0_2_1_PLAYABLE.md',out/'README.md')
    with zipfile.ZipFile(out/(name+'.zip'),'w') as z:
        add(z,out/(name+'.gbc'),name+'.gbc');add(z,out/'README.md','README.md')
        for path in REPORTS:add(z,assets/path,'validation/'+path)
    with zipfile.ZipFile(out/(name+'_assets.zip'),'w') as z:
        for directory in ['durotar_v021','durotar_v02','title_portal_gbc']:
            base=ROOT/'references/generated'/directory
            for p in sorted(base.rglob('*')):
                if p.is_file():add(z,p,p.relative_to(base.parent))
        add(z,out/'README.md','README.md')
    (out/'SHA256SUMS.txt').write_text(''.join(digest(out/(name+suffix))+'  '+name+suffix+'\n' for suffix in ['.gbc','.zip','_assets.zip']))
    print('Validated release:',out,'ROM SHA256:',sha)
if __name__=='__main__':main()
