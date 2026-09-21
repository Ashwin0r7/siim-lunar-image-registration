"""EXP-016 — the scale ladder to 320:1 on real lunar texture, run exactly as
Part 1 froze it (docs/stages/EXP-016_scale_ladder.md, commit f7d94f5).

Every real pair the frozen pipeline registers at its native rung, inside the
illumination envelope (Δinc ≤ 15°), is degraded through a stated PSF to a
common coarser GSD and matched there — the architecture's answer to scale —
at r ∈ {2, 4, 8, 16, 32, 64, 128, 320}. Arms:

    D  degrade both to the coarse GSD (the architecture)
    N  fine at k = 2 against the coarse image (the counterfactual, RL-051b)
    X  central-quarter crop at r/2: same coarse pixel count as the full r cell,
       half the ratio — the one cell that separates starvation from descriptor
    L  NCC localisation of a 4096-line tile inside a long window (what §345
       says 320:1 physically is)

Nothing is re-implemented: the degradation operator is
``siim.preprocessing.degrade.degrade_to_gsd`` (``psf = 0`` IS the recorded box
average, which is what makes S0's operator gate bit-exact), orientation is
``north_up_east_right`` through ``run_real_data_07.run_edge``'s route, the
geometry check is ``run_exp007.geometry_check``, registration is
``siim.pipeline.register_pair`` with its defaults.

    python scripts/run_exp016.py
    python scripts/run_exp016.py --quick --out <scratch>   # tests / smoke only
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.baselines import learned_available  # noqa: E402
from siim.geometry import Transform, endpoint_error, pixel_grid  # noqa: E402
from siim.ingest.footprint import TileWindow  # noqa: E402
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

STAGE = "EXP-016"
DATA = ROOT / "data"
OUT = ROOT / "experiments" / STAGE
RULE = _e7.N_INLIERS_FAILURE_RULE
BASE = {"model": "affine", "ransac_threshold": 3.0, "seed": 0}
#: The same constants in run_exp007.run_engine's spelling (its reproduction route).
E7_BASE = {"model": "affine", "ransac_threshold_px": 3.0, "seed": 0}

# -- Part 1 section 3, declared in full -------------------------------------
LADDER = (2, 4, 8, 16, 32, 64, 128, 320)
ARM_D_RUNGS = (4, 8, 16, 32, 64, 128, 320)
ARM_N_RUNGS = (4, 8, 16, 32)
ARM_X_RUNGS = (8, 16, 32, 64, 128, 320)          # cropped cell runs at r / 2
ARM_L_RUNGS = (32, 64, 128, 320)
B4L_RUNGS = (8, 16, 32, 64, 128, 320)
PSF_FWHM_COARSE_PX = 1.0
NATIVE_K = 2
NATIVE_FINE_K = 2                                # arm N's source rung

#: Population A: the 14 REAL-DATA-07 pairs with Δinc ≤ 15° (Part 1 §3 table),
#: (window, edge, native n_inliers to reproduce). Direction is the row's
#: ``edge``, never ``pair`` (E-036).
POP_A = [
    ("RD03", "nac.m1271742202lc -> nac.m1182331886lc", 1656),
    ("RD03", "nac.m1182331886lc -> nac.m1212932972lc", 5437),
    ("RD03", "nac.m1236465772rc -> nac.m1175268993rc", 8239),
    ("RD03", "nac.m1212932972lc -> nac.m1363396554rc", 3486),
    ("RD03", "nac.m1452560468lc -> nac.m1335207975rc", 5392),
    ("RD03", "nac.m1096350825rc -> nac.m1142297886lc", 7554),
    ("RD03", "nac.m1199981485rc -> nac.m1142297886lc", 4),
    ("RD03", "nac.m1335207975rc -> nac.m1142297886lc", 5),
    ("RD04", "nac.m1299958135lc -> nac.m1315225542lc", 2726),
    ("RD04", "nac.m1299958135lc -> nac.m1271742202lc", 1608),
    ("RD04", "nac.m1315225542lc -> nac.m1271742202lc", 2138),
    ("RD04", "nac.m1271742202lc -> nac.m1341069775rc", 47),
    ("RD04", "nac.m1212932972lc -> nac.m1363396554rc", 2597),
    ("RD04", "nac.m1341069775rc -> nac.m1212932972lc", 8),
]
#: Population B: the two low-Δinc long windows and their EXP-007 counts
#: (tier 1 at k = 2; tier 2 at k = 4 / 8 / 16 / 32), box average, EXP-007's route.
#: The k = 2 count is EXP-007 TIER 1, which ran on the recorded 4096-line tiles
#: (``real_triplet_geo_manifest`` / ``real_quad_d_geo_manifest``), not on the
#: long window -- the long window at k = 2 gives ~42 000 inliers and is not a
#: recorded number. Part 1 §3 lists the count without saying which window; it
#: is reproduced where it was recorded, and that is stated for Part 2.
POP_B = [
    ("RD03-target", "exp007_long_triplet_abc_manifest.json",
     "nac.m1335207975rc -> nac.m1452560468lc", {4: 9460, 8: 3054, 16: 1373, 32: 566},
     ("REAL-DATA-03", "real_triplet_geo_manifest.json", 5365)),
    ("RD04-target", "exp007_long_triplet_abd_manifest.json",
     "nac.m1299958135lc -> nac.m1271742202lc", {4: 3693, 8: 1665, 16: 693, 32: 243},
     ("REAL-DATA-04", "real_quad_d_geo_manifest.json", 1656)),
]
#: Above this many inliers the verdict engine's coverage statistic (an exact
#: N x N distance matrix, siim.evaluation.coverage) needs tens of GB; the cell
#: is then recorded from the engine stage alone and says so. A runner-side
#: guard, not a change to src/ (Part 1 §7: assess() untouched).
COVERAGE_POINT_CAP = 20000

# -- Part 1 section 4, frozen ---------------------------------------------
S0_SELF_SHIFT_PX = 0.05
S0_SELF_MIN_N_SHIFT = 1024
S0_SELF_MIN_N_INLIERS = 4096
S1_MIN_PAIRS = 10          # of 11
S2_CONCORDANCE = 0.80
S2_ALPHA = 0.05
S3_ALPHA = 0.05
S4_CONSISTENCY_PX = 1.0
S4_FRACTION = 0.90
S4_MIN_GRID = 50
S5_PSR = 5.0
S5_MIN_TOL_PX = 1.5
CONSISTENCY_GRID_STEP = 8
SELF_SHIFT_MULT = 3
PSR_EXCLUSION = 5


# ---------------------------------------------------------------------------
# frames and windows
# ---------------------------------------------------------------------------
class Window:
    """One raw window of one frame: everything a cell needs, from the archive."""

    def __init__(self, ctx, line0: int, sample0: int, n_lines: int, n_samples: int,
                 raw: np.ndarray | None = None):
        self.ctx = ctx
        self.pdsid = ctx.pdsid
        self.corners = ctx.corners
        self.scaled_pixel_m = ctx.scaled_pixel_m
        self.line0, self.sample0 = int(line0), int(sample0)
        self.n_lines, self.n_samples = int(n_lines), int(n_samples)
        self._raw = raw

    def raw(self) -> np.ndarray:
        if self._raw is None:
            self._raw = self.ctx.raw()
        return self._raw

    def window(self, k: int) -> TileWindow:
        return TileWindow(self.line0, self.sample0, self.n_lines, self.n_samples, k)

    def centre(self) -> tuple[float, float]:
        return (self.line0 + (self.n_lines - 1) / 2, self.sample0 + (self.n_samples - 1) / 2)

    def handedness(self) -> float:
        return handedness(self.corners, *self.centre())

    def cropped_quarter(self) -> "Window":
        """Central quarter (half the extent on each axis), exact on the native grid."""
        r0, c0 = self.n_lines // 4, self.n_samples // 4
        h, w = self.n_lines // 2, self.n_samples // 2
        return Window(self.ctx, self.line0 + r0, self.sample0 + c0, h, w,
                      raw=self.raw()[r0:r0 + h, c0:c0 + w])

    def sub(self, line0: int, sample0: int, n_lines: int, n_samples: int) -> "Window":
        r0, c0 = line0 - self.line0, sample0 - self.sample0
        if r0 < 0 or c0 < 0 or r0 + n_lines > self.n_lines or c0 + n_samples > self.n_samples:
            raise ValueError("sub-window not inside the window")
        return Window(self.ctx, line0, sample0, n_lines, n_samples,
                      raw=self.raw()[r0:r0 + n_lines, c0:c0 + n_samples])

    def coarse(self, r: int, psf: float = PSF_FWHM_COARSE_PX) -> np.ndarray:
        """C_r: PSF-degrade the RAW window by r, then the recorded percentile stretch."""
        return _e7.stretch(degrade_to_gsd(self.raw(), r, psf_fwhm_coarse_px=psf))

    def native_box(self, k: int) -> np.ndarray:
        """The recorded route: box decimate, then stretch (run_exp007.FrameContext.img)."""
        return _e7.stretch(_e7.decimate(self.raw(), k))

    def oriented(self, img: np.ndarray):
        line, sample = self.centre()
        return north_up_east_right(img, self.corners, line=line, sample=sample)


def load_contexts(products: dict):
    """Every tile dict this stage needs, keyed by (window, pdsid)."""
    out: dict = {}
    for wname, mname in _rd7.WINDOWS.items():
        man = json.loads((DATA / "manifests" / mname).read_text(encoding="utf-8"))
        target = tuple(man["target_ground_point_lon_lat"])
        for t in man["tiles"]:
            ctx = _e7.FrameContext(t["pdsid"], t, products, target)
            out[(wname, t["pdsid"])] = Window(ctx, t["line0"], t["sample0"], t["n_lines"], t["n_samples"])
    for tname, mname, _edge, _counts, (t1name, t1man, _n) in POP_B:
        for name, mn in ((tname, mname), (t1name, t1man)):
            man = json.loads((DATA / "manifests" / mn).read_text(encoding="utf-8"))
            target = tuple(man["target_ground_point_lon_lat"])
            for t in man["tiles"]:
                ctx = _e7.FrameContext(t["pdsid"], t, products, target)
                out[(name, t["pdsid"])] = Window(ctx, t["line0"], t["sample0"], t["n_lines"], t["n_samples"])
    return out


def recorded_rows() -> dict:
    """The B1 north-up rows of the amended RD-07 run, keyed by (window, edge)."""
    out = {}
    for w in ("rd03", "rd04"):
        doc = json.loads((ROOT / "experiments" / "REAL-DATA-07" / f"rows_{w}_nue.json").read_text(encoding="utf-8"))
        for r in doc["rows"]:
            if r.get("engine") == "b1" and r.get("north_up") is True:
                out[(w.upper(), r["edge"])] = r
    return out


def exp007_rows() -> dict:
    doc = json.loads((ROOT / "experiments" / "EXP-007" / "exp007_results.json").read_text(encoding="utf-8"))
    out = {}
    for r in doc["rows"]:
        if r.get("arm") == "none":
            out[(r["edge"], int(r["decimation"]))] = r
    return out


# ---------------------------------------------------------------------------
# one registration cell
# ---------------------------------------------------------------------------
def _n_valid(img: np.ndarray) -> int:
    return int(np.isfinite(img).sum())


def register_oriented(ws: Window, ks: int, a_img: np.ndarray, wr: Window, kr: int,
                      b_img: np.ndarray, engine: str = "B1") -> dict:
    """Orient both images (E-037), register, map the final transform back to
    ORIGINAL (decimated, un-oriented) tile pixels and check it against the
    archive geometry -- run_real_data_07.run_edge's route, with the pipeline."""
    ra, rb = ws.oriented(a_img), wr.oriented(b_img)
    t0 = time.perf_counter()
    try:
        res = register_pair(ra.image, rb.image, engine=engine, **BASE)
        note = None
    except MemoryError as exc:
        # The engine ran; the verdict's coverage matrix did not fit. Keep the
        # estimate stage's result and say what was skipped (COVERAGE_POINT_CAP).
        from siim.baselines import run_baseline
        base = run_baseline(engine, ra.image, rb.image, model=BASE["model"],
                            ransac_threshold=BASE["ransac_threshold"], seed=BASE["seed"])
        res = _EngineOnly(base, engine)
        note = f"pipeline stages refine/reestimate/verify skipped: MemoryError in the verdict's coverage ({exc})"
    wall = time.perf_counter() - t0
    s = res.summary()
    rec = {
        "n_keypoints_src": int(len(res.baseline.src_features)),
        "n_keypoints_dst": int(len(res.baseline.dst_features)),
        "n_putative": s["n_putative"], "n_inliers": s["n_inliers"], "n_refined": s["n_refined"],
        "pass": bool(s["n_inliers"] > RULE),
        "status": s["status"], "confidence": s["confidence"],
        "model": s["model"], "model_selected_by": s["model_selected_by"],
        "heldout_px": s["heldout_px"], "decided_by_tie_break": s["decided_by_tie_break"],
        "fit_rmse_px": float(res.baseline.ransac.inlier_rmse) if res.baseline.ransac is not None else None,
        "fit_rmse_is_not_accuracy": True,
        "shape_src": list(ra.image.shape), "shape_dst": list(rb.image.shape),
        "n_valid_src": _n_valid(ra.image), "n_valid_dst": _n_valid(rb.image),
        "north_up": {"src": ra.record, "dst": rb.record},
        "wall_s": wall,
    }
    if note:
        rec["pipeline_note"] = note
    if res.transform is not None:
        tf = rb.inverse @ res.transform @ ra.forward
        rec["transform_matrix_original_pixels"] = np.asarray(tf.matrix).tolist()
        rec["transform_matrix"] = np.asarray(res.transform.matrix).tolist()
        if res.initial_transform is not None:
            ti = rb.inverse @ res.initial_transform @ ra.forward
            rec["initial_transform_matrix_original_pixels"] = np.asarray(ti.matrix).tolist()
        rec["_tf_original"] = tf
    else:
        tf = None
    if res.n_inliers >= 3:
        from siim.evaluation.coverage import coverage_metrics
        pts = res.src_points[res.inlier_mask]
        if pts.shape[0] > COVERAGE_POINT_CAP:
            pts = pts[np.random.default_rng(BASE["seed"]).choice(pts.shape[0], COVERAGE_POINT_CAP, replace=False)]
            rec["coverage_subsampled_to"] = COVERAGE_POINT_CAP
        cov = coverage_metrics(pts, ra.image.shape)
        rec["coverage_occupancy"] = float(cov.grid_occupancy)
        rec["coverage_max_uncovered_disc_ratio"] = float(cov.max_uncovered_disc_ratio)
    rec["geometry"] = _e7.geometry_check(tf, ws.corners, ws.window(ks), wr.corners,
                                         wr.window(kr), BASE["model"])
    g = rec["geometry"].get("verdict", "")
    rec["wrong_pass"] = bool(rec["pass"] and g.startswith("INCONSISTENT"))
    rec["success"] = bool(rec["pass"] and not rec["wrong_pass"])
    return rec


class _EngineOnly:
    """A RegistrationResult look-alike for the MemoryError fallback: the
    estimate stage only, no refinement, no re-estimation, no verdict."""

    def __init__(self, base, engine: str):
        self.baseline, self.engine = base, engine
        p = np.asarray(base.matches.src_points, float).reshape(-1, 2)
        m = np.asarray(base.inlier_mask, bool).reshape(-1) if np.size(base.inlier_mask) else np.zeros(p.shape[0], bool)
        self.src_points, self.inlier_mask = p, m
        self.transform, self.initial_transform = base.transform, base.transform
        self.n_inliers = int(m.sum())

    def summary(self) -> dict:
        return {"n_putative": int(self.src_points.shape[0]), "n_inliers": self.n_inliers, "n_refined": 0,
                "status": "NOT ASSESSED", "confidence": None,
                "model": None if self.transform is None else self.transform.model,
                "model_selected_by": "engine_default (verdict skipped)", "heldout_px": None,
                "decided_by_tie_break": None}


# ---------------------------------------------------------------------------
# rung consistency (Part 1 section 2.2(c))
# ---------------------------------------------------------------------------
def rung_map(t_native: Transform, w_src_native: TileWindow, w_dst_native: TileWindow,
             w_src_r: TileWindow, w_dst_r: TileWindow) -> Transform:
    """S_r ∘ T_2 ∘ S_r⁻¹: the native-rung transform expressed on the rung-r grids,
    through TileWindow's C4 offset in both directions."""
    def s(win_from: TileWindow, win_to: TileWindow) -> Transform:
        # (x, y) in win_from grid -> frame -> (x, y) in win_to grid; affine in x, y
        kf, kt = win_from.decimation, win_to.decimation
        of, ot = (kf - 1) / 2.0, (kt - 1) / 2.0
        sc = kf / kt
        tx = (win_from.sample0 + of - win_to.sample0 - ot) / kt
        ty = (win_from.line0 + of - win_to.line0 - ot) / kt
        return Transform(np.array([[sc, 0, tx], [0, sc, ty], [0, 0, 1.0]]), "similarity")
    return s(w_dst_native, w_dst_r) @ t_native @ s(w_src_r, w_src_native)


def rung_consistency(t_r: Transform | None, t_pred: Transform, src_img: np.ndarray,
                     r: int, native_pixel_m: float) -> dict:
    if t_r is None:
        return {"status": "no transform"}
    grid = pixel_grid(src_img.shape, step=CONSISTENCY_GRID_STEP)
    valid = np.isfinite(src_img[grid[:, 1].astype(int), grid[:, 0].astype(int)])
    grid = grid[valid]
    if grid.shape[0] < S4_MIN_GRID:
        return {"status": "CANNOT CHECK", "n_grid": int(grid.shape[0])}
    d = np.sqrt(((t_r.apply(grid) - t_pred.apply(grid)) ** 2).sum(axis=1))
    d = d[np.isfinite(d)]
    med, p90 = float(np.median(d)), float(np.percentile(d, 90))
    return {"status": "ok", "n_grid": int(grid.shape[0]),
            "median_coarse_px": med, "p90_coarse_px": p90,
            "median_m": med * r * native_pixel_m, "p90_m": p90 * r * native_pixel_m,
            "within_1px": bool(med <= S4_CONSISTENCY_PX)}


# ---------------------------------------------------------------------------
# S0(iv) self-scale control
# ---------------------------------------------------------------------------
def self_scale_control(w: Window, r: int) -> dict:
    """C_r(P) against C_r(P shifted by SELF_SHIFT_MULT * r native px on both
    axes). The shifted image's content sits SELF_SHIFT_MULT coarse px earlier
    on each axis, so the truth is a pure translation of -SELF_SHIFT_MULT."""
    s = SELF_SHIFT_MULT * r
    raw = w.raw()
    a = raw[: raw.shape[0] - s, : raw.shape[1] - s]
    b = raw[s:, s:]
    ca = _e7.stretch(degrade_to_gsd(a, r, psf_fwhm_coarse_px=PSF_FWHM_COARSE_PX))
    cb = _e7.stretch(degrade_to_gsd(b, r, psf_fwhm_coarse_px=PSF_FWHM_COARSE_PX))
    n = _n_valid(ca)
    rec = {"r": r, "n_coarse_px": n, "shape": list(ca.shape), "expected_shift_coarse_px": -SELF_SHIFT_MULT}
    if min(ca.shape) < 8:
        rec.update({"status": "image too small for the detector", "n_inliers": 0})
        return rec
    # The estimate stage only: this control measures the detector and the
    # estimator on identical texture; an identical-texture pair at r = 4 on a
    # long window returns ~10^4-10^5 inliers, beyond the verdict's O(N^2)
    # coverage statistic (COVERAGE_POINT_CAP).
    from siim.baselines import run_baseline
    res = _EngineOnly(run_baseline("B1", ca, cb, model=BASE["model"],
                                   ransac_threshold=BASE["ransac_threshold"], seed=BASE["seed"]), "B1")
    rec["n_inliers"] = res.n_inliers
    rec["n_keypoints_src"] = int(len(res.baseline.src_features))
    rec["stage"] = "estimate only (run_baseline B1); no refine, no verdict"
    if res.transform is not None:
        truth = Transform(np.array([[1, 0, -SELF_SHIFT_MULT], [0, 1, -SELF_SHIFT_MULT], [0, 0, 1.0]]), "translation")
        err = endpoint_error(res.transform, truth, ca.shape, step=4)
        rec["shift_error_coarse_px"] = err.median
        rec["model"] = res.transform.model
    rec["clause_shift"] = ("n/a (N < %d)" % S0_SELF_MIN_N_SHIFT if n < S0_SELF_MIN_N_SHIFT
                           else bool(rec.get("shift_error_coarse_px", np.inf) < S0_SELF_SHIFT_PX))
    rec["clause_inliers"] = ("n/a (N < %d)" % S0_SELF_MIN_N_INLIERS if n < S0_SELF_MIN_N_INLIERS
                             else bool(res.n_inliers > RULE))
    rec["status"] = "ok"
    return rec


# ---------------------------------------------------------------------------
# arm L: NCC localisation
# ---------------------------------------------------------------------------
def psr(ncc: np.ndarray) -> tuple[float, tuple[int, int], float]:
    """Peak-to-sidelobe ratio: peak over the standard deviation of the map
    outside a PSR_EXCLUSION x PSR_EXCLUSION box around the peak (Part 1 §2.1)."""
    m = np.asarray(ncc, float)
    m = np.where(np.isfinite(m), m, -np.inf)
    iy, ix = np.unravel_index(int(np.argmax(m)), m.shape)
    peak = float(m[iy, ix])
    mask = np.ones(m.shape, bool)
    h = PSR_EXCLUSION // 2
    mask[max(0, iy - h): iy + h + 1, max(0, ix - h): ix + h + 1] = False
    out = m[mask]
    out = out[np.isfinite(out)]
    sd = float(out.std()) if out.size > 1 else float("nan")
    return (peak / sd if sd > 0 else float("inf")), (iy, ix), peak


def localise(tmpl_w: Window, search_w: Window, r: int) -> dict:
    """NCC of the oriented coarse template inside the oriented coarse search
    window; the prediction goes tile centre -> ground -> search grid through
    the archive corner maps and the same orientation transforms."""
    t_img = tmpl_w.coarse(r)
    s_img = search_w.coarse(r)
    ot, os_ = tmpl_w.oriented(t_img), search_w.oriented(s_img)
    T, S = ot.image, os_.image
    rec = {"r": r, "template_shape": list(T.shape), "search_shape": list(S.shape),
           "template_n_px": int(T.size), "search_n_px": int(S.size)}
    wt, wsr = tmpl_w.window(r), search_w.window(r)
    # prediction: template centre (coarse, un-oriented) -> frame -> ground -> search grid
    rc, cc = (wt.shape[0] - 1) / 2.0, (wt.shape[1] - 1) / 2.0
    line, sample = wt.to_frame(rc, cc)
    try:
        lon, lat = tmpl_w.corners.lonlat_at(line, sample)
        lb, sb = search_w.corners.pixel_at(lon, lat)
    except ValueError:
        rec["status"] = "template centre outside the search frame by archive geometry"
        return rec
    rb, cb = wsr.from_frame(lb, sb)
    pred = os_.forward.apply(np.array([[cb, rb]]))[0]          # oriented search (x, y)
    tc = ot.forward.apply(np.array([[cc, rc]]))[0]             # oriented template (x, y)
    rec["predicted_xy_oriented"] = [float(pred[0]), float(pred[1])]
    # the geometry check's own floor at this rung: est = predicted -> err 0 -> floor returned
    pred_tf, _ = _e7._predict(tmpl_w.corners, wt, search_w.corners, wsr, BASE["model"])
    floor = None
    if pred_tf is not None:
        g = _e7.geometry_check(pred_tf, tmpl_w.corners, wt, search_w.corners, wsr, BASE["model"])
        floor = g.get("discrimination_floor_px")
    rec["geometry_floor_coarse_px"] = floor
    tol = max(S5_MIN_TOL_PX, floor if floor is not None else 0.0)
    rec["tolerance_coarse_px"] = tol
    if T.shape[0] > S.shape[0] or T.shape[1] > S.shape[1] or min(T.shape) < 2:
        rec["status"] = "template does not fit the search image"
        return rec
    fill_t = float(np.nanmedian(T)) if np.isfinite(T).any() else 0.0
    fill_s = float(np.nanmedian(S)) if np.isfinite(S).any() else 0.0
    Tf = np.where(np.isfinite(T), T, fill_t).astype(np.float32)
    Sf = np.where(np.isfinite(S), S, fill_s).astype(np.float32)
    ncc = cv2.matchTemplate(Sf, Tf, cv2.TM_CCOEFF_NORMED)
    ratio, (iy, ix), peak = psr(ncc)
    found = np.array([ix + tc[0], iy + tc[1]])
    off = float(np.hypot(*(found - pred)))
    rec.update({"ncc_peak": peak, "psr": ratio, "peak_top_left": [int(ix), int(iy)],
                "found_xy_oriented": [float(found[0]), float(found[1])],
                "offset_coarse_px": off,
                "within_tolerance": bool(off <= tol), "psr_ok": bool(ratio >= S5_PSR),
                "localised": bool(off <= tol and ratio >= S5_PSR), "status": "ok"})
    return rec


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------
def mcnemar(b: int, c: int) -> dict:
    """Exact McNemar on discordant counts b (first-only) and c (second-only)."""
    from scipy.stats import binomtest
    n = b + c
    if n == 0:
        return {"b": b, "c": c, "n_discordant": 0, "p_two_sided": None, "p_one_sided_first": None,
                "note": "no discordant pairs: the test cannot run"}
    two = float(binomtest(min(b, c), n, 0.5, alternative="two-sided").pvalue)
    one = float(binomtest(b, n, 0.5, alternative="greater").pvalue)
    return {"b": b, "c": c, "n_discordant": n, "p_two_sided": two, "p_one_sided_first": one}


def concordance(full: list[bool], cropped: list[bool]) -> dict:
    full, cropped = list(map(bool, full)), list(map(bool, cropped))
    n = len(full)
    agree = sum(f == c for f, c in zip(full, cropped))
    b = sum(f and not c for f, c in zip(full, cropped))     # full-r succeeds, cropped r/2 fails
    c = sum(c_ and not f for f, c_ in zip(full, cropped))   # cropped r/2 succeeds, full r fails
    return {"n_cells": n, "n_agree": agree, "concordance": (agree / n) if n else None,
            "full_only_success": b, "cropped_only_success": c, "mcnemar": mcnemar(b, c)}


def logistic(N: np.ndarray, r: np.ndarray, y: np.ndarray) -> dict:
    """logit P = b0 + bN log2 N + br log2 r, Wald p per coefficient."""
    X = np.column_stack([np.ones(len(y)), np.log2(N.astype(float)), np.log2(r.astype(float))])
    y = np.asarray(y, float)
    try:
        import statsmodels.api as sm
        fit = sm.Logit(y, X).fit(disp=0, maxiter=200)
        beta, p = np.asarray(fit.params), np.asarray(fit.pvalues)
        method = f"statsmodels {sm.__version__} Logit"
    except Exception as exc:  # separation or absence: numpy IRLS
        beta = np.zeros(3)
        for _ in range(100):
            eta = X @ beta
            mu = 1 / (1 + np.exp(-eta))
            W = mu * (1 - mu) + 1e-9
            H = X.T @ (X * W[:, None]) + 1e-6 * np.eye(3)
            step = np.linalg.solve(H, X.T @ (y - mu))
            beta = beta + step
            if np.abs(step).max() < 1e-8:
                break
        eta = X @ beta
        mu = 1 / (1 + np.exp(-eta))
        W = mu * (1 - mu) + 1e-9
        cov = np.linalg.inv(X.T @ (X * W[:, None]) + 1e-6 * np.eye(3))
        from scipy.stats import norm
        z = beta / np.sqrt(np.diag(cov))
        p = 2 * (1 - norm.cdf(np.abs(z)))
        method = f"numpy IRLS (statsmodels failed: {type(exc).__name__}: {exc})"
    return {"method": method, "n": int(len(y)), "n_success": int(y.sum()),
            "beta0": float(beta[0]), "beta_N": float(beta[1]), "beta_r": float(beta[2]),
            "p_beta_N": float(p[1]), "p_beta_r": float(p[2])}


def pixel_floor(cells: list[dict]) -> dict:
    """N*: smallest octave bin of coarse pixel count with ≥ 50 % success."""
    bins: dict[int, list[bool]] = {}
    for c in cells:
        n = c.get("n_valid_src", 0)
        if n <= 0:
            continue
        bins.setdefault(int(np.floor(np.log2(n))), []).append(bool(c["success"]))
    table = {f"2^{k}..2^{k + 1}": {"n_cells": len(v), "success_rate": float(np.mean(v))}
             for k, v in sorted(bins.items())}
    n_star = next((2 ** k for k, v in sorted(bins.items()) if np.mean(v) >= 0.5), None)
    largest = max((2 ** (k + 1) for k in bins), default=None)
    return {"octave_bins": table, "N_star": n_star,
            "note": ("above the largest N run" if n_star is None else "smallest octave bin with >= 50 % success"),
            "largest_N_run": largest}


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------
def s0_operator_gate(windows: dict, pop_b_rows: dict, quick: bool) -> dict:
    """(i) psf = 0 equals decimate bit for bit; (ii) EXP-007's route with psf = 0
    reproduces the recorded tier-1/tier-2 counts exactly."""
    out = {"i_bit_exact": [], "ii_reproduction": []}
    ks = (2, 4, 8) if quick else (2, 4, 8, 16, 32)
    for (wname, pdsid), w in windows.items():
        if wname not in ("RD03-target", "RD04-target"):
            continue
        raw = w.raw()
        for k in ks:
            eq = bool(np.array_equal(degrade_to_gsd(raw, k, psf_fwhm_coarse_px=0.0), _e7.decimate(raw, k),
                                     equal_nan=True))
            out["i_bit_exact"].append({"window": wname, "pdsid": pdsid, "k": k, "equal": eq})
    for tname, _m, edge, counts, (t1name, _t1m, n1) in POP_B:
        s, d = edge.split(" -> ")
        for k, n_rec in list(counts.items()) + [(NATIVE_K, n1)]:
            if quick and k not in (8, 32):
                continue
            # tier 1 ran on the recorded 4096-line tiles; tier 2 on the long windows
            src_name = t1name if k == NATIVE_K else tname
            ws, wd = windows[(src_name, s)], windows[(src_name, d)]
            t0 = time.perf_counter()
            a, b = ws.native_box(k), wd.native_box(k)
            res = _e7.run_engine("b1", a, b, E7_BASE)
            rec = _e7.summarise_result(res, a.shape)
            rec.update({"target": src_name, "edge": edge, "k": k, "recorded_n_inliers": n_rec,
                        "tier": "tier1" if k == NATIVE_K else "tier2",
                        "reproduces": bool(rec["n_inliers"] == n_rec), "wall_s": time.perf_counter() - t0})
            row7 = pop_b_rows.get((edge, k))
            if row7 is not None and row7.get("transform_matrix") is not None and rec["transform_matrix"] is not None:
                rec["transform_max_abs_diff"] = float(np.abs(np.asarray(row7["transform_matrix"]) -
                                                            np.asarray(rec["transform_matrix"])).max())
            out["ii_reproduction"].append(rec)
            print(f"  [S0 ii] {src_name} {edge[4:16]}->{edge[-13:]} k={k:2d} inliers={rec['n_inliers']:5d} "
                  f"recorded={n_rec:5d} {'REPRODUCES' if rec['reproduces'] else 'DIFFERS'}", flush=True)
    out["i_met"] = all(x["equal"] for x in out["i_bit_exact"])
    out["ii_met"] = all(x["reproduces"] for x in out["ii_reproduction"]) and bool(out["ii_reproduction"])
    return out


def s0_native_gate(windows: dict, rows: dict, pop_a) -> dict:
    """(iii) r = 2 through run_real_data_07.run_edge (north_up_east_right)."""
    _rd7.ORIENT_FN = north_up_east_right
    out = []
    for wname, edge, n_rec in pop_a:
        s, d = edge.split(" -> ")
        ws, wd = windows[(wname, s)], windows[(wname, d)]
        t0 = time.perf_counter()
        rec = _rd7.run_edge(ws.ctx, wd.ctx, "b1", True)
        rec.update({"window": wname, "edge": edge, "recorded_n_inliers": n_rec,
                    "reproduces": bool(rec["n_inliers"] == n_rec), "wall_s": time.perf_counter() - t0})
        row = rows.get((wname, edge))
        if row is not None and row.get("transform_matrix_original_pixels") is not None \
                and rec.get("transform_matrix_original_pixels") is not None:
            rec["transform_max_abs_diff"] = float(np.abs(
                np.asarray(row["transform_matrix_original_pixels"]) -
                np.asarray(rec["transform_matrix_original_pixels"])).max())
        out.append(rec)
        print(f"  [S0 iii] {wname} {edge[4:16]}->{edge[-13:]} inliers={rec['n_inliers']:5d} "
              f"recorded={n_rec:5d} {'REPRODUCES' if rec['reproduces'] else 'DIFFERS'}", flush=True)
    return {"rows": out, "met": all(x["reproduces"] for x in out) and bool(out)}


def native_transform(row: dict) -> Transform:
    m = row.get("transform_matrix_original_pixels")
    if m is None:
        m = row["transform_matrix"]
    return Transform(np.asarray(m, float), "affine")


def run_cells(windows: dict, rows: dict, e7rows: dict, pop_a, pop_b, rungs_d, rungs_n, rungs_x,
              rungs_l, rungs_b4l, learned_ok: bool) -> list[dict]:
    cells: list[dict] = []
    # (population, window, edge, native count, native row, name of the window the native row was recorded on)
    pairs = [("A", w, e, n, rows.get((w, e)), w) for w, e, n in pop_a]
    pairs += [("B", t, e, t1[2], e7rows.get((e, NATIVE_K)), t1[0]) for t, _m, e, _c, t1 in pop_b]
    for pop, wname, edge, n_native, native_row, nat_name in pairs:
        s, d = edge.split(" -> ")
        ws, wd = windows[(wname, s)], windows[(wname, d)]
        nat_ws, nat_wd = windows[(nat_name, s)], windows[(nat_name, d)]
        native_ok = bool(n_native > RULE)
        t_nat = native_transform(native_row) if native_row is not None else None
        base = {"population": pop, "window": wname, "edge": edge, "pair": sorted((s, d)),
                "native_n_inliers": n_native, "native_success": native_ok,
                "delta_incidence_deg": abs(ws.ctx.incidence_published - wd.ctx.incidence_published),
                "native_pixel_m_src": ws.scaled_pixel_m, "native_pixel_m_dst": wd.scaled_pixel_m,
                "handedness_src": ws.handedness(), "handedness_dst": wd.handedness()}
        nat_w2s, nat_w2d = nat_ws.window(NATIVE_K), nat_wd.window(NATIVE_K)
        base["native_window"] = nat_name

        def add(rec: dict, arm: str, r: int, r_run: int, ks: int, kr: int, w_s: Window, w_d: Window,
                engine: str = "B1", src_img=None):
            tf = rec.pop("_tf_original", None)
            rec.update(base)
            rec.update({"arm": arm, "r": r, "r_run": r_run, "k_src": ks, "k_dst": kr, "engine": engine,
                        "coarse_gsd_m": r_run * ws.scaled_pixel_m})
            if tf is not None and t_nat is not None and rec["success"] and src_img is not None:
                pred = rung_map(t_nat, nat_w2s, nat_w2d, w_s.window(ks), w_d.window(kr))
                rec["rung_consistency"] = rung_consistency(tf, pred, src_img, r_run, ws.scaled_pixel_m)
            elif t_nat is None:
                rec["rung_consistency"] = {"status": "no native transform recorded"}
            if arm == "N" and tf is not None:
                A = np.asarray(tf.matrix)[:2, :2]
                rec["recovered_scale"] = float(np.sqrt(abs(np.linalg.det(A))))
                rec["expected_scale"] = ks / kr
            cells.append(rec)
            g = rec["geometry"].get("verdict", rec["geometry"].get("status", ""))
            rc = rec.get("rung_consistency", {})
            print(f"  [{pop} {wname:11s} {edge[4:16]}->{edge[-13:]}] {arm} r={r:3d}(run {r_run:3d}) {engine:3s} "
                  f"N={rec['n_valid_src']:8d} kp={rec['n_keypoints_src']:5d} put={rec['n_putative']:5d} "
                  f"inl={rec['n_inliers']:5d} {'SUCCESS' if rec['success'] else ('WRONG-PASS' if rec['wrong_pass'] else 'fail'):10s} "
                  f"geom={g[:12]:12s} cons={rc.get('median_coarse_px', float('nan')):.3f}px "
                  f"({rec['wall_s']:.0f}s)", flush=True)

        # arm D
        for r in rungs_d:
            a, b = ws.coarse(r), wd.coarse(r)
            if min(a.shape) < 2 or min(b.shape) < 2:
                continue
            rec = register_oriented(ws, r, a, wd, r, b)
            add(rec, "D", r, r, r, r, ws, wd, src_img=a)
            if learned_ok and r in rungs_b4l:
                rec = register_oriented(ws, r, a, wd, r, b, engine="B4L")
                add(rec, "D", r, r, r, r, ws, wd, engine="B4L", src_img=a)
        # arm N
        a2 = ws.native_box(NATIVE_FINE_K)
        for r in rungs_n:
            b = wd.coarse(r)
            rec = register_oriented(ws, NATIVE_FINE_K, a2, wd, r, b)
            add(rec, "N", r, r, NATIVE_FINE_K, r, ws, wd, src_img=a2)
        # arm X: central quarter at r/2
        cs, cd = ws.cropped_quarter(), wd.cropped_quarter()
        for r in rungs_x:
            rh = r // 2
            a, b = cs.coarse(rh), cd.coarse(rh)
            if min(a.shape) < 2 or min(b.shape) < 2:
                continue
            rec = register_oriented(cs, rh, a, cd, rh, b)
            add(rec, "X", r, rh, rh, rh, cs, cd, src_img=a)
        # self-scale control (S0 iv) on the source window
        for r in rungs_d:
            sc = self_scale_control(ws, r)
            sc.update({"population": pop, "window": wname, "edge": edge, "arm": "SELF", "r": r})
            cells.append(sc)
            print(f"  [{pop} {wname:11s} {edge[4:16]}] SELF r={r:3d} N={sc['n_coarse_px']:8d} "
                  f"inl={sc.get('n_inliers', 0):5d} shift_err={sc.get('shift_error_coarse_px', float('nan')):.4f}px",
                  flush=True)
        ws.ctx.release(); wd.ctx.release()
        ws._raw = None; wd._raw = None
    # arm L on population B
    for tname, _m, edge, _c, (t1name, _t1m, _n1) in pop_b:
        s, d = edge.split(" -> ")
        ws, wd = windows[(tname, s)], windows[(tname, d)]
        rdw = t1name
        tile = windows.get((rdw, s))
        if tile is None:
            cells.append({"population": "B", "window": tname, "edge": edge, "arm": "L",
                          "status": f"no recorded 4096-line tile of {s} in {rdw}"})
            continue
        try:
            tmpl = ws.sub(tile.line0, tile.sample0, tile.n_lines, tile.n_samples)
        except ValueError as exc:
            cells.append({"population": "B", "window": tname, "edge": edge, "arm": "L", "status": str(exc)})
            continue
        for r in rungs_l:
            rec = localise(tmpl, wd, r)
            rec.update({"population": "B", "window": tname, "edge": edge, "arm": "L",
                        "template_tile": f"l{tile.line0}s{tile.sample0}"})
            cells.append(rec)
            print(f"  [B {tname} L] r={r:3d} tmpl={rec['template_shape']} search={rec['search_shape']} "
                  f"off={rec.get('offset_coarse_px', float('nan')):.2f}px tol={rec.get('tolerance_coarse_px', float('nan')):.2f} "
                  f"psr={rec.get('psr', float('nan')):.2f} {'LOCALISED' if rec.get('localised') else rec.get('status', 'no')}",
                  flush=True)
        ws.ctx.release(); wd.ctx.release(); ws._raw = None; wd._raw = None
    return cells


def evaluate(cells: list[dict], s0: dict, rungs_d) -> dict:
    A11 = [c for c in cells if c.get("population") == "A" and c.get("native_success")]
    A_fail = [c for c in cells if c.get("population") == "A" and not c.get("native_success") and c.get("arm") != "SELF"]
    B = [c for c in cells if c.get("population") == "B"]
    d11 = [c for c in A11 if c["arm"] == "D" and c["engine"] == "B1"]
    n_pairs = len({c["edge"] for c in d11}) or 11
    # S1
    per_rung = {}
    for r in rungs_d:
        cs = [c for c in d11 if c["r"] == r]
        per_rung[str(r)] = {"n_pairs_run": len(cs), "n_success": sum(c["success"] for c in cs),
                            "n_wrong_pass": sum(c["wrong_pass"] for c in cs),
                            "n_pass_rule_only": sum(c["pass"] for c in cs)}
    ok_r = [r for r in rungs_d if per_rung[str(r)]["n_success"] >= S1_MIN_PAIRS]
    envelope = max(ok_r) if ok_r else None
    s1 = {"met": bool(all(per_rung[str(r)]["n_success"] >= S1_MIN_PAIRS for r in rungs_d)),
          "envelope_r": envelope, "per_rung": per_rung, "n_pairs": n_pairs,
          "clause": f">= {S1_MIN_PAIRS} of {n_pairs} native-success pairs succeed at every rung incl. 320",
          "population_B": [{"edge": c["edge"], "r": c["r"], "success": c["success"], "n_inliers": c["n_inliers"]}
                           for c in B if c.get("arm") == "D" and c.get("engine") == "B1"]}
    # S2
    full = {(c["edge"], c["r"]): c for c in d11}
    crop = {(c["edge"], c["r"]): c for c in A11 if c["arm"] == "X"}
    keys = sorted(set(full) & set(crop))
    conc = concordance([full[k]["success"] for k in keys], [crop[k]["success"] for k in keys])
    pooled = d11 + [c for c in A11 if c["arm"] == "X"]
    pooled = [c for c in pooled if c.get("n_valid_src", 0) > 0]
    lg = logistic(np.array([c["n_valid_src"] for c in pooled]), np.array([c["r_run"] for c in pooled]),
                  np.array([c["success"] for c in pooled])) if len(pooled) >= 6 else {"method": "too few cells"}
    starv = bool(conc.get("concordance") is not None and conc["concordance"] >= S2_CONCORDANCE
                 and lg.get("beta_N", 0) > 0 and lg.get("p_beta_N", 1) < S2_ALPHA
                 and not (lg.get("beta_r", 0) < 0 and lg.get("p_beta_r", 1) < S2_ALPHA))
    desc = bool(conc.get("concordance") is not None and conc["concordance"] < S2_CONCORDANCE
                and lg.get("beta_r", 0) < 0 and lg.get("p_beta_r", 1) < S2_ALPHA)
    s2 = {"verdict": "STARVATION" if starv else ("DESCRIPTOR" if desc else "UNRESOLVED"),
          "concordance": conc, "logistic": lg,
          "discordant_cells": [{"edge": k[0], "r": k[1], "full_success": full[k]["success"],
                                "cropped_success": crop[k]["success"],
                                "N_full": full[k]["n_valid_src"], "N_cropped": crop[k]["n_valid_src"]}
                               for k in keys if full[k]["success"] != crop[k]["success"]],
          "pixel_floor_arm_D": pixel_floor(d11),
          "pixel_floor_arm_D_plus_X": pixel_floor(pooled)}
    # S3
    nn = {(c["edge"], c["r"]): c for c in A11 if c["arm"] == "N"}
    s3_r, b_tot, c_tot, ge = {}, 0, 0, True
    for r in ARM_N_RUNGS:
        ks = [e for (e, rr) in nn if rr == r and (e, r) in full]
        dsucc = sum(full[(e, r)]["success"] for e in ks)
        nsucc = sum(nn[(e, r)]["success"] for e in ks)
        b = sum(full[(e, r)]["success"] and not nn[(e, r)]["success"] for e in ks)
        c = sum(nn[(e, r)]["success"] and not full[(e, r)]["success"] for e in ks)
        b_tot += b; c_tot += c
        ge = ge and dsucc >= nsucc
        s3_r[str(r)] = {"n": len(ks), "D_success": dsucc, "N_success": nsucc, "D_only": b, "N_only": c,
                        "N_failure_kinds": {"rule": sum((not nn[(e, r)]["pass"]) for e in ks),
                                            "wrong_pass": sum(nn[(e, r)]["wrong_pass"] for e in ks)},
                        "N_recovered_scale": [nn[(e, r)].get("recovered_scale") for e in ks],
                        "N_expected_scale": [nn[(e, r)].get("expected_scale") for e in ks]}
    mc = mcnemar(b_tot, c_tot)
    s3 = {"met": bool(ge and mc.get("p_one_sided_first") is not None and mc["p_one_sided_first"] < S3_ALPHA),
          "D_ge_N_every_rung": ge, "pooled_mcnemar": mc, "per_rung": s3_r,
          "vacuity_note": ("both arms succeed on every cell at some rung; the rung carries no contrast"
                           if any(v["D_only"] == 0 and v["N_only"] == 0 and v["n"] > 0 for v in s3_r.values()) else None)}
    # S4
    succ = [c for c in d11 if c["success"]]
    checked = [c for c in succ if c.get("rung_consistency", {}).get("status") == "ok"]
    cannot = [c for c in succ if c.get("rung_consistency", {}).get("status") != "ok"]
    within = [c for c in checked if c["rung_consistency"]["within_1px"]
              and not c["geometry"].get("verdict", "").startswith("INCONSISTENT")]
    per_r = {}
    for r in rungs_d:
        cs = [c["rung_consistency"] for c in checked if c["r"] == r]
        if cs:
            per_r[str(r)] = {"n": len(cs),
                             "median_coarse_px": float(np.median([x["median_coarse_px"] for x in cs])),
                             "p90_coarse_px": float(np.median([x["p90_coarse_px"] for x in cs])),
                             "median_m": float(np.median([x["median_m"] for x in cs])),
                             "p90_m": float(np.median([x["p90_m"] for x in cs]))}
    frac = (len(within) / len(checked)) if checked else None
    s4 = {"met": bool(frac is not None and frac >= S4_FRACTION), "fraction_within": frac,
          "n_successes": len(succ), "n_checked": len(checked), "n_cannot_check": len(cannot),
          "per_rung": per_r, "label": "agreement with the native-rung solution; NOT accuracy",
          "vacuity_note": (f"only {len({c['r'] for c in succ})} rung(s) succeed" if len({c["r"] for c in succ}) <= 2 else None)}
    # S5
    L = [c for c in cells if c.get("arm") == "L"]
    per_rL = {}
    for r in ARM_L_RUNGS:
        cs = [c for c in L if c.get("r") == r]
        per_rL[str(r)] = {"n": len(cs), "n_localised": sum(bool(c.get("localised")) for c in cs),
                          "offsets": [c.get("offset_coarse_px") for c in cs], "psr": [c.get("psr") for c in cs]}
    both = [r for r in ARM_L_RUNGS if per_rL[str(r)]["n"] >= 2 and per_rL[str(r)]["n_localised"] == per_rL[str(r)]["n"]]
    s5 = {"met": bool(320 in both), "localisation_envelope_r": max(both) if both else None, "per_rung": per_rL}
    # secondary
    b4l = [c for c in A11 if c["arm"] == "D" and c.get("engine") == "B4L"]
    b4l_r = {str(r): {"n": len([c for c in b4l if c["r"] == r]),
                      "n_success": sum(c["success"] for c in b4l if c["r"] == r),
                      "n_wrong_pass": sum(c["wrong_pass"] for c in b4l if c["r"] == r)} for r in B4L_RUNGS}
    b4l_ok = [r for r in B4L_RUNGS if b4l_r[str(r)]["n"] and b4l_r[str(r)]["n_success"] >= S1_MIN_PAIRS]
    selfc = [c for c in cells if c.get("arm") == "SELF"]
    s0_iv = {"n": len(selfc),
             "shift_clause_failures": [{"edge": c["edge"], "r": c["r"], "err": c.get("shift_error_coarse_px")}
                                       for c in selfc if c.get("clause_shift") is False],
             "inlier_clause_failures": [{"edge": c["edge"], "r": c["r"], "n_inliers": c.get("n_inliers"),
                                         "N": c.get("n_coarse_px")} for c in selfc if c.get("clause_inliers") is False],
             "detector_floor_per_rung": {str(r): {"N": [c["n_coarse_px"] for c in selfc if c["r"] == r],
                                                  "n_inliers": [c.get("n_inliers") for c in selfc if c["r"] == r]}
                                         for r in rungs_d}}
    s0_iv["met_shift"] = not s0_iv["shift_clause_failures"]
    s0_iv["inlier_clause_note"] = ("a failing inlier clause is a floor measurement of the detector on identical "
                                   "texture, reported, and does not exclude the cell (Part 1 S0(iv))")
    s0["iv_self_scale"] = s0_iv
    s0["v_handedness"] = sorted({(c["edge"], round(c["handedness_src"], 6), round(c["handedness_dst"], 6))
                                 for c in cells if "handedness_src" in c})
    s0["vi_counts_recorded"] = all(("n_valid_src" in c and "n_keypoints_src" in c and "n_putative" in c)
                                   for c in cells if c.get("arm") in ("D", "N", "X"))
    s0["met"] = bool(s0["operator_gate"]["i_met"] and s0["operator_gate"]["ii_met"]
                     and s0["native_gate"]["met"] and s0_iv["met_shift"] and s0["vi_counts_recorded"])
    occ = {}
    for r in rungs_d:
        cs = [c.get("coverage_occupancy") for c in d11 if c["r"] == r and c.get("coverage_occupancy") is not None]
        occ[str(r)] = float(np.median(cs)) if cs else None
    return {"S0": s0, "S1": s1, "S2": s2, "S3": s3, "S4": s4, "S5": s5,
            "secondary": {"B4L_arm_D": {"per_rung": b4l_r, "envelope_r": max(b4l_ok) if b4l_ok else None,
                                        "n_wrong_pass": sum(c["wrong_pass"] for c in b4l)},
                          "native_failure_stratum": [{"edge": c["edge"], "arm": c["arm"], "r": c["r"],
                                                      "n_inliers": c["n_inliers"], "success": c["success"]}
                                                     for c in A_fail if c.get("arm") in ("D", "N", "X")],
                          "grid_occupancy_median_per_rung_arm_D": occ,
                          "starvation_curve": [{"edge": c["edge"], "r": c["r"], "N": c["n_valid_src"],
                                                "kp_src": c["n_keypoints_src"], "kp_dst": c["n_keypoints_dst"],
                                                "putative": c["n_putative"], "inliers": c["n_inliers"]}
                                               for c in d11]}}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=None)
    ap.add_argument("--quick", action="store_true", help="2 pairs, r in {8, 64}; tests and smoke only")
    args = ap.parse_args()
    out_path = Path(args.out) if args.out else OUT / "exp016_results.json"
    if out_path.exists():
        raise SystemExit(f"{out_path} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()
    quick = args.quick
    pop_a = [POP_A[4], POP_A[9]] if quick else POP_A
    pop_b = [] if quick else POP_B
    rungs_d = (8, 64) if quick else ARM_D_RUNGS
    rungs_n = (8,) if quick else ARM_N_RUNGS
    rungs_x = (64,) if quick else ARM_X_RUNGS
    rungs_l = () if quick else ARM_L_RUNGS
    rungs_b4l = () if quick else B4L_RUNGS
    learned_ok = learned_available()

    products = _rd7.load_products()
    windows = load_contexts(products)
    rows = recorded_rows()
    e7rows = exp007_rows()
    print(f"EXP-016 | windows {len(windows)} | recorded NU rows {len(rows)} | B4L {'yes' if learned_ok else 'no'}\n")
    print("== S0 (i)/(ii): operator gate ==", flush=True)
    s0 = {"operator_gate": s0_operator_gate(windows, e7rows, quick) if not quick else
          {"i_met": True, "ii_met": True, "note": "quick mode: skipped"}}
    print("\n== S0 (iii): native gate ==", flush=True)
    s0["native_gate"] = s0_native_gate(windows, rows, pop_a)
    for w in windows.values():
        w.ctx.release(); w._raw = None
    print("\n== ladder ==", flush=True)
    cells = run_cells(windows, rows, e7rows, pop_a, pop_b, rungs_d, rungs_n, rungs_x, rungs_l, rungs_b4l,
                      learned_ok)
    verdict = evaluate(cells, s0, rungs_d)
    doc = {
        "stage": STAGE,
        "preregistration": "docs/stages/EXP-016_scale_ladder.md Part 1 (commit f7d94f5)",
        "quick_mode": quick,
        "ladder": list(LADDER), "arm_D_rungs": list(rungs_d), "arm_N_rungs": list(rungs_n),
        "arm_X_rungs": list(rungs_x), "arm_L_rungs": list(rungs_l), "b4l_rungs": list(rungs_b4l),
        "operator": {"function": "siim.preprocessing.degrade.degrade_to_gsd",
                     "psf_fwhm_coarse_px": PSF_FWHM_COARSE_PX, "then": "run_exp007.stretch, north_up_east_right"},
        "pipeline": {"function": "siim.pipeline.register_pair", "engine": "B1", **BASE,
                     "failure_rule": f"n_inliers <= {RULE} (D-023)",
                     "success": "pass and geometry not INCONSISTENT (run_exp007.geometry_check)"},
        "population_A": [{"window": w, "edge": e, "native_n_inliers": n} for w, e, n in pop_a],
        "population_B": [{"target": t, "edge": e, "recorded_tier2_counts": c,
                          "tier1": {"target": t1[0], "manifest": t1[1], "k2_count": t1[2]}}
                         for t, _m, e, c, t1 in pop_b],
        "runner_notes": [
            "EXP-007's tier-1 counts (5365, 1656) were recorded on the 4096-line tiles of "
            "real_triplet_geo_manifest / real_quad_d_geo_manifest at k = 2, not on the long windows; "
            "they are reproduced there, and the native-rung transform for population B's rung "
            "consistency is the tier-1 transform mapped through the frame (TileWindow) to the long window.",
            f"Coverage statistics in this runner's own records are computed on at most {COVERAGE_POINT_CAP} "
            "inliers (seeded subsample) because siim.evaluation.coverage builds an exact N x N distance "
            "matrix; a cell whose verdict stage raised MemoryError for the same reason is recorded from the "
            "estimate stage with pipeline_note set. The self-scale control uses the estimate stage only.",
        ],
        "criteria": verdict,
        "n_cells": len(cells), "cells": cells,
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "opencv": cv2.__version__, "platform": platform.platform(),
                        "learned_engine": learned_ok},
        "total_runtime_s": time.perf_counter() - t_start,
        "claims_not_supported": [
            "Not a cross-sensor result: the coarse sensor is a NAC frame through a Gaussian PSF.",
            "Not accuracy: rung consistency is agreement with the native-rung solution; the geometry "
            "check corroborates at its floor.",
            "Not a 320:1 result for OHRC <-> IIRS: the largest window on disk gives 38 x 15 px at 320:1.",
            "One region, one terrain class, one engine in every criterion, Delta-inc <= 15 deg by construction.",
        ],
    }
    out_path.write_text(json.dumps(doc, indent=2, default=float), encoding="utf-8")
    c = verdict
    print(f"\nS0 {'MET' if c['S0']['met'] else 'NOT MET'} | S1 {'MET' if c['S1']['met'] else 'NOT MET'} "
          f"(envelope r={c['S1']['envelope_r']}) | S2 {c['S2']['verdict']} "
          f"(N*={c['S2']['pixel_floor_arm_D']['N_star']}) | S3 {'MET' if c['S3']['met'] else 'NOT MET'} | "
          f"S4 {'MET' if c['S4']['met'] else 'NOT MET'} ({c['S4']['fraction_within']}) | "
          f"S5 {'MET' if c['S5']['met'] else 'NOT MET'} (loc r={c['S5']['localisation_envelope_r']})")
    print(f"wrote {out_path} in {doc['total_runtime_s']:.0f}s")


if __name__ == "__main__":
    main()
