# Final world-actor performance check

`validation.json` is the aggregate result with status PASS and the exact ROM SHA256. It links the candidate evidence, copied native v14 baseline, and native LCD screenshots. The baseline copy is an earlier verified read-only run, not a new execution.

Normal GBC CPU speed, ordinary buttons and fresh private ROM copies; no RAM edits, state loads or user batteries. The 240-frame Den sample and four steps pass. Idle cadence is the same as v14: 60 updates per 240 LCD frames, with median 159388 versus 159766 Tcycles. The four movement latencies are 49/48/53/54 versus 45/48/41/41 LCD frames: cumulative 16.57% higher.

The bounded lodge test also passes: 36 visible OAM cells, at most 6 on one scanline, all 27 master cells plus all 9 hero cells. Source VRAM, masks and actual native LCD pixels are exact; the optional HUD is omitted whole. No bank/index leaks or idle graphics uploads are observed.

No further source changes are proposed. `probe.py` is the exact final instrumentation, using ordinary controls and read-only hooks.
