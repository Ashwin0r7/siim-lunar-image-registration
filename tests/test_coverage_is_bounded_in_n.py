"""E-044: the coverage metric must be bounded in N.

EXP-016's long-window cell at r = 2 produced ~42 000 inliers and the verify
stage raised MemoryError: the median nearest-neighbour distance was computed
from an exact N x N x 2 difference tensor (26 GB at that N). Every recorded
real registration had <= 8 239 inliers and never reached it. A verification
path that only the first large success can break is a defect in the
deliverable; this test exercises it at the largest N a real pair produces.
"""

from __future__ import annotations

import time
import tracemalloc

import numpy as np

from siim.evaluation.coverage import coverage_metrics


def test_coverage_completes_on_fifty_thousand_points_within_a_stated_bound():
    rng = np.random.default_rng(20260922)
    n = 50_000
    pts = np.column_stack([rng.uniform(0, 2048, n), rng.uniform(0, 4096, n)])
    tracemalloc.start()
    t0 = time.perf_counter()
    m = coverage_metrics(pts, (4096, 2048))
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert m.n_points == n
    assert np.isfinite(m.median_nn_distance) and m.median_nn_distance > 0
    # The N x N tensor was 2 * 8 * N^2 bytes = 40 GB here; the bound below is
    # two orders of magnitude under that and above the image-sized buffers
    # the distance transform legitimately needs (4096 * 2048 * 8 B = 67 MB).
    assert peak < 600 * 1024 * 1024, f"peak {peak / 2**20:.0f} MiB"
    assert elapsed < 30.0, f"{elapsed:.1f} s"


def test_nearest_neighbour_distance_matches_the_exact_answer_on_a_small_set():
    rng = np.random.default_rng(1)
    pts = rng.uniform(0, 200, (300, 2))
    d2 = ((pts[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2)
    np.fill_diagonal(d2, np.inf)
    exact = float(np.median(np.sqrt(d2.min(axis=1))))
    got = coverage_metrics(pts, (200, 200)).median_nn_distance
    assert abs(got - exact) < 1e-9
