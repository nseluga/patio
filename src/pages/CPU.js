// Import dependencies and components
import BottomNav from "../components/BottomNav";
import { useState } from "react";
import { createStandardBet } from "../utils/betCreation";
import {
  useAutoSaveBets,
  removeBetByIndex,
  acceptBetWithOngoing,
} from "../utils/acceptHandling";
import { useContext } from "react";
import UserContext from "../UserContext";
import "./PvP.css"; // Reuse PvP styles for layout and cards

// Load bets from localStorage or use a default bet
const loadInitialCPUBets = () => {
  const saved = localStorage.getItem("cpuBets");
  if (saved) return JSON.parse(saved);
  return [
    // Hardcoded test bet for CPU
    createStandardBet({
      id: 3,
      poster: "CPU",
      posterId: "0",
      timePosted: "just now",
      matchup: "Skib vs Eddy",
      amount: "40 caps",
      lineType: "Over",
      lineNumber: 12.5,
      gameType: "Shots Made",
      gamePlayed: "Caps",
    }),
  ];
};

// CPU bets page component
export default function CPU({ addOngoingBet }) {
  const [bets, setBets] = useState(loadInitialCPUBets);
  const { user } = useContext(UserContext); // Store CPU bets

  // Auto-save
  useAutoSaveBets(bets, "cpuBets");

  // Functions
  const removeBet = (index) => removeBetByIndex(index, setBets);
  const acceptBet = (index) => acceptBetWithOngoing(index, setBets, addOngoingBet, user?.playerId);


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
            style={{
              // Defined style directly here just because this is a temporary reset button
              position: "fixed",
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
              <div className="game-played">Game: {bet.gamePlayed}</div>
              <div className="bet-bottom">
                <div className="amount">{bet.amount}</div>
                <div className="line">
                  {bet.lineType} {bet.lineNumber}
                </div>
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
