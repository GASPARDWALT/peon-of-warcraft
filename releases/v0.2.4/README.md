# Peon of Warcraft v0.2.4

[Playable ROM ZIP](https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/main/releases/v0.2.4/peon_of_warcraft_v0_2_4.zip) · [Visuals, native captures and offline browser gallery](https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/main/releases/v0.2.4/peon_of_warcraft_v0_2_4_assets.zip)


This is a real 2 MiB Game Boy Color ROM, extending the published audio preview
at commit `1435e70`. The adventure is in English, with one Shaman character,
one battery save and four actions. Original Warcraft-inspired GBC music,
sound effects and golden level-up particles remain integrated.

## What changed

- Orc and Troll houses/inns have four distinct terrain layouts. Nine native
  dry trees, clearer Den trails and stone Valley exit boundaries enrich the
  existing world. The atlas thumbnails reflect these maps.
- Start always has seven Shaman entries: CHARACTER, BAGS, MAP, SAVE,
  HEARTHSTONE, OPTION, EXIT. Character/bag/item pages retain fixed frames.
  Inventory shows quantities, stack position, rarity and equipped weapons;
  browsing retains fonts and successful consumption keeps a useful selection.
- The world face/life HUD has one fixed 34×8 ink footprint. It never switches
  between large and miniature versions. In exceptionally crowded Den frames
  it temporarily hides to preserve native NPC rendering. It does not claim
  an always-visible large panel or a mana system.
- Mace Strike is an unlimited basic attack and still costs a turn. Spells
  retain their charges. SELECT cannot reorder the apprentice's battle actions.
  Kento repairs older reordered Mace/Bolt records by moving their complete
  move/charge pairs to slots 1/2; other spells and charges are preserved.
- Zureetha offers Vile Familiars before Burning Blade Medallion. Four existing
  finite imps count, including kills before acceptance; dialogue shows X/4.
  Accepted/completed older medallion saves retain their existing progression.
- Hana'zua's Sarkoth turn-in opens a report to Gornek after his initial chain.
  This awards 25 XP/50 copper once. Familiars awards 40 XP/50 copper once.
  The atlas shows live familiar objectives, the cave entrance and Gornek's
  ready report. Markers retain yellow !, gray ?, yellow ? states.
- Gornek's partially delivered club/pouch rewards can be collected later
  after a full inventory, without repeating copper/XP or duplicating the club.
  Pending gear remains visibly marked.
- K'waii and Jark now offer usable Minor Potions and Tough Bread alongside
  water. Water remains five units for 25 copper; bread/potion prices are
  prototype balance, not a claimed complete Classic vendor catalog.
- Battle exits clear transient totem/shield/pose state. Peon victories skip
  inherited evolution, Pokérus and berry-conversion processing. NPC reactions
  and trainer text fit their native frames.
- Continue rebuilds current Peon terrain before uploading graphics. Saved
  cactus harvest flags are reapplied, preventing old screen caches from
  overwriting the new art or resurrecting collected decorations.

## Download, controls and saves

Extract `peon_of_warcraft_v0_2_4.gbc` from the playable ZIP and open it in a
Game Boy Color emulator. D-pad moves; A talks/interacts/confirms; B cancels;
Start opens the fixed menu. After Gornek's scorpid quest, Select or Start → MAP
opens the earned atlas; Left/Right browse discovered/fogged regions.

Visit an innkeeper to heal and choose a home. Hearthstone returns there;
travel itself does not heal. Poison still causes damage while walking.
If defeated, dismiss the dialogue, then ask the innkeeper to recover from
the one-HP return. In combat, BAGS lets you use potions/water or place the
reusable Earth Totem, each successful use costing a turn.

Back up your existing battery save. For an upgrade, put a copy beside the new
ROM with the basename/extension your emulator expects. For example, PyBoy
uses `peon_of_warcraft_v0_2_4.gbc.ram`; other emulators commonly use `.sav`.
Continue loads the same real slot. Save and restart to confirm it locally.
Never substitute an emulator savestate for the battery save when upgrading.

The gallery ZIP contains `deep_polish/index.html`; extract the ZIP and open
that file in a browser. Native captures, compiler reconstructions and explicit
diagnostic captures have separate filters. The transparent native tree is
`references/generated/deep_polish/world/props/deadthorn_tree_native.png` in
the repository (`deep_polish/world/props/` inside the assets ZIP).

## Verification and remaining scope

Release packaging checks that every required native report passes on the
exact packaged ROM SHA-256. Tests include normal naming/input, ten quest-route
battles, quest-marker pixels, one-time rewards, nine door returns, four room
battery cold restarts, a real previous-audio-release save with a harvested
cactus, native level gains/audio/poison recovery, inventory/refusal cases,
trainer purchases/legacy moves, spell/status cases and battle item turn costs.
Fault scenarios that edit temporary emulator RAM are explicitly labelled.
The supported normal routes use ordinary buttons and read-only observers.

Map IDs, dimensions, every original movement collision, item/music/sound IDs,
all prior event IDs and SRAM/WRAM layouts are preserved. Four unused reserved
event bits store the new quest/reward state. Earlier release archives and
published evidence remain unchanged. The manifest records the native CGB,
MBC3+RTC+RAM+battery header and the exact tested hash.

Shared room IDs remain within each race; exits remember the originating door.
The requested seven fixed Valley screens and complete Valley overview need
the final path drawing and a camera/location migration. This build improves
the current scrolling geography. A full armor system, six actions, other
class routes, respawning world, full Classic economy and multi-save are still
future systems. Clearing every tested enemy/side quest reaches approximately
level seven; longer progression and human balance playtesting remain useful.
Physical Chromatic cartridge/SRAM/RTC validation is still outstanding.

Build with `sh tools/rebuild_peon_v024.sh --build`; the `--validate` mode runs
the native checks without overwriting prior release evidence. See the focused
world/UI/combat/quest documents for implementation and diagnostic boundaries.

ROM SHA-256: `704022c22c441944d13e3ff65950a971e5c7ead614a1ff0e1bba476c340bea2d`
