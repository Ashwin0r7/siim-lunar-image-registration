# Three overlapping frames: the only path on the page to VERIFIED

Upload all three (image A, B and the optional third). The three edges are estimated independently and composed around the loop; VERIFIED is returned only when the loop closes under the frozen 2.0 px line.

## Files

- `A_nac_i18.png` — LRO NAC, `nac.m1299958135lc`, 512 × 1024 px, ~4.28 m/px, incidence 18.22°
- `B_nac_i21.png` — LRO NAC, `nac.m1315225542lc`, 512 × 1024 px, ~3.22 m/px, incidence 21.13°
- `C_nac_i30.png` — LRO NAC, `nac.m1271742202lc`, 512 × 1024 px, ~3.72 m/px, incidence 29.95°

## How to use it

Open the live card, drop the files in order into **A**, **B** and the optional **third image**, keep engine **B1**, and run.

## What the live card returned on these exact files

**VERIFIED / moderate** — loop closure 0.067 px

> Correspondences are clustered: 0.174 of the overlap has no nearby constraint, so the alignment is extrapolated there even if it is accurate where the points are.

> Loop closure agrees, but coverage is weak: trust the alignment near the correspondences more than far from them.

Recorded stage evidence for the same ground: EXP-012 primary triplet R4-6 (VERIFIED on all three edges).

This is a **live** result, measured by `scripts/build_sample_images.py` through the demo's own endpoint. It is not a recorded stage number, and VERIFIED means *corroborated by the named evidence*, never *correct*.
