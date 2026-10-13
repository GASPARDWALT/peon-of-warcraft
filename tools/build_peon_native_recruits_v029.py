#!/usr/bin/env python3
"""Prepare exact native picture dictionaries from the authored v029 frames.

Only new gfx/peon_native_v029 and generated recruitment evidence are written.
The species bindings are metadata until root applies the ROM integration.
"""
from pathlib import Path
import hashlib
import json
import re
import struct
import subprocess
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'gfx/peon_recruits_v029'
OUT = ROOT / 'gfx/peon_native_v029'
EVIDENCE = ROOT / 'references/generated/recruitment_v029/native_inputs'
BINDINGS = {'onix': 'earth_spirit', 'geodude': 'demon_imp',
            'machamp': 'orc_grunt', 'grimer': 'orc_warlock',
            'ponyta': 'kolkar_archer', 'rapidash': 'kolkar_melee'}


def run(name, *args):
    return subprocess.check_output([str(ROOT / 'tools' / name), *map(str, args)], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decode_world_frame(data):
    """Independent row-major four-tile decoder for the ordinary NPC layout."""
    assert len(data) == 64
    pixels = [0] * 256
    for tile in range(4):
        tx, ty = (tile % 2) * 8, (tile // 2) * 8
        for y in range(8):
            lo, hi = data[tile * 16 + y * 2:tile * 16 + y * 2 + 2]
            for x in range(8):
                pixels[(ty + y) * 16 + tx + x] = ((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1)
    return pixels


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    records = {}
    for species, art in BINDINGS.items():
        source, target = SOURCE / art, OUT / species
        target.mkdir(exist_ok=True)
        front = (source / 'portrait_frames.bin').read_bytes()  # RGBGFX row order
        backs = (source / 'back_frames.bin').read_bytes()  # native column order
        assert len(front) == 3 * 49 * 16 and len(backs) == 3 * 36 * 16
        (target / 'front.2bpp').write_bytes(front)
        (target / 'front.dimensions').write_bytes(bytes((0x77,)))
        dictionary, tilemap = target / 'front.animated.2bpp', target / 'front.animated.tilemap'
        run('pokemon_animation_graphics', '-o', dictionary, '-t', tilemap,
            target / 'front.2bpp', target / 'front.dimensions')
        data, indices = dictionary.read_bytes(), tilemap.read_bytes()
        assert len(indices) == 3 * 49 and len(data) % 16 == 0
        tiles = len(data) // 16
        # These six packets intentionally need no overflow upload. Never let
        # a later art edit silently cross the engine's two 7x7 allocations.
        assert 49 <= tiles <= 98, (species, tiles)
        # Dictionary references must reconstruct each independently authored
        # frame, including the engine's row-to-column transposition.
        for frame in range(3):
            rebuilt = b''.join(data[index * 16:(index + 1) * 16]
                               for index in indices[frame * 49:(frame + 1) * 49])
            expected = (SOURCE / art / 'front_frames.bin').read_bytes()[frame * 784:(frame + 1) * 784]
            assert rebuilt == expected, (species, frame, 'dictionary changed pixels')
        for switch, filename in (('-b', 'bitmask.asm'), ('-f', 'frames.asm')):
            (target / filename).write_bytes(run('pokemon_animation', switch, tilemap, target / 'front.dimensions'))
        (target / 'anim.asm').write_text('\tframe 0, 10\n\tframe 1, 08\n\tframe 2, 08\n\tframe 0, 10\n\tendanim\n')
        (target / 'anim_idle.asm').write_text('\tframe 0, 10\n\tframe 1, 08\n\tframe 0, 10\n\tendanim\n')
        (target / 'back.2bpp').write_bytes(backs[:576])
        (target / 'back_frames.bin').write_bytes(backs)
        (target / 'overflow.2bpp').write_bytes(data[98 * 16:])
        colors = [int(v) for v in re.findall(r'\d+', (source / 'front.pal').read_text().split('RGB', 1)[1])]
        assert len(colors) == 12 and all(0 <= v < 32 for v in colors)
        encoded = b''.join(struct.pack('<H', r | g << 5 | b << 10)
                           for r, g, b in zip(colors[::3], colors[1::3], colors[2::3]))
        (target / 'normal.gbcpal').write_bytes(encoded)
        (target / 'shiny.gbcpal').write_bytes(encoded)
        world = (source / 'overworld.bin').read_bytes()
        assert len(world) == 12 * 64
        # Authored source is phase-major: idle Down/Up/Left/Right, walkA,
        # walkB. Ordinary WALKING_SPRITE consumes three facings twice and
        # mirrors Left for Right. Never confuse this with contact-sheet rows.
        npc_source_frames = [0, 1, 2, 4, 5, 6]
        npc_world = b''.join(world[n * 64:(n + 1) * 64] for n in npc_source_frames)
        assert len(npc_world) == 6 * 64
        (target / 'world_npc.2bpp').write_bytes(npc_world)
        head = (source / 'head_8x8.2bpp').read_bytes()
        assert len(head) == 16
        (target / 'head_8x8.2bpp').write_bytes(head)
        indexed_source = Image.open(source / 'world_frames.png')
        assert indexed_source.mode == 'P' and indexed_source.size == (16, 192)
        for n, original in enumerate(npc_source_frames):
            assert npc_world[n * 64:(n + 1) * 64] == world[original * 64:(original + 1) * 64]
            actual_pixels = decode_world_frame(npc_world[n * 64:(n + 1) * 64])
            expected_pixels = [indexed_source.getpixel((x, original * 16 + y))
                               for y in range(16) for x in range(16)]
            assert actual_pixels == expected_pixels, (species, n, original, 'ordinary NPC tile order changed authored PNG pixels')
        for name in ('front.animated.2bpp', 'back.2bpp'):
            run('lzcompress', '--', target / name, target / (name + '.lz'))
        records[species] = {'source_art': art, 'dictionary_tiles': tiles,
                            'overflow_tiles': max(0, tiles - 98), 'front_frames': 3,
                            'back_frames': 3, 'roundtrip_all_native_front_pixels': True,
                            'npc_world_frames': 6, 'npc_world_source_frame_indices': npc_source_frames,
                            'npc_world_order': ['idle_down', 'idle_up', 'idle_left', 'walk_down', 'walk_up', 'walk_left'],
                            'npc_right_facing': 'native ordinary horizontal mirror of Left',
                            'npc_world_roundtrip_source_indices': True,
                            'npc_world_all_6_frames_decode_exact_indexed_source_png': True,
                            'files': {p.name: {'bytes': p.stat().st_size,
                                             'sha256': sha(p.read_bytes())}
                                      for p in sorted(target.iterdir()) if p.is_file()}}
    report = {'passed': True, 'source_inputs_only': True,
              'runtime_integration_verified': False, 'species_bindings': records}
    (EVIDENCE / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v['dictionary_tiles'] for k, v in records.items()}))


if __name__ == '__main__':
    main()
