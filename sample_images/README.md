# Real lunar sample images for the live card

Real images from real archives, cut by `scripts/build_sample_images.py` and
ready to drop into the demo's live registration card
(`python scripts/run_demo.py --port 8017 --strict-port`, then the **Live** card).

| scenario | what it shows | what the live card returned |
|---|---|---|
| [`01_pair_registers_small_sun_change`](01_pair_registers_small_sun_change/README.md) | Same ground, small Sun change: the pair registers | **INCONCLUSIVE** / moderate |
| [`02_triplet_reaches_VERIFIED`](02_triplet_reaches_VERIFIED/README.md) | Three overlapping frames: the only path on the page to VERIFIED | **VERIFIED** / moderate |
| [`03_illumination_refusal`](03_illumination_refusal/README.md) | 39.8 deg of Sun change: the verdict refuses, and draws nothing | **REJECTED** / none |
| [`04_held_out_site_triplet`](04_held_out_site_triplet/README.md) | Held-out ground (Mare Tranquillitatis): VERIFIED on a site no threshold was tuned on | **VERIFIED** / moderate |
| [`05_cross_mission_nasa_to_jaxa`](05_cross_mission_nasa_to_jaxa/README.md) | Cross-mission: an LRO NAC frame onto a Kaguya (JAXA) ortho map | **INCONCLUSIVE** / moderate |
| [`06_unrelated_ground_must_refuse`](06_unrelated_ground_must_refuse/README.md) | Wrong ground on purpose: the system must refuse | **REJECTED** / none |

Every result in the right-hand column was produced by posting these exact
files to the demo's own endpoint when the folder was built
(`manifest.json` → `live_check`). The files are **16-bit PNG**, north-up and
east-right. `manifest.json` records, per file, the product, the tile window,
the decimation, the orientation applied, the SHA-256 and the linear map from
the stored value back to reflectance.

**Credits.** LRO NAC: NASA/GSFC/Arizona State University. SELENE (Kaguya) TC:
(c) JAXA/SELENE, produced by LISM, distributed by JAXA/ISAS DARTS.
**Chandrayaan-2** images are *not* in this folder: PRADAN products are
"(c) reserved ISRO". Running the build script on a machine that has the
PRADAN download writes a TMC-2 → NAC scenario into `_local_chandrayaan2/`,
which git ignores.
