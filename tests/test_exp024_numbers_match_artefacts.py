"""EXP-024 Part 2's numbers are derived from the artefact, not transcribed.

E-038's rule: every figure the Part 2, the ledgers and the scorecards quote
must open its artefact. These tests recompute the quoted numbers from
``exp024_results.json`` and verify the recorded positions file is the one
the results reference (its SHA-256), so the stage's central deliverable —
the inlier positions REAL-DATA-07 never recorded — cannot silently drift
from the numbers derived from it.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "experiments" / "EXP-024" / "exp024_results.json"
NPZ = ROOT / "experiments" / "EXP-024" / "exp024_inlier_positions.npz"

pytestmark = pytest.mark.skipif(not RES.exists(), reason="EXP-024 artefact absent")

NINE = "nac.m1271742202lc -> nac.m1335207975rc"        # RD04, 9 inliers
TWENTY_EIGHT = "nac.m1299958135lc -> nac.m1363396554rc"  # RD04, 28 inliers
SIXTY_EIGHT = "nac.m1182331886lc -> nac.m1335207975rc"   # RD03, 68 inliers


def _doc():
    return json.loads(RES.read_text(encoding="utf-8"))


def test_criteria_outcomes_are_as_part2_states():
    c = _doc()["criteria"]
    assert {k: c[k]["met"] for k in ("S0", "S1", "S2", "S3", "S4")} == {
        "S0": True, "S1": False, "S2": True, "S3": True, "S4": True}


def test_s1_fails_on_exactly_the_two_named_edges_with_the_quoted_numbers():
    d = _doc()
    over = {(e["edge"], e["n_inliers"]) for e in d["criteria"]["S1"]["edges_over_bound"]}
    assert over == {(NINE, 9), (TWENTY_EIGHT, 28)}
    by = {(e["window"], e["edge"]): e for e in d["edges"]}
    assert by[("RD04", NINE)]["p95_of_p99_own_px"] == pytest.approx(5.4245, abs=1e-4)
    assert by[("RD04", TWENTY_EIGHT)]["p95_of_p99_own_px"] == pytest.approx(1.5899, abs=1e-4)
    # every other distinct edge is within the bound, and 20 of 22 in total
    within = [e for e in d["edges"] if e["p95_of_p99_own_px"] < 1.0]
    assert len(d["edges"]) == 22 and len(within) == 20


def test_the_68_inlier_edge_passes_where_its_proxy_failed():
    d = _doc()
    row = next(r for r in d["criteria"]["S3"]["rows"] if r["n_inliers"] == 68)
    assert row["direct_p95_px"] == pytest.approx(0.8301, abs=1e-4)
    assert row["proxy_p95_px"] > 1.0            # EXP-022's cell said over
    assert row["proxy_call_stands"] is False    # and the direct number says within
    # the 9- and 28-inlier proxy calls stand
    assert all(r["proxy_call_stands"] for r in d["criteria"]["S3"]["rows"]
               if r["n_inliers"] in (9, 28))


def test_harness_identity_held_everywhere():
    d = _doc()
    assert all(e["reproduces_recorded"] for e in d["edges"])
    checks = d["criteria"]["S0"]["occupancy_checks"]
    assert len(checks) == 39 and all(c["equal"] for c in checks)
    assert d["constants"]["sigma_n_px"] == pytest.approx(0.7202, abs=1e-4)


def test_null_and_triplet_counts_match_the_quoted_ones():
    d = _doc()
    assert d["criteria"]["S4"]["n_null_exceeds_own"] == 22
    assert d["n_triplets_clear"] == 11 and len(d["triplets"]) == 13
    carrying = [t for t in d["triplets"] if not t["clear_on_all_edges"]]
    assert len(carrying) == 2
    for t in carrying:  # each carries exactly one failing edge, over 1 px
        vals = [v for v in t["p95_of_p99_px"] if v is not None]
        assert len(vals) == 3 and sum(v >= 1.0 for v in vals) == 1


def test_the_positions_file_is_the_one_the_results_reference():
    d = _doc()
    ref = d["inlier_positions_file"]
    assert NPZ.exists() and NPZ.name == ref["path"]
    assert hashlib.sha256(NPZ.read_bytes()).hexdigest() == ref["sha256"]
    with np.load(NPZ) as z:
        keys = list(z.keys())
        assert len(keys) == 22                    # (window, edge) identity: no collision
        by = {(e["window"], e["edge"]): e for e in d["edges"]}
        for k in keys:
            window, edge = k.split(":", 1)
            pts = z[k]
            assert pts.shape == (by[(window, edge)]["n_inliers"], 2)
