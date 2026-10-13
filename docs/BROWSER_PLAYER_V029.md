# Browser player v0.2.9

[Download the browser player](https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/main/releases/browser-player-v0.2.9/peon_of_warcraft_v0_2_9_player.zip).
Extract the ZIP, open `peon_of_warcraft_v0_2_9_player.html` in Chrome or Edge,
and click **Jouer**. The HTML contains the ROM, emulator and audio support.

Controls: arrow keys to move, Z = A, X = B, Enter = Start, Shift = Select,
Space = pause. The on-screen buttons provide touch controls.

Save with **Start → SAVE**. Export `.sav` to move the native 32 KiB battery
save between versions or devices. Keep a copy of an older save before
upgrading: v0.2.9 introduces party and resource metadata that older ROMs
do not understand. Importing an old emulator session is not an upgrade;
complete session checkpoints belong to their exact ROM hash.

The emulated clock advances during play and pauses while the player is
closed. Raw `.sav` exports contain RAM without RTC metadata; full session
exports preserve the emulated clock. Export before clearing browser data.

All three ordinary class routes, native battery saves and cold Continue,
session restore, keyboard/touch controls and audio pass in managed Chromium
over HTTP. The engine also passes twelve repeated initialization/reset
cycles. Evidence is in `references/generated/browser_player_v029/`.
The exact embedded ROM SHA-256 is
`4530c718bf299ec9e1c8de8c52895906a81024345bd60717cd5c99dbd30b8a93`.

The cloud blocks `file://` URLs, so double-click opening could not be tested
here. If a local browser refuses the file, run `python -m http.server 8765`
from the extracted directory, then open
`http://localhost:8765/peon_of_warcraft_v0_2_9_player.html` on that same
computer. Safari/iPhone, the Codex in-app browser and physical gamepads
remain untested.

The `gh-pages` branch is prepared for the latest player. To activate hosting,
the repository owner opens
[GitHub Settings → Pages](https://github.com/GASPARDWALT/peon-of-warcraft/settings/pages)
and chooses **Deploy from a branch → gh-pages → /(root) → Save**.
Publishing the branch alone does not activate Pages. Use the download until
GitHub confirms hosting; a GitHub raw URL downloads HTML and does not run it.

This independent Game Boy Color emulator does not reproduce the Chromatic
FPGA or a DevDay cartridge. No physical cartridge was programmed or tested.
