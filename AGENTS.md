# iOS Metal game skills: index for agents

This repository is a library of Agent Skills. If your tool loads `SKILL.md` files automatically,
install them (see README). If not, read the matching file below **before** working on that kind
of task in an iOS/iPadOS Swift + Metal game.

| Task | Read |
|---|---|
| Where state lives; fixed-step simulation; SwiftUI around Metal; switching levels without relaunch | `skills/metal-game-architecture/SKILL.md` |
| Display link, 60/120 Hz, frame drops to 30, frozen 3D view while HUD moves | `skills/metal-frame-pacing/SKILL.md` |
| Blurry frames, MetalFX, dynamic resolution, thermal state, device tiers | `skills/metal-adaptive-quality/SKILL.md` |
| GPU/CPU frame cost, shadows, LOD, draw calls, hitches after explosions | `skills/metal-gpu-performance/SKILL.md` |
| Wrong colours, white/magenta surfaces, z-fighting, holes, haze, render crashes | `skills/metal-render-debugging/SKILL.md` |
| Slow startup or level loading | `skills/ios-game-launch-time/SKILL.md` |
| Running the game unattended in the Simulator, debug knobs, autopilot playthroughs | `skills/ios-game-simulator-automation/SKILL.md` |
| Catching render regressions with captures and image diffs | `skills/metal-visual-regression/SKILL.md` |
| Device-only bugs, FPS/heat claims, on-device perf logs | `skills/ios-game-device-telemetry/SKILL.md` |
| Level files, validation CLI, procedural levels, daily challenge | `skills/game-level-data/SKILL.md` |
| Physics engine bridge, destructible terrain and buildings | `skills/game-destruction-physics/SKILL.md` |
| Recoil, haptics, audio, camera shake, slow motion, fair enemy AI | `skills/ios-game-feel/SKILL.md` |
| Game Center leaderboards and achievements | `skills/game-center-integration/SKILL.md` |
| Procedural meshes, vegetation, LODs, art-direction targets | `skills/procedural-art-and-lod/SKILL.md` |
| Setting up a game repo for AI agents; tests; worktrees; evidence | `skills/agentic-ios-game-workflow/SKILL.md` |

Ground rules that apply to all of them:

- Simulator results are functional/visual evidence only. Frame time and heat need a Release
  build on a physical device.
- Renderer and shader code compiles only in the app build, so build the app after changing it.
- Report what you changed, what you checked (with commands), and what is still unverified.

## Maintaining this repo

- One folder per skill under `skills/`; `name` in the frontmatter equals the folder name.
- `python3 scripts/validate_skills.py` must pass.
- No project-specific identifiers, device UDIDs, team IDs, bundle IDs or secrets.
