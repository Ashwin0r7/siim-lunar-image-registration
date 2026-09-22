"""EXP-019 — the controlled reference, run exactly as Part 1 froze it
(docs/stages/EXP-019_controlled_reference.md, commit 9cc9c13).

Every REAL-DATA-07 tile of both windows, plus the Chandrayaan-2 TMC-2 ortho
block of REAL-DATA-09 pair P1, is degraded to the SELENE (Kaguya) TC seamless
ortho's 8.42 m pixel through the R9 operator, oriented, and registered to that
reference with the frozen pipeline. What comes out is, per frame, a ground map
that does not pass through its own archive corners -- and with it:

    S1  does an independently controlled product register at all
    S2  how far the archive's answer is from another mission's, in metres
    S3  SS2.2's sub-pixel row on check points that do not pass through the
        estimate being checked (A -> R -> B against the recorded A -> B)
    S4  EXP-013's H3: are the per-frame terms the archive or the estimate
    S5  a Chandrayaan-2 triangle through an independent mission
    S6  the same sources against a disjoint block of the same product

Nothing is re-implemented: degradation is siim.preprocessing.degrade_to_gsd,
orientation is siim.ingest.orientation.north_up_east_right through the tile's
corner geometry, registration is siim.pipeline.register_pair with its
defaults, the reference grid is siim.ingest.mapgrid.MapBlock, and the recorded
rows are read exactly where Part 1 section 3.3 says.

    python scripts/run_exp019.py
    python scripts/run_exp019.py --quick --out <scratch>   # smoke only
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

import cv2  # noqa: E402

from siim.evaluation.coverage import coverage_metrics  # noqa: E402
from siim.geometry import Transform, endpoint_error, estimate, pixel_grid  # noqa: E402
from siim.ingest.footprint import TileWindow  # noqa: E402
from siim.ingest.geotiff import decode_window, place  # noqa: E402
from siim.ingest.mapgrid import load_map_block  # noqa: E402
from siim.ingest.orientation import handedness, north_up_east_right  # noqa: E402
from siim.pipeline import register_pair  # noqa: E402
from siim.preprocessing.degrade import degrade_to_gsd  # noqa: E402


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_e7 = _load("_exp007", "scripts/run_exp007.py")
_rd7 = _load("_rd07", "scripts/run_real_data_07.py")
_rd9 = _load("_rd09", "scripts/run_real_data_09.py")

STAGE = "EXP-019"
DATA = ROOT / "data"
OUT = ROOT / "experiments" / STAGE
BASE = {"model": "affine", "ransac_threshold_px": 3.0, "seed": 0}
RULE = _e7.N_INLIERS_FAILURE_RULE                      # n_inliers <= 8 fails (D-023)
ENGINE = "B1"
SECOND_ENGINE = "B4L"                                  # beside every criterion

REF_MANIFEST = "exp019_tc_ortho_ref_block.json"
NULL_MANIFEST = "exp019_tc_ortho_null_block.json"
REF_GSD_M = 8.42315289562
PSF = 1.0
MARGIN_M = 2000.0                                      # Part 1 section 2.2 step 3
K2 = 2                                                 # the decimation every recorded row used

# --- frozen constants, Part 1 section 4 -----------------------------------
GRID_STEP = 64                                         # D_f / A_f grid (section 2.2)
S3_GRID_STEP = 8
S1_MIN_NAC = 8
S2_MIN_FRAMES = 6
S2_MEDIAN_BOUND_M = 300.0
S3_MIN_PAIRS = 5
S3_BOUND_REF_PX = 0.5
S4_MIN_FRAMES = 8
S4_R_MIN = 0.7
S4_MEDIAN_DIFF_FRACTION = 0.30
S4_N_PERM = 1000
S5_BOUND_REF_PX = 2.0
S6_N_EXPECTED = 21
N_BOOT = 1000
BOOT_SEED = 19
SELF_SHIFT_PX = 7
SELF_SHIFT_TOL_PX = 0.05
GRID_GATE_TOL_PX = 0.5
ROUNDTRIP_TOL_DEG = 1e-9

# Part 1 section 3.2: k = round(8.42315289562 / g), frozen per frame.
K_FRAME = {
    "nac.m1271742202lc": 9, "nac.m1335207975rc": 9, "nac.m1452560468lc": 10,
    "nac.m1182331886lc": 7, "nac.m1236465772rc": 7, "nac.m1212932972lc": 8,
    "nac.m1205872034rc": 8, "nac.m1175268993rc": 7, "nac.m1363396554rc": 8,
    "nac.m1199981485rc": 8, "nac.m1096350825rc": 6, "nac.m1142297886lc": 7,
    "nac.m1299958135lc": 8, "nac.m1315225542lc": 10, "nac.m1341069775rc": 9,
}
TMC2_K = 2
TMC2_BLOCK = [1637, 56766, 2135, 57597]                # Part 1 section 3.2 (REAL-DATA-09 P1)
EXP013_FIXED_NODE = {"RD03": "nac.m1182331886lc", "RD04": "nac.m1212932972lc"}
S0_REPRODUCTION_EDGES = [                              # (window, edge) -> recorded n_inliers
    ("RD03", "nac.m1271742202lc -> nac.m1182331886lc"),
    ("RD03", "nac.m1182331886lc -> nac.m1212932972lc"),
    ("RD04", "nac.m1299958135lc -> nac.m1271742202lc"),
]
# The recorded REAL-DATA-09 direct edge S5 composes through (B1, passing).
S5_RD09 = {"window": "RD03-long", "frame": "nac.m1271742202lc", "engine": "b1"}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _aff(fn, shape_xy, name: str) -> tuple[Transform, float]:
    """Fit the affine that ``fn`` IS (every step in these chains is affine).

    Returns the transform and the maximum residual of the fit, which the
    artefact records: a residual above 1e-6 px would mean a step in the chain
    is not affine and the composition is not exact.
    """
    w, h = shape_xy
    gx, gy = np.meshgrid(np.linspace(0, w - 1, 5), np.linspace(0, h - 1, 5))
    pts = np.column_stack([gx.ravel(), gy.ravel()]).astype(float)
    out = np.asarray(fn(pts), float)
    res = estimate(pts, out, "affine")
    if not res.ok:
        raise RuntimeError(f"{name}: affine fit failed")
    resid = float(np.abs(res.transform.apply(pts) - out).max())
    return res.transform, resid


def _tile_px_to_frame(win: TileWindow) -> Transform:
    """Decimated tile (x, y) -> frame (sample, line), as an exact affine."""
    k = float(win.decimation)
    off = (k - 1) / 2.0
    m = np.array([[k, 0.0, win.sample0 + off],
                  [0.0, k, win.line0 + off],
                  [0.0, 0.0, 1.0]], float)
    return Transform(m, "affine")


def _lonlat(corners, xy_frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Frame (sample, line) pairs -> (lon, lat) through the corner map."""
    out = np.array([corners.lonlat_at(float(line), float(sample))
                    for sample, line in np.asarray(xy_frame, float)], float)
    return out[:, 0], out[:, 1]


def _metres_per_deg(lat_deg: float) -> tuple[float, float]:
    r = 1737400.0
    return (np.pi / 180.0 * r * np.cos(np.radians(lat_deg)), np.pi / 180.0 * r)


def _similarity_fit(src: np.ndarray, dst: np.ndarray) -> Transform | None:
    res = estimate(src, dst, "similarity")
    return res.transform if res.ok else None


def _bootstrap_ci(values: np.ndarray, rng, n: int = N_BOOT) -> list[float]:
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if v.size < 2:
        return [float("nan"), float("nan")]
    draws = np.median(rng.choice(v, size=(n, v.size), replace=True), axis=1)
    return [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))]


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.size < 3 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    def rank(v):
        order = np.argsort(np.argsort(np.asarray(v, float)))
        return order.astype(float)
    return _pearson(rank(a), rank(b))


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------
class Source:
    """One thing to register against the reference."""

    def __init__(self, key: str, window: str, name: str, kind: str):
        self.key, self.window, self.name, self.kind = key, window, name, kind
        self.ctx = None
        self.k = 1
        self.image = None            # matched image (oriented, stretched)
        self.to_ref = None           # Transform: matching-image px -> ref block px (measured)
        self.pred_to_ref = None      # Transform: matching-image px -> ref block px (archive prediction)
        self.k2_to_ref = None        # Transform: k=2 tile px -> ref block px (measured)
        self.record: dict = {}


def nac_sources() -> list[Source]:
    products = _rd7.load_products()
    out = []
    for window, mname in _rd7.WINDOWS.items():
        man = json.loads((DATA / "manifests" / mname).read_text(encoding="utf-8"))
        target = tuple(man["target_ground_point_lon_lat"])
        for t in man["tiles"]:
            s = Source(f"{window}/{t['pdsid']}", window, t["pdsid"], "NAC")
            s.ctx = _e7.FrameContext(t["pdsid"], t, products, target)
            s.k = K_FRAME[t["pdsid"]]
            out.append(s)
    return out


def prepare_nac(s: Source) -> dict:
    """Degrade to the reference GSD, orient, and record what was done."""
    t = s.ctx.tile
    raw = s.ctx.raw()
    deg = degrade_to_gsd(raw, s.k, psf_fwhm_coarse_px=PSF)
    img = _e7.stretch(deg)
    line_c = t["line0"] + (t["n_lines"] - 1) / 2
    sample_c = t["sample0"] + (t["n_samples"] - 1) / 2
    nu = north_up_east_right(img, s.ctx.corners, line=line_c, sample=sample_c)
    s.image = nu.image
    s._nu = nu
    s._win = TileWindow(t["line0"], t["sample0"], t["n_lines"], t["n_samples"], s.k)
    s.ctx.release()
    return {"k": s.k, "native_gsd_m": s.ctx.scaled_pixel_m,
            "coarse_gsd_m": s.k * s.ctx.scaled_pixel_m,
            "gsd_mismatch_pct": 100.0 * (s.k * s.ctx.scaled_pixel_m - REF_GSD_M) / REF_GSD_M,
            "incidence_deg": s.ctx.incidence_published,
            "delta_to_standard_geometry_deg": abs(s.ctx.incidence_published - 30.0),
            "shape": list(s.image.shape),
            "handedness_det": float(handedness(s.ctx.corners, line_c, sample_c)),
            "orientation": nu.record}


def nac_matching_px_to_frame(s: Source) -> Transform:
    """Matching-image (oriented, degraded) px -> frame (sample, line)."""
    return _tile_px_to_frame(s._win) @ s._nu.inverse


def tmc2_source() -> tuple[Source, dict]:
    prods = _rd9.tmc_products()
    rec = prods["TMC-2:ortho"]
    tif = ROOT / rec["data_file"].replace("\\", "/")
    x0, y0, x1, y1 = TMC2_BLOCK
    blk = place(tif, row0=y0, row1=y1, col0=x0, col1=x1, name="tmc2-exp019")
    crop = decode_window(tif, y0, y1, x0, x1).astype(np.float64)
    crop = np.where(crop > 0, crop, np.nan)
    deg = degrade_to_gsd(crop, TMC2_K, psf_fwhm_coarse_px=PSF)
    s = Source("C2/TMC-2", "RD09-P1", rec["product_id"], "TMC-2")
    s.image = _e7.stretch(deg)
    s.k = TMC2_K
    s._blk = blk
    s._block_xy = TMC2_BLOCK
    gsd = float(np.mean(blk.metres_per_pixel))
    meta = {"product_id": rec["product_id"], "block": TMC2_BLOCK, "k": TMC2_K,
            "native_gsd_m": gsd, "coarse_gsd_m": TMC2_K * gsd,
            "gsd_mismatch_pct": 100.0 * (TMC2_K * gsd - REF_GSD_M) / REF_GSD_M,
            "valid_fraction": float(np.isfinite(crop).mean()),
            "shape": list(s.image.shape),
            "incidence_deg": _rd9.TMC_INCIDENCE,
            "delta_to_standard_geometry_deg": abs(_rd9.TMC_INCIDENCE - 30.0),
            "orientation": "none applied: the product is map-projected; its own geometry "
                           "carries north, and the predicted affine's determinant is recorded"}
    return s, meta


def tmc2_matching_px_to_lonlat(s: Source, pts: np.ndarray) -> np.ndarray:
    """Matching-image px (degraded by TMC2_K) -> (lon, lat)."""
    p = np.asarray(pts, float) * TMC2_K + (TMC2_K - 1) / 2.0
    lon, lat = s._blk.lonlat_of_block_xy(p[:, 0], p[:, 1])
    return np.column_stack([np.asarray(lon, float).ravel(), np.asarray(lat, float).ravel()])


# ---------------------------------------------------------------------------
# registration against a block
# ---------------------------------------------------------------------------
def predicted_map(s: Source, block) -> tuple[Transform | None, float]:
    """Matching-image px -> block px, from archive geometry alone."""
    h, w = s.image.shape
    gx, gy = np.meshgrid(np.linspace(0, w - 1, 7), np.linspace(0, h - 1, 7))
    pts = np.column_stack([gx.ravel(), gy.ravel()]).astype(float)
    if s.kind == "NAC":
        frame_xy = nac_matching_px_to_frame(s).apply(pts)
        lon, lat = _lonlat(s.ctx.corners, frame_xy)
        lonlat = np.column_stack([lon, lat])
    else:
        lonlat = tmc2_matching_px_to_lonlat(s, pts)
    xy = block.block_xy_of_lonlat(lonlat[:, 0], lonlat[:, 1])
    res = estimate(pts, xy, "affine")
    if not res.ok:
        return None, float("nan")
    resid = float(np.abs(res.transform.apply(pts) - xy).max())
    return res.transform, resid


def crop_for(pred: Transform, s: Source, block, margin_px: int):
    h, w = s.image.shape
    corners = pred.apply(np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], float))
    x0 = int(np.floor(corners[:, 0].min())) - margin_px
    y0 = int(np.floor(corners[:, 1].min())) - margin_px
    x1 = int(np.ceil(corners[:, 0].max())) + margin_px + 1
    y1 = int(np.ceil(corners[:, 1].max())) + margin_px + 1
    H, W = block.data.shape
    xc0, yc0 = max(0, x0), max(0, y0)
    xc1, yc1 = min(W, x1), min(H, y1)
    if xc1 - xc0 < 32 or yc1 - yc0 < 32:
        return None, (x0, y0, x1, y1), (xc0, yc0, xc1, yc1)
    return block.data[yc0:yc1, xc0:xc1], (x0, y0, x1, y1), (xc0, yc0, xc1, yc1)


def register_against(s: Source, block, *, margin_px: int, engine: str,
                     crop_override=None) -> dict:
    """One cell: source -> block. Returns the record; nothing is graded here."""
    t0 = time.perf_counter()
    pred, pred_resid = predicted_map(s, block)
    rec: dict = {"source": s.key, "kind": s.kind, "engine": engine,
                 "predicted_affine_residual_px": pred_resid}
    if pred is None:
        return dict(rec, excluded="archive geometry does not predict a footprint")
    if crop_override is None:
        crop, want, got = crop_for(pred, s, block, margin_px)
    else:
        crop, want, got = crop_override
    rec["crop_requested"] = list(want)
    rec["crop_taken"] = list(got)
    if crop is None or not np.isfinite(crop).any():
        return dict(rec, excluded="no reference coverage under the predicted footprint")
    det = float(np.linalg.det(np.asarray(pred.matrix)[:2, :2]))
    rec["predicted_jacobian_det"] = det
    rec["predicted_mirrored"] = bool(det < 0)
    src_img = s.image
    flip = det < 0
    if flip:                                   # both products are proper maps; a negative
        src_img = np.ascontiguousarray(np.fliplr(src_img))   # determinant means one is mirrored
    rec["source_flipped_lr"] = bool(flip)
    ref_img = _e7.stretch(crop)
    rec["src_shape"] = list(src_img.shape)
    rec["ref_shape"] = list(ref_img.shape)
    rec["ref_valid_fraction"] = float(np.isfinite(crop).mean())
    res = register_pair(src_img, ref_img, engine=engine, model=BASE["model"],
                        ransac_threshold=BASE["ransac_threshold_px"], seed=BASE["seed"])
    mask = np.asarray(res.inlier_mask, bool)
    n_in = int(mask.sum())
    rec.update({
        "n_putative": int(res.src_points.shape[0]),
        "n_inliers": n_in,
        "n_refined": int(np.asarray(res.refined_mask, bool).sum()),
        "pass": bool(n_in > RULE),
        "fit_rmse_px": (float(res.baseline.ransac.inlier_rmse)
                        if res.baseline.ransac is not None else None),
        "fit_rmse_is_not_accuracy": True,
        "model_selected_by": res.model_selected_by,
        "verdict": {"status": res.verdict.status, "confidence": res.verdict.confidence,
                    "reasons": list(res.verdict.reasons)[:4]},
        "transform_matrix": (np.asarray(res.transform.matrix).tolist()
                             if res.transform is not None else None),
        "wall_s": round(time.perf_counter() - t0, 2),
    })
    if n_in >= 3:
        cov = coverage_metrics(res.src_points[mask], src_img.shape)
        rec["coverage_occupancy"] = float(cov.grid_occupancy)
        rec["coverage_max_uncovered_disc_ratio"] = float(cov.max_uncovered_disc_ratio)
    if res.transform is not None:
        # measured map: matching px -> block px (undo the flip, add the crop origin)
        w = src_img.shape[1]
        flip_tf = Transform(np.array([[-1.0, 0.0, w - 1.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
                            "euclidean") if flip else Transform(np.eye(3), "euclidean")
        shift = Transform(np.array([[1.0, 0.0, got[0]], [0.0, 1.0, got[1]], [0.0, 0.0, 1.0]]),
                          "euclidean")
        measured = shift @ res.transform @ flip_tf
        rec["measured_to_block_matrix"] = np.asarray(measured.matrix).tolist()
        pm = np.asarray(measured.matrix)[:2, :2]
        rec["recovered_scale"] = float(np.sqrt(abs(np.linalg.det(pm))))
        rec["predicted_scale"] = float(np.sqrt(abs(det)))
        rec["_measured"] = measured
        rec["_pred"] = pred
    return rec


# ---------------------------------------------------------------------------
# S0 gates
# ---------------------------------------------------------------------------
def s0_grid_gate(block, manifest_name: str) -> dict:
    man = json.loads((DATA / "manifests" / manifest_name).read_text(encoding="utf-8"))
    summ = man["label_summary_vs_offsets"]
    ppd = block.ppd_lat
    lat_top, lon_left = block.lat_top_deg, block.lon_left_deg
    corner_err_px = {
        "MAXIMUM_LATITUDE": abs(block.line_of_lat(summ["MAXIMUM_LATITUDE"]) - 0.0),
        "MINIMUM_LATITUDE": abs(block.line_of_lat(summ["MINIMUM_LATITUDE"]) - 10799.0),
        "WESTERNMOST_LONGITUDE": abs(block.sample_of_lon(summ["WESTERNMOST_LONGITUDE"]) - 0.0),
        "EASTERNMOST_LONGITUDE": abs(block.sample_of_lon(summ["EASTERNMOST_LONGITUDE"]) - 10799.0),
    }
    rng = np.random.default_rng(0)
    lon = rng.uniform(man["window_lon"][0], man["window_lon"][1], 10000)
    lat = rng.uniform(man["window_lat"][0], man["window_lat"][1], 10000)
    xy = block.block_xy_of_lonlat(lon, lat)
    lat2 = block.lat_of_line(xy[:, 1] + block.row0)
    lon2 = block.lon_of_sample(xy[:, 0] + block.col0)
    rt = float(max(np.abs(lat2 - lat).max(), np.abs(lon2 - lon).max()))
    met = max(corner_err_px.values()) < GRID_GATE_TOL_PX and rt < ROUNDTRIP_TOL_DEG
    return {"met": bool(met), "corner_error_px": {k: float(v) for k, v in corner_err_px.items()},
            "roundtrip_max_deg": rt, "ppd": ppd, "lat_top_deg": lat_top,
            "lon_left_deg": lon_left, "map_scale_m": man["grid"]["map_scale_m"],
            "block_shape": list(block.data.shape), "row0": block.row0, "col0": block.col0,
            "bytes_sha256": man["bytes_sha256"], "byte_start": man["byte_start"],
            "byte_count": man["byte_count"], "dummy_fraction": man["dn"]["dummy_fraction"],
            "label_summary_vs_offsets_px": summ["summary_vs_offsets_px"]}


def s0_reproduction() -> dict:
    """Three recorded RD-07 B1 north-up edges, re-run unchanged."""
    products = _rd7.load_products()
    rows = recorded_rows()
    out = []
    for window, edge in S0_REPRODUCTION_EDGES:
        rec = rows[(window, edge)]
        man = json.loads((DATA / "manifests" / _rd7.WINDOWS[window]).read_text(encoding="utf-8"))
        target = tuple(man["target_ground_point_lon_lat"])
        tiles = {t["pdsid"]: t for t in man["tiles"]}
        s_name, d_name = edge.split(" -> ")
        fs = _e7.FrameContext(s_name, tiles[s_name], products, target)
        fr = _e7.FrameContext(d_name, tiles[d_name], products, target)
        got = _rd7.run_edge(fs, fr, "b1", True)
        fs.release(); fr.release()
        out.append({"window": window, "edge": edge, "recorded": rec["n_inliers"],
                    "rerun": got["n_inliers"],
                    "reproduces": bool(rec["n_inliers"] == got["n_inliers"])})
        print(f"  [S0 iii] {window} {edge[4:16]}->{edge[-13:]} {got['n_inliers']:5d} "
              f"recorded {rec['n_inliers']:5d} "
              f"{'REPRODUCES' if out[-1]['reproduces'] else 'DIFFERS'}", flush=True)
    return {"met": all(r["reproduces"] for r in out), "edges": out}


def s0_self_reference(block) -> dict:
    """The reference against itself, shifted by an integer number of its pixels."""
    d = block.data
    h, w = d.shape
    sub = d[: h // 2 * 2, : w // 2 * 2]
    a = sub[200:200 + 512, 200:200 + 512]
    b = sub[200:200 + 512, 200 + SELF_SHIFT_PX:200 + SELF_SHIFT_PX + 512]
    res = register_pair(_e7.stretch(a), _e7.stretch(b), engine=ENGINE, model=BASE["model"],
                        ransac_threshold=BASE["ransac_threshold_px"], seed=BASE["seed"])
    n_in = int(np.asarray(res.inlier_mask, bool).sum())
    if res.transform is None:
        return {"met": False, "n_inliers": n_in, "error_px": None,
                "note": "no transform recovered on the self-shift control"}
    truth = Transform(np.array([[1.0, 0.0, -float(SELF_SHIFT_PX)], [0.0, 1.0, 0.0],
                                [0.0, 0.0, 1.0]]), "euclidean")
    ee = endpoint_error(res.transform, truth, a.shape, step=16)
    return {"met": bool(n_in > RULE and ee.median < SELF_SHIFT_TOL_PX),
            "n_inliers": n_in, "error_px": float(ee.median), "max_px": float(ee.max),
            "shift_px": SELF_SHIFT_PX}


# ---------------------------------------------------------------------------
# recorded inputs
# ---------------------------------------------------------------------------
def recorded_rows() -> dict:
    out = {}
    for w in ("rd03", "rd04"):
        doc = json.loads((ROOT / "experiments" / "REAL-DATA-07" /
                          f"rows_{w}_nue.json").read_text(encoding="utf-8"))
        for r in doc["rows"]:
            if r.get("engine") == "b1" and r.get("north_up") is True:
                out[(w.upper(), r["edge"])] = r
    return out


def exp013_terms() -> dict:
    doc = json.loads((ROOT / "experiments" / "EXP-013" /
                      "exp013_results.json").read_text(encoding="utf-8"))
    g = doc["supplementary_census_graph"]
    return {w: {"per_node_px": g[w]["b1"]["per_node_px"],
                "fixed_node": g[w]["b1"]["fixed_node"],
                "residual_before_px": g[w]["b1"]["residual_before_px"],
                "explained_fraction": g[w]["b1"]["explained_fraction"]} for w in g}


def rd09_direct_row() -> dict | None:
    doc = json.loads((ROOT / "experiments" / "REAL-DATA-09" /
                      "real_data_09_results_b1.json").read_text(encoding="utf-8"))
    for r in doc["rows"]:
        if (r.get("window") == S5_RD09["window"] and r.get("frame") == S5_RD09["frame"]
                and r.get("engine") == S5_RD09["engine"] and r.get("pass")):
            return r
    return None


# ---------------------------------------------------------------------------
# the per-frame displacement field (section 2.2)
# ---------------------------------------------------------------------------
def displacement_field(s: Source, block) -> dict | None:
    """D_f on the k = 2 tile grid: measured position minus archive position."""
    if s.k2_to_ref is None or s.kind != "NAC":
        return None
    t = s.ctx.tile
    win2 = TileWindow(t["line0"], t["sample0"], t["n_lines"], t["n_samples"], K2)
    h, w = win2.shape
    grid = pixel_grid((h, w), step=GRID_STEP)
    frame_xy = _tile_px_to_frame(win2).apply(grid)
    lon, lat = _lonlat(s.ctx.corners, frame_xy)
    p_arch = block.block_xy_of_lonlat(lon, lat)
    p_meas = s.k2_to_ref.apply(grid)
    d_ref = p_meas - p_arch                                   # reference px
    mag_ref = np.hypot(d_ref[:, 0], d_ref[:, 1])
    lat_mid = float(np.median(lat))
    mpd_lon, mpd_lat = _metres_per_deg(lat_mid)
    # the same displacement in the frame's own k = 2 pixels, as a map x -> A_f(x)
    inv = s.k2_to_ref.inverse()
    a_pts = inv.apply(p_arch)
    a_fit = _similarity_fit(grid, a_pts)
    disp_tile = a_pts - grid
    return {
        "n_grid": int(len(grid)),
        "rms_ref_px": float(np.sqrt(np.mean(mag_ref ** 2))),
        "median_ref_px": float(np.median(mag_ref)),
        "p95_ref_px": float(np.percentile(mag_ref, 95)),
        "rms_m": float(np.sqrt(np.mean(mag_ref ** 2)) * REF_GSD_M),
        "median_m": float(np.median(mag_ref) * REF_GSD_M),
        "p95_m": float(np.percentile(mag_ref, 95) * REF_GSD_M),
        "mean_east_m": float(np.mean(d_ref[:, 0]) * REF_GSD_M),
        "mean_north_m": float(-np.mean(d_ref[:, 1]) * REF_GSD_M),
        "median_lonlat_deg": [float(np.median(lon)), lat_mid],
        "metres_per_deg": [mpd_lon, mpd_lat],
        "rms_tile_px_k2": float(np.sqrt(np.mean(np.sum(disp_tile ** 2, axis=1)))),
        "_grid": grid, "_a_fit": a_fit,
        "similarity_fit": None if a_fit is None else {
            "matrix": np.asarray(a_fit.matrix).tolist(),
            "translation_px_k2": [float(a_fit.matrix[0, 2]), float(a_fit.matrix[1, 2])],
            "scale": float(np.sqrt(abs(np.linalg.det(np.asarray(a_fit.matrix)[:2, :2])))),
            "rotation_deg": float(np.degrees(np.arctan2(a_fit.matrix[1, 0], a_fit.matrix[0, 0]))),
            "residual_px_k2": float(np.sqrt(np.mean(np.sum(
                (a_fit.apply(grid) - a_pts) ** 2, axis=1)))),
        },
    }


# ---------------------------------------------------------------------------
# criteria
# ---------------------------------------------------------------------------
def evaluate(cells: dict, frames: dict, s0: dict, pairs: list, s4: dict, s5: dict,
             null_cells: list) -> dict:
    nac_pass = [k for k, c in cells.items() if c.get("kind") == "NAC" and c.get("pass")]
    tmc_pass = bool(cells.get("C2/TMC-2", {}).get("pass"))
    n_nac = len([c for c in cells.values() if c.get("kind") == "NAC"])
    s1 = {"met": bool(len(nac_pass) >= S1_MIN_NAC and tmc_pass),
          "n_nac_pass": len(nac_pass), "n_nac": n_nac, "tmc2_pass": tmc_pass,
          "bar": f">= {S1_MIN_NAC} of {n_nac} NAC tiles and the TMC-2 block",
          "passing": sorted(nac_pass),
          "by_delta_to_standard_geometry": [
              {"source": k, "delta_deg": frames[k]["delta_to_standard_geometry_deg"],
               "pass": bool(cells[k].get("pass")), "n_inliers": cells[k].get("n_inliers")}
              for k in sorted(cells, key=lambda x: frames.get(x, {}).get(
                  "delta_to_standard_geometry_deg", 0.0)) if k in frames]}

    d = {k: c["_field"] for k, c in cells.items() if c.get("_field")}
    med = [v["rms_m"] for v in d.values()]
    rng = np.random.default_rng(BOOT_SEED)
    s2 = {"met": bool(len(med) >= S2_MIN_FRAMES and float(np.median(med)) < S2_MEDIAN_BOUND_M),
          "n_frames": len(med), "bar_m": S2_MEDIAN_BOUND_M,
          "median_m": float(np.median(med)) if med else None,
          "median_ci95_m": _bootstrap_ci(np.array(med), rng) if med else None,
          "dispersion_p95_m": (float(np.percentile(np.abs(np.array(med) - np.median(med)), 95))
                               if med else None),
          "min_m": float(np.min(med)) if med else None,
          "max_m": float(np.max(med)) if med else None,
          "per_frame": {k: {"rms_m": v["rms_m"], "rms_ref_px": v["rms_ref_px"],
                            "rms_native_px": v["rms_m"] / frames[k]["native_gsd_m"],
                            "mean_east_m": v["mean_east_m"], "mean_north_m": v["mean_north_m"]}
                        for k, v in d.items()}}

    errs = [p["median_ref_px"] for p in pairs if p.get("median_ref_px") is not None]
    s3 = {"met": bool(len(errs) >= S3_MIN_PAIRS and float(np.median(errs)) < S3_BOUND_REF_PX),
          "n_pairs": len(errs), "bar_ref_px": S3_BOUND_REF_PX,
          "bar_m": S3_BOUND_REF_PX * REF_GSD_M,
          "median_ref_px": float(np.median(errs)) if errs else None,
          "median_m": float(np.median(errs)) * REF_GSD_M if errs else None,
          "median_ci95_ref_px": _bootstrap_ci(np.array(errs), rng) if errs else None,
          "p99_ref_px": float(np.percentile([p["p99_ref_px"] for p in pairs], 99)) if errs else None,
          "pairs": pairs}

    n_null_pass = sum(1 for c in null_cells if c.get("pass"))
    s6 = {"met": bool(n_null_pass == 0), "n_cells": len(null_cells),
          "n_pass": n_null_pass, "expected_cells": S6_N_EXPECTED,
          "false_accept_fraction": (n_null_pass / len(null_cells)) if null_cells else None,
          "passes": [{"source": c["source"], "n_inliers": c.get("n_inliers"),
                      "verdict": c.get("verdict", {}).get("status")}
                     for c in null_cells if c.get("pass")]}
    return {"S0": s0, "S1": s1, "S2": s2, "S3": s3, "S4": s4, "S5": s5, "S6": s6}


def s4_statistic(cells: dict, frames: dict, terms: dict) -> dict:
    """EXP-013's per-frame terms against the measured archive-vs-controlled offsets."""
    rows, per_window = [], {}
    for window, t in terms.items():
        fixed = t["fixed_node"]
        fkey = f"{window}/{fixed}"
        fixed_field = cells.get(fkey, {}).get("_field")
        if fixed_field is None or fixed_field.get("_a_fit") is None:
            per_window[window] = {"status": "fixed node has no measured field",
                                  "fixed_node": fixed}
            continue
        a_fix = fixed_field["_a_fit"]
        grid = fixed_field["_grid"]
        for name, value in t["per_node_px"].items():
            key = f"{window}/{name}"
            field = cells.get(key, {}).get("_field")
            if field is None or field.get("_a_fit") is None:
                rows.append({"window": window, "frame": name, "exp013_px": value,
                             "measured_px": None, "arm": cells.get(key, {}).get("arm"),
                             "excluded": "no measured field"})
                continue
            a_f = field["_a_fit"]
            m = float(np.sqrt(np.mean(np.sum((a_f.apply(grid) - a_fix.apply(grid)) ** 2, axis=1))))
            rows.append({"window": window, "frame": name, "exp013_px": value,
                         "measured_px": m, "arm": cells[key].get("arm", "R"),
                         "is_fixed_node": bool(name == fixed)})
        per_window[window] = {"fixed_node": fixed,
                              "n_used": sum(1 for r in rows if r["window"] == window
                                            and r.get("measured_px") is not None
                                            and not r.get("is_fixed_node"))}
    used = [r for r in rows if r.get("measured_px") is not None and not r.get("is_fixed_node")]
    used_r = [r for r in used if r.get("arm") == "R"]
    out = {"rows": rows, "per_window": per_window, "n_common_frames": len(used),
           "n_common_frames_arm_R_only": len(used_r),
           "bar": {"r_min": S4_R_MIN, "median_diff_fraction": S4_MEDIAN_DIFF_FRACTION,
                   "min_frames": S4_MIN_FRAMES}}
    for label, subset in (("pooled", used), ("arm_R_only", used_r)):
        if len(subset) < 3:
            out[label] = {"status": "too few frames"}
            continue
        a = np.array([r["exp013_px"] for r in subset], float)
        b = np.array([r["measured_px"] for r in subset], float)
        r_p, r_s = _pearson(a, b), _spearman(a, b)
        diff = np.abs(a - b)
        # null: permute the frame labels of the measured values WITHIN each window
        rng = np.random.default_rng(BOOT_SEED)
        windows = np.array([r["window"] for r in subset])
        null = []
        for _ in range(S4_N_PERM):
            bb = b.copy()
            for w in np.unique(windows):
                idx = np.flatnonzero(windows == w)
                bb[idx] = rng.permutation(b[idx])
            null.append(abs(_pearson(a, bb)))
        null = np.array([x for x in null if np.isfinite(x)])
        out[label] = {
            "n": len(subset), "pearson_r": r_p, "spearman_rho": r_s,
            "median_abs_difference_px": float(np.median(diff)),
            "median_exp013_px": float(np.median(a)),
            "difference_fraction": float(np.median(diff) / np.median(a)) if np.median(a) else None,
            "null_abs_r_p95": float(np.percentile(null, 95)) if null.size else None,
            "null_abs_r_max": float(null.max()) if null.size else None,
            "p_value_permutation": (float((null >= abs(r_p)).mean()) if null.size else None),
        }
    pooled = out.get("arm_R_only", {})
    met = bool(len(used_r) >= S4_MIN_FRAMES
               and isinstance(pooled.get("pearson_r"), float)
               and pooled.get("pearson_r", 0) >= S4_R_MIN
               and pooled.get("difference_fraction") is not None
               and pooled["difference_fraction"] <= S4_MEDIAN_DIFF_FRACTION)
    out["met"] = met
    out["not_met_for_want_of_data"] = bool(len(used_r) < S4_MIN_FRAMES)
    out["criterion_read_on"] = "arm_R_only"
    return out


# ---------------------------------------------------------------------------
# S3 and S5 compositions
# ---------------------------------------------------------------------------
def s3_pairs(cells: dict, frames: dict, rows: dict) -> list[dict]:
    out = []
    for (window, edge), rec in sorted(rows.items()):
        a_name, b_name = edge.split(" -> ")
        ka, kb = f"{window}/{a_name}", f"{window}/{b_name}"
        ca, cb = cells.get(ka), cells.get(kb)
        if not ca or not cb or ca.get("arm") != "R" or cb.get("arm") != "R":
            continue
        if not (ca.get("pass") and cb.get("pass")):
            continue
        if rec.get("transform_matrix_original_pixels") is None:
            continue
        direct = Transform(np.array(rec["transform_matrix_original_pixels"], float), "affine")
        composed = cb["_k2_to_ref"].inverse() @ ca["_k2_to_ref"]
        shape_a = cells[ka]["_k2_shape"]
        shape_b = cells[kb]["_k2_shape"]
        grid = pixel_grid(tuple(shape_a), step=S3_GRID_STEP)
        p_direct = direct.apply(grid)
        inside = ((p_direct[:, 0] >= 0) & (p_direct[:, 0] <= shape_b[1] - 1)
                  & (p_direct[:, 1] >= 0) & (p_direct[:, 1] <= shape_b[0] - 1))
        if inside.sum() < 100:
            out.append({"window": window, "edge": edge, "excluded":
                        f"joint overlap has {int(inside.sum())} grid points"})
            continue
        err = np.linalg.norm(composed.apply(grid[inside]) - p_direct[inside], axis=1)
        gsd_b = frames[kb]["native_gsd_m"]
        out.append({
            "window": window, "edge": edge,
            "n_inliers_recorded": rec["n_inliers"],
            "n_inliers_a_to_ref": cells[ka]["n_inliers"],
            "n_inliers_b_to_ref": cells[kb]["n_inliers"],
            "n_grid": int(inside.sum()),
            "median_k2_px": float(np.median(err)), "p99_k2_px": float(np.percentile(err, 99)),
            "median_m": float(np.median(err) * K2 * gsd_b),
            "median_ref_px": float(np.median(err) * K2 * gsd_b / REF_GSD_M),
            "p99_ref_px": float(np.percentile(err, 99) * K2 * gsd_b / REF_GSD_M),
            "dst_native_gsd_m": gsd_b,
        })
        print(f"  [S3] {window} {edge[4:16]}->{edge[-13:]} median "
              f"{out[-1]['median_ref_px']:.3f} ref px ({out[-1]['median_m']:.2f} m)", flush=True)
    return out


def s5_triangle(cells: dict, frames: dict) -> dict:
    """{TMC-2 -> NAC recorded} o {NAC -> REF measured} o {REF -> TMC-2 measured}."""
    row = rd09_direct_row()
    tmc = cells.get("C2/TMC-2")
    if row is None:
        return {"met": False, "status": "NO DATA: no passing REAL-DATA-09 B1 direct row"}
    frame = row["frame"]
    key = None
    for k, c in cells.items():
        if c.get("kind") == "NAC" and k.endswith("/" + frame) and c.get("pass") \
                and c.get("arm") == "R":
            key = k
            break
    if key is None or tmc is None or not tmc.get("pass"):
        return {"met": False, "status": "NO DATA: an edge of the triangle did not register",
                "rd09_row": {"window": row["window"], "frame": frame,
                             "n_inliers": row["n_inliers"]},
                "nac_to_ref": bool(key is not None), "tmc2_to_ref": bool(tmc and tmc.get("pass"))}
    # RD-09's recorded transform: TMC-2 crop px -> NAC degraded north-up px, on its own
    # window and its own crop. Rebuild both frames' pixel maps (integer, exact).
    x0, y0, x1, y1 = row["tmc2_block"]
    direct = Transform(np.array(row["transform_matrix"], float), "affine")
    s_nac = cells[key]["_source"]
    # RD-09's NAC frame for this row is the long window; ours is the 4096 tile of the
    # same frame. Both are windows of one frame, so the map between them is exact.
    long_tile = _rd9_long_tile(row["window"], frame)
    if long_tile is None:
        return {"met": False, "status": "NO DATA: REAL-DATA-09's tile is not on disk"}
    k_rd9 = long_tile.get("decimation", 2)
    f_rd9 = int(row["degrade_factor"])
    win_rd9 = TileWindow(long_tile["line0"], long_tile["sample0"], long_tile["n_lines"],
                         long_tile["n_samples"], k_rd9 * f_rd9)
    nu = _rebuild_northup(s_nac, long_tile, k_rd9 * f_rd9)
    # TMC-2 crop px of RD-09's block -> our block's px: an exact integer translation
    dx, dy = x0 - TMC2_BLOCK[0], y0 - TMC2_BLOCK[1]
    to_ours = Transform(np.array([[1.0, 0.0, dx], [0.0, 1.0, dy], [0.0, 0.0, 1.0]]), "euclidean")
    to_deg = Transform(np.array([[1.0 / TMC2_K, 0.0, -(TMC2_K - 1) / 2.0 / TMC2_K],
                                 [0.0, 1.0 / TMC2_K, -(TMC2_K - 1) / 2.0 / TMC2_K],
                                 [0.0, 0.0, 1.0]]), "affine")
    tmc_to_ref = cells["C2/TMC-2"]["_measured"] @ to_deg @ to_ours
    nac_to_ref = cells[key]["_frame_to_ref"] @ (_tile_px_to_frame(win_rd9) @ nu.inverse)
    # the grid lives on the INTERSECTION of the two TMC-2 crops, so neither measured
    # affine is evaluated outside the window it was estimated on
    ix0, iy0 = max(x0, TMC2_BLOCK[0]), max(y0, TMC2_BLOCK[1])
    ix1, iy1 = min(x1, TMC2_BLOCK[2]), min(y1, TMC2_BLOCK[3])
    if ix1 - ix0 < 64 or iy1 - iy0 < 64:
        return {"met": False, "status": "NO DATA: the two TMC-2 crops barely intersect",
                "intersection": [ix0, iy0, ix1, iy1]}
    grid = pixel_grid((iy1 - iy0, ix1 - ix0), step=32) + np.array([ix0 - x0, iy0 - y0], float)
    p_ref_a = tmc_to_ref.apply(grid)                       # TMC-2 -> reference, measured
    p_nac = direct.apply(grid)                             # TMC-2 -> NAC, recorded
    p_ref_b = nac_to_ref.apply(p_nac)                      # NAC -> reference, measured
    err = np.linalg.norm(p_ref_a - p_ref_b, axis=1)
    med = float(np.median(err))
    return {"met": bool(med < S5_BOUND_REF_PX), "bar_ref_px": S5_BOUND_REF_PX,
            "closure_median_ref_px": med, "closure_p99_ref_px": float(np.percentile(err, 99)),
            "closure_median_m": med * REF_GSD_M,
            "bar_m": S5_BOUND_REF_PX * REF_GSD_M,
            "n_grid": int(len(grid)),
            "edges": {"tmc2_to_nac_recorded": {"window": row["window"], "frame": frame,
                                               "engine": row["engine"],
                                               "n_inliers": row["n_inliers"],
                                               "degrade_factor": f_rd9},
                      "nac_to_ref": {"source": key, "n_inliers": cells[key]["n_inliers"]},
                      "tmc2_to_ref": {"n_inliers": tmc["n_inliers"]}},
            "note": "2.0 REFERENCE px is 16.85 m, where EXP-012's 2.0 px is about 2 m; "
                    "the frozen rule is applied in the working frame and the metres are "
                    "printed beside it"}


def _rd9_long_tile(window: str, frame: str) -> dict | None:
    for mname, wname in _rd9.NAC_SOURCES:
        man = json.loads((DATA / "manifests" / mname).read_text(encoding="utf-8"))
        if wname != window:
            continue
        for t in man["tiles"]:
            if t["pdsid"] == frame:
                return t
    return None


def _rebuild_northup(s: Source, tile: dict, k: int):
    """north_up_east_right on a tile of the same frame, from shape alone."""
    shape = (tile["n_lines"] // k, tile["n_samples"] // k)
    return north_up_east_right(np.zeros(shape, np.float32), s.ctx.corners,
                               line=tile["line0"] + (tile["n_lines"] - 1) / 2,
                               sample=tile["sample0"] + (tile["n_samples"] - 1) / 2)


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=None)
    ap.add_argument("--quick", action="store_true", help="4 sources, no B4L; smoke only")
    args = ap.parse_args()
    out_path = Path(args.out) if args.out else OUT / "exp019_results.json"
    if out_path.exists():
        raise SystemExit(f"{out_path} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()

    ref = load_map_block(REF_MANIFEST)
    nul = load_map_block(NULL_MANIFEST)
    margin_px = int(round(MARGIN_M / REF_GSD_M))
    print(f"{STAGE} | reference {ref.data.shape} | null {nul.data.shape} | "
          f"margin {margin_px} px", flush=True)

    print("\n== S0 gates ==", flush=True)
    s0 = {"grid_gate_ref": s0_grid_gate(ref, REF_MANIFEST),
          "grid_gate_null": s0_grid_gate(nul, NULL_MANIFEST)}
    print(f"  grid gate: corners {max(s0['grid_gate_ref']['corner_error_px'].values()):.4f} px, "
          f"round trip {s0['grid_gate_ref']['roundtrip_max_deg']:.2e} deg "
          f"-> {'MET' if s0['grid_gate_ref']['met'] else 'NOT MET'}", flush=True)
    s0["self_reference"] = s0_self_reference(ref)
    print(f"  self-reference: {s0['self_reference']['n_inliers']} inliers, "
          f"error {s0['self_reference']['error_px']} px", flush=True)
    s0["reproduction"] = s0_reproduction() if not args.quick else {"met": True, "note": "quick"}
    s0["met"] = bool(s0["grid_gate_ref"]["met"] and s0["grid_gate_null"]["met"]
                     and s0["self_reference"]["met"] and s0["reproduction"]["met"])

    sources = nac_sources()
    if args.quick:
        sources = sources[:3]
    frames, cells, null_cells, second = {}, {}, [], {}

    print("\n== arm R: sources against the controlled reference ==", flush=True)
    for s in sources:
        frames[s.key] = prepare_nac(s)
        rec = register_against(s, ref, margin_px=margin_px, engine=ENGINE)
        rec.update({"arm": "R", "kind": "NAC", "window": s.window, "frame": s.name})
        if rec.get("_measured") is not None:
            s.to_ref = rec["_measured"]
            frame_to_ref = rec["_measured"] @ nac_matching_px_to_frame(s).inverse()
            t = s.ctx.tile
            win2 = TileWindow(t["line0"], t["sample0"], t["n_lines"], t["n_samples"], K2)
            s.k2_to_ref = frame_to_ref @ _tile_px_to_frame(win2)
            rec["_frame_to_ref"] = frame_to_ref
            rec["_k2_to_ref"] = s.k2_to_ref
            rec["_k2_shape"] = list(win2.shape)
            rec["_source"] = s
            if rec["pass"]:
                rec["_field"] = displacement_field(s, ref)
        cells[s.key] = rec
        f = frames[s.key]
        print(f"  [R] {s.key:32s} k={s.k:2d} |i-30|={f['delta_to_standard_geometry_deg']:5.2f} "
              f"inl={rec.get('n_inliers', 0):5d} {'PASS' if rec.get('pass') else 'fail'} "
              f"{('D=%.1f m' % rec['_field']['rms_m']) if rec.get('_field') else ''} "
              f"({rec.get('wall_s', 0):.0f}s)", flush=True)

    print("\n== arm R: Chandrayaan-2 ==", flush=True)
    tmc, tmc_meta = tmc2_source()
    frames[tmc.key] = tmc_meta
    rec = register_against(tmc, ref, margin_px=margin_px, engine=ENGINE)
    rec.update({"arm": "R", "kind": "TMC-2", "window": tmc.window, "frame": tmc.name,
                "acknowledgement": "Chandrayaan-2 data courtesy ISRO/ISSDC (PRADAN); "
                                   "(c) reserved ISRO"})
    if rec.get("_measured") is not None:
        rec["_source"] = tmc
    cells[tmc.key] = rec
    print(f"  [R] {tmc.key:32s} k={TMC2_K} inl={rec.get('n_inliers', 0):5d} "
          f"{'PASS' if rec.get('pass') else 'fail'} ({rec.get('wall_s', 0):.0f}s)", flush=True)
    all_sources = sources + [tmc]

    print("\n== arm N: the same sources against a disjoint block of the same product ==",
          flush=True)
    H, W = nul.data.shape
    for s in all_sources:
        h, w = s.image.shape
        ch = min(H, int(h * 1.2) + 2 * margin_px)
        cw = min(W, int(w * 1.2) + 2 * margin_px)
        y0 = max(0, (H - ch) // 2)
        x0 = max(0, (W - cw) // 2)
        crop = nul.data[y0:y0 + ch, x0:x0 + cw]
        rec = register_against(s, nul, margin_px=margin_px, engine=ENGINE,
                               crop_override=(crop, (x0, y0, x0 + cw, y0 + ch),
                                              (x0, y0, x0 + cw, y0 + ch)))
        rec.update({"arm": "N", "kind": s.kind, "source": s.key})
        for k in list(rec):
            if k.startswith("_"):
                rec.pop(k)
        null_cells.append(rec)
        print(f"  [N] {s.key:32s} inl={rec.get('n_inliers', 0):5d} "
              f"{'WRONG PASS' if rec.get('pass') else 'fail (expected)'}", flush=True)

    if not args.quick:
        print("\n== B4L beside (no criterion) ==", flush=True)
        for s in all_sources:
            rec = register_against(s, ref, margin_px=margin_px, engine=SECOND_ENGINE)
            for k in list(rec):
                if k.startswith("_"):
                    rec.pop(k)
            second[s.key] = rec
            print(f"  [B4L] {s.key:32s} inl={rec.get('n_inliers', 0):5d} "
                  f"{'PASS' if rec.get('pass') else 'fail'}", flush=True)

    print("\n== arm C: chained through one recorded edge ==", flush=True)
    rows = recorded_rows()
    chained = []
    for s in sources:
        c = cells[s.key]
        if c.get("pass"):
            continue
        best = None
        for (window, edge), rec in rows.items():
            if window != s.window or rec.get("transform_matrix_original_pixels") is None:
                continue
            a, b = edge.split(" -> ")
            if s.name not in (a, b):
                continue
            other = b if a == s.name else a
            oc = cells.get(f"{window}/{other}")
            if not oc or not oc.get("pass") or oc.get("_k2_to_ref") is None:
                continue
            if best is None or rec["n_inliers"] > best[0]["n_inliers"]:
                best = (rec, other, a == s.name)
        if best is None:
            continue
        rec, other, forward = best
        t_ab = Transform(np.array(rec["transform_matrix_original_pixels"], float), "affine")
        to_other = t_ab if forward else t_ab.inverse()
        oc = cells[f"{s.window}/{other}"]
        s.k2_to_ref = oc["_k2_to_ref"] @ to_other
        cells[s.key]["_k2_to_ref"] = s.k2_to_ref
        cells[s.key]["arm"] = "C"
        cells[s.key]["chain"] = {"via": other, "edge": rec["edge"],
                                 "edge_n_inliers": rec["n_inliers"],
                                 "direction_forward": bool(forward)}
        cells[s.key]["_field"] = displacement_field(s, ref)
        chained.append(s.key)
        print(f"  [C] {s.key:32s} via {other} (edge {rec['n_inliers']} inliers) "
              f"D={cells[s.key]['_field']['rms_m']:.1f} m", flush=True)

    print("\n== S3: check points through the reference ==", flush=True)
    pairs = s3_pairs(cells, frames, rows)
    print("\n== S4: EXP-013's per-frame terms against the measured offsets ==", flush=True)
    s4 = s4_statistic(cells, frames, exp013_terms())
    print(f"  arm-R frames {s4['n_common_frames_arm_R_only']}, pooled {s4['n_common_frames']}; "
          f"r = {s4.get('arm_R_only', {}).get('pearson_r')}", flush=True)
    print("\n== S5: the Chandrayaan-2 triangle ==", flush=True)
    try:
        s5 = s5_triangle(cells, frames)
    except Exception as exc:                                   # noqa: BLE001
        s5 = {"met": False, "status": f"NO DATA: composition failed: {exc!r}"[:300]}
    print(f"  {s5.get('status', '')} closure "
          f"{s5.get('closure_median_ref_px')} ref px", flush=True)

    crit = evaluate(cells, frames, s0, pairs, s4, s5, null_cells)

    clean_cells = {}
    for k, c in cells.items():
        d = {kk: vv for kk, vv in c.items() if not kk.startswith("_")}
        if c.get("_field"):
            d["displacement_field"] = {kk: vv for kk, vv in c["_field"].items()
                                       if not kk.startswith("_")}
        clean_cells[k] = d
    doc = {
        "stage": STAGE,
        "preregistration": "docs/stages/EXP-019_controlled_reference.md Part 1 (commit 9cc9c13)",
        "quick_mode": args.quick,
        "reference": {
            "product": json.loads((DATA / "manifests" / REF_MANIFEST).read_text(
                encoding="utf-8"))["product"],
            "gsd_m": REF_GSD_M, "manifests": [REF_MANIFEST, NULL_MANIFEST],
            "credit": json.loads((DATA / "manifests" / REF_MANIFEST).read_text(
                encoding="utf-8"))["credit"],
        },
        "pipeline": {"function": "siim.pipeline.register_pair", "engine": ENGINE, **BASE,
                     "failure_rule": f"n_inliers <= {RULE} (D-023)",
                     "operator": "siim.preprocessing.degrade.degrade_to_gsd, "
                                 f"psf_fwhm_coarse_px = {PSF}",
                     "orientation": "siim.ingest.orientation.north_up_east_right (NAC); "
                                    "map projection (TMC-2)"},
        "criteria": crit,
        "frames": frames,
        "cells": clean_cells,
        "null_cells": null_cells,
        "second_engine": second,
        "chained": chained,
        "exp013_terms": exp013_terms(),
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "opencv": cv2.__version__, "platform": platform.platform()},
        "total_runtime_s": time.perf_counter() - t_start,
        "claims_not_supported": [
            "Not ground truth: a second product is a second opinion with its own control "
            "network and its own errors.",
            "Not manual check points: every correspondence is machine-made; the independence "
            "claimed is of the instrument chain, not of a human annotator.",
            "Not absolute selenographic accuracy: every number is a disagreement, which "
            "bounds the sum of two errors and attributes it to neither.",
            "Not multi-modal: TC is a panchromatic optical imager, like NAC and TMC-2.",
            "Not viewpoint or terrain transfer: one region, mare, near-nadir sources.",
            "Not a verdict change: assess(), select_model and siim.verify.gauge are untouched.",
            "One engine in every criterion; B4L is beside.",
        ],
    }
    out_path.write_text(json.dumps(doc, indent=1, default=_json_default), encoding="utf-8")
    c = crit
    print(f"\nS0 {'MET' if c['S0']['met'] else 'NOT MET'} | "
          f"S1 {'MET' if c['S1']['met'] else 'NOT MET'} ({c['S1']['n_nac_pass']}/{c['S1']['n_nac']}"
          f" NAC, TMC-2 {c['S1']['tmc2_pass']}) | "
          f"S2 {'MET' if c['S2']['met'] else 'NOT MET'} (median {c['S2']['median_m']} m) | "
          f"S3 {'MET' if c['S3']['met'] else 'NOT MET'} (median {c['S3']['median_ref_px']} ref px) | "
          f"S4 {'MET' if c['S4']['met'] else 'NOT MET'} "
          f"(r = {c['S4'].get('arm_R_only', {}).get('pearson_r')}) | "
          f"S5 {'MET' if c['S5'].get('met') else 'NOT MET'} | "
          f"S6 {'MET' if c['S6']['met'] else 'NOT MET'} ({c['S6']['n_pass']} passes)")
    print(f"wrote {out_path} in {doc['total_runtime_s']:.0f}s")


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Transform):
        return np.asarray(o.matrix).tolist()
    if isinstance(o, float) and not np.isfinite(o):
        return None
    raise TypeError(str(type(o)))


if __name__ == "__main__":
    main()
