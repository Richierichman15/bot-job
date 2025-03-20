#!/usr/bin/env python3
import os
import json
import logging
import openai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_openai_connection():
    """Test the OpenAI API connection"""
    load_dotenv()
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables")
        return False
    
    logger.info("OpenAI API key found, testing connection...")
    
    try:
        # Initialize client with the OpenAI API key
        openai.api_key = api_key
        
        # Make a simple test request
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello! Can you hear me? Please respond with a short message."}
            ],
            max_tokens=50
        )
        
        # Get response
        message = response.choices[0].message.content
        logger.info(f"OpenAI API test successful. Response: {message}")
        return True
        
    except Exception as e:
        logger.error(f"Error testing OpenAI API: {str(e)}")
        return False

def test_environment():
    """Test all environment variables"""
    load_dotenv()
    
    required_vars = [
        "JSEARCH_API_KEY",
        "JSEARCH_API_HOST",
        "OPENAI_API_KEY",
        "EMAIL_SENDER",
        "EMAIL_PASSWORD",
        "EMAIL_RECIPIENT",
        "SMTP_SERVER",
        "SMTP_PORT"
    ]
    
    # Check required variables
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        return False
    
    logger.info("All required environment variables found")
    return True

if __name__ == "__main__":
    print("\n=== Testing Environment Configuration ===")
    env_ok = test_environment()
    
    if env_ok:
        print("\n=== Testing OpenAI API Connection ===")
        openai_ok = test_openai_connection()
        
        if openai_ok:
            print("\n✅ All tests passed! Your environment is configured correctly.")
        else:
            print("\n❌ OpenAI API test failed. Please check your API key and connection.")
    else:
        print("\n❌ Environment test failed. Please check your .env file.") 