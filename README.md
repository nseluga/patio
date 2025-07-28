# Patio Sports Betting: Social Sports Entertainment Platform

Patio Sports Betting (PSB) is a full-stack web application that simulates a peer-vs-peer and player-vs-CPU sportsbook for casual games with friends like Caps and Pong. Players can post bets, accept "caps" wagers from others, track outcomes, and see who reigns supreme — all while building gameplay data for future analysis.

---

## Features

- **Multi-Game Support:** Bet on various playground-style games (Caps, Pong, Campus Golf, and more).
- **PvP Bets:** Create and accept bets against other users with customizable lines, amounts, and game types.
- **CPU Bets:** Generated automatically using backend player stats with a built-in house edge (~4%). Each user can accept once.
- **Ongoing Bets Tab:** Track accepted bets, enter post-game stats, and confirm results with peer verification.
- **Stat-Driven Match Logic:** Bet resolutions rely on exact player names, stats, and outcomes to confirm match integrity.
- **Player Analytics:** CPU logic leverages historical gameplay data with game-type and team-size filters to build fair matchups.

---

## Tech Stack

**Frontend:**  
- React (Hooks, Context API)  
- CSS for animations + responsive UI  
- Axios-based API calls with auth headers

**Backend:**  
- Flask (Python)  
- PostgreSQL via Supabase  
- JWT-based auth system  
- Modular CPU bet logic for each game

---

## Sports Analytics Emphasis

This project is built with analytics in mind:
- Each bet submission logs gameplay data (e.g., shots made, scores) for named players.
- A growing database of stats supports advanced CPU matchup logic.
- Designed for future expansion into predictive modeling and win probability estimation.

---


## Auth and User Flow

- Users register and receive 500 starter "caps".
- Login returns a JWT token stored in localStorage.
- Routes and actions are protected with auth headers.

---

## Dev Notes

- CPU admin is hardcoded as `playerId = 0` and has special access to bet generation tools.
- All bets use a standardized schema via `createStandardBet()` for frontend consistency.
- Match confirmation uses both backend and frontend validations to ensure fairness.

---
