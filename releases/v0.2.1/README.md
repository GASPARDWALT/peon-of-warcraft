# Peon of Warcraft — v0.2.1

Download `peon_of_warcraft_v0_2_1.zip`, extract it and open the `.gbc` in your Game Boy Color emulator. Controls: D-pad to move, A to talk/confirm, B to cancel, Start for CHARACTER/BAGS/MAP/SAVE, Select for the earned zone atlas. Keep a backup of an existing battery save when switching ROM versions. There is one real character/save slot.

If your emulator associates a battery save with the ROM filename, copy your old save and give the copy the new ROM's basename. For example, `peon_of_warcraft_v0_2.sav` becomes `peon_of_warcraft_v0_2_1.sav`; retain the emulator's actual extension (`.sav`, `.srm` or `.ram`). Keep the original copy. The upgrade checks cover v0.1.1 and v0.2 characters saved at The Den; other old locations need further migration checks.

## What changed

The native outdoor tileset now contains 192 eight-by-eight tiles and 40 blocks: shaped main roads bordered by grouped boulders and canyon walls, layered cliffs, coast, palms, troll huts, orc buildings, palisades, watchtowers, banners and cave decorations. The Den has a static campfire: face it and press A to rest and recover. The Den, Valley of Trials, Durotar Road, Sen'jin Village, Razor Hill, Orgrimmar Gate and Burning Blade Cavern are connected, compact playable maps. Orgrimmar Gate is the current northern endpoint, not the city interior. Terrain colors and the earned atlas match each region.

Sen'jin and Razor Hill each have six interactable NPCs; the road and gate each have three. Named Classic NPCs include Master Gadrin, Master Vornal, Bom'bay, K'waii, Vel'rin Fang, Gar'Thok, Grosk, Jark, Orgnil Soulscar and Thotar. Names/vendor roles were checked against Classic DB; text is adapted into short English dialogue. K'waii and Jark sell five Spring Waters for 25 copper. Some NPCs provide free rest or directions, rather than their complete Classic services.

Nine doors are visitable: two at The Den, three at Sen'jin and four at Razor Hill. They share two compact interior layouts with friendly attendants. Each door returns to its own exterior location, including after saving inside and restarting. Buildings are not personal storage or unique fully furnished shops yet.

Six new native overworld role sheets represent troll guards, fishers and casters, plus orc guards, vendors and questgivers. Their transparent exports have twelve directional walking frames; ordinary Crystal NPCs mirror side frames. Named NPCs share these role sheets. Thirteen speaker portraits render at 24×24 above the normal eighteen-column dialogue box.

The peon and six original humanoid roles now fill more of their native 16×16 frames. The peon's front/back idle silhouette is 15×15, up from 14×12; a one-pixel walking bob and alternating feet reach 15×16. Independent player side frames retain the mace and shield sides. Transparent per-direction APNG/GIF walking previews are included.

Boar, scorpid and imp front poses now play during enemy attacks, alongside original impact/spell effects. The boar and scorpid use visibly different anticipation, strike and recovery silhouettes. Crystal's poison application and one-eighth maximum-health residual damage remain. The prototype heals after training fights, so this is not a persistent poison-management quest yet.

Native Durotar encounters use a brief fade followed by the peon and enemy battle silhouettes. The trainer slide, Poké Ball transition/send-out, creature cry, summon text and Pokémon nickname question are skipped on this route. Kento's earlier question names the player. Legacy code outside the playable Durotar route remains in the original engine.

Start labels/help and battle SELF use the peon interface. CHARACTER shows Mak'gora Proofs as **zero earned**: duel/proof progression is reserved, not implemented. The gray weapon is CRACKED MACE and the white weapon WORN MACE; green BARBED CLUB and rare blue SHAMAN MACE remain custom prototype balance. Spring Water restores ten Lightning Bolt charges, capped at thirty. Water and weapons used from battle BAGS now update the active combatant as well as the saved character.

Character, backpack, inventory and atlas presentation use native Warcraft-inspired parchment, faction-red headings and a gold frame. Weapon quality appears in gray, white, green or blue, using Classic rarity colors reduced to RGB555. The atlas overlays yellow `!`/`?` markers for the Foreman and Galgar, only in discovered regions; completed quests remove their marker.

## Existing playable route

New Character runs the sleeping peon → hunter bonk → Thrall/class masters intro. Only Shaman can be chosen. Kento asks your name, and the saved character is addressed as `Péon <name>` (five chosen characters). You receive a crude mace, wooden shield, apprentice totem and Lightning Bolt, then reach The Den.

Talk to Gornek under the quest marker. Cutting Teeth uses one neutral boar: approach and press A; it does not aggro. Return to Gornek, accept Sting, then approach the red scorpid: it attacks within two tiles without A. Return for the Durotar Map, green club and twelve-stack pouch. Equip the club from BAGS. The atlas starts locked and reveals whole regions as you visit them.

The Den also has Foreman Thazz'ril, a sleeping worker and two additional neutral boars with yellow outlines. Lazy Peons adapts Classic quest 5441 to one worker: accept from the Foreman, wake the worker with a BONK, then return for a one-time 25-copper prototype reward. These two extra boars have flavor dialogue and never initiate combat.

Go east to Valley of Trials. Galgar asks for three cactus harvests: face a cactus and press A, then return for the twenty-stack Leather Bag. The cave has red imp fights with gray/white weapon loot and a 1/64 blue drop chance. Follow the main road to Sen'jin, Razor Hill and Orgrimmar Gate. For the detailed original walkthrough, see `V0_2_PLAYABLE.md`; current loot names and village visuals supersede that version.

## Transparent artwork and browser viewing

All generated visuals remain under `references/generated/`. The v0.2.1 asset ZIP includes sibling `durotar_v021`, `durotar_v02` and `title_portal_gbc` directories. Extract the ZIP and open **durotar_v021/index.html** in Chrome or Edge. No server or installation is needed. Search/filter by role, group, transparency, animation or version; open a thumbnail to download its exact native file.

There are sixteen overworld character/creature role sets across these two passes, fourteen prepared front/back battle sets, thirteen speaker roles, transparent building/prop cutouts, equipment icons and spell previews. Friendly village battle animations are prepared exports, not new combat encounters. Large concept sheets are inspiration; only files labeled actual ROM captures show in-game rendering. Text/icons baked into large presentation sheets are not import-ready native sprites.

## Validation and save compatibility

The release packager rejects stale validation reports. The build, normal-button intro/quests/vendors/equipment/map/cave route, sixteen player renderer facings, eighteen village conversations, nine door round trips, thirteen portrait variants, Lazy Peons and campfire rest, real battery save/restart and upgrades from v0.1.1 and v0.2 Den saves are checked. A separate battery save made inside a troll hut retains its return door after cold restart. Atlas quest-state and menu-color checks are isolated renderer diagnostics; ordinary encounter hooks verify that trainer, Poké Ball and nickname paths are not called.

Normal playable-route and village checks use no RAM edits. Renderer variants and diagnostic poison/defeat/battle-item checks use explicitly listed, isolated temporary injections; they are not used to pass the ordinary quest or save flow. Reports include the exact ROM SHA-256 under `durotar_v021`.

Map IDs were appended, original sprite/item IDs reused, and no new persistent fields or expanded inventory arrays were introduced. Shared rooms reuse Crystal's backup-warp fields. Old saves elsewhere may have coordinates occupied by new scenery; these locations require further migration testing. Chromatic cartridge flashing, SRAM persistence and RTC on actual hardware remain untested.

## Boundaries of this build

This is a playable slice, not all Durotar or all Classic quests/NPCs. Echo Isles, Sen'jin trolls' complete quest lines, Orgrimmar city, profession services, full vendor stock/selling/buyback, Warcraft-style shared mana, independent armor/shield/totem calculations and the full loot catalog remain future work. The one real equipment slot is the weapon. Bags remain six/twelve/twenty item stacks inside Crystal's existing twenty-entry save pocket. Quests use reduced counts; naming, rewards and story transitions include prototype adaptations.

The native ROM is 160×144. Detailed portal concept art and large atlas sheets have greater detail than the final native map/sprite budget. Terrain is opaque; sprite/building/prop exports use binary transparency. The title now plays a native four-channel arrangement of the supplied MIDI guide, with a 16-second actual-emulator WAV preview in the asset archive. The supplied MP3 is not streamed directly; the arrangement is not an exact transcription. Outdoor and battle music still use existing engine tracks. Short native effects now evoke Warcraft melee/spells/UI: BONK/mace impact, Lightning Bolt, Firebolt, poison/sting, menu rustle and shop coins. Wowhead catalog access was blocked by the environment; these are original chiptune interpretations, not copied samples or verified exact sound matches. Recorded effect WAVs are available through the offline sound player.

## Reproduce

Use RGBDS 1.0.4, Python with Pillow/NumPy, and PyBoy 2.7. Run the repository's `tools/rebuild_peon_v021.sh`, then the validation/packaging commands listed in that script. Source concept atlases are retained for repeatable native conversion; regeneration does not call an image service.
