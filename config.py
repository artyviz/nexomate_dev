# config.py
"""Central configuration for Nexomate MVP."""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = DATA_DIR / "exports"
IMPORTS_DIR = DATA_DIR / "imports"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
for d in [DATA_DIR, EXPORTS_DIR, IMPORTS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Environment ──────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=BASE_DIR / ".env")

try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for k, v in st.secrets.items():
            if isinstance(v, str) and k not in os.environ:
                os.environ[k] = v
except Exception:
    pass

# ── SMTP ─────────────────────────────────────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# ── IMAP (for reply tracking) ───────────────────────────────────────────────
IMAP_HOST = os.getenv("IMAP_HOST", "")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER = os.getenv("IMAP_USER", "")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", "")

# ── AI Provider ──────────────────────────────────────────────────────────────
# AI_PROVIDER: "auto" (try Groq→Ollama), "groq" (cloud only), "ollama" (local only)
AI_PROVIDER = os.getenv("AI_PROVIDER", "auto")

# ── Groq (Free Cloud AI) ────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "Nexomate")


# ── Ollama (Local AI) ───────────────────────────────────────────────────────
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

# ── Batch Email Settings ─────────────────────────────────────────────────────
EMAIL_BATCH_SIZE = int(os.getenv("EMAIL_BATCH_SIZE", "25"))
EMAIL_BATCH_DELAY_SECONDS = int(os.getenv("EMAIL_BATCH_DELAY_SECONDS", "3"))

# ── Lead status options ──────────────────────────────────────────────────────
LEAD_STATUSES = [
    "NEW", "REVIEWED", "SELECTED", "CONTACTED", "REPLIED",
    "INTERESTED", "NOT_INTERESTED", "FOLLOW_UP", "CONVERTED", "LOST",
]

EMAIL_STATUSES = [
    "NONE", "DRAFT", "SCHEDULED", "SENDING", "SENT", "DELIVERED",
    "OPENED", "CLICKED", "REPLIED", "BOUNCED", "FAILED",
]

CAMPAIGN_STATUSES = ["DRAFT", "READY", "RUNNING", "PAUSED", "COMPLETED"]

TONE_OPTIONS = ["Professional", "Friendly", "Direct", "Casual"]

REPLY_CLASSIFICATIONS = [
    "INTERESTED", "NOT_INTERESTED", "QUESTION",
    "FOLLOW_UP", "OUT_OF_OFFICE", "UNKNOWN",
]
