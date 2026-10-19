---
name: game-center-integration
description: Integrate Game Center leaderboards and achievements into an iOS game robustly - a single ID catalog with tests, an offline outbox, recurring daily leaderboards aligned to UTC, non-intrusive sign-in, and the App Store Connect setup steps. Use when adding Game Center, when scores are not appearing, or when preparing leaderboards and achievements in App Store Connect.
license: MIT
---

# Game Center integration

## Code

- **One catalog** (`GameCenterCatalog.swift`) defines every leaderboard and achievement ID,
  points, and title. A unit test checks: IDs unique, each achievement ≤ 100 points,
  total points ≤ 1000, metadata meets current service limits, and every scored level maps to a board. The setup doc lists the same IDs.
- **Entitlement** `com.apple.developer.game-center` + link `GameKit`.
- **Sign-in**: authenticate when menus appear, but don't push the sign-in view controller over
  your UI on your own. If GameKit offers one, show a "Tap to sign in" chip and present it on tap.
  Signed out, offline, or "game not recognized" must never block play.
- **Offline outbox** persisted atomically with bounded retries:
  - key every pending record by authenticated gamePlayerID, leaderboard/achievement ID and
    occurrence where applicable. Recheck identity before submission and on completion; account
    switches must not flush or clear another player's queue;
  - define signed-out behavior explicitly: keep local-only progress separate, or require an
    explicit policy for associating it with a later account. Never silently reassign ownership;
  - classic boards keep the best pending score according to that board's high/low sort order;
  - achievements coalesce to the highest pending percentage per player. Remove only the
    accepted revision so newer progress survives an in-flight completion;
  - flush after sign-in and after every completed mission;
  - a recurring (daily) board only accepts a score during its own occurrence, so drop stale
    daily scores instead of retrying forever.
- Report partial progress (`percentComplete`) for streak/rank/collection achievements.
- An env flag disables Game Center for automation.
- Log `GAME_CENTER state=signedIn`, `flushed scores=n/n achievements=m/m`.

## Recurring daily leaderboard

If your daily challenge changes at 00:00 UTC, set the recurring board to start at a fixed date
00:00 **UTC** (the form may ask for local time — convert), duration 1 day, restart every 1 day.
An application-defined `context` may carry the day number; it does not select an occurrence or
enforce scoring rules server-side. If the product permits one scored attempt, submit only that
attempt and keep practice separate. Reject stale queued occurrences before submitting.

## App Store Connect checklist

1. Identifier has Game Center capability (automatic signing usually adds it).
2. App → Services → Game Center → enable, single-game (not a group) unless you share boards.
3. Create leaderboards with the required score type, high/low sort direction, range, localized
   name and suffix. Racing times and high scores need different ordering.
4. Create achievements with points, visibility and localized pre-/post-earned descriptions.
   Apple currently requires a 1024×1024 RGB JPEG/PNG image at 72 ppi or higher.
5. Submit new/modified components for review. The first components must accompany an app
   version; later components may be submitted independently. Configure the app version and
   component availability as required, and verify their actual review/live state.
6. Test with Game Center accounts and development/TestFlight builds using Apple's current
   setup workflow. Game Center prerelease testing shares the production server environment;
   StoreKit sandbox accounts are a different system. Use separate test configuration when
   test data must not affect released boards. Diagnose actual GameKit errors; do not classify
   every authentication/configuration/network failure as "game not recognized".

Keep board IDs stable when mission names/order change. Create a new board only for an intentional
scoring identity change, with a migration and release plan.

Sources: [Game Center testing](https://developer.apple.com/help/app-store-connect/configure-game-center/overview-of-testing-game-center/),
[achievement limits](https://developer.apple.com/help/app-store-connect/reference/game-center/achievements),
[player authentication](https://developer.apple.com/documentation/gamekit/authenticating-a-player),
[component submission](https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/submit-game-center-components/).
Check current App Store Connect requirements before setup; UI labels and submission rules evolve.
