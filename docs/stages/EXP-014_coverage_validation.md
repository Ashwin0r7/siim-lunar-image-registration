# EXP-014 — Does the coverage metric predict the error it claims to bound?

**Part 1 — pre-registration. FROZEN 2026-09-21, before any correlation, AUC or
threshold has been computed.** Part 2 is empty until Part 1 is committed.

**Classification: DELIVERABLE-CRITICAL.** This is a debt the project set itself
and then did not pay. **ADR-0006 / D-006 has been `PROPOSED` since 2026-08-24**,
and its acceptance rule is explicit:

> **Accept** if EXP-007 shows it correlates with local held-out error better
> than the alternatives. **Reverse** if it does not — then it is simply the
> wrong metric.

**EXP-007 ran and never performed that test.** Its stage report does not
mention coverage once. The omission went unnoticed for six weeks because until
EXP-012 produced the project's first VERIFIED verdict, §53's criterion 4 ranged
over an empty set and nothing forced the question.

**What rests on the unpaid debt.** `COVERAGE_GAP_WARN = 0.15` in `verdict.py`
is the only one of the verdict's three constants with no measurement behind it
— `INLIER_CUTOFF = 8` cites EXP-002 (recall 1.000, FPR 0.0112 on 192 held-out
cases) and `LOOP_ERROR_REJECT_PX = 2.0` cites EXP-003 (correct loops 0.258 px
median against wrong loops 1368 px). The 0.15 first appears at
`MASTER_RESEARCH_AND_ARCHITECTURE_PLAN.md:46` as a design-table target and is
promoted to a §53 success criterion at line 725 without ever being measured.
**D-053** records that criterion 4 is therefore currently a failure against an
uncalibrated line: 14 of 39 VERIFIED edges exceed 0.15, and nobody knows what
0.15 means.

---

## 1. The question

**Q.** `max_uncovered_disc_ratio` was chosen over three alternatives by an
argument about what it *bounds*: registration error at a point grows with
distance to the nearest constraining correspondence, so the largest empty disc
upper-bounds worst-case local error. **Does it, measurably, and better than the
alternatives?** And at what value does a stated local-error bound actually get
crossed?

Both answers are results, and ADR-0006 already committed to acting on either:

- **If it wins**, D-006 moves to `ACCEPTED` after six weeks as `PROPOSED`, a
  *measured* threshold replaces the asserted 0.15, and §53's criterion 4 is
  re-measured against a line that means something.
- **If it loses**, `max_uncovered_disc_ratio` is the wrong metric, D-006
  **reverses** to whichever alternative wins, the verdict's coverage evidence
  is restated in those terms, and criterion 4 loses its subject.

## 2. What "local held-out error" means here, stated exactly

Not a fit residual, and not an average. For a correspondence subset `S` fitted
to transform `T̂`, against a **known** ground-truth transform `T`:

```
err(x) = ‖ T̂(x) − T(x) ‖     over a grid of x inside the ROI
```

This is `geometry.endpoint_error` — it compares the **maps**, not the residuals
of the points that produced them, which is what makes it a true accuracy and
not the circular statistic EXP-001 was built to avoid.

**The quantity coverage claims to bound is the WORST CASE, not the mean**, so
the response variable is `p99` of `err(x)` over the ROI, with `max` reported
beside it. An average cannot bound a worst case — that argument is ADR-0006's
own reason for rejecting occupancy and entropy as primary, and it would be
incoherent to validate the metric against a mean.

## 3. Data, fixed in advance

No new byte is fetched. Two populations:

**(a) Real NAC self-warps — the primary arm.** The recorded Mare Serenitatis
tiles in `data/processed/mare_serenitatis/` (**32 present**). Ten are used, the
first ten in sorted filename order, fixed here so the selection cannot follow
the result. Each tile is warped by a known transform to give **exact** ground
truth on real lunar texture — the EXP-010 / EXP-011 construction, unchanged.

**(b) Synthetic terrain — the breadth arm.** `data.synthetic_terrain` at two
regimes (mare and highlands), exact ground truth by construction. Reported
separately and **never pooled** with (a): a conclusion that holds on one and
not the other is a finding, and pooling would hide it.

**Subset construction — the independent variable.** Coverage is only testable
if coverage *varies*, so subsets are drawn with deliberately different spatial
shapes, declared in full here: `uniform`, `clustered` (one Gaussian blob),
`half` (one side of the frame), `corner` (one quadrant), `ring` (annulus),
`two_blobs`. Sizes: **12, 25, 50, 100, 200** points (capped at the pool size).
Every (shape × size) cell is attempted on every tile.

## 4. Success criteria — frozen

| ID | Criterion | MET if |
|---|---|---|
| **S0** | **Harness control.** The ground truth and the error field are real | fitting the **full** correspondence pool gives median `err(x)` **< 0.05 px**. If this fails, nothing is reported from that tile |
| **S1** | **ADR-0006's own test.** `max_uncovered_disc_ratio` correlates with p99 local error better than each alternative | its \|Spearman ρ\| against p99 error exceeds that of **all three** of `grid_occupancy`, `spatial_entropy`, `hull_ratio`, on the real arm |
| **S2** | **Discrimination.** It is the better *detector*, not merely the better correlate | as a binary detector of `p99 err > 1.0 px`, its ROC AUC exceeds all three alternatives', on the real arm |
| **S3** | **Calibration — the number that replaces 0.15** | reported unconditionally: the value of `max_uncovered_disc_ratio` at which the **95th percentile** of p99 local error crosses **1.0 px**, with a bootstrap CI. This is a *measurement*, not a pass/fail — it is MET when it is computed and reported, and it is reported **whether or not it lands near 0.15** |
| **S4** | **The confound control, and the criterion most likely to fail.** Coverage must predict error for a reason other than point count | the **partial** Spearman ρ between `max_uncovered_disc_ratio` and p99 error, controlling for `n_points`, is ≥ 0.3 in magnitude and of the predicted sign. **If S4 fails, S1 and S2 mean nothing** and must not be quoted without it |
| **S5** | **Breadth.** The ranking is not an artefact of one terrain | the S1 winner on the synthetic arm is the same metric as on the real arm. If not, the result is scoped to mare and said so |

**Predicted outcome, recorded now so it can be wrong.** S1 **MET** at MEDIUM
confidence, S4 **MET** at LOW-MEDIUM confidence. The honest worry is S4: a
small subset has both bad coverage and a worse fit for ordinary
degrees-of-freedom reasons, so the raw correlation in S1 is partly a proxy for
`n_points` and may be *entirely* that. **S4 exists because E-041 was recorded
three hours earlier**: name the confound, and the control for it, in Part 1 —
not after seeing the number.

**What may not happen in Part 2.** The 1.0 px bound in S2 and S3 is declared
here and may not be moved to make a threshold land near 0.15. The subset shapes
and sizes may not be extended. If the calibrated threshold disagrees with 0.15,
**0.15 is what changes**, and criterion 4 is re-measured against the new value
with the old figure kept beside it.

## 5. What this stage explicitly does NOT claim

- **Not a real cross-illumination accuracy claim.** Self-warps share the
  original's texture, so every error here is an **upper bound on precision**,
  exactly as EXP-010 §S1 states. This stage measures which *metric* tracks
  error, not how accurate the pipeline is on a real pair.
- **Not a verdict change.** Whatever S3 returns, `assess()` is not edited by
  this stage: REAL-DATA-03, -04 and -05 declare they applied that rule
  unchanged. A new constant is a separate, recorded decision.
- **Not a Chandrayaan-2 result.**

---

# Part 2 — what happened

**Run 2026-09-21, `scripts/run_exp014.py`, 48.3 s, CPU only, no new data.**
Artefact: `experiments/EXP-014/exp014_results.json`. **681 rows** — 501 real
(10 NAC tiles), 180 synthetic (mare + highlands).

## 0. The result in one paragraph

**ADR-0006 is refuted on its own test, and it reverses.**
`max_uncovered_disc_ratio` — the project's PRIMARY coverage metric for six
weeks — is the **worst of the four** on both measures the ADR named, on both
arms. It places last by correlation (|ρ| **0.603** against 0.681–0.701) and
last as a detector (AUC **0.927** against 0.980–0.984). The confound control
**passed** (partial ρ = 0.542 controlling for point count), so this is not an
artefact of subset size: coverage genuinely predicts worst-case local error,
and the incumbent metric is simply the weakest way to measure it. Separately,
the asserted **0.15** threshold is measured to be **4× too tight**: the
calibrated crossing is at **0.611** (95 % CI 0.498–0.720), and at 0.15 the 95th
percentile of worst-case local error is **0.048 px** — twenty times below the
1.0 px bound frozen in Part 1.

| | criterion | verdict |
|---|---|---|
| **S0** | harness control — full-pool fit median dense error < 0.05 px | **MET** — every tile that entered passed; none failed |
| **S1** | the incumbent beats all three alternatives by \|Spearman ρ\| | **NOT MET** — it is **last** |
| **S2** | the incumbent beats all three as a detector (ROC AUC) | **NOT MET** — it is **last** |
| **S3** | the calibrated threshold that replaces 0.15 | **MET (a measurement)** — **0.611**, CI **0.498–0.720** |
| **S4** | partial ρ ≥ 0.3 controlling for `n_points`, correct sign | **MET** — **0.542** |
| **S5** | the S1 winner replicates on synthetic terrain | **NOT MET by the letter** — see §5 |

Nothing was retuned. The 1.0 px bound, the subset shapes and sizes, and the
S4 floor are the ones Part 1 §4 froze.

## 1. S0 — the harness is real — **MET**

Fitting the full true-correspondence pool reproduces the known transform to a
**median dense endpoint error below 0.05 px** on every tile that entered. Tiles
that could not supply a pool were skipped with the reason recorded, and the
runner is written to report nothing from a tile whose control fails.

This matters more than it looks: it is the guarantee that the response variable
is a **true error against a known map**, not a fit residual — the distinction
EXP-001 exists to enforce (E-008).

## 2. S1 and S2 — the incumbent loses, on both measures — **NOT MET**

Real arm, 501 rows, 18 of them over the 1.0 px bound:

| metric | \|Spearman ρ\| | ρ | sign as predicted | ROC AUC | partial ρ (controlling `n_points`) |
|---|---|---|---|---|---|
| `max_uncovered_disc_ratio` *(incumbent, PRIMARY)* | **0.603** ← last | +0.603 | yes | **0.927** ← last | +0.542 |
| `hull_ratio` | 0.681 | −0.681 | yes | **0.984** | −0.602 |
| `grid_occupancy` | 0.699 | −0.699 | yes | **0.984** | −0.579 |
| `spatial_entropy` | **0.701** ← best | −0.701 | yes | 0.980 | −0.585 |

Every metric carries the **sign ADR-0006 predicts** — more coverage, less
worst-case error — so the *concept* is sound. What fails is the choice of
estimator.

**Why the incumbent loses, and it is not a subtlety.** ADR-0006's argument was
that "averages cannot bound a worst case", so the largest empty disc must beat
occupancy and entropy. **The argument is correct and the conclusion is wrong**,
for a reason the argument does not address: the largest empty disc is decided
by a **single hole**, so as an *estimator* it has high variance, while
occupancy and entropy aggregate over the whole ROI and are stable. The right
quantity, measured noisily, loses to a proxy measured precisely. That is a
statistical failure, not a conceptual one, and it could only ever have been
found by measurement — which is exactly why the ADR made itself falsifiable and
why leaving the test unrun for six weeks was the real defect (**E-042**).

## 3. S4 — the confound control — **MET**, and it is what makes §2 mean anything

Partial Spearman ρ between `max_uncovered_disc_ratio` and p99 local error,
controlling for `n_points`: **+0.542** against a frozen floor of 0.30, with the
predicted sign. Raw ρ was +0.603, so **most of the association survives** the
control — a small subset is not merely a badly-covered one.

All four metrics hold up: −0.579 (occupancy), −0.585 (entropy), −0.602 (hull).
So the ranking in §2 is a ranking of coverage measures, not a ranking of
proxies for point count.

Part 1 predicted S4 **MET at LOW-MEDIUM confidence** and called it the
criterion most likely to fail. It passed comfortably; the prediction was
too pessimistic and is recorded as such.

## 4. S3 — the number that replaces 0.15 — **0.611 (CI 0.498–0.720)**

Binned over the real arm, 24 bins of ~21 rows:

| coverage gap | n | p95 of p99 local error | median |
|---|---|---|---|
| 0.109 – 0.160 | 21 | **0.048 px** | 0.039 px |
| 0.193 – 0.236 | 21 | 0.077 px | 0.043 px |
| 0.294 – 0.325 | 21 | 0.098 px | 0.049 px |
| 0.415 – 0.447 | 20 | 0.090 px | 0.054 px |
| 0.498 – 0.518 | 21 | 0.457 px | 0.081 px |
| 0.590 – 0.604 | 21 | 0.344 px | 0.087 px |
| **0.604 – 0.623** | 21 | **1.956 px** ← crosses | 0.097 px |
| 0.666 – 0.733 | 21 | 3.603 px | 0.305 px |
| 0.733 – 0.908 | 21 | 4.004 px | 0.520 px |

**The incumbent 0.15 sits inside the very first bin, where the 95th percentile
of worst-case local error is 0.048 px.** The bound it is supposed to enforce is
1.0 px. It is not conservative by a margin — it is conservative by a factor of
**twenty in error**, and **four in threshold**.

The crossing at 0.604–0.623 is **directly observed**, not extrapolated: three
bins above it (n = 21 each) all exceed the bound, and the bootstrap over 200
resamples puts the crossing in **0.498–0.720**.

**Scope limit, stated rather than left to be found.** The calibration rests on
subsets of 12–200 correspondences, whose gaps span 0.109–0.908. Real recorded
registrations carry 1656–5437 inliers and sit at the low end of that range
(EXP-012's 39 VERIFIED edges run 0.038–0.406). The **crossing region** is
densely sampled, so the threshold itself is well supported; the behaviour
*below* 0.109 is not sampled here at all, and nothing in this stage says
anything about it.

## 5. S5 — replication on synthetic terrain — **NOT MET by the letter, and the part that matters replicates**

Synthetic arm, 180 rows, 21 over the bound:

| metric | \|ρ\| | ROC AUC |
|---|---|---|
| `max_uncovered_disc_ratio` *(incumbent)* | **0.722** ← last | **0.857** ← last |
| `spatial_entropy` | 0.778 | 0.928 |
| `hull_ratio` | 0.778 | 0.943 |
| `grid_occupancy` | **0.786** ← best | **0.946** ← best |

S5 asked whether the **S1 winner** is the same metric on both arms. It is not:
`spatial_entropy` wins on real (0.701), `grid_occupancy` on synthetic (0.786),
and on the real arm those two are separated by **0.002** — within noise. **So
S5 is NOT MET as frozen.**

**But S5 was written to test whether the ranking is a terrain artefact, and the
part of the ranking this stage turns on is identical on both arms:** the
incumbent places **last on both measures on both arms**. The refutation
replicates; only the identity of the winner does not.

This is the third time in two days a criterion has been answered as frozen
while the question it was meant to ask needed a different instrument (E-039,
E-041). It is recorded the same way: **S5 NOT MET as written, with the
replication the stage actually needed reported beside it** — not folded into
the criterion.

## 6. The decision ADR-0006 committed to in advance

> **Reverse** if it does not — then it is simply the wrong metric.

**D-055 reverses D-006.** `grid_occupancy` becomes the primary coverage metric:
it is the only one that is **best or tied-best on three of the four
measurements** (real AUC 0.984 tied-first, synthetic |ρ| 0.786 first, synthetic
AUC 0.946 first) and second by 0.002 on the fourth. `spatial_entropy` wins one
measurement by a margin inside noise; `max_uncovered_disc_ratio` wins none and
loses all four.

`max_uncovered_disc_ratio` is **retained and demoted to secondary**, reported
beside the others. It is not removed: it is the only one of the four that is
*interpretable in pixels* (a disc radius the reader can picture on the image),
and its sign is correct — it is a weak estimator, not a wrong idea.

## 7. What this means for §53 criterion 4 — and what it deliberately does not

Criterion 4 reads: *coverage gap ≤ 0.15 on every VERIFIED pair.* EXP-012 found
**14 of 39 VERIFIED edges above 0.15**, so it is **NOT MET**.

**It stays NOT MET, and this stage does not change that.** Two facts are now
measured and both are reported:

1. Its **metric** is the worst of four tested (§2, §5), so the criterion is
   phrased in terms of the weakest available instrument.
2. Its **threshold** is 4× too tight (§4). All 39 VERIFIED edges — gaps
   0.038–0.406 — fall **below** the calibrated 0.611, so against a calibrated
   line the criterion would pass.

**That second fact is stated and not acted on.** Declaring criterion 4 MET by
substituting a threshold this stage produced would be exactly the move the
audit's closing line forbids — *none of the above is fixed by lowering a bar* —
and it would be worse here than usual, because the substituted threshold is
4× looser and was produced by the same session that benefits from it. What is
legitimate is to **say the criterion is a weak instrument and show the
measurements**; restating §53 is a decision for the deliverable, taken
deliberately and recorded, not a side effect of a stage run.

The recommendation, recorded for that decision and not enacted here: restate
criterion 4 in terms of `grid_occupancy` with a threshold calibrated the same
way, and re-measure. That requires occupancy on the 39 edges and a fresh
calibration against the same 1.0 px bound — a separate, small stage.

## 8. What this stage does NOT claim

- **Not a real cross-illumination accuracy claim.** Self-warps share the
  original's texture, so every error here is an **upper bound on precision**
  (EXP-010 S1). This measures which *metric* tracks error, not how accurate the
  pipeline is on a real pair.
- **Not a verdict change.** `assess()` is untouched. `COVERAGE_GAP_WARN` still
  reads 0.15; changing it is D-055's follow-on decision, with the same
  frozen-rule constraint REAL-DATA-03, -04 and -05 impose.
- **Not a claim below gap 0.109**, which this design never sampled.
- **Not a Chandrayaan-2 result.**

## 9. Ledger and index

- **E-042** — an ADR made itself falsifiable, assigned its own acceptance test
  to a named stage, and nothing checked that the stage ran it. Six weeks and
  seven stages later the metric was still `PROPOSED` and load-bearing.
- **D-055** — D-006 reverses; `grid_occupancy` primary,
  `max_uncovered_disc_ratio` demoted to secondary and retained for
  interpretability.
- **RL-050** — research-log entry.
- `experiments/EXP-014/exp014_results.json` — every figure above.
