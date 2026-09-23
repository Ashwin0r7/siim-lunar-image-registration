"""Verdict-calibration evidence for the demo (EXP-012).

The demo's hardest question from a reader is "does your system ever say yes?"
Until EXP-012 the honest answer was no: every recorded verdict in the
repository was REJECTED, because VERIFIED needs loop closure under 2 px and the
42-pair census never formed triplets. This panel carries the answer, and it
carries the two findings that came with it -- that the residual does **not**
track edge strength, and that the coverage criterion fails once VERIFIED pairs
exist.

A separate module for the same reason as :mod:`siim.demo.chandrayaan2`: the
recorded demo paths import :mod:`siim.demo.evidence`, and the project's rule is
to add a module rather than edit one those artefacts depend on.
"""

from __future__ import annotations

from typing import Any

from .evidence import EXPERIMENTS, ROOT, DemoDataMissing, _read

__all__ = ["exp012_evidence", "exp012_status", "EXP012_SOURCES"]

EXP012_ARTEFACT = EXPERIMENTS / "EXP-012" / "exp012_results.json"

EXP012_SOURCES = ["experiments/EXP-012/exp012_results.json"]

#: EXP-021 -- the same verdict scored against another mission's reference. Its
#: two artefacts join this panel's sources only when both are on disk, so the
#: allow-list and the page cannot disagree about what is advertised.
EXP021_ARTEFACT = EXPERIMENTS / "EXP-021" / "exp021_results.json"
EXP021_TIER_AB = EXPERIMENTS / "EXP-021" / "exp021_s5_tier_ab_reading.json"
EXP021_SOURCES = ["experiments/EXP-021/exp021_results.json",
                  "experiments/EXP-021/exp021_s5_tier_ab_reading.json"]

EXP021_NOT_CLAIMED = [
    "NOT a false-acceptance rate: at the frozen ground truth no wrong transform existed "
    "to be accepted (FAR undefined, E-058). 0 of 12 counts VERIFIED edges that were right.",
    "NOT a held-out result: the independent reference reached 2 of 7 frames on the "
    "held-out site, so that reading is NOT EVALUABLE.",
    "NOT surveyed ground truth: correct means agreeing with the Kaguya TC ortho mosaic "
    "(JAXA) to 8.42 m, through a chain that uses no correspondence between the two images.",
]

EXP012_SUMMARY = (
    "Thirteen real triplets, thirteen VERIFIED -- and not one threshold was "
    "changed to get there. The strictest verdict this system ships is "
    "reachable on real lunar imagery, and the same run shows what it does not "
    "guarantee: loop closure cannot tell a nine-inlier edge from a "
    "sixteen-hundred-inlier one."
)

EXP012_SCOPE = (
    "Two ground windows on Mare Serenitatis, LRO NAC only, engine B1. The 13 "
    "triplets share frames and edges, so they are not 13 independent samples."
)

EXP012_NOT_CLAIMED = [
    "NOT an accuracy claim: loop closure is exactly invariant to per-image "
    "gauge error (ADR-0011 N1), so a closing loop verifies the transform set "
    "only up to that gauge. No surveyed ground truth exists for these pairs; "
    "the independent check above is another mission's product, not survey.",
    "NOT evidence that every contributing edge is strong: S2 was refuted. A "
    "9-inlier edge at 39.8 deg sits in a triplet closing at 1.15 px.",
    "NOT a verdict false-acceptance rate: triplet admissibility required "
    "success, which excludes wrong passes by construction, so a set that "
    "cannot contain a false acceptance cannot estimate their rate.",
    "NOT a Chandrayaan-2 result: one instrument, one region.",
]


def exp012_status() -> dict[str, Any]:
    missing = [str(p.relative_to(ROOT)).replace("\\", "/")
               for p in (EXP012_ARTEFACT,) if not p.exists()]
    return {"available": not missing, "missing": missing}


def exp012_evidence() -> dict[str, Any]:
    """EXP-012, assembled for the page. Raises if the artefact is absent."""
    status = exp012_status()
    if not status["available"]:
        raise DemoDataMissing(
            "verdict-calibration panel: missing " + ", ".join(status["missing"]))

    doc = _read(EXP012_ARTEFACT, "EXP-012 results",
                require=("triplets", "s4_control", "s5_control"))
    triplets = doc["triplets"]

    rows = []
    coverage: list[float] = []
    confidences: dict[str, int] = {}
    for t in triplets:
        statuses = t.get("statuses", [])
        for v in t.get("verdicts", []):
            vd = v.get("verdict") or {}
            conf = vd.get("confidence")
            if conf:
                confidences[conf] = confidences.get(conf, 0) + 1
            gap = (vd.get("metrics") or {}).get("coverage_max_gap")
            if isinstance(gap, (int, float)):
                coverage.append(float(gap))
        rows.append({
            "frames": [f[-12:] for f in t["frames"]],
            "window": t.get("window"),
            "min_edge_inliers": t.get("min_edge_inliers"),
            "residual_px": t.get("loop_closure_residual_px"),
            "statuses": sorted(set(statuses)),
            "all_verified": bool(statuses) and all(s == "VERIFIED" for s in statuses),
        })
    rows.sort(key=lambda r: (r["residual_px"] is None, r["residual_px"] or 0.0))

    residuals = [r["residual_px"] for r in rows if r["residual_px"] is not None]
    weakest = min((r for r in rows if r["min_edge_inliers"] is not None),
                  key=lambda r: r["min_edge_inliers"], default=None)
    crit = doc.get("criteria", {})
    over = [c for c in coverage if c > 0.15]

    return {
        "n_triplets": len(triplets),
        "n_all_verified": sum(1 for r in rows if r["all_verified"]),
        "n_edge_verdicts": sum(len(t.get("verdicts", [])) for t in triplets),
        "confidences": confidences,
        "rows": rows,
        "residual_px": {
            "min": min(residuals) if residuals else None,
            "max": max(residuals) if residuals else None,
            "reject_threshold_px": 2.0,
        },
        "weakest_triplet": weakest,
        "s4_control": {
            "met": bool(doc["s4_control"].get("met")),
            "recorded_px": doc["s4_control"].get("recorded_px"),
            "recomputed_px": doc["s4_control"].get("recomputed_px"),
            "difference_px": doc["s4_control"].get("abs_difference_px"),
        },
        "s5_control": {
            "met": bool(doc["s5_control"].get("met")),
            "n_edges": doc["s5_control"].get("n_edges"),
        },
        "s2": {
            "met": bool((crit.get("S2_residual_tracks_edge_quality") or {})
                        .get("spearman_rho", 0) < 0),
            "spearman_rho": (crit.get("S2_residual_tracks_edge_quality") or {})
                            .get("spearman_rho"),
        },
        "coverage": {
            "n": len(coverage),
            "n_over_warn": len(over),
            "warn": 0.15,
            "min": min(coverage) if coverage else None,
            "max": max(coverage) if coverage else None,
        },
        "summary": EXP012_SUMMARY,
        "scope": EXP012_SCOPE,
        "not_claimed": EXP012_NOT_CLAIMED,
        "independent_check": _exp021_block(),
        "sources": list(EXP012_SOURCES) + (EXP021_SOURCES if _exp021_present() else []),
    }


def _exp021_present() -> bool:
    return EXP021_ARTEFACT.exists() and EXP021_TIER_AB.exists()


def _exp021_block() -> dict[str, Any] | None:
    """EXP-021's scoring of this same verdict, read from its artefacts, or None.

    Every figure below is a field of ``exp021_results.json`` or
    ``exp021_s5_tier_ab_reading.json``; nothing is computed here except the
    median and maximum of the recorded per-edge errors.
    """
    if not _exp021_present():
        return None
    doc = _read(EXP021_ARTEFACT, "EXP-021 results", require=("criteria", "reported_beside"))
    ab = _read(EXP021_TIER_AB, "EXP-021 tier A u B reading", require=("summary",))
    crit = doc["criteria"]
    pooled = crit["primary_rates_b1_L2"]["pooled"]
    errs = sorted(float(e["e_m"]) for e in doc["reported_beside"]["verified_edge_errors"])
    n = len(errs)
    med = (errs[n // 2] if n % 2 else 0.5 * (errs[n // 2 - 1] + errs[n // 2])) if n else None
    abp = ab["summary"]["V+C|pooled"]
    return {
        "stage": "EXP-021",
        "reference": "SELENE (Kaguya) TC Ortho Map Seamless V2, 8.42 m, JAXA",
        "correct_line_m": 8.42, "wrong_line_m": 25.3,
        "fdr": pooled["FDR"], "frr": pooled["FRR"], "far_n": pooled["FAR"]["n"],
        "s2_reads": crit["S2"]["reads"], "s3_reads": crit["S3"]["reads"],
        "heldout_frames_tier_a": crit["S1"]["v_frames_tier_A"], "heldout_frames": 7,
        "withdraw_verified": bool(crit["S2"]["withdraw_verified_under_SS54"]),
        "verified_error_m": {"n": n, "median": med, "max": errs[-1] if errs else None},
        "tier_ab": {"verified": abp["verified"], "verified_wrong": abp["verified_wrong"],
                    "verified_ambiguous": abp["verified_ambiguous"],
                    "wrong_total": abp["wrong_total"], "hard_negatives": abp["hard_negatives"],
                    "max_inliers_on_a_wrong_edge": abp["max_inliers_on_a_wrong_edge"]},
        "not_claimed": EXP021_NOT_CLAIMED,
    }
