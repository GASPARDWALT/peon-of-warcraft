# Missing Earth Elemental — v0.2.12

This monster is newly generated under the user’s authorization to complete missing PNGs. It was absent from the supplied character packs. Original boar, scorpid, imp and approved Shaman artwork supplied style references; none were changed. The generation master and prompt are preserved in `originals/`. This is a lossy raster conversion, not recovery of an exact generated native grid or an extraction of user-provided elemental pixels.

The six complete source silhouettes are cropped at the coordinates in `manifest.json`. Alpha >=128 becomes255; lower alpha becomes0. Nearest-neighbor aspect fitting centers each pose inside a one-pixel transparent border: four16×16 world directions,56×56 combat front and48×48 true combat rear. Separate hardware packets use RGB555 source medoids, three opaque colors per8×8 BG tile and two palette families. World OBJ uses exactly three opaque colors. Three frame slots repeat each canonical pose; there are no manually drawn circles, polygons, extra silhouettes or invented attack poses.

Hardware previews are authored-asset projections, not running-ROM evidence. Engine bindings and build integration are separate. Reproduce with `python3 tools/import_peon_earth_elemental_v0212.py`.
