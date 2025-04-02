#!/usr/bin/env python3
"""
Test script for SmartFieldDetector

This script creates a simple local HTML form and tests that the SmartFieldDetector
can correctly identify and fill form fields based on the user profile.
"""

import os
import logging
import tempfile
import argparse
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from smart_field_detector import SmartFieldDetector
from dotenv import load_dotenv
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_user_profile_from_env():
    """Get user profile from environment variables"""
    load_dotenv()  # Load environment variables from .env file
    
    # Basic profile information
    profile = {
        'first_name': os.getenv('FIRST_NAME', ''),
        'last_name': os.getenv('LAST_NAME', ''),
        'email': os.getenv('EMAIL', ''),
        'phone': os.getenv('PHONE', ''),
        'date_of_birth': os.getenv('DATE_OF_BIRTH', ''),
        
        # Education information
        'education': [{
            'institution': os.getenv('EDUCATION_INSTITUTION', ''),
            'degree': os.getenv('EDUCATION_DEGREE', ''),
            'field_of_study': os.getenv('EDUCATION_FIELD', ''),
            'gpa': os.getenv('EDUCATION_GPA', ''),
            'start_date': os.getenv('EDUCATION_START_DATE', ''),
            'end_date': os.getenv('EDUCATION_END_DATE', ''),
            'graduation_date': os.getenv('EDUCATION_GRADUATION_DATE', '')
        }],
        
        # Work experience
        'work_experience': [{
            'company': os.getenv('CURRENT_COMPANY', ''),
            'title': os.getenv('CURRENT_TITLE', ''),
            'start_date': os.getenv('WORK_START_DATE', ''),
            'end_date': os.getenv('WORK_END_DATE', 'Present'),
            'description': os.getenv('WORK_DESCRIPTION', '')
        }],
        
        # Work preferences and eligibility
        'work_authorization': os.getenv('WORK_AUTHORIZATION', 'true').lower() == 'true',
        'requires_sponsorship': os.getenv('REQUIRES_SPONSORSHIP', 'false').lower() == 'true',
        'willing_to_relocate': os.getenv('WILLING_TO_RELOCATE', 'true').lower() == 'true',
        'willing_to_travel': os.getenv('WILLING_TO_TRAVEL', 'true').lower() == 'true',
        'prefers_remote': os.getenv('PREFERS_REMOTE', 'true').lower() == 'true',
        
        # File paths
        'resume_path': os.getenv('RESUME_PATH', ''),
        'cover_letter_path': os.getenv('COVER_LETTER_PATH', ''),
        'photo_path': os.getenv('PHOTO_PATH', ''),
        
        # Additional information
        'earliest_start_date': os.getenv('EARLIEST_START_DATE', ''),
        'availability_end_date': os.getenv('AVAILABILITY_END_DATE', ''),
        'salary_expectation': os.getenv('SALARY_EXPECTATION', '')
    }
    
    return profile

# HTML template for test forms
FORM_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SmartFieldDetector Test Form</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .form-section { margin-bottom: 30px; border: 1px solid #ddd; padding: 20px; border-radius: 5px; }
        h2 { margin-top: 0; color: #333; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, select, textarea { width: 100%; padding: 8px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 4px; }
        input[type="checkbox"], input[type="radio"] { width: auto; margin-right: 5px; }
        .radio-group, .checkbox-group { margin-bottom: 15px; }
        .radio-option, .checkbox-option { margin-bottom: 5px; }
        button { background-color: #4CAF50; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background-color: #45a049; }
        .loading { display: none; }
        .dynamic-section { display: none; }
    </style>
</head>
<body>
    <h1>Smart Form Detection Test</h1>
    <form id="test-form">
        <div class="form-section">
            <h2>Personal Information</h2>
            <label for="firstName">First Name</label>
            <input type="text" id="firstName" name="firstName" required>
            
            <label for="lastName">Last Name</label>
            <input type="text" id="lastName" name="lastName" required>
            
            <label for="email">Email Address</label>
            <input type="email" id="email" name="email" required>
            
            <label for="phone">Phone Number</label>
            <input type="tel" id="phone" name="phone">
            
            <label for="dob">Date of Birth</label>
            <input type="date" id="dob" name="dob">
            
            <label for="photo">Profile Photo</label>
            <input type="file" id="photo" name="photo" accept="image/*">
        </div>
        
        <div class="form-section">
            <h2>Education</h2>
            <label for="school">University/School</label>
            <input type="text" id="school" name="school">
            
            <label for="degree">Degree</label>
            <input type="text" id="degree" name="degree">
            
            <label for="major">Field of Study/Major</label>
            <input type="text" id="major" name="major">
            
            <label for="gpa">GPA</label>
            <input type="text" id="gpa" name="gpa">
            
            <label for="graduationDate">Graduation Date</label>
            <input type="date" id="graduationDate" name="graduationDate">
        </div>
        
        <div class="form-section">
            <h2>Work Experience</h2>
            <label for="currentCompany">Current Company</label>
            <input type="text" id="currentCompany" name="currentCompany">
            
            <label for="jobTitle">Job Title</label>
            <input type="text" id="jobTitle" name="jobTitle">
            
            <label for="startDate">Start Date</label>
            <input type="date" id="startDate" name="startDate">
            
            <label for="endDate">End Date</label>
            <input type="date" id="endDate" name="endDate">
            
            <label for="resume">Resume/CV</label>
            <input type="file" id="resume" name="resume" accept=".pdf,.doc,.docx">
            
            <label for="coverLetter">Cover Letter</label>
            <input type="file" id="coverLetter" name="coverLetter" accept=".pdf,.doc,.docx">
        </div>
        
        <div class="form-section">
            <h2>Work Eligibility & Preferences</h2>
            <div class="radio-group">
                <label>Are you authorized to work in the United States?</label>
                <div class="radio-option">
                    <input type="radio" id="authorizedYes" name="workAuthorized" value="yes">
                    <label for="authorizedYes">Yes</label>
                </div>
                <div class="radio-option">
                    <input type="radio" id="authorizedNo" name="workAuthorized" value="no">
                    <label for="authorizedNo">No</label>
                </div>
            </div>
            
            <div class="radio-group">
                <label>Do you require sponsorship to work in the United States?</label>
                <div class="radio-option">
                    <input type="radio" id="sponsorshipYes" name="requireSponsorship" value="yes">
                    <label for="sponsorshipYes">Yes</label>
                </div>
                <div class="radio-option">
                    <input type="radio" id="sponsorshipNo" name="requireSponsorship" value="no">
                    <label for="sponsorshipNo">No</label>
                </div>
            </div>
            
            <div class="checkbox-group">
                <label>Work Preferences:</label>
                <div class="checkbox-option">
                    <input type="checkbox" id="remoteWork" name="workPreferences" value="remote">
                    <label for="remoteWork">Remote Work</label>
                </div>
                <div class="checkbox-option">
                    <input type="checkbox" id="willingToRelocate" name="workPreferences" value="relocate">
                    <label for="willingToRelocate">Willing to Relocate</label>
                </div>
                <div class="checkbox-option">
                    <input type="checkbox" id="willingToTravel" name="workPreferences" value="travel">
                    <label for="willingToTravel">Willing to Travel</label>
                </div>
            </div>
        </div>
        
        <div class="form-section">
            <h2>Additional Information</h2>
            <label for="salaryExpectation">Salary Expectation</label>
            <input type="text" id="salaryExpectation" name="salaryExpectation">
            
            <label for="earliestStartDate">Earliest Start Date</label>
            <input type="date" id="earliestStartDate" name="earliestStartDate">
            
            <label for="availabilityEndDate">Availability End Date</label>
            <input type="date" id="availabilityEndDate" name="availabilityEndDate">
            
            <div class="checkbox-option">
                <input type="checkbox" id="termsAgreement" name="termsAgreement" value="agreed">
                <label for="termsAgreement">I agree to the terms and conditions</label>
            </div>
        </div>
        
        <button type="submit">Submit Application</button>
    </form>
    
    <script>
        // Simulate dynamic form loading
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                document.querySelector('.loading').style.display = 'none';
                document.querySelector('.dynamic-section').style.display = 'block';
            }, 2000);
        });
    </script>
</body>
</html>
"""

def create_test_form():
    """Create a temporary HTML file with the test form"""
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w') as f:
        f.write(FORM_TEMPLATE)
        return f.name

def run_test(debug=False):
    """
    Run the test script to verify the SmartFieldDetector functionality
    
    Args:
        debug (bool): Whether to run in debug mode (shows browser)
    """
    # Create the test form
    form_path = create_test_form()
    form_url = f"file://{form_path}"
    logger.info(f"Created test form at {form_path}")
    
    # Initialize browser
    options = Options()
    if not debug:
        options.add_argument("--headless=new")
    
    # Disable automation flags
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Create a new driver with simpler approach
    try:
        # First try the simple approach
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        logger.warning(f"Simple driver initialization failed: {str(e)}")
        try:
            # Try with ChromeDriverManager but specify mac-arm64 for Apple Silicon
            from webdriver_manager.core.os_manager import OperationSystemManager
            os_type = OperationSystemManager().get_os_type()
            if os_type == "mac" and os.uname().machine == 'arm64':
                logger.info("Detected macOS ARM64, using specific chromedriver")
                # Use webdriver-manager with specific platform
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            else:
                # Fallback to default
                driver = webdriver.Chrome(options=options)
        except Exception as e2:
            logger.error(f"Driver initialization failed: {str(e2)}")
            # Last resort, try using the system chrome directly
            driver = webdriver.Chrome(options=options)
    
    driver.maximize_window()
    
    try:
        # Load the test form
        driver.get(form_url)
        logger.info("Loaded test form in browser")
        
        # Get the user profile from environment variables
        user_profile = get_user_profile_from_env()
        logger.info("Loaded user profile from environment variables")
        
        # Initialize the SmartFieldDetector
        detector = SmartFieldDetector(user_profile)
        logger.info("Initialized SmartFieldDetector with user profile")
        
        # Run the field detection
        logger.info("Running field detection...")
        stats = detector.detect_and_fill_fields(driver)
        
        # Print stats
        logger.info(f"Field detection stats: {stats}")
        logger.info(f"Processed: {stats['processed']}")
        logger.info(f"Filled: {stats['filled']}")
        logger.info(f"Skipped: {stats['skipped']}")
        logger.info(f"Errors: {stats.get('errors', 0)}")
        logger.info(f"Retries: {stats.get('retries', 0)}")
        logger.info(f"Dynamic Fields: {stats.get('dynamic_fields', 0)}")
        
        # Pause to inspect the form if in debug mode
        if debug:
            logger.info("Pausing for manual inspection (30 seconds)...")
            time.sleep(30)
        
        # Take a screenshot
        screenshot_path = os.path.join(os.getcwd(), "smart_field_detector_test.png")
        driver.save_screenshot(screenshot_path)
        logger.info(f"Saved screenshot to {screenshot_path}")
        
        # Verify the results
        success = stats['filled'] > 0 and stats['errors'] == 0
        logger.info(f"Test {'PASSED' if success else 'FAILED'}")
        
        return success
        
    finally:
        # Clean up
        driver.quit()
        try:
            os.unlink(form_path)
        except Exception as e:
            logger.warning(f"Error removing temporary file: {str(e)}")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Test SmartFieldDetector functionality')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode (shows browser)')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    run_test(debug=args.debug) 