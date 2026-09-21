"""Checks that run **beside** a verdict, never inside it.

``siim.demo.verdict.assess`` is frozen: REAL-DATA-03, -04 and -05 each declare
they applied its rule unchanged, so a new rejection path inside it would
retroactively alter what those stages were evaluated under. ``verdict.py`` says
so in as many words:

    **Do not add geometric plausibility as a verdict criterion.** [...] The
    correct place for a new check is a new diagnostic reported beside the
    verdict, not inside it.

This package is that place. Nothing here may be imported by ``verdict.py``,
and ``tests/test_gauge_is_beside_the_verdict.py`` asserts the separation.
"""

from .gauge import (
    EXPLAINED_FRACTION_ALARM,
    GAUGE_MAGNITUDE_ALARM_PX,
    GaugeEdge,
    GaugeReport,
    decompose_gauge,
    decompose_gauge_graph,
    orient_cycle,
    two_core,
)

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
