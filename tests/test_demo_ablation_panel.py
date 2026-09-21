"""The component-ablation panel, and the bound it is not allowed to lose.

This panel makes the project's strongest architectural claim, so the thing
worth pinning is not the headline number — it is the paragraph that says what
the number does NOT license. EXP-006 measured one protocol step, chosen because
it is the only one whose both levels were recorded; a later edit that drops
that caveat turns a bounded result into the universal thesis the master plan
rules unfalsifiable.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from siim.demo import api
from siim.demo import exp006 as e6

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "src" / "siim" / "demo" / "static" / "index.html"

pytestmark = pytest.mark.skipif(
    not e6.exp006_status()["available"],
    reason="EXP-006 artefact absent: run scripts/run_exp006.py. Reported as "
           "CANNOT CHECK, not as checked and fine.")


@pytest.fixture(scope="module")
def ev() -> dict:
    return e6.exp006_evidence()


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_the_endpoint_serves_the_panel():
    r = TestClient(api.app).get("/api/evidence/component-ablation")
    assert r.status_code == 200
    assert r.json()["n_pairs"] > 0


def test_every_source_it_advertises_is_openable(ev):
    c = TestClient(api.app)
    for rel in ev["sources"]:
        assert c.get(f"/artefact/{rel}").status_code == 200, rel


def test_a_missing_artefact_is_named_never_worked_around(monkeypatch):
    monkeypatch.setattr(e6, "EXP006_ARTEFACT", ROOT / "experiments" / "no" / "such.json")
    with pytest.raises(Exception) as exc:
        e6.exp006_evidence()
    assert "no/such.json" in str(exc.value).replace("\\", "/")


# ---------------------------------------------------------------------------
# the bound, which is the part an edit would quietly drop
# ---------------------------------------------------------------------------

def test_the_panel_refuses_the_general_thesis(ev):
    joined = " ".join(ev["not_claimed"]).lower()
    assert "not the general thesis" in joined
    assert "unfalsifiable as phrased" in joined
    assert "because a defect was found" in joined, (
        "the panel must say the ablated step was recovered from a defect, not "
        "designed as an ablation — that is what bounds the claim")


def test_the_page_renders_the_bound_not_only_the_headline(page):
    assert "What this does not license" in page
    assert "at least one protocol step outweighs a" in page
    assert "general claim unfalsifiable as phrased" in page


def test_the_panel_reports_the_non_significant_matcher_arm(ev):
    """p = 0.0625 does not clear 0.05 and the panel must not round it down."""
    joined = " ".join(ev["not_claimed"])
    assert "0.0625" in joined
    assert "does not clear 0.05" in joined


# ---------------------------------------------------------------------------
# the figures are the artefact's, not the page's
# ---------------------------------------------------------------------------

def test_every_figure_comes_from_the_artefact(ev):
    doc = json.loads(e6.EXP006_ARTEFACT.read_text(encoding="utf-8"))
    crit = doc["criteria"]
    assert ev["n_pairs"] == doc["n_paired_pairs"]
    assert ev["headline"]["mean_changed_protocol"] == crit["S1"]["mean_changed_protocol"]
    assert ev["headline"]["mean_changed_matcher"] == crit["S1"]["mean_changed_matcher"]
    assert ev["headline"]["best_protocol_p"] == crit["S2"]["best_protocol_p"]
    assert ev["s5"]["rescued_by_protocol"] == crit["S5"]["n_rescued_by_protocol"]


def test_the_direction_asymmetry_survives(ev):
    """The qualitative finding: a protocol fix is monotone, a swap is a trade.

    If a later run makes the protocol regress anywhere, the panel's framing has
    to change with it — so this pins the property, not a number.
    """
    h = ev["headline"]
    assert h["protocol_regressions"] == 0
    assert h["matcher_regressions"] > 0
    assert h["ratio"] > 1.0


def test_chandrayaan2_is_mentioned_only_with_a_negation(ev):
    blob = " ".join([ev["summary"], ev["scope"], *ev["not_claimed"]]).lower()
    for m in re.finditer("chandrayaan", blob):
        w = blob[max(0, m.start() - 80): m.end() + 80]
        assert any(n in w for n in ("no ", "not ", "never", "nothing")), w


def test_the_panel_precedes_the_engines_panel(page):
    """Why-this-architecture reads before which-engine-is-better."""
    assert page.index("${ablationPanel(vm)}") < page.index("${enginesPanel(vm)}")
