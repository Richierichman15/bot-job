#!/usr/bin/env python3
import os
from dotenv import load_dotenv

def test_openai():
    """Simple test of OpenAI API"""
    load_dotenv()
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"API key found: {api_key is not None}")
    
    # Try importing openai
    try:
        import openai
        print("OpenAI package imported successfully")
        
        # Set API key
        openai.api_key = api_key
        print("API key set")
        
        try:
            # Make a simple request using the new API
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello! Can you hear me?"}
                ],
                max_tokens=50
            )
            print(f"Response message: {response.choices[0].message.content}")
            return True
        except Exception as e:
            print(f"Error: {str(e)}")
            return False
            
    except ImportError:
        print("Failed to import openai")
        return False

if __name__ == "__main__":
    print("\nSimple OpenAI API Test\n" + "-" * 20)
    test_openai() 