#!/usr/bin/env python3
"""Create a real v0.1.1 battery save, then continue it using the current ROM."""
import hashlib,json,shutil,tempfile,logging
from pathlib import Path
from pyboy import PyBoy
logging.disable(logging.CRITICAL)
ROOT=Path(__file__).resolve().parents[1]
def validate_release(release, source):
    sym={}
    for row in (ROOT/'pokecrystal.sym').read_text().splitlines():
        parts=row.split()
        if len(parts)==2 and ':' in parts[0]:
            sym[parts[1]]=tuple(int(n,16) for n in parts[0].split(':'))
    with tempfile.TemporaryDirectory(prefix='peon-save-upgrade-') as d:
        rom=Path(d)/'upgrade.gbc'
        shutil.copyfile(ROOT/source,rom)
        p=PyBoy(str(rom),window='null',sound_emulated=False,log_level='ERROR');p.set_emulation_speed(0)
        def read(n,l=1):
            bank,addr=sym[n];return list(p.memory[bank,addr:addr+l])
        def press(k,t=120):p.button(k,delay=8);p.tick(t,True)
        p.tick(1800,True);press('start');press('down');press('a')
        for _ in range(180):
            press('a')
            if read('wMapGroup',2)==[26,14] and read('wScriptMode')[0]==0:break
        assert read('wMapGroup',2)==[26,14]
        before={n:read(n,l) for n,l in [('wPlayerName',11),('wPlayerID',2),('wMapGroup',2),('wXCoord',1),('wYCoord',1),('wPartyMon1Moves',4),('wKeyItems',3)]}
        press('start')
        for _ in range(3):press('down',30)
        press('a')
        for _ in range(6):press('a',180)
        p.stop(save=True)
        assert Path(str(rom)+'.ram').stat().st_size==32768
        shutil.copyfile(ROOT/'pokecrystal.gbc',rom)
        p=PyBoy(str(rom),window='null',sound_emulated=False,log_level='ERROR');p.set_emulation_speed(0)
        p.tick(1800,True);press('start')
        for _ in range(6):press('a',180)
        after={n:read(n,l) for n,l in [('wPlayerName',11),('wPlayerID',2),('wMapGroup',2),('wXCoord',1),('wYCoord',1),('wPartyMon1Moves',4),('wKeyItems',3)]}
        assert before==after,(before,after)
        p.stop(save=False)
    return after

def main():
    states={}
    for version,path in [('v0_1_1','releases/v0.1.1/peon_of_warcraft_v0_1_1.gbc'),('v0_2','releases/v0.2/peon_of_warcraft_v0_2.gbc')]:
        states[version]=validate_release(version,path)
    report={'rom_sha256':hashlib.sha256((ROOT/'pokecrystal.gbc').read_bytes()).hexdigest(),'v0_1_1_save_upgrade_passed':True,'v0_2_save_upgrade_passed':True,'states':states,'scope':'Existing v0.1.1 and v0.2 characters at The Den. Other locations and Chromatic hardware not tested.'}
    out=ROOT/'references/generated/durotar_v021/save_upgrade_results.json';out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
