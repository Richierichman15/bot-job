#!/usr/bin/env python3
import os
import json
import logging
from datetime import datetime
import argparse
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_application(company_name, job_title, job_id=None):
    """
    Create a test job application package
    
    Args:
        company_name (str): Name of the company
        job_title (str): Job title
        job_id (str): Optional job ID (will be generated if None)
        
    Returns:
        str: Path to the created application directory
    """
    # Setup paths
    applications_dir = "applications"
    default_resume_path = "/Users/gitonga-nyaga/github/job/resume/GN.pdf"
    resume_path = os.getenv("RESUME_PATH", default_resume_path)
    
    # If the resume path doesn't exist, try relative path
    if not os.path.exists(resume_path):
        relative_path = os.path.join(os.getcwd(), "resume/GN.pdf")
        if os.path.exists(relative_path):
            resume_path = relative_path
            logger.info(f"Using resume from relative path: {resume_path}")
        else:
            logger.warning(f"Resume not found at {resume_path} or {relative_path}")
    
    # Create a unique job ID if not provided
    if not job_id:
        job_id = f"test-job-{int(datetime.now().timestamp())}"
    
    # Create a safe company name for directories
    safe_company = company_name.lower().replace(' ', '_')
    
    # Create application ID
    date_str = datetime.now().strftime('%Y%m%d')
    application_id = f"{safe_company}_{date_str}_{job_id}"
    
    # Create application directory
    app_dir = os.path.join(applications_dir, application_id)
    os.makedirs(app_dir, exist_ok=True)
    
    # Create fake job details
    job_details = {
        "job_id": job_id,
        "job_title": job_title,
        "employer_name": company_name,
        "job_location": "Remote",
        "job_description": f"This is a test job description for {job_title} at {company_name}. Skills needed: Python, JavaScript, React.",
        "job_min_salary": 100000,
        "job_max_salary": 130000,
        "job_salary_period": "yearly",
        "job_apply_link": f"https://example.com/jobs/{job_id}",
        "date_posted": "2023-08-01",
        "job_required_skills": ["Python", "JavaScript", "React"],
        "job_employment_type": "FULLTIME"
    }
    
    # Save job details
    job_details_path = os.path.join(app_dir, "job_details.json")
    with open(job_details_path, 'w') as f:
        json.dump(job_details, f, indent=2)
    
    # Create cover letter
    cover_letter = f"""Dear Hiring Manager at {company_name},

I am writing to express my interest in the {job_title} position at {company_name}. 
With my background in web development and experience with Python, JavaScript and React, 
I believe I would be a valuable addition to your team.

Thank you for considering my application.

Sincerely,
Test Candidate
test@example.com
555-123-4567
"""
    
    # Save cover letter
    cover_letter_path = os.path.join(app_dir, f"cover_letter_{safe_company}.txt")
    with open(cover_letter_path, 'w') as f:
        f.write(cover_letter)
    
    # Copy resume (or create empty file if resume doesn't exist)
    resume_filename = "GN.pdf" # Force use of this filename regardless of source
    destination_resume = os.path.join(app_dir, resume_filename)
    
    if os.path.exists(resume_path):
        shutil.copy(resume_path, destination_resume)
    else:
        # Create an empty file
        with open(destination_resume, 'w') as f:
            f.write("This is a placeholder for a resume file")
    
    # Create application metadata
    metadata = {
        "application_id": application_id,
        "job_title": job_title,
        "company": company_name,
        "apply_link": f"https://example.com/jobs/{job_id}",
        "date_prepared": datetime.now().isoformat(),
        "submitted": False,
        "submission_date": None
    }
    
    # Save metadata
    metadata_path = os.path.join(app_dir, "metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Created test application for {job_title} at {company_name} in {app_dir}")
    return app_dir

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate test job applications")
    parser.add_argument("--count", type=int, default=3, help="Number of test applications to generate")
    args = parser.parse_args()
    
    # Create applications directory if it doesn't exist
    os.makedirs("applications", exist_ok=True)
    
    # Sample companies and job titles
    companies = [
        "Tech Innovations Inc",
        "DataWorks Solutions",
        "CloudNative Systems",
        "DevOps Enterprise",
        "AI Solutions LLC"
    ]
    
    job_titles = [
        "Senior Software Engineer",
        "Full Stack Developer",
        "Python Backend Engineer",
        "DevOps Specialist",
        "Frontend Developer"
    ]
    
    # Generate test applications
    for i in range(args.count):
        company_index = i % len(companies)
        job_index = i % len(job_titles)
        
        company = companies[company_index]
        job_title = job_titles[job_index]
        
        create_test_application(company, job_title)
    
    logger.info(f"Generated {args.count} test applications")
    logger.info("You can now run 'python job_alert.py --apply-only' to process these applications")

if __name__ == "__main__":
    main() 