#!/usr/bin/env python3
"""Run the complete ordinary-button world checks against v0.2.17 packets.

The v0.2.16 checks already verify compiled native packet bytes, transparent
tile masks, per-cell palettes, actual VRAM, whole-body OAM admission, native
quest markers, three classes and captured hero LCD pixels. Reuse those
assertions with an explicit v0.2.17 import contract instead of duplicating
the emulator harness or weakening its coverage.
"""
from pathlib import Path
import hashlib
import json
import sys

import validate_peon_world_actors_v0216 as checks
from validate_peon_merchants_v0217 import check_world_palettes


class WorldActorSessionV0217(checks.WorldActorSession):
    def __init__(self, *args):
        self.renderer_hook_errors = []
        super().__init__(*args)

    def renderer_finish(self, context):
        try:
            if self.renderer_start is not None and self.read('hUsedSpriteIndex') == [0]:
                assert self.read('wScriptMode') != [0], 'Empty world body outside a native dialogue'
                assert self.read('hObjectStructIndex') == [self.renderer_start[1]]
                self.renderer_start = None
                return
            super().renderer_finish(context)
        except Exception as error:
            # PyBoy swallows callback exceptions. Preserve failures for the
            # next ordinary observation instead of silently passing them.
            self.renderer_hook_errors.append(repr(error))
            self.renderer_start = None

    def scene(self, *args, **kwargs):
        assert not self.renderer_hook_errors, self.renderer_hook_errors
        check_world_palettes(self)
        return super().scene(*args, **kwargs)


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    checks.ART_ROOT = root / 'references/generated/world_redraw_v0217'
    checks.ASSET_MANIFEST = root / 'gfx/world_redraw_v0217/manifest.json'
    checks.GRAPHICS = root / 'gfx/world_redraw_v0217/graphics.asm'
    checks.WorldActorSession = WorldActorSessionV0217
    if '--report-version' not in sys.argv:
        sys.argv.extend(('--report-version', 'v0.2.17'))
    checks.main()
    # The shared harness retains its v16 report wording. Replace that wording
    # with this version's actual authoring contract after all checks pass.
    digest = hashlib.sha256(Path(sys.argv[sys.argv.index('--rom') + 1]).read_bytes()).hexdigest()
    output = (Path(sys.argv[sys.argv.index('--output') + 1]) if '--output' in sys.argv
              else checks.ART_ROOT / ('runtime_' + digest[:8]))
    path = output / 'validation.json'
    report = json.loads(path.read_text())
    report['world_animation_scope'] = {
        'heroes_and_imp': 'Four authored native directions, idle and two separately drawn gait cels each.',
        'other_families': 'Four authored native directional stills, repeated at three gait addresses.',
        'native_address_coverage_is_not_distinct_art_pose_coverage': True,
    }
    for result in report['classes'].values():
        result['directions']['walking']['animation_note'] = (
            'Idle and two separately authored limb poses at the existing gait addresses; '
            'the controller walk observed all three addresses, with complete source/OAM checks.')
    path.write_text(json.dumps(report, indent=2) + '\n')
