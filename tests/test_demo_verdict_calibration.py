"""The verdict-calibration panel reports EXP-012's negatives, not just its win.

13 of 13 VERIFIED is the kind of number that invites overstatement, and the run
that produced it also refuted its own S2 and broke a project success criterion.
A panel that shows the first and quietly drops the other two would be exactly
the failure this repository exists to prevent, so both are pinned here.
"""

from __future__ import annotations

import json

import pytest

from siim.demo import api
from siim.demo import exp012 as e12

pytestmark = pytest.mark.skipif(
    not e12.exp012_status()["available"],
    reason="EXP-012 artefact is not on disk")


@pytest.fixture(scope="module")
def ev() -> dict:
    return e12.exp012_evidence()


@pytest.fixture(scope="module")
def page() -> str:
    return (api.STATIC / "index.html").read_text(encoding="utf-8")


def test_every_figure_comes_from_the_recorded_artefact(ev):
    doc = json.loads(e12.EXP012_ARTEFACT.read_text(encoding="utf-8"))
    assert ev["n_triplets"] == len(doc["triplets"])
    assert ev["n_edge_verdicts"] == sum(len(t["verdicts"]) for t in doc["triplets"])
    assert ev["s4_control"]["recorded_px"] == doc["s4_control"]["recorded_px"]
    assert ev["s5_control"]["n_edges"] == doc["s5_control"]["n_edges"]


def test_no_residual_is_advertised_above_the_reject_threshold(ev):
    """A VERIFIED row must have closed under the frozen 2.0 px line."""
    t = ev["residual_px"]["reject_threshold_px"]
    assert t == 2.0
    for r in ev["rows"]:
        if r["all_verified"]:
            assert r["residual_px"] < t, (
                f"{r['frames']} is shown VERIFIED at {r['residual_px']} px")


def test_the_refuted_prediction_is_carried_not_dropped(ev):
    """S2 was predicted MET and came out ~zero. The panel must say so."""
    assert ev["s2"]["met"] is False
    assert abs(ev["s2"]["spearman_rho"]) < 0.2


def test_the_marginal_edge_warning_survives(ev):
    """A 9-inlier edge inside a VERIFIED triplet is the honest caveat."""
    w = ev["weakest_triplet"]
    assert w is not None
    assert w["min_edge_inliers"] <= 10
    assert w["all_verified"] is True


def test_the_broken_coverage_criterion_is_reported(ev):
    """Producing VERIFIED pairs showed criterion 4 failing; keep showing it."""
    cov = ev["coverage"]
    assert cov["warn"] == 0.15
    assert cov["n_over_warn"] > 0
    assert cov["max"] > cov["warn"]


def test_both_controls_are_reported_and_held(ev):
    assert ev["s4_control"]["met"] is True
    assert ev["s4_control"]["difference_px"] == 0.0
    assert ev["s5_control"]["met"] is True
    assert ev["s5_control"]["n_edges"] == 22


def test_the_not_claimed_list_refuses_the_accuracy_reading(ev):
    joined = " ".join(ev["not_claimed"]).upper()
    assert "NOT AN ACCURACY" in joined
    assert "GAUGE" in joined


def test_every_advertised_source_is_servable(ev):
    allowed = set(api.advertised_artefacts())
    for src in ev["sources"]:
        assert src in allowed


def test_the_page_renders_the_panel_and_fetches_its_endpoint(page):
    assert "function verdictCalibrationPanel" in page
    assert "${verdictCalibrationPanel(vm)}" in page
    assert "/api/evidence/verdict-calibration" in page
    assert "window.__VC" in page


def test_the_endpoint_serves_the_same_structure(ev):
    from fastapi.testclient import TestClient
    r = TestClient(api.app).get("/api/evidence/verdict-calibration")
    assert r.status_code == 200
    got = r.json()
    assert got["n_all_verified"] == ev["n_all_verified"]
    assert got["s2"]["met"] is False


# ---------------------------------------------------------------------------
# EXP-021 inside module 02: the same verdict against another mission's reference
# ---------------------------------------------------------------------------

def test_the_independent_check_is_read_from_exp021_and_carries_its_vacuity(ev):
    ic = ev["independent_check"]
    if ic is None:
        pytest.skip("EXP-021 artefacts absent")
    doc = json.loads((api.ROOT / "experiments/EXP-021/exp021_results.json").read_text(encoding="utf-8"))
    pooled = doc["criteria"]["primary_rates_b1_L2"]["pooled"]
    assert ic["fdr"] == pooled["FDR"] and ic["frr"] == pooled["FRR"]
    assert ic["far_n"] == 0                                   # the vacuity must travel with the zeros
    assert "NOT EVALUABLE" in ic["s2_reads"]
    assert "experiments/EXP-021/exp021_results.json" in ev["sources"]
    assert all(line.startswith("NOT ") for line in ic["not_claimed"])


def test_the_independent_check_renders_under_node_with_its_negatives(ev, page):
    import os
    import re
    import subprocess
    import tempfile
    from pathlib import Path

    ic = ev["independent_check"]
    if ic is None:
        pytest.skip("EXP-021 artefacts absent")
    node = next((n for n in (r"C:\Program Files\nodejs\node.exe", "/usr/bin/node")
                 if Path(n).exists()), None)
    if node is None:
        pytest.skip("node is not available on this machine")
    script = max(re.findall(r"<script>(.*?)</script>", page, re.S), key=len)
    start = script.index("function independentCheck")
    fn = script[start:script.index("\nfunction ", start + 10)]
    harness = (
        "const esc = s => String(s === undefined || s === null ? '' : s);\n"
        "const st = (w, k) => `<span class=\"st st-${k}\">${esc(w)}</span>`;\n"
        "const notClaimed = l => l.map(x => `<li>${esc(x)}</li>`).join('');\n"
        f"{fn}\nconst out = independentCheck({json.dumps(ic)});\n"
        # the panel's own prose says "undefined" (the FAR is), so look for a RENDERED
        # undefined -- beside a tag or a unit, the way a missing field would appear
        "if (/>undefined|undefined<|undefined (m|px|%)|NaN|\\[object/.test(out)) {"
        " console.error(out.slice(0, 500)); process.exit(2); }\n"
        "console.log(out);\n")
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / "ic.js"
        f.write_text(harness, encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True, env={**os.environ},
                           encoding="utf-8")
    assert r.returncode == 0, r.stderr[-600:]
    out = r.stdout
    for frag in ("NOT EVALUABLE", "PARTLY", "E-058", f"{ic['fdr']['k']} <small>/ {ic['fdr']['n']}</small>",
                 "not demonstrated", f"{ic['tier_ab']['verified_ambiguous']}"):
        assert frag in out, frag
