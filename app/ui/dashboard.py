import streamlit as st
from app.ui.helpers import api

def render_header_stats(BASE):
    st.markdown(
        '<div style="font-family:JetBrains Mono,monospace;font-size:2.4rem;font-weight:700;color:#e2e0db;letter-spacing:-0.03em;line-height:1;">'
        'URL<span style="color:#4ade80;">Pulse</span></div>'
        '<div style="font-family:JetBrains Mono,monospace;font-size:0.7rem;color:#2e2e38;letter-spacing:0.12em;margin-bottom:1.5rem;">// shorten · track · observe</div>',
        unsafe_allow_html=True,
    )

    s_status, stats = api("GET", "/stats", BASE)
    if not (s_status == 200 and isinstance(stats, dict)):
        st.markdown('<div class="alert-warn" style="margin-bottom: 1rem;">System Offline — metrics temporarily unavailable. Verify backend connection in sidebar.</div>', unsafe_allow_html=True)
        stats = {}
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total URLs",   stats.get("total_urls",   "—"))
    c2.metric("Active URLs",  stats.get("active_urls",  "—"))
    c3.metric("Active Users", stats.get("active_users", "—"))
    c4.metric("Total Events", stats.get("total_events", "—"))
    c5.metric("Created evts", stats.get("events_by_type", {}).get("created", "—"))

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
