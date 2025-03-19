import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailNotifier:
    def __init__(self):
        """Initialize email notifier with SMTP settings"""
        load_dotenv()
        
        # Load email settings
        self.sender_email = os.getenv("EMAIL_SENDER")
        self.sender_password = os.getenv("EMAIL_PASSWORD")
        self.recipient_email = os.getenv("EMAIL_RECIPIENT", self.sender_email)
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        
        if not all([self.sender_email, self.sender_password, self.recipient_email]):
            raise ValueError("Email settings not properly configured in .env file")
    
    def send_job_notifications(self, applications):
        """
        Send email notifications for new job applications
        
        Args:
            applications (list): List of job application packages
        """
        if not applications:
            logger.info("No applications to send notifications for")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = self.recipient_email
            msg["Subject"] = f"New Job Opportunities ({len(applications)} matches) - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Build email body
            body = self._build_email_body(applications)
            msg.attach(MIMEText(body, "html"))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Successfully sent notifications for {len(applications)} jobs")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email notifications: {str(e)}")
            return False
    
    def _build_email_body(self, applications):
        """
        Build HTML email body from job applications
        
        Args:
            applications (list): List of job application packages
            
        Returns:
            str: HTML formatted email body
        """
        html = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                .job { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
                .job h2 { color: #2c5282; margin: 0 0 10px 0; }
                .company { color: #4a5568; font-size: 1.1em; }
                .location { color: #718096; }
                .salary { color: #48bb78; font-weight: bold; }
                .match { color: #4299e1; }
                .requirements { margin: 10px 0; }
                .apply-button {
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #4299e1;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 10px;
                }
                .cover-letter {
                    margin-top: 15px;
                    padding: 10px;
                    background-color: #f7fafc;
                    border-left: 4px solid #4299e1;
                }
            </style>
        </head>
        <body>
            <h1>New Job Opportunities</h1>
            <p>Here are new job opportunities that match your criteria:</p>
        """
        
        for app in applications:
            job = app['job_data']
            analysis = app['analysis']
            
            # Format salary information
            salary = self._format_salary(
                job.get('job_min_salary', 0),
                job.get('job_max_salary', 0),
                job.get('job_salary_period', ''),
                job.get('job_salary_currency', 'USD')
            )
            
            html += f"""
            <div class="job">
                <h2>{job.get('job_title', 'Position')}</h2>
                <div class="company">{job.get('employer_name', 'Company')}</div>
                <div class="location">{job.get('job_city', '')} {job.get('job_country', '')}</div>
                <div class="salary">{salary}</div>
                <div class="match">Match Score: {analysis.get('skill_match_percentage', 'N/A')}%</div>
                
                <div class="requirements">
                    <strong>Key Requirements:</strong>
                    <ul>
                        {''.join(f'<li>{req}</li>' for req in analysis.get('key_requirements', []))}
                    </ul>
                </div>
                
                <div>{analysis.get('explanation', '')}</div>
                
                <div class="cover-letter">
                    <strong>Suggested Cover Letter:</strong><br>
                    {app['materials'].get('cover_letter', 'Cover letter not generated').replace('\n', '<br>')}
                </div>
                
                <a href="{job.get('job_apply_link', '#')}" class="apply-button" target="_blank">Apply Now</a>
            </div>
            """
        
        html += """
            <p>
                <em>Note: Cover letters are AI-generated suggestions and should be reviewed and personalized before use.</em>
            </p>
        </body>
        </html>
        """
        
        return html
    
    def _format_salary(self, min_salary, max_salary, period, currency):
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