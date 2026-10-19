---
name: game-level-data
description: Make game levels data-driven JSON that extends a base scene, validate them on the Mac with a CLI before launching, generate levels procedurally from intents or plain text, and offer daily challenges and share codes. Use when adding a level format, letting an agent or player author levels, building a level editor/generator, or moving hard-coded world layout into data.
license: MIT
---

# Data-driven levels an agent can author

With this approach a single hard-coded scene can grow into many levels, a campaign, a daily
challenge and a player-facing level creator — all JSON, all validated, all playable end to end by
an autopilot.

## Format

- **`"extends": "<base-scene-or-file>"`** and hold only differences. A `resolve` command prints
  the merged result. Most levels are 50–300 lines.
- Coordinates in metres, yaw in degrees; place things **by relationship** where possible
  ("behind building X, 6 m from the road") and let the resolver compute coordinates.
- Sections: `world` (size, terrain features, water, roads), `structures`, `props`,
  `gameplay` (insertion, hostiles, patrols, vehicles, loadout), `mission` (objectives with type,
  text, hints, order, timers), `rules` (event → action: message, spawn, alarm, reinforce),
  `environment` (weather, time of day, haze).
- Everything the shipped scene had fixed must become movable, rotatable and removable, or a
  level eventually needs to fight it ("nothing stays at its shipped place or traps").
- Version the schema; migrate on load.

## Validate on the Mac, not in the app

Ship a small CLI from the engine package (same code the app uses):

```
level-tool validate L.json        # schema, references, ranges
level-tool check L.json           # semantic: reachable objectives, spawn not in walls, roads connect
level-tool map L.json -o map.png  # top-down render for a quick look
level-tool resolve L.json         # merged output
level-tool compose --random SEED  # procedural level
```

Agents run `validate` + `check` before ever launching the Simulator. Errors name the JSON path.

## Procedural generator (no ML needed)

`LevelIntent` (setting, size, objective types, twists, difficulty, weather, seed) →
`LevelComposer` → level JSON that extends the base scene. A small keyword parser maps free text
("night raid, heavy rain, three targets") to an intent. Every composed level must pass
`validate`/`check` in a test over many seeds. Share codes encode the intent + seed
(e.g. `XX1-…`), versioned when new twists appear.

## Daily challenge

UTC day number → curated theme rotation (shuffled cycles) → intent → composer. Every
player gets the same level; scene id `daily.YYYY-MM-DD`. One scored attempt per day, unlimited
practice.

## Loading levels in-process

Level-derived state must live in a per-level context so switching levels does not need a
relaunch (see `metal-game-architecture/references/level-context.md`). Precedence: env var
(automation) → menu selection → saved active level → bundled default.

## A level is done when

1. `validate` and `check` pass.
2. A fair autopilot route (enemies on, no cheats) logs `outcome=completed`.
3. VRT shots exist for it and match the baseline.
4. Its route is saved next to the level for regression runs.

Playtest notes worth keeping in the level's doc: sight ranges vs. enemy positions (can the
intended approach actually be taken unseen?), how much force a structure really needs to fall,
rotated props whose anchor offsets changed.
