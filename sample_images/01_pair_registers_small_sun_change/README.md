# Same ground, small Sun change: the pair registers

Two LRO NAC frames of Mare Serenitatis 11.7 deg apart in incidence. The pair path cannot exceed INCONCLUSIVE on its own, and says why: loop closure needs a third image.

## Files

- `A_source_nac_i18.png` — LRO NAC, `nac.m1299958135lc`, 512 × 1024 px, ~4.28 m/px, incidence 18.22°
- `B_reference_nac_i30.png` — LRO NAC, `nac.m1271742202lc`, 512 × 1024 px, ~3.72 m/px, incidence 29.95°

## How to use it

Open the live card, drop `A_*` as the source and `B_*` as the reference, keep engine **B1**, and run.

## What the live card returned on these exact files

**INCONCLUSIVE / moderate** — 926 inliers

Registered image emitted: **yes**.

> No evidence against, but the decisive check (loop closure) was not run. A self-consistent wrong answer cannot be excluded from a single image pair -- supply a third overlapping image to settle it.

Recorded stage evidence for the same ground: REAL-DATA-07 rows_rd04_nue.json, B1: 1608 inliers on this edge.

This is a **live** result, measured by `scripts/build_sample_images.py` through the demo's own endpoint. It is not a recorded stage number, and VERIFIED means *corroborated by the named evidence*, never *correct*.
