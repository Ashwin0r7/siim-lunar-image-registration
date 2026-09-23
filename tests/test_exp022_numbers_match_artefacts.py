"""EXP-022 Part 2's numbers are derived from the artefacts, not transcribed.

E-038 found an advertised count that did not open its artefact. Every figure
EXP-022's Part 2, the ledgers and the scorecards quote is recomputed here from
``exp022_results_A1.json`` (run v2, the verdict) and ``exp022_results.json``
(run v1, reported beside it). The proper S5 reading (E-060) is recomputed
from ``edges`` rather than taken from the runner's summary.
"""

import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "experiments" / "EXP-022" / "exp022_results_A1.json"
V1 = ROOT / "experiments" / "EXP-022" / "exp022_results.json"
PART2 = ROOT / "docs" / "stages" / "EXP-022_coverage_at_real_counts.md"

pytestmark = pytest.mark.skipif(not (V1.exists() and V2.exists()), reason="EXP-022 artefacts absent")

NINE = "nac.m1271742202lc -> nac.m1335207975rc"
TWENTY_EIGHT = "nac.m1299958135lc -> nac.m1363396554rc"
SIXTY_EIGHT = "nac.m1182331886lc -> nac.m1335207975rc"


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def _outcomes(d):
    c = d["criteria"]
    return {k: c[k]["met"] for k in ("S0", "S1", "S2", "S3", "S4", "S5", "S6")}


def test_v1_and_v2_agree_on_every_outcome_so_a1s_tiebreak_never_ran():
    assert _outcomes(_load(V1)) == _outcomes(_load(V2)) == {
        "S0": True, "S1": False, "S2": True, "S3": False, "S4": True, "S5": False, "S6": True}
    assert _load(V2)["adoption"]["criterion_4pp_adopted"] is False
    assert _load(V2)["image_preparation"] == "A1"


def test_s0_reproduces_exp015_and_every_tile_is_used_in_v2():
    s0 = _load(V2)["criteria"]["S0"]
    assert s0["i_reproduces_exp015"]["recomputed"] == s0["i_reproduces_exp015"]["recorded"] == 0.078125
    tiles = s0["ii_tiles"]
    assert len(tiles) == 10 and all(t["status"] == "OK" for t in tiles)
    pools = [t["n_pool"] for t in tiles]
    assert (min(pools), max(pools)) == (3600, 9182)
    errs = [t["full_fit_median_err_px"] for t in tiles]
    assert 0.024 <= min(errs) and max(errs) < 0.03
    assert round(s0["iv_sigma_n_px"], 4) == 0.7202
    v1_ok = [t for t in _load(V1)["criteria"]["S0"]["ii_tiles"] if t["status"] == "OK"]
    assert len(v1_ok) == 5                                          # E-059


def test_the_regime_was_reached_but_seven_edges_were_not():
    s1 = _load(V2)["criteria"]["S1"]
    assert (s1["rows_occupancy_ge_0_99"], s1["rows_n_points_ge_1000"]) == (97, 1026)
    assert len(s1["edges_without_a_cell"]) == 11
    assert len({(w, e) for w, e, *_ in s1["edges_without_a_cell"]}) == 7
    assert sum(1 for *_, n in s1["edges_without_a_cell"] if n == 0) == 2
    v1 = _load(V1)["criteria"]["S1"]
    assert (v1["rows_occupancy_ge_0_99"], v1["rows_n_points_ge_1000"], len(v1["edges_without_a_cell"])) == (0, 0, 27)


def test_the_floor_and_the_two_edges_below_it():
    c = _load(V2)["criteria"]
    assert c["S2"]["T2"] == 0.359375 and c["S2"]["bootstrap_ci95"] == [0.296875, 0.453125]
    assert _load(V1)["criteria"]["S2"]["T2"] == 0.328125
    assert c["S3"]["floor_plus_margin"] == 0.375 and (c["S3"]["n_pass"], c["S3"]["n"]) == (37, 39)
    assert sorted((e[1], e[2]) for e in c["S3"]["failing_edges"]) == [(NINE, 9), (TWENTY_EIGHT, 28)]
    assert round(c["S4"]["reject_fraction"], 3) == 0.436


def test_arm_zero_floor_is_nineteen_lattice_steps_below():
    d = _load(V2)
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("_e15", ROOT / "scripts" / "run_exp015.py")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    r0 = [r for r in d["rows"] if r["arm"] == "0"]
    t0, _bins = mod.crossing_from_above(np.array([r["grid_occupancy"] for r in r0]),
                                        np.array([r["p99_err_px"] for r in r0]), 1.0, 95)
    assert t0 == d["criteria"]["S2"]["arm0_T"] == 0.0625
    assert d["criteria"]["S2"]["rows_arm_N"] == 3376
    assert round((d["criteria"]["S2"]["T2"] - t0) * 64) == 19


def test_s5_read_properly_needs_five_rows_per_cell():
    d = _load(V2)
    assert d["criteria"]["S5"]["n_within"] == 34                  # the runner's line, E-060
    edges = d["edges"]
    ev = [e for e in edges if e["n_matched"] >= 5]
    within = [e for e in ev if e["p95_of_p99_err_px"] < 1.0]
    over = {e["edge"]: (e["n_inliers"], round(e["p95_of_p99_err_px"], 2), e["n_matched"])
            for e in ev if e["p95_of_p99_err_px"] >= 1.0}
    assert (len(ev), len(within)) == (28, 25)
    assert round(max(e["p95_of_p99_err_px"] for e in within), 2) == 0.81
    assert over == {NINE: (9, 3.93, 15), TWENTY_EIGHT: (28, 1.66, 45), SIXTY_EIGHT: (68, 1.04, 36)}
    sixty_eight = next(e for e in edges if e["edge"] == SIXTY_EIGHT)
    assert sixty_eight["occupancy"] >= d["criteria"]["S3"]["floor_plus_margin"], "above the floor, over the bound"
    ones = [e for e in edges if e["occupancy"] == 1.0]
    assert len(ones) == 14 and all(0.09 <= e["p95_of_p99_err_px"] <= 0.151 for e in ones)


def test_triplet_split_three_clear_three_over_seven_undecided():
    edges = _load(V2)["edges"]
    trip = {}
    for e in edges:
        trip.setdefault((e["window"], tuple(e["triplet"])), []).append(e)
    assert len(trip) == 13
    clear = over = 0
    for es in trip.values():
        if any(e["n_matched"] >= 5 and e["p95_of_p99_err_px"] >= 1.0 for e in es):
            over += 1
        elif all(e["n_matched"] >= 5 for e in es):
            clear += 1
    assert (clear, over, 13 - clear - over) == (3, 3, 7)


def test_s6_holds_at_every_small_size():
    s6 = _load(V2)["criteria"]["S6"]
    assert s6["fraction"] == 1.0 and len(s6["per_size"]) == 13


def test_part2_quotes_the_numbers_this_file_checks():
    text = PART2.read_text(encoding="utf-8")
    part2 = text[text.index("## Part 2"):]
    for s in ("0.359", "0.297–0.453", "0.0625", "3.93 px", "1.66 px", "1.04 px", "0.81", "25 within",
              "28 of 39", "3 376", "**97**", "**1 026**", "3 of 13"):
        assert s in part2, s
