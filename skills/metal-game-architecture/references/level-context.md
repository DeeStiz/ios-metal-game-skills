# In-process level switching with a level context

## The problem

Early on, every level-derived product (compiled scene, terrain, roster, spawn, physics catalogs,
renderer tables) was a process-wide `static let`. That is fast and thread-safe, but it means:

- changing level requires relaunching the app;
- a second level silently reuses the first level's products wherever an ID matches.

## The pattern

Prefer passing an immutable level context explicitly into sessions, workers and render plans.
If adapting static-heavy code, a scoped cache can reduce migration churn, but a mutable global
"current context" must not be read midway through a task. Capture one context and generation
at task submission and reject results belonging to retired generations.

Conceptual pseudocode, not a complete Swift synchronization implementation:

```text
context = makeContext(source, generation)
product = context.once(key, build)
plan = prepare(context, snapshot)
publish(plan) only if plan.generation == activeGeneration
```

`once` needs stable key identity, synchronization, build-failure propagation, and dependency-cycle
handling. Do not hold a nonrecursive cache lock while recursively building dependencies. Readers
must wait for one build or receive its error. Avoid `@unchecked Sendable` unless the storage and
all access paths actually satisfy its synchronization contract. Independent level sessions should
not depend on a process-wide mutable context.

## Finding every static

Combine scoped searches for static caches with a dependency walk from the resolver. Include
indirect dependencies such as renderer tables and constants built from level-derived values.

## Process caches

Caches keyed by IDs that another level may reuse (collision proxies, debug snapshots, per-instance
counters) must be emptied on switch (`retireProcessCaches()`). Caches keyed by **content hash**
(erosion maps, LOD segments, compiled pipelines) stay warm — that is what makes the second load
fast.

## Teardown order

1. Stop accepting new simulation/render work for the retiring generation.
2. Cancel or join its workers; ensure completions cannot publish into the new session.
3. Stop platform sessions and invalidate the view's display link.
4. Drain submitted GPU work asynchronously and retain resources until completion. Never block
   the main thread waiting for work whose completion requires that thread.
5. Explicitly shut down the physics scene after its users finish, then release session/context
   ownership. Use deinit assertions and object counts to detect leaks, not as the shutdown API.
6. Activate the new context when its required resources are ready. If generations overlap during
   a transition, keep separate ownership and enforce a peak memory budget. Bound teardown waits
   and report outstanding owners instead of waiting forever.

## Tests

Load A, B, A, B in one process and assert byte-identical products each time (scene hash, entity
lists, spawn, roster). Assert no A-only entity appears in B. Assert a retired context deallocates.
Assert values build once under concurrency.

## Measurement

Record cold and warm load latency, outstanding owners and memory trends across repeated A/B
switches. Compare like-for-like captures on the same platform. Simulator memory behavior does
not establish physical-device memory headroom.
