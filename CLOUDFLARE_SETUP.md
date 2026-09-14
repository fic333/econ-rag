# Persistent Cloudflare Tunnel Setup

Run both the RAG server and a persistent Cloudflare tunnel in one terminal with a stable URL.

## One-Time Setup

```bash
./setup-tunnel.sh
```

This:
1. ✅ Authenticates with your Cloudflare account (opens browser)
2. ✅ Creates a named tunnel (persistent—same URL every time)
3. ✅ Saves tunnel config to `~/.cloudflared/config.yml`

You'll be asked for a tunnel name. Choose something like `rag-hub` or `econ-nursing`.

**Output will show your URL:**
```
Your URL will be: https://rag-hub.pages.dev/
```

This URL is **permanent**—it won't change on restart.

## Launch Both Server + Tunnel

Now, anytime you want to run both systems with remote access:

```bash
./launch-all.sh
```

This starts:
- ✅ RAG server on `http://127.0.0.1:8100`
- ✅ Cloudflare tunnel routing to your domain

**Output:**
```
═══════════════════════════════════════════════════════
✅ ALL SYSTEMS RUNNING
═══════════════════════════════════════════════════════

Local URLs:
  Hub:      http://127.0.0.1:8100/
  Econ RAG: http://127.0.0.1:8100/econ/
  Nursing:  http://127.0.0.1:8100/nursing/

Remote URL (via Cloudflare):
  https://rag-hub.pages.dev/

  /econ/    - Economics RAG
  /nursing/ - Nursing RAG

Press Ctrl+C to stop both services
```

## Usage

**Local access** (on your machine):
```
http://127.0.0.1:8100/econ/
http://127.0.0.1:8100/nursing/
```

**Remote access** (from anywhere via Cloudflare):
```
https://rag-hub.pages.dev/econ/
https://rag-hub.pages.dev/nursing/
```

## Custom Domain (Optional)

If you own a domain (e.g., `example.com`):

```bash
cloudflared tunnel route dns rag-hub example.com
```

Then your URL becomes:
```
https://example.com/econ/
https://example.com/nursing/
```

Check your Cloudflare dashboard to verify the CNAME record.

## Stopping

Press `Ctrl+C` in the terminal running `launch-all.sh` to stop both:
- RAG server
- Cloudflare tunnel

Both shut down cleanly.

## Troubleshooting

### "Tunnel not configured"
```bash
./setup-tunnel.sh
```

### "cloudflared not found"
```bash
brew install cloudflare/cloudflare/cloudflared
```

### "Permission denied" on scripts
```bash
chmod +x setup-tunnel.sh launch-all.sh
```

### Tunnel keeps disconnecting
- Normal: tunnel needs authentication once per device
- Solution: Run `./setup-tunnel.sh` again, or check `~/.cloudflared/config.yml` exists

### Can't access from remote
1. Check Cloudflare status in dashboard
2. Verify local server works: `http://127.0.0.1:8100/econ/`
3. Check cloudflared logs: `~/.cloudflared/*.log`

## Scripts Summary

| Script | Purpose |
|--------|---------|
| `setup-tunnel.sh` | One-time: auth Cloudflare, create tunnel (run once) |
| `launch-all.sh` | Anytime: start server + persistent tunnel (use every session) |
| `serve-both.sh` | Local-only: start server without tunnel |

