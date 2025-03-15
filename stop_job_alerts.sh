#!/bin/bash

# Check if the PID file exists
if [ -f "job_alert.pid" ]; then
    # Read the PID from the file
    PID=$(cat job_alert.pid)
    
    # Check if the process is still running
    if ps -p $PID > /dev/null; then
        # Kill the process
        kill $PID
        echo "Job alert system stopped (PID: $PID)"
    else
        echo "Job alert system not running (PID: $PID)"
    fi
    
    # Remove the PID file
    rm job_alert.pid
else
    echo "Job alert system not running (PID file not found)"
fi 