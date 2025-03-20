# Setting Up Email Notifications

This guide will help you set up and test email notifications for your Job Alert System.

## Gmail Setup (Recommended)

The job alert system is configured to work with Gmail by default. To set up Gmail for sending notifications:

1. **Create a Gmail App Password**:
   - Google no longer allows regular passwords for app access
   - Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
   - Sign in with your Google account
   - Select "App" and choose "Other (Custom name)"
   - Enter "Job Alert System" and click "Generate"
   - Google will display a 16-character app password (four groups of four characters)
   - Copy this password for the next step

2. **Configure Email Settings**:
   ```bash
   # Set your email address
   python configure_email.py --set-sender "your.email@gmail.com"
   
   # Set your Gmail app password (the 16-character password from step 1)
   python configure_email.py --set-password "xxxx xxxx xxxx xxxx"
   
   # Set recipient email (if different from sender)
   python configure_email.py --set-recipient "recipient@example.com"
   ```

3. **Test Email Settings**:
   ```bash
   # Send a test email to verify your settings
   python configure_email.py --send-test
   ```

4. **Enable Email Sending**:
   ```bash
   # Once your test is successful, enable email notifications
   python configure_email.py --enable-emails
   ```

## Non-Gmail Setup

If you're using a different email provider:

1. **Update SMTP Settings**:
   - Open your `.env` file
   - Update the SMTP settings for your provider:
     ```
     SMTP_SERVER=your.smtp.server
     SMTP_PORT=587  # or your provider's port
     ```

2. **Configure Email Settings**:
   - Follow the same steps as Gmail setup above
   - Make sure to use the correct login credentials for your provider

## Troubleshooting

### Authentication Errors

- **Gmail Users**: Make sure you're using an App Password, not your regular Gmail password
- Verify that 2-Step Verification is enabled on your Google account (required for App Passwords)
- Check for typos in your email address and password

### Connection Errors

- Verify your internet connection
- Check if your email provider's SMTP server is correct
- Some networks block outgoing SMTP traffic; try on a different network

### Running in Dry Run Mode

To avoid sending actual emails during testing:

```bash
# Disable email sending (dry run mode)
python configure_email.py --disable-emails

# Run with explicit dry run flag
python job_alert.py --run-once --dry-run
```

## Verifying Current Settings

```bash
# Check your current email configuration
python configure_email.py --show-settings
``` 