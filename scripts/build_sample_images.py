"""Build ``sample_images/``: real lunar images a reviewer can drop into the live card.

    python scripts/build_sample_images.py            # public-domain / credited sets
    python scripts/build_sample_images.py --force    # rebuild (overwrites sample_images/)

Every file is cut from a product this repository already holds, by a rule
written here, and carries its provenance in ``sample_images/manifest.json``:
product ID, tile window, decimation, orientation applied, the linear map from
the stored 16-bit value back to reflectance, the SHA-256 of the file, and the
credit line its producer asks for.

**Every expected result is measured, not asserted.** After writing the files,
the script posts them -- the exact bytes on disk -- to the demo's own
``/api/register`` and ``/api/register-triplet`` endpoints through FastAPI's
test client, i.e. the code path a reviewer's browser hits, and records what
came back (status, confidence, inliers, loop residual). The scenario README a
reviewer reads is generated from that record. A test re-reads the manifest and
checks the files' digests, so the folder cannot drift from what it claims.

Images are exported **north-up, east-right** (``siim.ingest.orientation``),
because the live card does not re-orient uploads and a map-like product is
what a scientist would hand it. NAC tiles are exported at decimation 4
(~4 m, 1024 x 512 px), so the live card uses them without further
down-sampling.

**Chandrayaan-2 pixels are never committed.** PRADAN products are "(c) reserved
ISRO"; the Chandrayaan-2 scenario is generated locally into
``sample_images/_local_chandrayaan2/`` (gitignored) only when the products
are on disk, with the ISSDC acknowledgement written beside it.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.ingest.mapgrid import load_map_block  # noqa: E402
from siim.ingest.orientation import north_up_east_right  # noqa: E402

OUT = ROOT / "sample_images"
LOCAL = OUT / "_local_chandrayaan2"
K_NAC = 4
KAGUYA_MARGIN_PX = 40

CREDIT_NAC = ("LRO NAC (LROC CDR), NASA/GSFC/Arizona State University. Tile window cut by "
              "SIIM from the archive product named in `product`.")
CREDIT_KAGUYA = ("SELENE (Kaguya) Terrain Camera Ortho Map Seamless V2.0, (c) JAXA/SELENE, "
                 "produced by LISM, distributed by JAXA/ISAS DARTS.")
CREDIT_C2 = ("Chandrayaan-2 data courtesy ISRO/ISSDC (PRADAN); (c) reserved ISRO. "
             "Generated locally for evaluation; not redistributed.")


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_e7 = _load("_exp007", "scripts/run_exp007.py")
_rd7 = _load("_rd07", "scripts/run_real_data_07.py")


# ---------------------------------------------------------------------------
# frame loading
# ---------------------------------------------------------------------------
def _contexts() -> dict:
    """window -> {pdsid: FrameContext} for the RD-07 windows and EXP-018's."""
    out = {}
    products = _rd7.load_products()
    for window, mname in _rd7.WINDOWS.items():
        man = json.loads((ROOT / "data" / "manifests" / mname).read_text(encoding="utf-8"))
        target = tuple(man["target_ground_point_lon_lat"])
        out[window] = {t["pdsid"]: _e7.FrameContext(t["pdsid"], t, products, target)
                       for t in man["tiles"]}
    man = json.loads((ROOT / "data/manifests/exp018_tranquillitatis_manifest.json")
                     .read_text(encoding="utf-8"))
    prods = json.loads((ROOT / "data/manifests/exp018_tranquillitatis_index_geometry.json")
                       .read_text(encoding="utf-8"))["products"]
    target = tuple(man["target_ground_point_lon_lat"])
    out["TRANQ"] = {t["pdsid"]: _e7.FrameContext(t["pdsid"], t, prods, target)
                    for t in man["tiles"]}
    return out


def nac_image(ctx) -> tuple[np.ndarray, dict]:
    """Reflectance (I/F) at decimation K_NAC, north-up east-right."""
    t = ctx.tile
    dn = _e7.decimate(ctx.raw().astype(np.float64), K_NAC)
    iof = dn * float(t["scaling_factor"])
    nu = north_up_east_right(iof, ctx.corners,
                             line=t["line0"] + (t["n_lines"] - 1) / 2,
                             sample=t["sample0"] + (t["n_samples"] - 1) / 2)
    ctx.release()
    meta = {"product": ctx.pdsid, "instrument": "LRO NAC",
            "tile_window": {"line0": t["line0"], "sample0": t["sample0"],
                            "n_lines": t["n_lines"], "n_samples": t["n_samples"]},
            "decimation": K_NAC,
            "gsd_m": round(K_NAC * ctx.scaled_pixel_m, 3),
            "incidence_deg": ctx.incidence_published,
            "orientation": nu.record,
            "credit": CREDIT_NAC}
    return nu.image, meta


def kaguya_crop(ctx, manifest: str, *, centred: bool = False) -> tuple[np.ndarray, dict]:
    """The Kaguya TC block under a NAC tile's footprint (plus margin), or, with
    ``centred``, a crop of the same size from the centre of the block -- used on
    the null block, which shares no ground with the tile."""
    blk = load_map_block(manifest)
    t = ctx.tile
    l0, s0 = t["line0"], t["sample0"]
    l1, s1 = l0 + t["n_lines"] - 1, s0 + t["n_samples"] - 1
    ll = np.array([ctx.corners.lonlat_at(float(a), float(b))
                   for a, b in ((l0, s0), (l0, s1), (l1, s1), (l1, s0))], float)
    xy = blk.block_xy_of_lonlat(ll[:, 0], ll[:, 1])
    x0 = int(np.floor(xy[:, 0].min())) - KAGUYA_MARGIN_PX
    y0 = int(np.floor(xy[:, 1].min())) - KAGUYA_MARGIN_PX
    x1 = int(np.ceil(xy[:, 0].max())) + KAGUYA_MARGIN_PX
    y1 = int(np.ceil(xy[:, 1].max())) + KAGUYA_MARGIN_PX
    H, W = blk.data.shape
    if centred:
        h, w = y1 - y0, x1 - x0
        y0 = max(0, (H - h) // 2)
        x0 = max(0, (W - w) // 2)
        y1, x1 = y0 + h, x0 + w
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    crop = np.asarray(blk.data[y0:y1, x0:x1], np.float64)
    man = json.loads((ROOT / "data" / "manifests" / manifest).read_text(encoding="utf-8"))
    meta = {"product": man["product"], "instrument": "SELENE (Kaguya) TC Ortho Map Seamless V2.0",
            "block_manifest": f"data/manifests/{manifest}",
            "block_crop_rows_cols": [y0, y1, x0, x1],
            "gsd_m": round(float(man["grid"]["map_scale_m"]), 3),
            "photometry": "normalised to i = 30 deg, e = 0 deg, alpha = 30 deg",
            "orientation": "map projection (simple cylindrical): north up, east right",
            "credit": CREDIT_KAGUYA}
    return crop, meta


# ---------------------------------------------------------------------------
# writing
# ---------------------------------------------------------------------------
def write_png16(path: Path, img: np.ndarray, meta: dict) -> dict:
    from PIL import Image
    v = img[np.isfinite(img)]
    lo, hi = (float(x) for x in np.percentile(v, [0.1, 99.9]))
    scale = (hi - lo) / 65535.0 if hi > lo else 1.0
    q = np.clip(np.round((np.nan_to_num(img, nan=lo) - lo) / scale), 0, 65535).astype(np.uint16)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(q).save(path, optimize=True)
    raw = path.read_bytes()
    return dict(meta, file=path.name, shape=list(q.shape), bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
                stored_value_to_reflectance={"reflectance = value * scale + offset": True,
                                             "scale": scale, "offset": lo,
                                             "clipped_at_percentiles": [0.1, 99.9]})


# ---------------------------------------------------------------------------
# live verification through the demo's own endpoints
# ---------------------------------------------------------------------------
def _client():
    from fastapi.testclient import TestClient

    from siim.demo.api import app
    return TestClient(app)


def _b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode("ascii")


def live_pair(client, src: Path, ref: Path, engine: str = "B1") -> dict:
    t0 = time.perf_counter()
    r = client.post("/api/register", json={"source_png": _b64(src), "reference_png": _b64(ref),
                                           "engine": engine})
    r.raise_for_status()
    d = r.json()
    return {"endpoint": "/api/register", "engine": engine,
            "status": d["verdict"]["status"], "confidence": d["verdict"]["confidence"],
            "n_inliers": d["summary"].get("n_inliers"),
            "registered_image_emitted": d["registered_png"] is not None,
            "reasons": d["verdict"]["reasons"][:3],
            "wall_s": round(time.perf_counter() - t0, 2)}


def live_triplet(client, a: Path, b: Path, c: Path, engine: str = "B1") -> dict:
    t0 = time.perf_counter()
    r = client.post("/api/register-triplet", json={"a_png": _b64(a), "b_png": _b64(b),
                                                   "c_png": _b64(c), "engine": engine})
    r.raise_for_status()
    d = r.json()
    return {"endpoint": "/api/register-triplet", "engine": engine,
            "status": d["verdict"]["status"], "confidence": d["verdict"]["confidence"],
            "loop_error_px": d["loop_error_px"],
            "edges": [{"edge": e["edge"], "n_inliers": e["n_inliers"], "pass": e["pass"]}
                      for e in d["edges"]],
            "reasons": d["verdict"]["reasons"][:3],
            "wall_s": round(time.perf_counter() - t0, 2)}


# ---------------------------------------------------------------------------
# scenarios
# ---------------------------------------------------------------------------
SCENARIOS = [
    {"id": "01_pair_registers_small_sun_change", "kind": "pair",
     "title": "Same ground, small Sun change: the pair registers",
     "why": "Two LRO NAC frames of Mare Serenitatis 11.7 deg apart in incidence. The pair path "
            "cannot exceed INCONCLUSIVE on its own, and says why: loop closure needs a third image.",
     "images": [("RD04", "nac.m1299958135lc", "A_source_nac_i18.png"),
                ("RD04", "nac.m1271742202lc", "B_reference_nac_i30.png")],
     "recorded": "REAL-DATA-07 rows_rd04_nue.json, B1: 1608 inliers on this edge"},
    {"id": "02_triplet_reaches_VERIFIED", "kind": "triplet",
     "title": "Three overlapping frames: the only path on the page to VERIFIED",
     "why": "Upload all three (image A, B and the optional third). The three edges are estimated "
            "independently and composed around the loop; VERIFIED is returned only when the loop "
            "closes under the frozen 2.0 px line.",
     "images": [("RD04", "nac.m1299958135lc", "A_nac_i18.png"),
                ("RD04", "nac.m1315225542lc", "B_nac_i21.png"),
                ("RD04", "nac.m1271742202lc", "C_nac_i30.png")],
     "recorded": "EXP-012 primary triplet R4-6 (VERIFIED on all three edges)"},
    {"id": "03_illumination_refusal", "kind": "pair",
     "title": "39.8 deg of Sun change: the verdict refuses, and draws nothing",
     "why": "The same ground at incidence 29.95 deg and 69.76 deg. Long shadows change what the "
            "surface looks like; the system must say REJECTED and withhold the registered image "
            "rather than draw a plausible-looking wrong alignment.",
     "images": [("RD04", "nac.m1271742202lc", "A_source_nac_i30.png"),
                ("RD04", "nac.m1335207975rc", "B_reference_nac_i70.png")],
     "recorded": "REAL-DATA-07: 0 of 3 engines register this pair; EXP-021 labels B1's estimate "
                 "WRONG by 145-356 m on the related RD04 edges into this frame"},
    {"id": "04_held_out_site_triplet", "kind": "triplet",
     "title": "Held-out ground (Mare Tranquillitatis): VERIFIED on a site no threshold was tuned on",
     "why": "Frames from EXP-018's blind-validation window, ~800 km from the development site. "
            "Upload as A, B and the third image.",
     "images": [("TRANQ", "nac.m1121081627rc", "A_nac_i40.png"),
                ("TRANQ", "nac.m1177606647lc", "B_nac_i16.png"),
                ("TRANQ", "nac.m1447850428rc", "C_nac_i11.png")],
     "recorded": "EXP-018 triangle, loop 1.112 px, VERIFIED on all three edges"},
    {"id": "05_cross_mission_nasa_to_jaxa", "kind": "pair_kaguya",
     "title": "Cross-mission: an LRO NAC frame onto a Kaguya (JAXA) ortho map",
     "why": "Different agency, spacecraft, camera and decade; the Kaguya map is controlled by "
            "its own network and photometrically normalised. The pixel-size ratio between the "
            "two uploads is about 2:1 after the card's own down-sampling.",
     "images": [("RD04", "nac.m1212932972lc", "A_source_nac_i45.png")],
     "kaguya": ("exp019_tc_ortho_ref_block.json", "B_reference_kaguya_tc_8m.png", False),
     "recorded": "EXP-019 arm R: this tile registers to the reference with 474 inliers (B1)"},
    {"id": "06_unrelated_ground_must_refuse", "kind": "pair_kaguya",
     "title": "Wrong ground on purpose: the system must refuse",
     "why": "The same NAC frame against a Kaguya crop at least 25 km away. There is no correct "
            "answer, so any pass would be a false acceptance.",
     "images": [("RD04", "nac.m1212932972lc", "A_source_nac.png")],
     "kaguya": ("exp019_tc_ortho_null_block.json", "B_unrelated_kaguya_25km_away.png", True),
     "recorded": "EXP-019 arm N: 0 of 21 null cells pass; EXP-021 validation null: 0 of 7"},
]


def build(force: bool) -> None:
    if OUT.exists() and any(p.name != "_local_chandrayaan2" for p in OUT.iterdir()):
        if not force:
            raise SystemExit(f"{OUT} exists; pass --force to rebuild")
        for p in OUT.iterdir():
            if p.name != "_local_chandrayaan2":
                shutil.rmtree(p) if p.is_dir() else p.unlink()
    OUT.mkdir(exist_ok=True)
    ctxs = _contexts()
    client = _client()
    manifest = {"built_by": "scripts/build_sample_images.py",
                "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "note": ("expected results are measured by posting these exact files to the demo's "
                         "own endpoints; they are live runs, not recorded stage numbers"),
                "scenarios": []}
    for sc in SCENARIOS:
        d = OUT / sc["id"]
        files = []
        for window, pdsid, fname in sc["images"]:
            img, meta = nac_image(ctxs[window][pdsid])
            files.append(write_png16(d / fname, img, dict(meta, window=window)))
        if "kaguya" in sc:
            man, fname, centred = sc["kaguya"]
            window, pdsid, _ = sc["images"][0]
            ctx = _contexts()[window][pdsid]           # fresh context: corners only
            img, meta = kaguya_crop(ctx, man, centred=centred)
            files.append(write_png16(d / fname, img, meta))
        paths = [d / f["file"] for f in files]
        if sc["kind"] == "triplet":
            live = live_triplet(client, *paths)
        else:
            live = live_pair(client, paths[0], paths[1])
        rec = {k: sc[k] for k in ("id", "kind", "title", "why", "recorded")}
        rec.update({"files": files, "live_check": live})
        manifest["scenarios"].append(rec)
        (d / "README.md").write_text(_readme(rec), encoding="utf-8")
        print(f"{sc['id']:40s} -> {live['status']} / {live['confidence']} "
              f"({live.get('n_inliers', live.get('loop_error_px'))})", flush=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (OUT / "README.md").write_text(_index(manifest), encoding="utf-8")
    build_local_c2(client)


def build_local_c2(client) -> None:
    """Chandrayaan-2 TMC-2 ortho vs NAC, locally only (gitignored).

    Built the way REAL-DATA-09 P1 built its passing RD03-long pair: the NAC
    long tile degraded (PSF-aware, x3) to ~5.6 m and oriented north-up; the
    TMC-2 ortho cut at its native ~4.7 m to the footprint of a central NAC
    crop, through P1's RECORDED transform (TMC crop px -> NAC px). Both files
    stay under the live card's 1024 px cap so it applies no further
    down-sampling.
    """
    from siim.geometry import Transform
    from siim.ingest.geotiff import decode_window
    from siim.preprocessing.degrade import degrade_to_gsd
    _rd9 = _load("_rd09b", "scripts/run_real_data_09.py")
    try:
        row = next(r for r in json.loads((ROOT / "experiments/REAL-DATA-09/"
                                          "real_data_09_results_b1.json").read_text(encoding="utf-8"))["rows"]
                   if r.get("pass") and r.get("window") == "RD03-long"
                   and r.get("frame") == "nac.m1271742202lc")
        rec_p = _rd9.tmc_products()["TMC-2:ortho"]
        tif = ROOT / rec_p["data_file"].replace("\\", "/")
        if not tif.exists():
            raise FileNotFoundError(tif)
    except Exception as exc:  # noqa: BLE001 -- absent products are a skip, not a failure
        print(f"Chandrayaan-2 scenario skipped: {type(exc).__name__}: {exc}", flush=True)
        return
    man = json.loads((ROOT / "data/manifests/exp007_long_triplet_abc_manifest.json")
                     .read_text(encoding="utf-8"))
    tile = next(t for t in man["tiles"] if t["pdsid"] == "nac.m1271742202lc")
    ctx = _e7.FrameContext(tile["pdsid"], tile, _rd9.load_nac_products(),
                           tuple(man["target_ground_point_lon_lat"]))
    k = tile.get("decimation", 2)
    factor = int(row["degrade_factor"])
    iof = _e7.decimate(ctx.raw().astype(np.float64), k) * float(tile["scaling_factor"])
    deg = degrade_to_gsd(iof, factor, psf_fwhm_coarse_px=1.0)
    nu = north_up_east_right(deg, ctx.corners, line=tile["line0"] + (tile["n_lines"] - 1) / 2,
                             sample=tile["sample0"] + (tile["n_samples"] - 1) / 2)
    nac = nu.image
    H = nac.shape[0]
    n_rows = 860
    r0 = (H - n_rows) // 2
    nac_crop = nac[r0:r0 + n_rows]
    T = Transform(np.asarray(row["transform_matrix"], float), "affine")   # TMC crop px -> NAC px
    h, w = nac_crop.shape
    corners = np.array([[0, r0], [w - 1, r0], [w - 1, r0 + h - 1], [0, r0 + h - 1]], float)
    tc = T.inverse().apply(corners)
    bx0, by0, bx1, by1 = row["tmc2_block"]
    cx0 = bx0 + max(0, int(np.floor(tc[:, 0].min())))
    cy0 = by0 + max(0, int(np.floor(tc[:, 1].min())))
    cx1 = min(bx1, bx0 + int(np.ceil(tc[:, 0].max())) + 1)
    cy1 = min(by1, by0 + int(np.ceil(tc[:, 1].max())) + 1)
    tmc = decode_window(tif, cy0, cy1, cx0, cx1).astype(np.float64)
    tmc = np.where(tmc > 0, tmc, np.nan)
    LOCAL.mkdir(parents=True, exist_ok=True)
    f_tmc = write_png16(LOCAL / "A_source_chandrayaan2_tmc2_ortho.png", tmc,
                        {"product": str(rec_p.get("product_id", "TMC-2 L2 ortho")),
                         "instrument": "Chandrayaan-2 TMC-2 (L2 ortho, native pixels)",
                         "window_x0_y0_x1_y1": [cx0, cy0, cx1, cy1],
                         "gsd_m": round(float(row["tmc2_gsd_m"]), 3),
                         "valid_fraction": round(float(np.isfinite(tmc).mean()), 3),
                         "orientation": "map projection: north up, east right",
                         "credit": CREDIT_C2})
    f_nac = write_png16(LOCAL / "B_reference_lro_nac_5m.png", nac_crop,
                        {"product": tile["pdsid"], "instrument": "LRO NAC",
                         "tile_window": {"line0": tile["line0"], "sample0": tile["sample0"],
                                         "n_lines": tile["n_lines"], "n_samples": tile["n_samples"]},
                         "decimation": k, "degrade_factor_psf": factor,
                         "gsd_m": round(float(row["nac_effective_gsd_m"]), 3),
                         "incidence_deg": ctx.incidence_published,
                         "orientation": nu.record, "north_up_row_crop": [r0, r0 + n_rows],
                         "credit": CREDIT_NAC})
    ctx.release()
    live = live_pair(client, LOCAL / f_tmc["file"], LOCAL / f_nac["file"])
    rec = {"id": "_local_chandrayaan2", "title": "Chandrayaan-2 TMC-2 onto LRO NAC (local only)",
           "why": "ISRO onto NASA, 4.7 m onto 5.6 m. Generated from your own PRADAN download; "
                  "not redistributed.",
           "recorded": "REAL-DATA-09 P1, RD03-long, B1: 57 inliers, geometry CONSISTENT",
           "files": [f_tmc, f_nac], "live_check": live}
    (LOCAL / "manifest.json").write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    (LOCAL / "README.md").write_text(_readme(rec) + "\n" + CREDIT_C2 + "\n", encoding="utf-8")
    print(f"_local_chandrayaan2 -> {live['status']} / {live['confidence']} "
          f"({live.get('n_inliers')})", flush=True)


# ---------------------------------------------------------------------------
# READMEs, generated from the record
# ---------------------------------------------------------------------------
def _readme(rec: dict) -> str:
    live = rec["live_check"]
    lines = [f"# {rec['title']}", "", rec["why"], "", "## Files", ""]
    for f in rec["files"]:
        lines.append(f"- `{f['file']}` — {f['instrument']}, `{f['product']}`, "
                     f"{f['shape'][1]} × {f['shape'][0]} px, ~{f['gsd_m']} m/px"
                     + (f", incidence {f['incidence_deg']}°" if f.get("incidence_deg") else ""))
    lines += ["", "## How to use it", ""]
    if live["endpoint"].endswith("triplet"):
        lines.append("Open the live card, drop the files in order into **A**, **B** and the "
                     "optional **third image**, keep engine **B1**, and run.")
    else:
        lines.append("Open the live card, drop `A_*` as the source and `B_*` as the reference, "
                     "keep engine **B1**, and run.")
    lines += ["", "## What the live card returned on these exact files", "",
              f"**{live['status']} / {live['confidence']}**"
              + (f" — {live['n_inliers']} inliers" if live.get("n_inliers") is not None else "")
              + (f" — loop closure {live['loop_error_px']:.3f} px"
                 if live.get("loop_error_px") is not None else ""), ""]
    if "registered_image_emitted" in live:
        lines.append(f"Registered image emitted: **{'yes' if live['registered_image_emitted'] else 'no'}**.")
        lines.append("")
    for r in live["reasons"]:
        lines.append(f"> {r}")
        lines.append("")
    lines += [f"Recorded stage evidence for the same ground: {rec['recorded']}.", "",
              "This is a **live** result, measured by `scripts/build_sample_images.py` "
              "through the demo's own endpoint. It is not a recorded stage number, and "
              "VERIFIED means *corroborated by the named evidence*, never *correct*.", ""]
    return "\n".join(lines)


def _index(man: dict) -> str:
    rows = "\n".join(
        f"| [`{s['id']}`]({s['id']}/README.md) | {s['title']} | "
        f"**{s['live_check']['status']}** / {s['live_check']['confidence']} |"
        for s in man["scenarios"])
    return f"""# Real lunar sample images for the live card

Real images from real archives, cut by `scripts/build_sample_images.py` and
ready to drop into the demo's live registration card
(`python scripts/run_demo.py --port 8017 --strict-port`, then the **Live** card).

| scenario | what it shows | what the live card returned |
|---|---|---|
{rows}

Every result in the right-hand column was produced by posting these exact
files to the demo's own endpoint when the folder was built
(`manifest.json` → `live_check`). The files are **16-bit PNG**, north-up and
east-right. `manifest.json` records, per file, the product, the tile window,
the decimation, the orientation applied, the SHA-256 and the linear map from
the stored value back to reflectance.

**Credits.** LRO NAC: NASA/GSFC/Arizona State University. SELENE (Kaguya) TC:
(c) JAXA/SELENE, produced by LISM, distributed by JAXA/ISAS DARTS.
**Chandrayaan-2** images are *not* in this folder: PRADAN products are
"(c) reserved ISRO". Running the build script on a machine that has the
PRADAN download writes a TMC-2 → NAC scenario into `_local_chandrayaan2/`,
which git ignores.
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true")
    build(ap.parse_args().force)
