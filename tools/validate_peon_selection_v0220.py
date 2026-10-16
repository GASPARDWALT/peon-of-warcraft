#!/usr/bin/env python3
"""Run unchanged native selection/SAVE routes against the v20 ground packets."""
import json
from pathlib import Path
import validate_peon_selection_v0219 as prior

ROOT=Path(__file__).resolve().parents[1]


class SelectionSessionV0220(prior.SelectionSession):
    def open(self):
        super().open()
        self.native_gfx_entries=[]
        def entry(_):
            self.native_gfx_entries.append(dict(frame=self.p.frame_count,map=self.map(),
                VBK=self.p.memory[0xff4f]&1,WBK=self.p.memory[0xff70]&7,
                tileset_bank=self.read('wTilesetBank'),tileset_address=self.read('wTilesetAddress',2)))
        self.p.hook_register(*self.sym['PeonLoadNativeTilesetGFXV0213'],entry,None)

    def terrain_restored(self,name):
        path=ROOT/('gfx/readable_interiors_v0212/GrommashHold.2bpp' if name=='GrommashHold'
                   else 'gfx/quieter_ground_v0220/TheDen.2bpp')
        label='PeonReadableGrommashHoldGFXV0212' if name=='GrommashHold' else 'PeonUserEnvTheDenGFX'
        pointer=(self.read('wTilesetBank')[0],int.from_bytes(bytes(self.read('wTilesetAddress',2)),'little'))
        assert pointer==self.sym[label],('Unexpected source',name,pointer)
        data=path.read_bytes();actual=self.terrain_pair();animated=name=='TheDen'
        if animated:
            bank,address=self.sym['PeonUniformEnvironmentFireFramesV0220']
            offset=bank*0x4000+address-0x4000
            fire=self.rom_bytes[offset:offset+192]
            assert fire==(ROOT/'gfx/quieter_ground_v0220/fire_frames_world.bin').read_bytes()
            for tile in range(4):
                allowed=[data[tile*16:(tile+1)*16]]+[fire[p*64+tile*16:p*64+(tile+1)*16] for p in range(3)]
                assert actual[0][tile*16:(tile+1)*16] in allowed,('Native exterior fire differs',tile)
        begin=64 if animated else 0
        try:
            assert actual[0][begin:]==data[begin:1536] and actual[1]==data[1536:3072],('Native terrain not restored',name)
            if animated:assert bytes(self.p.memory[1,0x8e00:0x8f80])==data[3072:3456]
        except AssertionError:
            folder=self.folder;folder.mkdir(parents=True,exist_ok=True)
            for bank,payload in enumerate(actual):(folder/f'terrain_bank{bank}_failure.bin').write_bytes(payload)
            (folder/'native_loader_entries.json').write_text(json.dumps(self.native_gfx_entries,indent=2)+'\n')
            raise
        return dict(source=prior.source_record(path),bank0_static_terrain_exact=True,
                    native_brazier_cells_checked_against_compiled_phases=4 if animated else 0,
                    bank1_9000_95ff_exact=True,bank1_8e00_8f7f_exact=animated,
                    native_loader_entry_contexts=self.native_gfx_entries)


if __name__=='__main__':
    prior.SelectionSession=SelectionSessionV0220
    prior.main()
