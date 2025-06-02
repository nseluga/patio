// Import dependencies
import BottomNav from "../components/BottomNav";
import { useState, useEffect } from "react";
import "./PvP.css"; // Shared styles

// Load initial bets from localStorage or use fallback demo data
const loadInitialBets = () => {
  const saved = localStorage.getItem("pvpBets");
  return saved ? JSON.parse(saved) : [
    {
      poster: "nate",
      time: "2m ago",
      amount: "50 caps",
      matchup: "Nate and Skib W vs Drake and Mike: Caps",
      line: "Over 2.5",
    },
    {
      poster: "mike",
      time: "10m ago",
      amount: "10000 caps",
      matchup: "Logan Bedtime",
      line: "Under 10.5",
    },
  ];
};

// PvP component
export default function PvP() {
  // UI and form state
  const [showModal, setShowModal] = useState(false);
  const [gameType, setGameType] = useState("Shots Made");
  const [lineType, setLineType] = useState("Over");
  const [bets, setBets] = useState(loadInitialBets);
  const [matchup, setMatchup] = useState("");
  const [amount, setAmount] = useState("");
  const [line, setLine] = useState("");

  // Save bets to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem("pvpBets", JSON.stringify(bets));
  }, [bets]);

  // Remove a bet from the list
  const removeBet = (indexToRemove) => {
    setBets((prevBets) =>
      prevBets.filter((_, index) => index !== indexToRemove)
    );
  };

  // Accept a bet (currently removes it)
  const acceptBet = (indexToAccept) => {
    setBets((prevBets) =>
      prevBets.filter((_, index) => index !== indexToAccept)
    );
  };

  // Handle posting a new bet
  const handlePost = () => {
    if (!matchup.trim() || !amount.trim() || !line.trim()) {
      alert("Please fill out all fields before posting.");
      return;
    }

    const newBet = {
      poster: "you", // Placeholder for now
      time: "Just now",
      amount: `${amount} caps`,
      matchup,
      line: `${lineType} ${line}`,
    };

    // Add new bet to top of list
    setBets((prev) => [newBet, ...prev]);
    // Reset form and close modal
    setShowModal(false);
    setMatchup("");
    setAmount("");
    setLine("");
    setGameType("Shots Made");
  };

  return (
    <>
      {/* Main PvP page layout */}
      <div className="pvp-page">
        {/* Header with title and + button */}
        <div className="pvp-header">
          <h2 className="pvp-title">PvP Bets</h2>
          <button
            className="create-bet-button"
            onClick={() => setShowModal(true)}
          >
            ＋
          </button>
        </div>

        {/* Display all current bets */}
        <div className="bet-list">
          {bets.map((bet, index) => (
            <div className="bet-card" key={index}>
              <div className="bet-top">
                <span className="poster-time">
                  {bet.poster} · {bet.time}
                </span>
                <button
                  className="dismiss-button"
                  onClick={() => removeBet(index)}
                >
                  ×
                </button>
              </div>

              <div className="subject">{bet.matchup}</div>

              <div className="bet-bottom">
                <div className="amount">{bet.amount}</div>
                <div className="line">{bet.line}</div>
              </div>

              <button
                className="accept-button"
                onClick={() => acceptBet(index)}
              >
                Accept
              </button>
            </div>
          ))}
        </div>

        {/* Modal for creating a new bet */}
        {showModal && (
          <div className="bet-modal-overlay">
            <div className="bet-modal">
              <h3>Create a Bet</h3>

              {/* Matchup input */}
              <input
                type="text"
                placeholder="Matchup"
                className="modal-input"
                value={matchup}
                onChange={(e) => setMatchup(e.target.value)}
              />

              {/* Amount input */}
              <input
                type="number"
                step="any"
                placeholder="Amount (caps)"
                className="modal-input"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />

              {/* Over/Under selection */}
              <div className="line-type-toggle">
                <label>
                  <input
                    type="radio"
                    value="Over"
                    checked={lineType === "Over"}
                    onChange={(e) => setLineType(e.target.value)}
                  />
                  Over
                </label>
                <label style={{ marginLeft: "1rem" }}>
                  <input
                    type="radio"
                    value="Under"
                    checked={lineType === "Under"}
                    onChange={(e) => setLineType(e.target.value)}
                  />
                  Under
                </label>
              </div>

              {/* Line value input */}
              <input
                type="number"
                step="any"
                placeholder="Line"
                className="modal-input"
                value={line}
                onChange={(e) => setLine(e.target.value)}
              />

              {/* Game type dropdown */}
              <select
                value={gameType}
                onChange={(e) => setGameType(e.target.value)}
                className="modal-input"
              >
                <option value="Shots Made">Shots Made</option>
                <option value="Score">Score</option>
                <option value="Other">Other</option>
              </select>

              {/* Modal actions: Cancel / Post */}
              <div className="modal-actions">
                <button
                  onClick={() => setShowModal(false)}
                  className="cancel-button"
                >
                  Cancel
                </button>
                <button className="confirm-button" onClick={handlePost}>
                  Post
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Fixed bottom navigation bar */}
      <BottomNav />
    </>
  );
}
