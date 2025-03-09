import requests
import os

# Get the API key from environment variable (we'll set this in Heroku)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://api.google.com/gemini-2.0-flash/validate"  # Placeholder URL

def validate_word(category: str, letter: str, word: str) -> bool:
    """
    Call Gemini API to check if a word fits the category and starts with the letter.
    Returns True if valid, False otherwise.
    """
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY not set in environment variables")

    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "category": category,
        "letter": letter,
        "word": word
    }

    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result.get("is_valid", False)
    except requests.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        return False  # Default to invalid if API fails