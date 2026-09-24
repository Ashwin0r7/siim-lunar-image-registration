"""The manual check-point picker's record format, not its GUI.

The picker exists so a future pre-registered stage can evaluate accuracy
against points a human chose with no matcher in the loop. What these tests
guard is the part that stage will rely on:

* the CSV round-trips exactly (a residual computed later opens the same
  numbers the human produced);
* provenance ties the points to the pixels (both images' SHA-256 recorded);
* the purpose statement — never feed these to a matcher or a fit — is in
  the file itself, not just in a docstring;
* an existing file is never overwritten (integrity rule 4).

The interactive `pick()` is not driven here: no display exists in CI, and a
synthetic click stream would test matplotlib, not our record.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location("_picker", ROOT / "scripts" / "pick_checkpoints.py")
_picker = importlib.util.module_from_spec(_spec)
sys.modules["_picker"] = _picker
_spec.loader.exec_module(_picker)


@pytest.fixture
def images(tmp_path):
    rng = np.random.default_rng(3)
    a, b = tmp_path / "a.npy", tmp_path / "b.npy"
    np.save(a, rng.random((32, 48)))
    np.save(b, rng.random((32, 48)))
    return a, b


PAIRS = [(1.25, 2.5, 3.75, 4.0), (10.0, 20.0, 30.5, 40.125)]


def test_round_trip_is_exact_to_the_written_precision(tmp_path, images):
    src, ref = images
    out = tmp_path / "pts.csv"
    _picker.write_checkpoints(out, PAIRS, src, ref, decimate=2, picker="tester")
    prov, p, q = _picker.read_checkpoints(out)
    np.testing.assert_allclose(p, [[1.25, 2.5], [10.0, 20.0]], atol=5e-4)
    np.testing.assert_allclose(q, [[3.75, 4.0], [30.5, 40.125]], atol=5e-4)
    assert prov["picker"] == "tester"
    assert prov["decimation"].startswith("2")


def test_provenance_ties_the_points_to_the_pixels(tmp_path, images):
    src, ref = images
    out = tmp_path / "pts.csv"
    _picker.write_checkpoints(out, PAIRS, src, ref, decimate=1, picker="tester")
    prov, _, _ = _picker.read_checkpoints(out)
    assert prov["source_sha256"] == _picker._sha256(src)
    assert prov["reference_sha256"] == _picker._sha256(ref)
    # the discipline statement travels IN the record
    text = out.read_text(encoding="utf-8")
    assert "never be fed to a matcher" in text
    assert "pre-registered stage" in text


def test_an_existing_file_is_never_overwritten(tmp_path, images):
    src, ref = images
    out = tmp_path / "pts.csv"
    _picker.write_checkpoints(out, PAIRS, src, ref, decimate=1, picker="tester")
    before = out.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        _picker.write_checkpoints(out, [(0, 0, 0, 0)], src, ref, decimate=1, picker="x")
    assert out.read_text(encoding="utf-8") == before
    # and the CLI refuses with exit code 2, like the runners do
    rc = _picker.main([str(src), str(ref), "--out", str(out), "--picker", "x"])
    assert rc == 2


def test_a_file_that_is_not_a_picker_csv_is_refused(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(ValueError):
        _picker.read_checkpoints(bad)
