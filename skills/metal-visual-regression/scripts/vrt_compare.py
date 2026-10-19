#!/usr/bin/env python3
"""Tile-based visual regression compare for game frame captures.

usage:
  python3 vrt_compare.py BASELINE_DIR CANDIDATE_DIR [--out REPORT_DIR] [--tile 24]

Both directories hold PNGs with matching relative names. Frames of one shot can form sequences:
  <shot>__s00.png, <shot>__s01.png, ...   frames held at one fixed pose (nothing should change)
  <shot>__m00.png, <shot>__m01.png, ...   frames along a tiny camera path (used for z-fight detection)
Any other PNG is a single frame.

Each candidate frame is compared to its baseline per tile (mean colour delta + SSIM) and checked for
failure signatures:
  fallback-texture  textured tiles that became one flat colour (missing material), or magenta
  sky-hole          sky-coloured tiles where the baseline had ground or geometry
  blowout           tiles that turned near-white
  static-flicker    frames at one fixed pose that differ from each other
  z-fight           frame b departs from both a and c in the same direction while a ~ c, beyond the
                    baseline's own alternation
Writes REPORT_DIR/report.json and REPORT_DIR/index.html (baseline | candidate | diff, changed tiles
boxed). Exit status 1 when any frame fails.

Calibrate the thresholds below from two captures of the SAME build: a deterministic capture mode
should make them nearly identical (the reference project measured <= 4.3/255 per tile).
Requires numpy and Pillow.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("vrt_compare.py needs numpy and Pillow: python3 -m pip install numpy pillow")

TILE = 24
SSIM_TILE_FAIL = 0.6         # a tile this dissimilar with a mean |delta| above 4 ...
DELTA_TILE_FAIL = 8.0        # ... or any tile whose mean |colour delta| (0-255) is this large is changed
CHANGED_TILES_FAIL = 2       # changed tiles that fail a frame
FLAT_STD = 1.0               # luma std of a "flat" tile
TEXTURED_STD = 4.0           # luma std of a textured baseline tile
STATIC_DELTA = 3.0           # mean |delta| of a tile between frames at one fixed pose
ALTERNATION_FRACTION = 0.10  # fraction of a tile's pixels that alternate a->b->c ...
ALTERNATION_MARGIN = 0.06    # ... beyond the baseline's own alternation
SIGNATURE_MIN_TILES = 2

SEQ = re.compile(r"^(?P<shot>.+)__(?P<kind>[sm])(?P<index>\d+)\.png$")


def load(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.float32)


def luma(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def box(a: np.ndarray, r: int = 3) -> np.ndarray:
    p = np.pad(a, r + 1, mode="edge")
    s = p.cumsum(0).cumsum(1)
    k = 2 * r + 1
    out = s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k]
    return out[: a.shape[0], : a.shape[1]] / (k * k)


def ssim_map(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    ma, mb = box(a), box(b)
    va, vb = box(a * a) - ma * ma, box(b * b) - mb * mb
    cov = box(a * b) - ma * mb
    return ((2 * ma * mb + c1) * (2 * cov + c2)) / ((ma * ma + mb * mb + c1) * (va + vb + c2))


def tiles(a: np.ndarray, reduce: str = "mean") -> np.ndarray:
    th, tw = a.shape[0] // TILE, a.shape[1] // TILE
    t = a[: th * TILE, : tw * TILE].reshape(th, TILE, tw, TILE, *a.shape[2:])
    return t.mean(axis=(1, 3)) if reduce == "mean" else t.std(axis=(1, 3))


def sky_reference(std_t: np.ndarray, mean_t: np.ndarray):
    rows = max(1, std_t.shape[0] // 5)
    smooth = std_t[:rows] < 3.0
    if smooth.sum() < max(3, smooth.size // 4):
        return None
    colour = np.median(mean_t[:rows][smooth], axis=0)
    return None if colour.mean() < 60 else colour


def sky_like(mean_t, std_t, sky) -> np.ndarray:
    if sky is None:
        return np.zeros(std_t.shape, bool)
    return (std_t < 3.0) & (np.abs(mean_t - sky).max(axis=-1) < 14)


def analyse(base: np.ndarray, cand: np.ndarray) -> dict:
    if base.shape != cand.shape:
        return {"status": "fail", "reason": f"size {cand.shape[1]}x{cand.shape[0]} != "
                                            f"{base.shape[1]}x{base.shape[0]}", "signatures": {}}
    lb, lc = luma(base), luma(cand)
    ssim_t = tiles(ssim_map(lb, lc))
    delta_t = tiles(np.abs(cand - base).mean(axis=-1))
    changed = (delta_t > DELTA_TILE_FAIL) | ((ssim_t < SSIM_TILE_FAIL) & (delta_t > 4.0))
    std_b, std_c = tiles(lb, "std"), tiles(lc, "std")
    mean_b, mean_c = tiles(base), tiles(cand)
    sky = sky_reference(std_b, mean_b)
    if sky is None:
        sky = sky_reference(std_c, mean_c)
    sky_b, sky_c = sky_like(mean_b, std_b, sky), sky_like(mean_c, std_c, sky)
    r, g, b = cand[..., 0], cand[..., 1], cand[..., 2]
    magenta = tiles(((r > 190) & (b > 190) & (g < 90)).astype(np.float32)) > 0.5
    signatures = {
        "fallback-texture": ((std_c < FLAT_STD) & (std_b > TEXTURED_STD) & ~sky_c & changed) | magenta,
        "sky-hole": sky_c & ~sky_b & changed,
        "blowout": (luma(mean_c) > 240) & (luma(mean_b) < 215) & changed,
    }
    counts = {k: int(v.sum()) for k, v in signatures.items()}
    flagged = {k: c for k, c in counts.items() if c >= SIGNATURE_MIN_TILES}
    status = "fail" if int(changed.sum()) >= CHANGED_TILES_FAIL or flagged else "pass"
    return {"status": status, "ssimMin": float(ssim_t.min()), "deltaMean": float(delta_t.mean()),
            "changedTiles": int(changed.sum()), "signatures": flagged, "_changed": changed}


def alternation(a, b, c, threshold: float = 18.0) -> np.ndarray:
    la, lb, lc = luma(a), luma(b), luma(c)
    d1, d2 = lb - la, lb - lc
    alt = (np.abs(d1) > threshold) & (np.abs(d2) > threshold) & (np.sign(d1) == np.sign(d2)) \
        & (np.abs(la - lc) < threshold * 0.5)
    return tiles(alt.astype(np.float32))


def temporal(frames: list, kind: str):
    if kind == "s" and len(frames) >= 2:
        return np.max([tiles(np.abs(frames[i + 1] - frames[i]).mean(axis=-1))
                       for i in range(len(frames) - 1)], axis=0)
    if kind == "m" and len(frames) >= 3:
        return np.max([alternation(frames[i - 1], frames[i], frames[i + 1])
                       for i in range(1, len(frames) - 1)], axis=0)
    return None


def save_view(img: np.ndarray, path: Path, mask=None, width: int = 520) -> str:
    image = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    if mask is not None and mask.any():
        draw = ImageDraw.Draw(image)
        for ty, tx in zip(*np.nonzero(mask)):
            draw.rectangle([tx * TILE, ty * TILE, tx * TILE + TILE - 1, ty * TILE + TILE - 1],
                           outline=(255, 0, 255), width=2)
    if image.width > width:
        image = image.resize((width, round(image.height * width / image.width)), Image.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path.name


def diff_view(base, cand) -> np.ndarray:
    d = np.clip(np.abs(cand - base).mean(axis=-1) * 4, 0, 255)
    return np.stack([d, d * 0.35, 255 - d], -1) * (d[..., None] > 6) + luma(cand)[..., None] * 0.25 * (d[..., None] <= 6)


def main() -> int:
    global TILE
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("baseline", type=Path)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--tile", type=int, default=TILE)
    args = ap.parse_args()
    TILE = args.tile
    out = args.out or args.candidate / "vrt-report"
    out.mkdir(parents=True, exist_ok=True)

    results, rows, failed = [], [], 0
    sequences: dict[tuple, list] = defaultdict(list)
    for cand_path in sorted(args.candidate.rglob("*.png")):
        if out in cand_path.parents:
            continue
        rel = cand_path.relative_to(args.candidate)
        base_path = args.baseline / rel
        m = SEQ.match(cand_path.name)
        if m:
            sequences[(str(rel.parent), m["shot"], m["kind"])].append((int(m["index"]), cand_path, base_path))
        if not base_path.exists():
            results.append({"frame": str(rel), "status": "new"})
            continue
        base, cand = load(base_path), load(cand_path)
        r = analyse(base, cand)
        changed = r.pop("_changed", None)
        r["frame"] = str(rel)
        results.append(r)
        if r["status"] == "fail":
            failed += 1
            stem = re.sub(r"[^A-Za-z0-9_.-]", "_", str(rel))
            views = [save_view(base, out / f"{stem}.base.png"),
                     save_view(cand, out / f"{stem}.cand.png", changed),
                     save_view(diff_view(base, cand) if base.shape == cand.shape else cand, out / f"{stem}.diff.png")]
            label = html.escape(f"{rel}: {r.get('reason') or r['signatures'] or str(r['changedTiles']) + ' changed tiles'}")
            rows.append(f"<h3>{label}</h3><div>" + "".join(f'<img src="{v}">' for v in views) + "</div>")

    for (parent, shot, kind), frames in sorted(sequences.items()):
        frames.sort()
        cand_frames = [load(p) for _, p, _ in frames]
        metric = temporal(cand_frames, kind)
        if metric is None:
            continue
        if kind == "s":
            bad = metric > STATIC_DELTA
            name = "static-flicker"
        else:
            base_frames = [load(b) for _, _, b in frames if b.exists()]
            base_metric = temporal(base_frames, "m") if len(base_frames) == len(frames) else None
            floor = base_metric + ALTERNATION_MARGIN if base_metric is not None else ALTERNATION_FRACTION
            bad = (metric > ALTERNATION_FRACTION) & (metric > floor)
            name = "z-fight"
        if int(bad.sum()) >= SIGNATURE_MIN_TILES:
            failed += 1
            label = shot if parent == "." else f"{parent}/{shot}"
            entry = f"{label} {name}: {int(bad.sum())} tiles"
            results.append({"frame": label, "status": "fail", "signatures": {name: int(bad.sum())}})
            view = save_view(cand_frames[len(cand_frames) // 2], out / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', shot)}.{name}.png", bad)
            rows.append(f"<h3>{html.escape(entry)}</h3><div><img src='{view}'></div>")

    (out / "report.json").write_text(json.dumps({"failed": failed, "frames": results}, indent=2))
    summary = f"{failed} failing of {len(results)} checks"
    (out / "index.html").write_text(
        "<!doctype html><meta charset=utf-8><title>VRT report</title>"
        "<style>body{font:14px system-ui;margin:16px;background:#111;color:#eee}img{max-width:32%;margin:2px}</style>"
        f"<h1>VRT: {summary}</h1>" + ("".join(rows) or "<p>All frames pass.</p>"))
    print(f"{summary}; report: {out / 'index.html'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
