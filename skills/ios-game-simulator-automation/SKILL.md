---
name: ios-game-simulator-automation
description: Build, install, launch and capture an iOS game in the Simulator unattended - env-var debug knobs, grep-able log lines, stop-on-log-match, screenshots and video, scripted autopilot playthroughs, and sharing simulators between parallel agents. Use when an agent needs to run the game to check a change, reproduce a bug from a fixed camera, play a level end to end, or set up smoke tests.
license: MIT
---

# Simulator automation for games

Agents can't tap your game. Make the game drive itself from environment variables and report
through log lines, then a single script can build → install → launch → wait → capture.

## Script

`scripts/sim_smoke.sh` (in this skill) does it generically:

```bash
SCHEME=MyGame BUNDLE_ID=com.example.mygame APP_ENV_PREFIX=MYGAME_ \
SIMULATOR=<UDID> scripts/sim_smoke.sh /tmp/smoke DEBUG_SPAWN=10,20,90 MYGAME_MUTE_AUDIO=1
```

- Release build for the generic Simulator destination into a private DerivedData
  (`DERIVED_DATA=/tmp/DD-<agent>` when several agents share a Mac).
- Uninstall + install for a clean container.
- Passes `KEY=VALUE` pairs to the app via `SIMCTL_CHILD_KEY=VALUE`.
- `--until REGEX` stops as soon as the console log matches (e.g. `MISSION outcome=`), `--wait S`
  is the upper bound; `--video S` records instead of a screenshot.
- Writes `OUT.log`, `OUT.png` / `OUT.mp4`, and `OUT.build.log` (prints only `error:` lines).

## Make the game automatable

Read every knob in one place, with one prefix, and **echo the ones that arrived** at launch
(`DEBUG_ROUTE start noHostiles=1 immortal=0`). A misspelled knob that is silently ignored wastes
whole runs.

Useful knobs:

| Knob | Purpose |
|---|---|
| `LEVEL=<path>` | load a level file, skip menus |
| `SKIP_MENU=1` | load the default scene directly |
| `DEBUG_SPAWN=x,z[,yaw[,pitch]]` | grounded camera/insertion override for repeatable views |
| `DEBUG_NO_HOSTILES=1`, `DEBUG_IMMORTAL=1` | capture shortcuts — never for "fair" playthroughs |
| `DEBUG_FIRE=tool,count,delay,interval` | auto-fire for destruction/perf scenarios |
| `DEBUG_ROUTE=…` | autopilot (below) |
| `MUTE_AUDIO=1` | default for agent runs |
| `MENU=settings` etc. | open a specific screen for UI screenshots |
| `TIME_OF_DAY=18.0`, weather overrides | reproduce lighting bugs |

Launch-argument equivalents (`-MyGameMuteAudio`) help XCUITest.

## Log-line protocol

Prefix machine-readable lines with an upper-case tag and `key=value` fields:
`LEVEL_OBJECTIVE id=gen state=done`, `LEVEL_MISSION outcome=completed`, `DEBUG_ROUTE stuck at=…`.
Agents grep these; humans can still read them. Print to both the console (for `simctl launch
--console-pty`) and a log file in Documents (for devices).

## Autopilot playthroughs

A scripted route string, e.g.
`DEBUG_ROUTE="40,-38;use:11.8,20.8;throw:50,33;shoot:enemy.3;climb:ladder.1;-3,-45,8"`:

- path-find (A* over a grid built from the level: slope, deep water, footprints, trunks, plus
  live colliders at body height, re-stamped after explosions);
- stuck detection (a second without progress → learn the obstacle, back off, replan; accept the
  closest reachable spot after 3 pins near the goal);
- use the **real** player actions (equip, place, detonate, throw) so it tests the game, not a
  cheat path; solve grenade aim by forward-simulating the real projectile;
- human-like combat: reaction delay 0.25–0.45 s, aim noise, engage ranges per weapon;
- per-step timeouts, and a `complete` / `outcome=` line to stop on.

A level isn't done until a fair autopilot run (no immortal, no-hostiles or teleport shortcuts)
logs `outcome=completed`. Keep each level's route in a JSON file next to the levels.

## Sharing simulators

Reuse a few named simulator slots instead of creating one per task; check
`xcrun simctl list devices --json` for state; wait for a busy slot rather than shutting it down;
never erase a device as routine setup. Run XCTest with `-parallel-testing-enabled NO` to avoid
clone devices.

## Evidence limits

Simulator output is functional and visual evidence only — never frame time, thermal or
pacing evidence. Say which you have when reporting.
