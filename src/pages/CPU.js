// Import dependencies and components
import BottomNav from "../components/BottomNav";
import { useState, useEffect } from "react";
import { createStandardBet } from "../utils/betCreation";
import {
  useAutoSaveBets,
  removeBetByIndex,
  acceptBetForCPU,
} from "../utils/acceptHandling";
import { useContext } from "react";
import UserContext from "../UserContext";
import { formatTimeAgo } from "../utils/timeUtils";
import "./PvP.css"; // Reuse PvP styles for layout and cards

// Load bets from localStorage or use a default bet
const loadInitialCPUBets = () => {
  const saved = localStorage.getItem("cpuBets");
  if (saved) return JSON.parse(saved);
  return [
    createStandardBet({
      id: crypto.randomUUID(),
      poster: "CPU",
      posterId: "0",
      timePosted: new Date().toISOString(),
      matchup: "Skib vs Eddy",
      amount: 40,
      lineType: "Over",
      lineNumber: 12.5,
      gameType: "Score",
      gameSize: "1v1",
      gamePlayed: "Caps",
    }),
  ];
};

// CPU bets page component
export default function CPU({ addOngoingBet }) {
  const [bets, setBets] = useState(loadInitialCPUBets);
  const { user } = useContext(UserContext);
  // eslint-disable-next-line no-unused-vars
  const [_, setNow] = useState(Date.now());

  useEffect(() => {
    const interval = setInterval(() => {
      setNow(Date.now()); // just triggers a re-render
    }, 1000); // every second

    return () => clearInterval(interval);
  }, []);

  const visibleBets = bets.filter(
    (bet) => !(bet.hiddenFrom || []).includes(user?.playerId)
  );

  // Auto-save
  useAutoSaveBets(bets, "cpuBets");

  const removeBet = (index) => removeBetByIndex(index, setBets);
  const acceptBet = (index) =>
    acceptBetForCPU(index, setBets, addOngoingBet, user?.playerId);
  
  return (
    <>
      <div className="pvp-page">
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

        <div className="bet-list">
          {visibleBets.map((bet, index) => (
            <div className="bet-card" key={index}>
              <div className="bet-top">
                <span className="poster-time">
                  CPU · {formatTimeAgo(bet.timePosted)}
                </span>
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
                <div className="amount">{bet.amount} caps</div>
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

      <BottomNav />
    </>
  );
}
