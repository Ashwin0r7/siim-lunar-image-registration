# EXP-020 — Multi-modality, measured: nine reflectance bands and a thermal map against panchromatic, on one map frame

**Part 1 — pre-registration. FROZEN 2026-09-23, before any Kaguya MI or
Diviner byte has been fetched, before any band has been matched to anything,
before any statistic has been computed and before the runner exists.** Part 2
is empty until Part 1 is committed.

**Classification: DELIVERABLE-CRITICAL.** "Multi-modal" is in the problem
statement's title. `PROJECT_GAP_ANALYSIS.md` §1(b) scores the axis **NOT MET**
and §3 ranks it the **fourth** most damaging question a hostile reviewer can
ask — *"It's called multi-modal. Where is the multi-modality?"* — with the
honest answer being: **one measured negative** (REAL-DATA-08's radar, 0 of 48)
and nothing else.

**Why there is no IIRS result, stated first.** The PRADAN download of
2026-09-20 delivered TMC-2 and OHRC and **no IIRS product at all** (RL-046):
the thread is *data-REFUSED*, not data-blocked, and no amount of software
fixes it. This stage does **not** claim to test IIRS. It tests the *question*
§2.2 asks of IIRS, using the closest publicly available instrument of the same
kind, and §7 states exactly how the substitute differs.

**The acceptance criterion this stage answers, verbatim from
`MASTER_RESEARCH_AND_ARCHITECTURE_PLAN.md` §2.2:**

> | Multi-modality (OHRC/TMC ↔ IIRS bands) | … | **reflectance bands: same
> envelope as pan; thermal: envelope stated** |

Both clauses are adopted below: the reflectance clause as **S1/S2**, the
thermal clause as **S5**.

---

## 0. The substitution, and what it costs

| | Chandrayaan-2 **IIRS** (what §2.2 names) | Kaguya **MI** (what this stage uses) |
|---|---|---|
| kind | imaging spectrometer | multiband imager |
| bands | 256 contiguous | **9** discrete |
| range | 800 – 5000 nm | **414 – 1548 nm** |
| GSD | 80 m | **14.8 m** |
| on disk | **none delivered** | public, JAXA/ISAS DARTS |
| geometry | swath + LOC backplanes | **map-projected**, planetocentric simple cylindrical |
| photometry | L1 radiance | normalised to **(i = 30°, e = 0, α = 30°)** — the *same* standard geometry as the TC ortho EXP-019 validated |

**What transfers.** The question — *does a narrow reflectance band of a
spectrometer-class instrument register to a panchromatic image of the same
ground, and is the result the same as for pan?* — and the architecture that
answers it (degrade to a common GSD, match, verify).

**What does not.** IIRS's thermal half (2500–5000 nm, where the signal is
emitted rather than reflected) is not covered by MI at all; that is exactly
why **S5 brings in a real thermal instrument** instead of pretending a 1548 nm
band is one. And IIRS's 80 m GSD against OHRC's 0.25 m is the 320 : 1 rung,
which is EXP-016's subject, not this one.

**Why this pairing is unusually clean, and why that is a limitation too.** MI
and the TC ortho are the same mission, the same processing lineage (LISM), the
same map projection and the **same photometric standard geometry**. So between
an MI band and the TC pan reference there is **no illumination difference and
no georeferencing difference by construction** — the only differences are
**wavelength**, **GSD** (14.8 m vs 8.42 m) and the instruments' own noise.
That isolates the modality variable better than any pairing in this
repository — and it means a success here does **not** imply success across a
mission boundary. S3 and S4 cross that boundary deliberately, to Chandrayaan-2
and to LRO NAC, and are expected to be harder.

---

## 1. The question

**Q.** Take a multispectral imager's nine reflectance bands over ground this
project has measured to death. Ask, one band at a time:

1. Does the band register to a **panchromatic** reference of the same ground?
2. Is the answer the **same as for panchromatic** — measured against a
   synthetic pan image built from the *same instrument's own bands*, so that
   the only thing varying is spectral width?
3. Does a band register to **Chandrayaan-2's TMC-2 ortho** — the problem
   statement's own pairing shape, ISRO panchromatic against a
   spectrometer-class band?
4. Does it register to **LRO NAC** across a mission boundary and a 15 : 1
   scale ratio?
5. Does a **thermal** map — Diviner bolometric temperature, 236.9 m, an
   emitted-radiation signal with no reflectance in it — register to pan at
   28 : 1, and if not, what is the envelope?

| outcome | consequence |
|---|---|
| Bands register and match pan (S1 + S2 MET) | §2.2's reflectance clause is **MET on a real multispectral instrument**, in the stated scope, and the project's multimodality evidence stops being a single negative |
| Bands register but worse than pan (S1 MET, S2 NOT MET) | the envelope is **narrower** for bands than for pan, by a measured factor, and the deliverable states that factor |
| Bands do not register (S1 NOT MET) | a second measured multimodal negative, this time with illumination and georeferencing held fixed by construction — which would be a much stronger negative than REAL-DATA-08's radar, because it removes every confound the radar case had |
| A band registers to TMC-2 (S3 MET) | the PS's own pairing shape is demonstrated end to end on real ISRO data with a substitute spectrometer |
| Thermal registers (S5 MET) | surprising, and the envelope is stated with the ratio |
| Thermal does not (S5 NOT MET) | the thermal clause is **answered with a bound**, which is what "envelope stated" asks for |

---

## 2. What is measured, stated exactly

### 2.1 The ground truth this stage has, and its limit

Every product here is **map-projected**: MI, the TC ortho and Diviner in
planetocentric simple cylindrical on a 1737.4 km sphere; the Chandrayaan-2
TMC-2 ortho in its own projection, read through `siim.ingest.geotiff`. So for
any two of them the correspondence is **analytic** — composition of the two
label-defined pixel↔(lon, lat) maps — and needs no matcher.

**The measured error of a registration is therefore**

```
err(x) = ‖ T̂(x) − T_map(x) ‖      over an 8 px grid of the source, jointly valid
```

with `T_map` from the two labels alone. This is a **ground-truth-class**
statistic and it is the first in this repository that does not pass through a
matcher — with one limit, stated now and never dropped: it is exact only to
the extent that the two products are **correctly georeferenced relative to
each other**. Within Kaguya (MI ↔ TC) that is one mission, one processing
lineage and one control network, so the relative term is small and unmeasured
here; across missions (MI ↔ TMC-2, MI ↔ NAC) it is **not** small, and EXP-019
measured one such term at **137.6 m** (archive corners vs the Kaguya frame).
S1 and S2 therefore live inside Kaguya; S3 and S4 cross the boundary and
report error **against the label map with that caveat attached**, never as
accuracy.

### 2.2 The arms

| arm | source | reference | what varies |
|---|---|---|---|
| **P** (pan control) | **the band mean** of the nine MI bands, on the MI grid — a synthetic panchromatic image from the same instrument, same noise, same grid | TC ortho, 8.42 m pan | nothing but spectral width (this is the comparator S2 is read against) |
| **B**b (bands) | MI band *b*, `b = 1…9` (414, 749, 901, 950, 1001, 1000, 1049, 1248, 1548 nm) | TC ortho | **wavelength** |
| **C** (Chandrayaan-2) | MI bands | TMC-2 L2 ortho block (REAL-DATA-09 P1 block, 4.9 m) | wavelength **+ mission + sensor** |
| **N** (NAC) | MI bands | the NAC tiles EXP-019 registered to the same reference (arm-R passes), degraded to the MI GSD | wavelength + mission + **15 : 1 scale** |
| **T** (thermal) | Diviner `tbol` bolometric temperature, 236.9 m | TC ortho | **physics** (emitted, not reflected) + **28 : 1 scale** |
| **0** (null) | every MI band and arm P | the **TC null block** of EXP-019, ≥ 25 km away | nothing — it must fail |

**The pipeline is unchanged.** `siim.pipeline.register_pair`, engine **B1**,
affine LO-RANSAC at 3.0 px, seed 0; degradation through
`siim.preprocessing.degrade.degrade_to_gsd` with `psf_fwhm_coarse_px = 1.0`
(R9), coarser-to-finer never upsampled — the finer product is always the one
degraded, as §19 requires. B4L is run beside every cell and enters no
criterion.

### 2.3 Response variables per cell

- **(a)** success under the frozen rule `n_inliers > 8` (D-023);
- **(b)** `err` median, p99 and max against the label map (§2.1), in reference
  pixels **and** metres;
- **(c)** keypoints on both images, putatives, inliers, `grid_occupancy`
  (D-055) and `max_uncovered_disc_ratio` (secondary, D-053/D-057);
- **(d)** the verdict status and confidence from the unmodified `assess()`;
- **(e)** the recovered scale against the known GSD ratio;
- **(f)** the band's own statistics: valid fraction, mean reflectance, and the
  **contrast** (standard deviation / mean) of the degraded image, which is the
  quantity a descriptor actually sees and the one that predicts S1's per-band
  outcome if the physics is what it is expected to be.

---

## 3. Data, fixed in advance

| product | what | where |
|---|---|---|
| **Kaguya MI MAP V3** | `MI_MAP_03_N20E021N19E022SC`, `MI_MAP_03_N20E022N19E023SC`, `MI_MAP_03_N21E021N20E022SC`, `MI_MAP_03_N21E022N20E023SC` — the four 1° × 1° tiles covering the EXP-019 reference window. 2048 × 2048 × **9 bands**, BSQ, MSB int16, `SCALING_FACTOR` 2.0e-5, reflectance, **2048 px/deg = 14.806 m**, `STANDARD_GEOMETRY (30, 0, 30)`, `PHOTO_CORR_ID "LISM ORIGINAL"` | DARTS `sln-l-mi-5-map-v3.0/lon021/data/` and `lon022/data/` |
| **Kaguya TC ortho** | the REF and NULL blocks already on disk | `data/manifests/exp019_tc_ortho_{ref,null}_block.json` |
| **Chandrayaan-2 TMC-2** | the REAL-DATA-09 P1 block `[1637, 56766, 2135, 57597]` | `data/manifests/chandrayaan2_manifest.json` |
| **LRO NAC** | the arm-R passes of EXP-019, whose **controlled** positions that stage measured | `experiments/EXP-019/exp019_results.json` |
| **Diviner GDR L3** | `dgdr_tbol_avg_cyl_20090705n_128_img` — bolometric temperature average, **128 px/deg = 236.9 m**, cylindrical, PDS4 | PDS Geosciences `lro_diviner_derived1/data_derived_gdr_l3/2009/cylindrical/img/` |

**Window:** the EXP-019 reference block, **lat 19.52 – 20.24 N, lon 21.88 –
22.17 E** — the same ground as every real result in this project. MI tiles are
cut to it and mosaicked on the MI grid; the Diviner rows are byte-ranged out
of the 2.1 GB global product (that server honours ranges; **E-050** is a DARTS
behaviour and does not apply here, which the runner checks rather than
assumes).

**Invalid data:** MI reflectance is positive by definition, so a sample
`≤ 0` is invalid (the label's `INVALID_TYPE` names saturation, minus, dummy
and other without giving values); the fraction is recorded per band and a band
with **< 40 %** valid coverage over the window is reported `excluded` before
any registration. Diviner's label-declared missing constant is used as the
label gives it.

**Cost.** Four MI tiles ≈ 352 MB at the 5 MB/s measured for DARTS, ≈ 10 MB of
Diviner rows, ≈ 60 registrations on images ≤ 1200 × 800 px. Predicted 20–40
min wall clock.

**Runner and artefact.** `scripts/run_exp020.py`, written only after this
Part 1 is committed; `experiments/EXP-020/exp020_results.json`; refuses to
overwrite (integrity rule 4). Acquisition is
`scripts/acquire_exp020_multimodal.py`, which writes manifests with byte
ranges and SHA-256 **before** any product is opened.

---

## 4. Success criteria — FROZEN

| ID | Criterion | MET if |
|---|---|---|
| **S0** | **Harness and provenance controls. Nothing is reported from a cell unless every clause holds.** | (i) **grid gate**, MI and Diviner: the pixel↔(lon, lat) map built from each label's projection offsets reproduces that label's own corner summaries to **< 0.5 px**, and a round trip over 10⁴ points closes to **< 1e-9°**; (ii) **band co-registration control**: MI band 2 against MI band 5 on the same grid recovers a transform whose dense displacement over the window is **< 0.05 px** — the bands are co-registered by construction, so anything larger means the ingestion is wrong and the stage stops; (iii) **reproduction gate**: one recorded REAL-DATA-07 B1 north-up edge re-runs to its recorded `n_inliers` **exactly**; (iv) provenance — byte ranges, SHA-256, valid fractions and the label-derived grid recorded for every product before any registration; (v) the analytic map `T_map` is verified by round-tripping a grid through both labels and back to **< 1e-6 px** |
| **S1** | **Do reflectance bands register to panchromatic?** | **≥ 7 of 9** MI bands succeed against the TC pan reference under `n_inliers > 8` **and** their median `err` against the label map is **< 1.0 reference px (8.42 m)**. Per-band counts, errors and contrasts reported whatever happens |
| **S2** | **§2.2's clause, verbatim: "reflectance bands: same envelope as pan."** | Against arm **P** (the band-mean pan image, same instrument, same grid): every band that succeeded has median `err` **≤ 2 ×** arm P's median `err`, **and** the number of succeeding bands is **≥ 7 of 9** while arm P also succeeds. The **worst band is named** with its wavelength, and the band-vs-pan ratio is reported per band. If arm P itself fails, S2 is **NOT MET for want of a comparator** and says so |
| **S3** | **The problem statement's own pairing: ISRO panchromatic against a spectrometer-class band.** | **≥ 1** MI band registers to the Chandrayaan-2 TMC-2 ortho block with `n_inliers > 8` and median `err` against the label map **< 60 m** — the label's own `σ_C2 = 38.75 m` (REAL-DATA-09) plus the ≤ 21 m that S1's Kaguya-internal term is allowed to be. Reported: every band's count and error, and the verdict |
| **S4** | **Across a mission boundary and 15 : 1 of scale.** | **≥ 3 of 9** bands register to **≥ 2** of EXP-019's arm-R NAC frames (`n_inliers > 8`), with `err` measured against **EXP-019's controlled position** for that frame — not against its archive corners, which EXP-019 measured to be wrong by 137.6 m — and reported in metres |
| **S5** | **§2.2's thermal clause: "thermal: envelope stated."** | The Diviner `tbol` map against the TC pan reference at 28 : 1: **MET** if it registers (`n_inliers > 8`) with median `err` **< 2.0 thermal px (474 m)**; **NOT MET** otherwise. Either way the stage states the envelope: the ratio, the pixel counts on both sides, the keypoint counts, and — if it fails — which of the two (starvation or physics) the keypoint counts say it is |
| **S6** | **The null: every arm must be able to fail.** | **0 of 10** cells (nine bands + arm P) pass against the TC **null** block, 25 km away in the same product. Any pass is a wrong pass and is reported with its inlier count and error |

### 4.1 Parameter count against constraint count (E-041)

| statistic | fitted parameters | constraints | null / reference |
|---|---|---|---|
| affine per cell | 6 | ≥ 9 inliers by the rule; expected 10²–10³ on a ~900 × 500 px window | the null block (S6) — a wrong *place*, not a permutation |
| `err` vs `T_map` | **0** | ≥ 500 grid points per cell | the label maps, which no matcher touched |
| band-vs-pan ratio (S2) | 0 | 9 bands against one comparator | arm P itself |
| contrast vs success (§2.3 f) | 0 | 9 bands | reported, **not** a criterion — n = 9 cannot support a correlation and this is said now rather than discovered later |

### 4.2 Predicted outcome per criterion, recorded now so it can be wrong

- **S0 MET** — HIGH, except (ii): the band co-registration control is the one
  clause that could genuinely fail, because "co-registered by construction" is
  an assumption about LISM's processing that this project has never checked.
  If it fails, the stage stops and that is the finding.
- **S1 MET** — MEDIUM-HIGH, **8 or 9 of 9** (MEDIUM). Median `err` predicted
  **0.3 – 1.0 reference px**. Mare albedo structure is spectrally coherent —
  the same craters and the same regolith maturity contrasts appear in every
  band — so the descriptor should see the same scene nine times at different
  SNR. **The band most likely to fail is 414 nm** (MV1: lowest reflectance,
  lowest SNR on mare) — MEDIUM — with 1548 nm (MN4) second.
- **S2 MET** — MEDIUM. The worst band's ratio to pan predicted **1.2 – 2.0**;
  a ratio above 2 on one band while the rest pass would make S2 NOT MET on a
  single band, and that is the intended sensitivity.
- **S3 MET** — MEDIUM-LOW (45 %). The TMC-2 block is **415 × 249 px at 9.8 m**
  ≈ 4.1 × 2.4 km, which at MI's 14.8 m is **≈ 275 × 165 px** of overlap — a
  small window, and REAL-DATA-09's own B1 row on this block found **4
  inliers**. If any band succeeds where TMC-2 ↔ NAC needed a long window, that
  is because the reference is photometrically normalised and the NAC was not.
- **S4 MET** — MEDIUM. The 15 : 1 ratio is inside EXP-016's expected envelope
  and NAC is not photometrically normalised, so this arm carries a real
  illumination difference as well; **3–6 bands on 2–4 frames** predicted.
- **S5 NOT MET** — MEDIUM-HIGH (70 %). Bolometric temperature at 236.9 m is
  dominated by slope and albedo at scales far larger than the craters a
  descriptor keys on, and the window holds only **≈ 110 × 110 thermal px**.
  Predicted failure mode: **starvation** (< 50 keypoints on the thermal side),
  not descriptor mismatch — and the two are distinguished by the recorded
  keypoint counts. A thermal pass would be a genuine surprise and is given
  30 %.
- **S6 MET (0 of 10)** — HIGH.
- **Overall:** S0, S1, S2, S4, S6 MET; S3 a coin flip; S5 NOT MET with a
  stated envelope. If S1 fails, the project's multimodality position becomes
  *two* measured negatives with the second one confound-free, which is a
  stronger and more useful statement than the current single one.

---

## 5. Physical limits, in numbers

| quantity | value |
|---|---|
| MI GSD | **14.806 m**, 2048 px/deg |
| TC reference GSD | 8.423 m, 3600 px/deg — MI is the **coarser**, so the TC ortho is the image that gets degraded (ratio **1.758 : 1**) |
| window | lat 19.52–20.24, lon 21.88–22.17 ≈ **21.8 × 30.6 km** → MI **≈ 2070 × 1476 px**, TC ≈ 3640 × 2593 px |
| MI ↔ TMC-2 | 14.806 / 4.899 = **3.02 : 1**; overlap ≈ 275 × 165 MI px |
| MI ↔ NAC | 14.806 / 0.93 ≈ **15.9 : 1**; a 4096 × 2048 NAC tile is ≈ 257 × 129 MI px |
| Diviner ↔ TC | 236.901 / 8.423 = **28.1 : 1**; the window is ≈ **110 × 155 thermal px** |
| bands | 414, 749, 901, 950, 1001 nm (VIS) · 1000, 1049, 1248, 1548 nm (NIR) |
| 1.0 reference px (S1's bar) | **8.42 m** |
| 2.0 thermal px (S5's bar) | **473.8 m** |

- **What 28 : 1 means for a descriptor.** EXP-016 is measuring the pixel floor
  `N*` for degrade-and-match on NAC texture; REAL-DATA-08 found B1 starved at
  **111 × 46 px** on the WAC rung. The Diviner window at **110 × 155 px** is
  just above that, so S5's outcome is genuinely uncertain on pixel count alone
  and its *physics* is the variable of interest.
- **What the bands cost in SNR.** MI's VIS bands are 20 m native and the NIR
  bands 62 m native, both resampled to the 14.8 m MAP grid: the NIR bands are
  therefore **smoother than their grid**, which is a resolution difference
  masquerading as a wavelength difference. That confound is real, is stated
  here, and is why S2's comparator is the band **mean** rather than a VIS band.

---

## 6. What may not happen in Part 2

- No bar moves: 7 of 9 and 1.0 reference px (S1), 2× and 7 of 9 (S2), 60 m
  (S3), 3 bands × 2 frames (S4), 2.0 thermal px (S5), 0 of 10 (S6).
- **The band set is all nine.** No band is dropped for being noisy; a band
  that fails is reported with its contrast and its keypoint count.
- No re-run with a different engine, seed, PSF, RANSAC threshold or window.
  B4L stays outside every criterion.
- The synthetic pan comparator is the **unweighted mean of the nine bands**,
  fixed here; it may not be re-weighted after seeing which bands succeed.
- A criterion that passes vacuously — S6 because the null cells produced no
  keypoints at all, S2 because only one band succeeded — is reported as
  *MET, and here is why that is not reassurance*, beside the criterion.
- The substitution in §0 may not be softened in Part 2: this is **not** an
  IIRS result and the word IIRS may not appear in any claim sentence.
- If S0(ii) fails, the stage stops at S0 and reports that, rather than
  proceeding with an ingestion it has measured to be wrong.

## 7. What this stage explicitly does NOT claim

- **Not an IIRS result.** No IIRS product exists in this repository (RL-046).
  MI is 414–1548 nm at 14.8 m against IIRS's 800–5000 nm at 80 m.
- **Not a thermal-infrared *imaging* result.** Diviner's `tbol` is a gridded
  derived product at 236.9 m, not an image from a thermal camera.
- **Not accuracy across missions.** S3 and S4's errors are measured against
  label maps whose relative georeferencing carries the term EXP-019 measured
  at 137.6 m for the archive; within Kaguya (S1, S2) that term is small and
  **unmeasured**, which is stated wherever the number appears.
- **Not an illumination result.** MI and TC share a standard geometry by
  construction; there is **no** Sun-angle variation in S1, S2 or S5.
- **Not a new region or terrain class.** One mare window, the same one.
- **Not a verdict change.** `assess()`, `select_model` and every constant are
  untouched.
- **Not a matcher claim** beyond B1.

## 8. Reported beside the criteria, not part of any

- Per-band contrast (σ/μ) of the degraded image against success and `err` —
  the mechanism, reported as a table, never as a correlation (§4.1).
- B4L on every cell of every arm.
- The verdict status and confidence per cell, with `model_selected_by`.
- Coverage (occupancy primary, D-055) per cell.
- Recovered scale against the known GSD ratio per cell.
- The Diviner cell's keypoint counts on both sides, which decide *why* S5
  lands where it does.
- The MI band mean's own agreement with the TC ortho as an image: correlation
  after degradation, reported once, as context for what "same scene" means
  across 8.42 m pan and 14.8 m multispectral.

## 9. Ledger and index — what a Part 2 will create

A `STAGE-INDEX.md` row, a `STAGE_HISTORY.md` standing-table row, an `RL-nnn`
entry, a **D-nnn** recording what the §2.2 multimodality row may now say (and
what it may not), and an **E-nnn** for any defect S0 exposes.

---

## Amendment A1 — the frozen thermal product has no data over the window, and the replacement rule (2026-09-23, before any registration)

**This amendment is written after the acquisition and before any statistic.**
Nothing below concerns a matcher, an inlier count or an error; it is a
data-availability fact and the rule that answers it, both recorded before the
runner exists.

### A1.1 What happened

Part 1 §3 froze `dgdr_tbol_avg_cyl_20090705n_128_img`, chosen from ODE's
footprint index — which, for a **global** product, reports the whole Moon and
therefore cannot say whether a particular window holds data. The fetched block
over the window is **100 % `MISSING_CONSTANT`**: `missing_fraction 1.0000`,
recorded in `data/manifests/exp020_diviner_tbol_block.json`, which is kept
exactly as written.

**A second thing was wrong with that choice, and it is the more interesting
one.** The `n` suffix marks a **night** map cycle. Night-time bolometric
temperature over mare is governed by **thermal inertia and rock abundance** —
a field with no reason to share structure with a reflectance image. Daytime
bolometric temperature is governed by **insolation on slopes and by albedo**,
which is the only channel through which a thermal map can carry the same
scene a reflectance image carries. Part 1 §4.2 predicted S5 NOT MET with
*starvation* as the failure mode; a night map would have made that prediction
untestable for a second reason that has nothing to do with scale, and the
stage would have reported a negative for the wrong cause.

### A1.2 The replacement rule, frozen here

> **The thermal product is the earliest DAY cycle (`d`), in the archive's own
> date order, whose block over the window holds ≥ 50 % valid samples.**

Day rather than night for the physical reason above, stated before any
registration; earliest-with-coverage rather than best-looking, so that no
choice is made on appearance. The probe is a 16-row block per candidate — a
count of valid samples, not a statistic.

### A1.3 The probe, recorded

| cycle | valid fraction over the window rows | T range (K) |
|---|---|---|
| `dgdr_tbol_avg_cyl_20090705n_128_img` (the frozen one) | **0.000** | — |
| `dgdr_tbol_avg_cyl_20090705d_128_img` | 0.000 | — |
| **`dgdr_tbol_avg_cyl_20090727d_128_img`** | **0.668** | **322.8 – 335.1** |
| `dgdr_tbol_avg_cyl_20090823d_128_img` | 0.108 | 367.9 – 368.9 |
| `dgdr_tbol_avg_cyl_20090920d_128_img` | 0.260 | 382.8 – 384.8 |

**Selected: `dgdr_tbol_avg_cyl_20090727d_128_img`**, the first day cycle
clearing 50 %. Its block is written to
`data/manifests/exp020_diviner_tbol_day_block.json`; the night cycle's
empty-block manifest stays on disk as the record of what was frozen first.

### A1.4 What does not change

S5's bar (**2.0 thermal px = 473.8 m**), its prediction (**NOT MET at 70 %**,
failure mode *starvation* if the thermal keypoint count is under 50), the
28 : 1 ratio, the window, the engine and every other criterion are untouched.
The 33 % of the window that the selected cycle does not cover is carried as
`NaN` and reported with the cell.

---

## Part 2

**Written 2026-09-23, after the run.** Artefact:
`experiments/EXP-020/exp020_results.json` (831 s, Python 3.13.7, NumPy 2.3.3,
OpenCV 5.0.0, Windows 11). Supplements, both labelled as such and folded into
no criterion: `exp020_armN_cropped.json` (B1) and
`exp020_armN_cropped_b4l.json` (B4L).

### 6. The answer, in one paragraph

**Nine reflectance bands of a multispectral imager register to a panchromatic
image of the same ground, and they behave like the pan image does — but every
absolute number in this stage is dominated by a disagreement between two
products of the *same mission* that nobody had measured.** Seven of nine MI
bands pass the frozen rule against the Kaguya TC pan ortho, and each of the
seven lands within **1.334×** of the error of a synthetic pan image built from
the same instrument's own band mean, so **§2.2's clause — *reflectance bands:
same envelope as pan* — is MET as frozen (S2)**. What is NOT met is **S1's
absolute bound**: the median error against the analytic label map is **54.1 m**
where the bar was 8.42 m, and the reason is not wavelength. The same offset
appears in the pan comparator (**72.4 m**), the linear part of every recovered
transform matches the label map to **3 × 10⁻⁵**, and the learned engine — which
finds **1360–2024 inliers** where RootSIFT finds 9–41 — puts it at **83–91 m**.
**Two Kaguya products, one map frame, one control network, disagree by about
85 m**, and this stage measured it. On the problem statement's own pairing
shape, **two MI bands register to the Chandrayaan-2 TMC-2 ortho** (749 nm at
72.7 m, 901 nm at 80.8 m) — S3 NOT MET against its 60 m bar, by the same
budget. The thermal clause is answered with a bound: Diviner bolometric
temperature at **28 : 1** yields **49 keypoints and 0 inliers** — **starvation,
the failure mode Part 1 named in advance**. The null block returns **0 of 10**.

### 7. Criteria, answered exactly as frozen

| ID | Verdict | The number |
|---|---|---|
| **S0** | **MET** | Grid gates pass for MI and Diviner; the **band co-registration control** — the assumption this project had never checked — returns **3564 inliers and a median displacement of 0.0301 px** between band 2 and band 5 against a 0.05 px tolerance; the reproduction gate re-runs a recorded REAL-DATA-07 edge to **1656 = 1656**; the analytic map round-trips to **2.8e-12 px** with affine residuals of 2.3e-13 and 2.8e-14 |
| **S1** | **NOT MET** | **7 of 9** bands pass the frozen rule (bar ≥ 7) — but **0 of 9** land within **1.0 reference px (8.42 m)**. Median error over the seven: **54.13 m**; range **40.96 – 96.63 m**. The criterion's two clauses split, and §8 is why |
| **S2** | **MET as frozen** | Seven bands succeed (bar ≥ 7), the pan comparator succeeds, and the **worst band-to-pan ratio is 1.334** (1049 nm) against a bar of **2.0**; the other six run **0.566 – 0.894**, i.e. *better* than the pan comparator. **The artefact's own S2 field says NOT MET because the runner coupled S2's band count to S1's metre bound instead of to the success rule Part 1 names — E-053. The artefact is not rewritten; the criterion is read here as frozen** |
| **S3** | **NOT MET** | **2 of 9** bands register to the Chandrayaan-2 TMC-2 block (749 nm, 12 inliers, **72.66 m**; 901 nm, 9 inliers, **80.75 m**), and the bar was **< 60 m**. Missed by **21 %**, on the same offset budget S1 fails on |
| **S4** | **NOT MET** | **0 of 36** cells. Two supplements say why, and neither reason is the one the criterion was written to test — see §11 |
| **S5** | **NOT MET, envelope stated** | Diviner `tbol` at **28.1 : 1**: **49 keypoints** on a 120 × 65 thermal window against **60** on the 92 × 37 degraded pan, **0 putatives survive**, 0 inliers. **Failure mode: starvation**, as predicted, distinguished from descriptor failure by the recorded keypoint counts |
| **S6** | **MET** | **0 of 10** cells pass against the null block 25 km away; false-accept fraction **0.000** |

### 8. Why S1 fails, and why it is not about wavelength

The recovered transforms are not wrong — they are **displaced**. On the pan
comparator the estimated linear part is `[[0.87888, −0.00024], [0.00024,
0.87888]]` against the label map's `[[0.87891, 0], [0, 0.87891]]`: agreement to
**3 × 10⁻⁵**, i.e. the scale and rotation between the two products are exactly
what their labels say. The disagreement is a near-pure **translation**, and the
better the matcher, the more precisely it is measured:

| engine | inliers (pan) | median error |
|---|---|---|
| B1 (RootSIFT) | 14 | 72.42 m |
| **B4L (DISK + LightGlue)** | **1938** | **90.83 m** |

Per band, RootSIFT's errors scatter between 40.96 and 96.63 m on 9–41 inliers;
B4L's VIS bands, with 1360–2024 inliers, land at **83.17 – 91.43 m**. The
honest reading is that **the MI MAP V3 mosaic and the TC Ortho Seamless V2
mosaic are offset from each other by roughly 85 m (≈ 5.7 MI px, ≈ 10 TC px)**,
and S1's 8.42 m bar was written as if the two products' relative
georeferencing were exact. Part 1 §2.1 said the analytic map is *"exact only to
the extent that the two products are correctly georeferenced relative to each
other"* and that within Kaguya the term was "small and unmeasured". **It is no
longer unmeasured, and it is not small.**

**The wavelength-only quantity, reported beside.** Each band's disagreement
with the *pan comparator's own solution* removes the common product offset and
leaves what the wavelength costs:

| band | 414 | 749 | 901 | 950 | 1001 | 1000 | 1049 | 1248 | 1548 |
|---|---|---|---|---|---|---|---|---|---|
| vs pan (m) | 18.8 | 25.4 | 52.8 | 32.9 | 111.1 | 142.3 | 91.0 | 42.8 | 70.7 |

The five VIS bands sit at **18.8 – 52.8 m**; the NIR bands at **42.8 –
142.3 m**. So wavelength does cost something, and it costs more in the NIR —
which §9 attributes.

### 9. The two bands that fail, and what they have in common

The failures are **1001 nm (MV5)** and **1000 nm (MN1)** — the same
wavelength, measured by the imager's two different detectors at the VIS/NIR
boundary. The recorded keypoint counts explain it without any new statistic:

| | VIS bands (414–1001 nm) | NIR bands (1000–1548 nm) |
|---|---|---|
| keypoints on the degraded source | **10 821 – 15 546** | **3 025 – 3 516** |
| native GSD before the MAP grid | 20 m | **62 m** |

The NIR bands are resampled from a **62 m** native sampling onto the 14.8 m MAP
grid, so they are *smoother than their own grid* and a corner detector finds a
quarter as much to key on. **Part 1 §5 named this confound before the run** —
*"a resolution difference masquerading as a wavelength difference"* — and it is
why S2's comparator is the band **mean** rather than a VIS band. The stage
therefore does **not** claim that 1000 nm is intrinsically harder to register;
it claims that *these* 1000 nm products carry a quarter of the detectable
structure, which is a property of the instrument's optics and of LISM's
resampling, not of the modality question.

**And the two engines disagree about it, in the direction that matters.**
RootSIFT registers **7 of 9** bands including three NIR bands; DISK + LightGlue
registers **5 of 10** cells — the pan comparator and the four brightest VIS
bands — and fails **every NIR band** (0–4 inliers). A learned matcher trained
on terrestrial photographs is *more* dependent on the high-frequency content
the NIR bands lack. This is D-056's *"a matcher swap is a trade, not a monotone
gain"* appearing on a new axis, and it is reported beside the criteria, not
inside them.

### 10. S3 — the problem statement's own pairing, end to end

`TMC-2 ortho (Chandrayaan-2, ISRO, panchromatic, 4.9 m)` ↔ `MI band (SELENE,
JAXA, one reflectance band, 14.8 m)` is the shape §2.2 asks for with IIRS in
the second slot. Two bands register:

| band | inliers | error vs the label map |
|---|---|---|
| 749 nm | 12 | **72.66 m** |
| 901 nm | 9 | **80.75 m** |

against a bar of **60 m** = the label's own `σ_C2` (38.75 m, REAL-DATA-09) plus
the ≤ 21 m Part 1 allowed for the Kaguya-internal term. The Kaguya-internal
term turned out to be **~85 m**, not ≤ 21 m, so the bar was built on a
measurement that did not exist yet and the criterion is NOT MET **by a margin
smaller than the term it omitted**. That is stated rather than repaired: the
bar may not move (Part 1 §6), and the honest summary is *two bands of a
spectrometer-class instrument register to Chandrayaan-2's panchromatic ortho,
with an error consistent with the two missions' georeferencing budget and not
demonstrably better than it*.

### 11. S4 — the frozen arm failed, and the supplements say it was the matcher

Arm N put each MI band against the NAC frames EXP-019 placed, and **0 of 36
cells passed** (3–5 inliers each). Two supplements, both labelled and folded
into no criterion, test the two obvious harness explanations:

1. **Framing.** In the frozen arm the source was the whole **1477 × 596** MI
   mosaic against a **585 × 292** NAC matching image: the overlap is
   **4.6 – 6.2 %** of the source area. Re-run with the MI source cut to each
   NAC tile's footprint plus 2 km — the construction EXP-019 used everywhere —
   **0 of 36 cells still pass** (3–5 inliers). *Framing is not the cause.*
2. **Direction.** Matching is not symmetric (E-036). Swapping source and
   reference on one cell changes 5 inliers into 3. *Direction is not the cause.*

**The cause is the matcher.** On the same cropped cell, **DISK + LightGlue
returns 274 inliers (MI → NAC) and 433 (NAC → MI)** where RootSIFT returns 5
and 3. Run over the supplement's full set, B4L registers **5 of 36** cells, on
**3** of the four frames and **3** of the nine bands — and that count needs a
caveat of its own: **one of the five is a wrong pass** (1548 nm, 13 inliers, the
transform **2 630 m** out). The **four** that are right land at **52.7 – 85.5 m**
(414 nm with 304 and 11 inliers, 749 nm with 243 and 14), i.e. inside the same
~85 m inter-product budget every other arm carries. RootSIFT on the identical
cells passes **0 of 36**.

So the cross-mission, cross-modality, 15.9 : 1 case **is** reachable — by the
learned engine, not by the classical one — and S4 stays **NOT MET** because the
criterion was frozen on B1, which is the right way round: the criterion
measured what it said it would, and the supplement measured why.

### 12. S5 — the thermal clause, answered with a bound

| quantity | value |
|---|---|
| ratio | **28.1 : 1** (236.9 m against the TC pan degraded to 235.8 m) |
| thermal window | **120 × 65 px**, 66.7 % valid (Amendment A1's day cycle) |
| pan window | 92 × 37 px |
| keypoints | **49** thermal, **60** pan |
| inliers | **0** |
| failure mode | **starvation** (Part 1's rule: < 50 thermal keypoints ⇒ starvation, not descriptor) |

**The envelope, stated as §2.2 asks:** on this mare window, a Diviner
bolometric-temperature map does **not** register to a panchromatic image at
28 : 1, and the reason recorded is that the thermal side yields 49 keypoints —
below the number a 6-parameter model needs to be constrained at all, before any
question of whether temperature and reflectance share structure can be asked.
A larger window, a finer thermal product, or both, is what would move it; this
stage does not have any of them and says so.

### 13. The predictions, graded

| prediction (Part 1 §4.2) | outcome |
|---|---|
| S0 MET, HIGH, with (ii) the clause that could genuinely fail | **Right**, and (ii) passed decisively: 0.0301 px |
| S1 MET, MEDIUM-HIGH, 8–9 of 9, median 0.3–1.0 reference px | **HALF WRONG.** 7 of 9 register (inside the bar), but the median error is **6.4 reference px**, six to twenty times the predicted band. The prediction assumed the two Kaguya products were mutually registered; they are offset by ~85 m |
| **the band most likely to fail is 414 nm, MEDIUM** | **WRONG.** 414 nm has the **highest contrast of all nine (0.0924)** and the second-most keypoints; the failures are the two 1000 nm bands, and §9 gives the mechanism |
| S2 MET, MEDIUM, worst ratio 1.2–2.0 | **Right**, worst ratio **1.334** |
| S3 MET at 45 % | **Wrong direction by a little**: two bands register (the criterion's count clause is met) and both miss the 60 m bar |
| S4 MET, MEDIUM, 3–6 bands on 2–4 frames | **WRONG**, 0 of 36 on B1 — and the supplement shows the learned engine reaching it |
| **S5 NOT MET at 70 %, failure mode starvation** | **Right, including the mechanism named in advance** |
| S6 MET (0 of 10), HIGH | **Right** |
| Overall: "S0, S1, S2, S4, S6 MET; S3 a coin flip; S5 NOT MET" | **Four of eight right.** The stage's central assumption — that two products of one mission on one map frame agree — was wrong, and finding that is worth more than the criteria it cost |

### 14. Defects found

**E-052 — a block offset folded into a grid origin, twice (found by the smoke
test, before any recorded statistic).** The MI mosaic manifest first wrote
`lat_top_deg = 90 − row0/ppd + 0.5/ppd` *and* kept `row0` in the manifest;
`MapBlock` subtracts `row0` again, so the grid was wrong by 69.76° — **2216 km**
— which surfaced as an error statistic of 2 216 898 m rather than as a crash.
The convention is that `lat_top_deg` / `lon_left_deg` are the **global**
graticule's edges and `row0` / `col0` carry the block offset. Fixed in the
acquisition, the block re-sliced, and the reason written into the code beside
the formula. **Same family as E-040** (a coordinate frame paired with the wrong
partner), reached by a new route.

**E-053 — S2 was evaluated against S1's bound instead of its own clause.**
Part 1 §4 S2 counts *bands that succeeded*; the runner counted *bands within
the 8.42 m bound*, which is S1's conjunct. With 7 bands succeeding and the
worst ratio at 1.334, the frozen criterion is **MET** and the artefact's field
says NOT MET. **The artefact is not rewritten** (integrity rule 4); §7 reads
the criterion as frozen and this row is the record. Third instance this
session of the same shape — a clause stated in prose and implemented as a
different clause in code (E-051, then this) — and the mechanical guard is the
same: evaluate each criterion from the artefact's own recorded per-cell fields,
in a function that quotes the Part 1 sentence it implements.

**Not a defect, recorded anyway:** the frozen Diviner product was empty over
the window and was a night cycle; Amendment A1 handled both before any
statistic.

### 15. What this stage does NOT claim (Part 1 §7, restated against the results)

Every disclaimer in Part 1 §7 stands, and two are now load-bearing:

- **This is NOT an IIRS result.** No IIRS product exists in this repository.
  Kaguya MI is 414–1548 nm at 14.8 m; IIRS is 800–5000 nm at 80 m. The word
  IIRS appears in no claim sentence, as Part 1 §6 required.
- **This is NOT accuracy.** Every number is a disagreement against a label map,
  and the two products' relative georeferencing — which the error statistic
  assumes — is measured here at **~85 m**, so no number in this stage is
  better than that floor. What *is* claimed is the **comparison**: bands
  against pan, on the same grid, with the same offset in both.
- Not a thermal-imaging result; not an illumination result (MI and TC share a
  standard geometry by construction); one mare window; one engine in every
  criterion; `assess()` untouched.

### 16. Ledger and index

- **D-062** — what the §2.2 multimodality row may now say, and what it may not:
  *nine reflectance bands of a multispectral imager register to panchromatic on
  the same map frame, seven of nine under the frozen rule, every one within
  1.334× of a pan comparator built from the same instrument; two bands register
  to Chandrayaan-2's TMC-2 ortho; a thermal map at 28 : 1 does not, by
  starvation* — and **not** that IIRS registers, nor that any of it is accurate
  better than the ~85 m inter-product term this stage measured.
- **D-063** — the inter-product term itself: MI MAP V3 and TC Ortho Seamless V2
  disagree by **~85 m** (B4L, 1360–2024 inliers), with the linear part matching
  their labels to 3e-5. Every later stage that composes these two products
  carries it.
- **E-052**, **E-053** (§14).
- `STAGE-INDEX.md`, `STAGE_HISTORY.md` and `research_log.md` rows land with
  this commit.
