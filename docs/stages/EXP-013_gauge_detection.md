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

# Part 2 — what happened

**Run 2026-09-21, `scripts/run_exp013.py`, 427.7 s, CPU only, no new data.**
Artefact: `experiments/EXP-013/exp013_results.json`.

## 0. The result in one paragraph

**Four of the six frozen criteria are NOT MET, and the stage is a negative
result with a measured cause.** The instrument's mechanism is sound — on a
graph where the per-node model is over-determined it separates a real
disagreement from a structureless one decisively, and three independent
matchers recover the same per-frame term to within 1.5 px. But **the unit of
analysis Part 1 froze cannot support the statistic**: a three-edge cycle gives
eight free parameters against three edges, and a disagreement with *no*
per-node structure at all already scores an explained fraction of **0.834 at
its 95th percentile** there, against real values with a median of 0.837. On top
of that, the external reference this project holds is **coarse relative to the
signal**: its own per-frame disagreement is **66.0 px**, larger than every
gauge magnitude in the sweep except the last.

So the answer to §1's question is the second branch, and §1 already wrote down
what that obliges: *the blind spot is confirmed as irreducible with the
evidence on hand, the deliverable must say so plainly, and the correct
mitigation moves out of software and into acquisition.*

| | criterion | verdict |
|---|---|---|
| **S0** | construction control — the synthetic cases really are gauge cases | **MET** — max loop residual **1.27e-13 px** against a 1e-9 px tolerance |
| **S1** | detection: ≥ 11 of 12 alarms at each of 32 and 64 px | **NOT MET** — **10** of 12 at 32 px, 11 of 12 at 64 px |
| **S2** | specificity: 0 of 13 alarms on the real triplets | **NOT MET** — **13 of 13** alarmed |
| **S3** | detection floor < 84 px | **MET at 64 px — and the pass is vacuous, see §4** |
| **S4** | the permutation control | **NOT MET** — 9 of 13, against a bar of ≤ 1 |
| **S6** | 0 of 12 alarms at gauge magnitude 0 | **NOT MET** — **6** of 12 alarmed, median fitted gauge **55.55 px** where the true gauge is ~0 |

Nothing was retuned. The two alarm constants are the ones Part 1 §6 froze
(`gauge_magnitude_px > 2.0` **and** `explained_fraction > 0.5`), and
`tests/test_gauge_detection.py` pins them so a later edit is visible.

*(S5 — "`assess()` is untouched" — is a property of the code rather than of the
run, and is enforced continuously by `tests/test_gauge_detection.py`, which
parses `verdict.py`'s imports. It is MET and is not carried in the artefact's
criteria block.)*

## 1. S0 — the construction is what it claims to be — **MET**

All 96 cases close to **1.27e-13 px**, eleven orders of magnitude inside the
1e-9 px tolerance. This was checked **before any detection statistic was read**,
and the runner is written to report nothing from the synthetic arm if it fails.

This is the one place E-039's lesson was applied successfully: the adversarial
population is defined by the *property* it must have — a construction in the
loop-closure null space, stated as algebra in Part 1 §2 — and the property is
verified rather than assumed.

## 2. S6 — the zero-gauge control — **NOT MET**, and it explains S1 and S2

At gauge magnitude **0**, the instrument fits a gauge of **55.55 px** (median)
and raises **6 alarms in 12**.

There is no gauge to find at magnitude 0. What the fit is recovering is the
**reference noise**, which Part 1 §5(b) required be calibrated from the real
population before any detection statistic was read. That calibration came out
at **66.00 px** — the median archive disagreement over the 13 real triplets.

So the sweep gave the instrument a reference whose own error is **larger than
the signal at every magnitude below 64 px**, and a model with enough freedom to
absorb it. The consequence runs straight down the table:

| gauge applied | alarms | median true edge error | median fitted gauge | median explained |
|---|---|---|---|---|
| 0 px | **6 / 12** | 1.51 px | 55.55 px | 0.484 |
| 1 px | 6 / 12 | 1.98 px | 55.04 px | 0.492 |
| 2 px | 6 / 12 | 3.46 px | 54.56 px | 0.499 |
| 4 px | 6 / 12 | 6.71 px | 54.56 px | 0.516 |
| 8 px | 8 / 12 | 14.04 px | 58.80 px | 0.545 |
| 16 px | 8 / 12 | 28.51 px | 66.48 px | 0.588 |
| 32 px | **10 / 12** | 57.47 px | 83.10 px | 0.674 |
| 64 px | **11 / 12** | 115.40 px | 139.76 px | 0.780 |

The alarm rate at 0 px and at 4 px is **identical**. The fitted gauge barely
moves until the applied gauge approaches the reference noise. Read as a
detector, the first four rows are pure false-alarm rate and the last two are
signal beginning to emerge from it.

**S6 is the criterion that mattered most, and it is the one that failed
first.** A detector that fires half the time on nothing has no operating point,
and every other number in the synthetic arm has to be read through it.

## 3. S1 — detection — **NOT MET**

10 of 12 at 32 px and 11 of 12 at 64 px, against a bar of ≥ 11 at both.

It misses by one case at one magnitude, and **it should not be reported as a
near miss.** With S6 failing at 6 of 12, the alarms at 32 px are not
attributable to detection: a detector with a ~50 % false-alarm rate reaching
10 of 12 is a weak result, not a strong one. The right summary is that
detection and false alarm are not separated anywhere in this sweep.

## 4. S3 — the sensitivity floor — **MET, and the pass carries no information**

The smallest magnitude reaching the ≥ 11 of 12 bar is **64 px**, which is below
the 84 px per-edge discrimination floor Part 1 named, so the criterion as
written is **MET**.

**It is reported as MET and simultaneously as worthless**, because the same
arm's zero-gauge control fires 6 times in 12. A "detection floor" measured
against a detector that has no null is a number without a referent. This is S3
passing without meaning for the second time in two stages: EXP-012's S3 was MET
for the wrong reason (E-039), and this S3 is MET against a broken null. **The
criterion is answered as frozen and the reading is given beside it**, which is
the only honest option once a criterion has been committed.

## 5. S2 — specificity on real data — **NOT MET**

**All 13 real triplets alarmed.** Their archive disagreement runs
**40.6 – 117.3 px** (median 66.0), the per-node model explains **0.649 – 0.920**
of it (median 0.837), and the fitted gauges run **45.6 – 101.8 px** — against
recorded per-edge discrimination floors of **83.5 – 116.3 px**, and loop
closures of **0.3654 – 1.3358 px**.

Two readings were available, and Part 1 §7 H3 wrote down the unflattering one
in advance. §6 and §7 below decide what can be decided with controls, rather
than by choosing.

## 6. S4 — the permutation control — **NOT MET**, and it was the wrong instrument

9 of 13 real explained fractions sit below the 95th percentile of their
200-permutation null, against a bar of ≤ 1.

**S4 as frozen cannot test what it was written to test.** Permuting node labels
on a three-node cycle maps the cycle to a cycle carrying the same three
(estimate, prediction) pairs; it changes the names and — because the residual
is *not* invariant to composing every gauge with a common transform — which
node is held at identity, so it produces some spread. But it never removes the
per-node *structure* the criterion is meant to be testing for. It is a test of
labelling, not of structure.

The property the control actually needs is **a disagreement of the same
magnitude with no per-node structure at all**, and Part 1 named a *procedure*
instead. **This is E-039's lesson recurring inside the stage that exists
because of E-039** — and, before that, E-035's. Same defect, ascending levels:
E-035 at the level of an arm, E-039 at the level of a criterion, E-040 at the
level of an artefact's coordinate frames, and this at the level of a *control*.

### The control S4 should have been — supplementary, not folded into S4

`supplementary_structureless_null` builds the missing case: each edge's
prediction is replaced by a perturbation of its own estimate at the same
magnitude, giving a disagreement that is per-*edge* by construction. Fitted
with the identical model, at the identical grid step, on the identical graphs:

| redundancy | n | null median | null p95 | null max | real values |
|---|---|---|---|---|---|
| **1** (the 13 triplets) | 208 | 0.445 | **0.834** | 0.989 | 0.649 – 0.921, median **0.837** |

**The real triplets are inside their own null.** Six of the thirteen fall below
the null's 95th percentile, and the median real value (0.837) is
indistinguishable from the null's 95th percentile (0.834). On a three-edge
cycle the explained fraction is **not a discriminating statistic**, and S2's
13 of 13 therefore says nothing about whether those triplets carry a gauge.

**This is the stage's central finding, and it is a finding about the
pre-registration rather than about the Moon.** Part 1 fixed a population — 13
triplets — without checking that the population could support the statistic the
criteria would be computed from. `redundancy = n_edges − (n_nodes − 1)` is
**1** for every one of the 13: eight free parameters against three edges. The
number was not in Part 1 at all; `GaugeReport.redundancy` was added during
implementation, which is how the defect surfaced — late, and by luck.

## 7. The instrument itself works — supplementary, on a graph that can carry it

`supplementary_census_graph` runs the same fit on the REAL-DATA-07 census
graph, reduced to its 2-core (a node of degree 1 can always absorb its own
edge, so it inflates the explained fraction for free), with a structureless
null at the same topology:

| window | engine | edges / nodes | redundancy | archive disagreement | explained | null median | null p95 | **null max** |
|---|---|---|---|---|---|---|---|---|
| RD03 | B1 | 9 / 6 | 4 | 80.3 px | **0.846** | 0.351 | 0.565 | 0.590 |
| RD03 | B4L | 9 / 6 | 4 | 80.3 px | **0.845** | 0.351 | 0.564 | 0.590 |
| RD03 | B4X | 11 / 6 | 6 | 81.2 px | **0.857** | 0.314 | 0.471 | 0.529 |
| RD04 | B1 | 13 / 7 | 7 | 75.5 px | **0.851** | 0.250 | 0.475 | 0.515 |
| RD04 | B4L | 11 / 6 | 6 | 72.6 px | **0.845** | 0.291 | 0.448 | 0.549 |
| RD04 | B4X | 12 / 6 | 7 | 74.3 px | **0.848** | 0.258 | 0.370 | 0.421 |

**In all six graphs the real explained fraction exceeds the *maximum* of forty
structureless draws**, by a margin of 0.26 to 0.43. Where the model is
over-determined, the instrument separates a per-image effect from per-edge
noise without ambiguity. The mechanism Part 1 §3 proposed is real; the triplet
is simply the wrong place to apply it.

The archive disagreement on these graphs is **72.6 – 81.2 px** and the fitted
per-frame gauges are **92.1 – 109.4 px** — the same scale as the recorded
per-edge discrimination floors (83.5 – 116.3 px), which were derived
independently, from corner-coordinate quantisation.

## 8. Which side carries it — the cross-engine control

If the per-frame term lived in the *matching*, three unrelated matchers would
not agree on it. `supplementary_cross_engine` compares the per-frame gauges
recovered from RootSIFT (B1), DISK + LightGlue (B4L) and XFeat (B4X)
independently:

| window | pair | frames | median difference | max difference |
|---|---|---|---|---|
| RD03 | B1 vs B4L | 6 | 0.18 px | 0.52 px |
| RD03 | B1 vs B4X | 6 | 0.10 px | 1.06 px |
| RD03 | B4L vs B4X | 6 | 0.34 px | 0.88 px |
| RD04 | B1 vs B4L | 6 | 0.04 px | 0.27 px |
| RD04 | B1 vs B4X | 6 | 1.07 px | 1.50 px |
| RD04 | B4L vs B4X | 6 | 0.90 px | 1.50 px |

**Three independent matchers recover the same per-frame term to within 1.50 px
on terms of 92 – 109 px** — agreement to better than one part in sixty. A
per-frame error that RootSIFT, DISK + LightGlue and XFeat all reproduce to that
precision is **not a property of any of them.**

### What that does and does not settle

It rules out the matcher. It does **not** decide between the two remaining
readings, and Part 1 §7 H3 said in advance that it could not:

1. **The archive reference carries a per-frame error of ~66 – 109 px.** This is
   consistent with everything else the project has measured: the recorded
   `discrimination_floor_px`, derived from corner-coordinate quantisation by a
   completely different route, is **83.5 – 116.3 px** on exactly these edges. On
   this reading the instrument is working correctly and is measuring the
   reference's own error.
2. **The tiles carry a shared per-frame georeferencing error**, introduced
   before matching and therefore identical for every engine. On this reading
   the instrument has found **a real instance of exactly the defect it was
   built to detect** — a per-image gauge, invisible to loop closure, sitting in
   the project's own real data.

**These two are indistinguishable by this instrument**, because both are
per-image and the instrument only localises to an image. Reading (1) is the
more likely — a quantisation-derived floor and a fitted magnitude agreeing to
within their own spread would otherwise be a strong coincidence — but the
honest statement is that it has not been separated, and reading (2) is not
dismissed for being the uncomfortable one.

**What would separate them:** an independent absolute reference per frame, at a
resolution finer than the disagreement. The project already knows one exists
and has not used it — `README.md` records that LROC NAC regional controlled
mosaics carry a published average positional offset **below 13 m**, roughly
**7 – 26 px** at NAC resolution, against the ~100 px figures discussed here.
That is precisely the acquisition change §1's second branch pointed at, and it
is unblocked.

## 9. What this stage changes

**Nothing in the shipped verdict.** `assess()` is untouched;
`tests/test_gauge_detection.py` parses its imports and fails if
`siim.verify.gauge` ever appears among them. No threshold moved in either
direction. The 36-of-36 blind spot is exactly as open as it was before this
stage ran.

**What it adds is a bounded negative and a working mechanism.** The blind spot
cannot be closed with archive corner geometry as the reference, and the reason
is quantified rather than asserted: the reference's per-frame error is
66 – 109 px, larger than the gauge errors worth catching. The fit that would
catch them works — above the maximum of forty structureless draws on every
graph with redundancy ≥ 4.

**What must now be said in the deliverable.** The honest sentence is not *"we
detect gauge error"*. It is:

> Loop closure is exactly invariant to per-image gauge error; 36 of 36
> constructed cases reach VERIFIED / high with edges wrong by up to 115 px. We
> built the detector, and measured that the reference available to it — archive
> corner geometry — carries a per-frame error of its own of 66 – 109 px, which
> is larger than the errors it would need to find. The check is therefore **not
> deployed**. Closing this needs a geodetic reference, not more software.

## 10. What this stage does NOT claim

Unchanged from Part 1 §8, with two additions forced by the result:

- **Not a false-acceptance rate.** §53 criterion 3's first two clauses remain
  unmeasurable.
- **Not a fix to loop closure.** The invariance is an identity.
- **Not validated on a known real gauge error.** None exists to validate
  against; that asymmetry is the stage's main limitation.
- **Not an attribution** (§8).
- **Not a Chandrayaan-2 result.**
- **NEW — not a detector with an operating point.** S6 failed; there is no
  false-alarm rate to quote, and S1's and S3's numbers must never be quoted
  without S6 beside them.
- **NEW — not evidence that the 13 real triplets are gauge-free, or gauged.**
  The statistic does not discriminate at redundancy 1 (§6), so S2's 13 of 13 is
  uninformative about them in either direction.

## 11. Ledger and index

- **E-041** — S4 was frozen as a control that cannot test the property it
  names, and the population was frozen without checking that it could support
  the statistic (`redundancy = 1` on every triplet).
- **D-054** — the gauge check is **not deployed**, with the measured reason,
  and the mitigation recorded as an acquisition change rather than a software
  one.
- **RL-049** — research-log entry.
- `experiments/EXP-013/exp013_results.json` — every figure above.
