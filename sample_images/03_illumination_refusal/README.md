# 39.8 deg of Sun change: the verdict refuses, and draws nothing

The same ground at incidence 29.95 deg and 69.76 deg. Long shadows change what the surface looks like; the system must say REJECTED and withhold the registered image rather than draw a plausible-looking wrong alignment.

## Files

- `A_source_nac_i30.png` — LRO NAC, `nac.m1271742202lc`, 512 × 1024 px, ~3.72 m/px, incidence 29.95°
- `B_reference_nac_i70.png` — LRO NAC, `nac.m1335207975rc`, 512 × 1024 px, ~3.66 m/px, incidence 69.76°

## How to use it

Open the live card, drop `A_*` as the source and `B_*` as the reference, keep engine **B1**, and run.

## What the live card returned on these exact files

**REJECTED / none** — 4 inliers

Registered image emitted: **no**.

> Too few verified correspondences: 4 (threshold 8). Near the model's degrees of freedom, a fit can match its own points exactly while being catastrophically wrong.

> Correspondences are clustered: 0.557 of the overlap has no nearby constraint, so the alignment is extrapolated there even if it is accurate where the points are.

Recorded stage evidence for the same ground: REAL-DATA-07: 0 of 3 engines register this pair; EXP-021 labels B1's estimate WRONG by 145-356 m on the related RD04 edges into this frame.

This is a **live** result, measured by `scripts/build_sample_images.py` through the demo's own endpoint. It is not a recorded stage number, and VERIFIED means *corroborated by the named evidence*, never *correct*.
