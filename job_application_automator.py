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
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
import traceback

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
        Submit a job application using Selenium
        
        Args:
            application (dict): Application details
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get application details
            job_title = application.get('metadata', {}).get('job_title', 'Unknown Position')
            company = application.get('metadata', {}).get('company', 'Unknown Company')
            apply_link = application.get('metadata', {}).get('apply_link')
            application_dir = application.get('path')
            
            if not apply_link:
                logger.error(f"No application link provided for {job_title} at {company}")
                return False
                
            logger.info(f"Preparing to submit application for {job_title} at {company}")
            
            # Check if we're in test mode
            if self.test_mode:
                logger.info(f"Test mode: Simulating application submission for {job_title} at {company}")
                # Randomize success/failure for testing
                import random
                success = random.choice([True, True, False])  # 2/3 chance of success
                time.sleep(2)  # Simulate processing time
                
                if success:
                    logger.info(f"Test mode: Successfully submitted application to {company}")
                    return True
                else:
                    logger.error(f"Test mode: Failed to submit application to {company}")
                    return False
            
            # Get paths to resume and cover letter
            resume_path = os.path.join(application_dir, "resume.pdf")
            cover_letter_path = os.path.join(application_dir, "cover_letter.pdf")
            
            # Check that files exist
            if not os.path.exists(resume_path):
                logger.error(f"Resume not found at {resume_path}")
                return False
                
            if not os.path.exists(cover_letter_path):
                logger.warning(f"Cover letter not found at {cover_letter_path}, proceeding without it")
            
            # Determine which job site we're applying to
            site_type = self._detect_job_site(apply_link)
            
            # Configure Chrome options
            chrome_options = Options()
            if not os.getenv("DEBUG_BROWSER", "false").lower() == "true":
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Initialize the browser
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(60)
            
            try:
                # Navigate to the application page
                logger.info(f"Navigating to application page: {apply_link}")
                driver.get(apply_link)
                
                # Wait for page to load
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Handle site-specific application process
                if site_type == "linkedin":
                    success = self._apply_linkedin(driver, resume_path, cover_letter_path)
                elif site_type == "indeed":
                    success = self._apply_indeed(driver, resume_path, cover_letter_path)
                elif site_type == "glassdoor":
                    success = self._apply_glassdoor(driver, resume_path, cover_letter_path)
                else:
                    success = self._apply_generic(driver, resume_path, cover_letter_path)
                
                # Take screenshot for record
                screenshot_path = os.path.join(application_dir, "application_screenshot.png")
                driver.save_screenshot(screenshot_path)
                
                if success:
                    logger.info(f"Successfully submitted application to {company} for {job_title}")
                    # Record application in history
                    self._record_application(application, "submitted")
                    return True
                else:
                    logger.error(f"Failed to submit application to {company} for {job_title}")
                    # Record application in history
                    self._record_application(application, "failed")
                    return False
                    
            except Exception as e:
                logger.error(f"Error during application submission: {str(e)}")
                logger.error(traceback.format_exc())
                # Take error screenshot
                error_screenshot_path = os.path.join(application_dir, "error_screenshot.png")
                driver.save_screenshot(error_screenshot_path)
                # Record application in history
                self._record_application(application, "error", error=str(e))
                return False
                
            finally:
                # Close the browser
                driver.quit()
                
        except Exception as e:
            logger.error(f"Error preparing application: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _detect_job_site(self, url):
        """
        Detect which job site the URL belongs to
        
        Args:
            url (str): Application URL
            
        Returns:
            str: Site type (linkedin, indeed, glassdoor, or generic)
        """
        url = url.lower()
        if "linkedin.com" in url:
            return "linkedin"
        elif "indeed.com" in url:
            return "indeed"
        elif "glassdoor.com" in url:
            return "glassdoor"
        else:
            return "generic"
    
    def _apply_linkedin(self, driver, resume_path, cover_letter_path):
        """
        Apply to a job on LinkedIn
        
        Args:
            driver (WebDriver): Selenium WebDriver
            resume_path (str): Path to resume file
            cover_letter_path (str): Path to cover letter file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Wait for the apply button
            try:
                apply_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".jobs-apply-button"))
                )
                apply_button.click()
            except TimeoutException:
                logger.error("LinkedIn apply button not found")
                return False
            
            # Wait for the application form
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-easy-apply-content"))
                )
            except TimeoutException:
                logger.error("LinkedIn application form not loaded")
                return False
            
            # Upload resume if resume upload field is present
            try:
                resume_upload = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file'][name='resume']"))
                )
                resume_upload.send_keys(resume_path)
                logger.info("Resume uploaded successfully")
            except (TimeoutException, NoSuchElementException):
                logger.warning("Resume upload field not found, might be pre-filled")
            
            # Upload cover letter if the field is present
            try:
                cover_letter_upload = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file'][name='cover-letter']"))
                )
                cover_letter_upload.send_keys(cover_letter_path)
                logger.info("Cover letter uploaded successfully")
            except (TimeoutException, NoSuchElementException):
                logger.warning("Cover letter upload field not found, might not be required")
            
            # Handle multiple steps in the application process
            while True:
                # Look for next or submit button
                next_button = None
                try:
                    # First try to find Next button
                    next_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Continue to next step']"))
                    )
                except TimeoutException:
                    try:
                        # Then try to find Submit button
                        next_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Submit application']"))
                        )
                        # If we found Submit, this is the last step
                        next_button.click()
                        logger.info("Application submitted successfully")
                        return True
                    except TimeoutException:
                        # If no Next or Submit button, we might have reached the end or an error
                        logger.error("No Next or Submit button found")
                        return False
                
                # Click Next button and wait for next page
                next_button.click()
                time.sleep(2)  # Wait for the next step to load
                
                # Fill form fields if present (customize based on your resume details)
                self._fill_linkedin_form_fields(driver)
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying on LinkedIn: {str(e)}")
            return False
    
    def _fill_linkedin_form_fields(self, driver):
        """
        Fill common LinkedIn form fields
        
        Args:
            driver (WebDriver): Selenium WebDriver
        """
        # Example of filling common fields - customize based on your information
        fields_mapping = {
            "input[name='phoneNumber']": os.getenv("PHONE_NUMBER", ""),
            "input[name='email']": os.getenv("EMAIL", ""),
            "input[id='follow-company-checkbox']": True,  # Checkbox to follow company
        }
        
        for selector, value in fields_mapping.items():
            try:
                field = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                
                if isinstance(value, bool) and value is True:
                    # Handle checkboxes
                    if not field.is_selected():
                        field.click()
                else:
                    # Handle text inputs
                    field.clear()
                    field.send_keys(value)
                    
            except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                # Field not present on this page, continue
                pass
    
    def _apply_indeed(self, driver, resume_path, cover_letter_path):
        """
        Apply to a job on Indeed
        
        Args:
            driver (WebDriver): Selenium WebDriver
            resume_path (str): Path to resume file
            cover_letter_path (str): Path to cover letter file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Wait for the apply button
            try:
                apply_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".jobsearch-IndeedApplyButton"))
                )
                apply_button.click()
            except TimeoutException:
                logger.error("Indeed apply button not found")
                return False
            
            # Wait for the application iframe to load
            try:
                iframe = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "indeedapply-iframe"))
                )
                driver.switch_to.frame(iframe)
            except TimeoutException:
                logger.error("Indeed application iframe not found")
                return False
            
            # Upload resume if prompted
            try:
                resume_upload = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file'][name='resume']"))
                )
                resume_upload.send_keys(resume_path)
                logger.info("Resume uploaded to Indeed")
            except (TimeoutException, NoSuchElementException):
                logger.warning("Indeed resume upload not found, might be pre-filled")
            
            # Continue button after resume upload
            try:
                continue_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".ia-continueButton"))
                )
                continue_button.click()
            except TimeoutException:
                logger.warning("Indeed continue button not found after resume upload")
            
            # Handle multiple steps in the Indeed application
            step_count = 0
            max_steps = 10  # Prevent infinite loops
            
            while step_count < max_steps:
                step_count += 1
                
                # Fill out common fields
                self._fill_indeed_form_fields(driver)
                
                # Look for continue or submit button
                next_button = None
                try:
                    # First try to find continue button
                    next_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, ".ia-continueButton"))
                    )
                except TimeoutException:
                    try:
                        # Then try to find submit button
                        next_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, ".ia-SubmitButton"))
                        )
                        # If we found Submit, this is the last step
                        next_button.click()
                        logger.info("Indeed application submitted successfully")
                        return True
                    except TimeoutException:
                        # If no continue or submit button, we might have reached the end or an error
                        logger.error("No continue or submit button found on Indeed")
                        return False
                
                # Click continue button and wait for next page
                next_button.click()
                time.sleep(2)  # Wait for the next step to load
            
            logger.warning(f"Reached maximum steps ({max_steps}) for Indeed application")
            return False
            
        except Exception as e:
            logger.error(f"Error applying on Indeed: {str(e)}")
            return False
    
    def _fill_indeed_form_fields(self, driver):
        """
        Fill common Indeed form fields
        
        Args:
            driver (WebDriver): Selenium WebDriver
        """
        # Handle common Indeed form fields - customize based on your information
        fields_mapping = {
            "input[name='phone']": os.getenv("PHONE_NUMBER", ""),
            "input[name='email']": os.getenv("EMAIL", ""),
            # Add more field mappings as needed
        }
        
        for selector, value in fields_mapping.items():
            try:
                field = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                field.clear()
                field.send_keys(value)
            except (TimeoutException, NoSuchElementException):
                # Field not present on this page
                pass
    
    def _apply_glassdoor(self, driver, resume_path, cover_letter_path):
        """
        Apply to a job on Glassdoor
        
        Args:
            driver (WebDriver): Selenium WebDriver
            resume_path (str): Path to resume file
            cover_letter_path (str): Path to cover letter file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Wait for the apply button
            try:
                apply_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".applyButton"))
                )
                apply_button.click()
            except TimeoutException:
                logger.error("Glassdoor apply button not found")
                return False
            
            # Check if we're redirected to another site
            time.sleep(5)  # Wait for potential redirect
            
            # If redirected to the company's site, use generic application
            current_url = driver.current_url
            if "glassdoor.com" not in current_url:
                logger.info("Redirected to external site for application")
                return self._apply_generic(driver, resume_path, cover_letter_path)
            
            # Handle Glassdoor's own application system
            # Upload resume
            try:
                resume_upload = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file'][name='resume']"))
                )
                resume_upload.send_keys(resume_path)
                logger.info("Resume uploaded to Glassdoor")
            except (TimeoutException, NoSuchElementException):
                logger.warning("Glassdoor resume upload not found")
            
            # Upload cover letter if field exists
            try:
                cover_letter_upload = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file'][name='coverLetter']"))
                )
                cover_letter_upload.send_keys(cover_letter_path)
                logger.info("Cover letter uploaded to Glassdoor")
            except (TimeoutException, NoSuchElementException):
                logger.warning("Glassdoor cover letter upload not found")
            
            # Fill out additional fields
            self._fill_glassdoor_form_fields(driver)
            
            # Submit application
            try:
                submit_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                )
                submit_button.click()
                logger.info("Glassdoor application submitted")
                return True
            except TimeoutException:
                logger.error("Glassdoor submit button not found")
                return False
                
        except Exception as e:
            logger.error(f"Error applying on Glassdoor: {str(e)}")
            return False
    
    def _fill_glassdoor_form_fields(self, driver):
        """
        Fill common Glassdoor form fields
        
        Args:
            driver (WebDriver): Selenium WebDriver
        """
        # Handle common Glassdoor form fields
        fields_mapping = {
            "input[name='firstName']": os.getenv("FIRST_NAME", ""),
            "input[name='lastName']": os.getenv("LAST_NAME", ""),
            "input[name='email']": os.getenv("EMAIL", ""),
            "input[name='phoneNumber']": os.getenv("PHONE_NUMBER", ""),
            # Add more field mappings as needed
        }
        
        for selector, value in fields_mapping.items():
            try:
                field = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                field.clear()
                field.send_keys(value)
            except (TimeoutException, NoSuchElementException):
                # Field not present on this page
                pass
    
    def _apply_generic(self, driver, resume_path, cover_letter_path):
        """
        Apply to a job on a generic/unknown job site
        
        Args:
            driver (WebDriver): Selenium WebDriver
            resume_path (str): Path to resume file
            cover_letter_path (str): Path to cover letter file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Look for common file upload elements for resume
            resume_selectors = [
                "input[type='file'][name*='resume' i]",
                "input[type='file'][id*='resume' i]",
                "input[type='file'][name*='cv' i]",
                "input[type='file'][id*='cv' i]",
                "input[type='file'][name*='file' i]",
                "input[type='file']"  # Generic fallback
            ]
            
            resume_uploaded = False
            for selector in resume_selectors:
                try:
                    resume_upload = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    resume_upload.send_keys(resume_path)
                    logger.info(f"Resume uploaded using selector: {selector}")
                    resume_uploaded = True
                    break
                except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                    continue
            
            if not resume_uploaded:
                logger.warning("Could not find resume upload field")
            
            # Look for common file upload elements for cover letter
            cover_letter_selectors = [
                "input[type='file'][name*='cover' i]",
                "input[type='file'][id*='cover' i]",
                "input[type='file'][name*='letter' i]",
                "input[type='file'][id*='letter' i]"
            ]
            
            cover_letter_uploaded = False
            for selector in cover_letter_selectors:
                try:
                    cover_letter_upload = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    cover_letter_upload.send_keys(cover_letter_path)
                    logger.info(f"Cover letter uploaded using selector: {selector}")
                    cover_letter_uploaded = True
                    break
                except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                    continue
            
            if not cover_letter_uploaded:
                logger.warning("Could not find cover letter upload field")
            
            # Fill common form fields
            self._fill_generic_form_fields(driver)
            
            # Look for submit button
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button[id*='submit' i]",
                "button[class*='submit' i]",
                "button[id*='apply' i]",
                "button[class*='apply' i]",
                "a[id*='apply' i]",
                "a[class*='apply' i]"
            ]
            
            submit_clicked = False
            for selector in submit_selectors:
                try:
                    submit_button = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    submit_button.click()
                    logger.info(f"Submit button clicked using selector: {selector}")
                    submit_clicked = True
                    break
                except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                    continue
            
            if not submit_clicked:
                logger.warning("Could not find submit button")
                return False
            
            # Wait to see if the submission was successful
            time.sleep(5)
            
            # If the URL changed or there's a success message, assume it worked
            # This is a simple heuristic and might need adjustment
            current_url = driver.current_url
            if "thank" in current_url.lower() or "success" in current_url.lower() or "confirm" in current_url.lower():
                logger.info("Application appears to have been submitted successfully")
                return True
                
            # Look for common success messages in the page
            success_texts = ["thank you", "application received", "successfully submitted", "application submitted"]
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            
            for text in success_texts:
                if text in page_text:
                    logger.info(f"Success message found: '{text}'")
                    return True
            
            # If we can't confirm success, assume it might have worked
            logger.warning("Could not confirm application submission success")
            return True
            
        except Exception as e:
            logger.error(f"Error applying on generic site: {str(e)}")
            return False
    
    def _fill_generic_form_fields(self, driver):
        """
        Fill common form fields on generic job sites
        
        Args:
            driver (WebDriver): Selenium WebDriver
        """
        # Map common field names to environment variables
        fields_mapping = {
            "input[name*='first' i]": os.getenv("FIRST_NAME", ""),
            "input[name*='last' i]": os.getenv("LAST_NAME", ""),
            "input[name*='email' i]": os.getenv("EMAIL", ""),
            "input[name*='phone' i]": os.getenv("PHONE_NUMBER", ""),
            "input[name*='address' i]": os.getenv("ADDRESS", ""),
            "input[name*='city' i]": os.getenv("CITY", ""),
            "input[name*='state' i]": os.getenv("STATE", ""),
            "input[name*='zip' i]": os.getenv("ZIP_CODE", ""),
            "input[name*='postal' i]": os.getenv("ZIP_CODE", ""),
            "textarea[name*='cover' i]": os.getenv("COVER_LETTER_TEXT", ""),
            # Add more common field mappings as needed
        }
        
        for selector, value in fields_mapping.items():
            if not value:  # Skip empty values
                continue
                
            try:
                fields = driver.find_elements(By.CSS_SELECTOR, selector)
                for field in fields:
                    if field.is_displayed() and field.is_enabled():
                        field.clear()
                        field.send_keys(value)
                        logger.info(f"Filled field with selector: {selector}")
            except Exception:
                # Ignore errors for individual fields
                pass
                
        # Handle checkboxes for terms, privacy policy, etc.
        checkbox_selectors = [
            "input[type='checkbox'][name*='agree' i]",
            "input[type='checkbox'][id*='agree' i]",
            "input[type='checkbox'][name*='terms' i]",
            "input[type='checkbox'][id*='terms' i]",
            "input[type='checkbox'][name*='privacy' i]",
            "input[type='checkbox'][id*='privacy' i]"
        ]
        
        for selector in checkbox_selectors:
            try:
                checkboxes = driver.find_elements(By.CSS_SELECTOR, selector)
                for checkbox in checkboxes:
                    if checkbox.is_displayed() and checkbox.is_enabled() and not checkbox.is_selected():
                        checkbox.click()
                        logger.info(f"Checked checkbox with selector: {selector}")
            except Exception:
                # Ignore errors for individual checkboxes
                pass
    
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