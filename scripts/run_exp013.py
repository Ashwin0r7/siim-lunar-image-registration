"""EXP-013 — gauge detection, run exactly as Part 1 froze it.

Criteria S0-S6 are evaluated as ``docs/stages/EXP-013_gauge_detection.md``
section 6 fixes them, including the two alarm constants, which are read from
``siim.verify.gauge`` and are **not** re-declared here so they cannot drift.

Two arms are **supplementary** and are written to their own keys, deliberately
not folded into any criterion -- the same separation EXP-012 used for its gauge
probe after E-039:

* ``supplementary_structureless_null`` -- the control Part 1's S4 should have
  been. S4 as frozen permutes node *labels*, which on a 3-cycle is a relabelling
  and cannot test what it was written to test. The property the control needs is
  *a disagreement of the same magnitude with no per-node structure*, and this
  arm builds one.
* ``supplementary_census_graph`` -- the same fit on the REAL-DATA-07 census
  graph instead of a triplet, where the per-node model is genuinely
  over-determined, with a cross-engine control.

    python scripts/run_exp013.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.evaluation.gtfree import loop_closure  # noqa: E402
from siim.geometry import Transform, endpoint_error, pixel_grid, similarity  # noqa: E402
from siim.verify.gauge import (  # noqa: E402
    EXPLAINED_FRACTION_ALARM,
    GAUGE_MAGNITUDE_ALARM_PX,
    GaugeEdge,
    decompose_gauge,
    decompose_gauge_graph,
    two_core,
)

EXPERIMENTS = ROOT / "experiments"
OUT = EXPERIMENTS / "EXP-013"
RD07 = EXPERIMENTS / "REAL-DATA-07"
EXP012 = EXPERIMENTS / "EXP-012" / "exp012_results.json"

#: Part 1 section 5(a): EXP-012's base, unchanged.
ROWS = {"RD03": "rows_rd03_nue.json", "RD04": "rows_rd04_nue.json"}
ENGINE = "b1"

#: Part 1 section 5(b), declared in full and not extended afterwards.
MAGNITUDES = (0.0, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0)
SEEDS = list(range(9001, 9013))
SYNTH_SHAPE = (512, 512)
LOOP_TOL_PX = 1e-9

#: Part 1 section 6 S1/S6: "at least 11 of 12".
DETECT_MIN = 11
#: Part 1 section 6 S3: the smallest recorded discrimination floor at native
#: NAC scale. Not a tuning knob -- it is what the per-edge check already has.
PER_EDGE_FLOOR_PX = 84.0
N_PERMUTATIONS = 200
N_NULL_TRIALS = 200
#: The headline fits sample at the module default. The control arms run
#: thousands of fits, so they sample the same field more coarsely. The
#: statistic is an RMS over the grid and is insensitive to the step within
#: reason (``gauge.decompose_gauge``), and a control and the quantity it
#: calibrates always use the SAME step, which is the part that matters.
CONTROL_GRID_STEP = 128
CENSUS_GRID_STEP = 128


# ---------------------------------------------------------------------------
# real rows
# ---------------------------------------------------------------------------
def real_rows() -> dict[tuple[str, frozenset], dict]:
    """The B1 successes EXP-012 composed its triplets from, filtered its way.

    The filter is copied from ``run_exp012.recorded_successes`` rather than
    re-invented: a different filter would silently compose a different
    population and every comparison to EXP-012 would be meaningless.
    """
    out: dict[tuple[str, frozenset], dict] = {}
    for window, name in ROWS.items():
        doc = json.loads((RD07 / name).read_text(encoding="utf-8"))
        for r in doc["rows"]:
            if r.get("excluded") or "reproduces_recorded" in r:
                continue
            if r.get("engine") != ENGINE or not r.get("success"):
                continue
            out[(window, frozenset(r["pair"]))] = r
    return out


def row_to_edge(r: dict) -> GaugeEdge:
    """One recorded row as a gauge edge.

    ``transform_matrix_original_pixels`` is paired with
    ``geometry.predicted_transform_matrix``, **not** ``transform_matrix``:
    the archive prediction is expressed in the original-pixel frame, and the
    two tile-frame origins differ (E-040). Direction comes from ``edge``, the
    order the engine was actually fed, never from ``pair``, which is sorted
    (E-036, and EXP-012's S5 caught the same defect again).
    """
    src, dst = r["edge"].split(" -> ")
    g = r["geometry"]
    return GaugeEdge(
        src=src, dst=dst,
        estimate=Transform(np.asarray(r["transform_matrix_original_pixels"], float), "affine"),
        predicted=Transform(np.asarray(g["predicted_transform_matrix"], float), "affine"),
        floor_px=float(g["discrimination_floor_px"]),
    )


def triplet_edges(rows: dict, t: dict) -> list[GaugeEdge]:
    out = []
    for leg in t["cycle"]:
        a, b = leg.split(" -> ")
        out.append(row_to_edge(rows[(t["window"], frozenset((a, b)))]))
    return out


# ---------------------------------------------------------------------------
# the synthetic gauge construction, reused unmodified in its geometry
# ---------------------------------------------------------------------------
def gauge_case(seed: int, magnitude_px: float):
    """EXP-012's construction verbatim, plus the true transforms it hides.

    The geometry is unchanged from ``run_exp012_s3_gauge.gauge_case`` (Part 1
    section 5b). What is added is the return of ``t_*``, which that script did
    not need and this one uses as the noiseless external reference.
    """
    rng = np.random.default_rng(seed)
    t_ab = similarity(1.02, np.deg2rad(3.0), 9.0, -6.0)
    t_bc = similarity(0.99, np.deg2rad(-2.0), -5.0, 7.0)
    t_ca = (t_bc @ t_ab).inverse()

    def gauge():
        ang = float(rng.normal(0, 0.4))
        dx, dy = rng.normal(0, magnitude_px, size=2)
        return similarity(1.0, np.deg2rad(ang), float(dx), float(dy))

    g_a, g_b, g_c = gauge(), gauge(), gauge()
    e_ab = g_b @ t_ab @ g_a.inverse()
    e_bc = g_c @ t_bc @ g_b.inverse()
    e_ca = g_a @ t_ca @ g_c.inverse()
    true_err = float(endpoint_error(e_ab, t_ab, SYNTH_SHAPE, step=16).median)
    return (e_ab, e_bc, e_ca), (t_ab, t_bc, t_ca), true_err


def reference_noise(rng, magnitude_px: float):
    """A small similarity standing for the archive reference's own error.

    Magnitude is calibrated from the real population (Part 1 section 5b) and is
    written into the artefact before any detection statistic is read.
    """
    return similarity(
        1.0 + float(rng.normal(0, magnitude_px / 60000.0)),
        float(rng.normal(0, np.deg2rad(magnitude_px / 1200.0))),
        float(rng.normal(0, magnitude_px * 0.7)),
        float(rng.normal(0, magnitude_px * 0.7)),
    )


def main() -> None:
    out_path = OUT / "exp013_results.json"
    if out_path.exists():
        raise SystemExit(f"{out_path.relative_to(ROOT)} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    rows = real_rows()
    exp012 = json.loads(EXP012.read_text(encoding="utf-8"))
    triplets = exp012["triplets"]

    # -- S2: specificity on the real population ---------------------------
    real = []
    for i, t in enumerate(triplets):
        edges = triplet_edges(rows, t)
        rep = decompose_gauge(edges, tuple(t["shape_used"]))
        real.append({
            "index": i, "window": t["window"],
            "frames": t["frames"],
            "loop_closure_residual_px": t["loop_closure_residual_px"],
            **{k: v for k, v in rep.as_dict().items() if k != "rule"},
        })
    n_real_alarms = sum(1 for r in real if r["alarm"])
    s2 = {"criterion": "S2", "statement": "0 of 13 alarms on the real triplets",
          "met": n_real_alarms == 0, "n_triplets": len(real),
          "n_alarms": n_real_alarms}

    #: calibrated BEFORE any detection statistic is read (Part 1 section 5b)
    ref_noise_px = float(np.median([r["residual_before_px"] for r in real]))

    # -- S0 / S1 / S3 / S6: the synthetic sweep ---------------------------
    synth, loops = [], []
    for magnitude in MAGNITUDES:
        for seed in SEEDS:
            (e_ab, e_bc, e_ca), (t_ab, t_bc, t_ca), true_err = gauge_case(seed, magnitude)
            loops.append(float(loop_closure([e_ab, e_bc, e_ca], SYNTH_SHAPE)))
            rng = np.random.default_rng(seed + 4400)
            edges = [
                GaugeEdge("A", "B", e_ab, reference_noise(rng, ref_noise_px) @ t_ab),
                GaugeEdge("B", "C", e_bc, reference_noise(rng, ref_noise_px) @ t_bc),
                GaugeEdge("C", "A", e_ca, reference_noise(rng, ref_noise_px) @ t_ca),
            ]
            rep = decompose_gauge(edges, SYNTH_SHAPE)
            synth.append({
                "gauge_magnitude_px": magnitude, "seed": seed,
                "loop_error_px": loops[-1],
                "true_transform_error_px": true_err,
                "alarm": rep.alarm,
                "explained_fraction": rep.explained_fraction,
                "fitted_gauge_px": rep.gauge_magnitude_px,
                "residual_before_px": rep.residual_before_px,
            })

    max_loop = max(loops)
    s0 = {"criterion": "S0",
          "statement": "every synthetic case's loop closes, or it is not a gauge case",
          "met": bool(max_loop < LOOP_TOL_PX),
          "max_loop_error_px": max_loop, "tolerance_px": LOOP_TOL_PX}
    if not s0["met"]:
        raise SystemExit(
            f"S0 FAILED: max loop residual {max_loop} px exceeds {LOOP_TOL_PX}. "
            "These are not per-image gauge cases and nothing is reported from "
            "the synthetic arm.")

    by_mag = {}
    for m in MAGNITUDES:
        sel = [s for s in synth if s["gauge_magnitude_px"] == m]
        by_mag[f"{m:g}"] = {
            "n": len(sel),
            "n_alarm": sum(1 for s in sel if s["alarm"]),
            "median_true_edge_error_px": float(np.median(
                [s["true_transform_error_px"] for s in sel])),
            "median_fitted_gauge_px": float(np.median([s["fitted_gauge_px"] for s in sel])),
            "median_explained_fraction": float(np.median(
                [s["explained_fraction"] for s in sel])),
        }

    detected = [m for m in MAGNITUDES
                if m > 0 and by_mag[f"{m:g}"]["n_alarm"] >= DETECT_MIN]
    s1 = {"criterion": "S1",
          "statement": f">= {DETECT_MIN} of 12 alarms at each of 32 and 64 px",
          "met": all(by_mag[f"{m:g}"]["n_alarm"] >= DETECT_MIN for m in (32.0, 64.0)),
          "n_alarm_32": by_mag["32"]["n_alarm"], "n_alarm_64": by_mag["64"]["n_alarm"]}
    floor = min(detected) if detected else None
    s3 = {"criterion": "S3",
          "statement": f"measured detection floor < {PER_EDGE_FLOOR_PX} px "
                       "(the smallest recorded per-edge discrimination floor)",
          "met": floor is not None and floor < PER_EDGE_FLOOR_PX,
          "detection_floor_px": floor,
          "per_edge_floor_px": PER_EDGE_FLOOR_PX,
          "detected_magnitudes_px": detected}
    s6 = {"criterion": "S6", "statement": "0 of 12 alarms at gauge magnitude 0",
          "met": by_mag["0"]["n_alarm"] == 0,
          "n_alarm": by_mag["0"]["n_alarm"],
          "median_fitted_gauge_px": by_mag["0"]["median_fitted_gauge_px"]}

    # -- S4: the permutation control, run exactly as frozen ---------------
    rng = np.random.default_rng(13)
    perm_rows = []
    for i, t in enumerate(triplets):
        edges = triplet_edges(rows, t)
        real_expl = real[i]["explained_fraction"]
        draws = []
        for _ in range(N_PERMUTATIONS):
            nodes = sorted({n for e in edges for n in (e.src, e.dst)})
            shuffled = list(nodes)
            rng.shuffle(shuffled)
            mapping = dict(zip(nodes, shuffled))
            permuted = [GaugeEdge(mapping[e.src], mapping[e.dst],
                                  e.estimate, e.predicted, e.floor_px)
                        for e in edges]
            rep = decompose_gauge_graph(permuted, tuple(t["shape_used"]),
                                        grid_step=CONTROL_GRID_STEP)
            if rep.explained_fraction is not None:
                draws.append(rep.explained_fraction)
        p95 = float(np.percentile(draws, 95)) if draws else None
        perm_rows.append({"index": i, "window": t["window"],
                          "real_explained_fraction": real_expl,
                          "permuted_p95": p95, "n_draws": len(draws),
                          "real_below_p95": bool(p95 is not None and real_expl < p95)})
    n_below = sum(1 for p in perm_rows if p["real_below_p95"])
    s4 = {"criterion": "S4",
          "statement": "the real explained fraction sits below the permuted 95th "
                       "percentile for <= 1 of 13 triplets",
          "met": n_below <= 1, "n_below_p95": n_below, "n_permutations": N_PERMUTATIONS,
          "instrument_note": (
              "Run exactly as frozen. It is the WRONG instrument and this is "
              "reported rather than substituted: permuting node LABELS on a "
              "3-cycle relabels an isomorphic graph, so the permuted fit is the "
              "same fit and the control has no discriminating power. The "
              "property the control needs -- a disagreement of the same "
              "magnitude with no per-node structure -- is measured in "
              "supplementary_structureless_null, which is NOT folded into S4. "
              "This is E-039's lesson recurring inside the stage written "
              "because of it."),
          "rows": perm_rows}

    # -- supplementary: the control S4 should have been --------------------
    rng = np.random.default_rng(29)
    null_by_red = {}
    real_at_control_step = []
    for t, r in zip(triplets, real):
        edges = triplet_edges(rows, t)
        real_at_control_step.append(decompose_gauge(
            edges, tuple(t["shape_used"]),
            grid_step=CONTROL_GRID_STEP).explained_fraction)
        mag = r["residual_before_px"]
        draws = []
        for _ in range(N_NULL_TRIALS // len(triplets) + 1):
            ne = [GaugeEdge(e.src, e.dst, e.estimate,
                            reference_noise(rng, mag) @ e.estimate, e.floor_px)
                  for e in edges]
            rep = decompose_gauge(ne, tuple(t["shape_used"]),
                                  grid_step=CONTROL_GRID_STEP)
            if rep.explained_fraction is not None:
                draws.append(rep.explained_fraction)
        null_by_red.setdefault(r["redundancy"], []).extend(draws)
    structureless = {
        "what": "per-EDGE disagreement of the same magnitude as the real one, "
                "with no per-node structure by construction",
        "why": "S4 as frozen cannot test this (see S4.instrument_note). This "
               "arm names the property instead of a procedure, which is "
               "E-039's lesson.",
        "not_part_of_s4": True,
        "by_redundancy": {
            str(k): {"n": len(v), "median": float(np.median(v)),
                     "p95": float(np.percentile(v, 95)), "max": float(max(v))}
            for k, v in sorted(null_by_red.items())},
        "grid_step_px": CONTROL_GRID_STEP,
        "real_explained_fractions_at_same_grid_step": real_at_control_step,
    }

    # -- supplementary: the census graph, where the model is falsifiable ---
    census = {}
    for window, name in ROWS.items():
        doc = json.loads((RD07 / name).read_text(encoding="utf-8"))
        per_engine = {}
        for engine in ("b1", "lg", "xf"):
            sel = [r for r in doc["rows"]
                   if not r.get("excluded") and "reproduces_recorded" not in r
                   and r.get("engine") == engine and r.get("success")
                   and (r.get("geometry") or {}).get("predicted_transform_matrix")]
            edges = two_core([row_to_edge(r) for r in sel])
            if len(edges) < 3:
                per_engine[engine] = {"status": "CANNOT CHECK",
                                      "reason": f"2-core has {len(edges)} edges"}
                continue
            rep = decompose_gauge_graph(edges, (2048, 1024),
                                        grid_step=CENSUS_GRID_STEP)
            per_engine[engine] = {k: v for k, v in rep.as_dict().items() if k != "rule"}

            rng2 = np.random.default_rng(101)
            mag = rep.residual_before_px or 0.0
            nulls = []
            for _ in range(40):
                ne = [GaugeEdge(e.src, e.dst, e.estimate,
                                reference_noise(rng2, mag) @ e.estimate, e.floor_px)
                      for e in edges]
                nr = decompose_gauge_graph(ne, (2048, 1024),
                                           grid_step=CENSUS_GRID_STEP)
                if nr.explained_fraction is not None:
                    nulls.append(nr.explained_fraction)
            per_engine[engine]["structureless_null"] = {
                "n": len(nulls), "median": float(np.median(nulls)),
                "p95": float(np.percentile(nulls, 95)), "max": float(max(nulls))}
        census[window] = per_engine

    # cross-engine: do independent matchers recover the SAME per-frame term?
    grid = pixel_grid((2048, 1024), step=128)
    cross = {}
    for window, per_engine in census.items():
        pairs = {}
        for a, b in (("b1", "lg"), ("b1", "xf"), ("lg", "xf")):
            ra, rb = per_engine.get(a, {}), per_engine.get(b, {})
            if ra.get("status") != "OK" or rb.get("status") != "OK":
                continue
            common = sorted(set(ra["per_node_px"]) & set(rb["per_node_px"]))
            diffs = {n: abs(ra["per_node_px"][n] - rb["per_node_px"][n]) for n in common}
            if diffs:
                pairs[f"{a}_vs_{b}"] = {
                    "n_common_frames": len(common),
                    "max_difference_px": float(max(diffs.values())),
                    "median_difference_px": float(np.median(list(diffs.values()))),
                    "per_frame_px": diffs}
        cross[window] = pairs

    criteria = {c["criterion"]: c for c in (s0, s1, s2, s3, s4, s6)}
    doc = {
        "stage": "EXP-013",
        "part": 2,
        "preregistration": "docs/stages/EXP-013_gauge_detection.md",
        "what": "an instrument for the per-image gauge error loop closure "
                "cannot see (E-039), reported beside the verdict and never "
                "inside it",
        "alarm_rule": {
            "gauge_magnitude_alarm_px": GAUGE_MAGNITUDE_ALARM_PX,
            "explained_fraction_alarm": EXPLAINED_FRACTION_ALARM,
            "frozen": "EXP-013 Part 1 section 6, before any statistic; not "
                      "tuned in Part 2"},
        "reference_noise_calibration_px": ref_noise_px,
        "reference_noise_calibration_note":
            "median residual_before_px over the 13 real triplets, computed "
            "before any detection statistic was read (Part 1 section 5b)",
        "magnitudes_px": list(MAGNITUDES),
        "n_seeds": len(SEEDS),
        "criteria": criteria,
        "real_triplets": real,
        "synthetic_by_magnitude": by_mag,
        "synthetic_rows": synth,
        "supplementary_structureless_null": structureless,
        "supplementary_census_graph": census,
        "supplementary_cross_engine": cross,
        "claims_not_supported": [
            "NOT a false-acceptance rate: this adds an instrument, not ground "
            "truth. Criterion 3's first two clauses stay unmeasurable.",
            "NOT a fix to loop closure: the invariance is an identity. This is "
            "a second, independent check that looks only at the null space.",
            "NOT validated on a real gauge error: no real triplet is known to "
            "carry one. Detection is synthetic; specificity is real.",
            "NOT an attribution: the instrument localises a disagreement to an "
            "image and cannot say whether the estimate or the archive "
            "reference is the wrong one (Part 1 H3). The cross-engine arm "
            "bounds that, it does not settle it by itself.",
            "NOT a Chandrayaan-2 result.",
        ],
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
        "total_runtime_s": round(time.time() - t0, 1),
    }
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    print(f"reference-noise calibration: {ref_noise_px:.2f} px "
          f"(median real archive disagreement)\n")
    print(f"{'gauge px':>9s} {'n':>3s} {'alarm':>6s} {'true edge err':>14s} "
          f"{'fitted':>8s} {'explained':>10s}")
    for m in MAGNITUDES:
        k = by_mag[f"{m:g}"]
        print(f"{m:9.1f} {k['n']:3d} {k['n_alarm']:6d} "
              f"{k['median_true_edge_error_px']:14.2f} "
              f"{k['median_fitted_gauge_px']:8.2f} {k['median_explained_fraction']:10.3f}")
    print()
    for c in (s0, s1, s2, s3, s4, s6):
        print(f"  {c['criterion']}: {'MET' if c['met'] else 'NOT MET'} -- {c['statement']}")
    print(f"\nwrote {out_path.relative_to(ROOT)} in {doc['total_runtime_s']} s")


if __name__ == "__main__":
    main()
