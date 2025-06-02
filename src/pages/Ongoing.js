// Import dependencies
import { useState } from 'react';
import BottomNav from '../components/BottomNav';
import './PvP.css'; // Reuse existing styles

// Main component for ongoing bets
export default function Ongoing() {
  // Sample hardcoded bet data
  const [bets, setBets] = useState([
    {
      id: 1,
      poster: "mike",
      matchup: "Mike vs CPU: Score",
      amount: "100 caps",
      lineType: "Under",
      lineValue: "10.0",
      yourStats: "",
      opponentStats: "",
      gameType: "Score",
    },
    {
      id: 2,
      poster: "drake",
      matchup: "Logan Bedtime",
      amount: "50 caps",
      lineType: "Over",
      lineValue: "10.5",
      yourStats: "",
      opponentStats: "11",
      gameType: "Score",
    },
    {
      id: 3,
      poster: "drake",
      matchup: "Drake vs Nate: Shots Made",
      amount: "60 caps",
      lineType: "Under",
      lineValue: "10.5",
      yourStats: "9",
      opponentStats: "",
      gameType: "Shots Made",
    },
    {
      id: 4,
      poster: "skib",
      matchup: "Skib vs Nate: Score",
      amount: "120 caps",
      lineType: "Over",
      lineValue: "15",
      yourStats: "16",
      opponentStats: "13",
      gameType: "Score",
    },
  ]);

  // UI state for modal and stat input
  const [showModal, setShowModal] = useState(false);
  const [inputStats, setInputStats] = useState("");
  const [activeBetId, setActiveBetId] = useState(null);
  const [popupMessage, setPopupMessage] = useState("");

  // Handle stat submission
  const handleSubmit = () => {
    setBets(prev =>
      prev.flatMap(bet => {
        if (bet.id === activeBetId) {
          const updated = { ...bet, yourStats: inputStats };
          const isMatch = updated.opponentStats && updated.opponentStats === inputStats;

          if (isMatch) {
            setPopupMessage("✅ Match confirmed!");
            setTimeout(() => setPopupMessage(""), 3000);
            return []; // Remove matched bet
          }

          return [updated];
        }
        return [bet];
      })
    );

    setInputStats("");
    setShowModal(false);
  };

  // Get game type of active bet
  const getGameType = () => {
    const bet = bets.find(b => b.id === activeBetId);
    return bet?.gameType || "Shots Made";
  };

  // Get dynamic status message for each bet
  const getStatusMessage = (bet) => {
    if (bet.yourStats && !bet.opponentStats) return "Waiting for other player to input stats";
    if (!bet.yourStats && bet.opponentStats) return "Waiting for you to input stats";
    if (bet.yourStats && bet.opponentStats && bet.yourStats === bet.opponentStats) return "✅ Match confirmed";
    if (bet.yourStats && bet.opponentStats && bet.yourStats !== bet.opponentStats) return "❌ Stats not matching, please communicate";
    return "No stats submitted";
  };

  return (
    <>
      {/* Page container */}
      <div className="pvp-page">
        <div className="pvp-header">
          <h2 className="pvp-title">Ongoing Bets</h2>
        </div>

        {/* Bet list display */}
        <div className="bet-list" style={{ paddingBottom: '100px', overflowY: 'auto' }}>
          {bets.map((bet) => (
            <div className="bet-card" key={bet.id}>
              <div className="bet-top">
                <span className="poster-time">{bet.poster} · 1m ago</span>
              </div>
              <div className="subject">{bet.matchup}</div>
              <div className="bet-bottom">
                <div className="amount">{bet.amount}</div>
                <div className="line">
                  {bet.lineType} {bet.lineValue}
                </div>
              </div>
              <div className="status-text">{getStatusMessage(bet)}</div>
              <button
                className="accept-button"
                onClick={() => {
                  setShowModal(true);
                  setActiveBetId(bet.id);
                }}
              >
                Enter Stats
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Modal for entering stats */}
      {showModal && (
        <div className="bet-modal-overlay">
          <div className="bet-modal">
            <h3>Enter Stats</h3>

            {/* Input shown depends on game type */}
            {getGameType() === "Shots Made" && (
              <input
                type="number"
                placeholder="Shots Made"
                value={inputStats}
                onChange={(e) => setInputStats(e.target.value)}
                className="modal-input"
              />
            )}

            {getGameType() === "Score" && (
              <input
                type="number"
                placeholder="Your Score"
                value={inputStats}
                onChange={(e) => setInputStats(e.target.value)}
                className="modal-input"
              />
            )}

            {getGameType() === "Other" && (
              <input
                type="text"
                placeholder="Describe Outcome"
                value={inputStats}
                onChange={(e) => setInputStats(e.target.value)}
                className="modal-input"
              />
            )}

            {/* Modal buttons */}
            <div className="modal-actions">
              <button
                onClick={() => {
                  setShowModal(false);
                  setInputStats("");
                }}
                className="cancel-button"
              >
                Cancel
              </button>
              <button onClick={handleSubmit} className="confirm-button">
                Submit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Popup message for match confirmation */}
      {popupMessage && (
        <div className="popup-banner">
          {popupMessage}
        </div>
      )}

      {/* Fixed bottom navigation */}
      <BottomNav />
    </>
  );
}
