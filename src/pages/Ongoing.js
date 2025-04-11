import BottomNav from '../components/BottomNav';
import './PvP.css'; // reuse the same styles for now

export default function Ongoing() {
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
              <button className="dismiss-button">×</button>
            </div>
            <div className="subject">Nate vs Logan: Final Score</div>
            <div className="bet-bottom">
              <div className="amount">75 caps</div>
              <div className="line">Line: 11.5</div>
            </div>
            <button className="accept-button">Enter Stats</button>
          </div>
        </div>
      </div>

      <BottomNav />
    </>
  );
}