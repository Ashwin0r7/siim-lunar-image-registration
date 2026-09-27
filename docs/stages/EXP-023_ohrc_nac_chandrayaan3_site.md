# EXP-023 — OHRC ↔ LRO NAC at the Chandrayaan-3 landing site

**Part 1 — pre-registration. FROZEN 2026-09-23. No census script, runner or
fetch code exists yet, no NAC label, index row or pixel from this site has been
read, and no statistic of this stage has been computed.** Part 2 stays empty
until Part 1 is committed.

**Classification: DELIVERABLE-CRITICAL.** This is the problem statement's own
case. It registers Chandrayaan-2's highest-resolution optical camera (OHRC,
0.26 m) to LRO NAC, and the project has never done it. REAL-DATA-09 reported
OHRC `no_data`: *"Reaching it needs a fresh NAC acquisition there, and no NAC
tile from that region is on disk."* This stage is that acquisition, at the
fallback site REAL-DATA-09 Part 1 §3 named in advance (*"the Chandrayaan-3
landing region (≈ 69.4 S, 32.3 E; OHRC stereo and NAC coverage exist)"*).

---

## 0. What was known before this was written (disclosed)

- **The two OHRC labels**, read in full (metadata only; no OHRC pixel has
  been decoded for this stage):

  | | obs1 `…20240425T1012478407` | obs2 `…20240425T1603031918` |
  |---|---|---|
  | UTC start | 2024-04-25 10:12:47.8 | 2024-04-25 16:03:03.2 |
  | size (scans × pixels) | 91 945 × 12 000, UnsignedByte | 90 148 × 12 000 |
  | pixel resolution | 0.26 m | 0.26 m |
  | solar incidence / azimuth | **78.476° / 303.535°** | **79.097° / 304.448°** |
  | roll / pitch | −6.81° / +12.32° | +13.29° / −12.29° |
  | altitude | 102.33 km | 101.91 km |
  | `reference_data_used` | **LRO** | **LRO** |

- **Each label carries two corner sets.** `System_Level_Coordinates` are the
  SPICE-predicted corners. `Refined_Corner_Coordinates` are corners refined by
  ISRO **against LRO reference data**. The two sets differ by about 0.09° in
  latitude, roughly 2.7 km. The geometry grid (`g_grd`, a lat/lon node every 100
  pixels and 100 scans) starts at the **refined** upper-left corner
  (32.2695117 E, −68.9859415). **Consequence, stated before any number
  exists: agreement between this stage's registration and OHRC's refined
  geometry is not independent of LRO.** It is corroboration by a geometry
  already tied to the reference, and it is labelled that way everywhere.
- **The two observations are a stereo pair over the same ground.** Their
  refined footprints overlap almost completely. The Sun moved 0.6° in
  incidence and 0.9° in azimuth between them. Their pointing differs by about
  32° (roll −6.8 → +13.3, pitch +12.3 → −12.3).
- **Azimuth convention.** Read clockwise from north, 303.5° puts the Sun in
  the north-west. That is the only possibility at this latitude in the local
  afternoon, and the afternoon is fixed independently: incidence **increases**
  from obs1 to obs2, so the Sun is setting. On a sphere, an afternoon Sun at
  78.5° incidence at this point lies at azimuth 298–308° for any sub-solar
  latitude in ±1.5°, and 303.5° is inside that range. **Disclosed anomaly:**
  on a sphere the afternoon azimuth should *decrease* over the 5.84 h, but the
  labels show +0.91°. The label's azimuth reference therefore cannot be
  confirmed from the labels alone. §2.3 is built to survive this.
- **An unrecorded metadata look, earlier in this session.** An ODE query
  around the site returned roughly 140 NAC CDR products, several with
  incidence within 1° of 78.48°. Product ids seen: `m1450039289rc`,
  `m1486555640rc/lc`, `m1450025248lc`, `m1450053330rc/lc` and
  `m1524018718lc`. **No azimuth, label, index row or pixel was read**, and the
  query was not saved. The census in §2.2 reruns it under the frozen rules and
  records it. The ids above get no preference.

## 1. The question

**Does a Chandrayaan-2 OHRC image register to LRO NAC at the same ground, and
does the registration close a three-image loop tightly enough for the frozen
verdict to call it VERIFIED?**

## 2. What is measured

### 2.1 Target and windows (frozen)

- **Target point: (32.319 E, −69.373)**, the published Chandrayaan-3 (Vikram)
  landing position. It lies inside both refined OHRC footprints, 1.27 km
  (obs1) and 1.52 km (obs2) from the nearer swath edge. No criterion uses the
  lander; the point only fixes where the windows are centred.
- **NAC tile:** EXP-018's rule, unchanged. 4 096 lines × 2 048 samples at
  decimation 2, or 8 192 × 4 096 at decimation 4 when the ODE map resolution is
  under 0.6 m. Centred on the target by corner-map inversion, fully inside the
  frame with no clamping, and prepared by the recorded pipeline:
  `stretch(decimate(raw, k))`, then `north_up_east_right`.
- **OHRC window:** one per observation, cut from the full-resolution image. It
  is the ground rectangle of the Na tile's footprint (§2.2), found by inverting
  the refined `g_grd` grid at the tile's corners, with a 5 % margin and clipped
  to the swath. It is degraded to the NAC tile's coarse GSD by
  `degrade_to_gsd(…, psf_fwhm_coarse_px = 1.0)` at the integer factor
  `round(GSD_coarse / 0.26 m)` (REAL-DATA-09's P2 rule: the finer image is
  degraded to the coarser). It is then stretched and oriented by the **same**
  `north_up_east_right`, fed with corners built from the refined grid, so
  handedness is computed, never assumed.
- **Engines:** B1 (RootSIFT, the frozen pipeline) is primary. B4L runs beside
  it. Affine model, 3.0 px RANSAC, seed 0, and `N_INLIERS_FAILURE_RULE`
  unchanged.

### 2.2 NAC selection (frozen, from metadata only, before any pixel)

Candidates are ODE `CDRNAC4` products whose footprint intersects a 0.04° box
around the target, filtered in this order:

1. **Containment:** a full tile centred on the target fits unclamped.
2. **Emission ≤ 20°** from the archive index. EXP-018's ≤ 1.8° is not used:
   OHRC itself looks 14–19° off nadir, and a nadir-only rule would test a
   narrower case than the data allows.
3. **Sun-vector separation θ ≤ 10°**, where
   `cos θ = cos i_N cos i_O + sin i_N sin i_O cos(az_N − az_O)`. The NAC `i_N`
   and `az_N` come from `solar_geometry_at` on the index's
   `SUB_SOLAR_LATITUDE` / `SUB_SOLAR_LONGITUDE`. That module's
   `incidence_agreement` guard must reproduce the index `INCIDENCE_ANGLE` to
   ≤ 0.5°, or the frame is excluded. The OHRC values are obs1's label numbers,
   azimuth read clockwise from north.
4. **L/R of one orbit is one frame**; the lower emission is kept.

**D-029's 75° incidence ceiling is set aside here, deliberately and on the
record.** It exists to stop a Δincidence-*maximising* selector from choosing
the terminator (E-026). This selector *minimises* the difference to an image
taken at 78.5°, and the ceiling would exclude the only illumination OHRC has.
D-049's evidence that frames at 66.9–74.7° failed against every partner on
Serenitatis is the main reason S2 might fail (§3.2).

**Tiers and ranking.** θ ≤ 3°, then ≤ 6°, then ≤ 10°. Frames come from the
lowest non-empty tier, and within a tier they are ranked by emission
ascending, then θ. **Na** is the first-ranked frame and **Nb** the second, from
a different orbit, taken from the same tier or, if that tier holds one frame,
from the next. **How §2.3's anomaly is survived:** θ ≤ 10° cannot select a
morning frame, because a morning Sun at this incidence sits about 110° away in
azimuth. Within the afternoon, a misread azimuth reference changes θ by a few
degrees at most, which moves a frame between tiers but not into or out of the
admissible set.

**Overlap is established before pixels (D-035).** For each chosen NAC tile,
≥ 50 % of its ground footprint (NAC corner map) must lie inside **both** OHRC
refined footprints. Otherwise the frame is dropped and the next-ranked frame
is taken.

### 2.3 The image set and the loops

The images are O1 and O2 (the OHRC windows), Na and, if it exists, Nb. **Every
edge is estimated independently on its own image pair (E-021).** A closing
edge is never derived from the other two.

- **Primary triangle:** **{O1, Na, Nb}** if Nb exists, otherwise
  **{O1, O2, Na}**. This is fixed from the census, before any pixel. O1 comes
  first because it has the smaller off-nadir angle. {O1, Na, Nb} is preferred
  because it avoids the 32° OHRC–OHRC stereo edge. O1's own distortion enters
  both of its legs, so the loop cancels it. That is the gauge caveat of E-039,
  stated in §5.
- **Secondary:** every other triangle among {O1, O2, Na, Nb} that contains an
  OHRC → NAC edge. Each is reported with its status; none is a criterion.
- **Loop residual:** `siim.evaluation.gtfree.loop_closure` over the first
  image's shape, in **coarse NAC pixels** (the pair's coarse frame), exactly as
  REAL-DATA-09's loop runner does.
- **Verdict:** `assess()` on the primary triangle's OHRC → NAC edge, given the
  triangle's loop residual. It is unchanged: VERIFIED needs more than 8 inliers
  and a loop under 2.0 px.

### 2.4 Geometry corroboration (not independent; §0)

For each OHRC → NAC edge, the predicted transform is an affine fit to a 9 × 9
grid. Each grid node is carried OHRC window pixel → lon/lat (refined `g_grd`,
bilinear) → NAC pixel (NAC corner map), both in the oriented coarse frames. The
disagreement is the median over the overlap between the registered and the
predicted transform. The floor is REAL-DATA-09's: `150 m / GSD_coarse` plus a
1.2 % bilinear term on the tile diagonal. CONSISTENT means median ≤ floor.
The **system-level** corners are carried through the same construction, and
their disagreement is reported in metres beside the refined one. That is a
measurement of OHRC's own SPICE pointing against NAC, and it is not a
criterion.

### 2.5 Null from the property (E-039)

The property a pass claims is *the two windows show the same ground*. The null
removes exactly that and keeps everything else: same sensors, same
illumination, same terrain class, same pipeline.

- **N-a:** O1 against a NAC tile from Na, the same size, displaced 8 km
  along-track. Whichever direction fits unclamped is used; if neither fits, the
  displacement is made in Nb.
- **N-b:** an O1 window displaced 8 km along-track inside obs1, against Na.

Non-overlap of each null pair is confirmed from geometry before any pixel. The
null is listed, but not fetched, if the census cannot place it.

## 3. Success criteria — FROZEN

| ID | Criterion | MET if |
|---|---|---|
| **S0** | Harness | (i) both OHRC `.img` files match their label's MD5, and ingest through the unmodified `siim.ingest.pds4` reader with the file-size identity exact; (ii) each `g_grd` corner node equals the label's **refined** corner to ≤ 1e-5°, and the system-level offset is recorded in metres; (iii) OHRC handedness is computed from the refined grid and applied by `north_up_east_right`; (iv) every chosen NAC frame passes `incidence_agreement` (≤ 0.5°); (v) NAC bytes are SHA-256-manifested; §2.2 is applied exactly as written; runners refuse to overwrite |
| **S1** | The data exists | ≥ 1 admissible NAC frame (Na) with overlap confirmed from geometry against both OHRC footprints. **If NOT MET, S2–S5 are NO DATA** and the stage reports the census funnel |
| **S2** | OHRC registers to NAC | B1 passes (`n_inliers > 8`) on **both** O1 → Na and O2 → Na, and both are **CONSISTENT** with the refined geometry (§2.4) |
| **S3** | **The primary triangle is VERIFIED** | all three edges pass, and `assess()` on the primary triangle's OHRC → NAC edge returns **VERIFIED** (loop < 2.0 coarse px) |
| **S4** | The pass rule discriminates here | B1 **fails** (`n_inliers ≤ 8`) on both null pairs, N-a and N-b. If either passes, S2 and S3 are reported beside *"a pass does not discriminate same ground at this site"* |
| **S5** | A second engine agrees | B4L passes both O1 → Na and O2 → Na, with median dense disagreement from B1 **< 2.0 coarse px** over the overlap. The verdict is unchanged: engine agreement caps at INCONCLUSIVE |

**What each outcome means for the scorecards (frozen now):**

- **S3 MET** gives the project's first VERIFIED Chandrayaan-2 ↔ NAC result.
  §53 criterion 2 **still cannot be MET by this stage.** Its check-point clause
  needs an independent reference, and none exists at 69.4° S on disk (SLDEM
  stops at ±60°, and Kaguya TC at this latitude would starve under EXP-016's
  N\*). IIRS was never delivered. The criterion stays NOT MET, with its OHRC
  sub-clause recorded as *VERIFIED by loop closure, check points unavailable*.
- **§2.2 rows this can move:** the scale row gains a real cross-sensor OHRC
  rung (0.26 m against the NAC coarse GSD, reported as a ratio). The viewpoint
  row gains a real, not synthetic, viewing difference, reported as Δemission
  per edge, plus the 32° OHRC stereo edge. Neither row flips to MET on one
  site.

### 3.1 Parameter count against constraint count (E-041)

| statistic | fitted | constraints | null |
|---|---|---|---|
| affine per edge | 6 | `n_inliers` > 8 by the rule (expected ≫ 100) | — |
| predicted transform (§2.4) | 6 | 81 grid nodes × 2 | — |
| loop residual | 0 | dense grid over the first image | S4 is the null for the pass it rests on |
| B4L agreement | 0 | dense grid over the overlap | — |
| S4 nulls | 0 | 2 pairs | built from the property (§2.5) |

**Can the population contain the events its criteria count? (E-058)** Yes, on
every line. S2 can fail: 78.5° incidence, 14–19° of viewing difference and
D-049's precedent. S3 can fail: parallax the affine cannot absorb, and eight
months or more between acquisitions (the lander's blast zone is one known
change). S4 can fail: long shadows over a crater field are repetitive enough
that a false pass is plausible.

### 3.2 Predicted outcome, with confidence

- **S0 MET** — HIGH (90 %).
- **S1 MET** — MEDIUM-HIGH (80 %). Frames within 1° of the incidence exist.
  About half are expected in the afternoon. Nb is expected to exist (65 %).
- **S2 MET** — MEDIUM (55 %). Matched illumination and cratered terrain help,
  while 78.5° incidence and D-049's failures above 66° hurt. The likelier
  failure is O2 → Na, because of O2's larger off-nadir angle.
- **S3 MET** — MEDIUM-LOW (40 %). Given S2, the loop closes under 2 px with
  about 70 % probability (EXP-012: 13 of 13 real triplets at 0.37–1.34 px, but
  on nadir mare).
- **S4 MET** — HIGH (85 %).
- **S5 MET** — MEDIUM (50 %).
- **Geometry:** refined disagreement **tens of metres** (CONSISTENT);
  system-level disagreement **2–3 km**, in the direction of the corner offset.
- **The 32° OHRC stereo edge (O1 ↔ O2),** reported only: B1 passes
  (60 %), and any triangle through it closes worse than {O1, Na, Nb}.

## 4. What may not happen in Part 2

- No line moves: 8 inliers, 2.0 px, the §2.4 floor, θ tiers, emission 20°,
  the 50 % overlap, 8 km, 2.0 px agreement.
- The target, tiles, windows, tiers, ranking and primary triangle are fixed by
  §2.1–2.3 before any pixel. None is re-chosen after one is seen. A frame
  excluded by the census stays excluded.
- `assess()`, `N_INLIERS_FAILURE_RULE` and the recorded pipeline's preparation
  are untouched.
- A secondary triangle may not substitute for the primary in S3. B4L may not
  substitute for B1 in S2 or S3.

## 5. What this stage does NOT claim

- **Not accuracy.** No check point independent of LRO exists at this site. The
  refined OHRC geometry was itself tied to LRO, so geometric agreement is
  corroboration, not verification.
- **Not gauge-free.** Loop closure is exactly invariant to a per-image gauge
  error (E-039). O1's own distortion, including its off-nadir parallax, cancels
  in {O1, Na, Nb}. VERIFIED here means the three transforms are mutually
  consistent to 2 coarse px, and nothing more.
- **Not illumination invariance.** Illumination is *matched* by design (rule 8).
- **Not a second site.** One site, one lunation of OHRC, highland-type
  cratered terrain. Nothing transfers without another stage.

## 6. Ledger — what Part 2 will create

A `STAGE-INDEX.md` row, a `STAGE_HISTORY.md` row, `RL-060`, a D-nnn recording
what the OHRC result does to §53 criterion 2 and §2.2's scale and viewpoint
rows, and an E-nnn for any defect found. **One E-nnn is already due and is
recorded in Part 2:** REAL-DATA-09's result row reads *"OHRC is over the South
Pole; no NAC coverage there"*, and the README repeats it. That stage's own
fuller text says only that no NAC tile was *on disk*. The census here measures
the coverage. Both scorecards are re-scored in the audit and the gap analysis.

---

# Part 2 — results, written 2026-09-28 against Part 1 exactly as frozen

Artefacts: `experiments/EXP-023/exp023_results.json` (runner
`scripts/run_exp023.py`, 470 s, quicklook `exp023_quicklook.png`), census
`census.json` + `census_attempt3.log` (attempts 1–2 kept beside: rate-limited,
then ODE unreachable), fetch manifest `data/manifests/exp023_manifest.json`,
`run.log` with `EXIT 0`. Three earlier launches died non-scientifically —
console kills, the third mid-S3 — and their logs are kept
(`run_died_v1..v3.log`); nothing frozen changed between launches, and the
artefact was written once, by the fourth.

## 7. Verdict summary

**S0 MET · S1 MET · S2 NOT MET · S3 MET · S4 MET · S5 MET.**

**S3 is the headline: the project's first VERIFIED Chandrayaan-2 result.**
The primary triangle {O1, Na, O2} closes at **1.9158 Na-coarse px = 3.41 m**
against the frozen 2.0 px line (in O1's own frame: 1.80 px; VERIFIED under
either unit), with legs of 18 017, 18 447 and 29 422 inliers, and `assess()`
returns **VERIFIED · moderate** on O1 → Na — moderate, not high, because
0.299 of the overlap has no nearby constraint, and the verdict says so.

**S2 is NOT MET, and not for the predicted reason.** Both OHRC → NAC edges
pass overwhelmingly (18 017 and 17 919 inliers at 78.5° incidence — the
failure Part 1 priced at 45 % never happened). The clause that failed is
corroboration: against the **refined** grid the registrations sit at medians
of **105.33 and 109.74 coarse px (187.5 / 195.3 m)** versus a **98.01 px
(174.5 m)** floor — 7–12 % above it, so both edges read INCONCLUSIVE, not
CONSISTENT, and S2 as frozen is NOT MET. The reading beside (not instead):
the disagreement is dominated by a **constant eastward offset — centre
components (+183.9 E, +42.6 S) m on O1 and (+171.8 E, +93.0 S) m on O2** —
while the loop closes at 1.92 px and an independent engine agrees with B1 to
**0.35–0.42 px median** (S5). A shared ~180 m eastward term between two
independent 18 000-inlier registrations and a corner map is the signature
EXP-019 measured for archive geometry on Serenitatis (137.6 m median,
+101 ± 74 m east, D-061) — here at 69.4° S, larger, and in the same
direction. As frozen, that is a hypothesis for a later stage, and S2 stays
NOT MET.

## 8. S0 — harness (MET)

(i) both OHRC files match their label MD5s and ingest through the unmodified
PDS4 reader, file-size identity exact; (ii) `g_grd` reproduces the refined
corners to 5.0e-07 / 4.0e-07 deg (≤ 1e-5 required); the system-level offset
is recorded (§10); (iii) handedness computed from the refined grid: neither
OHRC window is mirrored (Jacobian determinants −0.073 / −0.079); Na is not
mirrored (−0.795); (iv) Na passes `incidence_agreement` (index 78.3° vs
computed 78.335°); (v) NAC bytes SHA-256-manifested; the runner refused to
run while an artefact existed (integrity rule 4 exercised during the retries).

## 9. S1 — the data exists (MET), and the census funnel

ODE returned **116** NAC products over the 0.04° box; 95 survived the implied
prefilter; **exactly one** survived containment + emission ≤ 20° + θ ≤ 10°:
`nac.m1486555640lc` (2024-11-18, emission 1.45°, incidence at target 78.34°,
**θ = 4.42°** from obs1's Sun; footprint overlap 0.986 / 1.000 with the two
OHRC footprints). **Nb does not exist** — the second-ranked frame Part 1
expected at 65 % never materialised, so the primary triangle is
**{O1, O2, Na}** by Part 1 §2.3's own rule, and the 32°-apart OHRC stereo
edge is *inside* the primary loop rather than avoided. The acquisition gap
OHRC → Na is 207 days (≈ 6.8 months; Part 1 said "eight months or more" —
an approximation, noted in §15).

## 10. S2 — OHRC registers to NAC (NOT MET as frozen)

| edge | inliers | pass | refined-grid median | floor | verdict | centre offset (E, S) m |
|---|---|---|---|---|---|---|
| O1 → Na | **18 017** | yes | 105.33 px = 187.49 m | 98.01 px = 174.45 m | **INCONCLUSIVE** | +183.9, +42.6 |
| O2 → Na | **17 919** | yes | 109.74 px = 195.33 m | 98.01 px | **INCONCLUSIVE** | +171.8, +93.0 |

Both clauses of the criterion were required (pass **and** CONSISTENT); the
second fails on both edges, by 7.3 and 11.7 px over the floor. **The
system-level (SPICE) corners disagree by 2 871 m / 2 671 m** — the measured
size of OHRC's own pre-refinement pointing error against NAC, reported as
Part 1 §2.4 requires, and inside Part 1's predicted 2–3 km.

What may not be done, and was not: no floor was widened (the 98 px floor is
REAL-DATA-09's rule applied to this geometry), no clause was re-read as
"INCONCLUSIVE counts", and the eastward-offset reading above moves nothing.

## 11. S3 — the primary triangle is VERIFIED (MET)

{O1, Na, O2}: legs O1 → Na 18 017, Na → O2 18 447, O2 → O1 29 422 inliers,
every leg its own B1 run on its own pair (E-021). Loop residual **1.9158 Na
coarse px = 3.41 m** (first-image frame: 1.80 px), against the frozen 2.0.
`assess()` on O1 → Na, given the loop: **VERIFIED · moderate**, reasons
verbatim: correspondences clustered (0.299 of the overlap has no nearby
constraint) and "trust the alignment near the correspondences more than far
from them." The margin is 4.2 % — this is a pass the way REAL-DATA-09's
2.2131 px was a fail: near the line, and the line was set first.

The reported-only stereo edge O1 → O2 passes with **30 148** inliers across a
32° pointing difference (off-nadir 14.05° vs 18.03°, roll/pitch reversed) —
the strongest real viewpoint evidence the project holds.

## 12. S4 — the pass rule discriminates here (MET)

Both nulls were placed by the census with non-overlap confirmed from geometry
(N-a: the same NAC product displaced 7.997 km along-track; N-b: the O1 window
displaced 8 km inside obs1) and both **fail exactly as required: 4 inliers
each** against the > 8 rule, fit RMSE 0.59 px on N-a — the RMSE trap again,
refused again.

## 13. S5 — a second engine agrees (MET)

B4L (DISK + LightGlue) passes both edges — 1 402 and 1 525 inliers — and its
dense disagreement with B1 over the overlap is **median 0.418 px (p90 0.82)**
on O1 → Na and **0.347 px (p90 0.75)** on O2 → Na, against the 2.0 px line.
Two engines with no shared machinery land on the same transform to a third of
a pixel; the verdict stays capped at INCONCLUSIVE for pairs, as frozen.

## 14. Descriptive — what §2.2's rows gain (D-071)

- **Scale, real cross-sensor:** OHRC 0.26 m registered against NAC at 0.89 m
  native / 1.78 m coarse — a **3.4 : 1 native (6.8 : 1 coarse) cross-sensor
  rung**, bridged by the recorded degrade (factor 7, 1-px PSF). The row does
  not flip on one site; it stops being NAC-only.
- **Viewpoint, real:** Δview O1↔Na ≈ 12.6°, O2↔Na ≈ 16.6°, and the 32° OHRC
  stereo edge — the first real (non-synthetic) viewpoint evidence, at 30 148
  inliers.
- **Illumination:** matched by design (θ = 4.42°); no invariance claim (rule 8).
- 78.5° incidence at 69.4° S is the highest-incidence success on the record —
  D-049's 66.9–74.7° Serenitatis failures were Δinc-driven, not an incidence
  ceiling; with Δ matched, 78.5° registers with five-digit inlier counts.

## 15. Predictions graded (Part 1 §3.2), and disclosed approximations

| prediction | confidence | outcome |
|---|---|---|
| S0 MET | 90 % | **right** |
| S1 MET | 80 % | **right** — but Nb (65 %) **wrong**: no second frame exists |
| S2 MET | 55 % | **wrong, doubly**: S2 failed, and not where predicted — matching (the priced risk) succeeded at 18 k inliers; the corroboration clause failed |
| "likelier failure is O2 → Na" | — | **wrong**: neither edge failed to match |
| S3 MET | 40 % | **right** (loop 1.9158 px; given-S2 conditional 70 % never activated as stated, since S2 failed while every leg passed) |
| S4 MET | 85 % | **right** (4 / 4 inliers) |
| S5 MET | 50 % | **right** (0.35–0.42 px agreement) |
| refined geometry "tens of metres, CONSISTENT" | — | **wrong**: 187–195 m, INCONCLUSIVE on both edges |
| system-level "2–3 km" | — | **right**: 2.87 / 2.67 km |
| stereo edge passes | 60 % | **right** (30 148 inliers); its "closes worse than {O1, Na, Nb}" clause is unevaluable — no Nb exists |

Approximate statements in Part 1, noted here rather than repaired there: the
1.27 / 1.52 km swath-edge distances were label-derived estimates; "eight
months or more between acquisitions" is 207 days as realised; "Kaguya TC at
this latitude would starve under N\*" was an arithmetic expectation, not a
measurement, and no Kaguya product was used or excluded by it.

**RL numbering deviation:** Part 1 §6 reserved `RL-060`; EXP-024's Part 2
landed first and took it. This stage's entry is **RL-061**, recorded as a
deviation instead of renumbering a committed log.

## 16. What this result is, and is not

It **is**: the first VERIFIED Chandrayaan-2 ↔ NAC result; OHRC — the problem
statement's flagship sensor — registering to LRO NAC at the Chandrayaan-3
site with five-digit inlier counts at 78.5° incidence, a loop under the
frozen line, both nulls refused, and two independent engines agreeing to a
third of a pixel.

It is **not**: accuracy (no check point independent of LRO exists at this
site — OHRC's refined geometry was itself tied to LRO); gauge-free (O1's own
distortion cancels in the loop, E-039); illumination or viewpoint invariance;
a second site; and it is not a CONSISTENT corroboration — S2 failed as
frozen, and §53 criterion 2 **stays NOT MET** with its OHRC sub-clause now
reading, exactly as frozen in advance: *VERIFIED by loop closure, check
points unavailable*.

## 17. Ledger

- **D-071** — what the OHRC result does to the scorecards (DECISION_LEDGER).
- **E-062** — the "no NAC coverage" wording: REAL-DATA-09's result row and
  the README said coverage where the record supported only "no tile on
  disk"; the census measured 116 NAC products over the site (ERROR_LEDGER).
- **RL-061**, STAGE-INDEX and STAGE_HISTORY rows, audit + gap-analysis
  re-score, README status row — this commit.
