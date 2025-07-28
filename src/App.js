// Import routing tools and page components
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
} from "react-router-dom";
import { useState, useEffect } from "react";
import Messages from "./pages/Messages";
import Leaderboard from "./pages/Leaderboard";
import PvP from "./pages/PvP";
import Ongoing from "./pages/Ongoing";
import CPU from "./pages/CPU";
import Profile from "./pages/Profile";
import Login from "./pages/Login";
import Register from "./pages/Register";
import UserContext from "./UserContext"; // import context
import "./App.css"; // Global styles

function App() {
  const [user, setUser] = useState(null); // global player info

  const [ongoingBets, setOngoingBets] = useState(() => {
    const saved = localStorage.getItem("ongoingBets");
    return saved ? JSON.parse(saved) : [];
  });

  useEffect(() => {
    const fetchUserFromBackend = async (token) => {
      try {
        const res = await fetch("http://localhost:5000/me", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) throw new Error("Failed to fetch profile");

        const data = await res.json();

        const savedId = localStorage.getItem("playerId");
        const savedUsername = localStorage.getItem("username");

        setUser({
          playerId: parseInt(savedId),
          username: savedUsername,
          token,
          ...data, // ✅ Merge in caps_balance, bets_won, bets_played, etc.
        });
        
      } catch (err) {
        console.error("Error fetching full profile:", err);
        setUser(null);
      }
    };

    const savedId = localStorage.getItem("playerId");
    const savedUsername = localStorage.getItem("username");
    const savedToken = localStorage.getItem("token");

    if (savedId && savedUsername && savedToken) {
      const parsedId = parseInt(savedId);
      if (!isNaN(parsedId)) {
        // Initially set basic info
        setUser({
          playerId: parsedId,
          username: savedUsername,
          token: savedToken,
        });

        // 🔁 Then fetch full stats from backend
        fetchUserFromBackend(savedToken);
      } else {
        console.warn("⚠️ playerId could not be parsed:", savedId);
      }
    }
  }, []);

  const addOngoingBet = (newBet) => {
    const local = localStorage.getItem("ongoingBets");
    const current = local ? JSON.parse(local) : [];

    const currentUserId = user?.playerId;

    const alreadyExists = current.some(
      (bet) => bet?.id === newBet?.id && bet?.accepterId === currentUserId
    );
    if (alreadyExists) return;

    const updated = [...current, { ...newBet, accepterId: currentUserId }];
    localStorage.setItem("ongoingBets", JSON.stringify(updated));
    setOngoingBets(updated);
  };

  return (
    <UserContext.Provider value={{ user, setUser }}>
      <Router>
        <Routes>
          <Route
            path="/"
            element={<Navigate to={user ? "/pvp" : "/login"} />}
          />

          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {user && (
            <>
              <Route
                path="/pvp"
                element={<PvP addOngoingBet={addOngoingBet} />}
              />
              <Route path="/messages" element={<Messages />} />
              <Route path="/leaderboard" element={<Leaderboard />} />
              <Route
                path="/ongoing"
                element={
                  <Ongoing
                    ongoingBets={ongoingBets}
                    setOngoingBets={setOngoingBets}
                  />
                }
              />
              <Route
                path="/house"
                element={<CPU addOngoingBet={addOngoingBet} />}
              />
              <Route path="/profile" element={<Profile />} />
            </>
          )}

          <Route
            path="*"
            element={<Navigate to={user ? "/pvp" : "/login"} />}
          />
        </Routes>
      </Router>
    </UserContext.Provider>
  );
}

export default App;
