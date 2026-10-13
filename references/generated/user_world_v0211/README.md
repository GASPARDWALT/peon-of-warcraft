# Canonical NPC source import

Each preview shows the selected supplied 16×16 PNG on the left and the decoded native 2bpp conversion on the right. These are static import previews, not ROM captures. Original PNG geometry and binary alpha remain intact. The native engine permits three opaque colors per OBJ, so color reduction is explicitly lossy.

`source_fidelity_report.json` records every requested original, selected source hash, damaged-crop fallback, palette choice and color-error measurement. Fallbacks copy complete existing canonical PNGs; no procedural repair or ASCII sprite drawing is imported. The enemy Warlock front remains a documented left-view fallback because its supplied frontal crop is an equipment sliver.

All eight shared OBJ palettes remain unchanged. SPRITE_SAGE uses the four intact troll_shaman views. The Shaman Apprentice packet is exported as PeonUserShamanApprenticeWorldV0211, palette2, and requires an explicit sprite-table binding. More than one palette per actor requires a separately coordinated engine change; no OAM entries, tile budgets, save fields or sprite IDs changed.
