"""EXP-023: NAC census at the Chandrayaan-3 site (labels + corners only), then fetch.

    python scripts/census_exp023.py census
    python scripts/census_exp023.py fetch

Part 1 section 2.2 (commit d273b8e), applied as written:

* candidates: ODE CDRNAC4 products intersecting a 0.04 deg box around the
  target (32.319 E, -69.373);
* filters in order: (1) a full tile centred on the target fits unclamped
  (EXP-018's tile rule); (2) index emission <= 20 deg; (3) sun-vector
  separation theta <= 10 deg from OHRC obs1's Sun, the NAC Sun computed by
  ``solar_geometry_at`` from the index sub-solar point, guarded by
  ``incidence_agreement`` <= 0.5 deg; (4) L/R of one orbit = one frame (lower
  emission kept);
* tiers theta <= 3, 6, 10; within a tier rank by emission then theta; Na first,
  Nb second (different orbit, same tier or the next);
* overlap before pixels: >= 50 % of a chosen tile's ground inside BOTH refined
  OHRC footprints, else the next-ranked frame;
* nulls (section 2.5): N-a = Na tile displaced 8 km along-track (whichever
  direction fits; else in Nb); N-b = an obs1 window displaced 8 km
  along-track. Non-overlap confirmed from geometry.

Two filters are applied early only because they are implied by the frozen
ones, and the census records them as such: ODE emission > 20 (confirmed from
the index before a frame is dropped for it), and |ODE incidence - 78.476| > 11,
since theta >= |delta incidence| and the ODE value is at the frame centre (a
1 deg margin covers centre-to-target).

The census reads ODE metadata, PDS4 labels and archive index rows. It reads
NO image byte. ``fetch`` reads image bytes for the tiles the census planned.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import importlib.util
import json
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
from siim.ingest.ohrc import OhrcGrid, parse_ohrc_label  # noqa: E402
from siim.ingest.orientation import handedness  # noqa: E402
from siim.ingest.solar_geometry import incidence_agreement, solar_geometry_at  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_acq = _load("_acq", ROOT / "scripts" / "acquire_real_pair.py")
_geo = _load("_geo", ROOT / "scripts" / "fetch_index_geometry.py")

STAGE = "EXP-023"
DATA = ROOT / "data"
OUT = ROOT / "experiments" / STAGE
REGION = "chandrayaan3_site"
TARGET = (32.319, -69.373)
BOX_HALF_DEG = 0.02
EMISSION_MAX = 20.0
TIERS = (3.0, 6.0, 10.0)
INCIDENCE_GUARD_DEG = 0.5
OVERLAP_MIN = 0.50
NULL_KM = 8.0
PREFILTER_INC_MARGIN = 1.0
#: Pause between archive requests. Attempt 1 ran unpaced and 67 of 95 candidates were
#: refused with HTTP 429 (E-061); the pause and the backoff in polite_get are harness
#: changes only -- no frozen rule depends on them.
PACE_S = 3.0
DEFAULT = {"n_lines": 4096, "n_samples": 2048, "decimation": 2}
FINE = {"n_lines": 8192, "n_samples": 4096, "decimation": 4}
FINE_BELOW_M = 0.6

OHRC_DIRS = {"O1": "realdata/realdata/OHRC/obs1", "O2": "realdata/realdata/OHRC/obs2"}


def ohrc(obs: str):
    base = ROOT / OHRC_DIRS[obs]
    xml = Path(glob.glob(str(base / "*" / "data" / "calibrated" / "*" / "*d_img*.xml"))[0])
    grd = Path(glob.glob(str(base / "*" / "geometry" / "calibrated" / "*" / "*g_grd*.csv"))[0])
    return parse_ohrc_label(xml.read_text(encoding="utf-8")), OhrcGrid.from_csv(grd), xml, grd


def sun_separation_deg(i1, az1, i2, az2) -> float:
    i1, az1, i2, az2 = map(np.deg2rad, (i1, az1, i2, az2))
    c = np.cos(i1) * np.cos(i2) + np.sin(i1) * np.sin(i2) * np.cos(az1 - az2)
    return float(np.rad2deg(np.arccos(np.clip(c, -1.0, 1.0))))


def corners_from_fields(pdsid: str, fields: dict, label_text: str) -> FrameCorners:
    disp = parse_display_direction(label_text)
    if (disp["vertical_axis"], disp["vertical_direction"]) != ("Line", "Top to Bottom") or \
            (disp["horizontal_axis"], disp["horizontal_direction"]) != ("Sample", "Left to Right"):
        raise ValueError(f"{pdsid}: unexpected Display_Direction {disp}")

    def c(name):
        return (float(fields[name + "_LONGITUDE"]), float(fields[name + "_LATITUDE"]))

    return FrameCorners(c("UPPER_LEFT"), c("UPPER_RIGHT"), c("LOWER_LEFT"), c("LOWER_RIGHT"),
                        int(fields["IMAGE_LINES"]), int(fields["LINE_SAMPLES"]))


def tile_lonlat(corners: FrameCorners, line0, sample0, n_lines, n_samples, n=21):
    ls = np.linspace(line0, line0 + n_lines - 1, n)
    ss = np.linspace(sample0, sample0 + n_samples - 1, n)
    L, S = np.meshgrid(ls, ss, indexing="ij")
    pts = [corners.lonlat_at(float(a), float(b)) for a, b in zip(L.ravel(), S.ravel())]
    return np.array(pts)


def fraction_inside(lonlat: np.ndarray, fc: FrameCorners) -> float:
    inside = 0
    for lo, la in lonlat:
        try:
            fc.pixel_at(float(lo), float(la))
            inside += 1
        except ValueError:
            pass
    return inside / len(lonlat)


def fraction_inside_tile(lonlat: np.ndarray, corners: FrameCorners, t: dict) -> float:
    inside = 0
    for lo, la in lonlat:
        try:
            line, sample = corners.pixel_at(float(lo), float(la))
        except ValueError:
            continue
        if t["line0"] <= line <= t["line0"] + t["n_lines"] - 1 and \
                t["sample0"] <= sample <= t["sample0"] + t["n_samples"] - 1:
            inside += 1
    return inside / len(lonlat)


def is_transport_error(exc: BaseException) -> bool:
    """True for failures of the network or the archive, which are NOT section 2.2 outcomes.

    Attempt 1 recorded 67 HTTP-429 refusals as exclusions (E-061). A frame the
    census could not read is *unresolved*, never *excluded*.
    """
    import requests
    text = f"{type(exc).__name__}: {exc}"
    return (isinstance(exc, requests.RequestException)
            or "failed after" in text or "still refused" in text
            or any(k in text for k in ("429", "Too Many Requests", "ConnectionError", "Timeout",
                                       "RemoteDisconnected")))


def gc_m(a, b, radius_m: float = 1737400.0) -> float:
    lon1, lat1, lon2, lat2 = map(np.deg2rad, (a[0], a[1], b[0], b[1]))
    hv = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return float(2 * radius_m * np.arcsin(np.sqrt(hv)))


def metres_per_line(corners: FrameCorners, line: float, sample: float, step: float = 1000.0) -> float:
    """Along-track ground distance of one frame line, from the frame's own corner map."""
    l2 = line + step if line + step <= corners.lines - 1 else line - step
    return gc_m(corners.lonlat_at(line, sample), corners.lonlat_at(l2, sample)) / step


def ohrc_window_box(grid: OhrcGrid, nac_corners: FrameCorners, tile: dict, shift_scans: int = 0,
                    n: int = 9, margin: float = 0.05) -> dict:
    """Part 1 section 2.1: the ground rectangle of a NAC tile's footprint in OHRC
    scan/pixel, with a 5 % margin, THEN clipped to the swath.

    Every footprint node is inverted on the grid extended linearly past its
    edge (``allow_outside``), so a footprint that crosses the swath edge gives
    a rectangle that is clipped there rather than one that silently shrinks
    (the defect the pre-run review found in the first runner draft).
    ``shift_scans`` moves the rectangle along-track for the N-b null.
    """
    ls = np.linspace(tile["line0"], tile["line0"] + tile["n_lines"] - 1, n)
    ss = np.linspace(tile["sample0"], tile["sample0"] + tile["n_samples"] - 1, n)
    sp = np.array([grid.pixel_at(*nac_corners.lonlat_at(float(a), float(b)), allow_outside=True)
                   for a in ls for b in ss])
    s_lo, s_hi = sp[:, 0].min() + shift_scans, sp[:, 0].max() + shift_scans
    p_lo, p_hi = sp[:, 1].min(), sp[:, 1].max()
    ms, mp = margin * (s_hi - s_lo), margin * (p_hi - p_lo)
    s_max, p_max = grid.extent
    s0, s1 = int(np.floor(s_lo - ms)), int(np.ceil(s_hi + ms)) + 1
    p0, p1 = int(np.floor(p_lo - mp)), int(np.ceil(p_hi + mp)) + 1
    unclipped = {"scan0": s0, "scan1": s1, "pixel0": p0, "pixel1": p1}
    box = {"scan0": max(0, s0), "scan1": min(int(s_max) + 1, s1),
           "pixel0": max(0, p0), "pixel1": min(int(p_max) + 1, p1)}
    shifted = sp[:, 0] + shift_scans
    inside = int(np.sum((shifted >= 0) & (shifted <= s_max) & (sp[:, 1] >= 0) & (sp[:, 1] <= p_max)))
    if box["scan1"] - box["scan0"] < 16 or box["pixel1"] - box["pixel0"] < 16:
        raise ValueError(f"window {box} is empty after clipping to the swath")
    return dict(box, unclipped=unclipped, footprint_nodes_inside_swath=inside, footprint_nodes=n * n,
                shift_scans=int(shift_scans))


def box_overlap_with_tile(grid: OhrcGrid, box: dict, nac_corners: FrameCorners, tile: dict, n: int = 11) -> float:
    """Fraction of an OHRC box's ground (n x n nodes) that falls inside a NAC tile."""
    ss = np.linspace(box["scan0"], box["scan1"] - 1, n)
    ps = np.linspace(box["pixel0"], box["pixel1"] - 1, n)
    ll = np.array([grid.lonlat_at(float(a), float(b)) for a in ss for b in ps])
    return fraction_inside_tile(ll, nac_corners, tile)


def census() -> None:
    out_json = OUT / "census.json"
    planned = DATA / "manifests" / "exp023_planned_manifest.json"
    geom_out = DATA / "manifests" / "exp023_index_geometry.json"
    for p in (out_json, planned, geom_out):
        if p.exists():
            raise SystemExit(f"{p.relative_to(ROOT)} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    lon, lat = TARGET
    L1, G1, _, _ = ohrc("O1")
    L2, G2, _, _ = ohrc("O2")
    i_o, az_o = L1.solar_incidence_deg, L1.sun_azimuth_deg
    fp = {"O1": L1.corners("refined"), "O2": L2.corners("refined")}
    print(f"== EXP-023 census: target ({lon}, {lat}); OHRC obs1 Sun i={i_o} az={az_o} ==\n")

    prods = query_nac(min_lat=lat - BOX_HALF_DEG, max_lat=lat + BOX_HALF_DEG,
                      min_lon=lon - BOX_HALF_DEG, max_lon=lon + BOX_HALF_DEG, limit=2000)
    print(f"ODE returned {len(prods)} CDRNAC4 products intersecting the 0.04 deg box\n")
    funnel = {"ode_returned": len(prods)}
    rows = []
    for p in prods:
        r = {"pdsid": p.pdsid, "ode_incidence_deg": p.incidence_deg, "ode_emission_deg": p.emission_deg,
             "map_resolution_m": p.map_resolution_m, "utc_start": p.utc_start, "admissible": True}
        if p.incidence_deg is None:
            r.update(admissible=False, rejected_by="no incidence (night or absent)")
        elif abs(p.incidence_deg - i_o) > TIERS[-1] + PREFILTER_INC_MARGIN:
            r.update(admissible=False, rejected_by=f"implied by theta <= {TIERS[-1]}: |ODE incidence - {i_o}| "
                                                   f"> {TIERS[-1] + PREFILTER_INC_MARGIN}")
        elif p.emission_deg is not None and p.emission_deg > EMISSION_MAX + 1.0:
            r.update(admissible=False, rejected_by=f"ODE emission > {EMISSION_MAX + 1.0} (index would fail too)")
        rows.append(r)
    funnel["after_implied_prefilter"] = sum(r["admissible"] for r in rows)
    prod_by_id = {p.pdsid: p for p in prods}
    ids = [r["pdsid"] for r in rows if r["admissible"]]
    print(f"fetching labels + index rows for {len(ids)} candidates ...", flush=True)
    vols: dict = {}
    for pdsid in ids:
        try:
            vols.update(_geo.volumes_from_ode([pdsid]))
        except (SystemExit, Exception) as exc:  # noqa: BLE001 -- recorded per frame
            vols[pdsid] = {"error": f"{type(exc).__name__}: {exc}"}
        time.sleep(PACE_S)
    records: dict = {}
    for r in rows:
        if not r["admissible"]:
            continue
        pdsid = r["pdsid"]
        try:
            if "error" in vols.get(pdsid, {"error": "no ODE volume"}):
                err = vols.get(pdsid, {}).get("error", "no ODE volume")
                if any(k in err for k in ("429", "Too Many Requests", "still refused", "failed after",
                                          "ConnectionError", "Timeout")):
                    raise RuntimeError(f"ODE volume lookup failed after retries: {err}")
                raise ValueError(err)
            lbl = fetch_label(prod_by_id[pdsid], DATA / "metadata" / REGION)
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
            ssl, sslat = float(f["SUB_SOLAR_LONGITUDE"]), float(f["SUB_SOLAR_LATITUDE"])
            g = solar_geometry_at(lon, lat, ssl, sslat)
            rec_c, diff_c = incidence_agreement(float(f["CENTER_LONGITUDE"]), float(f["CENTER_LATITUDE"]),
                                                ssl, sslat, float(f["INCIDENCE_ANGLE"]))
            theta = sun_separation_deg(g.incidence_deg, g.azimuth_deg, i_o, az_o)
            r.update({"index_incidence_deg": float(f["INCIDENCE_ANGLE"]),
                      "index_emission_deg": float(f["EMISSION_ANGLE"]),
                      "index_resolution_m": float(f["RESOLUTION"]),
                      "scaled_pixel_m": 0.5 * (float(f["SCALED_PIXEL_WIDTH"]) + float(f["SCALED_PIXEL_HEIGHT"])),
                      "incidence_at_target_deg": g.incidence_deg, "azimuth_at_target_deg": g.azimuth_deg,
                      "incidence_guard": {"recomputed_at_centre_deg": rec_c, "difference_deg": diff_c},
                      "sun_separation_deg": theta, "slew_angle_deg": f.get("SLEW_ANGLE"),
                      "start_time": f.get("START_TIME"), "orbit_number": f.get("ORBIT_NUMBER"),
                      "lines_samples": [corners.lines, corners.samples],
                      "window": dict(win, line0=line0, sample0=sample0), "window_detail": detail,
                      "label_path": str(lbl.relative_to(ROOT)).replace("\\", "/")})
            if not detail["fully_inside_frame"]:
                r.update(admissible=False, rejected_by="(1) a full tile centred on the target does not fit unclamped")
            elif float(f["EMISSION_ANGLE"]) > EMISSION_MAX:
                r.update(admissible=False, rejected_by=f"(2) index emission > {EMISSION_MAX}")
            elif abs(diff_c) > INCIDENCE_GUARD_DEG:
                r.update(admissible=False, rejected_by=f"(3) incidence_agreement {diff_c:+.3f} deg > {INCIDENCE_GUARD_DEG}")
            elif theta > TIERS[-1]:
                r.update(admissible=False, rejected_by=f"(3) sun-vector separation {theta:.2f} > {TIERS[-1]}")
            else:
                r["jacobian_determinant"] = handedness(corners, line0 + (win["n_lines"] - 1) / 2,
                                                       sample0 + (win["n_samples"] - 1) / 2)
                r["_corners"] = corners
        except Exception as exc:  # noqa: BLE001 -- recorded; nothing guessed
            if is_transport_error(exc):
                r.update(admissible=False, unresolved=f"{type(exc).__name__}: {exc}", rejected_by=None)
            else:
                r.update(admissible=False, rejected_by=f"{type(exc).__name__}: {exc}")
        time.sleep(PACE_S)
        print(f"   {pdsid}: inc {r.get('incidence_at_target_deg', r['ode_incidence_deg'])!s:.6} "
              f"az {r.get('azimuth_at_target_deg', '-')!s:.6} em {r.get('index_emission_deg', r['ode_emission_deg'])} "
              f"theta {r.get('sun_separation_deg', '-')!s:.5} -> "
              f"{'ADMISSIBLE' if r['admissible'] else (r.get('rejected_by') or 'UNRESOLVED ' + r.get('unresolved', ''))[:70]}",
              flush=True)
    unresolved = [r for r in rows if r.get("unresolved")]
    if unresolved:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        inc = OUT / f"census_incomplete_{stamp}.json"
        inc.write_text(json.dumps({"stage": STAGE, "status": "INCOMPLETE -- frozen artefacts NOT written",
                                   "funnel_so_far": funnel, "n_unresolved": len(unresolved),
                                   "unresolved": [{"pdsid": r["pdsid"], "error": r["unresolved"][:300]}
                                                  for r in unresolved],
                                   "candidates": [{k: v for k, v in r.items() if k != "_corners"} for r in rows]},
                                  indent=2, default=float), encoding="utf-8")
        raise SystemExit(f"{len(unresolved)} candidate(s) unresolved by transport errors; wrote "
                         f"{inc.relative_to(ROOT)} and refused to write census.json (E-061)")
    funnel["after_containment_emission_theta"] = sum(r["admissible"] for r in rows)
    by_orbit: dict = {}
    for r in rows:
        if r["admissible"]:
            by_orbit.setdefault(r["pdsid"][:-2], []).append(r)
    for grp in by_orbit.values():
        keep = min(grp, key=lambda r: (r["index_emission_deg"], r["pdsid"]))
        for r in grp:
            if r is not keep:
                r.update(admissible=False, rejected_by=f"(4) L/R of one orbit: {keep['pdsid']} kept (lower emission)")
    funnel["after_lr_dedupe"] = sum(r["admissible"] for r in rows)

    # tiers, ranking, overlap before pixels
    adm = [r for r in rows if r["admissible"]]
    for r in adm:
        r["tier"] = next(k for k, t in enumerate(TIERS) if r["sun_separation_deg"] <= t)
        w = r["window"]
        ll = tile_lonlat(r["_corners"], w["line0"], w["sample0"], w["n_lines"], w["n_samples"])
        r["overlap_fraction"] = {k: fraction_inside(ll, fc) for k, fc in fp.items()}
    ranked = sorted(adm, key=lambda r: (r["tier"], r["index_emission_deg"], r["sun_separation_deg"], r["pdsid"]))
    chosen, log = [], []
    for r in ranked:
        ok = min(r["overlap_fraction"].values()) >= OVERLAP_MIN
        log.append({"pdsid": r["pdsid"], "tier": r["tier"], "emission": r["index_emission_deg"],
                    "theta": r["sun_separation_deg"], "overlap_fraction": r["overlap_fraction"],
                    "taken": False, "why": None})
        if not ok:
            log[-1]["why"] = f"overlap < {OVERLAP_MIN} against an OHRC footprint"
            continue
        if not chosen:
            chosen.append(r)
            log[-1].update(taken=True, why="Na: first-ranked with confirmed overlap")
        elif len(chosen) == 1 and r["tier"] <= chosen[0]["tier"] + 1:
            chosen.append(r)
            log[-1].update(taken=True, why="Nb: second, different orbit, same or next tier")
            break
    roles = dict(zip(("Na", "Nb"), chosen))
    print(f"\nchosen: {[(k, v['pdsid'], round(v['sun_separation_deg'], 2), v['index_emission_deg']) for k, v in roles.items()]}")

    # nulls (section 2.5): displacement measured from each frame's own geometry, non-overlap
    # checked over the whole window and ENFORCED -- a null that overlaps is not placed.
    nulls = {}
    if "Na" in roles:
        na = roles["Na"]
        box_o1 = ohrc_window_box(G1, na["_corners"], na["window"])
        order = [roles["Na"]] + ([roles["Nb"]] if "Nb" in roles else [])
        tried = []
        for fr in order:
            c, w = fr["_corners"], fr["window"]
            lc, sc = w["line0"] + (w["n_lines"] - 1) / 2, w["sample0"] + (w["n_samples"] - 1) / 2
            mpl = metres_per_line(c, lc, sc)
            dl = int(round(NULL_KM * 1000.0 / mpl))
            for sign in (+1, -1):
                l0 = w["line0"] + sign * dl
                if not (0 <= l0 and l0 + w["n_lines"] <= c.lines):
                    tried.append({"pdsid": fr["pdsid"], "sign": sign, "why": "does not fit the frame unclamped"})
                    continue
                t = dict(w, line0=l0)
                ll = tile_lonlat(c, t["line0"], t["sample0"], t["n_lines"], t["n_samples"], n=11)
                ov = 0
                for lo_, la_ in ll:
                    try:
                        sc_, pc_ = G1.pixel_at(float(lo_), float(la_))
                    except ValueError:
                        continue
                    ov += int(box_o1["scan0"] <= sc_ < box_o1["scan1"] and box_o1["pixel0"] <= pc_ < box_o1["pixel1"])
                frac = ov / len(ll)
                centre = c.lonlat_at(lc + sign * dl, sc)
                realised = gc_m(c.lonlat_at(lc, sc), centre)
                if frac > 0:
                    tried.append({"pdsid": fr["pdsid"], "sign": sign, "why": f"overlaps the O1 window ({frac:.3f})"})
                    continue
                nulls["N-a"] = {"pdsid": fr["pdsid"], "window": t, "displacement_lines": sign * dl,
                                "metres_per_line": mpl, "displacement_km_nominal": sign * NULL_KM,
                                "displacement_km_realised": realised / 1000.0,
                                "overlap_with_o1_window": frac, "non_overlap_confirmed": True,
                                "centre_lonlat": list(centre)}
                break
            if "N-a" in nulls:
                break
        if "N-a" not in nulls:
            nulls["N-a"] = {"status": "NOT PLACED", "tried": tried}
        s_t, p_t = G1.pixel_at(lon, lat)
        m_scan, _ = G1.metres_per_step(s_t, p_t)
        ds = int(round(NULL_KM * 1000.0 / m_scan))
        for sign in (+1, -1):
            try:
                box = ohrc_window_box(G1, na["_corners"], na["window"], shift_scans=sign * ds)
            except ValueError:
                continue
            if box["unclipped"]["scan0"] < 0 or box["unclipped"]["scan1"] > G1.extent[0] + 1:
                continue
            frac = box_overlap_with_tile(G1, box, na["_corners"], na["window"])
            if frac > 0:
                continue
            c0 = G1.lonlat_at((box["scan0"] + box["scan1"] - 1) / 2, (box["pixel0"] + box["pixel1"] - 1) / 2)
            nulls["N-b"] = {"obs": "O1", "box": box, "displacement_scans": sign * ds, "metres_per_scan": m_scan,
                            "displacement_km_nominal": sign * NULL_KM,
                            "displacement_km_realised": gc_m(G1.lonlat_at(s_t, p_t),
                                                             G1.lonlat_at(s_t + sign * ds, p_t)) / 1000.0,
                            "overlap_with_na_tile": frac, "non_overlap_confirmed": True, "centre_lonlat": list(c0)}
            break
        if "N-b" not in nulls:
            nulls["N-b"] = {"status": "NOT PLACED"}

    for r in rows:
        r.pop("_corners", None)
    geom_out.write_text(json.dumps({
        "stage": STAGE, "purpose": "named corner geometry and sub-solar points for the EXP-023 census candidates",
        "source": "PDS Archive Index Table (per-volume INDEX.TAB + INDEX.LBL)",
        "licence": "NASA PDS public domain; credit NASA/GSFC/Arizona State University.",
        "products": records}, indent=2), encoding="utf-8")
    tiles = []
    for role, r in roles.items():
        w = r["window"]
        tiles.append({"role": role, "pdsid": r["pdsid"], **{k: w[k] for k in ("line0", "sample0", "n_lines",
                                                                              "n_samples", "decimation")},
                      "tile_npy": None, "incidence_deg": r["index_incidence_deg"],
                      "incidence_at_target_deg": r["incidence_at_target_deg"],
                      "azimuth_at_target_deg": r["azimuth_at_target_deg"], "sun_separation_deg": r["sun_separation_deg"],
                      "emission_deg": r["index_emission_deg"], "ode_map_resolution_m": r["map_resolution_m"],
                      "jacobian_determinant": r["jacobian_determinant"], "label_path": r["label_path"],
                      "start_time": r["start_time"]})
    if nulls.get("N-a", {}).get("non_overlap_confirmed"):
        n = nulls["N-a"]
        src = next(r for r in rows if r["pdsid"] == n["pdsid"])
        tiles.append({"role": "N-a", "pdsid": n["pdsid"], **{k: n["window"][k] for k in ("line0", "sample0", "n_lines",
                                                                                         "n_samples", "decimation")},
                      "tile_npy": None, "incidence_deg": src["index_incidence_deg"],
                      "emission_deg": src["index_emission_deg"], "ode_map_resolution_m": src["map_resolution_m"],
                      "jacobian_determinant": src["jacobian_determinant"], "label_path": src["label_path"],
                      "start_time": src["start_time"]})
    planned.write_text(json.dumps({"stage": STAGE, "status": "PLANNED -- no pixel fetched",
                                   "target_ground_point_lon_lat": list(TARGET), "tiles": tiles}, indent=2),
                       encoding="utf-8")
    primary = ["O1", "Na", "Nb"] if "Nb" in roles else (["O1", "O2", "Na"] if "Na" in roles else None)
    doc = {"stage": STAGE, "preregistration": "docs/stages/EXP-023_ohrc_nac_chandrayaan3_site.md Part 1 (d273b8e)",
           "target_lon_lat": list(TARGET),
           "ohrc_sun": {"incidence_deg": i_o, "azimuth_deg": az_o, "source": "obs1 label, azimuth read clockwise from north"},
           "ode_query": {"pt": "CDRNAC4", "minlat": lat - BOX_HALF_DEG, "maxlat": lat + BOX_HALF_DEG,
                         "westernlon": lon - BOX_HALF_DEG, "easternlon": lon + BOX_HALF_DEG, "limit": 2000},
           "filters": {"emission_max": EMISSION_MAX, "tiers_deg": list(TIERS), "incidence_guard_deg": INCIDENCE_GUARD_DEG,
                       "overlap_min": OVERLAP_MIN, "null_km": NULL_KM,
                       "implied_prefilter": f"|ODE incidence - {i_o}| > {TIERS[-1] + PREFILTER_INC_MARGIN}; "
                                            f"ODE emission > {EMISSION_MAX + 1.0}"},
           "funnel": funnel, "ranking_log": log, "roles": {k: v["pdsid"] for k, v in roles.items()},
           "primary_triangle": primary, "nulls": nulls, "candidates": rows,
           "data_read": "ODE metadata, PDS4 labels and index rows only; NO image byte",
           "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "runtime_s": round(time.time() - t0, 1)}
    out_json.write_text(json.dumps(doc, indent=2, default=float), encoding="utf-8")
    print(f"primary triangle: {primary}\nnulls: {json.dumps(nulls, default=float)[:600]}\nwritten: {out_json.relative_to(ROOT)}")
    if not roles:
        raise SystemExit(3)


def fetch() -> None:
    planned = DATA / "manifests" / "exp023_planned_manifest.json"
    out_path = DATA / "manifests" / "exp023_manifest.json"
    if out_path.exists():
        raise SystemExit(f"{out_path.relative_to(ROOT)} exists (integrity rule 4)")
    plan = json.loads(planned.read_text(encoding="utf-8"))
    out_dir = DATA / "processed" / REGION
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
        print(f"{t['role']} {pdsid}: lines [{t['line0']}, {t['line0'] + t['n_lines']}) samples "
              f"[{t['sample0']}, {t['sample0'] + t['n_samples']})  {byte_count / 1e6:.1f} MB", flush=True)
        t0 = time.perf_counter()
        raw = fetch_byte_range_chunked(
            prod.image_url, byte_start, byte_count,
            progress=lambda g, tot, _t0=t0: print(f"      {g / 1e6:6.1f}/{tot / 1e6:.1f} MB "
                                                   f"({time.perf_counter() - _t0:.0f}s)", flush=True)
            if g % (32 << 20) < (8 << 20) or g == tot else None)
        digest = hashlib.sha256(raw).hexdigest()
        arr = decode_tile(raw, struct, n_lines=t["n_lines"], sample0=t["sample0"], n_samples=t["n_samples"])
        np.save(npy, np.asarray(arr))
        dt = time.perf_counter() - t0
        log.append({"role": t["role"], "pdsid": pdsid, "bytes": byte_count, "seconds": round(dt, 1)})
        print(f"   {arr.shape} sha256={digest[:16]}... DN median {np.nanmedian(arr):.4g} ({dt:.0f}s)\n", flush=True)
        entries.append(dict(t, image_url=prod.image_url, img_file_name=struct.file_name, byte_start=byte_start,
                            byte_count=byte_count, bytes_sha256=digest,
                            parent_shape_lines_samples=[struct.lines, struct.samples],
                            data_type=struct.data_type, numpy_dtype=struct.numpy_dtype,
                            index_convention="array[row=line, column=sample], 0-based",
                            tile_npy=str(npy.relative_to(ROOT)).replace("\\", "/"),
                            retrieved_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            utc_start=rec.get("UTC_start_time"),
                            geolocation_status="GEOMETRY-DRIVEN (D-033): window from named archive corners"))
    out_path.write_text(json.dumps({
        "dataset": "LRO NAC (LROC) real image tiles via PDS", "stage": STAGE, "region": REGION,
        "target_ground_point_lon_lat": list(TARGET), "fetch_log": log,
        "total_fetch_s": round(time.perf_counter() - t_all, 1),
        "licence": "NASA PDS public domain; credit NASA/GSFC/Arizona State University.",
        "tiles": entries}, indent=2), encoding="utf-8")
    print(f"manifest: {out_path.relative_to(ROOT)} ({len(entries)} tiles, {(time.perf_counter() - t_all) / 60:.1f} min)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("census", "fetch"))
    args = ap.parse_args()
    (census if args.mode == "census" else fetch)()


if __name__ == "__main__":
    main()
