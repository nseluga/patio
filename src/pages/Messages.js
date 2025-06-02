import React from "react";
import BottomNav from "../components/BottomNav";
import "./Messages.css";

const dummyConversations = [
  { id: 1, name: "PlayerOne", lastMessage: "Yo did you input?", time: "2m ago" },
  { id: 2, name: "PlayerTwo", lastMessage: "GG that was insane", time: "10m ago" },
  { id: 3, name: "PlayerThree", lastMessage: "I'll send it rn", time: "1h ago" },
];

const Messages = () => {
  const handleOpenChat = (id) => {
    console.log("Open chat with ID:", id);
    // Use navigate(`/chat/${id}`) once routing is set up
  };

  const handleDelete = (id) => {
    console.log("Delete conversation with ID:", id);
    // Add deletion logic here
  };

  return (
    <div className="messages-container">
      <div className="messages-header">Messages</div>

      <div className="flex-1 overflow-y-auto px-4 space-y-4 pb-20">
        {dummyConversations.map((conv) => (
          <div key={conv.id} className="message-card">
            <div className="message-info" onClick={() => handleOpenChat(conv.id)}>
              <div className="message-header">
                <span className="message-name">{conv.name}</span>
                <span className="message-time">{conv.time}</span>
              </div>
              <p className="message-preview">{conv.lastMessage}</p>
            </div>
            <button
              onClick={() => handleDelete(conv.id)}
              className="delete-button"
            >
              ×
            </button>
          </div>
        ))}
      </div>

      <BottomNav />
    </div>
  );
};

export default Messages;
