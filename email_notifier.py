import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("email_notifier")

load_dotenv()

def send_job_notification(jobs):
    """
    Send email notification with new job listings
    
    Args:
        jobs (list): List of job dictionaries to notify about
    """
    if not jobs:
        logger.info("No new jobs to notify about")
        return
    
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_PASSWORD")
    recipient_email = os.getenv("EMAIL_RECIPIENT")
    
    if not all([sender_email, sender_password, recipient_email]):
        logger.error("Email configuration is missing in .env file")
        return
    
    # Create email message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🚨 {len(jobs)} New Job Opportunities Found!"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    # Create HTML content for the email
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .job-listing {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
            .job-title {{ font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }}
            .company {{ font-size: 16px; color: #3498db; margin-bottom: 5px; }}
            .location {{ color: #7f8c8d; margin-bottom: 5px; }}
            .salary {{ color: #27ae60; font-weight: bold; margin-bottom: 10px; }}
            .description {{ margin-bottom: 10px; }}
            .apply-btn {{ background-color: #3498db; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; display: inline-block; }}
            .apply-btn:hover {{ background-color: #2980b9; }}
        </style>
    </head>
    <body>
        <h1>New Job Listings Alert!</h1>
        <p>We found {len(jobs)} new job opportunities that match your criteria:</p>
    """
    
    for job in jobs:
        html_content += f"""
        <div class="job-listing">
            <div class="job-title">{job.get('job_title', 'Untitled Position')}</div>
            <div class="company">🏢 {job.get('employer_name', 'Unknown Company')}</div>
            <div class="location">📍 {job.get('job_city', '')} {job.get('job_state', '')} {job.get('job_country', '')}</div>
            <div class="salary">💰 {job.get('job_min_salary', '?')} - {job.get('job_max_salary', '?')} {job.get('job_salary_currency', 'USD')}</div>
            <div class="description">{job.get('job_description', '')[:300]}...</div>
            <a href="{job.get('job_apply_link', '#')}" class="apply-btn">Apply Now</a>
        </div>
        """
    
    html_content += """
        <p>Good luck with your job search!</p>
        <p>- Your Job Search Assistant</p>
    </body>
    </html>
    """
    
    # Attach HTML content
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        # Connect to SMTP server and send email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        logger.info(f"Email notification sent for {len(jobs)} new jobs")
        return True
    except Exception as e:
        logger.error(f"Failed to send email notification: {str(e)}")
        return False 