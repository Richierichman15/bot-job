#!/usr/bin/env python3
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('email_notifications.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Email configuration
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "gitonga.r.nyaga@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "tzulgzwnsdcpqgsw")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", EMAIL_SENDER)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_DRY_RUN = os.getenv("EMAIL_DRY_RUN", "true").lower() in ["true", "1", "yes", "t"]

def send_email_notification(data_dict, subject=None, dry_run=None):
    """
    Sends an email notification with the data details
    
    Args:
        data_dict: Dictionary containing the information to include in email
        subject: Optional custom subject line (default will be constructed from data)
        dry_run: Override environment dry run setting if provided
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Check if we should use dry run mode
    use_dry_run = EMAIL_DRY_RUN if dry_run is None else dry_run
    
    # Validate required settings
    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
        logger.error("Missing email configuration. Check your .env file.")
        if not use_dry_run:
            return False
        # Continue in dry run mode
        use_dry_run = True
        logger.warning("Forcing dry run mode due to missing configuration.")
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        
        # Use custom subject or construct from data
        if subject:
            msg['Subject'] = subject
        else:
            # Use a field from data_dict for subject, or fallback to default
            some_field = data_dict.get('some_field', 'New Notification')
            msg['Subject'] = f"Notification: {some_field}"
        
        # Create email body
        body = f"""
        Email Notification
        -----------------
        
        {data_dict.get('field1', 'N/A')}
        {data_dict.get('field2', 'N/A')}
        {data_dict.get('field3', 'N/A')}
        """
        
        # Add any additional fields in data_dict
        additional_fields = [f"{key}: {value}" for key, value in data_dict.items() 
                            if key not in ['field1', 'field2', 'field3', 'some_field']]
        
        if additional_fields:
            body += "\nAdditional Information:\n" + "\n".join(additional_fields)
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Handle dry run mode
        if use_dry_run:
            logger.info(f"[DRY RUN] Would send email to {EMAIL_RECIPIENT}")
            logger.info(f"[DRY RUN] Subject: {msg['Subject']}")
            logger.info(f"[DRY RUN] Body: {body}")
            return True
        
        # Connect to the server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.ehlo()
        
        # Debug the authentication
        print(f"Attempting to login with: {EMAIL_SENDER}, password length: {len(EMAIL_PASSWORD)}")
        # Login
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        
        # If not dry run, send the email
        if not use_dry_run:
            # Send the email
            server.send_message(msg)
            logger.info(f"Email sent to {EMAIL_RECIPIENT}")
        
        # Close the connection
        server.quit()
        
        # Return success
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed. Check your email and password. Error details: {e}")
        logger.error("For Gmail, use an App Password: https://myaccount.google.com/apppasswords")
        return False
        
    except smtplib.SMTPConnectError:
        logger.error(f"Failed to connect to SMTP server {SMTP_SERVER}:{SMTP_PORT}")
        return False
        
    except Exception as e:
        logger.error(f"Failed to send email notification: {str(e)}")
        return False

def send_html_notification(data_dict, subject=None, html_template=None, dry_run=None):
    """
    Sends an HTML email notification with the data details
    
    Args:
        data_dict: Dictionary containing the information to include in email
        subject: Optional custom subject line
        html_template: Optional HTML template string with {field} placeholders
        dry_run: Override environment dry run setting if provided
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Check if we should use dry run mode
    use_dry_run = EMAIL_DRY_RUN if dry_run is None else dry_run
    
    # Validate required settings
    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
        logger.error("Missing email configuration. Check your .env file.")
        if not use_dry_run:
            return False
        # Continue in dry run mode
        use_dry_run = True
        logger.warning("Forcing dry run mode due to missing configuration.")
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        
        # Use custom subject or construct from data
        if subject:
            msg['Subject'] = subject
        else:
            # Use a field from data_dict for subject, or fallback to default
            some_field = data_dict.get('some_field', 'New Notification')
            msg['Subject'] = f"Notification: {some_field}"
        
        # Create HTML body using template or default format
        if html_template:
            # Use the provided template and fill in values from data_dict
            try:
                html_body = html_template.format(**data_dict)
            except KeyError as e:
                logger.warning(f"Template key error: {e}. Using default template.")
                html_body = default_html_template(data_dict)
        else:
            html_body = default_html_template(data_dict)
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Handle dry run mode
        if use_dry_run:
            logger.info(f"[DRY RUN] Would send HTML email to {EMAIL_RECIPIENT}")
            logger.info(f"[DRY RUN] Subject: {msg['Subject']}")
            logger.info(f"[DRY RUN] HTML Body length: {len(html_body)} characters")
            return True
        
        # Connect to server and send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Enable TLS encryption
            
            # Attempt login
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            
            # Send message
            server.send_message(msg)
            
            logger.info(f"HTML email sent successfully to {EMAIL_RECIPIENT}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to send HTML email notification: {str(e)}")
        return False

def default_html_template(data_dict):
    """Generates a default HTML template for the email"""
    # Create table rows for all data fields
    table_rows = ""
    for key, value in data_dict.items():
        table_rows += f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>"
    
    return f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            table, th, td {{ border: 1px solid #ddd; }}
            th, td {{ padding: 12px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .header {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .footer {{ margin-top: 30px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Notification</h2>
                <p>You have received a new notification.</p>
            </div>
            
            <table>
                <tr>
                    <th>Field</th>
                    <th>Value</th>
                </tr>
                {table_rows}
            </table>
            
            <div class="footer">
                <p>This is an automated notification. Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

def configure_email(sender=None, password=None, recipient=None, dry_run=None):
    """Configure email settings."""
    global EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT, EMAIL_DRY_RUN
    
    # Only update if provided
    if sender:
        EMAIL_SENDER = sender
    if password:
        EMAIL_PASSWORD = password
    if recipient:
        EMAIL_RECIPIENT = recipient
    if dry_run is not None:
        EMAIL_DRY_RUN = dry_run
    
    # Log configuration (mask password)
    logging.info(f"Email configured with: sender={EMAIL_SENDER}, " +
                 f"recipient={EMAIL_RECIPIENT}, dry_run={EMAIL_DRY_RUN}")
    
    # Return current configuration (excluding password)
    return {
        "sender": EMAIL_SENDER,
        "recipient": EMAIL_RECIPIENT,
        "smtp_server": SMTP_SERVER,
        "smtp_port": SMTP_PORT,
        "dry_run": EMAIL_DRY_RUN
    }

def send_job_notification(jobs, subject=None, dry_run=None):
    """
    Sends an email notification with job details
    
    Args:
        jobs: List of job dictionaries with job details
        subject: Optional custom subject line
        dry_run: Override environment dry run setting if provided
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Check if we should use dry run mode
    use_dry_run = EMAIL_DRY_RUN if dry_run is None else dry_run
    
    # Validate job data
    if not jobs:
        logger.warning("No jobs provided for notification")
        return True
    
    # Validate required settings
    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
        logger.error("Missing email configuration. Check your .env file.")
        if not use_dry_run:
            return False
        # Continue in dry run mode
        use_dry_run = True
        logger.warning("Forcing dry run mode due to missing configuration.")
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        
        # Use custom subject or construct from data
        if subject:
            msg['Subject'] = subject
        else:
            msg['Subject'] = f"Job Alert: {len(jobs)} New Job Opportunities"
        
        # Create HTML email body
        html_body = job_notification_template(jobs)
        msg.attach(MIMEText(html_body, 'html'))
        
        # Handle dry run mode
        if use_dry_run:
            logger.info(f"[DRY RUN] Would send job notification email to {EMAIL_RECIPIENT}")
            logger.info(f"[DRY RUN] Subject: {msg['Subject']}")
            
            # Log job information
            for i, job in enumerate(jobs, 1):
                logger.info(f"[DRY RUN] Job {i}: {job.get('job_title', 'Untitled')} at {job.get('employer_name', 'Unknown')}")
                logger.info(f"[DRY RUN]   Location: {job.get('job_city', 'N/A')}, {job.get('job_country', 'N/A')}")
                logger.info(f"[DRY RUN]   Salary: {_format_salary(job.get('job_min_salary'), job.get('job_max_salary'), job.get('job_salary_period', ''))}")
                if 'job_apply_link' in job:
                    logger.info(f"[DRY RUN]   Apply: {job.get('job_apply_link')}")
                logger.info("---")
                
            return True
        
        # Connect to server and send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Enable TLS encryption
            
            # Attempt login
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            
            # Send message
            server.send_message(msg)
            
            logger.info(f"Job notification email sent successfully to {EMAIL_RECIPIENT}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to send job notification email: {str(e)}")
        return False

def job_notification_template(jobs):
    """
    Generates an HTML template for job notification emails
    
    Args:
        jobs: List of job dictionaries
        
    Returns:
        str: HTML template for the email
    """
    # Generate job cards for each job
    job_cards = ""
    for job in jobs:
        # Format salary
        salary = _format_salary(
            job.get('job_min_salary'),
            job.get('job_max_salary'),
            job.get('job_salary_period', '')
        )
        
        # Get job description preview
        description = job.get('job_description', '')
        if description and len(description) > 150:
            description = description[:150] + "..."
        
        # Create skills list
        skills_html = ""
        if job.get('job_required_skills'):
            for skill in job.get('job_required_skills'):
                skills_html += f"<li>{skill}</li>"
        
        # Create job card
        job_cards += f"""
        <div class="job-card">
            <h2 class="job-title">{job.get('job_title', 'Job Opening')}</h2>
            <div class="company">{job.get('employer_name', 'Company')}</div>
            <div class="job-meta">
                <div class="location">
                    <i class="icon">📍</i> {job.get('job_city', 'Location')}, {job.get('job_country', '')}
                </div>
                <div class="salary">
                    <i class="icon">💰</i> {salary}
                </div>
                <div class="job-type">
                    <i class="icon">⏱️</i> {job.get('job_employment_type', 'Not specified')}
                </div>
            </div>
            <div class="description">
                <h3>Description</h3>
                <p>{description}</p>
            </div>
            <div class="skills">
                <h3>Skills</h3>
                <ul class="skills-list">
                    {skills_html or "<li>Not specified</li>"}
                </ul>
            </div>
            <div class="job-actions">
                <a href="{job.get('job_apply_link', '#')}" class="apply-button">Apply Now</a>
            </div>
        </div>
        """
    
    # Assemble the complete email template
    return f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f5f5f5; margin: 0; padding: 0; }}
            .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #0066cc; padding: 20px; border-radius: 5px 5px 0 0; color: white; text-align: center; }}
            .header h1 {{ margin: 0; padding: 0; font-size: 24px; }}
            .content {{ background-color: white; padding: 20px; border-radius: 0 0 5px 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .job-card {{ margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; background-color: #fff; }}
            .job-title {{ margin: 0 0 10px 0; color: #0066cc; font-size: 22px; }}
            .company {{ font-size: 18px; color: #444; margin-bottom: 10px; }}
            .job-meta {{ display: flex; flex-wrap: wrap; gap: 15px; margin: 15px 0; color: #666; }}
            .job-meta > div {{ display: flex; align-items: center; }}
            .icon {{ margin-right: 5px; }}
            .description {{ margin: 15px 0; }}
            .skills {{ margin: 15px 0; }}
            .skills-list {{ padding-left: 20px; }}
            .skills-list li {{ margin-bottom: 5px; }}
            .job-actions {{ margin-top: 20px; }}
            .apply-button {{ display: inline-block; padding: 10px 20px; background-color: #0066cc; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 14px; text-align: center; }}
            @media (max-width: 600px) {{
                .job-meta {{ flex-direction: column; gap: 10px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>New Job Opportunities</h1>
                <p>We've found {len(jobs)} new job opportunities that match your criteria.</p>
            </div>
            <div class="content">
                {job_cards}
                <div class="footer">
                    <p>This is an automated notification from your Job Alert System.</p>
                    <p>To manage your job search preferences, check your settings in the application.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

def _format_salary(min_salary, max_salary, period="", currency="USD"):
    """
    Format salary information for display
    
    Args:
        min_salary: Minimum salary value
        max_salary: Maximum salary value
        period: Salary period (yearly, monthly, hourly, etc.)
        currency: Currency code
        
    Returns:
        str: Formatted salary string
    """
    if not min_salary and not max_salary:
        return "Salary not specified"
    
    # Format the salary range
    if min_salary and max_salary:
        if min_salary == max_salary:
            salary = f"{currency} {min_salary:,.0f}"
        else:
            salary = f"{currency} {min_salary:,.0f} - {max_salary:,.0f}"
    elif min_salary:
        salary = f"{currency} {min_salary:,.0f}+"
    else:
        salary = f"Up to {currency} {max_salary:,.0f}"
    
    # Add period if specified
    if period:
        period = period.lower()
        if period in ["yearly", "annual", "year", "annually"]:
            salary += " per year"
        elif period in ["monthly", "month"]:
            salary += " per month"
        elif period in ["weekly", "week"]:
            salary += " per week"
        elif period in ["daily", "day"]:
            salary += " per day"
        elif period in ["hourly", "hour"]:
            salary += " per hour"
    
    return salary

# Example usage
if __name__ == "__main__":
    # Example data
    data = {
        'some_field': 'Test Notification',
        'field1': 'This is a test notification',
        'field2': 'Testing email functionality',
        'field3': 'Complete',
        'timestamp': '2023-07-10 15:30:45'
    }
    
    # Send plain text email
    email_sent = send_email_notification(data, dry_run=True)
    
    # Send HTML email
    html_sent = send_html_notification(data, subject="HTML Test Notification", dry_run=True)
    
    # Optionally handle the result
    if email_sent and html_sent:
        print("Notifications sent successfully")
    else:
        print("Failed to send notifications") 