# dashboard/overview.py
"""Overview / Home dashboard page — Noir Press Broadsheet Edition."""

import streamlit as st
from datetime import datetime
from database.database import SessionLocal
from database.models import Lead, Campaign, Message, Reply


def overview_page():
    db = SessionLocal()
    try:
        total_leads = db.query(Lead).filter(Lead.is_demo == False).count()
        high_priority = db.query(Lead).filter(Lead.is_demo == False, Lead.score_level == "HIGH").count()
        messages_sent = db.query(Message).filter(Message.is_demo == False, Message.status == "SENT").count()
        total_replies = db.query(Reply).filter(Reply.is_demo == False).count()
        interested = db.query(Lead).filter(Lead.is_demo == False, Lead.lead_status == "INTERESTED").count()

        # ── Broadsheet Editorial Masthead ────────────────────────────────────
        now_str = datetime.now().strftime("%A, %B %d, %Y").upper()
        st.markdown(f"""
        <div class="editorial-masthead">
            <div class="masthead-meta-row">
                <span>VOL. I · NOCTURNAL WIRE DISPATCH</span>
                <span>EDITION: LIVE PRODUCTION TERMINAL</span>
                <span>{total_leads} VERIFIED PROSPECTS</span>
            </div>
            <h1 class="masthead-main-title">THE NOCTURNAL WIRE</h1>
            <div class="masthead-sub-rule">Autonomous Lead Intelligence & Broadsheet Outreach Terminal · {now_str}</div>
        </div>

        <div style="background: #121212; border: 1px solid #333333; padding: 0.6rem 1rem; margin-bottom: 1.8rem; display: flex; align-items: center; justify-content: space-between; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <span class="badge-crimson" style="padding: 2px 7px;">LIVE DISPATCH</span>
                <span style="color: #F3F3EF; letter-spacing: 0.5px;">RECON ACTIVE: {total_leads} COMMERCIAL SOLAR ACCOUNTS CATALOGUED IN AUSTRALIA</span>
            </div>
            <div style="color: #888888;">● OPERATIONAL · ZERO LATENCY</div>
        </div>
        """, unsafe_allow_html=True)

        # ── KPI Cards ────────────────────────────────────────────────────────
        cols = st.columns(5)
        metrics = [
            ("Total Leads", total_leads),
            ("High Priority", high_priority),
            ("Messages Sent", messages_sent),
            ("Replies", total_replies),
            ("Interested", interested),
        ]

        for col, (label, value) in zip(cols, metrics):
            with col:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{value:,}</div>
                    <div class="metric-label">{label}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

        # ── Columns: Recent Leads & Recent Replies ───────────────────────────
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            <div class="section-header">
                <span>Recent Prospects</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #888888;">LIVE FEED</span>
            </div>
            """, unsafe_allow_html=True)

            recent_leads = db.query(Lead).filter(Lead.is_demo == False).order_by(Lead.created_at.desc()).limit(5).all()
            if recent_leads:
                for lead in recent_leads:
                    score_badge = ""
                    if lead.score_level == "HIGH":
                        score_badge = f'<span class="badge-high">HIGH {int(lead.fit_score or 0)}</span>'
                    elif lead.score_level == "MEDIUM":
                        score_badge = f'<span class="badge-medium">MED {int(lead.fit_score or 0)}</span>'
                    elif lead.score_level == "LOW":
                        score_badge = f'<span class="badge-low">LOW {int(lead.fit_score or 0)}</span>'

                    title_comp = lead.job_title or ''
                    if lead.company and lead.full_name:
                        title_comp += f" · {lead.company}"
                    elif lead.company and not lead.full_name:
                        title_comp = lead.industry or lead.company or 'Direct Inbound'

                    subtitle = title_comp.strip()
                    if lead.city:
                        subtitle += f" · {lead.city}"
                    if not subtitle:
                        subtitle = lead.phone or lead.email or "WhatsApp Inbound Prospect"

                    card_html = (
                        '<div class="noir-card" style="padding: 1rem 1.2rem; margin-bottom: 0.6rem;">'
                        '<div style="display:flex; justify-content:space-between; align-items:center;">'
                        '<div>'
                        f'<div style="font-family: \'Lora\', serif; font-weight: 700; font-size: 1rem; color: #F3F3EF;">{lead.full_name or lead.company or "Unknown Lead"}</div>'
                        f'<div style="font-family: \'JetBrains Mono\', monospace; color: #888888; font-size: 0.75rem; margin-top: 2px;">{subtitle}</div>'
                        '</div>'
                        f'<div>{score_badge}</div>'
                        '</div>'
                        '</div>'
                    )
                    st.markdown(card_html, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="noir-card" style="padding: 1.5rem; text-align: center; color: #888888; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;">
                    NO DISPATCHES RECORDED. PROCEED TO RECONNAISSANCE TO LOCATE TARGETS.
                </div>
                """, unsafe_allow_html=True)

        # ── Recent Replies ───────────────────────────────────────────────────
        with col2:
            st.markdown("""
            <div class="section-header">
                <span>Incoming Wire</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #888888;">INBOX STREAM</span>
            </div>
            """, unsafe_allow_html=True)

            recent_replies = db.query(Reply).filter(Reply.is_demo == False).order_by(Reply.received_at.desc()).limit(5).all()
            if recent_replies:
                for reply in recent_replies:
                    lead = db.query(Lead).filter(Lead.lead_id == reply.lead_id).first()
                    classification = reply.classification or reply.user_override or "UNKNOWN"
                    badge_class = "badge-high" if classification == "INTERESTED" else "badge-medium"
                    sender_name = lead.full_name if lead else reply.sender
                    body_snippet = (reply.body or '').strip()[:130] or "Incoming response"

                    reply_html = (
                        '<div class="noir-card" style="padding: 1rem 1.2rem; margin-bottom: 0.6rem;">'
                        '<div style="display: flex; justify-content: space-between; align-items: baseline;">'
                        f'<div style="font-family: \'Lora\', serif; font-weight: 700; font-size: 1rem; color: #F3F3EF;">{sender_name}</div>'
                        f'<span class="{badge_class}">{classification}</span>'
                        '</div>'
                        f'<div style="font-family: \'Lora\', serif; color: #CCCCCC; font-size: 0.85rem; margin-top: 0.4rem; font-style: italic;">"{body_snippet}..."</div>'
                        '</div>'
                    )
                    st.markdown(reply_html, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="noir-card" style="padding: 1.5rem; text-align: center; color: #888888; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;">
                    NO WIRE REPLIES INTERCEPTED YET. TRANSMIT OUTREACH TO INITIATE RESPONSES.
                </div>
                """, unsafe_allow_html=True)

        # ── Active Campaigns ─────────────────────────────────────────────────
        st.markdown("""
        <div class="section-header" style="margin-top: 2rem;">
            <span>Active Deployments</span>
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #888888;">CAMPAIGN DIRECTORY</span>
        </div>
        """, unsafe_allow_html=True)

        active_campaigns = db.query(Campaign).filter(
            Campaign.is_demo == False,
            Campaign.status.in_(["RUNNING", "READY", "DRAFT"])
        ).order_by(Campaign.created_at.desc()).limit(3).all()

        if active_campaigns:
            cols = st.columns(3)
            for i, campaign in enumerate(active_campaigns):
                with cols[i % 3]:
                    status_badge = "badge-high" if campaign.status == "RUNNING" else "badge-medium"
                    st.markdown(f"""
                    <div class="noir-card" style="padding: 1.25rem;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div style="font-family: 'Playfair Display', serif; font-weight: 700; font-size: 1.15rem; color: #F3F3EF;">
                                {campaign.name}
                            </div>
                            <span class="{status_badge}">{campaign.status}</span>
                        </div>
                        <div style="font-family: 'JetBrains Mono', monospace; color: #888888; font-size: 0.75rem; margin: 0.5rem 0 1rem 0;">
                            {campaign.industry or 'GENERAL'} · {campaign.location or 'AUSTRALIA'}
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; border-top: 1px solid #262626; padding-top: 0.75rem; text-align: center;">
                            <div>
                                <div style="font-family: 'Playfair Display', serif; font-size: 1.3rem; font-weight: 700; color: #F3F3EF;">{campaign.total_leads}</div>
                                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #888888; text-transform: uppercase;">Leads</div>
                            </div>
                            <div>
                                <div style="font-family: 'Playfair Display', serif; font-size: 1.3rem; font-weight: 700; color: #F3F3EF;">{campaign.emails_sent}</div>
                                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #888888; text-transform: uppercase;">Sent</div>
                            </div>
                            <div>
                                <div style="font-family: 'Playfair Display', serif; font-size: 1.3rem; font-weight: 700; color: #F3F3EF;">{campaign.replies_count}</div>
                                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #888888; text-transform: uppercase;">Replies</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="noir-card" style="padding: 1.5rem; text-align: center; color: #888888; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;">
                NO ACTIVE CAMPAIGN MISSIONS. LAUNCH A NEW CAMPAIGN IN THE CAMPAIGNS TERMINAL.
            </div>
            """, unsafe_allow_html=True)

    finally:
        db.close()
