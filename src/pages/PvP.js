import BottomNav from '../components/BottomNav';
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
  return (
    <>
      <div className="pvp-page">
        <div className="pvp-header">
          <h2 className="pvp-title">PvP Bets</h2>
          <button className="create-bet-button">＋</button>
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
      </div>
  
      <BottomNav />
    </>
  );
}
