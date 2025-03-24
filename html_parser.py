#!/usr/bin/env python3
import logging
import re
from bs4 import BeautifulSoup
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("html_parser")

class JobPageParser:
    """
    Parser for job listing pages using Beautiful Soup
    """
    
    @staticmethod
    def parse_indeed_listings(html_content):
        """
        Parse job listings from Indeed search results
        
        Args:
            html_content (str): HTML content of the Indeed search results page
            
        Returns:
            list: List of job dictionaries
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            jobs = []
            
            # Find all job cards in the search results
            job_cards = soup.select('.job_seen_beacon')
            
            for card in job_cards:
                try:
                    # Extract the job ID
                    job_id = card.get('data-jk', '')
                    if not job_id:
                        job_id = card.get('id', '').replace('job_', '')
                    
                    # Extract job title
                    title_elem = card.select_one('.jobTitle span')
                    job_title = title_elem.text.strip() if title_elem else "Unknown Title"
                    
                    # Extract company name
                    company_elem = card.select_one('.companyName')
                    employer_name = company_elem.text.strip() if company_elem else "Unknown Company"
                    
                    # Extract location
                    location_elem = card.select_one('.companyLocation')
                    job_location = location_elem.text.strip() if location_elem else "Unknown Location"
                    
                    # Extract job snippet/description
                    snippet_elem = card.select_one('.job-snippet')
                    description = snippet_elem.text.strip() if snippet_elem else ""
                    
                    # Extract salary if available
                    salary_elem = card.select_one('.salary-snippet')
                    salary = salary_elem.text.strip() if salary_elem else ""
                    
                    # Extract date posted
                    date_elem = card.select_one('.date')
                    date_posted = date_elem.text.strip() if date_elem else ""
                    
                    # Create job object
                    job = {
                        'job_id': job_id,
                        'job_title': job_title,
                        'employer_name': employer_name,
                        'job_location': job_location,
                        'job_description': description,
                        'job_min_salary': None,
                        'job_max_salary': None,
                        'job_salary_period': None,
                        'job_apply_link': f"https://www.indeed.com/viewjob?jk={job_id}",
                        'date_posted': date_posted,
                        'job_source': 'indeed'
                    }
                    
                    # Parse salary information
                    if salary:
                        salary_info = JobPageParser._parse_salary(salary)
                        job.update(salary_info)
                    
                    jobs.append(job)
                except Exception as e:
                    logger.error(f"Error parsing Indeed job card: {str(e)}")
                    continue
            
            logger.info(f"Parsed {len(jobs)} jobs from Indeed")
            return jobs
            
        except Exception as e:
            logger.error(f"Error parsing Indeed listings: {str(e)}")
            return []
    
    @staticmethod
    def parse_linkedin_listings(html_content):
        """
        Parse job listings from LinkedIn search results
        
        Args:
            html_content (str): HTML content of the LinkedIn search results page
            
        Returns:
            list: List of job dictionaries
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            jobs = []
            
            # Find all job cards in the search results
            job_cards = soup.select('.job-search-card')
            
            for card in job_cards:
                try:
                    # Extract the job ID
                    job_id = card.get('data-id', '')
                    if not job_id:
                        job_id = card.get('id', '')
                    
                    # Extract job title
                    title_elem = card.select_one('.job-title')
                    job_title = title_elem.text.strip() if title_elem else "Unknown Title"
                    
                    # Extract company name
                    company_elem = card.select_one('.company-name')
                    employer_name = company_elem.text.strip() if company_elem else "Unknown Company"
                    
                    # Extract location
                    location_elem = card.select_one('.job-location')
                    job_location = location_elem.text.strip() if location_elem else "Unknown Location"
                    
                    # Extract job link
                    link_elem = card.select_one('a.job-search-card__link')
                    job_link = link_elem.get('href') if link_elem else ""
                    if job_link and not job_link.startswith('http'):
                        job_link = f"https://www.linkedin.com{job_link}"
                    
                    # Extract date posted
                    date_elem = card.select_one('.job-search-card__listdate')
                    date_posted = date_elem.text.strip() if date_elem else ""
                    
                    # Create job object
                    job = {
                        'job_id': job_id,
                        'job_title': job_title,
                        'employer_name': employer_name,
                        'job_location': job_location,
                        'job_description': "",  # Need to visit job page for description
                        'job_min_salary': None,
                        'job_max_salary': None,
                        'job_salary_period': None,
                        'job_apply_link': job_link,
                        'date_posted': date_posted,
                        'job_source': 'linkedin'
                    }
                    
                    jobs.append(job)
                except Exception as e:
                    logger.error(f"Error parsing LinkedIn job card: {str(e)}")
                    continue
            
            logger.info(f"Parsed {len(jobs)} jobs from LinkedIn")
            return jobs
            
        except Exception as e:
            logger.error(f"Error parsing LinkedIn listings: {str(e)}")
            return []
    
    @staticmethod
    def parse_indeed_job_details(html_content, base_job=None):
        """
        Parse detailed job information from Indeed job page
        
        Args:
            html_content (str): HTML content of the job details page
            base_job (dict): Basic job information to augment
            
        Returns:
            dict: Complete job details
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Start with base job or create a new one
            job = base_job or {}
            
            # Get job title if not already set
            if not job.get('job_title'):
                title_elem = soup.select_one('h1.jobsearch-JobInfoHeader-title')
                if title_elem:
                    job['job_title'] = title_elem.text.strip()
            
            # Get company name if not already set
            if not job.get('employer_name'):
                company_elem = soup.select_one('.jobsearch-InlineCompanyRating-companyName')
                if company_elem:
                    job['employer_name'] = company_elem.text.strip()
            
            # Get location if not already set
            if not job.get('job_location'):
                location_elem = soup.select_one('.jobsearch-JobInfoHeader-subtitle .jobsearch-JobInfoHeader-locationText')
                if location_elem:
                    job['job_location'] = location_elem.text.strip()
            
            # Get full job description
            description_elem = soup.select_one('#jobDescriptionText')
            if description_elem:
                job['job_description'] = description_elem.text.strip()
                
                # Extract skills from description
                skills = JobPageParser._extract_skills(job['job_description'])
                job['job_required_skills'] = skills
            
            # Try to find salary information
            salary_elem = soup.select_one('.jobsearch-JobMetadataHeader-item')
            if salary_elem and not (job.get('job_min_salary') or job.get('job_max_salary')):
                salary_text = salary_elem.text.strip()
                salary_info = JobPageParser._parse_salary(salary_text)
                job.update(salary_info)
            
            # Get employment type
            for metadata in soup.select('.jobsearch-JobMetadataHeader-item'):
                text = metadata.text.lower()
                if 'full-time' in text:
                    job['job_employment_type'] = 'FULLTIME'
                elif 'part-time' in text:
                    job['job_employment_type'] = 'PARTTIME'
                elif 'contract' in text or 'contractor' in text:
                    job['job_employment_type'] = 'CONTRACTOR'
            
            # Find the application link
            apply_button = soup.select_one('button.jobsearch-ApplyButton-button')
            if apply_button and not job.get('job_apply_link'):
                # This only gives the apply button, not the actual link
                # For Indeed, we might need to interact with the page
                job['job_apply_link'] = f"https://www.indeed.com/viewjob?jk={job.get('job_id', '')}"
            
            return job
            
        except Exception as e:
            logger.error(f"Error parsing Indeed job details: {str(e)}")
            return base_job or {}
    
    @staticmethod
    def parse_linkedin_job_details(html_content, base_job=None):
        """
        Parse detailed job information from LinkedIn job page
        
        Args:
            html_content (str): HTML content of the job details page
            base_job (dict): Basic job information to augment
            
        Returns:
            dict: Complete job details
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Start with base job or create a new one
            job = base_job or {}
            
            # Get job title if not already set
            if not job.get('job_title'):
                title_elem = soup.select_one('h1.job-details-header__title')
                if title_elem:
                    job['job_title'] = title_elem.text.strip()
            
            # Get company name if not already set
            if not job.get('employer_name'):
                company_elem = soup.select_one('.job-details-jobs-unified-top-card__company-name')
                if company_elem:
                    job['employer_name'] = company_elem.text.strip()
            
            # Get location if not already set
            if not job.get('job_location'):
                location_elem = soup.select_one('.job-details-jobs-unified-top-card__bullet')
                if location_elem:
                    job['job_location'] = location_elem.text.strip()
            
            # Get full job description
            description_elem = soup.select_one('.job-details-jobs-unified-description__content')
            if description_elem:
                job['job_description'] = description_elem.text.strip()
                
                # Extract skills from description
                skills = JobPageParser._extract_skills(job['job_description'])
                job['job_required_skills'] = skills
            
            # Try to find salary information
            criteria_list = soup.select('.job-details-jobs-unified-top-card__job-criteria-item')
            for criteria in criteria_list:
                label_elem = criteria.select_one('.job-details-jobs-unified-top-card__job-criteria-subheader')
                value_elem = criteria.select_one('.job-details-jobs-unified-top-card__job-criteria-text')
                
                if label_elem and value_elem:
                    label = label_elem.text.lower().strip()
                    value = value_elem.text.strip()
                    
                    if 'employment type' in label:
                        job_type = value.lower()
                        if 'full' in job_type:
                            job['job_employment_type'] = 'FULLTIME'
                        elif 'part' in job_type:
                            job['job_employment_type'] = 'PARTTIME'
                        elif 'contract' in job_type:
                            job['job_employment_type'] = 'CONTRACTOR'
                    elif 'salary' in label:
                        salary_info = JobPageParser._parse_salary(value)
                        job.update(salary_info)
            
            # Find the application link
            apply_button = soup.select_one('a.job-details-jobs-unified-top-card__apply-button')
            if apply_button and not job.get('job_apply_link'):
                job['job_apply_link'] = apply_button.get('href', '')
                if job['job_apply_link'] and not job['job_apply_link'].startswith('http'):
                    job['job_apply_link'] = f"https://www.linkedin.com{job['job_apply_link']}"
            
            return job
            
        except Exception as e:
            logger.error(f"Error parsing LinkedIn job details: {str(e)}")
            return base_job or {}
    
    @staticmethod
    def _parse_salary(salary_text):
        """
        Parse salary information from text
        
        Args:
            salary_text (str): Salary text from job listing
            
        Returns:
            dict: Parsed salary information
        """
        salary_info = {
            'job_min_salary': None,
            'job_max_salary': None,
            'job_salary_period': None
        }
        
        try:
            # Remove any non-essential parts
            salary_text = salary_text.replace('Estimated', '').replace('$', '')
            
            # Check for salary period
            if 'year' in salary_text.lower() or 'annually' in salary_text.lower():
                salary_info['job_salary_period'] = 'yearly'
            elif 'hour' in salary_text.lower():
                salary_info['job_salary_period'] = 'hourly'
            elif 'month' in salary_text.lower():
                salary_info['job_salary_period'] = 'monthly'
            elif 'week' in salary_text.lower():
                salary_info['job_salary_period'] = 'weekly'
            elif 'day' in salary_text.lower():
                salary_info['job_salary_period'] = 'daily'
            
            # Try to extract salary range using regex
            pattern = r'(\d[\d,.]+)\s*-\s*(\d[\d,.]+)'
            range_match = re.search(pattern, salary_text)
            
            if range_match:
                min_salary = range_match.group(1).replace(',', '')
                max_salary = range_match.group(2).replace(',', '')
                
                try:
                    salary_info['job_min_salary'] = float(min_salary)
                    salary_info['job_max_salary'] = float(max_salary)
                except ValueError:
                    pass
            else:
                # Try to extract single value
                pattern = r'(\d[\d,.]+)'
                single_match = re.search(pattern, salary_text)
                
                if single_match:
                    salary = single_match.group(1).replace(',', '')
                    
                    try:
                        # Use the same value for min and max
                        salary_info['job_min_salary'] = float(salary)
                        salary_info['job_max_salary'] = float(salary)
                    except ValueError:
                        pass
        
        except Exception as e:
            logger.error(f"Error parsing salary: {str(e)}")
        
        return salary_info
    
    @staticmethod
    def _extract_skills(description):
        """
        Extract potential skills from job description
        
        Args:
            description (str): Job description text
            
        Returns:
            list: List of potential skills
        """
        # List of common programming languages and skills
        common_skills = [
            "Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "PHP", "Ruby", "Go", "Swift",
            "React", "Angular", "Vue", "Node.js", "Express", "Django", "Flask", "Spring", "ASP.NET",
            "HTML", "CSS", "SASS", "LESS", "SQL", "NoSQL", "MongoDB", "MySQL", "PostgreSQL", "Oracle",
            "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "CI/CD", "Git", "REST", "GraphQL",
            "Agile", "Scrum", "DevOps", "TDD", "OOP", "Functional Programming", "Linux", "Bash",
            "Machine Learning", "AI", "Data Science", "Big Data", "Hadoop", "Spark", "TensorFlow",
            "PyTorch", "NLP", "Computer Vision", "Blockchain", "IoT", "Embedded Systems", "Microservices",
            "System Design", "Algorithms", "Data Structures", "Networking", "Security", "Authentication"
        ]
        
        # Extract mentioned skills
        mentioned_skills = []
        for skill in common_skills:
            # Regex to find whole words only, case insensitive
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, description, re.IGNORECASE):
                mentioned_skills.append(skill)
        
        return mentioned_skills
                
# For testing
if __name__ == "__main__":
    # Test with a sample HTML file
    try:
        with open('sample_indeed.html', 'r') as f:
            html_content = f.read()
            
        jobs = JobPageParser.parse_indeed_listings(html_content)
        print(json.dumps(jobs, indent=2))
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}") 