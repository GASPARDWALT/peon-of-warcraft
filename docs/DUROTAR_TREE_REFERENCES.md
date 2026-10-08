# Prepared Durotar trees

These are original pixel-art proposals for the current Durotar direction.
They are **not integrated into the ROM**, and the contact sheet is not an
emulator capture. No map, collision, palette table or existing tileset is changed.

## Repository references inspected

The following actual PNG/JPG files were visually inspected together:

- `references/zones/the_den/the_den_primary_reference.png`: orange terrain,
  a broad dry tree near the settlement, and open space around the building.
- `references/zones/valley_of_trials/valley_of_trials_inspiration_01.png`:
  the enclosed canyon geography and a sparse, dry valley.
- `references/zones/valley_of_trials/valley_of_trials_inspiration_03.png`:
  the pixel-art direction with branching dead trees, cacti and cliff edges.
- `references/zones/senjin_village/Capture d'écran 2026-10-07 143025.png`:
  the position of Senjin between the dry mainland and the coast.
- `references/zones/senjin_village/yvt8ladwa0m21.jpg`: the open coastal
  terrain and the village's relationship to the beach.
- `references/zones/senjin_village/images.jpg`: the palms beside the troll
  building and their narrow trunks beneath open fronds.

`references/zones/Durotar/durotar.webp` was found, but Pillow could not decode
its WebP container. It was not visually inspected or used to claim a specific
tree silhouette. The valid PNG/JPG references above supplied the art direction.

## Files and intended placement

All outputs are in `references/generated/warcraft_audio_update/trees/`:

| Transparent PNG | Native size | Intended use |
| --- | --- | --- |
| `deadthorn_tree.png` | 32×32 | Dry Valley cliff shoulders and canyon edges |
| `crooked_acacia.png` | 32×32 | Occasional tree near The Den or a widened canyon |
| `coastal_palm.png` | 32×40 | Senjin beach edge and coastal troll buildings |

Each has an `_8x.png` enlargement using nearest-neighbour sampling.
`durotar_trees_contact_sheet.png` displays the three proposals over a checker.
`manifest.json` records dimensions, colour counts, alpha values and hashes.

Keep trunks away from doors, quest markers, hostile trigger cells and mandatory
roads. Use sparse isolated trees rather than a forest: the canyon remains the
main silhouette of inland Durotar, with palms identifying the coast. Placement
coordinates and collisions must be decided against the final zone paths before
integration. These proposals do not change the requested seven-screen layout.

## Native constraints and integration work

The assets use four opaque RGB colours plus binary transparency, authored at
native resolution with no antialiasing. Their outlines and small colour clusters
follow the readability of a Crystal-style world while retaining Warcraft's dry
branches, leaning trunks and sparse canopies.

The present native background budget remains **192 distinct 8×8 tiles**, split
across the existing VRAM banks. These proposals do not allocate extra tiles.
A 32×32 source occupies at most sixteen 8×8 cells; the palm's 32×40 canvas
occupies at most twenty. Transparent cells and duplicated patterns can reduce
that cost, but actual reuse has not been implemented or claimed.

A GBC background tile has four colour indices including its ground colour.
Prepared RGBA transparency must therefore be baked into the region ground
palette, with colour reduction or multiple palette-controlled tiles as needed.
A GBC object instead has three visible colours plus transparent index zero;
these four-colour proposals require reduction before use as objects. Grouping
trees into large objects would also spend OAM entries, so background tiles are
the preferred integration path. New tree tiles must replace/reuse existing
decorative patterns or pass an explicit budget review before allocation.

Run `python tools/build_peon_durotar_trees.py` to reproduce the art. The builder
checks native sizes, at most four opaque colours and alpha values exactly 0/255.
It writes only the new trees directory; no native compile is part of this step.
