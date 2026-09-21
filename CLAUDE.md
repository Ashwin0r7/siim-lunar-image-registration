# SIIM — working rules for anyone (human or agent) touching this repo

SIH 2026, ISRO PS 26166: register Chandrayaan-2 optical images to LRO NAC under
illumination, viewpoint and scale variation. The repo's credibility rests on
the discipline below. A judge is invited to open every artefact.

## Stage discipline (non-negotiable)

- Every experiment is a **stage** with a report in `docs/stages/<ID>_<slug>.md`.
  **Part 1 (pre-registration) is written and COMMITTED before any runner code
  exists** and before any statistic is computed. Part 2 is appended afterwards
  and answers every criterion *exactly as frozen*, including NOT MET, "null by
  construction" and "MET for the wrong reason". Nothing is re-scoped after data.
- A Part 1 must state, for every criterion resting on a fit or a statistic:
  the **parameter count against the constraint count** (E-041), and the null
  must be built from the **property** being tested — never from a permutation
  that preserves it or a source assumed to carry it (E-039).
- Record the **predicted outcome with a confidence** in Part 1 so it can be
  wrong. When it is wrong, say so in Part 2; never drop a wrong prediction.
- A criterion that passes vacuously or for the wrong reason is reported as
  "MET, and here is why that is not reassurance" — beside the criterion, never
  folded into it.
- Runners refuse to overwrite an existing artefact (integrity rule 4). Recorded
  artefacts are never rewritten; if the runner's own summary line is
  insufficient, Part 2 says so and reads it properly.
- Superseded prose stays in place under an explicit
  `*(Historical note, retained under integrity rule 3: …)*` marker.
- Every stage lands with, in the same commit: its `STAGE-INDEX.md` row, a
  `STAGE_HISTORY.md` standing-table row, a `research_log.md` `RL-nnn` entry,
  and the `DECISION_LEDGER` (`D-nnn`) / `ERROR_LEDGER` (`E-nnn`) rows it
  creates. Superseding notes (`D-nnn-Nk`) rather than edits to old rows.
- **Two scorecards, always:** `MASTER_RESEARCH_AND_ARCHITECTURE_PLAN.md` §53
  (the project's own bar) and §2.2 (the problem statement's nine
  requirements). Score both in `docs/FINAL_SUCCESS_CRITERIA_AUDIT.md` and
  `docs/PROJECT_GAP_ANALYSIS.md`. Tracking only §53 is how two PS axes went
  untested for a month.

## Claim discipline

- Never quote a pass without the control that makes it meaningful beside it.
- "Corroborated" (archive geometry, ~100 px floor) is not "verified". Self-warp
  error is an upper bound on **precision**, never accuracy. No sub-pixel
  accuracy claim exists without independent check points.
- Every demo/README claim must be read from a recorded artefact the page
  links; `not_claimed` lists are required and tests scan them for negations.
- The universal "protocol beats matcher" thesis is **not** supported (§553);
  only the bounded EXP-006 form is.

## Artefact-reading traps (each cost real time)

- REAL-DATA-07: use **`rows_rd03_nue.json` / `rows_rd04_nue.json`** only; the
  un-suffixed files are the superseded quarter-turn run. Original-run rows have
  **no `pair` key** — derive the unordered pair from `edge`.
- Direction comes from **`edge`** (what the engine was fed), never `pair`
  (sorted). Matching is not symmetric (E-036).
- `geometry.predicted_transform_matrix` is in the ORIGINAL-pixel frame and
  pairs with **`transform_matrix_original_pixels`**, not `transform_matrix`
  (E-040). Wrong pairing is right on 8 of 12 rows and 20–30× off on the rest.
- Coverage: `grid_occupancy` is primary (D-055); `max_uncovered_disc_ratio` is
  secondary and its 0.15 threshold is uncalibrated (D-053/D-057).

## Environment gotchas

- `pytest -q` prints no count (pyproject `addopts=-q`): use `-o addopts=""`.
- **`jq` is not installed**; use Python for JSON. **Node is available** at
  `/c/Program Files/nodejs/node`.
- Bash heredocs mangle `\n` inside Python that writes source; use Write/Edit.
- Real tiles live in `data/processed/mare_serenitatis/` (32 present);
  Chandrayaan-2 in `realdata/realdata/` (gitignored, manifested).

## Demo rules

- New evidence module ⇒ update **both** `test_the_allow_list_is_exactly_what_the_page_advertises`
  and the boot `Promise.all` in `static/index.html`. Number helper is `sci()`,
  not `fmt()`. Before commit, extract the `<script>` block, `node --check` it,
  and `eval` the panel function against the live payload.
- Negatives stay on the page; a panel that hides its NOT MET is a regression.

## Commits

One stage per commit, message explains the *finding* not the diff. End with:
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`
