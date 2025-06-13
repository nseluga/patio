// import { User } from "lucide-react";       May need to put back when giving users ability to change from default profile pic
import { useContext, useEffect } from "react";
import UserContext from "../UserContext";
import BottomNav from "../components/BottomNav";
import { useNavigate } from "react-router-dom";
import "./Profile.css";

export default function Profile() {
  const { user, setUser } = useContext(UserContext);

  // Optional: redirect if no user
  const navigate = useNavigate();
  useEffect(() => {
    if (!user) {
      navigate("/login");
    }
  }, [user, navigate]);

  const handleLogout = () => {
    // Clear user data from localStorage or context
    localStorage.removeItem("playerId");
    localStorage.removeItem("token"); // if you're storing a JWT

    setUser(null);

    // Redirect to login page (or landing page)
    navigate("/login");
  };

  if (!user) return null; // avoid rendering empty page before redirect

  return (
    <div className="profile-container">
      <div className="profile-inner">
        {/* Profile Header */}
        <div className="profile-header">
          <button onClick={handleLogout} className="logout-button">
            Log Out
          </button>
          <div className="profile-pic-wrapper">
            <div className="profile-pic">
              <span className="profile-initial">
                {user.username?.charAt(0).toUpperCase()}
              </span>
            </div>
            <p className="profile-username">{user.username}</p>
          </div>

          <div className="profile-stats-inline">
            <div className="profile-stat-block">
              <p className="profile-stat-number">{user.caps_balance}</p>
              <p className="profile-stat">caps</p>
            </div>
            <div className="profile-stat-block">
              <p className="profile-stat-number">{user.bets_won ?? 0}</p>
              <p className="profile-stat">bets won</p>
            </div>
            <div className="profile-stat-block">
              <p className="profile-stat-number">{user.bets_played ?? 0}</p>
              <p className="profile-stat">bets played</p>
            </div>
          </div>
        </div>

        {/* Story Buttons
        <div className="story-buttons">
          <div className="story-button">?</div>
          <div className="story-button">?</div>
          <div className="story-button">?</div>
        </div> */}

        {/* Recent Bets */}
        <div className="recent-bets-section">
          <h2 className="recent-bets-title">Recent Bets</h2>
          {user.recent_bets?.map((bet, index) => (
            <div className="bet-card" key={index}>
              <div className="bet-top">
                <span className="poster-time">{bet.poster}</span>
                <span>{bet.timePosted}</span>
                <button className="dismiss-button">×</button>
              </div>
              <div className="subject">{bet.subject}</div>
              <div className="bet-bottom">
                <span>{bet.player}</span>
                <span>{bet.line}</span>
              </div>
              <button className="accept-button">{bet.gameType}</button>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Nav */}
      <BottomNav />
    </div>
  );
}
