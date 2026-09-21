# EXP-006 — Protocol vs matcher, as a component ablation

**Part 1 — pre-registration. FROZEN 2026-09-21, before any contrast, flip count
or test statistic has been computed.** Part 2 is empty until Part 1 is
committed.

**Classification: DELIVERABLE-CRITICAL.** This is the oldest open item in the
project and the one a reviewer is most entitled to ask about.

`STAGE-INDEX.md` has carried this row since the index existed:

> **NOT STARTED and NOT PRE-REGISTERED.** Unlike EXP-004 there is no frozen
> Part 1, no hypotheses, no success criterion and no artefact directory. It is
> referenced in the README and in four design documents as the experiment that
> would settle the thesis; **it is a named intention, not a registered stage.**

The thesis it was meant to settle — *the matcher is a replaceable part; the
protocol is the contribution* — is the claim the whole architecture (ADR-0001)
is organised around, and the only evidence behind it is a **33× protocol effect
measured on SAR-optical imagery in a single preprint** (`sources.md` S4),
carried with an explicit transfer caveat. That is a citation, not a result.

**Why it is being run now, and differently.** `MASTER_RESEARCH_AND_ARCHITECTURE_PLAN.md`
§553 refuses the original framing outright:

> EXP-006 as a stand-alone "protocol vs matcher" thesis — *Why it fails:* the
> 33× figure is SAR-optical; the thesis is unfalsifiable as phrased.
> *To revive:* **reframe as the component ablation of GAPC.**

So this stage does **not** ask "is the protocol more important than the
matcher?", which has no truth value as stated. It asks a bounded, falsifiable
version of it.

---

## 1. The question

**Q.** On the 42 real geometry-confirmed lunar pairs this project has already
registered: does changing **one step of the protocol** move more pair outcomes
than **replacing the entire feature matcher**?

Either answer is a result:

- **If the protocol step moves more**, ADR-0001's architectural bet is
  supported on lunar data for the first time, in a bounded form that names
  exactly which step and how much — replacing a citation with a measurement.
- **If the matcher moves more**, the thesis is refuted on this data, ADR-0001
  is demoted, and the deliverable must stop describing the matcher as a
  replaceable part.

## 2. Why this is answerable from recorded artefacts, and what that costs

**No tile is re-matched and no engine is re-run.** REAL-DATA-07 was executed
twice over the identical 42 pairs — once with the Part 1 quarter-turn
orientation, and once after **E-037** found that five of the fourteen census
frames are mirror images by their own corner metadata and a quarter-turn cannot
undo a reflection. Both runs are on disk and both are preserved:

| arm | artefact | orientation step | engines |
|---|---|---|---|
| original | `rows_rd03.json`, `rows_rd04.json` | quarter-turn | B1, B4L |
| amended | `rows_rd03_nue.json`, `rows_rd04_nue.json` | north-up-east-right | B1, B4L, B4X |

That is a **complete 2 × 2 paired factorial** (orientation × matcher) over the
same 42 pairs, with a third matcher on the amended arm.

**The honest cost of using it, stated before any number is read.** The
orientation step is **not a representative protocol component chosen for its
typicality — it is the one component for which both levels happen to have been
recorded**, and they were recorded because a defect was found, not because an
ablation was designed. Two consequences follow and are pre-registered here:

1. The contrast is *protocol step done correctly vs done incorrectly*, not
   *present vs absent*. That is arguably the sharper test — a single
   coordinate-convention step against a whole-matcher replacement — but it is a
   different claim and Part 2 must state it as such.
2. **A result here generalises to "at least one protocol step outweighs the
   matcher", never to "the protocol in general does".** The universal claim
   stays unsupported, and §553's judgement that it is unfalsifiable as phrased
   stands.

## 3. Data, fixed in advance

Recorded rows only. A row enters if it is not `excluded`, carries no
`reproduces_recorded` key (those are the raw reproduction arm), and belongs to
one of the four artefacts above — the identical filter
`run_exp012.recorded_successes` uses, copied rather than re-invented.

**Outcome variable:** `success` as recorded — the frozen `n_inliers > 8` rule
(D-023) **and** a transform CONSISTENT with archive corner geometry. Not
re-derived here.

**Pairing:** every contrast is computed over pairs present in **both** arms
being compared, matched on `(window, frozenset(pair))`. Pairs missing from
either arm are dropped from that contrast and counted in the report.

## 4. Success criteria — frozen

| ID | Criterion | MET if |
|---|---|---|
| **S0** | **Pairing control.** The arms really are the same pairs | every contrast has ≥ 40 paired pairs, and the pair sets are identical between arms. If not, that contrast reports `CANNOT CHECK` |
| **S1** | **The headline contrast.** The protocol step flips more outcomes than the matcher swap | the number of pairs whose outcome changes under the **orientation** step (at fixed matcher, averaged over B1 and B4L) exceeds the number that change under the **matcher** swap (at fixed orientation, averaged over both orientations) |
| **S2** | **Significance, by the discipline this project already uses.** | exact **McNemar** on the orientation contrast gives p ≤ 0.05 for at least one matcher, **and** the matcher contrast's p is larger than the orientation contrast's for the same arm. A protocol effect that is not significant is reported as not significant |
| **S3** | **Not one window.** | the sign of S1's comparison is the same computed on RD-03 and RD-04 separately |
| **S4** | **Direction.** The protocol step must *help*, not merely change things | every outcome the orientation step flips goes fail → success, or the exceptions are enumerated individually |
| **S5** | **The adversarial criterion, and the one most likely to fail.** A matcher swap must not recover what the protocol step loses | count the pairs where the **best** matcher under the **wrong** orientation succeeds while the **worst** matcher under the **right** orientation fails. If that count is not **below** the number of pairs the orientation step rescues outright, the thesis has no support here — a good enough matcher would have papered over the protocol defect |

**Predicted outcome, recorded now so it can be wrong.** S1 **MET** at
MEDIUM-HIGH confidence; S5 **MET** at LOW confidence. S5 is the criterion that
can genuinely refute the thesis and it is the one I would bet against myself
on: a learned matcher with 5–25× the inlier yield inside its envelope (D-047-N1)
is exactly the kind of component that could absorb an orientation defect.

**What may not happen in Part 2.** No threshold is re-derived, no row is
re-matched, and no further protocol component may be added to the contrast
after the numbers are seen. If additional components are ablated later they are
a new stage.

## 5. Secondary arms — reported, not part of any criterion

These are recorded elsewhere and are assembled here so the ablation reads as
one table. **None of them is paired or contrast-controlled**, so none may be
quoted as a protocol-vs-matcher comparison:

- **Verification step** (archive-geometry consistency): the wrong passes it
  converts from "pass" to "not a success", pooled over REAL-DATA-07 and
  REAL-DATA-08 as E-038's corrected tally gives them.
- **Refinement + model selection** (EXP-010, EXP-011): dense error **0.0975 px**
  under the affine default against **0.0018 px** under refine-then-reselect, on
  self-warps. A precision result, not an outcome result — a different response
  variable from S1's, and it may not be pooled with it.

## 6. What this stage explicitly does NOT claim

- **Not the universal thesis.** See §2: at most "one protocol step outweighs a
  matcher replacement on 42 mare pairs".
- **Not a claim about protocol components that were never ablated.** Scale
  normalisation, tiling, and the photometric arm are not in this design.
- **Not an accuracy claim.** The outcome variable is a binary success under a
  frozen rule, corroborated against archive geometry at its own ~100 px floor.
- **Not a Chandrayaan-2 result**, and not evidence about any non-mare terrain.

---

# Part 2 — what happened

**Run 2026-09-21, `scripts/run_exp006.py`, under a second, CPU only, no new
data and no re-match.** Artefact: `experiments/EXP-006/exp006_results.json`.
**42 paired pairs** (RD-03 23, RD-04 19) — the complete census, identical in
both arms.

## 0. The result in one paragraph

**All six criteria MET.** On the 42 real lunar pairs, correcting **one step of
the protocol** — the orientation convention — changes **2.2× as many pair
outcomes** as replacing the entire feature matcher, and it changes them in a
way a matcher swap does not: **every one of its 12 flips is an improvement**,
while matcher swaps produce 6 improvements and 5 regressions. The orientation
contrast reaches **p = 0.0156** (exact McNemar, B4L); **no matcher contrast
comes close to significance** (p ≥ 0.25). ADR-0001's architectural bet — *the
matcher is a replaceable part; the protocol is the contribution* — has, for the
first time, evidence on lunar imagery rather than a SAR-optical citation.

**And the claim this licenses is strictly bounded**, exactly as Part 1 §2
required: *at least one protocol step outweighs a matcher replacement on 42
mare pairs.* Not the universal thesis, which §553 rules unfalsifiable as
phrased and which nothing here rescues.

| | criterion | verdict |
|---|---|---|
| **S0** | ≥ 40 pairs in both arms, identical sets | **MET** — 42, 0 unmatched on either side |
| **S1** | the protocol step flips more outcomes than the matcher swap | **MET** — 6.0 vs 2.75 mean |
| **S2** | McNemar p ≤ 0.05 for the protocol on ≥ 1 matcher, and larger p for the matcher | **MET** — 0.0156 vs 0.25 |
| **S3** | the sign holds in RD-03 and RD-04 separately | **MET** — 2.5 vs 1.33 and 3.5 vs 1.33 |
| **S4** | flips go fail → success, or exceptions are enumerated | **MET** — **12 of 12**, zero regressions |
| **S5** | a better matcher must not paper over the protocol defect | **MET** — 1 papered over vs 7 rescued |

## 1. The factorial

Success under the frozen rule (`n_inliers > 8` **and** CONSISTENT with archive
corner geometry), over the same 42 pairs:

| | B1 RootSIFT | B4L DISK+LightGlue | B4X XFeat |
|---|---|---|---|
| **quarter-turn** (Part 1 orientation) | 20 / 42 · 0.476 | 17 / 42 · 0.405 | — |
| **north-up-east-right** (E-037) | **25 / 42 · 0.595** | **24 / 42 · 0.571** | **27 / 42 · 0.643** |

Read down a column — fixing the protocol step: **+5** (B1), **+7** (B4L).
Read across a row — swapping the matcher: **−3** (original), **−1** and **+2**
and **+3** (amended). The protocol step is worth more than any matcher
available, and it is worth more than the *spread* of all three matchers.

## 2. S1 and S2 — how much moves, and whether it is real

Paired, on the identical 42 pairs, with an **exact** McNemar (the discordant
counts are single digits, so a chi-square approximation would be wrong):

**PROTOCOL — the orientation step, same matcher:**

| matcher | changed | fail→success | success→fail | p (exact) |
|---|---|---|---|---|
| B1 RootSIFT | 5 | **5** | **0** | 0.0625 |
| B4L DISK+LightGlue | **7** | **7** | **0** | **0.0156** |

**MATCHER — engine swap, same orientation:**

| arm | swap | changed | fail→success | success→fail | p (exact) |
|---|---|---|---|---|---|
| quarter-turn | B1 ↔ B4L | 3 | 0 | 3 | 0.2500 |
| north-up-east-right | B1 ↔ B4L | 1 | 0 | 1 | 1.0000 |
| north-up-east-right | B1 ↔ B4X | 4 | 3 | 1 | 0.6250 |
| north-up-east-right | B4L ↔ B4X | 3 | 3 | 0 | 0.2500 |

**Mean outcomes changed: 6.0 by the protocol step, 2.75 by a matcher swap — a
factor of 2.18.** Totals across all contrasts: the protocol moves **12** pair
outcomes, **12 of them improvements**; matcher swaps move **11**, of which **6**
are improvements and **5** are regressions.

**Report the B1 p-value honestly: 0.0625 is not ≤ 0.05.** S2 as frozen asks for
significance on *at least one* matcher and gets it on B4L at 0.0156, with every
matcher contrast at p ≥ 0.25. But the B1 arm on its own does not clear the
line, and a five-flip McNemar cannot: with 5 discordant pairs all in one
direction the smallest attainable two-sided p is exactly 0.0625. **The B1
result is as significant as it is arithmetically possible for it to be**, and
that is a limit of the sample, not a weakness of the effect. Stated rather than
rounded down.

## 3. S4 — direction, which is the part a matcher swap cannot match

**Twelve flips, twelve improvements, zero regressions**, across both matchers
and both windows. The orientation step never broke a pair that was working.

Contrast with the matcher axis, where swapping engines moves pairs **both
ways** in three of four contrasts — B1 ↔ B4X gains 3 and loses 1. That is the
qualitative difference the ablation exposes and the raw counts alone would
hide: **a protocol fix is monotone; a matcher swap is a trade.** A team that
reaches for a better matcher is buying some pairs and selling others; a team
that fixes the coordinate convention is not.

## 4. S5 — the criterion that could have refuted the thesis

Part 1 predicted S5 **MET at LOW confidence** and said it was the one to bet
against: a learned matcher with 5–25× the inlier yield inside its envelope
(D-047-N1) is exactly the kind of component that could absorb an orientation
defect and make the protocol step look unnecessary.

**It does not.** Pairs where *some* matcher succeeds under the **wrong**
orientation but that are not unanimous successes under the **right** one:
**1**. Pairs the orientation step rescues outright: **7**. A better matcher
papers over the defect **one seventh** as often as fixing the protocol removes
it.

The prediction was wrong in the direction that strengthens the thesis, and it
is recorded as a wrong prediction rather than quietly dropped.

## 5. The mechanism, confirmed by a prediction that could have failed

**Post-hoc — not pre-registered, and labelled as such.** Having seen which
pairs flipped, the mechanism makes a sharp, falsifiable prediction, and it is
worth testing precisely because Part 1 did not think to.

E-037 identified **five of the fourteen** census frames as mirror images by
their own corner metadata (`frames_mirrored` in
`real_data_07_amendment_analysis.json`). A reflection is not undone by a
quarter-turn — but between **two** mirrored frames the reflection **cancels**,
because a mirror↔mirror match is handedness-consistent. So the orientation fix
should change outcomes on pairs with **exactly one** mirrored member, and on
**no others**.

The 42 pairs split: **26** with no mirrored frame, **12** with exactly one,
**4** with two.

- **All 12 flips have exactly one mirrored member.** 12 of 12.
- **No two-mirrored pair flipped**, as cancellation requires.
- **No zero-mirrored pair flipped.**

Under a null that flips fall where pairs are, P(all 12 land in a subset holding
12/42 of the pairs) = **2.96 × 10⁻⁷**.

This is the strongest form the result takes: the protocol step's gains land
**exactly** where its stated mechanism says they must, including on the
negative half of the prediction, which had four chances to fail and did not.

## 6. What this does and does not license

**Licensed:** on 42 geometry-confirmed mare pairs, a single coordinate-convention
step in the protocol changes 2.2× as many outcomes as replacing the matcher,
changes all of them for the better, reaches significance where no matcher swap
does, and does so through a mechanism that predicts which pairs it will move.

**Not licensed, and pre-registered as such before any number was seen:**

- **The universal thesis.** The orientation step is **the one protocol
  component whose both levels happen to have been recorded**, and they were
  recorded because a defect was found (E-037), not because an ablation was
  designed. §553's judgement that *"the protocol matters more than the
  matcher"* is unfalsifiable as phrased **stands**, and nothing here revives
  it.
- **A protocol-vs-matcher claim about components never ablated**: scale
  normalisation, tiling and the photometric arm are not in this design.
- **Any accuracy claim.** The outcome is a binary success corroborated against
  archive geometry at its own ~100 px floor. It says nothing about how
  accurate a succeeding registration is.
- **Anything outside mare terrain, one region, one instrument** — and nothing
  about Chandrayaan-2.

**The reframing was the right call, and it is worth saying why.** Asked as
*"is the protocol more important than the matcher?"* this has no truth value,
which is why it sat unregistered for the project's whole life. Asked as *"does
this one step move more outcomes than swapping this component, on these 42
pairs, with these criteria frozen first?"* it took under a second to answer
from artefacts that already existed. §553's instruction to reframe rather than
run was correct, and the six-week delay was the cost of not reframing sooner.

## 7. Secondary arms — reported, not part of any criterion

Neither is paired or contrast-controlled, so neither may be quoted as a
protocol-vs-matcher comparison (Part 1 §5):

- **Verification step** (archive-geometry consistency): on these 42 pairs it
  converts **0** passes into non-successes under any engine — the amended run
  has **0 wrong passes in 76**. Its value is recorded at the coarse rung
  instead, in REAL-DATA-08, as E-038's corrected tally gives it.
- **Refinement + model selection** (EXP-010, EXP-011): dense error **0.0975 px**
  under the affine default against **0.0018 px** under refine-then-reselect on
  self-warps. A **precision** result, a different response variable from this
  stage's binary outcome, and not poolable with it.

## 8. Ledger and index

- **D-056** — ADR-0001's architectural bet is supported in its bounded form on
  lunar data; the universal claim stays unsupported and §553 stands.
- **RL-051** — research-log entry.
- `experiments/EXP-006/exp006_results.json` — every figure above.
