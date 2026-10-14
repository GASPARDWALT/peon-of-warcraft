#!/usr/bin/env python3
"""Derive resource strips and type ink from retained native HUD/font bytes.

No actor/decor source is drawn or replaced. Native regular glyph silhouettes
remain exact; only their 2bpp color index changes for localized colored labels.
"""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'gfx/peon_resource_hud_v0213'
LABELS = ('PHYS', 'NATURE', 'FIRE', 'SHADOW', 'FROST', 'ARCANE', 'TOXIN', 'WATER')


def remap(tile, colors):
    result = bytearray()
    for low, high in zip(tile[0::2], tile[1::2]):
        lo = hi = 0
        for bit in range(7, -1, -1):
            value = colors[(low >> bit & 1) | (high >> bit & 1) << 1]
            lo = lo << 1 | (value & 1)
            hi = hi << 1 | (value >> 1)
        result.extend((lo, hi))
    return bytes(result)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    native_hud = (ROOT / 'gfx/pack/peon_player_hud.2bpp').read_bytes()
    gauges = [native_hud[i * 16:(i + 1) * 16] for i in range(5, 14)]
    # World palette6: color2 is existing blue/cyan; color3 is dark outline.
    (OUT / 'world_mana_gauges.2bpp').write_bytes(b''.join(remap(g, (0, 3, 3, 2)) for g in gauges))
    # Battle palette3 color1 is independent of native HP color2/black frame.
    (OUT / 'battle_resource_gauges.2bpp').write_bytes(b''.join(remap(g, (0, 3, 0, 1)) for g in gauges))
    font_path = ROOT / 'gfx/font/peon_regular_v026.1bpp'
    font = font_path.read_bytes()
    charmap = {match[1]: int(match[2], 16) for match in re.finditer(
        r'charmap\s+"([^"\n]+)",\s+\$([0-9a-f]+)',
        (ROOT / 'constants/charmap.asm').read_text())}
    for label in LABELS:
        output = bytearray()
        for char in label.ljust(6):
            code = charmap[char]
            if char == ' ':
                glyph = bytes(8)
            else:
                glyph = font[(code - 0x80) * 8:(code - 0x80 + 1) * 8]
            assert len(glyph) == 8
            for row in glyph:
                output.extend((row, 0))  # exact native ink, palette color1
        (OUT / (label.lower() + '.2bpp')).write_bytes(output)
    # Protect the two borrowed color1 slots against later art/engine changes.
    for name in ('gfx/battle/expbar.2bpp', 'gfx/font/font_battle_extra.2bpp'):
        data = (ROOT / name).read_bytes()
        selected = data if 'expbar' in name else data[2 * 16:11 * 16]
        for low, high in zip(selected[0::2], selected[1::2]):
            assert not (low & ~high), ('Native bar started using color1', name)
    report = {'sources': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in (font_path, ROOT / 'gfx/pack/peon_player_hud.2bpp')},
              'glyph_labels': list(LABELS), 'native_font_silhouettes_unchanged': True,
              'actor_and_decor_sources_modified': False, 'new_saved_bytes': 0}
    (OUT / 'provenance.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
