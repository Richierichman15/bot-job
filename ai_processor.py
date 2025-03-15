import os
import logging
import json
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ai_processor")

load_dotenv()

class AIProcessor:
    def __init__(self):
        """Initialize the AI processor with the appropriate model"""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.using_openai = bool(self.openai_api_key)
        
        if self.using_openai:
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
                logger.info("Initialized OpenAI client for job processing")
            except ImportError:
                logger.warning("OpenAI package not installed, but API key provided. Using fallback.")
                self.using_openai = False
        else:
            try:
                # Try to use Ollama if available
                import ollama
                self.ollama_available = True
                logger.info("Using Ollama for job processing")
            except ImportError:
                self.ollama_available = False
                logger.warning("Neither OpenAI nor Ollama available. AI processing disabled.")
    
    def analyze_job(self, job):
        """
        Analyze a job listing using AI to extract key information
        
        Args:
            job (dict): Job listing dictionary
            
        Returns:
            dict: Enhanced job dictionary with AI analysis
        """
        job_description = job.get('job_description', '')
        if not job_description:
            logger.warning("No job description provided for analysis")
            return job
        
        try:
            if self.using_openai:
                return self._analyze_with_openai(job)
            elif self.ollama_available:
                return self._analyze_with_ollama(job)
            else:
                logger.warning("No AI processing available")
                return job
        except Exception as e:
            logger.error(f"Error analyzing job with AI: {str(e)}")
            return job
    
    def _analyze_with_openai(self, job):
        """Analyze job using OpenAI"""
        job_description = job.get('job_description', '')
        job_title = job.get('job_title', 'Unspecified Position')
        
        prompt = f"""
        Analyze this job listing and extract the following information:
        
        Job title: {job_title}
        
        Description:
        {job_description[:3000]}...
        
        Please extract:
        1. Required skills (comma-separated list)
        2. Recommended skills (comma-separated list)
        3. Years of experience required (number or range)
        4. Education requirements (degree level)
        5. Key responsibilities (bullet points)
        6. A brief summary of the role (2-3 sentences)
        7. Suitability score (1-10, where 10 is perfect match for a {job_title})
        
        Format as JSON.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a job analysis assistant. Extract structured data from job descriptions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=800
            )
            
            analysis_text = response.choices[0].message.content
            
            # Try to extract JSON from the response
            try:
                # Find JSON part in the response
                import re
                json_match = re.search(r'```json\n(.*?)\n```', analysis_text, re.DOTALL)
                if json_match:
                    analysis_text = json_match.group(1)
                
                analysis = json.loads(analysis_text)
                job['ai_analysis'] = analysis
                logger.info(f"Successfully analyzed job with OpenAI")
                return job
            except json.JSONDecodeError:
                logger.warning(f"Could not parse AI response as JSON: {analysis_text[:100]}...")
                job['ai_analysis_text'] = analysis_text
                return job
                
        except Exception as e:
            logger.error(f"Error using OpenAI for analysis: {str(e)}")
            return job
    
    def _analyze_with_ollama(self, job):
        """Analyze job using Ollama"""
        import subprocess
        
        job_description = job.get('job_description', '')
        job_title = job.get('job_title', 'Unspecified Position')
        
        prompt = f"""
        Analyze this job listing and extract the following information:
        
        Job title: {job_title}
        
        Description:
        {job_description[:3000]}...
        
        Please extract:
        1. Required skills (comma-separated list)
        2. Recommended skills (comma-separated list)
        3. Years of experience required (number or range)
        4. Education requirements (degree level)
        5. Key responsibilities (bullet points)
        6. A brief summary of the role (2-3 sentences)
        7. Suitability score (1-10, where 10 is perfect match for a {job_title})
        
        Format as JSON.
        """
        
        try:
            # Using ollama via subprocess for compatibility
            cmd = f'ollama run mistral "{prompt}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            analysis_text = result.stdout
            
            # Try to extract JSON from the response
            try:
                # Find JSON part in the response
                import re
                json_match = re.search(r'```json\n(.*?)\n```', analysis_text, re.DOTALL)
                if json_match:
                    analysis_text = json_match.group(1)
                
                analysis = json.loads(analysis_text)
                job['ai_analysis'] = analysis
                logger.info(f"Successfully analyzed job with Ollama")
                return job
            except json.JSONDecodeError:
                logger.warning(f"Could not parse Ollama response as JSON: {analysis_text[:100]}...")
                job['ai_analysis_text'] = analysis_text
                return job
                
        except Exception as e:
            logger.error(f"Error using Ollama for analysis: {str(e)}")
            return job
            
    def summarize_jobs(self, jobs, max_jobs=5):
        """
        Create a summary of multiple job listings
        
        Args:
            jobs (list): List of job dictionaries
            max_jobs (int): Maximum number of jobs to summarize
            
        Returns:
            str: Summary of the jobs
        """
        if not jobs:
            return "No jobs to summarize."
        
        if not self.using_openai and not self.ollama_available:
            summaries = []
            for job in jobs[:max_jobs]:
                title = job.get('job_title', 'Unspecified Position')
                company = job.get('employer_name', 'Unknown Company')
                location = f"{job.get('job_city', '')} {job.get('job_state', '')}"
                summaries.append(f"- {title} at {company} in {location}")
            
            return "\n".join(summaries)
        
        try:
            # Prepare job data
            job_data = []
            for job in jobs[:max_jobs]:
                title = job.get('job_title', 'Unspecified Position')
                company = job.get('employer_name', 'Unknown Company')
                location = f"{job.get('job_city', '')} {job.get('job_state', '')}"
                salary = f"{job.get('job_min_salary', '?')} - {job.get('job_max_salary', '?')} {job.get('job_salary_currency', 'USD')}"
                
                job_data.append(f"{title} at {company} in {location}, Salary: {salary}")
            
            if self.using_openai:
                return self._summarize_with_openai(job_data)
            elif self.ollama_available:
                return self._summarize_with_ollama(job_data)
            else:
                return "\n".join(job_data)
        
        except Exception as e:
            logger.error(f"Error summarizing jobs: {str(e)}")
            return "\n".join([job.get('job_title', 'Unspecified Position') for job in jobs[:max_jobs]])
    
    def _summarize_with_openai(self, job_data):
        """Summarize jobs using OpenAI"""
        prompt = f"""
        Here are some job listings:
        
        {chr(10).join(job_data)}
        
        Please provide a brief summary of these job opportunities. Include:
        1. Types of positions available
        2. Salary ranges
        3. Common locations
        4. Brief advice for applying
        
        Keep it concise but helpful.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful job search assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Error using OpenAI for summarization: {str(e)}")
            return "\n".join(job_data)
    
    def _summarize_with_ollama(self, job_data):
        """Summarize jobs using Ollama"""
        import subprocess
        
        prompt = f"""
        Here are some job listings:
        
        {chr(10).join(job_data)}
        
        Please provide a brief summary of these job opportunities. Include:
        1. Types of positions available
        2. Salary ranges
        3. Common locations
        4. Brief advice for applying
        
        Keep it concise but helpful.
        """
        
        try:
            # Using ollama via subprocess for compatibility
            cmd = f'ollama run mistral "{prompt}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            return result.stdout.strip()
        
        except Exception as e:
            logger.error(f"Error using Ollama for summarization: {str(e)}")
            return "\n".join(job_data) 