"""The controlled-reference panel (EXP-019), and the negatives it must keep.

This panel carries the project's first accuracy-class number, which is exactly
the kind of figure that grows in the retelling. These tests pin the three
sentences that keep it honest: the criterion that failed (S5, the Chandrayaan-2
triangle, 2.177 against a frozen 2.0), the fact that the composed check shares
its reference and is therefore not absolute accuracy, and that every number is
read from the artefact rather than written into the page.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from siim.demo import api
from siim.demo import exp019 as e19

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "src" / "siim" / "demo" / "static" / "index.html"
NODE_CANDIDATES = (r"C:\Program Files\nodejs\node.exe", "/usr/bin/node", "node")

pytestmark = pytest.mark.skipif(
    not e19.exp019_status()["available"],
    reason="EXP-019 artefact absent: run scripts/run_exp019.py. Reported as "
           "CANNOT CHECK, not as checked and fine.")


@pytest.fixture(scope="module")
def ev() -> dict:
    return e19.exp019_evidence()


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


def _client() -> TestClient:
    return TestClient(api.app)


# ---------------------------------------------------------------------------
# the endpoint and its provenance
# ---------------------------------------------------------------------------

def test_the_endpoint_serves_the_panel():
    r = _client().get("/api/evidence/controlled-reference")
    assert r.status_code == 200
    assert r.json()["accuracy"]["n_pairs"] > 0


def test_every_source_it_advertises_is_openable(ev):
    c = _client()
    for rel in ev["sources"]:
        r = c.get(f"/artefact/{rel}")
        assert r.status_code == 200, rel
        assert r.json()


def test_a_missing_artefact_is_named_never_worked_around(monkeypatch):
    monkeypatch.setattr(e19, "EXP019_ARTEFACT", ROOT / "experiments" / "no" / "such.json")
    with pytest.raises(Exception) as exc:
        e19.exp019_evidence()
    assert "exp019_results.json" in str(exc.value) or "no/such.json" in str(exc.value)


# ---------------------------------------------------------------------------
# every number comes from the artefact
# ---------------------------------------------------------------------------

def test_the_accuracy_number_is_the_artefacts_number(ev):
    doc = json.loads((ROOT / "experiments" / "EXP-019" /
                      "exp019_results.json").read_text(encoding="utf-8"))
    s3 = doc["criteria"]["S3"]
    assert ev["accuracy"]["median_ref_px"] == s3["median_ref_px"]
    assert ev["accuracy"]["median_m"] == s3["median_m"]
    assert ev["accuracy"]["ci95_ref_px"] == s3["median_ci95_ref_px"]
    assert ev["accuracy"]["n_pairs"] == s3["n_pairs"]
    assert ev["accuracy"]["met"] is bool(s3["met"])


def test_the_triangle_is_reported_as_failing_with_its_margin(ev):
    """S5 did not pass, and the panel may not round that away."""
    tr = ev["triangle"]
    assert tr["met"] is False
    assert tr["closure_ref_px"] > tr["bar_ref_px"], "a failing closure must exceed its bar"
    assert tr["missed_by_pct"] > 0
    assert tr["bar_m"] and tr["closure_m"] > tr["bar_m"]


def test_the_attribution_reports_its_null_beside_the_correlation(ev):
    """r = 0.751 against a null p95 of 0.694 is a 0.06 margin, and it is shown."""
    r = ev["attribution"]["arm_R_only"]
    assert r["null_abs_r_p95"] is not None
    assert r["p_value_permutation"] is not None
    assert r["n"] >= 8


def test_the_floor_carries_the_frozen_reading_not_only_the_artefact_field(ev):
    """E-051: the artefact's S2 pools arm C, which Part 1 forbids."""
    fl = ev["floor"]
    assert fl["frozen_reading_m"] == pytest.approx(137.61, abs=0.01)
    assert fl["frozen_reading_n_frames"] == 12
    assert "E-051" in fl["note"]


# ---------------------------------------------------------------------------
# the page keeps the uncomfortable half
# ---------------------------------------------------------------------------

def test_the_panel_is_wired_into_the_boot_and_the_stage(page):
    assert '/api/evidence/controlled-reference' in page
    assert "window.__CR = cr;" in page
    assert "${controlledReferencePanel(vm)}" in page
    assert "of 7 modules on disk" in page, "the module count must include this panel"


def test_the_panel_prints_the_failed_criterion_and_the_shared_reference(page):
    body = page[page.index("function controlledReferencePanel"):]
    body = body[:body.index("\nfunction ")]
    assert "missed by" in body, "S5's margin must be on the page"
    assert "was not moved" in body, "the frozen line's status must be stated"
    assert "what_it_is_not" in body, "the shared-reference caveat must be rendered"
    assert "not_claimed" in body, "the not-claimed list must be rendered"


def test_the_panel_function_runs_against_the_live_payload(ev):
    """Extract the function, feed it the real evidence, and execute it.

    A string test cannot catch a ReferenceError in a template literal; this one
    can, and that class of defect has reached this page before.
    """
    node = next((n for n in NODE_CANDIDATES if n == "node" or Path(n).exists()), None)
    if node is None:
        pytest.skip("node is not available on this machine")
    html = PAGE.read_text(encoding="utf-8")
    js = max(re.findall(r"<script>(.*?)</script>", html, re.S), key=len)
    start = js.index("function controlledReferencePanel")
    fn = js[start:js.index("\nfunction ", start + 10)]
    harness = (
        "const esc = s => String(s === undefined || s === null ? '' : s);\n"
        "const sci = x => String(x);\n"
        "const st = (t, k) => `[${t}/${k}]`;\n"
        "const mod = (id, head, body) => head + body;\n"
        "const modHead = (n, t, q, s) => `${n} ${t} ${q} ${s}`;\n"
        "const unavailable = (a, b, c, d, e) => 'UNAVAILABLE';\n"
        f"window = {{}};\nwindow.__CR = {json.dumps(ev)};\n"
        f"{fn}\n"
        "const out = controlledReferencePanel({});\n"
        "if (out.indexOf('undefined') !== -1) { console.error('RENDERED undefined'); process.exit(2); }\n"
        "if (out.length < 500) { console.error('RENDERED too short'); process.exit(3); }\n"
        "console.log('OK', out.length);\n")
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "panel.js"
        f.write_text(harness, encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True,
                           env={**os.environ})
    assert r.returncode == 0, f"panel failed to render: {r.stderr[-800:]}"
    assert r.stdout.startswith("OK")
