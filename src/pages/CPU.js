import BottomNav from '../components/BottomNav';
import './PvP.css'; // reuse the styles

export default function CPU() {
  return (
    <>
      <div className="pvp-page">
        <div className="pvp-header">
          <h2 className="pvp-title">CPU Bets</h2>
        </div>

        <div className="bet-list">
          <div className="bet-card">
            <div className="bet-top">
              <span className="poster-time">CPU · just now</span>
              <button className="dismiss-button">×</button>
            </div>
            <div className="subject">House Line: Mike vs CPU</div>
            <div className="bet-bottom">
              <div className="amount">40 caps</div>
              <div className="line">Line: Over 12.0</div>
            </div>
            <button className="accept-button">Accept</button>
          </div>
        </div>
      </div>

      <BottomNav />
    </>
  );
}