const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const cors = require("cors");

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: "*", // Adjust in production!
  },
});

app.use(cors());

io.on("connection", (socket) => {
  console.log("User connected:", socket.id);

  socket.on("send_message", (message) => {
    // Broadcast to everyone except the sender
    socket.broadcast.emit("receive_message", message);
  });

  socket.on("disconnect", () => {
    console.log("User disconnected:", socket.id);
  });
});

const PORT = 3001;
server.listen(PORT, () => console.log(`Server running on port ${PORT}`));
