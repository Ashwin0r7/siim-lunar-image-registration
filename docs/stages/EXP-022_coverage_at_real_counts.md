# EXP-022 — Criterion 4 at the match counts real registrations actually have

**Part 1 — pre-registration. FROZEN 2026-09-23, before the runner exists and
before any statistic of this stage has been computed.** Part 2 is empty until
Part 1 is committed.

**Classification: DELIVERABLE-CRITICAL.** This is item B4 of
`docs/PROJECT_GAP_ANALYSIS.md` and the open direction of D-057. §53
criterion 4 is recorded as *NOT MET and MIS-SPECIFIED*. The binding reason
(RL-050c, promoted by EXP-015) is:

> *until a calibration samples occupancy above 0.938 — inlier counts in the
> thousands, not EXP-014's 12–200 point subsets — criterion 4 cannot be
> answered in either direction with evidence.*

EXP-015 restated the criterion as `grid_occupancy ≥ T` with `T = 5/64`, and it
passed 39/39. The restatement was refused on three counts: the lowest edge
sat **exactly on** the floor (margin 0), the anti-vacuity bar cleared by
0.58 pp, and **14 of 39 edges (36 %) sit at occupancy 1.0**, above everything
EXP-014 sampled, so they were judged by extrapolation. This stage removes the
extrapolation by sampling where the edges actually are. It also answers the
question criterion 4 exists for — *would this edge's point distribution bound
worst-case local error at 1 px?* — directly, per edge.

---

## 0. The requirement, quoted

> - Coverage gap ≤ 0.15 on every VERIFIED pair. — §53 criterion 4

D-055 made `grid_occupancy` the primary coverage metric; D-057 recorded the
criterion as mis-specified. This stage does **not** re-open D-055 and does
**not** edit `assess()`.

---

## 1. The question

**At the match counts and point layouts real VERIFIED edges have, where does
worst-case local error cross 1 px, and does every VERIFIED edge sit clear of
that line?**

---

## 2. What is measured

### 2.1 Population (EXP-014's instrument, at real counts)

- **Tiles:** the first 10 `*.tile.npy` in `data/processed/mare_serenitatis/`
  in sorted filename order (EXP-014's rule). Each is block-mean decimated by
  **k = 2** (`siim.preprocessing.degrade.block_mean`) to 2048 × 1024 — the frame
  in which the 39 edges' occupancy was measured. It is then scaled to [0, 1].
- **Truth:** a known similarity, `similarity(1.03, 4°, 11, −7)` (EXP-014). The
  reference is the tile warped by it. Error is measured between maps against
  that truth, never from a fit residual.
- **Pool:** RootSIFT (`run_baseline("b1")`) matches, kept only when they agree
  with the known transform to 2.0 px (EXP-014's admission rule). A tile whose
  pool is below 300 is skipped and listed. A size larger than a tile's pool is
  skipped for that tile and listed.
- **Sizes:** the 22 distinct inlier counts of the 39 VERIFIED edges (EXP-012):
  9, 28, 47, 68, 108, 143, 144, 190, 210, 265, 272, 284, 293, 1406, 1608,
  1656, 1679, 2138, 2597, 2726, 5392, 5437.
- **Shapes:** EXP-014's six: uniform, clustered, half, corner, ring and
  two_blobs (its `draw_subset`, imported). There are **3 draws** per (tile,
  shape, size).
- **Response:** the p99 of the dense endpoint error (16-px grid over the valid
  region) of an affine fit to the subset, in k2 pixels.
- **Metric:** `grid_occupancy` from `coverage_metrics(points, shape, roi)`.

### 2.2 Two arms — because self-warp matches are too clean

EXP-014's correspondences come from an image and its own warp, so their
positional noise is far below that of real cross-illumination inliers. Any
floor calibrated on them is **optimistic**. Therefore:

| arm | destination points | role |
|---|---|---|
| **N (primary)** | true matches plus iid Gaussian noise per axis, σ_N = median(recorded `fit_rmse` of the 39 VERIFIED edges) / √2 (read from `exp012_results.json`, seeded) | every criterion |
| **0** | true matches as found (EXP-014's condition) | reported beside; S0 continuity |

σ_N's formula is frozen here; its value is read by the runner and recorded.
It has **not** been computed for this document.

### 2.3 The calibrated floor and the restated criterion

- `T″` = `crossing_from_above(occupancy, p99_error, 1.0, 95)`, **imported** from
  `scripts/run_exp015.py` (itself built on EXP-014's `crossing_threshold`). It
  is the lowest occupancy above which the 95th percentile of p99 error stays
  under 1.0 px, on arm N. The bootstrap CI uses EXP-015's procedure, imported.
- **Criterion 4″:** every VERIFIED edge has `grid_occupancy ≥ T″ + 1/64`. The
  one-lattice-step margin answers EXP-015's exact-tie problem: occupancy lives
  on an 8 × 8 lattice, so a tie at the floor is a coin toss.
- **Matched cell of an edge:** the arm-N rows with `n_points` within ±25 % of
  the edge's inlier count **and** occupancy within ±1/64 of the edge's
  occupancy.

---

## 3. Success criteria — FROZEN

| ID | Criterion | MET if |
|---|---|---|
| **S0** | Harness and reproduction | (i) the imported `crossing_from_above` reproduces EXP-015's `T = 0.078125` from EXP-014's recorded real rows **exactly**; (ii) every used tile's full-pool fit has median dense error **< 0.05 px** in arm 0; (iii) the 39 edges' occupancy and inlier counts are read from `exp012_results.json`, never recomputed; (iv) σ_N is recorded with its source |
| **S1** | The regime is sampled, not extrapolated | arm N holds **≥ 30** rows with occupancy ≥ 0.99 **and ≥ 30** rows with `n_points ≥ 1000`, **and every one** of the 39 edges has a matched cell of **≥ 5** rows |
| **S2** | The floor at real counts | `T″` computed on arm N with a bootstrap 95 % CI. If the population never crosses 1 px, `T″` is recorded as *never crosses* and S3–S4 are NOT EVALUABLE |
| **S3** | Criterion 4″ | every VERIFIED edge: occupancy ≥ `T″ + 1/64` |
| **S4** | Anti-vacuity | `T″` rejects **≥ 10 %** of arm-N rows — a floor that rejects nothing at these counts is not a criterion |
| **S5** | The direct bound, per edge | for **every** edge, the 95th percentile of p99 error in its matched cell is **< 1.0 px** |
| **S6** | The property is present (null from the property, E-039) | in arm N, at **≥ 80 %** of the sizes ≤ 293, the median p99 error of `clustered` rows exceeds that of `uniform` rows — spatial concentration must hurt, or occupancy cannot be informative there |

**Adoption rule (frozen).** Criterion 4″ is adopted as the operational
statement of §53 criterion 4 **only if S0, S1, S3, S4, S5 and S6 are all
MET**. Otherwise criterion 4 stays **NOT MET**, and Part 2 names the edges and
criteria responsible. Adoption is recorded as a D-nnn beside D-057, never as
an edit to it. The written criterion ("gap ≤ 0.15") stays reported NOT MET
either way.

### 3.1 Parameter count against constraint count (E-041)

| statistic | fitted | constraints | null |
|---|---|---|---|
| affine per subset | 6 | ≥ 9 points (the smallest real count) | — |
| `T″` | 1 | ≈ 10 tiles × 22 sizes × 6 shapes × 3 draws ≈ 4 000 rows, 24 quantile bins of ≥ 4 | bootstrap over rows |
| per-edge p95 (S5) | 0 | ≥ 5 rows per matched cell (S1) | — |
| σ_N | 0 fitted, read | 39 recorded values | — |

**Can the population contain the event its criteria count? (E-058)** Yes:
arm N at 9–47 points in clustered or corner layouts will produce rows above
1 px. A population without such rows would make S2 *never crosses*, and that
outcome is frozen above.

### 3.2 Predicted outcome, with confidence

- **S0 MET** — HIGH.
- σ_N around **0.7–0.9 px** (recorded RD-07 fit RMSE is about 1–1.3 px).
- **S1 MET** — MEDIUM (70 %). The riskiest cell is the 9-inlier edge at
  occupancy 0.078.
- **S2:** `T″` (arm N) in **0.15–0.45** — MEDIUM (55 %). Arm 0 near
  EXP-015's 0.08–0.15.
- **S3 NOT MET** — MEDIUM (70 %), on the **9-inlier edge at occupancy 0.078**
  and possibly the 28-inlier edge at 0.28.
- **S4 MET** — MEDIUM (75 %).
- **S5 NOT MET** — MEDIUM (65 %), on the same one or two edges; **37–38 of 39**
  within the bound.
- **S6 MET** — MEDIUM-HIGH (80 %).
- **Overall:** criterion 4 goes from *answerable in neither direction* to
  **answered NOT MET, on one or two named edges**, with the rest demonstrably
  clear. The adoption rule fails. If every criterion passes, that is
  suspicious; Part 2 must look for why.

---

## 4. What may not happen in Part 2

- No line moves: 1.0 px, the 95th percentile, 1/64 margin, ±25 % and ±1/64
  cell widths, ≥ 5 rows, ≥ 30 rows, 10 %, 80 %.
- No tile, size or shape enters or leaves except by the rules above. σ_N is
  not re-derived from any other source.
- Arm 0 may not substitute for arm N in any criterion.
- `assess()`, `COVERAGE_GAP_WARN` and D-055 are untouched. Adoption, if it
  happens, is a D-nnn and a scorecard line, not a code change.

## 5. What this stage does NOT claim

- **Not real cross-illumination error.** The truth is synthetic; arm N adds
  noise at the recorded level but not its spatial structure.
- **Not a new verdict rule.** VERIFIED is unchanged.
- **Not a claim about other terrain.** Mare Serenitatis tiles only.

## 6. Ledger — what Part 2 will create

A `STAGE-INDEX.md` row, a `STAGE_HISTORY.md` row, `RL-059`, a D-nnn recording
criterion 4's answer (adopted 4″, or NOT MET with the responsible edges), and
an E-nnn for any defect found. Both scorecards are re-scored in the audit and
the gap analysis.

---

## Amendment A1 — written after run v1, before run v2 (2026-09-23)

**Run v1 was executed as frozen** (`experiments/EXP-022/exp022_results.json`,
`run.log`). It is kept, not rewritten, and Part 2 reports it. It could not do
what the stage exists to do: **S1 NOT MET with 0 rows at occupancy ≥ 0.99, 0
rows at ≥ 1000 points, and 27 of 39 edges without a sampled cell.** The cause
is two defects in the runner's image preparation, not in any frozen line:

1. **No-data pixels.** Five of the ten tiles carry 0.2–2 % NaN (frame edges).
   §2.1 said only "decimate, then scale to [0, 1]". The min-max scaling
   propagated NaN into the matcher, which returned **no putative matches**, so
   those tiles were skipped.
2. **Contrast.** Min-max scaling over a full tile is set by a few bright
   pixels. It left pools of **229–989** true matches, where the recorded
   REAL-DATA-07 pipeline found **thousands** on these same frames (5437 on one
   edge). The population therefore never reached real match counts.

**The amendment adopts the recorded pipeline's own preparation**,
`stretch(decimate(raw, 2))` from `scripts/run_exp007.py`: a NaN-aware block
mean, then a 1–99 % percentile stretch with no-data set to the median. This
is what produced the 39 edges' inlier counts in the first place. **Nothing
else changes:** tiles, truth, pool rule, sizes, shapes, draws, arms, σ_N,
every criterion, every line, and the adoption rule. Run v2 writes
`exp022_results_A1.json`.

**Disclosed:** v1's statistics were read before this amendment was written
(`T″` 0.328 on arm N, S3/S5 NOT MET, S6 MET). The amendment changes only how
an image is prepared, fixed by the recorded pipeline rather than chosen. Part
2 reports v1 and v2 side by side. If they disagree on a criterion, both are
stated, and the verdict is v2's **only** because v1 could not sample the
regime (S1).

---

## Part 2

**Written 2026-09-23 after both runs, against Part 1 as committed (`d727e3a`)
and Amendment A1 as committed (`d9752f2`).** Run v1: `exp022_results.json`,
`run.log` (237 s). Run v2 (A1): `exp022_results_A1.json`, `run_A1.log` (918 s,
CPU). Neither artefact is rewritten. Where a runner summary line is not the
frozen reading, this section says so and reads the artefact (E-060).

### 7. The answer, in one paragraph

**Criterion 4 now has an answer, and it is NOT MET on named edges.** At the
match counts real edges actually have (pools of **3 600–9 182** true matches;
**1 026** arm-N rows at ≥ 1 000 points; **97** at occupancy ≥ 0.99), the
calibrated floor is **T″ = 0.359** (bootstrap CI95 0.297–0.453). That is
**19 lattice steps above** the noiseless floor (arm 0: 0.0625), so EXP-015's
T = 5/64, calibrated on self-warp matches, was optimistic by a factor of about
six. Two VERIFIED edges fall below T″ + 1/64: the **9-inlier** edge at
occupancy 0.078 and the **28-inlier** edge at 0.281. Read directly
(S5), their matched cells put the 95th percentile of p99 error at **3.93 px**
and **1.66 px**. So does a third edge that the floor would *admit*: the
**68-inlier** edge at occupancy 0.4375 reaches **1.04 px**. That third edge is
the most useful line in the stage. **A single occupancy floor cannot be
criterion 4.** Near occupancy 0.44 the floor admits a layout that stays within
the bound (the 47-inlier edge, 0.81 px) and one that does not (the 68-inlier
edge, 1.04 px). Occupancy counts filled cells. It cannot see whether the
empty cells sit together on one side, and that is what extrapolation
punishes: the 68-inlier cell holds only `half` and `ring` layouts. Everywhere the population does reach, the
large edges are clear with a wide margin. All **14** edge-rows at occupancy
1.0 sit at **0.09–0.15 px**, so EXP-015's objection that they were "judged by
extrapolation" is retired for them. **Seven** distinct edges at mid-to-high
occupancy (108–5 392 inliers, occupancy 0.67–0.94) have fewer than five
comparable rows. The imported shapes do not produce those (count, occupancy)
combinations: `uniform` saturates at 0.92–1.0 above 100 points, and the others
stay below 0.66 (§9). The adoption rule therefore fails on S1, S3 and S5, and
criterion 4 stays **NOT MET**. It is no longer *answerable in neither
direction*. **3 of 13** VERIFIED triplets are demonstrated clear on all three
edges, **3** contain an edge whose layout does not bound local error at 1 px,
and **7** are not decided by this population.

### 8. Criteria, answered exactly as frozen

Verdicts are v2's (A1). v1 is beside every line. **v1 and v2 agree on every
criterion's outcome**, so A1's rule for disagreement was never invoked.

| ID | verdict (v2) | the number (v2) | v1 |
|---|---|---|---|
| **S0** | **MET** | (i) `crossing_from_above` on EXP-014's rows: **0.078125 = 0.078125**; (ii) **10 of 10** tiles used, full-pool median dense error **0.024–0.029 px** (bar 0.05); (iii) the 39 edges read from `exp012_results.json`; (iv) **σ_N = 0.7202 px** = median(fit_rmse) / √2 | MET, but on **5 of 10** tiles (5 skipped: 4 returned no matches through NaN, 1 had a pool of 229) |
| **S1** | **NOT MET** | **97** rows at occupancy ≥ 0.99 (bar 30) ✓; **1 026** at ≥ 1 000 points (bar 30) ✓; **11 of 39** edge-rows (**7 of 22** distinct edges) have a matched cell under 5 rows: two are **empty** (190 at 0.672; 293 at 0.6875), five are **thin**, with 1–3 rows (5392 at 0.9375; 2726 at 0.766; 2597 at 0.797; 265 at 0.844; 108 at 0.703) | NOT MET: **0**, **0**, **27 of 39** uncovered |
| **S2** | **MET** (crosses) | **T″ = 0.359375**, CI95 **0.296875–0.453125** (200 resamples). Arm 0 beside: **0.0625** | T″ = 0.328125, CI95 0.3125–0.4375 |
| **S3** | **NOT MET** | T″ + 1/64 = **0.375**; **37 of 39** pass. Failing: RD04 `m1271742202lc → m1335207975rc` (**9** inliers, 0.078); RD04 `m1299958135lc → m1363396554rc` (**28**, 0.281) | NOT MET, the same two edges at a margin of 0.34375 |
| **S4** | **MET, and here is why that is not reassurance** | T″ rejects **43.6 %** of arm-N rows (bar 10 %). That fraction describes the *designed* population, in which four of six shapes concentrate points on purpose. It does not describe real edges: against the 39 real edge-rows, T″ rejects **2** (5 %) | MET, 43.0 % |
| **S5** | **NOT MET** | The runner's summary line reads 34 / 39, and that is **not the frozen reading** (E-060): it counts cells of 1–3 rows as *within*. §3.1 makes S5 rest on ≥ 5 rows per cell. Read that way, S5 is **evaluable on 28 of 39** edge-rows: **25 within** (max 0.81 px) and **3 over**: the 9-inlier edge **3.93 px** (15 rows), the 28-inlier edge **1.66 px** (45), and RD03 `m1182331886lc → m1335207975rc`, the 68-inlier edge, **1.04 px** (36 rows). The other **11** are not evaluable (9 thin, 2 empty). NOT MET on either reading | NOT MET: 16 / 39 on the runner's line; the two S3 edges over (32.1 px, 1.51 px); 23 cells empty |
| **S6** | **MET, and here is why that is not reassurance** | clustered median p99 exceeds uniform at **13 of 13** sizes ≤ 293 (bar 80 %), by 4× to 34×. Affine extrapolation from a concentrated patch makes this near-certain. It confirms the property exists, so occupancy *can* inform. It does not show that occupancy alone *is* informative. The 68-inlier edge shows it is not (§7) | MET, 13 / 13 |

**Adoption rule: FAILS** (S1, S3, S5 NOT MET). Criterion 4″ is **not adopted**.
§53 criterion 4 stays **NOT MET**. The written criterion ("gap ≤ 0.15") stays
reported NOT MET, as frozen.

### 9. Why seven edges have no comparable rows

The population is EXP-014's six shapes, imported unchanged. At the counts that
matter, their occupancy ranges barely overlap the real edges' (arm N, v2):

| points | uniform | half | ring | corner | clustered | two_blobs |
|---|---|---|---|---|---|---|
| 100–300 | 0.70–0.98 (median 0.92) | 0.41–0.63 | 0.44–0.66 | 0.25–0.31 | 0.03–0.17 | 0.05–0.22 |
| ≥ 1 000 | 0.97–1.00 | 0.50–0.63 | 0.59–0.69 | 0.31 | 0.19–1.00 (median 0.47) | 0.22–0.98 (median 0.47) |

Real edges at 190 / 0.672 and 293 / 0.6875 fall between `ring`'s top and
`uniform`'s bottom. The edges at 2 597–5 392 and 0.77–0.94 fall between `ring`
and `uniform` again; only the tails of `clustered` and `two_blobs` touch them.
The real layouts are *nearly* uniform with holes, where no-data, shadow or
overlap boundaries remove a few lattice cells. None of the six shapes models
that. Filling those cells needs a seventh shape, "uniform over a random subset
of k lattice cells", which Part 1 did not freeze. It is therefore not run here
and is named as the next measurement (D-069).

**Rows not produced.** Arm N holds **3 376** of 3 960 designed rows. **216**
were skipped by the frozen pool rule (5 392 and 5 437 on the six tiles whose
pool is smaller; listed per tile in the artefact). **368** were not drawable:
the imported `draw_subset` returns no subset when the `corner` (201), `ring` (96)
or `half` (71) region holds fewer points than the size. All 368 are at sizes
≥ 1 406. EXP-014's rule, imported, did this. Part 1 did not write it down,
and it is disclosed here.

### 10. Predictions against outcomes

| prediction (Part 1 §3.2) | outcome | |
|---|---|---|
| S0 MET — HIGH | MET | right |
| σ_N 0.7–0.9 px | **0.7202** | right, at the low edge |
| S1 MET — 70 %; riskiest cell the 9-inlier edge | **NOT MET**, and not there: the 9-inlier cell has 15 rows. Seven mid-to-high-occupancy edges fail instead | **wrong, twice** |
| T″ (arm N) in 0.15–0.45 — 55 % | 0.359 | right |
| arm 0 near 0.08–0.15 | **0.0625** | wrong (one lattice step below) |
| S3 NOT MET on the 9-inlier edge, possibly the 28-inlier edge — 70 % | exactly those two | right |
| S4 MET — 75 % | MET | right, for a reason §8 qualifies |
| S5 NOT MET on the same one or two edges; 37–38 of 39 within — 65 % | NOT MET on **three** edges, one of which **passes** S3; 25 of 28 evaluable | **half right**: NOT MET, but the wrong edges and the wrong count |
| S6 MET — 80 % | MET, 13 / 13 | right |
| Overall: answered NOT MET on one or two named edges; adoption fails | NOT MET on **three** named edges, adoption fails, **and 4″ itself is shown inadequate** | right in direction, wrong in the part that matters most |

Seven right, three wrong, one half right. Part 1 said an all-MET outcome would
be suspicious. It did not predict the failure that actually carries
information: an edge above the floor and over the bound.

### 11. Defects

- **E-059** — run v1's image preparation (NaN propagation; min-max contrast
  starving the pools). It was found in v1's own artefact, handled by Amendment
  A1 and not rewritten.
- **E-060** — the runner's S5 summary counted cells of 1–3 rows as *within*,
  against §3.1's ≥ 5-row constraint. The verdict is unchanged (NOT MET on either
  reading), and the artefact is not rewritten. The proper reading is §8's.

### 12. What this changes

- **§53 criterion 4:** stays **NOT MET**. Its status changes from *NOT MET and
  MIS-SPECIFIED, unanswerable in either direction* to **answered NOT MET: three
  named low-count edges do not bound local error at 1 px under recorded noise;
  25 evaluable edge-rows do; seven distinct edges remain unsampled.** D-069.
- **EXP-015's T = 5/64 is superseded as a floor.** It was calibrated on
  noiseless matches. At the recorded noise level the floor is 0.359, not
  0.078. D-069 records this; EXP-015's text is untouched.
- **What a future criterion 4 should be:** the direct per-edge bound (S5's
  form) on a population that can reach every real (count, occupancy) cell, not
  a one-dimensional occupancy floor. This is a direction, not a re-scoping:
  nothing here is adopted.
- **`assess()`, `COVERAGE_GAP_WARN` and D-055 are untouched.**

### 13. What this stage does NOT claim (unchanged from §5, plus)

- Not that the three named edges are *wrong*. Each is in a VERIFIED triplet
  whose loop closed under 2 px, and EXP-021 labelled none of the 39 WRONG. The
  claim is only that their point layouts, *at recorded noise*, do not bound
  worst-case local error at 1 px.
- Not the edge's *own* layout. A matched cell holds synthetic subsets with the
  edge's count and occupancy (the 9-inlier cell is 11 of 15 `corner` rows), not
  the edge's recorded inlier positions. The tighter measurement fits the
  edge's own inlier layout under recorded noise. It needs those positions,
  which REAL-DATA-07 did not record.
- Not that the 25 within-bound edge-rows have sub-pixel **accuracy**. The truth
  is synthetic and the noise is iid. This is a statement about what a layout
  can support, not a measurement of any real edge's error.
