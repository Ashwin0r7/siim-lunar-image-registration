"""EXP-012 S3 — does the shipped verdict ever return VERIFIED on an adversarial case?

Part 1 §3.6 and §4 H3. The arm was specified and **not run** when EXP-012's
Part 2 was written; it is run here against the criterion exactly as frozen:

> **S3 MET** if zero adversarial cases are VERIFIED.
> **Prediction: NOT MET.** `verdict.py` already documents that a 64-px-wrong
> transform whose error cancels in the loop returns VERIFIED / high -- the
> per-image gauge null space (ADR-0011 N1). This stage predicts its own
> criterion will fail, and will report the gauge-error case as the reason.

**Scope, and why Part A is settled analytically rather than run.** EXP-002
objective 4 builds two families. Part A is single-edge correspondence sets:
there is no third image, so `loop_error_px` is absent and `assess()` cannot
return VERIFIED for *any* of them, correct or adversarial -- the ceiling is
INCONCLUSIVE by construction. Running 96 of those to observe a foregone
outcome would pad the artefact, so the reason is recorded instead and S3 is
decided on Part B, the family that can actually reach VERIFIED.

**How the Part B cases are obtained, and how the rebuild is proved faithful.**
`make_cycle_case` returns residuals, not the transforms behind them, and
`assess()` needs correspondences. Its construction is therefore rebuilt here
from the same recipe -- and the rebuild is **not trusted**: for every case the
three rebuilt edges are composed and their loop closure must equal the value
`make_cycle_case` recorded, to 1e-9 px. A rebuild that has drifted from the
original cannot pass that check, and the run stops if one does.

    python scripts/run_exp012_s3.py
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

from siim.demo.verdict import assess  # noqa: E402
from siim.evaluation.gtfree import loop_closure  # noqa: E402
from siim.geometry import similarity, translation  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "_exp002_gtfree", ROOT / "scripts" / "run_exp002_gtfree.py")
_g = importlib.util.module_from_spec(_spec)
sys.modules["_exp002_gtfree"] = _g
_spec.loader.exec_module(_g)

OUT = ROOT / "experiments" / "EXP-012"
SHAPE = _g.SHAPE
SEEDS = list(range(9001, 9013))     # 12 per kind, disjoint from EXP-002's seeds
N_POINTS = 400                      # "400 well-spread inliers", verdict.py:66-70
REBUILD_TOL_PX = 1e-9


def rebuild_cycle(kind: str, seed: int):
    """The three estimated edges of a cycle case, from `make_cycle_case`'s recipe.

    The rng draw order is reproduced exactly -- ``correct`` consumes four
    ``jitter`` calls and the adversarial kinds consume none -- because the
    loop-closure control below compares against the value the original
    produced, and a different draw order would not match.
    """
    rng = np.random.default_rng(seed)

    def jitter(s):
        return translation(float(rng.normal(0, s)), float(rng.normal(0, s)))

    t_ab = similarity(1.02, np.deg2rad(3.0), 9.0, -6.0)
    t_bc = similarity(0.99, np.deg2rad(-2.0), -5.0, 7.0)
    t_ca = (t_bc @ t_ab).inverse()
    shift = translation(_g.LATTICE_PERIOD, 0.0)

    if kind == "correct":
        e_ab, e_bc, e_ca = jitter(0.3) @ t_ab, jitter(0.3) @ t_bc, jitter(0.3) @ t_ca
    elif kind == "lattice_all_edges":
        e_ab, e_bc, e_ca = shift @ t_ab, shift @ t_bc, shift @ t_ca
    elif kind == "lattice_one_edge":
        e_ab, e_bc, e_ca = shift @ t_ab, t_bc, t_ca
    elif kind == "symmetric_wrong":
        e_ab, e_bc, e_ca = shift @ t_ab, t_bc, t_ca
    else:
        raise ValueError(kind)
    return e_ab, e_bc, e_ca


def main() -> None:
    out_path = OUT / "exp012_s3_adversarial.json"
    if out_path.exists():
        raise SystemExit(f"{out_path.relative_to(ROOT)} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    rows, rebuild_checks = [], []
    for kind in _g.CYCLE_KINDS:
        for seed in SEEDS:
            case = _g.make_cycle_case(kind, seed)
            e_ab, e_bc, e_ca = rebuild_cycle(kind, seed)

            # --- control: the rebuild must reproduce the recorded loop ------
            got = float(loop_closure([e_ab, e_bc, e_ca], SHAPE))
            want = float(case["loop_error"])
            diff = abs(got - want)
            rebuild_checks.append(diff)
            if diff > REBUILD_TOL_PX:
                raise SystemExit(
                    f"rebuild control FAILED on {kind} seed {seed}: loop "
                    f"closure {got} vs recorded {want} (diff {diff}). The "
                    f"reconstruction has drifted from make_cycle_case; the "
                    f"stage stops rather than judge a different construction.")

            rng = np.random.default_rng(seed + 500)
            src = rng.uniform(0, SHAPE[0], size=(N_POINTS, 2))
            dst = e_ab.apply(src) + rng.normal(0, 0.4, size=src.shape)
            mask = np.ones(len(src), bool)
            v = assess(transform=e_ab, src_points=src, dst_points=dst,
                       inlier_mask=mask, shape=SHAPE, fit_rmse=None,
                       loop_error_px=want)
            rows.append({
                "kind": kind, "seed": seed,
                "is_wrong": bool(case["is_wrong"]),
                "n_points": N_POINTS,
                "loop_error_px": want,
                "cycle_error_px": float(case["cycle_error"]),
                "true_transform_error_px": float(case["true_transform_error"]),
                "status": v.status, "confidence": v.confidence,
                "coverage_max_gap": (v.metrics or {}).get("coverage_max_gap"),
            })

    adversarial = [r for r in rows if r["is_wrong"]]
    verified_adv = [r for r in adversarial if r["status"] == "VERIFIED"]
    controls = [r for r in rows if not r["is_wrong"]]

    by_kind: dict[str, dict] = {}
    for r in rows:
        k = by_kind.setdefault(r["kind"], {
            "n": 0, "is_wrong": r["is_wrong"], "statuses": {},
            "median_true_error_px": None, "median_loop_px": None})
        k["n"] += 1
        k["statuses"][r["status"]] = k["statuses"].get(r["status"], 0) + 1
    for kind, k in by_kind.items():
        sel = [r for r in rows if r["kind"] == kind]
        k["median_true_error_px"] = float(np.median([r["true_transform_error_px"] for r in sel]))
        k["median_loop_px"] = float(np.median([r["loop_error_px"] for r in sel]))

    doc = {
        "stage": "EXP-012", "criterion": "S3",
        "statement": "zero adversarial cases are VERIFIED",
        "preregistered_prediction":
            "NOT MET (confidence HIGH) -- the per-image gauge null space, ADR-0011 N1",
        "met": not verified_adv,
        "n_rows": len(rows),
        "n_adversarial": len(adversarial),
        "n_adversarial_verified": len(verified_adv),
        "n_controls": len(controls),
        "n_controls_verified": sum(1 for r in controls if r["status"] == "VERIFIED"),
        "verified_adversarial_kinds": sorted({r["kind"] for r in verified_adv}),
        "by_kind": by_kind,
        "rebuild_control": {
            "statement": "each rebuilt triplet's loop closure equals the value "
                         "make_cycle_case recorded",
            "met": True, "n_checked": len(rebuild_checks),
            "max_abs_difference_px": float(max(rebuild_checks)),
            "tolerance_px": REBUILD_TOL_PX,
        },
        "part_a_not_run": (
            "EXP-002 objective 4's Part A cases are single-edge correspondence "
            "sets with no third image, so loop_error_px is absent and assess() "
            "cannot return VERIFIED for any of them -- the ceiling is "
            "INCONCLUSIVE by construction. Recorded as a reason rather than "
            "run to observe a foregone outcome."),
        "case_source": "scripts/run_exp002_gtfree.py (EXP-002 objective 4)",
        "rows": rows,
        "claims_not_supported": [
            "Synthetic constructions, not real imagery.",
            "Correspondences for each case are generated from that case's own "
            "estimated (wrong) transform; they are the situation the verdict "
            "faces, not independent evidence about it.",
        ],
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
        "total_runtime_s": round(time.time() - t0, 1),
    }
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    print(f"rebuild control: {len(rebuild_checks)} triplets, max diff "
          f"{max(rebuild_checks):.2e} px -- MET\n")
    for kind, k in sorted(by_kind.items(), key=lambda kv: (not kv[1]["is_wrong"], kv[0])):
        flag = "ADVERSARIAL" if k["is_wrong"] else "control    "
        print(f"  {flag} {kind:20s} loop {k['median_loop_px']:9.3f} px  "
              f"true err {k['median_true_error_px']:8.3f} px  {k['statuses']}")
    print(f"\nS3 {'MET' if doc['met'] else 'NOT MET'}", end="")
    if verified_adv:
        print(f" -- {len(verified_adv)} adversarial cases VERIFIED, kinds "
              f"{doc['verified_adversarial_kinds']}")
    else:
        print()
    print(f"wrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
