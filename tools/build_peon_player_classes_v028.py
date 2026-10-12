#!/usr/bin/env python3
"""Draw reusable Orc apprentice art directly on Crystal's native pixel grids.

These are authored pixels, not resized concept art. All output is versioned:
published v026 art and the existing saved actor IDs remain untouched.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'gfx/peon_classes_v028'
OUT = ROOT / 'references/generated/polish_v028/classes'
CLASSES = ('shaman', 'warrior', 'warlock')
DIRECTIONS = ('down', 'up', 'left', 'right')
POSES = ('idle', 'ready', 'release')
WORLD_PALETTE = [(31, 31, 31), (18, 11, 6), (15, 22, 8), (1, 1, 1)]
BATTLE_PALETTE = [(31, 31, 31), (15, 22, 8), (18, 11, 6), (0, 0, 0)]
DMG = [255, 255, 255, 170, 170, 170, 85, 85, 85, 0, 0, 0] + [0] * 756

# Three opaque object colors. Ears, brow and the robe's hem remain readable at
# 16 pixels; white tusks are reserved for the BG battle art, which has index0.
WORLD = {
    'warlock': {
        'down': [
            '.....######.....', '....#bbbbbb#....', '...#bbggggbb#...',
            '..#ggg#gg#ggg#..', '...#gggggggg#...', '....#gbbbbg#....',
            '..b..######.....', '..b.#gbbbbg#....', '..b#ggbbbbgg#...',
            '.bbb#gbbbbg#....', '..b..#bbbb#.....', '..b.#b#bb#b#....',
            '..b.#bbbbbb#....', '....#bb##bb#....', '....#gg##gg#....',
            '....###..###....'],
        'up': [
            '.....######.....', '....#bbbbbb#....', '...#bbbbbbbb#...',
            '..#gbbbbbbbbg#..', '...#bbbbbbbb#...', '....#bbbbbb#....',
            '.....######..b..', '....#gbbbbg#.b..', '...#ggbbbbgg#b..',
            '....#gbbbbg#bbb.', '.....#bbbb#..b..', '....#b#bb#b#.b..',
            '....#bbbbbb#.b..', '....#bb##bb#....', '....#gg##gg#....',
            '....###..###....'],
        'left': [
            '.....######.....', '....#bbbbbb#....', '...#bgggbbbb#...',
            '..#gg#ggbbbb#...', '..#gggggbbbb#...', '...#gbggbbb#....',
            '..b.######b#....', '..b.#ggbbbb#....', '.bbb#ggbbbb#....',
            '..b.#gbbbbb#....', '..b..#bbbb#.....', '..b.#b#bbb#.....',
            '..b.#bbbbbb#....', '....#bb##bb#....', '...#ggg##gg#....',
            '...####..###....'],
        'right': [
            '.....######.....', '....#bbbbbb#....', '...#bbbbgggb#...',
            '...#bbbbgg#gg#..', '...#bbbbggggg#..', '....#bbbggbg#...',
            '....#b######.b..', '....#bbbbgg#.b..', '....#bbbbgg#bbb.',
            '....#bbbbbg#.b..', '.....#bbbb#..b..', '.....#bbb#b#.b..',
            '....#bbbbbb#.b..', '....#bb##bb#....', '....#gg##ggg#...',
            '....###..####...'],
    },
    'warrior': {
        'down': [
            '......bbbb......', '.....#bggb#.....', '....#gggggg#....',
            '...#gg#gg#gg#...', '....#gggggg#....', '.....#bbbb#.....',
            '..b.##gbbg##....', '.bb#gg#bb#gg#...', '.bb#gg#bb#gg#...',
            '..b#bg#bb#gg#...', '...###bbbb###...', '....#bb##bb#....',
            '....#bb##bb#....', '....#gg##gg#....', '....#bg##gb#....',
            '....###..###....'],
        'up': [
            '......bbbb......', '.....#bggb#.....', '....#gggggg#....',
            '...#gggggggg#...', '....#gggggg#....', '.....#gggg#.....',
            '....##gbbg##.b..', '...#gg#bb#gg#bb.', '...#gg#bb#gg#bb.',
            '...#gb#bb#gb#b..', '....##bbbb##....', '....#bb##bb#....',
            '....#bb##bb#....', '....#gg##gg#....', '....#bg##gb#....',
            '....###..###....'],
        'left': [
            '......bbbb......', '.....#bggb#.....', '....#gggggg#....',
            '...#gg#gggg#....', '...#ggggggg#....', '....#bbggg#.....',
            '..b..######.....', '.bb#gg#bbbb#....', '.bb#gg#bbbb#....',
            '..b#bg#bbbb#....', '...###bbbb##....', '....#bb##bb#....',
            '....#bb##bb#....', '....#gg##gg#....', '...#bgg##gb#....',
            '...####..###....'],
        'right': [
            '......bbbb......', '.....#bggb#.....', '....#gggggg#....',
            '....#gggg#gg#...', '....#ggggggg#...', '.....#gggbb#....',
            '.....######.b...', '....#bbbb#gg#bb.', '....#bbbb#gg#bb.',
            '....#bbbb#gb#b..', '....##bbbb###...', '....#bb##bb#....',
            '....#bb##bb#....', '....#gg##gg#....', '....#bg##ggb#...',
            '....###..####...'],
    },
    'shaman': {
        'down': [
            '......bbbb......', '.....#bggb#.....', '....#gggggg#....',
            '...#gg#gg#gg#...', '....#gggggg#....', '.....#bbbb#.....',
            '.b..##gbbg##....', 'bbb#gg#bb#gg##..', '.b.#gg#bb#g#bb#.',
            '.b.#bg#bb#g#bb#.', '.b.###bgbb#bbb#.', '....#bb##bb###..',
            '....#bb##bb#....', '....#gg##gg#....', '....#bg##gb#....',
            '....###..###....'],
        'up': [
            '......bbbb......', '.....#bggb#.....', '....#gggggg#....',
            '...#gggggggg#...', '....#gggggg#....', '.....#gggg#.....',
            '....##gbbg##..b.', '..##gg#bb#gg#bbb', '.#bb#g#bb#gg#.b.',
            '.#bb#g#bb#gb#.b.', '.#bbb#bbgb###.b.', '..###bb##bb#..b.',
            '....#bb##bb#....', '....#gg##gg#....', '....#bg##gb#....',
            '....###..###....'],
        'left': [
            '......bbbb......', '.....#bggb#.....', '....#gggggg#....',
            '...#gg#gggg#....', '...#ggggggg#....', '....#bbggg#.....',
            '.b...######.....', 'bbb#gg#bbb###...', '.b.#gg#bb#bbb#..',
            '.b.#bg#bb#bbb#..', '.b.###bbg#bbb#..', '....#bb###bb#...',
            '....#bb##bb#....', '....#gg##gg#....', '...#bgg##gb#....',
            '...####..###....'],
        'right': [
            '......bbbb......', '.....#bggb#.....', '....#gggggg#....',
            '....#gggg#gg#...', '....#ggggggg#...', '.....#gggbb#....',
            '.....######...b.', '...###bbb#gg#bbb', '..#bbb#bb#gg#.b.',
            '..#bbb#bb#gb#.b.', '..#bbb#gbb###.b.', '...#bb###bb#..b.',
            '....#bb##bb#....', '....#gg##gg#....', '....#bg##ggb#...',
            '....###..####...'],
    },
}


class Paint:
    def __init__(self, size):
        self.pixels = Image.new('L', size, 0)
        self.mask = Image.new('L', size, 0)
        self.d, self.m = ImageDraw.Draw(self.pixels), ImageDraw.Draw(self.mask)

    def shape(self, method, xy, fill, **kwargs):
        getattr(self.d, method)(xy, fill=fill, **kwargs)
        getattr(self.m, method)(xy, fill=255, **kwargs)

    def polygon(self, xy, fill): self.shape('polygon', xy, fill)
    def rectangle(self, xy, fill): self.shape('rectangle', xy, fill)
    def line(self, xy, fill, width=1): self.shape('line', xy, fill, width=width)
    def point(self, xy, fill): self.shape('point', xy, fill)

    def stamp(self, rows, x, y, values=None):
        values = values or {'K': 3, 'B': 2, 'G': 1, 'W': 0}
        for dy, row in enumerate(rows):
            for dx, cell in enumerate(row):
                if cell != '.': self.point((x + dx, y + dy), values[cell])


def world_frames(cls):
    result = []
    values = {'.': 0, 'b': 1, 'g': 2, '#': 3}
    for phase in range(3):
        for direction in DIRECTIONS:
            rows = WORLD[cls][direction]
            assert len(rows) == 16 and all(len(row) == 16 for row in rows), (cls, direction)
            pixels = Image.new('L', (16, 16))
            for y, row in enumerate(rows):
                for x, cell in enumerate(row): pixels.putpixel((x, y), values[cell])
            # The head/tool stays anchored while both leg contours are redrawn.
            # A lateral step differs from a frontal step rather than reusing
            # the same footprint in all directions.
            if phase:
                d = ImageDraw.Draw(pixels)
                d.rectangle((3, 13, 12, 15), fill=0)
                if direction in ('down', 'up'):
                    left, right = ((3, 9) if phase == 1 else (4, 10))
                    for x, top in ((left, 13 if phase == 1 else 14), (right, 14 if phase == 1 else 13)):
                        d.rectangle((x, top, x + 2, 14), fill=2)
                        d.line((x, 15, x + 2, 15), fill=3)
                        d.point((x + 1, 14), fill=1)
                else:
                    near, far = ((3, 9) if phase == 1 else (5, 10))
                    d.line((near, 13, near + 2, 14), fill=2, width=2)
                    d.line((near - 1, 15, near + 2, 15), fill=3)
                    d.line((far, 13, far, 14), fill=2, width=2)
                    d.line((far, 15, far + 2, 15), fill=3)
                if cls == 'warlock':
                    d.line((5, 12, 10, 12), fill=1)
            result.append((pixels, pixels.point(lambda v: 255 if v else 0)))
    return result


FRONT_FACE = [
    '......KKKKKKKKKK.......',
    '....KKGGGGGGGGGGKK.....',
    '...KGGGGGGGGGGGGGGK....',
    '..KGGGGGGGGGGGGGGGGK...',
    '.KGGGGGGGGGGGGGGGGGGK..',
    'KGGGGGGGGGGGGGGGGGGGGK.',
    'KGBBKKKKGGGGGGKKKGGGGK.',
    '.KGBGWWKKGGGGKWWBGGGK..',
    '.KGBGWKKGGGGGGKWGGGGK..',
    '..KBGGGGGGBGGGGGGGGK...',
    '..KBGGGGGKGBGGGGGGGK...',
    '..KBGGGGGBBBGGGGBGGK...',
    '..KKBBBGGGGGGGBBGGKK...',
    '...KBGWWKKKKKWWGGGK....',
    '...KBBWWBBBBBWWGGGK....',
    '....KBBBBBBBBBBGGK.....',
    '.....KBGGGGGGGGGK......',
    '......KKKKKKKKKK.......',
]


def front_head(p, cls, dy):
    # Hood is a small garment framing an Orc face, not a featureless oval.
    if cls == 'warlock':
        p.polygon([(16, 8+dy), (20, 3+dy), (30, 2+dy), (37, 6+dy), (41, 13+dy),
                   (40, 25+dy), (34, 29+dy), (18, 27+dy), (14, 18+dy)], 3)
        p.polygon([(18, 9+dy), (22, 5+dy), (30, 4+dy), (35, 7+dy), (38, 14+dy),
                   (37, 23+dy), (33, 26+dy), (19, 24+dy), (17, 17+dy)], 2)
        p.line((23, 5+dy, 29, 5+dy), 0)
        p.line((35, 12+dy, 36, 17+dy), 3)
    # Asymmetrical tapered ears read as Orc ears at native size.
    p.polygon([(17, 11+dy), (10, 8+dy), (12, 16+dy), (18, 19+dy)], 3)
    p.polygon([(16, 12+dy), (12, 10+dy), (14, 15+dy), (18, 17+dy)], 1)
    p.line((14, 13+dy, 16, 16+dy), 2)
    p.polygon([(37, 12+dy), (45, 9+dy), (42, 17+dy), (36, 19+dy)], 3)
    p.polygon([(38, 13+dy), (43, 11+dy), (40, 16+dy), (36, 17+dy)], 1)
    p.line((41, 13+dy, 39, 16+dy), 2)
    p.stamp(FRONT_FACE, 16, 8+dy)
    # Angular brow and jaw shadows. Sparse edge clusters model green skin
    # with the existing three visible pigments instead of a flat green oval.
    p.line((20, 14+dy, 24, 15+dy), 3)
    p.line((32, 15+dy, 35, 14+dy), 3)
    p.line((20, 11+dy, 20, 14+dy), 2)
    p.point((21, 12+dy), 2); p.point((22, 14+dy), 2)
    p.line((22, 20+dy, 24, 21+dy), 2)
    p.point((24, 20+dy), 2); p.point((23, 19+dy), 2)
    p.line((32, 21+dy, 35, 20+dy), 2)
    p.point((34, 19+dy), 2)
    p.line((29, 11+dy, 31, 11+dy), 0)
    p.point((32, 12+dy), 0)
    if cls != 'warlock':
        p.polygon([(21, 7+dy), (23, 4+dy), (27, 3+dy), (32, 4+dy),
                   (34, 8+dy), (29, 9+dy), (26, 8+dy)], 3)
        p.polygon([(23, 6+dy), (27, 5+dy), (30, 5+dy), (32, 7+dy), (28, 7+dy)], 2)
        p.line((24, 5+dy, 26, 4+dy), 0)


def hand(p, x, y):
    p.polygon([(x-2, y-3), (x+1, y-3), (x+3, y-1), (x+3, y+2),
               (x+1, y+3), (x-2, y+2), (x-3, y)], 3)
    p.polygon([(x-1, y-2), (x+1, y-2), (x+2, y), (x+1, y+2), (x-1, y+1)], 1)
    p.point((x+1, y-1), 0)


def axe(p, origin, tip):
    hx, hy = origin; tx, ty = tip
    p.line((hx+2, hy+6, tx, ty), 3, 3)
    p.line((hx+2, hy+5, tx, ty), 2)
    p.polygon([(tx-1, ty-5), (tx+6, ty-6), (tx+8, ty-3), (tx+7, ty+3),
               (tx+4, ty+5), (tx-1, ty+3)], 3)
    p.polygon([(tx, ty-4), (tx+5, ty-5), (tx+6, ty-2), (tx+5, ty+2),
               (tx+3, ty+3), (tx, ty+2)], 2)
    p.line((tx+5, ty-4, tx+6, ty-2), 0)
    p.line((tx+6, ty-1, tx+5, ty+2), 0)
    p.point((tx+2, ty-2), 3)
    p.line((tx+2, ty-1, tx+1, ty+2), 3)
    p.point((tx+4, ty-3), 0)
    hand(p, hx, hy)


def mace(p, origin, tip):
    hx, hy = origin; tx, ty = tip
    p.line((hx+2, hy+6, tx, ty), 3, 3)
    p.line((hx+2, hy+5, tx, ty), 2)
    p.polygon([(tx-3, ty-4), (tx+2, ty-5), (tx+5, ty-2), (tx+4, ty+3),
               (tx, ty+5), (tx-4, ty+2)], 3)
    p.polygon([(tx-2, ty-3), (tx+1, ty-4), (tx+3, ty-1), (tx+2, ty+2),
               (tx, ty+3), (tx-2, ty+1)], 2)
    p.line((tx-1, ty-3, tx-1, ty+2), 0)
    p.line((tx+2, ty-1, tx+2, ty+1), 1)
    hand(p, hx, hy)


def wand(p, origin, tip):
    hx, hy = origin; tx, ty = tip
    p.line((hx, hy, tx, ty), 3, 3)
    p.line((hx, hy, tx, ty), 2)
    p.polygon([(tx, ty-2), (tx+2, ty), (tx, ty+2), (tx-2, ty)], 3)
    p.point((tx, ty), 0)
    hand(p, hx, hy)


def shield(p, x, y, small=False):
    width = 10 if small else 12; height = 13 if small else 16
    p.polygon([(x+3, y), (x+width-3, y), (x+width, y+3),
               (x+width-1, y+height-3), (x+width//2, y+height),
               (x+1, y+height-3), (x, y+3)], 3)
    p.polygon([(x+3, y+2), (x+width-3, y+2), (x+width-2, y+4),
               (x+width-3, y+height-4), (x+width//2, y+height-2),
               (x+3, y+height-4), (x+2, y+4)], 2)
    p.line((x+4, y+3, x+4, y+height-4), 3)
    p.line((x+width-4, y+3, x+width-4, y+height-4), 3)
    p.rectangle((x+width//2-1, y+height//2-1, x+width//2+1, y+height//2+1), 3)
    p.point((x+width//2, y+height//2), 0)
    p.line((x+2, y+4, x+3, y+2), 0)


def front_frame(cls, phase):
    p = Paint((56, 56)); dy = -1 if phase == 1 else 0
    # Lower legs and boots are separated by a dark gap, no green slippers.
    for x, shift in ((21, -1 if phase == 2 else 0), (32, 1 if phase == 2 else 0)):
        p.polygon([(x, 41), (x+7, 41), (x+6+shift, 49),
                   (x+4+shift, 53), (x-4+shift, 53), (x-3+shift, 50)], 3)
        p.rectangle((x+1, 43, x+5, 48), 2)
        p.line((x+1, 46, x+5, 46), 3)
        p.point((x+2, 45), 0)
        p.polygon([(x+shift, 49), (x+5+shift, 49), (x+4+shift, 52),
                   (x-2+shift, 52)], 2)
        p.point((x-1+shift, 51), 0)
    # Rounded trapezoid shoulders rather than squares or heroic armor.
    p.polygon([(18, 27+dy), (23, 24+dy), (34, 24+dy), (40, 29+dy),
               (37, 39), (39, 44), (20, 44), (19, 39)], 3)
    p.polygon([(21, 28+dy), (24, 26+dy), (33, 26+dy), (37, 30+dy),
               (34, 38), (36, 42), (22, 42), (22, 38)], 2)
    p.line((24, 27+dy, 30, 32+dy), 3)
    p.line((24, 28+dy, 28, 31+dy), 3)
    p.point((25, 28+dy), 0)
    p.line((34, 29+dy, 33, 37), 3)
    p.point((24, 35), 0); p.line((26, 36, 29, 36), 3)
    p.line((23, 31+dy, 22, 35), 3)
    p.line((31, 29+dy, 32, 33+dy), 3)
    p.point((31, 30+dy), 0); p.point((33, 35), 3)
    if cls == 'warlock':
        p.polygon([(22, 37), (36, 37), (39, 49), (35, 50), (30, 49),
                   (26, 50), (20, 49)], 3)
        p.polygon([(24, 39), (34, 39), (36, 47), (31, 47), (29, 48), (22, 47)], 2)
        p.line((27, 41, 25, 46), 3); p.line((32, 41, 34, 46), 3)
        p.point((24, 46), 0)
    else:
        p.rectangle((22, 41, 27, 46), 2); p.rectangle((31, 41, 36, 46), 2)
        p.line((28, 42, 30, 45), 3)
    p.rectangle((21, 38, 37, 40), 3)
    p.line((22, 39, 36, 39), 2)
    p.rectangle((28, 38, 30, 40), 0); p.point((29, 39), 3)
    # Arms angled away from torso retain negative space around equipment.
    p.polygon([(18, 27+dy), (14, 28+dy), (10, 35+dy), (12, 39+dy),
               (16, 39+dy), (21, 31+dy)], 3)
    p.polygon([(17, 29+dy), (15, 30+dy), (12, 35+dy), (14, 37+dy),
               (16, 35+dy), (19, 31+dy)], 1)
    p.line((15, 31+dy, 13, 34+dy), 0)
    p.polygon([(39, 28+dy), (43, 29+dy), (47, 34+dy), (46, 39+dy),
               (42, 40+dy), (37, 32+dy)], 3)
    p.polygon([(40, 30+dy), (42, 31+dy), (45, 35+dy), (44, 37+dy),
               (42, 36+dy), (39, 32+dy)], 1)
    p.line((42, 31+dy, 44, 34+dy), 0)
    front_head(p, cls, dy)
    if cls == 'warlock':
        origins = [(13, 37), (13, 32), (44, 34)]
        tips = [(7, 22), (8, 12), (51, 20)]
        wand(p, origins[phase], tips[phase])
        if phase == 2:
            p.line((40, 32, 43, 34), 1, 3)
            p.line((41, 31, 44, 33), 0)
    else:
        origins = [(13, 37), (14, 32), (15, 37)]
        tips = [(6, 26), (6, 11), (8, 40)]
        if cls == 'warrior':
            # The starting Warrior kit is a two-handed axe, no shield. Its
            # second forearm crosses to the lower grip without giant armor.
            hx, hy = origins[phase]
            second = (hx+3, hy+4)
            p.line((40, 30+dy, 34, 36+dy, second[0], second[1]), 3, 6)
            p.line((40, 31+dy, 34, 36+dy, second[0], second[1]), 1, 3)
            p.line((37, 34+dy, 31, 37+dy), 0)
        (axe if cls == 'warrior' else mace)(p, origins[phase], tips[phase])
        if cls == 'warrior': hand(p, *second)
        else: shield(p, 40, 31+dy)
        if cls == 'shaman':
            p.rectangle((34, 40, 38, 46), 3); p.rectangle((35, 41, 37, 45), 2)
            p.point((36, 42), 1); p.line((35, 44, 37, 44), 0)
    return p.pixels, p.mask


def back_head(p, cls, dy):
    if cls == 'warlock':
        p.polygon([(19, 9+dy), (23, 4+dy), (32, 2+dy), (38, 5+dy),
                   (43, 10+dy), (42, 22+dy), (36, 26+dy), (23, 26+dy), (18, 20+dy)], 3)
        p.polygon([(21, 10+dy), (25, 6+dy), (32, 4+dy), (37, 7+dy),
                   (40, 11+dy), (39, 21+dy), (35, 23+dy), (24, 24+dy), (21, 19+dy)], 2)
        p.line((29, 6+dy, 26, 13+dy), 3)
        p.line((26, 14+dy, 29, 21+dy), 3)
        p.line((32, 5+dy, 36, 7+dy), 3)
        p.point((34, 6+dy), 0)
        p.line((37, 9+dy, 38, 13+dy), 3)
        p.point((37, 10+dy), 0)
        p.polygon([(23, 12+dy), (25, 10+dy), (24, 16+dy), (27, 22+dy), (23, 20+dy)], 3)
        p.point((25, 18+dy), 2); p.point((26, 20+dy), 2)
        p.polygon([(39, 12+dy), (44, 11+dy), (46, 15+dy),
                   (44, 20+dy), (39, 22+dy), (37, 18+dy)], 3)
        p.polygon([(40, 13+dy), (44, 13+dy), (44, 17+dy), (42, 19+dy), (39, 20+dy)], 1)
        p.point((44, 16+dy), 3); p.point((44, 18+dy), 0)
    else:
        p.polygon([(20, 8+dy), (25, 4+dy), (34, 3+dy), (40, 6+dy),
                   (44, 12+dy), (44, 19+dy), (39, 24+dy), (26, 26+dy), (20, 21+dy), (18, 14+dy)], 3)
        p.polygon([(22, 9+dy), (26, 6+dy), (34, 5+dy), (39, 8+dy),
                   (42, 13+dy), (42, 18+dy), (38, 22+dy), (27, 23+dy), (22, 20+dy), (20, 14+dy)], 1)
        p.line((22, 15+dy, 24, 19+dy), 2)
        p.line((26, 22+dy, 29, 23+dy), 2)
        p.line((23, 10+dy, 21, 14+dy), 2, 2)
        p.line((25, 7+dy, 24, 9+dy), 2)
        p.line((30, 22+dy, 35, 22+dy), 2)
        p.polygon([(21, 14+dy), (24, 17+dy), (26, 21+dy), (29, 23+dy),
                   (25, 23+dy), (21, 20+dy)], 2)
        p.point((24, 19+dy), 1); p.point((25, 21+dy), 1)
        p.point((26, 20+dy), 2); p.point((28, 22+dy), 1)
        p.line((35, 8+dy, 37, 9+dy), 0)
        p.line((40, 12+dy, 43, 13+dy), 3)
        p.point((42, 14+dy), 0); p.point((43, 14+dy), 3)
        p.polygon([(43, 15+dy), (46, 16+dy), (46, 18+dy), (43, 19+dy)], 3)
        p.line((44, 16+dy, 45, 17+dy), 1)
        p.point((44, 19+dy), 0)
        p.polygon([(26, 5+dy), (28, 1+dy), (33, 1+dy), (35, 5+dy), (32, 9+dy), (29, 8+dy)], 3)
        p.rectangle((29, 2+dy, 32, 5+dy), 2); p.point((30, 2+dy), 0)
        p.line((38, 20+dy, 41, 20+dy), 2)
    p.polygon([(21, 11+dy), (14, 8+dy), (16, 17+dy), (22, 19+dy)], 3)
    p.polygon([(20, 12+dy), (16, 10+dy), (18, 16+dy), (21, 17+dy)], 1)
    p.line((17, 12+dy, 19, 16+dy), 2)


def back_frame(cls, phase):
    p = Paint((48, 48)); dy = -1 if phase == 1 else 0
    # Waist is deliberately higher than the old full frontal rear pose.
    p.polygon([(20, 26+dy), (27, 22+dy), (35, 23+dy), (42, 29+dy),
               (39, 37), (41, 44), (22, 44), (21, 36)], 3)
    p.polygon([(23, 27+dy), (28, 25+dy), (34, 25+dy), (39, 30+dy),
               (36, 36), (38, 41), (24, 41), (24, 35)], 2)
    p.line((25, 27+dy, 35, 34), 3, 2)
    p.line((26, 27+dy, 34, 33), 3)
    p.point((27, 27+dy), 0); p.point((31, 30+dy), 2)
    p.line((25, 35, 28, 37), 3); p.point((27, 36), 0)
    p.line((36, 30+dy, 35, 34), 3)
    p.line((29, 34, 31, 36), 3)
    p.rectangle((22, 38, 39, 40), 3); p.line((23, 39, 38, 39), 2)
    if cls == 'warlock':
        p.polygon([(23, 40), (39, 40), (42, 46), (36, 47), (31, 46), (26, 47), (21, 46)], 3)
        p.polygon([(25, 41), (37, 41), (39, 45), (33, 45), (30, 44), (25, 45)], 2)
        p.line((28, 41, 26, 45), 3); p.line((35, 41, 37, 45), 3)
    else:
        p.rectangle((23, 40, 29, 45), 2); p.rectangle((34, 40, 40, 45), 2)
        p.rectangle((30, 41, 33, 47), 0)
        # Erase the center gap from transparency, not an opaque ivory column.
        ImageDraw.Draw(p.mask).rectangle((30, 41, 33, 47), fill=0)
        p.line((22, 46, 29, 46), 3, 2); p.line((34, 46, 43, 46), 3, 2)
        p.line((23, 44, 27, 44), 0); p.line((36, 44, 39, 44), 0)
    # Left wrist carries the weapon. Right arm casts toward the upper-right.
    if cls == 'warlock' and phase == 2:
        # Raise the casting forearm to the established safe spell launch above
        # the HP HUD. Head, feet and body anchors do not jump with the hand.
        p.polygon([(20, 26), (14, 25), (12, 20), (15, 16), (19, 18), (23, 24)], 3)
        p.polygon([(19, 24), (16, 23), (15, 20), (17, 18), (19, 20), (21, 24)], 1)
        p.line((15, 20, 16, 22), 0)
    else:
        p.polygon([(20, 26+dy), (15, 27+dy), (11, 34+dy), (15, 38+dy),
                   (20, 35+dy), (23, 29+dy)], 3)
        p.polygon([(19, 28+dy), (16, 29+dy), (14, 34+dy), (16, 35+dy),
                   (19, 32+dy), (21, 29+dy)], 1)
        p.line((16, 30+dy, 15, 32+dy), 0)
    p.polygon([(40, 28+dy), (44, 29+dy), (47, 34+dy), (45, 39+dy),
               (41, 38+dy), (37, 31+dy)], 3)
    p.polygon([(41, 30+dy), (43, 31+dy), (45, 34+dy), (44, 36+dy), (42, 35+dy)], 1)
    back_head(p, cls, dy)
    if cls == 'warlock':
        origins = [(15, 34), (15, 28), (18, 20)]
        tips = [(6, 15), (7, 5), (16, 4)]
        wand(p, origins[phase], tips[phase])
    else:
        origins = [(15, 34), (15, 29), (15, 34)]
        tips = [(5, 22), (5, 7), (5, 36)]
        if cls == 'warrior':
            hx, hy = origins[phase]; second = (hx+3, hy+4)
            p.line((42, 31+dy, 35, 36+dy, second[0], second[1]), 3, 6)
            p.line((41, 32+dy, 35, 36+dy, second[0], second[1]), 1, 3)
            p.line((38, 34+dy, 32, 37+dy), 0)
        (axe if cls == 'warrior' else mace)(p, origins[phase], tips[phase])
        if cls == 'warrior': hand(p, *second)
        else: shield(p, 35, 30+dy)
        if cls == 'shaman':
            p.rectangle((23, 36, 27, 43), 3); p.rectangle((24, 37, 26, 42), 2)
            p.point((25, 38), 1); p.line((24, 40, 26, 40), 0)
    return p.pixels, p.mask


def encode(image, column_major=False):
    out = bytearray()
    coords = ([(x, y) for x in range(image.width//8) for y in range(image.height//8)]
              if column_major else [(x, y) for y in range(image.height//8) for x in range(image.width//8)])
    for tx, ty in coords:
        for y in range(8):
            row = [image.getpixel((tx*8+x, ty*8+y)) for x in range(8)]
            out.extend((sum((v&1)<<(7-x) for x, v in enumerate(row)),
                        sum((v>>1)<<(7-x) for x, v in enumerate(row))))
    return bytes(out)


def rgba(image, mask, palette):
    array = np.asarray(image, dtype='uint8'); color = np.asarray(palette, dtype='uint8')*8
    return Image.fromarray(np.dstack((color[array], np.asarray(mask, dtype='uint8'))), 'RGBA')


def emit(cls, kind, frames):
    native, public = NATIVE/cls, OUT/cls
    native.mkdir(parents=True, exist_ok=True); public.mkdir(parents=True, exist_ok=True)
    palette = WORLD_PALETTE if kind == 'world' else BATTLE_PALETTE
    size = 16 if kind == 'world' else 56 if kind == 'front' else 48
    strip = Image.new('P', (size, size*len(frames))); strip.putpalette(DMG)
    exports, metrics = [], []
    for i, (image, mask) in enumerate(frames):
        assert image.size == (size, size) and set(np.unique(np.asarray(image))) <= {0, 1, 2, 3}
        strip.paste(image, (0, i*size)); export = rgba(image, mask, palette); exports.append(export)
        assert set(np.unique(np.asarray(export.getchannel('A')))) <= {0, 255}
        label = f'{DIRECTIONS[i%4]}_step_{i//4}' if kind == 'world' else POSES[i]
        export.save(public/f'{cls}_{kind}_{label}_{size}x{size}.png')
        export.resize((size*8, size*8), Image.Resampling.NEAREST).save(public/f'{cls}_{kind}_{label}_8x.png')
        metrics.append({'frame': i, 'label': label, 'opaque_pixels': int(np.count_nonzero(np.asarray(mask))),
                        'opaque_bounds': export.getbbox(), 'native_index_sha256': hashlib.sha256(image.tobytes()).hexdigest()})
    strip.save(native/f'{kind}_frames.png')
    name = 'overworld.bin' if kind == 'world' else f'{kind}_frames.bin'
    data = b''.join(encode(image, column_major=kind != 'world') for image, _ in frames)
    (native/name).write_bytes(data)
    if kind == 'front':
        (native/'portrait_frames.bin').write_bytes(b''.join(encode(image) for image, _ in frames))
    sheet = Image.new('RGBA', (size*3, size*(4 if kind == 'world' else 1)))
    for i, export in enumerate(exports):
        x, y = (i//4, i%4) if kind == 'world' else (i, 0)
        sheet.alpha_composite(export, (x*size, y*size))
    sheet.save(public/f'{cls}_{kind}_sheet.png')
    sheet.resize((sheet.width*8, sheet.height*8), Image.Resampling.NEAREST).save(public/f'{cls}_{kind}_sheet_8x.png')
    motions = [(label, [exports[d+phase*4] for phase in (0, 1, 0, 2)], [140]*4)
               for d, label in enumerate(DIRECTIONS)] if kind == 'world' else [
                   ('', [exports[i] for i in (0, 1, 2, 1, 0)], [300, 150, 150, 150, 300])]
    for direction, sequence, timing in motions:
        name = f'{cls}_{kind}_{direction}_walk' if kind == 'world' else f'{cls}_{kind}_motion'
        sequence[0].save(public/f'{name}.apng', save_all=True, append_images=sequence[1:],
                         duration=timing, loop=0, disposal=1, blend=0)
        canvases = []
        for frame in sequence:
            large = frame.resize((size*8, size*8), Image.Resampling.NEAREST)
            canvas = Image.new('RGB', large.size, (243, 234, 207)); canvas.paste(large, mask=large.getchannel('A')); canvases.append(canvas)
        canvases[0].save(public/f'{name}_8x.gif', save_all=True, append_images=canvases[1:], duration=timing, loop=0)
    return {'size': [size, size], 'frames': metrics, 'binary_bytes': len(data),
            'binary': str((native/name).relative_to(ROOT)), 'sha256': hashlib.sha256(data).hexdigest(),
            'tile_order': 'row-major per frame' if kind == 'world' else 'column-major per frame',
            'binary_alpha': True, 'game_palette_rgb555': palette}


def emit_weapon_icons():
    """Four row-major BG tiles, explicit paper/highlight/wood/dark pigments."""
    native, public = NATIVE/'item_icons', OUT/'item_icons'
    native.mkdir(parents=True, exist_ok=True); public.mkdir(parents=True, exist_ok=True)
    palette = [(31, 29, 23), (23, 16, 9), (13, 8, 4), (0, 0, 0)]
    frames = {}
    p = Paint((16, 16))
    p.line((3, 14, 12, 4), 3, 3); p.line((4, 13, 12, 4), 2)
    p.line((4, 12, 8, 8), 1)
    p.polygon([(12, 1), (15, 4), (12, 7), (9, 4)], 3)
    p.polygon([(12, 2), (14, 4), (12, 6), (10, 4)], 1)
    p.line((12, 3, 13, 4), 0); p.point((11, 5), 2)
    p.line((4, 13, 5, 14), 1)
    frames['wand'] = (p.pixels, p.mask)
    p = Paint((16, 16))
    p.line((3, 14, 10, 4), 3, 3); p.line((4, 13, 10, 4), 2)
    p.line((4, 12, 6, 9), 1)
    p.polygon([(8, 2), (13, 1), (15, 3), (14, 7), (11, 9), (8, 7)], 3)
    p.polygon([(9, 3), (12, 2), (13, 3), (13, 6), (11, 7), (9, 6)], 1)
    p.line((13, 3, 13, 5), 0); p.point((12, 6), 0)
    p.line((10, 3, 10, 6), 2); p.point((11, 4), 3)
    p.point((4, 13), 1)
    frames['axe'] = (p.pixels, p.mask)
    report = {}
    sheet = Image.new('RGBA', (32, 16))
    for n, (name, (pixels, mask)) in enumerate(frames.items()):
        data = encode(pixels); assert len(data) == 64
        (native/f'{name}.2bpp').write_bytes(data)
        indexed = pixels.convert('P'); indexed.putpalette(DMG); indexed.save(native/f'{name}.png')
        (native/f'{name}.pal').write_text('\tRGB '+', '.join(str(value) for color in palette for value in color)+'\n')
        export = rgba(pixels, mask, palette)
        export.save(public/f'{name}_16x16.png')
        export.resize((128, 128), Image.Resampling.NEAREST).save(public/f'{name}_8x.png')
        sheet.alpha_composite(export, (n*16, 0))
        report[name] = {'binary': str((native/f'{name}.2bpp').relative_to(ROOT)),
                        'bytes': 64, 'tile_order': 'row-major', 'palette_rgb555': palette,
                        'sha256': hashlib.sha256(data).hexdigest(), 'transparent_png': str((public/f'{name}_16x16.png').relative_to(ROOT))}
    sheet.save(public/'wand_and_axe_sheet.png')
    sheet.resize((256, 128), Image.Resampling.NEAREST).save(public/'wand_and_axe_sheet_8x.png')
    return report


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'style': 'Original humble green Orc apprentices, explicit native-grid pixel clusters.',
              'classes': {}, 'dimensions_unchanged': True, 'saved_ids_and_layout_unchanged': True,
              'world_opaque_colors': 3, 'combat_palette_indices': 4,
              'warlock_rear_wand_tips_local': {'idle': [6, 15], 'ready': [7, 5], 'release': [16, 4]},
              'source_preview_only': True,
              'online_reference_sources': [
                  {'url': 'https://wow.zamimg.com/images/wow/icons/large/spell_shadow_shadowbolt.jpg', 'purpose': 'Warlock silhouette/color mood reference only; no image copied into native sprites.'},
                  {'url': 'https://wow.zamimg.com/images/wow/icons/large/inv_staff_02.jpg', 'purpose': 'Simple novice wooden caster implement reference only.'}]}
    report['weapon_icons'] = emit_weapon_icons()
    for cls in CLASSES:
        frames = {'world': world_frames(cls), 'front': [front_frame(cls, i) for i in range(3)],
                  'back': [back_frame(cls, i) for i in range(3)]}
        report['classes'][cls] = {kind: emit(cls, kind, values) for kind, values in frames.items()}
        assert (NATIVE/cls/'overworld.bin').stat().st_size == 768
        assert (NATIVE/cls/'front_frames.bin').stat().st_size == 2352
        assert (NATIVE/cls/'portrait_frames.bin').stat().st_size == 2352
        assert (NATIVE/cls/'back_frames.bin').stat().st_size == 1728
    sheet = Image.new('RGBA', (56*3, 56+48+16*4))
    for i, cls in enumerate(CLASSES):
        for kind, y in [('front', 0), ('back', 56), ('world', 104)]:
            src = Image.open(OUT/cls/f'{cls}_{kind}_sheet.png')
            if kind != 'world': src = src.crop((0, 0, 56 if kind == 'front' else 48, 56 if kind == 'front' else 48))
            sheet.alpha_composite(src, (i*56, y))
    sheet.save(OUT/'three_orc_apprentices_native.png')
    large = sheet.resize((sheet.width*6, sheet.height*6), Image.Resampling.NEAREST)
    large.save(OUT/'three_orc_apprentices_6x.png')
    review = Image.new('RGBA', large.size, (243, 234, 207)); review.alpha_composite(large)
    review.save(OUT/'three_orc_apprentices_paper_review.png')
    (OUT/'asset_manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'classes': CLASSES, 'native_dimensions': ['16x16 world', '56x56 front', '48x48 back'],
                      'transparent_native_pngs': 54, 'animation_previews': 18, 'saved_layout_unchanged': True}, indent=2))


if __name__ == '__main__': main()
