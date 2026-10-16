#!/usr/bin/env python3
"""Read-only v20 preservation/link audit against the delivered v19 Git tree.

Only explicitly listed renderer/ground/scheduling integration files may differ.
Their complete diffs are reported for review; they are not falsely called
byte-identical. All other historical sources are checked against independent
Git blob IDs. No ROM build, generator, emulator, RAM write or source edit occurs.
A PARTIAL native32 import can never produce PASS from this tool.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import re
import subprocess
import tempfile
import traceback

from validate_peon_preserved_packets_v0218 import (
    compiled_packets, digest, git, git_blob_id, symbols,
)
from validate_peon_preserved_packets_v0219 import master_tables

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '72e93e4ec611ed8badd850f1b9a4fa59f70207b1'
PROVENANCE = 'references/generated/world_redraw_v0217/source_png_hashes.json'
BASELINE_REPORT = 'references/generated/v0219/preservation_validation.json'
WORLD = 'gfx/world_native_v0220'
GROUND = 'gfx/quieter_ground_v0220'
GROUND_MANIFEST = 'references/generated/quieter_ground_v0220/manifest.json'
PROTECTED = (
    'assets', 'gfx', 'engine', 'home', 'data', 'maps', 'ram', 'constants',
    'audio', 'tools', 'macros', 'mobile', 'lib', 'references/characters',
    'main.asm', 'home.asm', 'audio.asm', 'ram.asm', 'includes.asm',
    'Makefile', 'layout.link', 'AGENTS.md', PROVENANCE,
)
# These are file-level review exceptions, not blanket "engine unchanged" claims.
# All additions/removals are embedded in the result with independent before OIDs.
ALLOWED_MODIFIED = {
    'AGENTS.md': 'Record the user-approved native32/world-ground/performance scope.',
    'main.asm': 'Switch the versioned world graphics include to the v20 packets.',
    'engine/gfx/color.asm': 'Upload the three exterior-only ground BG3 profiles.',
    'engine/gfx/dma_transfer.asm': 'Encode the exact requested HDMA block count and wait for hardware completion without writing its status register; prevent a completed transfer from restarting a spurious128-block GDMA at CGB double speed.',
    'engine/overworld/events.asm': 'Peon-only rendering/background frame scheduling; event content remains separately protected.',
    'engine/overworld/peon_large_world_v0215.asm': 'Mixed24/32 descriptor/slot/whole-body admission and direct lookup integration.',
    'engine/overworld/peon_world_renderer_native_v0215.asm': 'Skip failed actor palette searches for the four existing quest marker sprites.',
    'engine/tilesets/peon_user_environment_v0211.asm': 'Include the new exterior ground palette loader.',
    'engine/tilesets/tileset_anims.asm': 'Select the uniform-ground exterior fire backing; interior phases remain old.',
    'gfx/peon_user_environment_palettes_v0211.asm': 'Bind thirteen derived exterior palette/priority packets.',
    'gfx/peon_user_environment_v0211.asm': 'Bind thirteen derived exterior graphics/metatile/collision packets.',
    'home/init.asm': 'Select CGB double-speed CPU during startup; LCD/APU timing is a separate runtime check.',
    'home/peon_large_world_gdma_v0215.asm': 'Transfer the descriptor-selected complete9/16-tile actor frame.',
}
NEW_PREFIXES = ('assets/world_native_v0220/', WORLD+'/', GROUND+'/')
NEW_ENGINE = 'engine/tilesets/peon_uniform_ground_v0220.asm'
EXPECTED_NATIVE32 = {
    'base', 'shaman', 'warrior', 'warlock', 'sleeping', 'orc_merchant',
    'quest_peon', 'peon_worker', 'beast_handler', 'orc_guard', 'camp_guard',
    'veteran_questgiver', 'shaman_apprentice', 'troll_villager', 'troll_merchant',
    'troll_guard', 'troll_shaman', 'senjin_troll_shaman', 'senjin_chief',
}
OLD_ASSEMBLY = (
    'engine/menus/peon_class_graphics.asm', 'gfx/user_battle_v0211/data.asm',
    'gfx/large_masters_v0219/graphics.asm', 'gfx/peon_lightning_horizontal_v0213.asm',
)
OLD_PREFIXES = ('gfx/combat_heroes_v0216/', 'gfx/large_masters_v0213/',
                'gfx/large_masters_v0219/', 'gfx/peon_lightning_horizontal_v0213/')
UI_ASSEMBLY = ('gfx/class_portraits_v0218/graphics.asm',
               'gfx/welcome_scenes_v0218/graphics.asm',
               'gfx/selection_labels_v0218/graphics.asm',
               'gfx/class_portraits_v0219/graphics.asm')
GROUND_ASSEMBLY = ('gfx/peon_user_environment_v0211.asm',
                   'gfx/peon_user_environment_palettes_v0211.asm',
                   NEW_ENGINE, 'engine/tilesets/tileset_anims.asm')
SHA = re.compile(r'[0-9a-f]{64}')


def tree_entries(paths):
    result = {}
    for item in git('ls-tree', '-r', '-z', BASELINE, '--', *paths).split(b'\0'):
        if item:
            meta, name = item.split(b'\t', 1)
            mode, kind, oid = meta.decode().split()
            assert kind == 'blob', (name, kind)
            result[name.decode()] = (mode, oid)
    return result


def working_bytes(path, mode='100644'):
    item = ROOT/path
    if mode == '120000':
        assert item.is_symlink(), ('Protected symlink changed', path)
        return os.fsencode(os.readlink(item))
    assert item.is_file() and not item.is_symlink(), ('Protected source missing/replaced', path)
    return item.read_bytes()


def protected_sources():
    entries = tree_entries(PROTECTED)
    assert entries and set(ALLOWED_MODIFIED) <= set(entries)
    sources, exceptions, blobs = {}, {}, {}
    for name, (mode, oid) in sorted(entries.items()):
        actual = working_bytes(name, mode)
        same = git_blob_id(actual) == oid
        if not same:
            assert name in ALLOWED_MODIFIED, ('Protected baseline file changed', name)
            before = git('show', BASELINE+':'+name)
            patch = git('diff', '--no-ext-diff', '--no-color', '--unified=3', BASELINE, '--', name).decode()
            assert patch, ('Changed exception lacks a reviewable diff', name)
            exceptions[name] = {
                'allowed_scope': ALLOWED_MODIFIED[name], 'baseline_Git_blob': oid,
                'before_sha256': digest(before), 'after_sha256': digest(actual),
                'diff_sha256': digest(patch.encode()), 'diff': patch,
                'byte_identical': False, 'narrow_file_level_review_exception': True,
                'semantics_proved_by_this_static_audit': False,
            }
        sources[name], blobs[name] = digest(actual), oid
    # Untracked historical v16 preview PNGs are outside these protected roots.
    # Reject unrelated NEW core/assets files, including staged additions.
    new = git('ls-files', '-c', '-o', '-z', '--exclude-standard', '--', *PROTECTED).split(b'\0')
    new_paths = sorted({x.decode() for x in new if x and x.decode() not in entries})
    for name in new_paths:
        allowed = name.startswith(NEW_PREFIXES) or name == NEW_ENGINE or (
            name.startswith('tools/') and name.endswith('_v0220.py'))
        assert allowed, ('Unexpected new file under protected roots', name)
    return sources, exceptions, blobs, new_paths


def original_pngs():
    raw = git('show', BASELINE+':'+PROVENANCE)
    assert (ROOT/PROVENANCE).read_bytes() == raw
    sources = json.loads(raw)['source_files']
    assert len(sources) == 499
    assert sum(p.startswith('references/characters/') for p in sources) == 495
    entries = tree_entries(tuple(sources))
    for path, expected in sources.items():
        actual = (ROOT/path).read_bytes()
        assert digest(actual) == expected, ('Original supplied PNG changed', path)
        assert path in entries and git_blob_id(actual) == entries[path][1], ('Original PNG differs from independent v19 Git blob', path)
    return sources, digest(raw)


def checked_hash(path, expected, checked):
    assert isinstance(path, str) and SHA.fullmatch(expected), (path, expected)
    item = Path(path)
    if item.is_absolute():
        assert item.is_relative_to(ROOT), ('Provenance outside the immutable repository copies', path)
        item = item.relative_to(ROOT)
    assert str(item).startswith(('assets/', 'gfx/', 'references/', 'tools/', 'engine/'))
    actual = (ROOT/item).read_bytes()
    assert digest(actual) == expected, ('Declared source/output digest differs', str(item))
    checked[str(item)] = expected


def declared_hashes(node, checked):
    if isinstance(node, dict):
        pairs = (
            ('path', 'sha256'), ('source', 'source_sha256'), ('input', 'input_sha256'),
            ('output', 'output_sha256'), ('binary', 'binary_sha256'),
            ('source_path', 'source_sha256'), ('source_packet', 'source_sha256'),
            ('source_png', 'source_sha256'), ('source_original_copy', 'source_png_sha256'),
        )
        for pathkey, shakey in pairs:
            path, expected = node.get(pathkey), node.get(shakey)
            if isinstance(path, str) and isinstance(expected, str) and SHA.fullmatch(expected):
                checked_hash(path, expected, checked)
        for key, value in node.items():
            if isinstance(key, str) and key.startswith(('assets/', 'gfx/', 'references/', 'tools/', 'engine/')) and isinstance(value, str) and SHA.fullmatch(value):
                checked_hash(key, value, checked)
            declared_hashes(value, checked)
    elif isinstance(node, list):
        for value in node:
            declared_hashes(value, checked)


def linked(rom, syms, label, length):
    assert label in syms, ('Missing linked symbol', label)
    bank, address = syms[label]
    assert bank == 0 or 0x4000 <= address < 0x8000, (label, bank, address)
    offset = address if bank == 0 else bank*0x4000+address-0x4000
    assert length > 0 and offset+length <= len(rom)
    return rom[offset:offset+length]


def encode_rows(rows, size):
    assert len(rows) == size and all(len(row) == size for row in rows)
    assert set(''.join(rows)) <= set('.123')
    result = bytearray()
    for ty in range(0, size, 8):
        for tx in range(0, size, 8):
            for row in rows[ty:ty+8]:
                values = ['.123'.index(c) for c in row[tx:tx+8]]
                result.extend((sum((v&1) << (7-x) for x,v in enumerate(values)),
                               sum((v>>1) << (7-x) for x,v in enumerate(values))))
    return bytes(result)


def world_packets(rom, syms, checked):
    manifest_path = ROOT/WORLD/'manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    assert manifest['version'] == 'v0.2.20' and manifest['status'] == 'PASS', ('Partial native32 import cannot be audited as complete', manifest.get('status'))
    assert not manifest['missing_native32_roles'] and not manifest['partial_import_explicit']
    assert set(manifest['native32_roles']) == EXPECTED_NATIVE32, ('Missing/extra native32 actors', set(manifest['native32_roles']) ^ EXPECTED_NATIVE32)
    assert len(manifest['roles']) == 39
    declared_hashes(manifest, checked)
    prior_bytes = git('show', BASELINE+':gfx/world_readability_v0219/manifest.json')
    prior = json.loads(prior_bytes)
    assert manifest['prior_manifest_sha256'] == digest(prior_bytes)
    assert manifest['effective_world_palettes_rgb555'] == prior['effective_world_palettes_rgb555'], 'Existing actor palettes changed'
    assert len(manifest['runtime_bindings']) == len(prior['runtime_bindings'])
    for before, after in zip(prior['runtime_bindings'], manifest['runtime_bindings']):
        assert all(after[k] == before[k] for k in ('sprite', 'role', 'palette_index')), ('Native actor binding changed', before, after)
        expected_palette = before['palette_index'] | (0x20 if after['role'] in EXPECTED_NATIVE32 else 0)
        assert after['descriptor_palette_byte'] == expected_palette, ('Unexpected native32 descriptor flag', after)
    art = {}
    source_paths = manifest['source_json_sha256']
    assert set(source_paths) == {'assets/world_native_v0220/'+name+'.json' for name in ('heroes','orc_npcs','trolls')}
    for name in sorted(source_paths):
        path = ROOT/name
        payload = json.loads(path.read_bytes());declared_hashes(payload, checked)
        for role, record in payload.get('roles', {}).items():
            assert role not in art, ('Duplicate native art source role', role)
            art[role] = record
    native32_art = {role for role, record in art.items() if record.get('frame_size', record.get('dimensions',[24])[0]) == 32}
    assert native32_art == EXPECTED_NATIVE32
    assert set(art)-EXPECTED_NATIVE32 <= {'warrior_trainer'}, ('Unexpected source family outside reviewed native32 scope',set(art)-EXPECTED_NATIVE32)
    # Verification reports may have their own .roles summaries; they are not
    # additional artwork sources and must not override the three pinned inputs.
    for path in sorted((ROOT/'assets/world_native_v0220').glob('*verification.json')):
        declared_hashes(json.loads(path.read_bytes()), checked)
    packets = compiled_packets((WORLD+'/graphics.asm',), (WORLD+'/',), rom, syms)
    bound = {role for role, r in manifest['roles'].items() if r['exported_in_rom']}
    assert len(bound) == 30 and len(packets) == len(bound)*3
    actual_labels = {p['label'] for p in packets}
    results, retained = {}, {}
    for role, record in sorted(manifest['roles'].items()):
        size = record['frame_size'];assert size in (24,32)
        tiles, frame_bytes = (size//8)**2, size*size//4
        folder = ROOT/WORLD/role
        data, masks, attrs = [(folder/name).read_bytes() for name in ('overworld.bin','masks.bin','attrs.bin')]
        assert (len(data),len(masks),len(attrs)) == (12*frame_bytes,24,12*tiles), role
        assert set(attrs) <= {1,2,3,5,6,7}, ('Reserved world palette', role)
        assert digest(data) == record['output_sha256'] and digest(masks) == record['mask_sha256'] and digest(attrs) == record['attrs_sha256']
        assert digest((folder/'overworld.png').read_bytes()) == record['strip_sha256']
        frames = []
        for frame in range(12):
            cel = data[frame*frame_bytes:(frame+1)*frame_bytes]
            expected_mask = sum(1 << t for t in range(tiles) if any(cel[t*16:(t+1)*16]))
            assert int.from_bytes(masks[frame*2:frame*2+2],'little') == expected_mask, (role,frame,'False sparse mask')
            frames.append({'pose_index':frame,'sha256':digest(cel),'active_tiles':expected_mask.bit_count()})
        if size == 32:
            assert role in art and not record['preserved_v0219_bytes']
            source = art[role];expected_data, expected_attrs = bytearray(), bytearray()
            for direction in ('front','back','left','right'):
                keys = [source['views'][direction]]+source['walk'][direction]
                assert len(keys) == 3 and len({tuple(key) for key in keys}) == 3, (role,direction,'Missing actual gait keys')
                idle_attrs = source.get('attributes',{}).get(direction,[source['palette']]*16)
                gait_attrs = source.get('walk_attributes',{}).get(direction,[idle_attrs,idle_attrs])
                for cel,attributes in zip(keys,[idle_attrs]+gait_attrs):
                    assert len(attributes)==16
                    expected_data.extend(encode_rows(cel,32));expected_attrs.extend(attributes)
            assert data == bytes(expected_data) and attrs == bytes(expected_attrs), (role,'Native32 source cels/attributes do not match packets')
        else:
            assert role not in EXPECTED_NATIVE32 and record['preserved_v0219_bytes'], ('Unexpected24px humanoid fallback', role)
            proof = {}
            for name in ('overworld.bin','masks.bin','attrs.bin','overworld.png'):
                oldpath = 'gfx/world_readability_v0219/'+role+'/'+name
                old = git('show',BASELINE+':'+oldpath);current=(folder/name).read_bytes()
                assert current == old, ('Approved native24 actor changed',role,name)
                proof[name]={'sha256':digest(current),'baseline_Git_blob':git_blob_id(old),'byte_exact':True}
            retained[role]=proof
        layout = None
        if role in bound:
            assert {record['label'],record['masks_label'],record['attrs_label']} <= actual_labels
            frame_bank, frame_address = syms[record['label']]
            mask_bank, mask_address = syms[record['masks_label']]
            attr_bank, attr_address = syms[record['attrs_label']]
            assert frame_address % 16 == 0 and frame_address + len(data) <= 0x8000, (role, 'Frame packet is unaligned or crosses a ROM bank')
            # The existing descriptor has independent frame/mask bank bytes.
            # Only masks and attributes share a bank and have a fixed +24 offset.
            assert attr_bank == mask_bank and attr_address == mask_address + 24, (role, 'Mask/attribute ABI changed')
            assert attr_address + len(attrs) <= 0x8000, (role, 'Mask/attribute packet crosses a ROM bank')
            layout = {'frame_bank': frame_bank, 'frame_address': frame_address,
                      'mask_bank': mask_bank, 'mask_address': mask_address,
                      'attributes_bank': attr_bank, 'attributes_address': attr_address,
                      'frame_and_mask_banks_may_differ': True,
                      'mask_attributes_same_bank_and_contiguous': True}
        results[role]={'frame_size':size,'frames':12,'source_sha256':digest(data),'mask_sha256':digest(masks),'attributes_sha256':digest(attrs),'exported_in_rom':role in bound,'frames_proof':frames,'source_and_packet_exact':True,'compiled_layout':layout}
    assert {'boar','kolkar_archer','kolkar_raider'} <= set(retained), 'Approved Boar/Kolkar protection is mandatory'
    binding_bank,binding_address = syms['PeonLargeWorldBindingsV0215'];pointers=[0]*256
    for ordinal,binding in enumerate(manifest['runtime_bindings']):
        role=manifest['roles'][binding['role']];sprite=binding['sprite_id'];bank,address=syms[role['label']];mbank,maddress=syms[role['masks_label']]
        expected=bytes((sprite,role['descriptor_palette_byte'],bank))+address.to_bytes(2,'little')+bytes((mbank,))+maddress.to_bytes(2,'little')
        label_offset=ordinal*8
        assert linked(rom,syms,'PeonLargeWorldBindingsV0215',label_offset+8)[label_offset:]==expected
        assert not pointers[sprite];pointers[sprite]=binding_address+label_offset
    assert linked(rom,syms,'PeonLargeWorldBindingsV0215',len(manifest['runtime_bindings'])*8+1)[-1:] == b'\xff'
    assert syms['PeonLargeWorldDescriptorPointersV0220'][0]==binding_bank
    assert linked(rom,syms,'PeonLargeWorldDescriptorPointersV0220',512)==b''.join(p.to_bytes(2,'little')for p in pointers)
    for i,role in enumerate(('base','shaman','warrior','warlock')):
        record=manifest['roles'][role];bank,address=syms[record['label']];mbank,maddress=syms[record['masks_label']]
        expected=bytes((1,record['descriptor_palette_byte'],bank))+address.to_bytes(2,'little')+bytes((mbank,))+maddress.to_bytes(2,'little')
        assert linked(rom,syms,'PeonLargeWorldHeroBindingsV0215',(i+1)*8)[i*8:]==expected
    assert linked(rom,syms,'PeonLargeWorldWalkFlagsV0220',256)==bytes(manifest['walk_flags']['flags'])
    return manifest, packets, results, retained


def ground_packets(rom, syms, checked):
    payload=(ROOT/GROUND_MANIFEST).read_bytes();manifest=json.loads(payload)
    assert manifest['version']=='v0.2.20' and manifest['result']=='PASS' and len(manifest['maps'])==13
    declared_hashes(manifest,checked)
    packets=compiled_packets(GROUND_ASSEMBLY,(GROUND+'/',),rom,syms)
    assert len(packets)==54 and sum(p['path'].endswith('.2bpp.lz')for p in packets)==13
    constants={m[1]:int(m[2],16)for m in re.finditer(r'^DEF COLL_(\w+)\s+EQU \$([0-9a-fA-F]+)',(ROOT/'constants/collision_constants.asm').read_text(),re.M)}
    headers=(ROOT/'data/tilesets/peon_user_environment_headers_v0211.asm').read_text();expected_headers=bytearray();header_records={}
    pair=re.compile(r'^\s*dba ([^\n]+)\n\s*dw ([^\n]+)',re.M)
    for index,match in enumerate(pair.finditer(headers)):
        names=[s.strip()for s in match[1].split(',')];words=[s.strip()for s in match[2].split(',')];assert len(names)==len(words)==3
        row=bytearray()
        for label in names:
            bank,address=syms[label];row.extend(bytes((bank,))+address.to_bytes(2,'little'))
        for label in words:row.extend(syms[label][1].to_bytes(2,'little'))
        assert len(row)==15;expected_headers.extend(row);header_records[names[0]]={'table_index':index,'label_names':names+words,'bytes_sha256':digest(row)}
    assert len(header_records)==18 and linked(rom,syms,'PeonUserEnvironmentHeaders',len(expected_headers))==expected_headers
    results={}
    with tempfile.TemporaryDirectory(prefix='peon-v20-preservation-ground-')as temporary:
        tmp=Path(temporary)
        for item in manifest['maps']:
            name=item['map'];folder=ROOT/GROUND;data={s:(folder/(name+s)).read_bytes()for s in item['output_sha256']}
            for suffix,expected in item['output_sha256'].items():assert digest(data[suffix])==expected,(name,suffix)
            # The input packet is in the independent v19 Git tree, not a new report.
            before=git('show',BASELINE+':'+item['input_packet']+'/'+name+'_coll.asm')
            assert data['_coll.asm']==before,(name,'Collision source changed')
            values=bytearray()
            for line in data['_coll.asm'].decode().splitlines():
                m=re.fullmatch(r'\s*peon_user_tilecoll\s+([^;]+)(?:;.*)?',line)
                if not line.strip() or line.lstrip().startswith(';'):continue
                assert m,(name,'Unsupported collision directive',line)
                cells=[c.strip()for c in m[1].split(',')];assert len(cells)==4
                values.extend(constants[c]for c in cells)
            label='PeonUserEnv'+name+'Coll'
            assert linked(rom,syms,label,len(values))==values,(name,'Compiled collision bytes changed')
            compressed=tmp/(name+'.lz');raw=tmp/(name+'.bin');compressed.write_bytes(data['.2bpp.lz'])
            subprocess.run([str(ROOT/'tools/lzcompress'),'-u',str(compressed),str(raw)],check=True,capture_output=True)
            assert raw.read_bytes()==data['.2bpp'],(name,'Compiled graphics decompression differs')
            assert 'PeonUserEnv'+name+'GFX' in header_records,(name,'Ground packet is not bound to the native map header')
            assert item['map_blocks_sha256_unchanged']==digest(git('show',BASELINE+':maps/'+name+'.blk'))
            assert item['map_script_sha256_unchanged']==digest(git('show',BASELINE+':maps/'+name+'.asm'))
            assert item['collision_rows_byte_exact'] and item['native_priority_per_world_8x8_cell_exact']
            results[name]={'compressed_ROM_exact':True,'decompressed_native_2bpp_exact':True,'collision_Git_and_ROM_exact':True,'map_blocks_and_events_Git_exact':True,'native_header_entry_exact':header_records['PeonUserEnv'+name+'GFX'],'compiled_collision_sha256':digest(values),'native_patterns':len(data['.2bpp'])//16}
    return packets,results,digest(payload)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','sym','map','output'):parser.add_argument('--'+name,required=True,type=Path)
    for name in ('rom','sym','map'):parser.add_argument('--expected-'+name+'-sha256',required=True)
    args=parser.parse_args();report={'version':'v0.2.20','status':'FAIL','baseline_commit':BASELINE}
    try:
        rom=args.rom.read_bytes()
        for name in ('rom','sym','map'):
            actual=digest(getattr(args,name).read_bytes());expected=getattr(args,'expected_'+name+'_sha256')
            assert SHA.fullmatch(expected) and actual==expected,('Not the root-frozen final artifact',name,actual,expected)
            report[name+'_sha256']=actual
        syms=symbols(args.sym)
        highest_rom_bank=max(bank for bank,address in syms.values() if address < 0x8000)
        assert highest_rom_bank <= 0x7f, ('Linked ROM exceeds128 banks/2MiB', highest_rom_bank)
        report.update(highest_ROM_bank=highest_rom_bank,ROM_banks=128,validator_source_sha256=digest(Path(__file__).read_bytes()))
        sources,exceptions,blobs,new_paths=protected_sources();originals,provenance=original_pngs();checked={}
        manifest,world,roles,retained=world_packets(rom,syms,checked)
        ground,ground_maps,ground_manifest_sha=ground_packets(rom,syms,checked)
        old=compiled_packets(OLD_ASSEMBLY,OLD_PREFIXES,rom,syms);ui=compiled_packets(UI_ASSEMBLY,(),rom,syms)
        assert len(old)==50 and len(ui)==39
        baseline=json.loads(git('show',BASELINE+':'+BASELINE_REPORT));assert baseline['status']=='PASS'
        previous={p['label']:p for key in ('compiled_historical_packets','intentional_new_Garrosh_static_packet','compiled_UI_packets')for p in baseline[key]}
        assert len(previous)==89
        for packet in old+ui:assert previous[packet['label']]['sha256']==packet['sha256'],('Historical compiled packet differs from delivered v19',packet['label'])
        tables=master_tables(rom,syms)
        assert len(rom)==2097152 and rom[0x143]==0xc0 and rom[0x147:0x14a]==bytes((0x10,6,3))
        header=0
        for value in rom[0x134:0x14d]:header=(header-value-1)&255
        checksum=(sum(rom)-rom[0x14e]-rom[0x14f])&0xffff
        assert header==rom[0x14d] and checksum==int.from_bytes(rom[0x14e:0x150],'big')
        report.update(status='PASS',protected_source_count=len(sources),byte_identical_protected_source_count=len(sources)-len(exceptions),protected_sources=sources,protected_baseline_Git_blobs=blobs,intentional_source_exceptions=exceptions,new_allowed_source_paths=new_paths,original_source_PNG_count=len(originals),original_source_PNGs=originals,original_source_provenance_Git_sha256=provenance,compiled_historical_packets=old,compiled_historical_packet_count=len(old),compiled_UI_packets=ui,compiled_UI_packet_count=len(ui),compiled_world_packets=world,compiled_world_packet_count=len(world),world_source_role_count=len(roles),world_native32_roles=sorted(EXPECTED_NATIVE32),world_compiled_bound_roles=sum(r['exported_in_rom']for r in manifest['roles'].values()),world_source_packets=roles,approved_native24_packets_byte_exact_from_v19_Git=retained,Boar_and_Kolkar_independent_Git_and_compiled_ROM_exact=True,compiled_ground_packets=ground,compiled_ground_packet_count=len(ground),compiled_ground_maps=ground_maps,new_manifests_SHA256={WORLD+'/manifest.json':digest((ROOT/WORLD/'manifest.json').read_bytes()),GROUND_MANIFEST:ground_manifest_sha},new_manifest_source_SHA256_verified=checked,master_facing_and_palette_tables=tables,header_and_global_checksums_exact=True,header_checksum=header,global_checksum=checksum,ROM_bytes=len(rom),CGB_only=True,MBC3_timer_32KiB_RAM_battery=True,physical_console_tested=False,scope='Read-only independent v19 Git/source/compiled-packet/checksum audit. Listed renderer/ground/scheduling source diffs are file-level reviewed exceptions, not an assertion of unchanged engine semantics. Runtime input, timing and visual QA are separate reports.')
    except Exception as error:
        report['error']=repr(error);report['traceback']=traceback.format_exc()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report[key]for key in ('status','rom_sha256','protected_source_count','original_source_PNG_count','compiled_historical_packet_count','compiled_UI_packet_count','compiled_world_packet_count','compiled_ground_packet_count','error')if key in report}))
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
