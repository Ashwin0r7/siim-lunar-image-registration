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
| 2 | ≥ 1 VERIFIED Chandrayaan-2 pair per sensor against NAC, with check-point error and CI reported in coarse pixels | **NOT MET** — but no longer blocked on data (see the 2026-09-20 REAL-DATA-09 update) |
| 3 | Verdict FA ≤ 5 %, FR ≤ 20 % on validation sites; zero VERIFIED on the adversarial set | **PARTLY ANSWERED** — the adversarial clause is MET (0 of 36), but for the wrong reason (E-039); FA and FR remain unmeasurable. **EXP-013 built the instrument for the blind spot E-039 exposed and measured that it cannot be deployed with the reference on hand (D-054); the blind spot is open** |
| 4 | Coverage gap ≤ 0.15 on every VERIFIED pair | **NOT MET** — 14 of 39 VERIFIED edges exceed 0.15. **D-053: the verdict stands and is not re-scoped — and the 0.15 line itself was never calibrated** (ADR-0006 is still `PROPOSED`; the acceptance test it assigned to EXP-007 was never run) |
| 5 | Fresh-clone install, CPU-only, all tests pass, no non-commercial weights | **MET (measured today)** |

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

## What this audit says to do next — rewritten 2026-09-21

*(The 2026-09-20 list is kept below under integrity rule 3. Items 1, 2 and 3 of
it have since been done; item 4 has not.)*

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

4. **EXP-006 remains unregistered.** Unchanged from 2026-09-20 and now the
   oldest open item in the project. The thesis that *the protocol matters more
   than the matcher* — the claim the whole architecture is organised around —
   is still carried on one SAR-optical preprint. The data to test it is on disk
   (42 confirmed pairs, three engines, every protocol knob but tiling) and it
   runs fully offline. The master plan (§553) directs it be reframed as a
   component ablation of GAPC rather than run as a standalone thesis.

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
