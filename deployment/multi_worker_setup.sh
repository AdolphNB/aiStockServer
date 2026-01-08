#!/bin/bash
# Multi-worker setup script for load balancing
# This script starts multiple uvicorn workers on different ports
# Use this if you prefer manual process management over systemd

# Configuration
APP_MODULE="app.main:app"
HOST="127.0.0.1"
START_PORT=8001
NUM_WORKERS=4
LOG_DIR="/var/log/aistock"
PID_DIR="/var/run/aistock"

# Create directories if they don't exist
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# Function to start a worker
start_worker() {
    local port=$1
    local worker_num=$2
    
    echo "Starting worker $worker_num on port $port..."
    
    uvicorn "$APP_MODULE" \
        --host "$HOST" \
        --port "$port" \
        --log-config logging.conf \
        --access-log \
        >> "$LOG_DIR/worker_${worker_num}.log" 2>&1 &
    
    local pid=$!
    echo $pid > "$PID_DIR/worker_${worker_num}.pid"
    echo "Worker $worker_num started with PID $pid"
}

# Function to stop all workers
stop_workers() {
    echo "Stopping all workers..."
    
    for pid_file in "$PID_DIR"/*.pid; do
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                echo "Stopping process $pid..."
                kill "$pid"
            fi
            rm "$pid_file"
        fi
    done
    
    echo "All workers stopped."
}

# Function to check worker status
status_workers() {
    echo "Checking worker status..."
    
    for pid_file in "$PID_DIR"/*.pid; do
        if [ -f "$pid_file" ]; then
            worker_name=$(basename "$pid_file" .pid)
            pid=$(cat "$pid_file")
            
            if kill -0 "$pid" 2>/dev/null; then
                echo "$worker_name (PID $pid) is running"
            else
                echo "$worker_name (PID $pid) is not running"
            fi
        fi
    done
}

# Main script
case "$1" in
    start)
        echo "Starting $NUM_WORKERS workers..."
        for ((i=1; i<=NUM_WORKERS; i++)); do
            port=$((START_PORT + i - 1))
            start_worker "$port" "$i"
        done
        echo "All workers started."
        ;;
    
    stop)
        stop_workers
        ;;
    
    restart)
        stop_workers
        sleep 2
        $0 start
        ;;
    
    status)
        status_workers
        ;;
    
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
