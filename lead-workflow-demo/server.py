"""Nexomate Lead-to-Customer live demo server.

Runs the full workflow from "Final Workflow.pdf" over WhatsApp (Twilio) and Email
(SMTP/IMAP) with a Groq LLM. Every channel has a MOCK mode so the demo is always safe.

Run:  python server.py     ->  http://localhost:8000
"""
import imaplib
import email as emaillib
import json
import os
import re
import smtplib
import threading
import time
import uuid
from email.header import decode_header
from email.mime.text import MIMEText
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import parse_qs

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import sys
HERE = Path(__file__).parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))
load_dotenv(HERE.parent / ".env")   # reuse the main project's SMTP/IMAP/Groq settings
load_dotenv(HERE / ".env", override=True)

def env(k, d=""):
    return os.getenv(k, d).strip()

BUSINESS = env("BUSINESS_NAME", "Nexomate")
AGENT = env("AGENT_NAME", "Maya")
GROQ_KEY = env("GROQ_API_KEY")
GROQ_MODEL = env("DEMO_GROQ_MODEL", "openai/gpt-oss-20b")
TW_SID, TW_TOKEN = env("TWILIO_ACCOUNT_SID"), env("TWILIO_AUTH_TOKEN")
TW_FROM = env("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
SMTP_HOST, SMTP_PORT = env("SMTP_HOST"), int(env("SMTP_PORT", "587") or 587)
SMTP_USER, SMTP_PASS = env("SMTP_USER"), env("SMTP_PASSWORD")
IMAP_HOST, IMAP_PORT = env("IMAP_HOST"), int(env("IMAP_PORT", "993") or 993)
IMAP_USER, IMAP_PASS = env("IMAP_USER") or SMTP_USER, env("IMAP_PASSWORD") or SMTP_PASS
SALES_EMAIL = env("SALES_NOTIFY_EMAIL")
FOLLOWUP_SECONDS = int(env("FOLLOWUP_SECONDS", "45"))

STAGES = ["captured", "engaged", "qualified", "scored", "routed", "booked", "reminded",
          "attended", "proposal", "won", "onboarded", "review", "retained"]

STATE = {"mode": "live" if (TW_SID and TW_TOKEN) else "mock", "auto_followup": True}
LEADS: dict[str, dict] = {}
LOCK = threading.RLock()

app = FastAPI(title="Nexomate Live Demo")


# ───────────────────────── helpers ─────────────────────────
def now():
    return time.strftime("%H:%M:%S")

def log(lead, text):
    lead["log"].append({"ts": now(), "text": text})

def set_stage(lead, stage):
    if STAGES.index(stage) > STAGES.index(lead["stage"]):
        lead["stage"] = stage

def whatsapp_ready():
    return bool(TW_SID and TW_TOKEN)

def email_ready():
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASS)

def norm_phone(p):
    p = re.sub(r"[^\d+]", "", p or "")
    return p if p.startswith("+") or not p else "+" + p


# ───────────────────────── channels ─────────────────────────
def send_whatsapp(lead, text):
    if (STATE["mode"] == "live" or lead.get("is_live")) and whatsapp_ready() and lead.get("phone"):
        try:
            r = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{TW_SID}/Messages.json",
                auth=(TW_SID, TW_TOKEN),
                data={"From": TW_FROM, "To": f"whatsapp:{lead['phone']}", "Body": text}, timeout=20)
            if r.status_code >= 300:
                log(lead, f"⚠️ WhatsApp send failed ({r.status_code}): {r.text[:120]}")
                return False
            log(lead, "📲 WhatsApp delivered via Twilio")
            return True
        except Exception as e:
            log(lead, f"⚠️ WhatsApp error: {e}")
            return False
    elif STATE["mode"] == "live":
        log(lead, "⚠️ Live WhatsApp not configured – shown in mock only")
    return True

def send_email(lead, subject, text):
    if STATE["mode"] == "live" and email_ready() and lead["email"]:
        msg = MIMEText(text, "plain", "utf-8")
        msg["Subject"], msg["From"], msg["To"] = subject, f"{AGENT} · {BUSINESS} <{SMTP_USER}>", lead["email"]
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
                s.starttls(); s.login(SMTP_USER, SMTP_PASS); s.send_message(msg)
            log(lead, "✉️ Email delivered via SMTP")
        except Exception as e:  # noqa
            log(lead, f"⚠️ Email send failed: {e}")
            return False
    elif STATE["mode"] == "live":
        log(lead, "⚠️ Live email not configured – shown in mock only")
    return True

MEDIA = {
    "brochure": {"kind": "brochure", "title": f"{BUSINESS} – Product Brochure.pdf", "desc": "PDF · 2.4 MB · How AI WhatsApp automation works",
                 "url": env("BROCHURE_URL", "https://getnexomate.com/brochure.pdf")},
    "demo_video": {"kind": "video", "title": f"{BUSINESS} – 90s Product Demo", "desc": "Video · 1:30 · See a lead go from click to booked",
                   "url": env("DEMO_VIDEO_URL", "https://getnexomate.com/demo")},
    "case_study": {"kind": "brochure", "title": "Case Study – 3x faster response.pdf", "desc": "PDF · 1.1 MB · Real customer results",
                   "url": env("CASE_STUDY_URL", "https://getnexomate.com/case-study.pdf")},
}

def outbound(lead, channel, text, subject=None, buttons=None, media=None):
    subject = subject or f"{BUSINESS} – {lead['name']}, about your enquiry"
    link = f"\n\n📎 {media['title']}: {media['url']}" if media else ""
    if channel == "email":
        text_out = f"{text}{link}\n\nWarm regards,\n{AGENT}\n{BUSINESS}"
        send_email(lead, subject, text_out)
    else:
        text_out = text
        send_whatsapp(lead, text + link)
    lead["messages"].append({"id": uuid.uuid4().hex[:8], "ts": now(), "channel": channel,
                             "dir": "out", "text": text_out, "subject": subject if channel == "email" else None,
                             "buttons": (buttons or []) if channel == "whatsapp" else [], "media": media})
    lead["awaiting"], lead["last_out"] = True, time.time()

def broadcast(lead, text, subject=None, **kw):
    for ch in lead["channels"]:
        outbound(lead, ch, text, subject, **kw)


# ───────────────────────── AI ─────────────────────────
SYSTEM = f"""You are {AGENT}, the friendly 24/7 AI sales & lead qualification assistant of {BUSINESS}.
We help businesses automate lead capture, qualification, appointment booking, and customer retention on WhatsApp and Email.

LEAD GENERATION JOURNEY ON WHATSAPP:
1. First message / greeting:
   Send a warm welcome introducing {BUSINESS} with 3 numbered options:
   1️⃣ Book a Product Demo
   2️⃣ View Pricing & Plans
   3️⃣ Speak with Sales Team
2. Collect user details step-by-step (ONE question at a time):
   - Company/Business name and what they want to automate
   - Work email address (to send the calendar invite and brochure)
   - Monthly lead volume / team size
   (IMPORTANT: The user's phone number is ALREADY auto-captured directly from WhatsApp! Never ask for their phone number).
3. Qualify & score:
   - Needs demo/automation, has team/leads: HOT (score 80-95)
   - Exploring pricing: WARM (score 50-75)
   - Spam / no budget: COLD (score < 40)
4. Confirm & schedule demo:
   - Offer slots: Thursday 3:00 PM or Friday 11:00 AM.
   - When chosen, confirm warmly: "🎉 Thank you so much for the details! Our sales team has been notified and will send your calendar invite shortly."

RULES:
- WhatsApp messages must be punchy, friendly, 2-3 sentences with emojis and numbered choices.
- Detect emotion: if the lead is frustrated or skeptical, respond with genuine empathy first.
- Reply ONLY as valid JSON:
{{"reply": str, "sentiment": "positive"|"neutral"|"frustrated"|"confused",
"company": str|null, "role": str|null, "need": str|null, "email": str|null,
"interest": "interested"|"prospect"|"not_interested"|null,
"qualified": true|false|null, "score": 0-100|null, "priority": "HOT"|"WARM"|"COLD"|null,
"booking_slot": str|null, "send_media": "brochure"|"demo_video"|"case_study"|null, "quick_replies": [str]}}
"""

def call_llm(lead, channel):
    hist = [{"role": "assistant" if m["dir"] == "out" else "user", "content": m["text"]}
            for m in lead["messages"][-14:]]
    ctx = {k: lead.get(k) for k in ("company", "role", "email", "interest", "sentiment")} | lead["facts"]
    msgs = [{"role": "system", "content": SYSTEM + f"\nLead name: {lead['name']}. Phone: {lead['phone']}. Channel: {channel}. "
             f"Entry: {lead['source']}. Known facts: {json.dumps(ctx)}"}] + hist
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                      headers={"Authorization": f"Bearer {GROQ_KEY}"},
                      json={"model": GROQ_MODEL, "messages": msgs, "temperature": 0.5,
                            "response_format": {"type": "json_object"}}, timeout=30)
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])

def fallback_ai(lead, text):
    """Scripted Yellow.ai lead gen journey used when no GROQ_API_KEY is configured."""
    t, f = text.lower().strip(), lead["facts"]
    n = f.setdefault("turn", 0); f["turn"] = n + 1
    sent = "frustrated" if re.search(r"annoy|frustrat|waste|useless|slow|angry", t) else "positive" if re.search(r"great|love|awesome|excited", t) else "neutral"
    base = {"sentiment": sent}

    # Frustration handling
    if sent == "frustrated":
        return {**base, "reply": "I truly apologize for any friction, I understand your time is valuable! Let me simplify this immediately. How can I best assist you right now?",
                "quick_replies": ["1. Book Demo", "2. View Pricing", "3. Talk to human"]}

    # 1. First Touch / Greeting
    if n <= 1 or re.search(r"^(hi|hello|hey|start|menu|hola)", t):
        fname = lead['name'].split()[0] if lead['name'] else "there"
        return {
            **base,
            "reply": f"👋 Hello {fname}! Welcome to *{BUSINESS}*.\n\nWe help businesses automate lead capture, qualification & booking on WhatsApp 24/7.\n\nHow can I help you today?\n1️⃣ Book a Product Demo\n2️⃣ View Pricing & Plans\n3️⃣ Speak with Sales Team",
            "quick_replies": ["1. Book Demo", "2. View Pricing", "3. Talk to Sales"]
        }

    # 2. Pricing query
    if "2" in t or re.search(r"price|pricing|plan|cost|brochure", t):
        return {
            **base,
            "reply": f"Here is our pricing overview 📊\n• *Starter*: $99/mo (up to 500 leads/mo)\n• *Growth*: $299/mo (up to 2,500 leads + CRM sync)\n• *Scale*: Custom\n\nWould you like me to book a quick 15-min demo walkthrough?",
            "send_media": "brochure",
            "quick_replies": ["1. Book Demo", "Send Video Demo", "Talk to Sales"]
        }

    # 3. Capture email if present
    if "@" in text:
        m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        if m:
            em = m.group(0)
            lead["email"] = em
            return {
                **base,
                "reply": f"Got it, saved work email as *{em}*! 📧\n\nWhat is your estimated monthly lead volume?\n1️⃣ Under 100 leads / month\n2️⃣ 100 - 1,000 leads / month\n3️⃣ 1,000+ leads / month",
                "email": em,
                "quick_replies": ["Under 100", "100 - 1,000", "1,000+"]
            }

    # 4. Slot booking confirmation
    if re.search(r"thu|fri|3 ?pm|11|tomorrow|yes|ok|book", t) and lead.get("qualified"):
        slot = "Friday 11:00 AM" if ("fri" in t or "11" in t) else "Thursday 3:00 PM"
        return {
            **base,
            "reply": f"🎉 Fantastic! Your demo is confirmed for *{slot}*.\n\nOur team has received your details and will send the calendar invite to {lead.get('email') or 'your email'}. Looking forward to connecting!",
            "booking_slot": slot,
            "qualified": True,
            "score": 92,
            "priority": "HOT",
            "interest": "interested"
        }

    # 5. Detail collection
    if not lead.get("company"):
        lead["company"] = text.title()
        return {
            **base,
            "reply": f"Thanks for sharing! What is the best work email address to send your demo invite and brochure?",
            "company": lead["company"],
            "need": text
        }

    if not lead.get("email"):
        return {
            **base,
            "reply": "Please share your work email address so we can send the meeting link 📩",
        }

    return {
        **base,
        "reply": f"Perfect! I have open demo slots this week:\n📅 Thursday at 3:00 PM\n📅 Friday at 11:00 AM\n\nWhich slot works best for you?",
        "quick_replies": ["Thursday 3 PM", "Friday 11 AM"],
        "qualified": True,
        "score": 90,
        "priority": "HOT",
        "interest": "interested"
    }

def apply_ai(lead, out):
    f = lead["facts"]
    if out.get("need"): f["need"] = out["need"]
    for k in ("company", "role", "email"):
        if out.get(k) and not lead.get(k):
            lead[k] = out[k]
            if k == "email": log(lead, f"📧 Captured email: {lead['email']}")
            elif k == "company": log(lead, f"🏢 Captured company: {lead['company']}")
    if out.get("interest") in ("interested", "prospect", "not_interested") and out["interest"] != lead["interest"]:
        lead["interest"] = out["interest"]
        log(lead, {"interested": "🟢 Tagged: interested", "prospect": "🟡 Tagged: prospect", "not_interested": "⚪ Tagged: not interested"}[out["interest"]])
    s = out.get("sentiment")
    if s in ("positive", "neutral", "frustrated", "confused"):
        if s != lead["sentiment"] and s in ("frustrated", "confused"):
            log(lead, f"🫶 Emotion detected: {s} → empathetic response")
        lead["sentiment"] = s
    set_stage(lead, "engaged")
    if out.get("qualified") is True and lead["qualified"] is None:
        lead["qualified"] = True; set_stage(lead, "qualified"); log(lead, "✅ Lead qualified (company, need, volume, timeline)")
    elif out.get("qualified") is False and lead["qualified"] is None:
        lead["qualified"] = False; lead["flag"] = "unqualified"; log(lead, "🚫 Lead marked unqualified")
    if out.get("score") is not None and lead["score"] is None:
        lead["score"] = int(out["score"]); lead["priority"] = (out.get("priority") or
            ("HOT" if lead["score"] >= 75 else "WARM" if lead["score"] >= 40 else "COLD")).upper()
        set_stage(lead, "scored"); log(lead, f"🎯 Lead scored {lead['score']}/100 → {lead['priority']}")
        route(lead)
    if out.get("booking_slot") and not lead["slot"]:
        lead["slot"] = out["booking_slot"]; set_stage(lead, "booked"); lead["flag"] = None
        log(lead, f"📅 Demo booked: {lead['slot']} – confirmation sent")
    sync_to_sqlite(lead)

def sync_to_sqlite(lead):
    try:
        from database.database import SessionLocal
        from database.models import Lead as DBLead
        db = SessionLocal()
        try:
            existing = None
            if lead.get("phone"):
                existing = db.query(DBLead).filter(DBLead.phone == lead["phone"]).first()
            if not existing and lead.get("email"):
                existing = db.query(DBLead).filter(DBLead.email == lead["email"]).first()

            score_val = float(lead.get("score") or 0)
            score_tier = "HIGH" if lead.get("priority") == "HOT" else ("MEDIUM" if lead.get("priority") == "WARM" else "LOW")
            status_val = "QUALIFIED" if lead.get("stage") in ("booked", "won", "proposal") else "IN_PROGRESS"
            notes_text = f"WhatsApp Lead. Slot: {lead.get('slot')}. Sentiment: {lead.get('sentiment')}. Needs: {lead.get('facts', {}).get('need')}"

            if existing:
                if lead.get("name") and existing.full_name in ("WhatsApp Lead", "Unknown", None):
                    existing.full_name = lead["name"]
                if lead.get("company"): existing.company = lead["company"]
                if lead.get("email"): existing.email = lead["email"]
                if lead.get("score"): existing.fit_score = score_val
                if lead.get("priority"): existing.score_level = score_tier
                existing.lead_status = status_val
                existing.notes = notes_text
            else:
                new_l = DBLead(
                    full_name=lead.get("name") or "WhatsApp Lead",
                    phone=lead.get("phone"),
                    email=lead.get("email"),
                    company=lead.get("company"),
                    source="WhatsApp Inbound AI",
                    fit_score=score_val or 85.0,
                    score_level=score_tier,
                    lead_status=status_val,
                    whatsapp_status="ENGAGED",
                    notes=notes_text
                )
                db.add(new_l)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"SQLite sync error: {e}")

def route(lead):
    p = lead["priority"]
    set_stage(lead, "routed")
    if p == "HOT":
        log(lead, "🔔 HOT lead → instant sales team notification + human handoff")
        if SALES_EMAIL and STATE["mode"] == "live" and email_ready():
            tmp = {**lead, "email": SALES_EMAIL, "log": []}
            send_email(tmp, f"🔥 HOT lead: {lead['name']}", f"{lead['name']} ({lead.get('company') or 'n/a'}) {lead['phone'] or lead['email']} scored {lead['score']}.")
    elif p == "WARM":
        log(lead, "🌤 WARM lead → continue nurture + follow-up")
    else:
        log(lead, "❄️ COLD lead → long-term nurture, periodic re-engagement")

def process_inbound(lead, channel, text):
    with LOCK:
        t0 = time.time()
        lead["messages"].append({"id": uuid.uuid4().hex[:8], "ts": now(), "channel": channel,
                                 "dir": "in", "text": text, "subject": None, "buttons": [], "media": None})
        lead["awaiting"], lead["followups"] = False, 0
        if lead["flag"] == "unresponsive":
            lead["flag"] = None; log(lead, "↩️ Lead responded after nurture – re-engaged")
        log(lead, f"💬 Lead replied on {channel}")
        t_clean = text.lower().strip()
        is_greeting = bool(re.search(r"^(hi|hello|hey|start|menu|hola|namaste)[\s!.]*$", t_clean))
        if is_greeting and len(lead["messages"]) <= 1:
            out = fallback_ai(lead, text)
        else:
            try:
                out = call_llm(lead, channel) if GROQ_KEY else fallback_ai(lead, text)
            except Exception as e:  # noqa
                log(lead, f"⚠️ LLM fallback ({e})")
                out = fallback_ai(lead, text)
        apply_ai(lead, out)
        media = MEDIA.get(out.get("send_media") or "")
        if media: log(lead, f"📎 Sent {media['kind']}: {media['title']}")
        qr = [str(q)[:24] for q in (out.get("quick_replies") or [])][:3]
        outbound(lead, channel, out.get("reply", "Thanks! Could you tell me a bit more?"), buttons=qr, media=media)
        lead["resp_times"].append(round(time.time() - t0, 1))


# ───────────────────────── lead creation ─────────────────────────
ENTRY = {  # entry point → (source label, prefilled first message)
    "ad": ("Click-to-WhatsApp Ad", "Hi! I saw your ad and I'd like to know more."),
    "qr": ("QR Code", "Hi, I just scanned your QR code 👋"),
    "widget": ("Website Chat Widget", "Hello, I have a question about your service."),
}

class NewLead(BaseModel):
    name: str = "Sarah Johnson"
    phone: str = ""
    email: str = ""
    company: str = ""
    source: str = "Website Form"
    entry: str = "form"
    channels: list[str] = ["whatsapp"]
    message: str = ""

def new_lead(d: NewLead):
    lid = uuid.uuid4().hex[:6]
    if d.entry in ENTRY:
        d.source = ENTRY[d.entry][0]
    lead = {"id": lid, "name": d.name, "phone": norm_phone(d.phone), "email": d.email, "source": d.source,
            "company": d.company or None, "role": None, "interest": None, "sentiment": None,
            "channels": d.channels or ["whatsapp"], "stage": "captured", "flag": None, "qualified": None,
            "score": None, "priority": None, "slot": None, "value": None, "facts": {}, "messages": [],
            "log": [], "awaiting": False, "followups": 0, "last_out": 0, "resp_times": [], "created": time.time()}
    LEADS[lid] = lead
    log(lead, f"📥 Lead captured from {d.source}")
    log(lead, "🗂 Lead created in CRM")
    text = d.message or (ENTRY[d.entry][1] if d.entry in ENTRY else "")
    if text:   # conversational entry (ad / QR / widget / real inbound): lead speaks first
        lead["channels"] = lead["channels"] if "whatsapp" in lead["channels"] else ["whatsapp"] + lead["channels"]
        process_inbound(lead, "whatsapp", text)
        log(lead, f"⚡ Instant AI response in {lead['resp_times'][-1]}s")
    else:
        first = f"Hi {d.name.split()[0]}! Thanks for reaching out to {BUSINESS} 👋 I'm {AGENT}, what are you looking to achieve?"
        broadcast(lead, first, f"Thanks for contacting {BUSINESS}!",
                  buttons=["I want a demo", "Pricing", "Just browsing"])
        lead["resp_times"].append(0.8)
        log(lead, "⚡ Instant response sent")
    sync_to_sqlite(lead)
    return lead


# ───────────────────────── API ─────────────────────────
@app.get("/api/config")
def get_config():
    wa_num = re.sub(r"\D", "", TW_FROM)
    return {**STATE, "whatsapp_ready": whatsapp_ready(), "email_ready": email_ready(),
            "llm": "groq" if GROQ_KEY else "scripted", "business": BUSINESS, "agent": AGENT,
            "wa_from": TW_FROM, "smtp_user": SMTP_USER,
            "wa_link": f"https://wa.me/{wa_num}?text=Hi%20I%20saw%20your%20ad"}

@app.get("/api/stats")
def stats():
    ls = list(LEADS.values())
    times = [t for l in ls for t in l["resp_times"]]
    by_src: dict[str, int] = {}
    for l in ls: by_src[l["source"]] = by_src.get(l["source"], 0) + 1
    booked = sum(1 for l in ls if STAGES.index(l["stage"]) >= STAGES.index("booked"))
    return {"leads": len(ls), "avg_response_s": round(sum(times) / len(times), 1) if times else None,
            "hot": sum(1 for l in ls if l["priority"] == "HOT"),
            "interested": sum(1 for l in ls if l["interest"] == "interested"),
            "booked": booked, "won": sum(1 for l in ls if l["stage"] in ("won", "onboarded", "review", "retained")),
            "conversion_pct": round(100 * booked / len(ls)) if ls else 0, "by_source": by_src}

class Cfg(BaseModel):
    mode: str | None = None
    auto_followup: bool | None = None

@app.post("/api/config")
def set_config(c: Cfg):
    if c.mode in ("mock", "live"): STATE["mode"] = c.mode
    if c.auto_followup is not None: STATE["auto_followup"] = c.auto_followup
    return get_config()

@app.post("/api/leads")
def create_lead(d: NewLead):
    with LOCK:
        return new_lead(d)

@app.get("/api/leads")
def list_leads():
    return list(LEADS.values())

@app.get("/api/leads/{lid}")
def get_lead(lid: str):
    if lid not in LEADS: raise HTTPException(404)
    return LEADS[lid]

class Msg(BaseModel):
    channel: str = "whatsapp"
    text: str

@app.post("/api/leads/{lid}/message")
def lead_message(lid: str, m: Msg):
    if lid not in LEADS: raise HTTPException(404)
    process_inbound(LEADS[lid], m.channel, m.text)
    return LEADS[lid]

class Act(BaseModel):
    action: str

ACTIONS = {
    "followup": ("engaged", "Hi {n}, just checking in – are you still interested? 😊"),
    "reminder": ("reminded", "Reminder ⏰ your {b} demo is {slot}. Reply here if you need to reschedule."),
    "attended": ("attended", None),
    "noshow": (None, "Hi {n}, we missed you at the demo today! Want to reschedule? Reply with a day that suits you 🗓️"),
    "proposal": ("proposal", "Hi {n}, here's your tailored proposal: Growth plan – $299/mo + onboarding. Happy to answer any questions!"),
    "won": ("won", "Wonderful, {n}! 🎉 Welcome to {b} – let's get your account set up."),
    "lost": (None, "Hi {n}, no pressure at all – we'll keep your quote open. Anything we can adjust?"),
    "onboard": ("onboarded", "Hi {n}, your account is live! Thank you for choosing {b} 💙"),
    "review": ("review", "Loved working with you, {n}! Would you leave us a quick review? ⭐ g2.com/products/nexomate"),
    "referral": ("review", "Know another team that would benefit? Refer them and you both get a month free 🎁"),
    "upsell": ("retained", "Hi {n}, the Scale plan adds multi-team routing and analytics – want a walkthrough?"),
    "reactivate": ("retained", "Hi {n}, it's been a while! We've shipped new features – want a quick look? 😊"),
}

@app.post("/api/leads/{lid}/action")
def action(lid: str, a: Act):
    lead = LEADS.get(lid)
    if not lead or a.action not in ACTIONS: raise HTTPException(404)
    stage, tpl = ACTIONS[a.action]
    with LOCK:
        if a.action == "attended":
            set_stage(lead, "attended"); log(lead, "🙋 Lead attended – sales conversation held"); return lead
        if a.action == "noshow":
            lead["flag"] = "noshow"; log(lead, "😕 No-show → recovery message sent")
        if a.action == "lost":
            lead["flag"] = "lost"; log(lead, "📉 Deal lost → quote follow-up, moved to nurture")
        if a.action == "proposal": lead["value"] = "$1,450"; log(lead, "💼 Proposal / quote sent")
        if a.action == "won": log(lead, "🏆 Deal won!")
        if a.action == "reminder": log(lead, "⏰ Appointment reminder sent")
        if a.action == "followup": log(lead, "🔁 Automated follow-up sent")
        if a.action in ("review", "referral", "upsell", "reactivate", "onboard"):
            log(lead, {"review": "⭐ Review request sent", "referral": "🎁 Referral request sent",
                       "upsell": "➕ Upsell offer sent", "reactivate": "📣 Reactivation campaign sent",
                       "onboard": "🚀 Onboarding / service delivered"}[a.action])
        if stage: set_stage(lead, stage)
        if tpl:
            broadcast(lead, tpl.format(n=lead["name"].split()[0], b=BUSINESS, slot=lead["slot"] or "soon"))
    return lead

@app.get("/api/whatsapp/webhook")
def wa_webhook_check():
    return {
        "status": "online",
        "service": "Nexomate WhatsApp Inbound Webhook",
        "mode": STATE["mode"],
        "whatsapp_ready": whatsapp_ready(),
        "from_number": TW_FROM,
        "active_leads": len(LEADS),
        "message": "Webhook is live! Configure this URL in Twilio Console -> Messaging -> Sandbox settings (HTTP POST)."
    }

@app.post("/api/whatsapp/webhook")
async def wa_webhook(request: Request):
    raw_body = await request.body()
    form = {k: v[0] for k, v in parse_qs(raw_body.decode(errors="ignore")).items()}
    sender = form.get("From", "").replace("whatsapp:", "").strip()
    profile_name = form.get("ProfileName", "").strip() or "WhatsApp Lead"
    body = form.get("Body", "").strip()

    if not sender:
        return Response("<Response/>", media_type="application/xml")

    with LOCK:
        lead = next((l for l in LEADS.values() if l["phone"] == sender), None)
        if not lead:
            # AUTO-CAPTURE PHONE & NAME DIRECTLY WITHOUT ASKING USER!
            lead = new_lead(NewLead(
                name=profile_name,
                phone=sender,
                source="WhatsApp Inbound",
                entry="qr",
                channels=["whatsapp"],
                message=""
            ))
            lead["is_live"] = True

        lead["is_live"] = True
        process_inbound(lead, "whatsapp", body)

        # Get latest outbound message text to return directly in TwiML
        last_out = next((m["text"] for m in reversed(lead["messages"]) if m["dir"] == "out"), None)
        if last_out:
            escaped = last_out.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            twiml = f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n    <Message>{escaped}</Message>\n</Response>'
            return Response(content=twiml, media_type="application/xml")

    return Response("<Response/>", media_type="application/xml")


class WaInboundJson(BaseModel):
    phone: str
    name: str = "WhatsApp Prospect"
    text: str

@app.post("/api/whatsapp/inbound_json")
def wa_inbound_json(data: WaInboundJson):
    sender = norm_phone(data.phone)
    if not sender:
        raise HTTPException(400, "Phone number is required")
    with LOCK:
        lead = next((l for l in LEADS.values() if l["phone"] == sender), None)
        if not lead:
            lead = new_lead(NewLead(
                name=data.name,
                phone=sender,
                source="WhatsApp (Direct Number)",
                entry="qr",
                channels=["whatsapp"],
                message=""
            ))
            lead["is_live"] = True
        lead["is_live"] = True
        process_inbound(lead, "whatsapp", data.text)
        last_out = next((m["text"] for m in reversed(lead["messages"]) if m["dir"] == "out"), None)
        return {"reply": last_out or f"Hi! Thanks for contacting {BUSINESS}. How can I assist you?", "lead_id": lead["id"]}


class MissedCallReq(BaseModel):
    phone: str
    name: str = "Missed Caller"
    source: str = "Missed Call Recovery"

@app.post("/api/whatsapp/missed_call")
def wa_missed_call(data: MissedCallReq):
    sender = norm_phone(data.phone)
    if not sender:
        raise HTTPException(400, "Phone number required")

    with LOCK:
        lead = next((l for l in LEADS.values() if l["phone"] == sender), None)
        if not lead:
            lead = new_lead(NewLead(
                name=data.name if data.name not in ("Caller", "Missed Caller") else "Inbound Caller",
                phone=sender,
                source="Missed Call Recovery",
                entry="qr",
                channels=["whatsapp"],
                message=""
            ))
        lead["source"] = "Missed Call Recovery"
        lead["is_live"] = True
        log(lead, "📞 Inbound missed call intercepted → Auto-recovery triggered")

        first_name = lead["name"].split()[0] if lead["name"] and lead["name"] not in ("Caller", "Inbound Caller", "Missed Caller") else "there"
        recovery_text = (
            f"Hey {first_name}! 👋 Sorry I missed your call just now.\n\n"
            f"I was in a quick meeting, but I'm here right now on WhatsApp! How can I help you today?\n\n"
            f"1️⃣ Book a Quick Demo / Call\n"
            f"2️⃣ View Pricing & Plans\n"
            f"3️⃣ Leave a Quick Message"
        )

        outbound(lead, "whatsapp", recovery_text, buttons=["Book Demo", "Pricing", "Leave Message"])
        sync_to_sqlite(lead)

        # Proactively send via local WhatsApp Bridge if available
        bridge_sent = False
        try:
            r = requests.post("http://localhost:8001/send", json={"to": sender, "text": recovery_text}, timeout=3)
            if r.status_code == 200:
                bridge_sent = True
                log(lead, "🚀 Recovery message delivered via Linked WhatsApp SIM")
        except Exception:
            pass

        return {
            "success": True,
            "message": recovery_text,
            "bridge_sent": bridge_sent,
            "lead": lead
        }


# ───────────────────────── background workers ─────────────────────────
def followup_worker():
    while True:
        time.sleep(3)
        if not STATE["auto_followup"]:
            continue
        with LOCK:
            for lead in LEADS.values():
                if (lead["awaiting"] and lead["stage"] in ("captured", "engaged") and not lead["flag"]
                        and time.time() - lead["last_out"] > FOLLOWUP_SECONDS):
                    if lead["followups"] >= 2:
                        lead["flag"] = "unresponsive"; lead["awaiting"] = False
                        log(lead, "🔕 No reply after sequence → marked unresponsive / nurture")
                        continue
                    lead["followups"] += 1
                    log(lead, f"🔁 Automated follow-up #{lead['followups']} sent")
                    broadcast(lead, f"Hi {lead['name'].split()[0]}, just checking in – still interested? 😊")

def imap_worker():
    if not (IMAP_HOST and IMAP_USER and IMAP_PASS):
        return
    while True:
        time.sleep(10)
        if STATE["mode"] != "live":
            continue
        try:
            box = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            box.login(IMAP_USER, IMAP_PASS); box.select("INBOX")
            _, ids = box.search(None, "UNSEEN")
            for i in ids[0].split():
                _, data = box.fetch(i, "(RFC822)")
                msg = emaillib.message_from_bytes(data[0][1])
                addr = parseaddr(msg["From"])[1].lower()
                lead = next((l for l in LEADS.values() if l["email"].lower() == addr), None)
                if not lead:
                    continue
                body = ""
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore"); break
                body = re.split(r"\n>|\nOn .* wrote:", body)[0].strip()
                if body:
                    process_inbound(lead, "email", body)
            box.logout()
        except Exception as e:  # noqa
            print("IMAP error:", e)

@app.on_event("startup")
def start_workers():
    threading.Thread(target=followup_worker, daemon=True).start()
    threading.Thread(target=imap_worker, daemon=True).start()


@app.get("/")
def root():
    return FileResponse(HERE / "live.html")

app.mount("/", StaticFiles(directory=HERE), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(env("PORT", "8000")))
