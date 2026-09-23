"""EXP-021 Part 2's headline numbers are derived from the artefacts, not transcribed.

E-038 found an advertised count that did not open its artefact. Every figure
EXP-021's Part 2, the audit and the README quote is recomputed here from
``exp021_results.json`` and ``exp021_s5_tier_ab_reading.json``.
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "experiments" / "EXP-021" / "exp021_results.json"
TIER_AB = ROOT / "experiments" / "EXP-021" / "exp021_s5_tier_ab_reading.json"
PART2 = ROOT / "docs" / "stages" / "EXP-021_verdict_fa_fr.md"

pytestmark = pytest.mark.skipif(not MAIN.exists(), reason="EXP-021 artefact absent")


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_every_s0_gate_holds_and_reproduces_exactly():
    s0 = _load(MAIN)["criteria"]["S0"]
    assert s0["met"] is True
    assert s0["i_leg_rebuild"]["max_abs_diff_px"] == 0.0
    assert s0["iii_loop_rebuild"]["max_abs_diff_px"] == 0.0
    assert s0["iii_loop_rebuild"]["n"] == 20
    assert s0["vi_v_null"]["n_pass"] == 0


def test_the_primary_population_holds_no_negatives():
    d = _load(MAIN)
    labelled = [c for c in d["rows_classified"]
                if c["cls"] in ("CORRECT", "AMBIGUOUS", "WRONG", "NO_ESTIMATE")]
    assert len(labelled) == 39
    assert all(c["cls"] == "CORRECT" for c in labelled)          # E-058


def test_primary_rates_as_part2_quotes_them():
    c = _load(MAIN)["criteria"]
    pooled = c["primary_rates_b1_L2"]["pooled"]
    assert (pooled["FDR"]["k"], pooled["FDR"]["n"]) == (0, 12)
    assert (pooled["FRR"]["k"], pooled["FRR"]["n"]) == (0, 12)
    assert pooled["FAR"]["n"] == 0
    assert round(pooled["FDR"]["ci95"][1], 3) == 0.265
    assert c["S1"]["v_frames_tier_A"] == 2
    assert c["S2"]["met"] is False and "NOT EVALUABLE" in c["S2"]["reads"]
    assert c["S2"]["withdraw_verified_under_SS54"] is False
    assert c["S6"]["n_hard_negatives_V"] == 0


def test_tier_a_or_b_reading_as_part2_quotes_it():
    s = _load(TIER_AB)["summary"]["V+C|pooled"]
    assert s["verified"] == 84 and s["verified_wrong"] == 0
    assert s["verified_ambiguous"] == 15
    assert s["wrong_total"] == 20 and s["hard_negatives"] == 1
    assert s["max_inliers_on_a_wrong_edge"] == 13
    b1 = _load(TIER_AB)["summary"]["V+C|B1"]
    assert (b1["verified"], b1["verified_ambiguous"]) == (29, 7)


def test_verified_accuracy_figures():
    v = _load(MAIN)["reported_beside"]["verified_edge_errors"]
    e_m = sorted(x["e_m"] for x in v)
    assert len(v) == 36
    assert round(e_m[-1], 2) == 3.48
    med = (e_m[17] + e_m[18]) / 2
    assert round(med, 2) == 1.51


def test_part2_quotes_the_numbers_this_file_checks():
    text = PART2.read_text(encoding="utf-8")
    for frag in ("FDR 0 / 12", "FRR 0 / 12", "26.5 %", "0 of 84", "15 of 84", "1.51 m", "3.48 m"):
        assert frag in text, frag
