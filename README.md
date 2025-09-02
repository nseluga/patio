# Patio Sports Betting App

A full-stack sports betting application where users can place bets against other players (PvP) or the CPU, track ongoing bets, and resolve results in real time. Built with **React (frontend)** and **Flask + Supabase/Postgres (backend)**.

---

## 🚀 Features

- **Authentication**
  - JWT-based user authentication (`auth.py`).
  - User context in React to manage login state.

- **Betting System**
  - **PvP Bets** (`PvP.js`): Players create and accept bets against each other.
  - **CPU Bets** (`CPU.js`): CPU-generated bets with automated odds (~4% house edge).
  - **Ongoing Bets** (`Ongoing.js`): Tracks accepted bets, allows stat entry, and confirms matches.

- **Bet Types**
  - **Shots Made**
  - **Score**
  - **Other (custom lines/stat conditions)**
  - Supports multiple games (Caps, Beerball, Pong, Campus Golf, etc.) and game sizes (1v1, 2v2, 3v3).

- **Database Integration**
  - Flask backend (`app.py`) with Supabase/Postgres models (`models.py`).
  - Stores bets, submissions, and user/player stats.

- **UI/UX**
  - Styled bet cards, modal inputs, and confirmation popups.
  - Bottom navigation shared across pages (`BottomNav`).
  - Background images and betcard textures for immersive UI.

---

## 🛠️ Tech Stack

**Frontend**
- React + Hooks (`useState`, `useEffect`, `useContext`)
- Context API for user auth
- Axios API wrapper (`api.js`)
- CSS modules for styling (reuses `PvP.css`)

**Backend**
- Python Flask (`app.py`)
- JWT Authentication (`auth.py`)
- SQLAlchemy ORM models (`models.py`)
- Supabase/Postgres database

---

## 📂 Project Structure

