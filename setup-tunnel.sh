#!/bin/bash
# Setup a persistent Cloudflare Tunnel for the RAG systems
# Creates a named tunnel that keeps the same URL across restarts

set -e

echo "🔗 Setting up persistent Cloudflare Tunnel..."
echo ""

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared not found. Install with:"
    echo "   brew install cloudflare/cloudflare/cloudflared"
    exit 1
fi

# Create tunnel config directory
mkdir -p ~/.cloudflared

# Check if already authenticated
if [ ! -f ~/.cloudflared/cert.pem ]; then
    echo "🔐 Authenticating with Cloudflare..."
    echo "   This will open your browser to log in."
    cloudflared tunnel login
    echo "✅ Authentication complete"
fi

# Ask user for tunnel name
read -p "Enter a name for your tunnel (e.g., 'rag-hub'): " TUNNEL_NAME

if [ -z "$TUNNEL_NAME" ]; then
    TUNNEL_NAME="rag-hub"
fi

# Create tunnel if it doesn't exist
TUNNEL_ID=$(cloudflared tunnel list 2>/dev/null | grep "$TUNNEL_NAME" | awk '{print $1}' || echo "")

if [ -z "$TUNNEL_ID" ]; then
    echo "Creating tunnel: $TUNNEL_NAME"
    cloudflared tunnel create "$TUNNEL_NAME"
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
fi

echo "✅ Tunnel ID: $TUNNEL_ID"

# Create tunnel config
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << CONFIGEOF
tunnel: $TUNNEL_ID
credentials-file: /Users/michaelficociello/.cloudflared/${TUNNEL_ID}.json

ingress:
  - hostname: $TUNNEL_NAME.pages.dev
    service: http://localhost:8100
  - service: http_status:404
CONFIGEOF

echo "✅ Tunnel config created at ~/.cloudflared/config.yml"

# Route the tunnel to a domain (optional, uses pages.dev by default)
echo ""
echo "Your tunnel is ready! You can now use:"
echo "   ./launch-all.sh"
echo ""
echo "Your URL will be: https://$TUNNEL_NAME.pages.dev/"
echo ""
echo "For a custom domain, run:"
echo "   cloudflared tunnel route dns $TUNNEL_NAME yourdomain.com"
echo ""
