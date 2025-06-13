// Import dependencies
import { useState, useEffect, useContext } from "react";
import UserContext from "../UserContext";
// import { createStandardBet } from "../utils/betCreation"; // Function for creating hardcoded bets
import BottomNav from "../components/BottomNav";
import { formatTimeAgo } from "../utils/timeUtils";
import "./PvP.css"; // Reuse existing styles
import api from "../api";


function getNumPlayers(gameSize) {
  if (!gameSize) return 2; // fallback default
  const [a] = gameSize.split("v").map(Number);
  return isNaN(a) ? 2 : a;
}

// Main component for ongoing bets
export default function Ongoing({ ongoingBets, setOngoingBets }) {
  const { user } = useContext(UserContext);
  const bets = ongoingBets;
  const setBets = setOngoingBets;
  // eslint-disable-next-line no-unused-vars
  const [_, setNow] = useState(Date.now());

  useEffect(() => {
  const fetchBets = async () => {
    try {
      const res = await api.get("/bets"); // Replace with your actual endpoint if different
      setBets(res.data); // Update state with fetched bets
      console.log("✅ Loaded bets from backend:", res.data);
    } catch (err) {
      console.error("❌ Failed to fetch bets from DB:", err);
    }
  };

  fetchBets();
}, []);


  const visibleBets = bets.filter(
    (bet) =>
      bet.posterId === user?.playerId || bet.accepterId === user?.playerId
  );

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
  //   gameSize: "1v1",
  //   gamePlayed: "Caps",
  //   yourTeamA: "",
  //   oppTeamA: "Player1",
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
  const [showHelp, setShowHelp] = useState(false);
  const [activeBetId, setActiveBetId] = useState(null);
  const [popupMessage, setPopupMessage] = useState("");

  // State for Score bets
  const [yourTeamA, setYourTeamA] = useState([]);
  const [yourScoreA, setYourScoreA] = useState("");
  const [yourTeamB, setYourTeamB] = useState([]);
  const [yourScoreB, setYourScoreB] = useState("");

  // State for Shots Made
  const [yourPlayer, setYourPlayer] = useState("");
  const [yourShots, setYourShots] = useState("");

  // State for Other bets
  const [yourOutcome, setYourOutcome] = useState("");

  // Submit handler to update bet with user’s input and check for match
  const handleSubmit = () => {
    setBets((prev) =>
      prev.flatMap((bet) => {
        if (bet.id !== activeBetId) return [bet]; // only update the selected bet

        const updated = { ...bet }; // make a copy to mutate safely

        // Handle Score bets
        if (bet.gameType === "Score") {
          // Save input to bet object
          updated.yourTeamA = yourTeamA.map((p) => p.name);
          updated.yourTeamB = yourTeamB.map((p) => p.name);
          updated.yourScoreA = Number(yourScoreA);
          updated.yourScoreB = Number(yourScoreB);

          // Match logic: check players and scores
          const match =
            JSON.stringify(updated.yourTeamA) ===
              JSON.stringify(bet.oppTeamA || []) &&
            JSON.stringify(updated.yourTeamB) ===
              JSON.stringify(bet.oppTeamB || []) &&
            updated.yourScoreA === bet.oppScoreA &&
            updated.yourScoreB === bet.oppScoreB;

          console.log(
            "yourTeamA:",
            yourTeamA.map((p) => p.name)
          );
          console.log(
            "oppTeamA:",
            (bet.oppTeamA || []).map((p) => p.name)
          );
          console.log(
            "yourTeamB:",
            yourTeamB.map((p) => p.name)
          );
          console.log(
            "oppTeamB:",
            (bet.oppTeamB || []).map((p) => p.name)
          );
          console.log(
            "Scores:",
            updated.yourScoreA,
            bet.oppScoreA,
            updated.yourScoreB,
            bet.oppScoreB
          );
          console.log("Match?", match);

          if (match) {
            setPopupMessage("✅ Match confirmed!");

            setYourTeamA([]);
            setYourTeamB([]);
            setYourScoreA("");
            setYourScoreB("");

            setTimeout(() => setPopupMessage(""), 3000);
            return []; // remove bet from list
          }

          return [updated]; // keep updated bet in the list
          // Handle Shots Made bets
        } else if (bet.gameType === "Shots Made") {
          updated.yourPlayer = yourPlayer;
          updated.yourShots = Number(yourShots);

          const match =
            bet.oppPlayer &&
            bet.oppShots != null &&
            yourPlayer === bet.oppPlayer &&
            updated.yourShots === bet.oppShots;

          if (match) {
            setPopupMessage("✅ Match confirmed!");

            // Reset all input state fields
            setYourPlayer("");
            setYourShots("");

            setTimeout(() => setPopupMessage(""), 3000);
            return [];
          }

          return [updated];
        }
        // Handle Other bets (text/info match)
        else if (bet.gameType === "Other") {
          updated.yourOutcome = yourOutcome;

          const match =
            updated.oppOutcome && updated.yourOutcome === updated.oppOutcome;

          if (match) {
            setPopupMessage("✅ Match confirmed!");

            // Reset all input state fields
            setYourOutcome("");

            setTimeout(() => setPopupMessage(""), 3000);
            return [];
          }
        }

        return [updated]; // if no match, keep updated bet
      })
    );

    // Reset all form fields and close modal
    setShowModal(false);
    setActiveBetId(null);
    setYourTeamA([]);
    setYourTeamB([]);
    setYourScoreA("");
    setYourScoreB("");
    setYourPlayer("");
    setYourShots("");
    setYourOutcome("");
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
        bet.yourTeamA?.length &&
        bet.oppTeamA?.length &&
        bet.yourTeamB?.length &&
        bet.oppTeamB?.length &&
        bet.yourScoreA != null &&
        bet.oppScoreA != null &&
        bet.yourScoreB != null &&
        bet.oppScoreB != null
      ) {
        // Check if teams and scores match
        const teamAMatch =
          JSON.stringify(bet.yourTeamA) === JSON.stringify(bet.oppTeamA);
        const teamBMatch =
          JSON.stringify(bet.yourTeamB) === JSON.stringify(bet.oppTeamB);
        const scoresMatch =
          bet.yourScoreA === bet.oppScoreA && bet.yourScoreB === bet.oppScoreB;

        if (teamAMatch && teamBMatch && scoresMatch)
          return "✅ Match confirmed";
        if (!teamAMatch || !teamBMatch) return "❌ Player names do not match";
        return "❌ Scores not matching, please communicate";
      }
    }

    // Shots Made: player + stat match
    if (gameType === "Shots Made") {
      if (bet.yourPlayer && bet.oppPlayer && bet.yourShots && bet.oppShots) {
        const playersMatch = bet.yourPlayer === bet.oppPlayer;
        const statsMatch = bet.yourShots === bet.oppShots;

        if (playersMatch && statsMatch) return "✅ Match confirmed";
        if (!playersMatch) return "❌ Player names do not match";
        return "❌ Stats not matching, please communicate";
      }
    }

    // Other: text match
    if (gameType === "Other") {
      if (bet.yourOutcome && bet.oppOutcome) {
        return bet.yourOutcome === bet.oppOutcome
          ? "✅ Match confirmed"
          : "❌ Outcome not matching, please communicate";
      }
    }

    // Fallbacks for partial input
    if (
      gameType === "Score" &&
      (bet.yourTeamA?.length ||
        bet.yourScoreA != null ||
        bet.yourScoreB != null)
    ) {
      return "Waiting for other player to input stats";
    }

    if (
      gameType === "Shots Made" &&
      (bet.yourPlayer || bet.yourShots != null)
    ) {
      return "Waiting for other player to input stats";
    }

    if (gameType === "Other" && (bet.yourPlayer || bet.yourOutcome)) {
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
          <button className="help-button" onClick={() => setShowHelp(true)}>
            ?
          </button>
        </div>

        {/* Bet list display */}
        <div
          className="bet-list"
          style={{ paddingBottom: "100px", overflowY: "auto" }}
        >
          {visibleBets.map((bet) => (
            <div className="bet-card" key={bet.id}>
              <div className="bet-top">
                <span className="poster-time">
                  {bet.poster} · {formatTimeAgo(bet.timePosted)}
                </span>
              </div>
              <div className="subject">{bet.matchup}</div>
              <div className="game-played">Game: {bet.gamePlayed}</div>
              <div className="bet-bottom">
                <div className="amount">{bet.amount} caps </div>
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

                  const numPlayers = getNumPlayers(bet.gameSize || "2v2");
                  setYourTeamA(Array(numPlayers).fill({ name: "", score: "" }));
                  setYourTeamB(Array(numPlayers).fill({ name: "", score: "" }));

                  // Reset all state fields for shots made

                  // Reset for other
                }}
              >
                Enter Stats
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Help modal */}
      {showHelp && (
        <div className="help-modal">
          <div className="help-content">
            <h3>How to Enter Stats</h3>
            <p>While entering player stats, please follow these guidelines:</p>
            <p>
              Enter each player's real name with the first letter capitalized.
            </p>
            <p>ie: "Nate", "Mike", "Stryker"</p>
            <p>
              For Score bets, enter each side's total points at end of game.
            </p>
            <p>
              For Shots Made, enter the number of successful shots made by the
              player.
            </p>
            <p>For Other, enter the stat value relevant to the custom line.</p>
            <p>
              Entering stats and player names accurately is crucial for
              confirming matches and tracking stats.
            </p>
            <p>
              In order for a match to be confirmed both players must have
              matching players and stats.
            </p>
            <p>
              If you have a disagreement on stats, please communicate with the
              other player.
            </p>
            <p>
              If a disagreement persists feel free to reach out to the
              developers.
            </p>
            <button onClick={() => setShowHelp(false)}>Close</button>
          </div>
        </div>
      )}

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
                  value={yourShots}
                  onChange={(e) => setYourShots(e.target.value)}
                  className="modal-input"
                />
              </>
            )}

            {getGameType() === "Score" && (
              <>
                <h4>Your Team A</h4>
                {yourTeamA.map((player, i) => (
                  <div key={`teamA-${i}`}>
                    <div className="team-player-row">
                      <input
                        type="text"
                        placeholder={`Player ${i + 1} Name`}
                        value={player.name}
                        onChange={(e) => {
                          const newTeam = [...yourTeamA];
                          newTeam[i] = { ...newTeam[i], name: e.target.value };
                          setYourTeamA(newTeam);
                        }}
                        className="modal-input"
                      />
                    </div>
                  </div>
                ))}
                <input
                  type="number"
                  placeholder="Total Score for Team A"
                  value={yourScoreA}
                  onChange={(e) => setYourScoreA(Number(e.target.value))}
                  className="modal-input"
                />

                <h4>Your Team B</h4>
                {yourTeamB.map((player, i) => (
                  <div key={`teamB-${i}`}>
                    <div className="team-player-row">
                      <input
                        type="text"
                        placeholder={`Player ${i + 2} Name`}
                        value={player.name}
                        onChange={(e) => {
                          const newTeam = [...yourTeamB];
                          newTeam[i] = { ...newTeam[i], name: e.target.value };
                          setYourTeamB(newTeam);
                        }}
                        className="modal-input"
                      />
                    </div>
                  </div>
                ))}
                <input
                  type="number"
                  placeholder="Total Score for Team B"
                  value={yourScoreB}
                  onChange={(e) => setYourScoreB(Number(e.target.value))}
                  className="modal-input"
                />
              </>
            )}

            {getGameType() === "Other" && (
              <input
                type="number"
                placeholder="Describe Outcome"
                value={yourOutcome}
                onChange={(e) => setYourOutcome(e.target.value)}
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
