#!/usr/bin/env python3
"""Import complete archived WORLD drawings into v19 source JSON cels only.

This is explicitly a lossy source-art import, not newly drawn native detail.
No engine, compiled gfx packet, original PNG, battle art or ROM is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation, find_objects, label

from peon_world_readability_profile_v0219 import PALETTES
from import_peon_world_actors_v0215 import decode, encode


ROOT = Path(__file__).resolve().parents[1]
DIRS = ('front', 'back', 'left', 'right')
MASTER = 'references/generated/durotar_v02/concept_overworld.png'
IMP_MASTER = 'references/generated/durotar_v02/concept_imp_and_gear.png'
ROSTER = 'references/generated/durotar_v022/enemies/concept_overworld_roster.png'
CANON = 'references/characters/peon_world_character_sheets_split'
BEASTS = ('boar', 'tiger', 'panther', 'raptor', 'felhunter', 'crawler')
MONSTERS = ('imp', 'scorpid', 'sarkoth')
OPTIONS = {
    'boar': ((3,), 3), 'tiger': ((3,), 3),
    'panther': ((1,), 1), 'raptor': ((2, 3, 7), 2),
    'felhunter': ((1, 5), 1), 'crawler': ((3, 5, 7), 3),
    'imp': ((3, 5, 7), 7), 'scorpid': ((3, 5, 7), 7),
    'sarkoth': ((3, 5, 7), 7),
}
IDENTITIES = {
    'boar': 'Complete old WORLD boar: sloped bristled back, pointed ears, two pale eyes, broad snout, projecting pale tusks, stocky body and hooves.',
    'tiger': 'Complete old WORLD tiger: low four-legged body, striped head/back, pale muzzle and paws, raised striped tail; no upright humanoid torso.',
    'panther': 'Explicit authorized dark-plum palette variant of the complete archived WORLD tiger geometry/poses; native green eye landmarks, charcoal contour and low-contrast dark fur. This is a derived panther variant, not recovered original panther artwork.',
    'raptor': 'Complete old WORLD raptor: elongated snout, narrow neck, bent forearms, separated hind claws and long balancing tail.',
    'felhunter': 'Complete old WORLD demonic hound: long pale muzzle, purple quadruped body, splayed sensory tendrils and separate clawed paws.',
    'crawler': 'Complete old WORLD coastal crab: pale shell, two large red pincers, small eyes and independently separated legs.',
    'imp': 'Complete old WORLD red imp: swept dark horns, pointed ears, gold eyes/claws, crouched limbs, folded wing hints and a curved arrow tail.',
    'scorpid': 'Complete old WORLD scorpid: red segmented shell, curled stinger, two pincers and splayed legs; exterior reaction glow is excluded.',
    'sarkoth': 'Complete old WORLD Sarkoth: larger segmented scorpid with curled stinger, substantial pincers, low head and spread legs.',
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_image(path: str) -> Image.Image:
    return Image.open(ROOT / path).convert('RGBA')


def alpha_bounds(image: Image.Image):
    return image.getchannel('A').point(lambda a: 255 if a >= 180 else 0).getbbox()


def major_components(image: Image.Image):
    values = np.asarray(image)
    lab, _ = label(values[..., 3] >= 180)
    result = []
    for number, region in enumerate(find_objects(lab), 1):
        if region is None:
            continue
        count = int(np.count_nonzero(lab[region] == number))
        if count > 1000:
            result.append((region[1].start, region[0].start,
                           region[1].stop, region[0].stop))
    return sorted(result, key=lambda b: (b[1], b[0]))


def roster_rows(image: Image.Image):
    occupied = (np.asarray(image)[..., 3] >= 180).any(1)
    spans, start = [], None
    for y, occupied_row in enumerate(list(occupied) + [False]):
        if occupied_row and start is None:
            start = y
        elif not occupied_row and start is not None:
            spans.append((start, y))
            start = None
    assert len(spans) == 9, spans
    return spans


def read_frame(path: str, box, halo: str | None = None):
    """Keep true source alpha; only discard verified exterior reaction hue."""
    image = source_image(path).crop(box)
    values = np.asarray(image).copy()
    mask = values[..., 3] >= 180
    rgb = values[..., :3].astype('float64')
    removed = np.zeros_like(mask)
    if halo:
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        if halo == 'yellow':
            possible = mask & (r + g >= 70) & (g >= r * .82) & (g > b * 1.8)
        else:
            possible = mask & (r >= 175) & (g < 55) & (b < 55) & (r > g * 3)
        # Only colour components reaching the genuine exterior alpha boundary
        # are a reaction glow. Detached interior eyes/tusks remain source pixels.
        exterior = np.pad(~mask, 1, constant_values=True)
        edge = binary_dilation(exterior, structure=np.ones((3, 3)))[1:-1, 1:-1]
        labels, count = label(possible, structure=np.ones((3, 3)))
        touching = set(int(n) for n in np.unique(labels[possible & edge]) if n)
        removed = np.isin(labels, list(touching)) if touching else removed
    retained = mask & ~removed
    stray = np.zeros_like(mask)
    if halo:
        labels, count = label(retained)
        sizes = np.bincount(labels.ravel())
        sizes[0] = 0
        principal = labels == int(sizes.argmax())
        # Isolated halo flecks are not anatomy. Reject an extraction that would
        # discard meaningful detached source equipment or body parts.
        stray = retained & ~principal
        assert int(stray.sum()) <= max(80, int(mask.sum() * .01)), (path, box, 'Unexpected detached anatomy', int(stray.sum()))
        retained = principal
    values[..., 3] = np.where(retained, 255, 0)
    ys, xs = np.where(retained)
    local = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    cleaned = Image.fromarray(values).crop(local)
    return cleaned, {
        'source_path': path, 'source_sha256': sha((ROOT / path).read_bytes()),
        'source_canvas': list(source_image(path).size), 'source_crop': list(box),
        'clean_component_local_bbox': list(local),
        'actual_source_alpha_used': True, 'background_flood_fill_used': False,
        'alpha_threshold': 180, 'original_opaque_pixels': int(mask.sum()),
        'exterior_halo_hue': halo, 'exterior_halo_pixels_removed': int(removed.sum()),
        'isolated_halo_fleck_pixels_removed': int(stray.sum()),
        'retained_body_pixels': int(retained.sum()), 'clean_dimensions': list(cleaned.size),
    }


def nearest_canvas(image: Image.Image, maximum: int):
    copy = image.copy()
    copy.thumbnail((maximum, maximum), Image.Resampling.NEAREST)
    canvas = Image.new('RGBA', (24, 24))
    offset = ((24 - copy.width) // 2, 24 - copy.height)
    canvas.paste(copy, offset)
    return canvas, {
        'sampling': 'NEAREST, standard center phase(0,0), no smoothing or averaging',
        'nearest_phase_native_px': [0, 0], 'body_dimensions': list(copy.size),
        'target_canvas': [24, 24], 'target_offset': list(offset),
        'opaque_bbox': canvas.getchannel('A').getbbox(),
    }


def panther_palette_variant(image: Image.Image):
    """Recolour the existing complete cat; never draw, erase or move anatomy."""
    values = np.asarray(image).copy()
    source_rgb = values[..., :3].astype('int32')
    r, g, b = source_rgb[..., 0], source_rgb[..., 1], source_rgb[..., 2]
    opaque = values[..., 3] > 0
    eye = opaque & (r >= 130) & (g >= 100) & (g >= r * .8) & (b < g * .7)
    dark = opaque & (source_rgb.max(2) <= 70)
    palette = np.asarray(PALETTES[1], dtype='uint8')
    palette = (palette << 3) | (palette >> 2)
    values[opaque, :3] = palette[2]
    values[dark, :3] = palette[3]
    values[eye, :3] = palette[1]
    assert np.array_equal(values[..., 3], np.asarray(image)[..., 3])
    return Image.fromarray(values), {
        'derived_variant_of': 'Complete archived tiger WORLD source, including its actual source step',
        'palette_substitution_only': True, 'geometry_and_alpha_unchanged': True,
        'recovered_original_panther': False, 'native_pixel_anatomy_drawn': False,
        'source_colour_rule': 'Original near-black(maxRGB<=70) remains charcoal; remaining existing fur/muzzle becomes plum; only actual original yellow eye pixels(g>=.8r,b<.7g) become native green.',
        'source_eye_colour_pixels': int(eye.sum()), 'source_charcoal_pixels': int(dark.sum()),
    }


def fit_group(frames, role):
    """Use stable per-view attributes for idle and the real source step."""
    candidates, default = OPTIONS[role]
    source = [np.asarray(frame) for frame in frames]
    indices = [np.zeros((24, 24), dtype='uint8') for frame in frames]
    attrs, scores = [], []
    for y in range(0, 24, 8):
        for x in range(0, 24, 8):
            local_candidates = candidates
            material_guard = None
            source_colors = np.concatenate([
                data[y:y+8, x:x+8, :3].reshape(-1, 3)
                for data in source
            ]).astype('int32') >> 3
            source_opaque = np.concatenate([
                (data[y:y+8, x:x+8, 3] > 0).reshape(-1)
                for data in source
            ])
            red = source_opaque & (source_colors[:, 0] > source_colors[:, 1] * 2.2) & (source_colors[:, 0] > 10)
            if role in ('felhunter', 'panther'):
                purple = source_opaque & (source_colors[:, 2] > source_colors[:, 1] + 1) & (source_colors[:, 0] >= source_colors[:, 1]) & (source_colors.max(1) >= 5)
                pale = source_opaque & (source_colors.min(1) >= 12) & (source_colors.max(1) - source_colors.min(1) < 8)
                if purple.any() and (role == 'panther' or int(pale.sum()) < 3):
                    local_candidates = (1,)
                    material_guard = 'Existing source-purple fill retains purple; two darkest source levels remain ink. Pale hound muzzle may use palette5.'
            elif role == 'raptor':
                green = source_opaque & (source_colors[:, 1] >= source_colors[:, 0]) & (source_colors[:, 1] > source_colors[:, 2] + 2) & (source_colors[:, 1] > 8)
                if green.any():
                    local_candidates = (2,)
                    material_guard = 'Existing olive/green source skin stays in native green/brown material family2.'
            elif role == 'crawler' and int(red.sum()) < 3:
                local_candidates = (3,)
                material_guard = 'Pale/tan shell cannot borrow fire-yellow; palette7 is available only where real red source claws occur.'
            choices = {}
            distances = {}
            for palette_id in local_candidates:
                palette = np.asarray(PALETTES[palette_id][1:], dtype='int32')
                total, per_frame = 0., []
                pc = palette * 31 / np.maximum(palette.max(1, keepdims=True), 1)
                for data in source:
                    colors = data[y:y+8, x:x+8, :3].astype('int32') >> 3
                    opaque = data[y:y+8, x:x+8, 3] > 0
                    dist = ((colors[..., None, :] - palette) ** 2).sum(3)
                    chroma = colors * 31 / np.maximum(colors.max(2, keepdims=True), 1)
                    hue = ((chroma[..., None, :] - pc) ** 2).sum(3)
                    hue[..., 2] = 0
                    dist = dist + hue * np.where(colors.sum(2) > 10, 1., 0.)[..., None]
                    if palette_id == 1 and role in ('felhunter', 'panther'):
                        purple = opaque & (colors[..., 2] > colors[..., 1] + 1) & (colors[..., 0] >= colors[..., 1]) & (colors.max(2) >= 5)
                        # Pure RGB error would turn dim purple fur into a black
                        # slab. Retain the source's actual coloured fill while
                        # its two darkest levels remain the contour/shadow ink.
                        dist[..., 0][purple] += 100000
                        dist[..., 2][purple] += 100000
                    weight = np.where(colors.sum(2) < 20, 2, 1)
                    total += float((dist.min(2) * weight)[opaque].sum())
                    per_frame.append(dist)
                choices[palette_id], distances[palette_id] = total, per_frame
            chosen = min(local_candidates, key=lambda p: (choices[p], p != default, p))
            attrs.append(chosen)
            scores.append({'tile': len(attrs)-1, 'palette': chosen,
                           'material_candidates': list(local_candidates),
                           'source_material_guard': material_guard,
                           'RGB555_plus_hue_outline_weighted_error': choices[chosen],
                           'candidate_errors': choices})
            for number, data in enumerate(source):
                local = (distances[chosen][number].argmin(2) + 1).astype('uint8')
                local[data[y:y+8, x:x+8, 3] == 0] = 0
                indices[number][y:y+8, x:x+8] = local
    return indices, attrs, scores


def render(indices, attrs):
    result = np.zeros((24, 24, 4), dtype='uint8')
    for tile, palette_id in enumerate(attrs):
        y, x = divmod(tile, 3)
        local = indices[y*8:y*8+8, x*8:x*8+8]
        palette = np.asarray(PALETTES[palette_id], dtype='uint8')
        palette = (palette << 3) | (palette >> 2)
        result[y*8:y*8+8, x*8:x*8+8, :3] = palette[local]
        result[y*8:y*8+8, x*8:x*8+8, 3] = np.where(local, 255, 0)
    return Image.fromarray(result)


def rows(indices):
    return [''.join('.123'[int(value)] for value in row) for row in indices]


def source_specs():
    world = source_image(MASTER)
    components = major_components(world)
    assert len(components) == 36
    boar = sorted([box for box in components if 1180 <= box[1] < 1250], key=lambda b: b[0])
    scorpid = sorted([box for box in components if 1340 <= box[1] < 1390], key=lambda b: b[0])
    imp = sorted([box for box in major_components(source_image(IMP_MASTER)) if box[1] < 360], key=lambda b: b[0])
    assert len(boar) == len(scorpid) == len(imp) == 4
    result = {}
    for role, path, boxes, halo in [('boar', MASTER, boar, 'yellow'),
                                    ('scorpid', MASTER, scorpid, 'red'),
                                    ('imp', IMP_MASTER, imp, None)]:
        result[role] = {direction: [(path, box, halo, False)]
                        for direction, box in zip(DIRS, boxes)}
    image = source_image(ROSTER)
    spans = roster_rows(image)
    for role, row in [('tiger', 0), ('raptor', 1), ('crawler', 2), ('felhunter', 4), ('sarkoth', 7)]:
        views = {}
        for direction, column in [('front', 0), ('back', 1), ('left', 2), ('right', 2)]:
            views[direction] = []
            for offset in (0, 3):
                col = column + offset
                cell = (round(col * image.width / 6), spans[row][0],
                        round((col+1) * image.width / 6), spans[row][1])
                local = alpha_bounds(image.crop(cell))
                box = (cell[0]+local[0], cell[1]+local[1], cell[0]+local[2], cell[1]+local[3])
                views[direction].append((ROSTER, box, None, direction == 'right'))
        result[role] = views
    result['panther'] = result['tiger']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'assets/world_readability_v0219')
    parser.add_argument('--review', type=Path, default=ROOT / 'references/generated/world_readability_v0219/world_master_sources')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    args.review.mkdir(parents=True, exist_ok=True)
    specs = source_specs()
    hashes = {path: sha((ROOT / path).read_bytes()) for views in specs.values()
              for frames in views.values() for path, box, halo, mirrored in frames}
    panther_canonical = [f'{CANON}/panther/panther_world_{direction}.png' for direction in DIRS]
    hashes.update({path: sha((ROOT / path).read_bytes()) for path in panther_canonical})
    roles, native_views, source_views = {}, {}, {}
    report = {
        'version': 'v0.2.19', 'operation': 'Complete WORLD illustration import, lossy native24 conversion',
        'new_detail_generated': False, 'new_anatomy_authored': False,
        'source_originals_unchanged': True, 'source_sha256': hashes,
        'palette3_RGB555_required_by_root': PALETTES[3],
        'unmodified_ABI': '24px / nine8px tiles /144B per frame;12frames1728B, masks24B, attributes108B',
        'ROM_built_or_emulator_tested': False, 'roles': {},
    }
    for role in BEASTS + MONSTERS:
        native_views[role], source_views[role] = {}, {}
        art = {'references': sorted(set(frame[0] for frames in specs[role].values() for frame in frames)),
               'identity': IDENTITIES[role], 'palette': OPTIONS[role][1], 'views': {}, 'attributes': {}}
        if role == 'panther':
            art['references'] += panther_canonical
        walks, provenance = {}, {}
        folder = args.review / role
        folder.mkdir(exist_ok=True)
        for direction in DIRS:
            canvases, records, originals = [], [], []
            for path, box, halo, mirrored in specs[role][direction]:
                image, record = read_frame(path, box, halo)
                if mirrored:
                    image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                image.save(folder / f'{direction}_source_pose{len(canvases)}.png')
                originals.append(image)
                if role == 'panther':
                    image, variant = panther_palette_variant(image)
                    record['authorized_derived_palette_variant'] = variant
                    image.save(folder / f'{direction}_derived_plum_source_pose{len(canvases)}.png')
                canvas, geometry = nearest_canvas(image, 24 if role == 'boar' else 23)
                canvases.append(canvas)
                records.append({**record, **geometry, 'mirror_source_left': mirrored,
                                'mirror_reason': 'Atlas has only front/back/left source views' if mirrored else None})
            indices, attrs, tile_scores = fit_group(canvases, role)
            art['views'][direction] = rows(indices[0])
            art['attributes'][direction] = attrs
            if len(indices) == 2:
                # Only one independently illustrated source step exists. Reuse
                # it at both gait addresses; do not manufacture a second gait.
                walks[direction] = [rows(indices[1]), rows(indices[1])]
            statistics = []
            for number, (frame, canvas, record) in enumerate(zip(indices, canvases, records)):
                shown = render(frame, attrs)
                assert np.array_equal(np.asarray(shown)[..., 3], np.asarray(canvas)[..., 3])
                packet = encode(Image.fromarray(frame))
                assert len(packet) == 144
                assert np.array_equal(np.asarray(decode(packet, 24)), frame)
                shown.save(folder / f'{direction}_native_pose{number}.png')
                canvas.save(folder / f'{direction}_nearest_before_palette_pose{number}.png')
                opaque = np.asarray(canvas)[..., 3] > 0
                error = (np.asarray(shown)[..., :3].astype(float) - np.asarray(canvas)[..., :3])[opaque]
                statistics.append({**record, 'native_opaque_pixels': int(opaque.sum()),
                                   'RGBA_alpha_exact_after_palette_fit': True,
                                   'RGB_MSE_per_channel': float((error ** 2).mean()),
                                   'native_2bpp_roundtrip_exact': True,
                                   'native_frame_bytes': len(packet),
                                   'native_2bpp_sha256': sha(packet)})
                if role == 'boar' and direction == 'front' and number == 0:
                    original = np.asarray(originals[0])
                    white = (original[..., 3] > 0) & (original[..., :3].min(2) > 170)
                    components, _ = label(white)
                    # Label sampling uses exactly the same nearest grid as the
                    # image: no pixel is manually promoted to an eye highlight.
                    labels = Image.fromarray(components.astype('int32')).resize(tuple(record['body_dimensions']), Image.Resampling.NEAREST)
                    canvas_labels = Image.new('I', (24, 24))
                    canvas_labels.paste(labels, tuple(record['target_offset']))
                    sampled = np.asarray(canvas_labels)
                    landmarks = []
                    for component, bounds in enumerate(find_objects(components), 1):
                        if bounds is None:
                            continue
                        box = [bounds[1].start, bounds[0].start, bounds[1].stop, bounds[0].stop]
                        eye = box[2]-box[0] < 8 and box[3]-box[1] < 15
                        landmarks.append({'source_component': component,
                                          'feature': 'eye white' if eye else 'pale tusk',
                                          'source_component_bbox': box,
                                          'native_source_samples': int(np.count_nonzero(sampled == component)),
                                          'native_ivory_pixels': int(np.count_nonzero((sampled == component) & (frame == 1)))})
                    eyes = [item for item in landmarks if item['feature'] == 'eye white']
                    assert len(eyes) == 2 and all(item['native_ivory_pixels'] >= 1 for item in eyes), landmarks
                    statistics[-1]['direct_source_bright_landmarks'] = landmarks
                    statistics[-1]['both_source_eye_whites_preserved_without_drawing'] = True
            native_views[role][direction] = render(indices[0], attrs)
            source_views[role][direction] = originals[0]
            provenance[direction] = {'frames': statistics, 'palette_attributes': attrs,
                                     'palette_fit': tile_scores,
                                     'source_frame_count': len(indices)}
        if walks:
            art['walk'] = walks
        provenance['method'] = 'Complete existing source-alpha crop; nearest point samples; existing per8x8 material palette fit with hue/outline weights; no newly drawn pixels'
        provenance['new_detail_generated'] = False
        provenance['new_anatomy_authored'] = False
        provenance['native_gait'] = ('One real source step repeated at both gait addresses; no invented second step' if walks else 'No animated WORLD source exists; repeat the still at all three pose addresses')
        provenance['limitation'] = ('Only small canonical panther WORLD sources exist. Explicitly authorized tiger-source palette variant supplies coherent complete cat anatomy; it is not an extraction/recovery of original panther pixels. Four canonical16 originals are archived unchanged alongside this review.' if role == 'panther' else 'Explicitly lossy RGB555 palette and24px sampling of the archived WORLD artwork')
        if role == 'panther':
            provenance['derived_native_palette_variant'] = True
            provenance['canonical_originals_preserved'] = {path: hashes[path] for path in panther_canonical}
            for direction, path in zip(DIRS, panther_canonical):
                (folder / f'canonical_original16_{direction}.png').write_bytes((ROOT / path).read_bytes())
        art['provenance'] = provenance
        roles[role] = art
        report['roles'][role] = provenance
    for filename, names in [('beasts.json', BEASTS), ('monsters_base.json', MONSTERS)]:
        packet = {'version': 'v0.2.19',
                  'authoring': 'Complete existing WORLD source-art conversion; no newly drawn native anatomy or invented gait',
                  'roles': {role: roles[role] for role in names}}
        (args.output / filename).write_text(json.dumps(packet, indent=2) + '\n')
    (args.output / 'beasts_monsters_source_provenance.json').write_text(json.dumps(report, indent=2) + '\n')
    # All nine families, four facings, both native1x and4x are visible at once.
    contact = Image.new('RGB', (4*230, len(roles)*160), (220, 211, 190))
    draw = ImageDraw.Draw(contact)
    sources = Image.new('RGB', contact.size, (220, 211, 190))
    source_draw = ImageDraw.Draw(sources)
    for row, role in enumerate(roles):
        for col, direction in enumerate(DIRS):
            x, y = col*230, row*160
            draw.text((x+5, y+5), role+' '+direction, fill='black')
            pic = native_views[role][direction]
            contact.paste(pic, (x+8, y+35), pic)
            big = pic.resize((96, 96), Image.Resampling.NEAREST)
            contact.paste(big, (x+65, y+35), big)
            source_draw.text((x+5, y+5), role+' '+direction+' source', fill='black')
            old = source_views[role][direction].copy()
            old.thumbnail((125, 125), Image.Resampling.NEAREST)
            sources.paste(old, (x+45, y+25), old)
    contact.save(args.review / 'all_native_1x_4x.png')
    sources.save(args.review / 'all_source_crops.png')
    (args.review / 'source_import_report.json').write_text(json.dumps(report, indent=2) + '\n')
    assert all(sha((ROOT / path).read_bytes()) == expected for path, expected in hashes.items())
    assert all(len(cel) == 24 and all(len(row) == 24 and set(row) <= set('.123') for row in cel)
               for art in roles.values() for cel in art['views'].values())
    for direction in DIRS:
        tiger = np.array([[cell != '.' for cell in row] for row in roles['tiger']['views'][direction]])
        panther = np.array([[cell != '.' for cell in row] for row in roles['panther']['views'][direction]])
        assert np.array_equal(tiger, panther), ('Derived panther changed cat anatomy', direction)
    print(json.dumps({'status': 'PASS source conversion only', 'roles': len(roles),
                      'directions': len(roles)*4, 'source_PNGs_unchanged': len(hashes),
                      'source_true_step_roles': sorted(role for role in roles if 'walk' in roles[role]),
                      'new_detail_generated': False, 'ROM_built': False}))


if __name__ == '__main__':
    main()
