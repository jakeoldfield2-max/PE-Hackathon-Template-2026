import streamlit as st
from app.ui.helpers import api

def render_header_stats(BASE):
    st.markdown(
        '<div style="font-family:JetBrains Mono,monospace;font-size:2.4rem;font-weight:700;color:var(--text);letter-spacing:-0.03em;line-height:1;">'
        'URL<span style="color:var(--accent);">Pulse</span></div>'
        '<div style="font-family:JetBrains Mono,monospace;font-size:0.7rem;color:var(--text-xdim);letter-spacing:0.12em;margin-bottom:1.5rem;">// shorten · track · observe</div>',
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

    ev_status, events = api("GET", "/events", BASE, json={"limit": 5})
    if ev_status == 200 and isinstance(events, list) and events:
        st.markdown(
            '<div style="font-family:JetBrains Mono,monospace;font-size:0.68rem;color:var(--text-xdim);margin-top:0.8rem;">recent events</div>',
            unsafe_allow_html=True,
        )
        for event in events:
            ev_type = event.get("event_type", "?")
            ev_url_id = event.get("url_id", "?")
            ev_user_id = event.get("user_id", "?")
            st.markdown(
                f'<div style="font-family:JetBrains Mono,monospace;font-size:0.72rem;color:var(--text-dim);">'
                f'[{ev_type}] url:{ev_url_id} user:{ev_user_id}'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
