#!/bin/bash
set -e

# Port provided by Render, default to 8501 if unset
PORT=${PORT:-8501}

echo "=== Starting Nexomate Lead Engine ==="

# 1. Start FastAPI backend daemon on port 8000
echo "Starting FastAPI backend on port 8000..."
python lead-workflow-demo/server.py &

# 2. Start WhatsApp Linked Device Bridge on port 8001 (if node is available)
if command -v node >/dev/null 2>&1; then
    echo "Starting WhatsApp Bridge on port 8001..."
    (cd whatsapp-bridge && node bridge.js) &
else
    echo "Node.js not detected, skipping local WhatsApp bridge daemon."
fi

# 3. Start Streamlit web frontend on $PORT
echo "Starting Streamlit UI on port $PORT..."
exec streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
