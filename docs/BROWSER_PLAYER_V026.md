# Browser player v0.2.6

[Download the standalone reader](https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/main/releases/browser-player-v0.2.6/peon_of_warcraft_v0_2_6_player.zip).
Extract it, open `peon_of_warcraft_v0_2_6_player.html` in Chrome or Edge,
and click **Jouer**. The single HTML includes the ROM, MIT-licensed binjgb
core, WebAssembly and native audio, without external runtime downloads.

Arrows move; **Z** confirms; **X** cancels; **Enter** is Start; **Shift** is
Select; **Space** pauses. Touch controls support narrow screens. Save in the
game with **Start → SAVE**, then use **Exporter .sav** to transfer the
32 KiB battery. Full-session JSON checkpoints preserve the current frame
and emulated clock; they are distinct from the game's battery save.

To migrate from the v0.2.5 reader, import its exported `.sav`. Its old
full-session JSON is rejected because the native ROM differs. Automatic
sessions stay local to the browser/origin: export before changing device
or clearing site data. The clock advances during emulation and pauses
while closed; `.sav` excludes RTC.

## Hosting in Codex's in-app browser

The `gh-pages` branch contains the tested v0.2.6 reader as `index.html`.
The repository owner must enable [GitHub Pages](https://github.com/GASPARDWALT/peon-of-warcraft/settings/pages):
**Deploy from a branch → gh-pages → /(root) → Save**. After GitHub confirms
deployment, the expected URL is `https://gaspardwalt.github.io/peon-of-warcraft/`.
Hosting was not enabled or verified by this cloud task: the Pages settings
API is unavailable to its scoped credentials. A raw GitHub ZIP or HTML URL
downloads a file rather than running a hosted game.

Local double-click opening and the user's in-app display were not tested.
The managed cloud browser blocks `file://`; tests use permitted HTTP.
If local opening fails and Python is installed, serve the extracted folder
on your own computer with `python -m http.server 8765`, then open
`http://localhost:8765/peon_of_warcraft_v0_2_6_player.html` on that computer.
Safari/iPhone and a physical gamepad remain untested.

## Evidence and limits

The embedded ROM is the delivered v0.2.6 binary:
`fe80c80dee9ef2926c906e2ac18d36a2ce16dc1bd92291cf1dd54ebe58c523f5`.
Reports and screenshots are in `references/generated/browser_player_v026/`.
All three class routes are exercised through real browser buttons, native
SAVE, separate-context battery Continue, checkpoint reload, audio, touch,
pause, keyboard and 390/320-pixel layouts. The core additionally checks
MBC3 SRAM/RTC and twelve complete emulator allocation/destruction cycles.
Input hashes are checked again before reporting PASS. No external runtime
requests or JavaScript errors are permitted by the packaging gate.

This is an independent GBC emulator, not a Chromatic FPGA or DevDay
cartridge emulator. No ModRetro plugin or physical hardware was used.

```sh
python3 tools/build_peon_browser_player.py --version 0.2.6 --expected-sha ROM_SHA
python3 tools/validate_peon_browser_player.py --version 0.2.6 --class shaman \
  --html releases/browser-player-v0.2.6/peon_of_warcraft_v0_2_6_player.html \
  --output references/generated/browser_player_v026 --expected-sha ROM_SHA
python3 tools/build_peon_browser_player.py --version 0.2.6 --expected-sha ROM_SHA --package
```

Packaging also needs the matching passing core/lifecycle reports from
`tools/validate_peon_browser_core.js`. Keep the old releases unchanged.
