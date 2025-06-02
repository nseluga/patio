// Import routing tools and page components
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Messages from "./pages/Messages";
import Leaderboard from './pages/Leaderboard';
import PvP from './pages/PvP';
import Ongoing from './pages/Ongoing';
import CPU from './pages/CPU';
import Profile from './pages/Profile';
import Login from './pages/Login';
import Register from './pages/Register';
import "./App.css"; // Global styles

// Main app component with route definitions
function App() {
  return (
    <Router>
      <Routes>
        {/* Home route defaults to PvP */}
        <Route path="/" element={<PvP />} />

        {/* App page routes */}
        <Route path="/messages" element={<Messages />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
        <Route path="/ongoing" element={<Ongoing />} />
        <Route path="/house" element={<CPU />} />
        <Route path="/profile" element={<Profile />} />

        {/* Auth routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Routes>
    </Router>
  );
}

export default App;
