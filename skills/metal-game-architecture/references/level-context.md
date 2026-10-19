# In-process level switching with a level context

## The problem

Early on, every level-derived product (compiled scene, terrain, roster, spawn, physics catalogs,
renderer tables) was a process-wide `static let`. That is fast and thread-safe, but it means:

- changing level requires relaunching the app;
- a second level silently reuses the first level's products wherever an ID matches.

## The pattern

Wrap each level-derived static in a `LevelScoped<T>` whose storage lives in the current
`LevelContext`:

```swift
final class LevelContext: @unchecked Sendable {
    let source: LevelSource
    let generation: Int
    fileprivate var storage: [ObjectIdentifier: Any] = [:]
    fileprivate let lock = NSLock()
}

struct LevelScoped<T>: Sendable {
    let build: @Sendable (LevelContext) -> T
    var value: T { LevelContext.current.value(for: self) }  // builds once per context
}

enum Scenario {
    static let proceduralScene = LevelScoped { ctx in compileScene(ctx.source) }
}
```

- Keep the accessor's old name and type so call sites barely change.
- Within a context a value builds once on first read; concurrent readers **wait** for that build
  (same once-semantics as `static let`, so parallel launch prewarm still works).
- `activate(_:)` makes a fresh context current; the old one is released when nothing reads it.

## Finding every static

Do a dependency walk from the level resolver, not a text search. In practice ~250 values moved,
including renderer tables and a few level-independent constants that referenced them (cheap to
rebuild, simpler than splitting).

## Process caches

Caches keyed by IDs that another level may reuse (collision proxies, debug snapshots, per-instance
counters) must be emptied on switch (`retireProcessCaches()`). Caches keyed by **content hash**
(erosion maps, LOD segments, compiled pipelines) stay warm — that is what makes the second load
fast.

## Teardown order

1. Stop the simulation runtime.
2. End platform sessions (audio voices, haptics, controller input workers).
3. Drop the presentation controller; `dismantleUIView` invalidates the display link and releases
   the renderer.
4. The session controller's `deinit` stops the authority queue and shuts the physics scene down.
5. **Wait for an object census to read zero** (session, presentation controller, Metal renderer,
   mesh renderer, Metal view) before activating the next context. Log it:
   `LEVEL_SWITCH phase=teardown released=1 census=[...] footprintMiB=...`.

## Tests

Load A, B, A, B in one process and assert byte-identical products each time (scene hash, entity
lists, spawn, roster). Assert no A-only entity appears in B. Assert a retired context deallocates.
Assert values build once under concurrency.

## Measured result

Teardown 410–490 ms. Light levels reload in ~2.5 s instead of a ~11 s cold launch. Memory after
ten alternating loads showed no growth (Simulator readings swing 100–300 MiB because freed pages
are compressed lazily — compare trends, not single readings).
