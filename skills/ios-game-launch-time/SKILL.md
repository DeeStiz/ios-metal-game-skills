---
name: ios-game-launch-time
description: Measure and cut tap-to-playable time for an iOS Metal game - launch timelines, parallel prewarm, content-addressed cooked-product disk caches, pipeline compilation, and loading screens. Use when a game takes too long to start or to load a level, when adding a loading screen, or when deciding whether to add Metal binary archives.
license: MIT
---

# Launch time: tap to playable

Result in one project: first launch after install 17–18.7 s → 6.5–7.2 s; second launch 19.3 s →
5.3–5.8 s (Simulator, same build; confirm on device).

## Define and measure "playable"

"Playable" = the first authority tick after the renderer's resource gate opens, not the first
drawable. Stamp every stage with ms since **process start** (kernel start time via `sysctl`
`KERN_PROC` `p_starttime`), not since `main`, so pre-main and SwiftUI start are visible.

```
LaunchStage t=4120 dt=310 name=rendererInitialCommitStart
LaunchSummary tapToPlayableMs=6480 load=5120 cache=h2/m0 slowest=[...ten largest gaps...]
LaunchTimeline [every stage once, in time order]
```

Stages queued from other threads are stamped at the call site (`atMs=`), not when logged.

## Where the time actually was

| Cost | Before | Fix |
|---|---|---|
| First resource commit on main | 9.4 s | Imported-texture identity re-read and FNV-hashed every PNG on every material bind (5.9 s). Memoize per path. Move model parse + hash to an all-core prewarm at app start using a manifest of last launch's assets. |
| Full material table | 3.4 s | Build from app start; it is level-independent. |
| Scene statics | 2.3 s | Run independent statics on separate cores. |
| World template | 1.25 s | Build in parallel with the scene compile; disk-cache the voxel chunk (124 ms cook → 1.4 ms hit). |
| Renderer creation | 1.45 s | Build on main while the controller builds off-main. |
| Physics scene allocation | 0.4 s | Build in parallel; hand it over. |

Pattern: **find work that doesn't depend on the player's choice and start it at app launch on
other cores**; never resolve the level before the player picks it (a prewarm that read the level
broke the level picker).

## Cooked-product disk cache

- Key = `SHA-256(kind | codeIdentity | inputs)`.
- `codeIdentity` = the executable's `LC_UUID` (read from the Mach-O header): every new build
  starts cold automatically, no manual versioning.
- Level inputs = SHA-256 of the level's canonical, sorted-key manifest.
- Store each product with its content fingerprint; rebuild on mismatch.
- Test: a disk hit is byte-identical to a fresh cook (densities, materials, hashes).

## Pipelines

Warm launches compiled no pipelines (OS shader cache); cold cost was ~1.2 s in the Simulator and
overlapped controller init after the prewarm work. `MTLBinaryArchive` was *not* worth adding
until a device trace shows pipeline creation on the critical path. Create PSOs asynchronously
(`makeRenderPipelineState(descriptor:completionHandler:)`) in parallel either way.

## Loading screen

Spend the wait on a mission briefing (title, objectives, map) instead of a progress list. Hand off
at the resource gate. Cache the briefing map image with the same disk cache.

## Level switches

With a level context (see `metal-game-architecture`), warm content-keyed caches make the second
level load in ~2.5 s. Print a separate summary per load (`load=` menu tap → playable).
