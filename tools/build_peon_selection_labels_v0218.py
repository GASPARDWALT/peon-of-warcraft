#!/usr/bin/env python3
"""Compile four compact native menu labels into 24 reserved BG tiles.

This is small bitmap typography, not resampling character illustrations.
48px lines fit inside the annotated right-hand welcome panel.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GFX = ROOT / 'gfx/selection_labels_v0218'
SOURCE = ROOT / 'assets/selection_v0218/welcome_labels.json'
FONT = {
    'A': ['.11.', '1..1', '1..1', '1111', '1..1', '1..1'],
    'C': ['.111', '1...', '1...', '1...', '1...', '.111'],
    'E': ['1111', '1...', '111.', '1...', '1...', '1111'],
    'I': ['111.', '.1..', '.1..', '.1..', '.1..', '111.'],
    'N': ['1..1', '11.1', '11.1', '1.11', '1.11', '1..1'],
    'O': ['.11.', '1..1', '1..1', '1..1', '1..1', '.11.'],
    'P': ['111.', '1..1', '1..1', '111.', '1...', '1...'],
    'R': ['111.', '1..1', '111.', '1.1.', '1..1', '1..1'],
    'T': ['1111', '.1..', '.1..', '.1..', '.1..', '.1..'],
    'U': ['1..1', '1..1', '1..1', '1..1', '1..1', '.11.'],
    'V': ['1..1', '1..1', '1..1', '1..1', '.11.', '.11.'],
    ' ': ['....'] * 6,
}
LABELS = ('CONTINUER', 'CREER UN', 'NOUVEAU', 'PEON')


def main():
    source = {'version': 'v0.2.18', 'kind': 'authored native bitmap label glyphs',
              'advance': 5, 'glyph_dimensions': [4, 6], 'line_dimensions': [48, 8],
              'labels': LABELS, 'font': FONT}
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    SOURCE.write_text(json.dumps(source, indent=2) + '\n')
    GFX.mkdir(parents=True, exist_ok=True)
    packet = bytearray()
    preview = Image.new('RGB', (48, 32), (24, 16, 24))
    for line, text in enumerate(LABELS):
        width = len(text) * 5 - 1
        assert width <= 48
        pixels = [[0] * 48 for _ in range(8)]
        for i, char in enumerate(text):
            for y, row in enumerate(FONT[char]):
                for x, ink in enumerate(row):
                    if ink == '1':
                        px = (48 - width) // 2 + i * 5 + x
                        pixels[y + 1][px] = 3
                        preview.putpixel((px, line * 8 + y + 1), (247, 231, 181))
        for tile in range(6):
            for row in pixels:
                value = sum((row[tile * 8 + x] != 0) << (7 - x) for x in range(8))
                packet.extend((value, value))
    assert len(packet) == 24 * 16
    (GFX / 'labels.2bpp').write_bytes(packet)
    preview.save(GFX / 'labels.png')
    (GFX / 'graphics.asm').write_text('SECTION "Peon welcome compact labels v0218", ROMX\n'
        'PeonWelcomeLabelsV0218::\n\tINCBIN "gfx/selection_labels_v0218/labels.2bpp"\n'
        '\tassert @ - PeonWelcomeLabelsV0218 == 24 * TILE_SIZE\n')
    (GFX / 'manifest.json').write_text(json.dumps({'version': 'v0.2.18', 'status': 'PASS',
        'labels': LABELS, 'dimensions': [48, 8], 'tiles': 24,
        'bank': 0, 'tile_ids': [0x48, 0x5f], 'source': str(SOURCE.relative_to(ROOT)),
        'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'packet_sha256': hashlib.sha256(packet).hexdigest()}, indent=2) + '\n')
    print('24 native label tiles compiled')


if __name__ == '__main__':
    main()
