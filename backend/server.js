const express = require('express');
const http = require('http');
const socketIO = require('socket.io');
const mongoose = require('mongoose');
const cors = require('cors');
require('dotenv').config();

const app = express();
const server = http.createServer(app);
const io = socketIO(server, { cors: { origin: "*" } });

app.use(cors());
app.use(express.json());

// MongoDB connection
mongoose.connect('mongodb://localhost:27017/smartcampus')
    .then(() => console.log('✅ MongoDB connected'))
    .catch(err => console.log('❌ MongoDB error:', err));

// Alert schema
const alertSchema = new mongoose.Schema({
    type: String,
    message: String,
    camera: String,
    timestamp: { type: Date, default: Date.now }
});
const Alert = mongoose.model('Alert', alertSchema);

// Routes
app.get('/', (req, res) => {
    res.json({ message: 'Smart Campus API running' });
});

// Get all alerts
app.get('/alerts', async (req, res) => {
    const alerts = await Alert.find().sort({ timestamp: -1 }).limit(50);
    res.json(alerts);
});

// Socket connection
io.on('connection', (socket) => {
    console.log('📡 Client connected:', socket.id);

    socket.on('detection_alert', async (data) => {
        console.log('⚠️  Alert received:', data);

        // Save to MongoDB
        const alert = new Alert(data);
        await alert.save();
        console.log('💾 Alert saved to database');

        // Broadcast to all dashboard clients
        io.emit('new_alert', data);
    });

    socket.on('disconnect', () => {
        console.log('Client disconnected:', socket.id);
    });
});

const PORT = process.env.PORT || 5001;
server.listen(PORT, () => {
    console.log(`🚀 Server running on port ${PORT}`);
});