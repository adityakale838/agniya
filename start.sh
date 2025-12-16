#!/bin/bash

# AGNIYA Quick Start Script (Linux/macOS)

echo "========================================"
echo "  AGNIYA Web Application"
echo "  Professional Encryption Interface"
echo "========================================"
echo ""

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found at ./venv"
    echo "Please run: python3 -m venv venv"
    exit 1
fi

source venv/bin/activate

# Start Backend API Server
echo "Starting Backend API Server (ADVANCED)..."
python api/server_advanced.py &
BACKEND_PID=$!
sleep 3

# Start Frontend React App
echo ""
echo "Starting Frontend React App..."
cd webapp
npm run dev &
FRONTEND_PID=$!

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
