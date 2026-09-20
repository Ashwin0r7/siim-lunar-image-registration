"""REAL-DATA-09 — loop closure over {TMC-2 ortho, NAC A, NAC D}.

Part 1 §5, last sentence: *"Where three products cover one ground point
(OHRC, TMC-2, NAC), loop closure is computed and reported."* Both TMC-2 edges
registered in the RD04-long window (A: 29 inliers, D: 70, both CONSISTENT) and
the A<->D edge is a recorded NAC success, so the triplet closes on ground all
three products see.

All three edges are estimated **independently**, in the same frame: the RD04-long
tiles degraded to the TMC-2 GSD and oriented north-up-east-right. The A<->D leg
is therefore re-estimated in that frame rather than reused from REAL-DATA-04 at
native scale -- mixing frames would compose transforms that do not belong to one
another. E-021 is the reason the closing edge is never derived from the other two.

    python scripts/run_real_data_09_loop.py
"""

from __future__ import annotations

import glob
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.baselines import run_baseline  # noqa: E402
from siim.demo.verdict import assess  # noqa: E402
from siim.evaluation.gtfree import loop_closure  # noqa: E402
from siim.geometry import Transform  # noqa: E402
from siim.ingest.geotiff import decode_window, place  # noqa: E402
from siim.ingest.lola_dem import _lonlat_grid  # noqa: E402
from siim.ingest.orientation import north_up_east_right  # noqa: E402
from siim.preprocessing.degrade import degrade_to_gsd  # noqa: E402

_spec = importlib.util.spec_from_file_location("_exp007", ROOT / "scripts" / "run_exp007.py")
_e7 = importlib.util.module_from_spec(_spec)
sys.modules["_exp007"] = _e7
_spec.loader.exec_module(_e7)

DATA = ROOT / "data"
OUT = ROOT / "experiments" / "REAL-DATA-09"
BASE = {"model": "affine", "ransac_threshold_px": 3.0, "seed": 0}
MANIFEST = DATA / "manifests" / "chandrayaan2_manifest.json"
NAC_MANIFEST = "exp007_long_triplet_abd_manifest.json"
FRAME_A = "nac.m1271742202lc"
FRAME_D = "nac.m1299958135lc"
ENGINE = "b1"


def nac_products() -> dict:
    prod: dict = {}
    for p in glob.glob(str(DATA / "manifests" / "*.json")):
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and isinstance(d.get("products"), dict):
            prod.update(d["products"])
    return prod


def degraded_northup(ctx, ref_gsd_m: float):
    """NAC tile degraded to the TMC-2 GSD and oriented north-up-east-right."""
    k = ctx.tile.get("decimation", 2)
    factor = max(1, int(round(ref_gsd_m / (k * ctx.scaled_pixel_m))))
    img = ctx.img(k)
    deg = degrade_to_gsd(img, factor, psf_fwhm_coarse_px=1.0) if factor > 1 else img
    t = ctx.tile
    nu = north_up_east_right(_e7.stretch(deg), ctx.corners,
                             line=t["line0"] + (t["n_lines"] - 1) / 2,
                             sample=t["sample0"] + (t["n_samples"] - 1) / 2)
    return nu, factor


def tmc_crop(ctx, factor: int, probe, tif, geo, margin=60):
    """The TMC-2 ortho window under a NAC footprint, and the crop origin."""
    k = ctx.tile.get("decimation", 2)
    w = ctx.window(k)
    h, wd = w.shape
    gy, gx = np.mgrid[0:h:max(1, h // 8), 0:wd:max(1, wd // 8)]
    pts = np.column_stack([gx.ravel(), gy.ravel()]).astype(float)
    lines = np.array([w.to_frame(y, x)[0] for x, y in pts])
    samples = np.array([w.to_frame(y, x)[1] for x, y in pts])
    lon, lat = _lonlat_grid(ctx.corners, lines, samples)
    xy = probe.block_xy_of_lonlat(lon, lat)
    x0 = max(0, int(np.floor(xy[:, 0].min())) - margin)
    y0 = max(0, int(np.floor(xy[:, 1].min())) - margin)
    x1 = min(int(geo.shape[1]), int(np.ceil(xy[:, 0].max())) + margin + 1)
    y1 = min(int(geo.shape[0]), int(np.ceil(xy[:, 1].max())) + margin + 1)
    return decode_window(tif, y0, y1, x0, x1), (x0, y0, x1, y1)


def match(src, dst, label):
    t0 = time.perf_counter()
    res = run_baseline("B1", src, dst, model=BASE["model"],
                       ransac_threshold=BASE["ransac_threshold_px"], seed=BASE["seed"])
    mask = (np.asarray(res.inlier_mask, bool) if np.size(res.inlier_mask)
            else np.zeros(0, bool))
    n = int(mask.sum())
    print(f"  {label:34s} inliers={n:6d}  ({time.perf_counter()-t0:.0f}s)", flush=True)
    return res, mask, n


def main() -> None:
    out_path = OUT / "real_data_09_loop_closure.json"
    if out_path.exists():
        raise SystemExit(f"{out_path.relative_to(ROOT)} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    man_c2 = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ortho = next(r for r in man_c2["products"].values()
                 if r["instrument"] == "TMC-2" and r["kind"] == "ortho")
    tif = ROOT / ortho["data_file"]
    from siim.ingest.geotiff import read_geometry
    geo = read_geometry(tif)
    probe = place(tif, row0=0, row1=2, col0=0, col1=2, name="probe")
    ref_gsd = float(np.mean(probe.metres_per_pixel))

    man = json.loads((DATA / "manifests" / NAC_MANIFEST).read_text(encoding="utf-8"))
    target = tuple(man["target_ground_point_lon_lat"])
    prod = nac_products()
    ctx = {t["pdsid"]: _e7.FrameContext(t["pdsid"], t, prod, target)
           for t in man["tiles"] if t["pdsid"] in (FRAME_A, FRAME_D)}
    if len(ctx) != 2:
        raise SystemExit(f"need both {FRAME_A} and {FRAME_D} in {NAC_MANIFEST}")

    print(f"TMC-2 GSD {ref_gsd:.3f} m; degrading both NAC tiles to it\n")
    nuA, fA = degraded_northup(ctx[FRAME_A], ref_gsd)
    nuD, fD = degraded_northup(ctx[FRAME_D], ref_gsd)
    cropA, boxA = tmc_crop(ctx[FRAME_A], fA, probe, tif, geo)
    srcA = _e7.stretch(cropA)

    # Three independent estimates, all in the degraded north-up frame.
    resTA, mTA, nTA = match(srcA, nuA.image, "TMC-2 -> NAC A")
    resAD, mAD, nAD = match(nuA.image, nuD.image, "NAC A -> NAC D")
    resDT, mDT, nDT = match(nuD.image, srcA, "NAC D -> TMC-2")

    edges = [("TMC-2 -> NAC A", resTA, nTA), ("NAC A -> NAC D", resAD, nAD),
             ("NAC D -> TMC-2", resDT, nDT)]
    rows = [{"edge": e, "n_inliers": n,
             "pass": bool(n > _e7.N_INLIERS_FAILURE_RULE),
             "fit_rmse_px": float(r.ransac.inlier_rmse),
             "transform_matrix": (np.asarray(r.transform.matrix).tolist()
                                  if r.transform is not None else None)}
            for e, r, n in edges]

    doc = {
        "stage": "REAL-DATA-09",
        "what": "loop closure over {TMC-2 ortho, NAC A, NAC D} (Part 1 §5)",
        "frame": "RD04-long tiles degraded to the TMC-2 GSD, north-up-east-right",
        "tmc2_gsd_m": round(ref_gsd, 4),
        "degrade_factors": {FRAME_A: fA, FRAME_D: fD},
        "tmc2_block_used": list(boxA),
        "engine": "B1 (unmodified RootSIFT)",
        "base": BASE,
        "edge_independence": (
            "Each edge was estimated by a separate run of the baseline on its "
            "own image pair. The closing edge was NOT derived as "
            "(T_AD o T_TA)^-1; that derivation is E-021 and manufactures a "
            "zero residual."),
        "edges": rows,
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
    }

    if all(r["transform_matrix"] is not None for r in rows):
        legs = [Transform(np.array(r["transform_matrix"], float), "affine")
                for r in rows]
        residual = float(loop_closure(legs, srcA.shape))
        doc["loop_closure_residual_px"] = residual
        doc["loop_closure_residual_m"] = residual * ref_gsd
        doc["shape_used"] = list(srcA.shape)
        print(f"\n  loop closure residual: {residual:.4f} px "
              f"({residual * ref_gsd:.1f} m at {ref_gsd:.2f} m/px)")
        v = assess(transform=resTA.transform,
                   src_points=resTA.matches.src_points,
                   dst_points=resTA.matches.dst_points,
                   inlier_mask=mTA, shape=srcA.shape,
                   fit_rmse=float(resTA.ransac.inlier_rmse),
                   loop_error_px=residual)
        doc["verdict_tmc2_to_nac_a"] = v.as_dict()
        print(f"  verdict on TMC-2 -> NAC A: {v.status} / {v.confidence}")
    else:
        doc["loop_closure_residual_px"] = None
        doc["note"] = "at least one edge produced no transform; no loop computed"
        print("\n  at least one edge produced no transform; no loop computed")

    doc["claims_not_supported"] = [
        "No ground truth; loop closure is a self-consistency bound.",
        "Loop closure is exactly invariant to per-image gauge error "
        "(ADR-0011 N1): it verifies the transform set only up to that gauge.",
        "One triplet, one region, one TMC-2 strip. No significance claim.",
    ]
    doc["total_runtime_s"] = round(time.time() - t_start, 1)
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    for f in ctx.values():
        f.release()
    print(f"\nwrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
