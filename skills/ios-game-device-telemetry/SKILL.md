---
name: ios-game-device-telemetry
description: Instrument an iOS game so a real-device play session can be diagnosed afterwards - a once-per-second performance log in the app container, launch summaries, liveness counters, and pulling the log with devicectl before it is overwritten. Use when someone reports a device-only problem (stutter, heat, blur, freeze), before claiming any FPS or thermal result, or when adding perf logging to a Metal game.
license: MIT
---

# Device telemetry for games

The Simulator can't tell you frame time, heat, GPU state or device-only freezes. A plain text log
written by the app on the device can — if you design it so the next session answers the question.

## Write one line per second

To `Documents/perf.log` (and the console), `key=value`, one tag per line kind:

```
PerfSample t=63 fps=59.8 gpuMs=9.1/11.4 cpuMs=4.2 thermal=fair lowPower=0
  dynres=s75/60fps/flagship/i2/d1/u0 miss=g0/e1/m0 stall=0/0/0
  metalFX=temporal mipBias=-0.42 draws=412 tris=0.88M simMs=1.9/6.0
```

Include:

- presented fps and a cadence histogram; completed GPU ms p50/p90; encode CPU ms; authority
  tick ms (mean/max);
- **miss attribution**: correlate misses with GPU, encode and callback timing; keep an unknown
  category when evidence is insufficient rather than forcing a causal label;
  `stall=` counts display-link callbacks arriving > 1.5 frames late (busy main thread);
- quality state: render scale, tier, upscaler mode, shader level, heat policy step;
- OS thermal state and Low Power Mode;
- build identity, session ID, device/OS, scenario, power state and sampling configuration on
  the first line. Rotate bounded logs by session and flush off the critical render path.

Plus event lines: `LaunchSummary processToInteractiveMs=…`, `LEVEL_SWITCH render phase=t6s
liveCompleted=… callbacks=…`, `presentationWatchdog action=…`, command-buffer failures.

## Pull it before anything else

Apps may rotate logs on launch; uninstalling deletes the app container, while an ordinary update
generally preserves data. Pull the session log before changing builds or relaunching so the app
cannot overwrite the evidence:

```bash
xcrun devicectl list devices
xcrun devicectl device copy from --device "$DEVICE" --domain-type appDataContainer \
  --domain-identifier "$BUNDLE_ID" --source Documents/perf.log --destination ./device-logs/run.log
```

Install without launching (`xcrun devicectl device install app --device "$DEVICE" MyGame.app`);
launching fails while the phone is locked, so ask whoever has the phone to tap the app.

## Read it in this order

1. **Sample count and identity.** Zero samples can mean a dead loop/writer, wrong path, stale
   session, disabled instrumentation, or a failed copy. Check build/session identity and writer
   health before diagnosing rendering. Reopen a handle after intentional file rotation.
2. Launch summary.
3. Presented fps, GPU/CPU ms.
4. `dynres` / miss attribution / stalls.
5. Upscaler mode and sharpness fields.
6. Quality policy and thermal state over time.
7. Liveness lines: `liveCompleted` should rise with `callbacks`; any watchdog line is a stall.

## Rules for claims

- FPS, frame time and heat claims need a **Release build on a physical device**, with the device
  and scenario named. Simulator numbers are relative counts (draws, triangles) only.
- A fix for a device-only bug is "unconfirmed" until a device log shows it. Add the counters that
  would prove it *before* asking for another session.
- A single run is noisy; compare like-for-like scenarios (same spawn, scripted input).
