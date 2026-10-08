#!/usr/bin/env python3
"""Retain the native idle and author two pixel poses for the apprentice backpic.

The original back.png is an immutable input. Native images use indexed DMG
grayscale; exported PNG/APNG sprites use the existing RGB555 battle palette
with binary transparency. Each 48x48 frame is 36 column-major Game Boy tiles.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'gfx/pokemon/machop/back.png'
NATIVE = ROOT / 'gfx/peon_player_battle'
OUT = ROOT / 'references/generated/durotar_v023/player_combat'
NAMES = ['idle', 'brace', 'swing']


def rgb555_palette():
    binary = (ROOT / 'gfx/pokemon/machop/normal.gbcpal').read_bytes()
    words = [int.from_bytes(binary[i:i+2], 'little') for i in range(0,8,2)]
    return [[word & 31, word >> 5 & 31, word >> 10 & 31] for word in words]


def original_native_indices():
    source = Image.open(SOURCE).convert('RGB')
    rgb = np.asarray(source).astype('int16') >> 3
    palette = np.asarray(rgb555_palette()).astype('int16')
    distances = ((rgb[:, :, None, :] - palette[None, None, :, :]) ** 2).sum(axis=3)
    return Image.fromarray(distances.argmin(axis=2).astype('uint8'), 'P')


def move_region(image, source, box, delta):
    x1,y1,x2,y2 = box
    image.paste(0, box)
    image.paste(source.crop(box), (x1+delta[0],y1+delta[1]))


def draw_mace(draw, hand, tip):
    hx,hy = hand; tx,ty = tip
    draw.line((hx,hy,tx,ty), fill=3, width=4)
    draw.line((hx,hy,tx,ty), fill=2, width=2)
    # Rough wood head, an intentionally humble tool rather than heroic steel.
    draw.polygon([(tx-3,ty-4),(tx+2,ty-5),(tx+4,ty-2),(tx+4,ty+2),
                  (tx+1,ty+4),(tx-3,ty+3),(tx-4,ty)], fill=3)
    draw.polygon([(tx-2,ty-3),(tx+1,ty-4),(tx+3,ty-1),
                  (tx+2,ty+2),(tx,ty+3),(tx-2,ty+1)], fill=2)
    draw.line((tx-1,ty-2,tx+1,ty), fill=1)
    draw.point((tx+1,ty+2), fill=3)
    draw.point((tx-3,ty), fill=1)


def authored_pose(idle, swing=False):
    pose = idle.copy()
    draw = ImageDraw.Draw(pose)
    # Remove the old raised mace/left forearm while retaining boots and body.
    draw.rectangle((0,0,13,35), fill=0)
    draw.rectangle((13,22,17,34), fill=0)
    # A slight lean follows the left shoulder. Legs remain exactly anchored.
    move_region(pose, idle, (14,4,40,21), (-1,0 if swing else -1))
    # Shield moves with the braced/rotating shoulder, preserving its native art.
    move_region(pose, idle, (34,20,48,41), (-2,1 if swing else -1))
    draw = ImageDraw.Draw(pose)
    # Rebuild the vest edge beneath the moved shield; green muscle stays bare.
    draw.line((32,21,32,31), fill=3, width=2)
    draw.line((30,22,31,30), fill=2, width=2)
    if swing:
        # Left arm extends into the follow-through; the wooden mace is low.
        draw.polygon([(18,23),(15,23),(12,24),(8,23),(5,24),(4,27),
                      (7,29),(12,29),(16,31),(19,29)], fill=3)
        draw.polygon([(17,24),(14,25),(11,26),(7,25),(6,27),
                      (10,28),(14,28),(17,29),(18,27)], fill=1)
        draw.line((13,28,16,30), fill=2)
        draw_mace(draw, (7,27), (4,37))
        draw.polygon([(5,25),(8,24),(10,26),(8,28),(5,28)], fill=3)
        draw.polygon([(6,25),(8,25),(9,26),(7,27),(6,27)], fill=1)
        # Torso rotation changes the tunic fold and diagonal shoulder seam.
        draw.line((20,22,27,26), fill=3, width=2)
        draw.line((20,23,25,26), fill=2)
        draw.line((22,28,29,30), fill=3)
    else:
        # Left hand lifts toward the cast, with a visible bent elbow.
        draw.polygon([(18,23),(15,23),(12,21),(10,18),(7,17),(5,19),
                      (6,23),(12,29),(17,31),(19,28)], fill=3)
        draw.polygon([(17,24),(14,24),(11,22),(9,19),(7,19),(7,22),
                      (13,27),(17,29),(18,27)], fill=1)
        draw.line((13,27,16,30), fill=2)
        draw_mace(draw, (8,20), (6,6))
        draw.polygon([(6,17),(9,17),(11,20),(10,23),(7,23),(5,20)], fill=3)
        draw.polygon([(7,18),(9,18),(10,20),(9,22),(7,21)], fill=1)
        draw.line((21,22,28,24), fill=3)
        draw.line((20,25,22,30), fill=2)
    return pose


def bpp_column_major(image):
    native = bytearray()
    for tx in range(6):
        for ty in range(6):
            for y in range(8):
                values = [image.getpixel((tx*8+x,ty*8+y)) for x in range(8)]
                native.extend((sum((v & 1) << (7-x) for x,v in enumerate(values)),
                               sum((v >> 1) << (7-x) for x,v in enumerate(values))))
    assert len(native) == 576
    return bytes(native)


def transparent(image, palette):
    values = np.asarray(image)
    result = np.zeros((48,48,4), dtype='uint8')
    for index in (1,2,3):
        result[values == index,:3] = [n << 3 for n in palette[index]]
        result[values == index,3] = 255
    return Image.fromarray(result, 'RGBA')


def main():
    NATIVE.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    palette = rgb555_palette()
    idle = original_native_indices()
    frames = [idle, authored_pose(idle), authored_pose(idle,swing=True)]
    binaries = [bpp_column_major(frame) for frame in frames]
    original_binary = ROOT / 'gfx/pokemon/machop/back.2bpp'
    if original_binary.exists():
        assert binaries[0] == original_binary.read_bytes(), 'Idle native tiles differ from current backpic'
    public = []
    metrics = []
    for index,(name,frame,binary) in enumerate(zip(NAMES,frames,binaries)):
        internal = frame.copy()
        internal.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
        internal.save(NATIVE / ('back_' + name + '.png'))
        (NATIVE / ('back_' + name + '.2bpp')).write_bytes(binary)
        rgba = transparent(frame,palette); public.append(rgba)
        rgba.save(OUT / ('peon_back_' + name + '_48x48.png'))
        rgba.resize((384,384),Image.Resampling.NEAREST).save(OUT / ('peon_back_' + name + '_8x.png'))
        metrics.append({'name':name,'changed_pixels_from_idle':int(np.count_nonzero(
            np.asarray(frame) != np.asarray(idle))),
                        'changed_silhouette_pixels':int(np.count_nonzero(
                            (np.asarray(frame) != 0) != (np.asarray(idle) != 0))),
                        'tile_bytes':len(binary),'frame_offset':index*576})
    (NATIVE / 'back_frames.2bpp').write_bytes(b''.join(binaries))
    (NATIVE / 'back_frames.gbcpal').write_bytes((ROOT / 'gfx/pokemon/machop/normal.gbcpal').read_bytes())
    sheet = Image.new('RGBA',(144,48))
    for i,frame in enumerate(public): sheet.paste(frame,(i*48,0))
    sheet.save(OUT/'peon_back_three_pose_sheet_144x48.png')
    sheet_large = sheet.resize((1152,384),Image.Resampling.NEAREST)
    sheet_large.save(OUT/'peon_back_three_pose_sheet_8x.png')
    display = Image.new('RGB',sheet_large.size,(245,237,213))
    display.paste(sheet_large,mask=sheet_large.getchannel('A'))
    display.save(OUT/'peon_back_three_pose_sheet_display_8x.png')
    # Prep/strike recover through the brace and return to the unchanged idle.
    sequence = [public[i] for i in [0,1,2,1,0]]
    durations = [320,160,160,120,320]
    sequence[0].save(OUT/'peon_back_three_pose_preview.apng',save_all=True,
                     append_images=sequence[1:],duration=durations,loop=0,disposal=1,blend=0)
    large = [f.resize((384,384),Image.Resampling.NEAREST) for f in sequence]
    large[0].save(OUT/'peon_back_three_pose_preview_8x.apng',save_all=True,
                  append_images=large[1:],duration=durations,loop=0,disposal=1,blend=0)
    # GIF has a solid presentation canvas; native PNG/APNG exports keep alpha.
    canvases=[]
    for frame in large:
        canvas=Image.new('RGB',(384,384),(245,237,213));canvas.paste(frame,mask=frame.getchannel('A'))
        canvases.append(canvas)
    canvases[0].save(OUT/'peon_back_three_pose_preview_8x.gif',save_all=True,
                     append_images=canvases[1:],duration=durations,loop=0)
    manifest={'source':'gfx/pokemon/machop/back.png',
              'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'native_binary':'gfx/peon_player_battle/back_frames.2bpp',
              'size':[48,48],'frames':metrics,'bytes_per_frame':576,'tile_order':'column-major, tx outer then ty',
              'total_bytes':1728,'rgb555_palette':palette,'alpha':'binary transparent index0',
              'idle_matches_current_backpic':True,
              'notes':'Original authored arm/mace/torso poses; fixed leg baseline; no engine or balance changes.'}
    (OUT/'asset_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'README.md').write_text('# Peon rear combat poses — v0.2.3\n\n'
        'Idle, brace/casting preparation, and physical mace follow-through. '
        'The existing 48×48 idle and equipment are retained; the new poses change '
        'the left arm, mace, shield position and tunic folds while anchoring the feet.\n\n'
        'Native transparent PNGs use three opaque RGB555 colours plus transparency. '
        'The APNG keeps transparency; the GIF uses a presentation canvas.\n\n'
        '`gfx/peon_player_battle/back_frames.2bpp` stores three contiguous frames, '
        '576 bytes each, each with 36 column-major tiles. Frame offsets: 0, 576, 1152. '
        'The matching 8-byte `back_frames.gbcpal` is the unchanged current native '
        'battle palette. Internal PNGs are indexed DMG grayscale, not public art.\n\n'
        'Rebuild assets with `python tools/build_peon_player_combat.py`. Engine '
        'integration and real battle captures are a separate step.\n\n'
        'The separate `peon_back_pose_concept_original.png` is an image-generated '
        'concept reference. It is not native ROM artwork and does not provide the '
        'engine palette or frame data. Native frames preserve the equipped-hand '
        'orientation and are generated deterministically from the retained idle.\n')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
