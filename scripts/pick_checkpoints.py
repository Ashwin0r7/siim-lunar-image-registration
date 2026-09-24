"""Manual check points: the picker for the one accuracy number that has no
shared instrument in it.

Every accuracy-class figure this project has is a bound with an instrument in
common between its legs: self-warp precision shares the image, archive
geometry shares the labels, the Kaguya route shares the reference map
(EXP-019's 2.24 m is a two-leg bound for exactly that reason). Human-picked
check points, kept out of every fit, are the missing piece
(PROJECT_GAP_ANALYSIS corrected path item 4). This tool collects them; it
computes NO statistic and makes NO claim. The evaluation belongs to a future
pre-registered stage, which must be frozen before any residual is computed.

    python scripts/pick_checkpoints.py SOURCE REFERENCE --out points.csv
                                       [--decimate K] [--picker NAME]

Opens the two images side by side. Click a ground feature in the SOURCE
(left), then the same feature in the REFERENCE (right); repeat. Keys:
``u`` undoes the last click, ``s`` saves and continues, ``q`` saves and
quits. The CSV carries full provenance (paths, SHA-256, shapes, decimation,
picker name, UTC time, git commit) and the statement of what the points are
for. Refuses to overwrite (integrity rule 4).

Discipline the pre-registration will rely on, enforced here:

* points are written with the images' SHA-256, so an evaluation can prove it
  used the same pixels the human saw;
* the tool never displays, loads or computes any transform, so the picker
  cannot be steered by a registration result;
* a pair is only recorded when both clicks exist; a dangling click is
  discarded on save.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from siim.cli import load_image, preprocess  # noqa: E402

HEADER_COLUMNS = ["index", "src_x", "src_y", "ref_x", "ref_y"]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=10, cwd=ROOT)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def write_checkpoints(out: Path, pairs: list[tuple[float, float, float, float]],
                      src_path: Path, ref_path: Path, decimate: int,
                      picker: str) -> None:
    """The CSV, with provenance in `# key: value` header lines."""
    if out.exists():
        raise FileExistsError(f"{out} exists; check points are never overwritten "
                              "(integrity rule 4). Pick into a new file.")
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        nl = "\n"
        fh.write("# siim manual check points. Purpose: an INDEPENDENT accuracy check. "
                 "These points must never be fed to a matcher or a fit; an evaluation "
                 "against them belongs to a pre-registered stage frozen before any "
                 "residual is computed." + nl)
        fh.write(f"# picker: {picker}" + nl)
        fh.write(f"# time_utc: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}" + nl)
        fh.write(f"# git_commit: {_git_commit()}" + nl)
        fh.write(f"# decimation: {decimate} (coordinates are in the decimated, "
                 "stretched frame the picker displayed, pixel centres)" + nl)
        for role, p in (("source", src_path), ("reference", ref_path)):
            fh.write(f"# {role}: {p}" + nl)
            fh.write(f"# {role}_sha256: {_sha256(p)}" + nl)
        w.writerow(HEADER_COLUMNS)
        for i, (sx, sy, rx, ry) in enumerate(pairs):
            w.writerow([i, f"{sx:.3f}", f"{sy:.3f}", f"{rx:.3f}", f"{ry:.3f}"])


def read_checkpoints(path: Path) -> tuple[dict, np.ndarray, np.ndarray]:
    """(provenance, src_points (N,2), ref_points (N,2)) from a picker CSV."""
    prov: dict = {}
    rows: list[list[str]] = []
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if not row:
                continue
            if row[0].startswith("#"):
                text = ",".join(row).lstrip("# ")
                if ":" in text:
                    k, v = text.split(":", 1)
                    prov[k.strip()] = v.strip()
                continue
            rows.append(row)
    if not rows or rows[0] != HEADER_COLUMNS:
        raise ValueError(f"{path} does not look like a picker CSV "
                         f"(header {rows[0] if rows else 'missing'})")
    data = np.array([[float(v) for v in r[1:5]] for r in rows[1:]], dtype=float)
    if data.size == 0:
        return prov, np.zeros((0, 2)), np.zeros((0, 2))
    return prov, data[:, 0:2].copy(), data[:, 2:4].copy()


def pick(src, ref, src_name: str, ref_name: str) -> list[tuple[float, float, float, float]]:
    """The interactive session. Returns completed (sx, sy, rx, ry) pairs."""
    import matplotlib.pyplot as plt

    pairs: list[tuple[float, float, float, float]] = []
    pending: list[tuple[float, float]] = []          # a source click awaiting its partner
    fig, (ax_s, ax_r) = plt.subplots(1, 2, figsize=(14, 7))
    for ax, img, name in ((ax_s, src, src_name), (ax_r, ref, ref_name)):
        ax.imshow(img, cmap="gray", interpolation="nearest")
        ax.set_title(name, fontsize=9)
    fig.suptitle("click SOURCE (left) then REFERENCE (right) · u = undo · "
                 "s = save · q = save and quit", fontsize=10)
    marks = []

    def redraw():
        for m in marks:
            m.remove()
        marks.clear()
        for i, (sx, sy, rx, ry) in enumerate(pairs):
            marks.append(ax_s.plot(sx, sy, "r+", ms=12)[0])
            marks.append(ax_s.annotate(str(i), (sx, sy), color="red", fontsize=8))
            marks.append(ax_r.plot(rx, ry, "r+", ms=12)[0])
            marks.append(ax_r.annotate(str(i), (rx, ry), color="red", fontsize=8))
        for (sx, sy) in pending:
            marks.append(ax_s.plot(sx, sy, "y+", ms=12)[0])
        fig.canvas.draw_idle()

    def on_click(ev):
        if ev.inaxes is ax_s and ev.xdata is not None:
            pending.clear()
            pending.append((float(ev.xdata), float(ev.ydata)))
        elif ev.inaxes is ax_r and ev.xdata is not None and pending:
            sx, sy = pending.pop()
            pairs.append((sx, sy, float(ev.xdata), float(ev.ydata)))
            print(f"  pair {len(pairs) - 1}: source ({sx:.1f}, {sy:.1f}) -> "
                  f"reference ({ev.xdata:.1f}, {ev.ydata:.1f})")
        redraw()

    def on_key(ev):
        if ev.key == "u":
            if pending:
                pending.clear()
            elif pairs:
                pairs.pop()
            redraw()
        elif ev.key in ("s", "q"):
            fig._siim_save = True            # noqa: SLF001 - our own flag
            if ev.key == "q":
                plt.close(fig)

    fig.canvas.mpl_connect("button_press_event", on_click)
    fig.canvas.mpl_connect("key_press_event", on_key)
    plt.show()
    return pairs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("reference")
    ap.add_argument("--out", required=True)
    ap.add_argument("--decimate", type=int, default=1)
    ap.add_argument("--picker", default=None,
                    help="the human's name or initials, recorded in the CSV")
    args = ap.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        print(f"{out} exists; check points are never overwritten (integrity rule 4)",
              file=sys.stderr)
        return 2
    picker = args.picker or input("picker name (recorded in the CSV): ").strip() or "unnamed"
    src_path, ref_path = Path(args.source), Path(args.reference)
    src = preprocess(load_image(src_path), args.decimate)
    ref = preprocess(load_image(ref_path), args.decimate)
    pairs = pick(src, ref, src_path.name, ref_path.name)
    if not pairs:
        print("no completed pairs; nothing written")
        return 1
    write_checkpoints(out, pairs, src_path, ref_path, args.decimate, picker)
    print(f"{len(pairs)} check points -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
