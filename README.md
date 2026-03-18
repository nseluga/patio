# 🍺 Patio — Sports Betting App

A full-stack social sports betting app for backyard games (Caps, Beerball, Pong, Campus Golf, and more). Place bets against friends (PvP) or the House (CPU), track live bets, and climb the leaderboard.

---

## 🚀 Features

- **Authentication** — JWT-based login & registration
- **PvP Bets** — Create and accept bets against other players
- **CPU/House Bets** — Automated odds with ~4% house edge
- **Ongoing Bets** — Track accepted bets, enter stats, confirm results
- **Leaderboard** — See who's up and who owes
- **Profile** — Stats, bet history, profile photo

---

## 🛠️ Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React 19, React Router, Axios, Lucide React |
| Backend | Python Flask, JWT, SQLAlchemy |
| Database | Supabase (Postgres) |
| Deployment | Vercel (frontend) + Render (backend) |

---

## ⚙️ Environment Variables

Copy `.env.example` and fill in your values.

**Backend** (set in Render dashboard):
```
DATABASE_URL=postgresql://your-supabase-connection-string
SECRET_KEY=your-secure-random-secret-key
FRONTEND_URL=https://your-app.vercel.app
```

**Frontend** (set in Vercel dashboard):
```
REACT_APP_API_URL=https://your-backend.onrender.com
```

---

## 🖥️ Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
flask --app app run --port 5001
```

**Frontend:**
```bash
npm install
npm start
```

---

## 🌐 Deployment

**Backend → [Render.com](https://render.com)**
1. Push this repo to GitHub
2. New Web Service → connect repo
3. Build command: `pip install -r backend/requirements.txt`
4. Start command: `flask --app backend/app run --host=0.0.0.0 --port=$PORT`
5. Add environment variables in Render dashboard

**Frontend → [Vercel.com](https://vercel.com)**
1. New Project → import from GitHub
2. Framework: Create React App (auto-detected)
3. Add `REACT_APP_API_URL` environment variable pointing to your Render URL
4. Deploy

