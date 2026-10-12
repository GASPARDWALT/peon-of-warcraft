# Class player graphics in v0.2.6

The existing Shaman apprentice artwork is retained. Warrior and Warlock have
new native world sprites, character portraits and rear combat poses, selected
from the two already saved class flags. The Warrior has a modest axe and
wooden buckler; the Warlock has an apprentice robe and staff. All three remain
small early-game peons rather than characters in heroic armor.

The graphics keep the established game sizes: 16×16 world sprites, 56×56
character portraits and 48×48 rear battle pictures. Their native tile regions
and saved actor record do not grow. World sheets contain four actual facing
directions and two distinct walking foot poses, with an idle pose between
steps. Accessories are explicitly drawn for each direction instead of being
flipped to the opposite hand by the renderer.

The class selection screen previews the highlighted class before a class flag
is saved. The saved-character screen reads the verified battery record's
class for its center preview before Continue loads the world. Character,
world sprite reloads and battle entry then use the actual selected class.
The character sheet currently displays portrait frame 0; the additional
native portrait/front frames are supplied as artwork without claiming that
those portraits animate in this build.

Physical actions use idle, ready and release rear poses. The Shaman's
Lightning Bolt retains idle/ready casting motion; the Warlock's Shadow Bolt
also releases the casting hand. Player-pose uploads retain the original
6×6 tile anchor and protect enemy graphics, HUD, the elite emblem, placed
Shaman totem, Warlock imp and the separate bold-font graphics.

Source assets are in `gfx/peon_classes/{shaman,warrior,warlock}/`. Transparent
native PNGs and enlarged previews are in
`references/generated/visual_polish_v026/classes/`.

`tools/validate_peon_class_graphics_v026.py --expected-sha HASH` uses three
isolated copies of the exact candidate ROM. It performs the normal intro,
class choice, naming, walking, Character and map menus, inn entry/exit,
actual battles and 32 KiB battery saves using ordinary controls. Its hooks
are read-only, and an attempted emulator RAM write explicitly fails. It never
loads emulator states or opens a user's battery file.

The suite compares actual native VRAM bytes to each class's binary frames,
checks the selection previews' actual paper/brown/green palette and completed
RGB555 framebuffer, checks hardware OAM and visible RGB555 character pixels
for all four facing positions and both walking poses, verifies the row-major character portrait,
observes rear combat poses in motion and checks protected regions around
native uploads. A cold restart checks the saved-class center preview before
Continue, then the actual world sprite and subsequent battle back picture.
The native follower can overlap a foot during a turn. World pixel checks honor
earlier hardware OAM objects and require at least 16 visible authored pixels;
they do not force the pet away or replace a hidden pixel. Adjacent genuine OAM
snapshots handle the one-frame difference between DMA and the completed LCD
frame. Every hook error is retained and fails validation. Failed attempts keep
their first observed framebuffer and report in a separate `failures/` folder.

The canonical report is
`references/generated/visual_polish_v026/classes/validation.json`. It records
`passed: true` and the exact ROM hash only when all three routes complete.
Actual screenshots and GIFs belong to its `runtime/` subdirectory. These are
emulator results; physical Chromatic rendering remains a separate console
check.

The final ordinary three-class suite passed on ROM SHA256
`fe80c80dee9ef2926c906e2ac18d36a2ce16dc1bd92291cf1dd54ebe58c523f5`.
It observed all 12 world direction/pose combinations per class and five
real combat casts: three physical actions, Lightning Bolt and Shadow Bolt.
The 49 guarded rear uploads preserved the protected graphics and HUD regions.
All six selection previews matched their actual palettes and completed LCD
pixels; all three cold saved-name displays matched the stored name and bold
glyph pixels. The first candidate's stale CGB preview attributes were caught
by the framebuffer check and corrected before this passing run. Those earlier
captures remain separate in `preliminary_fb9a8fbe/`. The earlier passing
`0799c314` and `98e09e48` capture/report sets are retained in their respective
`preliminary_0799c314/` and `preliminary_98e09e48/` folders. The canonical
report and `runtime/` captures use the final physical-OAM-corrected ROM above.
