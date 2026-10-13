# Browser player v0.2.10

[Download the self-contained player](https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/main/releases/browser-player-v0.2.10/peon_of_warcraft_v0_2_10_player.zip).
Extract and open `peon_of_warcraft_v0_2_10_player.html` in Chrome/Edge, then click
Jouer. Arrow keys move, Z = A, X = B, Enter = START and Shift = SELECT.
Touch controls are also available.

Inside the game, EXIT returns to the title. Release A, then press START to open
character selection. Continue resumes the last native SAVE. B closes the menu;
EXIT does not save new progress. A held confirmation cannot bypass the title.

Use Start → SAVE and Exporter .sav to transfer the 32 KiB battery save. A
complete session checkpoint belongs to this exact ROM; an old reader's session
cannot upgrade it. The emulated clock advances during play and pauses while
closed. Raw `.sav` files do not contain RTC metadata.

All three ordinary class routes, EXIT/held-input/title checkpoint, native Save,
cold Continue, audio, keyboard, touch and repeated engine resets pass under
managed Chromium over HTTP. The final ROM SHA-256 is
`0e2d747636788211b9a046df698ef9fecdafd1166e0514381815fd88ed22bb66`.
Evidence is in `references/generated/browser_player_v0210/`.

Local double-click opening, Safari/iPhone and the Codex in-app browser have not
been verified here. If local opening is refused, run
`python -m http.server 8765` from the extracted directory and open
`http://localhost:8765/peon_of_warcraft_v0_2_10_player.html` on that same computer.

The prepared `gh-pages` branch requires the repository owner's GitHub Settings
→ Pages → Deploy from a branch → gh-pages → /(root) activation. Raw GitHub HTML
URLs download a file; they do not run it as a website. Hosting remains unverified.

This independent GBC player does not emulate the Chromatic FPGA or a DevDay
cartridge. No physical cartridge has been programmed. The new PNG/class-master
art proposals are a separate downloadable pack and are not integrated here.
