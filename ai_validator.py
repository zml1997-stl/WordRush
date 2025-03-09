import requests
import os

# Get the API key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

def validate_word(category: str, letter: str, word: str) -> bool:
    """
    Call Gemini API to check if a word fits the category and starts with the letter.
    Returns True if valid, False otherwise.
    """
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY not set in environment variables")

    headers = {
        "Content-Type": "application/json"
    }
    
    prompt = f"Does the word '{word}' belong to the category '{category}' and start with the letter '{letter}'? Respond with 'yes' or 'no'."
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()

        # Extract text response from API output
        if "candidates" in result and result["candidates"]:
            text_response = result["candidates"][0]["content"]["parts"][0]["text"].strip().lower()
            return text_response == "yes"

        return False  # Default to invalid if response is unclear
    except requests.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        return False  # Default to invalid if API fails