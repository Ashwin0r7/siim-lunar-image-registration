"""REAL-DATA-09 — Chandrayaan-2 TMC-2 ↔ LRO NAC, run against the frozen criteria.

Pre-registered in `docs/stages/REAL-DATA-09_chandrayaan2_ingestion.md` Part 1
(commit 720b161), implemented per `docs/REAL-DATA-09_IMPLEMENTATION_PLAN.md`.

Products actually delivered by PRADAN (see `data/manifests/chandrayaan2_manifest.json`):
TMC-2 calibrated image, TMC-2 DTM, TMC-2 L2 ortho (all equatorial, covering the
recorded NAC ground) and two OHRC observations (**South Pole**, ~69.5°S 32.2°E).
No IIRS product. The pairs Part 1 §5 fixes therefore resolve as:

    P1  TMC-2 ortho <-> NAC degraded to the TMC-2 GSD   -- RUNS
    P2  NAC <-> OHRC                                    -- no_data (see below)
    P3  OHRC <-> TMC-2 ortho                            -- no_data
    P4  IIRS <-> WAC / NAC                              -- no_data (no IIRS delivered)
    P5  TMC-2 ortho <-> TMC-2 DEM render                -- RUNS (Q4, the fine-DEM test)
    P6  OHRC in IIRS pixels                             -- no_data

**OHRC is reported `no_data`, not "failed".** Both observations lie over the
Chandrayaan-3 landing region near 69.5°S -- the fallback site Part 1 §3 named.
Reaching it needs a fresh NAC acquisition there; no NAC tile from that region is
on disk. Part 1's refusal table is explicit: *"OHRC swath misses both recorded
windows -> P2, P3, P6 report no_data; the stage says so"*, and moving the target
to wherever OHRC happens to look is listed as not allowed.

Overlap is verified before anything is interpreted (D-035): the fraction of
non-zero TMC-2 pixels under each NAC footprint is measured, and a pair with no
valid TMC-2 coverage is excluded before an engine is run.

    python scripts/run_real_data_09.py            # P1 + P5
    python scripts/run_real_data_09.py --pairs P1
"""

from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.baselines import learned_available, run_baseline  # noqa: E402
from siim.demo.verdict import assess  # noqa: E402
from siim.evaluation.coverage import coverage_metrics  # noqa: E402
from siim.geometry import endpoint_error, estimate  # noqa: E402
from siim.ingest.geotiff import decode_window, place, read_geometry, structural_identity  # noqa: E402
from siim.ingest.lola_dem import _lonlat_grid  # noqa: E402
from siim.ingest.orientation import north_up_east_right  # noqa: E402
from siim.preprocessing.degrade import degrade_to_gsd  # noqa: E402

_spec = importlib.util.spec_from_file_location("_exp007", ROOT / "scripts" / "run_exp007.py")
_e7 = importlib.util.module_from_spec(_spec)
sys.modules["_exp007"] = _e7
_spec.loader.exec_module(_e7)

STAGE = "REAL-DATA-09"
DATA = ROOT / "data"
OUT = ROOT / "experiments" / STAGE
RULE = _e7.N_INLIERS_FAILURE_RULE
BASE = {"model": "affine", "ransac_threshold_px": 3.0, "seed": 0}
ENGINES = {"b1": "B1", "lg": "B4L"}

MANIFEST = DATA / "manifests" / "chandrayaan2_manifest.json"
NAC_SOURCES = [("real_data_07_rd03_manifest.json", "RD03"),
               ("real_data_07_rd04_manifest.json", "RD04"),
               ("exp007_long_triplet_abc_manifest.json", "RD03-long"),
               ("exp007_long_triplet_abd_manifest.json", "RD04-long")]

#: Part 1 §5: floor = max(150 m, sigma_C2) / GSD_reference + 1.2 % bilinear term.
#: sigma_C2 is the product's stated accuracy when the label gives one -- it does
#: (`product_accuracy_rmse_CE`), so the 50 m assumption is NOT used.
CORNER_QUANTISATION_M = 150.0
BILINEAR_TERM = 0.012

#: A NAC footprint with less valid TMC-2 coverage than this is excluded before
#: any engine runs. Overlap is established first (D-035); it is not inferred
#: from a failed match.
MIN_VALID_FRACTION = 0.05


def tmc_products() -> dict:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    out = {}
    for rec in man["products"].values():
        out.setdefault(f"{rec['instrument']}:{rec['kind']}", rec)
    return out


def load_nac_products() -> dict:
    prod: dict = {}
    for p in glob.glob(str(DATA / "manifests" / "*.json")):
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and isinstance(d.get("products"), dict):
            prod.update(d["products"])
    return prod


def footprint_in_block(ctx, k: int, block, margin_px: int):
    """NAC tile footprint -> block pixels, the crop window, and the affine map.

    Same construction REAL-DATA-08 used for Mini-RF and WAC
    (`scripts/run_real_data_08.py:predicted_map`): a grid of tile pixels is
    pushed through the NAC corner map to lon/lat and then through the map
    product's own geometry. Returns (G: NAC-tile-px -> block-crop-px,
    (x0, y0), (x1, y1)).
    """
    w = ctx.window(k)
    h, wd = w.shape
    gy, gx = np.mgrid[0:h:max(1, h // 8), 0:wd:max(1, wd // 8)]
    pts = np.column_stack([gx.ravel(), gy.ravel()]).astype(float)
    lines = np.array([w.to_frame(y, x)[0] for x, y in pts])
    samples = np.array([w.to_frame(y, x)[1] for x, y in pts])
    lon, lat = _lonlat_grid(ctx.corners, lines, samples)
    xy = block.block_xy_of_lonlat(lon, lat)
    x0 = max(0, int(np.floor(xy[:, 0].min())) - margin_px)
    y0 = max(0, int(np.floor(xy[:, 1].min())) - margin_px)
    x1 = int(np.ceil(xy[:, 0].max())) + margin_px + 1
    y1 = int(np.ceil(xy[:, 1].max())) + margin_px + 1
    res = estimate(pts, xy - np.array([x0, y0]), "affine")
    return (res.transform if res.ok else None), (x0, y0), (x1, y1)


def run_p1(ctx, window: str, tif: Path, geo, sigma_c2_m: float,
           engines: list[str]) -> list[dict]:
    """One NAC frame against the TMC-2 ortho at the TMC-2 GSD."""
    k = ctx.tile.get("decimation", 2)
    nac_m = ctx.scaled_pixel_m
    # geometry-only block for the pixel map (2x2 read, no image data)
    probe = place(tif, row0=0, row1=2, col0=0, col1=2, name="tmc2-probe")
    ref_gsd = float(np.mean(probe.metres_per_pixel))

    g, (x0, y0), (x1, y1) = footprint_in_block(ctx, k, probe, margin_px=60)
    x1 = min(int(geo.shape[1]), x1)
    y1 = min(int(geo.shape[0]), y1)
    base = {"pair": "P1", "window": window, "frame": ctx.pdsid,
            "nac_incidence_deg": ctx.incidence_published,
            "tmc2_block": [x0, y0, x1, y1]}
    if g is None or x1 <= x0 or y1 <= y0:
        return [dict(base, excluded="no geometry prediction")]

    crop = decode_window(tif, y0, y1, x0, x1)
    valid = float((crop > 0).mean())
    base["tmc2_valid_fraction"] = round(valid, 4)
    if valid < MIN_VALID_FRACTION:
        return [dict(base, excluded="no valid TMC-2 coverage under this NAC "
                                    f"footprint ({valid:.1%} non-zero)")]

    # --- §4 step 7: degrade NAC to the coarser (TMC-2) GSD, PSF-aware --------
    factor = int(round(ref_gsd / (k * nac_m)))
    factor = max(1, factor)
    nac = ctx.img(k)
    nac_deg = degrade_to_gsd(nac, factor, psf_fwhm_coarse_px=1.0) if factor > 1 else nac
    # --- §4 step 8: orientation, reflection-aware (E-037) -------------------
    t = ctx.tile
    nu = north_up_east_right(
        _e7.stretch(nac_deg), ctx.corners,
        line=t["line0"] + (t["n_lines"] - 1) / 2,
        sample=t["sample0"] + (t["n_samples"] - 1) / 2)

    # prediction: NAC tile px -> block crop px, then to north-up degraded px
    scale = 1.0 / factor
    S = np.array([[scale, 0, 0], [0, scale, 0], [0, 0, 1]], float)
    from siim.geometry import Transform
    g_deg = g @ Transform(np.linalg.inv(S), "affine")      # degraded px -> crop px
    g_nu = g_deg @ nu.inverse                              # north-up px -> crop px
    pred_tmc_to_nac = g_nu.inverse()                       # crop px -> north-up px

    src = _e7.stretch(crop)                                # TMC-2 ortho (source)
    ref = nu.image                                         # NAC degraded (reference)
    floor_px = (max(CORNER_QUANTISATION_M, sigma_c2_m) / ref_gsd
                + BILINEAR_TERM * np.hypot(*ref.shape) / 2)

    rows = []
    for eng in engines:
        t0 = time.perf_counter()
        try:
            res = run_baseline(ENGINES[eng], src, ref, model=BASE["model"],
                               ransac_threshold=BASE["ransac_threshold_px"],
                               seed=BASE["seed"])
        except Exception as exc:  # noqa: BLE001 - an engine failure is a result
            rows.append(dict(base, engine=eng, error=repr(exc)[:200]))
            continue
        mask = (np.asarray(res.inlier_mask, bool) if np.size(res.inlier_mask)
                else np.zeros(0, bool))
        n_in = int(mask.sum())
        rec = dict(base)
        rec.update({
            "engine": eng, "direction": "TMC2_ortho_crop -> NAC_degraded_northup",
            "src_shape": list(src.shape), "ref_shape": list(ref.shape),
            "nac_native_gsd_m": round(k * nac_m, 4),
            "degrade_factor": factor,
            "nac_effective_gsd_m": round(k * nac_m * factor, 4),
            "tmc2_gsd_m": round(ref_gsd, 4),
            "delta_incidence_deg": round(abs(ctx.incidence_published - TMC_INCIDENCE), 3),
            "n_keypoints_src": int(len(res.src_features)),
            "n_keypoints_dst": int(len(res.dst_features)),
            "n_putative": int(res.matches.src_points.shape[0]),
            "n_inliers": n_in,
            "fit_rmse_px": float(res.ransac.inlier_rmse),
            "fit_rmse_is_not_accuracy": True,
            "pass": bool(n_in > RULE),
            "wall_s": round(time.perf_counter() - t0, 2),
        })
        if n_in >= 3:
            cov = coverage_metrics(res.matches.src_points[mask], src.shape)
            rec["coverage_max_uncovered_disc_ratio"] = float(cov.max_uncovered_disc_ratio)
        if res.transform is not None:
            err = endpoint_error(res.transform, pred_tmc_to_nac, src.shape, step=16)
            rec["geometry"] = {
                "disagreement_px_median": err.median, "p90": err.p90,
                "floor_px": floor_px, "excess": err.median / floor_px,
                "sigma_c2_m_used": sigma_c2_m,
                "sigma_c2_source": "label product_accuracy_rmse_CE",
                "verdict": ("CONSISTENT" if err.median <= floor_px else
                            "INCONSISTENT" if err.median > 3 * floor_px
                            else "INCONCLUSIVE"),
                "floor_note": "max(150 m corner quantisation, sigma_C2) in "
                              "reference px + 1.2% bilinear term",
            }
            rec["transform_matrix"] = np.asarray(res.transform.matrix).tolist()
            v = assess(transform=res.transform,
                       src_points=res.matches.src_points,
                       dst_points=res.matches.dst_points,
                       inlier_mask=mask, shape=src.shape,
                       fit_rmse=rec["fit_rmse_px"])
            rec["verdict"] = v.as_dict()
        else:
            rec["geometry"] = {"verdict": "no transform"}
        rec["wrong_pass"] = bool(rec["pass"]
                                 and rec["geometry"]["verdict"] == "INCONSISTENT")
        rec["success"] = bool(rec["pass"] and not rec["wrong_pass"])
        rows.append(rec)
        print(f"  P1 {window:10s} {ctx.pdsid[-12:]} {eng:3s} "
              f"dInc={rec['delta_incidence_deg']:5.2f} valid={valid:5.1%} "
              f"inl={n_in:5d} {rec['geometry']['verdict']:12s} "
              f"({rec['wall_s']:.0f}s)", flush=True)
    return rows


TMC_INCIDENCE = 20.744092


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default="P1")
    ap.add_argument("--engines", default="b1,lg",
                    help="comma list; the learned engine is memory-hungry on "
                         "the long windows and can be run in its own pass")
    ap.add_argument("--out", default="real_data_09_results.json")
    args = ap.parse_args()
    want = {p.strip().upper() for p in args.pairs.split(",")}

    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / args.out
    if out_path.exists():
        raise SystemExit(f"{out_path.relative_to(ROOT)} exists (integrity rule 4)")

    t_start = time.time()
    prods = tmc_products()
    ortho = prods.get("TMC-2:ortho")
    if ortho is None:
        raise SystemExit("no TMC-2 ortho in the manifest")
    tif = ROOT / ortho["data_file"]
    lf = ortho["label_fields"]
    sigma = float(lf.get("product_accuracy_rmse_CE") or 50.0)

    # --- §4 steps 1-2, before any window is decoded -----------------------
    geo = read_geometry(tif)
    ident = structural_identity(tif)
    print(f"TMC-2 ortho: {geo.shape} {geo.dtype} | tags {geo.tags_found}")
    print(f"  projection {geo.projection_name} | sigma_C2 {sigma} m "
          f"({'label' if lf.get('product_accuracy_rmse_CE') else 'assumed'})")
    for line in ident:
        print(f"  identity: {line}")

    asked = [e.strip() for e in args.engines.split(",") if e.strip()]
    engines = [e for e in asked if e != "lg" or learned_available()]
    nac_prod = load_nac_products()
    rows: list[dict] = []

    def snapshot() -> None:
        """Write the artefact after every frame.

        A frame that exhausts memory kills the process outright, and an
        exception handler cannot catch that. Writing as we go means a crash
        costs one frame, not the whole run.
        """
        out_path.write_text(json.dumps(build_doc(), indent=2), encoding="utf-8")

    # --- pairs with no data, reported as such ------------------------------
    no_data = {
        "P2": "OHRC <-> NAC: both OHRC observations are over the South Pole "
              "(~69.5S, 32.2E, incidence 78-79 deg); no NAC tile from that "
              "region is on disk. Part 1 refusal table: report no_data, do not "
              "move the target.",
        "P3": "OHRC <-> TMC-2 ortho: the OHRC products and the TMC-2 strip do "
              "not share ground (South Pole vs equatorial swath).",
        "P4": "IIRS <-> WAC/NAC: no IIRS product was delivered by PRADAN.",
        "P6": "OHRC in IIRS pixels: depends on P2/P3 and P4, none of which has data.",
    }

    def build_doc() -> dict:
        return {
            "stage": STAGE,
            "preregistration": "docs/stages/REAL-DATA-09_chandrayaan2_ingestion.md "
                               "Part 1 (frozen 2026-09-05, commit 720b161)",
            "manifest": "data/manifests/chandrayaan2_manifest.json",
            "engines": {k: ENGINES[k] for k in engines},
            "base": BASE,
            "failure_rule": f"n_inliers <= {RULE} fails (D-023)",
            "tmc2_ortho": {
                "product_id": ortho["product_id"],
                "sha256": ortho["data_file_sha256"],
                "shape": list(geo.shape), "dtype": geo.dtype,
                "geometry_tags_found": list(geo.tags_found),
                "projection": geo.projection_name,
                "structural_identity": ident,
                "solar_incidence_deg": lf.get("solar_incidence"),
                "sigma_c2_m": sigma,
                "sigma_c2_source": ("label product_accuracy_rmse_CE"
                                    if lf.get("product_accuracy_rmse_CE")
                                    else "assumed 50 m"),
            },
            "pairs_without_data": no_data,
            "rows": rows,
            "environment": {"python": sys.version.split()[0],
                            "numpy": np.__version__,
                            "platform": platform.platform()},
            "total_runtime_s": round(time.time() - t_start, 1),
            "acknowledgement": (
                "We acknowledge the use of data from the Chandrayaan-II, second "
                "lunar mission of the Indian Space Research Organisation (ISRO), "
                "archived at the Indian Space Science Data Centre (ISSDC)."),
            "claims_not_supported": [
                "No ground truth; the geometry check is a bound at its own floor.",
                "One TMC-2 strip, one region; no significance claim.",
                "No OHRC or IIRS result: those products were not delivered over "
                "ground this project has NAC coverage for.",
            ],
        }

    if "P1" in want:
        print("\n--- P1: TMC-2 ortho <-> NAC degraded to the TMC-2 GSD ---")
        seen = set()
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
                    ctx = _e7.FrameContext(t["pdsid"], t, nac_prod, target)
                except Exception as exc:  # noqa: BLE001
                    rows.append({"pair": "P1", "window": wname, "frame": t["pdsid"],
                                 "excluded": f"no context: {exc!r}"[:160]})
                    continue
                try:
                    rows.extend(run_p1(ctx, wname, tif, geo, sigma, engines))
                finally:
                    ctx.release()
                    snapshot()

    doc = build_doc()
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    ran = [r for r in rows if "engine" in r and "error" not in r]
    succ = [r for r in ran if r.get("success")]
    print(f"\nrows {len(rows)} | engine rows {len(ran)} | successes {len(succ)}")
    for r in succ:
        print(f"  SUCCESS {r['window']:10s} {r['frame'][-12:]} {r['engine']} "
              f"inl={r['n_inliers']} dInc={r['delta_incidence_deg']} "
              f"{r['geometry']['verdict']} verdict={r['verdict']['status']}")
    print(f"wrote {out_path.relative_to(ROOT)} in {doc['total_runtime_s']}s")


if __name__ == "__main__":
    main()
