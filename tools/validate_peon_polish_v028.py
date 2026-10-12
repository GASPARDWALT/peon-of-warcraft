#!/usr/bin/env python3
"""Cross-feature v028 visual restoration through ordinary native inputs.

This complements the art/marker/door/projectile suites. It checks the complete
settled background actually read by the CGB PPU, including both tile banks,
signed tile addressing, scrolling, window placement and RGB555 palettes. Real
OBJ ink is masked, never simulated or injected. Every result names an exact ROM
and retained native frame. No emulator RAM writes, states or user batteries.
"""
from contextlib import contextmanager
from pathlib import Path
import argparse
import hashlib
import json
import logging
import shutil
import tempfile

import numpy as np
from PIL import Image

import run_peon_v023_validation as adapter
import validate_peon_class_routes as routes
import validate_peon_warlock_pet as pets
import validate_peon_villages as villages

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/polish_v028/integration'
CLASSES = ('shaman', 'warrior', 'warlock')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decode_tile(data):
    bits = np.arange(7, -1, -1, dtype=np.uint8)
    raw = np.asarray(list(data), dtype=np.uint8).reshape(8, 2)
    return (raw[:, :1] >> bits & 1) | ((raw[:, 1:] >> bits & 1) << 1)


def symbols_from(path):
    out = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) == 2 and ':' in fields[0]:
            out[fields[1]] = tuple(int(part, 16) for part in fields[0].split(':'))
    return out


class ObservedTicks:
    """Preserve native inputs while retaining every frame in selected transitions."""
    def __init__(self, native, observer):
        self.native, self.observer = native, observer

    def __getattr__(self, name):
        return getattr(self.native, name)

    def tick(self, frames=1, render=True, *args, **kwargs):
        if self.observer.transition_active is None:
            return self.native.tick(frames, render, *args, **kwargs)
        result = True
        for _ in range(frames):
            result = self.native.tick(1, True, *args, **kwargs)
            self.observer.observe_transition_frame()
        return result


@contextmanager
def redirect_previous_outputs():
    """Even inherited diagnostic/failure paths can only write in our own tree."""
    saved, seen = [], set()
    for entry in (routes, pets, villages):
        for module in adapter.local_dependencies(entry):
            if module.__name__ in seen:
                continue
            seen.add(module.__name__)
            for name in ('OUT', 'OUTPUT'):
                if isinstance(getattr(module, name, None), Path):
                    saved.append((module, name, getattr(module, name)))
                    folder = OUT / 'private_helper_outputs' / module.__name__
                    folder.mkdir(parents=True, exist_ok=True)
                    setattr(module, name, folder)
    try:
        yield
    finally:
        for module, name, original in reversed(saved):
            setattr(module, name, original)


class Session(pets.PetSession):
    def __init__(self, rom, symbols, index):
        self.slug = CLASSES[index]
        self.folder = OUT / self.slug
        self.folder.mkdir(parents=True, exist_ok=True)
        self.bg_checks = []
        self.capture_records = {}
        self.theme_checks = []
        self.interface_identity_checks = []
        self.choice_reviewed = False
        self.opening_prompts = 0
        self.opening_maps = []
        self.events = []  # inherited BagSession timeout diagnostic only
        self.transition_active = None
        self.transition_checks = []
        self.transition_frames = []
        self.transition_previous = None
        self.applied_palette_history = []
        self.applied_palette_records = []
        self.lcd_publications = []
        self.native_dma_publications = []
        self.pending_dma_stores = {}
        super().__init__(rom, symbols, index)

    def write(self, *args, **kwargs):
        raise AssertionError('The integration route never writes emulator RAM.')

    def press(self, key, frames=90):
        # The inherited trainer-only wait knows no fullscreen Bags/input
        # phases. Recognize the real hooks already installed by PetSession,
        # while preserving the ordinary button delay and readiness checks.
        battle = bool(self.read('wBattleMode')[0])
        if not battle and self.phase in ('battle', 'battle_drawing', 'using_item'):
            self.phase, self.context = 'overworld', None
        self.p.button(key, delay=4 if battle else 8)
        self.p.tick(frames, True)
        if self.read('wBattleMode')[0]:
            return
        for _ in range(100):
            if self.phase in ('overworld', 'main', 'slots', 'bags', 'inventory'):
                return
            if self.phase in ('confirm', 'message') and self.wait_ready:
                return
            self.p.tick(10, True)
        raise AssertionError(('native input phase never became ready', self.phase))

    def open(self):
        super().open()
        self.p = ObservedTicks(self.p, self)
        self.applied_palette_history = []
        self.lcd_publications = []
        self.native_dma_publications = []
        self.pending_dma_stores = {}
        self.p.hook_register(*self.sym['ForceUpdateCGBPals'], self.observe_published_palette, None)
        raw = self.rom.read_bytes()
        for label in ('DisableLCD', 'EnableLCD'):
            bank, address = self.sym[label]
            offset = address if not bank else bank * 0x4000 + (address & 0x3fff)
            position = raw[offset:offset + 80].index(bytes((0xe0, 0x40)))
            self.p.hook_register(bank, address + position, self.observe_lcd_publication, label)
        for label in ('_continue_HDMATransfer', 'HDMATransfer_NoDI', 'DMATransfer'):
            bank, address = self.sym[label]
            offset = address if not bank else bank * 0x4000 + (address & 0x3fff)
            position = raw[offset:offset + 100].index(bytes((0xe0, 0x55)))
            code = raw[offset:offset + position]
            for register in (0x51, 0x52, 0x53, 0x54):
                locations = [index for index in range(len(code) - 1)
                             if code[index:index + 2] == bytes((0xe0, register))]
                if locations:
                    assert len(locations) == 1, (label, 'ambiguous DMA register store', register)
                    self.p.hook_register(bank, address + locations[0], self.observe_dma_register_store,
                                         (label, register))
            self.p.hook_register(bank, address + position, self.observe_native_dma, label)
        self.p.hook_register(*self.sym['Script_promptbutton'], self.opening_prompt, None)
        self.p.hook_register(*self.sym['PromptButton'], self.opening_prompt_ready, None)

    def observe_published_palette(self, _):
        # The engine can publish a white fade and restore colours between
        # two end-of-frame snapshots. Observe the actual native DMA source,
        # rather than inventing a white palette from the image that we test.
        record = {'frame': self.p.frame_count, 'palette': self.palette().copy(),
                  'native_source_sha256': sha(bytes(self.read('wBGPals2', 64)))}
        self.applied_palette_history.append(record)
        self.applied_palette_history = self.applied_palette_history[-12:]
        self.applied_palette_records.append({key: value for key, value in record.items() if key != 'palette'})

    def observe_lcd_publication(self, label):
        self.lcd_publications.append({'frame': self.p.frame_count, 'scanline': self.p.memory[0xff44],
                                      'native_instruction': label + ': LDH [rLCDC],A',
                                      'old_lcdc': self.p.memory[0xff40],
                                      'new_lcdc': self.p.register_file.A})

    def observe_native_dma(self, label):
        stores = self.pending_dma_stores.pop(label, {})
        # The emulator readback for FF51..54 is write-only/zero. Retain the
        # real native stores rather than mistaking those zeros for a source.
        source = ((stores[0x51] << 8) | (stores[0x52] & 0xf0)
                  if 0x51 in stores and 0x52 in stores else None)
        destination = (0x8000 | ((stores[0x53] & 31) << 8) | (stores[0x54] & 0xf0)
                       if 0x53 in stores and 0x54 in stores else None)
        self.native_dma_publications.append({
            'frame': self.p.frame_count, 'scanline': self.p.memory[0xff44],
            'native_instruction': label + ': LDH [rVDMA_LEN],A',
            'source': source, 'destination': destination,
            'observed_native_register_stores': {hex(0xff00 + register): value for register, value in stores.items()},
            'length_register': self.p.register_file.A, 'vbk': self.p.memory[0xff4f] & 1,
            'bg_map_mode': self.read('hBGMapMode')[0]})

    def observe_dma_register_store(self, context):
        label, register = context
        self.pending_dma_stores.setdefault(label, {})[register] = self.p.register_file.A

    def opening_prompt(self, _):
        if self.read('wMapGroup', 2) == [26, 12]:
            self.opening_prompts += 1

    def opening_prompt_ready(self, _):
        if self.read('wMapGroup', 2) != [26, 12]:
            return
        name = {1: 'opening_sleeping_at_palm_prompt', 2: 'opening_hunter_prompt',
                3: 'opening_bonk_prompt'}.get(self.opening_prompts)
        if name and name not in self.capture_records:
            self.capture(name)

    def capture(self, name):
        self.p.screen.image.save(self.folder / (name + '.png'))
        self.p.screen.image.resize((640, 576), Image.Resampling.NEAREST).save(
            self.folder / (name + '_4x.png'))
        self.capture_records[name] = {
            'frame': self.p.frame_count, 'map': self.map(),
            'xy': list(self.position()), 'script_mode': self.read('wScriptMode')[0],
            'battle_mode': self.read('wBattleMode')[0],
            'native_png': str((self.folder / (name + '.png')).relative_to(ROOT)),
        }
        if name == 'master_class_description':
            self.review_class_choices()
        print(self.slug, name, self.map(), self.position(), self.phase, flush=True)

    def palette(self):
        raw = np.asarray(self.read('wBGPals2', 64), dtype=np.uint16).reshape(8, 4, 2)
        words = raw[:, :, 0] | raw[:, :, 1] << 8
        return np.stack((words & 31, words >> 5 & 31, words >> 10 & 31), axis=-1).astype(np.uint8)

    def background(self):
        """Render only actual LCD register + VRAM data, without wTilemap guesses."""
        lcdc = self.p.memory[0xff40]
        assert lcdc & 0x80, 'LCD is disabled at a supposedly settled scene'
        scroll_x, scroll_y = self.p.memory[0xff43], self.p.memory[0xff42]
        win_x, win_y = self.p.memory[0xff4b] - 7, self.p.memory[0xff4a]
        yy, xx = np.indices((144, 160))
        window = ((lcdc & 0x20) != 0) & (yy >= win_y) & (xx >= win_x) & (win_x <= 159)
        bx = np.where(window, xx - win_x, (xx + scroll_x) & 255)
        by = np.where(window, yy - win_y, (yy + scroll_y) & 255)
        background_map = 0x9c00 if lcdc & 0x08 else 0x9800
        window_map = 0x9c00 if lcdc & 0x40 else 0x9800
        maps = np.where(window, window_map, background_map)
        # Read the native 2048 map bytes once, then index them. Reading one
        # byte for every screen pixel would make consecutive-frame QA costly.
        addresses = maps - 0x9800 + (by // 8) * 32 + bx // 8
        # PyBoy checks the exclusive slice endpoint against the VRAM bank;
        # append 9FFF separately rather than asking for its A000 endpoint.
        tiles = np.asarray(list(self.p.memory[0, 0x9800:0x9fff]) +
                           [self.p.memory[0, 0x9fff]], dtype=np.uint8)[addresses]
        attrs = np.asarray(list(self.p.memory[1, 0x9800:0x9fff]) +
                           [self.p.memory[1, 0x9fff]], dtype=np.uint8)[addresses]
        palettes = self.palette()
        local_x = np.where(attrs & 0x20, 7 - bx % 8, bx % 8)
        local_y = np.where(attrs & 0x40, 7 - by % 8, by % 8)
        native_ink = np.zeros((144, 160), dtype=np.uint8)
        pattern_base = 0x8000 if lcdc & 0x10 else 0x8800
        pattern_number = tiles if lcdc & 0x10 else (tiles.astype(np.uint16) + 128) % 256
        bits = np.arange(7, -1, -1, dtype=np.uint8)
        for bank in (0, 1):
            packed = np.asarray(self.p.memory[bank, pattern_base:pattern_base + 4096],
                                dtype=np.uint8).reshape(256, 8, 2)
            decoded = ((packed[:, :, :1] >> bits & 1) |
                       ((packed[:, :, 1:] >> bits & 1) << 1))
            cells = ((attrs >> 3) & 1) == bank
            native_ink[cells] = decoded[pattern_number[cells], local_y[cells], local_x[cells]]
        result = palettes[attrs & 7, native_ink]
        self.background_native_state = {'palettes': palettes, 'attributes': attrs & 7,
                                        'indices': native_ink}
        return result, {'lcdc': lcdc, 'scroll': [scroll_x, scroll_y],
                        'window_origin': [win_x, win_y], 'window_visible': bool(window.any()),
                        'bank1_bg_pixels': int(np.count_nonzero(attrs & 8))}

    @contextmanager
    def transition(self, label):
        """Audit every complete PPU frame; keep publication/fade frames explicit."""
        assert self.transition_active is None, 'Nested transition observers are not supported'
        self.transition_active = label
        self.transition_frames = []
        self.transition_previous = None
        start = self.p.frame_count
        record = {'label': label, 'start_frame': start, 'frames': []}
        self.transition_checks.append(record)
        try:
            yield
        finally:
            self.transition_active = None
            record['end_frame'] = self.p.frame_count
            record['consecutive_frames_observed'] = len(record['frames'])
            if self.transition_frames:
                native = self.transition_frames
                native[0].save(self.folder / (label + '_all_native_frames.gif'),
                               save_all=True, append_images=native[1:], duration=17, loop=0)
            self.transition_frames = []
            self.transition_previous = None

    def observe_transition_frame(self):
        label = self.transition_active
        image = self.p.screen.image.copy()
        self.transition_frames.append(image)
        row = {'frame': self.p.frame_count, 'lcd_enabled': bool(self.p.memory[0xff40] & 0x80),
               'palette_publication_pending': self.read('hCGBPalUpdate')[0],
               'bg_map_mode': self.read('hBGMapMode')[0], 'vbk': self.p.memory[0xff4f] & 1,
               'requested_1bpp_tiles': self.read('wRequested1bppSize')[0],
               'requested_2bpp_tiles': self.read('wRequested2bppSize')[0]}
        self.transition_checks[-1]['frames'].append(row)
        lcd_events = [event for event in self.lcd_publications
                      if self.p.frame_count - 1 <= event['frame'] <= self.p.frame_count]
        startup_events = [event for event in self.lcd_publications
                          if self.p.frame_count - 2 <= event['frame'] <= self.p.frame_count and
                          not event['old_lcdc'] & 0x80 and event['new_lcdc'] & 0x80]
        if lcd_events:
            row['observed_native_lcd_publications'] = lcd_events
        map_dma_events = [event for event in self.native_dma_publications
                          if self.p.frame_count - 1 <= event['frame'] <= self.p.frame_count and
                          event['destination'] is not None and event['destination'] >= 0x9800 and
                          event['length_register'] & 0x80]
        if map_dma_events:
            row['observed_native_hblank_map_dma'] = map_dma_events
        if not row['lcd_enabled']:
            row['pixel_check'] = 'native LCD-off transition'
            self.transition_previous = None
            return
        expected, registers = self.background()
        mask = self.object_mask()
        actual = np.asarray(image.convert('RGB'), dtype=np.uint8) >> 3
        publishing = bool(row['palette_publication_pending'] or
                          (not row['bg_map_mode'] and
                           (row['vbk'] or row['requested_1bpp_tiles'] or row['requested_2bpp_tiles'])))
        current = (expected, mask, registers, publishing,
                   self.background_native_state)
        candidates = [current[:4] + ('current VRAM/current palette',)]
        if self.transition_previous is not None:
            previous = self.transition_previous
            previous_state, current_state = previous[4], current[4]
            candidates.append((previous[0], mask | previous[1], previous[2], previous[3],
                               'previous VRAM/previous palette'))
            # Palette DMA and picture DMA can straddle the PyBoy frame boundary
            # independently. These are whole coherent native snapshots, never
            # a per-pixel selection that could hide a corrupted raster.
            candidates.append((previous_state['palettes'][current_state['attributes'],
                                                           current_state['indices']],
                               mask, registers, previous[3], 'current VRAM/previous palette'))
            candidates.append((current_state['palettes'][previous_state['attributes'],
                                                          previous_state['indices']],
                               mask | previous[1], previous[2], current[3],
                               'previous VRAM/current palette'))
        for index, published in enumerate(self.applied_palette_history):
            last = self.applied_palette_history[-1]
            latest_still_applied = index == len(self.applied_palette_history) - 1
            immediate_previous_at_boundary = (index == len(self.applied_palette_history) - 2 and
                                              last['frame'] >= self.p.frame_count - 1)
            if not (latest_still_applied or immediate_previous_at_boundary or
                    self.p.frame_count - 2 <= published['frame'] <= self.p.frame_count):
                continue
            for snapshot in (current, self.transition_previous):
                if snapshot is None:
                    continue
                state = snapshot[4]
                candidates.append((published['palette'][state['attributes'], state['indices']],
                                   mask | snapshot[1], snapshot[2], False,
                                   'observed ForceUpdateCGBPals at native frame ' + str(published['frame'])))
        trials = []
        for background, ignored, candidate_registers, publication, combination in candidates:
            visible = ~ignored
            wrong = np.any(actual != background, axis=-1) & visible
            trials.append((int(wrong.sum()), int(visible.sum()), wrong, candidate_registers, combination))
        # Do not claim a pixel proof while the palette buffer intentionally
        # precedes native publication, or for the first unseen prior frame.
        if self.transition_previous is None:
            row['pixel_check'] = 'native publication boundary retained for review'
        else:
            count, checked, mismatch, chosen_registers, combination = min(trials, key=lambda item: item[0])
            row.update({'pixel_check': 'actual PPU vs adjacent native hardware snapshots',
                        'matched_rgb555_pixels': checked - count, 'mismatched_pixels': count,
                        'native_snapshot_combination': combination,
                        **chosen_registers})
            if count and lcd_events:
                # LCD was physically stopped/restarted inside this tick. The
                # exposed PyBoy framebuffer can contain the tail of the old
                # raster and head of the new one, not a complete LCD frame.
                row['pixel_check'] = 'observed LCD restart; partial raster retained for review'
                self.transition_previous = current
                return
            if count and startup_events and np.all(actual == 31):
                # Re-enabling the LCD leaves its first completed raster blank.
                # A tick spanning the OFF->ON event can expose that white
                # startup frame two tick boundaries later. This exception is
                # limited to genuine observed restart and uniform white ink;
                # a coloured mixed map or later stable frame remains strict.
                row['pixel_check'] = 'observed LCD startup blank frame retained for review'
                row['observed_native_lcd_startup'] = startup_events
                self.transition_previous = current
                return
            if count and any(candidate[3] for candidate in candidates):
                # The native scene builder has suspended BG publication, or
                # is copying tiles/palettes during this raster. A snapshot of
                # its final memory does not reconstruct mid-line writes. Keep
                # the whole framebuffer and explicit count for visual review;
                # do not call these pixels verified or treat them as a stable
                # rendering failure. Every settled surface remains strict.
                row['pixel_check'] = 'native publication in progress; whole framebuffer retained for review'
                self.transition_previous = current
                return
            if count:
                image.save(self.folder / (label + '_transition_first_failure.png'))
                Image.fromarray(np.uint8(mismatch) * 255).save(
                    self.folder / (label + '_transition_first_failure_mask.png'))
                Image.fromarray(expected * 8).save(
                    self.folder / (label + '_transition_current_native_snapshot.png'))
                if self.transition_previous is not None:
                    Image.fromarray(self.transition_previous[0] * 8).save(
                        self.folder / (label + '_transition_previous_native_snapshot.png'))
            assert count == 0, (label, 'Consecutive transition PPU differs from native snapshots',
                                self.p.frame_count, count, row)
        self.transition_previous = current

    def object_mask(self):
        """Exclude actual opaque OBJ ink, with LCD-native8/16 height and mirrors."""
        mask = np.zeros((144, 160), dtype=bool)
        lcdc = self.p.memory[0xff40]
        if not lcdc & 2:
            return mask
        height = 16 if lcdc & 4 else 8
        oam = list(self.p.memory[0xfe00:0xfea0])
        for index in range(0, 160, 4):
            y, x, tile, attr = oam[index:index + 4]
            if not x or not y:
                continue
            x -= 8; y -= 16
            if height == 16:
                tile &= 0xfe
            parts = []
            for offset in range(height // 8):
                address = 0x8000 + (tile + offset) * 16
                parts.append(decode_tile(self.p.memory[attr >> 3 & 1, address:address + 16]))
            pixels = np.vstack(parts)
            if attr & 0x20:
                pixels = pixels[:, ::-1]
            if attr & 0x40:
                pixels = pixels[::-1]
            left, top, right, bottom = max(0, x), max(0, y), min(160, x + 8), min(144, y + height)
            if left < right and top < bottom:
                mask[top:bottom, left:right] |= pixels[top - y:bottom - y, left - x:right - x] != 0
        return mask

    def surface(self, label):
        """Three consecutive complete stationary frames, including any tile animation."""
        self.p.tick(60, True)
        checks = []
        previous_background = None
        previous_mask = None
        frames = []
        for _ in range(4):
            self.p.tick(1, True)
            expected, registers = self.background()
            mask = self.object_mask()
            actual = np.asarray(self.p.screen.image.convert('RGB'), dtype=np.uint8) >> 3
            # A PyBoy call ends after the next DMA; its completed LCD frame can
            # legitimately use the previous frame's tile animation/OAM. Both
            # candidates are observed native data, without forced CPU state.
            candidates = [(expected, mask)]
            if previous_background is not None:
                candidates.append((previous_background, mask | previous_mask))
            trials = []
            for background, ignore in candidates:
                visible = ~ignore
                mismatch = np.any(actual != background, axis=-1) & visible
                trials.append((int(mismatch.sum()), int(visible.sum()), mismatch))
            count, checked, mismatch = min(trials, key=lambda row: row[0])
            if previous_background is not None:
                if count:
                    self.capture(label + '_background_first_failure')
                    Image.fromarray(np.uint8(mismatch) * 255).save(
                        self.folder / (label + '_background_first_failure_mask.png'))
                assert checked >= 16000, (label, 'Not enough genuine background pixels', checked)
                assert count == 0, (label, 'Actual PPU background differs from VRAM/palette', count, registers)
                checks.append({'frame': self.p.frame_count, 'matched_rgb555_pixels': checked,
                               'mismatched_pixels': count, **registers})
                frames.append(self.p.screen.image.copy())
            previous_background, previous_mask = expected, mask
        self.capture(label)
        self.bg_checks.append({'label': label, 'consecutive_native_frames': checks})
        frames[0].resize((640, 576), Image.Resampling.NEAREST).save(
            self.folder / (label + '_consecutive_native.gif'), save_all=True,
            append_images=[frame.resize((640, 576), Image.Resampling.NEAREST) for frame in frames[1:]],
            duration=17, loop=0)
        return checks

    def review_class_choices(self):
        if self.choice_reviewed:
            return
        self.choice_reviewed = True
        # Start from the actual chosen cursor; return there before accepting.
        for expected_index in ((self.class_index + 1) % 3, (self.class_index + 2) % 3, self.class_index):
            with self.transition('class_transition_' + CLASSES[expected_index]):
                self.press('down', 40)
                assert self.read('wMenuCursorY') == [expected_index]
                self.surface('class_choice_' + CLASSES[expected_index])
            palette = self.palette().tolist()
            actual = np.asarray(self.p.screen.image.convert('RGB'), dtype=np.uint8) >> 3
            self.theme_checks.append({'class': CLASSES[expected_index], 'cursor': expected_index,
                                      'palette_bytes_sha256': sha(bytes(self.read('wBGPals2', 64))),
                                      'palette_rgb555': palette,
                                      'actual_background_corner': actual[16, 16].tolist()})
        assert len({item['palette_bytes_sha256'] for item in self.theme_checks}) == 3, 'Class themes identical'

    def menu(self, index, label):
        self.press('start')
        for _ in range(12):
            if self.read('wMenuCursorPosition') == [1]:
                break
            self.press('up', 30)
        for _ in range(index - 1):
            self.press('down', 30)
        assert self.read('wMenuCursorPosition') == [index], (label, 'Unexpected menu index')
        with self.transition(label + '_opening'):
            self.press('a', 90)
            self.surface(label)
        encoding = routes.text_encoding()
        tilemap = self.read('wTilemap', 360)
        if index == 1:
            basic = ('MACE STRIKE', 'MELEE STRIKE', 'WAND STRIKE')[self.class_index]
            weapon = ('CRUDE MACE', 'CRUDE AXE', 'WORN WAND')[self.class_index]
            for row, column, wanted in ((3, 10, self.slug.upper()), (11, 2, weapon), (12, 2, basic)):
                offset = row * 20 + column
                expected = [encoding[character] for character in wanted]
                assert tilemap[offset:offset + len(expected)] == expected, (label, 'wrong class/weapon/basic label', wanted)
            self.interface_identity_checks.append({'label': label, 'class': self.slug,
                                                   'native_weapon_label': weapon, 'native_basic_label': basic})
        elif index == 2:
            weapon = ('MACE', 'AXE', 'WAND')[self.class_index]
            assert tilemap[8 * 20 + 2:8 * 20 + 2 + len(weapon)] == [encoding[c] for c in weapon]
            if self.class_index:
                native = (ROOT / 'gfx/peon_classes_v028/item_icons' /
                          ('axe.2bpp' if self.class_index == 1 else 'wand.2bpp')).read_bytes()
                assert bytes(self.p.memory[0, 0x9400:0x9440]) == native, (label, 'wrong backpack class weapon icon')
                attrs = self.read('wAttrmap', 360)
                assert [attrs[row * 20 + column] for row in (6, 7) for column in (2, 3)] == [6] * 4
            self.interface_identity_checks.append({'label': label, 'native_backpack_weapon_label': weapon,
                                                   'class_weapon_icon_verified': bool(self.class_index)})

    def warm_menus(self):
        self.surface('den_after_colored_class_name_entry')
        for cycle in range(2):
            self.menu(1, 'character_warm_' + str(cycle))
            with self.transition('character_return_' + str(cycle)):
                self.press('b'); self.press('b')
                self.surface('den_after_character_' + str(cycle))
            self.menu(2, 'bags_warm_' + str(cycle))
            with self.transition('inventory_opening_' + str(cycle)):
                self.press('a', 60); self.ready('inventory')
                self.surface('inventory_warm_' + str(cycle))
            with self.transition('inventory_return_' + str(cycle)):
                self.press('b'); self.press('b'); self.press('b')
                self.surface('den_after_bags_inventory_' + str(cycle))
            with self.transition('map_opening_' + str(cycle)):
                self.press('select', 90)
                self.surface('locked_map_warm_' + str(cycle))
            with self.transition('map_return_' + str(cycle)):
                self.press('b', 90)
                self.surface('den_after_map_' + str(cycle))

    def fight_and_recover(self):
        self.talk_plain((10, 10), 'up')
        assert self.event('EVENT_PEON_QUEST_ACCEPTED')
        self.navigate((18, 13)); self.press('up', 30); self.press('a', 60)
        self.wait(lambda: self.phase == 'battle', buttons=True)
        self.surface('battle_before_any_action')
        # Opening/closing actual combat Bags must preserve all portraits,
        # fonts, private companions, class colors and HP UI together.
        with self.transition('battle_bags_opening'):
            self.open_bag_item(18)
            self.surface('battle_inventory_without_consuming_item')
        with self.transition('battle_bags_cancel_return'):
            self.press('b'); self.press('b')
            self.ready('battle')
            self.surface('battle_after_inventory_cancel')
        self.until_world(choose_bolt=False)
        assert self.event('EVENT_PEON_QUEST_DONE') and self.read('wBattleResult') == [0]
        self.surface('den_after_battle_victory')
        with self.transition('inn_door_entry'):
            self.navigate((17, 5), expected_map=23)
            self.surface('inn_after_battle_before_rest')
        heals = self.heal_calls
        self.talk((6, 5), 'up', 'actual_inn_healer')
        assert self.heal_calls == heals + 1
        assert self.read('wPartyMon1HP', 2) == self.read('wPartyMon1MaxHP', 2)
        self.surface('inn_after_healer')
        self.menu(1, 'inn_character_warm')
        with self.transition('inn_character_return'):
            self.press('b'); self.press('b')
            self.surface('inn_after_character')
        with self.transition('inn_door_exit'):
            self.navigate((5, 7), expected_map=14)
            self.surface('den_after_inn_exit')
        cold = self.cold_save()
        self.surface('den_after_actual_battery_continue')
        return {'actual_bags_cancel_without_item_use': True, 'ordinary_basic_melee_victory': True,
                'actual_inn_heal_calls': 1, 'actual_building_door_reciprocal_return': True,
                'actual_32k_battery_cold_continue': cold}


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-sha', required=True)
    parser.add_argument('--class', dest='class_name', choices=CLASSES)
    parser.add_argument('--rom', type=Path, default=ROOT / 'pokecrystal.gbc')
    parser.add_argument('--symbols', type=Path, default=ROOT / 'pokecrystal.sym')
    parser.add_argument('--output', type=Path, default=OUT,
                        help='A new evidence folder within polish_v028/integration')
    args = parser.parse_args()
    requested = args.output.resolve()
    assert requested.is_relative_to(OUT.resolve()), 'Evidence must stay in the integration output tree'
    OUT = requested
    logging.disable(logging.CRITICAL)
    raw = args.rom.read_bytes()
    assert sha(raw) == args.expected_sha
    OUT.mkdir(parents=True, exist_ok=True)
    symbols = symbols_from(args.symbols)
    report = {'passed': False, 'rom_sha256': sha(raw),
              'symbols_sha256': sha(args.symbols.read_bytes()),
              'ordinary_buttons_only': True, 'ram_writes': False, 'savestates_loaded': False,
              'user_battery_files_opened': False, 'classes': {}}
    with redirect_previous_outputs(), tempfile.TemporaryDirectory(prefix='peon-v028-integration-') as temp:
        for index, name in enumerate(CLASSES):
            if args.class_name and name != args.class_name:
                continue
            rom = Path(temp) / (name + '.gbc')
            rom.write_bytes(raw)
            session = Session(rom, symbols, index)
            try:
                session.fresh_class()
                assert 'opening_sleeping_at_palm_prompt' in session.capture_records
                opening_source = (ROOT / 'maps/PeonOpening.blk').read_bytes()
                bank, address = symbols['PeonOpening_Blocks']
                offset = bank * 0x4000 + (address & 0x3fff)
                assert raw[offset:offset + len(opening_source)] == opening_source
                assert opening_source[28] == 28, 'Opening lost the adjacent authored palm'
                session.warm_menus()
                recovery = session.fight_and_recover()
                assert not session.pet_errors, session.pet_errors
                report['classes'][name] = {'passed': True, 'class_choice_themes': session.theme_checks,
                                          'complete_native_bg_surface': session.bg_checks,
                                          'complete_consecutive_transition_frames': session.transition_checks,
                                          'observed_native_palette_publications': session.applied_palette_records,
                                          'native_interface_class_and_weapon_labels': session.interface_identity_checks,
                                          'combined_routes': recovery,
                                          'ordinary_opening_prompt_with_authored_adjacent_palm': True,
                                          'captures': session.capture_records}
            except BaseException as error:
                session.capture('integration_first_failure')
                failure = {'passed': False, 'rom_sha256': sha(raw), 'class': name,
                           'error': repr(error), 'map': session.map(), 'xy': session.position(),
                           'phase': session.phase, 'actual_pc': hex(session.p.register_file.PC),
                           'actual_rom_bank': session.read('hROMBank')[0],
                           'battle_mode': session.read('wBattleMode')[0],
                           'lcd_registers': {'lcdc': session.p.memory[0xff40],
                                             'ly': session.p.memory[0xff44],
                                             'vbk': session.p.memory[0xff4f] & 1,
                                             'bg_mode': session.read('hBGMapMode')[0]},
                           'observed_lcd_publications': session.lcd_publications[-12:],
                           'observed_dma_publications': session.native_dma_publications[-12:],
                           'observed_palette_publications': session.applied_palette_records[-12:]}
                (session.folder / 'first_failure.json').write_text(json.dumps(failure, indent=2) + '\n')
                raise
            finally:
                session.p.stop(save=False)
    assert sha(args.rom.read_bytes()) == report['rom_sha256'], 'ROM changed during QA'
    assert sha(args.symbols.read_bytes()) == report['symbols_sha256'], 'Symbols changed during QA'
    report['passed'] = True
    filename = 'validation.json' if not args.class_name else 'validation_' + args.class_name + '.json'
    (OUT / filename).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': True, 'rom_sha256': report['rom_sha256'],
                      'classes': list(report['classes'])}, indent=2))


if __name__ == '__main__':
    main()
