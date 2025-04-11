// App.js
import { BrowserRouter as Router, Route, Routes, Link } from "react-router-dom";
import Messages from "./pages/Messages";
import Leaderboard from './pages/Leaderboard';
import logo from "./logo.svg";
import "./App.css";

function Home() {
  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p>
          Patio Sports Betting 
        </p>
        <br />
        <Link to="/leaderboard" className="nav-button">
          Leaderboard
        </Link>
        {/* Link to Messages Page */}
        <br />
        <Link to="/messages" className="nav-button">
          Messages
        </Link>
      </header>
    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/messages" element={<Messages />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
      </Routes>
    </Router>
  );
}

export default App;
