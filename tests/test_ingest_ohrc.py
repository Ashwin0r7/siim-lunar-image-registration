"""OHRC label and geometry-grid reader.

Synthetic cases pin the parsing, the round trip and the refusal to
extrapolate. The real-data case, which skips when the gitignored PRADAN
products are absent, pins the fact EXP-023's design rests on: the grid
reproduces the REFINED corners and not the system-level ones.
"""

import glob
from pathlib import Path

import numpy as np
import pytest

from siim.ingest.ohrc import OhrcGrid, grid_matches_corners, parse_ohrc_label

ROOT = Path(__file__).resolve().parents[1]

LABEL = """
<Product_Observational><Observation_Area><Time_Coordinates>
<start_date_time>2024-04-25T10:12:47.8407Z</start_date_time></Time_Coordinates></Observation_Area>
<md5_checksum>abc123</md5_checksum>
<Axis_Array><axis_name>Line</axis_name><elements>301</elements></Axis_Array>
<Axis_Array><axis_name>Sample</axis_name><elements>201</elements></Axis_Array>
<Mission_Area><isda:Product_Parameters>
<isda:reference_data_used>LRO</isda:reference_data_used>
<isda:orbit_limb_direction>Descending</isda:orbit_limb_direction>
<isda:spacecraft_altitude unit="km">102.33</isda:spacecraft_altitude>
<isda:pixel_resolution unit="m/pixel">0.26</isda:pixel_resolution>
<isda:roll unit="deg">-6.809145</isda:roll><isda:pitch unit="deg">12.321116</isda:pitch>
<isda:yaw unit="deg">-0.000977</isda:yaw>
<isda:sun_azimuth unit="deg">303.534993</isda:sun_azimuth>
<isda:sun_elevation unit="deg">11.523608</isda:sun_elevation>
<isda:solar_incidence unit="deg">78.476392</isda:solar_incidence>
</isda:Product_Parameters><isda:Geometry_Parameters>
<isda:System_Level_Coordinates>
<isda:upper_left_latitude unit="deg">-69.1</isda:upper_left_latitude><isda:upper_left_longitude unit="deg">32.0</isda:upper_left_longitude>
<isda:upper_right_latitude unit="deg">-69.1</isda:upper_right_latitude><isda:upper_right_longitude unit="deg">32.3</isda:upper_right_longitude>
<isda:lower_left_latitude unit="deg">-69.9</isda:lower_left_latitude><isda:lower_left_longitude unit="deg">32.0</isda:lower_left_longitude>
<isda:lower_right_latitude unit="deg">-69.9</isda:lower_right_latitude><isda:lower_right_longitude unit="deg">32.3</isda:lower_right_longitude>
</isda:System_Level_Coordinates>
<isda:Refined_Corner_Coordinates>
<isda:upper_left_latitude unit="deg">-69.0</isda:upper_left_latitude><isda:upper_left_longitude unit="deg">32.1</isda:upper_left_longitude>
<isda:upper_right_latitude unit="deg">-69.0</isda:upper_right_latitude><isda:upper_right_longitude unit="deg">32.4</isda:upper_right_longitude>
<isda:lower_left_latitude unit="deg">-69.8</isda:lower_left_latitude><isda:lower_left_longitude unit="deg">32.1</isda:lower_left_longitude>
<isda:lower_right_latitude unit="deg">-69.8</isda:lower_right_latitude><isda:lower_right_longitude unit="deg">32.4</isda:lower_right_longitude>
</isda:Refined_Corner_Coordinates></isda:Geometry_Parameters></Mission_Area></Product_Observational>
"""


def _grid(lines=301, samples=201):
    scans = np.r_[np.arange(0, lines - 1, 100), lines - 1].astype(float)
    pixels = np.r_[np.arange(0, samples - 1, 100), samples - 1].astype(float)
    S, P = np.meshgrid(scans, pixels, indexing="ij")
    lon = 32.1 + 0.3 * P / (samples - 1) + 1e-6 * S
    lat = -69.0 - 0.8 * S / (lines - 1) + 2e-6 * P
    return OhrcGrid(scans, pixels, lon, lat)


def test_label_keeps_both_corner_sets_and_names_its_reference():
    lab = parse_ohrc_label(LABEL)
    assert (lab.lines, lab.samples, lab.md5) == (301, 201, "abc123")
    assert lab.reference_data_used == "LRO"
    assert lab.solar_incidence_deg == 78.476392 and lab.sun_azimuth_deg == 303.534993
    assert lab.refined_corners["upper_left"] == (32.1, -69.0)
    assert lab.system_corners["upper_left"] == (32.0, -69.1)
    assert lab.corners("refined").lines == 301
    with pytest.raises(KeyError):
        lab.corners("best")                          # no default: the caller names one
    assert 13.9 < lab.off_nadir_deg < 14.2


def test_label_missing_geometry_is_refused():
    with pytest.raises(ValueError):
        parse_ohrc_label(LABEL.replace("Refined_Corner_Coordinates", "Other"))


def test_grid_round_trip_and_no_extrapolation():
    g = _grid()
    for s, p in [(0, 0), (123.4, 56.7), (300, 200), (250.5, 199.9)]:
        lon, lat = g.lonlat_at(s, p)
        s2, p2 = g.pixel_at(lon, lat)
        assert abs(s2 - s) < 1e-4 and abs(p2 - p) < 1e-4
    with pytest.raises(ValueError):
        g.lonlat_at(301, 0)
    with pytest.raises(ValueError):
        g.pixel_at(31.0, -69.4)


def test_grid_identifies_which_corner_set_it_follows():
    lab = parse_ohrc_label(LABEL)
    g = _grid()
    assert grid_matches_corners(g, lab.refined_corners) < 1e-3
    assert grid_matches_corners(g, lab.system_corners) > 0.09


def _real(obs):
    xml = glob.glob(str(ROOT / "realdata" / "realdata" / "OHRC" / obs / "*" / "data" / "calibrated" / "*" / "*d_img*.xml"))
    grd = glob.glob(str(ROOT / "realdata" / "realdata" / "OHRC" / obs / "*" / "geometry" / "calibrated" / "*" / "*g_grd*.csv"))
    return (xml[0], grd[0]) if xml and grd else None


@pytest.mark.parametrize("obs", ["obs1", "obs2"])
def test_real_grid_follows_the_refined_corners(obs):
    paths = _real(obs)
    if paths is None:
        pytest.skip("OHRC products are not on disk (gitignored)")
    lab = parse_ohrc_label(Path(paths[0]).read_text(encoding="utf-8"))
    g = OhrcGrid.from_csv(paths[1])
    assert g.extent == (lab.lines - 1, lab.samples - 1)
    assert grid_matches_corners(g, lab.refined_corners) <= 1e-5
    assert grid_matches_corners(g, lab.system_corners) > 0.08
    assert lab.reference_data_used == "LRO"
    s, p = g.pixel_at(32.319, -69.373)                  # EXP-023's target is inside the swath
    assert 0 < s < lab.lines - 1 and 0 < p < lab.samples - 1
