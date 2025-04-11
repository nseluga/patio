import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import BottomNav from '../components/BottomNav';

const Messages = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: "Welcome to Vegas Chat 🎰!",
      sender: "System",
      timestamp: new Date(),
    },
  ]);
  const [newMessage, setNewMessage] = useState("");
  const messagesEndRef = useRef(null);
  const navigate = useNavigate();

  const sendMessage = () => {
    if (newMessage.trim() === "") return;
    const newMsg = {
      id: messages.length + 1,
      text: newMessage,
      sender: "You",
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newMsg]);
    setNewMessage("");
  };

  const formatTime = (date) =>
    date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  const handleHomeClick = () => {
    navigate("/");
  };

  return (
    <div
      className="w-screen h-screen flex flex-col relative"
      style={{
        background: "linear-gradient(to bottom, #ffdddd, #cc4444)",
        fontFamily: "'Luckiest Guy', cursive",
        color: "#2d2d2d",
      }}
    >
      {/* Header */}
      <header className="p-4 text-white text-2xl text-center font-bold shadow">
        🎲 Vegas Chat Room 🎲
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-2 pb-32 space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${
              msg.sender === "You" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`px-4 py-2 max-w-xs rounded-xl shadow ${
                msg.sender === "You"
                  ? "bg-yellow-400 text-black rounded-br-none"
                  : "bg-white bg-opacity-80 text-gray-800 rounded-bl-none"
              }`}
            >
              <p className="text-sm font-bold mb-1">
                {msg.sender}:{' '}
                <span className="font-normal">{msg.text}</span>
              </p>
              <p className="text-xs text-gray-600 text-right">
                {formatTime(new Date(msg.timestamp))}
              </p>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <BottomNav />

      {/* Message Input Area */}
      <div className="absolute bottom-16 left-0 w-full bg-white/80 border-t p-4 flex gap-2 backdrop-blur-md">
        <input
          type="text"
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          className="flex-1 border border-gray-300 p-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-400 text-black"
        />
        <button
          onClick={sendMessage}
          className="bg-yellow-500 text-white px-4 py-2 rounded-lg hover:bg-yellow-600 transition"
        >
          Send
        </button>
      </div>

      {/* Bottom Toolbar */}
      <div className="fixed bottom-0 left-0 w-full flex justify-around items-center bg-green-200 border-t border-green-300 shadow-inner h-16">
        <button
          onClick={handleHomeClick}
          className="text-green-900 px-6 py-2 rounded-md font-bold text-lg hover:bg-green-300 transition"
        >
          🏠 Home
        </button>
        {/* Placeholder for future buttons */}
        <button className="text-green-900 px-6 py-2 rounded-md font-bold text-lg opacity-50">
          🔒 Coming Soon
        </button>
      </div>
    </div>
  );
};

export default Messages;
