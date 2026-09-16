"""Unified FastAPI web server for multiple RAG systems (Economics, Nursing, etc.)."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import os

# Import both RAG systems
from econ_rag.services.rag_engine import RAGEngine as EconRAGEngine
from econ_rag.services.test_generator import TestGenerator as EconTestGenerator
from econ_rag.database import get_session as econ_get_session, Document as EconDocument, Concept as EconConcept
from econ_rag.config import settings as econ_settings

try:
    from nursing_rag.services.rag_engine import RAGEngine as NursingRAGEngine
    from nursing_rag.services.test_generator import TestGenerator as NursingTestGenerator
    from nursing_rag.database import get_session as nursing_get_session, Document as NursingDocument, Concept as NursingConcept
    from nursing_rag.config import settings as nursing_settings
    NURSING_AVAILABLE = True
except ImportError:
    NURSING_AVAILABLE = False
    NursingConcept = None

# Initialize FastAPI
app = FastAPI(
    title="RAG Systems Hub",
    version="1.0.0",
    description="Unified interface for multiple RAG systems"
)

# Lazy-loaded engine instances
_engines = {}

def get_system_engines(system_key):
    """Get or create RAG engines for a system."""
    if system_key not in _engines:
        if system_key == "econ":
            _engines[system_key] = {
                "rag_engine": EconRAGEngine(),
                "test_generator": EconTestGenerator(),
            }
        elif system_key == "nursing":
            _engines[system_key] = {
                "rag_engine": NursingRAGEngine(),
                "test_generator": NursingTestGenerator(),
            }
    return _engines[system_key]

# RAG system registry (metadata only, engines lazy-loaded)
SYSTEMS = {
    "econ": {
        "name": "Economics RAG",
        "description": "ECON 154: The Global Economy",
        "get_session": econ_get_session,
        "document_model": EconDocument,
        "concept_model": EconConcept,
        "color": "#3498db",
    },
}

if NURSING_AVAILABLE:
    SYSTEMS["nursing"] = {
        "name": "Nursing RAG",
        "description": "Nursing Knowledge System",
        "get_session": nursing_get_session,
        "document_model": NursingDocument,
        "concept_model": NursingConcept,
        "color": "#e74c3c",
    }

# Request/Response models
class QueryRequest(BaseModel):
    question: str
    top_k: int = 5

class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    chunk_count: int

class TestRequest(BaseModel):
    num_questions: int = 10
    topics: Optional[List[str]] = None

# Root redirect showing available systems
@app.get("/", response_class=HTMLResponse)
async def root():
    """Hub page listing available RAG systems."""
    systems_html = ""
    for key, system in SYSTEMS.items():
        systems_html += f"""
        <div class="system-card">
            <div class="system-color" style="background: {system['color']};"></div>
            <h3>{system['name']}</h3>
            <p>{system['description']}</p>
            <a href="/{key}/" class="btn">Open</a>
        </div>
        """
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>RAG Systems Hub</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
        .hub {{ max-width: 900px; margin: 0 auto; padding: 40px 20px; }}
        .hub-header {{ text-align: center; color: white; margin-bottom: 50px; }}
        .hub-header h1 {{ font-size: 48px; margin-bottom: 10px; }}
        .hub-header p {{ font-size: 18px; opacity: 0.9; }}
        .systems-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 30px; }}
        .system-card {{ background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,0.2); transition: transform 0.2s; }}
        .system-card:hover {{ transform: translateY(-5px); }}
        .system-color {{ height: 8px; }}
        .system-card h3 {{ padding: 25px 25px 10px; font-size: 22px; color: #2c3e50; }}
        .system-card p {{ padding: 0 25px 25px; color: #7f8c8d; font-size: 14px; line-height: 1.6; }}
        .btn {{ display: inline-block; padding: 12px 30px; background: #3498db; color: white; text-decoration: none; border-radius: 6px; margin: 0 25px 25px; font-weight: bold; transition: background 0.2s; }}
        .btn:hover {{ background: #2980b9; }}
    </style>
</head>
<body>
    <div class="hub">
        <div class="hub-header">
            <h1>🎓 RAG Systems</h1>
            <p>Multi-subject learning platform</p>
        </div>
        <div class="systems-grid">
            {systems_html}
        </div>
    </div>
</body>
</html>"""
    return html

# Generate UI for a specific RAG system
def generate_rag_ui(system_key: str, system: dict) -> str:
    """Generate the HTML UI for a RAG system."""
    color = system["color"]
    name = system["name"]
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{name}</title>
    <style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }}
.container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
.login-page {{ display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
.login-box {{ background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }}
.login-box h1 {{ text-align: center; margin-bottom: 30px; color: #2c3e50; }}
.login-box input {{ width: 100%; padding: 12px; margin-bottom: 15px; border: 2px solid #ddd; border-radius: 4px; font-size: 16px; }}
.login-box button {{ width: 100%; padding: 12px; background: {color}; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold; }}
.login-box button:hover {{ background: {color}cc; }}
.header {{ background: {color}; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
.header h1 {{ font-size: 24px; }}
.logout-btn, .back-btn {{ background: #e74c3c; padding: 8px 16px; border: none; color: white; border-radius: 4px; cursor: pointer; margin-right: 10px; }}
.main-page {{ display: none; }}
.nav-tabs {{ display: flex; gap: 10px; margin-bottom: 20px; }}
.nav-tabs button {{ padding: 10px 20px; background: white; border: 2px solid #ddd; border-radius: 4px; cursor: pointer; }}
.nav-tabs button.active {{ background: {color}; color: white; border-color: {color}; }}
.tab-content {{ display: none; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.tab-content.active {{ display: block; }}
input, select {{ width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 4px; margin-bottom: 15px; font-size: 16px; }}
button.search-btn, button.test-btn {{ background: {color}; color: white; padding: 12px 30px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold; width: auto; }}
button.search-btn:hover, button.test-btn:hover {{ background: {color}cc; }}
.result-item, .test-item {{ background: #f9f9f9; padding: 20px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid {color}; }}
.source {{ background: #ecf0f1; padding: 10px; border-radius: 4px; margin: 10px 0; font-size: 14px; }}
.question {{ background: white; padding: 15px; border-radius: 4px; margin-bottom: 15px; border-left: 4px solid #f39c12; }}
.option {{ margin: 10px 0; }}
.option input {{ width: auto; margin-right: 8px; }}
.loading {{ color: {color}; font-style: italic; }}
.error {{ color: #e74c3c; background: #fadbd8; padding: 10px; border-radius: 4px; }}
.success {{ color: #27ae60; background: #d5f4e6; padding: 10px; border-radius: 4px; }}
</style>
</head>
<body>
<div id="loginPage" class="login-page">
    <div class="login-box">
        <h1>{name}</h1>
        <input type="text" id="username" placeholder="Enter your name" />
        <button onclick="login()">Login</button>
    </div>
</div>
<div id="mainPage" class="main-page">
    <div class="header">
        <div><h1>{name}</h1><p id="userGreeting"></p></div>
        <button class="back-btn" onclick="goHome()">Home</button>
        <button class="logout-btn" onclick="logout()">Logout</button>
    </div>
    <div class="nav-tabs">
        <button class="active" onclick="switchTab('search')">Search</button>
        <button onclick="switchTab('test')">Generate Test</button>
        <button onclick="switchTab('history')">History</button>
    </div>
    <div id="search" class="tab-content active">
        <h2>Search Knowledge Base</h2>
        <input type="text" id="query" placeholder="Ask a question..." />
        <button class="search-btn" onclick="search()">Search</button>
        <div id="searchResults"></div>
    </div>
    <div id="test" class="tab-content">
        <h2>Generate Test</h2>
        <input type="number" id="numQuestions" placeholder="Number of questions" value="10" />
        <button class="test-btn" onclick="generateTest()">Generate</button>
        <div id="testContent"></div>
    </div>
    <div id="history" class="tab-content">
        <h2>Test History</h2>
        <div id="historyContent"></div>
    </div>
</div>
<script>
const SYSTEM_KEY = '{system_key}';
const API_PREFIX = `/${{SYSTEM_KEY}}/api`;

function getUsername() {{ return localStorage.getItem(`${{SYSTEM_KEY}}_username`) || null; }}
function setUsername(u) {{ localStorage.setItem(`${{SYSTEM_KEY}}_username`, u); }}

function login() {{
    const username = document.getElementById('username').value.trim();
    if (!username) {{ alert('Please enter your name'); return; }}
    setUsername(username);
    document.getElementById('loginPage').style.display = 'none';
    document.getElementById('mainPage').style.display = 'block';
    document.getElementById('userGreeting').textContent = `Welcome, ${{username}}!`;
}}

function logout() {{
    localStorage.removeItem(`${{SYSTEM_KEY}}_username`);
    location.reload();
}}

function goHome() {{ window.location.href = '/'; }}

function switchTab(tab) {{
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.nav-tabs button').forEach(b => b.classList.remove('active'));
    document.getElementById(tab).classList.add('active');
    event.target.classList.add('active');
}}

async function search() {{
    const query = document.getElementById('query').value.trim();
    if (!query) {{ alert('Please enter a question'); return; }}
    
    document.getElementById('searchResults').innerHTML = '<p class="loading">Searching...</p>';
    
    try {{
        const response = await fetch(`${{API_PREFIX}}/ask`, {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{question: query}})
        }});
        const data = await response.json();
        
        let html = `<div class="result-item"><h3>Answer</h3><p>${{data.answer || 'No answer found'}}</p>`;
        if (data.sources) {{
            html += '<h4>Sources:</h4>';
            data.sources.forEach(s => {{
                html += `<div class="source">${{s.document_name}}, p. ${{s.page_num || '?'}}</div>`;
            }});
        }}
        html += '</div>';
        document.getElementById('searchResults').innerHTML = html;
    }} catch (e) {{
        document.getElementById('searchResults').innerHTML = `<p class="error">Error: ${{e.message}}</p>`;
    }}
}}

async function generateTest() {{
    const num = document.getElementById('numQuestions').value;
    document.getElementById('testContent').innerHTML = '<p class="loading">Generating test...</p>';
    
    try {{
        const response = await fetch(`${{API_PREFIX}}/tests/create`, {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{num_questions: parseInt(num)}})
        }});
        const test = await response.json();
        
        let html = `<h3>Test created with ${{test.question_count || 0}} questions</h3>`;
        if (test.questions) {{
            test.questions.forEach((q, i) => {{
                html += `<div class="question">
                    <strong>Q${{i+1}}: ${{q.text}}</strong>`;
                if (q.options) {{
                    q.options.forEach((opt, j) => {{
                        html += `<div class="option"><input type="radio" name="q${{i}}" value="${{j}}" /> ${{opt}}</div>`;
                    }});
                }}
                html += '</div>';
            }});
            html += '<button class="test-btn" onclick="submitTest()">Submit</button>';
        }}
        document.getElementById('testContent').innerHTML = html;
    }} catch (e) {{
        document.getElementById('testContent').innerHTML = `<p class="error">Error: ${{e.message}}</p>`;
    }}
}}

window.onload = function() {{
    const user = getUsername();
    if (user) {{
        document.getElementById('loginPage').style.display = 'none';
        document.getElementById('mainPage').style.display = 'block';
        document.getElementById('userGreeting').textContent = `Welcome, ${{user}}!`;
    }}
}};
</script>
</body>
</html>"""
    return html

# Create sub-routers for each RAG system
for system_key, system in SYSTEMS.items():
    
    @app.get(f"/{system_key}/", response_class=HTMLResponse)
    async def system_ui(key=system_key, sys=system):
        """Render UI for a specific RAG system."""
        return generate_rag_ui(key, sys)
    
    @app.post(f"/{system_key}/api/ask")
    async def ask_system(request: QueryRequest, key=system_key, sys=system):
        """Query the RAG system."""
        try:
            engines = get_system_engines(key)
            rag = engines["rag_engine"]
            result = rag.query(request.question, top_k=request.top_k)
            return {
                "answer": result.get("answer", "No answer found"),
                "sources": result.get("sources", []),
                "chunk_count": result.get("chunk_count", 0)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get(f"/{system_key}/api/topics")
    async def list_topics(key=system_key, sys=system):
        """Get available topics for filtering quizzes."""
        try:
            session = sys["get_session"]()
            concept_model = sys["concept_model"]
            topics = session.query(concept_model.topic).distinct().filter(concept_model.topic != None).all()
            session.close()
            topic_list = sorted(list(set([t[0] for t in topics])))
            return {"topics": topic_list}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(f"/{system_key}/api/tests/create")
    async def create_test(request: TestRequest, key=system_key, sys=system):
        """Generate a test for the RAG system."""
        try:
            engines = get_system_engines(key)
            gen = engines["test_generator"]
            questions = gen.build_questions(
                num_questions=request.num_questions,
                topics=request.topics
            )
            return {
                "test_id": 1,
                "question_count": len(questions),
                "questions": questions
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
