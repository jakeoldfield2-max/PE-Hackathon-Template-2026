import streamlit as st
from app.ui.helpers import api


def render_tab_urls(BASE: str) -> None:
    """List all URLs."""
    st.markdown("<div class='section-label'>All URLs</div>", unsafe_allow_html=True)

    status, data = api("GET", "/urls", BASE)

    if status is None or not isinstance(data, list):
        err = data.get("error", f"HTTP {status}") if isinstance(data, dict) else f"HTTP {status}"
        st.markdown(f"<div class='alert-err'>⚠ {err}</div>", unsafe_allow_html=True)
        return

    if not data:
        st.markdown("<div class='alert-warn'>No URLs found.</div>", unsafe_allow_html=True)
        return

    for url in data:
        is_active = url.get("is_active", False)
        dot_cls = "dot-active" if is_active else "dot-inactive"
        short_code = url.get("short_code", "")
        original = url.get("original_url", "")
        title = url.get("title", "")
        owner_id = url.get("user_id", "")

        st.markdown(
            f"<div class='url-row'>"
            f"<span class='{dot_cls}'></span>"
            f"<span class='code-badge'>{short_code}</span>"
            f"<span class='orig-url'>{original}</span>"
            f"<span class='url-title-cell'>{title}</span>"
            f"<span class='owner-cell'>#{owner_id}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
