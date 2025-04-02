import os
from datetime import datetime, timedelta

def get_mock_user_profile():
    """
    Generate a mock user profile for testing field detection
    
    Returns:
        dict: A mock user profile filled with test data
    """
    # Get data from environment variables if available, otherwise use defaults
    return {
        # Personal information
        "first_name": os.getenv("FIRST_NAME", "John"),
        "last_name": os.getenv("LAST_NAME", "Doe"),
        "email": os.getenv("EMAIL", "johndoe@example.com"),
        "phone": os.getenv("PHONE", "555-123-4567"),
        "address": {
            "street": os.getenv("ADDRESS", "123 Main Street"),
            "city": os.getenv("CITY", "San Francisco"),
            "state": os.getenv("STATE", "California"),
            "zip_code": os.getenv("ZIP", "94105"),
            "country": os.getenv("COUNTRY", "United States")
        },
        
        # Education (in reverse chronological order)
        "education": [
            {
                "institution": "Stanford University",
                "degree": "Master of Science",
                "field_of_study": "Computer Science",
                "gpa": "3.8",
                "start_date": "2018-09-01",
                "end_date": "2020-05-15",
                "graduation_date": "May 2020"
            },
            {
                "institution": "University of California, Berkeley",
                "degree": "Bachelor of Science",
                "field_of_study": "Computer Engineering",
                "gpa": "3.7",
                "start_date": "2014-09-01",
                "end_date": "2018-05-15",
                "graduation_date": "May 2018"
            }
        ],
        
        # Work experience (in reverse chronological order)
        "work_experience": [
            {
                "company": "Tech Innovators Inc.",
                "title": "Senior Software Engineer",
                "location": "San Francisco, CA",
                "start_date": "2022-03-01",
                "end_date": "", # Current job
                "description": "Lead development of cloud-based applications using React, Node.js, and AWS. Implemented CI/CD pipelines and mentored junior developers."
            },
            {
                "company": "Digital Solutions LLC",
                "title": "Software Engineer",
                "location": "San Jose, CA",
                "start_date": "2020-06-01",
                "end_date": "2022-02-28",
                "description": "Developed and maintained web applications using modern JavaScript frameworks. Collaborated with cross-functional teams to deliver high-quality products."
            }
        ],
        
        # Skills
        "skills": {
            "programming": ["Python", "JavaScript", "TypeScript", "Java", "C++", "SQL", "React", "Node.js"],
            "tools": ["Git", "Docker", "AWS", "Azure", "Kubernetes", "Jenkins", "Jira"],
            "languages": ["English (Native)", "Spanish (Conversational)"],
            "soft_skills": ["Problem Solving", "Communication", "Teamwork", "Leadership"]
        },
        
        # Certifications
        "certifications": [
            "AWS Certified Solutions Architect",
            "Google Cloud Professional Developer",
            "Certified Scrum Master"
        ],
        
        # Social media and online presence
        "social_media": {
            "linkedin": "https://www.linkedin.com/in/johndoe",
            "github": "https://github.com/johndoe",
            "twitter": "https://twitter.com/johndoe"
        },
        "portfolio_url": "https://johndoe.portfolio.com",
        "personal_website": "https://johndoe.dev",
        
        # Preferences and eligibility
        "work_authorization": True,
        "requires_sponsorship": False,
        "visa_status": "U.S. Citizen",
        "willing_to_relocate": True,
        "willing_to_travel": True,
        "prefers_remote": True,
        "expected_salary": "125000",
        "preferred_location": "San Francisco Bay Area",
        "total_years_experience": "5",
        
        # Diversity information (optional)
        "has_disability": False,
        "is_veteran": False,
        "race": "Prefer not to say",
        "gender": "Prefer not to say",
        
        # Additional information
        "professional_summary": "Experienced software engineer with a passion for building scalable, high-performance applications. Strong background in full-stack development with expertise in cloud technologies and agile methodologies.",
        "cover_letter_text": "I am excited to apply for the [POSITION] role at [COMPANY]. With my background in software engineering and passion for innovative technology, I believe I would be a great addition to your team. Throughout my career, I have consistently delivered high-quality solutions while adapting to new technologies and methodologies.",
        "references": [
            {
                "name": "Jane Smith",
                "company": "Tech Innovators Inc.",
                "position": "Engineering Manager",
                "phone": "555-987-6543",
                "email": "jane.smith@example.com",
                "relationship": "Manager"
            }
        ],
        "earliest_start_date": "Immediately"
    } 