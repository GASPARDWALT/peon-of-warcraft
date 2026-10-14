# Mini-zone native portal QA

Final evidence: `attempt_02/validation.json`, `summary.json`, and 81 actual native 160×144 screenshots (each also has a nearest-neighbor 4× copy).

The exact frozen ROM was `/tmp/peon-v0213-frozen/peon_v0213.gbc`, SHA-256 `6cf84242e9a518af635fe9e2138f7f60228de2d0da7b4ee12ba7511f814f88e8`, with its matching `.sym`. The session cold-booted an isolated temporary ROM copy and selected a fresh Shaman through the actual menus. No RAM edits, CPU substitution, emulator states, user saves, or batteries were used. The private session was closed with `save=False`.

Twenty required crossings cover both lanes at every endpoint of Valley↔Crossroads, Crossroads↔Hana'zua, Hana'zua↔Sarkoth, Sarkoth↔The Den, and Crossroads↔Cave Approach. Six additional crossings provide ordinary routing. All 26 landings use the published destination indices, followed by an ordinary step to native `FLOOR` with no re-warp. All 78 stationary approach/arrival/egress observations passed the read-only allocator checker, including actual VRAM packets, PPU priority bits, and live OAM overlap checks.

Sarkoth was not defeated; the eastern basin endpoint was reached through the world loop via The Den. Cave Approach movement stayed at rows 8–9 below the imps. No battle triggered. Eastern road and cavern-interior checks belong to the other QA session.

`button_qa.py` is an artifact-only interactive harness. `commands.jsonl` preserves its exact sequence of high-level ordinary walking commands; `validation.json` records all 306 button operations and their frame counts. To repeat, select an unused attempt folder in the artifact harness, preserve existing evidence, and run with `PYTHONPATH=/workspace/toolchains/pyboy-preview`, feeding `commands.jsonl` to stdin.

`attempt_01` retains a harness timing diagnostic: a four-frame final portal tap changed facing without walking. The final clean run began again from a new private ROM and used the established 30-frame final entry tap. This was not a game warp failure.
