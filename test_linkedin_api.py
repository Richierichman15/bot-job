#!/usr/bin/env python3
"""
Test script for the LinkedIn Data API integration.
"""

import os
import json
from dotenv import load_dotenv
from linkedin_api import LinkedInAPI

def test_linkedin_api():
    """Test the LinkedIn Data API with company queries."""
    load_dotenv()
    
    print("Testing LinkedIn Data API...")
    
    # Initialize the API client
    api = LinkedInAPI()
    
    # Test companies
    companies = ["microsoft", "google", "amazon", "apple", "meta"]
    
    # Test getting company posts
    for company in companies[:2]:  # Just test the first 2 companies to avoid rate limits
        print(f"\nGetting posts for {company}...")
        
        # Get company posts
        posts_data = api.get_company_posts(company, limit=5)
        posts = posts_data.get("data", [])
        
        print(f"Found {len(posts)} posts for {company}")
        
        # Print details of up to 2 posts
        for i, post in enumerate(posts[:2]):
            print(f"\nPost {i+1}:")
            post_text = post.get("text", "")
            print(f"  Date: {post.get('postDate', 'Unknown')}")
            print(f"  URL: {post.get('postUrl', 'No URL')}")
            print(f"  Text preview: {post_text[:100]}..." if post_text else "  No text content")
    
    # Test searching for job posts
    print("\nSearching for job-related posts...")
    job_posts = api.search_jobs_from_posts(companies[:3])  # Just test the first 3 companies
    
    print(f"Found {len(job_posts)} job-related posts")
    
    # Print details of job posts
    for i, job in enumerate(job_posts[:3]):
        print(f"\nJob {i+1}: {job['job_title']}")
        print(f"  Company: {job['employer_name']}")
        print(f"  Apply: {job['job_apply_link']}")
        print(f"  Description preview: {job['job_description'][:100]}..." if job['job_description'] else "  No description")
    
    # Test getting company details
    print("\nGetting company details...")
    for company in companies[:2]:  # Just test the first 2 companies
        print(f"\nDetails for {company}:")
        company_data = api.get_company_details(company)
        
        # Print basic company info
        name = company_data.get("name", "Unknown")
        followers = company_data.get("followers", "Unknown")
        industry = company_data.get("industry", "Unknown")
        website = company_data.get("website", "Unknown")
        
        print(f"  Name: {name}")
        print(f"  Followers: {followers}")
        print(f"  Industry: {industry}")
        print(f"  Website: {website}")

if __name__ == "__main__":
    test_linkedin_api() 