#!/bin/bash

# ==============================================================================
# Django + Cloudflare Tunnel Deployment Script
# ==============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PORT=8000
HOST="0.0.0.0"

echo -e "${YELLOW}Starting Deployment...${NC}"

# 1. Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo -e "${RED}Error: cloudflared is not installed.${NC}"
    echo "Install it using: brew install cloudflared"
    exit 1
fi

# 2. Start the Django Server in the background
echo -e "${YELLOW}Starting Django Server on ${HOST}:${PORT}...${NC}"
python manage.py runserver ${HOST}:${PORT} &
DJANGO_PID=\$!

# Wait a moment for the server to start
sleep 3

# Check if the server started successfully
if ! kill -0 \$DJANGO_PID 2>/dev/null; then
    echo -e "${RED}Failed to start Django server.${NC}"
    exit 1
fi

echo -e "${GREEN}Django Server is running (PID: \$DJANGO_PID)${NC}"

# 3. Clean up child processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    echo "Stopping Cloudflare Tunnel..."
    kill \$TUNNEL_PID 2>/dev/null
    echo "Stopping Django Server..."
    kill \$DJANGO_PID 2>/dev/null
    exit 0
}

# Trap termination signals to ensure cleanup
trap cleanup SIGINT SIGTERM

# 4. Start Cloudflare Tunnel and parse the URL
echo -e "${YELLOW}Starting Cloudflare Tunnel...${NC}"

# Run cloudflared and capture both stdout and stderr
cloudflared tunnel --url http://localhost:${PORT} 2>&1 | tee cloudflared_output.tmp &
TUNNEL_PID=\$!

echo -e "\n${YELLOW}Waiting for tunnel URL...${NC}"

# Loop to extract the URL from the output file
for i in {1..15}; do
    URL=\$(grep -o 'https://.*\.trycloudflare\.com' cloudflared_output.tmp | head -n 1)
    if [ ! -z "\$URL" ]; then
        echo -e "\n============================================================"
        echo -e "${GREEN}🚀 SERVER IS LIVE!${NC}"
        echo -e "Public URL: ${GREEN}\$URL${NC}"
        echo -e "============================================================\n"
        break
    fi
    sleep 1
done

if [ -z "\$URL" ]; then
    echo -e "${RED}Timed out waiting for tunnel URL. The tunnel might still be starting.${NC}"
    echo "Check cloudflared_output.tmp for details."
fi

# Remove the temporary output file
rm cloudflared_output.tmp

# Wait indefinitely until interrupted (Ctrl+C)
echo -e "${YELLOW}Press Ctrl+C to stop the server and tunnel.${NC}"
wait \$DJANGO_PID
