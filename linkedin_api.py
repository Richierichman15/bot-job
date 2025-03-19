import http.client
import json
import logging
import os
import time
from dotenv import load_dotenv
from urllib.parse import quote

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinkedInAPI:
    """
    Client for the LinkedIn Data API from RapidAPI.
    Used to fetch company information and posts from LinkedIn.
    """
    
    def __init__(self):
        """Initialize the API client with credentials from environment variables."""
        load_dotenv()
        self.api_key = os.getenv("LINKEDIN_API_KEY", os.getenv("JSEARCH_API_KEY"))
        self.api_host = os.getenv("LINKEDIN_API_HOST", "linkedin-data-api.p.rapidapi.com")
        
        if not self.api_key:
            logger.warning("LinkedIn API key not found in environment variables")
    
    def get_company_posts(self, company_username, start=0, limit=10):
        """
        Get posts from a LinkedIn company page.
        
        Args:
            company_username (str): The LinkedIn username of the company
            start (int): The starting index for pagination
            limit (int): The maximum number of posts to retrieve
            
        Returns:
            dict: Company posts data
        """
        try:
            # Build the endpoint
            endpoint = f"/get-company-posts?username={quote(company_username)}&start={start}"
            
            # Add delay to avoid rate limiting
            api_delay = float(os.getenv("API_REQUEST_DELAY", "1.0"))
            time.sleep(api_delay)
            
            # Set up the connection
            conn = http.client.HTTPSConnection(self.api_host)
            
            # Set up the headers
            headers = {
                'x-rapidapi-key': self.api_key,
                'x-rapidapi-host': self.api_host
            }
            
            # Make the request
            logger.info(f"Fetching LinkedIn posts for company: {company_username}")
            conn.request("GET", endpoint, headers=headers)
            
            # Get the response
            res = conn.getresponse()
            
            # Read and parse the data
            data = res.read()
            posts_data = json.loads(data.decode("utf-8"))
            
            # Close the connection
            conn.close()
            
            logger.info(f"Retrieved {len(posts_data.get('data', []))} LinkedIn posts for {company_username}")
            return posts_data
            
        except Exception as e:
            logger.error(f"Error fetching LinkedIn company posts: {str(e)}")
            return {"data": []}
    
    def search_jobs_from_posts(self, companies, keywords=None):
        """
        Search for job-related posts from a list of companies.
        
        Args:
            companies (list): List of company LinkedIn usernames to search
            keywords (list): List of job-related keywords to look for
            
        Returns:
            list: Job-related posts formatted as job listings
        """
        if keywords is None:
            keywords = ["hiring", "job", "career", "position", "opportunity", "opening", "apply", "join our team"]
        
        job_posts = []
        
        for company in companies:
            try:
                # Get company posts
                company_data = self.get_company_posts(company)
                posts = company_data.get("data", [])
                
                # Filter for job-related posts
                for post in posts:
                    post_text = post.get("text", "").lower()
                    
                    # Check if the post mentions any job-related keywords
                    if any(keyword.lower() in post_text for keyword in keywords):
                        # Format as a job listing
                        job_post = self._format_post_as_job(post, company)
                        if job_post:
                            job_posts.append(job_post)
            
            except Exception as e:
                logger.error(f"Error processing LinkedIn posts for {company}: {str(e)}")
                continue
        
        logger.info(f"Found {len(job_posts)} job-related posts from LinkedIn companies")
        return job_posts
    
    def _format_post_as_job(self, post, company_username):
        """
        Format a LinkedIn post as a job listing.
        
        Args:
            post (dict): The LinkedIn post data
            company_username (str): The company's LinkedIn username
            
        Returns:
            dict: Formatted job listing or None if not job-related
        """
        try:
            # Generate a unique ID for the post
            post_id = post.get("postId", post.get("id", ""))
            if not post_id:
                return None
            
            job_id = f"linkedin_{post_id}"
            
            # Extract post text and try to identify job title
            post_text = post.get("text", "")
            title_candidates = [
                line for line in post_text.split("\n") 
                if any(keyword in line.lower() for keyword in ["hiring", "job", "position", "role", "opening"])
            ]
            
            # Default job title if we can't extract one
            job_title = "Job Opening"
            if title_candidates:
                job_title = title_candidates[0][:50]  # Limit title length
            
            # Extract company details
            company_name = post.get("companyName", company_username)
            company_logo = post.get("companyLogo", "")
            
            # Format as job listing
            job_listing = {
                "job_id": job_id,
                "job_title": job_title,
                "job_description": post_text,
                "employer_name": company_name,
                "employer_logo": company_logo,
                "job_apply_link": post.get("postUrl", ""),
                "job_city": "",  # LinkedIn posts may not include location
                "job_country": "",
                "job_posted_at_timestamp": post.get("postDate", ""),
                "job_min_salary": None,
                "job_max_salary": None,
                "job_salary_period": None,
                "job_salary_currency": None,
                "job_employment_type": "",
                "job_is_remote": None,
                "source": "linkedin_post"
            }
            
            return job_listing
            
        except Exception as e:
            logger.error(f"Error formatting LinkedIn post as job: {str(e)}")
            return None
    
    def get_company_details(self, company_username):
        """
        Get details about a LinkedIn company.
        
        Args:
            company_username (str): The LinkedIn username of the company
            
        Returns:
            dict: Company details
        """
        try:
            # Build the endpoint
            endpoint = f"/get-company-details?username={quote(company_username)}"
            
            # Set up the connection
            conn = http.client.HTTPSConnection(self.api_host)
            
            # Set up the headers
            headers = {
                'x-rapidapi-key': self.api_key,
                'x-rapidapi-host': self.api_host
            }
            
            # Make the request
            logger.info(f"Fetching LinkedIn details for company: {company_username}")
            conn.request("GET", endpoint, headers=headers)
            
            # Get the response
            res = conn.getresponse()
            
            # Read and parse the data
            data = res.read()
            company_data = json.loads(data.decode("utf-8"))
            
            # Close the connection
            conn.close()
            
            logger.info(f"Retrieved details for LinkedIn company: {company_username}")
            return company_data
            
        except Exception as e:
            logger.error(f"Error fetching LinkedIn company details: {str(e)}")
            return {}

# For testing the module directly
if __name__ == "__main__":
    linkedin_api = LinkedInAPI()
    
    # Test getting company posts
    company = "microsoft"
    posts = linkedin_api.get_company_posts(company)
    print(f"Found {len(posts.get('data', []))} posts for {company}")
    
    # Test searching for job-related posts
    job_posts = linkedin_api.search_jobs_from_posts(["microsoft", "google", "amazon"])
    print(f"Found {len(job_posts)} job-related posts")
    
    # Print sample of job posts
    for i, job in enumerate(job_posts[:3]):
        print(f"\nJob {i+1}: {job['job_title']}")
        print(f"Company: {job['employer_name']}")
        print(f"Apply: {job['job_apply_link']}")
        print(f"Description preview: {job['job_description'][:100]}...") 