"""EXP-020 supplementary — arm N with the source cropped to the overlap.

**This is reported BESIDE criterion S4 and is not folded into it.** S4 is read
on the arm the runner ran, exactly as Part 1 froze the population; this script
measures whether that arm's outcome is a property of *modality* or of *framing*.

In the recorded run, arm N put the whole 1477 x 596 MI mosaic (21.8 x 30.6 km)
against one NAC tile's 455 x 228 px matching image (3.8 x 1.9 km): the overlap
is about **15 % of the source area**, so 85 % of the source's keypoints have no
possible match and the ratio test is being asked to find a needle. The other
arms do not have this problem -- the TC pan reference covers the whole MI
window, and arm C's TMC-2 block is cut to its own footprint.

Here the MI source is cut to each NAC tile's archive-predicted footprint plus a
2 km margin, which is the construction EXP-019 used for every one of its cells,
and nothing else changes: same bands, same engine, same seed, same threshold,
same error statistic against EXP-019's controlled position for that frame.

    python scripts/run_exp020_armN_cropped.py
"""

from __future__ import annotations

import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.geometry import Transform, estimate, pixel_grid  # noqa: E402
from siim.ingest.orientation import north_up_east_right  # noqa: E402
from siim.preprocessing.degrade import degrade_to_gsd  # noqa: E402


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_e7 = _load("_exp007s", "scripts/run_exp007.py")
_rd7 = _load("_rd07s", "scripts/run_real_data_07.py")
_e19 = _load("_exp019s", "scripts/run_exp019.py")
_e20 = _load("_exp020s", "scripts/run_exp020.py")

import argparse

MARGIN_M = 2000.0
MAX_FRAMES = 4


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", default="B1", help="B1 (as arm N ran) or B4L")
    args = ap.parse_args()
    engine = args.engine
    out = (ROOT / "experiments" / "EXP-020" /
           ("exp020_armN_cropped.json" if engine == "B1"
            else f"exp020_armN_cropped_{engine.lower()}.json"))
    if out.exists():
        raise SystemExit(f"{out} exists (integrity rule 4)")
    t0 = time.perf_counter()
    mi, mi_grid, mi_man = _e20.mi_block()
    from siim.ingest.mapgrid import load_map_block
    tc_ref = load_map_block(_e20.TC_REF_MANIFEST)
    bands_nm = mi_man["bands_nm"]
    margin_px = int(round(MARGIN_M / _e20.MI_GSD_M))

    e19 = json.loads((ROOT / "experiments" / "EXP-019" /
                      "exp019_results.json").read_text(encoding="utf-8"))
    passes = [(k, c) for k, c in e19["cells"].items()
              if c.get("arm") == "R" and c.get("kind") == "NAC" and c.get("pass")
              and c.get("measured_to_block_matrix")]
    passes.sort(key=lambda kc: -kc[1]["n_inliers"])
    products = _rd7.load_products()
    rows = []
    for key, cell in passes[:MAX_FRAMES]:
        window, pdsid = key.split("/")
        man = json.loads((ROOT / "data" / "manifests" /
                          _rd7.WINDOWS[window]).read_text(encoding="utf-8"))
        tile = {t["pdsid"]: t for t in man["tiles"]}[pdsid]
        ctx = _e7.FrameContext(pdsid, tile, products,
                               tuple(man["target_ground_point_lon_lat"]))
        k_nac = _e19.K_FRAME[pdsid]
        img = _e7.stretch(degrade_to_gsd(ctx.raw(), k_nac, psf_fwhm_coarse_px=_e20.PSF))
        nu = north_up_east_right(img, ctx.corners,
                                 line=tile["line0"] + (tile["n_lines"] - 1) / 2,
                                 sample=tile["sample0"] + (tile["n_samples"] - 1) / 2)
        nac_gsd = k_nac * ctx.scaled_pixel_m
        ctx.release()

        m_nac = Transform(np.array(cell["measured_to_block_matrix"], float), "affine")
        t_mi_to_ref, _ = _e20.map_between(mi_grid, tc_ref, mi[0].shape)
        t_map_full = m_nac.inverse() @ t_mi_to_ref      # MI px -> NAC matching px

        # the NAC tile's footprint in MI pixels, through the SAME map
        h_n, w_n = nu.image.shape
        corners = np.array([[0, 0], [w_n - 1, 0], [w_n - 1, h_n - 1], [0, h_n - 1]], float)
        inv = t_map_full.inverse()
        f = inv.apply(corners)
        x0 = max(0, int(np.floor(f[:, 0].min())) - margin_px)
        y0 = max(0, int(np.floor(f[:, 1].min())) - margin_px)
        x1 = min(mi.shape[2], int(np.ceil(f[:, 0].max())) + margin_px + 1)
        y1 = min(mi.shape[1], int(np.ceil(f[:, 1].max())) + margin_px + 1)
        if x1 - x0 < 32 or y1 - y0 < 32:
            rows.append({"frame": key, "excluded": "footprint outside the MI block"})
            continue
        shift = Transform(np.array([[1.0, 0, x0], [0, 1.0, y0], [0, 0, 1.0]]), "euclidean")
        t_map = t_map_full @ shift                      # cropped MI px -> NAC matching px
        full_area = mi.shape[1] * mi.shape[2]
        crop_area = (y1 - y0) * (x1 - x0)
        overlap_frac_full = (w_n * h_n) * (nac_gsd / _e20.MI_GSD_M) ** 2 / full_area
        print(f"{key}: crop [{x0},{y0},{x1},{y1}] = {x1 - x0} x {y1 - y0} px "
              f"(was {mi.shape[2]} x {mi.shape[1]}); overlap was "
              f"{overlap_frac_full:.3f} of the source", flush=True)
        for b in range(mi.shape[0]):
            src = mi[b, y0:y1, x0:x1]
            rec = _e20.run_cell(f"N'/{key}/band{b + 1}", "N-cropped", src, nu.image,
                                t_map, nac_gsd, engine=engine,
                                extra={"wavelength_nm": bands_nm[b], "frame": key,
                                       "crop": [x0, y0, x1, y1], "k_nac": k_nac,
                                       "nac_gsd_m": nac_gsd,
                                       "source_area_ratio": crop_area / full_area,
                                       "overlap_fraction_uncropped": overlap_frac_full,
                                       "exp019_n_inliers": cell["n_inliers"]})
            rows.append(rec)
            print(f"   {bands_nm[b]:6.0f} nm inl={rec.get('n_inliers', 0):5d} "
                  f"{'PASS' if rec.get('pass') else 'fail'} "
                  f"err={rec.get('err_median_m', float('nan')):8.2f} m", flush=True)

    ok = [r for r in rows if r.get("pass")]
    doc = {
        "stage": "EXP-020", "part": "supplementary — reported beside S4, not folded into it",
        "engine": engine,
        "preregistration": "docs/stages/EXP-020_multimodality.md Part 1 (commit 4e043a4); "
                           "this arm is NOT the frozen arm N and does not change S4",
        "what_changed": "the MI source is cut to each NAC tile's archive-predicted footprint "
                        "plus a 2 km margin, the construction EXP-019 used for every cell; "
                        "bands, engine, seed, threshold and error statistic are unchanged",
        "n_cells": len(rows), "n_pass": len(ok),
        "n_bands_passing": len({r["wavelength_nm"] for r in ok}),
        "n_frames_passing": len({r["frame"] for r in ok}),
        "err_median_m": (float(np.median([r["err_median_m"] for r in ok
                                          if r.get("err_median_m") is not None]))
                         if ok else None),
        "rows": rows,
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "platform": platform.platform()},
        "total_runtime_s": time.perf_counter() - t0,
    }
    out.write_text(json.dumps(doc, indent=1, default=_e20._json_default), encoding="utf-8")
    print(f"\n{len(ok)}/{len(rows)} cells pass; {doc['n_bands_passing']} bands on "
          f"{doc['n_frames_passing']} frames; median err "
          f"{doc['err_median_m']} m\nwrote {OUT} in {doc['total_runtime_s']:.0f}s")


if __name__ == "__main__":
    main()
