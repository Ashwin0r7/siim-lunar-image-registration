"""EXP-018's grading arithmetic, pinned to Part 1 section 5.1 before any held-out row exists.

Part 1 states, from the frozen rates and nothing else, why S5's minima are what
they are:

    at n = 5 and p = 0.786 the two-sided test rejects only at k <= 1;
    at n = 5 and p = 0.222 it rejects at k >= 4;
    three pairs above 40 deg make S1c fail-able on a single success;
    at n_pass = 12 and p_upper = 0.0631, S2b can only fail at k >= 3.

These tests hold the runner to those sentences, and hold the runner to
integrity rule 4.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def e18():
    spec = importlib.util.spec_from_file_location("_e18_test", ROOT / "scripts" / "run_exp018.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_e18_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_low_range_rejects_only_at_k_le_1(e18):
    rej = [e18.binom_two_sided(k, 5, 0.786)["rejects"] for k in range(6)]
    assert rej == [True, True, False, False, False, False]


def test_high_range_rejects_at_k_ge_4(e18):
    rej = [e18.binom_two_sided(k, 5, 0.222)["rejects"] for k in range(6)]
    assert rej == [False, False, False, False, True, True]


def test_s2b_can_only_fail_at_k_ge_3_when_n_pass_is_12(e18):
    t2 = e18.binom_one_sided_upper(2, 12, 0.0631)
    t3 = e18.binom_one_sided_upper(3, 12, 0.0631)
    assert abs(t2["P_X_ge_k"] - 0.17) < 0.01 and not t2["rejects"]
    assert abs(t3["P_X_ge_k"] - 0.036) < 0.003 and t3["rejects"]


def test_rule_of_three_bound_above_40_is_vacuous_as_part_1_says(e18):
    # P(X >= 3 | 3, 0.527) = 0.146: a bound test would pass 3/3 successes.
    t = e18.binom_one_sided_upper(3, 3, 0.527)
    assert abs(t["P_X_ge_k"] - 0.146) < 0.002 and not t["rejects"]


def _row(engine, d, success, edge=None, wrong=False):
    return {"engine": engine, "edge": edge or f"a{d} -> b", "delta_incidence_deg": d,
            "success": success, "pass": success or wrong, "wrong_pass": wrong,
            "n_inliers": 100 if success else 3,
            "src_incidence_deg": 20.0, "dst_incidence_deg": 20.0 + d}


def test_s1c_single_success_above_40_fails_and_needs_three_pairs(e18):
    rows = [_row("b1", 45, False), _row("b1", 50, False), _row("b1", 60, True),
            _row("lg", 45, False), _row("lg", 50, False), _row("lg", 60, False)]
    s1 = e18.evaluate_s1(rows)
    assert s1["S1c_zero_above_40"]["per_engine"]["B1"]["status"] == "NOT MET"
    assert s1["S1c_zero_above_40"]["per_engine"]["B4L"]["status"] == "MET"
    assert s1["S1c_zero_above_40"]["status"] == "NOT MET"
    two = [r for r in rows if r["delta_incidence_deg"] != 60]
    assert e18.evaluate_s1(two)["S1c_zero_above_40"]["status"] == "CANNOT CHECK"


def test_s1_a_range_with_no_pair_is_flagged_vacuous_not_met_silently(e18):
    rows = [_row("b1", 5, True), _row("b1", 8, True), _row("lg", 5, True), _row("xf", 5, True)]
    s1 = e18.evaluate_s1(rows)
    assert "15to30" in s1["S1a_B1"]["vacuous_ranges"] and "ge30" in s1["S1a_B1"]["vacuous_ranges"]
    assert s1["S1a_B1"]["note"] and "not reassurance" in s1["S1a_B1"]["note"]


def test_s2_cannot_check_below_five_b1_passes(e18):
    rows = [_row("b1", 5, True)] * 4 + [_row("lg", 5, True)] * 6 + [_row("xf", 5, True)]
    assert e18.evaluate_s2(rows)["status"] == "CANNOT CHECK"


def test_s5_minima_are_the_part_1_numbers(e18):
    pairs = [{"delta_incidence_deg": d} for d in (5, 6, 7, 8, 9, 31, 32, 33, 41, 42, 43, 20)]
    s5 = e18.s5_counts(pairs, 7, [20.0, 65.0], 1)
    assert s5["met"] and s5["n_lt15"] == 5 and s5["n_ge30"] == 6 and s5["n_ge40"] == 3
    s5b = e18.s5_counts(pairs[1:], 7, [20.0, 65.0], 1)
    assert not s5b["met"] and not s5b["checks"]["n_lt15"]


def test_runner_refuses_to_overwrite_an_existing_artefact(e18, monkeypatch):
    # OUT must sit under ROOT (the refusal message prints a repo-relative path).
    scratch = ROOT / "experiments" / "EXP-018" / "_pytest_scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        monkeypatch.setattr(e18, "OUT", scratch)
        (scratch / "exp018_s0_gate.json").write_text("{}", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["run_exp018.py", "--gate"])
        with pytest.raises(SystemExit, match="integrity rule 4"):
            e18.main()
    finally:
        for p in scratch.glob("*"):
            p.unlink()
        scratch.rmdir()


def test_runner_and_census_compile():
    for name in ("run_exp018.py", "census_exp018.py"):
        r = subprocess.run([sys.executable, "-m", "py_compile", str(ROOT / "scripts" / name)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
