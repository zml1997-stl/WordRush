import requests
import os

# Get the API key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# Simple fallback for common cases (expand as needed)
FALLBACK_VALIDATIONS = {
    "Fruit": {"A": "Apple", "B": "Banana", "C": "Cherry"},
    "Country": {"A": "Australia", "B": "Brazil", "C": "Canada"},
    "Animal": {"A": "Ant", "B": "Bear", "C": "Cat"},
    "City": {"A": "Amsterdam", "B": "Boston", "C": "Cairo"},
    "Hat": {"A": "Aviator", "B": "Baseball cap", "C": "Cap"},
    "TV Show": {"A": "Avatar", "B": "Breaking Bad", "C": "Cheers"},
    "Toy": {"A": "Action Figure", "B": "Blocks", "C": "Car"},
    "Electronics": {"A": "Amplifier", "B": "Bedside alarm", "C": "Calculator"},
    "Dance": {"A": "Allemande", "B": "Break dance", "C": "Cha-cha"},
    "Director": {"A": "Anderson", "B": "Burton", "C": "Coppola"},
    "Star": {"A": "Altair", "B": "Betelgeuse", "C": "Canopus"},
    "Villain": {"A": "Ares", "B": "Bane", "C": "Catwoman"},
    "Play": {"A": "Antigone", "B": "Becket", "C": "Cyrano"}
}

def validate_word(category: str, letter: str, word: str) -> bool:
    """
    Call Gemini API to check if a word fits the category and starts with the letter.
    Returns True if valid, False otherwise.
    """
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY not set in environment variables")

    # Normalize inputs
    letter = letter.upper()
    word = word.strip().lower()

    # Local check: ensure word starts with the letter
    if not word.startswith(letter.lower()):
        return False

    # Fallback check to reduce API calls
    if category in FALLBACK_VALIDATIONS and letter in FALLBACK_VALIDATIONS[category]:
        return word.lower() == FALLBACK_VALIDATIONS[category][letter].lower()

    headers = {
        "Content-Type": "application/json"
    }
    
    # Improved prompt for clarity and consistency
    prompt = (
        f"Is '{word}' a valid example of the category '{category}' and does it start with the letter '{letter}'? "
        f"Respond only with 'yes' or 'no'."
    )
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()

        # Extract and normalize text response
        if "candidates" in result and result["candidates"]:
            text_response = result["candidates"][0]["content"]["parts"][0]["text"].strip().lower()
            print(f"Gemini response for {category}/{letter}/{word}: {text_response}")  # Debug
            return text_response == "yes"
        
        print(f"No valid response for {category}/{letter}/{word}")
        return False  # Default to invalid if response is unclear
    except requests.RequestException as e:
        print(f"Error calling Gemini API for {category}/{letter}/{word}: {e}")
        return False  # Default to invalid if API fails