# iOS Metal Game Skills

Agent Skills for building native iOS/iPadOS games with **Swift, Metal and a physics engine**.
They work with Claude Code, OpenAI Codex, GitHub Copilot, Gemini CLI, Cursor and any other agent
that reads the open [Agent Skills](https://agentskills.io) format (`SKILL.md` + optional
`references/` and `scripts/`).

Everything here came out of building a native 3D game for iPhone and iPad: a SwiftUI shell, a
deterministic Swift engine, Jolt physics through a C bridge, and a Metal renderer with MetalFX.
The skills hold the
parts that cost the most to learn: device-only freezes, blur, 30 fps locks, launch time,
hitches, and the process mistakes that slowed the agents down. The numbers in them come from real
device logs and captures. Where something was only checked in the Simulator, the skill says so.

## Skills

| Skill | Use it when |
|---|---|
| [metal-game-architecture](skills/metal-game-architecture/SKILL.md) | structuring a Metal game: fixed-step authority, immutable snapshots, SwiftUI shell, in-process level switching |
| [metal-frame-pacing](skills/metal-frame-pacing/SKILL.md) | `CAMetalDisplayLink`, 30/60/120 Hz ranges, frozen 3D view, liveness watchdog |
| [metal-adaptive-quality](skills/metal-adaptive-quality/SKILL.md) | dynamic resolution, MetalFX temporal/spatial, device tiers, thermal state, blurry frames |
| [metal-gpu-performance](skills/metal-gpu-performance/SKILL.md) | frame time over budget: measurement, geometry, shadows, LOD, binds, hitches |
| [metal-render-debugging](skills/metal-render-debugging/SKILL.md) | something renders wrong: slot clobbering, fallback textures, z-fighting, holes, haze |
| [ios-game-launch-time](skills/ios-game-launch-time/SKILL.md) | tap-to-playable time, prewarm, cooked-product disk cache, pipelines |
| [ios-game-simulator-automation](skills/ios-game-simulator-automation/SKILL.md) | letting agents build, launch, capture and play the game unattended |
| [metal-visual-regression](skills/metal-visual-regression/SKILL.md) | deterministic captures and image diffs that catch render regressions |
| [ios-game-device-telemetry](skills/ios-game-device-telemetry/SKILL.md) | diagnosing device-only problems from an on-device perf log |
| [game-level-data](skills/game-level-data/SKILL.md) | JSON levels with `extends`, a validation CLI, procedural generation, daily challenges |
| [game-destruction-physics](skills/game-destruction-physics/SKILL.md) | Jolt via a C bridge, tunnelable terrain, structural collapse, explosion hitches |
| [ios-game-feel](skills/ios-game-feel/SKILL.md) | recoil, haptics, audio, slow motion and readable enemies without breaking determinism |
| [game-center-integration](skills/game-center-integration/SKILL.md) | leaderboards, achievements, offline outbox, App Store Connect setup |
| [procedural-art-and-lod](skills/procedural-art-and-lod/SKILL.md) | code-built geometry, vegetation, LODs, impostors, colour targets, art bible |
| [agentic-ios-game-workflow](skills/agentic-ios-game-workflow/SKILL.md) | running a game repo with AI agents: AGENTS.md, tests, worktrees, evidence |

Bundled scripts:

- `skills/ios-game-simulator-automation/scripts/sim_smoke.sh`: build, install, launch, wait for
  a log line, then screenshot or record video in the Simulator.
- `skills/metal-visual-regression/scripts/vrt_compare.py`: compares frames tile by tile and
  flags fallback textures, sky holes, blowouts, flicker and z-fighting. Writes an HTML report.
- `skills/agentic-ios-game-workflow/scripts/run_tests.py`: a sharded SwiftPM test runner for
  engines whose shared fixtures are expensive to build.

## Install

### Claude Code

```text
/plugin marketplace add DeeStiz/ios-metal-game-skills
/plugin install ios-metal-game-skills@ios-metal-game-skills
```

You can also copy the skills into `~/.claude/skills/` for your user, or `.claude/skills/` for one
project.

### Any agent (Claude, Codex, Copilot, Gemini)

```bash
git clone https://github.com/DeeStiz/ios-metal-game-skills.git
cd ios-metal-game-skills
scripts/install.sh                       # every supported agent, user level
scripts/install.sh --agent codex --link  # one agent, symlinked so `git pull` updates it
scripts/install.sh --project ~/Developer/MyGame --agent copilot  # into a repo's .github/skills
```

| Agent | User folder | Project folder |
|---|---|---|
| Claude Code | `~/.claude/skills` | `.claude/skills` |
| OpenAI Codex | `~/.agents/skills` (older builds: `~/.codex/skills`) | `.agents/skills` |
| GitHub Copilot | `~/.copilot/skills` | `.github/skills` |
| Gemini CLI | `~/.gemini/skills` | `.gemini/skills` |
| Others | check your tool's docs; many read `.agents/skills` | |

Tools change their folders now and then. If yours isn't listed, copy `skills/<name>/` to wherever
it looks. The format is the same everywhere.

For agents without skill support, point them at [AGENTS.md](AGENTS.md). It lists every skill and
when to read it.

## How a skill loads

At startup the agent reads only each skill's `name` and `description`. When a task matches, it
loads the full `SKILL.md`, then opens `references/` or runs `scripts/` only when it needs them.
That keeps the context cost small even with all 15 installed.

## Contributing

Pull requests are welcome, especially lessons from other Metal games. Each lesson should name the
symptom, the cause and the fix, and include a measured number when there is one. Run
`python3 scripts/validate_skills.py` before you open the PR. Keep each `SKILL.md` under about 200
lines and put longer material in `references/`.

## License

MIT. See [LICENSE](LICENSE).
