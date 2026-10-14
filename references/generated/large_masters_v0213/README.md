# The Den training lodge and Zone Two sleeping worker

The western door at The Den `(5,7)` opens `PeonOrcHut`. It now houses the
three class masters. The eastern building, `PeonOrcInn` at `(17,5)`, retains
its rest and hearthstone service. Razor Hill instances of the shared hut
retain the ordinary attendant instead of duplicating these masters.

The masters are stationary complete 24×24 sprites: Kento, Tauren Shaman at
`(6,3)`; MoCMoc Zogzog, Orc Warrior at `(7,5)`; Bismillah LesTenèbres,
Undead Warlock at `(3,7)`. Their existing native class restrictions,
training menus, recruitment dialogue and speaker portraits remain wired.
The Warlock's full name uses two lines; narrow selection/training headings
use `BISMILLAH`. The font now includes the real grave-accent character.

Source: `references/characters/class_masters/class_masters_crystal_style_sheet_reference.png`.
The manifest records the original hash, exact three crop rectangles,
border-paper removal, complete retained silhouettes and nearest-neighbor
conversion. This is a lossy import from a supplied raster reference;
it is not recovery of a native 24px source grid. No equipment, anatomy,
primitive replacement art, smoothing or additional generation is authored.
The split `warrior_trainer_combat_front.png` contains only an axe and is
excluded from this NPC import because it is not the complete master.

Each master reserves nine standing graphics tiles and emits nine native
8×8 OAM objects. No walking graphics are uploaded. The vertical spacing
prevents three masters sharing a scanline. OBJ palettes 3/4/5/7 are
scoped to this training lodge; Bismillah shares unchanged Warlock family1.
Either hero1/2, life0 and mana6 remain intact.
The room hides its attendant and the walking Imp follower, retaining
the Imp's party record and restoring the follower outdoors. The largest
screen uses 27 master objects +4 hero +6 life/mana HUD =37 of40 OAM slots.
The runtime validator additionally checks the real ≤10 objects per scanline.

The lazy quest worker moves to Valley of Trials `(20,13)`, appended as
actor12. The Den keeps its foreman and return reward. Original disabled
actor slots remain in The Den so existing indices do not shift.
The objective marker and foreman's directions now point to Zone Two.
Quest flags, reward amount, party and saved-record layout remain unchanged.
The wake emote uses the current speaker rather than a hard-coded old actor.

Cold Continue recreates Peon actors from current ROM events. Its native
sprite allocation is now rebuilt before those object structs copy their
tile numbers. Without that order, newly copied NPCs inherited tile0 and
displayed fragments of the player's graphics. The correction is scoped to
Peon maps, keeps indices and saved records intact, and is tested against a
real private32KiB battery save in this lodge.

`tools/validate_peon_masters_sleeping_v0213.py` walks the real lodge, checks
all three native sprite packets/OAM, opens each class's proper trainer,
refuses other classes, wakes the relocated worker, returns for100c and
checks that the reward cannot duplicate. It uses ordinary buttons in
private fresh ROM copies; no emulator RAM edits or loaded states.
