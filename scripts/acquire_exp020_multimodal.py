"""EXP-020 acquisition: Kaguya MI nine-band reflectance and Diviner bolometric
temperature over the EXP-019 reference window.

    python scripts/acquire_exp020_multimodal.py

Frozen in ``docs/stages/EXP-020_multimodality.md`` Part 1 section 3 (commit
4e043a4). Two products, two very different servers:

* **Kaguya MI MAP V3** -- four 1 x 1 degree tiles, 2048 x 2048 x 9 bands, BSQ,
  MSB int16, SCALING_FACTOR 2e-5, 2048 px/deg. DARTS ignores HTTP Range
  (E-050), so each tile is downloaded once (88 MB) and sliced locally; the
  window is mosaicked onto one grid and written as ``(9, H, W)`` reflectance.
* **Diviner GDR L3 TBOL** -- one 2.1 GB global map at 128 px/deg, LSB int16,
  SCALING_FACTOR 0.02 K, MISSING_CONSTANT -32768. PDS Geosciences honours
  Range, and the script **checks** that rather than assuming it: the row block
  for the window is fetched by strict chunked byte range.

Both grids are taken from the labels' LINE/SAMPLE_PROJECTION_OFFSET
(authoritative) with the label's own corner summaries recorded beside them, as
REAL-DATA-08 and EXP-019 did. Nothing here computes a statistic. Refuses to
overwrite (integrity rule 4).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from siim.ingest import fetch_byte_range_chunked  # noqa: E402

DATA = ROOT / "data"
RAW = DATA / "raw" / "reference"
STAGE = "EXP-020"

# Part 1 section 3, frozen: the EXP-019 reference window.
LAT_MIN, LAT_MAX = 19.52, 20.24
LON_MIN, LON_MAX = 21.88, 22.17

MI_BASE = "https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-mi-5-map-v3.0/"
MI_TILES = [
    ("lon021", "MI_MAP_03_N20E021N19E022SC"),
    ("lon022", "MI_MAP_03_N20E022N19E023SC"),
    ("lon021", "MI_MAP_03_N21E021N20E022SC"),
    ("lon022", "MI_MAP_03_N21E022N20E023SC"),
]
MI_CREDIT = ("SELENE (Kaguya) Multiband Imager MAP V3.0, SLN-L-MI-5-MAP-V3.0, "
             "produced by LISM, distributed by JAXA/ISAS DARTS")
MI_MANIFEST = "exp020_kaguya_mi_block.json"

# Amendment A1: the frozen night cycle 20090705n has NO valid samples over the
# window (missing_fraction 1.0000, recorded), and a night map carries thermal
# inertia rather than the insolation-and-albedo field a reflectance image shares.
# The rule frozen in A1 selects the earliest DAY cycle with >= 50 % coverage.
DIV_URL = ("https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/"
           "data_derived_gdr_l3/2009/cylindrical/img/dgdr_tbol_avg_cyl_20090727d_128_img")
DIV_PRODUCT = "DGDR_TBOL_AVG_CYL_20090727D_128_IMG"
DIV_CREDIT = ("LRO Diviner Lunar Radiometer Experiment GDR L3 bolometric temperature, "
              "LRO-L-DLRE-5-GDR-V1.0, D. A. Paige / UCLA, PDS Geosciences Node")
DIV_MANIFEST = "exp020_diviner_tbol_day_block.json"
DIV_LAT_PAD = 0.1                      # a little wider than the window, in degrees


def _lbl_value(text: str, key: str) -> str:
    m = re.search(rf"^\s*{key}\s*=\s*([^\s<]+)", text, re.M)
    if not m:
        raise RuntimeError(f"{key} not in label")
    return m.group(1).strip('"').strip("'")


def _lbl_object(text: str, name: str) -> str:
    """The body of one PDS3 OBJECT block.

    The Kaguya MI label carries TWO array objects -- a 32-bit
    GEOMETRIC_DATA_ALTITUDE plane and the 9-band 16-bit IMAGE -- so a
    file-wide search for SAMPLE_TYPE finds the altitude plane's and silently
    describes the wrong array (found 2026-09-23, first run of this script).
    """
    m = re.search(rf"^\s*OBJECT\s*=\s*{name}\s*$(.*?)^\s*END_OBJECT\s*=\s*{name}\s*$",
                  text, re.M | re.S)
    if not m:
        raise RuntimeError(f"OBJECT = {name} not in label")
    return m.group(1)


def _download(url: str, path: Path, expected: int | None = None) -> int:
    if path.exists() and (expected is None or path.stat().st_size == expected):
        print(f"   {path.name} already on disk ({path.stat().st_size / 1e6:.0f} MB)", flush=True)
        return path.stat().st_size
    t0 = time.perf_counter()
    got = 0
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(path, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
                got += len(chunk)
    print(f"   {path.name} {got / 1e6:.0f} MB in {time.perf_counter() - t0:.0f}s "
          f"({got / 1e6 / max(1e-9, time.perf_counter() - t0):.2f} MB/s)", flush=True)
    if expected is not None and got != expected:
        path.unlink(missing_ok=True)
        raise RuntimeError(f"short body: {got} != {expected}")
    return got


def acquire_mi() -> None:
    man_path = DATA / "manifests" / MI_MANIFEST
    if man_path.exists():
        print(f"{man_path.name} exists; skipping (integrity rule 4)")
        return
    meta_dir = DATA / "metadata" / "kaguya_mi"
    meta_dir.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)

    tiles = []
    for lon_dir, pid in MI_TILES:
        lbl_url = f"{MI_BASE}{lon_dir}/data/{pid.replace('MI_MAP_03', 'MI_MAP_03')}.lbl"
        lbl_url = lbl_url.replace("MI_MAP_03", "MI_MAP_03")  # DARTS keeps the upper-case stem
        txt = requests.get(lbl_url, timeout=180).text
        if "PDS_VERSION_ID" not in txt:
            raise RuntimeError(f"unexpected label body for {pid}")
        (meta_dir / f"{pid}.lbl").write_text(txt, encoding="utf-8")
        img_obj = _lbl_object(txt, "IMAGE")
        proj_obj = _lbl_object(txt, "IMAGE_MAP_PROJECTION")
        bands = int(_lbl_value(img_obj, "BANDS"))
        lines = int(_lbl_value(img_obj, "LINES"))
        samples = int(_lbl_value(img_obj, "LINE_SAMPLES"))
        bits = int(_lbl_value(img_obj, "SAMPLE_BITS"))
        stype = _lbl_value(img_obj, "SAMPLE_TYPE")
        scaling = float(_lbl_value(img_obj, "SCALING_FACTOR"))
        offset = float(_lbl_value(img_obj, "OFFSET"))
        ppd = float(_lbl_value(proj_obj, "MAP_RESOLUTION"))
        lpo = float(_lbl_value(proj_obj, "LINE_PROJECTION_OFFSET"))
        spo = float(_lbl_value(proj_obj, "SAMPLE_PROJECTION_OFFSET"))
        clon = float(_lbl_value(proj_obj, "CENTER_LONGITUDE"))
        img_ptr = re.search(r"\^IMAGE\s*=\s*\([^,]+,\s*(\d+)", txt)
        if stype != "MSB_INTEGER" or bits != 16 or bands != 9:
            raise RuntimeError(f"{pid}: unexpected {stype}/{bits}/{bands} bands")
        lat_top = (lpo + 0.5) / ppd
        lon_left = clon - (spo + 0.5) / ppd
        tiles.append({
            "product_id": pid, "lon_dir": lon_dir, "label_url": lbl_url,
            "bands": bands, "lines": lines, "samples": samples, "bits": bits,
            "sample_type": stype, "scaling_factor": scaling, "offset": offset,
            "ppd": ppd, "lat_top_deg": lat_top, "lon_left_deg": lon_left,
            "image_start_byte": int(img_ptr.group(1)) - 1 if img_ptr else 0,
            "label_summary": {k: float(_lbl_value(proj_obj, k)) for k in
                              ("MAXIMUM_LATITUDE", "MINIMUM_LATITUDE",
                               "WESTERNMOST_LONGITUDE", "EASTERNMOST_LONGITUDE")},
            "filter_name": re.search(r"FILTER_NAME\s*=\s*\(([^)]*)\)", txt).group(1),
            "center_filter_wavelength_nm": [float(x) for x in re.findall(
                r"([0-9.]+)\s*<nm>", re.search(r"CENTER_FILTER_WAVELENGTH\s*=\s*\(([^)]*)\)",
                                               txt).group(1))],
        })
        print(f"{pid}: {lines}x{samples}x{bands} {ppd} px/deg top {lat_top:.6f} left {lon_left:.6f}",
              flush=True)

    ppd = tiles[0]["ppd"]
    if any(abs(t["ppd"] - ppd) > 1e-9 for t in tiles):
        raise RuntimeError("tiles disagree on MAP_RESOLUTION")
    # one common grid: global row/col indices on the MI graticule
    # The MI graticule is PIXEL-registered: the CENTRE of global row r is at
    # lat = 90 - r / ppd (each tile's LINE_PROJECTION_OFFSET says so), so the
    # grid's top EDGE is at 90 + 0.5 / ppd. Getting this half pixel wrong is
    # invisible here and 2216 km wrong once MapBlock subtracts row0 (E-052).
    def grow(lat):  # 0-based global row of a latitude, on the shared graticule
        return (90.0 - lat) * ppd

    def gcol(lon):
        return lon * ppd

    row0 = int(np.floor(grow(LAT_MAX)))
    row1 = int(np.ceil(grow(LAT_MIN))) + 1
    col0 = int(np.floor(gcol(LON_MIN)))
    col1 = int(np.ceil(gcol(LON_MAX))) + 1
    h, w = row1 - row0, col1 - col0
    block = np.full((9, h, w), np.nan, np.float32)
    print(f"mosaic: rows [{row0}, {row1}) cols [{col0}, {col1}) -> (9, {h}, {w})", flush=True)

    digests = {}
    for t in tiles:
        img_url = f"{MI_BASE}{t['lon_dir']}/data/{t['product_id'].replace('MI_MAP_03', 'MI_MAP_03')}.img"
        path = RAW / f"{t['product_id']}.img"
        expected = t["bands"] * t["lines"] * t["samples"] * (t["bits"] // 8) + t["image_start_byte"]
        _download(img_url, path, expected)
        digests[t["product_id"]] = hashlib.sha256(path.read_bytes()).hexdigest()
        mm = np.memmap(path, dtype=">i2", mode="r", offset=t["image_start_byte"],
                       shape=(t["bands"], t["lines"], t["samples"]))
        # this tile's own global row/col of its (0, 0) pixel
        t_row0 = int(round((90.0 - t["lat_top_deg"]) * ppd))
        t_col0 = int(round(t["lon_left_deg"] * ppd))
        r_lo, r_hi = max(row0, t_row0), min(row1, t_row0 + t["lines"])
        c_lo, c_hi = max(col0, t_col0), min(col1, t_col0 + t["samples"])
        if r_hi <= r_lo or c_hi <= c_lo:
            print(f"   {t['product_id']}: no overlap with the window", flush=True)
            continue
        sub = np.asarray(mm[:, r_lo - t_row0:r_hi - t_row0, c_lo - t_col0:c_hi - t_col0],
                         dtype=np.float64)
        vals = np.where(sub > 0, sub * t["scaling_factor"] + t["offset"], np.nan)
        block[:, r_lo - row0:r_hi - row0, c_lo - col0:c_hi - col0] = vals.astype(np.float32)
        print(f"   {t['product_id']}: placed rows [{r_lo}, {r_hi}) cols [{c_lo}, {c_hi})", flush=True)
        del mm

    npy = RAW / f"kaguya_mi_block_rows{row0}_{row1}.npy"
    np.save(npy, block)
    valid = [float(np.isfinite(block[b]).mean()) for b in range(9)]
    man = {
        "stage": STAGE, "product": "KAGUYA_MI_MAP_V3_MOSAIC", "tiles": tiles,
        "tile_sha256": digests, "credit": MI_CREDIT,
        "modality": "9-band VIS/NIR reflectance, photometrically normalised to "
                    "i = 30 deg, e = 0 deg, alpha = 30 deg (LISM ORIGINAL)",
        "block_npy": str(npy.relative_to(ROOT)),
        "block_shape": list(block.shape),
        "window_lat": [LAT_MIN, LAT_MAX], "window_lon": [LON_MIN, LON_MAX],
        "row0": row0, "row1_exclusive": row1, "col0": col0, "col1_exclusive": col1,
        "grid": {"ppd_lat": ppd, "ppd_lon": ppd,
                 # edges of the GLOBAL graticule; row0/col0 carry the block offset,
                 # exactly as MapBlock expects (E-052)
                 "lat_top_deg": 90.0 + 0.5 / ppd,
                 "lon_left_deg": -0.5 / ppd,
                 "map_scale_m": 14.806323445,
                 "projection": "SIMPLE CYLINDRICAL, planetocentric, pixel-registered",
                 "source": "LINE/SAMPLE_PROJECTION_OFFSET of each tile (authoritative)"},
        "valid_fraction_per_band": valid,
        "bands_nm": tiles[0]["center_filter_wavelength_nm"],
        "filter_names": tiles[0]["filter_name"],
        "invalid_rule": "sample <= 0 is invalid (reflectance is positive; the label's "
                        "INVALID_TYPE names saturation/minus/dummy/other without values)",
        "unit": "reflectance (I/F), photometrically normalised",
        "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "preregistration": "docs/stages/EXP-020_multimodality.md Part 1 section 3",
    }
    (DATA / "manifests" / MI_MANIFEST).write_text(json.dumps(man, indent=2), encoding="utf-8")
    print(f"MI: valid fractions {['%.3f' % v for v in valid]} -> {MI_MANIFEST}")


def acquire_diviner() -> None:
    man_path = DATA / "manifests" / DIV_MANIFEST
    if man_path.exists():
        print(f"{man_path.name} exists; skipping (integrity rule 4)")
        return
    meta_dir = DATA / "metadata" / "diviner"
    meta_dir.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)

    lbl = requests.get(DIV_URL + ".lbl", timeout=180).text
    (meta_dir / f"{DIV_PRODUCT}.lbl").write_text(lbl, encoding="utf-8")
    lines = int(_lbl_value(lbl, "LINES"))
    samples = int(_lbl_value(lbl, "LINE_SAMPLES"))
    bits = int(_lbl_value(lbl, "SAMPLE_BITS"))
    stype = _lbl_value(lbl, "SAMPLE_TYPE")
    scaling = float(_lbl_value(lbl, "SCALING_FACTOR"))
    offset = float(_lbl_value(lbl, "OFFSET"))
    missing = float(_lbl_value(lbl, "MISSING_CONSTANT"))
    ppd = float(_lbl_value(lbl, "MAP_RESOLUTION"))
    lpo = float(_lbl_value(lbl, "LINE_PROJECTION_OFFSET"))
    spo = float(_lbl_value(lbl, "SAMPLE_PROJECTION_OFFSET"))
    clon = float(_lbl_value(lbl, "CENTER_LONGITUDE"))
    rb = int(_lbl_value(lbl, "RECORD_BYTES"))
    if stype != "LSB_INTEGER" or bits != 16:
        raise RuntimeError(f"unexpected {stype}/{bits}")
    lat_top = (lpo + 0.5) / ppd
    lon_left = clon - (spo + 0.5) / ppd
    itemsize = bits // 8
    row0 = max(0, int(np.floor((lat_top - (LAT_MAX + DIV_LAT_PAD)) * ppd - 0.5)))
    row1 = min(lines, int(np.ceil((lat_top - (LAT_MIN - DIV_LAT_PAD)) * ppd - 0.5)) + 1)
    col0 = max(0, int(np.floor((LON_MIN - DIV_LAT_PAD - lon_left) * ppd - 0.5)))
    col1 = min(samples, int(np.ceil((LON_MAX + DIV_LAT_PAD - lon_left) * ppd - 0.5)) + 1)
    start = row0 * rb
    count = (row1 - row0) * rb
    print(f"{DIV_PRODUCT}: rows [{row0}, {row1}) cols [{col0}, {col1}) -> "
          f"{count / 1e6:.1f} MB of {lines * rb / 1e9:.2f} GB", flush=True)

    # E-050's lesson: check that the server really honours Range before chunking.
    probe = requests.get(DIV_URL + ".img", headers={"Range": "bytes=0-1023"}, timeout=180)
    honours_range = probe.status_code == 206
    print(f"   Range probe: HTTP {probe.status_code} "
          f"({'honoured' if honours_range else 'IGNORED - would download the whole product'})",
          flush=True)
    if not honours_range:
        raise SystemExit("this server ignores Range; fetch the whole product instead (E-050)")

    t0 = time.perf_counter()
    raw = fetch_byte_range_chunked(DIV_URL + ".img", start, count)
    sha = hashlib.sha256(raw).hexdigest()
    arr = np.frombuffer(raw, dtype="<i2").reshape(row1 - row0, samples)[:, col0:col1]
    vals = np.where(arr == missing, np.nan, arr * scaling + offset).astype(np.float32)
    npy = RAW / f"{DIV_PRODUCT}.rows{row0}_{row1}.npy"
    np.save(npy, vals)
    print(f"   {vals.shape} sha256={sha[:16]}... ({time.perf_counter() - t0:.0f}s), "
          f"missing {float(np.isnan(vals).mean()):.4f}", flush=True)

    man = {
        "stage": STAGE, "product": DIV_PRODUCT,
        "modality": "bolometric temperature (K), Diviner nadir-only, GDR L3 average",
        "source_url": DIV_URL + ".img", "label_url": DIV_URL + ".lbl",
        "label_path": str((meta_dir / f"{DIV_PRODUCT}.lbl").relative_to(ROOT)),
        "credit": DIV_CREDIT, "block_npy": str(npy.relative_to(ROOT)),
        "window_lat": [LAT_MIN - DIV_LAT_PAD, LAT_MAX + DIV_LAT_PAD],
        "window_lon": [LON_MIN - DIV_LAT_PAD, LON_MAX + DIV_LAT_PAD],
        "row0": row0, "row1_exclusive": row1, "col0": col0, "col1_exclusive": col1,
        "byte_start": start, "byte_count": count, "bytes_sha256": sha,
        "server_honours_range": honours_range,
        "grid": {"ppd_lat": ppd, "ppd_lon": ppd, "lat_top_deg": lat_top,
                 "lon_left_deg": lon_left, "map_scale_m": 236.901175,
                 "projection": "SIMPLE CYLINDRICAL, planetocentric, area-registered edges "
                               "from LINE/SAMPLE_PROJECTION_OFFSET",
                 "source": "LINE/SAMPLE_PROJECTION_OFFSET (authoritative)"},
        "label_summary": {k: float(_lbl_value(lbl, k)) for k in
                          ("MAXIMUM_LATITUDE", "MINIMUM_LATITUDE",
                           "WESTERNMOST_LONGITUDE", "EASTERNMOST_LONGITUDE")},
        "dn": {"sample_type": stype, "bits": bits, "scaling_factor": scaling,
               "offset": offset, "missing_constant": missing,
               "missing_fraction": float(np.isnan(vals).mean())},
        "unit": "K", "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "preregistration": "docs/stages/EXP-020_multimodality.md Part 1 section 3",
    }
    man_path.write_text(json.dumps(man, indent=2), encoding="utf-8")
    print(f"Diviner -> {DIV_MANIFEST}")


def main() -> None:
    acquire_mi()
    print()
    acquire_diviner()


if __name__ == "__main__":
    main()
