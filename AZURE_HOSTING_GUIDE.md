# Azure Hosting Guide for Unified RAG System

**Date Created:** September 15, 2026  
**Status:** Ready for Azure deployment  
**Current Setup:** Local macOS with Cloudflare tunnel (fully functional)

---

## System Overview

### Architecture
- **Unified FastAPI Server** on port 8100 serving both RAG systems
- **Economics RAG** at `/econ/` path with flashcards, quizzes, and knowledge search
- **Nursing RAG** at `/nursing/` path with nursing knowledge base and study tools
- **Remote Access** via Cloudflare tunnel to `https://rag-hub.michaelficociello.com`

### Current Local Setup
```
Host: macOS
Server: FastAPI running on 0.0.0.0:8100
Tunnel: Cloudflare tunnel (ID: d17e1bbc-4064-4bf0-8c8d-17a8e0d771c9)
Auto-start: launchd services for both server and tunnel
Database: SQLite (econ_rag.db) + MySQL (nursing_rag)
```

---

## Project Structure

```
~/Documents/projects/
├── econ-rag/                          # Economics RAG system
│   ├── web/
│   │   └── app.py                     # Unified FastAPI server (serves both RAG systems)
│   ├── econ_rag/
│   │   ├── database.py                # SQLAlchemy models (Document, Chunk, Concept, Flashcard, Test, etc.)
│   │   ├── config.py                  # Environment config
│   │   ├── services/
│   │   │   ├── rag_engine.py          # RAG query engine
│   │   │   ├── flashcard_generator.py # Flashcard generation from concepts
│   │   │   └── test_generator.py      # Quiz/test generation
│   │   └── scripts/
│   │       └── init_db.py             # Database initialization
│   ├── pyproject.toml                 # Dependencies (FastAPI, SQLAlchemy, sentence-transformers, etc.)
│   ├── econ_rag.db                    # SQLite database (economics data)
│   └── CLOUDFLARE_SETUP.md            # Cloudflare tunnel setup docs
│
└── nursing-rag/                       # Nursing RAG system
    ├── nursing_rag/
    │   ├── database.py                # SQLAlchemy models (Document, Chunk, etc.)
    │   ├── config.py                  # MySQL config, environment settings
    │   ├── services/
    │   │   ├── rag_engine.py          # RAG query engine
    │   │   └── test_generator.py      # Test generation
    │   └── scripts/
    │       └── init_db.py             # Database initialization
    ├── pyproject.toml                 # Dependencies (includes PyMySQL for MySQL)
    ├── nursing_rag.db                 # SQLite database (fallback/cache)
    ├── .env.example                   # MySQL configuration template
    └── QUICK_START.md                 # Setup guide
```

---

## Current Deployment (macOS)

### Server Startup
```bash
# Manual startup (current method)
cd /Users/michaelficociello/Documents/projects/econ-rag
PYTHONPATH="/Users/michaelficociello/Documents/projects/econ-rag:/Users/michaelficociello/Documents/projects/nursing-rag" \
  python3 web/app.py

# Auto-start via launchd (current setup)
launchctl load ~/Library/LaunchAgents/com.michaelficociello.ragserver.plist
```

### Tunnel Startup
```bash
# Manual startup (current method)
cloudflared tunnel run --token eyJhIjoiOWU5MjM4ZDljMDA0ODlhODU3NDkyOTNiNTZiZDU5OTYiLCJ0IjoiZDE3ZTFiYmMtNDA2NC00YmYwLThjOGQtMTdhOGUwZDc3MWM5IiwicyI6Ik5HWmxPV0ZoWXpBdE1UVTRNUzAwWTJFNExXRTBaR1V0TURFMk1XWmlOR1F5TVRGbSJ9

# Auto-start via launchd (current setup)
launchctl load ~/Library/LaunchAgents/com.michaelficociello.tunnel.plist
```

### Tunnel Configuration
```
Tunnel ID: d17e1bbc-4064-4bf0-8c8d-17a8e0d771c9
Domain: rag-hub.michaelficociello.com
Route: rag-hub.michaelficociello.com → http://localhost:8100
DNS Record: CNAME to rag-hub.d17e1bbc-4064-4bf0-8c8d-17a8e0d771c9.cfargotunnel.com
```

---

## Dependencies

### Economics RAG (econ-rag/pyproject.toml)
```toml
requires-python = ">=3.11"
dependencies = [
    "pypdf>=4.0",                    # PDF processing
    "sentence-transformers>=2.2",    # Embeddings (all-MiniLM-L6-v2 model)
    "sqlalchemy>=2.0",               # ORM
    "fastapi>=0.104",                # Web framework
    "uvicorn>=0.24",                 # ASGI server
    "pydantic>=2.0",                 # Data validation
    "pydantic-settings>=2.0",        # Config management
    "numpy>=1.24",                   # Numerical computing
    "click>=8.0",                    # CLI
]
```

### Nursing RAG (nursing-rag/pyproject.toml)
```toml
python = "^3.11"
dependencies = [
    "pypdf>=3.0",                    # PDF processing
    "python-docx>=0.8",              # DOCX processing
    "langchain>=0.1",                # LLM framework (optional)
    "sentence-transformers>=2.2",    # Embeddings
    "pymysql>=1.1",                  # MySQL driver
    "sqlalchemy>=2.0",               # ORM
    "fastapi>=0.104",                # Web framework
    "uvicorn>=0.24",                 # ASGI server
    "pydantic>=2.0",                 # Data validation
    "python-multipart>=0.0.6",       # Form data
    "click>=8.0",                    # CLI
    "python-dotenv>=1.0",            # .env loading
    "pydantic-settings>=2.0",        # Config management
]
```

---

## Database Schema

### Economics RAG (SQLite)
```sql
-- Core tables
documents          # Source materials (lecture notes, PDFs)
chunks             # Text passages with embeddings
concepts           # Mined term-definition pairs
tests              # Quiz sessions
test_questions     # Multiple-choice questions
topic_progress     # Per-topic performance tracking
query_history      # Search log
flashcard_sets     # User-created study sets
flashcards         # Individual flashcard (front/back)
```

### Nursing RAG (MySQL)
```sql
-- Similar structure
documents          # Nursing textbooks/materials
chunks             # Text passages
-- Plus nursing-specific tables as needed
```

---

## API Endpoints

### Economics RAG
```
GET  /econ/                            # Web UI
POST /econ/api/ask                     # Query RAG (search)
POST /econ/api/tests/create            # Generate quiz
GET  /api/flashcards/sets              # List flashcard sets
GET  /api/flashcards/sets/{id}         # Get flashcards
POST /api/flashcards/sets              # Create set
```

### Nursing RAG
```
GET  /nursing/                         # Web UI
POST /nursing/api/ask                  # Query RAG
POST /nursing/api/tests/create         # Generate quiz
```

### Hub
```
GET  /                                 # System selector (links to /econ/ and /nursing/)
```

---

## Environment Configuration

### Economics RAG (.env)
```
DATABASE_URL=sqlite:///./econ_rag.db
DEBUG=false
```

### Nursing RAG (.env)
```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=nursing_rag
DEBUG=false
```

---

## Azure Deployment Considerations

### Current vs Azure

| Component | Current (Local) | Azure Required |
|-----------|---|---|
| **Server** | FastAPI/Uvicorn | App Service, Container, or VM |
| **Database (Econ)** | SQLite file | SQL Database or Postgres |
| **Database (Nursing)** | MySQL locally | Azure MySQL or Cosmos DB |
| **Tunnel** | Cloudflare tunnel | Azure Application Gateway / Front Door |
| **Auto-start** | launchd (macOS) | Container restart policy or startup scripts |
| **Logging** | Local files | Application Insights / Log Analytics |
| **Secrets** | .env files | Azure Key Vault |

### Deployment Options

**Option 1: App Service (Recommended for simplicity)**
- Azure App Service (Linux) running Python 3.11+
- Azure SQL Database for econ_rag data
- Azure Database for MySQL for nursing_rag
- Azure Application Gateway for routing/SSL
- Application Insights for monitoring

**Option 2: Container (Recommended for scalability)**
- Dockerfile with Python 3.11
- Push to Azure Container Registry
- Deploy to Azure Container Instances or Kubernetes (AKS)
- Same database setup as Option 1

**Option 3: Virtual Machine**
- Azure VM (Linux) running the service directly
- MySQL database on VM or managed Azure MySQL
- Nginx reverse proxy for SSL/routing

---

## Key Deployment Steps (Planned)

1. **Create Azure SQL/MySQL databases**
   - Migrate econ_rag.db to Azure SQL
   - Migrate nursing_rag MySQL to Azure MySQL

2. **Containerize application** (if using containers)
   - Create Dockerfile
   - Build and push to Azure Container Registry

3. **Deploy to Azure**
   - App Service: Deploy code directly or via GitHub Actions
   - Containers: Deploy to ACI/AKS
   - Configure connection strings in Azure Key Vault

4. **Set up networking**
   - Azure Application Gateway for routing
   - SSL certificate (Azure Managed Certificate or custom)
   - Remove Cloudflare tunnel (no longer needed with public Azure endpoint)

5. **Configure auto-scaling**
   - App Service auto-scale based on CPU/memory
   - Implement health checks

6. **Set up monitoring**
   - Application Insights for logging
   - Azure Monitor alerts for errors/performance

---

## Current Cloudflare Tunnel Details

**Note:** This will be replaced by Azure's native networking.

```
Tunnel ID: d17e1bbc-4064-4bf0-8c8d-17a8e0d771c9
Domain: rag-hub.michaelficociello.com
Service Token: [long base64 token stored in launchd plist]
DNS Record: CNAME pointing to cfargotunnel.com
```

After Azure deployment, DNS will point directly to Azure Application Gateway/Static Web App.

---

## Data & Assets

### Included in Econ RAG
- Economics lecture notes (PDFs)
- Generated concepts, definitions, flashcards
- Sample quiz questions
- User progress data (if any)

### Included in Nursing RAG
- Nursing textbooks (5+ markdown files)
- Mined concepts and passages
- Embedded vectors (cached in database)
- Sample quiz questions

---

## Additional Notes

### Performance Characteristics (Current)
- RAG query latency: ~200-500ms (embedding + search)
- Flashcard load: <100ms
- Quiz generation: ~1-2 seconds
- Concurrent users supported: 5-10 (single server, no load balancing)

### Scaling Considerations for Azure
- Stateless server design (can scale horizontally)
- Database bottleneck (especially nursing_rag on MySQL)
- Embedding generation (sentence-transformers) is CPU-intensive
- Consider caching query results or using Redis

### Security
- No API authentication currently (localhost only during testing)
- Azure deployment should add:
  - Azure AD/Entra ID for user auth
  - API keys or OAuth2
  - CORS restrictions
  - Rate limiting

---

## Files to Migrate

```
Source → Azure Storage/Databases
econ_rag.db → Azure SQL Database
nursing_rag database → Azure MySQL
web/app.py → App Service / Container
econ_rag/ module → App Service / Container
nursing_rag/ module → App Service / Container
```

---

## Contact & Questions

- **Economics RAG**: econ_rag module in /econ-rag directory
- **Nursing RAG**: nursing_rag module in /nursing-rag directory
- **Unified Server**: web/app.py in /econ-rag/web/

For Azure deployment help, refer to this document and provide:
1. Preferred Azure tier (free, standard, premium)
2. Expected concurrent users
3. Database size estimates
4. Budget constraints
