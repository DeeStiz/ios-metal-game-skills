---
name: agentic-ios-game-workflow
description: How to run an iOS/Metal game repository with AI coding agents (Claude, Codex, Copilot and others) - a lean AGENTS.md, choosing the right check for each kind of change, fast sharded engine tests, parallel agents in worktrees with private DerivedData, evidence honesty (Simulator vs device), and avoiding process bureaucracy that slows agents down. Use when setting up a game repo for agents, writing AGENTS.md/CLAUDE.md, coordinating several agents, or when agent changes keep breaking the build or stalling on rituals.
license: MIT
---

# Running a game repo with AI agents

Lessons from building a native Swift/Metal game mostly with AI agents.

## Keep AGENTS.md short and practical (≈ 30–60 lines)

Include: what the game is, where things live, how to build and test each layer, how to run a
smoke, how levels/data are validated, evidence rules, and "preserve uncommitted work".
Point at docs for depth; explicitly identify any required checks and why they exist.

Keep required routing and checks that prevent demonstrated defects. Prefer concise instructions
and linked references over repeated paperwork. Respect repository/user instructions; do not
remove gates merely because another project did not need them. Golden images/hashes are useful
for intentional compatibility contracts, but should have a deliberate review/update process.

## Tests that help agents

- Test **properties**, not frozen content: save/restore round-trips, equivalent paths agree,
  read-only queries don't mutate, a changed input invalidates a cache, determinism per seed.
- Avoid source-text or frozen-content tests when behavior is the real contract. Exact values or
  golden hashes can be appropriate for serialization, deterministic fixtures and approved visual
  baselines; explain the invariant and require review when changing it.
- For macOS **XCTest-only** SwiftPM packages with expensive shared fixtures,
  `scripts/run_tests.py` builds once and runs classes in long-lived `xctest` shards. It requires
  Python 3.14 and Xcode, rejects unknown/Swift Testing discovery, and verifies every selected
  test completed. Use standard `swift test` for mixed-framework packages or Swift Testing.
  `--fast` uses debug configuration with `-O` in a separate scratch directory; validate that
  configuration's behavior before relying on it. Filter by class-name substring for focused
  runs. Timings depend on the package; logs go to `.build/test-shards/`.
- Keep one runner per package scratch directory at a time; worktrees isolate parallel builds.
  Example: `python3.14 scripts/run_tests.py --package-path /path/to/Engine --shards 4`.
  Here `scripts/` is relative to the installed skill folder, not an assumed app-repo script.

## Pick the check that matches the change

| Change | Check |
|---|---|
| Engine logic | focused engine test classes |
| Renderer / shaders | an app build (SwiftPM tests don't compile them) + a Simulator capture if visuals matter |
| `project.yml` / added or renamed app files | `xcodegen generate`, then app build |
| Level data | schema/semantic checks, then representative automated or human playthrough |
| Visual change | before/after captures from a fixed camera, or the VRT harness |
| Performance or heat | Release build on a device + device log; never the Simulator |

Save verbose output to a log, preserve the command's exit status, and inspect its failure summary.
A grep result is not a build/test result. Use unique log paths for concurrent runs.

## Parallel agents

- For authorized parallel work, use an isolated worktree and private DerivedData per agent.
  Build-output size varies; clean up owned temporary output when it is no longer needed.
- Use the repository's integration workflow. If a project generator owns `project.pbxproj`,
  regenerate after conflicts; otherwise resolve the Xcode project carefully and build it.
- Share a few simulator devices by UDID; wait for a busy one instead of erasing it.
- Route work by model capability: cheap/fast models for docs, log summaries, prompt lists;
  mid-tier for level authoring, tuning, HUD tweaks, merges and re-verification; the strongest for
  simulation, determinism and renderer architecture.
- Tests that pin absolute paths of the main checkout fail inside worktrees — make paths relative.

## Evidence honesty

Every report states what was checked and with which command, and what kind of evidence it is:
source/tests, Simulator (functional/visual), or device (performance/thermal). A device-only fix is
"unconfirmed" until a device log shows it. "Builds" is not "works"; "works in the Simulator" is not
"runs at 60 fps".

## Device logs

Pull the on-device perf log **before** reinstalling or relaunching (see
`ios-game-device-telemetry`). Follow the task's device authorization and preserve active sessions.
When launch is authorized, proceed on the available device; report a locked/unavailable device
without claiming a successful launch. Verify installation and process launch separately.

## Secrets

API keys for asset generation (TTS, SFX, images) live in the OS keychain and are read at runtime
by the generator script (`security find-generic-password -s <name> -w`); never printed, logged or
committed.

## Asset generation

Keep generator prompts, source files and output hashes next to generated assets; keep licensing
notes with sources. Follow the project's licensing and asset-selection requirements; distinguish
provenance records from any approvals actually needed to ship an asset.
