#!/usr/bin/env python3
import os
import json
import time
import logging
from dotenv import load_dotenv
from bright_data_scraper import BrightDataScraper
from html_parser import JobPageParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("test_brightdata")

# Load environment variables
load_dotenv()

def test_indeed_search():
    """Test searching for jobs on Indeed"""
    try:
        scraper = BrightDataScraper()
        
        # Search for Python developer jobs in remote locations
        query = "python developer"
        location = "remote"
        
        logger.info(f"Searching Indeed for: {query} in {location}")
        response = scraper._make_request(
            f"https://www.indeed.com/jobs?q={query.replace(' ', '+')}&l={location}",
            format_type="raw"
        )
        
        if not response:
            logger.error("Failed to get response from Bright Data API")
            return
        
        # Save the response to a file for debugging
        with open("indeed_response.html", "w") as f:
            f.write(response)
        logger.info("Saved Indeed response to indeed_response.html")
        
        # Parse the jobs from the response
        jobs = JobPageParser.parse_indeed_listings(response)
        
        logger.info(f"Found {len(jobs)} jobs on Indeed")
        
        # Save the parsed jobs to a file
        with open("indeed_jobs.json", "w") as f:
            json.dump(jobs, f, indent=2)
        logger.info("Saved parsed jobs to indeed_jobs.json")
        
        # Get details for the first job if any
        if jobs:
            first_job = jobs[0]
            job_url = first_job.get('job_apply_link')
            
            if job_url:
                logger.info(f"Getting details for job: {first_job.get('job_title')}")
                job_response = scraper._make_request(job_url, format_type="raw")
                
                if job_response:
                    # Save the job details page for debugging
                    with open("indeed_job_details.html", "w") as f:
                        f.write(job_response)
                    logger.info("Saved job details to indeed_job_details.html")
                    
                    # Parse the job details
                    detailed_job = JobPageParser.parse_indeed_job_details(job_response, first_job)
                    
                    # Save the detailed job to a file
                    with open("indeed_job_details.json", "w") as f:
                        json.dump(detailed_job, f, indent=2)
                    logger.info("Saved detailed job info to indeed_job_details.json")
    
    except Exception as e:
        logger.error(f"Error in Indeed test: {str(e)}")

def test_linkedin_search():
    """Test searching for jobs on LinkedIn"""
    try:
        scraper = BrightDataScraper()
        
        # Search for Software Engineer jobs in New York
        query = "software engineer"
        location = "new york"
        
        logger.info(f"Searching LinkedIn for: {query} in {location}")
        response = scraper._make_request(
            f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ', '%20')}&location={location.replace(' ', '%20')}",
            format_type="raw"
        )
        
        if not response:
            logger.error("Failed to get response from Bright Data API")
            return
        
        # Save the response to a file for debugging
        with open("linkedin_response.html", "w") as f:
            f.write(response)
        logger.info("Saved LinkedIn response to linkedin_response.html")
        
        # Parse the jobs from the response
        jobs = JobPageParser.parse_linkedin_listings(response)
        
        logger.info(f"Found {len(jobs)} jobs on LinkedIn")
        
        # Save the parsed jobs to a file
        with open("linkedin_jobs.json", "w") as f:
            json.dump(jobs, f, indent=2)
        logger.info("Saved parsed jobs to linkedin_jobs.json")
        
        # Get details for the first job if any
        if jobs:
            first_job = jobs[0]
            job_url = first_job.get('job_apply_link')
            
            if job_url:
                logger.info(f"Getting details for job: {first_job.get('job_title')}")
                job_response = scraper._make_request(job_url, format_type="raw")
                
                if job_response:
                    # Save the job details page for debugging
                    with open("linkedin_job_details.html", "w") as f:
                        f.write(job_response)
                    logger.info("Saved job details to linkedin_job_details.html")
                    
                    # Parse the job details
                    detailed_job = JobPageParser.parse_linkedin_job_details(job_response, first_job)
                    
                    # Save the detailed job to a file
                    with open("linkedin_job_details.json", "w") as f:
                        json.dump(detailed_job, f, indent=2)
                    logger.info("Saved detailed job info to linkedin_job_details.json")
    
    except Exception as e:
        logger.error(f"Error in LinkedIn test: {str(e)}")

def main():
    """Main function to run tests"""
    logger.info("Starting Bright Data scraper tests")
    
    # Test Indeed job search
    test_indeed_search()
    
    # Wait a bit before next test
    time.sleep(5)
    
    # Test LinkedIn job search
    test_linkedin_search()
    
    logger.info("Completed Bright Data scraper tests")

if __name__ == "__main__":
    main() 