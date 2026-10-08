#!/usr/bin/env python3
"""Compile a hand-pixelled live HUD; retain native and transparent PNG assets."""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/valley_layout_update/hud'
GFX = ROOT / 'gfx/pack'
PIXELS = {'.': 0, 'b': 1, 'g': 2, '#': 3}
FACE = [
    'bbbbbbbbbbbbbbbb',
    'b####gggggg####b',
    'b###gggggggg###b',
    'b##gggggggggg##b',
    'bggggggggggggggb',
    'bggg##gggg##gggb',
    'b#gg##gggg##gg#b',
    'b##gggggggggg##b',
    'b##gggbbggggg##b',
    'b###g#gggg#g###b',
    'b###gb####bg###b',
    'b####gbbbbg####b',
    'b#####gggg#####b',
    'b###bbbbbbbb###b',
    'b##bb######bb##b',
    'bbbbbbbbbbbbbbbb',
]
HEAD = [
    '..####..',
    '.#gggg#.',
    '#gggggg#',
    '#g#gg#g#',
    '.#gggg#.',
    '.#gbbg#.',
    '..####..',
    '...bb...',
]
PALETTE_FACE = [(255,255,255), (148,90,49), (123,181,66), (8,8,8)]
PALETTE_GAUGE = [(255,255,255), (181,66,33), (41,16,16), (255,41,24)]
GRAY = [255,255,255,170,170,170,85,85,85,0,0,0] + [0] * 756


def two_bpp(tile):
    data = bytearray()
    for row in tile:
        lo = hi = 0
        for value in row:
            lo = lo << 1 | int(value) & 1
            hi = hi << 1 | int(value) >> 1 & 1
        data.extend((lo, hi))
    return bytes(data)


def rgba(values, colors):
    rgb = np.array(colors, dtype='uint8')[values]
    alpha = np.where(values == 0, 0, 255).astype('uint8')
    return Image.fromarray(np.dstack((rgb, alpha)), 'RGBA')


def main():
    OUT.mkdir(parents=True, exist_ok=True); GFX.mkdir(parents=True, exist_ok=True)
    face = np.array([[PIXELS[c] for c in row] for row in FACE], dtype='uint8')
    head = np.array([[PIXELS[c] for c in row] for row in HEAD], dtype='uint8')
    assert face.shape == (16,16) and head.shape == (8,8)
    tiles = [face[y:y+8,x:x+8] for y in (0,8) for x in (0,8)] + [head]
    for fill in range(9):
        gauge = np.full((8,8), 2, dtype='uint8')
        gauge[0,:] = gauge[-1,:] = 1
        gauge[1:7,:fill] = 3
        tiles.append(gauge)
    assert len(tiles) == 14
    binary = b''.join(two_bpp(tile) for tile in tiles)
    assert len(binary) == 224
    (GFX / 'peon_player_hud.2bpp').write_bytes(binary)
    # A normal grayscale engine sheet is reproducible with RGBDS as well.
    sheet = Image.fromarray(np.concatenate(tiles, axis=0), 'P')
    sheet.putpalette(GRAY); sheet.save(GFX / 'peon_player_hud.png')
    rgba(face, PALETTE_FACE).save(OUT / 'peon_hud_portrait.png')
    rgba(head, PALETTE_FACE).save(OUT / 'peon_hud_small_head.png')
    gauges = np.concatenate(tiles[5:], axis=1)
    rgba(gauges, PALETTE_GAUGE).save(OUT / 'peon_hud_hp_tiles.png')
    preview = Image.new('RGBA', (52,16))
    preview.paste(rgba(face, PALETTE_FACE), (0,0))
    preview.paste(rgba(np.concatenate([tiles[13]]*4, axis=1), PALETTE_GAUGE), (18,1))
    preview.save(OUT / 'peon_hud_full_asset_preview.png')
    preview.resize((416,128), Image.Resampling.NEAREST).save(OUT / 'peon_hud_full_asset_preview_8x.png')
    report = {'native_binary':str((GFX/'peon_player_hud.2bpp').relative_to(ROOT)),
        'native_binary_sha256':hashlib.sha256(binary).hexdigest(), 'tiles':14, 'bytes':224,
        'native_vram_bank':0, 'native_vram_range':['0x8600','0x86df'],
        'full_oam_objects':8, 'compact_oam_objects':4, 'life_source':'wPartyMon1HP / wPartyMon1MaxHP',
        'save_layout_changed':False, 'mana_system_added':False,
        'palette_writes':False, 'portrait_palette':2, 'life_palette':0,
        'note':'Asset previews only; *_in_rom captures are actual emulator output.'}
    (OUT/'asset_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
