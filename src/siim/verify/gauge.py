"""Per-image gauge detection: the one error class loop closure cannot see.

Why this module exists
----------------------
The deliverable's decisive evidence is loop closure, and loop closure is
**exactly** invariant to a per-image coordinate error. If every image ``i``
carries its own gauge ``G_i`` and each edge is estimated in those gauged
frames::

    E_ij = G_j o T_ij o G_i^-1

then around a closed cycle the adjacent terms cancel::

    E_ca o E_bc o E_ab = G_a o (T_ca o T_bc o T_ab) o G_a^-1 = I

The loop closes to zero by algebra, however wrong each individual edge is.
EXP-012's supplementary probe measured the consequence end to end through
``assess()``: **36 of 36** such sets return VERIFIED / ``high`` with edges wrong
by a median of 14.04, 57.47 and 115.40 px (E-039).

This is not an implementation defect to patch. It is an identity, recorded in
``gtfree.loop_closure``'s docstring and in ADR-0011 note N1. What was missing
is an instrument that looks *only* at that null space.

Why the check has to be external
--------------------------------
Any statistic computed from the edge estimates alone lives inside the same
gauge and inherits the same invariance. Breaking the gauge needs a reference
that is not a function of the estimates. This module uses the one the project
already records on every REAL-DATA-07 row:
``geometry.predicted_transform_matrix``, derived from archive corner geometry
and SPICE ``SCALED_PIXEL`` without the matcher ever running.

That reference is **coarse** -- the recorded ``discrimination_floor_px`` runs
about 84-116 px at native NAC scale, so a 14 px gauge is far inside the floor
and the existing per-*edge* check (``scripts/check_transform_against_geometry.py``)
cannot see it. The claim this module tests is that per-*node* aggregation buys
the sensitivity the per-edge check lacks, because the two error classes have
different shapes:

=============================  ==============  =====================  ================
                               per-edge error  per-image gauge        reference noise
=============================  ==============  =====================  ================
appears on                     one edge        every edge at a node   every edge
coherent across a node's edges no              **yes**                no
seen by loop closure           **yes**         no                     n/a
seen by the per-edge check     above its floor only above its floor   it *is* the floor
=============================  ==============  =====================  ================

A gauge adds coherently across a node's edges; reference noise does not.

What it reports, and what it does not
-------------------------------------
:func:`decompose_gauge` fits one similarity gauge per image to the archive
disagreement and reports how much of that disagreement the per-node model
explains. It **localises a disagreement to an image; it does not attribute
blame.** A per-frame bias in the archive reference has the same shape as a
per-frame gauge in the estimate and is indistinguishable by this instrument
(EXP-013 Part 1 H3). That limitation is reported, not resolved by choosing the
flattering reading.

A gauge **common to every image** is near-unobservable here, and the reason is
structural rather than a tuning choice: a common ``G`` changes each edge only
by conjugation, ``E_ij = G T_ij G^-1``, whose effect scales with ``I - sR`` and
vanishes as the true transform approaches the identity. Holding one node at
identity removes that ill-conditioned direction instead of letting the
optimiser wander in it; what is recovered is the **relative** gauge between
images. Losing nothing else: an exact zero-residual solution with the fixed
node at identity always exists for a closed cycle (see ``orient_cycle``).

This module is imported by nothing that ``assess()`` touches, by design.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Sequence

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import least_squares

from ..geometry import Transform, pixel_grid

__all__ = [
    "EXPLAINED_FRACTION_ALARM",
    "GAUGE_MAGNITUDE_ALARM_PX",
    "GaugeEdge",
    "GaugeReport",
    "decompose_gauge",
    "decompose_gauge_graph",
    "orient_cycle",
    "two_core",
]

#: Frozen in EXP-013 Part 1 section 6, before any statistic was computed.
#: A fitted gauge below this is not an error worth reporting.
GAUGE_MAGNITUDE_ALARM_PX = 2.0
#: Frozen in EXP-013 Part 1 section 6. Below this, a large fitted gauge is
#: reference noise absorbed by free parameters, not a coherent per-node effect.
EXPLAINED_FRACTION_ALARM = 0.5

#: The alarm rule, stated once so the artefact and the code cannot drift.
ALARM_RULE = (
    f"gauge_magnitude_px > {GAUGE_MAGNITUDE_ALARM_PX} AND "
    f"explained_fraction > {EXPLAINED_FRACTION_ALARM} "
    "(EXP-013 Part 1 section 6, frozen before any statistic)"
)

_DOF = 4  # per node: dx, dy, rotation, log-scale


@dataclass(frozen=True)
class GaugeEdge:
    """One edge of a closed cycle, with its estimate and its external reference.

    ``estimate`` maps ``src`` pixels to ``dst`` pixels as the matcher found it.
    ``predicted`` maps the same way as archive geometry predicts it, computed
    without the matcher. ``floor_px`` is that edge's recorded discrimination
    floor -- the level below which the per-edge check cannot separate a
    disagreement from reference noise. It is reported for context and is not
    used in the fit.
    """

    src: str
    dst: str
    estimate: Transform
    predicted: Transform
    floor_px: float | None = None


@dataclass(frozen=True)
class GaugeReport:
    """What the per-node decomposition found, or why it refused to look."""

    status: str                       # "OK" | "CANNOT CHECK"
    alarm: bool
    reason: str
    nodes: tuple[str, ...] = ()
    fixed_node: str | None = None
    n_edges: int = 0
    n_grid: int = 0
    n_nodes: int = 0
    #: ``n_edges - (n_nodes - 1)``. Zero or below means the per-node model has
    #: at least as many free directions as the graph has constraints, so a high
    #: ``explained_fraction`` says nothing: it can fit anything. EXP-013 Part 2
    #: measures what a structureless disagreement scores at each redundancy.
    redundancy: int = 0
    residual_before_px: float | None = None
    residual_after_px: float | None = None
    explained_fraction: float | None = None
    gauge_magnitude_px: float | None = None
    per_node_px: dict[str, float] = field(default_factory=dict)
    edge_floor_px: dict[str, float] = field(default_factory=dict)
    rule: str = ALARM_RULE

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# similarity parameterisation
# ---------------------------------------------------------------------------

def _similarity(params: Sequence[float]) -> Transform:
    """``[dx, dy, theta_rad, log_scale]`` -> a similarity transform.

    Parameterised in ``log`` scale so that the identity is the origin and the
    optimiser cannot walk the scale through zero.
    """
    dx, dy, theta, log_s = (float(v) for v in params)
    s = float(np.exp(log_s))
    c, sn = np.cos(theta), np.sin(theta)
    m = np.array([[s * c, -s * sn, dx],
                  [s * sn, s * c, dy],
                  [0.0, 0.0, 1.0]], dtype=np.float64)
    return Transform(m, "similarity")


def _identity_params() -> list[float]:
    return [0.0, 0.0, 0.0, 0.0]


# ---------------------------------------------------------------------------
# cycle handling
# ---------------------------------------------------------------------------

def orient_cycle(edges: Sequence[GaugeEdge]) -> list[GaugeEdge] | None:
    """Reorder and invert edges so they traverse one closed directed cycle.

    Recorded edges carry the direction the engine was actually fed, which is
    not the cycle's direction and is not symmetric (E-036, and EXP-012's S5
    caught the same defect a second time). An edge traversed against its
    recorded direction has **both** its estimate and its prediction inverted,
    so the two stay in the same frame as each other.

    Returns ``None`` if the edges do not form exactly one closed cycle
    covering every node once.
    """
    if len(edges) < 3:
        return None
    nodes = {n for e in edges for n in (e.src, e.dst)}
    if len(nodes) != len(edges):
        return None

    remaining = list(edges)
    start = remaining[0].src
    ordered: list[GaugeEdge] = []
    current = start
    while remaining:
        for k, e in enumerate(remaining):
            if e.src == current:
                ordered.append(e)
                current = e.dst
                break
            if e.dst == current:
                try:
                    flipped = GaugeEdge(
                        src=e.dst, dst=e.src,
                        estimate=e.estimate.inverse(),
                        predicted=e.predicted.inverse(),
                        floor_px=e.floor_px,
                    )
                except ValueError:
                    return None
                ordered.append(flipped)
                current = e.src
                break
        else:
            return None
        remaining.pop(k)
    if current != start or len(ordered) != len(edges):
        return None
    return ordered


# ---------------------------------------------------------------------------
# the instrument
# ---------------------------------------------------------------------------

def two_core(edges: Sequence[GaugeEdge]) -> list[GaugeEdge]:
    """Drop nodes of degree < 2, repeatedly, and the edges that touch them.

    A degree-1 node contributes its own 4 free parameters and exactly one
    edge's worth of constraint, so it can always absorb that edge's
    disagreement completely. Leaving such nodes in inflates
    ``explained_fraction`` without any evidence behind it. The 2-core is the
    subgraph where every node is constrained by at least two edges.
    """
    kept = list(edges)
    while kept:
        deg: dict[str, int] = {}
        for e in kept:
            deg[e.src] = deg.get(e.src, 0) + 1
            deg[e.dst] = deg.get(e.dst, 0) + 1
        thin = {n for n, c in deg.items() if c < 2}
        if not thin:
            break
        kept = [e for e in kept if e.src not in thin and e.dst not in thin]
    return kept


def _connected(edges: Sequence[GaugeEdge], nodes: Sequence[str]) -> bool:
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    for e in edges:
        adj[e.src].add(e.dst)
        adj[e.dst].add(e.src)
    seen = {nodes[0]}
    stack = [nodes[0]]
    while stack:
        for nxt in adj[stack.pop()]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return len(seen) == len(nodes)


def _refuse(reason: str) -> GaugeReport:
    """A refusal, never a clean bill of health.

    ``CANNOT CHECK`` and ``no gauge detected`` are different statements and the
    deliverable must not blur them -- the same distinction the skipped
    re-derivation tests make when the NAC tiles are absent.
    """
    return GaugeReport(status="CANNOT CHECK", alarm=False, reason=reason)


def decompose_gauge(
    edges: Iterable[GaugeEdge],
    shape: tuple[int, int],
    *,
    grid_step: int = 64,
    fix_node: str | None = None,
) -> GaugeReport:
    """Decompose a **closed cycle**: the configuration loop closure is blind on.

    This is the entry point EXP-013 Part 1 section 4 specifies. It refuses
    anything that is not one closed cycle, because a per-image gauge is only
    *undetectable by loop closure* on a cycle, and that is the case the
    instrument exists to cover.

    See :func:`decompose_gauge_graph` for the same fit on a general graph, and
    read :attr:`GaugeReport.redundancy` before trusting either: on a 3-edge
    cycle the per-node model has 8 free parameters against 3 edges, and
    EXP-013 Part 2 measures how much a structureless disagreement scores there.
    """
    return _decompose(edges, shape, grid_step=grid_step, fix_node=fix_node,
                      require_cycle=True)


def decompose_gauge_graph(
    edges: Iterable[GaugeEdge],
    shape: tuple[int, int],
    *,
    grid_step: int = 64,
    fix_node: str | None = None,
) -> GaugeReport:
    """The same fit on any connected graph, not only a cycle.

    More edges per node is the only thing that makes ``explained_fraction``
    falsifiable, so a census graph discriminates where a triplet cannot.
    Pass the graph through :func:`two_core` first unless you have a reason not
    to.
    """
    return _decompose(edges, shape, grid_step=grid_step, fix_node=fix_node,
                      require_cycle=False)


def _decompose(
    edges: Iterable[GaugeEdge],
    shape: tuple[int, int],
    *,
    grid_step: int = 64,
    fix_node: str | None = None,
    require_cycle: bool = True,
) -> GaugeReport:
    """Fit one similarity gauge per image to the archive disagreement.

    The objective is identically zero at the true gauges when the prediction
    equals the true transform::

        sum over edges, over grid:  || E_ij(G_i(x)) - G_j(P_ij(x)) ||^2

    because ``E_ij o G_i = G_j o T_ij = G_j o P_ij`` by the definition in the
    module docstring. With no gauge error, ``G = I`` for every node is that
    solution, so a gauge-free triplet has nothing to explain and the fit has
    nowhere useful to go -- which is what makes the *explained fraction*, not
    the raw residual, the discriminating statistic.

    :param shape: ``(n_rows, n_cols)`` of the source frames, for the sample grid.
    :param grid_step: grid spacing in px. The statistic is an RMS over the
        grid, so it is insensitive to this within reason.
    :param fix_node: which image is held at identity. Defaults to the first
        node of the oriented cycle. See the module docstring for why one is
        held rather than all being free.
    """
    edges = list(edges)
    if require_cycle and len(edges) < 3:
        return _refuse(f"a closed cycle needs at least 3 edges; got {len(edges)}")
    if len(edges) < 1:
        return _refuse("no edges given")
    for e in edges:
        if e.predicted is None:
            return _refuse(f"edge {e.src} -> {e.dst} has no predicted transform: "
                           "there is no external reference to break the gauge")
    for e in edges:
        for name, t in (("estimate", e.estimate), ("predicted", e.predicted)):
            try:
                t.inverse()
            except ValueError:
                return _refuse(f"edge {e.src} -> {e.dst}: {name} is singular")

    if require_cycle:
        cycle = orient_cycle(edges)
        if cycle is None:
            return _refuse(
                "the edges do not form exactly one closed cycle covering every "
                "node once; a per-image gauge is only defined on a cycle, "
                "because that is where loop closure is blind to it")
        nodes = [e.src for e in cycle]
    else:
        cycle = edges
        nodes = sorted({n for e in cycle for n in (e.src, e.dst)})
        if not _connected(cycle, nodes):
            return _refuse(
                "the graph is not connected; per-image gauges are only "
                "comparable within a connected component, so each component "
                "must be decomposed separately")

    if fix_node is None:
        fix_node = nodes[0]
    if fix_node not in nodes:
        return _refuse(f"fix_node {fix_node!r} is not one of {tuple(nodes)}")
    free = [n for n in nodes if n != fix_node]

    grid = pixel_grid(shape, step=int(grid_step))
    if len(grid) < _DOF * len(free):
        return _refuse(f"grid of {len(grid)} points cannot constrain "
                       f"{_DOF * len(free)} free parameters; use a finer grid_step")

    def gauges(params: NDArray[np.float64]) -> dict[str, Transform]:
        g = {fix_node: _similarity(_identity_params())}
        for k, n in enumerate(free):
            g[n] = _similarity(params[k * _DOF:(k + 1) * _DOF])
        return g

    def residuals(params: NDArray[np.float64]) -> NDArray[np.float64]:
        g = gauges(np.asarray(params, dtype=np.float64))
        out = []
        for e in cycle:
            lhs = e.estimate.apply(g[e.src].apply(grid))
            rhs = g[e.dst].apply(e.predicted.apply(grid))
            out.append((lhs - rhs).ravel())
        return np.concatenate(out)

    x0 = np.zeros(_DOF * len(free), dtype=np.float64)
    before_vec = residuals(x0)
    residual_before = float(np.sqrt(np.mean(np.sum(
        before_vec.reshape(-1, 2) ** 2, axis=1))))

    fit = least_squares(residuals, x0, method="lm", xtol=1e-12, ftol=1e-12)
    after_vec = residuals(fit.x)
    residual_after = float(np.sqrt(np.mean(np.sum(
        after_vec.reshape(-1, 2) ** 2, axis=1))))

    # A residual of exactly zero before the fit means estimate == prediction on
    # every edge: there is no disagreement to decompose, and the explained
    # fraction is undefined rather than 1.0.
    if residual_before <= 0.0:
        return GaugeReport(
            status="OK", alarm=False,
            reason="estimate and archive prediction agree exactly on every "
                   "edge; there is no disagreement to decompose",
            nodes=tuple(nodes), fixed_node=fix_node, n_edges=len(cycle),
            n_grid=len(grid), n_nodes=len(nodes),
            redundancy=len(cycle) - (len(nodes) - 1),
            residual_before_px=0.0, residual_after_px=0.0,
            explained_fraction=None, gauge_magnitude_px=0.0,
            per_node_px={n: 0.0 for n in nodes},
            edge_floor_px={f"{e.src} -> {e.dst}": e.floor_px
                           for e in cycle if e.floor_px is not None},
        )

    explained = 1.0 - residual_after / residual_before
    g = gauges(fit.x)
    per_node = {
        n: float(np.sqrt(np.mean(np.sum(
            (g[n].apply(grid) - grid) ** 2, axis=1))))
        for n in nodes
    }
    magnitude = float(max(per_node.values()))

    alarm = (magnitude > GAUGE_MAGNITUDE_ALARM_PX
             and explained > EXPLAINED_FRACTION_ALARM)
    if alarm:
        worst = max(per_node, key=lambda n: per_node[n])
        reason = (
            f"A per-image model explains {explained:.1%} of a "
            f"{residual_before:.2f} px archive disagreement, with the largest "
            f"gauge on {worst} at {per_node[worst]:.2f} px. Loop closure is "
            f"blind to this by construction, so a closing loop is not evidence "
            f"against it. This localises the disagreement to an image; it does "
            f"NOT say whether the estimate or the archive reference is the "
            f"wrong one.")
    else:
        why = []
        if magnitude <= GAUGE_MAGNITUDE_ALARM_PX:
            why.append(f"largest fitted gauge {magnitude:.2f} px is at or below "
                       f"the {GAUGE_MAGNITUDE_ALARM_PX} px reporting floor")
        if explained <= EXPLAINED_FRACTION_ALARM:
            why.append(f"a per-image model explains only {explained:.1%} of the "
                       f"{residual_before:.2f} px disagreement, which is what "
                       f"reference noise looks like, not a coherent per-node error")
        reason = "No per-image gauge reported: " + "; ".join(why) + "."

    return GaugeReport(
        status="OK", alarm=alarm, reason=reason,
        nodes=tuple(nodes), fixed_node=fix_node, n_edges=len(cycle),
        n_grid=len(grid), n_nodes=len(nodes),
        redundancy=len(cycle) - (len(nodes) - 1),
        residual_before_px=residual_before,
        residual_after_px=residual_after,
        explained_fraction=float(explained),
        gauge_magnitude_px=magnitude,
        per_node_px=per_node,
        edge_floor_px={f"{e.src} -> {e.dst}": e.floor_px
                       for e in cycle if e.floor_px is not None},
    )
