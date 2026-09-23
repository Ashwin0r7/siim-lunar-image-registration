"""Chandrayaan-2 OHRC: label parameters, the two corner sets, and the geometry grid.

Why this module exists
----------------------
REAL-DATA-09 showed the image itself reads through the unmodified PDS4 reader
(:mod:`siim.ingest.pds4`). What that reader does not know is the ISRO mission
area (``isda:``) and the per-product geometry grid, which EXP-023 needs to
place a window, orient it and predict where it lands in a NAC frame.

Two facts about these products shape everything below. Both are read from the
label, never assumed:

* **Each label carries two corner sets.** ``System_Level_Coordinates`` are the
  predicted corners. ``Refined_Corner_Coordinates`` are corners ISRO refined
  against the reference named in ``isda:reference_data_used``, which is
  ``LRO`` for the products on disk. The two sets differ by kilometres.
  :class:`OhrcLabel` keeps both, so a caller must choose one by name.
* **The geometry grid follows the refined set.** ``g_grd`` gives
  ``(Longitude, Latitude)`` at nodes every 100 pixels and 100 scans, plus the
  last pixel and the last scan. :func:`grid_matches_corners` checks which
  corner set the grid reproduces, so no caller has to take that on trust.

Conventions: ``scan`` is the image line (array row), ``pixel`` the sample
(array column), both 0-based. Coordinates are ``(lon, lat)`` in degrees,
east-positive, as in :mod:`siim.ingest.footprint`.

What this module does NOT do: it is not a camera model. Interpolation on the
grid is bilinear within a 100 × 100 cell (26 m × 26 m at 0.26 m), and it
carries whatever error the grid itself has.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from siim.ingest.footprint import FrameCorners

_NUM = r"(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"


def _tag(xml: str, name: str) -> str | None:
    m = re.search(rf"<(?:isda:)?{name}\b[^>]*>\s*([^<]*?)\s*</(?:isda:)?{name}>", xml)
    return m.group(1) if m else None


def _num(xml: str, name: str) -> float | None:
    v = _tag(xml, name)
    return float(v) if v not in (None, "") else None


def _corner_block(xml: str, block: str) -> dict[str, tuple[float, float]]:
    m = re.search(rf"<isda:{block}>(.*?)</isda:{block}>", xml, re.S)
    if not m:
        raise ValueError(f"OHRC label has no isda:{block}")
    body = m.group(1)
    out = {}
    for c in ("upper_left", "upper_right", "lower_left", "lower_right"):
        lat, lon = _num(body, f"{c}_latitude"), _num(body, f"{c}_longitude")
        if lat is None or lon is None:
            raise ValueError(f"isda:{block} lacks {c}")
        out[c] = (lon, lat)
    return out


@dataclass(frozen=True)
class OhrcLabel:
    """The ISRO mission-area parameters of one OHRC calibrated product."""

    start_utc: str
    lines: int
    samples: int
    md5: str | None
    pixel_resolution_m: float
    solar_incidence_deg: float
    sun_azimuth_deg: float
    sun_elevation_deg: float
    roll_deg: float
    pitch_deg: float
    yaw_deg: float
    altitude_km: float
    reference_data_used: str | None
    orbit_limb_direction: str | None
    system_corners: dict
    refined_corners: dict

    def corners(self, which: str) -> FrameCorners:
        """``FrameCorners`` for ``which`` in {``"refined"``, ``"system"``}.

        Named explicitly because the two differ by kilometres, and a default
        would hide which one a result rests on.
        """
        c = {"refined": self.refined_corners, "system": self.system_corners}[which]
        return FrameCorners(c["upper_left"], c["upper_right"], c["lower_left"], c["lower_right"],
                            self.lines, self.samples)

    @property
    def off_nadir_deg(self) -> float:
        """Pointing off nadir from roll and pitch (small-angle composition)."""
        r, p = np.deg2rad(self.roll_deg), np.deg2rad(self.pitch_deg)
        return float(np.rad2deg(np.arccos(np.cos(r) * np.cos(p))))


def parse_ohrc_label(xml: str) -> OhrcLabel:
    """Read an OHRC calibrated-image label. Raises if a needed field is absent."""
    lines = re.search(r"<axis_name>Line</axis_name>\s*<elements>(\d+)</elements>", xml)
    samples = re.search(r"<axis_name>Sample</axis_name>\s*<elements>(\d+)</elements>", xml)
    if not (lines and samples):
        raise ValueError("OHRC label: Line/Sample axes not found")
    need = {"pixel_resolution": None, "solar_incidence": None, "sun_azimuth": None,
            "sun_elevation": None, "roll": None, "pitch": None, "yaw": None,
            "spacecraft_altitude": None}
    for k in need:
        need[k] = _num(xml, k)
        if need[k] is None:
            raise ValueError(f"OHRC label: isda:{k} not found")
    start = _tag(xml, "start_date_time")
    return OhrcLabel(
        start_utc=start or "", lines=int(lines.group(1)), samples=int(samples.group(1)),
        md5=_tag(xml, "md5_checksum"),
        pixel_resolution_m=need["pixel_resolution"], solar_incidence_deg=need["solar_incidence"],
        sun_azimuth_deg=need["sun_azimuth"], sun_elevation_deg=need["sun_elevation"],
        roll_deg=need["roll"], pitch_deg=need["pitch"], yaw_deg=need["yaw"],
        altitude_km=need["spacecraft_altitude"],
        reference_data_used=_tag(xml, "reference_data_used"),
        orbit_limb_direction=_tag(xml, "orbit_limb_direction"),
        system_corners=_corner_block(xml, "System_Level_Coordinates"),
        refined_corners=_corner_block(xml, "Refined_Corner_Coordinates"),
    )


class OhrcGrid:
    """The ``g_grd`` geometry grid: lon/lat at rectilinear (scan, pixel) nodes."""

    def __init__(self, scans: np.ndarray, pixels: np.ndarray, lon: np.ndarray, lat: np.ndarray):
        self.scans = np.asarray(scans, float)
        self.pixels = np.asarray(pixels, float)
        self.lon = np.asarray(lon, float)
        self.lat = np.asarray(lat, float)
        if self.lon.shape != (len(self.scans), len(self.pixels)) or self.lat.shape != self.lon.shape:
            raise ValueError("grid arrays do not match the node axes")
        if np.any(np.diff(self.scans) <= 0) or np.any(np.diff(self.pixels) <= 0):
            raise ValueError("grid node axes must increase strictly")

    @classmethod
    def from_csv(cls, path: str | Path) -> "OhrcGrid":
        a = np.loadtxt(path, delimiter=",", skiprows=1)
        pixels, scans = np.unique(a[:, 2]), np.unique(a[:, 3])
        if len(pixels) * len(scans) != len(a):
            raise ValueError(f"{path}: grid is not rectilinear")
        order = np.lexsort((a[:, 2], a[:, 3]))
        a = a[order]
        shape = (len(scans), len(pixels))
        return cls(scans, pixels, a[:, 0].reshape(shape), a[:, 1].reshape(shape))

    @property
    def extent(self) -> tuple[float, float]:
        """``(last scan, last pixel)``, i.e. ``(lines - 1, samples - 1)``."""
        return float(self.scans[-1]), float(self.pixels[-1])

    def _cell(self, scan: float, pixel: float):
        i = int(np.clip(np.searchsorted(self.scans, scan, side="right") - 1, 0, len(self.scans) - 2))
        j = int(np.clip(np.searchsorted(self.pixels, pixel, side="right") - 1, 0, len(self.pixels) - 2))
        v = (scan - self.scans[i]) / (self.scans[i + 1] - self.scans[i])
        u = (pixel - self.pixels[j]) / (self.pixels[j + 1] - self.pixels[j])
        return i, j, u, v

    def _interp(self, arr, i, j, u, v):
        return ((1 - u) * (1 - v) * arr[i, j] + u * (1 - v) * arr[i, j + 1]
                + (1 - u) * v * arr[i + 1, j] + u * v * arr[i + 1, j + 1])

    def lonlat_at(self, scan: float, pixel: float) -> tuple[float, float]:
        """Bilinear ``(lon, lat)`` at a 0-based ``(scan, pixel)``. Refuses to extrapolate."""
        s_max, p_max = self.extent
        if not (0.0 <= scan <= s_max and 0.0 <= pixel <= p_max):
            raise ValueError(f"(scan {scan}, pixel {pixel}) outside the grid [0, {s_max}] x [0, {p_max}]")
        i, j, u, v = self._cell(scan, pixel)
        return float(self._interp(self.lon, i, j, u, v)), float(self._interp(self.lat, i, j, u, v))

    def lonlat_many(self, scans, pixels) -> tuple[np.ndarray, np.ndarray]:
        out = np.array([self.lonlat_at(float(s), float(p)) for s, p in zip(np.ravel(scans), np.ravel(pixels))])
        return out[:, 0].reshape(np.shape(scans)), out[:, 1].reshape(np.shape(scans))

    def pixel_at(self, lon: float, lat: float, *, tol_deg: float = 1e-10,
                 max_iter: int = 50, allow_outside: bool = False) -> tuple[float, float]:
        """Inverse: the 0-based ``(scan, pixel)`` of a ground point.

        Newton on the piecewise-bilinear surface with a finite-difference
        Jacobian. By default it raises if the point is outside the grid, for the
        reason :meth:`FrameCorners.pixel_at` gives: **no clamping**.

        ``allow_outside=True`` returns the position on the surface extended
        linearly from the edge cells, which can lie outside ``[0, extent]``. It
        exists for one purpose: building a rectangle that is *then clipped* to
        the swath (EXP-023 section 2.1), where dropping the out-of-swath points
        would shrink the rectangle instead of clipping it. A caller must clip
        before using such a position as a pixel.
        """
        s_max, p_max = self.extent
        s, p = s_max / 2, p_max / 2
        h = 1.0
        for _ in range(max_iter):
            lo, la = self._unchecked(s, p)
            r = np.array([lon - lo, lat - la])
            if abs(r[0]) < tol_deg and abs(r[1]) < tol_deg:
                break
            ls, as_ = self._unchecked(s + h, p)
            lp, ap = self._unchecked(s, p + h)
            J = np.array([[(ls - lo) / h, (lp - lo) / h], [(as_ - la) / h, (ap - la) / h]])
            ds, dp = np.linalg.solve(J, r)
            s, p = s + ds, p + dp
        else:
            raise ValueError(f"no convergence locating ({lon}, {lat}) in the OHRC grid")
        if not allow_outside and not (-1e-6 <= s <= s_max + 1e-6 and -1e-6 <= p <= p_max + 1e-6):
            raise ValueError(f"({lon}, {lat}) is outside the OHRC grid (scan {s:.1f}, pixel {p:.1f})")
        return float(s), float(p)

    def _unchecked(self, scan, pixel):
        i, j, u, v = self._cell(scan, pixel)
        return float(self._interp(self.lon, i, j, u, v)), float(self._interp(self.lat, i, j, u, v))

    def metres_per_step(self, scan: float, pixel: float, radius_m: float = 1737400.0) -> tuple[float, float]:
        """Ground distance of one scan and one pixel at a point (sphere)."""
        def dist(a, b):
            lon1, lat1, lon2, lat2 = map(np.deg2rad, (a[0], a[1], b[0], b[1]))
            hv = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
            return float(2 * radius_m * np.arcsin(np.sqrt(hv)))
        s_max, p_max = self.extent
        s0, p0 = min(scan, s_max - 100), min(pixel, p_max - 100)
        c = self.lonlat_at(s0, p0)
        return dist(c, self.lonlat_at(s0 + 100, p0)) / 100, dist(c, self.lonlat_at(s0, p0 + 100)) / 100


def grid_matches_corners(grid: OhrcGrid, corners: dict) -> float:
    """Max |difference| (degrees) between the grid's corner nodes and a corner set."""
    s_max, p_max = grid.extent
    at = {"upper_left": (0, 0), "upper_right": (0, p_max), "lower_left": (s_max, 0), "lower_right": (s_max, p_max)}
    return float(max(max(abs(a - b) for a, b in zip(grid.lonlat_at(*at[k]), corners[k])) for k in at))
