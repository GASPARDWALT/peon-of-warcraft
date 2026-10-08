# Fixed native panels and inventory polish

The apprentice's Start menu has seven entries in a fixed `(6,0)`–`(19,15)`
box: CHARACTER, BAGS, MAP, SAVE, HEARTHSTONE, OPTION, EXIT. Imported Crystal
Dex/Gear flags cannot add duplicate character or atlas entries. Original
non-Shaman, link and contest list handling remains available internally.
The optional help strip still occupies rows 15–17.

Character, backpack and inventory retain the same native 20×18 tile frame
(160×144 pixels). Character now shows current/maximum HP and the four actual
prepared action names instead of a hardcoded opening spell list. Empty action
slots have their own stable rows. This remains a single weapon slot and four
prepared actions; it does not claim functional armor or six-spell storage.

Inventory keeps fonts and frame tiles resident while Left/Right changes the
selected item. Only the interior buffers change. The page shows used/capacity
stacks, the selected stack index, quantity, and EQUIPPED for the active weapon.
The rarity ribbon is reset before drawing the next item. Item help describes
real potion, water, bread, reusable Earth Totem, and quest-proof behavior.
Full-health/full-charge/invalid totem/food use gives visible feedback without
consuming an item or a battle turn. A successful world consumable keeps its
stack selected; removing its final unit selects the next existing stack or
clamps to the final preceding stack. An empty pocket safely accepts A/B.

No persistent fields, item IDs, event IDs or menu-index constants changed.
The zero Mak'gora Proof placeholder no longer crowds the character page:
proof progression is still unimplemented, and no proofs are awarded here.

`tools/validate_peon_deep_ui.py` uses normal buttons through new-game naming,
class acceptance, the actual starter bag, character/Start menus and invalid
world totem use. A separate diagnostic phase explicitly restores a private
state and edits its bag, damage, prepared spells and legacy flags to check
capacity text, rarity cleanup, non-waste guards, quantities, cursor retention
and empty inventory. It validates the actual native frame and CGB attributes,
not a drawn HTML approximation. The validator copies the ROM into a temporary
directory and never opens a user's battery save. Evidence is stored in
`references/generated/deep_polish/ui/` and includes its exact ROM SHA-256.
