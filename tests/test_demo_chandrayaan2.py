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


def test_the_panel_scopes_the_verified_and_keeps_tmc2_rejected(ev):
    """OHRC's VERIFIED is loop closure only; TMC-2's loop stays REJECTED.

    The not-claimed list must keep the TMC-2 refusal, keep the accuracy
    disclaimer over OHRC's failed geometry clause, and keep IIRS at zero.
    """
    joined = " ".join(ev["not_claimed"]).upper()
    assert "NOT A VERIFIED TMC-2" in joined
    assert "2.2131" in joined            # the refused TMC-2 loop, unrounded
    assert "FAILED AS FROZEN" in joined  # OHRC's geometry clause
    assert "NO IIRS RESULT" in joined


def test_the_ohrc_block_reads_the_artefact_exactly(ev):
    """Every OHRC figure equals the recorded EXP-023 artefact, unrounded."""
    doc = json.loads(c2.EXP023_RESULTS.read_text(encoding="utf-8"))
    oh = ev["ohrc"]
    tri = doc["criteria"]["S3"]["primary_triangle"]
    assert oh["loop"]["residual_px"] == tri["loop_residual_px"]
    assert oh["loop"]["status"] == "VERIFIED"
    assert oh["loop"]["reject_threshold_px"] == 2.0
    assert oh["loop"]["residual_px"] < 2.0
    by_edge = {e["edge"]: e for e in oh["edges"]}
    for name in ("O1->Na", "O2->Na"):
        rec = doc["criteria"]["S2"]["edges"][name]
        assert by_edge[name]["n_inliers"] == rec["n_inliers"]
        assert by_edge[name]["geometry_median_px"] == \
            rec["geometry"]["refined_grid"]["median_px"]
        # S2's failure must be carried, never softened into a pass
        assert by_edge[name]["geometry_verdict"] == "INCONCLUSIVE"
        assert by_edge[name]["geometry_median_px"] > by_edge[name]["floor_px"]
    assert ev["ohrc"]["criteria_met"]["S2"] is False
    assert ev["ohrc"]["criteria_met"]["S3"] is True
    assert all(not n["pass"] for n in oh["nulls"]) and len(oh["nulls"]) == 2


def test_the_ohrc_panel_renders_under_node(page):
    """Execute chandrayaan2Panel against the live payload, as the demo rules
    require: the pass and the failed clause must both be in the rendered HTML,
    and no field may render as undefined."""
    import os
    import subprocess
    import tempfile
    from pathlib import Path

    node = "C:/Program Files/nodejs/node.exe"
    if not Path(node).exists():
        pytest.skip("node is not installed")
    script = page[page.index("<script>") + 8:page.index("</script>",
                                                        page.index("<script>"))]
    start = script.index("function chandrayaan2Panel")
    fn = script[start:script.index("\nfunction ", start + 10)]
    harness = (
        "const esc = s => String(s === undefined || s === null ? '' : s);\n"
        "const fx = v => v === undefined || v === null ? '-' : (+v).toFixed(2);\n"
        "const st = (w, k) => `<span class=\"st st-${k}\">${esc(w)}</span>`;\n"
        "const mod = (id, head, body) => `<section id=\"${id}\">${head}${body}</section>`;\n"
        "const modHead = (n, t, q, s) => `<h2>${esc(t)}</h2><p>${esc(q)} ${esc(s)}</p>`;\n"
        "const notClaimed = l => `<ul>${l.map(x => `<li>${esc(x)}</li>`).join('')}</ul>`;\n"
        "const srcLinks = l => l.map(esc).join(' ');\n"
        "const unavailable = () => 'UNAVAILABLE';\n"
        f"window = {{}}; window.__C2 = {json.dumps(c2.chandrayaan2_evidence())};\n"
        f"{fn}\nconst out = chandrayaan2Panel({{}});\n"
        "if (/>undefined|undefined<|undefined (m|px|%)|NaN /.test(out)) {"
        " console.error(out.slice(0, 800)); process.exit(2); }\n"
        "console.log(out);\n")
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / "c2.js"
        f.write_text(harness, encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True,
                           env={**os.environ}, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-600:]
    out = r.stdout
    for frag in ("VERIFIED", "S2 NOT MET", "18017", "17919", "30148",
                 "1.9158", "98.01", "first VERIFIED Chandrayaan-2 result",
                 "116 NAC products"):
        assert frag in out, frag


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
