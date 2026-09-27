"""Chandrayaan-2 evidence for the demo (REAL-DATA-09).

A separate module rather than an addition to :mod:`siim.demo.evidence`: that
file is imported by every recorded demo path, and the project's rule is to add
a module rather than edit one the existing artefacts depend on.

Every figure here is read from a recorded REAL-DATA-09 artefact that the page
also links, so a reader can open the row behind any number. Nothing is
recomputed and nothing is widened: the wording that frames the numbers is
fixed in this file, exactly as ``engines_evidence`` fixes its own.
"""

from __future__ import annotations

from typing import Any

from .evidence import EXPERIMENTS, ROOT, DemoDataMissing, _read

__all__ = ["chandrayaan2_evidence", "chandrayaan2_status", "RD09_SOURCES"]

RD09 = EXPERIMENTS / "REAL-DATA-09"
RD09_B1 = RD09 / "real_data_09_results_b1.json"
RD09_LG = RD09 / "real_data_09_results_lg.json"
RD09_LOOP = RD09 / "real_data_09_loop_closure.json"
RD09_S6 = RD09 / "real_data_09_s6_control.json"
RD09_P5 = RD09 / "real_data_09_p5_dem_render_v2.json"

EXP023 = EXPERIMENTS / "EXP-023"
EXP023_RESULTS = EXP023 / "exp023_results.json"
EXP023_CENSUS = EXP023 / "census.json"

#: Advertised artefact paths, repo-relative. The allow-list is built from this.
RD09_SOURCES = [
    "experiments/REAL-DATA-09/real_data_09_results_b1.json",
    "experiments/REAL-DATA-09/real_data_09_results_lg.json",
    "experiments/REAL-DATA-09/real_data_09_loop_closure.json",
    "experiments/REAL-DATA-09/real_data_09_s6_control.json",
    "experiments/REAL-DATA-09/real_data_09_p5_dem_render_v2.json",
    "experiments/EXP-023/exp023_results.json",
    "experiments/EXP-023/census.json",
]

C2_SUMMARY = (
    "Chandrayaan-2 TMC-2 registers to LRO NAC at 5 m under two independent "
    "engines, every transform geometry-consistent, with no wrong pass; the "
    "illumination envelope measured on NAC-to-NAC pairs reproduces on ISRO's "
    "own sensor. And Chandrayaan-2 OHRC registers to LRO NAC at the "
    "Chandrayaan-3 landing site with five-digit inlier counts, closing a "
    "three-image loop at 1.92 px against the frozen 2.0 px line: the first "
    "VERIFIED Chandrayaan-2 result, by loop closure, with its failed "
    "geometry clause reported beside it."
)

C2_SCOPE = (
    "TMC-2: one strip over Mare Serenitatis, one region, no ground truth; "
    "the geometry check is a bound at its own floor, not a verification. "
    "OHRC: one site, illumination matched by design (theta = 4.42 deg), "
    "VERIFIED means the loop closes - no check point independent of LRO "
    "exists there."
)

C2_NOT_CLAIMED = [
    "NOT a VERIFIED TMC-2 verdict: the single TMC-2 pairs are INCONCLUSIVE, "
    "and the TMC-2 loop is REJECTED at 2.2131 px against a frozen 2.0 px "
    "line. The threshold was not moved to change that - the same frozen line "
    "the OHRC loop later passed at 1.9158 px.",
    "NOT an accuracy: no ground truth and no check points exist for these "
    "products. The geometry check is a bound at its own floor, and OHRC's "
    "own corner-geometry clause FAILED as frozen (105-110 px against a "
    "98 px floor); the VERIFIED is loop closure, nothing more.",
    "NOT an illumination or viewpoint invariance result for OHRC: the census "
    "matched the Sun by design (theta = 4.42 deg), and one site licenses no "
    "envelope.",
    "NO IIRS result: no IIRS product was delivered.",
    "NOT support for DEM-conditioned correspondence: the 10 m TMC-2 DEM "
    "render fails its own positive control on 15 of 15 frames (D-052).",
]

ACKNOWLEDGEMENT = (
    "We acknowledge the use of data from the Chandrayaan-II, second lunar "
    "mission of the Indian Space Research Organisation (ISRO), archived at "
    "the Indian Space Science Data Centre (ISSDC)."
)


def chandrayaan2_status() -> dict[str, Any]:
    """Which REAL-DATA-09 + EXP-023 artefacts are on disk. Never substitutes."""
    missing = [str(p.relative_to(ROOT)).replace("\\", "/")
               for p in (RD09_B1, RD09_LG, RD09_LOOP, RD09_S6, RD09_P5,
                         EXP023_RESULTS, EXP023_CENSUS)
               if not p.exists()]
    return {"available": not missing, "missing": missing}


def _ohrc_block() -> dict[str, Any]:
    """EXP-023, read from its artefact and census. Nothing recomputed."""
    doc = _read(EXP023_RESULTS, "EXP-023 results", require=("criteria",))
    census = _read(EXP023_CENSUS, "EXP-023 census", require=("funnel", "roles"))
    crit = doc["criteria"]
    na = next(r for r in census["ranking_log"] if r.get("taken"))

    def edge(name: str) -> dict[str, Any]:
        e = crit["S2"]["edges"][name]
        g = e["geometry"]
        east, south = g["refined_grid"]["centre_offset_m_east_south"]
        return {"edge": name, "n_inliers": e["n_inliers"],
                "pass": bool(e["pass"]),
                "geometry_median_px": g["refined_grid"]["median_px"],
                "geometry_median_m": g["refined_grid"]["median_m"],
                "floor_px": g["floor_px"], "floor_m": g["floor_m"],
                "geometry_verdict": g["refined_grid"]["verdict"],
                "offset_east_m": east, "offset_south_m": south,
                "system_level_m": g["system_level_corners"]["median_m"]}

    tri = crit["S3"]["primary_triangle"]
    verdict = tri["verdict_on_first_leg"]
    return {
        "site": {"lon_deg": 32.319, "lat_deg": -69.373,
                 "name": "Chandrayaan-3 landing site"},
        "sun_incidence_deg": 78.476,
        "census": {"ode_returned": census["funnel"]["ode_returned"],
                   "admissible": census["funnel"]["after_lr_dedupe"],
                   "na_pdsid": na["pdsid"], "theta_deg": na["theta"],
                   "emission_deg": na["emission"]},
        "edges": [edge("O1->Na"), edge("O2->Na")],
        "loop": {"residual_px": tri["loop_residual_px"],
                 "residual_m": tri["loop_residual_m"],
                 "reject_threshold_px": 2.0,
                 "status": tri["status"],
                 "confidence": verdict.get("confidence"),
                 "reasons": verdict.get("reasons", []),
                 "legs": tri["legs"],
                 "legs_n_inliers": tri["legs_n_inliers"]},
        "nulls": [{"name": k, "n_inliers": v.get("n_inliers"),
                   "pass": bool(v.get("pass"))}
                  for k, v in crit["S4"]["nulls"].items()],
        "b4l": [{"edge": k, "n_inliers": v["n_inliers"],
                 "agreement_median_px": v["agreement_with_b1"]["median_px"]}
                for k, v in crit["S5"]["rows"].items()],
        "stereo": {"n_inliers": doc["ohrc_stereo_edge"]["n_inliers"],
                   "off_nadir_deg": [doc["descriptive"]["viewing"]["O1"]["off_nadir_deg"],
                                     doc["descriptive"]["viewing"]["O2"]["off_nadir_deg"]]},
        "scale": doc["descriptive"]["scale"],
        "criteria_met": {k: crit[k]["met"] for k in
                         ("S0", "S1", "S2", "S3", "S4", "S5")},
    }


def _engine_rows(doc: dict) -> list[dict]:
    return [r for r in doc["rows"] if r.get("engine") and "error" not in r]


def chandrayaan2_evidence() -> dict[str, Any]:
    """REAL-DATA-09, assembled for the page. Raises if any artefact is absent."""
    status = chandrayaan2_status()
    if not status["available"]:
        raise DemoDataMissing(
            "Chandrayaan-2 panel: missing " + ", ".join(status["missing"]))

    b1 = _read(RD09_B1, "REAL-DATA-09 B1 results", require=("rows", "tmc2_ortho"))
    lg = _read(RD09_LG, "REAL-DATA-09 B4L results", require=("rows",))
    loop = _read(RD09_LOOP, "REAL-DATA-09 loop closure", require=("edges",))
    s6 = _read(RD09_S6, "REAL-DATA-09 S6 control", require=("met", "rows"))
    p5 = _read(RD09_P5, "REAL-DATA-09 P5 DEM render", require=("rows",))

    b1_rows, lg_rows = _engine_rows(b1), _engine_rows(lg)

    merged: dict[tuple, dict] = {}
    for doc_rows, col in ((b1_rows, "b1"), (lg_rows, "b4l")):
        for r in doc_rows:
            key = (r["window"], r["frame"])
            row = merged.setdefault(key, {
                "window": r["window"],
                "frame": r["frame"],
                "delta_incidence_deg": r.get("delta_incidence_deg"),
                "nac_incidence_deg": r.get("nac_incidence_deg"),
                "tmc2_valid_fraction": r.get("tmc2_valid_fraction"),
            })
            row[col + "_inliers"] = r["n_inliers"]
            row[col + "_pass"] = bool(r.get("pass"))
            row[col + "_success"] = bool(r.get("success"))
            row[col + "_geometry"] = (r.get("geometry") or {}).get(
                "verdict", "no transform")
    rows = sorted(merged.values(),
                  key=lambda r: (r["delta_incidence_deg"] is None,
                                 r["delta_incidence_deg"] or 0.0))

    successes = [r for r in b1_rows if r.get("success")] + \
                [r for r in lg_rows if r.get("success")]
    wrong = [r for r in b1_rows + lg_rows if r.get("wrong_pass")]

    best_b1 = max((r for r in b1_rows if r.get("success")),
                  key=lambda r: r["n_inliers"], default=None)
    best_lg = max((r for r in lg_rows if r.get("success")),
                  key=lambda r: r["n_inliers"], default=None)

    def headline(r: dict | None, engine: str) -> dict | None:
        if r is None:
            return None
        g = r.get("geometry") or {}
        return {"engine": engine, "frame": r["frame"], "window": r["window"],
                "n_inliers": r["n_inliers"],
                "delta_incidence_deg": r.get("delta_incidence_deg"),
                "geometry": g.get("verdict"),
                "disagreement_px": g.get("disagreement_px_median"),
                "floor_px": g.get("floor_px"),
                "verdict": (r.get("verdict") or {}).get("status")}

    ortho = b1["tmc2_ortho"]
    p5_rows = [r for r in p5["rows"] if "leg_b_test" in r]

    return {
        "product": {
            "id": ortho.get("product_id"),
            "sha256": ortho.get("sha256"),
            "shape": ortho.get("shape"),
            "projection": ortho.get("projection"),
            "geometry_tags_found": ortho.get("geometry_tags_found"),
            "solar_incidence_deg": ortho.get("solar_incidence_deg"),
            "sigma_c2_m": ortho.get("sigma_c2_m"),
            "sigma_c2_source": ortho.get("sigma_c2_source"),
            "structural_identity": ortho.get("structural_identity"),
        },
        "rows": rows,
        "n_engine_rows": len(b1_rows) + len(lg_rows),
        "n_successes": len(successes),
        "n_wrong_passes": len(wrong),
        "best_b1": headline(best_b1, "B1"),
        "best_b4l": headline(best_lg, "B4L"),
        "loop": {
            "edges": [{"edge": e["edge"], "n_inliers": e["n_inliers"]}
                      for e in loop["edges"]],
            "residual_px": loop.get("loop_closure_residual_px"),
            "residual_m": loop.get("loop_closure_residual_m"),
            "reject_threshold_px": 2.0,
            "verdict": (loop.get("verdict_tmc2_to_nac_a") or {}).get("status"),
            "independence": loop.get("edge_independence"),
        },
        "s6_control": {
            "met": bool(s6["met"]),
            "n_edges": s6.get("n_edges_checked"),
            "recorded_counts": s6.get("recorded_counts"),
        },
        "p5_dem_render": {
            "dem_gsd_m": (p5.get("dem") or {}).get("gsd_m"),
            "ortho_gsd_m": (p5.get("ortho") or {}).get("gsd_m"),
            "ratio": p5.get("dem_over_gsd_ratio"),
            "n_frames": len(p5_rows),
            "control_passes": p5.get("leg_a_control_passes"),
            "test_passes": p5.get("leg_b_test_passes"),
        },
        "pairs_without_data": b1.get("pairs_without_data", {}),
        "ohrc": _ohrc_block(),
        "summary": C2_SUMMARY,
        "scope": C2_SCOPE,
        "not_claimed": C2_NOT_CLAIMED,
        "acknowledgement": ACKNOWLEDGEMENT,
        "sources": list(RD09_SOURCES),
    }
