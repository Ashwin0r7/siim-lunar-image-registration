# EXP-024 — Criterion 4 from each edge's own inlier layout

**Part 1 — pre-registration. FROZEN 2026-09-24, before the runner exists and
before any statistic of this stage has been computed. No edge has been
re-matched and no inlier position has been read for this stage.** Part 2 is
empty until Part 1 is committed.

**Classification: DELIVERABLE-CRITICAL.** This is the successor measurement
EXP-022 Part 2 §12 named (D-069): *"the direct bound from each edge's own
inlier positions (not recorded by REAL-DATA-07; needs a re-run that records
them)"*. EXP-022 answered §53 criterion 4 NOT MET on three named edges, but
through **proxy cells**: synthetic subsets sharing an edge's inlier count and
occupancy, not the edge's actual point layout. Seven of the 22 distinct edges
had no comparable proxy rows at all, leaving 7 of 13 VERIFIED triplets
undecided. This stage replaces the proxy with the measurement it stood in
for.

---

## 0. What was known before this was written (disclosed)

- EXP-022's full Part 2, including the three named edges (9 inliers at
  3.93 px, 28 at 1.66 px, 68 at 1.04 px, all p95-of-p99 in proxy cells), the
  seven unsampled distinct edges (108–5 392 inliers, occupancy 0.67–0.94),
  σ_N = 0.7202 px, and T″ = 0.359. **Every prediction in §3.2 is conditioned
  on this knowledge and says so.** No number of THIS stage's form — a
  per-edge bound from the edge's own layout — exists anywhere yet.
- EXP-012's artefact (`experiments/EXP-012/exp012_results.json`): 22 distinct
  edges behind the 39 VERIFIED edge-rows, each with `n_inliers` reproduced
  exactly by its S5 control, and each edge-row's `coverage_occupancy` in its
  verdict metrics. The inlier **positions** were not written to any artefact;
  that absence is the reason this stage exists.
- The 32 mare tiles in `data/processed/mare_serenitatis/` are on disk;
  EXP-012's matching ran on them on this machine.

## 1. The question

**Under noise at the recorded level, does each VERIFIED edge's own inlier
layout — its actual recorded point positions, not a proxy with the same count
and occupancy — bound worst-case local error at 1 px?**

## 2. What is measured

### 2.1 The edges, re-matched with their positions kept

- **Edges:** the 22 distinct edges of EXP-012 (which carry all 39 VERIFIED
  edge-rows across the 13 triplets). The list is read from
  `exp012_results.json` `edges`; nothing may enter or leave it.
- **Matching:** exactly EXP-012's S5 control, by importing the matching
  machinery of `scripts/run_exp012.py` (itself `run_exp007.py`'s preparation:
  `stretch(decimate(raw, 2))`, `north_up_east_right`, B1 at the frozen
  settings, seed 0). The only change is that the RANSAC **inlier source
  positions** are written to the artefact, per edge, in the oriented k2
  source frame.
- **Harness identity (S0):** each edge's re-matched `n_inliers` must equal
  the recorded count **exactly** (EXP-012 S5's own bar), and
  `coverage_metrics(inlier_src_positions, shape, roi=None).grid_occupancy`
  must equal the edge-row's recorded `coverage_occupancy` **exactly** (same
  implementation, same inputs; occupancy is an exact multiple of 1/64). A
  single mismatch on either stops the stage.

### 2.2 The direct bound, per edge (S5's form from EXP-022, on real layouts)

- **Truth:** EXP-014's transform, unchanged:
  `similarity(1.03, deg2rad(4.0), 11.0, -7.0)`.
- **Noise:** destinations = `truth(positions) + N(0, σ_N²)` iid per axis,
  σ_N = `median(fit_rmse of the 39 VERIFIED edge-rows) / sqrt(2)` read from
  `exp012_results.json` — EXP-022's frozen formula, re-read and recorded by
  the runner, not copied from EXP-022's output.
- **Draws:** 200 per edge per arm. RNG: `default_rng(20260924 + edge_index)`
  where `edge_index` is the edge's position in the artefact's `edges` list;
  the same generator serves that edge's draws in order.
- **Response per draw:** fit an **affine** to the noisy correspondences (all
  of the edge's inliers), then the dense endpoint error against the truth on
  a 16-px grid over the valid (finite) region of the edge's prepared source
  tile, and its **p99** — EXP-022 §2.1's response, with the subset replaced
  by the edge's own layout. Where `scripts/run_exp022.py` has the function,
  it is imported; anything restated must be numerically identical on a shared
  test row.
- **The edge's number:** the **95th percentile of p99 over the 200 draws**,
  in k2 pixels. The bound is **1.0 px**. Both constants are EXP-022's,
  unchanged.

### 2.3 Null from the property (E-039)

The property a pass claims is that the edge's **spatial arrangement** bounds
extrapolation error. The null removes exactly that and keeps everything else
(count, tile, truth, noise, draws): the edge's own positions **shrunk toward
their centroid by a factor of 8** (`c + (p − c)/8`). A measurement that
cannot tell an edge's layout from its shrunk copy cannot support any claim
about layouts.

### 2.4 What is deliberately not run

The **seventh layout family** D-069 also named (uniform over a random k-cell
subset) exists to fill proxy cells. Once every edge is measured from its own
layout, no proxy cell is needed to answer criterion 4 for these edges; the
family remains open only for a future re-calibration of a floor, which this
stage does not attempt. T″ is neither recomputed nor used.

## 3. Success criteria — FROZEN

| ID | Criterion | MET if |
|---|---|---|
| **S0** | Harness | (i) all 22 edges re-match with `n_inliers` equal to the recorded counts exactly; (ii) recomputed `grid_occupancy` from the kept positions equals each edge-row's recorded `coverage_occupancy` exactly; (iii) σ_N is recorded with its formula and source, and equals EXP-022's recorded 0.7202 px to 1e-4 (same formula, same artefact); (iv) the truth transform is EXP-014's constant; (v) the runner refuses to overwrite an existing artefact |
| **S1** | The direct bound, every edge | for **every** one of the 22 distinct edges, p95 of p99 **< 1.0 px**. The 39 edge-rows inherit their distinct edge's number |
| **S2** | The seven undecided edges are decided | each of the seven distinct edges EXP-022 left unsampled (its §8 S1 list) has its direct number recorded, and **all seven are < 1.0 px** |
| **S3** | The proxy is graded | for the three edges EXP-022 named (9, 28, 68 inliers), the direct number and the proxy p95 are reported side by side, and Part 2 states for each whether the proxy's NOT-MET call **stands or falls** under the direct measurement. This criterion is MET when the comparison is recorded — the *direction* is S1's business, not S3's |
| **S4** | The property is present | the shrunk-layout null exceeds the edge's own p95 on **≥ 20 of 22** edges |

**Consequence rule (frozen).** §53 criterion 4's written form ("gap ≤ 0.15")
stays **NOT MET** whatever happens here; this stage cannot flip it and does
not try. What this stage changes is the **completeness of the answer**: from
*"25 of 39 edge-rows evaluable by proxy, 3 over, 11 not evaluable"* to a
direct number for **all 39**, and from *"3 of 13 triplets clear, 3 carrying a
failing edge, 7 undecided"* to a decided count for all 13. If S1 is NOT MET,
the failing edges are named beside every VERIFIED claim that cites their
triplets, exactly as EXP-022's three are now.

### 3.1 Parameter count against constraint count (E-041)

| statistic | fitted | constraints | null |
|---|---|---|---|
| affine per draw | 6 | ≥ 9 correspondences (the smallest edge) | — |
| per-edge p95 | 0 | 200 draws | shrunk-layout arm (§2.3) |
| σ_N | 0 fitted, read | 39 recorded values | — |
| S0 occupancy identity | 0 | 39 recorded values | — |

**Can the population contain the events its criteria count? (E-058)** Yes.
S1 can fail: the 9-inlier edge's proxy cell sat at 3.93 px, and its own
layout occupies 5 of 64 cells. S1 can also pass per edge: 14 edge-rows at
occupancy 1.0 sat at 0.09–0.15 px by proxy. S4 can fail: at the largest
counts the shrunk fit is still over-determined, and if the shrunk arm's p95
does not rise above the own-layout p95 there, the null catches it.

### 3.2 Predicted outcome, with confidence (conditioned on §0)

- **S0 MET** — HIGH (85 %). EXP-012 reproduced all 22 counts exactly on this
  machine; the environment is pinned. The riskiest clause is (ii): if
  EXP-012's `assess` received a roi this document did not find, the identity
  fails and the stage stops — which would be the right outcome.
- **S1 NOT MET** — HIGH (85 %): the 9-inlier edge (proxy 3.93 px) is expected
  over the bound from its own layout (90 %), the 28-inlier edge (proxy
  1.66 px) over at 70 %, and the 68-inlier edge (proxy 1.04 px, marginal) over
  at **50 %** — its own `half`/`ring`-like layout may bound better than the
  proxy cell that contained only `half` and `ring` rows.
- **S2 MET** — MEDIUM-HIGH (75 %): the seven unsampled edges have 108–5 392
  inliers on nearly-uniform-with-holes layouts; predicted direct numbers
  0.1–0.8 px.
- **S3 MET** — HIGH (90 %) by construction; the interesting line is whether
  the 68-inlier edge's proxy call **falls**, predicted 50 % as above.
- **S4 MET** — HIGH (85 %); the two largest edges (5 392, 5 437) are the
  likeliest of the ≤ 2 permitted misses.
- **Triplet outcome:** 13 of 13 decided; predicted **9–10 clear on all three
  edges, 3–4 carrying at least one edge over the bound**.

## 4. What may not happen in Part 2

- No line moves: 1.0 px, the 95th percentile, 200 draws, the 16-px grid, the
  shrink factor 8, the ≥ 20 of 22 bar, σ_N's formula, the truth constant.
- The edge list is EXP-012's, closed. A failed S0 identity stops the stage;
  it is never patched around by re-deriving positions another way.
- `assess()`, D-055, D-057, D-069 and EXP-022's artefacts are untouched.
- Arm results may not be mixed: the shrunk arm decides only S4.

## 5. What this stage does NOT claim

- **Not real cross-illumination error.** The truth is synthetic and the noise
  is iid at the recorded level, without its spatial structure — EXP-022's
  limitation, inherited and unchanged.
- **Not accuracy of any real edge.** A pass says the layout can support a
  1 px worst-case bound under that noise model, nothing more; a failure says
  the layout cannot, not that the edge is wrong (EXP-021 labelled none of the
  39 WRONG).
- **Not a new verdict rule and not a floor.** Nothing is adopted into
  `assess()`; T″ is not touched; criterion 4's written form stays NOT MET.
- **Not other terrain.** Mare Serenitatis tiles only.

## 6. Ledger — what Part 2 will create

A `STAGE-INDEX.md` row, a `STAGE_HISTORY.md` row, an `RL-nnn` entry, a D-nnn
recording criterion 4's completed answer (which edges and triplets are clear,
which are not, from their own layouts), and an E-nnn for any defect found.
Both scorecards are re-scored in the audit and the gap analysis.

---

## Part 2

**Written 2026-09-24 after the run, against Part 1 as committed (`8ebd78e`).**
Artefacts: `experiments/EXP-024/exp024_results.json`,
`exp024_inlier_positions.npz` (SHA-256 `e27d49e5…` in the results file — the
positions REAL-DATA-07 never recorded now exist on the record), `run.log`
(82 s). Nothing is rewritten.

### 7. The answer, in one paragraph

**Measured from their own layouts, 20 of the 22 distinct edges (37 of 39
edge-rows) bound worst-case local error under 1 px at recorded noise, and two
do not: the 9-inlier edge at 5.42 px and the 28-inlier edge at 1.59 px.
Criterion 4's answer is now complete — no edge is judged by proxy or left
unsampled — and it stays NOT MET, on two named edges instead of three.** The
seven edges EXP-022 could not sample sit at 0.07–0.51 px. The 68-inlier edge,
EXP-022's "most useful line", comes out **within** the bound at 0.83 px where
its proxy cell said 1.04 px: a cell holding only `half` and `ring` layouts
overestimated a real layout that is neither. That contradiction does not
weaken D-069's floor-insufficiency finding — it sharpens it. At occupancy
≈ 0.44 and 68 points there now exist, on the record, one layout at 0.83 px
(the edge's own) and one at 1.04 px (EXP-022's synthetic counterexample):
**identical count, identical occupancy, opposite sides of the bound**, which
is the cleanest demonstration yet that occupancy alone cannot decide the
criterion. Of the 13 VERIFIED triplets, **11 are now demonstrably clear on
all three edges** (previously 3), and 2 carry a failing edge — the triplets
containing the 9- and 28-inlier edges. The shrunk-layout null exceeded the
edge's own bound on 22 of 22 edges (5.4× to 8.2×), so the measurement sees
spatial concentration everywhere, including at 5 437 points.

### 8. Criteria, answered exactly as frozen

| ID | verdict | the number |
|---|---|---|
| **S0** | **MET** | (i) all 22 re-matched edges reproduce their recorded `n_inliers` **exactly** (9 to 5 437); (ii) recomputed `grid_occupancy` equals the recorded `coverage_occupancy` on **39 of 39** edge-rows exactly; (iii) σ_N = **0.7202 px** by the frozen formula, within 1e-4 of EXP-022's recorded value; (iv) truth is EXP-014's constant; (v) overwrite refused by construction |
| **S1** | **NOT MET** | 20 of 22 distinct edges < 1.0 px (0.074–0.874). Over: RD04 `m1271742202lc → m1335207975rc` (**9** inliers, occupancy 0.078) at **5.4245 px**; RD04 `m1299958135lc → m1363396554rc` (**28**, 0.281) at **1.5899 px** |
| **S2** | **MET** | all seven previously-unsampled edges decided, all within: 108 → 0.498, 190 → 0.507, 265 → 0.381, 293 → 0.399, 2 597 → 0.124, 2 726 → 0.128, 5 392 → 0.074 px |
| **S3** | **MET** (recorded) | 9-inlier: direct 5.42 vs proxy 3.93 — call **stands** (direct is worse). 28-inlier: 1.59 vs 1.66 — **stands**. 68-inlier: **0.830 vs 1.042 — the proxy call falls**; the real layout bounds where the cell's `half`/`ring` stand-ins did not |
| **S4** | **MET** | shrunk-layout null exceeds the edge's own p95 on **22 of 22** edges (bar 20), including both largest (5 437: 0.074 → 0.523; 5 392: 0.074 → 0.561) |

**Consequence rule, applied as frozen:** §53 criterion 4's written form stays
**NOT MET**. The completed answer replaces EXP-022's partial one everywhere
the three edges were named: the failing set is now **two** edges, and every
VERIFIED claim citing the two affected triplets carries them.

### 9. Predictions against outcomes

| prediction (§3.2) | outcome | |
|---|---|---|
| S0 MET — HIGH (85 %) | MET, identities exact on all 61 checks | right |
| S1 NOT MET — 85 % | NOT MET | right |
| 9-inlier over — 90 % | 5.42 px, over | right |
| 28-inlier over — 70 % | 1.59 px, over | right |
| 68-inlier over — 50 % | **0.83 px, within** | wrong at the stated coin-flip |
| S2 MET — 75 %, direct numbers 0.1–0.8 px | MET, 0.074–0.507 px | right |
| S3: the 68 proxy call falls — 50 % | it fell | right |
| S4 MET — 85 %, likeliest misses the two largest edges | MET **22 of 22**; the largest edges held with 7× margin | right, wrong about the risk |
| 9–10 triplets clear, 3–4 carrying | **11 clear, 2 carrying** | wrong in both counts, in the favourable direction |

Seven right, one wrong, one right-with-wrong-detail, one wrong-favourably.
The favourable misses are stated as misses; a prediction wrong in the
project's favour is still wrong (integrity of §3.2).

### 10. Defects

- **E-061** — the first runner rebuilt the 22-edge inventory by *pair
  membership* in each window's recorded rows instead of by run_exp012's own
  enumeration. The pair `m1271742202lc / m1212932972lc` exists in **both**
  windows with different tiles and different recorded counts (1406 in RD03,
  1679 in RD04), so the rebuilt inventory matched it four times and keyed
  positions by edge string alone, colliding across windows. Caught reading
  the live log during S0, before any artefact existed; the run was stopped
  and the runner corrected to reproduce the source's enumeration with a
  per-index assertion against EXP-012's `edges` list. No artefact was
  written by the flawed run. *(A prior start also died on a broken log pipe;
  likewise before any artefact.)*

### 11. What this changes

- **§53 criterion 4:** stays NOT MET; its answer is **complete**. From
  *"3 named edges over by proxy, 25 evaluable within, 7 unsampled"* to
  **"2 named edges over from their own layouts, 20 within, none unsampled;
  11 of 13 triplets clear"**. D-070, with D-069-N1 recording that D-069's
  reversal condition fired partially (the 68-inlier edge left the failing
  set) without reversing the verdict.
- **The floor-insufficiency finding (D-069) stands, with a sharper
  example:** two recorded layouts at the same (count, occupancy) on opposite
  sides of the bound.
- **The two failing edges' triplets** (`{2932972lc, 1742202lc, 5207975rc}`
  and `{2932972lc, 9958135lc, 3396554rc}`) are the ones any VERIFIED claim
  must flag; the other 11 are clear on all edges.
- `assess()`, D-055, D-057 and every EXP-022 artefact: untouched.

### 12. What this stage does NOT claim (§5 unchanged, plus)

- Not that the 9- and 28-inlier edges are wrong, and not that the 68-inlier
  edge is accurate: the truth is synthetic, the noise iid. The claims are
  about what each layout can bound under that model, in both directions.
