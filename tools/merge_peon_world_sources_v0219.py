#!/usr/bin/env python3
"""Assemble the three independently documented creature groups, without art edits."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'assets/world_readability_v0219'
GROUPS = ('monsters_base', 'monsters_extra', 'kolkar')


def main():
    roles, inputs = {}, {}
    for name in GROUPS:
        path = FOLDER / (name + '.json')
        data = path.read_bytes()
        packet = json.loads(data)
        assert packet['version'] == 'v0.2.19'
        assert not set(roles).intersection(packet['roles']), name
        roles.update(packet['roles'])
        inputs[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
    assert set(roles) == {'imp', 'scorpid', 'sarkoth', 'enemy_warlock', 'harpy',
                          'yarrog', 'rock_one_npc', 'kolkar_archer', 'kolkar_raider'}
    result = {'version': 'v0.2.19',
              'authoring': 'Documented source restoration/conversion; no pixels changed by this merge',
              'input_sha256': inputs, 'roles': roles}
    (FOLDER / 'monsters.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'roles': len(roles), 'inputs': inputs}))


if __name__ == '__main__':
    main()
