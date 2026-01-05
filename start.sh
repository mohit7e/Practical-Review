#!/bin/bash

# ============================================
# Refine - Document Correction App
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🔧 Refine - Document Correction"
echo "================================"
echo ""

# Kill existing processes
echo "Stopping any existing servers..."
pkill -f "python main.py" 2>/dev/null
pkill -f "http.server 3000" 2>/dev/null
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null
sleep 2

# Start backend
echo "Starting backend server..."
cd "$SCRIPT_DIR/backend"
source venv/bin/activate
python main.py &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend server..."
cd "$SCRIPT_DIR/frontend"
python3 -m http.server 3000 &
FRONTEND_PID=$!

sleep 3

# Check status
echo ""
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    HEALTH=$(curl -s http://localhost:8000/health)
    echo "✅ Backend running at http://localhost:8000"
    
    if echo "$HEALTH" | grep -q '"ai_available":true'; then
        echo "✅ Amazon Nova AI ENABLED"
    else
        echo "⚠️  AI not available (check AWS_BEARER_TOKEN_BEDROCK in .env)"
    fi
else
    echo "❌ Backend failed to start"
fi

echo "✅ Frontend running at http://localhost:3000"
echo ""
echo "Opening browser..."
open "http://localhost:3000"

echo ""
echo "Press Ctrl+C to stop all servers"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
