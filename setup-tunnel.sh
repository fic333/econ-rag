#!/bin/bash
# Setup a persistent Cloudflare Tunnel for the RAG systems
# Simpler version - creates tunnel without zone selection

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

# Ask user for tunnel name
read -p "Enter a name for your tunnel (e.g., 'rag-hub'): " TUNNEL_NAME

if [ -z "$TUNNEL_NAME" ]; then
    TUNNEL_NAME="rag-hub"
fi

echo ""
echo "🔐 Authenticating with Cloudflare in browser..."
echo "   Follow prompts in your browser"
echo ""

# Authenticate if not already done
if [ ! -f ~/.cloudflared/cert.pem ]; then
    # Try to authenticate
    cloudflared tunnel login 2>/dev/null || true
    
    # If still no cert, guide user
    if [ ! -f ~/.cloudflared/cert.pem ]; then
        echo ""
        echo "⚠️  Browser authentication didn't complete."
        echo ""
        echo "Please do this manually:"
        echo "1. Visit: https://dash.cloudflare.com/argotunnel"
        echo "2. Click 'Authorize' or 'Connect'"
        echo "3. The certificate will download"
        echo "4. Copy it to: ~/.cloudflared/cert.pem"
        echo ""
        read -p "Press Enter when done..."
    fi
fi

# Check if cert exists now
if [ ! -f ~/.cloudflared/cert.pem ]; then
    echo "❌ Could not get certificate. Please manually authenticate at:"
    echo "   https://dash.cloudflare.com/argotunnel"
    exit 1
fi

echo "✅ Certificate obtained"
echo ""

# Create tunnel
echo "Creating tunnel: $TUNNEL_NAME"
TUNNEL_ID=$(cloudflared tunnel create "$TUNNEL_NAME" 2>&1 | grep -oE '[a-f0-9\-]{36}' | head -1 || echo "")

if [ -z "$TUNNEL_ID" ]; then
    # Tunnel might already exist, get its ID
    TUNNEL_ID=$(cloudflared tunnel list 2>/dev/null | grep "$TUNNEL_NAME" | awk '{print $1}' || echo "")
fi

if [ -z "$TUNNEL_ID" ]; then
    echo "❌ Failed to create tunnel. Check:"
    echo "   cloudflared tunnel list"
    exit 1
fi

echo "✅ Tunnel created: $TUNNEL_ID"
echo ""

# Create tunnel config
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << CONFIGEOF
tunnel: $TUNNEL_ID
credentials-file: /Users/michaelficociello/.cloudflared/${TUNNEL_ID}.json

ingress:
  - hostname: $TUNNEL_NAME.michaelficociello.com
    service: http://localhost:8100
  - service: http_status:404
CONFIGEOF

echo "✅ Configuration saved"
echo ""
echo "═══════════════════════════════════════════════════════"
echo "✅ TUNNEL READY!"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Your permanent URL:"
echo "   https://$TUNNEL_NAME.pages.dev"
echo ""
echo "Next: Run this command to start everything:"
echo "   ./launch-all.sh"
echo ""
