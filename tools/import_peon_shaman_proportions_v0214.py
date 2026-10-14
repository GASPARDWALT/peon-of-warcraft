#!/usr/bin/env python3
"""Adjust the archived Shaman's head/body ratio using its existing pixels.

No drawing, palette change, smoothing or original-file replacement. The native
pose masks isolate the skull from the nearby mace and clothes. All transforms
use nearest sampling and retain the 48x48/56x56 loader contracts.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from import_peon_native_actors_v0213 import decode, preview, HERO_PALETTE
from build_peon_user_battle_v0211 import encode

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'gfx/native_actor_restore_v0213/peon'
OUTPUT = ROOT / 'gfx/shaman_proportions_v0214'
REPORT = ROOT / 'references/generated/shaman_proportions_v0214'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def isolate_head(source, rows, offset=(0, 0)):
    """Copy only the measured head region; keep nearby gear out of its mask."""
    image = source.copy()
    head = Image.new('P', source.size)
    dx, dy = offset
    for start_y, end_y, left, right in rows:
        for y in range(start_y + dy, end_y + dy):
            for x in range(left + dx, right + dx):
                head.putpixel((x, y), source.getpixel((x, y)))
                image.putpixel((x, y), 0)
    return image, head.crop(head.getbbox())


def overlay(destination, source, x, y):
    # Native index0 is transparent. Do not fill eyes, teeth or weapon holes.
    mask = Image.fromarray((np.asarray(source) != 0).astype('uint8') * 255)
    destination.paste(source, (x, y), mask)


def resize(source, size):
    return source.resize(size, Image.Resampling.NEAREST)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    records, frames = [], {'back': [], 'front': []}
    rear_rows = [(4, 12, 16, 39), (12, 13, 13, 39),
                 (13, 19, 14, 39), (19, 20, 16, 37)]
    face_rows = [(7, 14, 20, 40), (14, 16, 19, 40), (16, 24, 16, 44),
                 (24, 28, 20, 41), (28, 29, 22, 40)]
    back_packet, front_packet = (SOURCE / 'back_frames.bin').read_bytes(), (SOURCE / 'front_frames.bin').read_bytes()
    assert len(back_packet) == 3 * 576 and len(front_packet) == 3 * 784
    for view, size, stride, packet in [('back', 48, 576, back_packet), ('front', 56, 784, front_packet)]:
        for phase in range(3):
            original = decode(packet[phase * stride:(phase + 1) * stride], size, size)
            if view == 'back':
                offset = [(0, 0), (-1, -1), (-1, 0)][phase]
                body, head = isolate_head(original, rear_rows, offset)
                if phase == 1:
                    # Copy only the existing collar's next row into its old
                    # transparent seam. Weapon, shield and torso stay intact.
                    for x in range(14, 32):
                        if not body.getpixel((x, 20)):
                            body.putpixel((x, 20), original.getpixel((x, 19)))
                # 18x13 before the modest whole-frame normalization produces
                # a 16px-wide skull, instead of the old 25px-wide skull.
                overlay(body, resize(head, (18, 13)), 17 + offset[0], 7 + offset[1])
                result = Image.new('P', (48, 48))
                result.paste(resize(body, (44, 44)), (2, 0))
                operation = 'Head nearest 18x13 at original neck; full canvas nearest 44x44 centered in 48x48, feet at y44.'
                if phase == 1:
                    operation += ' Collar seam at y20,x14:32 copies its original y19 source row only into alpha-zero cells.'
            elif phase < 2:
                offset = (0, -phase)
                body, head = isolate_head(original, face_rows, offset)
                overlay(body, resize(head, (18, 16)), 21, 13 - phase)
                # Idle gear/body stay at their original native scale.
                # Their alpha bbox starts below y6; this shift clips no pixel.
                assert not any(body.getpixel((x, y)) for y in range(6) for x in range(56))
                result = Image.new('P', (56, 56))
                result.paste(body, (0, -6))
                operation = 'Head nearest 18x16 at original neck; intact body/gear translated up6, feet at y50.'
            else:
                # The turned casting skull already has a normal ratio. Fit
                # its complete aura too, rather than clipping the top sparks.
                result = Image.new('P', (56, 56))
                result.paste(resize(original, (50, 50)), (3, 0))
                operation = 'Complete existing turned casting pose and aura nearest 50x50 centered in 56x56; no separate skull replacement.'
            assert set(result.get_flattened_data()) <= set(original.get_flattened_data())
            frames[view].append(result)
            preview(original, HERO_PALETTE, REPORT / f'{view}_before_{phase}.png')
            preview(result, HERO_PALETTE, REPORT / f'{view}_{phase}.png')
            records.append({'view': view, 'pose': phase, 'before_bbox': original.getbbox(),
                            'after_bbox': result.getbbox(), 'operation': operation,
                            'indexed_before_sha256': sha(original.tobytes()),
                            'indexed_after_sha256': sha(result.tobytes())})
    outputs = {
        'back_frames.bin': b''.join(encode(np.asarray(im), column_major=True) for im in frames['back']),
        'front_frames.bin': b''.join(encode(np.asarray(im), column_major=True) for im in frames['front']),
        'portrait_frames.bin': b''.join(encode(np.asarray(im), column_major=False) for im in frames['front']),
    }
    for name, data in outputs.items():
        (OUTPUT / name).write_bytes(data)
        size = 48 if name.startswith('back') else 56
        stride = size * size // 4
        for phase in range(3):
            reconstructed = decode(data[phase * stride:(phase + 1) * stride], size, size,
                                   column_major=name != 'portrait_frames.bin')
            assert reconstructed.tobytes() == frames['back' if size == 48 else 'front'][phase].tobytes()
    manifest = {'version': 'v0.2.14', 'source': str(SOURCE.relative_to(ROOT)),
                'source_hashes': {'back_frames.bin': sha(back_packet), 'front_frames.bin': sha(front_packet)},
                'requested_change': 'Shaman head/body proportions aligned to other heroes; keep archived design and equipment.',
                'dimensions': {'back': [48, 48], 'front': [56, 56]},
                'nearest_only': True, 'original_sources_unchanged': True,
                'palette_and_alpha_index_unchanged': True, 'poses': records,
                'outputs': {name: sha(data) for name, data in outputs.items()},
                'runtime_tested': False}
    (REPORT / 'import_report.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    if args.apply:
        p = ROOT / 'engine/menus/peon_class_graphics.asm'
        source = p.read_text()
        for name in outputs:
            source = source.replace('"gfx/native_actor_restore_v0213/peon/' + name + '"',
                                    '"gfx/shaman_proportions_v0214/' + name + '"')
        p.write_text(source)
        p = ROOT / 'gfx/user_battle_v0211/data.asm'
        source = p.read_text()
        start = source.index('SECTION "User Shaman Battle v0211"')
        end = source.index('SECTION "User Warrior Battle v0211"', start)
        section = source[start:end]
        for name in outputs:
            section = section.replace('"gfx/native_actor_restore_v0213/peon/' + name + '"',
                                      '"gfx/shaman_proportions_v0214/' + name + '"')
        p.write_text(source[:start] + section + source[end:])
    print(json.dumps({'native_frames_decoded_exactly': 9, 'poses': records}))


if __name__ == '__main__':
    main()
