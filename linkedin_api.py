import http.client
import json
import logging
import os
import time
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from urllib.parse import quote

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinkedInAPI:
    """
    Client for the LinkedIn Data API.
    Used to search for job listings from LinkedIn companies.
    """
    
    def __init__(self):
        """Initialize the API client with credentials from environment variables."""
        load_dotenv()
        self.api_key = os.getenv("LINKEDIN_API_KEY", os.getenv("JSEARCH_API_KEY"))
        self.api_host = os.getenv("LINKEDIN_API_HOST", "linkedin-data-api.p.rapidapi.com")
        
        # Get list of companies to monitor
        companies_str = os.getenv("LINKEDIN_COMPANIES", "")
        self.companies = [c.strip() for c in companies_str.split(",")] if companies_str else []
        
        # Check if we should use mock data for testing
        self.use_mock_data = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
        
        if not self.api_key and not self.use_mock_data:
            logger.warning("LinkedIn API key not found in environment variables")
    
    def get_company_jobs(self, company_name):
        """
        Get job listings for a specific company.
        
        Args:
            company_name (str): The name of the company to get jobs for
            
        Returns:
            list: A list of job objects for the specified company
        """
        # Use mock data if enabled
        if self.use_mock_data:
            logger.info(f"[MOCK] Getting LinkedIn jobs for company: {company_name}")
            return self._get_mock_company_jobs(company_name)
        
        # Implement the actual API call here when needed
        logger.warning("LinkedIn API call not implemented yet. Mock data or other API sources will be used.")
        return []
    
    def search_all_companies(self):
        """
        Search for jobs across all configured companies.
        
        Returns:
            list: A list of job objects from all monitored companies
        """
        all_jobs = []
        
        for company in self.companies:
            logger.info(f"Searching LinkedIn jobs for company: {company}")
            company_jobs = self.get_company_jobs(company)
            all_jobs.extend(company_jobs)
            
            # Add delay to avoid rate limiting
            if not self.use_mock_data and len(self.companies) > 1:
                api_delay = float(os.getenv("API_REQUEST_DELAY", "1.0"))
                time.sleep(api_delay)
        
        logger.info(f"Found {len(all_jobs)} total jobs from LinkedIn companies")
        return all_jobs
    
    def _get_mock_company_jobs(self, company_name):
        """
        Generate mock job data for testing purposes.
        
        Args:
            company_name (str): The company to generate mock data for
            
        Returns:
            list: A list of mock job objects
        """
        # Determine how many jobs to generate (1-3)
        num_jobs = random.randint(1, 3)
        
        # Normalize the company name for matching
        company_lower = company_name.lower()
        
        # Job titles based on company
        if "google" in company_lower:
            job_titles = [
                "Software Engineer", 
                "Senior Software Engineer",
                "Product Manager", 
                "UX Designer", 
                "Data Scientist"
            ]
            locations = ["Mountain View, CA", "New York, NY", "Seattle, WA", "Remote"]
        elif "microsoft" in company_lower:
            job_titles = [
                "Software Engineer", 
                "Program Manager",
                "Cloud Solutions Architect", 
                "DevOps Engineer", 
                "AI Researcher"
            ]
            locations = ["Redmond, WA", "Boston, MA", "Austin, TX", "Remote"]
        elif "amazon" in company_lower:
            job_titles = [
                "Software Development Engineer", 
                "Technical Program Manager",
                "Solutions Architect", 
                "Systems Engineer", 
                "Data Engineer"
            ]
            locations = ["Seattle, WA", "Arlington, VA", "Nashville, TN", "Remote"]
        elif "apple" in company_lower:
            job_titles = [
                "Software Engineer", 
                "Machine Learning Engineer",
                "Hardware Engineer", 
                "iOS Developer", 
                "Product Designer"
            ]
            locations = ["Cupertino, CA", "Austin, TX", "New York, NY", "Remote"]
        elif "meta" in company_lower or "facebook" in company_lower:
            job_titles = [
                "Software Engineer", 
                "Research Scientist",
                "Product Manager", 
                "Data Engineer", 
                "Privacy Engineer"
            ]
            locations = ["Menlo Park, CA", "New York, NY", "Seattle, WA", "Remote"]
        else:
            job_titles = [
                "Software Engineer", 
                "Full Stack Developer",
                "DevOps Engineer", 
                "Product Manager", 
                "Data Scientist"
            ]
            locations = ["New York, NY", "San Francisco, CA", "Chicago, IL", "Remote"]
        
        # Mock jobs
        mock_jobs = []
        
        # Add one premium job opportunity if it's a top company
        top_companies = ["google", "microsoft", "amazon", "apple", "meta", "facebook"]
        if any(tc in company_lower for tc in top_companies) and random.random() < 0.7:  # 70% chance
            premium_job = self._create_premium_job(company_name, job_titles, locations)
            mock_jobs.append(premium_job)
            num_jobs -= 1  # Reduce regular jobs by 1
        
        # Add regular jobs
        for i in range(num_jobs):
            job = self._create_regular_job(company_name, job_titles, locations, i)
            mock_jobs.append(job)
        
        logger.info(f"[MOCK] Generated {len(mock_jobs)} mock LinkedIn jobs for {company_name}")
        return mock_jobs
    
    def _create_premium_job(self, company_name, job_titles, locations):
        """Create a premium job opportunity at a top company"""
        # Generate random dates (1-3 days ago)
        days_ago = random.randint(1, 3)
        post_date = datetime.now() - timedelta(days=days_ago)
        timestamp = int(post_date.timestamp())
        
        # Select job title and location
        job_title = random.choice(job_titles)
        location = random.choice(locations)
        
        # Premium jobs have higher salaries
        min_salary = random.randint(130000, 160000)
        max_salary = min_salary + random.randint(20000, 40000)
        
        # Create the premium job
        return {
            "job_id": f"linkedin-premium-{company_name.lower()}-{timestamp}",
            "job_title": f"Senior {job_title}",
            "job_description": f"""
            EXCEPTIONAL OPPORTUNITY at {company_name}!
            
            About This Role:
            We are looking for an exceptional Senior {job_title} to join our team and help shape the future of our technology. This is a high-visibility role working on products used by millions of people.
            
            What You'll Do:
            - Lead development of cutting-edge features and systems
            - Collaborate with product and design teams to define requirements
            - Architect solutions that scale to millions of users
            - Mentor junior team members and provide technical leadership
            
            Requirements:
            - 5+ years of professional experience in software development
            - Strong problem-solving skills and attention to detail
            - Experience with large-scale distributed systems
            - Excellent communication and collaboration skills
            
            Benefits:
            - Competitive salary and equity package
            - Comprehensive health, dental, and vision insurance
            - Flexible work arrangements
            - Generous vacation policy
            - Professional development budget
            - And much more!
            
            This is a rare opportunity to work on impactful projects at one of the world's leading technology companies.
            """,
            "employer_name": company_name,
            "job_apply_link": f"https://careers.{company_name.lower().replace(' ', '')}.com/apply/{timestamp}",
            "job_city": location.split(",")[0].strip(),
            "job_country": "US",
            "job_posted_at_timestamp": timestamp,
            "job_min_salary": min_salary,
            "job_max_salary": max_salary,
            "job_salary_period": "yearly",
            "job_salary_currency": "USD",
            "job_employment_type": "FULLTIME",
            "job_is_remote": "Remote" in location,
            "source": "linkedin",
            "is_premium": True
        }
    
    def _create_regular_job(self, company_name, job_titles, locations, index):
        """Create a regular job at the company"""
        # Generate random dates (3-7 days ago)
        days_ago = random.randint(3, 7)
        post_date = datetime.now() - timedelta(days=days_ago)
        timestamp = int(post_date.timestamp())
        
        # Select job title and location
        job_title = random.choice(job_titles)
        location = random.choice(locations)
        
        # Regular jobs have standard salaries
        min_salary = random.randint(90000, 120000)
        max_salary = min_salary + random.randint(10000, 30000)
        
        # Create the regular job
        return {
            "job_id": f"linkedin-{company_name.lower()}-{timestamp}-{index}",
            "job_title": job_title,
            "job_description": f"""
            {company_name} is seeking a {job_title} to join our team in {location}.
            
            Responsibilities:
            - Design and implement software solutions
            - Collaborate with cross-functional teams
            - Write clean, maintainable code
            - Participate in code reviews and testing
            
            Requirements:
            - 3+ years of professional experience
            - Strong programming skills
            - Bachelor's degree in Computer Science or related field
            - Good communication skills
            
            Benefits include competitive salary, health insurance, and flexible work arrangements.
            """,
            "employer_name": company_name,
            "job_apply_link": f"https://careers.{company_name.lower().replace(' ', '')}.com/apply/{timestamp}-{index}",
            "job_city": location.split(",")[0].strip(),
            "job_country": "US",
            "job_posted_at_timestamp": timestamp,
            "job_min_salary": min_salary,
            "job_max_salary": max_salary,
            "job_salary_period": "yearly",
            "job_salary_currency": "USD",
            "job_employment_type": "FULLTIME",
            "job_is_remote": "Remote" in location,
            "source": "linkedin"
        }

# For testing the module directly
if __name__ == "__main__":
    linkedin_api = LinkedInAPI()
    
    # Override mock mode for testing
    linkedin_api.use_mock_data = True
    
    # Test getting jobs for different companies
    companies_to_test = ["Google", "Microsoft", "Amazon", "Apple", "Meta"]
    
    for company in companies_to_test:
        jobs = linkedin_api.get_company_jobs(company)
        print(f"\n{company} Jobs ({len(jobs)}):")
        for job in jobs:
            print(f"- {job['job_title']} ({job['job_city']}) - ${job['job_min_salary']}-${job['job_max_salary']}")
            
    # Test getting all company jobs
    all_jobs = linkedin_api.search_all_companies()
    print(f"\nTotal Jobs: {len(all_jobs)}") 