"""EXP-018 — blind validation: the frozen pipeline opened ONCE on a held-out window.

Pre-registered in ``docs/stages/EXP-018_blind_validation.md`` Part 1 (commit
e8071c4) before this file existed. Every number this script grades against is
copied from that document's section 2; nothing here is fitted on held-out data.

    python scripts/run_exp018.py --gate                 # S0(e) reproduction gate only
    python scripts/run_exp018.py --window apollo16      # the one held-out run

What is IMPORTED, not re-implemented
------------------------------------
* ``scripts/run_real_data_07.py``'s ``run_edge`` -- the per-edge function that
  wrote every REAL-DATA-07 row (engine, orientation, geometry check, wrong-pass
  rule). Its orientation step is set to ``north_up_east_right`` (the amended
  run) and nothing else about it is touched.
* ``scripts/run_exp012.py``'s ``run_s4`` (RD-03 loop re-composition) and
  ``run_triplet`` (direction from ``edge``, inverse of a stored edge where the
  cycle needs it, ``loop_closure(step=16)``, unmodified ``assess()``).
* ``siim.pipeline.agreement.engine_agreement`` for S3.

The engine results are captured by wrapping ``run_exp007.run_engine`` at the
module attribute ``run_edge`` looks up at call time; ``run_edge`` itself is
byte-for-byte the recorded function.

Integrity rule 4: refuses to overwrite ``exp018_results.json`` or a rows file.
Crash policy (Part 1 section 4): rows are checkpointed to ``*.partial.json``
after every pair so a single restart can report what was already computed; a
restart re-runs nothing that was checkpointed.
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.baselines import learned_available  # noqa: E402
from siim.evaluation.significance import exact_separation_test  # noqa: E402
from siim.geometry import Transform  # noqa: E402
from siim.ingest.orientation import north_up_east_right  # noqa: E402
from siim.pipeline.agreement import AGREEMENT_FLOOR_PX, engine_agreement  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_rd07 = _load("_rd07", ROOT / "scripts" / "run_real_data_07.py")
_e7 = _rd07._e7
_e12 = _load("_e12", ROOT / "scripts" / "run_exp012.py")

STAGE = "EXP-018"
DATA = ROOT / "data"
OUT = ROOT / "experiments" / STAGE
PREREG = "docs/stages/EXP-018_blind_validation.md Part 1 (commit e8071c4)"

#: The frozen pipeline: REAL-DATA-07's amended run, byte for byte (Part 1 section 4).
BASE = _rd07.BASE
ENGINES = ("b1", "lg", "xf")
ENGINE_NAME = {"b1": "B1", "lg": "B4L", "xf": "B4X"}
_rd07.ORIENT_FN = north_up_east_right          # the E-037 amendment; the recorded orientation
_rd07.ORIENT_SUFFIX = "_nue"
N_INLIERS_FAILURE_RULE = _rd07.N_INLIERS_FAILURE_RULE
LOOP_REJECT_PX = 2.0                           # verdict.LOOP_ERROR_REJECT_PX, restated
ALPHA_TWO_SIDED = 0.025
ALPHA_ONE_SIDED = 0.05

# ---------------------------------------------------------------------------
# Part 1 section 2 -- the frozen predictions, copied, not computed
# ---------------------------------------------------------------------------
#: P1. Range -> (in-sample n, in-sample successes, point rate). Successes are
#: the arithmetic shown in Part 1 section 2.1.
P1 = {
    "B1": {"lt15": (14, 11, 0.786), "15to30": (19, 12, 0.632), "ge30": (9, 2, 0.222),
           "pooled": (42, 25, 0.595)},
    "B4L": {"lt15": (14, 11, 0.786), "15to30": (19, 12, 0.632), "ge30": (9, 1, 0.111),
            "pooled": (42, 24, 0.571)},
    "B4X": {"pooled": (42, 27, 0.643)},
}
#: S1c: 0 successes above 40 deg; point prediction; requires n >= 3.
P1_GE40_INSAMPLE = (4, 0)
#: P2. Exact one-sided 95 % Clopper-Pearson upper limits (Part 1 section 2.2).
P2_UPPER = {"B1": 0.0631, "B4L": 0.0929, "B4X": 0.105}
P2_INSAMPLE = {"B1": (46, 0), "B4L": (49, 1), "B4X": (27, 0)}
FA_LINE = 0.05
#: P3. D-051's floor and its reversal condition.
P3_AGREE_PX = 3.0
P3_INCONSISTENT_MIN_PX = 30.0
#: S5 minima from geometry (Part 1 section 5.1).
S5_MIN = {"n_lt15": 5, "n_ge30": 5, "n_ge40": 3, "n_total": 12, "max_frames": 8,
          "one_frame_incidence_le": 30.0, "one_frame_incidence_ge": 60.0}
#: S0(e): the three B1 counts of EXP-012's primary triplet R4-6, each in the
#: direction its recorded row's ``edge`` states, and RD-03's recorded loop.
GATE_EDGES = {"nac.m1299958135lc -> nac.m1271742202lc": 1608,
              "nac.m1299958135lc -> nac.m1315225542lc": 2726,
              "nac.m1315225542lc -> nac.m1271742202lc": 2138}
GATE_LOOP_PX = 1201.0378963072235

_captured: dict = {}
_orig_run_engine = _e7.run_engine


def _capturing_run_engine(engine, a, b, base):
    res = _orig_run_engine(engine, a, b, base)
    _captured["last"] = res
    return res


_e7.run_engine = _capturing_run_engine


# ---------------------------------------------------------------------------
# statistics -- pure functions, pinned by tests/test_exp018_runner.py
# ---------------------------------------------------------------------------
def binom_two_sided(k: int, n: int, p: float, alpha: float = ALPHA_TWO_SIDED) -> dict:
    """Exact two-sided binomial test at the frozen point rate (Part 1 S1)."""
    from scipy.stats import binom
    if n == 0:
        return {"n": 0, "k": 0, "p": p, "p_low": None, "p_high": None,
                "rejects": False, "vacuous": True}
    p_low = float(binom.cdf(k, n, p))
    p_high = float(binom.sf(k - 1, n, p))
    return {"n": int(n), "k": int(k), "p": p, "rate": k / n,
            "P_X_le_k": p_low, "P_X_ge_k": p_high,
            "rejects": bool(p_low < alpha or p_high < alpha), "vacuous": False}


def binom_one_sided_upper(k: int, n: int, p_upper: float,
                          alpha: float = ALPHA_ONE_SIDED) -> dict:
    """Does the held-out count reject H0: p <= p_upper?  P(X >= k | n, p_upper) < alpha."""
    from scipy.stats import binom
    if n == 0:
        return {"n": 0, "k": 0, "p_upper": p_upper, "P_X_ge_k": None, "rejects": False,
                "vacuous": True}
    p = float(binom.sf(k - 1, n, p_upper))
    return {"n": int(n), "k": int(k), "p_upper": p_upper, "P_X_ge_k": p,
            "rejects": bool(p < alpha), "vacuous": False}


def betabinom_predictive(k: int, n: int, s_in: int, f_in: int) -> dict:
    """Beta-binomial predictive interval with a Jeffreys prior on the in-sample count.

    Reported beside each S1 range (Part 1 section 5.2): it says whether a point-
    rate failure is attributable to a noisy in-sample estimate. Not graded.
    """
    from scipy.stats import betabinom
    a, b = 0.5 + s_in, 0.5 + f_in
    if n == 0:
        return {"a": a, "b": b, "interval_95": None, "p_two_sided": None}
    lo = int(betabinom.ppf(0.025, n, a, b))
    hi = int(betabinom.ppf(0.975, n, a, b))
    p_lo = float(betabinom.cdf(k, n, a, b))
    p_hi = float(betabinom.sf(k - 1, n, a, b))
    return {"a": a, "b": b, "interval_95": [lo, hi],
            "k_inside_interval": bool(lo <= k <= hi),
            "p_two_sided": float(min(1.0, 2 * min(p_lo, p_hi)))}


def delta_range(d: float) -> str:
    if d < 15.0:
        return "lt15"
    if d < 30.0:
        return "15to30"
    return "ge30"


def s5_counts(pairs: list[dict], n_frames: int, incidences: list[float],
              n_triangles: int) -> dict:
    """S5 from geometry alone: CONFIRMED pairs carrying (delta_incidence_deg)."""
    d = [p["delta_incidence_deg"] for p in pairs]
    c = {"n_lt15": sum(x < 15 for x in d), "n_15to30": sum(15 <= x < 30 for x in d),
         "n_ge30": sum(x >= 30 for x in d), "n_ge40": sum(x >= 40 for x in d),
         "n_total": len(d), "n_frames": n_frames, "n_confirmed_triangles": n_triangles,
         "min_incidence_deg": min(incidences) if incidences else None,
         "max_incidence_deg": max(incidences) if incidences else None}
    checks = {
        "n_lt15": c["n_lt15"] >= S5_MIN["n_lt15"],
        "n_ge30": c["n_ge30"] >= S5_MIN["n_ge30"],
        "n_ge40": c["n_ge40"] >= S5_MIN["n_ge40"],
        "n_total": c["n_total"] >= S5_MIN["n_total"],
        "one_frame_le_30": bool(incidences) and min(incidences) <= S5_MIN["one_frame_incidence_le"],
        "one_frame_ge_60": bool(incidences) and max(incidences) >= S5_MIN["one_frame_incidence_ge"],
        "at_least_one_triangle": n_triangles >= 1,
        "at_most_8_frames": n_frames <= S5_MIN["max_frames"],
    }
    c["checks"] = checks
    c["met"] = all(checks.values())
    c["minima"] = dict(S5_MIN)
    return c


def evaluate_s1(rows: list[dict]) -> dict:
    """P1 out of sample. ``rows`` are held-out edge rows (one per pair per engine)."""
    out: dict = {}
    for eng in ENGINES:
        name = ENGINE_NAME[eng]
        sub = [r for r in rows if r.get("engine") == eng and "success" in r]
        per_range: dict = {}
        ranges = P1[name]
        for rng_key, (n_in, s_in, p) in ranges.items():
            sel = sub if rng_key == "pooled" else [r for r in sub
                                                   if delta_range(r["delta_incidence_deg"]) == rng_key]
            k = sum(bool(r["success"]) for r in sel)
            t = binom_two_sided(k, len(sel), p)
            t["in_sample"] = {"n": n_in, "successes": s_in}
            t["predictive"] = betabinom_predictive(k, len(sel), s_in, n_in - s_in)
            per_range[rng_key] = t
        graded = [t for t in per_range.values()]
        met = not any(t["rejects"] for t in graded)
        vac = [k for k, t in per_range.items() if t["vacuous"]]
        out[name] = {"ranges": per_range, "met": bool(met), "vacuous_ranges": vac,
                     "note": ("MET, and here is why that is not reassurance: ranges "
                              f"{vac} had no held-out pair and could not fail" if met and vac else None)}
    # S1c: zero successes above 40 deg for B1 and B4L, point prediction, n >= 3
    s1c: dict = {}
    for eng in ("b1", "lg"):
        sel = [r for r in rows if r.get("engine") == eng and "success" in r
               and r["delta_incidence_deg"] >= 40.0]
        k = sum(bool(r["success"]) for r in sel)
        s1c[ENGINE_NAME[eng]] = {"n_ge40": len(sel), "successes": k,
                                 "status": ("CANNOT CHECK" if len(sel) < 3
                                            else ("MET" if k == 0 else "NOT MET")),
                                 "in_sample": {"n": P1_GE40_INSAMPLE[0], "successes": P1_GE40_INSAMPLE[1]},
                                 "successful_edges": [r["edge"] for r in sel if r["success"]]}
    s1c_met = all(v["status"] == "MET" for v in s1c.values())
    s1c_cc = any(v["status"] == "CANNOT CHECK" for v in s1c.values())
    return {
        "S1a_B1": out["B1"], "S1b_B4L": out["B4L"],
        "S1c_zero_above_40": {"per_engine": s1c,
                              "status": "CANNOT CHECK" if s1c_cc else ("MET" if s1c_met else "NOT MET")},
        "S1d_B4X_pooled": {"ranges": {"pooled": out["B4X"]["ranges"]["pooled"]},
                           "met": out["B4X"]["met"]},
        "met": bool(out["B1"]["met"] and out["B4L"]["met"] and s1c_met and not s1c_cc
                    and out["B4X"]["met"]),
        "status": ("CANNOT CHECK" if s1c_cc else
                   ("MET" if (out["B1"]["met"] and out["B4L"]["met"] and s1c_met
                              and out["B4X"]["met"]) else "NOT MET")),
    }


def evaluate_s2(rows: list[dict]) -> dict:
    per: dict = {}
    for eng in ENGINES:
        name = ENGINE_NAME[eng]
        sub = [r for r in rows if r.get("engine") == eng and "pass" in r]
        n_pass = sum(bool(r["pass"]) for r in sub)
        k = sum(bool(r.get("wrong_pass")) for r in sub)
        per[name] = {"n_pass": n_pass, "n_wrong_pass": k,
                     "wrong_pass_edges": [r["edge"] for r in sub if r.get("wrong_pass")],
                     "S2b_bound": binom_one_sided_upper(k, n_pass, P2_UPPER[name]),
                     "FA_le_5pct_line": binom_one_sided_upper(k, n_pass, FA_LINE),
                     "in_sample": {"n_pass": P2_INSAMPLE[name][0],
                                   "n_wrong_pass": P2_INSAMPLE[name][1]}}
    cannot = per["B1"]["n_pass"] < 5
    s2a = all(v["n_wrong_pass"] == 0 for v in per.values())
    s2b = not any(v["S2b_bound"]["rejects"] for v in per.values())
    return {"per_engine": per,
            "S2a_point": {"status": "CANNOT CHECK" if cannot else ("MET" if s2a else "NOT MET")},
            "S2b_bound": {"status": "CANNOT CHECK" if cannot else ("MET" if s2b else "NOT MET"),
                          "note": "weak by arithmetic (Part 1 section 5.2): at n_pass = 12 it can "
                                  "only fail at k >= 3"},
            "status": "CANNOT CHECK" if cannot else ("MET" if (s2a and s2b) else "NOT MET"),
            "floor_note": "a wrong pass is a transform wrong by >~ 250 px (the geometry check's "
                          "floor); this is a bound, not an FA rate, and FR is not measured"}


def evaluate_s3(agreements: list[dict], rows: list[dict]) -> dict:
    """S3a: both-succeed pairs agree within 3 px. S3b: INCONSISTENT passes >= 30 px from others."""
    by_pair_eng = {(r["edge"], r["engine"]): r for r in rows if "engine" in r}
    qualifying, viol = [], []
    for a in agreements:
        ra, rb = by_pair_eng.get((a["edge"], a["engine_a"])), by_pair_eng.get((a["edge"], a["engine_b"]))
        if ra is None or rb is None or a.get("median_px") is None:
            continue
        if ra["success"] and rb["success"]:
            q = {"edge": a["edge"], "engines": [a["engine_a"], a["engine_b"]],
                 "median_px": a["median_px"], "within_floor": a["median_px"] <= P3_AGREE_PX}
            qualifying.append(q)
            if not q["within_floor"]:
                viol.append(q)
    per_engine_pair: dict = {}
    for q in qualifying:
        key = "-".join(ENGINE_NAME[e] for e in q["engines"])
        per_engine_pair.setdefault(key, []).append(q["median_px"])
    s3a_status = ("CANNOT CHECK" if len(qualifying) < 3 else ("MET" if not viol else "NOT MET"))
    # S3b
    incons = [r for r in rows if "engine" in r and r.get("wrong_pass")]
    s3b_rows = []
    for r in incons:
        others = [a for a in agreements if a["edge"] == r["edge"]
                  and r["engine"] in (a["engine_a"], a["engine_b"]) and a.get("median_px") is not None]
        s3b_rows.append({"edge": r["edge"], "engine": r["engine"],
                         "disagreements_px": {"-".join((a["engine_a"], a["engine_b"])): a["median_px"]
                                              for a in others},
                         "all_ge_30px": all(a["median_px"] >= P3_INCONSISTENT_MIN_PX for a in others)
                         if others else None})
    s3b_status = ("CANNOT CHECK" if not s3b_rows else
                  ("MET" if all(x["all_ge_30px"] for x in s3b_rows if x["all_ge_30px"] is not None)
                   and any(x["all_ge_30px"] is not None for x in s3b_rows) else "NOT MET"))
    return {"S3a": {"status": s3a_status, "n_qualifying_pairs": len(qualifying),
                    "max_median_px": max((q["median_px"] for q in qualifying), default=None),
                    "violations": viol,
                    "per_engine_pair": {k: {"n": len(v), "max_px": max(v), "median_px": float(np.median(v))}
                                        for k, v in per_engine_pair.items()},
                    "floor_px": P3_AGREE_PX, "in_sample_max_px": 2.16},
            "S3b": {"status": s3b_status, "n_inconsistent_passes": len(incons), "rows": s3b_rows,
                    "min_px": P3_INCONSISTENT_MIN_PX,
                    "note": "null by construction when no INCONSISTENT pass occurs"},
            "status": s3a_status if s3b_status in ("MET", "CANNOT CHECK") else "NOT MET"}


def evaluate_s4(triangles: list[dict]) -> dict:
    if not triangles:
        return {"status": "CANNOT CHECK", "n_triangles": 0,
                "note": "no CONFIRMED triangle whose three edges are B1 successes formed"}
    ok = [t for t in triangles if t["loop_closure_residual_px"] < LOOP_REJECT_PX
          and all(s == "VERIFIED" for s in t["statuses"])]
    return {"status": "MET" if len(ok) == len(triangles) else "NOT MET",
            "n_triangles": len(triangles), "n_closing_and_verified": len(ok),
            "residuals_px": [t["loop_closure_residual_px"] for t in triangles],
            "reject_line_px": LOOP_REJECT_PX, "in_sample_range_px": [0.3654, 1.3358],
            "gauge_note": "exactly blind to per-image gauge error (EXP-012 section 6); "
                          "a closing loop is not an accuracy statement"}


def _spearman(x, y):
    return _e12.spearman(list(map(float, x)), list(map(float, y)))


def reported(rows: list[dict], triangles: list[dict], frames: dict) -> dict:
    """R1-R6, reported beside the criteria, not graded."""
    out: dict = {}
    # R1 separation test per engine
    r1 = {}
    for eng in ENGINES:
        sub = [r for r in rows if r.get("engine") == eng and "success" in r]
        if len({bool(r["success"]) for r in sub}) < 2:
            r1[ENGINE_NAME[eng]] = {"n": len(sub), "p_value": None, "note": "one outcome class only"}
            continue
        t = exact_separation_test([r["delta_incidence_deg"] for r in sub], [bool(r["success"]) for r in sub])
        r1[ENGINE_NAME[eng]] = {"n": len(sub), "n_success": sum(bool(r["success"]) for r in sub),
                                "statistic": t.statistic, "p_value": t.p_value, "exact": t.exact,
                                "perfectly_separated": t.perfectly_separated,
                                "note": "not called significant below n = 20 (Part 1 section 6.7)"}
    out["R1_separation"] = r1
    # R2 B4L yield inside the envelope
    by = {(r["edge"], r["engine"]): r for r in rows if "engine" in r}
    ratios = []
    for (edge, eng), r in by.items():
        if eng != "b1":
            continue
        lg = by.get((edge, "lg"))
        if lg and r["success"] and lg["success"] and 12.0 <= r["delta_incidence_deg"] <= 34.0 \
                and r["n_inliers"] > 0:
            ratios.append({"edge": edge, "ratio": lg["n_inliers"] / r["n_inliers"],
                           "delta_incidence_deg": r["delta_incidence_deg"]})
    out["R2_b4l_over_b1_inliers"] = {"n": len(ratios), "rows": ratios,
                                     "median_ratio": float(np.median([x["ratio"] for x in ratios])) if ratios else None,
                                     "prediction": "median in [3, 30] (in-sample 5-25x, D-047-N1)"}
    # R3 incidence ceiling
    r3 = {"le55": [], "65to70": [], "ge70": []}
    for r in rows:
        if r.get("engine") != "b1" or "success" not in r or r["delta_incidence_deg"] > 25.0:
            continue
        hi = max(r["src_incidence_deg"], r["dst_incidence_deg"])
        if hi <= 55:
            r3["le55"].append(bool(r["success"]))
        elif 65 <= hi < 70:
            r3["65to70"].append(bool(r["success"]))
        elif hi >= 70:
            r3["ge70"].append(bool(r["success"]))
    out["R3_incidence_ceiling"] = {k: {"n": len(v), "rate": float(np.mean(v)) if v else None}
                                   for k, v in r3.items()}
    out["R3_incidence_ceiling"]["prediction"] = "rate(ge70) < rate(le55) on Delta-inc <= 25 pairs"
    # R4 EXP-012's refuted H2
    if len(triangles) >= 3:
        rho, n = _spearman([t["min_edge_inliers"] for t in triangles],
                           [t["loop_closure_residual_px"] for t in triangles])
        out["R4_min_inliers_vs_loop"] = {"spearman_rho": rho, "n": n, "in_sample": 0.055}
    else:
        out["R4_min_inliers_vs_loop"] = {"n": len(triangles), "note": "fewer than 3 triangles"}
    # R5 resolution ratio and emission difference per pair
    r5 = {}
    for r in rows:
        if "engine" not in r or r["edge"] in r5:
            continue
        s, d = r["edge"].split(" -> ")
        fs, fd = frames[s], frames[d]
        rs, rd = fs["ode_map_resolution_m"], fd["ode_map_resolution_m"]
        r5[r["edge"]] = {"resolution_ratio": max(rs, rd) / min(rs, rd) if min(rs, rd) > 0 else None,
                         "emission_difference_deg": abs(fs["emission_deg"] - fd["emission_deg"]),
                         "emission_deg": [fs["emission_deg"], fd["emission_deg"]]}
    out["R5_per_pair"] = r5
    # R6 verdict bands and coverage on VERIFIED edges
    r6 = []
    for t in triangles:
        for v in t["verdicts"]:
            if v["verdict"]["status"] == "VERIFIED":
                r6.append({"edge": v["edge"], "confidence": v["verdict"].get("confidence"),
                           "grid_occupancy": v["verdict"].get("metrics", {}).get("coverage_occupancy"),
                           "max_uncovered_disc_ratio": v["verdict"].get("metrics", {}).get("coverage_max_gap")})
    out["R6_verified_edges"] = {"n": len(r6), "rows": r6,
                                "note": "both coverage metrics are recorded as mis-specified (D-057)"}
    return out


# ---------------------------------------------------------------------------
# S0(e) -- the reproduction gate
# ---------------------------------------------------------------------------
def run_gate() -> dict:
    man = json.loads((DATA / "manifests" / _rd07.WINDOWS["RD04"]).read_text(encoding="utf-8"))
    target = tuple(man["target_ground_point_lon_lat"])
    products = _rd07.load_products()
    need = {p for e in GATE_EDGES for p in e.split(" -> ")}
    ctx = {t["pdsid"]: _e7.FrameContext(t["pdsid"], t, products, target)
           for t in man["tiles"] if t["pdsid"] in need}
    edges = []
    for edge, want in GATE_EDGES.items():
        s, d = edge.split(" -> ")
        t0 = time.perf_counter()
        rec = _rd07.run_edge(ctx[s], ctx[d], "b1", True)
        got = int(rec["n_inliers"])
        edges.append({"edge": edge, "recorded_n_inliers": want, "n_inliers": got,
                      "reproduces": bool(got == want), "wall_s": round(time.perf_counter() - t0, 1)})
        print(f"  gate {edge}: {got} (recorded {want}) {'OK' if got == want else 'MISMATCH'}", flush=True)
    for c in ctx.values():
        c.release()
    s4 = _e12.run_s4()
    print(f"  gate RD-03 loop: {s4['recomputed_px']:.10f} px (recorded {GATE_LOOP_PX:.10f}) "
          f"{'OK' if s4['met'] else 'MISMATCH'}", flush=True)
    return {"criterion": "S0(e)", "edges": edges, "rd03_loop": s4,
            "met": bool(all(e["reproduces"] for e in edges) and s4["met"]
                        and abs(s4["recorded_px"] - GATE_LOOP_PX) < 1e-9)}


def frozen_code_record(runner_commit: str | None) -> dict:
    """S0(f): the runner commit and whether src/ changed since it."""
    def git(*a):
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    head = git("rev-parse", "HEAD")
    rec = {"head": head, "runner_commit": runner_commit,
           "head_utc": git("show", "-s", "--format=%cI", "HEAD")}
    if runner_commit:
        rec["src_diff_since_runner_commit"] = git("diff", "--stat", f"{runner_commit}..HEAD", "--", "src/")
        rec["src_unchanged_since_runner_commit"] = rec["src_diff_since_runner_commit"] == ""
    rec["src_dirty_now"] = git("status", "--porcelain", "--", "src/")
    return rec


# ---------------------------------------------------------------------------
# the held-out run
# ---------------------------------------------------------------------------
def load_window(window: str):
    man_path = DATA / "manifests" / f"exp018_{window}_manifest.json"
    geom_path = DATA / "manifests" / f"exp018_{window}_index_geometry.json"
    overlap_path = OUT / f"overlap_{window}.json"
    for p in (man_path, geom_path, overlap_path):
        if not p.exists():
            raise SystemExit(f"missing {p.relative_to(ROOT)}")
    man = json.loads(man_path.read_text(encoding="utf-8"))
    products = json.loads(geom_path.read_text(encoding="utf-8"))["products"]
    confirmed = _rd07.confirmed_pairs(overlap_path)
    overlap = json.loads(overlap_path.read_text(encoding="utf-8"))
    return man, products, confirmed, overlap


def geometry_pairs(man: dict, confirmed: set) -> list[dict]:
    inc = {t["pdsid"]: float(t["incidence_deg"]) for t in man["tiles"]}
    frames = sorted(inc, key=inc.get)
    pairs = []
    for s, d in itertools.combinations(frames, 2):
        if frozenset((s, d)) in confirmed:
            pairs.append({"edge": f"{s} -> {d}", "delta_incidence_deg": abs(inc[s] - inc[d])})
    return pairs


def confirmed_triangles(man: dict, confirmed: set) -> list[tuple]:
    frames = sorted(t["pdsid"] for t in man["tiles"])
    return [tri for tri in itertools.combinations(frames, 3)
            if all(frozenset(p) in confirmed for p in itertools.combinations(tri, 2))]


def run_window(window: str, man: dict, products: dict, confirmed: set, partial: Path):
    target = tuple(man["target_ground_point_lon_lat"])
    ctx = {t["pdsid"]: _e7.FrameContext(t["pdsid"], t, products, target) for t in man["tiles"]}
    frames = sorted(ctx, key=lambda p: ctx[p].incidence_published)
    done: dict = {"rows": [], "agreements": [], "edges_b1": {}}
    if partial.exists():
        prev = json.loads(partial.read_text(encoding="utf-8"))
        done["rows"], done["agreements"] = prev["rows"], prev["agreements"]
        print(f"  restart: {len(done['rows'])} rows checkpointed (crash policy, one restart)", flush=True)
    finished_edges = {r["edge"] for r in done["rows"] if "engine" in r}
    captured_b1: dict = {}
    for s, d in itertools.combinations(frames, 2):
        edge = f"{s} -> {d}"
        if frozenset((s, d)) not in confirmed:
            if not any(r.get("edge") == edge and "excluded" in r for r in done["rows"]):
                done["rows"].append({"window": window, "edge": edge, "excluded": "overlap not CONFIRMED"})
            continue
        fs, fr = ctx[s], ctx[d]
        d_inc = abs(fs.incidence_published - fr.incidence_published)
        ks = fs.tile.get("decimation", 2)
        ta = fs.tile
        shape_rot = north_up_east_right(fs.img(ks), fs.corners,
                                        line=ta["line0"] + (ta["n_lines"] - 1) / 2,
                                        sample=ta["sample0"] + (ta["n_samples"] - 1) / 2).image.shape
        if edge in finished_edges:
            # Already checkpointed: the B1 points for S4 are not on disk, so
            # re-run B1 only for the composition (its count must reproduce).
            b1_row = next(r for r in done["rows"] if r.get("edge") == edge and r.get("engine") == "b1")
            if b1_row["success"]:
                rec = _rd07.run_edge(fs, fr, "b1", True)
                if rec["n_inliers"] != b1_row["n_inliers"]:
                    raise SystemExit(f"restart re-match of {edge} gave {rec['n_inliers']} inliers, "
                                     f"checkpoint has {b1_row['n_inliers']}; environment drifted")
                captured_b1[edge] = (_captured["last"], shape_rot, b1_row)
            continue
        transforms: dict = {}
        for engine in ENGINES:
            t0 = time.perf_counter()
            rec = _rd07.run_edge(fs, fr, engine, True)
            res = _captured["last"]
            rec.update({"window": window, "edge": edge, "pair": sorted((s, d)), "engine": engine,
                        "north_up_applied": True, "delta_incidence_deg": d_inc,
                        "same_orbit_pair": s[:-2] == d[:-2],
                        "src_incidence_deg": fs.incidence_published,
                        "dst_incidence_deg": fr.incidence_published,
                        "src_emission_deg": fs.emission_deg, "dst_emission_deg": fr.emission_deg,
                        "shape_src_rotated": list(shape_rot),
                        "wall_s": time.perf_counter() - t0})
            done["rows"].append(rec)
            transforms[engine] = res.transform
            if engine == "b1":
                captured_b1[edge] = (res, shape_rot, rec)
            print(f"  [{window}] {s[-12:]}->{d[-12:]} dInc={d_inc:5.2f} {engine:3s}  inl={rec['n_inliers']:5d} "
                  f"{'SUCCESS' if rec['success'] else ('WRONG-PASS' if rec['wrong_pass'] else 'fail')}"
                  f"  geom={rec['geometry'].get('verdict', rec['geometry'].get('status'))}  "
                  f"({rec['wall_s']:.0f}s)", flush=True)
        for ea, eb in itertools.combinations(ENGINES, 2):
            agr = engine_agreement(ea, transforms.get(ea), eb, transforms.get(eb), shape_rot,
                                   floor_px=AGREEMENT_FLOOR_PX, step=16)
            done["agreements"].append({"window": window, "edge": edge, "engine_a": ea, "engine_b": eb,
                                       "median_px": None if agr.agree is None else agr.median_px,
                                       "p90_px": None if agr.agree is None else agr.p90_px,
                                       "max_px": None if agr.agree is None else agr.max_px,
                                       "agree": agr.agree, "statement": agr.statement})
        partial.write_text(json.dumps(done, indent=1, default=float), encoding="utf-8")
    # triangles: every CONFIRMED triangle whose three edges are B1 successes
    tri_out = []
    for tri in confirmed_triangles(man, confirmed):
        edge_by_pair = {}
        ok = True
        for a, b in itertools.combinations(tri, 2):
            key = next((e for e in captured_b1 if set(e.split(" -> ")) == {a, b}), None)
            if key is None or not captured_b1[key][2]["success"]:
                ok = False
                break
            res, shape_rot, row = captured_b1[key]
            src, dst = key.split(" -> ")
            edge_by_pair[frozenset((a, b))] = {
                "edge": key, "src": src, "dst": dst, "n_inliers": row["n_inliers"],
                "fit_rmse_px": row["fit_rmse_px"], "shape_src_rotated": list(shape_rot),
                "geometry_verdict_recorded": row["geometry"].get("verdict"),
                "_transform": res.transform, "_src_points": res.matches.src_points,
                "_dst_points": res.matches.dst_points,
                "_inlier_mask": np.asarray(res.inlier_mask, bool)}
        if not ok:
            continue
        r = _e12.run_triplet(window, tri, edge_by_pair)
        tri_out.append(r)
        print(f"  LOOP {'+'.join(f[-8:] for f in tri)}: {r['loop_closure_residual_px']:.4f} px -> "
              f"{','.join(sorted(set(r['statuses'])))}", flush=True)
    for c in ctx.values():
        c.release()
    return done["rows"], done["agreements"], tri_out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gate", action="store_true", help="S0(e) reproduction gate only")
    ap.add_argument("--window", default=None, help="held-out window name, e.g. apollo16")
    ap.add_argument("--runner-commit", default=None, help="commit hash of this runner (S0(f))")
    ap.add_argument("--out", default="exp018_results.json")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    if args.gate:
        out = OUT / "exp018_s0_gate.json"
        if out.exists():
            raise SystemExit(f"{out.relative_to(ROOT)} exists (integrity rule 4)")
        gate = run_gate()
        gate["environment"] = {"python": platform.python_version(), "numpy": np.__version__}
        gate["total_runtime_s"] = round(time.time() - t_start, 1)
        out.write_text(json.dumps(gate, indent=2, default=float), encoding="utf-8")
        print(f"S0(e) {'MET' if gate['met'] else 'NOT MET'}; wrote {out.relative_to(ROOT)}")
        if not gate["met"]:
            raise SystemExit(2)
        return

    if not args.window:
        raise SystemExit("--window is required unless --gate")
    if not learned_available():
        raise SystemExit("B4L unavailable: install kornia/torch")
    out = OUT / args.out
    rows_path = OUT / f"rows_{args.window}_nue.json"
    if out.exists() or rows_path.exists():
        raise SystemExit(f"{out.relative_to(ROOT)} or {rows_path.relative_to(ROOT)} exists (integrity rule 4)")

    man, products, confirmed, overlap = load_window(args.window)
    frames = {t["pdsid"]: t for t in man["tiles"]}

    print("S0(e) reproduction gate on the recorded tiles", flush=True)
    gate = run_gate()
    if not gate["met"]:
        (OUT / f"exp018_s0_gate_failed_{int(t_start)}.json").write_text(
            json.dumps(gate, indent=2, default=float), encoding="utf-8")
        raise SystemExit("S0(e) NOT MET: the runner does not reproduce the recorded counts; stop.")

    geo_pairs = geometry_pairs(man, confirmed)
    s5 = s5_counts(geo_pairs, len(frames), [float(t["incidence_deg"]) for t in man["tiles"]],
                   len(confirmed_triangles(man, confirmed)))
    print(f"S5 from geometry: {s5}", flush=True)

    print(f"\nheld-out run: {len(geo_pairs)} CONFIRMED pairs x {len(ENGINES)} engines", flush=True)
    partial = OUT / f"rows_{args.window}_nue.partial.json"
    rows, agreements, triangles = run_window(args.window, man, products, confirmed, partial)

    rows_doc = {"stage": STAGE, "window": args.window, "engines": list(ENGINES),
                "orientation": "north_up_east_right", "preregistration": PREREG,
                "environment": {"python": platform.python_version(), "numpy": np.__version__,
                                "opencv": __import__("cv2").__version__, "platform": platform.platform()},
                "total_runtime_s": time.time() - t_start, "rows": rows, "agreements": agreements}
    rows_path.write_text(json.dumps(rows_doc, indent=2, default=float), encoding="utf-8")

    edge_rows = [r for r in rows if "engine" in r]
    criteria = {
        "S0": {"a_untouched": "experiments/EXP-018/exp018_s0_untouched.json (pre-A1)",
               "b_separation": "Part 1 section 3.3 (> 500 km from RD-03/RD-04)",
               "c_overlap_before_pixels": {"n_confirmed": len(geo_pairs),
                                           "n_cases": len(overlap["cases"]),
                                           "excluded": [c["products"] for c in overlap["cases"]
                                                        if c["classification"] != "OVERLAP_CONFIRMED"]},
               "d_orientation": {"n_mirrored": sum(1 for r in edge_rows if r["engine"] == "b1"
                                                   and r["north_up"]["src"]["mirrored"]) if edge_rows else 0,
                                 "jacobian_sign_per_frame": {p: t.get("jacobian_determinant_sign")
                                                             for p, t in frames.items()}},
               "e_reproduction_gate": gate,
               "f_frozen_code": frozen_code_record(args.runner_commit)},
        "S1": evaluate_s1(edge_rows),
        "S2": evaluate_s2(edge_rows),
        "S3": evaluate_s3(agreements, edge_rows),
        "S4": evaluate_s4(triangles),
        "S5": s5,
    }
    doc = {
        "stage": STAGE, "window": args.window, "preregistration": PREREG,
        "frozen_pipeline": {"engines": list(ENGINES), "base": BASE, "orientation": "north_up_east_right",
                            "failure_rule": f"n_inliers <= {N_INLIERS_FAILURE_RULE} (D-023)",
                            "source_is_lower_incidence_frame": True},
        "frozen_predictions": {"P1": P1, "P1_ge40_in_sample": P1_GE40_INSAMPLE, "P2_upper": P2_UPPER,
                               "P2_in_sample": P2_INSAMPLE, "P3": {"agree_px": P3_AGREE_PX,
                                                                    "inconsistent_min_px": P3_INCONSISTENT_MIN_PX},
                               "P4_loop_reject_px": LOOP_REJECT_PX},
        "criteria": criteria,
        "reported": reported(edge_rows, triangles, frames),
        "triangles": triangles,
        "n_rows": len(edge_rows), "n_pairs": len(geo_pairs),
        "rows_artefact": str(rows_path.relative_to(ROOT)).replace("\\", "/"),
        "environment": rows_doc["environment"],
        "total_runtime_s": round(time.time() - t_start, 1),
        "claims_not_supported": [
            "Not an FA or FR measurement: the wrong-pass count is a bound at a ~250 px floor; FR is not measured.",
            "Not an accuracy claim: no ground truth; geometry corroboration at its floor; loop closure up to per-image gauge.",
            "One window, <= 8 frames, one illumination axis (Delta-incidence), near-nadir, native NAC rung only.",
            "Held-out rows are never pooled with the 42 in-sample pairs.",
        ],
    }
    out.write_text(json.dumps(doc, indent=2, default=float), encoding="utf-8")
    if partial.exists():
        partial.unlink()
    print("\n== criteria ==")
    for k in ("S1", "S2", "S3", "S4"):
        print(f"  {k}: {criteria[k]['status']}")
    print(f"  S5: {'MET' if s5['met'] else 'NOT MET'}")
    print(f"wrote {out.relative_to(ROOT)} in {doc['total_runtime_s']}s")


if __name__ == "__main__":
    main()
