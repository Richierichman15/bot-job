import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from .env
api_key = os.getenv("JSEARCH_API_KEY")
api_host = os.getenv("JSEARCH_API_HOST")

# Set up headers
headers = {
    'x-rapidapi-key': api_key,
    'x-rapidapi-host': api_host
}

# Simple test request to validate the API key
url = "https://jsearch.p.rapidapi.com/search?query=software%20developer%20in%20usa&page=1&num_pages=1"

print(f"Using API key: {api_key}")
print(f"Using API host: {api_host}")
print(f"Making request to: {url}")

try:
    response = requests.get(url, headers=headers)
    
    # Print status code
    print(f"Status code: {response.status_code}")
    
    # If successful, print some data
    if response.status_code == 200:
        data = response.json()
        print(f"API status: {data.get('status')}")
        print(f"Jobs found: {len(data.get('data', []))}")
        
        # Print the first job if available
        if data.get('data'):
            job = data.get('data')[0]
            print("\nFirst job details:")
            print(f"Title: {job.get('job_title')}")
            print(f"Company: {job.get('employer_name')}")
            print(f"Location: {job.get('job_city')}, {job.get('job_state')}")
    else:
        # Print error details
        print(f"Error response: {response.text}")
except Exception as e:
    print(f"Exception occurred: {str(e)}") 