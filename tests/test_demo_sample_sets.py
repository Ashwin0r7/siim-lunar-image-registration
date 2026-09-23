"""The live card's real lunar sample sets.

A reviewer who arrives without images should be able to put real archive
images through the pipeline in one click, see beforehand what the pipeline
returned on those exact files, and reach the refusals as easily as the
successes. These tests pin the endpoint (an allow-list, like ``/artefact``),
the ordering, and the card renderer, which is executed under node against the
live payload because a string test cannot see a template ReferenceError.
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

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "src" / "siim" / "demo" / "static" / "index.html"
MAN = ROOT / "sample_images" / "manifest.json"
NODE_CANDIDATES = (r"C:\Program Files\nodejs\node.exe", "/usr/bin/node", "node")

pytestmark = pytest.mark.skipif(not MAN.exists(), reason="sample_images not built")


def _client():
    return TestClient(api.app)


def _script() -> str:
    return max(re.findall(r"<script>(.*?)</script>", PAGE.read_text(encoding="utf-8"), re.S), key=len)


def _fn(script: str, name: str) -> str:
    start = script.index(f"function {name}")
    return script[start:script.index("\nfunction ", start + 10)]


def _node():
    return next((n for n in NODE_CANDIDATES if n == "node" or Path(n).exists()), None)


def test_the_endpoint_lists_every_committed_set_with_its_measured_outcome():
    d = _client().get("/api/samples").json()
    assert d["available"] is True
    committed = [s for s in d["scenarios"] if not s["local_only"]]
    man = json.loads(MAN.read_text(encoding="utf-8"))["scenarios"]
    assert [s["id"] for s in committed] == [s["id"] for s in man]
    for s, m in zip(committed, man):
        assert s["measured"]["status"] == m["live_check"]["status"]
    statuses = {s["measured"]["status"] for s in committed}
    assert {"VERIFIED", "REJECTED", "INCONCLUSIVE"} <= statuses, "the refusals must be offered too"


def test_a_local_chandrayaan2_set_if_present_leads_and_is_marked():
    d = _client().get("/api/samples").json()
    local = [s for s in d["scenarios"] if s["local_only"]]
    if local:
        assert d["scenarios"][0]["local_only"] is True
        assert all("ISRO" in (f["credit"] or "") for f in local[0]["files"]
                   if "Chandrayaan" in (f["instrument"] or ""))


def test_only_manifest_files_are_served():
    c = _client()
    s = c.get("/api/samples").json()["scenarios"][-1]
    assert c.get(s["files"][0]["url"]).status_code == 200
    assert c.get(s["files"][0]["url"]).headers["content-type"] == "image/png"
    for bad in (f"/samples/{s['id']}/README.md", f"/samples/{s['id']}/../manifest.json",
                "/samples/nope/x.png", f"/samples/{s['id']}/manifest.json"):
        assert c.get(bad).status_code == 404, bad


def test_the_gallery_cards_render_under_node_against_the_live_payload():
    node = _node()
    if node is None:
        pytest.skip("node is not available on this machine")
    script = _script()
    payload = _client().get("/api/samples").json()
    sci = script[script.index("const sci ="):script.index("};", script.index("const sci =")) + 2]
    harness = (
        "const esc = s => String(s === undefined || s === null ? '' : s);\n"
        f"{sci}\n{_fn(script, 'sampleCard')}\n"
        f"const d = {json.dumps(payload)};\n"
        "const out = d.scenarios.map(sampleCard).join('');\n"
        "if (/undefined|NaN|\\[object/.test(out)) { console.error('BAD ' + out.slice(0, 400)); process.exit(2); }\n"
        "for (const s of d.scenarios) {\n"
        "  if (out.indexOf('data-sample=\"' + s.id + '\"') === -1) { console.error('MISSING ' + s.id); process.exit(3); }\n"
        "  if (out.indexOf('v-' + s.measured.status) === -1) { console.error('NO STATUS ' + s.id); process.exit(4); }\n"
        "}\n"
        "console.log('OK', (out.match(/nothing drawn/g) || []).length);\n")
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / "g.js"
        f.write_text(harness, encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True, env={**os.environ})
    assert r.returncode == 0, r.stderr[-600:]
    n_refused = sum(1 for s in payload["scenarios"] if s["measured"]["status"] == "REJECTED")
    assert r.stdout.split() == ["OK", str(n_refused)], "every refusal says nothing was drawn"


def test_the_card_offers_multi_file_loading_and_every_table_is_wrapped():
    script = _script()
    card = _fn(script, "liveCard")
    assert 'id="live-multi"' in card and "multiple" in card
    assert 'id="live-samples"' in card
    assert "function wrapTables" in script and "MutationObserver" in script
