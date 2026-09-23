# Wrong ground on purpose: the system must refuse

The same NAC frame against a Kaguya crop at least 25 km away. There is no correct answer, so any pass would be a false acceptance.

## Files

- `A_source_nac.png` — LRO NAC, `nac.m1212932972lc`, 512 × 1024 px, ~4.34 m/px, incidence 45.48°
- `B_unrelated_kaguya_25km_away.png` — SELENE (Kaguya) TC Ortho Map Seamless V2.0, `TCO_MAPS02_N21E021N18E024SC`, 383 × 635 px, ~8.423 m/px

## How to use it

Open the live card, drop `A_*` as the source and `B_*` as the reference, keep engine **B1**, and run.

## What the live card returned on these exact files

**REJECTED / none** — 4 inliers

Registered image emitted: **no**.

> Too few verified correspondences: 4 (threshold 8). Near the model's degrees of freedom, a fit can match its own points exactly while being catastrophically wrong.

> Correspondences are clustered: 0.628 of the overlap has no nearby constraint, so the alignment is extrapolated there even if it is accurate where the points are.

Recorded stage evidence for the same ground: EXP-019 arm N: 0 of 21 null cells pass; EXP-021 validation null: 0 of 7.

This is a **live** result, measured by `scripts/build_sample_images.py` through the demo's own endpoint. It is not a recorded stage number, and VERIFIED means *corroborated by the named evidence*, never *correct*.
