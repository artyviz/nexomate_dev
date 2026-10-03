FROM python:3.11-slim

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies + Node.js 20
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    build-essential \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy WhatsApp bridge and install Node dependencies
COPY whatsapp-bridge/package*.json whatsapp-bridge/
RUN cd whatsapp-bridge && npm install --omit=dev

# Copy entire application code
COPY . .

# Ensure start script is executable
RUN chmod +x start.sh

# Render provides the PORT env var (e.g. 10000)
EXPOSE 8501 8000 8001

CMD ["./start.sh"]
