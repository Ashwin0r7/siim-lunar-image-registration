"""Local FastAPI backend for the SIIM demonstrator.

Deliberately small and local (§15): one process, no database, no auth, no
external calls at request time. It wraps the existing SIIM modules rather than
reimplementing anything, so what the demo shows is what the experiments
measured.

Honesty rules baked into the response shape (§16):

* every result carries ``computation``:

  - ``"live"`` -- computed in this request, for the synthetic scenarios;
  - ``"recorded_artefact"`` -- read from a file under ``experiments/``, for
    the real-data scenarios, which name the artefact they came from.

  Nothing may be displayed as live that was not computed in the request, and
  nothing read from disk may be displayed as live;
* every result carries ``data_source`` = ``"synthetic"`` or ``"real_lro_nac"``;
* ``fit_rmse`` is returned but flagged ``excluded_from_verdict`` so the UI
  cannot present it as the reason for anything.

Why the real-data scenarios read rather than recompute
------------------------------------------------------
The demo's real-data numbers are REAL-DATA-04's published result. Recomputing
them for display would let the demo drift from the stage report that justifies
them, and would put a live 10-second registration on the critical path of a
presentation. So they are read from the recorded artefacts and carry their
provenance -- see :mod:`siim.demo.evidence`. The correspondence *overlay*
coordinates come from a build-time asset that is written only when re-running
the identical seeded pipeline reproduces every recorded statistic exactly.

Run:  python -m uvicorn siim.demo.api:app --reload --port 8000
      (from the repo root, with src/ on PYTHONPATH)
"""

from __future__ import annotations

import base64
import io
import json
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from siim.baselines import run_rootsift_baseline  # noqa: E402
from siim.data import TERRAIN_REGIMES, height_field, make_pair  # noqa: E402
from siim.demo.chandrayaan2 import (  # noqa: E402
    chandrayaan2_evidence,
    chandrayaan2_status,
)
from siim.demo.exp006 import exp006_evidence, exp006_status  # noqa: E402
from siim.demo.exp012 import exp012_evidence, exp012_status  # noqa: E402
from siim.demo.exp013 import exp013_evidence, exp013_status  # noqa: E402
from siim.demo.exp016 import exp016_evidence, exp016_status  # noqa: E402
from siim.demo.exp017 import exp017_evidence, exp017_status  # noqa: E402
from siim.demo.exp019 import exp019_evidence, exp019_status  # noqa: E402
from siim.demo.exp020 import exp020_evidence, exp020_status  # noqa: E402
from siim.demo.evidence import (  # noqa: E402
    INLIER_FAILURE_RULE,
    REAL_SCENARIOS,
    DemoDataMissing,
    build_real_scenario,
    engines_evidence,
    engines_status,
    illumination_evidence,
    real_data_status,
)
from siim.demo.verdict import (  # noqa: E402
    EXCLUDED_FROM_VERDICT,
    LOOP_ERROR_REJECT_PX,
    assess,
)
from siim.evaluation import correspondence_metrics  # noqa: E402
from siim.evaluation.gtfree import loop_closure  # noqa: E402
from siim.geometry import Transform, affine, anchor_at, image_centre, translation  # noqa: E402

app = FastAPI(title="SIIM — Sun-angle Invariant Image Matching",
              version="0.1.0-demo")

STATIC = Path(__file__).resolve().parent / "static"
ASSETS = Path(__file__).resolve().parent / "assets"
SHAPE = (384, 384)

#: Failures that may occur while building the third view or closing the loop,
#: and that are attributable to the data rather than to a defect here.
#: ``numpy.linalg.LinAlgError`` subclasses ``ValueError``; ``cv2.error`` does
#: not, so it is named. Anything OUTSIDE this tuple deliberately propagates and
#: surfaces as a 500: an unexpected exception is a bug to see, not a result to
#: report, and the one thing this endpoint must never do is describe a crash as
#: a property of the imagery.
LOOP_CLOSURE_ERRORS = (ValueError, ArithmeticError, RuntimeError, cv2.error)


# ---------------------------------------------------------------------------
# scenarios
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, dict[str, Any]] = {
    "easy_same_sun": {
        "title": "Baseline — identical illumination",
        "regime": "A_highlands_moderate", "delta_azimuth": 0.0, "seed": 9001,
        "blurb": "Control case. Both images lit identically; registration should succeed.",
        "adversarial": False,
    },
    "illumination_cliff": {
        "title": "Sun azimuth 30° apart",
        "regime": "A_highlands_moderate", "delta_azimuth": 30.0, "seed": 9001,
        "blurb": ("Past the measured cliff. EXP-003 put the last fully-successful "
                  "Δazimuth at 27° on this regime across 3 seeds."),
        "adversarial": False,
    },
    "mare_starved": {
        "title": "Realistic mare — feature starvation",
        "regime": "A_mare_moderate", "delta_azimuth": 21.0, "seed": 9002,
        "blurb": ("Low-texture mare yields ~24 keypoints at 384². The hardest "
                  "realistic regime, and the project's priority benchmark."),
        "adversarial": False,
    },
    "coherent_wrong": {
        "title": "⚠ The trap — a confident, self-consistent, WRONG answer",
        "regime": "A_highlands_moderate", "delta_azimuth": 0.0, "seed": 9003,
        "blurb": ("Correspondences displaced by exactly one crater spacing. The fit "
                  "is near-perfect and the answer is 64 px wrong. This is a "
                  "CONTROLLED SYNTHETIC construction, reproducing the failure "
                  "EXP-001 measured on generated terrain — not a real-data failure."),
        "adversarial": True,
        "shift_px": 64.0,
    },
}

# -- REAL DATA -------------------------------------------------------------
# Declared in siim.demo.evidence, which reads every number out of a recorded
# artefact under experiments/. Merged in rather than written out here so the
# demo cannot acquire a real-data number that no experiment produced.
#
# REAL-DATA-01's pair was removed from this list, deliberately. It was the
# `real_lro_nac` scenario, and REAL-DATA-02 later measured its two tiles to be
# **22.75 km apart, sharing 0.0000 km2** (E-028, E-029). Demonstrating a
# registration failure on tiles that do not overlap would show the audience a
# failure whose cause is the acquisition, not the matcher -- the exact
# confusion REAL-DATA-02 and -03 existed to remove. It is superseded by the
# REAL-DATA-04 edges below, whose overlap is CONFIRMED before the matcher runs.
for _sid, _sc in REAL_SCENARIOS.items():
    SCENARIOS[_sid] = {
        "title": _sc["title"], "regime": None, "delta_azimuth": None,
        "seed": None, "blurb": _sc["blurb"], "adversarial": False,
        "real": True, "role": _sc["role"], "subtitle": _sc["subtitle"],
        "headline": _sc["headline"],
    }


class RunRequest(BaseModel):
    scenario: str = "easy_same_sun"
    model: str = "affine"


def _png_b64(arr: np.ndarray) -> str:
    """Grayscale array -> base64 PNG, for inline display."""
    from PIL import Image
    a = np.asarray(arr, dtype=np.float64)
    finite = np.isfinite(a)
    if finite.any():
        lo, hi = np.nanmin(a[finite]), np.nanmax(a[finite])
        a = (a - lo) / (hi - lo) if hi > lo else np.zeros_like(a)
    a = np.clip(np.nan_to_num(a), 0, 1)
    buf = io.BytesIO()
    Image.fromarray((a * 255).astype(np.uint8)).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _build_pair(sc: dict):
    reg = TERRAIN_REGIMES[sc["regime"]]
    field = height_field(
        (SHAPE[0] * 2, SHAPE[1] * 2), np.random.default_rng(sc["seed"]),
        scene=reg.scene, target_slope_median_deg=reg.target_slope_median_deg,
        octaves=reg.octaves, persistence=reg.persistence,
        crater_density=reg.crater_density, pixel_scale=1.0,
    )
    rng = np.random.default_rng(sc["seed"] * 31)
    c = image_centre(SHAPE)
    tf = anchor_at(affine([[1.0, 0.0, 8.0], [0.0, 1.0, -5.0]]), c)
    pair = make_pair(
        np.random.default_rng(sc["seed"]), tf, scene=reg.scene, out_shape=SHAPE,
        sun_source=(315.0, 45.0),
        sun_reference=(315.0 + sc["delta_azimuth"], 45.0),
        base_field=field, field_margin=2.0,
    )
    return pair


def _build_third_view(sc: dict, pair) -> tuple[Any, str | None]:
    """A third overlapping view of the same terrain, for loop closure.

    Rendered from the same height field under the source illumination and a
    different geometry, then registered independently.

    Returns ``(image, error)``. On success ``error`` is ``None``. On failure
    the image is ``None`` and ``error`` is a short description.

    **Why the two are distinguished.** The verdict engine treats a missing
    ``loop_error_px`` as *"the strongest available check was not run"*, and its
    printed reason says a third overlapping image is needed. That reason is
    true when no third view exists and **false** when one existed and the
    computation raised -- and this function used to collapse both into
    ``None``, so a crash was displayed to the reader as a statement about the
    data. Reporting a wrong reason is worse than reporting a failure, so the
    caller now surfaces the error instead of absorbing it into the sentinel.
    """
    try:
        from siim.geometry import warp
        reg = TERRAIN_REGIMES[sc["regime"]]
        field = height_field(
            (SHAPE[0] * 2, SHAPE[1] * 2), np.random.default_rng(sc["seed"]),
            scene=reg.scene, target_slope_median_deg=reg.target_slope_median_deg,
            octaves=reg.octaves, persistence=reg.persistence,
            crater_density=reg.crater_density, pixel_scale=1.0,
        )
        from siim.data import render
        c = image_centre(SHAPE)
        t_ac = anchor_at(affine([[1.0, 0.0, -6.0], [0.0, 1.0, 7.0]]), c)
        h, w = SHAPE
        fh, fw = field.shape
        oy, ox = (fh - h) // 2, (fw - w) // 2
        to_frame = t_ac @ translation(-float(ox), -float(oy))
        warped, _ = warp(field, to_frame, out_shape=SHAPE, cval=np.nan)
        return render(warped, sun_azimuth_deg=315.0, sun_elevation_deg=45.0,
                      pixel_scale=1.0), None
    except LOOP_CLOSURE_ERRORS as exc:
        return None, f"{type(exc).__name__}: {exc}"


@app.get("/api/scenarios")
def scenarios() -> dict:
    real = real_data_status()
    return {
        "scenarios": [
            {"id": k, "title": v["title"], "subtitle": v.get("subtitle"),
             "blurb": v["blurb"], "headline": v.get("headline"),
             "regime": v["regime"], "delta_azimuth": v["delta_azimuth"],
             "adversarial": v["adversarial"], "role": v.get("role"),
             "data_source": ("real_lro_nac" if v.get("real") else "synthetic")}
            for k, v in SCENARIOS.items()
        ],
        "data_status": {
            "synthetic": "available — generated live in each request",
            "real_lro_nac": (
                ("AVAILABLE — recorded REAL-DATA-04 artefacts on disk; no "
                 "network access needed")
                if real["available"] else
                ("UNAVAILABLE — missing " + ", ".join(real["missing"]))),
            "chandrayaan2_ohrc_tmc2_iirs": (
                ("AVAILABLE for TMC-2 — read from the REAL-DATA-09 artefacts. "
                 "OHRC was delivered over the South Pole, where this project "
                 "has no NAC coverage, and no IIRS product was delivered, so "
                 "no OHRC, IIRS or multi-modal claim is supported.")
                if chandrayaan2_status()["available"] else
                ("NOT AVAILABLE — missing "
                 + ", ".join(chandrayaan2_status()["missing"]))),
            "component_ablation": (
                ("AVAILABLE — read from the EXP-006 artefact. The "
                 "architecture's own justification, measured on 42 real pairs "
                 "rather than carried on a citation.")
                if exp006_status()["available"] else
                ("UNAVAILABLE — missing "
                 + ", ".join(exp006_status()["missing"]))),
            "gauge_detection": (
                ("AVAILABLE — read from the EXP-013 artefact and EXP-012's "
                 "gauge probe. This panel reports a measured limitation of "
                 "the shipped verdict, not a capability.")
                if exp013_status()["available"] else
                ("UNAVAILABLE — missing "
                 + ", ".join(exp013_status()["missing"]))),
            "engines_panel": (
                "AVAILABLE — read from the EXP-007 and REAL-DATA-07 artefacts"
                if engines_status()["available"] else
                "UNAVAILABLE — missing " + ", ".join(engines_status()["missing"])),
            "live_register": (
                "AVAILABLE — POST /api/register with two images; computed in the "
                "request, labelled live, never a recorded number"),
        },
        "real_data_files": real,
        "excluded_from_verdict": EXCLUDED_FROM_VERDICT,
    }


@app.get("/api/evidence/illumination")
def evidence_illumination() -> dict:
    """The cross-edge causal panel: every measured real edge, from artefacts."""
    try:
        return illumination_evidence()
    except DemoDataMissing as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/evidence/engines")
def evidence_engines() -> dict:
    """Two engines on the edges RootSIFT fails and on 42 real pairs, read from
    the EXP-007 and REAL-DATA-07 artefacts. Never recomputed."""
    try:
        return engines_evidence()
    except DemoDataMissing as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/evidence/verdict-calibration")
def evidence_verdict_calibration() -> dict:
    """EXP-012: is VERIFIED reachable on real lunar data, and what does it not
    guarantee? Read from the recorded artefact; never recomputed."""
    try:
        return exp012_evidence()
    except DemoDataMissing as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/evidence/component-ablation")
def evidence_component_ablation() -> dict:
    """EXP-006: does one protocol step move more outcomes than swapping the matcher?

    The architecture's own justification, measured rather than cited. Read from
    the recorded artefact; never recomputed."""
    try:
        return exp006_evidence()
    except DemoDataMissing as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/evidence/gauge-detection")
def evidence_gauge_detection() -> dict:
    """EXP-013: the one error the verdict cannot see, and the check that can.

    This panel exists to show the project's own worst measured finding beside
    its best one. Read from the recorded artefacts; never recomputed."""
    try:
        return exp013_evidence()
    except DemoDataMissing as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/evidence/controlled-reference")
def evidence_controlled_reference() -> dict:
    """EXP-019: what the ground positions are worth when another mission says
    where the ground is.

    The panel that turns "corroborated at ~100 px" into a measured 137.6 m and
    produces the project's first accuracy-class number. Read from the recorded
    artefacts; never recomputed."""
    try:
        return exp019_evidence()
    except DemoDataMissing as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/evidence/scale")
def evidence_scale() -> dict:
    """EXP-016: the scale ladder to 320:1 on real lunar texture.

    The problem statement names "2:1 to 320:1" in so many words, and this is
    the axis the project left untested longest. Read from the recorded
    artefact; never recomputed."""
    try:
        return exp016_evidence()
    except DemoDataMissing as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/evidence/viewpoint")
def evidence_viewpoint() -> dict:
    """EXP-017: where a 2-D model stops being valid over real relief.

    The problem statement's second named variation, on which this project had
    no evidence of any kind until this stage. Read from the recorded artefact;
    never recomputed."""
    try:
        return exp017_evidence()
    except DemoDataMissing as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/evidence/multimodality")
def evidence_multimodality() -> dict:
    """EXP-020: nine reflectance bands and a thermal map against panchromatic.

    The problem statement is titled for multi-modal registration and no IIRS
    product was ever delivered, so this panel says what was measured with the
    closest public instrument of the same kind -- and says, first, that it is
    not IIRS. Read from the recorded artefacts; never recomputed."""
    try:
        return exp020_evidence()
    except DemoDataMissing as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/evidence/chandrayaan2")
def evidence_chandrayaan2() -> dict:
    """REAL-DATA-09: Chandrayaan-2 TMC-2 against LRO NAC, from its artefacts.

    The problem statement is titled for Chandrayaan-2, so this is the panel a
    judge looks for. Every figure is read from a recorded file the page also
    links; none is recomputed here."""
    try:
        return chandrayaan2_evidence()
    except DemoDataMissing as exc:
        raise HTTPException(503, str(exc)) from exc


# ---------------------------------------------------------------------------
# live registration of a judge-supplied pair
# ---------------------------------------------------------------------------

#: Long side after down-sampling. Bounds the live run to seconds on a laptop;
#: the CLI (`siim register`) has no such cap and is the tool for full tiles.
LIVE_MAX_SIDE = 1024
LIVE_ENGINES = ("B1", "B4L", "B4X", "both")


class RegisterRequest(BaseModel):
    source_png: str      # base64 of any Pillow-readable image
    reference_png: str
    engine: str = "B1"   # B1, B4L, B4X, or "both" (B1 + B4L with agreement)
    seed: int = 0


class TripletRequest(BaseModel):
    """Three overlapping images of one piece of ground.

    The pair endpoint cannot reach VERIFIED: loop closure is the only check
    this project measured to catch a coherent wrong answer, and it needs a
    cycle. This request is what the pair verdict's own reason text asks for.
    """

    a_png: str
    b_png: str
    c_png: str
    engine: str = "B1"
    seed: int = 0


def _decode_upload(b64: str, what: str) -> tuple[np.ndarray, int]:
    from PIL import Image

    from siim.cli import preprocess
    try:
        raw = base64.b64decode(b64, validate=True)
        with Image.open(io.BytesIO(raw)) as im:
            if im.mode not in ("F", "I", "I;16", "L"):
                im = im.convert("L")
            a = np.asarray(im, dtype=np.float64)
    except Exception as exc:  # noqa: BLE001 -- a bad upload is a 400, not a crash
        raise HTTPException(400, f"{what}: not a readable image ({type(exc).__name__})") from exc
    if a.ndim == 3:
        a = a.mean(axis=2)
    if a.ndim != 2 or min(a.shape) < 64:
        raise HTTPException(400, f"{what}: need a 2-D image at least 64 px on each side")
    k = int(np.ceil(max(a.shape) / LIVE_MAX_SIDE))
    return preprocess(a, k), k


@app.post("/api/register")
def register_live(req: RegisterRequest) -> dict:
    """Run the deliverable pipeline on a pair the viewer supplies.

    ``computation`` is ``"live"`` and ``data_source`` is ``"user_supplied"``:
    nothing here is a recorded number, and nothing here is presented as one.
    The verdict engine, the rule and the pipeline order are the ones the
    stages measured; only the images are new.
    """
    from siim.pipeline import register_pair, register_pair_two_engines
    engine = req.engine if req.engine in LIVE_ENGINES else req.engine.upper()
    if engine not in LIVE_ENGINES:
        raise HTTPException(400, f"engine must be one of {LIVE_ENGINES}")
    src, k_s = _decode_upload(req.source_png, "source")
    ref, k_r = _decode_upload(req.reference_png, "reference")
    t0 = time.perf_counter()
    agreement = None
    secondary = None
    try:
        if engine == "both":
            res, secondary, agreement = register_pair_two_engines(
                src, ref, engines=("B1", "B4L"), seed=req.seed)
        else:
            res = register_pair(src, ref, engine=engine, seed=req.seed)
    except ImportError as exc:
        raise HTTPException(503, f"{engine} needs the `learned` extra: {exc}") from exc
    wall = time.perf_counter() - t0
    inl = res.inlier_mask
    reg_png = None
    if res.transform is not None and res.verdict.status != "REJECTED":
        from siim.geometry import warp
        reg, valid = warp(src, res.transform, out_shape=ref.shape, order=1, cval=np.nan)
        reg_png = _png_b64(np.where(valid, reg, np.nan))
    return {
        "computation": "live",
        "data_source": "user_supplied",
        "engine": engine,
        "preprocessing": {"decimation_source": k_s, "decimation_reference": k_r,
                          "stretch": "per-image 1-99 percentile", "max_side": LIVE_MAX_SIDE},
        "pipeline_order": list(res.summary()["pipeline_order"]),
        "summary": res.summary(),
        "secondary": None if secondary is None else secondary.summary(),
        "engine_agreement": None if agreement is None else agreement.__dict__,
        "verdict": res.verdict.as_dict(),
        "correspondences": {"src": res.src_points.tolist(),
                            "dst": res.dst_points_refined.tolist(),
                            "inlier": np.asarray(inl, bool).tolist(),
                            "refined": np.asarray(res.refined_mask, bool).tolist()},
        "source_png": _png_b64(src), "reference_png": _png_b64(ref),
        "registered_png": reg_png,
        "shape": list(src.shape),
        "timing": {"wall_s": wall, **res.runtime_s},
        "caveats": [
            "Live run on images you supplied; no recorded artefact backs these numbers.",
            "No ground truth: VERIFIED means corroborated by the named evidence, never correct.",
            "Loop closure is not evaluated (one pair), so the verdict cannot exceed INCONCLUSIVE "
            "unless a second engine agrees -- and agreement is evidence, not accuracy.",
        ],
    }


@app.post("/api/register-triplet")
def register_triplet_live(req: TripletRequest) -> dict:
    """Register A->B, B->C and C->A on three images the viewer supplies, close
    the loop, and run the **unmodified** verdict with that residual.

    This is the only path on this page that can return VERIFIED, and it returns
    it for the same reason every recorded triplet did: three independently
    estimated edges whose composition returns to the identity. Nothing here is
    a recorded number, and the composition is checked for independence the way
    EXP-012 checks it -- each edge is estimated from its own image pair, and no
    edge is derived from the other two (E-021's defect).
    """
    from siim.evaluation.gtfree import loop_closure
    from siim.pipeline import register_pair

    engine = req.engine if req.engine in LIVE_ENGINES else req.engine.upper()
    if engine == "both":
        raise HTTPException(400, "the triplet path runs one engine; choose B1, B4L or B4X")
    if engine not in LIVE_ENGINES:
        raise HTTPException(400, f"engine must be one of {LIVE_ENGINES}")
    imgs = {}
    for name, b64 in (("A", req.a_png), ("B", req.b_png), ("C", req.c_png)):
        imgs[name], _ = _decode_upload(b64, f"image {name}")
    t0 = time.perf_counter()
    edges = []
    results = {}
    for src_name, dst_name in (("A", "B"), ("B", "C"), ("C", "A")):
        try:
            res = register_pair(imgs[src_name], imgs[dst_name], engine=engine, seed=req.seed)
        except ImportError as exc:
            raise HTTPException(503, f"{engine} needs the `learned` extra: {exc}") from exc
        results[(src_name, dst_name)] = res
        inl = int(np.asarray(res.inlier_mask, bool).sum())
        edges.append({
            "edge": f"{src_name} -> {dst_name}",
            "n_putative": int(res.src_points.shape[0]),
            "n_inliers": inl,
            "n_refined": int(np.asarray(res.refined_mask, bool).sum()),
            "pass": bool(inl > INLIER_FAILURE_RULE),
            "model": res.summary().get("model"),
            "transform": (np.asarray(res.transform.matrix).tolist()
                          if res.transform is not None else None),
            "verdict": res.verdict.status,
            "estimated_from": "its own image pair",
        })
    wall = time.perf_counter() - t0

    # The cycle is A -> B -> C -> A, evaluated on A's grid. A missing edge makes
    # the loop unevaluable, which is reported rather than filled in.
    chain = [results[("A", "B")].transform, results[("B", "C")].transform,
             results[("C", "A")].transform]
    loop_px = None
    loop_note = ("every edge estimated from its own pair; no edge derived from the other two")
    if all(t is not None for t in chain):
        try:
            loop_px = float(loop_closure(chain, imgs["A"].shape))
        except LOOP_CLOSURE_ERRORS as exc:          # a degenerate cycle is a result
            loop_note = f"loop not evaluable: {type(exc).__name__}"
    else:
        loop_note = "loop not evaluable: at least one edge produced no transform"

    # The verdict is re-run for the A -> B edge WITH the loop residual, which is
    # the only difference from the pair path.
    ab = results[("A", "B")]
    verdict = assess(
        transform=ab.transform, src_points=ab.src_points,
        dst_points=ab.dst_points_refined,
        inlier_mask=np.asarray(ab.inlier_mask, bool), shape=imgs["A"].shape,
        fit_rmse=(float(ab.baseline.ransac.inlier_rmse)
                  if ab.baseline.ransac is not None else None),
        loop_error_px=loop_px,
        annotations={"computation": "live", "data_source": "user_supplied",
                     "triplet": "A -> B -> C -> A"})
    reg_png = None
    if ab.transform is not None and verdict.status != "REJECTED":
        from siim.geometry import warp
        reg, valid = warp(imgs["A"], ab.transform, out_shape=imgs["B"].shape,
                          order=1, cval=np.nan)
        reg_png = _png_b64(np.where(valid, reg, np.nan))
    return {
        "computation": "live",
        "data_source": "user_supplied",
        "engine": engine,
        "edges": edges,
        "loop_error_px": loop_px,
        "loop_note": loop_note,
        "loop_reject_threshold_px": LOOP_ERROR_REJECT_PX,
        "verdict": verdict.as_dict(),
        "verdict_edge": "A -> B",
        "images": {"a_png": _png_b64(imgs["A"]), "b_png": _png_b64(imgs["B"]),
                   "c_png": _png_b64(imgs["C"])},
        "registered_png": reg_png,
        "timing": {"wall_s": wall},
        "caveats": [
            "Live run on images you supplied; no recorded artefact backs these numbers.",
            "VERIFIED here means the three edges compose back to the identity within the "
            "frozen line -- it does NOT mean the alignment is correct. Loop closure is "
            "exactly invariant to a per-image coordinate error (module 03), so a set that "
            "closes can still be wrong in the one way this project measured and published.",
            "No ground truth: nothing on this page verifies against an independent frame "
            "except the recorded controlled-reference stage (module 07).",
        ],
    }


# ---------------------------------------------------------------------------
# provenance: serve the exact files the displayed numbers were read from
# ---------------------------------------------------------------------------

#: Every advertised artefact is JSON. Declaring that is what makes a browser
#: render one in a tab instead of downloading it, which is the difference
#: between a check a judge can watch and a file in a downloads folder.
ARTEFACT_MEDIA_TYPE = "application/json"


@lru_cache(maxsize=1)
def advertised_artefacts() -> frozenset[str]:
    """The repo-relative paths the page itself offers the reader to open.

    An allow-list, not a directory mount. The only files this endpoint will
    ever serve are the ones already named on the page, so no request can reach
    a path the demo does not display -- there is nothing to traverse to. It is
    built from the same ``provenance.artefacts`` list the UI renders and the
    same ``sources`` the illumination panel cites, so the link and the label
    cannot drift apart.

    A scenario whose artefacts are missing contributes nothing rather than
    raising: the endpoint's job is to serve what is advertised, and what is
    advertised is decided by :mod:`siim.demo.evidence`.
    """
    paths: set[str] = set()
    for sid in REAL_SCENARIOS:
        try:
            built = build_real_scenario(sid)
        except DemoDataMissing:
            continue
        paths.update(a["path"] for a in built["provenance"]["artefacts"])
    try:
        paths.update(illumination_evidence()["sources"])
    except DemoDataMissing:
        pass
    try:
        paths.update(engines_evidence()["sources"])
    except DemoDataMissing:
        pass
    try:
        paths.update(chandrayaan2_evidence()["sources"])
    except DemoDataMissing:
        pass
    try:
        paths.update(exp012_evidence()["sources"])
    except DemoDataMissing:
        pass
    try:
        paths.update(exp013_evidence()["sources"])
    except DemoDataMissing:
        pass
    try:
        paths.update(exp006_evidence()["sources"])
    except DemoDataMissing:
        pass
    try:
        paths.update(exp019_evidence()["sources"])
    except DemoDataMissing:
        pass
    try:
        paths.update(exp020_evidence()["sources"])
    except DemoDataMissing:
        pass
    try:
        paths.update(exp017_evidence()["sources"])
    except DemoDataMissing:
        pass
    try:
        paths.update(exp016_evidence()["sources"])
    except DemoDataMissing:
        pass
    return frozenset(paths)


@app.get("/artefact/{path:path}")
def artefact(path: str) -> FileResponse:
    """Serve one advertised provenance artefact, byte for byte.

    The provenance panel invites the reader to open these files and check the
    displayed numbers against them. That invitation used to be printable text
    only: the path was shown and nothing served it, so taking it up meant
    leaving the demo for an editor and a repository checkout. Serving the file
    turns the anti-hardcoding check into a click, which is the whole point of
    printing the path.

    Nothing is transformed on the way out -- no pretty-printing, no filtering,
    no re-serialisation. A file that is reformatted in transit is no longer
    evidence about what is on disk.
    """
    rel = path.replace("\\", "/").strip("/")
    if rel not in advertised_artefacts():
        raise HTTPException(
            404, f"{rel!r} is not one of the artefacts this page advertises. "
                 "Only the files named in a provenance panel are served.")
    full = ROOT / rel
    if not full.is_file():
        # Advertised but absent: the same class of problem as a missing
        # artefact anywhere else in this demo, and reported the same way --
        # named, and never substituted.
        raise HTTPException(
            503, f"{rel} is advertised on the page but is not on disk. The "
                 "demo reads recorded experiment artefacts and will not "
                 "substitute or recompute them.")
    return FileResponse(
        full, media_type=ARTEFACT_MEDIA_TYPE,
        # inline, so the browser shows it rather than downloading it.
        headers={"Content-Disposition": f'inline; filename="{full.name}"'})


@app.post("/api/run")
def run(req: RunRequest) -> dict:
    sc = SCENARIOS.get(req.scenario)
    if sc is None:
        raise HTTPException(404, f"unknown scenario {req.scenario!r}")
    if sc.get("real"):
        # Read, never recomputed. A DemoDataMissing here means an artefact is
        # absent or an overlay disagrees with the numbers beside it; both are
        # reported as 503 with the file named. The demo never falls back to
        # synthetic pixels under a real-data label.
        try:
            return build_real_scenario(req.scenario)
        except DemoDataMissing as exc:
            raise HTTPException(503, str(exc)) from exc

    t0 = time.perf_counter()
    pair = _build_pair(sc)
    t_gen = time.perf_counter() - t0

    t1 = time.perf_counter()
    res = run_rootsift_baseline(pair.source, pair.reference,
                                model=req.model, ransac_threshold=3.0, seed=0)
    t_pipe = time.perf_counter() - t1

    tf_est = res.transform
    src_p, dst_p = res.matches.src_points, res.matches.dst_points
    mask = res.inlier_mask

    # Adversarial construction: displace the *estimate* by one crater spacing,
    # exactly as EXP-001 measured. Declared in the response, never hidden.
    if sc.get("adversarial") and tf_est is not None:
        tf_est = translation(sc["shift_px"], 0.0) @ tf_est

    m = correspondence_metrics(
        src_p, dst_p, mask, gt_transform=pair.transform,
        estimated_transform=tf_est, shape=SHAPE,
        n_keypoints_src=len(res.src_features), n_keypoints_dst=len(res.dst_features),
        reported_inlier_rmse=res.ransac.inlier_rmse, correct_threshold=3.0,
    )

    # Loop closure needs a third view, and -- this is load-bearing -- the three
    # edges must be estimated INDEPENDENTLY from image data. An earlier version
    # of this endpoint derived the closing edge algebraically as
    # ``(t_bc @ tf_est).inverse()``. That makes the loop close by construction:
    # any error in ``tf_est`` appears in the closing edge too and cancels
    # exactly, so the loop reported 0.000 px on a registration that was 64 px
    # wrong. It is E-012's symmetric-error blind spot, reintroduced. Estimating
    # each edge from its own image pair is what makes the check independent.
    #
    # ``loop_err`` and ``loop_error`` are NOT interchangeable. ``loop_err``
    # stays None whenever the check did not produce a number, because the
    # verdict criteria are frozen and ``assess`` must see exactly what it saw
    # before. ``loop_error`` records *why* it is None when the reason was a
    # failure rather than an absence, so the reader is never told that no third
    # image existed when one did.
    loop_err: float | None = None
    loop_error: str | None = None
    third, third_error = _build_third_view(sc, pair)
    if third_error is not None:
        loop_error = f"the third view could not be rendered ({third_error})"
    elif tf_est is not None and third is not None:
        try:
            r_bc = run_rootsift_baseline(pair.reference, third, model=req.model,
                                         ransac_threshold=3.0, seed=0)
            r_ca = run_rootsift_baseline(third, pair.source, model=req.model,
                                         ransac_threshold=3.0, seed=0)
            if r_bc.transform is None or r_ca.transform is None:
                # A genuine absence, not a failure: an edge of the loop found
                # no transform, so there is no loop to close.
                loop_error = None
            else:
                loop_err = loop_closure(
                    [tf_est, r_bc.transform, r_ca.transform], SHAPE)
        except LOOP_CLOSURE_ERRORS as exc:
            loop_err = None
            loop_error = (f"loop closure could not be computed "
                          f"({type(exc).__name__}: {exc})")

    v = assess(
        transform=tf_est, src_points=src_p, dst_points=dst_p, inlier_mask=mask,
        shape=SHAPE, fit_rmse=res.ransac.inlier_rmse, loop_error_px=loop_err,
    )

    inl = np.asarray(mask, dtype=bool) if np.size(mask) else np.zeros(0, bool)
    return {
        "scenario": req.scenario,
        "title": sc["title"],
        "blurb": sc["blurb"],
        # -- honesty flags (§16) -------------------------------------------
        "computation": "live",
        "data_source": "synthetic",
        "real_data_caveats": None,
        "provenance": None,
        "adversarial_construction": bool(sc.get("adversarial")),
        # Non-null ONLY when loop closure was attempted and failed. The verdict
        # will still say the check "was not evaluated", because its criteria are
        # frozen; this field is what stops that from being read as "there was no
        # third image". Null means the check either ran or was genuinely absent.
        "loop_closure_error": loop_error,
        "adversarial_note": (
            f"The estimate was deliberately displaced by {sc.get('shift_px')} px "
            "to reproduce the coherent-wrong failure EXP-001 measured. This is a "
            "controlled synthetic construction, clearly labelled as such."
            if sc.get("adversarial") else None),
        # -- images ---------------------------------------------------------
        "source_png": _png_b64(pair.source),
        "reference_png": _png_b64(pair.reference),
        # -- correspondences ------------------------------------------------
        "correspondences": {
            "src": src_p.tolist(), "dst": dst_p.tolist(),
            "inlier": inl.tolist(),
        },
        "n_keypoints_src": int(len(res.src_features)),
        "n_keypoints_dst": int(len(res.dst_features)),
        # -- verdict ---------------------------------------------------------
        "verdict": v.as_dict(),
        # -- ground truth: available ONLY because this is synthetic ----------
        "ground_truth": {
            "available": True,
            "true_error_median_px": (float(m.transform_error_median)
                                     if np.isfinite(m.transform_error_median) else None),
            "note": ("Ground truth exists here only because the terrain is "
                     "synthetic. On real imagery it does not, which is why the "
                     "verdict above must stand on GT-free evidence alone."),
        },
        "timing": {"generate_s": t_gen, "pipeline_s": t_pipe,
                   "detect_describe_s": res.runtime["detect_describe_s"],
                   "match_s": res.runtime["match_s"],
                   "ransac_s": res.runtime["ransac_s"]},
    }


# ---------------------------------------------------------------------------
# real lunar sample sets for the live card (sample_images/)
# ---------------------------------------------------------------------------

SAMPLES = ROOT / "sample_images"
SAMPLES_LOCAL = SAMPLES / "_local_chandrayaan2"


def _sample_scenarios() -> list[dict]:
    """The scenarios ``scripts/build_sample_images.py`` recorded: the local-only
    Chandrayaan-2 pair first when this machine built one, then the committed sets."""
    out: list[dict] = []
    loc = SAMPLES_LOCAL / "manifest.json"
    if loc.exists():                  # the Chandrayaan-2 pair leads when this machine has one
        rec = json.loads(loc.read_text(encoding="utf-8"))
        out.append(dict(rec, kind="pair", local_only=True))
    man = SAMPLES / "manifest.json"
    if man.exists():
        out.extend(json.loads(man.read_text(encoding="utf-8"))["scenarios"])
    return out


@app.get("/api/samples")
def samples() -> dict:
    """Real lunar sample sets a reader can load into the live card in one click.

    Every expected outcome is the ``live_check`` the build script measured by
    posting these exact files to this server's own endpoints -- a live result,
    labelled as one, not a recorded stage number.
    """
    scen = _sample_scenarios()
    if not scen:
        return {"available": False,
                "reason": "sample_images/ not built -- python scripts/build_sample_images.py"}
    items = []
    for s in scen:
        files = [{"file": f["file"], "url": f"/samples/{s['id']}/{f['file']}",
                  "instrument": f.get("instrument"), "product": f.get("product"),
                  "gsd_m": f.get("gsd_m"), "incidence_deg": f.get("incidence_deg"),
                  "shape": f.get("shape"), "credit": f.get("credit")} for f in s["files"]]
        live = s["live_check"]
        items.append({"id": s["id"], "title": s["title"], "why": s["why"],
                      "kind": "triplet" if live["endpoint"].endswith("triplet") else "pair",
                      "local_only": bool(s.get("local_only")), "files": files,
                      "measured": {k: live.get(k) for k in
                                   ("status", "confidence", "n_inliers", "loop_error_px",
                                    "registered_image_emitted")},
                      "recorded": s.get("recorded")})
    return {"available": True, "computation": "live, measured when the folder was built",
            "folder": "sample_images/", "scenarios": items}


@app.get("/samples/{scenario}/{name}")
def sample_file(scenario: str, name: str) -> FileResponse:
    """One sample image, and only one the manifest names -- an allow-list, not
    a directory mount, for the same reason ``/artefact`` is one."""
    for s in _sample_scenarios():
        if s["id"] == scenario and any(f["file"] == name for f in s["files"]):
            base = SAMPLES_LOCAL if s.get("local_only") else SAMPLES / scenario
            return FileResponse(base / name, media_type="image/png")
    raise HTTPException(404, "not a sample file")


@app.get("/")
def index() -> FileResponse:
    """The demonstrator page, never from the browser's cache.

    The response carries no ``Cache-Control``, so a browser is free to apply
    heuristic freshness and serve a copy it already has without asking. It
    does: re-opening the URL after the page changed showed the previous
    version, with no error and nothing on screen to say so. That is the worst
    shape a demo defect can take -- a page that looks fine and is out of date --
    and the fix that was applied five minutes earlier appears not to have
    worked.

    ``no-store`` costs nothing here: the page is one local file on one local
    request. The tile previews under ``/assets`` are deliberately left
    cacheable -- they are immutable, and re-fetching megabytes of PNG on every
    case switch is a visible stutter on stage.
    """
    return FileResponse(STATIC / "index.html",
                        headers={"Cache-Control": "no-store"})


if STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
if ASSETS.is_dir():
    # Tile previews for the real-data scenarios. Served from disk rather than
    # inlined as base64 so the page stays small and the browser caches them.
    app.mount("/assets", StaticFiles(directory=ASSETS), name="assets")
