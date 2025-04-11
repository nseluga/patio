import { Link, useLocation } from 'react-router-dom';
import './BottomNav.css';

export default function BottomNav() {
  const location = useLocation();

  return (
    <nav className="bottom-nav">
      <div className="nav-item"><Link to="/leaderboard" className={location.pathname === '/leaderboard' ? 'active' : ''}>🏆</Link></div>
      <div className="nav-item"><Link to="/" className={location.pathname === '/' ? 'active' : ''}>🎮</Link></div>
      <div className="nav-item"><Link to="/house" className={location.pathname === '/house' ? 'active' : ''}>🤖</Link></div>
      <div className="nav-item"><Link to="/ongoing" className={location.pathname === '/ongoing' ? 'active' : ''}>⏳</Link></div>
      <div className="nav-item no-border"><Link to="/messages" className={location.pathname === '/messages' ? 'active' : ''}>💬</Link></div>
    </nav>
  );
}