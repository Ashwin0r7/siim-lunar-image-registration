"""EXP-018 held-out window: census (labels + corners only), then fetch.

    python scripts/census_exp018.py census --window apollo16
    python scripts/census_exp018.py fetch  --window apollo16

Part 1 section 3.4-3.5 (commit e8071c4), applied as written:

* candidate windows in the frozen priority order (Apollo 16, Fra Mauro,
  Tranquillitatis); the census runs on ONE window per invocation and the
  caller moves to the next priority only if S5 fails from geometry;
* filters identical to REAL-DATA-07 Part 1: calibrated NAC (CDRNAC4), swath
  contains the target point by corner-map inversion with NO clamping (a full
  4096 x 2048 tile at decimation 2 -- 8192 x 4096 at decimation 4 below 0.6 m
  -- must fit unclamped), incidence <= 75 (D-029), emission <= 1.8, no night
  frame, L/R of one orbit counted as one frame (lower emission kept);
* the incidence ladder {20, 25, 30, 40, 50, 60, 70} +/- 5 deg, <= 8 frames;
* S0(a): the untouched grep is run over the repository tree BEFORE any label
  or geometry is written for a candidate, and its record excludes only the
  paths this stage itself writes;
* S5 is evaluated from labels and CONFIRMED overlap alone, before any pixel.

The census reads ODE metadata, PDS4 labels (~13 KB each) and archive index
rows (~130 KB each). It reads NO image byte. ``fetch`` reads image bytes for
the frames the census listed and nothing else.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.ingest import (  # noqa: E402
    FrameCorners,
    decode_tile,
    fetch_byte_range_chunked,
    fetch_label,
    parse_display_direction,
    parse_image_structure,
    plan_tile_byte_range,
    validate_structure,
)
from siim.ingest.lro_nac import _parse_product, query_nac  # noqa: E402
from siim.ingest.orientation import handedness  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_acq = _load("_acq", ROOT / "scripts" / "acquire_real_pair.py")
_geo = _load("_geo", ROOT / "scripts" / "fetch_index_geometry.py")
_e18 = _load("_e18", ROOT / "scripts" / "run_exp018.py")

DATA = ROOT / "data"
OUT = ROOT / "experiments" / "EXP-018"

#: Part 1 section 3.4, priority order fixed there.
WINDOWS = {
    "apollo16": {"priority": 1, "arm": "H", "terrain": "highlands",
                 "centre_lon_lat": (15.50, -8.97), "name": "Apollo 16 / Descartes"},
    "fra_mauro": {"priority": 2, "arm": "H", "terrain": "hummocky highland ejecta",
                  "centre_lon_lat": (342.53, -3.65), "name": "Apollo 14 / Fra Mauro"},
    "tranquillitatis": {"priority": 3, "arm": "M", "terrain": "mare",
                        "centre_lon_lat": (23.47, 0.67), "name": "Apollo 11 / Mare Tranquillitatis"},
}
#: REAL-DATA-07's census box: 0.04 deg around the target.
BOX_HALF_DEG = 0.02
INCIDENCE_MAX = 75.0
EMISSION_MAX = 1.8
LADDER = (20.0, 25.0, 30.0, 40.0, 50.0, 60.0, 70.0)
LADDER_HALF_WIDTH = 5.0
MAX_FRAMES = 8
DEFAULT = {"n_lines": 4096, "n_samples": 2048, "decimation": 2}
FINE = {"n_lines": 8192, "n_samples": 4096, "decimation": 4}
FINE_BELOW_M = 0.6
RD03 = (22.034, 20.035)
RD04 = (22.010, 19.666)
MOON_R_KM = 1737.4

_TEXT_EXT = {".json", ".csv", ".log", ".md", ".py", ".xml", ".txt", ".html", ".js", ".yaml",
             ".yml", ".toml", ".cfg", ".ini", ".lbl", ".tab", ".rst", ".css"}
_GREP_DIRS = ["experiments", "data/manifests", "data/metadata", "data/processed", "docs",
              "src", "scripts", "tests"]


def great_circle_km(a, b) -> float:
    lon1, lat1, lon2, lat2 = map(np.deg2rad, (a[0], a[1], b[0], b[1]))
    h = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return float(2 * MOON_R_KM * np.arcsin(np.sqrt(h)))


# ---------------------------------------------------------------------------
# S0(a) -- the untouched grep
# ---------------------------------------------------------------------------
def untouched_grep(pdsids: list[str], exclude_prefixes: list[str]) -> dict:
    """Case-insensitive search for each product id (both spellings share the
    bare ``m<digits>[lr]c`` token) over file NAMES and text CONTENTS."""
    toks = {p: p.split(".")[-1].lower() for p in pdsids}
    pats = {p: re.compile(r"(?<![0-9a-z])" + re.escape(t) + r"(?![0-9a-z])") for p, t in toks.items()}
    hits = {p: [] for p in pdsids}
    n_files = n_read = 0
    for d in _GREP_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if not f.is_file():
                continue
            rel = str(f.relative_to(ROOT)).replace("\\", "/")
            if "__pycache__" in rel or any(rel.startswith(x) for x in exclude_prefixes):
                continue
            n_files += 1
            low = rel.lower()
            for p, pat in pats.items():
                if pat.search(low):
                    hits[p].append({"path": rel, "where": "name"})
            if f.suffix.lower() in _TEXT_EXT and f.stat().st_size < 200 << 20:
                try:
                    text = f.read_bytes().decode("latin-1").lower()
                except OSError:
                    continue
                n_read += 1
                for p, pat in pats.items():
                    if pat.search(text):
                        hits[p].append({"path": rel, "where": "content"})
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return {"criterion": "S0(a)", "git_head": head,
            "command": ("python scripts/census_exp018.py: rglob over " + ", ".join(_GREP_DIRS) +
                        "; regex (?<![0-9a-z])m<digits>[lr]c(?![0-9a-z]) on lower-cased file names and "
                        "on the contents of text files " + ", ".join(sorted(_TEXT_EXT))),
            "excluded_prefixes": exclude_prefixes,
            "n_files_scanned": n_files, "n_files_read": n_read,
            "hits_per_id": {p: len(h) for p, h in hits.items()},
            "hits": {p: h for p, h in hits.items() if h},
            "untouched": [p for p, h in hits.items() if not h],
            "dropped": [p for p, h in hits.items() if h],
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


# ---------------------------------------------------------------------------
# census
# ---------------------------------------------------------------------------
def corners_from_fields(pdsid: str, fields: dict, label_text: str) -> FrameCorners:
    disp = parse_display_direction(label_text)
    if (disp["vertical_axis"], disp["vertical_direction"]) != ("Line", "Top to Bottom") or \
            (disp["horizontal_axis"], disp["horizontal_direction"]) != ("Sample", "Left to Right"):
        raise SystemExit(f"{pdsid}: unexpected Display_Direction {disp}")

    def c(name):
        return (float(fields[name + "_LONGITUDE"]), float(fields[name + "_LATITUDE"]))

    return FrameCorners(c("UPPER_LEFT"), c("UPPER_RIGHT"), c("LOWER_LEFT"), c("LOWER_RIGHT"),
                        int(fields["IMAGE_LINES"]), int(fields["LINE_SAMPLES"]))


def ladder_select(admissible: list[dict]) -> tuple[list[dict], list[dict]]:
    """Part 1 section 3.5. Returns (chosen, ladder_record)."""
    pool = sorted(admissible, key=lambda r: (r["incidence_deg"], r["emission_deg"], r["pdsid"]))
    chosen, record = [], []
    used: set[str] = set()

    def nearest(rung, within):
        cands = [r for r in pool if r["pdsid"] not in used
                 and (within is None or abs(r["incidence_deg"] - rung) <= within)]
        if not cands:
            return None
        return min(cands, key=lambda r: (abs(r["incidence_deg"] - rung), r["emission_deg"], r["pdsid"]))

    for rung in LADDER:
        if len(chosen) >= MAX_FRAMES:
            break
        r = nearest(rung, LADDER_HALF_WIDTH)
        how = "within +/-5 deg"
        if r is None:
            r = nearest(rung, None)
            how = "rung empty within +/-5 deg; nearest unused admissible frame taken instead"
        if r is None:
            record.append({"rung_deg": rung, "pdsid": None, "how": "no admissible frame left"})
            continue
        used.add(r["pdsid"])
        chosen.append(dict(r, rung_deg=rung))
        record.append({"rung_deg": rung, "pdsid": r["pdsid"], "incidence_deg": r["incidence_deg"], "how": how})
    return chosen, record


def census(window: str) -> None:
    spec = WINDOWS[window]
    lon, lat = spec["centre_lon_lat"]
    out_json = OUT / f"census_{window}.json"
    planned = DATA / "manifests" / f"exp018_{window}_planned_manifest.json"
    geom_out = DATA / "manifests" / f"exp018_{window}_index_geometry.json"
    s0_out = OUT / "exp018_s0_untouched.json"
    for p in (out_json, planned, geom_out):
        if p.exists():
            raise SystemExit(f"{p.relative_to(ROOT)} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    sep = {"rd03_km": great_circle_km((lon, lat), RD03), "rd04_km": great_circle_km((lon, lat), RD04)}
    print(f"== EXP-018 census: {spec['name']} ({lon}, {lat}) priority {spec['priority']} arm {spec['arm']} ==")
    print(f"separation from RD-03 {sep['rd03_km']:.0f} km, RD-04 {sep['rd04_km']:.0f} km\n")

    prods = query_nac(min_lat=lat - BOX_HALF_DEG, max_lat=lat + BOX_HALF_DEG,
                      min_lon=lon - BOX_HALF_DEG, max_lon=lon + BOX_HALF_DEG, limit=2000)
    print(f"ODE returned {len(prods)} CDRNAC4 products intersecting the 0.04 deg box\n")
    funnel = {"ode_returned": len(prods)}
    rows = []
    for p in prods:
        r = {"pdsid": p.pdsid, "incidence_deg": p.incidence_deg, "emission_deg": p.emission_deg,
             "map_resolution_m": p.map_resolution_m, "utc_start": p.utc_start, "admissible": True}
        if p.incidence_deg is None or p.incidence_deg > INCIDENCE_MAX:
            r.update(admissible=False, rejected_by=f"incidence > {INCIDENCE_MAX} (D-029) or night/absent")
        elif p.emission_deg is None or p.emission_deg > EMISSION_MAX:
            r.update(admissible=False, rejected_by=f"emission > {EMISSION_MAX}")
        rows.append(r)
    funnel["after_incidence_emission"] = sum(r["admissible"] for r in rows)
    # L/R of one orbit = one frame: keep the lower emission (ties: lexically smaller id)
    by_orbit: dict[str, list[dict]] = {}
    for r in rows:
        if r["admissible"]:
            by_orbit.setdefault(r["pdsid"][:-2], []).append(r)
    for k, grp in by_orbit.items():
        keep = min(grp, key=lambda r: (r["emission_deg"], r["pdsid"]))
        for r in grp:
            if r is not keep:
                r.update(admissible=False, rejected_by=f"L/R of one orbit: {keep['pdsid']} kept (lower emission)")
    funnel["after_lr_dedupe"] = sum(r["admissible"] for r in rows)

    # S0(a) BEFORE any label or geometry is written for a candidate
    cand_ids = [r["pdsid"] for r in rows if r["admissible"]]
    s0 = untouched_grep(cand_ids, exclude_prefixes=["experiments/EXP-018/", "data/manifests/exp018_",
                                                    f"data/metadata/{window}/", f"data/processed/{window}/"])
    s0["window"] = window
    if s0_out.exists():
        prev = json.loads(s0_out.read_text(encoding="utf-8"))
        later = [w for w in prev.get("later_windows", []) if w.get("window") != window]
        prev["later_windows"] = later + [s0]
        s0_out.write_text(json.dumps(prev, indent=2), encoding="utf-8")
    else:
        s0_out.write_text(json.dumps(s0, indent=2), encoding="utf-8")
    for r in rows:
        if r["admissible"] and r["pdsid"] in s0["dropped"]:
            r.update(admissible=False, rejected_by="S0(a): product id appears in the repository")
    funnel["after_s0_untouched"] = sum(r["admissible"] for r in rows)
    print(f"S0(a): {s0['n_files_scanned']} files scanned, {len(s0['untouched'])} of {len(cand_ids)} "
          f"candidates untouched, dropped {s0['dropped']}\n")

    # authoritative corners + containment (no clamping) for every remaining candidate
    prod_by_id = {p.pdsid: p for p in prods}
    ids = [r["pdsid"] for r in rows if r["admissible"]]
    print(f"fetching labels + index rows for {len(ids)} candidates ...", flush=True)
    vols: dict = {}
    for pdsid in ids:
        # Per product, so one frame served from a volume layout the index-row
        # reader does not know (the PDS4-migrated LROLRC_1067C root, found on
        # the Fra Mauro census 2026-09-22) excludes that frame, not the census.
        try:
            vols.update(_geo.volumes_from_ode([pdsid]))
        except SystemExit as exc:
            vols[pdsid] = {"error": str(exc)}
    records: dict = {}
    for r in rows:
        if not r["admissible"]:
            continue
        pdsid = r["pdsid"]
        try:
            if "error" in vols.get(pdsid, {"error": "no ODE volume"}):
                raise ValueError(vols.get(pdsid, {}).get("error", "no ODE volume"))
            lbl = fetch_label(prod_by_id[pdsid], DATA / "metadata" / window)
            text = lbl.read_text(encoding="utf-8")
            struct = parse_image_structure(text)
            validate_structure(struct)
            rec = _geo.fetch_row(vols[pdsid]["volume"], vols[pdsid]["product_id"])
            rec.update(vols[pdsid])
            records[pdsid] = rec
            f = rec["fields"]
            corners = corners_from_fields(pdsid, f, text)
            if (corners.lines, corners.samples) != (struct.lines, struct.samples):
                raise ValueError(f"index {corners.lines}x{corners.samples} != label {struct.lines}x{struct.samples}")
            win = FINE if (r["map_resolution_m"] or 9.9) < FINE_BELOW_M else DEFAULT
            line0, sample0, detail = _acq.window_centred_on(corners, lon, lat, win["n_lines"], win["n_samples"])
            r.update({"index_incidence_deg": float(f["INCIDENCE_ANGLE"]),
                      "index_emission_deg": float(f["EMISSION_ANGLE"]),
                      "index_resolution_m": float(f["RESOLUTION"]),
                      "lines_samples": [corners.lines, corners.samples],
                      "window": dict(win, line0=line0, sample0=sample0), "window_detail": detail,
                      "jacobian_determinant": handedness(corners, line0 + (win["n_lines"] - 1) / 2,
                                                         sample0 + (win["n_samples"] - 1) / 2),
                      "lro_flight_direction": f.get("LRO_FLIGHT_DIRECTION"), "orbit_node": f.get("ORBIT_NODE"),
                      "label_path": str(lbl.relative_to(ROOT)).replace("\\", "/")})
            r["jacobian_determinant_sign"] = int(np.sign(r["jacobian_determinant"]))
            if not detail["fully_inside_frame"]:
                r.update(admissible=False, rejected_by="a full tile centred on the target does not fit "
                                                       "unclamped (no clamping, Part 1 section 3.5)")
            if float(f["EMISSION_ANGLE"]) > EMISSION_MAX or float(f["INCIDENCE_ANGLE"]) > INCIDENCE_MAX:
                r.update(admissible=False, rejected_by="index-table incidence/emission fails the filter")
        except Exception as exc:  # noqa: BLE001 -- recorded, the frame is excluded, nothing guessed
            r.update(admissible=False, rejected_by=f"{type(exc).__name__}: {exc}")
        print(f"   {pdsid}: inc {r['incidence_deg']} em {r['emission_deg']} res {r['map_resolution_m']} "
              f"-> {'ADMISSIBLE' if r['admissible'] else r['rejected_by'][:80]}", flush=True)
    funnel["admissible"] = sum(r["admissible"] for r in rows)
    geom_out.write_text(json.dumps({
        "stage": "EXP-018", "purpose": "named corner geometry for the held-out census candidates",
        "source": "PDS Archive Index Table (per-volume INDEX.TAB + INDEX.LBL)",
        "licence": "NASA PDS public domain; credit NASA/GSFC/Arizona State University.",
        "products": records}, indent=2), encoding="utf-8")

    chosen, ladder = ladder_select([r for r in rows if r["admissible"]])
    print(f"\nladder: {[(x['rung_deg'], x['pdsid'], x['incidence_deg']) for x in chosen]}\n")

    # planned manifest (no pixel yet) so the overlap verifier can run from corners
    tiles = []
    for r in chosen:
        w = r["window"]
        tiles.append({"pdsid": r["pdsid"], "line0": w["line0"], "sample0": w["sample0"],
                      "n_lines": w["n_lines"], "n_samples": w["n_samples"], "decimation": w["decimation"],
                      "tile_npy": None, "bytes_sha256": None, "incidence_deg": r["index_incidence_deg"],
                      "emission_deg": r["index_emission_deg"], "ode_map_resolution_m": r["map_resolution_m"],
                      "jacobian_determinant": r["jacobian_determinant"],
                      "jacobian_determinant_sign": r["jacobian_determinant_sign"],
                      "rung_deg": r["rung_deg"], "label_path": r["label_path"]})
    planned.write_text(json.dumps({"stage": "EXP-018", "window": window, "status": "PLANNED -- no pixel fetched",
                                   "target_ground_point_lon_lat": [lon, lat], "tiles": tiles}, indent=2),
                       encoding="utf-8")
    overlap_name = f"overlap_{window}.json"
    s5 = None
    if len(tiles) >= 2:
        cmd = [sys.executable, "scripts/verify_tile_overlap.py", "--manifest", planned.name,
               "--case", f"exp018_{window}", "--role", "EXP-018 held-out window, planned from corners",
               "--extra-geometry", geom_out.name, "--outdir", "EXP-018", "--stage", "EXP-018",
               "--out", overlap_name, "--figure", f"tile_overlap_{window}.png"]
        res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        (OUT / f"overlap_{window}.log").write_text(res.stdout + res.stderr, encoding="utf-8")
        if not (OUT / overlap_name).exists():
            raise SystemExit(f"overlap verification failed:\n{res.stdout[-2000:]}\n{res.stderr[-2000:]}")
        confirmed = _e18._rd07.confirmed_pairs(OUT / overlap_name)
        man = {"tiles": tiles}
        pairs = _e18.geometry_pairs(man, confirmed)
        s5 = _e18.s5_counts(pairs, len(tiles), [t["incidence_deg"] for t in tiles],
                            len(_e18.confirmed_triangles(man, confirmed)))
        s5["confirmed_pairs"] = pairs
        s5["unconfirmed"] = [c["products"] for c in json.loads((OUT / overlap_name).read_text(encoding="utf-8"))["cases"]
                             if c["classification"] != "OVERLAP_CONFIRMED"]
        print(f"S5 from geometry: {'MET' if s5['met'] else 'NOT MET'} {s5['checks']}")
    else:
        print("fewer than 2 admissible frames; S5 NOT MET")
    doc = {"stage": "EXP-018", "window": window, "spec": spec, "separation_km": sep,
           "ode_query": {"pt": "CDRNAC4", "minlat": lat - BOX_HALF_DEG, "maxlat": lat + BOX_HALF_DEG,
                         "westernlon": lon - BOX_HALF_DEG, "easternlon": lon + BOX_HALF_DEG, "limit": 2000},
           "filters": {"incidence_max": INCIDENCE_MAX, "emission_max": EMISSION_MAX,
                       "swath_contains_target": "corner-map inversion, full tile unclamped",
                       "lr_same_orbit": "one frame, lower emission kept",
                       "ladder": list(LADDER), "ladder_half_width": LADDER_HALF_WIDTH, "max_frames": MAX_FRAMES},
           "funnel": funnel, "ladder": ladder, "chosen": chosen, "candidates": rows,
           "s0_untouched": {k: s0[k] for k in ("git_head", "n_files_scanned", "n_files_read",
                                                "hits_per_id", "untouched", "dropped")},
           "s5_from_geometry": s5, "data_read": "ODE metadata, PDS4 labels and index rows only; NO image byte",
           "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "runtime_s": round(time.time() - t0, 1)}
    out_json.write_text(json.dumps(doc, indent=2, default=float), encoding="utf-8")
    print(f"\nwritten: {out_json.relative_to(ROOT)}")
    if s5 is None or not s5["met"]:
        raise SystemExit(3)


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------
def fetch(window: str) -> None:
    planned = DATA / "manifests" / f"exp018_{window}_planned_manifest.json"
    out_path = DATA / "manifests" / f"exp018_{window}_manifest.json"
    if out_path.exists():
        raise SystemExit(f"{out_path.relative_to(ROOT)} exists (integrity rule 4)")
    plan = json.loads(planned.read_text(encoding="utf-8"))
    geometry = json.loads((DATA / "manifests" / f"exp018_{window}_index_geometry.json").read_text(encoding="utf-8"))["products"]
    lon, lat = plan["target_ground_point_lon_lat"]
    out_dir = DATA / "processed" / window
    out_dir.mkdir(parents=True, exist_ok=True)
    entries, log = [], []
    t_all = time.perf_counter()
    for t in plan["tiles"]:
        pdsid = t["pdsid"]
        rec = _acq.ode_record(pdsid)
        prod = _parse_product(rec)
        text = (ROOT / t["label_path"]).read_text(encoding="utf-8")
        struct = parse_image_structure(text)
        byte_start, byte_count = plan_tile_byte_range(struct, line0=t["line0"], n_lines=t["n_lines"])
        npy = out_dir / f"{pdsid}.geo.l{t['line0']}s{t['sample0']}.n{t['n_lines']}.tile.npy"
        if npy.exists():
            raise SystemExit(f"{npy.relative_to(ROOT)} exists; refusing to overwrite")
        print(f"{pdsid}: inc {t['incidence_deg']} lines [{t['line0']}, {t['line0'] + t['n_lines']}) "
              f"samples [{t['sample0']}, {t['sample0'] + t['n_samples']})  {byte_count / 1e6:.1f} MB", flush=True)
        t0 = time.perf_counter()
        raw = fetch_byte_range_chunked(
            prod.image_url, byte_start, byte_count,
            progress=lambda g, tot, _t0=t0: print(f"      {g / 1e6:6.1f}/{tot / 1e6:.1f} MB "
                                                   f"({time.perf_counter() - _t0:.0f}s)", flush=True)
            if g % (16 << 20) < (8 << 20) or g == tot else None)
        digest = hashlib.sha256(raw).hexdigest()
        arr = decode_tile(raw, struct, n_lines=t["n_lines"], sample0=t["sample0"], n_samples=t["n_samples"])
        np.save(npy, np.asarray(arr))
        dt = time.perf_counter() - t0
        log.append({"pdsid": pdsid, "bytes": byte_count, "seconds": round(dt, 1), "kB_per_s": round(byte_count / dt / 1e3, 1)})
        print(f"   {arr.shape} sha256={digest[:16]}... DN median {np.nanmedian(arr):.1f} ({dt:.0f}s)\n", flush=True)
        f = geometry[pdsid]["fields"]
        corners = corners_from_fields(pdsid, f, text)
        entries.append({
            "pdsid": pdsid, "role": "EXP-018 held-out frame", "image_url": prod.image_url,
            "img_file_name": struct.file_name, "byte_start": byte_start, "byte_count": byte_count,
            "bytes_sha256": digest, "line0": t["line0"], "n_lines": t["n_lines"], "sample0": t["sample0"],
            "n_samples": t["n_samples"], "decimation": t["decimation"],
            "parent_shape_lines_samples": [struct.lines, struct.samples],
            "data_type": struct.data_type, "numpy_dtype": struct.numpy_dtype,
            "scaling_factor": struct.scaling_factor, "unit": struct.unit,
            "index_convention": "array[row=line, column=sample], 0-based",
            "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "fetch": "strict 8 MB chunks with retries (fetch_byte_range_chunked)",
            "region": window, "label_path": t["label_path"],
            "tile_npy": str(npy.relative_to(ROOT)).replace("\\", "/"),
            "incidence_deg": t["incidence_deg"], "emission_deg": t["emission_deg"],
            "utc_start": rec.get("UTC_start_time"), "ode_map_resolution_m": t["ode_map_resolution_m"],
            "rung_deg": t["rung_deg"], "jacobian_determinant": t["jacobian_determinant"],
            "jacobian_determinant_sign": t["jacobian_determinant_sign"],
            "selection_method": "EXP-018 Part 1 section 3.5 incidence ladder, from labels and corners only",
            "target_ground_point_lon_lat": [lon, lat],
            "index_geometry_sources": [f"exp018_{window}_index_geometry.json"],
            "index_corners_lon_lat": {"upper_left": list(corners.upper_left), "upper_right": list(corners.upper_right),
                                      "lower_left": list(corners.lower_left), "lower_right": list(corners.lower_right)},
            "lro_flight_direction": f.get("LRO_FLIGHT_DIRECTION"), "orbit_node": f.get("ORBIT_NODE"),
            "geolocation_status": "GEOMETRY-DRIVEN (REAL-DATA-03, D-033): window from named archive corners; "
                                  "not a geographic registration",
            "azimuth_status": "Sub-solar AZIMUTH not used; incidence-varied only (RL-032b)",
        })
    out_path.write_text(json.dumps({
        "dataset": "LRO NAC (LROC) real image tiles via PDS", "stage": "EXP-018", "region": window,
        "pair": [e["pdsid"] for e in entries], "pair_role": "exp018_held_out_window", "window": window,
        "target_ground_point_lon_lat": [lon, lat], "incidence_deg": [e["incidence_deg"] for e in entries],
        "n_mirrored_frames": sum(1 for e in entries if e["jacobian_determinant_sign"] > 0),
        "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fetch_log": log, "total_fetch_s": round(time.perf_counter() - t_all, 1),
        "chandrayaan2_status": "NOT OBTAINED. No Chandrayaan-2 data is present.",
        "licence": "NASA PDS public domain; credit NASA/GSFC/Arizona State University.",
        "tiles": entries}, indent=2), encoding="utf-8")
    print(f"manifest: {out_path.relative_to(ROOT)}  ({len(entries)} tiles, "
          f"{(time.perf_counter() - t_all) / 60:.1f} min)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("census", "fetch"))
    ap.add_argument("--window", choices=sorted(WINDOWS), required=True)
    args = ap.parse_args()
    (census if args.mode == "census" else fetch)(args.window)


if __name__ == "__main__":
    main()
