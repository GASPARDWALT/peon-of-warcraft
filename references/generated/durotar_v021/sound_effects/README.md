# Native Warcraft-inspired sound effects

[Open the portable listening gallery](index.html). Extract the asset ZIP and open
this file locally to listen in a browser. No autoplay or server is required.

These are original Game Boy pulse/noise imitations of the requested sound
categories. Direct access to the supplied [Wowhead Classic sound catalog](https://www.wowhead.com/classic/sounds)
was rejected by the network proxy. No Wowhead sample was heard or copied, and
these previews must not be represented as exact Blizzard sound recordings.

| Preview | Use | Measured duration |
| --- | --- | --- |
| [mace_bonk.wav](mace_bonk.wav) | Wood-and-metal mace impact / BONK | 13 frames / 0.22s |
| [lightning_bolt.wav](lightning_bolt.wav) | Lightning charge, crack and electric tail | 33 frames / 0.55s |
| [firebolt.wav](firebolt.wav) | Flame ignition, fiery rush and low impact | 23 frames / 0.38s |
| [poison.wav](poison.wav) | Short bubbling toxic hiss | 17 frames / 0.28s |
| [scorpid_sting.wav](scorpid_sting.wav) | Quick piercing sting with a dry click | 10 frames / 0.17s |
| [coins.wav](coins.wav) | Two small metal coin chimes | 13 frames / 0.22s |
| [menu.wav](menu.wav) | Quiet tactile menu click | 6 frames / 0.10s |
| [leather_bag.wav](leather_bag.wav) | Leather flap and soft strap rustle | 15 frames / 0.25s |

The WAVs record actual emulator APU output and are normalized individually
for listening. Native menu/bag volume remains deliberately softer than spell
impacts. All effects use finite pulse/noise sequences and existing SFX IDs;
they do not add streamed PCM or change save storage.

## Validation scope

`tools/validate_peon_sfx.py` runs each existing effect ID through the actual
PlaySFX engine using a labeled temporary diagnostic CALL and register argument
hook. It observes the expected native channel data, records sound, verifies
termination and checks that background title music resumes afterward.

A separate ordinary-button new-game test observes the opening BONK without
changing calls, arguments, RAM or save states. Its mixed game recording is
[bonk_in_opening.wav](bonk_in_opening.wav). The production ROM and user saves
are never changed by the diagnostic captures.

The same ROM hash is recorded in `validation.json`. Physical Chromatic audio
and exact identity with any original WoW sample remain unverified.

Regenerate native effect definitions with `python tools/build_peon_sfx.py`,
rebuild the ROM, then run `tools/validate_peon_sfx.py` with PyBoy available.
