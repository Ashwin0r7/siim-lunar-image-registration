"""E-042: a `PROPOSED` decision may not outlive the stage assigned to test it.

D-006 named EXP-007 as its acceptance test. EXP-007 ran, completed, and never
performed it — because EXP-007's own frozen criteria never mentioned coverage,
so it could pass everything it had while leaving D-006's test unrun. Nothing
anywhere noticed for six weeks, while the metric stayed load-bearing in the
verdict and in §53's criterion 4.

The failure is structural, not clerical: this project freezes criteria before
data and honours them scrupulously *within* a stage, and had no mechanism at
all for a criterion that spans stages. This test is that mechanism. It makes
`PROPOSED` a state that can come due.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "stages" / "DECISION_LEDGER.md"
INDEX = ROOT / "docs" / "stages" / "STAGE-INDEX.md"

STAGE_RE = re.compile(r"\b(EXP-\d{3}|REAL-DATA-\d{2}|PHASE-\d)\b")


def _rows() -> list[list[str]]:
    out = []
    for line in LEDGER.read_text(encoding="utf-8").split("\n"):
        if not line.startswith("| **D-"):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) >= 10:
            out.append(cells)
    return out


def _completed_stages() -> set[str]:
    """Stage IDs the index marks COMPLETE (or CLOSED — a stage that stopped)."""
    done = set()
    for line in INDEX.read_text(encoding="utf-8").split("\n"):
        if not line.startswith("| **"):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 6:
            continue
        ids = STAGE_RE.findall(cells[1])
        status = cells[4].upper()
        if ids and ("COMPLETE" in status or "CLOSED" in status):
            done.update(ids)
    return done


ROWS = _rows()
DONE = _completed_stages()


def test_the_ledger_and_index_are_parseable():
    assert ROWS, "no decision rows parsed from DECISION_LEDGER.md"
    assert DONE, "no completed stages parsed from STAGE-INDEX.md"


def _is_open_proposed(status_cell: str) -> bool:
    """`PROPOSED` and not already resolved by a superseding note in the cell."""
    s = status_cell.upper()
    if "PROPOSED" not in s:
        return False
    return not any(w in s for w in ("REVERSED", "ACCEPTED", "SUPERSEDED", "WITHDRAWN"))


@pytest.mark.parametrize(
    "row", [r for r in ROWS if _is_open_proposed(r[8])],
    ids=[r[1].replace("*", "").strip() for r in ROWS if _is_open_proposed(r[8])])
def test_an_open_proposed_decision_does_not_name_a_finished_stage(row):
    """The stage a `PROPOSED` decision defers to must not already be done.

    If it is, either the stage ran the test and the decision should have moved
    out of `PROPOSED`, or — the E-042 case — it did not, and the decision is
    quietly permanent. Both need a human; neither should be silent.
    """
    decision_id = row[1].replace("*", "").strip()
    reverse_clause = row[9]
    named = set(STAGE_RE.findall(reverse_clause))
    if not named:
        pytest.skip("acceptance rule names no stage; nothing to come due")

    # The clause routinely cites stages as *context* alongside the one it
    # defers to -- D-005 defers to EXP-004 and mentions EXP-002's E-015 as
    # already-known supporting evidence. Flagging every completed mention
    # would fail D-005 forever, and a guard that cries wolf gets ignored,
    # which is how E-042 would come back. So the condition is that NO named
    # stage is still open: if even one has yet to run, the decision is
    # legitimately waiting for it.
    pending = sorted(named - DONE)
    assert pending, (
        f"{decision_id} is still PROPOSED, but every stage its acceptance rule "
        f"names ({sorted(named)}) is already COMPLETE in STAGE-INDEX. Either "
        f"one of them ran the test and this row should record the outcome, or "
        f"none did and the decision has gone permanent by default — E-042 "
        f"exactly. Resolve the row, or point it at a stage that has not run yet.")


def test_d006_records_its_reversal():
    """The specific row E-042 was found on stays resolved.

    A regression here would mean the reversal was edited away, which is the one
    way this lesson could be lost.
    """
    d006 = [r for r in ROWS if r[1].startswith("**D-006**")]
    assert d006, "D-006 is missing from the decision ledger"
    status = d006[0][8].upper()
    assert "REVERSED" in status, (
        "D-006's status no longer records the reversal EXP-014 forced (D-055)")
    assert "D-055" in d006[0][8], "D-006 should name the decision that superseded it"
