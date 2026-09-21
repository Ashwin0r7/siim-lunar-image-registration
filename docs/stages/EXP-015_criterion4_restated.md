# EXP-015 — Criterion 4 restated under the metric that survived validation

**Part 1 — pre-registration. FROZEN 2026-09-21, before any threshold, pass
count or verdict has been computed.** Part 2 is empty until Part 1 is
committed.

**Classification: DELIVERABLE-CRITICAL, and unusually exposed to motivated
reasoning — which is why the criteria below are shaped the way they are.**

§53's criterion 4 reads *coverage gap ≤ 0.15 on every VERIFIED pair*. EXP-012
made it measurable and it **failed**: 14 of 39 VERIFIED edges exceed 0.15.
EXP-014 then measured **both of its components to be defective**:

- its **metric**, `max_uncovered_disc_ratio`, placed **last of four** on both
  measures and on both arms (D-055 reversed ADR-0006; `grid_occupancy` is now
  primary);
- its **threshold**, 0.15, is **4× too tight** — the calibrated crossing of a
  1.0 px worst-case bound is 0.611, and at 0.15 the 95th percentile of
  worst-case local error is **0.048 px**.

EXP-014 deliberately **did not** act on that. All 39 edges fall below the
calibrated 0.611, so declaring criterion 4 MET was available and was refused:
substituting a 4× looser threshold for the same metric, produced by the session
that benefits from it, is precisely the move the audit's closing line forbids.

**This stage does the principled version instead** — restate the criterion in
terms of the metric that *won* the validation, with a threshold calibrated the
same way — and it is written on the assumption that **this could be the same
bar-lowering wearing better clothes.** §4's S4 exists to catch that, and it is
the criterion this stage most expects to fail.

---

## 1. The question

**Q.** Under the coverage metric that survived EXP-014's validation, with a
threshold calibrated against the same 1.0 px worst-case local-error bound,
does §53's criterion 4 pass — **and does the restated criterion discriminate
at all at the inlier counts real registrations actually have?**

The second half is not a footnote. A criterion that everything passes is not a
criterion, and the honest failure mode here is not "it fails" but "it passes
vacuously".

Three outcomes, all of them results:

- **Restated criterion NOT MET** → criterion 4 fails under both its original
  and its corrected form, and the failure is now attributable to the
  registrations rather than to the instrument.
- **Restated criterion MET and discriminating** → criterion 4's failure was an
  artefact of a metric and threshold both measured to be wrong, the corrected
  form passes, and both verdicts stand side by side on the scorecard.
- **Restated criterion MET and vacuous** → §53's criterion 4 was
  **mis-specified from the start**: it tries to bound worst-case error through
  coverage on registrations whose coverage is saturated, where coverage carries
  no information. That is the most likely outcome (§5) and the most useful one.

## 2. What is re-analysed, and what is not

**No new computation of any kind. No re-match, no re-fit, no new byte.** Every
input is already recorded:

| input | source | what it supplies |
|---|---|---|
| 39 VERIFIED edge verdicts | `exp012_results.json`, `triplets[].verdicts[].verdict.metrics` | `coverage_occupancy` **and** `coverage_max_gap` per edge |
| 501 real calibration subsets | `exp014_results.json`, `rows[]` where `arm == "real"` | `grid_occupancy`, `max_uncovered_disc_ratio`, `p99_err_px` |

The calibration routine is `run_exp014.crossing_threshold`, **imported, not
reimplemented** — see S0.

**Disclosure.** While confirming the fields exist, one RD-07 row's
`coverage_occupancy` was seen incidentally (value 1.0). It is a REAL-DATA-07
row, not necessarily one of the 39, and no distribution, count or threshold has
been looked at. Recorded because the honest thing to do with an accidental peek
is to name it.

## 3. The restated criterion, fixed before it is evaluated

> **Criterion 4′.** `grid_occupancy` ≥ `T` on every VERIFIED pair, where `T`
> is the occupancy at which the 95th percentile of p99 local error crosses
> **1.0 px**, calibrated on EXP-014's real arm.

The 1.0 px bound is **EXP-014's, frozen there before any statistic and not
re-opened here**. Occupancy is "more is better", so `T` is a **floor** and the
crossing is approached from above — the mirror image of EXP-014's S3, and the
direction is fixed here so it cannot be chosen later.

## 4. Success criteria — frozen

| ID | Criterion | MET if |
|---|---|---|
| **S0** | **Instrument control.** The calibration is the same instrument EXP-014 used, not a new one | `crossing_threshold`, imported from `run_exp014`, reproduces EXP-014's recorded incumbent-metric crossing of **0.611** to within 1e-9 when re-run on `max_uncovered_disc_ratio`. If it does not, **nothing is reported** |
| **S1** | **Calibration.** `T` is computed and reported | `T` plus a 200-resample bootstrap CI, by the same routine. A measurement, not a pass/fail — MET when computed and reported, **whatever value it takes** |
| **S2** | **The re-measurement.** Criterion 4′ evaluated on the 39 VERIFIED edges | reported as it falls. **MET means the 39 pass; it does not mean criterion 4 is met** — see S3 |
| **S3** | **The original stays on the scorecard.** | the artefact records the original criterion 4 verdict (**NOT MET, 14 of 39 above 0.15**) in the same block as 4′, and the audit states both. A restatement that deletes the finding it restates is a rewrite, not a correction |
| **S4** | **The anti-vacuity criterion — the one this stage expects to fail.** 4′ must be able to reject something | **both** must hold: (a) `T` rejects **≥ 10 %** of EXP-014's own 501 real subsets — a floor nothing fails is not a floor; **and** (b) the 39 edges' occupancy values are **not** all saturated: at least one sits below 0.99, so the criterion is being applied in a regime where the metric still varies. **If S4 fails, 4′ is vacuous at real inlier counts, S2's verdict carries no evidential weight, and it may not be quoted as passing criterion 4** |
| **S5** | **Extrapolation honesty.** | the fraction of the 39 edges whose occupancy lies **outside** the range EXP-014 sampled (0.016–0.938) is computed and reported. Any edge above 0.938 is being judged by extrapolation, and the count is stated in the headline rather than a footnote |

**Predicted outcome, recorded now so it can be wrong.** S0–S3 MET; **S4 NOT
MET at MEDIUM-HIGH confidence**, and S5 expected to show most of the 39 edges
above EXP-014's sampled range. The reasoning: EXP-014's subsets carried 12–200
points and reached occupancy 0.016–0.938, while the 39 VERIFIED edges carry
**1656–5437 inliers**, which should saturate an 8×8 occupancy grid. This is
RL-050c — *nothing samples the regime real registrations occupy* — arriving as
a concrete consequence rather than a caveat.

**If S4 fails, this stage's conclusion is that criterion 4 is mis-specified,
not that it passes.** That conclusion is written here, before the numbers, so
it cannot be softened after them.

## 5. What may not happen in Part 2

- The **1.0 px bound may not move**, in either direction.
- `T` may not be adjusted, rounded, or replaced by a "practical" value.
- Criterion 4 may **not** be reported as MET on the strength of 4′ alone.
  4′ is a *restatement under a validated instrument*; whether §53 adopts it is
  a recorded decision, and this stage supplies the measurement for that
  decision rather than taking it.
- If S4 fails, **no pass verdict from S2 may appear in the README, the demo or
  the audit headline** without "vacuous at real inlier counts" in the same
  sentence.

## 6. What this stage explicitly does NOT claim

- **Not an accuracy claim.** Every error figure is inherited from EXP-014's
  self-warps, which share the original's texture and therefore bound
  *precision*, not accuracy (EXP-010 S1).
- **Not a verdict change.** `assess()` and `COVERAGE_GAP_WARN` are untouched.
- **Not a Chandrayaan-2 result.**
