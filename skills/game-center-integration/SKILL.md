---
name: game-center-integration
description: Integrate Game Center leaderboards and achievements into an iOS game robustly - a single ID catalog with tests, an offline outbox, recurring daily leaderboards aligned to UTC, non-intrusive sign-in, and the App Store Connect setup steps. Use when adding Game Center, when scores are not appearing, or when preparing leaderboards and achievements in App Store Connect.
license: MIT
---

# Game Center integration

## Code

- **One catalog** (`GameCenterCatalog.swift`) defines every leaderboard and achievement ID,
  points, and title. A unit test checks: IDs unique, total points ≤ 1000, titles ≤ 30
  characters, every scored level maps to a board. The setup doc lists the same IDs.
- **Entitlement** `com.apple.developer.game-center` + link `GameKit`.
- **Sign-in**: authenticate when menus appear, but don't push the sign-in view controller over
  your UI on your own. If GameKit offers one, show a "Tap to sign in" chip and present it on tap.
  Signed out, offline, or "game not recognized" must never block play.
- **Offline outbox** persisted as JSON in Documents:
  - classic boards keep the best pending score;
  - achievements keep the highest percentage, never resent after acceptance;
  - flush after sign-in and after every completed mission;
  - a recurring (daily) board only accepts a score during its own occurrence, so drop stale
    daily scores instead of retrying forever.
- Report partial progress (`percentComplete`) for streak/rank/collection achievements.
- An env flag disables Game Center for automation.
- Log `GAME_CENTER state=signedIn`, `flushed scores=n/n achievements=m/m`.

## Recurring daily leaderboard

If your daily challenge changes at 00:00 UTC, set the recurring board to start at a fixed date
00:00 **UTC** (the form may ask for local time — convert), duration 1 day, restart every 1 day.
Submit with `context` = day number since your epoch. Submit only the day's scored attempt, never
practice runs.

## App Store Connect checklist

1. Identifier has Game Center capability (automatic signing usually adds it).
2. App → Services → Game Center → enable, single-game (not a group) unless you share boards.
3. Create leaderboards: integer, high-to-low, best score, sensible range, localized name and
   suffix.
4. Create achievements: points, hidden flag, pre-/post-earned descriptions, **a 512² or 1024²
   image (required to save)**.
5. Add every leaderboard and achievement to the app version's Game Center section — otherwise
   they don't go live.
6. Test with a sandbox account (Settings → Developer → Sandbox Account) or TestFlight. Until step
   2–5 are done, flushes fail with "game not recognized" and stay queued.

Renaming or renumbering a mission changes its board ID — add the new board in App Store Connect
first.
