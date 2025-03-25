#!/usr/bin/env python3
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("error_notifier")

# Load environment variables
load_dotenv()

class ErrorNotifier:
    """
    A class to handle error notifications via email or other channels
    """
    
    def __init__(self):
        """
        Initialize the ErrorNotifier with configuration settings
        """
        self.admin_email = os.getenv("ADMIN_EMAIL")
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.email_from = os.getenv("EMAIL_FROM")
        
        # Check if email notifications are enabled
        self.enabled = (
            self.admin_email is not None and 
            self.smtp_server is not None and
            self.smtp_username is not None and
            self.smtp_password is not None and
            self.email_from is not None
        )
        
        if not self.enabled:
            logger.warning("Error notifier email notifications are disabled due to missing configuration")
    
    def notify(self, error_message, severity="ERROR"):
        """
        Send a notification about an error
        
        Args:
            error_message (str): The error message to send
            severity (str): The severity level of the error (ERROR, WARNING, etc.)
        
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        # Log the error
        logger.error(f"{severity}: {error_message}")
        
        # Send email notification if enabled
        if self.enabled and self.admin_email:
            return self._send_email_notification(error_message, severity)
        
        return False
    
    def _send_email_notification(self, error_message, severity):
        """
        Send an email notification about an error
        
        Args:
            error_message (str): The error message to send
            severity (str): The severity level of the error
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Create the email
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = self.admin_email
            msg['Subject'] = f"Job Bot {severity}: An error occurred"
            
            # Email body
            body = f"""
            <html>
                <body>
                    <h2>Job Bot Error Notification</h2>
                    <p><strong>Severity:</strong> {severity}</p>
                    <p><strong>Error:</strong> {error_message}</p>
                    <p>Please check the logs for more details.</p>
                </body>
            </html>
            """
            msg.attach(MIMEText(body, 'html'))
            
            # Send the email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Error notification email sent to {self.admin_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send error notification email: {str(e)}")
            return False


# For testing
if __name__ == "__main__":
    notifier = ErrorNotifier()
    notifier.notify("This is a test error message") 