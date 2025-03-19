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
        self.database = JobDatabase()
        self.notifier = EmailNotifier()
        
        # Load settings
        self.check_interval = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))
        
    def run_once(self):
        """Run one iteration of the job search and notification process"""
        try:
            logger.info("Starting job search process...")
            
            # Search for jobs and get AI-processed applications
            applications = self.searcher.search_jobs()
            logger.info(f"Found {len(applications)} potential jobs to apply for")
            
            # Process each application
            new_applications = []
            for application in applications:
                job_id = application['job_data'].get('job_id')
                
                # Check if we've seen this job before
                if not self.database.job_exists(job_id):
                    # Add to database
                    self.database.add_job(application)
                    new_applications.append(application)
                    logger.info(f"Added new job application for {application['job_data'].get('job_title')} at {application['job_data'].get('employer_name')}")
            
            # Send notifications for new jobs
            if new_applications:
                logger.info(f"Sending notifications for {len(new_applications)} new job opportunities")
                self.notifier.send_job_notifications(new_applications)
            else:
                logger.info("No new job opportunities found")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in job alert process: {str(e)}")
            return False
    
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