import { useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import UserContext from "../UserContext";
import BottomNav from "../components/BottomNav";
import "./Profile.css";
import back1 from "../assets/images/back1.png";
import defaultProfile from "../assets/images/defaultProfile.png";
import api from "../api";

export default function Profile() {
  const { user, setUser } = useContext(UserContext);
  const navigate = useNavigate();
  const [selectedImage, setSelectedImage] = useState(null);
  console.log("👤 User from context:", user);


  useEffect(() => {
      if (!user) {
        navigate("/login");
      }
    }, [user, navigate]);

  const handleLogout = () => {
    localStorage.removeItem("playerId");
    localStorage.removeItem("token");
    setUser(null);
    navigate("/login");
  };

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setSelectedImage(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRemovePhoto = () => {
    setSelectedImage(null);
  };

  const handleCleanupBets = async () => {
    try {
      const res = await api.post("/cleanup_bets", null, {
        headers: { Authorization: `Bearer ${user.token}` },
      });
      alert("✅ Cleanup successful!");
      console.log("🧼 Cleanup response:", res.data);
    } catch (err) {
      console.error("❌ Cleanup failed:", err);
      alert("❌ Cleanup failed — see console.");
    }
  };

  if (!user) return null;

  return (
    <div
      className="profile-container"
      style={{ backgroundImage: `url(${back1})` }}
    >
      <div className="profile-box">
        <div className="profile-header">
          <h1 className="profile-title">PROFILE</h1>
          <button onClick={handleLogout} className="logout-button">
            Log Out
          </button>
        </div>
        

        {/* Profile picture */}
        <div className="profile-pic-wrapper">
          <div className="profile-pic">
            {selectedImage ? (
              <img
                src={selectedImage}
                alt="profile"
                className="profile-pic-img"
              />
            ) : (
              <img
                src={defaultProfile}
                alt="default"
                className="profile-pic-img"
              />
            )}
          </div>
          <p className="profile-username">{user.username}</p>

          {/* Upload + Remove */}
          <input
            type="file"
            accept="image/*"
            id="file-upload"
            onChange={handleImageUpload}
            className="file-input"
          />
          <div className="edit-photo-buttons">
            <label htmlFor="file-upload" className="edit-button">
              Edit Photo
            </label>
            {selectedImage && (
              <button className="remove-button" onClick={handleRemovePhoto}>
                Remove Photo
              </button>
            )}
          </div>
        </div>

        {/* Stats section */}
        <div className="profile-stats-block">
          <div className="profile-stat">
            <div className="profile-stat-number">{user.caps_balance ?? 0}</div>
            <div className="profile-stat-label">caps</div>
          </div>
          <div className="profile-stat">
            <div className="profile-stat-number">{user.pvp_bets_won ?? 0}</div>
            <div className="profile-stat-label">bets won</div>
          </div>
          <div className="profile-stat">
            <div className="profile-stat-number">{user.pvp_bets_played ?? 0}</div>
            <div className="profile-stat-label">bets played</div>
          </div>
        </div>

        {/* Recent Bets */}

        <BottomNav />
      </div>
      <div className="recent-bets-section">
        <div className="recent-bets-wrap-box">
          <h2 className="recent-bets-title">Recent Bets:</h2>{" "}
        </div>
        {user.recent_bets?.map((bet, index) => (
          <div className="recent-bet-card" key={index}>
            <div className="bet-header">
              <span className="poster-time">{bet.poster}</span>
              <span>{bet.timePosted}</span>
              <button className="dismiss-button">×</button>
            </div>
            <div className="bet-details">
              <div className="subject">{bet.subject}</div>
              <div>{bet.player}</div>
              <div>{bet.line}</div>
            </div>
            <div className="bet-tag">{bet.gameType}</div>
          </div>
        ))}
      </div>
      <button onClick={handleCleanupBets} className="cleanup-button">🧹
          <span className="tooltip-text">CLEAN UP EXPIRED BETS</span>
      </button>
    </div>
  );
}
