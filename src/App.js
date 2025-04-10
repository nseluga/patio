// App.js
import { BrowserRouter as Router, Route, Routes, Link } from "react-router-dom";
import Messages from "./pages/Messages";
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
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          One game away from the next BIG WIN
        </a>
        {/* Link to Messages Page */}
        <br />
        <Link to="/messages" className="App-link">
          Go to Messages Page
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
      </Routes>
    </Router>
  );
}

export default App;
