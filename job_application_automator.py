#!/usr/bin/env python3
import os
import json
import logging
import time
import random
import shutil
from datetime import datetime
from dotenv import load_dotenv
from bright_data_scraper import BrightDataScraper
import re
import uuid

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
    
    def __init__(self, resume_path=None, application_path=None, config_file=None, test_mode=None):
        """
        Initialize the JobApplicationAutomator with necessary settings
        
        Args:
            resume_path (str): Path to the resume file
            application_path (str): Path to store application files
            config_file (str): Path to configuration file
            test_mode (bool): Whether to run in test mode
        """
        # Load config file if provided
        self.config = {}
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                logger.error(f"Error loading config file: {str(e)}")
        
        # Get settings from environment variables or parameters
        default_resume_path = "/Users/gitonga-nyaga/github/job/resume/GN.pdf"
        self.resume_path = resume_path or os.getenv("RESUME_PATH", default_resume_path)
        self.application_path = application_path or os.getenv("APPLICATIONS_DIR", "applications")
        self.cover_letter_template = os.getenv("COVER_LETTER_TEMPLATE", "resume/cover_letter_template.txt")
        self.max_daily_applications = int(os.getenv("MAX_DAILY_APPLICATIONS", "5"))
        self.application_delay = float(os.getenv("APPLICATION_DELAY", "2.0"))
        self.test_mode = test_mode if test_mode is not None else os.getenv("TEST_MODE", "false").lower() == "true"
        
        # Initialize pending applications list
        self._pending_applications = []
        self._application_history = None
        
        # Verify resume exists
        if not os.path.exists(self.resume_path):
            # Try relative path
            relative_path = os.path.join(os.getcwd(), "resume/GN.pdf")
            if os.path.exists(relative_path):
                self.resume_path = relative_path
                logger.info(f"Using resume from relative path: {self.resume_path}")
            else:
                logger.warning(f"Resume not found at {self.resume_path} or {relative_path}")
        
        # Initialize Bright Data scraper with test mode
        self.bright_data = BrightDataScraper(test_mode=self.test_mode)
        
        # Create applications directory if it doesn't exist
        os.makedirs(self.application_path, exist_ok=True)
        
        # Create applications log directory
        self.log_dir = os.path.join(self.application_path, "logs")
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
        for app_dir in os.listdir(self.application_path):
            app_path = os.path.join(self.application_path, app_dir)
            
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
        # Temporarily disable daily limit for testing
        return False
        
        # Commented out for testing
        # today = datetime.now().strftime("%Y-%m-%d")
        # daily_stats = self.application_history["stats"]["by_date"].get(today, {"count": 0})
        # 
        # if daily_stats["count"] >= self.max_daily_applications:
        #     logger.warning(f"Daily application limit reached: {daily_stats['count']}/{self.max_daily_applications}")
        #     return True
        # 
        # return False
    
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
        possible_resume_names = [
            "GN.pdf", 
            "Resume (1).pdf", 
            os.path.basename(self.resume_path)
        ]
        
        # Also check for resume in the source directory (might be an absolute path)
        if os.path.exists(self.resume_path) and os.path.isfile(self.resume_path):
            source_resume = self.resume_path
            target_resume = os.path.join(app_path, os.path.basename(self.resume_path))
            
            # Copy the source resume to the application directory if it doesn't exist
            if not os.path.exists(target_resume):
                try:
                    shutil.copy(source_resume, target_resume)
                    logger.info(f"Copied resume from {source_resume} to {target_resume}")
                except Exception as e:
                    logger.error(f"Error copying resume: {str(e)}")
        
        # Check for resume files in the application directory
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

    def job_meets_requirements(self, job):
        """
        Check if a job meets the requirements for applying
        
        Args:
            job (dict): Job details object
            
        Returns:
            bool: True if job meets requirements, False otherwise
        """
        try:
            # Skip jobs that don't match our criteria
            job_title = job.get("job_title", "").lower()
            employer_name = job.get("employer_name", "").lower()
            job_description = job.get("job_description", "").lower()
            
            # Load exclusion lists
            excluded_companies = set(self.config.get("excluded_companies", []))
            excluded_titles = set(self.config.get("excluded_titles", []))
            excluded_terms = set(self.config.get("excluded_terms", []))
            
            # Check if job title matches allowed patterns
            title_matches = False
            for title_pattern in self.config.get("job_titles", []):
                if title_pattern.lower() in job_title:
                    title_matches = True
                    break
            
            if not title_matches:
                logger.info(f"Skipping job '{job_title}' - title doesn't match any allowed patterns")
                return False
            
            # Check if this job is from an excluded company
            for company in excluded_companies:
                if company.lower() in employer_name:
                    logger.info(f"Skipping job at '{employer_name}' - excluded company")
                    return False
            
            # Check if this job title contains excluded terms
            for term in excluded_titles:
                if term.lower() in job_title:
                    logger.info(f"Skipping job '{job_title}' - excluded title term")
                    return False
            
            # Check if job description contains excluded terms
            for term in excluded_terms:
                if term.lower() in job_description:
                    logger.info(f"Skipping job '{job_title}' - excluded term in description")
                    return False
            
            # Check if we've already applied to this job
            if self.has_applied_to_job(job):
                logger.info(f"Skipping job '{job_title}' at '{employer_name}' - already applied")
                return False
            
            # All checks passed
            return True
            
        except Exception as e:
            logger.error(f"Error checking job requirements: {str(e)}")
            return False
    
    def prepare_application_package(self, job):
        """
        Prepare application package for a job
        
        Args:
            job (dict): Job details
            
        Returns:
            dict: Application package with all necessary materials
        """
        try:
            # Extract job details
            job_id = job.get("job_id", uuid.uuid4().hex)
            job_title = job.get("job_title", "Unknown Position")
            employer_name = job.get("employer_name", "Unknown Company")
            job_location = job.get("job_location", "Unknown Location")
            job_description = job.get("job_description", "")
            job_apply_link = job.get("job_apply_link", "")
            job_source = job.get("job_source", "unknown")
            
            # Clean up company name for filesystem
            clean_company_name = self._clean_filename(employer_name.lower())
            clean_job_title = self._clean_filename(job_title.lower())
            
            # Create a unique folder for this application
            date_str = datetime.now().strftime("%Y%m%d")
            application_dir = os.path.join(
                self.application_path,
                f"{clean_company_name}_{date_str}_{clean_job_title}"
            )
            
            # Skip if we've already created this application package
            if os.path.exists(application_dir):
                logger.info(f"Application package already exists for {employer_name} - {job_title}")
                return None
            
            # Create the application directory
            os.makedirs(application_dir, exist_ok=True)
            
            # Analyze the job for required skills and keywords
            required_skills = job.get("job_required_skills", self._extract_skills(job_description))
            
            # Generate a tailored cover letter
            cover_letter_path = self._generate_cover_letter(
                application_dir, 
                employer_name, 
                job_title, 
                job_description,
                required_skills
            )
            
            # Create a tailored resume
            resume_path = self._tailor_resume(
                application_dir,
                employer_name,
                job_title,
                required_skills
            )
            
            # Save job details to JSON
            job_details_path = os.path.join(application_dir, "job_details.json")
            with open(job_details_path, "w") as f:
                json.dump(job, f, indent=4)
            
            # Create application record
            application = {
                "job_id": job_id,
                "job_title": job_title,
                "employer_name": employer_name,
                "job_location": job_location,
                "job_apply_link": job_apply_link,
                "job_source": job_source,
                "application_date": None,  # Will be set when actually applied
                "status": "pending",
                "resume_path": resume_path,
                "cover_letter_path": cover_letter_path,
                "application_dir": application_dir,
                "job_description": job_description,
                "required_skills": required_skills
            }
            
            # Add the application to pending applications
            self._pending_applications.append(application)
            
            # Save the updated pending applications
            self._save_pending_applications()
            
            return application
            
        except Exception as e:
            logger.error(f"Error preparing application package: {str(e)}")
            return None
            
    def _clean_filename(self, name):
        """
        Clean a string to be used as a filename
        
        Args:
            name (str): Original string
            
        Returns:
            str: Cleaned string safe for filenames
        """
        # Replace spaces and special characters
        cleaned = re.sub(r'[^\w\s-]', '', name)
        cleaned = re.sub(r'[\s]+', '_', cleaned)
        cleaned = re.sub(r'[-]+', '-', cleaned)
        return cleaned
        
    def _extract_skills(self, text):
        """
        Extract skills from text
        
        Args:
            text (str): Text to extract skills from
            
        Returns:
            list: List of skills
        """
        # Get common skills from config
        common_skills = self.config.get("common_skills", [])
        
        # Extract skills that appear in the text
        found_skills = []
        for skill in common_skills:
            if skill.lower() in text.lower():
                found_skills.append(skill)
                
        return found_skills
    
    def _generate_cover_letter(self, application_dir, company_name, job_title, job_description, skills):
        """
        Generate a cover letter for a job application
        
        Args:
            application_dir (str): Directory to save the cover letter
            company_name (str): Company name
            job_title (str): Job title
            job_description (str): Job description
            skills (list): Required skills
            
        Returns:
            str: Path to the cover letter file
        """
        try:
            # Load cover letter template
            template_path = os.path.join(os.path.dirname(__file__), "templates", "cover_letter_template.txt")
            
            if not os.path.exists(template_path):
                logger.warning(f"Cover letter template not found at {template_path}, using default template")
                template = """Dear Hiring Manager,

I am writing to express my interest in the {job_title} position at {company_name}. With my experience in {skills}, I believe I would be a valuable addition to your team.

{custom_paragraph}

Thank you for considering my application. I look forward to the opportunity to discuss how my skills and experience align with your needs.

Sincerely,
{name}
{email}
{phone}
"""
            else:
                with open(template_path, "r") as f:
                    template = f.read()
            
            # Create custom paragraph based on job description and skills
            skills_text = ", ".join(skills[:5])  # Limit to top 5 skills
            
            custom_paragraph = f"Based on the job description, I understand you're looking for someone skilled in {skills_text}. " \
                              f"Throughout my career, I've developed expertise in these areas through hands-on experience and continuous learning."
            
            # Fill in the template
            cover_letter = template.format(
                job_title=job_title,
                company_name=company_name,
                skills=skills_text,
                custom_paragraph=custom_paragraph,
                name=self.config.get("name", "Your Name"),
                email=self.config.get("email", "your.email@example.com"),
                phone=self.config.get("phone", "123-456-7890")
            )
            
            # Save the cover letter
            cover_letter_file = f"cover_letter_{self._clean_filename(company_name)}.txt"
            cover_letter_path = os.path.join(application_dir, cover_letter_file)
            
            with open(cover_letter_path, "w") as f:
                f.write(cover_letter)
                
            return cover_letter_path
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {str(e)}")
            return None
    
    def _tailor_resume(self, application_dir, company_name, job_title, skills):
        """
        Tailor resume for the job application
        
        Args:
            application_dir (str): Directory to save the resume
            company_name (str): Company name
            job_title (str): Job title
            skills (list): Required skills
            
        Returns:
            str: Path to the tailored resume
        """
        try:
            # For now, just copy the main resume
            resume_filename = os.path.basename(self.resume_path)
            tailored_resume_path = os.path.join(application_dir, resume_filename)
            
            # Copy the resume to the application directory
            shutil.copy2(self.resume_path, tailored_resume_path)
            
            return tailored_resume_path
            
        except Exception as e:
            logger.error(f"Error tailoring resume: {str(e)}")
            return self.resume_path  # Return original resume path as fallback
        
    def process_applications(self, limit=3):
        """
        Process pending applications
        
        Args:
            limit (int): Maximum number of applications to process
            
        Returns:
            int: Number of applications successfully submitted
        """
        if self.test_mode:
            logger.info(f"Test mode: Would process up to {limit} applications")
        else:
            logger.info(f"Processing up to {limit} pending applications")
        
        # Load pending applications if needed
        if not self._pending_applications:
            self._load_pending_applications()
            
        # Get pending applications
        pending = [app for app in self._pending_applications if app.get("status") == "pending"]
        logger.info(f"Found {len(pending)} pending applications")
        
        if not pending:
            return 0
            
        # Process up to the limit
        processed_count = 0
        successful_count = 0
        
        for application in pending[:limit]:
            try:
                logger.info(f"Attempting to submit application for: {application.get('job_title')} at {application.get('employer_name')}")
                
                # Create an application dict that matches the format expected by submit_application
                app_submission = {
                    "metadata": {
                        "job_title": application.get("job_title"),
                        "company": application.get("employer_name"),
                        "apply_link": application.get("job_apply_link")
                    },
                    "path": application.get("application_dir"),
                    "dir": os.path.basename(application.get("application_dir"))
                }
                
                # Submit the application
                result = self.submit_application(app_submission)
                
                processed_count += 1
                
                if result:
                    successful_count += 1
                    # Update application status
                    application["status"] = "submitted"
                    application["application_date"] = datetime.now().isoformat()
                    # Save updated pending applications
                    self._save_pending_applications()
                    logger.info(f"Successfully submitted application for {application.get('job_title')} at {application.get('employer_name')}")
                else:
                    logger.error(f"Failed to submit application for {application.get('job_title')} at {application.get('employer_name')}")
                    
            except Exception as e:
                logger.error(f"Error processing application: {str(e)}")
                
        logger.info(f"Processed {processed_count} applications, {successful_count} successfully submitted")
        return successful_count
    
    def get_recent_applications(self, count=5, status=None):
        """
        Get recent applications
        
        Args:
            count (int): Number of applications to retrieve
            status (str, optional): Filter by status
            
        Returns:
            list: Recent applications
        """
        # Load application history
        if not self._application_history:
            self._load_application_history()
            
        # Sort by application date (newest first)
        sorted_applications = sorted(
            self._application_history,
            key=lambda x: x.get("application_date", ""),
            reverse=True
        )
        
        # Filter by status if provided
        if status:
            filtered = [app for app in sorted_applications if app.get("status") == status]
        else:
            filtered = sorted_applications
            
        # Return the most recent ones
        return filtered[:count]

    def _load_pending_applications(self):
        """
        Load pending applications from file
        """
        pending_file = os.path.join(self.log_dir, "pending_applications.json")
        
        if os.path.exists(pending_file):
            try:
                with open(pending_file, 'r') as f:
                    self._pending_applications = json.load(f)
                logger.info(f"Loaded {len(self._pending_applications)} pending applications")
            except Exception as e:
                logger.error(f"Error loading pending applications: {str(e)}")
                self._pending_applications = []
        else:
            self._pending_applications = []
    
    def _save_pending_applications(self):
        """
        Save pending applications to file
        """
        pending_file = os.path.join(self.log_dir, "pending_applications.json")
        
        try:
            with open(pending_file, 'w') as f:
                json.dump(self._pending_applications, f, indent=2)
            logger.info(f"Saved {len(self._pending_applications)} pending applications")
        except Exception as e:
            logger.error(f"Error saving pending applications: {str(e)}")
    
    def has_applied_to_job(self, job):
        """
        Check if we've already applied to a job
        
        Args:
            job (dict): Job details
            
        Returns:
            bool: True if already applied, False otherwise
        """
        # Load application history if needed
        if self._application_history is None:
            self._load_application_history()
        
        job_id = job.get('job_id')
        job_title = job.get('job_title', '').lower()
        employer_name = job.get('employer_name', '').lower()
        
        # Check applications by ID if available
        if job_id:
            for app in self._application_history:
                if app.get('job_id') == job_id:
                    return True
        
        # Check applications by title and employer
        for app in self._application_history:
            app_title = (app.get('job_title') or '').lower()
            app_employer = (app.get('employer_name') or '').lower()
            
            if app_title and app_employer and app_title in job_title and app_employer in employer_name:
                return True
        
        return False
    
    def _load_application_history(self):
        """
        Load application history
        """
        if not os.path.exists(self.application_history_file):
            self._application_history = []
            return
            
        try:
            with open(self.application_history_file, 'r') as f:
                history = json.load(f)
                self._application_history = history.get('applications', [])
            logger.info(f"Loaded {len(self._application_history)} application history entries")
        except Exception as e:
            logger.error(f"Error loading application history: {str(e)}")
            self._application_history = []

# For testing
if __name__ == "__main__":
    automator = JobApplicationAutomator()
    automator.run(limit=3) 