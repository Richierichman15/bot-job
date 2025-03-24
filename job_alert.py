#!/usr/bin/env python3
import os
import json
import time
import logging
import argparse
import signal
from datetime import datetime
from dotenv import load_dotenv
from job_searcher import JobSearcher
from job_database import JobDatabase
from email_notifier import EmailNotifier
from ai_processor import AIJobProcessor
from email_sender import send_job_notification
import re
from pathlib import Path
from job_application_automator import JobApplicationAutomator
import sys

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
        
        # Resume and application settings
        self.resume_path = os.getenv("RESUME_PATH", "resume/GN.pdf")
        self.auto_submit = os.getenv("AUTO_SUBMIT_APPLICATIONS", "false").lower() == "true"
        self.cover_letter_template = os.getenv("COVER_LETTER_TEMPLATE", "resume/cover_letter_template.txt")
        
        # Verify resume exists
        if self.auto_submit and not os.path.exists(self.resume_path):
            logger.warning(f"Resume not found at {self.resume_path}. Auto-submit will be disabled.")
            self.auto_submit = False
        
        # Verify cover letter template exists
        if self.auto_submit and not os.path.exists(self.cover_letter_template):
            logger.warning(f"Cover letter template not found at {self.cover_letter_template}. Using default template.")
            self._create_default_cover_letter_template()
        
        # Create applications directory
        self.applications_dir = "applications"
        os.makedirs(self.applications_dir, exist_ok=True)
        
        # Initialize job application automator if auto-submit is enabled
        self.application_automator = None
        if self.auto_submit:
            self.application_automator = JobApplicationAutomator()
            logger.info("Initialized job application automator")
        
    def _create_default_cover_letter_template(self):
        """Create a default cover letter template if none exists"""
        default_template = """Dear Hiring Manager,

I am writing to express my interest in the {{JOB_TITLE}} position at {{COMPANY_NAME}}. 
With my skills in web development, I believe I would be a valuable addition to your team.

My technical skills include Python, JavaScript, React, and database technologies.

Thank you for considering my application.

Sincerely,
{{CANDIDATE_NAME}}
{{CANDIDATE_EMAIL}}
{{CANDIDATE_PHONE}}
"""
        os.makedirs(os.path.dirname(self.cover_letter_template), exist_ok=True)
        with open(self.cover_letter_template, 'w') as f:
            f.write(default_template)
        logger.info(f"Created default cover letter template at {self.cover_letter_template}")
    
    def generate_cover_letter(self, job, analysis):
        """Generate a cover letter for a specific job application"""
        try:
            # Read the template
            with open(self.cover_letter_template, 'r') as f:
                template = f.read()
            
            # Get company name, job title
            company_name = job.get('employer_name', 'the Company')
            job_title = job.get('job_title', 'the Position')
            
            # Get matched skills
            skills_matched = ", ".join(job.get('job_required_skills', [])[:3])
            if not skills_matched:
                skills_matched = "relevant technologies"
            
            # Generate custom paragraph based on AI analysis
            custom_paragraph = "Based on my experience with these technologies, I am confident I can contribute effectively to this role."
            if analysis and 'explanation' in analysis:
                custom_paragraph = analysis['explanation']
            
            # Generate company reason
            company_reason = "of its innovative work and reputation"
            
            # Replace placeholders
            cover_letter = template.replace('{{COMPANY_NAME}}', company_name)
            cover_letter = cover_letter.replace('{{JOB_TITLE}}', job_title)
            cover_letter = cover_letter.replace('{{SKILLS_MATCHED}}', skills_matched)
            cover_letter = cover_letter.replace('{{CUSTOM_PARAGRAPH}}', custom_paragraph)
            cover_letter = cover_letter.replace('{{COMPANY_REASON}}', company_reason)
            
            # Replace candidate info
            cover_letter = cover_letter.replace('{{CANDIDATE_NAME}}', os.getenv("CANDIDATE_NAME", ""))
            cover_letter = cover_letter.replace('{{CANDIDATE_EMAIL}}', os.getenv("CANDIDATE_EMAIL", ""))
            cover_letter = cover_letter.replace('{{CANDIDATE_PHONE}}', os.getenv("CANDIDATE_PHONE", ""))
            cover_letter = cover_letter.replace('{{CANDIDATE_LINKEDIN}}', os.getenv("CANDIDATE_LINKEDIN", ""))
            
            return cover_letter
        
        except Exception as e:
            logger.error(f"Error generating cover letter: {str(e)}")
            return None
    
    def prepare_job_application(self, job, analysis):
        """Prepare a job application package with resume and cover letter"""
        if not os.path.exists(self.resume_path):
            logger.error(f"Resume not found at {self.resume_path}")
            return None
        
        try:
            # Create unique application ID
            job_id = job.get('job_id', 'unknown')
            company = job.get('employer_name', 'unknown').lower().replace(' ', '_')
            date_str = datetime.now().strftime('%Y%m%d')
            application_id = f"{company}_{date_str}_{job_id}"
            
            # Create application directory
            application_dir = os.path.join(self.applications_dir, application_id)
            os.makedirs(application_dir, exist_ok=True)
            
            # Generate cover letter
            cover_letter = self.generate_cover_letter(job, analysis)
            if cover_letter:
                cover_letter_path = os.path.join(application_dir, f"cover_letter_{company}.txt")
                with open(cover_letter_path, 'w') as f:
                    f.write(cover_letter)
            
            # Copy resume to application directory
            import shutil
            resume_filename = os.path.basename(self.resume_path)
            destination_resume = os.path.join(application_dir, resume_filename)
            shutil.copy(self.resume_path, destination_resume)
            
            # Save job details
            job_details_path = os.path.join(application_dir, "job_details.json")
            with open(job_details_path, 'w') as f:
                json.dump(job, f, indent=2)
            
            # Save application metadata
            metadata = {
                "application_id": application_id,
                "job_title": job.get('job_title', ''),
                "company": job.get('employer_name', ''),
                "apply_link": job.get('job_apply_link', ''),
                "date_prepared": datetime.now().isoformat(),
                "submitted": False,
                "submission_date": None
            }
            
            metadata_path = os.path.join(application_dir, "metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Prepared application package for {job.get('employer_name')} - {job.get('job_title')}")
            return {
                "application_id": application_id,
                "resume_path": destination_resume,
                "cover_letter_path": cover_letter_path if cover_letter else None,
                "job_details_path": job_details_path,
                "metadata_path": metadata_path,
                "apply_link": job.get('job_apply_link', '')
            }
        
        except Exception as e:
            logger.error(f"Error preparing job application: {str(e)}")
            return None
    
    def run_once(self):
        """Run the job alert system once"""
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
                
                # Prepare application packages with mock data
                if self.auto_submit:
                    for i, job in enumerate(jobs):
                        application_package = self.prepare_job_application(job, application_packages[i].get('analysis'))
                        if application_package:
                            application_packages[i]['application'] = application_package
                    
                    # Run job application automator if available
                    if self.application_automator:
                        logger.info("Processing pending job applications...")
                        applications_submitted = self.application_automator.run(limit=3)
                        logger.info(f"Submitted {applications_submitted} job applications")
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
                    
                    # Prepare job applications if auto-submit is enabled
                    if self.auto_submit:
                        for i, package in enumerate(new_job_packages):
                            job = package.get('job', {})
                            analysis = package.get('analysis', {})
                            
                            application = self.prepare_job_application(job, analysis)
                            if application:
                                new_job_packages[i]['application'] = application
                        
                        # Run job application automator if available
                        if self.application_automator:
                            logger.info("Processing pending job applications...")
                            applications_submitted = self.application_automator.run(limit=3)
                            logger.info(f"Submitted {applications_submitted} job applications")
                    
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
            return False
        
        return True
    
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
    """Main function"""
    parser = argparse.ArgumentParser(description="Job Alert System")
    parser.add_argument("--run-once", action="store_true", help="Run the system once and exit")
    parser.add_argument("--apply-only", action="store_true", help="Only process pending applications, don't search for new jobs")
    parser.add_argument("--limit", type=int, default=3, help="Maximum number of applications to process")
    args = parser.parse_args()
    
    # Initialize signal handler
    def signal_handler(sig, frame):
        logger.info("Received interrupt signal, shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize system
    system = JobAlertSystem()
    
    if args.apply_only:
        if system.auto_submit and system.application_automator:
            # Only process pending applications
            logger.info(f"Processing pending job applications (limit: {args.limit})...")
            applications_submitted = system.application_automator.run(limit=args.limit)
            logger.info(f"Submitted {applications_submitted} job applications")
        else:
            if not system.auto_submit:
                logger.error("Auto-submit is disabled. Enable it by setting AUTO_SUBMIT_APPLICATIONS=true in .env")
            else:
                logger.error("Application automator initialization failed.")
    else:
        # Run the full system
        if args.run_once:
            logger.info("Running job alert system once")
            system.run_once()
        else:
            logger.info("Running job alert system continuously")
            system.run_continuous()
    
if __name__ == "__main__":
    main() 