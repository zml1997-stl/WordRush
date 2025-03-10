import random
from ai_validator import validate_word

# 100 sample categories
CATEGORIES = [
    "Fruit", "Country", "Animal", "Movie", "Color", "Sport", "City", "Food", "Book", "Clothing",
    "Vehicle", "Plant", "Occupation", "Musical Instrument", "Furniture", "Drink", "Dessert", 
    "Vegetable", "Bird", "Fish", "Insect", "Reptile", "Mammal", "Tree", "Flower", 
    "Mountain", "River", "Lake", "Ocean", "Island", "Planet", "Star", "Constellation", 
    "Weather", "Season", "Holiday", "Festival", "Game", "Toy", "Tool", "Weapon", 
    "Building", "Room", "Appliance", "Electronics", "Software", "Website", "App", "Brand", 
    "Company", "Job Title", "School Subject", "Language", "Currency", "Law", "Crime", 
    "Sport Team", "Athlete", "Coach", "Dance", "Song", "Album", "Band", "Artist", 
    "Painting", "Sculpture", "Museum", "Theater", "Play", "Actor", "Director", "Writer", 
    "Poet", "Novel", "Poem", "Magazine", "Newspaper", "TV Show", "Cartoon", "Superhero", 
    "Villain", "Mythical Creature", "God", "Religion", "Ceremony", "Tradition", "Custom", 
    "Fashion", "Jewelry", "Shoe", "Hat", "Bag", "Fabric", "Material", "Element", 
    "Chemical", "Disease", "Medicine", "Body Part", "Emotion"
]
LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

def has_valid_answer(category, letter):
    """Check if a category has at least one valid answer starting with the letter using Gemini."""
    # Use a simple test word or query Gemini for existence
    test_words = [f"{letter.lower()}{suffix}" for suffix in ["a", "e", "i", "o", "u"]]  # Basic heuristic
    for test_word in test_words:
        if validate_word(category, letter, test_word):
            return True
    # Fallback: ask Gemini directly if any word exists (simplified for now)
    return validate_word(category, letter, f"{letter.lower()}test")  # Placeholder

def generate_round():
    """Generate a new game round with a random letter and 10 valid categories."""
    while True:
        letter = random.choice(LETTERS)
        categories = random.sample(CATEGORIES, 10)  # Pick 10 unique categories
        # Verify each category has a valid answer
        if all(has_valid_answer(category, letter) for category in categories):
            return {"letter": letter, "categories": categories}

def calculate_score(answers, round_data):
    """Calculate score based on validated answers and uniqueness."""
    score = 0
    letter = round_data["letter"]
    for category, answer in answers.items():
        if answer:  # Only validate if an answer is provided
            if validate_word(category, letter, answer):
                score += 10  # Base points for valid answer
                # Check uniqueness among non-blank answers
                if not any(validate_word(category, letter, a) for a in answers.values() if a != answer and a):
                    score += 5  # Bonus for unique answer
    return score