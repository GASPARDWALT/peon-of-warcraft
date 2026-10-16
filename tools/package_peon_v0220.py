#!/usr/bin/env python3
"""Package the exact validated native24/32 ROM, without regenerating artwork."""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path
import re
import zipfile

from PIL import Image
import package_peon_v0219 as retained
from import_peon_world_native_v0220 import decode, render, active_mask

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'v0.2.20'
BASE = 'peon_of_warcraft_v0_2_20'
WORLD = ROOT/'gfx/world_native_v0220'
GROUND = ROOT/'gfx/quieter_ground_v0220'
RELEASE = ROOT/'releases'/VERSION
sha, require, checked_file = retained.sha, retained.require, retained.checked_file
json_bytes = retained.json_bytes
EXPECTED_NATIVE32 = {
    'base', 'shaman', 'warrior', 'warlock', 'sleeping',
    'orc_merchant', 'quest_peon', 'peon_worker', 'beast_handler', 'orc_guard',
    'camp_guard', 'veteran_questgiver', 'shaman_apprentice',
    'troll_villager', 'troll_merchant', 'troll_guard', 'senjin_chief',
    'troll_shaman', 'senjin_troll_shaman',
}
EXPECTED_GROUND = {
    'PeonOpening', 'TheDen', 'ValleyOfTrials', 'PeonValleyCrossroads',
    'PeonHanazuaCamp', 'PeonSarkothBasin', 'PeonCaveApproach', 'PeonValleyExit',
    'DurotarRoad', 'SenjinVillage', 'RazorHill', 'OrgrimmarGate', 'BurningBladeCavern',
}


def rehash_sources(manifest):
    """Recheck declarations against source bytes, not just a prior PASS flag."""
    checked = {}

    def source(path, digest):
        require(isinstance(path, str) and isinstance(digest, str)
                and re.fullmatch(r'[0-9a-f]{64}', digest), 'Malformed source SHA declaration')
        resolved = retained.source_path(path)
        require(resolved.is_relative_to(ROOT), 'Source escapes repository: '+path)
        key = resolved.relative_to(ROOT).as_posix()
        require(key not in checked or checked[key]['sha256'] == digest,
                'Conflicting source SHA declarations: '+key)
        if key not in checked:
            data = checked_file(resolved, digest)
            checked[key] = dict(sha256=digest, bytes=len(data))

    for name in ('source_files_sha256', 'source_json_sha256',
                 'source_reference_files_sha256', 'preserved_v0219_files_sha256'):
        declared = manifest.get(name)
        require(isinstance(declared, dict) and declared, 'Missing declared source map: '+name)
        for path, digest in declared.items():
            source(path, digest)
    require(len(manifest['source_files_sha256']) == 499, 'Expected all499 original PNG declarations')
    expected_json = {'assets/world_native_v0220/'+pack+'.json' for pack in ('heroes', 'orc_npcs', 'trolls')}
    require(set(manifest['source_json_sha256']) == expected_json, 'Incomplete native32 source JSON set')
    for role in manifest['roles'].values():
        source(role['source_packet'], role['source_sha256'])
        for reference in role.get('design_references', []):
            source(reference['source'], reference['source_sha256'])
    return checked


def compiled_world_proof(validation, manifest_data, roles):
    """Require the final ROM report, rejecting partial pilot proofs."""
    bound = {role for role, record in roles.items() if record['exported_in_rom']}
    candidates = []
    for test in validation.get('tests', {}).values():
        if not isinstance(test, dict) or not test.get('report'):
            continue
        path = retained.source_path(test['report'])
        report_data = path.read_bytes()
        report = json.loads(report_data)
        proof = report.get('canonical_native_packets')
        if not isinstance(proof, dict):
            continue
        require(retained.passed(report) and report.get('rom_sha256') == validation.get('rom_sha256'),
                'Native world report is not PASS for the final ROM')
        require(test.get('report_sha256', sha(report_data)) == sha(report_data), 'Native world report changed')
        require(proof.get('status') == 'PASS'
                and proof.get('manifest_sha256') == sha(manifest_data)
                and proof.get('graphics_sha256') == sha((WORLD/'graphics.asm').read_bytes()),
                'Compiled native world proof differs from current packets')
        require(not proof.get('partial_import_explicitly_allowed')
                and not proof.get('frozen_shaman_only_pilot'), 'Pilot world proof cannot be released')
        for name in ('ordinary_and_hero_descriptors_exact', 'all_256_descriptor_pointers_exact',
                     'compiled_walk_flags_boolean_and_manifest_exact'):
            require(proof.get(name) is True, 'Missing compiled native world proof: '+name)
        compiled = {role: record for role, record in proof.get('roles', {}).items()
                    if record.get('ROM_exact') is True}
        require(set(compiled) == bound, 'Final report must verify exactly all30 compiled world families')
        for role, record in compiled.items():
            require(record.get('frame_size') == roles[role]['frame_size']
                    and record.get('packet_sha256') == roles[role]['output_sha256']
                    and record.get('all_frame_alpha_and_RGB555_exact') is True,
                    'Compiled world role proof differs: '+role)
        require(sum(record['frame_size'] == 32 for record in compiled.values()) == 15,
                'Expected15 compiled native32 families; the other4 native32 families are unbound')
        candidates.append(dict(source=str(path), sha256=sha(report_data),
                               compiled_families=30, compiled_packets=90))
    require(candidates, 'Missing final native24/32 compiled-packet validator report')
    return candidates


def add_tree(files, folder, prefix):
    result = []
    for path in sorted(folder.rglob('*')):
        if path.is_file():
            target = prefix + path.relative_to(folder).as_posix()
            require(target not in files, 'Duplicate asset: '+target)
            files[target] = path.read_bytes()
            result.append(target)
    return result


def world_assets(files, validation):
    payload = (WORLD/'manifest.json').read_bytes()
    manifest = json.loads(payload)
    require(manifest['status'] == 'PASS' and manifest['version'] == VERSION,
            'Partial native world import cannot be released')
    roles = manifest['roles']
    require(not manifest.get('missing_native32_roles'), 'Native32 source roles are incomplete')
    prior_data = (ROOT/'gfx/world_readability_v0219/manifest.json').read_bytes()
    prior = json.loads(prior_data)
    require(set(roles) == set(prior['roles']) and manifest.get('prior_manifest_sha256') == sha(prior_data),
            'Approved historical world contract differs')
    require({role for role, record in roles.items() if record.get('frame_size') == 32} == EXPECTED_NATIVE32
            and set(manifest.get('native32_roles', [])) == EXPECTED_NATIVE32,
            'Expected all19 intended native32 families;24px placeholders cannot be released')
    bound = {role for role, record in roles.items() if record['exported_in_rom']}
    contract = dict(manifest_sha256=sha(payload), role_families=len(roles),
                    bound_families=len(bound), bound_packets=len(bound)*3)
    require(len(roles) == 39 and len(bound) == 30, 'Unexpected world binding contract')
    require(validation['world_asset_contract'] == contract, 'Validation world contract differs')
    checked_sources = rehash_sources(manifest)
    proofs = compiled_world_proof(validation, payload, roles)
    declarations = re.findall(r'\bINCBIN\s+"([^"]+)"', (WORLD/'graphics.asm').read_text())
    expected_bound = {'gfx/world_native_v0220/'+role+'/'+name for role in bound
                      for name in ('overworld.bin', 'masks.bin', 'attrs.bin')}
    require(len(declarations) == 90 and len(set(declarations)) == 90 and set(declarations) == expected_bound,
            'Active world graphics must bind exactly90 declared native packets')
    verified_payloads = {'manifest.json': payload}
    for role, record in roles.items():
        size = record['frame_size']
        require(size in (24,32), 'Invalid native frame size')
        frame_bytes, tiles = size*size//4, (size//8)**2
        require(record.get('dimensions_after') == [size,size]
                and record.get('bytes_per_frame') == frame_bytes
                and record.get('tiles_per_frame') == tiles
                and record.get('attribute_bytes_per_frame') == tiles
                and record.get('mask_bytes_per_frame') == 2, 'Native dimensions/stride contract differs: '+role)
        palette = record['palette_index']
        require(type(palette) is int and palette in (1,2,3,5,6,7)
                and record.get('descriptor_palette_byte') == (palette | (0x20 if size == 32 else 0)),
                'Native descriptor size/palette flag differs: '+role)
        folder = WORLD/role
        require(retained.source_path(record['output_packet']) == folder/'overworld.bin',
                'World packet path differs from its role')
        packet = checked_file(folder/'overworld.bin', record['output_sha256'], frame_bytes*12)
        masks = checked_file(folder/'masks.bin', record['mask_sha256'], 24)
        attrs = checked_file(folder/'attrs.bin', record['attrs_sha256'], tiles*12)
        require(set(attrs) <= {1,2,3,5,6,7}, 'Reserved world palette')
        strip = Image.new('RGBA',(size*4,size*3))
        for frame in range(12):
            image = decode(packet[frame*frame_bytes:(frame+1)*frame_bytes],size)
            require(active_mask(image) == int.from_bytes(masks[frame*2:frame*2+2],'little'),
                    'Native sparse mask differs: '+role)
            strip.paste(render(image, attrs[frame*tiles:(frame+1)*tiles]),
                        (frame//3*size,frame%3*size))
        native = checked_file(folder/'overworld.png',record['strip_sha256'])
        actual = retained.png(native,(size*4,size*3),rgba=True)
        require(actual.tobytes() == strip.tobytes(), 'Native strip decode differs: '+role)
        if role not in EXPECTED_NATIVE32:
            require(size == 24 and record['preserved_v0219_bytes'] is True,
                    'Approved native24 family cannot be replaced: '+role)
            for name in ('overworld.bin','masks.bin','attrs.bin','overworld.png'):
                require((folder/name).read_bytes() == (ROOT/'gfx/world_readability_v0219'/role/name).read_bytes(),
                        'Approved native24 asset changed: '+role)
        else:
            require(size == 32 and record['preserved_v0219_bytes'] is False
                    and record['gait_cels_declared'] is True, 'Missing true native32 gait')
            for direction in range(4):
                poses = {packet[(direction*3+pose)*frame_bytes:(direction*3+pose+1)*frame_bytes]
                         for pose in range(3)}
                require(len(poses) == 3, 'Native32 idle/two gait cels are not distinct: '+role)
        source = record['source_packet']
        checked_file(source,record['source_sha256'])
        verified_payloads.update({role+'/'+name: data for name,data in
                                  (('overworld.bin',packet),('masks.bin',masks),('attrs.bin',attrs),('overworld.png',native))})
    require(roles['boar']['preserved_v0219_bytes'], 'Approved Boar must remain byte exact')
    packet_files = add_tree(files,WORLD,'assets/active_world/')
    for name, data in verified_payloads.items():
        require(files['assets/active_world/'+name] == data, 'World asset changed during packaging: '+name)
    sources = add_tree(files,ROOT/'assets/world_native_v0220','assets/world_design_sources/')
    for path, record in checked_sources.items():
        if path.startswith('assets/world_native_v0220/'):
            member = 'assets/world_design_sources/'+path.removeprefix('assets/world_native_v0220/')
            require(member in files and sha(files[member]) == record['sha256'],
                    'Design source changed during packaging: '+path)
    files['assets/active_world_source_provenance.json'] = json_bytes(dict(
        version=VERSION, source_files_rehashed=checked_sources, compiled_world_proofs=proofs,
        original_PNGs_unchanged=499, source_conversion='Explicitly lossy; source JSONs declare authored native gait.'))
    return dict(contract=contract, files=packet_files, sources=sources,
                source_files_rehashed_count=len(checked_sources), compiled_world_proofs=proofs,
                native32_roles=sorted(r for r,v in roles.items() if v['frame_size']==32),
                native24_roles=sorted(r for r,v in roles.items() if v['frame_size']==24))


def ground_assets(files):
    path = ROOT/'references/generated/quieter_ground_v0220/manifest.json'
    manifest = json.loads(path.read_bytes())
    require(manifest.get('version') == VERSION and manifest.get('result') == 'PASS',
            'Uniform ground source import is not v20 PASS')
    require(len(manifest['maps']) == 13 and {r['map'] for r in manifest['maps']} == EXPECTED_GROUND,
            'Expected13 unique uniform ground maps')
    for source, digest in manifest['protected_input_files_sha256'].items():
        checked_file(source,digest)
    stencil = manifest['source_stencil']
    checked_file(stencil['source'],stencil['source_sha256'])
    original_sources = json.loads(retained.source_path(manifest['source_hash_manifest']).read_bytes())['source_files']
    require(len(original_sources) == 499, 'Expected499 protected original ground/reference PNGs')
    for source,digest in original_sources.items():
        checked_file(source,digest)
    expected_suffixes = {'.2bpp','.2bpp.lz','_meta.bin','_palmap.bin','_priority.bin','_coll.asm'}
    fire = checked_file(manifest['exterior_fire']['output'],manifest['exterior_fire']['output_sha256'],192)
    prior_fire = checked_file(manifest['exterior_fire']['input'],manifest['exterior_fire']['input_sha256'],192)
    phases = manifest['exterior_fire']['phase_reports']
    require([p['phase'] for p in phases] == [0,1,2], 'Incomplete exterior fire phases')
    for phase in phases:
        source = checked_file(phase['source'],phase['source_sha256'])
        alpha = retained.png(source,(16,16),rgba=True).getchannel('A')
        number = phase['phase']
        before = decode(prior_fire[number*64:(number+1)*64],16)
        after = decode(fire[number*64:(number+1)*64],16)
        for y in range(16):
            for x in range(16):
                expected = before.getpixel((x,y)) if alpha.getpixel((x,y)) else 1
                require(after.getpixel((x,y)) == expected, 'Exterior fire changed opaque source indices')
    verified_payloads = {'fire_frames_world.bin':fire}
    for record in manifest['maps']:
        require(set(record['output_sha256']) == expected_suffixes, 'Incomplete native ground packet')
        require(record['native_pattern_capacity'] == 216 and 0 < record['unique_patterns'] <= 216,
                'Uniform ground exceeds the native216-pattern allocation')
        for suffix,digest in record['output_sha256'].items():
            data = checked_file(GROUND/(record['map']+suffix),digest)
            verified_payloads[record['map']+suffix] = data
            if suffix == '.2bpp':
                require(len(data) == 216*16 and data[:64] == fire[:64], 'Ground phase0/216pattern bytes differ')
            elif suffix == '_palmap.bin':
                require(len(data) == 128, 'Ground palette map must be128bytes')
            elif suffix == '_priority.bin':
                require(len(data) == 32, 'Ground priority map must be32bytes')
            elif suffix == '_meta.bin':
                require(len(data)%16 == 0 and not any(96 <= tile < 128 or tile >= 248 for tile in data),
                        'Ground metatile uses a reserved font/VRAM tile')
            elif suffix == '_coll.asm':
                require(data == (ROOT/'gfx/quieter_ground_v0214'/(record['map']+suffix)).read_bytes(),
                        'Uniform ground collision bytes changed')
        require(record['collision_rows_byte_exact'] is True and record['source_opaque_pixels_preserved'],
                'Ground import must preserve collisions and opaque supplied props')
        checked_file(ROOT/'maps'/(record['map']+'.blk'), record['map_blocks_sha256_unchanged'])
        checked_file(ROOT/'maps'/(record['map']+'.asm'), record['map_script_sha256_unchanged'])
        for source in record['opaque_source_records']:
            checked_file(source['source'],source['sha256'])
    profile = manifest['extra_exterior_BG3']
    palette = checked_file(profile['binary'],profile['binary_sha256'],24)
    require([(r['map'],r['slot'],r['byte_offset']) for r in profile['maps']]
            == [('TheDen',3,0),('RazorHill',3,8),('OrgrimmarGate',3,16)], 'BG3 scope/order differs')
    expected_palette = b''.join((rgb[0] | rgb[1] << 5 | rgb[2] << 10).to_bytes(2,'little')
                                for record in profile['maps'] for rgb in record['rgb555'])
    require(palette == expected_palette, 'BG3 declared RGB555 differs from its native bytes')
    verified_payloads['ground_bg3.bin'] = palette
    files['assets/ground_source_manifest.json'] = path.read_bytes()
    result = add_tree(files,GROUND,'assets/uniform_ground/')
    for name,data in verified_payloads.items():
        require(files['assets/uniform_ground/'+name] == data, 'Ground asset changed during packaging: '+name)
    return result


def compiled_ground_packets(rom, symbol_data):
    """Check active environment INCBINs against the actual same-build ROM."""
    symbols = {}
    for line in symbol_data.decode().splitlines():
        match = re.fullmatch(r'([0-9a-fA-F]+):([0-9a-fA-F]{4})\s+(\S+)',line)
        if match:
            symbols[match[3]] = (int(match[1],16),int(match[2],16))
    checks = []

    def bound(label, content):
        require(label in symbols, 'Missing native ground ROM label: '+label)
        bank,address = symbols[label]
        offset = bank*0x4000+address-(0x4000 if bank else 0)
        require(address+len(content) <= (0x8000 if bank else 0x4000)
                and rom[offset:offset+len(content)] == content,
                'Compiled native ground packet differs: '+label)
        checks.append(label)

    collision_codes = {'FLOOR':0, 'WALL':7, 'WARP_PANEL':0x7c}
    for name in sorted(EXPECTED_GROUND):
        for suffix,filename in (('GFX','.2bpp.lz'),('Meta','_meta.bin'),
                                ('PalMap','_palmap.bin'),('Priority','_priority.bin')):
            bound('PeonUserEnv'+name+suffix,(GROUND/(name+filename)).read_bytes())
        declarations = re.findall(r'^\s*peon_user_tilecoll\s+([^;\n]+)',
                                  (GROUND/(name+'_coll.asm')).read_text(),re.M)
        rows = [[field.strip() for field in row.split(',')] for row in declarations]
        require(rows and all(len(row) == 4 and set(row) <= set(collision_codes) for row in rows),
                'Unexpected collision macro in native ground packet')
        bound('PeonUserEnv'+name+'Coll',bytes(collision_codes[value] for row in rows for value in row))
        bound(name+'_Blocks',(ROOT/'maps'/(name+'.blk')).read_bytes())
    bound('PeonUniformEnvironmentFireFramesV0220',(GROUND/'fire_frames_world.bin').read_bytes())
    bound('PeonEnvironmentFireFrames',(ROOT/'gfx/tilesets/peon_environment_fire.bin').read_bytes())
    bound('PeonUniformGroundBG3PalettesV0220',(GROUND/'ground_bg3.bin').read_bytes())
    return dict(status='PASS',rom_sha256=sha(rom),sym_sha256=sha(symbol_data),
                map_packets=13,compiled_packet_and_block_labels=len(checks),labels=checks)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for option in ('rom','sym','map','validation-root'):
        parser.add_argument('--'+option,type=Path,required=True)
    args=parser.parse_args()
    rom,sym,map_data = [p.read_bytes() for p in (args.rom,args.sym,args.map)]
    rom_hash=sha(rom)
    require(len(rom)==2097152 and rom[0x143]==0xc0, 'Expected native2MiB GBC ROM')
    require(rom[0x147:0x14a] == bytes((0x10,0x06,0x03)), 'Expected MBC3/2MiB/32KiB RAM header')
    require(rom[0x14d] == ((-sum(rom[0x134:0x14d])-25)&255), 'ROM header checksum differs')
    require(int.from_bytes(rom[0x14e:0x150],'big') == ((sum(rom)-sum(rom[0x14e:0x150]))&0xffff),
            'ROM global checksum differs')
    if (RELEASE/'manifest.json').exists():
        require(json.loads((RELEASE/'manifest.json').read_bytes())['rom_sha256']==rom_hash,
                'Do not overwrite a delivered release with a different ROM')
    if (RELEASE/(BASE+'.gbc')).exists():
        require(sha((RELEASE/(BASE+'.gbc')).read_bytes()) == rom_hash,
                'Existing loose v20 ROM differs')
    if (RELEASE/(BASE+'.zip')).exists():
        with zipfile.ZipFile(RELEASE/(BASE+'.zip')) as archive:
            require(archive.testzip() is None and sha(archive.read(BASE+'.gbc')) == rom_hash,
                    'Existing v20 ZIP is damaged or contains a different ROM')
    files={BASE+'.gbc':rom,BASE+'.sym':sym,BASE+'.map':map_data}
    validation,reports,captures=retained.collect_validation(
        args.validation_root/'validation.json',rom,sym,map_data,files)
    retained.collect_assets(files)  # Unchanged approved v18 welcome and v19 master busts.
    prior_manifest=(ROOT/'gfx/world_readability_v0219/manifest.json').read_bytes()
    prior_contract=dict(manifest_sha256=sha(prior_manifest),role_families=39,bound_families=30,bound_packets=90)
    # Recheck the approved historical artwork and Garrosh provenance independently.
    retained.collect_world_assets(files,dict(world_asset_contract=prior_contract))
    world=world_assets(files,validation)
    ground=ground_assets(files)
    ground_rom=compiled_ground_packets(rom,sym)
    files['README.md']=(
        '# Peon of Warcraft v0.2.20\n\n'
        'Ouvrir '+BASE+'.gbc dans un émulateur Game Boy Color.\n\n'
        'Personnages du monde redessinés sur une grille native 32×32 : nouvelles silhouettes, '
        'visages, équipements et deux clés de marche par direction. Les nouvelles illustrations '
        'sont réduites directement à 32 px puis converties avec perte aux palettes GBC ; les pas sont '
        'édités séparément. Ce ne sont pas des sprites16px agrandis. Les créatures approuvées, '
        'dont le sanglier et le Kolkar, conservent leurs paquets natifs24px.\n\n'
        'Sol ocre uniforme sur 13 cartes, chemins compris, avec les pixels opaques des décors '
        'et les collisions préservés. Le moteur utilise le mode double vitesse du CPU CGB '
        'et place son travail dans le budget natif de deux images. Les mesures exactes de '
        'cadence, son et déplacements sont dans validation/.\n\n'
        'assets/active_world/ contient les graphismes du monde liés à cette version. '
        'assets/native_world/ conserve les références historiques v19 et la provenance Garrosh ; '
        'ces strips statiques ne sont pas des captures ROM. Les illustrations et menus approuvés '
        'restent inchangés. runtime/ ne contient que des captures LCD160×144 du SHA exact livré '
        'et leurs agrandissements4× sans lissage. Le matériel physique n’a pas été testé.\n\n'
        'La grille de déplacement reste16px. Les corps sont admis entiers dans les limites '
        '40objets OAM/10par ligne ; des acteurs éloignés peuvent être masqués dans les scènes '
        'chargées. Les sauvegardes, combats et règles de jeu restent compatibles.\n'
    ).encode()
    manifest=dict(version=VERSION,rom=BASE+'.gbc',rom_sha256=rom_hash,sym_sha256=sha(sym),
                  map_sha256=sha(map_data),tests=reports,runtime=captures,world_asset_contract=world['contract'],
                  active_world=world,uniform_ground_files=ground,uniform_ground_ROM_proof=ground_rom,
                  physical_modretro_tested=False,
                  files={n:dict(sha256=sha(d),bytes=len(d)) for n,d in sorted(files.items())})
    files['manifest.json']=json_bytes(manifest)
    # The external manifest adds the ZIP hash after the ZIP is finalized.
    # Exclude it here so the same checksum file is valid loose and in the ZIP.
    files['SHA256SUMS.txt']=''.join(f'{sha(d)}  {n}\n' for n,d in sorted(files.items())
                                  if n != 'manifest.json').encode()
    previous_base=retained.BASE
    retained.BASE=BASE
    try: archive=retained.verified_archive(files,rom_hash)
    finally: retained.BASE=previous_base
    RELEASE.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():
        if name == 'manifest.json':
            continue
        target=RELEASE/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    (RELEASE/(BASE+'.zip')).write_bytes(archive)
    manifest.update(zip_sha256=sha(archive),zip_bytes=len(archive),zip_crc_and_all_payload_sha256='PASS')
    (RELEASE/'manifest.json').write_bytes(json_bytes(manifest))
    (RELEASE/(BASE+'.zip.sha256')).write_text(f'{sha(archive)}  {BASE}.zip\n')
    print(json.dumps(dict(status='PASS',rom_sha256=rom_hash,zip_sha256=sha(archive),
                         native32_families=len(world['native32_roles']),captures=len(captures)),indent=2))


if __name__=='__main__':main()
