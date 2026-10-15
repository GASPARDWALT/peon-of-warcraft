#!/usr/bin/env python3
"""Read-only v18 regression audit against delivered v17 source and ROM packets.

This checks preservation and compiled bytes; it is not an emulator or a claim
that a static packet check proves the visual quality of a screen.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'a3ebea8d705fc182bc36be5bd37e5cba0cb1e985'
PROTECTED = (
    'assets/world_redraw_v0217', 'gfx/world_redraw_v0217',
    'gfx/combat_heroes_v0216', 'gfx/large_masters_v0213',
    'gfx/canonical_decor_v0213', 'gfx/readable_interiors_v0212',
    'gfx/quieter_ground_v0214', 'gfx/zone_passages_v0213',
    'gfx/peon_lightning_horizontal_v0213',
    'gfx/peon_lightning_horizontal_v0213.asm', 'gfx/rock_roster_v0213',
    'maps', 'data/maps', 'data/moves', 'data/pokemon', 'data/items',
    'engine/battle', 'engine/events', 'engine/overworld',
    'engine/menus/peon_class_graphics.asm', 'gfx/user_battle_v0211/data.asm',
    'engine/menus/save.asm', 'engine/menus/delete_save.asm',
    'engine/menus/empty_sram.asm', 'engine/menus/savemenu_copytilemapatonce.asm',
    'engine/gfx/color.asm', 'engine/gfx/peon_actor_world_palettes_v0213.asm',
    'home/map_objects.asm', 'home/peon_large_world_gdma_v0215.asm',
    'home/sram.asm', 'ram', 'constants',
    'references/generated/world_redraw_v0217/source_png_hashes.json',
)
OLD_ASSEMBLY = (
    'engine/menus/peon_class_graphics.asm', 'gfx/user_battle_v0211/data.asm',
    'gfx/large_masters_v0213/graphics.asm',
    'gfx/peon_lightning_horizontal_v0213.asm',
)
OLD_PREFIXES = (
    'gfx/combat_heroes_v0216/', 'gfx/large_masters_v0213/',
    'gfx/peon_lightning_horizontal_v0213/',
)
UI_ASSEMBLY = (
    'gfx/class_portraits_v0218/graphics.asm',
    'gfx/welcome_scenes_v0218/graphics.asm',
    'gfx/selection_labels_v0218/graphics.asm',
)
MAP_EXCEPTION = 'maps/GrommashHold.asm'
PROVENANCE = 'references/generated/world_redraw_v0217/source_png_hashes.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def git_blob_id(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def tree_entries(paths):
    entries = {}
    for entry in git('ls-tree', '-r', '-z', BASELINE, '--', *paths).split(b'\0'):
        if not entry:
            continue
        meta, name = entry.split(b'\t', 1)
        mode, kind, oid = meta.decode().split()
        assert kind == 'blob', (name, kind)
        entries[name.decode()] = (mode, oid)
    return entries


def symbols(path):
    result = {}
    for line in path.read_text().splitlines():
        match = re.fullmatch(r'([0-9A-Fa-f]+):([0-9A-Fa-f]+) (\S+)', line)
        if match:
            result[match[3]] = (int(match[1], 16), int(match[2], 16))
    return result


def compiled_packets(assembly, prefixes, rom, sym):
    packets = []
    for name in assembly:
        current = None
        for line in (ROOT / name).read_text().splitlines():
            label = re.fullmatch(r'\s*([A-Za-z_][A-Za-z0-9_]*)::?\s*(?:;.*)?', line)
            if label:
                current = label[1]
            include = re.fullmatch(r'\s*INCBIN\s+"([^"]+)"\s*(?:;.*)?', line)
            if not include or (prefixes and not include[1].startswith(prefixes)):
                continue
            assert current in sym, ('Compiled packet label missing', name, current)
            data = (ROOT / include[1]).read_bytes()
            assert data, ('Empty packet', include[1])
            bank, address = sym[current]
            assert bank == 0 or 0x4000 <= address < 0x8000, (current, bank, address)
            offset = address if not bank else bank * 0x4000 + address - 0x4000
            assert offset + len(data) <= len(rom), (current, offset, len(data))
            assert rom[offset:offset + len(data)] == data, ('Compiled packet differs', current, include[1])
            packets.append({
                'label': current, 'path': include[1], 'sha256': digest(data),
                'bytes': len(data), 'bank': bank, 'address': address,
                'ROM_offset': offset, 'ROM_exact': True,
            })
    return packets


def map_exception():
    before = git('show', BASELINE + ':' + MAP_EXCEPTION)
    current = (ROOT / MAP_EXCEPTION).read_bytes()
    anchor1 = b'\tspecial PeonEyeOpening\n'
    anchor2 = b'\tspecial PeonClassSelect\n'
    assert before.count(anchor1) == before.count(anchor2) == 1
    expected = before.replace(anchor1, anchor1 + b'.ChooseMaster:\n', 1)
    expected = expected.replace(anchor2, anchor2 + b'\tiffalse .ChooseMaster\n', 1)
    assert current == expected, 'GrommashHold changes exceed the two allowed cancellation lines'
    patch = git('diff', '--no-ext-diff', '--unified=3', BASELINE, '--', MAP_EXCEPTION).decode()
    additions = [line[1:] for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++')]
    removals = [line[1:] for line in patch.splitlines() if line.startswith('-') and not line.startswith('---')]
    assert additions == ['.ChooseMaster:', '\tiffalse .ChooseMaster'] and not removals, (additions, removals)
    return {
        'path': MAP_EXCEPTION, 'before_sha256': digest(before),
        'after_sha256': digest(current), 'added_lines': additions,
        'removed_lines': removals, 'only_expected_two_lines': True,
        'reason': 'B cancels the illustrated mentor selector and returns to mentor choice; no quest skip.',
        'diff': patch,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('rom', 'sym', 'map', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--expected-rom-sha256', required=True)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    assert digest(rom) == args.expected_rom_sha256, 'The audited ROM is not the frozen final candidate'
    assert args.sym.is_file() and args.map.is_file()
    syms = symbols(args.sym)

    entries = tree_entries(PROTECTED)
    assert entries
    changed = git('diff', '--name-only', BASELINE, '--', *PROTECTED).decode().splitlines()
    assert changed == [MAP_EXCEPTION], ('Unexpected protected source changes', changed)
    exception = map_exception()
    hashes = {}
    for name, (_mode, oid) in entries.items():
        data = (ROOT / name).read_bytes()
        if name != MAP_EXCEPTION:
            assert git_blob_id(data) == oid, ('Protected baseline source differs', name)
        hashes[name] = digest(data)

    # Read provenance from Git, not from an editable current manifest.
    provenance_data = git('show', BASELINE + ':' + PROVENANCE)
    assert (ROOT / PROVENANCE).read_bytes() == provenance_data
    source_hashes = json.loads(provenance_data)['source_files']
    assert len(source_hashes) == 499
    source_tree = tree_entries(tuple(source_hashes))
    original_sources = []
    for name, sha in sorted(source_hashes.items()):
        data = (ROOT / name).read_bytes()
        assert digest(data) == sha, ('Original supplied PNG changed', name)
        assert name in source_tree and git_blob_id(data) == source_tree[name][1], ('Original PNG differs from Git baseline', name)
        original_sources.append({'path': name, 'sha256': sha, 'unchanged': True})
    supplied_count = sum(item['path'].startswith('references/characters/') for item in original_sources)
    assert supplied_count == 495

    old = compiled_packets(OLD_ASSEMBLY, OLD_PREFIXES, rom, syms)
    world = compiled_packets(('gfx/world_redraw_v0217/graphics.asm',), ('gfx/world_redraw_v0217/',), rom, syms)
    ui = compiled_packets(UI_ASSEMBLY, (), rom, syms)
    assert len(old) == 50, len(old)
    assert len(world) == 90, len(world)
    assert len(ui) == 30, len(ui)
    assert len({packet['label'] for packet in old + world + ui}) == 170

    assert len(rom) == 2097152
    assert rom[0x143] == 0xc0 and rom[0x147] == 0x10 and rom[0x148] == 6 and rom[0x149] == 3
    header = 0
    for value in rom[0x134:0x14d]:
        header = (header - value - 1) & 255
    assert header == rom[0x14d], 'Header checksum differs'
    global_checksum = (sum(rom) - rom[0x14e] - rom[0x14f]) & 0xffff
    assert global_checksum == int.from_bytes(rom[0x14e:0x150], 'big'), 'Global checksum differs'
    report = {
        'version': 'v0.2.18', 'status': 'PASS',
        'rom_sha256': digest(rom), 'sym_sha256': digest(args.sym.read_bytes()),
        'map_sha256': digest(args.map.read_bytes()), 'baseline_commit': BASELINE,
        'protected_source_count': len(entries),
        'byte_identical_protected_source_count': len(entries) - 1,
        'protected_sources': hashes, 'map_exception': exception,
        'original_source_PNG_count': len(original_sources),
        'supplied_characters_environment_PNG_count': supplied_count,
        'archived_hero_reference_PNG_count': len(original_sources) - supplied_count,
        'source_PNG_provenance_path': PROVENANCE,
        'source_PNG_provenance_sha256': digest(provenance_data),
        'source_PNGs': original_sources,
        'compiled_protected_packets': old, 'compiled_protected_packet_count': len(old),
        'compiled_world_packets': world, 'compiled_world_packet_count': len(world),
        'compiled_new_UI_packets': ui, 'compiled_new_UI_packet_count': len(ui),
        'header_and_global_checksums_exact': True, 'header_checksum': header,
        'global_checksum': global_checksum, 'CGB_only': True,
        'MBC3_timer_32KiB_RAM_battery': True,
        'ROM_bytes': len(rom), 'physical_console_tested': False,
        'scope': 'Read-only Git/source/compiled-packet/checksum regression audit. Runtime navigation and visual QA are separate reports.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({
        'status': 'PASS', 'rom_sha256': digest(rom),
        'protected_sources': len(entries), 'original_source_PNGs': len(original_sources),
        'compiled_old_packets': len(old), 'compiled_world_packets': len(world),
        'compiled_new_UI_packets': len(ui), 'map_exception_exact': True,
    }))


if __name__ == '__main__':
    main()
