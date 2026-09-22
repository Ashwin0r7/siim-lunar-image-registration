"""EXP-019 acquisition: the SELENE (Kaguya) TC seamless ortho blocks.

    python scripts/acquire_exp019_reference.py

Frozen in ``docs/stages/EXP-019_controlled_reference.md`` Part 1 section 3.1
(commit 9cc9c13). One contiguous byte range of
``TCO_MAPs02_N21E021N18E024SC.img`` covering latitude 18.30 - 20.24 N is
fetched by strict chunked byte range, split into the two blocks Part 1 names,
and written with provenance:

    REF   19.52 - 20.24 N   covers every source footprint with ~2 km margin
    NULL  18.30 - 19.30 N   >= 25 km away, same product, same processing

The product is simple cylindrical, pixel-registered, MSB uint16 with
SCALING_FACTOR 0.01 and DUMMY 0. The grid is taken from the label's
LINE/SAMPLE_PROJECTION_OFFSET (authoritative) and the label's own corner
summaries are recorded beside it, exactly as REAL-DATA-08 did for Mini-RF.

**E-049.** The DARTS server does not honour HTTP ``Range`` on this product: it
answers ``200`` with the whole 233 MB image. ``fetch_byte_range`` detects that
(its documented failure mode 1) and slices the full body, which is correct and
which turns a 151 MB windowed read into **one full download per 8 MB chunk**.
So this script downloads the product **once**, records the SHA-256 of the
whole file, and slices locally -- which is also better provenance, because the
recorded digest is the archive's own file rather than a window of it.

Nothing here computes a statistic; the label is parsed, the file is fetched,
blocks are cut. Refuses to overwrite (integrity rule 4).
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

DATA = ROOT / "data"
RAW = DATA / "raw" / "reference"
STAGE = "EXP-019"

BASE = ("https://data.darts.isas.jaxa.jp/pub/pds3/"
        "sln-l-tc-5-ortho-map-seamless-v2.0/lon021/data/")
PRODUCT = "TCO_MAPS02_N21E021N18E024SC"
IMG = BASE + "TCO_MAPs02_N21E021N18E024SC.img"
LBL = BASE + "TCO_MAPs02_N21E021N18E024SC.lbl"
CREDIT = ("SELENE (Kaguya) Terrain Camera Ortho Map Seamless V2.0, "
          "SLN-L-TC-5-ORTHO-MAP-SEAMLESS-V2.0, produced by LISM, "
          "distributed by JAXA/ISAS DARTS")

# Part 1 section 3.1, frozen.
LAT_MIN, LAT_MAX = 18.30, 20.24          # one contiguous fetch spans both blocks
LON_MIN, LON_MAX = 21.88, 22.17
BLOCKS = {
    "ref": {"lat": (19.52, 20.24), "manifest": "exp019_tc_ortho_ref_block.json",
            "role": "reference block: every EXP-019 source footprint + ~2 km margin"},
    "null": {"lat": (18.30, 19.30), "manifest": "exp019_tc_ortho_null_block.json",
             "role": "null block: >= 25 km from any source footprint, same product"},
}


def _lbl_value(text: str, key: str) -> str:
    m = re.search(rf"^\s*{key}\s*=\s*([^\s<]+)", text, re.M)
    if not m:
        raise RuntimeError(f"{key} not in label")
    return m.group(1).strip('"')


def main() -> None:
    paths = {k: DATA / "manifests" / v["manifest"] for k, v in BLOCKS.items()}
    present = [p.name for p in paths.values() if p.exists()]
    if present:
        raise SystemExit(f"{', '.join(present)} exist (integrity rule 4)")
    RAW.mkdir(parents=True, exist_ok=True)
    (DATA / "metadata" / "kaguya_tc").mkdir(parents=True, exist_ok=True)

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

    # Same convention as REAL-DATA-08: the projection offsets are authoritative,
    # the label's corner summaries are recorded beside them.
    lat_top = (lpo + 0.5) / ppd                       # top EDGE of line 0
    lon_left = clon - (spo + 0.5) / ppd               # left EDGE of sample 0
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
    print(f"{PRODUCT}: {lines} x {samples}, {ppd} px/deg, {scale_km * 1000:.6f} m/px")
    print(f"  grid from offsets: top edge {lat_top:.6f} deg, left edge {lon_left:.6f} deg")
    print(f"  label summary vs offsets: {summary['summary_vs_offsets_px'][0]:+.3f} / "
          f"{summary['summary_vs_offsets_px'][1]:+.3f} px")

    itemsize = bits // 8
    record_bytes = samples * itemsize
    row0 = max(0, int(np.floor((lat_top - LAT_MAX) * ppd - 0.5)))
    row1 = min(lines, int(np.ceil((lat_top - LAT_MIN) * ppd - 0.5)) + 1)
    col0 = max(0, int(np.floor((LON_MIN - lon_left) * ppd - 0.5)))
    col1 = min(samples, int(np.ceil((LON_MAX - lon_left) * ppd - 0.5)) + 1)
    start = row0 * record_bytes                       # ^IMAGE = (..., 1 <BYTES>)
    count = (row1 - row0) * record_bytes
    expected = lines * record_bytes
    print(f"  want rows [{row0}, {row1}) cols [{col0}, {col1}): {count / 1e6:.1f} MB "
          f"of a {expected / 1e6:.1f} MB product (E-049: the server ignores Range, "
          f"so the whole file is fetched once)", flush=True)

    t0 = time.perf_counter()
    img_path = RAW / "TCO_MAPs02_N21E021N18E024SC.img"
    if img_path.exists() and img_path.stat().st_size == expected:
        print(f"   {img_path.name} already on disk ({expected / 1e6:.1f} MB)", flush=True)
    else:
        got = 0
        with requests.get(IMG, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(img_path, "wb") as fh:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
                    got += len(chunk)
                    if got % (32 << 20) < (1 << 20):
                        print(f"   {got / 1e6:.0f}/{expected / 1e6:.0f} MB "
                              f"({got / 1e6 / max(1e-9, time.perf_counter() - t0):.2f} MB/s)",
                              flush=True)
        if got != expected:
            img_path.unlink(missing_ok=True)
            raise RuntimeError(f"short body: {got} bytes, expected {expected}")
    sha_file = hashlib.sha256(img_path.read_bytes()).hexdigest()
    raw = np.memmap(img_path, dtype=">u2", mode="r", shape=(lines, samples))
    block = np.asarray(raw[row0:row1]).copy()
    sha = hashlib.sha256(block.tobytes()).hexdigest()
    whole = block
    print(f"   product sha256={sha_file[:16]}...  window {whole.shape} "
          f"sha256={sha[:16]}... ({time.perf_counter() - t0:.0f}s)", flush=True)

    retrieved = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for key, spec in BLOCKS.items():
        b_lat_min, b_lat_max = spec["lat"]
        r0 = max(row0, int(np.floor((lat_top - b_lat_max) * ppd - 0.5)))
        r1 = min(row1, int(np.ceil((lat_top - b_lat_min) * ppd - 0.5)) + 1)
        dn = whole[r0 - row0:r1 - row0, col0:col1].astype(np.float64)
        arr = np.where(dn == dummy, np.nan, dn * scaling + offset_dn).astype(np.float32)
        npy = RAW / f"{PRODUCT}.{key}.rows{r0}_{r1}.npy"
        np.save(npy, arr)
        man = {
            "stage": STAGE, "product": PRODUCT, "block": key, "role": spec["role"],
            "modality": "panchromatic ortho mosaic, photometrically normalised to "
                        "i = 30 deg, e = 0 deg, alpha = 30 deg (USGS), reflectance",
            "source_url": IMG, "label_url": LBL, "label_path": str(lbl_path.relative_to(ROOT)),
            "label_sha256": lbl_sha, "credit": CREDIT,
            "block_npy": str(npy.relative_to(ROOT)),
            "window_lat": [b_lat_min, b_lat_max], "window_lon": [LON_MIN, LON_MAX],
            "row0": r0, "row1_exclusive": r1, "col0": col0, "col1_exclusive": col1,
            "byte_start": start, "byte_count": count, "bytes_sha256": sha,
            "product_file_sha256": sha_file, "product_file_bytes": expected,
            "product_file_path": str(img_path.relative_to(ROOT)),
            "bytes_note": "product_file_sha256 is of the archive's whole .img (the server "
                          "ignores HTTP Range, E-049); bytes_sha256 is of the contiguous row "
                          "window [row0_fetch, row1_fetch) covering BOTH blocks, and each "
                          "block is a row slice of that window",
            "row0_fetch": row0, "row1_fetch_exclusive": row1,
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
            "preregistration": "docs/stages/EXP-019_controlled_reference.md Part 1 3.1",
        }
        paths[key].write_text(json.dumps(man, indent=2), encoding="utf-8")
        print(f"{key}: rows [{r0}, {r1}) {arr.shape} dummy {man['dn']['dummy_fraction']:.4f} "
              f"-> {paths[key].name}")


if __name__ == "__main__":
    main()
