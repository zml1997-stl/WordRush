from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form, Query
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
multiplayer_sessions = defaultdict(dict)

def generate_session_id():
    return ''.join(random.choices(string.ascii_uppercase, k=4))

def generate_player_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/multiplayer")
async def multiplayer(request: Request, player: str = "Player"):
    return templates.TemplateResponse("multiplayer.html", {"request": request, "player_name": player})

@app.get("/game")
async def game(
    request: Request,
    mode: str = "single",
    player: str = "Player",
    show_results: bool = False,
    session_id: str = Query(None)
):
    if mode == "multi":
        if session_id and session_id in multiplayer_sessions:
            session_data = multiplayer_sessions[session_id]
            total_score = sum(p['score'] for p in session_data['players'].values()) if session_data['players'] else 0
        else:
            session_id = generate_session_id()
            multiplayer_sessions[session_id] = {
                'players': {},
                'round_data': generate_round(),
                'votes': {},
                'time_left': 120
            }
            session_data = multiplayer_sessions[session_id]
            total_score = 0
        return templates.TemplateResponse("game.html", {
            "request": request,
            "letter": session_data['round_data']["letter"],
            "categories": session_data['round_data']["categories"],
            "total_score": total_score,
            "session_id": session_id,
            "mode": mode,
            "player_name": player,
            "show_results": show_results
        })
    else:
        round_data = generate_round()
        return templates.TemplateResponse("game.html", {
            "request": request,
            "letter": round_data["letter"],
            "categories": round_data["categories"],
            "total_score": 0,
            "session_id": generate_session_id(),
            "mode": mode,
            "player_name": player,
            "show_results": show_results
        })

@app.post("/submit", response_class=HTMLResponse)
async def submit(request: Request):
    form_data = await request.form()
    answers = {k: v for k, v in form_data.items() if k not in ["player_name", "mode", "session_id", "letter", "categories"]}
    player_name = form_data.get("player_name", "Player")
    mode = form_data.get("mode", "single")
    session_id = form_data.get("session_id", "")
    letter = form_data.get("letter", "")
    categories = [form_data.getlist("categories")[i] for i in range(len(form_data.getlist("categories")))]

    if mode == "multi":
        session_data = multiplayer_sessions.get(session_id, {})
        round_data = session_data.get("round_data", generate_round())
    else:
        round_data = {"letter": letter, "categories": categories}

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
            "voted": False
        }

    round_score = sum(result["points"] for result in results.values())
    total_score = round_score  # For single-player mode

    db = SessionLocal()
    new_score = Score(player_name=player_name, score=round_score)
    db.add(new_score)
    db.commit()
    db.close()

    return templates.TemplateResponse("game.html", {
        "request": request,
        "letter": letter,
        "categories": categories,
        "total_score": total_score,
        "session_id": session_id,
        "mode": mode,
        "player_name": player_name,
        "show_results": True,
        "results": results,
        "round_score": round_score
    })

@app.post("/vote")
async def vote(request: Request):
    form_data = await request.json()
    category = form_data.get("category", "")
    player_name = form_data.get("player_name", "Player")
    mode = form_data.get("mode", "single")
    session_id = form_data.get("session_id", "")

    if mode == "multi":
        session_data = multiplayer_sessions.get(session_id, {})
        if session_data:
            session_data['votes'][category] = True
            return {"status": "success", "message": f"Vote for {category} accepted by {player_name}"}
    return {"status": "success", "message": f"Vote for {category} accepted by {player_name}"}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    player_id = generate_player_id()
    if session_id not in multiplayer_sessions:
        multiplayer_sessions[session_id] = {
            'players': {},
            'round_data': generate_round(),
            'votes': {},
            'time_left': 120
        }
    multiplayer_sessions[session_id]['players'][player_id] = {
        'score': 0,
        'answers': None,
        'websocket': websocket,
        'name': f"Player_{player_id[:3]}"  # Simple name for chat
    }
    # Sync timer for new player
    await websocket.send_text(json.dumps({
        'type': 'timer_update',
        'time_left': multiplayer_sessions[session_id]['time_left']
    }))
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message['type'] == 'submit_answers':
                answers = message['answers']
                multiplayer_sessions[session_id]['players'][player_id]['answers'] = answers
                if all(p['answers'] is not None for p in multiplayer_sessions[session_id]['players'].values()):
                    round_data = multiplayer_sessions[session_id]['round_data']
                    players_answers = {pid: p['answers'] for pid, p in multiplayer_sessions[session_id]['players'].items()}
                    validation_results = validate_multiplayer_answers(players_answers, round_data["letter"])
                    scores = calculate_multiplayer_scores(players_answers, round_data)
                    for pid, player in multiplayer_sessions[session_id]['players'].items():
                        player_score = scores[pid]
                        player['score'] += player_score
                        await player['websocket'].send_text(json.dumps({
                            'type': 'round_results',
                            'results': validation_results[pid],
                            'round_score': player_score,
                            'total_score': player['score']
                        }))
                    for player in multiplayer_sessions[session_id]['players'].values():
                        player['answers'] = None
                    multiplayer_sessions[session_id]['round_data'] = generate_round()
                    multiplayer_sessions[session_id]['time_left'] = 120
            elif message['type'] == 'vote':
                category = message['category']
                multiplayer_sessions[session_id]['votes'][category] = True
                await broadcast_vote(session_id, player_id, category)
            elif message['type'] == 'chat_message':
                for player in multiplayer_sessions[session_id]['players'].values():
                    await player['websocket'].send_text(json.dumps({
                        'type': 'chat_message',
                        'player': multiplayer_sessions[session_id]['players'][player_id]['name'],
                        'message': message['message']
                    }))
            # Simplified timer sync (full sync would require a separate loop)
            multiplayer_sessions[session_id]['time_left'] -= 1
            if multiplayer_sessions[session_id]['time_left'] >= 0:
                for player in multiplayer_sessions[session_id]['players'].values():
                    await player['websocket'].send_text(json.dumps({
                        'type': 'timer_update',
                        'time_left': multiplayer_sessions[session_id]['time_left']
                    }))
            if multiplayer_sessions[session_id]['time_left'] <= 0:
                if all(p['answers'] is not None for p in multiplayer_sessions[session_id]['players'].values()):
                    round_data = multiplayer_sessions[session_id]['round_data']
                    players_answers = {pid: p['answers'] for pid, p in multiplayer_sessions[session_id]['players'].items()}
                    validation_results = validate_multiplayer_answers(players_answers, round_data["letter"])
                    scores = calculate_multiplayer_scores(players_answers, round_data)
                    for pid, player in multiplayer_sessions[session_id]['players'].items():
                        player_score = scores[pid]
                        player['score'] += player_score
                        await player['websocket'].send_text(json.dumps({
                            'type': 'round_results',
                            'results': validation_results[pid],
                            'round_score': player_score,
                            'total_score': player['score']
                        }))
                    for player in multiplayer_sessions[session_id]['players'].values():
                        player['answers'] = None
                    multiplayer_sessions[session_id]['round_data'] = generate_round()
                    multiplayer_sessions[session_id]['time_left'] = 120
    except WebSocketDisconnect:
        del multiplayer_sessions[session_id]['players'][player_id]
        await broadcast_player_left(session_id, player_id)
        if not multiplayer_sessions[session_id]['players']:
            del multiplayer_sessions[session_id]

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
    is_valid, explanation, _ = result[category]
    return {"category": category, "letter": letter, "word": word, "is_valid": is_valid, "explanation": explanation}

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard(request: Request):
    db = SessionLocal()
    scores = db.query(Score).order_by(Score.score.desc()).limit(10).all()
    db.close()
    return templates.TemplateResponse("leaderboard.html", {"request": request, "scores": scores})