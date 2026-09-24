"""EXP-024 — criterion 4 from each edge's own inlier layout.

Runs the stage frozen in `docs/stages/EXP-024_coverage_direct_bound.md`
Part 1 (commit 8ebd78e). Order of operations, and S0 can stop everything:

  S0  re-match all 22 distinct EXP-012 edges through run_exp012's own
      machinery and require every recorded `n_inliers` back EXACTLY (its S5
      bar; `rematch` raises on the first mismatch). Then recompute
      `grid_occupancy` from the kept inlier positions and require every
      edge-row's recorded `coverage_occupancy` back EXACTLY. Record sigma_N
      by EXP-022's formula, re-read from exp012_results.json.
  S1  per edge: 200 seeded draws of truth(positions) + N(0, sigma_N^2),
      affine fit, dense p99 against EXP-014's truth on a 16-px grid over the
      source tile's finite region; the edge's number is the p95 of p99.
  S2  the seven distinct edges EXP-022 left unsampled, decided directly.
  S3  the three edges EXP-022 named, beside their proxy-cell numbers
      (read from exp022_results_A1.json, never recomputed).
  S4  the shrunk-layout null (factor 8 toward the centroid), same draws.

Artefacts: `experiments/EXP-024/exp024_results.json` (numbers) and
`exp024_inlier_positions.npz` (each edge's positions, the thing
REAL-DATA-07 never recorded), SHA-256 cross-referenced.

    python scripts/run_exp024.py

Integrity rule 4: refuses to overwrite an existing artefact.
"""

from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.evaluation.coverage import coverage_metrics  # noqa: E402
from siim.geometry import estimate, pixel_grid, similarity  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_e12 = _load("_exp012", ROOT / "scripts" / "run_exp012.py")
_e7 = sys.modules["_exp007"]  # loaded by run_exp012 at import

STAGE = "EXP-024"
DATA = ROOT / "data"
OUT = ROOT / "experiments" / STAGE
EXP012 = ROOT / "experiments" / "EXP-012" / "exp012_results.json"
EXP022 = ROOT / "experiments" / "EXP-022" / "exp022_results_A1.json"

# -- Part 1, frozen ----------------------------------------------------------
TRUTH = dict(scale=1.03, theta_deg=4.0, tx=11.0, ty=-7.0)   # EXP-014, unchanged
DRAWS = 200
SEED_BASE = 20260924
GRID_STEP = 16
MODEL = "affine"
ERROR_BOUND_PX = 1.0
PCT = 95
SHRINK = 8.0
S4_MIN_EDGES = 20            # of 22
SIGMA_TOL = 1e-4             # S0 (iii): against EXP-022's recorded 0.7202
SIGMA_EXP022 = 0.7202
#: The seven distinct edges EXP-022 Part 2 section 8 (S1 row) lists as
#: unsampled (two empty cells, five thin), identified by their unique
#: inlier counts.
SEVEN_UNSAMPLED = (108, 190, 265, 293, 2597, 2726, 5392)
#: The three edges EXP-022 named, by inlier count.
THREE_NAMED = (9, 28, 68)


def verified_rows() -> list[dict]:
    """The 39 VERIFIED edge-rows: recorded occupancy, inliers, fit_rmse.
    Read from EXP-012's artefact, never recomputed (Part 1 section 0)."""
    doc = json.loads(EXP012.read_text(encoding="utf-8"))
    out = []
    for t in doc["triplets"]:
        for v in t.get("verdicts", []):
            vd = v.get("verdict") or {}
            if vd.get("status") != "VERIFIED":
                continue
            m = vd.get("metrics") or {}
            out.append({"window": t.get("window"), "edge": v.get("edge"),
                        "n_inliers": int(m["n_inliers"]),
                        "occupancy": float(m["coverage_occupancy"]),
                        "fit_rmse": float(m["fit_rmse"])})
    return out


def main() -> None:
    t_start = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    res_path = OUT / "exp024_results.json"
    npz_path = OUT / "exp024_inlier_positions.npz"
    for p in (res_path, npz_path):
        if p.exists():
            raise SystemExit(f"{p.relative_to(ROOT)} exists; an artefact is never "
                             "overwritten (integrity rule 4)")

    rows39 = verified_rows()
    sigma_n = float(np.median([r["fit_rmse"] for r in rows39]) / np.sqrt(2.0))
    sigma_ok = abs(sigma_n - SIGMA_EXP022) <= SIGMA_TOL
    print(f"sigma_N = median(fit_rmse of 39 rows)/sqrt(2) = {sigma_n:.4f} px "
          f"(EXP-022 recorded {SIGMA_EXP022}; within {SIGMA_TOL}: {sigma_ok})", flush=True)

    edges_recorded = json.loads(EXP012.read_text(encoding="utf-8"))["edges"]
    print(f"{len(edges_recorded)} distinct edges read from EXP-012", flush=True)

    # ---- S0: re-match through run_exp012's machinery, positions kept -------
    products: dict = {}
    for name in _e7.GEOMETRY_FILES + ["real_data_07_index_geometry.json"]:
        p = DATA / "manifests" / name
        if p.exists():
            products.update(json.loads(p.read_text(encoding="utf-8"))["products"])

    truth = similarity(TRUTH["scale"], np.deg2rad(TRUTH["theta_deg"]),
                       TRUTH["tx"], TRUTH["ty"])
    per_edge: list[dict] = []
    positions: dict[str, np.ndarray] = {}
    occ_checks: list[dict] = []

    # The inventory is run_exp012's own, reproduced exactly: per window, the
    # pairs its triplets need, in its sorted order. The SAME frame pair exists
    # in BOTH windows with different tiles and different recorded counts
    # (e.g. 1406 in RD03's window and 1679 in RD04's), so an edge's identity
    # here is (window, edge string), and the artefact-order index is asserted
    # against EXP-012's `edges` list entry by entry.
    art_i = 0
    for window in ("RD03", "RD04"):
        rec_by_pair = _e12.recorded_successes(window)
        tris = _e12.triplets(window)
        needed = {frozenset(p) for tri in tris
                  for p in itertools.combinations(tri, 2)}
        if not needed:
            continue
        man = json.loads((DATA / "manifests" / _e12.WINDOWS[window]).read_text(encoding="utf-8"))
        target = tuple(man["target_ground_point_lon_lat"])
        ctx = {t["pdsid"]: _e7.FrameContext(t["pdsid"], t, products, target)
               for t in man["tiles"]}
        rotated: dict[str, object] = {}

        def rot(pdsid):
            if pdsid not in rotated:
                rotated[pdsid] = _e12.rotate_frame(ctx[pdsid])
            return rotated[pdsid]

        for pair in sorted(needed, key=lambda s: sorted(s)):
            recorded = rec_by_pair[pair]
            src, dst = _e12.edge_direction(recorded)
            rec = _e12.rematch(ctx, src, dst, recorded)   # raises on S0 (i) failure
            want = edges_recorded[art_i]
            if want["edge"] != rec["edge"] or int(want["n_inliers"]) != rec["n_inliers"]:
                raise SystemExit(
                    f"S0: inventory drifted at index {art_i}: EXP-012 lists "
                    f"{want['edge']} ({want['n_inliers']}), this run produced "
                    f"{rec['edge']} ({rec['n_inliers']})")
            mask = rec["_inlier_mask"]
            pts = np.asarray(rec["_src_points"], float)[mask]
            shape = tuple(int(s) for s in rec["shape_src_rotated"])
            key = f"{window}:{rec['edge']}"
            positions[key] = pts
            # S0 (ii): occupancy identity against every edge-row that cites this edge
            occ = float(coverage_metrics(pts, shape, roi=None).grid_occupancy)
            for row in rows39:
                if row["window"] == window and row["edge"] == rec["edge"]:
                    occ_checks.append({"window": window, "edge": rec["edge"],
                                       "recorded": row["occupancy"],
                                       "recomputed": occ,
                                       "equal": bool(occ == row["occupancy"])})
            finite = np.isfinite(rot(src).image)
            per_edge.append({"edge": rec["edge"], "window": window, "index": art_i,
                             "n_inliers": rec["n_inliers"],
                             "n_inliers_recorded": rec["n_inliers_recorded"],
                             "reproduces_recorded": rec["reproduces_recorded"],
                             "occupancy_recomputed": occ,
                             "shape": list(shape), "_pts": pts, "_finite": finite})
            print(f"  S0 [{art_i}] {window} {rec['edge']}: {rec['n_inliers']} inliers "
                  f"(recorded {rec['n_inliers_recorded']}), occupancy {occ:.6f} "
                  f"[{rec['wall_s']}s]", flush=True)
            art_i += 1
        for f in ctx.values():
            f.release()

    if len(per_edge) != len(edges_recorded):
        raise SystemExit(f"S0: matched {len(per_edge)} edges, EXP-012 lists "
                         f"{len(edges_recorded)}; the inventory drifted")
    occ_all_equal = all(c["equal"] for c in occ_checks)
    if not occ_all_equal:
        bad = [c for c in occ_checks if not c["equal"]]
        raise SystemExit(f"S0 (ii) FAILED: recomputed occupancy differs on {bad}; "
                         "the stage stops (Part 1 section 4)")

    # ---- S1 / S4: the direct bound and the shrunk null ---------------------
    #: edge_index = the edge's position in EXP-012's `edges` list (Part 1 2.2),
    #: asserted above entry by entry.
    for ed in per_edge:
        rng = np.random.default_rng(SEED_BASE + ed["index"])
        pts, shape, finite = ed["_pts"], tuple(ed["shape"]), ed["_finite"]
        grid = pixel_grid(shape, step=GRID_STEP)
        gi = (np.clip(grid[:, 1].astype(int), 0, shape[0] - 1),
              np.clip(grid[:, 0].astype(int), 0, shape[1] - 1))
        g = grid[finite[gi]]
        tg = truth.apply(g)
        c = pts.mean(axis=0)
        shrunk = c + (pts - c) / SHRINK

        def p95_of_p99(p):
            td = truth.apply(p)
            p99s = []
            for _ in range(DRAWS):     # own arm first, then shrunk: one generator
                noisy = td + rng.normal(0.0, sigma_n, size=p.shape)
                fit = estimate(p, noisy, MODEL)
                if not fit.ok:
                    p99s.append(float("inf"))
                    continue
                err = np.linalg.norm(fit.transform.apply(g) - tg, axis=1)
                p99s.append(float(np.percentile(err, 99)))
            return float(np.percentile(p99s, PCT)), p99s

        own, own_draws = p95_of_p99(pts)
        null, _ = p95_of_p99(shrunk)
        ed.update(p95_of_p99_own_px=own, p95_of_p99_shrunk_px=null,
                  median_p99_own_px=float(np.median(own_draws)),
                  within_bound=bool(own < ERROR_BOUND_PX),
                  null_exceeds_own=bool(null > own))
        print(f"  BOUND {ed['edge']} (n={ed['n_inliers']}): own {own:.3f} px, "
              f"shrunk {null:.3f} px -> {'within' if own < ERROR_BOUND_PX else 'OVER'}",
              flush=True)

    # ---- criteria, exactly as frozen ---------------------------------------
    by_count = {e["n_inliers"]: e for e in per_edge}
    over = [e for e in per_edge if not e["within_bound"]]
    s1 = {"criterion": "S1", "met": not over,
          "n_edges": len(per_edge),
          "edges_over_bound": [{"edge": e["edge"], "n_inliers": e["n_inliers"],
                                "p95_of_p99_px": e["p95_of_p99_own_px"]} for e in over]}
    seven = [by_count[n] for n in SEVEN_UNSAMPLED]
    s2 = {"criterion": "S2", "met": all(e["within_bound"] for e in seven),
          "edges": [{"edge": e["edge"], "n_inliers": e["n_inliers"],
                     "p95_of_p99_px": e["p95_of_p99_own_px"],
                     "within_bound": e["within_bound"]} for e in seven]}
    proxy = {r["n_inliers"]: r for r in
             json.loads(EXP022.read_text(encoding="utf-8"))["edges"]}
    s3_rows = []
    for n in THREE_NAMED:
        e = by_count[n]
        s3_rows.append({"edge": e["edge"], "n_inliers": n,
                        "direct_p95_px": e["p95_of_p99_own_px"],
                        "proxy_p95_px": proxy[n]["p95_of_p99_err_px"],
                        "proxy_call_not_met": proxy[n]["p95_of_p99_err_px"] >= ERROR_BOUND_PX,
                        "direct_call_not_met": not e["within_bound"],
                        "proxy_call_stands": bool(
                            (proxy[n]["p95_of_p99_err_px"] >= ERROR_BOUND_PX)
                            == (not e["within_bound"]))})
    s3 = {"criterion": "S3", "met": True, "rows": s3_rows,
          "note": "MET means the comparison is recorded; direction is S1's business"}
    n_null = sum(1 for e in per_edge if e["null_exceeds_own"])
    s4 = {"criterion": "S4", "met": n_null >= S4_MIN_EDGES,
          "n_null_exceeds_own": n_null, "bar": S4_MIN_EDGES,
          "edges_where_null_did_not_exceed": [e["edge"] for e in per_edge
                                              if not e["null_exceeds_own"]]}

    # triplet outcome, from the artefact's triplets and this stage's numbers
    doc12 = json.loads(EXP012.read_text(encoding="utf-8"))
    p95_by_edge = {(e["window"], e["edge"]): e["p95_of_p99_own_px"] for e in per_edge}
    triplets = []
    for t in doc12["triplets"]:
        edges3 = [v["edge"] for v in t["verdicts"]]
        vals = []
        for name in edges3:
            v = p95_by_edge.get((t["window"], name))
            if v is None:  # the recorded edge string may be reversed vs verdicts
                a, b = (s.strip() for s in name.split("->"))
                v = p95_by_edge.get((t["window"], f"{b} -> {a}"))
            vals.append(v)
        triplets.append({"frames": t["frames"], "edges": edges3,
                         "p95_of_p99_px": vals,
                         "clear_on_all_edges": bool(all(
                             v is not None and v < ERROR_BOUND_PX for v in vals))})

    np.savez_compressed(npz_path, **{f"{e['window']}:{e['edge']}": e["_pts"]
                                     for e in per_edge})
    npz_sha = hashlib.sha256(npz_path.read_bytes()).hexdigest()

    s0 = {"criterion": "S0", "met": bool(sigma_ok and occ_all_equal),
          "i_counts_exact": True,   # rematch raises otherwise
          "ii_occupancy_exact": occ_all_equal, "occupancy_checks": occ_checks,
          "iii_sigma_n": {"value_px": sigma_n, "formula": "median(fit_rmse of the 39 "
                          "VERIFIED edge-rows)/sqrt(2), read from exp012_results.json",
                          "exp022_recorded": SIGMA_EXP022, "within_tol": sigma_ok},
          "iv_truth": TRUTH, "v_overwrite_refused": True}

    doc = {
        "stage": STAGE, "part": "Part 2 artefact",
        "preregistration": "docs/stages/EXP-024_coverage_direct_bound.md "
                           "(frozen 2026-09-24, commit 8ebd78e)",
        "constants": {"draws": DRAWS, "seed_base": SEED_BASE, "grid_step": GRID_STEP,
                      "model": MODEL, "bound_px": ERROR_BOUND_PX, "pct": PCT,
                      "shrink": SHRINK, "sigma_n_px": sigma_n},
        "criteria": {"S0": s0, "S1": s1, "S2": s2, "S3": s3, "S4": s4},
        "edges": [{k: v for k, v in e.items() if not k.startswith("_")}
                  for e in per_edge],
        "triplets": triplets,
        "n_triplets_clear": sum(1 for t in triplets if t["clear_on_all_edges"]),
        "inlier_positions_file": {"path": npz_path.name, "sha256": npz_sha},
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
        "total_runtime_s": round(time.time() - t_start, 1),
        "claims_not_supported": [
            "The truth is synthetic and the noise iid at the recorded level, "
            "without its spatial structure (EXP-022's limitation, inherited).",
            "A failing edge's layout does not bound local error at 1 px under "
            "this noise model; the edge itself is not shown wrong (EXP-021 "
            "labelled none of the 39 WRONG).",
            "Criterion 4's written form (gap <= 0.15) stays NOT MET whatever "
            "these numbers say (Part 1 consequence rule).",
            "Mare Serenitatis tiles only.",
        ],
    }
    res_path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"\nS0 {'MET' if s0['met'] else 'NOT MET'} | "
          f"S1 {'MET' if s1['met'] else 'NOT MET'} ({len(over)} over) | "
          f"S2 {'MET' if s2['met'] else 'NOT MET'} | S3 recorded | "
          f"S4 {'MET' if s4['met'] else 'NOT MET'} ({n_null}/22) | "
          f"triplets clear {doc['n_triplets_clear']}/13 | "
          f"{doc['total_runtime_s']}s -> {res_path.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
