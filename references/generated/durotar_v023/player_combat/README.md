# Peon rear combat poses — v0.2.3

Idle, brace/casting preparation, and physical mace follow-through. The existing 48×48 idle and equipment are retained; the new poses change the left arm, mace, shield position and tunic folds while anchoring the feet.

Native transparent PNGs use three opaque RGB555 colours plus transparency. The APNG keeps transparency; the GIF uses a presentation canvas.

`gfx/peon_player_battle/back_frames.2bpp` stores three contiguous frames, 576 bytes each, each with 36 column-major tiles. Frame offsets: 0, 576, 1152. The matching 8-byte `back_frames.gbcpal` is the unchanged current native battle palette. Internal PNGs are indexed DMG grayscale, not public art.

Rebuild assets with `python tools/build_peon_player_combat.py`. Engine integration and real battle captures are a separate step.

The separate `peon_back_pose_concept_original.png` is an image-generated concept reference. It is not native ROM artwork and does not provide the engine palette or frame data. Native frames preserve the equipped-hand orientation and are generated deterministically from the retained idle.
