import re
import logging
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, 
    ElementNotInteractableException, 
    StaleElementReferenceException,
    TimeoutException
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SmartFieldDetector:
    """
    A class that intelligently detects form fields and fills them appropriately based on user profiles.
    """
    
    def __init__(self, user_profile):
        """
        Initialize the smart field detector with user profile data.
        
        Args:
            user_profile (dict): User profile with all relevant information
        """
        self.profile = user_profile
        self.field_mapping = self._build_field_mapping()
        self.yes_values = ['yes', 'true', 'y', '1', 'agree']
        self.no_values = ['no', 'false', 'n', '0', 'disagree']
        
    def _build_field_mapping(self):
        """
        Build a comprehensive mapping of field keywords to profile values.
        """
        mapping = {
            # Personal Info
            'first[ -]?name': lambda: self.profile.get('first_name', ''),
            'last[ -]?name': lambda: self.profile.get('last_name', ''),
            'full[ -]?name': lambda: f"{self.profile.get('first_name', '')} {self.profile.get('last_name', '')}",
            'email': lambda: self.profile.get('email', ''),
            'phone': lambda: self.profile.get('phone', ''),
            'address': lambda: self.profile.get('address', {}).get('street', ''),
            'city': lambda: self.profile.get('address', {}).get('city', ''),
            'state': lambda: self.profile.get('address', {}).get('state', ''),
            'zip': lambda: self.profile.get('address', {}).get('zip_code', ''),
            'postal': lambda: self.profile.get('address', {}).get('zip_code', ''),
            'country': lambda: self.profile.get('address', {}).get('country', 'United States'),
            
            # Education
            'school': lambda: self._get_latest_education('institution'),
            'university': lambda: self._get_latest_education('institution'),
            'college': lambda: self._get_latest_education('institution'),
            'degree': lambda: self._get_latest_education('degree'),
            'major': lambda: self._get_latest_education('field_of_study'),
            'gpa': lambda: self._get_latest_education('gpa'),
            'graduation': lambda: self._get_latest_education('graduation_date'),
            
            # Employment
            'company': lambda: self._get_latest_job('company'),
            'employer': lambda: self._get_latest_job('company'),
            'job[ -]?title': lambda: self._get_latest_job('title'),
            'position': lambda: self._get_latest_job('title'),
            'start[ -]?date': lambda: self._get_latest_job('start_date'),
            'end[ -]?date': lambda: self._get_latest_job('end_date'),
            
            # Work Eligibility
            'authorized': lambda: 'Yes' if self.profile.get('work_authorization', False) else 'No',
            'eligible[ -]?to[ -]?work': lambda: 'Yes' if self.profile.get('work_authorization', False) else 'No',
            'sponsor': lambda: 'No' if self.profile.get('requires_sponsorship', False) else 'Yes',
            'visa': lambda: self.profile.get('visa_status', 'N/A'),
            
            # Skills and Qualifications
            'years[ -]?of[ -]?experience': lambda: self.profile.get('total_years_experience', ''),
            'programming': lambda: self._get_skills_by_category('programming'),
            'languages': lambda: self._get_skills_by_category('languages'),
            'tools': lambda: self._get_skills_by_category('tools'),
            'certifications': lambda: ', '.join(self.profile.get('certifications', [])),
            
            # Social Media
            'linkedin': lambda: self.profile.get('social_media', {}).get('linkedin', ''),
            'github': lambda: self.profile.get('social_media', {}).get('github', ''),
            'portfolio': lambda: self.profile.get('portfolio_url', ''),
            'website': lambda: self.profile.get('personal_website', '')
        }
        
        return mapping
    
    def _get_latest_education(self, field_name):
        """Get the specified field from the most recent education entry"""
        education = self.profile.get('education', [])
        if not education:
            return ''
            
        # Sort by end date to get most recent education
        sorted_edu = sorted(education, 
                           key=lambda x: datetime.strptime(x.get('end_date', '1900-01-01'), '%Y-%m-%d')
                           if x.get('end_date') else datetime.now(),
                           reverse=True)
                           
        return sorted_edu[0].get(field_name, '') if sorted_edu else ''
    
    def _get_latest_job(self, field_name):
        """Get the specified field from the most recent job"""
        experience = self.profile.get('work_experience', [])
        if not experience:
            return ''
            
        # Sort by end date to get most recent job
        sorted_jobs = sorted(experience,
                            key=lambda x: datetime.strptime(x.get('end_date', '1900-01-01'), '%Y-%m-%d')
                            if x.get('end_date') else datetime.now(),
                            reverse=True)
                            
        return sorted_jobs[0].get(field_name, '') if sorted_jobs else ''
    
    def _get_skills_by_category(self, category):
        """Get skills from a specific category as a comma-separated string"""
        skills = self.profile.get('skills', {}).get(category, [])
        return ', '.join(skills)
    
    def detect_and_fill_fields(self, driver):
        """
        Detect form fields on the current page and fill them with appropriate values.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            dict: Statistics on fields processed, filled, and skipped
        """
        stats = {
            'processed': 0,
            'filled': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Get all input elements, selects, and textareas
        input_elements = driver.find_elements(By.TAG_NAME, "input")
        select_elements = driver.find_elements(By.TAG_NAME, "select")
        textarea_elements = driver.find_elements(By.TAG_NAME, "textarea")
        
        # Process input elements
        stats = self._process_input_elements(input_elements, driver, stats)
        
        # Process select elements
        stats = self._process_select_elements(select_elements, driver, stats)
        
        # Process textarea elements
        stats = self._process_textarea_elements(textarea_elements, driver, stats)
        
        return stats
    
    def _process_input_elements(self, elements, driver, stats):
        """Process and fill input elements"""
        for element in elements:
            stats['processed'] += 1
            
            try:
                # Skip hidden or disabled elements
                if not element.is_displayed() or not element.is_enabled():
                    stats['skipped'] += 1
                    continue
                
                # Get element attributes
                element_id = element.get_attribute('id') or ''
                element_name = element.get_attribute('name') or ''
                element_type = element.get_attribute('type') or ''
                element_placeholder = element.get_attribute('placeholder') or ''
                element_label = self._find_label_for_element(element, driver) or ''
                element_class = element.get_attribute('class') or ''
                
                # Skip buttons, submit, and already filled elements
                if element_type in ['button', 'submit', 'reset', 'image']:
                    stats['skipped'] += 1
                    continue
                    
                # Skip file inputs (handled separately)
                if element_type == 'file':
                    stats['skipped'] += 1
                    continue
                
                # Get current value
                current_value = element.get_attribute('value')
                if current_value and len(current_value) > 0 and element_type != 'checkbox' and element_type != 'radio':
                    stats['skipped'] += 1
                    continue
                
                # Use all available information to identify the field
                field_identifiers = [
                    element_id.lower(),
                    element_name.lower(),
                    element_placeholder.lower(),
                    element_label.lower()
                ]
                
                # Handle checkboxes and radio buttons specially
                if element_type == 'checkbox' or element_type == 'radio':
                    if self._handle_checkbox_radio(element, field_identifiers):
                        stats['filled'] += 1
                    else:
                        stats['skipped'] += 1
                    continue
                
                # Handle regular text inputs
                value = self._find_matching_value(field_identifiers)
                if value:
                    element.clear()
                    element.send_keys(value)
                    stats['filled'] += 1
                    logger.info(f"Filled field: {' | '.join(filter(None, field_identifiers))} with: {value}")
                else:
                    stats['skipped'] += 1
                    
            except (StaleElementReferenceException, ElementNotInteractableException, NoSuchElementException) as e:
                logger.debug(f"Error processing input element: {str(e)}")
                stats['errors'] += 1
                continue
        
        return stats
    
    def _process_select_elements(self, elements, driver, stats):
        """Process and fill select elements"""
        for element in elements:
            stats['processed'] += 1
            
            try:
                # Skip hidden or disabled elements
                if not element.is_displayed() or not element.is_enabled():
                    stats['skipped'] += 1
                    continue
                
                # Get element attributes
                element_id = element.get_attribute('id') or ''
                element_name = element.get_attribute('name') or ''
                element_label = self._find_label_for_element(element, driver) or ''
                
                # Use all available information to identify the field
                field_identifiers = [
                    element_id.lower(),
                    element_name.lower(),
                    element_label.lower()
                ]
                
                # Get current selection
                select = Select(element)
                current_value = select.first_selected_option.text
                
                # Skip if already has a non-default selection
                if current_value and current_value.lower() not in ['select', 'choose', 'please select', '-- select --', '--select--']:
                    stats['skipped'] += 1
                    continue
                
                # Find the best matching value
                matched_value = self._find_matching_value(field_identifiers)
                if matched_value:
                    # Try to select the option with this text or value
                    self._select_best_option(select, matched_value)
                    stats['filled'] += 1
                    logger.info(f"Selected option for: {' | '.join(filter(None, field_identifiers))} with: {matched_value}")
                else:
                    stats['skipped'] += 1
                    
            except (StaleElementReferenceException, ElementNotInteractableException, NoSuchElementException) as e:
                logger.debug(f"Error processing select element: {str(e)}")
                stats['errors'] += 1
                continue
        
        return stats
    
    def _process_textarea_elements(self, elements, driver, stats):
        """Process and fill textarea elements"""
        for element in elements:
            stats['processed'] += 1
            
            try:
                # Skip hidden or disabled elements
                if not element.is_displayed() or not element.is_enabled():
                    stats['skipped'] += 1
                    continue
                
                # Get element attributes
                element_id = element.get_attribute('id') or ''
                element_name = element.get_attribute('name') or ''
                element_placeholder = element.get_attribute('placeholder') or ''
                element_label = self._find_label_for_element(element, driver) or ''
                
                # Use all available information to identify the field
                field_identifiers = [
                    element_id.lower(),
                    element_name.lower(),
                    element_placeholder.lower(),
                    element_label.lower()
                ]
                
                # Get current value
                current_value = element.get_attribute('value')
                if current_value and len(current_value) > 0:
                    stats['skipped'] += 1
                    continue
                
                # Find the best matching value
                matched_value = self._find_matching_value(field_identifiers)
                if matched_value:
                    element.clear()
                    element.send_keys(matched_value)
                    stats['filled'] += 1
                    logger.info(f"Filled textarea: {' | '.join(filter(None, field_identifiers))} with: {matched_value}")
                else:
                    stats['skipped'] += 1
                    
            except (StaleElementReferenceException, ElementNotInteractableException, NoSuchElementException) as e:
                logger.debug(f"Error processing textarea element: {str(e)}")
                stats['errors'] += 1
                continue
        
        return stats
    
    def _find_label_for_element(self, element, driver):
        """Find the associated label text for an element"""
        try:
            element_id = element.get_attribute('id')
            if element_id:
                label = driver.find_element(By.CSS_SELECTOR, f"label[for='{element_id}']")
                return label.text.strip()
        except NoSuchElementException:
            # Try to find a parent label
            try:
                parent_label = element.find_element(By.XPATH, "./ancestor::label")
                return parent_label.text.strip()
            except NoSuchElementException:
                pass
        
        return ''
    
    def _find_matching_value(self, field_identifiers):
        """Find a matching value for the field based on field identifiers"""
        for identifier in field_identifiers:
            if not identifier:
                continue
                
            for pattern, value_func in self.field_mapping.items():
                if re.search(pattern, identifier):
                    return value_func()
        
        return ''
    
    def _handle_checkbox_radio(self, element, field_identifiers):
        """Handle checkbox and radio button elements"""
        # Check if this is a yes/no type question
        for identifier in field_identifiers:
            if not identifier:
                continue
                
            # Common yes/no patterns in application forms
            yes_patterns = ['agree', 'accept', 'confirm', 'authorize', 'eligible', 'legally', 'permitted']
            no_patterns = ['decline', 'reject', 'disagree', 'not authorize', 'not eligible']
            
            # Default answer to common job application questions
            common_questions = {
                'authorized to work': lambda: self.profile.get('work_authorization', True),
                'eligible to work': lambda: self.profile.get('work_authorization', True),
                'require(?:s)? visa': lambda: self.profile.get('requires_sponsorship', False),
                'need(?:s)? sponsor': lambda: self.profile.get('requires_sponsorship', False),
                'felony': lambda: False,
                'criminal': lambda: False,
                'background check': lambda: True,
                'drug test': lambda: True,
                'willing to relocate': lambda: self.profile.get('willing_to_relocate', True),
                'willing to travel': lambda: self.profile.get('willing_to_travel', True),
                'remote': lambda: self.profile.get('prefers_remote', True),
                'disability': lambda: self.profile.get('has_disability', False),
                'veteran': lambda: self.profile.get('is_veteran', False),
                'terms and conditions': lambda: True,
                'privacy policy': lambda: True
            }
            
            # Check common questions first
            for question, answer_func in common_questions.items():
                if re.search(question, identifier):
                    should_check = answer_func()
                    
                    # Check element value attribute for 'yes' or 'no' indicators
                    element_value = element.get_attribute('value').lower() if element.get_attribute('value') else ''
                    
                    # Determine if this element should be checked
                    should_check_this_element = False
                    
                    if any(yes_val in element_value for yes_val in self.yes_values) and should_check:
                        should_check_this_element = True
                    elif any(no_val in element_value for no_val in self.no_values) and not should_check:
                        should_check_this_element = True
                    
                    # Handle element interaction
                    if should_check_this_element and not element.is_selected():
                        element.click()
                        return True
                    
                    return False
            
            # Check for positive patterns
            for pattern in yes_patterns:
                if pattern in identifier:
                    if not element.is_selected():
                        element.click()
                    return True
            
            # If we couldn't identify the type of checkbox/radio, we leave it as is
            return False
    
    def _select_best_option(self, select, value):
        """Select the best matching option from a select element"""
        options = select.options
        
        # Try exact match first
        try:
            select.select_by_visible_text(value)
            return
        except Exception:
            pass
        
        # Try partial text match
        for option in options:
            option_text = option.text.strip().lower()
            if value.lower() in option_text or option_text in value.lower():
                select.select_by_visible_text(option.text)
                return
                
        # Try value attribute match
        try:
            select.select_by_value(value)
            return
        except Exception:
            pass
        
        # If it's a state/province field, try to match state code
        state_codes = {
            'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
            'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
            'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
            'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
            'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
            'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
            'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
            'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
            'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
            'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
        }
        
        # Check if this is likely a state field and if the value is a state name
        if any(state_identifier in option.text.lower() for option in options for state_identifier in ['state', 'province']):
            if value in state_codes:
                # Try to select by state code
                try:
                    select.select_by_value(state_codes[value])
                    return
                except Exception:
                    # Try to select by visible text containing state code
                    for option in options:
                        if state_codes[value] in option.text:
                            select.select_by_visible_text(option.text)
                            return
        
        # As a fallback, select the first non-empty option if the field is required
        if len(options) > 1 and options[0].text.strip() in ['', 'Select', 'Choose', '-- Select --', '--Select--']:
            select.select_by_visible_text(options[1].text) 