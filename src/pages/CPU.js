// Import dependencies and components
import BottomNav from "../components/BottomNav";
import { useState, useEffect } from "react";
import { removeBetByIndex } from "../utils/acceptHandling";
import { useContext } from "react";
import UserContext from "../UserContext";
import { formatTimeAgo } from "../utils/timeUtils";
import api from "../api";
import "./PvP.css"; // Reuse PvP styles for layout and cards

// CPU bets page component
export default function CPU({ addOngoingBet }) {
  const [bets, setBets] = useState([]);
  const { user } = useContext(UserContext);
  // eslint-disable-next-line no-unused-vars
  const [_, setNow] = useState(Date.now());

  useEffect(() => {
    if (!user?.token) return;

    const fetchBets = async () => {
      try {
        const res = await api.get("/cpu_bets", {
          headers: {
            Authorization: `Bearer ${user.token}`,
          },
        });
        setBets(res.data);
        console.log("✅ CPU bets:", res.data);
      } catch (err) {
        console.error("❌ Error fetching CPU bets:", err);
      }
    };

    fetchBets();
  }, [user?.token]);

  const isCPUAdmin = user?.playerId === 0;

  const visibleBets = bets.filter((bet) => {
    if (isCPUAdmin) return false; // Hide all bets from admin
    // Later you may also check if this user has already accepted the CPU bet
    return true;
  });

  const acceptBet = async (bet, index) => {
    try {
      const res = await api.post(`/accept_cpu_bet/${bet.id}`, null, {
        headers: {
          Authorization: `Bearer ${user?.token}`,
        },
      });

      if (res.status === 200) {
        setBets((prev) => {
          const updated = [...prev];
          updated.splice(index, 1);
          return updated;
        });

        addOngoingBet(bet); // Add bet to Ongoing tab
      } else {
        console.error(
          "❌ CPU bet not accepted:",
          res.data?.error || "Unknown error"
        );
      }
    } catch (err) {
      console.error("❌ CPU bet accept error:", err);
    }
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
          {visibleBets.map((bet, index) => (
            <div className="bet-card" key={index}>
              <div className="bet-top">
                <span className="poster-time">
                  CPU · {formatTimeAgo(bet.timePosted)}
                </span>
                <button
                  className="dismiss-button"
                  onClick={() => removeBetByIndex(index, setBets)}
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
                onClick={() => acceptBet(bet, index)}
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
