---
name: metal-adaptive-quality
description: Dynamic resolution, MetalFX temporal/spatial upscaling, device tiers and thermal handling for iOS Metal games. Use when frames look soft or blurry, MetalFX keeps falling back to spatial, resolution or frame rate drops without real GPU pressure, the game locks to 30 fps when warm, or when adding quality tiers per GPU family.
license: MIT
---

# Adaptive quality: dynamic resolution, MetalFX and heat

## Principle

Combine measured GPU/CPU cost, sustained thermal trends, battery policy and user preferences.
Avoid drastic quality cuts based solely on one thermal-state sample, but do not ignore heat
because GPU frames are currently fast. CPU, display and other workloads also contribute.
Respond progressively to sustained pressure and promptly to serious/critical thermal conditions.
Use hysteresis and retest sustained sessions on each supported device class. Low Power Mode can
select a battery-saving policy; it is not proof of GPU overload.

## Device tiers

Pick a tier from `MTLDevice.supportsFamily(.appleN)`, not from model strings:

| Tier | GPU family | Target | Scale ladder (ceiling → floor) | Upscaler |
|---|---|---|---|---|
| flagship | Apple10+ | 60 | 0.85 … 0.67 | temporal |
| pro | Apple9 | 60 | 0.77 … 0.60 | temporal |
| base | Apple7/8 | 60 | 0.67 … 0.50 | temporal |
| entry | older | 30 | 0.60 … 0.50 | temporal if supported |

These are illustrative initial settings, not verified budgets for every device in a family.
Query scaler support and supported input-scale ranges, and account for memory and CPU limits.
Select a supported fallback when a feature or scale is unavailable.

## Dynamic resolution controller

Bucket per second: completed GPU ms, fraction over budget, presented misses, CPU cost and
thermal state. The following windows and percentages are tuning examples, not platform rules.

- **Step down** after 3 s where mean GPU > 90% of budget, ≥ 25% of frames over budget, and misses
  in 2 of the 3 seconds. Misses with low completed-GPU cost suggest CPU/scheduling pressure;
  correlate encode/callback timing before assigning a cause. Resolution reduction is unlikely
  to help a confirmed CPU bottleneck.
- **Step up** after a quiet 6 s window whose GPU time *projected to the next step*,
  `ms × (next/current)²`, is < 80% of budget. Otherwise probe after 15 s quiet, doubling to 120 s
  after a failed probe. The squared-scale estimate models pixel-proportional cost only; fixed
  geometry/pass overhead requires measured probes and can make that estimate optimistic.
- 3 s hold per change; 5 s grace after load.
- Allow a measured cadence reduction on any tier when sustained pressure requires it. Account
  for DVFS when estimating headroom after a cadence change; use bounded probes and cooldowns
  rather than assuming a slower GPU clock means the original workload cannot recover.
- Example sustained-load hysteresis to calibrate alongside thermal trends: if the per-second median GPU
  ≥ 75% of budget for 20 s, lower the ceiling one step; release at ≤ 57% for 30 s; 60 s minimum
  hold.
- Per-pass GPU "rungs" should shed non-resolution work first (shadow cadence/cascades, AO,
  volumetrics, far vegetation).

## MetalFX

- **Define temporal inputs precisely.** Temporal MetalFX requires iOS 16+ and a supported
  device. Check `supportsDevice`, input-scale limits and descriptor/texture compatibility.
  Jitter the color projection (for example Halton(2,3)); provide offsets in input-pixel units.
  Supply current-to-previous motion: at scale 1, an object moving 10 pixels right needs -10
  horizontal motion. Set motionVectorScaleX/Y to convert your units to input pixels.
  Use unjittered transforms for vectors or remove the jitter delta. On iOS 27+, vectors that
  include jitter may instead use `isJitteredMotionVectorsEnabled = true`; its default is false.
  Do not add jitter twice. Match texture Y orientation and `isDepthReversed` to the renderer.
  Validate a static camera, camera pan, moving/deforming objects and disocclusion separately.

- **Prepare before adopting.** Build the temporal scaler and a same-size spatial companion on a
  worker; switch render scale only once both exist. Per-sample scale swaps caused visible stalls
  and native/soft frames while scalers built.
- **Motion vectors per drawn surface, not per owner.** One character model drew 35 surfaces; a
  fixed owner-sized capacity overflowed when models contained many surfaces. Size or grow
  buffers from actual draw counts and enforce bounds. Rigid owner motion is only a valid
  fallback for rigid surfaces; skinning and deformation need their own previous geometry.
- **Use regional history rejection where supported.** Reactive-mask descriptor configuration
  requires iOS 17.4+. Enable it with the correct format and provide values in [0,1]; 1 rejects
  history at that pixel. Use it for transient unreliable motion/transparency rather than
  resetting the whole frame continuously. Reset full history on camera cuts, scene changes or
  incompatible history resources. If motion remains invalid, use a supported spatial/native
  fallback and log the cause. Calibrate recovery windows rather than copying a fixed count.

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
2. Are projection jitter, motion-vector convention and scaler offsets consistent?
3. Is mip bias applied?
4. Is the scale stuck at the floor because of a thermal label rather than GPU time?
5. Is distance haze washing things out at dusk? (see `metal-render-debugging`)

Sources: [temporal scaler descriptor](https://developer.apple.com/documentation/metalfx/mtlfxtemporalscalerdescriptor), [jittered vectors](https://developer.apple.com/documentation/metalfx/mtlfxtemporalscalerdescriptor/isjitteredmotionvectorsenabled), [reactive mask](https://developer.apple.com/documentation/metalfx/mtlfxtemporalscalerbase/reactivemasktexture). Verify availability against the deployment SDK.
