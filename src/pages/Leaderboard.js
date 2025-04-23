import BottomNav from '../components/BottomNav';
import { useState, useEffect } from 'react';

export default function Leaderboard() {
  const [players, setPlayers] = useState([]);
  useEffect(() => {
    fetch('http://localhost:5001/leaderboard')
      .then(res => {
        console.log("Raw response:", res);
        return res.json();
      })
      .then(data => {
        console.log('Fetched leaderboard:', data);
        setPlayers(data);
      })
      .catch(err => {
        console.error('Failed to fetch leaderboard:', err);
        alert('Failed to load leaderboard. Check console for details.');
      });
  }, []);
    return (
      <div className="leaderboard-page">
        <BottomNav />

        <h2>Leaderboard</h2>
  
        <div className="leaderboard-list">
          {players.map((player, index) => (
            <div key={index} className="leaderboard-entry">
              <span>#{index + 1}</span>
              <span>{player.name}</span>
              <span>{player.caps} caps</span>
            </div>
          ))}
        </div>
    </div>
  );
}
