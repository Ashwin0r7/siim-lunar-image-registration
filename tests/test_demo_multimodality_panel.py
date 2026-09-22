"""The multi-modality panel (EXP-020), and the three sentences it must keep.

A panel about the problem statement's title word is the one most likely to be
read as a capability claim. These tests pin: that it says "not IIRS" before it
says anything else, that the criterion the PS row actually asks for is shown as
MET while the stage's own absolute bound is shown as NOT MET, and that the 85 m
inter-product offset under every number is on the same screen.
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
from siim.demo import exp020 as e20

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "src" / "siim" / "demo" / "static" / "index.html"
NODE_CANDIDATES = (r"C:\Program Files\nodejs\node.exe", "/usr/bin/node", "node")

pytestmark = pytest.mark.skipif(
    not e20.exp020_status()["available"],
    reason="EXP-020 artefacts absent: run scripts/run_exp020.py and its arm-N "
           "supplements. Reported as CANNOT CHECK, not as checked and fine.")


@pytest.fixture(scope="module")
def ev() -> dict:
    return e20.exp020_evidence()


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


def _client() -> TestClient:
    return TestClient(api.app)


def test_the_endpoint_serves_the_panel():
    r = _client().get("/api/evidence/multimodality")
    assert r.status_code == 200
    assert r.json()["bands"]


def test_every_source_it_advertises_is_openable(ev):
    c = _client()
    for rel in ev["sources"]:
        r = c.get(f"/artefact/{rel}")
        assert r.status_code == 200, rel
        assert r.json()


def test_it_says_not_iirs_and_names_the_substitute(ev):
    sub = ev["substitution"]
    assert "IIRS" in sub["why"] or "IIRS" in sub["iirs"]
    assert "Kaguya MI" in sub["instrument"]
    assert any("NOT an IIRS result" in x for x in ev["not_claimed"])


def test_the_frozen_clause_and_the_absolute_bound_are_reported_separately(ev):
    """S2 as frozen is MET; S1's metre bound is not. Both, on the same screen."""
    assert ev["s2_as_frozen"]["met"] is True
    assert ev["s2_as_frozen"]["worst_ratio"] <= ev["s2_as_frozen"]["bar"]
    assert ev["s1"]["met"] is False
    assert ev["s1"]["n_within_bound"] == 0
    assert "E-053" in ev["s2_as_frozen"]["note"]


def test_the_numbers_are_the_artefacts_numbers(ev):
    doc = json.loads((ROOT / "experiments" / "EXP-020" /
                      "exp020_results.json").read_text(encoding="utf-8"))
    s1 = doc["criteria"]["S1"]
    assert ev["s1"]["median_err_m"] == s1["median_err_m"]
    assert ev["s1"]["n_pass"] == s1["n_pass"]
    assert [b["wavelength_nm"] for b in ev["bands"]] == [
        b["wavelength_nm"] for b in s1["per_band"]]


def test_the_inter_product_offset_is_carried_with_its_inlier_counts(ev):
    ip = ev["inter_product_offset"]
    assert ip["estimate_m"][0] and ip["estimate_m"][1]
    assert ip["b4l_inliers"][0] and ip["b4l_inliers"][0] > 100
    assert "one mission" in ip["what"]


def test_the_thermal_clause_states_its_failure_mode(ev):
    th = ev["thermal"]
    assert th["met"] is False
    assert th["failure_mode"] == "starvation"
    assert th["n_keypoints_thermal"] is not None and th["n_keypoints_thermal"] < 100


def test_the_cross_mission_arm_reports_the_wrong_pass_too(ev):
    cm = ev["cross_mission"]
    assert cm["cropped_b1"]["n_pass"] == 0, "the classical engine does not reach it"
    assert cm["cropped_b4l"]["n_pass"] >= 1
    assert cm["cropped_b4l"]["n_wrong_pass"] >= 1, (
        "the supplement's wrong pass must not be dropped from the count")


def test_the_panel_is_wired_into_the_boot_and_the_stage(page):
    assert "/api/evidence/multimodality" in page
    assert "window.__MM = mm;" in page
    assert "${multimodalityPanel(vm)}" in page
    assert re.search(r"of \d+ modules on disk", page), "the module count must be shown"


def test_the_panel_leads_with_the_substitution_and_keeps_the_negatives(page):
    body = page[page.index("function multimodalityPanel"):]
    body = body[:body.index("\nfunction ")]
    first_note = body[body.index('<div class="note'):]
    assert "not an IIRS result" in first_note[:900], (
        "the substitution must be stated before any number")
    assert "wrong pass" in body
    assert "not_claimed" in body
    assert "starvation" not in body or "failure_mode" in body


def test_the_panel_function_runs_against_the_live_payload(ev):
    node = next((n for n in NODE_CANDIDATES if n == "node" or Path(n).exists()), None)
    if node is None:
        pytest.skip("node is not available on this machine")
    html = PAGE.read_text(encoding="utf-8")
    js = max(re.findall(r"<script>(.*?)</script>", html, re.S), key=len)
    start = js.index("function multimodalityPanel")
    fn = js[start:js.index("\nfunction ", start + 10)]
    harness = (
        "const esc = s => String(s === undefined || s === null ? '' : s);\n"
        "const sci = x => String(x);\n"
        "const st = (t, k) => `[${t}/${k}]`;\n"
        "const mod = (id, head, body) => head + body;\n"
        "const modHead = (n, t, q, s) => `${n} ${t} ${q} ${s}`;\n"
        "const unavailable = (a, b, c, d, e) => 'UNAVAILABLE';\n"
        f"window = {{}};\nwindow.__MM = {json.dumps(ev)};\n"
        f"{fn}\n"
        "const out = multimodalityPanel({});\n"
        "if (out.indexOf('undefined') !== -1) { console.error('RENDERED undefined'); process.exit(2); }\n"
        "if (out.length < 800) { console.error('RENDERED too short'); process.exit(3); }\n"
        "console.log('OK', out.length);\n")
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "panel.js"
        f.write_text(harness, encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True, env={**os.environ})
    assert r.returncode == 0, f"panel failed to render: {r.stderr[-800:]}"
    assert r.stdout.startswith("OK")
