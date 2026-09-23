"""The 2026-09-23 UX refactor keeps the page's contracts and adds its own.

Pinned here: every evidence section is still reachable from the (now grouped)
navigation; the engine radio group sends exactly the four values the API
accepts; status never relies on colour alone (a glyph per verdict); a hidden
element stays hidden whatever a component's display rule says; and the
server refuses oversized uploads before decoding them.
"""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path

from fastapi.testclient import TestClient

from siim.demo import api

PAGE = Path(api.STATIC / "index.html").read_text(encoding="utf-8")


def test_every_section_is_reachable_from_the_navigation():
    nav = PAGE[PAGE.index('<nav aria-label="Sections"'):PAGE.index("</nav>")]
    for sec in ["case"] + [f"m{i:02d}" for i in range(1, 11)] + ["live", "prov"]:
        assert f'href="#{sec}"' in nav, sec
    assert 'aria-expanded="false"' in nav, "group menus are disclosure buttons"
    assert 'id="menubtn"' in PAGE and 'aria-controls="sitenav"' in PAGE


def test_the_engine_group_sends_the_values_the_api_accepts():
    block = PAGE[PAGE.index("const LIVE_ENGINES"):PAGE.index("const LIVE =")]
    values = re.findall(r'value: "([^"]+)"', block)
    assert values == ["B1", "B4L", "B4X", "both"]
    assert set(values) == set(api.LIVE_ENGINES)
    assert "best" not in block.lower(), "trade-offs are measured, not adjectives"


def test_status_never_relies_on_colour_alone():
    for state in ("VERIFIED", "REJECTED", "INCONCLUSIVE"):
        assert f".{state} .vstat::before" in PAGE, state
        assert f".vb.v-{state}::before" in PAGE, state
    assert ".st-pass::before" in PAGE and ".st-fail::before" in PAGE


def test_hidden_always_wins():
    assert "[hidden]{display:none!important}" in PAGE


def test_the_server_refuses_an_image_that_would_decode_too_large():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("1", (9000, 9000)).save(buf, "PNG")        # ~10 KB file, 81 Mpx decoded
    b = base64.b64encode(buf.getvalue()).decode()
    r = TestClient(api.app).post("/api/register", json={"source_png": b, "reference_png": b})
    assert r.status_code == 413 and "megapixels" in r.json()["detail"]


def test_the_server_refuses_an_oversized_payload():
    big = "A" * (api.LIVE_MAX_UPLOAD_BYTES * 4 // 3 + 16)
    r = TestClient(api.app).post("/api/register", json={"source_png": big, "reference_png": big})
    assert r.status_code == 413
