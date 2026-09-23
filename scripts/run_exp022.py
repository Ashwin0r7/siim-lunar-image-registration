"""EXP-022 — criterion 4 at the match counts real registrations actually have,
run exactly as Part 1 froze it (docs/stages/EXP-022_coverage_at_real_counts.md).

EXP-014's instrument, re-aimed: the same ten real NAC tiles, decimated k = 2 to
the 2048 x 1024 frame the 39 VERIFIED edges were measured in; the same known
similarity; the same true-correspondence pool and subset shapes -- but subset
sizes equal to the edges' own 22 distinct inlier counts (9 ... 5437), so the
regime the edges occupy is sampled instead of extrapolated. Arm N adds
positional noise at the level the edges' own recorded fit RMSE implies; arm 0
is EXP-014's clean condition, reported beside.

Nothing is re-implemented: subset shapes are run_exp014.draw_subset, the floor
is run_exp015.crossing_from_above, the CI is run_exp014.bootstrap_threshold on
the negated metric (EXP-015's procedure).

    python scripts/run_exp022.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from run_exp014 import bootstrap_threshold, crossing_threshold, draw_subset  # noqa: E402
from run_exp015 import crossing_from_above  # noqa: E402

from siim.baselines.engines import run_baseline  # noqa: E402
from siim.evaluation.coverage import coverage_metrics  # noqa: E402
from siim.geometry import estimate, pixel_grid, similarity, warp  # noqa: E402
from siim.preprocessing.degrade import block_mean  # noqa: E402

_spec = importlib.util.spec_from_file_location("_exp007", ROOT / "scripts" / "run_exp007.py")
_e7 = importlib.util.module_from_spec(_spec)
sys.modules["_exp007"] = _e7
_spec.loader.exec_module(_e7)

#: Amendment A1: image preparation. "v1" is Part 1 as frozen (min-max after a
#: block mean); "A1" is the recorded pipeline's own stretch(decimate(raw, 2)).
PREP = "v1"

STAGE = "EXP-022"
PREREG = "docs/stages/EXP-022_coverage_at_real_counts.md Part 1"
OUT = ROOT / "experiments" / STAGE
TILES = ROOT / "data" / "processed" / "mare_serenitatis"
EXP012 = ROOT / "experiments" / "EXP-012" / "exp012_results.json"
EXP014 = ROOT / "experiments" / "EXP-014" / "exp014_results.json"

# -- Part 1 section 2, frozen ------------------------------------------------
N_TILES = 10
K = 2
SIZES = (9, 28, 47, 68, 108, 143, 144, 190, 210, 265, 272, 284, 293,
         1406, 1608, 1656, 1679, 2138, 2597, 2726, 5392, 5437)
SHAPES = ("uniform", "clustered", "half", "corner", "ring", "two_blobs")
DRAWS = 3
MODEL = "affine"
GRID_STEP = 16
TRUE_MATCH_TOL_PX = 2.0
MIN_POOL = 300
TRUTH = dict(scale=1.03, theta_deg=4.0, tx=11.0, ty=-7.0)
# -- Part 1 section 3, frozen ------------------------------------------------
ERROR_BOUND_PX = 1.0
PCT = 95
LATTICE = 1.0 / 64
EXP015_T = 0.078125
S0_MEDIAN_ERR_PX = 0.05
S1_MIN_HIGH_OCC_ROWS = 30
S1_HIGH_OCC = 0.99
S1_MIN_LARGE_ROWS = 30
S1_LARGE_N = 1000
CELL_COUNT_FRAC = 0.25
CELL_OCC = 1.0 / 64
CELL_MIN_ROWS = 5
S4_MIN_REJECT = 0.10
S6_MAX_SIZE = 293
S6_MIN_FRACTION = 0.80


def verified_edges() -> list[dict]:
    """The 39 VERIFIED edges, read from EXP-012 -- never recomputed (S0 iii)."""
    doc = json.loads(EXP012.read_text(encoding="utf-8"))
    out = []
    for t in doc["triplets"]:
        for v in t.get("verdicts", []):
            vd = v.get("verdict") or {}
            if vd.get("status") != "VERIFIED":
                continue
            m = vd.get("metrics") or {}
            out.append({"window": t.get("window"), "edge": v.get("edge"),
                        "triplet": list(t.get("frames", [])),
                        "n_inliers": int(m["n_inliers"]),
                        "occupancy": float(m["coverage_occupancy"]),
                        "fit_rmse": float(m["fit_rmse"])})
    return out


def score_tile(path: Path, idx: int, sigma_n: float, rows: list, controls: list) -> None:
    raw = np.load(path, mmap_mode="r")
    if PREP == "A1":
        img = _e7.stretch(_e7.decimate(np.asarray(raw, dtype=np.float64), K))
    else:
        img = block_mean(np.asarray(raw, dtype=np.float64), K)
        lo_, hi_ = np.nanmin(img), np.nanmax(img)
        img = (img - lo_) / (hi_ - lo_) if hi_ > lo_ else img * 0
    h, w = img.shape
    truth = similarity(TRUTH["scale"], np.deg2rad(TRUTH["theta_deg"]), TRUTH["tx"], TRUTH["ty"])
    ref, valid = warp(img, truth, out_shape=(h, w))
    ref = np.nan_to_num(ref, nan=0.0)
    res = run_baseline("b1", img, ref)
    m = res.matches
    n_put = 0 if m.src_points is None else len(m.src_points)
    if n_put == 0:
        controls.append({"tile": path.name, "status": "SKIPPED", "reason": "no putative matches"})
        return
    err = np.linalg.norm(truth.apply(m.src_points) - m.dst_points, axis=1)
    keep = err < TRUE_MATCH_TOL_PX
    src, dst = m.src_points[keep], m.dst_points[keep]
    if len(src) < MIN_POOL:
        controls.append({"tile": path.name, "status": "SKIPPED", "n_putative": n_put,
                         "reason": f"true-correspondence pool {len(src)} < {MIN_POOL}"})
        return
    roi = valid & np.isfinite(valid)
    grid = pixel_grid((h, w), step=GRID_STEP)
    gi = (np.clip(grid[:, 1].astype(int), 0, h - 1), np.clip(grid[:, 0].astype(int), 0, w - 1))
    g = grid[roi[gi]]
    truth_g = truth.apply(g)

    def dense(t):
        return np.linalg.norm(t.apply(g) - truth_g, axis=1)

    full = estimate(src, dst, MODEL)
    med_full = float(np.median(dense(full.transform))) if full.ok else float("inf")
    ok = med_full < S0_MEDIAN_ERR_PX
    skipped_sizes = [s for s in SIZES if s > len(src)]
    controls.append({"tile": path.name, "status": "OK" if ok else "S0_FAILED",
                     "n_putative": n_put, "n_pool": int(len(src)),
                     "full_fit_median_err_px": med_full, "sizes_skipped_pool_too_small": skipped_sizes})
    if not ok:
        return
    rng = np.random.default_rng(22000 + idx)
    noise_rng = np.random.default_rng(22500 + idx)
    for shape_name in SHAPES:
        for size in SIZES:
            if size > len(src):
                continue
            for d in range(DRAWS):
                sel = draw_subset(src, shape_name, size, rng)
                if sel is None or len(sel) < 6:
                    continue
                s = src[sel]
                cov = coverage_metrics(s, (h, w), roi=roi)
                noise = noise_rng.normal(0.0, sigma_n, size=(len(sel), 2))
                for arm, t_pts in (("N", dst[sel] + noise), ("0", dst[sel])):
                    fit = estimate(s, t_pts, MODEL)
                    if not fit.ok:
                        continue
                    e = dense(fit.transform)
                    rows.append({"arm": arm, "tile": path.name, "shape": shape_name,
                                 "size": int(size), "draw": d, "n_points": int(len(sel)),
                                 "p99_err_px": float(np.percentile(e, 99)),
                                 "median_err_px": float(np.median(e)),
                                 "grid_occupancy": float(cov.grid_occupancy),
                                 "max_uncovered_disc_ratio": float(cov.max_uncovered_disc_ratio)})


def matched(rows: list, edge: dict) -> list:
    """Part 1 section 2.3: n_points within +/-25 % of the edge's count AND
    occupancy within +/-1/64 of its occupancy."""
    n, o = edge["n_inliers"], edge["occupancy"]
    return [r for r in rows if abs(r["n_points"] - n) <= CELL_COUNT_FRAC * n
            and abs(r["grid_occupancy"] - o) <= CELL_OCC + 1e-12]


def main() -> None:
    global PREP
    ap = argparse.ArgumentParser()
    ap.add_argument("--amendment", choices=["A1"], default=None)
    args = ap.parse_args()
    if args.amendment == "A1":
        PREP = "A1"
    out_path = OUT / ("exp022_results_A1.json" if PREP == "A1" else "exp022_results.json")
    if out_path.exists():
        raise SystemExit(f"{out_path} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    # -- S0 (i): the instrument reproduces EXP-015's floor ------------------
    e14 = json.loads(EXP014.read_text(encoding="utf-8"))
    real14 = [r for r in e14["rows"] if r["arm"] == "real"]
    t_repro, _ = crossing_from_above([r["grid_occupancy"] for r in real14],
                                     [r["p99_err_px"] for r in real14], ERROR_BOUND_PX, PCT)
    s0_i = {"met": t_repro == EXP015_T, "recomputed": t_repro, "recorded": EXP015_T}
    print(f"S0(i) crossing_from_above on EXP-014 rows: {t_repro} (EXP-015 recorded {EXP015_T})", flush=True)
    if not s0_i["met"]:
        raise SystemExit("S0(i) failed: the calibration instrument is not EXP-015's; nothing is reported")

    edges = verified_edges()
    sigma_n = float(np.median([e["fit_rmse"] for e in edges]) / np.sqrt(2.0))
    print(f"39 VERIFIED edges read; sigma_N = median(fit_rmse)/sqrt(2) = {sigma_n:.4f} px", flush=True)

    rows: list = []
    controls: list = []
    tiles = sorted(TILES.glob("*.tile.npy"))[:N_TILES]
    for i, p in enumerate(tiles):
        tt = time.perf_counter()
        score_tile(p, i, sigma_n, rows, controls)
        c = controls[-1]
        print(f"  [{i + 1}/{len(tiles)}] {p.name[:48]:48s} {c['status']:9s} pool={c.get('n_pool', '-')} "
              f"rows={len(rows)} ({time.perf_counter() - tt:.0f}s)", flush=True)

    rN = [r for r in rows if r["arm"] == "N"]
    r0 = [r for r in rows if r["arm"] == "0"]
    s0 = {"i_reproduces_exp015": s0_i,
          "ii_tiles": controls,
          "ii_met": any(c["status"] == "OK" for c in controls)
                    and not any(c["status"] == "S0_FAILED" for c in controls),
          "iii_edges_read_from": "experiments/EXP-012/exp012_results.json (verdict metrics)",
          "iv_sigma_n_px": sigma_n,
          "iv_sigma_n_source": "median of the 39 VERIFIED edges' recorded fit_rmse, divided by sqrt(2)"}
    s0["met"] = bool(s0_i["met"] and s0["ii_met"])

    # -- S1: the regime is sampled, not extrapolated -------------------------
    n_high = sum(r["grid_occupancy"] >= S1_HIGH_OCC for r in rN)
    n_large = sum(r["n_points"] >= S1_LARGE_N for r in rN)
    cells = []
    for e in edges:
        mr = matched(rN, e)
        p95 = float(np.percentile([r["p99_err_px"] for r in mr], PCT)) if mr else None
        cells.append(dict(e, n_matched=len(mr), p95_of_p99_err_px=p95,
                          p95_of_p99_err_px_arm0=(float(np.percentile(
                              [r["p99_err_px"] for r in matched(r0, e)], PCT)) if matched(r0, e) else None)))
    uncovered = [c for c in cells if c["n_matched"] < CELL_MIN_ROWS]
    s1 = {"met": bool(n_high >= S1_MIN_HIGH_OCC_ROWS and n_large >= S1_MIN_LARGE_ROWS and not uncovered),
          "rows_occupancy_ge_0_99": n_high, "rows_n_points_ge_1000": n_large,
          "edges_without_a_cell": [(c["window"], c["edge"], c["n_inliers"], c["occupancy"], c["n_matched"])
                                   for c in uncovered]}

    # -- S2: the floor at real counts ----------------------------------------
    occN = [r["grid_occupancy"] for r in rN]
    errN = [r["p99_err_px"] for r in rN]
    T2, bins = crossing_from_above(occN, errN, ERROR_BOUND_PX, PCT)
    lo = hi = None
    nboot = 0
    if T2 is not None:
        lo_n, hi_n, nboot = bootstrap_threshold([-x for x in occN], errN, ERROR_BOUND_PX, PCT)
        lo, hi = (None if hi_n is None else -hi_n), (None if lo_n is None else -lo_n)
    T0, _b0 = crossing_from_above([r["grid_occupancy"] for r in r0], [r["p99_err_px"] for r in r0],
                                  ERROR_BOUND_PX, PCT)
    s2 = {"met": True, "T2": T2, "never_crosses": T2 is None, "bootstrap_ci95": [lo, hi],
          "bootstrap_n": nboot, "bins": bins, "arm0_T": T0,
          "rows_arm_N": len(rN), "rows_over_bound_arm_N": int(sum(e > ERROR_BOUND_PX for e in errN))}

    # -- S3: criterion 4'' ----------------------------------------------------
    if T2 is None:
        s3 = {"met": None, "reads": "NOT EVALUABLE: the population never crosses 1 px"}
        s4 = {"met": None, "reads": "NOT EVALUABLE: no floor"}
    else:
        line = T2 + LATTICE
        fails = [c for c in cells if c["occupancy"] < line - 1e-12]
        s3 = {"met": not fails, "floor_plus_margin": line, "n_pass": len(cells) - len(fails),
              "n": len(cells), "failing_edges": [(c["window"], c["edge"], c["n_inliers"], c["occupancy"])
                                                 for c in fails]}
        rej = sum(o < T2 for o in occN) / len(occN)
        s4 = {"met": bool(rej >= S4_MIN_REJECT), "reject_fraction": rej, "bar": S4_MIN_REJECT}

    # -- S5: the direct bound, per edge --------------------------------------
    s5_fail = [c for c in cells if c["p95_of_p99_err_px"] is None or c["p95_of_p99_err_px"] >= ERROR_BOUND_PX]
    s5 = {"met": not s5_fail, "n_within": len(cells) - len(s5_fail), "n": len(cells),
          "failing_edges": [(c["window"], c["edge"], c["n_inliers"], c["occupancy"],
                             c["p95_of_p99_err_px"], c["n_matched"]) for c in s5_fail]}

    # -- S6: the property is present (null from the property) ----------------
    per_size = []
    for size in [s for s in SIZES if s <= S6_MAX_SIZE]:
        cl = [r["p99_err_px"] for r in rN if r["size"] == size and r["shape"] == "clustered"]
        un = [r["p99_err_px"] for r in rN if r["size"] == size and r["shape"] == "uniform"]
        if cl and un:
            per_size.append({"size": size, "median_clustered": float(np.median(cl)),
                             "median_uniform": float(np.median(un)),
                             "clustered_worse": bool(np.median(cl) > np.median(un))})
    frac = (sum(p["clustered_worse"] for p in per_size) / len(per_size)) if per_size else 0.0
    s6 = {"met": bool(frac >= S6_MIN_FRACTION), "fraction": frac, "per_size": per_size}

    adopted = bool(s0["met"] and s1["met"] and s3.get("met") and s4.get("met") and s5["met"] and s6["met"])
    doc = {"stage": STAGE, "preregistration": PREREG, "image_preparation": PREP,
           "image_preparation_note": ("stretch(decimate(raw, 2)) from scripts/run_exp007.py -- Amendment A1"
                                      if PREP == "A1" else "block_mean then min-max, as Part 1 froze it"),
           "constants": {"k": K, "sizes": list(SIZES), "shapes": list(SHAPES), "draws": DRAWS,
                         "truth": TRUTH, "error_bound_px": ERROR_BOUND_PX, "percentile": PCT,
                         "lattice": LATTICE, "cell": {"count_frac": CELL_COUNT_FRAC, "occupancy": CELL_OCC,
                                                      "min_rows": CELL_MIN_ROWS}},
           "criteria": {"S0": s0, "S1": s1, "S2": s2, "S3": s3, "S4": s4, "S5": s5, "S6": s6},
           "adoption": {"criterion_4pp_adopted": adopted,
                        "rule": "adopted only if S0, S1, S3, S4, S5 and S6 are all MET"},
           "edges": cells, "rows": rows,
           "environment": {"python": sys.version.split()[0], "numpy": np.__version__,
                           "platform": platform.platform()},
           "total_runtime_s": round(time.perf_counter() - t0, 1),
           "claims_not_supported": [
               "real cross-illumination local error: the truth is synthetic; arm N adds noise at the recorded "
               "level, not its spatial structure",
               "a change to the verdict: assess() and COVERAGE_GAP_WARN are untouched",
               "terrain beyond the ten Mare Serenitatis tiles"]}
    out_path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"\nS0 {'MET' if s0['met'] else 'NOT MET'} | S1 {'MET' if s1['met'] else 'NOT MET'} "
          f"(occ>=0.99: {n_high}, n>=1000: {n_large}, uncovered edges: {len(uncovered)}) | "
          f"S2 T''={T2} CI {lo}..{hi} (arm 0: {T0}) | S3 {s3.get('met')} | S4 {s4.get('met')} | "
          f"S5 {s5['met']} ({s5['n_within']}/{s5['n']}) | S6 {s6['met']} ({frac:.2f}) | adopted {adopted}",
          flush=True)
    print(f"-> {out_path} ({doc['total_runtime_s']} s)", flush=True)


if __name__ == "__main__":
    main()
