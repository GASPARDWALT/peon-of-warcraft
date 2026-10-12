#!/usr/bin/env python3
"""Redraw all 47 native environment blocks from modular original pixel art.

No old tiles, old image galleries or map layouts are used as drawing sources.
The current map block IDs/collisions remain stable. Exact 8x8 pixel+palette
deduplication keeps the new art within Crystal's two 96-tile background banks.
Two unique fire tiles are deliberately allocated first for native animation.
"""
from collections import Counter
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import hashlib
import json
import subprocess

from PIL import Image, ImageDraw

from build_peon_environment_palettes import BG, palettes_for
import peon_environment_plants_v025 as plants

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'references/generated/environment_v025'
BASE='6d2a0be'
NAMES=('bare_soil layered_escarpment main_road cactus hide_hut hold_red_carpet '
       'horde_standard sandstone_floor sandy_clearance den_0 den_1 den_2 den_3 '
       'dry_scrub sea cavern_mouth zone_transition road_ns road_ew road_ne road_nw '
       'road_se road_sw road_nse road_nsw road_new road_sew east_shore coastal_palm '
       'troll_thatched_hut spiked_palisade watchtower timber_boardwalk fortified_gate_wall '
       'fire_brazier wayfinding_sign burning_blade_skull desert_boulder walkable_bare_soil '
       'campfire inn_bedroll inn_table deadthorn_tree darkspear_bedroll darkspear_table '
       'woven_timber_floor darkspear_spirit_mask').split()
DIMS={'PeonOpening':(8,6),'GrommashHold':(8,6),'TheDen':(12,10),'ValleyOfTrials':(16,12),
      'DurotarRoad':(12,14),'SenjinVillage':(12,10),'RazorHill':(12,10),'OrgrimmarGate':(12,10),
      'BurningBladeCavern':(10,10),'PeonTrollHut':(6,5),'PeonOrcHut':(6,5),
      'PeonOrcInn':(6,5),'PeonTrollInn':(6,5)}


@dataclass
class Tile:
    pixels: Image.Image
    palette: int
    mask: Image.Image
    name: str

    @property
    def key(self): return (self.pixels.tobytes(),self.palette)


class Canvas:
    def __init__(self,size=(32,32)):
        self.indices=Image.new('L',size,0)
        self.palettes=Image.new('L',(size[0]//8,size[1]//8),1)
        self.mask=Image.new('L',size,0)

    def put(self,tile,x,y):
        self.indices.paste(tile.pixels,(x*8,y*8));self.mask.paste(tile.mask,(x*8,y*8))
        self.palettes.putpixel((x,y),tile.palette)

    def crop(self,box):
        im=Canvas((box[2]-box[0],box[3]-box[1]))
        im.indices=self.indices.crop(box);im.mask=self.mask.crop(box)
        im.palettes=self.palettes.crop(tuple(v//8 for v in box));return im

    def tiles(self):
        for y in range(self.indices.height//8):
            for x in range(self.indices.width//8):
                box=(x*8,y*8,x*8+8,y*8+8)
                yield Tile(self.indices.crop(box),self.palettes.getpixel((x,y)),
                           self.mask.crop(box),f'{x},{y}')


def tile(name,palette,draw=None,fill=0,opaque=False):
    im=Image.new('L',(8,8),fill)
    if draw: draw(ImageDraw.Draw(im))
    mask=Image.new('L',(8,8),255) if opaque else im.point(lambda p:255 if p else 0)
    return Tile(im,palette,mask,name)


def reflected(source,name):
    return Tile(source.pixels.transpose(Image.Transpose.FLIP_LEFT_RIGHT),source.palette,
                source.mask.transpose(Image.Transpose.FLIP_LEFT_RIGHT),name)


def array(grid,library):
    canvas=Canvas((len(grid[0])*8,len(grid)*8))
    for y,row in enumerate(grid):
        assert len(row)==len(grid[0])
        for x,name in enumerate(row):canvas.put(library[name],x,y)
    return canvas


def basic_tiles():
    t={}
    def add(name,pal,draw=None,fill=0,opaque=False):
        t[name]=tile(name,pal,draw,fill,opaque);return t[name]
    add('empty',1)
    add('soil',1,lambda d:(d.point((1,3),1),d.line((5,6,6,6),fill=1)),opaque=True)
    add('soil_quiet',1,lambda d:d.point((6,2),1),opaque=True)
    # Compact flat caps, long vertical faces and shallow sediment seams make
    # connected cliffs read as escarpments rather than a grid of round stones.
    add('rock_cap_l',0,lambda d:(d.polygon([(2,2),(7,0),(7,7),(0,7),(0,5)],fill=3),
                              d.polygon([(2,2),(7,1),(7,5),(1,6)],fill=1),
                              d.line((2,3,6,2),fill=2)))
    t['rock_cap_r']=reflected(t['rock_cap_l'],'rock_cap_r')
    add('rock_cap',0,lambda d:(d.rectangle((0,0,7,7),fill=2),d.rectangle((0,1,7,4),fill=1),
                            d.line((0,6,7,6),fill=3)),opaque=True)
    add('rock_face',0,lambda d:(d.line((1,0,1,7),fill=3),d.line((6,0,6,5),fill=1),
                             d.line((4,1,4,6),fill=3),d.point((2,3),1)),fill=2,opaque=True)
    add('rock_seam',0,lambda d:(d.line((0,1,7,1),fill=3),d.line((0,2,7,2),fill=1),
                             d.line((6,4,6,7),fill=3)),fill=2,opaque=True)
    add('rock_foot_l',0,lambda d:(d.polygon([(0,0),(7,0),(7,6),(3,7),(0,5)],fill=3),
                               d.polygon([(1,0),(7,0),(7,4),(2,5)],fill=2),
                               d.line((2,5,6,5),fill=1)))
    t['rock_foot_r']=reflected(t['rock_foot_l'],'rock_foot_r')
    # Broad hide courses and diagonal stitched roof seams; no borrowed pixels.
    add('roof',6,lambda d:(d.line((0,5,7,5),fill=2),d.point((2,2),2),d.point((6,1),3)),fill=1)
    add('roof_l',6,lambda d:(d.polygon([(7,0),(7,7),(0,7)],fill=3),
                           d.polygon([(7,2),(7,6),(2,6)],fill=1),d.line((4,5,7,3),fill=2)))
    t['roof_r']=reflected(t['roof_l'],'roof_r')
    add('roof_edge',6,lambda d:(d.rectangle((0,0,7,5),fill=1),d.line((0,5,7,5),fill=3),
                              d.line((0,6,7,6),fill=2)))
    # Roof material variants share pixels where possible. Thatched tiles use
    # ivory/brown; Orc hide stays unmistakably Horde red.
    add('thatch',5,lambda d:(d.line((1,0,1,7),fill=2),d.line((4,0,4,5),fill=3),
                           d.line((6,2,6,7),fill=2)),fill=1)
    add('thatch_l',5,lambda d:(d.polygon([(7,0),(7,7),(0,7)],fill=3),
                             d.polygon([(7,2),(7,6),(2,6)],fill=1),d.line((5,3,5,6),fill=2)))
    t['thatch_r']=reflected(t['thatch_l'],'thatch_r')
    add('thatch_edge',5,lambda d:(d.rectangle((0,0,7,5),fill=1),d.line((2,0,2,6),fill=2),
                                d.line((6,1,6,7),fill=3),d.line((0,7,7,7),fill=3)))
    add('timber',5,lambda d:(d.line((0,0,7,0),fill=3),d.point((1,1),1),
                            d.line((0,5,7,5),fill=3),d.line((3,2,3,4),fill=3)),fill=2)
    add('timber_floor',5,lambda d:(d.line((0,0,7,0),fill=3),d.line((0,6,7,6),fill=3),
                                 d.point((2,2),1),d.line((5,2,5,5),fill=3)),fill=2,opaque=True)
    add('stone_floor',5,lambda d:(d.line((0,0,7,0),fill=3),d.line((0,0,0,7),fill=3),
                                d.line((1,1,7,1),fill=1),d.point((6,6),3)),fill=2,opaque=True)
    add('base',5,lambda d:(d.rectangle((0,0,7,7),fill=2),d.line((0,0,7,0),fill=1),
                         d.line((0,6,7,6),fill=3)),opaque=True)
    # Continuous tusks have a pale interior, one warm shade and a strong edge.
    add('bone',5,lambda d:(d.rectangle((2,0,6,7),fill=3),d.rectangle((3,0,5,7),fill=1),
                         d.line((5,4,5,7),fill=2)))
    add('bone_tip_l',5,lambda d:(d.line([(5,7),(3,4),(4,1),(7,0)],fill=3,width=4),
                               d.line([(5,7),(4,4),(5,1),(7,0)],fill=1,width=2)))
    t['bone_tip_r']=reflected(t['bone_tip_l'],'bone_tip_r')
    add('bone_foot_l',5,lambda d:(d.rectangle((2,0,6,5),fill=3),d.rectangle((3,0,5,4),fill=1),
                                d.rectangle((0,6,7,7),fill=3),d.line((1,6,6,6),fill=2)))
    t['bone_foot_r']=reflected(t['bone_foot_l'],'bone_foot_r')
    add('door_dark',5,fill=3)
    add('door_arc_l',5,lambda d:(d.polygon([(0,7),(0,4),(3,1),(7,0),(7,7)],fill=1),
                               d.polygon([(2,7),(2,5),(4,3),(7,2),(7,7)],fill=3)))
    t['door_arc_r']=reflected(t['door_arc_l'],'door_arc_r')
    add('door_step',5,lambda d:(d.line((0,5,7,5),fill=1),d.line((0,6,7,6),fill=2)),fill=3)
    # Cave arch is rock, distinctly separate from timber doors. Dark center
    # touches the lower edge to lead naturally into the open transition below.
    add('cave_arc_l',0,lambda d:(d.polygon([(0,7),(2,3),(5,0),(7,0),(7,7)],fill=3),
                               d.line([(1,7),(3,3),(6,1),(7,1)],fill=1,width=2),
                               d.line((4,4,4,7),fill=2)))
    t['cave_arc_r']=reflected(t['cave_arc_l'],'cave_arc_r')
    add('cave_side_l',0,lambda d:(d.rectangle((0,0,7,7),fill=3),d.rectangle((1,0,3,7),fill=2),
                                d.line((1,0,1,5),fill=1)))
    t['cave_side_r']=reflected(t['cave_side_l'],'cave_side_r')
    add('cave_dark',0,fill=3)
    # Poles/palisades/legs/signs share a narrow carved timber silhouette.
    add('post',5,lambda d:(d.rectangle((2,0,5,7),fill=3),d.line((3,0,3,7),fill=2),d.point((3,1),1)))
    add('spike',5,lambda d:(d.polygon([(3,0),(6,5),(6,7),(1,7),(1,5)],fill=3),
                          d.polygon([(3,1),(4,5),(4,7),(2,7),(2,5)],fill=1)))
    add('crossbar',5,lambda d:(d.rectangle((0,2,7,5),fill=3),d.line((0,3,7,3),fill=2),
                             d.point((2,3),1)))
    add('ladder',5,lambda d:(d.line((1,0,1,7),fill=3),d.line((6,0,6,7),fill=3),
                           d.line((2,2,5,2),fill=1),d.line((2,6,5,6),fill=2)))
    add('sea',3,lambda d:(d.line((1,2,5,2),fill=1),d.line((0,6,3,6),fill=3),d.point((6,3),3)),fill=2,opaque=True)
    add('shore',3,lambda d:(d.rectangle((5,0,7,7),fill=2),d.line((4,0,4,7),fill=1),
                           d.point((3,2),1),d.point((5,5),1)),opaque=True)
    return t


def flame_tiles(phase=0):
    # Two top tiles only: these patterns never occur in a non-fire prop.
    im=Image.new('L',(16,8),0);d=ImageDraw.Draw(im)
    tips=[[(1,7),(2,4),(4,5),(5,1),(8,5),(10,2),(12,4),(14,7)],
          [(1,7),(3,3),(4,5),(7,0),(9,5),(11,3),(13,5),(14,7)],
          [(1,7),(2,5),(4,2),(6,5),(8,1),(10,5),(12,3),(14,7)]][phase]
    d.polygon(tips+[(14,7),(1,7)],fill=3)
    d.polygon([(3,7),(4,5),(6,6),(7,3),(9,6),(11,5),(12,7)],fill=2)
    d.polygon([(6,7),(7,5),(8,6),(9,5),(10,7)],fill=1)
    return [Tile(im.crop((x,0,x+8,8)),4,
                 im.crop((x,0,x+8,8)).point(lambda p:255 if p else 0),
                 'fire_l' if x==0 else 'fire_r') for x in (0,8)]


def special_tiles(t):
    def add(name,pal,draw=None,fill=0,opaque=False):
        t[name]=tile(name,pal,draw,fill,opaque);return t[name]
    # Horde emblem is a strong 16-pixel knot over red cloth. The same drawing
    # appears on standards and the hall's rugs, keeping visual vocabulary tight.
    emblem=Image.new('L',(16,16),1);d=ImageDraw.Draw(emblem)
    d.polygon([(8,1),(12,4),(14,8),(12,12),(8,15),(4,12),(2,8),(4,4)],fill=3)
    d.polygon([(8,4),(11,7),(10,10),(8,12),(6,10),(5,7)],fill=1)
    d.rectangle((7,6,8,14),fill=3)
    d.line([(3,2),(3,6),(5,7)],fill=3,width=2)
    d.line([(13,2),(13,6),(11,7)],fill=3,width=2)
    for i in range(4):
        pixels=emblem.crop((i%2*8,i//2*8,i%2*8+8,i//2*8+8))
        t[f'emblem_{i}']=Tile(pixels,6,Image.new('L',(8,8),255),f'emblem_{i}')
    add('cloth',6,fill=1)
    add('cloth_edge',6,lambda d:(d.line((0,0,0,7),fill=3),d.line((2,0,2,7),fill=2)),fill=1)
    add('cloth_foot_l',6,lambda d:(d.polygon([(0,0),(7,0),(7,7),(4,4),(0,6)],fill=1),
                                d.line((0,0,0,5),fill=3)))
    t['cloth_foot_r']=reflected(t['cloth_foot_l'],'cloth_foot_r')
    add('sign_l',5,lambda d:(d.rectangle((1,1,7,6),fill=3),d.rectangle((2,2,7,5),fill=2),
                            d.line((3,2,7,2),fill=1),d.line((5,4,7,4),fill=3)))
    add('sign_r',5,lambda d:(d.rectangle((0,1,6,6),fill=3),d.rectangle((0,2,5,5),fill=2),
                            d.polygon([(1,2),(4,4),(1,5)],fill=1)))
    # Stone/bone skulls mark a ritual prop, not a fake cave entrance.
    skull=Image.new('L',(16,16),0);d=ImageDraw.Draw(skull)
    d.polygon([(4,1),(11,1),(14,4),(14,9),(11,12),(11,15),(4,15),(4,12),(1,9),(1,4)],fill=3)
    d.polygon([(4,2),(11,2),(13,4),(13,9),(10,11),(10,14),(5,14),(5,11),(2,9),(2,4)],fill=1)
    d.rectangle((3,5,6,8),fill=3);d.rectangle((9,5,12,8),fill=3)
    d.polygon([(8,8),(6,11),(9,11)],fill=3)
    d.line((6,13,6,14),fill=2);d.line((9,13,9,14),fill=2)
    for i in range(4):
        pixels=skull.crop((i%2*8,i//2*8,i%2*8+8,i//2*8+8))
        t[f'skull_{i}']=Tile(pixels,5,pixels.point(lambda p:255 if p else 0),f'skull_{i}')
    add('ember_l',4,lambda d:(d.polygon([(0,0),(7,0),(7,5),(5,7),(1,5)],fill=3),
                            d.polygon([(1,0),(7,0),(7,4),(4,5),(2,3)],fill=2),
                            d.polygon([(5,0),(7,0),(7,3),(5,2)],fill=1)))
    t['ember_r']=reflected(t['ember_l'],'ember_r')
    add('log_l',5,lambda d:(d.line((0,0,7,6),fill=3,width=4),d.line((0,1,7,6),fill=2,width=2),
                          d.point((1,1),1)))
    t['log_r']=reflected(t['log_l'],'log_r')
    add('bowl_l',5,lambda d:(d.polygon([(0,0),(7,0),(7,6),(3,6)],fill=3),d.line((0,0,7,0),fill=1),
                           d.line((2,2,6,2),fill=2)))
    t['bowl_r']=reflected(t['bowl_l'],'bowl_r')
    add('pillow',5,lambda d:(d.rectangle((0,1,7,7),fill=3),d.rectangle((1,2,6,6),fill=1),
                           d.line((1,5,6,5),fill=2)))
    add('blanket_red',6,lambda d:(d.line((0,0,7,0),fill=3),d.line((1,1,6,1),fill=2),
                                d.point((3,4),2)),fill=1)
    add('blanket_green',2,lambda d:(d.line((0,0,7,0),fill=3),d.line((1,1,6,1),fill=1),
                                  d.line((2,3,2,6),fill=3),d.line((5,4,5,7),fill=1)),fill=2)
    add('table_l',5,lambda d:(d.rectangle((0,0,7,7),fill=3),d.rectangle((1,1,7,6),fill=2),
                            d.line((1,1,7,1),fill=1),d.line((2,5,7,5),fill=3)))
    t['table_r']=reflected(t['table_l'],'table_r')
    add('table_foot',5,lambda d:(d.rectangle((0,0,7,2),fill=3),d.line((2,3,2,7),fill=2),
                               d.line((5,3,5,7),fill=3)))
    for item in flame_tiles():t[item.name]=item


def plant_canvas(fn):
    im,pal,mask=fn();canvas=Canvas();canvas.indices=im;canvas.palettes=pal;canvas.mask=mask
    return canvas


def painted(size,palette=5):
    canvas=Canvas(size)
    canvas.palettes.paste(palette,(0,0,size[0]//8,size[1]//8))
    return canvas


def finish_paint(canvas):
    canvas.mask=canvas.indices.point(lambda n:255 if n else 0)
    return canvas


def sandstone_cliff():
    """Irregular sunlit ledge and broad diagonal sediment faces, not timbers."""
    canvas=painted((32,32),0);d=ImageDraw.Draw(canvas.indices)
    outline=[(0,5),(7,1),(19,0),(29,4),(31,8),(31,31),(0,31)]
    d.polygon(outline,fill=3)
    d.polygon([(1,5),(8,2),(19,1),(28,5),(30,8),(28,12),(20,15),
               (6,13),(1,10)],fill=1)
    d.polygon([(1,12),(8,15),(21,17),(29,14),(30,10),(30,28),
               (23,30),(2,30)],fill=2)
    d.line([(1,11),(8,14),(20,16),(27,13),(30,10)],fill=3)
    d.line([(1,23),(7,24),(13,23),(19,25),(25,23),(30,23)],fill=3)
    d.line([(2,24),(8,26),(14,25),(19,27)],fill=1)
    d.line([(9,3),(12,5),(10,8)],fill=2)
    d.line([(22,6),(24,8),(22,12)],fill=2)
    d.line([(7,17),(8,20),(6,23)],fill=3)
    d.line([(25,16),(23,19),(25,22)],fill=3)
    d.point((16,20),1);d.point((4,28),1)
    # Large sediment planes repeat between their jagged cap edges. This spends
    # tiles on the geology silhouette rather than invisible one-off vein noise.
    high=[canvas.indices.crop((8,8,16,16)),canvas.indices.crop((16,8,24,16))]
    low=[canvas.indices.crop((8,16,16,24)),canvas.indices.crop((16,16,24,24))]
    for y,sources in ((1,high),(2,low),(3,low)):
        for x in range(4):canvas.indices.paste(sources[x%2],(x*8,y*8))
    return finish_paint(canvas)


def sandstone_boulder():
    canvas=painted((32,32),0);d=ImageDraw.Draw(canvas.indices)
    d.polygon([(5,14),(10,6),(19,4),(27,11),(29,23),(23,28),
               (10,29),(3,23)],fill=3)
    d.polygon([(6,13),(11,8),(18,6),(24,12),(21,17),(6,17)],fill=1)
    d.polygon([(6,18),(20,18),(27,12),(27,22),(22,26),(10,27),
               (5,22)],fill=2)
    d.line([(17,8),(15,12),(18,17)],fill=3)
    d.line([(10,9),(14,7)],fill=2)
    d.line([(8,22),(12,24),(20,24)],fill=1)
    d.point((24,20),3);d.point((22,25),3)
    return finish_paint(canvas)


def horde_den():
    """64x64 rounded hide roof, curved tusks, offset real entrance quadrant."""
    canvas=painted((64,64),5);d=ImageDraw.Draw(canvas.indices)
    for y in range(4):
        for x in range(1,7):canvas.palettes.putpixel((x,y),6)
    d.polygon([(7,29),(13,16),(28,4),(38,8),(52,18),(56,29)],fill=3)
    d.polygon([(10,27),(16,17),(29,7),(37,11),(49,20),(53,27)],fill=1)
    d.line([(16,17),(29,7),(37,11),(49,20)],fill=2,width=2)
    # Stitching lies along actual hide seams, instead of repeated brick rows.
    d.line([(17,25),(20,21),(25,18),(28,13),(30,8)],fill=3)
    for x,y in ((18,24),(22,21),(25,19),(27,16),(29,13)):
        d.point((x+1,y),2)
    d.line([(34,10),(36,17),(41,24),(47,27)],fill=2)
    d.polygon([(7,28),(55,28),(56,57),(49,62),(8,60)],fill=3)
    d.polygon([(10,31),(52,31),(53,56),(48,59),(10,57)],fill=2)
    common=basic_tiles()
    for y in (4,5,6):
        for x in range(1,7):canvas.put(common['timber'],x,y)
    for x in (1,4,5,6):canvas.put(common['base'],x,7)
    # Window is high on the solid right-hand facade, away from an entrance.
    d.rectangle((42,39,49,44),fill=3);d.line((42,38,49,38),fill=1)
    # The actual door belongs to lower-left block11's bottom-right quadrant.
    d.polygon([(15,63),(15,50),(18,45),(23,43),(27,45),(32,49),(32,63)],fill=3)
    d.polygon([(17,63),(17,51),(20,47),(23,45),(26,47),(30,51),(30,63)],fill=1)
    d.polygon([(18,63),(18,52),(20,49),(24,47),(28,50),(29,63)],fill=3)
    d.line((16,60,31,60),fill=1);d.line((16,62,31,62),fill=2)
    # Tusks curve within their dedicated wood/ivory tile columns. Straps and
    # blunt stone feet anchor the hide ribs rather than forming straight rails.
    left=Image.new('L',(8,64),0);bd=ImageDraw.Draw(left)
    bd.line([(1,0),(2,9),(5,18),(6,30),(5,42),(5,59)],fill=3,width=5)
    bd.line([(1,0),(2,9),(4,18),(5,30),(4,42),(4,58)],fill=1,width=3)
    bd.line((3,19,7,19),fill=2);bd.line((2,21,7,21),fill=3)
    bd.ellipse((0,56,7,63),fill=3);bd.line((1,59,6,59),fill=2)
    shaft=left.crop((0,24,8,32))
    left.paste(shaft,(0,32));left.paste(shaft,(0,40))
    canvas.indices.paste(left,(0,0))
    canvas.indices.paste(left.transpose(Image.Transpose.FLIP_LEFT_RIGHT),(56,0))
    return finish_paint(canvas)


def horde_hut(troll=False):
    """Native32x32 rounded roofs; only the real BR foot quadrant is dark/open."""
    canvas=painted((32,32),5);d=ImageDraw.Draw(canvas.indices)
    if not troll:
        for y in (0,1):
            for x in (1,2):canvas.palettes.putpixel((x,y),6)
    d.polygon([(2,14),(7,7),(15,1),(23,6),(30,14)],fill=3)
    d.polygon([(5,13),(9,8),(15,4),(22,8),(27,13)],fill=1)
    if troll:
        for x in (9,13,17,21,25):
            d.line((x,8 if x in (9,25) else 5,x-2,13),fill=2)
        d.line((6,13,28,13),fill=3)
    else:
        d.line([(9,9),(15,4),(22,8)],fill=2)
        d.line((15,5,18,12),fill=3);d.point((17,10),2)
    d.polygon([(3,14),(30,14),(31,30),(5,31)],fill=3)
    d.rectangle((5,16,30,29),fill=2)
    d.line((6,22,16,22),fill=3);d.point((7,17),1)
    d.ellipse((15,16,34,36),fill=1);d.ellipse((18,18,35,37),fill=3)
    d.rectangle((18,24,31,31),fill=3)
    d.line((18,29,31,29),fill=1);d.line((18,30,31,30),fill=2)
    # Open at the right edge too: Razor's southwest hut approaches from east.
    d.line((31,22,31,31),fill=3)
    d.line([(2,1),(4,7),(5,16),(4,28)],fill=3,width=5)
    d.line([(2,1),(3,7),(4,16),(3,28)],fill=1,width=2)
    d.line((2,16,6,16),fill=2)
    d.ellipse((0,27,7,31),fill=3);d.line((1,29,6,29),fill=2)
    if troll:
        # Side weave is not a second door. Palette remains exact wood/ivory.
        d.line([(7,19),(9,17),(11,20),(13,18),(15,20)],fill=1)
    return finish_paint(canvas)


def road(openings,full=False,threshold=False):
    im=Canvas();d=ImageDraw.Draw(im.indices)
    if full:d.rectangle((0,0,31,31),fill=1)
    else:
        d.rectangle((4,4,27,27),fill=1)
        for edge,box in {'N':(4,0,27,4),'S':(4,27,27,31),'E':(27,4,31,27),'W':(0,4,4,27)}.items():
            if edge in openings:d.rectangle(box,fill=1)
    # Grain at the same tile-local positions is genuinely shareable, while the
    # middle remains consistently beaten earth on all named connection shapes.
    for y in range(4):
        for x in range(4):
            p=(x*8+3,y*8+5)
            if im.indices.getpixel(p)==1:d.point(p,2)
            im.palettes.putpixel((x,y),4)
    if threshold:
        for x in (1,9,17,25):d.line((x,15,x+4,15),fill=2)
    im.mask=im.indices.point(lambda n:255 if n else 0)
    return im


def build_blocks():
    t=basic_tiles();special_tiles(t)
    e='empty';s='soil';w='timber';b='bone'
    blocks=[None]*47
    def put(index,grid):blocks[index]=array(grid,t)
    put(0,[[s,s,s,s],[s,s,s,s],[s,s,s,s],[s,s,s,s]])
    blocks[1]=sandstone_cliff()
    blocks[2]=road('',full=True);blocks[3]=plant_canvas(plants.cactus)
    blocks[4]=horde_hut()
    put(5,[['cloth_edge','cloth','cloth','cloth_edge'],['cloth_edge','emblem_0','emblem_1','cloth_edge'],
           ['cloth_edge','emblem_2','emblem_3','cloth_edge'],['cloth_edge','cloth','cloth','cloth_edge']])
    put(6,[[e,'post','cloth','cloth'],[e,'post','emblem_0','emblem_1'],
           [e,'post','emblem_2','emblem_3'],[e,'post','cloth_foot_l','cloth_foot_r']])
    put(7,[['stone_floor']*4 for _ in range(4)])
    put(8,[['soil_quiet']*4 for _ in range(4)])
    den=horde_den()
    for i in range(4):
        x=i%2*32;y=i//2*32;blocks[9+i]=den.crop((x,y,x+32,y+32))
    blocks[13]=plant_canvas(plants.scrub)
    put(14,[['sea']*4 for _ in range(4)])
    put(15,[[e,'cave_arc_l','cave_arc_r',e],['cave_side_l','cave_dark','cave_dark','cave_side_r'],
            ['cave_side_l','cave_dark','cave_dark','cave_side_r'],
            ['cave_side_l','cave_dark','cave_dark','cave_side_r']])
    blocks[16]=road('',full=True,threshold=True)
    for i,openings in enumerate(('NS','EW','NE','NW','SE','SW','NSE','NSW','NEW','SEW'),17):
        blocks[i]=road(openings)
    put(27,[[s,'shore','sea','sea'] for _ in range(4)])
    blocks[28]=plant_canvas(plants.palm)
    blocks[29]=horde_hut(troll=True)
    put(30,[['spike']*4,['post']*4,['crossbar']*4,['post']*4])
    put(31,[['roof_l','roof','roof','roof_r'],['crossbar','door_dark','door_dark','crossbar'],
            ['post','ladder','ladder','post'],['post','crossbar','crossbar','post']])
    put(32,[['timber_floor']*4 for _ in range(4)])
    # Reuse the actual sandstone ledge faces between the ivory gate jambs.
    gate=Canvas()
    cliff_tiles=list(blocks[1].tiles())
    for y in range(4):
        for x in range(4):
            source=(t['bone_foot_l'] if x==0 and y==3 else
                    t['bone_foot_r'] if x==3 and y==3 else
                    t['bone'] if x in (0,3) else cliff_tiles[y*4+x])
            gate.put(source,x,y)
    blocks[33]=gate
    put(34,[[e,'fire_l','fire_r',e],[e,'ember_l','ember_r',e],
            [e,'bowl_l','bowl_r',e],[e,'post','post',e]])
    put(35,[[e,e,e,e],[e,'sign_l','sign_r',e],[e,'post','post',e],[e,'post','post',e]])
    put(36,[[e,e,e,e],[e,'skull_0','skull_1',e],[e,'skull_2','skull_3',e],[e,e,e,e]])
    blocks[37]=sandstone_boulder()
    blocks[38]=blocks[0]
    put(39,[[e,e,e,e],[e,'fire_l','fire_r',e],[e,'ember_l','ember_r',e],
            ['rock_cap_l','log_l','log_r','rock_cap_r']])
    put(40,[[e,'pillow','pillow',e],[e,'blanket_red','blanket_red',e],
            [e,'blanket_red','blanket_red',e],[e,'bone_foot_l','bone_foot_r',e]])
    put(41,[[e,e,e,e],[e,'table_l','table_r',e],[e,'table_l','table_r',e],
            [e,'table_foot','table_foot',e]])
    blocks[42]=plant_canvas(plants.deadthorn)
    put(43,[[e,'pillow','pillow',e],[e,'blanket_green','blanket_green',e],
            [e,'blanket_green','blanket_green',e],[e,'bone_foot_l','bone_foot_r',e]])
    put(44,[[e,e,e,e],[e,'table_l','table_r',e],
            [e,'blanket_green','blanket_green',e],[e,'table_foot','table_foot',e]])
    put(45,[['timber_floor']*4,['timber_floor','blanket_green','blanket_green','timber_floor'],
            ['timber_floor','blanket_green','blanket_green','timber_floor'],['timber_floor']*4])
    put(46,[['bone_tip_l','crossbar','crossbar','bone_tip_r'],
            ['post','skull_0','skull_1','post'],['post','skull_2','skull_3','post'],
            ['bone_foot_l',e,e,'bone_foot_r']])
    assert all(blocks)
    return blocks,den,t


def native_id(index):return index if index<96 else index+32


def compile_tiles(blocks):
    # Fire keys are never retired, recoloured, or reused by another prop.
    bank=flame_tiles();lookup={item.key:i for i,item in enumerate(bank)}
    meta=bytearray();per_block=[]
    for ident,block in enumerate(blocks):
        used=[]
        for item in block.tiles():
            key=item.key
            if not any(key[0]):key=(bytes(64),1)
            if key in lookup and lookup[key]<2:
                assert ident in (34,39),'An animated fire pattern leaked into non-fire scenery'
            if key not in lookup:
                lookup[key]=len(bank)
                bank.append(Tile(Image.frombytes('L',(8,8),key[0]),key[1],item.mask,item.name))
            idx=lookup[key];meta.append(native_id(idx));used.append(idx)
        per_block.append({'id':ident,'name':NAMES[ident],'allocated_patterns':len(set(used))})
    histogram=Counter(item.palette for item in bank)
    report={'patterns':len(bank),'budget':192,'palette_pattern_counts':dict(histogram),'blocks':per_block}
    return bank,meta,report


def reduce_shade_variants(blocks,library):
    """Consolidate only tiny colour variants, preserving every silhouette.

    Animated flames, all plant patterns, actual door/cave cells and the Horde
    glyph are immutable. Every merged pair has the same palette and the exact
    same zero/nonzero pixel footprint; this cannot erode an outline or add a
    background pixel. At most seven shade pixels change in any64-pixel tile.
    """
    bank,meta,_=compile_tiles(blocks)
    if len(bank)<=192:return {'applied':False,'initial_patterns':len(bank)}
    lookup={item.key:i for i,item in enumerate(bank)}
    protected={0,1}
    for ident in (3,13,28,42,15):
        for item in blocks[ident].tiles():
            if item.key in lookup:protected.add(lookup[item.key])
    for ident in (4,29,11):
        for j,item in enumerate(blocks[ident].tiles()):
            if j in (10,11,14,15) and item.key in lookup:protected.add(lookup[item.key])
    for i in range(4):protected.add(lookup[library[f'emblem_{i}'].key])
    original=[item.key[0] for item in bank]
    usage=Counter(meta);groups={i:[i] for i in range(len(bank))};merges=[]
    while len(groups)>192:
        candidates=[]
        for slave,members in groups.items():
            if slave in protected:continue
            for master,other in groups.items():
                if master<2 or slave==master or bank[slave].palette!=bank[master].palette:continue
                a,b=original[slave],original[master]
                if any((x==0)!=(y==0) for x,y in zip(a,b)):continue
                errors=[sum(x!=y for x,y in zip(original[m],b)) for m in members]
                if max(errors)>7:continue
                weighted=sum(e*usage[native_id(m)] for m,e in zip(members,errors))
                candidates.append((max(errors),weighted,sum(errors),
                                   -sum(usage[native_id(m)] for m in other),slave,master))
        assert candidates,'Cannot meet192 without damaging protected art or its silhouette'
        maximum,_,total,_,slave,master=min(candidates)
        groups[master]+=groups.pop(slave)
        merges.append({'source_pattern':slave,'shared_pattern':master,
                       'max_shade_pixel_changes':maximum,'total_shade_pixel_changes':total})
    representative={member:master for master,members in groups.items() for member in members}
    errors=[sum(x!=y for x,y in zip(original[i],original[representative[i]])) for i in range(len(bank))]
    assert max(errors)<=7 and all(not errors[i] for i in protected)
    for block in blocks:
        for j,item in enumerate(list(block.tiles())):
            key=item.key if any(item.key[0]) else (bytes(64),1)
            chosen=bank[representative[lookup[key]]]
            assert item.palette==chosen.palette or not any(item.key[0])
            assert all((x==0)==(y==0) for x,y in zip(item.key[0],chosen.key[0]))
            block.indices.paste(chosen.pixels,(j%4*8,j//4*8))
    return {'applied':True,'initial_patterns':len(bank),'final_patterns':192,
            'protected_pattern_count':len(protected),'palette_and_all_silhouettes_preserved':True,
            'max_shade_pixels_changed_per8x8_pattern':max(errors),'total_changed_shade_pixels':sum(errors),
            'merges':merges,'per_original_pattern_pixel_errors':errors}


def rgba(canvas,palettes=BG,transparent=True):
    out=Image.new('RGBA',canvas.indices.size)
    for y in range(out.height):
        for x in range(out.width):
            colour=palettes[canvas.palettes.getpixel((x//8,y//8))][canvas.indices.getpixel((x,y))]
            alpha=canvas.mask.getpixel((x,y)) if transparent else 255
            out.putpixel((x,y),tuple(colour)+(alpha,))
    return out


def encode_2bpp(image):
    out=bytearray()
    for y in range(image.height):
        row=[image.getpixel((x,y)) for x in range(8)]
        out.extend((sum((n&1)<<(7-x) for x,n in enumerate(row)),
                    sum(((n>>1)&1)<<(7-x) for x,n in enumerate(row))))
    return out


def raw_original(path):return subprocess.check_output(['git','show',f'{BASE}:{path}'],cwd=ROOT)


def old_decoded_blocks():
    sheet=Image.open(BytesIO(raw_original('gfx/tilesets/peon.png')))
    met=raw_original('data/tilesets/peon_metatiles.bin');attr=raw_original('gfx/tilesets/peon_palette_map.bin')
    result=[]
    for ident in range(47):
        block=Canvas()
        for j,tid in enumerate(met[ident*16:ident*16+16]):
            i=tid if tid<96 else tid-32
            pixels=sheet.crop((i%16*8,i//16*8,i%16*8+8,i//16*8+8))
            im=Image.frombytes('L',(8,8),pixels.tobytes())
            pal=(attr[tid//2]>>(tid%2*4))&7
            block.put(Tile(im,pal,Image.new('L',(8,8),255),'old'),j%4,j//4)
        result.append(block)
    return result


def main():
    blocks,den,library=build_blocks()
    reduction=reduce_shade_variants(blocks,library)
    if reduction['applied']:
        # Composite public Den PNG must depict the exact finalized tile data.
        den=Canvas((64,64))
        for i in range(4):
            b=blocks[9+i];x=i%2*32;y=i//2*32
            den.indices.paste(b.indices,(x,y));den.mask.paste(b.mask,(x,y))
            den.palettes.paste(b.palettes,(x//8,y//8))
    bank,meta,report=compile_tiles(blocks)
    report['shade_variant_consolidation']=reduction
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'budget_review.json').write_text(json.dumps(report,indent=2)+'\n')
    assert len(bank)<=192,f'{len(bank)} unique native patterns exceed192; see budget_review.json'
    sheet=Image.new('P',(128,96))
    sheet.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
    attributes=[7]*256
    for i,item in enumerate(bank):
        sheet.paste(item.pixels,(i%16*8,i//16*8))
        attributes[native_id(i)]=item.palette|(8 if i>=96 else 0)
    packed=bytes(attributes[i]|attributes[i+1]<<4 for i in range(0,256,2))
    assert len(meta)==47*16 and len(packed)==128
    old=old_decoded_blocks();changes=[]
    for ident,(before,after) in enumerate(zip(old,blocks)):
        a=rgba(before,transparent=False).tobytes();b=rgba(after,transparent=False).tobytes()
        changed=sum(a[i:i+3]!=b[i:i+3] for i in range(0,len(a),4))
        assert changed>0,(ident,'legacy art still used')
        changes.append({'id':ident,'name':NAMES[ident],'changed_pixels':changed})
    # Only after every budget/representation gate passes are the three native
    # inputs replaced. Collision scripts and maps belong to separate owners.
    sheet.save(ROOT/'gfx/tilesets/peon.png')
    (ROOT/'gfx/tilesets/peon_palette_map.bin').write_bytes(packed)
    (ROOT/'data/tilesets/peon_metatiles.bin').write_bytes(meta)
    frames=b''.join(bytes(encode_2bpp(item.pixels)) for phase in range(3) for item in flame_tiles(phase))
    assert len(frames)==96
    firepath=ROOT/'gfx/tilesets/peon_environment_fire.bin';firepath.write_bytes(frames)
    fires={'vram_bank':0,'tile_ids':[0,1],'vram_addresses':[0x9000,0x9010],
           'palette_id':4,'phase_count':3,'bytes_per_phase':32,'frame_order':'phase0L,phase0R,phase1L,phase1R,phase2L,phase2R',
           'native_frames_file':str(firepath.relative_to(ROOT)),'uses_block_ids':[34,39],
           'no_nonfire_tile_reuses_animated_patterns':True}
    (OUT/'fire_animation.json').write_text(json.dumps(fires,indent=2)+'\n')
    for name in ('blocks','sources','maps','props'):(OUT/name).mkdir(exist_ok=True)
    assets=[]
    for ident,block in enumerate(blocks):
        name=f'{ident:02d}_{NAMES[ident]}'
        im=rgba(block);im.save(OUT/'blocks'/(name+'.png'))
        im.resize((256,256),Image.Resampling.NEAREST).save(OUT/'blocks'/(name+'_8x.png'))
        block.indices.save(OUT/'sources'/(name+'_indices.png'))
        block.palettes.save(OUT/'sources'/(name+'_palette_grid.png'))
        block.mask.save(OUT/'sources'/(name+'_alpha.png'))
        assert set(im.getchannel('A').tobytes())<={0,255}
        assets.append({'id':ident,'name':NAMES[ident],'native_size':[32,32],
                       'transparent_png':str((OUT/'blocks'/(name+'.png')).relative_to(ROOT)),
                       'alpha_values':sorted(set(im.getchannel('A').tobytes()))})
    denim=rgba(den);denim.save(OUT/'props'/'the_den_horde_hide_and_tusks.png')
    denim.resize((512,512),Image.Resampling.NEAREST).save(OUT/'props'/'the_den_horde_hide_and_tusks_8x.png')
    for name,ident in {'orc_hut':4,'troll_hut':29,'horde_banner':6,'layered_cliff':1,
                        'sandstone_boulder':37,'cactus_red_blooms':3,'desert_agave':13,
                        'coastal_palm':28,'deadthorn_tree':42,'cave_mouth':15,
                        'campfire':39,'brazier':34,'palisade':30,'gate_jamb':33,
                        'watchtower':31,'orc_bedroll':40,'troll_bedroll':43,
                        'orc_table':41,'troll_table':44,'wayfinding_sign':35,
                        'burning_blade_skull':36,'darkspear_spirit_mask':46}.items():
        image=rgba(blocks[ident]);image.save(OUT/'props'/(name+'.png'))
        image.resize((256,256),Image.Resampling.NEAREST).save(OUT/'props'/(name+'_8x.png'))
    for phase in range(3):
        image=Image.new('RGBA',(16,8))
        for i,ft in enumerate(flame_tiles(phase)):
            for y in range(8):
                for x in range(8):
                    image.putpixel((i*8+x,y),BG[4][ft.pixels.getpixel((x,y))]+(ft.mask.getpixel((x,y)),))
        image.save(OUT/'props'/f'fire_top_phase_{phase}.png')
        image.resize((128,64),Image.Resampling.NEAREST).save(OUT/'props'/f'fire_top_phase_{phase}_8x.png')
    contact=Image.new('RGB',(1024,1632),'#35291f');draw=ImageDraw.Draw(contact)
    for ident,block in enumerate(blocks):
        col,row=ident%4,ident//4;x,y=col*256,row*136
        draw.text((x+8,y+5),f'{ident:02d} {NAMES[ident]}',fill='#ffdda4')
        im=rgba(block).resize((96,96),Image.Resampling.NEAREST)
        contact.paste(im,(x+8,y+26),im)
    contact.save(OUT/'all_native_environment_blocks_contact_sheet.png')
    mapreports={}
    for name,(width,height) in DIMS.items():
        data=(ROOT/f'maps/{name}.blk').read_bytes();assert len(data)==width*height
        pals=palettes_for(name);canvas=Image.new('RGB',(width*32,height*32))
        for pos,ident in enumerate(data):
            image=rgba(blocks[ident],pals,False).convert('RGB')
            canvas.paste(image,(pos%width*32,pos//width*32))
        canvas.save(OUT/'maps'/(name+'.png'))
        canvas.resize((width*64,height*64),Image.Resampling.NEAREST).save(OUT/'maps'/(name+'_2x.png'))
        mapreports[name]={'runtime_capture':False,'source':'Native compiler reconstruction; actors added by ROM.',
                         'native_pixel_size':[width*32,height*32],'block_sha256':hashlib.sha256(data).hexdigest()}
    manifest={'passed':True,'base':BASE,'drawing_source':'Original pixel-grid modular silhouettes; no old native patterns reused.',
              'native_pattern_count':len(bank),'tile_budget':192,'native_sheet_slots':192,
              'palettes_per_background_tile':1,'colours_per_tile':4,'palettes':BG,
              'block_ids_preserved':47,'all_47_blocks_redrawn':True,'old_to_new_pixel_changes':changes,
              'maps_and_collisions_modified_by_this_builder':False,
              'shade_variant_consolidation':reduction,
              'door_alignment':{'hut4_and29':'bottom-right movement quadrant x16..31,y16..31',
                                'den11':'64x64 composite doorway x16..31,y48..63',
                                'cave15':'dark mouth above separate open transition16',
                                'east_exit33':'off-white bone/stone jamb; transition16 stays open'},
              'assets':assets,'maps':mapreports,'fire':fires,'runtime_capture':False,
              'limitations':['The fixed-screen seven-zone migration is not part of this art redraw.',
                             'These are background tiles: transparent margins are baked into the exact regional ground colour.',
                             'ROM gameplay/Chromatic behavior requires native validation separate from this compiler sheet.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Redrawn47 native blocks: {len(bank)}/192 exact palette-aware patterns; two animated fire tiles inbank0.')


if __name__=='__main__':main()
