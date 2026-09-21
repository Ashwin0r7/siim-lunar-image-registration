# EXP-017 — Viewpoint variation: where a 2-D model stops being valid over real relief

**Part 1 — pre-registration. FROZEN 2026-09-21, before any oblique image has
been constructed, any displacement field computed, any registration run or
any residual statistic looked at.** Part 2 is empty until Part 1 is committed.

**Classification: DELIVERABLE-CRITICAL.** The problem statement names three
variations — illumination, **viewpoint**, scale — and this project has
**zero evidence of any kind on the second**. `PROJECT_GAP_ANALYSIS.md` §1(b)
scores it *NEVER TESTED*; `FINAL_SUCCESS_CRITERIA_AUDIT.md` calls it one of two
problem-statement axes that went invisible for a month because only §53 was
being tracked. The stage the master plan assigned to it, **EXP-008, was never
pre-registered and never ran** (§37 also lists the same question under the
label EXP-011, a number later spent on model selection; the naming drift is
recorded here and not repaired).

**The state of the data, said plainly.**

- **Every real frame on disk is near-nadir.** The 32 NAC tiles in
  `data/processed/mare_serenitatis/` carry published emission angles of
  **1.17°–1.77°**; the TMC-2 product delivered by PRADAN is the **nadir band
  only** (`ch2_tmc_ncn_*` calibrated image, `ch2_tmc_ndn_*_d_dtm_d18.tif`
  DTM, `ch2_tmc_ndn_*_d_oth_d18.tif` ortho — `data/manifests/chandrayaan2_manifest.json`,
  6 products, none of them a fore or aft band).
- **TMC-2 is a three-line stereo camera** with fore and aft bands at **±25°**
  (master plan §2.3, §20). A fore/aft pair acquired seconds apart in one pass
  would be the cleanest real viewpoint-only variation that exists for this
  problem — same Sun, same albedo, different emission — and **it is not on
  disk**. Obtaining it needs an interactive PRADAN login, which is a user
  action this stage neither performs nor waits for.
- **There is therefore no real off-nadir pair in this repository, and this
  stage does not pretend otherwise.** What it has instead is stronger than a
  synthetic-terrain experiment and weaker than a stereo pair: a **real 10 m
  DEM co-registered by construction with a real 5 m orthoimage** (ISRO placed
  both on one grid, REAL-DATA-09 S0), from which an oblique view can be
  **constructed** with **exact** ground-truth correspondence. Every result
  below is *synthetic viewpoint on real terrain*. §7 says what a real
  fore/aft pair would add and what this construction cannot see.

**The acceptance criterion this stage answers, quoted verbatim from
`MASTER_RESEARCH_AND_ARCHITECTURE_PLAN.md` §2.2 (line 43):**

> | Viewpoint invariance | Where is a 2D model physically valid given relief
> and off-nadir angle? | Model class chosen by residual test; DEM
> orthorectification when relief × tan(e) > 0.5 px | Residual structure vs
> relief; local-vs-global model AIC | EXP-008 | **Local model residuals
> white; no systematic relief signature** |

and the physics it rests on, §20 (line 365):

> Parallax error of a global 2D model ≈ `Δh · tan(e)` where `Δh` is relief
> within the tile. NAC at 20° slew over 100 m relief: 36 m ≈ 72 px at 0.5 m.
> TMC-2 fore/aft at 25° over 100 m: 47 m ≈ 9 px at 5 m. OHRC stereo at 25°:
> same 47 m ≈ 190 px at 0.25 m. `[INFERENCE, HIGH]` Global
> similarity/affine/homography are valid only for near-nadir pairs over low
> relief or for small tiles; otherwise orthorectify both images onto the DEM
> … and match in map space, where the residual is the DEM's own error. The
> pipeline must select the model by residual structure, not by default.

The acceptance sentence is adopted as criterion **S1** below, word for word,
with each of its two clauses given an operational meaning in §2.3 before any
number exists. The §2.2 *metric* column names an AIC; **no AIC is computed**.
This project measured (EXP-011) that a statistic built from the
correspondences' own residuals cannot see a correlated localisation bias, and
replaced it with held-out evidence on refined points (rule B, D-045). The
held-out residual is the instrument used here, and the substitution is stated
rather than made silently.

---

## 1. The question

**Q.** On real lunar relief, at what emission angle does a global 2-D
transform stop being an adequate model of the correspondence between an
oblique view and a nadir orthoimage — measured in the physical variable §20
names, `relief × tan(e)` in pixels — and does a *local* model, or
DEM-orthorectification with the DEM one would actually have, remove the
relief signature it leaves?

Every outcome is a result, and the consequence of each is fixed now:

| outcome | consequence |
|---|---|
| The global model holds to 25° (TMC-2's fore/aft angle) on every window | the deliverable may state that the TMC-2 rung needs no viewpoint treatment over mare relief, in the stated envelope; §20's threshold is measured too conservative |
| The global model fails inside the sweep and the failure carries a relief signature (S3) | §20's mechanism is confirmed on real terrain, the onset is *measured* rather than inferred, and §2.2's engineering requirement (residual test → model class → orthorectify) has a number to trigger on |
| The global model fails and the residual is **not** correlated with relief | §20's mechanism is wrong or incomplete on this terrain; the failure is something else and is reported as unexplained |
| A local model (S1) whitens the residual inside an envelope | the §2.2 acceptance is MET inside that envelope and NOT MET outside it, and the envelope is the product |
| No local model whitens the residual at any e > 0 | §2.2's acceptance as literally written is unattainable with these instruments on real relief, and the stage says so — the same finding EXP-015 recorded for §53 criterion 4 (D-057), at a different requirement |
| The held-out selector does not respond to e (S4) | the *"model class chosen by residual test"* requirement is not satisfiable by the selector the pipeline ships, and the GT-free signal that does respond, if any, is named |

## 2. What is measured, stated exactly

### 2.1 The construction — synthetic viewpoint on real terrain

Let `I(q)` be the nadir orthoimage on its map grid, `h(q)` the DEM height in
metres bilinearly resampled to that grid, `GSD` the grid's metres per pixel
**along the view azimuth** (read from the product, recorded per window), `e`
the emission angle and `φ` the view azimuth. A point at height `h` above the
window's mean height, imaged obliquely and rectified onto the reference sphere
**without** a DEM, appears displaced from its planimetric position by the
parallax

```
d(q) = (h(q) − h̄) · tan(e) / GSD      pixels, along the unit vector u_φ
```

**What is included:** the parallax term only — the term §20 names. **What is
excluded, and why:** (i) *foreshortening* — a uniform anisotropic scale
`cos(e)` along `u_φ` (0.906 at 25°), which is exactly affine, is absorbed
exactly by the affine model, and would therefore add nothing to the question
while contaminating it with a trivial scale-axis test; (ii) *occlusion* —
fold-over of the displacement field needs slope × tan(e) > 1, i.e. slopes
steeper than 90° − e (60° at e = 30°), and lunar regolith holds nothing above
its ~33° angle of repose, so the field is invertible everywhere on this
terrain (a real oblique image of a steep crater wall *is* occluded on the far
side; this construction is not, and §7 says so); (iii) *view-dependent
radiometry* — the phase angle changes with emission and real regolith is not
Lambertian, so a real fore/aft pair differs in brightness as well as geometry;
here the oblique image is the same photons displaced, so **texture and
illumination are identical by construction and every error is a bound on
precision, not accuracy** (EXP-010 S1's rule).

**Azimuth.** `φ` = image up (north; TMC-2's orbit is near-polar and the
fore/aft parallax is along-track). Displacement toward −y for positive
height. The aft view is the mirror; a second azimuth is **not** in this
design. The sign is irrelevant to every model (they are sign-symmetric) and is
used only by S3's slope check, which knows it.

**Resampling.** The oblique image is `I_obl(p) = I(q)` with `p = q + d(q)`:
for each oblique pixel `p` the source `q` is found by fixed-point iteration
`q ← p − d(q)` (contraction since `|∇d| ≤ tan(e) · slope < 0.31` at e = 30°
on 33° slopes; ≤ 50 iterations, stop at 1e-6 px), then sampled with the same
order-3 spline and NaN fill that `siim.geometry.warp` uses. Pixels whose
source lies outside the ortho's valid region, or where the DEM is nodata, are
NaN. The DEM is **bilinearly** resampled from its 2× coarser grid for this
purpose — a stated deviation from `run_real_data_09_p5.dem_on_ortho_grid`'s
nearest-neighbour repeat, whose reason (not inventing slope for a shading
test) does not apply to a displacement field, where a nearest repeat would
manufacture 2 px staircase discontinuities that are not on the Moon.

**Ground truth.** Exact by construction, and — this is the point — **not a
global 2-D transform at all**: for a reference grid point `q` the source point
is `q + d(q)`. For an estimated source → reference transform `T̂`:

```
err(q) = ‖ T̂( q + d(q) ) − q ‖      over a grid of q, step 8 px, jointly valid
```

evaluated on the reference grid so no field inversion enters the error. Step
8 rather than EXP-014's 16 because the short TMC-2 windows are 26–34 % valid
and a 16 px grid would leave under 500 points on them. A window with fewer
than **300** valid grid points reports `CANNOT CHECK` for every residual
statistic.

**Direction.** Source = the constructed oblique, reference = the nadir
ortho: the deliverable's use-case (Chandrayaan-2 off-nadir → map reference).
Not flipped afterwards.

### 2.2 Response variables, per (window, e)

- **(a) Success under the frozen rule.** `n_inliers > 8` (D-023) through
  `siim.pipeline.register_pair` — estimate → refine (ECC 48) → re-estimate
  with rule B → verify — and the verdict status. Engine B1, affine RANSAC at
  3.0 px, seed 0: the pipeline's defaults, unchanged.
- **(b) Dense endpoint error** against the exact GT, §2.1: median, p99, max
  — for the global pipeline transform and for each local arm (§2.4).
- **(c) The relief signature** — §2.3.
- **(d) Model class** selected by rule B (`selection.model`, its
  `heldout_px` per candidate, `decided_by_tie_break`), and the verdict's
  `model_selected_by`.
- **(e) Local arms** — §2.4 — and whether they remove (c).
- Secondary, reported: `grid_occupancy` (D-055) of the inlier set; the
  refinement's per-point `shift` against local DEM slope; the pixel-permutation
  null beside the shift null (§2.3).

### 2.3 The §2.2 acceptance, made operational

**"No systematic relief signature."** Project the residual vector of each
grid point onto the view azimuth: `r_φ(q) = u_φ · (T̂(q + d(q)) − q)`. Remove
the best-fit plane from the DEM over the window (3 parameters against 10⁵–10⁶
DEM pixels) to get the **residual relief** `h_res(q)`; a global affine absorbs
the planar component of the parallax exactly, so the plane is what the model
*can* explain and `h_res` is what it cannot. Regress `r_φ` on `h_res`:
**2 parameters** (slope, intercept) against N_g grid points (predicted ≈ 1 900
on the short windows, ≈ 18 000 on the long ones). The physics predicts the
slope with **no free parameter**: `tan(e) / GSD` px per metre, with the
construction's sign. The signature test **fires** when all three hold:

1. R² exceeds the **95th percentile of a null built by cyclically shifting
   the height field** — 200 draws, each a toroidal shift by a random offset
   of at least 10 % of the grid extent on each axis plus a random dihedral
   flip, seed 20260921 — which destroys the alignment between residual and
   relief **while preserving the relief field's spatial autocorrelation**;
2. the fitted slope has the predicted sign;
3. the fitted |slope| is within a factor of 2 of `tan(e) / GSD`.

*Why not a pixel permutation of heights.* The task's phrase is "a null built
by permuting heights", and a per-pixel permutation is the obvious reading. It
is the wrong instrument here, for E-041's reason: `r_φ` and `h` are both
spatially smooth, so their sample correlation under H0 has the variance of
two smooth fields (effective N ≈ number of independent patches), not of N_g
independent points. A pixel permutation would deliver a null that a smooth
but unrelated residual field beats every time — a control that cannot fail.
The shift null is the property-preserving one. **Both are computed; the
criterion uses the shift null; the pixel permutation is reported beside it so
the difference is visible**, and S0(v) checks the shift null's false-alarm
rate at e = 0 before S3 is read.

**"Local model residuals white."** Moran's I of `r_φ` over the grid (rook
adjacency on the 8 px grid, valid points only; 0 fitted parameters) against
200 **value permutations** of the residual field. Here a pixel permutation
*is* the right null: the property under test is the residual's own spatial
structure, and permuting its values destroys exactly that and nothing else
(E-039's rule — build the null from the property being tested). A field is
**white** when its Moran's I is at or below the null's 95th percentile, **or**
its RMS is below **0.05 px** — the harness's own resolution (EXP-014 S0's
line), below which structure is not measurable by this instrument. That floor
is the only non-invented one available and it is deliberately not tied to the
0.5 px accuracy bound: the criterion is read literally, and §4 predicts what
the literal reading will do.

**The same test, GT-free.** Replace `r_φ(q)` on the grid by the transfer
residual of each **refined inlier** under the final transform,
`u_φ · (T̂(p_i) − q_i^refined)`, and `h_res` by the DEM sampled at `q_i`. This
is the only version a deployed pipeline could run — it uses no ground truth
— and it is reported at every (window, e) with two height sources on arm A:
the TMC-2 DTM (best case) and the 59 m SLDEM (the DEM the deliverable
actually holds everywhere). **Reported, not a criterion**, because RANSAC and
refinement select and move exactly the points it is computed on (§4's
prediction says how much that blinds it).

### 2.4 Local arms

| arm | what it is | fitted parameters | against |
|---|---|---|---|
| **G** global | the pipeline's final transform, as shipped | 2 / 4 / 6 / 8 by selected model | N_refined refined inliers (predicted 10²–10⁴), evaluated on the independent dense grid |
| **L1** piecewise affine | a **4 × 4** grid of cells over the reference window; per cell an affine least-squares fit to the refined inliers whose reference point lies in it; a cell with **< 12** points (the selector's `MIN_POINTS`) falls back to G and is counted | 6 × 16 = **96** | N_refined; cells recorded |
| **L2** SLDEM-orthorectified | subtract the parallax **predicted from the independent 59 m SLDEM**, `d_S(p) = (h_S(p) − h̄_S) · tan(e) / GSD`, from each source point, then fit the global affine to the corrected correspondences; `e` and `φ` taken as known (from the label, on real data) | **6** — the DEM contributes 0 fitted parameters | N_refined |
| **L3** DTM-orthorectified | as L2 with the DTM that *built* the field | 6 | **circular by construction**; it is S0(iv), a harness control, and is never reported as evidence |

L2 exists only on arm A, where a second, independent DEM exists. On arm B the
SLDEM built the field (L2 would be L3); on arm C there is no second DEM. **L2
is the §2.2 engineering requirement tested with the DEM one would actually
have**, and its residual is, as §20 says, *the DEM's own error* — here the
SLDEM–DTM difference times `tan(e) / GSD`.

### 2.5 The physical variable, and the two readings of "relief"

§20 writes `Δh · tan(e)` with `Δh` "relief within the tile", which reads as
peak-to-peak. A global affine absorbs a tilted plane exactly, so the parallax
a global model *cannot* absorb scales with the **residual** relief. Both are
recorded per window, before any matching, from the DEM alone:

```
P_ptp(e) = ptp(h)      · tan(e) / GSD       §20's reading
P_rms(e) = rms(h_res)  · tan(e) / GSD       the reading a global affine sees
```

and every onset in §4 is reported in both. **Which reading §20's 0.5 px is
right under is one of this stage's outputs**, and §4 records a prediction.

## 3. Data, fixed in advance

No new byte is fetched. Three arms, reported separately and never pooled.

**Arm A — real DEM, real ortho, co-registered by construction (primary).**
The **15 TMC-2 windows** of `experiments/REAL-DATA-09/real_data_09_p5_dem_render_v2.json`
that carry a `leg_a_control` key (the 3 rows excluded there for no coverage
stay excluded): their `tmc2_block` `[x0, y0, x1, y1]` on the ortho grid,
decoded by `siim.ingest.geotiff.decode_window` from the ortho and the DTM
products named in `chandrayaan2_manifest.json`. Windows are 481–1409 px wide
and 799–2518 px tall; ortho valid fraction 0.15–0.61; DEM nodata fraction
0.08–0.70; **peak-to-peak relief 48–152 m** (the short RD03 windows 48–63 m,
the long RD03/RD04 windows 102–152 m). A window enters if its **jointly valid
area** (ortho > 0 and DEM finite) is **≥ 50 000 px**; otherwise it is reported
`excluded` before any e is run.

**Arm B — real NAC texture under a coarse real DEM (breadth).** The first
**ten** tiles of `data/processed/mare_serenitatis/` in sorted filename order
**whose name carries a `geo.l<line0>s<sample0>` window** (the eleventh file,
`nac.m1225876972lc.tile.npy`, has no window in its name and is skipped by
this rule, not by choice after the fact). Decimation 2, `decimate` then
`stretch` in the recorded order (`run_exp007`), GSD = 2 × the archive's scaled
pixel, **1.84–2.58 m**. Heights from the SLDEM2015 window
(`data/manifests/sldem2015_window_mare_serenitatis.json`, rows 4400–5700,
lat 18.87–21.41 °N, 512 ppd ≈ 59 m posting, 3–4 m vertical) on the tile
grid through `siim.ingest.lola_dem.dem_on_tile_grid`. Two tiles from one frame
are two windows, not one. The DEM is placed through the ~150 m corner
geometry, so its craters need not coincide with the tile's — irrelevant to
every criterion (all concern the model class against a smooth field), and
stated because it makes arm B's oblique image less *real* than arm A's.

**Arm C — fully synthetic (breadth, exact at every scale).**
`siim.data.synthetic_terrain.height_field` on regimes `A_mare_moderate` and
`A_highlands_moderate`, seeds **3001, 3002, 3003** (EXP-010's; never used for
a threshold), 768 × 768 field at **5 m/px**, rendered once under Sun
(315°, 45°) with the default 0.004 noise, cropped to 512 × 512; the oblique
view is the rendered image warped by the field's own parallax — **no
re-render**, so texture is identical as in arms A and B.

**Emission sweep, identical on every arm:**
`e ∈ {0, 1, 2, 3, 5, 10, 15, 20, 25, 30}°` — 0 is the control, ±25° is
TMC-2's fore/aft, 30° covers a slewed NAC. The low end is dense because §5
shows §20's own threshold is crossed at 1–3° on these windows; the onset
resolution is one sweep step.

**Cost.** 15 × 10 + 10 × 10 + 6 × 10 = **310 registrations**, B1 only, CPU
only; the long TMC-2 windows are 2.5–3.5 Mpx. Predicted 1–2 h. B4L is not run:
the question is about the model class, not the matcher, and EXP-006 measured
that a matcher swap is a trade rather than a monotone gain.

**Runner and artefact.** `scripts/run_exp017.py`, written only after this
Part 1 is committed; `experiments/EXP-017/exp017_results.json`; refuses to
overwrite (integrity rule 4). The dense-field warp and dense-field endpoint
error it needs do not exist yet and are specified by behaviour in S0(iii):
on an affine field they must reproduce `siim.geometry.warp` and
`endpoint_error` exactly.

## 4. Success criteria — frozen

| ID | Criterion | MET if |
|---|---|---|
| **S0** | **Harness control. Nothing is reported from a window or arm on which any clause fails.** | (i) at e = 0 the pipeline on (ortho, ortho) returns dense median error **< 0.05 px**, selects `translation` (EXP-011's gate) and passes the rule; (ii) the inverted field composed with the forward field returns identity to **< 1e-3 px** max over the valid grid; (iii) on an exactly affine field the dense warp reproduces `siim.geometry.warp` and the dense error reproduces `endpoint_error` to **1e-9**; (iv) **L3** returns dense median **< 0.05 px at every e** (the field is applied with the sign and convention L2 will use); (v) **null calibration**: at e = 0 the S3 detector fires on **≤ 1 of 15** arm-A windows (the 5 % rate on 15 trials) — if more, the shift null is mis-built and **S3 is not reported**; (vi) E-035's assertion: at every e > 0 the oblique differs from the ortho and the field's RMS is > 0 |
| **S1** | **The §2.2 acceptance, verbatim: "Local model residuals white; no systematic relief signature."** Evaluated on the **dense** residual of each local arm, per (window, e) | **S1a (literal):** the arm's residual is *white* (§2.3) **and** the signature test does **not** fire on it, on **≥ 12 of 15** arm-A windows at each of **e ∈ {1, 2, 3, 5}°**, for **L1**. Reported likewise for L2, and the **largest e at which S1a still holds** is reported per arm as that arm's envelope. **S1b (the bound reading, reported beside S1a and not a substitute for it):** the arm's dense median **< 0.5 px** (§23's sub-pixel definition) and p99 **< 1.0 px** (EXP-014's bound) on ≥ 12 of 15 windows; largest such e reported per arm |
| **S2** | **The onset, and §20's 0.5 px against it.** A measurement, MET when computed and reported for every window that passed S0 | per window, `e*_med` = smallest sweep e at which **G**'s dense median error exceeds **0.5 px**, and `e*_p99` = smallest at which p99 exceeds **1.0 px**; each with `P_ptp(e*)` and `P_rms(e*)` (§2.5). Beside it: on how many of the 15 windows §20's rule — `P_ptp = 0.5 px` — predicts `e*_med` to within **one sweep step**. Reported **whatever the count**. *Success under the frozen rule* and the verdict status are reported at every e in the same table |
| **S3** | **Anti-vacuity: the failure is a relief signature, not noise.** The criterion that stops S2 from passing for the wrong reason | the signature test (§2.3: R² above the **shift null's** 95th percentile, predicted sign, |slope| within 2× of `tan(e)/GSD`) fires on **G**'s dense residual on **≥ 80 %** of the (window, e) cells with **e ≥ e*_med**, and S0(v) held. **If S3 fails, S2's onset is an onset of *something* and may not be described as a relief effect.** The pixel-permutation null's firing count at e = 0 is reported beside, as the control that would have been wrong |
| **S4** | **Model-class selection tracks e.** The §2.2 requirement *"model class chosen by residual test"*, tested on the selector the pipeline ships | **S4a:** Spearman ρ between the **selected model's DOF** (2/4/6/8) and e, pooled over arm A's (window, e) cells (≤ 150; 0 fitted parameters), is **> 0.3 with p < 0.05**. **S4b:** Spearman ρ between the **best candidate's held-out median** (`min(heldout_px)`) and e is **> 0.5**. Both reported with the fraction of cells `decided_by_tie_break` per e |
| **S5** | **Breadth: the onset is a property of parallax-in-pixels, not of angle.** | for **arm C**, the geometric mean over its 6 fields of `P_rms(e*_med)` lies within a **factor of 2** of arm A's geometric mean; for **arm B**, the same — or, if no tile crosses 0.5 px inside the sweep, its maximum `P_rms` at 30° lies **below** arm A's geometric-mean onset. MET only if **both** arms satisfy their clause |

**Parameter counts against constraints (E-041), in one place:**

| statistic | fitted parameters | constraints | null |
|---|---|---|---|
| G global model | 2 / 4 / 6 / 8 | N_refined (10²–10⁴) inliers; scored on an **independent** grid of N_g points | — |
| L1 piecewise affine | 96 (fallback cells counted) | N_refined | — |
| L2 SLDEM-ortho | 6 | N_refined | — |
| plane removal → `h_res` | 3 | 10⁵–10⁶ DEM pixels | — |
| relief-signature regression | 2 | N_g ≥ 300 (≈ 1 900 short, ≈ 18 000 long) — effective N far smaller, which is why the null is a shift null | 200 toroidal shifts + flips of `h_res` |
| Moran's I | 0 | N_g | 200 value permutations of `r_φ` |
| Spearman ρ (S4a, S4b) | 0 | ≤ 150 cells | exact / asymptotic p |
| onset `e*` | 0 | 10 sweep levels; resolution one step | — |
| S5 factor of 2 | 0 | 15 / 10 / 6 onsets | — |

**Predicted outcome, recorded now so it can be wrong.**

- **S0 MET** — HIGH. The clause most likely to fail is (v): on the short
  windows (≈ 1 900 grid points, 30 % valid) a 10 % minimum shift may not
  decorrelate a large crater from itself.
- **S1a NOT MET at e ≥ 2° for L1** — MEDIUM-HIGH — and **NOT MET at e ≥ 3°
  for L2** — MEDIUM. The reasoning: even at 1–2° the residual relief
  (predicted 15–40 m RMS) leaves 0.1–0.3 px of *smooth* structure, a 4 × 4
  piecewise affine over 125–350 px cells leaves the intra-cell part of it,
  and the SLDEM–DTM difference (predicted ≥ 15 m RMS, the DTM's own stated
  height RMSE being 20.9 m) leaves a structured L2 residual. **The literal
  §2.2 acceptance is predicted to be unattainable on real relief with these
  instruments beyond ~1°**, and if that is what happens the stage's finding
  is that the acceptance is mis-specified — a bound, not whiteness, is what
  real relief admits — recorded the way D-057 recorded criterion 4. **S1b
  MET for L1 to e = 10°** — MEDIUM; **for L2 to 5°** — LOW-MEDIUM.
- **S2 MET** (a measurement). Predicted `e*_med`: **3–10°** on the long
  windows (ptp ≥ 100 m), **5–15°** on the short ones; `P_rms(e*_med)` ≈
  **0.3–0.7 px**; `P_ptp(e*_med)` ≈ 1.5–4 px. **§20's peak-to-peak reading
  predicts the onset early by ≥ 2× on ≥ 12 of 15 windows** — MEDIUM — while
  its 0.5 px figure is about right under the residual-RMS reading. **Success
  under the frozen rule at every e on every window** — HIGH: RANSAC keeps a
  height slab (≈ 2 · 3 px · GSD / tan(e) thick in `h_res`: 170 m at 10°, 52 m
  at 30°) and a slab of real texture yields far more than 8 inliers. **The
  verdict is never REJECTED at any e** — HIGH — which, if true, is the
  deliverable's viewpoint blind spot stated in one line: a map wrong by up to
  ~18 px off the slab, passed.
- **S3 MET** — MEDIUM-HIGH. The pixel-permutation null is predicted to fire
  at e = 0 on **≥ 3 of 15** windows — MEDIUM — i.e. to be the anti-conservative
  control §2.3 says it is.
- **S4a MET** — MEDIUM, with ρ ≈ 0.3–0.5 and the selection **saturating at
  affine**: projective is not the parallax field's shape either, so the
  selector cannot signal "no global model fits" by climbing the ladder.
  **S4b MET** — HIGH (ρ > 0.7): the held-out level is the GT-free signal that
  *does* respond, and it is what a residual test in the deliverable would
  have to read. `decided_by_tie_break` predicted to **fall** with e.
- **S5 MET** — MEDIUM-LOW overall (two independent clauses): arm C MEDIUM;
  arm B MEDIUM, predicted to cross at 10–20° with `P_rms` 0.3–0.7 px, the
  SLDEM's residual relief over a 2 × 4 km tile being predicted 5–15 m.
- **Secondary:** `grid_occupancy` of G's inliers **falls** with e on ≥ 12 of
  15 windows — MEDIUM (the slab is a height band, and height is spatially
  clustered); the GT-free signature test with DTM heights first fires at
  **≥ 2 × e*_med**, with SLDEM heights at ≥ 3 × or never — LOW-MEDIUM.

## 5. Physical limits, in numbers

At **5 m/px** (the ortho's nominal GSD; the value the runner reads from the
product is recorded per window — the P5 artefact records a 4.72 m mean of the
two axes, a discrepancy the scout resolves before the run):

| e | tan e | parallax per 10 m of height | per 100 m |
|---|---|---|---|
| 1° | 0.0175 | 0.035 px | 0.35 px |
| 2° | 0.0349 | 0.070 px | 0.70 px |
| 3° | 0.0524 | 0.105 px | 1.05 px |
| 5° | 0.0875 | 0.175 px | 1.75 px |
| 10° | 0.1763 | 0.353 px | 3.53 px |
| 15° | 0.2679 | 0.536 px | 5.36 px |
| 20° | 0.3640 | 0.728 px | 7.28 px |
| 25° | 0.4663 | 0.933 px | 9.33 px |
| 30° | 0.5774 | 1.155 px | 11.55 px |

- **§20's 0.5 px line under the peak-to-peak reading** is crossed at
  `tan(e) = 2.5 m / ptp`: **2.98°** for the 48 m windows, **2.27°** at 63 m,
  **1.40°** at 102 m, **0.94°** at 152 m. Every arm-A window crosses it below
  the sweep's 3° level, which is why the sweep is dense there.
- **Largest constructed parallax:** 152 m × tan 30° / 5 m = **17.5 px**
  (18.6 px at 4.72 m/px). The RANSAC threshold is 3 px, so above ~10° the
  inlier set is a height slab and not the window.
- **Fold-over** needs slope > 90° − e: 60° at e = 30°. Lunar angle of repose
  ≈ 33° (`synthetic_terrain.ANGLE_OF_REPOSE_DEG`). None on this terrain.
- **Refinement under relief.** ECC refines a pure translation over a 48 px
  patch; the parallax varies across the patch by 48 · slope · tan(e) px —
  **2.2 px** at e = 25° on a 5.7° (0.1) slope. EXP-010's 0.003 px precision
  was measured on a patch with no such gradient and **does not carry** to
  oblique views on slopes; the refined-point error on slopes ≥ 5° is
  predicted ≥ 0.5 px at 25°, and the per-point `shift` is reported against
  local slope.
- **The DEM inside the ground truth.** The TMC-2 DTM's own label states
  `product_accuracy_rmse_height` **20.88 m** (stdev 20.48 m) at a 10 m
  posting. The GT is exact *with respect to the constructed field*; the
  field is only as real as the DTM, so a real fore/aft pair would differ
  from this construction by ≈ 20.9 · tan(25°) / 5 ≈ **1.9 px RMS** at 25°.
  The SLDEM (59 m posting, 3–4 m vertical) enters only through L2 and the
  GT-free test.
- **Extrapolation to the other named sensors is arithmetic, not evidence:**
  the same 100 m of relief at 25° is 9.3 px at TMC-2, **36 px at NAC 0.5 m
  … 190 px at OHRC 0.25 m** (§20). Nothing here tests OHRC or a slewed NAC.

## 6. What may not happen in Part 2

- The emission set may not be extended, thinned or re-spaced; `e*` is read
  off this sweep at its one-step resolution.
- The **0.5 px** median and **1.0 px** p99 bounds may not move; the **0.05 px**
  whiteness floor may not be raised after S1a fails at the level §4 predicts.
- The null for S3 may not be swapped from the shift null to the pixel
  permutation (or back) after seeing which one fires; both are reported, the
  criterion uses the one frozen here.
- The **4 × 4** cell grid and the 12-point fallback may not be tuned; the
  10 % shift minimum and the 200-draw counts may not change.
- No window may be dropped except by the 50 000 px joint-validity rule and
  S0; no arm may be pooled with another; the direction (source = oblique) may
  not be flipped; the engine may not change; B4L, if ever run, is a separate
  reported arm outside every criterion.
- §20's threshold may not be *re-read* to fit the result: both readings of
  "relief" are reported and, if the residual-RMS reading is the one that
  holds, **§20's wording is what changes**, by a recorded note, with the
  peak-to-peak figure kept beside it.
- A criterion that passes vacuously — S4a because every cell selects the
  same model, S1a because a window's residual is under the floor at every
  e — is reported as *MET, and here is why that is not reassurance*, beside
  the criterion, never folded into it.

## 7. What this stage explicitly does NOT claim

- **Not a real stereo or off-nadir result.** The oblique image is the nadir
  image's own photons displaced by a DEM: identical texture, identical
  illumination, identical interpolation kernel. Every error is an **upper
  bound on precision** for the geometry question and says nothing about
  whether a real fore band's texture *matches* the nadir band's at all.
- **Not occlusion, not view-dependent radiometry, not a sensor model.** No
  fold-over, no phase-angle change, no line-scan attitude, no foreshortening
  (§2.1). A real oblique image has all four.
- **Not independent of the DTM.** The ground truth is exact relative to a
  DEM whose own stated height RMSE is 20.9 m (§5).
- **Not a Chandrayaan-2 fore/aft result, not an OHRC result, not a slewed-NAC
  result** — one region, mare, one TMC-2 strip, 15 windows; the other sensors'
  numbers in §5 are arithmetic.
- **Not a verdict change.** `assess()`, `select_model`, the pipeline order
  and every constant are untouched; if S2 shows the verdict passes a wrong
  map, that is recorded as a blind spot beside the verdict, as EXP-013 did
  for the gauge, and not patched here.
- **Not a matcher claim.** One engine.

**What a real TMC-2 fore/aft pair would add, and why it is the right next
acquisition.** (i) The one real viewpoint-only variation in this problem —
same pass, same Sun, seconds apart — so an outcome could be attributed to
viewpoint without the illumination confound that every NAC pair carries.
(ii) Occlusion, phase-angle radiometry and the true sensor geometry, which
decide whether the *matcher* survives 25°, a question this construction
cannot ask. (iii) A ground truth **independent of this DTM**: ISRO derived
the DTM from that very fore/aft pair, so pair-to-DTM consistency becomes a
check instead of an assumption. (iv) A test of L2 with the DEM the deliverable
would actually orthorectify with. The request is a PRADAN download of the
`ch2_tmc_ncf_*` / `ch2_tmc_nca_*` bands of the same observation, and it is a
user action.

## 8. Reported beside the criteria, not part of any

- The GT-free signature test (§2.3), detection rate vs e, DTM and SLDEM
  heights.
- `grid_occupancy` and `max_uncovered_disc_ratio` of G's inlier set vs e.
- The refinement `shift` magnitude vs local slope, per e.
- The pixel-permutation null's firing count at every e.
- The verdict status and confidence at every (window, e), with
  `model_selected_by`.
- The SLDEM–DTM height difference over each arm-A window (RMS, ptp), which is
  L2's floor by §20's own argument.

---

## Part 2

*Empty. Written only after this Part 1 is committed.*
