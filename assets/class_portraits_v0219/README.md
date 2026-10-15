# Approved illustrated class-master sources v0.2.19

The three PNGs are byte-identical copies of separate approved image-generation results. They are generated illustrations, not recovered native artwork or user sprite extraction.

- `kento_corrected_horns_source.png`: use only the LEFT bust; both horns are attached to the Tauren skull and the lowered staff remains separate.
- `zogzog_garrosh_brown_source.png`: use only the MIDDLE bust; MoCMoc Zogzog follows the requested bald brown Garrosh appearance, tusks, scar and iron/red armor. The player Warrior is unaffected.
- `bismillah_original_source.png`: use only the RIGHT bust from the initial atlas; the approved undead Warlock remains unchanged by the later Tauren/Warrior edits.

The importer selects the complete alpha-connected component identified by that role. It never cuts weapons or horns at equal-third panel boundaries, never uses the neighboring unapproved characters, and checks the three approved source SHA256 digests. Originals and v0.2.18 artwork are preserved.
