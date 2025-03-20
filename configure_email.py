#!/usr/bin/env python3
import os
import sys
import argparse
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv, set_key

def send_test_email(sender, password, recipient, smtp_server, smtp_port):
    """Send a test email to verify settings"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = "Job Alert System - Test Email"
        
        body = """
        <html>
        <body>
            <h2>Job Alert System - Test Email</h2>
            <p>This is a test email from your Job Alert System.</p>
            <p>If you're receiving this, your email settings are working correctly!</p>
            <hr>
            <p>Email configuration:</p>
            <ul>
                <li>Sender: {}</li>
                <li>Recipient: {}</li>
                <li>SMTP Server: {}</li>
                <li>SMTP Port: {}</li>
            </ul>
        </body>
        </html>
        """.format(sender, recipient, smtp_server, smtp_port)
        
        msg.attach(MIMEText(body, "html"))
        
        # Connect to server and send
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
            
        print(f"Test email sent successfully to {recipient}!")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("Error: SMTP authentication failed. Check your email and password.")
        print("For Gmail, use an App Password: https://myaccount.google.com/apppasswords")
        return False
        
    except Exception as e:
        print(f"Error sending test email: {str(e)}")
        return False

def update_env_file(key, value):
    """Directly update .env file to avoid quoted values"""
    env_file = ".env"
    
    # Read current file content
    try:
        with open(env_file, 'r') as file:
            lines = file.readlines()
    except:
        print(f"Error: Could not read {env_file}")
        return False
    
    # Flag to check if key was found and updated
    key_found = False
    
    # Create pattern to match the key
    pattern = re.compile(rf'^{key}\s*=.*$')
    
    # Update existing key or prepare to append
    with open(env_file, 'w') as file:
        for line in lines:
            if pattern.match(line):
                file.write(f"{key}={value}\n")
                key_found = True
            else:
                file.write(line)
    
    # Append key if not found
    if not key_found:
        with open(env_file, 'a') as file:
            file.write(f"\n{key}={value}\n")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Configure Email Settings")
    parser.add_argument("--enable-emails", action="store_true", 
                        help="Enable sending real emails (disable dry run mode)")
    parser.add_argument("--disable-emails", action="store_true", 
                        help="Disable sending real emails (enable dry run mode)")
    parser.add_argument("--set-password", type=str, 
                        help="Set email password (for Gmail, use App Password)")
    parser.add_argument("--set-sender", type=str, help="Set sender email address")
    parser.add_argument("--set-recipient", type=str, help="Set recipient email address")
    parser.add_argument("--show-settings", action="store_true", help="Show current email settings")
    parser.add_argument("--send-test", action="store_true", 
                        help="Send a test email to verify settings")
    
    args = parser.parse_args()
    
    # Load current settings
    load_dotenv()
    
    # Show current settings if requested
    if args.show_settings:
        print("\nCurrent Email Settings:")
        print(f"EMAIL_SENDER: {os.getenv('EMAIL_SENDER', 'Not set')}")
        print(f"EMAIL_RECIPIENT: {os.getenv('EMAIL_RECIPIENT', 'Not set')}")
        print(f"EMAIL_PASSWORD: {'Set' if os.getenv('EMAIL_PASSWORD') else 'Not set'}")
        print(f"SMTP_SERVER: {os.getenv('SMTP_SERVER', 'smtp.gmail.com')}")
        print(f"SMTP_PORT: {os.getenv('SMTP_PORT', '587')}")
        print(f"EMAIL_DRY_RUN: {os.getenv('EMAIL_DRY_RUN', 'true')}")
        print("\n")
    
    # Update settings based on arguments
    changes_made = False
    
    if args.enable_emails and args.disable_emails:
        print("Error: Cannot both enable and disable emails at the same time.")
        sys.exit(1)
    
    if args.enable_emails:
        os.environ["EMAIL_DRY_RUN"] = "false"
        update_env_file("EMAIL_DRY_RUN", "false")
        print("Email notifications enabled (dry run mode disabled)")
        changes_made = True
    
    if args.disable_emails:
        os.environ["EMAIL_DRY_RUN"] = "true"
        update_env_file("EMAIL_DRY_RUN", "true")
        print("Email notifications disabled (dry run mode enabled)")
        changes_made = True
    
    if args.set_password:
        os.environ["EMAIL_PASSWORD"] = args.set_password
        update_env_file("EMAIL_PASSWORD", args.set_password)
        print("Email password updated")
        changes_made = True
    
    if args.set_sender:
        os.environ["EMAIL_SENDER"] = args.set_sender
        update_env_file("EMAIL_SENDER", args.set_sender)
        print(f"Email sender set to: {args.set_sender}")
        changes_made = True
    
    if args.set_recipient:
        os.environ["EMAIL_RECIPIENT"] = args.set_recipient
        update_env_file("EMAIL_RECIPIENT", args.set_recipient)
        print(f"Email recipient set to: {args.set_recipient}")
        changes_made = True
    
    # Send test email if requested
    if args.send_test:
        sender = os.getenv("EMAIL_SENDER")
        password = os.getenv("EMAIL_PASSWORD")
        recipient = os.getenv("EMAIL_RECIPIENT", sender)
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        
        if not all([sender, password, recipient]):
            print("Error: Cannot send test email. Missing email settings.")
            print("Please set the following:")
            if not sender:
                print("  - EMAIL_SENDER (use --set-sender)")
            if not password:
                print("  - EMAIL_PASSWORD (use --set-password)")
            if not recipient:
                print("  - EMAIL_RECIPIENT (use --set-recipient)")
            return
        
        print(f"Sending test email from {sender} to {recipient}...")
        send_test_email(sender, password, recipient, smtp_server, smtp_port)
        changes_made = True
    
    if not changes_made and not args.show_settings:
        parser.print_help()
    
    # If enabling real emails, check if email settings are complete
    if args.enable_emails:
        sender = os.getenv("EMAIL_SENDER")
        password = os.getenv("EMAIL_PASSWORD")
        recipient = os.getenv("EMAIL_RECIPIENT")
        
        if not all([sender, password, recipient]):
            print("\nWarning: Email settings incomplete. Please set the following:")
            if not sender:
                print("  - EMAIL_SENDER (use --set-sender)")
            if not password:
                print("  - EMAIL_PASSWORD (use --set-password)")
            if not recipient:
                print("  - EMAIL_RECIPIENT (use --set-recipient)")
            print("\nFor Gmail, use an App Password: https://myaccount.google.com/apppasswords")
            print("Example: python configure_email.py --set-password 'xxxx xxxx xxxx xxxx'")

if __name__ == "__main__":
    main() 