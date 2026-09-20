"""EXP-012 — verdict calibration: is VERIFIED reachable on real lunar data?

Runs the stage frozen in `docs/stages/EXP-012_verdict_calibration.md`
(Part 1 + amendment A1). Nothing here selects a triplet: all 13 admissible
triplets enumerated in Part 1 §2 are run, including the four containing an
INCONCLUSIVE edge.

Order of operations, and every one of them can stop the stage:

  S4  compose REAL-DATA-03's three recorded edges and require its recorded
      1201.0378963072235 px back. If the composition code is wrong, nothing
      else this script computes means anything, so this runs first and alone.
  S5  re-match every edge of every triplet with B1 at the frozen settings and
      require each recorded `n_inliers` back EXACTLY. A single mismatch means
      the environment drifted from the amended REAL-DATA-07 run and the stage
      stops without reporting a residual.
  S1  compose each triplet, take `loop_closure`, run the UNMODIFIED
      `assess()` on all three of its edges with that residual supplied, and
      report every verdict.
  S2  Spearman rho between (minimum edge inliers) and (loop residual).

Usage:
    python scripts/run_exp012.py                # full stage
    python scripts/run_exp012.py --control-only # S4 and S5, no residuals

Integrity rule 4: refuses to overwrite an existing artefact.
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.demo.verdict import assess  # noqa: E402
from siim.evaluation.gtfree import loop_closure  # noqa: E402
from siim.geometry import Transform  # noqa: E402
from siim.ingest.orientation import north_up_east_right  # noqa: E402

_spec = importlib.util.spec_from_file_location("_exp007", ROOT / "scripts" / "run_exp007.py")
_e7 = importlib.util.module_from_spec(_spec)
sys.modules["_exp007"] = _e7
_spec.loader.exec_module(_e7)

STAGE = "EXP-012"
DATA = ROOT / "data"
OUT = ROOT / "experiments" / STAGE
RD07 = ROOT / "experiments" / "REAL-DATA-07"

#: Frozen engine settings. Identical to REAL-DATA-07's BASE (amendment A1: the
#: engine, model, threshold, seed, tiles, windows and orientation all unchanged).
BASE = {"model": "affine", "ransac_threshold_px": 3.0, "seed": 0}
ENGINE = "b1"

WINDOWS = {"RD03": "real_data_07_rd03_manifest.json",
           "RD04": "real_data_07_rd04_manifest.json"}
ROWS = {"RD03": "rows_rd03_nue.json", "RD04": "rows_rd04_nue.json"}

#: S4 control: the only real loop this project has ever computed.
S4_ARTEFACT = ROOT / "experiments" / "REAL-DATA-03" / "loop_closure_triplet.json"
S4_EXPECTED_PX = 1201.0378963072235
S4_TOLERANCE_PX = 1e-6


# --------------------------------------------------------------------------
# S4 — the composition control
# --------------------------------------------------------------------------
def run_s4() -> dict:
    """Re-compose REAL-DATA-03's recorded triplet. Must return its residual."""
    doc = json.loads(S4_ARTEFACT.read_text(encoding="utf-8"))
    edges = doc["edges"]
    if len(edges) != 3:
        raise SystemExit(f"S4: expected 3 recorded edges, found {len(edges)}")
    transforms, chain = [], []
    for e in edges:
        transforms.append(Transform(np.asarray(e["transform_matrix"], float),
                                    BASE["model"]))
        chain.append(e["edge"])
    shape = tuple(int(v) for v in doc["shape_after_decimation"])
    got = float(loop_closure(transforms, shape))
    ok = abs(got - S4_EXPECTED_PX) <= S4_TOLERANCE_PX
    return {"criterion": "S4", "met": bool(ok), "chain": chain, "shape": list(shape),
            "recorded_px": S4_EXPECTED_PX, "recomputed_px": got,
            "abs_difference_px": abs(got - S4_EXPECTED_PX),
            "tolerance_px": S4_TOLERANCE_PX}


# --------------------------------------------------------------------------
# triplet inventory — derived from recorded rows, exactly as Part 1 §2 lists it
# --------------------------------------------------------------------------
def recorded_successes(window: str) -> dict[frozenset, dict]:
    doc = json.loads((RD07 / ROWS[window]).read_text(encoding="utf-8"))
    out: dict[frozenset, dict] = {}
    for r in doc["rows"]:
        if r.get("excluded") or "reproduces_recorded" in r:
            continue
        if r.get("engine") != ENGINE or not r.get("success"):
            continue
        out[frozenset(r["pair"])] = r
    return out


def triplets(window: str) -> list[tuple]:
    es = recorded_successes(window)
    frames = sorted({p for e in es for p in e})
    found = []
    for a, b, c in itertools.combinations(frames, 3):
        need = [frozenset((a, b)), frozenset((b, c)), frozenset((a, c))]
        if all(n in es for n in need):
            found.append((a, b, c))
    return found


# --------------------------------------------------------------------------
# S5 — re-match, and require the recorded inlier count back
# --------------------------------------------------------------------------
def rotate_frame(fc):
    """north_up_east_right for a frame's tile, at the tile's own decimation."""
    k = fc.tile.get("decimation", 2)
    t = fc.tile
    return north_up_east_right(fc.img(k), fc.corners,
                               line=t["line0"] + (t["n_lines"] - 1) / 2,
                               sample=t["sample0"] + (t["n_samples"] - 1) / 2)


def edge_direction(recorded: dict) -> tuple[str, str]:
    """The direction the recorded edge was actually MATCHED in.

    A row carries both ``pair`` and ``edge``, and they disagree: ``pair`` is
    sorted, while ``edge`` is the order the runner fed the engine
    (REAL-DATA-07 iterated frames by ascending incidence). Matching is not
    symmetric -- src and dst play different roles in detection, the ratio test
    and the RANSAC fit -- so reading direction from ``pair`` re-matches some
    edges backwards and returns a different inlier count.

    This was caught by S5 on `m1271742202lc -> m1182331886lc`, which gave 1715
    inliers against a recorded 1656 while two edges whose alphabetical order
    happened to match their execution order reproduced exactly. It is E-036's
    defect -- a reproduction arm run in the wrong direction -- caught the same
    way, by a gate that demanded the recorded number back.
    """
    edge = recorded.get("edge")
    if not edge or " -> " not in edge:
        raise SystemExit(f"row has no usable `edge` field: {recorded.get('pair')}")
    src, dst = (s.strip() for s in edge.split(" -> "))
    if frozenset((src, dst)) != frozenset(recorded["pair"]):
        raise SystemExit(f"`edge` {edge!r} and `pair` {recorded['pair']} disagree "
                         f"on which frames this row relates")
    return src, dst


def rematch(ctx, src: str, dst: str, recorded: dict) -> dict:
    """Re-run B1 on one recorded edge. Returns the edge record, or raises on S5."""
    t0 = time.time()
    ra, rb = rotate_frame(ctx[src]), rotate_frame(ctx[dst])
    res = _e7.run_engine(ENGINE, ra.image, rb.image, BASE)
    mask = np.asarray(res.inlier_mask, dtype=bool)
    n_in = int(mask.sum())
    want = int(recorded["n_inliers"])
    rec = {
        "edge": f"{src} -> {dst}",
        "src": src, "dst": dst,
        "n_inliers": n_in,
        "n_inliers_recorded": want,
        "reproduces_recorded": bool(n_in == want),
        "n_putative": int(res.matches.src_points.shape[0]),
        "fit_rmse_px": float(res.ransac.inlier_rmse),
        "shape_src_rotated": list(ra.image.shape),
        "geometry_verdict_recorded": recorded["geometry"].get("verdict"),
        "delta_incidence_deg": recorded.get("delta_incidence_deg"),
        "wall_s": round(time.time() - t0, 2),
    }
    if not rec["reproduces_recorded"]:
        raise SystemExit(
            f"S5 FAILED on {rec['edge']}: re-match gives {n_in} inliers, the "
            f"amended REAL-DATA-07 run recorded {want}. The environment or the "
            f"code has drifted; the stage stops without reporting any residual.")
    rec["_transform"] = res.transform
    rec["_src_points"] = res.matches.src_points
    rec["_dst_points"] = res.matches.dst_points
    rec["_inlier_mask"] = mask
    return rec


# --------------------------------------------------------------------------
# S1 — compose the loop and run the shipped verdict
# --------------------------------------------------------------------------
def directed(edge_by_pair: dict, a: str, b: str) -> tuple[Transform, bool]:
    """T mapping a -> b, inverting the stored direction if needed.

    Inverting one independently estimated edge is exact and does not
    manufacture closure; the three estimates stay independent. E-021 was a
    *closing edge derived from the other two*, which is a different thing and
    is never done here. `inverted` is recorded per edge.
    """
    rec = edge_by_pair[frozenset((a, b))]
    tf = rec["_transform"]
    if tf is None:
        raise SystemExit(f"no transform on edge {rec['edge']}")
    if rec["src"] == a and rec["dst"] == b:
        return tf, False
    if rec["src"] == b and rec["dst"] == a:
        return tf.inverse(), True
    raise SystemExit(f"edge {rec['edge']} does not relate {a} and {b}")


def run_triplet(window: str, tri: tuple, edge_by_pair: dict) -> dict:
    a, b, c = tri
    legs, inverted = [], []
    for x, y in ((a, b), (b, c), (c, a)):
        tf, inv = directed(edge_by_pair, x, y)
        legs.append(tf)
        inverted.append(inv)

    shape = tuple(int(v) for v in edge_by_pair[frozenset((a, b))]["shape_src_rotated"])
    residual = float(loop_closure(legs, shape))

    edges = [edge_by_pair[frozenset(p)] for p in ((a, b), (b, c), (a, c))]
    min_inliers = min(int(e["n_inliers"]) for e in edges)

    verdicts = []
    for e in edges:
        v = assess(transform=e["_transform"],
                   src_points=e["_src_points"], dst_points=e["_dst_points"],
                   inlier_mask=e["_inlier_mask"],
                   shape=tuple(int(s) for s in e["shape_src_rotated"]),
                   fit_rmse=e["fit_rmse_px"],
                   loop_error_px=residual)
        verdicts.append({"edge": e["edge"], "verdict": v.as_dict()})

    return {
        "window": window,
        "frames": list(tri),
        "cycle": [f"{a} -> {b}", f"{b} -> {c}", f"{c} -> {a}"],
        "inverted_leg": inverted,
        "shape_used": list(shape),
        "loop_closure_residual_px": residual,
        "min_edge_inliers": min_inliers,
        "edge_inliers": {e["edge"]: int(e["n_inliers"]) for e in edges},
        "edge_geometry_recorded": {e["edge"]: e["geometry_verdict_recorded"] for e in edges},
        "verdicts": verdicts,
        "statuses": [v["verdict"]["status"] for v in verdicts],
        "any_verified": any(v["verdict"]["status"] == "VERIFIED" for v in verdicts),
    }


def spearman(x: list[float], y: list[float]) -> tuple[float, int]:
    """Spearman rho by rank-Pearson. Returns (rho, n); ties averaged."""
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(x), ranks(y)
    n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return (num / den if den else float("nan")), n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control-only", action="store_true",
                    help="run S4 and S5 only; compute no residual")
    ap.add_argument("--out", default="exp012_results.json")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / args.out
    if out_path.exists():
        raise SystemExit(f"{out_path.relative_to(ROOT)} exists (integrity rule 4)")

    t_start = time.time()

    # ---- S4 first: nothing else means anything if composition is wrong ----
    s4 = run_s4()
    print(f"S4 control: recorded {s4['recorded_px']:.10f} px, "
          f"recomputed {s4['recomputed_px']:.10f} px, "
          f"{'MET' if s4['met'] else 'NOT MET'}", flush=True)
    if not s4["met"]:
        raise SystemExit("S4 NOT MET: composition does not reproduce REAL-DATA-03's "
                         "recorded loop residual. Stage stops (Part 1 §4).")

    products = _e7.GEOMETRY_FILES + ["real_data_07_index_geometry.json"]
    prod: dict = {}
    for name in products:
        p = DATA / "manifests" / name
        if p.exists():
            prod.update(json.loads(p.read_text(encoding="utf-8"))["products"])

    all_triplets, all_edges, results = [], [], []
    for window in ("RD03", "RD04"):
        tris = triplets(window)
        print(f"\n{window}: {len(tris)} admissible triplets", flush=True)
        if not tris:
            continue
        man = json.loads((DATA / "manifests" / WINDOWS[window]).read_text(encoding="utf-8"))
        target = tuple(man["target_ground_point_lon_lat"])
        ctx = {t["pdsid"]: _e7.FrameContext(t["pdsid"], t, prod, target)
               for t in man["tiles"]}
        rec_by_pair = recorded_successes(window)

        needed = {frozenset(p) for tri in tris
                  for p in itertools.combinations(tri, 2)}
        edge_by_pair: dict[frozenset, dict] = {}
        for i, pair in enumerate(sorted(needed, key=lambda s: sorted(s)), 1):
            recorded = rec_by_pair[pair]
            src, dst = edge_direction(recorded)
            e = rematch(ctx, src, dst, recorded)
            edge_by_pair[pair] = e
            all_edges.append({k: v for k, v in e.items() if not k.startswith("_")})
            print(f"  S5 edge {i}/{len(needed)} {src[-12:]}->{dst[-12:]}: "
                  f"{e['n_inliers']} inliers (recorded {e['n_inliers_recorded']}) "
                  f"[{e['wall_s']}s]", flush=True)

        if args.control_only:
            for f in ctx.values():
                f.release()
            continue

        for tri in tris:
            r = run_triplet(window, tri, edge_by_pair)
            results.append(r)
            all_triplets.append(tri)
            print(f"  LOOP {'+'.join(f[-8:] for f in tri)}: "
                  f"{r['loop_closure_residual_px']:.4f} px -> "
                  f"{','.join(sorted(set(r['statuses'])))}", flush=True)
        for f in ctx.values():
            f.release()

    doc = {
        "stage": STAGE,
        "part": "Part 2 artefact",
        "preregistration": "docs/stages/EXP-012_verdict_calibration.md (frozen "
                           "2026-09-20, amendment A1 recorded before any residual)",
        "engine": ENGINE,
        "base": BASE,
        "orientation": "north_up_east_right",
        "s4_control": s4,
        "s5_control": {
            "criterion": "S5",
            "met": all(e["reproduces_recorded"] for e in all_edges),
            "n_edges": len(all_edges),
            "note": "every re-matched edge reproduced its recorded n_inliers exactly",
        },
        "n_triplets": len(results),
        "triplets": results,
        "edges": all_edges,
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
        "total_runtime_s": round(time.time() - t_start, 1),
        "claims_not_supported": [
            "No ground truth; the loop residual is a self-consistency bound.",
            "Loop closure is exactly invariant to per-image gauge error "
            "(ADR-0011 N1): a closing loop verifies the transform set only up "
            "to per-image gauge, and is NOT a claim of absolute accuracy.",
            "Triplets share frames and edges; they are not independent samples.",
            "One region (Mare Serenitatis), one instrument (LRO NAC). "
            "Nothing here is a Chandrayaan-2 result.",
        ],
    }

    if results:
        rho, n = spearman([r["min_edge_inliers"] for r in results],
                          [r["loop_closure_residual_px"] for r in results])
        verified = [r for r in results if r["any_verified"]]
        doc["criteria"] = {
            "S1_verified_reachable": {
                "met": bool(verified),
                "n_triplets_with_a_verified_edge": len(verified),
                "n_triplets": len(results),
                "triplets_verified": [r["frames"] for r in verified],
            },
            "S2_residual_tracks_edge_quality": {
                "spearman_rho": rho, "n": n,
                "note": "p-value not computed here; n = 13 and triplets share "
                        "edges, so this is reported as a descriptive statistic",
            },
        }
        print(f"\nS1: {len(verified)} of {len(results)} triplets have a VERIFIED edge")
        print(f"S2: Spearman rho = {rho:.4f} (n = {n})")

    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"\nwrote {out_path.relative_to(ROOT)} in {doc['total_runtime_s']}s")


if __name__ == "__main__":
    main()
