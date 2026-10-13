# Recruit and enemy art in v0.2.9

The six sets are original native pixel drawings: Earth Spirit, red Imp, Orc
Grunt, hostile Orc Warlock, Kolkar Archer and Kolkar Raider. The Orcs wear modest
equipment; the Kolkar have a humanoid torso and four-legged centaur silhouette.
The playable Peon's three apprentice class sets remain the v0.2.8 artwork.

Editable source generation is in `tools/build_peon_recruit_assets_v029.py`.
All public visual files are under
`references/generated/recruitment_v029/assets/`, including 288 PNGs with binary
transparency, 36 APNG motion previews and 36 GIF previews. The additional
`six_recruit_enemy_sets_paper_review.png` is an opaque review background.
Enlarged files use nearest-neighbor scaling; they are not additional native
detail or additional ROM frames.

Each set has twelve authored 16×16 world poses, three 56×56 front poses, three
48×48 back poses and 8×8 / 16×16 heads. Three transparent recruitment item icons
show the Elemental Relic, Domination Skull and Rally Horn; a fourth shows Tough
Jerky. The motion sheets and previews are source artwork until actual native
rendering has been checked.

`tools/build_peon_native_recruits_v029.py` converts these exact indices into
native dictionary packets and checks every front-frame roundtrip. It writes
only the new `gfx/peon_native_v029/` directory and source evidence. The stable
species bindings are:

| Native ID | Role | Front dictionary | Back allocation |
| --- | --- | --- | --- |
| ONIX (95) | Earth Spirit | 89 tiles | 36 tiles |
| GEODUDE (74) | Imp | 77 tiles | 36 tiles |
| MACHAMP (68) | Orc Grunt | 93 tiles | 36 tiles |
| GRIMER (88) | hostile Orc Warlock | 87 tiles | 36 tiles |
| PONYTA (77) | Kolkar Archer | 79 tiles | 36 tiles |
| RAPIDASH (78) | Kolkar Raider | 82 tiles | 36 tiles |

All six dictionaries fit Crystal's two 7×7 allocations, so these sets need no
overflow tail. The generator rejects a future change that exceeds 98 tiles.
The normal and shiny entries use the same authored middle RGB555 colors; native
white and black endpoints stay intact. The picture pointers keep their original
species IDs and public labels while the packets use floating ROM banks. Their
stored bank byte is resolved through the existing Peon raw-bank adapter.

Ordinary NPC sprites consume six 16×16 frames: idle Down/Up/Left followed by
walking Down/Up/Left. The converter extracts phase-major authored frame indices
`0, 1, 2, 4, 5, 6`. Right uses Crystal's ordinary horizontal mirror of Left;
the second Down/Up foot step also uses its native mirror. The additional
independently drawn right and second-foot source frames remain reusable source
art. They are not claimed as extra frames in this six-frame NPC format. The
smaller friendly Imp follower retains its separately authored v0.2.6 world
packet; its recruit backpic is the larger v0.2.9 picture.

`tools/validate_peon_recruit_art_v029.py` accepts an explicit ROM, symbols and
expected SHA. Linked-only checks read the frozen ROM's actual pointers,
compressed packets, decompressed data, palette table and five NPC packets;
their report is `runtime_art/linked_packets_validation.json`. They establish
compiled bindings, not gameplay rendering.

The full rendering branch runs private, labelled graphics fixtures through
actual battle controls and native picture/animation routines. It checks all
three enemy poses, all three active ally back poses after native Team switching,
protected font/portrait VRAM, physical OAM scanline counts and four-direction
world motion. Those fixtures do not establish ordinary capture, quest or
progression behavior; those systems have a separate integration regression.

The native animation check also covers the attribute bank of the animated
front picture. Graphic clearing preserves its bank-one attributes instead of
calling the dialogue font-style clearer. Settled battle checks compare the
actual digits, level and HP font packet with `FontBattleExtra`, and verify every
live bold name against the source glyph and rendered RGB555 pixels. A Team
return must restore the full battle font, including the tiles that its menu
temporarily reuses. Correct creature pixels alone do not pass these UI checks.

The optional populated Sen'jin check continues a copied private Warlock battery
with Sarkoth's report completed. It retains the real map objects and living
follower, checks both extra nodes, walks around their area and measures actual
native tile reservations and OAM pressure. This is separate from the isolated
one-NPC source-fidelity fixtures. Runtime reports and screenshots belong under
`references/generated/recruitment_v029/runtime_art/`. Physical cartridge testing
remains a separate step.

`runtime_art/final_runtime_gallery_manifest.json` lists the exact final-ROM
screenshots and motion previews with hashes. Its fourteen rendering cases are
explicitly labelled private graphics diagnostics; a populated Sen'jin scene is
included only after its separate ordinary-save check passes. Gallery consumers
should use this list rather than scanning old diagnostic folders. Earlier bug captures stay under
`preliminary_legacy_diagnostics/` and do not belong to the final gallery.
