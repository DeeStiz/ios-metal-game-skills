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

1. **Engine is a SwiftPM package with no UIKit/Metal imports.** It builds and tests on the Mac
   in seconds. The app target holds the renderer, shaders, HUD and platform services. Shader and
   renderer code is only compiled by the app build, so run an app build for those changes.
2. **Fixed-step authority, independent of presentation rate.** Gameplay steps at exactly 1/60 s
   (physics substeps ≤ 1/120 s). Presentation runs 30–120 Hz. The poll runs *zero or one* step
   per callback and rebases missed intervals; never catch up in bursts (burst catch-up turns a
   single hitch into a spiral).
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
7. **Determinism by construction.** No unseeded randomness in the engine. Use integer-hash value
   noise / fbm seeded from content, not `Foundation` RNG. Sort by stable IDs, not dictionary
   order. This is what makes replays, checkpoints, visual regression and cache keys possible.
8. **Checkpoints carry an authority hash** and restore rejects a mismatch. Version the schema per
   domain (an AI roster change bumps only the encounter schema).
9. **Level-derived state lives in a context, not in `static let`.** See
   `references/level-context.md`. Process-wide statics make in-process level switching
   impossible and leak the previous level.
10. **SwiftUI is the shell, not the game.** A `UIViewRepresentable` hosts a `UIView` that owns
    the `CAMetalLayer` and `CAMetalDisplayLink`. SwiftUI gets compact, cache-keyed scalar
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

- Generate the Xcode project from a spec (`xcodegen` `project.yml`). Commit the generated
  project if CI or teammates need it, but regenerate on conflicts instead of hand-merging
  `project.pbxproj`.
- Split very large types into ordered sibling files (`GameSession+01Core.swift`,
  `+02Authority.swift`, …) so readers and agents find code by name.
- Gate debug features behind environment variables read in one place, logged on launch
  (see the `ios-game-simulator-automation` skill).

## References

- `references/level-context.md` — in-process level switching without leaks.
- `references/water-and-hazards-as-authority.md` — why water, fire and floods are world state,
  not shaders.
