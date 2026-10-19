---
name: metal-frame-pacing
description: Drive an iOS Metal game with CAMetalDisplayLink, choose frame-rate ranges that actually present, keep a fixed-step simulation decoupled from presentation, and make frame starvation impossible to miss. Use when frames stutter or lock to 30 fps, when "only the HUD moves" or the 3D view freezes, when adding a worker-prepared render plan, or when setting up ProMotion / 120 Hz support.
license: MIT
---

# Metal frame pacing and presentation liveness

## Display link setup

- Use `CAMetalDisplayLink` (iOS 17+) on a `UIView` that owns the `CAMetalLayer`. Render to the
  drawable it hands you and use its `targetPresentationTimestamp`; don't call
  `nextDrawable()` yourself on that path.
- Default to an adaptive **30–60 Hz** range; offer up to 120 Hz as an opt-in "Performance mode"
  (needs `CADisableMinimumFrameDurationOnPhone = YES` in Info.plist for >60 Hz on iPhone).
- A frame-rate range is a preference, not a guarantee. For a desired fixed cadence, request
  a supported fixed range and measure actual presents. A range such as 30–40 can settle at 30;
  supported rates and power/thermal policy vary by device and display.
- Preserve the chosen simulation interval (for example 60 Hz) when presentation quality changes.
  Keep explicit time-scale, pause and overload policies separate from adaptive render cadence.

## Fixed-step scheduling

Keep the simulation clock independent of the display link. A dedicated scheduler owns the
fixed-step accumulator; display callbacks only read settled snapshots and interpolate.
Alternatively, a display-driven accumulator may run multiple ticks at low presentation rates.
For example, 60 Hz simulation at 30 Hz presentation requires two ticks per callback.

Pseudocode for the simulation scheduler (choose the cap for the workload):

```text
elapsed = monotonicNow - lastPoll
accumulator += elapsed
while accumulator >= step and ticksThisPoll < maxCatchUpTicks:
    consumeInputsForTick(tick)
    authority.step(step)
    accumulator -= step
    publishSettledSnapshot(tick)
if accumulator >= step:
    applyExplicitOverloadPolicy()  // log any discarded time or slowed simulation
```

Do not equate a fixed integration interval with guaranteed wall-clock progress under overload.
Reset the wall-clock origin after suspend/resume. Test the same tick-indexed input trace with
30/60/120 Hz presentation, stalls, and resume; compare tick counts and state at equal simulated
elapsed time. Lockstep games need a shared overload policy, not local silent time dropping.

Interpolate using snapshot timestamps. When simulation lags, clamp interpolation or use a
bounded prediction policy; never let rendering mutate authoritative state.

## Worker-prepared render plans: the freeze bug

A common optimisation is to build the scene draw plan (culling, sorting, batching) on a worker and
have `draw` accept it only if it is still fresh. **Freshness checks are a liveness hazard.**

Real incident: levels with a moving time of day updated the 3D view at ~0.5 fps on device while
the HUD stayed smooth. The plan's configuration signature hashed the *exact bytes* of the sun
direction. The sun moved every tick, so the plan built for frame N never matched frame N+1 and
~99% of draws were refused (6 live frames in 583 callbacks).

Rules:

1. **Never put a continuously changing float into an equality signature.** Fence it by
   tolerance (sun within 1.1°, camera within N cm) and patch per-frame uniforms at encode time.
2. **Name every refusal.** `draw` returns a reason (`plan-rejected:configuration-signature`,
   `plan-rejected:resource-revision`, `plan-worker-pending`, `depth-texture-unavailable`) and
   you count them (`notDrawn=reason:count`).
3. **Bound starvation.** After a measured refusal threshold, use a safe last-good plan, a
   simplified recovery frame, or a bounded synchronous rebuild. Never reuse resources from a
   retired generation. Synchronous work can itself hitch, so measure and log recovery cost.
4. **Keep a debug knob that forces rejection** so the fallback path is exercised.

## Liveness counters and watchdog

Per renderer, count: display-link callbacks, live frames submitted, live frames completed,
command-buffer successes/failures (log the first failures with status, error domain, code),
recovery frames and their reason.

Example starting thresholds, to calibrate for the app: a 0.5 s watchdog on the Metal view, active only when the resource gate is open, the window is
attached and the app is active:

- no live frame completed for 1.5 s, **or** 3 failed command buffers in a row, **or** live
  frames < 5% of callbacks over 2 s → restart the display link;
- still starving → recreate the renderer once;
- still starving → log `presentationWatchdog action=reportUnresolved` with all counters.

Put the policy (thresholds, decisions) in the engine package as a pure type so it is unit
tested; the view only feeds it numbers.

Log a render line at fixed points after each load (`t=2s, 6s, 15s`):
`LEVEL_SWITCH render phase=t6s liveCompleted=… callbacks=… failed=… recoveryFrames=… notDrawn=…`.
A healthy run shows `liveCompleted` rising with `callbacks`.

## Other pacing lessons

- Attribute every presented miss to the latest completed frame: GPU over budget, encode (CPU)
  late, or main thread busy (callback arrived > 1.5 frames late). Different fixes for each.
- Simulator captures can reproduce some logic failures, but cannot establish device pacing.
  Log callbacks, submits, completions and rejection reasons on the physical device, especially
  when the symptom does not reproduce in the Simulator.
- Visual-only springs (view-model kick, sway) integrate on the renderer's own frame delta so they
  don't step at authority rate.

Sources: [CAMetalDisplayLink](https://developer.apple.com/documentation/quartzcore/cametaldisplaylink), [CAFrameRateRange](https://developer.apple.com/documentation/quartzcore/caframeraterange). Example watchdog thresholds are policy choices, not API guarantees.
