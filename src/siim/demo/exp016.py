"""Scale-ladder evidence for the demo (EXP-016).

The problem statement names scale variation "2:1 to 320:1" in so many words,
and for most of this project's life that axis had no evidence at all: the best
real number was a ~65:1 proxy and the synthetic probe stopped at 32:1 while
measuring the *unmodified* baseline rather than the architecture's own answer.

This panel shows the ladder as it actually came out, which is not how the
stage predicted it:

* the acceptance ("every rung <= 320:1 registers") is **NOT MET**, and the
  measured envelope is the deliverable's number;
* the reason is separated from the ratio by a control that holds the coarse
  pixel count fixed and halves the ratio (arm X), so "descriptor failure or
  sampling starvation" is answered with a measurement rather than a story;
* the architecture's own scale-normalisation step is put against not taking it
  (arm N), and the panel reports that comparison whichever way it fell -- the
  stage pre-registered that a loss here **supersedes D-005**;
* the error at the rungs that work is quoted in coarse pixels **and in
  metres**, because 0.5 coarse px is 16 m at 32:1 and 160 m at 320:1.

Every number is read from the recorded artefact; nothing here is recomputed.
"""

from __future__ import annotations

from typing import Any

from .evidence import EXPERIMENTS, ROOT, DemoDataMissing, _read

__all__ = ["exp016_evidence", "exp016_status", "EXP016_SOURCES"]

EXP016_ARTEFACT = EXPERIMENTS / "EXP-016" / "exp016_results.json"

EXP016_SOURCES = ["experiments/EXP-016/exp016_results.json"]

EXP016_SUMMARY = (
    "Real LRO NAC pairs the pipeline already registers at its native rung, "
    "degraded through a stated PSF to a common coarser GSD and matched there, "
    "up a ladder of 2 : 4 : 8 : 16 : 32 : 64 : 128 : 320. The problem "
    "statement's acceptance is that every rung up to 320:1 registers. It does "
    "not. The measured envelope is reported as the deliverable's number, and a "
    "control that holds the coarse pixel count fixed while halving the ratio "
    "says whether the ceiling belongs to the descriptor or to the pixels."
)

EXP016_SCOPE = (
    "Eleven real NAC edges that succeed at the native rung, inside the "
    "measured illumination envelope (delta incidence <= 15 deg), plus two long "
    "windows. One engine in every criterion (B1, affine RANSAC at 3 px, seed "
    "0); B4L reported beside. One mare region, near-nadir, one instrument "
    "family. The coarse image is a NAC frame through a Gaussian PSF, not "
    "another sensor."
)

EXP016_NOT_CLAIMED = [
    "NOT a cross-sensor result. The 'coarse sensor' is an LRO NAC frame put "
    "through a Gaussian PSF and a block mean. A real IIRS or TMC-2 pixel has "
    "its own MTF, its own radiometry and its own along-track smear; none of "
    "those are in this ladder.",
    "NOT accuracy. There is no ground truth here. Rung consistency is "
    "agreement with the same edge's native-rung solution -- a PRECISION-class "
    "statement -- and the archive-geometry check only corroborates, at a floor "
    "that is about 100 native px.",
    "NOT a 320:1 result for OHRC-to-IIRS. The largest window on this disk "
    "holds about 570 coarse pixels at 320:1; the real OHRC-in-IIRS case holds "
    "about 5 550. Which side of the measured pixel floor that number falls on "
    "is arithmetic, stated beside the ladder, not evidence from it.",
    "NOT illumination, viewpoint or modality: every pair is inside the "
    "measured illumination envelope (delta incidence <= 15 deg) by "
    "construction, near-nadir, one instrument, one mare region.",
    "NOT a matcher claim beyond B1. B4L is reported beside every criterion and "
    "enters none of them.",
    "NOT a verdict change. A wrong pass at a coarse rung is recorded beside "
    "the verdict, not patched out of it.",
    "NOT sub-pixel in the fine image's native pixels beyond the native rung. "
    "Degradation discards everything above the coarse Nyquist before matching, "
    "by design; 'sub-pixel' at a coarse rung means sub-pixel in COARSE pixels, "
    "and the metres are printed beside every pixel figure so the two cannot be "
    "confused.",
]


def exp016_status() -> dict[str, Any]:
    missing = [] if EXP016_ARTEFACT.exists() else [
        str(EXP016_ARTEFACT.relative_to(ROOT)).replace("\\", "/")]
    return {"available": not missing, "missing": missing}


def exp016_evidence() -> dict[str, Any]:
    """EXP-016, assembled for the page. Raises if the artefact is absent."""
    status = exp016_status()
    if not status["available"]:
        raise DemoDataMissing("scale panel: missing " + ", ".join(status["missing"]))

    doc = _read(EXP016_ARTEFACT, "EXP-016 results",
                require=("criteria", "ladder", "operator", "population_A"))
    crit = doc["criteria"]
    s0, s1, s2, s3, s4, s5 = (crit["S0"], crit["S1"], crit["S2"],
                              crit["S3"], crit["S4"], crit["S5"])
    sec = doc.get("secondary") or crit.get("secondary") or {}

    ladder = [int(r) for r in doc["ladder"]]
    rungs_d = [int(r) for r in doc.get("arm_D_rungs", ladder)]

    per_rung = []
    for r in rungs_d:
        cell = s1["per_rung"].get(str(r)) or {}
        cons = (s4.get("per_rung") or {}).get(str(r)) or {}
        starv = [c for c in (sec.get("starvation_curve") or []) if c["r"] == r]
        kp = sorted(c["kp_src"] for c in starv) if starv else []
        nn = sorted(c["N"] for c in starv) if starv else []
        per_rung.append({
            "r": r,
            "n_pairs_run": cell.get("n_pairs_run"),
            "n_success": cell.get("n_success"),
            "n_wrong_pass": cell.get("n_wrong_pass"),
            "median_N": (nn[len(nn) // 2] if nn else None),
            "median_keypoints_src": (kp[len(kp) // 2] if kp else None),
            "consistency_median_coarse_px": cons.get("median_coarse_px"),
            "consistency_median_m": cons.get("median_m"),
            "consistency_p90_coarse_px": cons.get("p90_coarse_px"),
            "grid_occupancy_median": (sec.get("grid_occupancy_median_per_rung_arm_D")
                                      or {}).get(str(r)),
        })

    arm_n = []
    for r, v in sorted((s3.get("per_rung") or {}).items(), key=lambda kv: int(kv[0])):
        scales = [x for x in (v.get("N_recovered_scale") or []) if x is not None]
        arm_n.append({
            "r": int(r), "n": v.get("n"),
            "D_success": v.get("D_success"), "N_success": v.get("N_success"),
            "D_only": v.get("D_only"), "N_only": v.get("N_only"),
            "N_failure_kinds": v.get("N_failure_kinds"),
            "N_recovered_scale_median": (sorted(scales)[len(scales) // 2] if scales else None),
            "expected_scale": next((x for x in (v.get("N_expected_scale") or [])
                                    if x is not None), None),
        })

    arm_l = []
    for r, v in sorted((s5.get("per_rung") or {}).items(), key=lambda kv: int(kv[0])):
        arm_l.append({"r": int(r), "n": v.get("n"), "n_localised": v.get("n_localised"),
                      "offsets_coarse_px": v.get("offsets"), "psr": v.get("psr")})

    return {
        "construction": {
            "what": ("real LRO NAC pairs the pipeline already registers at its "
                     "native rung, both images degraded through a stated PSF to a "
                     "common coarser GSD and matched there -- the architecture's "
                     "own answer to scale"),
            "operator": doc["operator"],
            "ladder": ladder,
            "arms": {
                "D": "degrade both to the coarse GSD (the architecture)",
                "N": "no normalisation: native source against the coarse reference "
                     "(the counterfactual the architecture rejects)",
                "X": "same coarse pixel count, half the ratio -- the control that "
                     "separates starvation from descriptor failure",
                "L": "template localisation by normalised cross-correlation, which "
                     "is what 320:1 physically is on data that exists",
            },
            "n_pairs": s1.get("n_pairs"),
        },
        "criteria": {
            "S0": {"met": bool(s0.get("met")),
                   "operator_bitexact": bool((s0.get("operator_gate") or {}).get("i_met")),
                   "recorded_counts_reproduced": bool((s0.get("operator_gate") or {}).get("ii_met")),
                   "native_gate": bool((s0.get("native_gate") or {}).get("met")),
                   "self_scale_shift_ok": bool((s0.get("iv_self_scale") or {}).get("met_shift")),
                   "self_scale_inlier_failures": len(((s0.get("iv_self_scale") or {})
                                                      .get("inlier_clause_failures") or [])),
                   "why_that_matters": ((s0.get("iv_self_scale") or {})
                                        .get("inlier_clause_note"))},
            "S1": {"met": bool(s1.get("met")), "envelope_r": s1.get("envelope_r"),
                   "clause": s1.get("clause"), "n_pairs": s1.get("n_pairs")},
            "S2": {"verdict": s2.get("verdict"),
                   "concordance": (s2.get("concordance") or {}).get("concordance"),
                   "n_cell_pairs": (s2.get("concordance") or {}).get("n"),
                   "mcnemar_p": (s2.get("concordance") or {}).get("p_exact_mcnemar"),
                   "beta_N": (s2.get("logistic") or {}).get("beta_N"),
                   "p_beta_N": (s2.get("logistic") or {}).get("p_beta_N"),
                   "beta_r": (s2.get("logistic") or {}).get("beta_r"),
                   "p_beta_r": (s2.get("logistic") or {}).get("p_beta_r"),
                   "n_discordant": len(s2.get("discordant_cells") or []),
                   "pixel_floor": s2.get("pixel_floor_arm_D")},
            "S3": {"met": bool(s3.get("met")),
                   "D_ge_N_every_rung": bool(s3.get("D_ge_N_every_rung")),
                   "mcnemar": s3.get("pooled_mcnemar"),
                   "vacuity_note": s3.get("vacuity_note")},
            "S4": {"met": bool(s4.get("met")), "fraction_within": s4.get("fraction_within"),
                   "n_successes": s4.get("n_successes"), "n_checked": s4.get("n_checked"),
                   "n_cannot_check": s4.get("n_cannot_check"),
                   "label": s4.get("label"), "vacuity_note": s4.get("vacuity_note")},
            "S5": {"met": bool(s5.get("met")),
                   "localisation_envelope_r": s5.get("localisation_envelope_r")},
        },
        "per_rung": per_rung,
        "arm_N": arm_n,
        "arm_L": arm_l,
        "population_B": s1.get("population_B") or [],
        "secondary": {
            "B4L": sec.get("B4L_arm_D"),
            "native_failure_stratum_n": len(sec.get("native_failure_stratum") or []),
        },
        "ps_arithmetic": {
            "note": ("what the problem statement's own pairings hold in coarse "
                     "pixels; arithmetic against the measured pixel floor, not "
                     "evidence from this ladder"),
            "pairings": [
                {"pairing": "TMC-2 to NAC", "ratio": "5-10:1",
                 "coarse_px_per_NAC_tile": "400x200 down to 800x400"},
                {"pairing": "IIRS to NAC", "ratio": "40-160:1",
                 "coarse_px_per_NAC_tile": "100x50 down to 25x13; 512x256 at 8:1 over a long window"},
                {"pairing": "OHRC to IIRS", "ratio": "320:1",
                 "coarse_px_per_NAC_tile": "about 150x37 = 5 550 IIRS px per OHRC frame"},
            ],
        },
        "summary": EXP016_SUMMARY,
        "scope": EXP016_SCOPE,
        "not_claimed": list(EXP016_NOT_CLAIMED),
        "sources": list(EXP016_SOURCES),
    }
