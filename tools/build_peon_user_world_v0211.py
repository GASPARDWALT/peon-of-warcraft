#!/usr/bin/env python3
"""Import supplied native world pixels; only colors are reduced for GBC OBJ.

No resizing, alpha editing, invented walking anatomy, or legacy asset writes.
The three opaque OBJ colors are chosen from source RGB555 colors by family.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'references/characters/peon_world_character_sheets_split'
REPAIRS = ROOT / 'references/generated/user_npc_completion_v0211'
PLAYERS = ROOT / 'references/generated/user_player_v0211/sprites'
OUT = ROOT / 'gfx/user_world_v0211'
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
# Stable sprite IDs, actor records and saved flags remain unchanged. Masters
# Kento, Thrall, MoCMoc and Xasthur deliberately keep their established art.
BINDINGS = (
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


def source_path(role, direction):
    repaired = REPAIRS / role / f'{role}_world_{direction}.png'
    return repaired if repaired.is_file() else SOURCE / role / f'{role}_world_{direction}.png'


def source_palette(roles, anchors):
    """Select source medoids near semantic material/skin/outline anchors."""
    colors = Counter()
    for role in roles:
        for direction in DIRECTIONS:
            path = (PLAYERS / role / f'world_{direction}.png' if role in ('base', 'shaman', 'warrior', 'warlock')
                    else source_path(role, direction))
            if not path.is_file():
                continue
            rgba = np.asarray(Image.open(path).convert('RGBA'))
            colors.update(tuple(int(v) >> 3 for v in rgb) for rgb in rgba[..., :3][rgba[..., 3] > 0])
    if not colors:
        raise ValueError(f'Missing palette source for {roles}')
    chosen = []
    for anchor in anchors:
        color = min((c for c in colors if c not in chosen),
                    key=lambda c: (sum((x-y)**2 for x, y in zip(c, anchor)), -colors[c], c))
        chosen.append(color)
    return [(31, 31, 31), *chosen]


def make_palettes():
    # 0 is the fixed world HUD, 4 yellow quest markers, 5 gray quest markers.
    # The old brown family is retained for the locked Tauren master Kento.
    palettes = [
        [(31,31,31), (22,8,4), (5,2,2), (31,5,3)],
        # Purple stays index2, matching the locked legacy Warlock's cloak.
        source_palette(('warlock','enemy_warlock','felhunter','harpy'), ((13,18,8),(14,8,18),(1,1,1))),
        source_palette(('base','shaman','warrior','orc_guard','orc_merchant','quest_peon'), ((17,11,6),(15,20,8),(1,1,1))),
        [(31,31,31), (25,19,11), (12,7,4), (1,1,1)],
        [(31,31,31), (22,15,7), (9,5,2), (31,26,3)],
        [(31,31,31), (17,17,17), (31,25,7), (1,1,1)],
        source_palette(('troll_guard','troll_merchant','troll_shaman'), ((23,23,18),(10,17,20),(1,2,3))),
        source_palette(('imp','scorpid','sarkoth'), ((24,9,5),(12,6,3),(1,1,1))),
    ]
    return palettes


# Public helpers used by the player importer. Values are exact RGB555 colors.
WORLD_PALETTES = make_palettes()


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


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {'method': 'Native16x16 source geometry and binary alpha unchanged; explicit source-family RGB555 reduction to3 opaque OBJ colors.',
                'source_zip_sha256': hashlib.sha256((SOURCE.parent/(SOURCE.name+'.zip')).read_bytes()).hexdigest(),
                'palette_rgb555': WORLD_PALETTES, 'roles': {}, 'native_movement': 'NPC walking uses supplied direction art unchanged; player phases can be independently authored.',
                'color_exact': False, 'geometry_exact': True, 'source_originals_changed': False}
    for role in sorted(p.name for p in SOURCE.iterdir() if p.is_dir()):
        if role not in ROLE_PALETTE:
            continue
        folder = OUT / role
        folder.mkdir(exist_ok=True)
        palette = ROLE_PALETTE[role]
        frames, records = [], []
        for direction in DIRECTIONS:
            path = source_path(role, direction)
            original = Image.open(path).convert('RGBA')
            frame = index_world_rgba(original, palette)
            frames.append(frame)
            hardware_rgba(frame, palette).save(folder/f'world_{direction}.png')
            records.append({'direction': direction, 'source': str(path.relative_to(ROOT)),
                            'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                            'authorized_completion': path.is_relative_to(REPAIRS),
                            'opaque_pixels': int(np.count_nonzero(np.asarray(original)[...,3])),
                            'alpha_equal': True, 'source_dimensions': list(original.size)})
        data = build_world_bytes(frames)
        (folder/'overworld.bin').write_bytes(data)
        manifest['roles'][role] = {'palette_index': palette, 'frames': records,
                                   'binary_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                                   'independent_right_view': True, 'invented_walk_pixels': False}
    sleeping_source = PLAYERS / 'base/world_sleep.png'
    sleeping_rgba = Image.open(sleeping_source).convert('RGBA')
    sleeping_indices = index_world_rgba(sleeping_rgba, ROLE_PALETTE['base'])
    sleeping_data = encode_world_frame(sleeping_indices)
    (OUT/'base_sleeping.2bpp').write_bytes(sleeping_data)
    # Make's generic PNG->2bpp rule consumes opaque DMG indices. Keep RGBA
    # review art separately so a fresh timestamp cannot change the packet.
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
    (OUT/'sprites.asm').write_text('\n'.join(asm).rstrip()+'\n')
    overrides = ['; Sprite IDs and five actor palette families; HUD0 and quest4/5 are protected.']
    overrides += [f'\tdb {sprite}, {ROLE_PALETTE[role]}' for sprite, _, role in BINDINGS]
    overrides += ['\tdb $ff']
    (OUT/'palette_overrides.asm').write_text('\n'.join(overrides)+'\n')
    (OUT/'world_obj.pal').write_text(''.join('\tRGB '+', '.join(str(v) for c in palette for v in c)+'\n' for palette in WORLD_PALETTES))
    manifest['bindings'] = [{'sprite': sprite, 'label': label, 'role': role} for sprite,label,role in BINDINGS]
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'roles': len(manifest['roles']), 'bindings': len(BINDINGS),
                      'palette_rgb555': WORLD_PALETTES, 'geometry_and_alpha_preserved': True},indent=2))


if __name__ == '__main__':
    main()
