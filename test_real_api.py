#!/usr/bin/env python3
import os
import logging
from dotenv import load_dotenv
from bright_data_scraper import BrightDataScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("test_real_api")

# Load environment variables
load_dotenv()

def test_api_connectivity():
    """Test basic connectivity to the Bright Data API with a single call"""
    logger.info("Testing real API connectivity (not in test mode)")
    
    # Force test mode off
    os.environ["BRIGHTDATA_TEST_MODE"] = "false"
    
    # Initialize scraper with test mode off
    scraper = BrightDataScraper(test_mode=False)
    
    # Make a simple request to the test endpoint
    logger.info("Making request to test endpoint...")
    response = scraper._make_request(
        "https://geo.brdtest.com/welcome.txt?product=unlocker&method=api",
        format_type="raw"
    )
    
    if response:
        logger.info(f"Response received from API! First 100 characters: {response[:100]}")
        return True
    else:
        logger.error("Failed to get response from Bright Data API. Check your API key and connection.")
        return False

if __name__ == "__main__":
    success = test_api_connectivity()
    if success:
        print("API test successful! Your Bright Data API key is working correctly.")
    else:
        print("API test failed. Please check your API key and internet connection.") 