# Original item catalogue

Source: `concept_item_atlas.png`, generated with image_gen for this project.
The icons are original artwork inspired by early Durotar and GBC RPG readability.
They are not extracted Blizzard assets or exact replicas of Warcraft icons.

Run `python tools/build_peon_item_catalog.py` to reproduce the exports.
Each object has transparent 16×16 and 32×32 PNGs, plus nearest-neighbour 4× views.
Every native icon uses binary alpha and at most three opaque RGB555 colours.
The fourth ROM colour is the menu parchment background. This converts PNG
transparency into the existing opaque BG surface without an extra sprite layer.
Internal `gfx/pack/peon_item_icons/*.png` files are indexed grayscale without
alpha so RGBDS can rebuild their exact 2bpp indices through its generic DMG
rule. Public `references/generated/durotar_v022/items/*_16.png` exports retain
their colored RGBA artwork and transparency.

`engine/menus/peon_item_icons.asm` exports `PeonDrawInventoryItemIconFromC`.
Pass the item ID in C; AF/BC/DE/HL and VBK are preserved. It draws four tiles
at bank 0 `vTiles2 $28..$2b`, palette 5, columns 16–17 / rows 3–4. Unknown IDs
use the pouch. `$fe` is solely a menu selector for the hearthstone icon; it
does not create a tangible item or change the event-backed Hearthstone design.

Only Shaman is functional. Mage/Warrior assets are explicitly marked prepared
for locked routes. Earth Totem (`ITEM_94`) is an integrated starter battle
consumable. The remaining prepared gear/totem art does not add armor slots,
loot, class routes or combat effects. Quality tags use Classic gray/white/green/blue
semantics; material colours remain independent of quality. Native pixel and
2bpp round-trip checks are recorded in `asset_manifest.json`. Physical
Chromatic behavior still requires the ordinary console acceptance checks.
