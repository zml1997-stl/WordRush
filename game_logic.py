import random
from ai_validator import validate_word

# Sample categories and letters for the game
CATEGORIES = ["Fruit", "Country", "Animal", "Movie", "Color", "Sport"]
LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

def generate_round():
    """Generate a new game round with a random letter and categories."""
    letter = random.choice(LETTERS)
    categories = random.sample(CATEGORIES, 3)  # Pick 3 unique categories
    return {"letter": letter, "categories": categories}

def calculate_score(answers, round_data):
    """Calculate score based on validated answers and uniqueness."""
    score = 0
    letter = round_data["letter"]
    for category, answer in answers.items():
        if answer and validate_word(category, letter, answer):
            # Base score for valid answer, bonus for uniqueness (simplified)
            score += 10  # Base points
            if not any(validate_word(category, letter, a) for a in answers.values() if a != answer):
                score += 5  # Bonus for unique answer
    return score