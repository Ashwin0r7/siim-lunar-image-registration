# EXP-013 — Detecting the failure the verdict is built to miss

**Part 1 — pre-registration. FROZEN 2026-09-21, before any detector code
exists and before any statistic has been computed on any triplet, real or
synthetic.** Part 2 is empty until Part 1 is committed.

**Classification: DELIVERABLE-CRITICAL.** This is the only known defect in the
deliverable's safety claim, and it is already measured. EXP-012's supplementary
probe (`exp012_s3_gauge_probe.json`, E-039) returned **VERIFIED / `high` on 36
of 36** three-image sets in which *every edge was wrong* — by a median of
14.04, 57.47 and 115.40 px at gauge magnitudes 8, 32 and 64 px — with the loop
closing to **1.27e-13 px by construction**.

The project ships a verdict whose headline evidence is loop closure. Loop
closure is **exactly** invariant to this error class. That invariance is an
identity, not an implementation defect, and it is recorded in three places
already: `gtfree.loop_closure`'s docstring, ADR-0011 note N1, and a
hand-built assertion in `tests/test_demo_verdict.py`. What does **not** exist
is an instrument that detects it. This stage builds one.

---

## 1. The question

**Q.** Can a per-image gauge error — the null space of loop closure — be
detected from evidence the project already holds, at magnitudes **below** the
per-edge archive-geometry discrimination floor, without raising alarms on real
triplets that are believed gauge-free?

Either answer is a result:

- **If it can**, the deliverable gains a named instrument for its one known
  blind spot, and the honest sentence changes from *"loop closure cannot see
  this"* to *"loop closure cannot see this, and here is the check that does,
  with its measured sensitivity floor and its measured false-alarm rate."*
- **If it cannot**, the blind spot is confirmed as irreducible with the
  evidence on hand, the deliverable must say so plainly, and the correct
  mitigation moves out of software and into acquisition (an independent
  absolute reference per image).

## 2. What a per-image gauge error is, stated exactly

Each image `i` carries its own coordinate error `G_i`. Every edge is estimated
in those gauged frames:

```
E_ij = G_j ∘ T_ij ∘ G_i⁻¹
```

where `T_ij` is the true transform. Composing around a closed cycle, the
adjacent `G` terms cancel:

```
E_ca ∘ E_bc ∘ E_ab = G_a ∘ (T_ca ∘ T_bc ∘ T_ab) ∘ G_a⁻¹ = G_a ∘ I ∘ G_a⁻¹ = I
```

The loop closes **exactly**, for any `G`, however wrong each individual edge
is. No amount of loop-closure precision helps; the residual is zero by
algebra, not by luck.

**This is why the instrument must be external.** Any check computed only from
the edge estimates lives inside the same gauge and inherits the same
invariance. Breaking the gauge requires a reference that is not a function of
the estimates.

## 3. The reference this project already holds

Every REAL-DATA-07 row carries `geometry.predicted_transform_matrix` — a
transform predicted from **archive corner geometry and SPICE-derived
`SCALED_PIXEL`**, computed without the matcher ever running. It is the
reference `scripts/check_transform_against_geometry.py` uses to classify a
passing edge as CONSISTENT or INCONSISTENT.

It is a genuine external reference, and it is **coarse**: the recorded
`discrimination_floor_px` runs ≈ 84–116 px at native NAC scale. A 14 px gauge
error is far inside that floor and is invisible to the per-edge check. That
per-edge insensitivity is not a reason the reference is useless — it is the
reason this stage exists.

**The claim to be tested is that aggregation buys the sensitivity the per-edge
check lacks**, because the two error classes have different *shapes*:

| | per-edge error | per-image gauge | archive-reference noise |
|---|---|---|---|
| appears on | one edge | **every edge incident to that image** | every edge |
| correlated across a node's edges? | no | **yes, coherently** | no |
| seen by loop closure? | **yes** | no | n/a |
| seen by the per-edge geometry check? | above its floor | only above its floor | it *is* the floor |

A gauge signal adds coherently across a node's edges while the reference noise
does not. That is the entire mechanism, and it is falsifiable.

## 4. The instrument, specified as a contract (not as code)

A new module `src/siim/verify/gauge.py`, imported by nothing that `assess()`
touches.

**`decompose_gauge(edges, shape, fix_node=None) -> GaugeReport`**

- **Input.** For each edge of a closed triplet: the node names `(i, j)`, the
  estimated transform `E_ij`, the archive-predicted transform `P_ij`, and the
  edge's recorded `discrimination_floor_px`.
- **Model.** Assign each node an unknown gauge `G_n`, parameterised as a
  similarity (4 dof: translation ×2, rotation, log-scale). One node is held at
  identity to remove the global gauge freedom that no external reference can
  ever resolve, leaving `4(N−1)` free parameters against `2 × N_edges ×
  N_grid` observations.
- **Objective.** Minimise, over a fixed grid sampled in each source frame,

  ```
  Σ_edges Σ_grid ‖ E_ij(G_i(x)) − G_j(P_ij(x)) ‖²
  ```

  which is **identically zero at the true gauges** when `P_ij = T_ij`, by the
  algebra of §2.
- **Output (`GaugeReport`).** `residual_before_px` (RMS archive disagreement
  at `G = I`, i.e. what the per-edge check already sees), `residual_after_px`
  (RMS at the optimum), `explained_fraction = 1 − after/before`, the fitted
  per-node displacement magnitudes in px, `gauge_magnitude_px` (the largest of
  them), and the `alarm` boolean with the rule that produced it.
- **Refusals, not guesses.** Refuse and say which input was missing if: any
  edge lacks a predicted transform; the node set is not a closed cycle; fewer
  than 3 edges; any transform is singular. A refusal is reported as
  `CANNOT CHECK`, never as `no gauge detected`.

**`assess()` is not touched, and a test asserts it.** `verdict.py` states the
rule this stage obeys, and it is not being reinterpreted:

> **Do not add geometric plausibility as a verdict criterion.** Doing so would
> introduce a new rejection path into a rule that REAL-DATA-03, -04 and -05 all
> declare they applied unchanged […] The correct place for a new check is a new
> diagnostic reported beside the verdict, not inside it.

The gauge report is returned **beside** the verdict and can never move an edge
across the pass/fail line. If this stage succeeds completely, the correct
product change is a *reported diagnostic*, not a threshold.

## 5. Data, fixed in advance

No new byte is fetched. No tile is re-matched. Two populations, both already
recorded:

**(a) The real population — 13 triplets, 39 edges.** Exactly EXP-012's 13
admissible triplets. All 39 edges join to a B1 row in the amended REAL-DATA-07
run carrying both `transform_matrix` and `geometry.predicted_transform_matrix`
(**verified before freezing: 39 of 39 join, 0 missing**). All 13 enter; none is
dropped. These are the specificity population and are **believed gauge-free** —
that belief is itself a hypothesis and §7 H3 states what would refute it.

**(b) The synthetic gauge population.** EXP-012's gauge construction
(`scripts/run_exp012_s3_gauge.py`), reused **unmodified in its geometry**, at a
magnitude sweep declared here in full and not extended afterwards:

> **0 (control), 1, 2, 4, 8, 16, 32, 64 px**, 12 seeds each = **96 cases**.

The probe supplies the external reference as the true `T_ij` **plus additive
reference noise**, because a noiseless reference would make the problem trivial
and would not resemble the archive. The noise magnitude is **calibrated from
the real population** — the median `residual_before_px` measured on (a) — and
that calibration is computed and written into the artefact **before** any
detection statistic is read.

## 6. Success criteria — frozen

| ID | Criterion | MET if |
|---|---|---|
| **S0** | **Construction control.** The synthetic cases really are gauge cases | every case's loop closure < 1e-9 px. If any fails, **nothing is reported from the synthetic arm** |
| **S1** | **Detection.** The instrument flags gauge error at 32 and 64 px | alarm raised on **≥ 11 of 12** cases at each of 32 and 64 px |
| **S2** | **Specificity on real data.** The instrument does not cry wolf on the 13 real triplets | **0 of 13** alarms |
| **S3** | **Sensitivity below the per-edge floor.** The measured detection floor beats the per-edge archive check | the smallest swept magnitude at which ≥ 11 of 12 cases alarm is **< 84 px**, the smallest recorded `discrimination_floor_px` at native NAC scale |
| **S4** | **The null control.** The per-node model does not explain disagreement by having enough parameters | on a **permuted** control — the same real residuals with node labels shuffled within each triplet, 200 permutations — the real `explained_fraction` sits **below the 95th percentile** of the permuted distribution for ≤ 1 of 13 triplets. This is the criterion that can most easily fail, and it is the one that makes S2 mean anything |
| **S5** | **`assess()` is untouched.** | a test asserts `siim.demo.verdict` imports nothing from `siim.verify.gauge`, and the six recorded verdicts re-derive byte-identically |
| **S6** | **Zero-magnitude control.** | at gauge magnitude 0, **0 of 12** alarms |

**Failure criteria.** S1 NOT MET → the gauge class is not detectable from
archive geometry at these magnitudes; report it and say the mitigation is an
acquisition change. S2 NOT MET → the instrument is unusable regardless of S1,
and **S1 must not be quoted without S2 beside it**. S4 NOT MET → the explained
fraction is an artefact of parameter count and every number resting on it is
withdrawn.

**The alarm rule is frozen here, before any statistic is computed:**

> **alarm** ⟺ `gauge_magnitude_px > 2.0` **and** `explained_fraction > 0.5`.

Both halves are required: a large fitted gauge that explains little of the
disagreement is reference noise absorbed by free parameters, and a high
explained fraction at a negligible magnitude is not an error worth reporting.
**These two constants are declared now and may not be tuned in Part 2.** If
they turn out to be wrong, that is reported as wrong, with the measured
alternative named and *not* substituted.

## 7. Hypotheses

| | Statement | Confidence | Refuted by |
|---|---|---|---|
| **H1** | A per-image gauge is detectable from archive geometry by per-node aggregation, at magnitudes an order of magnitude below the per-edge floor | MEDIUM | S1 or S3 NOT MET |
| **H2** | The 13 real triplets carry no detectable gauge | MEDIUM-LOW | S2 NOT MET |
| **H3** | If H2 is refuted, the most likely cause is **not** a real gauge error but the archive reference itself being systematically wrong per frame — which is the same signal shape | — | stated now so that an S2 failure is not read as "the real data is corrupt"; a per-frame archive bias is indistinguishable from a per-frame gauge **by this instrument**, and that indistinguishability is a limitation to report, not to resolve by choosing the flattering reading |

**H3 is the honest half of this pre-registration.** The instrument cannot tell
a per-image estimation error from a per-image reference error. It localises
the disagreement to an image; it does not attribute blame. Part 2 must say
this whatever the outcome.

## 8. What this stage explicitly does NOT claim

- **Not a false-acceptance rate.** §53 criterion 3's first two clauses stay
  unmeasurable; this stage adds an instrument, not ground truth.
- **Not a fix to loop closure.** The invariance is an identity. Nothing here
  makes loop closure see the null space; it adds a second, independent check
  that looks *only* at the null space.
- **Not validated on a real gauge error.** No real triplet is known to carry
  one. Detection is measured on synthetic constructions; specificity is
  measured on real data. That asymmetry is the stage's main limitation and is
  stated in Part 2's headline, not in a footnote.
- **Not a Chandrayaan-2 result.**

## 9. Pre-registered relationship to E-039's lesson

E-039's lesson was: *name the property a test needs, not a source you assume
has it.* This Part 1 is written to obey it. The adversarial population here is
defined by the **property** — *a construction in the loop-closure null space*,
stated as algebra in §2 — and the construction is checked against that property
by S0 before any detection statistic is read. If S0 fails, the synthetic arm
reports nothing at all.

---

## Part 2

*Empty. Written only after this Part 1 is committed.*
