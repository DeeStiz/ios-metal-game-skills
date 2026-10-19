---
name: procedural-art-and-lod
description: Art-direction rules and LOD techniques for procedural or code-built 3D content in a mobile Metal game - silhouette-preserving LODs, impostors, foliage card shading and cross-fades, per-instance colour variation without breaking batching, linear albedo bands, exposure and haze targets, and an art bible agents can follow. Use when generating trees, props or buildings in code, when distant objects look wrong or pop, or when visuals drift from a consistent style.
license: MIT
---

# Procedural art and LOD for mobile Metal

Keep a short **art bible** with reference images, silhouette families, material conventions and
measurable budgets. The geometry/color values below are illustrative for a naturalistic mobile
scene, not universal quality rules. Preserve the project's chosen art direction.

## Silhouette and LOD

- Each object keeps **one silhouette class** at every distance. Reduce facets with distance;
  never swap a tiered conifer for a cone or a clustered crown for a sphere.
- Code-built geometry may be boxes only when the real thing is boxy. Round things: ≥ 12 sides
  near, ≥ 6 far.
- Organic masses: union several lobes so the outline breaks up — no perfectly smooth convex hulls.
- Define contiguous LOD selection bands with explicit hysteresis. Overlap is intentional during
  cross-fades; bound double-render cost and verify complementary coverage.
- Prefer offline/cook-time simplification with screen-space error limits. If generated content
  needs runtime simplification, move it off the critical path and cache it. Cull insignificant
  shadow casters based on projected size rather than an unconditional small-detail rule.

## Vegetation kit

One procedural kit for every tree, shrub, fern and horizon tree, sharing a bark set and one leaf
atlas, reads as one family.

- Budgets that worked on phones: trees LOD0 1.3k–5.9k tris (< 22 m), LOD1 350–2.2k (to 48 m),
  LOD2 = two crossed impostor cards from LOD0 renders (16 tris, to 110 m). Undamaged plant = 2
  instanced draws (welded bark + crown); all impostors share one mesh/material = 1 draw.
- Compare triangles, draws, overdraw and texture memory against the actual asset baseline.
  Procedural content does not inherently outperform imported models.
- **Card normals bent** toward the crown's outside (cylindrical for conifers, spherical for
  broadleaf) so a crown shades as a volume.
- **Choose a verified fade strategy**: card-rank fades or dither with correct depth/background
  handling. Test coverage and temporal stability in your pipeline.
- **Per-instance tint** from a deterministic seed (blue-green ↔ yellow-green, value ±12%). Don't
  create per-tree materials; that splits batches.
- Wind is presentation only: trunk bend ∝ height², limbs sway as bodies (weight/phase packed in a
  spare vertex lane), flutter toward card edges; strength from the weather state.
- Damaged plants switch to a split LOD0 (crown, limbs, trunk sections) driven by damage authority.
- Cache the cooked kit on disk (see `ios-game-launch-time`).

## Colour and light targets

- Shade in linear light. Color/albedo textures are commonly authored as sRGB and sampled with
  an sRGB texture format to decode to linear. Numeric albedo constants must be linear; normal,
  roughness and other data maps must not receive sRGB decoding. Choose the tone mapper for the
  art direction. Encode output exactly once: an sRGB render target performs encoding on write,
  so do not also apply manual gamma. Define a separate explicit HDR output path if supported.
- Grey card (0.18) in sun → ~0.45–0.55 sRGB after tone mapping at default exposure.
- Shadowed siding ≈ 25–35% of its lit value at late morning; canopy albedo never below 0.02 G (no
  black foliage).
- No world surface above ~0.65 HSV saturation except objective markers, hazard paint and fire.
- Horizon forest sits *in* the haze; haze colour follows the sky at dusk (see
  `metal-render-debugging`).
- Texel density and wear: one wear level per district; a house and its fence share an age.

## Fallback materials

Write down which material key each code-built surface uses (sawn lumber vs. trim paint vs.
fresh fracture vs. damaged framing) and which it must never use. Missing keys should fall back to a
neutral default, not the damage material.

## Checking a visual change

1. App build.
2. Before/after captures from the same camera with enemies off.
3. Compare draws and triangles from the same spawn (relative only in the Simulator).
4. Frame time and heat only from a device run.
5. Texture memory budget enforced by a test (a fixed MiB budget catches creep early).
