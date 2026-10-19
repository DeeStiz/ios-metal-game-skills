---
name: ios-game-feel
description: Add combat and destruction feel to an iOS game without breaking determinism - recoil patterns, view-model springs, camera shake, slow motion, Core Haptics, layered and distance-delayed audio, readable enemy telegraphs, and accessibility options. Use when a game feels flat or unfair, when adding haptics or impact audio, or when enemies feel like they shoot without warning.
license: MIT
---

# Game feel that stays deterministic

Split every feel feature into **authority** (affects outcomes, runs on the fixed step,
checkpointed) and **presentation** (visual/audio/haptic only, runs on the frame delta, never feeds
back).

## Weapons

- **Recoil** is authority: authored per-shot patterns (climb with a learnable drift right then
  left, loop the last 8 shots), a short climb window then exponential recovery, scaled by ADS.
  Runs on the fixed step so replays match.
- **View-model kick and sway** are presentation: critically damped springs integrated on the
  renderer's own delta, triggered by a fire serial in the snapshot. A small camera pitch punch is
  visual only and never feeds aim.
- Ejected casings and surface-specific impact ejecta (splinters, drywall, glass, chips, soil,
  sparks) are render FX.
- Hit markers, a distinct kill confirm, and damage-direction arcs toward the attacker — each with
  its own sound and haptic.

## Camera and time

- Blast/collapse shake with distance falloff, scaled by a **Reduce camera shake** setting and the
  system **Reduce Motion** flag.
- Slow motion for big moments (chain reactions, a collapse in view): stretch the *authority
  timeline* — the same fixed ticks arrive less often — so outcomes never change. Never start it,
  and cancel it, when the player was recently hit, is low on health, or is in combat.

## Haptics (Core Haptics)

Author `CHHapticPattern`s per weapon fire, reload, placing and detonating charges, near/far blasts
(scaled by distance, **delayed by the speed of sound**), collapse rumble, landing and player hits.
Settings: on/off and intensity. Route through one service so the session can stop all players on
teardown.

## Audio

- Layer blasts: crack + body + debris tail, plus a distant rumble with distance low-pass and
  speed-of-sound delay.
- Random variation per play (never repeat the previous file), ±0.5 semitone, 0 to −1 dB.
- Looping beds (fire, flood) whose gain/pan/low-pass follow hazard energy near the listener,
  updated ~10 Hz.
- Reverb by environment (open, street, interior, tunnel); duck the world mix for big moments.
- Keep a procedural synth fallback for any missing sample, and a self-test env flag that plays
  every cue once.
- Generated SFX/voice (e.g. ElevenLabs): keep the API key in the OS keychain, read at runtime by
  the generator script, never in the repo or logs.

## Readable enemies (fairness)

- An attack fires only after its firing solution has held for a **telegraph lead** per role;
  checkpoint the timer. Publish `ticksUntilAttack` in the snapshot.
- Presentation turns that into grenade wind-up and arc preview, aim glint, suppressive-fire lanes,
  alert icons, and spoken callouts with subtitles.
- Bound sight/attack ranges by **on-phone readability** (roughly 38–46 m sight, 28–36 m attack in
  a first-person phone game); calm patrols shouldn't spot a player at the insertion point.
- Navigation: grid A* over a level-derived grid inflated by the agent capsule, validated against
  live collision; an unreachable goal gets a rejection and backoff, never a silent intent change.
  Log every replan behind a debug flag.
- Reactive behaviour sells the world: guards beat out fires near their posts, back away from
  creaking structures, call out vehicles, alarms and collapses.
