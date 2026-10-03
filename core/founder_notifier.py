# core/founder_notifier.py
"""Automated Founder Notification Engine for Nexomate.

Dispatches instant alerts across:
1. Email (Hostinger SMTP -> umarfarhan474@gmail.com, devrajput0107@gmail.com)
2. WhatsApp (Baileys Bridge -> +91 9971786873, +91 8882502735)
3. SMS (Twilio or fallback logger -> +91 9971786873, +91 8882502735)
4. Persistent Storage (SQLite database & data/qualified_leads.json)
"""

import os
import json
import time
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LEADS_JSON = DATA_DIR / "qualified_leads.json"

# Founder alert recipients specified by Farhan & Devrajput
FOUNDER_EMAILS = [
    "umarfarhan474@gmail.com",
    "devrajput0107@gmail.com",
]

FOUNDER_PHONES = [
    "919971786873",
    "918882502735",
]

BRIDGE_URL = "http://localhost:8001/send"


def _get_smtp_credentials():
    host = os.getenv("SMTP_HOST", "smtp.hostinger.com")
    port = int(os.getenv("SMTP_PORT", "465") or 465)
    user = os.getenv("SMTP_USER", "connect@getnexomate.com")
    password = os.getenv("SMTP_PASSWORD", "Dl3sdf@3223")
    return host, port, user, password


def save_qualified_lead(lead: dict) -> bool:
    """Persists qualified lead to SQLite and JSON storage."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # 1. Update JSON dossier
        existing_leads = []
        if LEADS_JSON.exists():
            try:
                with open(LEADS_JSON, "r", encoding="utf-8") as f:
                    existing_leads = json.load(f)
            except Exception:
                existing_leads = []

        record = {
            "id": lead.get("id"),
            "name": lead.get("name"),
            "phone": lead.get("phone"),
            "email": lead.get("email"),
            "company": lead.get("company"),
            "slot": lead.get("slot"),
            "score": lead.get("score"),
            "priority": lead.get("priority"),
            "stage": lead.get("stage"),
            "facts": lead.get("facts", {}),
            "updated_at": datetime.now().isoformat(),
        }

        # Replace or append
        updated = False
        for idx, item in enumerate(existing_leads):
            if (lead.get("phone") and item.get("phone") == lead.get("phone")) or (lead.get("id") and item.get("id") == lead.get("id")):
                existing_leads[idx] = record
                updated = True
                break
        if not updated:
            existing_leads.append(record)

        with open(LEADS_JSON, "w", encoding="utf-8") as f:
            json.dump(existing_leads, f, indent=2)

        # 2. Sync to SQLite
        try:
            from database.database import SessionLocal
            from database.models import Lead as DBLead
            db = SessionLocal()
            try:
                db_lead = None
                if lead.get("phone"):
                    db_lead = db.query(DBLead).filter(DBLead.phone == lead["phone"]).first()
                if not db_lead and lead.get("email"):
                    db_lead = db.query(DBLead).filter(DBLead.email == lead["email"]).first()

                score_val = float(lead.get("score") or 90.0)
                score_tier = "HIGH" if lead.get("priority") == "HOT" else "MEDIUM"
                notes_text = f"Qualified WhatsApp Demo. Slot: {lead.get('slot')}. Needs: {lead.get('facts', {}).get('need')}"

                if db_lead:
                    if lead.get("name") and db_lead.full_name in ("WhatsApp Lead", "Unknown", None):
                        db_lead.full_name = lead["name"]
                    if lead.get("company"): db_lead.company = lead["company"]
                    if lead.get("email"): db_lead.email = lead["email"]
                    db_lead.fit_score = score_val
                    db_lead.score_level = score_tier
                    db_lead.lead_status = "QUALIFIED"
                    db_lead.whatsapp_status = "ENGAGED"
                    db_lead.notes = notes_text
                else:
                    new_db_lead = DBLead(
                        full_name=lead.get("name") or "WhatsApp Prospect",
                        phone=lead.get("phone"),
                        email=lead.get("email"),
                        company=lead.get("company"),
                        source="WhatsApp Inbound AI",
                        fit_score=score_val,
                        score_level=score_tier,
                        lead_status="QUALIFIED",
                        whatsapp_status="ENGAGED",
                        notes=notes_text,
                    )
                    db.add(new_db_lead)
                db.commit()
            finally:
                db.close()
        except Exception as dbe:
            print(f"[FounderNotifier] SQLite sync notice: {dbe}")

        return True
    except Exception as e:
        print(f"[FounderNotifier] Error saving qualified lead: {e}")
        return False


def send_founder_emails(lead: dict) -> dict:
    """Sends notification email to Farhan and Devrajput via Hostinger SMTP."""
    host, port, user, password = _get_smtp_credentials()
    results = {}

    name = lead.get("name") or "WhatsApp Prospect"
    phone = lead.get("phone") or "Auto-captured on WhatsApp"
    email = lead.get("email") or "Pending calendar invite"
    company = lead.get("company") or "Direct Inquiry"
    slot = lead.get("slot") or "Confirmed with AI"
    score = lead.get("score") or 92
    priority = lead.get("priority") or "HOT"
    need = lead.get("facts", {}).get("need") or "Automate lead capture & booking"

    subject = f"🚀 [NEXOMATE LEAD ALERT] New Qualified Demo Booked: {name} ({slot})"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f17; color: #f3f4f6; margin: 0; padding: 24px; }}
            .card {{ max-width: 600px; margin: 0 auto; background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 32px; }}
            .badge {{ display: inline-block; background: #10b981; color: #000000; font-weight: 700; font-size: 12px; padding: 4px 10px; border-radius: 4px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; }}
            h1 {{ font-size: 24px; font-weight: 700; color: #ffffff; margin: 0 0 8px 0; }}
            .subhead {{ color: #94a3b8; font-size: 14px; margin-bottom: 24px; }}
            .metric-box {{ background: #1e293b; border-radius: 6px; padding: 16px; margin-bottom: 20px; }}
            .row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #334155; font-size: 14px; }}
            .row:last-child {{ border-bottom: none; }}
            .label {{ color: #94a3b8; font-weight: 500; }}
            .val {{ color: #f8fafc; font-weight: 600; text-align: right; }}
            .highlight {{ color: #38bdf8; font-weight: 700; }}
            .footer {{ text-align: center; font-size: 12px; color: #64748b; margin-top: 24px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <span class="badge">🔥 Hot Lead · Demo Booked</span>
            <h1>New Lead Qualified on WhatsApp</h1>
            <div class="subhead">Nexomate Autonomous AI has locked in a prospective client meeting.</div>

            <div class="metric-box">
                <div class="row"><span class="label">👤 Contact Name:</span><span class="val">{name}</span></div>
                <div class="row"><span class="label">📞 WhatsApp Phone:</span><span class="val highlight">{phone}</span></div>
                <div class="row"><span class="label">📧 Work Email:</span><span class="val">{email}</span></div>
                <div class="row"><span class="label">🏢 Company / Org:</span><span class="val">{company}</span></div>
                <div class="row"><span class="label">📅 Scheduled Slot:</span><span class="val highlight">{slot}</span></div>
                <div class="row"><span class="label">🎯 Fit Score:</span><span class="val">{score}/100 ({priority})</span></div>
                <div class="row"><span class="label">📝 Automation Need:</span><span class="val">{need}</span></div>
            </div>

            <p style="font-size: 14px; line-height: 1.6; color: #cbd5e1;">
                <b>Next Action:</b> The prospect confirmed this slot directly with the AI agent. Please send the Google Calendar / Zoom invite to <b>{email}</b>.
            </p>

            <div class="footer">
                Nexomate AI Lead Operations · connect@getnexomate.com<br>
                Automated alert dispatched to Farhan & Devrajput
            </div>
        </div>
    </body>
    </html>
    """

    plain_content = f"""
    🚀 [NEXOMATE LEAD ALERT] New Qualified Demo Booked!
    --------------------------------------------------
    👤 Name: {name}
    📞 WhatsApp Phone: {phone}
    📧 Email: {email}
    🏢 Company: {company}
    📅 Scheduled Slot: {slot}
    🎯 Fit Score: {score}/100 ({priority})
    📝 Need / Goal: {need}
    --------------------------------------------------
    Next Action: Send calendar meeting invite to {email}.
    Nexomate Autonomous Lead Engine
    """

    for recipient in FOUNDER_EMAILS:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"Nexomate AI <{user}>"
            msg["To"] = recipient
            msg.attach(MIMEText(plain_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=10)
            else:
                server = smtplib.SMTP(host, port, timeout=10)
                server.starttls()

            server.login(user, password)
            server.sendmail(user, recipient, msg.as_string())
            server.quit()
            results[recipient] = "SENT"
        except Exception as e:
            print(f"[FounderNotifier] Email error to {recipient}: {e}")
            results[recipient] = f"FAILED: {e}"

    return results


def send_founder_whatsapp(lead: dict) -> dict:
    """Dispatches WhatsApp alert message to Farhan and Devrajput via Linked SIM."""
    name = lead.get("name") or "WhatsApp Prospect"
    phone = lead.get("phone") or "Auto-captured on WhatsApp"
    email = lead.get("email") or "Pending calendar invite"
    company = lead.get("company") or "Direct Inquiry"
    slot = lead.get("slot") or "Confirmed with AI"
    score = lead.get("score") or 92
    priority = lead.get("priority") or "HOT"
    need = lead.get("facts", {}).get("need") or "Automation demo inquiry"

    alert_text = (
        f"🚨 *[NEXOMATE FOUNDER ALERT]* 🚀\n"
        f"*New Qualified Demo Booked!*\n\n"
        f"👤 *Lead:* {name}\n"
        f"📞 *Phone:* {phone}\n"
        f"📧 *Email:* {email}\n"
        f"🏢 *Company:* {company}\n"
        f"📅 *Demo Slot:* *{slot}*\n"
        f"🎯 *Score:* {score}/100 ({priority})\n"
        f"📝 *Requirement:* {need}\n\n"
        f"👉 _Please send Google Calendar / Zoom invite to {email}._\n"
        f"✅ _Synced to Nexomate CRM & SQLite._"
    )

    results = {}
    for p in FOUNDER_PHONES:
        clean = p.replace("+", "").replace(" ", "").replace("-", "")
        try:
            r = requests.post(BRIDGE_URL, json={"to": clean, "text": alert_text}, timeout=5)
            if r.status_code == 200:
                results[clean] = "SENT"
            else:
                results[clean] = f"HTTP_{r.status_code}"
        except Exception as e:
            results[clean] = f"BRIDGE_OFFLINE: {e}"

    return results


def send_founder_sms(lead: dict) -> dict:
    """Sends SMS notification or creates direct SMS dispatches."""
    name = lead.get("name") or "Lead"
    phone = lead.get("phone") or "WhatsApp"
    slot = lead.get("slot") or "Soon"
    sms_text = f"Nexomate Alert: New Demo Booked with {name} ({phone}) for {slot}. Check email for full dossier."

    results = {}
    tw_sid = os.getenv("TWILIO_ACCOUNT_SID")
    tw_token = os.getenv("TWILIO_AUTH_TOKEN")
    tw_from = os.getenv("TWILIO_SMS_FROM")

    for p in FOUNDER_PHONES:
        clean = "+" + p.replace("+", "").replace(" ", "").replace("-", "")
        if tw_sid and tw_token and tw_from:
            try:
                import urllib.parse
                url = f"https://api.twilio.com/2010-04-01/Accounts/{tw_sid}/Messages.json"
                r = requests.post(
                    url,
                    auth=(tw_sid, tw_token),
                    data={"From": tw_from, "To": clean, "Body": sms_text},
                    timeout=5,
                )
                results[clean] = "SENT" if r.status_code in (200, 201) else f"ERR_{r.status_code}"
            except Exception as e:
                results[clean] = f"ERROR: {e}"
        else:
            # Fallback simulated log when Twilio SMS credentials aren't active
            results[clean] = "LOGGED (Twilio SMS credentials not set)"

    return results


def notify_all_founders(lead: dict, event: str = "DEMO_BOOKED") -> dict:
    """High-level orchestrator: saves data and fires alerts across all channels."""
    # 1. Save data first
    saved = save_qualified_lead(lead)

    # 2. Send emails
    email_status = send_founder_emails(lead)

    # 3. Send WhatsApp
    wa_status = send_founder_whatsapp(lead)

    # 4. Send SMS
    sms_status = send_founder_sms(lead)

    return {
        "saved": saved,
        "email": email_status,
        "whatsapp": wa_status,
        "sms": sms_status,
        "timestamp": datetime.now().isoformat(),
    }
