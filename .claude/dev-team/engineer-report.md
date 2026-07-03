# Engineer Report — M.1 + M.2

**Branch:** conversion
**Date:** 2026-07-03
**Commits:** 35d6a17 (M.1), 2752114 (M.2)

---

## Files Changed

- `mobile/` — new Expo SDK 57 app (blank template, no separate git repo — answered yes to "skip git init" prompt)
- `mobile/app.config.js` — exposes `apiUrl` via `extra.apiUrl`, sourced from `EXPO_PUBLIC_API_URL` env var
- `mobile/App.js` — full navigation shell + auth bootstrap (ActivityIndicator loading state, SecureStore token read → `/me` call → populate UserContext)
- `mobile/src/UserContext.js` — `createContext(null)`, exported as default
- `mobile/src/api.js` — axios instance with `baseURL` from `Constants.expoConfig.extra.apiUrl`, request interceptor reads token from `SecureStore.getItemAsync('token')`
- `mobile/src/screens/Login.js` — functional screen: POST `/login`, SecureStore persistence, setUser in context, navigate implicitly via context state change
- `mobile/src/screens/Register.js` — functional screen: POST `/register`, navigate to Login on success
- `mobile/src/screens/PvP.js` — placeholder
- `mobile/src/screens/CPU.js` — placeholder (renders "House")
- `mobile/src/screens/Ongoing.js` — placeholder
- `mobile/src/screens/Leaderboard.js` — placeholder
- `mobile/src/screens/Profile.js` — placeholder
- `backend/auth.py` — fixed `/me` handler (strip Bearer prefix, correct column names, read pvp stats from players table)
- `PROGRESS.md` — updated M.1/M.2 status rows and summary

---

## Design Decisions

- **Auth navigation driven by UserContext state, not navigation.navigate('MainTabs')**: Login sets `setUser(userObj)` and App.js re-renders to swap AuthStack → MainTabs automatically. This avoids having the Login screen know about the root navigator shape; the context is the authority on auth state.

- **SecureStore.deleteItemAsync on /me failure at bootstrap**: if the stored token is expired or invalid, we clear it immediately so the next launch goes straight to Login rather than hanging on a 401 loop. This is the correct fail-fast pattern for a persisted session.

- **No auto-login logic inside Login.js (unlike web version)**: the web Login.js ran a useEffect to attempt token restoration. In RN, App.js owns bootstrap entirely — Login is never mounted when a valid session exists. This avoids duplicating the bootstrap path.

- **`replace_all` avoided on /me fix in auth.py**: the dead `bets` Blueprint below the `/me` handler was intentionally left untouched — 0.3 in PLAN.md owns its deletion. Editing only the `/me` function block keeps M.2's diff minimal and 0.3 still meaningful.

- **lucide-react-native icons over custom SVGs**: lucide-react-native is the RN sibling of the lucide-react package used in the web app, so icon names are identical. Makes M.3 icon porting mechanical.

- **KeyboardAvoidingView in Login/Register**: iOS keyboard pushes inputs off-screen without it. `behavior: 'padding'` on iOS, `'height'` on Android is the standard Expo pattern.

- **`mobile/` subdirectory, not repo root**: keeps the CRA app in `src/` fully intact per the M.1 requirement. The root `package.json` and CRA toolchain are untouched.

---

## Deferred / Out of Scope

- The dead `bets` Blueprint in `backend/auth.py` (lines 165–219) — deferred to 0.3 per PLAN.md.
- `capsRefreshed` handling in mobile Login: stored to SecureStore but no UI uses it yet — deferred to M.3/Profile screen port.
- Logout: no logout button exists yet — deferred to M.3 Profile screen (where the web app put it).
- `app.json` still exists alongside `app.config.js` — Expo merges them; the static `app.json` has the SDK/platform config. No conflict, but M.4 can consolidate.

---

## Flags for Next Engineer (M.3)

- **M.3 is tagged --opus in PLAN.md**: ~1,300 LOC across 5 screens, layout re-thinking for mobile viewports. Recommend Opus model.
- **Port order per plan**: Leaderboard → Profile → PvP → CPU → Ongoing (simplest to most complex).
- **Profile needs a logout action**: call `SecureStore.deleteItemAsync('token')` then `setUser(null)` — App.js re-renders to AuthStack automatically. No `navigation.navigate` needed.
- **`acceptHandling.js` swap**: replace `localStorage` with `AsyncStorage` as a parity shim only — server-authoritative state is Stage 9 (9.1), do not redesign in M.3.
- **`betCreation.js` and `timeUtils.js`** are pure JS — copy unchanged, no RN primitives needed.
- **Icon names already confirmed**: `Swords`, `Home`, `Clock`, `Trophy`, `User` all exist in `lucide-react-native` (same names as web lucide-react).
- **`window.confirm`/`alert`** → `Alert.alert` from `react-native`. Messages tab: skip entirely per X.2 resolution.
