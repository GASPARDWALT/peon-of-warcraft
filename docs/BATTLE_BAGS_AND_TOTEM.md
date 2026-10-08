# Battle bags and Earth Totem — v0.2.2

The one-time apprentice kit includes one reusable Earth Totem, inventory ID
`$94`. During a battle, choose BAGS, open ITEMS, select EARTH TOTEM with
Left/Right and press A. Placing it takes the turn: the enemy may attack, and
the apprentice does not also strike. While placed, the apprentice acts first,
including against an enemy priority attack. This is the requested turn-based
Earthbind adaptation, not Classic's exact slowing radius or real-time timing.

The totem appears as an original transparent 8×16 native prop in front of the
player. Two signed BG tiles `$86/$87` use VRAM bank 1 at `$8860`, palette 6 and
screen cells `(8,6)` and `(8,7)`. This allocation preserves the enemy's full
49-tile front picture and the player's back picture. Its placed state is
battle-only and resets on entering another encounter. Placing never consumes
the saved inventory object; trying to place it again wastes neither an item
nor a turn. Merely browsing or cancelling the bag is also free.

Duokna now offers Spring Water first by default, a Minor Potion, and Cancel.
Water remains five units for 25 copper. A Minor Potion is one unit for 25
copper and restores 20 HP, capped to maximum. The potion's fixed price and
healing are prototype balance, not a claim of identical Classic vendor data.
Other village merchants retain their existing water offer.

Water restores up to ten charges to each learned spell in slots 2–4, capped
to that spell's maximum, and leaves Mace Strike unchanged. Lightning Bolt's
maximum is 30; Earth Shock, Flame Shock and Frost Shock use 15, Chain Lightning
uses five, and the other training spells use ten. At full health or full spell
charges, the corresponding consumable remains in the bag. A used potion or
water spends one battle turn and keeps party and battle health/charges in sync.

`tools/validate_peon_battle_totems.py` completes an ordinary fresh character,
both actual purchases, native bag placement, a battle, a battery save and cold
restart, and a second encounter. A separate diagnostic phase rewinds only that
isolated battle and sets documented HP, spell charges and speed fixtures for
the no-waste, turn-cost and priority cases. It checks actual native VRAM,
attributes, palette and front-picture preservation. It never edits a player's
save or claims that temporary diagnostic levels/stats were earned normally.

The report and screenshots are saved under
`references/generated/durotar_v022/battle_totems_validation/`. Physical Chromatic
console tests remain separate from these emulator checks.
