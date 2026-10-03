#!/usr/bin/env bash
set -e

echo "=== Nexomate Build Script for Render ==="

# 1. Install Python requirements
echo "Step 1: Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 2. Setup Node.js runtime if not present
if command -v node >/dev/null 2>&1; then
    echo "Node.js detected: $(node -v)"
else
    echo "Node.js not in PATH. Bootstrapping standalone Node.js..."
    NODE_VER="v20.18.0"
    NODE_DIR="$HOME/.node"
    mkdir -p "$NODE_DIR"
    curl -fsSL "https://nodejs.org/dist/${NODE_VER}/node-${NODE_VER}-linux-x64.tar.gz" -o /tmp/node.tar.gz
    tar -xzf /tmp/node.tar.gz -C "$NODE_DIR" --strip-components=1
    rm /tmp/node.tar.gz
    export PATH="$NODE_DIR/bin:$PATH"
    echo "Installed standalone Node.js: $(node -v)"
fi

# 3. Install WhatsApp bridge dependencies
if [ -d "whatsapp-bridge" ]; then
    echo "Step 2: Installing WhatsApp Baileys bridge dependencies..."
    cd whatsapp-bridge
    npm install --omit=dev
    cd ..
    echo "WhatsApp bridge dependencies installed successfully."
fi

echo "=== Nexomate Build Succeeded ==="
