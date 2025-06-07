// Import routing tools and page components
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import { useState } from "react";
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

// Main app component with route definitions
function App() {
  const [user, setUser] = useState(null); // global player info

  const [ongoingBets, setOngoingBets] = useState(() => {
    const saved = localStorage.getItem("ongoingBets");
    return saved ? JSON.parse(saved) : [];
  });

  // Add a bet to ongoing and sync to localStorage
  const addOngoingBet = (newBet) => {
    const local = localStorage.getItem("ongoingBets");
    const current = local ? JSON.parse(local) : [];
  
    const alreadyExists = current.some((bet) => bet.id === newBet.id);
    if (alreadyExists) return;
  
    const updated = [...current, newBet];
    localStorage.setItem("ongoingBets", JSON.stringify(updated));
    setOngoingBets(updated); // sync React state
  };

  return (
    <UserContext.Provider value={{ user, setUser }}>
      {" "}
      {/* wrap entire app */}
      <Router>
        <Routes>
          {/* Home route defaults to PvP */}
          <Route path="/" element={<PvP addOngoingBet={addOngoingBet} />} />

          {/* App page routes */}
          <Route path="/pvp" element={<PvP addOngoingBet={addOngoingBet} />} />
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
          <Route path="/house" element={<CPU addOngoingBet={addOngoingBet} />} />
          <Route path="/profile" element={<Profile />} />

          {/* Auth routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Routes>
      </Router>
    </UserContext.Provider>
  );
}

export default App;
