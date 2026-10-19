---
name: game-level-data
description: Make game levels data-driven JSON that extends a base scene, validate them on the Mac with a CLI before launching, generate levels procedurally from intents or plain text, and offer daily challenges and share codes. Use when adding a level format, letting an agent or player author levels, building a level editor/generator, or moving hard-coded world layout into data.
license: MIT
---

# Data-driven levels an agent can author

With this approach a single hard-coded scene can grow into many levels, a campaign, a daily
challenge and a player-facing level creator — all JSON, all validated, all playable end to end by
an autopilot where the game supports it. The schema and CLI below are designs to implement,
not tools bundled with this skill.

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
- Version the schema; migrate supported versions on load and reject unknown future versions.
- Specify merge rules: for example recursively merge objects, replace arrays as a whole, and
  use an explicit remove operation rather than an ambiguous null. Resolve the base first;
  reject cycles, duplicate entity IDs, unresolved references and unsupported fields.
- Restrict file-based extends to an allowed content root; bound depth, file size, entity counts
  and numeric ranges. Run validation in the app too when loading external/user-authored data.

Example overlay (the actual field names must match your schema):

```json
{"schemaVersion": 1, "extends": "base-yard", "environment": {"timeOfDay": 18.0}}
```

Document units, handedness, up axis, origin, rotation order and ID stability in the schema.
Resolve author-friendly relationships into a canonical product before runtime use.

## Validate before launching

Implement a small CLI from the engine package using the same validation code as the app.
The following commands describe the proposed interface, not installed executables:

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

Optional product policy: UTC day → versioned theme rotation → intent → composer. For identical
levels across players, include content/generator version as well as seed. Define offline clock
behavior and server authority for competitive scores. One scored attempt plus unlimited practice
is a possible rule, not a requirement for this architecture.

## Loading levels in-process

Level-derived state must live in a per-level context so switching levels does not need a
relaunch. Stop or retire old-generation work before publishing the new context; clear caches
keyed only by reusable entity IDs and retain caches keyed by complete content identity.
Example selection precedence: debug override → menu selection → saved level → bundled default.
Keep debug overrides unavailable in normal shipping play.

## Example acceptance checks

1. `validate` and `check` pass.
2. A representative playthrough reaches its objective. If an autopilot exists, run it with real
   player actions and no cheats; otherwise record a human/device playthrough.
3. Representative captures have been reviewed; compare against an accepted baseline if available.
4. Save any automated route next to the level for regression runs. Automation is not a substitute
   for human assessment of readability, pacing and enjoyment.

Playtest notes worth keeping in the level's doc: sight ranges vs. enemy positions (can the
intended approach actually be taken unseen?), how much force a structure really needs to fall,
rotated props whose anchor offsets changed.
