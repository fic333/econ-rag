# Quick Launch Guide

## One-Time Setup (First Time Only)

```bash
cd ~/Documents/projects/econ-rag
./setup-tunnel.sh
```

Answer the prompt and wait for Cloudflare authentication. You'll see:
```
Your URL will be: https://rag-hub.pages.dev/
```

**Done!** Your URL is now permanent.

---

## Every Time You Want to Use (Simple!)

```bash
cd ~/Documents/projects/econ-rag
./launch-all.sh
```

This starts:
- ✅ RAG server
- ✅ Cloudflare tunnel
- ✅ Both in one terminal

---

## Your URLs

**Local** (just you):
- Economics: `http://127.0.0.1:8100/econ/`
- Nursing: `http://127.0.0.1:8100/nursing/`

**Remote** (anyone, anywhere):
- Economics: `https://rag-hub.pages.dev/econ/`
- Nursing: `https://rag-hub.pages.dev/nursing/`

(Replace `rag-hub` with your tunnel name)

---

## To Stop

Press `Ctrl+C` in the terminal. Both server and tunnel stop cleanly.

---

## That's It!

No more:
- ❌ Multiple terminals
- ❌ Changing URLs every restart
- ❌ Manual tunnel commands

Just:
- ✅ `./launch-all.sh`
- ✅ Same URL every time
- ✅ Both services in one terminal

