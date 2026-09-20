# REAL-DATA-09 — Implementation plan

**Written 2026-09-20, before the PRADAN products exist.** This plan implements
the ingestion contract frozen in
[`stages/REAL-DATA-09_chandrayaan2_ingestion.md`](stages/REAL-DATA-09_chandrayaan2_ingestion.md)
§4 and the method in §5. **It changes no criterion.** Where this document and
Part 1 differ, Part 1 wins and the difference is a defect in this plan.

This is a behaviour specification, not code. Every item names what a module
must *do*, what it must *refuse*, and how we know it works.

---

## 1. Readiness audit (measured 2026-09-20 13:10)

The contract needs nine steps. Six are already built and stage-tested; three
are not, and one dependency was declared but never installed.

| §4 step | What it needs | Status |
|---|---|---|
| 1 Label (PDS4) | `siim.ingest.pds4.parse_image_structure` | **REUSE** — 2D only |
| 1 Label (PDS4 3-D) | `Array_3D_Spectrum` / `Array_3D_Image`, named band axis | **MISSING** |
| 1 Label (GeoTIFF) | `tifffile` + the four geometry tags | **MISSING** (dep now installed) |
| 2 Structural identity | size == offset + lines×samples×itemsize | **REUSE** — extend to 3-D and to TIFF strip/tile sums |
| 3 Window decode | `pds4.plan_tile_byte_range` / `decode_tile` | **REUSE** — extend to 3-D and TIFF |
| 4 Sanity gate | `siim.ingest.sanity.check_tile` | **REUSE** unchanged |
| 5 Geometry — line-scan | `siim.ingest.footprint.FrameCorners` | **REUSE** unchanged |
| 5 Geometry — map-projected | `siim.ingest.mapgrid.MapBlock` (RD-08 route) | **REUSE** — needs a GeoTIFF-tag constructor |
| 5 Geometry — IIRS | separate geometry file → bilinear (line,sample)↔(lat,lon) | **MISSING** |
| 6 Band policy | `siim.preprocessing.photometry.reflectance_domain_bands` | **REUSE** — wrap with the 0.8–2.0 µm selection |
| 7 Scale | `siim.preprocessing.degrade_to_gsd` (PSF-aware, FWHM 1.0) | **REUSE** unchanged |
| 8 Orientation | `siim.ingest.orientation.north_up_east_right` (E-037-aware) | **REUSE** unchanged |
| 9 Provenance | per-row product ID, SHA-256, window, bands, route, residual | **MISSING** — manifest + row schema |

**Also missing:** the P1–P6 runner, the manifest writer, and the S6 control
wiring.

**Dependency.** `tifffile>=2024.1` was declared as the `chandrayaan2` extra in
`pyproject.toml` on 2026-09-05 and was **not installed** in this environment —
the single hardest blocker, since TMC-2 carries P1, P3 and P5. Installed
2026-09-20 13:08 (**tifffile 2026.9.15**); the version and licence (BSD-3) go into the licence audit
and the frozen-requirements file in the same commit as the first RD-09
artefact.

---

## 2. New modules

Four new modules. Each is **new**, not an edit of a module a queued runner
imports — the rule that E-030 and the stage-discipline note exist to enforce.

### 2.1 `siim.ingest.geotiff` — the map-projected reader

**Purpose.** Turn a TMC-2 Level-2 GeoTIFF (ortho or DEM) into the same
`MapBlock` the Mini-RF and WAC products already flow through, so the rest of
the pipeline sees no new product type.

**Must do.**
- Open with `tifffile`, read tags **33922** (ModelTiepoint), **33550**
  (ModelPixelScale), **34264** (ModelTransformation) and **34735**
  (GeoKeyDirectory), and record **which were found**, verbatim, in the row.
- Build the pixel→(lon, lat) map from tiepoint + pixel scale, or from the 4×4
  transformation when it is the tag present. On the **1737.4 km sphere**.
- Support **equirectangular** and **polar stereographic** from the GeoKeys.
- Decode an arbitrary window by strip or tile, returning `array[line, sample]`
  (contract C2), without materialising the whole image.
- Report the **structural identity** of §4 step 2: the strip/tile byte counts
  must sum to the image size.

**Must refuse.**
- No tiepoint **and** no transformation → `not ingested`, step 1 named.
- A projection outside the two implemented → `not placed`, the GeoKey's own
  projection name quoted. It is **not** approximated with equirectangular.
- Strip/tile byte counts that do not sum → `not ingested`, step 2 named.

**Known-good test.** A synthetic GeoTIFF written by the test itself with known
tiepoint/scale: a round-trip of ten lon/lat points must return the originating
pixel to < 1e-9 px, and a decoded window must equal the array it was written
from, exactly.

### 2.2 `siim.ingest.pds4_cube` — the IIRS 3-D reader

**Purpose.** Read `Array_3D_Spectrum` / `Array_3D_Image` without touching the
2-D reader that every NAC result in the repository depends on.

**Must do.**
- Parse the three `Axis_Array` entries by **`sequence_number`** (1-based, as
  the 2-D reader already does), and identify the **band** axis by its
  `axis_name`, accepting the PDS4 spellings `Band`, `Wavelength`, `Spectral`.
- Record the axis order as found (BSQ / BIL / BIP follow from it) and compute
  each band's byte offset from that order — **never** assume BSQ.
- Extend structural identity to `offset + lines × samples × bands × itemsize`.
- Decode a **(window × band-subset)** by byte range, returning
  `array[band, line, sample]`.
- Read the per-band wavelengths from the label's spectral characteristics
  where present; where absent, say so — the band policy then cannot run and
  the product is `not placed` for matching.

**Must refuse.**
- A band axis it cannot name → raise with the axis names it did find.
- A data type outside `PDS4_DATA_TYPES` → raise with the type, as today. Any
  new type is an **explicit** addition to that table, in its own commit.

### 2.3 `siim.ingest.iirs_geometry` — the third placement route

**Purpose.** Place an IIRS cube from the separate geometry file that ships
with it, whose format Part 1 explicitly records as **not known in advance**.

**Must do.**
- **Detect** the format rather than assume it: try, in order, (a) a PDS4-
  labelled companion array of per-pixel lat/lon bands, (b) a delimited text
  table with a header naming line/sample/lat/lon columns, (c) a CSV without a
  header whose column count and monotonicity identify it. Record which branch
  fired.
- Fit a **bilinear** (line, sample) → (lat, lon) map per tile and record its
  **residual in metres** — the number that says whether a bilinear fit is even
  appropriate for this product.
- Expose the same interface the other two routes expose, so the runner does
  not branch on instrument.

**Must refuse.**
- No recognised branch → the cube is **`not placed`**, the file's first 200
  bytes recorded so the failure is diagnosable without the data in hand.
- A bilinear residual above **1 IIRS pixel (80 m)** → `not placed`, residual
  quoted. A worse fit is not silently accepted; S5's whole claim is measured
  in IIRS pixels.
- Longitude domain is **checked, not assumed**: if any fitted longitude leaves
  the product's own stated range, the 0–360 / ±180 alternative is tried and
  the choice is recorded. Neither working → `not placed`.

### 2.4 `scripts/run_real_data_09.py` — the runner

**Purpose.** Execute §5's P1–P6 in the frozen order against the frozen
criteria, writing one artefact row per attempt.

**Must do.**
- Enforce **S6 first**: re-run the `none` arm on the six recorded NAC edges and
  require **5365, 1656, 4, 4, 7, 3**. Any mismatch → **stop the stage**, write
  nothing further. This runs *before* any Chandrayaan-2 byte is read.
- Enforce **S0 per product**: steps 1–5, and a product that fails is recorded
  `not_ingested` with `failing_step` named, and is **excluded from S1–S5**.
- Run **P1, P2, P4, P5, P3, P6** — the order Part 1 §5 fixes and
  `NEXT_SESSION_PLAN.md` §2.4 repeats (most-likely-to-exist first).
- Use `siim.pipeline.register_pair_two_engines` with **B1** and **B4L**,
  LO-RANSAC affine, threshold 3.0, seed 0, rule `n_inliers <= 8`, and record
  engine agreement against the **3 px** floor (D-051).
- Check every pass against the geometry prediction with the floor
  `max(150 m, σ_C2) / GSD_reference` + 1.2 %, where **σ_C2 = 50 m** unless the
  label states its own accuracy. A pass that is INCONSISTENT is a **wrong
  pass** and is counted as one.
- **Refuse to overwrite** an existing artefact (integrity rule 4).
- Write rows carrying product ID, SHA-256, window, decimation, band indices,
  geometry route and residual (§4 step 9).

**Must refuse.**
- Any missing product → that pair is `no_data`, named, and the runner
  **continues** to the next pair. A missing OHRC does not stop the TMC-2 rung.

---

## 3. What happens at 14:00 — the run order

`T` is the moment the download finishes.

| When | Action | Gate before proceeding |
|---|---|---|
| T+0 | Place files **unrenamed** under `data/raw/chandrayaan2/<instrument>/`, every label and geometry file included | Nothing is opened yet |
| T+5 | Write `data/manifests/chandrayaan2_manifest.json`: path, size, SHA-256, PRADAN product ID, label fields | **Before any product is opened** (§3) |
| T+10 | Re-read `https://pradan.issdc.gov.in/ch2/ack.xhtml`; record any difference from S15 verbatim | Difference recorded, not summarised |
| T+15 | Run S6 control | **Stage stops if the six numbers do not reproduce** |
| T+20 | Run S0 ingestion on every product, one instrument at a time | Each product ingested or `not_ingested` with its step |
| T+35 | P1 (TMC-2 ortho → NAC at 5 m) | The pair most likely to exist and register |
| then | P2, P4, P5, P3, P6 | Each independently; `no_data` does not stop the rest |
| last | Part 2 written **exactly as the criteria read**, ledger rows and STAGE-INDEX in the same commit | Including every NOT MET |

**Demo beat 3 (320:1) is built if and only if P6 produced an artefact.**

---

## 4. Refusal table — what we do when the data surprises us

Part 1 §4 says each step refuses rather than guesses. Concretely, decided now,
before we can be tempted:

| Surprise | Response | Not allowed |
|---|---|---|
| OHRC swath misses both recorded windows | P2, P3, P6 report `no_data`; the stage says so | Moving the target ground point to where OHRC happens to look |
| TMC-2 L2 in a third projection | `not placed`; projection named | Approximating it as equirectangular |
| IIRS geometry file unreadable | Cube `not placed`; P4, P6 `no_data` | Placing it from the cube's own label corners |
| No OHRC/IIRS coverage in the box at all | Fallback region (≈69.4 S), **stated**, every criterion unchanged, high-incidence regime labelled | Presenting a fallback-region result as a Mare Serenitatis result |
| A product ingests but registers nothing | Reported as NOT MET | Tuning the matcher, changing the engine, re-scoping the rung |
| S6 does not reproduce | Stage stops; environment drift investigated first | Proceeding with "close enough" NAC numbers |

---

## 5. Tests required before the runner is trusted

Written against the **contract**, not against the data, so they can all exist
before 14:00:

1. `geotiff` — synthetic round-trip (§2.1), tiepoint-absent refusal,
   unsupported-projection refusal, strip-sum mismatch refusal.
2. `pds4_cube` — synthetic BSQ **and** BIL cubes decode identically through the
   sequence_number path; band-axis-absent raises; 3-D structural identity.
3. `iirs_geometry` — each of the three detection branches on synthetic files;
   residual-above-80 m refusal; longitude-domain switch.
4. `runner` — S6 stop-on-mismatch; `not_ingested` excluded from S1–S5;
   `no_data` does not halt later pairs; artefact overwrite refused.
5. **Regression** — the full suite (776 passed, 2 skipped at HEAD) must be
   unchanged by every module above, because none of them is imported by an
   existing runner.

---

## 6. Risks specific to today

- **Format surprise is the base case, not the exception.** Part 1 §3 records
  that the label schema, the IIRS geometry format, the GeoTIFF projection and
  the geolocation accuracy are all unknown. The plan's value is that every
  unknown has a named refusal instead of a guess.
- **Download size.** OHRC at 0.25 m is large; the manifest is written before
  anything is opened, so a partial download is detectable by SHA-256 rather
  than by a confusing decode.
- **Time.** If only TMC-2 arrives cleanly, **P1 alone** is a genuine
  Chandrayaan-2 ↔ LRO result and the first sentence in this repository in
  which "Chandrayaan-2" is a measurement. That is the minimum win condition
  and it is worth protecting over breadth.
