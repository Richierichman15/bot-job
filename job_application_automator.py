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
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException, WebDriverException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import traceback
from selenium.webdriver.support.ui import Select
from smart_field_detector import SmartFieldDetector
from mock_user_profile import get_mock_user_profile

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
    
    def __init__(self, config_path="config.json", debug=False, headless=True, use_incognito=True, test_mode=False):
        """
        Initialize the job application automator
        
        Args:
            config_path (str): Path to the configuration file
            debug (bool): Whether to run in debug mode (shows browser)
            headless (bool): Whether to run in headless mode
            use_incognito (bool): Whether to use incognito mode
            test_mode (bool): Whether to run in test mode (uses mock data)
        """
        # Load configuration
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            self.config = {
                "resume_path": os.getenv("RESUME_PATH", "resume.pdf"),
                "cover_letter_path": os.getenv("COVER_LETTER_PATH", "cover_letter.pdf"),
                "username": os.getenv("USERNAME", ""),
                "password": os.getenv("PASSWORD", ""),
                "job_platforms": {
                    "linkedin": True,
                    "indeed": True,
                    "glassdoor": True
                },
                "job_keywords": ["software engineer", "python developer"],
                "job_excluded_keywords": ["senior", "staff", "lead", "principal", "10+ years"],
                "job_locations": ["San Francisco", "Remote"],
                "blacklisted_companies": []
            }
        
        # Set debug mode
        self.debug = debug
        self.headless = not debug and headless
        self.use_incognito = use_incognito
        self.test_mode = test_mode
        
        # Load user profile
        if self.test_mode:
            # Use mock profile for testing
            self.user_profile = get_mock_user_profile()
            logger.info("Using mock user profile for testing")
        else:
            # Load from environment variables or config
            self.user_profile = self._load_user_profile()
            logger.info("Loaded user profile from environment/config")
        
        # Get settings from environment variables or parameters
        default_resume_path = "/Users/gitonga-nyaga/github/job/resume/GN.pdf"
        self.resume_path = self.config.get("resume_path", default_resume_path)
        self.application_path = self.config.get("applications_dir", "applications")
        self.cover_letter_template = self.config.get("cover_letter_template", "resume/cover_letter_template.txt")
        self.max_daily_applications = int(self.config.get("max_daily_applications", "5"))
        self.application_delay = float(self.config.get("application_delay", "2.0"))
        
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
        
        # Initialize Selenium WebDriver to None
        self.driver = None
        
        # Maximum retries for failed actions
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        
        # Timeouts
        self.page_load_timeout = int(os.getenv("PAGE_LOAD_TIMEOUT", "60"))
        self.element_timeout = int(os.getenv("ELEMENT_TIMEOUT", "10"))
        
        # Application status tracking
        self.current_application = None
        
        # Recovery points for resuming applications
        self.recovery_points = {}
        
        # CAPTCHA handling
        self.captcha_detection_enabled = os.getenv("CAPTCHA_DETECTION_ENABLED", "true").lower() == "true"
        self.captcha_service = os.getenv("CAPTCHA_SERVICE", None)
        self.captcha_api_key = os.getenv("CAPTCHA_API_KEY", None)
    
    def _initialize_browser(self):
        """
        Initialize and configure the Selenium WebDriver
        
        Returns:
            WebDriver: Configured Selenium WebDriver
        """
        if self.driver:
            try:
                # Check if browser is still responsive
                self.driver.title
                return self.driver
            except:
                # Browser crashed or is unresponsive, close it
                self._close_browser()
        
        try:
            # Configure Chrome options
            chrome_options = Options()
            
            # Run headless unless in debug mode
            if not os.getenv("DEBUG_BROWSER", "false").lower() == "true":
                chrome_options.add_argument("--headless")
                
            # Add common Chrome options for stability
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-gpu")
            
            # User agent to appear as a normal browser
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
            
            # Add preferences
            chrome_prefs = {
                "profile.default_content_settings.popups": 0,
                "download.default_directory": self.application_path,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", chrome_prefs)
            
            # Initialize the browser
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set timeouts
            driver.set_page_load_timeout(self.page_load_timeout)
            driver.set_script_timeout(self.page_load_timeout)
            
            # Set window size
            driver.set_window_size(1920, 1080)
            
            self.driver = driver
            logger.info("Successfully initialized Chrome WebDriver")
            return driver
        
        except Exception as e:
            logger.error(f"Error initializing browser: {str(e)}")
            if os.getenv("DEBUG_BROWSER", "false").lower() == "true":
                logger.error(traceback.format_exc())
            return None
    
    def _close_browser(self):
        """
        Safely close the browser
        """
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def _safe_click(self, element, retry_count=0, max_retries=3):
        """
        Safely click an element with retry logic
        
        Args:
            element: Selenium WebElement to click
            retry_count (int): Current retry attempt
            max_retries (int): Maximum number of retries
            
        Returns:
            bool: True if click was successful, False otherwise
        """
        if retry_count >= max_retries:
            logger.error(f"Failed to click element after {max_retries} attempts")
            return False
            
        try:
            # Try a standard click first
            element.click()
            return True
        except (ElementNotInteractableException, StaleElementReferenceException) as e:
            logger.warning(f"Click failed with {str(e)}, trying alternative methods")
            
            try:
                # Try to scroll the element into view
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.5)
                
                try:
                    # Try clicking again after scrolling
                    element.click()
                    return True
                except:
                    # Try JavaScript click
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
            except Exception as e2:
                logger.warning(f"Alternative click methods failed: {str(e2)}")
                
                # Wait a moment and retry
                time.sleep(1)
                return self._safe_click(element, retry_count + 1, max_retries)
        except Exception as e:
            logger.error(f"Unexpected error when clicking: {str(e)}")
            return False
    
    def _detect_and_handle_captcha(self, driver):
        """
        Detect and attempt to handle CAPTCHA challenges
        
        Args:
            driver (WebDriver): Selenium WebDriver
            
        Returns:
            bool: True if CAPTCHA was detected and handled, False otherwise
        """
        if not self.captcha_detection_enabled:
            return False
            
        try:
            # Common CAPTCHA identifiers
            captcha_indicators = [
                "iframe[src*='recaptcha']",
                "iframe[src*='captcha']",
                "div.g-recaptcha",
                "div[class*='captcha']",
                "input[name*='captcha']"
            ]
            
            # Check for presence of CAPTCHA elements
            for indicator in captcha_indicators:
                try:
                    captcha_element = driver.find_elements(By.CSS_SELECTOR, indicator)
                    if captcha_element:
                        logger.warning("CAPTCHA detected, attempting to handle")
                        
                        # Take screenshot for manual review
                        screenshot_path = os.path.join(self.application_path, "captcha_screenshot.png")
                        driver.save_screenshot(screenshot_path)
                        
                        # If we have a CAPTCHA service configured, try to solve it
                        if self.captcha_service and self.captcha_api_key:
                            return self._solve_captcha(driver, captcha_element)
                        else:
                            logger.error("CAPTCHA detected but no solver service configured")
                            return False
                except:
                    continue
                    
            # No CAPTCHA detected
            return False
            
        except Exception as e:
            logger.error(f"Error in CAPTCHA detection: {str(e)}")
            return False
    
    def _solve_captcha(self, driver, captcha_element):
        """
        Attempt to solve a CAPTCHA using an external service
        
        Args:
            driver (WebDriver): Selenium WebDriver
            captcha_element: The CAPTCHA element
            
        Returns:
            bool: True if CAPTCHA was solved, False otherwise
        """
        # This would integrate with a CAPTCHA solving service like 2captcha, Anti-Captcha, etc.
        # For now, we'll just log that we would solve it here
        logger.info("CAPTCHA solving would occur here if configured")
        return False
    
    def _save_application_state(self, application, state):
        """
        Save the current state of an application for possible recovery
        
        Args:
            application (dict): Application data
            state (str): Current state in the application process
        """
        try:
            app_id = application.get('id') or application.get('job_id')
            if not app_id:
                return
                
            self.recovery_points[app_id] = {
                'state': state,
                'timestamp': time.time(),
                'url': self.driver.current_url if self.driver else None
            }
            
            # Save recovery points to disk
            recovery_file = os.path.join(self.log_dir, "recovery_points.json")
            with open(recovery_file, 'w') as f:
                json.dump(self.recovery_points, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving application state: {str(e)}")
    
    def _load_recovery_points(self):
        """
        Load saved recovery points for applications
        
        Returns:
            dict: Recovery points by application ID
        """
        try:
            recovery_file = os.path.join(self.log_dir, "recovery_points.json")
            if os.path.exists(recovery_file):
                with open(recovery_file, 'r') as f:
                    self.recovery_points = json.load(f)
                    return self.recovery_points
            return {}
        except Exception as e:
            logger.error(f"Error loading recovery points: {str(e)}")
            return {}
    
    def _record_application(self, application, status, error=None):
        """
        Record application in history
        
        Args:
            application (dict): Application data
            status (str): Status of the application (submitted, failed, etc.)
            error (str): Error message if status is error
            
        Returns:
            bool: True if recorded successfully, False otherwise
        """
        try:
            # Get application details
            metadata = application.get('metadata', {})
            
            job_title = metadata.get('job_title', application.get('job_title', 'Unknown Position'))
            company = metadata.get('company', metadata.get('employer_name', application.get('employer_name', 'Unknown Company')))
            apply_link = metadata.get('apply_link', application.get('job_apply_link', '#'))
            
            # Prepare application record
            application_record = {
                'job_id': application.get('job_id', str(uuid.uuid4())),
                'job_title': job_title,
                'company': company,
                'apply_link': apply_link,
                'application_date': datetime.now().isoformat(),
                'status': status
            }
            
            # Add error message if present
            if error:
                application_record['error'] = error
            
            # Add to application history
            if not self.application_history:
                self.application_history = self.load_application_history()
                
            # Update statistics
            today = datetime.now().strftime("%Y-%m-%d")
            
            if today not in self.application_history['stats']['by_date']:
                self.application_history['stats']['by_date'][today] = {
                    'count': 0,
                    'submitted': 0,
                    'failed': 0,
                    'error': 0
                }
                
            self.application_history['stats']['total'] += 1
            self.application_history['stats']['by_date'][today]['count'] += 1
            
            if status == 'submitted':
                self.application_history['stats']['submitted'] += 1
                self.application_history['stats']['by_date'][today]['submitted'] += 1
            elif status == 'failed':
                self.application_history['stats']['failed'] += 1
                self.application_history['stats']['by_date'][today]['failed'] += 1
            elif status == 'error':
                self.application_history['stats']['errors'] += 1
                self.application_history['stats']['by_date'][today]['error'] += 1
                
            # Add to applications list
            self.application_history['applications'].append(application_record)
            
            # Save updated history
            self.save_application_history()
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording application: {str(e)}")
            return False
    
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
            # Set current application
            self.current_application = application
            
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
                    self._record_application(application, "submitted")
                    return True
                else:
                    logger.error(f"Test mode: Failed to submit application to {company}")
                    self._record_application(application, "failed")
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
            
            # Initialize the browser
            driver = self._initialize_browser()
            if not driver:
                logger.error("Failed to initialize browser")
                self._record_application(application, "error", error="Browser initialization failed")
                return False
            
            # Save application state
            self._save_application_state(application, "initialized")
            
            try:
                # Navigate to the application page
                logger.info(f"Navigating to application page: {apply_link}")
                driver.get(apply_link)
                
                # Wait for page to load
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Check for CAPTCHA
                if self._detect_and_handle_captcha(driver):
                    logger.info("CAPTCHA was detected and handled")
                
                # Save application state
                self._save_application_state(application, "page_loaded")
                
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
                self._close_browser()
                
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
                # Look for standard "Easy Apply" button
                apply_button = None
                apply_selectors = [
                    ".jobs-apply-button",
                    "button[aria-label='Easy Apply']",
                    "button[aria-label='Apply']",
                    "button[data-control-name='jobdetails_apply_button']"
                ]
                
                for selector in apply_selectors:
                    try:
                        apply_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        if apply_button:
                            break
                    except TimeoutException:
                        continue
                
                if not apply_button:
                    # Check if we have an "Apply on company website" button
                    try:
                        external_apply = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Apply on company website']"))
                        )
                        external_apply.click()
                        logger.info("Redirected to company website for application")
                        # Wait for the new tab/window to open
                        time.sleep(3)
                        
                        # Switch to the new tab if available
                        if len(driver.window_handles) > 1:
                            driver.switch_to.window(driver.window_handles[1])
                            logger.info(f"Switched to company website: {driver.current_url}")
                            # Now use the generic application method for the company website
                            return self._apply_generic(driver, resume_path, cover_letter_path)
                        else:
                            logger.error("External application opened but couldn't switch to new tab")
                            return False
                    except TimeoutException:
                        logger.error("No apply button found on LinkedIn job page")
                        return False
                
                # Click the Easy Apply button
                apply_button.click()
                logger.info("Clicked LinkedIn Easy Apply button")
            except Exception as e:
                logger.error(f"Error finding LinkedIn apply button: {str(e)}")
                return False
            
            # Wait for the application form
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-easy-apply-content"))
                )
                logger.info("LinkedIn application form loaded")
            except TimeoutException:
                logger.error("LinkedIn application form not loaded")
                return False
            
            # Upload resume if resume upload field is present
            try:
                resume_upload = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file'][name='resume']"))
                )
                resume_upload.send_keys(resume_path)
                logger.info("Resume uploaded successfully to LinkedIn")
            except (TimeoutException, NoSuchElementException):
                logger.warning("Resume upload field not found on LinkedIn, might be pre-filled")
            
            # Upload cover letter if the field is present
            try:
                # Try different possible selectors for cover letter upload
                cover_letter_selectors = [
                    "input[type='file'][name='cover-letter']",
                    "input[type='file'][name='coverLetter']",
                    "input[type='file'][data-test-form-element-file-upload-input='']"
                ]
                
                for selector in cover_letter_selectors:
                    try:
                        cover_letter_upload = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        cover_letter_upload.send_keys(cover_letter_path)
                        logger.info("Cover letter uploaded successfully to LinkedIn")
                        break
                    except (TimeoutException, NoSuchElementException):
                        continue
            except Exception as e:
                logger.warning(f"Error uploading cover letter to LinkedIn: {str(e)}")
            
            # Handle additional documents if requested
            try:
                # Check if there's a prompt to upload additional documents
                additional_doc_text = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, "//p[contains(text(), 'Upload additional')]"))
                )
                
                # If additional documents are optional, click "Skip"
                try:
                    skip_button = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Skip')]"))
                    )
                    skip_button.click()
                    logger.info("Skipped optional additional documents on LinkedIn")
                except:
                    logger.warning("No skip button found for additional documents")
            except:
                # No additional documents prompt, continue
                pass
            
            # Handle multiple steps in the application process
            max_steps = 20  # Prevent infinite loops
            current_step = 0
            
            while current_step < max_steps:
                current_step += 1
                logger.info(f"Processing LinkedIn application step {current_step}")
                
                # Wait a moment for the form to fully load
                time.sleep(1.5)
                
                # Run smart field detection on the current step
                logger.info("Running smart field detection on LinkedIn form...")
                stats = self._smart_field_detection(driver)
                logger.info(f"Smart field detection results: {stats}")
                
                # If few or no fields were filled, fall back to the existing specific field handlers
                if stats["filled"] < 3:
                    logger.info("Few fields filled by smart detection, falling back to specific LinkedIn handlers")
                    self._fill_linkedin_form_fields(driver)
                    self._handle_linkedin_custom_questions(driver)
                
                # Handle Work Authorization question if present
                try:
                    work_auth_dropdown = WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test-dropdown-trigger]"))
                    )
                    work_auth_dropdown.click()
                    
                    # Select "Yes, I am legally authorized" option
                    auth_options = driver.find_elements(By.CSS_SELECTOR, ".jobs-easy-apply-dropdown__option")
                    for option in auth_options:
                        if "yes" in option.text.lower() and "authorized" in option.text.lower():
                            option.click()
                            logger.info("Selected 'Yes' for work authorization")
                            break
                except:
                    # No work authorization dropdown on this step
                    pass
                
                # Handle "How many years of X experience" questions
                try:
                    experience_dropdowns = driver.find_elements(By.CSS_SELECTOR, "[data-test-dropdown-trigger]")
                    for dropdown in experience_dropdowns:
                        if "experience" in dropdown.text.lower() or "years" in dropdown.text.lower():
                            dropdown.click()
                            time.sleep(1)
                            
                            # Select an appropriate option (usually 2+ years)
                            options = driver.find_elements(By.CSS_SELECTOR, ".jobs-easy-apply-dropdown__option")
                            for option in options:
                                if "2" in option.text or "two" in option.text.lower() or "3" in option.text:
                                    option.click()
                                    logger.info(f"Selected '{option.text}' for experience question")
                                    break
                except:
                    # No experience dropdowns on this step
                    pass
                
                # Handle radio buttons for yes/no questions
                try:
                    radio_groups = driver.find_elements(By.CSS_SELECTOR, "fieldset.fb-radio-buttons")
                    for group in radio_groups:
                        question_text = group.find_element(By.XPATH, "./preceding-sibling::label").text.lower()
                        radio_buttons = group.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                        
                        # Default to "Yes" for most questions
                        selected = False
                        for radio in radio_buttons:
                            # Get the label text
                            label_id = radio.get_attribute("id")
                            label = driver.find_element(By.XPATH, f"//label[@for='{label_id}']")
                            
                            if "yes" in label.text.lower():
                                radio.click()
                                selected = True
                                logger.info(f"Selected 'Yes' for question: {question_text}")
                                break
                        
                        # If no "Yes" option, select the first option
                        if not selected and radio_buttons:
                            radio_buttons[0].click()
                            logger.info(f"Selected first option for question: {question_text}")
                except Exception as e:
                    # No radio buttons on this step
                    pass
                
                # Look for next or submit button
                next_button = None
                try:
                    # First try to find Next button
                    next_selectors = [
                        "button[aria-label='Continue to next step']",
                        "button[aria-label='Next']",
                        "button[data-control-name='continue_unify']",
                        "footer button:not([aria-label='Dismiss'])"
                    ]
                    
                    for selector in next_selectors:
                        try:
                            next_button = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                            if next_button:
                                break
                        except TimeoutException:
                            continue
                        
                    if not next_button:
                        # Look for "Review" button
                        try:
                            review_button = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Review')]"))
                            )
                            review_button.click()
                            logger.info("Clicked Review button")
                            time.sleep(2)
                            continue
                        except TimeoutException:
                            pass
                            
                        # Look for Submit button
                        submit_selectors = [
                            "button[aria-label='Submit application']",
                            "button[aria-label='Submit']",
                            "button[data-control-name='submit_unify']",
                            "button.jobs-apply-button"
                        ]
                        
                        for selector in submit_selectors:
                            try:
                                submit_button = WebDriverWait(driver, 3).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                )
                                submit_button.click()
                                logger.info("Application submitted successfully on LinkedIn")
                                
                                # Wait for confirmation
                                try:
                                    WebDriverWait(driver, 10).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, ".artdeco-inline-feedback--success"))
                                    )
                                    logger.info("Received success confirmation from LinkedIn")
                                except:
                                    logger.warning("No success confirmation found, but submission appears completed")
                                    
                                return True
                            except TimeoutException:
                                continue
                            
                        logger.error("No Next, Review, or Submit button found on LinkedIn application")
                        return False
                except TimeoutException:
                    logger.error("No navigation buttons found on LinkedIn application")
                    return False
                
                # Click Next button and wait for next page
                try:
                    next_button.click()
                    logger.info("Clicked Next button, moving to next step")
                    time.sleep(2)  # Wait for the next step to load
                except Exception as e:
                    logger.error(f"Error clicking Next button: {str(e)}")
                    return False
            
            logger.warning(f"Reached maximum steps ({max_steps}) for LinkedIn application")
            return False
            
        except Exception as e:
            logger.error(f"Error applying on LinkedIn: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _fill_linkedin_form_fields(self, driver):
        """
        Fill common LinkedIn form fields
        
        Args:
            driver (WebDriver): Selenium WebDriver
        """
        try:
            # Map of field types to environment variables and default values
            fields_mapping = {
                # Text inputs
                "input[name='phoneNumber']": os.getenv("PHONE_NUMBER", ""),
                "input[name='phone']": os.getenv("PHONE_NUMBER", ""),
                "input[name='email']": os.getenv("EMAIL", ""),
                "input[name='firstName']": os.getenv("FIRST_NAME", ""),
                "input[name='lastName']": os.getenv("LAST_NAME", ""),
                "input[name='address']": os.getenv("ADDRESS", ""),
                "input[name='city']": os.getenv("CITY", ""),
                "input[name='state']": os.getenv("STATE", ""),
                "input[name='zipCode']": os.getenv("ZIP_CODE", ""),
                "input[name='postal']": os.getenv("ZIP_CODE", ""),
                "input[name='website']": os.getenv("PORTFOLIO_URL", os.getenv("GITHUB_URL", "")),
                "input[name='githubUrl']": os.getenv("GITHUB_URL", ""),
                "input[name='portfolioUrl']": os.getenv("PORTFOLIO_URL", ""),
                "input[name='linkedin']": os.getenv("LINKEDIN_URL", ""),
                "input[name='salary']": os.getenv("EXPECTED_SALARY", ""),
                
                # Text areas (for longer text)
                "textarea[name='additionalInfo']": os.getenv("ADDITIONAL_INFO", "I'm passionate about technology and continuously developing my skills."),
                "textarea[name='customMessage']": os.getenv("COVER_LETTER_TEXT", "I am excited about this position and believe my skills are a perfect match..."),
                
                # Checkboxes
                "input[id='follow-company-checkbox']": True,  # Checkbox to follow company
                "input[id='contact-for-opportunities-checkbox']": True,  # Checkbox to be contacted for future opportunities
                "input[type='checkbox'][name*='agree']": True,  # Terms agreement checkbox
                "input[type='checkbox'][name*='privacy']": True,  # Privacy policy agreement checkbox
                "input[type='checkbox'][name*='terms']": True,  # Terms agreement checkbox
            }
            
            # Process each field
            for selector, value in fields_mapping.items():
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        # Skip hidden or disabled fields
                        if not element.is_displayed() or not element.is_enabled():
                            continue
                            
                        # Handle different element types
                        tag_name = element.tag_name.lower()
                        
                        if isinstance(value, bool) and value is True:
                            # Handle checkboxes
                            if tag_name == "input" and element.get_attribute("type") == "checkbox" and not element.is_selected():
                                element.click()
                                logger.info(f"Checked checkbox with selector: {selector}")
                        elif tag_name == "textarea":
                            # Handle textareas
                            element.clear()
                            element.send_keys(value)
                            logger.info(f"Filled textarea with selector: {selector}")
                        else:
                            # Handle text inputs
                            element.clear()
                            element.send_keys(value)
                            logger.info(f"Filled text field with selector: {selector}")
                except (TimeoutException, NoSuchElementException, ElementNotInteractableException) as e:
                    # Field not present on this page, continue
                    continue
                except Exception as e:
                    logger.warning(f"Error filling field with selector {selector}: {str(e)}")
                    continue
            
            # Handle custom questions with specific text patterns
            self._handle_linkedin_custom_questions(driver)
                
        except Exception as e:
            logger.error(f"Error filling LinkedIn form fields: {str(e)}")
    
    def _handle_linkedin_custom_questions(self, driver):
        """
        Handle LinkedIn custom questions by detecting patterns in question text
        
        Args:
            driver (WebDriver): Selenium WebDriver
        """
        try:
            # Get all visible questions
            questions = driver.find_elements(By.CSS_SELECTOR, ".jobs-easy-apply-form-section__grouping")
            
            for question in questions:
                try:
                    # Get the question text
                    question_element = question.find_element(By.CSS_SELECTOR, "label, legend")
                    question_text = question_element.text.lower()
                    
                    # Skip if no text
                    if not question_text:
                        continue
                    
                    # Salary expectations
                    if "salary" in question_text or "compensation" in question_text or "expected pay" in question_text:
                        # Look for text input
                        try:
                            salary_input = question.find_element(By.CSS_SELECTOR, "input[type='text']")
                            salary_input.clear()
                            salary_input.send_keys(os.getenv("EXPECTED_SALARY", "100000"))
                            logger.info(f"Filled salary question: {question_text}")
                            continue
                        except NoSuchElementException:
                            # Maybe it's a dropdown
                            try:
                                dropdown = question.find_element(By.CSS_SELECTOR, "[data-test-dropdown-trigger]")
                                dropdown.click()
                                time.sleep(1)
                                
                                # Choose a value in the middle range
                                options = driver.find_elements(By.CSS_SELECTOR, ".jobs-easy-apply-dropdown__option")
                                if options:
                                    middle_option = options[len(options) // 2]
                                    middle_option.click()
                                    logger.info(f"Selected middle option for salary: {middle_option.text}")
                            except:
                                logger.warning(f"Could not handle salary question: {question_text}")
                            continue
                    
                    # Start date
                    if "start date" in question_text or "start work" in question_text or "when can you start" in question_text:
                        # Look for text input
                        try:
                            date_input = question.find_element(By.CSS_SELECTOR, "input[type='text']")
                            date_input.clear()
                            date_input.send_keys("Immediately")
                            logger.info(f"Filled start date question: {question_text}")
                        except NoSuchElementException:
                            # Maybe it's a dropdown
                            try:
                                dropdown = question.find_element(By.CSS_SELECTOR, "[data-test-dropdown-trigger]")
                                dropdown.click()
                                time.sleep(1)
                                
                                # Choose immediate or 2 weeks
                                options = driver.find_elements(By.CSS_SELECTOR, ".jobs-easy-apply-dropdown__option")
                                for option in options:
                                    if "immediate" in option.text.lower() or "right away" in option.text.lower():
                                        option.click()
                                        logger.info(f"Selected immediate start: {option.text}")
                                        break
                                else:
                                    # If no immediate option, select first option
                                    if options:
                                        options[0].click()
                                        logger.info(f"Selected first start date option: {options[0].text}")
                            except:
                                logger.warning(f"Could not handle start date question: {question_text}")
                        continue
                    
                    # Work authorization
                    if "authorized" in question_text or "work authorization" in question_text or "legally" in question_text and "work" in question_text:
                        try:
                            # Try to find Yes radio button
                            radios = question.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                            for radio in radios:
                                # Get the label
                                label_id = radio.get_attribute("id")
                                label = driver.find_element(By.XPATH, f"//label[@for='{label_id}']")
                                
                                if "yes" in label.text.lower():
                                    radio.click()
                                    logger.info(f"Selected 'Yes' for work authorization")
                                    break
                        except:
                            # Try dropdown
                            try:
                                dropdown = question.find_element(By.CSS_SELECTOR, "[data-test-dropdown-trigger]")
                                dropdown.click()
                                time.sleep(1)
                                
                                options = driver.find_elements(By.CSS_SELECTOR, ".jobs-easy-apply-dropdown__option")
                                for option in options:
                                    if "yes" in option.text.lower() and "authorized" in option.text.lower():
                                        option.click()
                                        logger.info(f"Selected 'Yes' for work authorization")
                                        break
                            except:
                                logger.warning(f"Could not handle work authorization question: {question_text}")
                        continue
                
                except Exception as e:
                    logger.warning(f"Error processing question: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error handling LinkedIn custom questions: {str(e)}")
    
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
            # Check if we need to sign in first
            try:
                sign_in_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-testid='login-link']"))
                )
                logger.warning("Indeed login required, cannot proceed with application")
                
                # Take screenshot of the login page
                driver.save_screenshot("indeed_login_required.png")
                return False
            except TimeoutException:
                # No sign in required, continue
                pass
                
            # Wait for the apply button
            try:
                # Look for various apply button patterns
                apply_button = None
                apply_selectors = [
                    ".jobsearch-IndeedApplyButton",
                    "button[id*='indeed-apply-button']",
                    "button[aria-label='Apply now']",
                    "button.indeed-apply-button",
                    "a[data-testid='apply-button-link']",
                    "div.ia-IndeedApplyButton",
                    "button:contains('Apply')"
                ]
                
                for selector in apply_selectors:
                    try:
                        apply_button = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        if apply_button:
                            break
                    except TimeoutException:
                        continue
                
                if not apply_button:
                    # Check if there's an external apply button
                    try:
                        external_apply = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Apply on company site')]"))
                        )
                        external_apply.click()
                        logger.info("Redirected to company website for application")
                        
                        # Wait for the new tab/window to open
                        time.sleep(3)
                        
                        # Switch to the new tab if available
                        if len(driver.window_handles) > 1:
                            driver.switch_to.window(driver.window_handles[1])
                            logger.info(f"Switched to company website: {driver.current_url}")
                            # Use the generic application method for the company website
                            return self._apply_generic(driver, resume_path, cover_letter_path)
                        else:
                            logger.error("External application opened but couldn't switch to new tab")
                            return False
                    except TimeoutException:
                        logger.error("No apply button found on Indeed job page")
                        return False
                
                # Click the apply button
                apply_button.click()
                logger.info("Clicked Indeed Apply button")
            except Exception as e:
                logger.error(f"Error finding Indeed apply button: {str(e)}")
                return False
            
            # Wait for the application iframe to load
            try:
                # Wait a bit for iframe to appear
                time.sleep(2)
                
                # Try different iframe identifiers
                iframe_found = False
                iframe_selectors = [
                    "iframe#indeedapply-iframe",
                    "iframe[id*='indeed-apply']",
                    "iframe.indeed-apply-iframe",
                    "iframe[src*='indeed.com']"
                ]
                
                for selector in iframe_selectors:
                    try:
                        iframe = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        driver.switch_to.frame(iframe)
                        iframe_found = True
                        logger.info("Switched to Indeed application iframe")
                        break
                    except (TimeoutException, NoSuchElementException):
                        continue
                
                if not iframe_found:
                    # Check if we're already in the application flow (no iframe needed)
                    try:
                        WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".ia-Resume-label, .ia-ContactInfo-label"))
                        )
                        logger.info("Already in Indeed application flow (no iframe needed)")
                        iframe_found = True
                    except TimeoutException:
                        pass
                
                if not iframe_found:
                    logger.error("Indeed application iframe not found")
                    return False
            except Exception as e:
                logger.error(f"Error switching to Indeed application iframe: {str(e)}")
                return False
            
            # Upload resume if prompted
            try:
                resume_selectors = [
                    "input[type='file'][name='resume']",
                    "input[type='file'][data-testid='resume-upload-input']",
                    "input[type='file'][data-testid='resume-upload']",
                    "input[type='file'][accept='.pdf,.doc,.docx']"
                ]
                
                resume_uploaded = False
                for selector in resume_selectors:
                    try:
                        resume_upload = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        resume_upload.send_keys(resume_path)
                        logger.info(f"Resume uploaded to Indeed using selector: {selector}")
                        resume_uploaded = True
                        break
                    except (TimeoutException, NoSuchElementException):
                        continue
                
                if not resume_uploaded:
                    # Check if resume is already on file
                    try:
                        resume_on_file = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Resume on file')]"))
                        )
                        logger.info("Resume already on file with Indeed")
                    except TimeoutException:
                        logger.warning("Could not upload resume to Indeed and no resume on file found")
            except Exception as e:
                logger.error(f"Error handling Indeed resume upload: {str(e)}")
            
            # Look for "Continue with resume" button if present
            try:
                continue_with_resume = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue with resume')]"))
                )
                continue_with_resume.click()
                logger.info("Clicked 'Continue with resume' button")
                time.sleep(2)
            except TimeoutException:
                # Button not present, continue
                pass
            
            # Continue button after resume upload
            try:
                continue_selectors = [
                    ".ia-continueButton",
                    "button[data-testid='ia-continue-button']",
                    "button.icl-Button--primary",
                    "button:contains('Continue')",
                    "button.ia-ContinueButton"
                ]
                
                continue_clicked = False
                for selector in continue_selectors:
                    try:
                        continue_button = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        continue_button.click()
                        logger.info(f"Clicked continue button using selector: {selector}")
                        continue_clicked = True
                        time.sleep(2)
                        break
                    except (TimeoutException, NoSuchElementException):
                        continue
                
                if not continue_clicked:
                    logger.warning("No continue button found after resume upload")
            except Exception as e:
                logger.error(f"Error clicking continue after resume upload: {str(e)}")
            
            # Handle multiple steps in the Indeed application
            step_count = 0
            max_steps = 15  # Prevent infinite loops
            
            while step_count < max_steps:
                step_count += 1
                logger.info(f"Processing Indeed application step {step_count}")
                
                # Wait a moment for the form to fully load
                time.sleep(2)
                
                # Run smart field detection on the current step
                logger.info("Running smart field detection on Indeed form...")
                stats = self._smart_field_detection(driver)
                logger.info(f"Smart field detection results: {stats}")
                
                # If few or no fields were filled, fall back to the existing specific field handlers
                if stats["filled"] < 3:
                    logger.info("Few fields filled by smart detection, falling back to specific Indeed handlers")
                    self._fill_indeed_form_fields(driver)
                    self._handle_indeed_common_questions(driver)
                
                # Handle possible cover letter prompt
                try:
                    # Look for cover letter upload
                    cover_letter_selectors = [
                        "input[type='file'][name*='cover']",
                        "input[type='file'][accept*='.pdf'][name!='resume']",
                        "input[type='file'][data-testid='cover-letter-upload-input']"
                    ]
                    
                    for selector in cover_letter_selectors:
                        try:
                            cover_letter_upload = WebDriverWait(driver, 3).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                            cover_letter_upload.send_keys(cover_letter_path)
                            logger.info("Cover letter uploaded to Indeed")
                            break
                        except (TimeoutException, NoSuchElementException):
                            continue
                    
                    # Look for cover letter text area
                    try:
                        cover_letter_textarea = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[name*='cover'], textarea[placeholder*='cover']"))
                        )
                        
                        # If we have a cover letter file, read it and use its content
                        cover_letter_text = os.getenv("COVER_LETTER_TEXT", "I am excited about this position and believe my skills are a perfect match...")
                        if os.path.exists(cover_letter_path):
                            try:
                                with open(cover_letter_path, 'r') as f:
                                    cover_letter_text = f.read()
                            except Exception as e:
                                logger.error(f"Error reading cover letter file: {str(e)}")
                        
                        cover_letter_textarea.clear()
                        cover_letter_textarea.send_keys(cover_letter_text)
                        logger.info("Filled cover letter text area")
                    except TimeoutException:
                        pass
                except Exception as e:
                    logger.error(f"Error handling cover letter: {str(e)}")
                
                # Handle common questions that might appear
                self._handle_indeed_common_questions(driver)
                
                # Look for continue or submit button
                next_button = None
                try:
                    # First try to find continue button
                    continue_selectors = [
                        ".ia-continueButton",
                        "button[data-testid='ia-continue-button']",
                        "button.icl-Button--primary",
                        "button:contains('Continue')",
                        "button.ia-ContinueButton"
                    ]
                    
                    next_button_found = False
                    for selector in continue_selectors:
                        try:
                            next_button = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                            if next_button:
                                next_button_found = True
                                break
                        except TimeoutException:
                            continue
                    
                    if not next_button_found:
                        # Try to find submit button
                        submit_selectors = [
                            ".ia-SubmitButton",
                            "button[data-testid='ia-submit-button']",
                            "button:contains('Submit')",
                            "button:contains('Submit application')",
                            "button.ia-SubmitApplication"
                        ]
                        
                        for selector in submit_selectors:
                            try:
                                submit_button = WebDriverWait(driver, 3).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                )
                                submit_button.click()
                                logger.info("Indeed application submitted successfully")
                                
                                # Wait for confirmation
                                try:
                                    WebDriverWait(driver, 10).until(
                                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Application submitted') or contains(text(), 'Successfully submitted')]"))
                                    )
                                    logger.info("Received application confirmation from Indeed")
                                except:
                                    logger.warning("No confirmation message found, but submission button was clicked")
                                
                                return True
                            except TimeoutException:
                                continue
                            
                        # If we get here, no continue or submit button was found
                        logger.warning("No continue or submit button found on Indeed, checking for review button")
                        
                        # Check for "Review" button
                        try:
                            review_button = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Review')]"))
                            )
                            review_button.click()
                            logger.info("Clicked Review button")
                            time.sleep(2)
                            continue
                        except TimeoutException:
                            logger.error("No continue, submit, or review button found on Indeed")
                            return False
                except Exception as e:
                    logger.error(f"Error finding navigation buttons on Indeed: {str(e)}")
                    return False
                
                # Click continue button and wait for next page
                try:
                    next_button.click()
                    logger.info("Clicked continue button, moving to next step")
                    time.sleep(2)  # Wait for the next step to load
                except Exception as e:
                    logger.error(f"Error clicking continue button: {str(e)}")
                    return False
            
            logger.warning(f"Reached maximum steps ({max_steps}) for Indeed application")
            return False
            
        except Exception as e:
            logger.error(f"Error applying on Indeed: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _fill_indeed_form_fields(self, driver):
        """
        Fill common Indeed form fields
        
        Args:
            driver (WebDriver): Selenium WebDriver
        """
        try:
            # Map of field types to environment variables and default values
            fields_mapping = {
                # Text inputs
                "input[name*='first' i]": os.getenv("FIRST_NAME", ""),
                "input[name*='last' i]": os.getenv("LAST_NAME", ""),
                "input[name*='email' i]": os.getenv("EMAIL", ""),
                "input[name*='phone' i]": os.getenv("PHONE_NUMBER", ""),
                "input[name='address1']": os.getenv("ADDRESS", ""),
                "input[name='city']": os.getenv("CITY", ""),
                "input[name='state']": os.getenv("STATE", ""),
                "input[name='zip']": os.getenv("ZIP_CODE", ""),
                "input[name='postal']": os.getenv("ZIP_CODE", ""),
                "input[name*='url' i]": os.getenv("PORTFOLIO_URL", os.getenv("GITHUB_URL", "")),
                "input[name*='website' i]": os.getenv("PORTFOLIO_URL", os.getenv("GITHUB_URL", "")),
                "input[name*='linkedin' i]": os.getenv("LINKEDIN_URL", ""),
                "input[name*='github' i]": os.getenv("GITHUB_URL", ""),
                "input[name*='salary' i]": os.getenv("EXPECTED_SALARY", ""),
                
                # Text areas
                "textarea[name*='additional' i]": os.getenv("ADDITIONAL_INFO", "I'm passionate about technology and continuously developing my skills."),
                "textarea[name*='summary' i]": os.getenv("PROFESSIONAL_SUMMARY", "Experienced software developer with a passion for creating efficient, maintainable code."),
                
                # Checkboxes
                "input[type='checkbox'][name*='agree' i]": True,  # Agreement checkbox
                "input[type='checkbox'][name*='consent' i]": True,  # Consent checkbox
                "input[type='checkbox'][name*='sponsor' i]": True,  # Sponsorship checkbox
                "input[type='checkbox'][name*='relocate' i]": os.getenv("WILLING_TO_RELOCATE", "true").lower() == "true",
                "input[type='checkbox'][name*='remote' i]": os.getenv("WILLING_TO_WORK_REMOTE", "true").lower() == "true",
            }
            
            # Process each field
            for selector, value in fields_mapping.items():
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        # Skip hidden or disabled fields
                        if not element.is_displayed() or not element.is_enabled():
                            continue
                            
                        # Handle different element types
                        tag_name = element.tag_name.lower()
                        
                        if isinstance(value, bool) and value is True:
                            # Handle checkboxes
                            if tag_name == "input" and element.get_attribute("type") == "checkbox" and not element.is_selected():
                                element.click()
                                logger.info(f"Checked checkbox with selector: {selector}")
                        elif tag_name == "textarea":
                            # Handle textareas
                            element.clear()
                            element.send_keys(value)
                            logger.info(f"Filled textarea with selector: {selector}")
                        else:
                            # Handle text inputs
                            element.clear()
                            element.send_keys(value)
                            logger.info(f"Filled text field with selector: {selector}")
                except (TimeoutException, NoSuchElementException):
                    # Field not present on this page, continue
                    continue
                except Exception as e:
                    logger.warning(f"Error filling field with selector {selector}: {str(e)}")
                    continue
            
            # Look for select/dropdown elements
            try:
                selects = driver.find_elements(By.TAG_NAME, "select")
                for select_element in selects:
                    select_id = select_element.get_attribute("id")
                    select_name = select_element.get_attribute("name")
                    
                    # Skip if not visible
                    if not select_element.is_displayed():
                        continue
                    
                    # Handle different types of dropdowns based on name/id
                    if select_name and ("education" in select_name.lower() or "degree" in select_name.lower()):
                        # Select Bachelor's degree or highest available
                        options = select_element.find_elements(By.TAG_NAME, "option")
                        selected = False
                        
                        # Look for specific degree values
                        degree_keywords = ["bachelor", "bs", "ba", "master", "ms", "ma"]
                        for option in options:
                            option_text = option.text.lower()
                            if any(keyword in option_text for keyword in degree_keywords):
                                option.click()
                                logger.info(f"Selected education: {option.text}")
                                selected = True
                                break
                        
                        # If no specific degree found, select the middle option
                        if not selected and len(options) > 1:
                            # Skip the first option (usually a placeholder)
                            mid_index = min(len(options) - 1, 2)
                            options[mid_index].click()
                            logger.info(f"Selected education (default): {options[mid_index].text}")
                    
                    elif select_name and ("experience" in select_name.lower() or "years" in select_name.lower()):
                        # Select 2-3 years experience or middle option
                        options = select_element.find_elements(By.TAG_NAME, "option")
                        selected = False
                        
                        for option in options:
                            option_text = option.text.lower()
                            if "2" in option_text or "two" in option_text or "3" in option_text or "three" in option_text:
                                option.click()
                                logger.info(f"Selected experience: {option.text}")
                                selected = True
                                break
                        
                        # If no specific experience found, select the middle option
                        if not selected and len(options) > 1:
                            # Skip the first option (usually a placeholder)
                            mid_index = min(len(options) - 1, 2)
                            options[mid_index].click()
                            logger.info(f"Selected experience (default): {options[mid_index].text}")
                    
                    elif select_name and ("state" in select_name.lower() or "province" in select_name.lower()):
                        # Select the provided state
                        state = os.getenv("STATE", "CA")
                        options = select_element.find_elements(By.TAG_NAME, "option")
                        selected = False
                        
                        for option in options:
                            option_value = option.get_attribute("value")
                            option_text = option.text
                            
                            if (option_value and option_value.upper() == state.upper()) or \
                               (option_text and state.upper() in option_text.upper()):
                                option.click()
                                logger.info(f"Selected state: {option.text}")
                                selected = True
                                break
                        
                        # If state not found, leave as default
                        if not selected:
                            logger.warning(f"Could not select state: {state}")
                    
                    # If it's any other dropdown and nothing is selected, select the first non-empty option
                    else:
                        options = select_element.find_elements(By.TAG_NAME, "option")
                        current_selection = select_element.get_attribute("value")
                        
                        # If nothing selected, choose first real option
                        if not current_selection and len(options) > 1:
                            for option in options[1:]:  # Skip first (usually placeholder)
                                option_value = option.get_attribute("value")
                                if option_value:
                                    option.click()
                                    logger.info(f"Selected default for dropdown: {option.text}")
                                    break
            except Exception as e:
                logger.warning(f"Error handling select fields: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error filling Indeed form fields: {str(e)}")
    
    def _handle_indeed_common_questions(self, driver):
        """
        Handle common Indeed application questions
        
        Args:
            driver (WebDriver): Selenium WebDriver
        """
        try:
            # Handle radio button groups
            radio_groups = driver.find_elements(By.CSS_SELECTOR, "fieldset")
            
            for group in radio_groups:
                try:
                    # Get the question text if available
                    question_text = ""
                    try:
                        question_element = group.find_element(By.XPATH, "./preceding-sibling::*[1]")
                        question_text = question_element.text.lower()
                    except:
                        # If no preceding sibling, try to find legend
                        try:
                            legend = group.find_element(By.TAG_NAME, "legend")
                            question_text = legend.text.lower()
                        except:
                            pass
                    
                    # Skip if we couldn't find the question text
                    if not question_text:
                        continue
                    
                    # Get all radio buttons in this group
                    radio_buttons = group.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                    if not radio_buttons:
                        continue
                    
                    # Handle based on question type
                    selected = False
                    
                    # Work authorization questions
                    if "authorized" in question_text or "legally" in question_text and "work" in question_text:
                        # Select "Yes" for work authorization
                        for radio in radio_buttons:
                            # Get the label
                            try:
                                label_id = radio.get_attribute("id")
                                label = driver.find_element(By.XPATH, f"//label[@for='{label_id}']")
                                
                                if "yes" in label.text.lower():
                                    radio.click()
                                    logger.info(f"Selected 'Yes' for work authorization question: {question_text}")
                                    selected = True
                                    break
                            except:
                                continue
                    
                    # Sponsorship questions (usually want to answer "No")
                    elif "sponsor" in question_text or "sponsorship" in question_text:
                        # In most cases, employers prefer candidates who don't need sponsorship
                        need_sponsorship = os.getenv("NEED_SPONSORSHIP", "false").lower() == "true"
                        
                        for radio in radio_buttons:
                            try:
                                label_id = radio.get_attribute("id")
                                label = driver.find_element(By.XPATH, f"//label[@for='{label_id}']")
                                
                                if need_sponsorship and "yes" in label.text.lower():
                                    radio.click()
                                    logger.info(f"Selected 'Yes' for sponsorship question: {question_text}")
                                    selected = True
                                    break
                                elif not need_sponsorship and "no" in label.text.lower():
                                    radio.click()
                                    logger.info(f"Selected 'No' for sponsorship question: {question_text}")
                                    selected = True
                                    break
                            except:
                                continue
                    
                    # Relocation questions
                    elif "relocate" in question_text or "relocation" in question_text:
                        willing_to_relocate = os.getenv("WILLING_TO_RELOCATE", "true").lower() == "true"
                        
                        for radio in radio_buttons:
                            try:
                                label_id = radio.get_attribute("id")
                                label = driver.find_element(By.XPATH, f"//label[@for='{label_id}']")
                                
                                if willing_to_relocate and "yes" in label.text.lower():
                                    radio.click()
                                    logger.info(f"Selected 'Yes' for relocation question: {question_text}")
                                    selected = True
                                    break
                                elif not willing_to_relocate and "no" in label.text.lower():
                                    radio.click()
                                    logger.info(f"Selected 'No' for relocation question: {question_text}")
                                    selected = True
                                    break
                            except:
                                continue
                    
                    # Generic yes/no questions - default to "Yes" for most questions
                    elif not selected and len(radio_buttons) == 2:
                        # Assume it's a yes/no question and select "Yes"
                        for radio in radio_buttons:
                            try:
                                label_id = radio.get_attribute("id")
                                label = driver.find_element(By.XPATH, f"//label[@for='{label_id}']")
                                
                                if "yes" in label.text.lower():
                                    radio.click()
                                    logger.info(f"Selected 'Yes' for question: {question_text}")
                                    selected = True
                                    break
                            except:
                                continue
                    
                    # If still not selected and there are radio buttons, select the first one
                    if not selected and radio_buttons:
                        try:
                            radio_buttons[0].click()
                            logger.info(f"Selected first option for question: {question_text}")
                        except:
                            logger.warning(f"Could not select any option for question: {question_text}")
                
                except Exception as e:
                    logger.warning(f"Error processing radio group: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error handling Indeed common questions: {str(e)}")
    
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
            # Check if login wall appears
            try:
                login_container = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".ReactModalPortal, .authenticationModal"))
                )
                logger.warning("Glassdoor login wall detected, cannot proceed with application")
                driver.save_screenshot("glassdoor_login_required.png")
                return False
            except TimeoutException:
                # No login wall, continue
                pass
            
            # Wait for the apply button
            try:
                # Look for various apply button patterns
                apply_button = None
                apply_selectors = [
                    ".applyButton",
                    "button[data-test='apply-button']",
                    "a.gd-ui-button[data-test='apply-button']",
                    "button:contains('Apply Now')",
                    "button:contains('Easy Apply')",
                    "a[href*='glassdoor.com/partner/jobListing.htm']"
                ]
                
                for selector in apply_selectors:
                    try:
                        apply_button = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        if apply_button:
                            break
                    except TimeoutException:
                        continue
                
                if not apply_button:
                    # Check for an "Apply on company website" button
                    try:
                        external_apply = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Apply on company site') or contains(text(), 'Apply on Company Site')]"))
                        )
                        external_apply.click()
                        logger.info("Redirected to company website for application")
                        
                        # Wait for the new tab/window to open
                        time.sleep(3)
                        
                        # Switch to the new tab if available
                        if len(driver.window_handles) > 1:
                            driver.switch_to.window(driver.window_handles[1])
                            logger.info(f"Switched to company website: {driver.current_url}")
                            # Now use the generic application method for the company website
                            return self._apply_generic(driver, resume_path, cover_letter_path)
                        else:
                            logger.error("External application opened but couldn't switch to new tab")
                            return False
                    except TimeoutException:
                        logger.error("No apply button found on Glassdoor job page")
                        return False
                
                # Click the apply button
                apply_button.click()
                logger.info("Clicked Glassdoor Apply button")
            except Exception as e:
                logger.error(f"Error finding Glassdoor apply button: {str(e)}")
                return False
            
            # Check if we're redirected to another site
            # Wait a bit for potential redirect or modal to appear
            time.sleep(5)
            
            # Check for apply modal
            try:
                apply_modal = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".applyModal, .ApplicationModal, [data-test='APPLY_MODAL']"))
                )
                logger.info("Glassdoor application modal detected")
            except TimeoutException:
                # No modal, check if we're redirected to an external site
                current_url = driver.current_url
                if "glassdoor.com" not in current_url:
                    logger.info(f"Redirected to external site for application: {current_url}")
                    return self._apply_generic(driver, resume_path, cover_letter_path)
            
            # Handle Glassdoor's own application system
            # First check for "continue with resume" option
            try:
                continue_with_resume = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue with Resume') or contains(text(), 'Continue with resume')]"))
                )
                continue_with_resume.click()
                logger.info("Clicked 'Continue with resume' button on Glassdoor")
                time.sleep(2)
            except TimeoutException:
                # Button not present, continue with regular upload
                pass
            
            # Upload resume if prompt exists
            try:
                resume_selectors = [
                    "input[type='file'][name='resume']",
                    "input[type='file'][name='resumeFile']",
                    "input[type='file'][accept='.doc,.docx,.pdf']",
                    "input[type='file'][data-test='resume-upload-input']"
                ]
                
                resume_uploaded = False
                for selector in resume_selectors:
                    try:
                        resume_upload = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        resume_upload.send_keys(resume_path)
                        logger.info(f"Resume uploaded to Glassdoor using selector: {selector}")
                        resume_uploaded = True
                        break
                    except (TimeoutException, NoSuchElementException):
                        continue
                
                if not resume_uploaded:
                    logger.warning("Could not find resume upload field on Glassdoor")
            except Exception as e:
                logger.error(f"Error uploading resume to Glassdoor: {str(e)}")
            
            # Upload cover letter if field exists
            try:
                cover_letter_selectors = [
                    "input[type='file'][name='coverLetter']",
                    "input[type='file'][name='coverLetterFile']",
                    "input[type='file'][accept='.doc,.docx,.pdf,.txt'][name!='resume']",
                    "input[type='file'][data-test='coverletter-upload-input']"
                ]
                
                for selector in cover_letter_selectors:
                    try:
                        cover_letter_upload = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        cover_letter_upload.send_keys(cover_letter_path)
                        logger.info(f"Cover letter uploaded to Glassdoor using selector: {selector}")
                        break
                    except (TimeoutException, NoSuchElementException):
                        continue
                
                # Look for cover letter text area as alternative
                try:
                    cover_letter_textarea = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[name*='cover'], textarea[placeholder*='cover']"))
                    )
                    
                    # If we have a cover letter file, read it and use its content
                    cover_letter_text = os.getenv("COVER_LETTER_TEXT", "I am excited about this position and believe my skills are a perfect match...")
                    if os.path.exists(cover_letter_path):
                        try:
                            with open(cover_letter_path, 'r') as f:
                                cover_letter_text = f.read()
                        except Exception as e:
                            logger.error(f"Error reading cover letter file: {str(e)}")
                    
                    cover_letter_textarea.clear()
                    cover_letter_textarea.send_keys(cover_letter_text)
                    logger.info("Filled cover letter text area on Glassdoor")
                except TimeoutException:
                    logger.warning("No cover letter text area found on Glassdoor")
            except Exception as e:
                logger.warning(f"Error handling cover letter on Glassdoor: {str(e)}")
            
            # Fill out additional fields
            self._fill_glassdoor_form_fields(driver)
            
            # Handle multiple steps in the application process
            step_count = 0
            max_steps = 10  # Prevent infinite loops
            
            while step_count < max_steps:
                step_count += 1
                logger.info(f"Processing Glassdoor application step {step_count}")
                
                # Run smart field detection on the current step
                logger.info("Running smart field detection on Glassdoor form...")
                stats = self._smart_field_detection(driver)
                logger.info(f"Smart field detection results: {stats}")
                
                # If few or no fields were filled, fall back to the existing specific field handlers
                if stats["filled"] < 3:
                    logger.info("Few fields filled by smart detection, falling back to specific Glassdoor handlers")
                    self._fill_glassdoor_form_fields(driver)
                    self._handle_glassdoor_common_questions(driver)
                
                # Fill form fields again (for this step)
                self._fill_glassdoor_form_fields(driver)
                
                # Handle common Glassdoor questions
                self._handle_glassdoor_common_questions(driver)
                
                # Look for continue or submit button
                next_button = None
                try:
                    # First try to find continue button
                    continue_selectors = [
                        "button[data-test='continue-button']",
                        "button.e1ulk49s0",
                        "button:contains('Continue')",
                        "button:contains('Next')",
                        "button.continueButton"
                    ]
                    
                    next_button_found = False
                    for selector in continue_selectors:
                        try:
                            next_button = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                            if next_button:
                                next_button_found = True
                                break
                        except TimeoutException:
                            continue
                    
                    if not next_button_found:
                        # Try to find review button
                        try:
                            review_button = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Review')]"))
                            )
                            review_button.click()
                            logger.info("Clicked Review button on Glassdoor")
                            time.sleep(2)
                            continue
                        except TimeoutException:
                            pass
                        
                        # Try to find submit button
                        submit_selectors = [
                            "button[data-test='submit-button']",
                            "button[type='submit']",
                            "button:contains('Submit')",
                            "button:contains('Submit Application')",
                            "button.submit"
                        ]
                        
                        for selector in submit_selectors:
                            try:
                                submit_button = WebDriverWait(driver, 3).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                )
                                submit_button.click()
                                logger.info("Glassdoor application submitted successfully")
                                
                                # Wait for confirmation
                                try:
                                    WebDriverWait(driver, 10).until(
                                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Application submitted') or contains(text(), 'Successfully submitted')]"))
                                    )
                                    logger.info("Received application confirmation from Glassdoor")
                                except:
                                    logger.warning("No confirmation message found, but submission button was clicked")
                                
                                return True
                            except TimeoutException:
                                continue
                        
                        # If we get here, we couldn't find any navigation buttons
                        logger.error("No continue, review, or submit button found on Glassdoor")
                        return False
                except Exception as e:
                    logger.error(f"Error finding navigation buttons on Glassdoor: {str(e)}")
                    return False
                
                # Click continue button and wait for next page
                try:
                    next_button.click()
                    logger.info("Clicked continue button on Glassdoor, moving to next step")
                    time.sleep(2)  # Wait for the next step to load
                except Exception as e:
                    logger.error(f"Error clicking continue button on Glassdoor: {str(e)}")
                    return False
            
            logger.warning(f"Reached maximum steps ({max_steps}) for Glassdoor application")
            return False
                
        except Exception as e:
            logger.error(f"Error applying on Glassdoor: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _fill_glassdoor_form_fields(self, driver):
        """
        Fill common Glassdoor form fields
        
        Args:
            driver (WebDriver): Selenium WebDriver
        """
        try:
            # Map of field types to environment variables and default values
            fields_mapping = {
                # Text inputs
                "input[name='firstName']": os.getenv("FIRST_NAME", ""),
                "input[name='lastName']": os.getenv("LAST_NAME", ""),
                "input[name='email']": os.getenv("EMAIL", ""),
                "input[name='phoneNumber']": os.getenv("PHONE_NUMBER", ""),
                "input[name='phone']": os.getenv("PHONE_NUMBER", ""),
                "input[name='address']": os.getenv("ADDRESS", ""),
                "input[name='city']": os.getenv("CITY", ""),
                "input[name='zip']": os.getenv("ZIP_CODE", ""),
                "input[name='postal']": os.getenv("ZIP_CODE", ""),
                "input[name='workExperience']": os.getenv("YEARS_EXPERIENCE", "2"),
                "input[name='linkedinUrl']": os.getenv("LINKEDIN_URL", ""),
                "input[name='portfolioUrl']": os.getenv("PORTFOLIO_URL", ""),
                "input[name='githubUrl']": os.getenv("GITHUB_URL", ""),
                "input[name='desiredSalary']": os.getenv("EXPECTED_SALARY", ""),
                
                # Text areas
                "textarea[name='additionalInformation']": os.getenv("ADDITIONAL_INFO", "I'm passionate about technology and continuously developing my skills."),
                "textarea[name='customMessage']": os.getenv("COVER_LETTER_TEXT", "I am excited about this position and believe my skills are a perfect match..."),
                
                # Checkboxes
                "input[type='checkbox'][name*='agree']": True,
                "input[type='checkbox'][name*='privacy']": True,
                "input[type='checkbox'][name*='terms']": True,
            }
            
            # Process each field
            for selector, value in fields_mapping.items():
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        # Skip hidden or disabled fields
                        if not element.is_displayed() or not element.is_enabled():
                            continue
                            
                        # Handle different element types
                        tag_name = element.tag_name.lower()
                        
                        if isinstance(value, bool) and value is True:
                            # Handle checkboxes
                            if tag_name == "input" and element.get_attribute("type") == "checkbox" and not element.is_selected():
                                element.click()
                                logger.info(f"Checked checkbox with selector: {selector}")
                        elif tag_name == "textarea":
                            # Handle textareas
                            element.clear()
                            element.send_keys(value)
                            logger.info(f"Filled textarea with selector: {selector}")
                        else:
                            # Handle text inputs
                            element.clear()
                            element.send_keys(value)
                            logger.info(f"Filled text field with selector: {selector}")
                except (TimeoutException, NoSuchElementException):
                    # Field not present on this page, continue
                    continue
                except Exception as e:
                    logger.warning(f"Error filling field with selector {selector}: {str(e)}")
                    continue
            
            # Handle select/dropdown elements
            try:
                selects = driver.find_elements(By.TAG_NAME, "select")
                for select_element in selects:
                    # Skip if not visible
                    if not select_element.is_displayed():
                        continue
                    
                    select_name = select_element.get_attribute("name") or ""
                    
                    # Handle state dropdown
                    if "state" in select_name.lower():
                        state = os.getenv("STATE", "CA")
                        options = select_element.find_elements(By.TAG_NAME, "option")
                        
                        for option in options:
                            option_value = option.get_attribute("value")
                            option_text = option.text
                            
                            if (option_value and option_value.upper() == state.upper()) or \
                               (option_text and state.upper() in option_text.upper()):
                                option.click()
                                logger.info(f"Selected state: {option.text}")
                                break
                    
                    # Handle highest education level
                    elif "education" in select_name.lower() or "degree" in select_name.lower():
                        education_level = os.getenv("EDUCATION_LEVEL", "Bachelor's Degree")
                        options = select_element.find_elements(By.TAG_NAME, "option")
                        
                        selected = False
                        for option in options:
                            if education_level.lower() in option.text.lower():
                                option.click()
                                logger.info(f"Selected education level: {option.text}")
                                selected = True
                                break
                        
                        # If exact match not found, try keywords
                        if not selected:
                            education_keywords = ["bachelor", "degree", "college"]
                            for option in options:
                                for keyword in education_keywords:
                                    if keyword in option.text.lower():
                                        option.click()
                                        logger.info(f"Selected education level by keyword: {option.text}")
                                        selected = True
                                        break
                                if selected:
                                    break
            except Exception as e:
                logger.warning(f"Error handling select elements: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error filling Glassdoor form fields: {str(e)}")
    
    def _handle_glassdoor_common_questions(self, driver):
        """
        Handle common Glassdoor application questions
        
        Args:
            driver (WebDriver): Selenium WebDriver
        """
        try:
            # Look for radio button groups - common for yes/no questions
            try:
                # Find all possible question containers
                question_containers = driver.find_elements(By.CSS_SELECTOR, ".questionContainer, .form-group, fieldset")
                
                for container in question_containers:
                    try:
                        # Get the question text
                        question_element = container.find_element(By.CSS_SELECTOR, "label, legend, .question")
                        question_text = question_element.text.lower()
                        
                        # Skip if no text found
                        if not question_text:
                            continue
                        
                        # Find radio buttons in this container
                        radio_buttons = container.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                        
                        # Skip if no radio buttons
                        if not radio_buttons:
                            continue
                        
                        # Handle based on question type
                        selected = False
                        
                        # Work authorization
                        if "authorized" in question_text or "legally" in question_text and "work" in question_text:
                            for radio in radio_buttons:
                                try:
                                    # Get the label text
                                    label_id = radio.get_attribute("id")
                                    label = driver.find_element(By.XPATH, f"//label[@for='{label_id}']")
                                    
                                    if "yes" in label.text.lower():
                                        radio.click()
                                        logger.info(f"Selected 'Yes' for work authorization: {question_text}")
                                        selected = True
                                        break
                                except:
                                    continue
                        
                        # Sponsorship questions
                        elif "sponsor" in question_text or "sponsorship" in question_text:
                            need_sponsorship = os.getenv("NEED_SPONSORSHIP", "false").lower() == "true"
                            
                            for radio in radio_buttons:
                                try:
                                    label_id = radio.get_attribute("id")
                                    label = driver.find_element(By.XPATH, f"//label[@for='{label_id}']")
                                    
                                    if need_sponsorship and "yes" in label.text.lower():
                                        radio.click()
                                        logger.info(f"Selected 'Yes' for sponsorship question: {question_text}")
                                        selected = True
                                        break
                                    elif not need_sponsorship and "no" in label.text.lower():
                                        radio.click()
                                        logger.info(f"Selected 'No' for sponsorship question: {question_text}")
                                        selected = True
                                        break
                                except:
                                    continue
                        
                        # Default for yes/no questions (usually two radio buttons)
                        elif not selected and len(radio_buttons) == 2:
                            for radio in radio_buttons:
                                try:
                                    label_id = radio.get_attribute("id")
                                    label = driver.find_element(By.XPATH, f"//label[@for='{label_id}']")
                                    
                                    if "yes" in label.text.lower():
                                        radio.click()
                                        logger.info(f"Selected 'Yes' for question: {question_text}")
                                        selected = True
                                        break
                                except:
                                    continue
                        
                        # If still not selected, select the first option
                        if not selected and radio_buttons:
                            try:
                                radio_buttons[0].click()
                                logger.info(f"Selected first option for question: {question_text}")
                            except:
                                pass
                    
                    except Exception as e:
                        logger.warning(f"Error processing question container: {str(e)}")
                        continue
            
            except Exception as e:
                logger.warning(f"Error handling radio button questions: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error handling Glassdoor common questions: {str(e)}")
    
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
            # Start with smart field detection for any visible forms
            logger.info("Running smart field detection on generic application form...")
            stats = self._smart_field_detection(driver)
            logger.info(f"Smart field detection results: {stats}")
            
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
    
    def _smart_field_detection(self, driver):
        """
        Use smart field detection to fill out form fields
        
        Args:
            driver (WebDriver): Selenium WebDriver
            
        Returns:
            dict: Statistics about fields processed
        """
        try:
            # Initialize the smart field detector with user profile
            detector = SmartFieldDetector(self.user_profile)
            
            # Detect and fill fields
            stats = detector.detect_and_fill_fields(driver)
            
            return stats
        except Exception as e:
            logger.error(f"Error in smart field detection: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                'processed': 0,
                'filled': 0,
                'skipped': 0,
                'errors': 1
            }
    
    def _handle_checkbox(self, driver, checkbox, field_identifiers):
        """
        Intelligently handle checkbox fields
        
        Args:
            driver (WebDriver): Selenium WebDriver
            checkbox: The checkbox element
            field_identifiers (str): Combined field identifiers for pattern matching
            
        Returns:
            bool: True if checkbox was handled, False otherwise
        """
        try:
            # Common patterns for terms, agreements, etc. that should be checked
            positive_patterns = [
                r"agree|terms|consent|acknowledge|privacy|policy",
                r"subscribe|newsletter|updates|notifications",
                r"contact|opportunities|future|positions",
                r"confirm|certified|qualified|authorized"
            ]
            
            # Patterns for checkboxes that should generally NOT be checked
            negative_patterns = [
                r"unsubscribe|opt[ -]?out|no[ -]?contact",
                r"(don't|do not|never) (contact|email|call|text)",
                r"third[ -]?party"
            ]
            
            # Check if already selected
            if checkbox.is_selected():
                return True
            
            # Determine if checkbox should be checked
            should_check = False
            
            # Check against positive patterns
            for pattern in positive_patterns:
                if re.search(pattern, field_identifiers, re.IGNORECASE):
                    should_check = True
                    break
            
            # Check against negative patterns
            for pattern in negative_patterns:
                if re.search(pattern, field_identifiers, re.IGNORECASE):
                    should_check = False
                    break
                    
            # Try to examine the label for more context
            try:
                # Find associated label using for attribute
                checkbox_id = checkbox.get_attribute("id")
                if checkbox_id:
                    label = driver.find_element(By.CSS_SELECTOR, f"label[for='{checkbox_id}']")
                    label_text = label.text.lower()
                    
                    # Check label against positive patterns
                    for pattern in positive_patterns:
                        if re.search(pattern, label_text, re.IGNORECASE):
                            should_check = True
                            break
                    
                    # Check label against negative patterns
                    for pattern in negative_patterns:
                        if re.search(pattern, label_text, re.IGNORECASE):
                            should_check = False
                            break
            except (NoSuchElementException, StaleElementReferenceException):
                pass
            
            # Perform the click if it should be checked
            if should_check:
                self._safe_click(checkbox)
                logger.info(f"Checked checkbox for: {field_identifiers[:50]}...")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling checkbox: {str(e)}")
            return False
    
    def _handle_radio(self, driver, radio, field_identifiers, personal_info):
        """
        Intelligently handle radio button groups
        
        Args:
            driver (WebDriver): Selenium WebDriver
            radio: The radio button element
            field_identifiers (str): Combined field identifiers for pattern matching
            personal_info (dict): Personal information for making choices
            
        Returns:
            bool: True if radio was handled, False otherwise
        """
        try:
            # If radio already selected, skip
            if radio.is_selected():
                return True
                
            # Get the name to find the radio group
            radio_name = radio.get_attribute("name")
            if not radio_name:
                return False
                
            # Get all radios in this group
            radio_group = driver.find_elements(By.CSS_SELECTOR, f"input[type='radio'][name='{radio_name}']")
            if len(radio_group) <= 1:
                return False
                
            # Get the labels/values of all options
            options = []
            for option in radio_group:
                option_value = option.get_attribute("value") or ""
                option_id = option.get_attribute("id") or ""
                label_text = ""
                
                # Try to find label
                if option_id:
                    try:
                        label = driver.find_element(By.CSS_SELECTOR, f"label[for='{option_id}']")
                        label_text = label.text
                    except NoSuchElementException:
                        pass
                
                options.append({
                    "element": option,
                    "value": option_value.lower(),
                    "label": label_text.lower(),
                    "id": option_id
                })
            
            # Determine which radio to select based on context
            
            # Work authorization questions
            if re.search(r"authorized|legal|work.*permit|visa", field_identifiers, re.IGNORECASE):
                # Choose "Yes" for work authorization questions if not needing sponsorship
                if not personal_info["need_sponsorship"]:
                    for option in options:
                        if "yes" in option["value"] or "yes" in option["label"]:
                            self._safe_click(option["element"])
                            logger.info(f"Selected 'Yes' for work authorization question")
                            return True
                else:
                    # If need sponsorship, select appropriate option
                    for option in options:
                        if "no" in option["value"] or "no" in option["label"]:
                            self._safe_click(option["element"])
                            logger.info(f"Selected 'No' for work authorization question (requires sponsorship)")
                            return True
            
            # Relocation questions
            elif re.search(r"relocate|relocation|willing.*move", field_identifiers, re.IGNORECASE):
                willing_to_relocate = personal_info["willing_to_relocate"]
                for option in options:
                    if willing_to_relocate and ("yes" in option["value"] or "yes" in option["label"]):
                        self._safe_click(option["element"])
                        logger.info(f"Selected 'Yes' for relocation question")
                        return True
                    elif not willing_to_relocate and ("no" in option["value"] or "no" in option["label"]):
                        self._safe_click(option["element"])
                        logger.info(f"Selected 'No' for relocation question")
                        return True
            
            # Remote work questions
            elif re.search(r"remote|work.*home|telecommute", field_identifiers, re.IGNORECASE):
                willing_to_work_remote = personal_info["willing_to_work_remote"]
                for option in options:
                    if willing_to_work_remote and ("yes" in option["value"] or "yes" in option["label"]):
                        self._safe_click(option["element"])
                        logger.info(f"Selected 'Yes' for remote work question")
                        return True
                    elif not willing_to_work_remote and ("no" in option["value"] or "no" in option["label"]):
                        self._safe_click(option["element"])
                        logger.info(f"Selected 'No' for remote work question")
                        return True
            
            # Generic yes/no questions - default to yes for most things
            elif len(radio_group) == 2:
                # Look for yes option
                for option in options:
                    if "yes" in option["value"] or "yes" in option["label"]:
                        self._safe_click(option["element"])
                        logger.info(f"Selected 'Yes' for generic yes/no question")
                        return True
            
            # If all else fails, select first option (unless it's clearly a placeholder)
            for option in options:
                if option["value"] and not re.search(r"select|choose|placeholder", option["value"], re.IGNORECASE):
                    self._safe_click(option["element"])
                    logger.info(f"Selected first non-placeholder option: {option['value'] or option['label']}")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error handling radio button: {str(e)}")
            return False
    
    def _handle_select(self, driver, select_element, field_identifiers, personal_info):
        """
        Intelligently handle select/dropdown elements
        
        Args:
            driver (WebDriver): Selenium WebDriver
            select_element: The select element
            field_identifiers (str): Combined field identifiers for pattern matching
            personal_info (dict): Personal information for making choices
            
        Returns:
            bool: True if select was handled, False otherwise
        """
        try:
            # Skip if already has a value selected
            current_value = select_element.get_attribute("value")
            if current_value and current_value != "":
                return True
                
            # Get all options
            options = select_element.find_elements(By.TAG_NAME, "option")
            if len(options) <= 1:
                return False
                
            # Skip the first option if it appears to be a placeholder
            start_index = 0
            if len(options) > 1:
                first_option_text = options[0].text.lower()
                first_option_value = options[0].get_attribute("value") or ""
                if first_option_value == "" or re.search(r"select|choose|please|-----", first_option_text, re.IGNORECASE):
                    start_index = 1
                    
            # Education level dropdown
            if re.search(r"education|degree|qualification", field_identifiers, re.IGNORECASE):
                education_level = personal_info["education"].lower()
                
                # Look for exact match first
                for option in options[start_index:]:
                    option_text = option.text.lower()
                    if education_level in option_text:
                        option.click()
                        logger.info(f"Selected education level: {option.text}")
                        return True
                
                # Look for similar matches
                education_keywords = ["certification", "certificate", "web development", "bootcamp", "academy", "associate", "bachelor"]
                for option in options[start_index:]:
                    option_text = option.text.lower()
                    for keyword in education_keywords:
                        if keyword in option_text:
                            option.click()
                            logger.info(f"Selected education level with keyword match: {option.text}")
                            return True
            
            # Experience level dropdown
            elif re.search(r"experience|years", field_identifiers, re.IGNORECASE):
                years_experience = personal_info["years_experience"]
                
                # Look for exact match first
                for option in options[start_index:]:
                    option_text = option.text.lower()
                    if years_experience in option_text:
                        option.click()
                        logger.info(f"Selected experience level: {option.text}")
                        return True
                    
                # Try with patterns like "1-2 years", "2-3 years", etc.
                for option in options[start_index:]:
                    option_text = option.text.lower()
                    if re.search(r"1[\s-]*2|2[\s-]*3", option_text):
                        option.click()
                        logger.info(f"Selected experience level by pattern: {option.text}")
                        return True
            
            # State/location dropdown
            elif re.search(r"state|province", field_identifiers, re.IGNORECASE):
                state = personal_info["state"].upper()
                state_full = self._get_full_state_name(state).lower()
                
                for option in options[start_index:]:
                    option_text = option.text.lower()
                    option_value = option.get_attribute("value") or ""
                    
                    if (state.lower() == option_text.lower() or 
                        state.lower() == option_value.lower() or
                        state_full == option_text.lower()):
                        option.click()
                        logger.info(f"Selected state: {option.text}")
                        return True
            
            # Country dropdown
            elif re.search(r"country|nation", field_identifiers, re.IGNORECASE):
                country = personal_info["country"].lower()
                
                for option in options[start_index:]:
                    option_text = option.text.lower()
                    if "united states" in option_text or "usa" in option_text or "u.s" in option_text:
                        option.click()
                        logger.info(f"Selected country: {option.text}")
                        return True
            
            # If we couldn't make a specific match, select the second option (after placeholder)
            # This is usually a reasonable default for most dropdowns
            if len(options) > start_index:
                options[start_index].click()
                logger.info(f"Selected default option: {options[start_index].text}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error handling select element: {str(e)}")
            return False
    
    def _get_full_state_name(self, state_code):
        """
        Convert state code to full state name
        
        Args:
            state_code (str): Two-letter state code
            
        Returns:
            str: Full state name
        """
        state_map = {
            "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", 
            "CA": "California", "CO": "Colorado", "CT": "Connecticut", 
            "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", 
            "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", 
            "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", 
            "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", 
            "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", 
            "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", 
            "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", 
            "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", 
            "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", 
            "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", 
            "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", 
            "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", 
            "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia"
        }
        return state_map.get(state_code.upper(), state_code)
    
    def _load_user_profile(self):
        """
        Load user profile from environment variables or config file
        
        Returns:
            dict: User profile information
        """
        # Basic profile structure based on environment variables
        profile = {
            "first_name": os.getenv("FIRST_NAME", ""),
            "last_name": os.getenv("LAST_NAME", ""),
            "email": os.getenv("EMAIL", ""),
            "phone": os.getenv("PHONE", ""),
            "address": {
                "street": os.getenv("ADDRESS", ""),
                "city": os.getenv("CITY", ""),
                "state": os.getenv("STATE", ""),
                "zip_code": os.getenv("ZIP", ""),
                "country": os.getenv("COUNTRY", "United States")
            },
            "work_authorization": os.getenv("WORK_AUTHORIZATION", "true").lower() == "true",
            "requires_sponsorship": os.getenv("NEED_SPONSORSHIP", "false").lower() == "true",
            "willing_to_relocate": os.getenv("WILLING_TO_RELOCATE", "true").lower() == "true",
            "willing_to_travel": os.getenv("WILLING_TO_TRAVEL", "true").lower() == "true",
            "prefers_remote": os.getenv("PREFERS_REMOTE", "true").lower() == "true",
            "total_years_experience": os.getenv("YEARS_EXPERIENCE", ""),
            "expected_salary": os.getenv("EXPECTED_SALARY", ""),
            "professional_summary": os.getenv("PROFESSIONAL_SUMMARY", ""),
            "social_media": {
                "linkedin": os.getenv("LINKEDIN_URL", ""),
                "github": os.getenv("GITHUB_URL", ""),
            },
            "portfolio_url": os.getenv("PORTFOLIO_URL", ""),
            "personal_website": os.getenv("WEBSITE_URL", "")
        }
        
        # Check for a more detailed profile JSON file
        profile_path = os.getenv("USER_PROFILE_PATH", "user_profile.json")
        if os.path.exists(profile_path):
            try:
                with open(profile_path, 'r') as f:
                    detailed_profile = json.load(f)
                    # Merge with existing profile, with detailed profile taking precedence
                    profile = {**profile, **detailed_profile}
                    logger.info(f"Loaded detailed profile from {profile_path}")
            except Exception as e:
                logger.warning(f"Error loading detailed profile from {profile_path}: {str(e)}")
        
        return profile

# For testing
if __name__ == "__main__":
    automator = JobApplicationAutomator()
    automator.run(limit=3) 