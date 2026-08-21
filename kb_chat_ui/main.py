from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai

BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(Path('/home/jp/proyectos/gemini_test/.env'))

from kb_chat_ui.table_compiler import MesaCompiler

ATOMS_JSON = Path('/home/jp/proyectos/gemini_test/kb_agent_ui/atoms.json')

app = FastAPI(title='KB Chat UI')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

client = genai.Client()
compiler = MesaCompiler()
_atoms_cache: dict | None = None
sessions: dict[str, dict] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    turn: dict


def load_atoms() -> dict:
    global _atoms_cache
    if _atoms_cache is None:
        _atoms_cache = json.loads(ATOMS_JSON.read_text(encoding='utf-8'))
    return _atoms_cache


def get_session(session_id: str) -> dict:
    if session_id not in sessions:
        sessions[session_id] = {'turns': []}
    return sessions[session_id]


def build_prompt(message: str, prompt_mesa: dict) -> str:
    mesa_json = json.dumps(prompt_mesa, ensure_ascii=False, indent=2)
    return f"""
Responde en español usando SOLO la información incluida abajo.

Reglas:
- No inventes nada fuera de los items provistos.
- Sé concreto.
- Máximo 140 palabras.
- Máximo 5 bullets.
- Conserva los ids atom-... en el texto cuando cites evidencia.
- Si la información no alcanza, dilo en una línea.

Pregunta del usuario:
{message}

CONTEXTO:
{mesa_json}
""".strip()


@app.get('/')
def index():
    return FileResponse(BASE_DIR / 'index.html')


@app.post('/api/chat', response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid4())
    session = get_session(session_id)
    previous_turn = session['turns'][-1] if session['turns'] else None
    compiled = compiler.compile(req.message, previous_turn=previous_turn)
    prompt = build_prompt(req.message, compiled['prompt_mesa'])
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    reply = (response.text or '').strip()

    turn = {
        'turn_id': f"turn-{len(session['turns']) + 1:03d}",
        'user_message': req.message,
        'assistant_message': reply,
        'mesa': compiled['mesa'],
    }
    session['turns'].append(turn)
    return ChatResponse(session_id=session_id, turn=turn)


@app.get('/api/session/{session_id}')
def session_detail(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail='session not found')
    return sessions[session_id]


@app.get('/api/turn/{session_id}/{turn_id}')
def turn_detail(session_id: str, turn_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='session not found')
    for turn in session['turns']:
        if turn['turn_id'] == turn_id:
            return turn
    raise HTTPException(status_code=404, detail='turn not found')


@app.get('/api/atom/{atom_id}')
def atom(atom_id: str):
    data = load_atoms()
    for atom in data.get('atoms', []):
        if atom.get('id') == atom_id:
            return atom
    raise HTTPException(status_code=404, detail='atom not found')


app.mount('/static', StaticFiles(directory=BASE_DIR), name='static')
