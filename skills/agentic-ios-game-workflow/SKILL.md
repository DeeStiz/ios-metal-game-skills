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
Point at docs for depth. Docs are reference, not gates.

**Don't** add mandatory skill loading, golden-hash rebaselines, approval records, evidence
matrices, per-change ledgers or source-text policing. When a project accumulates a long
AGENTS.md, a "skill contract", dozens of source-guard test files and approval paperwork for
assets, every change paid for it and agents spent their effort satisfying rituals. Removing it
made agents faster *and* the remaining tests more meaningful. Add a check only for a concrete
recurring defect.

## Tests that help agents

- Test **properties**, not frozen content: save/restore round-trips, equivalent paths agree,
  read-only queries don't mutate, a changed input invalidates a cache, determinism per seed.
- Avoid tests that parse source text, pin exact coordinates/counts, or compare golden hashes of
  content — they fail on every legitimate edit and teach agents to "update the number".
- Shared expensive fixtures (compiled scene, terrain) make `swift test --parallel` slow because
  each test process rebuilds them. `scripts/run_tests.py` (this skill) builds once and runs whole
  classes in a few long-lived `xctest` shards, balanced by recorded timings; `--fast` gives a
  ~13 s incremental optimized rebuild; logs go to `.build/test-shards/`. Filter by class name
  substring for focused checks.

## Pick the check that matches the change

| Change | Check |
|---|---|
| Engine logic | focused engine test classes |
| Renderer / shaders | an app build (SwiftPM tests don't compile them) + a Simulator capture if visuals matter |
| `project.yml` / added or renamed app files | `xcodegen generate`, then app build |
| Level data | level CLI `validate` + `check`, then an autopilot run |
| Visual change | before/after captures from a fixed camera, or the VRT harness |
| Performance or heat | Release build on a device + device log; never the Simulator |

Send verbose build/test output to files and grep (`> /tmp/build.log 2>&1; grep error:`).

## Parallel agents

- One **git worktree per agent** and a private `-derivedDataPath /tmp/DD-<name>` (each is
  2–3 GB; delete when merged).
- Merge with `git merge`; on a `project.pbxproj` conflict regenerate the project, never hand-edit.
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
`ios-game-device-telemetry`). Install builds to the phone, but only launch when the person asks —
phones are often locked.

## Secrets

API keys for asset generation (TTS, SFX, images) live in the OS keychain and are read at runtime
by the generator script (`security find-generic-password -s <name> -w`); never printed, logged or
committed.

## Asset generation

Keep generator prompts, source files and output hashes next to generated assets; keep licensing
notes with sources. Make approval metadata informational — explicit resource selection decides
what ships.
