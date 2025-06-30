import React from "react";
import BottomNav from "../components/BottomNav";
import "./Messages.css";

export default function Messages() {
  return (
    <div className="messages-page">
      <div className="pvp-header">
        <h1 className="pvp-title">Messages</h1>
      </div>
      <div className="coming-soon-wrapper">
        <h2 className="coming-soon-text">Coming Soon</h2>
      </div>
      <BottomNav />
    </div>
  );
}
