// Import routing and styles
import { Link, useLocation } from 'react-router-dom';
import './BottomNav.css';

// Bottom navigation component
export default function BottomNav() {
  const location = useLocation(); // Get current route

  return (
    // Navigation container
    <nav className="bottom-nav">
      {/* Leaderboard tab */}
      <div className="nav-item">
        <Link to="/leaderboard" className={location.pathname === '/leaderboard' ? 'active' : ''}>Leaderboard 🏆</Link>
      </div>

      {/* Home/game tab */}
      <div className="nav-item">
        <Link to="/pvp" className={location.pathname === '/pvp' ? 'active' : ''}>PvP 🎮</Link>
      </div>

      {/* CPU/house tab */}
      <div className="nav-item">
        <Link to="/house" className={location.pathname === '/house' ? 'active' : ''}>House 🏠</Link>
      </div>

      {/* Ongoing bets tab */}
      <div className="nav-item">
        <Link to="/ongoing" className={location.pathname === '/ongoing' ? 'active' : ''}>Ongoing ⏳</Link>
      </div>

      {/* Messages tab */}
      <div className="nav-item">
        <Link to="/messages" className={location.pathname === '/messages' ? 'active' : ''}>Messages 💬</Link>
      </div>

      {/* Profile tab */}
      <div className="nav-item">
        <Link to="/profile" className={location.pathname === '/profile' ? 'active' : ''}>Profile 👤</Link>
      </div>
    </nav>
  );
}

