import React from 'react';
import BottomNav from '../components/BottomNav';
import './Profile.css'; // optional, for styling

export default function Profile() {
  return (
    <div className="profile-page">
      <h2>Your Profile</h2>
      <div className="profile-info">
        <p><strong>Username:</strong> nate</p>
        <p><strong>Level:</strong> 12</p>
        <p><strong>Caps:</strong> 2,430</p>
      </div>

      <BottomNav />
    </div>
  );
}
