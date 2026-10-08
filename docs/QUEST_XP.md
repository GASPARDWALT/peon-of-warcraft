# Native quest experience (v0.2.2)

The apprentice uses Crystal's existing saved 24-bit party EXP and native Slow
growth curve: `floor(5 × level³ / 4)`. Level 1 requires 1 EXP and has no
medium-slow underflow; a fresh level-2 apprentice starts at 10 EXP.

| Quest | Native helper | XP |
|---|---|---:|
| Cutting Teeth | `PeonGrantCuttingXP` | 15 |
| Scorpid quest | `PeonGrantScorpidXP` | 25 |
| Lazy Peons | `PeonGrantLazyXP` | 15 |
| Cactus quest | `PeonGrantCactusXP` | 25 |
| Sarkoth | `PeonGrantSarkothXP` | 50 |
| Burning Blade medallion | `PeonGrantMedallionXP` | 100 |

These six rewards total 230 XP. Without combat XP they advance the initial
level-2 apprentice to level 5 (240 total EXP), rather than making the existing
level-2-to-4 encounters trivial. Combat continues to award native battle EXP.
This is a prototype balance choice, not a copy of Classic's numerical XP curve.

## Integration and invariants

`engine/events/peon_quest_xp.asm` owns a ROMX section. Reward scripts call a
helper only after successful inventory delivery and the permanent completion
event. Repeated NPC interaction must bypass that reward branch. The helper
itself has no quest-specific flags and intentionally does not grant duplicate
protection independently of its caller.

The helper normalizes old saves to at least the current level's new Slow EXP
threshold, then adds the award and caps EXP at the native level-100 threshold
of 1,250,000. It never decreases the existing level. For example, an old
medium-fast level-2 character with 8 EXP becomes 25 EXP after a 15-XP reward
(10 EXP normalized minimum + 15), retaining level 2.

`PeonNormalizeApprenticeXP` calls the same logic with a zero award and can be
invoked on continue before the first battle. This migrates an old higher-level
save's medium-fast EXP to its Slow threshold without awarding quest XP. Without
that continue hook, normalization first occurs at a quest grant; the legacy
battle level calculation can otherwise reduce an under-threshold old save.

`CalcLevel` uses a full copied `wTempMon` and `CalcMonStats` uses the actual
party stat EXP, DVs and level. A level increase recalculates all six stats and
adds only the maximum-HP difference to current HP, preserving existing damage.
A fainted apprentice stays at zero HP. Status, move slots, charge/PP pools,
equipment and currency are not changed. No automatic spell learning,
evolution, party UI or full heal runs; Mace Strike and Lightning Bolt stay in
the first two slots and Kento manages the remaining two spell slots.

No SRAM fields or event IDs are added. Scratch space is existing `wTempMon`,
base data and arithmetic buffers. The prior current-species/current-level
context is restored. `wScriptVar` is 1 when a level increased and 0 otherwise.
`wStringBuffer2` stores the two-byte award for immediate feedback.

Inside an already open dialogue, a script may call `PeonQuestXPFeedback`
immediately after its grant and follow it with `waitbutton`. The native text
shows earned XP and, on a level increase, the new level and a reminder that
Kento trains the apprentice at even levels. All literal lines fit 18 columns.
Do not call unrelated string-buffer-changing helpers between grant and
feedback.

## Validation

Run after the parent rebuild:

```sh
PYTHONPATH=/workspace/toolchains/pyboy-preview python tools/validate_peon_quest_xp.py
```

The normal-button portion starts a fresh character, plays Lazy Peons, checks
the single award and repeat interaction, then saves and performs a cold
restart. The separate diagnostic portion explicitly edits an isolated party's
RAM, reloads an emulator state and temporarily overrides the campfire script
to call the actual grant labels. It covers all six award values, old-save
normalization, multiple levels, fainting, level-100 saturation and 24-bit
overflow while preserving damage, status, PP, moves and equipment. It also
creates an explicitly simulated old 8-EXP battery save and cold-restarts it
through the production continue hook, expecting 10 EXP with its level intact.
Those boundary checks are diagnostic tests, not claims that all six quests or the
entire level progression were played.

The diagnostic feedback test also checks the actual rendered tilemap for the
XP amount, new level and Kento reminder inside the two 18-column dialogue
rows, and captures each page. Source literals alone do not establish that
numeric text commands render correctly.

Results belong to the ROM SHA-256 recorded in
`references/generated/durotar_v022/quest_xp_validation/validation.json`.
Physical Chromatic validation remains separate.
