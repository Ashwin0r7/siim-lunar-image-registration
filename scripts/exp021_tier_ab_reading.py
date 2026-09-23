"""EXP-021 Part 2 SS12 -- the tier A u B reading, enumerated edge by edge.

    python scripts/exp021_tier_ab_reading.py

The runner records S5's tier A u B variant as rates only. Part 2 SS12 reads
it properly: which edges are WRONG, which are AMBIGUOUS, which were refused
while correct. This script does that with the runner's own functions and the
RECORDED legs (EXP-019's matrices for the calibration site, the artefact's
``validation_legs`` for the validation site) -- no registration is re-run --
and asserts that every frame's tier reproduces the artefact before counting.

Writes ``experiments/EXP-021/exp021_s5_tier_ab_reading.json``; refuses to
overwrite it (integrity rule 4). ``exp021_results.json`` is not touched.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "experiments" / "EXP-021" / "exp021_s5_tier_ab_reading.json"


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"{OUT} exists (integrity rule 4)")
    spec = importlib.util.spec_from_file_location("_r21", ROOT / "scripts" / "run_exp021.py")
    r = importlib.util.module_from_spec(spec)
    sys.modules["_r21"] = r
    spec.loader.exec_module(r)
    e19 = json.loads((ROOT / "experiments/EXP-019/exp019_results.json").read_text(encoding="utf-8"))
    art = json.loads((ROOT / "experiments/EXP-021/exp021_results.json").read_text(encoding="utf-8"))

    frames = {}
    for s in r._e19.nac_sources():
        r._e19.prepare_nac(s)
        frames[s.key] = dict(r.frame_record(s, e19["cells"].get(s.key),
                                            e19["second_engine"].get(s.key)), site="C")
    for s in r.v_sources():
        r._e19.prepare_nac(s)
        frames[s.key] = dict(r.frame_record(s, art["validation_legs"]["B1"][s.key],
                                            art["validation_legs"]["B4L"][s.key]), site="V")
    for k, v in art["frames"].items():
        if (v["tier_A"], v["tier_B"]) != (frames[k]["tier_A"], frames[k]["tier_B"]):
            raise SystemExit(f"tier of {k} does not reproduce the artefact")

    rows = r.load_rows()
    tris = r.triangles(rows, frames)
    r.attach_l2(rows, tris)
    cl = r.classify_all(rows, frames, r.CORRECT_REF_PX, r.WRONG_REF_PX, "AB")
    tier = {k: ("A" if v["tier_A"] else "B" if v["tier_B"] else "-") for k, v in frames.items()}
    for c in cl:
        a, b = c["edge"].split(" -> ")
        c["tier_src"], c["tier_dst"] = tier[f"{c['window']}/{a}"], tier[f"{c['window']}/{b}"]

    lab = ("CORRECT", "AMBIGUOUS", "WRONG")
    summary = {}
    for sites_name, sites in (("V", ("V",)), ("V+C", ("V", "C"))):
        for eng_name, engs in (("B1", ("b1",)), ("pooled", ("b1", "lg", "xf"))):
            s = [c for c in cl if c["site"] in sites and c["engine"] in engs and c["cls"] in lab]
            ver = [c for c in s if c["verified"]]
            summary[f"{sites_name}|{eng_name}"] = {
                "classes": dict(Counter(c["cls"] for c in s)),
                "verified": len(ver),
                "verified_wrong": sum(c["cls"] == "WRONG" for c in ver),
                "verified_ambiguous": sum(c["cls"] == "AMBIGUOUS" for c in ver),
                "wrong_total": sum(c["cls"] == "WRONG" for c in s),
                "hard_negatives": sum(c["cls"] == "WRONG" and c["n_inliers"] > r.RULE for c in s),
                "max_inliers_on_a_wrong_edge": max([c["n_inliers"] for c in s
                                                    if c["cls"] == "WRONG"] or [0]),
            }
    notable = [c for c in cl if c["cls"] in ("WRONG", "AMBIGUOUS")
               or (c["cls"] == "CORRECT" and (not c["pass"] or (c["reachable"] and not c["verified"])))]
    doc = {"stage": "EXP-021", "reading": "Part 2 SS12, tier A u B, CORRECT <= 1.0, WRONG > 3.0 ref px",
           "source_artefacts": ["experiments/EXP-021/exp021_results.json",
                                "experiments/EXP-019/exp019_results.json"],
           "re_registration": "none -- recorded legs only",
           "summary": summary, "notable_edges": notable,
           "leg_agreement_on_non_tier_A_frames": {
               k: {"incidence_deg": v["incidence_deg"], "b1_n_inliers": v["b1_n_inliers"],
                   "b4l_n_inliers": v["b4l_n_inliers"], "agreement_ref_px": v["leg_agreement_ref_px"],
                   "tier": tier[k]} for k, v in frames.items() if not v["tier_A"]}}
    OUT.write_text(json.dumps(doc, indent=1, default=float), encoding="utf-8")
    for k, v in summary.items():
        print(k, v)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
