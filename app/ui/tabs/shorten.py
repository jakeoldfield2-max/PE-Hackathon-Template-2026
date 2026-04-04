import streamlit as st
from app.ui.helpers import api, gen_code


def render_tab_shorten(BASE: str, user_map: dict) -> None:
    """Shorten a new URL."""
    st.markdown("<div class='section-label'>Shorten a URL</div>", unsafe_allow_html=True)

    if not user_map:
        st.markdown(
            "<div class='alert-warn'>⚠ No users found. Create a user in the Users tab first.</div>",
            unsafe_allow_html=True,
        )
        return

    owner_label = st.selectbox("Owner", list(user_map.keys()), key="shorten_owner")
    original_url = st.text_input("Original URL", placeholder="https://example.com/very/long/path", key="shorten_url")
    title = st.text_input("Title / label", placeholder="My link", key="shorten_title")

    if st.button("⚡ Shorten", key="shorten_btn"):
        if not original_url or not title:
            st.markdown("<div class='alert-err'>Original URL and title are required.</div>", unsafe_allow_html=True)
        else:
            uid = user_map[owner_label]
            status, data = api(
                "POST", "/shorten", BASE,
                json={"user_id": uid, "original_url": original_url, "title": title},
            )
            if status == 201 and isinstance(data, dict):
                short_url = data.get("short_url", "")
                short_code = data.get("short_code", "")
                st.markdown(
                    f"<div class='result-box'>"
                    f"<div class='result-label'>shortened url</div>"
                    f"<a class='result-link' href='{short_url}' target='_blank'>{short_url}</a>"
                    f"<div style='font-family:JetBrains Mono,monospace;font-size:0.72rem;"
                    f"color:#2e7040;margin-top:0.4rem;'>code: {short_code}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                err = data.get("error", f"HTTP {status}") if isinstance(data, dict) else f"HTTP {status}"
                st.markdown(f"<div class='alert-err'>✗ {err}</div>", unsafe_allow_html=True)
