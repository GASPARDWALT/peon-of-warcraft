#!/usr/bin/env python3
"""Read-only v19 preservation audit, run only against the frozen final ROM.

Preserves delivered v18 sources and checks exact linked packets. This is not
an emulator or a claim that static packet checks establish visual quality.
"""
from pathlib import Path
import argparse
import json
import re

from validate_peon_preserved_packets_v0218 import (
    compiled_packets, digest, git, git_blob_id, symbols,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'e81651eb'
PROVENANCE = 'references/generated/world_redraw_v0217/source_png_hashes.json'
PROTECTED = (
    'assets', 'gfx', 'tools', 'engine', 'home', 'data', 'maps', 'ram',
    'constants', 'audio', 'main.asm', 'references/characters', PROVENANCE,
)
NEW_PREFIXES = (
    'assets/world_readability_v0219/', 'assets/selection_v0219/',
    'assets/class_portraits_v0219/',
    'gfx/world_readability_v0219/', 'gfx/large_masters_v0219/',
    'gfx/class_portraits_v0219/',
)
NEW_ENGINE = 'engine/menus/peon_master_gallery_v0219.asm'
WORLD = 'gfx/world_readability_v0219'
LARGE = 'gfx/large_masters_v0219'
PORTRAITS = 'gfx/class_portraits_v0219'
OLD_ASSEMBLY = (
    'engine/menus/peon_class_graphics.asm', 'gfx/user_battle_v0211/data.asm',
    LARGE + '/graphics.asm', 'gfx/peon_lightning_horizontal_v0213.asm',
)
OLD_PREFIXES = (
    'gfx/combat_heroes_v0216/', 'gfx/large_masters_v0213/',
    'gfx/peon_lightning_horizontal_v0213/',
)
UI_ASSEMBLY = (
    'gfx/class_portraits_v0218/graphics.asm',
    'gfx/welcome_scenes_v0218/graphics.asm',
    'gfx/selection_labels_v0218/graphics.asm',
    PORTRAITS + '/graphics.asm',
)
WORLD_PALETTE3 = [(31, 31, 31), (25, 23, 17), (15, 9, 4), (1, 1, 1)]


def tree_entries(paths):
    entries = {}
    for item in git('ls-tree', '-r', '-z', BASELINE, '--', *paths).split(b'\0'):
        if item:
            meta, name = item.split(b'\t', 1)
            mode, kind, oid = meta.decode().split()
            assert kind == 'blob', (name, kind)
            entries[name.decode()] = (mode, oid)
    return entries


def replace_once(data, before, after):
    assert data.count(before) == 1, ('Expected unique intentional source edit', before)
    return data.replace(before, after, 1)


def intended_source_exceptions():
    """Build allowed bytes from Git, never from a current-file hash whitelist."""
    transformations = {
        'engine/overworld/peon_large_world_v0215.asm': [
            (b'INCLUDE "gfx/world_redraw_v0217/bindings.asm"', b'INCLUDE "gfx/world_readability_v0219/bindings.asm"'),
        ],
        'engine/overworld/peon_world_renderer_native_v0215.asm': [
            (b'INCLUDE "gfx/large_masters_v0213/facings.asm"', b'INCLUDE "gfx/large_masters_v0219/facings.asm"'),
        ],
        'engine/overworld/peon_large_masters_v0213.asm': [
            (b'INCLUDE "gfx/large_masters_v0213/palettes.asm"', b'INCLUDE "gfx/large_masters_v0219/palettes.asm"'),
            (b'INCLUDE "gfx/large_masters_v0213/graphics.asm"', b'INCLUDE "gfx/large_masters_v0219/graphics.asm"'),
        ],
        'engine/menus/peon_prototype.asm': [
            (b'\tfarcall PeonDrawMasterScreenV0218\n', b'\tfarcall PeonDrawMasterScreenV0219\n'),
        ],
        'engine/menus/peon_shaman_trainer.asm': [
            (b'.Exit:\n\tjp CloseSubmenu\n',
             b'.Exit:\n\t; Restore the saved menu tilemap before rebuilding its bank attributes.\n\tcall ExitAllMenus\n\t; The trainer script already closed its dialogue before opening us.\n\t; Stop the full-screen VBlank writer before native scrolling resumes.\n\tjp CloseText\n'),
        ],
        'engine/menus/peon_class_trainer.asm': [
            (b'.Exit:\n\tjp CloseSubmenu\n',
             b'.Exit:\n\t; Restore the saved menu tilemap before rebuilding its bank attributes.\n\tcall ExitAllMenus\n\t; The trainer script already closed its dialogue before opening us.\n\t; Stop the full-screen VBlank writer before native scrolling resumes.\n\tjp CloseText\n'),
        ],
        'engine/overworld/overworld.asm': [
            (b'RefreshSprites::\n\tcall .Refresh\n\tcall LoadUsedSpritesGFX\n\tret\n',
             b'RefreshSprites::\n\tcall .Refresh\n\tcall LoadUsedSpritesGFX\n\tfarcall PeonResyncMasterTileBasesV0219\n\tret\n'),
        ],
        'engine/menus/peon_selection_screens_v0218.asm': [],
        'engine/gfx/peon_actor_world_palettes_v0213.asm': [],
        'main.asm': [
            (b'INCLUDE "gfx/world_redraw_v0217/graphics.asm"', b'INCLUDE "gfx/world_readability_v0219/graphics.asm"'),
            (b'INCLUDE "gfx/class_portraits_v0218/graphics.asm"\n', b'INCLUDE "gfx/class_portraits_v0218/graphics.asm"\nINCLUDE "gfx/class_portraits_v0219/graphics.asm"\n'),
        ],
    }
    warm_upload = b'''\t; v19 world fur/bone highlights: actual ivory instead of a second tan.
\t; This is OBJ3 on PEON maps only; native battle/HUD/quest colors stay put.
\tld hl, .WarmWorldPaletteV0219
\tld de, wOBPals1 palette 3
\tld bc, 1 palettes
\tld a, BANK(wOBPals1)
\tcall FarCopyWRAM
\tld hl, .WarmWorldPaletteV0219
\tld de, wOBPals2 palette 3
\tld bc, 1 palettes
\tld a, BANK(wOBPals2)
\tcall FarCopyWRAM
'''
    master_resync = b'''; RefreshSprites can sort the three static families into a different order
; after a menu or battle. Rebind only their cached native tile bases; the
; streamed actors have per-object slots. Do not recreate objects or change
; positions, movement, facing, quest flags or saved records.
PeonResyncMasterTileBasesV0219::
\tpush af
\tldh a, [hCGB]
\tand a
\tjr z, .Return
\tld a, [wMapTileset]
\tcp TILESET_PEON
\tjr nz, .Return
\tpush bc
\tpush de
\tpush hl
\tldh a, [hMapObjectIndex]
\tpush af
\tldh a, [hObjectStructIndex]
\tpush af
\tldh a, [rWBK]
\tpush af
\tld a, BANK(wObjectStructs)
\tldh [rWBK], a
\tld bc, wObjectStructs
\tld e, 0
.Object:
\tld hl, OBJECT_SPRITE
\tadd hl, bc
\tld a, [hl]
\tcp SPRITE_PEON_SHAMAN_MASTER_LARGE
\tjr c, .Next
\tcp SPRITE_PEON_WARLOCK_MASTER_LARGE + 1
\tjr nc, .Next
\tpush af
\tld hl, OBJECT_MAP_OBJECT_INDEX
\tadd hl, bc
\tld a, [hl]
\tldh [hMapObjectIndex], a
\tld a, e
\tldh [hObjectStructIndex], a
\tpop af
\tcall GetSpriteVTile
\tjr c, .Next ; keep the existing slot if this family is not allocated
\tld hl, OBJECT_SPRITE_TILE
\tadd hl, bc
\tld [hl], a
.Next:
\tld hl, OBJECT_LENGTH
\tadd hl, bc
\tld b, h
\tld c, l
\tinc e
\tld a, e
\tcp NUM_OBJECT_STRUCTS
\tjr nz, .Object
\tpop af
\tldh [rWBK], a
\tpop af
\tldh [hObjectStructIndex], a
\tpop af
\tldh [hMapObjectIndex], a
\tpop hl
\tpop de
\tpop bc
.Return:
\tpop af
\tret

'''
    result = {}
    for path, replacements in transformations.items():
        original = git('show', BASELINE + ':' + path)
        expected = original
        for before, after in replacements:
            expected = replace_once(expected, before, after)
        if path == 'engine/menus/peon_selection_screens_v0218.asm':
            expected += b'\nINCLUDE "engine/menus/peon_master_gallery_v0219.asm"\n'
        elif path == 'engine/overworld/peon_large_masters_v0213.asm':
            anchor = b'SECTION "Peon large class master palette scope v0213", ROMX\n\n'
            expected = replace_once(expected, anchor, anchor + master_resync)
        elif path == 'engine/gfx/peon_actor_world_palettes_v0213.asm':
            anchor = b'\tjr nz, .done\n\tld hl, .FacePalette\n'
            expected = replace_once(expected, anchor, b'\tjr nz, .done\n' + warm_upload + b'\tld hl, .FacePalette\n')
            expected += b'.WarmWorldPaletteV0219:\n\tRGB 31, 31, 31\n\tRGB 25, 23, 17\n\tRGB 15, 9, 4\n\tRGB 1, 1, 1\n'
        actual = (ROOT / path).read_bytes()
        assert actual == expected, ('Source changes exceed the exact authorized integration edits', path)
        result[path] = {
            'before_sha256': digest(original), 'after_sha256': digest(actual),
            'only_expected_integration_edits': True,
            'diff': git('diff', '--no-ext-diff', '--unified=3', BASELINE, '--', path).decode(),
        }
    return result


def protected_sources():
    entries = tree_entries(PROTECTED)
    exceptions = intended_source_exceptions()
    changed = git('diff', '--name-only', BASELINE, '--', *PROTECTED).decode().splitlines()
    changed_existing = {path for path in changed if path in entries}
    assert changed_existing == set(exceptions), ('Unexpected baseline source edits', changed_existing ^ set(exceptions))
    for path in changed:
        if path not in entries:
            permitted = path.startswith(NEW_PREFIXES) or path == NEW_ENGINE or (path.startswith('tools/') and path.endswith('_v0219.py'))
            assert permitted, ('Unexpected new file under protected source roots', path)
    hashes = {}
    for path, (_mode, oid) in entries.items():
        data = (ROOT / path).read_bytes()
        if path not in exceptions:
            assert git_blob_id(data) == oid, ('Protected baseline source changed', path)
        hashes[path] = digest(data)
    assert 'maps/GrommashHold.asm' not in exceptions, 'The v18 cancellation fix must remain unchanged in v19'
    return hashes, exceptions


def original_pngs():
    raw = git('show', BASELINE + ':' + PROVENANCE)
    assert (ROOT / PROVENANCE).read_bytes() == raw
    source_hashes = json.loads(raw)['source_files']
    assert len(source_hashes) == 499
    entries = tree_entries(tuple(source_hashes))
    for path, expected in source_hashes.items():
        data = (ROOT / path).read_bytes()
        assert digest(data) == expected, ('Original PNG changed', path)
        assert path in entries and git_blob_id(data) == entries[path][1], ('Original PNG differs from independent Git baseline', path)
    assert sum(path.startswith('references/characters/') for path in source_hashes) == 495
    return source_hashes, digest(raw)


def world_packets():
    path = ROOT / WORLD / 'manifest.json'
    manifest = json.loads(path.read_text())
    roles = manifest['roles']
    assert len(roles) == 39, len(roles)
    bound = [role for role, entry in roles.items() if entry['exported_in_rom']]
    assert len(bound) == 30, bound
    result = {}
    for role, entry in roles.items():
        folder = ROOT / WORLD / role
        data = (folder / 'overworld.bin').read_bytes()
        masks = (folder / 'masks.bin').read_bytes()
        attrs = (folder / 'attrs.bin').read_bytes()
        assert (len(data), len(masks), len(attrs)) == (1728, 24, 108), role
        assert all(value <= 7 for value in attrs), role
        for frame in range(12):
            packet = data[frame*144:(frame+1)*144]
            expected_mask = sum((any(packet[tile*16:(tile+1)*16]) << tile) for tile in range(9))
            assert int.from_bytes(masks[frame*2:frame*2+2], 'little') == expected_mask, (role, frame, 'Sparse body mask differs from native pixels')
        result[role] = {
            'exported_in_rom': bool(entry['exported_in_rom']), 'frames': 12,
            'graphics_sha256': digest(data), 'masks_sha256': digest(masks),
            'attributes_sha256': digest(attrs), 'frame_bytes': 144,
            'sparse_masks_exact': True,
        }
    return manifest, result


def declared_source_hashes(node, checked):
    """Independently rehash explicit provenance paths in the new manifests."""
    if isinstance(node, dict):
        for path_key, sha_key in [('path', 'sha256'), ('source', 'source_sha256'),
                                  ('source_path', 'source_sha256'), ('source_packet', 'source_sha256')]:
            path, expected = node.get(path_key), node.get(sha_key)
            if isinstance(path, str) and isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected):
                if path.startswith(('assets/', 'gfx/', 'references/')):
                    assert digest((ROOT / path).read_bytes()) == expected, ('New manifest source digest differs', path)
                    checked[path] = expected
        for key, value in node.items():
            if isinstance(key, str) and key.startswith(('assets/', 'gfx/', 'references/')) and isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value):
                assert digest((ROOT / key).read_bytes()) == value, ('New manifest mapped digest differs', key)
                checked[key] = value
            declared_source_hashes(value, checked)
    elif isinstance(node, list):
        for value in node:
            declared_source_hashes(value, checked)


def read_linked(rom, syms, label, size):
    bank, address = syms[label]
    offset = address if not bank else bank * 0x4000 + address - 0x4000
    return rom[offset:offset+size]


def master_tables(rom, syms):
    facings = (ROOT / LARGE / 'facings.asm').read_text()
    before = git('show', BASELINE + ':gfx/large_masters_v0213/facings.asm').decode()
    def blocks(text):
        return {match[1]: match[2] for match in re.finditer(r'^(PeonLarge\w+FacingV0213):\n(.*?)(?=^PeonLarge|\Z)', text, re.M | re.S)}
    old, new = blocks(before), blocks(facings)
    assert set(new) == set(old) and len(new) == 3
    result = {}
    for name, body in new.items():
        values = []
        for line in body.splitlines():
            if not line.strip().startswith('db '):
                continue
            values += [int(value.strip().replace('$', '0x'), 0) & 255 for value in line.strip()[3:].split(',')]
        assert len(values) == 37 and values[0] == 9, name
        if 'Warrior' not in name:
            assert body == old[name], ('Original Shaman/Warlock master facing changed', name)
        else:
            # Only the palette byte may differ in a complete nine-cell body.
            old_values = []
            for line in old[name].splitlines():
                if line.strip().startswith('db '):
                    old_values += [int(value.strip().replace('$', '0x'), 0) & 255 for value in line.strip()[3:].split(',')]
            assert all(a == b for index, (a, b) in enumerate(zip(values, old_values)) if index % 4 != 3), 'Warrior cell positions/tile IDs changed'
        data = bytes(values)
        assert read_linked(rom, syms, name, len(data)) == data, ('Linked large-master facings differ', name)
        result[name] = {'bytes': len(data), 'sha256': digest(data), 'ROM_exact': True}
    palette_path = ROOT / LARGE / 'palettes.asm'
    text = palette_path.read_text()
    old_palettes = git('show', BASELINE + ':gfx/large_masters_v0213/palettes.asm').decode()
    def palette_blocks(text):
        return {match[1]: match[2] for match in re.finditer(r'^(PeonLargeMasterPalette\dV0213):\n(.*?)(?=^PeonLarge|\Z)', text, re.M | re.S)}
    old, new = palette_blocks(old_palettes), palette_blocks(text)
    for number in (7, 1, 5):
        name = f'PeonLargeMasterPalette{number}V0213'
        assert new[name] == old[name], ('Original large-master palette changed', name)
    palettes = {}
    for name, body in new.items():
        values = [int(value) for value in re.findall(r'\d+', body)]
        assert len(values) == 12 and all(0 <= value <= 31 for value in values)
        data = b''.join((r | g << 5 | b << 10).to_bytes(2, 'little') for r, g, b in zip(values[::3], values[1::3], values[2::3]))
        assert read_linked(rom, syms, name, 8) == data
        palettes[name] = {'sha256': digest(data), 'ROM_exact': True}
    expected = b''.join((r | g << 5 | b << 10).to_bytes(2, 'little') for r, g, b in WORLD_PALETTE3)
    assert read_linked(rom, syms, 'PeonApplyReadableWorldPalettesV0217.WarmWorldPaletteV0219', 8) == expected
    return {'facing_tables': result, 'palette_tables': palettes, 'PEON_world_OBJ3_exact': True,
            'Shaman_Warlock_source_and_linked_graphics_unchanged': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('rom', 'sym', 'map', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--expected-rom-sha256', required=True)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    assert digest(rom) == args.expected_rom_sha256, 'This is not the root-frozen final ROM'
    syms = symbols(args.sym)
    sources, exceptions = protected_sources()
    originals, provenance_sha = original_pngs()
    manifest, world_source_packets = world_packets()
    checked = {}
    manifests = {}
    for directory in (WORLD, LARGE, PORTRAITS):
        path = ROOT / directory / 'manifest.json'
        payload = json.loads(path.read_text())
        declared_source_hashes(payload, checked)
        manifests[directory] = digest(path.read_bytes())
    old = compiled_packets(OLD_ASSEMBLY, OLD_PREFIXES, rom, syms)
    garrosh = compiled_packets((LARGE + '/graphics.asm',), (LARGE + '/',), rom, syms)
    world = compiled_packets((WORLD + '/graphics.asm',), (WORLD + '/',), rom, syms)
    ui = compiled_packets(UI_ASSEMBLY, (), rom, syms)
    assert len(old) == 49 and len(garrosh) == 1 and len(world) == 90 and len(ui) == 39
    assert garrosh[0]['label'] == 'PeonLargeWarriorWorldV0213' and garrosh[0]['bytes'] == 144
    assert len({item['label'] for item in old + garrosh + world + ui}) == 179
    baseline_report = json.loads(git('show', BASELINE + ':references/generated/v0218/preservation_validation.json'))
    baseline_packets = {item['label']: item for item in baseline_report['compiled_protected_packets']}
    for item in old:
        assert baseline_packets[item['label']]['sha256'] == item['sha256'], ('Historical packet differs from delivered v18', item['label'])
    tables = master_tables(rom, syms)
    assert len(rom) == 2097152
    assert rom[0x143] == 0xc0 and rom[0x147] == 0x10 and rom[0x148] == 6 and rom[0x149] == 3
    header = 0
    for value in rom[0x134:0x14d]:
        header = (header - value - 1) & 255
    assert header == rom[0x14d]
    checksum = (sum(rom) - rom[0x14e] - rom[0x14f]) & 0xffff
    assert checksum == int.from_bytes(rom[0x14e:0x150], 'big')
    report = {
        'version': 'v0.2.19', 'status': 'PASS', 'baseline_commit': BASELINE,
        'rom_sha256': digest(rom), 'sym_sha256': digest(args.sym.read_bytes()),
        'map_sha256': digest(args.map.read_bytes()),
        'protected_source_count': len(sources),
        'byte_identical_protected_source_count': len(sources)-len(exceptions),
        'protected_sources': sources, 'intentional_source_exceptions': exceptions,
        'original_source_PNG_count': len(originals), 'original_source_PNGs': originals,
        'original_source_provenance_Git_sha256': provenance_sha,
        'compiled_historical_packets': old, 'compiled_historical_packet_count': len(old),
        'intentional_new_Garrosh_static_packet': garrosh,
        'compiled_world_packets': world, 'compiled_world_packet_count': len(world),
        'compiled_UI_packets': ui, 'compiled_UI_packet_count': len(ui),
        'world_source_role_count': len(world_source_packets),
        'world_compiled_bound_roles': 30, 'world_retained_unbound_roles': 9,
        'world_source_packets': world_source_packets,
        'new_manifests_SHA256': manifests, 'new_manifest_source_SHA256_verified': checked,
        'master_facing_and_palette_tables': tables,
        'header_and_global_checksums_exact': True, 'header_checksum': header,
        'global_checksum': checksum, 'ROM_bytes': len(rom), 'CGB_only': True,
        'MBC3_timer_32KiB_RAM_battery': True, 'physical_console_tested': False,
        'scope': 'Read-only preservation/source/link/checksum audit. Actual emulator navigation and visual QA are separate.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'rom_sha256': digest(rom),
                      'protected_sources': len(sources), 'source_PNGs': len(originals),
                      'historical_packets': len(old), 'new_Garrosh': len(garrosh),
                      'world_packets': len(world), 'UI_packets': len(ui)}))


if __name__ == '__main__':
    main()
