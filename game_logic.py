import random
from ai_validator import validate_word

CATEGORIES = [
    "Famous Celebrities", "Types of Fruit", "Types of Vegetables", "Cities in the World", "Countries",
    "Animals", "Types of Food", "Desserts", "Musical Instruments", "Sports", "Types of Clothing",
    "Types of Drinks", "Things Found in a Kitchen", "Items in a Bathroom", "Items in a Bedroom", 
    "Items in a Living Room", "Furniture", "Household Items", "Items in an Office", "School Subjects",
    "Books", "Movies", "TV Shows", "Things Found at a Mall", "Things Found at a Park", "Items in a Garage",
    "Items Found in a Car", "Things You Find in a Garden", "Types of Flowers", "Things That Are Red", 
    "Things That Are Blue", "Things That Are Green", "Things That Are Yellow", "Modes of Transportation", 
    "Modes of Communication", "Types of Weather", "Occupations", "Companies", "Brands", "Items Found in a Store",
    "Types of Electronics", "Items in a Hospital", "Medical Terms", "Animals on a Farm", "Types of Trees",
    "Types of Insects", "Body Parts", "Plants", "Hobbies", "Board Games", "Card Games", "Computer Programs",
    "Household Chores", "Tools", "Things You Can Wear", "Types of Jewelry", "Types of Shoes", "Types of Hats",
    "Party Supplies", "Vacation Spots", "Tourist Attractions", "Places to Visit", "Historical Figures",
    "Historical Events", "Items in a Museum", "Items Found at the Beach", "Winter Activities", "Types of Dance",
    "Music Genres", "Forms of Art", "Inventions", "Things You Can Write With", "Things That Are Soft",
    "Things That Are Hard", "Things That Are Fast", "Things That Are Slow", "Things That Smell Good",
    "Things That Smell Bad", "Types of Pets", "Items Found in a Library", "Types of Berries", "Types of Nuts",
    "Things Found in a Farmhouse", "Things in the Wilderness", "Tools Found in a Workshop", "Items Found in a Gym",
    "Things That Are Circular", "Things That Are Square", "Things That Are Triangular", "Modes of Entertainment"
]
LETTERS = list("ABCDEFGHIJKLMNOPRSTW")

def generate_round():
    """Generate a new game round with a random letter and 10 categories."""
    letter = random.choice(LETTERS)
    categories = random.sample(CATEGORIES, 10)
    return {"letter": letter, "categories": categories}

def calculate_score(answers, round_data):
    """Calculate score based on validated answers and uniqueness."""
    score = 0
    letter = round_data["letter"]
    for category, answer in answers.items():
        if answer and validate_word(category, letter, answer):
            score += 10  # Valid answer
            if not any(validate_word(category, letter, a) for a in answers.values() if a != answer and a):
                score += 5  # Bonus for unique answer
    return score

def calculate_multiplayer_scores(players_answers, round_data):
    """
    Calculate scores for all players in a multiplayer round.
    Returns a dictionary mapping player IDs to their scores.
    """
    letter = round_data["letter"]
    scores = {}
    all_answers = [answer for answers in players_answers.values() for answer in answers.values() if answer]
    
    for player_id, answers in players_answers.items():
        score = 0
        for category, answer in answers.items():
            if answer and validate_word(category, letter, answer):
                score += 10  # Valid answer
                if not any(a == answer for a in all_answers if a != answer):
                    score += 5  # Bonus for unique answer
        scores[player_id] = score
    return scores

def handle_vote(category: str, session_id: str, player_id: str, multiplayer_sessions: dict):
    """
    Handle voting on a category in a multiplayer session.
    Updates the session data to reflect the vote.
    """
    if session_id in multiplayer_sessions and player_id in multiplayer_sessions[session_id]['players']:
        multiplayer_sessions[session_id]['votes'][category] = True
        return True
    return False