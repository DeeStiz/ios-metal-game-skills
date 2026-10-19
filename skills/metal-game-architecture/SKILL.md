---
name: metal-game-architecture
description: Structure a native iOS/iPadOS game built on Swift, Metal and a physics engine so gameplay stays deterministic and the renderer, HUD and audio stay pure consumers. Use when starting a Metal game, adding a new system (weather, AI, water, vehicles), deciding where state should live, wiring SwiftUI around a Metal view, or untangling a renderer that mutates gameplay.
license: MIT
---

# Metal game architecture

A layout that held up in a large native iOS game (Swift + Metal + Jolt physics). The core idea: **one authority owns
truth, everything else reads immutable snapshots of it.**

## The pipeline

```
SwiftUI app shell ─► session controller (adapter) ─► engine reducers (pure Swift package)
                                                     │  fixed 60 Hz step
                                                     ▼
                                    physics bridge (C API over C++ engine)
                                                     │
                       immutable snapshot ◄──────────┘
                     ┌───────────┼─────────────┐
                Metal renderer  SwiftUI HUD   audio / haptics
                (presentation only — never writes back)
```

## Rules that paid off

1. **Keep simulation independently testable.** One useful layout is a pure SwiftPM engine with
   a native physics bridge and no UIKit/Metal dependency. Put renderer, shaders, HUD and platform
   services in app targets. Build the actual renderer/shader targets after changing them; engine
   tests alone do not validate those targets.
2. **Fixed-step authority, independent of presentation rate.** Choose a simulation interval
   for your physics/gameplay requirements (for example, 1/60 s), independent of 30/60/120 Hz
   presentation. Use a dedicated simulation scheduler or a bounded accumulator. At 30 Hz,
   a display-driven 60 Hz simulation normally needs two ticks per callback. Bound catch-up
   work and explicitly choose what overload does: slow simulation, discard elapsed wall time,
   or stall presentation. Log dropped time; do not silently claim real-time progress.
   On resume, reset the wall-clock origin instead of replaying the background interval.

3. **Publish one settled world product per tick.** After the tick's world work settles, publish
   a single immutable state object. Mission, AI, HUD and renderer all read that one product
   instead of inventing parallel truth.
4. **Snapshots through bounded mailboxes.** Previous + current snapshots go into a small mailbox;
   the renderer interpolates between them. GPU completion handlers drain on later presentation
   callbacks, not inline.
5. **Typed requests into authority, facts out.** Input becomes *intent* (move, aim, fire); the
   fixed step owns ammo, cooldowns, damage and consequences. Physics receives typed body
   requests; lifecycle facts publish only after the native side commits.
6. **Presentation-only systems are labeled as such.** Wildlife, wind sway, view-model springs,
   camera shake and aim telegraphs read authority output and never feed it. Write it in the type
   doc comment so later edits don't cross the line.
7. **Define the determinism contract.** Seed gameplay randomness, sort stable IDs, and record
   input by tick. Distinguish repeatability within one build from cross-device replay or lockstep.
   Pin physics version, build flags, substeps and solver settings; preserve native physics state
   in checkpoints. Async results need deterministic commit ticks or recorded commit events:
   revision fencing alone does not make completion timing repeatable. Test identical input
   traces across frame rates, worker schedules, restores and intended devices. A seeded RNG
   conforming to Swift's RandomNumberGenerator is fine; unseeded gameplay RNG is not.

8. **Checkpoints identify schema and content compatibility.** Verify integrity and reject
   incompatible state unless a tested migration exists. Version domains separately when their
   dependencies allow it; include native physics state needed to reproduce subsequent ticks.
9. **Level-derived state lives in a context, not in `static let`.** See
   `references/level-context.md`. Process-wide statics make in-process level switching
   impossible and leak the previous level.
10. **SwiftUI is the shell, not the game.** For an iOS 17+ custom presentation path, a
    `UIViewRepresentable` can host a view owning `CAMetalLayer` and `CAMetalDisplayLink`.
    An existing MTKView-based renderer can preserve the same ownership boundaries. SwiftUI gets compact, cache-keyed scalar
    snapshots (labels, values, callbacks) so the HUD does not invalidate at 120 Hz when nothing
    changed. It never receives mutable world or physics objects.

## Boundaries table (fill in for your game)

| Domain | Owns | Must not |
|---|---|---|
| Player/input | intent → action clocks, loadout, vitality | read renderer state |
| World/destruction | terrain edits, structure state, dirty sets | trust VFX as truth |
| Physics bridge | accepted body motion, static/dynamic commits | invent gameplay facts |
| AI | perception, cover, navigation, attacks | mutate terrain or mission |
| Mission/rules | stage, objectives, checkpoint semantics | read raw input |
| Renderer | GPU resources, quality, pacing | write gameplay state |
| HUD | labels, controls, accessibility strings | own any gameplay value |

## Project hygiene

- If the repository uses a project generator (for example XcodeGen), treat its spec as the source. Commit the generated
  project if CI or teammates need it, but regenerate on conflicts instead of hand-merging
  `project.pbxproj`.
- Split large types by responsibility when it improves navigation; follow the existing project conventions.
- Gate debug features behind environment variables read in one place, logged on launch
  (see the `ios-game-simulator-automation` skill).

## References

- `references/level-context.md` — in-process level switching without leaks.
- `references/water-and-hazards-as-authority.md` — why water, fire and floods are world state,
  not shaders.

Sources: [Jolt determinism and architecture](https://github.com/jrouwe/JoltPhysics/blob/master/Docs/Architecture.md). The SwiftPM/app split is a suggested layout; use the actual build targets when choosing checks.
