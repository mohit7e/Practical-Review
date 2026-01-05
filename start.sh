#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Practical Review"
echo "================"
echo ""

# Stop existing
pkill -f "python main.py" 2>/dev/null
pkill -f "http.server 3000" 2>/dev/null
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null
sleep 2

# Start backend
echo "Starting backend..."
cd "$SCRIPT_DIR/backend"
source venv/bin/activate
python main.py &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend..."
cd "$SCRIPT_DIR/frontend"
python3 -m http.server 3000 &
FRONTEND_PID=$!

sleep 3

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "Backend: http://localhost:8000"
    if curl -s http://localhost:8000/health | grep -q '"ai_available":true'; then
        echo "AI: Enabled"
    else
        echo "AI: Disabled (set AWS_BEARER_TOKEN_BEDROCK)"
    fi
else
    echo "Backend failed to start"
fi

echo "Frontend: http://localhost:3000"
echo ""
open "http://localhost:3000"

echo "Press Ctrl+C to stop"
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
