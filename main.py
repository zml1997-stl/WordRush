from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ai_validator import validate_word
from flask import Flask, render_template, request, session
from game_logic import generate_round, calculate_score
import random
import string

# SQLite database setup
DATABASE_URL = "sqlite:///wordrush.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
metadata = MetaData()

# Define a simple Scores table
class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, index=True)
    player_name = Column(String, index=True)
    score = Column(Integer)

# Create the table
Base.metadata.create_all(bind=engine)

# Initialize FastAPI and Flask
fastapi_app = FastAPI()
flask_app = Flask(__name__)
flask_app.secret_key = "your_secret_key"  # Replace with a secure key

def generate_session_id():
    """Generate a 4-letter session ID for multiplayer."""
    return ''.join(random.choices(string.ascii_uppercase, k=4))

# Flask routes for rendering templates
@flask_app.route('/')
def home():
    return render_template('index.html')

@flask_app.route('/game')
def game():
    if 'round_data' not in session:
        session['round_data'] = generate_round()
        session['total_score'] = 0
        session['session_id'] = generate_session_id()
    return render_template('game.html', 
                          letter=session['round_data']["letter"], 
                          categories=session['round_data']["categories"], 
                          total_score=session.get('total_score', 0),
                          session_id=session['session_id'])

@flask_app.route('/submit', methods=['POST'])
def submit():
    if 'round_data' not in session:
        session['round_data'] = generate_round()
        session['total_score'] = 0
        session['session_id'] = generate_session_id()
    
    round_data = session['round_data']
    answers = {category: request.form.get(category, '') for category in round_data["categories"]}
    letter = round_data["letter"]
    
    # Validate answers and assign points
    results = {}
    for category, answer in answers.items():
        if answer:
            is_valid = validate_word(category, letter, answer)
            points = 10 if is_valid else 0
        else:
            is_valid = False
            points = 0
        results[category] = {"answer": answer, "is_valid": is_valid, "points": points}
    
    # Calculate total round score
    round_score = sum(result["points"] for result in results.values())
    session['total_score'] = session.get('total_score', 0) + round_score
    
    # Save score to database
    db = SessionLocal()
    new_score = Score(player_name=f"Player1_{session['session_id']}", score=round_score)
    db.add(new_score)
    db.commit()
    db.close()
    
    # Render results page
    return render_template('game.html', 
                          letter=letter, 
                          categories=round_data["categories"], 
                          total_score=session['total_score'],
                          results=results,
                          round_score=round_score,
                          session_id=session['session_id'],
                          show_results=True)

@flask_app.route('/new_round')
def new_round():
    # Show loading state while generating new round
    session['is_loading'] = True
    session.modified = True
    round_data = generate_round()  # This may take time due to Gemini checks
    session['round_data'] = round_data
    session['is_loading'] = False
    return render_template('game.html', 
                          letter=session['round_data']["letter"], 
                          categories=session['round_data']["categories"], 
                          total_score=session.get('total_score', 0),
                          session_id=session['session_id'])

# FastAPI endpoints
@fastapi_app.get("/test")
async def test_endpoint():
    return {"status": "success", "detail": "Test endpoint is working!"}

@fastapi_app.get("/add_score/{player_name}/{score}")
async def add_score(player_name: str, score: int):
    db = SessionLocal()
    new_score = Score(player_name=player_name, score=score)
    db.add(new_score)
    db.commit()
    db.refresh(new_score)
    db.close()
    return {"status": "success", "player_name": player_name, "score": score}

@fastapi_app.get("/validate/{category}/{letter}/{word}")
async def validate(category: str, letter: str, word: str):
    is_valid = validate_word(category, letter, word)
    return {"category": category, "letter": letter, "word": word, "is_valid": is_valid}

# Combine Flask and FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
fastapi_app.mount("/", WSGIMiddleware(flask_app))

# For Heroku, we need to expose the FastAPI app as 'app'
app = fastapi_app