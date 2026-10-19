---
name: metal-visual-regression
description: Set up deterministic visual regression testing for an iOS Metal game - an in-app capture mode, fixed camera shot lists per level, tile-based image comparison with failure signatures (fallback texture, terrain holes, blowout, flicker, z-fighting), and local baselines. Use when render changes keep breaking things nobody notices, before a renderer refactor, or when an agent needs to prove a visual change did not regress other levels.
license: MIT
---

# Visual regression for a Metal game

Goal: flag possible visual regressions for review using deterministic captures. Pixel differences
and signature heuristics are evidence, not proof of a specific root cause. Requires Python 3.14,
NumPy and Pillow for comparison; the app-side capture mode is an integration you must implement.

## 1. Deterministic capture mode in the app

Enabled by an env var pointing at a shot list (`VRT_SHOTS=shots.json`). When active:

- Wait for player control + a warm-up (~8 s) so streaming and cooks settle.
- A **presentation-only review camera** visits each shot (position, yaw, pitch); gameplay is not
  touched.
- Capture the color target at the intended stage. Drawable capture excludes only HUD composed
  outside that drawable; Metal-rendered HUD needs a separate pre-HUD target or capture mode.
  Use a blit/readback path with appropriate texture usage and GPU completion synchronization.
  Separate optional system/UI shots can use Simulator screenshots while the pose is held.
- Reset temporal history after camera cuts, then warm up a fixed number of frames using the
  same jitter sequence and inputs. Copy only when the settled pose/history is ready; record
  capture settings, build/content identity and expected frame names in a manifest.
- Per shot: `static` frames at the pose (default 3), then `move` frames stepped along a tiny path
  (0.8 m right, 0.4 m forward, 2° yaw over 8 frames) for z-fight detection.
- **Freeze** the shader clock, dynamic resolution, and day cycle; disable enemies; the engine has
  no unseeded randomness. Repeated captures of one build then differ by ≤ ~4/255 per tile.
- Choose capture resolution for the defect: downsampling can hide one-pixel gaps and flicker.
  Use native resolution for those shots; reduced resolution can speed broad scene comparisons.
  Write PNGs plus `manifest.json`; log `VRT shot`, `VRT done`, `VRT timeout`.

Name frames `<shot>__s00.png…` and `<shot>__m00.png…` to use the bundled compare script.

## 2. Shot lists

One JSON per level: insertion view, overview, a few buildings, a roof, the tallest structure,
the horizon. Generate a starter list from level data, then **add a shot every time you fix a
visual bug** at that spot.

## 3. Compare

From the installed skill folder, run
`python3.14 scripts/vrt_compare.py BASELINE_DIR CANDIDATE_DIR --out REPORT` after installing
NumPy and Pillow in a Python 3.14 virtual environment:

- requires existing, distinct directories and matching nonempty frame sets; missing/new frames
  fail and need explicit review. Sequences start at 00 without gaps, with at least 2 static or
  3 moving frames and matching dimensions. Corrupt images fail with a diagnostic;
- per 24 px tile (including partial edge tiles): mean colour delta and SSIM; a tile is changed above delta 8 (or SSIM < 0.6 with
  delta > 4); a frame fails with ≥ 2 changed tiles (or the only tile for a tiny image);
- signatures: `fallback-texture` (textured → flat colour, or magenta), `sky-hole` (sky colour
  where the baseline had ground), `blowout` (near-white), `static-flicker` (frames at one pose
  differ), `z-fight` (b differs from a and c in the same direction while a ≈ c, beyond the
  baseline's own alternation);
- HTML report with baseline | candidate (changed tiles boxed) | diff, and `report.json`.

**Calibrate thresholds** by capturing the same build twice and comparing; set thresholds about
2× the worst tile noise.

## 4. Baselines

Keep them **out of git** (≈ 45 MB per level at half scale) in a gitignored folder shared by all
worktrees, per device/OS and render configuration, with an `ACCEPTED` file naming the commit.
Capture and compare under matching conditions. The comparator never updates baselines. After
review, archive the old baseline and copy the accepted capture set explicitly. Keep a shot
manifest so deleting the same shot from both directories cannot silently reduce coverage.

## 5. Playthrough gate

Optionally run each level's autopilot route (see `ios-game-simulator-automation`) with enemies on
and no shortcuts, and report the mission outcome, deaths and step timeouts next to the images.

## Evidence

A passing comparison means the supplied captures stayed within configured thresholds. It cannot
prove full visual correctness, coverage of uncaptured scenes, or device frame time. Review flagged
images and representative device captures; Simulator rendering can differ from physical GPUs.
