import BottomNav from '../components/BottomNav';
import { useState } from 'react';
import './PvP.css';

const bets = [
  {
    poster: 'nate',
    time: '2m ago',
    amount: '50 caps',
    matchup: 'Nate and Skib W vs Drake and Mike: Caps',
    line: 'Over 2.5',
  },
  {
    poster: 'mike',
    time: '10m ago',
    amount: '10000 caps',
    matchup: 'Logan Bedtime',
    line: 'Under 10.5',
  },
];

export default function PvP() {
  const [showModal, setShowModal] = useState(false);
  const [gameType, setGameType] = useState("Shots Made");

  return (
    <>
      <div className="pvp-page">
        <div className="pvp-header">
          <h2 className="pvp-title">PvP Bets</h2>
          <button 
            className="create-bet-button"
            onClick={() => setShowModal(true)}
            >＋
          </button>
        </div>
  
        <div className="bet-list">
          {bets.map((bet, index) => (
            <div className="bet-card" key={index}>
              <div className="bet-top">
                <span className="poster-time">{bet.poster} · {bet.time}</span>
                <button className="dismiss-button">×</button>
              </div>
  
              <div className="subject">{bet.matchup}</div>
  
              <div className="bet-bottom">
                <div className="amount">{bet.amount}</div>
                <div className="line">{bet.line}</div>
              </div>
  
              <button className="accept-button">Accept</button>
            </div>
          ))}
        </div>

        {showModal && (
          <div className="bet-modal-overlay">
            <div className="bet-modal">
              <h3>Create a Bet</h3>

              <input type="text" placeholder="Matchup" className="modal-input" />
              <input 
                type="number"
                step="any"
                placeholder="Amount (caps)"
                className="modal-input"
              />
              <input
                type="number"
                step="any"
                placeholder="Line"
                className="modal-input"
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

              <div className="modal-actions">
                <button onClick={() => setShowModal(false)} className="cancel-button">Cancel</button>
                <button className="confirm-button">Post</button>
              </div>
            </div>
          </div>
        )}

      </div>
  
      <BottomNav />
    </>
  );
}
