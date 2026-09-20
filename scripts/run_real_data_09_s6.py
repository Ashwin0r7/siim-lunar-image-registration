"""REAL-DATA-09 S6 — the control that must hold before any result is reported.

Part 1 §6: *"The `none` arm on the six recorded NAC edges reproduces 5365,
1656, 4, 4, 7, 3 in this run's environment; no Chandrayaan-2 step changes any
NAC number. If S6 fails the stage stops."*

The six edges and their recorded counts are read from the artefacts that
recorded them -- REAL-DATA-03's and REAL-DATA-04's loop-closure files -- rather
than typed here, so this control cannot drift from what it is checking (the
lesson of E-038).

Nothing about Chandrayaan-2 is imported, loaded or touched: the point is to
show the NAC numbers are what they always were, in the environment that just
produced the TMC-2 rows.

    python scripts/run_real_data_09_s6.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location("_exp007", ROOT / "scripts" / "run_exp007.py")
_e7 = importlib.util.module_from_spec(_spec)
sys.modules["_exp007"] = _e7
_spec.loader.exec_module(_e7)

DATA = ROOT / "data"
OUT = ROOT / "experiments" / "REAL-DATA-09"
BASE = {"model": "affine", "ransac_threshold_px": 3.0, "seed": 0}

#: The artefacts that recorded the six edges, with the tile manifest each used.
RECORDED = [
    ("experiments/REAL-DATA-03/loop_closure_triplet.json", "real_triplet_geo_manifest.json"),
    ("experiments/REAL-DATA-04/loop_closure_real_data_04.json", "real_quad_d_geo_manifest.json"),
]


def products() -> dict:
    out: dict = {}
    for name in _e7.GEOMETRY_FILES + ["real_data_07_index_geometry.json"]:
        p = DATA / "manifests" / name
        if p.exists():
            out.update(json.loads(p.read_text(encoding="utf-8"))["products"])
    return out


def main() -> None:
    out_path = OUT / "real_data_09_s6_control.json"
    if out_path.exists():
        raise SystemExit(f"{out_path.relative_to(ROOT)} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)

    prod = products()
    rows, t0 = [], time.time()
    for art_rel, man_name in RECORDED:
        art = json.loads((ROOT / art_rel).read_text(encoding="utf-8"))
        man = json.loads((DATA / "manifests" / man_name).read_text(encoding="utf-8"))
        target = tuple(man["target_ground_point_lon_lat"])
        ctx = {t["pdsid"]: _e7.FrameContext(t["pdsid"], t, prod, target)
               for t in man["tiles"]}
        for e in art["edges"]:
            src, dst = (s.strip() for s in e["edge"].split("->"))
            if src not in ctx or dst not in ctx:
                rows.append({"edge": e["edge"], "skipped": "tile not in manifest"})
                continue
            fs, fr = ctx[src], ctx[dst]
            ks = fs.tile.get("decimation", 2)
            kr = fr.tile.get("decimation", 2)
            res = _e7.run_engine("b1", fs.img(ks), fr.img(kr), BASE)
            mask = (np.asarray(res.inlier_mask, bool) if np.size(res.inlier_mask)
                    else np.zeros(0, bool))
            got = int(mask.sum())
            want = int(e["n_inliers"])
            rows.append({"edge": e["edge"], "artefact": art_rel,
                         "recorded_n_inliers": want, "n_inliers": got,
                         "reproduces_recorded": got == want})
            print(f"  {e['edge']:56s} recorded={want:6d} got={got:6d} "
                  f"{'OK' if got == want else 'MISMATCH'}", flush=True)
        for f in ctx.values():
            f.release()

    checked = [r for r in rows if "reproduces_recorded" in r]
    met = bool(checked) and all(r["reproduces_recorded"] for r in checked)
    doc = {"stage": "REAL-DATA-09", "criterion": "S6",
           "statement": ("the `none` arm on the recorded NAC edges reproduces "
                         "its recorded inlier counts in this run's environment; "
                         "no Chandrayaan-2 step changes any NAC number"),
           "met": met, "n_edges_checked": len(checked),
           "recorded_counts": sorted(r["recorded_n_inliers"] for r in checked),
           "rows": rows,
           "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
           "total_runtime_s": round(time.time() - t0, 1)}
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"\nS6 {'MET' if met else 'NOT MET'} on {len(checked)} edges "
          f"-> {out_path.relative_to(ROOT)}")
    if not met:
        raise SystemExit("S6 NOT MET: the stage stops (Part 1 §6).")


if __name__ == "__main__":
    main()
