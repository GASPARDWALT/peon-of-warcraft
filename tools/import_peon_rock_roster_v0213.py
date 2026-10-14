#!/usr/bin/env python3
"""Import the supplied rocks as three party stages, without drawing pixels.

Battle source canvases keep their native scale and complete alpha. Vibration
frames translate the whole source by one pixel. World previews use nearest
sampling only where the supplied 32px canvas must fit the existing 16px actor.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import numpy as np
from PIL import Image
from build_peon_user_battle_v0211 import encode, choose_palettes, tile_errors
from build_peon_user_world_v0211 import encode_world_frame

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'references/characters/peon_of_warcraft_environment_pack_v2_art_quality'
GFX = ROOT / 'gfx/rock_roster_v0213'
OUT = ROOT / 'references/generated/rock_roster_v0213'
STAGES = (
    ('one', 'PeonRockOne', 'durotar_valley/rock_durotar_small_01_16x16.png'),
    ('vein', 'PeonRockVein', 'shared_interactables/ore_shared_copper_vein_32x32.png'),
    ('element', 'PeonRockElement', 'durotar_valley/rock_durotar_large_01_32x32.png'),
)


def packed(palettes):
    return b''.join(int(r | g << 5 | b << 10).to_bytes(2, 'little')
                    for p in palettes for r, g, b in p)


def save_rgba(path, array):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array.astype('uint8')).save(path)


def frames_from_source(image, size):
    result = []
    for dx in (0, -1, 1):
        canvas = Image.new('RGBA', (size, size))
        # Native source canvas always fits; no trimming or enlargement.
        position = ((size - image.width) // 2 + dx, size - image.height)
        canvas.paste(image, position)
        assert sum(canvas.getchannel('A').getdata()) == sum(image.getchannel('A').getdata())
        result.append(np.asarray(canvas))
    return result


def reduce_frames(frames, palettes):
    choices = tile_errors(frames, palettes).argmin(1)
    indices, previews = [], []
    for frame in frames:
        h, w = frame.shape[:2]
        index = np.zeros((h, w), dtype='uint8')
        preview = np.zeros_like(frame)
        for n, p in enumerate(choices):
            y, x = (n // (w // 8)) * 8, (n % (w // 8)) * 8
            region = frame[y:y+8, x:x+8]
            palette = np.asarray(palettes[p], dtype='int32')
            rgb = region[:, :, :3].astype('int32') >> 3
            fit = ((rgb[:, :, None] - palette[None, None, 1:]) ** 2).sum(3).argmin(2) + 1
            fit[region[:, :, 3] == 0] = 0
            index[y:y+8, x:x+8] = fit
            color = palette[fit]
            preview[y:y+8, x:x+8, :3] = (color << 3) | (color >> 2)
            preview[y:y+8, x:x+8, 3] = region[:, :, 3]
        assert np.array_equal(preview[:, :, 3], frame[:, :, 3])
        indices.append(index)
        previews.append(preview)
    return indices, previews, choices


def native_front(folder, packets):
    # Crystal keeps frame0's 49 ordered tiles, then deduplicates changed tiles.
    first = [packets[0][i:i+16] for i in range(0, 784, 16)]
    dictionary = list(first)
    maps = [list(range(49))]
    for packet in packets[1:] + packets[:1]:
        mapping = []
        for i in range(0, 784, 16):
            tile = packet[i:i+16]
            if tile not in dictionary:
                dictionary.append(tile)
            mapping.append(dictionary.index(tile))
        maps.append(mapping)
    assert len(dictionary) <= 98, ('native 98-tile animation budget', len(dictionary))
    (folder / 'front.2bpp').write_bytes(b''.join(dictionary) + bytes((98-len(dictionary))*16))
    (folder / 'front.tilemap').write_bytes(bytes(v for row in maps for v in row))
    (folder / 'front.dimensions').write_bytes(bytes([0x77]))
    for option, target in (('-f', 'frames.asm'), ('-b', 'bitmask.asm')):
        with (folder / target).open('w') as output:
            subprocess.run([str(ROOT/'tools/pokemon_animation'), option,
                            str(folder/'front.tilemap'), str(folder/'front.dimensions')],
                           stdout=output, check=True)
    (folder / 'anim.asm').write_text('\tframe 1, 06\n\tframe 2, 06\n\tframe 3, 06\n\tendanim\n')
    (folder / 'anim_idle.asm').write_text('\tframe 1, 08\n\tframe 2, 08\n\tframe 3, 08\n\tendanim\n')
    subprocess.run([str(ROOT/'tools/lzcompress'), str(folder/'front.2bpp'), str(folder/'front.2bpp.lz')], check=True)
    return len(dictionary)


def main():
    manifest, declarations = [], []
    for name, label, relative in STAGES:
        source = SOURCE / relative
        image = Image.open(source).convert('RGBA')
        assert set(image.getchannel('A').getdata()) <= {0, 255}
        folder = GFX / name
        folder.mkdir(parents=True, exist_ok=True)
        front = frames_from_source(image, 56)
        back = frames_from_source(image, 48)
        palettes = choose_palettes(front + [np.pad(a, ((0,8),(0,8),(0,0))) for a in back], 2)
        # The two regional palettes share the source's darkest outline shade.
        native_counts = {}
        for kind, frames, slots in (('front', front, (1,5)), ('back', back, (0,6))):
            target = folder/kind
            target.mkdir(exist_ok=True)
            indexed, previews, choices = reduce_frames(frames, palettes)
            packets = [encode(a, True) for a in indexed]
            (target/'frames.2bpp').write_bytes(b''.join(packets))
            (target/'palettes.bin').write_bytes(packed(palettes))
            (target/'attrs.bin').write_bytes(bytes(slots[p] for p in choices))
            for i, (original, preview) in enumerate(zip(frames, previews)):
                save_rgba(OUT/name/f'{kind}_source_{i}.png', original)
                save_rgba(OUT/name/f'{kind}_native_{i}.png', preview)
            if kind == 'front':
                native_counts[kind] = native_front(target, packets)
            else:
                (target/'back.2bpp').write_bytes(packets[0])
                subprocess.run([str(ROOT/'tools/lzcompress'), str(target/'back.2bpp'), str(target/'back.2bpp.lz')], check=True)
        world = np.asarray(image.resize((16,16), Image.Resampling.NEAREST))
        world_palette = choose_palettes([world], 1)
        indexed, previews, _ = reduce_frames([world], world_palette)
        raw = encode_world_frame(indexed[0])
        # An organic rock has no authored head direction. Keep full source,
        # rather than inventing four anatomical views.
        (folder/'overworld.bin').write_bytes(raw*4*3)
        (folder/'world_palette.bin').write_bytes(packed(world_palette))
        save_rgba(OUT/name/'world_native.png', previews[0])
        if name == 'one':
            # Shared outdoor actors already own OBJ palette3. Quantize this
            # one map actor to that family instead of recoloring every Boar.
            npc_palette = [[(31,31,31), (25,19,11), (12,7,4), (1,1,1)]]
            npc_indexed, npc_previews, _ = reduce_frames([world], npc_palette)
            (folder/'overworld_npc.bin').write_bytes(encode_world_frame(npc_indexed[0])*4*3)
            save_rgba(OUT/name/'world_npc_native.png', npc_previews[0])
        head = np.asarray(Image.fromarray(indexed[0]).resize((8,8), Image.Resampling.NEAREST))
        (folder/'head.2bpp').write_bytes(encode(head))
        opaque = palettes[0][1:]
        (folder/'normal.gbcpal').write_bytes(packed([[(31,31,31), *opaque]]))
        (folder/'shiny.gbcpal').write_bytes(packed([[(31,31,31), *opaque]]))
        declarations += [f'SECTION "{label} Native Rock v0213", ROMX',
            f'{label}WorldV0213::', f'\tINCBIN "gfx/rock_roster_v0213/{name}/overworld.bin"',
            f'{label}WorldPaletteV0213::', f'\tINCBIN "gfx/rock_roster_v0213/{name}/world_palette.bin"',
            f'{label}BackFramesV0213::', f'\tINCBIN "gfx/rock_roster_v0213/{name}/back/frames.2bpp"',
            f'{label}BackPalsV0213::', f'\tINCBIN "gfx/rock_roster_v0213/{name}/back/palettes.bin"',
            f'\tINCBIN "gfx/rock_roster_v0213/{name}/back/attrs.bin"',
            f'{label}EnemyMetaV0213::', f'\tINCBIN "gfx/rock_roster_v0213/{name}/front/palettes.bin"',
            f'\tINCBIN "gfx/rock_roster_v0213/{name}/front/attrs.bin"', '']
        if name == 'one':
            declarations += [f'{label}NPCWorldV0213::',
                '\tINCBIN "gfx/rock_roster_v0213/one/overworld_npc.bin"', '']
        manifest.append({'stage': name, 'source': str(source.relative_to(ROOT)),
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'source_dimensions': list(image.size), 'battle_scale': '1:1',
            'battle_alpha_preserved': True, 'battle_frames': 'whole-source x0,-1,+1 translation',
            'world_resampling': 'nearest 16x16; stationary four-direction ABI',
            'back_view': 'same supplied organic rock, not invented anatomy',
            'native_front_dictionary_tiles': native_counts['front'],
            'palettes_rgb555': palettes, 'world_palette_rgb555': world_palette})
    (GFX/'data.asm').write_text('\n'.join(declarations))
    OUT.mkdir(parents=True, exist_ok=True)
    report = json.dumps(manifest, indent=2, default=int)
    (OUT/'manifest.json').write_text(report+'\n')
    print(report)


if __name__ == '__main__':
    main()
