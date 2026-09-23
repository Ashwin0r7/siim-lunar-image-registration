"""The live tool's guidance never leaves the reader without a next action.

`liveModel()` derives the step, the status line, the next-step sentence and
the action buttons from the real state. This test executes it under node for
every state a session passes through -- empty, one image, both, engine
chosen, running, each result, third image added, verified, error -- and pins
that each state names a step, says what is happening, says what to do next,
and offers at least one button whose action `liveAct` actually performs.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "src" / "siim" / "demo" / "static" / "index.html").read_text(encoding="utf-8")
SCRIPT = max(re.findall(r"<script>(.*?)</script>", PAGE, re.S), key=len)
NODE = next((n for n in (r"C:\Program Files\nodejs\node.exe", "/usr/bin/node") if Path(n).exists()), None)


def _fn(name: str) -> str:
    start = SCRIPT.index(f"function {name}")
    return SCRIPT[start:SCRIPT.index("\nfunction ", start + 10)]


def _handled_actions() -> set[str]:
    return set(re.findall(r'case "([a-z0-9-]+)"', _fn("liveAct")))


STATES = {
    "empty": {},
    "source only": {"src": 1},
    "reference only": {"ref": 1},
    "both": {"src": 1, "ref": 1},
    "engine chosen": {"src": 1, "ref": 1, "engineTouched": True},
    "running": {"src": 1, "ref": 1, "running": True},
    "pair inconclusive": {"src": 1, "ref": 1, "phase": "result", "lastKind": "pair",
                          "last": {"verdict": {"status": "INCONCLUSIVE"}}},
    "pair rejected": {"src": 1, "ref": 1, "phase": "result", "lastKind": "pair",
                      "last": {"verdict": {"status": "REJECTED"}}},
    "third added after pair": {"src": 1, "ref": 1, "thr": 1, "phase": "result", "lastKind": "pair",
                               "last": {"verdict": {"status": "INCONCLUSIVE"}}},
    "verified": {"src": 1, "ref": 1, "thr": 1, "phase": "result", "lastKind": "triplet",
                 "last": {"verdict": {"status": "VERIFIED"}}},
    "error": {"src": 1, "ref": 1, "phase": "error",
              "error": {"next": "check the server", "actions": [["Try again", "register"]]}},
}


@pytest.mark.skipif(NODE is None, reason="node is not available")
def test_every_state_has_a_step_a_status_a_next_step_and_a_working_action():
    engines = SCRIPT[SCRIPT.index("const LIVE_ENGINES"):SCRIPT.index("//: \"What is this?\"")]
    harness = (
        f"{engines}\n"
        "let LIVE = {};\n"
        "const liveEngine = () => 'B1';\n"
        f"{_fn('liveEngineName')}\n{_fn('liveModel')}\n"
        f"const states = {json.dumps(STATES)};\n"
        "const out = {};\n"
        "for (const [k, v] of Object.entries(states)) { LIVE = Object.assign({src: null, ref: null, thr: null,"
        " running: false, phase: 'input', lastKind: null, last: null, error: null}, v); out[k] = liveModel(); }\n"
        "console.log(JSON.stringify(out));\n")
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / "g.js"
        f.write_text(harness, encoding="utf-8")
        r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8",
                           env={**os.environ})
    assert r.returncode == 0, r.stderr[-800:]
    models = json.loads(r.stdout)
    handled = _handled_actions()
    for name, m in models.items():
        assert 1 <= m["step"] <= 7, name
        assert m["state"] and m["next"], name
        assert m["acts"], f"{name}: a state with no next action is a dead end"
        for label, act, *_ in m["acts"]:
            assert act in handled, f"{name}: button {label!r} has action {act!r} that liveAct does not handle"
    assert models["empty"]["acts"][0][1] == "add-src"
    assert models["source only"]["acts"][0][1] == "add-ref"
    assert models["both"]["step"] == 3 and models["engine chosen"]["step"] == 4
    assert models["running"]["acts"][0][1] == "cancel"
    assert any(a[1] == "add-thr" for a in models["pair inconclusive"]["acts"])
    assert any(a[1] == "engine" for a in models["pair rejected"]["acts"])
    assert models["third added after pair"]["acts"][0][1] == "verify"
    assert models["verified"]["step"] == 7 and any(a[1] == "new" for a in models["verified"]["acts"])


def test_the_steps_explain_themselves_and_the_help_never_needs_hover():
    card = _fn("liveCard")
    for label in ("What to do", "Why", "What happens", "Next"):
        assert f'"{label}"' in card, label
    assert card.count("liveHelp(") >= 5, "terms are explained where they are used"
    assert "<details" in SCRIPT[SCRIPT.index("const liveHelp"):SCRIPT.index("const liveGuide")], (
        "help is a disclosure, so it works by tap and keyboard, not only by hover")
    for n in range(1, 8):
        assert f"step({n}, " in card, f"step {n} is missing"


def test_guided_and_expert_change_presentation_only():
    css = PAGE[:PAGE.index("</style>")]
    rule = re.search(r"body\.expert [^{]*\{display:none\}", css.replace("\n", ""))
    assert rule, "expert mode must hide the teaching layer"
    assert "input" not in rule.group(0) and "button" not in rule.group(0), (
        "expert mode may not hide a control")
    assert 'data-mode="guided"' in PAGE and 'data-mode="expert"' in PAGE
