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
    
    def search_jobs(self, query=None, location=None, remote=True, page=1, num_pages=1, employment_types=None):
        """
        Search for jobs using multiple APIs. Handles multiple job titles and locations.
        
        Args:
            query (str): Job title or keyword to search for (can be comma-separated)
            location (str): Location to search in (can be comma-separated)
            remote (bool): Whether to include remote jobs
            page (int): Page number to retrieve
            num_pages (int): Number of pages to retrieve
            employment_types (list): List of employment types to filter by
            
        Returns:
            list: List of job dictionaries
        """
        all_jobs = []
        
        # Get job titles from env if not provided
        if not query:
            query = os.getenv("JOB_TITLES", os.getenv("JOB_TITLE", "software developer"))
        
        # Get locations from env if not provided
        if not location:
            location = os.getenv("JOB_LOCATIONS", os.getenv("JOB_LOCATION", "usa"))
        
        # Split job titles and locations
        job_titles = [title.strip() for title in query.split(',')]
        locations = [loc.strip() for loc in location.split(',')]
        
        logger.info(f"Searching for {len(job_titles)} job titles in {len(locations)} locations")
        
        # Make a search for each job title and location combination
        for title in job_titles:
            for loc in locations:
                # Search using JSearch API
                jsearch_jobs = self._search_single_query(title, loc, remote, page, num_pages)
                all_jobs.extend(jsearch_jobs)
                
                # If multiple APIs are enabled, also search with other APIs
                if self.use_multiple_apis:
                    try:
                        # Search with Active Jobs API
                        active_jobs = self.active_jobs_api.search_jobs(title, loc)
                        logger.info(f"Found {len(active_jobs)} additional jobs from Active Jobs API for {title} in {loc}")
                        all_jobs.extend(active_jobs)
                    except Exception as e:
                        logger.error(f"Error searching Active Jobs API: {str(e)}")
                        
                    # If LinkedIn companies are specified, search for job posts
                    if self.linkedin_companies:
                        try:
                            # Keywords to look for in LinkedIn posts should include the job title
                            keywords = ["hiring", "job", "career", "position", "opportunity", "opening", "apply", "join our team"]
                            keywords.extend([kw for kw in title.split() if len(kw) > 3])  # Add job title keywords
                            
                            linkedin_jobs = self.linkedin_api.search_jobs_from_posts(self.linkedin_companies, keywords)
                            logger.info(f"Found {len(linkedin_jobs)} additional jobs from LinkedIn company posts")
                            all_jobs.extend(linkedin_jobs)
                        except Exception as e:
                            logger.error(f"Error searching LinkedIn for jobs: {str(e)}")
        
        # Filter jobs by salary if min_salary is set
        if self.min_salary > 0:
            filtered_jobs = []
            for job in all_jobs:
                # Get salary data and handle None values
                min_salary = job.get('job_min_salary', 0)
                max_salary = job.get('job_max_salary', 0)
                salary_period = job.get('job_salary_period', '')
                salary_currency = job.get('job_salary_currency', 'USD')
                
                # Convert None values to 0
                if min_salary is None:
                    min_salary = 0
                if max_salary is None:
                    max_salary = 0
                
                # Handle None for salary_period
                if salary_period is None:
                    salary_period = ''
                else:
                    salary_period = salary_period.lower()
                
                # Default to annual if period is not specified
                if not salary_period:
                    salary_period = 'yearly'
                
                # For hourly rates, use the specified minimum directly
                # For annual salary, convert to hourly equivalent assuming 2000 hours/year
                meets_min_requirement = False
                
                if 'hour' in salary_period:
                    meets_min_requirement = min_salary >= self.min_salary or max_salary >= self.min_salary
                    logger.debug(f"Hourly salary: ${min_salary}-${max_salary} (min req: ${self.min_salary}/hr)")
                else:
                    # Divide annual salary by 2000 to get hourly equivalent
                    hourly_min = min_salary / 2000 if min_salary > 0 else 0
                    hourly_max = max_salary / 2000 if max_salary > 0 else 0
                    
                    # If either the min or max hourly equivalent is >= min requirement
                    meets_min_requirement = hourly_min >= self.min_salary or hourly_max >= self.min_salary
                    
                    # Also include if annual salary is very high (over $40,000)
                    if min_salary >= 40000 or max_salary >= 40000:
                        meets_min_requirement = True
                        
                    logger.debug(f"Annual salary: ${min_salary}-${max_salary} (hourly equiv: ${hourly_min:.2f}-${hourly_max:.2f}, min req: ${self.min_salary}/hr)")
                
                # Add jobs that meet salary requirements or jobs with missing salary data
                if meets_min_requirement or (min_salary == 0 and max_salary == 0):
                    filtered_jobs.append(job)
                
            logger.info(f"Filtered from {len(all_jobs)} to {len(filtered_jobs)} jobs based on minimum salary of ${self.min_salary}")
            all_jobs = filtered_jobs
        
        # Apply custom filters based on preferences
        filter_it_jobs = os.getenv("FILTER_IT_JOBS", "false").lower() == "true"
        filter_location = os.getenv("FILTER_LOCATION", "")
        filter_priorities = json.loads(os.getenv("FILTER_PRIORITIES", "[]"))
        
        # Apply custom filtering if enabled
        if filter_it_jobs or filter_location:
            filtered_jobs = self._apply_custom_filters(all_jobs, 
                                                      filter_it=filter_it_jobs,
                                                      location=filter_location,
                                                      priorities=filter_priorities)
            logger.info(f"Applied custom filters: IT jobs={filter_it_jobs}, Location={filter_location}")
            logger.info(f"Filtered from {len(all_jobs)} to {len(filtered_jobs)} jobs based on custom criteria")
            all_jobs = filtered_jobs
        
        # Remove duplicates based on job_id
        unique_jobs = {}
        for job in all_jobs:
            job_id = job.get('job_id')
            if job_id and job_id not in unique_jobs:
                unique_jobs[job_id] = job
        
        result_jobs = list(unique_jobs.values())
        logger.info(f"Found {len(result_jobs)} unique job listings across all searches")
        
        return result_jobs
    
    def _search_single_query(self, query, location, remote=True, page=1, num_pages=1):
        """
        Search for jobs with a single query and location
        
        Args:
            query (str): Job title or keyword to search for
            location (str): Location to search in
            remote (bool): Whether to include remote jobs
            page (int): Page number to retrieve
            num_pages (int): Number of pages to retrieve
            
        Returns:
            list: List of job dictionaries
        """
        # Simplify query to just use basic parameters that we know work
        query_str = f"{query} in {location}"
        logger.info(f"Search query: {query_str}")
        
        # Basic parameters that are known to work
        url = f"{self.base_url}/search?query={urllib.parse.quote(query_str)}&page={page}&num_pages={num_pages}"
        
        # Only add remote_jobs_only if it's true (to minimize parameters)
        if remote:
            url += "&remote_jobs_only=true"
            
        try:
            # Add delay to avoid rate limiting (0.5 to 2 seconds)
            api_delay = float(os.getenv("API_REQUEST_DELAY", "1.0"))
            time.sleep(api_delay)
            
            # Make API request
            logger.info(f"Making request to: {url}")
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") != "OK":
                logger.error(f"API returned non-OK status: {data.get('status')}")
                return []
            
            # Extract job data
            jobs = data.get("data", [])
            logger.info(f"Found {len(jobs)} job listings for {query} in {location}")
            
            # Add timestamp for when the job was found
            for job in jobs:
                job["found_timestamp"] = datetime.now().isoformat()
            
            return jobs
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching for jobs: {str(e)}")
            return []
    
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