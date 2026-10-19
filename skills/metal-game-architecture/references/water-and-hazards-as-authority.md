# Water, fire and floods are world state

When water affects movement, damage or world topology, model those effects in world authority
and render the result. Cosmetic-only water can remain a presentation effect. Example components:

- **Descriptor** per body: kind, bathymetry, optical profile, interaction profile, barriers
  (dams, banks), drainage metadata.
- **World object** per body: cells, revision, authority tick, open barriers, ripple directives,
  terrain-edit application, stable hash, checkpoint envelope.
- **Set** of bodies in descriptor-ID order: queries, interaction fan-out, terrain-edit fan-out,
  stable hash.

Consumers:

- Player movement reads wet/dry depth from authority.
- Terrain edits (craters, tunnels) reconcile through `applyTerrainEdit` before presentation may
  show changed water.
- Set pieces (a dam break) consume only the authoritative "barrier open" fact.
- The renderer draws cells and directives. It cannot open barriers or change hydrology.
- Splash VFX alone never mutates water or terrain.

The same split works for fire (a grid of burning cells with wind-led spread and fuel), floods (a
small shallow-water-equations solver drawn as one surface), rubble, and blast exposure: one hazard
authority stepped at the fixed rate, checkpointed, read by gameplay (damage, AI sight, footstep
masking) and by presentation (fire volumes, flood mesh, audio beds) through a broadcast snapshot.

## Bugs this prevented or caused

- **Shared mesh budget overflow:** spilled water overran a shared water vertex buffer and
  crashed. Give dynamic surfaces their own capacity and clamp with a logged warning.
- **Rising flood vs temporal upscaling:** changing topology may invalidate motion history.
  Preserve previous geometry when possible; otherwise use a supported reactive mask (MetalFX
  configuration requires iOS 17.4+) for affected pixels or a spatial fallback. A changing vertex
  array alone does not prove motion vectors are impossible.
- **Leftover water in valleys:** a flood solver on nearly flat terrain leaves puddles. Give valleys
  real slope or add drainage sinks.
