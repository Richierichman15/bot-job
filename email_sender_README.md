# Email Sender Module

A flexible and reusable email sending module for Python applications. This module provides functions for sending plain text and HTML emails with robust error handling and configuration options.

## Features

- Send plain text emails
- Send HTML formatted emails
- Send job notification emails with a professional template
- Dry run mode for testing without sending actual emails
- Comprehensive error handling and logging
- Configuration via environment variables or programmatic API

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/your-repo.git

# Install dependencies
pip install python-dotenv
```

## Configuration

### Environment Variables

The email sender module uses the following environment variables:

```
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_RECIPIENT=recipient@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_DRY_RUN=true
```

Create a `.env` file in your project root with these variables.

### Gmail Setup (Recommended)

For Gmail, you'll need to:

1. Enable 2-Step Verification for your Google account
2. Generate an App Password at https://myaccount.google.com/apppasswords
3. Use the App Password in your `.env` file

## Usage

### Basic Usage

```python
from email_sender import send_email_notification

# Prepare data
data = {
    'field1': 'First important piece of information',
    'field2': 'Second important detail',
    'field3': 'Additional context'
}

# Send email
success = send_email_notification(data)

if success:
    print("Email sent successfully")
else:
    print("Failed to send email")
```

### HTML Emails

```python
from email_sender import send_html_notification

# Prepare data
data = {
    'title': 'Important Notification',
    'message': 'This is an important message',
    'details': 'Here are some additional details'
}

# Send HTML email with default template
success = send_html_notification(data)

# Or with custom template
custom_template = """
<html>
<body>
    <h1>{title}</h1>
    <p>{message}</p>
    <div>{details}</div>
</body>
</html>
"""

success = send_html_notification(data, html_template=custom_template)
```

### Job Notifications

```python
from email_sender import send_job_notification

# List of job data
jobs = [
    {
        "job_id": "job-1",
        "job_title": "Software Engineer",
        "employer_name": "Tech Company",
        "job_city": "San Francisco",
        "job_country": "USA",
        "job_min_salary": 120000,
        "job_max_salary": 150000,
        "job_salary_period": "yearly",
        "job_description": "Description of the job...",
        "job_required_skills": ["Python", "JavaScript", "React"],
        "job_apply_link": "https://example.com/apply/job-1",
        "job_employment_type": "FULLTIME"
    },
    # More jobs...
]

# Send job notification email
success = send_job_notification(jobs)
```

### Dry Run Mode

To test without sending actual emails:

```python
from email_sender import send_email_notification

# Force dry run mode
success = send_email_notification(data, dry_run=True)
```

### Programmatic Configuration

```python
from email_sender import configure_email, send_email_notification

# Configure email settings
configure_email(
    sender="your_email@gmail.com",
    password="your_app_password",
    recipient="recipient@example.com",
    dry_run=False
)

# Then send emails
success = send_email_notification(data)
```

## Testing

The module includes a test script:

```bash
# Test plain text email (dry run)
python test_email_sender.py

# Test HTML email (dry run)
python test_email_sender.py --type html

# Test job notification email (dry run)
python test_email_sender.py --type job --job-count 5

# Send a real email (use with caution!)
python test_email_sender.py --live
```

## Error Handling

The module provides comprehensive error handling for common email sending issues:

- Authentication failures
- Connection issues
- Invalid recipient addresses
- Configuration errors

All errors are logged to the console and to `email_notifications.log`. 