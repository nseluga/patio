import BottomNav from "../components/BottomNav";
import { useState, useEffect } from "react";
import "./PvP.css"; // reuse the styles

const loadInitialCPUBets = () => {
  const saved = localStorage.getItem("cpuBets");
  return saved
    ? JSON.parse(saved)
    : [
        {
          time: "5m ago",
          amount: "500 caps",
          matchup: "Chungus Dicks Sucked",
          line: "Over 2.5",
        },
      ];
};

export default function CPU() {
  const [bets, setBets] = useState(loadInitialCPUBets);

  useEffect(() => {
    localStorage.setItem("cpuBets", JSON.stringify(bets));
  }, [bets]);

  const removeBet = (indexToRemove) => {
    setBets((prevBets) =>
      prevBets.filter((_, index) => index !== indexToRemove)
    );
  };

  const acceptBet = (indexToAccept) => {
    setBets((prevBets) =>
      prevBets.filter((_, index) => index !== indexToAccept)
    );
  };

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
          {bets.map((bet, index) => (
            <div className="bet-card">
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

      <BottomNav />
    </>
  );
}
