"""The viewpoint panel (EXP-017), and the shape of result it has to carry.

Most panels show criteria that passed or failed. This one has to show two that
are **undefined** — the onset they were written to characterise never
happened — without letting that read as "viewpoint is harmless". These tests
pin that, the literal-versus-bound split of the problem statement's acceptance,
and the blind spot (the verdict rejects nothing at any angle).
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
from siim.demo import exp017 as e17

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "src" / "siim" / "demo" / "static" / "index.html"
NODE_CANDIDATES = (r"C:\Program Files\nodejs\node.exe", "/usr/bin/node", "node")

pytestmark = pytest.mark.skipif(
    not e17.exp017_status()["available"],
    reason="EXP-017 artefact absent: run scripts/run_exp017.py. Reported as "
           "CANNOT CHECK, not as checked and fine.")


@pytest.fixture(scope="module")
def ev() -> dict:
    return e17.exp017_evidence()


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_the_endpoint_serves_the_panel():
    r = TestClient(api.app).get("/api/evidence/viewpoint")
    assert r.status_code == 200
    assert r.json()["by_e"]


def test_every_source_it_advertises_is_openable(ev):
    c = TestClient(api.app)
    for rel in ev["sources"]:
        assert c.get(f"/artefact/{rel}").status_code == 200, rel


def test_the_undefined_criteria_are_marked_undefined_not_passed(ev):
    c = ev["criteria"]
    assert c["S3"]["undefined"] is True
    assert c["S3"]["n_cells_at_or_above_onset"] == 0
    assert c["S3"]["met"] is False, "an undefined criterion may not be reported MET"
    assert c["S5"]["undefined"] is True
    assert c["S2"]["n_with_onset"] == 0


def test_the_literal_acceptance_and_the_bound_reading_are_separate(ev):
    c = ev["criteria"]
    assert c["S1a"]["met"] is False
    assert c["S1a"]["envelope_L1"] == 0 and c["S1a"]["envelope_L2"] == 0, (
        "the literal acceptance holds at e = 0 and nowhere else")
    assert c["S1b"]["met"] is True
    assert c["S1b"]["envelope_L2"] > c["S1b"]["envelope_L1"], (
        "orthorectifying with the DEM the deliverable has must be the wider envelope")


def test_the_blind_spot_is_carried_with_its_number(ev):
    b = ev["blind_spot"]
    assert b["never_rejected"] is True and b["pass_at_every_e"] is True
    assert b["p99_at_30"] and b["p99_at_30"] > 1.0, (
        "the p99 at the top of the sweep is the number that makes 'never rejected' matter")


def test_the_anticonservative_null_is_reported_beside_the_used_one(ev):
    n = ev["nulls"]
    assert n["met"] is True
    assert n["pixel_perm_fires_at_e0"] > n["shift_null_fires_at_e0"], (
        "the control that would have been wrong must be visible")


def test_the_construction_is_labelled_a_precision_bound(ev):
    assert "precision" in ev["construction"]["bound_on"]
    assert any("upper bound on" in x.lower() for x in ev["not_claimed"])
    assert any("NOT a real off-nadir result" in x for x in ev["not_claimed"])


def test_the_panel_is_wired_into_the_boot_and_the_stage(page):
    assert "/api/evidence/viewpoint" in page
    assert "window.__VP = vp;" in page
    assert "${viewpointPanel(vm)}" in page
    assert "of 9 modules on disk" in page


def test_the_panel_renders_against_the_live_payload(ev):
    node = next((n for n in NODE_CANDIDATES if n == "node" or Path(n).exists()), None)
    if node is None:
        pytest.skip("node is not available on this machine")
    js = max(re.findall(r"<script>(.*?)</script>", PAGE.read_text(encoding="utf-8"), re.S), key=len)
    start = js.index("function viewpointPanel")
    fn = js[start:js.index("\nfunction ", start + 10)]
    harness = (
        "const esc = s => String(s === undefined || s === null ? '' : s);\n"
        "const st = (t, k) => `[${t}/${k}]`;\n"
        "const mod = (i, h, b) => h + b;\n"
        "const modHead = (n, t, q, s) => `${n} ${t} ${q} ${s}`;\n"
        "const unavailable = (a, b, c, d, e) => 'UNAVAILABLE';\n"
        f"window = {{}};\nwindow.__VP = {json.dumps(ev)};\n{fn}\n"
        "const out = viewpointPanel({});\n"
        # the panel's own prose contains the word 'undefined'; a rendered
        # *value* would appear next to a tag or a unit, so look for those.
        "const bad = out.match(/>\\s*(undefined|NaN)|(undefined|NaN)\\s*(px|m|<|\\u00b0)/);\n"
        "if (bad) { console.error('RENDERED ' + bad[0]); process.exit(2); }\n"
        "if (out.length < 1200) { console.error('TOO SHORT'); process.exit(3); }\n"
        "console.log('OK', out.length);\n")
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "p.js"
        f.write_text(harness, encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True, env={**os.environ})
    assert r.returncode == 0, r.stderr[-600:]
    assert r.stdout.startswith("OK")
