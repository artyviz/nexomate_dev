# dashboard/whatsapp_page.py
"""WhatsApp Autonomous AI Lead Generation — Noir Press Edition."""

import base64
import time
import requests
import streamlit as st
from datetime import datetime
from database.database import SessionLocal
from database.models import Lead
from config import GROQ_MODEL
from dashboard.service_manager import ensure_all_services_running
BUSINESS_NAME = "Nexomate"


# Local FastAPI demo server endpoint
API_BASE = "http://127.0.0.1:8000/api"
BRIDGE_BASE = "http://127.0.0.1:8001"


def get_live_data():
    # Automatically verify and spawn background services if offline
    ensure_all_services_running()

    cfg, stats, leads, bridge = None, None, [], None
    try:
        cfg = requests.get(f"{API_BASE}/config", timeout=4).json()
        stats = requests.get(f"{API_BASE}/stats", timeout=4).json()
        leads = requests.get(f"{API_BASE}/leads", timeout=4).json()
    except Exception:
        pass
    try:
        bridge = requests.get(f"{BRIDGE_BASE}/status", timeout=4).json()
    except Exception:
        pass
    return cfg, stats, leads, bridge


def whatsapp_page():
    # ── Masthead ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="editorial-masthead" style="margin-bottom: 1.5rem; padding: 1rem 0.5rem;">
        <div class="masthead-meta-row">
            <span>WIRE INTERCEPT: WHATSAPP CLOUD</span>
            <span>24/7 AUTONOMOUS RECEPTOR</span>
            <span>NOIR PRESS TERMINAL</span>
        </div>
        <h1 class="masthead-main-title" style="font-size: 2.2rem;">WHATSAPP LEAD INTELLIGENCE</h1>
        <div class="masthead-sub-rule">Automated B2B lead capture · Phone auto-extraction · Groq LLM qualification · Instant CRM sync</div>
    </div>
    """, unsafe_allow_html=True)

    cfg, stats, leads, bridge = get_live_data()
    bridge_connected = bridge.get("connected", False) if bridge else False
    bridge_phone = bridge.get("phone", "") if bridge else ""

    # ── Live Telemetry Bar ───────────────────────────────────────────────────
    st.markdown("""
    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1.5px; color: #888888; margin-bottom: 0.5rem;">
        SYSTEM TELEMETRY & HARDWARE LINKS
    </div>
    """, unsafe_allow_html=True)

    tcol1, tcol2, tcol3, tcol4 = st.columns(4)

    is_online = bool(cfg)
    wa_active = bridge_connected or (cfg.get("whatsapp_ready", False) if cfg else False)
    mode = "DIRECT SIM" if bridge_connected else (cfg.get("mode", "OFFLINE").upper() if cfg else "OFFLINE")
    total_leads = stats.get("leads", 0) if stats else 0
    hot_leads = stats.get("hot", 0) if stats else 0
    booked_leads = stats.get("booked", 0) if stats else 0
    avg_latency = stats.get("avg_response_s", "—") if stats else "—"

    with tcol1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">ENGINE STATUS</div>
            <div class="metric-value font-mono" style="color: {'#34D399' if is_online else '#FF3333'}; font-size: 1.4rem;">
                {'LIVE WIRE' if is_online else 'DISCONNECTED'}
            </div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #888888; margin-top: 4px;">
                {'WHATSAPP: ' + bridge_phone if bridge_connected else 'MODE: ' + mode}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tcol2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">CAPTURED PROSPECTS</div>
            <div class="metric-value font-mono" style="font-size: 1.4rem;">{total_leads}</div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #888888; margin-top: 4px;">
                AUTO PHONE EXTRACTED
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tcol3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">HOT QUALIFIED</div>
            <div class="metric-value font-mono" style="color: #FF3333; font-size: 1.4rem;">{hot_leads}</div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #888888; margin-top: 4px;">
                HIGH-INTENT PIPELINE
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tcol4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">DEMOS BOOKED</div>
            <div class="metric-value font-mono" style="color: #22D3EE; font-size: 1.4rem;">{booked_leads}</div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #888888; margin-top: 4px;">
                AVG LATENCY: {avg_latency}s
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)

    # ── Direct WhatsApp Number Linking (Linked Device QR Code) ───────────────
    if bridge_connected:
        st.markdown(f"""
        <div style="border: 2px solid #34D399; background: rgba(52, 211, 153, 0.08); padding: 1rem 1.4rem; margin-bottom: 1.2rem; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; font-weight: 700; color: #34D399; letter-spacing: 1px;">
                    ● ACTIVE BUSINESS ACCOUNT: {bridge_phone}
                </span>
                <div style="font-family: 'Playfair Display', serif; font-size: 1.2rem; margin-top: 3px; color: #F3F3EF;">
                    Direct Autonomous Bot Is Answering Inbound Messages
                </div>
                <div style="font-family: 'Lora', serif; font-size: 0.85rem; color: #888888; margin-top: 2px;">
                    Anyone texting {bridge_phone} directly will be instantly qualified by Groq LLM and logged in CRM.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Unlink This WhatsApp Number / Logout", key="btn_unlink_wa"):
            try:
                requests.post(f"{BRIDGE_BASE}/logout", timeout=3)
                st.success("Unlinked WhatsApp device. Scan new QR code to reconnect.")
                st.rerun()
            except Exception as e:
                st.error(f"Error logging out: {e}")
    else:
        with st.expander("📲 LINK YOUR BUSINESS PHONE NUMBER (SCAN QR CODE)", expanded=True):
            qcol1, qcol2 = st.columns([1, 2])
            with qcol1:
                qr_data = bridge.get("qr") if bridge else None
                if qr_data and "," in qr_data:
                    st.session_state["qr_refresh_count"] = 0
                    try:
                        qr_bytes = base64.b64decode(qr_data.split(",")[1])
                        st.image(qr_bytes, caption="Scan in WhatsApp: Linked Devices", width=220)
                    except Exception:
                        st.image(qr_data, caption="Scan in WhatsApp: Linked Devices", width=220)

                    st.markdown("""
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #34D399; font-weight: 700; margin-top: 4px; letter-spacing: 0.5px;">
                        ● LIVE QR STREAM ACTIVE
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    refresh_count = st.session_state.get("qr_refresh_count", 0)
                    if refresh_count < 6:
                        st.session_state["qr_refresh_count"] = refresh_count + 1
                        st.info(f"⚡ Establishing WhatsApp Web socket... Polling for live QR ({refresh_count + 1}/6)...")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.warning("WhatsApp bridge is standing by. Click 'Refresh QR' below to stream the code.")

                qbtn_col1, qbtn_col2 = st.columns(2)
                with qbtn_col1:
                    if st.button("🔄 Refresh QR", key="btn_check_qr", use_container_width=True):
                        st.session_state["qr_refresh_count"] = 0
                        st.rerun()
                with qbtn_col2:
                    if st.button("⚡ New Code", key="btn_new_qr", use_container_width=True):
                        try:
                            requests.post(f"{BRIDGE_BASE}/logout", timeout=3)
                        except Exception:
                            pass
                        st.session_state["qr_refresh_count"] = 0
                        st.rerun()

            with qcol2:
                st.markdown(f"""
                <div style="font-family: 'Playfair Display', serif; font-size: 1.2rem; font-weight: 700; margin-bottom: 0.5rem; color: #F3F3EF;">
                    How to Link Any Business WhatsApp Account:
                </div>
                <ol style="font-family: 'Lora', serif; font-size: 0.9rem; line-height: 1.8; color: #CCCCCC; margin-left: 1.2rem;">
                    <li>Open <b>WhatsApp</b> on the target business smartphone or WhatsApp Business app.</li>
                    <li>Tap <b>Settings</b> (on iOS) or <b>⋮ Menu</b> (on Android) → <b>Linked Devices</b>.</li>
                    <li>Tap <b>Link a Device</b> and point the camera at the live QR code on the left.</li>
                </ol>
                <div style="background: #111111; border-left: 3px solid #22D3EE; padding: 0.6rem 0.8rem; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #888888; margin-top: 0.8rem;">
                    ⚡ <b>WORKS WITH ANY PHONE NUMBER:</b> The bot dynamically adopts whatever phone number scans the QR code. Zero Twilio fees, zero approval wait times.
                </div>
                """, unsafe_allow_html=True)

    # ── Webhook Connection Drawer (Twilio Alternative) ─────────────────────────
    with st.expander("▾ ADVANCED: TWILIO CLOUD WEBHOOK (OPTIONAL SANDBOX)", expanded=False):
        wcol1, wcol2 = st.columns([2, 1])
        with wcol1:
            st.markdown(f"""
            **Twilio WhatsApp Sandbox Setup:**
            1. Set Twilio Sandbox Webhook (HTTP POST):
               `https://curly-symbols-refuse.loca.lt/api/whatsapp/webhook`
            2. Join Sandbox from any phone:
               Send your Twilio join code (e.g. `join <code-word>`) to `+1 415 523 8886`
            3. Start chatting: send `Hi` to test autonomous qualification!
            """)
        with wcol2:
            st.markdown(f"""
            **Live Channel Telemetry:**
            - **Sender Account:** `{cfg.get('wa_from', 'whatsapp:+14155238886') if cfg else 'N/A'}`
            - **Twilio Ready:** `{'YES (Twilio Connected)' if wa_active else 'MOCK ONLY'}`
            - **LLM Engine:** `{cfg.get('llm', 'Groq') if cfg else 'Groq'}`
            """)

    # ── Autonomous Missed Call Recovery Drawer ────────────────────────────────
    with st.expander("📞 AUTONOMOUS MISSED CALL RECOVERY SUITE (ACTIVE)", expanded=False):
        mcol1, mcol2 = st.columns([3, 2])
        with mcol1:
            st.markdown("""
            <div style="font-family: 'Playfair Display', serif; font-size: 1.1rem; font-weight: 700; color: #F3F3EF; margin-bottom: 0.4rem;">
                Zero-Lead-Leakage: Instant Missed Call Intercept
            </div>
            <div style="font-family: 'Lora', serif; font-size: 0.85rem; color: #CCCCCC; line-height: 1.6;">
                Whenever a client or prospect calls your business line and the call is unanswered, busy, or declined:
                <br>• <b>WhatsApp In-App Missed Calls:</b> Intercepted automatically on your linked WhatsApp SIM in real-time.
                <br>• <b>Instant WhatsApp Recovery:</b> Dispatches an instant text within seconds offering instant booking & answers.
                <br>• <b>Live CRM Ingestion:</b> Automatically logged in your dossier with fit score and hot-intent tags.
            </div>
            """, unsafe_allow_html=True)

            st.code("""Hey there! 👋 Sorry I missed your call just now.
I was in a quick meeting, but I'm here right now on WhatsApp! How can I help you today?

1️⃣ Book a Quick Demo / Call
2️⃣ View Pricing & Plans
3️⃣ Leave a Quick Message""", language="text")

        with mcol2:
            st.markdown("""
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; font-weight: 700; color: #34D399; margin-bottom: 0.5rem;">
                ⚡ TEST MISSED CALL RECOVERY NOW
            </div>
            """, unsafe_allow_html=True)
            test_phone = st.text_input("Caller Phone Number:", value=bridge_phone or "+919876543210", key="sim_call_phone")
            test_caller = st.text_input("Caller Name (optional):", value="Prospective Client", key="sim_call_name")
            if st.button("🚨 TRIGGER MISSED CALL INTERCEPT", key="btn_trigger_missed_call"):
                try:
                    res = requests.post(f"{API_BASE}/whatsapp/missed_call", json={
                        "phone": test_phone,
                        "name": test_caller,
                        "source": "Missed Call Recovery"
                    }, timeout=5).json()
                    st.success(f"Delivered WhatsApp Missed Call Recovery to {test_phone}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error triggering missed call recovery: {e}")

    # ── Main Two-Column Terminal Interface ───────────────────────────────────
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #333333; padding-bottom: 0.4rem; margin-bottom: 1rem;">
        <span style="font-family: 'Playfair Display', serif; font-size: 1.3rem; font-weight: 700;">CONVERSATIONAL INTERCEPT TERMINAL</span>
        <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #888888;">PRESS REFRESH TO SYNC WIRE</span>
    </div>
    """, unsafe_allow_html=True)

    col_chat, col_crm = st.columns([3, 2])

    # ── Left Column: Live WhatsApp Chat Feed ──────────────────────────────────
    with col_chat:
        st.markdown("""
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; font-weight: 700; color: #F3F3EF; margin-bottom: 0.6rem;">
            ◈ LIVE INBOUND/OUTBOUND WIRE TRANSCRIPT
        </div>
        """, unsafe_allow_html=True)

        if not leads:
            st.markdown("""
            <div class="noir-card" style="padding: 2rem; text-align: center; color: #888888; font-family: 'Lora', serif; font-style: italic;">
                No dispatches detected on the wire yet.<br>
                Send a WhatsApp message from your phone or use the simulation console below.
            </div>
            """, unsafe_allow_html=True)
            selected_lead = None
        else:
            lead_options = {f"{l.get('name', 'Prospect')} ({l.get('phone', 'N/A')}) — {l.get('stage', 'captured').upper()}": l for l in leads}
            chosen_key = st.selectbox("Select Intercepted Transmission", list(lead_options.keys()), label_visibility="collapsed")
            selected_lead = lead_options[chosen_key]

            # Render Conversation Wire in Noir Press Editorial Format
            chat_container = st.container()
            with chat_container:
                st.markdown(f"""
                <div style="background: #080808; border: 1px solid #262626; padding: 1rem; margin-bottom: 1rem; max-height: 480px; overflow-y: auto;">
                """, unsafe_allow_html=True)

                msgs = selected_lead.get("messages", [])
                if not msgs:
                    st.markdown("<p style='color:#666; font-family:Lora; font-style:italic;'>No conversation recorded.</p>", unsafe_allow_html=True)
                else:
                    for m in msgs:
                        is_in = m.get("dir") == "in"
                        bubble_bg = "#121212" if is_in else "#1C1C1C"
                        border_color = "#333333" if is_in else "#FF3333"
                        sender_label = f"PROSPECT: {selected_lead.get('name', 'User')}" if is_in else "AUTONOMOUS AI AGENT"
                        badge_color = "#22D3EE" if is_in else "#34D399"
                        align = "left"

                        st.markdown(f"""
                        <div style="margin-bottom: 0.85rem; border-left: 3px solid {border_color}; background: {bubble_bg}; padding: 0.75rem 1rem;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px;">
                                <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 700; color: {badge_color}; text-transform: uppercase;">
                                    {sender_label}
                                </span>
                                <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #666666;">
                                    {m.get('ts', '')}
                                </span>
                            </div>
                            <div style="font-family: 'Lora', serif; font-size: 0.95rem; color: #E8EAF6; white-space: pre-wrap; line-height: 1.45;">
                                {m.get('text', '')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

        # Simulator / Live Intercept Input Box
        st.markdown("<div style='font-family: \"JetBrains Mono\", monospace; font-size: 0.75rem; color: #888888; margin-top: 0.5rem;'>TEST WIRE SIMULATOR (SEND AS PROSPECT)</div>", unsafe_allow_html=True)
        s_col1, s_col2 = st.columns([4, 1])
        with s_col1:
            sim_input = st.text_input("Simulate Prospect Response", placeholder="e.g. 1, or Acme Logistics, or farhan@acme.com", label_visibility="collapsed", key="sim_wa_input")
        with s_col2:
            if st.button("SEND ↵", key="btn_send_sim"):
                if sim_input.strip() and selected_lead:
                    try:
                        requests.post(f"{API_BASE}/leads/{selected_lead['id']}/message", json={"channel": "whatsapp", "text": sim_input.strip()})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ── Right Column: CRM Lead Dossier ────────────────────────────────────────
    with col_crm:
        st.markdown("""
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; font-weight: 700; color: #F3F3EF; margin-bottom: 0.6rem;">
            ◈ REAL-TIME CRM DOSSIER & ACTIONS
        </div>
        """, unsafe_allow_html=True)

        if not selected_lead:
            st.info("Capture or select a prospect to view dossier.")
        else:
            sl_name = selected_lead.get("name", "Unknown")
            sl_phone = selected_lead.get("phone", "—")
            sl_company = selected_lead.get("company", "—")
            sl_email = selected_lead.get("email", "—")
            sl_priority = selected_lead.get("priority", "UNSCORED")
            sl_score = selected_lead.get("score", "—")
            sl_slot = selected_lead.get("slot", "—")
            sl_stage = selected_lead.get("stage", "captured").upper()
            sl_sentiment = selected_lead.get("sentiment", "neutral").upper()

            priority_badge = "badge-high" if sl_priority == "HOT" else ("badge-medium" if sl_priority == "WARM" else "badge-low")

            st.markdown(f"""
            <div class="noir-card" style="padding: 1.25rem; margin-bottom: 1rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 1px solid #262626; padding-bottom: 0.6rem; margin-bottom: 0.8rem;">
                    <div>
                        <div style="font-family: 'Playfair Display', serif; font-size: 1.25rem; font-weight: 700; color: #F3F3EF;">
                            {sl_name}
                        </div>
                        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #888888;">
                            {sl_company} · {sl_phone}
                        </div>
                    </div>
                    <span class="{priority_badge}">{sl_priority}</span>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;">
                    <div style="background: #0A0A0A; padding: 6px 10px; border: 1px solid #222;">
                        <span style="color: #666; display: block; font-size: 0.65rem;">STAGE</span>
                        <b style="color: #F3F3EF;">{sl_stage}</b>
                    </div>
                    <div style="background: #0A0A0A; padding: 6px 10px; border: 1px solid #222;">
                        <span style="color: #666; display: block; font-size: 0.65rem;">FIT SCORE</span>
                        <b style="color: #22D3EE;">{sl_score} / 100</b>
                    </div>
                    <div style="background: #0A0A0A; padding: 6px 10px; border: 1px solid #222;">
                        <span style="color: #666; display: block; font-size: 0.65rem;">WORK EMAIL</span>
                        <b style="color: #F3F3EF; word-break: break-all;">{sl_email}</b>
                    </div>
                    <div style="background: #0A0A0A; padding: 6px 10px; border: 1px solid #222;">
                        <span style="color: #666; display: block; font-size: 0.65rem;">DEMO SLOT</span>
                        <b style="color: #34D399;">{sl_slot}</b>
                    </div>
                </div>

                <div style="margin-top: 10px; padding: 6px 10px; background: #0A0A0A; border: 1px solid #222; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;">
                    <span style="color: #666; display: block; font-size: 0.65rem;">EMOTIONAL SENTIMENT</span>
                    <span style="color: {'#34D399' if sl_sentiment == 'POSITIVE' else ('#FF3333' if sl_sentiment == 'FRUSTRATED' else '#F3F3EF')}">
                        {sl_sentiment}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Operator Quick Actions
            st.markdown("<div style='font-family: \"JetBrains Mono\", monospace; font-size: 0.75rem; color: #888888; margin-bottom: 0.4rem;'>OPERATOR OVERRIDE CONTROLS</div>", unsafe_allow_html=True)
            act1, act2 = st.columns(2)
            with act1:
                if st.button("CONFIRM DEMO", key="act_demo"):
                    requests.post(f"{API_BASE}/leads/{selected_lead['id']}/action", json={"action": "reminder"})
                    st.rerun()
                if st.button("SEND PROPOSAL", key="act_prop"):
                    requests.post(f"{API_BASE}/leads/{selected_lead['id']}/action", json={"action": "proposal"})
                    st.rerun()
            with act2:
                if st.button("MARK DEAL WON", key="act_won"):
                    requests.post(f"{API_BASE}/leads/{selected_lead['id']}/action", json={"action": "won"})
                    st.rerun()
                if sl_phone and sl_phone != "—":
                    wa_clean = re.sub(r"\D", "", sl_phone)
                    st.link_button("OPEN IN WHATSAPP ↗", f"https://wa.me/{wa_clean}")

            # Sync into Nexomate Permanent Database
            if st.button("💾 SAVE PROSPECT TO PROSPECT REGISTRY (SQLITE)", key="btn_save_sql"):
                db = SessionLocal()
                try:
                    exists = db.query(Lead).filter((Lead.phone == sl_phone) | (Lead.email == sl_email)).first()
                    if not exists:
                        new_db_lead = Lead(
                            full_name=sl_name,
                            phone=sl_phone,
                            email=sl_email if "@" in str(sl_email) else None,
                            company=sl_company if sl_company != "—" else None,
                            source="WhatsApp Inbound AI",
                            fit_score=float(sl_score) if str(sl_score).isdigit() else 85.0,
                            score_level="HIGH" if sl_priority == "HOT" else "MEDIUM",
                            lead_status="QUALIFIED" if sl_stage in ("BOOKED", "WON") else "IN_PROGRESS",
                            notes=f"Auto-captured via WhatsApp AI. Demo Slot: {sl_slot}. Sentiment: {sl_sentiment}"
                        )
                        db.add(new_db_lead)
                        db.commit()
                        st.success(f"Prospect {sl_name} permanently saved into SQLite Prospect Directory!")
                    else:
                        st.info("Prospect already recorded in database.")
                finally:
                    db.close()

    # ── Refresh trigger ──────────────────────────────────────────────────────
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    if st.button("🔄 REFRESH WIRE TELEMETRY"):
        st.rerun()
