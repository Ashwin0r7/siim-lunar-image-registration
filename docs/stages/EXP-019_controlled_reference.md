# EXP-019 — A reference from another mission: what the ground positions are worth when something other than the archive says where the ground is

**Part 1 — pre-registration. FROZEN 2026-09-22, before one byte of the
reference product has been fetched, before any registration against it has
been attempted, before any statistic has been computed and before the runner
exists.** Part 2 is empty until Part 1 is committed.

**Classification: DELIVERABLE-CRITICAL.** This is item **1** of
`docs/PROJECT_GAP_ANALYSIS.md` §4's corrected path that is still open (A1 and
A2 are running as EXP-016 and EXP-017; B1 landed as EXP-018), and item **1**
of the audit's own ranked list:

> **A geodetically controlled reference per frame.** … published offset
> **< 13 m ≈ 7–26 px**, against the **~100 px** archive floor everything real
> is currently corroborated against. Unblocked, needs no new mission data, and
> closes three gaps at once: the accuracy claim, EXP-013's S6, and the
> archive-vs-tile ambiguity.

Every real result in this repository is corroborated against **the same
reference**: the archive's own corner geometry, quantised at 0.01° and
measured to discriminate only at **84–116 px** (REAL-DATA-04 §11.2, EXP-013's
`edge_floor_px`). Three separate findings are limited by that one fact:

1. **The accuracy claim does not exist.** §2.2 asks for *median error on
   independent check points with a 95 % CI*; the project's 0.003 px is a
   **self-warp**, an upper bound on *precision* (§2.2 row 5, gap analysis §3.2).
2. **EXP-013's instrument cannot be deployed.** Its reference-noise
   calibration is **66.00 px**, larger than every gauge it was built to
   detect, so S6 is NOT MET at an applied gauge of zero (D-054: *built, not
   deployed*).
3. **EXP-013's H3 is unresolved by construction.** `siim.verify.gauge`'s own
   docstring: *"A per-frame bias in the archive reference has the same shape
   as a per-frame gauge in the estimate and is indistinguishable by this
   instrument."* The per-frame terms of **25–93 px** that three engines agree
   on to 1.50 px are either harmless reference error or a **real instance of
   the defect the project says it cannot rule out.**

All three are limited by the reference, not by the matcher. This stage brings
in a reference produced by **a different space agency, from a different
spacecraft, with a different sensor, in a different decade, controlled by a
different network** — and measures what changes.

---

## 0. The requirements this stage bears on, quoted

### 0.1 `MASTER_RESEARCH_AND_ARCHITECTURE_PLAN.md` §2.2, the sub-pixel row (verbatim)

> | **Sub-pixel accuracy** "of the source image" | … | median **< 0.5
> coarser-px on independent check points, with 95 % CI** |

Scored **NOT MET — no check points exist** in `PROJECT_GAP_ANALYSIS.md` §1(b).
The criterion is adopted below **verbatim as S3**, with "coarser" bound to the
reference's own 8.42 m pixel, which is what the word means in the sentence.

### 0.2 §53 criterion 2 (the project's own bar)

> ≥ 1 VERIFIED Chandrayaan-2 pair per sensor **+ check-point error / CI**

NOT MET on three named counts, one of which is *no check points*. This stage
attacks that count and, through S5, the VERIFIED-verdict count as well.

### 0.3 What this stage may NOT do to those criteria

Nothing here re-scopes, re-words or relaxes either requirement, and no bar
below moves after data exists. If S3's answer is "the bound is 11 m, not
4.2 m", the criterion stays NOT MET **and the 11 m is the deliverable's first
accuracy number**, which is a different and better thing than a pass.

---

## 1. The question

**Q.** Take the frames the project has registered a hundred times against each
other and against the archive's own corner geometry. Ask a **product from
another mission**, which was placed on the Moon by a control network this
project has never touched, where that same ground is. Then:

1. Does the frozen pipeline register a NAC frame — and the **Chandrayaan-2
   TMC-2 ortho** — to that reference at all, across a real **6.5–10.5 : 1**
   sensor scale ratio and a real photometric difference?
2. **How far is the archive's answer from the other mission's answer**, per
   frame, in metres?
3. What is the project's first **accuracy** number — an error measured against
   correspondences that pass through an instrument chain the estimate never
   used — and does it meet §2.2's 0.5-coarse-pixel bar?
4. **Are EXP-013's per-frame terms the archive, or the estimate?** The
   question its own Part 1 (H3) says the instrument cannot answer.
5. Does a triangle through the independent reference put a **Chandrayaan-2**
   edge inside the frozen 2.0 px loop-closure line?

Every outcome is a result, and the consequence of each is fixed now:

| outcome | consequence |
|---|---|
| The reference registers on most frames (S1 MET) | the project has a second, independent geodetic opinion per frame, and every later stage can use it |
| It registers on few or none (S1 NOT MET) | the cross-sensor envelope, not the reference, is the limit; the stage reports *which* frames failed against a normalised i = 30° reference, which is itself an illumination measurement |
| Archive-vs-controlled offsets are ≈ the corner quantisation (S2 MET) | the archive reference's error is **measured**, not assumed, and the ~100 px floor is explained rather than quoted |
| Offsets are far larger than the quantisation (S2 NOT MET) | something in the chain — corner convention, SPICE, or the tiles' own georeferencing — is wrong at a scale the project has been treating as noise; a defect, reported as one |
| S3's bound ≤ 0.5 reference px | §2.2's sub-pixel row is **MET on an external reference**, the first accuracy claim in the project |
| S3's bound > 0.5 reference px | the row stays NOT MET **with a number**, and that number replaces "no accuracy evidence exists" |
| S4 MET (terms track the measured archive error) | EXP-013's H3 resolves toward **reference error**; the 36/36 blind spot is *not* evidenced on real frames, D-054's detector becomes deployable against **this** reference, and the deployment path is written down |
| S4 NOT MET (they do not track) | the terms are **not** explained by archive error, i.e. a shared per-frame error in the estimates — **a live instance of the defect E-039 constructed synthetically**, and the deliverable says so |
| S5 closes < 2.0 reference px | a Chandrayaan-2 edge sits inside the frozen VERIFIED line **through an independent mission**, and §53 criterion 2 gains its first clause |
| S6 fires (any pass on the null block) | the stage's own false-accept rate is non-zero and every number above is read against it |

---

## 2. What is measured, stated exactly

### 2.1 The reference, and why it is independent

**Product:** `TCO_MAPS02_N21E021N18E024SC`, SELENE (Kaguya) Terrain Camera
**Ortho Map Seamless V2.0** (`SLN-L-TC-5-ORTHO-MAP-SEAMLESS-V2.0`), produced
by LISM, distributed by JAXA/ISAS DARTS:

```
https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-tc-5-ortho-map-seamless-v2.0/
    lon021/data/TCO_MAPs02_N21E021N18E024SC.img   (222 001 KB)
    lon021/data/TCO_MAPs02_N21E021N18E024SC.lbl
```

Read from the label, fetched 2026-09-22 **before this Part 1 was frozen** (the
label is a description of the product, not a statistic; its values are
restated here and re-verified by the runner at run time):

| property | value |
|---|---|
| projection | SIMPLE CYLINDRICAL, planetocentric, body-fixed rotating, east-positive |
| radii | 1737.400 km (sphere) |
| grid | `MAP_RESOLUTION` **3600 px/deg**, `MAP_SCALE` **0.00842315289562 km/px** |
| size | 10800 × 10800, `LINE_PROJECTION_OFFSET` 75600, `SAMPLE_PROJECTION_OFFSET` −75600 |
| extent | lat 18.000278 → 21.000000, lon 21.000000 → 23.999722 (**pixel-registered**: 2.999722° × 3600 = 10799 = 10800 − 1 pixel *centres*) |
| samples | `MSB_UNSIGNED_INTEGER` 16 bit, `SCALING_FACTOR` 0.01, `IMAGE_VALUE_TYPE` REFLECTANCE, `DUMMY` 0, valid 2 … 32766 |
| photometry | `PHOTO_CORR_ID` "USGS", `STANDARD_GEOMETRY` **(i = 30°, e = 0°, α = 30°)** |
| mosaicking | `PARAMETER_SET_NAME` `for_SCtoSCMAP_cm_craterMatchingSize-wide`, `HORIZONTAL_TRANSFORM_METHOD` "NON", `VERTICAL_TRANSFORM_METHOD` "TREND" |

**Why it is independent of everything this project has used.** Different
agency (JAXA, not NASA/ISRO), different spacecraft (SELENE, 2007–2009),
different sensor (TC, 10 m class push-broom stereo), different processing
chain (LISM DTM software 1.2), different control (LISM crater matching between
strips over the SELENE frame), different epoch, different illumination
(normalised to a **fixed** standard geometry rather than the frame's own Sun).
The only thing it shares with a NAC frame is the Moon.

**What is NOT asserted about it.** No published accuracy figure for *this*
product is quoted, because none was verified in this session. S9 of
`docs/sources.md` records the *SLDEM2015* lineage (LOLA absolute accuracy
typically < 10 m horizontally; ≈ 90 % of co-registered TC DEMs within 5 m RMS
vertically) and LROC controlled mosaics at **< 13 m**; those are the *class*
of number a controlled lunar product carries, and they are cited as context,
never as this tile's error bar. **Everything this stage reports is a
disagreement between two products, which bounds the sum of their errors and
attributes it to neither** — except where a per-frame pattern makes the
attribution testable, which is exactly S4.

### 2.2 The construction

For a source image `S` with native ground sample distance `g_S` and its tile
window `W`:

1. **Degrade to the reference GSD** — the architecture's own answer to scale
   (§19, EXP-016 arm D): `k_S = round(8.42315289562 / g_S)` and
   `degrade_to_gsd(raw, k_S, psf_fwhm_coarse_px = 1.0)`, the R9 operator
   unchanged. The residual GSD mismatch after integer `k` is ≤ **7.4 %** over
   the population and is recorded per frame; it is carried by the affine
   model, not corrected.
2. **Orient** with `north_up_east_right` through the tile's corner geometry,
   exactly as `run_real_data_07.run_edge` does, with the Jacobian-determinant
   sign recorded per frame (E-037/E-047: **`mirrored = det > 0`**, from
   `siim.ingest.orientation`, never from a session's own print label).
3. **Cut the reference** to the source's archive-predicted footprint plus a
   **2 km margin** on each side, through `MapBlock.block_xy_of_lonlat`. The
   prediction comes from archive corner geometry — a coarse prior, which is
   what a deployed system would have — and its error is the thing being
   measured, so the margin is 20× the largest plausible offset.
4. **Register** `S → R` with `siim.pipeline.register_pair`, engine **B1**,
   affine LO-RANSAC at 3.0 px, seed 0 — the pipeline's defaults, unchanged.
   B4L is run beside and enters no criterion.
5. **Read the answer in ground coordinates.** The estimate maps source pixels
   to reference pixels; the reference's label maps reference pixels to
   (lon, lat) exactly. So each registered frame acquires a **controlled ground
   map that does not pass through its own archive corners.**

**The measured quantity, per frame (the stage's primitive).** On the tile's
own pixel grid at step 64, in the frame's original-pixel coordinates:

```
D_f(x) = (controlled lon/lat of x)  −  (archive corner lon/lat of x)
```

converted to metres on the sphere at the tile's latitude, and to the frame's
own native pixels. `A_f` is the **similarity** (4 parameters) fitted to `D_f`
over ≥ 128 grid points — the same functional form and the same grid
construction `siim.verify.gauge` uses, so that S4 compares like with like.

### 2.3 Three arms

| arm | what it is | enters |
|---|---|---|
| **R** (reference) | source → TC reference, direct | S1, S2, S3, S5, S6 |
| **N** (null) | the same source → a **disjoint block of the same product**, lat 18.30–19.30, ≥ 25 km from any source footprint, identical sensor, processing and photometry | S6 only |
| **C** (chained) | a frame that fails arm R reaches the reference through **one recorded RD-07 edge** to a frame that succeeded | S4's secondary reading **only**, labelled as dependent on a recorded edge, never pooled with arm R |

### 2.4 What a disagreement can and cannot decide

A disagreement `|A − B|` between two products bounds `err(A) + err(B)` and
attributes nothing. Two things make it usable:

- **Per-frame structure.** If the archive error were the whole story, the
  measured `A_f` would be **frame-specific** and would reproduce EXP-013's
  per-node terms, which were fitted with no knowledge of this reference. That
  is a prediction with a 1-in-many chance of accidental agreement, and S4
  tests it against a label-permutation null.
- **The reference's own scale.** The reference is one product, one mosaic,
  one control network; a *constant* offset of the whole block would move every
  frame identically and would not show up in S4 at all. S2 therefore reports
  the **median across frames** (which contains any such constant) and the
  **dispersion about it** (which cannot), and never claims the first is the
  archive's error alone.

---

## 3. Data, fixed in advance

### 3.1 The reference blocks

One contiguous byte range of the product, fetched once, SHA-256 recorded:

| block | latitude band | purpose |
|---|---|---|
| **REF** | 19.52 … 20.24 N | covers every source footprint (union lat 19.5751 … 20.1802, lon 21.9490 … 22.1021) with ≈ 2 km margin |
| **NULL** | 18.30 … 19.30 N | ≥ 25 km south of the nearest source footprint; same product, same strip processing, same photometry |

Longitude window 21.88 … 22.17 E for both, cut after decoding (the product is
row-major, so a row block is fetched whole and the columns are cut in memory).

### 3.2 The sources — 20 NAC tiles + 1 Chandrayaan-2 block, named now

The **complete** REAL-DATA-07 tile set of both windows, no selection: RD03's
12 tiles and RD04's 8 tiles from `real_data_07_rd03_manifest.json` and
`real_data_07_rd04_manifest.json`, each 4096 × 2048 native pixels.

| window | frame | incidence (published) | native GSD (m) | `k` | coarse GSD (m) | \|i − 30°\| |
|---|---|---|---|---|---|---|
| RD03 | m1271742202lc | 29.95 | 0.930 | 9 | 8.37 | 0.05 |
| RD03 | m1335207975rc | 69.76 | 0.915 | 9 | 8.24 | 39.76 |
| RD03 | m1452560468lc | 68.80 | 0.855 | 10 | 8.55 | 38.80 |
| RD03 | m1182331886lc | 43.74 | 1.195 | 7 | 8.37 | 13.74 |
| RD03 | m1236465772rc | 44.44 | 1.130 | 7 | 7.91 | 14.44 |
| RD03 | m1212932972lc | 45.48 | 1.085 | 8 | 8.68 | 15.48 |
| RD03 | m1205872034rc | 47.11 | 1.075 | 8 | 8.60 | 17.11 |
| RD03 | m1175268993rc | 48.47 | 1.210 | 7 | 8.47 | 18.47 |
| RD03 | m1363396554rc | 52.40 | 1.030 | 8 | 8.24 | 22.40 |
| RD03 | m1199981485rc | 66.88 | 1.075 | 8 | 8.60 | 36.88 |
| RD03 | m1096350825rc | 72.29 | 1.300 | 6 | 7.80 | 42.29 |
| RD03 | m1142297886lc | 74.65 | 1.225 | 7 | 8.58 | 44.65 |
| RD04 | m1271742202lc | 29.95 | 0.930 | 9 | 8.37 | 0.05 |
| RD04 | m1335207975rc | 69.76 | 0.915 | 9 | 8.24 | 39.76 |
| RD04 | m1299958135lc | 18.22 | 1.070 | 8 | 8.56 | 11.78 |
| RD04 | m1315225542lc | 21.13 | 0.805 | 10 | 8.05 | 8.87 |
| RD04 | m1341069775rc | 42.43 | 0.965 | 9 | 8.69 | 12.43 |
| RD04 | m1212932972lc | 45.48 | 1.085 | 8 | 8.68 | 15.48 |
| RD04 | m1363396554rc | 52.40 | 1.030 | 8 | 8.24 | 22.40 |
| RD04 | m1096350825rc | 72.29 | 1.300 | 6 | 7.80 | 42.29 |

**Chandrayaan-2:** the TMC-2 L2 ortho block of REAL-DATA-09 pair **P1**
(`tmc2_block` [1637, 56766, 2135, 57597], 4.7232 m/px, `k = 2`, coarse GSD
9.446 m, +12.1 % of the reference — the largest residual mismatch in the
stage, recorded as such), read through `siim.ingest.geotiff.decode_window`,
with the PRADAN acknowledgement carried exactly as REAL-DATA-09 §S15 requires.

`k` is `round(8.42315289562 / g)` with `g` the archive
`SCALED_PIXEL_WIDTH/HEIGHT` mean, computed here and frozen in this table so
the runner cannot choose it after seeing a result.

### 3.3 The recorded numbers this stage reads, frozen

- **EXP-013 per-frame terms** — `experiments/EXP-013/exp013_results.json`,
  `supplementary_census_graph[W]["b1"]["per_node_px"]`, with the fixed nodes
  recorded there: **RD03 → `nac.m1182331886lc`**, **RD04 →
  `nac.m1212932972lc`**. Six frames per window; the fixed node is 0.0 by
  construction and is excluded from every correlation.
- **RD-07 recorded edges** — `rows_rd03_nue.json` / `rows_rd04_nue.json`,
  `engine == "b1" and north_up is True` only (never the un-suffixed files),
  direction from **`edge`**, transform read from
  **`transform_matrix_original_pixels`** and paired with
  `geometry.predicted_transform_matrix` (E-036, E-040).
- **REAL-DATA-09 P1** — `real_data_09_results_b1.json` and
  `real_data_09_loop_closure.json` for the recorded direct TMC-2 ↔ NAC edge
  and the 2.2131 px loop.

---

## 4. Success criteria — FROZEN

| ID | Criterion | MET if |
|---|---|---|
| **S0** | **Harness, provenance and reproduction controls. Nothing is reported from a cell unless every clause holds.** | (i) **grid gate** — the pixel↔(lon, lat) map built from `LINE_PROJECTION_OFFSET` / `SAMPLE_PROJECTION_OFFSET` reproduces the label's four corner latitudes and longitudes to **< 0.5 px**, and a (lon, lat) → pixel → (lon, lat) round trip over 10⁴ points closes to **< 1e-9°**; (ii) **provenance** — the fetched byte range, its SHA-256, the decoded shape and the `DUMMY`-zero fraction of both blocks are recorded before any registration runs; (iii) **reproduction gate** — three recorded RD-07 B1 north-up edges (one per window plus the 5437-inlier edge) re-run through the unchanged pipeline reproduce their recorded `n_inliers` **exactly**; (iv) **self-reference control** — the REF block against itself shifted by an integer 7 px recovers the shift to **< 0.05 reference px** with ≥ 9 inliers; (v) every frame's Jacobian-determinant sign recorded from `siim.ingest.orientation`, never from a print label (E-047) |
| **S1** | **An independently controlled product is registrable at all by this pipeline.** | Arm R succeeds — `n_inliers > 8` (D-023) — on **≥ 8 of the 20** NAC tiles **and** on the Chandrayaan-2 TMC-2 block. Per-frame counts, keypoints, putatives and `grid_occupancy` reported for all 21 cells whatever happens |
| **S2** | **The archive's answer against another mission's answer, in metres.** | Computed on **≥ 6** arm-R successes, and the **median across frames** of `RMS_grid |D_f|` is **< 300 m** (the 0.01° corner quantisation scale). Reported whatever it is, with: the median, the per-frame values, the dispersion about the median (p95 of `|D_f − median|`), a **bootstrap 95 % CI** over frames, and each value in metres **and** in the frame's own native pixels |
| **S3** | **§2.2's sub-pixel row, verbatim, on check points that do not pass through the estimate being checked.** | For every RD-07 pair whose **both** frames succeeded in arm R: the composed map `Â_AB = T̂_(B→R)^-1 ∘ T̂_(A→R)` — built from correspondences **A↔R and B↔R only, never A↔B** — is compared to the recorded direct `transform_matrix_original_pixels` on an 8-px grid over the joint overlap. MET if the **median endpoint error over ≥ 5 such pairs is < 0.5 reference px (4.21 m)**, with a **95 % CI** from 1000 bootstrap resamples of the inlier sets. Reported: median, p99, CI, per pair, in reference px **and** metres **and** source-native px |
| **S4** | **EXP-013's H3, decided: are the per-frame terms the archive or the estimate?** | On the **≥ 8** frames common to EXP-013's two census graphs and this stage's arm-R successes (arm C may supply up to 4 of them, counted separately and reported both ways): **Pearson r ≥ 0.7** between `per_node_px[f]` and the measured `RMS_grid |A_f − A_fix|` in the same units, **and** the median absolute difference ≤ **30 %** of the median `per_node_px`. The null is **1000 permutations of the frame labels within each window** — which destroys the frame-to-frame pairing being tested and preserves nothing else — and its p95 of \|r\| is printed beside the statistic. Fewer than 8 common frames ⇒ **NOT MET for want of data**, stated as such, with whatever correlation exists reported but not graded |
| **S5** | **A Chandrayaan-2 edge through an independent mission.** | The triangle {TMC-2 → NAC (recorded, REAL-DATA-09 P1), NAC → REF (measured here), REF → TMC-2 (measured here)} closes below **2.0 reference px** with all three edges successful, and the same closure is reported in **metres** beside it. MET only with all three edges; a missing edge is NO DATA, never a pass |
| **S6** | **The reference can fail — the stage's own false-accept measurement.** | **0 of 21** arm-N cells pass `n_inliers > 8`. Any pass is a **wrong pass**, reported with its inlier count, its geometry verdict and its recovered offset; the false-accept fraction is reported with the criterion whatever it is |

### 4.1 Parameter count against constraint count (E-041), per statistic

| statistic | fitted parameters | constraints | null / reference |
|---|---|---|---|
| affine per registration | 6 | ≥ 9 inliers by the rule; expected 10²–10³ on a 500 × 250 reference-pixel tile | the null block (S6), not a permutation |
| `A_f` (S2, S4) | 4 (similarity) | ≥ 128 grid points per frame | — |
| S2 median + CI | 0 | ≥ 6 frames | bootstrap over frames |
| S3 endpoint error | 0 | ≥ 5 pairs × ≥ 500 grid points | bootstrap over inlier sets |
| S4 correlation | 2 | 8–10 free frames (2 fixed nodes contribute 0 by construction and are excluded) | 1000 label permutations **within window** |
| S5 loop closure | 0 | 3 edges, composition only — nothing is fitted to the closure | the frozen 2.0 px line |
| S6 | 0 | 21 cells | it **is** the null |

**S4 is the criterion with the least margin**: 8–10 points against a 2-parameter
statistic. That is stated here, before the number exists, and the criterion
carries a permutation null precisely because a correlation on 10 points is
otherwise worth little. If `r` lands between the null's p95 and 0.7, the
criterion is **NOT MET and the stage says the sample cannot decide it** — it
is not read as "suggestive".

### 4.2 Predicted outcome per criterion, recorded now so it can be wrong

- **S0 MET** — HIGH for (i), (ii), (v); the label's own corner summaries and
  its projection offsets agree to 1 pixel by arithmetic already done above.
  (iii) HIGH: EXP-012 reproduced 22/22 and EXP-016's S0 is reproducing counts
  in this same session. (iv) HIGH.
- **S1 MET** — MEDIUM-HIGH overall, **9–13 of 20** NAC tiles (MEDIUM). The
  prediction is *not* uniform and is stated per stratum, because the reference
  is normalised to **i = 30°** and REAL-DATA-07's envelope is a Δ-incidence
  envelope: the **10 frames with |i − 30°| ≤ 23°** are predicted to succeed
  (MEDIUM-HIGH), the **6 frames at |i − 30°| ≥ 36°** to fail (MEDIUM-HIGH),
  and the rest are the boundary. TMC-2 predicted to succeed (MEDIUM: Δinc to
  the standard geometry ≈ 9°, inside the RD-09 envelope, but the largest
  GSD mismatch in the stage).
- **S2 MET** — MEDIUM. Median predicted **80–250 m** (≈ 60–250 native px),
  dispersion about the median **50–150 m**. If the median exceeds 300 m the
  criterion is NOT MET and the stage hunts the cause rather than widening the
  bar.
- **S3 NOT MET** — MEDIUM-HIGH (65 %). Predicted median **1.0–2.0 reference
  px (8–17 m)**: each leg carries the reference's own registration error at
  8.42 m, and the composition adds two of them. The *value* of the criterion
  is the number and its CI, not the verdict; a median under 0.5 reference px
  would be a genuine surprise and is given 20 %.
- **S4** — genuinely uncertain, **MET at 55 %**. The archive-quantisation
  arithmetic favours it (0.01° ≈ 300 m ≈ 150–350 px at k = 2, against terms of
  25–93 px), but the terms could equally be a shared per-frame estimate error.
  **This is the prediction most worth being wrong about**, and the stage is
  designed so that both answers are publishable: MET rehabilitates D-054's
  detector against a usable reference; NOT MET converts E-039's synthetic
  blind spot into a **measured** one on real frames.
- **S5 NOT MET** — MEDIUM (60 %). The TMC-2 leg carries a 12.1 % GSD mismatch
  and RD-09's direct loop missed 2.0 px by 10 %. Note in advance: a pass here
  is **weaker than EXP-012's**, because 2.0 *reference* px is 16.8 m where
  EXP-012's 2.0 px is ≈ 2 m — if S5 is MET, Part 2 states that beside it, not
  folded into it.
- **S6 MET (0 of 21)** — MEDIUM-HIGH. A mare null block at the same
  resolution is exactly the case REAL-DATA-08 found one wrong pass in, so 1–2
  passes would not be shocking; the criterion is written to expose them.
- **Overall:** the stage is predicted to land **S0, S1, S2, S6 MET; S3 NOT MET
  with a number; S4 a coin-flip that decides an open question either way; S5
  NOT MET.** If every criterion passes, that is itself suspicious and Part 2
  must say why it is not.

---

## 5. Physical limits, in numbers

| quantity | value |
|---|---|
| reference pixel | 8.42315289562 m |
| source pixels | 0.805 – 1.300 m native; 7.80 – 8.69 m after degradation |
| scale ratio actually crossed | **6.5 : 1 … 10.5 : 1**, a *real* cross-sensor ratio (EXP-016's ladder crosses the same ratios by degrading a NAC frame against itself) |
| tile at reference scale | 4096 × 2048 native ≈ **455 – 512 × 228 – 256** reference px |
| overlap | **100 %** of the source lies inside the reference block — §2.2's "≥ 50 % of the coarser tile" is satisfied by construction and is *not* what limits this stage |
| 0.5 reference px (S3's bar) | **4.21 m** = 3.2 – 5.2 native px |
| archive corner quantisation | 0.01° ≈ **303 m** in latitude, ≈ 285 m in longitude at 20° N |
| archive discrimination floor | 84 – 116 px native (EXP-013 `edge_floor_px`) ≈ **80 – 140 m** |
| EXP-013 reference noise | **66.00 px** ≈ 60 – 170 m depending on frame |
| EXP-013 per-frame terms | 25.70 – 92.84 px at k = 2 ≈ **50 – 240 m** |
| null block separation | ≥ 25 km, ≥ 3000 reference px — no overlap is geometrically possible |
| one reference pixel at the source | 6.5 – 10.5 native px: **an error invisible here can still be 10 px there**, and S3 reports both |

**The honest ceiling of this stage.** If both products were perfect the
measured disagreement would be zero; they are not, and nothing here can say
which one is wrong except through S4's per-frame structure. An accuracy
*claim* therefore takes the form: *the error of the registration is bounded by
the measured disagreement, which is X m, and that bound is an upper bound for
the sum of two errors.* That sentence is the deliverable's accuracy statement
and it may not be shortened.

---

## 6. What may not happen in Part 2

- No bar moves: 300 m (S2), 0.5 reference px (S3), r ≥ 0.7 and 30 % (S4),
  2.0 reference px (S5), 0 of 21 (S6), ≥ 8 of 20 (S1).
- **The population is the 21 sources in §3.2.** None enters or leaves; a frame
  that fails arm R is a failure, reported in its illumination stratum, and is
  not replaced.
- No re-run with a different seed, engine, orientation, PSF, `k`, RANSAC
  threshold or margin. B4L stays outside every criterion.
- The reference block may not be re-cut, re-stretched or filtered beyond the
  `DUMMY`-zero mask and the pipeline's own per-image stretch.
- Arm C may not enter S1, S2, S3, S5 or S6, and in S4 its frames are reported
  **separately** as well as pooled; if the pooled and arm-R-only answers
  disagree, both are reported and the arm-R-only answer is the criterion's.
- If S4's common-frame count falls below 8, S4 is NOT MET **for want of data**
  and no weaker statistic is substituted.
- A criterion that passes vacuously — S2 on 6 frames all from one illumination
  stratum, S6 because arm N produced no keypoints at all — is reported as
  *MET, and here is why that is not reassurance*, beside the criterion.
- Nothing in `src/` is retuned because of a result here. If S4 shows the
  detector is deployable, the deployment is a **separate** stage with its own
  Part 1; this stage writes the finding, not the change.
- The reference's absolute accuracy may not be asserted in Part 2 from any
  source not read and cited in this session.

---

## 7. What this stage explicitly does NOT claim

- **Not ground truth.** A second product is not truth; it is a second opinion
  with its own control network and its own errors.
- **Not manual check points.** §2.2's "independent check points" is honoured
  in the sense the sentence permits here — correspondences whose chain does
  not include the estimate under test — and **not** in the sense of
  human-identified features, which remain unbuilt (gap analysis A3/F).
- **Not absolute selenographic accuracy.** Every number is a disagreement.
- **Not a multi-modality result.** TC is a panchromatic optical imager, like
  NAC and TMC-2. The IIRS axis stays untested.
- **Not a viewpoint or terrain-transfer result.** One region, mare, near-nadir
  sources; the reference is orthorectified and the sources are not.
- **Not a verdict change.** `assess()`, `select_model`, `siim.verify.gauge`
  and every constant are untouched. If a cell reaches VERIFIED against a
  reference at 8.42 m, that is recorded with its metres, not celebrated.
- **Not a matcher claim** beyond B1.

---

## 8. Reported beside the criteria, not part of any

- Success against **|i − 30°|** per frame: the illumination envelope
  re-measured against a *photometrically normalised* reference — a different
  experiment from every Δ-incidence pair in the project, reported as such.
- B4L on all 21 arm-R cells and all 21 arm-N cells.
- `grid_occupancy` (primary, D-055) and `max_uncovered_disc_ratio`
  (secondary, uncalibrated line, D-053/D-057) per cell.
- The per-frame `A_f` decomposition: translation, rotation and scale parts
  separately — a rotation or scale term in the archive-vs-controlled
  disagreement would be a different defect from a shift.
- The recovered scale of each arm-R estimate against the known `k · g_S / 8.4232`.
- The Chandrayaan-2 cell's full verdict object, with the PRADAN acknowledgement.
- Every arm-C chain: which recorded edge it used and that edge's inlier count.
- Wall-clock and the fetched byte count, so the cost of this reference is on
  the record for anyone repeating it.

---

## 9. Ledger and index — what a Part 2 will create

A `STAGE-INDEX.md` row, a `STAGE_HISTORY.md` standing-table row, an `RL-nnn`
research-log entry, and: a **D-nnn** for whatever S4 decides about D-054's
deployability (either a superseding note on D-054 or a recorded refusal), a
**D-nnn** if S2 changes what the project calls its corroboration floor, and an
**E-nnn** for any defect S0 or S6 exposes. Superseding notes, never edits.

---

## Part 2

*Empty. Written only after this Part 1 is committed.*
