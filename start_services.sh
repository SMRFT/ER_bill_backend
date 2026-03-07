#!/bin/bash

# This script is for Linux servers

cleanup() {
    echo "Stopping services..."
    kill $(jobs -p) 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

echo "Starting Django Server on port 2111..."
# Using nohup to keep it running in the background
nohup python3 manage.py runserver 0.0.0.0:2111 > server.log 2>&1 &

echo "Starting Automation Worker..."
nohup python3 manage.py automate_results > worker.log 2>&1 &

echo "Services started with nohup. Logs: server.log, worker.log"
