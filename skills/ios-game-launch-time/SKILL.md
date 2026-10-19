---
name: ios-game-launch-time
description: Measure and cut tap-to-playable time for an iOS Metal game - launch timelines, parallel prewarm, content-addressed cooked-product disk caches, pipeline compilation, and loading screens. Use when a game takes too long to start or to load a level, when adding a loading screen, or when deciding whether to add Metal binary archives.
license: MIT
---

# Launch time: tap to playable

Measure cold install, cold process launch, warm launch and level transitions separately. Cache
state and shader compilation can change the result substantially; use comparable runs.

## Define and measure "playable"

Record distinct milestones: process start, first presented frame, simulation ready, and first
presented gameplay frame with controls enabled. A resource gate opening alone is not playable.
Measure process-start latency with a supported platform clock/source appropriate to your target;
include pre-main work where available. Reserve "tap-to-playable" for an externally observed tap
and visible interactive frame. Do not label process-start time as tap time.

Example application-defined log fields:

```
LaunchStage t=4120 dt=310 name=rendererInitialCommitStart
LaunchSummary processToInteractiveMs=6480 load=5120 cache=h2/m0 slowest=[...ten largest gaps...]
LaunchTimeline [every stage once, in time order]
```

Stages queued from other threads are stamped at the call site (`atMs=`), not when logged.

## Common sources of startup cost

| Work | Investigate | Possible change |
|---|---|---|
| First resource commit | Repeated asset parsing/hashing on every material bind | Memoize complete asset identities; prewarm with bounded concurrency and cancellation. |
| Material tables | Building identical level-independent products repeatedly | Share immutable tables with explicit versioning. |
| Scene products | Independent cooks serialized on the critical path | Run independent work concurrently within CPU/memory budgets. |
| Terrain/world template | Rebuilding deterministic products every launch | Content-addressed disk cache, verified against a fresh cook. |
| Renderer/PSOs | Blocking resource or pipeline creation | Overlap independent work and show a responsive loading UI. |
| Physics scene | Allocating before other independent work starts | Prepare off the critical path, then hand over through explicit ownership. |

Pattern: **find work that doesn't depend on the player's choice and start it at app launch on
other cores with measured concurrency**. Separate speculative preparation from activation;
prewarming a default level must not override a later player selection or exhaust startup memory.

## Cooked-product disk cache

- Key = `SHA-256(kind | codeIdentity | inputs)`.
- Include explicit cook/schema version and relevant tool/asset versions in `codeIdentity`.
  An executable LC_UUID can additionally isolate builds, but is not a substitute for all input
  identities (for example external data and separately built code). Bound cache size and recover
  from corrupt/partial writes with atomic replacement.
- Level inputs = SHA-256 of the level's canonical, sorted-key manifest.
- Store each product with its content fingerprint; rebuild on mismatch.
- Test: a disk hit is byte-identical to a fresh cook (densities, materials, hashes).

## Pipelines

Use a device trace to determine whether pipeline creation is on the critical path before adding
`MTLBinaryArchive`. OS caches vary with build and system state. Create PSOs asynchronously
(`makeRenderPipelineState(descriptor:completionHandler:)`) in parallel either way.

## Loading screen

Spend the wait on a mission briefing (title, objectives, map) instead of a progress list. Hand off
at the resource gate. Cache the briefing map image with the same disk cache.

## Level switches

Keep level-scoped state isolated and retain safe content-keyed caches across switches. Print a
separate summary per load (menu selection to visible interactive frame), with cache hit/miss counts.
