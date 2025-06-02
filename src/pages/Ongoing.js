import { useState } from 'react';
import BottomNav from '../components/BottomNav';
import './PvP.css'; // assuming you're using shared styles

export default function Ongoing() {
  const [showModal, setShowModal] = useState(false);
  const [playerName, setPlayerName] = useState("Player Name");
  const gameType = "Shots Made";

  return (
    <>
      <div className="pvp-page">
        <div className="pvp-header">
          <h2 className="pvp-title">Ongoing Bets</h2>
        </div>

        <div className="bet-list">
          <div className="bet-card">
            <div className="bet-top">
              <span className="poster-time">nate · 1m ago</span>
            </div>
            <div className="subject">Nate vs Logan: Final Score</div>
            <div className="bet-bottom">
              <div className="amount">75 caps</div>
              <div className="line">Line: 11.5</div>
            </div>
            <button
              className="accept-button"
              onClick={() => setShowModal(true)}
            >
              Enter Stats
            </button>
          </div>
        </div>
      </div>

      {showModal && (
        <div className="bet-modal-overlay">
          <div className="bet-modal">
            <h3>Enter Stats</h3>

            {gameType === "Other" && (
              <input
                type="number"
                placeholder="Score"
                style={{ padding: '10px', fontSize: '16px' }}
              />
            )}
            
            {gameType === "Shots Made" && (
              <>
                <select
                  value={playerName}
                  onChange={(e) => setPlayerName(e.target.value)}
                  className="modal-input"
                >
                  <option value="Player Name">Player Name</option>
                  <option value="Other Players">Other Players</option>
                </select>

                <input
                  type="number"
                  placeholder="Shots Made"
                  style={{ padding: '10px', fontSize: '16px' }}
                />
              </>
            )}

            {gameType === "Score" && (
                <>
                    <select
                      value={playerName}
                      onChange={(e) => setPlayerName(e.target.value)}
                      className="modal-input"
                    >
                      <option value="Player Name">Player Name</option>
                      <option value="Other Players">Other Players</option>
                    </select>

                    <input
                    type="number"
                    placeholder="Score"
                    style={{ padding: '10px', fontSize: '16px' }}
                    />

                    <select
                      value={playerName}
                      onChange={(e) => setPlayerName(e.target.value)}
                      className="modal-input"
                    >
                      <option value="Player Name">Player Name</option>
                      <option value="Other Players">Other Players</option>
                    </select>

                    <input
                    type="number"
                    placeholder="Score"
                    style={{ padding: '10px', fontSize: '16px' }}
                    />
                </>
            )}

            <div className="modal-actions">
              <button
                onClick={() => setShowModal(false)}
                className="cancel-button"
              >
                Cancel
              </button>
              <button className="confirm-button">Submit</button>
            </div>
          </div>
        </div>
      )}

      <BottomNav />
    </>
  );
}