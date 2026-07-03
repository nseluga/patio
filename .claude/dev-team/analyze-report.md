# Analysis Report
**Task:** Assess structural changes needed to make Patio professionally launchable on the App Store, with the frontend converted from React web (CRA) to React Native
**Date:** 2026-07-02

## Relevant Files
- `PLAN.md` — current refactor plan; 100% backend/web-focused, zero mobile or App Store items; no stage started (per PROGRESS.md)
- `PROGRESS.md` — status tracker mirroring PLAN.md; must gain rows for any new stages
- `package.json` — CRA (`react-scripts` 5), React 19, `react-router-dom` 7, axios, lucide-react; `proxy` to :5001; all of this is web-only tooling that does not carry to RN
- `src/App.js` — `BrowserRouter` routing, auth guard, `localStorage` for token/playerId/username/ongoingBets, raw `fetch` to `/me` with a `:5000` fallback (port bug, PLAN 0.4c); `/me` is broken server-side (PLAN 0.6) — mobile app boot will depend on this route
- `src/api.js` — axios instance, `localStorage` token interceptor, `withCredentials: true` (cookie pattern irrelevant/unavailable on RN)
- `src/components/BottomNav.js` + `.css` — bottom navigation; maps 1:1 to a React Navigation bottom-tab navigator
- `src/pages/*.js` — 8 screens (~1,450 LOC total): Login, Register, PvP (311), CPU (244), Ongoing (464), Profile (158), Leaderboard (53), Messages (17-line stub); all DOM/JSX + CSS files/CSS modules — every one needs RN primitives + StyleSheet
- `src/utils/acceptHandling.js` — `localStorage`-as-source-of-truth for ongoing bets (PLAN 9.1 audit note); becomes AsyncStorage or (better) server-authoritative on mobile
- `src/utils/betCreation.js`, `src/utils/timeUtils.js` — pure JS, port unchanged
- `src/assets/images/*` — PNGs, reusable in RN
- `server.js` — dead Socket.IO chat server (PLAN X.2); irrelevant to mobile, should be cut
- `backend/app.py` (1,499 LOC), `backend/auth.py` — API the mobile app consumes; all PLAN Stage 0/5 security + money bugs become App Store blockers (can't ship a public app with unauthenticated destructive routes and double-payout)
- `Procfile` — starts Flask **dev server** (`flask run`) on Render; not production-grade for a public mobile launch (needs gunicorn)
- `public/manifest.json`, `public/index.html` — CRA web shell, retired after conversion

## Data Flow
- Boot: App.js reads `localStorage` token → `GET /me` (broken, PLAN 0.6) → sets `UserContext` → routes render behind auth guard
- Bets: pages call axios (`api.js`) → Flask routes in `app.py` → raw psycopg2 → Supabase Postgres; accepted bets mirrored into `localStorage` (`ongoingBets`) — client state diverges from server
- On RN this becomes: SecureStore token → axios with header auth (no cookies) → same Flask API over HTTPS (ATS requires TLS; Render provides it)

## Patterns to Follow
- Auth: JWT in `Authorization: Bearer` header via axios request interceptor — this pattern survives the RN port (swap `localStorage` → `expo-secure-store`)
- Global state: single `UserContext` provider, no Redux — PLAN explicitly defers Redux; keep Context in RN
- Screens are self-contained page files with co-located CSS — RN port should keep one-file-per-screen with co-located `StyleSheet.create`
- API base URL from env (`REACT_APP_API_URL`) — RN equivalent is `app.config.js` extra / `EXPO_PUBLIC_API_URL`

## Likely Changes
- New `mobile/` Expo app (or repo-root conversion): React Navigation (auth stack + bottom tabs replacing BrowserRouter/BottomNav), all 8 screens re-rendered with RN primitives, StyleSheet replacing 7 CSS files
- `api.js` → RN version: drop `withCredentials`, token from SecureStore, base URL from Expo config
- `App.js` auth-bootstrap logic → RN root: SecureStore read + `/me` fetch (requires PLAN 0.6 fixed first — boot dependency)
- `acceptHandling.js` — AsyncStorage shim short-term; server-authoritative ongoing-bets endpoint long-term (existing 9.1 audit note)
- Backend additions for App Store compliance: account-deletion endpoint (App Review 5.1.1(v) mandates in-app account deletion), gunicorn in Procfile/requirements, token expiry/refresh story
- New launch stage: bundle ID + icons/splash, privacy policy + App Privacy labels, age rating (simulated gambling → 17+), EAS Build → TestFlight → App Store submission
- PLAN.md/PROGRESS.md restructured: RN conversion stages prepended, Stage 9.1 (web axios/services) folded into the RN port, App Store launch stage appended after security/money stages
- Retire: CRA scaffolding (`react-scripts`, `public/`, `proxy`), `server.js`

## Risks
- App Review 5.3 (gambling): app is betting-framed; virtual currency with **no purchase and no cash-out** avoids licensing requirements, but copy/metadata must never imply real-money wagering; expect "Simulated Gambling" age rating (17+)
- App Review 5.1.1(v): account creation ⇒ in-app account deletion is mandatory — backend has no such endpoint today
- Shipping publicly multiplies the existing PLAN Stage 0/5 bugs: unauthenticated `/cleanup_bets`, forged-identity bets, double-payout — these must gate submission, so App Store submission cannot literally be first even though RN conversion can
- Broken `/me` (0.6) is a hard boot dependency for the mobile app — the RN stage must pull it forward or land it first
- `withCredentials`/cookie decisions in PLAN 9.1's audit note are moot on RN — header token + SecureStore is the right pattern; don't build an httpOnly-cookie flow
- React 19 + RN version matrix: pin via current Expo SDK rather than hand-rolling react-native init
- CORS scoping (2.2) is a browser concept — native clients send no Origin; keep it only for any remaining web surface
- Flask dev server in Procfile will fall over under real App Store traffic — gunicorn swap is cheap and required
