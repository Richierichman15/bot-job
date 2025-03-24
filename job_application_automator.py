#!/usr/bin/env python3
import os
import json
import logging
import time
import random
from datetime import datetime
from dotenv import load_dotenv
from bright_data_scraper import BrightDataScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('job_applications.log')
    ]
)
logger = logging.getLogger("job_application_automator")

# Load environment variables
load_dotenv()

class JobApplicationAutomator:
    """
    A class for automating job applications using Bright Data Web Unlocker API
    """
    
    def __init__(self):
        """Initialize the JobApplicationAutomator with necessary settings"""
        # Get settings from environment variables
        self.resume_path = os.getenv("RESUME_PATH", "resume/GN.pdf")
        self.applications_dir = os.getenv("APPLICATIONS_DIR", "applications")
        self.cover_letter_template = os.getenv("COVER_LETTER_TEMPLATE", "resume/cover_letter_template.txt")
        self.max_daily_applications = int(os.getenv("MAX_DAILY_APPLICATIONS", "5"))
        self.application_delay = float(os.getenv("APPLICATION_DELAY", "2.0"))
        
        # Initialize Bright Data scraper
        self.bright_data = BrightDataScraper()
        
        # Create applications directory if it doesn't exist
        os.makedirs(self.applications_dir, exist_ok=True)
        
        # Create applications log directory
        self.log_dir = os.path.join(self.applications_dir, "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Load application history
        self.application_history_file = os.path.join(self.log_dir, "application_history.json")
        self.application_history = self.load_application_history()
        
        logger.info(f"JobApplicationAutomator initialized")
    
    def load_application_history(self):
        """
        Load application history from file
        
        Returns:
            dict: Application history
        """
        # Default history
        history = {
            "applications": [],
            "stats": {
                "total_submitted": 0,
                "successful": 0,
                "failed": 0,
                "by_date": {}
            }
        }
        
        # Try to load from file
        if os.path.exists(self.application_history_file):
            try:
                with open(self.application_history_file, 'r') as f:
                    history = json.load(f)
                logger.info(f"Loaded application history: {history['stats']['total_submitted']} applications")
            except Exception as e:
                logger.error(f"Error loading application history: {str(e)}")
        
        return history
    
    def save_application_history(self):
        """Save application history to file"""
        try:
            with open(self.application_history_file, 'w') as f:
                json.dump(self.application_history, f, indent=2)
            logger.info("Saved application history")
        except Exception as e:
            logger.error(f"Error saving application history: {str(e)}")
    
    def get_pending_applications(self):
        """
        Get list of pending applications
        
        Returns:
            list: List of application directories that haven't been submitted
        """
        pending = []
        
        # Check all subdirectories in applications directory
        for app_dir in os.listdir(self.applications_dir):
            app_path = os.path.join(self.applications_dir, app_dir)
            
            # Skip non-directories and the logs directory
            if not os.path.isdir(app_path) or app_dir == "logs":
                continue
            
            # Check if metadata.json exists
            metadata_path = os.path.join(app_path, "metadata.json")
            if not os.path.exists(metadata_path):
                continue
            
            try:
                # Load metadata
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                # Check if already submitted
                if not metadata.get('submitted', False):
                    pending.append({
                        "dir": app_dir,
                        "path": app_path,
                        "metadata": metadata
                    })
            except Exception as e:
                logger.error(f"Error reading metadata for {app_dir}: {str(e)}")
        
        logger.info(f"Found {len(pending)} pending applications")
        return pending
    
    def check_daily_limit(self):
        """
        Check if daily application limit has been reached
        
        Returns:
            bool: True if limit reached, False otherwise
        """
        today = datetime.now().strftime("%Y-%m-%d")
        daily_stats = self.application_history["stats"]["by_date"].get(today, {"count": 0})
        
        if daily_stats["count"] >= self.max_daily_applications:
            logger.warning(f"Daily application limit reached: {daily_stats['count']}/{self.max_daily_applications}")
            return True
        
        return False
    
    def submit_application(self, application):
        """
        Submit a job application
        
        Args:
            application (dict): Application data including directory and metadata
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check daily limit
        if self.check_daily_limit():
            return False
        
        app_dir = application["dir"]
        metadata = application["metadata"]
        app_path = application["path"]
        
        logger.info(f"Attempting to submit application for: {metadata.get('job_title')} at {metadata.get('company')}")
        
        # Get apply link
        apply_link = metadata.get('apply_link')
        if not apply_link:
            logger.error(f"No apply link found for {app_dir}")
            return False
        
        # Get resume path - try multiple possible filenames
        resume_path = None
        possible_resume_names = ["GN.pdf", "Resume (1).pdf", os.path.basename(self.resume_path)]
        
        for name in possible_resume_names:
            test_path = os.path.join(app_path, name)
            if os.path.exists(test_path):
                resume_path = test_path
                break
                
        if not resume_path:
            logger.error(f"Resume not found in {app_path}. Tried: {', '.join(possible_resume_names)}")
            return False
        
        # Get cover letter path
        cover_letter_path = None
        for file in os.listdir(app_path):
            if file.startswith("cover_letter_") and file.endswith(".txt"):
                cover_letter_path = os.path.join(app_path, file)
                break
        
        if not cover_letter_path:
            logger.warning(f"Cover letter not found for {app_dir}")
        
        # Submit application
        # In a real implementation, this would use the Bright Data API to automate form filling
        # For now, this is a simulation
        success = self._simulate_application_submission(apply_link, resume_path, cover_letter_path)
        
        if success:
            # Update metadata
            metadata['submitted'] = True
            metadata['submission_date'] = datetime.now().isoformat()
            metadata['submission_status'] = 'success'
            
            # Save updated metadata
            try:
                with open(os.path.join(app_path, "metadata.json"), 'w') as f:
                    json.dump(metadata, f, indent=2)
            except Exception as e:
                logger.error(f"Error updating metadata for {app_dir}: {str(e)}")
            
            # Update application history
            self._update_application_history(metadata, True)
            
            logger.info(f"Successfully submitted application for {metadata.get('job_title')} at {metadata.get('company')}")
        else:
            # Update metadata
            metadata['submission_attempts'] = metadata.get('submission_attempts', 0) + 1
            metadata['last_attempt'] = datetime.now().isoformat()
            metadata['submission_status'] = 'failed'
            
            # Save updated metadata
            try:
                with open(os.path.join(app_path, "metadata.json"), 'w') as f:
                    json.dump(metadata, f, indent=2)
            except Exception as e:
                logger.error(f"Error updating metadata for {app_dir}: {str(e)}")
            
            # Update application history
            self._update_application_history(metadata, False)
            
            logger.error(f"Failed to submit application for {metadata.get('job_title')} at {metadata.get('company')}")
        
        return success
    
    def _update_application_history(self, metadata, success):
        """
        Update application history
        
        Args:
            metadata (dict): Application metadata
            success (bool): Whether submission was successful
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Initialize today's stats if needed
        if today not in self.application_history["stats"]["by_date"]:
            self.application_history["stats"]["by_date"][today] = {
                "count": 0,
                "successful": 0,
                "failed": 0
            }
        
        # Update stats
        self.application_history["stats"]["total_submitted"] += 1
        self.application_history["stats"]["by_date"][today]["count"] += 1
        
        if success:
            self.application_history["stats"]["successful"] += 1
            self.application_history["stats"]["by_date"][today]["successful"] += 1
        else:
            self.application_history["stats"]["failed"] += 1
            self.application_history["stats"]["by_date"][today]["failed"] += 1
        
        # Add to applications list
        application_record = {
            "job_title": metadata.get("job_title"),
            "company": metadata.get("company"),
            "apply_link": metadata.get("apply_link"),
            "date": datetime.now().isoformat(),
            "success": success
        }
        
        self.application_history["applications"].append(application_record)
        
        # Save updated history
        self.save_application_history()
    
    def _simulate_application_submission(self, apply_link, resume_path, cover_letter_path=None):
        """
        Simulate submitting a job application (for testing)
        
        Args:
            apply_link (str): Link to the job application page
            resume_path (str): Path to the resume file
            cover_letter_path (str): Path to the cover letter file
            
        Returns:
            bool: True for successful submission (80% chance), False otherwise
        """
        # In a real implementation, this would use the Bright Data API to interact with forms
        # For testing purposes, we simulate a submission with an 80% success rate
        
        # Log the start of application
        logger.info(f"Simulating application for {apply_link}")
        
        # Add a delay to simulate form filling
        time.sleep(random.uniform(2.0, 5.0))
        
        # Log details about what we would submit
        logger.info(f"Would upload resume from: {resume_path}")
        if cover_letter_path:
            logger.info(f"Would upload cover letter from: {cover_letter_path}")
        
        # Simulate form filling
        logger.info("Simulating form filling...")
        time.sleep(random.uniform(1.0, 3.0))
        
        # Simulate form submission
        logger.info("Simulating form submission...")
        time.sleep(random.uniform(1.0, 2.0))
        
        # Determine success with 80% probability
        success = random.random() < 0.8
        
        if success:
            logger.info("Simulation successful!")
        else:
            logger.error("Simulation failed!")
        
        return success
    
    def run(self, limit=None):
        """
        Process pending applications
        
        Args:
            limit (int): Maximum number of applications to process
            
        Returns:
            int: Number of successfully submitted applications
        """
        # Get pending applications
        pending = self.get_pending_applications()
        
        if not pending:
            logger.info("No pending applications to process")
            return 0
        
        # Check daily limit
        if self.check_daily_limit():
            logger.warning("Daily application limit reached. Try again tomorrow.")
            return 0
        
        # Apply limit if specified
        if limit:
            pending = pending[:limit]
        
        # Track successful submissions
        successful = 0
        
        # Process applications
        for application in pending:
            try:
                # Submit application
                if self.submit_application(application):
                    successful += 1
                
                # Add delay between applications
                time.sleep(self.application_delay)
                
                # Check if daily limit reached
                if self.check_daily_limit():
                    logger.info("Daily application limit reached during processing")
                    break
                
            except Exception as e:
                logger.error(f"Error processing application {application['dir']}: {str(e)}")
        
        logger.info(f"Processed {len(pending)} applications, {successful} successfully submitted")
        return successful

# For testing
if __name__ == "__main__":
    automator = JobApplicationAutomator()
    automator.run(limit=3) 