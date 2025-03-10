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

DATABASE_URL = "sqlite:///wordrush.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
metadata = MetaData()

class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, index=True)
    player_name = Column(String, index=True)
    score = Column(Integer)

Base.metadata.create_all(bind=engine)

fastapi_app = FastAPI()
flask_app = Flask(__name__)
flask_app.secret_key = "your_secret_key"

def generate_session_id():
    return ''.join(random.choices(string.ascii_uppercase, k=4))

@flask_app.route('/')
def home():
    return render_template('index.html')

@flask_app.route('/game')
def game():
    if 'round_data' not in session:
        session['round_data'] = generate_round()
        session['total_score'] = 0
        session['session_id'] = generate_session_id()
        session['votes'] = {}
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
        session['votes'] = {}
    
    round_data = session['round_data']
    answers = {category: request.form.get(category, '') for category in round_data["categories"]}
    letter = round_data["letter"]
    
    # Batch validate all answers
    category_word_pairs = [(category, letter, answer) for category, answer in answers.items() if answer]
    validation_results = validate_word(category_word_pairs) if category_word_pairs else {}
    
    results = {}
    for category, answer in answers.items():
        if answer:
            is_valid, explanation = validation_results.get(category, (False, "Validation failed"))
            points = 10 if is_valid else 0
            # Uniqueness check (still calls API, but we'll optimize this next)
            uniqueness_bonus = 5 if is_valid and not any(
                validate_word([(c, letter, a)])[c][0] for c, a in answers.items() if a != answer and a
            ) else 0
        else:
            is_valid, explanation = False, "No answer provided"
            points = uniqueness_bonus = 0
        results[category] = {
            "answer": answer,
            "is_valid": is_valid,
            "points": points + uniqueness_bonus,
            "explanation": explanation,
            "voted": session.get('votes', {}).get(category, False)
        }
    
    for category, result in results.items():
        if result["voted"]:
            result["is_valid"] = True
            result["points"] = 10
            result["explanation"] += " (Accepted by vote)"
    
    round_score = sum(result["points"] for result in results.values())
    session['total_score'] = session.get('total_score', 0) + round_score
    session['last_results'] = results
    session['last_round_score'] = round_score
    
    db = SessionLocal()
    new_score = Score(player_name=f"Player1_{session['session_id']}", score=round_score)
    db.add(new_score)
    db.commit()
    db.close()
    
    return render_template('game.html', 
                          letter=letter, 
                          categories=round_data["categories"], 
                          total_score=session['total_score'],
                          results=results,
                          round_score=round_score,
                          session_id=session['session_id'],
                          show_results=True)

@flask_app.route('/vote/<category>', methods=['POST'])
def vote(category):
    if 'last_results' in session and category in session['last_results']:
        if 'votes' not in session:
            session['votes'] = {}
        session['votes'][category] = True
        session.modified = True
        
        results = session['last_results']
        results[category]["voted"] = True
        results[category]["is_valid"] = True
        results[category]["points"] = 10
        results[category]["explanation"] += " (Accepted by vote)"
        
        round_score = sum(result["points"] for result in results.values())
        session['total_score'] = session.get('total_score', 0) - session.get('last_round_score', 0) + round_score
        session['last_round_score'] = round_score
    
    return render_template('game.html', 
                          letter=session['round_data']["letter"], 
                          categories=session['round_data']["categories"], 
                          total_score=session['total_score'],
                          results=session['last_results'],
                          round_score=session['last_round_score'],
                          session_id=session['session_id'],
                          show_results=True)

@flask_app.route('/new_round')
def new_round():
    session['round_data'] = generate_round()
    session['votes'] = {}
    session.modified = True
    return render_template('game.html', 
                          letter=session['round_data']["letter"], 
                          categories=session['round_data']["categories"], 
                          total_score=session.get('total_score', 0),
                          session_id=session['session_id'])

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
    result = validate_word([(category, letter, word)])
    is_valid, explanation = result[category]
    return {"category": category, "letter": letter, "word": word, "is_valid": is_valid, "explanation": explanation}

from fastapi.middleware.wsgi import WSGIMiddleware
fastapi_app.mount("/", WSGIMiddleware(flask_app))

app = fastapi_app