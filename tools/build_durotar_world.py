#!/usr/bin/env python3
"""Reproducible native Durotar map art, with Crystal's 192-tile VRAM budget.

All artwork is drawn on the actual Game Boy pixel grid.  Each 32x32 map block
is composed of sixteen reusable 8x8 indexed tiles; no large image is resized.
The first 17 block IDs retain v0.2 collision semantics and save coordinates.
"""
from collections import deque
from pathlib import Path
import json

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/world'

# Native RGB555-compatible colours.  Palette zero matches soil at every edge.
BG = [
    [(239,181,115),(206,123,66),(140,66,41),(57,33,33)], # cliffs
    [(239,181,115),(214,148,82),(173,99,49),(90,57,33)], # soil
    [(239,181,115),(148,173,74),(82,115,49),(41,66,33)], # desert plants
    [(239,181,115),(123,198,206),(66,140,165),(33,82,123)], # coast
    [(239,181,115),(255,222,148),(230,165,99),(156,90,49)], # clear pale-earth paths
    [(239,181,115),(214,165,107),(132,90,57),(57,41,33)], # wood/hide
    [(239,181,115),(189,82,57),(123,49,41),(49,33,33)], # Horde roofs
    [(255,247,214),(255,247,214),(123,74,41),(8,8,8)], # Crystal font
]
REGION_BGS = {}
for name, soil in [
    ('TheDen',[(239,181,115),(214,148,82),(173,99,49),(90,57,33)]),
    ('ValleyOfTrials',[(239,165,99),(206,123,66),(165,82,49),(90,49,33)]),
    ('DurotarRoad',[(239,197,132),(214,165,90),(173,115,57),(99,66,33)]),
    ('SenjinVillage',[(247,222,165),(222,189,123),(181,148,90),(99,74,41)]),
    ('RazorHill',[(231,165,107),(198,115,66),(156,82,49),(90,49,33)]),
    ('OrgrimmarGate',[(222,148,90),(189,107,57),(140,66,41),(82,41,33)]),
    ('BurningBladeCavern',[(115,107,123),(99,90,107),(74,66,82),(41,33,49)]),
]:
    pals = [pal.copy() for pal in BG]
    pals[1] = soil
    # Matching ground colour prevents seams between vegetation and bare soil.
    for p in (0,2,3,4,5,6): pals[p][0] = soil[0]
    if name == 'SenjinVillage':
        # Amber beaten earth remains readable against the village's pale sand.
        pals[4] = [soil[0],(230,173,90),(189,123,57),(115,74,33)]
    if name == 'BurningBladeCavern':
        pals[0] = [(115,107,123),(90,82,107),(66,57,82),(33,24,41)]
        pals[4] = [(115,107,123),(148,140,165),(107,99,123),(57,49,74)]
        pals[5] = [(115,107,123),(148,123,99),(99,74,57),(41,33,41)]
        pals[6] = [(115,107,123),(206,90,49),(140,49,49),(41,24,41)]
    REGION_BGS[name] = pals

DIMS = {'PeonOpening':(8,6),'GrommashHold':(8,6),'TheDen':(12,10),
        'ValleyOfTrials':(16,12),'DurotarRoad':(12,14),'SenjinVillage':(12,10),
        'RazorHill':(12,10),'OrgrimmarGate':(12,10),'BurningBladeCavern':(10,10)}
WARPS = {'TheDen':[(20,10)],'ValleyOfTrials':[(4,12),(28,12),(24,4)],
         'DurotarRoad':[(4,14),(12,24),(12,4)],'SenjinVillage':[(10,4)],
         'RazorHill':[(12,16),(12,4)],'OrgrimmarGate':[(12,16)],
         'BurningBladeCavern':[(10,16)]}
OBJECTIVES = {
    'PeonOpening':[(5,8),(6,8),(7,8),(8,8)],
    'GrommashHold':[(8,3),(4,6),(8,5),(12,6),(8,8)],
    'TheDen':[(10,9),(10,8),(18,12),(19,15),(6,12),(14,9),(10,12),
              (8,15),(8,14),(5,16),(6,15),(14,15)],
    'ValleyOfTrials':[(8,10),(10,19),(6,11),(16,20),(8,9),(10,18),(6,10)],
    'DurotarRoad':[(8,10),(8,18),(16,20),(5,5),(18,8),(5,22),(18,23),(16,16)],
    'SenjinVillage':[(8,10),(6,12),(14,10),(16,13),(6,16),(14,16)],
    'RazorHill':[(8,10),(6,12),(16,10),(8,16),(16,16),(14,8)],
    'OrgrimmarGate':[(8,10),(10,12),(14,12)],
    'BurningBladeCavern':[(8,10),(12,8),(5,6),(5,3),(14,3)],
}
CACTI = [(7,7),(23,9),(9,17)]
BLOCKS = []

# Deliberate geological clusters frame the route rather than randomly placing
# obstacles.  Coordinates are 32x32 map blocks; all destinations, cactus
# approaches and NPC interaction rings are reserved before decoration.
CANYON_ESCARPMENTS = {
    'TheDen':[(1,1),(2,1),(3,1),(10,2),(10,3)],
    'ValleyOfTrials':[(5,8),(6,8),(7,8),(9,3),(9,4),(13,3),(14,3),(14,4),
                      (10,9),(11,9)],
    'DurotarRoad':[(3,3),(3,4),(3,5),(8,6),(8,7),(4,10),(4,11),(7,11),(7,12)],
    'RazorHill':[(2,3),(2,4),(9,3),(9,4),(2,6),(9,7)],
    'OrgrimmarGate':[(2,5),(2,6),(9,5),(9,6)],
}
CANYON_BOULDERS = {
    'TheDen':[(1,2),(1,3),(1,5),(4,2),(4,3),(8,1),(9,1),(9,3),(2,8),(3,8),(7,7)],
    'ValleyOfTrials':[(5,3),(6,3),(5,4),(6,4),(8,4),(8,5),(8,8),(9,8),
                      (11,8),(12,9),(13,10),(5,10),(13,5)],
    'DurotarRoad':[(3,2),(4,2),(5,3),(5,4),(5,5),(7,3),(8,3),(8,5),
                   (8,8),(4,9),(5,10),(5,11),(7,10),(8,11),(8,12),(9,12)],
    'RazorHill':[(4,3),(8,3),(8,4),(3,7),(9,5),(9,6)],
    'OrgrimmarGate':[(3,5),(3,6),(8,5),(8,6),(3,7),(8,7)],
}


def base(pattern=True):
    im = Image.new('P',(32,32),0)
    if pattern:
        d = ImageDraw.Draw(im)
        # A small repeated grain pattern keeps the shared terrain budget low.
        for y in (0,16):
            for x in (0,16):
                d.line((x+3,y+5,x+4,y+5),fill=1)
                d.point((x+12,y+12),fill=1)
    return im


def add(name, im, pal, collision='FLOOR'):
    BLOCKS.append({'name':name,'im':im,'pal':pal,'collision':collision})
    return len(BLOCKS)-1


def build_blocks():
    BLOCKS.clear()
    add('bare_soil',base(),1) # 0
    cliff = Image.new('P',(32,32),2); d=ImageDraw.Draw(cliff)
    for x,y in [(0,0),(16,0),(0,16),(16,16)]:
        d.polygon([(x,y),(x+13,y),(x+15,y+4),(x+14,y+12),(x+10,y+15),(x,y+14)],fill=1)
        d.line((x,y+1,x+12,y+1,x+14,y+4),fill=0)
        d.line((x,y+14,x+10,y+15,x+14,y+12),fill=3)
        d.line((x+5,y+5,x+10,y+6),fill=2)
    add('layered_escarpment',cliff,0,'WALL') # 1
    road=Image.new('P',(32,32),1);d=ImageDraw.Draw(road)
    for x,y in [(3,5),(19,5),(12,12),(28,12),(3,21),(19,21),(12,28),(28,28)]:
        d.line((x,y,x+1,y),fill=2)
    add('main_road',road,4) # 2
    cactus=base(False);d=ImageDraw.Draw(cactus)
    d.line((8,29,23,29),fill=2)
    d.rectangle((14,4,18,28),fill=3);d.rectangle((15,3,17,27),fill=1)
    d.line((15,5,15,25),fill=0)
    d.rectangle((8,11,14,15),fill=3);d.rectangle((8,6,10,13),fill=3)
    d.line((9,7,9,12),fill=1);d.line((10,12,14,12),fill=1)
    d.rectangle((18,16,23,20),fill=3);d.rectangle((21,10,23,19),fill=3)
    d.line((22,11,22,18),fill=1);d.line((18,17,21,17),fill=1)
    add('cactus',cactus,2,'WALL') # 3
    hut=base(False);d=ImageDraw.Draw(hut)
    d.polygon([(1,18),(6,11),(15,4),(23,11),(30,18)],fill=3)
    d.polygon([(3,17),(15,6),(28,17)],fill=1)
    for y in (11,14,17):d.line((16-(y-5),y,16+(y-5),y),fill=2)
    d.rectangle((4,19,27,29),fill=2);d.rectangle((12,21,20,31),fill=3)
    d.line((5,18,5,29),fill=1);d.line((26,18,26,29),fill=1)
    d.line((13,22,13,29),fill=1)
    add('hide_hut',hut,5,'WALL') # 4
    rug=Image.new('P',(32,32),2);d=ImageDraw.Draw(rug)
    d.rectangle((2,0,29,31),fill=1);d.line((3,0,3,31),fill=0);d.line((28,0,28,31),fill=0)
    d.polygon([(16,7),(22,16),(16,25),(10,16)],outline=3)
    d.line((16,10,16,22),fill=0);d.line((13,16,19,16),fill=0)
    add('hold_red_carpet',rug,6) # 5
    banner=base(False);d=ImageDraw.Draw(banner)
    d.line((8,3,8,29),fill=3,width=1);d.polygon([(9,4),(23,4),(23,19),(16,23),(9,19)],fill=3)
    d.polygon([(10,5),(22,5),(22,18),(16,21),(10,18)],fill=1)
    d.polygon([(16,7),(21,11),(19,16),(16,18),(13,16),(11,11)],fill=3)
    d.line((16,9,16,18),fill=0)
    add('horde_standard',banner,6,'WALL') # 6
    floor=Image.new('P',(32,32),2);d=ImageDraw.Draw(floor)
    for y in (0,16):
        for x in (0,16):
            d.rectangle((x+1,y+1,x+14,y+14),fill=1)
            d.line((x+2,y+2,x+13,y+2),fill=0)
            d.line((x+2,y+14,x+13,y+14),fill=3)
    add('sandstone_floor',floor,5) # 7
    add('sandy_clearance',base(False),1) # 8
    den=Image.new('P',(64,64),0);d=ImageDraw.Draw(den)
    # Narrow roof outline, a large dark arch, and tall bone supports.
    d.polygon([(2,29),(9,17),(32,2),(54,17),(62,29)],fill=3)
    d.polygon([(5,27),(32,5),(59,27)],fill=1)
    for y in (12,17,22,26):d.line((32-(y-5),y,32+(y-5),y),fill=2)
    d.line((32,6,32,26),fill=3)
    d.rectangle((7,29,56,57),fill=2);d.rectangle((10,31,53,54),fill=1)
    d.rectangle((25,35,39,63),fill=3);d.arc((24,32,40,49),180,360,fill=0,width=2)
    for x in (4,57):
        d.polygon([(x,59),(x,17),(x+2,7),(x+4,17),(x+4,59)],fill=0)
        d.line((x+4,19,x+4,57),fill=3)
    for x in (13,45):
        d.rectangle((x,36,x+6,41),fill=3);d.line((x,36,x+5,36),fill=0)
    for i in range(4):
        x,y=i%2*32,i//2*32
        add('den_'+str(i),den.crop((x,y,x+32,y+32)),6,'WALL') # 9..12
    scrub=base(False);d=ImageDraw.Draw(scrub)
    for x,y in [(7,9),(23,25)]:
        d.line((x,y,x,y-5),fill=2);d.line((x,y-1,x-3,y-4),fill=1);d.line((x,y-1,x+3,y-4),fill=1)
    add('dry_scrub',scrub,2) # 13
    water=Image.new('P',(32,32),2);d=ImageDraw.Draw(water)
    for x,y in [(1,5),(17,5),(5,13),(21,13),(1,21),(17,21),(5,29),(21,29)]:
        d.line((x,y,x+5,y),fill=1);d.point((x+2,y+1),3)
    add('sea',water,3,'WALL') # 14
    mouth=base(False);d=ImageDraw.Draw(mouth)
    d.polygon([(1,31),(3,13),(10,5),(23,4),(29,13),(31,31)],fill=2)
    d.line((4,13,11,7,22,6,27,13),fill=0,width=2)
    d.ellipse((8,13,24,39),fill=3);d.rectangle((8,25,24,31),fill=3)
    add('cavern_mouth',mouth,0,'WALL') # 15
    add('zone_transition',road.copy(),4,'WARP_PANEL') # 16
    # Path edge variants share the road's grain tiles and plain soil exterior.
    for name, openings in [('road_ns','NS'),('road_ew','EW'),('road_ne','NE'),
                           ('road_nw','NW'),('road_se','SE'),('road_sw','SW'),
                           ('road_nse','NSE'),('road_nsw','NSW'),
                           ('road_new','NEW'),('road_sew','SEW')]:
        im=base(False);d=ImageDraw.Draw(im);d.rectangle((8,8,23,23),fill=1)
        if 'N' in openings:d.rectangle((8,0,23,8),fill=1)
        if 'S' in openings:d.rectangle((8,23,23,31),fill=1)
        if 'E' in openings:d.rectangle((23,8,31,23),fill=1)
        if 'W' in openings:d.rectangle((0,8,8,23),fill=1)
        for x,y in [(12,4),(20,12),(12,20),(28,12)]:
            if im.getpixel((x,y))==1:d.line((x,y,x+1,y),fill=2)
        add(name,im,4)
    shore=water.copy();d=ImageDraw.Draw(shore)
    d.rectangle((0,0,7,31),fill=0)
    for y in range(0,32,8):
        d.rectangle((8,y,10,y+3),fill=1);d.rectangle((8,y+4,9,y+7),fill=0)
    add('east_shore',shore,3,'WALL') # 27
    palm=base(False);d=ImageDraw.Draw(palm)
    d.line((16,13,16,30),fill=3,width=3);d.line((15,15,15,29),fill=1)
    for y in (17,21,25):d.line((15,y,17,y),fill=2)
    for pts in [[(16,13),(3,6),(1,10),(13,12)],[(16,13),(11,1),(14,1),(18,11)],
                [(16,13),(28,4),(31,8),(20,13)],[(16,13),(6,17),(4,20),(15,16)],
                [(16,13),(25,17),(28,21),(18,16)]]:
        d.polygon(pts,fill=3);d.line(pts[:2],fill=1,width=2)
    add('coastal_palm',palm,2,'WALL') # 28
    troll=hut.copy();d=ImageDraw.Draw(troll)
    d.line((15,1,15,5),fill=3,width=2);d.line((14,2,17,2),fill=1)
    d.line((1,15,1,28),fill=3,width=2);d.line((30,15,30,28),fill=3,width=2)
    d.line((0,15,3,18),fill=1);d.line((28,18,31,15),fill=1)
    add('troll_thatched_hut',troll,5,'WALL') # 29
    fence=base(False);d=ImageDraw.Draw(fence)
    for x in (0,8,16,24):
        d.polygon([(x,12),(x+3,4),(x+6,12),(x+6,28),(x,28)],fill=3)
        d.polygon([(x+1,12),(x+3,6),(x+5,12),(x+5,27),(x+1,27)],fill=1)
        d.line((x+4,12,x+4,27),fill=2)
    d.rectangle((0,16,31,18),fill=2);d.line((0,16,31,16),fill=3)
    add('spiked_palisade',fence,5,'WALL') # 30
    tower=hut.copy();d=ImageDraw.Draw(tower)
    d.line((5,19,3,31),fill=3,width=2);d.line((26,19,28,31),fill=3,width=2)
    d.line((3,31,26,20),fill=2);d.line((6,20,28,31),fill=2)
    d.rectangle((5,18,26,21),fill=3);d.line((6,18,25,18),fill=1)
    add('watchtower',tower,6,'WALL') # 31
    bridge=Image.new('P',(32,32),3);d=ImageDraw.Draw(bridge)
    for y in range(0,32,8):
        d.rectangle((1,y+1,30,y+6),fill=2);d.line((2,y+1,29,y+1),fill=1)
    d.line((2,0,2,31),fill=1);d.line((29,0,29,31),fill=1)
    add('timber_boardwalk',bridge,5) # 32
    stones=cliff.copy();d=ImageDraw.Draw(stones)
    d.rectangle((0,0,31,7),fill=1);d.line((0,0,31,0),fill=0);d.line((0,7,31,7),fill=3)
    d.line((15,1,15,6),fill=2)
    add('fortified_gate_wall',stones,0,'WALL') # 33
    torch=base(False);d=ImageDraw.Draw(torch)
    d.rectangle((14,15,17,29),fill=3);d.rectangle((12,13,19,18),fill=2)
    d.polygon([(13,13),(12,8),(15,4),(17,8),(19,5),(20,11),(18,14)],fill=1)
    d.polygon([(15,13),(15,8),(17,10),(18,8),(18,13)],fill=0)
    add('fire_brazier',torch,6,'WALL') # 34
    # A coast-facing quay and a wooden sign use the same wood palette tiles.
    sign=base(False);d=ImageDraw.Draw(sign)
    d.rectangle((14,8,17,29),fill=3);d.rectangle((8,8,23,18),fill=3)
    d.rectangle((9,9,22,16),fill=1);d.line((11,12,20,12),fill=2)
    d.line((19,10,22,12,19,14),fill=3)
    add('wayfinding_sign',sign,5,'WALL') # 35
    skull=base(False);d=ImageDraw.Draw(skull)
    d.ellipse((8,8,23,23),fill=3);d.ellipse((9,8,22,21),fill=1)
    d.rectangle((11,18,20,23),fill=1);d.rectangle((11,12,14,15),fill=3)
    d.rectangle((18,12,21,15),fill=3);d.polygon([(16,15),(14,18),(18,18)],fill=3)
    d.line((13,21,13,23),fill=2);d.line((17,21,17,23),fill=2)
    add('burning_blade_skull',skull,5,'WALL') # 36
    rock=base(False);d=ImageDraw.Draw(rock)
    d.polygon([(8,14),(11,9),(18,8),(23,13),(22,21),(15,23),(9,21)],fill=3)
    d.polygon([(9,14),(12,10),(18,9),(21,13),(18,18),(10,17)],fill=1)
    d.polygon([(10,18),(18,19),(22,15),(21,20),(15,22),(10,20)],fill=2)
    d.line((12,11,16,10),fill=0)
    add('desert_boulder',rock,1,'WALL') # 37
    # Crystal rejects metatile ID zero before reading its collision row.  A
    # nonzero clone keeps the soil artwork and existing block IDs unchanged.
    add('walkable_bare_soil',BLOCKS[0]['im'].copy(),1) # 38
    # Rearrange existing palette-six tiles: brazier flame above the crossed
    # watchtower timbers.  This adds a campfire without allocating VRAM tiles.
    campfire=base(False)
    for row in (0,1):
        for col in (1,2):
            campfire.paste(BLOCKS[34]['im'].crop((col*8,row*8,col*8+8,row*8+8)),
                           (col*8,(row+1)*8))
    campfire.paste(BLOCKS[31]['im'].crop((0,24,32,32)),(0,24))
    add('campfire',campfire,6,'WALL') # 39


def road_shape(neighbours):
    names={b['name']:i for i,b in enumerate(BLOCKS)}
    s=''.join(c for c in 'NSEW' if c in neighbours)
    if len(s)==4 or len(s)<2: return 2
    lookup={'NS':'road_ns','EW':'road_ew','NE':'road_ne','NW':'road_nw',
            'SE':'road_se','SW':'road_sw','NSE':'road_nse','NSW':'road_nsw',
            'NEW':'road_new','SEW':'road_sew'}
    return names[lookup[s]]


def build_map(name):
    w,h=DIMS[name]; data=[0]*(w*h); roads=set()
    def put(x,y,block):
        if 0<=x<w and 0<=y<h:data[y*w+x]=block
    def line(points):
        for a,b in zip(points,points[1:]):
            x,y=a;tx,ty=b
            assert x==tx or y==ty,(name,a,b)
            while (x,y)!=(tx,ty):
                roads.add((x,y));x+=(tx>x)-(tx<x);y+=(ty>y)-(ty<y)
            roads.add((tx,ty))
    for y in range(h):
        for x in range(w):
            if x in (0,w-1) or y in (0,h-1):put(x,y,1)
            elif (x+3*y)%11==0:put(x,y,13)
    if name=='PeonOpening':
        line([(1,4),(6,4)]);put(2,2,3);put(6,1,3)
    elif name=='GrommashHold':
        for y in range(1,h-1):
            for x in range(1,w-1):put(x,y,5 if x in (3,4) else 7)
        put(1,1,6);put(6,1,6)
    elif name=='TheDen':
        line([(2,4),(2,5),(5,5),(10,5)])
        line([(5,4),(5,6),(9,6),(9,7)])
        for x,y,b in [(2,2,9),(3,2,10),(2,3,11),(3,3,12),(8,2,4),
                       (1,4,3),(9,2,3),(10,7,3),(6,2,6),(7,8,13),(3,7,35),(7,3,37)]:put(x,y,b)
    elif name=='ValleyOfTrials':
        # A cliff-wrapped basin: the cave is visibly north of the main exit.
        for y in (1,2):
            for x in range(3,10):put(x,y,1)
        for x,y in [(1,3),(2,3),(2,8),(2,9),(10,3),(10,4),(11,3),
                    (6,9),(7,9),(8,9),(13,9),(14,9)]:put(x,y,1)
        line([(2,6),(5,6),(5,7),(9,7),(9,6),(14,6)])
        line([(9,6),(12,6),(12,2)])
        line([(5,6),(4,6),(4,5)])
        # Hana'zua shelters beside the southern fork; Sarkoth's basin is
        # deliberately visible beyond the cliff bend, off the through road.
        line([(5,7),(5,9),(6,9),(6,10),(8,10)])
        put(12,1,15);put(11,1,1);put(13,1,1)
        put(3,3,3);put(11,4,3);put(4,8,3);put(13,8,3)
        for x,y in [(4,3),(8,4),(7,7),(12,7),(5,9),(3,9),(13,3)]:put(x,y,13)
        for x,y in [(7,4),(8,8),(3,9),(14,3)]:put(x,y,37)
        put(10,6,35)
        # A small Horde rest camp and palisade make the eastern canyon mouth
        # recognizable without sealing the saved exit or the cactus approaches.
        put(7,5,39);put(9,10,6);put(13,5,6);put(13,7,30)
    elif name=='DurotarRoad':
        line([(2,7),(4,7),(4,6),(6,6),(6,2)])
        line([(6,6),(7,6),(7,9),(6,9),(6,12)])
        for y in (2,3,4,5,9,10,11):put(1,y,1)
        for x,y in [(9,1),(9,2),(9,3),(10,3),(2,10),(3,10),(3,11),
                    (9,10),(9,11),(10,11)]:put(x,y,1)
        for x,y in [(3,3),(8,4),(2,8),(8,12)]:put(x,y,3)
        for x,y in [(3,2),(8,8),(4,11),(10,8)]:put(x,y,37)
        put(5,7,35);put(5,11,35)
        # A small eastern coastal branch gives the yellow crawler a distinct
        # habitat without turning the north/south route into a beach.
        for y in range(1,h-1):put(11,y,14);put(10,y,27)
        line([(7,9),(8,9),(8,11),(9,11)])
        put(9,12,28);put(9,9,28)
        put(7,2,39);put(5,2,6);put(8,2,6)
        put(9,6,30);put(9,7,30)
    elif name=='SenjinVillage':
        # Sand-coloured hamlet with a western inlet and east-facing quay.
        for y in range(h):
            for x in range(10,w):put(x,y,14)
            if y>1:put(9,y,27)
        for x in range(1,w):put(x,h-1,14)
        for x,y in [(2,2),(7,2),(8,4),(8,7)]:put(x,y,29)
        for x,y in [(1,3),(3,1),(8,1),(1,7),(7,7)]:put(x,y,28)
        line([(5,2),(5,5),(4,5),(4,7),(3,7),(3,8)])
        line([(5,5),(7,5),(7,6),(8,6)])
        line([(4,7),(7,7),(7,8)])
        put(9,6,32);put(10,6,32);put(8,8,35)
    elif name=='RazorHill':
        for x in range(1,w-1):put(x,1,30);put(x,8,30)
        for y in range(2,8):put(1,y,30);put(10,y,30)
        for x,y in [(2,2),(8,2),(2,7),(8,6)]:put(x,y,4)
        put(3,1,31);put(9,1,31);put(5,2,6)
        line([(6,2),(6,8)])
        line([(3,5),(8,5)]);line([(4,6),(4,8)])
        put(6,1,2);put(5,8,0);put(7,8,0);put(7,2,39)
    elif name=='OrgrimmarGate':
        for x in range(1,w-1):put(x,1,33);put(x,2,33)
        for y in (3,4):put(3,y,33);put(8,y,33)
        put(2,2,31);put(9,2,31);put(4,3,6);put(7,3,6)
        put(6,2,15) # Visible stone arch at the end of the north approach.
        line([(6,3),(6,8)]);line([(4,6),(7,6)])
        put(4,4,39);put(7,4,39);put(2,7,3);put(9,7,3)
    elif name=='BurningBladeCavern':
        # Two chambers linked by a clear two-tile-wide passage.
        data[:]=[1]*(w*h)
        for y in range(1,5):
            for x in range(2,8):put(x,y,0)
        for y in range(5,9):
            for x in range(2,7):put(x,y,0)
        for x in (2,3,7):put(x,4,1)
        for x in (2,3,6):put(x,5,1)
        for x,y in [(2,1),(7,1),(7,4),(2,8),(6,8)]:put(x,y,1)
        line([(5,8),(5,6),(4,6),(4,4),(6,4),(6,2)])
        put(3,2,36);put(7,2,34);put(2,6,34)
        put(3,3,37);put(6,6,37)
    reserved=set(roads)
    for x,y in OBJECTIVES.get(name,[])+WARPS.get(name,[]):
        reserved.update((xx//2,yy//2) for xx,yy in [(x,y),(x-1,y),(x+1,y),(x,y-1),(x,y+1)])
    if name=='ValleyOfTrials':
        for x,y in CACTI:
            reserved.update((xx//2,yy//2) for xx,yy in [(x,y),(x-1,y),(x+1,y),(x,y-1),(x,y+1)])
    if name=='TheDen':
        # The reactive scorpion's complete radius and the nine linked hut
        # approaches must retain their existing traversal and event behaviour.
        reserved.update((x//2,y//2) for x in range(17,22) for y in range(13,18)
                        if abs(x-19)+abs(y-15)<=2)
    # Reserve actual hut door approach quadrants, including the large Den.
    for i,block in enumerate(data):
        if block in (4,29):
            bx,by=i%w,i//w;reserved.update([(bx,by),(bx,by+1),(bx+1,by)])
        elif block==11:
            bx,by=i%w,i//w;reserved.update([(bx,by),(bx,by+1)])
    for block,clusters in [(1,CANYON_ESCARPMENTS),(37,CANYON_BOULDERS)]:
        for x,y in clusters.get(name,[]):
            if (x,y) not in reserved and data[y*w+x] in (0,8,13,38):put(x,y,block)
    for x,y in roads:
        neighbours={c for c,(dx,dy) in {'N':(0,-1),'S':(0,1),'E':(1,0),'W':(-1,0)}.items()
                    if (x+dx,y+dy) in roads}
        put(x,y,road_shape(neighbours))
    # Keep current save positions and each NPC's interaction ring traversable.
    for x,y in OBJECTIVES.get(name,[]):
        for xx,yy in [(x,y),(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
            bx,by=xx//2,yy//2
            if 0<bx<w-1 and 0<by<h-1 and BLOCKS[data[by*w+bx]]['collision']=='WALL':put(bx,by,8)
    if name=='TheDen':
        for x,y in [(17,15),(18,14),(18,15),(18,16),(19,13),(19,14),(19,16),(19,17),
                     (20,14),(20,15),(20,16),(21,15)]:
            if BLOCKS[data[y//2*w+x//2]]['collision']=='WALL':put(x//2,y//2,8)
    if name=='ValleyOfTrials':
        for x,y in CACTI:put(x//2,y//2,3)
    if name=='TheDen':
        put(6,3,39)
        # Two camp merchants use the upper-left alcove. Its former boulder
        # must not block their cells; this avoids overcrowding the center's
        # limited native NPC/OAM budget without relocating old save actors.
        put(4,3,8)
    for x,y in WARPS.get(name,[]):put(x//2,y//2,16)
    return [38 if block==0 else block for block in data]


def validate_map(name,data):
    w,h=DIMS[name]
    assert 0 not in data,(name,'Crystal treats block ID zero as impassable')
    def walkable(p):
        x,y=p
        return (0<=x<w*2 and 0<=y<h*2 and data[y//2*w+x//2]!=0
                and BLOCKS[data[y//2*w+x//2]]['collision']!='WALL')
    targets=OBJECTIVES.get(name,[])+WARPS.get(name,[])
    if not targets:return {}
    origin=targets[0];q=deque([origin]);reached={origin}
    while q:
        x,y=q.popleft()
        for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if p not in reached and walkable(p):reached.add(p);q.append(p)
    assert all(p in reached for p in targets),(name,'unreachable objective',set(targets)-reached)
    for p in WARPS.get(name,[]):assert data[p[1]//2*w+p[0]//2]==16,(name,p)
    if name=='ValleyOfTrials':
        for x,y in CACTI:
            assert data[y//2*w+x//2]==3
            assert any(p in reached for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)))
    return {'walkable_tiles':len(reached),'objectives_connected':len(targets),
            'boulder_blocks':data.count(37),'escarpment_blocks':data.count(1),
            'warps':WARPS.get(name,[]),'native_pixel_size':[w*32,h*32]}


def palfile(pals):
    return ''.join('\tRGB '+', '.join(f'{v>>3:02d}' for c in pal for v in c)+'\n' for pal in pals)


def transparent_exports():
    """Mask silhouettes, not colour zero: ivory highlights remain opaque."""
    dest=OUT/'buildings';dest.mkdir(parents=True,exist_ok=True)
    props=OUT/'props';props.mkdir(parents=True,exist_ok=True)
    def cutout(kind,mask):
        block=BLOCKS[kind];im=block['im'].copy()
        im.putpalette([v for c in BG[block['pal']] for v in c]+[0]*756)
        out=im.convert('RGBA');out.putalpha(mask);return out
    def silhouette():return Image.new('L',(32,32))
    mask=silhouette();d=ImageDraw.Draw(mask)
    d.polygon([(1,18),(6,11),(15,4),(23,11),(30,18)],fill=255)
    d.rectangle((4,19,27,29),fill=255);d.rectangle((12,21,20,31),fill=255)
    cutout(4,mask).save(dest/'orc_hut.png')
    troll=mask.copy();d=ImageDraw.Draw(troll)
    d.line((15,1,15,5),fill=255,width=2);d.line((14,2,17,2),fill=255)
    d.line((1,15,1,28),fill=255,width=2);d.line((30,15,30,28),fill=255,width=2)
    d.line((0,15,3,18),fill=255);d.line((28,18,31,15),fill=255)
    cutout(29,troll).save(dest/'troll_hut.png')
    tower=mask.copy();d=ImageDraw.Draw(tower)
    d.line((5,19,3,31),fill=255,width=2);d.line((26,19,28,31),fill=255,width=2)
    d.line((3,31,26,20),fill=255);d.line((6,20,28,31),fill=255)
    d.rectangle((5,18,26,21),fill=255)
    cutout(31,tower).save(dest/'watchtower.png')
    cave=silhouette();d=ImageDraw.Draw(cave)
    d.polygon([(1,31),(3,13),(10,5),(23,4),(29,13),(31,31)],fill=255)
    cutout(15,cave).save(dest/'cave_mouth.png')
    den=Image.new('RGBA',(64,64));mask=Image.new('L',(64,64));d=ImageDraw.Draw(mask)
    d.polygon([(2,29),(9,17),(32,2),(54,17),(62,29)],fill=255)
    d.rectangle((7,29,56,57),fill=255);d.rectangle((25,35,39,63),fill=255)
    for x in (4,57):d.polygon([(x,59),(x,17),(x+2,7),(x+4,17),(x+4,59)],fill=255)
    for i in range(4):
        block=BLOCKS[9+i];im=block['im'].copy()
        im.putpalette([v for c in BG[block['pal']] for v in c]+[0]*756)
        den.paste(im.convert('RGBA'),(i%2*32,i//2*32))
    den.putalpha(mask);den.save(dest/'the_den.png')
    # Assembly preview of the native stone wall and cave arch, with the ground
    # excluded.  This is a reusable silhouette, not a new map/warp asset.
    gate=Image.new('RGBA',(64,64));wall=BLOCKS[33]['im'].copy()
    wall.putpalette([v for c in BG[0] for v in c]+[0]*756)
    wall=wall.convert('RGBA')
    for x in (8,40):
        gate.paste(wall.crop((0,0,16,32)),(x,0))
        gate.paste(wall.crop((0,0,16,32)),(x,32))
    gate.paste(wall.crop((0,0,16,16)),(24,0))
    gate.alpha_composite(cutout(15,cave),(16,32))
    gate.save(dest/'orc_gateway.png')
    cactus=silhouette();d=ImageDraw.Draw(cactus)
    d.line((8,29,23,29),fill=255);d.rectangle((14,3,18,28),fill=255)
    d.rectangle((8,11,14,15),fill=255);d.rectangle((8,6,10,13),fill=255)
    d.rectangle((18,16,23,20),fill=255);d.rectangle((21,10,23,19),fill=255)
    cutout(3,cactus).save(props/'cactus.png')
    palm=silhouette();d=ImageDraw.Draw(palm)
    d.line((16,13,16,30),fill=255,width=3)
    for pts in [[(16,13),(3,6),(1,10),(13,12)],[(16,13),(11,1),(14,1),(18,11)],
                [(16,13),(28,4),(31,8),(20,13)],[(16,13),(6,17),(4,20),(15,16)],
                [(16,13),(25,17),(28,21),(18,16)]]:d.polygon(pts,fill=255)
    cutout(28,palm).save(props/'palm.png')
    banner=silhouette();d=ImageDraw.Draw(banner)
    d.line((8,3,8,29),fill=255);d.polygon([(9,4),(23,4),(23,19),(16,23),(9,19)],fill=255)
    cutout(6,banner).save(props/'horde_banner.png')
    rock=silhouette();d=ImageDraw.Draw(rock)
    d.polygon([(8,14),(11,9),(18,8),(23,13),(22,21),(15,23),(9,21)],fill=255)
    cutout(37,rock).save(props/'boulder.png')
    campfire=silhouette();d=ImageDraw.Draw(campfire)
    d.rectangle((12,21,19,23),fill=255)
    d.polygon([(13,21),(12,16),(15,12),(17,16),(19,13),(20,19),(18,22)],fill=255)
    # Mask the reused watchtower timbers geometrically, including both legs.
    logs=silhouette();d=ImageDraw.Draw(logs)
    d.line((5,19,3,31),fill=255,width=2);d.line((26,19,28,31),fill=255,width=2)
    d.line((3,31,26,20),fill=255);d.line((6,20,28,31),fill=255)
    campfire.paste(logs.crop((0,24,32,32)),(0,24))
    cutout(39,campfire).save(props/'campfire.png')


def main():
    build_blocks();maps={name:build_map(name) for name in DIMS}
    checks={name:validate_map(name,data) for name,data in maps.items()}
    tiles=[];tile_indices={};meta=[];palette_ids=[]
    for block in BLOCKS:
        im,pal=block['im'],block['pal']
        for y in range(4):
            for x in range(4):
                pixels=im.crop((x*8,y*8,x*8+8,y*8+8)).tobytes();key=(pixels,pal)
                if key not in tile_indices:
                    tile_indices[key]=len(tiles);tiles.append(key);palette_ids.append(pal)
                i=tile_indices[key];meta.append(i if i<96 else 128+i-96)
    assert len(tiles)<=192, f'{len(tiles)} native tiles exceeds the 192-tile VRAM allocation'
    (OUT/'terrain').mkdir(parents=True,exist_ok=True);(OUT/'maps').mkdir(parents=True,exist_ok=True)
    sheet=Image.new('P',(128,96));sheet.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
    for i,(tile,_) in enumerate(tiles):
        for j,v in enumerate(tile):sheet.putpixel(((i%16)*8+j%8,(i//16)*8+j//8),v)
    sheet.save(ROOT/'gfx/tilesets/peon.png')
    (ROOT/'data/tilesets/peon_metatiles.bin').write_bytes(bytes(meta))
    (ROOT/'data/tilesets/peon_collision.asm').write_text(''.join(
        '\ttilecoll '+', '.join([b['collision']]*4)+f' ; {i:02x} {b["name"]}\n'
        for i,b in enumerate(BLOCKS)))
    mapped=[7]*256
    for i,pal in enumerate(palette_ids):mapped[i if i<96 else 128+i-96]=pal|(8 if i>=96 else 0)
    (ROOT/'gfx/tilesets/peon_palette_map.bin').write_bytes(bytes(mapped[i]|mapped[i+1]<<4 for i in range(0,256,2)))
    (ROOT/'gfx/tilesets/peon_bg.pal').write_text(palfile(BG))
    (ROOT/'gfx/tilesets/peon_regions.pal').write_text(''.join(palfile(pals) for pals in REGION_BGS.values()))
    for i,b in enumerate(BLOCKS):
        im=b['im'].copy();im.putpalette([v for c in BG[b['pal']] for v in c]+[0]*756)
        im.convert('RGB').save(OUT/'terrain'/f'{i:02d}_{b["name"]}.png')
    for name,data in maps.items():
        w,h=DIMS[name];pals=REGION_BGS.get(name,BG)
        (ROOT/f'maps/{name}.blk').write_bytes(bytes(data))
        canvas=Image.new('RGB',(w*32,h*32))
        for i,value in enumerate(data):
            block=BLOCKS[value];im=block['im'].copy()
            im.putpalette([v for c in pals[block['pal']] for v in c]+[0]*756)
            canvas.paste(im.convert('RGB'),((i%w)*32,(i//w)*32))
        canvas.save(OUT/'maps'/f'{name}.png')
        canvas.resize((w*64,h*64),Image.Resampling.NEAREST).save(OUT/'maps'/f'{name}_2x.png')
    transparent_exports()
    entrances={}
    for name,data in maps.items():
        w,_=DIMS[name]
        entrances[name]=[{'block':b,'block_xy':[i%w,i//w],
                          'door_tile':[i%w*2+1,i//w*2+1]}
                         for i,b in enumerate(data) if b in (4,29)]
    manifest={'native_tiles':len(tiles),'tile_budget':192,'block_count':len(BLOCKS),
              'source':'Native pixel-grid art; no rescaled conceptual map',
              'bg_palettes':BG,'region_palettes':REGION_BGS,'maps':checks,
              'hut_entrances':entrances,
              'campfire':{'map':'TheDen','block_xy':[6,3],'block_id':39,
                          'interaction_tile':[12,7],'approach_tile':[12,8],
                          'animation':'Static native fire; flames and crossed logs reuse existing tiles.'},
              'transparent_exports':'Explicit geometry masks preserve index-zero ivory highlights.',
              'blocks':[{'id':i,'name':b['name'],'palette':b['pal'],'collision':b['collision']} for i,b in enumerate(BLOCKS)],
              'limitations':['Map geography is compressed to the existing v0.2 map sizes.',
                             'Shared huts and inns are appended by build_peon_interiors.py; no Echo Isles traversal.',
                             'The Orgrimmar gate is a north landmark, not a new city map.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Compiled {len(tiles)}/192 tiles, {len(BLOCKS)} blocks and {len(maps)} connected maps.')


if __name__=='__main__':main()
