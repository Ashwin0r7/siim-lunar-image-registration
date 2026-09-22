"""EXP-020 — multi-modality measured, run exactly as Part 1 froze it
(docs/stages/EXP-020_multimodality.md, commit 4e043a4).

Nine Kaguya MI reflectance bands (414-1548 nm, 14.8 m, photometrically
normalised to i = 30 deg) and a Diviner bolometric-temperature map (236.9 m) are
registered against panchromatic references over the ground every real result in
this project used:

    P   the band MEAN of the nine bands   -> TC pan  (the comparator S2 reads against)
    B   each band                         -> TC pan  (S1, S2)
    C   each band                         -> Chandrayaan-2 TMC-2 ortho block (S3)
    N   each band                         -> LRO NAC frames EXP-019 placed (S4)
    T   Diviner tbol                      -> TC pan at 28:1 (S5)
    0   every band and the pan            -> the TC NULL block, 25 km away (S6)

Every product here is map-projected, so the true correspondence between any two
is analytic from their labels and no matcher touches it: the error statistic is
``|| T_hat(x) - T_map(x) ||`` on an 8 px grid, in metres and in reference
pixels. Its limit -- exact only to the extent the two products are
georeferenced relative to each other -- is stated in Part 1 section 2.1 and
repeated in every reported number's units.

    python scripts/run_exp020.py
    python scripts/run_exp020.py --quick --out <scratch>
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
from siim.geometry import Transform, estimate, pixel_grid  # noqa: E402
from siim.ingest.footprint import TileWindow  # noqa: E402
from siim.ingest.geotiff import decode_window, place  # noqa: E402
from siim.ingest.mapgrid import MapBlock, load_map_block  # noqa: E402
from siim.ingest.orientation import north_up_east_right  # noqa: E402
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
_e19 = _load("_exp019", "scripts/run_exp019.py")

STAGE = "EXP-020"
DATA = ROOT / "data"
OUT = ROOT / "experiments" / STAGE
BASE = {"model": "affine", "ransac_threshold_px": 3.0, "seed": 0}
RULE = _e7.N_INLIERS_FAILURE_RULE
ENGINE = "B1"
SECOND_ENGINE = "B4L"
PSF = 1.0

MI_MANIFEST = "exp020_kaguya_mi_block.json"
DIV_MANIFEST = "exp020_diviner_tbol_day_block.json"   # Amendment A1
TC_REF_MANIFEST = "exp019_tc_ortho_ref_block.json"
TC_NULL_MANIFEST = "exp019_tc_ortho_null_block.json"
TC_GSD_M = _e19.REF_GSD_M                      # 8.42315289562
MI_GSD_M = 14.806323445
DIV_GSD_M = 236.901175

# --- frozen constants, Part 1 section 4 -----------------------------------
GRID_STEP = 8
S0_BAND_COREG_TOL_PX = 0.05
S0_MAP_ROUNDTRIP_TOL_PX = 1e-6
S1_MIN_BANDS = 7
S1_BOUND_M = TC_GSD_M                          # 1.0 reference px
S2_MAX_RATIO = 2.0
S3_BOUND_M = 60.0
S4_MIN_BANDS = 3
S4_MIN_FRAMES = 2
S5_BOUND_M = 2.0 * DIV_GSD_M                   # 2.0 thermal px
S6_N_CELLS = 10
MIN_VALID_FRACTION = 0.40
S0_COREG_BANDS = (1, 4)                        # band 2 and band 5, 0-based
S0_REPRO_EDGE = ("RD03", "nac.m1271742202lc -> nac.m1182331886lc")


# ---------------------------------------------------------------------------
# grids
# ---------------------------------------------------------------------------
def mi_block() -> tuple[np.ndarray, MapBlock, dict]:
    man = json.loads((DATA / "manifests" / MI_MANIFEST).read_text(encoding="utf-8"))
    arr = np.load(ROOT / man["block_npy"].replace("\\", "/"))
    g = man["grid"]
    grid = MapBlock(data=arr[0].astype(np.float32), row0=int(man["row0"]), col0=int(man["col0"]),
                    ppd_lat=float(g["ppd_lat"]), ppd_lon=float(g["ppd_lon"]),
                    lat_top_deg=float(g["lat_top_deg"]), lon_left_deg=float(g["lon_left_deg"]),
                    name=man["product"], provenance={"manifest": MI_MANIFEST})
    return arr, grid, man


def map_between(src: MapBlock, dst: MapBlock, shape: tuple[int, int]) -> tuple[Transform, float]:
    """Analytic source-block px -> destination-block px, from the two labels."""
    h, w = shape
    gx, gy = np.meshgrid(np.linspace(0, w - 1, 9), np.linspace(0, h - 1, 9))
    pts = np.column_stack([gx.ravel(), gy.ravel()]).astype(float)
    lon = src.lon_of_sample(pts[:, 0] + src.col0)
    lat = src.lat_of_line(pts[:, 1] + src.row0)
    xy = dst.block_xy_of_lonlat(lon, lat)
    res = estimate(pts, xy, "affine")
    if not res.ok:
        raise RuntimeError("analytic map fit failed")
    return res.transform, float(np.abs(res.transform.apply(pts) - xy).max())


def scaled(block: MapBlock, k: int) -> MapBlock:
    """The same map grid after a k x k block degradation (contract C4 offset)."""
    return MapBlock(data=block.data, row0=block.row0, col0=block.col0,
                    ppd_lat=block.ppd_lat / k, ppd_lon=block.ppd_lon / k,
                    lat_top_deg=block.lat_top_deg, lon_left_deg=block.lon_left_deg,
                    name=f"{block.name}/k{k}", provenance=block.provenance)


def _degraded_map_block(block: MapBlock, k: int) -> MapBlock:
    """Grid of ``degrade_to_gsd(block.data, k)`` in BLOCK pixel coordinates.

    A degraded pixel j covers original pixels [jk, jk+k), whose centres average
    to jk + (k-1)/2, so the degraded grid's own (lon, lat) map has k times the
    spacing and its origin shifted by (k-1)/2 original pixels.
    """
    ppd_lat, ppd_lon = block.ppd_lat / k, block.ppd_lon / k
    lat_top = block.lat_top_deg - (block.row0 + (k - 1) / 2.0 - 0.5 * k + 0.5) / block.ppd_lat
    lon_left = block.lon_left_deg + (block.col0 + (k - 1) / 2.0 - 0.5 * k + 0.5) / block.ppd_lon
    return MapBlock(data=block.data, row0=0, col0=0, ppd_lat=ppd_lat, ppd_lon=ppd_lon,
                    lat_top_deg=lat_top, lon_left_deg=lon_left,
                    name=f"{block.name}/deg{k}", provenance=block.provenance)


# ---------------------------------------------------------------------------
# one cell
# ---------------------------------------------------------------------------
def run_cell(name: str, arm: str, src_img: np.ndarray, dst_img: np.ndarray,
             t_map: Transform | None, dst_gsd_m: float, engine: str = ENGINE,
             extra: dict | None = None) -> dict:
    t0 = time.perf_counter()
    rec: dict = {"cell": name, "arm": arm, "engine": engine,
                 "src_shape": list(src_img.shape), "dst_shape": list(dst_img.shape),
                 "src_valid_fraction": float(np.isfinite(src_img).mean()),
                 "dst_valid_fraction": float(np.isfinite(dst_img).mean())}
    if extra:
        rec.update(extra)
    res = register_pair(_e7.stretch(src_img), _e7.stretch(dst_img), engine=engine,
                        model=BASE["model"], ransac_threshold=BASE["ransac_threshold_px"],
                        seed=BASE["seed"])
    mask = np.asarray(res.inlier_mask, bool)
    n_in = int(mask.sum())
    rec.update({
        "n_keypoints_src": int(len(res.baseline.src_features)),
        "n_keypoints_dst": int(len(res.baseline.dst_features)),
        "n_putative": int(res.src_points.shape[0]), "n_inliers": n_in,
        "n_refined": int(np.asarray(res.refined_mask, bool).sum()),
        "pass": bool(n_in > RULE),
        "fit_rmse_px": (float(res.baseline.ransac.inlier_rmse)
                        if res.baseline.ransac is not None else None),
        "fit_rmse_is_not_accuracy": True,
        "model_selected_by": res.model_selected_by,
        "verdict": {"status": res.verdict.status, "confidence": res.verdict.confidence},
        "wall_s": round(time.perf_counter() - t0, 2),
    })
    if n_in >= 3:
        cov = coverage_metrics(res.src_points[mask], src_img.shape)
        rec["coverage_occupancy"] = float(cov.grid_occupancy)
        rec["coverage_max_uncovered_disc_ratio"] = float(cov.max_uncovered_disc_ratio)
    if res.transform is not None:
        rec["transform_matrix"] = np.asarray(res.transform.matrix).tolist()
        lin = np.asarray(res.transform.matrix)[:2, :2]
        rec["recovered_scale"] = float(np.sqrt(abs(np.linalg.det(lin))))
        if t_map is not None:
            grid = pixel_grid(src_img.shape, step=GRID_STEP)
            err = np.linalg.norm(res.transform.apply(grid) - t_map.apply(grid), axis=1)
            rec.update({
                "err_median_dst_px": float(np.median(err)),
                "err_p99_dst_px": float(np.percentile(err, 99)),
                "err_max_dst_px": float(err.max()),
                "err_median_m": float(np.median(err) * dst_gsd_m),
                "err_p99_m": float(np.percentile(err, 99) * dst_gsd_m),
                "err_median_ref_px": float(np.median(err) * dst_gsd_m / TC_GSD_M),
                "n_grid": int(len(grid)),
            })
            lin_map = np.asarray(t_map.matrix)[:2, :2]
            rec["predicted_scale"] = float(np.sqrt(abs(np.linalg.det(lin_map))))
    return rec


def contrast(img: np.ndarray) -> float:
    v = img[np.isfinite(img)]
    if v.size < 16 or float(np.mean(v)) == 0.0:
        return float("nan")
    return float(np.std(v) / np.mean(v))


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=None)
    ap.add_argument("--quick", action="store_true", help="3 bands, no B4L, no arm N; smoke only")
    args = ap.parse_args()
    out_path = Path(args.out) if args.out else OUT / "exp020_results.json"
    if out_path.exists():
        raise SystemExit(f"{out_path} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()

    mi, mi_grid, mi_man = mi_block()
    tc_ref = load_map_block(TC_REF_MANIFEST)
    tc_null = load_map_block(TC_NULL_MANIFEST)
    div = load_map_block(DIV_MANIFEST)
    div_man = json.loads((DATA / "manifests" / DIV_MANIFEST).read_text(encoding="utf-8"))
    bands_nm = mi_man["bands_nm"]
    n_bands = mi.shape[0]
    band_idx = [0, 1, 8] if args.quick else list(range(n_bands))
    print(f"{STAGE} | MI {mi.shape} | TC ref {tc_ref.data.shape} | null {tc_null.data.shape} "
          f"| Diviner {div.data.shape}", flush=True)

    # ---------------- S0 -------------------------------------------------
    print("\n== S0 gates ==", flush=True)
    s0: dict = {}
    s0["grid_gate_mi"] = _e19.s0_grid_gate.__wrapped__(mi_grid, MI_MANIFEST) \
        if hasattr(_e19.s0_grid_gate, "__wrapped__") else mi_grid_gate(mi_grid, mi_man)
    s0["grid_gate_diviner"] = diviner_grid_gate(div, div_man)
    print(f"  grid gates: MI {s0['grid_gate_mi']['met']}, Diviner {s0['grid_gate_diviner']['met']}",
          flush=True)

    a, b = S0_COREG_BANDS
    co = run_cell(f"coreg/band{a + 1}_vs_band{b + 1}", "S0", mi[a], mi[b],
                  Transform(np.eye(3), "affine"), MI_GSD_M)
    s0["band_coregistration"] = {
        "met": bool(co.get("pass") and co.get("err_median_dst_px", 9e9) < S0_BAND_COREG_TOL_PX),
        "bands": [a + 1, b + 1], "wavelengths_nm": [bands_nm[a], bands_nm[b]],
        "n_inliers": co.get("n_inliers"), "err_median_px": co.get("err_median_dst_px"),
        "err_max_px": co.get("err_max_dst_px"), "tolerance_px": S0_BAND_COREG_TOL_PX}
    print(f"  band co-registration: {co.get('n_inliers')} inliers, "
          f"median {co.get('err_median_dst_px')} px -> {s0['band_coregistration']['met']}",
          flush=True)

    if not args.quick:
        window, edge = S0_REPRO_EDGE
        rows = _e19.recorded_rows()
        rec = rows[(window, edge)]
        man = json.loads((DATA / "manifests" / _rd7.WINDOWS[window]).read_text(encoding="utf-8"))
        tiles = {t["pdsid"]: t for t in man["tiles"]}
        target = tuple(man["target_ground_point_lon_lat"])
        products = _rd7.load_products()
        s_name, d_name = edge.split(" -> ")
        fs = _e7.FrameContext(s_name, tiles[s_name], products, target)
        fr = _e7.FrameContext(d_name, tiles[d_name], products, target)
        got = _rd7.run_edge(fs, fr, "b1", True)
        fs.release(); fr.release()
        s0["reproduction"] = {"met": bool(got["n_inliers"] == rec["n_inliers"]),
                              "edge": edge, "recorded": rec["n_inliers"], "rerun": got["n_inliers"]}
        print(f"  reproduction: {got['n_inliers']} vs recorded {rec['n_inliers']}", flush=True)
    else:
        s0["reproduction"] = {"met": True, "note": "quick"}

    # analytic-map round trip (S0 v)
    t_fwd, r_fwd = map_between(mi_grid, tc_ref, mi[0].shape)
    t_back, r_back = map_between(tc_ref, mi_grid, tc_ref.data.shape)
    g = pixel_grid(mi[0].shape, step=64)
    rt = float(np.abs(t_back.apply(t_fwd.apply(g)) - g).max())
    s0["analytic_map"] = {"met": bool(rt < S0_MAP_ROUNDTRIP_TOL_PX),
                          "roundtrip_max_px": rt, "affine_residual_px": [r_fwd, r_back]}
    print(f"  analytic map round trip {rt:.2e} px (affine residuals {r_fwd:.2e}, {r_back:.2e})",
          flush=True)
    s0["met"] = bool(all(s0[k]["met"] for k in
                         ("grid_gate_mi", "grid_gate_diviner", "band_coregistration",
                          "reproduction", "analytic_map")))
    if not s0["band_coregistration"]["met"]:
        print("S0(ii) FAILED — the stage stops here, as Part 1 section 6 requires", flush=True)

    # ---------------- arms P and B: bands against TC pan ------------------
    print("\n== arms P and B: MI against the TC pan reference ==", flush=True)
    k_tc = int(round(MI_GSD_M / TC_GSD_M))                      # 2
    tc_deg = degrade_to_gsd(tc_ref.data, k_tc, psf_fwhm_coarse_px=PSF)
    tc_deg_grid = _degraded_map_block(tc_ref, k_tc)
    tc_deg_gsd = TC_GSD_M * k_tc
    t_map_tc, resid_tc = map_between(mi_grid, tc_deg_grid, mi[0].shape)
    cells: list[dict] = []
    pan = np.nanmean(mi, axis=0)
    sources = [("P/pan", pan, None)] + [(f"B/band{i + 1}_{bands_nm[i]:.0f}nm", mi[i], bands_nm[i])
                                        for i in band_idx]
    for name, img, nm in sources:
        valid = float(np.isfinite(img).mean())
        extra = {"wavelength_nm": nm, "contrast": contrast(img), "valid_fraction": valid,
                 "gsd_ratio": MI_GSD_M / tc_deg_gsd}
        if valid < MIN_VALID_FRACTION:
            cells.append({"cell": name, "arm": "B" if nm else "P", "excluded":
                          f"valid fraction {valid:.3f} < {MIN_VALID_FRACTION}", **extra})
            continue
        rec = run_cell(name, "B" if nm else "P", img, tc_deg, t_map_tc, tc_deg_gsd, extra=extra)
        cells.append(rec)
        print(f"  [{rec['arm']}] {name:28s} inl={rec.get('n_inliers', 0):5d} "
              f"{'PASS' if rec.get('pass') else 'fail'} err={rec.get('err_median_m', float('nan')):7.2f} m "
              f"contrast={extra['contrast']:.3f} ({rec.get('wall_s', 0):.0f}s)", flush=True)

    # ---------------- arm C: Chandrayaan-2 --------------------------------
    print("\n== arm C: MI against the Chandrayaan-2 TMC-2 ortho ==", flush=True)
    c_cells = []
    prods = _rd9.tmc_products()
    tif = ROOT / prods["TMC-2:ortho"]["data_file"].replace("\\", "/")
    x0, y0, x1, y1 = _e19.TMC2_BLOCK
    tmc_blk = place(tif, row0=y0, row1=y1, col0=x0, col1=x1, name="tmc2-exp020")
    tmc_raw = decode_window(tif, y0, y1, x0, x1).astype(np.float64)
    tmc_raw = np.where(tmc_raw > 0, tmc_raw, np.nan)
    tmc_gsd = float(np.mean(tmc_blk.metres_per_pixel))
    k_tmc = max(1, int(round(MI_GSD_M / tmc_gsd)))
    tmc_deg = degrade_to_gsd(tmc_raw, k_tmc, psf_fwhm_coarse_px=PSF)
    tmc_deg_gsd = tmc_gsd * k_tmc
    # analytic map: MI px -> TMC-2 degraded px, through both products' own geometry
    hm, wm = mi[0].shape
    gx, gy = np.meshgrid(np.linspace(0, wm - 1, 9), np.linspace(0, hm - 1, 9))
    pts = np.column_stack([gx.ravel(), gy.ravel()]).astype(float)
    lon = mi_grid.lon_of_sample(pts[:, 0] + mi_grid.col0)
    lat = mi_grid.lat_of_line(pts[:, 1] + mi_grid.row0)
    xy = tmc_blk.block_xy_of_lonlat(lon, lat)
    xy_deg = (xy - (k_tmc - 1) / 2.0) / k_tmc
    res_c = estimate(pts, xy_deg, "affine")
    t_map_c = res_c.transform if res_c.ok else None
    for name, img, nm in sources:
        if nm is None:
            continue
        rec = run_cell(name.replace("B/", "C/"), "C", img, tmc_deg, t_map_c, tmc_deg_gsd,
                       extra={"wavelength_nm": nm, "tmc2_block": _e19.TMC2_BLOCK,
                              "tmc2_native_gsd_m": tmc_gsd, "k_tmc": k_tmc,
                              "acknowledgement": "Chandrayaan-2 data courtesy ISRO/ISSDC "
                                                 "(PRADAN); (c) reserved ISRO"})
        c_cells.append(rec)
        print(f"  [C] {name:28s} inl={rec.get('n_inliers', 0):5d} "
              f"{'PASS' if rec.get('pass') else 'fail'} err={rec.get('err_median_m', float('nan')):8.2f} m",
              flush=True)

    # ---------------- arm N: LRO NAC --------------------------------------
    n_cells = []
    if not args.quick:
        print("\n== arm N: MI against the NAC frames EXP-019 placed ==", flush=True)
        e19 = json.loads((ROOT / "experiments" / "EXP-019" /
                          "exp019_results.json").read_text(encoding="utf-8"))
        passes = [(k, c) for k, c in e19["cells"].items()
                  if c.get("arm") == "R" and c.get("kind") == "NAC" and c.get("pass")
                  and c.get("measured_to_block_matrix")]
        passes.sort(key=lambda kc: -kc[1]["n_inliers"])
        products = _rd7.load_products()
        for key, cell in passes[:4]:
            window, pdsid = key.split("/")
            man = json.loads((DATA / "manifests" /
                              _rd7.WINDOWS[window]).read_text(encoding="utf-8"))
            tile = {t["pdsid"]: t for t in man["tiles"]}[pdsid]
            ctx = _e7.FrameContext(pdsid, tile, products,
                                   tuple(man["target_ground_point_lon_lat"]))
            k_nac = _e19.K_FRAME[pdsid]
            img = _e7.stretch(degrade_to_gsd(ctx.raw(), k_nac, psf_fwhm_coarse_px=PSF))
            nu = north_up_east_right(img, ctx.corners,
                                     line=tile["line0"] + (tile["n_lines"] - 1) / 2,
                                     sample=tile["sample0"] + (tile["n_samples"] - 1) / 2)
            ctx.release()
            m_nac = Transform(np.array(cell["measured_to_block_matrix"], float), "affine")
            # MI px -> TC ref block px -> NAC matching px (EXP-019's controlled map)
            t_mi_to_ref, _ = map_between(mi_grid, tc_ref, mi[0].shape)
            t_map_n = m_nac.inverse() @ t_mi_to_ref
            nac_gsd = k_nac * ctx.scaled_pixel_m
            for name, bimg, nm in sources:
                if nm is None:
                    continue
                rec = run_cell(f"N/{key}/{name.split('/')[1]}", "N", bimg, nu.image, t_map_n,
                               nac_gsd, extra={"wavelength_nm": nm, "frame": key,
                                               "k_nac": k_nac, "nac_gsd_m": nac_gsd,
                                               "exp019_n_inliers": cell["n_inliers"]})
                n_cells.append(rec)
                print(f"  [N] {key:28s} {nm:6.0f} nm inl={rec.get('n_inliers', 0):5d} "
                      f"{'PASS' if rec.get('pass') else 'fail'} "
                      f"err={rec.get('err_median_m', float('nan')):8.2f} m", flush=True)

    # ---------------- arm T: thermal --------------------------------------
    print("\n== arm T: Diviner bolometric temperature against TC pan at 28:1 ==", flush=True)
    k_div = int(round(DIV_GSD_M / TC_GSD_M))
    tc_div = degrade_to_gsd(tc_ref.data, k_div, psf_fwhm_coarse_px=PSF)
    tc_div_grid = _degraded_map_block(tc_ref, k_div)
    t_map_t, resid_t = map_between(div, tc_div_grid, div.data.shape)
    t_cell = run_cell("T/diviner_tbol", "T", div.data, tc_div, t_map_t, TC_GSD_M * k_div,
                      extra={"k_tc": k_div, "ratio": DIV_GSD_M / TC_GSD_M,
                             "thermal_px": list(div.data.shape),
                             "pan_px": list(tc_div.shape)})
    print(f"  [T] diviner inl={t_cell.get('n_inliers', 0)} "
          f"kp {t_cell.get('n_keypoints_src')}/{t_cell.get('n_keypoints_dst')} "
          f"{'PASS' if t_cell.get('pass') else 'fail'} "
          f"err={t_cell.get('err_median_m', float('nan')):.1f} m", flush=True)

    # ---------------- arm 0: the null -------------------------------------
    print("\n== arm 0: the same sources against the TC NULL block ==", flush=True)
    null_cells = []
    tc_null_deg = degrade_to_gsd(tc_null.data, k_tc, psf_fwhm_coarse_px=PSF)
    h_n, w_n = tc_null_deg.shape
    h_s, w_s = mi[0].shape
    y_c, x_c = max(0, (h_n - h_s) // 2), max(0, (w_n - w_s) // 2)
    null_crop = tc_null_deg[y_c:y_c + h_s, x_c:x_c + w_s]
    for name, img, nm in sources:
        rec = run_cell(name.replace("B/", "0/").replace("P/", "0/"), "0", img, null_crop,
                       None, tc_deg_gsd, extra={"wavelength_nm": nm})
        null_cells.append(rec)
        print(f"  [0] {name:28s} inl={rec.get('n_inliers', 0):5d} "
              f"{'WRONG PASS' if rec.get('pass') else 'fail (expected)'}", flush=True)

    # ---------------- B4L beside ------------------------------------------
    second = []
    if not args.quick:
        print("\n== B4L beside (no criterion) ==", flush=True)
        for name, img, nm in sources:
            rec = run_cell(name, "B" if nm else "P", img, tc_deg, t_map_tc, tc_deg_gsd,
                           engine=SECOND_ENGINE, extra={"wavelength_nm": nm})
            second.append(rec)
            print(f"  [B4L] {name:28s} inl={rec.get('n_inliers', 0):5d} "
                  f"{'PASS' if rec.get('pass') else 'fail'} "
                  f"err={rec.get('err_median_m', float('nan')):7.2f} m", flush=True)

    # Reported, not a criterion: each band's disagreement with the PAN arm's own
    # solution. The band-vs-label error contains whatever offset the two products
    # carry between them; the band-vs-pan error contains only the wavelength.
    pan_cell = next((c for c in cells if c.get("arm") == "P"), None)
    if pan_cell and pan_cell.get("transform_matrix"):
        t_pan = Transform(np.array(pan_cell["transform_matrix"], float), "affine")
        g = pixel_grid(mi[0].shape, step=GRID_STEP)
        p_pan = t_pan.apply(g)
        for c in cells:
            if c.get("arm") != "B" or not c.get("transform_matrix"):
                continue
            d = np.linalg.norm(Transform(np.array(c["transform_matrix"], float),
                                         "affine").apply(g) - p_pan, axis=1)
            c["vs_pan_median_dst_px"] = float(np.median(d))
            c["vs_pan_median_m"] = float(np.median(d) * tc_deg_gsd)

    crit = evaluate(cells, c_cells, n_cells, t_cell, null_cells, s0)
    doc = {
        "stage": STAGE,
        "preregistration": "docs/stages/EXP-020_multimodality.md Part 1 (commit 4e043a4)",
        "quick_mode": args.quick,
        "products": {
            "kaguya_mi": {"manifest": MI_MANIFEST, "gsd_m": MI_GSD_M,
                          "bands_nm": bands_nm, "credit": mi_man["credit"],
                          "valid_fraction_per_band": mi_man["valid_fraction_per_band"]},
            "kaguya_tc": {"manifest": TC_REF_MANIFEST, "gsd_m": TC_GSD_M, "k": k_tc},
            "diviner": {"manifest": DIV_MANIFEST, "gsd_m": DIV_GSD_M,
                        "credit": div_man["credit"], "k_tc": k_div},
            "chandrayaan2_tmc2": {"block": _e19.TMC2_BLOCK, "gsd_m": tmc_gsd, "k": k_tmc},
        },
        "pipeline": {"function": "siim.pipeline.register_pair", "engine": ENGINE, **BASE,
                     "failure_rule": f"n_inliers <= {RULE} (D-023)",
                     "operator": f"degrade_to_gsd, psf_fwhm_coarse_px = {PSF}",
                     "error_statistic": "|| T_hat(x) - T_map(x) || on an 8 px grid, where T_map "
                                        "is the analytic map between the two products' labels"},
        "criteria": crit,
        "cells": cells, "arm_C": c_cells, "arm_N": n_cells, "arm_T": t_cell,
        "null_cells": null_cells, "second_engine": second,
        "analytic_map_residual_px": {"mi_to_tc": resid_tc, "diviner_to_tc": resid_t},
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "opencv": cv2.__version__, "platform": platform.platform()},
        "total_runtime_s": time.perf_counter() - t_start,
        "claims_not_supported": [
            "NOT an IIRS result: no IIRS product exists in this repository (RL-046). Kaguya MI is "
            "414-1548 nm at 14.8 m; IIRS is 800-5000 nm at 80 m.",
            "NOT a thermal-infrared imaging result: Diviner tbol is a gridded derived product at "
            "236.9 m, not an image from a thermal camera.",
            "NOT accuracy across missions: errors are measured against label maps whose relative "
            "georeferencing carries the term EXP-019 measured at 137.6 m for the archive.",
            "NOT an illumination result: MI and TC share a standard geometry by construction.",
            "One mare window, one terrain class, one engine in every criterion.",
            "NOT a verdict change: assess(), select_model and every constant are untouched.",
        ],
    }
    out_path.write_text(json.dumps(doc, indent=1, default=_json_default), encoding="utf-8")
    c = crit
    print(f"\nS0 {'MET' if c['S0']['met'] else 'NOT MET'} | "
          f"S1 {'MET' if c['S1']['met'] else 'NOT MET'} ({c['S1']['n_pass']}/{c['S1']['n_bands']}, "
          f"median err {c['S1']['median_err_m']}) | "
          f"S2 {'MET' if c['S2']['met'] else 'NOT MET'} (worst ratio {c['S2']['worst_ratio']}) | "
          f"S3 {'MET' if c['S3']['met'] else 'NOT MET'} ({c['S3']['n_pass']}) | "
          f"S4 {'MET' if c['S4']['met'] else 'NOT MET'} ({c['S4']['n_bands']} bands, "
          f"{c['S4']['n_frames']} frames) | "
          f"S5 {'MET' if c['S5']['met'] else 'NOT MET'} | "
          f"S6 {'MET' if c['S6']['met'] else 'NOT MET'} ({c['S6']['n_pass']} passes)")
    print(f"wrote {out_path} in {doc['total_runtime_s']:.0f}s")


def mi_grid_gate(grid: MapBlock, man: dict) -> dict:
    t = man["tiles"][0]
    summ = t["label_summary"]
    ppd = grid.ppd_lat
    err = {
        "MAXIMUM_LATITUDE": abs(((t["lat_top_deg"] - summ["MAXIMUM_LATITUDE"]) * ppd) - 0.5),
        "MINIMUM_LATITUDE": abs(((t["lat_top_deg"] - summ["MINIMUM_LATITUDE"]) * ppd)
                                - (t["lines"] - 0.5)),
        "WESTERNMOST_LONGITUDE": abs(((summ["WESTERNMOST_LONGITUDE"] - t["lon_left_deg"]) * ppd)
                                     - 0.5),
        "EASTERNMOST_LONGITUDE": abs(((summ["EASTERNMOST_LONGITUDE"] - t["lon_left_deg"]) * ppd)
                                     - (t["samples"] - 0.5)),
    }
    rng = np.random.default_rng(0)
    lon = rng.uniform(man["window_lon"][0], man["window_lon"][1], 10000)
    lat = rng.uniform(man["window_lat"][0], man["window_lat"][1], 10000)
    xy = grid.block_xy_of_lonlat(lon, lat)
    rt = float(max(np.abs(grid.lat_of_line(xy[:, 1] + grid.row0) - lat).max(),
                   np.abs(grid.lon_of_sample(xy[:, 0] + grid.col0) - lon).max()))
    return {"met": bool(max(err.values()) < 0.5 and rt < 1e-9), "corner_error_px": err,
            "roundtrip_max_deg": rt, "ppd": ppd, "tiles": [t["product_id"] for t in man["tiles"]],
            "tile_sha256": man["tile_sha256"], "valid_fraction_per_band":
                man["valid_fraction_per_band"]}


def diviner_grid_gate(block: MapBlock, man: dict) -> dict:
    summ = man["label_summary"]
    ppd = block.ppd_lat
    err = {
        "MAXIMUM_LATITUDE": abs((block.lat_top_deg - summ["MAXIMUM_LATITUDE"]) * ppd),
        "WESTERNMOST_LONGITUDE": abs((summ["WESTERNMOST_LONGITUDE"] - block.lon_left_deg) * ppd),
    }
    rng = np.random.default_rng(0)
    lon = rng.uniform(man["window_lon"][0], man["window_lon"][1], 10000)
    lat = rng.uniform(man["window_lat"][0], man["window_lat"][1], 10000)
    xy = block.block_xy_of_lonlat(lon, lat)
    rt = float(max(np.abs(block.lat_of_line(xy[:, 1] + block.row0) - lat).max(),
                   np.abs(block.lon_of_sample(xy[:, 0] + block.col0) - lon).max()))
    return {"met": bool(max(err.values()) < 0.5 and rt < 1e-9), "corner_error_px": err,
            "roundtrip_max_deg": rt, "ppd": ppd, "bytes_sha256": man["bytes_sha256"],
            "missing_fraction": man["dn"]["missing_fraction"]}


def evaluate(cells, c_cells, n_cells, t_cell, null_cells, s0) -> dict:
    bands = [c for c in cells if c.get("arm") == "B"]
    pan = next((c for c in cells if c.get("arm") == "P"), {})
    ok = [c for c in bands if c.get("pass") and c.get("err_median_m") is not None]
    within = [c for c in ok if c["err_median_m"] < S1_BOUND_M]
    s1 = {"met": bool(len(within) >= S1_MIN_BANDS), "n_bands": len(bands), "n_pass": len(ok),
          "n_within_bound": len(within), "bar": f">= {S1_MIN_BANDS} bands within {S1_BOUND_M:.2f} m",
          "median_err_m": float(np.median([c["err_median_m"] for c in ok])) if ok else None,
          "per_band": [{"wavelength_nm": c.get("wavelength_nm"), "n_inliers": c.get("n_inliers"),
                        "pass": c.get("pass"), "err_median_m": c.get("err_median_m"),
                        "err_median_ref_px": c.get("err_median_ref_px"),
                        "contrast": c.get("contrast"),
                        "n_keypoints_src": c.get("n_keypoints_src")} for c in bands]}
    pan_err = pan.get("err_median_m")
    ratios = ([{"wavelength_nm": c.get("wavelength_nm"),
                "ratio": c["err_median_m"] / pan_err} for c in ok]
              if pan.get("pass") and pan_err else [])
    worst = max(ratios, key=lambda r: r["ratio"]) if ratios else None
    s2 = {"met": bool(pan.get("pass") and ratios and len(within) >= S1_MIN_BANDS
                      and worst["ratio"] <= S2_MAX_RATIO),
          "pan_pass": bool(pan.get("pass")), "pan_err_median_m": pan_err,
          "pan_contrast": pan.get("contrast"),
          "bar": f"every succeeding band <= {S2_MAX_RATIO}x the pan comparator",
          "worst_ratio": worst["ratio"] if worst else None,
          "worst_band_nm": worst["wavelength_nm"] if worst else None,
          "ratios": ratios}
    c_ok = [c for c in c_cells if c.get("pass") and c.get("err_median_m") is not None
            and c["err_median_m"] < S3_BOUND_M]
    s3 = {"met": bool(len(c_ok) >= 1), "n_pass": sum(1 for c in c_cells if c.get("pass")),
          "n_within_bound": len(c_ok), "bar_m": S3_BOUND_M,
          "best": min((c for c in c_cells if c.get("err_median_m") is not None),
                      key=lambda c: c["err_median_m"], default={}).get("err_median_m"),
          "per_band": [{"wavelength_nm": c.get("wavelength_nm"), "n_inliers": c.get("n_inliers"),
                        "pass": c.get("pass"), "err_median_m": c.get("err_median_m")}
                       for c in c_cells]}
    n_ok = [c for c in n_cells if c.get("pass")]
    s4 = {"met": bool(len({c["wavelength_nm"] for c in n_ok}) >= S4_MIN_BANDS
                      and len({c["frame"] for c in n_ok}) >= S4_MIN_FRAMES),
          "n_bands": len({c["wavelength_nm"] for c in n_ok}),
          "n_frames": len({c["frame"] for c in n_ok}), "n_cells": len(n_cells),
          "bar": f">= {S4_MIN_BANDS} bands on >= {S4_MIN_FRAMES} frames",
          "err_median_m": float(np.median([c["err_median_m"] for c in n_ok
                                           if c.get("err_median_m") is not None]))
          if n_ok else None,
          "per_cell": [{"frame": c.get("frame"), "wavelength_nm": c.get("wavelength_nm"),
                        "n_inliers": c.get("n_inliers"), "pass": c.get("pass"),
                        "err_median_m": c.get("err_median_m")} for c in n_cells]}
    s5 = {"met": bool(t_cell.get("pass") and t_cell.get("err_median_m") is not None
                      and t_cell["err_median_m"] < S5_BOUND_M),
          "bar_m": S5_BOUND_M, "n_inliers": t_cell.get("n_inliers"),
          "err_median_m": t_cell.get("err_median_m"),
          "n_keypoints_thermal": t_cell.get("n_keypoints_src"),
          "n_keypoints_pan": t_cell.get("n_keypoints_dst"),
          "ratio": t_cell.get("ratio"), "thermal_px": t_cell.get("thermal_px"),
          "pan_px": t_cell.get("pan_px"),
          "failure_mode": (None if t_cell.get("pass") else
                           ("starvation" if (t_cell.get("n_keypoints_src") or 0) < 50
                            else "descriptor"))}
    n_null_pass = sum(1 for c in null_cells if c.get("pass"))
    s6 = {"met": bool(n_null_pass == 0), "n_cells": len(null_cells), "n_pass": n_null_pass,
          "expected_cells": S6_N_CELLS,
          "false_accept_fraction": n_null_pass / len(null_cells) if null_cells else None}
    return {"S0": s0, "S1": s1, "S2": s2, "S3": s3, "S4": s4, "S5": s5, "S6": s6}


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
