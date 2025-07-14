// Import dependencies and components
import BottomNav from "../components/BottomNav";
import { useState, useEffect } from "react";
import { removeBetByIndex } from "../utils/acceptHandling";
import { useContext } from "react";
import UserContext from "../UserContext";
import { formatTimeAgo } from "../utils/timeUtils";
import buttonpng from "../assets/images/button.png";
import back1 from "../assets/images/back1.png";
import betcard2 from "../assets/images/betcard2.png"
import api from "../api";
import "./PvP.css"; // Reuse PvP styles for layout and cards

// CPU bets page component
export default function CPU({ addOngoingBet }) {
  const [bets, setBets] = useState([]);
  const { user } = useContext(UserContext);
  const [showModal, setShowModal] = useState(false);
  const [selectedBetType, setSelectedBetType] = useState("");
  const [popupMessage, setPopupMessage] = useState("");
  // eslint-disable-next-line no-unused-vars
  const [_, setNow] = useState(Date.now());
  const [gameSize, setGameSize] = useState("1v1");

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
      <div className="cpu-page" style={{ backgroundImage: `url(${back1})` }}>
        <div className="pvp-page">
          <div className="pvp-header">
            <h2 className="pvp-title">HOUSE BETS</h2>
            {isCPUAdmin && (
              <button
                className="create-bet-button"
                onClick={() => setShowModal(true)}
                style={{ backgroundImage: `url(${buttonpng})` }}
              ></button>
            )}
          </div>

          <div className="bet-list">
            {visibleBets.map((bet, index) => {
              const flippedLineType = bet.lineType === "Over" ? "Under" : "Over";

              return (
                <div className="bet-card" key={index} style={{ backgroundImage: `url(${betcard2})` }}>
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
                  <div className="game-type">Type: {bet.gameType}</div>
                  <div className="bet-bottom">
                    <div className="amount">{bet.amount} caps</div>
                    <div className="line">
                      {flippedLineType} {bet.lineNumber}
                    </div>
                  </div>
                  <button
                    className="accept-button"
                    onClick={() => acceptBet(bet, index)}
                  >
                    ACCEPT
                  </button>
                </div>
              );
            })}
          </div>

          {showModal && (
            <div className="bet-modal-overlay">
              <div className="bet-modal">
                <h3>Generate CPU Bet</h3>

                <select
                  className="modal-input"
                  value={selectedBetType}
                  onChange={(e) => setSelectedBetType(e.target.value)}
                >
                  <option value="">Select Bet Type</option>
                  <option value="Caps - Shots Made">Caps - Shots Made</option>
                  <option value="Beerball - Shots Made">
                    Beerball - Shots Made
                  </option>
                  <option value="Pong - Shots Made">Pong - Shots Made</option>
                  <option value="Caps - Score">Caps - Score</option>
                  <option value="Beerball - Score">Beerball - Score</option>
                  <option value="Pong - Score">Pong - Score</option>
                </select>
                <select
                  value={gameSize}
                  onChange={(e) => setGameSize(e.target.value)}
                  className="modal-input"
                >
                  <option value="1v1">1v1</option>
                  <option value="2v2">2v2</option>
                  <option value="3v3">3v3</option>
                </select>

                <div className="modal-actions">
                  <button
                    onClick={() => setShowModal(false)}
                    className="cancel-button"
                  >
                    Cancel
                  </button>
                  <button
                    className="confirm-button"
                    onClick={async () => {
                      let endpoint = "";
                      switch (selectedBetType) {
                        case "Caps - Shots Made":
                          endpoint = "/cpu/create_caps_shots_bet";
                          break;
                        case "Beerball - Shots Made":
                          endpoint = "/cpu/create_beerball_shots_bet";
                          break;
                        case "Pong - Shots Made":
                          endpoint = "/cpu/create_pong_shots_bet";
                          break;
                        case "Caps - Score":
                          endpoint = "/cpu/create_caps_score_bet";
                          break;
                        case "Beerball - Score":
                          endpoint = "/cpu/create_beerball_score_bet";
                          break;
                        case "Pong - Score":
                          endpoint = "/cpu/create_pong_score_bet";
                          break;
                        default:
                          alert("Please select a valid bet type.");
                          return;
                      }

                      try {
                        await api.post(
                          endpoint,
                          { gameSize },
                          {
                            headers: {
                              Authorization: `Bearer ${user?.token}`,
                            },
                          }
                        );
                        setPopupMessage("✅ CPU bet created!");
                        setTimeout(() => setPopupMessage(""), 3000);

                        setShowModal(false);
                        window.location.reload();
                      } catch (err) {
                        console.error("❌ Failed to create CPU bet:", err);
                        alert(
                          "❌ " + (err.response?.data?.error || "Unknown error")
                        );
                      }
                    }}
                  >
                    Generate
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      {popupMessage && <div className="popup-banner">{popupMessage}</div>}
      <BottomNav />
    </>
  );
}
