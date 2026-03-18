// Import routing, styles, and icons
import { Link, useLocation } from 'react-router-dom';
import { Trophy, Swords, Home, Clock, MessageCircle, User } from 'lucide-react';
import './BottomNav.css';

// Bottom navigation component
export default function BottomNav() {
  const location = useLocation(); // Get current route

  const tabs = [
    { to: '/leaderboard', label: 'BOARD', icon: Trophy },
    { to: '/pvp', label: 'PvP', icon: Swords },
    { to: '/house', label: 'HOUSE', icon: Home },
    { to: '/ongoing', label: 'LIVE', icon: Clock },
    { to: '/messages', label: 'MSGS', icon: MessageCircle },
    { to: '/profile', label: 'ME', icon: User },
  ];

  return (
    <nav className="bottom-nav">
      {tabs.map(({ to, label, icon: Icon }) => {
        const isActive = location.pathname === to;
        return (
          <div key={to} className="nav-item">
            <Link to={to} className={isActive ? 'active' : ''}>
              <Icon size={isActive ? 22 : 20} strokeWidth={isActive ? 2.5 : 1.8} />
              <span className="nav-label">{label}</span>
            </Link>
          </div>
        );
      })}
    </nav>
  );
}
