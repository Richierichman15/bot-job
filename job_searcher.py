import os
import json
import urllib.parse
import requests
import time
from dotenv import load_dotenv
import logging
from datetime import datetime
from active_jobs_api import ActiveJobsAPI  # Import the Active Jobs DB API client
from linkedin_api import LinkedInAPI  # Import the LinkedIn API client
from ai_processor import AIJobProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("job_searcher")

load_dotenv()

class JobSearcher:
    def __init__(self):
        self.api_key = os.getenv("JSEARCH_API_KEY")
        self.api_host = os.getenv("JSEARCH_API_HOST")
        
        if not self.api_key or not self.api_host:
            raise ValueError("API credentials not found in .env file")
        
        self.base_url = f"https://{self.api_host}"
        self.headers = {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': self.api_host
        }
        
        # Get min salary for filtering
        self.min_salary = int(os.getenv("MIN_SALARY", "0"))
        
        # Initialize the API clients
        self.active_jobs_api = ActiveJobsAPI()
        self.linkedin_api = LinkedInAPI()
        
        # Check if we should use multiple APIs
        self.use_multiple_apis = os.getenv("USE_MULTIPLE_APIS", "true").lower() == "true"
        
        # Get LinkedIn companies to monitor (if any)
        linkedin_companies_str = os.getenv("LINKEDIN_COMPANIES", "")
        self.linkedin_companies = [c.strip() for c in linkedin_companies_str.split(",")] if linkedin_companies_str else []
        
        # Initialize AI processor
        self.ai_processor = AIJobProcessor()
        
        # API request delay to avoid rate limiting
        self.request_delay = float(os.getenv("API_REQUEST_DELAY", "1.5"))
    
    def search_jobs(self):
        """
        Search for jobs based on configured criteria
        
        Returns:
            list: List of processed job listings
        """
        all_jobs = []
        processed_jobs = []
        
        # Search for each job title in each location
        for title in self.job_titles:
            for location in self.job_locations:
                logger.info(f"Searching for {title} in {location}")
                
                try:
                    jobs = self._search_single_query(title, location)
                    if jobs:
                        all_jobs.extend(jobs)
                        logger.info(f"Found {len(jobs)} jobs for {title} in {location}")
                    
                    # Add delay between requests
                    time.sleep(self.request_delay)
                    
                except Exception as e:
                    logger.error(f"Error searching for {title} in {location}: {str(e)}")
        
        # Remove duplicates based on job ID
        unique_jobs = self._remove_duplicates(all_jobs)
        logger.info(f"Found {len(unique_jobs)} unique jobs after filtering")
        
        # Process each job with AI
        for job in unique_jobs:
            try:
                # Analyze and prepare application if salary meets minimum
                if self._meets_salary_requirements(job):
                    application = self.ai_processor.prepare_application(job)
                    if application['status'] == 'ready_to_apply':
                        processed_jobs.append(application)
                        logger.info(f"Prepared application for {job.get('job_title')} at {job.get('employer_name')}")
            except Exception as e:
                logger.error(f"Error processing job {job.get('job_id')}: {str(e)}")
        
        logger.info(f"Successfully processed {len(processed_jobs)} jobs")
        return processed_jobs
    
    def _search_single_query(self, query, location):
        """
        Perform a single job search query
        
        Args:
            query (str): Job title to search for
            location (str): Location to search in
            
        Returns:
            list: Job listings from the search
        """
        url = f"https://{self.api_host}/search"
        
        params = {
            "query": f"{query} in {location}",
            "page": "1",
            "num_pages": "1",
            "employment_types": ",".join(self.employment_types)
        }
        
        if self.remote_jobs_only:
            params["remote_jobs_only"] = "true"
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if response.status_code == 429:
                logger.warning("Rate limit exceeded. Waiting before next request.")
                time.sleep(self.request_delay * 2)  # Double delay on rate limit
            return []
    
    def _meets_salary_requirements(self, job):
        """
        Check if a job meets the minimum salary requirements
        
        Args:
            job (dict): Job listing to check
            
        Returns:
            bool: Whether the job meets requirements
        """
        min_salary = job.get('job_min_salary', 0) or 0
        max_salary = job.get('job_max_salary', 0) or 0
        salary_period = (job.get('job_salary_period', '') or '').lower()
        
        # Convert salary to hourly rate for comparison
        if salary_period == 'yearly':
            min_hourly = min_salary / (52 * 40)  # 52 weeks * 40 hours
            max_hourly = max_salary / (52 * 40)
        elif salary_period == 'monthly':
            min_hourly = min_salary / (4 * 40)   # 4 weeks * 40 hours
            max_hourly = max_salary / (4 * 40)
        elif salary_period == 'weekly':
            min_hourly = min_salary / 40         # 40 hours per week
            max_hourly = max_salary / 40
        elif salary_period == 'daily':
            min_hourly = min_salary / 8          # 8 hours per day
            max_hourly = max_salary / 8
        else:  # hourly or unspecified
            min_hourly = min_salary
            max_hourly = max_salary
        
        # If no salary info, assume it doesn't meet requirements
        if min_hourly == 0 and max_hourly == 0:
            return False
        
        # Check if either min or max salary meets requirements
        return min_hourly >= self.min_salary or max_hourly >= self.min_salary
    
    def _remove_duplicates(self, jobs):
        """
        Remove duplicate job listings based on job ID
        
        Args:
            jobs (list): List of job listings
            
        Returns:
            list: Deduplicated job listings
        """
        seen_ids = set()
        unique_jobs = []
        
        for job in jobs:
            job_id = job.get('job_id')
            if job_id and job_id not in seen_ids:
                seen_ids.add(job_id)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def get_job_details(self, job_id):
        """
        Get detailed information about a specific job
        
        Args:
            job_id (str): The job ID to retrieve details for
            
        Returns:
            dict: Job details dictionary
        """
        try:
            url = f"{self.base_url}/job-details?job_id={job_id}"
            logger.info(f"Getting details for job ID: {job_id}")
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") != "OK":
                logger.error(f"API returned non-OK status: {data.get('status')}")
                return {}
            
            return data.get("data", [{}])[0]
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting job details: {str(e)}")
            return {}

    def get_salary_estimate(self, job_title, location="remote"):
        """
        Get salary estimate for a job title in a location
        
        Args:
            job_title (str): The job title to estimate salary for
            location (str): The location to estimate salary in
            
        Returns:
            dict: Salary estimate information
        """
        try:
            # URL encode parameters
            params = {
                "job_title": job_title,
                "location": location,
                "location_type": "ANY"
            }
            encoded_params = urllib.parse.urlencode(params)
            
            url = f"{self.base_url}/estimated-salary?{encoded_params}"
            logger.info(f"Getting salary estimate for {job_title} in {location}")
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") != "OK":
                logger.error(f"API returned non-OK status: {data.get('status')}")
                return {}
            
            return data.get("data", [{}])[0]
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting salary estimate: {str(e)}")
            return {}

    def _apply_custom_filters(self, jobs, filter_it=False, location=None, priorities=None):
        """
        Apply custom filters to jobs based on preferences.
        
        Args:
            jobs (list): List of job dictionaries to filter
            filter_it (bool): Whether to filter for IT/software jobs
            location (str): Specific location to filter for (case insensitive)
            priorities (list): List of priority job types or keywords
            
        Returns:
            list: Filtered job dictionaries
        """
        filtered_jobs = []
        
        # Define IT and software-related keywords
        it_keywords = [
            "software", "developer", "engineer", "programming", "coder", "IT", 
            "information technology", "web", "frontend", "backend", "full stack",
            "python", "javascript", "java", "C#", ".NET", "node", "react", "angular",
            "cloud", "devops", "sysadmin", "database", "DBA", "data", "analytics",
            "machine learning", "AI", "artificial intelligence", "cybersecurity", 
            "security", "network", "support", "helpdesk", "QA", "quality assurance",
            "tester", "analyst", "architect", "administrator", "tech", "computer"
        ]
        
        # Apply filters to each job
        for job in jobs:
            # Get job details
            job_title = job.get('job_title', '').lower()
            job_description = job.get('job_description', '').lower()
            job_city = job.get('job_city', '').lower()
            job_country = job.get('job_country', '').lower()
            employer_name = job.get('employer_name', '').lower()
            
            # Combine all text fields for IT keyword matching
            all_job_text = f"{job_title} {job_description} {employer_name}"
            
            # Check if job passes IT filter (if enabled)
            passes_it_filter = True
            if filter_it:
                passes_it_filter = any(keyword.lower() in all_job_text for keyword in it_keywords)
            
            # Check if job passes location filter (if specified)
            passes_location_filter = True
            if location:
                location = location.lower()
                passes_location_filter = (
                    location in job_city or 
                    location in job_country or
                    # Also check description for location mentions
                    location in job_description
                )
            
            # Check if the job matches any priority keywords
            priority_match = False
            if priorities:
                priority_match = any(priority.lower() in all_job_text for priority in priorities)
            
            # Include job if it passes all enabled filters
            if passes_it_filter and passes_location_filter:
                # Mark priority matches for sorting later
                if priority_match:
                    job['priority_match'] = True
                filtered_jobs.append(job)
        
        # Sort filtered jobs by priority if any priorities were specified
        if priorities:
            filtered_jobs.sort(key=lambda j: j.get('priority_match', False), reverse=True)
        
        return filtered_jobs 