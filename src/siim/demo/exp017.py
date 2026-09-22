"""Viewpoint evidence for the demo (EXP-017).

The problem statement names three variations — illumination, viewpoint, scale —
and until this stage the page could show evidence for one of them. This panel
exists to show the second, and to show it in the shape the result actually
came out in, which is not the shape the stage expected:

* the failure the stage was designed around **does not happen** on this terrain
  (no window's dense median error reaches 0.5 px anywhere in the sweep), so two
  criteria are **undefined rather than refuted**;
* what does fail is **§2.2's own wording** — *residuals white* — at every
  emission angle above zero, because a residual that is small is still smooth;
* and the verdict **rejects nothing at any angle**, which is a blind spot and
  belongs on the page beside the number that looks good.

Every number here is an upper bound on **precision**: the oblique image is the
nadir image's own photons displaced by a DEM, so there is no radiometric
difference and no occlusion in it.
"""

from __future__ import annotations

from typing import Any

from .evidence import EXPERIMENTS, ROOT, DemoDataMissing, _read

__all__ = ["exp017_evidence", "exp017_status", "EXP017_SOURCES"]

EXP017_ARTEFACT = EXPERIMENTS / "EXP-017" / "exp017_results.json"

EXP017_SOURCES = ["experiments/EXP-017/exp017_results.json"]

EXP017_SUMMARY = (
    "A real 10 m Chandrayaan-2 DTM co-registered by construction with a real "
    "5 m orthoimage, from which an oblique view is built with exact ground "
    "truth, swept from 0 to 30 degrees of emission. The global 2-D model's "
    "dense median error never reaches 0.5 px in that sweep, because after a "
    "global affine absorbs the plane the residual relief is only 2.85-8.93 m "
    "RMS. What fails instead is the problem statement's literal acceptance -- "
    "residuals white -- which holds at 0 degrees and nowhere else, on both "
    "local arms, at residual amplitudes as small as 0.032 px."
)

EXP017_SCOPE = (
    "Synthetic viewpoint on real terrain: one TMC-2 strip over Mare "
    "Serenitatis, 15 arm-A windows of which 13 are reported (two excluded by "
    "S0's own control), plus 10 NAC tiles under the 59 m SLDEM and 6 synthetic "
    "fields. Engine B1, affine RANSAC at 3 px, seed 0. Emission 0-30 degrees, "
    "one azimuth."
)

EXP017_NOT_CLAIMED = [
    "NOT a real off-nadir result. The oblique image is the nadir image's own "
    "photons displaced by a DEM: identical texture, identical illumination, "
    "identical interpolation kernel. Every error is an upper bound on "
    "PRECISION, and a real fore/aft pair would differ from this construction "
    "by about 1.9 px RMS at 25 degrees from the DTM's own 20.9 m height error "
    "alone.",
    "NOT occlusion, view-dependent radiometry or a sensor model. A real "
    "oblique image has all three; this construction has none.",
    "NOT independent of the DTM. The ground truth is exact relative to a DEM "
    "whose own stated height RMSE is 20.9 m.",
    "NOT a Chandrayaan-2 fore/aft, OHRC or slewed-NAC result: one mare region, "
    "one strip, one engine, one azimuth.",
    "NOT a claim that the problem statement's acceptance is wrong -- only that "
    "its literal form is unattainable above 0 degrees with these instruments "
    "on this terrain, which is a measurement about the acceptance.",
    "NOT a verdict change. The verdict returns INCONCLUSIVE at every angle and "
    "rejects nothing; that is recorded as a blind spot, not patched.",
]


def exp017_status() -> dict[str, Any]:
    missing = [] if EXP017_ARTEFACT.exists() else [
        str(EXP017_ARTEFACT.relative_to(ROOT)).replace("\\", "/")]
    return {"available": not missing, "missing": missing}


def exp017_evidence() -> dict[str, Any]:
    """EXP-017, assembled for the page. Raises if the artefact is absent."""
    status = exp017_status()
    if not status["available"]:
        raise DemoDataMissing("viewpoint panel: missing " + ", ".join(status["missing"]))

    doc = _read(EXP017_ARTEFACT, "EXP-017 results",
                require=("criteria", "rows", "windows"))
    crit = doc["criteria"]
    s0, s1, s2, s4, s5 = crit["S0"], crit["S1"], crit["S2"], crit["S4"], crit["S5"]
    good = set(s0["windows_reported"])
    rows = [r for r in doc["rows"] if r["arm"] == "A" and r["window"] in good]
    meta = doc["windows"]

    sweep = sorted({r["e_deg"] for r in rows})

    def _median(vals):
        v = sorted(x for x in vals if x is not None)
        if not v:
            return None
        n = len(v)
        return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])

    by_e = []
    for e in sweep:
        rs = [r for r in rows if r["e_deg"] == e]
        arm = {}
        for key in ("G", "L1", "L2"):
            arm[key] = {
                "median": _median([(r.get(key) or {}).get("err", {}).get("median") for r in rs]),
                "p99": _median([(r.get(key) or {}).get("err", {}).get("p99") for r in rs]),
            }
        by_e.append({
            "e_deg": e, "n_windows": len(rs), **arm,
            "n_inliers_median": _median([r["n_inliers"] for r in rs]),
            "status": sorted({r["status"] for r in rs}),
            "pass_all": all(r["pass"] for r in rs),
            "models": sorted({r["model"] for r in rs}),
            "literal_ok_L1": (s1["L1"]["per_e"].get(str(e)) or {}).get("literal_ok"),
            "bound_ok_L1": (s1["L1"]["per_e"].get(str(e)) or {}).get("bound_ok"),
            "literal_ok_L2": (s1["L2"]["per_e"].get(str(e)) or {}).get("literal_ok"),
            "bound_ok_L2": (s1["L2"]["per_e"].get(str(e)) or {}).get("bound_ok"),
        })

    windows = []
    for w, v in sorted((s2.get("per_window") or {}).items()):
        m = meta.get(w, {})
        windows.append({
            "window": w,
            "relief_ptp_m": m.get("relief_ptp_m", m.get("p5_dem_height_ptp_m")),
            "relief_res_rms_m": m.get("relief_res_rms_m"),
            "e_star_med": v.get("e_star_med"),
            "e_star_p99": v.get("e_star_p99"),
            "sec20_ptp_predicts": v.get("e_sec20_ptp_0.5px"),
            "P_rms_at_30": v.get("P_rms_at_30"),
            "G_median_at_30": (v.get("G_median_by_e") or {}).get("30"),
        })

    return {
        "construction": {
            "what": ("an oblique view built from a real 10 m TMC-2 DTM on a real "
                     "5 m ortho, with exact ground truth by construction"),
            "why_not_real": ("every real frame on disk is near-nadir (emission "
                             "1.17-1.77 deg) and PRADAN delivered only TMC-2's "
                             "nadir band, so no real off-nadir pair exists here"),
            "bound_on": "precision, not accuracy",
        },
        "criteria": {
            "S0": {"met": bool(s0["met"]), "n_windows": s0["n_windows"],
                   "reported": len(good), "failed": s0["windows_failed"],
                   "why": "the circular L3 control exceeds its 0.05 px tolerance "
                          "at e = 25-30 on those two windows (E-054)"},
            "S1a": {"met": bool(s1["L1"]["s1a_met"]),
                    "envelope_L1": s1["L1"]["largest_e_literal"],
                    "envelope_L2": s1["L2"]["largest_e_literal"]},
            "S1b": {"met": bool(s1["L1"]["s1b_met"]),
                    "envelope_L1": s1["L1"]["largest_e_bound"],
                    "envelope_L2": s1["L2"]["largest_e_bound"]},
            "S2": {"met": bool(s2["met"]), "n_with_onset": s2["n_with_onset_med"],
                   "never_rejected": bool(s2["never_rejected"]),
                   "pass_at_every_e": bool(s2["pass_at_every_e"])},
            "S3": {"met": bool(crit["S3"]["met"]),
                   "n_cells_at_or_above_onset": crit["S3"]["n_cells_at_or_above_onset"],
                   "undefined": crit["S3"]["n_cells_at_or_above_onset"] == 0},
            "S4": {"met": bool(s4["met"]), "rho_dof": s4["s4a"]["rho"],
                   "p_dof": s4["s4a"]["p"], "rho_heldout": s4["s4b"]["rho"],
                   "p_heldout": s4["s4b"]["p"], "n": s4["s4a"]["n"],
                   "model_by_e": s4["model_by_e"],
                   "tie_break_rho": s4["tie_break_spearman_vs_e"]},
            "S5": {"met": bool(s5["met"]), "undefined": s5["arm_A_gmean_P_rms_onset"] is None,
                   "arm_B_max_P_rms_at_30": s5["arm_B_max_P_rms_at_30"]},
        },
        "by_e": by_e,
        "windows": windows,
        "nulls": {"shift_null_fires_at_e0": s0["v_null_calibration"]["shift_null_fires_at_e0"],
                  "pixel_perm_fires_at_e0": s0["v_null_calibration"]["pixel_perm_fires_at_e0"],
                  "max_allowed": s0["v_null_calibration"]["max_allowed"],
                  "met": bool(s0["v_null_calibration"]["met"]),
                  "why": ("a pixel permutation destroys the relief field's own spatial "
                          "correlation, so it is an anti-conservative null and fires on "
                          "most windows with nothing applied; the criterion uses the "
                          "shift null, which preserves it")},
        "blind_spot": {
            "never_rejected": bool(s2["never_rejected"]),
            "pass_at_every_e": bool(s2["pass_at_every_e"]),
            "p99_at_30": next((b["G"]["p99"] for b in by_e if b["e_deg"] == 30), None),
            "what": ("nothing in the shipped verdict is sensitive to emission angle; "
                     "the one signal that is -- the held-out residual, rho = 0.949 -- "
                     "is computed and not used to reject"),
        },
        "summary": EXP017_SUMMARY,
        "scope": EXP017_SCOPE,
        "not_claimed": list(EXP017_NOT_CLAIMED),
        "sources": list(EXP017_SOURCES),
    }
