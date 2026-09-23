# Held-out ground (Mare Tranquillitatis): VERIFIED on a site no threshold was tuned on

Frames from EXP-018's blind-validation window, ~800 km from the development site. Upload as A, B and the third image.

## Files

- `A_nac_i40.png` — LRO NAC, `nac.m1121081627rc`, 512 × 1024 px, ~3.42 m/px, incidence 40.06°
- `B_nac_i16.png` — LRO NAC, `nac.m1177606647lc`, 512 × 1024 px, ~3.96 m/px, incidence 16.21°
- `C_nac_i11.png` — LRO NAC, `nac.m1447850428rc`, 512 × 1024 px, ~3.54 m/px, incidence 10.88°

## How to use it

Open the live card, drop the files in order into **A**, **B** and the optional **third image**, keep engine **B1**, and run.

## What the live card returned on these exact files

**VERIFIED / moderate** — loop closure 0.556 px

> Correspondences are clustered: 0.237 of the overlap has no nearby constraint, so the alignment is extrapolated there even if it is accurate where the points are.

> Loop closure agrees, but coverage is weak: trust the alignment near the correspondences more than far from them.

Recorded stage evidence for the same ground: EXP-018 triangle, loop 1.112 px, VERIFIED on all three edges.

This is a **live** result, measured by `scripts/build_sample_images.py` through the demo's own endpoint. It is not a recorded stage number, and VERIFIED means *corroborated by the named evidence*, never *correct*.
