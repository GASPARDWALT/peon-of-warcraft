# Valley of Trials atlas — v0.2.5

After Gornek's second quest grants the map, **SELECT** opens the complete Valley
overview from the Den and all six other Valley sectors. The same chart is
available through **MAP** in the Start menu. The old Den zoom and the other
regional pages remain available with left/right; A, B or SELECT closes the map.

The chart follows the annotated geographic layout: Den west of zone 2, the
crossroads north of zone 2, Hana'zua west of the crossroads, Sarkoth south of
Hana'zua, the cave approach to the north, and the fortified gate to the east.
Each of the seven miniatures represents its real native map. The first two
maps retain their scrolling dimensions; the new five maps are compact sectors.

An undiscovered sector appears as a masked rectangle with a question mark.
Entering that sector reveals its terrain and relevant markers. Questgiver and
objective icons do not disclose points inside undiscovered sectors. The green
avatar uses the player's actual current map and movement coordinates. Inside
a shared inn or hut, it marks the precise exterior door that owns the room,
including Razor Hill's different shared-room entrances.

Markers reflect saved quest state:

- Yellow `!`: an available quest or a currently unfinished objective.
- Gray `?`: an accepted quest with incomplete objectives.
- Yellow `?`: ready to turn in, including the report to Gornek.
- Completed givers and collected/defeated targets disappear from the chart.

Galgar, Hana'zua and Zureetha use their actual positions in the split maps.
Sarkoth is shown in his basin, the two exterior familiars at the cave approach,
and remaining interior familiars on the separate cavern page. The map also
updates Lazy Peons, individual cactus harvests, the Burning Blade quest and
pending gear rewards.

Save compatibility uses seven previously reserved event bits, 342–348. Every
earlier event ID, inventory allocation and save structure stays unchanged. If
an old save has none of those bits, its prior Den/Valley discoveries reveal
only sectors 1/2, once. The bridge does not reveal the five new sectors. New-map
callbacks record each current sector separately.

Implementation belongs to the atlas builder and native menu/overlay helpers:
`tools/build_peon_valley_atlas_v025.py`,
`engine/menus/peon_interfaces.asm`, `engine/menus/peon_atlas_fog.asm`,
`engine/menus/peon_atlas_quests.asm` and generated geometry tables. The builder's
manifest is `references/generated/environment_v025/atlas_overview/geometry_manifest.json`.

`tools/validate_peon_atlas_v025.py` validates the actual ROM in a disposable
emulator. Its ordinary route earns the map, explores all seven sectors, picks
the cactus quest, completes the Lazy Peon/Sarkoth/report steps, clears the two
entrance guards, enters the cavern, and checks all nine linked room doors.
Temporary event/coordinate fixtures are explicitly separated for full fog,
the old-save bridge, fourteen concurrent markers, later quest states and
out-of-range avatar coordinates. No user battery-save file is opened.

Each checked chart compares native RGB555 screen pixels, actual hardware OAM,
both background VRAM banks, tile maps, attributes and palettes against the
compiled geometry and independently computed quest state. Native observer
hooks verify CPU registers, ROM/VRAM/WRAM banks, LCD/scroll guards and event
bits. Closing the atlas must restore the readable font, HUD, allocated actor
graphics and all 190 static scenery patterns. The two flame patterns may
advance only within their three real phases; another 128 ordinary frames
after every normal chart close verify that tile animation resumes.

Reports and real native PNG captures are written to
`references/generated/environment_v025/atlas_overview/runtime/`. The report
records the precise ROM SHA-256 and clearly labels diagnostic screenshots.
Physical Chromatic hardware still needs separate testing.

```sh
PYTHONPATH=/workspace/toolchains/pyboy-preview \
  python3 tools/validate_peon_atlas_v025.py --expected-sha <rom-sha256>
```
