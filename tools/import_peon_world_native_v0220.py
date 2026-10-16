#!/usr/bin/env python3
"""Encode declared native32 world cels alongside byte-exact native24 actors.

This is an encoder, not an artwork generator. Source JSON records separately
document the lossy nearest source conversion and newly authored gait cels.
No source PNG is resized, repainted or overwritten here. The ordinary and hero
descriptors retain their eight-byte ABI; bit5 of their palette byte marks32px.
An explicitly requested partial import is marked PARTIAL, never final PASS.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import copy
import hashlib
import json
import re
import shutil

import numpy as np
from PIL import Image

from peon_world_readability_profile_v0219 import PALETTES

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/world_native_v0220'
OUT = ROOT/'gfx/world_native_v0220'
PRIOR = ROOT/'gfx/world_readability_v0219'
DIRECTIONS = ('front', 'back', 'left', 'right')
PACK_ROLES = {
    'heroes': {'base', 'shaman', 'warrior', 'warlock', 'sleeping'},
    'orc_npcs': {'orc_merchant', 'quest_peon', 'peon_worker', 'beast_handler', 'orc_guard',
                 'camp_guard', 'veteran_questgiver', 'shaman_apprentice'},
    'trolls': {'troll_villager', 'troll_merchant', 'troll_guard', 'senjin_chief',
               'troll_shaman', 'senjin_troll_shaman'},
}
HERO_ROLES = ('base', 'shaman', 'warrior', 'warlock')
FILES = ('overworld.bin', 'masks.bin', 'attrs.bin', 'overworld.png')
LEGACY_WALK_SPRITES = {'SPRITE_CHRIS', 'SPRITE_KRIS', 'SPRITE_LASS', 'SPRITE_ROCKER',
                       'SPRITE_COOLTRAINER_M', 'SPRITE_COOLTRAINER_F'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def encode(frame):
    values = np.asarray(frame)
    size = values.shape[0]
    assert values.shape == (size, size) and size in (24, 32)
    assert set(np.unique(values)) <= {0, 1, 2, 3}
    packet = bytearray()
    for y in range(0, size, 8):
        for x in range(0, size, 8):
            for row in values[y:y+8, x:x+8]:
                packet.extend((sum((int(v) & 1) << (7-i) for i, v in enumerate(row)),
                               sum((int(v) >> 1) << (7-i) for i, v in enumerate(row))))
    assert len(packet) == size*size//4
    return bytes(packet)


def decode(data, size):
    assert len(data) == size*size//4
    values = np.zeros((size, size), dtype=np.uint8)
    columns = size//8
    for tile in range(columns*columns):
        ty, tx = divmod(tile, columns)
        for y in range(8):
            low, high = data[tile*16+y*2:tile*16+y*2+2]
            for x in range(8):
                values[ty*8+y, tx*8+x] = ((low >> (7-x)) & 1) | (((high >> (7-x)) & 1) << 1)
    return Image.fromarray(values)


def indexed(rows, size, role, direction, pose):
    assert len(rows) == size and all(isinstance(row, str) and len(row) == size for row in rows), (role, direction, pose, size)
    assert set(''.join(rows)) <= set('.123'), (role, direction, pose, 'Only .123 native cells are allowed')
    values = np.array([[0 if c == '.' else int(c) for c in row] for row in rows], dtype=np.uint8)
    assert np.any(values), (role, direction, pose, 'Empty body')
    frame = Image.fromarray(values)
    assert np.array_equal(np.asarray(decode(encode(frame), size)), values)
    return frame


def active_mask(frame):
    values = np.asarray(frame)
    size = frame.width
    return sum(int(np.any(values[y:y+8, x:x+8])) << i
               for i, (y, x) in enumerate((y, x) for y in range(0, size, 8) for x in range(0, size, 8)))


def render(frame, attrs):
    size = frame.width
    assert len(attrs) == (size//8)**2
    values = np.asarray(frame)
    result = np.zeros((size, size, 4), dtype=np.uint8)
    for tile, palette in enumerate(attrs):
        ty, tx = divmod(tile, size//8)
        pixels = values[ty*8:ty*8+8, tx*8:tx*8+8]
        colors = np.array(PALETTES[palette], dtype=np.uint8)
        colors = (colors << 3) | (colors >> 2)
        result[ty*8:ty*8+8, tx*8:tx*8+8, :3] = colors[pixels]
        result[ty*8:ty*8+8, tx*8:tx*8+8, 3] = np.where(pixels != 0, 255, 0)
    return Image.fromarray(result)


def validate_attrs(attrs, count, role, direction, pose):
    assert len(attrs) == count and all(type(p) is int and p in (1, 2, 3, 5, 6, 7) for p in attrs), (role, direction, pose, 'Reserved OBJ palette or invalid attribute count', attrs)
    return bytes(attrs)


def source_role(art, role):
    size = art.get('frame_size', art.get('dimensions', [len(art['views']['front'])])[0])
    assert size in (24, 32), (role, size)
    assert art.get('dimensions', [size, size]) == [size, size]
    assert set(art['views']) == set(DIRECTIONS), (role, 'All four views are required')
    assert type(art['palette']) is int and art['palette'] in (1, 2, 3, 5, 6, 7)
    assert art.get('references') and all((ROOT/path).is_file() for path in art['references'])
    frames, attrs = [], []
    for direction in DIRECTIONS:
        idle_attrs = art.get('attributes', {}).get(direction, [art['palette']] * (size//8)**2)
        walks = art.get('walk', {}).get(direction)
        walk_attrs = art.get('walk_attributes', {}).get(direction, [idle_attrs, idle_attrs])
        assert walks is None or len(walks) == 2, (role, direction, 'Two gait cels required')
        assert len(walk_attrs) == 2
        if size == 32:
            assert walks is not None, (role, direction, 'New native32 actors require authored gait cels')
        for pose, rows in enumerate([art['views'][direction]] + (walks or [art['views'][direction]]*2)):
            frames.append(indexed(rows, size, role, direction, pose))
            attrs.append(validate_attrs(idle_attrs if pose == 0 else walk_attrs[pose-1], (size//8)**2, role, direction, pose))
    packet = b''.join(encode(f) for f in frames)
    masks = b''.join(active_mask(f).to_bytes(2, 'little') for f in frames)
    attributes = b''.join(attrs)
    return size, frames, attrs, packet, masks, attributes


def sprite_ids():
    # The ordinary sprite enum is one append-only const_def sequence.
    source = (ROOT/'constants/sprite_constants.asm').read_text().split('DEF NUM_OVERWORLD_SPRITES', 1)[0]
    names = re.findall(r'^\s*const (SPRITE_\w+)', source, re.M)
    assert names[:2] == ['SPRITE_NONE', 'SPRITE_CHRIS']
    return {name: i for i, name in enumerate(names)}


def descriptor_table(runtime, ids):
    indexed = {ids[b['sprite']]: (i, b) for i, b in enumerate(runtime)}
    assert len(indexed) == len(runtime), 'Duplicate ordinary sprite descriptor'
    lines = ['; Generated sprite-ID lookup for the existing ordered eight-byte descriptors.\n',
             '; Include in the same floating ROMX section as the renderer and bindings.\n',
             '; Null entries preserve the former failed-lookup carry result.\n',
             'PeonLargeWorldDescriptorPointersV0220::\n']
    for sprite in range(256):
        if sprite in indexed:
            i, binding = indexed[sprite]
            lines.append(f'\tdw PeonLargeWorldBindingsV0215 + {i} * 8 ; ${sprite:02x} {binding["sprite"]}\n')
        else:
            lines.append(f'\tdw 0 ; ${sprite:02x} native/unbound\n')
    lines.append('\tassert @ - PeonLargeWorldDescriptorPointersV0220 == 256 * 2\n')
    return ''.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-partial', action='store_true', help='Explicit pilot only: retain unavailable roles at24 and mark the manifest PARTIAL.')
    args = parser.parse_args()
    prior_path = PRIOR/'manifest.json'
    prior = json.loads(prior_path.read_text())
    originals = prior['source_files_sha256']
    assert len(prior['roles']) == 39 and len(originals) == 499
    assert all(sha((ROOT/path).read_bytes()) == digest for path, digest in originals.items())
    references = dict(originals)
    for entry in prior['roles'].values():
        for reference in entry.get('design_references', []):
            path, digest = reference['source'], reference['source_sha256']
            assert sha((ROOT/path).read_bytes()) == digest, (path, 'A historical design reference changed')
            assert path not in references or references[path] == digest
            references[path] = digest
    preserved = {rel(PRIOR/role/name): sha((PRIOR/role/name).read_bytes()) for role in prior['roles'] for name in FILES}
    authored, source_hashes = {}, {}
    for pack, expected in PACK_ROLES.items():
        path = SOURCE/(pack+'.json')
        if not path.exists():
            continue
        content = path.read_bytes()
        source_hashes[rel(path)] = sha(content)
        source = json.loads(content)
        assert source['version'] == 'v0.2.20', path
        allowed = expected | ({'warrior_trainer'} if pack == 'orc_npcs' else set())
        for role, art in source['roles'].items():
            assert role in allowed and role in prior['roles'] and role not in authored, (path, role)
            authored[role] = (path, art, source_role(art, role))
            for reference in art['references']:
                digest = sha((ROOT/reference).read_bytes())
                assert reference not in references or references[reference] == digest
                references[reference] = digest
    required = set().union(*PACK_ROLES.values())
    missing = sorted(required - {role for role, (_, _, data) in authored.items() if data[0] == 32})
    assert not missing or args.allow_partial, ('Native32 sources not complete; use --allow-partial only for an explicit pilot', missing)
    assert authored, 'No native32 source packet is available'
    for role, (_, _, data) in authored.items():
        if role == 'warrior_trainer':
            assert data[0] == 24, (role, 'The approved Garrosh packet stays native24')
        else:
            assert data[0] == 32 or args.allow_partial, (role, 'Unexpected size')
    OUT.mkdir(parents=True, exist_ok=True)
    roles = {}
    for role, previous in prior['roles'].items():
        folder = OUT/role
        folder.mkdir(exist_ok=True)
        retained = role not in authored or authored[role][2][0] == 24
        if retained:
            if role in authored:
                _, _, parsed = authored[role]
                assert parsed[3:6] == tuple((PRIOR/role/name).read_bytes() for name in FILES[:3]), (role, 'The approved native24 master must stay byte-exact')
            for name in FILES:
                shutil.copyfile(PRIOR/role/name, folder/name)
            size = 24
            packet = (folder/'overworld.bin').read_bytes()
            masks = (folder/'masks.bin').read_bytes()
            attributes = (folder/'attrs.bin').read_bytes()
            frames = [decode(packet[i*144:(i+1)*144], size) for i in range(12)]
            attrs = [attributes[i*9:(i+1)*9] for i in range(12)]
            entry = copy.deepcopy(previous)
            entry.update({'source_packet': rel(PRIOR/role/'overworld.bin'), 'source_sha256': sha(packet),
                          'source_kind': 'byte_exact_retained_v0219_native24_packet',
                          'prior_source_kind': previous.get('source_kind'),
                          'source_note': 'All three native binaries and the strip PNG are byte-exact v19 inputs.'})
            if role in authored:
                entry['verified_retained_recipe'] = rel(authored[role][0])
        else:
            path, art, parsed = authored[role]
            size, frames, attrs, packet, masks, attributes = parsed
            for name, content in zip(FILES[:3], (packet, masks, attributes)):
                (folder/name).write_bytes(content)
            strip = Image.new('RGBA', (size*4, size*3))
            for i, (frame, attr) in enumerate(zip(frames, attrs)):
                strip.paste(render(frame, attr), ((i//3)*size, (i%3)*size))
            strip.save(folder/'overworld.png')
            entry = {'source_packet': rel(path), 'source_sha256': source_hashes[rel(path)],
                     'source_kind': art.get('source_kind', art.get('provenance', {}).get('source_kind', 'documented_lossy_source_conversion_with_authored_native_gait')),
                     'source_note': art.get('source_note', 'Native JSON cels encode losslessly; their source conversion is separately documented.'),
                     'provenance': art.get('provenance', {}), 'identity': art['identity'],
                     'design_references': [{'source': path, 'source_sha256': sha((ROOT/path).read_bytes())} for path in art['references']],
                     'new_anatomy_authored': art.get('new_anatomy_authored', False),
                     'new_detail_generated': art.get('new_detail_generated', False),
                     'detail_generated_by_encoder': False, 'exact_native_grid_recovery': False,
                     'resampling': art.get('resampling', 'See source provenance; no resizing occurs in this encoder'),
                     'animation_note': art.get('animation_note', 'New native gait cels are authored, not recovered source animation'),
                     'palette_index': art['palette'], 'authored_source_role': role}
        tiles = (size//8)**2
        frame_bytes = tiles*16
        assert (len(packet), len(masks), len(attributes)) == (12*frame_bytes, 24, 12*tiles)
        records = []
        for i, (frame, attr) in enumerate(zip(frames, attrs)):
            encoded = packet[i*frame_bytes:(i+1)*frame_bytes]
            assert np.array_equal(np.asarray(decode(encoded, size)), np.asarray(frame))
            assert int.from_bytes(masks[i*2:i*2+2], 'little') == active_mask(frame)
            validate_attrs(attr, tiles, role, DIRECTIONS[i//3], i%3)
            mask = active_mask(frame)
            records.append({'direction': DIRECTIONS[i//3], 'pose': i%3, 'frame_index': i,
                            'byte_offset': i*frame_bytes, 'opaque_pixels_after': int(np.count_nonzero(np.asarray(frame))),
                            'opaque_bounds_after': list(render(frame, attr).getbbox()), 'mask': mask,
                            'oam_entries': mask.bit_count(), 'per_tile_palette_ids': list(attr),
                            'native_decode_exact': True, 'source_cells_decode_exact': not retained})
        entry.update({'output_packet': rel(folder/'overworld.bin'), 'output_sha256': sha(packet),
                      'mask_sha256': sha(masks), 'attrs_sha256': sha(attributes),
                      'strip_sha256': sha((folder/'overworld.png').read_bytes()),
                      'label': previous['label'], 'masks_label': previous['masks_label'], 'attrs_label': previous['attrs_label'],
                      'frame_size': size, 'dimensions_after': [size, size], 'bytes_per_frame': frame_bytes,
                      'tiles_per_frame': tiles, 'attribute_bytes_per_frame': tiles, 'mask_bytes_per_frame': 2,
                      'descriptor_palette_byte': entry['palette_index'] | (0x20 if size == 32 else 0),
                      'uses_palette_indices': sorted(set(attributes)), 'preserved_v0219_bytes': retained,
                      'exported_in_rom': previous['exported_in_rom'], 'frame_records': records,
                      'gait_cels_declared': role in authored and bool(authored[role][1].get('walk'))})
        roles[role] = entry
    graphics = ['; Mixed native24/32 actors; all labels and the eight-byte descriptor ABI are retained.\n']
    for role, entry in roles.items():
        if not entry['exported_in_rom']:
            continue
        label, mask_label, attr_label = entry['label'], entry['masks_label'], entry['attrs_label']
        tiles = entry['tiles_per_frame']
        graphics += [f'SECTION "Peon{entry["frame_size"]} World {role} v0220", ROMX, ALIGN[4]\n',
                     f'{label}::\n\tINCBIN "gfx/world_native_v0220/{role}/overworld.bin"\n',
                     f'\tassert @ - {label} == 12 * {tiles} * TILE_SIZE\n',
                     f'\nSECTION "Peon{entry["frame_size"]} World {role} metadata v0220", ROMX\n',
                     f'{mask_label}::\n\tINCBIN "gfx/world_native_v0220/{role}/masks.bin"\n',
                     f'\tassert @ - {mask_label} == 12 * 2\n',
                     f'{attr_label}::\n\tINCBIN "gfx/world_native_v0220/{role}/attrs.bin"\n',
                     f'\tassert @ - {attr_label} == 12 * {tiles}\n',
                     f'\tassert {attr_label} - {mask_label} == 12 * 2\n',
                     f'\tassert BANK({mask_label}) == BANK({attr_label})\n\n']
    (OUT/'graphics.asm').write_text(''.join(graphics))
    bindings = (PRIOR/'bindings.asm').read_text()
    for role, entry in roles.items():
        value = f'{entry["palette_index"]} | $20' if entry['frame_size'] == 32 else str(entry['palette_index'])
        bindings = re.sub(r'(db SPRITE_[A-Z_]+, )\d+(, BANK\('+re.escape(entry['label'])+r'\))',
                          lambda m: m[1]+value+m[2], bindings)
    (OUT/'bindings.asm').write_text(bindings)
    runtime = copy.deepcopy(prior['runtime_bindings'])
    ids = sprite_ids()
    flags = [int(any(ids.get(name) == i for name in LEGACY_WALK_SPRITES)) for i in range(256)]
    for i, binding in enumerate(runtime):
        entry = roles[binding['role']]
        binding.update({'palette_index': entry['palette_index'], 'descriptor_palette_byte': entry['descriptor_palette_byte'],
                        'frame_size': entry['frame_size'], 'descriptor_offset': i*8, 'sprite_id': ids[binding['sprite']]})
        if entry['frame_size'] == 32 and entry['gait_cels_declared']:
            flags[ids[binding['sprite']]] = 1
    table = descriptor_table(runtime, ids)
    existing_table = OUT/'descriptor_table.asm'
    if existing_table.exists():
        assert table == existing_table.read_text(), 'The existing ordered descriptor pointer table must stay compatible'
    existing_table.write_text(table)
    walk = ['; Native gait availability by ordinary sprite ID; legacy creature flags retained.\n',
            '; New native32 NPC flags are enabled only for declared authored gait cels.\n',
            'PeonLargeWorldWalkFlagsV0220::\n']
    for i in range(0, 256, 16):
        walk.append('\tdb '+', '.join(map(str, flags[i:i+16]))+f' ; ${i:02x}..${i+15:02x}\n')
    walk.append('\tassert @ - PeonLargeWorldWalkFlagsV0220 == 256\n')
    (OUT/'walk_flags.asm').write_text(''.join(walk))
    assert all(sha((ROOT/path).read_bytes()) == digest for path, digest in originals.items())
    assert all(sha((ROOT/path).read_bytes()) == digest for path, digest in references.items())
    assert all(sha((ROOT/path).read_bytes()) == digest for path, digest in preserved.items())
    assert all(sha((ROOT/path).read_bytes()) == digest for path, digest in source_hashes.items()), 'Source JSON changed during export; rerun after its writer finishes'
    report = {'version': 'v0.2.20', 'status': 'PARTIAL' if missing else 'PASS', 'partial_import_explicit': args.allow_partial,
              'method': 'Lossless mixed native24/32 indexed-cell encoding; lossy source sampling and newly authored gait are recorded by each source JSON, never claimed recovered detail.',
              'native_tile_order': 'row-major', 'native_frame_order': 'direction*3+pose (front/back/left/right)',
              'dimensions_after': 'per-role24or32', 'effective_world_palettes_rgb555': PALETTES,
              'source_original_pngs_changed': False, 'source_files_sha256': originals,
              'source_reference_files_sha256': references,
              'source_json_sha256': source_hashes, 'prior_manifest_sha256': sha(prior_path.read_bytes()),
              'preserved_v0219_files_sha256': preserved,
              'native32_roles': [r for r, e in roles.items() if e['frame_size'] == 32],
              'retained_native24_roles': [r for r, e in roles.items() if e['frame_size'] == 24],
              'missing_native32_roles': missing, 'converted_actor_families': sum(e['frame_size'] == 32 for e in roles.values()),
              'exported_actor_families': sum(e['exported_in_rom'] for e in roles.values()),
              'runtime_bindings': runtime, 'hero_bindings': [{'role': r, 'descriptor_offset': i*8,
                  'frame_size': roles[r]['frame_size'], 'descriptor_palette_byte': roles[r]['descriptor_palette_byte']} for i, r in enumerate(HERO_ROLES)],
              'descriptor_table': {'path': rel(OUT/'descriptor_table.asm'), 'entries': 256, 'bytes': 512, 'ordered_binding_count': len(runtime)},
              'walk_flags': {'path': rel(OUT/'walk_flags.asm'), 'entries': 256, 'flags': flags,
                             'legacy_sprite_flags_retained': sorted(LEGACY_WALK_SPRITES)},
              'roles': roles, 'native16px_menu_icons_unchanged': True, 'battle_sprites_unchanged': True,
              'map_props_unchanged': True, 'static_masters_unchanged': True,
              'save_and_collision_formats_unchanged': True, 'engine_changes': False,
              'runtime_verification': 'Static source/packet checks only; final-ROM playtests are separate.'}
    (OUT/'manifest.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)+'\n')
    print(json.dumps({'status': report['status'], 'roles': len(roles), 'native32_roles': len(report['native32_roles']),
                      'native24_roles': len(report['retained_native24_roles']), 'runtime_roles': report['exported_actor_families'],
                      'runtime_bindings': len(runtime), 'source_pngs_unchanged': len(originals), 'missing_native32_roles': missing}))


if __name__ == '__main__':
    main()
