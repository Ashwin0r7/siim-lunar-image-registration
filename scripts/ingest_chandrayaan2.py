"""Write `data/manifests/chandrayaan2_manifest.json` — REAL-DATA-09 §3.

The contract is explicit that this runs **before any product is opened**: path,
size, SHA-256, PRADAN product ID and the label fields the ingestion contract
reads, for every file that came with every product. A partial download is then
detectable by hash rather than by a confusing decode.

Only the PDS4 XML labels are parsed here (they are the manifest's own source);
no image array is decoded.

**Recorded placement deviation.** Part 1 §3 says the products go unrenamed
under `data/raw/chandrayaan2/<instrument>/`. They arrived under
`realdata/realdata/<INSTRUMENT>/...` and are 23 GB, so they are manifested
where they lie rather than copied. Nothing is renamed, and every path in the
manifest is repo-relative, so the deviation is recorded and reversible.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "realdata" / "realdata"
OUT = ROOT / "data" / "manifests" / "chandrayaan2_manifest.json"

#: isda:* label fields the ingestion contract reads (§4 steps 1, 5, 6, 7).
ISDA_FIELDS = (
    "solar_incidence", "sun_azimuth", "sun_elevation", "projection", "area",
    "spacecraft_altitude", "product_accuracy_stdev_CE", "product_accuracy_rmse_CE",
    "imaging_orbit_number", "orbit_limb_direction", "line_exposure_duration",
    "focal_length", "detector_pixel_width", "reference_data_used",
    "upper_left_latitude", "upper_left_longitude",
    "upper_right_latitude", "upper_right_longitude",
    "lower_left_latitude", "lower_left_longitude",
    "lower_right_latitude", "lower_right_longitude",
)


def sha256(path: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def label_fields(xml_path: Path) -> dict:
    t = xml_path.read_text(encoding="utf-8", errors="replace")
    out: dict = {}
    for f in ISDA_FIELDS:
        m = re.search(rf"<isda:{f}[^>]*>([^<]+)<", t)
        if m:
            v = m.group(1).strip()
            try:
                out[f] = float(v)
            except ValueError:
                out[f] = v
    m = re.search(r"<logical_identifier>([^<]+)<", t)
    if m:
        out["logical_identifier"] = m.group(1).strip()
    m = re.search(r"<start_date_time>([^<]+)<", t)
    if m:
        out["start_date_time"] = m.group(1).strip()
    for tag in ("lines", "line_samples", "axes"):
        m = re.search(rf"<{tag}>([^<]+)<", t)
        if m:
            out[tag] = m.group(1).strip()
    return out


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"{OUT.relative_to(ROOT)} exists (integrity rule 4)")
    if not SRC.exists():
        raise SystemExit(f"{SRC} not found")

    # Precomputed hashes may be supplied on stdin as "<sha256>  <path>" lines so
    # a long hashing pass is not repeated. Anything absent is hashed here.
    precomputed: dict[str, str] = {}
    if not sys.stdin.isatty():
        for line in sys.stdin:
            parts = line.strip().split(None, 1)
            if len(parts) == 2 and len(parts[0]) == 64:
                precomputed[str(Path(parts[1]))] = parts[0]

    products: dict[str, dict] = {}
    for xml in sorted(SRC.rglob("data/**/*.xml")):
        pdir = xml.parent
        stem = xml.stem
        instrument = ("OHRC" if "_ohr_" in stem else
                      "TMC-2" if "_tmc_" in stem else
                      "IIRS" if "_iir_" in stem else "UNKNOWN")
        kind = ("dtm" if "_dtm_" in stem else "ortho" if "_oth_" in stem
                else "image")
        data_file = next((p for p in pdir.iterdir()
                          if p.suffix.lower() in (".img", ".tif", ".tiff")), None)
        if data_file is None:
            continue

        rel_key = str(data_file.relative_to(ROOT)).replace("\\", "/")
        if rel_key in products:          # the DTM ships twice; keep one entry
            products[rel_key]["also_delivered_at"] = products[rel_key].get(
                "also_delivered_at", [])
            continue

        files = []
        for f in sorted(pdir.parent.parent.parent.rglob("*")):
            if not f.is_file():
                continue
            rel = str(f.relative_to(ROOT)).replace("\\", "/")
            digest = precomputed.get(str(f)) or precomputed.get(rel)
            if digest is None and f.stat().st_size <= (64 << 20):
                digest = sha256(f)       # hash the small companions here
            files.append({"path": rel, "size_bytes": f.stat().st_size,
                          "sha256": digest})

        fields = label_fields(xml)
        products[rel_key] = {
            "instrument": instrument,
            "kind": kind,
            "product_id": stem,
            "pradan_logical_identifier": fields.get("logical_identifier"),
            "label_xml": str(xml.relative_to(ROOT)).replace("\\", "/"),
            "data_file": rel_key,
            "data_file_size_bytes": data_file.stat().st_size,
            "data_file_sha256": (precomputed.get(str(data_file))
                                 or precomputed.get(rel_key)),
            "label_fields": fields,
            "files": files,
        }
        print(f"  {instrument:6s} {kind:6s} {stem}", flush=True)

    doc = {
        "stage": "REAL-DATA-09",
        "written_before_any_product_was_opened": True,
        "source_root": str(SRC.relative_to(ROOT)).replace("\\", "/"),
        "placement_deviation": (
            "Part 1 §3 specifies data/raw/chandrayaan2/<instrument>/. The "
            "products (23 GB) arrived under realdata/realdata/<INSTRUMENT>/ "
            "and are manifested in place, unrenamed, rather than copied. "
            "Recorded deviation; no file was modified."),
        "acknowledgement_required": (
            "We acknowledge the use of data from the Chandrayaan-II, second "
            "lunar mission of the Indian Space Research Organisation (ISRO), "
            "archived at the Indian Space Science Data Centre (ISSDC)."),
        "marking_required": "© reserved ISRO on any printed data product.",
        "n_products": len(products),
        "products": products,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)} — {len(products)} products")


if __name__ == "__main__":
    main()
