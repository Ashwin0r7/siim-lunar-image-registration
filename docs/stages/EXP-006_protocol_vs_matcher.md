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
