"""REAL-DATA-09 P5 / S4 — the fine-DEM test of H0, on the TMC-2 stereo DEM.

Part 1 §2 Q4: *"Does the TMC-2 DEM, rendered under each image's Sun, carry
matchable structure where the 59 m SLDEM did not (RL-039b)?"*
Part 1 §6 H4: **S4 MET if P5's render arm passes at least one pair that the raw
B1 arm of the same pair fails**, with a geometry-consistent composed transform.

This is the only remaining test of H0. EXP-007 could only fail it: the 59 m
SLDEM carries nothing matchable on this mare at 1.8-30 m (D-046, demoted to
conditional on a fine DEM). The TMC-2 DEM is **10.1 m** against a 5.05 m ortho
-- the ≈ 2:1 DEM/GSD ratio Part 1 predicted -- against ≈ 30:1 for SLDEM.

**Structure of the test, and why leg A is a control rather than a result.**
The TMC-2 ortho and its DTM are orthorectified onto the *same* map grid by
ISRO, so `ortho <-> render(DEM, TMC Sun)` is near-identity by construction. It
is run anyway, as a **positive control**: if the renderer, the DEM window or
the Sun convention were wrong, that leg would not return identity. The
hypothesis is carried entirely by leg B:

    leg A (control)  TMC-2 ortho        <-> render(DEM under TMC-2's Sun)
    leg B (the test) NAC degraded       <-> render(DEM under that NAC's Sun)
    composed         NAC -> TMC-2 ortho, through the DEM

Leg B matches each NAC frame against a render lit by **its own** Sun, so if the
DEM carries structure the illumination difference that defeats the raw arm is
removed.

    python scripts/run_real_data_09_p5.py
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
from siim.data.synthetic_terrain import render  # noqa: E402
from siim.geometry import Transform, endpoint_error  # noqa: E402
from siim.ingest.geotiff import decode_window, place, read_geometry  # noqa: E402
from siim.ingest.lola_dem import _lonlat_grid  # noqa: E402
from siim.ingest.orientation import north_up_east_right  # noqa: E402
from siim.ingest.solar_geometry import solar_geometry_at  # noqa: E402
from siim.preprocessing.degrade import degrade_to_gsd  # noqa: E402

_spec = importlib.util.spec_from_file_location("_exp007", ROOT / "scripts" / "run_exp007.py")
_e7 = importlib.util.module_from_spec(_spec)
sys.modules["_exp007"] = _e7
_spec.loader.exec_module(_e7)

DATA = ROOT / "data"
OUT = ROOT / "experiments" / "REAL-DATA-09"
BASE = {"model": "affine", "ransac_threshold_px": 3.0, "seed": 0}
RULE = _e7.N_INLIERS_FAILURE_RULE
MANIFEST = DATA / "manifests" / "chandrayaan2_manifest.json"
NAC_SOURCES = [("real_data_07_rd03_manifest.json", "RD03"),
               ("exp007_long_triplet_abc_manifest.json", "RD03-long"),
               ("exp007_long_triplet_abd_manifest.json", "RD04-long")]
MIN_VALID = 0.05
#: DTM nodata. int16 grid; ISRO uses a large negative fill.
NODATA_BELOW = -30000.0


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


def dem_on_ortho_grid(dtm_path, y0, y1, x0, x1):
    """DTM window covering ortho rows [y0,y1) cols [x0,x1), on the ortho grid.

    Ortho and DTM share a tiepoint and the DTM is exactly 2x coarser, so an
    ortho pixel (r, c) is DTM pixel (r/2, c/2). The DTM window is read at half
    the indices and repeated 2x to land back on the ortho grid -- a nearest
    upsample, stated rather than smoothed, because interpolating a DEM invents
    slope and slope is what is being tested.
    """
    d0, d1 = y0 // 2, (y1 + 1) // 2 + 1
    e0, e1 = x0 // 2, (x1 + 1) // 2 + 1
    dem = decode_window(dtm_path, d0, d1, e0, e1).astype(np.float64)
    dem[dem < NODATA_BELOW] = np.nan
    up = np.repeat(np.repeat(dem, 2, axis=0), 2, axis=1)
    oy, ox = y0 - 2 * d0, x0 - 2 * e0
    out = up[oy:oy + (y1 - y0), ox:ox + (x1 - x0)]
    if out.shape != (y1 - y0, x1 - x0):
        pad = np.full((y1 - y0, x1 - x0), np.nan)
        pad[:out.shape[0], :out.shape[1]] = out
        out = pad
    return out


def shade(dem_m, azimuth_deg, elevation_deg, pixel_scale_m):
    """Render the DEM under one Sun. NaNs are filled with the window median.

    The map grid is geographic with north up and east right, and `render`'s
    azimuth is compass-style clockwise from image-up, so the ground bearing
    from `solar_geometry_at` (and the TMC-2 label's `sun_azimuth`) goes in
    directly, with no rotation.
    """
    h = np.array(dem_m, dtype=np.float64)
    if np.isnan(h).all():
        return None, 1.0
    nan_frac = float(np.isnan(h).mean())
    h[np.isnan(h)] = float(np.nanmedian(h))
    img = render(h, azimuth_deg, elevation_deg, pixel_scale=pixel_scale_m,
                 cast_shadows=True, noise_std=0.0)
    return img, nan_frac


def correspondence_diagnostic(image, rendered):
    """Does the render's structure correspond to the image's at all?

    A failed match has two possible causes and they must be told apart: the
    render is misaligned (a defect in this script), or the render simply does
    not share structure with the image (the scientific result). A high-pass
    cross-correlation answers it directly -- if the peak sits at ~zero shift
    the geometry is right, and the peak *height* is then the honest measure of
    how much structure is shared.
    """
    from scipy.ndimage import gaussian_filter

    def hp(a):
        a = np.asarray(a, float)
        a = (a - a.mean()) / (a.std() + 1e-12)
        return a - gaussian_filter(a, 8)

    A, B = hp(image), hp(rendered)
    if A.shape != B.shape:
        return None
    F = np.fft.rfft2(A) * np.conj(np.fft.rfft2(B))
    cc = np.fft.irfft2(F, s=A.shape)
    cc /= (A.size * A.std() * B.std() + 1e-12)
    pk = np.unravel_index(int(np.argmax(cc)), cc.shape)
    dy = pk[0] - (A.shape[0] if pk[0] > A.shape[0] // 2 else 0)
    dx = pk[1] - (A.shape[1] if pk[1] > A.shape[1] // 2 else 0)
    return {"peak_correlation": float(cc.max()),
            "peak_shift_px": [int(dy), int(dx)],
            "correlation_at_zero_shift": float(cc[0, 0]),
            "peak_over_mean_abs": float(cc.max() / (np.abs(cc).mean() + 1e-12)),
            "note": "high-pass (sigma 8) normalised cross-correlation; a peak "
                    "at ~zero shift means the render is correctly aligned, so "
                    "the peak height is how much structure is actually shared"}


def match(src, dst, label):
    t0 = time.perf_counter()
    res = run_baseline("B1", src, dst, model=BASE["model"],
                       ransac_threshold=BASE["ransac_threshold_px"], seed=BASE["seed"])
    mask = (np.asarray(res.inlier_mask, bool) if np.size(res.inlier_mask)
            else np.zeros(0, bool))
    n = int(mask.sum())
    print(f"    {label:38s} inliers={n:6d}  ({time.perf_counter()-t0:.0f}s)", flush=True)
    return res, n


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="real_data_09_p5_dem_render.json")
    args = ap.parse_args()
    out_path = OUT / args.out
    if out_path.exists():
        raise SystemExit(f"{out_path.relative_to(ROOT)} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    man_c2 = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ortho = next(r for r in man_c2["products"].values()
                 if r["instrument"] == "TMC-2" and r["kind"] == "ortho")
    dtm = next(r for r in man_c2["products"].values()
               if r["instrument"] == "TMC-2" and r["kind"] == "dtm")
    tif = ROOT / ortho["data_file"]
    dtm_tif = ROOT / dtm["data_file"]
    lf = ortho["label_fields"]
    tmc_az = float(lf["sun_azimuth"])
    tmc_el = float(lf["sun_elevation"])
    geo = read_geometry(tif)
    probe = place(tif, row0=0, row1=2, col0=0, col1=2, name="probe")
    ref_gsd = float(np.mean(probe.metres_per_pixel))
    print(f"TMC-2 ortho {ref_gsd:.3f} m/px | DTM 2x coarser | "
          f"TMC-2 Sun az {tmc_az:.2f} el {tmc_el:.2f}\n")

    prod = nac_products()
    rows, seen = [], set()
    for mf, wname in NAC_SOURCES:
        mp = DATA / "manifests" / mf
        if not mp.exists():
            continue
        man = json.loads(mp.read_text(encoding="utf-8"))
        target = tuple(man["target_ground_point_lon_lat"])
        for t in man["tiles"]:
            key = (wname, t["pdsid"])
            if key in seen:
                continue
            seen.add(key)
            try:
                ctx = _e7.FrameContext(t["pdsid"], t, prod, target)
            except Exception:
                continue
            try:
                k = ctx.tile.get("decimation", 2)
                w = ctx.window(k)
                h, wd = w.shape
                gy, gx = np.mgrid[0:h:max(1, h // 8), 0:wd:max(1, wd // 8)]
                pts = np.column_stack([gx.ravel(), gy.ravel()]).astype(float)
                lines = np.array([w.to_frame(y, x)[0] for x, y in pts])
                samples = np.array([w.to_frame(y, x)[1] for x, y in pts])
                lon, lat = _lonlat_grid(ctx.corners, lines, samples)
                xy = probe.block_xy_of_lonlat(lon, lat)
                x0 = max(0, int(np.floor(xy[:, 0].min())) - 60)
                y0 = max(0, int(np.floor(xy[:, 1].min())) - 60)
                x1 = min(int(geo.shape[1]), int(np.ceil(xy[:, 0].max())) + 61)
                y1 = min(int(geo.shape[0]), int(np.ceil(xy[:, 1].max())) + 61)
                if x1 <= x0 or y1 <= y0:
                    continue
                crop = decode_window(tif, y0, y1, x0, x1)
                valid = float((crop > 0).mean())
                rec = {"window": wname, "frame": ctx.pdsid,
                       "tmc2_block": [x0, y0, x1, y1],
                       "tmc2_valid_fraction": round(valid, 4),
                       "nac_incidence_deg": ctx.incidence_published}
                if valid < MIN_VALID:
                    rec["excluded"] = f"no valid TMC-2 coverage ({valid:.1%})"
                    rows.append(rec)
                    continue

                dem = dem_on_ortho_grid(dtm_tif, y0, y1, x0, x1)
                sg = solar_geometry_at(target[0], target[1], *ctx.sub_solar)
                nac_az, nac_el = sg.azimuth_deg, 90.0 - sg.incidence_deg
                rec.update({"nac_sun_azimuth_deg": round(nac_az, 3),
                            "nac_sun_elevation_deg": round(nac_el, 3),
                            "tmc2_sun_azimuth_deg": tmc_az,
                            "tmc2_sun_elevation_deg": tmc_el,
                            "delta_incidence_deg": round(
                                abs(ctx.incidence_published - (90.0 - tmc_el)), 3)})
                print(f"  {wname:10s} {ctx.pdsid[-12:]} dInc="
                      f"{rec['delta_incidence_deg']:5.2f} valid={valid:5.1%} "
                      f"NAC Sun az {nac_az:.1f} el {nac_el:.1f}", flush=True)

                r_tmc, nan_t = shade(dem, tmc_az, tmc_el, ref_gsd)
                r_nac, _ = shade(dem, nac_az, nac_el, ref_gsd)
                rec["dem_nan_fraction"] = round(nan_t, 4)
                if r_tmc is None:
                    rec["excluded"] = "DEM window is entirely nodata"
                    rows.append(rec)
                    continue
                rec["dem_height_ptp_m"] = float(np.nanmax(dem) - np.nanmin(dem))

                factor = max(1, int(round(ref_gsd / (k * ctx.scaled_pixel_m))))
                deg = (degrade_to_gsd(ctx.img(k), factor, psf_fwhm_coarse_px=1.0)
                       if factor > 1 else ctx.img(k))
                tl = ctx.tile
                nu = north_up_east_right(
                    _e7.stretch(deg), ctx.corners,
                    line=tl["line0"] + (tl["n_lines"] - 1) / 2,
                    sample=tl["sample0"] + (tl["n_samples"] - 1) / 2)

                src_tmc = _e7.stretch(crop)
                resA, nA = match(src_tmc, _e7.stretch(r_tmc),
                                 "leg A control: ortho <-> render(TMC Sun)")
                resB, nB = match(nu.image, _e7.stretch(r_nac),
                                 "leg B TEST   : NAC   <-> render(NAC Sun)")
                rec["leg_a_control"] = {"n_inliers": nA, "pass": bool(nA > RULE)}
                rec["leg_b_test"] = {"n_inliers": nB, "pass": bool(nB > RULE)}
                rec["leg_a_correspondence"] = correspondence_diagnostic(
                    src_tmc, _e7.stretch(r_tmc))
                rec["leg_b_correspondence"] = correspondence_diagnostic(
                    nu.image, _e7.stretch(r_nac))

                if resA.transform is not None:
                    err = endpoint_error(resA.transform,
                                         Transform(np.eye(3), "affine"),
                                         src_tmc.shape, step=16)
                    rec["leg_a_control"]["deviation_from_identity_px"] = err.median
                if resA.transform is not None and resB.transform is not None:
                    composed = resA.transform.inverse() @ resB.transform
                    rec["composed_transform_matrix"] = np.asarray(
                        composed.matrix).tolist()
                    rec["composed"] = "NAC -> render -> ortho"
                rec["render_arm_passes"] = bool(nB > RULE)
                rows.append(rec)
            finally:
                ctx.release()

    ran = [r for r in rows if "leg_b_test" in r]
    passes = [r for r in ran if r["leg_b_test"]["pass"]]
    controls = [r for r in ran if r["leg_a_control"]["pass"]]
    doc = {
        "stage": "REAL-DATA-09", "pair": "P5", "criterion": "S4 / H4",
        "question": "Does the TMC-2 DEM, rendered under each image's Sun, carry "
                    "matchable structure where the 59 m SLDEM did not (RL-039b)?",
        "dem": {"product_id": dtm["product_id"],
                "sha256": dtm["data_file_sha256"], "gsd_m": round(2 * ref_gsd, 3)},
        "ortho": {"product_id": ortho["product_id"], "gsd_m": round(ref_gsd, 3)},
        "dem_over_gsd_ratio": 2.0,
        "engine": "B1 (unmodified RootSIFT)", "base": BASE,
        "failure_rule": f"n_inliers <= {RULE} fails (D-023)",
        "n_frames": len(ran),
        "leg_a_control_passes": len(controls),
        "leg_b_test_passes": len(passes),
        "rows": rows,
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
        "total_runtime_s": round(time.time() - t_start, 1),
        "claims_not_supported": [
            "No ground truth.",
            "Leg A is near-identity by construction (ISRO orthorectified the "
            "ortho and the DTM onto one grid); it is a control on the renderer "
            "and the Sun convention, not evidence for H0.",
            "One region, one TMC-2 strip.",
        ],
    }
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"\nframes {len(ran)} | leg A control passes {len(controls)} "
          f"| leg B (the test) passes {len(passes)}")
    for r in passes:
        print(f"  RENDER ARM PASSES {r['window']} {r['frame'][-12:]} "
              f"dInc={r['delta_incidence_deg']} inliers={r['leg_b_test']['n_inliers']}")
    print(f"wrote {out_path.relative_to(ROOT)} in {doc['total_runtime_s']}s")


if __name__ == "__main__":
    main()
