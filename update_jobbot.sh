#!/bin/bash

echo "Updating Job Alert Bot with Bright Data integration..."

# Update code from git repository
git pull

# Install or update dependencies
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
else
    echo "Creating virtual environment..."
    python -m venv .venv
    source .venv/bin/activate
fi

echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p resume
mkdir -p applications
mkdir -p applications/logs

echo "Update completed successfully!"
echo ""
echo "To use the new features:"
echo "1. Update your .env file with Bright Data API credentials"
echo "2. Upload your resume to the 'resume' directory"
echo "3. Run 'python job_alert.py' to start the job alert system"
echo "4. Use 'python job_alert.py --apply-only' to process pending applications"
echo ""
echo "Happy job hunting!" 