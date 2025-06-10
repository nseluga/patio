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
import api from "./api"; // make sure api.js is set up correctly
import "./App.css"; // Global styles

// Main app component with route definitions
function App() {
  const [user, setUser] = useState(null); // global player info

  const [ongoingBets, setOngoingBets] = useState([]);


// Save a new bet to the database and update React state
const addOngoingBet = async (newBet) => {
  console.log("📤 Sending bet to backend:", newBet);
  try {
    // Send POST request to create the bet in the backend
    const res = await api.post("/bets", {
      game_type: newBet.gameType,
      subject: newBet.subject,
      line: newBet.line
    });

    // Log success response with new bet ID
    console.log("✅ Bet saved to DB:", res.data);

    // Update state with the new bet (including its DB ID)
    setOngoingBets((prev) => [...prev, { ...newBet, id: res.data.bet_id }]);
  } catch (err) {
    // Log any error during bet creation
    console.error("❌ Failed to save bet:", err);
  }
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
