import os
import smtplib
import logging
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailNotifier:
    """
    Email notification system for job opportunities.
    Sends HTML emails with job details, analysis, and application materials.
    """
    
    def __init__(self):
        """Initialize email settings from environment variables"""
        load_dotenv()
        
        # Email configuration
        self.sender_email = os.getenv("EMAIL_SENDER")
        self.sender_password = os.getenv("EMAIL_PASSWORD")
        self.recipient_email = os.getenv("EMAIL_RECIPIENT", self.sender_email)
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        
        # Default to dry run mode for safety
        self.dry_run = True
        logger.info("Initial dry run mode: True (safety default)")
        
        # Try to get the dry run setting from environment
        try:
            dry_run_value = os.getenv("EMAIL_DRY_RUN", "true")
            logger.info(f"EMAIL_DRY_RUN from env: '{dry_run_value}'")
            
            # If dry_run_value doesn't look right, try to read it directly from the file
            if dry_run_value.startswith("'") or dry_run_value.startswith('"'):
                try:
                    # Try to read directly from .env file
                    with open('.env', 'r') as f:
                        for line in f:
                            if line.strip().startswith('EMAIL_DRY_RUN='):
                                dry_run_value = line.strip().split('=', 1)[1].strip("'\"")
                                logger.info(f"EMAIL_DRY_RUN read directly from file: '{dry_run_value}'")
                                break
                except Exception as e:
                    logger.warning(f"Error reading .env file directly: {e}")
            
            # Parse the value with various checks
            if isinstance(dry_run_value, str):
                dry_run_value = dry_run_value.lower().strip().strip("'\"")
                if dry_run_value in ["false", "0", "no", "f", "n", "off"]:
                    self.dry_run = False
                    logger.info("Dry run mode disabled based on environment setting")
        except Exception as e:
            logger.warning(f"Error parsing EMAIL_DRY_RUN: {e}. Using default (True)")
        
        logger.info(f"Final email dry run mode: {self.dry_run}")
        
        # Validate email settings if not in dry run mode
        if not self.dry_run and not all([self.sender_email, self.sender_password, self.recipient_email]):
            logger.warning("Email settings incomplete. Will use dry run mode.")
            self.dry_run = True
    
    def send_job_notifications(self, applications, force_dry_run=False):
        """
        Send email notifications for new job opportunities
        
        Args:
            applications (list): List of job application packages
            force_dry_run (bool): If True, always use dry run mode regardless of settings
            
        Returns:
            bool: Whether the email was sent successfully
        """
        if not applications:
            logger.info("No applications to send notifications for")
            return True
            
        try:
            # Check if we should use dry run mode
            use_dry_run = self.dry_run or force_dry_run
            
            if use_dry_run:
                logger.info(f"Sending notifications for {len(applications)} jobs in dry run mode")
                return self._handle_dry_run(applications)
            else:
                logger.info(f"Sending real email notifications for {len(applications)} jobs")
                # Create email message
                msg = self._create_email_message(applications)
                
                # Connect to SMTP server and send email
                return self._send_email(msg)
            
        except Exception as e:
            logger.error(f"Error sending email notifications: {str(e)}")
            return False
    
    def _handle_dry_run(self, applications):
        """Handle dry run mode by logging email content instead of sending"""
        logger.info(f"[DRY RUN] Would send email with {len(applications)} job opportunities")
        
        # Create a summary of each job
        for i, app in enumerate(applications, 1):
            job = self._extract_job_data(app)
            analysis = app.get('analysis', {})
            
            logger.info(f"[DRY RUN] Job {i}: {job.get('job_title')} at {job.get('employer_name')}")
            logger.info(f"[DRY RUN]   Location: {job.get('job_city', 'N/A')}, {job.get('job_country', 'N/A')}")
            logger.info(f"[DRY RUN]   Salary: {self._format_salary(job.get('job_min_salary'), job.get('job_max_salary'), job.get('job_salary_period'))}")
            logger.info(f"[DRY RUN]   Match: {analysis.get('skill_match_percentage', 'N/A')}%")
            logger.info(f"[DRY RUN]   Apply: {job.get('job_apply_link', 'N/A')}")
            
            # Log first 100 chars of job description
            description = job.get('job_description', '')
            if description:
                logger.info(f"[DRY RUN]   Description: {description[:100]}...")
            
            logger.info("---")
        
        return True  # Indicate success in dry run mode
    
    def _create_email_message(self, applications):
        """Create a multipart email message with HTML content"""
        msg = MIMEMultipart()
        msg["From"] = self.sender_email
        msg["To"] = self.recipient_email
        msg["Subject"] = f"Job Opportunities Alert - {len(applications)} matches - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Build HTML body
        html_body = self._build_email_body(applications)
        msg.attach(MIMEText(html_body, "html"))
        
        return msg
    
    def _send_email(self, msg):
        """Send email via SMTP"""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                
            logger.info(f"Successfully sent email to {self.recipient_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed. Check your email and password.")
            return False
            
        except smtplib.SMTPConnectError:
            logger.error(f"Failed to connect to SMTP server {self.smtp_server}:{self.smtp_port}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def _extract_job_data(self, application):
        """Extract job data from different application package formats"""
        if 'job_data' in application:
            return application['job_data']
        elif 'job' in application:
            return application['job']
        return application
    
    def _build_email_body(self, applications):
        """Build the HTML email body with job details and analysis."""
        # Create the HTML email body
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .job-section {{ margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                .job-title {{ color: #2c3e50; font-size: 1.5em; margin-bottom: 10px; }}
                .company-name {{ color: #7f8c8d; font-size: 1.2em; margin-bottom: 15px; }}
                .location {{ color: #95a5a6; margin-bottom: 15px; }}
                .salary {{ color: #27ae60; font-weight: bold; margin-bottom: 15px; }}
                .description {{ margin-bottom: 15px; }}
                .requirements {{ margin-bottom: 15px; }}
                .apply-link {{ display: inline-block; background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 10px; }}
                .match-percentage {{ color: #e74c3c; font-weight: bold; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>New Job Opportunities Found!</h1>
                    <p>We've found {len(applications)} new job opportunities that match your criteria.</p>
                </div>
                
                {''.join(f'''
                <div class="job-section">
                    <h2 class="job-title">{self._extract_job_data(job).get('job_title', 'Job Posting')}</h2>
                    <p class="company-name">{self._extract_job_data(job).get('employer_name', 'Company')}</p>
                    <p class="location">{self._extract_job_data(job).get('job_city', 'Location')}, {self._extract_job_data(job).get('job_country', '')}</p>
                    <p class="salary">Salary: {self._format_salary(self._extract_job_data(job).get('job_min_salary'), self._extract_job_data(job).get('job_max_salary'), self._extract_job_data(job).get('job_salary_period', ''))}</p>
                    <div class="description">
                        <h3>Job Description:</h3>
                        <p>{self._extract_job_data(job).get('job_description', 'No description available')}</p>
                    </div>
                    <div class="requirements">
                        <h3>Required Skills:</h3>
                        <ul>
                            {self._format_skills_list(self._extract_job_data(job).get('job_required_skills', []))}
                        </ul>
                    </div>
                    <p class="match-percentage">Skill Match: {job.get('analysis', {}).get('skill_match_percentage', 0)}%</p>
                    <a href="{self._extract_job_data(job).get('job_apply_link', '#')}" class="apply-link" target="_blank">Apply Now</a>
                </div>
                ''' for job in applications)}
                
                <div class="footer">
                    <p>This is an automated job alert. You can manage your preferences in the job alert settings.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    def _format_salary(self, min_salary, max_salary, period, currency="USD"):
        """Format salary information for display"""
        if not min_salary and not max_salary:
            return "Salary not specified"
        
        # Format the salary range
        if min_salary and max_salary:
            salary = f"{currency} {min_salary:,.0f} - {max_salary:,.0f}"
        elif min_salary:
            salary = f"{currency} {min_salary:,.0f}+"
        else:
            salary = f"Up to {currency} {max_salary:,.0f}"
        
        # Add period if specified
        if period:
            period = period.lower()
            if period == "yearly":
                salary += " per year"
            elif period == "monthly":
                salary += " per month"
            elif period == "weekly":
                salary += " per week"
            elif period == "daily":
                salary += " per day"
            elif period == "hourly":
                salary += " per hour"
        
        return salary
    
    def _format_skills_list(self, skills):
        """Format a list of skills as HTML list items"""
        if not skills:
            return "<li>Skills not specified</li>"
        
        html = ""
        for skill in skills:
            html += f"<li>{skill}</li>"
        
        return html
    
    def _format_requirements_list(self, requirements):
        """Format a list of requirements as HTML list items"""
        if not requirements:
            return "<li>Requirements not specified</li>"
        
        html = ""
        for req in requirements:
            html += f"<li>{req}</li>"
        
        return html
    
    def _get_email_template_header(self):
        """Get HTML email template header with CSS styling"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Job Opportunities</title>
            <style>
                body {
                    font-family: Arial, Helvetica, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #fff;
                }
                .header {
                    text-align: center;
                    padding: 20px;
                    background-color: #0066cc;
                    color: white;
                    border-radius: 5px 5px 0 0;
                }
                .footer {
                    text-align: center;
                    padding: 15px;
                    font-size: 14px;
                    color: #666;
                    border-top: 1px solid #eee;
                    margin-top: 30px;
                }
                .job-card {
                    margin: 25px 0;
                    padding: 20px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    background-color: #fff;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                .job-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 10px;
                    margin-bottom: 10px;
                }
                .job-header h2 {
                    margin: 0;
                    color: #0066cc;
                    font-size: 22px;
                }
                .job-company {
                    font-size: 18px;
                    color: #444;
                    margin-bottom: 10px;
                }
                .job-meta {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 15px;
                    margin: 15px 0;
                    color: #666;
                }
                .job-meta > div {
                    display: flex;
                    align-items: center;
                }
                .icon {
                    margin-right: 5px;
                }
                .job-description {
                    margin: 15px 0;
                    padding: 10px;
                    background-color: #f9f9f9;
                    border-left: 3px solid #0066cc;
                }
                .job-columns {
                    display: flex;
                    gap: 20px;
                    margin: 20px 0;
                }
                .job-skills, .job-requirements {
                    flex: 1;
                    background-color: #f9f9f9;
                    padding: 15px;
                    border-radius: 5px;
                }
                .job-footer {
                    margin-top: 20px;
                    padding-top: 15px;
                    border-top: 1px solid #eee;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-wrap: wrap;
                }
                .explanation {
                    flex: 1;
                    margin-right: 20px;
                }
                .badge {
                    padding: 5px 10px;
                    border-radius: 15px;
                    font-size: 14px;
                    font-weight: bold;
                }
                .match-score {
                    background-color: #e3f2fd;
                    color: #0066cc;
                }
                .apply-button {
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #0066cc;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    text-align: center;
                }
                .apply-button:hover {
                    background-color: #0052a3;
                }
                .cover-letter {
                    margin: 20px 0;
                    padding: 15px;
                    background-color: #f9f9f9;
                    border: 1px dashed #ccc;
                    border-radius: 5px;
                }
                .cover-letter-content {
                    white-space: pre-line;
                    line-height: 1.5;
                }
                ul.skills-list, ul.requirements-list {
                    padding-left: 20px;
                }
                li {
                    margin-bottom: 5px;
                }
                h3 {
                    color: #0066cc;
                    margin: 10px 0;
                }
                @media (max-width: 600px) {
                    .job-columns {
                        flex-direction: column;
                    }
                    .job-footer {
                        flex-direction: column;
                        align-items: flex-start;
                    }
                    .apply-button {
                        margin-top: 15px;
                        width: 100%;
                    }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Job Opportunities</h1>
                    <p>Here are new job opportunities that match your skills and preferences</p>
                </div>
        """
    
    def _get_email_template_footer(self):
        """Get HTML email template footer"""
        return """
                <div class="footer">
                    <p><em>Note: Cover letters are AI-generated suggestions. Please review and personalize before using.</em></p>
                    <p>Generated on: {}</p>
                </div>
            </div>
        </body>
        </html>
        """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) 