---
name: game-destruction-physics
description: Build destructible terrain and structures on iOS with a native physics engine (Jolt via a C bridge) while keeping the simulation deterministic and hitch-free - voxel/SDF terrain edits, structural support and progressive collapse, explosives tuning, craters, and async collision rebuilds. Use when integrating Jolt or another C++ physics engine into Swift, adding destruction, or fixing hitches and crashes after explosions.
license: MIT
---

# Destruction and physics on iOS

## Physics bridge

- Vendor the C++ engine (Jolt) as a SwiftPM target; expose a **narrow C API** target
  (`JoltBridge`) that Swift imports. No C++ types cross into Swift.
- The engine issues *typed requests* (add static, add dynamic, impulse, remove); the bridge
  commits them and returns results. Gameplay facts publish only after the native commit.
- Validate every handle crossing the boundary — a grenade waking sleeping debris crashed on a
  stale body ID.
- Batch add/remove (`AddBodiesPrepare`/`AddBodiesFinalize`); optimise the broadphase after bulk
  static changes. Expose worker count and solver steps as env knobs (2 workers and 4 velocity / 1
  position steps were a good phone default).
- Register real terrain and building statics. A "legacy floor" plane hid many bugs; remove it from
  production paths.
- Physics substeps ≤ 1/120 s under a 1/60 s authority step.

## Terrain you can tunnel through

- Heightfield for open ground + **voxel/SDF density chunks** where digging matters (mountains,
  banks). Fill the interior solid from chunk floor to surface so sphere/capsule subtraction bores
  real navigable cavities, not visual holes.
- Deterministic generation: integer-hash value noise, fbm and ridged fbm from a seed (no
  Foundation RNG); test that a seed reproduces bytes and that variants differ.
- Edits mark dirty bounds → async remesh + collision + navigation refresh. Water reconciles with
  the edit before presentation.
- Thin features cause "see-through" reports. Keep enough rock mass around likely tunnel paths
  (a fuller massif instead of a needle peak), and mask the heightfield inside bores so there is
  no "lid" or fall-through bounce.
- A cheap crater layer: a sparse lattice of signed height offsets + scorch over the flat
  landscape (capped node count, depth limits), saved with the world, sampled by movement and aim.

## Structures

- Buildings as parts with structural support (footprint, rooms, walls, openings, roof). Local
  breach removes panels and collision; loss of support detaches assemblies; load paths give
  progressive collapse and a "topple forecast" you can show the player.
- Size holes to the **player capsule**: a rocket hole in a wall is an ellipsoid stretched downward so
  the player can walk through; walking surfaces are only carved near the impact height so floors
  survive.
- Explosive roles: an area wave with a door-only role was a silent no-op on glass and props. Give
  the secondary wave a generic "secondary blast" role and exclude the direct target.
- Players judge explosives by visible results. If playtesters say a small explosive "didn't do
  anything", tune radius, damage and impulse until it breaks doors, glass, cover and light panels
  while staying well below the biggest weapon.

## Hitches

The topology/collision rebuild after a collapse took 186–282 ms on the authority tick. Fix:
compute the topology product + native payload on a worker, keep the old static bodies until a
**revision-fenced commit**, and treat the changed region as conservatively solid for movement and
raycasts during the gap. Instrument the slowest product and its owner before changing anything.

Also watch for growth over long sessions (debris never sleeping, caches keyed per event).

## Tests worth having

- A tunnel bored upward reaches near the summit and stays enclosed.
- Save → restore preserves world hash; read-only queries don't mutate.
- A changed input invalidates a cache; equivalent implementations agree.
- Avoid tests that freeze content (exact coordinates, counts, golden hashes) — they block every
  level edit without catching bugs.
