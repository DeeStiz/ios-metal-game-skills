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
- **A capped cadence must be requested as a fixed range** (`cap...cap`). Measured on a current flagship
  iPhone: a `30...40` request presented a locked 30 fps, not 40. Ranges with a low minimum let
  the system pick the minimum when it is unsure.
- Gameplay authority stays at 60 Hz regardless. Thermal and quality changes alter presentation,
  never simulation cadence.

## Fixed-step poll

```swift
func onDisplayLink(now: CFTimeInterval) {
    let due = clock.dueSteps(now)          // 0 or 1, never more
    if due == 1 { authority.step() }       // missed intervals are rebased, not replayed
    renderer.draw(interpolating: mailbox.previous, mailbox.current, alpha: clock.alpha(now))
}
```

Run the authority on its own queue when its worst tick can exceed a frame; the renderer keeps
presenting the last snapshot while it catches up.

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
3. **Bound the starvation.** After 3 consecutive refusals, build one plan synchronously for the
   current request. Log `syncFallbacks=`. No future stale-plan class can freeze the picture.
4. **Keep a debug knob that forces rejection** so the fallback path is exercised.

## Liveness counters and watchdog

Per renderer, count: display-link callbacks, live frames submitted, live frames completed,
command-buffer successes/failures (log the first failures with status, error domain, code),
recovery frames and their reason.

A 0.5 s watchdog on the Metal view, active only when the resource gate is open, the window is
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
- The Simulator can never reproduce device-only starvation or pacing; the freeze above did not
  reproduce until a specific level with a moving sun was used. Make the device log tell you
  instead (see `ios-game-device-telemetry`).
- Visual-only springs (view-model kick, sway) integrate on the renderer's own frame delta so they
  don't step at authority rate.
