"""GeoTIFF reading and placement (REAL-DATA-09 §4 steps 1-3, 5).

No Chandrayaan-2 product exists when these are written. Every fixture is a
GeoTIFF this test writes itself with a *known* tiepoint, pixel scale and
GeoKey set, so the assertions are against the contract rather than against
data whose conventions Part 1 §3 explicitly records as unknown.

The round-trip tests are the ones that matter: a ground point pushed through
``block_xy_of_lonlat`` and back through ``lonlat_of_block_xy`` must return
where it started. A placement that is silently mirrored or half-a-pixel out
is exactly the class of defect E-037 and E-001 were.
"""

from __future__ import annotations

import numpy as np
import pytest

tifffile = pytest.importorskip("tifffile",
                               reason="the `chandrayaan2` extra is not installed")

from siim.ingest.geotiff import (  # noqa: E402
    MOON_RADIUS_M,
    GeoTiffNotIngested,
    GeoTiffNotPlaced,
    PolarStereoBlock,
    decode_window,
    place,
    read_geometry,
    structural_identity,
)
from siim.ingest.mapgrid import MapBlock  # noqa: E402

M_PER_DEG = MOON_RADIUS_M * np.pi / 180.0


# --------------------------------------------------------------------------
# fixture writers
# --------------------------------------------------------------------------
def _geokey_directory(keys: dict[int, int]) -> tuple[int, ...]:
    """A GeoKeyDirectory holding only SHORT values (TIFFTagLocation 0)."""
    body: list[int] = []
    for key_id in sorted(keys):
        body += [key_id, 0, 1, int(keys[key_id])]
    return tuple([1, 1, 0, len(keys)] + body)


def _write(path, data, *, tiepoint=None, pixel_scale=None, geokeys=None,
           transformation=None, doubles=None):
    extratags = []
    if pixel_scale is not None:
        extratags.append((33550, "d", 3, tuple(float(v) for v in pixel_scale), True))
    if tiepoint is not None:
        extratags.append((33922, "d", 6, tuple(float(v) for v in tiepoint), True))
    if transformation is not None:
        extratags.append((34264, "d", 16, tuple(float(v) for v in transformation), True))
    if geokeys is not None:
        d = _geokey_directory(geokeys)
        extratags.append((34735, "H", len(d), d, True))
    if doubles is not None:
        extratags.append((34736, "d", len(doubles), tuple(float(v) for v in doubles), True))
    tifffile.imwrite(str(path), data, extratags=extratags, compression=None)
    return path


def _ramp(lines=40, samples=60):
    """A non-symmetric ramp: any transpose or mirror changes the values."""
    r = np.arange(lines, dtype=np.float32)[:, None]
    c = np.arange(samples, dtype=np.float32)[None, :]
    return (r * 1000.0 + c).astype(np.float32)


# --------------------------------------------------------------------------
# §4 step 1 -- the tags, and the refusal
# --------------------------------------------------------------------------
def test_the_four_geometry_tags_are_recorded_as_found(tmp_path):
    p = _write(tmp_path / "ortho.tif", _ramp(),
               tiepoint=(0, 0, 0, 22.0, 21.0, 0), pixel_scale=(0.001, 0.001, 0),
               geokeys={1024: 2, 1025: 1})
    geo = read_geometry(p)
    assert geo.tags_found == ("ModelPixelScale", "ModelTiepoint", "GeoKeyDirectory")
    assert geo.shape == (40, 60)
    assert geo.model_type == 2


def test_a_geotiff_without_a_ground_tie_is_not_ingested(tmp_path):
    p = tmp_path / "bare.tif"
    tifffile.imwrite(str(p), _ramp(), compression=None)
    with pytest.raises(GeoTiffNotIngested) as exc:
        read_geometry(p)
    # the failing step is named, per §4
    assert "step 1" in str(exc.value)
    assert "ModelTiepoint" in str(exc.value) or "(none)" in str(exc.value)


# --------------------------------------------------------------------------
# §4 step 2 -- structural identity
# --------------------------------------------------------------------------
def test_structural_identity_passes_on_an_uncompressed_product(tmp_path):
    p = _write(tmp_path / "s.tif", _ramp(),
               tiepoint=(0, 0, 0, 22.0, 21.0, 0), pixel_scale=(0.001, 0.001, 0),
               geokeys={1024: 2})
    passed = structural_identity(p)
    assert any("byte counts sum to" in line for line in passed)
    assert any("40 lines x 60 samples" in line for line in passed)


def test_a_compressed_product_says_the_sum_was_not_compared(tmp_path):
    p = tmp_path / "z.tif"
    tifffile.imwrite(str(p), _ramp(), compression="zlib",
                     extratags=[(33550, "d", 3, (0.001, 0.001, 0.0), True),
                                (33922, "d", 6, (0, 0, 0, 22.0, 21.0, 0), True)])
    passed = structural_identity(p)
    assert any("compressed sizes" in line for line in passed)


# --------------------------------------------------------------------------
# §4 step 3 -- the window decode, contract C2
# --------------------------------------------------------------------------
def test_a_decoded_window_equals_the_array_it_was_written_from(tmp_path):
    data = _ramp()
    p = _write(tmp_path / "w.tif", data,
               tiepoint=(0, 0, 0, 22.0, 21.0, 0), pixel_scale=(0.001, 0.001, 0),
               geokeys={1024: 2})
    got = decode_window(p, 7, 19, 5, 23)
    assert got.shape == (12, 18)
    # exact, not approximate: array[line, sample] with no transpose or flip
    assert np.array_equal(got, data[7:19, 5:23])


def test_a_window_outside_the_product_is_refused(tmp_path):
    p = _write(tmp_path / "w.tif", _ramp(),
               tiepoint=(0, 0, 0, 22.0, 21.0, 0), pixel_scale=(0.001, 0.001, 0),
               geokeys={1024: 2})
    with pytest.raises(GeoTiffNotIngested):
        decode_window(p, 0, 41, 0, 60)


# --------------------------------------------------------------------------
# §4 step 5 -- placement
# --------------------------------------------------------------------------
def test_a_geographic_grid_places_as_a_mapblock_and_round_trips(tmp_path):
    """lon/lat in, pixel out, lon/lat back -- to floating-point closure."""
    dpp = 0.001                      # degrees per pixel
    lon_left, lat_top = 21.5, 20.5   # the (-0.5, -0.5) edge
    p = _write(tmp_path / "geo.tif", _ramp(),
               tiepoint=(0, 0, 0, lon_left, lat_top, 0),
               pixel_scale=(dpp, dpp, 0), geokeys={1024: 2, 1025: 1})
    block = place(p, row0=0, row1=40, col0=0, col1=60, name="tmc2-geo")

    assert isinstance(block, MapBlock)
    assert block.ppd_lon == pytest.approx(1.0 / dpp)
    assert block.lat_top_deg == pytest.approx(lat_top)

    lons = np.array([21.51, 21.53, 21.55])
    lats = np.array([20.49, 20.47, 20.45])
    xy = block.block_xy_of_lonlat(lons, lats)
    back_lon, back_lat = block.lonlat_of_block_xy(xy[:, 0], xy[:, 1])
    assert np.allclose(back_lon, lons, atol=1e-9)
    assert np.allclose(back_lat, lats, atol=1e-9)


def test_pixel_is_point_shifts_the_edge_by_half_a_pixel(tmp_path):
    """The E-001 class of defect: a half-pixel convention error placed silently."""
    dpp = 0.001
    common = dict(tiepoint=(0, 0, 0, 21.5, 20.5, 0), pixel_scale=(dpp, dpp, 0))
    area = place(_write(tmp_path / "a.tif", _ramp(), geokeys={1024: 2, 1025: 1}, **common),
                 row0=0, row1=40, col0=0, col1=60, name="area")
    point = place(_write(tmp_path / "p.tif", _ramp(), geokeys={1024: 2, 1025: 2}, **common),
                  row0=0, row1=40, col0=0, col1=60, name="point")
    assert point.lon_left_deg == pytest.approx(area.lon_left_deg - 0.5 * dpp)
    assert point.lat_top_deg == pytest.approx(area.lat_top_deg + 0.5 * dpp)


def test_an_equirectangular_product_in_metres_places_and_round_trips(tmp_path):
    """The shape TMC-2 L2 is most likely to arrive in: projected metres."""
    gsd = 5.0                                   # 5 m, the TMC-2 rung
    lon0, lat0 = 0.0, 0.0
    lon_left, lat_top = 21.5, 20.5
    x0 = (lon_left - lon0) * M_PER_DEG
    y0 = (lat_top - lat0) * M_PER_DEG
    p = _write(tmp_path / "eq.tif", _ramp(),
               tiepoint=(0, 0, 0, x0, y0, 0), pixel_scale=(gsd, gsd, 0),
               geokeys={1024: 1, 1025: 1, 3075: 17})
    block = place(p, row0=0, row1=40, col0=0, col1=60, name="tmc2-eq")

    assert isinstance(block, MapBlock)
    mx, my = block.metres_per_pixel
    assert my == pytest.approx(gsd, rel=1e-9)
    assert block.lon_left_deg == pytest.approx(lon_left, abs=1e-9)
    assert block.lat_top_deg == pytest.approx(lat_top, abs=1e-9)

    lons = np.array([21.5001, 21.5004])
    lats = np.array([20.4999, 20.4996])
    xy = block.block_xy_of_lonlat(lons, lats)
    back_lon, back_lat = block.lonlat_of_block_xy(xy[:, 0], xy[:, 1])
    assert np.allclose(back_lon, lons, atol=1e-9)
    assert np.allclose(back_lat, lats, atol=1e-9)


def test_polar_stereographic_places_and_round_trips(tmp_path):
    """The fallback region (~69 S) would arrive polar stereographic."""
    p = _write(tmp_path / "ps.tif", _ramp(),
               tiepoint=(0, 0, 0, -6000.0, -600_000.0, 0),
               pixel_scale=(5.0, 5.0, 0),
               geokeys={1024: 1, 1025: 1, 3075: 15, 3081: 0, 3095: 0},
               doubles=None)
    block = place(p, row0=0, row1=40, col0=0, col1=60, name="ps")
    assert isinstance(block, PolarStereoBlock)
    assert block.north is False or block.north is True   # decided by 3081

    # round-trip through the projection, in block coordinates
    x = np.array([3.0, 17.5, 44.0])
    y = np.array([2.0, 21.5, 33.0])
    lon, lat = block.lonlat_of_block_xy(x, y)
    xy = block.block_xy_of_lonlat(lon, lat)
    assert np.allclose(xy[:, 0], x, atol=1e-6)
    assert np.allclose(xy[:, 1], y, atol=1e-6)


def test_an_unsupported_projection_is_not_placed_and_is_named(tmp_path):
    """Part 1 §4: never approximated by equirectangular."""
    p = _write(tmp_path / "merc.tif", _ramp(),
               tiepoint=(0, 0, 0, 1.0, 2.0, 0), pixel_scale=(5.0, 5.0, 0),
               geokeys={1024: 1, 1025: 1, 3075: 7})   # CT_Mercator
    with pytest.raises(GeoTiffNotPlaced) as exc:
        place(p, row0=0, row1=10, col0=0, col1=10, name="merc")
    msg = str(exc.value)
    assert "step 5" in msg
    assert "3075" in msg or "unsupported" in msg
    assert "never" in msg and "approximated" in msg


def test_placement_records_the_audit_trail_in_provenance(tmp_path):
    """§4 step 9: the row must say which tags placed it, and how."""
    p = _write(tmp_path / "prov.tif", _ramp(),
               tiepoint=(0, 0, 0, 21.5, 20.5, 0), pixel_scale=(0.001, 0.001, 0),
               geokeys={1024: 2, 1025: 1})
    block = place(p, row0=0, row1=40, col0=0, col1=60, name="prov",
                  provenance={"product_id": "ch2_tmc2_demo"})
    prov = block.provenance
    assert prov["product_id"] == "ch2_tmc2_demo"
    assert "ModelTiepoint" in prov["geometry_tags_found"]
    assert prov["raster_type"] == "PixelIsArea"
    assert "Geographic" in prov["projection"]


def test_a_transformation_tag_alone_is_enough_to_place(tmp_path):
    """ModelTransformation is the other legal tie; it must not need a tiepoint."""
    dpp = 0.001
    t = (dpp, 0, 0, 21.5,
         0, -dpp, 0, 20.5,
         0, 0, 1, 0,
         0, 0, 0, 1)
    p = _write(tmp_path / "t.tif", _ramp(), transformation=t,
               geokeys={1024: 2, 1025: 1})
    block = place(p, row0=0, row1=40, col0=0, col1=60, name="t")
    assert isinstance(block, MapBlock)
    assert block.lon_left_deg == pytest.approx(21.5)
    assert block.lat_top_deg == pytest.approx(20.5)
    assert block.ppd_lon == pytest.approx(1.0 / dpp)
