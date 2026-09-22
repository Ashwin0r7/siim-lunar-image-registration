"""Multi-modality evidence for the demo (EXP-020).

The problem statement is titled for multi-modal registration and, until this
stage, the project's entire evidence for that word was **one measured
negative**: REAL-DATA-08's radar, 0 of 48. No IIRS product was ever delivered
(RL-046), so the axis was data-REFUSED rather than untested, and no amount of
software could change that.

EXP-020 asks the question §2.2 asks of IIRS with the closest public instrument
of the same kind — nine Kaguya MI reflectance bands, on the same map frame and
the same photometric standard geometry as the panchromatic reference, so that
only wavelength and GSD vary — and answers the thermal half with a real thermal
instrument.

The panel must carry three things a summary would drop: that this is **not**
IIRS; that the clause §2.2 actually asks for (*same envelope as pan*) is met
while the stage's own absolute bound is not; and that the reason the bound
fails is an **85 m offset between two products of the same mission**, which the
same run measured.
"""

from __future__ import annotations

import json
from typing import Any

from .evidence import EXPERIMENTS, ROOT, DemoDataMissing, _read

__all__ = ["exp020_evidence", "exp020_status", "EXP020_SOURCES"]

EXP020_ARTEFACT = EXPERIMENTS / "EXP-020" / "exp020_results.json"
ARMN_B1 = EXPERIMENTS / "EXP-020" / "exp020_armN_cropped.json"
ARMN_B4L = EXPERIMENTS / "EXP-020" / "exp020_armN_cropped_b4l.json"

EXP020_SOURCES = [
    "experiments/EXP-020/exp020_results.json",
    "experiments/EXP-020/exp020_armN_cropped.json",
    "experiments/EXP-020/exp020_armN_cropped_b4l.json",
    "data/manifests/exp020_kaguya_mi_block.json",
    "data/manifests/exp020_diviner_tbol_day_block.json",
]

#: The wrong-pass bound for the supplementary arm: a pass whose error is far
#: beyond the inter-product term cannot be a correct registration. Stated here
#: rather than inside a loop so the page and the report use one number.
WRONG_PASS_M = 500.0

EXP020_SUMMARY = (
    "Nine reflectance bands of a multispectral imager against a panchromatic "
    "image of the same ground, on one map frame and one photometric standard "
    "geometry, so that only wavelength and resolution vary. Seven of nine "
    "register under the frozen rule, and every one of the seven lands within "
    "1.334x of a pan comparator built from the same instrument's own band mean "
    "-- six of them better than pan. Two bands also register to the "
    "Chandrayaan-2 TMC-2 ortho. A thermal map at 28:1 does not register at "
    "all, by measured starvation. And the absolute bar fails for a reason that "
    "has nothing to do with colour: the two Kaguya products underneath this "
    "comparison are offset from each other by about 85 m."
)

EXP020_SCOPE = (
    "One mare window (Mare Serenitatis), nine Kaguya MI MAP V3 bands at 14.8 m "
    "against the SELENE TC ortho at 8.42 m, the Chandrayaan-2 TMC-2 P1 block, "
    "the LRO NAC frames EXP-019 placed, and one Diviner GDR L3 day cycle at "
    "236.9 m. Engine B1 in every criterion; B4L beside. Errors are measured "
    "against the analytic map between each pair of product labels, which is "
    "exact only to the extent those products are georeferenced relative to "
    "each other."
)

EXP020_NOT_CLAIMED = [
    "NOT an IIRS result. No IIRS product exists in this repository: PRADAN "
    "delivered TMC-2 and OHRC and no IIRS at all. Kaguya MI is 414-1548 nm at "
    "14.8 m; IIRS is 800-5000 nm at 80 m. The substitution is stated, not "
    "smuggled.",
    "NOT accuracy. Every number is a disagreement against a label map, and the "
    "two products' relative georeferencing -- which that map assumes -- is "
    "measured here at about 85 m. No figure in this panel is better than that "
    "floor.",
    "NOT a thermal-imaging result. Diviner tbol is a gridded derived product "
    "at 236.9 m, not an image from a thermal camera.",
    "NOT an illumination result. MI and the TC reference share a standard "
    "geometry by construction, so nothing here varies the Sun.",
    "NOT a cross-mission claim for the classical engine: MI against LRO NAC is "
    "0 of 36 under RootSIFT, and it is the learned engine that reaches it.",
    "NOT a verdict change. assess(), select_model and every constant are "
    "untouched.",
]


def exp020_status() -> dict[str, Any]:
    missing = [str(p.relative_to(ROOT)).replace("\\", "/")
               for p in (EXP020_ARTEFACT, ARMN_B1, ARMN_B4L) if not p.exists()]
    return {"available": not missing, "missing": missing}


def _met(crit: dict, name: str) -> bool:
    return bool((crit.get(name) or {}).get("met"))


def exp020_evidence() -> dict[str, Any]:
    """EXP-020, assembled for the page. Raises if an artefact is absent."""
    status = exp020_status()
    if not status["available"]:
        raise DemoDataMissing(
            "multi-modality panel: missing " + ", ".join(status["missing"]))

    doc = _read(EXP020_ARTEFACT, "EXP-020 results",
                require=("criteria", "cells", "arm_C", "arm_T", "null_cells"))
    b1 = _read(ARMN_B1, "EXP-020 arm N (B1, cropped)", require=("rows", "n_pass"))
    b4l = _read(ARMN_B4L, "EXP-020 arm N (B4L, cropped)", require=("rows", "n_pass"))
    crit = doc["criteria"]
    s1, s2, s3, s5, s6 = crit["S1"], crit["S2"], crit["S3"], crit["S5"], crit["S6"]

    # --- S2 read as Part 1 froze it (E-053) --------------------------------
    n_succeed = int(s1.get("n_pass") or 0)
    ratios = s2.get("ratios") or []
    worst = max((r["ratio"] for r in ratios), default=None)
    s2_as_frozen = bool(n_succeed >= 7 and s2.get("pan_pass") and worst is not None
                        and worst <= 2.0)

    bands = [{"wavelength_nm": b["wavelength_nm"], "n_inliers": b["n_inliers"],
              "pass": bool(b["pass"]), "err_median_m": b["err_median_m"],
              "err_median_ref_px": b["err_median_ref_px"], "contrast": b["contrast"],
              "n_keypoints": b["n_keypoints_src"],
              "ratio_to_pan": next((r["ratio"] for r in ratios
                                    if r["wavelength_nm"] == b["wavelength_nm"]), None),
              "vs_pan_m": next((c.get("vs_pan_median_m") for c in doc["cells"]
                                if c.get("arm") == "B"
                                and c.get("wavelength_nm") == b["wavelength_nm"]), None)}
             for b in s1["per_band"]]

    pan = next((c for c in doc["cells"] if c.get("arm") == "P"), {})
    second = doc.get("second_engine") or []
    b4l_pan = next((c for c in second if c.get("wavelength_nm") is None), {})
    inter_product = {
        "estimate_m": [min((c["err_median_m"] for c in second
                            if c.get("pass") and c.get("err_median_m") is not None),
                           default=None),
                       max((c["err_median_m"] for c in second
                            if c.get("pass") and c.get("err_median_m") is not None),
                           default=None)],
        "b4l_inliers": [min((c["n_inliers"] for c in second if c.get("pass")), default=None),
                        max((c["n_inliers"] for c in second if c.get("pass")), default=None)],
        "b1_pan_m": pan.get("err_median_m"), "b1_pan_inliers": pan.get("n_inliers"),
        "b4l_pan_m": b4l_pan.get("err_median_m"), "b4l_pan_inliers": b4l_pan.get("n_inliers"),
        "linear_part_agreement": "3e-5",
        "what": ("MI MAP V3 and TC Ortho Map Seamless V2 -- two products of one "
                 "mission, one map frame, one control network -- are offset from "
                 "each other by a near-pure translation of about 85 m"),
    }

    chandrayaan2 = [{"wavelength_nm": c["wavelength_nm"], "n_inliers": c["n_inliers"],
                     "pass": bool(c.get("pass")), "err_median_m": c.get("err_median_m")}
                    for c in doc["arm_C"]]

    t = doc["arm_T"]
    thermal = {"met": _met(crit, "S5"), "ratio": s5.get("ratio"),
               "n_inliers": s5.get("n_inliers"),
               "n_keypoints_thermal": s5.get("n_keypoints_thermal"),
               "n_keypoints_pan": s5.get("n_keypoints_pan"),
               "thermal_px": s5.get("thermal_px"), "pan_px": s5.get("pan_px"),
               "failure_mode": s5.get("failure_mode"), "bar_m": s5.get("bar_m"),
               "valid_fraction": t.get("src_valid_fraction"),
               "envelope": ("on this mare window a Diviner bolometric-temperature "
                            "map does not register to panchromatic at 28:1, and the "
                            "recorded keypoint counts say why: the thermal side "
                            f"yields {s5.get('n_keypoints_thermal')} keypoints")}

    def _armn(d: dict) -> dict:
        rows = [r for r in d["rows"] if "n_inliers" in r]
        ok = [r for r in rows if r.get("pass")]
        right = [r for r in ok if (r.get("err_median_m") or 9e9) < WRONG_PASS_M]
        wrong = [r for r in ok if (r.get("err_median_m") or 9e9) >= WRONG_PASS_M]
        return {"engine": d.get("engine", "B1"), "n_cells": len(rows), "n_pass": len(ok),
                "n_right": len(right), "n_wrong_pass": len(wrong),
                "err_range_m": [min((r["err_median_m"] for r in right), default=None),
                                max((r["err_median_m"] for r in right), default=None)],
                "max_inliers": max((r["n_inliers"] for r in rows), default=0),
                "overlap_fraction_uncropped": (rows[0].get("overlap_fraction_uncropped")
                                               if rows else None)}

    return {
        "substitution": {
            "why": ("no IIRS product was delivered by PRADAN (RL-046), so the "
                    "axis is data-REFUSED, not untested"),
            "instrument": "Kaguya MI MAP V3, nine bands 414-1548 nm at 14.8 m",
            "iirs": "800-5000 nm at 80 m",
            "held_fixed": ("same map frame and same photometric standard geometry "
                           "(i = 30 deg, e = 0, alpha = 30 deg) as the TC pan reference, "
                           "so only wavelength and GSD vary"),
        },
        "criteria": {k: {"met": _met(crit, k)} for k in
                     ("S0", "S1", "S2", "S3", "S4", "S5", "S6")},
        "s2_as_frozen": {"met": s2_as_frozen, "n_succeed": n_succeed,
                         "worst_ratio": worst, "worst_band_nm": s2.get("worst_band_nm"),
                         "bar": 2.0, "pan_pass": bool(s2.get("pan_pass")),
                         "note": ("the artefact's own S2 field says NOT MET because the "
                                  "runner counted bands within S1's metre bound instead "
                                  "of bands that succeeded -- E-053; the artefact is not "
                                  "rewritten and the criterion is read as frozen")},
        "s1": {"met": _met(crit, "S1"), "n_pass": n_succeed, "n_bands": s1.get("n_bands"),
               "n_within_bound": s1.get("n_within_bound"),
               "median_err_m": s1.get("median_err_m"), "bar_m": 8.42315289562},
        "bands": bands,
        "pan_comparator": {"n_inliers": pan.get("n_inliers"),
                           "err_median_m": pan.get("err_median_m"),
                           "contrast": pan.get("contrast")},
        "inter_product_offset": inter_product,
        "chandrayaan2": {"met": _met(crit, "S3"), "bar_m": s3.get("bar_m"),
                         "n_pass": s3.get("n_pass"), "per_band": chandrayaan2},
        "thermal": thermal,
        "cross_mission": {"frozen_arm_n_pass": (crit["S4"].get("n_cells") or 0) and 0,
                          "frozen_arm_cells": crit["S4"].get("n_cells"),
                          "cropped_b1": _armn(b1), "cropped_b4l": _armn(b4l),
                          "what_it_decides": ("framing is not the cause and direction is "
                                              "not the cause; the matcher is")},
        "null": {"met": _met(crit, "S6"), "n_cells": s6.get("n_cells"),
                 "n_pass": s6.get("n_pass"),
                 "false_accept_fraction": s6.get("false_accept_fraction")},
        "summary": EXP020_SUMMARY,
        "scope": EXP020_SCOPE,
        "not_claimed": list(EXP020_NOT_CLAIMED),
        "sources": list(EXP020_SOURCES),
    }
