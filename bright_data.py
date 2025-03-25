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
    
    url_encoded_query = quote(search_query)
    url_encoded_location = quote(location)
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
            'job_id': f"glassdoor-{uuid.uuid4()}",
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