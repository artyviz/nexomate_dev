# Live WhatsApp + Email demo setup

## Run
```
cd lead-workflow-demo
python server.py            # http://localhost:8000
```
Works immediately in **Mock** mode (WhatsApp phone mockup + email inbox mockup).
Without `GROQ_API_KEY` the AI uses a scripted brain; with it, replies are live LLM.

## Go Live (optional) – create `lead-workflow-demo/.env`
Settings in the parent `../.env` (SMTP_*, IMAP_*, GROQ_API_KEY) are reused automatically.

```
GROQ_API_KEY=...
BUSINESS_NAME=Brightside Dental
AGENT_NAME=Maya

# WhatsApp via Twilio Sandbox
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Email (Gmail: use an App Password; IMAP host imap.gmail.com)
SMTP_HOST=smtp.gmail.com
SMTP_USER=you@gmail.com
SMTP_PASSWORD=app-password
IMAP_HOST=imap.gmail.com

SALES_NOTIFY_EMAIL=sales@yourcompany.com   # HOT lead alerts
FOLLOWUP_SECONDS=45
```

### WhatsApp steps
1. Twilio Console → Messaging → Try it out → WhatsApp sandbox. From the client/founder phone send `join <your-code>` to the sandbox number.
2. Expose the server: `ngrok http 8000`.
3. Set sandbox "When a message comes in" to `https://<ngrok-id>.ngrok.app/api/whatsapp/webhook` (POST).
4. In the UI switch to **Live**, enter the phone as `+91…`, capture the lead. Replies from that phone flow into the AI automatically.

### Email
Switch to **Live**, tick Email, enter an inbox you control. Replying to the email is picked up by IMAP polling (every 10s).

## B2B chatbot features
- Entry points: web form, Click-to-WhatsApp ad, QR code, chat widget (in Live mode with Twilio, scanning the QR / messaging the number creates the lead automatically).
- B2B qualification (company, role, need, budget, timeline) and interested / prospect / not-interested tagging.
- Emotion detection with empathetic replies, quick-reply buttons, brochure / demo-video / case-study cards.
- Live analytics strip: response time, leads, HOT, demos booked, conversion.
- Set BROCHURE_URL, DEMO_VIDEO_URL, CASE_STUDY_URL, BUSINESS_NAME in .env to brand it.
