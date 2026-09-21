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

---

# Part 2 — what happened

**Run 2026-09-21, `scripts/run_exp015.py`, 0.1 s, pure re-analysis of recorded
artefacts.** Artefact: `experiments/EXP-015/exp015_results.json`.

## 0. The result in one paragraph

**All six criteria are MET — and criterion 4 should still not be reported as
passed.** The restated criterion 4′ passes on all 39 VERIFIED edges, but it
passes on three margins so thin that the pass carries almost no weight:
**one edge sits *exactly* on the calibrated floor** (occupancy 0.078125, floor
0.078125, margin **0.000000**, and a `>` instead of the frozen `≥` would make
it 38/39 and NOT MET); **S4's anti-vacuity bar clears by 0.58 percentage
points** (10.58 % against a frozen 10 %); and **14 of 39 edges — 36 % — are
judged by extrapolation**, sitting above the occupancy range EXP-014 ever
sampled. The honest conclusion is the one Part 1 §1 listed third, arrived at by
a different route than predicted: **§53's criterion 4 is mis-specified**, and
restating it under a validated metric converts a clear failure into a marginal
pass rather than into a meaningful one.

**The prediction in Part 1 was wrong.** S4 was expected to fail at MEDIUM-HIGH
confidence on saturation grounds. It passed: 25 of the 39 edges sit below the
0.99 saturation level, so the metric does still vary where it is applied. The
reasoning was half right — 14 edges *are* pinned at exactly 1.0 — and the
conclusion drawn from it was wrong. Recorded as a wrong prediction.

| | criterion | verdict |
|---|---|---|
| **S0** | the calibration is EXP-014's instrument, not a new one | **MET** — reproduces 0.6113534312076709 **exactly** |
| **S1** | the calibrated occupancy floor `T` | **MET** — `T` = **0.078125**, CI **0.03125 – 0.09375** |
| **S2** | criterion 4′ on the 39 VERIFIED edges | **MET** — 39 / 39 pass, **one by exact equality** |
| **S3** | the original verdict stays on the scorecard | **MET** — original **NOT MET**, 14 / 39 over 0.15, recorded beside 4′ |
| **S4** | anti-vacuity: the floor must reject something, and the metric must vary | **MET** — rejects **10.58 %** of the calibration set; **25 / 39** edges below saturation |
| **S5** | extrapolation honesty | **MET** — **14 / 39 (35.9 %)** lie outside the sampled range |

## 1. S0 — the instrument is the same one — **MET**

`crossing_threshold`, imported from `run_exp014` rather than reimplemented,
reproduces EXP-014's recorded incumbent crossing to the **last bit**:
`0.6113534312076709` against `0.6113534312076709`, difference exactly zero.

This is the criterion that makes the rest admissible. A "corrected" criterion
evaluated with a newly written calibration routine would be free to produce any
answer and call the difference a correction; this shows the only thing that
changed is the **metric being calibrated**.

## 2. S1 — the floor — **`T` = 0.078125**

The occupancy at which the 95th percentile of p99 local error crosses 1.0 px
is **0.078125**, bootstrap CI **0.03125 – 0.09375**.

**That value is exactly 5/64** — five occupied cells of an 8 × 8 grid. It is not
a coincidence that it looks like a fraction: `grid_occupancy` is a **discrete**
metric taking only values `k/64`, so both the calibration bins and the
threshold land on lattice points. §3 is where that stops being a curiosity.

## 3. S2 — the re-measurement, and the tie it turns on — **MET, 39 / 39**

The 39 VERIFIED edges carry occupancy **0.078125 – 1.000000**, median
**0.9375**. All 39 clear the floor.

**One of them clears it by exactly nothing.**

| rank | occupancy | margin over `T` |
|---|---|---|
| 1 | **0.078125** | **+0.000000** |
| 2 | 0.281250 | +0.203125 |
| 3 | 0.437500 | +0.359375 |
| 4 | 0.453125 | +0.375000 |
| 5 | 0.453125 | +0.375000 |

The lowest-coverage VERIFIED edge sits **exactly on the calibrated floor** —
both are 5/64, because a discrete metric and a threshold calibrated on it share
a lattice. Part 1 §3 froze the criterion as **`grid_occupancy ≥ T`**, so the
edge passes and the freezing was done before any number was seen. But the
verdict on criterion 4′ **turns on that `≥`**: written `>`, the result is
**38 / 39 and NOT MET**.

**A criterion whose verdict is decided by the inclusive-versus-exclusive
comparison on an exact tie is not a criterion anyone should lean on**, and no
amount of correct pre-registration changes that. It is reported here in the
headline rather than left for a reader to find in the rows.

## 4. S3 — the original stays — **MET**

Recorded in the same block as 4′, not replaced by it:

> **§53 criterion 4, as written:** coverage gap ≤ 0.15 on every VERIFIED pair.
> **Verdict: NOT MET — 14 of 39 edges exceed 0.15**, gaps running 0.038–0.406.

A restatement that deletes the finding it restates is a rewrite. Both verdicts
now sit side by side, and the audit states both.

## 5. S4 — the anti-vacuity criterion — **MET, by 0.58 percentage points**

Both halves were required and both hold, one of them barely:

- **(a)** The floor rejects **53 of EXP-014's 501** real calibration subsets =
  **10.58 %**, against the frozen bar of **10 %**. **Had the bar been set at
  10.6 % this criterion would have failed.**
- **(b)** **25 of 39** VERIFIED edges sit below the 0.99 saturation level, so
  the metric genuinely varies in the regime where the criterion is applied.
  This is the half Part 1 expected to fail, and it did not.

**(a) clearing by 0.58 pp is not a comfortable pass.** The bar was frozen at a
round 10 % with no measurement behind *it* either, and the result landing 0.58
pp above a number chosen for its roundness is luck, not evidence. Stated
plainly rather than presented as a pass.

## 6. S5 — how much of this is extrapolation — **14 of 39, 35.9 %**

EXP-014 sampled occupancy **0.016 – 0.938**. **Fourteen of the 39 edges sit at
exactly 1.000** — above everything the calibration ever observed. They are
judged by extrapolating a floor into a regime the calibration never entered.

They would pass any floor in `(0, 1]`, so their passing carries no information
about the threshold. **The effective evidential population is 25 edges, not
39**, and that is RL-050c — *nothing samples the regime real registrations
occupy* — arriving as a measured count rather than a caveat.

## 7. What this stage concludes

**Criterion 4 is not rescued, and must not be reported as passed.** Collecting
the three margins:

1. the pass depends on an **exact tie** resolved by a `≥`;
2. the anti-vacuity bar clears by **0.58 pp** against a round number with no
   measurement behind it;
3. **36 %** of the population is above the calibration's range and would pass
   any floor at all.

Any one of those would be a caveat. Together they mean 4′ separates the 39
edges from failure by almost nothing, and the correct reading of §53's
criterion 4 is the third branch Part 1 §1 listed: **it is mis-specified.** It
attempts to bound worst-case local error through a coverage statistic on
registrations carrying 1656–5437 inliers, where coverage is at or near
saturation for a third of them and the discriminating range is a handful of
lattice points wide.

**The artefact's own one-line verdict reads *"Criterion 4' is MET and
discriminating."*** That sentence is mechanically true against the frozen
criteria and it is **insufficient**, which is why it is quoted here rather than
repeated as the finding. The artefact is not rewritten — integrity rule 4 — and
Part 2 is where it is read properly.

**What this vindicates.** EXP-014 §7 declined to declare criterion 4 MET by
substituting a looser threshold for the same metric, calling that "the move the
audit's closing line forbids". Doing the principled version instead produced a
pass so marginal that leaning on it would have been the same error with better
paperwork. **The refusal was right, and it is worth more than the pass would
have been.**

## 8. What this stage does NOT claim

- **Not an accuracy claim.** Every error figure is inherited from EXP-014's
  self-warps, which bound **precision**, not accuracy (EXP-010 S1).
- **Not a verdict change.** `assess()` and `COVERAGE_GAP_WARN = 0.15` are
  untouched.
- **Not an adoption of 4′ into §53**, and on this evidence it should not be
  adopted. The measurement is supplied; the decision is D-057's.
- **Not a Chandrayaan-2 result.**

## 9. Ledger and index

- **D-057** — §53 criterion 4 is recorded as **mis-specified**; it stays
  **NOT MET** on the scorecard in its original form, 4′ is **not** adopted, and
  what would settle it is named.
- **RL-052** — research-log entry.
- `experiments/EXP-015/exp015_results.json` — every figure above.
