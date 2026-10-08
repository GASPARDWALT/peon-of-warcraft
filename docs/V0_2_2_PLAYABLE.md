# Peon of Warcraft v0.2.2 — playable Shaman chapter

The apprentice can complete the opening, quest in the Valley of Trials, explore
the Burning Blade cavern, visit Sen'jin and Razor Hill, and reach Orgrimmar Gate.
This build adds finite persistent enemies, quest XP and markers, inns, battle
consumables, spell training, original elemental animations and native music.

## Start and play

Extract the playable ZIP and open `peon_of_warcraft_v0_2_2.gbc` in a GBC
emulator. Choose New Character for the revised progression. Kento asks for your
name; conversations use **Péon + your chosen name**. The humble green apprentice
receives a crude mace, wooden shield, belt totem and simple Lightning Bolt.
The separate reusable Earth Totem is placed from battle BAGS.

- D-pad: move and select. A: interact/confirm. B: cancel.
- Start: character, bags, map, save and Hearthstone. Hearthstone follows SAVE.
- Select: zone map after Gornek's second quest. Undiscovered zones stay hidden.
- Yellow outlined creatures: interact with A. Red outlined enemies: proximity
  combat. A quest giver handles one quest at a time.
- Quest marker: yellow `!` → gray `?` → yellow `?` → hidden after reward.
- Buy training from Kento; prepare spells in the two slots after Mace Strike
  and Lightning Bolt. Buying and re-preparing a spell never repeats the kit. Older characters can
  receive the new reusable Earth Totem at Kento; a full bag allows a later retry.
- Rest at an inn to recover health, statuses and spell charges, and bind home.
  Defeat, including poison outside battle, leaves one HP at the bound inn
  or falls back to The Den. Neither victory nor defeat gives a free full heal.

Gornek's boar and scorpid quests award 15 and 25 XP; Lazy Peons awards 15 XP.
Galgar's three harvestable cacti award 25 XP and a larger bag. Sarkoth awards
50 XP and two potions. Yarrog's medallion awards 100 XP and a green Spirit Mace.
Rewards and dead actors persist through actual battery saves. Ordinary mobs
give small copper rewards rather than repeated equipment. A level-four road
pack contains two consecutive scorpids; the first remains defeated if the
second fight is lost. There is no spawn or infinite XP loop in this chapter.

## Spells and animations

| Apprentice level | Training |
| --- | --- |
| 2 | Rockbiter, empowering the next physical hit |
| 4 | Earth Shock and Flame Shock; Flame Shock burns eligible targets |
| 6 | Healing Wave, restoring half maximum health |
| 8 | Lightning Shield, three physical-hit retaliations |
| 10 | Strength of Earth, an attack buff |
| 12 | Purge, removing enemy bonuses while preserving their debuffs |
| 14 | Frost Shock, slowing eligible targets |
| 16 | Stronger Flame Shock |
| 18 | Windfury, two to five physical hits |
| 20 | Chain Lightning, a stronger single-target Nature spell |

Higher-level trainer cases are covered by explicitly isolated emulator
diagnostics; the finite first chapter does not provide a normal route to level
20. Prices and effects include documented prototype adaptations. This is a
turn-based game using native charges, rather than a shared Classic mana pool.

Eleven new native animation scripts use original four-frame flame, green leaf,
lightning and wind particles, with separate frost colouring and earth debris.
Lightning Bolt retains its simple arc. Effects use native GBC sprite palettes,
without changing the front/back picture allocation or saved character layout.
Transparent PNG particle sheets and real-ROM GIFs are in
`references/generated/durotar_v022/spell_animations/`.

Battle BAGS offers a reusable Earth Totem and consumables outside the four
attack slots. Placing the totem makes the apprentice act first for the encounter,
including against priority moves. Placement costs a turn; repeats are rejected
without spending one. Potions heal up to 20 HP and water restores up to ten
charges to each prepared spell. Used consumables spend a turn and cannot be
wasted at full health/charges. The totem resets on the next encounter.

## Art, audio and browser gallery

Eight additional enemies have native directional sprites, 56×56 fronts,
48×48 backs and four battle poses. Boss rank dragons, fourteen speaking
portraits, thirty-two item illustrations, harvestable cacti, campfires, Horde
banners, palisades and clearer rocky roads are included. Nine doors lead into
six residences and three inns. Prepared Mage/Warrior art is labeled separately.

All new visual exports live under `references/generated/durotar_v022/`. Native
sprite and icon PNGs have binary transparency and the actual ROM palette.
Terrain/screenshots are opaque. Concept drawings are distinct from compiled
native art. The game still renders at 160×144 with 16×16 world characters;
large concept artwork is not inserted at its original resolution.

Extract the asset ZIP and open `durotar_v022/index.html` in Chrome or Edge,
keeping its sibling folders together. The offline gallery offers filters,
individual image downloads, animations and native audio previews.

Seven original four-channel GBC themes cover Durotar, cave, battle, inn,
victory, the Barrens-inspired road and Orgrimmar Gate. The title remains an
arrangement of the supplied guide. Native WAV previews are emulator APU output.
No Warcraft recordings, Wowhead icons or MP3s are embedded or streamed.

## Saves, compatibility and verification

The ROM is 2 MiB, CGB-only, with MBC3 + RTC + battery and 32 KiB save RAM.
Both cartridge header checksums pass. The native character/box structures keep
four move/PP entries; persistent progress uses previously unused event bits.
One real save slot remains. Continue reloads current Peon NPC scripts and
visibility from saved progress; roaming NPCs reset to their defined positions,
while the player location and inn binding are preserved. Back up the original battery save before migrating
it to the new ROM basename; preserve your emulator's `.sav`/`.srm`/`.ram`
extension. Use battery saves rather than emulator save states across versions.

Compilation passes with pinned RGBDS 1.0.4, including a forced rebuild of every
target. PyBoy checks cover ordinary-button new-game/quests/travel/merchants,
14 actual battles, real 32 KiB battery cold restarts, and actual save upgrades
from v0.1.1, v0.2 and v0.2.1. Diagnostic renderer, spell, priority and full-bag
cases are labeled explicitly. Every release report must match the exact ROM
SHA; the packager rejects stale/failed reports. Dialogue lint checks 597 rows
against the longest supported player name.

Physical Chromatic/cartridge flashing, RTC behavior and console audio remain
untested. A cartridge supporting the ROM's size, mapper and save features is
still required. Six stored attacks, other playable classes, full equipment
slots, multiple characters, simultaneous group combat and the complete world
are separate systems; see `PEON_V022_ATTACK_SLOTS.md` for the save risks.

Reproduce with `sh tools/rebuild_peon_v022.sh --build`, then the validators,
gallery generator and `tools/package_peon_v022.py`. No image-generation API
or external audio downloads are needed to rebuild retained assets.
