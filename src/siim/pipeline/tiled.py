"""Full-frame registration by tiles: the driver the gap analysis called
"designed, not built" (PROJECT_GAP_ANALYSIS §3, the full-frame risk row).

A full NAC frame is ~264 megapixels; matching it whole extrapolates to about
100 hours per pair on the recorded laptop. Every recorded stage therefore ran
on tiles. This module makes the tile protocol a driver:

1. **coarse** -- both images are block-mean decimated until the longer side is
   at most ``coarse_max`` and registered once with the ordinary pipeline
   (``register_pair``). The pre-registered failure rule applies unchanged: if
   the coarse pass is REJECTED, the run is REJECTED and no tile is matched.
   The coarse transform is lifted back to full resolution by conjugation with
   the decimation's pixel-centre scaling.
2. **tiles** -- the source is cut into ``tile``-sized windows. For each, the
   lifted coarse transform predicts where that window lands on the reference;
   the predicted window, expanded by ``margin``, is cut from the reference and
   the pair runs through the identical four-stage pipeline. Each tile keeps
   its own verdict; a tile the rule rejects contributes nothing.
3. **pool and re-fit** -- the refined correspondences of every passing tile
   are mapped to full-frame coordinates and pooled, the pooled set goes
   through the same LO-RANSAC (so one tile locked onto a wrong local solution
   is outvoted, not averaged in), and the final model is chosen and
   re-estimated exactly as the pair pipeline does (rule B).
4. **verdict** -- ``assess`` runs once on the pooled evidence over the FULL
   source frame, so the coverage terms finally measure spread across the
   whole image rather than one tile.

What this driver is not. It changes no threshold and adds no new signal:
tiles use the same ``INLIER_CUTOFF``, the same RANSAC, the same refinement
and the same verdict as every recorded stage. It has not been run on a real
full NAC frame in any recorded stage, so no envelope measured on tiles is
claimed to transfer to full frames until a stage does; the per-tile verdicts
and the pooled verdict are the same corroboration, not accuracy.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..demo.verdict import INLIER_CUTOFF, Verdict, assess
from ..geometry import Transform
from ..geometry.transforms import affine
from ..verification import ransac
from .register import PIPELINE_ORDER, RegistrationResult, register_pair
from .select import MIN_POINTS, ModelSelection, reestimate, select_model

__all__ = ["TileOutcome", "TiledResult", "register_large", "decimation_transform"]

#: Default tile side, in pixels: the recorded stages' tile scale.
TILE_DEFAULT = 1024
#: Longest side of the coarse pass, in pixels.
COARSE_MAX_DEFAULT = 2048
#: Reference window expansion, as a fraction of the tile side on every edge,
#: absorbing coarse-transform error at full resolution.
MARGIN_DEFAULT = 0.25
#: A tile with less than this fraction of finite pixels is not matched.
MIN_FINITE_FRACTION = 0.30
#: A predicted reference window smaller than this on either side is skipped.
MIN_WINDOW_PX = 64


def _block_decimate(a: np.ndarray, k: int) -> np.ndarray:
    """NaN-aware block-mean decimation by ``k`` (the recorded preprocessing's
    decimation step, without its stretch: inputs here are already stretched)."""
    if k <= 1:
        return a
    a = a[: a.shape[0] // k * k, : a.shape[1] // k * k]
    import warnings
    with warnings.catch_warnings():
        # an all-NaN block is legal (no-data margin) and must stay NaN quietly
        warnings.filterwarnings("ignore", "Mean of empty slice", RuntimeWarning)
        return np.nanmean(a.reshape(a.shape[0] // k, k, a.shape[1] // k, k), axis=(1, 3))


def decimation_transform(k: int) -> Transform:
    """coarse pixel -> full pixel for block-mean decimation by ``k``.

    Pixel centres (contract C1): coarse pixel ``j`` covers full pixels
    ``jk .. jk+k-1``, whose centre is ``jk + (k-1)/2``.
    """
    o = (k - 1) / 2.0
    return affine([[float(k), 0.0, o], [0.0, float(k), o]])


def _lift(t_coarse: Transform, k: int) -> Transform:
    """A coarse-frame transform, conjugated to the full-resolution frame."""
    s = decimation_transform(k)
    return s @ t_coarse @ s.inverse()


def _tile_starts(extent: int, tile: int) -> list[int]:
    if extent <= tile:
        return [0]
    starts = list(range(0, extent - tile + 1, tile))
    if starts[-1] + tile < extent:
        starts.append(extent - tile)  # clamped last tile; may overlap its neighbour
    return starts


@dataclass(frozen=True)
class TileOutcome:
    """One tile's run: where it was, what the pipeline said, what it gave."""

    row: int
    col: int
    #: (y0, y1, x0, x1) of the source tile, full-frame pixels.
    src_window: tuple[int, int, int, int]
    #: (y0, y1, x0, x1) of the reference window; ``None`` when the predicted
    #: window fell outside the reference (status ``NO_OVERLAP``).
    ref_window: tuple[int, int, int, int] | None
    #: The tile pair's own verdict status, ``NO_OVERLAP``, or ``EMPTY``
    #: (too few finite pixels to match).
    status: str
    n_inliers: int
    n_refined: int
    #: Median ||T_tile(p) - T_global(p)|| over the tile, full-frame reference
    #: pixels; ``None`` when either transform is missing. A per-tile
    #: consistency figure, not an accuracy.
    median_dev_from_global_px: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "row": self.row, "col": self.col,
            "src_window": list(self.src_window),
            "ref_window": None if self.ref_window is None else list(self.ref_window),
            "status": self.status, "n_inliers": self.n_inliers,
            "n_refined": self.n_refined,
            "median_dev_from_global_px": self.median_dev_from_global_px,
        }


@dataclass(frozen=True)
class TiledResult:
    """The full-frame answer, with the evidence trail of every tile."""

    engine: str
    coarse: RegistrationResult
    #: The decimation factor of the coarse pass.
    coarse_k: int
    #: The coarse transform lifted to full resolution; ``None`` when coarse
    #: was rejected.
    coarse_transform_full: Transform | None
    tiles: list[TileOutcome]
    #: Pooled refined correspondences of the passing tiles, full-frame pixels.
    src_points: NDArray[np.float64]
    dst_points: NDArray[np.float64]
    #: LO-RANSAC inlier mask over the pooled correspondences.
    inlier_mask: NDArray[np.bool_]
    selection: ModelSelection | None
    model_selected_by: str
    #: The final full-frame transform, source -> reference.
    transform: Transform | None
    verdict: Verdict
    runtime_s: dict[str, float] = field(default_factory=dict)

    @property
    def n_inliers(self) -> int:
        return int(self.inlier_mask.sum()) if self.inlier_mask.size else 0

    def summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for t in self.tiles:
            counts[t.status] = counts.get(t.status, 0) + 1
        return {
            "engine": self.engine,
            "pipeline_order": list(PIPELINE_ORDER) + ["pool", "reestimate_global", "verify"],
            "status": self.verdict.status, "confidence": self.verdict.confidence,
            "coarse_status": self.coarse.verdict.status, "coarse_k": self.coarse_k,
            "n_tiles": len(self.tiles), "tile_status_counts": counts,
            "n_pooled": int(self.src_points.shape[0]), "n_inliers": self.n_inliers,
            "model_selected_by": self.model_selected_by,
            "model": None if self.transform is None else self.transform.model,
            "transform_matrix": None if self.transform is None
            else np.asarray(self.transform.matrix).tolist(),
            "runtime_s": dict(self.runtime_s),
        }


def _rejected(engine: str, coarse: RegistrationResult, k: int,
              lifted: Transform | None, tiles: list[TileOutcome],
              src_shape: tuple[int, int], reason: str,
              pooled: tuple[np.ndarray, np.ndarray] | None,
              rt: dict[str, float]) -> TiledResult:
    p, q = (np.zeros((0, 2)), np.zeros((0, 2))) if pooled is None else pooled
    verdict = assess(transform=None, src_points=p, dst_points=q,
                     inlier_mask=np.zeros(p.shape[0], bool), shape=src_shape,
                     annotations={"engine": engine, "tiled": True, "tiled_reason": reason})
    return TiledResult(engine=engine, coarse=coarse, coarse_k=k,
                       coarse_transform_full=lifted, tiles=tiles,
                       src_points=p, dst_points=q,
                       inlier_mask=np.zeros(p.shape[0], bool), selection=None,
                       model_selected_by="none", transform=None, verdict=verdict,
                       runtime_s=rt)


def register_large(source: ArrayLike, reference: ArrayLike, *, engine: str = "B1",
                   model: str = "affine", tile: int = TILE_DEFAULT,
                   coarse_max: int = COARSE_MAX_DEFAULT, margin: float = MARGIN_DEFAULT,
                   ransac_threshold: float = 3.0, seed: int = 0,
                   refine: bool = True, **engine_kwargs: Any) -> TiledResult:
    """Register a large source to a large reference through the tile protocol.

    Inputs are 2-D arrays, already preprocessed the way the pair pipeline
    expects (the CLI does its recorded decimate-then-stretch first); NaN is
    invalid. The verdict's coverage terms are measured over the full source
    frame -- the whole point of the driver.
    """
    src = np.asarray(source, dtype=np.float64)
    ref = np.asarray(reference, dtype=np.float64)
    if src.ndim != 2 or ref.ndim != 2:
        raise ValueError("source and reference must be 2-D images")
    rt: dict[str, float] = {}

    # 1. coarse
    k = max(1, int(np.ceil(max(src.shape + ref.shape) / coarse_max)))
    t0 = time.perf_counter()
    coarse = register_pair(_block_decimate(src, k), _block_decimate(ref, k),
                           engine=engine, model=model, ransac_threshold=ransac_threshold,
                           seed=seed, refine=refine, **engine_kwargs)
    rt["coarse"] = time.perf_counter() - t0
    if coarse.verdict.status == "REJECTED" or coarse.transform is None:
        return _rejected(engine, coarse, k, None, [], src.shape,
                         "coarse pass rejected; no tile was matched", None, rt)
    lifted = _lift(coarse.transform, k)

    # 2. tiles
    t0 = time.perf_counter()
    tiles: list[TileOutcome] = []
    tile_transforms: dict[tuple[int, int], Transform] = {}
    pooled_p: list[np.ndarray] = []
    pooled_q: list[np.ndarray] = []
    pad = int(round(margin * tile))
    for row, y0 in enumerate(_tile_starts(src.shape[0], tile)):
        for col, x0 in enumerate(_tile_starts(src.shape[1], tile)):
            y1, x1 = min(y0 + tile, src.shape[0]), min(x0 + tile, src.shape[1])
            sw = (y0, y1, x0, x1)
            st = src[y0:y1, x0:x1]
            if np.isfinite(st).mean() < MIN_FINITE_FRACTION:
                tiles.append(TileOutcome(row, col, sw, None, "EMPTY", 0, 0))
                continue
            corners = np.array([[x0, y0], [x1 - 1, y0], [x0, y1 - 1], [x1 - 1, y1 - 1]], float)
            proj = lifted.apply(corners)
            wx0 = int(np.floor(proj[:, 0].min())) - pad
            wx1 = int(np.ceil(proj[:, 0].max())) + pad + 1
            wy0 = int(np.floor(proj[:, 1].min())) - pad
            wy1 = int(np.ceil(proj[:, 1].max())) + pad + 1
            wx0, wy0 = max(wx0, 0), max(wy0, 0)
            wx1, wy1 = min(wx1, ref.shape[1]), min(wy1, ref.shape[0])
            if wx1 - wx0 < MIN_WINDOW_PX or wy1 - wy0 < MIN_WINDOW_PX:
                tiles.append(TileOutcome(row, col, sw, None, "NO_OVERLAP", 0, 0))
                continue
            rw = (wy0, wy1, wx0, wx1)
            res = register_pair(st, ref[wy0:wy1, wx0:wx1], engine=engine, model=model,
                                ransac_threshold=ransac_threshold, seed=seed,
                                refine=refine, **engine_kwargs)
            n_ref = int(res.refined_mask.sum())
            tiles.append(TileOutcome(row, col, sw, rw, res.verdict.status,
                                     res.n_inliers, n_ref))
            if res.n_inliers > INLIER_CUTOFF and res.transform is not None:
                m = res.refined_mask if n_ref else res.inlier_mask
                pooled_p.append(res.src_points[m] + [x0, y0])
                pooled_q.append(res.dst_points_refined[m] + [wx0, wy0])
                # tile-local -> full-frame conjugation of the tile's transform
                to_src = affine([[1.0, 0.0, -x0], [0.0, 1.0, -y0]])
                to_ref = affine([[1.0, 0.0, wx0], [0.0, 1.0, wy0]])
                tile_transforms[(row, col)] = to_ref @ res.transform @ to_src
    rt["tiles"] = time.perf_counter() - t0

    if not pooled_p:
        return _rejected(engine, coarse, k, lifted, tiles, src.shape,
                         "no tile passed the pre-registered rule", None, rt)
    p = np.concatenate(pooled_p)
    q = np.concatenate(pooled_q)

    # 3. pooled robust re-fit, then rule-B model selection on the survivors
    t0 = time.perf_counter()
    rr = ransac(p, q, model=model, threshold=ransac_threshold, seed=seed)
    mask = (np.asarray(rr.inlier_mask, bool).reshape(-1)
            if rr.transform is not None and np.size(rr.inlier_mask) == p.shape[0]
            else np.zeros(p.shape[0], bool))
    n_in = int(mask.sum())
    selection: ModelSelection | None = None
    final: Transform | None = rr.transform
    selected_by = "none" if final is None else "pooled_ransac"
    if final is not None and n_in > INLIER_CUTOFF and n_in >= MIN_POINTS:
        selection = select_model(p[mask], q[mask], seed=seed)
        final = reestimate(p[mask], q[mask], selection.model)
        selected_by = "held_out_on_pooled_tile_points"
    rt["reestimate_global"] = time.perf_counter() - t0

    # per-tile deviation from the global model, over each tile's own extent
    tiles_out: list[TileOutcome] = []
    for t in tiles:
        dev = None
        tt = tile_transforms.get((t.row, t.col))
        if tt is not None and final is not None:
            y0, y1, x0, x1 = t.src_window
            gy, gx = np.meshgrid(np.linspace(y0, y1 - 1, 8), np.linspace(x0, x1 - 1, 8))
            pts = np.column_stack([gx.ravel(), gy.ravel()])
            dev = float(np.median(np.linalg.norm(tt.apply(pts) - final.apply(pts), axis=1)))
        tiles_out.append(TileOutcome(t.row, t.col, t.src_window, t.ref_window,
                                     t.status, t.n_inliers, t.n_refined, dev))

    # 4. one verdict over the whole frame
    t0 = time.perf_counter()
    verdict = assess(
        transform=final, src_points=p, dst_points=q, inlier_mask=mask, shape=src.shape,
        fit_rmse=float(rr.inlier_rmse) if rr.transform is not None else None,
        annotations={
            "engine": engine, "tiled": True, "tile_px": tile, "coarse_k": k,
            "n_tiles": len(tiles_out),
            "n_tiles_passed": sum(1 for t in tiles_out
                                  if t.n_inliers > INLIER_CUTOFF),
            "model_selected_by": selected_by,
            "heldout_px": None if selection is None else selection.heldout_px,
        })
    rt["verify"] = time.perf_counter() - t0

    return TiledResult(engine=engine, coarse=coarse, coarse_k=k,
                       coarse_transform_full=lifted, tiles=tiles_out,
                       src_points=p, dst_points=q, inlier_mask=mask,
                       selection=selection, model_selected_by=selected_by,
                       transform=final, verdict=verdict, runtime_s=rt)
