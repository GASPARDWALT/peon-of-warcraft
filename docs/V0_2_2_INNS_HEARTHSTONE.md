# Inns and Hearthstone — v0.2.2

The prototype has three home locations: The Den, Sen'jin Village and Razor Hill.
Their inn doors are `(17,5)`, `(15,5)` and `(17,5)` respectively. The remaining
six building doors still lead to residences with conversation and no free heal.
All nine entrances remain visitable.

A guest talks to the innkeeper, chooses rest, then chooses whether to make that
inn home. Rest restores HP, clears wounds/poison and refills spell charges. The
first accepted home grants the HEARTHSTONE menu action. Binding another inn
clears the previous home flags, so only one home is active.

The main menu lists CHARACTER, BAGS, MAP, SAVE, HEARTHSTONE, OPTION and EXIT.
SAVE remains the fourth entry, reached by three Down presses from CHARACTER.
HEARTHSTONE asks for confirmation and uses Crystal's queued overworld script,
teleport animation and native warp transition. It arrives inside the bound inn;
the backup warp points to that inn's actual outdoor door. Shared interiors
therefore exit into the correct village after travel, saving and cold restart.
It is unavailable in the battle BAGS interface.

The new maps append group 26 IDs 23 and 24. Existing map IDs, item arrays,
party structures and SRAM layout do not move. Home ownership uses previously
unused saved event bits, with no new save fields. The Orc Inn and Troll Inn
reuse the existing Orc/Troll interior palettes. Bedroll/table blocks 40 and 41
rearrange existing native tiles, adding zero tiles to the 192-tile VRAM budget.

## Classic inspiration and deliberate prototype adaptations

CMaNGOS ClassicDB identifies Innkeeper Grosk (6928) and Innkeeper Shul'kar (9356).
They inspire the Razor Hill and Sen'jin innkeepers. The Den innkeeper and its inn
are additions for this prototype; they are not presented as a Classic location.
The general concept of choosing an inn as home and using a Hearthstone follows
WoW Classic. Dialogue here is newly written, concise English.

Instant full restoration, free rest, a menu action instead of an inventory stone,
and no Hearthstone cooldown are prototype adaptations. They do not reproduce
Classic's regeneration timing, rested XP or one-hour Hearthstone cooldown.
There is no room purchase, rested XP system or item-specific stone cooldown yet.

Sources: [CMaNGOS ClassicDB](https://github.com/cmangos/classic-db),
[Innkeeper Grosk](https://www.wowhead.com/classic/npc=6928/innkeeper-grosk),
[Innkeeper Shul'kar](https://www.wowhead.com/classic/npc=9356/innkeeper-shulkar).
The NPC entries were checked against the ClassicDB SQL snapshot used for the
v0.2.1 village references. The linked web pages are reference links, not a claim
that their current contents were fetched from this cloud environment.

## Verification

`tools/validate_peon_inns.py` uses an isolated ROM, ordinary buttons and a real
battery-save restart. It checks persistent combat wounds, declined rest, HP and
charge restoration, all nine building round trips, exclusive home rebinding,
Hearthstone cancellation and all three travel destinations. It also checks SAVE's
old position and saving/restarting inside a shared inn with the correct exit.
No RAM edits, quest-flag injection or savestate shortcuts pass those checks.
Results and actual ROM captures are written to
`references/generated/durotar_v022/inn_validation/` after the integrated build.
Chromatic hardware has not been tested by this script.

`tools/rebuild_peon_v022.sh` rebuilds retained assets and the ROM without image
services or `make clean`. `--assets-only` skips the ROM build; `--validate` also
runs the integrated checks. Legacy concept compilers export into v0.2.2 and
verify that the published v0.2.1 art remains byte-for-byte unchanged. Map
generation runs world geometry, interiors, region atlas and quest POIs in that
order. Packaging stays a separate command after reviewing the reports.
