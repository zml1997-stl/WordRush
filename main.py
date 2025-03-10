from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ai_validator import validate_word, validate_multiplayer_answers
from game_logic import generate_round, calculate_score, calculate_multiplayer_scores
import random
import string
from collections import defaultdict
import json

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

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Multiplayer session management
multiplayer_sessions = defaultdict(dict)

def generate_session_id():
    return ''.join(random.choices(string.ascii_uppercase, k=4))

def generate_player_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/game")
async def game(request: Request, mode: str = "single"):
    if mode == "multi":
        session_id = generate_session_id()
        multiplayer_sessions[session_id] = {
            'players': {},
            'round_data': generate_round(),
            'votes': {}
        }
        return templates.TemplateResponse("game.html", {
            "request": request,
            "letter": multiplayer_sessions[session_id]['round_data']["letter"],
            "categories": multiplayer_sessions[session_id]['round_data']["categories"],
            "total_score": 0,
            "session_id": session_id,
            "mode": mode
        })
    else:
        round_data = generate_round()
        return templates.TemplateResponse("game.html", {
            "request": request,
            "letter": round_data["letter"],
            "categories": round_data["categories"],
            "total_score": 0,
            "session_id": generate_session_id(),
            "mode": mode
        })

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    player_id = generate_player_id()
    multiplayer_sessions[session_id]['players'][player_id] = {
        'score': 0,
        'answers': {},
        'websocket': websocket
    }

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message['type'] == 'submit_answers':
                answers = message['answers']
                multiplayer_sessions[session_id]['players'][player_id]['answers'] = answers
                await broadcast_answers(session_id, player_id, answers)
            elif message['type'] == 'vote':
                category = message['category']
                multiplayer_sessions[session_id]['votes'][category] = True
                await broadcast_vote(session_id, player_id, category)
    except WebSocketDisconnect:
        del multiplayer_sessions[session_id]['players'][player_id]
        await broadcast_player_left(session_id, player_id)

async def broadcast_answers(session_id: str, player_id: str, answers: dict):
    for player in multiplayer_sessions[session_id]['players'].values():
        await player['websocket'].send_text(json.dumps({
            'type': 'answers_submitted',
            'player_id': player_id,
            'answers': answers
        }))

async def broadcast_vote(session_id: str, player_id: str, category: str):
    for player in multiplayer_sessions[session_id]['players'].values():
        await player['websocket'].send_text(json.dumps({
            'type': 'vote_accepted',
            'player_id': player_id,
            'category': category
        }))

async def broadcast_player_left(session_id: str, player_id: str):
    for player in multiplayer_sessions[session_id]['players'].values():
        await player['websocket'].send_text(json.dumps({
            'type': 'player_left',
            'player_id': player_id
        }))

@app.get("/test")
async def test_endpoint():
    return {"status": "success", "detail": "Test endpoint is working!"}

@app.get("/add_score/{player_name}/{score}")
async def add_score(player_name: str, score: int):
    db = SessionLocal()
    new_score = Score(player_name=player_name, score=score)
    db.add(new_score)
    db.commit()
    db.refresh(new_score)
    db.close()
    return {"status": "success", "player_name": player_name, "score": score}

@app.get("/validate/{category}/{letter}/{word}")
async def validate(category: str, letter: str, word: str):
    result = validate_word([(category, letter, word)])
    is_valid, explanation, _ = result[category]  # Ignore is_unique for this endpoint
    return {"category": category, "letter": letter, "word": word, "is_valid": is_valid, "explanation": explanation}