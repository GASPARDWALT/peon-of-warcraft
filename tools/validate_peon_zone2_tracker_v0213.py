#!/usr/bin/env python3
"""Observe Zone 2 quest-giver scrolling and map screens through native controls.

Every run starts a new Shaman in an isolated ROM copy. Emulator hooks only
observe; no WRAM edits, CPU substitution, save states or user batteries occur.
"""
from pathlib import Path
import argparse, hashlib, json, logging, re, shutil, tempfile
from PIL import Image
from validate_peon_class_routes import ClassSession
from validate_peon_villages import MAPS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/zone2_tracker_v0213'


def symbols(path):
    result = {}
    for row in path.read_text().splitlines():
        parts = row.split()
        if len(parts) == 2 and ':' in parts[0]:
            try: result[parts[1]] = tuple(int(v, 16) for v in parts[0].split(':'))
            except ValueError: pass
    return result


class Zone2Session(ClassSession):
    def __init__(self, rom, sym, folder):
        self.folder, self.captures = folder, []
        super().__init__(rom, sym, 0)
        for match in re.finditer(r'^\s*DEF\s+(EVENT_\w+)\s+EQU\s+(\$[0-9a-fA-F]+|\d+)\b',
                                 (ROOT / 'constants/event_flags.asm').read_text(), re.M):
            number = match[2]
            self.flags[match[1]] = int(number[1:], 16) if number.startswith('$') else int(number)

    def write(self, *args, **kwargs):
        raise AssertionError('Zone 2 validation permits no emulator RAM writes')

    def rest(self):
        self.go_den(); self.navigate((17, 5), 23)
        self.talk_plain((6, 5), 'up')
        assert self.read('wPartyMon1HP', 2) == self.read('wPartyMon1MaxHP', 2)
        self.navigate((5, 9), 14)

    def collision_at(self, x, y):
        _, w, h = MAPS[self.map()]
        if not (0 <= x < w * 2 and 0 <= y < h * 2): return 'WALL'
        bank, address = self.sym['wOverworldMapBlocks']
        block = self.p.memory[bank, address + (y // 2 + 3) * (w + 6) + x // 2 + 3]
        if not block: return 'WALL'
        bank = self.read('wTilesetCollisionBank')[0]
        pointer = self.read('wTilesetCollisionAddress', 2)
        address = pointer[0] | pointer[1] << 8
        return 'WALL' if self.p.memory[bank, address + block * 4 + y % 2 * 2 + x % 2] == 7 else 'FLOOR'

    def capture(self, name):
        self.folder.mkdir(parents=True, exist_ok=True)
        self.p.screen.image.save(self.folder / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(self.folder / (name + '_4x.png'))
        state = {'name': name, 'map': self.map(), 'position': self.position(),
                 'registers': {hex(a): self.p.memory[a] for a in (0xff40, 0xff42, 0xff43, 0xff4a, 0xff4b, 0xff4f)},
                 'native': {k: self.read(k) for k in ('hSCX', 'hSCY', 'hBGMapMode', 'hBGMapThird', 'wScriptMode', 'wMapTileset', 'wTileset')},
                 'bgmap_anchor': self.read('wBGMapAnchor', 2),
                 'window_y': self.read('hWY'), 'state_flags': self.read('wStateFlags'),
                 'static_map_vram_sha256': [hashlib.sha256(bytes(self.p.memory[bank, start:0x9600])).hexdigest()
                                            for bank, start in ((0, 0x9040), (1, 0x9000))],
                 'bgpals1_sha256': hashlib.sha256(bytes(self.read('wBGPals1', 64))).hexdigest(),
                 'bgpals2_sha256': hashlib.sha256(bytes(self.read('wBGPals2', 64))).hexdigest(),
                 'tilemap': self.read('wTilemap', 360), 'attrmap': self.read('wAttrmap', 360)}
        base = 0x9c00 if self.p.memory[0xff40] & 8 else 0x9800
        scx, scy = self.p.memory[0xff43] // 8, self.p.memory[0xff42] // 8
        visible = [base + ((scy + y) % 32) * 32 + (scx + x) % 32 for y in range(18) for x in range(20)]
        state['visible_ppu_tiles'] = [self.p.memory[0, p] for p in visible]
        state['visible_ppu_attrs'] = [self.p.memory[1, p] for p in visible]
        self.captures.append(state)
        print(name, self.map(), self.position(), state['registers'], state['native'], flush=True)
        return state

    def map_cycle(self, name):
        before = self.capture(name + '_world')
        record = self.persistent_snapshot()
        self.press('select', 120)
        panel = self.capture(name + '_panel')
        self.press('b', 120)
        after = self.capture(name + '_return')
        assert self.map() == 15 and self.read('wScriptMode') == [0]
        assert record == self.persistent_snapshot(), 'Map screen changed player/quest/save record'
        tiles_equal = before['visible_ppu_tiles'] == after['visible_ppu_tiles']
        attrs_equal = before['visible_ppu_attrs'] == after['visible_ppu_attrs']
        vram_equal = before['static_map_vram_sha256'] == after['static_map_vram_sha256']
        return {'before': before['native'], 'panel': panel['native'], 'after': after['native'],
                'panel_scroll_zero': panel['native']['hSCX'] == [0] and panel['native']['hSCY'] == [0],
                'visible_world_tiles_restored': tiles_equal, 'visible_world_attrs_restored': attrs_equal,
                'static_map_vram_restored': vram_equal,
                'native_record_unchanged': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', type=Path, default=ROOT / 'pokecrystal.gbc')
    parser.add_argument('--sym', type=Path, default=ROOT / 'pokecrystal.sym')
    parser.add_argument('--variant', default='current')
    parser.add_argument('--expect-fixed', action='store_true')
    parser.add_argument('--unlocked', action='store_true', help='Finish native Gornek battles before testing the owned atlas')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    folder = OUT / args.variant
    folder.mkdir(parents=True, exist_ok=True)
    for image in folder.glob('first_failure*.png'): image.unlink()
    report = {'rom_sha256': hashlib.sha256(args.rom.read_bytes()).hexdigest(),
              'ordinary_new_shaman_buttons_only': True, 'ram_edits': False,
              'save_states_loaded': False, 'user_save_opened': False,
              'fixed_behavior_required': args.expect_fixed, 'native_gornek_unlock_requested': args.unlocked,
              'status': 'RUNNING', 'cycles': {}}
    with tempfile.TemporaryDirectory(prefix='peon-zone2-tracker-') as temp:
        rom = Path(temp) / 'zone2.gbc'; shutil.copyfile(args.rom, rom)
        s = Zone2Session(rom, symbols(args.sym), folder)
        try:
            s.fresh_class()
            s.navigate((20, 10), 15); s.p.tick(120, True)
            s.navigate((8, 11)); s.p.tick(60, True)
            report['cycles']['south_locked'] = s.map_cycle('south_locked')
            s.talk_plain((8, 11), 'up')
            assert s.event('EVENT_PEON_CACTUS_ACCEPTED')
            for position in ((9, 10), (9, 9), (9, 8), (8, 8), (8, 7)):
                s.navigate(position); s.p.tick(60, True)
                s.capture('north_walk_' + '_'.join(map(str, position)))
            report['cycles']['north_locked'] = s.map_cycle('north_locked')
            for position in ((8, 8), (9, 8), (9, 9), (9, 10), (8, 11)):
                s.navigate(position); s.p.tick(30, True)
            s.capture('south_after_panels')
            if args.unlocked:
                s.navigate((4, 12), 14)
                s.talk_plain((10, 10), 'up')
                s.navigate((18, 13)); s.press('up', 30); s.press('a', 120)
                assert s.fight('gornek_boar', 'EVENT_PEON_QUEST_DONE')['outcome'] == 0
                s.talk_plain((10, 10), 'up'); s.rest()
                path = s.path((17, 15))
                for key in path[:-1]: s.walk(key)
                s.press(path[-1], 60)
                assert s.fight('gornek_scorpid', 'EVENT_PEON_SCORPID_DEFEATED')['outcome'] == 0
                s.talk_plain((10, 10), 'up')
                assert s.event('EVENT_PEON_MAP_RECEIVED')
                s.navigate((20, 10), 15); s.navigate((8, 11))
                report['cycles']['south_owned'] = s.map_cycle('south_owned')
                s.navigate((9, 8)); s.navigate((8, 8))
                report['cycles']['north_owned'] = s.map_cycle('north_owned')
                s.navigate((9, 9)); s.capture('walking_after_owned_return')
            if args.expect_fixed:
                assert all(c['panel_scroll_zero'] for c in report['cycles'].values()), 'Fullscreen locked panel retained world scroll'
                assert all(c['visible_world_tiles_restored'] and c['visible_world_attrs_restored'] and c['static_map_vram_restored']
                           for c in report['cycles'].values()), 'Map return did not restore actual visible terrain tiles/attrs'
            report['status'] = 'PASS'
        except Exception as error:
            report['failure'] = repr(error); s.capture('first_failure'); raise
        finally:
            report['captures'] = s.captures
            (folder / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
            s.p.stop(save=False)
    print(json.dumps({k: v for k, v in report.items() if k != 'captures'}, indent=2))


if __name__ == '__main__': main()
