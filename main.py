from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ai_validator import validate_word
from flask import Flask, render_template, request
import random
from game_logic import generate_round, calculate_score

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

# Flask routes for rendering templates
@flask_app.route('/')
def home():
    return render_template('index.html')

@flask_app.route('/game')
def game():
    round_data = generate_round()
    return render_template('game.html', letter=round_data["letter"], categories=round_data["categories"])

@flask_app.route('/submit', methods=['POST'])
def submit():
    answers = {key: value for key, value in request.form.items() if value}
    round_data = generate_round()  # Generate new round data for next game
    score = calculate_score(answers, round_data)
    
    # Save score (simplified, using a placeholder player name)
    db = SessionLocal()
    new_score = Score(player_name="Player1", score=score)
    db.add(new_score)
    db.commit()
    db.close()
    
    return render_template('game.html', letter=round_data["letter"], categories=round_data["categories"], 
                          message=f"Score: {score} points! New round started.")

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