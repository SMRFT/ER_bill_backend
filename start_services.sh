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
export SECURITY_DISABLED=true && python3 manage.py runserver 0.0.0.0:2111 --settings=ER_bill_backend.settings-prod

echo "Starting Automation Worker..."
python3 manage.py automate_resultsyy

echo "Services started with nohup. Logs: server.log, worker.log"
