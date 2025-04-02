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
from mock_user_profile import get_mock_user_profile

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
            
            <label for="address">Street Address</label>
            <input type="text" id="address" name="address">
            
            <label for="city">City</label>
            <input type="text" id="city" name="city">
            
            <label for="state">State</label>
            <select id="state" name="state">
                <option value="">Select a state</option>
                <option value="AL">Alabama</option>
                <option value="AK">Alaska</option>
                <option value="CA">California</option>
                <option value="NY">New York</option>
                <option value="TX">Texas</option>
                <option value="WA">Washington</option>
            </select>
            
            <label for="zipCode">ZIP Code</label>
            <input type="text" id="zipCode" name="zipCode">
            
            <label for="country">Country</label>
            <input type="text" id="country" name="country" value="United States">
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
            <input type="text" id="graduationDate" name="graduationDate">
        </div>
        
        <div class="form-section">
            <h2>Work Experience</h2>
            <label for="currentCompany">Current Company</label>
            <input type="text" id="currentCompany" name="currentCompany">
            
            <label for="jobTitle">Job Title</label>
            <input type="text" id="jobTitle" name="jobTitle">
            
            <label for="yearsOfExperience">Years of Experience</label>
            <input type="number" id="yearsOfExperience" name="yearsOfExperience" min="0">
            
            <label for="skills">Skills</label>
            <textarea id="skills" name="skills" rows="3"></textarea>
        </div>
        
        <div class="form-section">
            <h2>Social Media & Online Presence</h2>
            <label for="linkedin">LinkedIn URL</label>
            <input type="url" id="linkedin" name="linkedin">
            
            <label for="github">GitHub URL</label>
            <input type="url" id="github" name="github">
            
            <label for="portfolio">Portfolio URL</label>
            <input type="url" id="portfolio" name="portfolio">
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
            
            <label for="coverLetter">Cover Letter or Additional Information</label>
            <textarea id="coverLetter" name="coverLetter" rows="5"></textarea>
            
            <div class="checkbox-option">
                <input type="checkbox" id="termsAgreement" name="termsAgreement" value="agreed">
                <label for="termsAgreement">I agree to the terms and conditions</label>
            </div>
        </div>
        
        <button type="submit">Submit Application</button>
    </form>
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
    # For macOS ARM64, we use a different approach
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
        
        # Get the mock user profile
        user_profile = get_mock_user_profile()
        
        # Initialize the SmartFieldDetector
        detector = SmartFieldDetector(user_profile)
        logger.info("Initialized SmartFieldDetector with mock user profile")
        
        # Run the field detection
        logger.info("Running field detection...")
        stats = detector.detect_and_fill_fields(driver)
        
        # Print stats
        logger.info(f"Field detection stats: {stats}")
        logger.info(f"Processed: {stats['processed']}")
        logger.info(f"Filled: {stats['filled']}")
        logger.info(f"Skipped: {stats['skipped']}")
        logger.info(f"Errors: {stats.get('errors', 0)}")
        
        # Pause to inspect the form if in debug mode
        if debug:
            logger.info("Pausing for manual inspection (30 seconds)...")
            time.sleep(30)
        
        # Take a screenshot
        screenshot_path = os.path.join(os.getcwd(), "smart_field_detector_test.png")
        driver.save_screenshot(screenshot_path)
        logger.info(f"Saved screenshot to {screenshot_path}")
        
        # Verify the results
        success = stats['filled'] > 0
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