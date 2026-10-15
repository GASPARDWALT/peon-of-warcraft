#!/usr/bin/env python3
"""Encode restored complete world images into the unchanged nine-tile ABI.

The indexed JSON files record the native restoration or source-art conversion
that created each cel. Encoding is lossless; conversion provenance must remain
explicit. Neither resizing historical16px art nor reducing an illustration is
claimed to add detail. Original PNGs and older releases are read-only.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import import_peon_world_actors_v0215 as native
from peon_world_readability_profile_v0219 import PALETTES

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/world_readability_v0219'
OUT = ROOT / 'gfx/world_readability_v0219'
REVIEW = ROOT / 'references/generated/world_readability_v0219'
PRIOR = ROOT / 'gfx/world_redraw_v0217'
DIRECTIONS = ('front', 'back', 'left', 'right')
PACKS = ('heroes', 'orc_npcs', 'trolls', 'beasts', 'monsters')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def indexed(rows, role, direction, pose):
    assert len(rows) == 24 and all(len(row) == 24 for row in rows), (role, direction, pose, '24x24 required')
    assert set(''.join(rows)) <= set('.123'), (role, direction, pose, 'Invalid native color index')
    values = np.array([[0 if cell == '.' else int(cell) for cell in row] for row in rows], dtype=np.uint8)
    assert np.any(values), (role, direction, pose, 'Empty body')
    result = Image.fromarray(values)
    assert np.array_equal(np.asarray(native.decode(native.encode(result), 24)), values)
    return result


def render(frame, attrs, palettes=PALETTES):
    result = Image.new('RGBA', (24, 24))
    for tile, palette in enumerate(attrs):
        y, x = divmod(tile, 3)
        crop = frame.crop((x * 8, y * 8, x * 8 + 8, y * 8 + 8))
        result.paste(native.rgba(crop, palettes[palette]), (x * 8, y * 8))
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    prior = json.loads((PRIOR / 'manifest.json').read_text())
    original_hashes = prior['source_files_sha256']
    assert all(sha((ROOT / name).read_bytes()) == digest for name, digest in original_hashes.items())
    authored = {}
    source_hashes = {}
    for pack in PACKS:
        path = SOURCE / (pack + '.json')
        payload = path.read_bytes()
        source_hashes[rel(path)] = sha(payload)
        packet = json.loads(payload)
        assert packet['version'] == 'v0.2.19'
        for role, record in packet['roles'].items():
            assert role not in authored and role in prior['roles'], ('Unknown or duplicate role', role)
            assert set(record['views']) == set(DIRECTIONS), (role, 'Four real directions required')
            assert all((ROOT / reference).is_file() for reference in record['references']), (role, 'Missing reference')
            authored[role] = (path, record)
    exported = {role for role, entry in prior['roles'].items() if entry['exported_in_rom']}
    assert exported <= set(authored), ('Runtime bodies missing authored cels', sorted(exported - set(authored)))
    roles = {}
    comparisons = []
    for role, previous in prior['roles'].items():
        folder, review = OUT / role, REVIEW / role
        folder.mkdir(exist_ok=True)
        review.mkdir(exist_ok=True)
        frames, attributes, records = [], [], []
        if role in authored:
            path, art = authored[role]
            for direction in DIRECTIONS:
                attrs = art.get('attributes', {}).get(direction, [art['palette']] * 9)
                assert len(attrs) == 9 and all(type(p) is int and 0 <= p < 8 and p not in (0, 4) for p in attrs), (role, direction, attrs)
                walks = art.get('walk', {}).get(direction)
                assert walks is None or len(walks) == 2, (role, direction, 'Two gait cels required')
                cels = [art['views'][direction]] + (walks or [art['views'][direction]] * 2)
                for pose, rows in enumerate(cels):
                    frames.append(indexed(rows, role, direction, pose))
                    attributes.append(bytes(attrs))
            references = [{'source': reference, 'source_sha256': sha((ROOT / reference).read_bytes())}
                          for reference in art['references']]
            entry = {
                'source_packet': rel(path), 'source_sha256': source_hashes[rel(path)],
                'source_kind': art.get('source_kind', art.get('provenance', {}).get('source_kind', 'documented_complete_source_restoration')),
                'source_note': art.get('source_note', 'Source restoration or lossy raster import; see role provenance'),
                'provenance': art.get('provenance', {}),
                'identity': art['identity'], 'design_references': references,
                'new_anatomy_authored': art.get('new_anatomy_authored', False),
                'new_detail_generated': False,
                'exact_native_grid_recovery': False,
                'resampling': art.get('resampling', 'See source provenance; no smoothing'),
                'animation_note': art.get('animation_note', 'Historical gait cels restored' if art.get('walk') else 'Source stills repeated at the existing three pose addresses'),
                'palette_index': art['palette'], 'authored_source_role': role,
            }
        else:
            # Unbound roster previews and the existing large-master reference
            # are retained explicitly; none is a fallback for a live NPC.
            source = PRIOR / role / 'overworld.bin'
            data = source.read_bytes()
            attrs = (PRIOR / role / 'attrs.bin').read_bytes()
            for i in range(12):
                frames.append(native.decode(data[i * 144:(i + 1) * 144], 24))
                attributes.append(attrs[i * 9:(i + 1) * 9])
            entry = {
                'source_packet': rel(source), 'source_sha256': sha(data),
                'source_kind': 'retained_unbound_v0217_packet',
                'source_note': 'Not a bound runtime body; existing bytes retained',
                'new_anatomy_authored': False, 'new_detail_generated': False,
                'palette_index': previous['palette_index'],
            }
            assert not previous['exported_in_rom']
        packet = b''.join(native.encode(frame) for frame in frames)
        masks = [native.active_mask(frame) for frame in frames]
        mask_data = b''.join(mask.to_bytes(2, 'little') for mask in masks)
        attr_data = b''.join(attributes)
        assert (len(packet), len(mask_data), len(attr_data)) == (1728, 24, 108)
        for name, data in (('overworld.bin', packet), ('masks.bin', mask_data), ('attrs.bin', attr_data)):
            (folder / name).write_bytes(data)
        strip = Image.new('RGBA', (96, 72))
        for i, (frame, attrs) in enumerate(zip(frames, attributes)):
            shown = render(frame, attrs)
            direction, pose = DIRECTIONS[i // 3], i % 3
            shown.save(review / f'world_{direction}_{pose}_24x24.png')
            strip.paste(shown, ((i // 3) * 24, pose * 24))
            records.append({
                'direction': direction, 'pose': pose, 'frame_index': i, 'byte_offset': i * 144,
                'opaque_pixels_after': int(np.count_nonzero(np.asarray(frame))),
                'opaque_bounds_after': list(shown.getbbox()), 'mask': masks[i],
                'oam_entries': masks[i].bit_count(), 'per_tile_palette_ids': list(attrs),
                'native_decode_exact': True, 'source_cells_decode_exact': role in authored,
            })
        strip.save(folder / 'overworld.png')
        # Review at1x and4x; labelled static art, never an emulator screenshot.
        comparison = Image.new('RGB', (4 * 160, 142), (217, 209, 182))
        draw = ImageDraw.Draw(comparison)
        draw.text((4, 2), role + ' — static v18 / restored v19', fill=(20, 20, 20))
        old_data = (PRIOR / role / 'overworld.bin').read_bytes()
        old_attrs = (PRIOR / role / 'attrs.bin').read_bytes()
        for d, direction in enumerate(DIRECTIONS):
            i = d * 3
            previous_frame = native.decode(old_data[i * 144:(i + 1) * 144], 24)
            from import_peon_world_redraw_v0217 import PALETTES as old_palettes
            before = render(previous_frame, old_attrs[i * 9:(i + 1) * 9], old_palettes)
            after = render(frames[i], attributes[i])
            x = d * 160
            draw.text((x + 2, 19), direction, fill=(20, 20, 20))
            comparison.paste(before.resize((48, 48), Image.Resampling.NEAREST), (x + 3, 40), before.resize((48, 48), Image.Resampling.NEAREST))
            comparison.paste(after.resize((96, 96), Image.Resampling.NEAREST), (x + 59, 37), after.resize((96, 96), Image.Resampling.NEAREST))
            comparison.paste(after, (x + 14, 105), after)
        comparison.save(review / 'comparison.png')
        if role in authored:
            comparisons.append((role, strip))
        entry.update({
            'output_packet': rel(folder / 'overworld.bin'), 'output_sha256': sha(packet),
            'mask_sha256': sha(mask_data), 'attrs_sha256': sha(attr_data),
            'label': previous['label'], 'masks_label': previous['masks_label'], 'attrs_label': previous['attrs_label'],
            'uses_palette_indices': sorted(set(attr_data)), 'exported_in_rom': previous['exported_in_rom'],
            'frame_records': records,
        })
        roles[role] = entry
    (OUT / 'graphics.asm').write_text((PRIOR / 'graphics.asm').read_text().replace('gfx/world_redraw_v0217/', 'gfx/world_readability_v0219/'))
    bindings = (PRIOR / 'bindings.asm').read_text()
    for role, entry in roles.items():
        label = entry['label']
        bindings = re.sub(r'(db SPRITE_[A-Z_]+, )\d+(, BANK\(' + re.escape(label) + r'\))',
                          lambda match: match[1] + str(entry['palette_index']) + match[2], bindings)
    (OUT / 'bindings.asm').write_text(bindings)
    runtime_bindings = copy.deepcopy(prior['runtime_bindings'])
    for binding in runtime_bindings:
        binding['palette_index'] = roles[binding['role']]['palette_index']
    report = {
        'version': 'v0.2.19', 'status': 'PASS',
        'method': 'Complete archived native art and whole source-world illustrations, converted separately and losslessly encoded into native2bpp',
        'native_tile_order': 'row-major', 'native_frame_order': 'direction*3+pose (front/back/left/right)',
        'dimensions_after': [24, 24], 'bytes_per_frame': 144,
        'effective_world_palettes_rgb555': PALETTES,
        'source_original_pngs_changed': False, 'source_files_sha256': original_hashes,
        'source_json_sha256': source_hashes, 'converted_actor_families': len(authored),
        'exported_actor_families': len(exported), 'converted_roles': sorted(authored),
        'retained_unbound_roles': sorted(set(roles) - set(authored)),
        'runtime_bindings': runtime_bindings, 'roles': roles,
        'new_anatomy_authored': any(roles[r].get('new_anatomy_authored') for r in authored),
        'native16px_menu_icons_unchanged': True,
        'battle_sprites_unchanged': True, 'map_props_unchanged': True,
        'static_masters': {'kento_and_bismillah_packets_unchanged': True,
                           'warrior_replaced_from_garrosh_world_source': True},
        'save_and_collision_formats_unchanged': True,
        'runtime_verification': 'Static source and encode checks only; exact-ROM emulator tests are separate',
    }
    for path in (OUT / 'manifest.json', REVIEW / 'import_report.json'):
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    assert all(sha((ROOT / name).read_bytes()) == digest for name, digest in original_hashes.items())
    (REVIEW / 'source_png_hashes.json').write_text(json.dumps({
        'source_files': original_hashes, 'source_files_count': len(original_hashes),
        'all_source_sha256_identical_before_after_import': True,
    }, indent=2) + '\n')
    overview = Image.new('RGB', (576, len(comparisons) * 100), (217, 209, 182))
    draw = ImageDraw.Draw(overview)
    for row, (role, strip) in enumerate(comparisons):
        draw.text((4, row * 100 + 3), role + ' — static restored cels', fill=(20, 20, 20))
        for d, direction in enumerate(DIRECTIONS):
            frame = strip.crop((d * 24, 0, d * 24 + 24, 24))
            overview.paste(frame.resize((72, 72), Image.Resampling.NEAREST), (d * 144 + 40, row * 100 + 24), frame.resize((72, 72), Image.Resampling.NEAREST))
            overview.paste(frame, (d * 144 + 6, row * 100 + 54), frame)
    overview.save(REVIEW / 'all_world_native_art.png')
    print(json.dumps({'authored_roles': len(authored), 'runtime_roles': len(exported), 'frames': len(roles) * 12, 'source_pngs_unchanged': len(original_hashes)}))


if __name__ == '__main__':
    main()
