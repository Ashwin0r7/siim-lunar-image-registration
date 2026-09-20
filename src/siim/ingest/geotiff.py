"""GeoTIFF reading and placement for Chandrayaan-2 TMC-2 Level-2 products.

REAL-DATA-09 §4 steps 1-3 and 5, map-projected route. TMC-2 Level-2
orthoimages and their stereo DEMs are distributed by PRADAN as GeoTIFF, a
format no other product in this project uses: every reader here so far is
PDS4 (``pds4``) or a raw PDS3 row block (``mapgrid``).

**What is verified, not assumed.** Part 1 §3 records that the projection and
datum of these products are *not known to this project in advance*. This
module therefore reads the four GeoTIFF geometry tags and **records which were
found**, derives the pixel map from what is actually present, and refuses --
naming the failing step -- rather than defaulting. In particular an unknown
projection is never approximated by equirectangular: the GeoKey's own
projection code is quoted back and the product is *not placed*.

**Where the output goes.** An equirectangular product becomes a
:class:`~siim.ingest.mapgrid.MapBlock`, the identical structure REAL-DATA-08
built for the Mini-RF strip and the WAC mosaic, so the runner, the geometry
check and the pipeline see no new product type. Polar stereographic cannot be
expressed as a MapBlock -- it is not affine in (lon, lat) -- and gets
:class:`PolarStereoBlock`, which exposes the same four ground<->pixel methods.

**Sphere.** 1737.4 km, the value used for SLDEM, Mini-RF and WAC throughout
this repository. If a label states a different semi-major axis
(``GeogSemiMajorAxisGeoKey``) the difference is recorded and the label's value
is used.

Contract C2 holds: decoded windows are ``array[line, sample]``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .mapgrid import MapBlock

__all__ = [
    "GeoTiffError",
    "GeoTiffNotIngested",
    "GeoTiffNotPlaced",
    "MOON_RADIUS_M",
    "GEOTIFF_GEOMETRY_TAGS",
    "GeoTiffGeometry",
    "PolarStereoBlock",
    "read_geometry",
    "structural_identity",
    "decode_window",
    "place",
]

#: The sphere this project measures the Moon on, in metres.
MOON_RADIUS_M = 1_737_400.0

#: The four tags Part 1 §4 step 1 names, by TIFF tag number. Recorded as found.
GEOTIFF_GEOMETRY_TAGS: dict[int, str] = {
    33922: "ModelTiepoint",
    33550: "ModelPixelScale",
    34264: "ModelTransformation",
    34735: "GeoKeyDirectory",
}

# GeoTIFF GeoKey numbers actually consulted here. Others are recorded verbatim
# in `geokeys` but not interpreted.
_GT_MODEL_TYPE = 1024        # 1 Projected, 2 Geographic, 3 Geocentric
_GT_RASTER_TYPE = 1025       # 1 PixelIsArea, 2 PixelIsPoint
_GEOG_SEMI_MAJOR = 2057
_PROJ_COORD_TRANS = 3075     # 15 PolarStereographic, 17 Equirectangular
_PROJ_STD_PARALLEL1 = 3078
_PROJ_NAT_ORIGIN_LONG = 3080
_PROJ_NAT_ORIGIN_LAT = 3081
_PROJ_FALSE_EASTING = 3082
_PROJ_FALSE_NORTHING = 3083
_PROJ_CENTER_LONG = 3088
_PROJ_STRAIGHT_VERT_POLE_LONG = 3095

_CT_POLAR_STEREOGRAPHIC = 15
_CT_EQUIRECTANGULAR = 17

#: Coordinate transformations this module implements. Anything else is
#: *not placed*, by name.
_SUPPORTED_CT = {
    _CT_EQUIRECTANGULAR: "Equirectangular (CT 17)",
    _CT_POLAR_STEREOGRAPHIC: "PolarStereographic (CT 15)",
}


class GeoTiffError(ValueError):
    """Base for every refusal in this module."""


class GeoTiffNotIngested(GeoTiffError):
    """The file cannot be read as an image at all (§4 steps 1-3)."""


class GeoTiffNotPlaced(GeoTiffError):
    """The file decodes but its ground placement is not supported (§4 step 5)."""


def _tifffile():
    """Import ``tifffile`` with the reason it is needed, not an ImportError."""
    try:
        import tifffile  # noqa: PLC0415 - optional `chandrayaan2` extra
    except ModuleNotFoundError as exc:  # pragma: no cover - environment
        raise GeoTiffNotIngested(
            "tifffile is not installed; it is the `chandrayaan2` extra "
            "(BSD-3) declared in pyproject.toml. Install with "
            "`pip install 'tifffile>=2024.1'`."
        ) from exc
    return tifffile


@dataclass(frozen=True)
class GeoTiffGeometry:
    """What the four geometry tags actually said, plus the derived pixel map.

    ``tags_found`` is the audit trail Part 1 §4 step 1 asks for: the names of
    the geometry tags present in *this* file, in tag order.
    """

    path: Path
    shape: tuple[int, int]               # (lines, samples)
    dtype: str
    tags_found: tuple[str, ...]
    tiepoint: tuple[float, ...] | None   # (i, j, k, x, y, z), model units
    pixel_scale: tuple[float, ...] | None  # (sx, sy, sz), model units
    transformation: tuple[float, ...] | None  # 16 values, row-major 4x4
    geokeys: dict[int, Any] = field(default_factory=dict)
    semi_major_m: float = MOON_RADIUS_M
    semi_major_from_label: bool = False

    @property
    def model_type(self) -> int | None:
        return self.geokeys.get(_GT_MODEL_TYPE)

    @property
    def raster_type(self) -> int:
        """1 PixelIsArea (default per the GeoTIFF spec), 2 PixelIsPoint."""
        return int(self.geokeys.get(_GT_RASTER_TYPE, 1) or 1)

    @property
    def coord_transform(self) -> int | None:
        return self.geokeys.get(_PROJ_COORD_TRANS)

    @property
    def projection_name(self) -> str:
        ct = self.coord_transform
        if ct in _SUPPORTED_CT:
            return _SUPPORTED_CT[ct]
        if self.model_type == 2:
            return "Geographic (lon/lat, no projection)"
        return f"unsupported (ProjCoordTransGeoKey={ct!r})"

    def upper_left_model_xy(self) -> tuple[float, float]:
        """Model (x, y) of the raster's **line -0.5, sample -0.5 edge**.

        ``MapBlock`` is pixel-registered on that edge. A ``PixelIsArea``
        tiepoint already refers to the corner; a ``PixelIsPoint`` tiepoint
        refers to the centre of pixel (i, j) and is moved out by half a pixel.
        """
        if self.transformation is not None:
            t = self.transformation
            x0, y0 = float(t[3]), float(t[7])
            sx, sy = float(t[0]), float(t[5])
            if self.raster_type == 2:
                x0 -= 0.5 * sx
                y0 -= 0.5 * sy
            return x0, y0

        assert self.tiepoint is not None and self.pixel_scale is not None
        i, j = float(self.tiepoint[0]), float(self.tiepoint[1])
        x, y = float(self.tiepoint[3]), float(self.tiepoint[4])
        sx, sy = float(self.pixel_scale[0]), float(self.pixel_scale[1])
        # Walk from the tiepoint's raster position back to raster (0, 0);
        # y decreases as the line index grows, hence the sign.
        x0 = x - i * sx
        y0 = y + j * sy
        if self.raster_type == 2:
            x0 -= 0.5 * sx
            y0 += 0.5 * sy
        return x0, y0

    def model_pixel_size(self) -> tuple[float, float]:
        """(sx, sy) in model units, positive, from whichever tag is present."""
        if self.transformation is not None:
            t = self.transformation
            return abs(float(t[0])), abs(float(t[5]))
        assert self.pixel_scale is not None
        return abs(float(self.pixel_scale[0])), abs(float(self.pixel_scale[1]))


@dataclass(frozen=True)
class PolarStereoBlock:
    """A polar stereographic window, with MapBlock's ground<->pixel interface.

    Spherical polar stereographic about the pole named by
    ``ProjStraightVertPoleLongGeoKey``. Not a MapBlock: the lon/lat map is not
    affine in the pixel indices, so the four methods are implemented here
    rather than inherited.
    """

    data: NDArray[np.float32]
    row0: int
    col0: int
    x_left_m: float          # model x of the sample -0.5 edge
    y_top_m: float           # model y of the line   -0.5 edge
    sx_m: float
    sy_m: float
    north: bool
    vertical_lon_deg: float
    semi_major_m: float
    name: str
    provenance: dict

    def _model_xy(self, line, sample):
        x = self.x_left_m + (np.asarray(sample, float) + 0.5) * self.sx_m
        y = self.y_top_m - (np.asarray(line, float) + 0.5) * self.sy_m
        return x, y

    def lonlat_of_block_xy(self, x, y):
        mx, my = self._model_xy(np.asarray(y, float) + self.row0,
                                np.asarray(x, float) + self.col0)
        rho = np.hypot(mx, my)
        c = 2.0 * np.arctan2(rho, 2.0 * self.semi_major_m)
        sign = 1.0 if self.north else -1.0
        lat = sign * (np.pi / 2.0 - c)
        lon = np.deg2rad(self.vertical_lon_deg) + np.arctan2(mx, sign * -my)
        return (np.rad2deg(lon) + 180.0) % 360.0 - 180.0, np.rad2deg(lat)

    def block_xy_of_lonlat(self, lon, lat) -> NDArray[np.float64]:
        lon_r = np.deg2rad(np.asarray(lon, float))
        lat_r = np.deg2rad(np.asarray(lat, float))
        sign = 1.0 if self.north else -1.0
        dlon = lon_r - np.deg2rad(self.vertical_lon_deg)
        t = np.tan(np.pi / 4.0 - sign * lat_r / 2.0)
        rho = 2.0 * self.semi_major_m * t
        mx = rho * np.sin(dlon)
        my = -sign * rho * np.cos(dlon)
        sample = (mx - self.x_left_m) / self.sx_m - 0.5 - self.col0
        line = (self.y_top_m - my) / self.sy_m - 0.5 - self.row0
        return np.column_stack([np.asarray(sample, float).ravel(),
                                np.asarray(line, float).ravel()])

    @property
    def metres_per_pixel(self) -> tuple[float, float]:
        return (float(self.sx_m), float(self.sy_m))


def read_geometry(path: str | Path) -> GeoTiffGeometry:
    """Read shape, dtype and the four geometry tags. Refuse if unplaceable.

    Raises :class:`GeoTiffNotIngested` when the file carries neither a
    tiepoint-with-pixel-scale nor a transformation -- Part 1 §4 step 1's
    explicit refusal.
    """
    tf = _tifffile()
    path = Path(path)
    with tf.TiffFile(str(path)) as fh:
        if not fh.pages:
            raise GeoTiffNotIngested(f"{path.name}: no TIFF pages")
        page = fh.pages[0]
        tags = page.tags

        found = tuple(name for num, name in sorted(GEOTIFF_GEOMETRY_TAGS.items())
                      if num in tags)

        def _vals(num: int) -> tuple[float, ...] | None:
            if num not in tags:
                return None
            v = tags[num].value
            return tuple(float(x) for x in np.atleast_1d(v).ravel())

        tiepoint = _vals(33922)
        pixel_scale = _vals(33550)
        transformation = _vals(34264)
        geokeys = _parse_geokeys(tags)

        shape = (int(page.imagelength), int(page.imagewidth))
        dtype = np.dtype(page.dtype).str

    has_tiepoint = tiepoint is not None and len(tiepoint) >= 6 and \
        pixel_scale is not None and len(pixel_scale) >= 2
    has_transform = transformation is not None and len(transformation) >= 16
    if not (has_tiepoint or has_transform):
        raise GeoTiffNotIngested(
            f"{path.name}: not ingested at §4 step 1 -- no usable ground tie. "
            f"Geometry tags found: {found or '(none)'}. A GeoTIFF without "
            f"either ModelTiepoint+ModelPixelScale or ModelTransformation "
            f"cannot be placed and is not decoded further.")

    semi = MOON_RADIUS_M
    from_label = False
    if _GEOG_SEMI_MAJOR in geokeys:
        try:
            semi = float(geokeys[_GEOG_SEMI_MAJOR])
            from_label = True
        except (TypeError, ValueError):
            semi, from_label = MOON_RADIUS_M, False

    return GeoTiffGeometry(
        path=path, shape=shape, dtype=dtype, tags_found=found,
        tiepoint=tiepoint, pixel_scale=pixel_scale,
        transformation=transformation, geokeys=geokeys,
        semi_major_m=semi, semi_major_from_label=from_label)


def _parse_geokeys(tags) -> dict[int, Any]:
    """Decode GeoKeyDirectory (34735) with its two value tags (34736/34737)."""
    if 34735 not in tags:
        return {}
    d = [int(x) for x in np.atleast_1d(tags[34735].value).ravel()]
    if len(d) < 4:
        return {}
    doubles = ([float(x) for x in np.atleast_1d(tags[34736].value).ravel()]
               if 34736 in tags else [])
    ascii_val = tags[34737].value if 34737 in tags else ""
    if isinstance(ascii_val, bytes):
        ascii_val = ascii_val.decode("ascii", "replace")

    out: dict[int, Any] = {}
    n = d[3]
    for k in range(n):
        base = 4 + 4 * k
        if base + 3 >= len(d):
            break
        key_id, loc, count, off = d[base], d[base + 1], d[base + 2], d[base + 3]
        if loc == 0:
            out[key_id] = off
        elif loc == 34736 and off < len(doubles):
            out[key_id] = doubles[off] if count == 1 else doubles[off:off + count]
        elif loc == 34737:
            out[key_id] = str(ascii_val[off:off + count]).rstrip("|\x00")
    return out


def structural_identity(path: str | Path) -> list[str]:
    """§4 step 2 for TIFF: strip/tile byte counts must sum to the image size.

    Returns the list of checks that passed, in the style of
    ``pds4.validate_structure``. Raises :class:`GeoTiffNotIngested` on
    mismatch -- the check that caught E-025's shape on NAC, and it is not
    optional.
    """
    tf = _tifffile()
    path = Path(path)
    passed: list[str] = []
    with tf.TiffFile(str(path)) as fh:
        page = fh.pages[0]
        lines, samples = int(page.imagelength), int(page.imagewidth)
        itemsize = int(np.dtype(page.dtype).itemsize)
        spp = int(page.samplesperpixel or 1)
        expected = lines * samples * itemsize * spp

        counts = page.tags.get(279) or page.tags.get(325)   # Strip/TileByteCounts
        if counts is None:
            raise GeoTiffNotIngested(
                f"{path.name}: not ingested at §4 step 2 -- neither "
                f"StripByteCounts (279) nor TileByteCounts (325) present.")
        total = int(np.sum(np.atleast_1d(counts.value)))

        compression = int(page.compression) if page.compression is not None else 1
        if compression != 1:
            passed.append(
                f"compression {compression} (not 1/none): byte counts are "
                f"compressed sizes, so the sum is not compared to "
                f"{expected} bytes; decode is checked instead")
        elif total != expected:
            raise GeoTiffNotIngested(
                f"{path.name}: not ingested at §4 step 2 -- strip/tile byte "
                f"counts sum to {total}, expected {expected} "
                f"({lines} lines x {samples} samples x {itemsize} bytes"
                f"{f' x {spp} bands' if spp > 1 else ''}).")
        else:
            passed.append(f"strip/tile byte counts sum to {total} == "
                          f"{lines}x{samples}x{itemsize}"
                          f"{f'x{spp}' if spp > 1 else ''}")

        passed.append(f"shape {lines} lines x {samples} samples, dtype "
                      f"{np.dtype(page.dtype).str}")
        if 33922 in page.tags or 34264 in page.tags:
            passed.append("ground tie present")
    return passed


def decode_window(path: str | Path, row0: int, row1: int, col0: int,
                  col1: int) -> NDArray[np.float32]:
    """Decode ``[row0:row1, col0:col1]`` as ``array[line, sample]`` (C2).

    Reads through ``tifffile``'s page-level access so that strip/tile layout,
    byte order and predictors are handled by the library rather than
    re-implemented here. The window is bounds-checked against the product.
    """
    tf = _tifffile()
    path = Path(path)
    with tf.TiffFile(str(path)) as fh:
        page = fh.pages[0]
        lines, samples = int(page.imagelength), int(page.imagewidth)
        if not (0 <= row0 < row1 <= lines and 0 <= col0 < col1 <= samples):
            raise GeoTiffNotIngested(
                f"{path.name}: window [{row0}:{row1}, {col0}:{col1}] is "
                f"outside the product's {lines} x {samples} pixels.")
        arr = page.asarray()
    if arr.ndim == 3:
        arr = arr[..., 0]
    return np.ascontiguousarray(arr[row0:row1, col0:col1]).astype(np.float32)


def place(path: str | Path, *, row0: int, row1: int, col0: int, col1: int,
          name: str, provenance: dict | None = None
          ) -> MapBlock | PolarStereoBlock:
    """Decode a window and place it on the ground. The §4 step 5 entry point.

    Equirectangular (or a plain geographic lon/lat grid) returns a
    :class:`~siim.ingest.mapgrid.MapBlock`; polar stereographic returns a
    :class:`PolarStereoBlock`. Every other projection raises
    :class:`GeoTiffNotPlaced` **naming the projection**, and the caller
    records the product as *not placed* rather than approximating it.
    """
    geo = read_geometry(path)
    data = decode_window(path, row0, row1, col0, col1)
    prov = dict(provenance or {})
    prov.setdefault("geometry_tags_found", list(geo.tags_found))
    prov.setdefault("projection", geo.projection_name)
    prov.setdefault("raster_type",
                    "PixelIsPoint" if geo.raster_type == 2 else "PixelIsArea")
    if geo.semi_major_from_label:
        prov.setdefault("semi_major_m_from_label", geo.semi_major_m)

    ct = geo.coord_transform
    x0, y0 = geo.upper_left_model_xy()
    sx, sy = geo.model_pixel_size()

    # -- geographic: model units are already degrees ------------------------
    if ct is None and geo.model_type == 2:
        return MapBlock(data=data, row0=row0, col0=col0,
                        ppd_lat=1.0 / sy, ppd_lon=1.0 / sx,
                        lat_top_deg=y0, lon_left_deg=x0,
                        name=name, provenance=prov)

    if ct == _CT_EQUIRECTANGULAR:
        std_par = float(geo.geokeys.get(_PROJ_STD_PARALLEL1, 0.0) or 0.0)
        lon0 = float(geo.geokeys.get(_PROJ_CENTER_LONG,
                                     geo.geokeys.get(_PROJ_NAT_ORIGIN_LONG, 0.0)) or 0.0)
        lat0 = float(geo.geokeys.get(_PROJ_NAT_ORIGIN_LAT, 0.0) or 0.0)
        fe = float(geo.geokeys.get(_PROJ_FALSE_EASTING, 0.0) or 0.0)
        fn = float(geo.geokeys.get(_PROJ_FALSE_NORTHING, 0.0) or 0.0)
        m_per_deg = geo.semi_major_m * np.pi / 180.0
        cos_std = float(np.cos(np.deg2rad(std_par)))
        if abs(cos_std) < 1e-12:
            raise GeoTiffNotPlaced(
                f"{Path(path).name}: not placed -- equirectangular standard "
                f"parallel {std_par} deg is degenerate.")
        deg_per_px_lon = sx / (m_per_deg * cos_std)
        deg_per_px_lat = sy / m_per_deg
        lon_left = lon0 + (x0 - fe) / (m_per_deg * cos_std)
        lat_top = lat0 + (y0 - fn) / m_per_deg
        return MapBlock(data=data, row0=row0, col0=col0,
                        ppd_lat=1.0 / deg_per_px_lat, ppd_lon=1.0 / deg_per_px_lon,
                        lat_top_deg=lat_top, lon_left_deg=lon_left,
                        name=name, provenance=prov)

    if ct == _CT_POLAR_STEREOGRAPHIC:
        lat_nat = float(geo.geokeys.get(_PROJ_NAT_ORIGIN_LAT, 90.0) or 90.0)
        vert_lon = float(geo.geokeys.get(_PROJ_STRAIGHT_VERT_POLE_LONG,
                                         geo.geokeys.get(_PROJ_NAT_ORIGIN_LONG, 0.0)) or 0.0)
        fe = float(geo.geokeys.get(_PROJ_FALSE_EASTING, 0.0) or 0.0)
        fn = float(geo.geokeys.get(_PROJ_FALSE_NORTHING, 0.0) or 0.0)
        return PolarStereoBlock(
            data=data, row0=row0, col0=col0,
            x_left_m=x0 - fe, y_top_m=y0 - fn, sx_m=sx, sy_m=sy,
            north=lat_nat >= 0.0, vertical_lon_deg=vert_lon,
            semi_major_m=geo.semi_major_m, name=name, provenance=prov)

    raise GeoTiffNotPlaced(
        f"{Path(path).name}: not placed at §4 step 5 -- projection "
        f"{geo.projection_name}. Only {', '.join(_SUPPORTED_CT.values())} are "
        f"implemented; an unsupported projection is reported, never "
        f"approximated by equirectangular.")
