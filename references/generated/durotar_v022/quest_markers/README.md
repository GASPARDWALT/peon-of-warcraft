# Native region quest points — v0.2.2

Four quest givers appear on discovered pages: The Den Foreman, Galgar, Hana'zua and Zureetha. Yellow `!` means offered, gray `?` means active, yellow `?` means ready to turn in. Completed points disappear.

Two transparent native 8×8 OBJ glyphs reuse palettes4 and7 for three visible states, without changing the full-color BG atlas. Public glyph PNGs are RGBA; the internal compiler PNG is opaque indexed grayscale.

Static previews are compiler reconstructions. Actual ROM captures and explicitly labelled diagnostic availability/fog checks are saved by `validate_peon_atlas_quests.py`.
