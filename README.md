# iOS Metal Game Skills

Agent Skills for building native iOS/iPadOS games with **Swift, Metal and a physics engine**.
They work with Claude Code, OpenAI Codex, GitHub Copilot, Gemini CLI, Cursor and any other agent
that reads the open [Agent Skills](https://agentskills.io) format (`SKILL.md` + optional
`references/` and `scripts/`).

Practical engineering patterns for native games: a SwiftUI shell, a testable simulation,
a native physics bridge, and a Metal renderer. These skills help an agent make implementation
and validation decisions; they do not provide a game engine or guarantee a particular visual
quality level. Art direction, assets, animation, accessibility and sustained device playtesting
remain part of shipping a polished game.

Case studies explain failure modes. Numerical thresholds, geometry budgets and quality ladders
are examples to calibrate for your content and devices, not portable performance promises.
Preserve your project's architecture and product decisions unless the requested change requires
revisiting them. Commands and app hooks labeled as examples need integration into your game.

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
  flags possible fallback textures, sky holes, blowouts, flicker and z-fighting. Rejects incomplete
  capture sets and writes an HTML report. Baselines are never changed automatically.
- `skills/agentic-ios-game-workflow/scripts/run_tests.py`: a macOS XCTest-only SwiftPM runner for
  expensive shared fixtures. Rejects unsupported discovery; use standard `swift test` for Swift
  Testing or mixed-framework packages.

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
scripts/install.sh --agent codex --skill metal-frame-pacing --replace # back up, then replace
```

| Agent | User folder | Project folder |
|---|---|---|
| Claude Code | `~/.claude/skills` | `.claude/skills` |
| OpenAI Codex | `~/.agents/skills` (older builds: `~/.codex/skills`) | `.agents/skills` |
| GitHub Copilot | `~/.copilot/skills` | `.github/skills` |
| Gemini CLI | `~/.gemini/skills` | `.gemini/skills` |
| Others | check your tool's docs; many read `.agents/skills` | |

Existing skills are preserved by default, including local edits and symlinks. `--replace`
moves the old entry to a unique `.skill-backup.*` directory beside the skills directory, then
installs the replacement. The script prints the backup path. Review/remove backups yourself.
All requested skill names and agent names are validated before installation starts. Run only one
installer at a time per destination. `--project` requires an existing directory.

Each skill includes its own required scripts/references. Mentions of sibling skills are optional
further reading, so `--skill` can install a single topic. Script paths in a skill are relative to
its installed folder; invoke the full path when your working directory is the game repository.

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
symptom, the cause and the fix, and include a measured number when there is one. Keep each `SKILL.md` under about 200 lines and put conditional detail in `references/`.
Do not include private project names, identifiers, home paths, credentials or device identifiers.
Use generic placeholders and primary-source links for API/version claims.

## Development and validation

Use Python 3.14. The validator requires PyYAML; image comparison and its tests require NumPy and
Pillow. Shell helpers require Bash; app/device workflows require macOS and Xcode. VRT can run on
other platforms against existing captures.

```bash
python3.14 -m venv .venv
. .venv/bin/activate
python3.14 -m pip install -r requirements-dev.txt
python3.14 scripts/validate_skills.py
bash -n scripts/install.sh skills/ios-game-simulator-automation/scripts/sim_smoke.sh
python3.14 -m unittest discover -s tests -v
# macOS/Xcode only: real temporary XCTest and Swift Testing packages
python3.14 tests/swift_integration.py
```

The unit suite uses temporary folders, generated image fixtures and mocked simulator commands;
it does not modify a live simulator or user-level skill installation. The macOS integration test
builds temporary Swift packages. CI runs structural/behavioral checks on Linux and macOS, plus
real Swift integration on macOS. Syntax and metadata checks alone do not validate skill advice.

For an installed VRT skill alone, create a Python 3.14 virtual environment and install
`numpy` and `Pillow`. The XCTest runner uses only Python's standard library.

## License

MIT. See [LICENSE](LICENSE).
