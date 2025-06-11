// Import dependencies
import BottomNav from "../components/BottomNav";
import { createStandardBet } from "../utils/betCreation"; // Utility function for creating bets
import { useState, useEffect } from "react";
import {
  useAutoSaveBets,
  removeBetByIndex,
  acceptBetWithOngoing,
} from "../utils/acceptHandling";
import { formatTimeAgo } from "../utils/timeUtils";
import { useContext } from "react";
import UserContext from "../UserContext";
import flic from '../assets/images/flic.png';
import buttonpng from '../assets/images/button.png';
import "./PvP.css"; // Shared styles

// Load initial bets from localStorage or use fallback demo data
const loadInitialBets = () => {
  const saved = localStorage.getItem("pvpBets");
  if (saved) return JSON.parse(saved);

  // Hardcoded Test Bets
  return [
    createStandardBet({
      id: 1,
      poster: "nate",
      posterId: "1",
      timePosted: "2m ago",
      matchup: "Nate vs Mike",
      amount: 50,
      lineType: "Over",
      lineNumber: 2.5,
      gameType: "Score",
      gameSize: "1v1",
      gamePlayed: "Caps",
      oppTeamA: ["Player1"],
      oppTeamB: ["Player2"],
      oppScoreA: 10,
      oppScoreB: 7,
    }),
    createStandardBet({
      id: 2,
      poster: "mike",
      posterId: "2",
      timePosted: "10m ago",
      matchup: "Logan Bedtime",
      amount: 10000,
      lineType: "Under",
      lineNumber: 10.5,
      gameType: "Other",
      gamePlayed: "Other",
      oppOutcome: "10",
    }),
    createStandardBet({
      id: 3,
      poster: "Charm",
      posterId: "3",
      timePosted: "1h ago",
      matchup: "Drake Charm vs Eddy Zane",
      amount: 20,
      lineType: "Over",
      lineNumber: 5.5,
      gameType: "Score",
      gamePlayed: "Pong",
      oppTeamA: ["Drake", "Charm"],
      oppTeamB: ["Eddy", "Zane"],
      oppScoreA: 4,
      oppScoreB: 9,
    }),
  ];
};

// PvP component
export default function PvP({ addOngoingBet }) {
  // UI and form state
  const [showModal, setShowModal] = useState(false);
  const [gameType, setGameType] = useState("Shots Made");
  const [lineType, setLineType] = useState("Over");
  const [bets, setBets] = useState(loadInitialBets);
  const [matchup, setMatchup] = useState("");
  const [amount, setAmount] = useState("");
  const [lineNumber, setLineNumber] = useState("");
  const [gamePlayed, setGamePlayed] = useState("Caps"); // default game
  const { user } = useContext(UserContext);
  const [gameSize, setGameSize] = useState("2v2");
  // eslint-disable-next-line no-unused-vars
  const [_, setNow] = useState(Date.now());

  useEffect(() => {
    const interval = setInterval(() => {
      setNow(Date.now()); // just triggers a re-render
    }, 1000); // every second

    return () => clearInterval(interval);
  }, []);

  // Save bets to localStorage whenever they change

  // Auto-save
  useAutoSaveBets(bets, "pvpBets");

  // Functions
  const removeBet = (index) => removeBetByIndex(index, setBets);
  const acceptBet = (index) =>
    acceptBetWithOngoing(index, setBets, addOngoingBet, user?.playerId);

  // Handle posting a new bet
  const handlePost = () => {
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
      lineNumber,
      gameType,
      gamePlayed,
      gameSize: gameType === "Score" ? gameSize : null,
    });

    // Add new bet to top of list
    setBets((prev) => [newBet, ...prev]);
    // Reset form and close modal
    setShowModal(false);
    setMatchup("");
    setAmount("");
    setLineNumber("");
    setLineType("Over");
    setGameType("Shots Made");
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
          {bets.map((bet, index) => (
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
                onClick={() => acceptBet(index)}
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

      {/* Fixed bottom navigation bar */}
      <BottomNav />
    </>
  );
}
