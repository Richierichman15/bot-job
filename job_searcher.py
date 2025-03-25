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
from bright_data_scraper import BrightDataScraper
from html_parser import JobPageParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("job_searcher")

load_dotenv()

class JobSearcher:
    def __init__(self, config_file=None, use_mock_data=None, use_brightdata=None, bright_data_test_mode=None):
        """
        Initialize the JobSearcher with configuration settings
        
        Args:
            config_file (str): Path to the config file
            use_mock_data (bool): Whether to use mock data for testing
            use_brightdata (bool): Whether to use Bright Data for scraping
            bright_data_test_mode (bool): Whether to run Bright Data in test mode
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
        
        # Check if we should use mock data for testing (parameter overrides env var)
        self.use_mock_data = use_mock_data if use_mock_data is not None else os.getenv("USE_MOCK_DATA", "false").lower() == "true"
        
        # Check if we should use Bright Data scraping (parameter overrides env var)
        self.use_brightdata = use_brightdata if use_brightdata is not None else os.getenv("USE_BRIGHTDATA", "false").lower() == "true"
        
        self.api_key = os.getenv("JSEARCH_API_KEY")
        self.api_host = os.getenv("JSEARCH_API_HOST")
        
        if not self.use_mock_data and (not self.api_key or not self.api_host):
            logger.warning("API credentials not found in .env file, falling back to mock data")
            self.use_mock_data = True
        
        self.base_url = f"https://{self.api_host}" if self.api_host else ""
        self.headers = {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': self.api_host
        } if self.api_key and self.api_host else {}
        
        # Get job titles to search for (config overrides env vars)
        job_titles_str = os.getenv("JOB_TITLES", "software developer")
        self.job_titles = self.config.get("job_titles", []) or [title.strip() for title in job_titles_str.split(",")]
        
        # Get locations to search in (config overrides env vars)
        job_locations_str = os.getenv("JOB_LOCATIONS", "usa,remote")
        self.job_locations = self.config.get("locations", []) or [loc.strip() for loc in job_locations_str.split(",")]
        
        # Get employment types to filter by
        employment_types_str = os.getenv("JOB_EMPLOYMENT_TYPES", "FULLTIME,CONTRACTOR")
        self.employment_types = [type.strip() for type in employment_types_str.split(",")]
        
        # Check if we should search for remote jobs only
        self.remote_jobs_only = os.getenv("JOB_REMOTE", "false").lower() == "true"
        
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
        
        # Initialize Bright Data scraper if needed
        self.bright_data = None
        if self.use_brightdata:
            try:
                # Use the test_mode parameter if provided, otherwise use the env var
                test_mode = bright_data_test_mode if bright_data_test_mode is not None else os.getenv("BRIGHTDATA_TEST_MODE", "false").lower() == "true"
                self.bright_data = BrightDataScraper(test_mode=test_mode)
                logger.info(f"Initialized Bright Data scraper for job search (test mode: {test_mode})")
            except ValueError as e:
                logger.error(f"Failed to initialize Bright Data scraper: {str(e)}")
                logger.warning("Falling back to mock data")
                self.use_mock_data = True
    
    def search_jobs(self):
        """
        Search for jobs using the specified APIs or mock data
        
        Returns:
            list: Processed job listings
        """
        all_jobs = []
        
        # Get setting to use real scraping
        use_real_scraping = os.getenv("USE_REAL_SCRAPING", "false").lower() == "true"
        
        # If using mock data and not real scraping, return mock jobs
        if self.use_mock_data and not use_real_scraping:
            logger.info("Generating mock job data for testing")
            return self._get_mock_jobs()
        
        # Use Bright Data scraper if enabled (even in test mode)
        if self.use_brightdata and self.bright_data:
            logger.info("Using Bright Data to scrape job listings")
            all_jobs = self._search_with_brightdata()
        else:
            # Use existing API methods if Bright Data is not enabled
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
            logger.warning("Bright Data not enabled, falling back to mock data")
            return self._get_mock_jobs()
        
        # Process the jobs
        return self._process_jobs(all_jobs)
    
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
            "num_pages": "1"
        }
        
        # Add employment types if available
        if hasattr(self, 'employment_types') and self.employment_types:
            params["employment_types"] = ",".join(self.employment_types)
        
        if hasattr(self, 'remote_jobs_only') and self.remote_jobs_only:
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
            if hasattr(response, 'status_code') and response.status_code == 429:
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

    def _get_mock_jobs(self):
        """
        Generate mock job data for testing with various quality levels.
        Includes both regular jobs and a few exceptional opportunities.
        
        Returns:
            list: Sample job listings of varying quality
        """
        logger.info("Generating mock job data for testing")
        
        # Helper function to generate random timestamps within the last week
        def random_timestamp():
            import random
            # Random time between now and 7 days ago
            days_ago = random.randint(0, 7)
            hours_ago = random.randint(0, 23)
            return int(time.time() - (days_ago * 86400) - (hours_ago * 3600))
        
        # Create a variety of job listings - some great, some mediocre
        mock_jobs = [
            # GOLDEN OPPORTUNITY 1: High-paying remote position at a top company
            {
                "job_id": "golden-job-1",
                "job_title": "Senior Full Stack Engineer",
                "employer_name": "Tech Innovations Inc.",
                "job_city": "Remote",
                "job_country": "US",
                "job_min_salary": 140000,
                "job_max_salary": 180000,
                "job_salary_period": "yearly",
                "job_description": """
                EXCEPTIONAL OPPORTUNITY: Tech Innovations Inc. is seeking a Senior Full Stack Engineer to join our growing team!

                About Us:
                We're a fast-growing tech company focusing on AI-driven solutions that are changing how businesses operate. We've secured $50M in Series B funding and are expanding our engineering team.

                What You'll Do:
                - Build scalable, robust applications using modern technologies
                - Lead development of new product features from conception to deployment
                - Mentor junior engineers and foster technical excellence
                - Collaborate with cross-functional teams to define requirements

                Required Skills:
                - 4+ years experience with JavaScript/TypeScript, React, and Node.js
                - Strong understanding of database systems (SQL and NoSQL)
                - Experience with cloud platforms (AWS, Azure, or GCP)
                - Track record of leading complex technical projects

                Benefits:
                - Competitive salary ($140K-$180K)
                - 100% remote work with flexible hours
                - Comprehensive health benefits
                - 401(k) matching
                - 4 weeks paid vacation
                - Professional development budget
                - Home office stipend
                
                This is a rare opportunity to join a team that's making a real impact with cutting-edge technology. Apply now to grow your career with us!
                """,
                "job_apply_link": "https://example.com/apply/golden1",
                "job_employment_type": "FULLTIME",
                "job_is_remote": True,
                "job_posted_at_timestamp": random_timestamp(),
                "job_required_skills": [
                    "JavaScript", "TypeScript", "React", "Node.js", "AWS", 
                    "SQL", "NoSQL", "System Design", "Team Leadership", "CI/CD"
                ],
                "job_required_experience": {"minimum_years": 4, "maximum_years": 8},
                "job_benefits": [
                    "Health Insurance", "401(k) Matching", "Remote Work", 
                    "Flexible Hours", "Professional Development", "Home Office Stipend"
                ],
                "job_highlights": {
                    "Qualifications": [
                        "4+ years experience with JavaScript/TypeScript", 
                        "Experience with React and Node.js",
                        "Strong understanding of database systems",
                        "Experience with cloud platforms"
                    ],
                    "Responsibilities": [
                        "Build scalable applications", 
                        "Lead development of new product features",
                        "Mentor junior engineers",
                        "Collaborate with cross-functional teams"
                    ],
                    "Benefits": [
                        "Competitive salary", 
                        "100% remote work", 
                        "Comprehensive health benefits",
                        "4 weeks paid vacation"
                    ]
                }
            },
            
            # GOLDEN OPPORTUNITY 2: High-quality position in Oklahoma City
            {
                "job_id": "golden-job-2",
                "job_title": "Python Backend Developer",
                "employer_name": "DataWorks Solutions",
                "job_city": "Oklahoma City",
                "job_country": "US",
                "job_min_salary": 110000,
                "job_max_salary": 135000,
                "job_salary_period": "yearly",
                "job_description": """
                EXCELLENT OPPORTUNITY: Join DataWorks Solutions as a Python Backend Developer in our Oklahoma City office!

                About the Role:
                We're looking for a talented Python Developer to help build our next-generation data processing platform. This is a key position working on core systems that process millions of data points daily.

                What You'll Do:
                - Develop high-performance backend services using Python
                - Design and implement RESTful APIs and microservices
                - Work with large-scale databases and data processing pipelines
                - Participate in system architecture decisions

                Required Skills:
                - Strong Python programming skills
                - Experience with Django or Flask frameworks
                - Knowledge of SQL and database optimization
                - Understanding of RESTful API design principles
                - Comfortable with Git version control

                Benefits:
                - Competitive salary ($110K-$135K)
                - Modern downtown office with standing desks
                - Comprehensive benefits package with health, dental, and vision
                - Flexible work schedule with 2 days WFH option
                - Generous PTO policy
                - Professional growth opportunities
                
                This position offers an excellent opportunity to work on challenging technical problems with a growing company right here in Oklahoma City!
                """,
                "job_apply_link": "https://example.com/apply/golden2",
                "job_employment_type": "FULLTIME",
                "job_is_remote": False,
                "job_posted_at_timestamp": random_timestamp(),
                "job_required_skills": [
                    "Python", "Django", "Flask", "SQL", "REST APIs", 
                    "Microservices", "Git", "PostgreSQL", "Docker"
                ],
                "job_required_experience": {"minimum_years": 3, "maximum_years": 6},
                "job_benefits": [
                    "Health Insurance", "Dental Insurance", "Vision Insurance", 
                    "Flexible Schedule", "Professional Development", "Generous PTO"
                ],
                "job_highlights": {
                    "Qualifications": [
                        "Strong Python programming skills", 
                        "Experience with Django or Flask",
                        "Knowledge of SQL and database optimization",
                        "Understanding of RESTful API design"
                    ],
                    "Responsibilities": [
                        "Develop high-performance backend services", 
                        "Design and implement RESTful APIs",
                        "Work with large-scale databases",
                        "Participate in architecture decisions"
                    ],
                    "Benefits": [
                        "Competitive salary", 
                        "Modern downtown office", 
                        "Comprehensive benefits package",
                        "Flexible work schedule"
                    ]
                }
            },
            
            # Standard job 1: Mid-level developer position
            {
                "job_id": "standard-job-1",
                "job_title": "JavaScript Developer",
                "employer_name": "WebSoft Solutions",
                "job_city": "Remote",
                "job_country": "US",
                "job_min_salary": 85000,
                "job_max_salary": 105000,
                "job_salary_period": "yearly",
                "job_description": """
                WebSoft Solutions is seeking a JavaScript Developer to join our development team.

                Responsibilities:
                - Develop responsive web applications using JavaScript frameworks
                - Write clean, maintainable code
                - Troubleshoot and debug issues
                - Collaborate with the design team

                Requirements:
                - 2+ years experience with JavaScript
                - Experience with React or Angular
                - Understanding of RESTful APIs
                - Basic knowledge of HTML/CSS
                
                Benefits include health insurance, 401(k), and flexible work options.
                """,
                "job_apply_link": "https://example.com/apply/standard1",
                "job_employment_type": "FULLTIME",
                "job_is_remote": True,
                "job_posted_at_timestamp": random_timestamp(),
                "job_required_skills": [
                    "JavaScript", "React", "Angular", "HTML", "CSS", "RESTful APIs"
                ],
                "job_required_experience": {"minimum_years": 2, "maximum_years": 4}
            },
            
            # Standard job 2: Local position
            {
                "job_id": "standard-job-2",
                "job_title": "Junior Web Developer",
                "employer_name": "Digital Marketing Group",
                "job_city": "Oklahoma City",
                "job_country": "US",
                "job_min_salary": 60000,
                "job_max_salary": 75000,
                "job_salary_period": "yearly",
                "job_description": """
                Digital Marketing Group is looking for a Junior Web Developer to assist with client websites.

                Responsibilities:
                - Develop and maintain client websites
                - Implement designs in HTML/CSS
                - Update website content
                - Assist with WordPress customizations

                Requirements:
                - Knowledge of HTML, CSS, and JavaScript
                - Experience with WordPress
                - Basic understanding of PHP
                - Attention to detail
                """,
                "job_apply_link": "https://example.com/apply/standard2",
                "job_employment_type": "FULLTIME",
                "job_is_remote": False,
                "job_posted_at_timestamp": random_timestamp(),
                "job_required_skills": [
                    "HTML", "CSS", "JavaScript", "WordPress", "PHP"
                ],
                "job_required_experience": {"minimum_years": 0, "maximum_years": 2}
            },
            
            # Standard job 3: Contract position
            {
                "job_id": "standard-job-3",
                "job_title": "React Developer (Contract)",
                "employer_name": "TechStaff Inc.",
                "job_city": "Remote",
                "job_country": "US",
                "job_min_salary": 50,
                "job_max_salary": 70,
                "job_salary_period": "hourly",
                "job_description": """
                TechStaff Inc. is seeking a React Developer for a 6-month contract role.

                Responsibilities:
                - Build user interfaces using React
                - Integrate with backend APIs
                - Help maintain existing applications
                - Write unit tests

                Requirements:
                - Experience with React
                - Understanding of JavaScript, HTML, and CSS
                - Able to work independently
                - Available for full-time hours (40 hours/week)
                """,
                "job_apply_link": "https://example.com/apply/standard3",
                "job_employment_type": "CONTRACTOR",
                "job_is_remote": True,
                "job_posted_at_timestamp": random_timestamp(),
                "job_required_skills": [
                    "React", "JavaScript", "HTML", "CSS", "Jest"
                ],
                "job_required_experience": {"minimum_years": 1, "maximum_years": 3}
            },
            
            # Low-quality job 1: Suspicious high-demands low-pay
            {
                "job_id": "low-job-1",
                "job_title": "Full Stack Developer (Entry Level)",
                "employer_name": "Budget Applications LLC",
                "job_city": "Remote",
                "job_country": "US",
                "job_min_salary": 40000,
                "job_max_salary": 45000,
                "job_salary_period": "yearly",
                "job_description": """
                Budget Applications is hiring a Full Stack Developer with a can-do attitude!

                What we're looking for:
                - Proficiency in JavaScript, React, Node.js, Express, MongoDB
                - Experience with AWS, Docker, Kubernetes
                - Knowledge of Python, Java, and C#
                - Excellent communication skills
                - Ability to work under tight deadlines
                - Available for occasional weekend work
                - Willing to be on-call

                This is an entry-level position with great learning opportunities!
                """,
                "job_apply_link": "https://example.com/apply/low1",
                "job_employment_type": "FULLTIME",
                "job_is_remote": True,
                "job_posted_at_timestamp": random_timestamp(),
                "job_required_skills": [
                    "JavaScript", "React", "Node.js", "Express", "MongoDB", 
                    "AWS", "Docker", "Kubernetes", "Python", "Java", "C#"
                ],
                "job_required_experience": {"minimum_years": 0, "maximum_years": 1}
            },
            
            # Low-quality job 2: Vague description
            {
                "job_id": "low-job-2",
                "job_title": "Web Developer",
                "employer_name": "Generic IT Solutions",
                "job_city": "Oklahoma City",
                "job_country": "US",
                "job_min_salary": 0,
                "job_max_salary": 0,
                "job_salary_period": "",
                "job_description": """
                We are looking for a web developer to join our team. The ideal candidate will be responsible for coding and developing websites and web applications. Salary is competitive and based on experience.

                Required skills:
                - Programming knowledge
                - Web development experience
                - Good communication
                - Team player
                """,
                "job_apply_link": "https://example.com/apply/low2",
                "job_employment_type": "FULLTIME",
                "job_is_remote": False,
                "job_posted_at_timestamp": random_timestamp(),
                "job_required_skills": [
                    "Web Development"
                ],
                "job_required_experience": {"minimum_years": 1, "maximum_years": 3}
            },
            
            # Part-time job
            {
                "job_id": "part-time-job-1",
                "job_title": "Frontend Developer (Part-Time)",
                "employer_name": "Creative Studios",
                "job_city": "Remote",
                "job_country": "US",
                "job_min_salary": 30,
                "job_max_salary": 40,
                "job_salary_period": "hourly",
                "job_description": """
                Creative Studios is seeking a part-time Frontend Developer to assist with various design projects.

                Responsibilities:
                - Implement frontend designs using HTML, CSS, and JavaScript
                - Create responsive web pages
                - Optimize sites for performance and usability
                - 20 hours per week, flexible scheduling

                Requirements:
                - Strong HTML, CSS, and JavaScript skills
                - Knowledge of responsive design principles
                - Portfolio of previous work
                - Available at least 20 hours per week
                """,
                "job_apply_link": "https://example.com/apply/parttime1",
                "job_employment_type": "PARTTIME",
                "job_is_remote": True,
                "job_posted_at_timestamp": random_timestamp(),
                "job_required_skills": [
                    "HTML", "CSS", "JavaScript", "Responsive Design"
                ],
                "job_required_experience": {"minimum_years": 1, "maximum_years": 3}
            }
        ]
        
        return mock_jobs

    def _search_with_brightdata(self):
        """
        Search for jobs using Bright Data web scrapers
        
        Returns:
            list: Job listings
        """
        job_listings = []
        
        try:
            # Get search parameters from config
            job_titles = self.job_titles
            locations = self.job_locations
            
            # Log search details
            logger.info(f"Searching for jobs with Bright Data for {len(job_titles)} job titles in {len(locations)} locations")
            
            # Search on different platforms for each job title and location
            for job_title in job_titles:
                for location in locations:
                    # LinkedIn search
                    linkedin_jobs = self.bright_data.search_linkedin(job_title, location)
                    job_listings.extend(linkedin_jobs)
                    
                    # Indeed search
                    indeed_jobs = self.bright_data.search_indeed(job_title, location)
                    job_listings.extend(indeed_jobs)
                    
                    # Glassdoor search
                    glassdoor_jobs = self.bright_data.search_glassdoor(job_title, location)
                    job_listings.extend(glassdoor_jobs)
                    
                    # Wait to avoid rate limiting
                    if not self.bright_data.test_mode:
                        time.sleep(1)
                        
            # Process the job listings to filter out any duplicates
            unique_job_listings = self._remove_duplicates(job_listings)
            
            logger.info(f"Found {len(unique_job_listings)} unique job listings with Bright Data")
            return unique_job_listings
            
        except Exception as e:
            logger.error(f"Error searching jobs with Bright Data: {str(e)}")
            return []
            
    def _remove_duplicates(self, job_listings):
        """
        Remove duplicate job listings based on job title and employer
        
        Args:
            job_listings (list): List of job dictionaries
            
        Returns:
            list: Filtered list of unique jobs
        """
        unique_jobs = {}
        
        for job in job_listings:
            job_id = job.get('job_id')
            title = job.get('job_title', '').lower()
            employer = job.get('employer_name', '').lower()
            
            # Create a unique key
            if job_id:
                key = job_id
            else:
                key = f"{title}_{employer}"
                
            # Only add if not a duplicate
            if key not in unique_jobs:
                unique_jobs[key] = job
                
        return list(unique_jobs.values())

    def _process_jobs(self, jobs):
        """
        Process job listings to filter out irrelevant ones
        
        Args:
            jobs (list): Job listings to process
            
        Returns:
            list: Filtered job listings
        """
        # Filter out duplicate and irrelevant jobs
        processed_jobs = []
        
        for job in jobs:
            try:
                # Check if job meets our filtering criteria
                if self._matches_job_filters(job):
                    processed_jobs.append(job)
            except Exception as e:
                logger.error(f"Error processing job: {str(e)}")
        
        logger.info(f"Processed {len(processed_jobs)} jobs after filtering")
        return processed_jobs
    
    def _matches_job_filters(self, job):
        """
        Check if a job matches our filtering criteria
        
        Args:
            job (dict): Job to check
            
        Returns:
            bool: True if job matches criteria, False otherwise
        """
        # Skip jobs without required fields
        if not job.get('job_title') or not job.get('employer_name'):
            return False
        
        # Check if salary meets requirements (if available)
        if self.min_salary > 0 and job.get('job_min_salary'):
            if not self._meets_salary_requirements(job):
                return False
        
        # Check if job title matches what we're looking for
        title_match = False
        job_title = job.get('job_title', '').lower()
        
        for title in self.job_titles:
            if title.lower() in job_title:
                title_match = True
                break
        
        if not title_match:
            return False
        
        # Check for excluded companies
        excluded_companies = self.config.get('excluded_companies', [])
        employer_name = job.get('employer_name', '').lower()
        
        for company in excluded_companies:
            if company.lower() in employer_name:
                return False
        
        # Check for excluded terms in title
        excluded_titles = self.config.get('excluded_titles', [])
        
        for term in excluded_titles:
            if term.lower() in job_title:
                return False
        
        # Check for excluded terms in description
        excluded_terms = self.config.get('excluded_terms', [])
        job_description = job.get('job_description', '').lower()
        
        for term in excluded_terms:
            if term.lower() in job_description:
                return False
        
        # All filters passed
        return True 