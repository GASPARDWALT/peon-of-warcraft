# Peon of Warcraft v0.2.9

This build extends the native 160×144 Game Boy Color prototype with actual
companions, shared mana/rage, class recruitment and successive enemy packs.
The Peon remains the hero in the first saved record. One fighter acts at a
time; native switching selects another living companion.

## Implemented scope

- The initial roster holds two characters. Reporting Sarkoth to Gornek
  unlocks the third place. Warlocks begin with a real Red Imp as their second
  member. CHARACTER → Right opens TEAM; battle TEAM uses the native switch
  turn and trapping rules. Forced replacement after a knockout cannot cancel.
- Shaman and Warlock actions use a shared mana pool; Warriors use rage.
  Basic actions are free. Max mana is derived from class/level: Shaman
  `48 + 12 × level`, Warlock `60 + 15 × level`, capped at 999. Rage starts at 0,
  caps at 100, gains 8 from a successful free basic hit and 5 from direct damage
  taken. Four completed walking steps restore 2 mana or reduce 5 rage for a
  living member. These turn/step rules are explicit prototype approximations
  of Classic, including the compressed trainer progression.
- The selected Den master offers one recruitment task after the first
  Cutting Teeth turn-in, while continuing normal spell training. Earth
  Relic binds Earth Spirits for Shaman; Demon Skull binds Red Imps for
  Warlock; Rally Horn recruits Orc Grunts for Warrior. Relics are reusable.
  A valid failed attempt spends a turn; wrong family, wrong class, full
  roster or invalid target spends neither a turn nor an item. The completed
  task grants 50 experience and 100 copper once.
- Recruitment uses Crystal's original base-ball HP/catch-rate Random rule,
  including its historical status and HP-division behavior. It opens no
  ball animation, Dex page, creature naming prompt or storage box. Captured
  HP/status/DVs/experience are preserved; raw stats are recalculated before
  actions and resource metadata are initialized.
- Binding is limited to five explicit neutral training/pact nodes for this
  release: Earth Spirit at Crossroads (3,5), Grunt at Hana'zua Camp (3,6), Red
  Imp at Cave Approach (7,7), and optional level 6 Earth/Grunt at Sen'jin
  (11,14)/(12,14). The later pair requires the Sarkoth report. Capture retires
  the node permanently. A training knockout hides it until the next zone
  visit, allowing another pact attempt. These neutral encounters grant no
  scripted copper, potion or ration loot. Hostile quest enemies cannot be
  bound in v0.2.9, preventing capture from awarding kill credit or kill loot.
- A living inactive Warlock imp contributes its small one-HP end-of-round
  Firebolt. It does not contribute an extra passive bolt while it is the
  active fighter. A fainted imp stops following/assisting; inn recovery
  restores its follower. Smaller ally heads and health bars show the group
  beside the main battle presentation.
- The Valley exit has a successive Kolkar pack: level 7 archer followed by
  level 8 melee raider. The cave Warlock gains an imp reinforcement from hero
  level 4. The southern road presents a harder successive group of two
  scorpids and a raptor. Enemy members act successively, without a trainer
  presentation. Partial kills remain retired across flee, defeat and save
  reload; completing the pack grants its final scripted reward once.
- Six additional art sets cover Earth Spirit, Red Imp, Orc Grunt, evil Orc
  Warlock, Kolkar Archer and Kolkar Raider. They provide 16×16 world frames,
  three 56×56 front poses, three 48×48 rear poses, and 8×8/16×16 heads. Original
  transparent PNG/APNG sources are reusable under
  `references/generated/recruitment_v029/`. Native dictionary budgets and
  complete rear-pose transfers retain the GBC sprite/tile constraints.
- Native arrow, Firebolt, wand and elemental spell effects supplement the
  existing class animations. Three rear poses are available for each new
  active companion. The standard enemy animation path retains its native
  frames; the player/companion path uses complete guarded pose uploads.
- Spring Water restores 60 mana outside combat; Tough Jerky restores 10 HP
  outside combat. Minor mana and healing potions restore 40 mana/20 HP and
  use one battle turn when used successfully in combat. Potion loot retains
  the one-in-six roll. Curated eligible hostile drops can also supply useful
  food/water. These restoration amounts are the prototype's scale, rather
  than a claim of identical WoW Classic item units or complete loot tables.

## Valley layout and presentation

The seven-zone plan retains its intended directions: 1 → right → 2,
2 → up → 3, 3 → left → 4, 4 → down → 5, 3 → up → 6 and 2 → right → 7,
with the existing reciprocal returns
and basin shortcut. Clear soil trails, real collision cliffs and the marked
exit corridor make the connections visible. Partial cliff metatiles trace
the supplied mountain outlines more closely. Saved positions that became
walls or new NPC anchors have narrowly defined safe landing replacements.

The Den and the main Valley remain scrolling maps; the other sectors are
compact maps. This is not a literal reproduction of every reference square
as one fixed camera screen. Mountain shapes and terrain remain an adaptation
to the existing native tile/collision grid. The rest of Durotar and every
future building/map have not been recreated.

The opening keeps the sleeping Peon near the palm, BONK sequence, class
selection and master-led naming. The three low-level apprentices, class
selection colours, traversable quest indicators, rounded huts/inns, corner
beds, wall braziers and wall-only Horde banners carry forward from v0.2.8.
The atlas preserves discovery fog and adds recruitment objective/turn-in
markers. Ordinary text uses the regular font; actor names use the bold font.

Music uses the native four-channel eight-bar reduction of the supplied
“What's Up” sheet music. It is a short manually interpreted arrangement,
not a faithful transcription of all 70 printed bars. Peon maps and battles
share the theme; title and reward jingles retain their separate roles.

## Files, saves and limits

The release archive contains `peon_of_warcraft_v0_2_9.gbc`, the exact-ROM
manifest and the reports that belong to that ROM hash. Art and emulator
captures are labeled separately in the visual archive. Extract the whole
art archive before opening its `index.html` gallery.

There is one real Crystal battery save and four stored actions per member.
The native six-slot storage layout remains intact, but the playable roster
limit is two then three. Hero record/order, old numeric IDs, SRAM addresses
and 48-byte party record size are preserved. Mana/rage intentionally reuse
the two caught-metadata bytes, tagged by the cured 0x80 Pokerus byte. This is
a one-way semantic upgrade: older ROMs do not understand the new resources
or party progression. Keep an independent copy of your older save and do
not interchange saves with unmodified Pokémon Crystal.

New characters and genuine one-member legacy Warlocks receive one real
imp once. Migration preserves hero identity, equipment, HP, PP, experience,
money, bag pockets and the old Dex bitsets. Only the documented resource
metadata changes within the old hero record; the added imp occupies a
previously unused record. Existing
populated legacy parties are preserved, rather than deleting members.

Use a battery `.sav` for ROM upgrades. Emulator session snapshots are tied
to their original ROM hash. The browser RTC pauses while closed, and raw
`.sav` export contains RAM without RTC metadata. The cartridge header
remains CGB-only, MBC3+RTC+RAM+battery, 2 MiB ROM and 32 KiB save RAM.

The three hero classes retain the shared native base-stat model; the six new
roles have dedicated stats. Further ordinary balance work is needed near
Sen'jin. The recorded Warlock travel reaches the village with native RUN;
full pack victories, partial retirement and forced replacements are covered
separately by explicitly labelled combat fixtures.

This build does not add simultaneous 2v2/3v3 combat, six action slots, true
multi-save, a complete equipment/loot system, unrestricted enemy capture,
or the whole WoW world. Hardware and DevDay cartridge programming are not
performed here. Physical mapper, RTC, persistence and console performance
still need verification with the actual cartridge/firmware.

## Validation and rebuilding

Final validation status must be read from the release's exact-hash reports.
Earlier candidate passes and source-only art checks do not certify a later
ROM. The release workflow checks ordinary three-class play, party/recruitment,
resource usage, pack continuation, map routes, cold saves, older-battery
migration, raster/tile/palette stability and the browser player. No claim
that every possible bug has been removed is made by this document.

`tools/rebuild_peon_v029.sh` uses the configured RGBDS 1.0.4 toolchain, the
existing C/Python dependencies and only the new v029 art generators. It
copies tracked source plus explicitly named new v029 inputs to an isolated
temporary build directory, regenerates the new art there and checks its
native output against the current expected inputs. Make/lint also run there,
so legacy generation cannot replace old published visual evidence. Only the
resulting ROM/SYM/MAP are copied back. It creates no Git worktree and does
not flash a cartridge or publish a release.

In the prepared cloud environment run `sh tools/rebuild_peon_v029.sh`.
Elsewhere put RGBDS 1.0.4 on PATH or set `PEON_RGBDS` to its binary directory,
and use `PEON_MAKE_JOBS` to change the default four build jobs. Python/Pillow,
NumPy and the existing Make C-tool dependencies must already be available.
The helper does not install dependencies. Intentional art edits should first
update/review the versioned expected gfx inputs; a byte mismatch is an error,
not something the helper silently accepts.
