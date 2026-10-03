#!/bin/bash
set -e

# Prepend portable node directories if present
if [ -d "$HOME/.node/bin" ]; then
    export PATH="$HOME/.node/bin:$PATH"
fi
if [ -d "/app/.node_runtime/bin" ]; then
    export PATH="/app/.node_runtime/bin:$PATH"
fi
if [ -d "./.node_runtime/bin" ]; then
    export PATH="$(pwd)/.node_runtime/bin:$PATH"
fi

# Port provided by Render, default to 8501 if unset
PORT=${PORT:-8501}

echo "=== Starting Nexomate Lead Engine ==="

# 1. Start FastAPI backend daemon on port 8000
echo "Starting FastAPI backend on port 8000..."
BACKEND_PORT=8000 python lead-workflow-demo/server.py &

# 2. Start WhatsApp Linked Device Bridge on port 8001
if command -v node >/dev/null 2>&1; then
    echo "Starting WhatsApp Bridge on port 8001 (node: $(command -v node))..."
    (cd whatsapp-bridge && node bridge.js) &
else
    echo "Node.js not in PATH; background service_manager will bootstrap it automatically."
fi

# 3. Start Streamlit web frontend on $PORT
echo "Starting Streamlit UI on port $PORT..."
exec streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
