#!/bin/bash

# Change to the directory where the script is located
cd "$(dirname "$0")"

# Run the job alert script in the background
nohup python3 job_alert.py > job_alerts.log 2>&1 &

# Get the process ID
PID=$!

# Print the process ID
echo "Job alert system started with PID: $PID"
echo "To stop it, run: kill $PID"

# Save the PID to a file for later reference
echo $PID > job_alert.pid 