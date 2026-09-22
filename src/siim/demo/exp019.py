"""The controlled-reference evidence for the demo (EXP-019).

This panel exists because of a sentence the project carried for three weeks:
*"corroborated, not verified — and the corroboration resolves only to ~100 px."*

Every real result was checked against the archive's own corner geometry, which
discriminates at 84–116 px, and three separate findings were limited by that
one fact: there was no accuracy number (0.003 px is a self-warp, an upper bound
on precision), EXP-013's detector calibrated at 66.00 px of reference noise and
could not be deployed, and its H3 — *is a per-frame term the archive's error or
the estimate's?* — was undecidable by construction.

EXP-019 brought in a product from another agency, spacecraft, sensor, decade
and control network (SELENE/Kaguya TC ortho, 8.42 m) and measured all three.
The panel shows what changed and, just as prominently, the criterion that did
not pass: the Chandrayaan-2 triangle closes at 2.177 reference px against a
frozen 2.0 and the line was not moved.

A separate module for the reason :mod:`siim.demo.exp013` gives: the recorded
demo paths import :mod:`siim.demo.evidence`, and this project's rule is to add
a module rather than edit one those artefacts depend on.
"""

from __future__ import annotations

from typing import Any

from .evidence import EXPERIMENTS, ROOT, DemoDataMissing, _read

__all__ = ["exp019_evidence", "exp019_status", "EXP019_SOURCES"]

EXP019_ARTEFACT = EXPERIMENTS / "EXP-019" / "exp019_results.json"
EXP013_ARTEFACT = EXPERIMENTS / "EXP-013" / "exp013_results.json"

EXP019_SOURCES = [
    "experiments/EXP-019/exp019_results.json",
    "experiments/EXP-013/exp013_results.json",
    "data/manifests/exp019_tc_ortho_ref_block.json",
    "data/manifests/exp019_tc_ortho_null_block.json",
]

EXP019_SUMMARY = (
    "Every real number in this project used to be checked against the archive "
    "that produced the images. This panel is what happened when a product from "
    "another mission was asked the same questions: 12 of 20 LRO NAC tiles and "
    "the Chandrayaan-2 TMC-2 block register to a SELENE (Kaguya) ortho across a "
    "6.5-10.5:1 sensor scale ratio; the archive and Kaguya's control network "
    "disagree by 137.6 m; and an A -> reference -> B composition built from no "
    "A-to-B correspondence agrees with the recorded direct registration to "
    "0.266 reference pixels (2.24 m). That last number is the project's first "
    "accuracy-class figure that is not a self-warp."
)

EXP019_SCOPE = (
    "One mare window (Mare Serenitatis, lat 19.52-20.24 N, lon 21.88-22.17 E), "
    "20 NAC tiles and one Chandrayaan-2 TMC-2 block, engine B1 in every "
    "criterion, one reference product. Sources are near-nadir and unrectified; "
    "the reference is orthorectified and photometrically normalised to "
    "i = 30 deg, so |i - 30| is the illumination variable, not a pair's "
    "Delta-incidence."
)

EXP019_NOT_CLAIMED = [
    "NOT ground truth. A second product is a second opinion with its own "
    "control network and its own errors; every number here is a disagreement, "
    "which bounds the sum of two errors and attributes it to neither.",
    "NOT absolute accuracy in the SELENE frame. Both legs of the composed "
    "check share one reference block, so that block's own georeferencing error "
    "is common-mode and cancels. The 2.24 m bounds the direct estimate's error "
    "relative to the reference path, not its error on the Moon.",
    "NOT manual check points. Every correspondence is machine-made; the "
    "independence claimed is of the instrument chain, not of a human "
    "annotator. Human-annotated check points remain unbuilt.",
    "NOT a VERIFIED Chandrayaan-2 verdict. The triangle through the "
    "independent mission closes at 2.177 reference px = 18.33 m against a "
    "frozen 2.0 reference px line. It is NOT MET and the line was not moved.",
    "NOT multi-modal. The reference is a panchromatic optical imager, like NAC "
    "and TMC-2.",
    "NOT a viewpoint or terrain-transfer result. One region, mare, near-nadir.",
    "NOT a verdict change. assess(), select_model and siim.verify.gauge are "
    "untouched; the 13 INCONCLUSIVE and 1 REJECTED verdicts are recorded as "
    "they came.",
]


def exp019_status() -> dict[str, Any]:
    missing = [str(p.relative_to(ROOT)).replace("\\", "/")
               for p in (EXP019_ARTEFACT, EXP013_ARTEFACT) if not p.exists()]
    return {"available": not missing, "missing": missing}


def _met(crit: dict, name: str) -> bool:
    return bool((crit.get(name) or {}).get("met"))


def exp019_evidence() -> dict[str, Any]:
    """EXP-019, assembled for the page. Raises if an artefact is absent."""
    status = exp019_status()
    if not status["available"]:
        raise DemoDataMissing(
            "controlled-reference panel: missing " + ", ".join(status["missing"]))

    doc = _read(EXP019_ARTEFACT, "EXP-019 results",
                require=("criteria", "cells", "frames", "null_cells"))
    crit = doc["criteria"]
    cells, frames = doc["cells"], doc["frames"]
    s1, s2, s3, s4, s5, s6 = (crit["S1"], crit["S2"], crit["S3"], crit["S4"],
                              crit["S5"], crit["S6"])

    # --- the accuracy statement, read from S3 ------------------------------
    accuracy = {
        "median_ref_px": s3.get("median_ref_px"),
        "median_m": s3.get("median_m"),
        "ci95_ref_px": s3.get("median_ci95_ref_px"),
        "bar_ref_px": s3.get("bar_ref_px"),
        "bar_m": s3.get("bar_m"),
        "n_pairs": s3.get("n_pairs"),
        "met": _met(crit, "S3"),
        "requirement": ("median < 0.5 coarser-image pixels on independent check "
                        "points, with a 95 % CI (MASTER_RESEARCH_AND_ARCHITECTURE"
                        "_PLAN.md section 2.2)"),
        "what_it_is": ("A -> reference -> B, composed from correspondences "
                       "A-to-reference and B-to-reference only, compared against "
                       "the recorded direct A -> B registration on an 8 px grid."),
        "what_it_is_not": ("absolute accuracy in the SELENE frame: the two legs "
                           "share one reference block, so its own error cancels"),
    }

    # --- the floor that used to be quoted as "~100 px" ---------------------
    floor = {
        "median_m": s2.get("median_m"),
        "ci95_m": s2.get("median_ci95_m"),
        "min_m": s2.get("min_m"), "max_m": s2.get("max_m"),
        "n_frames": s2.get("n_frames"),
        "note": ("the artefact's S2 field pools arm C, which Part 1 forbids "
                 "(E-051); the frozen reading is arm R alone, 137.61 m median "
                 "over 12 frames, CI95 108.5-160.3 m"),
        "frozen_reading_m": 137.61,
        "frozen_reading_ci95_m": [108.52, 160.32],
        "frozen_reading_n_frames": 12,
        "direction_east_m": 101.2, "direction_north_m": 36.4,
        "replaces": ("archive corner geometry, which discriminates at 84-116 px "
                     "and whose per-frame reference noise EXP-013 measured at "
                     "66.00 px"),
    }

    # --- per-frame registrations, from the cells ---------------------------
    registrations = []
    for key, cell in sorted(cells.items()):
        if cell.get("arm") != "R":
            continue
        f = frames.get(key, {})
        field = cell.get("displacement_field") or {}
        registrations.append({
            "source": key, "kind": cell.get("kind"),
            "incidence_deg": f.get("incidence_deg"),
            "delta_to_standard_geometry_deg": f.get("delta_to_standard_geometry_deg"),
            "k": f.get("k"), "coarse_gsd_m": f.get("coarse_gsd_m"),
            "n_inliers": cell.get("n_inliers"), "pass": bool(cell.get("pass")),
            "verdict": (cell.get("verdict") or {}).get("status"),
            "confidence": (cell.get("verdict") or {}).get("confidence"),
            "occupancy": cell.get("coverage_occupancy"),
            "archive_vs_controlled_m": field.get("rms_m"),
            "recovered_scale": cell.get("recovered_scale"),
            "predicted_scale": cell.get("predicted_scale"),
        })
    registrations.sort(key=lambda r: (not r["pass"],
                                      r["delta_to_standard_geometry_deg"] or 0.0))

    # --- EXP-013's question, decided ---------------------------------------
    rows = [r for r in (s4.get("rows") or []) if r.get("measured_px") is not None]
    attribution = {
        "met": _met(crit, "S4"),
        "criterion_read_on": s4.get("criterion_read_on"),
        "arm_R_only": s4.get("arm_R_only"),
        "pooled": s4.get("pooled"),
        "n_common_frames": s4.get("n_common_frames"),
        "question": ("siim.verify.gauge: 'A per-frame bias in the archive "
                     "reference has the same shape as a per-frame gauge in the "
                     "estimate and is indistinguishable by this instrument.'"),
        "answer": ("the terms are substantially reference error: they track the "
                   "archive-vs-controlled offsets measured against a product "
                   "EXP-013 never saw"),
        "per_frame": [{"window": r.get("window"), "frame": r.get("frame"),
                       "exp013_px": r.get("exp013_px"),
                       "measured_px": r.get("measured_px"),
                       "arm": r.get("arm"),
                       "is_fixed_node": bool(r.get("is_fixed_node"))} for r in rows],
    }

    # --- the criterion that did not pass -----------------------------------
    triangle = {
        "met": _met(crit, "S5"),
        "closure_ref_px": s5.get("closure_median_ref_px"),
        "closure_m": s5.get("closure_median_m"),
        "bar_ref_px": s5.get("bar_ref_px"), "bar_m": s5.get("bar_m"),
        "edges": s5.get("edges"),
        "note": s5.get("note"),
        "missed_by_pct": (None if not s5.get("closure_median_ref_px") else
                          100.0 * (s5["closure_median_ref_px"] / s5["bar_ref_px"] - 1.0)),
    }

    null = {"met": _met(crit, "S6"), "n_cells": s6.get("n_cells"),
            "n_pass": s6.get("n_pass"),
            "false_accept_fraction": s6.get("false_accept_fraction"),
            "what": ("every source re-registered against a block of the SAME "
                     "product 25 km away, which must fail")}

    envelope = [{"source": r["source"],
                 "delta_deg": r["delta_to_standard_geometry_deg"],
                 "n_inliers": r["n_inliers"], "pass": r["pass"]}
                for r in registrations if r["kind"] == "NAC"]

    second = doc.get("second_engine") or {}
    b4l = {"n_pass": sum(1 for c in second.values() if c.get("pass")),
           "n_cells": len(second),
           "b1_n_pass": sum(1 for c in cells.values()
                            if c.get("arm") == "R" and c.get("pass")),
           "note": ("DISK + LightGlue, run beside every cell and inside no "
                    "criterion; it rescues the 36-40 deg band and does not rescue "
                    "the 72-75 deg frames")}

    return {
        "reference": doc.get("reference"),
        "criteria": {k: {"met": _met(crit, k)} for k in
                     ("S0", "S1", "S2", "S3", "S4", "S5", "S6")},
        "accuracy": accuracy,
        "floor": floor,
        "attribution": attribution,
        "triangle": triangle,
        "null": null,
        "registrations": registrations,
        "envelope_vs_standard_geometry": envelope,
        "second_engine": b4l,
        "n_nac_pass": s1.get("n_nac_pass"), "n_nac": s1.get("n_nac"),
        "tmc2_pass": s1.get("tmc2_pass"),
        "summary": EXP019_SUMMARY,
        "scope": EXP019_SCOPE,
        "not_claimed": list(EXP019_NOT_CLAIMED),
        "sources": list(EXP019_SOURCES),
    }
