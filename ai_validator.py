import requests
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

def validate_word(category_word_pairs: list[tuple[str, str, str]]) -> dict[str, tuple[bool, str, bool]]:
    """
    Validate multiple category-letter-word pairs in one API call.
    Returns a dict mapping category to (is_valid, explanation, is_unique).
    """
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY not set in environment variables")

    results = {}
    prompt_parts = []
    words_by_category = {}
    for category, letter, word in category_word_pairs:
        letter = letter.upper()
        word = word.strip().lower()
        if not word.startswith(letter.lower()):
            results[category] = (False, f"'{word}' does not start with '{letter}'", True)
        else:
            prompt_parts.append(f"('{category}', '{word}') starts with '{letter}'")
            words_by_category[category] = word

    if not prompt_parts:
        return results

    headers = {"Content-Type": "application/json"}
    prompt = (
        f"Evaluate these category-word pairs for validity in any common context (e.g., proper nouns, cultural references, team names):\n"
        f"{'; '.join(prompt_parts)}.\n"
        f"For each, respond with 'yes' or 'no', a period, a short explanation (max 20 words), and 'unique' or 'duplicate' if the word repeats elsewhere. "
        f"Format as: category: response; category: response."
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()

        if "candidates" in result and result["candidates"]:
            text_response = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"Gemini response: {text_response}")
            for line in text_response.split(";"):
                if ":" in line:
                    category, resp = line.split(":", 1)
                    category = category.strip()
                    parts = resp.strip().split(". ", 2)
                    is_valid = parts[0].strip().lower() == "yes"
                    explanation = parts[1].strip()
                    is_unique = parts[2].strip().lower() == "unique" if len(parts) > 2 else True
                    results[category] = (is_valid, explanation, is_unique)
        
        for category, _, _ in category_word_pairs:
            if category not in results:
                results[category] = (False, "No clear response from API", True)
        return results
    
    except requests.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        return {category: (False, f"API error: {str(e)}", True) for category, _, _ in category_word_pairs}