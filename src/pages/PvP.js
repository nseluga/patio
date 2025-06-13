// Import dependencies
import BottomNav from "../components/BottomNav";
import { createStandardBet } from "../utils/betCreation"; // Utility function for creating bets
import { useState, useEffect } from "react";
import { removeBetByIndex } from "../utils/acceptHandling";
import { formatTimeAgo } from "../utils/timeUtils";
import { useContext } from "react";
import UserContext from "../UserContext";
import flic from '../assets/images/flic.png';
import buttonpng from '../assets/images/button.png';
import { supabase } from "../utils/supabaseClient";
import "./PvP.css"; // Shared styles

// PvP component
export default function PvP({ addOngoingBet }) {
  // UI and form state
  const [showModal, setShowModal] = useState(false);
  const [gameType, setGameType] = useState("Shots Made");
  const [lineType, setLineType] = useState("Over");
  const [bets, setBets] = useState([]);
  const [matchup, setMatchup] = useState("");
  const [amount, setAmount] = useState("");
  const [lineNumber, setLineNumber] = useState("");
  const [gamePlayed, setGamePlayed] = useState("Caps"); // default game
  const { user } = useContext(UserContext);
  const [gameSize, setGameSize] = useState("2v2");
  // eslint-disable-next-line no-unused-vars
  const [_, setNow] = useState(Date.now());
  const [popupMessage, setPopupMessage] = useState("");

  useEffect(() => {
  const fetchBets = async () => {
    if (!user?.playerId) return;

    const { data, error } = await supabase
      .from("bets")
      .select("*")
      .is("accepterId", null)
      .neq("posterId", user.playerId)
      .order("timePosted", { ascending: false });

    if (error) {
      console.error("❌ Error fetching bets:", error);
    } else {
      setBets(data);
    }
  };

  fetchBets();
  }, [user?.playerId]);


  // Functions
  const removeBet = (index) => removeBetByIndex(index, setBets);
  const acceptBet = async (betId) => {
  const { error } = await supabase
    .from("bets")
    .update({ accepterId: user.playerId })
    .eq("id", betId);

  if (error) {
    console.error("❌ Error accepting bet:", error);
  } else {
    setBets((prev) => prev.filter((b) => b.id !== betId));
    addOngoingBet(betId); // You may want to fetch the full bet again here
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

  const newBet = createStandardBet({
    id: crypto.randomUUID(),
    poster: user?.username,
    posterId: user?.playerId,
    timePosted: new Date().toISOString(),
    matchup,
    amount: parseInt(amount),
    lineType,
    lineNumber: parseFloat(lineNumber),
    gameType,
    gamePlayed,
    gameSize: gameType === "Score" ? gameSize : null,
  });

  const { error } = await supabase.from("bets").insert([newBet]);

  if (error) {
    console.error("❌ Error inserting bet:", error);
    return;
  }

  setPopupMessage("✅ Bet posted!");
  setTimeout(() => setPopupMessage(""), 3000);

  // Close modal and reset form
  setShowModal(false);
  setMatchup("");
  setAmount("");
  setLineNumber("");
  setLineType("Over");
  setGameType("Shots Made");

  // Re-fetch visible bets
  const { data } = await supabase
    .from("bets")
    .select("*")
    .is("accepterId", null)
    .neq("posterId", user.playerId)
    .order("timePosted", { ascending: false });

  setBets(data || []);
};


  return (
    <>
      {/* Main PvP page layout */}
      <div 
        className="pvp-page"
        style={{ backgroundImage: `url(${flic})` }}
      >
        {/* Header with title and + button */}
        <div className="pvp-header">
          <h2 className="pvp-title">PvP BETS</h2>
          <button
            className="create-bet-button"
            onClick={() => setShowModal(true)}
            style={{ backgroundImage: `url(${buttonpng})` }}
          >

          </button>
        </div>

        {/* Display all current bets */}
        <div className="bet-list">
          {visibleBets.map((bet, index) => (
            <div className="bet-card" key={index}>
              <div className="bet-top">
                <span className="poster-time">
                  {bet.poster} · {formatTimeAgo(bet.timePosted)}
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
                onClick={() => acceptBet(bet.id)}
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
                value={lineNumber}
                onChange={(e) => setLineNumber(e.target.value)}
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

              {gameType === "Score" && (
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

      {popupMessage && <div className="popup-banner">{popupMessage}</div>}

      {/* Fixed bottom navigation bar */}
      <BottomNav />
    </>
  );
}
