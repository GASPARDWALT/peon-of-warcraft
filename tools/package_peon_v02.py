#!/usr/bin/env python3
"""Package only the current ROM after all three emulator reports agree."""
import hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    rom=(ROOT/'pokecrystal.gbc').read_bytes();digest=hashlib.sha256(rom).hexdigest()
    assets=ROOT/'references/generated/durotar_v02'
    reports=[json.loads((assets/p).read_text()) for p in ['in_game/validation_results.json','sprite_validation/validation_results.json','save_upgrade_results.json']]
    assert all(r['rom_sha256']==digest for r in reports),'Validation is stale'
    intro,sprites,upgrade=reports
    for key in ['new_game_reaches_den','master_asks_name','neutral_boar_does_not_aggro','scorpid_proximity_aggro_passed','second_quest_map_reward_passed','zone_map_and_fog_render_passed','equipment_persists_in_existing_held_item_field','classic_vendor_bundle_price_passed','cactus_quest_and_bag_upgrade_passed','red_imp_combat_and_loot_passed','zone_discovery_flags_passed','save_cold_restart_passed']:
        assert intro[key],key
    assert len(sprites['renderer_facings_verified'])==16 and sprites['save_cold_restart_passed']
    assert upgrade['v0_1_1_save_upgrade_passed']
    assert len(rom)==2097152 and rom[0x143]==0xc0 and rom[0x147]==0x10 and rom[0x149]==3
    header=0
    for value in rom[0x134:0x14d]:header=(header-value-1)&255
    assert header==rom[0x14d]
    assert (sum(rom)-rom[0x14e]-rom[0x14f])&65535==int.from_bytes(rom[0x14e:0x150],'big')
    out=ROOT/'releases/v0.2';out.mkdir(parents=True,exist_ok=True);name='peon_of_warcraft_v0_2'
    (out/(name+'.gbc')).write_bytes(rom)
    shutil.copyfile(ROOT/'docs/V0_2_PLAYABLE.md',out/'README.md')
    with zipfile.ZipFile(out/(name+'.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        z.write(out/(name+'.gbc'),name+'.gbc');z.write(out/'README.md','README.md')
        for path in ['in_game/validation_results.json','sprite_validation/validation_results.json','save_upgrade_results.json']:z.write(assets/path,'validation/'+path)
    with zipfile.ZipFile(out/(name+'_assets.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(assets.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(assets))
    sums=[]
    for suffix in ['.gbc','.zip','_assets.zip']:
        p=out/(name+suffix);sums.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name)
    (out/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n')
    print('Validated release:',out,'ROM SHA256:',digest)
if __name__=='__main__':main()
