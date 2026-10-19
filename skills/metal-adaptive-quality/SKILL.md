---
name: metal-adaptive-quality
description: Dynamic resolution, MetalFX temporal/spatial upscaling, device tiers and thermal handling for iOS Metal games. Use when frames look soft or blurry, MetalFX keeps falling back to spatial, resolution or frame rate drops without real GPU pressure, the game locks to 30 fps when warm, or when adding quality tiers per GPU family.
license: MIT
---

# Adaptive quality: dynamic resolution, MetalFX and heat

## Principle

**Quality follows measured GPU time, not the OS thermal label.** On a flagship device the OS
reported thermal state `fair` for an entire 3.5-minute session. An early ladder treated `fair` as
pressure: 0.60 render scale, low shaders and a 30 Hz cap — while completed GPU frames were
8.7 ms p50 / 10.9 ms p90, comfortably inside a 16.6 ms budget. Treat `fair` as normal play. Only
`serious`/`critical` and Low Power Mode engage a fixed safety path (e.g. 0.5 scale, simple
materials, 30 Hz).

## Device tiers

Pick a tier from `MTLDevice.supportsFamily(.appleN)`, not from model strings:

| Tier | GPU family | Target | Scale ladder (ceiling → floor) | Upscaler |
|---|---|---|---|---|
| flagship | Apple10+ | 60 | 0.85 … 0.67 | temporal |
| pro | Apple9 | 60 | 0.77 … 0.60 | temporal |
| base | Apple7/8 | 60 | 0.67 … 0.50 | temporal |
| entry | older | 30 | 0.60 … 0.50 | temporal if supported |

Numbers are a starting point that held up on device; tune per game.

## Dynamic resolution controller

Bucket per second: mean completed GPU ms, fraction of GPU frames over budget, presented misses.

- **Step down** after 3 s where mean GPU > 90% of budget, ≥ 25% of frames over budget, and misses
  in 2 of the 3 seconds. Seconds with misses but < 10% over-budget GPU frames are CPU/main-thread
  misses — resolution won't fix them, so don't shed.
- **Step up** after a quiet 6 s window whose GPU time *projected to the next step*,
  `ms × (next/current)²`, is < 80% of budget. Otherwise probe after 15 s quiet, doubling to 120 s
  after a failed probe.
- 3 s hold per change; 5 s grace after load.
- Only lower tiers may drop to 30 Hz at the scale floor. Flagship/pro hold 60: at a low cadence
  DVFS stretches frame timings and the headroom test never passes again.
- A separate sustained-heat governor (only while thermal is `fair`): if the per-second median GPU
  ≥ 75% of budget for 20 s, lower the ceiling one step; release at ≤ 57% for 30 s; 60 s minimum
  hold.
- Per-pass GPU "rungs" should shed non-resolution work first (shadow cadence/cascades, AO,
  volumetrics, far vegetation).

## MetalFX

- **Temporal needs jitter.** With jitter hard-coded to zero temporal recovers nothing over spatial.
  Use a Halton(2,3) sub-pixel jitter on the main pass projection and motion vectors (not
  shadows) and pass it to the scaler.
- **Prepare before adopting.** Build the temporal scaler and a same-size spatial companion on a
  worker; switch render scale only once both exist. Per-sample scale swaps caused visible stalls
  and native/soft frames while scalers built.
- **Motion vectors per drawn surface, not per owner.** One character model drew 35 surfaces; a
  128-owner capacity overflowed with 3–4 moving enemies and failed every combat frame. Use a
  per-surface capacity (768 worked) and derive a surface's previous transform from its owner's
  rigid motion when exact history is missing.
- **Reactive mask instead of failure.** Surfaces with no truthful motion (ring full, alpha on a
  moving owner, a rising flood whose vertices changed) go into the reactive mask. A frame with
  incomplete motion runs temporal with a history reset. Only persistent gaps (15 consecutive
  failures or > 25% sustained) latch to spatial, until 30 clean frames pass.
- **Mip bias.** The colour pass renders at render resolution and MetalFX reconstructs the
  drawable, so texture mips follow render-resolution derivatives and look soft. Pass
  `bias = clamp(log2(renderWidth / drawableWidth), -0.6, 0)` and sample with `bias(b)`; scale
  manual gradients by `exp2(bias)`. Native frames get 0.
- Lowering the temporal scale aggressively (0.77 → 0.67) caused blur bursts on mode flips; keep
  green scales equal across modes and keep the spatial companion resident.

## Log it

One line per second on device, e.g.:

```
dynres=s75/60fps/flagship/i2/d1/u0 miss=g0/e1/m0 stall=0 metalFX=temporal motion=r0/rx3 sharpness=mipBias=-0.42
```

so a play session can be diagnosed afterwards (see `ios-game-device-telemetry`).

## Checklist when "it looks blurry"

1. Is MetalFX actually temporal? (count temporal samples)
2. Is jitter non-zero and applied to both projection and motion?
3. Is mip bias applied?
4. Is the scale stuck at the floor because of a thermal label rather than GPU time?
5. Is distance haze washing things out at dusk? (see `metal-render-debugging`)
