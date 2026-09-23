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

*(Empty until Part 1 is committed.)*
