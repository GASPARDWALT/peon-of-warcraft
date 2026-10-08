# Native level-up gold aura

The apprentice gains a brief yellow ring and rising sparks around his actual
overworld sprite, or around his 48×48 battle backpic. The source is original
two-tile GBC pixel art with three opaque colors and transparent index zero.
`peon_level_glow.png` is the transparent 16×8 source; `_16x.png` is a
nearest-neighbor magnification. These source previews are not game captures.

The effect has six distinct native poses held for six frames each: 36 visible
frames, roughly 0.6 seconds, plus graphics upload and hardware-restoration time.
`SFX_PEON_LEVEL_UP` (`$D0`) starts once before the visual and finishes within
29 native frames. The helper waits for earlier effects first, and for the ding
to finish before returning. A quest reward without a level plays the shorter
`SFX_PEON_QUEST_REWARD` (`$D3`) instead.

Battle entry: `PeonBattleLevelUpFeedback`, called by
`AnimateExpBar.LoopLevels` at each actual level threshold for the Peon map.
Quest entry: `PeonWorldLevelUpFeedback`, called by `PeonQuestXPFeedback` only
when the actual XP grant reports a level increase in `wScriptVar`. Continuing
a saved game normalizes XP without invoking this reward-feedback path.
The legacy non-Peon battle path retains its original presentation.

The six phase callbacks are `PeonPlayLevelGlow.Phase`. The precise restoration
point is `PeonPlayLevelGlow.Restored`, after palette/OAM/bank/update states have
been restored and served to hardware, before the input DE/HL arguments are
popped. The public wrappers subsequently restore all caller registers.

Native resources: OBJ bank0 `$86e0..$86ff`, tiles `$6e/$6f`, immediately after
the player HUD. They are loaded immediately before the effect because battle
animations may reuse this area. Temporary OBJ palette7 is saved and restored
in both buffers; OAM entries32–39 are saved/restored on the stack. The first32
OAM entries are never changed. Terrain, fonts, front/back portraits, rank,
totem, quest data, XP and saved fields are untouched by the visual helper.

The visual is deliberately skipped if any of the final eight OAM entries
contains a visible actor; the ding still plays. This preserves crowded NPC
scenes rather than replacing an actor. Scènes OFF also skips the visual while
retaining the sound. Particles outside the viewport are hidden. The visual
therefore needs actual rendered-pixel validation, not only source-file checks.
