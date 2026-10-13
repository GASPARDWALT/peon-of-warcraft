# Peon of Warcraft — Environment Pack v2 (Art Quality)

This replaces the procedural placeholder pack.

The assets were generated from the approved high-detail GBC/Warcraft visual standard and then exported at native game dimensions.

Folders:
- `durotar_valley/`
- `razor_hill/`
- `senjin_village/`
- `echo_isles/`
- `shared_interactables/`
- `source_atlases/`
- `previews/`
- `docs/`

Technical rules:
- terrain tiles: 32×32, opaque
- props/buildings: transparent PNG
- dimensions are multiples of 8
- each 8×8 block is palette-reduced for GBC-style use
- nearest-neighbor only
- animated pairs keep identical canvas dimensions

Recommended repo destination:
`references/generated/environment_pack_v2/`
