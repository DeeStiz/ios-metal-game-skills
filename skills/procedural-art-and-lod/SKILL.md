---
name: procedural-art-and-lod
description: Art-direction rules and LOD techniques for procedural or code-built 3D content in a mobile Metal game - silhouette-preserving LODs, impostors, foliage card shading and cross-fades, per-instance colour variation without breaking batching, linear albedo bands, exposure and haze targets, and an art bible agents can follow. Use when generating trees, props or buildings in code, when distant objects look wrong or pop, or when visuals drift from a consistent style.
license: MIT
---

# Procedural art and LOD for mobile Metal

Agents produce geometry fast; without written rules it drifts into boxes, cones and neon
greens. Keep a short **art bible** in the repo with numbers an agent can check, and follow it.

## Silhouette and LOD

- Each object keeps **one silhouette class** at every distance. Reduce facets with distance;
  never swap a tiered conifer for a cone or a clustered crown for a sphere.
- Code-built geometry may be boxes only when the real thing is boxy. Round things: ≥ 12 sides
  near, ≥ 6 far.
- Organic masses: union several lobes so the outline breaks up — no perfectly smooth convex hulls.
- LOD bands for one object must not overlap or gap; use hysteresis (≈ 2 m for houses).
- Simplify at load with a quadric simplifier within ~1 px; don't let small details cast shadows.

## Vegetation kit

One procedural kit for every tree, shrub, fern and horizon tree, sharing a bark set and one leaf
atlas, reads as one family.

- Budgets that worked on phones: trees LOD0 1.3k–5.9k tris (< 22 m), LOD1 350–2.2k (to 48 m),
  LOD2 = two crossed impostor cards from LOD0 renders (16 tris, to 110 m). Undamaged plant = 2
  instanced draws (welded bark + crown); all impostors share one mesh/material = 1 draw.
- Result vs. imported models: −37 to −40% triangles, fewer draws, ~29 MiB textures.
- **Card normals bent** toward the crown's outside (cylindrical for conifers, spherical for
  broadleaf) so a crown shades as a volume.
- **Cross-fade by card rank**, not screen dither (dither holes rendered black).
- **Per-instance tint** from a deterministic seed (blue-green ↔ yellow-green, value ±12%). Don't
  create per-tree materials; that splits batches.
- Wind is presentation only: trunk bend ∝ height², limbs sway as bodies (weight/phase packed in a
  spare vertex lane), flutter toward card edges; strength from the weather state.
- Damaged plants switch to a split LOD0 (crown, limbs, trunk sections) driven by damage authority.
- Cache the cooked kit on disk (see `ios-game-launch-time`).

## Colour and light targets

- Shade in linear; tone-map (ACES) and gamma in the presentation pass. Author albedo in linear.
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
