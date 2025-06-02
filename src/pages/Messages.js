// Import dependencies and components
import React from "react";
import BottomNav from "../components/BottomNav";
import "./Messages.css"; // Styles for message list UI

// Sample conversation data (placeholder for now)
const dummyConversations = [
  { id: 1, name: "PlayerOne", lastMessage: "Yo did you input?", time: "2m ago" },
  { id: 2, name: "PlayerTwo", lastMessage: "GG that was insane", time: "10m ago" },
  { id: 3, name: "PlayerThree", lastMessage: "I'll send it rn", time: "1h ago" },
];

// Messages page component
const Messages = () => {
  // Placeholder for opening a conversation
  const handleOpenChat = (id) => {
    console.log("Open chat with ID:", id);
    // TODO: Use navigate(`/chat/${id}`) when routing is added
  };

  // Placeholder for deleting a conversation
  const handleDelete = (id) => {
    console.log("Delete conversation with ID:", id);
    // TODO: Add deletion logic here
  };

  // Render message cards and layout
  return (
    <div className="messages-container">
      {/* Page header */}
      <div className="messages-header">Messages</div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto px-4 space-y-4 pb-20">
        {dummyConversations.map((conv) => (
          <div key={conv.id} className="message-card">
            <div
              className="message-info"
              onClick={() => handleOpenChat(conv.id)}
            >
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

      {/* Bottom navigation bar */}
      <BottomNav />
    </div>
  );
};

export default Messages;
