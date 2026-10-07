#!/usr/bin/env python3
"""Package only a ROM matching both successful emulator test reports."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    rom=(ROOT/'pokecrystal.gbc').read_bytes()
    digest=hashlib.sha256(rom).hexdigest()
    intro=json.loads((ROOT/'references/generated/v0_1_playable/validation_results.json').read_text())
    sprite=json.loads((ROOT/'references/generated/v0_1_sprite_validation/validation_results.json').read_text())
    assert intro['rom_sha256']==sprite['rom_sha256']==digest
    assert intro['new_game_reaches_den'] and intro['save_cold_restart_passed']
    assert intro['battle_result']==0 and 84 in intro['moves_observed_in_battle']
    assert intro['native_title_rgb555_matches']
    assert len(sprite['renderer_facings_verified'])==16
    assert sprite['save_cold_restart_passed']
    assert len(rom)==2097152
    assert rom[0x143]==0xc0 and rom[0x147]==0x10 and rom[0x149]==3
    checksum=0
    for b in rom[0x134:0x14d]: checksum=(checksum-b-1)&255
    assert checksum==rom[0x14d]
    assert (sum(rom)-rom[0x14e]-rom[0x14f])&65535==int.from_bytes(rom[0x14e:0x150],'big')
    out=ROOT/'releases/v0.1.1'; out.mkdir(parents=True,exist_ok=True)
    name='peon_of_warcraft_v0_1_1'
    (out/(name+'.gbc')).write_bytes(rom)
    (out/'SHA256SUMS.txt').write_text(digest+'  '+name+'.gbc\n')
    shutil.copyfile(ROOT/'docs/V0_1_PLAYABLE.md',out/'README.md')
    with zipfile.ZipFile(out/(name+'.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for p in [out/(name+'.gbc'),out/'SHA256SUMS.txt',out/'README.md']:
            z.write(p,p.name)
        for folder in ('v0_1_playable','v0_1_sprite_validation'):
            p=ROOT/'references/generated'/folder/'validation_results.json'
            z.write(p,'validation/'+folder+'.json')
    print(out/(name+'.zip'))
    print('SHA256',digest)

if __name__=='__main__': main()
