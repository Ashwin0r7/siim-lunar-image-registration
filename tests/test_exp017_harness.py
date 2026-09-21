"""EXP-017's harness controls, pinned before the frozen run (Part 1 S0).

S0(iii): on an exactly affine field the dense warp must reproduce
``siim.geometry.warp`` and the dense error ``endpoint_error`` to 1e-9 --
otherwise every number the stage reports is measuring the harness.
S0(ii): the inverted field composed with the forward field is the identity.
S0(v)-shape: the shift null does not fire on an unrelated smooth field.
S0(iv)-shape: L3, orthorectifying with the field that built the oblique,
recovers the identity map to well under the 0.05 px floor.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(scope="module")
def r17():
    spec = importlib.util.spec_from_file_location("_r17_test", ROOT / "scripts" / "run_exp017.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _terrain(shape=(96, 80), sigma=5.0, amp_m=60.0, seed=3):
    rng = np.random.default_rng(seed)
    return ndimage.gaussian_filter(rng.normal(size=shape), sigma) * amp_m


def test_s0_iii_dense_warp_and_error_reproduce_the_library_on_an_affine_field(r17):
    rep = r17.s0_iii_reproduction()
    assert rep["max_image_diff"] < 1e-9, rep
    assert rep["dense_median_diff"] < 1e-9 and rep["dense_max_diff"] < 1e-9, rep
    assert rep["met"]


def test_s0_ii_inversion_composes_to_identity_with_and_without_a_hole(r17):
    h = _terrain()
    for holed in (False, True):
        hh = h.copy()
        if holed:
            hh[30:45, 20:35] = np.nan
        d = r17.parallax_field(hh, 5.0, 25.0)
        q = r17.pixel_grid(h.shape, step=r17.GRID_STEP)
        p = r17.forward_points(d, q)
        ok = np.isfinite(p).all(axis=1)
        qx, qy, d_ok, iters = r17.invert_field(d, p[ok, 0], p[ok, 1])
        err = np.hypot(qx - q[ok, 0], qy - q[ok, 1])[d_ok]
        assert err.size > 50
        assert err.max() < r17.S0_INVERSION_PX, (holed, err.max(), iters)
        assert iters < r17.FIXED_POINT_ITERS


def test_parallax_field_has_the_sign_and_scale_of_section_20(r17):
    h = np.zeros((10, 10)); h[5, 5] = 100.0   # 100 m above the mean (nearly)
    d = r17.parallax_field(h, 5.0, 25.0)
    # 100 m x tan(25 deg) / 5 m = 9.33 px, and the mean removal is 1 % of it
    assert d[5, 5] == pytest.approx(99.0 * np.tan(np.deg2rad(25.0)) / 5.0)
    assert (d[0, 0] < 0) and r17.parallax_field(h, 5.0, 0.0).max() == 0.0


def test_shift_null_false_alarm_rate_is_at_most_5_percent_on_unrelated_smooth_fields(r17):
    """Residual and relief both smooth but independent: the detector's clause 1
    must fire at roughly the nominal 5 %; a pixel permutation fires far more."""
    fires_shift, fires_perm, n = 0, 0, 40
    for k in range(n):
        h2d = _terrain((30, 24), sigma=2.0, seed=100 + k)
        r2d = _terrain((30, 24), sigma=2.0, amp_m=0.3, seed=500 + k)
        sig = r17.signature_test(r2d, h2d, 10.0, 5.0, np.random.default_rng(k), np.random.default_rng(k + 1), n_null=100)
        fires_shift += int(sig["r2_beats_shift_null"])
        fires_perm += int(sig["r2_beats_perm_null"])
    assert fires_shift <= int(np.ceil(0.15 * n)), fires_shift        # 5 % nominal, slack for n = 40
    assert fires_perm > fires_shift                                    # the control that cannot fail


def test_signature_detector_fires_on_the_constructed_parallax(r17):
    h2d = _terrain((30, 24), sigma=2.0)
    h_res = r17.remove_plane(h2d)
    e, gsd = 10.0, 5.0
    r2d = h_res * np.tan(np.deg2rad(e)) / gsd + _terrain((30, 24), sigma=1.0, amp_m=0.02, seed=9)
    sig = r17.signature_test(r2d, h_res, e, gsd, np.random.default_rng(0), np.random.default_rng(1), n_null=100)
    assert sig["fired"] and sig["sign_ok"] and sig["magnitude_ok"], sig


def test_morans_i_calls_white_noise_white_and_smooth_structure_not(r17):
    rng = np.random.default_rng(0)
    white = r17.morans_i(rng.normal(size=(30, 24)), np.random.default_rng(1), n_null=100)
    smooth = r17.morans_i(_terrain((30, 24), sigma=2.0), np.random.default_rng(2), n_null=100)
    assert white["white_by_I"] is True
    assert smooth["white_by_I"] is False


def test_l3_orthorectification_with_the_building_field_recovers_identity(r17):
    h = _terrain()
    d = r17.parallax_field(h, 5.0, 25.0)
    q = r17.pixel_grid(h.shape, step=4)
    p = r17.forward_points(d, q)
    ok = np.isfinite(p).all(axis=1)
    back = r17.orthorectify(d, p[ok])
    err = np.hypot(*(back - q[ok]).T)
    assert np.isfinite(err).all() and np.median(err) < r17.S0_MEDIAN_PX / 10


def test_piecewise_affine_falls_back_to_global_in_empty_cells(r17):
    from siim.geometry import translation
    g = translation(1.0, 2.0)
    rng = np.random.default_rng(0)
    src = 4.0 + rng.uniform(0, 8, size=(20, 2))          # all inside cell (0, 0), not collinear
    dst = src + [1.0, 2.0]
    apply, fallback = r17.piecewise_affine(src, dst, (64, 64), g)
    assert fallback == r17.CELLS ** 2 - 1
    far = np.array([[60.0, 60.0]])
    assert np.allclose(apply(far, far + [1.0, 2.0]), far + [1.0, 2.0])
