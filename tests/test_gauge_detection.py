"""EXP-013's instrument, and the separation that lets it exist at all.

``verdict.py`` forbids a new rejection path inside ``assess()``, because
REAL-DATA-03, -04 and -05 each declare they applied that rule unchanged. The
first test here is the one that matters most: it pins the separation, not a
number.
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest

from siim.demo.verdict import assess
from siim.evaluation.gtfree import loop_closure
from siim.geometry import similarity
from siim.verify import (
    EXPLAINED_FRACTION_ALARM,
    GAUGE_MAGNITUDE_ALARM_PX,
    GaugeEdge,
    decompose_gauge,
    decompose_gauge_graph,
    two_core,
)

ROOT = Path(__file__).resolve().parents[1]
SHAPE = (512, 512)


# ---------------------------------------------------------------------------
# S5 -- the instrument is beside the verdict, not inside it
# ---------------------------------------------------------------------------

def test_the_verdict_does_not_import_the_gauge_instrument():
    """EXP-013 S5. The whole stage is only legitimate because of this.

    Adding geometric plausibility inside ``assess()`` would retroactively alter
    what REAL-DATA-03, -04 and -05 were evaluated under. The gauge report is
    returned *beside* a verdict and can never move an edge across the
    pass/fail line.
    """
    src = (ROOT / "src" / "siim" / "demo" / "verdict.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
    offending = [m for m in imported if "verify" in m or "gauge" in m]
    assert not offending, (
        f"verdict.py imports {offending}: the gauge instrument has leaked into "
        "the frozen rule. It must be reported beside the verdict, never inside "
        "it -- see verdict.py's own 'Do not add geometric plausibility as a "
        "verdict criterion.'")


def test_the_alarm_constants_are_the_ones_part_1_froze():
    """They may not be tuned in Part 2. Pinned so a later edit is visible."""
    assert GAUGE_MAGNITUDE_ALARM_PX == 2.0
    assert EXPLAINED_FRACTION_ALARM == 0.5


# ---------------------------------------------------------------------------
# the mechanism: loop closure is blind, the instrument is not
# ---------------------------------------------------------------------------

def _gauge_case(seed: int, magnitude_px: float):
    rng = np.random.default_rng(seed)
    t_ab = similarity(1.02, np.deg2rad(3.0), 9.0, -6.0)
    t_bc = similarity(0.99, np.deg2rad(-2.0), -5.0, 7.0)
    t_ca = (t_bc @ t_ab).inverse()

    def g():
        return similarity(1.0, np.deg2rad(float(rng.normal(0, 0.4))),
                          *(float(v) for v in rng.normal(0, magnitude_px, size=2)))

    ga, gb, gc = g(), g(), g()
    return ([gb @ t_ab @ ga.inverse(), gc @ t_bc @ gb.inverse(), ga @ t_ca @ gc.inverse()],
            [t_ab, t_bc, t_ca])


def test_loop_closure_is_blind_to_a_gauge_and_assess_returns_verified():
    """The defect this stage exists for, asserted end to end (E-039).

    If this ever fails, the null space has changed and EXP-013's reason to
    exist has changed with it.
    """
    est, _ = _gauge_case(9001, 64.0)
    loop = float(loop_closure(est, SHAPE))
    assert loop < 1e-9, "the construction is not a gauge case"

    rng = np.random.default_rng(1)
    src = rng.uniform(0, SHAPE[0], size=(400, 2))
    dst = est[0].apply(src) + rng.normal(0, 0.4, size=src.shape)
    v = assess(transform=est[0], src_points=src, dst_points=dst,
               inlier_mask=np.ones(len(src), bool), shape=SHAPE,
               fit_rmse=None, loop_error_px=loop)
    assert v.status == "VERIFIED"


def test_the_instrument_sees_what_loop_closure_cannot():
    est, truth = _gauge_case(9001, 64.0)
    edges = [GaugeEdge(a, b, e, t) for (a, b), e, t in
             zip((("A", "B"), ("B", "C"), ("C", "A")), est, truth)]
    rep = decompose_gauge(edges, SHAPE)
    assert rep.status == "OK"
    assert rep.alarm is True
    assert rep.explained_fraction > 0.99, rep.explained_fraction
    assert rep.gauge_magnitude_px > GAUGE_MAGNITUDE_ALARM_PX


def test_a_gauge_free_triplet_raises_no_alarm():
    _, truth = _gauge_case(9001, 0.0)
    edges = [GaugeEdge(a, b, t, t) for (a, b), t in
             zip((("A", "B"), ("B", "C"), ("C", "A")), truth)]
    rep = decompose_gauge(edges, SHAPE)
    assert rep.status == "OK"
    assert rep.alarm is False
    assert rep.gauge_magnitude_px == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# refusals -- CANNOT CHECK is not "no gauge detected"
# ---------------------------------------------------------------------------

def test_a_missing_reference_is_refused_not_passed():
    _, truth = _gauge_case(9001, 0.0)
    edges = [GaugeEdge(a, b, t, None) for (a, b), t in
             zip((("A", "B"), ("B", "C"), ("C", "A")), truth)]
    rep = decompose_gauge(edges, SHAPE)
    assert rep.status == "CANNOT CHECK"
    assert rep.alarm is False
    assert "no predicted transform" in rep.reason
    assert rep.explained_fraction is None


def test_an_open_chain_is_refused_because_the_blind_spot_needs_a_cycle():
    _, truth = _gauge_case(9001, 0.0)
    edges = [GaugeEdge("A", "B", truth[0], truth[0]),
             GaugeEdge("B", "C", truth[1], truth[1]),
             GaugeEdge("C", "D", truth[2], truth[2])]
    rep = decompose_gauge(edges, SHAPE)
    assert rep.status == "CANNOT CHECK"
    assert "cycle" in rep.reason


def test_too_few_edges_is_refused():
    _, truth = _gauge_case(9001, 0.0)
    rep = decompose_gauge([GaugeEdge("A", "B", truth[0], truth[0])], SHAPE)
    assert rep.status == "CANNOT CHECK"
    assert "at least 3 edges" in rep.reason


def test_a_disconnected_graph_is_refused():
    _, truth = _gauge_case(9001, 0.0)
    edges = [GaugeEdge("A", "B", truth[0], truth[0]),
             GaugeEdge("C", "D", truth[1], truth[1])]
    rep = decompose_gauge_graph(edges, SHAPE)
    assert rep.status == "CANNOT CHECK"
    assert "not connected" in rep.reason


# ---------------------------------------------------------------------------
# orientation -- direction comes from the edge, and inverting must carry both
# ---------------------------------------------------------------------------

def test_an_edge_traversed_backwards_inverts_estimate_and_prediction_together():
    """E-036's defect, guarded structurally.

    If only the estimate were inverted, the prediction would be left in the
    other frame and every residual would be meaningless -- which is exactly how
    this instrument first read the real rows.
    """
    est, truth = _gauge_case(9001, 32.0)
    forward = [GaugeEdge(a, b, e, t) for (a, b), e, t in
               zip((("A", "B"), ("B", "C"), ("C", "A")), est, truth)]
    # same cycle, one leg recorded in the opposite direction
    backward = [forward[0],
                GaugeEdge("C", "B", est[1].inverse(), truth[1].inverse()),
                forward[2]]
    a = decompose_gauge(forward, SHAPE)
    b = decompose_gauge(backward, SHAPE)
    assert a.alarm == b.alarm
    assert b.explained_fraction == pytest.approx(a.explained_fraction, abs=1e-6)


# ---------------------------------------------------------------------------
# redundancy -- the number that says whether the explained fraction means anything
# ---------------------------------------------------------------------------

def test_redundancy_is_reported_so_a_high_explained_fraction_can_be_discounted():
    est, truth = _gauge_case(9001, 32.0)
    edges = [GaugeEdge(a, b, e, t) for (a, b), e, t in
             zip((("A", "B"), ("B", "C"), ("C", "A")), est, truth)]
    rep = decompose_gauge(edges, SHAPE)
    assert rep.n_nodes == 3
    assert rep.n_edges == 3
    assert rep.redundancy == 1


def test_two_core_drops_nodes_that_could_absorb_their_own_edge():
    _, truth = _gauge_case(9001, 0.0)
    cycle = [GaugeEdge("A", "B", truth[0], truth[0]),
             GaugeEdge("B", "C", truth[1], truth[1]),
             GaugeEdge("C", "A", truth[2], truth[2])]
    leaf = GaugeEdge("A", "Z", truth[0], truth[0])
    kept = two_core(cycle + [leaf])
    assert len(kept) == 3
    assert all(e.dst != "Z" for e in kept)
