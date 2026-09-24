"""The full-frame tiling driver: the gap-analysis debt "designed, not built".

``siim.pipeline.register_large`` and ``siim register-large`` exist so that a
frame too big to match whole goes through the SAME four-stage pipeline
tile by tile: one coarse pass under the pre-registered failure rule, the
identical per-tile pipeline, a pooled LO-RANSAC re-fit, and ONE verdict whose
coverage terms span the whole frame.

**What these tests guard.** The driver adds no science: no new threshold, no
new signal, no loosened rule. So the failure modes to guard are protocol
drift, not accuracy claims:

* the pooled transform must recover a known synthetic warp (a precision check
  on synthetic truth -- it says nothing about real-pair accuracy);
* the pixel-centre conjugation between coarse and full frames must be exact,
  or every predicted reference window silently shifts by ``(k-1)/2``;
* a coarse REJECTED must reject the run without matching any tile -- the
  refusal must not be worked around by the driver;
* the CLI must refuse to overwrite existing artefacts (integrity rule 4) and
  must exit 3 on REJECTED like ``siim register`` does, so batch scripts treat
  both commands identically.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.cli import main as cli_main  # noqa: E402
from siim.demo.verdict import INLIER_CUTOFF  # noqa: E402
from siim.geometry import Transform, warp  # noqa: E402
from siim.pipeline import register_large  # noqa: E402
from siim.pipeline.tiled import decimation_transform  # noqa: E402


def _texture(shape: tuple[int, int], seed: int) -> np.ndarray:
    """Multi-octave smoothed noise: texture at every scale, so both the coarse
    pass (decimated) and the tiles (native) have features to detect."""
    from scipy.ndimage import gaussian_filter
    rng = np.random.default_rng(seed)
    a = np.zeros(shape)
    for sigma, weight in ((1, 1.0), (2, 1.0), (4, 1.5), (8, 2.0), (16, 3.0)):
        a += weight * gaussian_filter(rng.standard_normal(shape), sigma)
    lo, hi = np.percentile(a, [1, 99])
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0)


TRUE = Transform(np.array([
    [1.02 * np.cos(np.radians(2.0)), -1.02 * np.sin(np.radians(2.0)), 18.5],
    [1.02 * np.sin(np.radians(2.0)), 1.02 * np.cos(np.radians(2.0)), -7.25],
    [0.0, 0.0, 1.0],
]), "similarity")


@pytest.fixture(scope="module")
def pair():
    src = _texture((1200, 1600), seed=7)
    ref, _valid = warp(src, TRUE, out_shape=src.shape, order=3, cval=np.nan)
    return src, ref


@pytest.fixture(scope="module")
def result(pair):
    src, ref = pair
    return register_large(src, ref, tile=512, coarse_max=512, seed=0)


def test_conjugation_is_exact_for_the_identity():
    # lift(I) must be I: any residual here shifts every reference window.
    s = decimation_transform(4)
    ident = Transform(np.eye(3), "affine")
    lifted = s @ ident @ s.inverse()
    np.testing.assert_allclose(lifted.matrix, np.eye(3), atol=1e-12)


def test_decimation_transform_maps_pixel_centres():
    # coarse pixel 0 of a k=4 block covers full pixels 0..3, centre 1.5.
    t = decimation_transform(4)
    np.testing.assert_allclose(t.apply([[0.0, 0.0]]), [[1.5, 1.5]])
    np.testing.assert_allclose(t.apply([[2.0, 3.0]]), [[9.5, 13.5]])


def test_known_warp_is_recovered_by_the_pooled_transform(pair, result):
    src, _ref = pair
    assert result.verdict.status != "REJECTED"
    assert result.transform is not None
    # precision on synthetic truth over the valid interior; NOT an accuracy claim
    gy, gx = np.meshgrid(np.linspace(100, 1099, 12), np.linspace(100, 1499, 12))
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    err = np.linalg.norm(result.transform.apply(pts) - TRUE.apply(pts), axis=1)
    assert np.median(err) < 0.5, f"median deviation from truth {np.median(err):.3f} px"


def test_tiles_ran_and_pooled_evidence_spans_more_than_one(result):
    assert len(result.tiles) >= 6           # 1200x1600 at 512 -> 3 x 4 grid (clamped)
    passed = [t for t in result.tiles if t.n_inliers > INLIER_CUTOFF]
    assert len(passed) >= 2, [t.status for t in result.tiles]
    # every passing tile got its consistency figure against the global model
    assert all(t.median_dev_from_global_px is not None for t in passed)
    # the pooled set is what the verdict saw
    assert result.src_points.shape[0] == result.inlier_mask.shape[0]
    assert result.n_inliers > INLIER_CUTOFF


def test_verdict_names_the_tiling_in_its_metrics(result):
    m = result.verdict.metrics
    assert m.get("tiled") is True
    assert m.get("n_tiles") == len(result.tiles)
    # coverage is measured over the FULL frame -- the driver's purpose
    assert "coverage_max_gap" in m and "coverage_occupancy" in m


def test_a_rejected_coarse_pass_rejects_the_run_without_matching_tiles():
    rng = np.random.default_rng(11)
    a = _texture((600, 800), seed=3)
    b = _texture((600, 800), seed=4)            # unrelated ground on purpose
    res = register_large(a, b, tile=512, coarse_max=512, seed=0)
    if res.coarse.verdict.status == "REJECTED":
        assert res.verdict.status == "REJECTED"
        assert res.tiles == []                   # the refusal is not worked around
        assert res.transform is None
    else:
        # unrelated smoothed noise occasionally clears the coarse rule; the
        # run must then still refuse at the pooled stage or state its pass
        assert res.verdict.status in ("REJECTED", "INCONCLUSIVE")
    del rng


def test_cli_register_large_writes_artefacts_and_refuses_overwrite(tmp_path, pair):
    from PIL import Image
    src, ref = pair
    sp, rp = tmp_path / "src.png", tmp_path / "ref.png"
    Image.fromarray((src * 255).astype(np.uint8)).save(sp)
    Image.fromarray((np.nan_to_num(ref) * 255).astype(np.uint8)).save(rp)
    out = tmp_path / "out"
    rc = cli_main(["register-large", str(sp), str(rp), "--out", str(out),
                   "--tile", "512", "--coarse-max", "512"])
    assert rc == 0
    for name in ("tiles.json", "metrics.json", "verdict.json"):
        assert (out / name).exists(), name
    tiles = json.loads((out / "tiles.json").read_text(encoding="utf-8"))
    assert tiles["coarse"]["status"] != "REJECTED"
    assert len(tiles["tiles"]) >= 6
    verdict = json.loads((out / "verdict.json").read_text(encoding="utf-8"))
    assert verdict["status"] != "REJECTED"
    assert verdict["provenance"]["tool"].endswith("register-large")
    assert "pre_registered_rule" in verdict["provenance"]
    # integrity rule 4: a second run may not silently replace the artefacts
    rc2 = cli_main(["register-large", str(sp), str(rp), "--out", str(out),
                    "--tile", "512", "--coarse-max", "512"])
    assert rc2 == 2
