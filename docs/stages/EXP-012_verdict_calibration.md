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

---

## Part 2 — Results

*Empty until Part 1 is committed.*
