# Demo video — run sheet

**Superseded for the SIH 2026 submission (2026-09-28):** the operative
recording script is `D:/MyData/downloads/SIH-submission/09_Demo_Video_Shooting_Card.md`
(full reference: `05_Demo_Video_Script.md` beside it). Those carry the EXP-023
OHRC scene and the current counts; this file predates them and its counts are
stale. Kept for its beat structure and fallback notes.

**What this is.** Everything needed to record the submission video in one take:
the pre-flight checks, the exact click order, the words to say, the number to
point at in each shot, and what to do when something goes wrong on camera.

**Length target 7:30**, rewritten 2026-09-23 when four modules and a live
path were added. Every beat has a timecode.

**If you are capped at five minutes**, cut in this order: beat 8 (ablation),
then beat 9b's viewpoint and modality paragraphs (keep scale), then beat 10
(provenance). **Never cut beat 5** (the trap), **beat 7** (what the system can
still be wrong about), or **beat 9c's refusal** (the live REJECTED with no
registered image). Those three are why this entry is not interchangeable with
every other one — everybody else will show you an alignment that worked.

**The one rule: never say a number the page is not showing.** Every figure on
screen is read from a recorded artefact and the page prints that artefact's
path beside it. That is the whole pitch, and it is the only part that cannot
be faked. Every number in this script has been checked against the live page
— the beat that quotes it also puts it on screen.

**Note added 2026-09-23 (later): two things on the page changed, and two beats
get easier.** *(The sheet below is kept as written; read it with these in mind.)*

- **Beat 9c's live run no longer needs files ready on disk.** The live card now
  lists the **real lunar sample sets** (`sample_images/`). One click loads a set,
  and a three-image set fills the third slot. On camera, click **"Three
  overlapping frames"** then **Register triplet**: it returns **VERIFIED, loop
  0.0669 px**, measured in the browser. For the refusal, click **"39.8 deg of Sun
  change"**: it returns **REJECTED, 4 inliers**, with no registered image drawn.
  On the recording machine the **Chandrayaan-2 TMC-2 → LRO NAC** card leads the
  list (**INCONCLUSIVE / low, 36 inliers**). Say *"local only — ISRO's products
  are not redistributed"* while it is on screen.
- **Module 02 now answers "how often is VERIFIED wrong?"** (EXP-021) under the 13
  triplets: **0 / 12** against another mission's reference, **1.51 m** median
  error on the ground, and **NOT EVALUABLE** on the held-out site in red beside
  it. If you show the zeros, show the red tile in the same shot. The panel's own
  "why the zeros are not reassurance" block is the line to read aloud.

---

## 0. Pre-flight — 10 minutes before recording

| # | check | command / action | expected |
|---|---|---|---|
| 1 | No heavy job is running | `Get-CimInstance Win32_Process -Filter "Name='python.exe'"` | **only `run_demo.py`.** This is the one check you cannot skip — see the box below |
| 2 | Tests green | `python -m pytest -o addopts="" -q` | all pass. Read the count off *this* run for beat 10; do not quote it from memory |
| 3 | Demo starts | `python scripts/run_demo.py --open` | it prints every real-data artefact it looked for, then a URL. **Read that printout** — a missing artefact appears here, not on camera |
| 4 | Page loads | browser opens at `http://127.0.0.1:8000/` (or the next free port) | hero, then modules 01–11 and the **Live** card in the nav |
| 5 | Offline is real | turn Wi-Fi **off**, reload | identical page. Say so on camera; it is true and it is rare |
| 6 | Frame is clean | 1920 × 1080, zoom 100 %, bookmarks bar hidden (`Ctrl+Shift+B`), notifications off | the page is near-black; a white bookmarks bar ruins the shot |
| 7 | Cursor is slow | ~1 s per scroll step | fast scrolling through a dense page reads as panic |
| 8 | Three cases present | the case strip shows `D → A`, `B → D`, `A → B` | all three are real LRO NAC. No synthetic case is on the page |

> **Do not record while a stage runner is going — measured, not guessed.**
> On 2026-09-22, with two stage runners holding the CPU (one at 3.6 GB), this
> page's DOM was verifiably complete and correct — every panel, every number —
> while Chrome's compositor could not keep up: a screenshot request timed out
> after 30 seconds, and later captures came back as blank black frames. The
> page was fine; the machine was not. On camera that looks like a broken
> demo, and no one watching will believe otherwise. **Check item 1 first,
> every time.**

**Recording:** 1080p30, microphone only, capture the browser window — not the
whole desktop.

---

## 1. Cold open (0:00–0:20)

**Shot.** Hero, full screen. Do not scroll.

> "Lunar image registration has a failure mode that looks exactly like
> success: a fitted residual so small it reads as perfect, on an alignment
> that is hundreds of pixels wrong. In ninety seconds I will show you that
> case, on real data, and show this system refusing it."

**Point at** the line under the headline — *every number on this page is read
from a recorded artefact on real LRO NAC / Chandrayaan-2 data. No synthetic
data appears on this page.*

---

## 2. What it is (0:20–0:35)

> "SIIM registers Chandrayaan-2 optical imagery to LRO NAC across Sun angle
> and scale. Three real cases are on this page, and one panel registers a
> pair you upload, live in the request. Every other number was recorded by an
> experiment whose criteria were frozen in Git before the data existed."

---

## 3. The gate before the pixels (0:35–1:10)

**Shot.** Case `D → A` (selected by default). Scroll to **step 1 of 4**.

> "Step one is not matching. Before a single pixel is read, the system proves
> the two images see the same ground, from the archive's own named corner
> coordinates. Seventy-one point three per cent shared footprint; tile centres
> one metre apart. And the uncertainty is propagated, not assumed away — four
> thousand Monte Carlo draws over the archive's corner quantisation put the
> pessimistic bound at sixty-eight per cent, still above a criterion fixed in
> advance."

**Point at:** `71.30%` → `1 m` → the `50% · confirm criterion` mark.

> "It is a gate, not a display: a separate command exits non-zero unless every
> edge is confirmed, and it ran before the registration below."

---

## 4. The matcher, and the signal that is excluded (1:10–1:45)

**Shot.** Step 2, then step 3.

> "Now the matcher — unmodified RootSIFT, affine, seed zero. Seventeen
> fifty-nine candidates, sixteen fifty-six survive geometric verification.
> Blue survived, red was rejected."

**Point at:** `1759` → `1656` → the overlay.

> "Step three lists every signal with what it was *measured* to be worth. Look
> at the bottom row: fit RMSE — the number most pipelines report as confidence
> — is shown and **excluded from the verdict**. We measured it as a failure
> detector: area under the ROC curve, zero point four nine four seven, on a
> hundred and ninety-two unseen cases. That is a coin flip."

**Point at:** the `fit_rmse ... EXCLUDED` row.

> "Verdict: **INCONCLUSIVE** — not VERIFIED — with sixteen hundred inliers and
> nothing against it, because the one check that catches a self-consistent
> wrong answer needs a third overlapping image and this case has two. The
> system reports incomplete evidence instead of assuming a pass."

**Point at:** `INCONCLUSIVE`, then the *Why not "VERIFIED"?* block.

---

## 5. The trap — the most important 45 seconds (1:45–2:30)

**Shot.** Click case **`B → D` — large illumination difference`**. Scroll to
**step 3**. The page has a block built for exactly this: **"THE RMSE TRAP —
WHAT THE MOST-QUOTED NUMBER DOES HERE"**, four numbered panels. Walk them
left to right and **slow down — this is the beat of the whole video.**

> "Same system, same settings. Two real frames fifty-one point five degrees
> apart in solar incidence. And now look at the fit residual."

**Point at panel 1 —** *The fit RMSE looks flawless* — `1.885e-13 px`.

> "One point eight eight five times ten to the minus thirteen pixels. A
> conventional pipeline reports that as a sub-picometre registration. It is the
> number most systems would put on the slide."

**Point at panel 2 —** `3 / 29 inliers`.

> "Three of twenty-nine correspondences survived. An affine model has six
> degrees of freedom — with three points it fits its own correspondences
> exactly and can still be arbitrarily wrong. **The residual is small because
> the evidence is thin.** That is the whole mechanism."

**Point at panel 3 —** `gap 0.4268 · occupancy 0.047`.

> "Forty-three per cent of the overlap has no nearby constraint. The transform
> is extrapolating almost everywhere."

**Point at panel 4 —** `REJECTED`.

> "Verdict: rejected — on inlier count, a rule frozen before this data
> existed."

**Now scroll to the corroboration block at the bottom of step 4.**

> "And here is how wrong it actually was. Independent archive geometry — a
> field the matcher never sees — puts that transform **seven hundred and
> ninety-seven point five pixels** off, against a discrimination floor of
> eighty-two point seven. Nine point six times the floor: not a borderline
> call. The SPICE-derived pixel scale disagrees by seventy-eight and a hundred
> and seven per cent against a one point seven per cent tolerance."

**Point at:** `797.5 px vs 82.7 px floor (9.64×)` → `INCONSISTENT`.

> "So the fit residual was not merely uninformative here — it was **inverted**.
> The failing edge reports ten to the minus thirteen; the succeeding edge you
> just saw reports zero point eight eight. And note the order: the geometry
> check is corroboration applied *after* the decision. It never moves an edge
> across the line."

---

## 6. Why it failed — the envelope (2:30–3:00)

**Shot.** Module 01.

> "Every measured real edge, against illumination difference. Every success is
> at or below eleven point seven degrees; every failure at or above thirty-
> eight point eight. And the control that makes that meaningful is stated
> beside it: **every frame appears in both a succeeding and a failing edge**,
> so no frame's identity predicts the outcome. It is the illumination."

**Point at:** the scatter, then the `CONTROL` block.

> "The p-value is zero point zero six six seven, which does **not** reach
> point zero five — and the page says so instead of rounding it down. Every
> panel here carries a list of what the result is **not**."

**Point at:** the `NOT CLAIMED` list.

---

## 7. Does it ever say VERIFIED — and what can it still be wrong about? (3:00–3:55)

**Shot.** Module 02.

> "Yes. Thirteen real triplets, thirty-nine edge verdicts, all VERIFIED, loop
> residuals from zero point three seven to one point three four pixels against
> a two-pixel reject line — and not one threshold was changed to get there."

**Point at:** `13 / 13` → `0.37–1.34`.

> "The same run refuted one of our own predictions: we expected the loop
> residual to track edge quality. Spearman rho came back zero point zero five
> five. Refuted, reported, still on the page."

**Then module 03. This is the honesty beat — do not rush it.**

> "And this panel is the one I would keep if I could keep only one. Loop
> closure has an error it cannot see — by algebra, not by accident. Give every
> image its own coordinate error and the terms cancel around the loop. So we
> built those cases and ran them through the shipped verdict, unchanged:
> **thirty-six of thirty-six come back VERIFIED, high confidence, with edges
> wrong by up to a hundred and fifteen pixels and the loop closing to ten to
> the minus thirteen.**"

**Point at:** the `36 / 36` rows, the `115.40 px` and `1.271e-13 px` columns.

> "We then built the detector for it — and measured that it **cannot be
> deployed** with the reference we hold. Four of its six criteria are NOT MET,
> and they are on this page. It runs beside the verdict, never inside it, and
> nothing was retuned to make it look better."

**Point at:** the `NOT MET` marks.

---

## 8. Why a protocol, not a better matcher (3:55–4:20)

**Shot.** Module 04.

> "One architectural measurement. On the same forty-two real pairs, correcting
> **one step of the protocol** moves two point two times as many outcomes as
> replacing the entire feature matcher — and moves every one of them for the
> better, twelve of twelve, where swapping matchers trades six gains against
> five losses. A protocol fix is monotone; a matcher swap is a trade."

**Point at:** `2.18×` → `12 / 12` → `6 / 11`.

> "And the claim is bounded on the page: this licenses *at least one* protocol
> step outweighing a matcher replacement — not the general thesis. We ruled
> our own general claim unfalsifiable as phrased and left that standing."

---

## 9. Chandrayaan-2 — the sensor the problem statement names (4:20–5:00)

**Shot.** Module 06.

> "ISRO's own sensor. Chandrayaan-2 TMC-2, from PRADAN — twenty-three
> gigabytes, SHA-256 manifested before any product was opened — registered to
> LRO NAC at five metres. Six passes across two independent engines, **zero
> wrong passes**: every success consistent with archive geometry."

**Point at:** `6` → `0` → the `CONSISTENT` column.

> "And the envelope measured on NAC-to-NAC pairs reproduces on a different
> spacecraft: everything at nine point two degrees or below passes, everything
> at twenty-four point seven or above produces no transform at all."

> "The cross-mission loop closes to two point two one pixels — ten and a half
> metres — against a two-pixel line frozen before the data existed. So the
> verdict is **REJECTED**, and we did not move the threshold. That is the
> honest state of the Chandrayaan-2 result, and it sits on the page next to
> the six passes."

**Point at:** `2.21 px` → `REJECTED`.

---

## 9a. Against what? — the controlled reference (5:00–5:35)

**Shot.** Module 07. Land on the tile that reads **137.6 m**, then the one that
reads **2.24 m**.

> "Everything you have seen so far was checked against the archive's own
> corner geometry, and we have always said that only resolves to about a
> hundred pixels. This week we stopped saying *about*. We brought in a
> product from a different mission — Kaguya, a different agency, a different
> spacecraft, a different decade, tied to its own control network — and
> registered it to twenty of our tiles."

**Point at:** `137.6 m`.

> "The archive and Kaguya's control network disagree by a hundred and
> thirty-seven metres, systematically eastward. That is the hundred-pixel
> floor, measured instead of estimated."

**Point at:** `2.24 m` and the CI beside it.

> "And here is the number we could not produce until now. Register A to the
> reference, the reference to B — never A to B — and compose. That chain
> agrees with the direct registration to **two point two four metres**, with
> a confidence interval, on seventeen pairs. It is the first accuracy-class
> number in this project that is not the image checked against itself."

**Say the limit out loud. Do not let a judge find it:**

> "It is a bound on the sum of two registration errors, not an absolute
> accuracy — both legs share the reference, so the reference's own error
> cancels. Manual check points are the only way past that, and we say so on
> the page."

---

## 9b. The three variations the problem statement names (5:35–6:35)

*This is the beat that answers the brief directly. Move quickly — three
modules, one sentence each, one number each.*

**Shot.** Module 08. The four tiles.

> "Scale. The problem statement asks for two-to-one through three-hundred-
> twenty-to-one. We built the ladder on real imagery and it stops at
> **thirty-two to one**."

**Pause. Then the second tile.**

> "The useful part is *why*. We ran a control that halves the ratio while
> holding the pixel count fixed. The ratio's coefficient comes out at
> **zero point zero zero zero two, p equals zero point nine nine nine**. It
> is not the ratio. It is the number of pixels — and that number is
> **two thousand and forty-eight**."

**Point at:** the arithmetic table.

> "Which turns every sensor pair into arithmetic instead of another
> experiment. The pairing the problem statement actually names — the
> high-resolution camera inside the hyperspectral grid at three-twenty to one
> — holds about five and a half thousand pixels. That is **above** our floor.
> The rung that failed on our disk had five hundred and seventy."

**Shot.** Still module 08, the arm-N table.

> "And this one costs us something. Our own architecture says scale
> normalisation is a required stage. We ablated it. Without it, ten out of
> ten, at every rung. It ties. We superseded our own decision and left the
> row in the ledger."

**Shot.** Module 09.

> "Viewpoint. We had no evidence of any kind — every frame we hold is
> near-nadir. So we built an oblique view from a real terrain model on a real
> orthoimage, where the ground truth is exact. A flat model holds to thirty
> degrees. What fails is the problem statement's own wording — *residuals
> white* — which holds at zero degrees and nowhere else, at amplitudes as
> small as three hundredths of a pixel. We report that as mis-specified, with
> the measurement that shows it."

**Shot.** Module 10.

> "Multi-modality. No hyperspectral product was ever delivered to us, so we
> asked the same question with the closest public instrument: nine reflectance
> bands on the same map frame. **Seven of nine register**, all within
> one-point-three times the panchromatic comparator. Thermal starves — forty-
> nine keypoints, zero inliers — and we state that as a bound. It is not
> IIRS, and that word appears in no claim we make."

---

## 9c. Now do it to our system, live (6:35–7:05)

*The only beat where the machine is not reading a recorded file. If the room
has a laptop, this is the moment to hand it over.*

**Shot.** Click **Live** in the nav. Drop the two example images.

> "Everything so far is recorded and traceable. This is not. Drop two images
> and it registers them here, in this request, and labels the result live."

**Let it run. Land on the verdict.**

> "INCONCLUSIVE — because two images cannot close a loop, and loop closure is
> the only check we measured that catches a coherent wrong answer. The page
> says so and then tells you what to do about it."

**Click the third slot. Drop the third image. Run.**

> "Three images, three independent edges, and the composition returns to the
> identity. **VERIFIED.** Same verdict code, same frozen thresholds, on
> images it has never seen."

**Then the refusal — this is the part to keep if you cut anything else:**

> "And here is one it refuses."

**Load the forty-degree pair. Run.**

> "Five inliers. **REJECTED** — and notice what is *not* on the screen. There
> is no registered image. It will not hand you an alignment it cannot
> defend."

---

## 10. Provenance — the close (7:05–7:30)

**Shot.** Module 11 — provenance. Click one artefact link.

*(It was module 07 before the reference, scale, viewpoint and modality
panels were added; provenance is now the last module on the page.)*

> "Every figure you have seen names the file it came from. Here are the
> products, the byte ranges we fetched, and the SHA-256 of those bytes."

**Click** `experiments/REAL-DATA-04/loop_closure_real_data_04.json`.

> "That is the file on disk, unmodified — and a test suite keeps the page from
> drifting from it."

**Back to the page, end on the hero.**

> "Twenty-five completed pre-registered stages, each with its criteria frozen
> in Git before its data existed. An error ledger with fifty-six entries —
> our own mistakes, including the ones that invalidated our own criteria, and
> the two from this week that say a criterion we wrote could never have been
> satisfied. A decision ledger with sixty-seven, and one of them supersedes
> our own architecture because its ablation tied. Negative results published
> so nobody repeats them."

> "We built a system that refuses to certify what it cannot defend. Then we
> held it to the same standard."

---

## 11. If something breaks on camera

| symptom | do this |
|---|---|
| A panel reads `CANNOT CHECK` or is blank | say *"that artefact is not on this machine"* and move on — honest, one line. **Do not** reload mid-take |
| A `503` in a case | the artefact is missing; the page names the missing file rather than substituting anything. Say that, switch cases |
| Page stutters | a stage runner has the CPU. Stop, wait for it, restart the take |
| Port is not 8000 | use the URL the launcher printed |
| Stale tab | hard-reload (`Ctrl+Shift+R`) **between** takes, never during one |

---

## 12. The thirty-second version

> "Lunar registration fails in a way that looks like success. We have the case
> on real data: a fit residual of ten to the minus thirteen pixels on a
> transform that is seven hundred and ninety-seven pixels wrong. SIIM proves
> two images see the same ground before it reads a pixel, decides from signals
> whose worth it has measured, excludes the fit residual because we measured it
> to be a coin flip, and returns VERIFIED, INCONCLUSIVE or REJECTED with the
> reason. It registers Chandrayaan-2 TMC-2 to LRO NAC at five metres with zero
> wrong passes — and it tells you, on the same page, the one error it still
> cannot see."

---

## 13. Questions judges will ask, and the honest answer

| question | answer — all of it already on the page |
|---|---|
| "Is it sub-pixel accurate?" | "Our 0.003 px figure is a **precision** bound measured on self-warps — not accuracy. Accuracy needs independent check points and we have none; a geodetically controlled reference is the next acquisition. We say that rather than quoting the number as accuracy." |
| "Why INCONCLUSIVE and not VERIFIED?" | "Loop closure needs a third overlapping image. With three, the system does return VERIFIED — module 02, thirteen of thirteen." |
| "Can it be fooled?" | "Yes, and we measured exactly how: thirty-six of thirty-six per-image gauge cases reach VERIFIED with high confidence. Module 03. We built the detector and measured it undeployable with the reference we hold." |
| "It says multi-modal. Where is IIRS?" | "No IIRS product was delivered by PRADAN, so we make no spectral claim. Our only cross-modality evidence is a measured negative — radar, zero of forty-eight — and it is on the page." |
| "Where is OHRC?" | "Both OHRC observations delivered are over the South Pole, where we hold no NAC coverage. We report no data rather than moving the target." |
| "Did you tune anything to make it pass?" | "Criteria are committed to Git before each experiment runs. Two of our own success criteria are NOT MET, and one we measured to be mis-specified. They are still NOT MET." |
| "How fast is it?" | "Five to fifty seconds per 2048 × 1024 tile pair on a laptop CPU. No GPU, offline, deterministic under a seed." |
| "What is actually novel?" | "Not a single component — RootSIFT, LightGlue, ECC and DEM rendering all exist. What does not exist in the literature we found is the evaluation protocol: fit residuals excluded **by measurement**, success decided by a rule frozen before the data, and coherent-wrong answers caught by evidence independent of the matcher." |
