"""EXP-023 — OHRC <-> LRO NAC at the Chandrayaan-3 site, against the frozen criteria.

Pre-registered in `docs/stages/EXP-023_ohrc_nac_chandrayaan3_site.md` Part 1
(commit d273b8e). Inputs: the census (`experiments/EXP-023/census.json`), the
fetched NAC tiles (`data/manifests/exp023_manifest.json`), their index rows
(`data/manifests/exp023_index_geometry.json`) and the two OHRC products on disk.

What it does, in Part 1's order:

* S0 harness: OHRC MD5 against the label, PDS4 structure and file-size identity,
  the grid against both corner sets, handedness from the refined grid, the NAC
  incidence guard read from the census, NAC byte hashes from the manifest.
* Images: each NAC tile as the recorded pipeline prepares it
  (`stretch(decimate(raw, k))`, `north_up_east_right`). One OHRC window per
  observation, cut to the Na tile's ground footprint plus 5 %, degraded to Na's
  coarse GSD by `round(GSD / 0.26)` with a 1-coarse-px PSF (strip-wise, which
  is identical to the whole-image call), stretched and oriented by the same
  function from the refined corners.
* Every edge is its own B1 run on its own image pair (E-021); B4L beside.
* Geometry corroboration against the refined grid (and, reported, the
  system-level corners), with REAL-DATA-09's floor.
* Loops and `assess()` for the primary and secondary triangles; the
  displaced-ground nulls; B4L agreement.

    python scripts/run_exp023.py
"""

from __future__ import annotations

import glob
import hashlib
import importlib.util
import json
import os
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.baselines import run_baseline  # noqa: E402
from siim.demo.verdict import assess  # noqa: E402
from siim.evaluation.gtfree import loop_closure  # noqa: E402
from siim.geometry import estimate, warp  # noqa: E402
from siim.ingest import parse_image_structure, validate_structure  # noqa: E402
from siim.ingest.footprint import FrameCorners, TileWindow  # noqa: E402
from siim.ingest.ohrc import OhrcGrid, grid_matches_corners, parse_ohrc_label  # noqa: E402
from siim.ingest.orientation import north_up_east_right  # noqa: E402
from siim.preprocessing.degrade import degrade_to_gsd_strips  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_e7 = _load("_exp007", ROOT / "scripts" / "run_exp007.py")
_cen = _load("_census023", ROOT / "scripts" / "census_exp023.py")

STAGE = "EXP-023"
DATA = ROOT / "data"
OUT = ROOT / "experiments" / STAGE
RULE = _e7.N_INLIERS_FAILURE_RULE
BASE = {"model": "affine", "ransac_threshold_px": 3.0, "seed": 0}
ENGINES = {"b1": "B1", "b4l": "B4L"}
OHRC_GSD_NOMINAL_M = 0.26
PSF_FWHM_COARSE_PX = 1.0
WINDOW_MARGIN = 0.05
CORNER_QUANTISATION_M = 150.0
BILINEAR_TERM = 0.012
AGREEMENT_PX = 2.0
GRID_EXACT_DEG = 1e-5
INCIDENCE_GUARD_DEG = 0.5
MOON_R_M = 1737400.0
GEOM_GRID = 9
DENSE_STEP = 16


def md5_of(path: Path, chunk: int = 1 << 24) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def gc_m(a, b) -> float:
    lon1, lat1, lon2, lat2 = map(np.deg2rad, (a[0], a[1], b[0], b[1]))
    hv = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return float(2 * MOON_R_M * np.arcsin(np.sqrt(hv)))


# ---------------------------------------------------------------------------
# images
# ---------------------------------------------------------------------------
class Image:
    """An oriented coarse image and the exact map from its pixels to the frame."""

    def __init__(self, name, image, north_up, window: TileWindow, kind, meta):
        self.name, self.image, self.nu, self.window, self.kind, self.meta = name, image, north_up, window, kind, meta

    @property
    def shape(self):
        return self.image.shape

    def to_frame(self, xy: np.ndarray) -> np.ndarray:
        """Oriented (x, y) -> frame (line, sample)."""
        orig = self.nu.inverse.apply(np.asarray(xy, float))
        return np.array([self.window.to_frame(y, x) for x, y in orig])

    def from_frame(self, ls: np.ndarray) -> np.ndarray:
        """Frame (line, sample) -> oriented (x, y)."""
        rc = np.array([self.window.from_frame(line, s) for line, s in ls])
        return self.nu.forward.apply(rc[:, ::-1])


def nac_image(role: str, tile: dict, corners: FrameCorners, scaled_pixel_m: float) -> Image:
    raw = np.load(ROOT / tile["tile_npy"])
    k = int(tile["decimation"])
    img = _e7.stretch(_e7.decimate(np.asarray(raw, dtype=np.float64), k))
    del raw
    nu = north_up_east_right(img, corners, line=tile["line0"] + (tile["n_lines"] - 1) / 2,
                             sample=tile["sample0"] + (tile["n_samples"] - 1) / 2)
    w = TileWindow(tile["line0"], tile["sample0"], tile["n_lines"], tile["n_samples"], k)
    meta = {"pdsid": tile["pdsid"], "role": role, "decimation": k, "scaled_pixel_m": scaled_pixel_m,
            "coarse_gsd_m": k * scaled_pixel_m, "orientation": nu.record, "shape": list(nu.image.shape)}
    return Image(role, nu.image, nu, w, "NAC", meta)


class Ohrc:
    def __init__(self, obs: str):
        self.obs = obs
        self.label, self.grid, self.xml, self.grd = _cen.ohrc(obs)
        self.struct = parse_image_structure(self.xml.read_text(encoding="utf-8"))
        self.img_path = self.xml.with_name(self.struct.file_name)

    def memmap(self):
        s = self.struct
        return np.memmap(self.img_path, dtype=np.dtype(s.numpy_dtype), mode="r", offset=s.offset_bytes,
                         shape=(s.lines, s.samples))

    def window_for(self, na_tile: dict, na_corners: FrameCorners, shift_scans: int = 0) -> dict:
        """Part 1 section 2.1's window, built by the census's own function, so the
        census's overlap checks and the runner's cut are one computation."""
        return _cen.ohrc_window_box(self.grid, na_corners, na_tile, shift_scans=shift_scans,
                                    n=GEOM_GRID, margin=WINDOW_MARGIN)

    def image(self, name: str, box: dict, factor: int) -> Image:
        mm = self.memmap()
        cut = mm[box["scan0"]:box["scan1"], box["pixel0"]:box["pixel1"]]
        deg = degrade_to_gsd_strips(cut, factor, psf_fwhm_coarse_px=PSF_FWHM_COARSE_PX)
        del mm, cut
        img = _e7.stretch(deg)
        n_l, n_s = box["scan1"] - box["scan0"], box["pixel1"] - box["pixel0"]
        nu = north_up_east_right(img, self.label.corners("refined"), line=box["scan0"] + (n_l - 1) / 2,
                                 sample=box["pixel0"] + (n_s - 1) / 2)
        w = TileWindow(box["scan0"], box["pixel0"], n_l, n_s, factor)
        m_scan, m_pix = self.grid.metres_per_step(box["scan0"] + n_l / 2, box["pixel0"] + n_s / 2)
        meta = {"obs": self.obs, "box": box, "degrade_factor": factor,
                "coarse_gsd_m_nominal": factor * OHRC_GSD_NOMINAL_M,
                "native_m_per_scan_pixel_measured": [m_scan, m_pix],
                # the grid's own spacing, not the label's nominal 0.26 m (pre-run review)
                "coarse_gsd_m": factor * 0.5 * (m_scan + m_pix),
                "orientation": nu.record, "shape": list(nu.image.shape),
                "off_nadir_deg": self.label.off_nadir_deg}
        return Image(name, nu.image, nu, w, "OHRC", meta)


# ---------------------------------------------------------------------------
# matching, geometry, agreement
# ---------------------------------------------------------------------------
_CACHE: dict = {}


def match(engine: str, a: Image, b: Image) -> dict:
    key = (engine, a.name, b.name)
    if key in _CACHE:
        return _CACHE[key]
    t0 = time.perf_counter()
    res = run_baseline(ENGINES[engine], a.image, b.image, model=BASE["model"],
                       ransac_threshold=BASE["ransac_threshold_px"], seed=BASE["seed"])
    mask = np.asarray(res.inlier_mask, bool) if np.size(res.inlier_mask) else np.zeros(0, bool)
    n = int(mask.sum())
    row = {"engine": engine, "edge": f"{a.name} -> {b.name}", "src_shape": list(a.shape), "dst_shape": list(b.shape),
           "n_keypoints_src": int(len(res.src_features)), "n_keypoints_dst": int(len(res.dst_features)),
           "n_putative": int(res.matches.src_points.shape[0]), "n_inliers": n,
           "fit_rmse_px": float(res.ransac.inlier_rmse), "fit_rmse_is_not_accuracy": True,
           "pass": bool(n > RULE), "wall_s": round(time.perf_counter() - t0, 1),
           "transform_matrix": (np.asarray(res.transform.matrix).tolist() if res.transform is not None else None)}
    print(f"  {engine:4s} {row['edge']:24s} inliers {n:6d}  pass {row['pass']}  ({row['wall_s']}s)", flush=True)
    _CACHE[key] = {"row": row, "res": res, "mask": mask}
    return _CACHE[key]


def dense_points(shape, step=DENSE_STEP):
    ys, xs = np.mgrid[0:shape[0]:step, 0:shape[1]:step]
    return np.column_stack([xs.ravel(), ys.ravel()]).astype(float)


def inside(xy, shape):
    return (xy[:, 0] >= 0) & (xy[:, 0] <= shape[1] - 1) & (xy[:, 1] >= 0) & (xy[:, 1] <= shape[0] - 1)


def masked_disagreement(t_a, t_b, src_shape, dst_shape):
    """Median / p90 of |t_a(x) - t_b(x)| over source points t_b maps inside the destination."""
    pts = dense_points(src_shape)
    pa, pb = t_a.apply(pts), t_b.apply(pts)
    m = inside(pb, dst_shape)
    if not m.any():
        return None
    d = np.hypot(*(pa[m] - pb[m]).T)
    return {"median_px": float(np.median(d)), "p90_px": float(np.percentile(d, 90)),
            "n_points": int(m.sum()), "overlap_fraction_of_source": float(m.mean())}


def predicted_transform(src: Image, dst: Image, dst_corners: FrameCorners, lonlat_of_frame):
    """OHRC oriented px -> lon/lat (given geometry) -> NAC frame -> NAC oriented px, affine fit."""
    xs = np.linspace(0, src.shape[1] - 1, GEOM_GRID)
    ys = np.linspace(0, src.shape[0] - 1, GEOM_GRID)
    grid = np.array([(x, y) for y in ys for x in xs])
    frame = src.to_frame(grid)
    s_pts, d_ls = [], []
    for (x, y), (scan, pixel) in zip(grid, frame):
        lo, la = lonlat_of_frame(scan, pixel)
        try:
            line, samp = dst_corners.pixel_at(lo, la)
        except ValueError:
            continue
        s_pts.append((x, y))
        d_ls.append((line, samp))
    if len(s_pts) < 3:
        return None, len(s_pts)
    d_pts = dst.from_frame(np.array(d_ls))
    r = estimate(np.array(s_pts), d_pts, "affine")
    return (r.transform if r.ok else None), len(s_pts)


def geometry_check(edge: dict, src: Image, dst: Image, dst_corners: FrameCorners, oh: Ohrc) -> dict:
    t = edge["res"].transform
    gsd = dst.meta["coarse_gsd_m"]
    floor = CORNER_QUANTISATION_M / gsd + BILINEAR_TERM * np.hypot(*dst.shape) / 2
    out = {"floor_px": float(floor), "floor_m": float(floor * gsd),
           "floor_note": "150 m corner quantisation in NAC coarse px + 1.2 % bilinear term (REAL-DATA-09)"}
    for which, fn in (("refined_grid", lambda s, p: oh.grid.lonlat_at(s, p)),
                      ("system_level_corners", lambda s, p: oh.label.corners("system").lonlat_at(s, p))):
        P, n_nodes = predicted_transform(src, dst, dst_corners, fn)
        rec = {"n_grid_nodes": n_nodes}
        if P is not None and t is not None:
            d = masked_disagreement(t, P, src.shape, dst.shape)
            if d is None:
                pts = dense_points(src.shape)
                dd = np.hypot(*(t.apply(pts) - P.apply(pts)).T)
                d = {"median_px": float(np.median(dd)), "p90_px": float(np.percentile(dd, 90)),
                     "n_points": int(len(pts)), "overlap_fraction_of_source": 0.0,
                     "note": "the prediction maps no source point inside the destination; median over the whole source"}
            c = np.array([[(src.shape[1] - 1) / 2, (src.shape[0] - 1) / 2]])
            off = (t.apply(c) - P.apply(c))[0]
            rec.update(d, median_m=d["median_px"] * gsd,
                       centre_offset_px_xy=[float(off[0]), float(off[1])],
                       centre_offset_m_east_south=[float(off[0] * gsd), float(off[1] * gsd)],
                       predicted_matrix=np.asarray(P.matrix).tolist())
            if which == "refined_grid":
                rec["verdict"] = ("CONSISTENT" if d["median_px"] <= floor else
                                  "INCONSISTENT" if d["median_px"] > 3 * floor else "INCONCLUSIVE")
        out[which] = rec
    return out


def triangle(nodes: list[Image], nac_coarse_gsd_m: float) -> dict:
    """One loop. Part 1 section 2.3 names the residual 'in coarse NAC pixels'.
    The loop is evaluated over the first image's shape (REAL-DATA-09's
    convention), whose pixel is an OHRC coarse pixel (factor x the grid's own
    spacing) -- close to, not equal to, Na's coarse pixel. So the residual is
    reported in both units and the NAC-pixel value, the unit Part 1 froze, is
    what `assess()` receives. The conversion uses geometry (measured ground
    spacings), never the registration being judged."""
    a, b, c = nodes
    legs = [match("b1", a, b), match("b1", b, c), match("b1", c, a)]
    rec = {"cycle": [a.name, b.name, c.name, a.name], "legs": [lg["row"]["edge"] for lg in legs],
           "legs_n_inliers": [lg["row"]["n_inliers"] for lg in legs],
           "legs_pass": [lg["row"]["pass"] for lg in legs]}
    if all(lg["res"].transform is not None for lg in legs):
        r_first = float(loop_closure([lg["res"].transform for lg in legs], a.shape))
        ratio = a.meta["coarse_gsd_m"] / nac_coarse_gsd_m
        r = r_first * ratio
        rec.update(loop_residual_first_image_px=r_first, first_image=a.name,
                   first_image_px_in_nac_coarse_px=ratio,
                   loop_residual_px=r, loop_residual_unit="Na coarse px (Part 1 section 2.3)",
                   loop_residual_m=r_first * a.meta["coarse_gsd_m"])
        first = legs[0]
        v = assess(transform=first["res"].transform, src_points=first["res"].matches.src_points,
                   dst_points=first["res"].matches.dst_points, inlier_mask=first["mask"], shape=a.shape,
                   fit_rmse=float(first["res"].ransac.inlier_rmse), loop_error_px=r)
        v_first = assess(transform=first["res"].transform, src_points=first["res"].matches.src_points,
                         dst_points=first["res"].matches.dst_points, inlier_mask=first["mask"], shape=a.shape,
                         fit_rmse=float(first["res"].ransac.inlier_rmse), loop_error_px=r_first)
        rec["status_if_first_image_px"] = v_first.status
        rec["verdict_on_first_leg"] = v.as_dict()
        rec["status"] = v.status
    else:
        rec.update(loop_residual_px=None, status="NO LOOP (a leg produced no transform)")
    print(f"  triangle {'-'.join(rec['cycle'])}: loop {rec.get('loop_residual_px')}  -> {rec['status']}", flush=True)
    return rec


# ---------------------------------------------------------------------------
def main() -> None:
    out_path = OUT / "exp023_results.json"
    if out_path.exists():
        raise SystemExit(f"{out_path.relative_to(ROOT)} exists (integrity rule 4)")
    t_start = time.time()
    census = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
    man = json.loads((DATA / "manifests" / "exp023_manifest.json").read_text(encoding="utf-8"))
    geo = json.loads((DATA / "manifests" / "exp023_index_geometry.json").read_text(encoding="utf-8"))["products"]
    tiles = {t["role"]: t for t in man["tiles"]}
    cand = {c["pdsid"]: c for c in census["candidates"]}

    # ---------------- S0
    print("S0 harness")
    s0 = {"ohrc": {}, "nac": {}}
    ohrc = {k: Ohrc(k) for k in ("O1", "O2")}
    for k, oh in ohrc.items():
        st = oh.struct
        validate_structure(st)
        size = os.path.getsize(oh.img_path)
        ident = st.offset_bytes + st.lines * st.samples * np.dtype(st.numpy_dtype).itemsize
        md5 = md5_of(oh.img_path)
        sys_off = {c: gc_m(oh.label.system_corners[c], oh.label.refined_corners[c]) for c in oh.label.refined_corners}
        s0["ohrc"][k] = {
            "file": str(oh.img_path.relative_to(ROOT)).replace("\\", "/"),
            "md5": md5, "md5_label": oh.label.md5, "md5_match": md5 == oh.label.md5,
            "file_size": size, "size_identity": ident, "size_identity_exact": size == ident,
            "grid_vs_refined_max_deg": grid_matches_corners(oh.grid, oh.label.refined_corners),
            "grid_vs_system_max_deg": grid_matches_corners(oh.grid, oh.label.system_corners),
            "system_minus_refined_corner_m": sys_off,
            "sun": {"incidence_deg": oh.label.solar_incidence_deg, "azimuth_deg": oh.label.sun_azimuth_deg},
            "off_nadir_deg": oh.label.off_nadir_deg, "reference_data_used": oh.label.reference_data_used,
            "start_utc": oh.label.start_utc}
        print(f"  {k}: md5 {'OK' if md5 == oh.label.md5 else 'MISMATCH'}, size identity "
              f"{size == ident}, grid-refined {s0['ohrc'][k]['grid_vs_refined_max_deg']:.1e} deg", flush=True)
    for role, t in tiles.items():
        c = cand.get(t["pdsid"], {})
        s0["nac"][role] = {"pdsid": t["pdsid"], "bytes_sha256": t.get("bytes_sha256"),
                           "tile_exists": (ROOT / t["tile_npy"]).exists(),
                           "incidence_guard_difference_deg": (c.get("incidence_guard") or {}).get("difference_deg")}
    s0_i = all(v["md5_match"] and v["size_identity_exact"] for v in s0["ohrc"].values())
    s0_ii = all(v["grid_vs_refined_max_deg"] <= GRID_EXACT_DEG for v in s0["ohrc"].values())
    guarded = [v for r, v in s0["nac"].items() if r in ("Na", "Nb")]
    # never vacuously true: an empty set of chosen frames is "not applicable", recorded as None
    s0_iv = (all(abs(v["incidence_guard_difference_deg"] if v["incidence_guard_difference_deg"] is not None
                     else 99) <= INCIDENCE_GUARD_DEG for v in guarded) if guarded else None)
    s0_v = all(v["bytes_sha256"] and v["tile_exists"] for v in s0["nac"].values()) if s0["nac"] else None

    if "Na" not in tiles:
        # Part 1 section 3, S1 NOT MET: S2-S5 are NO DATA. S0's OHRC clauses are still recorded.
        s0_iii_nd = {}
        for k, oh in ohrc.items():
            s_t, p_t = oh.grid.pixel_at(*census["target_lon_lat"])
            nu = north_up_east_right(np.zeros((8, 8)), oh.label.corners("refined"), line=s_t, sample=p_t)
            s0_iii_nd[k] = nu.record
        doc = {"stage": STAGE, "preregistration": "docs/stages/EXP-023_ohrc_nac_chandrayaan3_site.md Part 1 (d273b8e)",
               "target_lon_lat": census["target_lon_lat"],
               "criteria": {
                   "S0": {"met": bool(s0_i and s0_ii), "i_md5_structure": s0_i, "ii_grid_is_refined": s0_ii,
                          "iii_orientation": s0_iii_nd, "iv_incidence_guard": "NOT APPLICABLE (no frame chosen)",
                          "v_nac_bytes": "NOT APPLICABLE (no frame fetched)", "detail": s0},
                   "S1": {"met": False, "funnel": census["funnel"], "reads": "no admissible NAC frame"},
                   **{k: {"met": None, "reads": "NO DATA (S1 NOT MET)"} for k in ("S2", "S3", "S4", "S5")}},
               "environment": {"python": sys.version.split()[0], "numpy": np.__version__,
                               "platform": platform.platform()},
               "total_runtime_s": round(time.time() - t_start, 1)}
        OUT.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, indent=2, default=float), encoding="utf-8")
        print(f"S1 NOT MET -- NO DATA for S2-S5; S0 {doc['criteria']['S0']['met']}\n-> {out_path.relative_to(ROOT)}")
        return

    # ---------------- images
    print("\nimages")
    nac_corners = {r: _cen.corners_from_fields(t["pdsid"], geo[t["pdsid"]]["fields"],
                                               (ROOT / t["label_path"]).read_text(encoding="utf-8"))
                   for r, t in tiles.items()}

    def spm(pdsid):
        f = geo[pdsid]["fields"]
        return 0.5 * (float(f["SCALED_PIXEL_WIDTH"]) + float(f["SCALED_PIXEL_HEIGHT"]))

    imgs: dict = {}
    for r, t in tiles.items():
        imgs[r] = nac_image(r, t, nac_corners[r], spm(t["pdsid"]))
        print(f"  {r} {t['pdsid']}: {imgs[r].shape} at {imgs[r].meta['coarse_gsd_m']:.3f} m", flush=True)
    na = imgs["Na"]
    factor = int(round(na.meta["coarse_gsd_m"] / OHRC_GSD_NOMINAL_M))
    boxes = {}
    for k, oh in ohrc.items():
        boxes[k] = oh.window_for(tiles["Na"], nac_corners["Na"])
        imgs[k] = oh.image(k, boxes[k], factor)
        print(f"  {k}: scans [{boxes[k]['scan0']}, {boxes[k]['scan1']}) pixels [{boxes[k]['pixel0']}, "
              f"{boxes[k]['pixel1']}) -> {imgs[k].shape} (factor {factor})", flush=True)
    s0_iii = {k: imgs[k].meta["orientation"] for k in ("O1", "O2")}

    # ---------------- S2 edges + geometry
    print("\nS2 edges")
    edges = {}
    for k in ("O1", "O2"):
        e = match("b1", imgs[k], na)
        e["row"]["geometry"] = geometry_check(e, imgs[k], na, nac_corners["Na"], ohrc[k])
        edges[f"{k}->Na"] = e["row"]
        if "Nb" in imgs:
            e2 = match("b1", imgs[k], imgs["Nb"])
            e2["row"]["geometry"] = geometry_check(e2, imgs[k], imgs["Nb"], nac_corners["Nb"], ohrc[k])
            edges[f"{k}->Nb"] = e2["row"]
    s2_rows = [edges["O1->Na"], edges["O2->Na"]]
    s2_met = all(r["pass"] and r["geometry"]["refined_grid"].get("verdict") == "CONSISTENT" for r in s2_rows)

    # ---------------- S3 triangles
    print("\nS3 triangles")
    prim_names = census["primary_triangle"]
    tri_defs = {"O1-Na-Nb": ["O1", "Na", "Nb"], "O1-Na-O2": ["O1", "Na", "O2"],
                "O1-Nb-O2": ["O1", "Nb", "O2"], "O2-Na-Nb": ["O2", "Na", "Nb"]}
    tris = {}
    for name, nodes in tri_defs.items():
        if all(n in imgs for n in nodes):
            tris[name] = triangle([imgs[n] for n in nodes], na.meta["coarse_gsd_m"])
    prim_key = "O1-Na-Nb" if prim_names == ["O1", "Na", "Nb"] else "O1-Na-O2"
    prim = tris.get(prim_key)
    s3_met = bool(prim and all(prim["legs_pass"]) and prim["status"] == "VERIFIED")

    # ---------------- stereo edge (reported)
    print("\nOHRC stereo edge (reported only)")
    stereo = match("b1", imgs["O1"], imgs["O2"])["row"]

    # ---------------- S4 nulls
    print("\nS4 nulls")
    nulls = {}
    na_plan = census["nulls"].get("N-a", {})
    if "N-a" in imgs and na_plan.get("non_overlap_confirmed") is True:
        nulls["N-a"] = dict(match("b1", imgs["O1"], imgs["N-a"])["row"], census=na_plan)
    else:
        nulls["N-a"] = {"status": "NOT PLACED by the census (or non-overlap unconfirmed)", "census": na_plan}
    nb_plan = census["nulls"].get("N-b", {})
    if nb_plan.get("non_overlap_confirmed") is True:
        box = ohrc["O1"].window_for(tiles["Na"], nac_corners["Na"], shift_scans=int(nb_plan["displacement_scans"]))
        if {k: box[k] for k in ("scan0", "scan1", "pixel0", "pixel1")} != \
                {k: nb_plan["box"][k] for k in ("scan0", "scan1", "pixel0", "pixel1")}:
            raise SystemExit("N-b box differs from the census's -- the non-overlap check does not describe it")
        imgs["O1-null"] = ohrc["O1"].image("O1-null", box, factor)
        nulls["N-b"] = dict(match("b1", imgs["O1-null"], na)["row"], box=box, census=nb_plan)
    else:
        nulls["N-b"] = {"status": "NOT PLACED by the census (or non-overlap unconfirmed)", "census": nb_plan}
    placed = [v for v in nulls.values() if "n_inliers" in v]
    s4_met = (len(placed) == 2 and all(not v["pass"] for v in placed)) if placed else None

    # ---------------- S5 B4L
    print("\nS5 B4L")
    s5_rows = {}
    for k in ("O1", "O2"):
        b4 = match("b4l", imgs[k], na)
        b1 = match("b1", imgs[k], na)
        agree = (masked_disagreement(b4["res"].transform, b1["res"].transform, imgs[k].shape, na.shape)
                 if b4["res"].transform is not None and b1["res"].transform is not None else None)
        s5_rows[f"{k}->Na"] = dict(b4["row"], agreement_with_b1=agree)
    s5_met = all(r["pass"] and r["agreement_with_b1"] and r["agreement_with_b1"]["median_px"] < AGREEMENT_PX
                 for r in s5_rows.values())

    # ---------------- descriptive
    desc = {"scale": {"ohrc_nominal_m": OHRC_GSD_NOMINAL_M, "degrade_factor": factor,
                      "nac_coarse_gsd_m": na.meta["coarse_gsd_m"], "nac_native_m": na.meta["scaled_pixel_m"],
                      "ohrc_to_nac_native_ratio": na.meta["scaled_pixel_m"] / OHRC_GSD_NOMINAL_M,
                      "ohrc_to_nac_coarse_ratio": na.meta["coarse_gsd_m"] / OHRC_GSD_NOMINAL_M},
            "viewing": {r: {"emission_deg": cand.get(t["pdsid"], {}).get("index_emission_deg")} for r, t in tiles.items()},
            "sun": {r: {k2: cand.get(t["pdsid"], {}).get(k2) for k2 in ("incidence_at_target_deg", "azimuth_at_target_deg",
                                                                         "sun_separation_deg", "start_time")}
                    for r, t in tiles.items()}}
    for k in ("O1", "O2"):
        desc["viewing"][k] = {"off_nadir_deg": ohrc[k].label.off_nadir_deg}

    crit = {
        "S0": {"met": bool(s0_i and s0_ii and s0_iv and s0_v), "i_md5_structure": s0_i, "ii_grid_is_refined": s0_ii,
               "iii_orientation": s0_iii, "iv_incidence_guard": s0_iv, "v_nac_bytes": s0_v, "detail": s0},
        "S1": {"met": True, "roles": census["roles"], "primary_triangle": prim_names,
               "note": "the runner only runs when the census found Na; S1's funnel is in census.json"},
        "S2": {"met": bool(s2_met), "edges": {k: v for k, v in edges.items()}},
        "S3": {"met": s3_met, "primary": prim_key, "primary_triangle": prim, "all_triangles": tris},
        "S4": {"met": s4_met, "nulls": nulls},
        "S5": {"met": bool(s5_met), "rows": s5_rows, "floor_px": AGREEMENT_PX},
    }
    doc = {"stage": STAGE, "preregistration": "docs/stages/EXP-023_ohrc_nac_chandrayaan3_site.md Part 1 (d273b8e)",
           "target_lon_lat": census["target_lon_lat"], "base": BASE, "engines": ENGINES,
           "images": {k: v.meta for k, v in imgs.items()}, "criteria": crit, "ohrc_stereo_edge": stereo,
           "descriptive": desc,
           "claims_not_supported": [
               "accuracy: no check point independent of LRO exists at this site; OHRC's refined geometry was tied to LRO",
               "gauge-free verification: loop closure is invariant to per-image gauge (E-039); O1's distortion cancels",
               "illumination invariance: illumination is matched by design",
               "any second site or terrain"],
           "environment": {"python": sys.version.split()[0], "numpy": np.__version__, "platform": platform.platform()},
           "total_runtime_s": round(time.time() - t_start, 1)}
    OUT.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, default=float), encoding="utf-8")
    print(f"\nS0 {crit['S0']['met']} | S2 {crit['S2']['met']} | S3 {crit['S3']['met']} "
          f"({prim_key}: {prim and prim.get('status')}, loop {prim and prim.get('loop_residual_px')}) | "
          f"S4 {crit['S4']['met']} | S5 {crit['S5']['met']}\n-> {out_path.relative_to(ROOT)} "
          f"({doc['total_runtime_s']} s)")

    # quicklook, after the measurement is persisted (E-031)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        e = _CACHE[("b1", "O1", "Na")]
        fig, ax = plt.subplots(1, 3, figsize=(15, 6))
        ax[0].imshow(imgs["O1"].image, cmap="gray")
        ax[0].set_title(f"OHRC obs1, degraded x{factor}, north up")
        ax[1].imshow(na.image, cmap="gray")
        ax[1].set_title(f"NAC {tiles['Na']['pdsid']}, north up")
        if e["res"].transform is not None:
            wimg, valid = warp(imgs["O1"].image, e["res"].transform, out_shape=na.shape, order=1)
            yy, xx = np.mgrid[0:na.shape[0], 0:na.shape[1]]
            chk = ((yy // 128 + xx // 128) % 2).astype(bool)
            comp = np.where(chk & valid, np.nan_to_num(wimg), na.image)
            ax[2].imshow(comp, cmap="gray")
            ax[2].set_title("checkerboard: OHRC registered into NAC")
        for a in ax:
            a.axis("off")
        fig.tight_layout()
        fig.savefig(OUT / "exp023_quicklook.png", dpi=110)
    except Exception as exc:  # noqa: BLE001 -- a figure may fail; the measurement is already written
        print(f"quicklook not written: {exc}")


if __name__ == "__main__":
    main()
