# Lazy Peons and camp life

The Den now contains eleven map actors. The original six keep their indices;
Foreman Thazz'ril, one lazy peon, one quest marker and two additional yellow
boars are appended. The new NPCs use existing native Warcraft role sheets.

| Actor | Coordinate | Role |
| --- | --- | --- |
| Foreman Thazz'ril | 8,15 | Offers and completes Lazy Peons |
| Lazy Peon | 5,16 | Wakes on interaction after accepting the quest |
| Foreman quest marker | 8,14 | Remains visible until this quest is complete |
| Neutral boar | 6,15 | Yellow, idle, non-aggressive flavor interaction |
| Neutral boar | 14,15 | Yellow, idle, non-aggressive flavor interaction |

The original east-camp boar remains Gornek's combat target. The two new boars
do not start battles, grant loot or change Gornek's quest; neither approaching
nor talking to them causes aggression.

Accept the foreman's task, speak to the sleeper, then return to the foreman.
The wake interaction plays the native BONK/mace effect and a surprise emote.
It is not a battle. Completion gives twenty-five copper once and hides the
marker. Further conversations cannot wake the worker again or repeat the reward.

A warm campfire at `(12,7)` is interactable from below `(12,8)`. It offers
optional health and spell-charge restoration. It clears the dialogue speaker
identity so scenery does not inherit a previously visited NPC's portrait.
Clicking either quest marker attributes dialogue to its actual questgiver.

## Source and deliberate adaptations

[Questie v8.8.2 Classic quest 5441](https://github.com/Questie/Questie/blob/v8.8.2/Database/Classic/classicQuestDB.lua)
is **Lazy Peons**, offered by Foreman Thazz'ril (11378). Classic requires waking
five Lazy Peons using the Foreman's Blackjack (16114). This compact adaptation
wakes one peon using the apprentice's starter mace and pays a custom twenty-five
copper reward. The Den position, shortened English dialogue, exact reward and
campfire rest are prototype additions, not verbatim Classic implementation.

The three persistent flags occupy previously unused bits before `const_next 600`:
`EVENT_PEON_LAZY_ACCEPTED` 277, `EVENT_PEON_LAZY_AWAKE` 278 and
`EVENT_PEON_LAZY_DONE` 279. Existing event IDs and SRAM allocation are preserved.

`tools/validate_peon_lazy_quest.py` uses a fresh normal-button new game, walking,
NPC/marker conversations, wildlife proximity, campfire rest, one-time reward
checks and battery-save cold restart. It does not edit RAM or load emulator
states to pass the playable flow. Its report and captures are saved under
`references/generated/durotar_v021/lazy_quest_validation/`.
