"""Gauge-detection evidence for the demo (EXP-013).

This panel exists to put the project's own worst finding on the page.

EXP-012 produced the first VERIFIED verdicts, and the same stage found that the
verdict's decisive evidence -- loop closure -- is **exactly** invariant to a
per-image coordinate error: 36 of 36 constructed cases return VERIFIED /
``high`` while every edge is wrong by up to 115 px (E-039). A deliverable that
shows only the 13/13 and not the 36/36 is selling a safety claim it has
already measured to be incomplete.

So the panel shows both: the instrument that detects the blind spot, its
measured sensitivity on synthetic gauges, and the reason it does **not** clear
real triplets -- which turns out to be a property of the archive reference
rather than of the estimates, established by three independent engines
recovering the same per-frame term.

A separate module for the same reason as :mod:`siim.demo.exp012` and
:mod:`siim.demo.chandrayaan2`: the recorded demo paths import
:mod:`siim.demo.evidence`, and the project's rule is to add a module rather
than edit one those artefacts depend on.
"""

from __future__ import annotations

from typing import Any

from .evidence import EXPERIMENTS, ROOT, DemoDataMissing, _read

__all__ = ["exp013_evidence", "exp013_status", "EXP013_SOURCES"]

EXP013_ARTEFACT = EXPERIMENTS / "EXP-013" / "exp013_results.json"
GAUGE_PROBE = EXPERIMENTS / "EXP-012" / "exp012_s3_gauge_probe.json"

EXP013_SOURCES = [
    "experiments/EXP-013/exp013_results.json",
    "experiments/EXP-012/exp012_s3_gauge_probe.json",
]

EXP013_SUMMARY = (
    "Loop closure is the verdict's decisive evidence, and there is one error "
    "it cannot see by algebra rather than by accident: give every image its "
    "own coordinate error and the terms cancel around the loop. Measured "
    "through the shipped verdict, 36 of 36 such cases come back VERIFIED with "
    "high confidence while every edge is wrong. This is the instrument that "
    "sees them -- reported beside the verdict, never inside it."
)

EXP013_SCOPE = (
    "Detection measured on synthetic gauge constructions; specificity "
    "measured on the 13 real LRO NAC triplets of EXP-012, against archive "
    "corner geometry as the external reference. One region, one instrument, "
    "no ground truth."
)

EXP013_NOT_CLAIMED = [
    "NOT a fix to loop closure. The invariance is an identity, not a bug: no "
    "amount of loop-closure precision helps, because the residual is zero by "
    "algebra. This is a second, independent check that looks only at the null "
    "space.",
    "NOT a verdict false-acceptance rate. This adds an instrument, not ground "
    "truth; the first two clauses of success criterion 3 remain unmeasurable.",
    "NOT validated against a real gauge error. No real triplet is known to "
    "carry one, so detection is measured on constructions and specificity on "
    "real data. That asymmetry is the main limitation and is not hidden.",
    "NOT an attribution. The instrument localises a disagreement to an image; "
    "it cannot say by itself whether the estimate or the archive reference is "
    "the wrong one. That was written down as H3 before the stage ran.",
    "NO Chandrayaan-2 evidence in this panel: these are LRO NAC triplets. The "
    "Chandrayaan-2 result is measured separately in the REAL-DATA-09 panel.",
]


def exp013_status() -> dict[str, Any]:
    missing = [str(p.relative_to(ROOT)).replace("\\", "/")
               for p in (EXP013_ARTEFACT, GAUGE_PROBE) if not p.exists()]
    return {"available": not missing, "missing": missing}


def _criterion(crit: dict, name: str) -> dict[str, Any]:
    c = crit.get(name) or {}
    return {"met": bool(c.get("met")), "statement": c.get("statement")}


def exp013_evidence() -> dict[str, Any]:
    """EXP-013, assembled for the page. Raises if an artefact is absent."""
    status = exp013_status()
    if not status["available"]:
        raise DemoDataMissing(
            "gauge-detection panel: missing " + ", ".join(status["missing"]))

    doc = _read(EXP013_ARTEFACT, "EXP-013 results",
                require=("criteria", "real_triplets", "synthetic_by_magnitude"))
    probe = _read(GAUGE_PROBE, "EXP-012 gauge probe",
                  require=("by_gauge_magnitude", "n_verified", "n_rows"))

    crit = doc["criteria"]

    # the defect, read from EXP-012's probe rather than restated
    blind_spot = {
        "n_cases": probe["n_rows"],
        "n_verified": probe["n_verified"],
        "by_magnitude": {
            m: {"n": k["n"], "n_verified": k["n_verified"],
                "median_true_error_px": k["median_true_error_px"],
                "max_loop_error_px": k["max_loop_error_px"]}
            for m, k in probe["by_gauge_magnitude"].items()},
        "source": "experiments/EXP-012/exp012_s3_gauge_probe.json",
    }

    # detection, by gauge magnitude
    sweep = [
        {"gauge_magnitude_px": float(m), **v}
        for m, v in sorted(doc["synthetic_by_magnitude"].items(), key=lambda kv: float(kv[0]))
    ]

    real = doc["real_triplets"]
    specificity = {
        "n_triplets": len(real),
        "n_alarms": sum(1 for r in real if r.get("alarm")),
        "median_archive_disagreement_px": doc.get("reference_noise_calibration_px"),
        "redundancy": sorted({r.get("redundancy") for r in real if r.get("redundancy") is not None}),
    }

    # the census graph -- where the per-node model is actually over-determined
    census = []
    for window, engines in (doc.get("supplementary_census_graph") or {}).items():
        for engine, rep in engines.items():
            if rep.get("status") != "OK":
                continue
            null = rep.get("structureless_null") or {}
            census.append({
                "window": window, "engine": engine,
                "n_edges": rep.get("n_edges"), "n_nodes": rep.get("n_nodes"),
                "redundancy": rep.get("redundancy"),
                "residual_before_px": rep.get("residual_before_px"),
                "residual_after_px": rep.get("residual_after_px"),
                "explained_fraction": rep.get("explained_fraction"),
                "gauge_magnitude_px": rep.get("gauge_magnitude_px"),
                "structureless_null_p95": null.get("p95"),
                "structureless_null_median": null.get("median"),
            })
    census.sort(key=lambda c: (c["window"], c["engine"]))

    cross = []
    for window, pairs in (doc.get("supplementary_cross_engine") or {}).items():
        for name, v in pairs.items():
            cross.append({"window": window, "pair": name,
                          "n_common_frames": v.get("n_common_frames"),
                          "max_difference_px": v.get("max_difference_px"),
                          "median_difference_px": v.get("median_difference_px")})
    cross.sort(key=lambda c: (c["window"], c["pair"]))

    return {
        "blind_spot": blind_spot,
        "alarm_rule": doc.get("alarm_rule"),
        "criteria": {
            "S0": _criterion(crit, "S0"), "S1": _criterion(crit, "S1"),
            "S2": _criterion(crit, "S2"), "S3": _criterion(crit, "S3"),
            "S4": _criterion(crit, "S4"), "S6": _criterion(crit, "S6"),
        },
        "detection_sweep": sweep,
        "detection_floor_px": (crit.get("S3") or {}).get("detection_floor_px"),
        "per_edge_floor_px": (crit.get("S3") or {}).get("per_edge_floor_px"),
        "specificity": specificity,
        "census_graph": census,
        "cross_engine": cross,
        "summary": EXP013_SUMMARY,
        "scope": EXP013_SCOPE,
        "not_claimed": list(EXP013_NOT_CLAIMED),
        "sources": list(EXP013_SOURCES),
    }
