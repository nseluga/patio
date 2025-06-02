// Import dependencies and components
import BottomNav from "../components/BottomNav";
import { useState, useEffect } from "react";
import "./PvP.css"; // Reuse PvP styles for layout and cards

// Load bets from localStorage or use a default bet
const loadInitialCPUBets = () => {
  const saved = localStorage.getItem("cpuBets");
  return saved
    ? JSON.parse(saved)
    : [
        {
          time: "5m ago",
          amount: "500 caps",
          matchup: "Chungus Dicks Sucked", // Placeholder matchup
          line: "Over 2.5",
        },
      ];
};

// CPU bets page component
export default function CPU() {
  const [bets, setBets] = useState(loadInitialCPUBets); // Store CPU bets

  // Save bets to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem("cpuBets", JSON.stringify(bets));
  }, [bets]);

  // Remove a bet by index
  const removeBet = (indexToRemove) => {
    setBets((prevBets) =>
      prevBets.filter((_, index) => index !== indexToRemove)
    );
  };

  // Accept a bet (currently same as remove)
  const acceptBet = (indexToAccept) => {
    setBets((prevBets) =>
      prevBets.filter((_, index) => index !== indexToAccept)
    );
  };

  return (
    <>
      {/* Page layout */}
      <div className="pvp-page">
        {/* Header and reset button */}
        <div className="pvp-header">
          <h2 className="pvp-title">CPU Bets</h2>
          <button
            onClick={() => {
              localStorage.removeItem("pvpBets");
              localStorage.removeItem("cpuBets");
              localStorage.removeItem("ongoingBets");
              window.location.reload();
            }}
            style={{                              // I noticed you did the styling directly in js file rather than use a css here
              position: "fixed",                  // It works fine but we should prob be uniform with how we do styling
              bottom: "80px",
              right: "20px",
              backgroundColor: "#ef4444",
              color: "white",
              padding: "0.5rem 1rem",
              borderRadius: "0.5rem",
              fontSize: "0.9rem",
              zIndex: 1000,
            }}
          >
            🔄 Reset All
          </button>
        </div>

        {/* Bet cards list */}
        <div className="bet-list">
          {bets.map((bet, index) => (
            <div className="bet-card" key={index}>
              <div className="bet-top">
                <span className="poster-time">CPU · {bet.time}</span>
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
      </div>

      {/* Bottom nav bar */}
      <BottomNav />
    </>
  );
}
