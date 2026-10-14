#!/usr/bin/env python3
"""Bounded native-button QA for calmer floors, both portal lanes and the lodge.

Every run uses a fresh disposable ROM. Hooks and VRAM/PPU reads only observe;
no RAM writes, CPU substitution, emulator states or user batteries are allowed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import logging
import shutil
import tempfile

from PIL import Image
from validate_peon_masters_sleeping_v0213 import MasterSession
from validate_peon_earth_stone_v0212 import symbols
from validate_peon_villages import MAPS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'references/generated/quieter_ground_v0214'


def check_native(session):
    """Read the actual padded map and displayed PPU, not an image-only gallery."""
    name, width, height = MAPS[session.map()]
    exterior = session.map() != 22
    folder = ROOT/('gfx/quieter_ground_v0214' if exterior else 'gfx/readable_interiors_v0212')
    source = (folder/f'{name}.2bpp').read_bytes()
    p = session.p
    assert bytes(p.memory[0, 0x9040:0x9600]) == source[64:1536], (name, 'base bank0 graphics')
    assert bytes(p.memory[1, 0x9000:0x9600]) == source[1536:3072], (name, 'base bank1 graphics')
    if exterior:
        assert len(source) == 216*16
        assert bytes(p.memory[1, 0x8e00:0x8f80]) == source[3072:3456], (name, 'extended bank1 graphics')
    else:
        assert len(source) == 192*16
    meta = (folder/f'{name}_meta.bin').read_bytes()
    palettes = (folder/f'{name}_palmap.bin').read_bytes()
    priorities = (folder/f'{name}_priority.bin').read_bytes()
    base = 0x9c00 if p.memory[0xff40] & 8 else 0x9800
    scx, scy = p.memory[0xff43], p.memory[0xff42]
    assert scx % 8 == scy % 8 == 0, (name, 'stationary PPU required')
    origin_x, origin_y = session.position()[0]*2-8, session.position()[1]*2-8
    block_bank, block_address = session.sym['wOverworldMapBlocks']
    compared, extra = 0, []
    for y in range(18):
        for x in range(20):
            wx, wy = origin_x+x, origin_y+y
            if not (0 <= wx < width*4 and 0 <= wy < height*4):
                continue
            bx, tx = divmod(wx, 4)
            by, ty = divmod(wy, 4)
            block = p.memory[block_bank, block_address+(by+3)*(width+6)+bx+3]
            logical = meta[block*16+ty*4+tx]
            attr = (palettes[logical//2] >> ((logical % 2)*4)) & 15
            attr |= 128 if priorities[logical//8] & (128 >> (logical % 8)) else 0
            address = base+((scy//8+y) % 32)*32+(scx//8+x) % 32
            tile = logical & (255 if logical >= 224 else 127)
            assert p.memory[0, address] == tile and p.memory[1, address] == attr, (
                name, 'displayed PPU tile/palette/bank/priority mismatch', x, y, logical,
                p.memory[0, address], p.memory[1, address], tile, attr)
            compared += 1
            if logical >= 224:
                extra.append([x, y, logical])
    # Moving object allocations must never occupy the signed background extension.
    oam = list(p.memory[0xfe00:0xfea0])
    for i in range(0, 160, 4):
        y, x, tile, attr = oam[i:i+4]
        assert not (x and y and attr & 8 and 0xe0 <= tile < 0xf8), (name, 'OBJ overlaps background extension')
    return {'map': name, 'position': session.position(), 'base_192_patterns_in_real_vram_exact': True,
            'extended_24_patterns_in_real_vram_exact': exterior,
            'visible_world_tile_ids_palette_bank_priority_exact': True,
            'compared_in_world_ppu_cells': compared, 'visible_extended_cells': extra,
            'no_live_oam_background_extension_overlap': True, 'scroll': [scx, scy]}


class GroundSession(MasterSession):
    def __init__(self, *args):
        self.ground_checks = []
        super().__init__(*args)

    def capture_checked(self, name):
        self.p.tick(90, True)
        assert self.read('wScriptMode') == [0] and self.read('wBattleMode') == [0]
        check = check_native(self)
        check['capture'] = name
        self.ground_checks.append(check)
        self.capture(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--sym', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'result': 'RUNNING', 'rom': str(args.rom),
              'rom_sha256': hashlib.sha256(args.rom.read_bytes()).hexdigest(),
              'ordinary_new_shaman_game': True, 'ram_writes': False, 'emulator_states': False,
              'user_batteries_opened': False, 'world_routes': [], 'checks': []}
    with tempfile.TemporaryDirectory(prefix='peon-quieter-ground-') as directory:
        rom = Path(directory)/'ground.gbc'
        shutil.copyfile(args.rom, rom)
        session = GroundSession(rom, symbols(args.sym), 0, args.output)
        try:
            session.fresh_class()
            session.navigate((12, 9))
            session.capture_checked('the_den_quiet_floor_and_clear_paths')
            session.enter_lodge()
            report['approved_lodge_and_three_full_masters'] = session.master_scene()
            session.capture_checked('approved_lodge_three_masters_unchanged')
            session.leave_lodge()
            session.navigate((19, 10))
            session.capture_checked('the_den_spiked_gateway_approach')
            for lane in range(2):
                session.navigate((20, 10+lane), 15)
                arrival = session.position()
                session.navigate((5, 12))
                session.capture_checked(f'zone2_gateway_lane_{lane+1}_safe_arrival')
                assert session.map() == 15 and session.collision_at(5, 12) == 'FLOOR'
                if lane == 0:
                    session.navigate((8, 11))
                    session.capture_checked('zone2_south_of_cactus_questgiver')
                    session.navigate((9, 8))
                    session.capture_checked('zone2_north_of_cactus_questgiver')
                session.navigate((4, 12+lane), 14)
                returned = session.position()
                session.navigate((19, 10))
                session.capture_checked(f'the_den_gateway_lane_{lane+1}_safe_return')
                report['world_routes'].append({'outbound_lane': [20, 10+lane], 'zone2_arrival': arrival,
                                                'inbound_lane': [4, 12+lane], 'the_den_arrival': returned,
                                                'two_way_warp_and_floor_egress': True})
            report['checks'] = session.ground_checks
            report['result'] = 'PASS'
        except Exception as error:
            report['result'] = 'FAIL'
            report['error'] = repr(error)
            session.capture('failure')
            raise
        finally:
            report['checks'] = session.ground_checks
            (args.output/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
            session.p.stop(save=False)
    print(json.dumps({'result': report['result'], 'rom_sha256': report['rom_sha256'],
                      'native_ppu_checks': len(report['checks']), 'two_way_routes': len(report['world_routes'])}))


if __name__ == '__main__':
    main()
