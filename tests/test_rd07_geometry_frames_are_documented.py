"""E-040: a REAL-DATA-07 row's two transforms must name their own frames.

The row stores ``transform_matrix`` (tile frame), ``transform_matrix_original_pixels``
(original-pixel frame) and ``geometry.predicted_transform_matrix``. Nothing in
the artefact says which frame the prediction is in, and the two candidates have
the same linear part, so the wrong pairing looks right on most rows and is
wrong by 20-30x on the few where the two tile windows sit differently on their
parent images.

This test re-derives each row's own recorded ``disagreement_px.median`` from
the matrices stored beside it. It is the standing form of the lesson: a stored
derived quantity must be re-derivable from the stored inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from siim.geometry import Transform, endpoint_error

ROOT = Path(__file__).resolve().parents[1]
RD07 = ROOT / "experiments" / "REAL-DATA-07"
ROWS = ("rows_rd03_nue.json", "rows_rd04_nue.json")

#: The tile shape every REAL-DATA-07 frame was matched at (4096 x 2048 at
#: decimation 2). Taken from the stage manifests, not guessed.
SHAPE = (2048, 1024)
#: The recorded medians are computed at step 16; step 32 is the same field
#: sampled more coarsely, so a few tenths of a percent is expected.
TOLERANCE_REL = 0.05


def _rows():
    out = []
    for name in ROWS:
        path = RD07 / name
        if not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        for r in doc["rows"]:
            if r.get("excluded") or "reproduces_recorded" in r:
                continue
            g = r.get("geometry") or {}
            if not g.get("predicted_transform_matrix"):
                continue
            if not r.get("transform_matrix_original_pixels"):
                continue
            if not (g.get("disagreement_px") or {}).get("median"):
                continue
            out.append((name, r))
    return out


ALL_ROWS = _rows()


def test_there_are_rows_to_check():
    assert ALL_ROWS, "no REAL-DATA-07 rows with a stored prediction were found"


@pytest.mark.parametrize("name,row", ALL_ROWS,
                         ids=[f"{n}:{r['engine']}:{r['edge'][-26:]}"
                              for n, r in ALL_ROWS])
def test_the_recorded_disagreement_is_reproducible_from_the_stored_matrices(name, row):
    """The documented pairing must reproduce the row's own number."""
    predicted = Transform(
        np.asarray(row["geometry"]["predicted_transform_matrix"], float), "affine")
    estimate = Transform(
        np.asarray(row["transform_matrix_original_pixels"], float), "affine")
    got = endpoint_error(estimate, predicted, SHAPE, step=32).median
    recorded = float(row["geometry"]["disagreement_px"]["median"])
    assert got == pytest.approx(recorded, rel=TOLERANCE_REL), (
        f"{row['edge']}: recorded disagreement {recorded:.2f} px could not be "
        f"re-derived ({got:.2f} px) from transform_matrix_original_pixels and "
        f"predicted_transform_matrix. Either the stored frames changed or the "
        f"pairing E-040 documents is no longer the right one.")


def test_the_naive_pairing_is_wrong_on_at_least_one_row():
    """The defect E-040 records is real, and stays visible.

    If this ever passes trivially -- i.e. the tile-frame pairing reproduces
    every row too -- then the two frames have converged and E-040's hazard is
    gone. That would be good news, and it should be noticed rather than
    silently assumed.
    """
    offenders = []
    for _, row in ALL_ROWS:
        predicted = Transform(
            np.asarray(row["geometry"]["predicted_transform_matrix"], float), "affine")
        tile = Transform(np.asarray(row["transform_matrix"], float), "affine")
        got = endpoint_error(tile, predicted, SHAPE, step=32).median
        recorded = float(row["geometry"]["disagreement_px"]["median"])
        if got > 5.0 * recorded:
            offenders.append((row["edge"], recorded, got))
    assert offenders, (
        "the tile-frame pairing now reproduces every row: E-040's hazard may "
        "have been removed, which should be recorded rather than assumed")
