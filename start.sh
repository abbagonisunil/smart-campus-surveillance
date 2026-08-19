#!/bin/bash

# Smart Campus Surveillance System Launcher

echo "=================================================="
echo "   🎓 Smart Campus Surveillance System"
echo "=================================================="

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 1. Check MongoDB
echo "🔍 Checking MongoDB..."
if ! mongosh --eval "db.adminCommand('ping')" --quiet > /dev/null 2>&1; then
    echo "⚠️ MongoDB is not running locally on port 27017."
    echo "Starting MongoDB via brew..."
    brew services start mongodb-community || brew services start mongodb-community@6.0 || true
    sleep 2
fi

if mongosh --eval "db.adminCommand('ping')" --quiet > /dev/null 2>&1; then
    echo "✅ MongoDB is running!"
else
    echo "❌ Could not connect to MongoDB. Please start MongoDB on port 27017."
fi

# 2. Start Backend
echo "🚀 Starting Node.js Backend on port 5001..."
(cd "$PROJECT_DIR/backend" && node server.js) &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# 3. Start Frontend
echo "💻 Starting React Frontend on port 3000..."
(cd "$PROJECT_DIR/frontend" && npm start) &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

# Function to handle shutdown
cleanup() {
    echo ""
    echo "🛑 Shutting down Smart Campus services..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

echo ""
echo "=================================================="
echo "🎉 System is running!"
echo "   👉 Dashboard: http://localhost:3000"
echo "   👉 Backend API: http://localhost:5001"
echo "   🔑 Default Login: admin / admin123"
echo "=================================================="
echo ""
echo "To start the YOLO AI Detection module in another tab:"
echo "   ./venv/bin/python ai-module/decoder.py"
echo ""
echo "Press Ctrl+C to stop backend and frontend."

wait
