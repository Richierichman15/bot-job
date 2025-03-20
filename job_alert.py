#!/usr/bin/env python3
import os
import json
import time
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv
from job_searcher import JobSearcher
from job_database import JobDatabase
from email_notifier import EmailNotifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('job_alerts.log')
    ]
)
logger = logging.getLogger(__name__)

class JobAlertSystem:
    def __init__(self):
        """Initialize the job alert system"""
        load_dotenv()
        
        # Initialize components
        self.searcher = JobSearcher()
        self.db = JobDatabase()
        self.email_notifier = EmailNotifier()
        
        # Load settings
        self.check_interval = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))
        
    def run_once(self):
        """Run the job alert system once and exit"""
        logger.info("Running job alert system once")
        
        try:
            # Search for jobs
            logger.info("Starting job search process...")
            
            # Use job searcher to find jobs
            logger.info("Searching for jobs using basic search...")
            job_searcher = JobSearcher()
            
            # If using mock data, we'll get processed jobs directly
            if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
                # Get mock jobs directly
                mock_jobs = job_searcher._get_mock_jobs()
                jobs = mock_jobs  # These are raw job objects without any AI processing
                
                # Create simple application packages with mock data
                application_packages = []
                for job in jobs:
                    # Create mock analysis
                    analysis = {
                        "skill_match_percentage": 85,
                        "key_requirements": [
                            "Python programming",
                            "JavaScript/React experience",
                            "Database knowledge (SQL, NoSQL)",
                            "Team collaboration skills",
                            "Problem-solving abilities"
                        ],
                        "explanation": "This job is a good match for your skills in web development and programming."
                    }
                    
                    # Create a mock application package
                    app_package = {
                        "job": job,
                        "analysis": analysis,
                        "status": "ready_to_apply",
                        "materials": {
                            "cover_letter": "Dear Hiring Manager,\n\nI am writing to express my interest in the position. My experience with Python and JavaScript makes me a good fit.\n\nSincerely,\nGitonga Nyaga"
                        }
                    }
                    application_packages.append(app_package)
                
                # Get existing job IDs from the database
                existing_jobs = self.db.get_all_jobs()
                existing_job_ids = set()
                
                # Extract job IDs from the database entries
                for job_id, job_entry in existing_jobs.items():
                    existing_job_ids.add(job_id)
                
                # Filter out jobs that are already in the database
                new_job_packages = []
                new_jobs = []
                
                for app_package in application_packages:
                    job = app_package["job"]
                    job_id = job.get("job_id")
                    
                    if job_id not in existing_job_ids:
                        new_job_packages.append(app_package)
                        new_jobs.append(job)
                
                # Store new jobs in the database
                for job in new_jobs:
                    self.db.add_job(job)
                
                # Send email notifications if there are any new jobs
                if new_job_packages:
                    logger.info(f"Sending notifications for {len(new_job_packages)} jobs")
                    self.email_notifier.send_job_notifications(new_job_packages)
                    logger.info("Email notifications sent successfully")
                else:
                    logger.info("No new job opportunities found")
            else:
                # Use the normal search process
                processed_jobs = job_searcher.search_jobs()
                
                if processed_jobs:
                    # These are already application packages processed by the AI
                    # Get existing job IDs from the database
                    existing_jobs = self.db.get_all_jobs()
                    existing_job_ids = set()
                    
                    # Extract job IDs from the database entries
                    for job_id, job_entry in existing_jobs.items():
                        existing_job_ids.add(job_id)
                    
                    # Filter out jobs that are already in the database
                    new_job_packages = []
                    new_jobs = []
                    
                    for app_package in processed_jobs:
                        job = app_package["job"]
                        job_id = job.get("job_id")
                        
                        if job_id not in existing_job_ids:
                            new_job_packages.append(app_package)
                            new_jobs.append(job)
                    
                    # Store new jobs in the database
                    for job in new_jobs:
                        self.db.add_job(job)
                    
                    # Send email notifications if there are any new jobs
                    if new_job_packages:
                        logger.info(f"Sending notifications for {len(new_job_packages)} jobs")
                        self.email_notifier.send_job_notifications(new_job_packages)
                        logger.info("Email notifications sent successfully")
                    else:
                        logger.info("No new job opportunities found")
                else:
                    logger.info("No job opportunities found")
        
        except Exception as e:
            logger.error(f"Error in job alert system: {str(e)}")
    
    def run_continuous(self):
        """Run the job alert system continuously"""
        logger.info(f"Starting continuous job alert system, checking every {self.check_interval} minutes")
        
        while True:
            try:
                self.run_once()
                
                # Sleep until next check
                logger.info(f"Sleeping for {self.check_interval} minutes until next check")
                time.sleep(self.check_interval * 60)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in continuous run: {str(e)}")
                # Sleep for a minute before retrying
                time.sleep(60)

def main():
    """Main entry point for the job alert system"""
    parser = argparse.ArgumentParser(description="Job Alert System")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    args = parser.parse_args()
    
    try:
        system = JobAlertSystem()
        
        if args.run_once:
            logger.info("Running job alert system once")
            success = system.run_once()
            exit(0 if success else 1)
        else:
            logger.info("Running job alert system continuously")
            system.run_continuous()
            
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main() 