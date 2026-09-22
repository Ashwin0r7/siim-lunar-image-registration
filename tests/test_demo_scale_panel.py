"""The scale panel (EXP-016), and the three things it must not let a reader do.

The stage's result is unusually easy to misread in three specific ways, and
each of these tests pins one of them:

* **the envelope without the mechanism.** "32 : 1" on its own tells a reader
  nothing about their own sensor pair. The panel has to carry the pixel floor
  N* and the control that established it, because the floor is what transfers;
* **the coarse pixel read as a fine pixel.** The agreement improves in coarse
  pixels as the ladder climbs and worsens in metres. Both columns must be on
  the page, or a scale result reads as an accuracy result;
* **a tie read as a loss.** S3 is NOT MET because the un-normalised arm tied
  the normalised one everywhere, which is a different statement from the
  architecture's step losing. The payload must carry the counts that say so.

The last test runs the panel function under node against the live payload,
because a string test cannot catch an `undefined` inside a template literal.
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
from siim.demo import exp016 as e16

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "src" / "siim" / "demo" / "static" / "index.html"
NODE_CANDIDATES = (r"C:\Program Files\nodejs\node.exe", "/usr/bin/node", "node")

pytestmark = pytest.mark.skipif(
    not e16.exp016_status()["available"],
    reason="EXP-016 artefact absent: run scripts/run_exp016.py. Reported as "
           "CANNOT CHECK, not as checked and fine.")


@pytest.fixture(scope="module")
def ev() -> dict:
    return e16.exp016_evidence()


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_the_endpoint_serves_the_panel():
    r = TestClient(api.app).get("/api/evidence/scale")
    assert r.status_code == 200
    assert r.json()["per_rung"]


def test_every_source_it_advertises_is_openable(ev):
    c = TestClient(api.app)
    for rel in ev["sources"]:
        assert c.get(f"/artefact/{rel}").status_code == 200, rel


def test_the_acceptance_is_reported_not_met_with_its_envelope(ev):
    s1 = ev["criteria"]["S1"]
    assert s1["met"] is False, "the problem statement's 320:1 acceptance is NOT MET"
    assert s1["envelope_r"] is not None, (
        "a NOT MET acceptance must still carry the measured envelope; that is "
        "the number the deliverable can defend")
    rungs = {r["r"]: r for r in ev["per_rung"]}
    assert rungs[320]["n_success"] == 0
    assert rungs[s1["envelope_r"]]["n_success"] >= rungs[64]["n_success"]


def test_no_rung_reports_a_wrong_pass(ev):
    """Every failure on this ladder is the inlier rule, never a wrong answer
    that passed. If that ever stops being true the panel must not keep the
    claim."""
    assert all(r["n_wrong_pass"] == 0 for r in ev["per_rung"])
    assert (ev["secondary"]["B4L"] or {}).get("n_wrong_pass") == 0


def test_the_mechanism_travels_with_the_envelope(ev):
    """The envelope is local to this data; the pixel floor is what transfers."""
    s2 = ev["criteria"]["S2"]
    assert s2["verdict"] in ("STARVATION", "DESCRIPTOR", "UNRESOLVED")
    assert (s2["pixel_floor"] or {}).get("N_star"), (
        "N* is the portable number; the panel is not allowed to show an "
        "envelope without it")
    assert s2["concordance"] is not None and s2["beta_N"] is not None
    assert s2["beta_r"] is not None, (
        "the ratio coefficient is the whole point of the control and must be "
        "shown even though it is indistinguishable from zero")
    assert ev["ps_arithmetic"]["pairings"], (
        "the problem statement's own pairings must be checkable against N*")
    assert "arithmetic" in ev["ps_arithmetic"]["note"], (
        "the pairing table is arithmetic, not evidence, and must say so")


def test_the_error_is_carried_in_metres_as_well_as_coarse_pixels(ev):
    """0.5 coarse px is 16 m at 32:1 and 160 m at 320:1. Both or neither."""
    checked = [r for r in ev["per_rung"] if r["consistency_median_coarse_px"] is not None]
    assert checked, "at least one rung must report agreement"
    for r in checked:
        assert r["consistency_median_m"] is not None, (
            f"rung {r['r']} shows coarse pixels with no metres beside them")
    px = [r["consistency_median_coarse_px"] for r in checked]
    m = [r["consistency_median_m"] for r in checked]
    assert px[-1] < px[0] and m[-1] > m[0], (
        "the two columns move in opposite directions; that is exactly why both "
        "are required, and if the data ever stops doing this the prose above "
        "the table is wrong")
    assert "NOT accuracy" in ev["criteria"]["S4"]["label"]


def test_the_ablation_tie_is_not_presentable_as_a_loss(ev):
    """S3 is NOT MET because both arms were perfect, not because ours lost."""
    s3 = ev["criteria"]["S3"]
    assert s3["met"] is False
    assert s3["D_ge_N_every_rung"] is True, (
        "the normalised arm never did worse; a panel that let S3 read as a "
        "defeat would be wrong in the other direction")
    assert (s3["mcnemar"] or {}).get("n_discordant") == 0
    for r in ev["arm_N"]:
        assert r["D_success"] == r["N_success"], (
            f"rung {r['r']}: the arms are recorded as tied and the panel says so")
        assert r["N_recovered_scale_median"] is not None, (
            "the un-normalised arm's recovered scale is the one continuous "
            "statistic that separates the arms and must survive the tie")


def test_the_two_failed_harness_clauses_are_visible(ev):
    """S0 gates the stage as frozen. The panel reports the stage anyway and
    must therefore show the gate."""
    s0 = ev["criteria"]["S0"]
    assert s0["met"] is False
    assert s0["operator_bitexact"] is False or s0["self_scale_shift_ok"] is False
    assert s0["recorded_counts_reproduced"] is True and s0["native_gate"] is True, (
        "the clauses that did hold are what make the failing ones readable")


def test_the_localisation_arm_keeps_its_two_failures_apart(ev):
    """At 320:1 the peaks are in the right place and not sharp enough; lower
    down one window's *prediction* is wrong. Collapsing the two would blame
    the correlator for the archive's corner map."""
    s5 = ev["criteria"]["S5"]
    assert s5["met"] is False
    by_r = {r["r"]: r for r in ev["arm_L"]}
    assert set(by_r) >= {32, 320}
    assert all(p is not None and p < 5.0 for p in by_r[320]["psr"]), (
        "the 320:1 cells fail on peak sharpness, not on position")
    assert max(abs(o) for o in by_r[320]["offsets_coarse_px"]) < 1.5, (
        "both 320:1 offsets are inside the tolerance; that is the finding")


def test_it_does_not_claim_a_cross_sensor_or_an_accuracy_result(ev):
    joined = " ".join(ev["not_claimed"]).lower()
    assert "not a cross-sensor result" in joined
    assert "not accuracy" in joined
    assert "ohrc" in joined, "the 320:1 arithmetic must be disclaimed by name"
    assert len(ev["not_claimed"]) >= 5


def test_the_panel_is_wired_into_the_boot_and_the_stage(page):
    assert "/api/evidence/scale" in page
    assert "window.__SC = sc;" in page
    assert "${scalePanel(vm)}" in page
    assert 'href="#m08"' in page, "the nav must reach the panel"
    assert re.search(r"of \d+ modules on disk", page), "the module count must be shown"


def test_the_panel_renders_against_the_live_payload(ev):
    node = next((n for n in NODE_CANDIDATES if n == "node" or Path(n).exists()), None)
    if node is None:
        pytest.skip("node is not available on this machine")
    js = max(re.findall(r"<script>(.*?)</script>", PAGE.read_text(encoding="utf-8"), re.S), key=len)
    start = js.index("function scalePanel")
    fn = js[start:js.index("\nfunction ", start + 10)]
    harness = (
        "const esc = s => String(s === undefined || s === null ? '' : s);\n"
        "const st = (t, k) => `[${t}/${k}]`;\n"
        "const mod = (i, h, b) => h + b;\n"
        "const modHead = (n, t, q, s) => `${n} ${t} ${q} ${s}`;\n"
        "const unavailable = (a, b, c, d, e) => 'UNAVAILABLE';\n"
        f"window = {{}};\nwindow.__SC = {json.dumps(ev)};\n{fn}\n"
        "const out = scalePanel({});\n"
        "const bad = out.match(/>\\s*(undefined|NaN)|(undefined|NaN)\\s*(px|m|<|:)/);\n"
        "if (bad) { console.error('RENDERED ' + bad[0]); process.exit(2); }\n"
        "if (!out.includes('STARVATION')) { console.error('NO VERDICT'); process.exit(4); }\n"
        "if (out.length < 1200) { console.error('TOO SHORT'); process.exit(3); }\n"
        "console.log('OK', out.length);\n")
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "p.js"
        f.write_text(harness, encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True, env={**os.environ})
    assert r.returncode == 0, r.stderr[-600:]
    assert r.stdout.startswith("OK")
