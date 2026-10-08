# Warcraft audio and level-up preview

This update extends the released Valley preview. It retains its maps, quests,
items, one battery save slot, life HUD and compatible save layout. It does not
implement the requested seven-screen geography or a shared mana pool.

## What changes in play

- Level gains have an original short rising ding and golden particles around
  the apprentice. Battle scene options can suppress the visual; the sound
  remains. Quest XP and combat XP both use the native level-up presentation.
- Six quest offers have a confirmation sound on acceptance. Finishing a new
  objective has a short ready cue; quest reward feedback is distinct from a
  level gain. Completed flags keep these cues from replaying on reminders.
- Successful potion, bread and water use, Earth Totem placement, inn rest,
  Hearthstone travel and defeat recovery have their own sounds. Refused use
  keeps the item and does not play a successful-use sound.
- Boars keep their grunt. Scorpids, Sarkoth and coastal crawlers share chitin
  sounds; imps yelp; felstalkers, tigers and raptors share a low creature growl.
  These are original family gestures, not individually recorded WoW voices.
- Earth, frost, purge, healing and nature spells use original elemental cues.
  Lightning, flame, poison, mace, coins, bag and menu cues remain available;
  the custom bag also clicks when its selected item changes.
- Durotar/Den, the Burning Blade cavern and inns have longer original ambient
  arrangements. Battle, victory, Barrens and Orgrimmar keep the preceding
  original compositions. The supplied title arrangement is unchanged.

Nineteen new native effects are authored. Eighteen have reachable gameplay
hooks; the separate short `victory` effect is a prepared alternative, while
ordinary victories keep the existing native musical fanfare. New IDs append
after the previous 208 sounds; none are renumbered.

## Reference and recording limits

The Wowhead sound catalog was inaccessible from the cloud proxy. Historical
WoW sound filenames and Classic quest data were checked where accessible, but
Blizzard recordings were not downloaded or auditioned. These GBC compositions
and effects are original interpretations, not verified transcriptions. This
work also does not claim that a level 1–6 gameplay video was watched.

Actual emulator APU captures are supplied as WAV; MP3 listening copies are
derived from those captures. They are not PCM streaming inside the cartridge.
Individual sound and music previews use isolated diagnostics; ordinary button
play and battery-save evidence are reported separately in the gallery.

## Play and saves

Extract the playable ZIP and open `peon_of_warcraft_audio_preview.gbc`
in a GBC emulator. D-pad moves, A interacts/confirms, B cancels, Start opens
the menu, and Select opens the atlas after Gornek's second quest.

Transfer the emulator's battery save beside the new ROM with the same basename
and its usual `.sav`, `.ram` or `.srm` extension. Emulator save states are not
a cross-version save format. Physical Chromatic, cartridge SRAM and RTC checks
remain outstanding; the ROM keeps its CGB-only 2 MiB MBC3+RTC/32 KiB SRAM header.

## Trees and next Classic additions

Three transparent proposals are supplied as prepared art, not new map tiles:
`trees/deadthorn_tree.png`, `trees/crooked_acacia.png` and
`trees/coastal_palm.png`, with enlarged previews. The inland Valley should
stay sparse and dry; palms identify the Sen'jin coast. Integration needs
native background palette/tile allocation and placement against final paths.
See `DUROTAR_TREE_REFERENCES.md` for inspected sources and exact constraints.

`ORC_LEVEL_1_6_REVIEW.md` compares the existing prototype with verified Classic
data. The recommended next quest additions are Vile Familiars before the
medallion, Sarkoth's report back to Gornek, and a compact Call of Earth ritual.
They are recommendations, not quests added by this audio update.

## Reproduce

Run `sh tools/rebuild_peon_warcraft_audio.sh --build`, or `--validate` for native
APU and normal-input checks. Use the retained checkout/toolchains; do not run
historical broad world generators to rewrite published art or calibrated data.
All new public visuals and audio are in
`references/generated/warcraft_audio_update/`.
