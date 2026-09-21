"""The gauge-detection panel, and the negatives it is not allowed to lose.

This panel exists to put a measured limitation of the shipped verdict on the
page. The risk is not that it shows a wrong number -- every figure is read from
an artefact -- but that a later edit quietly drops the uncomfortable half and
leaves a panel that reads like a capability. These tests pin the uncomfortable
half.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from siim.demo import api
from siim.demo import exp013 as e13

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "src" / "siim" / "demo" / "static" / "index.html"

pytestmark = pytest.mark.skipif(
    not e13.exp013_status()["available"],
    reason="EXP-013 artefact absent: run scripts/run_exp013.py. Reported as "
           "CANNOT CHECK, not as checked and fine.")


@pytest.fixture(scope="module")
def ev() -> dict:
    return e13.exp013_evidence()


def _client() -> TestClient:
    return TestClient(api.app)


# ---------------------------------------------------------------------------
# the endpoint
# ---------------------------------------------------------------------------

def test_the_endpoint_serves_the_panel():
    r = _client().get("/api/evidence/gauge-detection")
    assert r.status_code == 200
    assert r.json()["blind_spot"]["n_cases"] > 0


def test_every_source_it_advertises_is_openable():
    c = _client()
    for rel in e13.exp013_evidence()["sources"]:
        r = c.get(f"/artefact/{rel}")
        assert r.status_code == 200, rel
        assert r.json()


def test_a_missing_artefact_is_named_never_worked_around(monkeypatch):
    monkeypatch.setattr(e13, "EXP013_ARTEFACT", ROOT / "experiments" / "no" / "such.json")
    with pytest.raises(Exception) as exc:
        e13.exp013_evidence()
    assert "no/such.json" in str(exc.value).replace("\\", "/")


# ---------------------------------------------------------------------------
# the negatives must stay on the page
# ---------------------------------------------------------------------------

def test_the_blind_spot_is_reported_as_verified_not_softened(ev):
    """The 36/36 is the reason this panel exists. It must survive edits."""
    b = ev["blind_spot"]
    assert b["n_verified"] == b["n_cases"], (
        "the gauge probe's cases are all VERIFIED; a panel that reports fewer "
        "has stopped reading the artefact")
    assert b["n_cases"] >= 36


def test_specificity_failed_and_the_panel_says_so(ev):
    """S2 is NOT MET. A panel that hides that is selling the instrument."""
    assert ev["criteria"]["S2"]["met"] is False
    assert ev["specificity"]["n_alarms"] == ev["specificity"]["n_triplets"]


def test_the_not_claimed_list_refuses_every_flattering_reading(ev):
    joined = " ".join(ev["not_claimed"]).upper()
    for phrase in ("NOT A FIX TO LOOP CLOSURE",
                   "NOT A VERDICT FALSE-ACCEPTANCE RATE",
                   "NOT VALIDATED AGAINST A REAL GAUGE ERROR",
                   "NOT AN ATTRIBUTION"):
        assert phrase in joined, phrase


def test_chandrayaan2_is_mentioned_only_with_a_negation(ev):
    blob = " ".join([ev["summary"], ev["scope"], *ev["not_claimed"]]).lower()
    for m in re.finditer("chandrayaan", blob):
        window = blob[max(0, m.start() - 80): m.end() + 80]
        assert any(n in window for n in ("no ", "not ", "never", "nothing")), window


def test_the_alarm_constants_travel_with_the_numbers(ev):
    rule = ev["alarm_rule"]
    assert rule["gauge_magnitude_alarm_px"] == 2.0
    assert rule["explained_fraction_alarm"] == 0.5
    assert "frozen" in rule


# ---------------------------------------------------------------------------
# the page renders what the endpoint returns
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_the_page_fetches_and_renders_the_panel(page):
    assert '/api/evidence/gauge-detection' in page
    assert "function gaugePanel" in page
    assert "${gaugePanel(vm)}" in page


def test_the_page_states_the_mechanism_not_only_the_outcome(page):
    """A reader who is told "the check can be fooled" and not why learns nothing.

    The cancellation is the whole point: it is an identity, so it cannot be
    fixed by tightening a threshold.
    """
    assert "G_a⁻¹" in page or "G_a^-1" in page
    assert "by algebra" in page


def test_the_page_keeps_the_verdict_separation_visible(page):
    lo = page.lower()
    assert "beside the verdict, never inside it" in lo
    assert "assess()" in page


def test_a_vacuous_s3_is_not_styled_as_a_win(page, ev):
    """Found by looking, 2026-09-21: the first browser check after five panels.

    S3 is MET as frozen and Part 2 calls the pass vacuous, because the
    zero-gauge control (S6) fired. The tile was green and read "64 px vs the
    84 px floor" -- a judge would read it as a sensitivity win. No string test
    caught it because every string was true. The tile must say "vacuous" next
    to the number whenever S6 is NOT MET, and must not take the good style.
    """
    s3, s6 = ev["criteria"]["S3"], ev["criteria"]["S6"]
    if not (s3["met"] and not s6["met"]):
        pytest.skip("only meaningful while S3 is MET and S6 is NOT MET")
    i = page.index("S3 — sensitivity floor")
    tile = page[i - 200: i + 700]
    assert "and vacuous" in tile, "the S3 tile must say the pass is vacuous when S6 fired"
    assert "zero-gauge control (S6) fired" in tile
    # the class expression must route a vacuous S3 to the failure style
    assert '!crit.S6.met) ? "bad"' in page


def test_the_panel_sits_after_the_verdict_calibration_panel(page):
    """The 36/36 is only honest next to the 13/13; order carries that."""
    assert page.index("${verdictCalibrationPanel(vm)}") < page.index("${gaugePanel(vm)}")


# ---------------------------------------------------------------------------
# no figure is invented in the page
# ---------------------------------------------------------------------------

def test_every_reported_figure_comes_from_the_artefact(ev):
    doc = json.loads(e13.EXP013_ARTEFACT.read_text(encoding="utf-8"))
    assert ev["detection_floor_px"] == doc["criteria"]["S3"]["detection_floor_px"]
    assert ev["per_edge_floor_px"] == doc["criteria"]["S3"]["per_edge_floor_px"]
    assert ev["specificity"]["n_triplets"] == len(doc["real_triplets"])
    assert len(ev["detection_sweep"]) == len(doc["synthetic_by_magnitude"])
