"""EXP-012 — supplementary: the adversarial case the frozen set does not contain.

**This is NOT part of S3 and does not change it.** S3 was decided on EXP-002
objective 4's constructions, exactly as Part 1 §3.6 fixed, and came out **MET**
(`exp012_s3_adversarial.json`: zero adversarial cases VERIFIED). This script
records why that result is weaker than it reads.

Every adversarial kind in that set is a **per-edge** error -- a lattice shift
applied to one edge, or to each edge independently. Loop closure is *designed*
to catch exactly that subspace, and it did: 62.7 px and 190.1 px residuals,
REJECTED 36 / 36. Even `symmetric_wrong`, whose own comment calls it "the blind
spot cycle consistency cannot see", is a per-edge error as far as the *loop* is
concerned, and the loop caught it.

The blind spot ADR-0011 note N1 names is different and is **not in the set**: a
**per-image gauge**, where each image carries its own coordinate error and the
adjacent terms cancel around the composition:

    T_AB = G_B o T_AB o G_A^-1 ,  T_BC = G_C o T_BC o G_B^-1 ,  T_CA = G_A o T_CA o G_C^-1
    =>  T_CA o T_BC o T_AB  =  I   exactly, however wrong each edge is

`verdict.py` states the consequence in prose and pins it on one hand-built case
in `tests/test_demo_verdict.py`. This script measures it as a population, so
the limitation is a recorded number rather than an assertion.

Written to its own artefact so the frozen-set result stays untouched.

    python scripts/run_exp012_s3_gauge.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.demo.verdict import assess  # noqa: E402
from siim.evaluation.gtfree import loop_closure  # noqa: E402
from siim.geometry import endpoint_error, similarity, translation  # noqa: E402

OUT = ROOT / "experiments" / "EXP-012"
SHAPE = (512, 512)
SEEDS = list(range(9001, 9013))
N_POINTS = 400
LOOP_TOL_PX = 1e-9


def gauge_case(seed: int, magnitude_px: float):
    """A three-image set whose every edge is wrong, and whose loop still closes.

    Each image is given its own coordinate gauge ``G_i`` -- a small rotation
    and a translation of ``magnitude_px`` -- and every edge is estimated in
    those gauged frames. The per-image terms cancel around the loop, so the
    residual is zero by construction while each individual edge is wrong.
    """
    rng = np.random.default_rng(seed)
    t_ab = similarity(1.02, np.deg2rad(3.0), 9.0, -6.0)
    t_bc = similarity(0.99, np.deg2rad(-2.0), -5.0, 7.0)
    t_ca = (t_bc @ t_ab).inverse()

    def gauge():
        ang = float(rng.normal(0, 0.4))
        dx, dy = rng.normal(0, magnitude_px, size=2)
        return similarity(1.0, np.deg2rad(ang), float(dx), float(dy))

    g_a, g_b, g_c = gauge(), gauge(), gauge()
    e_ab = g_b @ t_ab @ g_a.inverse()
    e_bc = g_c @ t_bc @ g_b.inverse()
    e_ca = g_a @ t_ca @ g_c.inverse()
    true_err = endpoint_error(e_ab, t_ab, SHAPE, step=16).median
    return e_ab, e_bc, e_ca, float(true_err)


def main() -> None:
    out_path = OUT / "exp012_s3_gauge_probe.json"
    if out_path.exists():
        raise SystemExit(f"{out_path.relative_to(ROOT)} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    rows = []
    for magnitude in (8.0, 32.0, 64.0):
        for seed in SEEDS:
            e_ab, e_bc, e_ca, true_err = gauge_case(seed, magnitude)
            loop = float(loop_closure([e_ab, e_bc, e_ca], SHAPE))

            rng = np.random.default_rng(seed + 900)
            src = rng.uniform(0, SHAPE[0], size=(N_POINTS, 2))
            dst = e_ab.apply(src) + rng.normal(0, 0.4, size=src.shape)
            mask = np.ones(len(src), bool)
            v = assess(transform=e_ab, src_points=src, dst_points=dst,
                       inlier_mask=mask, shape=SHAPE, fit_rmse=None,
                       loop_error_px=loop)
            rows.append({
                "gauge_magnitude_px": magnitude, "seed": seed,
                "loop_error_px": loop,
                "true_transform_error_px": true_err,
                "status": v.status, "confidence": v.confidence,
                "coverage_max_gap": (v.metrics or {}).get("coverage_max_gap"),
            })

    # the construction's own control: the loop must close, or it is not a gauge case
    max_loop = max(r["loop_error_px"] for r in rows)
    if max_loop > LOOP_TOL_PX:
        raise SystemExit(
            f"construction control FAILED: max loop residual {max_loop} px "
            f"exceeds {LOOP_TOL_PX}. These are not per-image gauge cases and "
            f"nothing is reported from them.")

    verified = [r for r in rows if r["status"] == "VERIFIED"]
    by_mag = {}
    for m in sorted({r["gauge_magnitude_px"] for r in rows}):
        sel = [r for r in rows if r["gauge_magnitude_px"] == m]
        by_mag[str(m)] = {
            "n": len(sel),
            "n_verified": sum(1 for r in sel if r["status"] == "VERIFIED"),
            "median_true_error_px": float(np.median([r["true_transform_error_px"] for r in sel])),
            "max_loop_error_px": float(max(r["loop_error_px"] for r in sel)),
            "confidences": {c: sum(1 for r in sel if r["confidence"] == c)
                            for c in sorted({r["confidence"] for r in sel})},
        }

    doc = {
        "stage": "EXP-012",
        "what": "supplementary probe -- the per-image gauge case EXP-002's "
                "adversarial set does not contain",
        "not_part_of_s3": (
            "S3 was decided on EXP-002 objective 4's constructions exactly as "
            "Part 1 §3.6 fixed, and is MET (exp012_s3_adversarial.json). This "
            "probe adds a construction outside that set and does not change S3."),
        "why_it_matters": (
            "Every adversarial kind in the frozen set is a per-EDGE error, the "
            "subspace loop closure is designed to detect -- and it detected all "
            "36 of them. The null space named in ADR-0011 N1 is per-IMAGE, and "
            "the set contains no such case, so S3 MET does not clear it."),
        "construction": "T_AB = G_B o T_AB o G_A^-1 (and cyclically); the "
                        "per-image terms cancel around the loop",
        "construction_control": {
            "statement": "every case's loop closes to ~0, or it is not a gauge case",
            "met": True, "max_loop_error_px": max_loop, "tolerance_px": LOOP_TOL_PX,
        },
        "n_rows": len(rows),
        "n_verified": len(verified),
        "verified_fraction": len(verified) / len(rows),
        "by_gauge_magnitude": by_mag,
        "rows": rows,
        "claims_not_supported": [
            "Synthetic constructions, not real imagery.",
            "This is a limitation of loop closure as a check, not a defect in "
            "its implementation: the invariance is an identity, stated in "
            "gtfree.loop_closure's docstring and in ADR-0011 N1.",
            "It says nothing about how often per-image gauge error occurs on "
            "real products; that is unmeasured.",
        ],
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
        "total_runtime_s": round(time.time() - t0, 1),
    }
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    print(f"construction control: max loop residual {max_loop:.2e} px -- MET\n")
    print(f"{'gauge px':>9s} {'n':>4s} {'VERIFIED':>9s} {'median true error':>18s}  confidences")
    for m, k in by_mag.items():
        print(f"{float(m):9.1f} {k['n']:4d} {k['n_verified']:9d} "
              f"{k['median_true_error_px']:18.2f}  {k['confidences']}")
    print(f"\n{len(verified)} of {len(rows)} per-image gauge cases return VERIFIED "
          f"while every edge is wrong.")
    print(f"wrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
