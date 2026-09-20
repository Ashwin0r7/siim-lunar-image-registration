"""The advertised false-acceptance bound must be derivable from the artefacts.

E-038. ``siim.demo.verdict.MEASURED_WRONG_PASS`` is the number the deliverable
quotes as its false-acceptance bound and the demo prints to a judge. It was
transcribed by hand from the stage runs, and the transcription was wrong in two
independent ways: the B4L denominator said 47 where the rows give 49, and the
PSF-aware re-run's two Mini-RF wrong passes were counted in neither the stage
report nor the constant.

The fix is not a corrected number -- it is this file. Every figure in the
constant is recomputed here from the recorded row files, so prose and artefact
cannot drift apart again. If a future run adds rows, this test fails until the
constant is updated to match them, which is the intended behaviour.

The counting rule, matching the runners that wrote the rows
(``scripts/run_real_data_07.py:108``, ``scripts/run_real_data_08.py:127``):

    pass       = n_inliers > 8                (D-023, the frozen failure rule)
    wrong_pass = pass and geometry INCONSISTENT

Rows carrying ``excluded`` never ran. The ``b1`` raw-reproduction arm
(``reproduces_recorded``) re-runs already-recorded edges as a gate and is not
part of the census, so it is excluded here exactly as the constant excludes it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from siim.demo.verdict import MEASURED_WRONG_PASS

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments"

#: Row files behind each engine's tally, as the constant's `source` strings name
#: them. The PSF-aware re-run is deliberately absent: it is a separate recorded
#: operator, reported beside the box run rather than pooled into it.
BOX_TALLY_FILES = [
    EXP / "REAL-DATA-07" / "rows_rd03.json",
    EXP / "REAL-DATA-07" / "rows_rd04.json",
    EXP / "REAL-DATA-07" / "rows_rd03_nue.json",
    EXP / "REAL-DATA-07" / "rows_rd04_nue.json",
    EXP / "REAL-DATA-08" / "real_data_08_results.json",
]

PSF_FILE = EXP / "REAL-DATA-08" / "real_data_08_psf_fwhm1.json"

#: Runner engine aliases -> the constant's engine keys.
ALIAS = {"b1": "B1", "lg": "B4L", "xf": "B4X"}


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        pytest.skip(f"{path.relative_to(ROOT)} is not on disk")
    doc = json.loads(path.read_text(encoding="utf-8"))
    return doc["rows"] if isinstance(doc, dict) and "rows" in doc else doc


def _counts(paths) -> dict[str, dict[str, int]]:
    """Recompute {engine: {n_pass, n_wrong_pass}} from recorded rows."""
    out: dict[str, dict[str, int]] = {}
    for path in paths:
        for row in _rows(path):
            if row.get("excluded"):
                continue
            if "reproduces_recorded" in row:      # the raw-reproduction gate
                continue
            engine = ALIAS.get(row.get("engine"))
            if engine is None:                    # b7 and friends: not advertised
                continue
            if not row.get("pass"):
                continue
            tally = out.setdefault(engine, {"n_pass": 0, "n_wrong_pass": 0})
            tally["n_pass"] += 1
            if row.get("wrong_pass"):
                tally["n_wrong_pass"] += 1
    return out


def test_the_failure_rule_recorded_in_every_row_is_the_frozen_one():
    """`pass` must be exactly `n_inliers > 8` wherever a row records both."""
    checked = 0
    for path in [*BOX_TALLY_FILES, PSF_FILE]:
        for row in _rows(path):
            if row.get("excluded") or "n_inliers" not in row or "pass" not in row:
                continue
            assert bool(row["pass"]) is bool(row["n_inliers"] > 8), (
                f"{path.name}: n_inliers={row['n_inliers']} but pass={row['pass']}; "
                f"the frozen rule is D-023 'n_inliers <= 8 fails'")
            checked += 1
    assert checked > 400, f"only {checked} rows carried both fields; expected the full census"


@pytest.mark.parametrize("engine", sorted(MEASURED_WRONG_PASS))
def test_the_advertised_tally_is_what_the_artefacts_say(engine):
    """E-038: the constant is derived from the rows, never typed beside them."""
    measured = _counts(BOX_TALLY_FILES)
    assert engine in measured, f"{engine} is advertised but no recorded row carries it"

    advertised = MEASURED_WRONG_PASS[engine]
    assert measured[engine]["n_pass"] == advertised["n_pass"], (
        f"{engine}: artefacts give {measured[engine]['n_pass']} passes, "
        f"MEASURED_WRONG_PASS says {advertised['n_pass']}. The constant must be "
        f"recomputed from the rows (E-038), not edited to taste.")
    assert measured[engine]["n_wrong_pass"] == advertised["n_wrong_pass"], (
        f"{engine}: artefacts give {measured[engine]['n_wrong_pass']} wrong passes, "
        f"MEASURED_WRONG_PASS says {advertised['n_wrong_pass']}.")


def test_the_psf_rerun_is_not_silently_pooled_into_the_box_tally():
    """The two operators are separate recorded runs and stay separate."""
    psf = _counts([PSF_FILE])
    assert psf["B4L"]["n_pass"] == 13
    assert psf["B4L"]["n_wrong_pass"] == 5, (
        "the PSF re-run records five B4L wrong passes -- three at the WAC rung "
        "and two on Mini-RF; E-038 was that the Mini-RF pair was counted nowhere")
    # and the box tally must not have absorbed them
    assert MEASURED_WRONG_PASS["B4L"]["n_wrong_pass"] == 1


def test_the_two_radar_wrong_passes_are_still_in_the_artefact():
    """E-038's specific finding, pinned so it cannot be quietly dropped.

    A wrong pass is not a success: REAL-DATA-08's "radar registers under no
    engine (0 / 48 successes)" is unaffected. But two Mini-RF rows did pass the
    inlier rule with an INCONSISTENT transform, and the stage must keep saying so.
    """
    radar_wrong = [r for r in _rows(PSF_FILE)
                   if r.get("wrong_pass") and r.get("proxy") == "minirf"]
    assert len(radar_wrong) == 2, "expected exactly the two Mini-RF wrong passes of E-038"
    assert {r["frame"] for r in radar_wrong} == {"B", "D"}
    for row in radar_wrong:
        assert row["n_inliers"] == 9
        assert not row.get("success"), "a wrong pass must never also count as a success"
