import { useEffect, useState } from "react";
import BottomNav from "../components/BottomNav";
import "./Leaderboard.css";

export default function Leaderboard() {
  const [players, setPlayers] = useState([]);

  useEffect(() => {
    async function fetchLeaderboard() {
      try {
        const response = await fetch("http://localhost:5001/leaderboard");
        const data = await response.json();
        setPlayers(data.slice(0, 5)); // top 5 only
      } catch (error) {
        console.error("Failed to fetch leaderboard:", error);
      }
    }

    fetchLeaderboard();
  }, []);

  return (
    <div className="leaderboard-page">
      <BottomNav />

      <div className="leaderboard-title-wrapper">
        <h2>LEADERBOARD</h2>
      </div>

      <div className="leaderboard-list">
        {players.slice(0, 5).map((player, index) => (
          <div key={index} className="leaderboard-entry">
            <span
              className={
                index === 1 || index === 2
                  ? "top-rank-symbol"
                  : "below-top3-symbol"
              }
            >
              {index === 0 && "🥇"}
              {index === 1 && "🥈"}
              {index === 2 && "🥉"}
              {index > 2 && `#${index + 1}`}
            </span>
            <span>{player.username}</span>
            <span>{player.caps_balance} caps</span>
          </div>
        ))}
      </div>
    </div>
  );
}
