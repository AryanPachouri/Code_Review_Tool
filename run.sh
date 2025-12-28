#!/bin/bash

echo "============================================"
echo "Code Review Tool Launcher"
echo "============================================"
echo ""

# Check if we're in the right directory
if [ ! -d "backend" ]; then
    echo "ERROR: backend folder not found!"
    echo "Please run this script from the code-review-tool directory"
    exit 1
fi

if [ ! -d "frontend" ]; then
    echo "ERROR: frontend folder not found!"
    echo "Please run this script from the code-review-tool directory"
    exit 1
fi

# Detect terminal emulator
if command -v gnome-terminal &> /dev/null; then
    TERM_CMD="gnome-terminal --"
elif command -v xterm &> /dev/null; then
    TERM_CMD="xterm -e"
elif command -v konsole &> /dev/null; then
    TERM_CMD="konsole -e"
else
    # For macOS
    TERM_CMD="open -a Terminal"
fi

echo "Starting Backend Server..."
echo ""

# Start backend
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    osascript -e 'tell app "Terminal" to do script "cd \"'$(pwd)'/backend\" && source venv/bin/activate && python app.py"'
else
    # Linux
    $TERM_CMD bash -c "cd backend && source venv/bin/activate && python app.py; exec bash" &
fi

# Wait for backend
sleep 3

echo "Starting Frontend Server..."
echo ""

# Start frontend
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    osascript -e 'tell app "Terminal" to do script "cd \"'$(pwd)'/frontend\" && npm start"'
else
    # Linux
    $TERM_CMD bash -c "cd frontend && npm start; exec bash" &
fi

echo ""
echo "============================================"
echo "Both servers are starting!"
echo "============================================"
echo "Backend:  http://localhost:5000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Two new terminal windows should open."
echo "Press Ctrl+C to exit this script."
echo ""

# Keep script running
wait