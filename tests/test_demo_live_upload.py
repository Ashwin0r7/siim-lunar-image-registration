"""The live upload path — the one part of this page a judge *operates*.

Everything else on the page is read. This is the part where someone puts two
files in and gets a verdict out, so the failure modes are different: a slot
that silently accepts a PDF, a Register button that starts a run with nothing
loaded, a result that shows a registered image for a REJECTED verdict, or a
"success" screen that hides the refusal. These tests pin the behaviour that
keeps those from coming back.

The rendering tests execute the page's own functions under node against a
payload shaped like the API's, because a template literal's ReferenceError is
invisible to a string test and has reached this page before.
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
ASSETS = ROOT / "src" / "siim" / "demo" / "assets"
NODE_CANDIDATES = (r"C:\Program Files\nodejs\node.exe", "/usr/bin/node", "node")


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def script(page: str) -> str:
    return max(re.findall(r"<script>(.*?)</script>", page, re.S), key=len)


def _node() -> str | None:
    return next((n for n in NODE_CANDIDATES if n == "node" or Path(n).exists()), None)


def _fn(script: str, name: str) -> str:
    start = script.index(f"function {name}")
    return script[start:script.index("\nfunction ", start + 10)]


# ---------------------------------------------------------------------------
# the two slots
# ---------------------------------------------------------------------------

def test_both_slots_are_drop_targets_a_keyboard_can_reach(script):
    card = _fn(script, "liveCard")
    assert 'role="button"' in card and 'tabindex="0"' in card, (
        "a drop zone that only responds to a mouse excludes keyboard users")
    assert card.count('class="drop"') >= 1 and 'data-slot="${id}"' in card
    for slot in ('"src", "Source"', '"ref", "Reference"'):
        assert slot in card, f"missing slot {slot}"
    assert 'accept="image/*"' in card


def test_the_slot_handlers_cover_drop_click_paste_and_clear(script):
    wire = _fn(script, "wireLive")
    for handler in ("ondragover", "ondragleave", "ondrop", "onclick", "onkeydown"):
        assert handler in wire, f"{handler} is not wired"
    assert "document.onpaste" in wire, "paste is the fastest way to supply a screenshot"
    assert "data-clear" in wire and "data-example" in wire
    assert "live-swap" in wire


def test_a_non_image_is_refused_before_any_request_is_made(script):
    set_slot = _fn(script, "setSlot")
    assert "Use a PNG, JPEG or TIFF image" in set_slot
    assert "at least 64 px on each side" in set_slot, (
        "the API's own minimum must be stated in the browser, not discovered by a 400")


def test_the_run_button_starts_disabled_and_tracks_readiness(script):
    card = _fn(script, "liveCard")
    assert 'id="live-run" disabled' in card, "a run cannot be startable with no images"
    ready = _fn(script, "liveReady")
    assert "run.disabled = !ready" in ready
    assert "Add two images to begin." in ready


def test_the_status_line_is_announced_to_assistive_tech(script):
    card = _fn(script, "liveCard")
    assert 'id="live-status"' in card
    assert 'role="status"' in card and 'aria-live="polite"' in card


# ---------------------------------------------------------------------------
# the example pairs
# ---------------------------------------------------------------------------

def test_the_example_pairs_exist_on_disk_and_are_served():
    block = PAGE.read_text(encoding="utf-8")
    urls = set(re.findall(r'"(/assets/[^"]+\.png)"', block))
    assert urls, "the page offers no example pair"
    c = TestClient(api.app)
    for u in urls:
        assert (ASSETS / Path(u).name).exists(), f"{u} is advertised but absent"
        assert c.get(u).status_code == 200, f"{u} is not served"


def test_a_failing_example_is_offered_as_prominently_as_a_succeeding_one(script):
    card = _fn(script, "liveCard")
    assert card.count('class="exbtn"') == 2, (
        "a demo that offers only its good case is a brochure")
    consts = script[script.index("const LIVE_EXAMPLES"):script.index("const LIVE =")]
    assert "expected to fail" in consts
    assert "registers" in consts


# ---------------------------------------------------------------------------
# the result view
# ---------------------------------------------------------------------------

def test_no_registered_image_is_shown_when_the_verdict_refuses(script):
    body = _fn(script, "renderLive")
    assert "No registered image" in body
    assert "does not draw an alignment it\n      would not certify" in body.replace("\r", "")


def test_the_result_offers_the_evidence_and_a_way_to_keep_it(script):
    body = _fn(script, "renderLive")
    assert "live-corr" in body, "the correspondence overlay must be drawn"
    assert "Download the registered image" in body
    assert "Download this result as JSON" in body
    assert "Run another pair" in body
    assert "not a recorded number" in body


def test_the_swipe_comparison_is_wired_to_the_slider(script):
    body = _fn(script, "wireLiveResult")
    assert "clipPath" in body and "live-swipe-range" in body


def test_the_narrow_layout_stacks_the_two_slots(page):
    """The page keeps each component's narrow rules next to that component, so
    there are several `max-width:760px` blocks; the one that matters here is
    whichever declares `.drops`."""
    blocks = re.findall(r"@media \(max-width:760px\)\{(.*?)\n\}", page, re.S)
    assert blocks, "the page has no narrow-viewport rules at all"
    drops = [b for b in blocks if ".drops" in b]
    assert drops, "the two upload slots have no narrow-viewport rule"
    assert "grid-template-columns:1fr" in drops[0], (
        "on a phone the two slots must stack rather than shrink to thumbnails")
    assert ".runrow{grid-template-columns:1fr}" in drops[0], (
        "the engine selector and the Register button must stack too")


# ---------------------------------------------------------------------------
# execute the renderers against payloads shaped like the API's
# ---------------------------------------------------------------------------

_PAYLOAD = {
    "computation": "live", "data_source": "user_supplied", "engine": "B1",
    "timing": {"wall_s": 3.25},
    "summary": {"engine": "B1", "n_putative": 120, "n_inliers": 96, "n_refined": 90,
                "model": "affine", "model_selected_by": "held_out_on_refined_points"},
    "verdict": {"status": "INCONCLUSIVE", "confidence": "moderate",
                "reasons": ["the decisive check was not run"],
                "evidence": [{"name": "n_inliers", "value": 96.0, "verdict": "SUPPORTS",
                              "weight": "supporting"},
                             {"name": "loop_error_px", "value": None,
                              "verdict": "INCONCLUSIVE", "weight": "decisive"}]},
    "engine_agreement": None,
    "correspondences": {"src": [[1, 2], [3, 4]], "dst": [[5, 6], [7, 8]],
                        "inlier": [True, False], "refined": [True, False]},
    "source_png": "data:image/png;base64,AAAA", "reference_png": "data:image/png;base64,BBBB",
    "registered_png": "data:image/png;base64,CCCC",
    "caveats": ["not a recorded number"],
}


def _render(script: str, payload: dict) -> str:
    node = _node()
    if node is None:
        pytest.skip("node is not available on this machine")
    harness = (
        "const esc = s => String(s === undefined || s === null ? '' : s);\n"
        "const st = (t, k) => `[${t}/${k}]`;\n"
        "const notClaimed = xs => '<ul>' + (xs || []).map(x => `<li>${x}</li>`).join('') + '</ul>';\n"
        f"const d = {json.dumps(payload)};\n"
        f"{_fn(script, 'renderLive')}\n"
        "const out = renderLive(d);\n"
        "if (/undefined|NaN/.test(out)) { console.error('BAD:' + out.slice(0, 400)); process.exit(2); }\n"
        "console.log(out);\n")
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / "r.js"
        f.write_text(harness, encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True, env={**os.environ})
    assert r.returncode == 0, r.stderr[-600:]
    return r.stdout


def test_the_result_renders_with_a_registered_image(script):
    out = _render(script, _PAYLOAD)
    assert "live-swipe" in out and "Drag the slider" in out
    assert "Download the registered image" in out
    assert "INCONCLUSIVE" in out


def test_the_result_renders_without_one_and_says_why(script):
    payload = dict(_PAYLOAD)
    payload["registered_png"] = None
    payload["verdict"] = dict(payload["verdict"], status="REJECTED", confidence="none")
    out = _render(script, payload)
    assert "live-swipe" not in out
    assert "No registered image" in out
    assert "REJECTED" in out
    assert "Download the registered image" not in out


def test_the_card_renders_and_names_both_slots(script):
    node = _node()
    if node is None:
        pytest.skip("node is not available on this machine")
    consts = script[script.index("const LIVE_EXAMPLES"):script.index("const LIVE =")]
    harness = (
        "const esc = s => String(s === undefined || s === null ? '' : s);\n"
        "const mod = (id, head, body) => head + body;\n"
        "const modHead = (n, t, q, s) => `${n} ${t} ${q} ${s}`;\n"
        f"{consts}\n{_fn(script, 'liveCard')}\n"
        "const out = liveCard();\n"
        "if (/undefined/.test(out)) { console.error('BAD'); process.exit(2); }\n"
        "for (const need of ['drop-src', 'drop-ref', 'live-run', 'live-status', 'data-example'])\n"
        "  if (out.indexOf(need) === -1) { console.error('MISSING ' + need); process.exit(3); }\n"
        "console.log('OK', out.length);\n")
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / "c.js"
        f.write_text(harness, encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True, env={**os.environ})
    assert r.returncode == 0, r.stderr[-600:]
    assert r.stdout.startswith("OK")


# ---------------------------------------------------------------------------
# the endpoint behind it
# ---------------------------------------------------------------------------

def test_a_bad_upload_is_refused_with_a_message_naming_the_side():
    c = TestClient(api.app)
    r = c.post("/api/register", json={"source_png": "bm90IGFuIGltYWdl",
                                      "reference_png": "bm90IGFuIGltYWdl", "engine": "B1"})
    assert r.status_code == 400
    assert "source" in r.json()["detail"]


def test_an_unknown_engine_is_refused_before_any_decode():
    c = TestClient(api.app)
    r = c.post("/api/register", json={"source_png": "AAAA", "reference_png": "AAAA",
                                      "engine": "MAGIC"})
    assert r.status_code == 400
    assert "engine must be one of" in r.json()["detail"]


# ---------------------------------------------------------------------------
# a run is a thing you can watch, stop, and recover from
# ---------------------------------------------------------------------------

def test_a_run_in_flight_can_be_cancelled(script):
    card = _fn(script, "liveCard")
    assert 'id="live-cancel"' in card and "hidden" in card, (
        "a 60-second operation needs a way out that is not the back button")
    wire = _fn(script, "wireLive")
    assert "LIVE.abort.abort()" in wire
    run = _fn(script, "runLive")
    assert "AbortController" in run
    assert 'e.name === "AbortError"' in run and "Cancelled." in run
    assert "cancel.hidden = false" in run and "cancel.hidden = true" in run


def test_a_file_dropped_anywhere_on_the_card_lands_in_a_slot(script):
    wire = _fn(script, "wireLive")
    block = wire[wire.index('document.getElementById("live")'):]
    assert 'card.addEventListener("drop"' in block, (
        "a file dropped on the margin otherwise navigates away and loses the page")
    assert 'ev.target.closest(".drop")' in block, "the slots must keep their own handling"


def test_the_result_is_scrolled_into_view(script):
    run = _fn(script, "runLive")
    assert "scrollIntoView" in run


def test_a_refusal_suggests_the_engine_that_needs_nothing_extra(script):
    run = _fn(script, "runLive")
    assert "learned|extra" in run
    assert "choose <b>RootSIFT</b>" in run
    assert "Check that both files are images of the same ground." in run


def test_the_page_offers_two_ways_into_the_live_card(page):
    """The sidebar card is the only route a reader knows about if nothing else
    points at it; a judge reading the hero should not have to hunt."""
    assert 'id="hero-live"' in page, "the hero has no call to action"
    assert 'id="nav-live"' in page, "the sticky nav has no live entry"
    assert '["hero-live", "nav-live"].forEach' in page, (
        "both entry points must go through the one handler that renders and wires the card")
    hero = page[page.index('<p class="lede">'):page.index('<div class="hfigs"')]
    assert "herocta" in hero, "the call to action belongs with the lede, not below the figures"


# ---------------------------------------------------------------------------
# the third image: the only path on this page to VERIFIED
# ---------------------------------------------------------------------------

def test_the_card_offers_a_third_slot_and_says_what_it_buys(script, page):
    card = _fn(script, "liveCard")
    assert '"thr", "Third image' in card, "there is no third slot"
    assert "loop closure" in card and "VERIFIED" in card, (
        "the third slot must say what it changes, or it is just another box")
    ready = _fn(script, "liveReady")
    assert 'LIVE.thr ? "Register triplet" : "Register"' in ready
    assert "only way past INCONCLUSIVE" in ready


def test_three_images_go_to_the_triplet_endpoint(script):
    run = _fn(script, "runLive")
    assert "const triplet = !!LIVE.thr;" in run
    assert "/api/register-triplet" in run
    assert "a_png: LIVE.src.b64" in run and "c_png: LIVE.thr.b64" in run
    assert "renderLiveTriplet(d) : renderLive(d)" in run


def test_the_triplet_view_leads_with_the_loop_and_keeps_its_caveat(script):
    body = _fn(script, "renderLiveTriplet")
    assert "loop closure" in body
    assert "loop_reject_threshold_px" in body, "the frozen line must be shown beside the residual"
    assert "exactly</b> invariant" in body, (
        "a VERIFIED live result must carry what loop closure cannot see")
    assert "estimated_from" in body, "the independence of each edge must be visible"


def test_the_triplet_endpoint_registers_three_edges_and_closes_the_loop():
    """A real triplet, built from three overlapping crops of a recorded tile."""
    import base64
    import io

    import numpy as np
    from PIL import Image

    tile = ASSETS / "tile_nac.m1271742202lc.png"
    if not tile.exists():
        pytest.skip("the recorded tile asset is absent")
    a = np.asarray(Image.open(tile).convert("L"))
    if min(a.shape) < 460:
        pytest.skip("the tile is too small for three overlapping crops")

    def b64(arr):
        buf = io.BytesIO()
        Image.fromarray(arr.astype(np.uint8)).save(buf, "PNG")
        return base64.b64encode(buf.getvalue()).decode()

    c = TestClient(api.app)
    r = c.post("/api/register-triplet", json={
        "a_png": b64(a[0:400, 0:400]), "b_png": b64(a[20:420, 25:425]),
        "c_png": b64(a[40:440, 10:410]), "engine": "B1"})
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert [e["edge"] for e in d["edges"]] == ["A -> B", "B -> C", "C -> A"]
    assert all(e["estimated_from"] == "its own image pair" for e in d["edges"]), (
        "E-021: no edge may be derived from the other two")
    assert d["loop_error_px"] is not None and d["loop_error_px"] < d["loop_reject_threshold_px"]
    assert d["verdict"]["status"] == "VERIFIED", (
        "three overlapping crops of one tile must close the loop; if this fails the "
        "live path can never reach the verdict the page advertises")
    assert d["computation"] == "live" and d["data_source"] == "user_supplied"
    assert any("does NOT mean the alignment is correct" in c for c in d["caveats"])


def test_the_triplet_endpoint_refuses_the_two_engine_mode():
    c = TestClient(api.app)
    r = c.post("/api/register-triplet", json={"a_png": "AAAA", "b_png": "AAAA",
                                              "c_png": "AAAA", "engine": "both"})
    assert r.status_code == 400
    assert "one engine" in r.json()["detail"]


def test_the_match_points_csv_carries_its_own_provenance(script):
    """The PS asks for match points as a deliverable; a CSV with no header is a
    liability, because the coordinates are the pipeline's pixels, not the
    file's, and the verdict they belong to is not in the numbers."""
    node = _node()
    if node is None:
        pytest.skip("node is not available on this machine")
    fn = _fn(script, "wireLiveResult")
    harness = (
        "let written = null;\n"
        "class Blob { constructor(parts) { written = parts.join(''); } }\n"
        "const URL = {createObjectURL: () => 'blob:stub', revokeObjectURL: () => {}};\n"
        "const els = {};\n"
        "const mk = id => ({id, onclick: null, click(){}, style:{}, set href(v){}, set download(v){}});\n"
        "const document = {getElementById: id => (els[id] = els[id] || mk(id)),\n"
        "                  createElement: () => mk('a')};\n"
        "const setTimeout = (f) => {};\n"
        f"const d = {json.dumps(_PAYLOAD)};\n"
        "function drawLiveCorrespondences() {}\n"
        "const LIVE = {}; const $ = () => null; const paintSlot = () => {};\n"
        f"{fn}\n"
        "wireLiveResult(d, false);\n"
        "els['live-dl-points'].onclick();\n"
        "console.log(JSON.stringify(written));\n")
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / "csv.js"
        f.write_text(harness, encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True, env={**os.environ})
    assert r.returncode == 0, r.stderr[-600:]
    csv = json.loads(r.stdout)
    assert csv.startswith("# SIIM live registration - match points")
    assert "NOT a recorded number" in csv
    assert "verdict INCONCLUSIVE" in csv
    assert "down-sampled to 1024 px" in csv
    body = [ln for ln in csv.splitlines() if not ln.startswith("#")]
    assert body[0] == "source_x,source_y,reference_x,reference_y,inlier,refined"
    assert body[1] == "1,2,5,6,1,1", body[1]
    assert body[2] == "3,4,7,8,0,0", body[2]
