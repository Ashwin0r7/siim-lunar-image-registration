"""EXP-014 — ADR-0006's acceptance test, run exactly as Part 1 froze it.

Does ``max_uncovered_disc_ratio`` predict worst-case LOCAL registration error
better than grid occupancy, spatial entropy or convex-hull ratio -- and at what
value does a 1.0 px worst-case bound actually get crossed?

The response variable is the **worst case** (p99 of the dense endpoint error
over the ROI), not a mean, because an average cannot bound a worst case and
that is ADR-0006's own reason for rejecting occupancy and entropy as primary.
Error is measured between the **maps** against a known transform, never from a
fit residual.

    python scripts/run_exp014.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.baselines.engines import run_baseline  # noqa: E402
from siim.data.synthetic_terrain import height_field, render  # noqa: E402
from siim.evaluation.coverage import coverage_metrics  # noqa: E402
from siim.geometry import Transform, endpoint_error, estimate, pixel_grid, similarity, warp  # noqa: E402

OUT = ROOT / "experiments" / "EXP-014"
TILES = ROOT / "data" / "processed" / "mare_serenitatis"

# -- Part 1 section 3, declared in full and not extended -------------------
N_TILES = 10
SHAPES = ("uniform", "clustered", "half", "corner", "ring", "two_blobs")
SIZES = (12, 25, 50, 100, 200)
DRAWS_PER_CELL = 3
CROP = 768                     # centre crop, native resolution (real texture)
MODEL = "affine"
GRID_STEP = 16                 # dense error sampling
TRUE_MATCH_TOL_PX = 2.0        # pool admission: agrees with the known transform

# -- Part 1 section 4, frozen ---------------------------------------------
S0_MEDIAN_ERR_PX = 0.05        # harness control
ERROR_BOUND_PX = 1.0           # S2/S3 bound; may NOT be moved in Part 2
S3_PERCENTILE = 95             # "95th percentile of p99 error crosses the bound"
S4_MIN_PARTIAL_RHO = 0.3

METRICS = ("max_uncovered_disc_ratio", "grid_occupancy",
           "spatial_entropy", "hull_ratio")
#: Sign each metric is expected to take against error. Lower coverage-gap is
#: better (positive correlation with error); the other three are "more is
#: better" (negative correlation). Declared so a sign flip is visible.
EXPECTED_SIGN = {"max_uncovered_disc_ratio": +1, "grid_occupancy": -1,
                 "spatial_entropy": -1, "hull_ratio": -1}


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------
def _rank(a):
    a = np.asarray(a, float)
    order = a.argsort()
    r = np.empty(len(a), float)
    r[order] = np.arange(len(a), dtype=float)
    # average ties
    _, inv, cnt = np.unique(a, return_inverse=True, return_counts=True)
    sums = np.zeros(len(cnt)); np.add.at(sums, inv, r)
    return (sums / cnt)[inv]


def spearman(x, y) -> float:
    rx, ry = _rank(x), _rank(y)
    rx = rx - rx.mean(); ry = ry - ry.mean()
    d = float(np.sqrt((rx ** 2).sum() * (ry ** 2).sum()))
    return float((rx * ry).sum() / d) if d > 0 else 0.0


def partial_spearman(x, y, z) -> float:
    """Spearman of x,y with z partialled out -- the S4 confound control."""
    xy, xz, yz = spearman(x, y), spearman(x, z), spearman(y, z)
    den = np.sqrt(max(1e-12, (1 - xz ** 2) * (1 - yz ** 2)))
    return float((xy - xz * yz) / den)


def roc_auc(score, label) -> float:
    """P(score of a positive > score of a negative), ties at 0.5."""
    score = np.asarray(score, float); label = np.asarray(label, bool)
    n_pos, n_neg = int(label.sum()), int((~label).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    r = _rank(score)
    return float((r[label].sum() - n_pos * (n_pos - 1) / 2) / (n_pos * n_neg))


def crossing_threshold(gap, err, bound, pct, n_bins=24):
    """Lowest coverage gap at which the pct-th percentile of err exceeds bound.

    Binned so the answer is a property of the population rather than of one
    unlucky row. Returns None when the population never crosses -- which is
    itself a reportable outcome, not a failure to compute.
    """
    gap = np.asarray(gap, float); err = np.asarray(err, float)
    if len(gap) < n_bins * 4:
        n_bins = max(4, len(gap) // 8)
    edges = np.quantile(gap, np.linspace(0, 1, n_bins + 1))
    rows = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        sel = (gap >= lo) & (gap <= hi if i == n_bins - 1 else gap < hi)
        if sel.sum() < 4:
            continue
        rows.append({"gap_lo": float(lo), "gap_hi": float(hi),
                     "gap_mid": float(np.median(gap[sel])), "n": int(sel.sum()),
                     "err_pct": float(np.percentile(err[sel], pct)),
                     "err_median": float(np.median(err[sel]))})
    cross = next((r["gap_mid"] for r in rows if r["err_pct"] > bound), None)
    return cross, rows


def bootstrap_threshold(gap, err, bound, pct, n=200, seed=17):
    rng = np.random.default_rng(seed)
    gap = np.asarray(gap, float); err = np.asarray(err, float)
    out = []
    for _ in range(n):
        idx = rng.integers(0, len(gap), len(gap))
        c, _r = crossing_threshold(gap[idx], err[idx], bound, pct)
        if c is not None:
            out.append(c)
    if not out:
        return None, None, 0
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), len(out)


# ---------------------------------------------------------------------------
# subsets -- the independent variable
# ---------------------------------------------------------------------------
def draw_subset(pts, shape_name, size, rng):
    """Indices of a subset with a declared spatial shape, or None if short."""
    n = len(pts)
    if size > n:
        return None
    x, y = pts[:, 0], pts[:, 1]
    cx, cy = x.mean(), y.mean()
    if shape_name == "uniform":
        return rng.choice(n, size, replace=False)
    if shape_name == "clustered":
        c = pts[rng.integers(n)]
        return np.argsort(((pts - c) ** 2).sum(1))[:size]
    if shape_name == "half":
        keep = (x < cx) if rng.random() < 0.5 else (x >= cx)
        idx = np.flatnonzero(keep)
        return rng.choice(idx, size, replace=False) if len(idx) >= size else None
    if shape_name == "corner":
        keep = (x < cx) & (y < cy) if rng.random() < 0.5 else (x >= cx) & (y >= cy)
        idx = np.flatnonzero(keep)
        return rng.choice(idx, size, replace=False) if len(idx) >= size else None
    if shape_name == "ring":
        r = np.hypot(x - cx, y - cy)
        rmax = r.max() or 1.0
        idx = np.flatnonzero((r > 0.35 * rmax) & (r < 0.65 * rmax))
        return rng.choice(idx, size, replace=False) if len(idx) >= size else None
    if shape_name == "two_blobs":
        half = size // 2
        out = []
        for _ in range(2):
            c = pts[rng.integers(n)]
            out.append(np.argsort(((pts - c) ** 2).sum(1))[:half])
        idx = np.unique(np.concatenate(out))
        return idx if len(idx) >= half else None
    raise ValueError(shape_name)


# ---------------------------------------------------------------------------
# one image -> many rows
# ---------------------------------------------------------------------------
def score_image(img, label, arm, seed, rows, controls):
    rng = np.random.default_rng(seed)
    h, w = img.shape
    truth = similarity(1.03, np.deg2rad(4.0), 11.0, -7.0)
    ref, valid = warp(img, truth, out_shape=(h, w))
    ref = np.nan_to_num(ref, nan=0.0)

    res = run_baseline("b1", img, ref)
    m = res.matches
    if m.src_points is None or len(m.src_points) < 250:
        controls.append({"image": label, "arm": arm, "status": "SKIPPED",
                         "reason": f"pool too small ({0 if m.src_points is None else len(m.src_points)} putative)"})
        return

    # admit only correspondences that agree with the KNOWN transform
    err = np.linalg.norm(truth.apply(m.src_points) - m.dst_points, axis=1)
    keep = err < TRUE_MATCH_TOL_PX
    src, dst = m.src_points[keep], m.dst_points[keep]
    if len(src) < max(SIZES):
        controls.append({"image": label, "arm": arm, "status": "SKIPPED",
                         "reason": f"true-correspondence pool {len(src)} < {max(SIZES)}"})
        return

    roi = valid & np.isfinite(valid)
    grid = pixel_grid((h, w), step=GRID_STEP)
    gi = np.clip(grid[:, 1].astype(int), 0, h - 1), np.clip(grid[:, 0].astype(int), 0, w - 1)
    in_roi = roi[gi]
    if in_roi.sum() < 100:
        controls.append({"image": label, "arm": arm, "status": "SKIPPED",
                         "reason": "ROI too small"})
        return
    g = grid[in_roi]
    truth_g = truth.apply(g)

    def dense_err(t: Transform):
        return np.linalg.norm(t.apply(g) - truth_g, axis=1)

    # -- S0: the harness control, on the FULL pool ------------------------
    full = estimate(src, dst, MODEL)
    if not full.ok:
        controls.append({"image": label, "arm": arm, "status": "SKIPPED",
                         "reason": "full-pool fit failed"})
        return
    e_full = dense_err(full.transform)
    med = float(np.median(e_full))
    ok = med < S0_MEDIAN_ERR_PX
    controls.append({"image": label, "arm": arm,
                     "status": "OK" if ok else "S0_FAILED",
                     "n_pool": int(len(src)), "full_fit_median_err_px": med,
                     "threshold_px": S0_MEDIAN_ERR_PX})
    if not ok:
        return  # nothing is reported from a tile whose harness control fails

    for shape_name in SHAPES:
        for size in SIZES:
            for d in range(DRAWS_PER_CELL):
                idx = draw_subset(src, shape_name, size, rng)
                if idx is None or len(idx) < 6:
                    continue
                s, t = src[idx], dst[idx]
                fit = estimate(s, t, MODEL)
                if not fit.ok:
                    continue
                e = dense_err(fit.transform)
                cov = coverage_metrics(s, (h, w), roi=roi)
                rows.append({
                    "arm": arm, "image": label, "shape": shape_name,
                    "size": int(size), "draw": d, "n_points": int(len(idx)),
                    "p99_err_px": float(np.percentile(e, 99)),
                    "max_err_px": float(e.max()),
                    "median_err_px": float(np.median(e)),
                    "max_uncovered_disc_ratio": float(cov.max_uncovered_disc_ratio),
                    "grid_occupancy": float(cov.grid_occupancy),
                    "spatial_entropy": float(cov.spatial_entropy),
                    "hull_ratio": float(cov.hull_ratio),
                })


def main() -> None:
    out_path = OUT / "exp014_results.json"
    if out_path.exists():
        raise SystemExit(f"{out_path.relative_to(ROOT)} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows: list[dict] = []
    controls: list[dict] = []

    # -- arm (a): real NAC self-warps, first ten in sorted filename order --
    tiles = sorted(TILES.glob("*.tile.npy"))[:N_TILES]
    print(f"real arm: {len(tiles)} tiles")
    for i, p in enumerate(tiles):
        a = np.load(p, mmap_mode="r")
        h, w = a.shape[:2]
        if min(h, w) < CROP:
            controls.append({"image": p.name, "arm": "real", "status": "SKIPPED",
                             "reason": f"tile {h}x{w} smaller than {CROP} crop"})
            continue
        r0, c0 = (h - CROP) // 2, (w - CROP) // 2
        img = np.asarray(a[r0:r0 + CROP, c0:c0 + CROP], dtype=np.float64)
        rng_ = img.max() - img.min()
        img = (img - img.min()) / rng_ if rng_ > 0 else img * 0
        print(f"  [{i+1}/{len(tiles)}] {p.name}", flush=True)
        score_image(img, p.name, "real", 4000 + i, rows, controls)

    # -- arm (b): synthetic terrain, two regimes, reported separately ------
    for j, scene in enumerate(("mare", "highlands")):
        rng = np.random.default_rng(7000 + j)
        hf = height_field((CROP, CROP), rng, scene=scene, relief=30.0)
        img = render(hf, sun_azimuth_deg=135.0, sun_elevation_deg=45.0, rng=rng)
        img = (img - img.min()) / (img.max() - img.min() or 1.0)
        print(f"  synthetic {scene}", flush=True)
        score_image(img, scene, "synthetic", 7000 + j, rows, controls)

    if not rows:
        raise SystemExit("no rows produced; nothing is reported")

    # -- criteria ---------------------------------------------------------
    def arm_rows(a):
        return [r for r in rows if r["arm"] == a]

    def analyse(sel):
        if len(sel) < 30:
            return None
        err = [r["p99_err_px"] for r in sel]
        npts = [r["n_points"] for r in sel]
        label = [e > ERROR_BOUND_PX for e in err]
        out = {"n": len(sel), "n_over_bound": int(sum(label)),
               "bound_px": ERROR_BOUND_PX, "metrics": {}}
        for m in METRICS:
            v = [r[m] for r in sel]
            rho = spearman(v, err)
            # orient the score so "higher = more likely bad" for the AUC
            score = v if EXPECTED_SIGN[m] > 0 else [-x for x in v]
            out["metrics"][m] = {
                "spearman_rho": rho,
                "abs_spearman_rho": abs(rho),
                "sign_as_expected": bool(np.sign(rho) == EXPECTED_SIGN[m]) if rho else False,
                "roc_auc": roc_auc(score, label),
                "partial_rho_controlling_n_points": partial_spearman(v, err, npts),
            }
        return out

    real, synth = analyse(arm_rows("real")), analyse(arm_rows("synthetic"))
    if real is None:
        raise SystemExit("real arm produced too few rows to analyse")

    def winner(a, key):
        return max(a["metrics"], key=lambda m: (a["metrics"][m][key]
                                                if np.isfinite(a["metrics"][m][key]) else -9))

    prim = "max_uncovered_disc_ratio"
    s1_win = winner(real, "abs_spearman_rho")
    s2_win = winner(real, "roc_auc")
    s1 = {"criterion": "S1",
          "statement": "|Spearman rho| of max_uncovered_disc_ratio vs p99 local error "
                       "exceeds all three alternatives (real arm)",
          "met": s1_win == prim, "winner": s1_win,
          "values": {m: real["metrics"][m]["abs_spearman_rho"] for m in METRICS}}
    s2 = {"criterion": "S2",
          "statement": f"ROC AUC as a detector of p99 err > {ERROR_BOUND_PX} px "
                       "exceeds all three alternatives (real arm)",
          "met": s2_win == prim, "winner": s2_win,
          "values": {m: real["metrics"][m]["roc_auc"] for m in METRICS}}

    sel = arm_rows("real")
    gap = [r[prim] for r in sel]; err = [r["p99_err_px"] for r in sel]
    cross, bins = crossing_threshold(gap, err, ERROR_BOUND_PX, S3_PERCENTILE)
    lo, hi, nboot = bootstrap_threshold(gap, err, ERROR_BOUND_PX, S3_PERCENTILE)
    s3 = {"criterion": "S3",
          "statement": f"the max_uncovered_disc_ratio at which the {S3_PERCENTILE}th "
                       f"percentile of p99 local error crosses {ERROR_BOUND_PX} px",
          "met": True,
          "calibrated_threshold": cross,
          "bootstrap_ci95": [lo, hi], "bootstrap_n": nboot,
          "incumbent_asserted_value": 0.15,
          "note": "a measurement, not a pass/fail; reported whether or not it "
                  "lands near the asserted 0.15 (D-053)",
          "bins": bins}

    pr = real["metrics"][prim]["partial_rho_controlling_n_points"]
    s4 = {"criterion": "S4",
          "statement": f"|partial Spearman rho| controlling for n_points >= "
                       f"{S4_MIN_PARTIAL_RHO}, with the predicted sign",
          "met": bool(abs(pr) >= S4_MIN_PARTIAL_RHO
                      and np.sign(pr) == EXPECTED_SIGN[prim]),
          "partial_rho": pr, "raw_rho": real["metrics"][prim]["spearman_rho"],
          "min_required": S4_MIN_PARTIAL_RHO,
          "all_metrics": {m: real["metrics"][m]["partial_rho_controlling_n_points"]
                          for m in METRICS},
          "note": "if NOT MET, S1 and S2 mean nothing and must not be quoted "
                  "without this beside them (Part 1 section 4)"}

    s5 = {"criterion": "S5",
          "statement": "the S1 winner on the synthetic arm is the same metric as on the real arm",
          "met": bool(synth and winner(synth, "abs_spearman_rho") == s1_win),
          "real_winner": s1_win,
          "synthetic_winner": winner(synth, "abs_spearman_rho") if synth else None}

    n_ok = sum(1 for c in controls if c.get("status") == "OK")
    s0 = {"criterion": "S0",
          "statement": f"full-pool fit median dense error < {S0_MEDIAN_ERR_PX} px",
          "met": n_ok > 0 and not any(c.get("status") == "S0_FAILED" for c in controls),
          "n_images_passing": n_ok,
          "n_images_failed": sum(1 for c in controls if c.get("status") == "S0_FAILED"),
          "n_images_skipped": sum(1 for c in controls if c.get("status") == "SKIPPED"),
          "images": controls}

    doc = {
        "stage": "EXP-014", "part": 2,
        "preregistration": "docs/stages/EXP-014_coverage_validation.md",
        "what": "ADR-0006's acceptance test: does max_uncovered_disc_ratio predict "
                "worst-case LOCAL registration error better than the alternatives, "
                "and at what value does a 1.0 px bound get crossed?",
        "frozen_constants": {
            "error_bound_px": ERROR_BOUND_PX, "s3_percentile": S3_PERCENTILE,
            "s0_median_err_px": S0_MEDIAN_ERR_PX,
            "s4_min_partial_rho": S4_MIN_PARTIAL_RHO,
            "shapes": list(SHAPES), "sizes": list(SIZES),
            "note": "Part 1 section 4; not tuned in Part 2"},
        "model": MODEL, "crop_px": CROP, "grid_step_px": GRID_STEP,
        "n_rows": len(rows),
        "criteria": {c["criterion"]: c for c in (s0, s1, s2, s3, s4, s5)},
        "analysis_real": real, "analysis_synthetic": synth,
        "rows": rows,
        "claims_not_supported": [
            "NOT a real cross-illumination accuracy claim: self-warps share the "
            "original's texture, so every error here is an upper bound on "
            "precision (EXP-010 S1).",
            "NOT a verdict change: assess() is not edited by this stage.",
            "NOT a Chandrayaan-2 result.",
        ],
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
        "total_runtime_s": round(time.time() - t0, 1),
    }
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    print(f"\nrows: {len(rows)}  (real {len(arm_rows('real'))}, synthetic {len(arm_rows('synthetic'))})")
    print(f"\n{'metric':30s} {'|rho|':>8s} {'rho':>8s} {'AUC':>8s} {'partial rho':>12s}")
    for m in METRICS:
        k = real["metrics"][m]
        print(f"{m:30s} {k['abs_spearman_rho']:8.3f} {k['spearman_rho']:8.3f} "
              f"{k['roc_auc']:8.3f} {k['partial_rho_controlling_n_points']:12.3f}")
    print()
    for c in (s0, s1, s2, s3, s4, s5):
        print(f"  {c['criterion']}: {'MET' if c['met'] else 'NOT MET'} -- {c['statement']}")
    print(f"\ncalibrated threshold: {cross}  (asserted incumbent 0.15)  CI95 [{lo}, {hi}]")
    print(f"wrote {out_path.relative_to(ROOT)} in {doc['total_runtime_s']} s")


if __name__ == "__main__":
    main()
