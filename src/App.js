import { BrowserRouter as Router, Route, Routes} from "react-router-dom";
import Messages from "./pages/Messages";
import Leaderboard from './pages/Leaderboard';
import PvP from './pages/PvP';
import Ongoing from './pages/Ongoing';
import CPU from './pages/CPU';
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
      </Routes>
    </Router>
  );
}

export default App;
