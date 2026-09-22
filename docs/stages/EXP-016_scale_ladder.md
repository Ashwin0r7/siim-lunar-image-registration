# EXP-016 — The scale ladder to 320:1 on real lunar texture: where it dies, and whether that is the descriptor or the pixels

**Part 1 — pre-registration. FROZEN 2026-09-21, before any image has been
degraded past the recorded rungs, before any statistic has been computed and
before the runner exists.** Part 2 is empty until Part 1 is committed.

**Classification: DELIVERABLE-CRITICAL.** The problem statement names scale
variation **"2:1 to 320:1"** in so many words. `PROJECT_GAP_ANALYSIS.md`
§1(b) scores it *NOT MET / UNTESTED*; its §4 ranks this stage **first** of the
corrected path — "highest value ÷ cost in the project by a wide margin" —
because every byte it needs is already on disk. The best real evidence is
≈ 65:1 from a proxy (REAL-DATA-08, NAC ↔ WAC, B1 **1 of 4**, B4L 3 of 4 with
one wrong pass); the synthetic probe stops at **32:1** (EXP-007 tier 2) and
measures the *unmodified* baseline, not the architecture's own answer.

**The stage number.** EXP-016 was never assigned; EXP-017 and EXP-018 were
numbered first because they were pre-registered first. The gap is filled here
rather than left, and the ordering of numbers carries no meaning.

**The acceptance criterion this stage answers, verbatim from
`MASTER_RESEARCH_AND_ARCHITECTURE_PLAN.md` §2.2 (line 42):**

> | Scale invariance (2:1 to 320:1) | Is the limit descriptor failure or
> sampling starvation? | PSF-aware degrade-to-coarser ladder; never upsample |
> Success rate per rung; error in coarser-image pixels | Scale probe extended
> to real pairs | **Every rung ≤ 320:1 registers when overlap ≥ 50 % of the
> coarser tile** |

and the analysis it rests on, §19 (line 359):

> The unmodified baseline holds to 4× on mare and 8× on highlands; every
> failure beyond is detector starvation … Therefore scale is a sampling
> problem: degrade the fine image with the coarse sensor's PSF to the coarse
> GSD, match there, express sub-pixel in coarse pixels. … **Envelope:** every
> PS rung ≤ 320:1 is reachable by degradation; what is lost is that the fine
> image's own pixel accuracy cannot exceed the coarse image's.

and §345's arithmetic on what 320:1 physically is:

> OHRC↔IIRS 320:1 (only meaningful as OHRC block-averaged to 80 m; an OHRC
> frame is ~40 × 150 IIRS pixels, so this is **patch-in-image localisation,
> not general registration**).

The §2.2 sentence is adopted as criterion **S1** below, word for word. §19's
claim *"every rung is reachable by degradation"* is a prediction this stage
can refute, and §2.2's own question — *descriptor failure or sampling
starvation?* — is criterion **S2**, given a design that can tell the two apart.

---

## 1. The question

**Q.** Take real NAC pairs of the same ground that the frozen pipeline already
registers at its native rung, inside the illumination envelope it has
measured. Degrade both to a common coarser GSD through a stated PSF — the
architecture's answer to scale — and climb the ratio ladder 2 : 4 : 8 : 16 :
32 : 64 : 128 : 320. **At which rung does registration stop, is the stop
decided by the ratio or by the number of coarse pixels the overlap contains,
does the architecture's normalisation step actually beat not normalising, what
is the error in coarse pixels where it works, and what does the 320:1 rung
mean on data that exists?**

Every outcome is a result, and the consequence of each is fixed now:

| outcome | consequence |
|---|---|
| Every rung to 320:1 registers on ≥ 90 % of pairs (S1 MET) | §2.2's acceptance is MET on real mare texture for the NAC-derived ladder; §19's envelope claim survives its first real test |
| Registration stops at a rung r* < 320 **and** the stop tracks coarse pixel count, not ratio (S2 → starvation) | §19's mechanism is confirmed and **measured**: the deliverable states a pixel floor N*, and whether any named sensor pairing sits above it becomes arithmetic (§5) |
| The stop tracks ratio at fixed pixel count (S2 → descriptor) | §19 is wrong on this terrain; the descriptor, not the sampling, is the limit, and "degrade and match" is not sufficient — reported as such |
| Normalising to the coarse GSD does **not** beat matching across the gap (S3 NOT MET) | the architecture's scale stage (D-005, "required first-class pipeline stage") is refuted by its own ablation and D-005 is superseded |
| The 320:1 rung localises but does not register (S5) | the PS's largest ratio is answered in the only form §345 says it can take, with its measured error in coarse pixels |
| Nothing at 320:1 works in either form | the 320:1 rung is **unreachable from any NAC window on disk**, and the deliverable says so with the pixel arithmetic beside it, instead of leaving the axis blank |

## 2. What is measured, stated exactly

### 2.1 The construction — a real pair, degraded to a common coarse GSD

Let `P` and `Q` be two real NAC frames of the same ground, `P` the
lower-incidence frame (source), `Q` the reference, exactly as REAL-DATA-07
ordered its edges. Native GSD `g_P`, `g_Q` (0.8–1.3 m, archive
`SCALED_PIXEL_WIDTH/HEIGHT`; resolution ratio ≤ 1.5 in-sample, recorded per
pair). For a ladder rung `r` the **coarse image** is

```
C_r(Q) = degrade_to_gsd(Q_window, k = r, psf_fwhm_coarse_px = 1.0)
```

— `siim.preprocessing.degrade.degrade_to_gsd`, a Gaussian PSF of one coarse
pixel FWHM followed by an `r × r` block mean, the operator R9 states and
REAL-DATA-08 Part 2 records as the correction to its own box average. With
`psf = 0` it **is** the box average `decimate` of every recorded run, which is
what makes S0's reproduction gate exact.

**Arm D (degrade — the architecture's answer).** The source is `C_r(P)`: the
fine image degraded through the same PSF to the same GSD. Both images enter
`siim.pipeline.register_pair` at the coarse GSD, in `north_up_east_right`
orientation (E-037, applied through `siim.ingest.orientation` with the tile's
corner geometry exactly as `run_real_data_07.run_edge` does), engine B1,
affine LO-RANSAC at 3.0 px, seed 0 — the pipeline's defaults, unchanged. The
**ratio** `r` is the ratio between the source's native GSD and the GSD at
which matching happens; that is the PS's ratio, since the architecture never
matches at the finer GSD (§345: "not sensible").

**Arm N (naive — the counterfactual the architecture rejects).** The source is
`P` at the recorded native rung (`k = 2`, the rung every real-data stage used)
and the reference is `C_r(Q)`, `r ≥ 4`: the pipeline is asked to bridge a
GSD gap of `r / 2` with no normalisation, relying on the detector's own
scale space. **This is RL-051b's requested ablation** — a protocol component
*designed* as an ablation rather than recovered from a defect (EXP-006,
D-056): scale normalisation ON (arm D) against OFF (arm N), both levels
implementable, neither recorded. The recovered transform's scale is
reported against the known `r / 2`.

**Arm X (the cropped control that separates ratio from pixel count).** For
every rung `r ≥ 8` in arm D, a second registration at rung `r / 2` on the
**central quarter** of both windows (half the extent on each axis), so that
the coarse image has **the same pixel count** as the full window at rung `r`
but **half the ratio**. If success is a function of pixel count, the cropped
`r / 2` cell and the full `r` cell agree; if it is a function of ratio, the
cropped cell succeeds where the full one fails. Crop, then degrade, in that
order; the crop is exact on the native grid.

**Arm L (localisation — what §345 says 320:1 is).** On the two long windows
(§3) at `r ∈ {32, 64, 128, 320}`: the **template** is `P`'s recorded
4096 × 2048 tile (which lies inside `P`'s long window; §3 lists the line
ranges) degraded by `r`; the **search image** is `Q`'s long window degraded by
`r`. Normalised cross-correlation (`cv2.matchTemplate`, `TM_CCOEFF_NORMED`,
NaN-filled with the window median) gives a peak; the **predicted** location is
the tile centre's ground point carried through the archive corner maps into
`Q`'s coarse grid (`siim.ingest.footprint`, the same route as the geometry
check). Reported per cell: peak offset from prediction in coarse px, the
peak-to-sidelobe ratio (PSR: peak over the standard deviation of the map
outside a 5 × 5 exclusion, a stated definition, no tuning), template and
search sizes in coarse px.

**What is not varied.** One engine in every criterion (B1). B4L is run on arm
D at `r ≥ 8` only (EXP-007's memory rule) and **reported beside**, never in a
criterion. No re-tuning of the RANSAC threshold to the coarse grid: 3.0 px is
3.0 coarse px at every rung, which is the pipeline as shipped, and its
consequence (a looser bound in metres at coarse rungs) is stated.

### 2.2 Response variables, per (pair, rung, arm)

- **(a) Success under the frozen rule:** `n_inliers > 8` (D-023) **and** the
  transform not INCONSISTENT with archive corner geometry
  (`run_exp007.geometry_check`, its floor now expressed in coarse pixels —
  ≈ 100 native px / `r`, which at `r ≥ 64` is **under 2 coarse px**, so the
  archive geometry becomes a *tight* check exactly where the inlier counts
  become small). `wrong_pass` as REAL-DATA-07 defines it.
- **(b) Coarse pixel count** `N_r` = jointly valid pixels of the coarse source
  after orientation; keypoint counts on both images; putative count.
- **(c) Rung consistency, in coarse px** (successes only): the median over an
  8 px coarse grid of `‖ T̂_r(x) − S_r ∘ T_2 ∘ S_r⁻¹(x) ‖`, where `T_2` is the
  **recorded** native-rung transform of the same edge from
  `rows_rd03_nue.json` / `rows_rd04_nue.json` (field
  `transform_matrix_original_pixels`, in original tile pixels — E-040; **never**
  `transform_matrix`) and `S_r` is `TileWindow.from_frame` at decimation `r`
  (contract C4's `(r − 1) / 2` offset included). This is agreement with the
  native solution, whose engine agreement is ≤ 2.16 px native (D-051) — a
  **precision-class** statement, not accuracy, and Part 2 will not call it
  accuracy.
- **(d) Recovered scale** (arm N): `|det(A)|^{1/2}` of the affine's linear part
  against the known `r / 2`.
- **(e)** The verdict status and confidence, `model_selected_by`,
  `grid_occupancy` (D-055) — reported.
- **(f)** Arm L: peak offset, PSR, sizes.

### 2.3 Two readings of "the limit", and the design that tells them apart

§2.2 asks *descriptor failure or sampling starvation?* Both predict failure at
large `r`; they differ in **what** the failure is a function of. Over the full
window, `r` and `N_r` are perfectly confounded (`N_r ∝ 1 / r²`), so a ladder
alone cannot answer the question — which is why EXP-007 tier 2 could not.
Arm X breaks the confound with one extra cell per rung: same `N`, half the
`r`. Pooled over pairs and rungs, the model

```
logit P(success) = β₀ + β_N · log₂ N + β_r · log₂ r
```

has **3 parameters** against **≈ 13 pairs × 7 rungs × 2 arms ≈ 180 cells**
(E-041), and the two hypotheses are its two coefficients: starvation says
`β_N > 0` and `β_r ≈ 0`; descriptor says `β_r < 0` at fixed `N`. Beside the
fit, the model-free version: the **concordance** between the full-`r` cell
and the cropped-`r/2` cell across all (pair, r ≥ 8), with the discordant
counts in both directions and an exact McNemar p.

### 2.4 The pixel floor N*, and what it decides

The smallest coarse pixel count at which arm D succeeds on ≥ 50 % of the
pairs that reach it is **N***, read off the pooled (`N`, success) table on a
log₂ grid of `N` (bins of one octave). N* is the number the deliverable can
carry to any sensor pairing: a pairing is *reachable* by degradation when the
coarser image's overlap holds more than N* pixels. §5 does that arithmetic for
the PS's own pairings, and it is arithmetic, not evidence.

## 3. Data, fixed in advance

No new byte is fetched. Every window is on disk and every frame's geometry is
in `data/manifests/`.

**Population A — the 14 REAL-DATA-07 pairs inside the illumination envelope.**
Every B1 `north_up` row of `rows_rd03_nue.json` and `rows_rd04_nue.json` with
`delta_incidence_deg ≤ 15.0` — the range in which the amended RD-07 run
succeeds at 0.786 (11 of 14; EXP-018 §2.1). Illumination is thereby held
*inside* the envelope so that the ladder varies scale and not Sun. The 14 are
listed here from the rows, so no pair can be added or dropped later
(direction as recorded in `edge`; native `n_inliers` is the S0 reproduction
target):

| window | edge (source → reference) | Δinc | native n_inliers | native outcome |
|---|---|---|---|---|
| RD03 | m1271742202lc → m1182331886lc | 13.79 | 1656 | success |
| RD03 | m1182331886lc → m1212932972lc | 1.74 | 5437 | success |
| RD03 | m1236465772rc → m1175268993rc | 4.03 | 8239 | success |
| RD03 | m1212932972lc → m1363396554rc | 6.92 | 3486 | success |
| RD03 | m1452560468lc → m1335207975rc | 0.96 | 5392 | success |
| RD03 | m1096350825rc → m1142297886lc | 2.36 | 7554 | success |
| RD03 | m1199981485rc → m1142297886lc | 7.77 | 4 | **fail** |
| RD03 | m1335207975rc → m1142297886lc | 4.89 | 5 | **fail** |
| RD04 | m1299958135lc → m1315225542lc | 2.91 | 2726 | success |
| RD04 | m1299958135lc → m1271742202lc | 11.73 | 1608 | success |
| RD04 | m1315225542lc → m1271742202lc | 8.82 | 2138 | success |
| RD04 | m1271742202lc → m1341069775rc | 12.48 | 47 | success |
| RD04 | m1212932972lc → m1363396554rc | 6.92 | 2597 | success |
| RD04 | m1341069775rc → m1212932972lc | 3.05 | 8 | **fail** |

*(Where the artefact holds two B1 north-up rows for one edge, the row whose
`n_inliers` is listed above is the one the runner must reproduce; it names
the row it used.)* The three native **failures** are carried through every
rung and reported in their own stratum: a pair the pipeline cannot register
at 1 : 1 cannot be evidence about scale, in either direction. **The S1–S4
population is the 11 native successes.** Tiles are 4096 × 2048 native pixels;
at `r = 320` the coarse image is **12 × 6 px**.

**Population B — the two low-Δinc long windows (12288 × 5064 native).**
`exp007_long_triplet_abc` (target 22.034° E, 20.035° N): edge
**m1335207975rc → m1452560468lc**, Δinc 0.96°, EXP-007 tier 1 `k = 2`
**5365** inliers, tier 2 `k = 4 / 8 / 16 / 32` = **9460 / 3054 / 1373 / 566**.
`exp007_long_triplet_abd` (22.010° E, 19.666° N): edge
**m1299958135lc → m1271742202lc**, Δinc 11.73°, tier 1 **1656**, tier 2
**3693 / 1665 / 693 / 243**. These eight recorded counts are S0's operator
gate. At `r = 320` a long window is **38 × 15 px**. The recorded 4096-line
tiles of the same frames lie inside these windows (A `l17955` ⊂ `l13859`
window, `l6413` ⊂ `l2317`; B `l29822` ⊂ `l25726`, `l18077` ⊂ `l13981`; C
`l9088` ⊂ `l4992`; D `l42463` ⊂ `l38367`) and are arm L's templates.

**Ladder, identical on every pair:** `r ∈ {2, 4, 8, 16, 32, 64, 128, 320}`.
`r = 2` is the recorded native rung and is reproduced, not re-measured;
`r = 1` (62 Mpx SIFT on a long window) is not run and is said to be not run.
Arm N at `r ∈ {4, 8, 16, 32}`; arm X at `r ∈ {8, …, 320}` (cropped rung
`r / 2`); arm L at `r ∈ {32, 64, 128, 320}`; B4L at `r ≥ 8`, reported.

**Cost.** Population A: 14 × (7 rungs D + 6 X + 4 N) ≈ 240 B1 registrations
on images ≤ 1024 × 512 px; population B: 2 × the same on images ≤ 3072 × 1266
px at `r = 4`; the `r = 2` long-window reproduction (6144 × 2532) twice; B4L
≈ 100 small cells. Predicted **1–2 h CPU**.

**Runner and artefact.** `scripts/run_exp016.py`, written only after this
Part 1 is committed; `experiments/EXP-016/exp016_results.json`; refuses to
overwrite (integrity rule 4). The runner **imports** `run_exp007.geometry_check`,
`run_exp007.FrameContext`, `run_real_data_07.run_edge`'s orientation route and
`siim.preprocessing.degrade.degrade_to_gsd`; nothing is re-implemented.

## 4. Success criteria — frozen

| ID | Criterion | MET if |
|---|---|---|
| **S0** | **Harness and provenance controls. Nothing is reported from a cell unless every clause holds.** | (i) `degrade_to_gsd(·, k, psf = 0)` equals `run_exp007.decimate(·, k)` **bit for bit** on every window at every `k`; (ii) **operator gate:** with `psf = 0` and EXP-007's orientation, the runner reproduces all **eight** tier-2 counts of population B **exactly** (9460 / 3054 / 1373 / 566; 3693 / 1665 / 693 / 243) and both tier-1 counts (5365, 1656); (iii) **native gate:** at `r = 2` the runner reproduces every population-A `n_inliers` in the table **exactly** through `run_real_data_07.run_edge`; (iv) **self-scale control:** for each pair and rung, `C_r(P)` against `C_r(P shifted by an integer multiple of r native px)` recovers the shift to **< 0.05 coarse px** wherever `N_r ≥ 1024`, else CANNOT CHECK, and returns ≥ 9 inliers wherever `N_r ≥ 4096` (if it does not, the detector — not the pair — is starved at that `N`, and that cell is a *floor* measurement, reported); (v) every frame's Jacobian-determinant sign (E-037) is recorded and `north_up_east_right` applied; (vi) `N_r`, both keypoint counts and the putative count are recorded in every cell |
| **S1** | **The §2.2 acceptance, verbatim: "Every rung ≤ 320:1 registers when overlap ≥ 50 % of the coarser tile."** | Arm D succeeds (§2.2(a)) on **≥ 10 of the 11** native-success pairs at **every** rung of the ladder including 320. The **envelope** — the largest `r` at which the ≥ 10 / 11 clause still holds — is reported whatever it is, with per-rung success counts, and is the deliverable's number. Population B is reported beside on its own two rows |
| **S2** | **Descriptor failure or sampling starvation (§2.3).** | Over all (pair, `r ≥ 8`) cells of the 11 pairs: concordance between the full-`r` cell and the cropped-`r/2` cell is **≥ 80 %**, and in the logistic fit `β_N` is positive with `p < 0.05` while `β_r` is **not** significantly negative at `p < 0.05`. Both must hold for **STARVATION**; `β_r` significantly negative with concordance < 80 % is **DESCRIPTOR**; anything else is **UNRESOLVED**, and the discordant counts in both directions are printed beside the verdict |
| **S3** | **The architecture's step beats not taking it (RL-051b).** | On the 11 pairs at each `r ∈ {4, 8, 16, 32}`, arm D's success count is **≥** arm N's, and pooled over the four rungs the exact McNemar test on discordant pairs gives **p < 0.05** in D's favour. Reported beside: arm N's recovered scale against `r / 2`, and the rungs at which N's failures are `n_inliers ≤ 8` versus geometry-INCONSISTENT |
| **S4** | **Error in coarser-image pixels.** | On **≥ 90 %** of arm-D successes across all rungs, rung consistency (§2.2(c)) is **≤ 1.0 coarse px** *and* the geometry check is not INCONSISTENT. Reported per rung as median / p90 in coarse px **and** in metres. This is agreement with the native-rung solution and is labelled so |
| **S5** | **320:1 as localisation (§345).** | Arm L localises the template to within **max(1.5, floor_r)** coarse px of the geometry prediction — `floor_r` the geometry check's own discrimination floor in coarse px — with **PSR ≥ 5**, on **both** population-B pairs at `r = 320`. The largest `r` at which both localise is reported as the localisation envelope, with the peak offsets and PSRs at every rung |

**Parameter counts against constraints (E-041), in one place:**

| statistic | fitted parameters | constraints | null / reference |
|---|---|---|---|
| affine per cell | 6 | ≥ 9 inliers by the rule; typically 10²–10³ at `r ≤ 16` | archive geometry at its floor (coarse px) |
| rung consistency | 0 | 8 px coarse grid (≥ 50 points at `r = 320` on a long window; on a 12 × 6 tile the grid has **1–2 points and the cell is CANNOT CHECK**) | the recorded `T_2` |
| logistic (S2) | 3 | ≈ 150–180 cells | Wald p on each coefficient |
| concordance (S2) | 0 | ≈ 70 cell pairs | exact McNemar |
| McNemar (S3) | 0 | 44 paired cells | exact binomial on discordants |
| N* | 0 | octave bins of `N` | — |
| NCC (S5) | 0 | one map per cell | PSR ≥ 5, a stated constant |

**Predicted outcome, recorded now so it can be wrong.**

- **S0 MET** — HIGH for (i)–(iii), (v), (vi): the operator is the same code
  path with `psf = 0`, and EXP-012 reproduced 22 / 22 recorded counts on this
  environment. (iv) — MEDIUM: the self-scale control is predicted to **fail
  the inlier clause below N ≈ 2 000–4 000 px**, which is the point of it —
  the detector floor is measured on an identical-texture pair before any
  cross-frame cell is read.
- **S1 NOT MET** — HIGH. Predicted envelope **r* = 32** (MEDIUM; 16–64 at
  MEDIUM-HIGH): at `r = 32` a tile is 128 × 64 px; EXP-007 tier 2 kept
  566 / 243 inliers at `k = 32` on 384 × 158 long windows and REAL-DATA-08
  found B1 starved at 111 × 46. At `r = 64` (64 × 32 px) predicted ≤ 5 / 11;
  at 128 and 320 predicted **0 / 11**. Population B predicted to reach 64
  (MEDIUM), not 128.
- **S2 → STARVATION** — MEDIUM-HIGH. `β_N` positive, `β_r` indistinguishable
  from zero; concordance ≥ 85 %. **N* ≈ 4 000–16 000 px** — LOW-MEDIUM. If
  instead the cropped `r / 2` cells succeed where full-`r` cells fail, §19 is
  wrong and the descriptor's scale-space is the limit — and the honest
  reading would then be that PSF-degradation *costs* matchable structure the
  descriptor could have used.
- **S3 MET** — HIGH from `r ≥ 8`; at `r = 4` (a 2 : 1 gap) predicted a **tie**
  (MEDIUM): SIFT's own octaves cover one doubling. Arm N's failures at
  `r ≥ 16` predicted to be `n_inliers ≤ 8`, not wrong passes (MEDIUM-HIGH);
  its recovered scale where it succeeds predicted within 2 % of `r / 2`.
- **S4 MET** — MEDIUM-HIGH: consistency predicted 0.2–0.6 coarse px median to
  `r = 32`, rising toward 1 px at the last succeeding rung as the inlier
  count falls. Note the trivial direction: **the same 1.0 coarse-px bound is
  32 m at `r = 32` and 320 m at `r = 320`**, and Part 2 prints the metres
  beside the pixels so that "sub-pixel in coarse pixels" cannot be read as a
  fine-pixel claim.
- **S5 NOT MET** — MEDIUM: at `r = 320` the template is **12 × 6 px** (72
  samples of mare) inside a **38 × 15** search image; NCC has ~600 candidate
  positions and 72 samples, and PSR ≥ 5 is predicted not to be reached.
  Localisation envelope predicted **128** (LOW-MEDIUM; 64 at MEDIUM).
- **Secondary:** B4L predicted to extend arm D's envelope by one rung
  (MEDIUM; RD-08's pattern) and to produce ≥ 1 wrong pass somewhere in the
  ladder (MEDIUM; RD-08 D-050). `grid_occupancy` predicted to fall with `r`
  on ≥ 9 / 11 pairs.

## 5. Physical limits, in numbers

At a native NAC pixel of ≈ 1.0 m (population A frames 1.04–1.29 m;
population B 0.82–1.05 m; the per-frame value is read from the archive):

| r | coarse GSD (≈ m) | tile 4096 × 2048 → | long window 12288 × 5064 → | native 100 px geometry floor in coarse px |
|---|---|---|---|---|
| 2 | 2 | 2048 × 1024 | 6144 × 2532 | 50 |
| 4 | 4 | 1024 × 512 | 3072 × 1266 | 25 |
| 8 | 8 | 512 × 256 | 1536 × 633 | 12.5 |
| 16 | 16 | 256 × 128 | 768 × 316 | 6.3 |
| 32 | 32 | 128 × 64 | 384 × 158 | 3.1 |
| 64 | 64 | 64 × 32 | 192 × 79 | 1.6 |
| 128 | 128 | 32 × 16 | 96 × 39 | 0.8 |
| 320 | 320 | **12 × 6** | **38 × 15** | 0.3 |

- **What the PS's pairings are in coarse pixels of overlap** (§345's
  geometry, arithmetic only): TMC-2 ↔ NAC at 5–10 : 1 — a 4096-line NAC tile
  is 400–800 × 200–400 TMC-2 px; IIRS ↔ NAC at 40–160 : 1 — 25–100 × 13–50
  IIRS px per tile, **512 × 256 at 8 : 1 over a long window** and 77 × 32 at
  160 : 1; OHRC ↔ IIRS at 320 : 1 — an OHRC frame (≈ 12 × 3 km at 0.25 m) is
  **≈ 150 × 37 = 5 550 IIRS px**, which is **~4× more pixels than the largest
  window on this disk gives at 320 : 1** (38 × 15 = 570). So the 320 : 1 rung
  here is *harsher* in pixel count than the real OHRC-in-IIRS case; whether
  that case is reachable is decided by N* (§2.4), not by this ladder's last
  cell, and Part 2 says which side of N* 5 550 falls on.
- **Detector arithmetic.** SIFT's first octave needs ≥ 2 × (3 + 3) scale
  samples; a 12 × 6 image has **zero** DoG extrema that survive the border
  rule. The 320 : 1 tile cell is predicted to record `n_keypoints = 0`, which
  is a measurement of the instrument, not of the pair.
- **The geometry floor tightens with r.** The corner-map quantisation floor
  (≈ 84–103 native px, RD-07) is **≈ 1.3–1.6 coarse px at r = 64**. A
  coarse-rung wrong pass therefore needs only a ~2 px error to be caught,
  where the native rung needs ~250 px — the *opposite* regime from REAL-DATA-07,
  and S4's geometry clause is correspondingly stronger at the top of the
  ladder than at the bottom.
- **What degradation loses.** Under the architecture, the source's native
  information above the coarse Nyquist is discarded before matching, by
  design: sub-pixel *in coarse pixels* is the only accuracy that can exist,
  and 0.5 coarse px is **16 m at 32 : 1, 160 m at 320 : 1**. §19 says so; the
  PS's phrase "sub-pixel accuracy of the source image" is, for the coarse
  rungs, satisfiable only in this sense, and the deliverable defines it so.

## 6. What may not happen in Part 2

- The ladder may not be extended, thinned or re-spaced; the envelope is read
  at the ladder's own resolution (one rung).
- **The population is the 14 rows in §3's table.** No pair enters or leaves;
  the three native failures are reported in their stratum and never pooled
  with the eleven.
- The PSF FWHM (1.0 coarse px) and the RANSAC threshold (3.0 px at every
  rung) may not change. B4L, the second engine, stays outside every
  criterion.
- S2's 80 % concordance and 0.05 significance, S3's rung set, S4's 1.0 coarse
  px and 90 %, S5's PSR ≥ 5 and tolerance rule may not move.
- N* may not be redefined after the table is seen; it is the octave-binned
  ≥ 50 % point, and if the table never reaches 50 % at any bin N* is
  reported as *above the largest N run*, not extrapolated.
- No cell may be re-run with a different seed, orientation or engine; a
  failed cell is a failed cell.
- §19's envelope sentence may not be *re-read* to fit the result; if S1 is
  NOT MET, §19's "every PS rung ≤ 320:1 is reachable by degradation" is
  recorded as **refuted on NAC-derived data at the measured N***, with the
  OHRC-in-IIRS arithmetic beside it, by a recorded note.
- A criterion that passes vacuously — S4 because only two rungs succeed, S3
  at `r = 4` because both arms succeed everywhere — is reported as *MET, and
  here is why that is not reassurance*, beside the criterion, never folded
  into it.

## 7. What this stage explicitly does NOT claim

- **Not a cross-sensor result.** The "coarse sensor" is a NAC frame through a
  Gaussian PSF. A real IIRS or TMC-2 pixel has its own MTF, its own
  radiometry, its own along-track smear; REAL-DATA-08's WAC and REAL-DATA-09's
  TMC-2 are the only real coarse references in this repository, and both are
  reported where they were reported, not here.
- **Not accuracy.** No ground truth. Rung consistency is agreement with the
  native-rung solution; the geometry check corroborates at its floor. Nothing
  here is sub-pixel in any frame's *native* pixels beyond `r = 2`.
- **Not a 320 : 1 result for OHRC ↔ IIRS.** The largest window on disk gives
  570 px at 320 : 1; the OHRC-in-IIRS case has ≈ 5 550. The ladder measures
  N*; the OHRC case is arithmetic against it.
- **Not illumination, viewpoint or modality.** Δinc ≤ 15° by construction;
  near-nadir; one instrument. One region (Mare Serenitatis), one terrain class.
- **Not a matcher claim** beyond B1; B4L is reported beside.
- **Not a verdict change.** `assess()`, `select_model`, the RANSAC threshold
  and the pipeline order are untouched; a wrong pass at a coarse rung is
  recorded beside the verdict, not patched.

## 8. Reported beside the criteria, not part of any

- B4L on arm D at `r ≥ 8`: success per rung, wrong passes, envelope.
- The three native-failure pairs at every rung and arm.
- Arm N's recovered scale and the failure kind per rung.
- `grid_occupancy` and `max_uncovered_disc_ratio` per cell (D-055 order).
- Keypoint and putative counts per cell — the raw starvation curve.
- The self-scale control's inlier count per (pair, rung): the detector floor
  on identical texture.
- Rung consistency in metres beside pixels, per rung.
- Arm L at every rung: peak offset, PSR, sizes — including the cells below
  the PSR bar.

---

## Part 2 — what happened

**Run 2026-09-23, `scripts/run_exp016.py`, one run, 488 cells, 11 685 s
(3 h 15 m) on CPU. Artefact `experiments/EXP-016/exp016_results.json`
(1.85 MB), written once; the runner refuses to overwrite it.** Two earlier
launches died before writing anything (`run_died_v1`, `run_died_v2` logs are
kept beside it); no statistic from either survives, because neither reached
`evaluate()`.

> **Headline.** The problem statement's scale acceptance is **NOT MET**, and
> the measured envelope is **32 : 1**. The ceiling is **not the ratio** — the
> control that halves the ratio at a fixed pixel count agrees with the full
> cell on **55 of 60** cases and the ratio's fitted coefficient is
> **+0.00018 (p = 0.9998)** against pixel count's **+2.04 (p = 0.0025)** — so
> the limit is **sampling starvation** at a measured floor of **N\* = 2048
> coarse pixels**, which is a number any sensor pairing can be checked
> against. And the architecture's own scale-normalisation step — D-005's
> "required first-class pipeline stage" — **did not beat not taking it
> anywhere on the ladder**: arm N succeeded **10 of 10 at every rung it was
> run at**, exactly as arm D did, so the pre-registered McNemar has **zero
> discordant pairs** and S3 is NOT MET as a **null by construction**. The
> stage set out to measure where scale breaks and also refuted one of its own
> architecture's decisions, by the ablation it pre-registered for that purpose.

### 0. S0 — **NOT MET**, on two clauses, and the second one matters

Part 1's S0 opens with *"Nothing is reported from a cell unless every clause
holds."* Two clauses do not hold. **Everything below is nevertheless reported,
beside this failure and never folded into it**, because silently withholding
the stage would be re-scoping in the other direction — and because both
failures are measured, not guessed, so a reader can price them.

**(i) bit-exactness — NOT MET on 4 of 30 cells, all at k = 32.**
`degrade_to_gsd(·, k, psf = 0)` and `run_exp007.decimate(·, k)` are the same
crop-reshape-`nanmean` in exact arithmetic, and they agree **exactly** at
k = 2, 4, 8, 16 on every window. At k = 32 they differ on the two long
windows of population B. The artefact records only `equal: false`, which is
insufficient, so the discrepancy was **measured afterwards on the same
windows** (a control, not a recorded statistic):

| window / frame | k | max abs diff (DN) | relative | coarse px differing |
|---|---|---|---|---|
| RD03-target `m1271742202lc` | 16 | **0** | 0 | 0 of 240 384 |
| RD03-target `m1271742202lc` | 32 | 4.069 × 10⁻⁵ | 2.9 × 10⁻⁸ | 266 of 60 288 |
| RD04-target `m1299958135lc` | 16 | **0** | 0 | 0 of 240 384 |
| RD04-target `m1299958135lc` | 32 | 8.138 × 10⁻⁵ | 4.7 × 10⁻⁸ | 251 of 60 288 |

**The cause is a dtype, not an operator.** `decimate` accumulates `nanmean`
in the array's own **float32**; `degrade_to_gsd` casts to **float64** first.
Summing 1 024 float32 samples (k = 32) loses the last bits; summing 256
(k ≤ 16) does not. The two functions are the same function over the reals and
different functions over IEEE-754, and the criterion said *bit for bit*.
**It is NOT MET, it is not a defect in either operator, and both statements
are true at once** — recorded as **E-055**.

**(iv) the self-scale control — NOT MET on 15 of 112 cells.** Degrading a
window and matching it against the *same window shifted by an integer
multiple of `r` native pixels* must recover that shift to < 0.05 coarse px
wherever N ≥ 1024. Per rung:

| r | cells | shift-clause failures | median error (coarse px) | worst | median N |
|---|---|---|---|---|---|
| 4 | 16 | **4** | 0.0040 | **0.591** | 519 689 |
| 8 | 16 | **2** | 0.0053 | 0.373 | 128 777 |
| 16 | 16 | 0 | 0.0070 | 0.013 | 31 625 |
| 32 | 16 | **1** | 0.0135 | 0.099 | 7 625 |
| 64 | 16 | **8** | 0.0374 | 0.356 | 1 769 |
| 128 | 16 | 0 (N < 1024 → CANNOT CHECK) | 0.158 | 5.33 | 377 |
| 320 | 16 | 0 (CANNOT CHECK) | — | — | 27 |

The **inlier** clause — the one Part 1 predicted would fail — did **not fail
once**. The clause that failed is the one Part 1 was confident about. The
typical cell is two orders of magnitude inside the bound (medians 0.004–0.037
px); the failures are a tail, and eight of them sit at r = 64, the rung where
S1's envelope is decided.

**What that costs, stated plainly.** On identical texture with a known answer,
this harness's own recovery error reaches **0.59 coarse px at r = 4** and
**0.36 at r = 64** on some pairs. S4 reports rung consistency of **0.26 / 0.09
coarse px** at those rungs. **On the pairs where the control failed, the
number S4 reports is at or below the harness's own demonstrated floor**, so
S4's pass may not be read as *"the coarse solution agrees with the native one
to better than a tenth of a coarse pixel"* — only as *"it agrees to within a
bound that the harness cannot itself resolve on those cells"*. This is
recorded beside S4 and not folded into it.

**Clauses (ii), (iii), (v), (vi) — MET.** The operator gate reproduced all
**eight** population-B tier-2 counts and both tier-1 counts **exactly**
(9460 / 3054 / 1373 / 566 and 3693 / 1665 / 693 / 243, transform max-abs-diff
**0.0**), the native gate reproduced every population-A `n_inliers` in §3's
table exactly, every frame's Jacobian-determinant sign is recorded with
`north_up_east_right` applied, and `N`, both keypoint counts and the putative
count are present in every D / N / X cell.

### 1. S1 — **NOT MET**. The envelope is **32 : 1**

| r | coarse tile | pairs run | success | wrong pass | median N | median kp (src) | median putative | median inliers |
|---|---|---|---|---|---|---|---|---|
| 4 | 1024 × 512 | 11 | **11** | 0 | 524 288 | 3 897 | 1 379 | 1 355 |
| 8 | 512 × 256 | 11 | **11** | 0 | 131 072 | 1 345 | 500 | 500 |
| 16 | 256 × 128 | 11 | **11** | 0 | 32 768 | 537 | 206 | 206 |
| 32 | 128 × 64 | 11 | **11** | 0 | 8 192 | 152 | 55 | 54 |
| 64 | 64 × 32 | 11 | 8 | 0 | 2 048 | 34 | 12 | 11 |
| 128 | 32 × 16 | 11 | **0** | 0 | 512 | 6 | 2 | 0 |
| 320 | 12 × 6 | 11 | **0** | 0 | 72 | **0** | 0 | 0 |

**Every failure is the frozen inlier rule (`n_inliers ≤ 8`), never the
geometry check.** Across the 77 arm-D cells the archive geometry returned
**CONSISTENT 55 times, INCONCLUSIVE 5 times and INCONSISTENT never**, and
there are **zero wrong passes at any rung** — which is the interesting half of
a negative result: at r = 64 the geometry floor is ≈ 1.6 coarse px, so a
wrong pass needed only a ~2 px error to be caught, and none was.

The clause is *≥ 10 of the native-success pairs at every rung*. It holds to
r = 32 and breaks at 64 with 8. **Envelope = 32 : 1.**

*Bookkeeping, stated because the artefact's two fields disagree and a reader
will notice:* the 11 native-success rows of §3's table contain **10 distinct
edges** — `m1212932972lc → m1363396554rc` appears in both the RD03 and the
RD04 window as two separate tile pairs. The runner therefore prints
`n_pairs: 10` (distinct edges) while every per-rung count is over **11 cells**.
No pair entered or left; the frozen population is unchanged.

**Population B, the two long windows**, reported beside on their own rows:
the RD03 window (`m1335207975rc → m1452560468lc`, Δinc 0.96°) succeeds to
**r = 64** (104 inliers) and fails at 128 (7); the RD04 window
(`m1299958135lc → m1271742202lc`, Δinc 11.73°) succeeds to **r = 128** (21
inliers) and fails at 320 (0). Nine times the pixels buys one to two more
rungs — which is S2's answer arriving early.

### 2. S2 — **STARVATION**, and the ratio's coefficient is indistinguishable from zero

| test | value |
|---|---|
| concordance, full-`r` vs cropped-`r/2` | **0.9167** (55 of 60 cells agree) — bar was 0.80 |
| discordant | 2 full-only, 3 cropped-only; exact McNemar **p = 1.0** |
| logistic, n = 143 cells | `β_N = +2.0382`, **p = 0.00245**; `β_r = +0.000178`, **p = 0.99983** |
| **N\*** | **2 048 coarse pixels** (smallest octave bin ≥ 50 % success) |

Both S2 clauses hold: `β_N` positive and significant, `β_r` not significantly
negative, concordance ≥ 80 %. **Verdict: STARVATION.** The ratio coefficient
is not merely insignificant — it is **+1.8 × 10⁻⁴**, four orders of magnitude
smaller than the pixel-count coefficient and of the wrong sign for the
descriptor hypothesis. Halving the ratio while holding the pixel count fixed
changes nothing; the five disagreements split 2 / 3, i.e. noise.

The octave table is the deliverable's number:

| N (coarse px) | cells | success |
|---|---|---|
| 2⁶–2⁷ (≈ 72) | 11 | **0 %** |
| 2⁹–2¹⁰ (≈ 512) | 11 | **0 %** |
| 2¹¹–2¹² (≈ 2 048) | 11 | **72.7 %** |
| 2¹³–2¹⁴ (≈ 8 192) | 11 | 100 % |
| ≥ 2¹⁵ | 33 | 100 % |

**N\* = 2048.** Pooling arm X with arm D (143 cells) gives the same N\*, which
is the model-free version of the same statement.

**What N\* decides, as arithmetic and not as evidence** (§5's pairings):

| pairing | ratio | coarse px over the stated window | above N\* = 2048? |
|---|---|---|---|
| TMC-2 ↔ NAC | 5–10 : 1 | 400 × 200 … 800 × 400 = 80 000–320 000 | **yes, by 40–160×** |
| IIRS ↔ NAC, one 4096-line tile | 40–160 : 1 | 25 × 13 … 100 × 50 = 325–5 000 | **marginal** |
| IIRS ↔ NAC, a long window | 8 : 1 equivalent | 512 × 256 = 131 072 | **yes** |
| OHRC ↔ IIRS | 320 : 1 | ≈ 150 × 37 = **5 550** | **yes, by 2.7×** |

So the 320 : 1 rung's failure **here** is a statement about the 570 pixels the
largest window on this disk gives at that ratio, not about OHRC-in-IIRS, which
has ≈ 5 550 — above N\* and inside the 72.7 % bin's neighbourhood. The
deliverable states it exactly that way: **the ratio is not what stops the
registration; the pixel count is, and the pixel count of the real pairing is
arithmetic against 2 048.**

### 3. S3 — **NOT MET**, and it is the architecture that loses

| r | gap arm N must bridge | arm D success | arm N success | D-only | N-only | N failure kind |
|---|---|---|---|---|---|---|
| 4 | 2 : 1 | 10 / 10 | **10 / 10** | 0 | 0 | none |
| 8 | 4 : 1 | 10 / 10 | **10 / 10** | 0 | 0 | none |
| 16 | 8 : 1 | 10 / 10 | **10 / 10** | 0 | 0 | none |
| 32 | **16 : 1** | 10 / 10 | **10 / 10** | 0 | 0 | none |

Pooled discordant pairs: **b = 0, c = 0.** The exact McNemar test **cannot
run** — there is nothing for it to run on. S3's first clause (*arm D ≥ arm N
at every rung*) holds **as a tie at every rung**; its second (*p < 0.05 in
D's favour*) is unreachable. **S3 is NOT MET, as a null by construction**, and
the runner says so in its own `vacuity_note`.

**The consequence was fixed in Part 1 and is not being re-read now:**

> *Normalising to the coarse GSD does not beat matching across the gap
> (S3 NOT MET) ⇒ the architecture's scale stage (D-005, "required first-class
> pipeline stage") is refuted by its own ablation and D-005 is superseded.*

**It is superseded — by D-005-N1, a note, not an edit.** The measured
statement is narrower than "the step is useless" and is written that way:
*on real mare NAC texture inside the illumination envelope, across GSD gaps up
to 16 : 1, RootSIFT's own scale space bridges the gap unaided on every pair
the normalised arm also registers, so the normalisation step has no measured
benefit on this terrain in this range.* It may still matter above 16 : 1,
where arm N was not run — and Part 1 fixed the rung set, so it was not
extended after the result was seen.

Arm N's **recovered scale** against the known `r / 2`: median **0.393–0.553
at an expected 0.5** and the same ±10 % spread at every rung (0.196–0.276 at
0.25; 0.098–0.138 at 0.125; 0.049–0.069 at 0.0625). Part 1 predicted **within
2 %**; the measured spread is **five times wider**, which is the one respect
in which the un-normalised arm is visibly worse — it registers, and the
similarity it recovers is off by up to 10 %.

### 4. S4 — **MET (0.977)**, with two reasons that is less than it sounds

**43 of 44 checked arm-D successes** are within 1.0 coarse px of the recorded
native-rung solution *and* not geometry-INCONSISTENT. The single failure is
`m1271742202lc → m1341069775rc` at r = 16, at **1.068** coarse px.

| r | cells | median (coarse px) | median (m) | p90 (coarse px) | p90 (m) |
|---|---|---|---|---|---|
| 4 | 11 | 0.2577 | **1.16** | 0.4366 | 1.97 |
| 8 | 11 | 0.1366 | **1.11** | 0.2353 | 1.97 |
| 16 | 11 | 0.1108 | **2.03** | 0.1853 | 2.99 |
| 32 | 11 | 0.0939 | **2.93** | 0.1342 | 4.60 |

**The metres are printed beside the pixels because they move the other way.**
The agreement improves monotonically in coarse pixels (0.258 → 0.094) and
**worsens monotonically on the ground** (1.16 m → 2.93 m). A reader who quotes
"0.09 coarse px at 32 : 1" without the 2.93 m has quoted the pixel that got
larger. Part 1 pre-committed to this sentence and it is kept.

**Why the pass is not reassurance, twice over:**

1. **All eight successes at r = 64 are CANNOT CHECK** — a 64 × 32 coarse tile
   does not carry enough 8-px grid points. So S4 is silent exactly at the rung
   where the envelope is decided, and its 97.7 % is computed on r ≤ 32 only.
2. **S0(iv) failed on some of these very pairs** (§0): where the self-scale
   control could not recover a known shift better than 0.36–0.59 coarse px,
   a reported consistency of 0.09–0.26 coarse px is inside the harness's own
   floor and is a bound, not a measurement.

And the label, unchanged from Part 1: **this is agreement with the native-rung
solution — a precision-class statement. It is not accuracy.** The native
solution's own engine agreement is ≤ 2.16 native px (D-051).

### 5. S5 — **NOT MET**. Localisation envelope: **none**

| window | r | template | search | offset (coarse px) | offset (m) | tolerance | PSR | localised |
|---|---|---|---|---|---|---|---|---|
| RD03-target | 32 | 128 × 64 | 384 × 158 | 9.577 | **306.5** | 7.089 | 9.23 | no |
| RD03-target | 64 | 64 × 32 | 192 × 79 | 4.788 | **306.5** | 3.901 | 9.32 | no |
| RD03-target | 128 | 32 × 16 | 96 × 39 | 2.394 | **306.5** | 1.953 | 7.95 | no |
| RD03-target | 320 | **12 × 6** | 38 × 15 | 0.818 | 261.6 | 1.500 | **4.50** | no |
| RD04-target | 32 | 128 × 64 | 384 × 158 | 1.945 | 62.2 | 6.645 | 5.57 | **yes** |
| RD04-target | 64 | 64 × 32 | 192 × 79 | 1.306 | 83.6 | 3.532 | 5.57 | **yes** |
| RD04-target | 128 | 32 × 16 | 96 × 39 | 0.414 | 53.1 | 1.748 | 5.50 | **yes** |
| RD04-target | 320 | **12 × 6** | 38 × 15 | 0.329 | 105.2 | 1.500 | **4.23** | no |

S5 needs **both** windows at r = 320; neither reaches PSR 5 there, so S5 is
NOT MET. No rung has both windows localised, so the **localisation envelope is
`None`**.

**Two different things failed, and collapsing them would be the error.**

* **At r = 320 the peak is in the right place and the confidence is not
  there.** Both offsets — 0.82 and 0.33 coarse px, i.e. **262 m and 105 m** —
  are *inside* the 1.5 px tolerance. What fails is **PSR: 4.50 and 4.23
  against the frozen 5**. A 12 × 6 template (72 mare samples) in a 38 × 15
  search image produces a peak that is right and not sharp, exactly as Part 1
  predicted at MEDIUM. **The prediction was correct and the criterion is NOT
  MET for the predicted reason.**
* **At r ≤ 128 the RD03 window fails on the *prediction*, not the peak.** Its
  offset is **306.5 m at r = 32, 64 and 128 — the same distance on the ground
  three times over**, with PSR 7.95–9.32, the sharpest peaks in the table.
  A localisation error would shrink or wander as the template grows; a
  **constant ground offset** is the archive corner map disagreeing with where
  the image content actually is. **EXP-019 measured that disagreement
  independently at 137.6 m median, systematically eastward (+101 ± 74 m)**;
  306 m is large for that distribution but the same kind of thing, and the
  tolerance this criterion uses **is** the archive's own floor (7.09 coarse px
  = 227 native px at r = 32). So S5's RD03 cells are the geometry check
  failing its own prediction, recorded as **D-067**, not the NCC failing to
  find the tile.

### 6. Reported beside the criteria

**B4L (DISK + LightGlue), arm D, r ≥ 8** — outside every criterion:

| r | 8 | 16 | 32 | 64 | 128 | 320 |
|---|---|---|---|---|---|---|
| B4L success / 11 | 11 | 11 | 11 | **5** | 0 | 0 |
| B1 success / 11 | 11 | 11 | 11 | **8** | 0 | 0 |

**B4L's envelope is 32 — the same as B1's — and at r = 64 it is worse (5 vs
8). It produced zero wrong passes.** Part 1 predicted it would *extend* the
envelope by one rung and produce *at least one* wrong pass. **Both predictions
are wrong**, and in the direction that matters for the project's own
narrative: the learned matcher's advantage on the REAL-DATA-08 proxy did not
reappear when the scale gap was built by a stated PSF instead of by two
different instruments.

**The starvation curve, raw** (medians over the 11 cells): keypoints on the
source fall **3 897 → 1 345 → 537 → 152 → 34 → 6 → 0** across the ladder.
At r = 320 a 12 × 6 image yields **zero** DoG extrema that survive the border
rule — Part 1 predicted exactly that, and it is a measurement of the detector,
not of the pair.

**Coverage** (`grid_occupancy`, D-055's primary metric) falls monotonically
with the rung: **0.969, 0.922, 0.781, 0.484, 0.156, 0.063** at r = 4…128, and
is undefined at 320. Predicted to fall on ≥ 9 / 11 pairs — correct. Note the
consequence for §53's criterion 4: **at the envelope rung the median occupancy
is 0.484**, so a coarse-rung registration that passes every other check is
also the least uniformly covered.

**The native-failure stratum, and the one result nobody predicted.** The three
edges that **fail at the native rung** were carried through every rung and
arm, and they are **not** uniformly dead: of their 69 cells, **11 succeed after
degradation**, including `m1341069775rc → m1212932972lc` at r = 8 with **994
inliers** (it fails at 1 : 1 with 8). Degrading to a coarser GSD suppresses the
high-frequency shadow texture that an illumination difference writes into the
two images, and on these three pairs that *rescues* an edge the pipeline could
not register at full resolution. **This is reported, not claimed:** n = 3
edges, the geometry check is CONSISTENT on those cells and there are no wrong
passes, but the stage was not designed to test it and it is **not** a
criterion. It is the most interesting thing in the artefact that was not asked
for, and it is written down here so that a later stage can test it properly.

### 7. Predictions, scored — including every one that was wrong

| prediction (Part 1) | confidence | outcome |
|---|---|---|
| S0 MET, (i)–(iii)/(v)/(vi) | HIGH | **WRONG** — (i) NOT MET at k = 32 (float32 vs float64) |
| S0(iv) fails the **inlier** clause below N ≈ 2 000–4 000 | MEDIUM | **WRONG** — the inlier clause failed **zero** times; the **shift** clause failed 15 times |
| S1 NOT MET | HIGH | **RIGHT** |
| envelope r\* = 32 | MEDIUM | **RIGHT** |
| ≤ 5 / 11 at r = 64 | — | **WRONG** — 8 / 11 |
| 0 / 11 at r = 128 and 320 | — | **RIGHT** |
| population B reaches 64, not 128 | MEDIUM | **HALF WRONG** — RD03 reaches 64, RD04 reaches **128** |
| S2 → STARVATION | MEDIUM-HIGH | **RIGHT** |
| concordance ≥ 85 % | — | **RIGHT** — 91.7 % |
| N\* ≈ 4 000–16 000 | LOW-MEDIUM | **WRONG** — N\* = **2 048**, below the predicted range |
| S3 MET from r ≥ 8 | HIGH | **WRONG** — arm N ties arm D at every rung; no discordant pairs |
| a tie at r = 4 | MEDIUM | **RIGHT**, and it was a tie at 8, 16 and 32 as well |
| arm N's failures are `n_inliers ≤ 8`, not wrong passes | MEDIUM-HIGH | **VACUOUS** — arm N had no failures |
| arm N's recovered scale within 2 % | — | **WRONG** — ±10 % |
| S4 MET | MEDIUM-HIGH | **RIGHT** — 0.977 |
| consistency 0.2–0.6 coarse px to r = 32 | — | **BETTER THAN PREDICTED** — 0.094–0.258 |
| consistency rises toward 1 px at the last succeeding rung | — | **NOT OBSERVABLE** — every r = 64 success is CANNOT CHECK |
| S5 NOT MET | MEDIUM | **RIGHT** |
| PSR ≥ 5 not reached at 320 | — | **RIGHT** — 4.50 and 4.23 |
| localisation envelope 128 | LOW-MEDIUM | **WRONG** — envelope is **none**; RD04 reaches 128, RD03 reaches nothing |
| B4L extends the envelope by one rung | MEDIUM | **WRONG** — same envelope, worse at r = 64 |
| B4L produces ≥ 1 wrong pass | MEDIUM | **WRONG** — zero, in either engine, at any rung |
| the 320 : 1 cell records `n_keypoints = 0` | — | **RIGHT** |
| `grid_occupancy` falls with r on ≥ 9 / 11 | — | **RIGHT** — monotone on the medians |

**Nine predictions wrong, eleven right, one vacuous, one unobservable.** The
two that cost the most are S0 (a criterion written against an operator's dtype)
and S3 (a test whose power was assumed rather than designed) — both are in the
error ledger.

### 8. What this stage changes

* **D-066** — the scale envelope on real NAC texture is **32 : 1** under the
  frozen rule, the limit is **sampling starvation** and not the ratio, and the
  deliverable's portable number is **N\* = 2 048 coarse pixels of overlap**.
  §2.2's *"every rung ≤ 320 : 1 registers"* is **NOT MET**; the replacement
  claim is a floor plus arithmetic, and the arithmetic says OHRC-in-IIRS
  (≈ 5 550 px) sits **above** the floor while a single IIRS-against-one-NAC-tile
  (325–5 000 px) sits across it.
* **D-005-N1** — D-005's scale-normalisation stage is **not supported by its
  own ablation** up to a 16 : 1 GSD gap on this terrain: arm N ties arm D
  10 / 10 at every rung run. The decision is superseded by note, the original
  row is left as written, and the narrower measured statement replaces the
  claim. *(This also retires C2 in `PROJECT_GAP_ANALYSIS.md` — D-005 was a
  permanent `PROPOSED` deferring to an experiment that never ran. It is now
  decided by a different experiment that did.)*
* **D-067** — S5's RD03 failures are the **archive corner map**, not the
  correlator: a **constant 306.5 m** offset at three rungs with the sharpest
  peaks in the run, against EXP-019's independently measured 137.6 m median
  archive-vs-control disagreement.
* **E-055** — a *bit for bit* criterion written across two implementations
  that differ only in accumulation dtype. Cost: S0(i) NOT MET at a relative
  discrepancy of 3–5 × 10⁻⁸, which gates the whole stage as frozen while being
  a defect in neither operator.
* **E-056** — a McNemar test whose power was assumed, not designed: S3 could
  only be MET if arm N failed somewhere, and Part 1's parameter table counted
  *44 paired cells* as the constraint when the real constraint is the number of
  **discordant** pairs, which turned out to be **zero**. The criterion could
  not have been MET by any tie, however strong the tie. Same family as E-041.

### 9. What is still not claimed

Everything in Part 1 §7 stands, and two things are added by the result:

* **The envelope is 32 : 1 for this construction**, in which the coarse image
  is a NAC frame through a Gaussian PSF. A real coarse sensor has its own MTF
  and radiometry, and REAL-DATA-08's WAC proxy (≈ 65 : 1, B1 1 of 4) is the
  only real cross-sensor scale evidence this project holds.
* **N\* = 2 048 is measured for B1 on mare at Δinc ≤ 15°.** It is a property of
  a detector, a terrain and an illumination range, not a constant of nature —
  and B4L, the other engine, has the same envelope and a *lower* success rate
  at the rung where it is decided.

