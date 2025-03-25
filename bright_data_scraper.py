#!/usr/bin/env python3
import os
import json
import requests
import logging
import time
import random
import uuid
from dotenv import load_dotenv
from urllib.parse import quote_plus
from datetime import datetime

# Import JobPageParser for HTML parsing
from html_parser import JobPageParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("bright_data_scraper")

# Load environment variables
load_dotenv()

class BrightDataScraper:
    """
    A class to scrape job data using Bright Data's Web Unlocker API
    """
    
    def __init__(self, test_mode=False):
        """
        Initialize the BrightDataScraper with API credentials and settings
        
        Args:
            test_mode (bool): If True, don't make real API calls, return test data instead
        """
        self.api_key = os.getenv("BRIGHTDATA_API_KEY")
        self.zone = os.getenv("BRIGHTDATA_ZONE", "job_socket")
        self.base_url = "https://api.brightdata.com/request"
        self.test_mode = test_mode or os.getenv("BRIGHTDATA_TEST_MODE", "false").lower() == "true"
        
        # API call rate limiting
        self.max_calls_per_minute = int(os.getenv("BRIGHTDATA_MAX_CALLS_PER_MINUTE", "10"))
        self.call_history = []
        
        if not self.api_key and not self.test_mode:
            raise ValueError("BRIGHTDATA_API_KEY not found in environment variables")
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }
        
        # Get request delay to avoid rate limiting
        self.request_delay = float(os.getenv("API_REQUEST_DELAY", "1.0"))
        
        if self.test_mode:
            logger.info("BrightDataScraper initialized in TEST MODE - no real API calls will be made")
        else:
            logger.info(f"BrightDataScraper initialized with zone: {self.zone}")
    
    def _enforce_rate_limit(self):
        """
        Enforce rate limiting for API calls
        
        Returns:
            float: Time to wait in seconds before making the call (0 if no wait needed)
        """
        current_time = datetime.now()
        # Remove calls older than 1 minute from history
        self.call_history = [t for t in self.call_history if (current_time - t).total_seconds() < 60]
        
        # Check if we've made too many calls in the last minute
        if len(self.call_history) >= self.max_calls_per_minute:
            # Calculate the time to wait - until the oldest call leaves the window
            oldest_call = self.call_history[0]
            wait_time = 60 - (current_time - oldest_call).total_seconds()
            wait_time = max(0, wait_time)  # Ensure non-negative
            
            if wait_time > 0:
                logger.warning(f"Rate limit reached. Waiting {wait_time:.2f} seconds before making the next call.")
                return wait_time
        
        # No need to wait
        return 0
    
    def _make_request(self, url, params=None, format_type="json"):
        """
        Make a request to the Bright Data API
        
        Args:
            url (str): The target URL to scrape
            params (dict): Additional request parameters
            format_type (str): Response format (json, raw, etc.)
            
        Returns:
            dict or str: The response data
        """
        # Return fake data in test mode
        if self.test_mode:
            logger.info(f"TEST MODE: Would request URL: {url}")
            return self._get_test_response(url, format_type)
        
        try:
            # Enforce rate limiting
            wait_time = self._enforce_rate_limit()
            if wait_time > 0:
                time.sleep(wait_time)
            
            # Track this call
            self.call_history.append(datetime.now())
            
            # Prepare the request payload
            payload = {
                "zone": self.zone,
                "url": url,
                "format": format_type
            }
            
            # Add any additional parameters
            if params:
                payload.update(params)
            
            logger.info(f"Making request to Bright Data API for URL: {url}")
            response = requests.post(
                self.base_url, 
                headers=self.headers,
                json=payload
            )
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Add delay to avoid rate limiting
            time.sleep(self.request_delay)
            
            # Return the data based on format
            if format_type == "json":
                return response.json()
            else:
                return response.text
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to Bright Data API: {str(e)}")
            return None
    
    def _get_test_response(self, url, format_type):
        """
        Generate test response data instead of making real API calls
        
        Args:
            url (str): The URL that would have been requested
            format_type (str): Requested format type
            
        Returns:
            dict or str: Fake response data
        """
        if "welcome.txt" in url:
            # Test endpoint
            return "This is a test response from the BrightData API."
        
        elif "indeed.com" in url:
            if "viewjob" in url:
                # Job details page
                return "<html><body><h1>Software Developer</h1><div class='company'>Test Company</div><div class='location'>Remote</div><div id='jobDescriptionText'>This is a test job description. Skills needed: Python, JavaScript, React.</div></body></html>"
            else:
                # Search results page
                return "<html><body><div class='job_seen_beacon' data-jk='test123'><div class='jobTitle'><span>Software Developer</span></div><div class='companyName'>Test Company</div><div class='companyLocation'>Remote</div><div class='job-snippet'>Test job description</div><div class='date'>Posted 3 days ago</div></div></body></html>"
        
        elif "linkedin.com" in url:
            if "jobs/search" in url:
                # Search results page
                return "<html><body><div class='job-search-card' data-id='test456'><div class='job-title'>Software Engineer</div><div class='company-name'>LinkedIn Test Company</div><div class='job-location'>Remote</div><a class='job-search-card__link' href='/jobs/view/test456'>View Job</a></div></body></html>"
            else:
                # Job details page
                return "<html><body><h1 class='job-details-header__title'>Software Engineer</h1><div class='job-details-jobs-unified-top-card__company-name'>LinkedIn Test Company</div><div class='job-details-jobs-unified-top-card__bullet'>Remote</div><div class='job-details-jobs-unified-description__content'>This is a LinkedIn test job description. Skills needed: Python, JavaScript, React.</div></body></html>"
        
        # Default fake response
        if format_type == "json":
            return {"status": "ok", "data": {}}
        else:
            return "<html><body><p>Test HTML response</p></body></html>"
    
    def search_indeed_jobs(self, query, location, page=1, max_results=10):
        """
        Search for jobs on Indeed
        
        Args:
            query (str): Job title or keyword
            location (str): Job location
            page (int): Page number for results
            max_results (int): Maximum number of results to return
            
        Returns:
            list: List of job listings
        """
        # Format the Indeed URL
        encoded_query = quote_plus(query)
        encoded_location = quote_plus(location)
        url = f"https://www.indeed.com/jobs?q={encoded_query}&l={encoded_location}&start={10 * (page - 1)}"
        
        # Make the request
        logger.info(f"Searching Indeed for: {query} in {location} (page {page})")
        response = self._make_request(url)
        
        if not response:
            logger.error("Failed to get response from Bright Data API")
            return []
        
        # Parse the Indeed job listings from the response
        # This is a simplified version - would need to be adapted based on actual response structure
        return self._parse_indeed_jobs(response)
    
    def _parse_indeed_jobs(self, response_data):
        """
        Parse Indeed job listings from the scraped data
        
        Args:
            response_data (dict): The raw response data
            
        Returns:
            list: Parsed job listings
        """
        try:
            # This would need to be customized based on the actual HTML structure
            # For now, return a mock empty list
            jobs = []
            
            # Extract job details from response_data using DOM parsing
            # Example (pseudocode):
            # job_cards = response_data.select('.jobCard')
            # for card in job_cards:
            #     job = {
            #         'job_id': card.get('data-jk'),
            #         'job_title': card.select_one('.jobTitle').text,
            #         'employer_name': card.select_one('.companyName').text,
            #         'job_location': card.select_one('.companyLocation').text,
            #         'job_description': card.select_one('.job-snippet').text,
            #         'job_apply_link': f"https://www.indeed.com/viewjob?jk={card.get('data-jk')}",
            #         'date_posted': card.select_one('.date').text
            #     }
            #     jobs.append(job)
            
            logger.info(f"Parsed {len(jobs)} jobs from Indeed")
            return jobs
            
        except Exception as e:
            logger.error(f"Error parsing Indeed jobs: {str(e)}")
            return []
    
    def search_linkedin_jobs(self, query, location, page=1):
        """
        Search for jobs on LinkedIn
        
        Args:
            query (str): Job title or keyword
            location (str): Job location
            page (int): Page number for results
            
        Returns:
            list: List of job listings
        """
        # Format the LinkedIn URL
        encoded_query = quote_plus(query)
        encoded_location = quote_plus(location)
        url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_query}&location={encoded_location}&start={25 * (page - 1)}"
        
        # Make the request
        logger.info(f"Searching LinkedIn for: {query} in {location} (page {page})")
        response = self._make_request(url)
        
        if not response:
            logger.error("Failed to get response from Bright Data API")
            return []
        
        # Parse the LinkedIn job listings from the response
        return self._parse_linkedin_jobs(response)
    
    def _parse_linkedin_jobs(self, response_data):
        """
        Parse LinkedIn job listings from the scraped data
        
        Args:
            response_data (dict): The raw response data
            
        Returns:
            list: Parsed job listings
        """
        try:
            # This would need to be customized based on the actual HTML structure
            # For now, return a mock empty list
            jobs = []
            
            # Extract job details from response_data using DOM parsing
            # Example (pseudocode):
            # job_cards = response_data.select('.job-card-container')
            # for card in job_cards:
            #     job = {
            #         'job_id': card.get('data-job-id'),
            #         'job_title': card.select_one('.job-title').text,
            #         'employer_name': card.select_one('.company-name').text,
            #         'job_location': card.select_one('.job-location').text,
            #         'job_description': card.select_one('.job-description').text,
            #         'job_apply_link': card.select_one('.apply-button').get('href'),
            #         'date_posted': card.select_one('.job-date').text
            #     }
            #     jobs.append(job)
            
            logger.info(f"Parsed {len(jobs)} jobs from LinkedIn")
            return jobs
            
        except Exception as e:
            logger.error(f"Error parsing LinkedIn jobs: {str(e)}")
            return []
    
    def get_job_details(self, job_url):
        """
        Get detailed job information from a job posting URL
        
        Args:
            job_url (str): URL of the job posting
            
        Returns:
            dict: Job details
        """
        # Make the request
        logger.info(f"Getting job details from URL: {job_url}")
        response = self._make_request(job_url)
        
        if not response:
            logger.error("Failed to get job details")
            return {}
        
        # Parse job details based on the URL
        if "indeed.com" in job_url:
            return self._parse_indeed_job_details(response)
        elif "linkedin.com" in job_url:
            return self._parse_linkedin_job_details(response)
        elif "glassdoor.com" in job_url:
            return self._parse_glassdoor_job_details(response)
        else:
            logger.warning(f"Unsupported job site: {job_url}")
            return {}
            
    def search_glassdoor(self, search_query, location, search_type="jobs", num_pages=1):
        """
        Search for jobs on Glassdoor
        
        Args:
            search_query (str): Job search query
            location (str): Location for job search
            search_type (str): Type of search (jobs, companies, etc.)
            num_pages (int): Number of pages to scrape
            
        Returns:
            list: Job listings from glassdoor
        """
        if self.test_mode:
            logger.info(f"Test mode: Simulating Glassdoor search for '{search_query}' in '{location}'")
            # Generate test data that mimics the structure of Glassdoor listings
            return self._generate_glassdoor_test_data(search_query, location)
        
        url_encoded_query = quote_plus(search_query)
        url_encoded_location = quote_plus(location)
        target_url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={url_encoded_query}&locT=C&locId=1147401&locKeyword={url_encoded_location}"
        
        params = {
            "url": target_url,
            "parse": False,
            "country": "us",
            "wait_for": ".react-job-listing"
        }
        
        try:
            response = self._make_api_call("glassdoor_search", params)
            html_content = response.get('body', '')
            
            # Parse the listings using the HTML parser
            all_jobs = JobPageParser.parse_glassdoor_listings(html_content)
            
            # Get job details for the first few listings
            detailed_jobs = []
            max_details = min(5, len(all_jobs))  # Limit to 5 detailed pages to avoid excessive API calls
            
            for i in range(max_details):
                job = all_jobs[i]
                job_url = job.get('job_apply_link')
                
                if job_url:
                    job_details = self.get_glassdoor_job_details(job_url, job)
                    detailed_jobs.append(job_details)
                else:
                    detailed_jobs.append(job)
            
            # Add the remaining jobs without details
            if max_details < len(all_jobs):
                detailed_jobs.extend(all_jobs[max_details:])
            
            logger.info(f"Retrieved {len(detailed_jobs)} Glassdoor job listings for '{search_query}' in '{location}'")
            return detailed_jobs
            
        except Exception as e:
            logger.error(f"Error in Glassdoor search: {str(e)}")
            return []
    
    def get_glassdoor_job_details(self, job_url, base_job=None):
        """
        Get detailed job information from a Glassdoor job page
        
        Args:
            job_url (str): URL of the job posting
            base_job (dict): Basic job information to augment
            
        Returns:
            dict: Complete job details
        """
        if self.test_mode:
            logger.info(f"Test mode: Simulating Glassdoor job details fetch for URL: {job_url}")
            
            # Start with the base job or create a new one
            job = dict(base_job) if base_job else {
                'job_title': 'Software Engineer (Test)',
                'employer_name': 'Test Company',
                'job_location': 'San Francisco, CA',
                'job_apply_link': job_url,
                'job_source': 'glassdoor'
            }
            
            # Add mock description and skills
            job['job_description'] = f"This is a mock job description for a {job['job_title']} position at {job['employer_name']}. " \
                               f"The ideal candidate will have experience with Python, JavaScript, and cloud platforms."
            job['job_required_skills'] = ['Python', 'JavaScript', 'AWS', 'Git']
            
            return job
        
        params = {
            "url": job_url,
            "parse": False,
            "country": "us",
            "wait_for": ".jobDescriptionContent"
        }
        
        try:
            response = self._make_api_call("glassdoor_job_details", params)
            html_content = response.get('body', '')
            
            # Parse the job details 
            job_details = JobPageParser.parse_glassdoor_job_details(html_content, base_job)
            return job_details
            
        except Exception as e:
            logger.error(f"Error in Glassdoor job details fetch: {str(e)}")
            return base_job or {}
            
    def _generate_glassdoor_test_data(self, search_query, location):
        """Generate mock data for Glassdoor in test mode"""
        jobs = []
        for i in range(1, 11):
            job = {
                'job_id': f"glassdoor-{i}",
                'job_title': f"{search_query.title()} Specialist {i}",
                'employer_name': f"Glassdoor Test Company {i}",
                'job_location': location,
                'job_description': f"This is a test job for {search_query} in {location}. " \
                                 f"The ideal candidate will have excellent skills and experience.",
                'job_min_salary': random.randint(70, 90) * 1000,
                'job_max_salary': random.randint(100, 150) * 1000,
                'job_salary_period': 'yearly',
                'job_apply_link': f"https://www.glassdoor.com/job-listing/test-{i}",
                'date_posted': f"{random.randint(1, 30)} days ago",
                'job_source': 'glassdoor',
                'job_required_skills': ['Python', 'JavaScript', 'AWS', 'Communication']
            }
            jobs.append(job)
        return jobs
    
    def _parse_glassdoor_job_details(self, response_data):
        """
        Parse detailed job information from a Glassdoor job page
        
        Args:
            response_data (dict): The raw response data
            
        Returns:
            dict: Job details
        """
        try:
            # This would need to be customized based on actual HTML structure
            job = {}
            
            # TODO: Implement actual parsing logic once we know the structure
            
            return job
            
        except Exception as e:
            logger.error(f"Error parsing Glassdoor job details: {str(e)}")
            return {}
    
    def submit_job_application(self, application_url, resume_path, cover_letter_path=None, answers=None):
        """
        Submit a job application through the website
        
        Args:
            application_url (str): URL to submit the application
            resume_path (str): Path to the resume file
            cover_letter_path (str): Path to the cover letter file
            answers (dict): Answers to application questions
            
        Returns:
            bool: True if successful, False otherwise
        """
        # This would need significant customization per site
        # and likely additional Bright Data capabilities
        
        logger.warning("Job application submission requires site-specific implementation")
        
        # Mock implementation
        return False

    def _make_api_call(self, call_type, params=None):
        """
        Make an API call to Bright Data with standardized error handling
        
        Args:
            call_type (str): Type of API call for logging
            params (dict): Parameters for the API call
            
        Returns:
            dict: API response 
        """
        if self.test_mode:
            logger.info(f"TEST MODE: Would make {call_type} API call")
            
            # Return a mock response with HTML body
            return {
                "status": "success",
                "body": self._get_test_response(params.get("url", ""), "raw") if params and "url" in params else ""
            }
            
        try:
            # Use the _make_request method to make the actual call
            if not params:
                logger.error(f"No parameters provided for {call_type} API call")
                return {"status": "error", "body": ""}
                
            if "url" not in params:
                logger.error(f"No URL provided for {call_type} API call")
                return {"status": "error", "body": ""}
                
            url = params.pop("url")
            response = self._make_request(url, params, "raw")
            
            if not response:
                return {"status": "error", "body": ""}
                
            return {"status": "success", "body": response}
            
        except Exception as e:
            logger.error(f"Error in {call_type} API call: {str(e)}")
            return {"status": "error", "body": ""}

    def search_linkedin(self, query, location, page=1):
        """
        Search for jobs on LinkedIn
        
        Args:
            query (str): Job title or keyword
            location (str): Job location
            page (int): Page number for results
            
        Returns:
            list: List of job listings
        """
        # Just redirect to the existing method for now
        return self.search_linkedin_jobs(query, location, page)
    
    def search_indeed(self, query, location, page=1, max_results=10):
        """
        Search for jobs on Indeed
        
        Args:
            query (str): Job title or keyword
            location (str): Job location
            page (int): Page number for results
            max_results (int): Maximum number of results to return
            
        Returns:
            list: List of job listings
        """
        # Just redirect to the existing method for now
        return self.search_indeed_jobs(query, location, page, max_results)

# For testing
if __name__ == "__main__":
    try:
        scraper = BrightDataScraper()
        
        # Test Indeed scraping
        indeed_jobs = scraper.search_indeed("python developer", "remote", 1)
        print(f"Found {len(indeed_jobs)} jobs on Indeed")
        
        # Test LinkedIn scraping
        linkedin_jobs = scraper.search_linkedin("software engineer", "new york", 1)
        print(f"Found {len(linkedin_jobs)} jobs on LinkedIn")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}") 