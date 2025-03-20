import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Direct credentials - this removes dotenv dependency for testing
sender = "gitonga.r.nyaga@gmail.com"
password = "tzulgzwnsdcpqgsw"  # App Password without spaces
recipient = "gitonga.r.nyaga@gmail.com"
smtp_server = "smtp.gmail.com"
smtp_port = 587

def test_email():
    """Simple email test function"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = "Simple Test Email from Python"
        
        # Add body
        body = "This is a test email sent from Python using direct credentials."
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect and send
        print(f"Connecting to {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        print("Starting TLS...")
        server.starttls()
        server.ehlo()
        
        print(f"Attempting login with: {sender}")
        server.login(sender, password)
        
        print("Sending email...")
        server.send_message(msg)
        server.quit()
        
        print("Email sent successfully!")
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_email() 