#!/usr/bin/env python3
"""Four exact native bow frames in the existing twelve-tile projectile budget."""
from pathlib import Path
import hashlib
import json
from PIL import Image
from build_peon_pet_spell_assets_v026 import encode, indices

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/recruitment_v029/combat_assets'
GFX = ROOT / 'gfx/peon_combat_v029'
PALETTE = [(31, 31, 31), (25, 21, 14), (15, 10, 5), (2, 2, 2)]
FRAMES = [
    ['0000000000000000', '0000000000001000', '0030000000002100', '0003232222211110',
     '0030000000002100', '0000000000001000', '0000000000000000', '0000000000000000'],
    ['0000000000000000', '0000000000001000', '0003000000002100', '0003322222211110',
     '0003000000002100', '0000000000001000', '0000000000000000', '0000000000000000'],
    ['0000000000000000', '0000000000001000', '0030000000002100', '0003322222211110',
     '0030000000002100', '0000000000001000', '0000000000000000', '0000000000000000'],
    ['0000000000000000', '0000000000001000', '0003000000002100', '0003232222211110',
     '0003000000002100', '0000000000001000', '0000000000000000', '0000000000000000'],
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    GFX.mkdir(parents=True, exist_ok=True)
    frames = [indices(rows) for rows in FRAMES]
    packet = (ROOT / 'gfx/peon_combat_v028/projectiles.2bpp').read_bytes()[:64]
    packet += b''.join(encode(frame) for frame in frames)
    assert len(packet) == 12 * 16
    (GFX / 'arrow_projectiles.2bpp').write_bytes(packet)
    pictures = []
    for phase, frame in enumerate(frames):
        im = Image.new('RGBA', (16, 8), (0, 0, 0, 0))
        for y, row in enumerate(frame):
            for x, index in enumerate(row):
                if index:
                    im.putpixel((x, y), tuple((v << 3) | (v >> 2) for v in PALETTE[index]) + (255,))
        im.save(OUT / f'kolkar_arrow_phase_{phase:02d}_16x8.png')
        im.resize((128, 64), Image.Resampling.NEAREST).save(OUT / f'kolkar_arrow_phase_{phase:02d}_8x.png')
        pictures.append(im)
    pictures[0].save(OUT / 'kolkar_arrow_native.apng', save_all=True,
                     append_images=pictures[1:], duration=50, loop=0)
    # Keep native-observation claims tied to the immutable report and this
    # exact packet. Rebuilding source art alone cannot create a runtime PASS.
    runtime_path = OUT.parent / 'projectile_runtime/validation.json'
    try:
        runtime = json.loads(runtime_path.read_text())
    except (OSError, ValueError):
        runtime = {}
    arrow = runtime.get('cases', {}).get('kolkar_incoming', {}).get('kolkar_arrow', {})
    native_observed = bool(runtime.get('passed') and
        runtime.get('scope') == 'all_four_native_families' and
        arrow.get('native_12_tile_packet_sha256') == hashlib.sha256(packet).hexdigest() and
        arrow.get('phases') == [0, 1, 2, 3] and not arrow.get('hud_overlap'))
    (OUT / 'manifest.json').write_text(json.dumps({
        'authored_original': True, 'native_frames': 4, 'size': [16, 8],
        'alpha': [0, 255], 'palette_rgb555': PALETTE, 'packet_tiles': 12,
        'packet_sha256': hashlib.sha256(packet).hexdigest(),
        'native_sprite_objects_per_arrow_scanline': 2,
        'runtime_integrated': native_observed,
        'runtime_rom_sha256': runtime.get('rom_sha256') if native_observed else None,
        'runtime_validation_report': str(runtime_path.relative_to(ROOT)),
        'runtime_note': 'Native observation applies only to the stated immutable ROM; a future build needs its own report.' if native_observed else 'Source packet only until an exact built-ROM native animation is observed.'
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
