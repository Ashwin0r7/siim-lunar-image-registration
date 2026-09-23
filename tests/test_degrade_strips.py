"""The strip-wise degradation is the whole-image degradation, bit for bit.

EXP-023 degrades a ~15 000 x 7 700 OHRC window that the whole-image float64
path cannot hold in memory. The strip version is only admissible if it
changes nothing, so this checks exact equality, including NaNs, halo edges and
a height that is not a multiple of the strip.
"""

import numpy as np
import pytest

from siim.preprocessing.degrade import degrade_to_gsd, degrade_to_gsd_strips


@pytest.mark.parametrize("k,fwhm,strip", [(8, 1.0, 5), (4, 1.0, 3), (3, 0.0, 4), (8, 2.0, 2), (1, 1.0, 7)])
def test_strips_equal_whole_image(k, fwhm, strip):
    rng = np.random.default_rng(k * 10 + strip)
    a = rng.random((k * 37 + 5, k * 11 + 3)).astype(np.float32)
    a[5:9, 7:12] = np.nan
    whole = degrade_to_gsd(a, k, psf_fwhm_coarse_px=fwhm)
    strips = degrade_to_gsd_strips(a, k, psf_fwhm_coarse_px=fwhm, strip_coarse_rows=strip)
    assert strips.shape == whole.shape
    np.testing.assert_array_equal(strips, whole)


def test_uint8_memmap_like_input():
    rng = np.random.default_rng(0)
    a = rng.integers(0, 255, size=(8 * 20, 8 * 9), dtype=np.uint8)
    np.testing.assert_array_equal(degrade_to_gsd_strips(a, 8, strip_coarse_rows=3), degrade_to_gsd(a, 8))
