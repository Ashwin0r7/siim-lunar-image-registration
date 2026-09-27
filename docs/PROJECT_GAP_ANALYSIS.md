# Project gap analysis — rewritten 2026-09-23, after five stages in two days

**UPDATE 2026-09-28 — EXP-023 closed the largest named gap in its
loop-closure form.** The problem statement's flagship case — OHRC ↔ LRO NAC —
now has a recorded result: the triangle at the Chandrayaan-3 site closes at
**1.9158 coarse px = 3.41 m** against the frozen 2.0 → **the first VERIFIED
Chandrayaan-2 result** (18 017 / 17 919-inlier edges at 78.5° incidence,
nulls refused at 4 inliers, second engine agreeing to 0.35–0.42 px; S2's
refined-corner corroboration NOT MET at 105–110 px vs a 98 px floor — an
eastward ~180 m term, EXP-019's archive signature at a new latitude). §53
criterion 2 **stays NOT MET** (no check point independent of LRO exists at
69.4° S); its OHRC sub-clause reads *VERIFIED by loop closure, check points
unavailable* (D-071, E-062). Weak point #6 ("sub-pixel against what?") and
corrected-path item 4 (manual check points) are now the sharpest remaining
gaps; the check-point picker (`scripts/pick_checkpoints.py`) exists and no
point has been picked. Counts as of this update: **30 stages run, 21 with
Part 1 committed before code; D-071; E-062; 1,132 tests passing at HEAD.**
Figures below this line are as of their own dates and are kept unedited
(integrity rule 3).

**This document was written on 2026-09-21 and its §4 gave a corrected path of
five numbered items. Four of the five have since run, and so has the one item
it ranked as already done.** The 2026-09-21 text is kept in full below under
integrity rule 3, including the parts this rewrite makes wrong, because a gap
analysis that quietly re-scores itself is worth nothing.

**What is different about this version.** The 2026-09-21 document's central
claim was *"the engineering is ~95 % done; the science the problem statement
asks for is ~30 % done."* **That gap is now roughly half closed, and the
closing is measurable rather than asserted** — but the five stages also
produced **three results that argue against the project's own architecture and
one against its own pre-registration discipline**, and those are the parts a
reviewer should be handed first.

---

## 1. Completion, four ways — 2026-09-23

### (a) Against §53's five criteria — **40 %, unchanged**

| # | criterion | verdict | moved this week? |
|---|---|---|---|
| 1 | Illumination separation, ≥ 2 rungs, p ≤ 0.05 | **MET** | re-measured out of sample (EXP-018) |
| 2 | ≥ 1 VERIFIED Chandrayaan-2 pair + check-point error/CI | **NOT MET** | its **check-point clause is now MET** (EXP-019); the triangle misses 2.0 px by **8.9 %** |
| 3 | FA ≤ 5 %, FR ≤ 20 %, zero VERIFIED adversarial | **PARTLY** | a stronger bound: **0 wrong passes in 41 out-of-sample passes** (EXP-018) |
| 4 | Coverage gap ≤ 0.15 on every VERIFIED pair | **NOT MET + mis-specified** | worse, not better: occupancy **0.484** at the scale envelope's rung (EXP-016). *(Later, EXP-022: **answered NOT MET** — at real counts and recorded noise the floor is 0.359; the 9-, 28- and 68-inlier edges exceed the 1 px bound, the last one **above** the floor, so no occupancy floor can be the criterion; D-069)* |
| 5 | Fresh clone, CPU-only, tests pass, licences | **MET** | suite larger and green; the demo now registers user-supplied images live |

**2 of 5 = 40 %.** Five stages moved this scorecard by **zero**, and that is a
property of §53 rather than of the stages: **§53 contains no criterion about
scale, viewpoint or modality**, the three variations the problem statement
names. The 2026-09-21 document's structural fix — *score §2.2 beside §53* — is
what makes the week's work visible at all.

### (b) Against §2.2, the problem statement's own decomposition — **≈ 30 % → ≈ 55 %**

| PS requirement | 2026-09-21 | **2026-09-23** |
|---|---|---|
| Sun-angle correspondence | NOT MET | **NOT MET as an envelope**; the 40° hard edge is **refuted in the permissive direction** out of sample (44.19° under three engines, 57.43° under two, no wrong pass) |
| **Scale 2:1 → 320:1** | NOT MET / **UNTESTED** | **NOT MET and MEASURED** — envelope **32 : 1**, mechanism **starvation**, floor **N\* = 2048 coarse px**, zero wrong passes at any rung |
| **Viewpoint** | **NEVER TESTED** | **literal form NOT MET and mis-specified; bound form MET to 20°** with the DEM the deliverable has |
| **Multi-modality** | NOT MET | **MET for reflectance** (7/9 bands within 1.334× of pan), **thermal envelope stated** (starvation at 28 : 1) — **not IIRS** |
| **Sub-pixel accuracy on check points** | NOT MET — none exist | **MET** — 0.266 reference px = **2.24 m**, CI95 0.222–0.413, 17 pairs, against another mission's control network |
| Uniform match-point distribution | NOT MET + mis-specified | unchanged *(later, EXP-022: NOT MET with named edges and a measured floor, no longer by extrapolation)* |
| Registered product | MET | MET, **and now for images the reader supplies** |
| Metrics incl. RMSE / inliers | MET | MET |
| All named formats load | PARTIAL | **PARTIAL, wider** — PDS3 map-projected products added (Kaguya TC, MI, Diviner); **IIRS still absent** |

**4 MET, 3 PARTIAL, 2 NOT MET ≈ 55 %.** Every MET row carries its scope in the
same sentence, because three of the four are met in a narrower sense than the
words suggest and saying so first is the only way the number survives contact
with a reviewer.

### (c) Against the §51 roadmap, effort-weighted — **≈ 88 % of 65 pd**

Phases 3, 6 and 10 moved. **Phase 2 (baselines) and phase 5 (verification) are
where the remaining unspent effort sits**, and phase 5's gap — the
calibration/validation site split — is the one that blocks a §53 criterion.

### (d) As a software deliverable — **≈ 97 %**

Installable from a fresh clone, CPU-only, licence-clean, fully offline,
**1 050+ tests passing**, 25 stages with frozen pre-registrations, two ledgers
with 67 decisions and 56 error entries, every advertised number traceable to an
artefact the demo serves byte for byte — and the demo now has a **live path**
that registers images a reader drops onto the page, refuses what it cannot
defend, and reaches VERIFIED only on a three-image loop.

### The number that matters, restated

> **The engineering is ~97 % done. The science the problem statement asks for
> is ~55 % done, and every remaining hole has a named blocker rather than an
> absence of evidence.**

---

## 2. What the five stages actually cost the project's own claims

This section is the reason the rewrite exists. **Four of this week's results
weaken something the project had previously asserted**, and each is in a
ledger:

1. **The architecture's scale stage lost its own ablation (D-005-N1).** D-005
   called scale normalisation *"a required first-class pipeline stage"*. Run
   against the counterfactual, it **ties 10/10 at every rung to a 16 : 1 GSD
   gap** — the detector's own scale space bridges the gap unaided. The step is
   still in the pipeline and is now justified by **nothing measured**.
2. **The illumination envelope's hard edge is refuted (D-059).** "Nothing
   passes above 40° Δinc" was an advertised number and it was wrong out of
   sample, in the permissive direction.
3. **The engine-agreement floor reversed by its own condition (D-051-N1)** at
   5.24 px, on two marginal passes.
4. **§2.2's viewpoint acceptance is unattainable as literally written
   (D-064)**, and the project reports its own acceptance mis-specified for the
   second time (after D-057 on coverage). **Two mis-specified acceptances in
   nine is a finding about the acceptances**, and it is the kind a reviewer is
   entitled to be suspicious of — which is why both are reported with the
   measurement that shows it, not as an opinion.

And two results argue against the *method*, not the architecture:

5. **E-055** — an exactness criterion that cannot hold, because "bit for bit"
   was written across two implementations differing only in accumulation dtype.
6. **E-056** — a McNemar test whose power was assumed rather than designed: with
   both arms perfect there are no discordant pairs, so the criterion could not
   have been MET by any tie however strong. **Pre-registration protects against
   moving the goalposts; it does not protect against a criterion that cannot be
   satisfied**, and this project has now hit that failure four times (E-041,
   E-046, E-053, E-056).

---

## 3. Pending work — 2026-09-23

### Tier A — named in the problem statement

| # | item | status |
|---|---|---|
| ~~A1~~ | ~~Scale ladder to 320:1~~ | **DONE — EXP-016.** Envelope 32 : 1, N\* = 2048, starvation confirmed and separated from ratio |
| ~~A2~~ | ~~Viewpoint variation~~ | **DONE — EXP-017**, synthetic viewpoint on real terrain. The real fore/aft version is still blocked: PRADAN delivered only TMC-2's nadir band |
| ~~A3~~ | ~~Sub-pixel accuracy on check points~~ | **DONE — EXP-019.** 2.24 m against Kaguya's control network. **Manual check points remain open** — the only number with no shared instrument in it |
| A4 | **IIRS ingestion + EXP-009** | **still data-blocked, and now answered by proxy.** EXP-020 ran §2.2's question on nine Kaguya MI bands; no IIRS product exists to ingest |

### Tier B — closes a §53 criterion

| # | item | status |
|---|---|---|
| ~~B1~~ | ~~Blind validation~~ | **DONE — EXP-018** |
| B2 | **VERIFIED Chandrayaan-2 verdict** | **open, and now quantified: 2.177 reference px against 2.0 — 8.9 %.** Needs a NAC frame centred on the TMC-2 swath (fresh ODE census) |
| B3 | **Calibration/validation site split** | **open — the largest remaining hole.** FA and FR are unmeasurable without it |
| B3 *(note 2026-09-23, EXP-021)* | *(row above retained under integrity rule 3)* | **RAN — measured, not closed.** B1 VERIFIED FDR 0 / 12 and FRR 0 / 12 on the pooled reading; **NOT EVALUABLE on the held-out site** (ground truth reached 2 of 7 frames); **no wrong transform in the labelled population** (E-058), so FA was never exercised. Successor item **B3′: tier-A ground truth on the hard frames** (an illumination-matched or second independent reference) - the only route to a population that contains its own negatives |
| B4 | **Coverage calibration at real inlier counts** | **open**, and EXP-016 gives it a second reason: occupancy is 0.484 at the scale envelope's rung |
| B4 *(note 2026-09-23, EXP-022)* | *(row above retained under integrity rule 3)* | **RAN — answered, not closed.** Floor at recorded noise **T″ = 0.359**; 25 of 28 evaluable edge-rows within 1 px; **three over** (9, 28 and 68 inliers: 3.93, 1.66, 1.04 px), the 68-inlier edge *above* the floor; 7 of 22 distinct edges unsampled. Criterion 4 stays NOT MET, and 4″ is not adopted (D-069). Successor **B4′**: the direct bound from each edge's own inlier positions (needs a re-run of REAL-DATA-07 that records them) and a seventh layout family for the unsampled cells |
| B4′ *(note 2026-09-24, EXP-024)* | *(row above retained under integrity rule 3)* | **RAN — the direct bound exists for every edge.** All 22 distinct edges re-matched with positions kept (counts and occupancies reproduced exactly); **20 of 22 within 1 px from their own layouts**, over: the 9-inlier (5.42 px) and 28-inlier (1.59 px) edges. The 7 unsampled cells are decided directly (all within, 0.07–0.51 px), so the seventh layout family is no longer needed for the criterion. The 68-inlier edge's proxy call **falls** (own layout 0.83 px against the proxy's 1.04) — and that pair, same count and occupancy on opposite sides of the bound, is the sharpest demonstration that no occupancy floor can be the criterion. **Triplets: 11 of 13 clear on all edges** (was 3/3/7). Criterion 4 stays NOT MET as frozen (D-070, D-069-N1) |

### Tier C — debts and loose ends

| # | item | status |
|---|---|---|
| ~~C1~~ | ~~Demo never browser-verified~~ | **DONE.** Verified in a real browser end to end: example pair → INCONCLUSIVE with a swipe comparison; a 39.81° pair → REJECTED **with no registered image emitted**; a three-image loop → **VERIFIED at 2.7e-4 px in 8.6 s**; no horizontal overflow |
| ~~C2~~ | ~~D-005 is a permanent `PROPOSED`~~ | **RETIRED — by a stage that ran.** D-005 deferred to EXP-004, which never existed; EXP-016's ablation decided it instead (D-005-N1) |
| C3 | Engines never built: ALIKED, RoMa, RIFT2 | open — phase 2 delivered 2 of 5 |
| C4 | EXP-004, EXP-005 | open; EXP-004's purpose is now partly discharged by EXP-016 |
| C5 | **Second region (highlands) on real data** | **open and now the top scope risk** — EXP-018's highland candidates could not supply an anti-vacuous set, so terrain transfer is untested |
| C6 | Incidence-ceiling sweep 70–75° | open |
| C7 | MatchAnything-ELoFTR on RD-08 radar rows | open; EXP-020 partly supersedes the motivation |
| C8 | The deck is hand-laid-out and fragile | open — `SIH_PPT` is not under git and boxes overflow silently |

---

## 4. Weak and vulnerable parts — re-ranked 2026-09-23

1. **"FA and FR?"** — still unmeasurable. **Now the single most exposed point**,
   inherited from the old list's #5 and promoted because the two axes that used
   to outrank it (viewpoint, scale) have answers.
2. **"Everything is one region."** Mare Serenitatis, one instrument family,
   near-nadir, one illumination axis. Every envelope, p-value and engine
   ranking inherits that scope — and EXP-018 measured that the **pooled** rate
   transfers while **every component range moves**, which is exactly the way
   this bites.
3. **"Your verdict can be fooled."** 36 of 36 constructed cases reach VERIFIED
   with edges wrong by up to 115 px (E-039); the detector built for it is
   undeployable with the reference on hand (D-054). **EXP-019 moved this**: the
   gauge terms track the measured archive offsets at r = 0.751, so the blind
   spot's cause is now partly attributed — but not closed.
4. **"Your own architecture's scale stage does nothing."** New this week, and
   the project says it first (D-005-N1).
5. **"Two of your nine acceptances are mis-specified."** D-057 and D-064. True,
   measured, and uncomfortable — the defence is that both are reported with the
   measurement that shows it and neither was rewritten to pass.
6. **"Sub-pixel against what?"** Much stronger than three days ago (2.24 m
   against another mission's control) — but it is a **two-leg bound** whose
   shared reference cancels, and manual check points still do not exist.
7. **"The 320 : 1 rung fails."** It does. The answer is the floor plus the
   arithmetic, and the arithmetic puts the real OHRC-in-IIRS case **above** the
   floor — but that is arithmetic, and it is labelled as such everywhere.
8. **"Your success criterion 4 fails."** Unchanged, and now with a second
   number against it. *(Later, EXP-022: it fails on **three named edges**,
   and the stage shows why no occupancy floor could fix it. That answer is
   stronger than the question, and it should be given first.)* *(Later still,
   EXP-024: the answer is **complete** — every edge measured from its own
   layout, **two** named edges fail (9 and 28 inliers), nothing is decided
   by proxy, and 11 of 13 VERIFIED triplets are demonstrably clear. The
   criterion still fails, and the failing set is now exactly known.)*
9. **The 42-pair census is exhausted** — blocks the cheap route to criterion 2.
10. ~~"Nothing was held out."~~ **Answered (EXP-018).** ~~"Demo never seen in a
    browser."~~ **Answered.**

---

## 5. Is the path right? — **yes, for the first time, and here is the next one**

The 2026-09-21 correction said: *stop refining the verification layer; run the
PS axes.* That is what happened — **five stages, four of them on PS axes, and
the §2.2 scorecard moved from ≈ 30 % to ≈ 55 % while §53 stayed still.** The
correction worked, and the fact that it is visible at all is due to the
structural fix (score both scorecards), not to anyone trying harder.

**The corrected path from here, in order:**

1. **B3 — the calibration/validation site split.** The largest hole, the one
   §53 criterion that is *unmeasurable* rather than failing, and the answer to
   the first question a hostile reviewer now asks. ~1 day.
2. **C5 — a second terrain class on real data.** Every number in the project
   inherits Mare Serenitatis. EXP-018 showed pooled figures transfer while
   component ranges do not; a highland window is the only way to price that.
   Needs a census that can supply an anti-vacuous set.
3. **B4 — coverage calibration at real inlier counts.** Cheap, closes D-057's
   open direction, and EXP-016 gave it a second motivation.
4. **Manual check points** on one window — the only accuracy number with no
   shared instrument in it, and the thing that converts EXP-019's bound into an
   accuracy.
5. **B2 — a NAC frame centred on the TMC-2 swath.** Now worth doing *because*
   the miss is quantified at 8.9 %; before EXP-019 it was an unbounded gamble.

**What to stop:** adding evidence modules to the demo. It has ten, every one
tied to a recorded artefact, and a live path. The marginal reader learns more
from the eleventh *number* than from the eleventh *panel*.

---

*(Everything below is the 2026-09-21 document, retained under integrity rule 3.
Its §4 corrected path is the one that was executed; its scores and its "what to
do next" are superseded by the sections above and are **not** edited.)*

---

# Project gap analysis — how complete is this, really, and is the path right?
*(2026-09-21 version, retained under integrity rule 3)*

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
