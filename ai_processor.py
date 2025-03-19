import os
import logging
import json
from dotenv import load_dotenv
from datetime import datetime
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ai_processor")

load_dotenv()

class AIJobProcessor:
    """
    AI-powered job processing using OpenAI.
    Analyzes job descriptions, generates applications, and helps automate the application process.
    """
    
    def __init__(self):
        """Initialize the AI processor with OpenAI credentials."""
        load_dotenv()
        
        # Initialize OpenAI client
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
        
        self.client = OpenAI(api_key=self.api_key)
        
        # Load candidate profile
        self.candidate_profile = self._load_candidate_profile()
        
        # Define job requirements
        self.min_salary = float(os.getenv("MIN_SALARY", "20"))
        self.required_skills = os.getenv("REQUIRED_SKILLS", "python,javascript,react,node.js").split(",")
        self.preferred_location = os.getenv("PREFERRED_LOCATION", "oklahoma city")
        self.experience_level = os.getenv("EXPERIENCE_LEVEL", "entry-level,mid-level")
    
    def _load_candidate_profile(self):
        """Load the candidate's profile from the profile.json file."""
        try:
            profile_path = os.path.join(os.path.dirname(__file__), "profile.json")
            if os.path.exists(profile_path):
                with open(profile_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning("profile.json not found. Using default profile.")
                return {
                    "name": os.getenv("CANDIDATE_NAME", ""),
                    "email": os.getenv("CANDIDATE_EMAIL", ""),
                    "phone": os.getenv("CANDIDATE_PHONE", ""),
                    "linkedin": os.getenv("CANDIDATE_LINKEDIN", ""),
                    "github": os.getenv("CANDIDATE_GITHUB", ""),
                    "portfolio": os.getenv("CANDIDATE_PORTFOLIO", ""),
                    "skills": self.required_skills,
                    "experience": os.getenv("CANDIDATE_EXPERIENCE", "2 years"),
                    "education": os.getenv("CANDIDATE_EDUCATION", "Bachelor's in Computer Science"),
                }
        except Exception as e:
            logger.error(f"Error loading profile: {str(e)}")
            return {}
    
    def analyze_job(self, job_data):
        """
        Analyze a job posting to determine if it's a good match.
        
        Args:
            job_data (dict): Job posting data including title, description, requirements, etc.
            
        Returns:
            dict: Analysis results including match score and reasons
        """
        try:
            # Prepare the job analysis prompt
            prompt = f"""
            Analyze this job posting for a software development position:
            
            Title: {job_data.get('job_title', '')}
            Company: {job_data.get('employer_name', '')}
            Location: {job_data.get('job_city', '')} {job_data.get('job_country', '')}
            Description: {job_data.get('job_description', '')}
            
            Candidate Profile:
            - Skills: {', '.join(self.required_skills)}
            - Experience: {self.candidate_profile.get('experience', '')}
            - Education: {self.candidate_profile.get('education', '')}
            - Preferred Location: {self.preferred_location}
            
            Requirements:
            1. Minimum salary equivalent to ${self.min_salary}/hour
            2. Must be in {self.preferred_location} or remote
            3. Must match candidate's skills and experience level
            
            Please analyze:
            1. Is this job a good match? (Yes/No)
            2. What percentage of required skills match?
            3. Is the location suitable?
            4. Is the salary acceptable?
            5. What are the key requirements?
            6. Should we apply? (Yes/No)
            7. Provide a brief explanation of your recommendation.
            
            Format your response as JSON.
            """
            
            # Get AI analysis
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            analysis = json.loads(response.choices[0].message.content)
            
            # Add timestamp
            analysis['timestamp'] = datetime.now().isoformat()
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing job: {str(e)}")
            return {
                "is_match": False,
                "should_apply": False,
                "error": str(e)
            }
    
    def generate_cover_letter(self, job_data, analysis):
        """
        Generate a customized cover letter for the job.
        
        Args:
            job_data (dict): Job posting data
            analysis (dict): Job analysis results
            
        Returns:
            str: Generated cover letter
        """
        try:
            # Prepare the cover letter prompt
            prompt = f"""
            Generate a professional cover letter for this job application:
            
            Job Details:
            - Title: {job_data.get('job_title', '')}
            - Company: {job_data.get('employer_name', '')}
            - Location: {job_data.get('job_city', '')} {job_data.get('job_country', '')}
            
            Candidate Profile:
            - Name: {self.candidate_profile.get('name', '')}
            - Skills: {', '.join(self.required_skills)}
            - Experience: {self.candidate_profile.get('experience', '')}
            - Education: {self.candidate_profile.get('education', '')}
            
            Job Description:
            {job_data.get('job_description', '')}
            
            Requirements:
            1. Keep it concise but compelling
            2. Highlight relevant skills and experience
            3. Show enthusiasm for the company
            4. Explain why you're a great fit
            5. Include specific details from the job posting
            
            Format: Standard business letter format
            """
            
            # Get AI-generated cover letter
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {str(e)}")
            return None
    
    def prepare_application(self, job_data):
        """
        Prepare a complete job application including analysis and materials.
        
        Args:
            job_data (dict): Job posting data
            
        Returns:
            dict: Complete application package
        """
        try:
            # First analyze the job
            analysis = self.analyze_job(job_data)
            
            # If it's a good match, prepare application materials
            if analysis.get('should_apply', False):
                # Generate cover letter
                cover_letter = self.generate_cover_letter(job_data, analysis)
                
                # Prepare application package
                application = {
                    'job_data': job_data,
                    'analysis': analysis,
                    'materials': {
                        'cover_letter': cover_letter,
                        'resume': self.candidate_profile.get('resume_path', ''),
                        'portfolio': self.candidate_profile.get('portfolio', ''),
                        'github': self.candidate_profile.get('github', ''),
                        'linkedin': self.candidate_profile.get('linkedin', '')
                    },
                    'candidate': {
                        'name': self.candidate_profile.get('name', ''),
                        'email': self.candidate_profile.get('email', ''),
                        'phone': self.candidate_profile.get('phone', '')
                    },
                    'status': 'ready_to_apply',
                    'timestamp': datetime.now().isoformat()
                }
                
                return application
            else:
                return {
                    'job_data': job_data,
                    'analysis': analysis,
                    'status': 'not_suitable',
                    'timestamp': datetime.now().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Error preparing application: {str(e)}")
            return {
                'job_data': job_data,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

# For testing the module directly
if __name__ == "__main__":
    processor = AIJobProcessor()
    
    # Test job data
    test_job = {
        "job_title": "Senior Python Developer",
        "employer_name": "Tech Corp",
        "job_city": "Oklahoma City",
        "job_country": "USA",
        "job_description": """
        We're looking for a Python developer with:
        - 2+ years of experience with Python
        - Experience with web frameworks (Django/Flask)
        - JavaScript and React knowledge
        - Database experience (PostgreSQL)
        - Good communication skills
        
        Salary: $80,000 - $120,000/year
        Location: Oklahoma City (Hybrid)
        """,
        "job_salary_min": 80000,
        "job_salary_max": 120000,
        "job_salary_period": "yearly"
    }
    
    # Test analysis
    analysis = processor.analyze_job(test_job)
    print("\nJob Analysis:")
    print(json.dumps(analysis, indent=2))
    
    # If it's a good match, test cover letter generation
    if analysis.get('should_apply', False):
        print("\nGenerating Cover Letter:")
        cover_letter = processor.generate_cover_letter(test_job, analysis)
        print(cover_letter)
        
        print("\nPreparing Full Application:")
        application = processor.prepare_application(test_job)
        print(json.dumps(application['status'], indent=2)) 