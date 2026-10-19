---
name: metal-render-debugging
description: Diagnose visual bugs in an iOS Metal game renderer - wrong or white surfaces, magenta/flat fallback textures, z-fighting, black holes in foliage, missing geometry or see-through terrain, blown-out haze, NaNs, and crashes from shared buffers. Use when something renders wrong, flickers, disappears, or looks different on device than expected.
license: MIT
---

# Metal render debugging: symptoms → causes

Each entry is a bug that actually shipped to a device build and how it was found.

## A surface renders white / ignores its depth or a texture

**Texture-slot clobbering by a shared bind helper.** The water fragment shader read the scene
depth at `[[texture(9)]]`. A `bindLightingTextures()` helper ran again per water batch and owned
slot 9 for the weather occlusion map. Water read a top-down precipitation depth as its bed depth
and drew a snow-white sheet — only on levels with weather.

- Keep a **slot map** in a C-compatible shared header with explicit integer constants, imported
  through the app bridge and included by MSL, or generate matching Swift/MSL declarations.
  A Swift enum cannot itself be included by an MSL shader. Validate generated layouts.
- Give pass-specific inputs slots above the shared range.
- When a bug appears only under one feature (weather, night, flood), suspect a binding that
  feature adds.
- Metal API validation does not catch a valid-but-wrong texture in a slot; a debug view does.

## Flat colour / magenta patches

Fallback textures — a material lookup failed and you got the default. Log material misses once
per key; render fallback as obvious magenta in debug; make visual regression flag
"textured tile became flat colour".

Related: a release device build loaded nothing because the bundled cooked-asset revision didn't
match the one the catalog referenced. Validate that every catalog path exists in the bundle as a
build phase.

## Z-fighting

Coplanar faces (building corners, walls meeting terrain, decals). Fix geometry (inset, overlap one
side) rather than depth bias where you can. Detect it automatically: capture three frames along a
tiny camera path; regions where frame b differs from both a and c while a and c agree are
alternating (see `metal-visual-regression`).

## Black holes / speckles in alpha-tested foliage at LOD transitions

Screen-door dithered LOD cross-fades leave holes the sky pass can't fill, which showed black.
First inspect background clearing, depth writes and sample/discard behavior. Rank-based card
fades are one alternative: pair outgoing/incoming coverage and verify the silhouette. Dithering
is not inherently invalid; choose a transition compatible with the depth and temporal pipeline.

## Geometry missing / "lid" deleted / see-through terrain

- A tiled render path culled a chunk as "detached" during a sub-region rebuild and deleted the
  mountain top. Forbid detach-culling on partial rebuilds; test with a dug tunnel.
- "I can see through the mountain from inside the tunnel" was a thin needle peak, not a render
  bug: the carved mesh was watertight but the rock was < 1 voxel thick. Check the data before the
  shader.
- Blasted tunnels need the landscape heightfield masked inside the bore or you get a "lid" and a
  fall-through bounce.

## Everything far away is white/milky at dusk

Distance haze used a fixed daylight colour; at golden hour far trees blended 80–90% into it and
read as white cut-outs against a purple sky. Scale haze by the time-of-day horizon radiance and
borrow its hue near twilight. Keep a readable near-field floor (haze start ≥ ~60 m) and clamp
opacity/exposure for every weather × hour combination in a unit test.

## Snow/wet on vertical faces, wrong lighting

Weather surface effects must weight by world-space normal (snow ∝ saturate(N.y)), and by an
occlusion map so covered surfaces stay dry.

## NaNs and broken normals

Ship debug views behind a function constant or env knob: `1` NaN check (green ok, magenta bad),
`2` LOD lanes, `3` shading normal, `4` shadow / N·L / ambient. Also an AO-only and a raw-HDR view.
For alpha cards, compare two-sided normal conventions against the authored normals and lighting
model; avoid applying a universal flip/mirror rule without a debug-normal capture.

## Crash after a big event

"Spilled water overran the shared water mesh budget." Any dynamic geometry appended into a
shared fixed-capacity buffer needs its own capacity, a clamp, and a logged warning. Also a
grenade waking sleeping debris crashed the physics bridge — validate body handles crossing the C
boundary.

## Workflow

1. Reproduce from a fixed camera (`DEBUG_SPAWN=x,z,yaw,pitch`), no enemies, muted audio.
2. Toggle the suspect feature off with an env knob (A/B on the same pose).
3. Switch to a debug view.
4. Capture a GPU frame (Xcode → Debug → Capture GPU Workload) and inspect the bound resources of
   the bad draw — this finds slot clobbering immediately.
5. Fix, then add a VRT shot at that pose so it stays fixed.
