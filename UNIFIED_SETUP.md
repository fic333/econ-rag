# Running Both RAG Systems on One Server

You can run both the Economics and Nursing RAGs on the same FastAPI instance using path-based routing.

## Single System Mode (Default)

To run **only** the Economics RAG:

```bash
./.venv/bin/econ-rag serve
# Opens at http://127.0.0.1:8100/
```

This uses the original single-system setup with no path prefix.

## Unified Mode (Both Systems)

To run **both** Economics and Nursing RAGs on the same port with different paths:

### Prerequisites

1. **Set up nursing-rag** (if not already done):
   ```bash
   cd ~/Documents/projects/nursing-rag
   ./setup.sh
   ```

2. **Ensure both projects have their databases**:
   - `~/Documents/projects/econ-rag/econ_rag.db` ✓
   - `~/Documents/projects/nursing-rag/nursing_rag.db` ✓

### Launch Unified Server

```bash
cd ~/Documents/projects/econ-rag
./serve-both.sh
```

This starts a unified FastAPI instance at `http://127.0.0.1:8100` serving:

- **Hub**: `http://127.0.0.1:8100/` — lists both systems
- **Economics**: `http://127.0.0.1:8100/econ/` — ECON 154 RAG
- **Nursing**: `http://127.0.0.1:8100/nursing/` — Nursing Knowledge System

Each system has:
- Separate databases (no data mixing)
- Separate progress tracking and test history
- Independent search and quiz generation
- Same polished web UI

### URLs for Cloudflare

Point your Cloudflare DNS to the same server IP, and use subdomains for clarity:

```
econ.example.com    → your-server:8100/econ/
nursing.example.com → your-server:8100/nursing/
```

Or use Cloudflare Workers to route:

```
econ.example.com/*    → localhost:8100/econ/*
nursing.example.com/* → localhost:8100/nursing/*
```

## Architecture

### Single System (Original)
```
FastAPI App (web/app.py)
├── /api/topics
├── /api/lectures
├── /api/tests
├── /api/ask
└── / (HTML UI)
```

Database: `econ_rag.db`

### Unified System (New)
```
FastAPI Hub (web/app.py)
├── / (Hub page listing both systems)
├── /econ/
│   ├── /econ/api/topics
│   ├── /econ/api/tests
│   ├── /econ/api/ask
│   └── /econ/ (HTML UI)
├── /nursing/
│   ├── /nursing/api/topics
│   ├── /nursing/api/tests
│   ├── /nursing/api/ask
│   └── /nursing/ (HTML UI)
└── ...
```

Databases: `econ_rag.db` + `nursing_rag.db` (independent)

## Switching Between Modes

### To use Economics-only again:

```bash
cd ~/Documents/projects/econ-rag
./.venv/bin/econ-rag serve
```

### To use both systems:

```bash
cd ~/Documents/projects/econ-rag
./serve-both.sh
```

## Troubleshooting

### "nursing_rag not found"

The unified server tries to import nursing_rag but falls back gracefully if missing.

To make nursing available:

1. **Ensure nursing-rag is installed** and has `__init__.py` files in all directories
2. **Check Python path**:
   ```bash
   python -c "import sys; print('\\n'.join(sys.path))"
   ```
   Should include `/Users/michaelficociello/Documents/projects/nursing-rag`

3. **The serve-both.sh script adds it to PYTHONPATH automatically**

### "port 8100 already in use"

Kill the existing process:

```bash
pkill -f "uvicorn web.app:app"
pkill -f "python web/app.py"
```

Then restart.

### Different databases aren't isolated

Ensure both projects have separate database URLs:

- **econ-rag/econ_rag/config.py**: `DATABASE_URL = "sqlite:///econ_rag.db"`
- **nursing-rag/nursing_rag/config.py**: `DATABASE_URL = "sqlite:///nursing_rag.db"`

Each system uses its own config and database file.

## Remote Access (Cloudflare Tunnel)

You can expose the unified server to the internet the same way:

```bash
cloudflared tunnel --url http://localhost:8100
```

This gives you a single URL like `https://example.trycloudflare.com` that serves all three endpoints:
- Hub: `/`
- Econ: `/econ/`
- Nursing: `/nursing/`

Or set up a custom domain:

```bash
cloudflared tunnel create rag-hub
cloudflared tunnel route dns rag-hub example.com
cloudflared tunnel run --url http://localhost:8100 rag-hub
```

Then:
- `https://example.com/econ/`
- `https://example.com/nursing/`
