# Job Search Alert Bot

A Python application that automatically searches for job listings based on your criteria and sends email notifications for new opportunities.

## Features

- Search for jobs across multiple job titles and locations
- Support for multiple job search APIs (JSearch and Active Jobs DB)
- Filter jobs by minimum salary (supports both hourly and annual rates)
- Configurable search parameters through .env file
- Email notifications for new job listings
- API-based job searching with comprehensive results
- Optional AI processing for job description analysis

## Setup

1. Clone this repository
2. Create a `.env` file with your configuration (see `.env.example`)
3. Install dependencies: `pip install -r requirements.txt`
4. Run the job alert: `python job_alert.py`

## Environment Variables

Configuration is done through a `.env` file with the following variables:

```
# JSearch API credentials
JSEARCH_API_KEY=your_api_key
JSEARCH_API_HOST=jsearch.p.rapidapi.com

# Active Jobs DB API credentials
ACTIVEJOBS_API_KEY=your_api_key
ACTIVEJOBS_API_HOST=active-jobs-db.p.rapidapi.com

# Use multiple APIs
USE_MULTIPLE_APIS=true

# Email configuration
EMAIL_SENDER=your_email@example.com
EMAIL_PASSWORD=your_email_password
EMAIL_RECIPIENT=recipient@example.com
SMTP_SERVER=smtp.example.com
SMTP_PORT=587

# Job search parameters
JOB_TITLES=software developer,fullstack developer
JOB_LOCATIONS=usa,remote
JOB_REMOTE=true
MIN_SALARY=20
JOB_EMPLOYMENT_TYPES=FULLTIME,CONTRACT,PARTTIME
CHECK_INTERVAL_MINUTES=288
```

## Usage

Run once:
```
python job_alert.py --run-once
```

Run continuously:
```
python job_alert.py
```

## Advanced Features

### Using OpenAI for Job Analysis

If you provide an OpenAI API key, the system will:
- Extract key skills required for each job
- Identify years of experience needed
- Summarize job responsibilities
- Provide a suitability score

### Using Ollama for Local AI Processing

If you have Ollama installed, the system will use it as a fallback when no OpenAI key is provided.

## Troubleshooting

- **Email Not Sending**: Make sure you're using an app password for Gmail, not your regular password
- **No Jobs Found**: Try broadening your search terms or location
- **API Errors**: Check your JSearch API key and usage limits
- **Searching for Specific Locations**: Some specific cities may not be recognized by the API. Try using more general locations like state or country names.

## License

This project is open source and available under the MIT License.

## Acknowledgements

- Uses the JSearch API from RapidAPI for job data
- Optional integration with OpenAI API and Ollama 