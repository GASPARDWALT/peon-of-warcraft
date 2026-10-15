# Native world characters v0.2.17

User correction: all world characters need genuinely authored larger pixel
drawings, not recolored or enlarged 16px silhouettes. Use the supplied designs
for identity and Pokémon Crystal map NPC proportions for readability.

Each artist owns a distinct JSON file in this directory, never existing source
PNGs. Format:

```json
{
  "version": "v0.2.17",
  "authoring": "deliberate native 24x24 pixel cells",
  "roles": {
    "orc_merchant": {
      "references": ["references/characters/peon_world_character_sheets_split/orc_merchant/orc_merchant_world_front.png"],
      "identity": "Broad green face, pointed ears, leather apron, belt and satchel",
      "palette": 2,
      "views": {
        "front": ["........................", "...23 other rows of 24 cells..."],
        "back": ["...24 rows..."],
        "left": ["...24 rows..."],
        "right": ["...24 rows..."]
      },
      "attributes": {"front": [2,2,2,2,2,2,2,2,2]},
      "walk": {"front": [["...24 rows step A..."], ["...24 rows step B..."]]}
    }
  }
}
```

Use **`.` transparent, `1` first opaque shade, `2` second opaque shade,
`3` darkest outline**. Exactly 24 rows of 24 characters per view. Attributes
are optional per direction, nine palette IDs in row-major order; absent means
the role's palette for all tiles. The optional walk poses apply only to heroes
and already animated native families; they reuse the same direction attributes.

Effective three-opaque-color palettes (RGB555):

| ID | shade1 | shade2 | shade3 |
| -- | ------ | ------ | ------ |
| 1 | green (12,17,5) | purple (16,11,17) | ink (1,1,1) |
| 2 | brown (18,11,6) | green (15,22,8) | ink (1,1,1) |
| 3 | tan (25,19,11) | brown (12,7,4) | ink (1,1,1) |
| 5 | pale (20,19,17) | blue (12,17,19) | ink (2,2,3) |
| 6 | ivory (25,23,17) | green (15,22,8) | ink (1,1,1) |
| 7 | gold (31,25,7) | red (27,5,3) | ink (2,1,1) |

Orc faces use palette6 (ivory tusks, green skin, ink); leather bodies use2.
Warlock robes retain1. Trolls/crawler use5, and crests/Imps use7. Palette6
survives the training lodge's3/4/5/7 overrides. The optional world HUD moves
mana to5 (identical old6 blue) and is omitted in that crowded lodge. Quest/HUD
palettes0/4 cannot be borrowed for bodies. These palette changes are scoped
to the Peon world, never the combat BG palettes.

Humanoid target: head about11–13px wide, distinct eyes and brows, projecting
ears, shoulders about16–20px wide, separated arms and boots, occupied height
20–23px. Profession cues must survive at1x: apron/satchel, shoulder armor/axe,
staff/necklace, worker straps/tool, troll crest/tusks. Do not derive the drawing
by nearest-scaling the old16px sprite or by raster-quantizing a large portrait.
All anatomy and contour transitions are intentionally authored pixel cells.
Keep the whole body inside24px, bottom row free where practical for walk poses.

Four directions must agree about clothing and physical equipment sides. Draw
the back and side views; do not label a front body as a missing rear view.
No generative geometric primitives, random texture, blur, alpha smoothing,
placeholder circles or rectangles. Renderer9tile/OAM budgets stay unchanged.
