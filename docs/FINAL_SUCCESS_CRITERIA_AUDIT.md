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
| 3 | Verdict FA ≤ 5 %, FR ≤ 20 % on validation sites; zero VERIFIED on the adversarial set | **STILL NOT EVALUABLE** (see the 2026-09-20 update) |
| 4 | Coverage gap ≤ 0.15 on every VERIFIED pair | **NOT MET** — 14 of 39 VERIFIED edges exceed 0.15 |
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

## What this audit says to do next

Ranked by what a reviewer would notice first:

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
