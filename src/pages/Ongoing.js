// Import dependencies
import { useState } from "react";
// import { createStandardBet } from "../utils/betCreation"; // Function for creating hardcoded bets
import BottomNav from "../components/BottomNav";
import "./PvP.css"; // Reuse existing styles

// Main component for ongoing bets
export default function Ongoing({ ongoingBets, setOngoingBets }) {
  const bets = ongoingBets;
  const setBets = setOngoingBets;

    // Hardcoded test bets, left in case we ever need
    // createStandardBet({
    //   id: 1,
    //   poster: "mike",
    //   timePosted: "1m ago",
    //   matchup: "Mike vs CPU: Score",
    //   amount: "100 caps",
    //   lineType: "Under",
    //   lineNumber: 10.5,
    //   gameType: "Score",
    //   oppPlayerA: "Player1",
    //   oppStatsA: "5",
    //   oppPlayerB: "Player2",
    //   oppStatsB: "7",
    // }),
    // createStandardBet({
    //   id: 2,
    //   poster: "drake",
    //   timePosted: "1m ago",
    //   matchup: "Logan Bedtime",
    //   amount: "50 caps",
    //   lineType: "Over",
    //   lineNumber: 10.5,
    //   gameType: "Other",
    //   oppInfo: "9",
    // }),
    // createStandardBet({
    //   id: 3,
    //   poster: "drake",
    //   timePosted: "1m ago",
    //   matchup: "Drake vs Nate: Shots Made",
    //   amount: "60 caps",
    //   lineType: "Under",
    //   lineNumber: 10.5,
    //   gameType: "Shots Made",
    //   oppPlayer: "Nate",
    //   oppStats: "13",
    // }),
    // createStandardBet({
    //   id: 4,
    //   poster: "skib",
    //   timePosted: "1m ago",
    //   matchup: "Skib vs Nate: Score",
    //   amount: "120 caps",
    //   lineType: "Over",
    //   lineNumber: 15.5,
    //   gameType: "Score",
    // }),

  // UI state for modal and stat input
  const [showModal, setShowModal] = useState(false);
  const [activeBetId, setActiveBetId] = useState(null);
  const [popupMessage, setPopupMessage] = useState("");

  // State for Score bets
  const [yourPlayerA, setYourPlayerA] = useState("");
  const [yourStatsA, setYourStatsA] = useState("");
  const [yourPlayerB, setYourPlayerB] = useState("");
  const [yourStatsB, setYourStatsB] = useState("");

  // State for Shots Made
  const [yourPlayer, setYourPlayer] = useState("");
  const [yourStats, setYourStats] = useState("");

  // State for Other bets
  const [yourInfo, setYourInfo] = useState("");

  // Submit handler to update bet with user’s input and check for match
  const handleSubmit = () => {
    setBets((prev) =>
      prev.flatMap((bet) => {
        if (bet.id !== activeBetId) return [bet]; // only update the selected bet

        const updated = { ...bet }; // make a copy to mutate safely

        // Handle Score bets
        if (bet.gameType === "Score") {
          updated.yourPlayerA = yourPlayerA;
          updated.yourStatsA = yourStatsA;
          updated.yourPlayerB = yourPlayerB;
          updated.yourStatsB = yourStatsB;

          // Full match check: players AND stats must match
          const match =
            updated.oppPlayerA &&
            updated.oppStatsA &&
            updated.oppPlayerB &&
            updated.oppStatsB &&
            updated.yourPlayerA === updated.oppPlayerA &&
            updated.yourPlayerB === updated.oppPlayerB &&
            updated.yourStatsA === updated.oppStatsA &&
            updated.yourStatsB === updated.oppStatsB;

          if (match) {
            setPopupMessage("✅ Match confirmed!");

            // Reset all input state fields
            setYourPlayerA("");
            setYourStatsA("");
            setYourPlayerB("");
            setYourStatsB("");
            setYourPlayer("");
            setYourStats("");
            setYourInfo("");

            setTimeout(() => setPopupMessage(""), 3000);
            return []; // Remove bet from list
          }
          // Handle Shots Made bets
        } else if (bet.gameType === "Shots Made") {
          updated.yourPlayer = yourPlayer;
          updated.yourStats = yourStats;

          const match =
            updated.oppPlayer &&
            updated.oppStats &&
            updated.yourPlayer === updated.oppPlayer &&
            updated.yourStats === updated.oppStats;

          if (match) {
            setPopupMessage("✅ Match confirmed!");

            // Reset all input state fields
            setYourPlayerA("");
            setYourStatsA("");
            setYourPlayerB("");
            setYourStatsB("");
            setYourPlayer("");
            setYourStats("");
            setYourInfo("");

            setTimeout(() => setPopupMessage(""), 3000);
            return [];
          }
          // Handle Other bets (text/info match)
        } else if (bet.gameType === "Other") {
          updated.yourInfo = yourInfo;

          const match = updated.oppInfo && updated.yourInfo === updated.oppInfo;

          if (match) {
            setPopupMessage("✅ Match confirmed!");

            // Reset all input state fields
            setYourPlayerA("");
            setYourStatsA("");
            setYourPlayerB("");
            setYourStatsB("");
            setYourPlayer("");
            setYourStats("");
            setYourInfo("");

            setTimeout(() => setPopupMessage(""), 3000);
            return [];
          }
        }

        return [updated]; // if no match, keep updated bet
      })
    );

    // Reset all form fields and close modal
    setShowModal(false);
    setYourPlayerA("");
    setYourStatsA("");
    setYourPlayerB("");
    setYourStatsB("");
    setYourPlayer("");
    setYourStats("");
    setYourInfo("");
  };

  // Get game type of active bet
  const getGameType = () => {
    const bet = bets.find((b) => b.id === activeBetId);
    return bet?.gameType || "Shots Made";
  };

  // Get dynamic status message for each bet
  const getStatusMessage = (bet) => {
    const { gameType } = bet;

    // Score game: requires full player and stat match
    if (gameType === "Score") {
      if (
        bet.yourPlayerA &&
        bet.oppPlayerA &&
        bet.yourPlayerB &&
        bet.oppPlayerB &&
        bet.yourStatsA &&
        bet.oppStatsA &&
        bet.yourStatsB &&
        bet.oppStatsB
      ) {
        const playersMatch =
          bet.yourPlayerA === bet.oppPlayerA &&
          bet.yourPlayerB === bet.oppPlayerB;
        const statsMatch =
          bet.yourStatsA === bet.oppStatsA && bet.yourStatsB === bet.oppStatsB;

        if (playersMatch && statsMatch) return "✅ Match confirmed";
        if (!playersMatch) return "❌ Player names do not match";
        return "❌ Stats not matching, please communicate";
      }
    }

    // Shots Made: player + stat match
    if (gameType === "Shots Made") {
      if (bet.yourPlayer && bet.oppPlayer && bet.yourStats && bet.oppStats) {
        const playersMatch = bet.yourPlayer === bet.oppPlayer;
        const statsMatch = bet.yourStats === bet.oppStats;

        if (playersMatch && statsMatch) return "✅ Match confirmed";
        if (!playersMatch) return "❌ Player names do not match";
        return "❌ Stats not matching, please communicate";
      }
    }

    // Other: text match
    if (gameType === "Other") {
      if (bet.yourInfo && bet.oppInfo) {
        return bet.yourInfo === bet.oppInfo
          ? "✅ Match confirmed"
          : "❌ Info not matching, please communicate";
      }
    }

    // Fallbacks for missing inputs
    if (
      gameType === "Score" &&
      (bet.yourStatsA || bet.yourStatsB || bet.yourPlayerA || bet.yourPlayerB)
    ) {
      return "Waiting for other player to input stats";
    }

    if (gameType === "Shots Made" && (bet.yourStats || bet.yourPlayer)) {
      return "Waiting for other player to input stats";
    }

    if (gameType === "Other" && bet.yourInfo) {
      return "Waiting for other player to input stats";
    }

    return "No stats submitted";
  };

  return (
    <>
      {/* Page container */}
      <div className="pvp-page">
        <div className="pvp-header">
          <h2 className="pvp-title">Ongoing Bets</h2>
        </div>

        {/* Bet list display */}
        <div
          className="bet-list"
          style={{ paddingBottom: "100px", overflowY: "auto" }}
        >
          {bets.map((bet) => (
            <div className="bet-card" key={bet.id}>
              <div className="bet-top">
                <span className="poster-time">{bet.poster} · 1m ago</span>
              </div>
              <div className="subject">{bet.matchup}</div>
              <div className="bet-bottom">
                <div className="amount">{bet.amount}</div>
                <div className="line">
                  {bet.lineType} {bet.lineNumber}
                </div>
              </div>
              <div className="status-text">{getStatusMessage(bet)}</div>
              <button
                className="accept-button"
                onClick={() => {
                  setShowModal(true);
                  setActiveBetId(bet.id);

                  // Reset all state fields for score
                  setYourPlayerA("");
                  setYourStatsA("");
                  setYourPlayerB("");
                  setYourStatsB("");

                  // Reset all state fields for shots made
                  setYourPlayer("");
                  setYourStats("");

                  // Reset for other
                  setYourInfo("");
                }}
              >
                Enter Stats
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Modal for entering stats */}
      {showModal && (
        <div className="bet-modal-overlay">
          <div className="bet-modal">
            <h3>Enter Stats</h3>

            {/* Input shown depends on game type */}
            {getGameType() === "Shots Made" && (
              <>
                <input
                  type="text"
                  placeholder="Your Player"
                  value={yourPlayer}
                  onChange={(e) => setYourPlayer(e.target.value)}
                  className="modal-input"
                />
                <input
                  type="number"
                  placeholder="Shots Made"
                  value={yourStats}
                  onChange={(e) => setYourStats(e.target.value)}
                  className="modal-input"
                />
              </>
            )}

            {getGameType() === "Score" && (
              <>
                <input
                  type="text"
                  placeholder="Your Player A"
                  value={yourPlayerA}
                  onChange={(e) => setYourPlayerA(e.target.value)}
                  className="modal-input"
                />
                <input
                  type="number"
                  placeholder="Player A Score"
                  value={yourStatsA}
                  onChange={(e) => setYourStatsA(e.target.value)}
                  className="modal-input"
                />
                <input
                  type="text"
                  placeholder="Your Player B"
                  value={yourPlayerB}
                  onChange={(e) => setYourPlayerB(e.target.value)}
                  className="modal-input"
                />
                <input
                  type="number"
                  placeholder="Player B Score"
                  value={yourStatsB}
                  onChange={(e) => setYourStatsB(e.target.value)}
                  className="modal-input"
                />
              </>
            )}

            {getGameType() === "Other" && (
              <input
                type="number"
                placeholder="Describe Outcome"
                value={yourInfo}
                onChange={(e) => setYourInfo(e.target.value)}
                className="modal-input"
              />
            )}

            {/* Modal buttons */}
            <div className="modal-actions">
              <button
                onClick={() => {
                  setShowModal(false);
                }}
                className="cancel-button"
              >
                Cancel
              </button>
              <button onClick={handleSubmit} className="confirm-button">
                Submit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Popup message for match confirmation */}
      {popupMessage && <div className="popup-banner">{popupMessage}</div>}

      {/* Fixed bottom navigation */}
      <BottomNav />
    </>
  );
}

export function addToOngoingBets(bet) {
  const saved = localStorage.getItem("ongoingBets");
  const existing = saved ? JSON.parse(saved) : [];

  // Prevent duplicates
  const alreadyExists = existing.some((b) => b.id === bet.id);
  if (!alreadyExists) {
    const updated = [...existing, bet];
    localStorage.setItem("ongoingBets", JSON.stringify(updated));
  }
}
