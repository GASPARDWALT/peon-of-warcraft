# Peon of Warcraft — v0.2.3

Extract `peon_of_warcraft_v0_2_3.zip` and open the `.gbc` in a GBC emulator.
This patch retains the Shaman chapter and improves player movement in battle
and encounter attrition. Its measured balance and methods are recorded in
the included movement/balance reports and `docs/V023_COMBAT_BALANCE.md`.

Move with the D-pad, confirm/interact with A and cancel with B. Start opens
CHARACTER/BAGS/MAP/SAVE/HEARTHSTONE; Select opens the earned zone map. The game
keeps one real save and four attacks. The reusable Earth Totem is placed from
battle BAGS, outside those attack slots. Bring potions and use inns deliberately;
victory does not heal automatically. This chapter still ends at Orgrimmar Gate.

Back up the original battery save before moving it to the new ROM basename.
Keep the emulator extension `.sav`, `.srm` or `.ram`; avoid cross-version save
states. The packaged migration checks cover real prior-version batteries,
including v0.2.2. Kento does not duplicate an already owned Earth Totem, and
older characters can retry his handoff after freeing a bag slot.

Extract `peon_of_warcraft_v0_2_3_assets.zip`, then open
`durotar_v023/index.html` in Chrome or Edge. Keep all five sibling folders
together. The offline gallery provides individual downloads and distinguishes
integrated native art, prepared/locked art, concepts, diagnostic captures and
historical screenshots. The separate transparent PNG ZIP is an artwork pack,
not a promise that every prepared item or class route is functional.

The release packager refuses stale or failed reports and invalid checksums.
`validation_manifest.json` and `SHA256SUMS.txt` identify the exact packaged ROM.
**Physical Chromatic, cartridge flashing and RTC testing remain unperformed.**
The 2 MiB CGB ROM requires MBC3+RTC and 32 KiB battery SRAM support.
