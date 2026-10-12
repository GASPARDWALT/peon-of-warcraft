# Browser player v0.2.7

[Download](https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/main/releases/browser-player-v0.2.7/peon_of_warcraft_v0_2_7_player.zip).
Extract, open `peon_of_warcraft_v0_2_7_player.html` in Chrome/Edge and click
**Jouer**. The intro includes the new palm. Controls: arrows, Z/A, X/B,
Enter/Start, Shift/Select, Space/pause. Touch controls are also tested.

Save with Start → SAVE, then export `.sav` to transfer your game. Import an
older `.sav` to Continue. Full-session checkpoints use this version's ROM
hash and cannot upgrade an older reader session. The emulated RTC advances
during play and pauses while closed; raw `.sav` excludes RTC.

All three ordinary browser routes, actual battery saves/cold Continue,
session restore, audio and desktop/mobile layouts pass. Exact ROM hash:
`4a1fa7ff7e744cd8ca656e57491f21ef32b3ea515c0af784b5878802446a9a8a`.
Evidence: `references/generated/browser_player_v027/`.

The `gh-pages` branch hosts the latest prepared reader. To activate hosting,
the owner chooses GitHub Settings → Pages → Deploy from a branch → gh-pages
→ /(root) → Save. Publishing that branch alone does not activate the site.
The hosting configuration and actual in-app display remain unverified.

This independent GBC reader does not use the ModRetro plugin or certify
DevDay/Chromatic hardware. Local double-click, Safari/iPhone and physical
gamepads were not tested. Tests use permitted HTTP in managed Chromium;
the cloud's file-URL policy is preserved. See
[previous browser instructions](BROWSER_PLAYER_V026.md) for the local HTTP
fallback and hosting details, using this version's HTML filename.
