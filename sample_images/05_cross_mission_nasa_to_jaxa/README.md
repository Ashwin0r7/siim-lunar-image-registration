# Cross-mission: an LRO NAC frame onto a Kaguya (JAXA) ortho map

Different agency, spacecraft, camera and decade; the Kaguya map is controlled by its own network and photometrically normalised. The pixel-size ratio between the two uploads is about 2:1 after the card's own down-sampling.

## Files

- `A_source_nac_i45.png` — LRO NAC, `nac.m1212932972lc`, 512 × 1024 px, ~4.34 m/px, incidence 45.48°
- `B_reference_kaguya_tc_8m.png` — SELENE (Kaguya) TC Ortho Map Seamless V2.0, `TCO_MAPS02_N21E021N18E024SC`, 383 × 635 px, ~8.423 m/px

## How to use it

Open the live card, drop `A_*` as the source and `B_*` as the reference, keep engine **B1**, and run.

## What the live card returned on these exact files

**INCONCLUSIVE / moderate** — 455 inliers

Registered image emitted: **yes**.

> No evidence against, but the decisive check (loop closure) was not run. A self-consistent wrong answer cannot be excluded from a single image pair -- supply a third overlapping image to settle it.

Recorded stage evidence for the same ground: EXP-019 arm R: this tile registers to the reference with 474 inliers (B1).

This is a **live** result, measured by `scripts/build_sample_images.py` through the demo's own endpoint. It is not a recorded stage number, and VERIFIED means *corroborated by the named evidence*, never *correct*.
