from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ai_validator import validate_word, validate_multiplayer_answers
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from game_logic import generate_round, calculate_score, calculate_multiplayer_scores
import random
import string
from collections import defaultdict

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
socketio = SocketIO(flask_app, async_mode="gevent")

# Multiplayer session management
multiplayer_sessions = defaultdict(dict)

def generate_session_id():
    return ''.join(random.choices(string.ascii_uppercase, k=4))

def generate_player_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@flask_app.route('/')
def home():
    return render_template('index.html')

@flask_app.route('/game')
def game():
    mode = request.args.get('mode', 'single')
    if mode == 'multi':
        if 'player_id' not in session:
            session['player_id'] = generate_player_id()
        if 'session_id' not in session:
            session['session_id'] = generate_session_id()
            multiplayer_sessions[session['session_id']] = {
                'players': {},
                'round_data': generate_round(),
                'votes': {}
            }
        session_data = multiplayer_sessions[session['session_id']]
        session_data['players'][session['player_id']] = {
            'score': 0,
            'answers': {}
        }
        return render_template('game.html', 
                              letter=session_data['round_data']["letter"], 
                              categories=session_data['round_data']["categories"], 
                              total_score=session_data['players'][session['player_id']]['score'],
                              session_id=session['session_id'],
                              mode='multi')
    else:
        if 'round_data' not in session:
            session['round_data'] = generate_round()
            session['total_score'] = 0
            session['session_id'] = generate_session_id()
            session['votes'] = {}
        return render_template('game.html', 
                              letter=session['round_data']["letter"], 
                              categories=session['round_data']["categories"], 
                              total_score=session.get('total_score', 0),
                              session_id=session['session_id'],
                              mode='single')

@flask_app.route('/submit', methods=['POST'])
def submit():
    mode = request.args.get('mode', 'single')
    if mode == 'multi':
        session_data = multiplayer_sessions[session['session_id']]
        round_data = session_data['round_data']
        player_data = session_data['players'][session['player_id']]
        answers = {category: request.form.get(category, '') for category in round_data["categories"]}
        player_data['answers'] = answers
        socketio.emit('answers_submitted', {'player_id': session['player_id'], 'answers': answers}, room=session['session_id'])
        return redirect(url_for('multiplayer_results'))
    else:
        if 'round_data' not in session:
            session['round_data'] = generate_round()
            session['total_score'] = 0
            session['session_id'] = generate_session_id()
            session['votes'] = {}
        
        round_data = session['round_data']
        answers = {category: request.form.get(category, '') for category in round_data["categories"]}
        letter = round_data["letter"]
        
        category_word_pairs = [(category, letter, answer) for category, answer in answers.items() if answer]
        validation_results = validate_word(category_word_pairs) if category_word_pairs else {}
        
        results = {}
        for category, answer in answers.items():
            if answer:
                is_valid, explanation, is_unique = validation_results.get(category, (False, "Validation failed", True))
                points = 10 if is_valid else 0
                uniqueness_bonus = 5 if is_valid and is_unique else 0
            else:
                is_valid, explanation, is_unique = False, "No answer provided", True
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
                              show_results=True,
                              mode='single')

@socketio.on('join')
def handle_join(data):
    session_id = data['session_id']
    player_id = session.get('player_id')
    if session_id in multiplayer_sessions and player_id in multiplayer_sessions[session_id]['players']:
        join_room(session_id)
        emit('player_joined', {'player_id': player_id}, room=session_id)

@socketio.on('vote')
def handle_vote(data):
    category = data['category']
    session_id = session.get('session_id')
    player_id = session.get('player_id')
    if session_id in multiplayer_sessions and player_id in multiplayer_sessions[session_id]['players']:
        multiplayer_sessions[session_id]['votes'][category] = True
        emit('vote_accepted', {'category': category, 'player_id': player_id}, room=session_id)

@flask_app.route('/multiplayer_results')
def multiplayer_results():
    session_data = multiplayer_sessions[session['session_id']]
    round_data = session_data['round_data']
    player_data = session_data['players'][session['player_id']]
    answers = player_data['answers']
    letter = round_data["letter"]
    
    category_word_pairs = [(category, letter, answer) for category, answer in answers.items() if answer]
    validation_results = validate_word(category_word_pairs) if category_word_pairs else {}
    
    results = {}
    for category, answer in answers.items():
        if answer:
            is_valid, explanation, is_unique = validation_results.get(category, (False, "Validation failed", True))
            points = 10 if is_valid else 0
            uniqueness_bonus = 5 if is_valid and is_unique else 0
        else:
            is_valid, explanation, is_unique = False, "No answer provided", True
            points = uniqueness_bonus = 0
        results[category] = {
            "answer": answer,
            "is_valid": is_valid,
            "points": points + uniqueness_bonus,
            "explanation": explanation,
            "voted": session_data['votes'].get(category, False)
        }
    
    for category, result in results.items():
        if result["voted"]:
            result["is_valid"] = True
            result["points"] = 10
            result["explanation"] += " (Accepted by vote)"
    
    round_score = sum(result["points"] for result in results.values())
    player_data['score'] += round_score
    session_data['last_results'] = results
    session_data['last_round_score'] = round_score
    
    return render_template('game.html', 
                          letter=letter, 
                          categories=round_data["categories"], 
                          total_score=player_data['score'],
                          results=results,
                          round_score=round_score,
                          session_id=session['session_id'],
                          show_results=True,
                          mode='multi')

@flask_app.route('/new_round')
def new_round():
    mode = request.args.get('mode', 'single')
    if mode == 'multi':
        session_data = multiplayer_sessions[session['session_id']]
        session_data['round_data'] = generate_round()
        session_data['votes'] = {}
        socketio.emit('new_round_started', {'letter': session_data['round_data']["letter"], 'categories': session_data['round_data']["categories"]}, room=session['session_id'])
        return redirect(url_for('game', mode='multi'))
    else:
        session['round_data'] = generate_round()
        session['votes'] = {}
        session.modified = True
        return render_template('game.html', 
                              letter=session['round_data']["letter"], 
                              categories=session['round_data']["categories"], 
                              total_score=session.get('total_score', 0),
                              session_id=session['session_id'],
                              mode='single')

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
    is_valid, explanation, _ = result[category]  # Ignore is_unique for this endpoint
    return {"category": category, "letter": letter, "word": word, "is_valid": is_valid, "explanation": explanation}

from fastapi.middleware.wsgi import WSGIMiddleware
fastapi_app.mount("/", WSGIMiddleware(flask_app))

app = fastapi_app