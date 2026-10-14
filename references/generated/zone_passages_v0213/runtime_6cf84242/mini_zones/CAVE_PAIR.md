# Full cave pair native QA

Final evidence: `cave_pair_attempt_03/validation.json`, `cave_pair_summary.json`, and 81 actual native screenshots, each also available at nearest-neighbor 4× scale.

Exact frozen ROM: `/tmp/peon-v0213-frozen/peon_v0213.gbc`, SHA-256 `6cf84242e9a518af635fe9e2138f7f60228de2d0da7b4ee12ba7511f814f88e8`, matching frozen `.sym`. The run cold-booted a fresh private ROM copy, selected Shaman through native menus, accepted Gornek's quests, won the level-one boar and level-two scorpid encounters, turned them in to reach level 4, and rested at the actual inn. It did not use the offered private progress battery.

Both level-three approach guards were triggered by ordinary walking and defeated. Imp 1 took three Lightning Bolts (HP 20→12, mana 96→51). A deliberate inn rest restored the hero before imp 2, which took two Lightning Bolts (HP 20→15, mana 96→66). Both persistent retirement flags were observed; neither fight silently healed. No lesson purchase or injected level/money/resource was used.

Required portal checks all passed:

- Approach `(5,2)` and `(4,2)` → Cavern original landing `(10,16)`.
- Cavern `(10,16)` and `(11,16)` → Approach original landing `(5,2)`.
- Each arrival took an ordinary native `FLOOR` step without immediate re-warp.
- All 12 required approach/arrival/egress allocator observations passed actual base/extra VRAM packet, PPU priority-bit, and live OAM overlap checks.

The run records 19 crossings including inn and routing, four genuine victories, 54 world allocator observations, 969 button operations, and final frame 55368. It then revisited both guard proximity cells after the cave returns without starting another encounter. The private session closed with `save=False`; no RAM writes, CPU substitutions, emulator states, or user saves were used.

Cavern traversal stayed beside its doorway. This proves the full two-way portal pair, not the interior boss fight, audio, or physical Chromatic behavior. Interior inn traversal/screenshots are recorded; its unrelated graphics packet is outside the canonical world allocator checker.

Preliminary evidence remains preserved. Attempt 01 caught an observer timing issue before any first battle action; adding 80 neutral frames before actions fixed the helper. Attempt 02 retains an ordinary boar win and turn-in; the final run restarted fresh after scoping allocation checks to the actual world packets. No concrete game failure was found.
