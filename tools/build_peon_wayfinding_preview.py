#!/usr/bin/env python3
"""Render retained native map geometry with the clearer current path palettes.

This does not run the historical world generator. It refreshes palette inputs
and writes compiler previews of the current maps in a new directory.
Native runtime captures are produced separately by emulator validators.
"""
import hashlib
import json
from pathlib import Path

from PIL import Image

from build_durotar_world import BG, DIMS, REGION_BGS, palfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/valley_layout_update/world'


def expanded(colour):
    return tuple(((c >> 3) << 3) | ((c >> 3) >> 2) for c in colour)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'maps').mkdir(exist_ok=True)
    (ROOT / 'gfx/tilesets/peon_bg.pal').write_text(palfile(BG))
    (ROOT / 'gfx/tilesets/peon_regions.pal').write_text(
        ''.join(palfile(pals) for pals in REGION_BGS.values()))
    sheet = Image.open(ROOT / 'gfx/tilesets/peon.png')
    assert sheet.mode == 'P' and set(sheet.getdata()) <= {0, 1, 2, 3}
    metatiles = (ROOT / 'data/tilesets/peon_metatiles.bin').read_bytes()
    attributes = (ROOT / 'gfx/tilesets/peon_palette_map.bin').read_bytes()
    report = {'source': 'Compiler reconstruction of committed native map blocks.',
              'runtime_capture': False,
              'geometry_changes': ['The Den block (4,3): boulder to merchant alcove floor.'],
              'maps': {}}
    for name, (width, height) in DIMS.items():
        blocks = (ROOT / 'maps' / (name + '.blk')).read_bytes()
        assert len(blocks) == width * height, name
        palettes = REGION_BGS.get(name, BG)
        canvas = Image.new('RGB', (width * 32, height * 32))
        for offset, block in enumerate(blocks):
            for tile_offset, tile_id in enumerate(metatiles[block*16:block*16+16]):
                native_index = tile_id if tile_id < 96 else tile_id - 32
                tx, ty = (native_index % 16) * 8, (native_index // 16) * 8
                tile = sheet.crop((tx, ty, tx + 8, ty + 8))
                packed = attributes[tile_id // 2]
                palette_id = ((packed >> (4 * (tile_id % 2))) & 15) & 7
                palette = [v for colour in palettes[palette_id] for v in expanded(colour)]
                tile.putpalette(palette + [0] * (768 - len(palette)))
                x = (offset % width) * 32 + (tile_offset % 4) * 8
                y = (offset // width) * 32 + (tile_offset // 4) * 8
                canvas.paste(tile.convert('RGB'), (x, y))
        canvas.save(OUT / 'maps' / (name + '.png'))
        canvas.resize((width * 64, height * 64), Image.Resampling.NEAREST).save(
            OUT / 'maps' / (name + '_2x.png'))
        report['maps'][name] = {
            'native_pixel_size': list(canvas.size),
            'retained_block_sha256': hashlib.sha256(blocks).hexdigest(),
            'path_rgb555': [[v >> 3 for v in c] for c in palettes[4]]}
    (OUT / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Refreshed path palettes and reconstructed nine retained maps; no layout changes.')


if __name__ == '__main__':
    main()
