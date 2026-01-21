#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting AIStock System...${NC}"

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if Python virtual environment exists
if [ -d "venv" ]; then
    echo -e "${GREEN}Using virtual environment...${NC}"
    source venv/bin/activate
else
    echo -e "${RED}Warning: Virtual environment not found. Using system python.${NC}"
fi

# Function to kill child processes on exit
cleanup() {
    echo -e "${RED}Stopping all services...${NC}"
    kill $(jobs -p) 2>/dev/null
    exit
}

# Trap SIGINT (Ctrl+C)
trap cleanup SIGINT

# Start API Server
echo -e "${GREEN}Starting API Server (Port 8000)...${NC}"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# Start Fetcher Service
echo -e "${GREEN}Starting Data Fetcher Service...${NC}"
python run_fetcher.py &
FETCHER_PID=$!

echo -e "${BLUE}System is running!${NC}"
echo -e "API Server PID: $API_PID"
echo -e "Fetcher PID: $FETCHER_PID"
echo -e "Press Ctrl+C to stop all services."

# Wait for all background processes
wait
