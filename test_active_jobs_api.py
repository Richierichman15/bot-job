#!/usr/bin/env python3
"""
Test script for the Active Jobs DB API integration.
"""

import os
import json
from dotenv import load_dotenv
from active_jobs_api import ActiveJobsAPI

def test_active_jobs_api():
    """Test the Active Jobs DB API with a simple query."""
    load_dotenv()
    
    print("Testing Active Jobs DB API...")
    
    # Initialize the API client
    api = ActiveJobsAPI()
    
    # Test job titles and locations
    job_titles = ["Data Engineer", "Software Developer", "Python Developer"]
    locations = ["United States", "Remote"]
    
    # Test each combination
    for title in job_titles:
        for location in locations:
            print(f"\nSearching for {title} in {location}...")
            
            # Search for jobs
            jobs = api.search_jobs(title, location)
            
            print(f"Found {len(jobs)} jobs for {title} in {location}")
            
            # Print details of up to 3 jobs
            for i, job in enumerate(jobs[:3]):
                print(f"\nJob {i+1}:")
                print(f"  Title: {job.get('job_title')}")
                print(f"  Company: {job.get('employer_name')}")
                print(f"  Location: {job.get('job_city')}, {job.get('job_country')}")
                print(f"  Salary: {job.get('job_min_salary')} - {job.get('job_max_salary')} {job.get('job_salary_currency')} ({job.get('job_salary_period')})")
                print(f"  Apply: {job.get('job_apply_link')}")
                
                # Print a truncated description
                description = job.get('job_description', '')
                if description:
                    print(f"  Description: {description[:100]}...")

if __name__ == "__main__":
    test_active_jobs_api() 