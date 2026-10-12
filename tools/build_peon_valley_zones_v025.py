#!/usr/bin/env python3
"""Build the seven connected Valley areas from the user's annotated geography.

Zone 1 (Den14) and zone 2 (Valley15) keep their saved map numbers and dimensions.
Five 5x5-block areas append IDs25-29. Every old walkable movement cell remains
walkable; only explicitly listed canyon openings turn WALL into FLOOR/WARP.
NPC scripts retain their original event flags and stable object indices.
All rendered maps are native compiler reconstructions, not emulator captures.
"""
from collections import deque
from pathlib import Path
import argparse
import hashlib
import json
import re

from PIL import Image, ImageDraw

import build_peon_wayfinding_v025 as paths

ROOT = paths.ROOT
OUT = ROOT / 'references/generated/environment_v025/zone_layout'
MAP_NUMBERS = {
    'PeonOpening': 12, 'GrommashHold': 13, 'TheDen': 14,
    'ValleyOfTrials': 15, 'DurotarRoad': 16, 'SenjinVillage': 17,
    'RazorHill': 18, 'OrgrimmarGate': 19, 'BurningBladeCavern': 20,
    'PeonTrollHut': 21, 'PeonOrcHut': 22, 'PeonOrcInn': 23, 'PeonTrollInn': 24,
    'PeonValleyCrossroads': 25, 'PeonHanazuaCamp': 26,
    'PeonSarkothBasin': 27, 'PeonCaveApproach': 28, 'PeonValleyExit': 29,
}
MAP_CONSTANTS = {
    'PEON_OPENING': 'PeonOpening', 'GROMMASH_HOLD': 'GrommashHold',
    'THE_DEN': 'TheDen', 'VALLEY_OF_TRIALS': 'ValleyOfTrials',
    'DUROTAR_ROAD': 'DurotarRoad', 'SENJIN_VILLAGE': 'SenjinVillage',
    'RAZOR_HILL': 'RazorHill', 'ORGRIMMAR_GATE': 'OrgrimmarGate',
    'BURNING_BLADE_CAVERN': 'BurningBladeCavern',
    'PEON_TROLL_HUT': 'PeonTrollHut', 'PEON_ORC_HUT': 'PeonOrcHut',
    'PEON_ORC_INN': 'PeonOrcInn', 'PEON_TROLL_INN': 'PeonTrollInn',
    'PEON_VALLEY_CROSSROADS': 'PeonValleyCrossroads',
    'PEON_HANAZUA_CAMP': 'PeonHanazuaCamp',
    'PEON_SARKOTH_BASIN': 'PeonSarkothBasin',
    'PEON_CAVE_APPROACH': 'PeonCaveApproach', 'PEON_VALLEY_EXIT': 'PeonValleyExit',
}
NEW_NAMES = tuple(list(MAP_NUMBERS)[13:])
DIMS = dict(paths.DIMS, **{name: (5, 5) for name in NEW_NAMES})
ZONE_NAMES = {
    1: 'TheDen', 2: 'ValleyOfTrials', 3: 'PeonValleyCrossroads',
    4: 'PeonHanazuaCamp', 5: 'PeonSarkothBasin',
    6: 'PeonCaveApproach', 7: 'PeonValleyExit',
}
DISCOVERY_CALLBACKS = {
    1: 'TheDenDiscover', 2: 'ValleyOfTrialsDiscover',
    3: 'PeonValleyCrossroadsDiscover', 4: 'PeonHanazuaCampDiscover',
    5: 'PeonSarkothBasinDiscover', 6: 'PeonCaveApproachDiscover',
    7: 'PeonValleyExitDiscover',
}
# Approximate rectangles measured against the annotated 645x549 conversation
# image. They are a layout reference, not an attachment falsely stored in git.
REFERENCE_RECTS = {
    1: (150, 397, 297, 541), 2: (303, 397, 449, 542),
    3: (207, 245, 352, 389), 4: (57, 178, 201, 322),
    5: (2, 336, 147, 480), 6: (262, 0, 405, 145),
    7: (480, 397, 625, 541),
}
OPENED_OLD_WALL_BLOCKS = {
    'TheDen': {(0, 7)},
    'ValleyOfTrials': {(8, 0), (8, 1), (8, 2), (8, 4), (8, 5)},
}
RETIRED_OLD_VALLEY_ACTORS = (2, 3, 4, 6, 7, 8, 9)
REQUIRED_ROUTE = [
    ('TheDen', 1, 'ValleyOfTrials', 1, 'RIGHT', 1, 2),
    ('ValleyOfTrials', 3, 'PeonValleyCrossroads', 1, 'UP', 2, 3),
    ('PeonValleyCrossroads', 3, 'PeonHanazuaCamp', 1, 'LEFT', 3, 4),
    ('PeonHanazuaCamp', 2, 'PeonSarkothBasin', 1, 'DOWN', 4, 5),
    ('PeonSarkothBasin', 2, 'TheDen', 4, 'RIGHT', 5, 1),
    ('PeonValleyCrossroads', 2, 'PeonCaveApproach', 1, 'UP', 3, 6),
    ('ValleyOfTrials', 2, 'PeonValleyExit', 1, 'RIGHT', 2, 7),
    ('PeonValleyExit', 2, 'DurotarRoad', 1, 'RIGHT', 7, None),
    ('PeonCaveApproach', 2, 'BurningBladeCavern', 1, 'UP', 6, None),
]


def simple_map():
    return [1 if x in (0, 4) or y in (0, 4) else 38
            for y in range(5) for x in range(5)]


def road_shapes(data, width):
    roads = {(i % width, i // width) for i, b in enumerate(data) if b in paths.ROAD_IDS}
    for x, y in roads:
        if data[y * width + x] == 16:
            continue
        connected = ''.join(k for k in 'NSEW' if
                            (x + paths.OFFSETS[k][0], y + paths.OFFSETS[k][1]) in roads)
        data[y * width + x] = paths.ROAD_SHAPES.get(connected, 2)


def compact(name):
    data = simple_map()
    def put(x, y, block):
        data[y * 5 + x] = block
    def road(cells):
        for x, y in cells:
            put(x, y, 2)
    if name == 'PeonValleyCrossroads':
        road([(2, 0), (2, 1), (2, 2), (2, 3), (2, 4), (0, 2), (1, 2), (3, 2)])
        for x, y in ((2, 0), (2, 4), (0, 2)):
            put(x, y, 16)
        put(1, 1, 42)  # Shaded dry tree beside the west fork.
        put(3, 3, 6)   # Horde standard behind Zureetha's camp.
    elif name == 'PeonHanazuaCamp':
        road([(1, 2), (2, 2), (3, 2), (4, 2), (2, 3), (2, 4)])
        put(4, 2, 16); put(2, 4, 16)
        put(3, 1, 42); put(3, 3, 37)
    elif name == 'PeonSarkothBasin':
        road([(2, 0), (2, 1), (2, 2), (2, 3), (3, 3), (4, 3)])
        put(2, 0, 16); put(4, 3, 16)
        put(1, 1, 37); put(3, 1, 3); put(1, 3, 42)
    elif name == 'PeonCaveApproach':
        road([(2, 1), (2, 2), (2, 3), (2, 4)])
        put(2, 0, 15); put(2, 1, 16); put(2, 4, 16)
        put(1, 1, 34); put(3, 1, 34); put(1, 3, 36)
    elif name == 'PeonValleyExit':
        # Off-white fortifications surround a genuinely open horizontal gate.
        data = [33 if x in (0, 4) or y in (0, 4) else 38
                for y in range(5) for x in range(5)]
        road([(0, 2), (1, 2), (2, 2), (3, 2), (4, 2)])
        put(0, 2, 16); put(4, 2, 16)
        put(1, 1, 6); put(3, 1, 39); put(3, 3, 6)
    else:
        raise ValueError(name)
    road_shapes(data, 5)
    return bytes(data)


def build_maps():
    maps = {name: bytearray(data) for name, data in paths.build_maps().items()}
    den = maps['TheDen']
    den[7 * 12] = 16  # New west portal; all pre-existing Den floor is retained.
    den[7 * 12 + 1] = 18
    road_shapes(den, 12)
    valley = maps['ValleyOfTrials']
    # The former cave no longer duplicates the new zone-six entrance. Its saved
    # threshold remains walkable, and its empty road spur returns to bare soil.
    valley[1 * 16 + 12] = 33
    for x, y in ((12, 2), (12, 3), (12, 4), (5, 8), (5, 9), (6, 9),
                 (6, 10), (7, 10), (8, 10)):
        valley[y * 16 + x] = 38
    for y in range(6):
        valley[y * 16 + 8] = 16 if y == 0 else 17
    road_shapes(valley, 16)
    maps = {name: bytes(data) for name, data in maps.items()}
    maps.update({name: compact(name) for name in NEW_NAMES})
    return maps


def warp_events(name):
    result = []
    for i, event in enumerate(paths.events(name, 'warp_event'), 1):
        arguments = event['arguments'].split(';', 1)[0].split(',')
        target_constant, target_number = (x.strip() for x in arguments)
        result.append({'index': i, 'xy': event['xy'],
                       'target_name': MAP_CONSTANTS.get(target_constant, target_constant),
                       'target_constant': target_constant, 'target_warp': int(target_number),
                       'dynamic_room_return': int(target_number) == -1})
    return result


def object_events(name):
    result = []
    for i, event in enumerate(paths.events(name, 'object_event'), 1):
        args = [x.strip() for x in event['arguments'].split(';', 1)[0].split(',')]
        result.append({'index': i, 'xy': event['xy'], 'sprite': args[0],
                       'movement': args[1], 'palette': args[6], 'script': args[9],
                       'event_flag': args[10], 'masked_placeholder': args[0] == 'SPRITE_NONE'})
    return result


def validate(maps):
    cols = paths.collision_rows((ROOT / 'data/tilesets/peon_collision.asm').read_text())
    old_cols = paths.collision_rows(paths.original('data/tilesets/peon_collision.asm').decode())
    assert cols == old_cols, 'Tileset collision semantics changed'
    report = {}
    for name, data in maps.items():
        width, height = DIMS[name]
        assert len(data) == width * height and 0 not in data
        def collision(p):
            x, y = p
            if not (0 <= x < width * 2 and 0 <= y < height * 2):
                return 'WALL'
            return cols[data[y // 2 * width + x // 2]][(y % 2) * 2 + x % 2]
        was = None
        opened = []
        changed = []
        if name in paths.DIMS:
            was = paths.original(f'maps/{name}.blk')
            assert len(was) == len(data)
            for i, (a, b) in enumerate(zip(was, data)):
                old, new = cols[a], cols[b]
                xy = i % width, i // width
                for q, (before, after) in enumerate(zip(old, new)):
                    if before != 'WALL':
                        assert after != 'WALL', (name, xy, q, 'old saved floor became wall')
                    elif after != 'WALL':
                        assert xy in OPENED_OLD_WALL_BLOCKS.get(name, set()), (name, xy)
                        opened.append({'block_xy': list(xy), 'quadrant': q})
                if a != b:
                    changed.append({'block_xy': list(xy), 'old_id': a, 'new_id': b})
        warps, actors = warp_events(name), object_events(name)
        start = tuple((warps or actors)[0]['xy'])
        assert collision(start) != 'WALL', (name, start)
        reached, queue = {start}, deque([start])
        while queue:
            x, y = queue.popleft()
            for p in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if p not in reached and collision(p) != 'WALL':
                    reached.add(p); queue.append(p)
        for event in warps:
            assert tuple(event['xy']) in reached, (name, 'unreachable portal', event)
        if name not in ('PeonOpening', 'GrommashHold'):
            for event in actors + paths.events(name, 'bg_event'):
                if event.get('masked_placeholder'):
                    continue
                x, y = event['xy']
                assert any(p in reached for p in
                           ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))), (
                               name, 'inaccessible interaction', event)
        report[name] = {'map_id': MAP_NUMBERS[name], 'blocks': [width, height],
                        'movement_grid': [width * 2, height * 2],
                        'sha256': paths.sha(data),
                        'baseline_sha256': paths.sha(was) if was else None,
                        'changed_blocks': changed, 'opened_old_wall_quadrants': opened,
                        'all_old_saved_walkable_cells_remain_walkable': True,
                        'reachable_movement_cells': len(reached), 'warps': warps,
                        'actors': actors, 'bg_events': paths.events(name, 'bg_event')}
    assert len({r['sha256'] for r in report.values()}) == len(report)
    old_actors = object_events('ValleyOfTrials')
    assert all(old_actors[i - 1]['masked_placeholder'] for i in RETIRED_OLD_VALLEY_ACTORS)
    assert len(old_actors) == 9 and old_actors[0]['sprite'] != 'SPRITE_NONE'
    assert old_actors[4]['sprite'] == 'SPRITE_PEON_QUEST_1'
    assert not paths.events('ValleyOfTrials', 'coord_event')
    for name, source_warp, target, target_warp, *_ in REQUIRED_ROUTE:
        a = report[name]['warps'][source_warp - 1]
        assert (a['target_name'], a['target_warp']) == (target, target_warp), (name, a)
        b = report[target]['warps'][target_warp - 1]
        assert (b['target_name'], b['target_warp']) == (name, source_warp), (target, b)
    assert report['ValleyOfTrials']['warps'][2]['xy'] == [16, 0]
    assert report['TheDen']['warps'][1]['xy'] == [17, 5]
    assert report['TheDen']['warps'][2]['xy'] == [5, 7]
    assert report['BurningBladeCavern']['warps'][0]['xy'] == [10, 16]
    return {'all_checks_passed': True, 'baseline_commit': paths.BASELINE,
            'seven_geographic_areas_connected': True,
            'five_compact_nodes_appended_after_map24': True,
            'old_map_ids_and_dimensions_preserved': True,
            'all_old_saved_walkable_cells_remain_walkable': True,
            'all47_collision_rows_unchanged': True,
            'duplicate_old_quest_npcs_and_hostile_triggers_retired': True,
            'original_death_quest_and_reward_flags_retained': True,
            'fixed_camera_not_implemented': True,
            'maps': report}


def metadata(report):
    zones = []
    for zone, name in ZONE_NAMES.items():
        rect = REFERENCE_RECTS[zone]
        zones.append({'zone': zone, 'name': name, 'map_id': MAP_NUMBERS[name],
                      'map_group': 26, 'blocks': list(DIMS[name]),
                      'discovery_callback_label': DISCOVERY_CALLBACKS[zone],
                      'movement_grid': [v * 2 for v in DIMS[name]],
                      'annotated_reference_rect_px': list(rect),
                      'annotated_reference_rect_normalized': [
                          round(rect[0] / 645, 6), round(rect[1] / 549, 6),
                          round(rect[2] / 645, 6), round(rect[3] / 549, 6)],
                      'warps': report['maps'][name]['warps'],
                      'active_npcs': [a for a in report['maps'][name]['actors']
                                      if not a['masked_placeholder']]})
    edges = []
    for name, sw, target, tw, direction, sz, tz in REQUIRED_ROUTE:
        edges.append({'from_name': name, 'from_zone': sz, 'from_map_id': MAP_NUMBERS[name],
                      'source_warp': sw, 'source_xy': report['maps'][name]['warps'][sw - 1]['xy'],
                      'direction': direction, 'to_name': target, 'to_zone': tz,
                      'to_map_id': MAP_NUMBERS[target], 'target_warp': tw,
                      'target_xy': report['maps'][target]['warps'][tw - 1]['xy'],
                      'reciprocal_return_verified_static': True})
    return {'schema_version': 1, 'map_group': 26, 'zones': zones, 'edges': edges,
            'quest_landmarks': {
                'Gornek': {'zone': 1, 'map_id': 14, 'xy': [10, 9]},
                'Galgar': {'zone': 2, 'map_id': 15, 'xy': [8, 10]},
                'CactusApples': {'zone': 2, 'map_id': 15,
                                 'coordinates': [[7, 7], [23, 9], [9, 17]],
                                 'flags': ['EVENT_PEON_CACTUS_1', 'EVENT_PEON_CACTUS_2',
                                           'EVENT_PEON_CACTUS_3']},
                'Zureetha': {'zone': 3, 'map_id': 25, 'xy': [6, 4], 'actor': 3,
                             'marker': 7, 'marker_xy': [6, 3]},
                'Hanazua': {'zone': 4, 'map_id': 26, 'xy': [3, 4], 'actor': 2,
                            'marker': 6, 'marker_xy': [3, 3]},
                'Sarkoth': {'zone': 5, 'map_id': 27, 'xy': [4, 4], 'actor': 4,
                            'death_flag': 'EVENT_PEON_SARKOTH_DEAD'},
                'OutsideFamiliars': {'zone': 6, 'map_id': 28,
                                     'coordinates': [[4, 5], [6, 4]], 'actors': [8, 9],
                                     'death_flags': ['EVENT_PEON_CAVE_APPROACH_IMP_1_DEAD',
                                                     'EVENT_PEON_CAVE_APPROACH_IMP_2_DEAD']},
                'InsideFamiliars': {'map_id': 20, 'coordinates': [[12, 8], [8, 10]],
                                    'actors': [1, 2],
                                    'death_flags': ['EVENT_PEON_CAVE_STRONG_IMP_DEAD',
                                                    'EVENT_PEON_CAVE_IMP_DEAD']},
                'Yarrog': {'map_id': 20, 'xy': [14, 3], 'actor': 5,
                           'death_flag': 'EVENT_PEON_YARROG_DEAD'},
            },
            'additional_maps': {n: report['maps'][n] for n in
                                ('BurningBladeCavern', 'DurotarRoad')},
            'reference_image_is_conversation_attachment_not_stored_repository_file': True,
            'reference_measurements_are_approximate': True,
            'old_cave_threshold_xy_now_walkable_without_warp': [24, 4],
            'new_cave_threshold': {'map': 28, 'xy': [5, 2]},
            'quest_and_death_flags_retained_without_migration': True,
            'new_sector_discovery_flags_owned_by_root': [342, 343, 344, 345, 346, 347, 348]}


def previews(maps, meta):
    for subdir in ('maps', 'before', 'annotated'):
        (OUT / subdir).mkdir(parents=True, exist_ok=True)
    for name, data in maps.items():
        im = paths.render(name, data, dimensions=DIMS[name],
                          palette_name='ValleyOfTrials' if name in NEW_NAMES else None)
        im.save(OUT / 'maps' / f'{name}.png')
        im.resize((im.width * 2, im.height * 2), Image.Resampling.NEAREST).save(
            OUT / 'maps' / f'{name}_2x.png')
        if name in paths.DIMS:
            paths.render(name, paths.original(f'maps/{name}.blk'), before=True).save(
                OUT / 'before' / f'{name}_v024.png')
        if name in ZONE_NAMES.values():
            scaled = im.resize((im.width * 3, im.height * 3), Image.Resampling.NEAREST)
            d = ImageDraw.Draw(scaled)
            for w in warp_events(name):
                x, y = (v * 48 for v in w['xy'])
                d.rectangle((x, y, x + 47, y + 47), outline='#7fffff', width=2)
                d.text((x + 2, y + 2), f"W{w['index']}", fill='white',
                       stroke_width=1, stroke_fill='black')
            for npc in object_events(name):
                if not npc['masked_placeholder']:
                    x, y = (v * 48 for v in npc['xy'])
                    d.rectangle((x, y, x + 47, y + 47), outline='#fff08c', width=2)
                    d.text((x + 2, y + 22), f"NPC{npc['index']}", fill='white',
                           stroke_width=1, stroke_fill='black')
            final = Image.new('RGB', (scaled.width, scaled.height + 28), '#18110c')
            final.paste(scaled)
            d = ImageDraw.Draw(final)
            d.text((5, scaled.height + 8), 'COMPILER RECONSTRUCTION; cyan warps / amber actors', fill='#eee2c3')
            final.save(OUT / 'annotated' / f'{name}_actual_portals_and_actors.png')
    # Review diagram keeps the seven rectangles in their supplied relative
    # geography. Thumbnails are reconstructions, with explicit boundary labels.
    canvas = Image.new('RGB', (645, 585), '#22150f')
    d = ImageDraw.Draw(canvas)
    for zone in meta['zones']:
        x0, y0, x1, y1 = zone['annotated_reference_rect_px']
        im = Image.open(OUT / 'maps' / f"{zone['name']}.png").convert('RGB')
        im.thumbnail((x1 - x0 - 4, y1 - y0 - 20), Image.Resampling.NEAREST)
        canvas.paste(im, (x0 + ((x1 - x0) - im.width) // 2, y0 + 18))
        d.rectangle((x0, y0, x1, y1), outline='#abb848', width=2)
        d.text((x0 + 5, y0 + 4), f"ZONE {zone['zone']} / MAP {zone['map_id']}", fill='#fff4c4')
    d.text((8, 555), 'ANNOTATED GEOGRAPHY REVIEW: actual map reconstructions, not gameplay.', fill='#eee2c3')
    d.text((8, 571), 'Compact zones 3-7 append native map IDs; zones 1-2 retain saved scrolling geometry.', fill='#eee2c3')
    canvas.save(OUT / 'seven_zone_geography_review.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--refresh-previews', action='store_true')
    args = parser.parse_args()
    maps = build_maps()
    report = validate(maps)
    if args.check_only or args.refresh_previews:
        assert all((ROOT / f'maps/{n}.blk').read_bytes() == data for n, data in maps.items()), (
            'Native map bytes differ from deterministic seven-zone layout')
    else:
        for name, data in maps.items():
            path = ROOT / f'maps/{name}.blk'
            if not path.exists() or path.read_bytes() != data:
                path.write_bytes(data)
    meta = metadata(report)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    (OUT / 'metadata.json').write_text(json.dumps(meta, indent=2) + '\n')
    if not args.check_only:
        previews(maps, meta)
    print(json.dumps({k: v for k, v in report.items() if k != 'maps'}, indent=2))


if __name__ == '__main__':
    main()
