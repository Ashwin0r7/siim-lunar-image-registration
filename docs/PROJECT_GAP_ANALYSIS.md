# Project gap analysis — how complete is this, really, and is the path right?

**Written 2026-09-21, after EXP-015.** This document measures the project
against **three different definitions of "done"** and reports all three,
because a single completion number would be misleading in either direction.

It is deliberately unkind. Every other document here reports what was
measured; this one reports **what was never attempted**.

---

## 1. Completion, three ways

### (a) Against §53's five final success criteria — **40 %**

| # | criterion | verdict |
|---|---|---|
| 1 | Illumination separation, ≥ 2 rungs, p ≤ 0.05 | **MET** |
| 2 | ≥ 1 VERIFIED Chandrayaan-2 pair per sensor + check-point error/CI | **NOT MET** |
| 3 | Verdict FA ≤ 5 %, FR ≤ 20 %, zero VERIFIED adversarial | **PARTLY** (1 clause of 3) |
| 4 | Coverage gap ≤ 0.15 on every VERIFIED pair | **NOT MET + mis-specified** (D-057) |
| 5 | Fresh clone, CPU-only, tests pass, licences | **MET** |

**2 of 5 = 40 %.** Generous reading with criterion 3's adversarial clause: 50 %.

### (b) Against the problem statement's own requirement decomposition (§2.2) — **≈ 30 %**

This is the scorecard that matters to a judge, and it is the harshest.

| PS requirement | acceptance criterion (§2.2, as written) | status |
|---|---|---|
| Correspondence under Sun-angle change | envelope **≥ 40° Δinc** at TMC/IIRS rungs; boundary stated at OHRC/NAC | **NOT MET** — TMC-2 rung passes to 9.2°, fails from 24.7°. Boundary *is* stated |
| Scale invariance **2:1 to 320:1** | every rung ≤ 320:1 registers at ≥ 50 % overlap | **NOT MET / UNTESTED** — best real evidence ≈ 65:1 (RD-08 proxy); synthetic probe stops at 32:1 and tests the *unmodified* baseline, not the architecture's answer |
| Viewpoint invariance | local model residuals white; no systematic relief signature | **NEVER TESTED** — EXP-008 does not exist; every real frame is near-nadir (emission ≤ 1.75°) |
| Multi-modality (OHRC/TMC ↔ IIRS bands) | reflectance bands: same envelope as pan; thermal: envelope stated | **NOT MET** — no IIRS delivered; EXP-009 never ran; the only modality evidence is RD-08's radar **negative** |
| **Sub-pixel accuracy** "of the source image" | median **< 0.5 coarser-px on independent check points, with 95 % CI** | **NOT MET** — **no check points exist.** 0.003 px is a self-warp *precision* upper bound, not accuracy |
| Uniform distribution of match points | gap ≤ 0.15 of image diagonal | **NOT MET**, and the criterion is measured mis-specified (D-057) |
| Registered product | emitted only for accepted pairs | **MET** — exists for the D→A edge, with provenance |
| Metrics incl. RMSE, inlier count, ratio | verdict never rests on a signal with AUC < 0.9 | **MET** — fit RMSE measured at AUC 0.4947 and structurally excluded |
| Generic software, all named formats | every named format loads with geometry | **PARTIAL** — PDS4 (NAC, OHRC) ✓, GeoTIFF (TMC-2) ✓, **IIRS cube ✗** (no reader, no data) |

**2 MET, 2 partial, 5 not met ≈ 28–33 %.**

### (c) Against the §51 implementation roadmap, effort-weighted — **≈ 75 % of 65 pd**

| phase | pd | spent | note |
|---|---|---|---|
| 0 Research reset | 2 | **2** | done |
| 1 Data foundation | 8 | ~7 | IIRS reader never built |
| 2 Baselines | 5 | ~2 | 2 engines of 5 (no ALIKED, RoMa, RIFT2); **EXP-008 raw arm never ran** |
| 3 Scientific experiments | 10 | ~8 | **EXP-005 never ran** |
| 4 Breakthrough component | 10 | **10** | **its own kill criterion fired** — H0 refuted at every rung (D-052). Effort spent; result is a negative |
| 5 Verification | 5 | ~2.5 | EXP-012 ran; calibration/validation site split never created; FA/FR unmeasurable |
| 6 Real Chandrayaan-2 | 8 | ~4 | TMC-2 only; **EXP-009 never ran** |
| 7 Ablation | 3 | **3** | EXP-006, done 2026-09-21 |
| 8 **Blind validation** | 2 | **2** | **DONE 2026-09-22 — EXP-018.** Freeze, run, report, once |
| 9 Hardening | 4 | **4** | done |
| 10 Demo | 3 | ~2 | **the 320:1 beat was planned and never built** |
| 11 Final benchmark | 2 | ~1.5 | p = 0.0012 ✓; aggregate tables partial |
| 12 Documentation | 3 | **3** | done, extensively |

**≈ 49 / 65 pd ≈ 75 % of planned effort expended.**

### (d) As a software deliverable — **≈ 95 %**

Installable from a fresh clone, **965 tests passing**, CPU-only, licence-clean,
runs fully offline, every advertised number traceable to an artefact the demo
links, 21 stages documented with frozen pre-registrations and two ledgers.

### The number that matters

> **The engineering is ~95 % done. The science the problem statement asks for
> is ~30 % done.**

That gap *is* the finding of this document, and §5 is about how it happened.

---

## 2. Pending work — everything not done, by PS relevance

### Tier A — named in the problem statement, not tested at all

| # | item | why it matters | cost | blocked? |
|---|---|---|---|---|
| A1 | **Scale ladder to 320:1 on real lunar texture** | The PS names "2:1 to 320:1" explicitly. Best real evidence is ~65:1. `degrade_to_gsd` exists and 32 NAC tiles are on disk — **this is runnable now** | 0.5 day | **no** |
| A2 | **Viewpoint variation (EXP-008)** | One of the three PS-named variations. Zero evidence. Every real frame is near-nadir | 1 day synthetic / 2 days real | real version needs TMC-2 fore+aft from PRADAN (**not on disk** — only the nadir band was delivered) |
| A3 | **Sub-pixel accuracy on independent check points** | The PS's headline phrase. §2.2's acceptance *requires* check points; none exist | 1 day + download | needs a geodetic reference (LROC controlled mosaic, offset < 13 m) |
| A4 | **IIRS ingestion + EXP-009** | "Multi-modal" is in the PS title and has zero supporting evidence | 2 days | **yes** — no IIRS product was delivered by PRADAN |

### Tier B — closes a §53 criterion

| # | item | why | cost | blocked? |
|---|---|---|---|---|
| ~~B1~~ | ~~**Blind validation (roadmap phase 8)**~~ | **DONE 2026-09-22 — EXP-018.** One held-out window (Mare Tranquillitatis, 20 CONFIRMED pairs, 0 grep hits in 518 files) opened once against ten frozen predictions. **Eight held, two failed:** the envelope's 40° edge is refuted (passes at 44.19° and 57.43°, D-059) and D-051's agreement floor is reversed by its own condition (5.24 px, D-051-N1). **0 wrong passes in 41 out-of-sample passes; 7/7 triangles VERIFIED at 0.40–1.11 px.** "Every figure is in-sample" is retired | ~~0.5 day~~ | ~~no~~ |
| B2 | **VERIFIED Chandrayaan-2 verdict** (criterion 2) | The loop misses the frozen 2.0 px line by 10 %. Needs NAC centred on the TMC-2 swath | 1 day | needs a fresh ODE census — the existing 22-frame census cannot centre a tile east of lon 22.10 |
| B3 | **Calibration/validation site split** (criterion 3) | FA/FR are unmeasurable without it | 1 day | needs ground truth → A3 |
| B4 | **Coverage calibration at real inlier counts** (RL-050c) | Criterion 4 is answerable in neither direction until occupancy > 0.938 is sampled | 0.5 day | no |

### Tier C — known debts and loose ends

| # | item | note |
|---|---|---|
| C1 | **Demo never browser-verified** since the reskin and four new panels | The last real browser check found 3 defects no string test caught |
| C2 | **D-005 is a permanent `PROPOSED`** | It defers to EXP-004, which has been "pre-registered, not implemented" for the project's whole life. E-042's pattern by a second route: pointing at a stage that will never run. The new guard does **not** catch it, because EXP-004 is not COMPLETE |
| C3 | Engines never built: ALIKED, RoMa, RIFT2 | Phase 2 delivered 2 of 5 |
| C4 | EXP-004 (orientation assignment), EXP-005 (rendered-GT Sun sweep) | Both pre-registered or named; neither implemented |
| C5 | Second region (highlands) on real data | All real results are Mare Serenitatis; highlands is synthetic only |
| C6 | Incidence-ceiling sweep 70–75° | D-029's 75° looks 5–10° too high; n = 3 in the decisive bin |
| C7 | MatchAnything-ELoFTR on RD-08 radar rows | The only remaining route to a multimodal claim without IIRS |
| C8 | The deck is hand-laid-out and fragile | Boxes overflow silently; `SIH_PPT` is not under git |

---

## 3. Weak and vulnerable parts — what a hostile reviewer attacks first

Ranked by how much damage the question does.

1. **"Show me viewpoint invariance."** One of the three variations the PS names. **There is no answer.** No experiment, no data, no number. This is the single most exposed point in the project.
2. **"You claim sub-pixel. Against what ground truth?"** There is none. Every real result is *corroborated* against archive geometry at a **~100 px** discrimination floor. The 0.003 px figure is a self-warp, which shares the original's texture — an upper bound on **precision**, not accuracy. The project states this honestly, which converts the attack into a credibility gain *only if stated first*.
3. **"The PS says 320:1. What do you have?"** ~65:1, from a proxy, uncontrolled. The synthetic probe stops at 32:1 and measures the wrong thing (the unmodified baseline, not the architecture's degrade-to-common-GSD answer).
4. **"It's called multi-modal."** No IIRS. The only cross-modality evidence is a **measured negative** (radar, 0/48). Genuinely data-blocked, but the title word is unsupported.
5. **"Your verdict can be fooled."** Yes — 36 of 36 constructed cases reach VERIFIED / `high` with edges wrong by up to 115 px (E-039). A detector was built and measured **undeployable** with the reference on hand (D-054). Stated openly, which is the right posture, but it is a live defect.
6. **"Everything is one region."** Mare Serenitatis, one instrument family, near-nadir, one illumination axis. Every envelope, every p-value, every engine ranking inherits that scope.
7. ~~**"Nothing was held out."**~~ **ANSWERED 2026-09-22 (EXP-018).** One window no stage had touched, opened once, against ten numbers frozen as predictions with tolerances. Eight survived; **two did not, and both failures are published with the numbers that broke them** (D-059, D-051-N1). The remaining honest caveat is smaller and is stated: **one** held-out window, mare, 20 pairs, Δincidence only — and the two highland candidates **could not supply an anti-vacuous set at all**, so terrain transfer is still untested (C5).
8. **"Your own success criterion 4 fails."** It does — and the project now also shows the criterion is mis-specified, which is a better answer than a pass would have been, but it must be *led with*, not discovered.
9. **The 42-pair census is exhausted.** No further frame can centre a tile east of lon ≈ 22.10, which blocks the cheap route to criterion 2.
10. **Demo fragility.** Four panels added today, none seen in a browser. The project's own history says string tests miss what looking catches.

---

## 4. Is the path right? — **No, and here is the correction**

### What the path has been

Twenty-one stages. Overwhelmingly concentrated on **illumination** (the axis
the project is genuinely strong on) and on **epistemic infrastructure** —
ledgers, frozen pre-registrations, negative results, guard tests. That
infrastructure is unusual and is a real differentiator: 41 error-ledger
entries, 63 decisions, and stages that report their own criteria failing.

### Where it went wrong

**The last three stages (EXP-013, EXP-014, EXP-015) all refined the
verification layer** — gauge detection, which coverage metric is best,
restating criterion 4. Each was rigorous and each produced an honest result.

**Together they moved the PS scorecard by zero.**

Meanwhile **two of the three variation axes the problem statement names —
viewpoint and scale-to-320:1 — have never been tested at all.** The project
optimised for *defensibility of what it measured* rather than *coverage of
what it was asked*.

That is a real failure of prioritisation, and it is the kind that is invisible
from inside: every individual stage was well-chosen **given the stages before
it**, and the sequence still drifted away from the brief.

### The corrected path, in order

1. **A1 — the 320:1 scale ladder, now.** A PS-named axis, currently the largest
   untested requirement, and **runnable today from data already on disk**
   (`degrade_to_gsd` + 32 NAC tiles). It also unlocks the demo's 320:1 beat,
   which the roadmap planned and nobody built. **Highest value ÷ cost in the
   project by a wide margin.**
2. **B1 — blind validation.** Half a day. Freeze, open a held-out site once,
   report whatever happens. Converts "every number is in-sample" from an attack
   into a demonstrated discipline.
3. **A2 — viewpoint, synthetic first.** The honest cheap version: a relief ×
   off-nadir sweep that finds where a 2-D model stops being valid, which is
   exactly §2.2's acceptance ("residuals white; no systematic relief
   signature"). Answers a PS axis with *something* measured instead of nothing.
4. **A3 — geodetic check points.** The only route to an accuracy claim, and it
   simultaneously unblocks criterion 2's check-point clause, criterion 3's
   FA/FR, and EXP-013's undeployable detector.
5. **B4 — coverage calibration at real inlier counts.** Cheap, closes D-057.

### What to stop

**Stop refining the verification layer.** Coverage metrics, gauge detection and
criterion restatements are now at diminishing returns — three stages today for
zero scorecard movement. The verification story is already the strongest part
of the deliverable and does not need a fourth pass.

**Do not chase criterion 2's NAC re-acquisition** (B2) before A1 and B1. It
needs a fresh ODE census for an uncertain gain, and two cheaper items move the
PS scorecard more.

---

## 5. How the drift happened — worth recording

Every stage since EXP-012 was chosen by asking *"what is the most
scientifically defensible next question given what we just found?"* That is a
good question and it produced good work. It is **not** the same question as
*"what is the problem statement still missing?"*, and the two diverged silently
from about EXP-013 onward.

The fix is structural, not a matter of trying harder: **the §2.2 requirement
decomposition should be scored in the audit alongside §53's criteria.** §53 is
the project's own bar; §2.2 is ISRO's. Only §53 has been tracked, which is why
a gap of this size could open without anything failing.

`docs/FINAL_SUCCESS_CRITERIA_AUDIT.md` measures §53 every session. Nothing
measured §2.2 until this document.
