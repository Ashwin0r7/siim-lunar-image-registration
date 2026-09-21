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

*Empty until the Part 1 above is committed. Appended before any pixel byte is
fetched; may add records, may not alter §2, §5, §6 or §8.*

---

## Part 2

*Empty. Written only after this Part 1 is committed.*
