import { User } from "lucide-react";
import BottomNav from "../components/BottomNav";
import "./Profile.css";

export default function Profile() {
  return (
    <div className="profile-container">
      <div className="profile-inner">
        {/* Profile Picture */}
        <div className="profile-pic">
          <User className="w-12 h-12 text-black" />
        </div>

        {/* Stats Row */}
        <div className="profile-stats">
          <div>
            <p className="profile-stat-number">#</p>
            <p className="profile-stat">caps</p>
          </div>
          <div>
            <p className="profile-stat-number">#</p>
            <p className="profile-stat">bets won</p>
          </div>
          <div>
            <p className="profile-stat-number">#</p>
            <p className="profile-stat">bets played</p>
          </div>
        </div>

        {/* Story Buttons */}
        <div className="story-buttons">
          <div className="story-button">?</div>
          <div className="story-button">?</div>
          <div className="story-button">?</div>
        </div>

        {/* Recent Bets */}
        <div className="recent-bets-section">
          <h2 className="recent-bets-title">Recent Bets</h2>
          <div className="bet-card">
            <div className="bet-top">
              <span className="poster-time">SS</span>
              <span>1h</span>
              <button className="dismiss-button">×</button>
            </div>
            <div className="subject">Caps Made Over</div>
            <div className="bet-bottom">
              <span>SS</span>
              <span>15.5</span>
            </div>
            <button className="accept-button">Shots made</button>
          </div>
        </div>
      </div>

      {/* Bottom Nav */}
      <BottomNav />
    </div>
  );
}
