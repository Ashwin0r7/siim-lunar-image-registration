# Final success criteria — measured audit

**Written 2026-09-20.** `MASTER_RESEARCH_AND_ARCHITECTURE_PLAN.md` §53 states
five final success criteria. This document evaluates each one against recorded
artefacts and says, without softening, which are met, which are not, and which
**cannot be evaluated from what exists**.

Nothing here re-scopes a criterion. Where a criterion cannot be answered, that
is reported as a gap in the evidence, not rewritten into one that can be.

| # | Criterion (§53, verbatim) | Verdict |
|---|---|---|
| 1 | H1 MET on real data at ≥ 2 rungs with the frozen rule; p ≤ 0.05 on the illumination separation with ≥ 8 edges | **MET** |
| 2 | ≥ 1 VERIFIED Chandrayaan-2 pair per sensor against NAC, with check-point error and CI reported in coarse pixels | **NOT MET** — but no longer blocked on data (see the 2026-09-20 REAL-DATA-09 update). *(2026-09-28: EXP-023 delivers the first **VERIFIED** Chandrayaan-2 result — OHRC ↔ NAC, loop 1.9158 px — and the criterion still stays NOT MET: its check-point clause needs a reference independent of LRO and none exists at the site. The OHRC sub-clause now reads, as frozen in advance: **VERIFIED by loop closure, check points unavailable** — see the update below.)* |
| 3 | Verdict FA ≤ 5 %, FR ≤ 20 % on validation sites; zero VERIFIED on the adversarial set | **PARTLY ANSWERED** — the adversarial clause is MET (0 of 36), but for the wrong reason (E-039); FA and FR remain unmeasurable *(2026-09-23: measured by EXP-021 — see below)*. **EXP-013 built the instrument for the blind spot E-039 exposed and measured that it cannot be deployed with the reference on hand (D-054); the blind spot is open** |
| 4 | Coverage gap ≤ 0.15 on every VERIFIED pair | **NOT MET — and now measured to be MIS-SPECIFIED (D-057).** 14 of 39 VERIFIED edges exceed 0.15. **EXP-014** then measured both components defective: the metric placed **last of four** (D-055 reversed ADR-0006) and the threshold is **4× too tight**. **EXP-015** restated it under the metric that won, and the restatement passes 39/39 **on an exact tie at the floor, a 0.58 pp anti-vacuity margin, and 36 % of edges extrapolated** — so the restatement is **not adopted** and the original verdict stands. Answerable in neither direction until a calibration samples real inlier counts (RL-050c). *(2026-09-23: **answered by EXP-022, NOT MET on three named edges** — see the update below.)* |
| 5 | Fresh-clone install, CPU-only, all tests pass, no non-commercial weights | **MET (measured today)** |

---

## UPDATE 2026-09-28 (latest) — EXP-023: the first VERIFIED Chandrayaan-2 result, and neither scorecard's verdict moves

`docs/stages/EXP-023_ohrc_nac_chandrayaan3_site.md` Part 2, artefacts
`experiments/EXP-023/`. The problem statement's own case, frozen before any
NAC label or pixel from the Chandrayaan-3 site was read.

| reading | number | verdict |
|---|---|---|
| OHRC → NAC edges (B1, 78.5° incidence) | **18 017 / 17 919 inliers**, both pass | matching succeeded |
| refined-corner corroboration | 105.33 / 109.74 px against a **98.01 px floor** (187–195 m; centre terms **+184 / +172 m east**) | INCONCLUSIVE ⇒ **S2 NOT MET as frozen** |
| primary triangle {O1, O2, Na} | loop **1.9158 Na-coarse px = 3.41 m** vs the frozen 2.0; legs 18 017 / 18 447 / 29 422 | **VERIFIED · moderate** (S3 MET) |
| displaced-ground nulls (8 km) | **4 / 4 inliers**, both fail | S4 MET |
| second engine (B4L) | 1 402 / 1 525 inliers; agreement with B1 **0.418 / 0.347 px median** | S5 MET |
| system-level (SPICE) corners | 2.87 / 2.67 km | as predicted (2–3 km) |

**Scorecards after EXP-023: §53 2 of 5, unchanged.** Criterion 2 stays NOT
MET — the check-point clause is unanswerable at this site — while its OHRC
sub-clause becomes *VERIFIED by loop closure, check points unavailable*
(D-071), the exact wording Part 1 froze for this outcome. **§2.2 ≈ 55 %,
unchanged in verdicts, stronger in text:** the scale row gains a real
cross-sensor rung (OHRC 0.26 m ↔ NAC 0.89 m native, 3.4 : 1, bridged by the
recorded degrade), and the viewpoint row gains the first real viewing
differences (12.6° / 16.6°, and the 32° stereo edge at 30 148 inliers).
Neither row flips on one site with matched illumination. E-062 records the
"no NAC coverage" wording the census refuted (116 products, 1 admissible).

## UPDATE 2026-09-24 — EXP-024: criterion 4's answer is complete, from each edge's own layout

`docs/stages/EXP-024_coverage_direct_bound.md`, artefacts `experiments/EXP-024/`.
EXP-022's proxy cells are replaced by the measurement they stood in for: all 22
distinct edges re-matched with the inlier positions kept (every recorded count
and occupancy reproduced **exactly**; the positions are now an artefact), and
the 1 px worst-case bound read from each edge's own layout at σ_N = 0.7202 px.

| reading | number | verdict |
|---|---|---|
| direct bound from the edge's own layout, every edge | **20 of 22** distinct edges (37 of 39 edge-rows) within 1 px (0.074–0.874); over: **9-inlier 5.42 px**, **28-inlier 1.59 px** | NOT MET |
| the 7 edges EXP-022 could not sample | 0.074–0.507 px, **all within** — nothing is unsampled any more | decided |
| the 68-inlier edge (EXP-022's "above the floor and over the bound") | its **own layout is within at 0.83 px** against the proxy's 1.04: same count, same occupancy, opposite sides — the sharpest floor-insufficiency example yet | proxy call falls (D-069-N1) |
| shrunk-layout null | exceeds every edge's own bound, **22 of 22** (5.4–8.2×) | property present |
| VERIFIED triplets | **11 of 13 clear on all three edges** (was 3 clear, 3 carrying, 7 undecided); the 2 carrying a failing edge are named in D-070 | complete |

**Scorecards after EXP-024: §53 2 of 5, unchanged** (row 4 stays NOT MET as
frozen; its answer is now complete and rests on two named edges, not three,
with nothing decided by proxy). **§2.2 ≈ 55 %, unchanged**: the
uniform-distribution row stays NOT MET with the smaller named set. Scope
beside every number: synthetic truth, iid noise at the recorded level, mare
only; no edge is shown wrong and no edge is shown accurate.


## UPDATE 2026-09-23 — EXP-022: criterion 4 answered, NOT MET, and the floor itself is inadequate

`docs/stages/EXP-022_coverage_at_real_counts.md`, artefacts `experiments/EXP-022/`
(v1 as frozen; v2 under Amendment A1, the recorded pipeline's own image
preparation). **The two runs agree on every criterion's outcome.**

**Criterion 4 stays NOT MET, and it is no longer answerable in neither
direction.** EXP-014's instrument was re-run at the 39 VERIFIED edges' own
inlier counts (9–5 437), with destination noise at the recorded fit RMSE
(σ_N = 0.720 px). It reached the regime EXP-015 could only extrapolate to:
1 026 rows at ≥ 1 000 points, and 97 at occupancy ≥ 0.99.

| reading | number | verdict |
|---|---|---|
| floor at recorded noise, T″ | **0.359** (CI95 0.297–0.453); noiseless arm 0.0625 — EXP-015's 5/64 was optimistic by 19 lattice steps | measured |
| every edge ≥ T″ + 1/64 (4″) | **37 / 39**; below: the **9-inlier** (0.078) and **28-inlier** (0.281) edges | NOT MET |
| direct bound: p95 of p99 < 1 px in the edge's matched cell | **25 of 28** evaluable edge-rows within (max 0.81 px); over: 9-inlier **3.93 px**, 28-inlier **1.66 px**, and a **68-inlier edge above the floor, 1.04 px** | NOT MET |
| every edge has ≥ 5 comparable rows | 7 of 22 distinct edges do not (108–5 392 inliers, occupancy 0.67–0.94) | NOT MET |
| high-count edges | all 14 edge-rows at occupancy 1.0 at **0.09–0.15 px** | extrapolation objection retired |

**What it means.** The 68-inlier edge sits above the floor and still breaks
the bound. A 47-inlier edge at nearly the same occupancy stays within it. So
**a one-dimensional occupancy floor cannot be criterion 4**: occupancy counts
filled cells, and it cannot see that the empty ones sit on one side. The
restatement 4″ is **not adopted** (D-069). A future criterion should be the
direct per-edge bound. Across the 13 VERIFIED triplets: **3 are clear on every
edge, 3 carry an edge over the bound, and 7 are undecided.** None of this says
any edge is wrong: EXP-021 labelled none of the 39 WRONG, and `assess()` is
untouched.

**Scorecards after EXP-022: §53 2 of 5, unchanged** (row 4 stays NOT MET, now
*answered* rather than *mis-specified and unanswerable*). **§2.2 ≈ 55 %,
unchanged**: the uniform-distribution row stays NOT MET, now with named edges
and a measured floor in place of an extrapolation.


## UPDATE 2026-09-23 (later) — EXP-021: criterion 3 measured, and it could not be tested where it matters

`docs/stages/EXP-021_verdict_fa_fr.md`, artefacts `experiments/EXP-021/`.

**Criterion 3 stays NOT MET, and it is no longer unmeasurable.** *(Correction
2026-09-28, integrity rule 3: the standing scorecard word for row 3 is
**PARTLY** — the FINAL RESCORE table and this update's own closing line both
say so, and "stays NOT MET" contradicted them as a drafting slip. The substance
is unchanged: the adversarial clause is MET for the wrong reason (E-039), and
FA/FR now carry pooled numbers — FDR 0/12, FRR 0/12 — that are not demonstrated
on the held-out site.)* Every recorded
edge was labelled against A -> Kaguya reference -> B, which uses no A<->B
correspondence, at 8.42 m / 25.3 m lines. That is 20-60x finer than the ~250 px
archive floor behind every earlier wrong-pass count.

| clause | reading | number | verdict |
|---|---|---|---|
| FA <= 5 % | B1 VERIFIED, pooled V u C | FDR **0 / 12** (CI95 upper 26.5 %); FAR **undefined** - 0 WRONG edges in the population | MET on the pooled reading, **not demonstrated**, never exercised |
| FA <= 5 % | held-out site alone | 1 labelled B1 edge | **NOT EVALUABLE** - ground truth reached 2 of 7 frames |
| FR <= 20 % | B1 VERIFIED, pooled | FRR **0 / 12** (CI95 upper 26.5 %) | MET on the pooled reading, **not demonstrated** |
| FR <= 20 % | held-out site alone | 1 edge | **NOT EVALUABLE** |
| zero VERIFIED adversarial | EXP-012, unchanged | 0 / 36 | MET for the wrong reason (E-039), unchanged |

**Why it is not reassurance (E-058).** All 39 labelled engine-edges were
CORRECT. The admission rule - B1 must register the frame to the reference -
kept only frames whose edges succeed. Re-read with single-engine legs admitted
(S5), the population finally holds **20 WRONG edges: 19 were stopped by the
inlier rule and the twentieth never reached VERIFIED. 0 of 84 VERIFIED
engine-edges are wrong, and 15 of 84 are AMBIGUOUS** (8.8-19.8 m) on three
frames whose own legs disagree by 0.5-1.6 ref px. **§54 is not triggered**, and
VERIFIED stays in the deliverable (D-068).

**Scorecards after EXP-021: §53 2 of 5, unchanged** (row 3 stays PARTLY: its FA
and FR now carry numbers and CIs, but not on the held-out site). **§2.2 ≈ 55 %,
unchanged** - no §2.2 row turns on FA/FR. Neither scorecard moved, and that is
recorded rather than softened.


## FINAL RESCORE — 2026-09-23, after EXP-016, EXP-017, EXP-018, EXP-019 and EXP-020

**Both scorecards, in one place, as `CLAUDE.md` requires.** Five stages ran
since the last rescore. **§53 did not move. §2.2 moved by more than any other
week in this project.** That sentence is the finding, and it is the same lesson
the section *"A second scorecard this audit never kept"* recorded two days
earlier: the project's own bar and the problem statement's bar measure
different things, and only tracking both makes the difference visible.

### (a) §53 — the project's own five criteria: **2 of 5 MET, unchanged**

| # | criterion | verdict 2026-09-21 | verdict 2026-09-23 | what changed |
|---|---|---|---|---|
| 1 | Illumination separation, ≥ 2 rungs, p ≤ 0.05 | **MET** | **MET** | EXP-018 re-measured it out of sample: the pooled rate transferred (0.600 against 0.595) **while every component range moved**, and Δincidence did **not** order outcomes on the held-out window (p = 0.575) |
| 2 | ≥ 1 VERIFIED Chandrayaan-2 pair per sensor + check-point error and CI | **NOT MET** | **NOT MET — and now missed by 8.9 %, not by a missing capability** | EXP-019 supplied the **check-point clause** (0.266 reference px = 2.24 m, CI95 0.222–0.413, 17 pairs) but the Chandrayaan-2 triangle closes at **2.177 reference px against the frozen 2.0**. The line was **not moved** |
| 3 | FA ≤ 5 %, FR ≤ 20 %; zero VERIFIED adversarial | **PARTLY** | **PARTLY, with a stronger bound** | EXP-018: **0 wrong passes in 41 out-of-sample passes** across three engines, and **7/7 triangles VERIFIED at 0.40–1.11 px** on ground no stage had opened. FA and FR remain **unmeasurable** without a calibration/validation site split |
| 4 | Coverage gap ≤ 0.15 on every VERIFIED pair | **NOT MET + mis-specified** | **NOT MET + mis-specified** | EXP-016 adds a number that makes it worse rather than better: at the scale envelope's own rung the median `grid_occupancy` is **0.484**, so the coarse registrations that pass every other check are the least uniformly covered |
| 5 | Fresh clone, CPU-only, tests pass, licences | **MET** | **MET** | the suite is larger and still green; the demo now also runs a **live** registration on user-supplied images, on CPU, offline |

**2 of 5 = 40 %.** Five stages, zero movement. **That is not a failure of the
stages** — each answered a question the project could not answer before — it is
a property of §53, which contains no criterion about scale, viewpoint or
modality. A judge reading only §53 would learn almost nothing about the week's
work.

### (b) §2.2 — the problem statement's nine requirements: **≈ 30 % → ≈ 55 %**

| PS requirement | acceptance (§2.2, as written) | 2026-09-21 | **2026-09-23** |
|---|---|---|---|
| Correspondence under Sun-angle change | envelope **≥ 40° Δinc** at TMC/IIRS rungs; boundary stated | NOT MET | **NOT MET as an envelope — but the hard edge is refuted in the permissive direction.** Out of sample, **44.19° passes under all three engines and 57.43° under two**, every one geometry-CONSISTENT with **no wrong pass** (D-059). In-sample the TMC-2 rung still fails from 24.7°, so what exists is *passes above 40°*, not *an envelope to 40°*, and the row says so |
| Scale invariance **2:1 to 320:1** | every rung ≤ 320:1 registers at ≥ 50 % overlap | NOT MET / **UNTESTED** | **NOT MET — and now MEASURED**, which is the whole change. Envelope **32 : 1** (11/11 to 32, 8/11 at 64, 0/11 at 128 and 320), zero wrong passes at any rung, mechanism **STARVATION** (β_N = +2.038 p = 0.0025 against β_r = +0.00018 p = 0.9998), and a transferable floor **N\* = 2048 coarse px** that turns every sensor pairing into arithmetic (D-066) |
| Viewpoint invariance | local model residuals **white**; no systematic relief signature | **NEVER TESTED** | **Literal form NOT MET and measured MIS-SPECIFIED (D-064); bound form MET to 20°.** *Residuals white* holds at e = 0 and nowhere else on both local arms, because a smooth residual fires a whiteness test at any amplitude — including **0.032 px**. The bound reading holds to **5°** (96-parameter piecewise affine) and **20°** (six parameters + the 59 m SLDEM the deliverable actually has), and a global model's dense median stays under 0.5 px to **30°** |
| Multi-modality (reflectance bands ↔ pan; thermal envelope stated) | reflectance: same envelope as pan; thermal: envelope stated | NOT MET | **MET, with its scope named in the same breath.** **7 of 9** Kaguya MI bands register and every succeeding band lands within **1.334×** of a pan comparator built from the same instrument's band mean (six of seven *better* than pan). **Thermal: Diviner at 28 : 1 gives 49 keypoints and 0 inliers — starvation**, which is an envelope stated with a bound. **It is NOT IIRS**, and the word appears in no claim sentence (D-062) |
| **Sub-pixel accuracy** "of the source image" | median **< 0.5 coarser-px on independent check points, with 95 % CI** | NOT MET — *no check points exist* | **MET.** A product from another mission (SELENE/Kaguya TC ortho, LISM control) gives an **A → reference → B** composition containing **no A ↔ B correspondence** that agrees with the recorded direct registration to **0.266 reference px = 2.24 m, CI95 0.222–0.413, 17 pairs**. **What it is not:** absolute accuracy in the SELENE frame — both legs share the reference, so its own error cancels; it is an upper bound on the **sum of two independent registration errors**. Manual check points remain the only route to a number with no shared instrument in it |
| Uniform distribution of match points | gap ≤ 0.15 of image diagonal | NOT MET + mis-specified | **NOT MET + mis-specified**, unchanged (D-057), and EXP-016 adds that occupancy falls to **0.484** at the scale envelope's rung |
| Registered product | emitted only for accepted pairs | MET | **MET, and now also for images the reader supplies** — the live card emits the registered product, the match points and the transform, and **withholds the registered image when the verdict is REJECTED** |
| Metrics incl. RMSE, inlier count, ratio | verdict never rests on a signal with AUC < 0.9 | MET | **MET** — fit RMSE measured at AUC 0.4947 and structurally excluded; unchanged |
| Generic software, all named formats | every named format loads with geometry | PARTIAL | **PARTIAL, wider than before.** PDS4 (NAC, OHRC) ✓, GeoTIFF (TMC-2 ortho and DTM) ✓, **PDS3 map-projected (Kaguya TC ortho, MI MAP V3, Diviner GDR) ✓ added this week**, LROC WAC ✓, Mini-RF ✓ — **IIRS cube ✗**, no reader and no data |

**4 MET, 3 PARTIAL, 2 NOT MET ≈ 55 %**, against ≈ 30 % on 2026-09-21. **Read
the MET column with its scope attached**, which is why every row carries it:
the accuracy row is a two-leg bound, not absolute accuracy; the multimodality
row is not IIRS; the viewpoint row is met in a reading the stage itself
records as a *re-reading* of the acceptance, with the literal form reported
NOT MET beside it. **No row was re-scoped to make it pass**, and the two rows
that fail — scale and coverage uniformity — fail with numbers rather than with
silence, which is the difference between this scorecard and the one three days
ago.

### (c) What is still, honestly, missing

1. **FA and FR** (§53 criterion 3) — needs a calibration/validation site split;
   unchanged and still the largest single hole in the verification story.
2. **A VERIFIED Chandrayaan-2 triangle** (§53 criterion 2) — 2.177 against 2.0.
   The nearest route is a NAC frame centred on the TMC-2 swath, which needs a
   fresh ODE census.
3. **Coverage calibration at real inlier counts** (§53 criterion 4) —
   answerable in neither direction until occupancy above 0.938 is sampled.
   *(Historical note, retained under integrity rule 3: EXP-022 sampled it on
   2026-09-23. Criterion 4 is answered NOT MET on three named low-count edges,
   and seven edges remain unsampled — D-069.)*
4. **IIRS** — no product exists to ingest. Data-refused, not untested, and the
   README says so.
5. **Manual check points** — the only accuracy number with no shared instrument
   in it.
6. **Terrain transfer** — every real result is Mare Serenitatis; the two
   highland candidates could not supply an anti-vacuous set (EXP-018 arm H).

---

## 1. Illumination separation — **MET**

REAL-DATA-07's amended run (E-037 corrected) on 42 confirmed-overlap pairs
across two independent ground windows, three engines:

- Pooled Δincidence separation **p = 0.0012**, with **both** windows below 0.05
  independently (RD-03 0.0043, RD-04 0.029). The criterion asks for ≥ 8 edges;
  this is 42 pairs.
- Replication S1 **MET**: E2 → A 2138 geometry-consistent inliers at
  Δinc 8.82°, E2 → B 4 at 48.63°.
- The frozen rule (`n_inliers <= 8`, D-023) was used unchanged throughout;
  **0 wrong passes in 76** successes across B1 / B4L / B4X.
- Rungs: ~2 m (RD-07), 3.6–30 m (EXP-007 tier 2), 100 m (RD-08 WAC). More than
  the two the criterion requires.

**This criterion is met on its own terms.** It is the project's strongest
result and it is honestly bounded: no ground truth, geometry-bound only, one
mare region.

---

## 2. Chandrayaan-2 — **NOT MET, and the reason is not technical**

Zero Chandrayaan-2 bytes are on disk. `data/raw/chandrayaan2/` does not exist.
REAL-DATA-09 is pre-registered and not started; the download is pending.

Everything measured to date is LRO NAC ↔ LRO NAC plus two open-archive proxies.
`STAGE_HISTORY.md` has carried *"NO Chandrayaan-2 data — no multi-modal claim
is supported"* since the first commit, and that sentence is still true.

**This is the single largest gap in the deliverable**, because the problem
statement is titled for Chandrayaan-2 optical products. The ingestion path is
built and tested ahead of the data (`docs/REAL-DATA-09_IMPLEMENTATION_PLAN.md`,
`siim.ingest.geotiff`), so the blocker is the download alone.

---

## 3. Verdict false-acceptance and false-rejection — **NOT EVALUABLE**

This criterion cannot be answered, and the reason is structural rather than an
oversight in any one run.

**There is no VERIFIED verdict anywhere in the repository.** Exactly six
artefacts carry a serialised verdict from `siim.demo.verdict.assess()`, and all
six are REJECTED (`REAL-DATA/registration_usable.json`, `…usableH2.json`,
`…terminator.json`, `REAL-DATA-03/registration_usable_geo.json`,
`REAL-DATA-03/loop_closure_triplet.json`,
`REAL-DATA-04/loop_closure_real_data_04.json`). A false-acceptance rate over
zero acceptances is undefined.

**Why no VERIFIED exists.** `assess()` returns VERIFIED only when loop closure
is present and under 2.0 px. The 42-pair RD-07 census and the RD-08 proxy grid
never form triplets, so no row in either can reach better than INCONCLUSIVE.
This is deliberate and already stated in `DEMO_TRACK.md`: *the verdict criteria
were not adjusted to turn the success case green.*

**What IS measured, and what it is not.** The figure the deliverable quotes is
a wrong-pass rate of the **inlier rule**, not of the **verdict** — a pass under
`n_inliers > 8` whose transform is INCONSISTENT with archive corner geometry:

| engine | passes | wrong | rate | operator |
|---|---|---|---|---|
| B1 | 46 | 0 | 0.00 % | box average |
| B4L | 49 | 1 | 2.04 % | box average |
| B4X | 27 | 0 | 0.00 % | box average |
| B4L | 13 | 5 | 38.5 % | PSF-aware re-run, reported separately |

These are bounds at the geometry check's own discrimination floor (~84–116 px
at native NAC scale, ~2.3–2.8 px at 100 m), on one mare region, with no ground
truth. **They are not probabilities and not verdict-level rates.**

> Both tallies were found wrong on 2026-09-20 and corrected — see **E-038**.
> The B4L denominator read 47 where the rows give 49, and the PSF re-run's two
> Mini-RF wrong passes were counted nowhere.
> `tests/test_wrong_pass_tally_matches_artefacts.py` now derives every figure
> from the row files, so the constant and the artefacts cannot drift apart again.

**False rejection is not measurable at all.** FR requires knowing which pairs
*should* have registered. No real pair has ground truth; confirmed overlap is
explicitly *not* a claim of equivalent difficulty (RD-07 is the measurement
that illumination, not overlap, decides registrability), so treating
failure-on-confirmed-overlap as false rejection would conflate the verdict's
error with the matcher's illumination envelope. The nearest measured figure is
EXP-002's `n_inliers <= 8` rule on 192 held-out **synthetic** cases: FPR
**0.0112**, recall 1.000 — the rule, on synthetic terrain, not the verdict.

**The adversarial clause cannot be checked either.** EXP-002 objective 4 builds
adversarial cases but records per-estimator detection/false-alarm rates with no
verdict on any case. The demo's `coherent_wrong` scenario is computed live, not
stored; its recorded outcome is REJECTED at 63.998 px loop error. Separately,
`verdict.py` documents a case that **is** returned VERIFIED / high while 64 px
wrong — when the error cancels in loop closure — pinned as an executable
assertion in `tests/test_demo_verdict.py`. That is the per-image gauge null
space (ADR-0011 N1), recorded as a known limitation rather than patched.

**What would close this: EXP-012 (verdict calibration),** designated at
`MASTER_RESEARCH_AND_ARCHITECTURE_PLAN.md:577` and never run. There is no
`experiments/EXP-012/` and no calibration/validation site split.

---


## UPDATE 2026-09-23 (last) — the third PS variation is measured, and the architecture lost its own ablation (EXP-016)

**What ran.** EXP-016 took 11 real NAC edges that register at the native rung
inside the measured illumination envelope, degraded both images through a
stated PSF to a common coarser GSD, and climbed
**2 : 4 : 8 : 16 : 32 : 64 : 128 : 320**. 488 cells, 3 h 15 m.
**S4 MET; S0, S1, S3, S5 NOT MET; S2 returns STARVATION.**

**§53 does not move — and for the third stage running, that is the point.**
No §53 criterion is about scale. The scorecard this stage moves is §2.2's, and
it moves the row that was the single largest untested requirement in the
project.

**§2.2's scale row: NOT MET / UNTESTED → NOT MET, with an envelope, a
mechanism and a floor.** The acceptance is *"every rung ≤ 320:1 registers when
overlap ≥ 50 % of the coarser tile"*. Measured: **11/11 at r = 4, 8, 16, 32;
8/11 at 64; 0/11 at 128 and 320**, so the acceptance is **NOT MET** and the
**envelope is 32 : 1**. Three things make that a defensible deliverable rather
than a bare failure:

1. **Every failure is the frozen inlier rule, never the geometry check.**
   55 CONSISTENT, 5 INCONCLUSIVE, **INCONSISTENT never**, and **zero wrong
   passes at any rung in either engine** — at rungs where the archive
   geometry's discrimination floor has tightened from ~250 native px to
   **~1.6 coarse px**, i.e. where a wrong pass would have been easy to catch.
2. **The mechanism is measured, not asserted.** §2.2's own question is
   *descriptor failure or sampling starvation?* A control that holds the coarse
   pixel count fixed while halving the ratio agrees with the full cell on
   **55 of 60**; the pooled logistic over 143 cells gives **β_N = +2.038
   (p = 0.0025)** against **β_r = +0.00018 (p = 0.9998)**. Verdict:
   **STARVATION**.
3. **The answer transfers as arithmetic.** **N\* = 2048 coarse pixels of
   overlap.** TMC-2 ↔ NAC clears it by 40–160×; OHRC-in-IIRS (≈ 5 550 px)
   clears it by 2.7×; one IIRS grid against a single 4096-line NAC tile
   (325–5 000 px) straddles it. **The 320 : 1 rung failed here on 570 pixels** —
   ten times fewer than the real OHRC-in-IIRS case — so the deliverable carries
   the floor and the arithmetic, and says which is which.

**What this stage takes away from the architecture.** D-005 called scale
normalisation *"a required first-class pipeline stage"* and deferred its
validation to EXP-004, which never ran — `PROJECT_GAP_ANALYSIS.md` C2 named
that as E-042's pattern by a second route. EXP-016 ran the ablation instead:
the **un-normalised** arm succeeds **10/10 at every rung run**, across GSD gaps
to **16 : 1**, exactly as the normalised arm does. **Zero discordant pairs**,
so the pre-registered McNemar cannot run and S3 is **NOT MET as a null by
construction** — a *tie*, not a loss, and the distinction is in the ledger
(D-005-N1, E-056). C2 is retired: the decision was settled by a stage that ran.

**Two harness clauses failed, and the stage is reported beside them.** S0's
chapeau says *nothing is reported from a cell unless every clause holds*.
(i) the *bit for bit* clause fails on 4 of 30 cells at k = 32 because one
implementation accumulates in float32 and the other in float64 — measured
afterwards at **3–5 × 10⁻⁸ relative** (E-055); (iv) the self-scale control
misses a known integer shift by more than 0.05 coarse px on **15 of 112**
cells, worst **0.591**. The consequence is carried to S4 rather than hidden:
on those pairs the reported 0.09–0.26 coarse px agreement is **inside the
harness's own floor** and is a bound, not a measurement.

**One thing to carry into any accuracy claim.** S4 is MET at 0.977, and its
agreement with the native-rung solution *improves* in coarse pixels
(0.258 → 0.094 from r = 4 to 32) while **worsening on the ground
(1.16 m → 2.93 m)**. Every quotation of a coarse-pixel figure in this project
must carry its metres.

---

## UPDATE 2026-09-23 (later still) — viewpoint has evidence for the first time, and one more §2.2 acceptance is measured mis-specified (EXP-017)

**What ran.** EXP-017 constructed an oblique view from a real 10 m TMC-2 DTM
co-registered with a real 5 m ortho and swept emission angle 0–30° over 31
windows, with exact ground truth by construction. **S2, S4 MET (S1b MET); S0,
S1a, S3, S5 NOT MET.**

**§53 does not move.** No criterion here touches the five. That is stated
rather than implied, because this audit's own lesson — the section *"A second
scorecard this audit never kept"* — is that a stage can be excellent and move
this scorecard by zero. The scorecard it moves is §2.2's.

**§2.2's viewpoint row: NEVER TESTED → measured, with its acceptance split in
two.**

- The row's acceptance is *"local model residuals white; no systematic relief
  signature"*. Operationalised exactly as pre-registered, it holds at **e = 0
  and nowhere else** on both local arms. **D-064** records that the literal form
  is **mis-specified** for this instrument class on this terrain — a smooth
  residual fires a whiteness test at any amplitude, including 0.032 px — and
  that the **bound** form is what a deliverable may claim: **5°** for a
  96-parameter piecewise affine, **20°** for six parameters plus the 59 m
  SLDEM, and a global model's dense median under 0.5 px to **30°**.
- This is the **second** acceptance measured mis-specified as written (after
  §53 criterion 4, D-057), and the pattern is worth naming: *an acceptance
  phrased as a property of the residual's **shape** (white, uniform) is not the
  same requirement as one phrased as a bound on its **size**, and on real data
  the two diverge by an order of magnitude in what they admit.*

**What the row may now say.** Viewpoint invariance is **measured on real
relief**, in a construction that carries no occlusion, no view-dependent
radiometry and no sensor model — so every number is an upper bound on
precision, and a real TMC-2 fore/aft pair remains the acquisition that would
test the matcher rather than the model class.

**A blind spot this audit should carry.** On all 130 arm-A cells the verdict
returns INCONCLUSIVE and **never REJECTED**, including at 30° where the dense
p99 error is 1.535 px. Criterion 3's false-rejection clause is unmeasurable for
the usual reason; this is the complementary observation on the acceptance side,
recorded beside the verdict rather than patched into it.

---

## UPDATE 2026-09-23 (later) — the multimodality axis is answered, and §53 does not move (EXP-020)

**What ran.** EXP-020 put nine Kaguya MI reflectance bands (414–1548 nm, 14.8 m)
and a Diviner bolometric-temperature map (236.9 m) against panchromatic
references over the same mare window, plus the Chandrayaan-2 TMC-2 block and a
null block. **S0, S6 MET; S2 MET as Part 1 froze it (E-053); S1, S3, S4, S5 NOT
MET.**

**§53 is unchanged by this stage, and that is the point.** Criterion 2 still
needs a VERIFIED Chandrayaan-2 verdict per sensor; criterion 3 still has no
measurable FA/FR; criterion 4 is still mis-specified (D-057). **A stage can be
worth running and move this scorecard by zero** — which is exactly the failure
mode `PROJECT_GAP_ANALYSIS.md` §4 recorded for EXP-013/014/015, and it is not one
here **because the scorecard this stage moves is §2.2**, which is now tracked
beside §53.

**§2.2's multimodality row: NOT MET → answered, in the scope D-062 fixes.**
- *reflectance bands: same envelope as pan* — **MET**: 7 of 9 bands register
  under the frozen rule and every succeeding band is within **1.334×** of a pan
  comparator built from the same instrument's own band mean.
- *thermal: envelope stated* — **stated**: at **28 : 1**, 49 keypoints and 0
  inliers, failure mode **starvation**, named in advance.
- **What is still NOT MET:** the row names **IIRS**, and no IIRS product exists
  (RL-046). The evidence is a substitute instrument, and D-062 fixes the
  sentence the deliverable may use.

**A number every other row in this audit now inherits.** MI MAP V3 and TC Ortho
Seamless V2 — two products of one mission, one map frame, one control network —
are offset from each other by **83–91 m** (D-063), measured with 1360–2024
inliers and a linear part matching the labels to 3e-5. EXP-019's 137.6 m
archive-vs-Kaguya disagreement and this 85 m inter-product term are the two
floors under every "corroborated" sentence here.

---

## UPDATE 2026-09-23 — the reference changed, and two criteria move (EXP-019)

**What ran.** EXP-019 registered 20 REAL-DATA-07 NAC tiles and the
Chandrayaan-2 TMC-2 block to the **SELENE (Kaguya) TC Ortho Map Seamless V2**
tile over the same ground — a product from another agency, spacecraft, sensor,
decade and control network — and against a **null block of the same product**
25 km away. S0, S1, S2, S3, S4, S6 MET; S5 NOT MET.

**Criterion 2 — still NOT MET, and the reason is now one clause, not three.**
The three named counts were: no VERIFIED Chandrayaan-2 verdict, one sensor not
three, no check points.

- **Check points: the clause is now answered in the sense §2.2 defines it.** An
  A → reference → B composition, built from **no A ↔ B correspondence**, agrees
  with the recorded direct registration to **0.266 reference px = 2.24 m**,
  bootstrap CI95 **[0.222, 0.413] reference px**, over 17 pairs — against the
  requirement *median < 0.5 coarser-px on independent check points, with 95 %
  CI*. The independence is of the **instrument chain**, not of a human
  annotator, and both legs share the reference, so the number bounds the sum of
  two independent registration errors and is **not** absolute accuracy. Stated
  that way, the clause is **MET**; stated as "human-annotated check points", it
  is not, and that reading is recorded here so nobody has to discover it.
- **A VERIFIED Chandrayaan-2 verdict: still not reached.** The new triangle
  {TMC-2 → NAC recorded, NAC → reference, reference → TMC-2} closes at **2.177
  reference px = 18.33 m** against the frozen **2.0 reference px** line — an
  8.9 % miss, on the leg with 9 inliers. The line was not moved. Note what a
  pass would have meant: 2.0 *reference* px is 16.85 m where EXP-012's 2.0 px
  is ≈ 2 m.
- **One sensor, not three: unchanged.** TMC-2 only; OHRC is over the South Pole
  and no IIRS was delivered.

**Criterion 3 — the blind spot's attribution changes.** EXP-013 could not say
whether its per-frame terms (25.70–109.43 px) were archive-reference error or a
real shared per-frame error in the estimates; `siim.verify.gauge`'s docstring
records that as undecidable by that instrument. Measured against a reference
EXP-013 never saw, the terms track the archive-vs-controlled offsets at
**r = 0.751** (Spearman 0.738, permutation **p = 0.026** against a null p95 of
0.694) on 8 frames, and **r = 0.746 at p = 0.001** pooled over 11. So the
36-of-36 gauge blind spot is **not evidenced on these real frames** (D-061),
and D-054's detector has a deployment path — against this reference, in a stage
of its own. **FA and FR are still unmeasurable**, so criterion 3 stays
**PARTLY ANSWERED**.

**What the audit gains permanently.** The corroboration floor quoted in every
earlier row — "~100 px" — is now a measurement: **137.6 m median, CI95
108.5–160.3 m, +101 ± 74 m east**, on 12 frames, against an independently
controlled product (D-060). Rows that say *corroborated, not verified* keep
their wording; the number behind the word is no longer an estimate.

---

## UPDATE 2026-09-22 — criterion 3 measured out of sample for the first time (EXP-018)

**Criterion 3 stays NOT EVALUABLE for FA and FR, and that is now a measured
statement rather than an untested one.** EXP-018 opened one held-out window
once and reports, on data no stage had touched:

- **Wrong passes: 0 in 41 out-of-sample passes** — B1 0/12, B4L 0/12,
  B4X 0/17, every pass CONSISTENT with archive corner geometry. In-sample the
  counts were 0/46, 1/49, 0/27.
- **This is still not an FA rate.** It is a bound at the geometry check's own
  ~250 px discrimination floor: a wrong pass means a transform wrong by
  *more than about 250 px*, and nothing here sees an error below that. EXP-018
  Part 2 does not call it an FA rate and neither does this audit.
- **FR is not measured at all.** A REJECTED pair that was in fact registrable
  is indistinguishable from one that was not, without ground truth. There is
  none.
- **The adversarial clause is unchanged** and still MET for the wrong reason
  (E-039).

**What did change.** The clause *"on validation sites"* now has validation
sites. Two of the project's advertised numbers **failed** there — the
illumination envelope's 40° edge (**D-059**) and the 3 px engine-agreement
floor (**D-051-N1**) — and two of the load-bearing ones held: zero wrong
passes, and **7 of 7 triplets VERIFIED at 0.4001–1.1120 px**, the first
VERIFIED verdicts produced on ground this project had never opened.

**FA and FR remain unmeasurable.** Closing them needs ground truth, which is
item A3 (geodetic check points) and is not on disk.

## UPDATE 2026-09-21 (later) — EXP-013 ran; the blind spot is measured and NOT closed

`docs/stages/EXP-013_gauge_detection.md`, artefact
`experiments/EXP-013/exp013_results.json`.

The update above says criterion 3's adversarial clause is MET "for the wrong
reason", and that the verdict's real blind spot — a **per-image gauge** — had
been quantified with **no instrument against it**. EXP-013 built the
instrument. **Four of its six criteria are NOT MET, and the blind spot is
still open.**

**What was measured.** The check has to be external, because anything computed
from the edge estimates lives inside the same gauge. The only external
reference this project holds is archive corner geometry — and EXP-013 measured
that it carries a **per-frame disagreement of its own of 66–109 px**,
calibrated at **66.00 px** before any detection statistic was read. That is
larger than the gauge errors worth catching. At an applied gauge of **zero**
the fit still returns **55.55 px** and alarms on **6 of 12** cases (S6 NOT
MET), so there is no operating point; S1 reaches 10 of 12 at 32 px, and S2
alarms on **13 of 13** real triplets.

**The mechanism is sound, which is what makes the negative bounded rather than
inconclusive.** On the REAL-DATA-07 census graph — redundancy 4–7 instead of a
triplet's 1 — the per-node model explains **0.845–0.857** of the disagreement
against a structureless null whose **maximum over 40 draws** is **0.421–0.590**,
in all six window × engine graphs. And **RootSIFT, DISK + LightGlue and XFeat
recover the same per-frame term to within 1.50 px** on terms of 92–109 px, so
the term belongs to no matcher.

**What it did not settle, as Part 1 predicted it could not.** The instrument
localises a disagreement to an image; it cannot say whether the archive
reference or a shared per-frame tile georeferencing carries it. The second
reading would mean the instrument has found **a real instance of the very
defect it was built to detect**, in this project's own data. Separating them
needs an absolute reference finer than the disagreement — LROC NAC regional
controlled mosaics, published average offset below 13 m (~7–26 px at NAC
resolution), which this README has recorded as available and unused since
amendment S9.

**D-054: the check is built and not deployed.** No constant was retuned,
`assess()` is untouched, and a test parses its imports to keep it that way. The
deliverable's honest sentence is *"we built the detector and measured that the
reference available to it is too coarse to run it"* — not *"we detect gauge
error."*

**E-041** records why four criteria were unanswerable as posed: every triplet
is a 3-edge cycle, so the per-node model has **8 free parameters against 3
edges**, and a structureless disagreement of the same magnitude already scores
**0.834 at its 95th percentile** there against real values whose median is
**0.837**. S2's 13 of 13 is therefore uninformative in **either** direction.
Part 1 froze *which rows* were in the population without stating *what the
population had to satisfy for its own statistic to be falsifiable* —
E-035's and E-039's defect at two further levels.

**Criterion 3 is unchanged by this stage.** Its first two clauses — a
verdict-level false-acceptance rate and any false-rejection rate — remain
unmeasurable for the reasons below. EXP-013 adds an instrument and a measured
limit on it, not ground truth.

---

## UPDATE 2026-09-21 — criterion 4 has a recorded decision (D-053)

The 2026-09-20 update found criterion 4 **NOT MET**: 14 of 39 VERIFIED edges
have coverage gap above 0.15. **That verdict stands and is not re-scoped.**

What D-053 adds is that **the 0.15 line itself has never been measured**, so
"NOT MET" carries less information than it appears to. `verdict.py` cites a
measurement for each of its other two constants — `INLIER_CUTOFF = 8` from
EXP-002 (recall 1.000, FPR 0.0112 on 192 held-out cases) and
`LOOP_ERROR_REJECT_PX = 2.0` from EXP-003 (correct loops 0.258 px median
against wrong loops 1368 px) — while `COVERAGE_GAP_WARN = 0.15` cites only
ADR-0006, which is a *rationale for the metric* and not a calibration of the
number. The 0.15 first appears in
`MASTER_RESEARCH_AND_ARCHITECTURE_PLAN.md:46` as a design-table target and is
promoted to a §53 success criterion at line 725 without ever being measured.

**D-006 / ADR-0006 has been `PROPOSED` since 2026-08-24**, and its own
acceptance rule reads: *"Accept if EXP-007 shows it correlates with local
held-out error better than the alternatives. Reverse if it does not."*
**EXP-007 ran and never performed that test** — its stage report does not
mention coverage once. It went unnoticed for six weeks because until EXP-012
produced the first VERIFIED verdict the criterion ranged over an empty set.

Withdrawing criterion 4 as unvalidated was considered and **refused**: it would
replace a recorded failure with silence, and the failure is the more useful
statement. **Nothing in the verdict changed** — the 14 affected edges were
returned `moderate` rather than `high` and stay `moderate`.

The acceptance test is now an explicit debt rather than an assumption
discharged by silence. It needs what EXP-007 was supposed to supply: **local**
held-out error as a function of distance to the nearest correspondence.
EXP-010 and EXP-011 built exactly that machinery, so it is a scoring pass over
recorded tiles, not new data.

---

## UPDATE 2026-09-21 — criterion 3's adversarial clause is now answered

EXP-012's S3 arm ran (`exp012_s3_adversarial.json`). **The third clause of
criterion 3 — *zero VERIFIED on the adversarial set* — is MET: 0 of 36.**

**It should not be read as a clean pass, and E-039 records why.** Every
adversarial construction in EXP-002 objective 4 is a **per-edge** error, which
is precisely the subspace loop closure exists to detect; it detected all 36.
The blind spot the verdict actually has is **per-image** gauge error, and the
set contains no case of that shape — so the criterion could not have failed for
the reason its own HIGH-confidence prediction named.

A supplementary probe (`exp012_s3_gauge_probe.json`, deliberately **not** folded
into S3) builds that missing case: **36 of 36 return VERIFIED / high while every
edge is wrong**, by a median of 14.04, 57.47 and 115.40 px at gauge magnitudes
8, 32 and 64 px, with the loop closing to 1.27e-13 px by construction.

**The first two clauses of criterion 3 are still unanswered.** A verdict-level
false-acceptance rate and any false-rejection rate remain unmeasurable for the
reasons below: no ground truth, and no calibration/validation site split.
EXP-012 did not change that.

---

## UPDATE 2026-09-20 (later) — REAL-DATA-09 ran on real Chandrayaan-2 data

The PRADAN products arrived: TMC-2 ortho / DTM / calibrated image (equatorial,
covering the recorded NAC ground) and two OHRC observations (**South Pole**,
the Chandrayaan-3 region). No IIRS.

**Criterion 2 is no longer blocked on data, and is still NOT MET.** TMC-2
*registers* to LRO NAC at 5 m — 6 passes across two engines, all
geometry-CONSISTENT, 0 wrong passes, engines agreeing to 0.619 px and 2.570 px
— but a registration is not a VERIFIED verdict. The single pairs return
INCONCLUSIVE (no loop available; coverage gap above 0.15), and the one loop
that exists, {TMC-2, NAC A, NAC D}, closes to **2.2131 px = 10.5 m** against
the frozen 2.0 px reject line, so `assess()` returns **REJECTED**. The
threshold was not moved to change that. The criterion also asks for *per
sensor* and for *check-point error and CI*: only TMC-2 has usable data, and no
check points exist.

So criterion 2 now fails on three named counts — no VERIFIED verdict, one
sensor not three, no check points — rather than on absence of data. That is a
much more useful statement of where the project stands.

---

## UPDATE 2026-09-20 — EXP-012 ran, and two rows above changed

`EXP-012` (verdict calibration) composed the 13 real triplets whose three edges
each register, and ran the **unmodified** `assess()` on them. Its controls both
held: REAL-DATA-03's recorded 1201.0378963072235 px loop was reproduced to
**0.0 px**, and all **22 re-matched edges reproduced their recorded inlier
counts exactly** (9 through 5437).

**Criterion 4 is now measurable, and is NOT MET.** 39 VERIFIED edge verdicts
exist; their coverage gaps run **0.038 – 0.406**, and **14 of 39 exceed 0.15**.
Those 14 are precisely the verdicts returned at `moderate` rather than `high` —
coverage counted against them as designed, and VERIFIED was still reached
because loop closure agreed. §53's criterion and the verdict's coverage
handling are in conflict; EXP-012 Part 2 reports that rather than retuning
either.

**Criterion 3 is still not evaluable, and EXP-012 does not fix it.** A
verdict-level false-acceptance rate over these 39 is **0 / 39 against archive
geometry — but by construction, not by measurement**: triplet admissibility
required `success == true`, which excludes wrong passes by definition. A set
that cannot contain a false acceptance cannot estimate their rate. FR still has
no ground truth, and the adversarial arm (S3) was specified in EXP-012 Part 1
§3.6 and **not run**.

The section below is superseded by this update and kept as written.

---

## 4. Coverage gap on VERIFIED pairs — **vacuously true** *(superseded above)*

Zero VERIFIED pairs exist (§3), so "every VERIFIED pair has coverage gap
≤ 0.15" holds over an empty set and carries no evidence.

For context, the six recorded REJECTED verdicts have `metrics.coverage_max_gap`
between **0.427 and 0.618**, all well above the 0.15 warning threshold. Among
the 76 passing rows of the amended RD-07 run, **43 (57 %) exceed 0.15**, and
**all 21** RD-08 passes do. Had those rows been run through `assess()`, coverage
would have counted against them.

This is worth stating plainly in the deliverable rather than leaving implicit:
the coverage bound is implemented and enforced, but the criterion as phrased has
never been exercised.

---

## 5. Fresh-clone install, CPU-only, all tests pass, no non-commercial weights — **MET**

Measured today, not asserted:

- **Fresh clone.** Cloned to a clean directory at `ae29a2b`; 384 tracked files.
  Suite run against the clone alone: **787 passed, 4 skipped**, exit 0, 2:28.
- **The two extra skips are honest and self-documenting.** Locally the suite is
  789 passed / 2 skipped. The two additional skips are the RD-03 and RD-04
  re-derivation tests, which skip because the 166 MB NAC tiles are gitignored.
  The skip message names the missing file and says: *"Re-fetch with the byte
  ranges in `data/manifests/` and this test becomes live."* The test reports
  **CANNOT CHECK**, explicitly not "checked and fine" — the correct behaviour.
- **CPU-only.** `torch==2.10.0+cpu` recorded in `requirements-frozen.txt`; no
  CUDA path is used anywhere.
- **No non-commercial weights.** S14 verifies DISK and LightGlue as Apache-2.0
  (`depth-save.pth`, `disk_lightglue_v0-1_arxiv-pth`, loaded via kornia, nothing
  vendored) and XFeat as Apache-2.0 from a pinned commit. SuperGlue and the
  original SuperPoint are **excluded by licence** under ADR-0008, and the engine
  registry refuses them rather than silently substituting.

---

## A second scorecard this audit never kept — added 2026-09-21

This document has measured **§53's five criteria** every session since it was
written. §53 is *the project's own bar*. It is not ISRO's.

`MASTER_RESEARCH_AND_ARCHITECTURE_PLAN.md` **§2.2** decomposes the problem
statement into nine requirements with their own acceptance criteria, and
**nothing has ever scored them.** Measured for the first time in
[`PROJECT_GAP_ANALYSIS.md`](PROJECT_GAP_ANALYSIS.md), the result is **2 MET,
2 partial, 5 not met ≈ 30 %** — against 40 % on §53 — and it exposes two
problem-statement axes with **no evidence of any kind**:

- **Viewpoint variation.** One of the three variations the PS names. EXP-008
  does not exist; every real frame is near-nadir (emission ≤ 1.75°).
- **Scale to 320:1.** Named explicitly in the PS. Best real evidence ≈ 65:1;
  the synthetic probe stops at 32:1 and measures the *unmodified* baseline
  rather than the architecture's degrade-to-common-GSD answer.

Both were invisible here because this audit tracked the wrong scorecard.
**§2.2 is scored in the gap analysis from now on, beside §53.**

---

## What this audit says to do next — rewritten 2026-09-21

*(The 2026-09-20 list is kept below under integrity rule 3. **All four of its
items are now done** — the Chandrayaan-2 data arrived and REAL-DATA-09 ran,
EXP-012 produced the first VERIFIED verdicts, the blind spot behind them is
stated plainly in the README, and EXP-006 ran on 2026-09-21.)*

**What closed since this list was first written, and what it cost.** Three
stages ran on 2026-09-21 and two of them returned **negatives**:

- **EXP-013** built the detector for the verdict's known blind spot and
  measured that the reference available to it is too coarse to run it — a
  bounded negative (D-054), and the reason item 1 below is now top of the list.
- **EXP-014** ran ADR-0006's six-week-overdue acceptance test and **refuted
  it**: the primary coverage metric is the worst of four, and its threshold is
  4× too tight (D-055, E-042).
- **EXP-006** is the one that landed positive, and it replaced the
  architecture's founding citation with a measurement (D-056).

Ranked by what a reviewer would notice first:

1. **A geodetically controlled reference per frame.** This is now the single
   highest-value unblocked item, and it closes two separate gaps at once.
   `README.md` amendment S9 already records that LROC NAC regional controlled
   mosaics carry a published average positional offset **below 13 m** — about
   **7–26 px** at NAC resolution — against the **~100 px** archive-geometry
   floor everything real is currently corroborated against. With it:
   **(a)** the accuracy claim stops being "corroborated to ~100 px" and becomes
   a measured number, which is the weakest link in criterion 1's otherwise
   strong result; **(b)** EXP-013's S6 becomes testable and the gauge check
   gains an operating point (D-054); and **(c)** the two readings EXP-013 §8
   could not separate — archive-reference error versus a shared per-frame
   georeferencing error in the tiles — separate, and the second would be a
   **real instance of the verdict's blind spot in this project's own data**.
   It needs no new mission data and no permission.

2. **A VERIFIED Chandrayaan-2 verdict (criterion 2).** The only criterion
   failing on something other than instrument limits. TMC-2 registers to NAC at
   5 m with 0 wrong passes, and the one available loop misses the frozen 2.0 px
   line by **10 %** (2.2131 px). REAL-DATA-09 names the route: a NAC
   acquisition centred on the TMC-2 swath at lon ≈ 22.42 would raise overlap
   from 26–44 % toward full. **It was investigated on 2026-09-20 and not
   pursued** — none of the 22 known census frames can centre a full tile east of
   lon ≈ 22.10, and those reaching 22.10 carry Δinc ≥ 20° against the
   2.5° / 9.2° of the frames actually used — so it needs a fresh ODE census for
   an uncertain gain. High value, genuinely uncertain.

3. **ADR-0006's acceptance test, which D-053 turned from an assumption into a
   debt.** D-006 has been `PROPOSED` since 2026-08-24 and its acceptance rule
   names EXP-007; EXP-007 ran and never performed it, and nobody noticed for six
   weeks because the criterion ranged over an empty set until EXP-012. It needs
   **local** held-out error against distance to the nearest correspondence —
   machinery EXP-010 and EXP-011 already built — so it is a scoring pass over
   recorded tiles, not new data. Until it runs, criterion 4 is a failure
   against an uncalibrated line, which is a weaker statement than it looks.

4. **~~EXP-006~~ — DONE 2026-09-21, and it replaced a citation with a
   measurement.** Reframed as §553 directs, it found that one protocol step
   changes **2.18×** as many outcomes as replacing the entire matcher (mean 6.0
   vs 2.75; p = **0.0156** against no significant matcher contrast), with **all
   12 of its flips improvements** against the matcher axis's 6 gains / 5
   losses, and all 12 landing on pairs the mechanism predicts (P = 2.96e-07).
   **D-056** records the bounded claim. What is *not* closed is the general
   thesis: the step used was the one whose both levels happened to be recorded.
   **The successor item is RL-051b** — ablate a component *designed* as an
   ablation (scale normalisation: both levels implementable, neither recorded),
   which is the only route from "at least one step" toward the general claim.

**A note on what the last three stages have in common.** E-035, E-039 and E-041
are the same defect at ascending levels — an *arm* that could not produce the
outcome it was written to detect, a *criterion* frozen against a set lacking the
property it needed, and a *population and control* frozen without asking what
would make their statistic falsifiable. Each was caught by a control the stage
itself had frozen, which is the process working; but the interval between
occurrences is not lengthening. **The concrete change this implies for every
future Part 1:** state the parameter count against the constraint count for any
criterion resting on a goodness-of-fit, and build the null from the *property*
being tested, never from a permutation or a source assumed to carry it.

**None of the above is fixed by lowering a bar.** Criteria 3 and 4 are
unevaluable because the verdict was built strictly; that strictness is the
contribution, and the honest move is to measure it properly, not to relax it
until something passes. EXP-013 is the clearest case: four of six criteria
failed, no constant was retuned, and the result is a bounded negative with a
named next step rather than a softened pass.

---

## What this audit said to do next — 2026-09-20, kept as written

*(Integrity rule 3. Items 1–3 were done on 2026-09-20/21: the Chandrayaan-2
data arrived and REAL-DATA-09 ran; EXP-012 ran and produced the first VERIFIED
verdicts; and the "no VERIFIED pair exists" statement is superseded by that
result, with the blind spot behind it now stated plainly in the README.)*

**Ranked by what a reviewer would notice first:**

1. **Get the Chandrayaan-2 data.** Criterion 2 is the only one failing for lack
   of input rather than lack of work, and it is the criterion the problem
   statement is named after.
2. **Run EXP-012, or stop quoting a false-acceptance rate as if it were the
   verdict's.** Today the honest sentence is *"the inlier rule produced 1 wrong
   pass in 49 against a geometry bound"* — not *"the verdict's false-acceptance
   rate is 2 %."* The deliverable must not blur those two.
3. **Say plainly that no VERIFIED pair exists yet**, and why (loop closure is
   required and the census never formed triplets). A reviewer who discovers this
   unaided will discount everything else; a team that states it up front is
   demonstrating the exact discipline the project is selling.
4. **EXP-006 remains unregistered.** The thesis that the protocol matters more
   than the matcher is still carried on one SAR-optical preprint. The data to
   test it is already on disk (42 confirmed pairs, three engines, every protocol
   knob but tiling). The master plan directs it be reframed as a component
   ablation rather than run as a standalone thesis.

**None of the above is fixed by lowering a bar.** Criteria 3 and 4 are
unevaluable because the verdict was built strictly; that strictness is the
contribution, and the honest move is to measure it properly, not to relax it
until something passes.
