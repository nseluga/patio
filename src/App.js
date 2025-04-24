import { BrowserRouter as Router, Route, Routes} from "react-router-dom";
import Messages from "./pages/Messages";
import Leaderboard from './pages/Leaderboard';
import PvP from './pages/PvP';
import Ongoing from './pages/Ongoing';
import CPU from './pages/CPU';
import Profile from './pages/Profile';
import Login from './pages/Login';
import Register from './pages/Register'
import "./App.css";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<PvP />} />
        <Route path="/messages" element={<Messages />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
        <Route path="/ongoing" element={<Ongoing />} />
        <Route path="/house" element={<CPU />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Routes>
    </Router>
  );
}

export default App;



