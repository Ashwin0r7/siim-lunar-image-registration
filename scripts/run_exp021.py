"""EXP-021 — verdict false acceptance and false rejection, run exactly as
Part 1 froze it (docs/stages/EXP-021_verdict_fa_fr.md).

For every recorded directed edge whose two frames reach a Kaguya TC reference,
the composition ``G_AB = T_B^-1 o T_A`` -- correspondences A<->R and B<->R
only, never A<->B -- labels the recorded direct transform CORRECT (<= 1.0
reference px), AMBIGUOUS, WRONG (> 3.0) or NO ESTIMATE. The shipped verdict is
then scored against that label at two levels:

    L1  acceptance at the edge: the recorded ``pass`` (n_inliers > 8, D-023)
    L2  VERIFIED: the edge sits in a triangle of three passing recorded edges
        whose loop closure is < 2.0 px (EXP-012's population and rule)

on a calibration site (Serenitatis, EXP-019's recorded legs, rebuilt) and a
validation site (Tranquillitatis, legs measured here against a Kaguya tile
fetched after Part 1 was committed).

Nothing is re-implemented: the legs are ``scripts/run_exp019.py``'s
construction imported unchanged (``prepare_nac``, ``register_against``,
``nac_matching_px_to_frame``, ``s0_grid_gate``, ``s3_pairs``), loop closure is
``siim.evaluation.gtfree.loop_closure`` at step 16, and every rate is a count.
No recorded direct edge is re-matched.

    python scripts/run_exp021.py
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scipy.stats import beta  # noqa: E402

from siim.evaluation.gtfree import loop_closure  # noqa: E402
from siim.geometry import Transform, pixel_grid  # noqa: E402
from siim.ingest.footprint import TileWindow  # noqa: E402
from siim.ingest.mapgrid import load_map_block  # noqa: E402
from siim.ingest.orientation import handedness, north_up_east_right  # noqa: E402


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_e19 = _load("_exp019", "scripts/run_exp019.py")
_e7 = _e19._e7

STAGE = "EXP-021"
PREREG = "docs/stages/EXP-021_verdict_fa_fr.md Part 1"
DATA = ROOT / "data"
OUT = ROOT / "experiments" / STAGE
REF_GSD_M = _e19.REF_GSD_M
K2 = _e19.K2
RULE = 8                                               # n_inliers <= 8 fails (D-023)
LOOP_REJECT_PX = 2.0                                   # verdict.LOOP_ERROR_REJECT_PX
LOOP_STEP = 16
ENGINES = ("b1", "lg", "xf")
ENGINE_NAME = {"b1": "B1", "lg": "B4L", "xf": "B4X"}
PRIMARY = "b1"

# --- frozen constants, Part 1 sections 2 and 4 ------------------------------
CORRECT_REF_PX = 1.0
WRONG_REF_PX = 3.0
LEG_AGREE_REF_PX = 0.5
LEG_GRID_STEP = 64
CLASS_GRID_STEP = 8
MIN_GT_GRID = 100
FA_LINE = 0.05
FA_WITHDRAW_LINE = 0.10                                # SS54, bound in Part 1 SS0.2
FR_LINE = 0.20
S1_MIN_V_FRAMES = 4
S1_MIN_V_B1_EDGES = 6
S2_MIN_VERIFIED = 10
S3_MIN_CORRECT = 10
S4_C_RANGE = (3, 50)
S4_MIN_WRONG_C = 5
S4_MIN_WRONG_V = 3
S4_MIN_CORRECT_V = 10
S6_MIN_HARD_NEG = 3
S0_TOL_PX = 1e-6
DRIFT_GATE = ("RD03/nac.m1271742202lc", 253)
S5_VARIANTS = {
    "tolerance_0.5": {"correct": 0.5, "wrong": 1.5, "tier": "A"},
    "tolerance_2.0": {"correct": 2.0, "wrong": 6.0, "tier": "A"},
    "tier_A_or_B": {"correct": 1.0, "wrong": 3.0, "tier": "AB"},
    "b1_legs_only": {"correct": 1.0, "wrong": 3.0, "tier": "B1"},
}

C_ROWS = {"RD03": "experiments/REAL-DATA-07/rows_rd03_nue.json",
          "RD04": "experiments/REAL-DATA-07/rows_rd04_nue.json"}
V_ROWS = "experiments/EXP-018/rows_tranquillitatis_nue.json"
V_WINDOW = "tranquillitatis"
V_REF_MANIFEST = "exp021_tc_ortho_ref_block.json"
V_NULL_MANIFEST = "exp021_tc_ortho_null_block.json"


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def clopper_pearson(k: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    lo = 0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(0.975, k + 1, n - k))
    return [lo, hi]


def rate(k: int, n: int) -> dict:
    return {"k": int(k), "n": int(n), "rate": (k / n) if n else None,
            "ci95": clopper_pearson(k, n)}


def _tf(m) -> Transform:
    """A recorded 3x3 matrix as a Transform. The pipeline's model selection can
    return a homography (first run died on a 4-inlier leg whose bottom row was
    [4.7e-05, -3.2e-06, 1]); the model is read from the matrix, not assumed."""
    a = np.asarray(m, float)
    affine = np.allclose(a[2], [0.0, 0.0, 1.0], atol=1e-12, rtol=0.0)
    return Transform(a, "affine" if affine else "projective")


def _strip(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if not k.startswith("_")}


# ---------------------------------------------------------------------------
# legs: frame -> reference, in the k2 tile frame
# ---------------------------------------------------------------------------
def k2_map(s, measured: Transform) -> tuple[Transform, list[int]]:
    """k2-tile px -> reference px, from a measured matching-px -> block-px map."""
    t = s.ctx.tile
    win2 = TileWindow(t["line0"], t["sample0"], t["n_lines"], t["n_samples"], K2)
    frame_to_ref = measured @ _e19.nac_matching_px_to_frame(s).inverse()
    return frame_to_ref @ _e19._tile_px_to_frame(win2), list(win2.shape)


def leg_agreement(s, m1: Transform, m2: Transform) -> float:
    grid = pixel_grid(s.image.shape, step=LEG_GRID_STEP)
    return float(np.median(np.linalg.norm(m1.apply(grid) - m2.apply(grid), axis=1)))


def frame_record(s, b1: dict | None, b4l: dict | None) -> dict:
    """Everything the classification needs about one frame's two legs."""
    rec = {"key": s.key, "window": s.window, "frame": s.name, "k": s.k,
           "native_gsd_m": s.ctx.scaled_pixel_m,
           "incidence_deg": s.ctx.incidence_published,
           "b1_n_inliers": (b1 or {}).get("n_inliers", 0),
           "b1_pass": bool((b1 or {}).get("pass")),
           "b4l_n_inliers": (b4l or {}).get("n_inliers", 0),
           "b4l_pass": bool((b4l or {}).get("pass")),
           "leg_agreement_ref_px": None}
    m1 = _tf(b1["measured_to_block_matrix"]) if b1 and b1.get("measured_to_block_matrix") else None
    m2 = (_tf(b4l["measured_to_block_matrix"])
          if b4l and b4l.get("measured_to_block_matrix") else None)
    if m1 is not None:
        rec["_k2_b1"], rec["_k2_shape"] = k2_map(s, m1)
    if m2 is not None:
        rec["_k2_b4l"], rec["_k2_shape"] = k2_map(s, m2)
    if m1 is not None and m2 is not None:
        rec["leg_agreement_ref_px"] = leg_agreement(s, m1, m2)
    agree = rec["leg_agreement_ref_px"]
    rec["tier_A"] = bool(rec["b1_pass"] and rec["b4l_pass"] and agree is not None
                         and agree <= LEG_AGREE_REF_PX)
    rec["tier_B"] = bool(rec["b4l_pass"] and not rec["tier_A"])
    t = s.ctx.tile
    line_c = t["line0"] + (t["n_lines"] - 1) / 2
    sample_c = t["sample0"] + (t["n_samples"] - 1) / 2
    rec["handedness_det"] = float(handedness(s.ctx.corners, line_c, sample_c))
    nu2 = north_up_east_right(np.zeros((t["n_lines"] // K2, t["n_samples"] // K2), np.float32),
                              s.ctx.corners, line=line_c, sample=sample_c)
    rec["northup_k2_shape"] = list(nu2.image.shape)
    return rec


def gt_leg(fr: dict, tier: str) -> Transform | None:
    """The leg a variant admits for this frame, or None."""
    if tier == "A":
        return fr.get("_k2_b1") if fr["tier_A"] else None
    if tier == "AB":
        if fr["tier_A"]:
            return fr.get("_k2_b1")
        return fr.get("_k2_b4l") if fr["tier_B"] else None
    if tier == "B1":
        return fr.get("_k2_b1") if fr["b1_pass"] else None
    raise ValueError(tier)


# ---------------------------------------------------------------------------
# recorded rows
# ---------------------------------------------------------------------------
def load_rows() -> list[dict]:
    out = []
    for window, rel in C_ROWS.items():
        doc = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        for r in doc["rows"]:
            if (r.get("engine") in ENGINES and r.get("north_up") is True
                    and "reproduces_recorded" not in r and not r.get("excluded")):
                out.append(dict(r, _site="C", _window=window))
    doc = json.loads((ROOT / V_ROWS).read_text(encoding="utf-8"))
    for r in doc["rows"]:
        if r.get("engine") in ENGINES and not r.get("excluded"):
            out.append(dict(r, _site="V", _window=V_WINDOW))
    for r in out:
        a, b = (x.strip() for x in r["edge"].split(" -> "))           # E-036: direction from edge
        if "pair" in r and frozenset((a, b)) != frozenset(r["pair"]):
            raise SystemExit(f"edge/pair disagree on {r['edge']}")
        r["_a"], r["_b"] = a, b
    seen = set()
    for r in out:
        key = (r["_site"], r["_window"], r["engine"], frozenset((r["_a"], r["_b"])))
        if key in seen:
            raise SystemExit(f"two rows for one pair: {key}")
        seen.add(key)
    return out


# ---------------------------------------------------------------------------
# L2: triangles from recorded rows, EXP-012's rule
# ---------------------------------------------------------------------------
def triangles(rows: list[dict], frames: dict) -> list[dict]:
    by_group: dict = {}
    for r in rows:
        by_group.setdefault((r["_site"], r["_window"], r["engine"]), []).append(r)
    out = []
    for (site, window, engine), rs in sorted(by_group.items()):
        edge_by_pair = {frozenset((r["_a"], r["_b"])): r for r in rs
                        if r.get("transform_matrix") is not None}
        names = sorted({x for p in edge_by_pair for x in p})
        for a, b, c in itertools.combinations(names, 3):
            need = [frozenset((a, b)), frozenset((b, c)), frozenset((a, c))]
            if not all(n in edge_by_pair for n in need):
                continue
            edges = [edge_by_pair[n] for n in need]
            all_pass = all(bool(e["pass"]) for e in edges)
            rec = {"site": site, "window": window, "engine": engine, "frames": [a, b, c],
                   "edges": [e["edge"] for e in edges], "all_pass": all_pass,
                   "edge_inliers": [int(e["n_inliers"]) for e in edges],
                   "loop_closure_residual_px": None, "verified": False}
            if all_pass:
                legs, inverted = [], []
                for x, y in ((a, b), (b, c), (c, a)):
                    e = edge_by_pair[frozenset((x, y))]
                    t = _tf(e["transform_matrix"])
                    if e["_a"] == x and e["_b"] == y:
                        legs.append(t)
                        inverted.append(False)
                    else:
                        legs.append(t.inverse())
                        inverted.append(True)
                e_ab = edge_by_pair[frozenset((a, b))]
                if e_ab.get("shape_src_rotated"):
                    shape = tuple(int(v) for v in e_ab["shape_src_rotated"])
                else:
                    shape = tuple(frames[f"{window}/{e_ab['_a']}"]["northup_k2_shape"])
                res = float(loop_closure(legs, shape, step=LOOP_STEP))
                rec.update({"loop_closure_residual_px": res, "inverted_leg": inverted,
                            "shape_used": list(shape), "verified": bool(res < LOOP_REJECT_PX)})
            out.append(rec)
    return out


def attach_l2(rows: list[dict], tris: list[dict]) -> None:
    idx = {}
    for r in rows:
        idx[(r["_site"], r["_window"], r["engine"], r["edge"])] = r
        r["_reachable"], r["_verified"], r["_n_ver_tri"], r["_n_allpass_tri"] = False, False, 0, 0
    for t in tris:
        for e in t["edges"]:
            r = idx[(t["site"], t["window"], t["engine"], e)]
            r["_reachable"] = True
            if t["all_pass"]:
                r["_n_allpass_tri"] += 1
            if t["verified"]:
                r["_verified"] = True
                r["_n_ver_tri"] += 1


# ---------------------------------------------------------------------------
# correctness classes
# ---------------------------------------------------------------------------
def edge_error(r: dict, frames: dict, tier: str) -> dict:
    ka, kb = f"{r['_window']}/{r['_a']}", f"{r['_window']}/{r['_b']}"
    fa, fb = frames.get(ka), frames.get(kb)
    if fa is None or fb is None:
        return {"cls": None, "why": "frame not in ground-truth set"}
    la, lb = gt_leg(fa, tier), gt_leg(fb, tier)
    if la is None or lb is None:
        return {"cls": None, "why": "a leg is not admitted"}
    if r.get("transform_matrix_original_pixels") is None:
        return {"cls": "NO_ESTIMATE"}
    g = lb.inverse() @ la
    grid = pixel_grid(tuple(fa["_k2_shape"]), step=CLASS_GRID_STEP)
    pg = g.apply(grid)
    hb, wb = fb["_k2_shape"]
    inside = ((pg[:, 0] >= 0) & (pg[:, 0] <= wb - 1) & (pg[:, 1] >= 0) & (pg[:, 1] <= hb - 1))
    n = int(inside.sum())
    if n < MIN_GT_GRID:
        return {"cls": None, "why": f"ground-truth overlap {n} grid points < {MIN_GT_GRID}"}
    d = _tf(r["transform_matrix_original_pixels"]).apply(grid[inside])
    err = np.linalg.norm(d - pg[inside], axis=1)
    med = float(np.median(err))
    to_ref = K2 * fb["native_gsd_m"] / REF_GSD_M
    return {"cls": "?", "e_k2_px": med, "e_ref_px": med * to_ref, "e_m": med * K2 * fb["native_gsd_m"],
            "e_p95_ref_px": float(np.percentile(err, 95)) * to_ref, "n_grid": n}


def classify(e: dict, correct: float, wrong: float) -> str | None:
    if e["cls"] in (None, "NO_ESTIMATE"):
        return e["cls"]
    v = e["e_ref_px"]
    return "CORRECT" if v <= correct else ("WRONG" if v > wrong else "AMBIGUOUS")


def classify_all(rows: list[dict], frames: dict, correct: float, wrong: float,
                 tier: str) -> list[dict]:
    out = []
    for r in rows:
        e = edge_error(r, frames, tier)
        out.append({"site": r["_site"], "window": r["_window"], "engine": r["engine"],
                    "edge": r["edge"], "n_inliers": int(r["n_inliers"]),
                    "pass": bool(r["pass"]), "reachable": r["_reachable"],
                    "verified": r["_verified"], "n_verified_triangles": r["_n_ver_tri"],
                    "n_allpass_triangles": r["_n_allpass_tri"],
                    "delta_incidence_deg": r.get("delta_incidence_deg"),
                    "geometry_verdict": (r.get("geometry") or {}).get("verdict"),
                    "cls": classify(e, correct, wrong),
                    **{k: v for k, v in e.items() if k != "cls"}})
    return out


# ---------------------------------------------------------------------------
# rates
# ---------------------------------------------------------------------------
LABELLED = ("CORRECT", "AMBIGUOUS", "WRONG", "NO_ESTIMATE")


def rates(cl: list[dict], sites: tuple, engines: tuple, level: str) -> dict:
    sel = [c for c in cl if c["site"] in sites and c["engine"] in engines and c["cls"] in LABELLED]
    if level == "L1":
        acc = lambda c: c["pass"]                                  # noqa: E731
        reach = lambda c: True                                     # noqa: E731
    else:
        acc = lambda c: c["verified"]                              # noqa: E731
        reach = lambda c: c["reachable"]                           # noqa: E731
    A = [c for c in sel if acc(c) and c["cls"] != "NO_ESTIMATE"]
    wrong_acc = sum(c["cls"] == "WRONG" for c in A)
    amb_acc = sum(c["cls"] == "AMBIGUOUS" for c in A)
    W = [c for c in sel if c["cls"] == "WRONG" and reach(c)]
    C = [c for c in sel if c["cls"] == "CORRECT" and reach(c)]
    return {
        "n_labelled": len(sel),
        "n_accepted_labelled": len(A),
        "counts": {k: sum(c["cls"] == k for c in sel) for k in LABELLED},
        "FDR": rate(wrong_acc, len(A)),
        "FDR_cons": rate(wrong_acc + amb_acc, len(A)),
        "FAR": rate(sum(acc(c) for c in W), len(W)),
        "FRR": rate(sum(not acc(c) for c in C), len(C)),
    }


def s2_reading(r: dict) -> dict:
    n = r["FDR"]["n"]
    if n < S2_MIN_VERIFIED:
        return {"outcome": "NOT EVALUABLE", "why": f"{n} VERIFIED labelled edges < {S2_MIN_VERIFIED}",
                "withdraw": False}
    fdr = r["FDR"]["rate"]
    far = r["FAR"]["rate"]
    met = fdr <= FA_LINE and (far is None or far <= FA_LINE)
    dem = (r["FDR"]["ci95"][1] <= FA_LINE
           and (r["FAR"]["ci95"] is None or r["FAR"]["ci95"][1] <= FA_LINE))
    return {"outcome": "MET" if met else "NOT MET", "demonstrated": bool(dem),
            "FAR_defined": far is not None, "withdraw": bool(fdr > FA_WITHDRAW_LINE)}


def s3_reading(r: dict) -> dict:
    n = r["FRR"]["n"]
    if n < S3_MIN_CORRECT:
        return {"outcome": "NOT EVALUABLE", "why": f"{n} reachable CORRECT edges < {S3_MIN_CORRECT}"}
    return {"outcome": "MET" if r["FRR"]["rate"] <= FR_LINE else "NOT MET",
            "demonstrated": bool(r["FRR"]["ci95"][1] <= FR_LINE)}


def combine(strict: dict, pooled: dict) -> dict:
    s, p = strict["outcome"], pooled["outcome"]
    if s == "MET" and p == "MET":
        return {"met": True, "reads": "MET on both readings"}
    if s == "NOT EVALUABLE" and p != "NOT EVALUABLE":
        return {"met": False,
                "reads": f"{p} on V u C; NOT EVALUABLE on the held-out site alone"}
    return {"met": False, "reads": f"strict (V): {s}; pooled (V u C): {p}"}


def score_s2_s3(cl: list[dict]) -> dict:
    out = {}
    for name, sites in (("strict", ("V",)), ("pooled", ("V", "C"))):
        r = rates(cl, sites, (PRIMARY,), "L2")
        out[name] = {"rates": r, "S2": s2_reading(r), "S3": s3_reading(r)}
    out["S2"] = combine(out["strict"]["S2"], out["pooled"]["S2"])
    out["S3"] = combine(out["strict"]["S3"], out["pooled"]["S3"])
    out["withdraw_verified"] = bool(out["strict"]["S2"]["withdraw"] or out["pooled"]["S2"]["withdraw"])
    return out


def s4(cl: list[dict]) -> dict:
    lab = lambda site: [c for c in cl if c["site"] == site and c["cls"] in  # noqa: E731
                        ("CORRECT", "AMBIGUOUS", "WRONG")]
    C, V = lab("C"), lab("V")
    wc = [c for c in C if c["cls"] == "WRONG"]
    table = []
    for cut in range(S4_C_RANGE[0], S4_C_RANGE[1] + 1):
        far = sum(c["n_inliers"] > cut for c in wc) / len(wc) if wc else None
        table.append({"c": cut, "FAR_C": far})
    rec = {"n_wrong_C": len(wc), "n_correct_C": sum(c["cls"] == "CORRECT" for c in C),
           "far_by_cutoff_C": table}
    if len(wc) < S4_MIN_WRONG_C:
        rec.update({"met": False, "c_star": None,
                    "reads": f"NOT MET for want of data: {len(wc)} WRONG rows on C < {S4_MIN_WRONG_C}"})
    else:
        rec["c_star"] = next((t["c"] for t in table
                              if t["FAR_C"] is not None and t["FAR_C"] <= FA_LINE), None)
        if rec["c_star"] is None:
            rec.update({"met": False, "reads": f"NOT MET: no cutoff in {S4_C_RANGE} reaches FAR <= 5 % on C"})
    wv = [c for c in V if c["cls"] == "WRONG"]
    cv = [c for c in V if c["cls"] == "CORRECT"]
    rec.update({"n_wrong_V": len(wv), "n_correct_V": len(cv)})
    for label, cut in (("at_frozen_8", RULE), ("at_c_star", rec.get("c_star"))):
        if cut is None:
            continue
        rec[label] = {"c": cut,
                      "FAR_V": rate(sum(c["n_inliers"] > cut for c in wv), len(wv)),
                      "FRR_V": rate(sum(c["n_inliers"] <= cut for c in cv), len(cv)),
                      "FAR_C": rate(sum(c["n_inliers"] > cut for c in wc), len(wc)),
                      "FRR_C": rate(sum(c["n_inliers"] <= cut for c in C if c["cls"] == "CORRECT"),
                                    rec["n_correct_C"])}
    if rec.get("c_star") is not None:
        if len(wv) < S4_MIN_WRONG_V or len(cv) < S4_MIN_CORRECT_V:
            rec.update({"met": False, "reads": f"NOT MET for want of data on V: {len(wv)} WRONG "
                        f"(need {S4_MIN_WRONG_V}), {len(cv)} CORRECT (need {S4_MIN_CORRECT_V})"})
        else:
            a = rec["at_c_star"]
            ok = a["FAR_V"]["rate"] <= FA_LINE and a["FRR_V"]["rate"] <= FR_LINE
            rec.update({"met": bool(ok), "reads": "MET" if ok else "NOT MET"})
    return rec


# ---------------------------------------------------------------------------
# S0 gates
# ---------------------------------------------------------------------------
def s0_i(frames_c: dict, e19: dict) -> dict:
    """Rebuilt C legs reproduce EXP-019's 17 S3 medians."""
    cells = {}
    frames = {}
    for key, fr in frames_c.items():
        c = e19["cells"][key]
        cells[key] = {"arm": "R", "pass": c.get("pass"), "n_inliers": c.get("n_inliers"),
                      "_k2_to_ref": fr.get("_k2_b1"), "_k2_shape": fr["_k2_shape"]}
        frames[key] = {"native_gsd_m": fr["native_gsd_m"]}
    got = {(p["window"], p["edge"]): p for p in _e19.s3_pairs(cells, frames, _e19.recorded_rows())}
    rows = []
    for p in e19["criteria"]["S3"]["pairs"]:
        g = got.get((p["window"], p["edge"]))
        diff = abs(g["median_k2_px"] - p["median_k2_px"]) if g and "median_k2_px" in g else None
        rows.append({"window": p["window"], "edge": p["edge"], "recorded": p["median_k2_px"],
                     "rebuilt": g.get("median_k2_px") if g else None, "abs_diff_px": diff})
    ok = all(r["abs_diff_px"] is not None and r["abs_diff_px"] <= S0_TOL_PX for r in rows)
    return {"met": bool(ok and len(rows) == 17), "n": len(rows),
            "max_abs_diff_px": max((r["abs_diff_px"] if r["abs_diff_px"] is not None else np.inf)
                                   for r in rows), "pairs": rows}


def s0_ii(rows: list[dict]) -> dict:
    bad = [r["edge"] for r in rows if bool(r["pass"]) != (int(r["n_inliers"]) > RULE)]
    return {"met": not bad, "n_rows": len(rows), "violations": bad}


def s0_iii(tris: list[dict]) -> dict:
    mine = {(t["window"], tuple(t["frames"])): t for t in tris if t["engine"] == PRIMARY}
    out = []
    for rel, key in (("experiments/EXP-012/exp012_results.json", "triplets"),
                     ("experiments/EXP-018/exp018_results.json", "triangles")):
        doc = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        for t in doc[key]:
            m = mine.get((t["window"], tuple(sorted(t["frames"]))))
            rec_status = all(s == "VERIFIED" for s in t["statuses"])
            got = m["loop_closure_residual_px"] if m else None
            out.append({"source": rel.split("/")[1], "window": t["window"], "frames": t["frames"],
                        "recorded_px": t["loop_closure_residual_px"], "rebuilt_px": got,
                        "abs_diff_px": abs(got - t["loop_closure_residual_px"]) if got is not None else None,
                        "recorded_all_verified": rec_status,
                        "rebuilt_verified": m["verified"] if m else None})
    ok = all(o["abs_diff_px"] is not None and o["abs_diff_px"] <= S0_TOL_PX
             and o["recorded_all_verified"] == o["rebuilt_verified"] for o in out)
    return {"met": bool(ok and len(out) == 20), "n": len(out),
            "max_abs_diff_px": max((o["abs_diff_px"] if o["abs_diff_px"] is not None else np.inf)
                                   for o in out), "triangles": out}


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------
def v_sources() -> list:
    man = json.loads((DATA / "manifests" / "exp018_tranquillitatis_manifest.json")
                     .read_text(encoding="utf-8"))
    prods = json.loads((DATA / "manifests" / "exp018_tranquillitatis_index_geometry.json")
                       .read_text(encoding="utf-8"))["products"]
    target = tuple(man["target_ground_point_lon_lat"])
    out = []
    for t in man["tiles"]:
        s = _e19.Source(f"{V_WINDOW}/{t['pdsid']}", V_WINDOW, t["pdsid"], "NAC")
        s.ctx = _e7.FrameContext(t["pdsid"], t, prods, target)
        s.k = int(round(REF_GSD_M / s.ctx.scaled_pixel_m))
        out.append(s)
    return out


def null_cell(s, nul, margin_px: int, engine: str) -> dict:
    """EXP-019 arm N, unchanged: a centred crop of the null block."""
    H, W = nul.data.shape
    h, w = s.image.shape
    ch = min(H, int(h * 1.2) + 2 * margin_px)
    cw = min(W, int(w * 1.2) + 2 * margin_px)
    y0 = max(0, (H - ch) // 2)
    x0 = max(0, (W - cw) // 2)
    crop = nul.data[y0:y0 + ch, x0:x0 + cw]
    rec = _e19.register_against(s, nul, margin_px=margin_px, engine=engine,
                                crop_override=(crop, (x0, y0, x0 + cw, y0 + ch),
                                               (x0, y0, x0 + cw, y0 + ch)))
    rec.update({"arm": "N", "source": s.key})
    return _strip(rec)


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out_path = Path(args.out) if args.out else OUT / "exp021_results.json"
    if out_path.exists():
        raise SystemExit(f"{out_path} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()
    margin_px = int(round(_e19.MARGIN_M / REF_GSD_M))
    e19 = json.loads((ROOT / "experiments" / "EXP-019" / "exp019_results.json")
                     .read_text(encoding="utf-8"))

    # ---- C: EXP-019's recorded legs, rebuilt ---------------------------------
    print(f"{STAGE} | calibration site: rebuilding EXP-019 legs", flush=True)
    ref19 = load_map_block(_e19.REF_MANIFEST)
    frames: dict = {}
    drift = None
    for s in _e19.nac_sources():
        _e19.prepare_nac(s)
        fr = frame_record(s, e19["cells"].get(s.key), e19["second_engine"].get(s.key))
        fr["site"] = "C"
        frames[s.key] = fr
        if s.key == DRIFT_GATE[0]:
            rec = _e19.register_against(s, ref19, margin_px=margin_px, engine="B1")
            drift = {"source": s.key, "recorded": DRIFT_GATE[1], "rerun": rec.get("n_inliers"),
                     "met": bool(rec.get("n_inliers") == DRIFT_GATE[1])}
            print(f"  [S0 v] drift gate {s.key}: {rec.get('n_inliers')} vs recorded "
                  f"{DRIFT_GATE[1]} -> {'MET' if drift['met'] else 'NOT MET'}", flush=True)
        print(f"  [C] {s.key:30s} B1 {fr['b1_n_inliers']:5d} B4L {fr['b4l_n_inliers']:5d} "
              f"agree {fr['leg_agreement_ref_px'] if fr['leg_agreement_ref_px'] is None else round(fr['leg_agreement_ref_px'], 3)} "
              f"tier {'A' if fr['tier_A'] else ('B' if fr['tier_B'] else '-')}", flush=True)
    del ref19
    frames_c = {k: v for k, v in frames.items() if v["site"] == "C"}
    s0 = {"i_leg_rebuild": s0_i(frames_c, e19)}
    print(f"  [S0 i] {s0['i_leg_rebuild']['n']} pairs, max |diff| "
          f"{s0['i_leg_rebuild']['max_abs_diff_px']:.3e} px -> "
          f"{'MET' if s0['i_leg_rebuild']['met'] else 'NOT MET'}", flush=True)
    s0["v_drift_gate"] = drift

    # ---- V: legs measured here ------------------------------------------------
    print(f"\n== validation site: legs against {V_REF_MANIFEST} ==", flush=True)
    refv = load_map_block(V_REF_MANIFEST)
    s0["iv_grid_gate"] = _e19.s0_grid_gate(refv, V_REF_MANIFEST)
    print(f"  [S0 iv] corners {max(s0['iv_grid_gate']['corner_error_px'].values()):.4f} px, "
          f"round trip {s0['iv_grid_gate']['roundtrip_max_deg']:.2e} deg -> "
          f"{'MET' if s0['iv_grid_gate']['met'] else 'NOT MET'}", flush=True)
    v_cells, v_second, v_null, v_null_b4l = {}, {}, [], []
    vsrc = v_sources()
    for s in vsrc:
        _e19.prepare_nac(s)
        b1 = _e19.register_against(s, refv, margin_px=margin_px, engine="B1")
        b4 = _e19.register_against(s, refv, margin_px=margin_px, engine="B4L")
        v_cells[s.key], v_second[s.key] = _strip(b1), _strip(b4)
        fr = frame_record(s, v_cells[s.key], v_second[s.key])
        fr["site"] = "V"
        frames[s.key] = fr
        print(f"  [V] {s.key:34s} k={s.k:2d} i={fr['incidence_deg']:5.2f} B1 {fr['b1_n_inliers']:5d} "
              f"B4L {fr['b4l_n_inliers']:5d} agree "
              f"{fr['leg_agreement_ref_px'] if fr['leg_agreement_ref_px'] is None else round(fr['leg_agreement_ref_px'], 3)} "
              f"tier {'A' if fr['tier_A'] else ('B' if fr['tier_B'] else '-')}", flush=True)
    del refv
    nul_path = DATA / "manifests" / V_NULL_MANIFEST
    if nul_path.exists():
        nul = load_map_block(V_NULL_MANIFEST)
        for s in vsrc:
            v_null.append(null_cell(s, nul, margin_px, "B1"))
            v_null_b4l.append(null_cell(s, nul, margin_px, "B4L"))
            print(f"  [N] {s.key:34s} B1 {v_null[-1].get('n_inliers', 0):4d} "
                  f"{'WRONG PASS' if v_null[-1].get('pass') else 'fail'} | B4L "
                  f"{v_null_b4l[-1].get('n_inliers', 0):4d} "
                  f"{'WRONG PASS' if v_null_b4l[-1].get('pass') else 'fail'}", flush=True)
        s0["vi_v_null"] = {"met": not any(c.get("pass") for c in v_null),
                           "n_pass": sum(bool(c.get("pass")) for c in v_null), "n": len(v_null)}
    else:
        s0["vi_v_null"] = {"met": None, "reads": "NO DATA: no null band fits the tile"}
    s0["vii_handedness"] = {"met": True, "source": "siim.ingest.orientation.handedness",
                            "per_frame": {k: v["handedness_det"] for k, v in frames.items()}}

    # ---- rows, triangles --------------------------------------------------------
    rows = load_rows()
    s0["ii_pass_rule"] = s0_ii(rows)
    tris = triangles(rows, frames)
    attach_l2(rows, tris)
    s0["iii_loop_rebuild"] = s0_iii(tris)
    print(f"\n  [S0 ii] {s0['ii_pass_rule']['n_rows']} rows, "
          f"{len(s0['ii_pass_rule']['violations'])} violations", flush=True)
    print(f"  [S0 iii] {s0['iii_loop_rebuild']['n']} triangles, max |diff| "
          f"{s0['iii_loop_rebuild']['max_abs_diff_px']:.3e} px -> "
          f"{'MET' if s0['iii_loop_rebuild']['met'] else 'NOT MET'}", flush=True)
    s0["met"] = bool(s0["i_leg_rebuild"]["met"] and s0["ii_pass_rule"]["met"]
                     and s0["iii_loop_rebuild"]["met"] and s0["iv_grid_gate"]["met"]
                     and (drift or {}).get("met") and s0["vi_v_null"]["met"] is not False)

    # ---- classification, primary ------------------------------------------------
    cl = classify_all(rows, frames, CORRECT_REF_PX, WRONG_REF_PX, "A")
    v_frames_a = [k for k, v in frames.items() if v["site"] == "V" and v["tier_A"]]
    v_b1_cw = sum(c["site"] == "V" and c["engine"] == PRIMARY and c["cls"] in ("CORRECT", "WRONG")
                  for c in cl)
    S1 = {"met": bool(len(v_frames_a) >= S1_MIN_V_FRAMES and v_b1_cw >= S1_MIN_V_B1_EDGES),
          "v_frames_tier_A": len(v_frames_a), "v_frames": sorted(v_frames_a),
          "v_b1_edges_correct_or_wrong": v_b1_cw}
    prim = score_s2_s3(cl)
    S4 = s4(cl)
    hard = [c for c in cl if c["site"] == "V" and c["cls"] == "WRONG" and c["n_inliers"] > RULE]
    hard_c = [c for c in cl if c["site"] == "C" and c["cls"] == "WRONG" and c["n_inliers"] > RULE]
    S6 = {"met": len(hard) >= S6_MIN_HARD_NEG, "n_hard_negatives_V": len(hard),
          "hard_negatives_V": hard, "n_hard_negatives_C_beside": len(hard_c),
          "hard_negatives_C_beside": hard_c,
          "n_wrong_in_L2_population": {
              site: sum(c["site"] == site and c["cls"] == "WRONG" and c["n_allpass_triangles"] > 0
                        for c in cl) for site in ("V", "C")}}

    # ---- S5 ------------------------------------------------------------------
    variants = {}
    for name, v in S5_VARIANTS.items():
        clv = classify_all(rows, frames, v["correct"], v["wrong"], v["tier"])
        sv = score_s2_s3(clv)
        variants[name] = {"spec": v,
                          "S2": {r: sv[r]["S2"]["outcome"] for r in ("strict", "pooled")},
                          "S3": {r: sv[r]["S3"]["outcome"] for r in ("strict", "pooled")},
                          "rates_pooled_b1_L2": {k: sv["pooled"]["rates"][k] for k in ("FDR", "FAR", "FRR")},
                          "rates_strict_b1_L2": {k: sv["strict"]["rates"][k] for k in ("FDR", "FAR", "FRR")}}
    base = {c: {r: prim[r][c]["outcome"] for r in ("strict", "pooled")} for c in ("S2", "S3")}
    changed = [n for n, v in variants.items() if v["S2"] != base["S2"] or v["S3"] != base["S3"]]
    S5 = {"met": not changed, "primary": base, "variants": variants, "changed": changed}

    # ---- reported beside --------------------------------------------------------
    beside = {}
    for level in ("L1", "L2"):
        for sites_name, sites in (("V", ("V",)), ("C", ("C",)), ("V+C", ("V", "C"))):
            for eng in ENGINES + ("pooled",):
                engs = ENGINES if eng == "pooled" else (eng,)
                beside[f"{level}|{sites_name}|{ENGINE_NAME.get(eng, eng)}"] = rates(cl, sites, engs, level)
    ver = [c for c in cl if c["verified"] and c["cls"] in LABELLED]
    beside["verified_edge_errors"] = sorted(
        ({"site": c["site"], "window": c["window"], "engine": ENGINE_NAME[c["engine"]],
          "edge": c["edge"], "e_ref_px": c.get("e_ref_px"), "e_m": c.get("e_m"),
          "e_k2_px": c.get("e_k2_px"), "n_inliers": c["n_inliers"], "cls": c["cls"]} for c in ver),
        key=lambda d: -(d["e_ref_px"] or 0))
    beside["ambiguous"] = [c for c in cl if c["cls"] == "AMBIGUOUS"]
    geo = {}
    for c in cl:
        if c["cls"] in ("CORRECT", "AMBIGUOUS", "WRONG"):
            key = f"{c['cls']} | {c['geometry_verdict']}"
            geo[key] = geo.get(key, 0) + 1
    beside["archive_geometry_vs_class"] = geo
    units = {}
    for t in tris:
        if not t["all_pass"]:
            continue
        for e in t["edges"]:
            c = next(x for x in cl if x["site"] == t["site"] and x["window"] == t["window"]
                     and x["engine"] == t["engine"] and x["edge"] == e)
            if c["cls"] not in ("CORRECT", "AMBIGUOUS", "WRONG"):
                continue
            k = (t["site"], ENGINE_NAME[t["engine"]])
            u = units.setdefault(f"{k[0]}|{k[1]}", {"verified_units": 0, "wrong_verified_units": 0,
                                                   "correct_units": 0, "correct_not_verified_units": 0})
            if t["verified"]:
                u["verified_units"] += 1
                u["wrong_verified_units"] += c["cls"] == "WRONG"
            if c["cls"] == "CORRECT":
                u["correct_units"] += 1
                u["correct_not_verified_units"] += not t["verified"]
    beside["edge_triangle_units"] = units
    beside["unlabelled_rows"] = {}
    for c in cl:
        if c["cls"] is None:
            beside["unlabelled_rows"][c.get("why", "?")] = beside["unlabelled_rows"].get(c.get("why", "?"), 0) + 1

    criteria = {"S0": s0, "S1": S1,
                "S2": {"met": prim["S2"]["met"], "reads": prim["S2"]["reads"],
                       "strict": prim["strict"]["S2"], "pooled": prim["pooled"]["S2"],
                       "withdraw_verified_under_SS54": prim["withdraw_verified"]},
                "S3": {"met": prim["S3"]["met"], "reads": prim["S3"]["reads"],
                       "strict": prim["strict"]["S3"], "pooled": prim["pooled"]["S3"]},
                "primary_rates_b1_L2": {"strict": prim["strict"]["rates"],
                                        "pooled": prim["pooled"]["rates"]},
                "S4": S4, "S5": S5, "S6": S6}

    doc = {
        "stage": STAGE, "preregistration": PREREG,
        "constants": {"correct_ref_px": CORRECT_REF_PX, "wrong_ref_px": WRONG_REF_PX,
                      "leg_agree_ref_px": LEG_AGREE_REF_PX, "ref_gsd_m": REF_GSD_M,
                      "loop_reject_px": LOOP_REJECT_PX, "inlier_rule": f"n_inliers <= {RULE} fails",
                      "primary_engine": "B1"},
        "criteria": criteria,
        "frames": {k: _strip(v) for k, v in frames.items()},
        "validation_legs": {"B1": v_cells, "B4L": v_second},
        "validation_null": {"B1": v_null, "B4L_beside": v_null_b4l},
        "triangles": tris,
        "rows_classified": cl,
        "reported_beside": beside,
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__,
                        "platform": platform.platform()},
        "total_runtime_s": round(time.perf_counter() - t_start, 1),
        "claims_not_supported": [
            "geodetic check points: 'correct' means agrees with Kaguya TC Ortho Seamless V2 to 8.42 m",
            "an FA rate against a per-image gauge (loop closure's null space, ADR-0011 N1)",
            "highland, viewpoint, scale or multimodal transfer",
            "any change to the verdict: c* is reported, not adopted",
            "VERIFIED at fine resolution: the correctness tolerance is 8.42 m",
        ],
    }
    out_path.write_text(json.dumps(doc, indent=1, default=_json_default), encoding="utf-8")
    print(f"\nS0 {'MET' if s0['met'] else 'NOT MET'} | S1 {'MET' if S1['met'] else 'NOT MET'} "
          f"({S1['v_frames_tier_A']} V frames tier A, {S1['v_b1_edges_correct_or_wrong']} B1 edges) | "
          f"S2 {prim['S2']['reads']} | S3 {prim['S3']['reads']} | S4 {S4.get('reads', S4.get('met'))} "
          f"(c* = {S4.get('c_star')}) | S5 {'MET' if S5['met'] else 'NOT MET: ' + ', '.join(changed)} | "
          f"S6 {'MET' if S6['met'] else 'NOT MET'} ({S6['n_hard_negatives_V']} hard negatives on V)",
          flush=True)
    for r in ("strict", "pooled"):
        rr = prim[r]["rates"]
        print(f"  B1 L2 {r:6s}: FDR {rr['FDR']['k']}/{rr['FDR']['n']}  FAR {rr['FAR']['k']}/{rr['FAR']['n']}  "
              f"FRR {rr['FRR']['k']}/{rr['FRR']['n']}", flush=True)
    print(f"-> {out_path} ({doc['total_runtime_s']} s)", flush=True)


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Transform):
        return np.asarray(o.matrix).tolist()
    raise TypeError(type(o))


if __name__ == "__main__":
    main()
