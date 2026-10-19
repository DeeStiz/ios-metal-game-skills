---
name: metal-gpu-performance
description: Find and cut GPU and CPU frame cost in an iOS Metal game - repeatable measurement, vertex/geometry budgets, shadow cascades, LODs and impostors, fragment variants, bind and state-change reduction, and hitches from destruction or physics. Use when frame time is over budget on device, when planning a performance pass, or when a single event (explosion, collapse) causes a long frame.
license: MIT
---

# Metal GPU and frame-cost playbook

## 1. Make measurements repeatable first

- **Pin the GPU clock** for A/B runs: Xcode → Devices → Induced performance state → Minimum, then
  Medium. On a flagship phone most of a real session ran at the *Minimum* GPU state, starting
  ~25 s in while thermal was still nominal. Design for that state (goal: ≤ 15 ms total GPU at
  Minimum for 60 fps with margin).
- **Scripted scenarios only.** Unscripted launches drifted and were not comparable. Keep three:
  a static heavy view (fixed spawn pose), a moving camera (scripted path), and a destruction
  burst (same spawn + auto-fire N explosives).
- **Per-pass GPU timing** with counter sample buffers or command-buffer `gpuStartTime/gpuEndTime`
  per pass, logged as `gpuPasses=main:7.8,csm:2.2,…`.
- Release builds, physical device, name the device and scenario in every number. Simulator
  numbers are only good for *relative* counts (draws, triangles), never time.

## 2. Geometry is often the unexamined third of the frame

Main pass + shadow vertex work was ~30% of GPU time; earlier audits had only looked at fragment
ALU.

- **Vertex size.** `float3 + float3 + float4 + float2 + uint` pads to 64 B. Step 1: a 12 B
  position-only stream for shadow and motion passes (bit-identical). Step 2: pack the main stream
  (packed position, half/snorm normal and tangent, half2 UV) — 40 B shipped.
- **Shadow casters per cascade.** Don't give every cascade the same caster list. Require a minimum
  caster radius per cascade relative to texel size; skip foliage cards in the far cascade. Build
  the lists once in the candidate index so steady frames cost nothing.
- **Shadow LODs.** Shadow maps are ≤ 2048²; don't draw LOD0 trees into them. LOD1 in cascade 0,
  LOD2 beyond.
- **Cascade cadence.** Far cascades every 2/4 frames, and **stagger** so at most one reduced-cadence
  slice refreshes per frame (two 2048² slices in one frame cost 1.1–1.9 ms vs 0.3–0.5 ms).
- **Check content for duplication.** A small-plant mesh turned out to be byte-identical to a full
  tree (6.2k tris each). A dedicated 600/300/120-triangle mesh was the largest single triangle cut.
  Hash your mesh files and look for duplicates.
- **Unindexed triangle soup** (3 unique verts per triangle) defeats the post-transform cache;
  weld at cook time if vertices are actually shared.
- **LOD ladders with impostors** for vegetation beyond ~50 m (two crossed cards rendered from
  LOD0). Distant terrain: per-tile LOD with quadric-simplified index lists, tile borders
  vertex-exact so mixed levels can't crack.
- Log `renderTopMaterialTriangles` / top triangle groups to see what actually dominates.

## 3. Fragment and post

- Function-constant **variants per material family** (terrain splat, grass, foliage) instead of
  one uber-shader; check register count/occupancy in the shader profiler before and after.
- Bloom chain in `rg11b10Float` instead of `rgba16Float` (keep a fallback; check banding before
  tone mapping).
- Memoryless, unstored depth for the main pass when nothing samples it later.
- Half-resolution volumetrics/AO with a bilateral upsample.
- Temporal upscaling with jitter is the biggest fragment lever (see `metal-adaptive-quality`).

## 4. Renderer CPU

- Bind lighting/shared textures **once per encoder segment**, track the bound material, don't
  rebind 12 textures + `setFragmentBytes` per draw.
- Sort opaque draws by PSO then material; `renderStateBatches ≈ draws` means no batching.
- Argument buffers / Metal 4 argument tables make a material change one offset and enable
  indirect command buffers for static passes.
- Cache sort keys per candidate; rank labels once and sort integers.
- Planning on a worker is not free: it burns P-core power and delays plans.

## 5. Hitches from gameplay events

A house collapse produced a 245 ms authority tick (186 ms static-collision topology rebuild).

- Move topology product + physics payload planning for the changed structure to a worker. Keep
  the previous static bodies until a **revision-fenced commit**. During the gap treat the
  affected region as conservatively solid for movement and raycasts.
- Add/remove physics bodies in batches (Jolt: `AddBodiesPrepare/Finalize`, batched removal;
  optimise the broadphase after bulk static changes).
- Instrument the owner of every slow product (`slowestTopologyProduct=…`) before fixing.

## 6. Order of work that worked

1. Measurement harness + owner fields.
2. Small isolated wins: shadow cadence, caster filtering, lighting binds.
3. Bit-identical vertex wins (position stream, welding).
4. Temporal jitter + lower temporal scale.
5. Content (duplicate meshes, prop LODs).
6. Async topology for hitches.
7. Medium-risk: shadow LODs, fragment variants, bloom format.
8. Large: argument tables/ICB, packed vertices, impostors — measure after 1–7.

Result on device after steps 1–6: GPU median 13.0 → 9.0 ms, missed authority steps 360+ → 5,
MetalFX mode flips 53 → 10 per run.

See `references/profiling-commands.md` for xctrace / Metal HUD commands.
