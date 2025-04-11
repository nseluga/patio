import BottomNav from '../components/BottomNav';

export default function Leaderboard() {
    return (
      <div className="leaderboard-page">
        <BottomNav />

        <h2>Leaderboard</h2>
  
        <div className="leaderboard-entry">
          <span>#1</span>
          <span>Nate</span>
          <span>420 caps</span>
          <span>12W - 0L</span>
        </div>

        <div className="leaderboard-entry">
          <span>#2</span>
          <span>Skib</span>
          <span>69 caps</span>
          <span>10W - 6L</span>
        </div>

        <div className="leaderboard-entry">
          <span>#3</span>
          <span>Mike</span>
          <span>69 caps</span>
          <span>8W - 8L</span>
        </div>
    </div>
  );
}
