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
