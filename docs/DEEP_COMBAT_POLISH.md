# Native battle lifecycle and basic melee polish

The apprentice's Mace Strike is now a reusable basic attack. Selecting it still
spends a normal combat turn, allows the enemy response, and honors status and
Disable checks. It no longer spends a spell charge. The attack panel displays
`--/--` in the same five character cells where other moves show their remaining
charges. Lightning Bolt and trained spells retain their existing costs.

An older character with an exhausted mace can enter the next battle normally:
before Crystal tests whether all attacks are exhausted, the adapter finds the
actual Mace Strike slot and restores its ordinary stored charge value. Reordered
move slots work, and upper PP Up bits are retained for save compatibility. This
changes neither saved record sizes nor event or item numbering. No other move is
refilled. The behavior is scoped to the Peon tileset and the apprentice adapter;
native transformed characters and ordinary Crystal battles retain their rules.

The Peon attack menu no longer accepts SELECT to reorder moves. Its trainer
already fixes Mace Strike/Lightning Bolt to slots 1–2 and prepares spells in
slots 3–4; retaining native reordering allowed basic melee's charge pool to move
into a training slot and replenish a spell there. Ordinary Crystal keeps SELECT
reordering. Already reordered imported characters still have a usable Mace
Strike wherever it exists during combat. Visiting Kento now normalizes the real
Mace Strike and Lightning Bolt IDs into slots 1–2, swapping whole move/charge
pairs so learned attacks and remaining charges are preserved. This happens only
at the trainer's entry; combat does not silently rewrite the move order. Kento
refuses training when either basic attack ID is missing rather than overwriting
a foreign or damaged record. The services regression suite verifies that
trainer normalization separately from the reordered combat diagnostic below.

All battle exits now clear Rockbiter's next-strike charge, Lightning Shield's
remaining orbs, the placed Earth Totem flag and the player attack-pose flag. These
four bytes already occupied unsaved battle padding, outside Crystal's existing
cleanup loop. Previously they were reset only when another battle started.
Victory, escape and defeat now share the same explicit zero-state invariant at
cleanup completion. The overworld subsequently reuses this shared WRAM area;
those bytes are not treated as permanent world state.

Peon victories also stop before Crystal's native evolution, Pokérus and held
berry conversion postprocessing. The current apprentice evolution table was
already empty, and virus/berry handling requires the otherwise unused
Goldenrod-reached flag. This removes a latent legacy compatibility path rather
than claiming that ordinary Durotar characters frequently experienced infection.
Ordinary Crystal tilesets keep their original postprocessing.

## Verification

`tools/validate_peon_combat_lifecycle.py` uses a fresh character and the actual
inventory Earth Totem for its ordinary-button victory. Separate branches declare
their temporary fixtures for escape, lethal enemy attack and the non-Peon
postprocessing fallback. Hooks observe the real evolution/virus/cleanup calls;
the original fallback fixture changes only the tileset at post-battle entry and
restores it before returning to the world. Normal victories retire the enemy;
escaping and losing retain it. The reusable inventory totem remains owned.

`tools/validate_peon_unlimited_mace.py` completes an ordinary Mace-only boar
battle, then tests fully exhausted charges, a reordered Mace slot with upper
PP bits, and actual Lightning Bolt consumption in labelled temporary branches.
It checks the native turn count, battle/party charge agreement, the five attack
panel cells and exact register/flag restoration by the repair helper.

Both tools write only new evidence under `references/generated/deep_polish/combat/`.
The historical lifecycle comparison rebuilds source commit `1435e70` in an
isolated directory, reproducing published ROM SHA-256
`6f1fc01438a0b35c3facdd228af0734d2a517091581e56a790769a1685c68ca7`.
No player's battery save is opened, and no published evidence is overwritten.
Final reports record the exact candidate ROM hash and test outcome.

For the retained native spell and item regression suites, run
`tools/validate_peon_deep_combat_retained.py spells` and
`tools/validate_peon_deep_combat_retained.py totems` with the configured PyBoy
environment. Their original assertions run to completion against the current
ROM, with output paths redirected into the same new evidence tree. Temporary
fixtures remain explicit, including later training spells that the ordinary
starter has not yet earned; they do not claim level 10–20 quest progression.
