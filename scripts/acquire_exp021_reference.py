"""EXP-021 acquisition: the validation site's Kaguya TC seamless ortho blocks.

    python scripts/acquire_exp021_reference.py

Frozen in ``docs/stages/EXP-021_verdict_fa_fr.md`` Part 1 section 3.1.
One 3 x 3 degree tile, ``TCO_MAPs02_N03E021N00E024SC`` (0-3 N, 21-24 E),
covering EXP-018's held-out Tranquillitatis window, is fetched ONCE (E-050:
DARTS ignores HTTP Range) and cut by rule into two blocks:

    REF   the bounding box of the seven EXP-018 tiles' footprints (from the
          archive corner map, no pixel read) plus 2 km on every side
    NULL  same longitude span, latitude [top + 0.825, top + 1.825] deg
          (>= 25 km clear of REF); if that leaves the tile, the band
          [bottom - 1.825, bottom - 0.825]; if neither fits, NO DATA

The grid, the label parsing and the manifest layout are
``scripts/acquire_exp019_reference.py``'s, unchanged: projection offsets are
authoritative, the label's corner summaries are recorded beside them, and the
manifest carries GLOBAL graticule edges with the block offset in row0/col0
(E-052). Nothing here computes a statistic. Refuses to overwrite (integrity
rule 4).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DATA = ROOT / "data"
RAW = DATA / "raw" / "reference"
STAGE = "EXP-021"

BASE = ("https://data.darts.isas.jaxa.jp/pub/pds3/"
        "sln-l-tc-5-ortho-map-seamless-v2.0/lon021/data/")
PRODUCT = "TCO_MAPS02_N03E021N00E024SC"
FILE = "TCO_MAPs02_N03E021N00E024SC"
IMG = BASE + FILE + ".img"
LBL = BASE + FILE + ".lbl"
CREDIT = ("SELENE (Kaguya) Terrain Camera Ortho Map Seamless V2.0, "
          "SLN-L-TC-5-ORTHO-MAP-SEAMLESS-V2.0, produced by LISM, "
          "distributed by JAXA/ISAS DARTS")
MOON_R_M = 1737400.0

# Part 1 section 3.1, frozen.
MARGIN_M = 2000.0
NULL_GAP_DEG = 0.825
NULL_SPAN_DEG = 1.0
MANIFESTS = {"ref": "exp021_tc_ortho_ref_block.json",
             "null": "exp021_tc_ortho_null_block.json"}
ROLES = {"ref": "validation reference block: every EXP-018 Tranquillitatis tile footprint + 2 km",
         "null": "validation null block: >= 25 km from every source footprint, same product"}


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _lbl_value(text: str, key: str) -> str:
    m = re.search(rf"^\s*{key}\s*=\s*([^\s<]+)", text, re.M)
    if not m:
        raise RuntimeError(f"{key} not in label")
    return m.group(1).strip('"')


def tile_footprints() -> dict:
    """(lon, lat) of each EXP-018 tile's four corners, through the archive corner map."""
    e7 = _load("_exp007", "scripts/run_exp007.py")
    man = json.loads((DATA / "manifests" / "exp018_tranquillitatis_manifest.json")
                     .read_text(encoding="utf-8"))
    prods = json.loads((DATA / "manifests" / "exp018_tranquillitatis_index_geometry.json")
                       .read_text(encoding="utf-8"))["products"]
    out = {}
    for t in man["tiles"]:
        corners = e7.corners_for(t["pdsid"], prods)
        l0, s0 = t["line0"], t["sample0"]
        l1, s1 = l0 + t["n_lines"] - 1, s0 + t["n_samples"] - 1
        out[t["pdsid"]] = [list(map(float, corners.lonlat_at(float(li), float(si))))
                           for li, si in ((l0, s0), (l0, s1), (l1, s1), (l1, s0))]
    return out


def main() -> None:
    paths = {k: DATA / "manifests" / v for k, v in MANIFESTS.items()}
    present = [p.name for p in paths.values() if p.exists()]
    if present:
        raise SystemExit(f"{', '.join(present)} exist (integrity rule 4)")
    RAW.mkdir(parents=True, exist_ok=True)
    (DATA / "metadata" / "kaguya_tc").mkdir(parents=True, exist_ok=True)

    fp = tile_footprints()
    lons = np.array([c[0] for v in fp.values() for c in v])
    lats = np.array([c[1] for v in fp.values() for c in v])
    lat_c = float(np.mean(lats))
    dlat = MARGIN_M / (np.pi / 180.0 * MOON_R_M)
    dlon = dlat / np.cos(np.radians(lat_c))
    ref_lat = (float(lats.min() - dlat), float(lats.max() + dlat))
    ref_lon = (float(lons.min() - dlon), float(lons.max() + dlon))
    print(f"footprints: lon {lons.min():.4f}-{lons.max():.4f}, lat {lats.min():.4f}-"
          f"{lats.max():.4f}; REF lon {ref_lon[0]:.4f}-{ref_lon[1]:.4f} lat "
          f"{ref_lat[0]:.4f}-{ref_lat[1]:.4f}", flush=True)

    lbl = requests.get(LBL, timeout=180).text
    lbl_path = DATA / "metadata" / "kaguya_tc" / f"{PRODUCT}.lbl"
    lbl_path.write_text(lbl, encoding="utf-8")
    lbl_sha = hashlib.sha256(lbl.encode("utf-8")).hexdigest()

    lines = int(_lbl_value(lbl, "LINES"))
    samples = int(_lbl_value(lbl, "LINE_SAMPLES"))
    bits = int(_lbl_value(lbl, "SAMPLE_BITS"))
    stype = _lbl_value(lbl, "SAMPLE_TYPE")
    scaling = float(_lbl_value(lbl, "SCALING_FACTOR"))
    offset_dn = float(_lbl_value(lbl, "OFFSET"))
    dummy = float(_lbl_value(lbl, "DUMMY"))
    ppd = float(_lbl_value(lbl, "MAP_RESOLUTION"))
    scale_km = float(_lbl_value(lbl, "MAP_SCALE"))
    lpo = float(_lbl_value(lbl, "LINE_PROJECTION_OFFSET"))
    spo = float(_lbl_value(lbl, "SAMPLE_PROJECTION_OFFSET"))
    clon = float(_lbl_value(lbl, "CENTER_LONGITUDE"))
    clat = float(_lbl_value(lbl, "CENTER_LATITUDE"))
    proj = _lbl_value(lbl, "MAP_PROJECTION_TYPE")
    if stype != "MSB_UNSIGNED_INTEGER" or bits != 16:
        raise RuntimeError(f"unexpected sample type {stype}/{bits}")
    if abs(clat) > 1e-9 or abs(clon) > 1e-9:
        raise RuntimeError(f"projection centre is not (0, 0): {clon}, {clat}")

    lat_top = (lpo + 0.5) / ppd
    lon_left = clon - (spo + 0.5) / ppd
    lat_bottom_tile = lat_top - lines / ppd
    summary = {
        "MAXIMUM_LATITUDE": float(_lbl_value(lbl, "MAXIMUM_LATITUDE")),
        "MINIMUM_LATITUDE": float(_lbl_value(lbl, "MINIMUM_LATITUDE")),
        "WESTERNMOST_LONGITUDE": float(_lbl_value(lbl, "WESTERNMOST_LONGITUDE")),
        "EASTERNMOST_LONGITUDE": float(_lbl_value(lbl, "EASTERNMOST_LONGITUDE")),
        "top_edge_from_LPO": lat_top, "left_edge_from_SPO": lon_left,
        "summary_vs_offsets_px": [
            (lat_top - float(_lbl_value(lbl, "MAXIMUM_LATITUDE"))) * ppd,
            (float(_lbl_value(lbl, "WESTERNMOST_LONGITUDE")) - lon_left) * ppd],
    }
    print(f"{PRODUCT}: {lines} x {samples}, {ppd} px/deg, {scale_km * 1000:.6f} m/px; "
          f"top {lat_top:.6f} left {lon_left:.6f}", flush=True)

    # NULL band by the frozen rule
    null_lat = (ref_lat[1] + NULL_GAP_DEG, ref_lat[1] + NULL_GAP_DEG + NULL_SPAN_DEG)
    null_rule = "north"
    if null_lat[1] > lat_top:
        null_lat = (ref_lat[0] - NULL_GAP_DEG - NULL_SPAN_DEG, ref_lat[0] - NULL_GAP_DEG)
        null_rule = "south"
        if null_lat[0] < lat_bottom_tile:
            null_lat, null_rule = None, "NO DATA: neither band fits the tile"
    blocks = {"ref": ref_lat}
    if null_lat is not None:
        blocks["null"] = null_lat
    print(f"NULL band: {null_lat} ({null_rule})", flush=True)

    itemsize = bits // 8
    record_bytes = samples * itemsize
    expected = lines * record_bytes
    col0 = max(0, int(np.floor((ref_lon[0] - lon_left) * ppd - 0.5)))
    col1 = min(samples, int(np.ceil((ref_lon[1] - lon_left) * ppd - 0.5)) + 1)

    t0 = time.perf_counter()
    img_path = RAW / f"{FILE}.img"
    if img_path.exists() and img_path.stat().st_size == expected:
        print(f"   {img_path.name} already on disk", flush=True)
    else:
        # Whole-file retries: the server ignores Range (E-050), so a broken
        # stream cannot be resumed, only restarted. The first attempt on
        # 2026-09-23 broke at 124 MB of 233 MB (IncompleteRead).
        for attempt in range(1, 6):
            got = 0
            try:
                with requests.get(IMG, stream=True, timeout=600) as r:
                    r.raise_for_status()
                    with open(img_path, "wb") as fh:
                        for chunk in r.iter_content(chunk_size=1 << 20):
                            fh.write(chunk)
                            got += len(chunk)
            except (requests.exceptions.RequestException, OSError) as exc:
                print(f"   attempt {attempt}: broken at {got / 1e6:.0f} MB ({exc.__class__.__name__})",
                      flush=True)
            if got == expected:
                print(f"   attempt {attempt}: {got / 1e6:.0f} MB in "
                      f"{time.perf_counter() - t0:.0f}s", flush=True)
                break
            time.sleep(5)
        else:
            img_path.unlink(missing_ok=True)
            raise RuntimeError(f"short body after 5 attempts, expected {expected}")
    sha_file = hashlib.sha256(img_path.read_bytes()).hexdigest()
    raw = np.memmap(img_path, dtype=">u2", mode="r", shape=(lines, samples))
    print(f"   product sha256={sha_file[:16]}... ({time.perf_counter() - t0:.0f}s)", flush=True)

    retrieved = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for key, (b_lat_min, b_lat_max) in blocks.items():
        r0 = max(0, int(np.floor((lat_top - b_lat_max) * ppd - 0.5)))
        r1 = min(lines, int(np.ceil((lat_top - b_lat_min) * ppd - 0.5)) + 1)
        dnr = np.asarray(raw[r0:r1]).copy()
        sha = hashlib.sha256(dnr.tobytes()).hexdigest()
        dn = dnr[:, col0:col1].astype(np.float64)
        arr = np.where(dn == dummy, np.nan, dn * scaling + offset_dn).astype(np.float32)
        npy = RAW / f"{PRODUCT}.{key}.rows{r0}_{r1}.npy"
        np.save(npy, arr)
        man = {
            "stage": STAGE, "product": PRODUCT, "block": key, "role": ROLES[key],
            "modality": "panchromatic ortho mosaic, photometrically normalised to "
                        "i = 30 deg, e = 0 deg, alpha = 30 deg (USGS), reflectance",
            "source_url": IMG, "label_url": LBL, "label_path": str(lbl_path.relative_to(ROOT)),
            "label_sha256": lbl_sha, "credit": CREDIT,
            "block_npy": str(npy.relative_to(ROOT)),
            "window_lat": [b_lat_min, b_lat_max], "window_lon": list(ref_lon),
            "row0": r0, "row1_exclusive": r1, "col0": col0, "col1_exclusive": col1,
            "byte_start": r0 * record_bytes, "byte_count": (r1 - r0) * record_bytes,
            "bytes_sha256": sha,
            "product_file_sha256": sha_file, "product_file_bytes": expected,
            "product_file_path": str(img_path.relative_to(ROOT)),
            "bytes_note": "product_file_sha256 is of the archive's whole .img (the server "
                          "ignores HTTP Range, E-050); bytes_sha256 is of this block's full "
                          "rows [row0, row1_exclusive) before the column cut",
            "grid": {"ppd_lat": ppd, "ppd_lon": ppd, "lat_top_deg": lat_top,
                     "lon_left_deg": lon_left, "map_scale_m": scale_km * 1000.0,
                     "projection": f"{proj}, planetocentric, pixel-registered",
                     "source": "LINE/SAMPLE_PROJECTION_OFFSET (authoritative)"},
            "label_summary_vs_offsets": summary,
            "dn": {"sample_type": stype, "bits": bits, "scaling_factor": scaling,
                   "offset": offset_dn, "dummy": dummy,
                   "dummy_fraction": float(np.isnan(arr).mean())},
            "unit": "reflectance (I/F), photometrically normalised",
            "retrieved_utc": retrieved,
            "footprints_lon_lat": fp if key == "ref" else None,
            "null_rule": null_rule if key == "null" else None,
            "preregistration": "docs/stages/EXP-021_verdict_fa_fr.md Part 1 section 3.1",
        }
        paths[key].write_text(json.dumps(man, indent=2), encoding="utf-8")
        print(f"{key}: rows [{r0}, {r1}) {arr.shape} dummy {man['dn']['dummy_fraction']:.4f} "
              f"-> {paths[key].name}", flush=True)
    if "null" not in blocks:
        print("NULL block: NO DATA (S0(vi) reported as NO DATA)", flush=True)


if __name__ == "__main__":
    main()
