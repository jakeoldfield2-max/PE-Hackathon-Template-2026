import streamlit as st
from app.ui.helpers import api


def render_header_stats(BASE: str) -> None:
    """Render the top-level stats metrics row."""
    st.markdown(
        "<h1 style='font-family:JetBrains Mono,monospace;font-size:1.6rem;"
        "font-weight:700;color:#e2e0db;margin:0 0 0.2rem 0;'>URLPulse</h1>"
        "<p style='font-family:Sora,sans-serif;font-size:0.85rem;color:#3d3d45;"
        "margin:0 0 1.8rem 0;'>URL shortener dashboard</p>",
        unsafe_allow_html=True,
    )

    status, data = api("GET", "/stats", BASE)

    if status != 200 or not isinstance(data, dict):
        st.markdown(
            f"<div class='alert-err'>⚠ Could not load stats — {data.get('error', status)}</div>",
            unsafe_allow_html=True,
        )
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total URLs", data.get("total_urls", "—"))
    with col2:
        st.metric("Active URLs", data.get("active_urls", "—"))
    with col3:
        st.metric("Total Users", data.get("total_users", "—"))
    with col4:
        st.metric("Active Users", data.get("active_users", "—"))

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
