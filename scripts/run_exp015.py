"""EXP-015 — criterion 4 restated under the validated metric, as Part 1 froze it.

Pure re-analysis of recorded artefacts. No re-match, no re-fit, no new byte.

The calibration routine is IMPORTED from ``run_exp014`` rather than
reimplemented, and S0 requires it to reproduce that stage's recorded crossing
on the incumbent metric before anything else is reported -- otherwise this
stage would be free to produce a different answer with a different instrument
and call it a correction.

    python scripts/run_exp015.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from run_exp014 import bootstrap_threshold, crossing_threshold  # noqa: E402

EXPERIMENTS = ROOT / "experiments"
OUT = EXPERIMENTS / "EXP-015"
EXP012 = EXPERIMENTS / "EXP-012" / "exp012_results.json"
EXP014 = EXPERIMENTS / "EXP-014" / "exp014_results.json"

#: Part 1 section 3. Inherited from EXP-014, frozen there; not re-opened.
ERROR_BOUND_PX = 1.0
S3_PERCENTILE = 95
#: Part 1 section 4, S0.
EXP014_RECORDED_CROSSING = 0.6113534312076709
S0_TOL = 1e-9
#: Part 1 section 4, S4.
S4_MIN_REJECT_FRACTION = 0.10
S4_SATURATION = 0.99
#: Part 1 section 4, S5 -- EXP-014's sampled occupancy range.
INCUMBENT_WARN = 0.15


def crossing_from_above(occ, err, bound, pct, n_bins=24):
    """Lowest occupancy ABOVE which the pct-th percentile of err stays under bound.

    Occupancy is more-is-better, so the criterion is a floor. Reuses
    ``crossing_threshold`` on the NEGATED metric, which turns "higher is
    better" into the "higher is worse" orientation that routine expects -- the
    same instrument, not a second one.
    """
    cross, bins = crossing_threshold([-x for x in occ], err, bound, pct, n_bins=n_bins)
    for b in bins:
        for k in ("gap_lo", "gap_hi", "gap_mid"):
            b[k] = -b[k]
        b["gap_lo"], b["gap_hi"] = b["gap_hi"], b["gap_lo"]
    bins.reverse()
    return (None if cross is None else -cross), bins


def main() -> None:
    out_path = OUT / "exp015_results.json"
    if out_path.exists():
        raise SystemExit(f"{out_path.relative_to(ROOT)} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    e14 = json.loads(EXP014.read_text(encoding="utf-8"))
    real = [r for r in e14["rows"] if r["arm"] == "real"]
    err = [r["p99_err_px"] for r in real]

    # -- S0: the instrument control ---------------------------------------
    repro, _ = crossing_threshold([r["max_uncovered_disc_ratio"] for r in real],
                                  err, ERROR_BOUND_PX, S3_PERCENTILE)
    s0 = {"criterion": "S0",
          "statement": "crossing_threshold, imported from run_exp014, reproduces that "
                       "stage's recorded incumbent crossing to 1e-9",
          "met": repro is not None and abs(repro - EXP014_RECORDED_CROSSING) <= S0_TOL,
          "recorded": EXP014_RECORDED_CROSSING, "recomputed": repro,
          "tolerance": S0_TOL}
    if not s0["met"]:
        raise SystemExit(
            f"S0 FAILED: recomputed {repro} vs recorded {EXP014_RECORDED_CROSSING}. "
            "The calibration is not the same instrument; nothing is reported.")

    # -- S1: calibrate the floor on the validated metric -------------------
    occ = [r["grid_occupancy"] for r in real]
    T, bins = crossing_from_above(occ, err, ERROR_BOUND_PX, S3_PERCENTILE)
    lo, hi, nboot = (None, None, 0)
    if T is not None:
        lo_n, hi_n, nboot = bootstrap_threshold([-x for x in occ], err,
                                                ERROR_BOUND_PX, S3_PERCENTILE)
        lo, hi = (None if hi_n is None else -hi_n), (None if lo_n is None else -lo_n)
    s1 = {"criterion": "S1",
          "statement": f"the grid_occupancy floor T at which the {S3_PERCENTILE}th "
                       f"percentile of p99 local error crosses {ERROR_BOUND_PX} px",
          "met": T is not None, "T": T, "bootstrap_ci95": [lo, hi],
          "bootstrap_n": nboot,
          "sampled_range": [float(min(occ)), float(max(occ))],
          "bins": bins}

    # -- the 39 VERIFIED edges --------------------------------------------
    e12 = json.loads(EXP012.read_text(encoding="utf-8"))
    edges = []
    for t in e12["triplets"]:
        for v in t.get("verdicts", []):
            vd = v.get("verdict") or {}
            if vd.get("status") != "VERIFIED":
                continue
            m = vd.get("metrics") or {}
            edges.append({
                "edge": v.get("edge"), "window": t.get("window"),
                "confidence": vd.get("confidence"),
                "occupancy": m.get("coverage_occupancy"),
                "gap": m.get("coverage_max_gap"),
                "n_inliers": m.get("n_inliers")})
    missing = [e for e in edges if e["occupancy"] is None]
    if missing:
        raise SystemExit(f"{len(missing)} VERIFIED edges carry no coverage_occupancy; "
                         "reported as CANNOT CHECK rather than assumed")

    occ39 = [e["occupancy"] for e in edges]
    gap39 = [e["gap"] for e in edges]
    passes = [e for e in edges if T is not None and e["occupancy"] >= T]
    s2 = {"criterion": "S2",
          "statement": "criterion 4' (grid_occupancy >= T) on every VERIFIED edge",
          "met": T is not None and len(passes) == len(edges),
          "n_edges": len(edges), "n_pass": len(passes),
          "n_fail": len(edges) - len(passes),
          "occupancy_min": float(min(occ39)), "occupancy_max": float(max(occ39)),
          "occupancy_median": float(np.median(occ39)),
          "note": "MET here means the 39 pass 4'. It does NOT mean criterion 4 is "
                  "met -- see S3 and S4 (Part 1 section 4)."}

    n_over_incumbent = sum(1 for g in gap39 if g > INCUMBENT_WARN)
    s3 = {"criterion": "S3",
          "statement": "the ORIGINAL criterion 4 verdict stays recorded beside 4'",
          "met": True,
          "original_criterion": "coverage gap <= 0.15 on every VERIFIED pair",
          "original_verdict": "NOT MET",
          "original_n_over": n_over_incumbent, "original_n": len(edges),
          "original_gap_min": float(min(gap39)), "original_gap_max": float(max(gap39))}

    # -- S4: the anti-vacuity criterion ------------------------------------
    rejected = sum(1 for o in occ if T is not None and o < T)
    reject_frac = rejected / len(occ) if occ else 0.0
    n_unsaturated = sum(1 for o in occ39 if o < S4_SATURATION)
    s4 = {"criterion": "S4",
          "statement": f"T rejects >= {S4_MIN_REJECT_FRACTION:.0%} of EXP-014's 501 real "
                       f"subsets AND at least one VERIFIED edge sits below "
                       f"{S4_SATURATION} occupancy",
          "met": bool(reject_frac >= S4_MIN_REJECT_FRACTION and n_unsaturated >= 1),
          "calibration_reject_fraction": reject_frac,
          "calibration_rejected": rejected, "calibration_n": len(occ),
          "n_edges_below_saturation": n_unsaturated,
          "saturation_level": S4_SATURATION,
          "note": "if NOT MET, 4' is vacuous at real inlier counts, S2's verdict "
                  "carries no evidential weight, and it may not be quoted as passing "
                  "criterion 4 without 'vacuous at real inlier counts' in the same "
                  "sentence (Part 1 section 5)."}

    lo_s, hi_s = s1["sampled_range"]
    outside = [e for e in edges if not (lo_s <= e["occupancy"] <= hi_s)]
    s5 = {"criterion": "S5",
          "statement": "how many VERIFIED edges lie outside EXP-014's sampled "
                       "occupancy range, and are therefore judged by extrapolation",
          "met": True,
          "sampled_range": [lo_s, hi_s],
          "n_outside": len(outside), "n_total": len(edges),
          "fraction_outside": len(outside) / len(edges) if edges else 0.0}

    verdict_sentence = (
        "Criterion 4' is MET on the 39 edges, and the result is VACUOUS: "
        f"the calibrated floor rejects {reject_frac:.1%} of the calibration "
        f"population and {len(edges) - n_unsaturated} of {len(edges)} edges are "
        "saturated, so the criterion cannot discriminate where it is applied."
        if (s2["met"] and not s4["met"]) else
        "Criterion 4' is MET and discriminating." if (s2["met"] and s4["met"]) else
        f"Criterion 4' is NOT MET: {s2['n_fail']} of {s2['n_edges']} edges fall "
        "below the calibrated floor.")

    doc = {
        "stage": "EXP-015", "part": 2,
        "preregistration": "docs/stages/EXP-015_criterion4_restated.md",
        "what": "restate §53 criterion 4 under the metric that survived EXP-014's "
                "validation, with a threshold calibrated the same way, and re-measure",
        "inputs": ["experiments/EXP-012/exp012_results.json",
                   "experiments/EXP-014/exp014_results.json"],
        "computation": "pure re-analysis of recorded artefacts; no re-match, no "
                       "re-fit, no new byte",
        "frozen_constants": {
            "error_bound_px": ERROR_BOUND_PX, "percentile": S3_PERCENTILE,
            "s4_min_reject_fraction": S4_MIN_REJECT_FRACTION,
            "s4_saturation": S4_SATURATION,
            "note": "inherited from EXP-014 / EXP-015 Part 1; not tuned here"},
        "headline": verdict_sentence,
        "criteria": {c["criterion"]: c for c in (s0, s1, s2, s3, s4, s5)},
        "verified_edges": edges,
        "claims_not_supported": [
            "NOT an accuracy claim: every error figure is inherited from EXP-014's "
            "self-warps, which bound precision rather than accuracy (EXP-010 S1).",
            "NOT a verdict change: assess() and COVERAGE_GAP_WARN are untouched.",
            "NOT an adoption of criterion 4' into §53: this stage supplies the "
            "measurement for that decision, it does not take it.",
            "NOT a Chandrayaan-2 result.",
        ],
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
        "total_runtime_s": round(time.time() - t0, 2),
    }
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    print(f"S0 instrument control: recomputed {repro!r} vs recorded "
          f"{EXP014_RECORDED_CROSSING!r} -- MET\n")
    print(f"calibrated occupancy floor T = {T}   CI95 [{lo}, {hi}]")
    print(f"EXP-014 sampled occupancy {lo_s:.3f} .. {hi_s:.3f}")
    print(f"\n39 VERIFIED edges: occupancy {min(occ39):.4f} .. {max(occ39):.4f} "
          f"(median {np.median(occ39):.4f})")
    print(f"  pass 4': {len(passes)}/{len(edges)}   below saturation "
          f"({S4_SATURATION}): {n_unsaturated}   outside sampled range: {len(outside)}")
    print(f"  original criterion (gap <= 0.15): {n_over_incumbent}/{len(edges)} OVER "
          f"-> NOT MET")
    print(f"\ncalibration floor rejects {rejected}/{len(occ)} = {reject_frac:.1%} "
          f"of EXP-014's real subsets")
    print()
    for c in (s0, s1, s2, s3, s4, s5):
        print(f"  {c['criterion']}: {'MET' if c['met'] else 'NOT MET'} -- {c['statement']}")
    print(f"\n>>> {verdict_sentence}")
    print(f"\nwrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
