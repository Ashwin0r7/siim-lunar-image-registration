# EXP-012 — Verdict calibration: is VERIFIED reachable on real lunar data?

**Part 1 — pre-registration. FROZEN 2026-09-20, before any loop residual on a
real triplet has been computed.** The triplet *inventory* below was computed
first (it is a property of already-recorded rows, not of this experiment's
outcome) and is stated in full so that no triplet can be selected after seeing
its residual. Part 2 is empty until Part 1 is committed.

**Classification: DELIVERABLE-CRITICAL.** `MASTER_RESEARCH_AND_ARCHITECTURE_PLAN.md`
§53 requires a verdict false-acceptance rate, a false-rejection rate, and zero
VERIFIED on the adversarial set. `docs/FINAL_SUCCESS_CRITERIA_AUDIT.md`
(2026-09-20) found all three **NOT EVALUABLE**, for one structural reason:

> There is no VERIFIED verdict anywhere in the repository. All six recorded
> `assess()` verdicts are REJECTED. A false-acceptance rate over zero
> acceptances is undefined.

`assess()` returns VERIFIED only when loop closure is present and under
`LOOP_ERROR_REJECT_PX = 2.0`. The 42-pair REAL-DATA-07 census and the
REAL-DATA-08 proxy grid never form triplets, so no row in either can exceed
INCONCLUSIVE. This stage asks whether that ceiling is a property of the data or
only of how the census was run.

## 1. The question

**Q.** Do three real NAC frames that each register pairwise compose to a loop
that closes, and does the deliverable's own verdict engine then return VERIFIED
on real lunar data — under the criteria exactly as they are frozen today?

This is not a request for a better number. Either answer is a result:

- **If a real loop closes**, the project's strictest verdict is reachable
  without relaxing anything, and criteria 3 and 4 become measurable.
- **If no real loop closes**, then VERIFIED is unreachable on real data under
  the current criteria, and the deliverable must say so — that a verdict level
  it ships can never be earned is a finding about the architecture, and a more
  important one than a passing rate.

## 2. Data, fixed in advance — the complete triplet inventory

Recorded rows only. No tile is re-matched, no engine is re-run, no new byte is
fetched. A triplet is **admissible** if all three of its edges are recorded
B1 successes (`success == true`, i.e. passed `n_inliers > 8` and not a wrong
pass) in the amended REAL-DATA-07 run (`rows_rd03_nue.json`,
`rows_rd04_nue.json`).

**13 admissible triplets exist. All 13 enter this stage; none is dropped.**
Enumerated here before any residual is computed, by frame suffix:

**RD03 window (4):**

| # | edges (inliers, Δinc, geometry) |
|---|---|
| R3-1 | 1182331886lc↔1199981485rc (190, 23.14°, CONSISTENT) · 1199981485rc↔1212932972lc (293, 21.40°, CONSISTENT) · 1182331886lc↔1212932972lc (5437, 1.74°, CONSISTENT) |
| R3-2 | 1182331886lc↔1212932972lc (5437, 1.74°, C) · 1212932972lc↔1271742202lc (1406, 15.53°, C) · 1182331886lc↔1271742202lc (1656, 13.79°, C) |
| R3-3 | 1182331886lc↔1212932972lc (5437, 1.74°, C) · 1212932972lc↔1335207975rc (144, 24.28°, C) · 1182331886lc↔1335207975rc (68, 26.02°, C) |
| R3-4 | 1212932972lc↔1335207975rc (144, 24.28°, C) · 1335207975rc↔1452560468lc (5392, 0.96°, **INCONCLUSIVE**) · 1212932972lc↔1452560468lc (143, 23.32°, C) |

**RD04 window (9):**

| # | edges (inliers, Δinc, geometry) |
|---|---|
| R4-1 | 1212932972lc↔1271742202lc (1679, 15.53°, C) · 1271742202lc↔1299958135lc (1608, 11.73°, C) · 1212932972lc↔1299958135lc (272, 27.26°, **INCONCLUSIVE**) |
| R4-2 | 1212932972lc↔1271742202lc (1679, C) · 1271742202lc↔1315225542lc (2138, 8.82°, C) · 1212932972lc↔1315225542lc (284, 24.35°, C) |
| R4-3 | 1212932972lc↔1271742202lc (1679, C) · 1271742202lc↔1335207975rc (9, 39.81°, C) · 1212932972lc↔1335207975rc (210, 24.28°, C) |
| R4-4 | 1212932972lc↔1299958135lc (272, **INCONCLUSIVE**) · 1299958135lc↔1315225542lc (2726, 2.91°, C) · 1212932972lc↔1315225542lc (284, C) |
| R4-5 | 1212932972lc↔1299958135lc (272, **INCONCLUSIVE**) · 1299958135lc↔1363396554rc (28, 34.18°, C) · 1212932972lc↔1363396554rc (2597, 6.92°, C) |
| **R4-6** | **1271742202lc↔1299958135lc (1608, 11.73°, C) · 1299958135lc↔1315225542lc (2726, 2.91°, C) · 1271742202lc↔1315225542lc (2138, 8.82°, C)** |
| R4-7 | 1271742202lc↔1299958135lc (1608, C) · 1299958135lc↔1341069775rc (265, 24.21°, C) · 1271742202lc↔1341069775rc (47, 12.48°, C) |
| R4-8 | 1271742202lc↔1315225542lc (2138, C) · 1315225542lc↔1341069775rc (108, 21.30°, C) · 1271742202lc↔1341069775rc (47, C) |
| R4-9 | 1299958135lc↔1315225542lc (2726, C) · 1315225542lc↔1341069775rc (108, C) · 1299958135lc↔1341069775rc (265, C) |

**R4-6 is named in advance as the primary triplet**: it is the only one whose
three edges are all ≥ 1600 inliers and all geometry-CONSISTENT, and it is
composed of frames A (`m1271742202lc`), D (`m1299958135lc`) and E2
(`m1315225542lc`) — the frames that carry D-040 and its replication (D-040-N2).
Every other triplet is reported beside it, including the four containing an
INCONCLUSIVE edge, which are **not** excluded: their geometry verdict is an
input to `assess()`, not a filter on this stage.

## 3. Method, fixed in advance

1. **Edge independence, asserted in code before anything is composed.** Each
   of the three transforms must come from a *separately estimated* recorded
   row. E-021 was exactly an algebraically derived closing edge manufacturing a
   zero residual; the runner refuses to proceed if any edge of a triplet is
   derived from the other two rather than read from its own row.
2. **Direction gate.** Recorded transforms are stored per ordered pair. The
   runner determines each edge's direction from the row's own `pair` field and
   **verifies** it: composing an edge with the inverse of its stored form must
   return the identity to < 1e-9 px. A triplet whose direction cannot be
   resolved this way is reported `direction_unresolved`, not guessed.
3. **Frame.** The amended run's `transform_matrix` is in the north-up
   (`north_up_east_right`, E-037) frame of the two tiles it relates. Loops are
   composed in that frame throughout; `transform_matrix_original_pixels` is not
   mixed in. The frame used is recorded per row.
4. **Residual.** `siim.evaluation.gtfree.loop_closure(transforms, shape,
   step=16)`, unchanged, on the recorded decimated tile shape.
5. **Verdict.** `siim.demo.verdict.assess()`, unchanged, with the loop residual
   supplied, producing a real `Verdict` per triplet. **No threshold in
   `verdict.py` is touched by this stage.**
6. **Adversarial arm.** The EXP-002 objective-4 adversarial constructions are
   run through `assess()` so the third clause of §53 criterion 3 acquires a
   recorded verdict rather than remaining unevaluable.
7. **Provenance.** Every row records the three source row files, the three
   edges, inlier counts, geometry verdicts, the residual, and the full verdict.

## 4. Hypotheses and criteria — FROZEN

**H1 (VERIFIED is reachable on real data).** At least one admissible triplet
returns `status == "VERIFIED"` from the unmodified `assess()`.
> **S1 MET** if ≥ 1 of the 13 triplets is VERIFIED.
> **Prediction: MET for R4-6, UNKNOWN for the rest. Confidence LOW-MEDIUM.**
> The reasoning, recorded so it can be wrong: the three edges are strong and
> geometry-consistent, but REAL-DATA-03's only real loop returned **1201.04 px**
> with two broken legs, and no real loop with three *good* legs has ever been
> computed in this project. There is no prior measurement to extrapolate from.

**H2 (the residual tracks edge quality).** Triplets whose weakest edge has more
inliers close tighter.
> **S2 MET** if Spearman ρ between (minimum edge inliers) and (loop residual)
> is negative with p < 0.05 over the 13 triplets. Prediction: MET, confidence
> LOW — n = 13 and the edges are not independent across triplets (they share
> frames), which is stated as a limitation, not corrected.

**H3 (the verdict rejects the adversarial set).** No adversarial construction
from EXP-002 objective 4 returns VERIFIED.
> **S3 MET** if zero adversarial cases are VERIFIED.
> **Prediction: NOT MET.** `verdict.py` already documents that a 64-px-wrong
> transform whose error cancels in the loop returns **VERIFIED / high** — the
> per-image gauge null space (ADR-0011 N1), pinned in
> `tests/test_demo_verdict.py`. This stage predicts its own criterion will
> fail, and will report the gauge-error case as the reason. Confidence HIGH.

**S4 (control, must hold).** Re-composing REAL-DATA-03's recorded triplet must
reproduce its recorded **1201.04 px**. If it does not, the composition code is
wrong and the stage stops before reporting any new residual.

## 5. What each outcome licenses

| Result | Claim |
|---|---|
| S1 MET | VERIFIED is reachable on real lunar data under unmodified criteria; §53 criteria 3 and 4 become measurable and are reported in Part 2 |
| S1 NOT MET | **VERIFIED is unreachable on real data as the criteria stand.** The deliverable states this plainly and either justifies shipping an unreachable level or records the change as a decision with its evidence — it is not quietly retuned |
| S2 MET | Loop residual is a usable edge-quality signal at this scale |
| S3 NOT MET (predicted) | The gauge null space is a **measured** limitation of the shipped verdict, quantified on real data rather than only asserted in a docstring |
| S4 fails | Stage stops; nothing is reported |

## 6. Threats to validity, registered in advance

- **The null space is the headline threat.** `loop_closure` is *exactly*
  invariant to any error belonging to an image rather than an edge. A closing
  loop therefore verifies the transform set **only up to per-image gauge** —
  per-frame interior orientation, line-scan jitter, attitude drift, a per-image
  resampling convention. A VERIFIED result from this stage is **not** a claim of
  absolute accuracy and Part 2 will not phrase it as one.
- **No ground truth.** Nothing here measures error against truth; the residual
  is a self-consistency bound, and the geometry verdict is a separate bound at
  its own discrimination floor.
- **Shared edges.** The 13 triplets share frames and edges, so they are not 13
  independent samples. Reported, not corrected.
- **One region, one instrument.** Mare Serenitatis, LRO NAC only. Nothing here
  is a Chandrayaan-2 result.
- **n = 13** on triplets and one region: no significance claim beyond S2's
  stated test.

## 7. What this stage does NOT do

No re-matching, no new acquisition, no engine change, no threshold change, no
tuning of `assess()`, no accuracy claim, no Chandrayaan-2 claim. It composes
transforms that are already recorded and runs the verdict that already ships.

## 8. AMENDMENT A1 — 2026-09-20, before any residual was computed

**Status when this was written: no loop residual, on any triplet, had been
computed.** The triplet inventory in §2 was already fixed and is unchanged.
This amendment therefore cannot be outcome-driven, and is recorded rather than
applied silently — the failure mode E-035 and the RD-08 operator deviation both
came from a Part 1 whose method could not do what it said.

**The obstacle.** §3.5 requires `assess()` unchanged. `assess()` derives its
coverage evidence from the **inlier point coordinates**
(`src_points[inlier_mask]` → `coverage_metrics`, `verdict.py:269-271`). The
amended REAL-DATA-07 rows record the resulting coverage *statistics*
(`coverage_max_uncovered_disc_ratio`, `coverage_occupancy`) but **not the
correspondences themselves**. The verdict therefore cannot be produced from the
recorded rows alone, and §7's "no re-matching" makes §3.5 unimplementable.

**The two honest options, and the one taken.** Fabricating a point set that
reproduces the recorded coverage statistics would be inventing data and is
refused outright. The stage instead **re-runs engine B1 on the edges of the 13
admissible triplets** to recover the correspondences it needs. Nothing else
changes: the same engine, `BASE = {model: affine, ransac_threshold_px: 3.0,
seed: 0}`, the same tiles at the same recorded windows and decimation, the same
`north_up_east_right` orientation.

**This strengthens rather than weakens the stage, and adds a control:**

> **S5 (re-match control, must hold).** Every re-matched edge must reproduce
> its recorded `n_inliers` **exactly**. A single mismatch means the environment
> or the code has drifted from what produced the amended REAL-DATA-07 run, and
> **the stage stops** — no residual and no verdict is reported. This is the
> same species of control as S4 and as REAL-DATA-09's S6.

§7 is amended to read: *no new acquisition, no engine change, no threshold
change, no tuning of `assess()`, no accuracy claim, no Chandrayaan-2 claim.*
Re-matching of already-recorded edges, gated by S5, is permitted and is the
only method change. §2's inventory, §4's hypotheses, and every criterion
S1–S4 are untouched.

---

## Part 2 — Results

**Run 2026-09-20.** Artefact: `experiments/EXP-012/exp012_results.json`.
Runner: `scripts/run_exp012.py`. Engine B1, `model=affine`,
`ransac_threshold_px=3.0`, `seed=0`, `north_up_east_right` — every setting
identical to the amended REAL-DATA-07 run. 13 triplets, 22 unique edges,
39 edge verdicts, 112 s.

### Headline

**VERIFIED is reachable on real lunar data, and no threshold was touched to
get there.** All 13 admissible triplets close, with loop residuals of
**0.3654 – 1.3358 px** against the frozen 2.0 px reject line, and the
unmodified `assess()` returns **VERIFIED on all 39 edge verdicts** (25 `high`,
14 `moderate`). These are the first VERIFIED verdicts in the repository.

The prediction in Part 1 §4 was *"MET for R4-6, UNKNOWN for the rest,
confidence LOW-MEDIUM"*, reasoning that the only prior real loop had returned
1201 px. The outcome exceeded it: **13 of 13**, not one.

### Controls, both MET, both run before anything was reported

| Control | Requirement | Result |
|---|---|---|
| **S4** | Re-composing REAL-DATA-03's recorded triplet returns 1201.0378963072235 px | **MET — difference 0.0 px exactly** |
| **S5** | Every re-matched edge reproduces its recorded `n_inliers` exactly | **MET — 22 / 22 edges exact** |

S5 reproduced counts spanning **9 to 5437 inliers** bit-for-bit, which is a
stronger reproducibility statement than this project has previously made: the
amended REAL-DATA-07 run is re-derivable from the tiles on disk, edge by edge.

**S5 earned its place on the first attempt by failing.** The initial run
stopped at the third edge — 1715 inliers against a recorded 1656 — while two
earlier edges reproduced exactly. The cause was not drift: a row carries both
`pair` (sorted) and `edge` (the direction the engine was actually fed), the
runner read direction from `pair`, and matching is not symmetric. Two edges
happened to have alphabetical order equal to execution order and so passed.
**This is E-036's defect** — a reproduction arm run in the wrong direction —
**caught the same way, by a gate that demanded the recorded number back.** No
residual and no verdict was computed until it was fixed.

### S1 — VERIFIED is reachable: **MET**

| # | frames (suffix) | min edge inliers | loop residual px | verdicts |
|---|---|---|---|---|
| R3-1 | 331886 + 981485 + 932972 | 190 | 1.1508 | VERIFIED ×3 |
| R3-2 | 331886 + 932972 + 742202 | 1406 | 0.6776 | VERIFIED ×3 |
| R3-3 | 331886 + 932972 + 207975 | 68 | 0.4938 | VERIFIED ×3 |
| R3-4 | 932972 + 207975 + 560468 | 143 | 0.8638 | VERIFIED ×3 |
| R4-1 | 932972 + 742202 + 958135 | 272 | 0.7383 | VERIFIED ×3 |
| R4-2 | 932972 + 742202 + 225542 | 284 | 1.3358 | VERIFIED ×3 |
| R4-3 | 932972 + 742202 + 207975 | **9** | 1.1545 | VERIFIED ×3 |
| R4-4 | 932972 + 958135 + 225542 | 272 | 0.6326 | VERIFIED ×3 |
| R4-5 | 932972 + 958135 + 396554 | 28 | 1.1145 | VERIFIED ×3 |
| **R4-6** | **742202 + 958135 + 225542** | **1608** | **0.8014** | **VERIFIED ×3** |
| R4-7 | 742202 + 958135 + 069775 | 47 | 0.3654 | VERIFIED ×3 |
| R4-8 | 742202 + 225542 + 069775 | 47 | 0.7082 | VERIFIED ×3 |
| R4-9 | 958135 + 225542 + 069775 | 108 | 0.5314 | VERIFIED ×3 |

R4-6 — frames A, D and E2, the frames carrying D-040 and its replication —
closes at **0.8014 px** with every edge ≥ 1608 inliers. It is the cleanest
instance and the one the deliverable should show.

The four triplets containing a geometry-INCONCLUSIVE edge (R3-4, R4-1, R4-4,
R4-5) were **not** excluded, as Part 1 §2 fixed, and all four close.

### S2 — the residual tracks edge quality: **NOT MET**

Spearman ρ between minimum edge inliers and loop residual is **0.0551**
(n = 13) — not merely weak but the wrong sign, and indistinguishable from zero.
Part 1 predicted MET at LOW confidence; the prediction is **refuted**.

The clearest counterexample is **R4-3**, whose weakest edge carries **9
inliers** at Δincidence 39.81° — one above the failure rule's cutoff of 8 — and
whose loop nonetheless closes at **1.1545 px**, tighter than four triplets
built from far stronger edges.

**This is the stage's most consequential finding, and it is a warning, not a
success.** Loop closure does not discriminate on edge strength at this scale,
so a marginal edge rides into VERIFIED on a loop that closes around it. That is
consistent with the null space registered in Part 1 §6: loop closure constrains
the *quotient*, not the individual transforms. A reader must not take VERIFIED
as a statement that each edge is independently strong.

### Criterion 4 of §53 becomes measurable, and is **NOT MET**

`FINAL_SUCCESS_CRITERIA_AUDIT.md` recorded criterion 4 — *coverage gap ≤ 0.15
on every VERIFIED pair* — as vacuously true over an empty set. VERIFIED pairs
now exist, so the criterion can be evaluated, and it fails:

- coverage gap over the 39 VERIFIED edges: **min 0.038, median 0.097, max 0.406**
- **25 of 39 are ≤ 0.15; 14 are not.**

The 14 are exactly the verdicts `assess()` returned at `moderate` rather than
`high` confidence — the coverage evidence counted against them as designed, and
the verdict still reached VERIFIED because loop closure agreed. **Criterion 4
as phrased in §53 is therefore NOT MET, and no threshold is being adjusted to
change that.** Either §53's criterion or the verdict's coverage handling must
be revisited as a recorded decision; this stage reports the conflict rather
than resolving it silently.

### S3 — adversarial set: **NOT RUN**

Part 1 §3.6 specified running the EXP-002 objective-4 adversarial
constructions through `assess()`, with S3 predicted NOT MET because a
64-px-wrong transform whose error cancels in the loop already returns
VERIFIED / high (ADR-0011 N1). **That arm was not implemented in this run.**
It is reported as not run rather than as an outcome, and §53 criterion 3's
third clause remains unevaluated.

### Summary against the frozen criteria

| Criterion | Result |
|---|---|
| **S1** VERIFIED reachable on real data | **MET** — 13 / 13 triplets, 39 / 39 edge verdicts VERIFIED |
| **S2** residual tracks edge quality | **NOT MET** — ρ = 0.0551, prediction refuted |
| **S3** zero VERIFIED on adversarial set | **NOT RUN** |
| **S4** RD-03 composition control | **MET** — 0.0 px |
| **S5** re-match control | **MET** — 22 / 22 edges exact |

### What this licenses, and what it does not

**Licensed.** The deliverable may state that its strictest verdict is
attainable on real lunar imagery under unmodified criteria, on 13 independent
triplets over two ground windows, with the residual range quoted. §53
criterion 4 is now measurable and is reported NOT MET.

**Not licensed.** This is **not** an accuracy claim. Loop closure is exactly
invariant to per-image gauge error, so a closing loop verifies the transform
set only up to that gauge — per-frame interior orientation, line-scan jitter,
attitude drift. There is no ground truth here. The 13 triplets share frames and
edges and are not independent samples. One region, one instrument; nothing here
is a Chandrayaan-2 result. And per S2, VERIFIED does not imply every
contributing edge is strong.
