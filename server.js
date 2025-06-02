// Import required modules
const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const cors = require("cors");

// Create Express app and HTTP server
const app = express();
const server = http.createServer(app);

// Initialize Socket.IO server with CORS settings
const io = new Server(server, {
  cors: {
    origin: "*", // Allow all origins (change for production!)
  },
});

// Enable CORS for HTTP requests
app.use(cors());

// Handle WebSocket connections
io.on("connection", (socket) => {
  console.log("User connected:", socket.id);

  // Handle incoming messages from a client
  socket.on("send_message", (message) => {
    // Broadcast message to all other connected clients
    socket.broadcast.emit("receive_message", message);
  });

  // Handle client disconnect
  socket.on("disconnect", () => {
    console.log("User disconnected:", socket.id);
  });
});

// Start server on specified port
const PORT = 3001;
server.listen(PORT, () => console.log(`Server running on port ${PORT}`));
