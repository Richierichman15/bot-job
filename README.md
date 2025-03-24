# Job Alert Bot

A Python-based job alert system that searches for job opportunities, sends notifications via email, and can now automatically prepare and submit job applications.

## New Feature: Bright Data Integration

The system now uses Bright Data's Web Unlocker API to scrape job listings from popular job sites and automate application submission. This provides greater reliability and bypass rate limiting issues with traditional APIs.

### Key Features

1. **Web Scraping**: Scrape job listings from Indeed, LinkedIn, and other job sites.
2. **Application Automation**: Automatically prepare and submit job applications with your resume and custom cover letters.
3. **History Tracking**: Track application history and maintain daily application limits.

## Setup

1. Clone this repository
2. Create a virtual environment: `python -m venv .venv`
3. Activate the virtual environment: `source .venv/bin/activate` (Linux/Mac) or `.venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Configure the environment variables in `.env` file
6. Upload your resume to the `resume` directory
7. Run `./update_jobbot.sh` to update with the latest features

## Configuration

The system is configured through environment variables in the `.env` file:

```
# API Settings
USE_MOCK_DATA=true  # Use mock data for testing
USE_BRIGHTDATA=true  # Use Bright Data for web scraping

# Bright Data API Settings
BRIGHTDATA_API_KEY=your_brightdata_api_key
BRIGHTDATA_ZONE=job_socket

# Resume Settings
RESUME_PATH=resume/your_resume.pdf
AUTO_SUBMIT_APPLICATIONS=true
COVER_LETTER_TEMPLATE=resume/cover_letter_template.txt
MAX_DAILY_APPLICATIONS=5
```

## Usage

### Running the Job Alert System

```bash
# Run once and exit
python job_alert.py --run-once

# Run continuously (checks at intervals defined in .env)
python job_alert.py

# Process pending applications only
python job_alert.py --apply-only

# Process a limited number of applications
python job_alert.py --apply-only --limit 2
```

### Automatic Job Applications

When `AUTO_SUBMIT_APPLICATIONS=true`, the system will:

1. Find job listings that match your criteria
2. Generate customized cover letters for each job
3. Prepare application packages with your resume
4. Process a limited number of applications per day
5. Track application history and success rates

Application packages are stored in the `applications` directory, organized by company and date.

## Application Report

View your application history in `applications/logs/application_history.json`, which includes:

- Total applications submitted
- Success and failure statistics
- Daily application counts
- Complete list of all applications with details

## Dependencies

- Python 3.6 or higher
- requests
- BeautifulSoup4
- python-dotenv
- lxml

## License

MIT

## Acknowledgements

This project uses the Bright Data Web Unlocker API for web scraping. 