"""EXP-017 — viewpoint variation, run exactly as Part 1 froze it.

On real lunar relief, at what emission angle does a global 2-D transform stop
being an adequate model of the correspondence between an oblique view and a
nadir orthoimage -- measured in ``relief x tan(e)`` pixels -- and does a local
model, or DEM-orthorectification with the DEM one would actually have, remove
the relief signature it leaves?

The construction (Part 1 section 2.1): the oblique image is the nadir image's
own photons displaced by the DEM's parallax, ``d(q) = (h(q) - h_mean) tan(e)
/ GSD`` px along image-up. Ground truth is therefore exact and is NOT a global
2-D transform; every error is a bound on precision, never accuracy.

Three arms, never pooled: A -- real TMC-2 DTM on the real TMC-2 ortho
(primary); B -- real NAC texture under the 59 m SLDEM; C -- fully synthetic.
Sweep e in {0, 1, 2, 3, 5, 10, 15, 20, 25, 30} deg, B1 only, pipeline defaults.

    python scripts/run_exp017.py            # the frozen run, no flags
    python scripts/run_exp017.py --quick    # smoke test only (tests use it)
"""

from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage, stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.data.synthetic_terrain import TERRAIN_REGIMES, height_field, render  # noqa: E402
from siim.evaluation.coverage import coverage_metrics  # noqa: E402
from siim.geometry import Transform, estimate, pixel_grid  # noqa: E402
from siim.geometry.transforms import MODEL_DOF  # noqa: E402
from siim.ingest.geotiff import decode_window, place, read_geometry  # noqa: E402
from siim.ingest.lola_dem import dem_on_tile_grid, load_sldem_window  # noqa: E402
from siim.pipeline.register import register_pair  # noqa: E402
from siim.pipeline.select import MIN_POINTS  # noqa: E402


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(f"_{name}", ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"_{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


_e7 = _load_script("run_exp007")
_e14 = _load_script("run_exp014")
spearman = _e14.spearman

STAGE = "EXP-017"
DATA = ROOT / "data"
OUT = ROOT / "experiments" / STAGE
P5_ARTEFACT = ROOT / "experiments" / "REAL-DATA-09" / "real_data_09_p5_dem_render_v2.json"
C2_MANIFEST = DATA / "manifests" / "chandrayaan2_manifest.json"
TILES = DATA / "processed" / "mare_serenitatis"

# -- Part 1 sections 2-3, declared in full and not extended ------------------
E_SWEEP = (0, 1, 2, 3, 5, 10, 15, 20, 25, 30)
GRID_STEP = 8                    # dense error grid on the reference
MIN_GRID_POINTS = 300            # below this every residual statistic is CANNOT CHECK
JOINT_VALID_MIN_PX = 50_000      # arm-A admission
CELLS = 4                        # L1: 4 x 4 piecewise affine
CELL_MIN_POINTS = MIN_POINTS     # 12, the selector's own floor
N_NULL = 200
SHIFT_MIN_FRAC = 0.10
NULL_SEED = 20260921
FIXED_POINT_ITERS = 50
FIXED_POINT_TOL = 1e-6
N_ARM_B = 10
ARM_C_REGIMES = ("A_mare_moderate", "A_highlands_moderate")
ARM_C_SEEDS = (3001, 3002, 3003)
ARM_C_FIELD = 768
ARM_C_CROP = 512
ARM_C_GSD_M = 5.0
ARM_C_SUN = (315.0, 45.0)
NODATA_BELOW = -30000.0
ENGINE = "B1"
BASE = {"model": "affine", "ransac_threshold": 3.0, "seed": 0}
RULE = _e7.N_INLIERS_FAILURE_RULE          # 8 (D-023)

# -- Part 1 section 4, frozen -------------------------------------------------
S0_MEDIAN_PX = 0.05
S0_INVERSION_PX = 1e-3
S0_REPRODUCE_TOL = 1e-9
S0_NULL_MAX_FIRES = 1
WHITE_FLOOR_PX = 0.05
MEDIAN_BOUND_PX = 0.5
P99_BOUND_PX = 1.0
S1_MIN_WINDOWS = 12
S1_E_LEVELS = (1, 2, 3, 5)
S3_MIN_FRACTION = 0.80
S4A_MIN_RHO, S4A_MAX_P = 0.3, 0.05
S4B_MIN_RHO = 0.5
S5_FACTOR = 2.0
SLOPE_FACTOR = 2.0
SEC20_PX = 0.5


# ---------------------------------------------------------------------------
# the construction (section 2.1)
# ---------------------------------------------------------------------------
def parallax_field(h: np.ndarray, gsd_m: float, e_deg: float) -> np.ndarray:
    """``d(q) = (h - h_mean) tan(e) / GSD`` px, NaN where the DEM is nodata.
    Positive ``d`` displaces toward -y (image up)."""
    h = np.asarray(h, float)
    return (h - np.nanmean(h)) * np.tan(np.deg2rad(e_deg)) / gsd_m


def _bilinear(field: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Bilinear sample with NaN outside and where any neighbour is NaN."""
    return ndimage.map_coordinates(field, np.vstack([y.ravel(), x.ravel()]), order=1,
                                   mode="constant", cval=np.nan).reshape(np.shape(x))


def _fill_nearest(a: np.ndarray) -> np.ndarray:
    """NaN holes replaced by the nearest finite value (for iteration only)."""
    nan = ~np.isfinite(a)
    if not nan.any():
        return a
    idx = ndimage.distance_transform_edt(nan, return_distances=False, return_indices=True)
    return a[tuple(idx)]


def invert_field(d: np.ndarray, px: np.ndarray, py: np.ndarray):
    """Source point ``q`` of oblique point ``p``: solve ``q = p - d_vec(q)``.

    The displacement is along y only, so ``q_x = p_x`` exactly and the
    fixed-point iteration is one-dimensional: ``q_y <- p_y + d(q_x, q_y)``. A
    contraction while ``|dd/dy| < 1``, i.e. ``tan(e) x slope < 1`` (section 5).

    The iteration runs on a nearest-filled, edge-extended copy of the field so
    that a point whose trajectory crosses a nodata hole or the array edge
    converges instead of oscillating; validity is then read from the RAW
    field at the converged point, so no such point is ever reported valid.
    """
    qx = np.asarray(px, float)
    py = np.asarray(py, float)
    qy = py.copy()
    d_iter = _fill_nearest(d)
    iters = 0
    for iters in range(1, FIXED_POINT_ITERS + 1):
        dq = ndimage.map_coordinates(d_iter, np.vstack([qy.ravel(), qx.ravel()]), order=1,
                                     mode="nearest").reshape(qy.shape)
        new = py + dq
        step = float(np.max(np.abs(new - qy))) if new.size else 0.0
        qy = new
        if step < FIXED_POINT_TOL:
            break
    dq = _bilinear(d, qx, qy)
    return qx, qy, np.isfinite(dq), iters


def dense_warp(image: np.ndarray, valid: np.ndarray, d: np.ndarray, order: int = 3):
    """``I_obl(p) = I(q)`` with ``p = q + d_vec(q)``. Same order-3 spline and
    NaN fill as ``siim.geometry.warp``; on a d = 0 field it IS that warp."""
    h, w = image.shape
    ys, xs = np.mgrid[0:h, 0:w].astype(float)
    qx, qy, d_ok, _ = invert_field(d, xs, ys)
    fill = np.where(valid, image, np.nanmedian(image[valid]) if valid.any() else 0.0)
    sampled = ndimage.map_coordinates(fill, np.vstack([qy.ravel(), qx.ravel()]), order=order,
                                      mode="constant", cval=0.0, prefilter=True).reshape(h, w)
    v_interp = _bilinear(valid.astype(float), qx, qy)
    inside = (qx >= -0.5) & (qx <= w - 0.5) & (qy >= -0.5) & (qy <= h - 0.5)
    ok = inside & d_ok & (np.nan_to_num(v_interp, nan=0.0) > 0.999)
    out = np.where(ok, sampled, np.nan)
    return out, ok


def forward_points(d: np.ndarray, q: np.ndarray) -> np.ndarray:
    """``p = q + d_vec(q)`` for reference-grid points ``q`` (N, 2)."""
    dq = _bilinear(d, q[:, 0], q[:, 1])
    return np.column_stack([q[:, 0], q[:, 1] - dq])


def orthorectify(d_model: np.ndarray, p: np.ndarray) -> np.ndarray:
    """L2/L3: map oblique points back to the map with a DEM's parallax field.
    Same sign and convention as the construction; exact when ``d_model`` is
    the field that built the oblique (L3)."""
    qx, qy, _, _ = invert_field(d_model, p[:, 0], p[:, 1])
    return np.column_stack([qx, qy])


# ---------------------------------------------------------------------------
# dense error and local arms
# ---------------------------------------------------------------------------
def dense_grid(shape, joint_valid: np.ndarray, obl_valid: np.ndarray, d: np.ndarray):
    """Reference grid q at GRID_STEP, jointly valid on both sides."""
    q = pixel_grid(shape, step=GRID_STEP)
    qi = q.astype(int)
    ok = joint_valid[qi[:, 1], qi[:, 0]]
    p = forward_points(d, q)
    ov = _bilinear(obl_valid.astype(float), p[:, 0], p[:, 1])
    ok &= np.isfinite(p).all(axis=1) & (np.nan_to_num(ov, nan=0.0) > 0.999)
    return q[ok], p[ok]


def err_stats(err: np.ndarray) -> dict:
    f = err[np.isfinite(err)]
    if f.size == 0:
        return {"median": None, "p99": None, "max": None, "rms": None, "n": 0}
    return {"median": float(np.median(f)), "p99": float(np.percentile(f, 99)),
            "max": float(f.max()), "rms": float(np.sqrt((f ** 2).mean())), "n": int(f.size)}


def apply_global(t: Transform, p: np.ndarray) -> np.ndarray:
    return t.apply(p)


def fit_affine(src: np.ndarray, dst: np.ndarray) -> Transform | None:
    if src.shape[0] < 3:
        return None
    r = estimate(src, dst, "affine")
    return r.transform if r.ok else None


def piecewise_affine(src_pts, dst_pts, shape, t_global: Transform):
    """L1: 4 x 4 cells over the reference; per cell an affine LS fit to the
    refined inliers whose reference point lies in it; < CELL_MIN_POINTS ->
    the global transform, counted."""
    h, w = shape
    cy = np.minimum((dst_pts[:, 1] * CELLS / h).astype(int), CELLS - 1)
    cx = np.minimum((dst_pts[:, 0] * CELLS / w).astype(int), CELLS - 1)
    cells, fallback = {}, 0
    for i in range(CELLS):
        for j in range(CELLS):
            sel = (cy == i) & (cx == j)
            t = fit_affine(src_pts[sel], dst_pts[sel]) if sel.sum() >= CELL_MIN_POINTS else None
            if t is None:
                t, fallback = t_global, fallback + 1
            cells[(i, j)] = t

    def apply(p, ref_guess):
        gy = np.clip((ref_guess[:, 1] * CELLS / h).astype(int), 0, CELLS - 1)
        gx = np.clip((ref_guess[:, 0] * CELLS / w).astype(int), 0, CELLS - 1)
        out = np.empty_like(p)
        for (i, j), t in cells.items():
            sel = (gy == i) & (gx == j)
            if sel.any():
                out[sel] = t.apply(p[sel])
        return out
    return apply, fallback


# ---------------------------------------------------------------------------
# section 2.3 statistics
# ---------------------------------------------------------------------------
def remove_plane(h: np.ndarray) -> np.ndarray:
    """Residual relief: the DEM minus its best-fit plane (3 parameters)."""
    ys, xs = np.mgrid[0:h.shape[0], 0:h.shape[1]].astype(float)
    ok = np.isfinite(h)
    A = np.column_stack([xs[ok], ys[ok], np.ones(int(ok.sum()))])
    coef, *_ = np.linalg.lstsq(A, h[ok], rcond=None)
    return h - (coef[0] * xs + coef[1] * ys + coef[2])


def _r2_slope(x, y):
    """2-parameter regression y = a x + b; returns (slope, intercept, R^2)."""
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if x.size < 3 or np.ptp(x) == 0:
        return float("nan"), float("nan"), float("nan")
    a, b = np.polyfit(x, y, 1)
    res = y - (a * x + b)
    ss = ((y - y.mean()) ** 2).sum()
    return float(a), float(b), float(1 - (res ** 2).sum() / ss) if ss > 0 else float("nan")


def grid_to_2d(q: np.ndarray, values: np.ndarray, shape):
    """Scatter grid values back onto the (ny, nx) step-grid, NaN elsewhere."""
    ny, nx = (shape[0] + GRID_STEP - 1) // GRID_STEP, (shape[1] + GRID_STEP - 1) // GRID_STEP
    out = np.full((ny, nx), np.nan)
    out[(q[:, 1] // GRID_STEP).astype(int), (q[:, 0] // GRID_STEP).astype(int)] = values
    return out


def shift_null_draw(h2d: np.ndarray, rng) -> np.ndarray:
    """One toroidal shift by >= SHIFT_MIN_FRAC of each extent plus a random
    dihedral element (flips; transpose too when square)."""
    ny, nx = h2d.shape
    dy = int(rng.integers(int(np.ceil(SHIFT_MIN_FRAC * ny)), max(ny - int(np.ceil(SHIFT_MIN_FRAC * ny)), int(np.ceil(SHIFT_MIN_FRAC * ny))) + 1))
    dx = int(rng.integers(int(np.ceil(SHIFT_MIN_FRAC * nx)), max(nx - int(np.ceil(SHIFT_MIN_FRAC * nx)), int(np.ceil(SHIFT_MIN_FRAC * nx))) + 1))
    g = np.roll(h2d, (dy, dx), axis=(0, 1))
    if rng.integers(2):
        g = g[::-1]
    if rng.integers(2):
        g = g[:, ::-1]
    if ny == nx and rng.integers(2):
        g = g.T
    return g


def signature_test(r2d: np.ndarray, h2d: np.ndarray, e_deg: float, gsd_m: float,
                   rng_shift, rng_perm, n_null: int = N_NULL) -> dict:
    """The relief-signature detector (section 2.3): R^2 of r_phi on h_res
    against the SHIFT null (the criterion) and the pixel-permutation null
    (reported beside it), predicted sign, |slope| within 2x of tan(e)/GSD."""
    a, b, r2 = _r2_slope(h2d.ravel(), r2d.ravel())
    pred = np.tan(np.deg2rad(e_deg)) / gsd_m
    null_shift = np.array([_r2_slope(shift_null_draw(h2d, rng_shift).ravel(), r2d.ravel())[2]
                           for _ in range(n_null)])
    ok = np.isfinite(h2d) & np.isfinite(r2d)
    hv, rv = h2d[ok], r2d[ok]
    null_perm = np.array([_r2_slope(rng_perm.permutation(hv), rv)[2] for _ in range(n_null)])
    p95_shift = float(np.nanpercentile(null_shift, 95)) if np.isfinite(null_shift).any() else float("nan")
    p95_perm = float(np.nanpercentile(null_perm, 95)) if np.isfinite(null_perm).any() else float("nan")
    sign_ok = bool(np.isfinite(a) and a > 0) if pred > 0 else None
    mag_ok = bool(np.isfinite(a) and pred > 0 and (pred / SLOPE_FACTOR <= abs(a) <= pred * SLOPE_FACTOR))
    r2_beats_shift = bool(np.isfinite(r2) and np.isfinite(p95_shift) and r2 > p95_shift)
    r2_beats_perm = bool(np.isfinite(r2) and np.isfinite(p95_perm) and r2 > p95_perm)
    fired = bool(r2_beats_shift and (sign_ok is True) and mag_ok)
    fired_perm = bool(r2_beats_perm and (sign_ok is True) and mag_ok)
    return {"slope_px_per_m": a, "intercept_px": b, "r2": r2,
            "predicted_slope_px_per_m": float(pred), "sign_ok": sign_ok, "magnitude_ok": mag_ok,
            "null_shift_p95": p95_shift, "null_perm_p95": p95_perm,
            "r2_beats_shift_null": r2_beats_shift, "r2_beats_perm_null": r2_beats_perm,
            "fired": fired, "fired_under_pixel_permutation": fired_perm, "n": int(ok.sum())}


def morans_i(z2d: np.ndarray, rng, n_null: int = N_NULL) -> dict:
    """Moran's I under rook adjacency on the step grid vs value permutations."""
    ok = np.isfinite(z2d)
    idx = np.full(z2d.shape, -1)
    idx[ok] = np.arange(int(ok.sum()))
    z = z2d[ok]
    pairs = []
    a, b = idx[:, :-1], idx[:, 1:]
    m = (a >= 0) & (b >= 0)
    pairs.append(np.column_stack([a[m], b[m]]))
    a, b = idx[:-1, :], idx[1:, :]
    m = (a >= 0) & (b >= 0)
    pairs.append(np.column_stack([a[m], b[m]]))
    pr = np.vstack(pairs)
    n = z.size
    if n < 3 or pr.shape[0] == 0:
        return {"I": None, "null_p95": None, "white_by_I": None, "n": int(n), "n_pairs": int(pr.shape[0])}
    zc = z - z.mean()
    denom = (zc ** 2).sum()
    W = 2.0 * pr.shape[0]

    def I_of(v):
        return float(n / W * 2.0 * (v[pr[:, 0]] * v[pr[:, 1]]).sum() / denom) if denom > 0 else float("nan")
    I = I_of(zc)
    null = np.array([I_of(rng.permutation(zc)) for _ in range(n_null)])
    p95 = float(np.percentile(null, 95))
    return {"I": I, "null_p95": p95, "white_by_I": bool(I <= p95), "n": int(n), "n_pairs": int(pr.shape[0])}


def whiteness(r_phi_grid: np.ndarray, r2d: np.ndarray, rng) -> dict:
    rms = float(np.sqrt(np.nanmean(r_phi_grid ** 2))) if np.isfinite(r_phi_grid).any() else float("nan")
    mi = morans_i(r2d, rng)
    under_floor = bool(np.isfinite(rms) and rms < WHITE_FLOOR_PX)
    white = bool(under_floor or (mi["white_by_I"] is True))
    return {"rms_px": rms, "under_floor": under_floor, "moran": mi, "white": white}


# ---------------------------------------------------------------------------
# per-arm windows
# ---------------------------------------------------------------------------
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


class Window:
    """One (image, heights) pair on one grid. ``valid`` marks jointly valid px."""

    def __init__(self, arm, name, image, valid, heights_m, gsd_m, meta, sldem_m=None):
        self.arm, self.name = arm, name
        self.image = np.where(valid, image, np.nan)
        self.valid = valid
        self.h = np.where(valid, heights_m, np.nan)
        self.gsd = float(gsd_m)
        self.meta = dict(meta)
        self.sldem = None if sldem_m is None else np.where(valid, sldem_m, np.nan)
        self.h_res = remove_plane(self.h)
        self.meta.update({
            "shape": list(image.shape), "n_joint_valid_px": int(valid.sum()),
            "gsd_m_along_view": self.gsd,
            "relief_ptp_m": float(np.nanmax(self.h) - np.nanmin(self.h)),
            "relief_res_rms_m": float(np.sqrt(np.nanmean(self.h_res ** 2))),
        })
        if self.sldem is not None:
            diff = self.sldem - self.h
            self.meta["sldem_minus_dtm_m"] = {"rms": float(np.sqrt(np.nanmean(diff ** 2))),
                                              "ptp": float(np.nanmax(diff) - np.nanmin(diff)),
                                              "mean": float(np.nanmean(diff))}
            self.sldem_res = remove_plane(self.sldem)


def _dtm_on_ortho_grid(dtm_tif, ortho_tif, y0, y1, x0, x1) -> np.ndarray:
    """DTM bilinearly resampled onto ortho rows [y0,y1) cols [x0,x1), through
    both products' GeoTIFF geometry (PixelIsArea centres), a stated deviation
    from P5's nearest repeat (section 2.1)."""
    go, gd = read_geometry(ortho_tif), read_geometry(dtm_tif)
    ox0, oy0 = go.upper_left_model_xy(); osx, osy = go.model_pixel_size()
    dx0, dy0 = gd.upper_left_model_xy(); dsx, dsy = gd.model_pixel_size()
    cols = np.arange(x0, x1); rows = np.arange(y0, y1)
    mx = ox0 + (cols + 0.5) * osx
    my = oy0 - (rows + 0.5) * osy
    dc = (mx - dx0) / dsx - 0.5
    dr = (dy0 - my) / dsy - 0.5
    r0, r1 = max(0, int(np.floor(dr.min())) - 1), min(int(gd.shape[0]), int(np.ceil(dr.max())) + 2)
    c0, c1 = max(0, int(np.floor(dc.min())) - 1), min(int(gd.shape[1]), int(np.ceil(dc.max())) + 2)
    dem = decode_window(dtm_tif, r0, r1, c0, c1).astype(np.float64)
    dem[dem < NODATA_BELOW] = np.nan
    rr, cc = np.meshgrid(dr - r0, dc - c0, indexing="ij")
    return _bilinear(dem, cc, rr)


def arm_a_windows(quick: bool, excluded: list):
    """Yields one window at a time; a 3.5 Mpx window carries six float64
    arrays, so fifteen of them may not be resident together."""
    art = json.loads(P5_ARTEFACT.read_text(encoding="utf-8"))
    man = json.loads(C2_MANIFEST.read_text(encoding="utf-8"))
    ortho = next(r for r in man["products"].values() if r["instrument"] == "TMC-2" and r["kind"] == "ortho")
    dtm = next(r for r in man["products"].values() if r["instrument"] == "TMC-2" and r["kind"] == "dtm")
    tif, dtm_tif = ROOT / ortho["data_file"], ROOT / dtm["data_file"]
    sldem = load_sldem_window()
    rows = [r for r in art["rows"] if "leg_a_control" in r]
    if quick:
        rows = rows[:1]
    excluded += [{"window": r["window"], "frame": r["frame"], "excluded": r["excluded"]}
                 for r in art["rows"] if "excluded" in r]
    for r in rows:
        x0, y0, x1, y1 = r["tmc2_block"]
        name = f"{r['window']}/{r['frame'][-12:]}"
        crop = decode_window(tif, y0, y1, x0, x1).astype(np.float64)
        o_valid = crop > 0
        h = _dtm_on_ortho_grid(dtm_tif, tif, y0, y1, x0, x1)
        valid = o_valid & np.isfinite(h)
        probe = place(tif, row0=y0, row1=y0 + 2, col0=x0, col1=x0 + 2, name="probe")
        mpp_x, mpp_y = probe.metres_per_pixel
        meta = {"tmc2_block": [x0, y0, x1, y1], "ortho_valid_fraction": float(o_valid.mean()),
                "dem_nan_fraction": float(np.isnan(h).mean()), "metres_per_pixel_xy": [mpp_x, mpp_y],
                "p5_dem_height_ptp_m": r.get("dem_height_ptp_m"), "products": {"ortho": ortho["product_id"], "dtm": dtm["product_id"]}}
        if int(valid.sum()) < JOINT_VALID_MIN_PX:
            excluded.append({"window": name, "excluded": f"jointly valid area {int(valid.sum())} px < {JOINT_VALID_MIN_PX}", **meta})
            print(f"  A {name}: excluded ({int(valid.sum())} jointly valid px)", flush=True)
            continue
        ys, xs = np.mgrid[0:crop.shape[0], 0:crop.shape[1]].astype(float)
        lon, lat = probe.lonlat_of_block_xy(xs, ys)
        sl = sldem.height_m_at(lon, lat)
        img = _e7.stretch(np.where(o_valid, crop, np.nan))
        win = Window("A", name, img, valid, h, mpp_y, meta, sldem_m=sl)
        print(f"  A {name}: {crop.shape[1]}x{crop.shape[0]} joint {valid.mean():.2f} "
              f"ptp {win.meta['relief_ptp_m']:.0f} m  res-rms {win.meta['relief_res_rms_m']:.1f} m  gsd {mpp_y:.3f}", flush=True)
        yield win


def arm_b_windows(quick: bool, excluded: list):
    prod = nac_products()
    sldem = load_sldem_window()
    names = [p.name for p in sorted(TILES.glob("*.tile.npy")) if "geo.l" in p.name][:N_ARM_B]
    if quick:
        names = names[:1]
    for nm in names:
        m = re.match(r"(nac\.m\d+[lr]c)\.geo\.l(\d+)s(\d+)\.n(\d+)\.tile\.npy", nm)
        pdsid, line0, sample0 = m.group(1), int(m.group(2)), int(m.group(3))
        raw = np.load(TILES / nm)
        n_lines, n_samples = raw.shape
        k = 2
        img = _e7.stretch(_e7.decimate(raw, k))
        corners = _e7.corners_for(pdsid, prod)
        h, _, _ = dem_on_tile_grid(sldem, corners, line0, sample0, n_lines, n_samples, k)
        f = prod[pdsid]["fields"]
        spm = 0.5 * (float(f["SCALED_PIXEL_WIDTH"]) + float(f["SCALED_PIXEL_HEIGHT"]))
        valid = np.isfinite(img) & np.isfinite(h)
        meta = {"tile": nm, "pdsid": pdsid, "decimation": k, "scaled_pixel_m": spm,
                "emission_deg": float(f.get("EMISSION_ANGLE", "nan")), "dem": "SLDEM2015 512 ppd"}
        win = Window("B", nm.replace(".tile.npy", ""), img, valid, h, k * spm, meta)
        print(f"  B {pdsid} l{line0}: ptp {win.meta['relief_ptp_m']:.0f} m res-rms "
              f"{win.meta['relief_res_rms_m']:.1f} m gsd {k*spm:.2f}", flush=True)
        yield win


def arm_c_windows(quick: bool, excluded: list):
    combos = [(r, s) for r in ARM_C_REGIMES for s in ARM_C_SEEDS]
    if quick:
        combos = combos[:1]
    for regime, seed in combos:
        reg = TERRAIN_REGIMES[regime]
        rng = np.random.default_rng(seed)
        h = height_field((ARM_C_FIELD, ARM_C_FIELD), rng, scene=reg.scene,
                         target_slope_median_deg=reg.target_slope_median_deg, octaves=reg.octaves,
                         persistence=reg.persistence, crater_density=reg.crater_density,
                         pixel_scale=ARM_C_GSD_M)
        img = render(h, ARM_C_SUN[0], ARM_C_SUN[1], pixel_scale=ARM_C_GSD_M, rng=rng)
        o = (ARM_C_FIELD - ARM_C_CROP) // 2
        sl = slice(o, o + ARM_C_CROP)
        img, h = img[sl, sl], h[sl, sl]
        valid = np.isfinite(img)
        win = Window("C", f"{regime}/seed{seed}", img, valid, h, ARM_C_GSD_M,
                     {"regime": regime, "seed": seed, "sun": list(ARM_C_SUN)})
        print(f"  C {regime} seed {seed}: ptp {win.meta['relief_ptp_m']:.0f} m res-rms "
              f"{win.meta['relief_res_rms_m']:.1f} m", flush=True)
        yield win


# ---------------------------------------------------------------------------
# one (window, e) cell
# ---------------------------------------------------------------------------
def _seed(win_idx, e_idx, tag):
    return np.random.default_rng([NULL_SEED, win_idx, e_idx, tag])


def run_cell(win: Window, e: float, win_idx: int, e_idx: int, n_null: int) -> dict:
    t0 = time.perf_counter()
    row = {"arm": win.arm, "window": win.name, "e_deg": e, "gsd_m": win.gsd,
           "P_ptp_px": float(win.meta["relief_ptp_m"] * np.tan(np.deg2rad(e)) / win.gsd),
           "P_rms_px": float(win.meta["relief_res_rms_m"] * np.tan(np.deg2rad(e)) / win.gsd)}
    d = parallax_field(win.h, win.gsd, e)
    d_filled = np.where(np.isfinite(d), d, np.nan)
    obl, obl_valid = dense_warp(win.image, win.valid, d_filled)
    row["field_rms_px"] = float(np.sqrt(np.nanmean(d ** 2)))
    row["oblique_differs_from_reference"] = bool(
        np.nanmax(np.abs(np.where(obl_valid & win.valid, obl - win.image, 0.0))) > 0.0)
    row["oblique_valid_fraction"] = float(obl_valid.mean())

    q, p = dense_grid(win.image.shape, win.valid, obl_valid, d_filled)
    row["n_grid"] = int(q.shape[0])
    # S0(ii): inversion composed with forward returns identity
    qx, qy, _, iters = invert_field(d_filled, p[:, 0], p[:, 1])
    row["inversion_max_px"] = float(np.nanmax(np.hypot(qx - q[:, 0], qy - q[:, 1]))) if q.size else None
    row["inversion_iters"] = int(iters)

    try:
        res = register_pair(obl, win.image, engine=ENGINE, **BASE)
    except Exception as exc:  # recorded, never hidden
        row.update({"error": f"{type(exc).__name__}: {exc}", "runtime_s": time.perf_counter() - t0})
        return row
    s = res.summary()
    row.update({"n_inliers": s["n_inliers"], "pass": bool(s["n_inliers"] > RULE),
                "status": s["status"], "confidence": s["confidence"], "model": s["model"],
                "model_dof": None if s["model"] is None else MODEL_DOF[s["model"]],
                "model_selected_by": s["model_selected_by"], "heldout_px": s["heldout_px"],
                "heldout_best_px": (None if not s["heldout_px"] else float(min(s["heldout_px"].values()))),
                "decided_by_tie_break": s["decided_by_tie_break"], "n_refined": s["n_refined"],
                "transform_matrix": s["transform_matrix"]})
    if res.transform is None or q.shape[0] < MIN_GRID_POINTS:
        row["residual"] = "CANNOT CHECK" if q.shape[0] < MIN_GRID_POINTS else "no transform"
        row["runtime_s"] = time.perf_counter() - t0
        return row

    u_phi = np.array([0.0, -1.0])
    h2d = grid_to_2d(q, _bilinear(win.h_res, q[:, 0], q[:, 1]), win.image.shape)
    arms = {}
    # G
    mapped = res.transform.apply(p)
    errG = np.hypot(*(mapped - q).T)
    arms["G"] = {"err": err_stats(errG), "residual_phi": grid_to_2d(q, (mapped - q) @ u_phi, win.image.shape)}
    # refined inliers
    rm = res.refined_mask
    ps, qs = res.src_points[rm], res.dst_points_refined[rm]
    # L1
    apply_l1, fallback = piecewise_affine(ps, qs, win.image.shape, res.transform)
    m1 = apply_l1(p, mapped)
    arms["L1"] = {"err": err_stats(np.hypot(*(m1 - q).T)), "residual_phi": grid_to_2d(q, (m1 - q) @ u_phi, win.image.shape),
                  "cells_fallback_to_global": int(fallback)}
    # L2 (arm A only) and L3 (control)
    if win.arm == "A":
        dS = parallax_field(win.sldem, win.gsd, e)
        A2 = fit_affine(orthorectify(dS, ps), qs)
        if A2 is not None:
            m2 = A2.apply(orthorectify(dS, p))
            arms["L2"] = {"err": err_stats(np.hypot(*(m2 - q).T)), "residual_phi": grid_to_2d(q, (m2 - q) @ u_phi, win.image.shape)}
    A3 = fit_affine(orthorectify(d_filled, ps), qs)
    if A3 is not None:
        m3 = A3.apply(orthorectify(d_filled, p))
        arms["L3"] = {"err": err_stats(np.hypot(*(m3 - q).T))}

    for i, (k, a) in enumerate(arms.items()):
        rec = {"err": a["err"]}
        if "cells_fallback_to_global" in a:
            rec["cells_fallback_to_global"] = a["cells_fallback_to_global"]
        if "residual_phi" in a:
            r2d = a["residual_phi"]
            rec["signature"] = signature_test(r2d, h2d, e, win.gsd, _seed(win_idx, e_idx, 10 + i),
                                              _seed(win_idx, e_idx, 20 + i), n_null)
            rec["whiteness"] = whiteness(r2d, r2d, _seed(win_idx, e_idx, 30 + i))
        row[k] = rec

    # GT-free signature on refined inliers (reported, not a criterion)
    if ps.shape[0] >= 3:
        r_free = (res.transform.apply(ps) - qs) @ u_phi
        gtfree = {}
        for tag, field2d in (("dtm", h2d),) + ((("sldem", grid_to_2d(q, _bilinear(win.sldem_res, q[:, 0], q[:, 1]), win.image.shape)),) if win.arm == "A" else ()):
            hq = _bilinear(field2d, qs[:, 0] / GRID_STEP, qs[:, 1] / GRID_STEP)
            a, b, r2 = _r2_slope(hq, r_free)
            rng = _seed(win_idx, e_idx, 40 + (tag == "sldem"))
            null = np.array([_r2_slope(_bilinear(shift_null_draw(field2d, rng), qs[:, 0] / GRID_STEP, qs[:, 1] / GRID_STEP), r_free)[2]
                             for _ in range(n_null)])
            pred = np.tan(np.deg2rad(e)) / win.gsd
            p95 = float(np.nanpercentile(null, 95)) if np.isfinite(null).any() else float("nan")
            gtfree[tag] = {"slope_px_per_m": a, "r2": r2, "null_shift_p95": p95, "n": int(np.isfinite(hq).sum()),
                           "fired": bool(np.isfinite(r2) and r2 > p95 and a > 0 and pred > 0 and pred / SLOPE_FACTOR <= abs(a) <= pred * SLOPE_FACTOR)}
        row["gt_free_signature"] = gtfree

    # secondaries: coverage, refinement shift vs slope
    dst_in = res.dst_points[res.inlier_mask]
    cov = coverage_metrics(dst_in, win.image.shape, roi=win.valid) if dst_in.shape[0] else None
    row["coverage"] = None if cov is None else {"grid_occupancy": cov.grid_occupancy,
                                                 "max_uncovered_disc_ratio": cov.max_uncovered_disc_ratio}
    if res.refinement is not None and res.refinement.ok.any():
        ok = res.refinement.ok
        sh = np.hypot(*res.refinement.shift[ok].T)
        gy, gx = np.gradient(np.nan_to_num(win.h, nan=float(np.nanmean(win.h))))
        slope = np.hypot(gx, gy) / win.gsd
        pts = res.dst_points[res.inlier_mask][ok]
        sl = _bilinear(slope, pts[:, 0], pts[:, 1])
        good = np.isfinite(sl) & np.isfinite(sh)
        steep = good & (sl >= np.tan(np.deg2rad(5.0)))
        row["refinement_shift"] = {"n": int(good.sum()), "median_px": float(np.median(sh[good])) if good.any() else None,
                                   "median_px_on_slopes_ge_5deg": float(np.median(sh[steep])) if steep.any() else None,
                                   "n_on_slopes_ge_5deg": int(steep.sum()),
                                   "spearman_shift_vs_slope": spearman(sh[good], sl[good]) if good.sum() > 3 else None}
    row["runtime_s"] = time.perf_counter() - t0
    return row


def _fmt(v, w=7, d=3):
    return f"{v:{w}.{d}f}" if isinstance(v, (int, float)) and v is not None and np.isfinite(v) else f"{'--':>{w}}"


def print_row(r: dict) -> None:
    g = r.get("G", {}).get("err", {}); l1 = r.get("L1", {}).get("err", {})
    sig = r.get("G", {}).get("signature", {}).get("fired")
    print(f"  {r['arm']} {r['window'][:34]:34s} e={r['e_deg']:2d} n={r.get('n_inliers', -1):5d} "
          f"{str(r.get('status', r.get('error', '?')))[:12]:12s} {str(r.get('model'))[:11]:11s} "
          f"G med {_fmt(g.get('median'))} p99 {_fmt(g.get('p99'))} | L1 med {_fmt(l1.get('median'))} "
          f"| sig {'FIRE' if sig else ('----' if sig is False else '  ? ')} | {r.get('runtime_s', 0):.0f}s", flush=True)


# ---------------------------------------------------------------------------
# criteria
# ---------------------------------------------------------------------------
def _median_or_none(vals):
    return float(np.median(vals)) if len(vals) else None


def _cells(rows, arm):
    return [r for r in rows if r["arm"] == arm and "error" not in r]


def _g_median(r):
    return r.get("G", {}).get("err", {}).get("median")


def _g_p99(r):
    return r.get("G", {}).get("err", {}).get("p99")


def onset(rows_w):
    """e*_med, e*_p99 for one window from its sweep rows."""
    by_e = {r["e_deg"]: r for r in rows_w}
    e_med = next((e for e in E_SWEEP if e in by_e and (_g_median(by_e[e]) or 0) > MEDIAN_BOUND_PX), None)
    e_p99 = next((e for e in E_SWEEP if e in by_e and (_g_p99(by_e[e]) or 0) > P99_BOUND_PX), None)
    e_sec20 = next((e for e in E_SWEEP if e in by_e and by_e[e]["P_ptp_px"] >= SEC20_PX), None)
    return e_med, e_p99, e_sec20


def evaluate(rows: list[dict], windows_meta: dict) -> dict:
    A = _cells(rows, "A")
    a_names = sorted({r["window"] for r in A})

    # ---- S0 -------------------------------------------------------------
    s0_windows = {}
    for w in a_names:
        rw = [r for r in A if r["window"] == w]
        e0 = next((r for r in rw if r["e_deg"] == 0), None)
        c = {}
        c["i_median_lt_0.05"] = bool(e0 and (_g_median(e0) is not None) and _g_median(e0) < S0_MEDIAN_PX)
        c["i_model_translation"] = bool(e0 and e0.get("model") == "translation")
        c["i_pass"] = bool(e0 and e0.get("pass"))
        c["ii_inversion_lt_1e-3"] = all((r.get("inversion_max_px") is not None and r["inversion_max_px"] < S0_INVERSION_PX) for r in rw)
        l3 = [r.get("L3", {}).get("err", {}).get("median") for r in rw]
        c["iv_L3_median_lt_0.05_every_e"] = all(v is not None and v < S0_MEDIAN_PX for v in l3)
        c["vi_field_nonzero_every_e_gt_0"] = all((r["field_rms_px"] > 0 and r["oblique_differs_from_reference"]) for r in rw if r["e_deg"] > 0)
        c["all_clauses"] = all(c.values())
        c["L3_median_by_e"] = {str(r["e_deg"]): r.get("L3", {}).get("err", {}).get("median") for r in rw}
        s0_windows[w] = c
    # At e = 0 the predicted slope is 0, so clauses 2-3 of the detector cannot
    # pass and the calibration reads clause 1 alone: R^2 above the null's p95.
    e0_fires = sum(1 for r in A if r["e_deg"] == 0 and r.get("G", {}).get("signature", {}).get("r2_beats_shift_null"))
    e0_fires_perm = sum(1 for r in A if r["e_deg"] == 0 and r.get("G", {}).get("signature", {}).get("r2_beats_perm_null"))
    s0_v = e0_fires <= S0_NULL_MAX_FIRES
    good = [w for w in a_names if s0_windows[w]["all_clauses"]]
    s0 = {"per_window": s0_windows, "v_null_calibration": {"shift_null_fires_at_e0": e0_fires,
                                                            "pixel_perm_fires_at_e0": e0_fires_perm,
                                                            "max_allowed": S0_NULL_MAX_FIRES, "met": s0_v},
          "windows_reported": good, "windows_failed": [w for w in a_names if w not in good],
          "n_windows": len(a_names), "met": bool(good) and s0_v and len(good) == len(a_names)}
    AG = [r for r in A if r["window"] in good]
    n_good = len(good)

    # ---- S1 -------------------------------------------------------------
    def s1_arm(arm_key):
        per_e = {}
        for e in E_SWEEP:
            ok_lit, ok_bound, n = 0, 0, 0
            for w in good:
                r = next((x for x in AG if x["window"] == w and x["e_deg"] == e), None)
                a = None if r is None else r.get(arm_key)
                if a is None:
                    continue
                n += 1
                if a["whiteness"]["white"] and not a["signature"]["fired"]:
                    ok_lit += 1
                er = a["err"]
                if er["median"] is not None and er["median"] < MEDIAN_BOUND_PX and er["p99"] < P99_BOUND_PX:
                    ok_bound += 1
            per_e[str(e)] = {"n": n, "literal_ok": ok_lit, "bound_ok": ok_bound,
                             "literal_holds": ok_lit >= S1_MIN_WINDOWS, "bound_holds": ok_bound >= S1_MIN_WINDOWS}
        lit_env = max([e for e in E_SWEEP if per_e[str(e)]["literal_holds"]], default=None)
        bnd_env = max([e for e in E_SWEEP if per_e[str(e)]["bound_holds"]], default=None)
        s1a = all(per_e[str(e)]["literal_holds"] for e in S1_E_LEVELS)
        s1b = all(per_e[str(e)]["bound_holds"] for e in S1_E_LEVELS)
        return {"per_e": per_e, "largest_e_literal": lit_env, "largest_e_bound": bnd_env,
                "s1a_met": s1a, "s1b_met": s1b}
    s1 = {"L1": s1_arm("L1"), "L2": s1_arm("L2"), "n_windows_required": S1_MIN_WINDOWS,
          "e_levels": list(S1_E_LEVELS), "met": None}
    s1["met"] = s1["L1"]["s1a_met"]
    s1["vacuity_note"] = {"L1_cells_under_floor_at_every_e": [
        w for w in good if all((r.get("L1", {}).get("whiteness", {}).get("under_floor") is True)
                               for r in AG if r["window"] == w and "L1" in r)]}

    # ---- S2 -------------------------------------------------------------
    def onset_table(arm):
        cells = [r for r in _cells(rows, arm) if (arm != "A" or r["window"] in good)]
        out = {}
        for w in sorted({r["window"] for r in cells}):
            rw = [r for r in cells if r["window"] == w]
            e_med, e_p99, e_sec20 = onset(rw)
            by_e = {r["e_deg"]: r for r in rw}
            out[w] = {"e_star_med": e_med, "e_star_p99": e_p99, "e_sec20_ptp_0.5px": e_sec20,
                      "P_ptp_at_e_star_med": None if e_med is None else by_e[e_med]["P_ptp_px"],
                      "P_rms_at_e_star_med": None if e_med is None else by_e[e_med]["P_rms_px"],
                      "sec20_within_one_step": (None if e_med is None or e_sec20 is None
                                                else abs(E_SWEEP.index(e_med) - E_SWEEP.index(e_sec20)) <= 1),
                      "P_rms_at_30": by_e[30]["P_rms_px"] if 30 in by_e else None,
                      "pass_by_e": {str(e): by_e[e].get("pass") for e in E_SWEEP if e in by_e},
                      "status_by_e": {str(e): by_e[e].get("status") for e in E_SWEEP if e in by_e},
                      "G_median_by_e": {str(e): _g_median(by_e[e]) for e in E_SWEEP if e in by_e},
                      "G_p99_by_e": {str(e): _g_p99(by_e[e]) for e in E_SWEEP if e in by_e}}
        return out
    s2_tab = onset_table("A")
    s2 = {"per_window": s2_tab,
          "n_with_onset_med": sum(1 for v in s2_tab.values() if v["e_star_med"] is not None),
          "sec20_predicts_within_one_step": sum(1 for v in s2_tab.values() if v["sec20_within_one_step"]),
          "sec20_early_by_2x_or_more": sum(1 for v in s2_tab.values() if v["e_star_med"] is not None and v["e_sec20_ptp_0.5px"] is not None
                                           and v["e_sec20_ptp_0.5px"] > 0 and v["e_star_med"] / v["e_sec20_ptp_0.5px"] >= 2.0),
          "never_rejected": all(r.get("status") != "REJECTED" for r in AG),
          "pass_at_every_e": all(r.get("pass") for r in AG),
          "met": bool(n_good > 0 and len(s2_tab) == n_good)}

    # ---- S3 -------------------------------------------------------------
    n_cells, n_fired, n_fired_perm = 0, 0, 0
    for w, v in s2_tab.items():
        if v["e_star_med"] is None:
            continue
        for r in AG:
            if r["window"] == w and r["e_deg"] >= v["e_star_med"] and "G" in r:
                n_cells += 1
                n_fired += int(bool(r["G"]["signature"]["fired"]))
                n_fired_perm += int(bool(r["G"]["signature"]["fired_under_pixel_permutation"]))
    frac = n_fired / n_cells if n_cells else None
    s3 = {"n_cells_at_or_above_onset": n_cells, "n_fired_shift_null": n_fired,
          "n_fired_pixel_perm": n_fired_perm, "fraction": frac,
          "pixel_perm_fires_at_e0": e0_fires_perm, "s0_v_held": s0_v,
          "met": bool(n_cells and frac >= S3_MIN_FRACTION and s0_v)}

    # ---- S4 -------------------------------------------------------------
    sel = [r for r in AG if r.get("model_dof") is not None]
    e_v = np.array([r["e_deg"] for r in sel], float)
    dof = np.array([r["model_dof"] for r in sel], float)
    if len(sel) >= 3 and np.ptp(dof) > 0:
        rho_a, p_a = stats.spearmanr(dof, e_v)
    else:
        rho_a, p_a = (0.0 if len(sel) >= 3 else float("nan")), float("nan")
    hb = [r for r in AG if r.get("heldout_best_px") is not None]
    if len(hb) >= 3:
        rho_b, p_b = stats.spearmanr([r["heldout_best_px"] for r in hb], [r["e_deg"] for r in hb])
    else:
        rho_b, p_b = float("nan"), float("nan")
    model_counts = {str(e): {} for e in E_SWEEP}
    tie = {}
    for e in E_SWEEP:
        ce = [r for r in AG if r["e_deg"] == e]
        for r in ce:
            model_counts[str(e)][str(r.get("model"))] = model_counts[str(e)].get(str(r.get("model")), 0) + 1
        tb = [r["decided_by_tie_break"] for r in ce if r.get("decided_by_tie_break") is not None]
        tie[str(e)] = (sum(tb) / len(tb)) if tb else None
    tie_e = [(e, tie[str(e)]) for e in E_SWEEP if tie[str(e)] is not None]
    s4 = {"s4a": {"rho": float(rho_a), "p": float(p_a), "n": len(sel),
                  "met": bool(np.isfinite(rho_a) and rho_a > S4A_MIN_RHO and p_a < S4A_MAX_P),
                  "vacuous_single_model": bool(len(sel) and np.ptp(dof) == 0)},
          "s4b": {"rho": float(rho_b), "p": float(p_b), "n": len(hb), "met": bool(np.isfinite(rho_b) and rho_b > S4B_MIN_RHO)},
          "model_by_e": model_counts, "tie_break_fraction_by_e": tie,
          "tie_break_spearman_vs_e": spearman([t for _, t in tie_e], [e for e, _ in tie_e]) if len(tie_e) >= 3 else None,
          "met": None}
    s4["met"] = bool(s4["s4a"]["met"] and s4["s4b"]["met"])

    # ---- S5 -------------------------------------------------------------
    def gmean(vals):
        v = [x for x in vals if x is not None and x > 0]
        return float(np.exp(np.mean(np.log(v)))) if v else None
    gA = gmean([v["P_rms_at_e_star_med"] for v in s2_tab.values()])
    tabB, tabC = onset_table("B"), onset_table("C")
    gB, gC = gmean([v["P_rms_at_e_star_med"] for v in tabB.values()]), gmean([v["P_rms_at_e_star_med"] for v in tabC.values()])
    c_ok = bool(gA and gC and gA / S5_FACTOR <= gC <= gA * S5_FACTOR)
    b_cross = sum(1 for v in tabB.values() if v["e_star_med"] is not None)
    if b_cross:
        b_ok = bool(gA and gB and gA / S5_FACTOR <= gB <= gA * S5_FACTOR)
        b_clause = "geometric-mean onset within 2x"
    else:
        mx = max([v["P_rms_at_30"] for v in tabB.values() if v["P_rms_at_30"] is not None], default=None)
        b_ok = bool(gA is not None and mx is not None and mx < gA)
        b_clause = "no tile crosses; max P_rms at 30 deg below arm A's onset"
    s5 = {"arm_A_gmean_P_rms_onset": gA, "arm_C_gmean_P_rms_onset": gC, "arm_B_gmean_P_rms_onset": gB,
          "arm_B_n_crossing": b_cross, "arm_B_clause": b_clause, "arm_B_max_P_rms_at_30": max([v["P_rms_at_30"] for v in tabB.values() if v["P_rms_at_30"] is not None], default=None),
          "arm_C_met": c_ok, "arm_B_met": b_ok, "met": bool(c_ok and b_ok),
          "arm_B_per_window": tabB, "arm_C_per_window": tabC}

    # ---- secondaries (section 8) -------------------------------------------
    occ_falls = 0
    for w in good:
        rw = sorted([r for r in AG if r["window"] == w and r.get("coverage")], key=lambda r: r["e_deg"])
        if len(rw) >= 3:
            rho = spearman([r["coverage"]["grid_occupancy"] for r in rw], [r["e_deg"] for r in rw])
            occ_falls += int(rho < 0)
    gtf = {}
    for tag in ("dtm", "sldem"):
        first = {}
        for w in good:
            rw = sorted([r for r in AG if r["window"] == w and r.get("gt_free_signature", {}).get(tag)], key=lambda r: r["e_deg"])
            first[w] = next((r["e_deg"] for r in rw if r["gt_free_signature"][tag]["fired"]), None)
        ratios = [first[w] / s2_tab[w]["e_star_med"] for w in good if first[w] and s2_tab.get(w, {}).get("e_star_med")]
        gtf[tag] = {"first_fire_e_by_window": first, "first_fire_over_e_star_med": ratios,
                    "fires_by_e": {str(e): sum(1 for r in AG if r["e_deg"] == e and r.get("gt_free_signature", {}).get(tag, {}).get("fired")) for e in E_SWEEP}}
    perm_fires_by_e = {str(e): sum(1 for r in AG if r["e_deg"] == e and r.get("G", {}).get("signature", {}).get("fired_under_pixel_permutation")) for e in E_SWEEP}
    shift_fires_by_e = {str(e): sum(1 for r in AG if r["e_deg"] == e and r.get("G", {}).get("signature", {}).get("fired")) for e in E_SWEEP}
    r2_beats_by_e = {null: {str(e): sum(1 for r in AG if r["e_deg"] == e and r.get("G", {}).get("signature", {}).get(f"r2_beats_{null}_null")) for e in E_SWEEP}
                     for null in ("shift", "perm")}
    sec = {"occupancy_falls_with_e_windows": occ_falls, "n_windows": n_good,
           "gt_free_signature": gtf, "pixel_perm_fires_by_e": perm_fires_by_e, "shift_fires_by_e": shift_fires_by_e,
           "r2_beats_null_by_e": r2_beats_by_e,
           "status_counts": {st: sum(1 for r in AG if r.get("status") == st) for st in ("VERIFIED", "REJECTED", "INCONCLUSIVE")},
           "refinement_shift_by_e": {str(e): {"median_px": _median_or_none([r["refinement_shift"]["median_px"] for r in AG if r["e_deg"] == e and r.get("refinement_shift", {}).get("median_px") is not None]),
                                               "median_px_on_slopes_ge_5deg": _median_or_none([r["refinement_shift"]["median_px_on_slopes_ge_5deg"] for r in AG if r["e_deg"] == e and r.get("refinement_shift", {}).get("median_px_on_slopes_ge_5deg") is not None])}
                                     for e in E_SWEEP},
           "sldem_minus_dtm_by_window": {w: windows_meta[w].get("sldem_minus_dtm_m") for w in good if w in windows_meta}}

    # ---- predictions (section 4), measured counterpart beside each ---------
    pred = {
        "S0_MET": {"predicted": True, "measured": s0["met"]},
        "S1a_L1_not_met_at_e_ge_2": {"predicted": True, "measured_largest_e_literal_L1": s1["L1"]["largest_e_literal"]},
        "S1a_L2_not_met_at_e_ge_3": {"predicted": True, "measured_largest_e_literal_L2": s1["L2"]["largest_e_literal"]},
        "S1b_L1_to_10": {"predicted_largest_e": 10, "measured": s1["L1"]["largest_e_bound"]},
        "S1b_L2_to_5": {"predicted_largest_e": 5, "measured": s1["L2"]["largest_e_bound"]},
        "S2_e_star_med_range": {"predicted": "3-10 long, 5-15 short", "measured": {w: v["e_star_med"] for w, v in s2_tab.items()}},
        "S2_P_rms_at_onset_0.3_to_0.7": {"measured": {w: v["P_rms_at_e_star_med"] for w, v in s2_tab.items()}},
        "sec20_ptp_early_by_2x_on_ge_12": {"predicted": True, "measured_count": s2["sec20_early_by_2x_or_more"]},
        "pass_at_every_e": {"predicted": True, "measured": s2["pass_at_every_e"]},
        "never_rejected": {"predicted": True, "measured": s2["never_rejected"]},
        "S3_MET": {"predicted": True, "measured": s3["met"]},
        "pixel_perm_fires_ge_3_at_e0": {"predicted": True, "measured": e0_fires_perm},
        "S4a_rho_0.3_to_0.5_saturating_affine": {"predicted": True, "measured_rho": s4["s4a"]["rho"], "model_by_e": model_counts},
        "S4b_rho_gt_0.7": {"predicted": True, "measured_rho": s4["s4b"]["rho"]},
        "tie_break_falls_with_e": {"predicted": True, "measured_spearman": s4["tie_break_spearman_vs_e"]},
        "S5_MET": {"predicted": True, "measured": s5["met"]},
        "occupancy_falls_on_ge_12": {"predicted": True, "measured": occ_falls},
        "gt_free_dtm_first_fire_ge_2x_e_star": {"predicted": True, "measured_ratios": gtf["dtm"]["first_fire_over_e_star_med"]},
    }
    return {"S0": s0, "S1": s1, "S2": s2, "S3": s3, "S4": s4, "S5": s5, "secondary": sec, "predictions": pred}


# ---------------------------------------------------------------------------
# S0(iii): the dense warp against siim.geometry.warp on an affine field
# ---------------------------------------------------------------------------
def s0_iii_reproduction(seed: int = 0) -> dict:
    """On a field that is exactly a y-translation the dense warp must equal
    ``siim.geometry.warp`` and the dense error must equal ``endpoint_error``."""
    from siim.geometry import endpoint_error, translation, warp
    rng = np.random.default_rng(seed)
    img = ndimage.gaussian_filter(rng.normal(size=(96, 80)), 1.5)
    ty = 3.25
    d = np.full(img.shape, ty)                       # p = q + (0, -ty)  ->  T: p -> q is +ty
    obl, ok = dense_warp(img, np.ones(img.shape, bool), d)
    # warp takes the forward source->reference map q -> p = q - (0, ty) and inverts it internally
    ref, ok_ref = warp(img, translation(0.0, -ty))
    both = ok & ok_ref
    max_img = float(np.nanmax(np.abs(obl[both] - ref[both])))
    q = pixel_grid(img.shape, step=GRID_STEP)
    p = forward_points(d, q)
    t_hat = translation(0.4, ty + 0.2)
    err = np.hypot(*(t_hat.apply(p) - q).T)
    ee = endpoint_error(t_hat, translation(0.0, ty), img.shape, step=GRID_STEP)
    return {"max_image_diff": max_img, "dense_median_diff": abs(float(np.median(err)) - ee.median),
            "dense_max_diff": abs(float(err.max()) - ee.max),
            "met": bool(max_img < S0_REPRODUCE_TOL and abs(float(np.median(err)) - ee.median) < S0_REPRODUCE_TOL)}


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="exp017_results.json")
    ap.add_argument("--arm", choices=["A", "B", "C"], action="append")
    ap.add_argument("--quick", action="store_true", help="smoke test: one window per arm, e in {0, 10}, 50 null draws")
    args = ap.parse_args()
    out_path = Path(args.out) if Path(args.out).is_absolute() else OUT / args.out
    if out_path.exists():
        raise SystemExit(f"{out_path} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    sweep = (0, 10) if args.quick else E_SWEEP
    n_null = 50 if args.quick else N_NULL
    arms = args.arm or ["A", "B", "C"]

    print(f"{STAGE}: S0(iii) reproduction control", flush=True)
    s0iii = s0_iii_reproduction()
    print(f"  image diff {s0iii['max_image_diff']:.2e}  dense-median diff {s0iii['dense_median_diff']:.2e}  met={s0iii['met']}", flush=True)

    rows, excluded, meta = [], [], {}
    wi = 0
    for arm, fn in (("A", arm_a_windows), ("B", arm_b_windows), ("C", arm_c_windows)):
        if arm not in arms:
            continue
        print(f"arm {arm}", flush=True)
        for win in fn(args.quick, excluded):
            for e in sweep:
                row = run_cell(win, float(e), wi, E_SWEEP.index(e), n_null)
                row["e_deg"] = int(e)
                rows.append(row)
                print_row(row)
            meta[win.name] = win.meta
            wi += 1

    crit = evaluate(rows, meta)
    doc = {
        "stage": STAGE, "question": __doc__.split("\n\n")[1].strip(),
        "frozen": {"e_sweep_deg": list(E_SWEEP), "grid_step_px": GRID_STEP, "min_grid_points": MIN_GRID_POINTS,
                   "joint_valid_min_px": JOINT_VALID_MIN_PX, "cells": CELLS, "cell_min_points": CELL_MIN_POINTS,
                   "n_null": N_NULL, "shift_min_fraction": SHIFT_MIN_FRAC, "null_seed": NULL_SEED,
                   "white_floor_px": WHITE_FLOOR_PX, "median_bound_px": MEDIAN_BOUND_PX, "p99_bound_px": P99_BOUND_PX,
                   "s1_min_windows": S1_MIN_WINDOWS, "s1_e_levels": list(S1_E_LEVELS), "s3_min_fraction": S3_MIN_FRACTION,
                   "engine": ENGINE, "base": BASE, "failure_rule": f"n_inliers <= {RULE} fails (D-023)",
                   "direction": "source = constructed oblique, reference = nadir", "view_azimuth": "image up (-y)",
                   "dem_resampling": "bilinear through both products' GeoTIFF geometry (PixelIsArea centres); stated deviation from P5's nearest repeat",
                   "s0_v_reading": "at e = 0 the predicted slope is 0 so detector clauses 2-3 cannot pass; the null calibration counts clause 1 alone (R^2 above the shift null's p95)",
                   "L1_cell_lookup": "a grid point's cell is taken from the GLOBAL transform's prediction of its reference position, as a deployed pipeline would, not from the ground truth",
                   "quick": args.quick, "arms": arms},
        "s0_iii_reproduction": s0iii,
        "windows": meta, "excluded": excluded,
        "criteria": crit, "rows": rows,
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
        "total_runtime_s": round(time.time() - t_start, 1),
        "claims_not_supported": [
            "Not a real stereo or off-nadir result: the oblique is the nadir image's own photons displaced by a DEM; every error bounds precision, not accuracy.",
            "No occlusion, no view-dependent radiometry, no sensor model, no foreshortening.",
            "Ground truth is exact only relative to the TMC-2 DTM (stated height RMSE 20.9 m).",
            "One region, mare, one TMC-2 strip; other sensors' numbers are arithmetic.",
            "assess(), select_model and every constant untouched; a passed wrong map is a recorded blind spot, not a patch.",
            "One engine.",
        ],
    }
    out_path.write_text(json.dumps(_clean(doc), indent=1, default=_json_default), encoding="utf-8")
    c = crit
    print(f"\nS0 {c['S0']['met']} (windows {len(c['S0']['windows_reported'])}/{c['S0']['n_windows']}, null fires {c['S0']['v_null_calibration']['shift_null_fires_at_e0']})"
          f" | S1a L1 {c['S1']['L1']['s1a_met']} env {c['S1']['L1']['largest_e_literal']} | S1b L1 env {c['S1']['L1']['largest_e_bound']}"
          f" | S2 onsets {c['S2']['n_with_onset_med']} | S3 {c['S3']['met']} ({c['S3']['fraction']}) | S4a {c['S4']['s4a']['rho']:.3f} S4b {c['S4']['s4b']['rho']:.3f}"
          f" | S5 {c['S5']['met']}")
    print(f"wrote {out_path} in {doc['total_runtime_s']}s")


def _clean(o):
    """NaN/inf -> null so the artefact is strict JSON; numpy scalars -> Python."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return float(o) if np.isfinite(o) else None
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    return o


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, float) and not np.isfinite(o):
        return None
    raise TypeError(str(type(o)))


if __name__ == "__main__":
    main()
