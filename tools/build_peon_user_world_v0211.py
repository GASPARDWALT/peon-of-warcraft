#!/usr/bin/env python3
"""Import supplied native world pixels; only colors are reduced for GBC OBJ.

No resizing, alpha editing or invented walking anatomy. Shared OBJ palettes
remain unchanged; NPCs select an existing compatible material/skin family.
"""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'references/characters/peon_world_character_sheets_split'
PLAYERS = ROOT / 'references/generated/user_player_v0211/sprites'
OUT = ROOT / 'gfx/user_world_v0211'
REVIEW = ROOT / 'references/generated/user_world_v0211'
DIRECTIONS = ('front', 'back', 'left', 'right')
ROLE_PALETTE = {
    'imp': 7, 'scorpid': 7, 'sarkoth': 7,
    'boar': 3, 'tiger': 3, 'panther': 3, 'raptor': 3,
    'felhunter': 1, 'harpy': 1, 'enemy_warlock': 1,
    'orc_guard': 2, 'orc_merchant': 2, 'camp_guard': 2,
    'quest_peon': 2, 'peon_worker': 2, 'veteran_questgiver': 2,
    'shaman_apprentice': 2, 'shaman_master': 2, 'warrior_trainer': 2,
    'beast_handler': 2, 'troll_guard': 6, 'troll_villager': 6,
    'troll_merchant': 6, 'troll_shaman': 6, 'senjin_troll_shaman': 6,
    'senjin_chief': 6,
    'base': 2, 'shaman': 2, 'warrior': 2, 'warlock': 1,
}
# Stable IDs and save records. Masters/innkeepers use canonical imports too.
BINDINGS = (
    ('SPRITE_OAK', 'PeonUserThrallWorldV0212', 'veteran_questgiver'),
    ('SPRITE_ELDER', 'PeonUserKentoWorldV0212', 'shaman_apprentice'),
    ('SPRITE_BRUNO', 'PeonUserWarriorMasterWorldV0212', 'warrior_trainer'),
    ('SPRITE_MORTY', 'PeonUserWarlockMasterWorldV0212', 'enemy_warlock'),
    ('SPRITE_BLAINE', 'PeonUserInnkeeperWorldV0212', 'orc_merchant'),
    ('SPRITE_JANINE', 'PeonUserSarkothWorldV0211', 'sarkoth'),
    ('SPRITE_BUG_CATCHER', 'PeonUserTigerWorldV0211', 'tiger'),
    ('SPRITE_TWIN', 'PeonUserRaptorWorldV0211', 'raptor'),
    ('SPRITE_YOUNGSTER', 'PeonUserHunterWorldV0211', 'beast_handler'),
    ('SPRITE_TEACHER', 'PeonUserHarpyWorldV0211', 'harpy'),
    ('SPRITE_BEAUTY', 'PeonUserFelhunterWorldV0211', 'felhunter'),
    ('SPRITE_SUPER_NERD', 'PeonUserCultistWorldV0211', 'enemy_warlock'),
    ('SPRITE_LINK_RECEPTIONIST', 'PeonUserTrollGuardWorldV0211', 'troll_guard'),
    ('SPRITE_CLERK', 'PeonUserTrollMerchantWorldV0211', 'troll_merchant'),
    ('SPRITE_FISHER', 'PeonUserQuestPeonWorldV0211', 'quest_peon'),
    ('SPRITE_SAGE', 'PeonUserTrollShamanWorldV0211', 'troll_shaman'),
    ('SPRITE_GENTLEMAN', 'PeonUserOrcMerchantWorldV0211', 'orc_merchant'),
    ('SPRITE_BLACK_BELT', 'PeonUserVeteranWorldV0211', 'veteran_questgiver'),
    ('SPRITE_OFFICER', 'PeonUserOrcGuardWorldV0211', 'orc_guard'),
    ('SPRITE_MONSTER', 'PeonUserImpWorldV0211', 'imp'),
    ('SPRITE_POKE_BALL', 'PeonUserBoarWorldV0211', 'boar'),
    ('SPRITE_PAPER', 'PeonUserScorpidWorldV0211', 'scorpid'),
    ('SPRITE_PEON_FRIENDLY_IMP', 'PeonUserFriendlyImpWorldV0211', 'imp'),
    ('SPRITE_PEON_WORKER', 'PeonUserWorkerWorldV0211', 'peon_worker'),
)


# These crops in the preserved archive contain labels, isolated equipment or
# clipped bodies. A fallback uses a complete supplied PNG unchanged; it is not
# a reconstruction of the missing view. Valid originals always take priority.
CANONICAL_FALLBACKS = {
    **{('quest_peon', d): ('orc_merchant', d, 'Label/weapon/body fragments') for d in DIRECTIONS},
    **{('peon_worker', d): ('beast_handler', d, 'Clipped body or isolated row') for d in DIRECTIONS if d != 'front'},
    **{('camp_guard', d): ('orc_guard', d, 'Overworld label instead of character') for d in DIRECTIONS},
    **{('shaman_master', d): ('orc_guard', d, 'Overworld label instead of character') for d in DIRECTIONS},
    **{('shaman_apprentice', d): ('beast_handler', d, 'Label, 24-pixel bottom crop or isolated equipment sliver') for d in DIRECTIONS},
    **{('senjin_troll_shaman', d): ('troll_shaman', d, 'Clipped body/label crop') for d in DIRECTIONS},
    **{('senjin_chief', d): ('troll_guard', d, 'Clipped body/label crop') for d in DIRECTIONS if d != 'left'},
    **{('warrior_trainer', d): ('orc_guard', d, 'Label instead of character') for d in DIRECTIONS},
    **{('veteran_questgiver', d): ('orc_guard', d, 'Label instead of character') for d in DIRECTIONS},
    **{('sarkoth', d): ('scorpid', d, 'Overworld label instead of character') for d in DIRECTIONS},
    ('enemy_warlock', 'front'): ('enemy_warlock', 'left', '19-pixel equipment sliver; frontal view unavailable, supplied left view retained'),
}


def canonical_path(role, direction):
    return SOURCE / role / f'{role}_world_{direction}.png'


def world_source_rgba(path):
    image = Image.open(path).convert('RGBA')
    pixels = np.asarray(image)
    if image.size != (16, 16) or not set(np.unique(pixels[..., 3])) <= {0, 255} or not np.any(pixels[..., 3]):
        raise ValueError(f'World source must be a nonempty 16x16 PNG with binary alpha: {path}')
    return image


def source_selection(role, direction):
    original = canonical_path(role, direction)
    world_source_rgba(original)
    fallback = CANONICAL_FALLBACKS.get((role, direction))
    if fallback:
        # A later replacement at the canonical path must not remain hidden by
        # an old damaged-crop decision. Only the archived damaged bytes trigger
        # this explicit fallback.
        archive = SOURCE.parent / (SOURCE.name + '.zip')
        with zipfile.ZipFile(archive) as source:
            archived = source.read(f'{role}/{role}_world_{direction}.png')
        if hashlib.sha256(original.read_bytes()).digest() == hashlib.sha256(archived).digest():
            alternate_role, alternate_direction, reason = fallback
            selected = canonical_path(alternate_role, alternate_direction)
            world_source_rgba(selected)
            return selected, {'requested_original': str(original.relative_to(ROOT)),
                              'requested_original_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
                              'canonical_role_fallback': True, 'fallback_role': alternate_role,
                              'fallback_direction': alternate_direction, 'fallback_reason': reason,
                              'fallback_pixels_redrawn': False}
    return original, {'requested_original': str(original.relative_to(ROOT)),
                      'requested_original_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
                      'canonical_role_fallback': False}


def source_path(role, direction):
    return source_selection(role, direction)[0]


def make_palettes():
    # Preserve the established shared palette slots byte-for-byte. Choosing
    # different NPC PNGs must not recolor heroes, locked masters, HUD or quest
    # markers. NPCs may select an existing compatible family independently.
    return [
        [(31,31,31), (22,8,4), (5,2,2), (31,5,3)],
        [(31,31,31), (12,17,5), (16,11,17), (1,1,1)],
        [(31,31,31), (18,12,6), (15,17,8), (2,1,1)],
        [(31,31,31), (25,19,11), (12,7,4), (1,1,1)],
        [(31,31,31), (22,15,7), (9,5,2), (31,26,3)],
        [(31,31,31), (17,17,17), (31,25,7), (1,1,1)],
        [(31,31,31), (20,19,17), (12,17,19), (2,2,3)],
        [(31,31,31), (18,9,6), (10,3,2), (2,1,1)],
    ]


# Public helpers used by the player importer. Values are exact RGB555 colors.
WORLD_PALETTES = make_palettes()


def allowed_npc_palettes(role):
    # A lowest-error fit across every family would turn dark green Orcs red.
    # Restrict the fit to the supplied character's material/skin family. HUD0
    # and quest/emote4/5 are never candidates and no shared slot is modified.
    if role.startswith('troll_') or role.startswith('senjin_'):
        return (6,)
    if role in ('felhunter', 'harpy', 'enemy_warlock', 'panther'):
        return (1,)
    if role in ('imp',):
        return (7,)
    if role in ('scorpid', 'sarkoth'):
        return (1, 7)
    if role in ('boar', 'tiger'):
        return (3,)
    if role == 'raptor':
        return (2,)
    return (1, 2)


def choose_npc_palette(role, images):
    pixels = np.concatenate([(np.asarray(image)[..., :3].astype(np.int32) >> 3)
                             [np.asarray(image)[..., 3] > 0] for image in images])
    errors = {index: int(((pixels[:, None, :] - np.asarray(WORLD_PALETTES[index][1:])[None, :, :]) ** 2)
                        .sum(2).min(1).sum()) for index in allowed_npc_palettes(role)}
    selected = min(errors, key=lambda index: (errors[index], index != ROLE_PALETTE[role], index))
    return selected, errors


def fidelity_record(original, native):
    source = np.asarray(original)
    actual = np.asarray(native)
    visible = source[..., 3] > 0
    rgb = source[..., :3].astype(np.int32) >> 3
    fitted = actual[..., :3].astype(np.int32) >> 3
    assert np.array_equal(actual[..., 3], source[..., 3])
    colors = [len(np.unique(rgb[y:y+8, x:x+8][visible[y:y+8, x:x+8]], axis=0))
              for y in (0, 8) for x in (0, 8)]
    return {'opaque_pixels': int(visible.sum()), 'alpha_equal': True,
            'source_rgb555_opaque_colors': len(np.unique(rgb[visible], axis=0)),
            'native_rgb555_opaque_colors': len(np.unique(fitted[visible], axis=0)),
            'rgb555_exact_opaque_pixels': int((rgb[visible] == fitted[visible]).all(1).sum()),
            'rgb555_rmse': round(float(np.sqrt(((rgb[visible] - fitted[visible]) ** 2).mean())), 4),
            'source_opaque_colors_per_8x8': colors, 'hardware_opaque_colors_per_obj_limit': 3,
            'color_exact': bool(np.array_equal(rgb[visible], fitted[visible])), 'geometry_exact': True}


def review_preview(role, sources, native):
    # Inspection artifact only: unchanged source pixels and decoded hardware
    # colors enlarged by whole cells. This is not a gameplay capture.
    canvas = Image.new('RGBA', (544, 108), (28, 28, 28, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((4, 2), role + ' | source / native | static import preview', fill='white')
    for number, (direction, source, rendered) in enumerate(zip(DIRECTIONS, sources, native)):
        x = number * 136
        draw.text((x + 4, 20), direction, fill='white')
        for offset, image in ((4, source), (72, rendered)):
            canvas.alpha_composite(image.resize((64, 64), Image.Resampling.NEAREST), (x + offset, 36))
    canvas.convert('RGB').save(REVIEW / (role + '_source_vs_native_4x.png'))


def index_world_rgba(image, palette_index):
    rgba = np.asarray(image.convert('RGBA'))
    if image.size != (16,16) or not set(np.unique(rgba[...,3])) <= {0,255}:
        raise ValueError('World source must be 16x16 with binary alpha')
    palette = np.asarray(WORLD_PALETTES[palette_index][1:], dtype=np.int32)
    rgb = rgba[..., :3].astype(np.int32) >> 3
    distances = ((rgb[:,:,None,:] - palette[None,None,:,:]) ** 2).sum(axis=3)
    indices = (distances.argmin(axis=2) + 1).astype('uint8')
    indices[rgba[...,3] == 0] = 0
    assert np.array_equal(indices > 0, rgba[...,3] > 0)
    return Image.fromarray(indices, 'L')


def encode_world_frame(indexed):
    pixels = np.asarray(indexed)
    result = bytearray()
    for y in (0,8):
        for x in (0,8):
            for row in pixels[y:y+8,x:x+8]:
                result.extend((sum((int(v)&1) << (7-i) for i,v in enumerate(row)),
                               sum((int(v)>>1) << (7-i) for i,v in enumerate(row))))
    assert len(result) == 64
    return bytes(result)


def decode_world_frame(data):
    if len(data) != 64:
        raise ValueError('A native 16x16 world frame must contain exactly four tiles')
    pixels = np.zeros((16, 16), dtype='uint8')
    for tile, (y, x) in enumerate(((0, 0), (0, 8), (8, 0), (8, 8))):
        for row in range(8):
            low, high = data[tile*16 + row*2:tile*16 + row*2 + 2]
            for column in range(8):
                pixels[y+row, x+column] = ((low >> (7-column)) & 1) | (((high >> (7-column)) & 1) << 1)
    return Image.fromarray(pixels, 'L')


def build_world_bytes(four_frames):
    assert len(four_frames) == 4
    result = b''.join(encode_world_frame(frame) for frame in four_frames) * 3
    assert len(result) == 768
    return result


def hardware_rgba(indexed, palette_index):
    indices = np.asarray(indexed)
    colors = np.asarray(WORLD_PALETTES[palette_index], dtype='uint8')
    # Standard RGB555 expansion; all visible pixels keep their source alpha.
    colors = (colors << 3) | (colors >> 2)
    return Image.fromarray(np.dstack((colors[indices], np.where(indices > 0,255,0).astype('uint8'))), 'RGBA')


def main(npc_only=False):
    OUT.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    previous = json.loads((OUT/'manifest.json').read_text()) if (OUT/'manifest.json').is_file() else {}
    previous_palette_bytes = (OUT/'world_obj.pal').read_bytes() if (OUT/'world_obj.pal').is_file() else None
    if npc_only and 'sleeping_pose' not in previous:
        raise ValueError('--npc-only requires the existing sleeping-pose metadata; it never generates hero art')
    source_before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in SOURCE.rglob('*.png')}
    manifest = {'method': 'Unchanged canonical16x16 PNG pixels and alpha; explicit documented whole-PNG fallbacks for archived damaged crops; nearest RGB555 reduction to3 opaque OBJ colors.',
                'source_zip_sha256': hashlib.sha256((SOURCE.parent/(SOURCE.name+'.zip')).read_bytes()).hexdigest(),
                'palette_rgb555': WORLD_PALETTES, 'roles': {}, 'native_movement': 'NPC walking uses supplied direction art unchanged; player phases can be independently authored.',
                'color_exact': False, 'geometry_exact': True, 'source_originals_changed': False,
                'procedural_repair_pngs_imported': False, 'protected_obj_palette_indices': [0, 4, 5],
                'shared_obj_palette_colors_preserved': True,
                'preview_is_gameplay_capture': False,
                'geometry_note': 'Geometry and alpha refer to the selected canonical PNG; damaged requested files remain intact and each alternate role is recorded.',
                'engine_palette_limitation': 'One palette per actor; three opaque colors per8x8 OBJ. More palettes per16x16 require a separate per-quadrant engine change.'}
    for role in sorted(p.name for p in SOURCE.iterdir() if p.is_dir()):
        if role not in ROLE_PALETTE:
            continue
        folder = OUT / role
        folder.mkdir(exist_ok=True)
        selections = [source_selection(role, direction) for direction in DIRECTIONS]
        originals = [world_source_rgba(path) for path, _ in selections]
        palette, palette_errors = choose_npc_palette(role, originals)
        frames, records, previews = [], [], []
        for direction, original, (path, selection) in zip(DIRECTIONS, originals, selections):
            frame = index_world_rgba(original, palette)
            frames.append(frame)
            packet = encode_world_frame(frame)
            decoded = decode_world_frame(packet)
            assert np.array_equal(np.asarray(decoded), np.asarray(frame))
            native = hardware_rgba(decoded, palette)
            native.save(folder/f'world_{direction}.png')
            previews.append(native)
            records.append({'direction': direction, 'source': str(path.relative_to(ROOT)),
                            'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                            'authorized_completion': False,
                            'source_dimensions': list(original.size), 'native_2bpp_decode_exact': True,
                            **selection, **fidelity_record(original, native)})
        data = build_world_bytes(frames)
        (folder/'overworld.bin').write_bytes(data)
        assert data[:256] == data[256:512] == data[512:]
        review_preview(role, originals, previews)
        manifest['roles'][role] = {'palette_index': palette, 'frames': records,
                                   'allowed_existing_palette_indices': list(palette_errors),
                                   'allowed_palette_rgb555_squared_errors': palette_errors,
                                   'binary_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                                   'independent_right_view': True, 'invented_walk_pixels': False}
    if npc_only:
        manifest['sleeping_pose'] = previous['sleeping_pose']
    else:
        sleeping_source = PLAYERS / 'base/world_sleep.png'
        sleeping_rgba = Image.open(sleeping_source).convert('RGBA')
        sleeping_indices = index_world_rgba(sleeping_rgba, ROLE_PALETTE['base'])
        sleeping_data = encode_world_frame(sleeping_indices)
        (OUT/'base_sleeping.2bpp').write_bytes(sleeping_data)
        sleeping_build_png = sleeping_indices.convert('P')
        sleeping_build_png.putpalette([255,255,255,170,170,170,85,85,85,0,0,0] + [0]*756)
        sleeping_build_png.save(OUT/'base_sleeping.png')
        hardware_rgba(sleeping_indices, ROLE_PALETTE['base']).save(OUT/'base_sleeping_hardware_rgba.png')
        manifest['sleeping_pose'] = {
            'sprite': 'SPRITE_RED', 'label': 'PeonSleepingGFX',
            'source': str(sleeping_source.relative_to(ROOT)),
            'source_sha256': hashlib.sha256(sleeping_source.read_bytes()).hexdigest(),
            'authorized_completion': True, 'source_dimensions': list(sleeping_rgba.size),
            'opaque_pixels': int(np.count_nonzero(np.asarray(sleeping_rgba)[...,3])),
            'palette_index': ROLE_PALETTE['base'], 'alpha_equal': True,
            'binary': 'gfx/user_world_v0211/base_sleeping.2bpp',
            'native_build_png': 'gfx/user_world_v0211/base_sleeping.png',
            'hardware_preview': 'gfx/user_world_v0211/base_sleeping_hardware_rgba.png',
            'binary_bytes': len(sleeping_data), 'sha256': hashlib.sha256(sleeping_data).hexdigest(),
            'tile_order': 'row-major', 'source_originals_changed': False,
        }
    asm = ['; User-derived native world imports; originals and previous assets remain intact.']
    # Separate floating sections avoid demanding a single large bank.
    for sprite, label, role in BINDINGS:
        if role not in manifest['roles']:
            raise ValueError(f'Missing bound role: {role}')
        asm += [f'SECTION "User world {sprite} v0211", ROMX', f'{label}::',
                f'\tINCBIN "gfx/user_world_v0211/{role}/overworld.bin"',
                f'\tassert @ - {label} == 48 * TILE_SIZE', '']
    # A source-faithful apprentice packet is available for the map/sprite-table
    # owner to bind explicitly. This does not allocate a new sprite ID or
    # silently replace another actor's existing binding.
    apprentice_label = 'PeonUserShamanApprenticeWorldV0211'
    asm += ['SECTION "User world Shaman Apprentice v0211", ROMX', apprentice_label + '::',
            '\tINCBIN "gfx/user_world_v0211/shaman_apprentice/overworld.bin"',
            f'\tassert @ - {apprentice_label} == 48 * TILE_SIZE', '']
    manifest['available_unbound_roles'] = {'shaman_apprentice': {'label': apprentice_label,
        'palette_index': manifest['roles']['shaman_apprentice']['palette_index'],
        'requires_explicit_sprite_table_binding': True}}
    (OUT/'sprites.asm').write_text('\n'.join(asm).rstrip()+'\n')
    overrides = ['; Sprite IDs and five actor palette families; HUD0 and quest4/5 are protected.']
    overrides += [f'\tdb {sprite}, {manifest["roles"][role]["palette_index"]}' for sprite, _, role in BINDINGS]
    overrides += ['\tdb $ff']
    (OUT/'palette_overrides.asm').write_text('\n'.join(overrides)+'\n')
    (OUT/'world_obj.pal').write_text(''.join('\tRGB '+', '.join(str(v) for c in palette for v in c)+'\n' for palette in WORLD_PALETTES))
    if previous_palette_bytes is not None:
        assert (OUT/'world_obj.pal').read_bytes() == previous_palette_bytes, 'Shared world OBJ palette colors changed'
    manifest['bindings'] = [{'sprite': sprite, 'label': label, 'role': role} for sprite,label,role in BINDINGS]
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest for path, digest in source_before.items())
    (REVIEW/'source_fidelity_report.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (REVIEW/'README.md').write_text(
        '# Canonical NPC source import\n\n'
        'Each preview shows the selected supplied 16×16 PNG on the left and the decoded native 2bpp conversion on the right. '
        'These are static import previews, not ROM captures. Original PNG geometry and binary alpha remain intact. '
        'The native engine permits three opaque colors per OBJ, so color reduction is explicitly lossy.\n\n'
        '`source_fidelity_report.json` records every requested original, selected source hash, damaged-crop fallback, palette choice and color-error measurement. '
        'Fallbacks copy complete existing canonical PNGs; no procedural repair or ASCII sprite drawing is imported. '
        'The enemy Warlock front remains a documented left-view fallback because its supplied frontal crop is an equipment sliver.\n\n'
        'All eight shared OBJ palettes remain unchanged. SPRITE_SAGE uses the four intact troll_shaman views. '
        'The Shaman Apprentice packet is exported as PeonUserShamanApprenticeWorldV0211, palette2, and requires an explicit sprite-table binding. '
        'More than one palette per actor requires a separately coordinated engine change; no OAM entries, tile budgets, save fields or sprite IDs changed.\n')
    print(json.dumps({'roles': len(manifest['roles']), 'bindings': len(BINDINGS),
                      'palette_rgb555': WORLD_PALETTES, 'geometry_and_alpha_preserved': True},indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--npc-only', action='store_true', help='Import only NPCs; preserve all existing hero sleeping-pose files')
    args = parser.parse_args()
    if not args.npc_only:
        raise SystemExit('Use --npc-only. Hero assets are imported separately by import_peon_approved_players_v0212.py; historical procedural sleeping/art inputs are preserved.')
    main(True)
