# EXP-021 — How often the verdict is wrong: false acceptance and false rejection against a reference that is not the archive, on a site split fixed in advance

**Status: COMPLETE — S0, S5 MET; S1, S4, S6 NOT MET; S2 and S3 MET on V ∪ C and NOT EVALUABLE on the held-out site alone (NOT MET as frozen).** Part 2 below.

**Part 1 — pre-registration. FROZEN 2026-09-23, before the validation site's
reference product has been fetched, before any registration against it has
been attempted, before any correctness class, rate or threshold has been
computed on any site, and before the runner exists.** Part 2 is empty until
Part 1 is committed.

**Classification: DELIVERABLE-CRITICAL.** This is item **1** of
`docs/PROJECT_GAP_ANALYSIS.md` §5's corrected path (B3) and item 1 of
`docs/NEXT_SESSION_PLAN.md` §2. §53 criterion 3 is the only one of the five
that is **unmeasurable** rather than failing:

> *"FA and FR are still unmeasurable. Closing them needs ground truth, which
> is item A3 (geodetic check points) and is not on disk."*
> — `FINAL_SUCCESS_CRITERIA_AUDIT.md`, UPDATE 2026-09-22

That sentence was true when written. **EXP-019 changed its premise.** It
registered every REAL-DATA-07 tile to a Kaguya TC ortho mosaic controlled by
another mission's network, and showed that the composition
`A → reference → B` — built from **no A↔B correspondence at all** — agrees with
the recorded direct registration to **0.266 reference px = 2.24 m** (CI95
0.222–0.413, 17 pairs). That composition is an independent answer to *"where
does A land in B"* for every pair whose two frames reach the reference. It is
exactly the ground truth a false-acceptance / false-rejection measurement needs,
at a tolerance ~25× finer than the archive's ~250 px floor that every
wrong-pass count in this repository is stated against.

---

## 0. The requirements this stage bears on, quoted

### 0.1 §53 criterion 3 (verbatim)

> - Verdict FA ≤ 5 %, FR ≤ 20 % on validation sites; zero VERIFIED on the adversarial set.

### 0.2 §54, the failure criterion that rides on it (verbatim)

> - Verdict FA > 10 % on validation: do not ship VERIFIED; ship INCONCLUSIVE/REJECTED only.

**This stage binds itself to §54 now.** If the frozen FA statistic of §4 (S2)
exceeds **10 %** on the validation reading, Part 2 records a D-nnn withdrawing
VERIFIED from the deliverable (demo, CLI, README) until a later stage restores
it. That consequence is written here so that it cannot be argued away later.

### 0.3 What the problem statement asks (§2.2, rejection row)

The rejection requirement is scored in `FINAL_SUCCESS_CRITERIA_AUDIT.md`'s
FINAL RESCORE; this stage supplies the first rate behind it. It does not touch
the other eight §2.2 rows.

### 0.4 What this stage may NOT do to those criteria

- It may not change `assess()`, any constant in `siim.demo.verdict`, or any
  recorded verdict. The verdict under test is the one that shipped.
- It may not adopt a threshold fitted here (S4's cutoff). A fitted value is
  reported; adopting it would be a later, separately pre-registered decision.
- It may not re-open the adversarial clause. EXP-012's **0 of 36** and its
  E-039 caveat stand unchanged; this stage measures FA and FR only.

---

## 1. The question

**When the shipped verdict says VERIFIED, how often is the transform wrong —
and when the transform is right, how often does the verdict refuse it?**
Measured on real lunar pairs, three engines, against a correctness label that
does not pass through the archive's corner geometry and does not pass through
the A↔B correspondence being judged, on a validation site that no threshold in
the verdict was ever fitted on.

---

## 2. What is measured, stated exactly

### 2.1 The correctness label (ground truth, and what kind)

For a frame `F` with a tile at decimation 2 (every REAL-DATA-07 and EXP-018
tile), let `T_F : k2-tile px → reference px` be its registration to a Kaguya TC
Ortho Seamless V2 block, built by **EXP-019's frozen construction**
(`scripts/run_exp019.py`: `degrade_to_gsd` to `k_F = round(8.42315289562 /
g_F)`, PSF FWHM 1.0 coarse px, `north_up_east_right` from the frame's corner
geometry, `register_pair` affine / 3.0 px / seed 0, 2000 m crop margin, flip
when the predicted determinant is negative). For a directed recorded edge
`A → B`:

```
G_AB = T_B^-1 ∘ T_A          (k2-tile px of A → k2-tile px of B)
```

`G_AB` uses correspondences **A↔R and B↔R only**. Its measured agreement with
recorded direct edges is EXP-019's S3: median 0.266 reference px.

**Leg admission (frozen).** `T_F` is admitted as ground truth at one of two
tiers:

| tier | rule | role |
|---|---|---|
| **A (primary)** | the B1 leg passes (`n_inliers > 8`) **and** the B4L leg passes **and** the two legs agree: median over a 64-px grid on the matched tile of `‖T_B1(x) − T_B4L(x)‖ ≤ 0.5` reference px | every criterion |
| **B (sensitivity)** | the B4L leg passes and tier A does not hold | S5 only, reported beside, never in S1–S4 |

Tier A needs two independent engines to put the frame in the same place to
half the correctness tolerance, so a leg error alone cannot move a correct
edge across the line. Tier B exists because the reference is photometrically
normalised to i = 30°, so tier A is **biased toward the frames that register
easily** (§6.3); tier B is the only handle on that bias that the data permit.

**Disclosed before the fact:** EXP-019's recorded artefact, which this Part 1
has read, shows B1 legs passing on 12 of 20 Serenitatis tiles and B4L legs on
16 of 20; the agreement statistic of tier A has **not** been computed on any
frame. The correctness classes and rates below have not been computed on any
pair.

### 2.2 Correctness classes

For each directed recorded edge with a transform and with both frames admitted,
`e_AB` = the **median** over an 8-px grid on A's k2 tile, restricted to grid
points that `G_AB` maps inside B's k2 tile, of `‖D_AB(x) − G_AB(x)‖`, where
`D_AB` is the row's `transform_matrix_original_pixels` (E-040: that is the
k2-tile frame; `transform_matrix` is not). Converted to reference px by
`× 2 · g_B / 8.42315289562`, as EXP-019 did.

**The overlap is decided by the ground truth, never by the estimate.** EXP-019's
S3 decided it by the direct estimate, which drops a wildly wrong transform from
the population; for an FA measurement that would remove exactly the cases being
counted. Pairs with fewer than 100 grid points inside B under `G_AB` are
excluded **by geometry** and listed.

| class | rule |
|---|---|
| **CORRECT** | `e_AB ≤ 1.0` reference px (8.42 m) |
| **AMBIGUOUS** | `1.0 < e_AB ≤ 3.0` reference px |
| **WRONG** | `e_AB > 3.0` reference px (25.3 m) |
| **NO ESTIMATE** | the row has no transform |

**Disclosed before the fact:** EXP-019's S3 table (17 pairs, recorded) was read
when 1.0 was chosen; its correct pairs sit at 0.077–0.839 reference px and its
one failed edge at 21.0. The 0.839 pair sits close to the line, which is why S5
re-scores everything at 0.5 and 2.0.

### 2.3 The verdict, at two levels

**L1 — acceptance at the edge.** Accepted ⇔ the recorded `pass` field, which is
`n_inliers > 8` (D-023). With no loop and no engine agreement supplied,
`assess()` returns REJECTED exactly when `n_inliers ≤ 8` (`verdict.py`, the
`decisive_against` branch); S0(ii) checks `pass == (n_inliers > 8)` on every row
used.

**L2 — VERIFIED.** A **triangle** is three frames of one window whose three
edges are all recorded for one engine with `pass` true — EXP-012's and
EXP-018's population. Its residual is `siim.evaluation.gtfree.loop_closure`
(step 16) on the recorded `transform_matrix` legs, a leg inverted when its
recorded direction is opposite, with the shape rule of
`scripts/run_exp012.py::run_triplet` (the recorded source of the (a, b) edge).
Given three passing edges and no engine agreement, `assess()` returns VERIFIED
exactly when the residual is `< 2.0` px. The unit of L2 is the **edge**: an edge
is **VERIFIED** if it lies in at least one VERIFIED triangle — the permissive
reading, and therefore the conservative one for FA. The (edge, triangle) unit
is reported beside.

An edge is **L2-reachable** if it lies in at least one triangle of three
recorded edges of one engine that have transforms, whatever their pass state:
a third overlapping image exists, so VERIFIED was possible in principle.

### 2.4 The rates

Per site reading, per level, per engine and pooled:

| rate | definition |
|---|---|
| **FDR** (*"how often VERIFIED is wrong"*) | (accepted ∧ WRONG) / (accepted ∧ class ≠ NO ESTIMATE); **FDR_cons** also counts AMBIGUOUS in the numerator |
| **FAR** (*"how often a wrong transform gets through"*) | (accepted ∧ WRONG) / WRONG — at L2 the denominator is WRONG edges that are L2-reachable |
| **FRR** | (not accepted ∧ CORRECT) / CORRECT — at L2 the denominator is CORRECT edges that are L2-reachable |

Every rate is reported with its counts and an exact two-sided **95 %
Clopper–Pearson** interval. **"Met" is judged on the point estimate** (§53 states
a rate), and beside every verdict the stage says whether the interval's upper
bound also clears the line (**demonstrated**) or not.

**Why FA is scored on both FDR and FAR.** The project's own wrong-pass tables
(`MEASURED_WRONG_PASS`, E-038) count *wrong passes per pass* — an FDR. The
biometric definition conditions on truth — an FAR. Picking the kinder one after
the data would be the move the audit forbids, so **the FA clause is MET only
if both are ≤ 5 %** wherever each is defined. An undefined FAR (no WRONG edge in
its denominator) does not block the clause. It is reported as the vacuity it
is (S6).

### 2.5 The site split

| role | site | ground truth | why it has that role |
|---|---|---|---|
| **Calibration C** | Mare Serenitatis, REAL-DATA-07 windows RD03 + RD04 (14 frames, 20 tiles) | EXP-019's recorded legs, rebuilt; no re-matching | the project's development ground: every real-data stage since REAL-DATA-03 looked at it |
| **Validation V** | Mare Tranquillitatis, EXP-018's held-out window (7 frames, 20 confirmed pairs, ~800 km from C) | **new**: a Kaguya TC tile fetched after this commit (§3.1) | opened once, by EXP-018, on 2026-09-22 — after every verdict threshold was fixed |

**No threshold in the status decision was ever fitted on either site.** The
inlier cutoff 8 comes from EXP-002 (synthetic, D-023) and the loop line 2.0 px
from EXP-003 (synthetic). Coverage moves confidence, not status, and engine
agreement is not supplied here. So **both** sites are validation sites for the
*frozen* verdict in §53's sense, and C differs from V only in having been
*looked at*. The §53 clause is therefore scored on **two readings**, and must
hold on both:

- **strict:** V alone;
- **pooled:** V ∪ C.

If the strict reading is not evaluable (sample minima, §4), the clause is
reported as *"MET/NOT MET on V ∪ C; NOT EVALUABLE on the held-out site
alone"*. It is never reported as MET on the pooled reading alone.

The split's other job — *thresholds fitted on one site and reported on the
other* — is S4: the inlier cutoff is fitted on C and carried to V.

**Primary engine: B1**, the pipeline's default (`register_pair(engine="B1")`).
B4L and B4X are reported per engine and pooled beside every criterion. The
pooled-engine unit (engine, edge) is **not** independent across engines: three
engines judge the same pair. That is stated wherever a pooled figure appears.

---

## 3. Data, fixed in advance

### 3.1 The validation reference (to be fetched after this commit)

`TCO_MAPs02_N03E021N00E024SC` — SELENE (Kaguya) TC Ortho Map Seamless V2.0,
3° × 3° tile, 0–3° N, 21–24° E, from
`https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-tc-5-ortho-map-seamless-v2.0/lon021/data/`.
A HEAD request on 2026-09-23 returned **200, 233 280 000 bytes** for the .img and
200 for the .lbl. No byte of image data has been read. EXP-018's target ground
point (23.47° E, 0.67° N) lies inside it.

Fetched **once** (E-050: DARTS ignores Range), with the whole file's SHA-256
recorded, then cut by rule:

- **REF block:** the bounding box of the seven tiles' index corners plus
  **2 km** on every side (EXP-019 §2.2 step 3).
- **NULL block:** the same longitude span, latitude band **[top + 0.825°,
  top + 1.825°]**, where *top* is REF's north edge (≥ 25 km clear). If that band
  leaves the tile, the band **[bottom − 1.825°, bottom − 0.825°]** is used. If
  neither fits, the null clause is NO DATA.

Grid from `LINE/SAMPLE_PROJECTION_OFFSET`, exactly as
`scripts/acquire_exp019_reference.py`, and `MapBlock` with global graticule
edges and block offsets in `row0`/`col0` (E-052).

### 3.2 The recorded rows this stage reads, frozen

| site | rows | filter |
|---|---|---|
| C | `experiments/REAL-DATA-07/rows_rd03_nue.json`, `rows_rd04_nue.json` | `north_up is True`, engine ∈ {b1, lg, xf}; direction from `edge` (E-036); no row with `reproduces_recorded` |
| V | `experiments/EXP-018/rows_tranquillitatis_nue.json` | engine ∈ {b1, lg, xf}; direction from `edge` |
| C legs | `experiments/EXP-019/exp019_results.json` → `cells[*]` (B1) and `second_engine[*]` (B4L), `measured_to_block_matrix` | arm R, NAC only |
| reproduction | `exp019_results.json` → `criteria.S3.pairs` (17); `experiments/EXP-012/exp012_results.json` → `triplets` (13); `experiments/EXP-018/exp018_results.json` → `triangles` (7) | as recorded |

The un-suffixed REAL-DATA-07 row files (the superseded quarter-turn run) are
not read.

---

## 4. Success criteria — FROZEN

| ID | Criterion | MET if |
|---|---|---|
| **S0** | **Harness, reproduction and the ground truth's own false-accept control.** | (i) the C legs rebuilt from EXP-019's recorded matrices reproduce EXP-019's **17** S3 `median_k2_px` values to **≤ 1e-6 px** each; (ii) `pass == (n_inliers > 8)` on every row used; (iii) the L2 construction reproduces EXP-012's **13** and EXP-018's **7** recorded loop residuals to **≤ 1e-6 px** and their statuses exactly; (iv) V's grid gate — label corners to **< 0.5 px**, a 10⁴-point round trip to **< 1e-9°** — and V's byte provenance recorded before any registration; (v) **drift gate:** one EXP-019 B1 leg (`RD03/nac.m1271742202lc`, recorded **253** inliers) re-run through the unchanged construction reproduces its count **exactly**; (vi) **V null:** **0 of 7** B1 legs against the NULL block pass; (vii) every Jacobian sign read from `siim.ingest.orientation`, never from a print label (E-047) |
| **S1** | **Ground truth exists on the held-out site.** | **≥ 4 of 7** V frames admitted at tier A, **and ≥ 6** B1 edges on V classified CORRECT or WRONG. Otherwise the strict reading of S2–S4 is **NOT EVALUABLE for want of ground truth**, stated as such |
| **S2** | **§53's FA clause.** | On the B1 L2 population, **FDR ≤ 5 %** and (where defined) **FAR ≤ 5 %**, on **both** readings of §2.5, each reading needing **≥ 10** VERIFIED edges with a class ≠ NO ESTIMATE. A reading below that minimum is NOT EVALUABLE. **FDR > 10 %** on either reading triggers §0.2 |
| **S3** | **§53's FR clause.** | On the B1 L2 population, **FRR ≤ 20 %** on **both** readings, each needing **≥ 10** L2-reachable CORRECT edges. A reading below that minimum is NOT EVALUABLE |
| **S4** | **A threshold fitted on one site holds on the other.** | On C, pooled over the three engines at L1, `c*` = the smallest integer `c ∈ [3, 50]` such that the rule *accept ⇔ n_inliers > c* gives **FAR ≤ 5 %**; needs **≥ 5** WRONG rows on C, else NOT MET for want of data. MET if, on V at L1 pooled over engines, the rule at `c*` gives **FAR ≤ 5 % and FRR ≤ 20 %**, with **≥ 3** WRONG and **≥ 10** CORRECT rows on V. `c*` beside 8 is reported whatever happens, and is **not adopted** |
| **S5** | **The answer is not an artefact of where the lines were drawn.** | The MET / NOT MET / NOT EVALUABLE outcome of S2 **and** S3, on both readings, is **unchanged** under each of four re-scorings: CORRECT at ≤ 0.5 and ≤ 2.0 reference px (WRONG line moved to 1.5 and 6.0 in step); ground truth at tier A ∪ B; ground truth from B1 legs alone (EXP-019's S3 population rule) |
| **S6** | **The FA measurement is exercised, not vacuous.** | On V, pooled over the three engines, **≥ 3 hard negatives** — rows that are WRONG **and** have `n_inliers > 8`, i.e. wrong transforms the inlier rule did not stop. Fewer means every FA figure on V rests on wrong edges the cheapest rule already rejected, and S2 cannot have failed there |

### 4.1 Parameter count against constraint count (E-041)

| statistic | fitted parameters | constraints | null / reference |
|---|---|---|---|
| each leg `T_F` | 6 (affine) | ≥ 9 inliers by the rule, and tier A's second engine | the NULL block (S0(vi)), **built from the property** "can the construction place a frame where it is not" — no permutation |
| correctness `e_AB` | 0 | ≥ 100 grid points | the tier-A leg agreement, 0.5 ref px ≤ half the CORRECT line |
| FDR / FAR / FRR | 0 — counts | the stated minima | none needed: each rate is a count of real wrong or real correct transforms. No rate is compared with a shuffled or synthetic population |
| `c*` (S4) | **1** integer | ≥ 5 WRONG + all CORRECT rows on C | evaluated on a disjoint site. That is the whole point of the criterion |
| tolerance, leg gate | 0 fitted, 2 chosen | — | disclosed in §2.1–§2.2; S5 re-scores at both neighbours |

**What the null is.** §53's FA asks whether the verdict separates wrong
transforms from correct ones. The only honest null is **real wrong
transforms**, and S6 exists because real data may not contain enough of them
where it matters. EXP-012's adversarial set perturbs correct edges per edge,
which is the subspace loop closure is built to catch (E-039). It is not
re-used here as a substitute for S6.

### 4.2 Predicted outcome per criterion, recorded now so it can be wrong

- **S0 MET** — HIGH for (i), (ii), (iv), (v), (vii). **(iii) MEDIUM-HIGH (80 %)**:
  the frame and shape conventions of the recorded L2 runs are reconstructed,
  not imported. **(vi) MEDIUM-HIGH**: EXP-019's null was 0 of 21.
- **V legs:** B1 passes on **5–6 of 7** V frames (the 73.64° frame fails; 10.88°
  is the boundary at |i − 30°| ≈ 19°). Tier A admits **4–6** (MEDIUM).
- **S1 MET** — MEDIUM (65 %).
- **S2:** **FDR = 0** on both readings — HIGH (85 %). This matches 0 wrong
  passes in 41 out of sample (EXP-018) and 7 of 7 VERIFIED triangles, now at an
  8.42 m tolerance instead of ~250 px. **FAR undefined** at L2 on V — MEDIUM-HIGH
  (75 %): no WRONG edge will sit in an all-pass triangle. **Strict reading NOT
  EVALUABLE** — MEDIUM (60 %): V has 7 frames, and tier A will leave fewer than
  10 VERIFIED B1 edges. **Pooled reading MET.** So the overall S2 prediction is
  *"MET on V ∪ C, NOT EVALUABLE on V alone"*.
- **S3:** **FRR at L2, B1, pooled reading: 10–35 %, point ≈ 20 %** — a coin
  flip, MET at 50 %. At L1 FRR is predicted **≤ 10 %**: correct transforms
  almost never have ≤ 8 inliers. EXP-019 recorded exactly one (6 inliers,
  0.433 reference px), and it will be counted.
- **S4:** `c*` **between 4 and 8** — MEDIUM (wrong real transforms carry 3–8
  inliers in every recorded stage). **S4 NOT MET for want of data** on V (fewer
  than 3 WRONG rows at L1) — MEDIUM (55 %).
- **S5 MET** — MEDIUM (65 %). The risk is S3, whose point estimate may sit near
  20 %.
- **S6 NOT MET** — HIGH (85 %). **This is the prediction that matters most.**
  Real mare data will hold no wrong transform with more than 8 inliers on V,
  which means §53's FA clause, however it scores, is **not tested against the
  failure it was written for** on this site. The only instances of that failure
  on record are synthetic (EXP-012's gauge probe, 36 of 36 VERIFIED while
  14–115 px wrong) and one WAC-rung wrong pass (REAL-DATA-08, 9 inliers, 28 px).
- **Overall:** S0 MET; S1 MET narrowly; S2 MET on the pooled reading and not
  evaluable on V alone; S3 a coin flip; S4 not evaluable on V; S5 MET; S6 NOT
  MET. **If S2, S3, S4 and S6 all pass, that is itself suspicious** and Part 2
  must say why it is not.

---

## 5. Physical limits, in numbers

| quantity | value |
|---|---|
| reference pixel | 8.42315289562 m |
| CORRECT line | 1.0 ref px = **8.42 m** ≈ 3.9 k2 px ≈ 7.8 native NAC px |
| WRONG line | 3.0 ref px = **25.3 m** ≈ 11.7 k2 px |
| ground-truth precision | 0.266 ref px median (EXP-019 S3), the **sum** of two legs' errors |
| archive discrimination floor it replaces | ~250 px at k2 ≈ **540 m** (EXP-018), 84–116 px native (EXP-013) |
| gain in resolving power | **≈ 20–60×** finer than every wrong-pass count on record |
| invisible here | an error below 8.42 m on the ground — up to ~8 native px. **A CORRECT edge is correct to 8 m, not to a pixel** |
| V site size | 7 frames, 20 confirmed pairs, 30 triangles, ≤ 60 engine-edges |
| C site size | 14 frames on 20 tiles, 42 pairs, ≤ 126 engine-edges |

---

## 6. What may not happen in Part 2

### 6.1 No line moves

1.0 / 3.0 reference px, the 0.5 ref px leg gate, 5 %, 10 %, 20 %, the sample
minima (4 frames, 6 edges, 10 VERIFIED, 10 CORRECT, 5 and 3 WRONG, 3 hard
negatives), and `c ∈ [3, 50]`.

### 6.2 No population moves

- No frame, pair or row enters or leaves except by the rules in §2 and §3.2.
  A V frame whose legs fail is **not replaced**, and its edges are listed as
  *no ground truth*.
- No re-match of any recorded direct edge. The only new matching is V's legs,
  V's null cells and the S0(v) drift gate.
- The adversarial set is not re-run and not re-scored.
- Nothing in `src/` changes because of a result here. If S2 triggers §0.2, the
  withdrawal of VERIFIED is a D-nnn **and** a separate commit that touches the
  deliverable, never `assess()`.

### 6.3 Biases that are stated, not corrected

- **Spectrum bias.** Ground truth exists only where a frame registers to an
  i = 30° reference. Those frames also register easily to each other, so the
  population under-represents the hard cases: the 66–75° frames, where real
  failures live. FRR is biased **low** and FA's opportunities are reduced.
  Tier B (S5) is the one handle on this, and it is partial.
- **Engine correlation.** Pooled-engine figures count one pair up to three
  times.
- **One terrain class.** Both sites are mare; C5 stays open.

### 6.4 Vacuity is reported beside, never folded in

A criterion that passes because its hard cases are absent — S2 with an
undefined FAR and S6 NOT MET, or S3 on a population that tier A has already
filtered to easy frames — is reported as *MET, and here is why that is not
reassurance*, beside the criterion.

---

## 7. What this stage explicitly does NOT claim

- **Not geodetic check points.** The label is a second mission's product, not
  surveyed ground, and "correct" means *agrees with that product to 8.42 m*.
  Manual check points (gap analysis item 4) remain unbuilt.
- **Not an FA rate against the per-image gauge.** Loop closure's exact null
  space (ADR-0011 N1) is untouched. EXP-012's gauge probe (36/36 VERIFIED while
  wrong) remains the measured value there, and a direct `G_AB` would *see* such
  an error, but only if one occurs in the data.
- **Not a highland, viewpoint, scale or multimodal result.**
- **Not a new verdict.** `c*` is not adopted and nothing is retuned.
- **Not a claim about VERIFIED at fine resolution.** The tolerance is 8.42 m.

---

## 8. Reported beside the criteria, not part of any

- The full confusion table (class × status) per site, level and engine.
- L1 and L2 rates on C alone (the development site's own figures).
- Every AMBIGUOUS edge by name, with its `e_AB`, inlier count and
  `delta_incidence_deg`.
- `e_AB` against `n_inliers` and against Δincidence for every classified row,
  so a reader can see whether the verdict's positive evidence tracks
  correctness.
- For every VERIFIED edge: its `e_AB` in reference px, metres and k2 px — the
  first per-edge accuracy distribution of VERIFIED on real data.
- The (edge, triangle) unit rates beside the edge unit.
- B4L legs on V, the tier-A agreement per frame, and the V null cells under B4L.
- The recorded geometry verdict (archive check) beside each correctness class:
  how often the archive's CONSISTENT agrees with the reference's CORRECT.

---

## 9. Ledger and index — what a Part 2 will create

A `STAGE-INDEX.md` row, a `STAGE_HISTORY.md` standing-table row, an `RL-058`
research-log entry, a line in `FINAL_SUCCESS_CRITERIA_AUDIT.md` and
`PROJECT_GAP_ANALYSIS.md` scoring **both** scorecards, and: a **D-nnn** stating
what §53 criterion 3 now reads (MET / NOT MET / NOT EVALUABLE, per clause and per
reading), a **D-nnn** under §0.2 if FDR exceeds 10 %, a superseding note on
`MEASURED_WRONG_PASS`'s floor if the stage replaces it, and an **E-nnn** for any
defect S0 exposes. Superseding notes, never edits.

---

## Part 2

**Written 2026-09-23 after the run, against Part 1 as committed (`EXP-021 Part 1`,
the commit before this one).** Artefact `experiments/EXP-021/exp021_results.json`
(213 s, CPU), log `run.log`. The validation reference was fetched by
`scripts/acquire_exp021_reference.py` (log `acquire.log`; the first attempt broke
at 124 of 233 MB and is kept as `acquire_attempt1_broken.log`). Product SHA-256
`08b073eda662d971…`, REF block rows 7895–8882 (987 × 738 px), NULL block rows
1325–4927 (north band, 1.63–2.63° N), DUMMY fraction 0.0000 in both.

### 10. The answer, in one paragraph

**The verdict was never wrong where it could be checked, and it could be checked
almost nowhere that matters.** At the frozen tier-A ground truth, every labelled
edge on both sites is **CORRECT**: 39 of 39 engine-edges, including 13 of 13 for
B1. The primary B1 VERIFIED population scores **FDR 0 / 12** and **FRR 0 / 12** on
the pooled reading, with a Clopper–Pearson upper bound of **26.5 %** on each, and
no wrong transform anywhere in the population to compute an FAR from. On the
held-out site alone the ground truth **did not reach**: B1 registers only **3 of
7** Tranquillitatis frames to the Kaguya reference, **one of them at i = 29.45°,
the reference's own standard geometry, fails**, and tier A admits **2** frames
and **1** B1 edge. So §53's FA and FR clauses are **MET on V ∪ C and NOT
EVALUABLE on the held-out site alone**, and the reason is not the verdict but
the construction Part 1 chose for ground truth: an admission rule that requires
B1 to register the frame to an i = 30° reference selects exactly the frames that
also register to each other. **That population contained no negatives at all**
(E-058). The one reading that admits the hard frames (tier A ∪ B, S5) finds
**20 wrong transforms, and all but one have 3–8 inliers**. The inlier rule
stopped them, and **0 of 84 VERIFIED engine-edges is wrong by more than 25 m**.
But **15 of those 84 are AMBIGUOUS** (8.8–19.8 m), clustered on three frames
whose own two legs disagree by 0.5–1.6 reference px. A frozen rule cannot say
whether that is leg noise or a per-image error the loop cannot see, and this
part does not pretend to.

### 11. Criteria, answered exactly as frozen

| ID | verdict | the number |
|---|---|---|
| **S0** | **MET** | (i) 17/17 EXP-019 S3 medians rebuilt from the recorded matrices, max \|diff\| **0.0 px**; (ii) 186 rows, **0** violations of `pass == (n_inliers > 8)`; (iii) EXP-012's 13 and EXP-018's 7 loop residuals rebuilt from recorded rows, max \|diff\| **0.0 px**, statuses identical; (iv) V grid: corners **0.0008 px**, round trip **6.7e-16°**; (v) drift gate **253 = 253**; (vi) V null **0 of 7** B1 passes (B4L beside: 0 of 7, max 5 inliers); (vii) signs from `siim.ingest.orientation.handedness` |
| **S1** | **NOT MET** | **2 of 7** V frames at tier A (bar 4), **1** B1 edge classified (bar 6). The strict reading of S2–S4 is **NOT EVALUABLE for want of ground truth** |
| **S2** | **NOT MET as frozen** — *MET on V ∪ C; NOT EVALUABLE on the held-out site alone* | B1 L2 pooled: **FDR 0 / 12** (CI95 0–26.5 %), FDR_cons 0 / 12, **FAR undefined (0 WRONG edges reachable)**. Strict: 0 / 1. **Not demonstrated**: the upper bound is 26.5 % against 5 %. §0.2's withdrawal line (FDR > 10 %) is **not triggered** on either reading |
| **S3** | **NOT MET as frozen** — *MET on V ∪ C; NOT EVALUABLE on the held-out site alone* | B1 L2 pooled: **FRR 0 / 12** (CI95 0–26.5 %). Strict: 0 / 1. **Not demonstrated** against 20 % |
| **S4** | **NOT MET for want of data** | **0 WRONG rows on C** at tier A (bar 5), so `c*` cannot be fitted; V has 0 WRONG and 3 CORRECT rows. At the frozen cutoff 8: FRR_C **0 / 36**, FRR_V **0 / 3**, both FARs undefined |
| **S5** | **MET, and here is why that is not reassurance** | S2 and S3 read *MET on V ∪ C / NOT EVALUABLE on V* under all four re-scorings (§12). Their outcome strings are stable because they count WRONG. Under tier A ∪ B the **AMBIGUOUS** count, which the frozen FDR excludes, rises from 0 to **7 of 29** B1 VERIFIED edges |
| **S6** | **NOT MET** | **0** hard negatives on V (bar 3), **0** on C. **No WRONG edge exists in either L2 population** at tier A. Predicted, and the most important line in the table |

**§53 criterion 3, restated (D-068).** FA and FR move from **unmeasurable** to
**measured on the pooled reading, not evaluable on the held-out site alone, not
demonstrated, and never exercised against a wrong transform at tier A**. The
criterion stays **NOT MET**. Nothing was re-scoped to change that: the pooled
reading was frozen as insufficient on its own, and it is reported that way.

### 12. S5 in full — where the wrong transforms were hiding

| re-scoring | B1 L2 pooled FDR | FAR | FRR | S2 / S3 outcome |
|---|---|---|---|---|
| **primary** (tier A, 1.0 / 3.0) | 0 / 12 | 0 / 0 | 0 / 12 | MET on V ∪ C; NE on V |
| CORRECT ≤ 0.5, WRONG > 1.5 | 0 / 12 | 0 / 0 | 0 / 12 | same |
| CORRECT ≤ 2.0, WRONG > 6.0 | 0 / 12 | 0 / 0 | 0 / 12 | same |
| **tier A ∪ B** | **0 / 29** | **0 / 9** | **2 / 24** | same |
| B1 legs alone (EXP-019's rule) | 0 / 17 | 0 / 1 | 1 / 18 | same |

**The tolerance does not matter at tier A: every tier-A edge sits below 0.414
reference px, so moving the line from 0.5 to 2.0 changes nothing.** What matters
is which frames have ground truth. Read at tier A ∪ B, pooled over engines and
both sites (`exp021_s5_tier_ab_reading.json`: the recorded legs re-read, with no re-match), the
population finally contains negatives:

- **20 WRONG engine-edges.** Every one involves a tier-B frame (66.9–69.8°,
  42–48° frames that fail against most partners, and three Tranquillitatis
  frames). **19 have 3–8 inliers and were REJECTED at L1. The twentieth is the
  only hard negative in the stage:** Tranquillitatis `m188085530rc → m1282310415lc`
  under **B4X, 13 inliers, 3.25 reference px (27 m)**, archive-CONSISTENT, passed
  at L1, **not VERIFIED**. It sits 0.25 px over the WRONG line, while B1 (5
  inliers) rejected the same pair and B4L (9 inliers, 2.99 px) landed on the
  AMBIGUOUS side of it.
- **0 of 84 VERIFIED engine-edges is WRONG** (CI95 upper 4.3 %; not independent
  across engines, and not the frozen criterion).
- **15 of 84 VERIFIED engine-edges are AMBIGUOUS** (FDR_cons **17.9 %**; B1 alone
  **7 / 29 = 24.1 %**). All 15 end on one of three tier-B frames: RD04
  `m1341069775rc` (B1 leg failed, B4L's disagrees with it by 237 px), RD04
  `m1335207975rc` (legs disagree by **1.32** ref px) and Tranquillitatis
  `m1282310415lc` (B1 leg failed). **The three engines agree with each other on
  each of those edges** to 0.04–0.18 ref px (e.g. 2.17 / 2.30 / 2.35 on
  `m1447850428rc → m1282310415lc`), **and the loops close**. So the direct edges
  are mutually consistent, and the disagreement is between them and a chain
  through a single-engine leg. On the six frames where both legs exist and tier A
  still refused them, the legs disagree by **0.51–1.57** ref px, the same size as
  the ambiguity. **Leg noise on hard frames fully accounts for it. A per-image
  gauge — loop closure's exact blind spot — would look identical.** This stage
  cannot tell the two apart. That is why tier A was frozen as primary, and why
  the 17.9 % is printed here and not folded away.
- **The two false rejections at tier A ∪ B are instructive and different.**
  RD03 B1 `m1271742202lc → m1452560468lc`: **6 inliers, correct to 0.53 ref px**,
  refused by the inlier rule, the one EXP-019 had already seen. RD03 B1
  `m1236465772rc → m1175268993rc`: **8239 inliers, correct to 0.36 ref px, never
  VERIFIED**, because both frames fail against every third frame in the window,
  so no all-pass triangle exists. The second is not a verdict error; it is a
  system that correctly refuses to call anything VERIFIED without a third image.

### 13. What VERIFIED is worth, on the ground, for the first time

The 36 VERIFIED engine-edges with a tier-A label (both sites, three engines)
agree with the Kaguya chain to **0.077–0.414 reference px — median 0.180 =
1.51 m, p95 0.375, max 3.48 m**. Every one is also archive-CONSISTENT (36/36;
the 3 labelled non-VERIFIED edges are archive-INCONCLUSIVE). This is the first
per-edge accuracy distribution of VERIFIED on real data at a resolution finer
than the archive floor. **What it does not claim:** it covers only the frames
tier A admits, it is a two-leg disagreement and not an absolute error, and it
says nothing about the frames where VERIFIED is hardest to earn.

### 14. The predictions, graded — including the ones that were wrong

| Part 1 prediction | outcome |
|---|---|
| S0 MET, (iii) at 80 % | **right** — both rebuilds exact to 0.0 px |
| V: B1 passes 5–6 of 7 | **wrong — 3 of 7.** The frame at i = 29.45° (Δ to the reference's standard geometry **0.55°**) fails with 3 inliers; 10.88° passes with 96 |
| V: tier A admits 4–6 | **wrong — 2** |
| S1 MET at 65 % | **wrong** |
| S2: FDR = 0 on both readings at 85 % | **right** (0 / 12, 0 / 1) |
| S2: FAR undefined at L2 on V at 75 % | **right, and more so than predicted** — undefined on C too |
| S2: strict NOT EVALUABLE at 60 %; overall *"MET on V ∪ C, NE on V"* | **right** |
| S3: FRR at L2 10–35 %, point ≈ 20 % | **wrong — 0 / 12.** Tier A left no hard frame in which a correct edge could fail to find a closing triangle |
| S3: L1 FRR ≤ 10 % | **right** (0 / 13) |
| *"EXP-019's 6-inlier correct edge will be counted"* | **wrong** — its frame is tier B, so it is counted only in S5 (§12) |
| S4: `c*` in 4–8 | **unobservable** — no WRONG row on C |
| S4 NOT MET for want of data on V at 55 % | **right outcome, wrong reason** — it failed for want of data on **C** |
| S5 MET at 65 % | **right** |
| S6 NOT MET at 85 % | **right** |

**Nine right, five wrong, one unobservable, one right for the wrong reason.**
Every wrong prediction is the same mistake: Part 1 treated *"B1 registers the
frame to a photometrically normalised reference"* as a property of illumination
geometry alone. At i = 29.45° it should be the easiest case in the stage, and it
fails.

### 15. Defects found, and what is NOT rewritten

- **E-057 — two runner defects before the artefact existed.** (a) The first run
  died building a Transform from a failed 4-inlier leg whose recorded matrix is
  projective (bottom row `[4.7e-05, -3.2e-06, 1]`). The helper now reads the
  model from the matrix (`run_died_v1.log`). (b) The S0(i) summary printed
  `max |diff| inf px -> MET`. An exact 0.0 difference is falsy, so
  `x or np.inf` turned perfect agreement into infinity. The gate's own logic
  used `is not None` and was right. The run was stopped **before any artefact
  was written**, the summary fixed and the run repeated (`run_killed_v2.log`).
  Nothing frozen changed, and no statistic was read from either dead run beyond
  the gate lines printed in their logs.
- **E-058 — the ground-truth admission rule was correlated with the thing being
  measured.** Tier A admits a frame only if B1 registers it to the reference, and
  B1 registering a frame is strongly associated with that frame's edges being
  correct. The admitted population therefore contained **no negatives**. That
  made S4 unfittable, S6 unreachable and every FAR undefined, a consequence
  Part 1 predicted for S6 and failed to see for S4 and for the FAR on C. It is
  **the fifth member of E-041's family** (E-041, E-046, E-053, E-056): a
  pre-registration that checked its parameter count but not whether its
  population *could contain* the event its criteria count. **Not fixed, by
  choice.** The criteria are reported as they read, and S5's tier A ∪ B reading
  shows where the negatives were.

The artefact is not rewritten. Its summary line is accurate. §12's tier A ∪ B
enumeration is a re-reading of the recorded legs through the runner's own
functions, with no re-match, committed as `scripts/exp021_tier_ab_reading.py`.
That script asserts every frame's tier reproduces the artefact before it counts
anything, and its output is `experiments/EXP-021/exp021_s5_tier_ab_reading.json`
(a second artefact beside the first, never a rewrite of it).

### 16. What this stage does NOT claim (Part 1 §7, restated against the results)

- **Not an FA rate.** No wrong transform existed where the frozen ground truth
  could see it. *"0 / 12"* is a count of VERIFIED edges that were right, not a
  probability that VERIFIED is right.
- **Not a validation-site result.** One edge on the held-out site had frozen
  ground truth.
- **Not evidence against the verdict either.** No VERIFIED edge was WRONG in any
  reading, and the only hard negative was stopped.
- **Not a resolution of the 15 AMBIGUOUS VERIFIED edges.** Leg noise and a
  per-image gauge both fit them.
- **Not a change to anything shipped.** `assess()`, `MEASURED_WRONG_PASS`, the
  demo and the CLI are untouched; §0.2 was not triggered.

### 17. What would make criterion 3 evaluable, in the order the data suggests

1. **Ground truth on the hard frames at tier-A quality**: a reference whose
   illumination matches the hard frames (Kaguya TC has morning/evening
   mosaics; the seamless product is normalised to i = 30°), or a second
   independent reference, so the 66–75° and 42–48° frames get two agreeing legs.
   This is the only route to a population that contains its own negatives
   (E-058).
2. **Manual check points on the three AMBIGUOUS-carrying frames**, which decide
   leg noise versus a per-image gauge directly. The same work is gap-analysis
   item 4.
3. **A larger held-out site.** Seven frames give at most 21 pairs; a site with
   ≥ 12 frames spread across 10–75° would clear every sample minimum even at
   tier A's admission rate.

### 18. Ledger and index

`STAGE-INDEX.md` row; `STAGE_HISTORY.md` standing-table row; `research_log.md`
**RL-058**; `DECISION_LEDGER.md` **D-068** (criterion 3's reading);
`ERROR_LEDGER.md` **E-057**, **E-058**; the audit's FINAL RESCORE gains a
2026-09-23 (EXP-021) line for both scorecards; `PROJECT_GAP_ANALYSIS.md` B3
status. §0.2 was not triggered, so no withdrawal decision exists.
