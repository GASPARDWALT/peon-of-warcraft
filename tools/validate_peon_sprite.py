#!/usr/bin/env python3
"""Exercise the built ROM in PyBoy without touching personal saves or ROM data.

Run with a Python environment containing PyBoy and Pillow. All state files and
battery saves belong to an isolated temporary copy of the ROM. Renderer checks
force only the player-facing field, then normal D-pad movement is tested without
that hook. Results go to references/generated/v0_1_sprite_validation/.
"""
import hashlib
import io
import json
import logging
import shutil
import tempfile
from pathlib import Path

from pyboy import PyBoy

logging.disable(logging.CRITICAL)
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'references/generated/durotar_v021/sprite_validation'


def symbols():
    result = {}
    for line in (ROOT / 'pokecrystal.sym').read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and ':' in parts[0]:
            try:
                bank, address = (int(n, 16) for n in parts[0].split(':'))
            except ValueError:
                continue
            result[parts[1]] = (bank, address)
    return result


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sym = symbols()
    rom = (ROOT / 'pokecrystal.gbc').read_bytes()
    tile_data = (ROOT / 'gfx/sprites/peon.2bpp').read_bytes()
    assert len(tile_data) == 48 * 16
    results = {'rom_sha256': hashlib.sha256(rom).hexdigest(), 'rom_bytes': len(rom)}
    with tempfile.TemporaryDirectory(prefix='peon-sprite-') as directory:
        path = Path(directory) / 'test.gbc'
        shutil.copyfile(ROOT / 'pokecrystal.gbc', path)
        p = PyBoy(str(path), window='null', sound_emulated=False, log_level='ERROR')
        p.set_emulation_speed(0)

        def read(name, length=1):
            bank, address = sym[name]
            return list(p.memory[bank, address:address + length])

        def press(key, frames=120):
            p.button(key, delay=10)
            p.tick(frames, True)

        def capture(name):
            p.screen.image.save(str(OUTPUT / name))

        p.tick(1800, False)
        press('start'); press('down'); press('a')
        for _ in range(180):
            press('a', 90)
        p.tick(300, True)
        assert read('wMapGroup', 2) == [26, 14], read('wMapGroup', 2)
        assert read('wPlayerPalette')[0] & 7 == 2
        capture('peon_den.png')

        tile_base = read('wPlayerSpriteTile')[0]
        vram_bank = 0 if tile_base & 128 else 1
        tile_base &= 127
        address = 0x8000 + tile_base * 16
        actual_idle = bytes(p.memory[vram_bank, address:address + 256])
        assert actual_idle == tile_data[:256], {
            'tile_base': tile_base, 'vram_bank': vram_bank,
            'used_sprites': read('wUsedSprites', 24),
            'expected_prefix': tile_data[:32].hex(), 'actual_prefix': actual_idle[:32].hex(),
            'first_difference': next((i for i, (a, b) in enumerate(zip(actual_idle, tile_data)) if a != b), None),
        }
        assert bytes(p.memory[vram_bank, address + 0x800:address + 0x800 + 512]) == tile_data[256:]
        results['vram_graphics_match'] = True
        results['vram_bank'] = vram_bank
        results['idle_tiles'] = 16
        results['walking_tiles'] = 32

        baseline = io.BytesIO()
        p.save_state(baseline)
        oam_bank, oam_address = sym['wShadowOAM']
        facing_bank, facing_address = sym['wPlayerFacing']
        update_bank, update_address = sym['_UpdateSprites']
        checked = []
        for facing in range(16):
            baseline.seek(0); p.load_state(baseline)
            p.hook_register(update_bank, update_address,
                            lambda value: p.memory.__setitem__((facing_bank, facing_address), value), facing)
            p.tick(3, True)
            phase = facing & 3
            direction = facing // 4
            frame_tile = direction * 4 + (0 if phase % 2 == 0 else (0x80 if phase == 1 else 0x90))
            expected = [tile_base + frame_tile + n for n in range(4)]
            oam = list(p.memory[oam_bank, oam_address:oam_address + 160])
            entries = [oam[n:n + 4] for n in range(0, 160, 4) if oam[n] != 160]
            actual = [entry for entry in entries if entry[2] in expected
                      and bool(entry[3] & 8) == bool(vram_bank)]
            assert sorted(entry[2] for entry in actual) == expected, (facing, expected, entries)
            assert all(not (entry[3] & 0x20) for entry in actual), (facing, actual)
            assert all((entry[3] & 7) == 2 for entry in actual), (facing, actual)
            assert all(bool(entry[3] & 8) == bool(vram_bank) for entry in actual)
            capture(f'peon_facing_{facing:02d}.png')
            checked.append(facing)
            p.hook_deregister(update_bank, update_address)
        results['renderer_facings_verified'] = checked
        results['mirrored_accessories'] = False

        baseline.seek(0); p.load_state(baseline)
        start = read('wMapGroup', 4)
        steps = []
        animation = []
        for key in ('left', 'right', 'up', 'down'):
            baseline.seek(0); p.load_state(baseline)
            p.button_press(key)
            facings = set()
            for frame in range(40):
                p.tick(1, True)
                facings.add(read('wPlayerFacing')[0])
                if frame % 4 == 0:
                    animation.append(p.screen.image.copy())
            p.button_release(key); p.tick(90, True)
            end = read('wMapGroup', 4)
            steps.append({'direction': key, 'start': start, 'end': end, 'facings': sorted(facings)})
            capture(f'peon_walk_{key}.png')
        assert sum(step['start'] != step['end'] for step in steps) >= 2, steps
        assert all(any(facing % 4 in (1, 3) for facing in step['facings']) for step in steps), steps
        results['normal_movement'] = steps
        animation[0].save(OUTPUT / 'peon_walking.gif', save_all=True,
                          append_images=animation[1:], duration=67, loop=0)

        # The Den is the sole free-play map; scripted intro warps are tested by
        # validate_peon_intro.py. Check ordinary NPC allocation in this map.
        baseline.seek(0); p.load_state(baseline)
        capture('peon_npc_allocation.png')
        assert read('wMapGroup', 2) == [26, 14], read('wMapGroup', 4)
        results['map_for_npc_allocation'] = read('wMapGroup', 4)

        # Other ordinary sprites retain their original graphics at their new
        # VRAM offsets. Variable icons resolve through the runtime table.
        checked_npcs = []
        sprites_bank, sprites_address = sym['OverworldSprites']
        for index in range(0, 64, 2):
            sprite, tile = read('wUsedSprites', 64)[index:index + 2]
            if sprite == 0:
                break
            if sprite >= 0xf0:
                sprite = read('wVariableSprites', 16)[sprite - 0xf0]
            if sprite >= 0x80 or sprite in (1, 0x3f) or sprite == 0:
                continue
            entry_address = sprites_address + (sprite - 1) * 6
            entry = list(p.memory[sprites_bank, entry_address:entry_address + 6])
            source = entry[0] + entry[1] * 256
            length = entry[2]
            bank = 0 if tile & 128 else 1
            destination = 0x8000 + (tile & 127) * 16
            expected = bytes(p.memory[entry[3], source:source + length])
            actual = bytes(p.memory[bank, destination:destination + length])
            assert actual == expected, ('NPC graphics changed', sprite, tile)
            checked_npcs.append(sprite)
        assert checked_npcs, 'No ordinary NPC sprite checked after transition'
        results['npc_graphics_verified'] = checked_npcs

        # Save at the verified Den baseline using the game's own menu.
        baseline.seek(0); p.load_state(baseline)
        before = {name: read(name, length) for name, length in
                  [('wPlayerName', 11), ('wPlayerID', 2), ('wMoney', 3), ('wMapGroup', 4)]}
        press('start'); press('down'); press('down'); press('down'); press('a')
        for _ in range(5): press('a', 180)
        p.stop(save=True)
        assert (Path(str(path) + '.ram')).stat().st_size == 32768

        p = PyBoy(str(path), window='null', sound_emulated=False, log_level='ERROR')
        p.set_emulation_speed(0)
        p.tick(1800, True); press('start')
        capture('peon_continue_menu.png')
        for _ in range(5): press('a', 180)
        p.tick(180, True)
        after = {name: read(name, length) for name, length in
                 [('wPlayerName', 11), ('wPlayerID', 2), ('wMoney', 3), ('wMapGroup', 4)]}
        assert before == after, (before, after)
        capture('peon_after_save_restart.png')
        results['save_cold_restart_passed'] = True
        results['player_state_before_save'] = before
        results['player_state_after_restart'] = after
        p.stop(save=False)
    results['emulator'] = 'PyBoy 2.7.0'
    results['limitations'] = ['Chromatic hardware untested', 'Unreachable bike, surf and fishing presentations are not adapted', 'Sound not emulated in this check']
    (OUTPUT / 'validation_results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
