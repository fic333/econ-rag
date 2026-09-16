#!/bin/bash
# Launch both RAG server and persistent Cloudflare tunnel in one terminal
# Routes to both /econ/ and /nursing/ paths

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if setup was done
if [ ! -f ~/.cloudflared/config.yml ]; then
    echo "❌ Tunnel not configured. Run setup first:"
    echo "   ./setup-tunnel.sh"
    exit 1
fi

# Extract tunnel name from config
TUNNEL_NAME=$(grep "^tunnel:" ~/.cloudflared/config.yml | awk '{print $2}')

# Kill any existing processes on port 8100 (optional cleanup)
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    pkill -f "uvicorn web.app:app" 2>/dev/null || true
    pkill -f "cloudflared tunnel run" 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start the RAG server in background
echo -e "${BLUE}🚀 Starting unified RAG server...${NC}"
export PYTHONPATH="${PYTHONPATH}:${HOME}/Documents/projects/nursing-rag"
cd ~/Documents/projects/econ-rag
./.venv/bin/python web/app.py > /tmp/rag_server.log 2>&1 &
RAG_PID=$!

# Give server time to start
sleep 2

# Check if server started
if ! kill -0 $RAG_PID 2>/dev/null; then
    echo -e "${RED}❌ Server failed to start. Check log:${NC}"
    cat /tmp/rag_server.log
    exit 1
fi

echo -e "${GREEN}✅ RAG server running (PID: $RAG_PID)${NC}"

# Start Cloudflare tunnel
echo -e "${BLUE}🔗 Starting Cloudflare tunnel...${NC}"
sleep 1

# Run the persistent tunnel
cloudflared tunnel --config ~/.cloudflared/config.yml run $TUNNEL_NAME &
TUNNEL_PID=$!

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ ALL SYSTEMS RUNNING${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Local URLs:${NC}"
echo -e "  Hub:      ${YELLOW}http://127.0.0.1:8100/${NC}"
echo -e "  Econ RAG: ${YELLOW}http://127.0.0.1:8100/econ/${NC}"
echo -e "  Nursing:  ${YELLOW}http://127.0.0.1:8100/nursing/${NC}"
echo ""
echo -e "${BLUE}Remote URL (via Cloudflare):${NC}"
echo -e "  ${YELLOW}https://${TUNNEL_NAME}.pages.dev/${NC}"
echo ""
echo -e "  /econ/    - Economics RAG"
echo -e "  /nursing/ - Nursing RAG"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both services${NC}"
echo ""

# Wait for both processes
wait $RAG_PID $TUNNEL_PID

