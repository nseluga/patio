/// Import dependencies
import BottomNav from "../components/BottomNav";
import { useState, useEffect, useContext } from "react";
import { removeBetByIndex } from "../utils/acceptHandling";
import { formatTimeAgo } from "../utils/timeUtils";
import UserContext from "../UserContext";
import back1 from "../assets/images/back1.png";
import buttonpng from "../assets/images/button.png";
import betcard from "../assets/images/betcard.png";
import "./PvP.css";
import api from "../api";
import { v4 as uuidv4 } from "uuid";

// PvP component
export default function PvP({ addOngoingBet }) {
  const [showModal, setShowModal] = useState(false);
  const [gameType, setGameType] = useState("Shots Made");
  const [lineType, setLineType] = useState("Over");
  const [bets, setBets] = useState([]);
  const [matchup, setMatchup] = useState("");
  const [amount, setAmount] = useState("");
  const [lineNumber, setLineNumber] = useState("");
  const [gamePlayed, setGamePlayed] = useState("Caps");
  const [gameSize, setGameSize] = useState("2v2");
  const [popupMessage, setPopupMessage] = useState("");
  const { user, setUser } = useContext(UserContext);

  const refreshUser = async () => {
    try {
      const res = await api.get("/me", {
        headers: { Authorization: `Bearer ${user.token}` },
      });
      setUser(res.data);
    } catch (err) {
      console.error("❌ Failed to refresh user:", err);
    }
  };

  // Fetch PvP bets from Flask backend
  useEffect(() => {
    if (!user?.playerId) return;

    const fetchBets = async () => {
      try {
        const res = await api.get(`/pvp_bets`, {
          params: { playerId: user.playerId },
        });
        setBets(res.data);
      } catch (err) {
        console.error("Error fetching PvP bets:", err);
      }
    };

    fetchBets();
  }, [user?.playerId]); // runs only when playerId is set

  // Helper to flip line type
  const flipLineType = (type) => {
    return type === "Over" ? "Under" : "Over";
  };

  // Handle accepting a bet
  const acceptBet = async (betId) => {
    try {
      const bet = bets.find((b) => b.id === betId);
      if (!bet) {
        console.error("❌ Bet not found");
        return;
      }

      const accepterLineType = flipLineType(bet.lineType);

      const res = await api.post(
        `/accept_bet/${betId}`,
        { accepterLineType }, // send the opposite side
        {
          headers: {
            Authorization: `Bearer ${user?.token}`,
          },
        }
      );

      if (res.status === 200) {
        setBets((prev) => prev.filter((b) => b.id !== betId));
        addOngoingBet(betId);
        await refreshUser(); // this will update caps and pvp_bets_placed in Profile
      } else {
        console.error(
          "❌ Error accepting bet:",
          res.data?.message || "Unknown error"
        );
      }
    } catch (err) {
      console.error("❌ Request failed:", err);
    }
  };

  const handlePost = async () => {
    if (
      !matchup.trim() ||
      !amount.trim() ||
      !lineType.trim() ||
      !lineNumber.trim()
    ) {
      alert("Please fill out all fields before posting.");
      return;
    }

    const newBet = {
      id: uuidv4(), // Generate a unique ID for the bet
      poster: user?.username,
      posterId: user?.playerId,
      timePosted: new Date().toISOString(),
      matchup,
      amount: parseInt(amount),
      lineType,
      lineNumber: parseFloat(lineNumber),
      gameType,
      gamePlayed,
      gameSize: ["Shots Made", "Score"].includes(gameType) ? gameSize : null,
    };

    try {
      const response = await api.post("/create_bet", newBet, {
        headers: {
          Authorization: `Bearer ${user?.token}`,
        },
      });

      if (response.status !== 201) {
        console.error("❌ Error posting bet:", response.data);
        alert(response.data?.error || "Failed to post bet.");
        return;
      }

      setPopupMessage("✅ Bet posted!");
      setTimeout(() => setPopupMessage(""), 3000);

      // Clear modal
      setShowModal(false);
      setMatchup("");
      setAmount("");
      setLineNumber("");
      setLineType("Over");
      setGameType("Shots Made");
    } catch (err) {
      console.error("❌ Network error:", err);
    }
  };

  return (
    <>
      <div className="pvp-page" style={{ backgroundImage: `url(${back1})` }}>
        <div className="pvp-header">
          <h2 className="pvp-title">PvP BETS</h2>
          <button
            className="create-bet-button"
            onClick={() => setShowModal(true)}
            style={{ backgroundImage: `url(${buttonpng})` }}
          ></button>
        </div>

        <div className="bet-list">
          {bets.map((bet, index) => (
            <div className="bet-card" key={index} style={{ backgroundImage: `url(${betcard})` }}> 
              <div className="bet-top">
                <span className="poster-time">
                  {bet.poster} · {formatTimeAgo(bet.timePosted)}
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
                  {user?.playerId === bet.posterId
                    ? `${bet.lineType} ${bet.lineNumber}`
                    : `${flipLineType(bet.lineType)} ${bet.lineNumber}`}
                </div>
              </div>

              <button
                className="accept-button"
                onClick={() => acceptBet(bet.id)}
              >
                ACCEPT
              </button>
            </div>
          ))}
        </div>

        {/* Modal for creating a new bet */}
        {showModal && (
          <div className="bet-modal-overlay">
            <div className="bet-modal">
              <h3>CREATE A BET!</h3>

              <input
                type="text"
                placeholder="Matchup"
                className="modal-input"
                value={matchup}
                onChange={(e) => setMatchup(e.target.value)}
              />

              <input
                type="number"
                step="any"
                placeholder="Amount (caps)"
                className="modal-input"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />

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

              <input
                type="number"
                step="any"
                placeholder="Line"
                className="modal-input"
                value={lineNumber}
                onChange={(e) => setLineNumber(e.target.value)}
              />

              <select
                value={gameType}
                onChange={(e) => setGameType(e.target.value)}
                className="modal-input"
              >
                <option value="Shots Made">Shots Made</option>
                <option value="Score">Score</option>
                <option value="Other">Other</option>
              </select>

              <select
                value={gamePlayed}
                onChange={(e) => setGamePlayed(e.target.value)}
                className="modal-input"
              >
                <option value="Caps">Caps</option>
                <option value="Pong">Pong</option>
                <option value="Beerball">Beerball</option>
                <option value="Campus Golf">Campus Golf</option>
                <option value="Other">Other</option>
              </select>

              {["Score", "Shots Made"].includes(gameType) && (
                <select
                  value={gameSize}
                  onChange={(e) => setGameSize(e.target.value)}
                  className="modal-input"
                >
                  <option value="1v1">1v1</option>
                  <option value="2v2">2v2</option>
                  <option value="3v3">3v3</option>
                </select>
              )}

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

      {popupMessage && <div className="popup-banner">{popupMessage}</div>}
      <BottomNav />
    </>
  );
}
