# Native v0.2.2 ambient soundtrack

These listening previews are recordings of the ROM's emulated Game Boy Color
APU, captured at 48 kHz in stereo. They contain original four-channel
compositions, not imported World of Warcraft recordings.

| File | Native use | Form |
| --- | --- | --- |
| `durotar_native.wav` | The Den, Valley of Trials and Sen'jin Village | 128-tick loop |
| `cave_native.wav` | Burning Blade Cavern | 128-tick loop |
| `battle_native.wav` | Warcraft enemy encounters | 128-tick loop |
| `inn_native.wav` | Orc/troll huts and inns | 128-tick loop |
| `victory_native.wav` | Victory fanfare | 32 ticks, then all four channels stop |
| `barrens_native.wav` | Durotar Road and Razor Hill | 128-tick loop |
| `orgrimmar_native.wav` | Orgrimmar Gate | 128-tick loop |

The six looping previews contain one complete phrase. Playback gain is
normalized for listening; the ROM's original channel volumes remain unchanged.
The PNG waveforms show the recorded audio, while the map PNGs are actual native
160×144 emulator captures.

`validation.json` records the tested ROM hash, channel activity, real music
bytecode phrase addresses, synchronized loop periods and finite fanfare ending.
Isolated sound tests replace the requested title song ID at the native
`PlayMusic` entry, explicitly as diagnostic inputs. The separate playable route
uses ordinary controls with no RAM edits or saved emulator states, including a
real boar battle and victory. All seven score IDs are selected and decoded by
the native game engine.

Crystal temporarily reuses `wMusicID` for cries and sound effects. The validator
therefore verifies current map music through `wMapMusic`, the four active
channels' real banks/pointers, and `PlayMusic`/`_PlayMusic` calls, rather than
assuming that temporary word always identifies the background score. Physical
Chromatic audio output has not been measured.
