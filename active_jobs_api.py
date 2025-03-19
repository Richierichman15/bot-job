import http.client
import json
import logging
import os
from urllib.parse import quote
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActiveJobsAPI:
    """
    Client for the Active Jobs DB API from RapidAPI.
    Used to search for job listings from active applicant tracking systems.
    """
    
    def __init__(self):
        """Initialize the API client with credentials from environment variables."""
        load_dotenv()
        self.api_key = os.getenv("ACTIVEJOBS_API_KEY", os.getenv("JSEARCH_API_KEY"))
        self.api_host = os.getenv("ACTIVEJOBS_API_HOST", "active-jobs-db.p.rapidapi.com")
        
        if not self.api_key:
            logger.warning("Active Jobs API key not found in environment variables")
        
    def search_jobs(self, job_title, location, page=1, limit=20):
        """
        Search for jobs using the Active Jobs DB API.
        
        Args:
            job_title (str): The job title to search for
            location (str): The location to search in
            page (int): The page number for pagination
            limit (int): The number of results per page
            
        Returns:
            list: A list of job objects matching the search criteria
        """
        try:
            # URL encode the job title and location
            encoded_title = quote(f'"{job_title}"')
            encoded_location = quote(f'"{location}"')
            
            # Build the endpoint
            endpoint = f"/active-ats-1h?title_filter={encoded_title}&location_filter={encoded_location}"
            
            # Set up the connection
            conn = http.client.HTTPSConnection(self.api_host)
            
            # Set up the headers
            headers = {
                'x-rapidapi-key': self.api_key,
                'x-rapidapi-host': self.api_host
            }
            
            # Make the request
            logger.info(f"Searching Active Jobs DB for {job_title} in {location}")
            conn.request("GET", endpoint, headers=headers)
            
            # Get the response
            res = conn.getresponse()
            
            # Read and parse the data
            data = res.read()
            jobs_data = json.loads(data.decode("utf-8"))
            
            # Format the job data to match the structure used in the rest of the application
            formatted_jobs = self._format_jobs(jobs_data, job_title, location)
            
            # Close the connection
            conn.close()
            
            logger.info(f"Found {len(formatted_jobs)} job listings from Active Jobs DB for {job_title} in {location}")
            return formatted_jobs
            
        except Exception as e:
            logger.error(f"Error searching Active Jobs DB: {str(e)}")
            return []
    
    def _format_jobs(self, jobs_data, job_title, location):
        """
        Format the job data from Active Jobs DB to match the structure used in the rest of the application.
        
        Args:
            jobs_data (dict): The raw job data from the API
            job_title (str): The job title that was searched for
            location (str): The location that was searched for
            
        Returns:
            list: A list of formatted job objects
        """
        formatted_jobs = []
        
        # Check if we have valid jobs data
        if not jobs_data or not isinstance(jobs_data, list):
            logger.warning("No valid job data returned from Active Jobs DB API")
            return formatted_jobs
        
        # Format each job
        for job in jobs_data:
            try:
                # Extract relevant fields and map to our standard format
                formatted_job = {
                    "job_id": job.get("id", ""),
                    "job_title": job.get("title", job_title),
                    "job_description": job.get("description", ""),
                    "employer_name": job.get("company", ""),
                    "employer_logo": job.get("company_logo", ""),
                    "job_apply_link": job.get("url", ""),
                    "job_city": job.get("location", "").split(",")[0].strip() if job.get("location") else "",
                    "job_country": location,
                    "job_posted_at_timestamp": job.get("post_time", ""),
                    "job_min_salary": job.get("min_salary", None),
                    "job_max_salary": job.get("max_salary", None),
                    "job_salary_period": job.get("salary_period", "yearly"),
                    "job_salary_currency": job.get("salary_currency", "USD"),
                    "job_employment_type": job.get("employment_type", ""),
                    "job_is_remote": job.get("is_remote", False),
                    "source": "active_jobs_db"
                }
                
                formatted_jobs.append(formatted_job)
            except Exception as e:
                logger.error(f"Error formatting job from Active Jobs DB: {str(e)}")
                continue
        
        return formatted_jobs

# For testing the module directly
if __name__ == "__main__":
    active_jobs_api = ActiveJobsAPI()
    jobs = active_jobs_api.search_jobs("Data Engineer", "United States")
    print(f"Found {len(jobs)} jobs")
    for job in jobs[:5]:  # Print first 5 jobs as a sample
        print(f"{job['job_title']} at {job['employer_name']} in {job['job_city']}") 