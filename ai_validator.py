import requests
import os

# Get the API key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# Simple fallback for common cases
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

def validate_word(category: str, letter: str, word: str) -> tuple[bool, str]:
    """
    Call Gemini API to check if a word fits the category and starts with the letter.
    Returns (is_valid, explanation).
    """
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY not set in environment variables")

    # Normalize inputs
    letter = letter.upper()
    word = word.strip().lower()

    # Local check: ensure word starts with the letter
    if not word.startswith(letter.lower()):
        return False, f"'{word}' does not start with '{letter}'"

    # Fallback check
    if category in FALLBACK_VALIDATIONS and letter in FALLBACK_VALIDATIONS[category]:
        is_valid = word.lower() == FALLBACK_VALIDATIONS[category][letter].lower()
        explanation = "Matches fallback example" if is_valid else f"Not the expected '{FALLBACK_VALIDATIONS[category][letter]}'"
        return is_valid, explanation

    headers = {"Content-Type": "application/json"}
    
    prompt = (
        f"Is '{word}' a valid example of the category '{category}' and does it start with '{letter}'? "
        f"Respond with 'yes' or 'no', followed by a short explanation (max 20 words)."
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()

        if "candidates" in result and result["candidates"]:
            text_response = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Split response into validity and explanation
            parts = text_response.split(",", 1)
            is_valid = parts[0].strip().lower() == "yes"
            explanation = parts[1].strip() if len(parts) > 1 else ("Valid" if is_valid else "Invalid")
            print(f"Gemini response for {category}/{letter}/{word}: {text_response}")
            return is_valid, explanation
        
        return False, "No clear response from API"
    except requests.RequestException as e:
        print(f"Error calling Gemini API for {category}/{letter}/{word}: {e}")
        return False, f"API error: {str(e)}"