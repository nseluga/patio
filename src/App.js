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
import api from "./api"; // make sure api.js is set up correctly
import "./App.css"; // Global styles

function App() {
  const [user, setUser] = useState(null); // global player info

  const [ongoingBets, setOngoingBets] = useState(() => {
    const saved = localStorage.getItem("ongoingBets");
    return saved ? JSON.parse(saved) : [];
  });

  useEffect(() => {
    const savedId = localStorage.getItem("playerId");
    const savedUsername = localStorage.getItem("username");

    if (savedId && savedUsername) {
      setUser({ playerId: savedId, username: savedUsername });
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
