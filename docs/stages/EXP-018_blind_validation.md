# EXP-018 — Blind validation: the frozen pipeline opened once on data no stage has touched

**Part 1 — pre-registration. FROZEN 2026-09-21, before any held-out product
has been named, before any held-out byte has been fetched, and before any
runner code for this stage exists.** Part 2 is empty until Part 1 is
committed. Amendment A1 (the census and frame list, §3.5) is appended
*after* this commit and *before* any pixel is fetched; it may add frames to
the record and may not touch a criterion, a tolerance or a prediction.

**Classification: DELIVERABLE-CRITICAL.** Roadmap phase 8 has never been
attempted. `docs/PROJECT_GAP_ANALYSIS.md` item B1 and hostile-reviewer point 7
say the same thing in two registers:

> **Nothing was held out.** No blind validation. Every figure is in-sample,
> including the ones with CIs.

Every envelope, every wrong-pass count, every agreement floor and every loop
residual this project advertises was measured on the 42 Mare Serenitatis pairs
that produced it. This stage freezes each of those numbers as a **prediction
with a tolerance**, opens one new ground window **once**, and reports every
number as it falls. **A failed prediction is the headline of Part 2, not a
footnote.**

---

## 0. The requirement, quoted, and what can and cannot be adopted from it

### 0.1 Roadmap phase 8 (`MASTER_RESEARCH_AND_ARCHITECTURE_PLAN.md` §51, verbatim)

> | 8 Blind validation | Held-out sites opened once | 5, 6 | Freeze, run, report | — | Blind report | Verdict FA/FR within calibration | — | 7 | 2 pd | medium |

Its success column reads **"Verdict FA/FR within calibration"**, and §53's
third criterion gives the numbers:

> - Verdict FA ≤ 5 %, FR ≤ 20 % on validation sites; zero VERIFIED on the adversarial set.

**Neither FA nor FR can be adopted as a criterion here, and the reason is
structural, not a shortage of effort.** A false-acceptance rate needs a set of
accepted registrations *and the truth of each*; a false-rejection rate needs
rejected registrations *and the truth of each*. This project has no ground
truth on any real pair — `FINAL_SUCCESS_CRITERIA_AUDIT.md` records criterion 3
as **NOT EVALUABLE** for exactly this reason, and its 2026-09-21 update adds
that EXP-012's 0 / 39 "is by construction, not by measurement". Nothing this
stage does creates ground truth (that is item A3, geodetic check points, and
it is not on disk). So:

- **FA is replaced by the only proxy the project has:** the *wrong-pass* rate
  — passes under the frozen rule whose transform is INCONSISTENT with archive
  corner geometry — at that check's own discrimination floor (§6.2: it cannot
  see an error below ~250 px). That is what `MEASURED_WRONG_PASS` already is,
  and it is what S2 tests out of sample. **It is a bound at a stated floor,
  never an FA rate**, and Part 2 will not call it one.
- **FR has no proxy and is not measured.** A REJECTED pair that was in fact
  registrable is indistinguishable from one that was not, without truth. Part
  2 says "FR: not measurable" and stops.

The phase-8 verb sequence — **freeze, run, report** — *is* adopted in full,
and is the discipline this whole document exists to enforce.

### 0.2 The §2.2 row this stage bears on (verbatim)

> | Correspondence under Sun-angle change | What fraction of appearance change is predictable from DEM + ephemeris, and what residual remains? | Illumination-conditioned matching path with a stated operating envelope in Δincidence and Δazimuth | Success rate vs Δinc/Δaz on real pairs; endpoint error on rendered-GT pairs | EXP-007 (real), EXP-005 (rendered GT) | Envelope ≥ 40° Δinc at TMC/IIRS rungs; boundary *stated* at OHRC/NAC rung |

Of its acceptance criterion, the clause **"boundary *stated* at OHRC/NAC
rung"** is adopted: the project *has* stated a boundary at the native NAC rung
(REAL-DATA-07 amended run: last ≥ 0.8 bin at 20–25°, 0.29 at 25–30°, nothing
above 40°), and S1 asks whether a stated boundary is a *property of the
pipeline* or *a property of the 42 pairs it was read from*. The clause
"Envelope ≥ 40° Δinc at TMC/IIRS rungs" is **not** adoptable here: this stage
runs at the native rung only, with no Chandrayaan-2 data (REAL-DATA-09 owns
that) and no coarser rung.

---

## 1. The question

**Q.** Take every quantitative claim the project makes about real NAC
registration that is falsifiable on new data. Freeze each as a numeric
prediction with a tolerance. Fetch a small set of frames over **one ground
window no stage has ever used**, run the pipeline **exactly as frozen**, once,
and ask: **how many of the predictions survive contact with data that did not
produce them?**

Every outcome is a result:

- **If the predictions hold**, the deliverable's headline numbers acquire the
  one property they currently lack — an out-of-sample check — and the phrase
  "every figure is in-sample" is retired from the gap analysis.
- **If a prediction fails**, that failure is the finding. The advertised number
  was a description of 42 pairs, not of the pipeline, and the demo, README and
  §53 scorecard must say so beside the number. Nothing is re-tuned to make it
  pass.
- **If the held-out set cannot be built** (archive unreachable, or no window
  satisfies the anti-vacuity gate S5 within budget), the stage reports
  **CANNOT RUN**, fetches nothing, and does **not** substitute in-sample data.

---

## 2. What is frozen as a prediction — the numbers, quoted from their sources

Each prediction below is copied from a recorded artefact or a ledger row. The
arithmetic that pools recorded 5° bins into three ranges is shown so that no
reader has to trust it. **Nothing here is computed on held-out data.**

### 2.1 P1 — the illumination envelope (REAL-DATA-07 amended run)

Source: `experiments/REAL-DATA-07/real_data_07_results_nue.json`,
`criteria.envelope_b1.pooled.bins_5deg` and `criteria.envelope_lg.pooled.bins_5deg`
(B1 RootSIFT and B4L DISK + LightGlue; 42 geometry-confirmed pairs, two mare
windows, orientation `north_up_east_right`). Success = `n_inliers > 8` (D-023)
**and** transform not INCONSISTENT with archive geometry.

Recorded 5° bins (bin label = lower edge of Δincidence), B1:

| bin | 0 | 5 | 10 | 15 | 20 | 25 | 30 | 35 | 40 | 45 | 50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| n | 7 | 4 | 3 | 3 | 9 | 7 | 2 | 3 | 1 | 1 | 2 |
| B1 rate | 0.714 | 0.750 | 1.000 | 0.667 | 0.889 | 0.286 | 0.500 | 0.333 | 0 | 0 | 0 |
| B4L rate | 0.714 | 0.750 | 1.000 | 0.667 | 0.889 | 0.286 | 0.500 | **0.000** | 0 | 0 | 0 |

The stage report's own summary of the same run: *"the last bin with ≥ 0.8
success is 20–25°; the 25–30° bin is 0.29; nothing passes above 40°."*

**Frozen predictions, pooled into three ranges** (successes = rate × n, from
the table above; single 5° bins with n = 1–3 cannot carry a test):

| range | in-sample n | B1 successes | **B1 predicted rate** | Wilson 95 % (in-sample) | B4L successes | **B4L predicted rate** |
|---|---|---|---|---|---|---|
| Δinc < 15° | 14 | 5 + 3 + 3 = 11 | **0.786** | ≈ 0.52 – 0.92 | 11 | **0.786** |
| 15° ≤ Δinc < 30° | 19 | 2 + 8 + 2 = 12 | **0.632** | ≈ 0.41 – 0.81 | 12 | **0.632** |
| Δinc ≥ 30° | 9 | 1 + 1 + 0 + 0 + 0 = 2 | **0.222** | ≈ 0.06 – 0.55 | 1 | **0.111** |
| Δinc ≥ 40° | 4 | 0 | **0.000** | 0 – 0.53 (one-sided 95 %) | 0 | **0.000** |
| pooled | 42 | 25 | **0.595** | ≈ 0.45 – 0.73 | 24 | **0.571** |

B4X (XFeat) has no per-bin record in the artefact; its pooled rate is frozen
from `MEASURED_WRONG_PASS["B4X"]` and the Part 2 addendum: **27 / 42 = 0.643**.

The Wilson column is stated because it is the parameter-count honesty E-041
demands: each predicted rate is itself an estimate from 9–19 pairs, and a test
against the *point* rate can fail because the point was noisy in-sample. S1
is graded on the point rate (the stricter, more falsifiable form) and the
beta-binomial predictive interval is reported beside it (§5.2).

### 2.2 P2 — the wrong-pass bound (`siim.demo.verdict.MEASURED_WRONG_PASS`, as corrected by E-038)

Quoted from `src/siim/demo/verdict.py:157-167`:

> `"B1": {"n_pass": 46, "n_wrong_pass": 0, ...}` ·
> `"B4L": {"n_pass": 49, "n_wrong_pass": 1, ...}` ·
> `"B4X": {"n_pass": 27, "n_wrong_pass": 0, ...}`

with the counting rule `tests/test_wrong_pass_tally_matches_artefacts.py`
enforces: `pass = n_inliers > 8`, `wrong_pass = pass and geometry
INCONSISTENT`. **Frozen bounds** (exact one-sided 95 % Clopper–Pearson upper
limit on the wrong-pass probability):

| engine | in-sample | **p_upper (95 %)** |
|---|---|---|
| B1 | 0 / 46 | 1 − 0.05^(1/46) = **0.0631** |
| B4L | 1 / 49 | **0.0929** |
| B4X | 0 / 27 | 1 − 0.05^(1/27) = **0.105** |

**Point prediction:** zero wrong passes for every engine on the held-out set.
§53's own line, FA ≤ 5 %, is evaluated beside these at p₀ = 0.05 (§5.2).

### 2.3 P3 — the engine-agreement floor (D-051)

Quoted from `docs/stages/DECISION_LEDGER.md` D-051:

> **The engine-agreement floor is 3 px, measured on three engines** … 24
> all-success triples: max pairwise disagreement 2.16 px (B1 vs B4X); any
> geometry-inconsistent transform: min 247 px … *Reversed by:* A
> geometry-consistent all-success triple disagreeing by > 3 px, or an
> inconsistent one under 30 px.

D-051 states its own reversal condition. **S3 is that condition, tested out
of sample**: prediction — no agreeing pair above **3.0 px**, no inconsistent
pass under **30 px**. Agreement is `siim.pipeline.agreement.engine_agreement`,
the dense median endpoint disagreement between two engines' final transforms
on a 16 px grid over the source tile, unchanged.

### 2.4 P4 — loop closure on real triplets (EXP-012)

Quoted from `docs/stages/EXP-012_verdict_calibration.md` Part 2:

> All 13 admissible triplets close, with loop residuals of **0.3654 – 1.3358
> px** against the frozen 2.0 px reject line, and the unmodified `assess()`
> returns **VERIFIED on all 39 edge verdicts**.

**Prediction:** every held-out triplet whose three edges are B1 successes
closes under `LOOP_ERROR_REJECT_PX = 2.0` px, composed exactly as EXP-012
composed (direction read from each row's `edge`, inverse check to < 1e-9 px,
`north_up_east_right` tile frame throughout, `loop_closure(step=16)`).
EXP-012 also found the residual does **not** track edge quality (ρ = 0.055);
that is *not* frozen as a prediction because it was a refuted hypothesis, but
the correlation is reported again (§7).

### 2.5 P5 — the incidence-ceiling effect (REAL-DATA-07 addendum, RL-042c) — reported, not graded

> B1 success by the HIGHER incidence of the pair, restricted to Δinc ≤ 25°:
> ≤ 55° — 13 / 15 (0.87); 65–70° — 6 / 8 (0.75); **70–75° — 1 / 3 (0.33)**.

Post hoc in its origin and n = 3 in the decisive bin, so it is **reported
(§7), not a criterion**. Prediction recorded anyway: on held-out pairs with
Δinc ≤ 25° whose higher-incidence frame is ≥ 70°, the success rate is below
that of pairs whose higher frame is ≤ 55°.

---

## 3. What counts as held out — established from evidence, not assumed

### 3.1 Inventory: every tile on disk is already used

Run 2026-09-21 before this document was written (it inspects file names and
artefact text; it computes no response variable): a case-insensitive scan for
NAC product IDs (`M` + 9–10 digits + `L`/`R` + optional `C`) over
`experiments/**/*.{json,csv,log,md}` and `data/manifests/*.json` — **154
files, 910 distinct product IDs referenced** — against the 32 tile files in
`data/processed/mare_serenitatis/`, which carry **17 distinct product IDs**.

| result | count |
|---|---|
| product IDs on disk that appear in **no** artefact | **0** |
| tile files on disk whose file name appears in no artefact | **0** (every one of the 32 is named by 1–17 artefacts) |

**There is no untouched tile. The "untouched tiles exist" branch is closed by
evidence, and a fresh acquisition is the only honest route.** The 32 tiles
are the incumbents A–D (three windows each), the REAL-DATA-07 census, the
EXP-007 long triplets and the H1/H2 hypothesis tiles; every one has fed a
recorded row.

### 3.2 Ground the project has touched at label level

Two further regions were surveyed on 2026-08-24 (`scripts/acquire_lro_nac.py`,
labels only, no image bytes): **`tycho_highlands`** (box −43.8…−42.8° N,
348.5…349.5° E) and **`apollo15_hadley`** (25.5…26.5° N, 2.5…3.5° E).
`data/metadata/tycho_highlands/` holds 4 PDS4 labels and
`data/metadata/apollo15_hadley/` 4; `region_survey.json` and
`lro_nac_manifest.json` name two products from each. No pixel of any of them
was ever decoded — but a product whose label is on disk is not "untouched" by
the grep S0 demands, and a box that was *chosen* by this project is not a box
this project never looked at. **Both boxes are excluded as held-out
candidates.** The Mini-RF and WAC proxies (REAL-DATA-08) sit over the
Serenitatis windows and are irrelevant here.

### 3.3 The 50 km rule

`MASTER_RESEARCH_AND_ARCHITECTURE_PLAN.md` §28: *"no site within 50 km of
another split's site; no repeat acquisitions of a split's ground in another
split."* The in-sample ground is RD-03 (lon 22.034°, lat 20.035°) and RD-04
(lon 22.010°, lat 19.666°), plus the EXP-007 long windows on the same frames.
Every candidate below is > 500 km from both (Apollo 16 ≈ 880 km, Apollo 14
> 1 000 km, Apollo 11 ≈ 590 km — great-circle on a 1 738 km radius).

### 3.4 Candidate windows, in priority order, fixed here

The primary arm is **highlands**, because it is the terrain the project has
never registered on real data (gap item C5) and because a window that only
re-samples mare would answer the out-of-sample question without touching the
one-region weakness. The fallback is a **fresh mare window**, which tests the
envelope on its own terrain with no transfer confound. The scout's census
decides which is *feasible*; the priority order decides which is *used*, and
it is fixed now:

| priority | arm | window centre (lon E, lat) | terrain | why this one; physical check (§6.1) |
|---|---|---|---|---|
| **1** | **H** | **Apollo 16 / Descartes: 15.50° E, −8.97°** | highlands | Repeatedly targeted by LROC under many illuminations; latitude 9° S ⇒ minimum attainable incidence ≈ 7.4°, so low-Δinc *and* low-absolute-incidence pairs are physically available |
| 2 | H | Apollo 14 / Fra Mauro: 342.53° E, −3.65° | hummocky highland ejecta | Same argument; terrain is intermediate and is labelled as such if used |
| 3 | M | Apollo 11 / Mare Tranquillitatis: 23.47° E, 0.67° | mare | The no-transfer control: same terrain class as in-sample, ≈ 590 km away; latitude 0.7° N ⇒ minimum incidence ≈ 0.9° |
| — | excluded | Chandrayaan-3 site: 32.32° E, −69.37° | highlands | **Physically unable to supply the low-incidence regime:** at 69.4° S the minimum solar incidence is ≈ 67.8° (§6.1), above the ~66° regime where RD-07's two darkest frames fail against everyone; every pair would confound Δinc with the incidence ceiling |
| — | excluded | Tycho box, Apollo 15 box | highlands / boundary | label-touched (§3.2) |

**Rule:** the census (§3.5) is run on priority 1. If it satisfies S5 from
geometry alone, that window is the held-out set and no other is censused. If
not, priority 2, then 3. If none satisfies S5 within the budget, the stage is
**CANNOT RUN** and no pixel is fetched. The window actually used is recorded
in A1 before any byte of image data moves. **The arm may not be switched
after any pixel has been seen.**

### 3.5 Frame selection — deterministic, from archive metadata only

Identical filters to REAL-DATA-07 Part 1 §1 and §3, copied and not re-tuned:
calibrated NAC (`pt=CDRNAC4`) whose swath contains the window's target point
(corner-map inversion, **no clamping** — RD-07 excluded E1 for exactly this),
**incidence ≤ 75°** (D-029), **emission ≤ 1.8°** (RD-07's off-nadir cut), no
night frames, L/R frames of one orbit counted as one frame (only one of the
pair enters, the one with the lower emission).

**Selection is an incidence ladder, so the Δinc spread S5 needs is engineered
by construction rather than hoped for:** for each rung in
**{20°, 25°, 30°, 40°, 50°, 60°, 70°}** take the admissible frame whose
incidence is nearest the rung (ties: lower emission, then lexically smaller
product ID); a rung with no frame within ±5° is left empty and the nearest
unused admissible frame is taken instead, until **at most 8 frames** are
listed. This is a function of the label fields alone.

**Budget, stated:** ≤ 8 frames, one window, one 4096-line × 2048-sample
tile per frame centred on the target by the same corner-map inversion as
REAL-DATA-03/04/07, **decimation 2** (4 for any frame finer than 0.6 m, the
E1 rule), fetched by strict 8 MB byte-range chunks with SHA-256 recorded per
tile (`scripts/acquire_real_data_07.py` pattern; a new `--window` entry, no
change to how bytes are planned or decoded). At the 100 KB/s the archive
served on 2026-09-04 (RD-07 Part 1 §7) a window is 4096 × 5064 × 2 B =
**41.5 MB ≈ 7 min**; eight frames ≈ **1 h**.

**Amendment A1** — appended to this file after the Part 1 commit and before
any pixel byte is fetched — records: the ODE census (query box, product count,
filter counts), the incidence ladder and the ≤ 8 frames chosen, each frame's
corner geometry from the PDS index table (`fetch_index_geometry.py`), each
frame's **Jacobian-determinant sign** (E-037 handedness, read from corners
before any pixel exists), the CONFIRMED overlap graph
(`verify_tile_overlap.py --require-confirmed`, CONFIRM_AT = 0.50 at the
pessimistic end, unchanged), the S5 counts computed from that geometry, and
the S0 grep record (§5.1). A1 may **add** this information; it may not alter
§2, §5, §6 or §8.

---

## 4. Method, fixed in advance

**The frozen pipeline is REAL-DATA-07's amended run, byte for byte.** Engines
B1 (RootSIFT, unmodified), B4L (DISK + LightGlue, 4096 keypoints, unmodified),
B4X (XFeat, pinned commit); LO-RANSAC affine, `ransac_threshold_px = 3.0`,
`seed = 0`; `--orientation north_up_east_right`; percentile stretch; failure
rule `n_inliers <= 8` (D-023); geometry check
`scripts/check_transform_against_geometry.py` with its restated constants
(INCONSISTENT only beyond 3× the discrimination floor at the optimistic end);
one direction per unordered pair, **lower-incidence frame as source**, exactly
as RD-07 ordered its edges. Loop composition and `assess()` exactly as
EXP-012 §3 (post-A1).

**Runner rules.** `scripts/run_exp018.py` is written only after this Part 1 is
committed, and is committed **before** A1 and before any tile is fetched, so
the code that will read the held-out data is on record before the data
exists. It **imports** `run_real_data_07`'s per-edge function rather than
re-implementing it, and it refuses to overwrite an existing artefact
(integrity rule 4). Artefacts: `experiments/EXP-018/exp018_s0_untouched.json`
(pre-A1), `data/manifests/exp018_<window>_manifest.json`,
`experiments/EXP-018/overlap_<window>.json`, `experiments/EXP-018/rows_<window>_nue.json`
(the RD-07 row schema, so every existing test and reader applies unchanged),
and `experiments/EXP-018/exp018_results.json` (every criterion, every
prediction, every fall).

**Sequence — each step once, in this order:**

1. Commit this Part 1.
2. Write and commit the runner and its tests (reproduction gate included).
3. Census the priority-1 window from labels and corners; evaluate S5 from
   geometry; run the S0 grep; append and commit **A1**.
4. Fetch the ≤ 8 tiles; manifest with SHA-256; record handedness per frame.
5. Verify overlap from corners (`--require-confirmed`); exclude and list
   unconfirmed pairs.
6. Run the S0 reproduction gate on the *recorded* tiles. If it fails, stop.
7. Run the held-out set **once**: three engines, every CONFIRMED pair, the
   geometry check, engine agreement, every B1-success triangle composed and
   assessed.
8. Write Part 2 answering every criterion as frozen.

**Crash policy, stated now:** if the runner dies for a non-scientific reason
(machine, network mid-fetch, an exception) the partial artefact is kept, the
defect is recorded as an E-nnn, and the run is restarted **once** with no
change to any criterion, tolerance, frame, engine or setting. This is what
REAL-DATA-07 did on 2026-09-04 (`run_rd04_died_v1.log`). A second restart is
not permitted; the stage reports what it has.

---

## 5. Success criteria — FROZEN

### 5.1 The table

| ID | Criterion | MET if |
|---|---|---|
| **S0** | **Harness and provenance controls — nothing is reported from the held-out set unless all six hold.** | **(a) untouched:** before A1, a case-insensitive grep for each candidate product ID (both `Mnnnnnnnnn[LR]C` and `nac.mnnnnnnnnn[lr]c` spellings) over the entire repository tree at the Part 1 commit — `experiments/**`, `data/manifests/**`, `data/metadata/**` (file names and contents), `data/processed/**` (file names), `docs/**`, `src/**`, `scripts/**`, `tests/**` — returns **zero hits for every frame**; the command, the file count and the per-ID hit count are recorded in `exp018_s0_untouched.json`. A frame with a hit is dropped before A1 and listed. **(b) separation:** the window centre is ≥ 50 km from RD-03 and RD-04 (§3.3). **(c) overlap before pixels:** every pair that enters is CONFIRMED by `verify_tile_overlap.py --require-confirmed` from archive corners, before any matching. **(d) orientation before pixels:** every frame's Jacobian-determinant sign is recorded in the manifest, and `north_up_east_right` is applied; the number of mirrored frames is reported (E-037). **(e) reproduction gate:** on the recorded tiles, the runner reproduces the three B1 counts of EXP-012's primary triplet R4-6 **exactly** — `m1271742202lc ↔ m1299958135lc` **1608**, `m1299958135lc ↔ m1315225542lc` **2726**, `m1271742202lc ↔ m1315225542lc` **2138** (`rows_rd04_nue.json`, each in the direction its `edge` records) — and re-composes REAL-DATA-03's recorded triplet to **1201.0378963072235 px** (EXP-012 S4). **(f) frozen code:** the runner commit precedes the manifest's `retrieved_utc`, and no file under `src/` changes between that commit and the run. |
| **S1** | **The envelope holds out of sample (P1).** | For B1 (**S1a**) and B4L (**S1b**) separately: in each of the three ranges (< 15°, 15–30°, ≥ 30°) and pooled, with n_r held-out CONFIRMED pairs and k_r successes, the exact two-sided binomial test at the frozen point rate does not reject — i.e. neither P(X ≤ k_r) < 0.025 nor P(X ≥ k_r) < 0.025 under Binomial(n_r, p_r). **S1c**: **0 successes** among the n_≥40 pairs at Δinc ≥ 40° for B1 and B4L (point prediction; requires n_≥40 ≥ 3). **S1d**: B4X pooled success count within the same two-sided test at p = 0.643. S1 as a whole is MET only if S1a, S1b, S1c and S1d are all MET; each is reported on its own line. |
| **S2** | **The wrong-pass rate is within its predicted bound (P2).** | **S2a (point):** zero wrong passes for every engine. **S2b (bound):** for every engine, with n_pass held-out passes and k wrong passes, the exact one-sided binomial test does not reject H₀: p ≤ p_upper at α = 0.05 — i.e. P(X ≥ k \| n_pass, p_upper) ≥ 0.05 with p_upper = 0.0631 (B1), 0.0929 (B4L), 0.105 (B4X). §53's FA ≤ 5 % line is evaluated the same way at p₀ = 0.05 and reported beside S2b. Requires n_pass(B1) ≥ 5; otherwise **CANNOT CHECK**. |
| **S3** | **Engine agreement stays inside D-051's floor (P3) — D-051's own reversal condition, out of sample.** | **S3a:** for every engine pair (B1–B4L, B1–B4X, B4L–B4X) and every held-out pair on which *both* engines succeed, median dense disagreement ≤ **3.0 px**. **S3b:** every geometry-INCONSISTENT pass disagrees with every other engine's transform on that pair by ≥ **30 px** (null by construction — reported as CANNOT CHECK — if no INCONSISTENT pass occurs). S3a requires ≥ 3 qualifying pairs; otherwise CANNOT CHECK. |
| **S4** | **Loop closure behaves as EXP-012 predicts (P4).** | Every triangle in the CONFIRMED overlap graph whose three edges are B1 successes closes with `loop_closure` residual **< 2.0 px**, and the unmodified `assess()` returns VERIFIED on each of its edges. **CANNOT CHECK** if no such triangle forms — reported as such, never as MET. |
| **S5** | **Anti-vacuity: the held-out set must be able to fail S1, S2 and S3.** Decided from geometry in A1, before any pixel. | From labels and CONFIRMED overlap alone: **n_<15 ≥ 5**, **n_≥30 ≥ 5**, **n_≥40 ≥ 3**, **n_total ≥ 12** CONFIRMED pairs; at least one frame with incidence ≤ 30° and one ≥ 60°; at least one CONFIRMED triangle (so S4 is at least possible); ≤ 8 frames. If unsatisfied, the window is rejected at A1 and the next priority is censused (§3.4). |

**Why S5's minima are what they are** (from the frozen rates, nothing else):
at n = 5 and p = 0.786 the two-sided test rejects only at k ≤ 1, so five
low-Δinc pairs make S1's low range *fail-able* at 1 / 5 or worse; at n = 5 and
p = 0.222 it rejects at k ≥ 4, so five high-Δinc pairs make the high range
fail-able at 4 / 5 or better; three pairs above 40° make S1c fail-able on a
single success. With fewer pairs than that the ranges cannot fail at all, and
a MET would be E-039's "passed for the wrong reason" — the set lacking the
property the test needs.

### 5.2 Parameter count against constraint count (E-041), per criterion

| criterion | parameters fitted on held-out data | constraints | what the statistic can and cannot resolve |
|---|---|---|---|
| S1 | **0** — the four rates per engine are fixed numbers from §2.1 | n_r held-out pairs per range (≥ 5 / ≥ 2 / ≥ 5 / ≥ 3 by S5) | The point rates carry their own in-sample uncertainty (Wilson column, from 9–19 pairs). Reported beside each range: the beta-binomial predictive interval with a Jeffreys prior on the in-sample count — the graded test is the point-rate one; the predictive interval says whether a failure is attributable to a noisy in-sample estimate |
| S2 | **0** | n_pass held-out passes (≥ 5) | At n_pass = 12 and p_upper = 0.0631, P(X ≥ 2) = 0.17 and P(X ≥ 3) = 0.036: **S2b can only fail at k ≥ 3**. It is a weak bound and is said to be; S2a carries the weight |
| S3 | **0** — floor fixed at 3 px | each qualifying pair is one constraint; each engine's transform is a 6-parameter affine estimated from its own inliers | Agreement is not accuracy: two engines agreeing on a shared preprocessing error is invisible (module docstring) |
| S4 | **0** in the residual; each edge is a 6-parameter affine, 18 per triplet, against a 3-edge cycle (redundancy 1, E-041) | one constraint per triplet | **Exactly blind to per-image gauge error** (EXP-012 §6, 36 / 36 VERIFIED at up to 115 px) — a closing loop is not an accuracy statement and Part 2 will not phrase it as one |
| S5 | none | counts | — |

### 5.3 Predicted outcome per criterion, recorded now so it can be wrong

Confidence is stated for the primary arm (H, highlands) and the fallback (M,
fresh mare). Where they differ, the difference is the terrain-transfer risk,
named.

| criterion | prediction | confidence, arm H | confidence, arm M | why, and what I would bet against |
|---|---|---|---|---|
| S0 | MET | HIGH | HIGH | EXP-012 reproduced 22 / 22 recorded counts bit-for-bit one day ago on this environment. The likeliest failure is (a): a candidate frame turning up in a census listing — that drops the frame, not the stage |
| S1a (B1 ranges + pooled) | MET | **LOW-MEDIUM** | MEDIUM | On mare the point rates come from 42 pairs and the tolerance is wide. On highlands the < 15° range should hold or improve (more persistent topographic edges); the 15–30° range is where a transfer failure would show first |
| S1b (B4L) | MET | LOW-MEDIUM | MEDIUM | As S1a; B4L's ≥ 30° rate (0.111, 1 / 9) is the least-constrained prediction in the document |
| S1c (0 above 40°) | MET | **LOW** | MEDIUM | **The prediction most likely to fail on highlands, and I record that I would bet against it there.** Crater rims and boulder shadows persist across large Δinc; a single pass above 40° refutes the point prediction. Its failure would widen the deliverable's envelope and narrow its generality claim simultaneously — both are reported |
| S1d (B4X pooled) | MET | LOW-MEDIUM | MEDIUM | 0.643 from 42 pairs, no per-bin record |
| S2a (0 wrong passes) | MET | MEDIUM | MEDIUM | Wrong passes come from repetitive texture; highlands is less periodic than mare. But the floor is ~250 px (§6.2), so only gross wrong passes count either way |
| S2b (bound) | MET | HIGH | HIGH | Arithmetically hard to fail (§5.2) |
| S3a (≤ 3 px) | MET | **MEDIUM** | MEDIUM-HIGH | In-sample max 2.16 px on 24 triples; 3 px is 39 % headroom. On highlands, relief parallax between frames of different emission is 2–9 px at the tile GSD (§6.3) and two affines fitted to different inlier sets will absorb it differently. **S3a may fail on highlands for a physical reason, and that reason is registered now** |
| S3b (≥ 30 px) | CANNOT CHECK (predicted no INCONSISTENT pass) | MEDIUM | MEDIUM | Follows from S2a |
| S4 (loops < 2.0 px) | MET, if any triangle forms | LOW-MEDIUM | MEDIUM | In-sample 0.37–1.34 px on 13; 2.0 px is 50 % headroom above the worst. Same parallax caveat as S3a. Probability that ≥ 1 all-success triangle forms at all: MEDIUM |
| S5 (from geometry) | MET on priority 1 | MEDIUM | — | Apollo 16 is heavily imaged, but the ladder needs ≥ 7 admissible frames through one target point with emission ≤ 1.8°; the scout's census decides |

**Overall:** I predict at least one graded prediction **fails** on arm H
(most likely S1c or S3a), at MEDIUM confidence; and that all graded
predictions hold on arm M, at MEDIUM confidence. If arm H is run and every
prediction holds, that is a stronger result than this document expects and
will be reported as exceeding its prediction — not as confirmation of a
prediction that was not made.

---

## 6. Physical limits, stated numerically

1. **Solar geometry bounds the attainable incidence.** The Moon's solar
   declination stays within ±1.54°, so at latitude φ the minimum solar
   incidence at nadir is ≈ |φ| − 1.54°. Apollo 16 (9.0° S): ≥ **7.4°**.
   Tycho box (43.3° S): ≥ **41.8°**. Chandrayaan-3 site (69.4° S): ≥
   **67.8°**, which is *above* the ~66° regime where RD-07's two darkest
   frames (DN medians 342–391) fail against nearly every partner. A polar
   site therefore cannot supply the low-incidence half of the envelope, and
   is excluded on that arithmetic, not on preference.
2. **The geometry check is blind below ~250 px.** Corner coordinates are
   quantised at 0.005° (≈ 152 m latitude, ≈ 142 m longitude at 20° N;
   comparable at 9° S), giving discrimination floors of **84–103 px** at the
   ≈ 2 m tile GSD on RD-07's rows; INCONSISTENT requires the disagreement's
   optimistic end to exceed **3×** that floor. A wrong pass therefore means a
   transform wrong by **≳ 250 px**; S2 says nothing about errors below that.
   This is the floor `MEASURED_WRONG_PASS` already carries and it is why S2 is
   a bound and not an FA rate.
3. **Relief parallax on highlands.** With both frames at emission |e| ≤ 1.8°
   the differential parallax of a point at height h above the local reference
   is ≤ h · tan(3.6°) = **0.0629 h**. For h = 300 m (a modest highland crater
   rim; an assumption, stated because no DEM window for the site is on disk)
   that is **18.9 m ≈ 7–9 px** at 2.0–2.6 m per decimated pixel; at a typical
   1° differential it is 5.2 m ≈ **2–3 px** — the same magnitude as the 3 px
   agreement floor (S3a) and the 2 px loop line (S4). A global affine cannot
   absorb it. On mare (relief tens of metres) the same term is < 1 px. **A
   highlands failure of S3a or S4 is therefore ambiguous between pipeline and
   physics, and Part 2 must report the per-pair emission difference beside
   any such failure rather than choose.** §2.2's own rule — "DEM
   orthorectification when relief × tan(e) > 0.5 px" — is not part of the
   frozen pipeline and is not added for this stage.
4. **Rule-of-three bounds.** 0 / 46 → p ≤ 0.0631; 1 / 49 → p ≤ 0.0929;
   0 / 27 → p ≤ 0.105; **0 / 4 above 40° → p ≤ 0.527**. The last number is
   why S1c is graded as a point prediction: a bound test at 0.527 would pass
   3 / 3 successes (P(X ≥ 3 | 3, 0.527) = 0.146) and is vacuous by
   arithmetic.
5. **Loop closure's null space is exact.** `T̂_CA ∘ T̂_BC ∘ T̂_AB = I` for
   any per-image gauge, however large (EXP-012: 36 / 36 VERIFIED / high at
   8, 32, 64 px gauge, edges wrong by up to 115 px). S4 tests per-edge
   coherence only.
6. **Archive throughput.** 100 KB/s measured 2026-09-04; 41.5 MB per
   4096-line window (full 5064-sample lines are what a contiguous byte range
   returns) ⇒ ≈ 7 min per tile, ≈ 1 h for eight. The scout's current
   measurement supersedes this if it differs.
7. **Sample size.** With ≤ 8 frames the held-out set has ≤ 28 pairs before
   overlap exclusion, ≈ 12–20 after. No criterion here reaches the power of
   the 42-pair in-sample census, and none of the p-values reported in §7 will
   be called significant below n = 20.

---

## 7. Reported beside the criteria — not graded

- **R1 — separation test.** `exact_separation_test` on Δincidence vs success,
  per engine, on the held-out set, with n stated. Prediction: same sign as
  in-sample (higher Δinc → failure); p reported, not graded (§6.7).
- **R2 — B4L yield inside the envelope.** On pairs where B1 and B4L both
  succeed at Δinc 12–34°, B4L inliers / B1 inliers. In-sample 5–25×
  (D-047-N1). Prediction: median ratio in [3, 30].
- **R3 — incidence ceiling (P5).** As §2.5.
- **R4 — EXP-012's refuted H2.** Spearman ρ between min-edge inliers and loop
  residual over whatever triplets form. In-sample 0.055 (refuted). No
  prediction; reported for continuity.
- **R5 — resolution ratio per pair** (RD-07 threat: up to 1.5 in-sample) and
  **emission difference per pair** (for §6.3), beside every S3/S4 row.
- **R6 — `assess()` confidence bands** (`high` / `moderate`) and
  `grid_occupancy` (D-055 primary) / `max_uncovered_disc_ratio` (secondary)
  on every VERIFIED edge, so §53 criterion 4 and EXP-015's restated 4′ can be
  read on out-of-sample edges. Reported, not graded: both are already
  recorded as mis-specified (D-057).

---

## 8. What may not happen in Part 2

- **Nothing is re-run after the held-out data has been seen.** Not a pair,
  not an engine, not a threshold, not a bin edge, not a range boundary, not a
  tolerance. The crash policy (§4) permits one restart of an *unfinished* run
  and nothing else.
- **No frame is added or dropped after A1**, and no pair is excluded after
  matching for any reason other than the pre-pixel overlap verdict. A pair
  whose result looks anomalous is reported as anomalous.
- **The arm is not switched after any pixel is fetched.** If arm H runs and
  fails, arm M is not run "as well" inside this stage; it would be a new
  stage with its own Part 1.
- **The held-out rows are never pooled with the 42 in-sample pairs** to
  produce a larger envelope, a smaller p-value or a tighter bound. Part 2 may
  place them side by side; it may not add them.
- **A NOT MET is not converted into a scope qualifier.** "The envelope holds
  on mare" is a legitimate sentence only if it appears beside "S1 NOT MET on
  highlands", never instead of it.
- **No new constant enters `verdict.py`, `agreement.py` or the runner** as a
  consequence of this stage. A change is a separate recorded decision with
  this stage as its evidence.
- **CANNOT CHECK is never reported as MET**, and a criterion that is MET
  because the set could not fail it is reported as "MET, and here is why that
  is not reassurance" beside the criterion.
- **The census listing may not be re-issued with a different box or filter**
  after the first census has been recorded in A1, except by moving to the
  next priority window under §3.4's rule.

---

## 9. What this stage does NOT claim

- **Not an FA or FR measurement.** §0.1. The wrong-pass count is a bound at a
  ~250 px floor on one new window; FR is not measured at all.
- **Not an accuracy claim.** No ground truth; geometry corroboration at its
  floor; loop closure up to per-image gauge; agreement up to shared
  preprocessing. Nothing here is sub-pixel.
- **Not "the envelope holds on highlands"** even if S1 is MET on arm H: one
  window, ≤ 8 frames, ≤ ~20 pairs, one illumination axis (Δincidence only —
  sub-solar azimuth is unavailable from ODE and the labels, as recorded since
  REAL-DATA-01), near-nadir only, native NAC rung only.
- **Not a viewpoint, scale, multi-modal or Chandrayaan-2 result.**
- **Not a verdict calibration.** §53 criterion 3 stays NOT EVALUABLE for FA
  and FR; only its adversarial clause was ever answered (EXP-012), and for the
  wrong reason (E-039).
- **Not a replacement for ISRO's blind set**, whatever it turns out to be
  (§28's separate "blind test" tier).

---

## 10. Ledger and index — what a Part 2 will create

- A `STAGE-INDEX.md` row, a `STAGE_HISTORY.md` row, an `RL-nnn` entry.
- A **D-nnn** row for each frozen prediction that survives or fails, with the
  out-of-sample number beside the in-sample one — including a superseding
  note on **D-051** if S3 fails, and on the RD-07 envelope claim if S1 fails.
- An **E-nnn** row for any harness failure (S0), any restart (§4), and for any
  criterion found to be unanswerable as frozen — reported as E-039 / E-041
  were, beside the criterion, not inside it.
- `docs/PROJECT_GAP_ANALYSIS.md` item B1 and hostile-reviewer point 7
  re-scored; `docs/FINAL_SUCCESS_CRITERIA_AUDIT.md` criterion 3 re-stated with
  the out-of-sample wrong-pass count and the words "FA and FR remain
  unmeasurable".

---

## Amendment A1 — census, frame list, S0 grep record, S5 counts from geometry

**Appended 2026-09-22, after the Part 1 commit (`e8071c4`) and the runner
commit (`cb3fa51`), and BEFORE any image byte was fetched.** It adds records
only; §2, §5, §6 and §8 are untouched. Everything below is derived from ODE
metadata, PDS4 labels and archive index rows — **no pixel of any candidate
frame has been read at the time of writing.**

### A1.1 Two windows were censused and REJECTED at S5 first, in the frozen order

§3.4 fixes the priority order and §3.4's rule says the census moves on only
when S5 fails from geometry. It failed twice, and both records are committed
(`531ad29`) rather than discarded:

| priority | window | outcome | why |
|---|---|---|---|
| 1 | **Apollo 16 / Descartes** (15.50° E, −8.97°) | **S5 NOT MET** | the admissible ladder could not supply the high-Δinc pairs S1's high range needs |
| 2 | **Apollo 14 / Fra Mauro** (342.53° E, −3.65°) | **S5 NOT MET** | `n_ge30` and `n_ge40` both false; the ladder it can build spans 14.89°–62.08° but too few pairs land above 30° |
| **3** | **Apollo 11 / Mare Tranquillitatis** (23.47° E, 0.67°) | **S5 MET — this is the held-out set** | all eight clauses hold, with margin (A1.5) |

**The arm is therefore M (mare), not H (highlands).** §5.3 predicted arm H's
S1c at **LOW** confidence and said *"I record that I would bet against it
there"*; that bet is now **not taken**, because arm H could not supply a set
capable of failing the criterion. §5.3's arm-M column is the operative
prediction: all graded predictions hold, at MEDIUM. **The terrain-transfer
question is not answered by this stage** — §9's scope sentence stands, and
gap item C5 (highlands on real data) stays open. Recording that plainly: the
cheaper, weaker arm is the one the archive allowed.

### A1.2 Separation (S0(b))

Great-circle on a 1 738 km radius from the in-sample ground:
**588.76 km from RD-03** and **577.65 km from RD-04**. §3.3's rule is 50 km;
both clear it by more than 11×.

### A1.3 The ODE census and the funnel

Query: `pt=CDRNAC4`, `minlat=0.65`, `maxlat=0.69`, `westernlon=23.45`,
`easternlon=23.49`, `limit=2000`. Filters exactly as §3.5 froze them.

| stage | count |
|---|---|
| ODE returned | **106** |
| after incidence ≤ 75° and emission ≤ 1.8° | **25** |
| after L/R-of-one-orbit dedupe (lower emission kept) | **21** |
| after the S0(a) untouched grep | **21** (nothing dropped) |
| **admissible** (full 4096 × 2048 tile centred on the target, corner-map inversion, **no clamping**) | **9** |
| chosen by the incidence ladder | **7** |

Twelve of the 21 were excluded because a full tile centred on the target does
not fit inside the frame **unclamped** — the rule RD-07 used to exclude its
frame E1, applied here without exception.

### A1.4 The ≤ 8 frames, and their handedness before any pixel exists

Ladder rungs {20, 25, 30, 40, 50, 60, 70}°, ±5°, nearest unused admissible
frame when a rung is empty. Four rungs were empty and took the nearest frame,
which is why the incidence set is bottom-heavy — **a property of what the
archive holds over this ground, fixed by a rule written before the census.**

| rung | product | incidence | emission | map res (m) | frame lines × samples | tile line0, sample0 | clamped | J determinant | mirrored? |
|---|---|---|---|---|---|---|---|---|---|
| 70 | `nac.m1447850428rc` | **10.88°** | 1.18° | 0.885 | 33792 × 5064 | 23625, 1536 | 0 / 0 | −0.771738 | no |
| 60 | `nac.m188085530rc` | 15.85° | 1.17° | 0.783 | 52224 × 5064 | 29286, 760 | 0 / 0 | −0.550820 | no |
| 20 | `nac.m1177606647lc` | 16.21° | 1.74° | 0.989 | 30720 × 5064 | 13535, 233 | 0 / 0 | **+0.976607** | **YES** |
| 25 | `nac.m1282310415lc` | 29.45° | 1.73° | 0.880 | 52224 × 5064 | 23167, 600 | 0 / 0 | −0.790538 | no |
| 30 | `nac.m1121081627rc` | 40.06° | 1.17° | 0.854 | 52224 × 5064 | 24255, 1267 | 0 / 0 | −0.738601 | no |
| 40 | `nac.m1190561570lc` | 44.94° | 1.72° | 0.840 | 52224 × 5064 | 21898, 1960 | 0 / 0 | −0.729385 | no |
| 50 | `nac.m1157600009rc` | **73.64°** | 1.17° | 1.003 | 52224 × 5064 | 26444, 12 | 0 / 0 | −0.990175 | no |

Acquired 2012-04-03 to 2023-08-28. Resolution ratio across the set
**1.281** (0.783–1.003 m), inside RD-07's in-sample range (R5 will report it
per pair).

**S0(d) — one of the seven frames is mirrored.** The convention is
`siim.ingest.orientation`'s and is not a matter of taste: a normal
north-up-east-right view has a **negative** Jacobian determinant
(`dN/dy < 0` with `dE/dx > 0`), and **a positive determinant is the mirror
image** (`orientation.py`, `mirrored = det > 0`). By that rule
`nac.m1177606647lc` (+0.976607) is mirrored and the other six are not — so
**1 of 7 here against RD-07's 5 of 14**, read from the archive's own corner
columns before any pixel was fetched. `north_up_east_right` is applied to
every frame regardless, as the frozen pipeline requires, and it performs the
left–right flip on that one frame only.

*(Historical note, retained under integrity rule 3: this paragraph first
claimed the opposite — "six of the seven frames are mirrored … load-bearing on
86 % of this held-out set" — by reading the sign backwards. The error and how
it was caught are recorded as **E-047**; the table above always carried the
correct determinants, and no criterion, frame or threshold depended on the
mistaken reading.)*

### A1.5 S5 from geometry — MET, with the margin stated

Counts over the **20 CONFIRMED** pairs (`verify_tile_overlap.py
--require-confirmed`, CONFIRM_AT = 0.50 at the pessimistic end, unchanged):

| clause | required | measured | |
|---|---|---|---|
| `n_<15` | ≥ 5 | **7** | ✓ |
| `n_15–30` | — | 8 | (reported) |
| `n_≥30` | ≥ 5 | **5** | ✓ *exactly at the minimum* |
| `n_≥40` | ≥ 3 | **3** | ✓ *exactly at the minimum* |
| `n_total` | ≥ 12 | **20** | ✓ |
| a frame with incidence ≤ 30° | 1 | 10.88° | ✓ |
| a frame with incidence ≥ 60° | 1 | 73.64° | ✓ |
| CONFIRMED triangles | ≥ 1 | **30** | ✓ |
| frames | ≤ 8 | 7 | ✓ |

**Two clauses sit exactly on their minimum**, which is worth saying out loud
before any result exists: `n_≥30 = 5` and `n_≥40 = 3` are the smallest sets
that make S1's high range and S1c *capable of failing* at all (§5.1's "why
S5's minima are what they are"). So S1's high-Δinc verdict will rest on five
pairs and S1c on three. That is enough to fail and not much more, and Part 2
will not describe a pass there as strong evidence.

**One pair is excluded as unconfirmed** and is listed rather than dropped
silently: `nac.m1157600009rc` ↔ `nac.m188085530rc`. Seven frames give 21
unordered pairs; 20 enter.

Δincidence of the 20 CONFIRMED pairs: 0.36, 4.88, 4.97, 5.33, 10.61, 13.24,
13.60, 15.49, 18.57, 23.85, 24.21, 28.70, 28.73, 29.09, 29.18, 33.58, 34.06,
44.19, 57.43, 62.76°.

### A1.6 S0(a) — the untouched grep

`experiments/EXP-018/exp018_s0_untouched.json`, run at git HEAD
**`531ad29`**, over the whole repository tree: **518 files scanned, 435 read**
(file names and contents), both spellings (`Mnnnnnnnnn[LR]C` and
`nac.mnnnnnnnnn[lr]c`), all **21** post-dedupe candidates.

**Total hits: 0. No frame was dropped.** The held-out set is untouched by
this repository's entire history, by the same test that closed the
"untouched tiles exist" branch in §3.1.

### A1.7 What happens next, in this order

Fetch ≤ 8 tiles (byte ranges, SHA-256 per tile, decimation 2) → manifest with
`retrieved_utc` → re-verify overlap on the recorded tiles → **S0(e)
reproduction gate** → the single run. If the reproduction gate fails, the
stage stops there and reports it (§4 step 6).

---

---

## Part 2

**Run 2026-09-22.** One window, one pass, 20 CONFIRMED pairs × 3 engines = 60
edge rows, 7 triangles, **9.9 min**. Artefacts:
`experiments/EXP-018/exp018_results.json`,
`experiments/EXP-018/rows_tranquillitatis_nue.json`,
`experiments/EXP-018/exp018_s0_gate.json`,
`data/manifests/exp018_tranquillitatis_manifest.json`.

### 6. The answer, in one paragraph

**Of the ten graded predictions this document froze, eight held and two
failed — and the two that failed are exactly the two §5.3 named as the most
likely to fail.** The advertised illumination envelope's hard edge is
**refuted**: registration succeeded out of sample at **Δinc 44.19° and
57.43°**, where in-sample nothing passed above 40°. The engine-agreement
floor is **breached**: two engines disagree by **5.24 px** against a 3.0 px
line and an in-sample maximum of 2.16 px, which is **D-051's own stated
reversal condition**. Against that, the two claims the project leans on
hardest both survived: **zero wrong passes** on all three engines out of
sample, and **7 of 7 triangles closing at 0.40–1.11 px with all 21 edge
verdicts VERIFIED** — the first VERIFIED verdicts this project has produced
on ground it had never opened. The phrase *"every figure is in-sample"* is
retired; the phrase *"nothing passes above 40°"* is retired with it.

### 7. Criteria, answered exactly as frozen

| ID | frozen verdict | the numbers |
|---|---|---|
| **S0** | **MET** (all six clauses) | (a) 0 grep hits for all 21 candidates over 518 files at HEAD `531ad29`, no frame dropped; (b) 588.76 / 577.65 km from RD-03 / RD-04; (c) **20 of 21** pairs CONFIRMED before any matching, the one exclusion named; (d) orientation applied, per-frame Jacobian signs recorded — **but the reported count is wrong, see E-049**; (e) **the gate holds exactly** — 1608 / 2726 / 2138 reproduced as 1608 / 2726 / 2138, RD-03's loop re-composed to **1201.0378963072 px**; (f) runner committed before the fetch, no `src/` change between that commit and the run |
| **S1** | **NOT MET** — through S1c alone | S1a, S1b and S1d are each MET: **no range rejects at the frozen two-sided 0.05** for any engine. **S1c NOT MET:** the point prediction was 0 successes at Δinc ≥ 40°, and there are **3** |
| **S2** | **MET** | **0 wrong passes out of sample on every engine** — B1 0/12 passes, B4L 0/12, B4X 0/17. S2b: `P(X ≥ 0)` = 1.0 against every `p_upper`; §53's FA ≤ 5 % line likewise not rejected. **Weak by arithmetic and said to be** (§5.2: at n_pass = 12 it can only fail at k ≥ 3) |
| **S3** | **NOT MET** — through S3a | **S3a NOT MET:** 34 qualifying pairs; B1–B4L max **1.04 px** (n=10) and B1–B4X max **2.29 px** (n=12) both hold, but **B4L–B4X reaches 5.2406 px** (n=12) against the 3.0 px floor. **S3b CANNOT CHECK** — 0 INCONSISTENT passes occurred, so it is null by construction and is **not** reported as MET |
| **S4** | **MET** | **7 triangles, 7 closing, 21 of 21 edge verdicts VERIFIED.** Residuals **0.4001, 0.4132, 0.4624, 0.5409, 0.8530, 1.0419, 1.1120 px** — every one under the 2.0 px line frozen before the data, and the range sits *inside* EXP-012's in-sample 0.3654–1.3358 px |
| **S5** | **MET, from geometry, before any pixel** | 20 CONFIRMED pairs ≥ 12; 7 at Δinc < 15 ≥ 5; **5 at ≥ 30 and 3 at ≥ 40, both exactly on the minimum**; 30 triangles; 7 frames ≤ 8; incidence 10.88°–73.64° |

### 8. S1c — the envelope's hard edge is a property of 42 pairs, not of the pipeline

Every pair at Δinc ≥ 40°, all three engines, with the geometry verdict:

| Δinc | B1 | B4L | B4X | archive geometry |
|---|---|---|---|---|
| **44.19°** | **318 ✓** | **1337 ✓** | **375 ✓** | CONSISTENT for all three |
| **57.43°** | **10 ✓** | 0 ✗ | **29 ✓** | CONSISTENT for both passes |
| 62.76° | 3 ✗ | 0 ✗ | 6 ✗ | INCONSISTENT (B1, B4X) |

So **B1 passes 2 of 3 above 40° where in-sample it passed 0 of 4**, and B4L
1 of 3. **Not one of those passes is a wrong pass** — every one is consistent
with archive corner geometry, checked after the decision. The 44.19° pair is
not marginal either: 318, 1337 and 375 inliers across three independent
engines.

**What this costs and what it buys, both stated.** It buys a wider envelope:
the deliverable may now say *successes observed to 57.43° Δincidence on mare,
nothing at 62.76°*, which is a better number than the one it replaces. It
costs the generality of the old claim: **"nothing passes above 40°" was a
description of the 42 Mare Serenitatis pairs and did not survive contact with
a second mare window.** §5.3 predicted S1c **MET at MEDIUM on arm M** and
recorded a bet against it only on highlands. The bet was placed on the wrong
arm; the prediction is **WRONG**, and this is the first thing Part 2 says.

**The pooled rate transferred and the shape did not** — the more interesting
half, and it is not a criterion:

| engine | < 15° | 15–30° | ≥ 30° | pooled |
|---|---|---|---|---|
| **B1 out of sample** | 3/7 = **0.429** | 7/8 = **0.875** | 2/5 = **0.400** | 12/20 = **0.600** |
| B1 predicted | 0.786 | 0.632 | 0.222 | **0.595** |
| **B4L out of sample** | 5/7 = 0.714 | 6/8 = 0.750 | 1/5 = 0.200 | 12/20 = **0.600** |
| B4L predicted | 0.786 | 0.632 | 0.111 | 0.571 |

The pooled prediction is almost exactly right (0.600 against 0.595 and 0.571).
Underneath it, **B1's low-Δinc range collapsed from 0.786 to 0.429** — the
closest call in the document, `P(X ≤ 3) = 0.0420` against a 0.025 rejection
bar, a miss in the *downward* direction that the frozen two-sided test does
not catch — while the mid and high ranges over-performed. A pooled figure that
lands while every component moves is a warning about pooled figures, and it is
recorded as one rather than as a success. B4X pooled 17/20 = 0.85 against
0.643 nearly rejects *upward* (`P(X ≥ 17) = 0.0388`).

### 9. S3a — D-051's own reversal condition, fired out of sample

D-051 reads: *"Reversed by: a geometry-consistent all-success triple
disagreeing by > 3 px, or an inconsistent one under 30 px."* The first clause
has now happened.

The breach is **one edge**, `nac.m188085530rc → nac.m1282310415lc` at Δinc
13.60°, and its mechanism is worth more than the number:

| engine | inliers | verdict | archive geometry | occupancy |
|---|---|---|---|---|
| B1 | 5 | **fails** the frozen rule | INCONSISTENT | 0.047 |
| B4L | **9** | passes | CONSISTENT | 0.094 |
| B4X | **13** | passes | CONSISTENT | 0.172 |

**The two engines that disagree by 5.24 px are two marginal passes** — 9 and
13 inliers, one and five above the cutoff of 8 — **both with coverage under
0.18**, i.e. both extrapolating across more than 80 % of the overlap. B1, on
the same pair, fails and is caught by geometry. So the 3 px floor did not fail
where registrations are strong; it failed exactly where the evidence is
thinnest, and the pipeline's other signals were already saying so. The
agreement floor is not wrong about strong pairs — **it was calibrated on a
set that contained no pair this weak that two engines both passed.**

`B1–B4L` (max 1.04 px) and `B1–B4X` (max 2.29 px) both stay inside the floor
across 22 pairs, so the in-sample 2.16 px figure reproduces for every engine
pair involving B1.

§5.3 predicted S3a **MET at MEDIUM** on arm M, naming relief parallax as the
physical risk on highlands. **The prediction is WRONG, and the reason it gave
is not the reason it failed** — this is mare, the emission difference on that
edge is small, and the cause is marginal-pass coverage, not parallax. Both
halves are recorded.

### 10. What held, and why it matters more than what broke

**S2 — zero wrong passes, out of sample, on all three engines.** 41 passes
across B1, B4L and B4X, every one consistent with archive corner geometry.
The in-sample count was 0/46, 1/49, 0/27; out of sample it is 0/12, 0/12,
0/17. This is the project's central safety claim and it transferred. **It
remains a bound at the geometry check's ~250 px floor and is not an FA
rate** (§0.1), and S2b is arithmetically weak (§5.2) — S2a carries the weight.

**S4 — the first out-of-sample VERIFIED verdicts.** Seven triangles formed,
seven closed, 21 of 21 edge verdicts VERIFIED under the unmodified
`assess()`, at 0.4001–1.1120 px against a line frozen before the data. And the
same run reproduces EXP-012's refuted S2 out of sample: the weakest triangle
carries a **10-inlier** edge and still closes at 0.4624 px; Spearman ρ between
minimum edge inliers and loop residual is **0.0901** (in-sample 0.0551). A
marginal edge rides into VERIFIED on a loop that closes around it, on ground
this project had never opened. **Loop closure is exactly blind to per-image
gauge error** (§5.2, EXP-012 §6) and a closing loop is still not an accuracy
statement.

### 11. Reported beside the criteria, not graded (§7)

- **R1 — the Δincidence separation does NOT reproduce for B1.** Exact test on
  20 held-out pairs: B1 **p = 0.575**, B4L p = 0.0784, B4X p = 0.0272, against
  an in-sample pooled **p = 0.0012**. §6.7 forbids calling anything
  significant below n = 20 and this is n = 20, so no significance is claimed
  in either direction — but the honest reading is that **on this window
  Δincidence does not order B1's outcomes at all**, which is the same message
  S1c delivers from the other end. The project's strongest single result is
  the one that looks weakest out of sample.
- **R2 — B4L's yield advantage does not reproduce.** Median B4L/B1 inlier
  ratio **1.36** (range 0.270–21.36, n = 7) against an in-sample 5–25×
  (D-047-N1) and a predicted median in [3, 30]. **The prediction missed**, and
  R2 is reported, not graded, so it changes no criterion.
- **R3 — no data.** The window holds no frame pairing with Δinc ≤ 25° whose
  higher incidence is ≥ 65°, so the incidence-ceiling comparison has n = 0 in
  both decisive bins. Reported as no data, not as agreement.
- **R4 — EXP-012's refutation reproduces**, above.
- **R5** — resolution ratios 1.006–1.130, emission differences 0.01°–0.57°,
  recorded per pair beside every S3/S4 row.
- **R6 — §53 criterion 4 fails out of sample too.** Over the 21 VERIFIED
  edges, `max_uncovered_disc_ratio` runs **0.0346–0.4316 and 6 of 21 exceed
  0.15**; 15 edges are `high` confidence and 6 `moderate`. Under EXP-015's
  restated form 4′, `grid_occupancy` runs 0.125–1.000 and **all 21 clear the
  calibrated floor T = 0.078125**. Both are already recorded as mis-specified
  (D-057) and neither is graded here; the out-of-sample numbers are added to
  that record and change nothing.

### 12. The predictions, graded — including the overall one

| prediction (§5.3, arm M column) | confidence | outcome |
|---|---|---|
| S0 MET | HIGH | **MET** ✓ |
| S1a (B1 ranges) MET | MEDIUM | **MET** ✓ (narrowly, and downward) |
| S1b (B4L) MET | MEDIUM | **MET** ✓ |
| S1c — 0 above 40° | MEDIUM | **NOT MET — WRONG** ✗ |
| S1d (B4X pooled) MET | MEDIUM | **MET** ✓ |
| S2a — 0 wrong passes | MEDIUM | **MET** ✓ |
| S2b — bound | HIGH | **MET** ✓ |
| S3a — ≤ 3 px | MEDIUM | **NOT MET — WRONG** ✗ |
| S3b — CANNOT CHECK | MEDIUM | **CANNOT CHECK** ✓ |
| S4 — loops < 2.0 px | MEDIUM | **MET** ✓ |
| S5 MET **on priority 1** | MEDIUM | **WRONG** ✗ — priority 1 and 2 both failed S5; priority 3 passed |

**The overall prediction was WRONG in the most instructive way available.**
§5.3 closed: *"I predict at least one graded prediction fails on arm H (most
likely S1c or S3a), at MEDIUM confidence; and that all graded predictions hold
on arm M, at MEDIUM confidence."* Arm H was never reachable — it could not
supply a set capable of failing the criteria — and on arm M **two predictions
failed: S1c and S3a, precisely the two named.** The document identified which
of its claims were fragile and was wrong about where the fragility lived. That
is a better outcome than being right, and it is why the arm was fixed in
advance (§8) rather than chosen after.

### 13. What this stage does NOT claim (§9, restated against the results)

- **Not an FA or FR measurement.** 0 wrong passes in 41 out-of-sample passes
  is a bound at a ~250 px floor. **FR: not measurable.** §53 criterion 3 stays
  **NOT EVALUABLE** for both clauses.
- **Not an accuracy claim.** No ground truth, no check points. Loop closure is
  blind to per-image gauge; geometry corroborates at its floor.
- **Not "the envelope reaches 57°".** One mare window, 7 frames, 20 pairs,
  Δincidence only, near-nadir, native NAC rung. What is licensed is:
  *successes were observed at 44.19° and 57.43° on this window, so the
  in-sample "nothing above 40°" is not a property of the pipeline.*
- **Not a highlands or terrain-transfer result.** Arm H was censused twice and
  rejected at S5 from geometry; gap item **C5 stays open** (A1.1).
- **Not a Chandrayaan-2, viewpoint, scale or multi-modal result.**
- **Not a verdict recalibration.** No constant in `verdict.py`, `agreement.py`
  or the runner changed as a consequence of this stage (§8). D-051's reversal
  is recorded as a superseding note (**D-051-N1**), and what replaces the 3 px
  floor is deliberately left to a stage that can calibrate it.

### 14. Ledger and index

- **D-059** — the envelope's upper edge is restated from the held-out result.
- **D-051-N1** — the engine-agreement floor is reversed by its own condition;
  the constant is **not** retuned here.
- **E-049** — S0(d)'s `n_mirrored` counts edge rows, not frames.
- `STAGE-INDEX.md`, `STAGE_HISTORY.md`, `research_log.md` **RL-053**;
  `PROJECT_GAP_ANALYSIS.md` **B1 closed**, hostile-reviewer point 7 answered;
  `FINAL_SUCCESS_CRITERIA_AUDIT.md` criterion 3 restated with the
  out-of-sample wrong-pass count and the words *"FA and FR remain
  unmeasurable"*.
