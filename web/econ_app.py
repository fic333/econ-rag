"""FastAPI web server for the Economics RAG system with flashcards."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from econ_rag.services.rag_engine import RAGEngine
from econ_rag.services.test_generator import TestGenerator
from econ_rag.services.flashcard_generator import FlashcardGenerator
from econ_rag.database import get_session, Document, Flashcard
from econ_rag.config import settings

# Initialize FastAPI
app = FastAPI(title="Economics RAG System", version="1.0.0")

# Request/Response models
class QueryRequest(BaseModel):
    question: str
    top_k: int = 5

class TestRequest(BaseModel):
    num_questions: int = 10
    topics: Optional[List[str]] = None
    lectures: Optional[List[int]] = None

class FlashcardSetRequest(BaseModel):
    name: str
    description: Optional[str] = None
    topics: Optional[List[str]] = None
    lectures: Optional[List[int]] = None

class FlashcardResponse(BaseModel):
    id: int
    card_num: int
    front: str
    back: str
    citation: Optional[str]
    card_type: str

class FlashcardSetResponse(BaseModel):
    id: int
    name: str
    card_count: int
    cards: List[FlashcardResponse]

# Initialize services
rag_engine = RAGEngine()
test_gen = TestGenerator()
flashcard_gen = FlashcardGenerator()

# Web UI
@app.get("/", response_class=HTMLResponse)
async def root():
    """Web interface with login and multiple study modes."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Economics RAG - Study Hub</title>
    <style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.login-page { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.login-box { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); width: 100%; max-width: 400px; }
.login-box h1 { text-align: center; margin-bottom: 30px; color: #2c3e50; }
.login-box input { width: 100%; padding: 12px; margin-bottom: 15px; border: 2px solid #ddd; border-radius: 6px; font-size: 16px; }
.login-box button { width: 100%; padding: 12px; background: #3498db; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; }
.login-box button:hover { background: #2980b9; }
.header { background: #3498db; color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; }
.header h1 { font-size: 28px; }
.logout-btn { background: #e74c3c; padding: 10px 20px; border: none; color: white; border-radius: 6px; cursor: pointer; font-weight: bold; }
.main-page { display: none; }
.modes-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px; }
.mode-card { background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; border-left: 6px solid #3498db; }
.mode-card:hover { transform: translateY(-5px); box-shadow: 0 8px 20px rgba(0,0,0,0.15); }
.mode-card h3 { margin-bottom: 10px; color: #2c3e50; font-size: 20px; }
.mode-card p { color: #7f8c8d; line-height: 1.6; margin-bottom: 15px; }
.mode-card button { width: 100%; padding: 12px; background: #3498db; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
.mode-card button:hover { background: #2980b9; }
.study-area { display: none; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.study-area.active { display: block; }
.flashcard-container { perspective: 1000px; height: 400px; margin-bottom: 30px; }
.flashcard { width: 100%; height: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 40px; color: white; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; cursor: pointer; transition: transform 0.6s; transform-style: preserve-3d; box-shadow: 0 8px 20px rgba(0,0,0,0.2); position: relative; }
.flashcard.flipped { transform: rotateY(180deg); }
.flashcard-face { position: absolute; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; backface-visibility: hidden; }
.flashcard-front { color: white; }
.flashcard-back { transform: rotateY(180deg); background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
.flashcard h2 { font-size: 32px; margin-bottom: 20px; }
.flashcard-label { position: absolute; top: 20px; right: 20px; font-size: 12px; opacity: 0.8; background: rgba(255,255,255,0.2); padding: 5px 10px; border-radius: 4px; }
.flashcard-nav { display: flex; justify-content: space-between; gap: 20px; margin-bottom: 20px; }
.btn { padding: 12px 30px; background: #3498db; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
.btn:hover { background: #2980b9; }
.progress-bar { width: 100%; height: 8px; background: #ecf0f1; border-radius: 4px; margin-bottom: 30px; overflow: hidden; }
.progress-fill { height: 100%; background: #3498db; width: 0%; transition: width 0.3s; }
input, select { width: 100%; padding: 12px; margin-bottom: 15px; border: 2px solid #ddd; border-radius: 6px; font-size: 16px; }
.form-group { margin-bottom: 20px; }
.form-group label { display: block; margin-bottom: 8px; font-weight: bold; color: #2c3e50; }
</style>
</head>
<body>
<div id="loginPage" class="login-page">
    <div class="login-box">
        <h1>📚 Economics RAG</h1>
        <p style="text-align: center; color: #7f8c8d; margin-bottom: 20px;">ECON 154: The Global Economy</p>
        <input type="text" id="username" placeholder="Enter your name" />
        <button onclick="login()">Login</button>
    </div>
</div>

<div id="mainPage" class="main-page">
    <div class="header">
        <div><h1>📚 Economics RAG</h1><p id="userGreeting" style="margin-top: 5px;"></p></div>
        <button class="logout-btn" onclick="logout()">Logout</button>
    </div>

    <div class="modes-grid">
        <div class="mode-card">
            <h3>📝 Flashcards</h3>
            <p>Study with interactive flashcards. Flip to reveal answers and track your progress.</p>
            <button onclick="switchMode('flashcards')">Study Flashcards</button>
        </div>
        <div class="mode-card">
            <h3>❓ Quizzes</h3>
            <p>Test your knowledge with multiple-choice questions and get immediate feedback.</p>
            <button onclick="switchMode('quiz')">Take a Quiz</button>
        </div>
        <div class="mode-card">
            <h3>🔍 Search</h3>
            <p>Ask questions and get answers cited from the lecture notes.</p>
            <button onclick="switchMode('search')">Ask a Question</button>
        </div>
    </div>

    <div id="flashcards" class="study-area">
        <h2>📚 Flashcard Study</h2>
        <div class="form-group">
            <label>Flashcard Set:</label>
            <select id="flashcardSetSelect" onchange="loadFlashcardSet()">
                <option value="">Load a set or create new...</option>
            </select>
        </div>
        <button class="btn" style="width: auto; margin-bottom: 20px;" onclick="showCreateFlashcardForm()">+ Create New Set</button>
        
        <div id="flashcardCreateForm" style="display: none; background: #f9f9f9; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3>Create Flashcard Set</h3>
            <div class="form-group">
                <label>Set Name:</label>
                <input type="text" id="flashcardName" placeholder="e.g., Supply & Demand Basics" />
            </div>
            <div class="form-group">
                <label>Topics (comma-separated):</label>
                <input type="text" id="flashcardTopics" placeholder="e.g., equilibrium, demand-supply" />
            </div>
            <button class="btn" onclick="createFlashcardSet()">Create</button>
        </div>

        <div id="flashcardDisplay">
            <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
            <div class="flashcard-container">
                <div class="flashcard" id="flashcard" onclick="toggleFlip(this)">
                    <div class="flashcard-label" id="cardLabel">Front</div>
                    <div class="flashcard-face flashcard-front">
                        <div id="flashcardFront">Click to start</div>
                    </div>
                    <div class="flashcard-face flashcard-back">
                        <div id="flashcardBack">Click to flip</div>
                    </div>
                </div>
            </div>
            <div class="flashcard-nav">
                <button class="btn" onclick="previousCard()">← Previous</button>
                <span id="cardCounter" style="align-self: center; font-weight: bold; color: #2c3e50;">1 / 1</span>
                <button class="btn" onclick="nextCard()">Next →</button>
            </div>
        </div>
    </div>

    <div id="quiz" class="study-area">
        <h2>❓ Quiz</h2>
        <input type="number" id="numQuestions" placeholder="Number of questions" value="10" />
        <button class="btn" onclick="generateQuiz()">Generate Quiz</button>
        <div id="quizContent"></div>
    </div>

    <div id="search" class="study-area">
        <h2>🔍 Search</h2>
        <input type="text" id="query" placeholder="Ask a question..." />
        <button class="btn" onclick="search()">Search</button>
        <div id="searchResults"></div>
    </div>
</div>

<script>
let currentFlashcardSet = null;
let currentCardIndex = 0;

function getUsername() { return localStorage.getItem("econ_username") || null; }
function setUsername(u) { localStorage.setItem("econ_username", u); }

function login() {
    const username = document.getElementById("username").value.trim();
    if (!username) { alert("Please enter your name"); return; }
    setUsername(username);
    document.getElementById("loginPage").style.display = "none";
    document.getElementById("mainPage").style.display = "block";
    document.getElementById("userGreeting").textContent = `Welcome, ${username}!`;
    loadFlashcardSets();
}

function logout() {
    localStorage.removeItem("econ_username");
    location.reload();
}

function switchMode(mode) {
    document.querySelectorAll(".study-area").forEach(s => s.classList.remove("active"));
    document.getElementById(mode).classList.add("active");
}

async function loadFlashcardSets() {
    const response = await fetch("/api/flashcards/sets");
    const sets = await response.json();
    const select = document.getElementById("flashcardSetSelect");
    select.innerHTML = '<option value="">Create a new set...</option>';
    sets.forEach(s => {
        const opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = `${s.name} (${s.card_count} cards)`;
        select.appendChild(opt);
    });
}

function showCreateFlashcardForm() {
    document.getElementById("flashcardCreateForm").style.display = 
        document.getElementById("flashcardCreateForm").style.display === "none" ? "block" : "none";
}

async function createFlashcardSet() {
    const name = document.getElementById("flashcardName").value.trim();
    const topicsStr = document.getElementById("flashcardTopics").value.trim();
    if (!name) { alert("Enter set name"); return; }
    
    const topics = topicsStr ? topicsStr.split(",").map(t => t.trim()) : null;
    
    const response = await fetch("/api/flashcards/sets", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ name, topics })
    });
    const set = await response.json();
    loadFlashcardSets();
    document.getElementById("flashcardSetSelect").value = set.id;
    loadFlashcardSet();
    showCreateFlashcardForm();
}

async function loadFlashcardSet() {
    const setId = document.getElementById("flashcardSetSelect").value;
    if (!setId) return;
    
    const response = await fetch(`/api/flashcards/sets/${setId}`);
    currentFlashcardSet = await response.json();
    currentCardIndex = 0;
    displayCard();
}

function displayCard() {
    if (!currentFlashcardSet || !currentFlashcardSet.cards) return;
    
    const card = currentFlashcardSet.cards[currentCardIndex];
    document.getElementById("flashcardFront").textContent = card.front;
    document.getElementById("flashcardBack").textContent = card.back;
    document.getElementById("cardLabel").textContent = card.card_type.toUpperCase();
    document.getElementById("cardCounter").textContent = `${currentCardIndex + 1} / ${currentFlashcardSet.cards.length}`;
    
    const progress = ((currentCardIndex + 1) / currentFlashcardSet.cards.length) * 100;
    document.getElementById("progressFill").style.width = progress + "%";
    
    document.getElementById("flashcard").classList.remove("flipped");
}

function toggleFlip(el) {
    el.classList.toggle("flipped");
}

function nextCard() {
    if (currentFlashcardSet && currentCardIndex < currentFlashcardSet.cards.length - 1) {
        currentCardIndex++;
        displayCard();
    }
}

function previousCard() {
    if (currentCardIndex > 0) {
        currentCardIndex--;
        displayCard();
    }
}

async function generateQuiz() {
    const num = document.getElementById("numQuestions").value;
    document.getElementById("quizContent").innerHTML = "<p>Generating quiz...</p>";
    
    const response = await fetch("/api/tests/create", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ num_questions: parseInt(num) })
    });
    const test = await response.json();
    document.getElementById("quizContent").innerHTML = `<p>Quiz created with ${test.question_count} questions</p>`;
}

async function search() {
    const query = document.getElementById("query").value.trim();
    if (!query) return;
    
    document.getElementById("searchResults").innerHTML = "<p>Searching...</p>";
    
    const response = await fetch("/api/ask", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ question: query })
    });
    const data = await response.json();
    document.getElementById("searchResults").innerHTML = `<p>${data.answer || "No answer found"}</p>`;
}

window.onload = function() {
    const user = getUsername();
    if (user) {
        document.getElementById("loginPage").style.display = "none";
        document.getElementById("mainPage").style.display = "block";
        document.getElementById("userGreeting").textContent = `Welcome, ${user}!`;
        loadFlashcardSets();
    }
};
</script>
</body>
</html>"""
    return html

# Flashcard endpoints
@app.post("/api/flashcards/sets")
async def create_flashcard_set(request: FlashcardSetRequest):
    """Create a new flashcard set."""
    try:
        s = flashcard_gen.create_set(
            user_id="default_user",
            name=request.name,
            description=request.description,
            topics=request.topics,
            lectures=request.lectures,
        )
        return {
            "id": s.id,
            "name": s.name,
            "card_count": s.card_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/flashcards/sets")
async def list_flashcard_sets():
    """List all flashcard sets for the user."""
    try:
        sets = flashcard_gen.list_sets("default_user")
        return [
            {
                "id": s.id,
                "name": s.name,
                "card_count": s.card_count,
                "created_date": s.created_date.isoformat(),
            }
            for s in sets
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/flashcards/sets/{set_id}")
async def get_flashcard_set(set_id: int):
    """Get a specific flashcard set with all cards."""
    try:
        s = flashcard_gen.get_set(set_id)
        if not s:
            raise HTTPException(status_code=404, detail="Set not found")
        
        return {
            "id": s.id,
            "name": s.name,
            "card_count": s.card_count,
            "cards": [
                {
                    "id": card.id,
                    "card_num": card.card_num,
                    "front": card.front,
                    "back": card.back,
                    "citation": card.citation,
                    "card_type": card.card_type or "definition",
                }
                for card in s.cards
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Other endpoints (quiz, search, etc.)
@app.post("/api/tests/create")
async def create_test(request: TestRequest):
    """Create a new quiz."""
    try:
        test = test_gen.generate_test(
            user_id="default_user",
            num_questions=request.num_questions,
            topics=request.topics,
            lectures=request.lectures,
        )
        return {"test_id": test.id, "question_count": len(test.questions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ask")
async def ask(request: QueryRequest):
    """Query the knowledge base."""
    try:
        result = rag_engine.query(request.question, top_k=request.top_k)
        return {
            "answer": result.get("answer", "No answer found"),
            "sources": result.get("sources", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("ECON_PORT", settings.API_PORT or 8100))
    print(f"Starting Economics RAG on http://127.0.0.1:{port}/")
    uvicorn.run(app, host="0.0.0.0", port=port)
