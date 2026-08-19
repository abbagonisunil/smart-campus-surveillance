# 🎓 Smart Campus AI Surveillance System

A real-time intelligent surveillance system combining YOLOv8 computer vision, Node.js + Express backend with Socket.IO, and a modern React dashboard.

---

## 🏗️ System Architecture

1. **AI Detection Module (`ai-module/`)**:
   - Uses Ultralytics YOLOv8n to detect persons and monitor predefined restricted zones.
   - Triggers real-time intrusion alerts sent via WebSockets (`python-socketio`) to the backend.
   - Supports webcam (auto-detect index 0/1), video files, headless mode, or synthetic demo simulation.

2. **Backend Server (`backend/`)**:
   - Express REST API & Socket.IO server on port `5001`.
   - JWT authentication & bcrypt password hashing.
   - MongoDB database for storing alerts and users with auto-seeding default credentials.
   - Real-time event broadcasting to connected frontend clients.

3. **Frontend Dashboard (`frontend/`)**:
   - React application running on port `3000`.
   - Live real-time surveillance dashboard, alert logs, analytics with Recharts, and camera feed status.

---

## 🔑 Default Credentials

- **Username**: `admin`
- **Password**: `admin123`

---

## 🚀 How to Run

### Quick Start (All-in-One):
```bash
./start.sh
```

### Manual Component Start:

1. **Start Backend**:
   ```bash
   cd backend
   node server.js
   ```

2. **Start Frontend**:
   ```bash
   cd frontend
   npm start
   ```

3. **Start AI Detection Module**:
   ```bash
   # Auto-detect camera (or demo fallback)
   ./venv/bin/python ai-module/decoder.py

   # Specific camera (e.g. camera 0 or 1)
   ./venv/bin/python ai-module/decoder.py --source 0

   # Demo simulation mode
   ./venv/bin/python ai-module/decoder.py --source demo

   # Headless mode (no OpenCV GUI window)
   ./venv/bin/python ai-module/decoder.py --headless
   ```

---

## 🌐 URLs
- **Web App**: [http://localhost:3000](http://localhost:3000)
- **API Server**: [http://localhost:5001](http://localhost:5001)
