const express = require('express');
const http = require('http');
const socketIO = require('socket.io');
const mongoose = require('mongoose');
const cors = require('cors');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
require('dotenv').config();

const app = express();
const server = http.createServer(app);
const io = socketIO(server, { cors: { origin: "*" } });

app.use(cors());
app.use(express.json());

// MongoDB connection
mongoose.connect('mongodb://localhost:27017/smartcampus')
    .then(async () => {
        console.log('✅ MongoDB connected');
        // Auto-seed default admin user if not existing
        try {
            const adminExists = await User.findOne({ username: 'admin' });
            if (!adminExists) {
                const hashedPassword = await bcrypt.hash('admin123', 10);
                await User.create({ username: 'admin', password: hashedPassword, role: 'admin' });
                console.log('👤 Default admin user created (admin / admin123)');
            }
        } catch (seedErr) {
            console.error('Error seeding admin user:', seedErr);
        }
    })
    .catch(err => console.log('❌ MongoDB error:', err));

// Schemas
const userSchema = new mongoose.Schema({
    username: String,
    password: String,
    role: { type: String, default: 'guard' }
});
const User = mongoose.model('User', userSchema);

const alertSchema = new mongoose.Schema({
    type: String,
    message: String,
    camera: String,
    timestamp: { type: Date, default: Date.now }
});
const Alert = mongoose.model('Alert', alertSchema);

// Middleware - verify token
const verifyToken = (req, res, next) => {
    const token = req.headers['authorization']?.split(' ')[1];
    if (!token) return res.status(401).json({ message: 'No token' });
    try {
        req.user = jwt.verify(token, 'smartcampus_secret');
        next();
    } catch {
        res.status(401).json({ message: 'Invalid token' });
    }
};

// Routes
app.get('/', (req, res) => res.json({ message: 'Smart Campus API running', status: 'healthy' }));

// Register (run once to create admin)
app.post('/auth/register', async (req, res) => {
    const { username, password, role } = req.body;
    const existing = await User.findOne({ username });
    if (existing) return res.status(400).json({ message: 'User already exists' });
    const hashed = await bcrypt.hash(password, 10);
    const user = new User({ username, password: hashed, role: role || 'guard' });
    await user.save();
    res.json({ message: 'User created successfully' });
});

// Login
app.post('/auth/login', async (req, res) => {
    const { username, password } = req.body;
    const user = await User.findOne({ username });
    if (!user) return res.status(400).json({ message: 'User not found' });
    const valid = await bcrypt.compare(password, user.password);
    if (!valid) return res.status(400).json({ message: 'Invalid password' });
    const token = jwt.sign(
        { id: user._id, username: user.username, role: user.role },
        'smartcampus_secret',
        { expiresIn: '24h' }
    );
    res.json({ token, username: user.username, role: user.role });
});

// Get alerts (protected)
app.get('/alerts', verifyToken, async (req, res) => {
    const alerts = await Alert.find().sort({ timestamp: -1 }).limit(100);
    res.json(alerts);
});

// Clear alerts (protected)
app.delete('/alerts', verifyToken, async (req, res) => {
    await Alert.deleteMany({});
    res.json({ message: 'Alerts cleared' });
});

// Socket
io.on('connection', (socket) => {
    console.log('📡 Client connected:', socket.id);
    socket.on('detection_alert', async (data) => {
        console.log('⚠️  Alert received:', data);
        const alert = new Alert({
            type: data.type || 'intrusion',
            message: data.message || 'Intrusion detected',
            camera: data.camera || 'CAM-01',
            timestamp: data.timestamp ? new Date(data.timestamp) : new Date()
        });
        const savedAlert = await alert.save();
        io.emit('new_alert', savedAlert);
    });
    socket.on('disconnect', () => console.log('Client disconnected:', socket.id));
});

const PORT = process.env.PORT || 5001;
server.listen(PORT, () => console.log(`🚀 Server running on port ${PORT}`));