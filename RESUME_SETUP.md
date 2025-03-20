# Resume and Job Application Setup

This document explains how to set up and use the resume submission feature in the Job Alert System.

## Overview

The Job Alert System now includes functionality to prepare job application packages, including:

1. Customized cover letters for each job
2. Your resume
3. Job details for reference
4. Application metadata for tracking

## Setup

### 1. Upload Your Resume

Place your resume PDF file in the `resume/` directory. The current configuration is looking for:
```
resume/Resume (1).pdf
```

### 2. Configure Your Settings

In your `.env` file, the following settings control the job application feature:

```
# Resume Settings
RESUME_PATH=resume/Resume (1).pdf
AUTO_SUBMIT_APPLICATIONS=true
COVER_LETTER_TEMPLATE=resume/cover_letter_template.txt
```

- `RESUME_PATH`: Path to your resume file
- `AUTO_SUBMIT_APPLICATIONS`: Set to `true` to automatically prepare application packages for new jobs
- `COVER_LETTER_TEMPLATE`: Path to your cover letter template

### 3. Customize Your Cover Letter Template

Edit `resume/cover_letter_template.txt` to customize your cover letter. The template uses placeholders that will be automatically filled in:

- `{{COMPANY_NAME}}`: The company name from the job listing
- `{{JOB_TITLE}}`: The job title
- `{{SKILLS_MATCHED}}`: Skills from the job that match your profile
- `{{CUSTOM_PARAGRAPH}}`: AI-generated paragraph specific to the job
- `{{COMPANY_REASON}}`: Reason for interest in the company
- `{{CANDIDATE_NAME}}`: Your name from the .env file
- `{{CANDIDATE_EMAIL}}`: Your email
- `{{CANDIDATE_PHONE}}`: Your phone number
- `{{CANDIDATE_LINKEDIN}}`: Your LinkedIn profile URL

## How It Works

1. When the Job Alert System finds new jobs, it will:
   - Create a folder for each application in the `applications/` directory
   - Generate a customized cover letter based on the job details
   - Copy your resume to the application folder
   - Save the job details and application metadata

2. Each application folder contains:
   - Your resume
   - A customized cover letter
   - The job details in JSON format
   - Application metadata (including the application link)

3. Application folders are named using the format: `company_date_jobid`

## Using the Application Packages

For each prepared application, you'll find:

1. **The application link**: Stored in the metadata.json file as `apply_link`
2. **A customized cover letter**: Named `cover_letter_company.txt`
3. **Your resume**: A copy of your original resume

To apply to the job:
1. Open the application folder
2. Visit the application link in your browser
3. Upload your resume and cover letter as requested by the employer
4. Complete any additional application steps

## Command Line Options

To use the resume submission feature:

```bash
# Run once with auto-application preparation
python job_alert.py --run-once

# Run continuously (checks at intervals defined in .env)
python job_alert.py
``` 