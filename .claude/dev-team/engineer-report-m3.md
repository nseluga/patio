# Engineer Report — Stage M, Item M.3

**Branch:** `conversion`
**Task:** Port the five main screens from web React (JSX + CSS) to React Native (Expo) primitives.
**Status:** Complete.

## Files changed / added

- `mobile/App.js` — Fixed bootstrap `playerId` bug: now reads `playerId` from SecureStore
  (`/me` does not return `id`) instead of `res.data.id`.
- `mobile/src/utils/timeUtils.js` — New. `formatTimeAgo()`, copied verbatim from web (pure JS).
- `mobile/src/utils/betCreation.js` — New. `createStandardBet()` factory, copied verbatim from web.
- `mobile/src/utils/acceptHandling.js` — New. AsyncStorage parity shim: `useAutoSaveBets` (no-op),
  `removeBetByIndex`, `acceptBetForCPU`, `acceptBetWithOngoing`.
- `mobile/src/assets/images/*` — Copied all 8 PNGs from `src/assets/images/`.
- `mobile/src/screens/Leaderboard.js` — GET `/leaderboard`, top-5 list via FlatList with medal emoji.
- `mobile/src/screens/Profile.js` — user stats, Log Out (clears SecureStore → setUser(null)),
  Cleanup Bets (POST `/cleanup_bets`), recent-bets list, ImageBackground(back1) + default avatar.
- `mobile/src/screens/PvP.js` — GET `/pvp_bets`, bet cards, ACCEPT (POST `/accept_bet/:id` with
  flipped lineType), dismiss, create-bet Modal with Picker dropdowns + Over/Under toggle, capsRefreshed banner.
- `mobile/src/screens/CPU.js` — GET `/cpu_bets`, bet cards, ACCEPT (POST `/accept_cpu_bet/:id`),
  CPU-admin (playerId===0) generate Modal posting to the six `/cpu/create_*` endpoints.
- `mobile/src/screens/Ongoing.js` — GET `/ongoing_bets`, dedup + admin filtering, Enter-Stats Modal
  with per-gameType inputs (Shots Made / Score team rows / Other), POST `/submit_stats/:id` then
  refetch, Help modal.
- `mobile/package.json` / `package-lock.json` — Added `@react-native-async-storage/async-storage`
  and `@react-native-picker/picker` via `npx expo install` (SDK-57 compatible versions).
- `PROGRESS.md` — M.3 flipped to done.

## Design decisions

- **Styling:** Each screen owns a co-located `StyleSheet.create({})`. The three bet screens
  (PvP/CPU/Ongoing) share an identical card visual language (matching the web `PvP.css` reuse) but
  keep independent style objects rather than a shared module, per the "styles co-located per file" rule.
- **`<select>` → Picker:** Used `@react-native-picker/picker` wrapped in a bordered `pickerWrap` view.
- **Over/Under radios → toggle buttons:** Two Pressables toggling `lineType` state.
- **Auth headers:** Removed all manual `Authorization` headers — the `api.js` interceptor attaches
  the token automatically.
- **addOngoingBet:** PvP and CPU are tab screens without props, so each defines a local
  `addOngoingBet()` that appends the accepted bet to an `ongoingBets` AsyncStorage array (dedup by id).
  Ongoing itself ignores this cache and fetches fresh from `/ongoing_bets` on mount — the cache is
  parity-only, matching the task guidance.
- **Ongoing submit simplification:** The web version did a large optimistic local mutation before the
  network call; I kept the authoritative path (POST `/submit_stats/:id` → refetch `/ongoing_bets`)
  and drove the "Match confirmed!" popup off the server's `res.data.match` flag. Behavior is
  equivalent and less state-fragile. Added a `submitting` lock to prevent double submits.
- **Temp bet id:** `create_bet` uses `Date.now().toString()` as a local key (no `uuid` dep); the
  server assigns the real id and PvP refetches on mount.
- **Validation:** Verified all five screens + utils + App.js parse via `@babel/preset-react`.

## Deferred / out of scope

- **Image upload / edit-photo** — skipped for MVP. Profile shows the static `defaultProfile.png` only;
  no file picker, no `FileReader`, no remove-photo flow.
- **Messages tab** — skipped. It is not one of the five MainTabs screens (BOARD/PvP/HOUSE/LIVE/ME)
  and had no navigation entry.
- Full babel/expo bundle was not run end-to-end (no simulator in this environment); syntax validated
  via standalone babel parse. Recommend a smoke run in Expo Go / simulator.

## Flags for next step (M.4 — web app retirement)

- The CRA app in `src/` (including `src/pages/`, `src/components/BottomNav`, all `*.css`, `uuid` dep)
  is now fully superseded by `mobile/` and is the target for M.4 removal/restructure.
- `src/utils/*` were duplicated into `mobile/src/utils/*`; the web copies can go with the web app.
- Confirm no backend endpoints are web-only before deleting `src/`.
