---
name: metal-gpu-performance
description: Find and cut GPU and CPU frame cost in an iOS Metal game - repeatable measurement, vertex/geometry budgets, shadow cascades, LODs and impostors, fragment variants, bind and state-change reduction, and hitches from destruction or physics. Use when frame time is over budget on device, when planning a performance pass, or when a single event (explosion, collapse) causes a long frame.
license: MIT
---

# Metal GPU and frame-cost playbook

## 1. Make measurements repeatable first

- Where supported, use Xcode's induced GPU performance states for controlled A/B measurements.
  Also measure normal sustained gameplay with automatic power management. Record the selected
  state; induced states do not establish shipping battery life or thermal behavior.
- **Use scripted scenarios for comparable A/B runs.** Unscripted launches drifted and were not comparable. Keep three:
  a static heavy view (fixed spawn pose), a moving camera (scripted path), and a destruction
  burst (same spawn + auto-fire N explosives).
- **Per-pass GPU timing** requires supported counter sampling boundaries or an Instruments
  trace. Command-buffer `gpuStartTime/gpuEndTime` measure the whole completed command buffer,
  not each encoder inside it. Do not split production buffers just to pretend these are pass
  timings. Label passes and report unsupported measurements as unavailable.
- Release builds, physical device, name the device and scenario in every number. Simulator
  numbers are only good for *relative* counts (draws, triangles), never time.

## 2. Geometry is often the unexamined third of the frame

Measure vertex and shadow work as well as fragment cost. Fragment-only optimization can miss
a significant geometry bottleneck in a foliage-heavy or destructible scene.

- **Vertex size.** Inspect actual host/shader stride and alignment rather than summing field
  widths. Consider a packed position-only stream for passes that need no other attributes,
  then compressed main attributes. Verify layout, precision and deformation requirements;
  skinned, alpha-tested and displaced shadow/motion passes may need additional inputs.
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
- Memoryless, unstored depth only when nothing reads it after the pass. Temporal upscaling,
  motion reconstruction and depth-aware postprocessing often require stored depth.
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

For each experiment record device/OS, build, scenario, resolution, quality, power state, duration
and sample count. Historical reductions motivate these hypotheses but do not predict your gain.

See `references/profiling-commands.md` for xctrace / Metal HUD commands.

Source: [GPU command-buffer timing](https://developer.apple.com/documentation/metal/mtlcommandbuffer/gpustarttime). Geometry budgets and pass costs above are case-study examples; remeasure for your assets and device.
