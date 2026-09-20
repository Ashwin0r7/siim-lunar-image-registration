"""The Chandrayaan-2 panel says what REAL-DATA-09 measured, and no more.

The problem statement is titled for Chandrayaan-2, so this is the panel a
judge reads first and the one most likely to be overstated. These tests pin
the two things that matter: every figure comes from a recorded artefact, and
the page never upgrades a REJECTED loop or an INCONCLUSIVE pair into a claim
the stage does not support.
"""

from __future__ import annotations

import json

import pytest

from siim.demo import api
from siim.demo import chandrayaan2 as c2

pytestmark = pytest.mark.skipif(
    not c2.chandrayaan2_status()["available"],
    reason="REAL-DATA-09 artefacts are not on disk")


@pytest.fixture(scope="module")
def ev() -> dict:
    return c2.chandrayaan2_evidence()


@pytest.fixture(scope="module")
def page() -> str:
    return (api.STATIC / "index.html").read_text(encoding="utf-8")


def test_every_number_comes_from_a_recorded_artefact(ev):
    """The panel's headline figures must equal the rows in the files."""
    b1 = json.loads((c2.RD09_B1).read_text(encoding="utf-8"))
    lg = json.loads((c2.RD09_LG).read_text(encoding="utf-8"))
    rows = [r for r in b1["rows"] + lg["rows"]
            if r.get("engine") and "error" not in r]
    assert ev["n_engine_rows"] == len(rows)
    assert ev["n_successes"] == sum(1 for r in rows if r.get("success"))
    assert ev["n_wrong_passes"] == sum(1 for r in rows if r.get("wrong_pass"))


def test_no_success_is_advertised_that_the_geometry_check_rejected(ev):
    """A pass with an INCONSISTENT transform is a wrong pass, never a success."""
    for r in ev["rows"]:
        for col in ("b1", "b4l"):
            if r.get(col + "_success"):
                assert r[col + "_geometry"] == "CONSISTENT", (
                    f"{r['frame']} {col} is advertised as a success with "
                    f"geometry {r[col + '_geometry']}")


def test_the_loop_is_reported_as_rejected_and_the_threshold_is_not_moved(ev):
    """2.2131 px against a 2.0 px line. The page must not round that away."""
    loop = ev["loop"]
    assert loop["reject_threshold_px"] == 2.0
    assert loop["residual_px"] > loop["reject_threshold_px"]
    assert loop["verdict"] == "REJECTED"
    assert len(loop["edges"]) == 3


def test_the_panel_claims_no_verified_chandrayaan2_pair(ev):
    """S1 is MET but no pair is VERIFIED; the not-claimed list must say so."""
    joined = " ".join(ev["not_claimed"]).upper()
    assert "NOT A VERIFIED" in joined
    assert "OHRC" in joined and "IIRS" in joined


def test_the_dem_render_arm_is_reported_as_failing_its_own_control(ev):
    """S4 NOT MET. The control passing 0 of 15 is the finding, not a footnote."""
    p5 = ev["p5_dem_render"]
    assert p5["control_passes"] == 0
    assert p5["test_passes"] == 0
    assert p5["n_frames"] > 0


def test_the_s6_control_is_reported_and_held(ev):
    assert ev["s6_control"]["met"] is True
    assert ev["s6_control"]["n_edges"] == 6
    assert 5365 in ev["s6_control"]["recorded_counts"]
    assert 1656 in ev["s6_control"]["recorded_counts"]


def test_the_acknowledgement_required_by_issdc_is_carried(ev):
    """PRADAN's terms (S15) require this wording wherever the data is used."""
    assert "Chandrayaan-II" in ev["acknowledgement"]
    assert "Indian Space Research Organisation" in ev["acknowledgement"]
    assert "Indian Space Science Data Centre" in ev["acknowledgement"]


def test_every_advertised_source_is_servable(ev):
    """Each linked path must be on the allow-list, or the link 404s."""
    allowed = set(api.advertised_artefacts())
    for src in ev["sources"]:
        assert src in allowed, f"{src} is linked by the panel but not servable"


def test_the_page_renders_the_panel_and_fetches_its_endpoint(page):
    assert "function chandrayaan2Panel" in page
    assert "${chandrayaan2Panel(vm)}" in page
    assert "/api/evidence/chandrayaan2" in page
    assert "window.__C2" in page


def test_the_endpoint_serves_the_same_structure(ev):
    from fastapi.testclient import TestClient
    r = TestClient(api.app).get("/api/evidence/chandrayaan2")
    assert r.status_code == 200
    got = r.json()
    assert got["n_successes"] == ev["n_successes"]
    assert got["loop"]["verdict"] == "REJECTED"
