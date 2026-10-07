#!/usr/bin/env python3
"""Compile six Warcraft village NPC concepts to the native Crystal NPC format.

Run from any directory: python3 tools/build_durotar_village_assets.py
The committed transparent concept is the reproducible source. Engine PNGs are
indexed grayscale build inputs: index zero becomes OBJ transparency at runtime.
Public PNGs use the exact three opaque RGB555 colors plus alpha zero/255.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v021/village_assets'
SOURCE = OUT / 'concept_village_npcs.png'
DIRS = ('down', 'up', 'left', 'right')
NAMES = ('troll_guard', 'troll_fisher', 'troll_caster',
         'orc_guard', 'orc_vendor', 'orc_questgiver')
TROLL = ((255, 255, 255), (239, 222, 181), (82, 165, 189), (16, 33, 57))
ORC = ((255, 255, 255), (148, 90, 49), (123, 181, 66), (8, 8, 8))
GRAY = (255, 255, 255, 170, 170, 170, 85, 85, 85, 0, 0, 0) + (0,) * 756
LABELS = ('PeonTrollGuardGFX', 'PeonTrollFisherGFX', 'PeonTrollCasterGFX',
          'PeonOrcGuardGFX', 'PeonOrcVendorGFX', 'PeonOrcQuestgiverGFX')


def row_spans(source):
    """Find the six foreground rows; generator cells are not exact equal boxes."""
    mask = np.array(source.getchannel('A')) >= 180
    occupied = np.any(mask, axis=1)
    spans, start = [], None
    for y, full in enumerate(occupied):
        if full and start is None:
            start = y
        elif not full and start is not None:
            spans.append((start, y))
            start = None
    if start is not None:
        spans.append((start, source.height))
    assert len(spans) == 6, f'Expected six isolated rows, got {spans}'
    return spans


def quantize(source, palette):
    pixels = np.array(source.convert('RGBA'))
    colors = np.array(palette[1:], dtype=float)
    distances = ((pixels[:, :, None, :3].astype(float) - colors) ** 2).sum(-1)
    values = (distances.argmin(-1) + 1).astype('uint8')
    values[pixels[:, :, 3] < 180] = 0
    out = Image.fromarray(values, 'P')
    out.putpalette([n for color in palette for n in color] + [0] * 756)
    return out


def native(source, span, column, palette):
    cell = source.crop((column * source.width // 4, span[0],
                        (column + 1) * source.width // 4, span[1]))
    bounds = cell.getchannel('A').point(lambda a: 255 if a >= 180 else 0).getbbox()
    assert bounds, (span, column)
    cell = cell.crop(bounds)
    cell.thumbnail((14, 15), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (16, 16))
    canvas.paste(cell, ((16 - cell.width) // 2, 16 - cell.height))
    return quantize(canvas, palette)


def rgba(frame):
    alpha = np.where(np.array(frame) == 0, 0, 255).astype('uint8')
    return Image.fromarray(np.dstack((np.array(frame.convert('RGB')), alpha)), 'RGBA')


def step(frame):
    """Shift weight between the two feet without relocating a NPC's silhouette."""
    out = frame.copy()
    # Only the lowest three rows are animated: head and held tools remain stable.
    out.paste(0, (0, 13, 16, 16))
    out.paste(frame.crop((0, 13, 8, 16)), (0, 12))
    out.paste(frame.crop((8, 13, 16, 16)), (8, 13))
    return out


def readable_face(name, frame):
    """Pin face landmarks that disappear when source art is reduced to 16 pixels.

    This is a deterministic native conversion rule: the three-color limit cannot
    preserve sub-pixel eyes or tusks by ordinary resampling alone. One dark pixel
    per eye and one ivory pixel per tusk make the race readable at actual size.
    """
    out = frame.copy()
    d = ImageDraw.Draw(out)
    if name == 'troll_guard':
        d.rectangle((5, 6, 9, 9), fill=2)
        d.point((4, 6), fill=2); d.point((10, 6), fill=2)
        d.point((5, 7), fill=3); d.point((9, 7), fill=3)
        d.line((7, 9, 8, 9), fill=3)
        d.point((5, 9), fill=1); d.point((9, 9), fill=1)
        d.rectangle((6, 2, 7, 4), fill=3)
    elif name == 'troll_fisher':
        d.rectangle((5, 6, 9, 8), fill=2)
        d.point((5, 6), fill=3); d.point((9, 6), fill=3)
        d.point((5, 8), fill=1); d.point((9, 8), fill=1)
        d.point((7, 8), fill=3)
    elif name == 'troll_caster':
        d.rectangle((5, 6, 9, 9), fill=2)
        d.point((4, 6), fill=2); d.point((10, 6), fill=2)
        d.point((5, 7), fill=3); d.point((9, 7), fill=3)
        d.line((7, 9, 8, 9), fill=3)
        d.point((5, 9), fill=1); d.point((9, 9), fill=1)
        d.line((7, 1, 7, 4), fill=3)
    elif name == 'orc_guard':
        d.rectangle((5, 6, 9, 8), fill=2)
        d.point((5, 7), fill=3); d.point((9, 7), fill=3)
        d.point((7, 8), fill=3)
    elif name == 'orc_vendor':
        d.point((6, 6), fill=3); d.point((9, 6), fill=3)
    elif name == 'orc_questgiver':
        d.point((5, 7), fill=3); d.point((9, 7), fill=3)
    return out


def exports(name, idle, walking):
    dest = OUT / name
    dest.mkdir(parents=True, exist_ok=True)
    # The right-facing NPC is reflected by the existing Crystal engine.
    phase_b = [ImageOps.mirror(walking[i]) if i < 2 else idle[i].copy()
               for i in range(4)]
    frames = [rgba(frame) for phase in (idle, walking, phase_b) for frame in phase]
    labels = [f'{direction}_step_{phase}' for phase in range(3) for direction in DIRS]
    sheet = Image.new('RGBA', (16 * len(frames), 16))
    for i, (frame, label) in enumerate(zip(frames, labels)):
        frame.save(dest / f'{label}.png')
        sheet.paste(frame, (16 * i, 0))
    sheet.save(dest / 'sheet.png')
    frames[0].save(dest / 'animation.png', save_all=True,
                   append_images=frames[1:], duration=160, loop=0,
                   disposal=1, blend=0)
    preview = []
    for frame in frames:
        canvas = Image.new('RGBA', (16, 16), (41, 33, 39, 255))
        canvas.alpha_composite(frame)
        preview.append(canvas.resize((128, 128), Image.Resampling.NEAREST).convert('RGB'))
    preview[0].save(dest / 'preview.gif', save_all=True,
                    append_images=preview[1:], duration=160, loop=0)
    # Include exactly the six source frames used by the ROM, in source order.
    engine = Image.new('RGBA', (16, 96))
    for i, frame in enumerate(idle[:3] + walking[:3]):
        engine.paste(rgba(frame), (0, 16 * i))
    engine.save(dest / 'native_npc_sheet.png')
    return frames


def main():
    source = Image.open(SOURCE).convert('RGBA')
    spans = row_spans(source)
    all_frames = {}
    manifest = {
        'concept_source': str(SOURCE.relative_to(ROOT)),
        'concept_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'native_size': [16, 16], 'npc_engine_frames': 6,
        'npc_engine_sheet': [16, 96],
        'npc_engine_order': ['down_idle', 'up_idle', 'left_idle',
                             'down_step', 'up_step', 'left_step'],
        'right_facing': 'Mirrored left by the standard Crystal NPC renderer.',
        'troll_palette_index': 6,
        'troll_palette_rgb555': [[c >> 3 for c in color] for color in TROLL],
        'orc_palette_index': 2,
        'characters': [],
    }
    for row, (name, label) in enumerate(zip(NAMES, LABELS)):
        palette = TROLL if row < 3 else ORC
        idle = [native(source, spans[row], col, palette) for col in range(3)]
        idle[0] = readable_face(name, idle[0])
        idle.append(ImageOps.mirror(idle[2]))
        walking = [step(frame) for frame in idle[:3]]
        walking.append(ImageOps.mirror(walking[2]))
        all_frames[name] = exports(name, idle, walking)
        indexed = Image.new('P', (16, 96))
        indexed.putpalette(GRAY)
        for i, frame in enumerate(idle[:3] + walking[:3]):
            indexed.paste(frame, (0, 16 * i))
        target = ROOT / f'gfx/sprites/peon_{name}.png'
        indexed.save(target)
        colors = sorted(set(np.array(indexed).ravel()))
        assert len(colors) <= 4 and colors[0] == 0, (name, colors)
        manifest['characters'].append({'name': name, 'label': label,
                                       'engine_png': str(target.relative_to(ROOT)),
                                       'opaque_colors': len(colors) - 1,
                                       'public_frames': 12})
    # An opaque contact preview remains readable on GitHub; sprite files stay RGBA.
    preview = Image.new('RGB', (672, 6 * 158), (41, 33, 39))
    draw = ImageDraw.Draw(preview)
    for row, name in enumerate(NAMES):
        draw.text((10, row * 158 + 5), name.replace('_', ' ').upper(), fill=(239, 222, 181))
        for col, frame in enumerate(all_frames[name][:4]):
            enlarged = frame.resize((128, 128), Image.Resampling.NEAREST)
            preview.paste(enlarged, (132 + 132 * col, row * 158 + 22), enlarged)
    preview.save(OUT / 'native_npc_preview.png')
    (OUT / 'asset_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    asm = ['; Native Warcraft NPC sheets: six frames, 16x16 each.',
           '; Referenced from data/sprites/sprites.asm by the integration.',
           'SECTION "Peon Village NPC Sprites", ROMX', '']
    for name, label in zip(NAMES, LABELS):
        asm.append(f'{label}:: INCBIN "gfx/sprites/peon_{name}.2bpp"')
    (ROOT / 'gfx/peon_village_sprites.asm').write_text('\n'.join(asm) + '\n')
    (OUT / 'README.md').write_text(
        '# Native Warcraft village NPCs\n\n'
        'These 16×16 sprites are the native game assets, enlarged without smoothing below. '
        'The larger concept is a source reference. NPCs use three opaque colors plus '
        'transparency; right-facing sprites use Crystal’s normal reflection.\n\n'
        '![Native NPC preview](native_npc_preview.png)\n\n'
        + '\n'.join(f'**{name.replace("_", " ")}** — ![{name}]({name}/preview.gif)\n'
                     for name in NAMES)
        + '\nEach character folder contains twelve transparent frame PNGs, a transparent '
        '`sheet.png`, `animation.png` (APNG), and the exact six-frame '
        '`native_npc_sheet.png` used by the engine. These six NPC roles are a starting '
        'population, not a complete reproduction of Classic’s NPC roster.\n\n'
        'Regenerate with `python3 tools/build_durotar_village_assets.py`.\n')
    print(json.dumps({'characters': len(NAMES), 'npc_frames_each': 6,
                      'native_size': [16, 16], 'opaque_colors': 3,
                      'public_folder': str(OUT.relative_to(ROOT))}))


if __name__ == '__main__':
    main()
