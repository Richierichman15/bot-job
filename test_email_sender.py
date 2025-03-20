#!/usr/bin/env python3
import argparse
from email_sender import (
    send_email_notification, 
    send_html_notification,
    send_job_notification, 
    configure_email
)

def main():
    """Test the email_sender module with command line arguments"""
    parser = argparse.ArgumentParser(description="Test email sending functionality")
    parser.add_argument("--type", choices=["plain", "html", "job"], default="plain", 
                        help="Type of email to send (plain, html, or job)")
    parser.add_argument("--sender", type=str, help="Override sender email address")
    parser.add_argument("--recipient", type=str, help="Override recipient email address")
    parser.add_argument("--subject", type=str, help="Email subject line", default="Test Email from Job Alert System")
    parser.add_argument("--message", type=str, help="Main message content", default="This is a test message from the Job Alert System")
    parser.add_argument("--live", action="store_true", help="Send actual email (not dry run)")
    parser.add_argument("--job-count", type=int, default=3, help="Number of mock jobs to include in job notification")
    args = parser.parse_args()
    
    # Configure email settings if needed
    if args.sender or args.recipient:
        configure_email(
            sender=args.sender, 
            recipient=args.recipient, 
            dry_run=not args.live
        )
    else:
        # Force values that we know work
        configure_email(
            sender="gitonga.r.nyaga@gmail.com",
            password="tzulgzwnsdcpqgsw", 
            recipient="gitonga.r.nyaga@gmail.com",
            dry_run=not args.live
        )
    
    # Prepare test data
    data = {
        'some_field': args.subject,
        'field1': args.message,
        'field2': 'This test was run using the email_sender module',
        'field3': 'If you receive this, email notifications are working!',
        'timestamp': '2023-07-10 15:30:45'
    }
    
    # Send email based on args
    if args.type == "html":
        print(f"Sending HTML test email {'(LIVE)' if args.live else '(DRY RUN)'}")
        success = send_html_notification(
            data_dict=data,
            subject=args.subject,
            dry_run=not args.live
        )
    elif args.type == "job":
        print(f"Sending job notification test email {'(LIVE)' if args.live else '(DRY RUN)'}")
        # Create mock job data
        jobs = generate_mock_jobs(args.job_count)
        success = send_job_notification(
            jobs=jobs,
            subject=args.subject,
            dry_run=not args.live
        )
    else:
        print(f"Sending plain text test email {'(LIVE)' if args.live else '(DRY RUN)'}")
        success = send_email_notification(
            data_dict=data,
            subject=args.subject,
            dry_run=not args.live
        )
    
    # Print result
    if success:
        print("Email test completed successfully!")
        if not args.live:
            print("Note: This was a dry run. No actual email was sent.")
            print("To send a real email, use the --live flag")
    else:
        print("Email test failed. Check logs for details.")

def generate_mock_jobs(count=3):
    """Generate mock job data for testing"""
    job_titles = [
        "Senior Software Engineer", 
        "Full Stack Developer", 
        "Python Developer",
        "DevOps Engineer",
        "Data Scientist",
        "Machine Learning Engineer",
        "Front-end Developer",
        "Back-end Developer"
    ]
    
    companies = [
        "Tech Innovations Inc.",
        "DataWorks Solutions",
        "WebSoft Technologies",
        "Cloud Systems Inc.",
        "AI Research Group",
        "Digital Solutions LLC"
    ]
    
    locations = [
        {"city": "New York", "country": "USA"},
        {"city": "San Francisco", "country": "USA"},
        {"city": "Chicago", "country": "USA"},
        {"city": "Austin", "country": "USA"},
        {"city": "Boston", "country": "USA"},
        {"city": "Remote", "country": "USA"}
    ]
    
    skills = [
        "Python", "JavaScript", "TypeScript", "React", "Node.js",
        "AWS", "Docker", "Kubernetes", "SQL", "NoSQL",
        "Machine Learning", "Data Analysis", "REST APIs",
        "Git", "CI/CD", "Agile", "Scrum"
    ]
    
    employment_types = ["FULLTIME", "CONTRACT", "PARTTIME"]
    
    import random
    
    jobs = []
    for i in range(count):
        # Select random values
        title = random.choice(job_titles)
        company = random.choice(companies)
        location = random.choice(locations)
        job_skills = random.sample(skills, min(5, random.randint(3, 8)))
        employment_type = random.choice(employment_types)
        
        # Generate salary based on job title and type
        is_senior = "Senior" in title or "Lead" in title
        is_fulltime = employment_type == "FULLTIME"
        
        min_salary = random.randint(80000, 120000) if is_senior else random.randint(60000, 90000)
        max_salary = min_salary + random.randint(10000, 30000)
        
        # For part-time or contract, convert to hourly
        salary_period = "yearly"
        if not is_fulltime:
            min_salary = round(min_salary / 2080)  # Convert to hourly (rough estimate)
            max_salary = round(max_salary / 2080)
            salary_period = "hourly"
        
        # Job description text
        description = f"""
        {company} is seeking a talented {title} to join our team.
        
        This role involves working with {', '.join(job_skills[:3])} to develop innovative solutions.
        
        The ideal candidate will have experience with {', '.join(job_skills)} and be able to work in a fast-paced environment.
        
        {random.choice([
            "We offer competitive benefits and a great work-life balance.",
            "Join our growing team and make an impact!",
            "This is an exciting opportunity to work on cutting-edge projects.",
            "We're building the future of technology and need your expertise."
        ])}
        """
        
        # Create job object
        job = {
            "job_id": f"job-{i+1}",
            "job_title": title,
            "employer_name": company,
            "job_city": location["city"],
            "job_country": location["country"],
            "job_employment_type": employment_type,
            "job_min_salary": min_salary,
            "job_max_salary": max_salary,
            "job_salary_period": salary_period,
            "job_description": description,
            "job_required_skills": job_skills,
            "job_apply_link": f"https://example.com/apply/{company.lower().replace(' ', '-')}/{i+1}",
            "date_posted": "2023-07-01"
        }
        
        jobs.append(job)
    
    return jobs

if __name__ == "__main__":
    main() 