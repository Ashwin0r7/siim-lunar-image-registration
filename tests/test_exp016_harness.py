"""EXP-016 harness controls (Part 1 S0), on small synthetic inputs.

What each guards: the degradation operator's psf = 0 member IS the recorded box
average (else S0's reproduction gate is comparing two operators); the C4 offset
mapping between rungs is exact (else rung consistency carries a half-pixel
artefact at every rung); the self-scale control recovers a known shift; the
McNemar / concordance and PSR helpers do what Part 1 says they do.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(scope="module")
def m():
    spec = importlib.util.spec_from_file_location("_exp016", ROOT / "scripts" / "run_exp016.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_exp016"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_psf_zero_is_the_recorded_box_average_bit_for_bit(m):
    rng = np.random.default_rng(16)
    a = rng.normal(size=(96, 80))
    a[3, 5] = np.nan
    for k in (2, 4, 8):
        assert np.array_equal(m.degrade_to_gsd(a, k, psf_fwhm_coarse_px=0.0), m._e7.decimate(a, k),
                              equal_nan=True)


def test_rung_map_c4_offset_is_exact_between_rungs(m):
    from siim.geometry import Transform
    from siim.ingest.footprint import TileWindow
    ws2, wd2 = TileWindow(100, 40, 4096, 2048, 2), TileWindow(700, 10, 4096, 2048, 2)
    ws8, wd8 = TileWindow(100, 40, 4096, 2048, 8), TileWindow(700, 10, 4096, 2048, 8)
    t2 = Transform(np.array([[1.02, 0.01, 30.0], [-0.02, 0.98, -12.0], [0, 0, 1.0]]), "affine")
    t8 = m.rung_map(t2, ws2, wd2, ws8, wd8)
    back = m.rung_map(t8, ws8, wd8, ws2, wd2)
    assert np.abs(back.matrix - t2.matrix).max() < 1e-12
    # a point through the frame by hand
    x, y = 100.0, 37.0
    line, sample = ws8.to_frame(y, x)
    r2, c2 = ws2.from_frame(line, sample)
    q2 = t2.apply(np.array([[c2, r2]]))[0]
    lq, sq = wd2.to_frame(q2[1], q2[0])
    r8, c8 = wd8.from_frame(lq, sq)
    assert np.allclose(t8.apply(np.array([[x, y]]))[0], [c8, r8], atol=1e-10)


def test_self_scale_control_recovers_a_known_shift(m):
    from siim.data.synthetic_terrain import height_field, render
    h = height_field((640, 640), np.random.default_rng(3), scene="highlands")
    img = render(h, 315.0, 45.0, pixel_scale=2.0, noise_std=0.004)

    class Ctx:
        pdsid = "synthetic"
        corners = None
        scaled_pixel_m = 2.0

        def raw(self):
            return img

    w = m.Window(Ctx(), 0, 0, *img.shape)
    rec = m.self_scale_control(w, 2)
    assert rec["status"] == "ok"
    assert rec["n_inliers"] > m.RULE
    assert rec["shift_error_coarse_px"] < m.S0_SELF_SHIFT_PX


def test_concordance_and_mcnemar_counts(m):
    full = [True, True, False, False, True, False]
    crop = [True, False, False, True, True, False]
    c = m.concordance(full, crop)
    assert c["n_agree"] == 4 and abs(c["concordance"] - 4 / 6) < 1e-12
    assert c["full_only_success"] == 1 and c["cropped_only_success"] == 1
    mc = m.mcnemar(5, 0)
    assert mc["n_discordant"] == 5 and abs(mc["p_one_sided_first"] - 0.5 ** 5) < 1e-12
    assert m.mcnemar(0, 0)["p_two_sided"] is None


def test_psr_finds_the_single_peak(m):
    rng = np.random.default_rng(0)
    ncc = rng.normal(0.0, 0.05, size=(40, 60))
    ncc[17, 42] = 0.9
    ratio, (iy, ix), peak = m.psr(ncc)
    assert (iy, ix) == (17, 42) and peak == 0.9
    assert ratio > m.S5_PSR


def test_logistic_recovers_a_pixel_count_effect(m):
    rng = np.random.default_rng(1)
    N = 2 ** rng.integers(6, 20, size=200)
    r = 2 ** rng.integers(1, 9, size=200)
    p = 1 / (1 + np.exp(-(np.log2(N) - 12.0)))
    y = rng.random(200) < p
    out = m.logistic(N, r, y)
    assert out["beta_N"] > 0 and out["p_beta_N"] < 0.05
    assert out["p_beta_r"] > 0.05


def test_runner_refuses_to_overwrite(m, tmp_path, monkeypatch):
    target = tmp_path / "exp016_results.json"
    target.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["run_exp016.py", "--out", str(target), "--quick"])
    with pytest.raises(SystemExit, match="integrity rule 4"):
        m.main()
