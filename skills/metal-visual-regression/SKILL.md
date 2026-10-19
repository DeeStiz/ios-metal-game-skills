---
name: metal-visual-regression
description: Set up deterministic visual regression testing for an iOS Metal game - an in-app capture mode, fixed camera shot lists per level, tile-based image comparison with failure signatures (fallback texture, terrain holes, blowout, flicker, z-fighting), and local baselines. Use when render changes keep breaking things nobody notices, before a renderer refactor, or when an agent needs to prove a visual change did not regress other levels.
license: MIT
---

# Visual regression for a Metal game

Goal: render regressions (fallback textures, z-fighting, flashing or missing geometry, terrain
holes) show up in a report instead of by eye.

## 1. Deterministic capture mode in the app

Enabled by an env var pointing at a shot list (`VRT_SHOTS=shots.json`). When active:

- Wait for player control + a warm-up (~8 s) so streaming and cooks settle.
- A **presentation-only review camera** visits each shot (position, yaw, pitch); gameplay is not
  touched.
- Copy the **drawable**, not a screenshot, so the HUD is excluded; separate optional HUD shots use
  a Simulator screenshot while the pose is held.
- Only copy once the presented snapshot has shown exactly that pose for N frames.
- Per shot: `static` frames at the pose (default 3), then `move` frames stepped along a tiny path
  (0.8 m right, 0.4 m forward, 2° yaw over 8 frames) for z-fight detection.
- **Freeze** the shader clock, dynamic resolution, and day cycle; disable enemies; the engine has
  no unseeded randomness. Repeated captures of one build then differ by ≤ ~4/255 per tile.
- Write PNGs at 0.5× drawable + `manifest.json`; log `VRT shot`, `VRT done`, `VRT timeout`.

Name frames `<shot>__s00.png…` and `<shot>__m00.png…` to use the bundled compare script.

## 2. Shot lists

One JSON per level: insertion view, overview, a few buildings, a roof, the tallest structure,
the horizon. Generate a starter list from level data, then **add a shot every time you fix a
visual bug** at that spot.

## 3. Compare

`scripts/vrt_compare.py BASELINE_DIR CANDIDATE_DIR --out REPORT` (numpy + Pillow):

- per 24 px tile: mean colour delta and SSIM; a tile is changed above delta 8 (or SSIM < 0.6 with
  delta > 4); a frame fails with ≥ 2 changed tiles;
- signatures: `fallback-texture` (textured → flat colour, or magenta), `sky-hole` (sky colour
  where the baseline had ground), `blowout` (near-white), `static-flicker` (frames at one pose
  differ), `z-fight` (b differs from a and c in the same direction while a ≈ c, beyond the
  baseline's own alternation);
- HTML report with baseline | candidate (changed tiles boxed) | diff, and `report.json`.

**Calibrate thresholds** by capturing the same build twice and comparing; set thresholds about
2× the worst tile noise.

## 4. Baselines

Keep them **out of git** (≈ 45 MB per level at half scale) in a gitignored folder shared by all
worktrees, per Simulator device model, with an `ACCEPTED` file naming the commit. Capture and
compare on the same device. `--update-baseline` is an explicit human/agent decision after an
intended change.

## 5. Playthrough gate

Optionally run each level's autopilot route (see `ios-game-simulator-automation`) with enemies on
and no shortcuts, and report the mission outcome, deaths and step timeouts next to the images.

## Evidence

VRT proves *pixels didn't change unexpectedly in the Simulator*. It says nothing about device frame
time, and Simulator rendering can differ slightly from device GPUs.
