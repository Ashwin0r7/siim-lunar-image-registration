# SIIM — Satellite / Lunar Image Integrity & Matching

**SIH 2026 · Problem Statement 26166 (ISRO)** · CPU-only · runs offline

> **A lunar image-registration system that refuses to report an alignment it cannot defend.**

Registration failure is not the danger in orbital imagery. **Silent** registration failure is —
an aligner that returns a confident, self-consistent, wrong answer, and a quality metric that
agrees with it. SIIM is built around that problem: it establishes overlap *before* it
interprets anything, excludes the metric the field normally trusts, corroborates against data
the matcher never saw, and states the scope of every claim it makes.

## Run it — one command

```bash
python -m pip install -e ".[dev]"
python scripts/run_demo.py --open
```

That is the whole setup. **No network access, no API keys, no build step, no GPU.** Every
real-data number in the demonstrator is read from a recorded artefact under `experiments/`
and every image is a local PNG, so it behaves identically on a disconnected laptop. If port
8000 is busy the launcher moves to the next free port and says so.

**What you will see**, in four steps on one page, for a real pair of LRO NAC frames:

| | |
|---|---|
| **1 · Do these images even overlap?** | Answered from archive corner geometry with **no pixel read and no matcher involved**, with the archive's own coordinate quantisation propagated by Monte Carlo |
| **2 · What did the matcher find?** | The unmodified RootSIFT + LO-RANSAC baseline, with its correspondences drawn on the real tiles |
| **3 · What does the evidence say?** | Inlier count, coverage, loop closure — and `fit_rmse` shown but **flagged as excluded from the verdict** |
| **4 · Should this be trusted?** | `VERIFIED` / `REJECTED` / `INCONCLUSIVE` **with the reasons**, the pre-registered pass/fail rule stated separately, and every number naming the file it came from |

Three real cases are loaded (one that succeeds, one that fails, one control) plus a
**controlled synthetic adversarial case**: an alignment that is 64 px wrong, self-consistent,
and reports a near-zero fit residual. Comparing that case against the real failing edge is the
fastest way to see what this project is actually about.

**Try it on your own hands: [`sample_images/`](sample_images/README.md).** Six folders
of real lunar images (LRO NAC, and Kaguya TC from JAXA), 16-bit PNG, north-up, ready to
drop into the live card. They include a pair that registers, two three-image loops that
reach **VERIFIED** (one on held-out ground), a NASA → JAXA cross-mission pair, and two
pairs the system **must refuse**: a 39.8° Sun change, and deliberately unrelated ground.
The result each one returns was measured by posting the exact files to the demo's own
endpoint, and is recorded in `sample_images/manifest.json` with every file's provenance
and SHA-256. On a machine with the PRADAN download, `python scripts/build_sample_images.py
--force` also writes a **Chandrayaan-2 TMC-2 → LRO NAC** pair into
`sample_images/_local_chandrayaan2/`. ISRO products are not redistributed, so that
folder is git-ignored.

## How to verify the demo evidence

The demonstrator's real-data figures are **read from recorded experiment
artefacts**, not recomputed while you watch. That is deliberate — it keeps the
page identical to the stage reports that justify it — but it means "read from a
file" and "typed into a file" look the same from the outside. Three mechanisms
exist so you don't have to take it on trust:

| | |
|---|---|
| **The overlay is certified when it is built** | `scripts/build_demo_assets.py` re-runs the identical seeded pipeline and **refuses to write** unless every recomputed statistic matches the recorded artefact exactly |
| **It is re-checked at load time** | `_check_asset_matches_artefact` in `src/siim/demo/evidence.py` re-verifies that certification on every request, so a hand-edited asset is rejected rather than displayed |
| **Tests pin the page to the artefacts** | the displayed numbers are asserted equal to the recorded ones, edge by edge |

Run the third one yourself — it takes a few seconds and needs no network:

```bash
python -m pytest tests/test_demo_real_data.py tests/test_demo_evidence_integrity.py -q
```

Those cover, among other things: displayed numbers equal recorded numbers; every
step names the artefact it came from; a missing **or corrupt** artefact produces
a clean error naming the file rather than a silent substitution; an overlay that
disagrees with its artefact is refused; and a diagnostic that *fails* is never
displayed as a diagnostic that was *not applicable*.

In the demo itself, each real case's provenance panel lists the exact repo-relative
path of every file its numbers were read from, alongside the byte ranges and
SHA-256 of the archive imagery. Open any of them and check.

### The strongest version of that check: re-derive the numbers from the pixels

Every mechanism above compares **a recorded number against another recorded
number**. A sufficiently careful hand-edit would survive all three. Re-running
the pipeline would not.

```bash
python scripts/rederive_recorded_registrations.py
```

This loads the archive tile bytes, applies each stage's preprocessing, runs the
**unmodified** baseline, and compares **54 quantities** against the recorded
artefacts — keypoint counts, putative counts, inliers, inlier ratio, fit RMSE,
both coverage metrics and the full 3×3 transform matrix, for all six real edges
of REAL-DATA-03 and REAL-DATA-04. It exits non-zero on any disagreement, and the
baseline configuration is read **out of each artefact** rather than hard-coded,
so it cannot pass by checking a configuration nobody ran.

Current result: **all 54 re-derive exactly** — including `4.138e-13 px`,
`1.885e-13 px`, and every transform matrix to `max|Δ| = 0`.

It needs the decoded tiles, which are gitignored (~166 MB, re-fetchable by the
byte ranges and SHA-256 in `data/manifests/`). Without them it exits **2** —
*cannot check* — which is deliberately a different answer from **1**, *checked
and wrong*. `tests/test_rederivation.py` runs it when the tiles are present and
**skips** otherwise, reporting the skip as "cannot check", never as a pass.

**What a pass establishes:** the recorded numbers are genuine pipeline output.
**What it does not:** that any registration is *correct*. The B→D edge
reproduces its `1.885e-13 px` fit residual to every digit while being
independently measured hundreds of pixels wrong. Reproducing a wrong answer
exactly is still a wrong answer — which is the entire point of this project.

## What is honestly claimed, and what is not

| | |
|---|---|
| **Real LRO NAC, end to end** | Byte-range fetched from the public PDS archive, SHA-256 recorded, PDS4-decoded, sanity-gated, registered by an unmodified baseline |
| **Δincidence predicts registration outcome on six edges — and on 42 pairs it is significant, necessary, and NOT sufficient** | On **six** real edges across five frames and two ground windows — successes at 0.96° and 11.73°, failures at 38.85°–51.54° — the separation is perfect and the exact one-tailed permutation test gives **p = 0.0667** (`siim.evaluation.exact_separation_test`; the direction was frozen before frame D was acquired; the edges share frames, so this is a lower bound). `[MEASURED]` REAL-DATA-07 (2026-09-05) then registered **42 geometry-confirmed pairs over 14 frames**: the pooled separation reaches **p = 0.0042** (RD-03 window 0.0040, RD-04 window 0.121), **no pair above 40° passes** under either engine, and there were **0 wrong passes in 37** (a pass whose transform is inconsistent with archive geometry). But the success rate is already 0.71 at 0–5° and 0.50 at 5–10°: **four frames failed against every partner irrespective of Δincidence**, and on 2026-09-05 the cause for at least two of them was found to be a **mirror image in the tile orientation** (E-037: the archive corner map's Jacobian has the opposite sign for 5 of the 14 census frames, and a quarter-turn cannot undo a reflection). Flipping frame E2 turns 5 inliers into **2691** against D. **The corrected run** (recorded beside the original, Part 2 amendment) **meets the replication criterion** — E2 → A 2138 consistent inliers, E2 → B fails — reaches **p = 0.0012** with both windows under 0.05, and has **0 wrong passes in 76** across three engines. The remaining frame-level failures are two frames at 72–75° incidence: the ceiling, not identity |
| **The RMSE trap, on real data** | A real edge reports a fit RMSE of `1.885e-13 px` for a transform independently measured **797 px wrong** |
| **Illumination as the cause: replicated on a second low-incidence frame** | D-040-N1's debt is discharged by the amended REAL-DATA-07 run (D-040-N2): frame E2 (21°) succeeds against A (2138 consistent inliers) and fails against B, as D did. Within the tested set no measured edge is explained by frame identity (D-040-N2 supersedes the D-040-N1 caveat); the scope stays *this mare, incidence only, below ~70°* |
| **Chandrayaan-2 TMC-2 registers to LRO NAC at 5 m — and OHRC and IIRS still do not** | `[MEASURED]` REAL-DATA-09 (2026-09-20), after the PRADAN download (23 GB, SHA-256 manifested before any product was opened). TMC-2 L2 ortho against NAC degraded to the TMC-2 GSD: **6 passes across two engines, every transform geometry-CONSISTENT, 0 wrong passes**; where both engines pass they agree to **0.619 px** and **2.570 px** against a 3 px floor. **The REAL-DATA-07 illumination envelope reproduces on ISRO's sensor**: every pair at Δinc ≤ 9.2° passes, everything ≥ 24.7° yields no transform, and the two rows above 48° are INCONSISTENT. σ_C2 = **38.75 m** is read from the label, not assumed. **What is still NOT supported:** no VERIFIED Chandrayaan-2 verdict (the single pairs are INCONCLUSIVE; the one loop, {TMC-2, NAC A, NAC D}, closes at **2.2131 px = 10.5 m** against a frozen **2.0 px** line and is **REJECTED** — the threshold was not moved); **no OHRC result** (both observations are over the South Pole, where this project holds no NAC — they ingest cleanly, so the exclusion is coverage, not format); **no IIRS result** (no product was delivered). **No multi-modal claim beyond REAL-DATA-08's measured negative** |
| **Radar ↔ optical: measured on a real proxy, and NOT registered by anything** | `[MEASURED]` REAL-DATA-08 (2026-09-05): NAC tiles degraded to 7 and 17 m against the Mini-RF S-band strip over the same mare — RootSIFT, phase congruency and DISK + LightGlue each register **0 of 16** pairs; the nearest miss is 8 inliers with a transform 193 px wrong. A PROXY for the DFSAR case, never a Chandrayaan-2 result. The multimodal claim in the problem statement is a measured negative here, not an untested one |
| **The 100 m rung: registered by the learned engine, starved for the classical one** | `[MEASURED]` REAL-DATA-08: NAC long windows degraded to 60–118 m (strips of **111 × 46 px** at the 100 m rung) against the LROC WAC 100 m mosaic. RootSIFT passes 1 of 4 frames (9 inliers); DISK + LightGlue passes 3 of 4 with **34–99 geometry-consistent inliers at ≈ 2 px against a ≈ 2.3 px floor**, and produced **one wrong pass** (9 inliers, 28 px off) — the reason no coarse-rung pass is reported without its geometry verdict. The IIRS rung of the ladder, on a real reference, by proxy |
| **The architecture's own justification, measured instead of cited** | ADR-0001 bets that *the matcher is a replaceable part; the protocol is the contribution* — and until 2026-09-21 that bet rested on a **33× protocol effect measured on SAR-optical imagery in a single preprint**, carried with an explicit transfer caveat. `[MEASURED]` **EXP-006** (reframed as a component ablation per master plan §553, which refuses the stand-alone thesis as unfalsifiable): on **42 paired real lunar pairs**, correcting **one protocol step** changes **2.18×** as many outcomes as replacing the entire matcher — mean **6.0 vs 2.75**, exact McNemar **p = 0.0156** (B4L) against **no significant matcher contrast** (p ≥ 0.25) — and the direction differs in kind: **all 12 protocol flips are improvements with 0 regressions**, while matcher swaps trade **6 gains against 5 losses**. *A protocol fix is monotone; a matcher swap is a trade.* The criterion written to refute this held: **1** pair papered over by a better matcher against **7** rescued by the step. Post-hoc mechanism check: all 12 flips carry **exactly one** E-037-mirrored frame and **none of the four two-mirrored pairs flipped** — the reflection cancels between two mirrors — at **P = 2.96e-07**. **What is NOT claimed:** the general thesis. The step measured is the one protocol component whose *both levels* happen to have been recorded, and they were recorded because a **defect was found**, not because an ablation was designed — so this licenses *at least one protocol step outweighs a matcher replacement on 42 mare pairs*, and §553's judgement on the general form **stands** (D-056). Also not claimed: significance on every matcher — B1 gives **p = 0.0625**, which does not clear 0.05 and arithmetically cannot with five one-directional discordant pairs |
| **The verdict has a blind spot, it is measured, and it is NOT closed** | The deliverable's decisive evidence is loop closure, and loop closure is **exactly** invariant to a per-image coordinate error: give every image its own gauge and the terms cancel around the composition, so the residual is zero **by algebra, not by luck**. `[MEASURED]` EXP-012's supplementary probe (E-039): **36 of 36** such cases return VERIFIED at **high** confidence through the unmodified `assess()`, with every edge wrong — by a median of **14.04 / 57.47 / 115.40 px** — while the loop closes to **1.27e-13 px**. EXP-013 then built the external check that would detect them and measured why it cannot be run here: the only external reference on hand, archive corner geometry, has a **per-frame error of its own of 66–109 px**, larger than the errors it would need to find, and at an applied gauge of **zero** the detector still alarms on **6 of 12** cases. **What is NOT claimed:** any gauge-error detection capability, and any false-acceptance rate for the verdict. **What IS claimed:** the mechanism works where the model is over-determined (explained fraction **0.845–0.857** against a structureless null whose maximum is **0.421–0.590**, in all six census graphs) and **three independent matchers recover the same per-frame term to within 1.50 px**, so it belongs to no matcher. Closing this needs a **geodetic reference**, not more software (D-054) |
| **NO ground truth on real imagery — and the corroboration resolves only to ~100 px** | None exists for these products. A succeeding real edge is *corroborated*, never verified — and the resolution of that corroboration is stated here rather than left to be found. The archive-geometry bound **discriminates at the scale of ~100 px and certifies nothing finer**: D→A's median disagreement is **56.3 px against a 105.6 px discrimination floor** (0.53×), i.e. *inside* the floor, so the check cannot separate a correct alignment from one translated by up to ~100 px. The **0.04 % / 0.13 %** `SCALED_PIXEL` agreement constrains **SCALE ONLY, not translation**. **Neither check provides any sub-pixel accuracy evidence.** `[MEASURED]` REAL-DATA-04 §11.2. **Amended 2026-09-03 (S9):** the first sentence is too broad and is left as written rather than restated. No *correspondence* ground truth exists — but **geodetic control does**, and this project has not used it. LROC NAC regional controlled mosaics have a published average positional offset **below 13 m** (median <12 m latitude, <5 m longitude), which at NAC resolution is roughly **7–26 px** against the 105.6 px floor quoted above. The accuracy claim is therefore weaker than the evidence available, not weaker than the evidence obtainable, and closing that gap is an unblocked task rather than a limitation of the data. **Amended 2026-09-23 (EXP-019): the task was done, and the first sentence of this row is now wrong in the direction it warned about.** A product from another mission — SELENE (Kaguya) TC ortho, 8.42 m, LISM control — was registered to 12 of 20 NAC tiles and to the Chandrayaan-2 TMC-2 block. The archive's corner geometry and Kaguya's control network disagree by **137.6 m median (+101 ± 74 m east)**, which is the ~100 px floor **measured** rather than estimated; and an **A → reference → B** composition containing **no A ↔ B correspondence** agrees with the recorded direct registration to **0.266 reference px = 2.24 m (CI95 0.222–0.413)**. That is an upper bound on the sum of two independent registration errors — the first accuracy-class number here that is not a self-warp — and it is **not** absolute accuracy in the SELENE frame, because both legs share the reference and its own error cancels. Manual check points remain the only route to a number with no shared instrument in it |
| **Δazimuth measured, and it does NOT explain the outcomes** | `[MEASURED]` `scripts/check_solar_geometry.py` — ground solar azimuth computed from the archive's sub-solar point. **Δincidence separates all six edges (11.73° → 38.85°); Δazimuth does not** (the strongest success sits at Δaz 50.29°, above three of four failures). **Not pre-registered** — run after the fact as a confound check |
| **Δphase and Δincidence are NOT separable here** | Every frame is near-nadir (emission ≤ 1.75°), so phase = incidence + emission and the two deltas agree to **2.56°**. Lunar photometry is **phase**-driven, so *incidence* is our **label** for the variable, not a demonstrated mechanism. Separating them needs an off-nadir frame we do not have |
| **Sub-pixel: measured on real texture, NOT on a real cross-illumination pair** | The PS's headline accuracy requirement. `[MEASURED]` EXP-010 (2026-09-04): a local ECC refinement stage (`siim.refinement`) reaches **0.003 px** median (95 % CI 0.0032–0.0033) against exact self-warps of all four recorded real NAC tiles — an **upper bound on precision**, since a self-warp shares the original's texture — and under synthetic Sun-azimuth change to 30° the refined error stays **below 0.25 px**. EXP-011: the affine default was absorbing correlated localisation error (**up to 0.99 px on frame D with a zero fit residual**, E-034); refine-then-reselect brings it to **0.0018 px** on 48/48 self-warp cases. **What is still NOT held:** any sub-pixel number on a real pair under *different* illumination — no correspondence ground truth exists, and manual check points are the only route. `check_transform_against_geometry.py` still states that it *"certifies NO accuracy, and in particular NO sub-pixel accuracy"* |
| **A licensable learned engine registers real edges at 39–40° where RootSIFT fails** | `[MEASURED]` EXP-007 (2026-09-04): DISK + LightGlue (Apache-2.0 code and weights, CPU, via kornia; SuperPoint/SuperGlue excluded under ADR-0008) registers the failing C → A edge at Δinc 38.85° with **56 inliers** and a transform **CONSISTENT with archive geometry** (47 px against a 104 px floor) where RootSIFT gives 4; at 7, 15 and 30 m it registers **three of the four** ~40° pairs with 447–2042 consistent inliers. It does **not** cross 51.54° (0, 5, 37 inliers), and it breaks neither succeeding pair. Corroborated inside the geometry floor, not verified; no ground truth. Its envelope on 42 real pairs is REAL-DATA-07 |
| **DEM-render conditioning: measured, and it carries NOTHING on this mare** | The master plan's central physics bet (H0): match each image against the 59 m SLDEM2015 rendered under its own Sun, so the illumination difference lives in the DEM rather than the matcher. `[MEASURED]` EXP-007: **0 of 4** failing pairs convert at any rung from 1.8 m to 30 m; the render side yields **0–19 SIFT keypoints** on the high-Sun frames against 560–20 700 on the images, because the height field contains none of the 10–100 m relief the images are made of. H0 was **demoted to conditional on a fine DEM** (D-046) — and then **refuted on one** (**D-052**, REAL-DATA-09 S4, 2026-09-20). The Chandrayaan-2 TMC-2 stereo DTM gives a **10.1 m DEM over a 5.05 m ortho, co-registered by construction**: a **2:1** DEM/GSD ratio against EXP-007's 59 m, spanning a **15× range**. The positive control `ortho ↔ render(own DEM, own Sun)` returns **0 inliers on 15 of 15 frames**, and a high-pass cross-correlation on a fully valid sub-block peaks **correctly at (2, 3) px** but only **0.117** high — so the failure is **photometric, not misalignment**, and it is not DEM coarseness. The physics-conditioning claim is **withdrawn from the architecture except as a verifier**; D-052 supersedes D-046 and SERENRIDGE1 is no longer the pending test. Per-frame photometric normalisation (REAL-DATA-06) turned out to be a no-op after the pipeline's own stretch (E-035); per-pixel normalisation from the 59 m DEM changes counts and converts nothing |
| **Registered product + match points: produced, for ONE edge** | The two named PS deliverables now exist for the D→A edge — `experiments/REAL-DATA-04/products/`: 1759 correspondences with full-frame pixel and archive-derived ground coordinates, the warped source tile, and a difference image. **Emitted from recorded evidence; no matcher runs and nothing is estimated.** Labelled *"a registered product; no ground truth exists for it; corroborated, not verified; class B."* An edge the pre-registered rule **rejected** is refused a product |
| **Viewpoint: measured for the first time — and the acceptance, not the model, is what fails** | `[MEASURED]` **EXP-017** (2026-09-23). The problem statement names three variations and this project had **no evidence of any kind** on the second: every real frame on disk is near-nadir (emission 1.17–1.77°) and PRADAN delivered only TMC-2's nadir band. The stage constructs an oblique view from a **real 10 m DTM co-registered by construction with a real 5 m ortho**, so the ground truth is exact — and every error is therefore an **upper bound on precision**, not an accuracy. Over 310 cells and 31 windows, **a global 2-D transform's dense median error never reaches 0.5 px anywhere in a 0–30° sweep**, so no window has an onset and **two criteria written to characterise that onset are undefined rather than refuted** — reported as nulls by construction. The mechanism is measured: peak-to-peak relief of **47–123 m** collapses to **2.85–8.93 m RMS** once a global affine absorbs the plane (the pre-registration predicted 15–40 m), which makes §20's peak-to-peak rule **early by ≥ 6×** (D-065). **What does fail is §2.2's own wording:** *"local model residuals white"* holds at **e = 0 and nowhere else** on both local arms — a smooth residual fires a whiteness test at any amplitude, including 0.032 px — so D-064 records the literal form **mis-specified** and the bound form as what may be claimed: **5°** for a 96-parameter piecewise affine, **20°** for six parameters plus the 59 m SLDEM. **A blind spot, stated:** on all 130 cells the verdict returns INCONCLUSIVE and **never REJECTED**, including at 30° with a 1.535 px p99 |
| **Multi-modality: nine reflectance bands behave like panchromatic — and it is NOT IIRS** | `[MEASURED]` **EXP-020** (2026-09-23). No IIRS product was ever delivered (RL-046), so the axis was **data-REFUSED**, not untested, and the project's whole evidence for the title word was REAL-DATA-08's radar negative. This stage asks §2.2's question with the closest public instrument of the same kind: **nine Kaguya MI bands, 414–1548 nm at 14.8 m**, on the **same map frame and the same photometric standard geometry** as the panchromatic reference, so only wavelength and GSD vary. **7 of 9 bands register** under the frozen rule and every succeeding band lands within **1.334×** of a pan comparator built from the same instrument's own band mean (six of seven *better* than pan) — so §2.2's *“reflectance bands: same envelope as pan”* is **MET**. **Two bands register to the Chandrayaan-2 TMC-2 ortho** (749 nm 72.7 m, 901 nm 80.8 m). **Thermal:** Diviner bolometric temperature at **28 : 1** gives **49 keypoints and 0 inliers — starvation**, the failure mode named in advance, which answers *“thermal: envelope stated”* with a bound. **What is NOT claimed:** that this is IIRS (the word appears in no claim sentence, D-062), and that any of it is accurate better than the **83–91 m** offset this same run measured **between two Kaguya products of one mission** (D-063) — which is also why the stage's own 8.42 m bar fails while the band-to-pan comparison passes |
| **Scale: 4× on mare, 8× on highlands — the PS implies 320:1** | `[MEASURED]` `experiments/EXP-001/scale_limit_probe.json`. **Every** failure beyond those ratios is **detector starvation**, not descriptor failure — mare yields *literally zero* SIFT keypoints at 128², which is D-026's texture poverty in its sharpest form. The fix is normalising to a common GSD before matching (D-005): **designed, not implemented**, and untestable here because no cross-modal data exists. **Amended 2026-09-23 (EXP-016): the fix was implemented, run on real NAC texture, and it did not beat leaving it out.** Both images degraded through a stated PSF to a common coarser GSD, up the ladder 2 : 4 : 8 : 16 : 32 : 64 : 128 : 320 on 11 real edges: **11/11 to 32 : 1, 8/11 at 64 : 1, 0/11 at 128 and 320** — measured envelope **32 : 1**, every failure the frozen `n_inliers <= 8` rule, **zero wrong passes at any rung in either engine**. The starvation reading above is **confirmed and separated from the ratio**: a control holding the coarse pixel count fixed while halving the ratio agrees with the full cell on **55 of 60**, and the pooled logistic gives `β_N = +2.038 (p = 0.0025)` against `β_r = +0.00018 (p = 0.9998)`. The transferable number is a **pixel floor, N\* = 2048 coarse pixels of overlap** — which makes every sensor pairing arithmetic rather than a new experiment (TMC-2/NAC clears it by 40–160×; OHRC-in-IIRS at ≈ 5 550 px clears it by 2.7×; one IIRS grid against a single 4096-line NAC tile straddles it). **And D-005 is superseded by its own ablation:** the un-normalised arm ties the normalised one **10/10 at every rung to a 16 : 1 gap**, so the pre-registered McNemar has zero discordant pairs (D-005-N1). The PS's 320 : 1 is **NOT MET as a registration** — a 12 × 6 px tile yields **zero** keypoints — and **NOT MET as a localisation** either, though both peaks land *inside* tolerance (262 m, 105 m) and fail only on sharpness (PSR 4.50, 4.23 against 5) |
| **The pipeline runs on tiles, not full frames** | `[MEASURED]` matching is O(keypoints²): 0.18 s at 0.26 Mpx, 5.68 s at 1.05 Mpx. A full 264 Mpx NAC frame extrapolates to ~100 h/edge and ~2 GB of descriptors. Every real result used 2048×1024 decimated tiles (4.5–10.1 s). Tiling is what the geometry layer is built for; **the tiling driver is not written** |
| **NOT established: that the synthetic illumination model predicts real behaviour** | The two disagree, in both directions, and we state it rather than wait to be told. EXP-001 measured Δelevation −30° (≈ Δincidence 30°) as **survivable** — 49 inliers, 0.81 px — where real Δincidence 38.85° gives **4**. EXP-003 put the Δazimuth cliff at **21–27°** on A-regimes, where real edge D→A succeeds with **1656** inliers at Δaz **50.29°**. *(That real edge also has small Δincidence, so it is not a controlled azimuth test — but the synthetic model offers no mechanism by which small Δincidence rescues large Δazimuth.)* Likely causes, none measured: Lambertian shading with cast shadows omits the Hapke backscatter and opposition surge that dominate real regolith; the synthetic scene is highlands where the real data is mare; the synthetic sweep never reaches the 70° incidence regime of frames B and C. **EXP-001/002/003 remain internally valid; their external validity to lunar imagery is unsupported** |
| **NO Sun-azimuth *invariance* claim** | Every real result is illumination-varied by **incidence** (see the two rows above for what that does and does not mean) |

The project is named for Sun-angle invariance, and the honest position is that **we measured
the classical baseline and it is not Sun-angle invariant**, and then measured a licensable
learned engine that is — to about 40° of incidence difference on this mare, and not to 52°.
Those measurements — on real archive imagery, against criteria fixed before the data existed —
are the contribution.

---

## Status

| Phase | State |
|---|---|
| Phase 0 — Research & analysis | **complete** — `docs/00_PROJECT_ANALYSIS.md` |
| EXP-000 — Geometry gate | **passed** — `experiments/EXP-000/` |
| EXP-001 — RootSIFT baseline + GT harness | **complete** — `experiments/EXP-001/` |
| EXP-002 — RANSAC fix, terrain realism, threshold + GT-free validation | **complete** — `experiments/EXP-002/` |
| EXP-003 — Illumination-robust representations | **complete — pre-registered criterion NOT met.** ADR-0004 superseded — `experiments/EXP-003/` |
| REAL-DATA-01 — Real LRO NAC ingestion | **complete — ingestion succeeded, first registration FAILED (class C / REJECTED)** — `experiments/REAL-DATA/` |
| EXP-004 — Orientation assignment | **pre-registered, NOT started.** Part 1 frozen; no implementation exists |
| REAL-DATA-02 — Establish real overlap independently of the matcher | **complete — question answered.** The REAL-DATA-01 headline pair does **not** overlap — `experiments/REAL-DATA-02/` |
| REAL-DATA-03 — The first correctly controlled real-data registration experiment | **complete — the experiment is valid; 2 of 3 edges fail, 1 succeeds** — `experiments/REAL-DATA-03/` |
| REAL-DATA-04 — Can frame identity and illumination be separated? | **complete — ANSWERED.** D↔A succeeds (1656 inliers at Δinc 11.73°), D↔B fails (3 at 51.54°). **Illumination attributed (D-040); frame identity substantially weakened, NOT conclusively refuted** — `experiments/REAL-DATA-04/` |
| REAL-DATA-05 — Does the illumination result replicate on a second low-incidence frame? | **complete — UNRESOLVED, BY DATA AVAILABILITY.** The pre-registered screen returned **zero** admissible frames at every tier and rung; no image byte was fetched and no registration was run. The replication is still owed — `data/manifests/screen_frame_e_*.json` |
| September 2 demo | **delivered** — `python scripts/run_demo.py --open` |
| EXP-010 — Sub-pixel refinement | **complete — gate, S1, S2, S3 MET; S4 undefined.** 0.003 px on real self-warps; < 0.25 px under synthetic Sun change to 30° — `experiments/EXP-010/` |
| EXP-011 — Transform model selection | **complete — gate, S2, S3 MET; S1 NOT MET.** Refine-then-reselect 0.0018 px vs 0.0975 px affine default — `experiments/EXP-011/` |
| EXP-007 — DEM-conditioned correspondence + learned engine | **complete — S2, S3, S4, S5 MET; S1 NOT MET; S6 NOT MET for the two DEM-render arms.** H0 demoted (D-046) — **and later refuted on a fine DEM, D-052, REAL-DATA-09 S4**; DISK + LightGlue admitted as engine arm (D-047) — `experiments/EXP-007/` |
| REAL-DATA-06 — Photometric normalisation | **closed — null by construction (E-035, D-048)** |
| REAL-DATA-07 — Replication + illumination envelope on 42 real pairs | **complete, amended (E-037) — amended run: S1, S2, S4, S5 MET; S3, S6 NOT MET.** Replication MET, p = 0.0012, 0 wrong passes in 76, nothing above 40°; original run preserved — `experiments/REAL-DATA-07/` |
| REAL-DATA-08 — Radar (Mini-RF) and 100 m (WAC) proxies | **complete — S1 MET; S2, S3 NOT MET.** Radar: 0 / 48 under every engine; 100 m: B4L 3 of 4 frames consistent, one wrong pass (D-050). Proxies, never Chandrayaan-2 results — `experiments/REAL-DATA-08/` |
| REAL-DATA-09 — Chandrayaan-2 ingestion and first C2 ↔ NAC registration | **complete — S0, S1, S6 MET; S4 NOT MET; S2, S3, S5 NO DATA.** TMC-2 ↔ NAC at 5 m: 6 passes, 0 wrong, engines agree to 0.6 / 2.6 px; loop 2.2131 px → REJECTED at the frozen 2.0 px line. **S4 NOT MET: H0 refuted at a 2:1 DEM/GSD ratio** (D-052) — `experiments/REAL-DATA-09/` |
| EXP-012 — Verdict calibration: is VERIFIED reachable on real data? | **complete — S1, S3, S4, S5 MET; S2 NOT MET.** The repository's **first VERIFIED verdicts**: 13/13 real triplets close at 0.37–1.34 px under unmodified criteria. S2 refuted (ρ = 0.055) — loop closure does not track edge strength. **S3 ran 2026-09-21 and is MET (0 of 36) for the wrong reason (E-039):** every kind in the frozen adversarial set is a per-*edge* error, which is exactly what loop closure is built to catch, so the criterion could not fail as its own HIGH-confidence prediction said it would — `experiments/EXP-012/` |
| EXP-013 — Gauge detection: can the verdict's known blind spot be detected? | **complete — S0 MET; S1, S2, S4, S6 NOT MET; S3 MET and vacuous.** A **bounded negative with a measured cause.** Loop closure is exactly invariant to per-image gauge error (36/36 reach VERIFIED / high with edges wrong by up to 115 px, E-039); the external check that would see it was built and **cannot be deployed with the reference this project holds** — archive corner geometry carries a per-frame disagreement of its own of **66–109 px**, and at an applied gauge of **zero** the detector still fires on **6 of 12**. Where the model is over-determined the mechanism works decisively, and **three independent engines recover the same per-frame term to within 1.50 px**. **D-054: built, not deployed** — no constant retuned, `assess()` untouched — `experiments/EXP-013/` |
| EXP-014 — Coverage metric validation (ADR-0006's acceptance test) | **complete — S0, S3, S4 MET; S1, S2 NOT MET.** **The primary coverage metric is the worst of four and it reverses.** On 681 subsets over 10 real tiles + 2 synthetic regimes, `max_uncovered_disc_ratio` places last on both measures and both arms (|ρ| **0.603** vs 0.681–0.701; AUC **0.927** vs 0.980–0.984); confound control passed (partial ρ 0.542). The asserted 0.15 is **4× too tight** — calibrated crossing **0.611**; at 0.15 worst-case local error is **0.048 px** against a 1.0 px bound. **D-055 reverses D-006** (E-042: EXP-007 was assigned this test and never ran it) — `experiments/EXP-014/` |
| EXP-006 — Protocol vs matcher, as a component ablation | **complete — S0–S5 all MET.** The project's oldest open item. On 42 paired real pairs, **one protocol step (orientation) changes 2.18× as many outcomes as replacing the entire matcher** — mean 6.0 vs 2.75, p = **0.0156** (B4L, exact McNemar) against **no significant matcher contrast** (p ≥ 0.25) — and **all 12 of its flips are improvements** where matcher swaps trade 6 gains against 5 losses. All 12 land on pairs with exactly one E-037-mirrored frame (P = 2.96e-07), so the mechanism predicts them. **Bounded claim only** (D-056): *at least one protocol step outweighs a matcher replacement on 42 mare pairs* — the universal thesis stays unsupported — `experiments/EXP-006/` |
| EXP-015 — Criterion 4 restated under the validated metric | **complete — all six criteria MET, and criterion 4 is still NOT reported as passed.** The restated criterion passes **39/39**, and the pass is worth almost nothing: the lowest edge sits **exactly on the calibrated floor** (a `>` in place of the frozen `≥` gives 38/39 **NOT MET**), the anti-vacuity bar clears by **0.58 pp**, and **36 % of the edges are judged by extrapolation** above the range the calibration sampled. **D-057: §53 criterion 4 is mis-specified** — it stays NOT MET in its original form and the restatement is **not** adopted — `experiments/EXP-015/` |
| EXP-018 — Blind validation: the frozen pipeline opened once on held-out ground | **complete — S0, S2, S4, S5 MET; S1, S3 NOT MET.** The project's **first out-of-sample test**. One window no stage had touched (Mare Tranquillitatis; **0 grep hits over 518 files**; Apollo 16 and Fra Mauro both failed the anti-vacuity gate from geometry first), ten advertised numbers frozen as predictions, run **once**. **Eight held, two failed:** *nothing passes above 40° Δinc* is **refuted** — 44.19° passes under all three engines and 57.43° under two, all geometry-consistent, **no wrong pass** (D-059); and D-051's 3 px agreement floor is **reversed by its own stated condition** at 5.24 px, on two *marginal* passes of 9 and 13 inliers (D-051-N1, constant not retuned). **What held: 0 wrong passes in 41 out-of-sample passes, and 7/7 triplets VERIFIED at 0.40–1.11 px** — the first VERIFIED verdicts on unopened ground. FA and FR remain unmeasurable — `experiments/EXP-018/` |
| EXP-017 — Viewpoint variation: where a 2-D model stops being valid over real relief | **complete — S2, S4 MET (S1b MET); S0, S1a, S3, S5 NOT MET.** The problem statement's second named variation, on which this project had **no evidence of any kind**: every real frame on disk is near-nadir and PRADAN delivered only TMC-2's nadir band. Synthetic viewpoint on real terrain — a real 10 m DTM co-registered by construction with a real 5 m ortho, 310 cells over 31 windows, exact ground truth. **The failure the stage was built around does not happen:** a global 2-D transform's dense median error stays **under 0.5 px to 30°**, so no window reaches an onset and two criteria written to characterise it are **undefined rather than refuted**. The mechanism is measured: peak-to-peak relief of 47–123 m collapses to **2.85–8.93 m RMS** once a global affine absorbs the plane — Part 1 predicted 15–40 m — so §20's rule, read as peak-to-peak, is **early by ≥ 6×** (D-065). **What does fail is §2.2's own wording:** *“residuals white”* holds at **e = 0 and nowhere else** on both local arms, because the residual is smooth at any amplitude and a whiteness test fires on smooth fields (D-064). The **bound** reading holds to **5°** for a 96-parameter piecewise affine and to **20°** for six parameters plus the 59 m SLDEM — the first measured case for orthorectifying with the DEM the deliverable actually has. The selector responds (ρ = 0.530 on model DOF, **0.949** on the held-out residual), and the **verdict rejects nothing at any angle**, including 30° with a 1.535 px p99 — a blind spot recorded beside the verdict, not patched. **Every error here is an upper bound on precision:** the oblique is the nadir image's own photons displaced by a DEM, so a real fore/aft pair would differ by ≈ 1.9 px RMS at 25° from the DTM's own height error alone — `experiments/EXP-017/` |
| EXP-019 — The controlled reference: another mission says where the ground is | **complete — S0, S1, S2, S3, S4, S6 MET; S5 NOT MET.** Every real result until now was corroborated against the archive's own corner geometry, which discriminates at 84–116 px. The **SELENE (Kaguya) TC Ortho Map Seamless V2** tile over the same mare (8.42 m, LISM/JAXA control, photometrically normalised, different agency/spacecraft/sensor/decade) was fetched once and registered against: **12 of 20 NAC tiles and the Chandrayaan-2 TMC-2 block pass** at a 6.5–10.5 : 1 cross-sensor ratio, **0 of 21** on a null block 25 km away. Archive vs SELENE control disagree by **137.6 m median** (CI95 108.5–160.3 m), **systematically eastward** (+101 ± 74 m) — the ~100 px floor, measured. **A → reference → B, built from no A ↔ B correspondence, agrees with the recorded direct registration to 0.266 reference px = 2.24 m (CI95 0.222–0.413 reference px, 17 pairs)** → the problem statement's *median < 0.5 coarser px on independent check points, with 95 % CI* is **MET**, against a frozen prediction of NOT MET. EXP-013's per-frame gauge terms track the measured archive offsets at **r = 0.751** (p = 0.026; pooled r = 0.746, p = 0.001), so its unresolved H3 **resolves toward the archive** (D-061). **S5 NOT MET:** the Chandrayaan-2 triangle closes at **2.177 reference px = 18.33 m** against the frozen 2.0 — missed by 8.9 %, line not moved — `experiments/EXP-019/` |
| EXP-021 — Verdict false acceptance and false rejection against an independent reference | **complete — S0, S5 MET; S1, S4, S6 NOT MET; S2 and S3 MET on the pooled reading and NOT EVALUABLE on the held-out site alone.** §53 criterion 3 was *unmeasurable*; every recorded edge is now labelled by composing A -> Kaguya reference -> B (no A<->B correspondence) at 8.42 m / 25.3 m lines. **Every edge the frozen ground truth could label was correct (39 of 39)**: B1 VERIFIED FDR **0 / 12**, FRR **0 / 12** (CI95 upper 26.5 %), FAR undefined. **Not reassurance, and said so:** that ground truth only admits frames that register easily (E-058), so it contains no wrong transform, and on the held-out site it reached 2 of 7 frames. Admitting single-engine legs finds **20 wrong edges, 19 rejected by the inlier rule, none VERIFIED**, and **15 of 84 VERIFIED engine-edges AMBIGUOUS** (8.8–19.8 m) on three frames. VERIFIED edges agree with the Kaguya chain to **median 1.51 m** — `experiments/EXP-021/` |
| EXP-022 — Criterion 4 at the match counts real registrations actually have | **complete — S0, S2 MET; S4, S6 MET and not reassurance; S1, S3, S5 NOT MET; criterion 4 stays NOT MET.** EXP-015's coverage floor (5/64) was calibrated on noiseless 12–200-point subsets while real VERIFIED edges carry up to 5 437 inliers. Re-run at the real counts with noise at the recorded fit RMSE, the floor is **0.359** (CI95 0.297–0.453). The **9- and 28-inlier** edges fall below it and exceed the 1 px local-error bound (3.93 px, 1.66 px). **So does a 68-inlier edge that sits above it** (1.04 px), while a 47-inlier edge at the same occupancy does not. No occupancy floor can therefore be the criterion (D-069). Every occupancy-1.0 edge is at 0.09–0.15 px; 7 of 22 edges are unsampled. Run v1 could not reach real counts (E-059) and is kept beside v2; they agree on every outcome — `experiments/EXP-022/` |
| EXP-020 — Multi-modality, measured: nine reflectance bands and a thermal map against panchromatic | **complete — S0, S6 MET; S2 MET as frozen (E-053); S1, S3, S4, S5 NOT MET.** The problem statement's title word had one piece of evidence — REAL-DATA-08's radar negative — because **no IIRS product was ever delivered**. This stage asks the question §2.2 asks of IIRS with the closest public instrument of the same kind: **nine Kaguya MI reflectance bands** (414–1548 nm, 14.8 m) on the **same map frame and the same photometric standard geometry** as the panchromatic reference, so only wavelength and GSD vary. **7 of 9 bands register** under the frozen rule and every succeeding band lands within **1.334×** of a pan comparator built from the same instrument's own band mean (six of the seven *better* than pan) — so **"reflectance bands: same envelope as pan" is MET**. **Two bands register to the Chandrayaan-2 TMC-2 ortho** (749 nm at 72.7 m, 901 nm at 80.8 m). **Thermal:** Diviner bolometric temperature at **28 : 1** gives **49 keypoints and 0 inliers — starvation**, the failure mode named in advance, which answers "thermal: envelope stated" with a bound. **What S1's 8.42 m bar actually failed on is not wavelength:** the recovered linear part matches the analytic label map to **3e-5**, and the learned engine (1360–2024 inliers) measures a near-pure **83–91 m translation between two Kaguya products of the same mission** (D-063). **NOT an IIRS result**, and the word appears in no claim sentence — `experiments/EXP-020/` |
| EXP-016 — The scale ladder to 320:1 on real lunar texture | **complete — S4 MET; S0, S1, S3, S5 NOT MET; S2 returns STARVATION.** The problem statement's third named variation, and the axis this project left untested longest: the best real evidence was a ~65:1 proxy and the synthetic probe stopped at 32:1 while measuring the *unmodified* baseline instead of the architecture's answer. 488 cells, 3 h 15 m. **The envelope is 32 : 1** — 11/11 at r = 4, 8, 16, 32; **8/11 at 64**; **0/11 at 128 and 320** — and every failure is the frozen `n_inliers <= 8` rule, never the geometry check (55 CONSISTENT, 5 INCONCLUSIVE, **INCONSISTENT never, zero wrong passes**), at rungs where the geometry floor has tightened to ~1.6 coarse px. **The ceiling is the pixel count, not the ratio, and that is measured rather than argued:** a control holding N fixed while halving the ratio agrees on **55 of 60** cells, and the pooled logistic over 143 cells gives **β_N = +2.038 (p = 0.0025)** against **β_r = +0.00018 (p = 0.9998)**. **N\* = 2048 coarse pixels** — the one number that transfers to any sensor pairing, and it puts OHRC-in-IIRS (≈ 5 550 px) *above* the floor the 320:1 rung failed at here (570 px) (D-066). **The architecture lost its own ablation:** the un-normalised arm succeeds **10/10 at every rung run** — GSD gaps to 16 : 1 — exactly as the normalised arm does, so S3's McNemar has **zero discordant pairs**, S3 is NOT MET **as a tie, not a loss**, and D-005's "required first-class pipeline stage" is superseded by note (D-005-N1); its only visible cost is a **±10 %** error in recovered scale. **S4 MET at 0.977 and twice not reassurance:** all eight successes at r = 64 are CANNOT CHECK, so it is silent where the envelope is decided, and its agreement improves in coarse pixels (0.258 → 0.094) while **worsening on the ground (1.16 → 2.93 m)**. **S5 NOT MET, localisation envelope none** — at 320 : 1 both peaks are *inside* tolerance and fail only on **PSR 4.50 / 4.23 against 5**, while one long window misses by a **constant 306.5 m at three consecutive rungs** with the sharpest peaks in the run, which is the archive corner map and not the correlator (D-067, cross-read against EXP-019's 137.6 m). **Nobody predicted this:** 11 of the 69 cells of the *natively-failing* stratum **succeed after degradation**, one with **994 inliers** where 1 : 1 gives 8 — reported, n = 3, not claimed. **E-055** (a *bit for bit* clause written across a float32/float64 dtype difference, NOT MET at a relative 3–5e-8, which gates the stage as frozen) and **E-056** (a McNemar whose power was assumed, so a perfect tie cannot be expressed) — `experiments/EXP-016/` |
| Chandrayaan-2 (OHRC / TMC-2 / IIRS) | **TMC-2 OBTAINED and measured; OHRC obtained but unusable here (South Pole, no NAC coverage); IIRS NOT DELIVERED.** No multi-modal claim beyond REAL-DATA-08's measured negative |

**Where the real data stands.** The project now ingests, decodes and verifies genuine LRO NAC
imagery from the public PDS archive end to end. **The first real registration attempt failed**
— 3 inliers at a fit RMSE of `1.575e-12 px`, correctly rejected — and REAL-DATA-02 has since
established, **independently of the matcher**, why: those two tiles were **22.75 km apart and
shared no ground at all**. That run measured nothing about the matcher, and the fit residual
was reported at a picometre for a transform between disjoint pieces of the Moon.

REAL-DATA-03 then built the experiment properly. Three real NAC tiles of the same patch of
mare, every window derived from archive geometry, **overlap confirmed before anything was
interpreted** — 97.12 %, 82.72 %, 85.00 % — and the **unmodified** baseline run on all three
edges:

| edge | Δincidence | inliers | result |
|---|---|---|---|
| A → B | **39.81°** | **4** of 9538/12420 keypoints | REJECTED, and independently measured **1614 px wrong** at a fit residual of 4.1e-13 px |
| **B → C** | **0.96°** | **5365** (inlier ratio 0.9950) | recovers a scale a SPICE-derived archive field predicts to **0.04 %** |
| C → A | **38.85°** | **4** | REJECTED |

**A failure on a valid pair is the result, and this is one.** Seven candidate causes —
overlap, mare texture, decimation, resolution mismatch, relief displacement, window
uncertainty, the affine model — are eliminated by measurement against the succeeding edge on
the same ground. At that point illumination was the only survivor and was deliberately **not**
claimed as the cause: across three frames it was perfectly confounded with frame identity.

**REAL-DATA-04 broke that confound with a fourth frame D**, against a decision table frozen
before the data existed. D↔A succeeds (**1656** inliers at Δinc 11.73°) and D↔B fails (**3**
at 51.54°) on edges whose independently confirmed overlap differs by 0.95 percentage points.
Across the six real edges now measured, every frame appears in both a succeeding and a failing
edge, and Δincidence separates all six.

**What that does and does not license.** Illumination — specifically Δ*incidence* — is the
attributed cause, in the scope D-040 states. Frame identity is **substantially weakened, not
conclusively refuted**: the argument is a join across two stages, and frames A and D each have
**n = 1** observations in the successful regime. **REAL-DATA-05 was the pre-registered
replication and it returned UNRESOLVED** — of 906 archive products, only two sit in the
required incidence band over shared ground, and both are orientation-incompatible with the
incumbents, so the screen returned zero admissible frames and the stage stopped rather than
relax a criterion. The replication is owed, and **EXP-004** (orientation assignment,
pre-registered and not started) is now the measured blocker on it.

Loop closure also met real data for the first time — three **independently estimated** edges,
residual 1201.04 px, no false closure.
See [`docs/stages/REAL-DATA_LRO_NAC.md`](docs/stages/REAL-DATA_LRO_NAC.md),
[`docs/stages/REAL-DATA-02_overlap_verification.md`](docs/stages/REAL-DATA-02_overlap_verification.md)
and [`docs/stages/REAL-DATA-03_real_overlap_registration.md`](docs/stages/REAL-DATA-03_real_overlap_registration.md).

---

## Read these first

The design documents are normative. Code that contradicts them is a bug.

| Document | What it is |
|---|---|
| [`docs/STAGE_HISTORY.md`](docs/STAGE_HISTORY.md) | **Start here.** Chronological record of how the project's understanding evolved, stage by stage |
| [`docs/00_PROJECT_ANALYSIS.md`](docs/00_PROJECT_ANALYSIS.md) | Problem analysis, candidate architectures, evaluation strategy, risk register, success criteria |
| [`docs/coordinate_contract.md`](docs/coordinate_contract.md) | Coordinate conventions, obeyed everywhere. **Read before touching `geometry/`** |
| [`docs/architecture_decisions.md`](docs/architecture_decisions.md) | Every major decision, its alternatives, and what would overturn it |
| [`docs/research_log.md`](docs/research_log.md) | Open hypotheses and the experiments that resolve them |
| [`docs/sources.md`](docs/sources.md) | External facts, their provenance, and how each influenced the design |
| [`docs/stages/REAL-DATA_LRO_NAC.md`](docs/stages/REAL-DATA_LRO_NAC.md) | The real-data stage: what was ingested, what was measured, and what the registration failure does and does not license |
| [`docs/stages/REAL-DATA-02_overlap_verification.md`](docs/stages/REAL-DATA-02_overlap_verification.md) | Whether the real tiles ever shared ground, answered from archive geometry with **no pixel read and no matcher involved** |
| [`docs/stages/REAL-DATA-03_real_overlap_registration.md`](docs/stages/REAL-DATA-03_real_overlap_registration.md) | The first **valid** real-data registration experiment: overlap confirmed first, baseline unmodified, and what the failure does and does not license |

### Stage records

| Document | What it is |
|---|---|
| [`docs/stages/STAGE-INDEX.md`](docs/stages/STAGE-INDEX.md) | Navigable per-stage summary: objective, status, key result, major failure |
| [`docs/stages/ERROR_LEDGER.md`](docs/stages/ERROR_LEDGER.md) | Every significant failure found, with root cause, fix and lesson |
| [`docs/stages/DECISION_LEDGER.md`](docs/stages/DECISION_LEDGER.md) | Every decision, its evidential status, and what would reverse it |
| [`docs/stages/STAGE_TEMPLATE.md`](docs/stages/STAGE_TEMPLATE.md) | Mandatory template — every future experiment produces a stage report |
| `docs/stages/PHASE-0_GEOMETRY.md` · `EXP-001_ROOTSIFT.md` · `EXP-002_EVALUATION_REALISM_RANSAC.md` | Full per-stage reports |

**Working rule:** a stage report is never rewritten to make a result look better. Failed hypotheses stay in, stated as they were originally believed. Negative results are first-class results.

## The core idea (provisional)

> **The matcher is a replaceable part; the protocol is the contribution.**

A benchmark of 24 pretrained matchers on cross-modal satellite registration found that *protocol* choices — tiling, normalisation, transform model, RANSAC threshold — change mean error by up to **33×** for a fixed matcher, exceeding the gap between top-tier and mid-tier models. So the architecture is a fixed geometric protocol with a **swappable matcher engine**, and the engine is selected by measurement rather than assumption.

This is a hypothesis carried over from SAR-optical imagery, not an established lunar result — and its source is a **single preprint** (`docs/sources.md` S4), carried with an explicit transfer caveat. **EXP-006 tested it on 2026-09-21, reframed as a component ablation** (master plan §553 refuses the stand-alone thesis as unfalsifiable as phrased). On 42 paired real lunar pairs **one protocol step changes 2.18× as many outcomes as replacing the entire matcher** — mean 6.0 vs 2.75, p = **0.0156** against no significant matcher contrast — and **all 12 of its flips are improvements**, where matcher swaps trade 6 gains against 5 losses: a protocol fix is monotone, a matcher swap is a trade. **What that licenses is bounded** (D-056): *at least one protocol step outweighs a matcher replacement on 42 mare pairs.* The step used was the one whose both levels happened to be recorded, and recorded because a defect was found rather than because an ablation was designed, so **the general claim above is still a design rationale and nothing more** — §553 stands. Until a component *designed* as an ablation is run, the general thesis above is a design rationale and nothing more, and the project reports the refutation if that is the outcome.

## What this system is built to do that the obvious version does not

- **Measure accuracy non-circularly.** Reprojection RMSE over RANSAC inliers is a *fit* statistic: it falls monotonically as you tighten the threshold, and it cannot detect a match set uniformly shifted by one crater spacing. Accuracy is instead evidenced by **synthetic ground truth** and **loop closure over image triplets**. K-fold held-out residuals and cycle consistency are retained as **degeneracy detectors only** — ADR-0011 measured their detection of a coherent wrong solution at **0.200**, and forbids describing them as protection against one. Headline claims quote the *worst* applicable estimator.
- **Handle the real scale ladder.** Sensor GSDs mandate ratios of 2:1 up to **320:1** (OHRC↔IIRS). The unmodified baseline is measured to hold to **4× on mare and 8× on highlands** (`experiments/EXP-001/scale_limit_probe.json`), and every failure beyond that is **detector starvation**, not descriptor failure. Scale normalisation to a common GSD is therefore **designed as a first-class stage (D-005) and is NOT implemented** — the gap is stated, not closed, and it is untestable here because no cross-modal data exists.
- **Survive shadow motion.** Measured against exact ground truth on terrain matched to published LOLA slope statistics: a RootSIFT baseline fails between **Δazimuth 15° and 30°** — a cliff, not a slope. We expected the break at 180° from shadow *reversal*; it arrives far earlier, because shadow *movement* alone changes gradient orientations. Contrast normalisation cannot repair it, since it preserves sign. Sun elevation is survivable by comparison.
- **Know that a confident answer can still be wrong.** A correspondence set displaced by exactly one crater spacing is 64 px wrong and perfectly self-consistent: fit RMSE reads ~0, held-out residual reads 0.47 px. Measured: `fit_rmse` scores **ROC AUC 0.495** as a failure detector — chance. Only **loop closure** over three images catches it (100% detection, 0% false alarm).
- **Know when it has failed.** A system that is right 90% of the time and knows which 10% is worth more operationally than one that is right 95% and cannot tell you when it is not.

## Reproducing the experiments

**None of this is needed to evaluate the project** — see *Run it* at the top of this file.
Everything below re-derives results that are already recorded under `experiments/`.

```bash
python -m pip install -e ".[dev,viz,experiments,learned]"   # learned = torch (CPU) + kornia
# The learned engines fetch their weights once into ~/.cache/torch/hub (DISK, LightGlue via
# kornia; XFeat via torch.hub from a PINNED commit of verlab/accelerated_features -- that one
# is executable code downloaded at first use, stated here rather than hidden). Offline after that.
python -m siim register SRC REF --out DIR    # two images in, four deliverables out (see src/siim/cli.py)
python -m pytest tests/ -o addopts="" -q   # 768 passed, 2 skipped (2026-09-05)
                                      # (4 skipped on a fresh clone: the two
                                      #  re-derivation tests report CANNOT CHECK
                                      #  until the gitignored tiles are fetched)
```

Every real-data number is a function of the OpenCV SIFT build, so the exact
environment that produced the recorded artefacts is written down in
[`requirements-frozen.txt`](requirements-frozen.txt) — a record, not a
lockfile. `pip install -e` above remains the documented install; use the frozen
file only to reproduce the artefacts bit-for-bit.

**Offline** — synthetic experiments, no network:

```bash
python scripts/run_exp000.py          # geometry gate measurements
python scripts/run_exp001.py          # classical baseline vs synthetic ground truth
python scripts/run_exp002_ransac.py   # LO-RANSAC defect: before/after
python scripts/run_exp002_terrain.py  # terrain realism + regime comparison
python scripts/run_exp002_threshold.py  # failure threshold, disjoint validation
python scripts/run_exp002_gtfree.py     # GT-free estimators vs coherent wrong answers
python scripts/run_exp010.py            # sub-pixel refinement (needs the real tiles for S1)
python scripts/run_exp011.py            # model selection, refine-then-reselect (real tiles)
```

**Real tiles, DEM and the learned engine** (the tiles and the SLDEM window are gitignored; the
DISK/LightGlue weights are fetched once by kornia into `~/.cache/torch/hub`):

```bash
python scripts/run_exp007.py            # DEM render + photometric + learned arms, 84 min CPU
python scripts/run_real_data_07.py --window RD03 --overlap overlap_rd03.json   # then RD04, --evaluate
python scripts/run_real_data_08.py      # radar and 100 m proxies
```

**Requires network, and re-fetches ~166 MB of archive imagery.** The decoded tiles are
gitignored; the manifests under `data/manifests/` carry the byte ranges and SHA-256 that make
them reproducible. The demonstrator does **not** need any of this.

```bash
# the two named PS deliverables, from RECORDED evidence -- runs NO matcher
# and estimates nothing; needs the tiles only for the warp
python scripts/register_real_triplet.py --emit-product        --manifest real_quad_d_geo_manifest.json --outdir REAL-DATA-04        --overlap-artefact experiments/REAL-DATA-04/overlap_real_data_04.json

# real LRO NAC (network; tiles are gitignored and must be fetched once)
python scripts/acquire_real_pair.py     # observational labels + byte-range image tiles
python scripts/check_real_tiles.py      # Phase-6 sanity checks + diagnostic figures
python scripts/register_real_pair.py    # UNMODIFIED baseline on the real pair

# does the pair actually share ground? (metadata only, ~130 KB, no image bytes)
python scripts/fetch_index_geometry.py  # named frame corners from the PDS archive index
python scripts/verify_tile_overlap.py   # tile overlap in km2 -- NO pixels, NO matcher

# a valid real experiment: geometry-driven windows, gated on confirmed overlap
python scripts/acquire_real_pair.py --from-geometry real_pair_index_geometry.json \
       --products nac.m1271742202lc,nac.m1335207975rc --out real_pair_usable_geo_manifest.json
python scripts/verify_tile_overlap.py --manifest real_pair_usable_geo_manifest.json \
       --outdir REAL-DATA-03 --require-confirmed        # THE GATE: non-zero unless CONFIRMED
python scripts/register_real_pair.py --manifest real_pair_usable_geo_manifest.json \
       --outdir REAL-DATA-03
python scripts/register_real_triplet.py                 # 3 INDEPENDENT edges + loop closure
python scripts/check_transform_against_geometry.py \
       --manifest real_triplet_geo_manifest.json \
       --registration experiments/REAL-DATA-03/loop_closure_triplet.json
```

CPU-only by design — no CUDA required at any point in the delivered pipeline.

## Layout

```
src/siim/geometry/     coordinate contract, transforms, estimation, resampling  [done]
src/siim/data/         synthetic lunar terrain + physically shaded GT pairs      [done]
src/siim/matching/     RootSIFT detection and descriptor matching                [done]
src/siim/verification/ LO-RANSAC robust estimation                               [done]
src/siim/evaluation/   GT metrics, coverage, failure taxonomy, GT-free estimators [done]
src/siim/baselines/    B0-B7 classical engines + B4L DISK/LightGlue (Apache-2.0)  [done]
src/siim/preprocessing/ photometric models, DEM render under a given Sun          [done]
src/siim/refinement/   per-correspondence sub-pixel ECC refinement (EXP-010)      [done]
src/siim/pipeline/     estimate -> refine -> re-estimate -> verify; engine agreement [done]
src/siim/ingest/       PDS4 decoding, byte-range fetch, map grids, DEM, orientation [done]
src/siim/demo/         verdict engine + FastAPI demonstrator                      [done]
src/siim/cli.py        `python -m siim register`: two images in, four files out   [done]
docs/                  normative design documents
tests/                 property tests pinning the coordinate contract
scripts/               experiment runners
experiments/           EXP-XXX: config, metrics, findings
```

Further modules are added when a stage exists, not upfront.
