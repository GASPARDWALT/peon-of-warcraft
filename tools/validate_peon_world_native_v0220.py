#!/usr/bin/env python3
"""Observe mixed native24/32 world actors with real controller input only.

Fresh private ROMs, read-only hooks and native SAVE/Continue are used. Source
packets, descriptors, VRAM, masks, relative templates and complete OAM bodies
are checked independently of the artwork's declared size. Historical tests
are imported for their controller routes and remain unchanged.
"""
from pathlib import Path
import argparse
import hashlib
import json
import logging
import re
import shutil
import tempfile

from PIL import Image

from validate_peon_earth_stone_v0212 import CLASSES
from validate_peon_exit_title import symbols
from validate_peon_merchants_v0217 import check_world_palettes
import validate_peon_world_restore_v0219 as restoration
from validate_peon_masters_sleeping_v0219 import MasterSessionV0219, MASTER_ATTRS

ROOT = Path(__file__).resolve().parents[1]
SLOT_TILES = 16
SLOT_BYTES = SLOT_TILES * 16
OBJECTS = 13


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rom_bytes(rom, bank, address, length):
    offset = address if not bank else bank * 0x4000 + address - 0x4000
    return rom[offset:offset + length]


def decode_tile(data):
    return [[((data[y * 2] >> (7 - x)) & 1)
             | (((data[y * 2 + 1] >> (7 - x)) & 1) << 1)
             for x in range(8)] for y in range(8)]


def canonical_packets(rom, sym, manifest_path, graphics_path, allow_partial=False, pilot_shaman_only=False):
    manifest = json.loads(manifest_path.read_text())
    sprite_source = (ROOT / 'constants/sprite_constants.asm').read_text().split('DEF NUM_OVERWORLD_SPRITES', 1)[0]
    sprite_ids = {name: index for index, name in enumerate(re.findall(r'^\s*const (SPRITE_\w+)', sprite_source, re.M))}
    selected_graphics = graphics_path
    if pilot_shaman_only:
        assert allow_partial, 'A one-role pilot must be explicitly partial'
        # This frozen ROM preceded later NPC/troll imports. Select the exact
        # retained v19 packets independently of mutable v20 files, and only
        # the compiled new Shaman packet from the current native32 import.
        shaman = manifest['roles']['shaman']
        manifest = json.loads((ROOT / 'gfx/world_readability_v0219/manifest.json').read_text())
        manifest['roles']['shaman'] = shaman
        manifest['status'] = 'PARTIAL'
        manifest['missing_native32_roles'] = ['pilot_only_shaman_selected']
        legacy_gaits = ('SPRITE_CHRIS', 'SPRITE_KRIS', 'SPRITE_LASS', 'SPRITE_ROCKER',
                        'SPRITE_COOLTRAINER_M', 'SPRITE_COOLTRAINER_F')
        manifest['walk_flags'] = {'flags': [int(i in {sprite_ids[name] for name in legacy_gaits}) for i in range(256)]}
        selected_graphics = ROOT / 'gfx/world_readability_v0219/graphics.asm'
    palettes = manifest['effective_world_palettes_rgb555']
    if not allow_partial:
        assert manifest.get('status') == 'PASS', ('Native32 import is incomplete', manifest.get('status'))
        assert not manifest.get('missing_native32_roles'), manifest.get('missing_native32_roles')
    paths, current = {}, None
    for line in selected_graphics.read_text().splitlines():
        label = re.fullmatch(r'\s*([A-Za-z_][A-Za-z0-9_]*)::?\s*(?:;.*)?', line)
        if label:
            current = label[1]
        incbin = re.fullmatch(r'\s*INCBIN\s+"([^"]+)"\s*(?:;.*)?', line)
        if incbin:
            assert current and current not in paths, ('Ambiguous packet import', line)
            paths[current] = ROOT / incbin[1]
    if pilot_shaman_only:
        for suffix, filename in (('', 'overworld.bin'), ('Masks', 'masks.bin'), ('Attrs', 'attrs.bin')):
            paths[manifest['roles']['shaman']['label'] + suffix] = ROOT / 'gfx/world_native_v0220/shaman' / filename
    assert paths, ('No compiled packets', graphics_path)
    by_address, roles, native32_roles, compiled_native32_roles = {}, {}, [], []
    for role, record in manifest['roles'].items():
        label = record.get('label')
        exported = record.get('exported_in_rom', True)
        packet_path = paths[label] if exported else ROOT / record['output_packet']
        mask_path = paths[record.get('masks_label', label + 'Masks')] if exported else packet_path.parent / 'masks.bin'
        attrs_path = paths[record.get('attrs_label', label + 'Attrs')] if exported else packet_path.parent / 'attrs.bin'
        size = record.get('frame_size', record.get('dimensions_after', [24, 24])[0])
        assert size in (24, 32), (role, size)
        columns, tiles = size // 8, (size // 8) ** 2
        frame_bytes = tiles * 16
        packet = packet_path.read_bytes()
        masks = mask_path.read_bytes()
        attrs = attrs_path.read_bytes()
        assert (len(packet), len(masks), len(attrs)) == (12 * frame_bytes, 24, 12 * tiles), (role, size)
        assert all(value < 8 for value in attrs), ('Not a source OBJ palette', role)
        if exported:
            for name, data in ((label, packet), (label + 'Masks', masks), (label + 'Attrs', attrs)):
                assert rom_bytes(rom, *sym[name], len(data)) == data, ('Compiled source differs', role, name)
            bank, address = sym[label]
            assert address % 16 == 0 and address + len(packet) <= 0x8000
            mask_bank, mask_address = sym[label + 'Masks']
            assert sym[label + 'Attrs'] == (mask_bank, mask_address + 24), (
                'Native attributes must directly follow masks in their own bank', role)
            assert 0x4000 <= mask_address and mask_address + len(masks) + len(attrs) <= 0x8000, (
                'Native metadata crosses its ROMX bank', role)
        if record.get('output_sha256'):
            assert record['output_sha256'] == sha(packet), ('Stale packet manifest', role)
        image_path = packet_path.parent / 'overworld.png'
        image = Image.open(image_path).convert('RGBA')
        assert image.size == (size * 4, size * 3), (role, image.size)
        frames = []
        for frame in range(12):
            source = packet[frame * frame_bytes:(frame + 1) * frame_bytes]
            mask = int.from_bytes(masks[frame * 2:frame * 2 + 2], 'little')
            expected_mask = sum(1 << tile for tile in range(tiles)
                                if any(source[tile * 16:(tile + 1) * 16]))
            assert mask == expected_mask, ('Mask differs from opaque native tiles', role, frame)
            alpha = image.crop((frame // 3 * size, frame % 3 * size,
                                (frame // 3 + 1) * size, (frame % 3 + 1) * size)).getchannel('A')
            for tile in range(tiles):
                pixels = decode_tile(source[tile * 16:(tile + 1) * 16])
                for y in range(8):
                    for x in range(8):
                        assert bool(pixels[y][x]) == bool(alpha.getpixel((tile % columns * 8 + x, tile // columns * 8 + y))), (
                            'Native transparency differs from individual body strip', role, frame, tile, x, y)
                        if pixels[y][x]:
                            pixel = image.getpixel((frame // 3 * size + tile % columns * 8 + x,
                                                    frame % 3 * size + tile // columns * 8 + y))
                            expected_rgb555 = palettes[attrs[frame * tiles + tile]][pixels[y][x]]
                            assert tuple(value >> 3 for value in pixel[:3]) == tuple(expected_rgb555), (
                                'Source strip RGB differs from native packet/palette', role, frame, tile, x, y)
            frames.append({'frame': frame, 'mask': mask, 'oam_cells': mask.bit_count(), 'packet_sha256': sha(source)})
        item = {'role': role, 'label': label, 'size': size, 'tiles': tiles,
                'frame_bytes': frame_bytes, 'packet': packet, 'masks': masks,
                'attrs': attrs, 'path': str(packet_path.relative_to(ROOT)),
                'image': image, 'record': record}
        if exported:
            assert (bank, address) not in by_address
            by_address[bank, address] = item
        roles[role] = {'label': label, 'frame_size': size, 'tiles_per_frame': tiles,
                       'frame_bytes': frame_bytes, 'exported_in_rom': exported,
                       'ROM_exact': True if exported else None,
                       'packet_sha256': sha(packet), 'source_strip': str(image_path.relative_to(ROOT)),
                       'all_frame_alpha_and_RGB555_exact': True, 'frames': frames,
                       'distinct_pose_packets_per_direction': [len({frames[i + pose]['packet_sha256'] for pose in range(3)}) for i in range(0, 12, 3)]}
        if size == 32:
            native32_roles.append(role)
            if exported:
                compiled_native32_roles.append(role)
    assert roles, 'No runtime actor packets were inspected'
    if not allow_partial:
        assert len(native32_roles) == 19, ('Expected nineteen complete native32 sources', native32_roles)
        assert len(compiled_native32_roles) == 15, ('Expected fifteen bound native32 families', compiled_native32_roles)
    bindings = manifest['runtime_bindings']
    bindings_bank, bindings_address = sym['PeonLargeWorldBindingsV0215']
    pointers = [0] * 256
    for ordinal, binding in enumerate(bindings):
        role = binding['role']
        item = roles[role]
        source_bank, source_address = sym[item['label']]
        mask_bank, mask_address = sym[item['label'] + 'Masks']
        record_address = bindings_address + ordinal * 8
        actual = rom_bytes(rom, bindings_bank, record_address, 8)
        sprite = sprite_ids[binding['sprite']]
        descriptor_palette = manifest['roles'][role].get('descriptor_palette_byte', binding['palette_index'])
        expected = bytes((sprite, descriptor_palette, source_bank)) + source_address.to_bytes(2, 'little') + bytes((mask_bank,)) + mask_address.to_bytes(2, 'little')
        assert actual == expected, ('Compiled ordinary descriptor differs', ordinal, role)
        assert not pointers[sprite], ('Duplicate ordinary descriptor', sprite)
        pointers[sprite] = record_address
    assert rom_bytes(rom, bindings_bank, bindings_address + len(bindings) * 8, 1) == b'\xff'
    assert sym['PeonLargeWorldDescriptorPointersV0220'][0] == bindings_bank
    assert rom_bytes(rom, *sym['PeonLargeWorldDescriptorPointersV0220'], 512) == b''.join(value.to_bytes(2, 'little') for value in pointers)
    hero_bank, hero_address = sym['PeonLargeWorldHeroBindingsV0215']
    for ordinal, role in enumerate(('base', 'shaman', 'warrior', 'warlock')):
        label = roles[role]['label']
        source_bank, source_address = sym[label]
        mask_bank, mask_address = sym[label + 'Masks']
        descriptor_palette = manifest['roles'][role].get('descriptor_palette_byte', manifest['roles'][role]['palette_index'])
        expected = bytes((1, descriptor_palette, source_bank)) + source_address.to_bytes(2, 'little') + bytes((mask_bank,)) + mask_address.to_bytes(2, 'little')
        assert rom_bytes(rom, hero_bank, hero_address + ordinal * 8, 8) == expected, ('Compiled class descriptor differs', role)
    flags = rom_bytes(rom, *sym['PeonLargeWorldWalkFlagsV0220'], 256)
    assert set(flags) <= {0, 1}
    if isinstance(manifest.get('walk_flags'), dict) and 'flags' in manifest['walk_flags']:
        assert flags == bytes(manifest['walk_flags']['flags']), 'Compiled NPC gait flags differ'
    return {'manifest': manifest, 'by_address': by_address,
            'report': {'status': 'PASS', 'manifest': str(manifest_path.relative_to(ROOT)),
                       'manifest_sha256': sha(manifest_path.read_bytes()),
                       'graphics_sha256': sha(graphics_path.read_bytes()),
                       'native32_roles': native32_roles, 'native24_roles': sorted(set(roles) - set(native32_roles)),
                       'compiled_native32_roles': compiled_native32_roles,
                       'compiled_role_count': len(by_address),
                       'partial_import_explicitly_allowed': allow_partial,
                       'frozen_shaman_only_pilot': pilot_shaman_only,
                       'retained_packet_graphics': str(selected_graphics.relative_to(ROOT)),
                       'ordinary_and_hero_descriptors_exact': True, 'all_256_descriptor_pointers_exact': True,
                       'compiled_walk_flags_boolean_and_manifest_exact': True, 'roles': roles}}


class WorldNativeSessionV0220(restoration.RestoredWorldSession):
    contract = None
    marker_offset_pixels = 16
    enter_lodge = MasterSessionV0219.enter_lodge
    leave_lodge = MasterSessionV0219.leave_lodge
    talk_master = MasterSessionV0219.talk_master
    cold_continue_in_lodge = MasterSessionV0219.cold_continue_in_lodge
    check_lodge_palettes = MasterSessionV0219.check_lodge_palettes
    check_world_warm_palette = MasterSessionV0219.check_world_warm_palette
    native_background = MasterSessionV0219.native_background
    same_native_background = MasterSessionV0219.same_native_background

    def __init__(self, *args):
        self.runtime_roles = {}
        self.native_class_panel_seen = False
        self.lodge_background_reference = None
        super().__init__(*args)

    def open(self):
        super().open()
        self.native_class_panel_seen = False

    def drawing_class(self, context):
        super().drawing_class(context)
        self.native_class_panel_seen = True

    def press(self, key, frames=90):
        if ("PeonInitLargeWorldSpritesV0215" in self.sym and key == "a"
                and self.map() == 13 and self.native_class_panel_seen
                and not self.class_ready):
            # The native panel can still be publishing after it is drawn;
            # wait for its real input loop before sending another confirm.
            self.p.tick(frames, True)
            return
        if ("PeonInitLargeWorldSpritesV0215" in self.sym and key == "a"
                and self.map() == 13 and not self.native_class_panel_seen):
            # Stop a dialogue-advance press as the actual class panel starts
            # drawing. A later menu requires its own deliberate confirm.
            self.p.button(key, delay=4)
            for elapsed in range(1, frames + 1):
                self.p.tick(1, True)
                if self.native_class_panel_seen:
                    self.p.button_release(key)
                    self.p.tick(max(frames - elapsed, 1), True)
                    return
            return
        if ("PeonInitLargeWorldSpritesV0215" in self.sym
                and self.class_ready and not self.naming and self.map() == 13
                and key in ("up", "down")):
            old = self.read("wMenuCursorY")
            self.p.button_press(key)
            elapsed = 0
            for elapsed in range(1, 33):
                self.p.tick(1, True)
                if self.read("wMenuCursorY") != old:
                    break
            self.p.button_release(key)
            self.p.tick(max(frames - elapsed, 1), True)
            return
        if ("PeonInitLargeWorldSpritesV0215" in self.sym
                and key in ("up", "down", "left", "right")
                and self.presentation == "world"
                and self.read("wScriptMode") == [0]):
            # Hold until the first native movement/turn acknowledges the
            # D-pad, then release before it can buffer another tile step.
            # This respects a slower renderer without long held movement.
            start = self.position()
            facing = self.read("wObjectStructs", 14)[13]
            self.p.button_press(key)
            elapsed = 0
            for elapsed in range(1, 13):
                self.p.tick(1, True)
                if (self.position() != start or self.read("wPlayerStepFlags")[0]
                        or self.read("wObjectStructs", 14)[13] != facing):
                    break
            self.p.button_release(key)
            self.p.tick(max(frames - elapsed, 1), True)
            return
        if ("PeonInitLargeWorldSpritesV0215" in self.sym
                and key in ("a", "start", "select")
                and self.presentation == "world"
                and self.read("wScriptMode") == [0]):
            self.p.button_press(key)
            elapsed = 0
            for elapsed in range(1, 17):
                self.p.tick(1, True)
                if self.read("wScriptMode") != [0] or self.presentation != "world":
                    break
            self.p.button_release(key)
            self.p.tick(max(frames - elapsed, 1), True)
            return
        super().press(key, frames)

    def live_actors(self, name):
        actors = super().live_actors(name)
        records = self.read("wObjectStructs", 13 * 40)
        follower_slots = {records[i * 40 + 1] for i in range(1, 13)
                          if records[i * 40] == 0x68}
        # Native IsNPCAtCoord explicitly ignores the friendly Imp. Its
        # transient slot15 replaces a map template; the static-source route
        # helper must not reinterpret that follower as a blocking cook.
        return [actor for actor in actors if actor["index"] not in follower_slots]

    def scene(self, label=None, strict_lcd=False):
        assert not self.renderer_hook_errors, self.renderer_hook_errors
        check_world_palettes(self)
        raw = list(self.p.memory[0xfe00:0xfea0])
        oam = [tuple(raw[i:i + 4]) for i in range(0, 160, 4)
               if 8 < raw[i] < 160 and 0 < raw[i + 1] < 168]
        occupancy = [sum(y <= row + 16 < y + 8 for y, x, tile, flags in oam) for row in range(144)]
        assert len(oam) <= 40 and max(occupancy, default=0) <= 10
        keys = self.read('wPeonLargeWorldCacheIDsV0215', OBJECTS)
        frames = self.read('wPeonLargeWorldCacheFramesV0215', OBJECTS)
        groups = {}
        for cell in oam:
            if cell[3] & 8 and cell[2] < OBJECTS * SLOT_TILES:
                groups.setdefault(cell[2] // SLOT_TILES, []).append(cell)
        assert 0 in groups, ('Hero disappeared', self.map(), self.position(), oam)
        reports = {}
        lcd = self.p.screen.image.convert('RGB')
        for index, cells in groups.items():
            key, frame = keys[index], frames[index]
            assert key != 255 and frame < 12
            desc = self.descriptor(key)
            pointer = (desc[2], int.from_bytes(desc[3:5], 'little'))
            item = self.contract['by_address'][pointer]
            size, tiles, width, frame_bytes = item['size'], item['tiles'], item['size'] // 8, item['frame_bytes']
            assert bool(desc[1] & 0x20) == (size == 32), ('Descriptor native32 flag differs from source', key, item['role'])
            assert desc[1] & ~0x27 == 0, ('Unexpected descriptor bits', key, desc[1])
            source = item['packet'][frame * frame_bytes:(frame + 1) * frame_bytes]
            assert bytes(self.p.memory[1, 0x8000 + index * SLOT_BYTES:0x8000 + index * SLOT_BYTES + frame_bytes]) == source, (
                'Native whole-body VRAM differs from compiled source', index, key, frame, size)
            masks_address = int.from_bytes(desc[6:8], 'little')
            mask = int.from_bytes(self.rom_range(desc[5], masks_address + frame * 2, 2), 'little')
            attrs = self.rom_range(desc[5], masks_address + 24 + frame * tiles, tiles)
            assert mask == int.from_bytes(item['masks'][frame * 2:frame * 2 + 2], 'little')
            assert attrs == item['attrs'][frame * tiles:(frame + 1) * tiles]
            assert self.read('wPeonLargeMetadataIDsV0215', OBJECTS)[index] == key
            assert self.read('wPeonLargeMetadataFramesV0215', OBJECTS)[index] == frame
            cache_masks = bytes(self.read('wPeonLargeMetadataMasksV0215', OBJECTS * 2))
            assert int.from_bytes(cache_masks[index * 2:index * 2 + 2], 'little') == mask
            cache_attrs = bytes(self.read('wPeonLargeMetadataAttrsV0215', OBJECTS * SLOT_TILES))
            assert cache_attrs[index * SLOT_TILES:index * SLOT_TILES + tiles] == attrs
            dy, dx = (-16, -8) if size == 32 else (-8, -4)
            entries = [bytes(((tile // width * 8 + dy) & 255, (tile % width * 8 + dx) & 255,
                              tile, attrs[tile] | (0x80 if tile >= tiles - width else 0)))
                       for tile in range(tiles) if mask & 1 << tile]
            count = self.read('wPeonLargeRelativeCountsV0215', OBJECTS)[index]
            assert count == len(entries)
            template = bytes(self.read('wPeonLargeRelativeOAMV0215', OBJECTS * SLOT_TILES * 4))
            assert template[index * 64:index * 64 + count * 4] == b''.join(entries), (
                'Native relative template differs from source', index, key, frame, size)
            assert all(tile % SLOT_TILES < tiles for y, x, tile, flags in cells)
            origins = {((y - (tile % SLOT_TILES // width * 8 + dy)) & 255,
                        (x - (tile % SLOT_TILES % width * 8 + dx)) & 255)
                       for y, x, tile, flags in cells}
            assert len(origins) == 1, ('Actor split across origins', index, cells, origins)
            oy, ox = next(iter(origins))
            expected = {((oy + tile // width * 8 + dy) & 255,
                         (ox + tile % width * 8 + dx) & 255, index * SLOT_TILES + tile)
                        for tile in range(tiles) if mask & 1 << tile
                        and 8 < ((oy + tile // width * 8 + dy) & 255) < 160
                        and 0 < ((ox + tile % width * 8 + dx) & 255) < 168}
            assert {cell[:3] for cell in cells} == expected, ('Partially admitted native actor', index, size, cells, expected)
            assert all(flags & 7 == attrs[tile % SLOT_TILES] and not flags & 0x60
                       for y, x, tile, flags in cells), ('Incorrect source palette/mirror', index, cells)
            checked = occluded = 0
            if strict_lcd:
                for cell in cells:
                    y, x, tile, flags = cell
                    pixels = decode_tile(source[(tile % SLOT_TILES) * 16:(tile % SLOT_TILES + 1) * 16])
                    for py in range(8):
                        for px in range(8):
                            color, sx, sy = pixels[py][px], x - 8 + px, y - 16 + py
                            if not color or not (0 <= sx < 160 and 0 <= sy < 144):
                                continue
                            if self.earlier_object_covers(oam, oam.index(cell), sx, sy):
                                continue
                            bg_color, bg_attr, bg_rgb = self.background_pixel(sx, sy)
                            if self.p.memory[0xff40] & 1 and bg_color and (bg_attr & 0x80 or flags & 0x80):
                                assert lcd.getpixel((sx, sy)) == bg_rgb, (
                                    'Actual foreground-priority LCD pixel mismatch', item['role'], size, frame, sx, sy)
                                occluded += 1
                            else:
                                assert lcd.getpixel((sx, sy)) == self.palette_rgb(flags & 7, color), (
                                    'Actual LCD source pixel mismatch', item['role'], size, frame, sx, sy,
                                    lcd.getpixel((sx, sy)), self.palette_rgb(flags & 7, color), bg_attr)
                                checked += 1
                if index == 0:
                    assert checked > 0, ('No actual hero source pixels inspected', item['role'])
            reports[str(index)] = {'key': key, 'frame': frame, 'role': item['role'], 'frame_size': size,
                'complete_visible_tiles': len(cells), 'source_mask': mask, 'source_VRAM_exact': True,
                'source_palette_attrs_exact': True, 'relative_OAM_template_source_exact': True,
                'actual_LCD_source_pixels': checked, 'actual_LCD_foreground_occlusion_pixels': occluded,
                'reserved_slot_tiles': SLOT_TILES}
            self.runtime_roles.setdefault(item['role'], {'frame_size': size, 'observed_frames': set()})['observed_frames'].add(frame)
        self.body_checks += 1
        if label:
            self.capture(label)
        result = {'objects': len(oam), 'maximum_scanline': max(occupancy, default=0), 'actors': reports}
        self.last_native_scene = result
        return result

    def direction_checks(self):
        result = super().direction_checks()
        role = CLASSES[self.class_index]
        result['walking']['animation_note'] = (
            'Actual native gait addresses were observed with complete source/VRAM/OAM checks; '
            'address coverage alone does not establish newly drawn animation.')
        result['walking']['distinct_source_pose_packets_per_direction'] = (
            self.contract['report']['roles'][role]['distinct_pose_packets_per_direction'])
        result['walking']['completed_native_scene'] = self.last_native_scene
        return result

    def earlier_object_covers(self, oam, position, sx, sy):
        for y, x, tile, flags in oam[:position]:
            if x - 8 <= sx < x and y - 16 <= sy < y - 8:
                pixels = decode_tile(bytes(self.p.memory[1 if flags & 8 else 0,
                    0x8000 + tile * 16:0x8000 + (tile + 1) * 16]))
                px, py = sx - x + 8, sy - y + 16
                if flags & 0x20:
                    px = 7 - px
                if flags & 0x40:
                    py = 7 - py
                if pixels[py][px]:
                    return True
        return False

    def background_pixel(self, sx, sy):
        lcdc = self.p.memory[0xff40]
        wx, wy = self.p.memory[0xff4b] - 7, self.p.memory[0xff4a]
        if lcdc & 0x20 and sx >= wx and sy >= wy:
            x, y = sx - wx, sy - wy
            base = 0x9c00 if lcdc & 0x40 else 0x9800
        else:
            x, y = (sx + self.p.memory[0xff43]) & 255, (sy + self.p.memory[0xff42]) & 255
            base = 0x9c00 if lcdc & 8 else 0x9800
        address = base + y // 8 * 32 + x // 8
        tile, attr = self.p.memory[0, address], self.p.memory[1, address]
        address = (0x8000 + tile * 16 if lcdc & 0x10
                   else 0x9000 + (tile if tile < 128 else tile - 256) * 16)
        pixels = decode_tile(bytes(self.p.memory[(attr >> 3) & 1, address:address + 16]))
        tx, ty = x % 8, y % 8
        if attr & 0x20:
            tx = 7 - tx
        if attr & 0x40:
            ty = 7 - ty
        color = pixels[ty][tx]
        offset = (attr & 7) * 8 + color * 2
        raw = bytes(self.read('wBGPals2', 64))
        rgb555 = int.from_bytes(raw[offset:offset + 2], 'little')
        rgb = tuple(((rgb555 >> shift) & 31) * 8 for shift in (0, 5, 10))
        return color, attr, rgb

    def gornek_marker(self, label):
        # A glyph-only priority fix must not hide or split its quest giver.
        # Inspect the same paused frame's complete native bodies and LCD.
        scene = self.scene(strict_lcd=True)
        records = self.read('wObjectStructs', 13 * 40)
        marker = next(records[i:i + 40] for i in range(40, 13 * 40, 40)
                      if records[i] == 0xfd and records[i + 1] == 2)
        assert tuple(marker[16:18]) == (14, 12), 'Marker event coordinates changed'
        resolved = self.read('wVariableSprites', 16)[0xfd - 0xf0]
        source_label = {0x35: 'PeonQuestAvailableYellowGFX',
                        0x36: 'PeonQuestActiveGrayGFX',
                        0x3c: 'PeonQuestCompleteYellowGFX'}[resolved]
        tile = marker[2] & 0x7f
        assert marker[2] & 0x80, 'Marker overlaps streamed bank1 pool'
        source = self.rom_range(*self.sym[source_label], 64)
        assert bytes(self.p.memory[0, 0x8000 + tile * 16:0x8000 + (tile + 4) * 16]) == source
        origin_x = (marker[23] + marker[25] + 8 + self.read('wPlayerBGMapOffsetX')[0]) & 255
        origin_y = (marker[24] + marker[26] + 12 + self.read('wPlayerBGMapOffsetY')[0] - self.marker_offset_pixels) & 255
        raw = list(self.p.memory[0xfe00:0xfea0])
        oam = [tuple(raw[i:i + 4]) for i in range(0, 160, 4)]
        expected = {(origin_y + i // 2 * 8, origin_x + i % 2 * 8, tile + i)
                    for i in range(4)}
        cells = [cell for cell in oam if cell[:3] in expected and not cell[3] & 8]
        assert {cell[:3] for cell in cells} == expected, ('Quest glyph partially missing', cells, expected)
        assert all(flags & 7 == marker[6] & 7 for y, x, t, flags in cells)
        checked = 0
        lcd = self.p.screen.image.convert('RGB')
        for y, x, t, flags in cells:
            for py, row in enumerate(self.tile_indices(source[(t - tile) * 16:(t - tile + 1) * 16])):
                for px, color in enumerate(row):
                    sx, sy = x - 8 + px, y - 16 + py
                    if color and 0 <= sx < 160 and 0 <= sy < 144:
                        assert lcd.getpixel((sx, sy)) == self.palette_rgb(flags & 7, color), (
                            'Actual LCD marker pixel mismatch', sx, sy)
                        checked += 1
        assert checked > 0
        records = self.read('wObjectStructs', OBJECTS * 40)
        npc_index = next(i for i in range(1, OBJECTS)
                         if records[i * 40] == 0x3a and records[i * 40 + 1] == 1)
        assert str(npc_index) in scene['actors'], 'The nearby quest giver was culled below its glyph'
        npc_cells = [cell for cell in oam if cell[3] & 8 and cell[2] // SLOT_TILES == npc_index
                     and 8 < cell[0] < 160 and 0 < cell[1] < 168]
        assert npc_cells, 'The nearby quest giver must remain visible below its glyph'
        head_y = []
        for ny, nx, nt, nf in npc_cells:
            pixels = decode_tile(bytes(self.p.memory[1, 0x8000 + nt * 16:0x8000 + (nt + 1) * 16]))
            head_y.extend(ny - 16 + py for py in range(8) for px in range(8) if pixels[py][px])
        marker_y = []
        for my, mx, mt, mf in cells:
            pixels = decode_tile(source[(mt - tile) * 16:(mt - tile + 1) * 16])
            marker_y.extend(my - 16 + py for py in range(8) for px in range(8) if pixels[py][px])
        assert max(marker_y) < min(head_y), ('Quest glyph overlaps the source head', max(marker_y), min(head_y))
        self.capture(label)
        return {'source': source_label, 'source_VRAM_exact': True,
                'native_event_coordinates': [10, 8], 'visual_Y_shift_pixels': -self.marker_offset_pixels,
                'source_opaque_head_clearance_pixels': min(head_y) - max(marker_y) - 1,
                'complete_visible_tiles': len(cells), 'actual_LCD_source_pixels': checked,
                'same_frame_whole_actor_scene': scene,
                'quest_giver_complete_visible_tiles': scene['actors'][str(npc_index)]['complete_visible_tiles'],
                'optional_companion_visible': any(actor['role'] == 'imp' for actor in scene['actors'].values())}

    def master_scene(self):
        self.p.tick(4, True)
        assert self.map() == 22 and self.read('wBackupMapNumber') == [14]
        world = self.scene(strict_lcd=True)
        records = self.read('wObjectStructs', OBJECTS * 40)
        raw = list(self.p.memory[0xfe00:0xfea0])
        oam = [tuple(raw[i:i + 4]) for i in range(0, 160, 4) if 8 < raw[i] < 160 and 0 < raw[i + 1] < 168]
        masters = {}
        for i in range(1, OBJECTS):
            actor = records[i * 40:(i + 1) * 40]
            if actor[0] not in (0x6a, 0x6b, 0x6c):
                continue
            ordinal = actor[0] - 0x6a
            role = ('shaman_master', 'warrior_trainer', 'enemy_warlock')[ordinal]
            folder = 'large_masters_v0219' if ordinal == 1 else 'large_masters_v0213'
            packet = (ROOT / 'gfx' / folder / (role + '.bin')).read_bytes()
            label = ('PeonLargeShamanWorldV0213', 'PeonLargeWarriorWorldV0213', 'PeonLargeWarlockWorldV0213')[ordinal]
            assert self.rom_range(*self.sym[label], len(packet)) == packet
            bank, base = (0 if actor[2] & 128 else 1), actor[2] & 127
            assert bytes(self.p.memory[bank, 0x8000 + base * 16:0x8000 + base * 16 + 144]) == packet
            cells = [cell for cell in oam if bool(cell[3] & 8) == bool(bank) and base <= cell[2] < base + 9]
            assert not cells or len(cells) == 9, ('A static master was partially admitted', role, cells)
            assert all(flags & 7 == MASTER_ATTRS[role][tile - base] for y, x, tile, flags in cells)
            masters[role] = {'source_ROM_and_VRAM_exact': True, 'complete_admitted_cells': len(cells),
                             'whole_body_omitted_by_native_budget': not cells}
        assert len(masters) == 3
        assert not any(records[i * 40] == 0x68 for i in range(OBJECTS)), 'Indoor imp stays in party, hidden in lodge'
        self.check_lodge_palettes()
        background = self.native_background()
        assert self.position() == (5, 5)
        if self.lodge_background_reference is None:
            self.lodge_background_reference = background
        assert background['cells'] == self.lodge_background_reference['cells']
        return {'world': world, 'static_masters': masters,
                'visible_background_restoration': {k: v for k, v in background.items() if k != 'cells'}}


def run_lodge(session):
    session.enter_lodge()
    before = session.master_scene()
    session.capture('mixed_native_lodge_before_training')
    interactions = []
    for index in range(3):
        interaction = session.talk_master(index)
        session.navigate((5, 5))
        interaction['after_dialogue'] = session.master_scene()
        session.capture('mixed_native_lodge_after_' + CLASSES[index])
        interactions.append(interaction)
    restart = session.cold_continue_in_lodge()
    session.leave_lodge()
    session.capture('mixed_native_cold_continue_outdoors')
    return {'before': before, 'trainer_interactions': interactions, 'cold_continue': restart}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--sym', type=Path, required=True)
    parser.add_argument('--expected-rom-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--classes', default='shaman,warrior,warlock')
    parser.add_argument('--asset-manifest', type=Path, default=ROOT / 'gfx/world_native_v0220/manifest.json')
    parser.add_argument('--graphics', type=Path, default=ROOT / 'gfx/world_native_v0220/graphics.asm')
    parser.add_argument('--allow-partial', action='store_true', help='Explicit prototype checks; no complete native32 import claim')
    parser.add_argument('--pilot-shaman-only', action='store_true', help='Frozen pilot: Shaman32 plus exact retained v19 native24 packets')
    parser.add_argument('--include-lodge', action='store_true', help='Real three-master dialogue/training and native SAVE/cold Continue')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    rom = args.rom.read_bytes()
    assert sha(rom) == args.expected_rom_sha256, 'Unexpected ROM candidate'
    sym = symbols(args.sym)
    contract = canonical_packets(rom, sym, args.asset_manifest, args.graphics, args.allow_partial, args.pilot_shaman_only)
    WorldNativeSessionV0220.contract = contract
    WorldNativeSessionV0220.marker_offset_pixels = 8 if args.pilot_shaman_only else 16
    restoration.SOURCE_MAPS = dict(restoration.SOURCE_MAPS)
    restoration.SOURCE_MAPS[14] = ('TheDen', 'gfx/quieter_ground_v0220/TheDen.2bpp', 'PeonUserEnvTheDenGFX')
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'version': 'v0.2.20', 'status': 'RUNNING', 'rom_sha256': sha(rom),
              'canonical_native_packets': contract['report'], 'slot_tiles': SLOT_TILES,
              'ordinary_buttons_only': True, 'RAM_edits': False, 'states_loaded': False,
              'user_batteries_opened': False, 'classes': {}}
    with tempfile.TemporaryDirectory(prefix='peon-world-native-v0220-') as temp:
        for name in args.classes.split(','):
            private = Path(temp) / (name + '.gbc')
            shutil.copyfile(args.rom, private)
            session = WorldNativeSessionV0220(private, sym, CLASSES.index(name), args.output)
            try:
                session.fresh_class()
                directions = session.direction_checks()
                session.navigate((10, 10))
                session.p.tick(90, True)
                available = session.gornek_marker('native_available_marker_above_actor')
                session.talk_at((10, 10), 'up', 'native_gornek_quest_with_larger_actor')
                assert session.event('EVENT_PEON_QUEST_ACCEPTED')
                session.p.tick(90, True)
                npc = session.scene('nearby_quest_NPC_after_dialogue')
                active = session.gornek_marker('native_active_marker_above_actor')
                occupied = {actor['xy'] for actor in session.live_actors('TheDen')}
                point = next(p for p in ((10, 11), (11, 11), (10, 12))
                             if p not in occupied and session.collision_at(*p) != 'WALL')
                session.navigate(point)
                crowded = session.scene('mixed_native_crowded_priority', strict_lcd=True)
                samples = []
                for _ in range(3):
                    session.p.tick(90, True)
                    samples.append(session.scene())
                lodge = run_lodge(session) if args.include_lodge else None
                assert not session.renderer_hook_errors, session.renderer_hook_errors
                report['classes'][name] = {'status': 'PASS', 'directions': directions,
                    'base_opening': session.base_intro, 'nearby_NPC_interaction': npc,
                    'crowded_scene': crowded, 'crowded_additional_complete_body_samples': samples,
                    'quest_markers': {'available': available, 'active': active},
                    'whole_actor_scene_checks': session.body_checks,
                    'complete_renderer_histogram_checks': session.histogram_checks,
                    'native_current_object_context_preserved': True,
                    'lodge_save_continue': lodge,
                    'runtime_observed_roles': {role: record | {'observed_frames': sorted(record['observed_frames'])}
                                               for role, record in session.runtime_roles.items()}}
            except Exception as error:
                report['status'], report['failure'] = 'FAIL', repr(error)
                session.capture('failure')
                (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
                raise
            finally:
                session.p.stop(save=False)
    report['status'] = 'PASS'
    report['native32_runtime_observed'] = any(record['frame_size'] == 32
        for result in report['classes'].values() for record in result['runtime_observed_roles'].values())
    if not args.allow_partial:
        assert report['native32_runtime_observed'], 'No integrated native32 actor was observed'
    (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'rom_sha256': sha(rom), 'classes': list(report['classes']),
                      'native32_runtime_observed': report['native32_runtime_observed']}), flush=True)


if __name__ == '__main__':
    main()
