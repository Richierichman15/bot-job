#!/usr/bin/env python3
import os
import logging
import time
import schedule
from dotenv import load_dotenv
import argparse
import sys

from job_searcher import JobSearcher
from job_database import JobDatabase
from email_notifier import send_job_notification
from ai_processor import AIProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("job_alert.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("job_alert")

# Load environment variables
load_dotenv()

def search_and_notify():
    """Main function to search for jobs and send notifications"""
    logger.info("Starting job search and notification process")
    
    try:
        # Initialize components
        job_searcher = JobSearcher()
        job_db = JobDatabase()
        ai = AIProcessor()
        
        # Get search parameters from environment
        job_titles = os.getenv("JOB_TITLES", os.getenv("JOB_TITLE", "software developer"))
        job_locations = os.getenv("JOB_LOCATIONS", os.getenv("JOB_LOCATION", "usa"))
        job_remote = os.getenv("JOB_REMOTE", "true").lower() == "true"
        
        # Search for jobs
        jobs = job_searcher.search_jobs(
            query=job_titles,
            location=job_locations,
            remote=job_remote,
            page=1,
            num_pages=2
        )
        
        if not jobs:
            logger.warning("No jobs found in search")
            return
        
        logger.info(f"Found {len(jobs)} jobs in search")
        
        # Add jobs to database and get new ones
        new_jobs = job_db.add_jobs(jobs)
        
        if not new_jobs:
            logger.info("No new jobs found")
            return
        
        logger.info(f"Found {len(new_jobs)} new jobs")
        
        # Process each job with AI if available
        processed_jobs = []
        for job in new_jobs:
            # Optionally get more details for each job
            job_id = job.get('job_id')
            if job_id:
                try:
                    detailed_job = job_searcher.get_job_details(job_id)
                    if detailed_job:
                        # Merge the detailed data into the job
                        job.update(detailed_job)
                except Exception as e:
                    logger.error(f"Error getting details for job {job_id}: {str(e)}")
            
            # Use AI to analyze the job if available
            processed_job = ai.analyze_job(job)
            processed_jobs.append(processed_job)
        
        # Send email notification for new jobs
        notification_sent = send_job_notification(processed_jobs)
        
        if notification_sent:
            # Mark jobs as notified
            job_ids = [job.get('job_id') for job in processed_jobs if job.get('job_id')]
            job_db.mark_jobs_as_notified(job_ids)
            
            # Log summary of jobs found
            summary = ai.summarize_jobs(processed_jobs)
            logger.info(f"Job summary: {summary}")
        
    except Exception as e:
        logger.error(f"Error in search and notify process: {str(e)}")

def run_schedule():
    """Run the scheduler to check for jobs at regular intervals"""
    interval_minutes = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))
    
    logger.info(f"Setting up schedule to run every {interval_minutes} minutes")
    
    schedule.every(interval_minutes).minutes.do(search_and_notify)
    
    # Run once at startup
    search_and_notify()
    
    logger.info("Starting scheduler. Press Ctrl+C to stop.")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")

def main():
    """Main entry point with command-line argument parsing"""
    parser = argparse.ArgumentParser(description="Job Search and Alert System")
    
    parser.add_argument("--run-once", action="store_true", help="Run search once and exit")
    parser.add_argument("--configure", action="store_true", help="Configure settings")
    
    args = parser.parse_args()
    
    if args.configure:
        configure()
    elif args.run_once:
        search_and_notify()
    else:
        run_schedule()

def configure():
    """Interactive configuration to set up the .env file"""
    print("=== Job Alert System Configuration ===")
    
    # Load existing .env if it exists
    existing_env = {}
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    existing_env[key] = value
    
    # Job search parameters
    job_titles = input(f"Job titles to search for (comma-separated) [{existing_env.get('JOB_TITLES', existing_env.get('JOB_TITLE', 'software developer'))}]: ")
    job_titles = job_titles or existing_env.get('JOB_TITLES', existing_env.get('JOB_TITLE', 'software developer'))
    
    job_locations = input(f"Locations to search in (comma-separated) [{existing_env.get('JOB_LOCATIONS', existing_env.get('JOB_LOCATION', 'usa'))}]: ")
    job_locations = job_locations or existing_env.get('JOB_LOCATIONS', existing_env.get('JOB_LOCATION', 'usa'))
    
    job_remote = input(f"Include remote jobs (true/false) [{existing_env.get('JOB_REMOTE', 'true')}]: ")
    job_remote = job_remote or existing_env.get('JOB_REMOTE', 'true')
    
    min_salary = input(f"Minimum salary (annual) [{existing_env.get('MIN_SALARY', '0')}]: ")
    min_salary = min_salary or existing_env.get('MIN_SALARY', '0')
    
    job_types = input(f"Employment types (comma-separated, e.g., FULLTIME,CONTRACT) [{existing_env.get('JOB_EMPLOYMENT_TYPES', 'FULLTIME')}]: ")
    job_types = job_types or existing_env.get('JOB_EMPLOYMENT_TYPES', 'FULLTIME')
    
    interval = input(f"Check interval in minutes [{existing_env.get('CHECK_INTERVAL_MINUTES', '60')}]: ")
    interval = interval or existing_env.get('CHECK_INTERVAL_MINUTES', '60')
    
    # Email configuration
    email_sender = input(f"Sender email (Gmail recommended) [{existing_env.get('EMAIL_SENDER', '')}]: ")
    email_sender = email_sender or existing_env.get('EMAIL_SENDER', '')
    
    email_password = input(f"Email password or app password (leave empty to keep existing): ")
    email_password = email_password or existing_env.get('EMAIL_PASSWORD', '')
    
    email_recipient = input(f"Recipient email [{existing_env.get('EMAIL_RECIPIENT', email_sender)}]: ")
    email_recipient = email_recipient or existing_env.get('EMAIL_RECIPIENT', email_sender)
    
    # API keys
    jsearch_key = input(f"JSearch API key (leave empty to keep existing) [{existing_env.get('JSEARCH_API_KEY', '****')}]: ")
    jsearch_key = jsearch_key or existing_env.get('JSEARCH_API_KEY', '')
    
    jsearch_host = input(f"JSearch API host [{existing_env.get('JSEARCH_API_HOST', 'jsearch.p.rapidapi.com')}]: ")
    jsearch_host = jsearch_host or existing_env.get('JSEARCH_API_HOST', 'jsearch.p.rapidapi.com')
    
    openai_key = input(f"OpenAI API key (optional, leave empty to skip) [{existing_env.get('OPENAI_API_KEY', '')}]: ")
    openai_key = openai_key or existing_env.get('OPENAI_API_KEY', '')
    
    # Write configuration to .env file
    with open(".env", "w") as f:
        f.write("# JSearch API credentials\n")
        f.write(f"JSEARCH_API_KEY={jsearch_key}\n")
        f.write(f"JSEARCH_API_HOST={jsearch_host}\n")
        f.write("\n# Email configuration\n")
        f.write(f"EMAIL_SENDER={email_sender}\n")
        f.write(f"EMAIL_PASSWORD={email_password}\n")
        f.write(f"EMAIL_RECIPIENT={email_recipient}\n")
        f.write("\n# Job search parameters\n")
        f.write(f"JOB_TITLES={job_titles}\n")
        f.write(f"JOB_LOCATIONS={job_locations}\n")
        f.write(f"JOB_REMOTE={job_remote}\n")
        f.write(f"MIN_SALARY={min_salary}\n")
        f.write(f"JOB_EMPLOYMENT_TYPES={job_types}\n")
        f.write(f"CHECK_INTERVAL_MINUTES={interval}\n")
        if openai_key:
            f.write("\n# OpenAI API (optional, for job description summarization)\n")
            f.write(f"OPENAI_API_KEY={openai_key}\n")
    
    print("\nConfiguration saved to .env file.")
    print("Run 'python job_alert.py' to start job alerts or 'python job_alert.py --run-once' to test.")

if __name__ == "__main__":
    main() 