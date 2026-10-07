#!/usr/bin/env python3
"""Build the hand-pixelled peon sheet; no generated mockup is resized or sampled.

Each character below is one gameplay pixel. Indices match `rgbgfx --colors dmg`:
transparent white, leather (light grey), green skin (dark grey), black outline.
The game supplies the existing green overworld palette.
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PIXELS = {'.': 0, 'b': 1, 'g': 2, '#': 3}
IDLE = {
    'down': [
        '.....######.....',
        '....#gggggg#....',
        '...#gggggggg#...',
        '..#gg#gggg#gg#..',
        '...#gggggggg#...',
        '....#gbbbbg#....',
        '..##g######g##..',
        '.#bb#gbbbbgg#b#.',
        '.#bb#gbbbbgg#b#.',
        '.##b#gbbbbgg#b#.',
        '..#b#bbbbbb#bb#.',
        '..#g########bb#.',
        '...##bb#gbb###..',
        '....#bb#bbb#....',
        '....#gg##gg#....',
        '....####.###....',
    ],
    'up': [
        '.....######.....',
        '....#gggggg#....',
        '...#gggggggg#...',
        '..#gggggggggg#..',
        '...#gggggggg#...',
        '....#gggggg#....',
        '..##g######g##..',
        '.#b#ggbbbbg#bb#.',
        '.#b#ggbbbbg#bb#.',
        '.#bb#bbbbbg#b##.',
        '.#bb#bbbbbb#b#..',
        '.#bb########g#..',
        '..###bbg#bb##...',
        '....#bbb#bb#....',
        '....#gg##gg#....',
        '....####.###....',
    ],
    'left': [
        '.....######.....',
        '....#gggggg#....',
        '...#gggggggg#...',
        '..#ggg#ggggg#...',
        '..#ggggggggg#...',
        '...#bbggggg#....',
        '....######g##...',
        '.###gbbbbb#bb#..',
        '.#b#gbbbbb#bb#..',
        '.#b##bbbbg#bb#..',
        '..#g#bbbbg#bb#..',
        '...##bb#gb#bb#..',
        '.....#b##b###...',
        '.....#bb#bb#....',
        '....#gg##gg#....',
        '....####.###....',
    ],
    'right': [
        '.....######.....',
        '....#gggggg#....',
        '...#gggggggg#...',
        '...#ggggg#ggg#..',
        '...#ggggggggg#..',
        '....#gggggbb#...',
        '...##g######....',
        '..#bbb#bbbbg###.',
        '..#bbb#bbbbg#b#.',
        '..#bbb#bbbbg#b#.',
        '..#bbb#bbbb#g#..',
        '..#bbb#bg#bb##..',
        '...####b##b#....',
        '....#bb#bb#.....',
        '....#gg##gg#....',
        '....###.####....',
    ],
}


def frames():
    """VRAM layout: four idle frames, four step-A frames, four step-B frames."""
    for phase in range(3):
        for direction, idle in IDLE.items():
            rows = idle.copy()
            if phase == 1:
                rows[13:] = ['....#bb##bb#....', '...#ggg##gg#....', '...####..###....']
            elif phase == 2:
                rows[13:] = ['....#bb##bb#....', '....#gg##ggg#...', '....###..####...']
            assert len(rows) == 16 and all(len(row) == 16 for row in rows), (direction, phase)
            yield direction, phase, rows


def main():
    sheet = Image.new('P', (16, 16 * 12))
    sheet.putpalette([255, 255, 255, 170, 170, 170, 85, 85, 85, 0, 0, 0] + [0] * 756)
    for index, (_, _, rows) in enumerate(frames()):
        for y, row in enumerate(rows):
            for x, pixel in enumerate(row):
                sheet.putpixel((x, index * 16 + y), PIXELS[pixel])
    # rgbgfx's DMG palette expects opaque greyscale input; index 0 becomes
    # transparent at runtime because these tiles are rendered as OBJ sprites.
    sheet.save(ROOT / 'gfx/sprites/peon.png', optimize=False)
    output = ROOT / 'references/generated/peon_in_game'
    output.mkdir(parents=True, exist_ok=True)
    # Technical preview uses the unmodified daytime green NPC palette. No
    # invented colours or detailed mockup pixels are used in this preview.
    palette = [(36, 36, 42), (255, 156, 82), (57, 189, 24), (0, 0, 0)]
    preview = Image.new('RGB', (96, 92), palette[0])
    labels = {'down': 'FACE', 'up': 'DOS', 'left': 'GAUCHE', 'right': 'DROITE'}
    draw = ImageDraw.Draw(preview)
    for direction_index, direction in enumerate(IDLE):
        draw.text((1, direction_index * 23 + 6), labels[direction], fill=(220, 220, 220))
    for direction, phase, rows in frames():
        y_offset = list(IDLE).index(direction) * 23 + 3
        for y, row in enumerate(rows):
            for x, pixel in enumerate(row):
                preview.putpixel((40 + phase * 18 + x, y_offset + y), palette[PIXELS[pixel]])
    preview.resize((768, 736), Image.Resampling.NEAREST).save(output / 'peon_sprite_sheet_actual.png')
    print('Created gfx/sprites/peon.png: 16 x 192, 12 independent 16 x 16 frames, four indices.')


if __name__ == '__main__':
    main()
