import requests
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

def validate_word(category: str, letter: str, word: str) -> tuple[bool, str]:
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY not set in environment variables")

    letter = letter.upper()
    word = word.strip().lower()

    if not word.startswith(letter.lower()):
        return False, f"'{word}' does not start with '{letter}'"

    headers = {"Content-Type": "application/json"}
    prompt = (
        f"Does '{word}' fit the category '{category}' in any common context (e.g., proper nouns, cultural references, team names) "
        f"and start with '{letter}'? Respond with 'yes' or 'no', followed by a period and a short explanation (max 20 words)."
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()

        if "candidates" in result and result["candidates"]:
            text_response = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            parts = text_response.split(". ", 1)
            is_valid = parts[0].strip().lower() == "yes"
            explanation = parts[1].strip() if len(parts) > 1 else ("Valid" if is_valid else "Invalid")
            print(f"Gemini response for {category}/{letter}/{word}: {text_response}")
            return is_valid, explanation
        
        return False, "No clear response from API"
    except requests.RequestException as e:
        print(f"Error calling Gemini API for {category}/{letter}/{word}: {e}")
        return False, f"API error: {str(e)}"